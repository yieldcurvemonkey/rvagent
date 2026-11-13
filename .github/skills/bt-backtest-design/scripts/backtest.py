#!/usr/bin/env python
"""Vectorised RV backtest core: trailing z-score -> fade state machine -> lagged DV01 position -> P&L.

Conventions (same as the skill):
  * spread_bp   : spread LEVEL in bp, A-B = longer minus shorter. Position +1 = long the spread (profits when it rises).
  * units       : signed ccy per bp of spread_bp (+ = profits when the level rises; for an outright yield that is a payer, i.e. -DV01_long),
                  DECIDED at close t from data <= t (the signal date).
  * exec_lag    : fill happens exec_lag marks after the signal close (default 1 = next close; 0 = same-bar diagnostic).
  * held h_t    = units_{t-exec_lag}  (position at close t);  P&L over (t-1, t] uses h_{t-1}  -> no look-ahead.
  * P&L parts   : mtm (h*dS), carry and financing (h * bp/yr * calendar days/365.25), cost (-|dh| * one-way bp) in ccy.
CLI: python backtest.py --series spread.csv --value-col spread_bp [--entry 2 --exit 0.5 --stop 4 --cost-bp 0.3]
     python -I backtest.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


def zscore_trailing(x: pd.Series, window: int = 60) -> pd.Series:
    """Causal z-score: mean/std over the `window` obs ENDING at t (inclusive). NaN until the window is full."""
    r = x.rolling(window, min_periods=window)
    sd = r.std(ddof=1).replace(0.0, np.nan)
    return (x - r.mean()) / sd


def fade_positions(z: pd.Series, entry: float = 2.0, exit_: float = 0.5, stop: float = 4.0) -> pd.Series:
    """Mean-reversion state machine on a z-score. +1 = long spread (z <= -entry), -1 = short (z >= +entry).

    Exit when z has come back to within +-exit_ (or overshot); stop when |z| >= stop moves against the trade,
    then stay flat until |z| < entry again (otherwise the same bar re-enters). NaN z -> flat.
    """
    out = np.zeros(len(z))
    pos, locked = 0, False
    for i, v in enumerate(z.to_numpy(float)):
        if np.isnan(v):
            pos = 0
        else:
            if locked and abs(v) < entry:
                locked = False
            if pos == 1 and v >= -exit_:
                pos = 0
            elif pos == -1 and v <= exit_:
                pos = 0
            if pos != 0 and abs(v) >= stop:  # only reachable when the move is against us (exit tested first)
                pos, locked = 0, True
            if pos == 0 and not locked:
                if abs(v) >= stop:
                    locked = True
                elif v <= -entry:
                    pos = 1
                elif v >= entry:
                    pos = -1
        out[i] = pos
    return pd.Series(out, index=z.index)


def vol_target_dv01(spread_bp: pd.Series, target_daily_ccy: float, window: int = 60) -> pd.Series:
    """DV01 (ccy/bp) so one sd of daily spread change (trailing, through t) costs/earns target_daily_ccy."""
    sd = spread_bp.diff().rolling(window, min_periods=window).std(ddof=1).replace(0.0, np.nan)
    return target_daily_ccy / sd


def _rate(x, index):
    """Scalar -> constant; Series -> value known at t-1 (NaN kept: the caller rejects NaN where a position is held)."""
    return x.reindex(index).shift(1) if isinstance(x, pd.Series) else pd.Series(float(x), index=index)


def run_backtest(spread_bp: pd.Series, units: pd.Series, exec_lag: int = 1, carry_bp_yr=0.0,
                 financing_bp_yr=0.0, cost_bp: float = 0.0) -> pd.DataFrame:
    """Daily P&L in ccy with components matching the canonical `pnl` table. Index must be a DatetimeIndex.

    carry_bp_yr / financing_bp_yr: scalar or Series (bp per year per unit of DV01 held; a Series is read as of t-1).
    cost_bp: one-way cost in bp per unit of DV01 traded (half bid/offer + fees). Charged on the traded increment.
    """
    if not isinstance(spread_bp.index, pd.DatetimeIndex):
        raise TypeError("spread_bp needs a DatetimeIndex (carry accrues on calendar days)")
    if exec_lag < 0:
        raise ValueError("exec_lag < 0 trades before the signal exists (look-ahead)")
    if spread_bp.isna().any():  # a NaN mark would silently drop the move across the gap
        raise ValueError("NaN in spread_bp: drop/log stale rows upstream, never forward-fill")
    h = units.reindex(spread_bp.index).shift(exec_lag).fillna(0.0)  # position at close t
    hp = h.shift(1).fillna(0.0)  # position held over (t-1, t]
    dd = pd.Series(spread_bp.index, index=spread_bp.index).diff().dt.days.fillna(0.0)  # Fri->Mon = 3
    res = pd.DataFrame(index=spread_bp.index)
    res["pos_dv01_ccy"] = h
    res["mtm_ccy"] = (hp * spread_bp.diff()).fillna(0.0)
    rates = {k: _rate(v, res.index) for k, v in (("carry", carry_bp_yr), ("financing", financing_bp_yr))}
    for k, r_ in rates.items():  # missing carry/financing while a position is held is an error, not zero
        if (r_.isna() & (hp != 0) & (dd > 0)).any():
            raise ValueError(f"{k} series has NaN on days a position is held")
    res["carry_ccy"] = (hp * rates["carry"] * dd / 365.25).fillna(0.0)
    res["financing_ccy"] = (hp * rates["financing"] * dd / 365.25).fillna(0.0)
    res["cost_ccy"] = -(h - hp).abs() * cost_bp
    res["total_ccy"] = res[["mtm_ccy", "carry_ccy", "financing_ccy", "cost_ccy"]].sum(axis=1)
    return res


def summary(total_ccy: pd.Series, periods_per_year: int = 252) -> dict:
    """Sharpe uses the raw P&L (no rf subtraction for a self-financing book). SE(SR) = sqrt((1+SR^2/2)/T)."""
    x = total_ccy.dropna()
    sd = x.std(ddof=1)
    sr_p = x.mean() / sd if sd > 0 else np.nan
    cum = x.cumsum()
    return {"n": int(len(x)), "total_ccy": float(x.sum()), "sharpe_ann": float(sr_p * np.sqrt(periods_per_year)),
            "t_stat": float(sr_p * np.sqrt(len(x))), "se_sharpe_ann": float(np.sqrt((1 + sr_p ** 2 / 2) / len(x)) * np.sqrt(periods_per_year)),
            "hit_rate_active": float((x[x != 0] > 0).mean()) if (x != 0).any() else np.nan,
            "max_dd_ccy": float((cum.cummax() - cum).max())}


def cost_sweep(spread_bp, units, base_cost_bp, mults=(0, 0.5, 1, 2), **kw) -> dict:
    """Net P&L at k x base cost and the break-even one-way cost (bp per DV01 traded)."""
    out = {m: float(run_backtest(spread_bp, units, cost_bp=base_cost_bp * m, **kw)["total_ccy"].sum()) for m in mults}
    r0 = run_backtest(spread_bp, units, cost_bp=0.0, **kw)
    traded = float((r0["pos_dv01_ccy"].diff().abs().fillna(r0["pos_dv01_ccy"].abs())).sum())
    out["breakeven_cost_bp"] = float(r0["total_ccy"].sum() / traded) if traded > 0 else np.nan
    return out


def truncation_test(signal_fn, data: pd.Series, n: int = 60) -> bool:
    """Look-ahead test: positions from the full data must equal positions from data minus the last n obs."""
    if not 0 < n < len(data):
        raise ValueError("need 0 < n < len(data), else the comparison is empty and passes vacuously")
    a = signal_fn(data).iloc[:-n]
    b = signal_fn(data.iloc[:-n])
    return bool(np.allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True))


# ----------------------------------------------------------------------------------------------------- selftest
def _raises(f) -> bool:
    try:
        f()
    except (ValueError, TypeError):
        return True
    return False


def _selftest() -> int:
    fails = []

    def check(name, ok):
        print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            fails.append(name)

    bd = pd.bdate_range("2026-01-05", periods=5)  # Mon..Fri
    S = pd.Series([10.0, 11, 13, 12, 12], index=bd)
    q = pd.Series([10.0, 10, 0, 0, 0], index=bd)  # decided at close t; DV01 10 ccy/bp
    r = run_backtest(S, q, exec_lag=1, cost_bp=0.5)
    # held h = [0,10,10,0,0]; mtm: t2 10*2=20, t3 10*(-1)=-10; trades: 0->10 and 10->0 = 20 DV01 * 0.5 = 10
    check("T1 known P&L (mtm 10, cost -10, total 0)", np.isclose(r.mtm_ccy.sum(), 10.0) and np.isclose(r.cost_ccy.sum(), -10.0)
          and np.isclose(r.total_ccy.sum(), 0.0))
    r2 = run_backtest(S, q, exec_lag=2)  # h=[0,0,10,10,0]: only t3 earns 10*(12-13) = -10
    check("T1c lag-2 fill: mtm -10", np.isclose(r2.mtm_ccy.sum(), -10.0))
    r0 = run_backtest(S, q, exec_lag=0)  # same-bar fill: h=[10,10,0,0,0]; earns t1 10*1 + t2 10*2 = 30
    check("T1b lag-0 diagnostic earns more on this path (30 vs 10)", np.isclose(r0.mtm_ccy.sum(), 30.0))

    d2 = pd.DatetimeIndex(["2026-01-07", "2026-01-08", "2026-01-09", "2026-01-12", "2026-01-13"])  # Wed Thu Fri Mon Tue
    flat = pd.Series(100.0, index=d2)
    rc = run_backtest(flat, pd.Series(10.0, index=d2), carry_bp_yr=36.525)  # 0.1bp/day * DV01 10 = 1.0 ccy/day
    check("T2 carry accrual: Fri->Mon = 3x one day", np.allclose(rc.carry_ccy.to_numpy(), [0, 0, 1.0, 3.0, 1.0]))

    check("T2b NaN mark or missing carry while held raises, negative lag raises", all(
        _raises(f) for f in (lambda: run_backtest(S.where(S != 13), q), lambda: run_backtest(S, q, exec_lag=-1),
                             lambda: run_backtest(S, q, carry_bp_yr=pd.Series([np.nan] * 5, index=bd)))))
    sm = summary(pd.Series([1.0, 3.0] * 50))  # mean 2, deviations +-1 -> var = 100/99; no cum loss
    sd_ = np.sqrt(100 / 99)
    check("T2c summary: Sharpe, t, SE closed form", np.isclose(sm["sharpe_ann"], 2 / sd_ * np.sqrt(252))
          and np.isclose(sm["t_stat"], 2 / sd_ * 10) and np.isclose(sm["se_sharpe_ann"], np.sqrt((1 + (2 / sd_) ** 2 / 2) / 100 * 252)))
    dd_ = summary(pd.Series([1.0, 1, -3, -1, 2]))  # cum 1,2,-1,-2,0 -> peak 2, trough -2
    check("T2d summary: max drawdown 4, hit rate 3/5", np.isclose(dd_["max_dd_ccy"], 4.0) and np.isclose(dd_["hit_rate_active"], 0.6))
    vt = vol_target_dv01(pd.Series([0.0, 1, 0, 1, 0]), 100.0, window=4)  # diffs +1,-1,+1,-1: sd = sqrt(4/3)
    check("T2e vol target = target / sd(dS)", np.isclose(vt.iloc[-1], 100 / np.sqrt(4 / 3)) and vt.iloc[:3].isna().all())
    z = pd.Series([0, -2.5, -1.0, -0.4, 2.5, 0.4])
    check("T3 exit at |z|<=0.5 and flip", fade_positions(z).tolist() == [0, 1, 1, 0, -1, 0])
    z = pd.Series([0, -2.5, -4.5, -4.2, -1.0, -2.5])
    check("T3b stop forces flat and locks until |z|<entry", fade_positions(z).tolist() == [0, 1, 0, 0, 0, 1])

    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2000-01-03", periods=20000)
    rw = pd.Series(np.cumsum(rng.normal(size=len(idx))), index=idx)
    fn = lambda s: fade_positions(zscore_trailing(s, 60))  # noqa: E731
    cheat = lambda s: fade_positions((s - s.mean()) / s.std())  # noqa: E731  full-sample z = look-ahead
    check("T4 truncation test passes for causal signal", truncation_test(fn, rw, 100))
    check("T4b truncation test FAILS for full-sample z (test bites)", not truncation_test(cheat, rw, 100))

    t_rw = summary(run_backtest(rw, fn(rw) * 1.0)["total_ccy"])["t_stat"]
    check(f"T5 random walk: no edge (|t|={abs(t_rw):.2f} < 3.5)", abs(t_rw) < 3.5)

    phi, e = 0.9, rng.normal(size=len(idx))
    ou = np.zeros(len(idx))
    for i in range(1, len(idx)):
        ou[i] = phi * ou[i - 1] + e[i]
    ou = pd.Series(ou, index=idx)
    pos = fn(ou)
    t_ou = summary(run_backtest(ou, pos)["total_ccy"])["t_stat"]
    t_inv = summary(run_backtest(ou, -pos)["total_ccy"])["t_stat"]
    check(f"T6 OU(phi=0.9): fade earns (t={t_ou:.1f} > 4), inverted loses (t={t_inv:.1f})", t_ou > 4 and t_inv < -4)
    t_l0 = summary(run_backtest(ou, pos, exec_lag=0)["total_ccy"])["t_stat"]
    check("T7 same-bar fill (lag 0) flatters vs lag 1 on OU", t_l0 > t_ou)

    sw = cost_sweep(ou, pos, base_cost_bp=0.2)
    check("T8 costs monotone and break-even cost zeroes P&L",
          sw[0] > sw[0.5] > sw[1] > sw[2]
          and abs(run_backtest(ou, pos, cost_bp=sw["breakeven_cost_bp"])["total_ccy"].sum()) < 1e-6)
    return 1 if fails else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--series", help="CSV/Parquet with a date column and a spread level column (bp)")
    ap.add_argument("--date-col", default="date")
    ap.add_argument("--value-col", default="spread_bp")
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--entry", type=float, default=2.0)
    ap.add_argument("--exit", dest="exit_", type=float, default=0.5)
    ap.add_argument("--stop", type=float, default=4.0)
    ap.add_argument("--lag", type=int, default=1)
    ap.add_argument("--dv01", type=float, default=10000.0, help="ccy per bp (ignored if --target-daily-ccy)")
    ap.add_argument("--target-daily-ccy", type=float, default=None, help="vol-target: ccy P&L per 1sd daily move")
    ap.add_argument("--carry-bp-yr", type=float, default=0.0)
    ap.add_argument("--cost-bp", type=float, default=0.0, help="one-way bp per unit DV01 traded")
    ap.add_argument("--out", help="write daily P&L (pnl-table columns) to this CSV")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if not a.series:
        ap.error("--series is required (or use --selftest)")
    df = pd.read_parquet(a.series) if a.series.endswith(".parquet") else pd.read_csv(a.series)
    s = df.set_index(pd.to_datetime(df[a.date_col]))[a.value_col].astype(float).sort_index()
    if s.isna().any():
        sys.exit("NaN in series: drop/log stale rows upstream, never forward-fill")
    z = zscore_trailing(s, a.window)
    size = vol_target_dv01(s, a.target_daily_ccy, a.window) if a.target_daily_ccy else a.dv01
    units = fade_positions(z, a.entry, a.exit_, a.stop) * size
    res = run_backtest(s, units, a.lag, a.carry_bp_yr, 0.0, a.cost_bp)
    print({k: round(v, 3) if isinstance(v, float) else v for k, v in summary(res["total_ccy"]).items()})
    print("cost sweep (x0, x0.5, x1, x2, breakeven):", {k: round(v, 1) for k, v in cost_sweep(
        s, units, max(a.cost_bp, 0.1), exec_lag=a.lag, carry_bp_yr=a.carry_bp_yr).items()})
    if a.out:
        res.rename_axis("date").to_csv(a.out)


if __name__ == "__main__":
    main()
