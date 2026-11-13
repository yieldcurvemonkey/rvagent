"""Causal z-scores, percentiles, robust z, cross-sectional screen table, bucket study, multiple-testing flags.

Every statistic at date t uses data up to t only (optionally up to t-1). Nothing is forward-filled.

Library use:   from zscore import rolling_z, robust_z, rolling_pctile, screen, bucket_table, holm, bh
CLI (wide CSV/Parquet: date column + one column per series; or long with --id-col/--value-col):
    python zscore.py --input panel.csv --lookbacks 63,252,756 --out screen.csv
    python zscore.py --input long.csv --id-col package_id --value-col value
    python zscore.py --selftest
Sign: z > 0 means the level is HIGH vs its own history. Whether that is rich or cheap depends on the series
convention (yield/spread high = cheap for a receiver); the caller maps it.
"""
from __future__ import annotations

import argparse
import sys
import warnings

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

MAD_K = 1.4826  # MAD -> sigma for normal data


def _s(x) -> pd.Series:
    return x.astype(float) if isinstance(x, pd.Series) else pd.Series(np.asarray(x, dtype=float))


def _win(x: pd.Series, window: int, exclude_current: bool):
    """Return (values, n x window matrix of the trailing window, NaN padded at the front)."""
    v = x.to_numpy(float)
    xp = np.concatenate([np.full(window, np.nan), v])
    w = sliding_window_view(xp, window + 1)  # row t = x[t-window .. t]
    return v, (w[:, :-1] if exclude_current else w[:, 1:])


def rolling_z(x, window: int = 63, min_periods: int | None = None, exclude_current: bool = False,
              ddof: int = 1, std_floor: float = 1e-12, clip: float | None = None) -> pd.Series:
    """z_t = (x_t - mean_L) / std_L over the trailing window. exclude_current=True uses x_{t-L..t-1}.
    Inclusive windows cap |z| at (L-1)/sqrt(L); exclude_current removes that self-inclusion shrinkage."""
    x = _s(x)
    base = x.shift(1) if exclude_current else x
    r = base.rolling(window, min_periods=window if min_periods is None else min_periods)
    mu, sd = r.mean(), r.std(ddof=ddof)
    z = (x - mu) / sd.where(sd > std_floor * (1 + mu.abs()))
    return z.clip(-clip, clip) if clip else z


def ewma_z(x, halflife: float = 21, min_periods: int | None = None, exclude_current: bool = True) -> pd.Series:
    """EWMA z-score (exponentially weighted mean and std, weights only on the past). halflife 21 ~ lambda 0.968."""
    x = _s(x)
    base = x.shift(1) if exclude_current else x
    e = base.ewm(halflife=halflife, min_periods=int(3 * halflife) if min_periods is None else min_periods)
    sd = e.std()
    return (x - e.mean()) / sd.where(sd > 1e-12)


def robust_z(x, window: int = 252, min_periods: int | None = None, exclude_current: bool = False,
             k: float = MAD_K) -> pd.Series:
    """(x - rolling median) / (k * rolling MAD). NaN where MAD is 0 (many repeated values)."""
    x = _s(x)
    v, w = _win(x, window, exclude_current)
    ok = (~np.isnan(w)).sum(1) >= (window if min_periods is None else min_periods)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        med = np.nanmedian(w, axis=1)
        sig = k * np.nanmedian(np.abs(w - med[:, None]), axis=1)
        z = np.where(ok & (sig > 1e-12), (v - med) / sig, np.nan)
    return pd.Series(z, index=x.index)


def rolling_pctile(x, window: int = 252, min_periods: int | None = None, exclude_current: bool = False) -> pd.Series:
    """Share of window observations <= x_t (0..1). 1.0 = at/above everything in the window."""
    x = _s(x)
    v, w = _win(x, window, exclude_current)
    cnt = (~np.isnan(w)).sum(1)
    p = (w <= v[:, None]).sum(1) / np.maximum(cnt, 1)
    ok = (cnt >= (window if min_periods is None else min_periods)) & ~np.isnan(v)
    return pd.Series(np.where(ok, p, np.nan), index=x.index)


def move_score(x, h: int = 5, window: int = 252) -> pd.Series:
    """h-period change / std of h-period changes over the trailing window (sigma-move). Report the raw change too."""
    x = _s(x)
    d = x.diff(h)
    return d / d.rolling(window, min_periods=window).std()


