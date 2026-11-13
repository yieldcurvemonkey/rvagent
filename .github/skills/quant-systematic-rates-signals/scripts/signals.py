"""Rule-based duration-timing and cross-market signals for G10 rates.

Sign convention for every output: + = long duration / receive fixed / overweight that market.

Time-series (duration) signals, one column per market:
  carry-to-risk  c2r = (y_long - y_short) / EWMA vol of daily excess returns (decay 0.97, annualised)
                 position = 4 * (trailing 10y percentile of c2r - 0.5)  ->  +2 at 10y high, -2 at 10y low
  momentum       +1 if the excess-return index is above its mean over BOTH the short (1m) and long (12m)
                 windows, -1 if below both, 0 if they disagree
  macro momentum +1 if local AND global indicator fell over n periods, -1 if both rose, else 0
                 (manufacturing PMI n=2 months; earnings-revision ratio n=3 months)
  equity         contrarian: +1 if the equity index is below its 6m mean, -1 if above
Cross-sectional (cross-market) signals, one row per date:
  carry          rank of slope (y_long - y_short)
  slope reversal rank of (y_long - y_mid) minus its 6m mean (overweight the market that steepened most)
  -> +1 for the top n_pairs markets, -1 for the bottom n_pairs
Composite: weighted sum, weights renormalised over the signals available on each date.

CLI reads the canonical `curve_par` table (CSV or Parquet). Macro/equity signals computed elsewhere can be fed
with --extra (long CSV: date, curve_id, signal, value). Run `python signals.py --selftest`.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

PPY = 252  # rows per year (business days)
DEFAULT_WEIGHTS = {"c2r": 0.35, "mom": 0.20, "pmi": 0.15, "revisions": 0.15, "equity": 0.15}


# ---------------------------------------------------------------- building blocks
def par_duration(y_pct, years: float):
    """Annuity (modified-duration proxy) of an annual-pay par swap, in years. y in pct."""
    y = np.asarray(y_pct, dtype=float) / 100.0
    with np.errstate(divide="ignore", invalid="ignore"):
        d = (1.0 - (1.0 + y) ** (-years)) / y
    return np.where(np.abs(y) < 1e-10, float(years), d)


def excess_return(y_long: pd.DataFrame, y_short: pd.DataFrame, years: float = 10.0) -> pd.DataFrame:
    """Daily excess return of a constant-maturity receiver, % of notional: carry accrual minus duration x dy.

    ponytail: no roll-down or convexity; use fi-carry-and-rolldown for an exact carry/roll split.
    """
    dur = pd.DataFrame(par_duration(y_long.values, years), index=y_long.index, columns=y_long.columns)
    carry = (y_long - y_short).shift(1) / PPY
    return carry - dur.shift(1) * y_long.diff()


def ewma_vol(ret: pd.DataFrame, decay: float = 0.97) -> pd.DataFrame:
    """Zero-mean EWMA vol (RiskMetrics style), annualised, same units as ret."""
    return np.sqrt((ret ** 2).ewm(alpha=1.0 - decay, adjust=False).mean() * PPY)


def _pct_of_last(w: np.ndarray) -> float:
    x = w[-1]
    w = w[~np.isnan(w)]
    if len(w) < 2 or np.isnan(x):
        return np.nan
    return ((w < x).sum() + ((w == x).sum() - 1) / 2.0) / (len(w) - 1)  # 0 at window low, 1 at high


def trailing_percentile(x: pd.DataFrame, window: int = 10 * PPY, min_periods: int = 3 * PPY) -> pd.DataFrame:
    return x.rolling(window, min_periods=min_periods).apply(_pct_of_last, raw=True)


def carry_to_risk(y_long, y_short, ret, decay=0.97):
    """c2r = slope (pct per year) / annualised EWMA vol of excess returns (pct): an ex-ante Sharpe ratio."""
    return (y_long - y_short) / ewma_vol(ret, decay)


def c2r_position(c2r: pd.DataFrame, window: int = 10 * PPY, min_periods: int = 3 * PPY) -> pd.DataFrame:
    return 4.0 * (trailing_percentile(c2r, window, min_periods) - 0.5)


def momentum_signal(index: pd.DataFrame, short: int = 21, long: int = PPY) -> pd.DataFrame:
    """+1 if index above BOTH trailing means, -1 if below both, 0 otherwise. NaN until the long window fills."""
    ms, ml = index.rolling(short).mean(), index.rolling(long).mean()
    out = pd.DataFrame(0.0, index=index.index, columns=index.columns)
    out[(index > ms) & (index > ml)] = 1.0
    out[(index < ms) & (index < ml)] = -1.0
    return out.where(ml.notna())


def macro_momentum(local: pd.DataFrame, global_: pd.Series, n: int) -> pd.DataFrame:
    """Duration signal from an activity indicator: long (+1) if local AND global fell over n periods.
    Index the inputs by PUBLICATION date (first release), not reference month, or the signal looks ahead."""
    dl, dg = local.diff(n), global_.diff(n)
    both_down = dl.lt(0).mul(dg.lt(0), axis=0)
    both_up = dl.gt(0).mul(dg.gt(0), axis=0)
    out = both_down.astype(float) - both_up.astype(float)
    return out.where(dl.notna() & dg.notna().values[:, None])


def equity_contrarian(equity: pd.DataFrame, window: int = 126) -> pd.DataFrame:
    """Long duration when local equities are below their trailing mean (bond-equity correlation < 0 regime)."""
    m = equity.rolling(window).mean()
    return -np.sign(equity - m).where(m.notna())


def xs_rank_signal(x: pd.DataFrame, n_pairs: int = 2) -> pd.DataFrame:
    """Per row: +1 for the n_pairs largest values, -1 for the n_pairs smallest, 0 otherwise."""
    r = x.rank(axis=1, method="first")
    n = x.notna().sum(axis=1)
    top = r.gt(n - n_pairs, axis=0)
    bot = r.le(n_pairs, axis=0)
    out = top.astype(float) - bot.astype(float)
    return out.where(x.notna() & (n >= 2 * n_pairs).values[:, None])


def slope_reversal(slope: pd.DataFrame, window: int = 126) -> pd.DataFrame:
    return slope - slope.rolling(window).mean()


def combine(signals: dict, weights: dict = DEFAULT_WEIGHTS) -> pd.DataFrame:
    """Weighted mean over the signals present on each date (weights renormalised to sum to 1)."""
    num = den = None
    for k, s in signals.items():
        w = weights.get(k, 0.0)
        if w == 0:
            continue
        num = s.fillna(0) * w if num is None else num.add(s.fillna(0) * w, fill_value=0)
        den = s.notna() * w if den is None else den.add(s.notna() * w, fill_value=0)
    return num / den.replace(0, np.nan)


def monthly_hold(sig: pd.DataFrame, nth: int = -1) -> pd.DataFrame:
    """Sample on the nth row of each month (-1 = last; 1 = 2nd working day, the source's PMI-driven rebalance),
    hold until the next sample, trade from the following row (shift 1: no look-ahead)."""
    idx = sig.index
    k = pd.Series(0, index=idx).groupby(idx.to_period("M")).cumcount(ascending=nth >= 0)
    pick = (k == (nth if nth >= 0 else -nth - 1)).values
    # reindex(method=ffill) carries the last SAMPLE forward, NaN included (a stale position never survives a data gap)
    return sig.loc[pick].reindex(idx, method="ffill").shift(1)


# ---------------------------------------------------------------- pipeline
def build(y_long, y_short, y_mid, years=10.0, extra=None, n_pairs=2, pct_window=10 * PPY, pct_min=3 * PPY,
          max_gap=5):
    # bridge local holidays / dropped rows so the move across a gap is not lost from the return index
    y_long, y_short, y_mid = (y.ffill(limit=max_gap) for y in (y_long, y_short, y_mid))
    ret = excess_return(y_long, y_short, years)
    index = ret.fillna(0).cumsum().where(ret.notna() | ret.notna().cumsum().gt(0))
    c2r = carry_to_risk(y_long, y_short, ret)
    ts = {"c2r": c2r_position(c2r, pct_window, pct_min), "mom": momentum_signal(index)}
    ts.update(extra or {})
    out = {
        **ts,
        "duration_score": combine(ts),
        "xs_carry": xs_rank_signal(y_long - y_short, n_pairs),
        "xs_c2r": xs_rank_signal(c2r, n_pairs),
        "xs_slope_rev": xs_rank_signal(slope_reversal(y_long - y_mid), n_pairs),
        "slope_bp": (y_long - y_short) * 100.0,
        "c2r_raw": c2r,
    }
    return out, ret


def _read(path):
    return pd.read_parquet(path) if str(path).lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def load_curve_par(path, snap=None, curves=None):
    df = _read(path)
    df = df[df["start"].astype(str) == "0D"]
    if "data_ok" in df:
        df = df[df["data_ok"].astype(str).str.lower() != "false"]
    snaps = df["snap"].unique()
    if snap is None and len(snaps) > 1:
        sys.exit(f"several snaps in curve_par {sorted(snaps)}; pick one with --snap (never mix snaps)")
    snap = snap or snaps[0]
    df = df[df["snap"] == snap]
    if curves:
        df = df[df["curve_id"].isin(curves)]
    df = df.assign(date=pd.to_datetime(df["date"]))
    return df.pivot_table(index="date", columns=["tenor", "curve_id"], values="par_rate_pct", aggfunc="last"), snap


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--curve-par", help="canonical curve_par CSV/Parquet")
    ap.add_argument("--snap")
    ap.add_argument("--curves", help="comma list of curve_id, e.g. USD-SOFR,EUR-ESTR,GBP-SONIA")
    ap.add_argument("--long-tenor", default="10Y")
    ap.add_argument("--short-tenor", default="3M", help="carry funding leg; use the swap's own float index")
    ap.add_argument("--mid-tenor", default="1Y", help="slope-reversal short leg (10y-1y)")
    ap.add_argument("--extra", help="long CSV date,curve_id,signal,value for pmi/revisions/equity signals")
    ap.add_argument("--n-pairs", type=int, default=2)
    ap.add_argument("--out", help="write full history in the canonical `signals` long format")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.curve_par:
        ap.error("--curve-par is required")
    wide, snap = load_curve_par(a.curve_par, a.snap, a.curves.split(",") if a.curves else None)
    try:
        yl, ys, ym = (wide[t] for t in (a.long_tenor, a.short_tenor, a.mid_tenor))
    except KeyError as e:
        sys.exit(f"tenor {e} missing from curve_par; ask the data adapter for it")
    years = float(a.long_tenor.rstrip("Y"))
    extra = None
    if a.extra:
        ex = _read(a.extra).assign(date=lambda d: pd.to_datetime(d["date"]))
        extra = {k: g.pivot_table(index="date", columns="curve_id", values="value").reindex(yl.index, method="ffill")
                 for k, g in ex.groupby("signal")}
        unknown = sorted(set(extra) - set(DEFAULT_WEIGHTS))
        if unknown:
            print(f"warning: --extra signals {unknown} have no weight and are ignored; use pmi, revisions, equity")
    else:
        print("note: no --extra macro/equity signals; duration_score = (0.35 c2r + 0.20 mom) / 0.55, range +/-1.64:"
              " not a fraction of the risk limit, and the 0.2/0.5 bands do not apply")
    out, _ = build(yl, ys, ym, years, extra, a.n_pairs)
    last = yl.index.max()
    table = pd.DataFrame({k: v.loc[last] for k, v in out.items()}).round(2)
    print(f"as of {last.date()}  (+ = long duration / receive / overweight)")
    print(table.to_string())
    if a.out:
        rows = []
        for k, v in out.items():
            s = v.stack().rename("value").reset_index()
            s.columns = ["date", "curve_id", "value"]
            rows.append(s.assign(strategy_id=f"sys_{k}"))
        res = pd.concat(rows)
        res["package_id"] = res["curve_id"] + f":{a.long_tenor}:outright"
        res["snap"] = snap
        res["unit"] = np.where(res["strategy_id"] == "sys_slope_bp", "bp", "score")
        res[["date", "snap", "strategy_id", "package_id", "value", "unit"]].to_csv(a.out, index=False)
        print(f"wrote {len(res)} rows to {a.out}")
    return 0


# ---------------------------------------------------------------- self-test
def selftest():
    fails = []

    def check(name, ok):
        print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            fails.append(name)

    # 1. par annuity: 10y at 0% = 10; at 5% = (1 - 1.05^-10)/0.05 = 7.72173
    check("par duration", abs(float(par_duration(0.0, 10)) - 10) < 1e-9
          and abs(float(par_duration(5.0, 10)) - 7.721735) < 1e-5)

    # 2. EWMA vol of alternating +/-0.1 returns is exactly 0.1*sqrt(252)
    alt = pd.DataFrame({"a": [0.1, -0.1] * 50})
    check("ewma vol", np.allclose(ewma_vol(alt).values, 0.1 * np.sqrt(PPY)))

    # 2b. EWMA recursion with a known answer: returns [0, 1, 0] -> var = 0.03, then 0.97 x 0.03 (decay 0.97)
    check("ewma recursion", np.allclose(ewma_vol(pd.DataFrame({"a": [0.0, 1.0, 0.0]})).values.ravel()[1:],
                                        np.sqrt(np.array([0.03, 0.0291]) * PPY)))

    # 3. carry-to-risk position: +2 at window high, -2 at window low, 0 at median
    win = pd.DataFrame({"hi": [1, 2, 3, 4, 5.0], "lo": [5, 4, 3, 2, 1.0], "mid": [1, 2, 5, 4, 3.0]})
    pos = c2r_position(win, window=5, min_periods=5).iloc[-1]
    check("c2r position +2/-2/0", np.allclose(pos.values, [2.0, -2.0, 0.0]))

    # 4. momentum sign: falling yields -> rising excess-return index -> +1 (long duration); rising -> -1
    n = 400
    d = pd.bdate_range("2020-01-01", periods=n)
    yl = pd.DataFrame({"bull": np.linspace(5, 3, n), "bear": np.linspace(3, 5, n)}, index=d)
    ys = pd.DataFrame(2.0, index=d, columns=yl.columns)
    idx = excess_return(yl, ys).fillna(0).cumsum()
    m = momentum_signal(idx).iloc[-1]
    check("momentum sign (bull=+1, bear=-1)", m["bull"] == 1 and m["bear"] == -1)
    # disagreement -> 0: long uptrend then a sharp 1m drop that stays above the 12m mean
    path = np.r_[np.linspace(0, 10, 300), np.linspace(10, 9.0, 15)]
    check("momentum neutral when 1m/12m disagree",
          momentum_signal(pd.DataFrame({"x": path})).iloc[-1, 0] == 0)

    # 5. macro momentum: both PMIs fell over 2m -> +1, both rose -> -1, mixed -> 0
    loc = pd.DataFrame({"down": [52, 51, 50.0], "up": [50, 51, 52.0], "mixed": [50, 51, 52.0]})
    glb = pd.Series([51, 50.5, 50.0])
    mm = macro_momentum(loc, glb, 2).iloc[-1]
    loc2 = loc.assign(up=[50, 51, 52.0])
    mm_up = macro_momentum(loc2[["up"]], pd.Series([50, 51, 52.0]), 2).iloc[-1, 0]
    check("macro momentum", mm["down"] == 1 and mm["mixed"] == 0 and mm_up == -1)

    # 6. composite reproduces published per-country combined signals (35/20/15/15/15)
    def comb(rows):
        df = {k: pd.DataFrame([v]) for k, v in rows.items()}
        return combine(df).iloc[0].values

    # JPM, Simple rules to trade duration, Oct 2012: US, JP, EA, UK -> -0.3, +0.1, -0.5, 0.0
    oct12 = comb({"pmi": [-1, -1, -1, -1], "revisions": [-1, 0, 0, 0], "mom": [1, 1, 1, 1],
                  "equity": [-1, 1, -1, -1], "c2r": [-0.2, -0.4, -1.1, 0.4]})
    check("composite = JPM Oct-2012 table", np.all(np.abs(oct12 - [-0.3, 0.1, -0.5, 0.0]) <= 0.05 + 1e-9))
    # JPM systematic update, Jul 2017: EA JP UK US AU CA SE CH NZ NO
    jul17 = comb({"pmi": [0, 1, 1, 0, 1, 1, 1, 0, 0, 0], "revisions": [1, 1, 1, 0, 1, 1, 0, 1, 0, 1],
                  "mom": [-1] * 10, "equity": [-1, -1, -1, -1, 1, 1, -1, -1, -1, -1],
                  "c2r": [0.4, -1.4, -0.7, -0.4, 1.6, -0.6, 1.2, 0.7, 0.3, 1.2]})
    pub17 = np.array([-0.1, -0.5, -0.3, -0.5, 0.8, 0.0, 0.2, 0.0, -0.2, 0.2])
    check("composite = JPM Jul-2017 table", np.all(np.abs(jul17 - pub17) <= 0.05 + 1e-9)
          and abs(jul17.mean()) < 0.05)
    # renormalisation: only c2r (+1) and mom (+1) present -> score 1.0 (weights rescaled to sum 1)
    check("composite renormalises", abs(comb({"c2r": [1.0], "mom": [1.0]})[0] - 1.0) < 1e-12)

    # 7. cross-sectional rank: top-2 +1, bottom-2 -1
    xs = xs_rank_signal(pd.DataFrame([[5, 1, 3, 4, 2, 0.0]], columns=list("ABCDEF")), 2).iloc[0]
    check("xs rank pairs", list(xs.values) == [1, -1, 0, 1, 0, -1])

    # 8. no look-ahead: signals on data[:k] equal full-sample signals before k
    rng = np.random.default_rng(7)
    n = 900
    d = pd.bdate_range("2015-01-01", periods=n)
    cols = ["A", "B", "C", "D", "E"]
    yl = pd.DataFrame(3 + np.cumsum(rng.normal(0, 0.05, (n, 5)), 0), index=d, columns=cols)
    ys = yl - 1 + np.cumsum(rng.normal(0, 0.02, (n, 5)), 0)
    ym = yl - 0.5 + np.cumsum(rng.normal(0, 0.02, (n, 5)), 0)
    full, _ = build(yl, ys, ym, pct_window=500, pct_min=300)
    k = 700
    part, _ = build(yl.iloc[:k], ys.iloc[:k], ym.iloc[:k], pct_window=500, pct_min=300)
    same = all(full[s].iloc[:k].equals(part[s]) or np.allclose(full[s].iloc[:k], part[s], equal_nan=True)
               for s in part)
    hold_full, hold_part = monthly_hold(full["duration_score"]), monthly_hold(part["duration_score"])
    same &= np.allclose(hold_full.iloc[:k], hold_part, equal_nan=True)
    check("no look-ahead (truncation invariance)", same)
    # monthly hold changes only on the first row of a month
    chg = hold_full.diff().abs().sum(axis=1) > 0
    check("monthly hold rebalances only at month start",
          bool((chg[chg].index.to_period("M") != chg[chg].index.shift(-1, freq="B").to_period("M")).all()))
    # nth=1: sampled on the 2nd row of each month, traded from the 3rd
    h2 = monthly_hold(pd.DataFrame({"x": np.arange(len(d), dtype=float)}, index=d), nth=1)["x"]
    feb = d[d.to_period("M") == d[60].to_period("M")]
    check("monthly hold nth=1 (2nd working day)", h2[feb[2]] == d.get_loc(feb[1]) and h2[feb[1]] != h2[feb[2]])

    # 9. excess return, analytic: flat 5% vs 2% -> carry 3/252; a +1bp day -> 3/252 - 7.721735 * 0.01
    er = excess_return(pd.DataFrame({"a": [5.0, 5.0, 5.01]}), pd.DataFrame({"a": [2.0, 2.0, 2.0]}))["a"]
    check("excess return carry and duration", abs(er[1] - 3 / 252) < 1e-12
          and abs(er[2] - (3 / 252 - 7.721735 * 0.01)) < 1e-7)
    # a one-day gap must not swallow the move: 5 -> NaN -> 4 gives the full -1% yield move in the index
    yg = pd.DataFrame({"a": [5.0, 5.0, np.nan, 4.0]})
    _, rg = build(yg, yg * 0 + 5.0, yg * 0 + 5.0, pct_window=3, pct_min=2)
    check("gap bridged (no lost yield move)", abs(rg["a"].sum() - 7.721735) < 1e-5)

    # slope reversal: slope above its trailing mean -> positive (receive the market that steepened)
    sr = slope_reversal(pd.DataFrame({"a": [1.0, 2.0, 4.0]}), window=3).iloc[-1, 0]
    check("slope reversal sign", abs(sr - (4 - 7 / 3)) < 1e-12)
    # a NaN sample must not resurrect the previous month's position
    dd = pd.bdate_range("2021-01-01", "2021-03-31")
    sg = pd.DataFrame({"a": 1.0}, index=dd)
    sg.loc[sg.index[sg.index.month == 2][-1], "a"] = np.nan
    hn = monthly_hold(sg)["a"]
    check("monthly hold NaN sample not stale", hn["2021-03-02"] != hn["2021-03-02"] and hn["2021-02-26"] == 1.0)

    # 10. equity contrarian: equities above 6m mean -> -1 (short duration); below -> +1
    eq = equity_contrarian(pd.DataFrame({"up": np.linspace(100, 120, 130), "dn": np.linspace(120, 100, 130)}))
    check("equity contrarian sign", eq["up"].iloc[-1] == -1 and eq["dn"].iloc[-1] == 1)

    # 11. percentile is NaN (not stale) when today's value is missing
    check("percentile NaN on missing today",
          np.isnan(trailing_percentile(pd.DataFrame({"a": [1, 2, 3, 4, np.nan]}), 5, 3).iloc[-1, 0]))

    # 12. CLI smoke test on a tiny synthetic curve_par (load, pivot, --out in canonical signals format)
    import os, tempfile
    with tempfile.TemporaryDirectory() as td:
        dd = pd.bdate_range("2020-01-01", periods=300)
        rows = [(t, s, "0D", c, ten, lvl + 0.001 * i) for i, t in enumerate(dd) for c in ("X-A", "X-B", "X-C", "X-D")
                for ten, lvl in (("10Y", 3.0), ("3M", 1.0), ("1Y", 1.5)) for s in ("eod",)]
        cp = pd.DataFrame(rows, columns=["date", "snap", "start", "curve_id", "tenor", "par_rate_pct"])
        src, dst = os.path.join(td, "cp.csv"), os.path.join(td, "sig.csv")
        cp.to_csv(src, index=False)
        rc = main(["--curve-par", src, "--n-pairs", "1", "--out", dst])
        res = pd.read_csv(dst)
        ok = rc == 0 and list(res.columns) == ["date", "snap", "strategy_id", "package_id", "value", "unit"]
        ok &= set(res.loc[res.strategy_id == "sys_slope_bp", "value"].round(6)) == {200.0}
        check("CLI end-to-end (curve_par -> signals)", bool(ok))

    print(f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
