#!/usr/bin/env python3
"""Regime and scenario primitives for G10 rates relative value.

Conventions: yields in percent (pct), curve changes in basis points (bp), returns in percent,
probabilities in 0..1, durations in years. Functions take pandas Series/DataFrames or numpy arrays.

CLI (curve regime shares from a wide canonical extract with columns date,y2_pct,y10_pct):
    python scripts/regime_tools.py --curve curve_2s10s.csv [--window 21] [--min-move-bp 2]
Self-test (known-answer checks, exits non-zero on failure):
    python -I scripts/regime_tools.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

DIRECTIONAL = ("bull_steepening", "bear_flattening", "bull_flattening", "bear_steepening")


def curve_move_regime(d_front_bp, d_back_bp, min_move_bp: float = 2.0) -> pd.Series:
    """Label each curve move from its level and slope change.

    level = (d_front + d_back) / 2 ; slope = d_back - d_front   (bp)
    bull = level < 0, bear = level > 0 ; steepening = slope > 0, flattening = slope < 0.
    NaN inputs are 'missing'; moves with max(|d_front|, |d_back|) < min_move_bp are 'below_threshold'; exact ties are 'tie'.
    (Willer-Saunders apply the floor to the 2y move only; this max-of-legs rule is a house variant.)
    """
    f = pd.Series(d_front_bp, dtype=float)
    b = pd.Series(d_back_bp, dtype=float, index=f.index)
    level = (f + b) / 2.0
    slope = b - f
    small = np.maximum(f.abs(), b.abs()) < min_move_bp
    missing = f.isna() | b.isna()
    labels = np.select(
        [missing, small,
         (level < 0) & (slope > 0),
         (level > 0) & (slope < 0),
         (level < 0) & (slope < 0),
         (level > 0) & (slope > 0)],
        ["missing", "below_threshold", "bull_steepening", "bear_flattening", "bull_flattening", "bear_steepening"],
        default="tie",
    )
    return pd.Series(labels, index=f.index)


def move_shares(labels: pd.Series, window: int = 21) -> pd.DataFrame:
    """Rolling share of each directional regime over `window` observations.

    Denominator = directional moves only (missing, below_threshold and tie excluded), so the four columns sum to 1.
    """
    ind = pd.DataFrame({c: (labels == c).astype(float) for c in DIRECTIONAL}, index=labels.index)
    num = ind.rolling(window, min_periods=window).sum()
    den = ind.sum(axis=1).rolling(window, min_periods=window).sum()
    return num.div(den, axis=0)


def conviction_from_shares(shares) -> float:
    """Conviction in [0, 1] from regime shares: 1 - H / ln(n), H = Shannon entropy of the shares.

    Equal shares give 0 (no conviction); one type at 100% gives 1. The source gives no formula, so this
    normalisation is a house default; it only fixes the endpoints.
    """
    p = np.asarray(shares, dtype=float)
    if not np.isfinite(p).all() or p.sum() <= 0:
        return float("nan")  # no directional moves in the window: undefined, not "full conviction"
    p = p / p.sum()
    nz = p[p > 0]
    h = float(-(nz * np.log(nz)).sum())
    return 1.0 - h / np.log(len(p))


def above_ma_flags(x, window: int = 55, lag: int = 1) -> pd.Series:
    """1.0 where x is above its trailing `window` moving average, shifted `lag` observations.

    lag=1 means the signal on day t uses data through t-1 (no look-ahead). NaN during warm-up.
    """
    x = pd.Series(x, dtype=float)
    ma = x.rolling(window, min_periods=window).mean()
    flag = (x > ma).astype(float).where(ma.notna())
    return flag.shift(lag)


def rolling_z(x, window: int = 252) -> pd.Series:
    """Trailing z-score (sample std, ddof=1) over `window` observations, current value included."""
    x = pd.Series(x, dtype=float)
    m = x.rolling(window, min_periods=window).mean()
    s = x.rolling(window, min_periods=window).std(ddof=1)
    return (x - m) / s


def max_z_switch(vols: pd.DataFrame, window: int = 252, cut: float = 2.0, reenter: float = 2.0) -> pd.Series:
    """Risk on (1) / off (0) switch from the maximum trailing z-score across input columns.

    Cut when max z > cut; re-enter when max z <= reenter. Returned position for day t is the state set
    at the close of t-1 (shift 1). Columns are implied vols or stress gauges; skipna=False keeps the
    warm-up period undefined instead of silently using a subset of columns.
    """
    zmax = pd.concat([rolling_z(vols[c], window) for c in vols.columns], axis=1).max(axis=1, skipna=False)
    state, out = 1.0, []
    for v in zmax.to_numpy():
        if np.isnan(v):
            out.append(np.nan)
            continue
        if state == 1.0 and v > cut:
            state = 0.0
        elif state == 0.0 and v <= reenter:
            state = 1.0
        out.append(state)
    return pd.Series(out, index=vols.index).shift(1)


def scenario_summary(probs, returns_pct, dy_bp, duration_yrs: float, zero_vol_pct: float = 0.0) -> dict:
    """Probability-weighted scenario return and the view decomposition (two-step scenario analysis).

    returns_pct: scenario returns with the view (%), dy_bp: scenario yield changes (bp).
    duration impact = with-view E[R] - viewless E[R] = -D * mean(dy) / 100   (%)
    D is the duration at the END of the horizon (e.g. 2y for a 3y-duration portfolio held 1y).
    viewless return_i = R_i + D * mean(dy) / 100   (same shocks with the mean yield change removed)
    convexity value = viewless E[R] - zero-volatility return
    """
    p = np.asarray(probs, dtype=float)
    if not np.isclose(p.sum(), 1.0):
        raise ValueError(f"scenario probabilities sum to {p.sum():.6f}, not 1")
    R = np.asarray(returns_pct, dtype=float)
    dy = np.asarray(dy_bp, dtype=float)
    ybar = float(p @ dy)
    e_ret = float(p @ R)
    dur_impact = -duration_yrs * ybar / 100.0
    viewless = e_ret - dur_impact
    return {
        "expected_return_pct": e_ret,
        "mean_yield_change_bp": ybar,
        "duration_impact_pct": dur_impact,
        "viewless_expected_pct": viewless,
        "convexity_value_pct": viewless - zero_vol_pct,
    }


def collapse_probs(probs, remaining) -> np.ndarray:
    """Bayesian collapse: after a fact rules scenarios out, renormalise the survivors' probabilities."""
    p = np.asarray(probs, dtype=float)
    m = np.asarray(remaining, dtype=bool)
    kept = np.where(m, p, 0.0)
    total = kept.sum()
    if total <= 0:
        raise ValueError("no scenario survives the new information")
    return kept / total


