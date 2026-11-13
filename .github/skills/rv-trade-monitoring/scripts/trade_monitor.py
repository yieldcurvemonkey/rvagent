"""Live monitor for one open relative-value spread trade.

Functions take pandas/numpy objects. The CLI reads a spread CSV with columns `date` and `spread_bp`
(a spread built from canonical curve or bond tables, e.g. 10y minus 2y par rate x 100) and prints a JSON status.

Conventions: spread in bp, curve spread = longer minus shorter, DV01 in currency per bp, positive = long duration,
direction +1 = long the spread (profits when it rises), -1 = short the spread.

Usage:
    python -I scripts/trade_monitor.py --selftest
    python -I scripts/trade_monitor.py --spread data/spread_2s10s.csv --entry-date 2026-03-02 --direction 1 \
        --entry -6 --target -3 --stop -10 --window 252
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np
import pandas as pd


def ou_fit(x, dt: float = 1.0) -> dict:
    """AR(1) fit x_t = a + b x_{t-1}. Discrete OU with phi = b; half-life = -ln(2) / ln(phi) in units of dt.

    Returns nan half-life when phi is outside (0, 1): a random walk or explosive series has no half-life.
    """
    v = np.asarray(x, dtype=float)
    y, xl = v[1:], v[:-1]
    ok = np.isfinite(y) & np.isfinite(xl)  # keep consecutive pairs only: dropping NaNs would fake transitions
    y, xl = y[ok], xl[ok]
    if y.size < 30:
        raise ValueError("need >= 30 consecutive observation pairs for an OU fit")
    b, a = np.polyfit(xl, y, 1)  # slope, intercept
    resid = y - (a + b * xl)
    sd_e = float(np.std(resid, ddof=2))
    mu = a / (1.0 - b) if b != 1.0 else float("nan")
    if 0.0 < b < 1.0 - 1e-9:
        half_life = -math.log(2.0) / math.log(b) * dt
        theta = -math.log(b) / dt
        sd_stat = sd_e / math.sqrt(1.0 - b * b)  # stationary sd of the discrete process
    else:
        half_life, theta, sd_stat = float("nan"), float("nan"), float("nan")
    return {"phi": float(b), "mu": float(mu), "half_life": half_life, "theta": theta,
            "resid_sd": sd_e, "stationary_sd": sd_stat, "n_obs": int(y.size)}


def zscore(x: pd.Series, window: int) -> pd.Series:
    """Rolling z-score of the level versus its trailing mean and sample sd (ddof=1)."""
    m = x.rolling(window).mean()
    s = x.rolling(window).std(ddof=1)
    return (x - m) / s


def pnl_explain(total: float, carry: float, roll: float, dv01: float, dy_bp: float, cost: float = 0.0,
                spread: float = 0.0, convexity: float = 0.0, financing: float = 0.0) -> dict:
    """One-day P&L explain with DV01 as the rates driver: rates = -DV01 * dy_bp (positive DV01 loses when yields rise).

    Residual = total - carry - roll - rates - spread - convexity - financing - cost. Large residuals mean the risk model is wrong, not that the
    trade made money: investigate before acting on P&L.
    """
    rates = -dv01 * dy_bp
    resid = total - carry - roll - rates - spread - convexity - financing - cost
    return {"carry": carry, "roll": roll, "rates": rates, "spread": spread, "convexity": convexity,
            "financing": financing, "cost": cost, "residual": resid, "total": total}


def neutral_qty(dv01_a: float, dv01_per_unit_b: float) -> float:
    """Quantity of instrument b that offsets leg a's DV01: qty_b = -DV01_a / DV01_per_unit_b."""
    if dv01_per_unit_b == 0:
        raise ValueError("instrument b has zero DV01")
    return -dv01_a / dv01_per_unit_b


