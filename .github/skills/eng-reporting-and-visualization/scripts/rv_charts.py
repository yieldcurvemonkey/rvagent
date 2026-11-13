#!/usr/bin/env python3
"""Standard RV screen columns and charts (numbers need only numpy/pandas; PNGs need matplotlib).

Units: rates and spreads in bp. Curve spread A-B = y(longer) - y(shorter) (2s10s = 10y - 2y).
Fly a,b,c = 2*y_b - y_a - y_c (2s5s10s; positive = belly high/cheap). Series are indexed by business day.

CLI:  python rv_charts.py --curve-par curve_par.csv --curve-id USD-SOFR --legs 2Y,5Y,10Y --out outdir
      (2 legs = curve spread, 3 = fly; writes screen.csv, z_matrix.csv and PNGs)
      python rv_charts.py --selftest
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile

import numpy as np
import pandas as pd

ACCENT, DATA, GREY = "#d95f02", "#1f77b4", "#9a9a9a"
SPARKS = "▁▂▃▄▅▆▇█"
BD_YEAR = 252


# ---------------------------------------------------------------- structures
def tenor_months(t: str) -> int:
    m = re.fullmatch(r"(\d+)([MY])", t.strip().upper())
    if not m:
        raise ValueError(f"bad tenor {t!r}")
    return int(m[1]) * (12 if m[2] == "Y" else 1)


def spread(y: pd.DataFrame, short: str, long: str) -> pd.Series:
    """Curve spread in bp = long - short."""
    return y[long] - y[short]


def fly(y: pd.DataFrame, a: str, b: str, c: str) -> pd.Series:
    """Fly in bp = 2*belly - wing_a - wing_c. Unweighted (50/50 in yield); rebuild DV01-neutral before trading."""
    return 2 * y[b] - y[a] - y[c]


def trader_name(legs: list[str]) -> str:
    """['2Y','10Y'] -> '2s10s'; ['2Y','5Y','10Y'] -> '2s5s10s'. Non-year tenors fall back to the raw join."""
    if all(t.endswith("Y") for t in legs):
        return "s".join(t[:-1] for t in legs) + "s"
    return "".join(legs)


# ---------------------------------------------------------------- screen statistics
def _roll(s: pd.Series, window: int):
    return s.rolling(window, min_periods=min(window, max(10, int(0.8 * window))))


def rolling_z(s: pd.Series, window: int) -> pd.Series:
    """Trailing z of the level; the window includes today (desk: 'current vs 5y mean / 5y sd'). Needs >= 80% of window."""
    r = _roll(s, window)
    return (s - r.mean()) / r.std(ddof=1)


def bands(s: pd.Series, window: int, ks=(1, 2)) -> pd.DataFrame:
    r = _roll(s, window)
    out = pd.DataFrame({"level": s, "mean": r.mean()})
    sd = r.std(ddof=1)
    for k in ks:
        out[f"+{k}sd"], out[f"-{k}sd"] = out["mean"] + k * sd, out["mean"] - k * sd
    return out


def range_stats(s: pd.Series, window: int = BD_YEAR) -> dict:
    """1y min/max bar with 25th/75th markers; pctile = mid-rank percentile of the last value inside the window."""
    w = s.dropna().iloc[-window:]
    if len(w) < min(window, max(10, int(0.8 * window))):  # short history: no 1y range/percentile
        return dict(lo=np.nan, p25=np.nan, p75=np.nan, hi=np.nan, last=w.iloc[-1] if len(w) else np.nan, pctile=np.nan)
    last = w.iloc[-1]
    pct = 100 * ((w < last).sum() + 0.5 * (w == last).sum()) / len(w)
    return dict(lo=w.min(), p25=w.quantile(.25), p75=w.quantile(.75), hi=w.max(), last=last, pctile=pct)


def normalised_move(s: pd.Series, h: int = 1, window: int = 62) -> float:
    """Change over h obs / sd of h-obs changes over the `window` obs ENDING BEFORE the move starts (ex-ante sd).
    Desk practice: window 62 for 1d and 1w, 252 for 1m. A short window inflates the score in quiet regimes."""
    ch = s.diff(h)
    hist = ch.iloc[:-h].dropna().iloc[-window:]
    sd = hist.std(ddof=1) if len(hist) > 1 else np.nan
    return float(ch.iloc[-1] / sd) if sd > 0 else float("nan")  # short history or zero sd -> nan, never inf


def sparkline(v) -> str:
    v = np.asarray(v, float)
    lo, hi = v.min(), v.max()
    idx = np.zeros(len(v), int) if hi == lo else np.round((v - lo) / (hi - lo) * 7).astype(int)
    return "".join(SPARKS[i] for i in idx)


def screen(levels: pd.DataFrame, z_window: int = 63, range_window: int = BD_YEAR, spark_n: int = 30) -> pd.DataFrame:
    """One row per structure (column of `levels`, bp): level, 1d/1w/1m change, normalised 1d/1w/1m moves,
    z over z_window (3m) and over range_window (1y), 1y percentile, 1y min/max, sparkline of the last spark_n obs."""
    rows = {}
    for c in levels:
        s = levels[c].dropna()
        rs = range_stats(s, range_window)
        chg = lambda h: s.iloc[-1] - s.iloc[-1 - h] if len(s) > h else np.nan  # 1d, 1w, 1m = 1, 5, 21 obs
        rows[c] = dict(level=s.iloc[-1], chg_1d=chg(1), chg_1w=chg(5), chg_1m=chg(21),
                       nm_1d=normalised_move(s, 1, 62), nm_1w=normalised_move(s, 5, 62), nm_1m=normalised_move(s, 21, 252),
                       **{f"z{z_window}": rolling_z(s, z_window).iloc[-1], f"z{range_window}": rolling_z(s, range_window).iloc[-1]},
                       pctile_1y=rs["pctile"], min_1y=rs["lo"], max_1y=rs["hi"], spark=sparkline(s.iloc[-spark_n:]))
    return pd.DataFrame.from_dict(rows, orient="index")


def z_matrix(levels: pd.DataFrame, windows=(63, 252, 1260)) -> pd.DataFrame:
    """Last z of each column over several lookbacks (rows = structures)."""
    return pd.DataFrame({f"z{w}": {c: float(rolling_z(levels[c].dropna(), w).iloc[-1]) for c in levels} for w in windows})


# ---------------------------------------------------------------- desk score columns (payer perspective)
def vol_3m_horizon(daily_changes: pd.Series, window: int = 63) -> float:
    """Realised sd of daily changes over `window` obs scaled to a 3m (63 obs) horizon, bp = annualised vol / 2.
    ASSUMPTION: the desk's printed '3m realised vol' behaves like this number (see ex_ante_sharpe)."""
    return float(daily_changes.dropna().iloc[-window:].std(ddof=1) * np.sqrt(63))


