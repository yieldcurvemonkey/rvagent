#!/usr/bin/env python3
"""Backtest validation toolkit: splits, Sharpe inference, trial deflation, PBO, multiple testing, nulls.

Self-contained (numpy, pandas, scipy). All Sharpe ratios are PER-PERIOD unless a function says 'annual'.
Kurtosis is NON-excess (Gaussian = 3). Time-label arrays t0/t1 are integer bar positions (use
index.searchsorted(date) to convert), so embargo is counted in bars.

Library use:   from validation import dsr, pbo_cscv, purged_kfold, cpcv_splits, ...
CLI:           python validation.py report --pnl pnl.csv [--strategy ID] [--n-trials N] [--blocks 16]
               python validation.py --selftest
`report` reads the canonical `pnl` table (csv or parquet), uses package_id == 'ALL' rows when present, pivots
date x strategy_id on total_ccy; every strategy column is one trial. Missing days count as flat (0).
"""
from __future__ import annotations

import argparse
import itertools
import math
import sys

import numpy as np
import pandas as pd
from scipy import stats

EULER_GAMMA = 0.5772156649015329


# ----------------------------------------------------------------------------- Sharpe inference
def sharpe(r) -> float:
    """Per-period Sharpe = mean / std (ddof=1). No risk-free term (self-financing RV packages)."""
    r = np.asarray(r, float)
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 0 else float("nan")


def annualise(sr: float, periods_per_year: float = 252.0) -> float:
    """Annual SR = per-period SR * sqrt(periods per year). Assumes serially uncorrelated returns."""
    return sr * math.sqrt(periods_per_year)


def psr(sr_hat: float, n_obs: int, skew: float = 0.0, kurt: float = 3.0, sr_star: float = 0.0) -> float:
    """Probabilistic Sharpe ratio P[true SR > sr_star]. sr_hat, sr_star per-period; kurt non-excess."""
    var = 1.0 - skew * sr_hat + (kurt - 1.0) / 4.0 * sr_hat ** 2
    if var <= 0 or n_obs < 2:
        return float("nan")
    return float(stats.norm.cdf((sr_hat - sr_star) * math.sqrt(n_obs - 1) / math.sqrt(var)))


def psr_from_returns(r, sr_star: float = 0.0) -> float:
    r = np.asarray(r, float)
    return psr(sharpe(r), len(r), float(stats.skew(r)), float(stats.kurtosis(r, fisher=False)), sr_star)


def expected_max_normal(n: int) -> float:
    """E[max of n iid N(0,1)] ~ (1-g) Z^-1(1-1/n) + g Z^-1(1-1/(n e)); <= sqrt(2 ln n)."""
    if n <= 1:
        return 0.0
    return float((1 - EULER_GAMMA) * stats.norm.ppf(1 - 1.0 / n)
                 + EULER_GAMMA * stats.norm.ppf(1 - 1.0 / (n * math.e)))


def expected_max_sharpe(n_trials: int, var_trial_sr: float) -> float:
    """SR* = sqrt(V[SR_n]) * E[max of N std normals]: the best per-period SR expected under zero skill."""
    return math.sqrt(max(var_trial_sr, 0.0)) * expected_max_normal(n_trials)


def dsr(r, trial_sharpes, n_trials: int | None = None) -> float:
    """Deflated Sharpe ratio of the chosen strategy r (per-period returns) against the trial family.
    trial_sharpes: per-period Sharpes of EVERY trial run (controls and categorical choices included).
    n_trials: defaults to len(trial_sharpes); pass the trial-log row count (or an effective N) to override."""
    ts = np.asarray(trial_sharpes, float)
    ts = ts[np.isfinite(ts)]                       # flat / constant trials have no Sharpe
    n = int(n_trials) if n_trials is not None else len(ts)
    sr_star = expected_max_sharpe(n, float(np.var(ts, ddof=1)) if len(ts) > 1 else 0.0)
    return psr_from_returns(r, sr_star)


