"""Forward-grid RV: forward strip from par or zero curves, forward-vs-spot grid, kink residuals, roll, frontier.

Conventions (match SKILL.md):
  * AyBy = swap of tenor B years starting in A years. xF1Y = AyBy with B = 1 ("1y rate x years forward").
  * Annual fixed-leg approximation: DF_N = (1 - s_N * sum_{i<N} DF_i) / (1 + s_N); forward par rate
    R(A,B) = (DF(A) - DF(A+B)) / sum_{i=1..B} DF(A+i). For B = 1 this is DF(A)/DF(A+1) - 1.
    Good to ~1bp for screening; for trade levels use the full-convention curve (fi-curve-construction).
  * DF between annual nodes: log-linear (constant overnight forward inside each year).
  * Rates in percent; spreads, residuals and rolls in bp.
  * fwd_minus_spot_bp = R(A,B) - R(0,B): the change in the B-year rate the forwards imply over A years.
  * roll_bp (receiver, curve unchanged, horizon h years) = R(A,B) - R(A-h,B). Positive = a receiver earns.
  * resid_bp = forward - cross-sectional cubic LSQ spline fit. Positive = forward high = cheap to receive.
  * off_frontier_bp = resid - (a + b * roll3m) from the daily cross-sectional OLS over starts 2..15.
    Positive = cheaper than its carry implies (receive candidate).
  * Forward-curve pair "S/L" (e.g. 10y10y/20y10y): level_bp = R(L) - R(S) (later minus earlier; negative =
    inverted). Flattener = receive L, pay S, DV01-neutral. carry_bp_yr = 1y unchanged-curve P&L of the flattener
    per bp of DV01 = roll(L) - roll(S). gamma_dur(A,B) = A+(B+1)/2 (mean payment year): gamma per unit PV01 is 2*gamma_dur*1e-4 per bp
    (rule of thumb; matches 10Y 1.1, 10Y10Y 3.1, 20Y10Y 5.1 per 1000 PV01; flat-curve bump-and-reprice gives (2A+B)*1e-4,
    the +1 cancels in d_gamma_dur). Pairs with d_gamma_dur < 4 or sigma_be > 300 get sigma_be = NaN (small d_gamma_dur explodes it).
    sigma_be_bp_yr = sqrt(max(-carry, 0) / (1e-4 * d_gamma_dur)): normal vol (bp/yr) at which the convexity gain of
    the DV01-neutral pair equals its carry cost (0 when carry >= 0). be_over_rv = (sigma_be/sqrt(252)) / 1y
    realised daily vol (bp/day) of the later leg.

CLI (canonical tables, see data-contract-and-adapters):
  python forward_grid.py --input curve_par.parquet --curve-id EUR-ESTR --out fg_eur
  python forward_grid.py --input curve_zero.csv --table curve_zero --curve-id USD-SOFR --out fg_usd
  python forward_grid.py --selftest
Outputs <out>_strip.csv (date, start, fwd_pct, fit_pct, resid_bp, roll3m_bp, off_frontier_bp, resid_z,
months_to_be), <out>_grid.csv (date, structure, fwd_pct, spot_pct, fwd_minus_spot_bp, roll3m_bp, z) and
<out>_pairs.csv (date, pair, level_bp, carry_bp_yr, d_gamma_dur, sigma_be_bp_yr, level_z, rv_bp_day, be_over_rv).
"""
from __future__ import annotations

import argparse
import re
import sys

import numpy as np
import pandas as pd
from scipy.interpolate import make_lsq_spline

GRID = [(1, 1), (2, 1), (1, 2), (2, 2), (2, 3), (3, 2), (5, 5), (10, 5), (15, 5), (10, 10), (20, 10), (10, 20)]
KNOTS = (3.0, 7.0, 15.0)  # interior knots in forward-start years; dense front, sparse back
PAIRS = [((10, 10), (20, 10)), ((15, 5), (20, 10)), ((10, 10), (25, 10)), ((15, 10), (25, 10)), ((20, 5), (25, 5)),
         ((5, 5), (10, 5)), ((10, 5), (15, 5)), ((5, 5), (10, 10))]  # ((start, tenor) of S, (start, tenor) of L)
MIN_DGD, MAX_SIGMA_BE = 4.0, 300.0  # sigma_BE filters from the straddle-package spec
Z_WIN, Z_MIN = 756, 252  # 3y trailing window for z-scores, 1y minimum, current day excluded