def ex_ante_sharpe(carry_roll_3m_bp: float, vol_bp: float) -> float:
    """Desk 'Carry' score: implied 3m carry & roll / 3m realised vol, annualised. Arithmetic of the printed tables
    (reader-verified on every row checked): Sharpe = 2 * C / printed vol. It is exactly annualised, 4C / (sd_daily*sqrt(252)),
    when printed vol = vol_3m_horizon (= annualised vol / 2)."""
    return 2 * carry_roll_3m_bp / vol_bp


def trend(ret_2w_bp: float, vol_bp: float) -> float:
    """Desk 'Trend': 2w realised total return (incl. roll; NOT a price change) / 3m realised vol, annualised.
    Printed tables fit Trend = 13 * r_2w / printed vol (= 26 r / annualised vol when vol_bp = annualised vol / 2)."""
    return 13 * ret_2w_bp / vol_bp


def spearman_r(level: pd.Series, ref: pd.Series, h: int = 3, window: int = 63) -> float:
    """Directionality R: Spearman rank correlation of h-day changes of the trade level vs h-day changes of the
    10y swap rate over the last `window` obs. Overlapping changes (document it in the footer)."""
    d = pd.concat([level.diff(h), ref.diff(h)], axis=1).dropna().iloc[-window:]
    return float(d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank()))


def carry_over_r(sharpe: float, r: float) -> float:
    """Carry/R = Sharpe / (1 + |R|): penalises carry that is disguised duration."""
    return sharpe / (1 + abs(r))


