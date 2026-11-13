"""Event-window entry/exit grid for supply and cash-flow trades (auctions, redemptions, coupons, buybacks).

For every event date T and every (entry, exit) pair of trading-day offsets, the trade P&L in bp is
    pnl = direction * (x[T + exit] - x[T + entry])
where x is a level series in bp (yield, curve spread, fly, curve-adjusted spread vs Germany, ASW).
direction = +1 profits when x RISES (short the bond / pay the spread: pre-auction concession short on a
yield or a cheapening spread); direction = -1 profits when x FALLS (post-auction or reinvestment long).
Offsets count rows of the series (trading days), so T-5 = five trading days before the event.
An event that is not a trading day maps to the next trading day. Events whose window leaves the
sample are dropped for that cell (no look-ahead, no padding).

Per cell: n, mean_bp, median_bp, hit (share of pnl > 0), sharpe = mean/std (per trade, ddof=1),
score = hit * sharpe (BofA auction-grid ranking), ir_ann = sharpe * sqrt(events per year).

CLI (canonical tables from data-contract-and-adapters, or a wide CSV: date + one column per series):
    python supply_event_grid.py --file curve_par.parquet --snap eod_ny \
        --series "USD-GOVT-US|0D|2Y,USD-GOVT-US|0D|10Y" --weights=-1,1 \
        --auctions auctions.csv --issuer US --instruments BOND:US91282CXX00 \
        --entries=-10:0 --exits=-5:10 --direction 1
    python supply_event_grid.py --file wide.csv --series my_spread --events 2026-01-14,2026-02-11
    python supply_event_grid.py --selftest
Series ids: `curve_id|start|tenor` (curve_par, par_rate_pct x100), instrument_id (bond_quotes, ytm_pct x100),
`curve_id|measure|ref` (swap_spreads, value_bp), or a column name of a wide file (taken as bp).
Output: JSON on stdout (ASCII only), cells sorted by score.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np
import pandas as pd


def event_positions(index: pd.Index, events) -> np.ndarray:
    """Row position of each event in a sorted DatetimeIndex; non-trading days roll to the next row."""
    idx = pd.DatetimeIndex(index)
    ev = pd.DatetimeIndex(pd.to_datetime(list(events))).sort_values().unique()
    ev = ev[ev >= idx[0]] if len(idx) else ev  # events before the sample start must not map to row 0
    pos = idx.searchsorted(ev, side="left")
    return pos[pos < len(idx)]


def event_window_pnl(x: pd.Series, events, entry: int, exit: int, direction: int = 1) -> pd.Series:
    """Per-event P&L in bp for one (entry, exit) cell. Requires entry < exit."""
    if entry >= exit:
        raise ValueError("entry offset must be before exit offset")
    x = x.sort_index()
    v = x.to_numpy(dtype=float)
    out = {}
    for p in event_positions(x.index, events):
        a, b = p + entry, p + exit
        if a < 0 or b >= len(v) or np.isnan(v[a]) or np.isnan(v[b]):
            continue
        out[x.index[p]] = direction * (v[b] - v[a])
    return pd.Series(out, dtype=float, name=f"{entry}->{exit}")


def event_grid(x: pd.Series, events, entries, exits, direction: int = 1,
               events_per_year: float | None = None) -> pd.DataFrame:
    """Grid of event-window statistics; one row per (entry, exit) with entry < exit."""
    if events_per_year is None:
        pos = event_positions(x.sort_index().index, events)
        dates = pd.DatetimeIndex(x.sort_index().index[pos])
        span = (dates.max() - dates.min()).days / 365.25 if len(dates) > 1 else 0.0
        events_per_year = (len(dates) - 1) / span if span > 0 else 12.0
    rows = []
    for e in entries:
        for f in exits:
            if e >= f:
                continue
            p = event_window_pnl(x, events, e, f, direction)
            n = len(p)
            mean = float(p.mean()) if n else math.nan
            sd = float(p.std(ddof=1)) if n > 1 else math.nan
            sharpe = mean / sd if sd and sd > 1e-9 else math.nan  # float-noise sd (identical pnl) is not a Sharpe
            hit = float((p > 0).mean()) if n else math.nan
            rows.append({"entry": e, "exit": f, "n": n, "mean_bp": mean,
                         "median_bp": float(p.median()) if n else math.nan, "hit": hit,
                         "sharpe": sharpe, "score": hit * sharpe,
                         "ir_ann": sharpe * math.sqrt(events_per_year)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- CLI helpers
def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def load_series(path: str, ids: list[str], snap: str | None) -> pd.DataFrame:
    df = _read(path)
    if snap and "snap" in df.columns:
        df = df[df["snap"] == snap]
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    cols = {}
    for sid in ids:
        parts = sid.split("|")
        if {"curve_id", "tenor", "par_rate_pct"} <= set(df.columns) and len(parts) == 3:
            m = (df["curve_id"] == parts[0]) & (df["start"] == parts[1]) & (df["tenor"] == parts[2])
            s = df[m].set_index("date")["par_rate_pct"] * 100.0
        elif {"measure", "value_bp"} <= set(df.columns) and len(parts) == 3:
            m = (df["curve_id"] == parts[0]) & (df["measure"] == parts[1]) & (df["ref"] == parts[2])
            if "sign_convention" in df.columns and df[m]["sign_convention"].nunique() > 1:
                raise SystemExit(f"series {sid!r} mixes sign conventions; normalise first")
            s = df[m].set_index("date")["value_bp"]
        elif {"instrument_id", "ytm_pct"} <= set(df.columns):
            s = df[df["instrument_id"] == sid].set_index("date")["ytm_pct"] * 100.0
        elif sid in df.columns:
            s = df.set_index("date")[sid].astype(float)
        else:
            raise SystemExit(f"series {sid!r} not found in {path}")
        if s.empty:
            raise SystemExit(f"series {sid!r} is empty")
        if s.index.duplicated().any():
            raise SystemExit(f"series {sid!r} has several rows per date (mixed snaps?); pass --snap")
        cols[sid] = s
    return pd.DataFrame(cols).sort_index().dropna()


def load_events(a) -> list:
    if a.events:
        return [pd.Timestamp(s) for s in a.events.split(",")]
    au = _read(a.auctions)
    if a.issuer:
        au = au[au["issuer"] == a.issuer]
    if a.instruments:
        au = au[au["instrument_id"].isin(a.instruments.split(","))]
    if a.exclude_formats and "format" in au.columns:
        au = au[~au["format"].isin(a.exclude_formats.split(","))]
    return sorted(pd.to_datetime(au["auction_date"]).unique())


def _rng(s: str) -> list[int]:
    lo, hi = (int(t) for t in s.split(":"))
    return list(range(lo, hi + 1))


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    fails = []
    # 36 events 20 trading days apart. Into each auction the series cheapens linearly from T-5 to T-1
    # by c_k in {2, 4, 6} bp, holds at T, then fully reverts by T+4. Known answers:
    #   pre cell (-5,-1), direction +1: pnl = c_k -> mean 4, hit 1,
    #     sd (ddof=1) = sqrt(8/3 * 36/35), sharpe = score = 4/sd = 2.41523
    #   post cell (-1,+4), direction -1: pnl = c_k (full reversion) -> same stats
    #   cell (+5,+10): 0 bp every time -> mean 0, hit 0
    n_ev, gap, start = 36, 20, 30
    idx = pd.bdate_range("2020-01-01", periods=start + n_ev * gap + 30)
    x = np.zeros(len(idx))
    events = []
    for k in range(n_ev):
        p = start + k * gap
        c = (2.0, 4.0, 6.0)[k % 3]
        x[p - 5:p] = c * np.arange(0, 5) / 4.0            # T-5 = 0 ... T-1 = c
        x[p] = c
        x[p + 1:p + 4] = c * np.array([0.75, 0.5, 0.25])
        events.append(idx[p])
    s = pd.Series(x, index=idx)
    g = event_grid(s, events, [-5, -1, 5], [-1, 4, 10], direction=1, events_per_year=12)
    pre = g[(g.entry == -5) & (g.exit == -1)].iloc[0]
    sr = 4.0 / math.sqrt(8.0 / 3.0 * 36.0 / 35.0)
    if not (pre.n == n_ev and abs(pre.mean_bp - 4) < 1e-12 and abs(pre.sharpe - sr) < 1e-12
            and pre.hit == 1 and abs(pre.score - sr) < 1e-12 and abs(pre.ir_ann - sr * math.sqrt(12)) < 1e-9):
        fails.append(f"pre-auction cell wrong: {pre.to_dict()}")
    post = event_grid(s, events, [-1], [4], direction=-1).iloc[0]
    if not (abs(post.mean_bp - 4) < 1e-12 and post.hit == 1):
        fails.append(f"post-auction cell wrong: {post.to_dict()}")
    flat = g[(g.entry == 5) & (g.exit == 10)].iloc[0]
    if not (abs(flat.mean_bp) < 1e-12 and flat.hit == 0):
        fails.append(f"flat cell wrong: {flat.to_dict()}")
    # non-trading-day event rolls forward; window off the sample end is dropped
    if idx[event_positions(idx, ["2020-02-01"])[0]] != pd.Timestamp("2020-02-03"):  # Sat -> Mon
        fails.append("event roll to next trading day failed")
    if len(event_window_pnl(s, [idx[-2]], -1, 4)) != 0:
        fails.append("window beyond sample end was not dropped")
    if len(event_positions(idx, ["2019-12-02"])) != 0:  # before the first row: dropped, not mapped to row 0
        fails.append("event before sample start was not dropped")
    print("selftest", "FAILED" if fails else "passed")
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", help="canonical curve_par / bond_quotes / swap_spreads, or wide CSV")
    ap.add_argument("--snap")
    ap.add_argument("--series", help="comma-separated series ids")
    ap.add_argument("--weights", help="comma-separated weights (default 1 each); 2s10s = -1,1")
    ap.add_argument("--auctions", help="canonical auctions table")
    ap.add_argument("--issuer")
    ap.add_argument("--instruments", help="comma-separated instrument_ids to keep")
    ap.add_argument("--exclude-formats", default="syndication",
                    help="auction formats to drop (default syndication)")
    ap.add_argument("--events", help="comma-separated event dates instead of --auctions")
    ap.add_argument("--entries", default="-10:0")
    ap.add_argument("--exits", default="-5:10")
    ap.add_argument("--direction", type=int, default=1, choices=[1, -1])
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not (a.file and a.series and (a.events or a.auctions)):
        ap.error("--file, --series and one of --events/--auctions are required")
    ids = a.series.split(",")
    w = [float(t) for t in a.weights.split(",")] if a.weights else [1.0] * len(ids)
    if len(w) != len(ids):
        ap.error("--weights must match --series")
    panel = load_series(a.file, ids, a.snap)
    x = (panel[ids] * w).sum(axis=1)
    events = load_events(a)
    g = event_grid(x, events, _rng(a.entries), _rng(a.exits), a.direction)
    g = g.sort_values(["score", "mean_bp"], ascending=False)
    out = {"n_events": len(events), "first": str(x.index.min().date()), "last": str(x.index.max().date()),
           "direction": a.direction, "top": json.loads(g.head(a.top).to_json(orient="records"))}
    print(json.dumps(out, indent=1, ensure_ascii=True))


if __name__ == "__main__":
    main()
