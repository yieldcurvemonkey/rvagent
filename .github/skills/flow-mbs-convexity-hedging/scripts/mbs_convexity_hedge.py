#!/usr/bin/env python3
"""Agency MBS arithmetic: CPR/SMM, level-pay balances, effective duration and convexity,
drift convexity, and the 10y-equivalent convexity-hedge need.

Conventions
- Prices per 100 face. Shocks in bp. Durations in years.
- Effective duration D = (P_dn - P_up) / (2 P0 dy); effective (standard) convexity
  C = (P_up + P_dn - 2 P0) / (P0 dy^2) with dy in decimal yield. Prepayments held
  fixed inside each shock unless the caller models them.
- Drift convexity C_d = -dD/dy_pct (duration change per 1% yield move, sign flipped).
  MBS and callables are negative (duration extends as yields rise). This is the
  "convexity" used by the hedge-need recipe. It is NOT the standard convexity above:
  do not mix the two scales.
- Per-1% drift from standard measures: C_d = (C - D^2) / 100 (drift_from_standard).
- Dollar roll: roll_value and implied_financing (actual/360, invoices include accrued).
- Hedge need in $bn of 10y-equivalents = duration * amount / 10. Negative = sell
  duration (receive fixed / sell UST); positive = buy duration.

CLI
  python -I scripts/mbs_convexity_hedge.py --selftest
  python -I scripts/mbs_convexity_hedge.py --hedge-need --duration 7 --amount-bn 100 \
        --convexity=-2 --moves-bp=25,50,100
  python -I scripts/mbs_convexity_hedge.py --hedge-need --duration 7 --amount-bn 100 \
        --convexity=-2 --moves-bp=-25,-50,-100          (rallies: note the = sign)
  python -I scripts/mbs_convexity_hedge.py --scenario-px prices.csv --out eff.csv
      prices.csv (or .parquet) columns: date, instrument_id, px_base, px_up, px_dn, dy_bp
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- prepayment math
def smm_to_cpr(smm):
    """Annualised CPR from a constant single-month rate: CPR = 1 - (1 - SMM)^12."""
    return 1.0 - (1.0 - np.asarray(smm, dtype=float)) ** 12


def cpr_to_smm(cpr):
    """Inverse of smm_to_cpr: SMM = 1 - (1 - CPR)^(1/12)."""
    return 1.0 - (1.0 - np.asarray(cpr, dtype=float)) ** (1.0 / 12.0)


def cpr_from_monthly(smm_path):
    """CPR over a path of monthly SMMs: 1 - prod(1 - SMM_i)^(12/n).

    For n = 3 this is the book's exponent-4 form. It reduces to smm_to_cpr when all
    SMMs are equal.
    """
    s = np.asarray(smm_path, dtype=float)
    return 1.0 - float(np.prod(1.0 - s)) ** (12.0 / len(s))


def level_payment(balance, rate_pct, n_months):
    """Level monthly payment X = B0 * (r/12) / (1 - (1 + r/12)^-N), rate in percent."""
    m = rate_pct / 100.0 / 12.0
    if m == 0:
        return balance / n_months
    return balance * m / (1.0 - (1.0 + m) ** (-n_months))


def balance_path(balance, rate_pct, n_months, months=None):
    """Scheduled balance after each month (no prepayments). Returns pd.Series indexed by month."""
    m = rate_pct / 100.0 / 12.0
    x = level_payment(balance, rate_pct, n_months)
    months = range(1, n_months + 1) if months is None else months
    out, b = {}, float(balance)
    for i in range(1, max(months) + 1):
        b = b * (1.0 + m) - x
        if i in months:
            out[i] = b
    return pd.Series(out, name="balance")


# ---------------------------------------------------------------- price-based measures
def effective_duration(px_base, px_up, px_dn, dy_bp):
    """Effective (curve-shift) duration: (P_dn - P_up) / (2 * P0 * dy). Prices per 100."""
    dy = dy_bp / 10000.0
    return (np.asarray(px_dn) - np.asarray(px_up)) / (2.0 * np.asarray(px_base) * dy)


def effective_convexity(px_base, px_up, px_dn, dy_bp):
    """Standard effective convexity: (P_up + P_dn - 2 P0) / (P0 * dy^2), dy in decimal."""
    dy = dy_bp / 10000.0
    return (np.asarray(px_up) + np.asarray(px_dn) - 2.0 * np.asarray(px_base)) / (
        np.asarray(px_base) * dy * dy
    )


def drift_convexity(dur_up, dur_dn, dy_bp):
    """Duration-drift convexity C = -dD/dy_pct, from durations at +dy_bp and -dy_bp.

    Negative for MBS and callables. Positive for non-callable bullets. Equals
    OAC - OAD^2 in the usual notation (per 1% yield).
    """
    dy_pct = dy_bp / 100.0
    return -(np.asarray(dur_up) - np.asarray(dur_dn)) / (2.0 * dy_pct)


def drift_from_standard(duration, convexity):
    """Per-1% drift convexity from standard measures: C_d = (C - D^2) / 100.

    D in years, C standard (dy in decimal). Derived from -dD/dy = C - D^2 per unit yield.
    """
    return (np.asarray(convexity, dtype=float) - np.asarray(duration, dtype=float) ** 2) / 100.0


# ---------------------------------------------------------------- dollar roll
def roll_value(hold_value, s_sell, s_buy, days, repo, basis=360.0):
    """Roll value = (sale invoice + reinvestment at repo - rebuy invoice) - hold value.

    Invoices include accrued interest; repo is a decimal rate (0.001 = 10bp).
    """
    return s_sell + s_sell * repo * days / basis - s_buy - hold_value


def implied_financing(hold_value, s_sell, s_buy, days, basis=360.0):
    """Reinvestment rate (decimal) that sets roll value to zero. Specialness = repo - this."""
    return (hold_value - (s_sell - s_buy)) / (s_sell * days / basis)


# ---------------------------------------------------------------- hedge need
def hedge_need(duration, amount_bn, convexity_drift, moves_bp):
    """10y-equivalent hedge need over parallel moves (BofA primer recipe).

    10y_eq = duration * amount / 10
    new_duration = duration + (move_bp / 100) * (-convexity_drift)
    hedge_need = base_10y_eq - new_10y_eq   (negative = sell duration)
    Returns a DataFrame with one row per move.
    """
    moves = np.asarray(list(moves_bp), dtype=float)
    base_eq = duration * amount_bn / 10.0
    new_dur = duration + (moves / 100.0) * (-convexity_drift)
    new_eq = new_dur * amount_bn / 10.0
    return pd.DataFrame(
        {
            "move_bp": moves,
            "duration_new": new_dur,
            "tenY_eq_base_bn": base_eq,
            "tenY_eq_new_bn": new_eq,
            "hedge_need_bn": base_eq - new_eq,
        }
    )


# ---------------------------------------------------------------- I/O
def _load_table(path):
    """Canonical CSV or Parquet table into a DataFrame."""
    p = Path(path)
    if p.suffix.lower() == ".parquet":
        return pd.read_parquet(p)
    return pd.read_csv(p)


# ---------------------------------------------------------------- self-test
def _close(a, b, tol, label, fails):
    ok = abs(float(a) - float(b)) <= tol
    print(f"{'PASS' if ok else 'FAIL'} {label}: got {float(a):.6f} want {float(b):.6f}")
    if not ok:
        fails.append(label)


def selftest() -> int:
    fails: list[str] = []
    # 1. Prepayment: SMM 2% -> CPR 21.53% (book); multi-month form agrees.
    _close(smm_to_cpr(0.02), 0.2152833, 1e-6, "CPR from SMM 2%", fails)
    _close(cpr_from_monthly([0.02, 0.02, 0.02]), smm_to_cpr(0.02), 1e-12, "CPR path == constant", fails)
    _close(cpr_to_smm(smm_to_cpr(0.02)), 0.02, 1e-12, "SMM round trip", fails)
    # 2. Level pay: $100k, 4.5%, 360m -> 506.6853; balances 99,868.31 / 91,157.92 / 80,089.43.
    _close(level_payment(100000, 4.5, 360), 506.6853, 5e-5, "level payment", fails)
    bp = balance_path(100000, 4.5, 360, months=[1, 60, 120])
    _close(bp[1], 99868.31, 0.01, "balance month 1", fails)
    _close(bp[60], 91157.92, 0.01, "balance month 60", fails)
    _close(bp[120], 80089.43, 0.01, "balance month 120", fails)
    # 3. Hedge need (BofA primer): duration 7, $100bn, convexity -2 -> need -5/-10/-20 bn on +25/+50/+100.
    hn = hedge_need(7.0, 100.0, -2.0, [25, 50, 100])
    _close(hn.loc[0, "hedge_need_bn"], -5.0, 1e-9, "hedge need +25bp", fails)
    _close(hn.loc[1, "hedge_need_bn"], -10.0, 1e-9, "hedge need +50bp", fails)
    _close(hn.loc[2, "hedge_need_bn"], -20.0, 1e-9, "hedge need +100bp", fails)
    _close(hn.loc[2, "duration_new"], 9.0, 1e-9, "duration after +100bp", fails)
    # 3b. Same recipe, rallies: duration shortens, so hedgers must BUY duration (+5/+10/+20 bn).
    hr = hedge_need(7.0, 100.0, -2.0, [-25, -50, -100])
    _close(hr.loc[0, "duration_new"], 6.5, 1e-9, "duration after -25bp", fails)
    _close(hr.loc[2, "hedge_need_bn"], 20.0, 1e-9, "hedge need -100bp (buy)", fails)
    # 4. Effective duration/convexity of a zero: P=(1+y)^-10, y=4%.
    #    D = T/(1+y); standard convexity = T(T+1)/(1+y)^2 (analytic).
    y, T, dy = 0.04, 10.0, 1.0
    p0 = (1 + y) ** -T
    pu = (1 + y + dy / 1e4) ** -T
    pd_ = (1 + y - dy / 1e4) ** -T
    _close(effective_duration(p0, pu, pd_, dy), T / (1 + y), 1e-4, "zero effective duration", fails)
    _close(effective_convexity(p0, pu, pd_, dy), T * (T + 1) / (1 + y) ** 2, 1e-3, "zero convexity", fails)
    # 5. Drift convexity of the same zero: D(y)=T/(1+y), C_d = -dD/dy_pct = T/(100(1+y)^2).
    d_up = T / (1 + y + 0.005)
    d_dn = T / (1 + y - 0.005)
    _close(drift_convexity(d_up, d_dn, 50.0), T / (100 * (1 + y) ** 2), 1e-5, "zero drift convexity", fails)
    # 6. Bassman pair (Leverage is NOT a four-letter Word, 26 Jan 2023): UST 10y and FN 4.5%.
    _close(effective_duration(105.06, 96.96, 113.96, 100), 8.09, 5e-3, "UST pair duration", fails)
    _close(effective_convexity(105.06, 96.96, 113.96, 100), 76.1, 0.1, "UST pair convexity (+)", fails)
    _close(effective_duration(98.44, 96.22, 100.11, 50), 3.95, 5e-3, "MBS pair duration", fails)
    _close(effective_convexity(98.44, 96.22, 100.11, 50), -223.5, 0.5, "MBS pair convexity (-)", fails)
    # 6b. Drift from standard: zero-coupon, C_d = T / (100 (1+y)^2) (same as test 5).
    _close(drift_from_standard(T / (1 + y), T * (T + 1) / (1 + y) ** 2), T / (100 * (1 + y) ** 2), 1e-12, "drift from standard", fails)
    # 7. Dollar roll (Tuckman & Serrat 2022, Ch.15): hold 10,849.67, sell 1,019,583.33, rebuy 1,008,201.83,
    #    32 days, repo 10bp -> roll value 622.46; implied financing -58.7bp on these cash flows (book prints -58.4bp).
    _close(roll_value(10849.67, 1019583.33, 1008201.83, 32, 0.001), 622.46, 0.01, "roll value", fails)
    f = implied_financing(10849.67, 1019583.33, 1008201.83, 32)
    _close(f * 1e4, -58.68, 0.02, "implied financing bp", fails)
    _close(roll_value(10849.67, 1019583.33, 1008201.83, 32, f), 0.0, 1e-6, "roll value zero at implied financing", fails)
    if fails:
        print(f"SELFTEST FAILED: {len(fails)} check(s): {', '.join(fails)}")
        return 1
    print("SELFTEST OK")
    return 0


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--hedge-need", action="store_true")
    ap.add_argument("--duration", type=float, help="MBS duration, years")
    ap.add_argument("--amount-bn", type=float, help="position size, $bn face")
    ap.add_argument("--convexity", type=float, help="drift convexity, recipe units (MBS negative)")
    ap.add_argument("--moves-bp", default="25,50,100", help="comma list; use --moves-bp=-25,-50 for rallies")
    ap.add_argument("--scenario-px", help="table: date, instrument_id, px_base, px_up, px_dn, dy_bp (.csv/.parquet)")
    ap.add_argument("--out", help="output CSV for --scenario-px")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.hedge_need:
        if None in (a.duration, a.amount_bn, a.convexity):
            print("--hedge-need needs --duration, --amount-bn and --convexity", file=sys.stderr)
            return 2
        moves = [float(x) for x in a.moves_bp.split(",")]
        print(hedge_need(a.duration, a.amount_bn, a.convexity, moves).to_string(index=False))
        return 0
    if a.scenario_px:
        df = _load_table(a.scenario_px)
        need = {"instrument_id", "px_base", "px_up", "px_dn", "dy_bp"}
        if not need.issubset(df.columns):
            print(f"missing columns: {sorted(need - set(df.columns))}", file=sys.stderr)
            return 2
        if (df.dy_bp == 0).any():
            print("dy_bp must be non-zero", file=sys.stderr)
            return 2
        df["eff_duration"] = effective_duration(df.px_base, df.px_up, df.px_dn, df.dy_bp)
        df["eff_convexity"] = effective_convexity(df.px_base, df.px_up, df.px_dn, df.dy_bp)
        keep = [c for c in ["date", "instrument_id", "eff_duration", "eff_convexity"] if c in df.columns]
        out = df[keep]
        if a.out:
            out.to_csv(a.out, index=False)
        else:
            print(out.to_string(index=False))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
