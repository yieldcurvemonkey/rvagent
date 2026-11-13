"""Fit a Nelson-Siegel-Svensson discount curve to government bond prices and report issue rich/cheap.

Model (continuously compounded zero rate, tau in years, decimals):
    z(t) = b0 + b1*(1-e^-x1)/x1 + b2*[(1-e^-x1)/x1 - e^-x1] + b3*[(1-e^-x2)/x2 - e^-x2],  x_k = t/lam_k
    DF(t) = exp(-z(t)*t);  P_model_i = sum_j CF_ij * DF(t_ij)   (dirty, per 100, actual cash flows)
Objective (yield space, Duering eq. 19.33 / JPM 1/(P*D) weights):
    min sum_i [ (P_i - P_model_i) / (P_i * D_i / 1e4) ]^2      -> each error is ~ a yield error in bp
    4 multi-starts on (lam1, lam2), lam in [0.05, 30]; loss 'linear' (OLS) or 'soft_l1' (robust, knee at 1bp).
Outputs per bond (SIGNS STATED):
    price_gap   = P_mkt - P_model           (+ = RICH, Tuckman convention), per 100 face
    spread_bp   = y(P_mkt) - y(P_model)     (+ = CHEAP, spline/z-type spread, Duering eq. 22.2)
    z_3m        = rolling z-score of spread_bp per bond (default 63 observations; uses data up to and including
                  the row's date, so lag it one day before trading)
    loo         = optional leave-one-out: the bond is excluded from the curve that prices it.

ponytail: year fractions are ACT/365.25 and the coupon schedule is rolled back from maturity
(no stubs, ex-div or holiday adjustment). Both P_mkt and P_model use the same flows, so spread_bp
error is small; use a full conventions engine (fi-g10-market-conventions) when sub-0.1bp matters.

CLI (canonical tables from data-contract-and-adapters; CSV or Parquet):
    python fit_curve.py --static bond_static.csv --quotes bond_quotes.csv --issuer US --out rc_us.csv
    python fit_curve.py --static bond_static.parquet --quotes bond_quotes.parquet --issuer DE --loo --robust
    python fit_curve.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq, least_squares

STARTS = [(2.0, 5.0), (1.5, 4.0), (3.0, 8.0), (1.0, 10.0)]
LAM_BOUNDS = (0.05, 30.0)


# ---------------------------------------------------------------- curve
def nss_zero(t, p) -> np.ndarray:
    """Zero rate (decimal, cont. comp.) for params p = [b0, b1, b2, b3, lam1, lam2]."""
    b0, b1, b2, b3, l1, l2 = p
    t = np.maximum(np.asarray(t, float), 1e-6)
    x1, x2 = t / l1, t / l2
    s1 = (1 - np.exp(-x1)) / x1
    s2 = (1 - np.exp(-x2)) / x2
    return b0 + b1 * s1 + b2 * (s1 - np.exp(-x1)) + b3 * (s2 - np.exp(-x2))


def nss_df(t, p) -> np.ndarray:
    t = np.asarray(t, float)
    return np.exp(-nss_zero(t, p) * t)


# ---------------------------------------------------------------- bond maths
def cashflows(asof, maturity, coupon_pct: float, freq: int):
    """Future flows per 100 face after `asof`: (times in years, amounts, accrued)."""
    asof, maturity = pd.Timestamp(asof), pd.Timestamp(maturity)
    if freq <= 0:
        return np.array([(maturity - asof).days / 365.25]), np.array([100.0]), 0.0
    dates = [maturity]
    while dates[-1] > asof:   # roll back from maturity in whole periods (no day-of-month drift: 31 Aug -> 28 Feb -> 31 Aug)
        dates.append(maturity - pd.DateOffset(months=(12 // freq) * len(dates)))
    prev = dates.pop()                       # last coupon date on/before asof
    dates = dates[::-1]
    cpn = coupon_pct / freq
    amts = np.full(len(dates), cpn)
    amts[-1] += 100.0
    t = np.array([(d - asof).days / 365.25 for d in dates])
    accrued = cpn * (asof - prev).days / max((dates[0] - prev).days, 1)
    return t, amts, accrued


def price_from_yield(y_pct: float, t, cf, freq: int) -> float:
    f = max(freq, 1)
    return float(np.sum(cf / (1 + y_pct / 100 / f) ** (f * t)))


def yield_from_price(p_dirty: float, t, cf, freq: int) -> float:
    """Yield in % compounded `freq` times a year (annual for zeros)."""
    return 100 * brentq(lambda y: price_from_yield(100 * y, t, cf, freq) - p_dirty, -0.5, 1.0, xtol=1e-12)


def mod_duration(y_pct: float, t, cf, freq: int) -> float:
    h = 0.01
    up, dn = price_from_yield(y_pct + h, t, cf, freq), price_from_yield(y_pct - h, t, cf, freq)
    return -(up - dn) / (2 * h / 100) / price_from_yield(y_pct, t, cf, freq)


# ---------------------------------------------------------------- fitting
def _model_prices(p, bonds):
    return np.array([np.sum(b["cf"] * nss_df(b["t"], p)) for b in bonds])


def fit_nss(bonds: list[dict], robust: bool = False):
    """bonds: dicts with t, cf, dirty, dur. Returns (params, rmse_bp of weighted errors)."""
    scale = np.array([b["dirty"] * b["dur"] / 1e4 for b in bonds])
    dirty = np.array([b["dirty"] for b in bonds])
    lo = [-1, -1, -1, -1, LAM_BOUNDS[0], LAM_BOUNDS[0]]
    hi = [1, 1, 1, 1, LAM_BOUNDS[1], LAM_BOUNDS[1]]
    best = None
    for l1, l2 in STARTS:
        y_long = np.median([yield_from_price(b["dirty"], b["t"], b["cf"], b["freq"]) for b in bonds]) / 100
        x0 = [y_long, 0.0, 0.0, 0.0, l1, l2]
        r = least_squares(lambda p: (dirty - _model_prices(p, bonds)) / scale, x0, bounds=(lo, hi),
                          loss="soft_l1" if robust else "linear", f_scale=1.0, xtol=1e-12, ftol=1e-12)
        if best is None or r.cost < best.cost:
            best = r
    return best.x, float(np.sqrt(np.mean(best.fun ** 2)))


def rich_cheap_one_date(df: pd.DataFrame, asof, robust: bool = False, loo: bool = False) -> pd.DataFrame:
    """df: one row per bond with instrument_id, coupon_pct, coupon_freq, maturity_date, dirty_px."""
    bonds = []
    for r in df.itertuples(index=False):
        t, cf, _ = cashflows(asof, r.maturity_date, r.coupon_pct, int(r.coupon_freq))
        freq = int(r.coupon_freq) or 1
        y = yield_from_price(r.dirty_px, t, cf, freq)
        bonds.append(dict(id=r.instrument_id, t=t, cf=cf, dirty=float(r.dirty_px), freq=freq, y=y,
                          dur=mod_duration(y, t, cf, freq), ttm=t[-1]))
    params, rmse = fit_nss(bonds, robust)
    out = []
    for i, b in enumerate(bonds):
        p = params
        if loo:
            p = fit_nss(bonds[:i] + bonds[i + 1:], robust)[0]
        pm = float(np.sum(b["cf"] * nss_df(b["t"], p)))
        ym = yield_from_price(pm, b["t"], b["cf"], b["freq"])
        out.append(dict(date=pd.Timestamp(asof), instrument_id=b["id"], ttm_years=b["ttm"], ytm_pct=b["y"],
                        model_ytm_pct=ym, price_gap=b["dirty"] - pm, spread_bp=100 * (b["y"] - ym),
                        mod_dur=b["dur"], fit_rmse_bp=rmse))
    return pd.DataFrame(out)


def add_zscores(panel: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    """Rolling per-bond z-score, median and percentile of spread_bp (63bd ~ 3 months)."""
    panel = panel.sort_values("date").copy()
    g = panel.groupby("instrument_id")["spread_bp"]
    mp = min(window, 20)       # >= 20 observations, but never more than the window (pandas raises otherwise)
    m = g.transform(lambda s: s.rolling(window, min_periods=mp).mean())
    sd = g.transform(lambda s: s.rolling(window, min_periods=mp).std())
    panel["z_3m"] = (panel["spread_bp"] - m) / sd
    panel["median_3m"] = g.transform(lambda s: s.rolling(window, min_periods=mp).median())
    panel["pctile_3m"] = g.transform(lambda s: s.rolling(window, min_periods=mp).rank(pct=True))
    return panel


# ---------------------------------------------------------------- CLI
def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


MIN_BONDS = 12   # 6-parameter NSS: fewer bonds and the fit is near-exact, so residuals are meaningless


def run(static_path, quotes_path, issuer, min_ttm=1.0, exclude=(), robust=False, loo=False, window=63, snap=None,
        min_bonds=MIN_BONDS):
    st, q = _read(static_path), _read(quotes_path)
    st = st[(st["issuer"] == issuer) & (st["bond_type"] == "nominal")]
    st = st.sort_values("valid_from").groupby("instrument_id").tail(1)   # ponytail: latest static row
    if snap is not None:
        q = q[q["snap"] == snap]
    q = q.merge(st[["instrument_id", "coupon_pct", "coupon_freq", "maturity_date", "issue_date"]], on="instrument_id")
    if "dirty_px" not in q or q["dirty_px"].isna().any():
        q["dirty_px"] = q["dirty_px"].fillna(q["clean_px"] + q["accrued_px"]) if "dirty_px" in q else \
            q["clean_px"] + q["accrued_px"]
    q = q.dropna(subset=["dirty_px"])
    if q.duplicated(["date", "instrument_id"]).any():
        raise SystemExit("several snaps per date: pass --snap (never mix snaps in one fit)")
    for c in ("date", "maturity_date", "issue_date"):
        q[c] = pd.to_datetime(q[c])
    q = q[(q["issue_date"] <= q["date"]) & ~q["instrument_id"].isin(exclude)]
    q = q[(q["maturity_date"] - q["date"]).dt.days / 365.25 >= min_ttm]
    frames = [rich_cheap_one_date(g, d, robust, loo) for d, g in q.groupby("date") if len(g) >= min_bonds]
    if not frames:
        raise SystemExit(f"need >= {min_bonds} bonds per date after filters")
    return add_zscores(pd.concat(frames), window)


# ---------------------------------------------------------------- selftest
def selftest() -> None:
    # 1) Known answer (Tuckman & Serrat 2022, Ch.3): 1y spot 0%, 2y spot 10% (annual):
    #    5% 2y bond price 91.7769, yield 9.7203%.
    t, cf = np.array([1.0, 2.0]), np.array([5.0, 105.0])
    p = 5 / 1.0 + 105 / 1.1 ** 2
    assert abs(p - 91.7769) < 1e-4, p
    y = yield_from_price(p, t, cf, 1)
    assert abs(y - 9.7203) < 1e-3, y
    assert abs(mod_duration(10.0, np.array([2.0]), np.array([100.0]), 1) - 2 / 1.1) < 1e-5   # 2y zero at 10%: D = 2/1.1

    # 1b) Hand-computed NSS values (independent of the code): z(2) for b=[.04,-.02,.01,0], lam1=2 is exactly 0.03,
    #     because -0.02(1-e^-1) + 0.01(1-2e^-1) = -0.01; Svensson term: z(5) = 0.04 + 0.01(1-2e^-1) for lam2=5.
    assert abs(nss_zero(2.0, [0.04, -0.02, 0.01, 0.0, 2.0, 5.0]) - 0.03) < 1e-12
    assert abs(nss_zero(5.0, [0.04, 0.0, 0.0, 0.01, 2.0, 5.0]) - (0.04 + 0.01 * (1 - 2 / np.e))) < 1e-12
    # 1c) Cash flows: 5% semiannual maturing 2028-11-12 seen on 2026-12-12: 4 flows, accrued 2.5*30/181.
    tt, cc, acc = cashflows("2026-12-12", "2028-11-12", 5.0, 2)
    assert np.allclose(cc, [2.5, 2.5, 2.5, 102.5]) and abs(tt[0] - 151 / 365.25) < 1e-12, (tt, cc)
    assert abs(acc - 2.5 * 30 / 181) < 1e-12, acc
    # 31 Aug maturity keeps month-end coupon dates (31 Aug / 28 Feb), no drift to the 28th
    tt, cc, _ = cashflows("2026-11-12", "2028-08-31", 4.0, 2)
    assert abs(tt[0] - (pd.Timestamp("2027-02-28") - pd.Timestamp("2026-11-12")).days / 365.25) < 1e-12
    assert abs(tt[1] - (pd.Timestamp("2027-08-31") - pd.Timestamp("2026-11-12")).days / 365.25) < 1e-12

    # 2) Flat 4% cont.-comp. curve built WITHOUT the model function -> fit must return 4% everywhere.
    asof = pd.Timestamp("2026-11-12")
    rng = np.random.default_rng(7)
    rows = []
    for k, yrs in enumerate(np.linspace(1.3, 29.7, 24)):
        mat = asof + pd.DateOffset(days=int(yrs * 365.25))
        cpn = float(rng.choice([0.5, 2.0, 4.0, 6.5]))
        tt, cc, _ = cashflows(asof, mat, cpn, 2)
        rows.append(dict(instrument_id=f"B{k}", coupon_pct=cpn, coupon_freq=2, maturity_date=mat,
                         dirty_px=float(np.sum(cc * np.exp(-0.04 * tt)))))
    flat = pd.DataFrame(rows)
    res = rich_cheap_one_date(flat, asof)
    assert res["spread_bp"].abs().max() < 0.05, res["spread_bp"].abs().max()
    bonds = [dict(t=cashflows(asof, r.maturity_date, r.coupon_pct, 2)[0],
                  cf=cashflows(asof, r.maturity_date, r.coupon_pct, 2)[1], dirty=r.dirty_px, freq=2,
                  dur=8.0) for r in flat.itertuples()]
    prm, _ = fit_nss(bonds)
    zz = nss_zero(np.array([2.0, 10.0, 25.0]), prm)
    assert np.allclose(zz, 0.04, atol=1e-5), zz

    # 3) Humped curve, one bond cheapened by exactly +3.0bp in its own yield.
    true = [0.035, -0.01, 0.02, 0.01, 1.8, 9.0]
    rows = []
    for k, yrs in enumerate(np.linspace(1.2, 29.5, 26)):
        mat = asof + pd.DateOffset(days=int(yrs * 365.25))
        cpn = float(rng.choice([1.0, 3.0, 5.0]))
        tt, cc, _ = cashflows(asof, mat, cpn, 2)
        px = float(np.sum(cc * nss_df(tt, true)))
        if k == 12:
            px = price_from_yield(yield_from_price(px, tt, cc, 2) + 3.0 / 100, tt, cc, 2)
        rows.append(dict(instrument_id=f"B{k}", coupon_pct=cpn, coupon_freq=2, maturity_date=mat, dirty_px=px))
    hump = pd.DataFrame(rows)
    rob = rich_cheap_one_date(hump, asof, robust=True).set_index("instrument_id")["spread_bp"]
    assert abs(rob["B12"] - 3.0) < 0.3 and rob.drop("B12").abs().max() < 0.3, rob.round(2).tolist()
    # weighted residuals are in bp: one planted 3bp bond among 26 -> RMSE = 3/sqrt(26) (checks the 1/(P*D) weights)
    fit_rmse = rich_cheap_one_date(hump, asof, robust=True)["fit_rmse_bp"].iloc[0]
    assert abs(fit_rmse - 3.0 / np.sqrt(26)) < 0.1, fit_rmse
    res = rich_cheap_one_date(hump, asof, robust=True, loo=True).set_index("instrument_id")
    s = res["spread_bp"]
    assert abs(s["B12"] - 3.0) < 0.1, s["B12"]
    # LOO at the curve ends is extrapolation (B0 ~1bp off): test interior bonds only.
    interior = s.drop(["B0", "B12", "B25"])
    assert interior.abs().max() < 0.3, interior.abs().max()
    assert res.loc["B12", "price_gap"] < 0          # cheap bond -> negative price gap (Tuckman sign)

    # 4) z-score plumbing: constant-then-jump series gives a large positive z on the jump.
    d = pd.bdate_range("2026-01-01", periods=70)
    pan = pd.DataFrame(dict(date=d, instrument_id="X", spread_bp=np.r_[rng.normal(0, 0.5, 69), 5.0]))
    assert add_zscores(pan)["z_3m"].iloc[-1] > 4
    assert add_zscores(pan, window=15)["z_3m"].notna().sum() > 0      # short window must not raise
    print("selftest ok")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--static"), ap.add_argument("--quotes"), ap.add_argument("--issuer")
    ap.add_argument("--min-ttm", type=float, default=1.0, help="years; <1y bonds are money-market priced")
    ap.add_argument("--exclude", default="", help="comma-separated instrument_ids (specials, OTRs, tiny float)")
    ap.add_argument("--robust", action="store_true", help="soft-L1 loss so outliers do not pull the curve")
    ap.add_argument("--loo", action="store_true", help="leave-one-out fair value (n+1 fits per date)")
    ap.add_argument("--snap", default=None, help="bond_quotes.snap to use (required if several snaps per date)")
    ap.add_argument("--min-bonds", type=int, default=MIN_BONDS, help="minimum bonds per date's fit (NSS has 6 parameters)")
    ap.add_argument("--window", type=int, default=63, help="z-score lookback in business days")
    ap.add_argument("--out", default="rich_cheap.csv")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.static and a.quotes and a.issuer):
        ap.error("--static, --quotes and --issuer are required")
    out = run(a.static, a.quotes, a.issuer, a.min_ttm, [x for x in a.exclude.split(",") if x], a.robust, a.loo,
              a.window, a.snap, a.min_bonds)
    out.to_csv(a.out, index=False)
    last = out[out["date"] == out["date"].max()].sort_values("spread_bp")
    print(last[["instrument_id", "ttm_years", "spread_bp", "z_3m", "fit_rmse_bp"]].to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
