#!/usr/bin/env python3
"""SDR and dealer-flow metrics for G10 swap RV.

Library use (pandas / numpy objects):
    par_fixed_leg_dv01, horizon_sd_bp, price_forming, offset_sign,
    mean_offsetting_ratio, imm_roll_naive, hhi

CLI (canonical CSV paths; see SKILL.md for the column contract):
    python -I scripts/sdr_flow_metrics.py --selftest
    python -I scripts/sdr_flow_metrics.py --flows flows_trades.csv
    python -I scripts/sdr_flow_metrics.py --dealer-flow dealer_flow.csv --window-min 30 60

Conventions: DV01 is currency per bp, positive = long duration (receive fixed).
Shares for HHI are in percent (10 equal firms = 1000).
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd

BP = 1e-4
DROP_ACTIONS = ("cancel", "error")          # the print itself is removed
REF_ACTIONS = ("cancel", "error", "correct")  # the print they point at is removed


def par_fixed_leg_dv01(notional: float, tenor_years: float, rate_pct: float, freq: int = 1,
                       dcf_scale: float = 1.0) -> float:
    """DV01 of the fixed annuity of a par swap at a flat yield (floating-leg DV01 ignored).

    A = (1 - (1 + y/f)^(-n)) / y with n = tenor * f and y = rate_pct / 100.
    DV01 = notional * 1e-4 * A * dcf_scale. Returns a positive number (magnitude).
    dcf_scale = average accrual factor x f: 1.0 for 30/360, about 365/360 = 1.0139 for an annual ACT/360
    fixed leg (SOFR/EUR RFR swaps), about 1.0 for ACT/365F annual. Discounting is not re-based (approximation).
    """
    y = rate_pct / 100.0
    n = tenor_years * freq
    if abs(y) < 1e-12:
        annuity = tenor_years
    else:
        annuity = (1.0 - (1.0 + y / freq) ** (-n)) / y
    return float(notional * BP * annuity * dcf_scale)


def horizon_sd_bp(daily_sd_bp: float, days: int = 63) -> float:
    """Square-root-of-time translation of a daily rate sd to a horizon sd (bp)."""
    return float(daily_sd_bp * math.sqrt(days))


def pnl_sd(dv01_per_bp: float, daily_sd_bp: float, days: int = 63) -> float:
    """Horizon P&L sd in currency: horizon rate sd (bp) times DV01 (ccy per bp)."""
    return horizon_sd_bp(daily_sd_bp, days) * dv01_per_bp


def price_forming(flows: pd.DataFrame, drop_packages: bool = True) -> pd.DataFrame:
    """Keep print-level rows that represent economic trades.

    Netting: a row referenced by a later cancel, error or correct is removed, and cancel/error
    rows are removed; the corrected row (action 'correct') is kept as the new version.
    Also removes compression rows and, by default, package legs.
    Expects columns: trade_uid, action, orig_trade_uid, is_compression, is_package.
    """
    f = flows.copy()
    action = f["action"].fillna("new").astype(str).str.lower()
    refs = set(f.loc[action.isin(REF_ACTIONS), "orig_trade_uid"].dropna().astype(str))
    keep = ~f["trade_uid"].astype(str).isin(refs) & ~action.isin(DROP_ACTIONS)
    keep &= ~f["is_compression"].fillna(False).astype(bool)
    if drop_packages:
        keep &= ~f["is_package"].fillna(False).astype(bool)
    return f.loc[keep]


def offset_sign(d2c_net, d2d_net) -> np.ndarray:
    """Riggs-style offset sign per dealer-day (inputs are signed net DV01 on D2C and D2D venues).

    -1 = opposite sides (client flow offloaded in D2D), +1 = same side, 0 = one side zero,
    NaN = both zero (dropped from the statistic).
    """
    a = np.asarray(d2c_net, dtype=float)
    b = np.asarray(d2d_net, dtype=float)
    same = np.sign(a) * np.sign(b)
    out = np.where((a == 0) & (b == 0), np.nan, np.where((a == 0) | (b == 0), 0.0, same))
    return out


def mean_offsetting_ratio(flows: pd.DataFrame, window_min: float = 30.0):
    """Mean Offsetting Ratio after each large trade (Fleming et al. definition).

    For a large trade L by dealer d in currency c at time t:
        MOR_L = (DV01 traded opposite in (t, t+window] - DV01 traded same way) / |DV01_L|
    Columns: ts (UTC datetime), dealer, ccy, dv01 (signed, sign = dealer direction), large (bool).
    The caller sets `large` (for example DV01 above the 95th percentile of its tenor bucket).
    Returns (mean over large trades, per-trade DataFrame). Large trades with no later
    trades in the window count as 0.
    """
    f = flows.sort_values("ts").reset_index(drop=True)
    rec = []
    win = np.timedelta64(int(round(window_min * 60)), "s")
    for (dealer, ccy), g in f.groupby(["dealer", "ccy"], sort=False):
        ts = g["ts"].to_numpy(dtype="datetime64[ns]")
        dv = g["dv01"].to_numpy(dtype=float)
        lg = g["large"].fillna(False).to_numpy(dtype=bool)
        for k in np.flatnonzero(lg):
            m = (ts > ts[k]) & (ts <= ts[k] + win)
            opp = np.abs(dv[m & (np.sign(dv) != np.sign(dv[k]))]).sum()
            same = np.abs(dv[m & (np.sign(dv) == np.sign(dv[k]))]).sum()
            rec.append({"dealer": dealer, "ccy": ccy, "ts": ts[k], "dv01_large": abs(dv[k]),
                        "opp_dv01": opp, "same_dv01": same,
                        "mor": (opp - same) / abs(dv[k]) if dv[k] != 0 else np.nan})
    per = pd.DataFrame(rec)
    mean = float(per["mor"].fillna(0.0).mean()) if len(per) else float("nan")
    return mean, per


def imm_roll_naive(mar_notional: float, jun_notional: float) -> float:
    """Naive IMM-roll volume: the smaller of the March-start and June-start volumes is assumed
    rolled, and doubled because both legs trade. Same units as inputs."""
    return 2.0 * min(mar_notional, jun_notional)


def hhi(shares_pct) -> float:
    """Herfindahl-Hirschman index of percentage shares (10 equal firms = 1000)."""
    s = np.asarray(shares_pct, dtype=float)
    return float(np.sum(s ** 2))


# ----------------------------------------------------------------------------- self-test

def _selftest() -> int:
    fails = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"{'PASS' if ok else 'FAIL'} {name}: got {got:.6f} want {want:.6f}")
        if not ok:
            fails.append(name)

    # 1. Par fixed-leg DV01, 10y at 2%, 100m, annual: explicit sum of discounted annuity.
    explicit = sum(1.02 ** (-i) for i in range(1, 11))
    check("par DV01 10y 2% 100m (explicit sum)", par_fixed_leg_dv01(100e6, 10, 2.0, 1),
          1e8 * BP * explicit, 1e-6)
    check("par DV01 magnitude near 90k/bp", par_fixed_leg_dv01(100e6, 10, 2.0, 1), 89826.0, 1.0)
    # semi-annual with the same yield: closed form must differ from annual (more periods, smaller tau)
    sa = sum(0.5 * (1.01) ** (-i) for i in range(1, 21))
    check("par DV01 semi-annual (explicit sum)", par_fixed_leg_dv01(100e6, 10, 2.0, 2),
          1e8 * BP * sa, 1e-6)

    check("par DV01 ACT/360 scale = x365/360", par_fixed_leg_dv01(100e6, 10, 2.0, 1, 365 / 360),
          1e8 * BP * explicit * 365 / 360, 1e-6)

    # 2. Horizon translation: 5bp daily sd over 63 days = 5*sqrt(63) = 39.686bp.
    check("horizon sd 5bp daily over 63d", horizon_sd_bp(5.0, 63), 5.0 * math.sqrt(63), 1e-9)
    check("quarterly P&L sd = 5*sqrt(63) * DV01 (DV01 = 100k)", pnl_sd(100_000.0, 5.0, 63),
          5.0 * math.sqrt(63) * 100_000.0, 1e-6)

    # 3. Price-forming netting. Survivors must be exactly A (plain new) and C (correction of B).
    flows = pd.DataFrame({
        "trade_uid": ["A", "B", "C", "D", "E", "F", "G"],
        "action": ["new", "new", "correct", "new", "cancel", "new", "new"],
        "orig_trade_uid": [None, None, "B", None, "D", None, None],
        "is_compression": [False, False, False, False, False, True, False],
        "is_package": [False, False, False, False, False, False, True],
    })
    kept = sorted(price_forming(flows)["trade_uid"].tolist())
    check("price_forming survivors == [A, C]", float(kept == ["A", "C"]), 1.0, 0.0)

    # 4. Offset sign: -1 opposite, +1 same, 0 one side zero, NaN both zero.
    s = offset_sign([10, -5, 0, 0], [-4, -3, 2, 0])
    check("offset sign opposite", s[0], -1.0, 0.0)
    check("offset sign same", s[1], 1.0, 0.0)
    check("offset sign one side zero", s[2], 0.0, 0.0)
    check("offset sign both zero is NaN", float(np.isnan(s[3])), 1.0, 0.0)

    # 5. Mean Offsetting Ratio. Large trade +50k at t=0. In 30m: -30k (opposite), +5k (same).
    #    A -10k print at 40m is outside 30m, inside 60m. Known answers: 0.5 at 30m, 0.7 at 60m.
    t0 = pd.Timestamp("2026-11-10 10:00:00")
    mor_rows = pd.DataFrame({
        "ts": [t0, t0 + pd.Timedelta("10min"), t0 + pd.Timedelta("20min"),
               t0 + pd.Timedelta("40min"), t0 + pd.Timedelta("15min")],
        "dealer": ["D1"] * 5, "ccy": ["USD"] * 5,
        "dv01": [50_000.0, -30_000.0, 5_000.0, -10_000.0, 1_000.0],
        "large": [True, False, False, False, False],
    })
    m30, _ = mean_offsetting_ratio(mor_rows, 30)
    check("MOR 30m = (30-6)/50 = 0.48", m30, 0.48, 1e-9)
    m60, _ = mean_offsetting_ratio(mor_rows, 60)
    check("MOR 60m = (40-6)/50 = 0.68", m60, 0.68, 1e-9)

    # 6. Naive IMM roll: 15.999bn March vs 13.25bn June -> 2 * 13.25 = 26.5bn.
    check("IMM naive roll", imm_roll_naive(15.999, 13.25), 26.5, 1e-9)

    # 7. HHI: ten equal 10% firms = 1000.
    check("HHI ten equal firms", hhi([10] * 10), 1000.0, 1e-9)

    if fails:
        print(f"SELFTEST FAILED: {len(fails)} check(s): {', '.join(fails)}")
        return 1
    print("SELFTEST OK")
    return 0


# ----------------------------------------------------------------------------- CLI

def _cli_flows(path: str) -> None:
    f = pd.read_csv(path)
    f["is_compression"] = f.get("is_compression", False)
    f["is_package"] = f.get("is_package", False)
    kept = price_forming(f)
    print(f"raw prints: {len(f)}   price-forming: {len(kept)} ({len(kept) / max(len(f), 1):.1%})")
    for col in ("is_package", "is_compression", "notional_capped"):
        if col in f:
            share = f[col].fillna(False).astype(bool).mean()
            print(f"share {col} (raw): {share:.1%}")
    grp = kept.groupby(["ccy", "product"]).size().rename("price_forming_prints")
    print(grp.to_string())


def _cli_dealer(path: str, windows) -> None:
    d = pd.read_csv(path).rename(columns={"exec_ts_utc": "ts", "dealer_id": "dealer", "dv01_ccy": "dv01",
                                          "is_large": "large"})  # canonical dealer_flow -> short names
    if "large" not in d:
        sys.exit("dealer-flow file needs is_large (or large): the offsetting ratio is defined on large prints")
    d["ts"] = pd.to_datetime(d["ts"], utc=True).dt.tz_localize(None)
    d["large"] = d["large"].astype(str).str.lower().isin(("true", "1"))
    for w in windows:
        mean, per = mean_offsetting_ratio(d, w)
        print(f"window {w:g}m: mean MOR {mean:.3f} over {len(per)} large trades")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="run known-answer checks and exit")
    ap.add_argument("--flows", help="flows_trades CSV (canonical columns)")
    ap.add_argument("--dealer-flow", help="dealer_flow CSV: dealer_id,exec_ts_utc,ccy,dv01_ccy,is_large (or ts,dealer,ccy,dv01,large)")
    ap.add_argument("--window-min", type=float, nargs="+", default=[30.0, 60.0, 240.0, 480.0])
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.flows:
        _cli_flows(a.flows)
    if a.dealer_flow:
        _cli_dealer(a.dealer_flow, a.window_min)
    if not (a.flows or a.dealer_flow):
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
