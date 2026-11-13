---
name: bt-validation-and-overfitting
description: 'Decide whether a backtested G10 rates RV signal or strategy is real or overfit. Covers pre-registration and trial logs, walk-forward, purged/embargoed k-fold, combinatorial purged CV (CPCV), holdout discipline, parameter plateaus, Sharpe inference (Newey-West/HAC, probabilistic and deflated Sharpe, minimum backtest length, effective trials), probability of backtest overfitting (PBO/CSCV), permutation and placebo nulls, cost ladder, multiple-testing control (Bonferroni, Holm, BH), look-ahead/leakage tests, strategy-failure probability, sequential evidence. Use when asked ''is this backtest overfit'', ''backtest validation'', ''out-of-sample'', ''walk-forward'', ''purging'', ''embargo'', ''CPCV'', ''deflated Sharpe'', ''PBO'', ''how many trials'', ''data snooping'', ''look-ahead bias'', ''does the signal survive costs'', ''multiple testing across spreads/flies'', ''holdout'', or before promoting any curve, fly, swap-spread, basis, STIR, bond or vol signal to a trade idea. Building the engine and P&L chain: bt-backtest-design.'
---

# Backtest validation and overfitting control

A rates RV backtest is one draw from a very large garden of forking paths: lookbacks, thresholds, tenors, hedge
weights, entry dates. The best of N zero-skill draws always looks good, and the expected maximum grows with N. This
skill is the gate between "the backtest looks good" and "the signal is probably real": it fixes the protocol
before the run, chooses a split that does not leak, counts every trial, and tests the survivor against nulls,
costs and multiple-testing corrections. The default verdict is "not proven"; a negative result is a valid outcome.

## When to use
- Any request to validate, audit or stress a backtest, a z-score or PCA-residual signal, a systematic overlay or an ML model.
- Choosing a split: walk-forward vs purged k-fold vs CPCV vs a held-out quarantine period.
- A Sharpe, IC or hit rate "looks too good": run the leakage tests and the deflation below before believing it.
- Scanning many spreads, flies, tenors, months or parameters and reporting the best ones.
- Deciding how many trials were run, and what Sharpe the best of them would show with zero skill.
- Before promoting a screen result to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Daily P&L per strategy, net of costs | `pnl` (`package_id = ALL`, `total_ccy`) | daily, full backtest plus holdout | one column per trial in the trials matrix; missing day = flat |
| Signals as decided on each date | `signals` | daily | signal at `t` uses data to close of `t`; position from `t+1` |
| Positions and fills | `positions`, `trades` | daily / per trade | trade count, per-trade P&L, holding periods (the independent unit) |
| Label or holding horizon per observation | derived from `trades` | start and end bar per trade | drives purge/embargo and the Newey-West lag |
| Trial log (every run, incl. controls) | `trial_log` (append-only) | one row per run | `strategy_id`, `param_hash`, sample window, `cost_multiple`, `sharpe_is`, `sharpe_oos`, `is_control`, `status` |

Needs at least 3 years of daily history for a single-parameter daily rule, and about 252 daily observations per
free parameter (Chan, Quantitative Trading, 2009). If P&L, holding periods or the trial log are missing, ask the user
or the data adapter; never reconstruct a trial count from memory. Table definitions:
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Method

### 1. Pre-register before the first run
1. **State the mechanism** (who loses money to us and why it persists). A theory with an economic mechanism comes first;
   features may come from a black box, the strategy may not (López de Prado, Advances in Financial Machine Learning, 2018).
2. **Fix the parameter set and the budget.** At most 5 free parameters including thresholds, holding period and
   lookback (Chan, 2009); the internal convexity-RV spec used 6 and listed each tuning grid in advance. Qualitative
   choices made after repeated runs (open vs close entry, overnight holding) count as parameters.
3. **Fix the pass bars in numbers** (template, internal forward-curve-vs-straddle backtest spec v0.4, Oct 2026):
   net OOS Sharpe at 1x costs >= 0.4 and DSR >= 0.95; beats always-on and random-entry controls (bootstrap p < 0.10);
   hedge leg helps in stress windows; the edge is the intended one (intended component >= 50% of pre-cost P&L);
   score ranks forward P&L (pooled IC > 0, Newey-West t >= 2 at the holding horizon); net Sharpe > 0 at 2x costs.
4. **Fix direction, universe, sample start.** Start the sample after any data seam (IBOR to RFR splice, contract
   redefinition). Exclude universe members only for data corruption, never for performance.
5. **Lock the holdout** (section 2) and **open a trial log**. Every run, including controls and categorical choices
   (curve source, interpolation, hedge type), appends one row. Rows = N in every deflation below.
6. **Costs on in every headline number**, sign conventions established empirically on a known case, every run saved with
   its full config, in-sample never reported as performance, no silent default changes.
7. **Stop and ask** when data are shorter than assumed, two reasonable implementations differ materially, or the spec looks wrong.
   Keep a deviations list: spec says / did / why / expected effect.

