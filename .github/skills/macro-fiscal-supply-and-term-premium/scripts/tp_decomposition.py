"""Forward-rate and term-premium arithmetic for macro-fiscal-supply-and-term-premium.

Library functions take numpy arrays or pandas Series. The CLI reads canonical
`curve_zero` rows (columns: date, curve_id, node_date, zero_rate_pct) and prints
one-period forwards, with tau = ACT/365F years from `date` to `node_date`.

Conventions
- rates in percent unless the name says `_dec`; durations in years; spreads in bp.
- forward between nodes a < b: annual compounding  (1+z_b)^tau_b / (1+z_a)^tau_a, power 1/(tau_b-tau_a)
  continuous compounding (the curve_zero default): (z_b*tau_b - z_a*tau_a) / (tau_b - tau_a)
- expected excess return (decimal) = lam * duration, lam = price of risk per unit of duration (decimal per year)
- term funding premium (bp/yr) = minus the OLS slope of matched-maturity swap spreads (bp) on modified duration

Run: python -I scripts/tp_decomposition.py --selftest
"""
import argparse
import sys

import numpy as np


def forward_rates(tau, zero_pct, compounding="annual"):
    """One-period forwards between consecutive nodes, in percent.

    tau: increasing year fractions (> 0). zero_pct: zero rates at those nodes (percent).
    The first forward runs from t=0 to tau[0].
    """
    tau = np.asarray(tau, dtype=float)
    z = np.asarray(zero_pct, dtype=float) / 100.0
    if tau.shape != z.shape or tau.size == 0 or not (np.isfinite(tau).all() and np.isfinite(z).all()):
        raise ValueError("tau and zero_pct must be equal-length, non-empty and finite (drop NaN nodes first)")
    if tau[0] <= 0 or np.any(np.diff(tau) <= 0):
        raise ValueError("tau must be positive and strictly increasing")
    t = np.concatenate([[0.0], tau])
    zz = np.concatenate([[0.0], z])
    if compounding == "annual":
        growth = (1.0 + zz[1:]) ** t[1:] / (1.0 + zz[:-1]) ** t[:-1]
        fwd = growth ** (1.0 / np.diff(t)) - 1.0
    elif compounding == "cont":
        fwd = (zz[1:] * t[1:] - zz[:-1] * t[:-1]) / np.diff(t)
    else:
        raise ValueError("compounding must be 'annual' or 'cont'")
    return 100.0 * fwd


def sharpe_from_lambda(lam_dec, sigma_dec):
    """Sharpe ratio = lam / sigma (both decimal per year). lam 10bp, sigma 100bp -> 0.10."""
    return lam_dec / sigma_dec


def expected_excess_return(lam_dec, duration_years):
    """E[dP/P] - r0 = lam * D (decimal). Premium is proportional to factor duration."""
    return lam_dec * duration_years


def risk_premium_from_sharpe(sharpe, sigma_dec, duration_years, loading=1.0):
    """Long-factor premium = Sharpe * sigma * duration * loading (decimal)."""
    return sharpe * sigma_dec * duration_years * loading


def convexity_bias(convexity, sigma_dec):
    """Forward convexity bias = 0.5 * C * sigma^2 (decimal). Subtract from the forward."""
    return 0.5 * convexity * sigma_dec ** 2


