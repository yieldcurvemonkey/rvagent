#!/usr/bin/env python3
"""Transaction-cost arithmetic for G10 rates RV backtests.

Conventions: half-spread = ONE-WAY mid-to-bid/offer in bp of rate (or bp of yield). DV01 is currency per bp.
cost_ccy = |DV01 traded| x half_spread_bp x cost_mult  (always >= 0 here; the CLI writes it <= 0 to match the
canonical `pnl.cost_ccy` sign). Costs are charged on the TRADED INCREMENT (change in DV01), never on the position.
Caveats: DV01 of a constant-notional hold drifts daily, so use drift_tol (or difference notional) to avoid phantom trades;
a roll with unchanged DV01 shows no trade, so give each contract its own leg; flat days need explicit zero rows.

Functions
  leg_cost_ccy          one-way cost of trading a DV01 amount.
  increment_cost        per-date cost of a DV01 path (entry, resizes, optional terminal liquidation).
  package_cost          one-way cost of a multi-leg package; also bp per gross DV01.
  breakeven_hold_days   days of carry needed to repay a round-trip cost (NaN if carry <= 0).
  net_edge_bp           gross edge + carry - round-trip cost.
  annualised_cost       round-trip cost / holding period in years.
  price_to_yield_bp     price-point spread -> bp of yield: pts / (ModDur x Price / 10000).
  impact_addon_ccy      square-root impact add-on (2/3) alpha ((|I+x|)^1.5 - |I|^1.5), inventory aware.
  quote_cost_ccy        core half-spread cost plus (liquidity-scaled) add-on, floored at 0.
  roll_half_spread      Roll (1984) half-spread from the lag-1 autocovariance of price changes.
  amihud                mean(|ret| / volume).
  ma_round_turns        expected round turns of a moving-average rule on a random walk (Lequeux).

CLI
  python costs.py cost-path --positions positions.csv --half-spread-bp 0.4 [--hs-table hs.csv] [--mult 1]
        [--sweep 0,0.5,1,2] [--no-liquidate] [--drift-tol 0.02] [--out costs.csv]
      positions.csv = canonical `positions` (date, strategy_id, package_id, leg, dv01_ccy [, instrument_id]).
      hs.csv (optional) = instrument_id, half_spread_bp (overrides the scalar per leg).
  python costs.py breakeven --round-trip-bp 1.0 --carry-bp-day 0.02
  python costs.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


def leg_cost_ccy(dv01_traded, half_spread_bp, cost_mult=1.0):
    return np.abs(dv01_traded) * half_spread_bp * cost_mult


def traded_dv01(dv01, drift_tol=0.0):
    """|day-over-day change| of a signed DV01 path; first day trades the full position. A change smaller than
    drift_tol x |previous DV01| is treated as DV01 drift, not a trade. NaN is an error (a gap is not 'flat')."""
    dv01 = pd.Series(dv01, dtype=float)
    if dv01.isna().any():
        raise ValueError("NaN in DV01 path: fill flat days with 0 explicitly")
    if not len(dv01):
        return dv01
    d = dv01.diff().abs()
    d.iloc[0] = abs(dv01.iloc[0])
    if drift_tol > 0:
        d[d <= drift_tol * dv01.shift().abs()] = 0.0
    return d


def increment_cost(dv01, half_spread_bp, cost_mult=1.0, liquidate=True, drift_tol=0.0):
    """dv01: Series of end-of-day signed DV01 (ccy/bp) for ONE leg, date-ordered.
    Returns (per-date cost Series, terminal liquidation cost). Entry day trades the full position."""
    dv01 = pd.Series(dv01, dtype=float)
    traded = traded_dv01(dv01, drift_tol)
    per_date = traded * half_spread_bp * cost_mult
    term = abs(float(dv01.iloc[-1])) * half_spread_bp * cost_mult if (liquidate and len(dv01)) else 0.0
    return per_date, term


def package_cost(dv01, half_spread_bp, cost_mult=1.0):
    """One-way cost of a package: sum_i |dv01_i| * hs_i. Returns (ccy, bp per gross DV01)."""
    d, h = np.abs(np.asarray(dv01, float)), np.asarray(half_spread_bp, float)
    ccy = float((d * h).sum() * cost_mult)
    gross = float(d.sum())
    return ccy, (ccy / gross if gross else float("nan"))


def breakeven_hold_days(round_trip_bp, carry_bp_per_day):
    """Days of carry to repay the round-trip cost. NaN when carry <= 0 (carry never repays it)."""
    return round_trip_bp / carry_bp_per_day if carry_bp_per_day > 0 else float("nan")


def net_edge_bp(gross_bp, round_trip_bp, carry_bp_per_day=0.0, hold_days=0.0):
    return gross_bp + carry_bp_per_day * hold_days - round_trip_bp


def annualised_cost(round_trip_cost, hold_years):
    return round_trip_cost / hold_years


def price_to_yield_bp(price_pts, mod_dur, price=100.0):
    """Convert a price-point cost per 100 face to bp of yield (price DV01 = ModDur x Price / 10000 per bp)."""
    return price_pts / (mod_dur * price / 10000.0)


def impact_addon_ccy(x, alpha=1e-3, inventory=0.0):
    """(2/3) alpha (|I+x|^1.5 - |I|^1.5). x, inventory in DV01 (ccy/bp); alpha in bp per sqrt(DV01 unit),
    default 1e-3 = 1bp of impact for 1mm DV01. Negative when the trade reduces inventory."""
    return (2.0 / 3.0) * alpha * (abs(inventory + x) ** 1.5 - abs(inventory) ** 1.5)


def quote_cost_ccy(x, core_half_spread_bp, alpha=1e-3, inventory=0.0, liq_scale=1.0, floor=True):
    raw = abs(x) * core_half_spread_bp + liq_scale * impact_addon_ccy(x, alpha, inventory)
    return max(0.0, raw) if floor else raw


def roll_half_spread(prices):
    """Roll half-spread c = sqrt(-Cov(dp_t, dp_t-1)); 0 if the covariance is >= 0; NaN if < 4 prices or any NaN."""
    p = np.asarray(prices, float)
    if len(p) < 4 or np.isnan(p).any():
        return float("nan")
    dp = np.diff(p)
    cov = np.cov(dp[1:], dp[:-1])[0, 1]
    return float(np.sqrt(max(0.0, -cov)))


def amihud(ret, volume):
    ret, vol = np.asarray(ret, float), np.asarray(volume, float)
    m = (vol > 0) & np.isfinite(ret) & np.isfinite(vol)
    return float(np.mean(np.abs(ret[m]) / vol[m])) if m.any() else float("nan")


def ma_round_turns(m, T):
    """E(N) = 1 + (T-2)(1/2 - arcsin(rho_F)/pi) for an m-day moving-average rule on T days of a random walk."""
    if m < 2:
        raise ValueError("moving-average window m must be >= 2")
    i = np.arange(0, m - 1)
    num = ((m - i - 1) * (m - i - 2)).sum()
    den = ((m - i - 1) ** 2).sum()
    return 1 + (T - 2) * (0.5 - np.arcsin(num / den) / np.pi)


def run_cost_path(a):
    pos = pd.read_parquet(a.positions) if a.positions.endswith(".parquet") else pd.read_csv(a.positions)
    pos = pos.sort_values("date")
    hs = None
    if a.hs_table:
        t = pd.read_parquet(a.hs_table) if a.hs_table.endswith(".parquet") else pd.read_csv(a.hs_table)
        hs = t.set_index("instrument_id")["half_spread_bp"]
    mults = [float(s) for s in a.sweep.split(",")] if a.sweep else [a.mult]
    rows, totals = [], {m: 0.0 for m in mults}
    for (sid, pid, leg), g in pos.groupby(["strategy_id", "package_id", "leg"]):
        h = a.half_spread_bp
        if hs is not None and "instrument_id" in g:
            h = float(hs.get(g["instrument_id"].iloc[-1], a.half_spread_bp))
        for m in mults:
            per, term = increment_cost(g["dv01_ccy"].to_numpy(), h, m, liquidate=not a.no_liquidate, drift_tol=a.drift_tol)
            totals[m] += per.sum() + term
            if len(mults) == 1:  # per-row detail only for a single multiple; a sweep prints totals
                for d, c, tr in zip(g["date"], per, traded_dv01(g["dv01_ccy"].to_numpy(), a.drift_tol)):
                    rows.append((d, sid, pid, leg, tr, -c))
                if term:
                    rows.append(("LIQUIDATION", sid, pid, leg, abs(g["dv01_ccy"].iloc[-1]), -term))
    out = pd.DataFrame(rows, columns=["date", "strategy_id", "package_id", "leg", "traded_dv01_ccy", "cost_ccy"])
    if a.out:
        out.to_csv(a.out, index=False)
    elif len(out):
        print(out.to_string(index=False))
    for m, v in totals.items():
        print(f"cost_mult {m:g}: total cost_ccy {-v:,.2f}")


def selftest():
    ok = True

    def check(label, got, want, tol=1e-6):
        nonlocal ok
        good = (np.isnan(got) and np.isnan(want)) or abs(got - want) <= tol
        ok &= bool(good)
        print(f"{'ok  ' if good else 'FAIL'} {label}: got {got:.6g} want {want:.6g}")

    # 1. leg cost: 10,000 ccy/bp x 0.4bp = 4,000; sweep multiple scales linearly; sign of DV01 irrelevant
    check("leg cost", leg_cost_ccy(-10000, 0.4), 4000.0)
    check("leg cost 2x", leg_cost_ccy(10000, 0.4, 2.0), 8000.0)
    # 2. resize path charged on the increment: 0 -> 100 -> 150 -> 150 -> 0 gives 100+50+0+150 = 300 DV01 traded.
    #    Charging on the position instead would give 100+150+150+0 = 400 and would FAIL this check.
    per, term = increment_cost([100, 150, 150, 0], 0.5, liquidate=True)
    check("increment cost path", float(per.sum()), 300 * 0.5)
    check("no terminal cost when flat", term, 0.0)
    per, term = increment_cost([100, 150, 150], 0.5, liquidate=True)
    check("terminal liquidation", float(per.sum()) + term, (150 + 150) * 0.5)
    # 3. package: fly 100/-200/100 DV01 at 0.4/0.5/0.4bp half-spreads -> 40+100+40 = 180 ccy over 400 gross = 0.45bp
    c, bp = package_cost([100, -200, 100], [0.4, 0.5, 0.4])
    check("package ccy", c, 180.0)
    check("package bp per gross DV01", bp, 0.45)
    # 3b. SKILL worked example A: 2y -5,000 / 5y +10,000 / 10y -5,000 at 0.4/0.5/0.5bp -> 9,500 one way, 0.475bp per gross DV01
    c, bp = package_cost([-5000, 10000, -5000], [0.4, 0.5, 0.5])
    check("example A one-way ccy", c, 9500.0)
    check("example A round trip per belly DV01 (bp)", 2 * c / 10000, 1.9)
    check("example A break-even days", breakeven_hold_days(1.9, 0.01), 190.0)
    # 3c. DV01 drift: a constant-notional hold whose DV01 decays 0.5%/day is not trading; a real 10% resize is
    path = [1000.0, 995.0, 990.0, 1090.0]
    per, term = increment_cost(path, 1.0, liquidate=False, drift_tol=0.02)
    check("drift ignored, resize charged", float(per.sum()), 1000.0 + 100.0)
    check("drift_tol 0 charges every wiggle", float(increment_cost(path, 1.0, liquidate=False)[0].sum()), 1000 + 5 + 5 + 100)
    try:
        increment_cost([100.0, float("nan"), 100.0], 1.0)
        check("NaN DV01 raises", 0.0, 1.0)
    except ValueError:
        check("NaN DV01 raises", 1.0, 1.0)
    # 4. break-even: 1.0bp round trip at 0.02bp/day carry = 50 days; negative or zero carry never breaks even
    check("breakeven days", breakeven_hold_days(1.0, 0.02), 50.0)
    check("negative carry -> NaN", breakeven_hold_days(1.0, -0.02), float("nan"))
    check("zero carry -> NaN", breakeven_hold_days(1.0, 0.0), float("nan"))
    check("net edge", net_edge_bp(3.0, 1.0, 0.02, 30), 2.6)
    # 5. Grinold-Kahn: 1.5 round trip (2 x 0.75); 6m holds repeated -> 3%/yr; 24m hold -> 0.75%/yr
    check("GK 6m: 4% - 3% = 1%", 4.0 - annualised_cost(1.5, 0.5), 1.0)
    check("GK 24m: 4% - 0.75% = 3.25%", 4.0 - annualised_cost(1.5, 2.0), 3.25)
    # 6. 1/256 price tick on a 10y (ModDur 8, price 100) = 0.0039/0.08 = 0.0488bp of yield
    check("tick to yield bp", price_to_yield_bp(1 / 256, 8.0, 100.0), (1 / 256) / 0.08)
    # 7. square-root add-on (Darbyshire): 100k DV01 from flat = 21,081.85; core 0.5bp -> 71,081.85 (0.7108bp)
    check("addon 0->100k", impact_addon_ccy(100000), 21081.85, 0.01)
    check("addon 0->50k", impact_addon_ccy(50000), 7453.56, 0.01)
    check("addon 50k->100k", impact_addon_ccy(50000, inventory=50000), 13628.29, 0.01)
    check("quote 100k", quote_cost_ccy(100000, 0.5), 71081.85, 0.01)
    check("quote bp", quote_cost_ccy(100000, 0.5) / 100000, 0.7108185, 1e-6)
    check("addon reduces inventory", impact_addon_ccy(-50000, inventory=50000), -7453.56, 0.01)
    check("raw reverse quote at 4x scarcity", quote_cost_ccy(-50000, 0.5, inventory=50000, liq_scale=4, floor=False),
          50000 * 0.5 - 4 * 7453.56, 0.1)
    check("floored reverse quote", quote_cost_ccy(-50000, 0.5, inventory=50000, liq_scale=4), 0.0)
    # 8. Amihud exact: |0.01|/100 and |-0.02|/200 are both 1e-4; zero-volume day is skipped
    check("amihud", amihud([0.01, -0.02, 0.5], [100, 200, 0]), 1e-4, 1e-15)
    # 9. Roll: simulate m = random walk (sd 0.02) + c*q, q = +/-1 iid, c = 0.05 -> estimate within 5%
    rng = np.random.default_rng(7)
    n, c_true = 400000, 0.05
    p = np.cumsum(rng.normal(0, 0.02, n)) + c_true * rng.choice([-1.0, 1.0], n)
    check("roll half-spread", roll_half_spread(p), c_true, 0.05 * c_true)
    check("roll short history -> NaN", roll_half_spread([100.0, 100.1, 100.0]), float("nan"))
    check("roll on pure random walk ~0", roll_half_spread(np.cumsum(rng.normal(0, 0.02, n))), 0.0, 0.002)
    # 10. Lequeux round turns (T=250): MA2 -> 125, MA3 -> 92.5 (x 0.03% = 3.75% and 2.77% drag)
    check("MA2 round turns", ma_round_turns(2, 250), 125.0, 1e-9)
    check("MA3 round turns", ma_round_turns(3, 250), 92.5, 0.05)
    check("MA2 drag %", ma_round_turns(2, 250) * 0.03, 3.75, 1e-9)
    return ok


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("cost-path", help="cost of the DV01 paths in a canonical positions table")
    p.add_argument("--positions", required=True)
    p.add_argument("--half-spread-bp", type=float, required=True, help="one-way half-spread, bp")
    p.add_argument("--hs-table")
    p.add_argument("--mult", type=float, default=1.0)
    p.add_argument("--sweep", help="comma list of cost multiples, e.g. 0,0.5,1,2")
    p.add_argument("--no-liquidate", action="store_true")
    p.add_argument("--drift-tol", type=float, default=0.0, help="ignore DV01 changes below this fraction of the position (drift)")
    p.add_argument("--out")
    b = sub.add_parser("breakeven", help="break-even holding period vs carry")
    b.add_argument("--round-trip-bp", type=float, required=True)
    b.add_argument("--carry-bp-day", type=float, required=True)
    a = ap.parse_args()
    if a.cmd == "cost-path":
        run_cost_path(a)
    else:
        d = breakeven_hold_days(a.round_trip_bp, a.carry_bp_day)
        print("never (carry <= 0)" if np.isnan(d) else f"break-even holding period: {d:.1f} days")


if __name__ == "__main__":
    main()