### 2. Choose the split
| Scheme | Use when | Guard | Limit |
|---|---|---|---|
| Simple train/test (older/recent) | quick sanity check of 1-3 parameters | test >= 1/3 of train; fit everything (weights, z-score mean/std) on train only | one path; easy to reuse |
| **Walk-forward (WF)** | default for daily RV rules; closest to production | expanding IS 3y, OOS 1y, step 1y; `gap >=` label horizon; <= 6 tuned parameters | single path; weak early folds |
| **Purged k-fold** | ML or any model with labels longer than 1 bar | purge + embargo (below); unshuffled | no historical story |
| **CPCV** | you need a distribution of OOS Sharpes, or PBO/DSR inputs | N groups, k test groups, purge + embargo | model fits = C(N, k) |
| **Quarantine / holdout** | final one-shot test of the frozen choice | untouchable in code; run once; report whatever comes out | burns when peeked at |
| Forward / paper | the only true OOS | log before the fact | slow |

**Walk-forward details.** Objective on each IS block = net Sharpe at 1x costs; stitch OOS P&L across folds; judge the
stitched series. WF early decisions use few data: with warm-up `t0` out of `T`, half the decisions rest on an average
of `T/4 + 3·t0/4` points, so a long warm-up shortens the test (López de Prado, 2018). For overlapping labels WF needs a purge of the
labels crossing the train/test boundary but no embargo (López de Prado, 2018). A WF is also overfit by repetition: if results flip when the sequence is
reversed, the signal is overfit.

**Purging.** Label `i` spans `[t0_i, t1_i]`. Drop training obs `i` if its span overlaps a test span `[lo, hi]`:
`t0_i <= hi AND t1_i >= lo` (covers start-inside, end-inside and the case where the training label envelops the whole
test block, the one most often forgotten). **Embargo:** also drop training obs starting within `h` bars after `hi`;
`h ~ 0.01·T` is usually enough (López de Prado, 2018); at least the holding period for daily rules. Diagnostic:
with leakage, CV score keeps improving as k grows toward T; with proper purging it plateaus (López de Prado, 2018).
Label construction, uniqueness weights and OOB inflation are in
[ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md).

**CPCV.** Partition T bars into N contiguous groups; test sets are all C(N, k) choices of k groups:
- splits = `C(N, k)`; paths `phi = k/N · C(N, k)`; train fraction `1 - k/N`; each group lies in `phi` test sets.
- N=6, k=2: 15 splits, 5 paths. N=10, k=2: 45 splits, 9 paths. Rule of thumb: `N = phi + 1`, `k = 2`.
- Assemble `phi` paths (each covers every group once), compute one Sharpe per path: the empirical Sharpe distribution.
  Variance of the mean across paths is `sigma²(1 + (phi-1)·rho)/phi` (rho = average path correlation) (López de Prado, 2018).