def tenor_years(t: str) -> float:
    m = re.fullmatch(r"(\d+)([DWMY])", str(t).strip().upper())
    if not m:
        raise ValueError(f"bad tenor {t!r}")
    return int(m.group(1)) / {"D": 365.0, "W": 52.0, "M": 12.0, "Y": 1.0}[m.group(2)]


def bootstrap_annual(par_pct: pd.Series) -> np.ndarray:
    """par_pct indexed by integer years (gaps linearly interpolated in par space). Returns DF[0..N], DF[0]=1."""
    s = par_pct.sort_index()
    n = int(s.index.max())
    s = s.reindex(range(1, n + 1)).interpolate(limit_area="inside").bfill() / 100.0
    df = np.ones(n + 1)
    for i in range(1, n + 1):
        df[i] = (1.0 - s[i] * df[1:i].sum()) / (1.0 + s[i])
    return df


def df_at(df_annual: np.ndarray, t) -> np.ndarray:
    """Log-linear DF interpolation on the annual grid (t in years, 0 <= t <= N)."""
    return np.exp(np.interp(t, np.arange(len(df_annual)), np.log(df_annual)))


def fwd_par(df_annual: np.ndarray, a: float, b: int) -> float:
    """Annual-pay par rate (%) of the swap starting in a years with tenor b years."""
    if a < 0 or a + b > len(df_annual) - 1 + 1e-9:
        return np.nan
    pay = a + np.arange(1, b + 1)
    return 100.0 * (df_at(df_annual, a) - df_at(df_annual, a + b)) / df_at(df_annual, pay).sum()


def receiver_roll_bp(df_annual: np.ndarray, a: float, b: int, h: float = 0.25) -> float:
    """Unchanged-curve roll of a receiver in AyBy over h years: R(A,B) - R(A-h,B), bp. Forward starts only."""
    if a < h:
        return np.nan  # spot-start or inside horizon: carry + roll, see fi-carry-and-rolldown
    return 100.0 * (fwd_par(df_annual, a, b) - fwd_par(df_annual, a - h, b))


def gamma_dur(a: float, b: float) -> float:
    """Gamma 'duration' of AyBy = mean payment year A+(B+1)/2; gamma per unit PV01 = 2*gamma_dur*1e-4 per bp."""
    return (2.0 * a + b + 1.0) / 2.0


def convexity_value_bp(vol_bp_yr: float, d_gamma_dur: float, tau: float = 1.0) -> float:
    """Expected convexity gain (bp of PV01) of a DV01-neutral pair over tau years: 0.5*(2*dGD*1e-4)*vol^2*tau."""
    return 1e-4 * d_gamma_dur * vol_bp_yr ** 2 * tau


def breakeven_vol_bp(carry_bp_yr: float, d_gamma_dur: float) -> float:
    """Normal vol (bp/yr) at which convexity gain offsets carry cost; 0 if carry >= 0 (free convexity)."""
    if not d_gamma_dur > 0:
        return np.nan
    return float(np.sqrt(max(-carry_bp_yr, 0.0) / (1e-4 * d_gamma_dur)))


def pair_one_date(df_annual: np.ndarray, pairs=PAIRS, h: float = 1.0) -> pd.DataFrame:
    """Forward-curve pairs S/L as DV01-neutral flatteners (receive L, pay S). Leg tenors must be integer years."""
    rows = []
    for (sa, sb), (la, lb) in pairs:
        if min(sa, la) < h or max(sa + sb, la + lb) > len(df_annual) - 1:
            continue
        r_s, r_l = fwd_par(df_annual, sa, sb), fwd_par(df_annual, la, lb)
        carry = receiver_roll_bp(df_annual, la, lb, h) - receiver_roll_bp(df_annual, sa, sb, h)
        dgd = gamma_dur(la, lb) - gamma_dur(sa, sb)
        sig = breakeven_vol_bp(carry / h, dgd) if dgd >= MIN_DGD else np.nan
        if sig > MAX_SIGMA_BE:
            sig = np.nan
        rows.append({"pair": f"{sa}y{sb}y/{la}y{lb}y", "level_bp": 100.0 * (r_l - r_s), "long_leg_pct": r_l,
                     "carry_bp_yr": carry / h, "d_gamma_dur": dgd, "sigma_be_bp_yr": sig})
    return pd.DataFrame(rows, columns=["pair", "level_bp", "long_leg_pct", "carry_bp_yr", "d_gamma_dur", "sigma_be_bp_yr"])