def stationary(P) -> np.ndarray:
    """Stationary distribution pi of a row-stochastic matrix (pi P = pi, sum pi = 1)."""
    P = np.asarray(P, dtype=float)
    n = P.shape[0]
    A = np.vstack([P.T - np.eye(n), np.ones((1, n))])
    b = np.zeros(n + 1)
    b[-1] = 1.0
    return np.linalg.lstsq(A, b, rcond=None)[0]


def expected_duration(P) -> np.ndarray:
    """Expected regime duration in periods: 1 / (1 - p_jj)."""
    return 1.0 / (1.0 - np.diag(np.asarray(P, dtype=float)))


def hamilton_filter(eta, P, xi0=None):
    """Hamilton (1989/1994) filter for a Markov-switching model, given regime densities.

    eta: (T, N) array, eta[t, j] = p(y_t | s_t = j, past). P: (N, N) row-stochastic, P[i, j] = Pr(s_{t+1}=j | s_t=i).
    Returns (filtered, loglik): filtered[t, j] = Pr(s_t = j | y_1..t) and the log-likelihood.
    Filtered probabilities use only past data; Kim-smoothed probabilities use the full sample (look-ahead).
    """
    eta = np.asarray(eta, dtype=float)
    P = np.asarray(P, dtype=float)
    xi = stationary(P) if xi0 is None else np.asarray(xi0, dtype=float)
    T, N = eta.shape
    filtered = np.empty((T, N))
    loglik = 0.0
    for t in range(T):
        joint = xi * eta[t]
        m = joint.sum()
        loglik += float(np.log(m))
        filtered[t] = joint / m
        xi = filtered[t] @ P
    return filtered, loglik


