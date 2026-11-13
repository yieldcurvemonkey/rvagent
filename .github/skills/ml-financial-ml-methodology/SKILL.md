---
name: ml-financial-ml-methodology
description: "Financial-ML data methodology for G10 rates RV models: event sampling (CUSUM filter), triple-barrier and meta-labels on bp yield/spread/fly/basis series including carry, sample weights for overlapping labels (concurrency, average uniqueness, return attribution, time decay, sequential bootstrap, class weights), fractionally differentiated (FFD, min-d ADF) features that are stationary but keep memory, point-in-time feature hygiene, feature importance (MDI, MDA/permutation, SFI, PCA-orthogonal), scoring (neg log loss, F1) and leakage control (purging, embargo, quarantine, truncation test, wrong-way CV). Use when building or auditing a classifier or ML signal on UST, Bund, gilt, JGB, swaps, swap spreads, curve flies or futures; when asked about labels, triple barrier, meta-labeling, primary vs secondary model, bet size from probability, overlapping returns, sample uniqueness, fracdiff, look-ahead bias, data leakage, random forest overfitting, class imbalance, or why an ML backtest looks too good."
---

# Financial ML methodology: labels, weights, features, leakage

ML on rates RV fails less often in the model than in the data pipeline around it. Common failures are labels that
ignore the path and the carry, overlapping outcomes treated as IID, non-stationary levels fed in raw or
over-differenced into noise, and features or scalers that see the future. This skill turns a bp-quoted package
series (a yield, spread, fly, basis or ASW) and a feature set into labelled, weighted, leakage-free training data.
It also covers how to judge which features matter. The model families are in
[ml-models-for-rates](../ml-models-for-rates/SKILL.md), and CV, CPCV, DSR and PBO are in
[bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).

