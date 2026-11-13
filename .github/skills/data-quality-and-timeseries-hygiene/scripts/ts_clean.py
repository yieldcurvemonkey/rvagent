"""ts_clean.py - data-quality primitives for rates time series. Flags, never fills.

Pipeline order (matters): calendar audit -> stale rows -> stale runs -> roll stitch -> spike/jump flags.

Library use:
    from ts_clean import audit, stitch_rolls, point_in_time, off_grid, min_run_for
CLI (canonical-style CSV/Parquet, wide panel = date column + one column per series):
    python ts_clean.py audit  --panel panel.csv [--calendar calendars.csv --calendar-id USNY] [--out flags.csv]
    python ts_clean.py stitch --px px.csv --active roll_map.csv [--ratio] [--out stitched.csv]
    python ts_clean.py --selftest
Output flags use the canonical `_common` columns: data_ok (bool) and dq_reason (str). Rows are kept, not deleted.
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- calendar
def calendar_audit(index, holidays=()):
    """(missing, extra): business days absent from `index`, and rows dated on a weekend or holiday."""
    idx = pd.DatetimeIndex(index).normalize()
    bd = pd.offsets.CustomBusinessDay(holidays=[pd.Timestamp(h) for h in holidays])
    expected = pd.date_range(idx.min(), idx.max(), freq=bd)
    return expected.difference(idx), idx.difference(expected)


# ---------------------------------------------------------------- stale
def stale_rows(df, tol=0.0):
    """True where EVERY non-null column is unchanged vs the previous row (vendor carried the prior close)."""
    d = df.diff().abs()
    same = (d <= tol) | d.isna()
    return same.all(axis=1) & d.notna().any(axis=1)


def stale_runs(s, min_run=5, tol=0.0):
    """True for the repeats inside a run of >= min_run equal consecutive observations (first obs of the run is kept)."""
    rep = (s.diff().abs() <= tol).fillna(False)
    run_id = (~rep).cumsum()
    run_len = rep.groupby(run_id).transform("sum") + 1
    return rep & (run_len >= min_run)


def min_run_for(tick, daily_sigma, alpha=1e-4):
    """Smallest run (observations) whose chance under a tick-quantised random walk is < alpha.
    P(unchanged) ~ tick / (sigma * sqrt(2 pi)) when tick << sigma; r repeats have probability p**r."""
    if not (tick > 0 and daily_sigma > 0):
        raise ValueError("tick and daily_sigma must be > 0")
    p = min(0.999, tick / (daily_sigma * math.sqrt(2 * math.pi)))
    return 1 + math.ceil(math.log(alpha) / math.log(p))


# ---------------------------------------------------------------- outliers
def spike_flags(s, window=60, k=6.0, floor=None, revert=0.5, exclude=None):
    """Label each date '' / 'spike' / 'jump' from changes d_t = s_t - s_{t-1}.
    scale = 1.4826 * trailing MAD of d over `window` obs, EXCLUDING the current change, floored (MAD is 0 on tick-
    quantised series). |d_t| > k*scale is 'spike' when d_{t+1} reverses >= (1 - revert) of it (one bad print: only
    date t is labelled, the reversal day is not), otherwise 'jump' (level shift: review, do not delete).
    `exclude` (bool Series) drops stale/known-bad rows before differencing. Warm-up: first window//2 changes unlabelled.
    EX-POST CLEANING ONLY: the spike/jump label for t uses d_{t+1} and the default floor uses the full sample. In a
    backtest or live signal use only the causal test |d_t| > k*scale_t (with an explicit `floor`) at time t."""
    x = s.astype(float)
    if exclude is not None:
        x = x[~exclude.reindex(x.index).fillna(False).to_numpy()]
    x = x.dropna()
    d = x.diff()
    if floor is None:
        nz = d.abs()[d.abs() > 0]
        floor = 0.5 * float(np.percentile(nz, 10)) if len(nz) else 0.0
    med = d.rolling(window, min_periods=window // 2).median()
    mad = (d - med).abs().rolling(window, min_periods=window // 2).median()
    scale = (1.4826 * mad).shift(1).clip(lower=floor)
    big = (d.abs() > k * scale).to_numpy()
    dv = d.to_numpy()
    lab = np.array([""] * len(x), dtype=object)
    i = 1
    while i < len(x):
        if big[i]:
            if i + 1 < len(x) and abs(dv[i] + dv[i + 1]) <= revert * abs(dv[i]):
                lab[i] = "spike"
                i += 2
                continue
            lab[i] = "jump"
        i += 1
    return pd.Series(lab, index=x.index).reindex(s.index, fill_value="")


def off_grid(price, tick, tol=1e-9):
    """True where price is not a whole number of ticks. Use tick = fut_static.tick_size_px (never hard-code):
    a settle that is off-grid while neighbours sit on-grid marks a cash-settled contract's final settlement."""
    q = np.asarray(price, float) / tick
    return pd.Series(np.abs(q - np.round(q)) > tol, index=getattr(price, "index", None))