def spline_residual_bp(x: np.ndarray, y_pct: np.ndarray, knots=KNOTS) -> np.ndarray:
    """Cross-sectional cubic least-squares spline through the strip; residual = market - fit (bp)."""
    x, y = np.asarray(x, float), np.asarray(y_pct, float)
    ok = np.isfinite(y)
    if ok.sum() < 8:
        return np.full_like(y, np.nan)
    xs, ys = x[ok], y[ok]
    inner = [k for k in knots if xs.min() < k < xs.max()]
    t = np.r_[[xs.min()] * 4, inner, [xs.max()] * 4]
    try:
        spl = make_lsq_spline(xs, ys, t, k=3)
    except (ValueError, np.linalg.LinAlgError):  # Schoenberg-Whitney fails: too few points between knots
        return np.full_like(y, np.nan)
    out = np.full_like(y, np.nan)
    out[ok] = 100.0 * (ys - spl(xs))
    return out


def frontier_fit(roll3m: np.ndarray, resid_bp: np.ndarray) -> tuple[float, float]:
    """OLS of residual (y) on 3m receiver roll (x): returns (intercept a, slope b). Negative slope = value costs carry."""
    b, a = np.polyfit(roll3m, resid_bp, 1)
    return a, b


def strip_one_date(df_annual: np.ndarray, starts=None) -> pd.DataFrame:
    n = len(df_annual) - 1
    starts = [s for s in (starts or list(range(1, 16)) + [20, 25, 30]) if s + 1 <= n]
    fwd = np.array([fwd_par(df_annual, s, 1) for s in starts])
    out = pd.DataFrame({"start": starts, "fwd_pct": fwd})
    out["resid_bp"] = spline_residual_bp(out["start"].to_numpy() + 0.5, fwd)
    out["fit_pct"] = out["fwd_pct"] - out["resid_bp"] / 100.0
    out["roll3m_bp"] = [receiver_roll_bp(df_annual, s, 1, 0.25) for s in starts]
    core = out[(out.start >= 2) & (out.start <= 15)].dropna(subset=["resid_bp", "roll3m_bp"])
    if len(core) >= 4:
        a, b = frontier_fit(core.roll3m_bp, core.resid_bp)
        out["off_frontier_bp"] = out.resid_bp - (a + b * out.roll3m_bp)
    else:
        out["off_frontier_bp"] = np.nan
    # months for adverse carry to erase the residual (trade direction = fade the residual)
    carry_m = np.where(out.resid_bp > 0, out.roll3m_bp, -out.roll3m_bp) / 3.0
    out["months_to_be"] = np.where(carry_m < 0, out.resid_bp.abs() / np.maximum(-carry_m, 1e-9), np.inf)
    return out


def grid_one_date(df_annual: np.ndarray, grid=GRID) -> pd.DataFrame:
    rows = []
    for a, b in grid:
        f, s = fwd_par(df_annual, a, b), fwd_par(df_annual, 0, b)
        rows.append({"structure": f"{a}y{b}y", "fwd_pct": f, "spot_pct": s,
                     "fwd_minus_spot_bp": 100.0 * (f - s), "roll3m_bp": receiver_roll_bp(df_annual, a, b)})
    return pd.DataFrame(rows)


def trailing_z(s: pd.Series, win: int = Z_WIN, min_obs: int = Z_MIN) -> pd.Series:
    """Backward-looking z: today's value vs mean/std of the prior window (today excluded)."""
    r = s.shift(1).rolling(win, min_periods=min_obs)
    return (s - r.mean()) / r.std()


def annual_dfs_from_table(g: pd.DataFrame, table: str) -> np.ndarray:
    if table == "curve_par":
        g = g[g["start"].astype(str).str.upper().isin(["0D", "0Y"])]
        yrs = g["tenor"].map(tenor_years)
        g = g[(yrs >= 1) & (np.isclose(yrs, yrs.round()))]
        s = pd.Series(g["par_rate_pct"].to_numpy(), index=yrs[g.index].round().astype(int)).groupby(level=0).last()
        if len(s) < 6:
            raise ValueError("need >= 6 integer-year par tenors")
        return bootstrap_annual(s)
    tau = (pd.to_datetime(g["node_date"]) - pd.to_datetime(g["date"])).dt.days.to_numpy() / 365.25
    ok = tau > 0
    tau, lndf = np.r_[0.0, tau[ok]], np.r_[0.0, np.log(g["discount_factor"].to_numpy()[ok])]
    order = np.argsort(tau)
    n = int(np.floor(tau.max()))
    return np.exp(np.interp(np.arange(n + 1), tau[order], lndf[order]))