def stale_days(x) -> int:
    """Trailing run of identical values (a frozen input), minus one."""
    v = _s(x).dropna().to_numpy()
    if len(v) == 0:
        return 0
    n = 0
    for a in v[::-1]:
        if a != v[-1]:
            break
        n += 1
    return n - 1


def cs_zscore(wide: pd.DataFrame, trim: float | None = 2.0) -> pd.DataFrame:
    """Cross-sectional z per date across columns (ddof=1), trimmed to +/-trim. Not comparable across screens."""
    sd = wide.std(axis=1, ddof=1)
    z = wide.sub(wide.mean(axis=1), axis=0).div(sd.where(sd > 1e-12), axis=0)
    return z.clip(-trim, trim) if trim else z


def screen(wide: pd.DataFrame, lookbacks=(63, 252, 756), primary: int = 252, exclude_current: bool = False,
           move_h: int = 5, ewma_halflife: float = 21) -> pd.DataFrame:
    """One row per series for the latest observation: levels, multi-lookback z, robust z, EWMA z, percentile,
    sigma-move, stale/lag diagnostics, window agreement flag and cross-sectional ranks (1 = highest z / most extreme)."""
    rows = {}
    end = wide.index.max()
    for c in wide.columns:
        s = wide[c].dropna()
        if s.empty:
            continue
        r = {"last_date": s.index[-1], "lag_obs": int((wide.index > s.index[-1]).sum()), "n_obs": len(s),
             "last": s.iloc[-1], "stale_days": stale_days(s)}
        zs = []
        for L in lookbacks:
            z = rolling_z(s, L, exclude_current=exclude_current).iloc[-1]
            r[f"z_{L}"] = z
            zs.append(z)
        r[f"rz_{primary}"] = robust_z(s, primary, exclude_current=exclude_current).iloc[-1]
        r[f"ewz_h{ewma_halflife:g}"] = ewma_z(s, ewma_halflife).iloc[-1]
        r[f"pct_{primary}"] = rolling_pctile(s, primary, exclude_current=exclude_current).iloc[-1]
        r[f"move_{move_h}"] = move_score(s, move_h, primary).iloc[-1]
        zv = [z for z in zs if np.isfinite(z)]
        big = [z for z in zv if abs(z) >= 1]
        if len(zv) < 2:
            view = "n/a"
        elif len(big) == len(zv) and len({np.sign(z) for z in zv}) == 1:
            view = "agree"
        elif len({np.sign(z) for z in big}) > 1 or (abs(zv[0]) >= 2 and abs(zv[-1]) < 1):
            view = "disagree"
        else:
            view = "mixed"
        r["window_view"] = view
        zp = r.get(f"z_{primary}")
        if zp is None:  # primary window not among the displayed lookbacks
            zp = r[f"z_{primary}"] = rolling_z(s, primary, exclude_current=exclude_current).iloc[-1]
        r["flag"] = ("alert>=3" if abs(zp) >= 3 else "flag>=2" if abs(zp) >= 2 else "watch>=1.5" if abs(zp) >= 1.5
                     else "") if np.isfinite(zp) else "n/a"
        rows[c] = r
    out = pd.DataFrame(rows).T
    zp = pd.to_numeric(out.get(f"z_{primary}"), errors="coerce")
    out["rank_z"] = zp.rank(ascending=False, method="min")
    out["rank_abs"] = zp.abs().rank(ascending=False, method="min")
    out.attrs["as_of"] = end
    return out


def fwd_change(x, h: int) -> pd.Series:
    """Forward h-period change x_{t+h} - x_t. FOR EVALUATION ONLY (looks ahead by design)."""
    x = _s(x)
    return x.shift(-h) - x


def bucket_table(signal, fwd, n: int = 5, edges=None) -> pd.DataFrame:
    """Forward outcome by signal bucket: count, mean, median, share>0, mean minus overall mean (quantile buckets
    unless edges given). Signal should itself be causal (rolling z/percentile)."""
    d = pd.concat({"s": _s(signal), "f": _s(fwd)}, axis=1).dropna()
    b = (pd.qcut(d["s"], n, labels=False, duplicates="drop") if edges is None
         else pd.cut(d["s"], edges, labels=False, include_lowest=True))
    g = d["f"].groupby(b)
    out = pd.DataFrame({"n": g.size(), "mean": g.mean(), "median": g.median(),
                        "share_pos": g.apply(lambda v: (v > 0).mean())})
    out["mean_less_all"] = out["mean"] - d["f"].mean()
    return out