def trade_status(level: float, entry: float, direction: int, target: float, stop: float,
                 days_held: float = 0.0, half_life: float = float("nan"), max_hold_halflives: float = 2.0) -> str:
    """Status of an open spread trade against levels and a time stop.

    Long spread (direction +1): target above entry, stop below entry. Short spread: mirror image.
    Returns one of 'target', 'stop', 'time_stop', 'open', 'no_data' (level is NaN). Stop and target are checked before the time stop.
    """
    if direction not in (1, -1):
        raise ValueError("direction must be +1 or -1")
    if not (direction * (target - entry) > 0 and direction * (entry - stop) > 0):
        raise ValueError("levels must satisfy stop < entry < target for a long spread (mirror for a short)")
    if not math.isfinite(level):
        return "no_data"
    if direction == 1:
        hit_target, hit_stop = level >= target, level <= stop
    else:
        hit_target, hit_stop = level <= target, level >= stop
    if hit_target:
        return "target"
    if hit_stop:
        return "stop"
    if math.isfinite(half_life) and days_held >= max_hold_halflives * half_life:
        return "time_stop"
    return "open"


def _selftest() -> None:
    # 1. Noise-free AR(1) with phi = 0.5 is recovered exactly; half-life = 1 period.
    mu, phi, n = 10.0, 0.5, 200
    x = np.empty(n)
    x[0] = 20.0
    for t in range(1, n):
        x[t] = mu + phi * (x[t - 1] - mu)
    fit = ou_fit(x)
    assert abs(fit["phi"] - 0.5) < 1e-9, fit
    assert abs(fit["half_life"] - 1.0) < 1e-9, fit
    assert abs(fit["mu"] - 10.0) < 1e-6, fit
    # 2. phi = exp(-k) with k = 0.05 per day -> half-life = ln2 / k = 13.8629 days.
    k = 0.05
    phi2 = math.exp(-k)
    x2 = np.empty(300)
    x2[0] = 5.0
    for t in range(1, 300):
        x2[t] = 0.0 + phi2 * x2[t - 1]
    fit2 = ou_fit(x2)
    assert abs(fit2["half_life"] - math.log(2) / k) < 1e-6, fit2
    # 3. A random walk (phi = 1) has no half-life.
    rw = np.cumsum(np.ones(100))
    assert math.isnan(ou_fit(rw)["half_life"])
    # 4. Rolling z-score: [1..5], window 5 -> mean 3, sd sqrt(2.5); last z = 2 / sqrt(2.5).
    z = zscore(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]), 5).iloc[-1]
    assert abs(z - 2.0 / math.sqrt(2.5)) < 1e-12, z
    # 5. P&L explain: DV01 +10,000/bp long duration, yields +2bp -> rates -20,000; components sum to total.
    pe = pnl_explain(total=-17000.0, carry=3000.0, roll=0.0, dv01=10000.0, dy_bp=2.0, cost=0.0)
    assert pe["rates"] == -20000.0, pe
    assert abs(pe["residual"]) < 1e-9, pe
    # 4b. P&L explain with every component: residual is what is left.
    pe2 = pnl_explain(total=100.0, carry=10.0, roll=5.0, dv01=-1000.0, dy_bp=-0.05, cost=-2.0, spread=20.0,
                      convexity=3.0, financing=-1.0)
    assert abs(pe2["rates"] - (-50.0)) < 1e-12 and abs(pe2["residual"] - 115.0) < 1e-9, pe2
    # 4c. Seeded noisy AR(1): phi, stationary sd and half-life recovered within sampling error.
    rng = np.random.default_rng(7)
    phi3, sig3, n3 = 0.95, 1.0, 40000
    e = rng.normal(0.0, sig3, n3)
    x3 = np.empty(n3)
    x3[0] = 0.0
    for t in range(1, n3):
        x3[t] = 3.0 + phi3 * x3[t - 1] + e[t]
    f3 = ou_fit(x3)
    assert abs(f3["phi"] - phi3) < 0.01, f3
    assert abs(f3["stationary_sd"] - sig3 / math.sqrt(1 - phi3 ** 2)) < 0.15, f3
    assert abs(f3["mu"] - 3.0 / (1 - phi3)) < 1.0, f3
    assert abs(f3["half_life"] - (-math.log(2) / math.log(phi3))) < 2.0, f3
    # 4d. NaN inside the history must not create fake transitions: still recovers phi from the remaining pairs.
    x4 = x3[:3000].copy()
    x4[1000] = np.nan
    assert abs(ou_fit(x4)["phi"] - phi3) < 0.04
    # 5b. Tuckman-Serrat worked attribution (realised-forward scenario, financing ignored) sums to the total.
    assert abs((-3.76099 + 0.18292 + 0.09843 + 3.81250) - 0.33286) < 1e-9
    # 6. Hedge: leg A DV01 +50,000 needs -6,250 units of B at 8 DV01 per unit.
    assert neutral_qty(50000.0, 8.0) == -6250.0
    # 7. Status: long spread entry -10, target 0, stop -20.
    assert trade_status(-3.0, -10.0, 1, 0.0, -20.0) == "open"
    assert trade_status(0.5, -10.0, 1, 0.0, -20.0) == "target"
    assert trade_status(-21.0, -10.0, 1, 0.0, -20.0) == "stop"
    # 7b. Short spread entry 10, target 0, stop 20.
    assert trade_status(15.0, 10.0, -1, 0.0, 20.0) == "open"
    assert trade_status(-0.1, 10.0, -1, 0.0, 20.0) == "target"
    assert trade_status(21.0, 10.0, -1, 0.0, 20.0) == "stop"
    # 7c. Time stop at 2 half-lives when levels are untouched.
    assert trade_status(-5.0, -10.0, 1, 0.0, -20.0, days_held=20, half_life=10) == "time_stop"
    assert trade_status(float("nan"), -10.0, 1, 0.0, -20.0) == "no_data"
    try:  # stop on the wrong side of entry must be rejected
        trade_status(-5.0, -10.0, 1, 0.0, -5.0)
        raise SystemExit("selftest failed: bad levels accepted")
    except ValueError:
        pass
    print("selftest passed")


