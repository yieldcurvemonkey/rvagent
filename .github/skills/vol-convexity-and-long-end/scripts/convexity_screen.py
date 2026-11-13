"""Curve-implied (breakeven) vol screen for DV01-neutral forward flatteners.

A DV01-neutral package that receives the later-start forward swap and pays the earlier-start one (a forward
"flattener", curve spread = later minus earlier) is long convexity.  Per unit curve DV01, in bp:

    leg gamma per DV01   = 2 * D * 1e-4            (D = modified annuity duration from today, years)
    convexity P&L / yr   = 1e-4 * dD * sigma^2     (sigma = normal vol, bp/yr; dD = D_long - D_short)
    carry c (bp/yr)      = r_long - r_short        (r_i = d f_i / d start, receiver roll at unchanged spot curve)
    breakeven vol        = sign(v) * sqrt(|v|),  v = -c * 1e4 / dD       (negative sigma_BE = paid to own gamma)
    edge vs option vol   = c + 1e-4 * dD * sigma_imp^2    (bp/yr per unit curve DV01; > 0 = curve is the cheaper gamma)

Usage:
    python convexity_screen.py --curve curve_par.csv --vol vol_surface.csv --date 2026-11-10 --curve-id USD-SOFR [--snap eod_ny --index-id USD-SOFR]
    python convexity_screen.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import math
import re
import sys

import numpy as np
import pandas as pd

TRADING_DAYS = 252.0


def ann_duration(start: float, tenor: float, y_pct: float, freq: int = 2) -> float:
    """Modified duration (years) of the annuity of a forward swap [start, start+tenor] at a flat yield (percent)."""
    v = 1.0 + y_pct / 100.0 / freq
    m = freq * start + np.arange(1, int(round(freq * tenor)) + 1)
    df = v ** (-m)
    return float(np.sum((m / freq) * df / v) / np.sum(df))


def roll_from_strip(starts, f_bp) -> np.ndarray:
    """d f / d start (bp per year) by 3-point (Lagrange) differences on an uneven grid; one-sided at the ends."""
    starts, f_bp = np.asarray(starts, float), np.asarray(f_bp, float)
    if len(starts) < 3:
        raise ValueError("need >= 3 forward starts to estimate the roll")
    return np.gradient(f_bp, starts, edge_order=2)


def sigma_be(carry_bp_yr: float, d_dur: float) -> float:
    """Breakeven normal vol (bp/yr). Negative = carry is positive, i.e. you are paid to own the gamma."""
    v = -carry_bp_yr * 1e4 / d_dur
    return math.copysign(math.sqrt(abs(v)), v)


def edge_bp_yr(carry_bp_yr: float, d_dur: float, sigma_imp: float) -> float:
    """Expected P&L per year per unit curve DV01 if realised vol = sigma_imp: carry + convexity."""
    return carry_bp_yr + 1e-4 * d_dur * sigma_imp ** 2


def be_over_rv(carry_bp_yr: float, d_dur: float, rlzd_bp_day: float) -> tuple[float, float]:
    """(daily breakeven bp/day, BE/RV). BE = 0 when carry >= 0 (saturated; the ratio is then uninformative)."""
    if not (d_dur > 0 and rlzd_bp_day > 0) or math.isnan(carry_bp_yr):
        return math.nan, math.nan
    be = 0.0 if carry_bp_yr >= 0 else sigma_be(carry_bp_yr, d_dur) / math.sqrt(TRADING_DAYS)
    return be, be / rlzd_bp_day


def convexity_value_bp(d_annuity: float, vol_bp_yr: float, horizon_yr: float = 1.0) -> float:
    """Value of convexity (bp of yield per unit DV01) = 0.5 * (2 D 1e-4) * sigma^2 * T. Doubling vol quadruples it."""
    return 1e-4 * d_annuity * vol_bp_yr ** 2 * horizon_yr


def flat_pair_pnl_bp(start_s: float, start_l: float, tenor: float, y_pct: float, shift_bp: float) -> float:
    """Full-repricing P&L (bp per unit DV01) of the DV01-neutral flattener after an instantaneous parallel shift,
    flat semi-annual curve at y_pct, receivers struck at today's forward rate (= y_pct on a flat curve)."""
    def pv(start, y):
        v = 1.0 + y / 200.0
        m = 2 * start + np.arange(1, int(round(2 * tenor)) + 1)
        return float(np.sum(0.5 * v ** (-m)))          # annuity (per unit fixed rate, decimal)

    k = y_pct / 100.0
    y1 = y_pct + shift_bp / 100.0
    val = lambda s: (k - y1 / 100.0) * pv(s, y1)        # receiver value per unit notional (decimal)
    hedge = pv(start_l, y_pct) / pv(start_s, y_pct)     # short-leg notional so annuity (= DV01 / 1e-4) matches
    pnl = val(start_l) - hedge * val(start_s)
    return pnl / (pv(start_l, y_pct) * 1e-4)            # per unit DV01 of the long leg -> bp