# ---------------------------------------------------------------- backtest tearsheet fields
def max_drawdown(cum: pd.Series) -> float:
    """Largest fall from a running high-water mark (same units as cum)."""
    return float((cum.cummax() - cum).max())


def time_under_water(cum: pd.Series) -> int:
    """Longest run, in obs, from a high-water mark until PnL regains it (>=); an unrecovered tail counts to the last obs.
    Sitting flat at the high-water mark is not under water (a monotone or flat series gives 1)."""
    c = cum.dropna().to_numpy(float)
    if len(c) == 0:
        return 0
    hwm = np.maximum.accumulate(c)
    best = peak = 0
    for i in range(len(c)):
        if c[i] >= hwm[i]:  # at or above the previous maximum: drawdown (if any) ends here
            best, peak = max(best, i - peak), i
    return int(max(best, len(c) - 1 - peak))


def hhi_concentration(r) -> float:
    """AFML h = (sum w^2 - 1/n) / (1 - 1/n), w = r / sum r of same-sign bet returns. 0 uniform, 1 one bet. n<=1 -> nan."""
    r = np.asarray(r, float)
    n = len(r)
    if n <= 1:
        return float("nan")
    w = r / r.sum()
    return float(((w ** 2).sum() - 1 / n) / (1 - 1 / n))


def bet_stats(bet_returns) -> dict:
    """Hit ratio, mean hit, mean miss and positive/negative-return concentration over BETS (flat-to-flat), not trades."""
    r = np.asarray(bet_returns, float)
    if len(r) == 0:
        return dict(n_bets=0, hit_ratio=np.nan, avg_hit=np.nan, avg_miss=np.nan, h_plus=np.nan, h_minus=np.nan)
    up, dn = r[r > 0], r[r < 0]
    return dict(n_bets=len(r), hit_ratio=len(up) / len(r), avg_hit=up.mean() if len(up) else np.nan,
                avg_miss=dn.mean() if len(dn) else np.nan, h_plus=hhi_concentration(up), h_minus=hhi_concentration(dn))


# ---------------------------------------------------------------- regression / density
def regress(x, y) -> dict:
    """OLS y = a + b x. Returns slope, intercept, r2, resid (ndarray), resid_z of the last point."""
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    b, a = np.polyfit(xa, ya, 1)
    res = ya - (a + b * xa)
    sd = res.std(ddof=2)
    ss_tot = ((ya - ya.mean()) ** 2).sum()
    return dict(slope=b, intercept=a, r2=1 - (res ** 2).sum() / ss_tot if ss_tot > 0 else np.nan,
                resid=res, resid_z=res[-1] / sd if sd > 1e-12 else 0.0)