def _cli(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--spread", help="CSV with columns date, spread_bp")
    ap.add_argument("--entry-date", help="YYYY-MM-DD")
    ap.add_argument("--entry", type=float, help="entry level, bp")
    ap.add_argument("--direction", type=int, choices=[1, -1])
    ap.add_argument("--target", type=float, help="target level, bp")
    ap.add_argument("--stop", type=float, help="stop level, bp")
    ap.add_argument("--window", type=int, default=252, help="z-score and OU lookback, observations")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return 0
    missing = [k for k in ("spread", "entry_date", "entry", "direction", "target", "stop") if getattr(a, k) is None]
    if missing:
        ap.error("missing: " + ", ".join("--" + m.replace("_", "-") for m in missing))
    df = pd.read_csv(a.spread, parse_dates=["date"]).sort_values("date").set_index("date")
    s = df["spread_bp"].astype(float)
    entry_ts = pd.Timestamp(a.entry_date)
    if entry_ts not in s.index:
        ap.error(f"entry date {a.entry_date} not in spread file")
    look = s.iloc[-a.window:]
    try:
        fit = ou_fit(look.values)
    except ValueError as exc:
        ap.error(str(exc))
    z = zscore(s, min(a.window, len(s))).iloc[-1]
    level = float(s.iloc[-1])
    days_held = float(len(s.loc[entry_ts:]) - 1)
    status = trade_status(level, a.entry, a.direction, a.target, a.stop, days_held, fit["half_life"])
    out = {"as_of": str(s.index[-1].date()), "level_bp": level, "status": status,
           "pnl_bp": a.direction * (level - a.entry), "days_held": days_held, "z": float(z),
           "half_life_days": fit["half_life"], "phi": fit["phi"], "stationary_sd_bp": fit["stationary_sd"],
           "n_obs": fit["n_obs"], "half_life_reliable": fit["n_obs"] >= 100,
           # adverse-side 2 stationary sd stop: below the mean for a long spread, above it for a short spread
           "reversion_stop_bp": fit["mu"] - a.direction * 2 * fit["stationary_sd"]}
    print(json.dumps(out, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
