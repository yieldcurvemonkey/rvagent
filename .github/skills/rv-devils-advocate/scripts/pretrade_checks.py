#!/usr/bin/env python3
"""Numeric helpers for the adversarial pre-trade review (rv-devils-advocate).

Sign convention: dv01_ccy > 0 = long duration (receive fixed / long bond). A yield or spread shock of +x bp
changes value by -dv01_ccy * x (first order). Spread legs: give the DV01 of each leg and the shock of each leg's
own yield, or one synthetic leg whose dv01 is per bp of the spread.

CLI:
  python pretrade_checks.py scenario --positions positions.csv --scenarios scen.csv
      positions: instrument_id, dv01_ccy      scenarios: scenario, instrument_id, shock_bp
  python pretrade_checks.py hurdles --risk 2 --gain 1.5 --p 0.63 --n 52
  python pretrade_checks.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649015329


def scenario_pnl(positions: pd.DataFrame, scenarios: pd.DataFrame) -> pd.DataFrame:
    """First-order P&L per scenario (ccy) = -sum(dv01_ccy * shock_bp). Returns scenario, pnl_ccy, worst_leg.
    Instruments missing a shock in a scenario are treated as unshocked (0) and reported in n_unshocked.
    If `positions` has a date column (canonical positions table) only the latest date is used, so DV01 is not summed over days."""
    if "date" in positions.columns:
        positions = positions[positions["date"] == positions["date"].max()]
    if positions["dv01_ccy"].isna().any():
        raise ValueError("dv01_ccy has missing values; refusing to treat them as zero risk")
    pos = positions.groupby("instrument_id", as_index=False)["dv01_ccy"].sum()
    rows = []
    for name, g in scenarios.groupby("scenario", sort=False):
        m = pos.merge(g[["instrument_id", "shock_bp"]], on="instrument_id", how="left")
        n_miss = int(m["shock_bp"].isna().sum())
        m["pnl"] = -m["dv01_ccy"] * m["shock_bp"].fillna(0.0)
        worst = m.loc[m["pnl"].idxmin(), "instrument_id"] if len(m) else ""
        rows.append({"scenario": name, "pnl_ccy": float(m["pnl"].sum()), "worst_leg": worst, "n_unshocked": n_miss})
    return pd.DataFrame(rows)


def breakeven_hit_rate(risk: float, gain: float) -> float:
    """Win probability at which a bet risking `risk` to win `gain` has zero EV: risk / (risk + gain)."""
    return risk / (risk + gain)


def binomial_sharpe(p: float, n: float, loss: float = 1.0, gain: float = 1.0) -> float:
    """Annualised Sharpe of n independent bets/yr: win `gain` w.p. p, lose `loss` (positive number) w.p. 1-p.
    Symmetric case reduces to (2p-1)/(2*sqrt(p(1-p)))*sqrt(n)."""
    if not (0.0 < p < 1.0) or gain + loss <= 0:
        return float("nan")
    mu = p * gain - (1 - p) * loss
    sd = (gain + loss) * math.sqrt(p * (1 - p))
    return mu / sd * math.sqrt(n)


def required_hit_rate(sr_target: float, n: float, loss: float = 1.0, gain: float = 1.0) -> float:
    """Smallest p with binomial_sharpe(p, n, loss, gain) >= sr_target (bisection above break-even)."""
    lo, hi = breakeven_hit_rate(loss, gain), 1 - 1e-9
    if binomial_sharpe(hi, n, loss, gain) < sr_target:
        return float("nan")
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if binomial_sharpe(mid, n, loss, gain) < sr_target else (lo, mid)
    return hi


def deflated_sr_threshold(var_sr_trials: float, n_trials: int) -> float:
    """Expected maximum Sharpe among n_trials unskilled trials: SR* = sqrt(V)*((1-g)Z^-1(1-1/N)+g Z^-1(1-1/(N e)))."""
    from scipy.stats import norm
    if n_trials < 2:
        return 0.0
    return math.sqrt(var_sr_trials) * ((1 - EULER_GAMMA) * norm.ppf(1 - 1 / n_trials)
                                       + EULER_GAMMA * norm.ppf(1 - 1 / (n_trials * math.e)))


def carry_cushion_bp(carry_ccy: float, dv01_ccy: float) -> float:
    """Adverse move (bp) the horizon carry+roll absorbs: carry_ccy / |dv01_ccy|. Negative carry gives a negative cushion."""
    return carry_ccy / abs(dv01_ccy) if dv01_ccy else float("nan")


def days_to_exit(position_dv01: float, adv_dv01: float, participation: float = 0.1) -> float:
    """Days to liquidate at `participation` of average daily volume (both in DV01 units)."""
    return abs(position_dv01) / (participation * adv_dv01) if adv_dv01 > 0 and participation > 0 else float("inf")


def haircut_cash_call(notional: float, haircut_now: float, haircut_stress: float) -> float:
    """Extra cash needed if the financing haircut (fraction) rises from haircut_now to haircut_stress."""
    return notional * max(haircut_stress - haircut_now, 0.0)


def _selftest() -> int:
    bad = []

    def chk(name, got, want, tol):
        if not (abs(got - want) <= tol):
            bad.append(f"{name}: got {got!r} want {want!r}")

    # receive-belly 50/50 2s5s10s fly, DV01 +10k belly, -5k wings (ccy/bp)
    pos = pd.DataFrame({"instrument_id": ["y2", "y5", "y10"], "dv01_ccy": [-5000.0, 10000.0, -5000.0]})
    sc = pd.DataFrame({
        "scenario": ["parallel+25"] * 3 + ["belly_cheapens"] * 3,
        "instrument_id": ["y2", "y5", "y10"] * 2,
        "shock_bp": [25, 25, 25, 5, 20, 10]})
    out = scenario_pnl(pos, sc).set_index("scenario")
    chk("parallel is fly-neutral", out.loc["parallel+25", "pnl_ccy"], 0.0, 1e-9)
    chk("fly +25bp costs 5000*25", out.loc["belly_cheapens", "pnl_ccy"], -125000.0, 1e-9)
    chk("breakeven R=2 G=1.5", breakeven_hit_rate(2, 1.5), 4 / 7, 1e-12)
    chk("sharpe p=.55 n=396", binomial_sharpe(0.55, 396), 2.0, 0.01)
    chk("sharpe asym p=.70", binomial_sharpe(0.70, 260, loss=1.0, gain=0.5), 1.173, 0.002)
    chk("weekly bets need p=.6336", required_hit_rate(2.0, 52), 0.6336, 0.0005)
    chk("SR* N=100 V=1", deflated_sr_threshold(1.0, 100), 2.533, 0.005)
    chk("carry cushion", carry_cushion_bp(3000.0, 1000.0), 3.0, 1e-12)
    chk("days to exit", days_to_exit(1.0e6, 1.0e6, 0.1), 10.0, 1e-12)
    chk("haircut call", haircut_cash_call(1e9, 0.03, 0.15), 1.2e8, 1.0)
    chk("SR* N=7 V=.25", deflated_sr_threshold(0.25, 7), 0.693, 0.002)
    chk("sharpe p=1 is nan", float(math.isnan(binomial_sharpe(1.0, 52))), 1.0, 0)
    chk("zero ADV is inf", float(math.isinf(days_to_exit(1.0, 0.0))), 1.0, 0)
    # canonical positions table with two dates: only the latest counts
    p2 = pd.DataFrame({"date": ["d1", "d1", "d2", "d2"], "instrument_id": ["a", "b", "a", "b"], "dv01_ccy": [1e3, 1e3, 10.0, 20.0]})
    s2 = pd.DataFrame({"scenario": ["s", "s"], "instrument_id": ["a", "b"], "shock_bp": [1.0, 1.0]})
    chk("latest date only", scenario_pnl(p2, s2).loc[0, "pnl_ccy"], -30.0, 1e-9)
    if bad:
        print("SELFTEST FAILED\n" + "\n".join(bad))
        return 1
    print("selftest ok")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("scenario")
    s.add_argument("--positions", required=True)
    s.add_argument("--scenarios", required=True)
    h = sub.add_parser("hurdles")
    h.add_argument("--risk", type=float, required=True)
    h.add_argument("--gain", type=float, required=True)
    h.add_argument("--p", type=float, required=True, help="your estimated hit rate")
    h.add_argument("--n", type=float, default=52, help="independent bets per year")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.cmd == "scenario":
        rd = lambda f: pd.read_parquet(f) if f.endswith(".parquet") else pd.read_csv(f)  # noqa: E731
        print(scenario_pnl(rd(a.positions), rd(a.scenarios)).to_string(index=False))
        return 0
    if a.cmd == "hurdles":
        be = breakeven_hit_rate(a.risk, a.gain)
        print(f"break-even hit rate {be:.3f}; your p {a.p:.3f}; margin {a.p - be:+.3f}")
        print(f"binomial Sharpe at p, n={a.n:g}: {binomial_sharpe(a.p, a.n, a.risk, a.gain):.2f}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