## When to use
- "Label this fly / swap-spread / basis series for a classifier", "triple barrier", "meta-label my z-score signal".
- An ML or rule-plus-ML filter on an RV signal: decide *whether* to take a primary signal and *how big* (meta-labeling).
- Overlapping horizons (e.g. 20-day outcomes sampled daily), random forest OOB accuracy suspiciously high.
- Need stationary features from yield/spread *levels* without throwing away the level (fracdiff, min d).
- "Which features matter?", "is this feature importance real?", "why does CV look great but live fail?" (leakage audit).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Level `x_t` of the traded package, bp | built from `curve_par`, `bond_quotes`, `fut_quotes`, `swap_spreads`, `basis_swaps` (`_pct` columns × 100) | daily, one `snap`, ≥ 5y (≥ 1,250 obs) | Weights frozen as of each date (no today's PCA weights on history) |
| Daily carry + roll-down of the package, bp/day for side +1 (= −1 × the receiver's carry on an outright) | from [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md) | daily | Without it labels flatter the negative-carry side and penalise the positive-carry side |
| Primary-model side, fair value, z-score | `signals` (`unit` z or bp) | per decision date | Required for meta-labels |
| Features | `curve_par`, `vol_surface`, `repo_rates`, `positioning`, `macro_series` (by `pub_ts_utc`), `cb_meetings`, `events_probs` | point-in-time | Indexed by when the value was *known*, not the period it describes |
| Bid/offer of the package, bp | `curve_par` bid/ask (pct × 100) or desk estimate | current | Sets the minimum barrier width |

Output probabilities go back to `signals` with `unit = prob`. Schemas:
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If an input is missing, ask for it or hand off
to the `rv-data-engineer` agent. Never invent values.

## Method

### 0. Conventions (state them in every output)
- `x_t` is in bp. **No log transform**, because EUR, JPY, CHF and SEK yields have been negative. Bar change is `Δx_t = x_t − x_{t−1}`.
- `side = +1` means the position earns when `x` rises and `−1` when it falls. Package P&L per unit DV01 is
  `pnl_bp(t0,t) = side·(x_t − x_t0) + side·Σ carry_bp`. Curve and fly signs follow the house convention
  (2s10s = 10y − 2y; fly = 2·5y − 2y − 10y, positive = belly cheap). Receiving the belly of a fly that is
  too high is therefore `side = −1`. On an outright yield or swap rate, `side = −1` is receive / long bond
  (DV01 > 0), and `side = +1` is pay / short.
- One snap per series. Asian closes (JGB, ACGB, NZGB) print before London and NY. A feature from a later-closing market
  is lagged one day for an earlier-closing target. Lag 1 day as the rule and 2 days across time zones
  (Willer & Saunders, Trading Global Macro Markets, 2026).

### 1. Sample events, not every day
- Daily overlapping sampling makes neighbouring labels near-duplicates. Sample on **events** instead.
- **Symmetric CUSUM filter** on `Δx`: `S⁺_t = max(0, S⁺_{t−1} + Δx_t)` and `S⁻_t = min(0, S⁻_{t−1} + Δx_t)`.
  Emit an event and reset that side when `S⁺ > h` or `S⁻ < −h`.
  - Default `h = 1–2 × σ_daily`. AFML Ex. 3.1 uses 1× the daily std and Ex. 5.6 uses 2× (López de Prado, AFML, 2018).
  - A full run of size `h` is needed, so a series hovering at a threshold does not re-trigger, unlike Bollinger bands.
- **Primary-model events** are the natural choice for RV: a z-score crosses ±2, a PCA residual exceeds its band, an
  auction concession window opens, or a CB meeting falls inside the horizon. AFML's own example of an event is "a
  significant departure in a spread away from its equilibrium level".
- For listed futures with trade data, volume or dollar bars beat time bars. Size bond bars dynamically, e.g. to debt
  outstanding. OTC swaps have daily snaps only, so CUSUM or primary events on daily data are the practical choice.

### 2. Volatility unit for barriers
- `σ_daily` = EWM std of `Δx_bp` with span 100, the AFML Snippet 3.1 default. That is a half-life of about 35
  business days: slow enough to be stable, fast enough to follow vol regimes.
- Barrier unit `trgt = σ_daily · √H`, where `H` is the vertical barrier in days. The √H scaling is this skill's
  convention for multi-day RV horizons. AFML scales by daily vol with a 1-day vertical barrier.
- `min_trgt` drops events whose `trgt` is ≤ 2 × the package round-trip bid/offer in bp. Otherwise noise inside the
  spread decides the labels. In low-vol regimes such as JPY under YCC this drops many events, which is correct.

### 3. Triple-barrier labels
For event `t0` with side `s`, walk the path `pnl_bp(t0, t)` for `t = t0+1 … t0+H`:
- **upper** (profit-take) at `+pt·trgt`, **lower** (stop) at `−sl·trgt`, **vertical** at `t0 + H` bars.
- `t1` is the first touch. The label is `+1` on the upper barrier and `−1` on the lower one. On the vertical barrier
  it is `sign(pnl)`, which AFML prefers, or `0`. Test both.
- Drop events whose vertical barrier lies beyond the data and that touched nothing. Their outcome is unknown.
- `[pt, sl, H]` configurations (1 = active):
  - `[1,1,1]` is the standard.
  - `[0,1,1]` holds to the horizon unless stopped.
  - `[1,1,0]` is "somewhat unrealistic".
  - `[0,0,1]` is the fixed-horizon label AFML criticises. It ignores the stop you would have hit:
    "It is simply unrealistic to build a strategy that profits from positions that would have been stopped-out".
  - `[1,0,1]` ignores interim losses.
  - `[1,0,0]` can lock in a loser for years.
  - `[0,1,0]` and `[0,0,0]` are illogical.
- **Side unknown**: `pt = sl`, because the profit-take and the stop cannot be told apart.
- **RV mapping** (this skill's defaults, all from the primary model):
  - `pt` = the gap to fair value `|x_t0 − FV|` expressed in `trgt` units, floored at 1.
  - `sl` = 1.5–2 × `trgt`.
  - `H` = 1–2 × the OU half-life from [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md).
- **Don't tune `pt`/`sl` on history.** AFML Ch.13 simulated discrete-OU exits:
  - With zero equilibrium and a 5-day half-life, the best rule was a *small* profit-take with a *wide* stop (non-annualised SR ≈ 3.2).
  - The worst rule was a tight stop with a wide profit-take. Symmetric barriers were near neutral.
  - From half-lives of 25 to 100 the surface became progressively flatter, with no recognisable optimum as the
    process nears a random walk. A rule calibrated there is overfit.
  - An RV entry away from fair value is AFML's *positive-equilibrium* case (forecast 5σ away). At a 5-day half-life
    the best profit-take sat near the gap (≈ 6) with stops of 4–10 and SR ≈ 12. Max SR fell to 2.7 at a half-life of 25
    and 0.32 at 100. This supports `pt` ≈ the gap to FV. Simulate it from the fitted OU instead of back-fitting.

### 4. Meta-labeling: rules pick the side, ML picks the bet
1. The **primary model** is a transparent RV rule tuned for high **recall**, even at low precision. Examples are a
   z-score, a PCA residual, a macro fair value, or a list of discretionary ideas.
2. Label only the primary's events with `side` passed in: `label = 1` if `pnl_bp(t0, t1) > 0`, else `0`.
3. The **secondary model** learns `P(label = 1 | features)` and so filters false positives. Score it with **F1**,
   not accuracy.
4. Size from the probability with `z = (p − 0.5)/√(p(1−p))` and `m = 2Φ(z) − 1`. Average the sizes of all bets
   still active, and discretise `m` in steps of `d = 0.2` to stop jitter (AFML Ch.10). The position is `side · m`.
   The JPM desk used `S = 2P − 1` (Kelly for symmetric payoffs). Hand-off:
   [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).
5. Why it is safer:
   - The ML never chooses the side, which limits overfitting.
   - Long and short layers can be trained separately, because rally and sell-off drivers differ.
   - "achieving high accuracy on small bets and low accuracy on large bets will ruin you" (AFML Ch.3).

### 5. Sample weights for overlapping labels
| Quantity | Formula | Use |
|---|---|---|
| Concurrency | `c_t = Σ_i 1_{t,i}`, with `1_{t,i} = 1` if label `i` spans bar change `t` (`t0_i < t ≤ t1_i`) | crowding of labels |
| Average uniqueness | `ū_i = mean over i's life of 1/c_t`, in (0, 1] | **effective sample size ≈ Σ ū_i** |
| Attribution weight | `w̃_i = \|Σ_{t∈(t0_i,t1_i]} Δx_t / c_t\|` (bp incl. carry), `w_i = w̃_i·I/Σ w̃` | weights big unique moves, sums to I |
| Time decay | `d = max(0, a + b·x)` with `x` = cumulative uniqueness, newest = 1, oldest ≈ `c` | `c=1` none, `c=0` linear to 0, `c<0` drops the oldest `\|c\|` share |
| Class weights | `balanced` (or `balanced_subsample` in bagging) | rare but important outcomes |

- When mean `ū ≪ 1`, bootstrap in-bag samples look like out-of-bag samples. The forest becomes copies of one overfit
  tree and **OOB accuracy is grossly inflated**. Fixes, in order:
  1. Bag trees with `max_samples = mean ū`.
  2. Use the **sequential bootstrap**, which draws `j` with probability ∝ `ū_j` given the draws so far. In AFML's
     Monte Carlo it lifted median uniqueness from 0.6 to 0.7.
  3. Set `min_weight_fraction_leaf ≈ 5%` and a low `max_features`.
- Attribution weights fail with a neutral class (AFML 4.6), so drop neutral labels instead. A neutral outcome is just
  a low-confidence ±1.
- JPM's move-size weights for 5-day 10y moves (`σ` = std of 5-day changes):
  - Gaussian: `w = 1 − (1−b)·exp(−dy²/(sσ)²)`.
  - Piecewise linear: `w = min(1, |dy/(2sσ)| + b)`.
  - Fitted `b = 0`, `s = 1` (roughly 10bp). They helped in CV but **generalised worse in quarantine** (see the worked examples).
  - Treat any weighting scheme as a hyperparameter and validate it out of sample.

### 6. Stationary features that keep memory (FFD)
- Levels have memory but are non-stationary (`d = 0`). Changes are stationary but memoryless (`d = 1`). Fractional
  differencing finds the minimum `d` in between.
- Weights: `ω_0 = 1`, `ω_k = −ω_{k−1}(d − k + 1)/k`. Then `X̃_t = Σ_{k=0..l*} ω_k X_{t−k}`, truncating once `|ω_k| < τ`.
  This is the **fixed-width window** (FFD). The expanding window drifts, so do not use it.
- Recipe:
  1. Compute FFD(d) for `d = 0, 0.1, …, 1`.
  2. Run ADF on each (constant, maxlag 1).
  3. `d*` is the smallest `d` with p < 5%. The 95% critical value is about −2.86.
  4. Use FFD(d*) as the feature, and report `d*`, `τ`, the window and the correlation with the level.
- **`τ` matters as much as `d`**, because a truncated window keeps `Σω` of the level. Computed with the bundled script:

  | τ | window at d = 0.2 / 0.4 / 0.6 (lags) | level loading Σω at d = 0.2 / 0.4 / 0.6 |
  |---|---|---|
  | 1e-2 (AFML's daily setting) | 10 / 10 / 8 | 0.54 / 0.26 / 0.13 |
  | 1e-3 | 72 / 54 / 33 | 0.36 / 0.14 / 0.06 |
  | 1e-4 | 496 / 281 / 139 | 0.25 / 0.07 / 0.02 |

  Default `τ = 1e-2` for comparability with AFML. Re-check `d*` at `1e-3` when you have ≥ 2,500 daily observations.
  A `d*` that moves a lot with `τ` is fragile.
- Apply FFD to yield levels, spread and swap-spread levels, breakevens and vol levels. Series that are already
  stationary, such as most z-scores and many flies, have `d* = 0` and need none. FFD replaces "the cointegration
  trick" for ML features. For trade construction see [quant-cointegration](../quant-cointegration/SKILL.md).

### 7. Point-in-time feature hygiene
- Rule: "never use data in a backtest on a certain date that we are not able to use in production on that day"
  (Paleologo, Elements of Quantitative Investing, 2025).
  - Macro data goes in by `pub_ts_utc` with first-release vintages.
  - CFTC data goes in by its release date, not its as-of date.
  - Curve-fit or PCA weights are re-estimated with data up to `t` only.
- Every scaler is fit on the training fold only. This covers z-score means and stds, winsor limits, PCA loadings and
  percentile thresholds. Full-sample z-scores and percentiles are look-ahead
  (Palomar, Portfolio Optimization, 2025; Willer & Saunders, 2026).
- Make inputs ratio-like or relative to their own history, never mix units, and limit the number of data categories
  (Tulchinsky et al., Finding Alphas, 2015).
- For regression-based features (Kyle/Amihud λ, rolling betas), feed the **t-value**, not the coefficient (AFML 19.4).
- JPM's kitchen-sink design:
  - About 1,250 daily features.
  - Transforms: 1w/1m/3m changes and 3m/6m/1y/2y trailing z-scores.
  - Binary date flags for FOMC, payrolls and month-end. These are not normalised.
  - Continuous variables are de-trended and normalised, then reduced by PCA.
  - 10 PCs explain about half the variance on 2008–16, and about 100 PCs are needed for about 90%. The number of PCs
    is a hyperparameter, and more PCs can hurt.
  - The authors' curated alternative: level, slope and curvature, or the residual of VIX vs 1Mx10Y vol
    (J.P. Morgan, Do androids dream of electric bonds?, Nov 2017).
- The training sample must span regimes. Fits made on ZLB years break in hiking years. Add regime dummies or
  interactions, or label data from both regimes (J.P. Morgan, Welcome to the machine, Apr 2023).
- Structural-break statistics (SADF, CSW CUSUM) make good "switch off mean reversion" features:
  [quant-regime-detection](../quant-regime-detection/SKILL.md).

### 8. Leakage controls (run all of them)
1. **Purge.** Drop a training label `i` if `[t0_i, t1_i]` overlaps any test label.
2. **Embargo.** Also drop training labels that start within `h` after the last test label's `t1`. Use `h ≥` the
   label horizon, and `≈ 0.01·T` often suffices. JPM instead dropped the first *n* test days, *n* = the holding period.
   - Leakage symptom: CV score keeps improving as the number of folds k → T. With proper purging it plateaus.
3. **Do every supervised step inside the folds.** That covers screening, feature selection and hyperparameters. In
   ESL's simulation, selecting the top 100 of 5,000 noise predictors on all data and then cross-validating gave a
   **3% CV error against a true 50%** (Hastie et al., ESL, 2009). The RV version of this error: screen 500 flies on
   the full sample, then CV only the winners. Only unsupervised screening (e.g. highest variance) may precede CV.
4. **Quarantine** a final block, untouched until the model is frozen. JPM held back all of 2017.
5. **Truncation test.** Rerun the pipeline with the last N = 60 days removed. Positions on the overlapping dates must
   be identical (Chan, Quantitative Trading, 2009).
6. **Future-perturbation test.** Scramble every value dated after `t` and check that features and labels-in-training at `t` do not change.
7. **Log every trial**, including each hyperparameter set. Trial count and variance feed DSR/PBO in
   [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).

### 9. Fitting and scoring defaults
- **Scorer.** Use sample-weighted **neg log loss** when the model sets side and size. Accuracy treats a confident
  miss like a timid one. Use **F1** for meta-labels: on mostly-0 labels an all-zero model scores high accuracy with
  zero recall. scikit-learn's `cross_val_score` passed sample weights to fit but not to the scorer in the versions AFML
  used, and newer versions do so only with metadata routing switched on. Score with an explicit loop that passes
  `sample_weight` to both fit and score.
- **Trees and forests.**
  - Settings: shallow or pruned, `min_weight_fraction_leaf` ≈ 5%, `class_weight='balanced_subsample'`,
    `n_estimators` ≈ 1,000 and `max_samples = mean ū`.
  - Fitting on PCA-rotated features speeds up fitting and reduces overfitting.
  - Never report OOB accuracy as performance.
- **Hyperparameter search.** Use randomised search over purged CV, with log-uniform draws for scale parameters
  (e.g. SVM `C` and `γ` on [1e-2, 1e2]).
- **JPM evidence on 10y UST direction.**
  - Random forest won.
  - KNN generalised better at k ≈ 80 than at 10.
  - ANNs were erratic across neighbouring hyperparameters and seeds.
  - Class weighting dominated behaviour: balanced forests went short 30–40% of the time (40–45% in TradeRunner),
    non-balanced ones 15–20% (TradeRunner).
    Non-balanced out-of-sample hit rate saturated near 57%, while Sharpe kept rising through better sizing.
  - Details: [references/rates-ml-case-studies.md](references/rates-ml-case-studies.md).

### 10. Feature importance: the research tool (not the backtest)
- **MDI** (in-sample, trees only):
  - Set `max_features = 1` so masked features get a chance.
  - Replace zero importances with NaN before averaging.
  - Importances sum to 1, so the noise line is `1/N`.
  - Substitutes dilute each other: two copies each get half.
- **MDA** (out-of-sample, any model and scorer, purged CV):
  - Importance is the score loss when one column is permuted: `(s0 − s1)/(1 − s1)` for accuracy and
    `(s0 − s1)/(−s1)` for log loss.
  - Negative means the feature hurts.
  - Two identical critical features can *both* look useless.
- **SFI**: the CV score of each feature alone. It has no substitution effects but misses joint effects.
- Run MDI and MDA on **PCA-orthogonalised** features as well, keeping the PCs that explain 95%. That removes linear
  substitution, so rankings that agree across the raw and PC versions are credible.
- Validate the importance pipeline on synthetic data first. AFML's harness: 40 features (10 informative, 10 linear
  combinations of them, 20 noise) and 10,000 observations. MDI and MDA should place every informative feature above
  the noise.
- "Backtesting is not a research tool. Feature importance is." Decide what to keep from importance. Backtest once,
  at the end, and only to discard.

## Worked examples

**Sequential bootstrap (AFML 4.5.3, reproduced by the script self-test).** The labels use returns `r_{0,3}`,
`r_{2,4}` and `r_{4,6}`. Concurrency over bars 1..6 is `[1,1,2,1,1,1]` and average uniqueness is `[5/6, 3/4, 1]`.
After label 2 is drawn, the next-draw probabilities are `{5/14, 3/14, 6/14}`. The label already drawn is least likely
and the non-overlapping one most likely (López de Prado, AFML, 2018).

**Fracdiff on rates futures (AFML Table 5.1; ADF on FFD(d), 95% critical value −2.8623).** These are the smallest
passing `d` on the 0.1 grid. Contract names were decoded from the book's generic codes, so treat them as approximate.

| Contract | ADF at d=0 | d* |
|---|---|---|
| 3m Euribor futures | −0.20 | 0.6 |
| US 5y note futures | −0.73 | 0.6 |
| Long gilt futures | +0.23 | 0.6 |
| 3m short-sterling futures | −0.08 | 0.6 |
| 10y JGB futures | −0.21 | 0.5 |
| Euro-BTP futures | −1.74 | 0.3 |
| ASX 90-day bank bill futures | −2.06 | 0.2 |

The book says every contract it tested is stationary with d < 0.6, and most with d < 0.3. Five of these seven rates
contracts sit at the top of that range, with d* of 0.5–0.6 on the grid. Never assume a small d for rates.
For comparison, E-mini S&P passes at d ≈ 0.35 with correlation 0.995 to the level, against 0.03 for returns.

**Meta-labeling a 2s5s10s fly (illustrative numbers, not market data).**
1. Setup: the fly is 8bp above its 60-day mean (z = +2.1). The primary rule says receive the belly, `side = −1`.
   `σ_daily = 1.1bp` and `H = 20` give `trgt = 1.1·√20 = 4.9bp`.
2. Barriers: `pt` = gap 8bp = 1.6·trgt; `sl` = 1.5·trgt = 7.4bp. Belly carry for `side −1` is −0.1bp/day, so 20 days
   cost 2bp. That carry is why it belongs in the label.
3. Outcomes:
   - The fly falls 8.5bp by day 12: `pnl = 8.5 − 1.2 = 7.3bp`, still short of 8bp. A fall of 9.5bp by day 12 gives
     8.3bp: profit-take, label 1.
   - The fly rises 7bp by day 5: `pnl = −7 − 0.5 = −7.5bp < −7.4bp`: stop, label 0.
   - No touch, and the fly is 2bp lower on day 20: `pnl = 2 − 2 = 0`, vertical barrier, label 0. Carry turned a
     price win into a non-win.
4. The secondary model then learns which fly signals end as 1s.

**JPM random forest on 10y UST (1-week hold).**
- CV ran in expanding windows from 2010 to end-2016, with the first *n* test days purged. 2017 was quarantined.
- The balanced RF scored Sharpe 1.35 in quarantine against 0.38 for always-long.
- Permutation thresholds (3,000 shuffles of the daily sizing decisions at a fixed sell fraction):
  - Median Sharpe ≈ 0.6 all-long, 0.0 at 50/50 and −0.6 all-short.
  - Max ≈ 0.95 near a 20% sell fraction.
- Only RF and RBF-SVM beat the 95th and 99th percentiles.
- So a Sharpe of 0.75 at 50% sells is far more impressive than 0.75 at 80% long
  (J.P. Morgan, Do androids dream of electric bonds?, Nov 2017).

**Move-size sample weights that did not generalise.** With `b = 0` and `s = 1` the CV profile became symmetric, making
money in both rallies and sell-offs. CV residual Sharpe was > 0.8 with a sell fraction > 50%, though outright Sharpe
fell about 10% to about 1.07. In quarantine, Sharpe was about 0.2 *lower* than the best standard GBM and residual
Sharpe was much more negative (J.P. Morgan, #SquadGoals, Sep 2018).

## Signals & interpretation
- Meta-probability `p > 0.5`: take the primary trade, sized by `m = 2Φ(z) − 1`. `p ≤ 0.5`: pass. Track the realised
  hit rate by `p` bucket. JPM found that conviction tracked the realised hit rate, so the model was well calibrated.
- Mean `ū < 0.5`: overlap is material. Use `max_samples = mean ū` or the sequential bootstrap, and quote
  `N_eff = Σ ū_i` next to any t-stat.
- Any label class below 5% of events: drop it, recursively, until 2 classes remain (AFML Snippet 3.8). Otherwise
  re-define the barriers.
- `d* ≥ 0.7`, or `d*` jumps between `τ = 1e-2` and `1e-3`: the level carries little stable memory. Use changes or a
  cointegration residual.
- MDA importance ≤ 0, or below the noise features: drop the feature. MDI near `1/N`: indistinguishable from noise.
- CV improves steadily as k → T, OOB is much higher than purged-CV accuracy, or in-sample accuracy is near 100%:
  leakage or memorisation. Stop and audit before reading any result.
- A model that only beats always-long, or only beats zero, has not shown skill. Require a positive **residual
  Sharpe** over the permutation 95th percentile in quarantine, and over the MC max in CV.

## Pitfalls
- **Fixed-horizon labels with a constant bp threshold.** A 5bp threshold means different things in a 0.5bp/day market
  (JPY under YCC) and a 6bp/day one (2022 UST). Scale by `σ_daily`.
- **Ignoring carry** in path P&L. Labels for negative-carry sides (e.g. paying fixed on a steep curve) are biased
  towards wins, and positive-carry sides towards losses.
- **Today's benchmarks back-filled into history.** Building a package from today's on-the-run bonds or CTDs gives
  history to instruments that were not benchmarks then, a survivorship error. Map benchmarks point-in-time
  (Paleologo, 2025).
- **Instrument-split "out of sample".** Training on one fly and testing on a correlated fly over the same dates is not
  out of sample. Split by time (Tulchinsky et al., Finding Alphas, 2015, Ch.10).
- **Log returns on negative yields**, or % returns on a spread near zero, give garbage. Stay in bp per DV01.
- **Historical PCA or fly weights estimated on the full sample.** The weights leak future covariance into every label.
- **Leaving scaler, PCA or feature screening outside the CV loop.** This is ESL's 3%-vs-50% trap.
- **Shuffled k-fold or OOB on overlapping labels.** These are inflated. Use purged, embargoed, contiguous folds.
- **A hyperparameter loop run against the quarantine set.** It is no longer out of sample. JPM: "cherry-picking these
  predictors and calling it a day strikes us as highly irresponsible." Prefer hyperparameters that sit inside a
  cluster of similar results, not lone peaks.
- **Time-zone misalignment.** A US-close feature used for a same-day JGB target is look-ahead.
- **Revised macro data.** Use first-release vintages by publication time.
- **Small effective samples.** Ten years of daily data with a 20-day horizon is roughly 125 independent outcomes.
  Fat tails mean a few days drive Sharpe, so benchmark against simple carry strategies, not zero.
- **Text-derived labels** (CB hawk/dove scores): sentence-level calls are noisy. JPM's 5-class model was 48% accurate,
  against 80% for hawk vs dove. Average over documents and train on both regimes
  ([macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md)).

## Output
1. **Label table**, one row per event: `t0, t1, side, trgt_bp, pt, sl, H, barrier (pt/sl/vert), ret_bp (incl. carry),
   label, avg_uniqueness, weight`. Add a summary of label shares, mean `ū`, `N_eff` and the event count per year.
2. **Feature manifest**, one row per feature: source table, availability lag (days), transform (FFD `d*`, `τ`,
   window, corr with level, z-window), and whether it is fit-in-fold.
3. **Leakage checklist** with pass/fail: purge, embargo `h`, in-fold screening, quarantine dates, truncation test,
   future-perturbation test, and trial count.
4. **Importance report**: MDI, MDA and SFI (mean ± std/√n) on raw and PCA features, with the noise line `1/N`.
5. **Validation summary**: purged-CV neg log loss or F1, permutation residual Sharpe vs the 95th percentile and the
   MC max, and quarantine result.
6. Hand-offs:
   - Probabilities go to `signals` (`unit = prob`) for [rv-composite-scoring](../rv-composite-scoring/SKILL.md).
   - Sizing goes to [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).
   - Final validation goes to [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).

## Scripts
- [`scripts/labeling.py`](scripts/labeling.py) provides:
  - CUSUM events
  - triple-barrier and meta labels on bp series with carry and side
  - indicator matrix, average uniqueness, attribution weights, time decay and the sequential bootstrap
  - purged train mask
  - FFD weights, fracdiff and the min-d ADF table (statsmodels optional)
- CLI: `python scripts/labeling.py label --input pkg.csv --col level_bp --side-col side --carry-col carry_bp --horizon 20`
  and `python scripts/labeling.py fracdiff --input pkg.csv --col level_bp`.
- `--selftest` checks analytic FFD weights (d=1 gives first differences), deterministic barrier paths, carry sign, the
  AFML 5/14-3/14-6/14 sequential-bootstrap example, attribution and time-decay values, the purge mask, and min-d on
  white noise vs a random walk.

## Related skills
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): purged k-fold, CPCV, deflated Sharpe, PBO and trial accounting
- [ml-models-for-rates](../ml-models-for-rates/SKILL.md): model families (regularised regression, trees, ensembles, NNs) fitted on these labels
- [bt-backtest-design](../bt-backtest-design/SKILL.md): signal → position → P&L with carry and point-in-time data
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life for `H`, and OU exit thresholds
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): primary-model signals for meta-labeling
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA features and residuals, with weights re-estimated point-in-time
- [curve-butterflies](../curve-butterflies/SKILL.md): building the fly package series that gets labelled
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll in bp/day for path P&L
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): bet size from probability, Kelly
- [quant-cointegration](../quant-cointegration/SKILL.md): the alternative to fracdiff for spread stationarity
- [quant-regime-detection](../quant-regime-detection/SKILL.md): structural-break and regime features
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC, horizon and decay of the resulting signal
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): snaps, holidays, stale prints
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): labelling text-derived features
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): where meta-probabilities enter the ranking