def mbs_hedge_need(duration: float, notional_bn: float, convexity: float, move_bp: float) -> float:
    """Change in hedger 10y-equivalents ($bn) for a rate move: old - new. Negative = sell duration (sell-off).
    convexity in duration-years per 100bp (MBS convention: -2 means duration +0.5 for +25bp)."""
    new_dur = duration + move_bp / 100.0 * (-convexity)
    return duration * notional_bn / 10.0 - new_dur * notional_bn / 10.0


def pair_table(starts, tenor: float, f_pct, sigma_imp: float | None = None, min_dd: float = 4.0) -> pd.DataFrame:
    """All same-tenor forward pairs (short start < long start) with D, dD, carry, sigma_BE and optional edge."""
    starts, f_pct = np.asarray(starts, float), np.asarray(f_pct, float)
    r = roll_from_strip(starts, f_pct * 100.0)
    d = np.array([ann_duration(s, tenor, y) for s, y in zip(starts, f_pct)])
    rows = []
    for i, j in itertools.combinations(range(len(starts)), 2):
        dd, c = d[j] - d[i], r[j] - r[i]
        row = dict(short_start=starts[i], long_start=starts[j], tenor=tenor,
                   curve_bp=100 * (f_pct[j] - f_pct[i]), d_short=d[i], d_long=d[j], d_dur=dd, carry_bp_yr=c,
                   sigma_be=sigma_be(c, dd) if dd > 0 else np.nan, gate_dd=bool(dd >= min_dd))
        if sigma_imp is not None:
            row["sigma_imp"], row["edge_bp_yr"] = sigma_imp, edge_bp_yr(c, dd, sigma_imp)
        rows.append(row)
    return pd.DataFrame(rows)


def _tenor_years(s: str) -> float | None:
    m = re.fullmatch(r"(\d+)([YM])", str(s).strip().upper())
    if m:
        return int(m.group(1)) * (1.0 if m.group(2) == "Y" else 1 / 12)
    return 0.0 if str(s).strip().upper() == "0D" else None


def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


def run(curve: pd.DataFrame, vol: pd.DataFrame | None, date: str, curve_id: str, tenor: str, expiry: str,
        vol_tail: str, min_dd: float, snap: str | None = None, index_id: str | None = None) -> pd.DataFrame:
    c = curve[(curve["date"].astype(str).str[:10] == date) & (curve["curve_id"] == curve_id)
              & (curve["tenor"] == tenor)].copy()
    if snap and "snap" in c:
        c = c[c["snap"] == snap]
    c["s"] = c["start"].map(_tenor_years)
    c = c.dropna(subset=["s", "par_rate_pct"])
    if c["s"].duplicated().any():
        raise SystemExit("duplicate forward starts in curve_par for this date/curve/tenor: pass --snap to pick one snap")
    c = c.sort_values("s")
    if len(c) < 3:
        raise SystemExit(f"need >= 3 forward-start rows for {curve_id} tenor {tenor} on {date} in curve_par "
                         f"(got {len(c)}); build the forward grid first (see curve-forward-grid-rv)")
    sig = None
    if vol is not None:
        v = vol[(vol["date"].astype(str).str[:10] == date) & (vol["product"] == "swaption")
                & (vol["expiry"] == expiry) & (vol["tenor"] == vol_tail) & (vol["strike_offset_bp"] == 0)]
        if "fwd_start" in v:
            v = v[v["fwd_start"] == "0D"]                      # spot-starting swaptions only (not midcurves)
        if snap and "snap" in v:
            v = v[v["snap"] == snap]
        if index_id and "index_id" in v:
            v = v[v["index_id"] == index_id]
        v = v.dropna(subset=["nvol_bp"])
        if len(v) > 1:
            raise SystemExit("several vol_surface rows match (snap / index_id): pass --snap and --index-id")
        if len(v):
            sig = float(v["nvol_bp"].iloc[0])
    return pair_table(c["s"].values, _tenor_years(tenor), c["par_rate_pct"].values, sig, min_dd)


