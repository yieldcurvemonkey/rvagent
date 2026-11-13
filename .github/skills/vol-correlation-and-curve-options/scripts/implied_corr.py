"""Implied vs realized correlation for curve (CMS spread) options and midcurves, normal (bp) model.

Conventions
  vols        normal (Bachelier) vol, bp per year
  spread      S = w_b * B - w_a * A  (2s10s cap: A = 2y rate, B = 10y rate, w = 1)
  spread var  sig_s^2 = w_a^2 sig_a^2 + w_b^2 sig_b^2 - 2 rho w_a w_b sig_a sig_b
  premiums    bp of notional; a swaption premium = annuity * Bachelier(F, K, sig, T) * df
  implied rho is returned RAW (not clipped): > 1 means the spread/midcurve vol is below the rho = 1 floor.

CLI
  python implied_corr.py spread --sig-a 49.5 --sig-b 55.4 --sig-s 20.1
  python implied_corr.py spread --premium 4 --fwd 9.8 --strike 9.8 --T 0.25          (vol from a curve-cap premium)
  python implied_corr.py spread --premium 96 --fwd 266 --strike 266 --T 0.25 --annuity 8.68 --kind put
  python implied_corr.py fwdvol --sig1 107 --T1 0.5 --sig2 99 --T2 1.5
  python implied_corr.py midcurve --vol-surface vol_surface.csv [--snap eod_ny] [--date 2026-11-10] [--ccy USD] [--rate 3.5]
  python implied_corr.py realized --curve-par curve_par.csv --curve-id USD-SOFR --a 2Y --b 10Y [--snap eod_ny] [--window 63]
  python implied_corr.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

DAYS = 252


# ---------- core formulas ----------
def spread_vol(sig_a, sig_b, rho, w_a=1.0, w_b=1.0):
    """Normal vol of S = w_b*B - w_a*A."""
    var = (w_a * sig_a) ** 2 + (w_b * sig_b) ** 2 - 2.0 * rho * w_a * w_b * sig_a * sig_b
    return np.sqrt(np.maximum(var, 0.0))


def implied_corr(sig_s, sig_a, sig_b, w_a=1.0, w_b=1.0):
    """Correlation that reprices sig_s from the leg vols. Raw: may fall outside [-1, 1]."""
    return ((w_a * sig_a) ** 2 + (w_b * sig_b) ** 2 - np.square(sig_s)) / (2.0 * w_a * w_b * sig_a * sig_b)


def dspread_drho(sig_a, sig_b, sig_s, w_a=1.0, w_b=1.0):
    """bp of spread vol per 1.00 of correlation (negative: higher rho, lower spread vol)."""
    return -w_a * w_b * sig_a * sig_b / sig_s


def bachelier(fwd, strike, sig, T, df=1.0, kind="call", annuity=1.0):
    """Normal-model option price, same units as fwd/strike (bp). call = cap/payer, put = floor/receiver."""
    sd = sig * math.sqrt(T)
    if sd <= 0:
        return df * annuity * max((fwd - strike) if kind == "call" else (strike - fwd), 0.0)
    d = (fwd - strike) / sd
    call = (fwd - strike) * norm.cdf(d) + sd * norm.pdf(d)
    px = call if kind == "call" else call - (fwd - strike)
    return df * annuity * px


def bachelier_iv(price, fwd, strike, T, df=1.0, kind="call", annuity=1.0):
    """Normal vol (bp/yr) that reprices `price` (bp of notional)."""
    intrinsic = df * annuity * max((fwd - strike) if kind == "call" else (strike - fwd), 0.0)
    if price <= intrinsic:
        raise ValueError("price at or below intrinsic value")
    return brentq(lambda s: bachelier(fwd, strike, s, T, df, kind, annuity) - price, 1e-6, 5000.0)


def forward_vol(sig1, T1, sig2, T2, t0=0.0):
    """Forward vol between expiries T1 < T2 on the same underlying (variance additivity).
    (T2-T1) sig_f^2 = (T2-t0) sig2^2 - (T1-t0) sig1^2. NaN if the forward variance is negative."""
    var = ((T2 - t0) * sig2 ** 2 - (T1 - t0) * sig1 ** 2) / (T2 - T1)
    return math.sqrt(var) if var >= 0 else float("nan")


def annuity(n_years, rate_pct):
    """Flat-rate annual-pay annuity (years per unit notional). Fractional n is a smooth approximation."""
    r = rate_pct / 100.0
    return n_years if abs(r) < 1e-12 else (1.0 - (1.0 + r) ** (-n_years)) / r


def midcurve_weights(gap_years, tail_years, rate_pct):
    """Weights so that F(T2,T3) = w13*F(T1,T3) - w12*F(T1,T2) at the expiry T1.
    gap = T2 - T1, tail = T3 - T2. Flat-curve annuities: w13 - w12 = 1 exactly.
    ponytail: flat-rate annuities; use DV01s from a built curve when weights matter to < 1%."""
    a13 = annuity(gap_years + tail_years, rate_pct)
    a12 = annuity(gap_years, rate_pct)
    a23 = a13 - a12
    return a13 / a23, a12 / a23


# ---------- time series ----------
def realized(a: pd.Series, b: pd.Series, window: int = 63) -> pd.DataFrame:
    """Rolling realized normal vols (bp/yr) of A, B, B-A and the correlation of daily changes.
    Inputs are levels in pct (canonical par_rate_pct); changes are converted to bp."""
    d = pd.concat({"a": a, "b": b}, axis=1).dropna().diff().mul(100.0).dropna()
    out = pd.DataFrame(index=d.index)
    out["vol_a_bp"] = d["a"].rolling(window).std() * math.sqrt(DAYS)
    out["vol_b_bp"] = d["b"].rolling(window).std() * math.sqrt(DAYS)
    out["vol_spread_bp"] = (d["b"] - d["a"]).rolling(window).std() * math.sqrt(DAYS)
    out["corr"] = d["a"].rolling(window).corr(d["b"])
    return out.dropna()


def tenor_years(t: str) -> float:
    t = str(t).strip().upper()
    if t in ("0D", "", "NAN", "NONE"):
        return 0.0
    n, u = float(t[:-1]), t[-1]
    return {"D": n / 365.0, "W": n / 52.0, "M": n / 12.0, "Y": n}[u]


def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def _one_snap(df: pd.DataFrame, snap: str | None) -> pd.DataFrame:
    """Never mix snaps in one series: filter to `snap`, or fail if the file holds several."""
    if snap:
        df = df[df["snap"] == snap]
    if "snap" in df and df["snap"].nunique() > 1:
        raise SystemExit(f"several snaps in input {sorted(df['snap'].unique())}: pass --snap")
    return df


def midcurve_table(vs: pd.DataFrame, default_rate_pct: float = 3.0) -> pd.DataFrame:
    """For each ATM midcurve row (expiry E, fwd_start G, tenor L) find ATM swaptions E x (G+L) and E x G
    on the same date/ccy/index and return the implied correlation and the rho=1 floor vol."""
    vs = vs[np.isclose(vs["strike_offset_bp"].astype(float), 0.0)].copy()
    key = ["date", "ccy", "index_id", "expiry"]
    sw = vs[vs["product"] == "swaption"].copy()
    sw["tail_y"] = sw["tenor"].map(tenor_years).round(4)
    sw = sw.set_index(key + ["tail_y"])["nvol_bp"]
    sw = sw[~sw.index.duplicated()]
    rows = []
    for _, r in vs[vs["product"] == "midcurve"].iterrows():
        g, l = tenor_years(r["fwd_start"]), tenor_years(r["tenor"])
        k = tuple(r[c] for c in key)
        s13, s12 = sw.get(k + (round(g + l, 4),)), sw.get(k + (round(g, 4),))
        if s13 is None or s12 is None or pd.isna(s13) or pd.isna(s12):
            rows.append({**{c: r[c] for c in key}, "fwd_start": r["fwd_start"], "tenor": r["tenor"],
                         "status": "missing vanilla leg (interpolate tails first)"})
            continue
        rate = r.get("atm_fwd_pct")
        rate = default_rate_pct if rate is None or pd.isna(rate) else float(rate)
        w13, w12 = midcurve_weights(g, l, rate)
        rho = float(implied_corr(r["nvol_bp"], s12, s13, w_a=w12, w_b=w13))
        rows.append({**{c: r[c] for c in key}, "fwd_start": r["fwd_start"], "tenor": r["tenor"],
                     "mc_nvol_bp": r["nvol_bp"], "vanilla_long_nvol_bp": s13, "vanilla_short_nvol_bp": s12,
                     "w_long": round(w13, 4), "w_short": round(w12, 4), "implied_corr": round(rho, 4),
                     "rho1_floor_nvol_bp": round(float(spread_vol(s12, s13, 1.0, w12, w13)), 2),
                     "status": "rho>1: below rho=1 floor, check inputs" if rho > 1 else "ok"})
    return pd.DataFrame(rows)


# ---------- self-test ----------
def selftest() -> int:
    fails = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got:.4f} want {want:.4f} (tol {tol})")
        if not ok:
            fails.append(name)

    # 1. analytic anchors of the spread-vol formula
    check("rho=1 spread vol = |100-60|", float(spread_vol(100, 60, 1.0)), 40.0, 1e-9)
    check("rho=0 spread vol = rss", float(spread_vol(100, 60, 0.0)), math.sqrt(100**2 + 60**2), 1e-9)
    check("rho=-1 spread vol = 160", float(spread_vol(100, 60, -1.0)), 160.0, 1e-9)
    check("implied corr inverts rho=0.9", float(implied_corr(spread_vol(86, 76.8, 0.9), 86, 76.8)), 0.9, 1e-12)
    check("dS/drho finite diff", dspread_drho(80, 60, float(spread_vol(80, 60, 0.7))),
          float(spread_vol(80, 60, 0.7005) - spread_vol(80, 60, 0.6995)) / 0.001, 1e-3)

    # 2. simulation with known parameters: realized spread vol and corr recover the inputs
    rng = np.random.default_rng(7)
    n, sa, sb, rho = 200_000, 80.0, 60.0, 0.7
    z1, z2 = rng.standard_normal(n), rng.standard_normal(n)
    da = sa / math.sqrt(DAYS) * z1
    db = sb / math.sqrt(DAYS) * (rho * z1 + math.sqrt(1 - rho**2) * z2)
    lvl = pd.DataFrame({"a": 3 + np.cumsum(da) / 100, "b": 4 + np.cumsum(db) / 100})
    rz = realized(lvl["a"], lvl["b"], window=n - 5).iloc[-1]
    check("sim realized corr", rz["corr"], rho, 0.01)
    check("sim realized spread vol vs formula", rz["vol_spread_bp"], float(spread_vol(sa, sb, rho)), 0.6)
    check("sim implied corr from realized vols", float(implied_corr(rz["vol_spread_bp"], rz["vol_a_bp"],
                                                                   rz["vol_b_bp"])), rho, 0.01)

    # 3. Bachelier: ATM closed form, parity, inversion. RateLab 2006: 1y ATM 2s10s cap 15bp -> ~37.6bp
    check("ATM = sig*sqrt(T/2pi)", bachelier(28, 28, 37.6, 1.0), 37.6 * math.sqrt(1 / (2 * math.pi)), 1e-9)
    c, p = bachelier(27, 40, 30, 1.0, 0.97), bachelier(27, 40, 30, 1.0, 0.97, "put")
    check("put-call parity", c - p, 0.97 * (27 - 40), 1e-9)
    check("1y ATM cap 15bp -> spread vol", bachelier_iv(15, 28, 28, 1.0), 15 * math.sqrt(2 * math.pi), 1e-6)
    # annuity: 10y annual at 2.66% = (1 - 1.0266^-10)/0.0266 = 8.6801; JPM Mar 2019 3Mx10Y ATM receiver 96c -> 55.45bp
    check("flat annuity 10y @ 2.66%", annuity(10, 2.66), (1 - 1.0266 ** -10) / 0.0266, 1e-12)
    check("annuity 10y @ 2.66% value", annuity(10, 2.66), 8.6801, 1e-4)
    check("receiver premium -> vol with annuity", bachelier_iv(96, 266, 266, 0.25, kind="put", annuity=annuity(10, 2.66)),
          96 / (8.68015 * math.sqrt(0.25 / (2 * math.pi))), 1e-3)

    # 4. FVA primer (Credit Suisse, Aug 2013): 6m1y10y midcurve at rho=1 ~106-107, 6m-fwd 1y10y vol ~95
    mc = float(spread_vol(37, 99, 1.0, w_a=1.0 / 8.6, w_b=9.6 / 8.6))
    check("FVA midcurve vol rho=1 = (9.6*99 - 37)/8.6", mc, 106.21, 0.01)
    check("FVA forward vol", forward_vol(107, 0.5, 99, 1.5), 94.7, 0.5)
    check("calendar cap fwd vol = sqrt(2*s1y^2 - s6m^2)", forward_vol(25, 0.5, 30, 1.0),
          math.sqrt(2 * 30**2 - 25**2), 1e-9)

    # 5. flat-curve midcurve weights: forward identity w13 - w12 = 1
    w13, w12 = midcurve_weights(5, 5, 3.5)
    check("midcurve weights w13 - w12", w13 - w12, 1.0, 1e-12)

    # 6. midcurve_table on canonical rows: 1y5y5y priced at a known rho with asymmetric legs recovers it
    s13, s12, rho_true = 90.0, 95.0, 0.8
    w13, w12 = midcurve_weights(5, 5, 3.8)
    base = {"date": "2026-11-10", "snap": "eod_ny", "ccy": "USD", "index_id": "USD-SOFR", "expiry": "1Y",
            "strike_offset_bp": 0.0}
    vs = pd.DataFrame([
        {**base, "product": "swaption", "fwd_start": "0D", "tenor": "10Y", "atm_fwd_pct": 3.6, "nvol_bp": s13},
        {**base, "product": "swaption", "fwd_start": "0D", "tenor": "5Y", "atm_fwd_pct": 3.5, "nvol_bp": s12},
        {**base, "product": "midcurve", "fwd_start": "5Y", "tenor": "5Y", "atm_fwd_pct": 3.8,
         "nvol_bp": float(spread_vol(s12, s13, rho_true, w_a=w12, w_b=w13))},
    ])
    check("midcurve_table recovers rho", float(midcurve_table(vs)["implied_corr"].iloc[0]), rho_true, 1e-3)
    vs.loc[1, "nvol_bp"] = np.nan  # a NaN vanilla leg must be flagged, not priced
    check("NaN leg flagged missing", float(midcurve_table(vs)["status"].iloc[0].startswith("missing")), 1.0, 0)

    print("SELFTEST", "FAILED: " + ", ".join(fails) if fails else "PASSED")
    return 1 if fails else 0


# ---------- CLI ----------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    s = sub.add_parser("spread", help="spread vol <-> implied correlation; premium -> normal vol")
    s.add_argument("--sig-a", type=float, help="short-leg normal vol, bp/yr")
    s.add_argument("--sig-b", type=float, help="long-leg normal vol, bp/yr")
    s.add_argument("--w-a", type=float, default=1.0)
    s.add_argument("--w-b", type=float, default=1.0)
    s.add_argument("--rho", type=float)
    s.add_argument("--sig-s", type=float, help="spread normal vol, bp/yr")
    s.add_argument("--premium", type=float, help="option premium, bp of notional")
    s.add_argument("--fwd", type=float, help="forward (spread or rate) in bp")
    s.add_argument("--strike", type=float, help="strike in bp")
    s.add_argument("--T", type=float, help="expiry, years")
    s.add_argument("--df", type=float, default=1.0)
    s.add_argument("--annuity", type=float, default=1.0, help="1 for single-look spread options")
    s.add_argument("--kind", choices=["call", "put"], default="call")

    f = sub.add_parser("fwdvol", help="forward vol from two expiries on the same underlying")
    for a in ("--sig1", "--T1", "--sig2", "--T2"):
        f.add_argument(a, type=float, required=True)

    m = sub.add_parser("midcurve", help="midcurve implied correlations from a canonical vol_surface file")
    m.add_argument("--vol-surface", required=True)
    m.add_argument("--snap")
    m.add_argument("--date")
    m.add_argument("--ccy")
    m.add_argument("--rate", type=float, default=3.0, help="flat rate pct if atm_fwd_pct is missing")
    m.add_argument("--out")

    r = sub.add_parser("realized", help="rolling realized leg/spread vols and correlation from curve_par")
    r.add_argument("--curve-par", required=True)
    r.add_argument("--curve-id", required=True)
    r.add_argument("--snap")
    r.add_argument("--a", required=True, help="short tenor, e.g. 2Y")
    r.add_argument("--b", required=True, help="long tenor, e.g. 10Y")
    r.add_argument("--start", default="0D")
    r.add_argument("--window", type=int, default=63)
    r.add_argument("--out")

    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    if a.cmd == "spread":
        if a.premium is not None:
            sig = bachelier_iv(a.premium, a.fwd, a.strike, a.T, a.df, a.kind, a.annuity)
            print(f"implied normal vol: {sig:.3f} bp/yr")
            if a.sig_s is None:
                a.sig_s = sig
        if a.sig_a is not None and a.sig_b is not None:
            if a.rho is not None:
                print(f"spread vol: {float(spread_vol(a.sig_a, a.sig_b, a.rho, a.w_a, a.w_b)):.3f} bp/yr")
            elif a.sig_s is not None:
                rho = float(implied_corr(a.sig_s, a.sig_a, a.sig_b, a.w_a, a.w_b))
                print(f"implied corr: {rho:.4f}{'  (>1: below rho=1 floor)' if rho > 1 else ''}")
                print(f"d spread vol / d rho: {dspread_drho(a.sig_a, a.sig_b, a.sig_s, a.w_a, a.w_b):.2f} bp per 1.00")
        return 0

    if a.cmd == "fwdvol":
        print(f"forward vol: {forward_vol(a.sig1, a.T1, a.sig2, a.T2):.3f} bp/yr")
        return 0

    if a.cmd == "midcurve":
        vs = _read(a.vol_surface)
        vs["date"] = vs["date"].astype(str)
        if a.date:
            vs = vs[vs["date"] == a.date]
        if a.ccy:
            vs = vs[vs["ccy"] == a.ccy]
        out = midcurve_table(_one_snap(vs, a.snap), a.rate)
        out.to_csv(a.out, index=False) if a.out else print(out.to_string(index=False))
        return 0

    if a.cmd == "realized":
        cp = _read(a.curve_par)
        cp = _one_snap(cp[(cp["curve_id"] == a.curve_id) & (cp["start"] == a.start)], a.snap)
        piv = cp.pivot_table(index="date", columns="tenor", values="par_rate_pct").sort_index()
        out = realized(piv[a.a], piv[a.b], a.window)
        if out.empty:
            raise SystemExit(f"history shorter than --window {a.window} after dropping gaps")
        out.to_csv(a.out) if a.out else print(out.tail(10).round(3).to_string())
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