def pca_loadings(changes: pd.DataFrame, n: int = 3):
    """PCA of the covariance of daily changes (columns ordered short -> long). Signs fixed: PC1 sum > 0 (level up),
    PC2 last - first > 0 (steepening), PC3 belly minus wings > 0. Returns (loadings, explained ratio)."""
    X = changes.dropna()
    w_all, v_all = np.linalg.eigh(np.cov(X.values.T))
    o = np.argsort(w_all)[::-1][:n]
    w, v = w_all[o], v_all[:, o]
    k = v.shape[0]
    mid = slice((k - 1) // 2, k // 2 + 1)
    for j in range(v.shape[1]):
        f = [v[:, j].sum(), v[-1, j] - v[0, j], v[mid, j].mean() - (v[0, j] + v[-1, j]) / 2][j] if j < 3 else 1
        if f < 0:
            v[:, j] *= -1
    return pd.DataFrame(v, index=X.columns, columns=[f"PC{i + 1}" for i in range(len(w))]), w / w_all.sum()


def density_grid(x, y, n: int = 80):
    """Sum of 2-D Gaussians (one per point, bandwidth = Scott factor x observed sd) on an n x n grid, scaled to max 1.
    Draw it as greyscale behind the dots so clustered points do not read as one and outliers are not over-weighted."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    f = len(x) ** (-1 / 6)
    hx, hy = (x.std(ddof=1) * f) or 1.0, (y.std(ddof=1) * f) or 1.0  # constant series: unit bandwidth, no 0-division
    gx = np.linspace(x.min() - 2 * hx, x.max() + 2 * hx, n)
    gy = np.linspace(y.min() - 2 * hy, y.max() + 2 * hy, n)
    d = np.zeros((n, n))
    for xi, yi in zip(x, y):
        d += np.exp(-0.5 * (((gx[None, :] - xi) / hx) ** 2 + ((gy[:, None] - yi) / hy) ** 2))
    return gx, gy, d / d.max()


# ---------------------------------------------------------------- charts
def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:  # the numbers above work without matplotlib
        raise RuntimeError("matplotlib required for charts") from e


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    _plt().close(fig)
    return path


def plot_ts_bands(s: pd.Series, path: str, window: int = BD_YEAR, title: str = "", unit: str = "bp"):
    """Level + trailing mean + 1/2 sd bands. One data hue, accent on the last point, grey guides, one y-axis,
    business-day x index (holidays do not stretch the axis). Title carries last value and z."""
    plt = _plt()
    s = s.dropna()
    b = bands(s, window)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    x = np.arange(len(b))
    ax.fill_between(x, b["-2sd"], b["+2sd"], color=GREY, alpha=.15, lw=0)
    ax.fill_between(x, b["-1sd"], b["+1sd"], color=GREY, alpha=.25, lw=0)
    ax.plot(x, b["mean"], color=GREY, lw=1, ls="--")
    ax.plot(x, b["level"], color=DATA, lw=1.4)
    ax.scatter([x[-1]], [b["level"].iloc[-1]], color=ACCENT, zorder=3)
    z = rolling_z(s, window).iloc[-1]
    ax.set_title(f"{title}  last {b['level'].iloc[-1]:.1f} {unit}, z{window} {z:+.2f}", loc="left", fontsize=10)
    ticks = np.linspace(0, len(b) - 1, 5).astype(int)
    ax.set_xticks(ticks, [str(b.index[i])[:10] for i in ticks])
    ax.set_ylabel(unit)
    return _save(fig, path)


def plot_scatter_resid(x: pd.Series, y: pd.Series, path: str, xlabel="x (bp)", ylabel="y (bp)", title="", density=True):
    """Regression scatter; last point in accent; +/-1 residual-sd lines; density shading behind the dots."""
    plt = _plt()
    d = pd.concat([x, y], axis=1).dropna()
    r = regress(d.iloc[:, 0], d.iloc[:, 1])
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    if density and len(d) > 20:
        gx, gy, g = density_grid(d.iloc[:, 0], d.iloc[:, 1])
        ax.contourf(gx, gy, g, levels=6, cmap="Greys", alpha=.35)
    ax.scatter(d.iloc[:, 0], d.iloc[:, 1], s=6, color=DATA, alpha=.6)
    xs = np.array([d.iloc[:, 0].min(), d.iloc[:, 0].max()])
    sd = r["resid"].std(ddof=2)
    for off, ls in ((0, "-"), (sd, ":"), (-sd, ":")):
        ax.plot(xs, r["intercept"] + off + r["slope"] * xs, color=GREY, ls=ls, lw=1)
    ax.scatter(d.iloc[-1:, 0], d.iloc[-1:, 1], color=ACCENT, zorder=3)
    ax.set_xlabel(xlabel), ax.set_ylabel(ylabel)
    ax.set_title(f"{title} beta {r['slope']:.2f}, R2 {r['r2']:.2f}, last resid {r['resid'][-1]:+.1f} bp ({r['resid_z']:+.1f} sd)",
                 loc="left", fontsize=9)
    return _save(fig, path)


def plot_pca_loadings(load: pd.DataFrame, expl, path: str):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6, 3.6))
    styles = [(DATA, "-"), (ACCENT, "-"), (GREY, "--")]
    for j, c in enumerate(load.columns):
        col, ls = styles[j % 3]
        ax.plot(range(len(load)), load[c], color=col, ls=ls, marker="o", ms=3, label=f"{c} {100 * expl[j]:.0f}%")
    ax.axhline(0, color=GREY, lw=.8)
    ax.set_xticks(range(len(load)), list(load.index))
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("PCA loadings, daily changes (PC1 level up, PC2 steepening, PC3 belly up)", loc="left", fontsize=9)
    return _save(fig, path)


def plot_zgrid(zm: pd.DataFrame, path: str, cap: float = 3.0):
    """Diverging heat-map, neutral midpoint at z = 0, cell text = z (bold at |z| >= 2). + = level high vs own history."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(1.2 + 0.9 * zm.shape[1], 0.4 + 0.28 * len(zm)))
    im = ax.imshow(zm.values, cmap="coolwarm", vmin=-cap, vmax=cap, aspect="auto")
    ax.set_xticks(range(zm.shape[1]), list(zm.columns))
    ax.set_yticks(range(len(zm)), list(zm.index), fontsize=7)
    for i in range(zm.shape[0]):
        for j in range(zm.shape[1]):
            ax.text(j, i, f"{zm.iat[i, j]:+.1f}", ha="center", va="center", fontsize=7,
                    fontweight="bold" if abs(zm.iat[i, j]) >= 2 else "normal")
    fig.colorbar(im, ax=ax, fraction=.04)
    ax.set_title("z of level (+ = high vs own history; |z|>=2 bold)", loc="left", fontsize=9)
    return _save(fig, path)


# ---------------------------------------------------------------- pipeline
def build_panel(curve_par: pd.DataFrame, curve_id: str, snap: str | None = None) -> pd.DataFrame:
    """Canonical curve_par -> date x tenor panel of spot-start par rates in bp (columns short -> long)."""
    d = curve_par[(curve_par["curve_id"] == curve_id) & (curve_par["start"] == "0D")]
    if snap:
        d = d[d["snap"] == snap]
    if d.duplicated(["date", "tenor"]).any():
        raise ValueError("several snaps per date/tenor: pass --snap (never mix snaps in one series)")
    p = d.pivot(index="date", columns="tenor", values="par_rate_pct").sort_index() * 100.0
    return p[sorted(p.columns, key=tenor_months)]


def run(panel: pd.DataFrame, legs: list[str], out: str, window: int = BD_YEAR) -> list[str]:
    """Write screen.csv (all adjacent-or-not curve spreads + the requested structure), z_matrix.csv and the PNGs."""
    os.makedirs(out, exist_ok=True)
    cols = list(panel.columns)
    grid = {trader_name([a, b]): spread(panel, a, b) for i, a in enumerate(cols) for b in cols[i + 1:]}
    target = spread(panel, *legs) if len(legs) == 2 else fly(panel, *legs)
    name = trader_name(legs)
    grid[name] = target
    levels = pd.DataFrame(grid)
    files = []
    scr = screen(levels)
    scr.to_csv(f"{out}/screen.csv")
    zm = z_matrix(levels)
    zm.to_csv(f"{out}/z_matrix.csv")
    files += [f"{out}/screen.csv", f"{out}/z_matrix.csv"]
    try:
        files.append(plot_ts_bands(target, f"{out}/ts_{name}.png", window, name))
        files.append(plot_zgrid(zm.sort_values(zm.columns[-1]), f"{out}/zgrid.png"))
        L, ev = pca_loadings(panel.diff())
        files.append(plot_pca_loadings(L, ev, f"{out}/pca_loadings.png"))
        files.append(plot_scatter_resid(panel[legs[0]], panel[legs[-1]], f"{out}/scatter_{legs[0]}_{legs[-1]}.png",
                                        f"{legs[0]} (bp)", f"{legs[-1]} (bp)", f"{legs[-1]} vs {legs[0]}"))
    except RuntimeError as e:
        print("charts skipped:", e, file=sys.stderr)
    return files


# ---------------------------------------------------------------- selftest
def _selftest() -> int:
    bad = []

    def chk(name, ok):
        if not ok:
            bad.append(name)

    g = np.random.default_rng(0)
    # z of a ramp over a 5-point window: last five are 95..99, z = 2 / sd(1..5) = 2 / sqrt(2.5)
    ramp = pd.DataFrame({"a": np.arange(100, dtype=float)})
    chk("ramp z", abs(z_matrix(ramp, (5,)).iloc[0, 0] - 2 / np.sqrt(2.5)) < 1e-9)
    # normalised move: increments [1,-1,1,-1,3]; ex-ante sd of the first four = sqrt(4/3)
    s = pd.Series(np.cumsum([0, 1, -1, 1, -1, 3.0]))
    chk("norm move", abs(normalised_move(s, 1, 62) - 3 / np.sqrt(4 / 3)) < 1e-9)
    # conventions: 2s10s = 10y - 2y = 50; 2s5s10s = 2*430 - 400 - 450 = 10
    y = pd.DataFrame({"2Y": [400.0], "5Y": [430.0], "10Y": [450.0]})
    chk("spread/fly", spread(y, "2Y", "10Y").iloc[0] == 50 and fly(y, "2Y", "5Y", "10Y").iloc[0] == 10)
    chk("names", trader_name(["2Y", "10Y"]) == "2s10s" and trader_name(["2Y", "5Y", "10Y"]) == "2s5s10s")
    # desk definitions, checked against numbers printed in the desk tables (30 Sep 2026): CHF 1y1y/2y1y C 7.7 vol 12.3 -> 1.26
    chk("sharpe CHF", abs(ex_ante_sharpe(7.7, 12.3) - 1.26) < 0.01)
    chk("sharpe JPY", abs(ex_ante_sharpe(4.0, 6.6) - 1.20) < 0.02)     # printed 1.20
    chk("trend EUR", abs(trend(9.1, 45.6) - 2.61) < 0.03)               # printed 2.61
    chk("trend GBP", abs(trend(-12.1, 10.9) - (-14.60)) < 0.5)           # printed (14.60)
    # simulated: daily sd 2 bp -> vol_3m_horizon = 2*sqrt(63); annualised form 4C/(sd*sqrt(252)) must agree
    dc = pd.Series(g.normal(scale=2.0, size=20000))
    v = vol_3m_horizon(dc, 20000)
    chk("vol3m", abs(v - 2 * np.sqrt(63)) < 0.15)
    chk("sharpe annualised", abs(ex_ante_sharpe(11.3, v) - 4 * 11.3 / (dc.std(ddof=1) * np.sqrt(252))) < 1e-9)
    chk("trend annualised", abs(trend(3.9, v) - 26 * 3.9 / (dc.std(ddof=1) * np.sqrt(252))) < 1e-9)
    # Carry/R from the desk table: Sharpe 1.20, R 0.26 -> 0.95
    chk("carry/R", abs(carry_over_r(1.20, 0.26) - 0.952) < 1e-3 and carry_over_r(1.2, -0.26) == carry_over_r(1.2, 0.26))
    # Spearman R: level = 2*ref -> +1; level = -ref**1 -> -1; independent noise -> ~0
    ref = pd.Series(np.cumsum(g.normal(size=400)))
    chk("R +1", abs(spearman_r(2 * ref, ref, 3, 200) - 1) < 1e-9)
    chk("R -1", abs(spearman_r(-ref, ref, 3, 200) + 1) < 1e-9)
    chk("R 0", abs(spearman_r(pd.Series(np.cumsum(g.normal(size=4000))), pd.Series(np.cumsum(g.normal(size=4000))), 3, 4000)) < 0.1)
    # regression: exact line, then known slope under noise
    r = regress([0, 1, 2, 3], [2, 5, 8, 11])
    chk("line", abs(r["slope"] - 3) < 1e-9 and abs(r["intercept"] - 2) < 1e-9 and r["r2"] > 1 - 1e-12)
    xx = g.normal(size=3000)
    chk("noisy slope", abs(regress(xx, 1.5 * xx + g.normal(scale=.5, size=3000))["slope"] - 1.5) < 0.05)
    # PCA: planted level/slope/curvature factors with sd 3 / 1.5 / .5 -> PC1 explains 9 / 11.5
    Lv, Sl, Cv = np.ones(4) / 2, np.array([-1, -.5, .5, 1]) / np.sqrt(2.5), np.array([-1, 1, 1, -1]) / 2
    X = pd.DataFrame((g.normal(size=(20000, 3)) * [3, 1.5, .5]) @ np.vstack([Lv, Sl, Cv]), columns=["2Y", "5Y", "10Y", "30Y"])
    L, ev = pca_loadings(X)
    chk("pca vectors", all(L[f"PC{i + 1}"].values @ vv > .99 for i, vv in enumerate([Lv, Sl, Cv])))
    chk("pca explained", abs(ev[0] - 9 / 11.5) < .01)
    # tearsheet: cum [0,2,1,0,3,2,2,4]: max DD 2; marks at 1,4,7 -> longest underwater gap 3
    cum = pd.Series([0, 2, 1, 0, 3, 2, 2, 4.0])
    chk("maxdd/tuw", max_drawdown(cum) == 2 and time_under_water(cum) == 3)
    chk("tuw tail", time_under_water(pd.Series([0, 3, 2, 1, 2.0])) == 3)  # open drawdown counts
    chk("tuw equal regain", time_under_water(pd.Series([0, 2, 1, 2, 3.0])) == 2)  # regained at the equal level, not the next high
    chk("tuw flat at hwm", time_under_water(pd.Series([0, 2, 2, 2, 2, 2.0])) == 1)  # flat is not under water
    chk("hhi", abs(hhi_concentration([.5, .3, .2]) - .07) < 1e-9 and abs(hhi_concentration([1, 1, 1, 1])) < 1e-12)
    bs = bet_stats([2, -1, 3, -1, 1])
    chk("bets", bs["hit_ratio"] == .6 and bs["avg_hit"] == 2 and bs["avg_miss"] == -1 and bs["n_bets"] == 5)
    chk("short history", np.isnan(range_stats(pd.Series(range(5)), 252)["pctile"]) and np.isnan(normalised_move(pd.Series([1.0, 2.0, 4.0]), 1, 62)))
    chk("empty bets", bet_stats([])["n_bets"] == 0)
    chk("spark", sparkline(range(1, 9)) == SPARKS)
    chk("range", abs(range_stats(pd.Series(range(1, 101)), 100)["pctile"] - 99.5) < 1e-9)
    gx, gy, d = density_grid(np.r_[np.zeros(30), 5.0], np.r_[np.zeros(30), 5.0])
    chk("density", abs(gx[np.argmax(d.max(0))]) < .5)
    # canonical panel units (pct -> bp) and end-to-end: screen.csv, z_matrix.csv, PNG magic bytes
    dates = pd.bdate_range("2023-01-02", periods=400)
    rows = [dict(date=dt, snap="eod_ny", curve_id="USD-SOFR", start="0D", tenor=t,
                 par_rate_pct=3.0 + .1 * i + .05 * np.sin(k / 20 + i))
            for k, dt in enumerate(dates) for i, t in enumerate(["2Y", "5Y", "10Y", "30Y"])]
    p = build_panel(pd.DataFrame(rows), "USD-SOFR")
    chk("units", abs(p["2Y"].iloc[0] - 300) < 1e-9 and list(p.columns) == ["2Y", "5Y", "10Y", "30Y"])
    with tempfile.TemporaryDirectory() as td:
        fl = run(p, ["2Y", "5Y", "10Y"], td)
        chk("outputs", any(f.endswith("screen.csv") for f in fl))
        scr = pd.read_csv(f"{td}/screen.csv", index_col=0)
        exp = 2 * p["5Y"] - p["2Y"] - p["10Y"]
        chk("screen level", abs(scr.loc["2s5s10s", "level"] - exp.iloc[-1]) < 1e-9)
        chk("screen z", abs(scr.loc["2s5s10s", "z63"] - rolling_z(exp, 63).iloc[-1]) < 1e-9)
        for f in fl:
            if f.endswith(".png"):
                chk(f"png {os.path.basename(f)}", open(f, "rb").read(4) == b"\x89PNG")
    if bad:
        print("SELFTEST FAILED:", bad)
        return 1
    print("selftest ok")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--curve-par", help="canonical curve_par CSV or Parquet")
    ap.add_argument("--curve-id")
    ap.add_argument("--snap")
    ap.add_argument("--legs", default="2Y,10Y", help="2 tenors = curve spread, 3 = fly")
    ap.add_argument("--window", type=int, default=BD_YEAR)
    ap.add_argument("--out", default="rv_charts_out")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not (a.curve_par and a.curve_id):
        ap.error("--curve-par and --curve-id required")
    df = pd.read_parquet(a.curve_par) if a.curve_par.endswith(".parquet") else pd.read_csv(a.curve_par)
    df["date"] = pd.to_datetime(df["date"])
    legs = [t.strip().upper() for t in a.legs.split(",")]
    for f in run(build_panel(df, a.curve_id, a.snap), legs, a.out, a.window):
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