**Holdout and quarantine.** Choose the final candidates (top 2-5) before touching it; run it once with the last-fold
parameters; if you peek and retune, it is in-sample from then on, and the repeated-use cost is real: the JPM authors
admit their quarantine "infected" their thinking over about 12 months (JPM, #SquadGoals, 21 Sep 2018). Compare models on an
identical OOS window.

**Invalid OOS designs.** (a) Treat early years as "OOS" after tuning on recent ones; recent markets embed older history.
(b) Split instruments into IS/OOS sets: instruments are correlated. (c) Any OOS you looked at twice. A published
strategy's post-publication period is genuine OOS only if you do not optimise on it (Chan, 2009; Tulchinsky, Finding Alphas, 2015).

**Leakage tests (run all, cheaply).**
1. *Truncation*: run on full data, save positions A; delete the last N rows (N = 10-100), rerun to get B; positions must
   match A on the shared dates, else there is look-ahead (Chan, 2009).
2. *Lag injection*: lag all inputs one more day; a true signal decays gently, a leaky one collapses. Peek at `t+1`: Sharpe must jump.
   Always lag 1 day (2 across time zones); a gold rule scored IR 1.60 with contemporaneous data and "completely broke down" with a 1-day lag (Willer & Saunders, Trading Global Macro Markets, 2026).
3. *Date permutation*: shuffle dates; Sharpe must go to about 0 (internal backtest spec, Oct 2026).
4. *Full-sample statistics*: z-scores, percentile thresholds, regression betas and PCA weights must use data to `t-1` only. Run
   walk-forward vs full-sample on any PCA or regression weighting: a large gap means you are trading the estimator (internal convexity-RV handover note, 2026).
5. *Screening inside folds*: supervised screening (pick the best spreads, then test) must sit inside the training fold. Screening
   100 of 5,000 noise predictors on all data gave CV error 3% against a true 50% (Hastie, Tibshirani, Friedman, Elements of Statistical Learning, 2009).
6. *Snap and alignment*: a +/-1 day misalignment barely moves median vol level but widens dispersion ~30x; grade date logic with an exact identity.
   Mixed snaps (settlement vs end-of-day, 1.82bp/day noise vs 0.55bp real moves in one case) create spurious signals (internal handover note, 2026).
7. *Point-in-time*: restatements, release dates, adjusted vs as-of prices; see [bt-backtest-design](../bt-backtest-design/SKILL.md).

### 3. Select parameters by plateau, not peak
- Pick the grid point with the highest **median** objective over its +/-1-step neighbourhood, not the single maximum (internal backtest spec, Oct 2026);
  drop "fluke" optima with no cluster of similar neighbours; prefer stable, intuitive trends (JPM, Do androids dream of electric bonds?, 22 Nov 2017).
- Neighbourhood test: move one parameter at a time; if performance collapses for any value but the optimum, the result is snooped (Chan, 2009).
- Simplification test: remove conditions one by one; keep the simpler rule if OOS does not drop significantly, even if IS drops. Never add or
  adjust parameters to fix OOS (Chan, 2009).
- Optional: split capital across neighbouring parameter sets (parameter averaging) so live tracks the backtest.
- One-standard-error rule when tuning with CV: choose the simplest model within one SE of the best CV score (Hastie et al., 2009).
- Grid on pre-computed signal panels is fine, but certify the top 2-3 cells through the full engine (one case agreed to 0.9997 daily-change correlation).
- Same lookback and one-day lag reused across rules reduces the freedom to overfit (Willer & Saunders, 2026). Specification noise is large:
  3m momentum IR moved 0.3-0.7 only by changing the rebalance day of the month (JPM, Simple rules to trade duration, 2 Oct 2012).

### 4. Inference on the OOS result
**Per-period vs annual.** `SR_annual = SR_period · sqrt(periods per year)` (252 daily trading days; use actual trading periods), valid for serially
uncorrelated returns. PSR/DSR take per-period Sharpes. No risk-free term for self-financing packages.

**Sampling error.** `IR ~ t/sqrt(years)`, `SE(IR) ~ 1/sqrt(years)`; `SE(SR_hat) = sqrt((1 + SR²/2)/T)` for iid returns. Proving skill
at IR 0.5 takes about 16 years (t = IR·sqrt(years) = 2) (Grinold & Kahn, Active Portfolio Management, 1999). For a 5y daily backtest, SE(annual SR) ~ 0.45.

**Dependence.** Daily P&L of multi-week holds is autocorrelated and a naive t is inflated by roughly `sqrt(days per trade)`.
- Newey-West (Bartlett) t of mean P&L, lag = max(median holding period in days, floor(T^(1/4))). A regression of 1y on 3y UST yield levels gave naive t 107.9 vs HAC 39.9 (Tsay, Analysis of Financial Time Series, 2010).
- Also report **trade-level** statistics and Sharpe on non-overlapping trades; the independent unit is a bet, not a day. Breadth
  `BR = (IR/IC)²`; reassessing annually but rebalancing monthly is 1 bet, not 12 (Grinold & Kahn, 1999).
- Stationary or circular block bootstrap (block = median hold, 5,000 draws) for CIs; check **per-regime** results: alive in one regime and dead in three is not alive.

**Probabilistic Sharpe ratio.** With `SR` per period, `T` returns, skew `g3`, NON-excess kurtosis `g4` (3 if Gaussian), benchmark `SR*` (0 by default):

`PSR[SR*] = Phi( (SR - SR*)·sqrt(T-1) / sqrt(1 - g3·SR + ((g4 - 1)/4)·SR²) )`   (López de Prado, 2018)

PSR >= 0.95 is the 5% test. Fat tails and negative skew (short-vol, carry, convergence trades) lower it.

**Deflated Sharpe ratio.** DSR = PSR evaluated at the benchmark expected under zero skill from `N` trials:

`SR* = sqrt(V[SR_n]) · ( (1 - g)·Z⁻¹[1 - 1/N] + g·Z⁻¹[1 - 1/(N·e)] )`, `g = 0.5772156649`   (López de Prado, 2018)

`V` is the variance of the per-period Sharpes across ALL trials, `N` the independent trial count. Rules:
- `N` = distinct `trial_id` in the trial log, controls and categorical choices included. If trials are highly correlated, also report DSR at an effective
  `N_eff = 1 + (N-1)(1 - mean pairwise correlation)` (heuristic; N = 1 when all trials are one idea, N when independent), and use the larger-N verdict as the headline.
- Compute at the **effective sample size** (overlapping holds and cross-structure correlation make nominal T too large).
- `E[max of N std normals] ~ (1-g)Z⁻¹[1-1/N] + g·Z⁻¹[1-1/(Ne)] <= sqrt(2 ln N)`: 1.39 at N=7, 1.90 at 20, 2.53 at 100, 3.26 at 1000.
- DSR >= 0.95 is the pass bar. An annualised Sharpe above 2 at 95% confidence, reproduced on the same dataset, is still likely false (López de Prado, 2018).

**Minimum backtest length.** The best of `N` zero-skill backtests reaches `E[max_N]/sqrt(years)` in annual SR, so to keep a target annual
`SR_t` out of luck's reach: `years >= (E[max_N] / SR_t)²`. N=7, SR_t=1 gives 1.9 years, matching "after trying seven configurations a researcher
is expected to find a two-year backtest with Sharpe over 1 while the OOS expectation is 0" (Tulchinsky, Finding Alphas, 2015).
Same bound, SR_t = 0.5: 7.7 years at N=7, 14.5 at N=20, 26 at N=100.

### 5. Probability of backtest overfitting (CSCV)
1. Build `M` (T x N): P&L of N trials on one synchronous index (down-sample to a common frequency).
2. Split rows into an even number `S` of contiguous blocks (default 16). Enumerate all `C(S, S/2)` train/test splits
   (S=16: 12,870; the book prints 12,780, a typo).
3. In each split: `n*` = best in-sample Sharpe; `w` = relative OOS rank of `n*` among the N trials, `w = rank/(N+1)`; `logit = ln(w/(1-w))`.
4. `PBO = share of splits with logit <= 0` (the in-sample winner is at or below the OOS median).

Interpretation: PBO near 0.5 = the selection is coin-flipping (pure noise gives 0.5); PBO < 0.1 with a stable IS-to-OOS relationship = selection works;
PBO > 0.5 = the more you optimise, the worse it gets. Example: `SR_OOS = 0.87 - 0.75·SR_IS` (adj R² 0.17), PBO 0.74 (López de Prado, 2018).
Needs N >= 2 genuinely different trials, so log them all; PBO says nothing about a single backtest.

### 6. Nulls and controls the winner must beat
| Control | What it tests | Pass |
|---|---|---|
| **Timing permutation**: shuffle daily positions (sizes, signs, sell fraction kept) vs returns, 3,000 draws; for multi-day holds use a circular shift (`rotate=True`) so the holding structure survives | skill beyond exposure mix | observed Sharpe above the 95th pct (CV stage: above the null max); `p = (1+#{null>=obs})/(draws+1)` |
| Always-on / carry benchmark (buy-and-hold, sell vol) | mere exposure | beat it, not zero; high kurtosis lets a few days dominate Sharpe (JPM, 22 Nov 2017) |
| Random entry, 1,000 draws | entry timing | p < 0.10 |
| Inverted signal | sign sanity | should lose |
| Shuffled-sign placebo with calendar and sizing kept; mismatched-pair placebo | calendar/structure artefact | beat the 95th percentile |
| Date permutation, look-ahead injection | the checker itself | Sharpe ~ 0; Sharpe jumps |
| Ablation (drop each gate or the model, keep raw z-score) | which part earns | the model must add |
| Cost ladder 0x / 0.5x / 1x / 2x / 3x, plus break-even cost | cost fragility | net > 0 at 2x ("dies at 2x = never alive"); report break-even bp/leg |
| Delete-one instrument / null group | coding errors | stable |

Judge a timing model against the permutation benchmark at the SAME long/short mix, not passive long in a trending market:
a Sharpe of 0.75 at 50% sold is far better than 0.75 at 80% long (JPM, Is bank convexity hedging lying in wait?, 31 May 2019).
For ML ensembles, shuffle the secondary model's decisions (JPM, TradeRunner, 16 Aug 2018).
State factor exposure before quoting P&L: regress daily P&L on level/slope/vol changes and a benchmark P&L and report alpha t; a convex payoff
must show a smile, not a ramp, when P&L is bucketed by size of move.

### 7. Multiple testing in scans
- Chance of at least one |t| >= 2 among 20 informationless strategies is 64%; with m independent tests FWER = `1 - (1-alpha)^m` (m=100: 0.994).
- Scanning spreads/flies/tenors: apply **Holm** (any dependence) for a few decisive tests, **Benjamini-Hochberg** FDR for large screens;
  report how many flagged vs the `alpha·m` expected by chance ("green jelly beans"). Seasonality: 2007-2017 Bund ASW January/September
  tightening was not supported (p 0.750 and 0.136) (swapsball.net, Testing for seasonality, 19 Nov 2017).
- Compare the winner with the distribution of family MAXIMA, not a single-test null. Formulas, the 5-manager Holm example and
  post-hoc p-value calibration: [references/multiple-testing-and-sequential.md](references/multiple-testing-and-sequential.md).

### 8. Verdict gate (defaults; adjust only before the run)
| Test | Default | Why |
|---|---|---|
| DSR (full trial count incl. controls) | >= 0.95 | 5% false-discovery bar after selection |
| OOS net Sharpe at 1x costs (WF + holdout) | >= 0.4 | pre-registered bar, internal spec |
| Net Sharpe at 2x costs | > 0 | costs are under-modelled more often than over |
| Permutation / placebo percentile | >= 95th | exposure-matched luck |
| Top-3 trades share of total P&L | < 0.60 | concentration fragility |
| OOS trades per side | >= 20 (below: descriptive only) | 10 trades leave SE of a hit rate near 15 points; 20 is the spec floor |
| OOS / IS performance ratio | >= 0.5 (Narang: OOS/IS R² >= 0.5 is good); far below = overfit | IS-to-OOS decay is the overfit measure |
| Parameter neighbourhood | median of +/-1 neighbours within ~30% of chosen | no knife edge |
| Regimes | positive in a majority of distinct policy regimes | alive in one is not alive |
Output "ALIVE" only if all pass; otherwise "NOT PROVEN" with the failing rows. Combine sides only if each passes alone.

### 9. Verify the checker before trusting it
A wrong checker reports success. Known-answer tests for an RV backtest engine (internal backtest spec, Oct 2026): flat strip with zero moves gives zero curve P&L to 1e-9;
simulated delta-hedged option with realised vol = implied gives mean P&L about 0, and at 2x implied gives `0.5·Gamma·(sigma_r² - sigma_i²)` per unit time (normal vol, Gamma per bp²); zero-move
day carry = carry · days/365.25 (Friday to Monday = 3x); long and short sides symmetric to 1e-9; look-ahead injection raises Sharpe sharply;
date permutation gives about 0; attribution residual <= 10% of gross. Record the bias factor of any estimator recovered on synthetic data next to
every live estimate (a 5% vol bias, about 4.5 vol points, can equal the whole edge). **Mutation test:** break a sign or factor on purpose,
confirm the matching test fails, restore.

### 10. Strategy-failure probability (precision form)
For bets with payoffs `pi+ > 0 > pi-` and precision `p`, `n` bets per year: `SR = ((pi+ - pi-)·p + pi-) / ((pi+ - pi-)·sqrt(p(1-p))) · sqrt(n)`.
Break-even `p* = -pi-/(pi+ - pi-)`. With n=260, payoffs +0.5% / -1%: p=0.70 gives SR 1.17, p=0.72 gives 1.9, p=2/3 gives 0.
A 2-point change in hit rate lifts the Sharpe by about 60% (1.17 to 1.9), so the CI on precision matters more than its point value. Failure probability
`P[p < p_target]`: the book bootstraps `p` over the assessment horizon; a simple alternative is a Beta(wins+1, losses+1) posterior. Reject if > 5% (López de Prado, 2018).
Illustration with the Beta form (our calculation, not from the book): 231 wins / 71 losses against `p* = 2/3` fails with probability 0.0001; 180 / 80 fails with 0.20, so reject.
Bet counts, not days, set `n`; `pi+`, `pi-` are the mean winning and losing bet.

### 11. Sequential / anytime-valid evidence (live tracking)
- A p-value picked after seeing the data is not evidence at face value. Calibrate it with a rule fixed in advance: a p of 0.05
  found by looking back is worth about 2.5x (Vovk-Sellke bound) to 4.5x (a simple calibrator), not 20x (Shafer & Vovk, Game-Theoretic Foundations for Probability and Finance, 2019).
- Test ONE strategy as a betting game: a non-negative capital process starting at 1 reaches `lambda` with probability at most `1/lambda` under the null (Ville/Doob).
  Do not count how many of many correlated strategies beat a threshold (Shafer & Vovk, Probability and Finance: It's Only a Game!, 2001).
- Measure time by accumulated variance, not calendar time, when normalising P&L. Details: [references/multiple-testing-and-sequential.md](references/multiple-testing-and-sequential.md).

## Worked example
**Deflating a good-looking Sharpe** (illustrative inputs, computed with `scripts/validation.py`). A daily fly strategy shows annual SR 1.5 over 5y
(T = 1,260 days), skew -0.5, kurtosis 6. The trial log has N distinct trials; the annual-SR variance across trials is 0.25 (SD 0.5).

| N (distinct trials) | zero-skill best annual SR, `SR*` | DSR |
|---|---|---|
| 1 | 0 | 0.999 |
| 10 | 0.79 | 0.94 |
| 100 | 1.27 | 0.69 |

Same backtest, same returns: convincing at 1 trial, about 70% at 100. If you tried 100 lookback/threshold/tenor combinations,
a 1.5 is not enough; you need a longer sample, fewer trials (restraint) or a higher Sharpe. At daily frequency with SR 1.5 the skew and kurtosis
terms move DSR by under 0.01 (Gaussian 0.700 vs 0.695 at N=100); they matter for trade-level or monthly series with strongly negative skew,
so keep them in the formula.

**Walk-forward vs in-sample gap** (Salomon Brothers, Understanding the Yield Curve Part 4, Aug 1995): the 1965-95 expanding-window bond excess-return model had in-sample scaled
excess return 11.15% but OOS 8.64% (Sharpe 0.68); a 0/1 version 4.94% IS vs 4.16% OOS (Sharpe 0.53); the 16-23% shortfall was attributed to data snooping, and the
OOS sign was right 61% of months. A shortfall of that size is the benchmark for a modest, economically motivated model; a collapse is the warning.

**Plateau and threshold grids** (BofA Merrill Lynch, A simple framework for swap spread relative value, 2 Jun 2016): US swap-spread PCA dislocation backtest,
threshold 1.0 to 2.0 sd, Sharpe 1.2, 1.2, 1.0, 0.8, 0.7, 0.4 and bp/day 0.15, 0.16, 0.14, 0.13, 0.13, 0.08: neighbouring cells tell the same story
with no lone peak, so the choice is not a knife edge; but the best cells are the many-small-trades ones, which costs erode first. Costs, carry and stops were excluded, so treat the levels as upper bounds. Germany's Sharpe rose from 2.4 to 2.8 with threshold
while days in position fell from 2,278 to 967: fewer trades, same story, still no costs.

**Costs flip the sign** (Chan, 2009): a 2006 equity reversal strategy had Sharpe 0.25 gross and -3.19 net of 5bp one-way; a 5-minute index mean-reversion rule showed about 3 gross and about -3
net of 1bp. For rates, UST on-the-run 2s/5s/10s/30s top-of-book widths were roughly 0.4bp, 0.2-0.3bp, 0.2-0.3bp, 0.1-0.2bp (JPM, TradeRunner, 16 Aug 2018), and the 10y bid/ask cut a timing model's Sharpe by just under 0.1
(JPM, Do androids dream of electric bonds?, 22 Nov 2017). More sell-side validation cases in [references/rates-validation-cases.md](references/rates-validation-cases.md).

## Signals & interpretation
- **Too good**: IR above 2 on public information, IC above 0.20, OOS R² above 0.15 (a signal with R² 0.05 OOS is superb) point to a bug before they point to alpha
  (Grinold & Kahn, 1999; Narang, Inside the Black Box, 2024). IC tiers: 0.05 good, 0.10 great, 0.15 world-class. Only about 10% of realised IRs exceed 1.
- **Equity Sharpe brackets do not transfer** to a few dozen RV packages; demand deeper per-instrument evidence and stronger OOS discipline (Tulchinsky, 2015).
- **Uniqueness**: a new signal with correlation above ~0.7 to the existing pool adds little (Tulchinsky, 2015); measure IC period by period on non-overlapping intervals, not on overlapping windows (Grinold & Kahn, 1999).
- **Time-decay check**: delay execution by 1, 2, 3 days. A signal that improves with delay is early or leaky.
- **Signal strength buckets**: average return per forecast bucket should rise with magnitude; hit rate alone can be flat (Salomon, Part 4, Aug 1995).
- **Persistence gate**: a "cheap/rich" reading that holds 75-85% of days is structural carry, not transient RV; require the share of the last 252 days with the same sign <= 0.6 (internal backtest spec, Oct 2026).
- **Trade-level vs daily**: a factor unidentified in daily P&L (t 0.9-2.1) may be visible at trade level (t 2.1-5.4), but collinear factors need incremental R² (internal handover note, 2026).
- **Performance dominated by % time long in a bull market** (12m momentum best because long 77% of the time) is exposure, not skill (JPM, 2 Oct 2012).
- **Live vs backtest divergence**, check in order: system bugs, do live trades match backtest trades, execution cost, illiquid names, only then snooping and regime shift (Chan, 2009).
  Use IS drawdown size and duration as the benchmark for "worse than normal".

## Pitfalls
- **Reporting the winner without N.** Every result is reported with all trials that produced it (the "Third Law of Backtesting"; López de Prado, 2018). Researching under the influence of a backtest ("start from scratch when it fails") defeats this.
- **Backtesting is not a research tool.** The purpose is to discard bad models; the loop data-model-backtest-repeat finds a false strategy in about 20 iterations at 5% significance (López de Prado, 2018).
- **Single-instrument discoveries.** Model whole universes or asset classes; a mistake that exists on one security is likely a false discovery. Bag the model: if bagging hurts, it was fitted to outliers.
- **Overlapping labels treated as IID** inflate OOB/CV scores and t-stats. Use purged contiguous folds and HAC.
- **Regression on levels** (R² 96.5% for 1y vs 3y UST, non-cointegrated) and **single-OOS windows** are not validation; a regression on changes cannot give a fair value (Tsay, 2010; swapsball.net, Regression in finance, 27 Oct 2017).
- **Costs excluded** inflate hit ratios, especially at low thresholds; high-threshold cells with a handful of trades show 100% hit rates (BofA, Many EGBs, one simple value tool, 21 Mar 2018).
- **Regime shift, sample too short.** Expanding windows adapt slowly; expect degradation at policy transitions (end of QE reinvestment). PCs and their loadings change by regime, so weights fit in one regime fail in another (Quantitative Finance Stack Exchange, butterfly 2s5s10s directionality Q&A, 2018, edited 2021). Too-short calibration is noisy, too-long is stale; an older analogous regime may beat the latest window (Tuckman & Serrat, Fixed Income Securities, 2022).
- **Small event samples** (n < 25) are base rates, not tests; expect some strategies to break (Willer & Saunders, 2026). Max drawdown hinges on one path point; 99% CVaR on ~200 observations rests on ~2 points (Palomar, Portfolio Optimization, 2025).
- **Calibrating profit-take/stop-loss by historical simulation** overfits; on slow-reverting spreads (half-life 25, 50, 100 days) heat-maps go flat, so there is no optimal rule. Fit the OU process and simulate instead (López de Prado, 2018); see [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md).
- **Evaluation target noise.** Scoring a fair-value model against the next noisy print rewards the overfit model: apparent error 0.020 vs 0.038, actual error vs truth 0.056 vs 0.029 (Cotton, NYU Tandon seminar slides, 27 Apr 2016).
- **ML specifics.** Near-100% in-sample accuracy is memorisation; the best single learner of many is the "million dart players" fallacy (JPM, 22 Nov 2017). A model trained in a rally learns long-only and fails in a selloff; judge on much longer samples.
- **Market seams.** Reference-rate transitions (IBOR to RFR; CDOR ceased 28 Jun 2024 and CAD futures converted) and short RFR histories (SOFR since 2018, EUR RFR since 2019) mean few independent observations: label such results exploratory. Policy regimes (zero rates, QE, QT, yield-curve control in JPY) are distinct samples; one regime is one observation of the effect. G10 markets with short liquid futures history (NZD, SEK, NOK, CHF) are descriptive only. Snap-time mismatches between futures settlement and end-of-day curves create phantom signals.
- **Extrapolation artefacts.** A 1M expiry slot showed Sharpe 1.94 that came entirely from extrapolating below the shortest quoted node; restricted to the quoted term structure it was -0.19 (internal backtest rigor notes). Pre-register that positions must sit inside the quoted surface or curve envelope.
- **Hiding failures.** A "negative result" is acceptable; hunting for settings until something passes is the failure.

## Output
Return a validation report with:
1. **Protocol**: hypothesis and mechanism, parameter set and grids, pass bars, split, holdout dates, costs, N and trial-log summary.
2. **Table by trial group**: IS vs OOS Sharpe, net at 0x/0.5x/1x/2x costs, break-even cost (bp per leg), trades, top-3 share, NW t, trade-level Sharpe.
3. **Inference**: DSR at N and N_eff with `E[max SR | null]`, PSR, PBO (if N >= 2 trials), CPCV path Sharpe distribution (min / median / max), block-bootstrap CI.
4. **Controls**: permutation percentile, random-entry p, inverted-signal result, ablations, factor regression alpha t.
5. **Robustness**: plateau map or neighbourhood table, per-regime and per-currency results, leakage-test results, time-decay table.
6. **Verdict**: ALIVE or NOT PROVEN, with failing rows and what additional data or trials would change it; list of deviations and engine tests passed.
Hand the survivors, with the caveats and trial counts, to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and [rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Scripts
- [`scripts/validation.py`](scripts/validation.py): walk-forward splits (expanding/rolling, gap), purged/embargoed k-fold, CPCV splits and path map,
  PSR, expected-max Sharpe, DSR, effective trials, minimum backtest length, Newey-West t, top-k share, PBO via CSCV, Bonferroni/Holm/BH, timing permutation p-value (iid shuffle or circular shift),
  strategy-failure maths, verdict gate. CLI: `python scripts/validation.py report --pnl <pnl.csv|parquet> [--strategy ID] [--n-trials N] [--blocks 16]`
  pivots the canonical `pnl` table into a trials matrix and prints DSR and PBO. `python scripts/validation.py --help`; `--selftest` checks known values
  (12,870 CSCV splits, 15 splits / 5 paths for CPCV N=6 k=2, E[max] vs Monte Carlo, PSR calibration, Newey-West shrink by sqrt 3, Holm vs Bonferroni, precision-Sharpe 1.173).
  To import: put the scripts folder on `sys.path`.

## Related skills
- [bt-backtest-design](../bt-backtest-design/SKILL.md): engine, point-in-time data, lag discipline that this skill audits
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): P&L explain and factor regression of the survivor
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): realistic cost and capacity inputs for the cost ladder
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): labels, uniqueness weights, purge/embargo for models, feature importance
- [ml-models-for-rates](../ml-models-for-rates/SKILL.md): model families whose CV and trial counts are judged here
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC, IR, breadth and decay, signal combination weights fitted OOS
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): screens whose multiple-testing burden is controlled here
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): seasonality screens and the jelly-bean check
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): rolling betas and OOS hedge tests
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA weights to validate walk-forward vs full-sample
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): scores whose forward IC and calibration need this validation
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): adversarial review of the survivor
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md): live-vs-backtest tracking after promotion
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): bad prints, seams and snaps that fake signals
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical `pnl`, `signals`, `positions`, `trades`