# ---------------------------------------------------------------- futures roll stitching
def stitch_rolls(px, active, ratio=False):
    """Back-adjusted continuous series from specific-contract prices.
    px: DataFrame date x contract (same snap). active: Series date -> contract held ON that date (roll_map).
    Roll decided at the close of t-1, new contract held from t. gap = P_new(t-1) - P_old(t-1), so the roll-day change
    equals the new contract's own change; no roll jump. Additive by default (rates/spreads/price points can go
    negative); ratio=True multiplies history by P_new/P_old (keeps returns, series stays positive).
    Backward adjustment: the last segment is untouched, so series end == raw end. Returns (series, gaps)."""
    px = px.sort_index()
    active = active.reindex(px.index)
    if active.isna().any():
        raise ValueError("active contract missing on some dates")
    cols = px.columns.get_indexer(active)
    if (cols < 0).any():
        raise ValueError("active contract not in px columns")
    P = px.to_numpy(float)
    adj = P[np.arange(len(px)), cols].copy()
    gaps = {}
    for i in range(1, len(px)):
        if cols[i] != cols[i - 1]:
            new, old = P[i - 1, cols[i]], P[i - 1, cols[i - 1]]
            if np.isnan(new) or np.isnan(old):
                raise ValueError(f"cannot roll on {px.index[i].date()}: both contracts need a price on the prior date")
            if ratio:
                gaps[px.index[i]] = new / old
                adj[:i] *= new / old
            else:
                gaps[px.index[i]] = new - old
                adj[:i] += new - old
    return pd.Series(adj, index=px.index, name="stitched"), pd.Series(gaps, dtype=float, name="gap")


# ---------------------------------------------------------------- point in time
def point_in_time(vint, asof, by="ref_period", ts="pub_ts_utc", val="value"):
    """Value of each `by` key as known at `asof`: latest vintage with pub_ts <= asof. Later revisions are invisible."""
    a = pd.Timestamp(asof)
    a = a.tz_localize("UTC") if a.tzinfo is None else a.tz_convert("UTC")  # naive input = UTC
    t = pd.to_datetime(vint[ts], utc=True)
    v = vint[t <= a].assign(**{ts: t[t <= a]})
    return v.sort_values(ts).groupby(by)[val].last()


# ---------------------------------------------------------------- panel audit
def audit(df, holidays=(), min_run=5, window=60, k=6.0, floor=None):
    """Flag a wide panel (DatetimeIndex x series). Returns (flags, missing_dates).
    flags: data_ok / dq_reason per row. data_ok=False for non-business-day rows, all-unchanged carry-forward rows,
    stale runs and spikes. 'review_jump:<col>' is recorded but leaves data_ok True (level shifts need a human)."""
    df = df.sort_index()
    missing, extra = calendar_audit(df.index, holidays)
    reasons = {t: [] for t in df.index}
    bad = pd.Series(False, index=df.index)
    for t in extra:
        reasons[t].append("non_business_day_row")
        bad[t] = True
    carry = stale_rows(df)
    for t in df.index[carry]:
        reasons[t].append("carry_forward_all_unchanged")
        bad[t] = True
    for c in df.columns:
        run = stale_runs(df[c], min_run)
        for t in df.index[run]:
            reasons[t].append(f"stale:{c}")
            bad[t] = True
        lab = spike_flags(df[c], window, k, floor, exclude=carry | run)
        for t in df.index[lab == "spike"]:
            reasons[t].append(f"spike:{c}")
            bad[t] = True
        for t in df.index[lab == "jump"]:
            reasons[t].append(f"review_jump:{c}")
    out = pd.DataFrame({"data_ok": ~bad, "dq_reason": [";".join(reasons[t]) for t in df.index]}, index=df.index)
    return out, missing


# ---------------------------------------------------------------- I/O + CLI
def _read(path, date_col):
    if str(path).lower().endswith((".parquet", ".pq")):
        try:
            df = pd.read_parquet(path)
        except ImportError as e:  # pyarrow/fastparquet not installed
            raise SystemExit(f"parquet support missing ({e}); convert to CSV") from e
    else:
        df = pd.read_csv(path)
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col).sort_index()


def _holidays(cal_path, cal_id):
    if not cal_path:
        return []
    c = pd.read_csv(cal_path)
    if cal_id:
        c = c[c["calendar_id"] == cal_id]
    return list(pd.to_datetime(c.loc[~c["is_business_day"].astype(str).str.lower().isin(["true", "1"]), "cal_date"]))