def ar1_regime_densities(y, c, phi, sigma) -> np.ndarray:
    """Gaussian densities for y_t | y_{t-1}, s_t = j ~ N(c_j + phi_j y_{t-1}, sigma_j^2), t = 1..T-1."""
    y = np.asarray(y, dtype=float)
    c, phi, sigma = (np.asarray(v, dtype=float) for v in (c, phi, sigma))
    mean = c[None, :] + phi[None, :] * y[:-1, None]
    z = (y[1:, None] - mean) / sigma[None, :]
    return np.exp(-0.5 * z ** 2) / (np.sqrt(2 * np.pi) * sigma[None, :])


def _selftest() -> None:
    # 1. Curve-move labels from hand-computed level and slope.
    lab = curve_move_regime([-5, 4, 5, -5, 1, np.nan], [3, 6, 1, -7, 1, 2])
    assert list(lab) == ["bull_steepening", "bear_steepening", "bear_flattening", "bull_flattening",
                         "below_threshold", "missing"], list(lab)

    # 2. Rolling shares: window of 5 with one non-directional row; 2 bull-steep + 2 bear-flat of 4 directional -> 0.5 each
    #    (a mutant dividing by the window, 5, would give 0.4).
    s = pd.Series(["bull_steepening", "bear_flattening", "below_threshold", "bull_steepening", "bear_flattening"])
    sh = move_shares(s, window=5)
    assert abs(sh.iloc[-1]["bull_steepening"] - 0.5) < 1e-12 and abs(sh.iloc[-1]["bear_flattening"] - 0.5) < 1e-12

    # 3. Conviction endpoints and midpoint: equal shares -> 0; one type 100% -> 1; half-half -> 1 - ln2/ln4 = 0.5.
    assert abs(conviction_from_shares([0.25] * 4)) < 1e-12
    assert abs(conviction_from_shares([1, 0, 0, 0]) - 1.0) < 1e-12
    assert abs(conviction_from_shares([0.5, 0.5, 0, 0]) - 0.5) < 1e-12
    assert np.isnan(conviction_from_shares([np.nan] * 4)) and np.isnan(conviction_from_shares([0, 0, 0, 0]))

    # 4. 55dma flag with a 1-day lag: a step at index 60 is first visible at index 61.
    x = np.zeros(62)
    x[60] = 100.0
    f = above_ma_flags(x, window=55, lag=1)
    assert f.iloc[60] == 0.0 and f.iloc[61] == 1.0, (f.iloc[60], f.iloc[61])

    # 5. Trailing z on [1..5], window 5: mean 3, sample sd sqrt(2.5), z = 2 / sqrt(2.5).
    z = rolling_z([1, 2, 3, 4, 5], window=5)
    assert abs(z.iloc[-1] - 2.0 / np.sqrt(2.5)) < 1e-12

    # 6. Max-z switch: alternating 1/2 then a spike at index 30 cuts risk; the position flips one day later.
    v = np.where(np.arange(40) % 2 == 0, 1.0, 2.0)
    v[30] = 10.0
    pos = max_z_switch(pd.DataFrame({"a": v}), window=20, cut=2.0, reenter=2.0)
    assert pos.iloc[29] == 1.0 and pos.iloc[31] == 0.0, (pos.iloc[29], pos.iloc[31])
    assert pos.iloc[32] == 1.0, pos.iloc[32]  # re-entry: z falls back below 2 the day after, position follows a day later

    # 7. Scenario decomposition with a hand answer: p=(.5,.5), dy=(20,0) bp, D=5, R=(-1,0)%.
    #    mean dy = 10bp, E[R] = -0.5%, duration impact = -5*10/100 = -0.5%, viewless E[R] = 0%.
    out = scenario_summary([0.5, 0.5], [-1.0, 0.0], [20, 0], duration_yrs=5.0)
    assert abs(out["expected_return_pct"] + 0.5) < 1e-12
    assert abs(out["duration_impact_pct"] + 0.5) < 1e-12
    assert abs(out["viewless_expected_pct"]) < 1e-12

    # 7b. Salomon Part 6 Fig 7: five zeros, scenarios bear/bull/neutral/bear-flat/bull-steep with equal weights;
    #     printed E[R] 6.82%, duration impact -0.20% (horizon-end duration 2y, mean dy +10bp), viewless 7.02%, convexity 0.02%.
    sal = scenario_summary([0.2] * 5, [5.02, 9.06, 7.00, 5.51, 7.51], [100, -100, 0, 75, -25],
                           duration_yrs=2.0, zero_vol_pct=7.00)
    assert abs(sal["expected_return_pct"] - 6.82) < 1e-9 and abs(sal["mean_yield_change_bp"] - 10.0) < 1e-9
    assert abs(sal["duration_impact_pct"] + 0.20) < 1e-9 and abs(sal["viewless_expected_pct"] - 7.02) < 1e-9
    assert abs(sal["convexity_value_pct"] - 0.02) < 1e-9, sal

    # 8. Bayesian collapse: ruling out the first scenario renormalises the rest.
    c = collapse_probs([0.2, 0.4, 0.4], [False, True, True])
    assert np.allclose(c, [0.0, 0.5, 0.5])

    # 9. Stationary distribution of [[0.9,0.1],[0.2,0.8]] is (2/3, 1/3); expected durations of
    #    diag (0.9, 0.75) are 10 and 4 periods (the Hamilton GNP example's durations).
    pi = stationary([[0.9, 0.1], [0.2, 0.8]])
    assert np.allclose(pi, [2 / 3, 1 / 3], atol=1e-10), pi
    assert np.allclose(expected_duration([[0.9, 0.1], [0.25, 0.75]]), [10.0, 4.0])

    # 10. Hamilton filter with an absorbing regime (P = I) and constant densities 0.8 / 0.2:
    #     posterior of regime 1 after n observations = 0.8^n / (0.8^n + 0.2^n); n=2 -> 0.64/0.68.
    filt, ll = hamilton_filter(np.tile([0.8, 0.2], (2, 1)), np.eye(2), xi0=[0.5, 0.5])
    assert abs(filt[0, 0] - 0.8) < 1e-12 and abs(filt[1, 0] - 0.64 / 0.68) < 1e-12
    #     Likelihood: step 1 mass 0.5 (0.5*0.8 + 0.5*0.2), step 2 mass 0.68 (0.8*0.8 + 0.2*0.2).
    assert abs(ll - (np.log(0.5) + np.log(0.68))) < 1e-12, ll
    #     Row-stochastic transition: start surely in regime 0, flat densities -> next prior is row 0 of P = (0.9, 0.1),
    #     so the second filtered row is (0.9, 0.1) (a column-convention bug would give (0.9, 0.2)/1.1).
    filt, _ = hamilton_filter(np.ones((2, 2)), [[0.9, 0.1], [0.2, 0.8]], xi0=[1.0, 0.0])
    assert np.allclose(filt[1], [0.9, 0.1]), filt

    # 11. AR(1) regime density: at its mean it equals the normal pdf at 0 divided by sigma; with sigma=2, c=1, phi=0.5,
    #     y_{t-1}=2, y_t=3 the residual is 1 and the density is exp(-0.5*(1/2)^2) / (2*sqrt(2*pi)).
    d = ar1_regime_densities([0.0, 0.0], c=[0.0, 1.0], phi=[0.0, 0.0], sigma=[1.0, 1.0])
    assert abs(d[0, 0] - 1 / np.sqrt(2 * np.pi)) < 1e-12
    d = ar1_regime_densities([2.0, 3.0], c=[1.0], phi=[0.5], sigma=[2.0])
    assert abs(d[0, 0] - np.exp(-0.5 * 0.25) / (2 * np.sqrt(2 * np.pi))) < 1e-12, d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="run known-answer checks and exit")
    ap.add_argument("--curve", help="CSV with date,y2_pct,y10_pct (daily, same snap)")
    ap.add_argument("--window", type=int, default=21, help="rolling window for move shares (obs)")
    ap.add_argument("--min-move-bp", type=float, default=2.0, help="ignore moves below this size")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        print("selftest OK")
        return 0
    if not a.curve:
        ap.error("give --curve or --selftest")
    df = pd.read_csv(a.curve, parse_dates=["date"]).sort_values("date").set_index("date")
    d2 = df["y2_pct"].diff() * 100.0
    d10 = df["y10_pct"].diff() * 100.0
    labels = curve_move_regime(d2, d10, a.min_move_bp).iloc[1:]
    counts = labels.value_counts()
    print("label counts:")
    print(counts.to_string())
    sh = move_shares(labels.reset_index(drop=True), a.window).iloc[-1]
    nd = int(labels.iloc[-a.window:].isin(DIRECTIONAL).sum())
    print(f"latest {a.window}-obs shares (from {nd} directional moves; treat < 10 as noise):")
    print(sh.to_string())
    print(f"conviction (house default): {conviction_from_shares(sh.to_numpy()):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
