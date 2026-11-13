#!/usr/bin/env python3
"""Check trade levels and policy-path increments taken from a research note.

Functions accept scalars, numpy arrays or pandas Series. The CLI reads a CSV and writes one row per input.

  python scripts/claim_check.py --trades TRADES.csv              # columns: id, entry, target, stop
  python scripts/claim_check.py --policy PATH.csv --step 25      # columns: meeting, cum_bp
  python scripts/claim_check.py --selftest

Units: levels and step in the unit the note quotes (bp for spreads and ASW, % for yields, bp/yr for vol).
Direction is inferred from the target: a target above entry means the position gains when the level rises.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


def level_check(entry, target, stop):
    """Check that a stated trade is internally coherent and measure its payoff shape.

    direction      = sign(target - entry): +1 gains when the level rises, -1 gains when it falls.
    ok             = target and stop are both off entry, on opposite sides, with the stop on the loss side.
    reward, risk   = |target - entry|, |stop - entry|.
    reward_risk    = reward / risk.
    breakeven_hit  = risk / (reward + risk): the hit rate at which expected P&L is zero, before carry,
                     roll, costs and slippage (p * reward = (1 - p) * risk).
    reward_risk and breakeven_hit are NaN where ok is False: they have no meaning for an incoherent trade.
    """
    e = np.asarray(entry, dtype=float)
    t = np.asarray(target, dtype=float)
    s = np.asarray(stop, dtype=float)
    dt = t - e
    ds = s - e
    direction = np.sign(dt)
    ok = (dt != 0) & (ds != 0) & (np.sign(ds) == -direction)
    reward = np.abs(dt)
    risk = np.abs(ds)
    with np.errstate(divide="ignore", invalid="ignore"):
        reward_risk = reward / risk
        breakeven_hit = risk / (reward + risk)
    reward_risk = np.where(ok, reward_risk, np.nan)
    breakeven_hit = np.where(ok, breakeven_hit, np.nan)
    return {"direction": direction, "ok": ok, "reward": reward, "risk": risk,
            "reward_risk": reward_risk, "breakeven_hit": breakeven_hit}


def cumulative_to_marginal(cum_bp, step_bp):
    """Split a cumulative priced move (bp at each meeting, in date order) into per-meeting increments.

    marginal        = first difference of the cumulative path (first meeting measured from zero).
    expected_moves  = cum / step: expected number of policy moves priced by each meeting, if each move is one step.
    multi_move      = True where a single meeting increment exceeds one step, so a one-move model is wrong there.
    """
    if not float(step_bp) > 0:
        raise ValueError("step_bp must be positive")
    c = np.asarray(cum_bp, dtype=float)
    marginal = np.diff(c, prepend=0.0)
    expected_moves = c / float(step_bp)
    multi_move = np.abs(marginal) > float(step_bp) + 1e-9
    return {"marginal": marginal, "expected_moves": expected_moves, "multi_move": multi_move}


def _trades_table(path):
    df = pd.read_csv(path)
    missing = {"id", "entry", "target", "stop"} - set(df.columns)
    if missing:
        raise SystemExit(f"trades CSV missing columns: {sorted(missing)}")
    r = level_check(df["entry"], df["target"], df["stop"])
    return pd.DataFrame({
        "id": df["id"],
        "direction": r["direction"].astype(int),
        "ok": r["ok"],
        "reward": np.round(r["reward"], 4),
        "risk": np.round(r["risk"], 4),
        "reward_risk": np.round(r["reward_risk"], 3),
        "breakeven_hit": np.round(r["breakeven_hit"], 3),
    })


def _policy_table(path, step):
    df = pd.read_csv(path)
    missing = {"meeting", "cum_bp"} - set(df.columns)
    if missing:
        raise SystemExit(f"policy CSV missing columns: {sorted(missing)}")
    d = pd.to_datetime(df["meeting"], errors="coerce")
    if d.notna().all():  # the path must be in date order for the first difference to mean anything
        df = df.iloc[np.argsort(d.to_numpy(), kind="stable")].reset_index(drop=True)
    m = cumulative_to_marginal(df["cum_bp"], step)
    return pd.DataFrame({
        "meeting": df["meeting"],
        "marginal_bp": np.round(m["marginal"], 4),
        "expected_moves": np.round(m["expected_moves"], 3),
        "multi_move": m["multi_move"],
    })


def selftest():
    """Known answers taken from published trade levels and from hand-checked arithmetic."""
    fails = []
    n_checks = [0]

    def check(name, cond):
        n_checks[0] += 1
        if not bool(cond):
            fails.append(name)

    def close(a, b):
        return bool(np.isclose(float(a), float(b), rtol=0, atol=1e-9))

    # Long Jan SOFR/FF basis, entry -6.5, target -2, stop -11 (BofA, 6 Oct 2025): R = S = 4.5, RR = 1, breakeven 50%.
    r = level_check(-6.5, -2.0, -11.0)
    check("long basis direction", r["direction"] == 1)
    check("long basis ok", r["ok"])
    check("long basis reward_risk", close(r["reward_risk"], 1.0))
    check("long basis breakeven", close(r["breakeven_hit"], 0.5))

    # Short Oct SOFR/FF, entry -4, target -8, stop -1 (BofA, 27 Jun 2025): R = 4, S = 3, breakeven 3/7.
    r = level_check(-4.0, -8.0, -1.0)
    check("short basis direction", r["direction"] == -1)
    check("short basis ok", r["ok"])
    check("short basis reward_risk", close(r["reward_risk"], 4.0 / 3.0))
    check("short basis breakeven", close(r["breakeven_hit"], 3.0 / 7.0))

    # 2s30s flattener, entry 62, target 40, stop 100 after a stop reset (BofA, 2 Oct 2026): R = 22, S = 38, breakeven 38/60.
    r = level_check(62.0, 40.0, 100.0)
    check("flattener direction", r["direction"] == -1)
    check("flattener ok", r["ok"])
    check("flattener reward_risk", close(r["reward_risk"], 22.0 / 38.0))
    check("flattener breakeven", close(r["breakeven_hit"], 38.0 / 60.0))

    # Incoherent levels: target above entry and stop above entry, both on the profit side -> must fail.
    r = level_check(10.0, 20.0, 15.0)
    check("incoherent levels flagged", not r["ok"])
    check("incoherent metrics masked", np.isnan(r["reward_risk"]) and np.isnan(r["breakeven_hit"]))
    check("stop at entry flagged", not level_check(10.0, 20.0, 10.0)["ok"])
    check("NaN input flagged", not level_check(np.nan, 20.0, 5.0)["ok"])

    # Policy path: cumulative 20bp by Sep, 25bp by Oct, step 25 -> marginal [20, 5], expected moves [0.8, 1.0].
    m = cumulative_to_marginal([20.0, 25.0], 25.0)
    check("marginal increments", np.allclose(m["marginal"], [20.0, 5.0]))
    check("expected moves", np.allclose(m["expected_moves"], [0.8, 1.0]))
    check("no multi-move", not m["multi_move"].any())

    # Cumulative jumps 20 -> 50 in one meeting with step 25: a 30bp increment must be flagged as multi-move.
    m = cumulative_to_marginal([20.0, 50.0], 25.0)
    check("multi-move flagged", list(m["multi_move"]) == [False, True])

    if fails:
        print("SELFTEST FAILED: " + ", ".join(fails))
        return 1
    print(f"selftest passed ({n_checks[0]} checks)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="run known-answer checks and exit")
    ap.add_argument("--trades", help="CSV with columns id, entry, target, stop")
    ap.add_argument("--policy", help="CSV with columns meeting, cum_bp (cumulative priced move, bp)")
    ap.add_argument("--step", type=float, default=25.0, help="policy step in bp (default 25)")
    ap.add_argument("--out", help="write the result CSV here instead of stdout")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not (args.trades or args.policy):
        ap.print_help()
        return 2
    table = _trades_table(args.trades) if args.trades else _policy_table(args.policy, args.step)
    if args.out:
        table.to_csv(args.out, index=False)
    else:
        table.to_csv(sys.stdout, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