# --------------------------------------------------------------------------------------------- self-test
def _holee_par(starts, tenor, sigma_bp, r0_pct=4.0):
    s = sigma_bp * 1e-4
    P = lambda T: np.exp(-r0_pct / 100 * T + s * s * T ** 3 / 6)    # Ho-Lee, flat expected short rate: f = r0 - s^2 T^2/2
    out = []
    for h in starts:
        legs = h + 0.5 * np.arange(1, int(2 * tenor) + 1)
        out.append(100 * (P(h) - P(h + tenor)) / np.sum(0.5 * P(legs)))
    return np.array(out)


def selftest() -> int:
    ok = True

    def chk(name, cond, info=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info else ""))
        ok &= bool(cond)

    # 1. annuity duration at ~0% yield: mean of m/2 over m = 21..40  ->  15.25 (10y10y) and 25.25 (20y10y)
    d1, d2 = ann_duration(10, 10, 1e-9), ann_duration(20, 10, 1e-9)
    chk("annuity duration at 0% (15.25, 25.25, dD 10)", abs(d1 - 15.25) < 1e-6 and abs(d2 - d1 - 10) < 1e-6, f"{d1:.4f} {d2:.4f}")
    # 1b. modified (not Macaulay) duration: matches -dA/dy / A by finite difference of the annuity PV at 4%
    A = lambda s, t_, y: sum(0.5 * (1 + y / 2) ** -(2 * s + k) for k in range(1, int(2 * t_) + 1))
    fd = -(A(10, 10, 0.0401) - A(10, 10, 0.0399)) / 0.0002 / A(10, 10, 0.04)
    chk("ann_duration = -dA/dy/A (modified) at 4%", abs(ann_duration(10, 10, 4.0) / fd - 1) < 1e-4, f"{ann_duration(10, 10, 4.0):.4f} vs {fd:.4f}")
    # 2. 3-point roll is exact on a quadratic, uneven grid; zero on a flat strip
    x = np.array([10, 15, 20, 25, 30.0])
    chk("roll exact on quadratic", np.allclose(roll_from_strip(x, 3 + 0.5 * x - 0.01 * x ** 2), 0.5 - 0.02 * x))
    chk("roll zero on flat strip", np.allclose(roll_from_strip(x, np.full(5, 2.0)), 0))
    # 3. published anchors: carry -8.38bp/yr, dD 9.9 -> sigma_BE ~92; Citi-style BE/RV (c=-1.75, dD 9.9 -> ~2.6bp/day)
    chk("sigma_be anchor 92", abs(sigma_be(-8.38, 9.9) - 92) < 0.5, f"{sigma_be(-8.38, 9.9):.2f}")
    chk("sigma_be sign (+carry -> negative)", sigma_be(+1.0, 9.9) < 0)
    be, ratio = be_over_rv(-1.75, 9.9, 3.1)
    chk("daily BE anchor 2.6bp, BE/RV 0.84", abs(be - 2.65) < 0.1 and abs(ratio - 0.84) < 0.04, f"{be:.2f} {ratio:.2f}")
    chk("BE = 0 when carry >= 0", be_over_rv(0.3, 9.9, 3.0)[0] == 0.0)
    # 4. edge is zero at sigma_imp = sigma_BE
    chk("edge zero at breakeven", abs(edge_bp_yr(-8.38, 9.9, sigma_be(-8.38, 9.9))) < 1e-9)
    # 5. value of convexity: 10y swap D~5.5, 50bp vol -> ~1.4bp (QF SE gamma table); doubling vol quadruples it
    chk("convexity value 1.375", abs(convexity_value_bp(5.5, 50) - 1.375) < 1e-9
        and abs(convexity_value_bp(5.5, 100) / convexity_value_bp(5.5, 50) - 4) < 1e-12)
    # 6. full repricing on a flat curve: positive both ways and ~ 1e-4 * dD * s^2 for a small shift
    dd = ann_duration(20, 10, 4.0) - ann_duration(10, 10, 4.0)
    up, dn = flat_pair_pnl_bp(10, 20, 10, 4.0, 20), flat_pair_pnl_bp(10, 20, 10, 4.0, -20)
    chk("flattener convex both ways", up > 0 and dn > 0, f"{up:.4f} {dn:.4f}")
    chk("repricing matches 1e-4*dD*s^2 (5%)", abs(0.5 * (up + dn) / (1e-4 * dd * 400) - 1) < 0.05,
        f"{0.5 * (up + dn):.4f} vs {1e-4 * dd * 400:.4f}")
    # 7. non-circular: Ho-Lee curve built from discount factors, run the real pipeline, recover sigma within 5%
    starts, sig = [10, 15, 20, 25, 30], 90.0
    t = pair_table(starts, 5, _holee_par(starts, 5, sig), min_dd=4.0)
    sel = t[(t.short_start == 10) & (t.long_start == 25)].iloc[0]
    chk("Ho-Lee sigma_BE within 5% of true 90", abs(sel.sigma_be / sig - 1) < 0.05, f"{sel.sigma_be:.1f}")
    # 8. BofA hedge-need example: dur 7, $100bn, convexity -2, +25/+100bp -> -5 / -20 ($bn 10y-eq, sell)
    chk("MBS hedge need -5 / -20", abs(mbs_hedge_need(7, 100, -2, 25) + 5) < 1e-9 and abs(mbs_hedge_need(7, 100, -2, 100) + 20) < 1e-9)
    # 9. degenerate inputs return NaN instead of raising; NaN in the strip is dropped before the roll
    chk("be_over_rv zero-vol / zero-dD guards", all(math.isnan(x) for x in be_over_rv(-1.0, 9.9, 0.0) + be_over_rv(-1.0, 0.0, 3.0)))
    cur = pd.DataFrame({"date": "2026-11-10", "curve_id": "X", "tenor": "5Y", "snap": "eod_ny",
                        "start": ["10Y", "15Y", "20Y", "25Y"], "par_rate_pct": [4.0, np.nan, 3.8, 3.7]})
    try:
        tt = run(cur, None, "2026-11-10", "X", "5Y", "1Y", "30Y", 4.0)
        chk("NaN strip row dropped (3 starts -> 3 pairs, no NaN carry)", len(tt) == 3 and tt["carry_bp_yr"].notna().all())
    except SystemExit as e:
        chk("NaN strip row dropped", False, str(e))
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--curve", help="curve_par table (csv/parquet) with forward-start rows")
    ap.add_argument("--vol", help="optional vol_surface table (csv/parquet)")
    ap.add_argument("--date", help="YYYY-MM-DD")
    ap.add_argument("--curve-id", default="USD-SOFR")
    ap.add_argument("--tenor", default="5Y", help="swap tenor of the forward strip (same-tenor pairs)")
    ap.add_argument("--expiry", default="1Y", help="swaption expiry for sigma_imp")
    ap.add_argument("--vol-tail", default="30Y", help="swaption tail for sigma_imp (30Y = matched tail)")
    ap.add_argument("--min-dd", type=float, default=4.0, help="gate: dD below this makes sigma_BE explode")
    ap.add_argument("--snap", help="snap to use in both tables (e.g. eod_ny); required if a date has several snaps")
    ap.add_argument("--index-id", help="vol_surface index_id of the curve (e.g. the curve's index), if several")
    ap.add_argument("--out", help="write csv")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not (a.curve and a.date):
        ap.error("--curve and --date are required (or use --selftest)")
    t = run(_read(a.curve), _read(a.vol) if a.vol else None, a.date, a.curve_id, a.tenor, a.expiry, a.vol_tail, a.min_dd, a.snap, a.index_id)
    print(t.round(2).to_string(index=False))
    if a.out:
        t.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