## References
- Marcos López de Prado - Advances in Financial Machine Learning (John Wiley & Sons, 2018):
  - Ch.2–5: CUSUM, triple barrier, meta-labeling, uniqueness and sequential bootstrap, FFD and Table 5.1.
  - Ch.6: bagging under overlap, `max_samples`, random-forest settings.
  - Ch.7–10: purging and embargo, MDI/MDA/SFI, scoring, bet sizing.
  - Ch.13: OU exit heat-maps.
  - Ch.19: t-value features.
- J.P. Morgan US Fixed Income Strategy - M. Salem, J. Younger, Z. Zhao et al. - "Do androids dream of electric bonds? Machine learning in interest rate markets" (22 Nov 2017): rates ML pipeline, purged walk-forward, quarantine, permutation residual Sharpe, class weighting, feature PCA.
- J.P. Morgan North America Fixed Income Strategy - M. Salem, J. Younger, J. Huang - "TradeRunner: Ensemble learning-driven systematic trading in interest rate markets" (16 Aug 2018): RF vs GBM across 2s/5s/10s/30s, embargo, sell fractions, costs.
- J.P. Morgan North America Fixed Income Strategy - M. Salem, J. Younger, J. Huang - "#SquadGoals: Stacking and voting with machine learning classifiers" (21 Sep 2018): move-size sample weights and their out-of-sample failure, stacking.
- J.P. Morgan Global Economic Research - J. Lupton, D. Aitas, D. Weitzenfeld - "Welcome to the machine: NLP of central bank speak" (26 Apr 2023): ordinal labels, active learning, regime-spanning training data, ZLB dummies.
- T. Hastie, R. Tibshirani, J. Friedman - The Elements of Statistical Learning (2nd ed., Springer, 2009): the wrong and right way to cross-validate (Sec 7.10.2).
- G. A. Paleologo - The Elements of Quantitative Investing (John Wiley & Sons, 2025): point-in-time leakage and survivorship rules, k-fold buffers, parameter plateaus.
- I. Tulchinsky et al. - Finding Alphas: A Quantitative Approach to Building Trading Strategies (John Wiley & Sons, 2015): trial logging, ratio-like inputs, unit discipline, data validation.
- E. P. Chan - Quantitative Trading (John Wiley & Sons, 2009): truncation test for look-ahead bias.
- D. Willer, A. Saunders - Trading Global Macro Markets (John Wiley & Sons, 2026): lag discipline across time zones, full-sample percentile look-ahead.
- D. P. Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): full-sample preprocessing as look-ahead (seven sins).
- R. S. Tsay - Analysis of Financial Time Series (3rd ed., John Wiley & Sons, 2010): long-memory fractional differencing and ACF decay.
- J. R. M. Hosking - "Fractional differencing", Biometrika (1981) (external): the fractional difference operator.
- L. Breiman - "Random Forests", Machine Learning (2001) (external): bagging plus random feature subsets.
- C. Strobl, A.-L. Boulesteix, A. Zeileis, T. Hothorn - "Bias in random forest variable importance measures", BMC Bioinformatics (2007) (external): MDI bias.
- C. Guo, G. Pleiss, Y. Sun, K. Weinberger - "On Calibration of Modern Neural Networks", ICML (2017) (external): uncalibrated network probabilities, a caution for probability-based sizing.