def run(panel: pd.DataFrame, table: str):
    for c in ("curve_id", "snap"):  # one curve and one snap per run: mixing them silently blends different curves
        if c in panel and panel[c].nunique() > 1:
            raise ValueError(f"panel has several {c} values {sorted(panel[c].unique())[:5]}; filter first")
    strips, grids, pairs = [], [], []
    for d, g in panel.groupby("date"):
        try:
            dfa = annual_dfs_from_table(g, table)
        except ValueError as e:
            print(f"skip {d}: {e}", file=sys.stderr)
            continue
        strips.append(strip_one_date(dfa).assign(date=d))
        grids.append(grid_one_date(dfa).assign(date=d))
        pairs.append(pair_one_date(dfa).assign(date=d))
    if not strips:
        raise ValueError("no date had a usable curve (need >= 6 integer-year par tenors or zero nodes)")
    strip, grid = pd.concat(strips, ignore_index=True), pd.concat(grids, ignore_index=True)
    strip = strip.sort_values(["start", "date"])
    strip["resid_z"] = strip.groupby("start")["resid_bp"].transform(trailing_z)
    grid = grid.sort_values(["structure", "date"])
    grid["z"] = grid.groupby("structure")["fwd_minus_spot_bp"].transform(trailing_z)
    pr = pd.concat(pairs, ignore_index=True).sort_values(["pair", "date"])
    pr["level_z"] = pr.groupby("pair")["level_bp"].transform(trailing_z)
    pr["rv_bp_day"] = pr.groupby("pair")["long_leg_pct"].transform(lambda x: 100 * x.diff().rolling(252, min_periods=126).std())
    pr["be_over_rv"] = pr.sigma_be_bp_yr / np.sqrt(252) / pr.rv_bp_day
    return strip, grid, pr.drop(columns="long_leg_pct")