def _selftest():
    rng = np.random.default_rng(7)
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok &= bool(cond)

    ts = pd.Timestamp
    # 1 calendar: 23-Dec absent (gap), 25-Dec holiday row, 26-Dec Saturday row
    idx = pd.DatetimeIndex(["2026-12-21", "2026-12-22", "2026-12-24", "2026-12-25", "2026-12-26", "2026-12-28"])
    miss, extra = calendar_audit(idx, [ts("2026-12-25")])
    check("calendar missing", list(miss) == [ts("2026-12-23")])
    check("calendar extra", list(extra) == [ts("2026-12-25"), ts("2026-12-26")])

    # 2 min_run_for: p = 0.01/(0.05*sqrt(2pi)) = 0.0798 ; ceil(ln 1e-4 / ln p) = 4 repeats -> 5 observations
    check("min_run_for", min_run_for(0.01, 0.05, 1e-4) == 5)
    check("min_run_for pinned rate", min_run_for(0.01, 0.01, 1e-4) == 12)  # p = 0.399, ceil(9.21/0.919)=11 repeats

    # 3 stale rows / runs on exact positions
    a = pd.Series([1, 2, 2, 3, 3, 3, 3, 3, 4, 5.0])
    check("stale_runs", list(np.flatnonzero(stale_runs(a, 4))) == [4, 5, 6, 7])
    p = pd.DataFrame({"x": [1, 2, 2, 3.0], "y": [5, 6, 6, 7.0]})
    check("stale_rows", list(stale_rows(p)) == [False, False, True, False])
    p2 = pd.DataFrame({"x": [1, 2, 2, 3.0], "y": [5, 6, 7, 7.0]})  # never ALL columns unchanged on one row
    check("stale_rows needs every column", not stale_rows(p2).any())

    # 4 spikes: random walk, spike at 200 (+30 reverts), one-way jump at 350 (+25)
    n = 500
    w = np.cumsum(rng.normal(0, 1, n))
    w[200] += 30
    w[350:] += 25
    lab = spike_flags(pd.Series(w))
    check("spike exact", list(np.flatnonzero(lab == "spike")) == [200])
    check("jump exact", list(np.flatnonzero(lab == "jump")) == [350])

    # 4b scale must EXCLUDE the current change: tiny window, +/-0.1 steps, +5 spike reverting at t+1
    st = np.cumsum(np.where(np.arange(30) % 2 == 0, 0.1, -0.1))
    st[10] += 5
    lab = spike_flags(pd.Series(st), window=2, floor=0.1)
    check("scale excludes current change", list(np.flatnonzero(lab == "spike")) == [10])

    # 5 tick-quantised, mostly flat (MAD = 0): 1-tick moves not flagged, 40-tick print flagged
    q = np.round(np.cumsum(rng.choice([0, 0, 0, 0, 0.0025, -0.0025], n)) / 0.0025) * 0.0025 + 98.0
    q[120] += 0.10
    lab = spike_flags(pd.Series(q))
    check("quantised no false flags", list(np.flatnonzero(lab == "spike")) == [120] and (lab == "jump").sum() == 0)

    # 6 off-grid settle
    og = off_grid(pd.Series([98.0025, 98.0050, 98.0013]), 0.0025)
    check("off_grid", list(og) == [False, False, True])

    # 7 roll stitching: 3 contracts with different spreads and slopes; stitched change must equal the HELD contract's
    # own change on every date including roll days; end == raw end
    m = 40
    dts = pd.bdate_range("2026-01-05", periods=m)
    u = 100 + np.cumsum(rng.normal(0, 0.2, m))
    t = np.arange(m)
    px = pd.DataFrame({"A": u + 0.30 + 0.010 * t, "B": u + 0.80 - 0.020 * t, "C": u + 1.50 + 0.015 * t}, index=dts)
    held = np.array(["A"] * 12 + ["B"] * 14 + ["C"] * 14)
    act = pd.Series(held, index=dts)
    own = np.array([px.at[d, c] for d, c in zip(dts, held)])
    s, g = stitch_rolls(px, act)
    exp = np.diff(px.to_numpy()[np.arange(m), px.columns.get_indexer(held)])
    exp[11] = px.at[dts[12], "B"] - px.at[dts[11], "B"]
    exp[25] = px.at[dts[26], "C"] - px.at[dts[25], "C"]
    check("stitch additive changes", np.allclose(np.diff(s.to_numpy()), exp))
    check("stitch end == raw end", np.isclose(s.iloc[-1], own[-1]) and len(g) == 2)
    r, _ = stitch_rolls(px, act, ratio=True)
    ret_s = r.to_numpy()[1:] / r.to_numpy()[:-1] - 1
    ret_h = np.array([px.at[dts[i], held[i]] / px.at[dts[i - 1], held[i]] - 1 for i in range(1, m)])
    check("stitch ratio returns", np.allclose(ret_s, ret_h) and bool((r > 0).all()))

    # 8 point-in-time: first print 0.2, revised 0.5 later; as-of between the two sees 0.2
    v = pd.DataFrame({"ref_period": ["2026-Q1", "2026-Q1"], "value": [0.2, 0.5],
                      "pub_ts_utc": pd.to_datetime(["2026-04-29T12:30:00Z", "2026-05-29T12:30:00Z"])})
    check("pit first print", point_in_time(v, "2026-05-01T00:00:00Z")["2026-Q1"] == 0.2)
    check("pit revision", point_in_time(v, "2026-06-01T00:00:00Z")["2026-Q1"] == 0.5)
    check("pit release instant inclusive", point_in_time(v, "2026-05-29T12:30:00Z")["2026-Q1"] == 0.5)
    check("pit before release empty", len(point_in_time(v, "2026-04-29T12:29:59Z")) == 0)

    # 9 end-to-end audit with injected defects at known dates
    days = pd.bdate_range("2025-01-01", periods=330)
    hol = days[150]
    days = days.delete(150)
    base = pd.DataFrame(np.cumsum(rng.normal(0, 0.05, (len(days), 3)), axis=0) + 4.0, index=days, columns=list("abc"))
    base["a"] = np.round(base["a"], 4)
    base.iloc[200:206, 1] = base.iloc[200, 1]  # stale run in b: obs 200..205 -> flags 201..205
    base.iloc[250, 2] = base.iloc[249, 2] + 3.0  # one-day spike in c, reverts next day
    base.iloc[251, 2] = base.iloc[249, 2] + 0.01
    prev = base.loc[days[days < hol][-1]]
    base.loc[hol] = prev.to_numpy()  # carry-forward row on a holiday
    base = base.sort_index()
    fl, miss = audit(base, holidays=[hol], min_run=5)
    bad = set(fl.index[~fl["data_ok"]])
    want = {hol} | set(days[201:206]) | {days[250]}
    check("audit flagged set exact", bad == want)
    check("audit reasons", "carry_forward_all_unchanged" in fl.at[hol, "dq_reason"] and "spike:c" in fl.at[days[250], "dq_reason"])
    check("audit no missing", len(miss) == 0)
    # 10 catch-up move after a long stale run must not be flagged (stale rows are excluded from the MAD window)
    wk = np.cumsum(rng.normal(0, 1, 260))
    wk[100:140] = wk[100]
    wk[140:] = wk[140:] - wk[140] + wk[100] + 3.0
    fl2, _ = audit(pd.DataFrame({"x": wk}, index=pd.bdate_range("2025-01-01", periods=260)), min_run=5)
    check("catch-up after stale run not flagged", "review_jump" not in fl2.dq_reason.iloc[140] and fl2.data_ok.iloc[140] and (~fl2.data_ok).sum() == 39)
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("audit")
    a.add_argument("--panel", required=True)
    a.add_argument("--date-col", default="date")
    a.add_argument("--calendar")
    a.add_argument("--calendar-id")
    a.add_argument("--min-run", type=int, default=5)
    a.add_argument("--window", type=int, default=60)
    a.add_argument("--k", type=float, default=6.0)
    a.add_argument("--floor", type=float)
    a.add_argument("--out")
    s = sub.add_parser("stitch")
    s.add_argument("--px", required=True, help="wide: date + one column per specific contract")
    s.add_argument("--active", required=True, help="roll_map shape: date, instrument_id")
    s.add_argument("--date-col", default="date")
    s.add_argument("--ratio", action="store_true")
    s.add_argument("--out")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.cmd == "audit":
        df = _read(args.panel, args.date_col)
        fl, miss = audit(df, _holidays(args.calendar, args.calendar_id), args.min_run, args.window, args.k, args.floor)
        print(f"rows={len(df)} flagged={int((~fl.data_ok).sum())} missing_business_days={len(miss)}")
        for t in miss:
            print("missing", t.date())
        print(fl[fl.dq_reason != ""].to_string())
        if args.out:
            fl.to_csv(args.out, index_label=args.date_col)
        return 0
    if args.cmd == "stitch":
        px = _read(args.px, args.date_col)
        act = _read(args.active, args.date_col)["instrument_id"]
        ser, gaps = stitch_rolls(px, act, args.ratio)
        print(gaps.to_string() if len(gaps) else "no rolls")
        (ser.to_csv(args.out, index_label=args.date_col) if args.out else print(ser.tail().to_string()))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