def effective_trials(returns: pd.DataFrame) -> float:
    """Heuristic effective N = 1 + (N-1)(1 - mean pairwise correlation): rho=1 -> 1, rho=0 -> N."""
    n = returns.shape[1]
    if n < 2:
        return float(n)
    with np.errstate(invalid="ignore", divide="ignore"):
        c = np.nan_to_num(np.corrcoef(returns.values, rowvar=False))   # constant column -> NaN -> uncorrelated
    rho = (c.sum() - n) / (n * (n - 1))
    return float(1 + (n - 1) * (1 - max(min(rho, 1.0), 0.0)))


def min_backtest_years(n_trials: int, sr_target_annual: float) -> float:
    """Years T so that the best of n_trials zero-skill backtests is not expected to reach sr_target_annual:
    SE(annual SR) ~ 1/sqrt(T) so E[max] ~ E[max_N]/sqrt(T) -> T = (E[max_N] / SR_target)^2."""
    return (expected_max_normal(n_trials) / sr_target_annual) ** 2


def newey_west_t(x, lags: int | None = None) -> float:
    """t-stat of the mean with Bartlett-kernel HAC variance. Default lags = floor(T^(1/4)); for daily P&L of
    multi-week holds pass lags = median holding period in days."""
    x = np.asarray(x, float)
    n = len(x)
    if lags is None:
        lags = int(n ** 0.25)
    e = x - x.mean()
    lrv = float(e @ e) / n
    for k in range(1, lags + 1):
        lrv += 2 * (1 - k / (lags + 1)) * float(e[k:] @ e[:-k]) / n
    return float(x.mean() / math.sqrt(lrv / n))


def top_k_share(trade_pnl, k: int = 3) -> float:
    """Share of total P&L contributed by the k best trades (concentration). nan if total <= 0."""
    p = np.sort(np.asarray(trade_pnl, float))[::-1]
    tot = p.sum()
    return float(p[:k].sum() / tot) if tot > 0 else float("nan")


# ----------------------------------------------------------------------------- strategy-failure probability
def bet_sharpe(p: float, n_bets: int, pi_plus: float, pi_minus: float) -> float:
    """Annual-style Sharpe of n_bets per year with precision p and payoffs pi_plus > 0 > pi_minus (return per bet):
    SR = ((pi_plus - pi_minus) p + pi_minus) / ((pi_plus - pi_minus) sqrt(p(1-p))) * sqrt(n_bets)."""
    d = pi_plus - pi_minus
    return float((d * p + pi_minus) / (d * math.sqrt(p * (1 - p))) * math.sqrt(n_bets))


def breakeven_precision(sr_target: float, n_bets: int, pi_plus: float, pi_minus: float) -> float:
    """Smallest precision p giving Sharpe >= sr_target (bisection; Sharpe is increasing in p above breakeven)."""
    lo = -pi_minus / (pi_plus - pi_minus)          # SR = 0 here
    if sr_target <= 0:
        return lo
    hi = 1 - 1e-9
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if bet_sharpe(mid, n_bets, pi_plus, pi_minus) < sr_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def failure_probability(wins: int, losses: int, p_breakeven: float) -> float:
    """P[true precision < p_breakeven] under a Beta(wins+1, losses+1) posterior (uniform prior; a simple
    illustrative choice, not the only valid one). Reject if > 0.05."""
    return float(stats.beta.cdf(p_breakeven, wins + 1, losses + 1))


# ----------------------------------------------------------------------------- walk-forward
def walk_forward_splits(n: int, train: int, test: int, step: int | None = None,
                        expanding: bool = True, gap: int = 0):
    """Yield (train_idx, test_idx). First train block has `train` bars; `gap` bars (>= label horizon) are
    skipped between train end and test start; the window advances by `step` (default = test)."""
    step = step or test
    t_end = train                                  # exclusive end of train block
    while t_end + gap + test <= n:
        start = 0 if expanding else t_end - train
        yield np.arange(start, t_end), np.arange(t_end + gap, t_end + gap + test)
        t_end += step


# ----------------------------------------------------------------------------- purged / embargoed CV
def _overlaps(t0, t1, lo, hi):
    """Label [t0, t1] overlaps test span [lo, hi]: covers all three cases (starts inside, ends inside, envelops)."""
    return (t0 <= hi) & (t1 >= lo)