def selftest() -> int:
    fails = []

    def check(name, got, want, tol):
        if not np.all(np.abs(np.asarray(got, float) - np.asarray(want, float)) <= tol):
            fails.append(f"{name}: got {np.round(got, 4)}, want {want}")

    # 1. Flat 3% annual par curve: every forward 3%, fwd - spot 0, roll 0, residual 0.
    flat = bootstrap_annual(pd.Series(3.0, index=range(1, 41)))
    check("flat DF10", flat[10], 1.03 ** -10, 1e-12)
    g = grid_one_date(flat)
    check("flat fwd", g.fwd_pct, 3.0, 1e-9)
    check("flat fwd-spot", g.fwd_minus_spot_bp, 0.0, 1e-7)
    check("flat roll", g.roll3m_bp.dropna(), 0.0, 1e-7)
    check("flat resid", strip_one_date(flat).resid_bp, 0.0, 1e-7)
    # 2. Ilmanen (Salomon, UYC Part 1, 1995) Fig 9: par 6/8/9.5/10.5/11 -> 1y forwards 6.00/10.20/13.07/14.36/13.77.
    il = bootstrap_annual(pd.Series([6.0, 8.0, 9.5, 10.5, 11.0, 11.25, 11.38, 11.44, 11.48, 11.5], index=range(1, 11)))
    check("Ilmanen 1y fwds", [fwd_par(il, a, 1) for a in range(5)], [6.00, 10.20, 13.07, 14.36, 13.77], 0.006)
    check("Ilmanen 2y spot", 100 * ((1 / il[2]) ** 0.5 - 1), 8.08, 0.006)
    # 3. Duering (2021, Ch.19) USD swaps 5 Jun 2020: par 0.307/0.299/0.346 -> fwd 0.291 (1y1y), 0.441 (2y1y).
    du = bootstrap_annual(pd.Series([0.307, 0.299, 0.346], index=[1, 2, 3]))
    check("Duering DF1", du[1], 0.996939, 2e-6)
    check("Duering fwds", [fwd_par(du, 1, 1), fwd_par(du, 2, 1)], [0.291, 0.441], 0.0015)
    # 4. Annuity identity R(0,10)A(0,10) = R(0,5)A(0,5) + R(5,5)A(5,5) on the Ilmanen curve.
    ann = lambda a, b: il[a + 1:a + b + 1].sum()
    check("annuity identity", fwd_par(il, 0, 10) * ann(0, 10),
          fwd_par(il, 0, 5) * ann(0, 5) + fwd_par(il, 5, 5) * ann(5, 5), 1e-9)
    # 5. Linear-in-start 1y forward curve 2% + 0.1%/yr: receiver 3m roll of xF1Y = +2.5bp, cubic fit exact.
    f = 0.02 + 0.001 * np.arange(31)
    lin = np.r_[1.0, np.cumprod(1.0 / (1.0 + f))]
    s = strip_one_date(lin)
    check("linear roll3m", s.roll3m_bp, 2.5, 0.02)
    check("linear resid", s.resid_bp, 0.0, 1e-6)
    # 6. +10bp kink at 6F1Y on that curve: largest residual at start 6, positive, and most of the 10bp.
    f2 = f.copy(); f2[6] += 0.001
    k = strip_one_date(np.r_[1.0, np.cumprod(1.0 / (1.0 + f2))])
    top = k.loc[k.resid_bp.idxmax()]
    check("kink location", top.start, 6, 0)
    if not 5.0 < top.resid_bp <= 10.0:
        fails.append(f"kink size {top.resid_bp:.2f} not in (5, 10]")
    # 7. Trailing z excludes today: N(0,1) noise then a 6-sigma print, 30d window. Excluding today z ~ 6; including
    #    it the print inflates its own std and z falls to ~4, so the threshold 5 catches look-ahead leakage.
    x = np.r_[np.random.default_rng(0).normal(0, 1, 300), 6.0]
    z = trailing_z(pd.Series(x), 30, 30)
    if not z.iloc[-1] > 5:
        fails.append(f"trailing z {z.iloc[-1]:.2f} should exceed 5 (today must be excluded from its own window)")
    # 8. Gamma and convexity value vs QF StackExchange "ultra long-end invert" (2019): per 1000 PV01 gamma 1.1/3.1/5.1/
    #    7.1/9.1 for 10Y, 10Y10Y, 20Y10Y, 30Y10Y, 40Y10Y; 50bp/yr vol, 1y -> 1.4/3.9/6.4/8.9/11.4bp.
    qf = [(0, 10), (10, 10), (20, 10), (30, 10), (40, 10)]
    check("QF gamma", [2e3 * 1e-4 * gamma_dur(a, b) for a, b in qf], [1.1, 3.1, 5.1, 7.1, 9.1], 1e-9)
    check("QF value", [convexity_value_bp(50, gamma_dur(a, b)) for a, b in qf], [1.4, 3.9, 6.4, 8.9, 11.4], 0.06)
    # 9. Breakeven vol vs Citi spec: 10y10y/20y10y curve cost ~8.4bp/yr, dGD ~9.9 -> sigma_BE ~92 (spec: 92).
    check("sigma_BE", breakeven_vol_bp(-8.4, 9.9), 92.1, 0.2)
    check("BE roundtrip", convexity_value_bp(breakeven_vol_bp(-5.0, 10.0), 10.0), 5.0, 1e-9)
    if breakeven_vol_bp(+1.0, 10.0) != 0.0:
        fails.append("positive carry must give sigma_BE 0")
    # 9b. Citi (Trading long-dated convexity, 9 May 2019) screen: carry -> daily breakeven bp: 15y5y/20y10y -0.31 -> 1.3,
    #     10y10y/20y10y -1.75 -> 2.6, 10y10y/25y10y -1.83 -> 2.2, 10y5y/15y15y -2.91 -> 3.5 (as printed, 1dp).
    cit = [((15, 5), (20, 10), -0.31, 1.3), ((10, 10), (20, 10), -1.75, 2.6), ((10, 10), (25, 10), -1.83, 2.2),
           ((10, 5), (15, 15), -2.91, 3.5)]
    check("Citi daily BE", [breakeven_vol_bp(c, gamma_dur(*L) - gamma_dur(*S)) / np.sqrt(252) for S, L, c, _ in cit],
          [w for *_, w in cit], 0.11)
    # 10. Pairs: flat curve -> level 0, carry 0. Concave 1y-forward strip peaking at 12y: 10y/20y level = f20 - f10
    #     (-60bp) and flattener carry = (f20 - f19) - (f10 - f9) = -20bp/yr.
    pf = pair_one_date(flat)
    check("flat pair level", pf.level_bp, 0.0, 1e-7)
    check("flat pair carry", pf.carry_bp_yr, 0.0, 1e-7)
    fc = 0.04 - 0.0001 * (np.arange(41) - 12.0) ** 2
    cv = np.r_[1.0, np.cumprod(1.0 / (1.0 + fc))]
    pc = pair_one_date(cv, [((10, 1), (20, 1))])
    want = 1e4 * (fc[20] - fc[10])
    check("concave level", pc.level_bp, want, 0.05)
    check("concave carry", pc.carry_bp_yr, 1e4 * ((fc[20] - fc[19]) - (fc[10] - fc[9])), 0.05)
    if not pc.carry_bp_yr.iloc[0] < -1.0:
        fails.append(f"concave strip flattener should carry negatively, got {pc.carry_bp_yr.iloc[0]:.2f}")
    check("concave dGD", pc.d_gamma_dur, 10.0, 1e-12)  # (2*20+1+1)/2 - (2*10+1+1)/2
    check("concave sigma_BE", pc.sigma_be_bp_yr, np.sqrt(20.0 / (1e-4 * 10.0)), 0.5)  # carry -20bp/yr
    if not np.isnan(pair_one_date(flat, [((10, 10), (11, 10))]).sigma_be_bp_yr.iloc[0]):
        fails.append("dGD < 4 must give sigma_BE NaN")
    # 11. Frontier recovers the planted ING-style line resid = -1.2716*roll + 16.425 (y on x, not x on y).
    x_ = np.linspace(-5, 15, 14)
    a_, b_ = frontier_fit(x_, -1.2716 * x_ + 16.425)
    check("frontier slope", b_, -1.2716, 1e-9)
    check("frontier intercept", a_, 16.425, 1e-9)
    # 12. months_to_be on the linear curve with a +10bp kink at 6F1Y: 5F1Y is rich (resid -2.09bp) and is paid, so the +2.5bp/3m
    #     receiver roll costs the payer 2.5/3 bp a month -> 2.51 months; 6F1Y is cheap (resid +8bp), received, earns roll -> inf.
    kd = strip_one_date(np.r_[1.0, np.cumprod(1.0 / (1.0 + np.r_[f[:6], f[6] + 0.001, f[7:]]))]).set_index("start")
    r5 = kd.loc[5]
    check("months_to_be pay", r5.months_to_be, abs(r5.resid_bp) / (2.5 / 3.0), 0.05)
    core = kd.loc[2:15]
    a5, b5 = frontier_fit(core.roll3m_bp, core.resid_bp)
    check("off_frontier", r5.off_frontier_bp, r5.resid_bp - (a5 + b5 * r5.roll3m_bp), 1e-9)  # positive = cheap for its carry
    if not (r5.resid_bp < 0 and np.isinf(kd.loc[6, "months_to_be"])):
        fails.append("months_to_be direction: rich/paid point finite, cheap/received point with positive roll inf expected")
    for m in fails:
        print("FAIL", m)
    print("selftest", "FAILED" if fails else "passed")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", help="curve_par or curve_zero table (.csv or .parquet)")
    ap.add_argument("--table", choices=["curve_par", "curve_zero"], default="curve_par")
    ap.add_argument("--curve-id")
    ap.add_argument("--snap", help="optional snap filter, e.g. eod_ldn")
    ap.add_argument("--out", default="forward_grid")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.input:
        ap.error("--input required")
    df = pd.read_parquet(a.input) if a.input.endswith(".parquet") else pd.read_csv(a.input)
    if "data_ok" in df:
        df = df[df["data_ok"].astype(str).str.lower() != "false"]
    if a.curve_id:
        df = df[df["curve_id"] == a.curve_id]
    if a.snap:
        df = df[df["snap"] == a.snap]
    try:
        strip, grid, pairs = run(df, a.table)
    except ValueError as e:
        sys.exit(f"error: {e}")
    strip.to_csv(f"{a.out}_strip.csv", index=False)
    grid.to_csv(f"{a.out}_grid.csv", index=False)
    pairs.to_csv(f"{a.out}_pairs.csv", index=False)
    last = strip[strip.date == strip.date.max()]
    print(last[["start", "fwd_pct", "resid_bp", "roll3m_bp", "off_frontier_bp", "resid_z"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