def z_to_p(z, dof: float | None = None):
    """Two-sided p-value of a z (normal) or of a t-stat with dof (use dof = window-1 for a z built from a window)."""
    from scipy import stats
    z = np.abs(np.asarray(z, float))
    return 2 * (stats.norm.sf(z) if dof is None else stats.t.sf(z, dof))


def holm(p, alpha: float = 0.05) -> np.ndarray:
    """Holm step-down: reject ordered p_(j) while p_(j) <= alpha/(m+1-j). Valid under any dependence."""
    p = np.asarray(p, float)
    m, rej = len(p), np.zeros(len(p), bool)
    for rank, i in enumerate(np.argsort(p)):
        if p[i] <= alpha / (m - rank):
            rej[i] = True
        else:
            break
    return rej


def bh(p, alpha: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg FDR: reject all p <= p_(L), L = max{j : p_(j) <= alpha*j/m} (independent/PRDS tests)."""
    p = np.asarray(p, float)
    m = len(p)
    srt = np.sort(p)
    ok = np.nonzero(srt <= alpha * np.arange(1, m + 1) / m)[0]
    return p <= srt[ok.max()] if len(ok) else np.zeros(m, bool)


# --------------------------------------------------------------------------------------------- self-test
def selftest() -> int:
    fails: list[str] = []

    def check(name, cond, info=""):
        if not cond:
            fails.append(f"{name} {info}")

    # 1. hand-computed z: window [1..5], x=5 -> (5-3)/sd(1..5)=2/1.5811
    z = rolling_z([1, 2, 3, 4, 5], 5).iloc[-1]
    check("z_known", abs(z - 2 / np.sqrt(2.5)) < 1e-9, z)
    ze = rolling_z([1, 2, 3, 4, 5, 6], 5, exclude_current=True).iloc[-1]
    check("z_excl_known", abs(ze - 3 / np.sqrt(2.5)) < 1e-9, ze)
    # 2. cap of an inclusive window: 20 zeros then 1, L=21 -> (L-1)/sqrt(L); all-zero windows must give NaN
    zz = rolling_z([0.0] * 20 + [1.0], 21)
    check("z_cap", abs(zz.iloc[-1] - 20 / np.sqrt(21)) < 1e-9, zz.iloc[-1])
    check("z_floor", np.isnan(rolling_z([0.0] * 30, 21).iloc[-1]))
    # 3. causality: changing the future must not change any statistic at t; excluding current ignores x_t itself
    rng = np.random.default_rng(1)
    x = pd.Series(np.cumsum(rng.normal(size=600)) + rng.normal(size=600))
    k = 450
    y = x.copy()
    y.iloc[k + 1:] += rng.normal(10, 5, size=len(y) - k - 1)  # future shock
    for name, f in {
        "rolling_z": lambda s: rolling_z(s, 63), "rolling_z_ex": lambda s: rolling_z(s, 63, exclude_current=True),
        "ewma_z": lambda s: ewma_z(s, 21), "robust_z": lambda s: robust_z(s, 63),
        "pctile": lambda s: rolling_pctile(s, 63), "move": lambda s: move_score(s, 5, 63),
    }.items():
        a, b = f(x).iloc[k], f(y).iloc[k]
        check(f"causal_{name}", np.isfinite(a) and abs(a - b) < 1e-12, (a, b))
    w = x.copy()
    w.iloc[k] += 50  # a shock at t must not leak into its own mean/std when exclude_current=True
    past = x.iloc[k - 63:k]
    manual = (w.iloc[k] - past.mean()) / past.std(ddof=1)
    check("excl_uses_past_only", abs(rolling_z(w, 63, exclude_current=True).iloc[k] - manual) < 1e-9)
    # 4. robust z: [1,2,3,4,100] -> median 3, MAD 1 -> (100-3)/1.4826 ; plain z is bounded near 1.79
    d = [1, 2, 3, 4, 100]
    check("robust_known", abs(robust_z(d, 5).iloc[-1] - 97 / 1.4826) < 1e-9, robust_z(d, 5).iloc[-1])
    check("plain_bounded", rolling_z(d, 5).iloc[-1] < 1.8)
    # 5. percentile: last 4 in [3,1,2,5,4] -> 4/5 ; excluding current, 6 vs prior five -> 1.0
    check("pct_known", abs(rolling_pctile([3, 1, 2, 5, 4], 5).iloc[-1] - 0.8) < 1e-12)
    check("pct_excl", rolling_pctile([3, 1, 2, 5, 4, 6], 5, exclude_current=True).iloc[-1] == 1.0)
    # 6. iid N(0,1): causal z has sd ~ 1 and ~4.6% beyond |2|
    e = pd.Series(np.random.default_rng(7).normal(size=30000))
    zr = rolling_z(e, 252, exclude_current=True).dropna()
    check("iid_sd", 0.99 < zr.std() < 1.04, zr.std())
    check("iid_tail", 0.035 < (zr.abs() > 2).mean() < 0.06, (zr.abs() > 2).mean())
    ze2 = ewma_z(e, 63).dropna()
    check("ewma_sd", 0.97 < ze2.std() < 1.06, ze2.std())
    # 7. cross-sectional z: row [1,2,3,10] -> mean 4, sd sqrt(50/3); trimmed at 2
    cz = cs_zscore(pd.DataFrame([[1, 2, 3, 10.0]]), trim=None).iloc[0, 3]
    check("cs_known", abs(cz - 6 / np.sqrt(50 / 3)) < 1e-9, cz)
    check("cs_trim", cs_zscore(pd.DataFrame([[0, 0, 0, 0, 0, 0, 0, 0, 0, 100.0]]), trim=2.0).iloc[0, 9] == 2.0)
    # 8. multiple testing: Holm vs Bonferroni vs BH on a published 5-test example (alpha 0.05)
    p = [0.006, 0.012, 0.601, 0.756, 0.918]
    check("bonferroni", (np.array(p) < 0.05 / 5).sum() == 1)
    check("holm", holm(p).sum() == 2 and holm(p)[:2].all(), holm(p))
    check("bh", bh(p).sum() == 2 and bh(p)[:2].all(), bh(p))
    check("bh_none", bh([0.5, 0.6]).sum() == 0)
    # 9. bucket table: f = s, 100 points, 5 quantile buckets -> means 9.5, 29.5, ...
    s = pd.Series(np.arange(100.0))
    bt = bucket_table(s, s, 5)
    check("bucket_means", np.allclose(bt["mean"].to_numpy(), [9.5, 29.5, 49.5, 69.5, 89.5]), bt["mean"].tolist())
    check("fwd_change", fwd_change([1, 4, 9], 1).iloc[0] == 3)
    # 10. screen end to end: A trends up (high z), B noise, C frozen; stale count and ranks
    idx = pd.bdate_range("2020-01-01", periods=300)
    r2 = np.random.default_rng(3)
    wide = pd.DataFrame({"A": np.linspace(0, 6, 300) + r2.normal(0, .05, 300), "B": r2.normal(size=300),
                         "C": 5.0}, index=idx)
    sc = screen(wide, lookbacks=(63, 252), primary=252)
    check("screen_rank", sc.loc["A", "rank_z"] == 1 and sc.loc["A", "flag"] != "", sc[["z_252", "rank_z", "flag"]])
    check("screen_frozen", sc.loc["C", "stale_days"] == 299 and sc.loc["C", "flag"] == "n/a")
    check("primary_not_in_lookbacks", screen(wide, lookbacks=(63,), primary=252).loc["A", "rank_z"] == 1)
    check("stale_small", stale_days([1, 2, 3, 3, 3]) == 2)
    check("holm_z_to_p", abs(float(z_to_p(1.96)) - 0.05) < 1e-3)
    for f in fails:
        print("FAIL", f)
    print("selftest", "FAILED" if fails else "OK")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--input", help="CSV or Parquet path")
    ap.add_argument("--date-col", default="date")
    ap.add_argument("--id-col", help="long format: series id column (omit for wide)")
    ap.add_argument("--value-col", default="value")
    ap.add_argument("--lookbacks", default="63,252,756")
    ap.add_argument("--primary", type=int, default=252)
    ap.add_argument("--exclude-current", action="store_true")
    ap.add_argument("--out", help="write CSV here (default: print)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.input:
        ap.error("--input required (or --selftest)")
    df = pd.read_parquet(a.input) if a.input.endswith(".parquet") else pd.read_csv(a.input)
    df[a.date_col] = pd.to_datetime(df[a.date_col])
    wide = (df.pivot_table(index=a.date_col, columns=a.id_col, values=a.value_col, aggfunc="last")
            if a.id_col else df.set_index(a.date_col)).sort_index().apply(pd.to_numeric, errors="coerce")
    lb = tuple(int(v) for v in a.lookbacks.split(","))
    out = screen(wide, lb, a.primary, a.exclude_current)
    if a.out:
        out.to_csv(a.out)
    else:
        print(out.to_string(float_format=lambda v: f"{v:.3f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