def _train_mask(t0, t1, test_groups, embargo: int):
    """Boolean mask of usable training obs given contiguous test groups (arrays of obs indices).
    Purge: drop labels overlapping a test group's span. Embargo: drop obs starting within `embargo` bars after it."""
    keep = np.ones(len(t0), bool)
    for g in test_groups:
        lo, hi = t0[g].min(), t1[g].max()
        keep &= ~_overlaps(t0, t1, lo, hi + embargo)
        keep[g] = False
    return keep


def purged_kfold(t0, t1, n_splits: int = 5, embargo: int = 0):
    """Contiguous (unshuffled) k-fold with purging and embargo. Yields (train_idx, test_idx)."""
    t0, t1 = np.asarray(t0), np.asarray(t1)
    for g in np.array_split(np.arange(len(t0)), n_splits):
        yield np.flatnonzero(_train_mask(t0, t1, [g], embargo)), g


def cpcv_n_splits(n_groups: int, k: int) -> int:
    return math.comb(n_groups, k)


def cpcv_n_paths(n_groups: int, k: int) -> int:
    """phi[N,k] = k/N * C(N,k) backtest paths."""
    return k * math.comb(n_groups, k) // n_groups


def cpcv_splits(t0, t1, n_groups: int = 6, k: int = 2, embargo: int = 0):
    """Combinatorial purged CV. Yields (split_id, test_group_ids, train_idx, test_idx)."""
    t0, t1 = np.asarray(t0), np.asarray(t1)
    groups = np.array_split(np.arange(len(t0)), n_groups)
    for sid, combo in enumerate(itertools.combinations(range(n_groups), k)):
        tg = [groups[i] for i in combo]
        yield sid, combo, np.flatnonzero(_train_mask(t0, t1, tg, embargo)), np.concatenate(tg)


def cpcv_path_map(n_groups: int, k: int) -> np.ndarray:
    """Array (n_paths, n_groups): entry = split_id whose test set supplies that group on that path.
    Every path covers every group exactly once."""
    combos = list(itertools.combinations(range(n_groups), k))
    per_group = {g: [i for i, c in enumerate(combos) if g in c] for g in range(n_groups)}
    phi = cpcv_n_paths(n_groups, k)
    return np.array([[per_group[g][p] for g in range(n_groups)] for p in range(phi)])


