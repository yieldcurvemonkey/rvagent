"""Seasonality and calendar-effect tests for rates series.

Functions take pandas Series indexed by business-day dates (daily changes in bp unless stated).

  monthly_screen   month-of-year screen: month x year sums, mean/median/trimmed, t and Wilcoxon vs all months,
                   up-ratio with binomial p, expected false flags (alpha x 12)
  window_study     event-window study (month-end, quarter-end, auction dates ...): per-offset mean, window excess
                   over the non-window baseline, t-stat across events, placebo p-value from shifted dates
  seasonal_factors ratio-to-centred-moving-average seasonal factors (% of trend, sum to zero) for a monthly NSA index
  sa_price         seasonally adjusted linker price  SAP = P * Sv / Sm
  ff_year_end_decomp  Fed-funds-futures decomposition into two FOMC steps and the year-end premium

CLI:
  python seasonality.py screen  --csv curve_par.csv --value-col par_rate_pct --where curve_id=USD-SOFR --where tenor=10Y
                                --where start=0D --scale 100 --diff --drop-roll
  python seasonality.py weekday --csv x.csv --value-col value --diff
  python seasonality.py window  --csv x.csv --value-col value --diff --events month_end --lo -3 --hi 1
  python seasonality.py window  --csv x.csv ... --events auctions.csv --event-date-col auction_date --event-where issuer=US
  python seasonality.py --selftest
--where col=value (repeatable) filters a long canonical table to one series (case-insensitive string match; booleans as
true/false); --scale multiplies values (100 turns a _pct column into bp). Up = change > 0 (a yield sell-off, a steeper
longer-minus-shorter spread, a wider spread in the stored sign convention). CSV or Parquet.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ----------------------------------------------------------------------------------------------- helpers
def roll_window_mask(index: pd.DatetimeIndex, expiry_months=(3, 6, 9, 12), day_from=6, day_to=10) -> pd.Series:
    """True on days to drop around a futures roll (default: 6th-10th of expiry months, as roll sits 2bd before expiry)."""
    m = index.month.isin(expiry_months) & (index.day >= day_from) & (index.day <= day_to)
    return pd.Series(m, index=index)


def period_end_events(index: pd.DatetimeIndex, kind: str = "month_end") -> pd.DatetimeIndex:
    """Last trading day in `index` of each month / quarter / year. Incomplete final month is dropped.
    ponytail: assumes the series holds every business day; pass explicit dates from the calendars table otherwise."""
    s = pd.Series(index, index=index)
    last = s.groupby([index.year, index.month]).max()
    ev = pd.DatetimeIndex(last.values)
    if len(ev) and ev[-1] == index[-1] and ev[-1].day < 25:
        ev = ev[:-1]
    if kind == "quarter_end":
        ev = ev[ev.month.isin([3, 6, 9, 12])]
    elif kind == "year_end":
        ev = ev[ev.month == 12]
    elif kind != "month_end":
        raise ValueError(kind)
    return ev


def _clean(x: pd.Series) -> pd.Series:
    x = pd.Series(x).dropna()
    x.index = pd.DatetimeIndex(x.index)
    return x.sort_index()


# ---------------------------------------------------------------------------------------- month-of-year
def monthly_screen(changes: pd.Series, drop_mask: pd.Series | None = None, alpha: float = 0.10,
                   min_obs: int = 10, trims=(0.0, 0.10, 0.25, 0.50), up_hi: float = 0.70, up_lo: float = 0.30):
    """Returns (table, month_year_sums). Table index = month 1..12.

    H0: month's move equals the move in all months. t-test on the mean of yearly sums vs the pooled mean,
    Wilcoxon signed-rank on (yearly sums - pooled median). Months-years with < min_obs observations are dropped.
    low_n marks months with < 10 usable years (tests have little power; do not read the flags).
    trim_{p} = scipy trimmed mean cutting p from each tail (0 = mean, 0.5 -> median).
    """
    x = _clean(changes)
    if drop_mask is not None:
        x = x[~drop_mask.reindex(x.index).fillna(False).astype(bool)]
    g = x.groupby([x.index.year, x.index.month])
    ms = g.sum()[g.count() >= min_obs].unstack()  # year x month
    ms = ms.reindex(columns=range(1, 13))
    allv = ms.stack().to_numpy()
    if len(allv) < 12:
        raise ValueError(f"only {len(allv)} usable month-years: need a longer history (>= 10 years per month)")
    mu, med = allv.mean(), np.median(allv)
    rows = {}
    for m in range(1, 13):
        v = ms[m].dropna().to_numpy()
        n = len(v)
        if n < 4:
            continue
        r = dict(n=n, low_n=n < 10, mean=v.mean(), median=np.median(v), std=v.std(ddof=1), up_ratio=(v > 0).mean())
        for t in trims:
            r[f"trim{int(t * 100)}"] = stats.trim_mean(v, min(t, 0.4999)) if t < 0.5 else np.median(v)
        r["p_t"] = stats.ttest_1samp(v, mu).pvalue
        d = v - med
        r["p_w"] = stats.wilcoxon(d).pvalue if np.any(d != 0) else 1.0
        r["p_binom"] = stats.binomtest(int((v > 0).sum()), n, 0.5).pvalue
        r["flag_up_ratio"] = "UP" if r["up_ratio"] >= up_hi else ("DOWN" if r["up_ratio"] <= up_lo else "")
        r["flag_sig"] = bool(r["p_t"] < alpha and r["p_w"] < alpha)
        r["sigma_over_mu"] = r["std"] / abs(r["mean"]) if r["mean"] != 0 else np.inf
        rows[m] = r
    if not rows:
        raise ValueError("no month has >= 4 usable years")
    tab = pd.DataFrame(rows).T.infer_objects()
    tab.attrs["expected_false_flags"] = alpha * len(tab)
    tab.attrs["n_flagged"] = int(tab["flag_sig"].sum())
    return tab, ms


def weekday_screen(changes: pd.Series, alpha: float = 0.10, min_obs: int = 100) -> pd.DataFrame:
    """Day-of-week screen: per weekday n, mean, median, std, up-ratio, t vs the median of the OTHER four weekdays' means, Wilcoxon vs
    the median of their medians (with only 5 groups a pooled benchmark is contaminated by one strong day; the median of
    group statistics is not). Expect alpha x 5 false flags per series. Daily changes are autocorrelated around events: treat p-values as optimistic."""
    x = _clean(changes)
    x = x[x.index.dayofweek < 5]
    rows = {}
    for d, v in x.groupby(x.index.dayofweek):
        if len(v) < min_obs:
            continue
        rest = x[x.index.dayofweek != d].groupby(x.index[x.index.dayofweek != d].dayofweek)
        mu, med = rest.mean().median(), rest.median().median()
        dm = v.to_numpy() - med
        rows[d] = dict(n=len(v), mean=v.mean(), median=v.median(), std=v.std(ddof=1), up_ratio=(v > 0).mean(),
                       p_t=stats.ttest_1samp(v, mu).pvalue, p_w=stats.wilcoxon(dm[dm != 0]).pvalue if np.any(dm != 0) else 1.0)
        rows[d]["flag_sig"] = bool(rows[d]["p_t"] < alpha and rows[d]["p_w"] < alpha)
    if not rows:
        raise ValueError(f"no weekday has >= {min_obs} observations")
    tab = pd.DataFrame(rows).T.infer_objects()
    tab.index = [["Mon", "Tue", "Wed", "Thu", "Fri"][int(i)] for i in tab.index]
    tab.attrs["expected_false_flags"] = alpha * len(tab)
    tab.attrs["n_flagged"] = int(tab["flag_sig"].sum())
    return tab


# ------------------------------------------------------------------------------------------ event windows
def _event_matrix(x: pd.Series, events, pre: int, post: int, snap: str = "forward") -> tuple[np.ndarray, list]:
    ev = pd.DatetimeIndex(events)
    # event on a non-trading day -> next trading day (auctions, settlements) or previous one (period-ends)
    pos = x.index.searchsorted(ev) if snap == "forward" else x.index.searchsorted(ev, side="right") - 1
    # several event dates can snap to one trading day (a holiday on Sat and Sun): count that day once
    ok = sorted({int(p) for p in pos if p - pre >= 0 and p + post < len(x)})
    vals = x.to_numpy()
    return np.array([vals[p - pre:p + post + 1] for p in ok]), ok


def window_study(changes: pd.Series, events, pre: int = 5, post: int = 5, lo: int | None = None,
                 hi: int | None = None, placebo_shifts: int = 20, snap: str = "forward",
                 placebo_exclude=(20, 21, 22, 23)):
    """Event-window study. Offset 0 = event day (e.g. last business day of the month).

    Returns (by_offset, summary). by_offset: mean change per offset, t across events, n.
    summary: window [lo,hi] mean total, baseline-adjusted excess (baseline = mean daily change outside all
    +/-(pre..post) windows x window length), t-stat across events, placebo p (event dates shifted by +/-w..+/-(w+shifts)
    business days, w = window width; p = (1+#{|placebo mean| >= |observed|})/(1+N)). N is about 2*placebo_shifts, so the
    smallest reportable p is about 1/(1+N) (0.024 for 40 shifts): never quote a tighter threshold. Shifts with
    |shift| in placebo_exclude (about one month) are skipped because month-end events recur every ~21 bdays.
    snap: 'forward' or 'backward' for event dates that are not trading days in the series.
    The change at offset k is close(k) - close(k-1), so [lo, hi] is a position entered at the close of day lo-1 and
    exited at the close of day hi ("enter 3 days before, exit 1 after" = lo=-2, hi=1).
    """
    x = _clean(changes)
    lo = -pre if lo is None else lo
    hi = post if hi is None else hi
    E, ok = _event_matrix(x, events, pre, post, snap)
    off = np.arange(-pre, post + 1)
    n = E.shape[0]
    if n < 5:
        raise ValueError(f"only {n} usable events: need at least 5 (more than 30 for a claim)")
    se = E.std(axis=0, ddof=1) / np.sqrt(n)
    by = pd.DataFrame({"mean": E.mean(0), "t": E.mean(0) / se, "n": n}, index=off)
    inwin = np.zeros(len(x), bool)
    for p in ok:
        inwin[p - pre:p + post + 1] = True
    base = x.to_numpy()[~inwin].mean()
    w = hi - lo + 1
    cols = (off >= lo) & (off <= hi)
    S = E[:, cols].sum(1)
    ex = S - w * base
    t = ex.mean() / (ex.std(ddof=1) / np.sqrt(n))
    vals = x.to_numpy()
    plc = []
    for s in list(range(-(w + placebo_shifts), -w)) + list(range(w + 1, w + placebo_shifts + 1)):
        if abs(s) in placebo_exclude:
            continue
        q = [p + s + lo for p in ok if p + s + lo >= 0 and p + s + hi < len(x)]
        if len(q) >= max(5, n // 2):
            plc.append(np.mean([vals[a:a + w].sum() for a in q]))
    plc = np.array(plc)
    p_pl = (1 + (np.abs(plc) >= abs(S.mean())).sum()) / (1 + len(plc)) if len(plc) else np.nan
    summ = dict(n_events=n, window=(lo, hi), mean_total=S.mean(), baseline_per_day=base, excess=ex.mean(), t_excess=t,
                hit_rate=float((ex > 0).mean()), p_placebo=p_pl)
    return by, summ


# ---------------------------------------------------------------------------------- seasonal factors etc
def seasonal_factors(nsa: pd.Series) -> pd.Series:
    """Seasonal factors (% deviation from trend, sum to 0) of a monthly NSA index level.
    Trend = centred 2x12 moving average; factor_m = mean over years of 100*(x/trend - 1), then demeaned.
    ponytail: ratio-to-MA, no Easter/moving-feast handling; use X-13/STL when available."""
    x = _clean(nsa)
    if len(x) < 36 or (np.diff(x.index.year * 12 + x.index.month) != 1).any():
        raise ValueError("need >= 36 contiguous monthly observations")
    trend = _centred_2x12(x)
    dev = 100 * (x / trend - 1)
    f = dev.dropna().groupby(dev.dropna().index.month).mean().reindex(range(1, 13))
    return f - f.mean()


def _centred_2x12(x: pd.Series) -> pd.Series:
    """Centred 2x12 moving average: value at t = mean of x[t-6..t+6] with half weight on the two ends."""
    ma = x.rolling(12).mean()  # window ending at t covers t-11..t, centre t-5.5
    return (ma + ma.shift(-1)).div(2).shift(-5)  # ending at t+5 and t+6 -> centred on t


def sa_price(price, s_value, s_maturity):
    """Seasonally adjusted real price: SAP = P * Sv / Sm (seasonal index at value date / at maturity reference month)."""
    return price * s_value / s_maturity


def ff_futures_from_steps(ff_nov, d_dec, d_jan, ye, dec_days=(11, 20), jan_days=(29, 2)):
    """Monthly-average FF futures for Dec, Jan, Feb (inputs and outputs in the same unit, pct or bp).
    ff_nov: expected average rate for Nov (the pre-December rate); d_dec, d_jan: FOMC steps; ye: year-end excess,
    positive = overnight rate above the neighbouring days, applied only to the post-FOMC part of December.
    dec_days = (days before, days from the Dec meeting-effective day); jan_days likewise for the Jan meeting.
    Defaults = one specific calendar (Dec meeting effective 12 Dec, Jan meeting effective 30 Jan): re-derive weights
    for any other calendar by passing the day counts."""
    a, b = dec_days
    c, d = jan_days
    dec = (a * ff_nov + b * (ff_nov + d_dec + ye)) / (a + b)
    jan = (c * (ff_nov + d_dec) + d * (ff_nov + d_dec + d_jan)) / (c + d)
    feb = ff_nov + d_dec + d_jan
    return dec, jan, feb


def ff_year_end_decomp(ff_nov, ff_dec, ff_jan, ff_feb, dec_days=(11, 20), jan_days=(29, 2)):
    """Invert ff_futures_from_steps. Returns (d_dec, d_jan, ye) in the input unit; ye > 0 = year-end premium.
    Linear in the four futures, so the weights on (Nov, Dec, Jan, Feb) are the DV01 ratios of a package with exposure
    to ye only; defaults give (-11/20, 31/20, -31/29, 2/29)."""
    a, b = dec_days
    c, d = jan_days
    nd, nj = a + b, c + d
    d_jan = (ff_feb - ff_jan) / (1 - d / nj)
    d_dec = ff_jan - ff_nov - d / nj * d_jan
    ye = nd / b * (ff_dec - ff_nov) - d_dec
    return d_dec, d_jan, ye


# ------------------------------------------------------------------------------------------------ selftest
def _selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name} {info}")
        ok &= bool(cond)

    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2005-01-03", "2024-12-31")

    # 1. monthly screen: inject +1bp/day in January (about +22bp per Jan) into 3bp/day noise
    x = pd.Series(rng.normal(0, 3, len(idx)), idx)
    x[idx.month == 1] += 1.0
    tab, _ = monthly_screen(x)
    check("screen finds injected Jan", tab.loc[1, "flag_sig"] and 14 < tab.loc[1, "mean"] < 30 and tab.loc[1, "p_t"] < 0.01,
          f"mean={tab.loc[1, 'mean']:.1f} p_t={tab.loc[1, 'p_t']:.4f}")
    check("screen: few false flags elsewhere", tab["flag_sig"].drop(1).sum() <= 3, f"n={tab['flag_sig'].drop(1).sum()}")
    null = pd.Series(rng.normal(0, 3, len(idx)), idx)
    tn, _ = monthly_screen(null)
    check("screen null: flagged <= 4 of 12 (expect ~1.2)", tn.attrs["n_flagged"] <= 4, f"flagged={tn.attrs['n_flagged']}")

    # 1b. weekday screen: inject +1bp on Fridays into 3bp noise (2,600 Fridays -> clear)
    w = pd.Series(rng.normal(0, 3, len(idx)), idx)
    w[idx.dayofweek == 4] += 1.0
    tw = weekday_screen(w)
    check("weekday screen finds injected Friday", tw.loc["Fri", "flag_sig"] and 0.7 < tw.loc["Fri", "mean"] < 1.3 and tw["flag_sig"].drop("Fri").sum() <= 1,
          f"Fri mean={tw.loc['Fri', 'mean']:.2f}")
    tn5 = weekday_screen(null)
    check("weekday null: <= 2 of 5 flagged", tn5.attrs["n_flagged"] <= 2, f"flagged={tn5.attrs['n_flagged']}")

    # 2. window study: +2bp on each of offsets -2,-1 before month-end (+4bp total over [-2,-1])
    y = pd.Series(rng.normal(0.3, 2, len(idx)), idx)  # +0.3bp/day drift: baseline subtraction must remove 0.6 over 2 days
    ev = period_end_events(idx)
    pos = idx.searchsorted(ev)
    for k in (-2, -1):
        y.iloc[[p + k for p in pos if p + k < len(y)]] += 2.0
    by, s = window_study(y, ev, pre=5, post=3, lo=-2, hi=-1)
    check("window recovers +4bp net of drift", abs(s["excess"] - 4.0) < 0.6 and s["mean_total"] - s["excess"] > 0.4
          and s["t_excess"] > 5 and s["p_placebo"] < 0.05,
          f"excess={s['excess']:.2f} t={s['t_excess']:.1f} p_pl={s['p_placebo']:.3f}")
    _, s0 = window_study(null, ev, pre=5, post=3, lo=-2, hi=-1)
    check("window null not significant", abs(s0["t_excess"]) < 3 and s0["p_placebo"] > 0.02,
          f"t={s0['t_excess']:.1f} p_pl={s0['p_placebo']:.3f}")
    check("event dates = last bday", all(d in idx and (idx[idx.searchsorted(d) + 1].month != d.month) for d in ev[:-1]))

    # 3. seasonal factors: inject known factors on a 2%/yr trend
    f_true = np.array([-0.7, -0.5, 0.1, 0.4, 0.4, 0.35, -0.1, -0.1, 0.1, 0.1, -0.1, 0.0])
    f_true -= f_true.mean()
    mi = pd.date_range("2005-01-01", periods=15 * 12, freq="MS")
    lvl = 100 * np.exp(0.02 / 12 * np.arange(len(mi))) * (1 + f_true[mi.month - 1] / 100)
    est = seasonal_factors(pd.Series(lvl * np.exp(rng.normal(0, 0.0003, len(mi))), mi))
    lin = pd.Series(np.arange(48.0), mi[:48])
    check("2x12 trend is centred (linear series reproduced exactly)", np.allclose((_centred_2x12(lin) - lin).dropna(), 0))
    kink = pd.Series(np.where(np.arange(len(mi)) < 90, 100.0, 100 + 2.0 * (np.arange(len(mi)) - 90)), mi)  # trend with a kink, no seasonality
    check("seasonal factors ~0 on a seasonality-free kinked trend", np.abs(seasonal_factors(kink)).max() < 0.15,
          f"max={np.abs(seasonal_factors(kink)).max():.3f}")
    check("seasonal factors recovered", np.abs(est.to_numpy() - f_true).max() < 0.08, f"maxerr={np.abs(est.to_numpy() - f_true).max():.3f}")

    # 4. linker SAP and FF decomposition against hand-computed numbers
    check("SAP = 100*1.01/0.99", abs(sa_price(100, 1.01, 0.99) - 102.020202) < 1e-5)
    dec, jan, feb = ff_futures_from_steps(2.00, 0.25, 0.25, 0.05)
    check("FF Dec/Jan/Feb hand values", abs(dec - 2.193548) < 1e-5 and abs(jan - 2.266129) < 1e-5 and abs(feb - 2.5) < 1e-12,
          f"{dec:.6f} {jan:.6f} {feb:.3f}")
    dd, dj, ye = ff_year_end_decomp(2.00, dec, jan, feb)
    check("FF decomposition inverts", abs(dd - 0.25) < 1e-9 and abs(dj - 0.25) < 1e-9 and abs(ye - 0.05) < 1e-9, f"{dd:.4f} {dj:.4f} {ye:.4f}")
    dec2, jan2, feb2 = ff_futures_from_steps(2.00, 0.25, -0.25, -0.04, (15, 16), (28, 3))
    r = ff_year_end_decomp(2.00, dec2, jan2, feb2, (15, 16), (28, 3))
    check("FF decomposition inverts for another calendar", np.allclose(r, (0.25, -0.25, -0.04)), f"{np.round(r, 4)}")
    ex_idx = pd.bdate_range("2020-11-20", "2020-12-10")
    _, ok_b = _event_matrix(pd.Series(0.0, ex_idx), [pd.Timestamp("2020-11-29")], 1, 1, "backward")
    _, ok_f = _event_matrix(pd.Series(0.0, ex_idx), [pd.Timestamp("2020-11-29")], 1, 1, "forward")
    check("snap backward/forward on a Sunday", ex_idx[ok_b[0]] == pd.Timestamp("2020-11-27") and ex_idx[ok_f[0]] == pd.Timestamp("2020-11-30"))
    return 0 if ok else 1


# --------------------------------------------------------------------------------------------------- CLI
def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


def _where(df: pd.DataFrame, filters) -> pd.DataFrame:
    for f in filters or []:
        col, val = f.split("=", 1)
        df = df[df[col].astype(str).str.lower() == val.lower()]
    return df


def _load(a) -> pd.Series:
    df = _where(_read(a.csv), a.where)
    if df.empty:
        raise SystemExit("no rows left after --where filters")
    s = pd.Series(df[a.value_col].to_numpy(float) * a.scale, pd.to_datetime(df[a.date_col]))
    if s.index.duplicated().any():
        raise SystemExit("duplicate dates: add --where filters until one series remains (curve_id, tenor, start, snap ...)")
    s = _clean(s)
    return s.diff().dropna() if a.diff else s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("screen", "weekday", "window"):
        p = sub.add_parser(name)
        p.add_argument("--csv", required=True, help="CSV or Parquet with a date column and a value column")
        p.add_argument("--where", action="append", help="col=value filter selecting one series; repeatable")
        p.add_argument("--scale", type=float, default=1.0, help="multiply values (100 converts a _pct column to bp)")
        p.add_argument("--date-col", default="date")
        p.add_argument("--value-col", default="value")
        p.add_argument("--diff", action="store_true", help="input is a level; take first differences")
        if name == "screen":
            p.add_argument("--alpha", type=float, default=0.10)
            p.add_argument("--drop-roll", action="store_true", help="drop 6th-10th of Mar/Jun/Sep/Dec")
        else:
            p.add_argument("--events", default="month_end", help="month_end|quarter_end|year_end|<csv/parquet path>")
            p.add_argument("--event-where", action="append", help="col=value filter on the events table; repeatable")
            p.add_argument("--pre", type=int, default=5)
            p.add_argument("--post", type=int, default=5)
            p.add_argument("--event-date-col", default="date", help="date column in the events CSV (auction_date, cal_date ...)")
            p.add_argument("--snap", default="forward", choices=["forward", "backward"],
                           help="non-trading event dates: next (auctions) or previous (period-ends) trading day")
            p.add_argument("--lo", type=int, default=None)
            p.add_argument("--hi", type=int, default=None)
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.cmd is None:
        ap.print_help()
        return 2
    x = _load(a)
    pd.set_option("display.width", 200)
    if a.cmd == "weekday":
        tab = weekday_screen(x)
        print(tab.round(3).to_string())
        print(f"flagged {tab.attrs['n_flagged']} of {len(tab)}; expected by chance {tab.attrs['expected_false_flags']:.1f}")
    elif a.cmd == "screen":
        tab, _ = monthly_screen(x, roll_window_mask(x.index) if a.drop_roll else None, alpha=a.alpha)
        tab.index = [MONTHS[m - 1] for m in tab.index]
        print(tab.round(3).to_string())
        print(f"flagged {tab.attrs['n_flagged']} of {len(tab)}; expected by chance {tab.attrs['expected_false_flags']:.1f}")
    else:
        if a.events in ("month_end", "quarter_end", "year_end"):
            ev = period_end_events(x.index, a.events)
        else:
            ev = pd.DatetimeIndex(pd.to_datetime(_where(_read(a.events), a.event_where)[a.event_date_col]))
        by, s = window_study(x, ev, a.pre, a.post, a.lo, a.hi, snap=a.snap)
        print(by.round(3).to_string())
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