def term_funding_premium(mod_dur_years, spread_bp):
    """TFP (bp/yr) = minus the OLS slope of maturity-matched swap spreads (bp) on modified duration."""
    x = np.asarray(mod_dur_years, dtype=float)
    y = np.asarray(spread_bp, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 3 or np.ptp(x) == 0:
        return float("nan")  # too few matched maturities for a daily cross-sectional slope
    slope = np.polyfit(x, y, 1)[0]
    return -slope


def _selftest():
    # 1) flat 3% continuous curve: every forward is 3%
    tau = np.arange(1, 11, dtype=float)
    f = forward_rates(tau, np.full(10, 3.0), compounding="cont")
    assert np.allclose(f, 3.0, atol=1e-9), f
    # 1b) continuous compounding, known forwards 2,3,4: zeros are running averages 2, 2.5, 3
    backc = forward_rates(np.array([1.0, 2.0, 3.0]), np.array([2.0, 2.5, 3.0]), compounding="cont")
    assert np.allclose(backc, [2.0, 3.0, 4.0], atol=1e-9), backc
    # 1c) non-integer, unequal spacing (0.5y, 2y): annual forward from 0.5y to 2y
    z = np.array([2.0, 3.0])
    g = forward_rates(np.array([0.5, 2.0]), z, compounding="annual")
    exp = ((1.03 ** 2.0) / (1.02 ** 0.5)) ** (1 / 1.5) - 1
    assert abs(g[1] - 100 * exp) < 1e-9, g

    # 2) annual compounding: build zeros from known forwards 2%, 3%, 4%, then recover them
    known = [2.0, 3.0, 4.0]
    zs, prod = [], 1.0
    for n, fw in enumerate(known, start=1):
        prod *= 1 + fw / 100.0
        zs.append(100.0 * (prod ** (1.0 / n) - 1.0))
    back = forward_rates(np.array([1.0, 2.0, 3.0]), np.array(zs), compounding="annual")
    assert np.allclose(back, known, atol=1e-9), back

    # 3) Tuckman & Serrat style: r0 = 1%, D = 5, lam = 10bp per year of duration -> E[return] = 1.5%
    er = 0.01 + expected_excess_return(0.0010, 5.0)
    assert abs(er - 0.015) < 1e-12, er
    # 4) Sharpe = lam/sigma = 10bp / 100bp = 10%
    assert abs(sharpe_from_lambda(0.0010, 0.01) - 0.10) < 1e-12
    # 5) Gauss+ 10y long-factor premium: 0.09 * 1% * 10 * 0.7 = 63bp
    prem = risk_premium_from_sharpe(0.09, 0.01, 10.0, 0.7)
    assert abs(prem - 0.0063) < 1e-12, prem
    # 6) convexity bias 0.5 * 100 * (1%)^2 = 50bp
    assert abs(convexity_bias(100.0, 0.01) - 0.005) < 1e-12

    # 7) TFP: spreads fall 0.5bp per year of duration -> TFP = +0.5 bp/yr (sign: minus the slope)
    dur = np.array([2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
    tfp = term_funding_premium(dur, 10.0 - 0.5 * dur)
    assert abs(tfp - 0.5) < 1e-9, tfp
    # 8) NaN rows are dropped, too-short history returns NaN, bad tau raises
    assert abs(term_funding_premium(np.r_[dur, np.nan], np.r_[10.0 - 0.5 * dur, 1.0]) - 0.5) < 1e-9
    assert np.isnan(term_funding_premium([2.0, 5.0], [1.0, 2.0]))
    try:
        forward_rates([2.0, 1.0], [3.0, 3.0])
        raise SystemExit("unsorted tau not rejected")
    except ValueError:
        pass
    print("tp_decomposition selftest OK")


def _cli(argv):
    import pandas as pd

    ap = argparse.ArgumentParser(description="One-period forwards from a curve_zero CSV.")
    ap.add_argument("csv", help="canonical curve_zero CSV")
    ap.add_argument("--curve_id", required=True)
    ap.add_argument("--date", default=None, help="as-of date YYYY-MM-DD (default: latest)")
    ap.add_argument("--compounding", default="cont", choices=["cont", "annual"])
    a = ap.parse_args(argv)
    df = pd.read_csv(a.csv, parse_dates=["date", "node_date"])
    df = df[df["curve_id"] == a.curve_id]
    if df.empty:
        sys.exit("no rows for curve_id")
    d = pd.Timestamp(a.date) if a.date else df["date"].max()
    df = df[df["date"] == d].sort_values("node_date")
    if "snap" in df.columns and df["snap"].nunique() > 1:
        sys.exit("several snaps on this date; filter the CSV to one snap first")
    df = df.dropna(subset=["zero_rate_pct"]).drop_duplicates("node_date")
    df = df[df["node_date"] > df["date"]]  # DF(date) = 1 node has tau = 0
    tau = (df["node_date"] - df["date"]).dt.days.to_numpy() / 365.0
    fwd = forward_rates(tau, df["zero_rate_pct"].to_numpy(), a.compounding)
    out = pd.DataFrame({"node_date": df["node_date"].dt.date, "tau_years": tau.round(4),
                        "zero_pct": df["zero_rate_pct"].to_numpy(), "fwd_pct": fwd.round(4)})
    print(out.to_string(index=False))


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    if len(sys.argv) > 1:
        _cli(sys.argv[1:])
    else:
        print(__doc__)