# ----------------------------------------------------------------------------- PBO (CSCV)
def pbo_cscv(M, n_blocks: int = 16):
    """Probability of backtest overfitting. M: T x N matrix of per-period P&L of N trials (rows synchronous).
    For each of C(S, S/2) train/test block splits: pick the in-sample-best trial, take its out-of-sample
    relative rank w in (0,1), logit = ln(w/(1-w)). PBO = share of splits with logit <= 0 (IS winner is at or
    below the OOS median). Returns dict(pbo, n_combos, logits)."""
    M = np.asarray(M, float)
    T, N = M.shape
    if n_blocks % 2 or N < 2 or T < n_blocks:
        raise ValueError("n_blocks must be even, M needs >= 2 trials and >= n_blocks rows")
    if not np.isfinite(M).all():
        raise ValueError("M contains NaN/inf: fill missing days with 0 (flat) first")
    blocks = np.array_split(np.arange(T), n_blocks)
    cnt = np.array([len(b) for b in blocks], float)
    s1 = np.array([M[b].sum(0) for b in blocks])
    s2 = np.array([(M[b] ** 2).sum(0) for b in blocks])

    def sr(ix):
        n = cnt[ix].sum()
        mu = s1[ix].sum(0) / n
        var = s2[ix].sum(0) / n - mu ** 2
        return mu / np.sqrt(np.maximum(var, 1e-300))

    logits = []
    everything = set(range(n_blocks))
    for c in itertools.combinations(range(n_blocks), n_blocks // 2):
        is_ix = list(c)
        oos_ix = sorted(everything - set(c))
        best = int(np.argmax(sr(is_ix)))
        oos = sr(oos_ix)
        rank = (oos < oos[best]).sum() + 1                  # 1 = worst, N = best
        w = rank / (N + 1.0)
        logits.append(math.log(w / (1 - w)))
    logits = np.array(logits)
    return {"pbo": float((logits <= 0).mean()), "n_combos": len(logits), "logits": logits}


# ----------------------------------------------------------------------------- multiple testing
def bonferroni(p, alpha: float = 0.05):
    p = np.asarray(p, float)
    return p < alpha / len(p)


def holm(p, alpha: float = 0.05):
    """Holm step-down; returns boolean reject mask in the original order. Valid under any dependence."""
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    rej = np.zeros(m, bool)
    for rank, i in enumerate(order):
        if p[i] < alpha / (m - rank):
            rej[i] = True
        else:
            break
    return rej


def benjamini_hochberg(p, alpha: float = 0.05):
    """BH step-up FDR control (independence or positive dependence); boolean reject mask."""
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    thresh = alpha * (np.arange(1, m + 1)) / m
    ok = np.flatnonzero(p[order] <= thresh)
    rej = np.zeros(m, bool)
    if len(ok):
        rej[order[: ok.max() + 1]] = True
    return rej


# ----------------------------------------------------------------------------- permutation null
def permutation_pvalue(position, ret, n_perm: int = 3000, seed: int = 0, rotate: bool = False):
    """Timing null: shuffle the daily positions (sizes and signs kept, so exposure mix is kept) against the
    returns. position[t] must already be lagged (it is the position held over ret[t]).
    rotate=True uses a random circular shift instead of an iid shuffle: use it when positions are held for
    several days, because an iid shuffle destroys the holding structure and gives a null that is too narrow.
    p = (1 + #{null Sharpe >= observed}) / (n_perm + 1). Returns (p, observed SR, null SR array); p is NaN
    when the observed Sharpe is undefined (flat or constant P&L)."""
    position, ret = np.asarray(position, float), np.asarray(ret, float)
    rng = np.random.default_rng(seed)
    obs = sharpe(position * ret)
    null = np.empty(n_perm)
    for i in range(n_perm):
        pos = np.roll(position, int(rng.integers(1, len(position)))) if rotate else rng.permutation(position)
        null[i] = sharpe(pos * ret)
    if not np.isfinite(obs):
        return float("nan"), obs, null
    return float((1 + (null >= obs).sum()) / (n_perm + 1)), obs, null


# ----------------------------------------------------------------------------- uniform verdict
def verdict(dsr_value, top3_share, net_sharpe_2x_cost, perm_p, n_trades, min_trades: int = 20):
    """Single pass/fail gate with the reasons that failed. Defaults documented in SKILL.md."""
    fails = []
    if not dsr_value >= 0.95:
        fails.append("DSR < 0.95")
    if not top3_share < 0.60:
        fails.append("top-3 trades >= 60% of P&L")
    if not net_sharpe_2x_cost > 0:
        fails.append("net Sharpe <= 0 at 2x costs")
    if not perm_p <= 0.05:
        fails.append("permutation p > 0.05")
    if n_trades < min_trades:
        fails.append(f"fewer than {min_trades} trades")
    return ("ALIVE" if not fails else "NOT PROVEN"), fails


# ----------------------------------------------------------------------------- CLI
def _load(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def trials_matrix(pnl: pd.DataFrame) -> pd.DataFrame:
    """Canonical pnl table -> date x strategy_id matrix of total_ccy (package_id == 'ALL' rows if present)."""
    if "package_id" in pnl and (pnl["package_id"] == "ALL").any():
        pnl = pnl[pnl["package_id"] == "ALL"]
    m = pnl.pivot_table(index="date", columns="strategy_id", values="total_ccy", aggfunc="sum").sort_index()
    return m.fillna(0.0)


def report(pnl: pd.DataFrame, strategy: str | None, n_trials: int | None, blocks: int, ppy: float = 252.0):
    m = trials_matrix(pnl)
    srs = np.array([sharpe(m[c]) for c in m])
    srs_ok = srs[np.isfinite(srs)]
    chosen = strategy or m.columns[int(np.nanargmax(srs))]
    r = m[chosen].values
    n_log = n_trials or m.shape[1]
    if len(srs_ok) < 2 and n_log > 1:
        print("WARNING: <2 trials with a Sharpe: V[SR_n] is unknown, so DSR below is NOT deflated. "
              "Supply the Sharpes of every trial (all columns of the trial log).")
    n_eff = effective_trials(m)
    print(f"trials in matrix: {m.shape[1]}   trial-log N used: {n_log}   effective N (heuristic): {n_eff:.1f}")
    print(f"strategy: {chosen}   T={len(r)}   annual SR={annualise(sharpe(r), ppy):.2f}   "
          f"skew={stats.skew(r):.2f}   kurt={stats.kurtosis(r, fisher=False):.2f}   "
          f"NW t (lags=21)={newey_west_t(r, 21):.2f}")
    for label, n in (("N = trial log", n_log), ("N = effective", max(int(round(n_eff)), 2))):
        sr_star = expected_max_sharpe(n, float(np.var(srs_ok, ddof=1)) if len(srs_ok) > 1 else 0.0)
        print(f"  {label:14s} E[max SR] annual={annualise(sr_star, ppy):.2f}   DSR={dsr(r, srs, n):.3f}")
    if m.shape[1] >= 2 and len(m) >= blocks:
        res = pbo_cscv(m.values, blocks)
        print(f"PBO (CSCV, {blocks} blocks, {res['n_combos']} splits) = {res['pbo']:.2f}")
    else:
        print("PBO skipped: needs >= 2 trial columns and >= one row per block")


# ----------------------------------------------------------------------------- selftest
def _selftest() -> int:
    fails = []

    def check(name, cond):
        if not cond:
            fails.append(name)

    # walk-forward: counts, order, gap
    sp = list(walk_forward_splits(10, 4, 2))
    check("wf count", len(sp) == 3)
    check("wf expanding", list(sp[1][0]) == list(range(6)) and list(sp[1][1]) == [6, 7])
    sp = list(walk_forward_splits(10, 4, 2, expanding=False, gap=1))
    check("wf rolling+gap", len(sp) == 2 and list(sp[0][1]) == [5, 6] and list(sp[1][0]) == [2, 3, 4, 5])
    check("wf test after train", all(tr.max() < te.min() for tr, te in sp))

    # purged k-fold: label of 3 bars, fold {4,5} -> obs 2,3 purged (end inside test span); embargo 1 drops obs 8
    t0 = np.arange(10)
    t1 = t0 + 2
    tr = [s for s in purged_kfold(t0, t1, 5, 0)][2]
    check("purge basic", list(tr[1]) == [4, 5] and set(tr[0]) == {0, 1, 8, 9})
    tr = [s for s in purged_kfold(t0, t1, 5, 1)][2]
    check("embargo", set(tr[0]) == {0, 1, 9})
    # a training label that ENVELOPS the test block must be purged (third overlap condition)
    e0 = np.array([0, 1, 2, 3, 4])
    e1 = np.array([9, 1, 2, 3, 4])
    m = _train_mask(e0, e1, [np.array([2])], 0)
    check("purge envelope", (not m[0]) and m[1] and m[3] and m[4])

    # CPCV: N=6,k=2 -> 15 splits, 5 paths; N=10,k=2 -> 9 paths; every path covers each group once
    check("cpcv counts", cpcv_n_splits(6, 2) == 15 and cpcv_n_paths(6, 2) == 5 and cpcv_n_paths(10, 2) == 9)
    pm = cpcv_path_map(6, 2)
    check("cpcv paths shape", pm.shape == (5, 6))
    combos = list(itertools.combinations(range(6), 2))
    check("cpcv path covers groups", all(g in combos[pm[p, g]] for p in range(5) for g in range(6)))
    check("cpcv paths distinct splits per group", all(len(set(pm[:, g])) == 5 for g in range(6)))
    t0 = np.arange(120)
    sp = list(cpcv_splits(t0, t0 + 2, 6, 2, embargo=1))
    check("cpcv n", len(sp) == 15)
    check("cpcv no overlap", all(not (set(tr) & set(te)) for _, _, tr, te in sp))
    check("cpcv purge gap", all(all(abs(a - b) > 2 for a in te for b in tr) for _, _, tr, te in sp[:3]))

    # expected max normal vs Monte Carlo, bound sqrt(2 ln n)
    rng = np.random.default_rng(1)
    mc = rng.standard_normal((20000, 100)).max(1).mean()
    check("E[max] vs MC", abs(expected_max_normal(100) - mc) < 0.05)
    check("E[max] bound", expected_max_normal(100) <= math.sqrt(2 * math.log(100)))

    # PSR
    check("psr at benchmark", abs(psr(0.1, 250, 0, 3, 0.1) - 0.5) < 1e-12)
    check("psr value", abs(psr(0.1, 250) - 0.9423) < 2e-3)
    check("psr skew/kurt hand value", abs(psr(0.2, 60, -1.0, 8.0) - 0.91359) < 1e-4)  # var = 1 + .2 + 7/4*.04 = 1.27
    check("psr neg skew lowers", psr(0.1, 250, -2.448, 10.164) < psr(0.1, 250))
    sims = rng.standard_normal((4000, 250))
    p = np.array([psr_from_returns(s) for s in sims])
    check("psr calibration", 0.03 < (p > 0.95).mean() < 0.07 and abs(p.mean() - 0.5) < 0.02)

    # dsr(): independent re-derivation (scipy only) at the SKILL worked example: T=1260, SR 1.5/yr, trial SD 0.5/yr, N=100
    sr_h, T_, sd_ = 1.5 / math.sqrt(252), 1260, 0.5 / math.sqrt(252)
    g_ = 0.5772156649015329
    srs_ = stats.norm.ppf(1 - 1 / 100) * (1 - g_) + g_ * stats.norm.ppf(1 - 1 / (100 * math.e))
    z_ = (sr_h - sd_ * srs_) * math.sqrt(T_ - 1) / math.sqrt(1 + 0.5 * sr_h ** 2)
    rr = rng.standard_normal(T_)
    rr = (rr - rr.mean()) / rr.std(ddof=1) * 0.01 + sr_h * 0.01        # per-period SR exactly sr_h, ~Gaussian moments
    ts_ = np.array([0.0, math.sqrt(2) * sd_])                          # two trial Sharpes, sample variance sd_^2
    check("dsr trial-variance input", abs(np.var(ts_, ddof=1) - sd_ ** 2) < 1e-15)
    check("dsr value ~0.70", abs(dsr(rr, ts_, 100) - stats.norm.cdf(z_)) < 0.02 and 0.65 < dsr(rr, ts_, 100) < 0.75)
    check("dsr monotone in N", dsr(rr, ts_, 10) > dsr(rr, ts_, 100) > dsr(rr, ts_, 1000))
    check("dsr ignores NaN trials", abs(dsr(rr, np.append(ts_, np.nan), 100) - dsr(rr, ts_, 100)) < 1e-12)

    # DSR: 100 trials with trial-SR variance 0.5 -> SR* = sqrt(.5) * 2.534
    check("SR* closed form", abs(expected_max_sharpe(100, 0.5) - 1.7918) < 5e-3)
    check("effective N", abs(effective_trials(pd.DataFrame(np.ones((50, 4)) + np.arange(4) * 0 +
                                                             rng.standard_normal((50, 1)))) - 1.0) < 1e-9
          and 3.2 < effective_trials(pd.DataFrame(rng.standard_normal((5000, 4)))) <= 4.0)

    # minimum backtest length: 7 trials, SR 1 -> about 2 years; MC of best-of-7 noise over 2y
    check("minBTL 7 trials", 1.7 < min_backtest_years(7, 1.0) < 2.1)
    daily = rng.standard_normal((4000, 7, 504))
    best = (daily.mean(2) / daily.std(2, ddof=1) * math.sqrt(252)).max(1).mean()
    check("best of 7 noise ~ 1 (annual SR)", 0.85 < best < 1.1)

    # Newey-West: AR(1) rho 0.5 -> variance of mean inflated by (1+rho)/(1-rho)=3 -> t shrinks by sqrt 3
    n, rho = 40000, 0.5
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = rho * x[i - 1] + e[i]
    x += 0.01
    naive_t = x.mean() / (x.std(ddof=1) / math.sqrt(n))
    check("NW shrinks t by sqrt(3)", abs(naive_t / newey_west_t(x, 40) - math.sqrt(3)) < 0.15)

    # multiple testing: textbook example (5 managers)
    pv = [0.006, 0.012, 0.601, 0.756, 0.918]
    check("bonferroni 1", bonferroni(pv).sum() == 1)
    check("holm 2", holm(pv).sum() == 2)
    check("bh", benjamini_hochberg([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216], 0.05).sum() == 2)

    # strategy-failure maths (payoffs -1% / +0.5%, 260 bets)
    check("bet SR p=.70", abs(bet_sharpe(0.70, 260, 0.005, -0.01) - 1.173) < 2e-3)
    check("bet SR p=2/3", abs(bet_sharpe(2 / 3, 260, 0.005, -0.01)) < 1e-9)
    check("breakeven p", abs(breakeven_precision(0, 260, 0.005, -0.01) - 2 / 3) < 1e-9
          and abs(breakeven_precision(1.173, 260, 0.005, -0.01) - 0.70) < 1e-3)
    check("failure prob", failure_probability(231, 71, 2 / 3) < 1e-3 and 0.05 < failure_probability(180, 80, 2 / 3) < 0.25
          and failure_probability(10, 10, 2 / 3) > 0.9)

    # constant (flat) trial column must not break effective N
    check("effective N constant col", np.isfinite(effective_trials(pd.DataFrame({"a": np.zeros(50), "b": rng.standard_normal(50)}))))

    # top-3 share
    check("top3", abs(top_k_share([10, 5, 3, 1, 1], 3) - 0.9) < 1e-12)

    # PBO: 16 blocks -> 12870 splits (book prints 12,780 in error); noise ~ 0.5; one skilled column ~ 0
    noise = rng.standard_normal((1600, 20))
    res = pbo_cscv(noise, 16)
    check("pbo combos", res["n_combos"] == 12870)
    check("pbo noise ~0.5", 0.38 < res["pbo"] < 0.62)
    skilled = noise.copy()
    skilled[:, 3] += 0.15
    check("pbo skilled ~0", pbo_cscv(skilled, 16)["pbo"] < 0.05)

    # permutation null: look-ahead positions beat the null, random positions do not
    r = rng.standard_normal(1500)
    p_cheat, _, _ = permutation_pvalue(np.sign(r), r, 500, 1)
    p_rand = [permutation_pvalue(np.sign(rng.standard_normal(1500)), r, 200, i)[0] for i in range(20)]
    check("perm cheat", p_cheat < 0.01)
    # rotate null keeps holding structure: persistent (5-day block) positions on iid returns must NOT look significant
    blk = np.repeat(rng.choice([-1.0, 1.0], 300), 5)
    p_blk = [permutation_pvalue(blk, rng.standard_normal(1500), 200, i, rotate=True)[0] for i in range(20)]
    check("perm rotate null calibrated", np.mean(np.array(p_blk) < 0.05) <= 0.2)
    check("perm rotate cheat", permutation_pvalue(np.sign(r), r, 300, 2, rotate=True)[0] < 0.01)
    check("perm nan obs -> nan p", math.isnan(permutation_pvalue(np.zeros(50), r[:50], 20)[0]))
    check("perm random not systematically significant", np.mean(np.array(p_rand) < 0.05) <= 0.2 and np.mean(p_rand) > 0.3)

    # verdict
    check("verdict pass", verdict(0.97, 0.4, 0.3, 0.01, 40)[0] == "ALIVE")
    check("verdict fail", verdict(0.97, 0.7, 0.3, 0.01, 40)[1] == ["top-3 trades >= 60% of P&L"])

    # report path on a synthetic canonical pnl table
    days = pd.bdate_range("2020-01-01", periods=800)
    rows = [pd.DataFrame({"date": days, "strategy_id": f"s{j}", "package_id": "ALL",
                          "total_ccy": rng.standard_normal(800) * 1000}) for j in range(8)]
    report(pd.concat(rows), None, None, 8)

    if fails:
        print("SELFTEST FAILED: " + ", ".join(fails))
        return 1
    print("selftest ok")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["report"])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pnl", help="canonical pnl table (csv/parquet)")
    ap.add_argument("--strategy", help="strategy_id to judge (default: best in-sample Sharpe)")
    ap.add_argument("--n-trials", type=int, help="trial-log row count if larger than the columns supplied")
    ap.add_argument("--blocks", type=int, default=16)
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.cmd == "report" and a.pnl:
        report(_load(a.pnl), a.strategy, a.n_trials, a.blocks)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
