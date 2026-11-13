#!/usr/bin/env python3
"""Positioning measures for G10 rate-futures flow analysis.

Library use (pandas / numpy):
    from flow_positioning import release_date, rolling_zscore, rolling_percentile, pit_daily, ...

CLI (canonical `positioning` table as CSV; uses report == cftc_tff rows):
    python scripts/flow_positioning.py --positioning PATH --as-of 2026-11-12 [--window 260]
    python scripts/flow_positioning.py --selftest

Conventions: net = long - short (positive = net long). Timestamps are naive UTC.
Standard deviations use ddof=1. A z-score or percentile needs a full window, else NaN.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


def release_date(as_of, holidays=()):
    """CFTC TFF release day: the as-of Tuesday plus 3 business days (normally Friday).

    Each holiday in `holidays` is not a business day and pushes the release out one day.
    """
    hol = {pd.Timestamp(h).normalize() for h in holidays}
    d = pd.Timestamp(as_of).normalize()
    n = 0
    while n < 3:
        d += pd.Timedelta(days=1)
        if d.weekday() < 5 and d not in hol:
            n += 1
    return d


def rolling_zscore(x, window=260):
    """z_t = (x_t - mean_W) / sd_W over the trailing window W ending at t (t included)."""
    x = pd.Series(x, dtype=float)
    m = x.rolling(window, min_periods=window).mean()
    s = x.rolling(window, min_periods=window).std(ddof=1).replace(0.0, np.nan)
    return (x - m) / s


def rolling_percentile(x, window=260):
    """Share of the trailing window (t included) that is <= the current value, 0..1."""
    x = pd.Series(x, dtype=float)
    return x.rolling(window, min_periods=window).apply(lambda w: np.mean(w <= w[-1]), raw=True)


def pit_daily(values, pub_ts, days):
    """Point-in-time view: each value is visible only from its publication instant.

    values, pub_ts: equal-length sequences; pub_ts are naive UTC timestamps.
    days: DatetimeIndex of cutoff instants (naive UTC). Returns, for each cutoff, the latest
    value published at or before it (NaN before the first release).
    """
    s = pd.Series(np.asarray(values, dtype=float), index=pd.DatetimeIndex(pub_ts)).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    days = pd.DatetimeIndex(days)
    return s.reindex(s.index.union(days)).ffill().reindex(days)


def valuation_adjusted_flow(mv_prev, mv_now, dy, duration=5.0):
    """Valuation-adjusted purchases = dMV + D * MV_prev * dy.

    dy is the yield change in decimal (+10bp = 0.001). A holding whose market value fell only
    because yields rose returns 0 (pure valuation, no trade).
    """
    return (mv_now - mv_prev) + duration * mv_prev * dy


def cumulative_put_call(put_notional, call_notional):
    """Year-to-date put/call = sum(put notional) / sum(call notional). Above 1 = more puts bought.

    NaN when there is no call notional.
    """
    calls = float(np.sum(call_notional))
    return float(np.sum(put_notional)) / calls if calls else float("nan")


def ma_trend_position(price, mas=(22, 66, 200, 252)):
    """Simulated trend-follower position: sum over n of sign(price - SMA_n).

    Range is -len(mas)..+len(mas). Values are NaN until the longest moving average exists.
    """
    price = pd.Series(price, dtype=float)
    out = pd.Series(0.0, index=price.index)
    for n in mas:
        out = out + np.sign(price - price.rolling(n, min_periods=n).mean())
    return out


def swap_trade_upper_bound(hf_ust_long, hf_ust_short):
    """Form PF-style upper bound on the long-cash / pay-fixed-swap trade.

    Long UST exposure minus all short UST exposure (cash-futures basis shorts included).
    """
    return hf_ust_long - hf_ust_short


def sigma_move(returns, lam=0.97):
    """Daily return divided by the prior day's EWMA realised vol (daily units, no annualising).

    var_t = lam * var_{t-1} + (1 - lam) * r_t^2, seeded with r_0^2, so the first value is NaN and the
    scale uses information up to t-1 only. Use a warm-up period before reading early values.
    """
    r = pd.Series(returns, dtype=float)
    out = pd.Series(np.nan, index=r.index)
    if len(r) == 0:
        return out
    v = r.iloc[0] ** 2
    for i in range(1, len(r)):
        if v > 0:
            out.iloc[i] = r.iloc[i] / np.sqrt(v)
        v = lam * v + (1 - lam) * r.iloc[i] ** 2
    return out


CANON_CLASSES = ("asset_manager", "leveraged_funds", "dealer")


def snapshot(df, as_of, window=260, classes=CANON_CLASSES):
    """Latest point-in-time z-score and percentile of net contracts, per contract and class.

    `as_of` is a date (end of that day, UTC) or a timestamp (that instant). Only rows with pub_ts_utc at or
    before it are used, so the result is what was knowable. Where a date has several vintages the latest one
    published by then is used. The window counts weekly observations, so missing weeks stretch it.
    """
    d = df[df["report"].eq("cftc_tff") & df["trader_class"].isin(classes)].copy()
    d["date"] = pd.to_datetime(d["date"])
    d["pub"] = pd.to_datetime(d["pub_ts_utc"], utc=True).dt.tz_localize(None)
    cut = pd.Timestamp(as_of)
    if cut == cut.normalize():
        cut = cut + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    d = d[d["pub"] <= cut]
    d["net"] = d["long_cnt"].astype(float) - d["short_cnt"].astype(float)
    rows = []
    for (con, cls), g in d.sort_values(["date", "pub"]).groupby(["contract", "trader_class"]):
        g = g.drop_duplicates("date", keep="last")
        net = g["net"].to_numpy()
        last = g.iloc[-1]
        rows.append({
            "contract": con,
            "trader_class": cls,
            "as_of_date": last["date"].date(),
            "released_utc": last["pub"],
            "net_cnt": last["net"],
            "z": rolling_zscore(net, window).iloc[-1],
            "pct": rolling_percentile(net, window).iloc[-1],
        })
    return pd.DataFrame(rows)


def selftest():
    """Each check has a known answer. Any failure raises AssertionError (non-zero exit)."""
    # Release: Tue 2026-11-10 + 3 business days = Fri 2026-11-13; a holiday on Wed 11th moves it to Mon 16th.
    assert release_date("2026-11-10") == pd.Timestamp("2026-11-13")
    assert release_date("2026-11-10", holidays=["2026-11-11"]) == pd.Timestamp("2026-11-16")

    # z of the last point of 1..5 over a 5-long window, sample sd: (5 - 3) / sqrt(2.5).
    z = rolling_zscore([1, 2, 3, 4, 5], window=5).iloc[-1]
    assert abs(z - 2 / np.sqrt(2.5)) < 1e-12, z

    # Window [5, 1, 2, 3, 4] ends at 4: four of five values are <= 4, so percentile 0.8.
    p = rolling_percentile([5, 1, 2, 3, 4], window=5).iloc[-1]
    assert abs(p - 0.8) < 1e-12, p

    # Point-in-time: a Friday 20:30 UTC release is invisible at 12:00, visible at 23:00.
    days = pd.DatetimeIndex(["2026-11-13 12:00", "2026-11-13 23:00"])
    v = pit_daily([1.0], ["2026-11-13 20:30"], days)
    assert np.isnan(v.iloc[0]) and v.iloc[1] == 1.0, list(v)

    # Valuation: yields +10bp, D = 5. MV falls 0.5 on 100 from yields alone -> 0 purchases.
    # MV unchanged at 100 -> must have bought 0.5.
    assert abs(valuation_adjusted_flow(100.0, 99.5, 0.001)) < 1e-12
    assert abs(valuation_adjusted_flow(100.0, 100.0, 0.001) - 0.5) < 1e-12

    # Put/call: Jan puts 80, calls 100; Feb puts 110, calls 100 -> (80 + 110) / (100 + 100) = 95%.
    assert abs(cumulative_put_call([80, 110], [100, 100]) - 0.95) < 1e-12

    # A steadily rising price is above every SMA (+4); a falling one is below every SMA (-4).
    ramp = np.arange(300, dtype=float)
    assert ma_trend_position(ramp).iloc[-1] == 4.0
    assert ma_trend_position(-ramp).iloc[-1] == -4.0
    assert ma_trend_position(ramp).iloc[:251].isna().all()  # no position before the longest SMA exists

    # Short history or a constant series gives NaN, never a fake z; a NaN inside the window blocks it too.
    assert rolling_zscore([1, 2, 3], window=5).isna().all()
    assert rolling_zscore([2, 2, 2, 2, 2], window=5).isna().all()
    assert np.isnan(rolling_zscore([1, 2, np.nan, 4, 5], window=5).iloc[-1])
    assert np.isnan(cumulative_put_call([1.0], [0.0]))

    # Sigma move: equal-size moves score 1; a move of 3 after three unit moves scores 3; the EWMA update is 0.97*1 + 0.03*4.
    sm = sigma_move([1, -1, 1, -1])
    assert np.isnan(sm.iloc[0]) and (sm.iloc[1:].abs() == 1.0).all(), list(sm)
    assert abs(sigma_move([1, 1, 1, 3]).iloc[3] - 3.0) < 1e-12
    assert abs(sigma_move([1, 2, 3]).iloc[2] - 3 / np.sqrt(0.97 + 0.03 * 4)) < 1e-12

    # Form PF bound (BIS, Q2 2025, $bn): 2,379 long minus 1,748 short = 631.
    assert swap_trade_upper_bound(2379.0, 1748.0) == 631.0

    # Snapshot on a synthetic weekly table with net = 1..5, released each Friday after the Tuesday as-of.
    dates = ["2026-10-06", "2026-10-13", "2026-10-20", "2026-10-27", "2026-11-03"]
    pubs = ["2026-10-09T20:30:00Z", "2026-10-16T20:30:00Z", "2026-10-23T20:30:00Z",
            "2026-10-30T20:30:00Z", "2026-11-06T20:30:00Z"]
    syn = pd.DataFrame({"date": dates, "pub_ts_utc": pubs, "report": "cftc_tff", "contract": "TY",
                        "trader_class": "asset_manager", "long_cnt": [1, 2, 3, 4, 5], "short_cnt": 0})
    full = snapshot(syn, "2026-11-06", window=5)
    assert abs(full["z"].iloc[0] - 2 / np.sqrt(2.5)) < 1e-12, full
    assert full["net_cnt"].iloc[0] == 5.0
    # Cut off on 5 Nov: the last release is not yet visible, so only four rows exist and z is NaN.
    early = snapshot(syn, "2026-11-05", window=5)
    assert early["net_cnt"].iloc[0] == 4.0 and np.isnan(early["z"].iloc[0]), early
    # A timestamp as-of is an instant: 12:00 on release day is before the 20:30 UTC release, 23:00 is after.
    assert snapshot(syn, "2026-11-06 12:00", window=5)["net_cnt"].iloc[0] == 4.0
    assert snapshot(syn, "2026-11-06 23:00", window=5)["net_cnt"].iloc[0] == 5.0
    # A revision of the last week published later is invisible until its own release.
    rev = pd.concat([syn, syn.iloc[[4]].assign(long_cnt=9, pub_ts_utc="2026-11-10T20:30:00Z")])
    assert snapshot(rev, "2026-11-09", window=5)["net_cnt"].iloc[0] == 5.0
    assert snapshot(rev, "2026-11-10", window=5)["net_cnt"].iloc[0] == 9.0


def main(argv=None):
    ap = argparse.ArgumentParser(description="CFTC TFF point-in-time positioning snapshot.")
    ap.add_argument("--positioning", help="canonical positioning CSV")
    ap.add_argument("--as-of", help="cutoff date YYYY-MM-DD (end of day; only earlier releases are used)")
    ap.add_argument("--window", type=int, default=260,
                    help="trailing observations for z and percentile (260 = 5y of weekly data)")
    ap.add_argument("--selftest", action="store_true", help="run known-answer checks and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        print("selftest OK")
        return 0
    if not a.positioning or not a.as_of:
        ap.error("--positioning and --as-of are required (or use --selftest)")
    df = pd.read_csv(a.positioning)
    out = snapshot(df, a.as_of, a.window)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
