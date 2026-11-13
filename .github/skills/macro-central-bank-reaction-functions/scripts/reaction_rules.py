"""Central-bank reaction-rule anchors and market-path read-outs.

Functions take floats or numpy/pandas arrays. Rates are in percent (4.25 = 4.25%), spreads and
moves in basis points (bp). Sign conventions: curve spread = longer minus shorter, so 2s10s =
y10 - y2 and an inversion is a negative spread; fly 2s5s10s = 2*y5 - y2 - y10.

CLI (canonical CSV: one row per meeting, columns meeting_date and implied_avg_rate_pct, where
implied_avg_rate_pct is the OIS/futures-implied average policy rate for the period after that
meeting, in percent):

    python -I scripts/reaction_rules.py taylor --pi 3.0 --gap 1.0
    python -I scripts/reaction_rules.py strip --csv path/to/strip.csv --current 3.75 --step-bp 25
    python -I scripts/reaction_rules.py --selftest

The strip output gives p_full_step signed (negative = cut probability); |p| > 1 means more than one step or a
premium in the strip. Monthly-average futures need post_meeting_rate first.

Requires numpy and pandas only.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np


def taylor_rate(pi_pct, gap_pct, r_star=2.0, pi_star=2.0, a_pi=0.5, a_y=0.5):
    """Taylor-type policy rate in percent: i = r* + pi + a_pi*(pi - pi*) + a_y*gap.

    Defaults are Taylor's 0.5/0.5 weights, r* = 2 and pi* = 2. With these defaults this equals
    Duering's form r = p + y/2 + (p-2)/2 + 2 (Fixed Income Trading and Risk Management, eq. 20.1).
    Use it as an ex-post explanation or as a bound, not a forecast: the gap is not observable in
    real time.
    """
    pi = np.asarray(pi_pct, dtype=float)
    gap = np.asarray(gap_pct, dtype=float)
    out = r_star + pi + a_pi * (pi - pi_star) + a_y * gap
    return float(out) if out.ndim == 0 else out


def implied_hike_prob(fwd_pct, current_pct, step_bp=25.0):
    """Probability of a full step move implied by a meeting-period forward vs the current rate.

    P = (forward - current) in bp / step_bp. Assumes at most one step at the meeting. Values
    outside [0, 1] mean the strip holds more than one move or contains a term premium, so the
    caller must flag them rather than clip them.
    """
    fwd = np.asarray(fwd_pct, dtype=float)
    cur = np.asarray(current_pct, dtype=float)
    p = (fwd - cur) * 100.0 / float(step_bp)
    return float(p) if p.ndim == 0 else p


def meeting_moves_bp(current_pct, avg_rates_pct):
    """Incremental move in bp between successive meeting-period average rates, starting at the current rate.

    The input must be the implied rate in force AFTER each meeting (see post_meeting_rate for monthly-average
    futures). NaN in the input propagates to that move and the next one, so callers must drop or flag it.
    """
    path = np.concatenate([[float(current_pct)], np.asarray(avg_rates_pct, dtype=float)])
    return np.diff(path) * 100.0


def post_meeting_rate(avg_month_pct, prev_rate_pct, days_pre, days_in_month):
    """Rate in force after a meeting, from a monthly-average future (fed funds style; rate = 100 - price).

    The month average mixes days_pre days at the old rate and the rest at the new one:
    new = (avg * D - prev * days_pre) / (D - days_pre). Using the raw average understates the move
    when the meeting is late in the month (and overstates it when early).
    """
    d, k = float(days_in_month), float(days_pre)
    return (float(avg_month_pct) * d - float(prev_rate_pct) * k) / (d - k)


def ff_spread_cut_signal(ff1_pct, ff6_pct, threshold_bp=-12.5):
    """True when the 6-month-out fed funds future sits at least 12.5bp below the 1-month one.

    Inputs are implied RATES in percent (100 minus futures price), not prices. NaN gives False.

    Historically this flagged cuts or no hikes within 6 months. It failed in 2023 (-34bp, then
    +75bp over 6 months), so treat it as a screen, not a rule.
    """
    spread_bp = (np.asarray(ff6_pct, dtype=float) - np.asarray(ff1_pct, dtype=float)) * 100.0
    out = spread_bp <= threshold_bp + 1e-9  # tolerance: an exact -12.5bp must not flip on float noise
    return bool(out) if np.ndim(out) == 0 else out


def curve_inverted(short_pct, long_pct, min_inversion_bp=12.5):
    """True when the longer tenor is at least min_inversion_bp below the shorter one (spread = long - short)."""
    spread_bp = (np.asarray(long_pct, dtype=float) - np.asarray(short_pct, dtype=float)) * 100.0
    out = spread_bp <= -min_inversion_bp + 1e-9  # same float tolerance as the FF6-FF1 screen
    return bool(out) if np.ndim(out) == 0 else out


def fly_2s5s10s_bp(y2_pct, y5_pct, y10_pct):
    """2s5s10s fly in bp: 2*y5 - y2 - y10. Positive means the belly is cheap (high yield)."""
    y2 = np.asarray(y2_pct, dtype=float)
    y5 = np.asarray(y5_pct, dtype=float)
    y10 = np.asarray(y10_pct, dtype=float)
    out = (2.0 * y5 - y2 - y10) * 100.0
    return float(out) if np.ndim(out) == 0 else out


def _selftest():
    failures = []

    def check(name, got, want, tol=1e-9):
        ok = abs(got - want) <= tol if isinstance(want, float) else got == want
        if not ok:
            failures.append(f"{name}: got {got!r}, want {want!r}")

    # Off-equilibrium Taylor case: pi=3, gap=1 -> 2 + 3 + 0.5*(3-2) + 0.5*1 = 6.0.
    # On-target cases (pi=2, gap=0) cannot detect a wrong weight, so they are not used here.
    check("taylor off-equilibrium", taylor_rate(3.0, 1.0), 6.0)
    check("taylor Duering form", taylor_rate(3.0, 1.0), 3.0 + 1.0 / 2 + (3.0 - 2.0) / 2 + 2.0)
    # Known answer from the textbook formula: pi=4, gap=-2 -> 2 + 4 + 1 - 1 = 6.0.
    check("taylor negative gap", taylor_rate(4.0, -2.0), 6.0)
    # 10bp priced over one 25bp step is a 40% probability (worked example in the skill).
    check("hike prob 10bp of 25", implied_hike_prob(3.85, 3.75, 25.0), 0.4)
    check("hike prob full step", implied_hike_prob(4.00, 3.75, 25.0), 1.0)
    moves = meeting_moves_bp(3.75, [3.85, 4.10])
    check("meeting moves first", float(moves[0]), 10.0)
    check("meeting moves second", float(moves[1]), 25.0)
    check("ff cut signal on", ff_spread_cut_signal(3.50, 3.30), True)
    check("ff cut signal off", ff_spread_cut_signal(3.50, 3.45), False)
    check("inversion on", curve_inverted(4.00, 3.85), True)
    check("inversion off", curve_inverted(4.00, 3.95), False)
    check("fly 2s5s10s", fly_2s5s10s_bp(2.0, 2.6, 3.0), 20.0)
    check("fly sign on zero", fly_2s5s10s_bp(2.0, 2.5, 3.0), 0.0)
    # Boundary: exactly -12.5bp qualifies for both screens (binary-exact inputs, tolerance guards the rest).
    check("ff boundary", ff_spread_cut_signal(3.50, 3.375), True)
    check("inversion boundary", curve_inverted(4.00, 3.875), True)
    # Float-noise boundary: (3.879 - 4.004)*100 = -12.499999999999956, still exactly a 12.5bp inversion.
    check("inversion noisy boundary", curve_inverted(4.004, 3.879), True)
    check("ff noisy boundary", ff_spread_cut_signal(4.004, 3.879), True)
    # Monthly-average future: 30-day month, meeting after 10 days, old rate 3.75, month avg 3.85
    # -> (3.85*30 - 3.75*10)/20 = 3.90 (15bp, i.e. 60% of a step; the raw average would show only 40%).
    check("post-meeting rate", post_meeting_rate(3.85, 3.75, 10, 30), 3.90, tol=1e-9)
    check("nan screen is False", ff_spread_cut_signal(3.50, float("nan")), False)

    if failures:
        print("SELFTEST FAILED")
        for f in failures:
            print("  " + f)
        return 1
    print("selftest passed")
    return 0


def _cli(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("taylor")
    t.add_argument("--pi", type=float, required=True, help="inflation, percent")
    t.add_argument("--gap", type=float, default=0.0, help="output or unemployment gap, percent")
    t.add_argument("--r-star", type=float, default=2.0)
    t.add_argument("--pi-star", type=float, default=2.0)
    s = sub.add_parser("strip")
    s.add_argument("--csv", required=True)
    s.add_argument("--current", type=float, required=True, help="current policy rate, percent")
    s.add_argument("--step-bp", type=float, default=25.0)
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.cmd == "taylor":
        print(f"{taylor_rate(args.pi, args.gap, args.r_star, args.pi_star):.4f}")
        return 0
    if args.cmd == "strip":
        import pandas as pd

        df = pd.read_csv(args.csv, parse_dates=["meeting_date"]).sort_values("meeting_date")
        moves = meeting_moves_bp(args.current, df["implied_avg_rate_pct"].to_numpy())
        out = df[["meeting_date"]].copy()
        out["move_bp"] = moves
        out["p_full_step"] = moves / args.step_bp  # signed: negative = cut probability
        out["flag"] = np.select(
            [out["p_full_step"].isna(), out["p_full_step"].abs() > 1, out["p_full_step"] < 0],
            ["missing", "multi-step or premium", "cut"],
            default="",
        )
        print(out.to_string(index=False))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