## References
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): purging/embargo, CPCV, PSR/DSR, PBO/CSCV, walk-forward critique, strategy risk, recommendations against backtest overfitting.
- Internal research documents - Forward Curve vs Straddle systematic backtest spec v0.4 (23 Oct 2026), its backtest implementation prompt, the convexity-RV handover note (2026) and internal backtest-rigor / statistical-inference notes: pre-registered pass bars, trial log = N, holdout lock, controls, engine known-answer and mutation tests, ALIVE gate, support-restriction (extrapolation) check.
- J.P. Morgan - Do androids dream of electric bonds? Machine learning in interest rate markets (Salem, Younger, Zhao et al., 22 Nov 2017): purged contiguous CV, quarantine set, permutation Sharpe thresholds, plateau preference.
- J.P. Morgan - TradeRunner: Ensemble learning-driven systematic trading in interest rate markets (Salem, Younger, Huang, 16 Aug 2018) and #SquadGoals: Stacking and voting with machine learning classifiers (21 Sep 2018): walk-forward with embargo, quarantine results, residual-Sharpe shuffle test.
- J.P. Morgan - Is bank convexity hedging lying in wait? (Younger et al., 31 May 2019): retraining vs a same-sell-fraction random benchmark.
- Grinold, Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): t = IR·sqrt(years), data-mining guards, information analysis, breadth, IC/IR sanity tiers.
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): seven-trials result, invalid OOS designs, trial logs, IS-to-OS gates, robustness criteria.
- Chan - Quantitative Trading (Wiley, 2009): <= 5 parameters, 252 points per parameter, train/test, truncation test, sensitivity and simplification tests, cost-flip examples.
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): Sharpe SE, k-fold critique, single-use holdout, leakage rule.
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): seven sins, overfitting checklists, resampling and randomised backtests.
- Hastie, Tibshirani, Friedman - The Elements of Statistical Learning (2nd ed., Springer, 2009): wrong-way CV, one-standard-error rule, Bonferroni/BH/permutation FDR.
- James, Witten, Hastie, Tibshirani - An Introduction to Statistical Learning with Applications in Python (Springer): Holm, FWER, permutation p-values.
- Narang - Inside the Black Box (3rd ed., Wiley, 2024): time decay, parameter plateau, OOS/IS ratio, R² sanity.
- Shafer, Vovk - Game-Theoretic Foundations for Probability and Finance (Wiley, 2019) and Probability and Finance: It's Only a Game! (Wiley, 2001): p-value calibrators, Ville/Doob bound, variance-clock testing.
- Willer, Saunders - Trading Global Macro Markets (Wiley, 2026): lag discipline, consistent parametrisation, small-sample caveats.
- Tsay - Analysis of Financial Time Series (3rd ed., Wiley, 2010): HAC vs OLS t-stats, spurious levels regressions.
- Tuckman, Serrat - Fixed Income Securities (4th ed., Wiley, 2022): OOS residual check for regression hedges, window choice.
- BofA Merrill Lynch - A simple framework for swap spread relative value (Axel, Satko, Cross, 2 Jun 2016) and Many EGBs, one simple value tool (Satko, 21 Mar 2018): rolling OOS PCA backtests, threshold grids, no-cost caveats.
- J.P. Morgan - Simple rules to trade duration (Mac Gorain, 2 Oct 2012): rebalance-day specification noise, IS-optimised weights vs equal weight.
- Salomon Brothers - Understanding the Yield Curve, Part 3 (Ilmanen, Jul 1995) and Part 4: Forecasting U.S. Bond Returns (Aug 1995): sample-period specificity, expanding-window OOS, IS-vs-OOS gap, subperiods.
- swapsball.net - Testing for seasonality (19 Nov 2017) and Regression in finance: friend or foe? (27 Oct 2017): seasonality test template, 122-day/122-day OOS hedge test.
- Quantitative Finance Stack Exchange - How to adjust butterfly 2s5s10s swaps trade for directionality? (Q&A, 2018, edited 2021): in-sample vs out-of-sample comparison of fly weighting methods, regime-dependent PCs.
- Cotton - Filtering bond and credit default swap markets (NYU Tandon seminar slides, 27 Apr 2016): evaluation-target overfitting illusion.
- Bailey, Borwein, Lopez de Prado, Zhu - Pseudo-mathematics and financial charlatanism (Notices of the AMS, 2014) (external): minimum backtest length and the overfitting argument.
- Bailey, Borwein, Lopez de Prado, Zhu - The probability of backtest overfitting (Journal of Computational Finance, 2017) (external): CSCV and PBO.
- Bailey, Lopez de Prado - The deflated Sharpe ratio (Journal of Portfolio Management, 2014) (external): DSR derivation.
