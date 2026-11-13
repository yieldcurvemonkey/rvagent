---
name: ml-models-for-rates
description: "Supervised and unsupervised ML for G10 rates RV: forecasting forward changes or direction of yields, spreads, flies, swap spreads, basis and vol with ridge, lasso, elastic net, PCR/PLS, random forest, boosted trees (GBM), bagging, stacking and soft voting, SVM, logistic and ordinal classifiers, small neural nets, k-means and hierarchical clustering, plus nearest-neighbour curve-shape analog search (shift-invariant distance, Leela correlation analog, regime KNN). Gives baselines, lambda and class-weight defaults, probability to size (Kelly 2P-1), walk-forward evaluation with embargo, permutation Sharpe threshold, IC, MDI/MDA/SFI importance, and a bundled walk-forward and analog tool. Use when asked: can ML predict this spread or fly, train a model, random forest, gradient boosting, LASSO, regularised regression, feature selection, find similar historical curve shapes, analog, nearest neighbour, KNN, cluster the regimes, turn a probability into a position size, or is this ML result overfit."
---

# ML models for rates RV

Rates series are short, autocorrelated, regime-bound and have a tiny signal-to-noise ratio. The model that wins is
usually the most regularised one that still beats a zero-change or AR baseline out of sample, and most "great"
backtests are overfit. This skill says which model family to try for which question, the defaults and why, how to
turn a prediction into a position size, how to decide whether the result is luck, and how to run a nearest-neighbour
search for historical curves that looked like today. Label construction, sample weights and fractional
differentiation live in [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md). Validation
statistics (CPCV, deflated Sharpe, PBO) are in [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).

## When to use
- "Can a model predict the 2s5s10s / swap spread / basis / vol?", "train a random forest / boosted trees on this".
- Many correlated candidate features: ridge vs lasso vs elastic net, which features survive, how to set lambda.
- Probability from a classifier (rally vs selloff, revert vs not) to a DV01 size.
- "Find historical periods when the curve looked like this", analog / nearest-neighbour / KNN / pattern matching.
- Clustering instruments (representative assets) or macro states (regime clusters).
- Review of someone else's ML result: leakage, trial count, permutation test, importance that cannot be trusted.

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Package level `x_t` in bp (yield, spread, fly, swap spread, basis) | built from `curve_par`, `swap_spreads`, `basis_swaps`, `bond_quotes` (`_pct` x 100 = bp) | daily, one `snap`, >= 5y (about 1,250 obs) | Weights frozen as of each date; never mix snaps |
| Candidate features | `curve_par`, `vol_surface`, `repo_rates`, `positioning`, `auctions`, `cb_meetings`, `events_probs`, `macro_series` | point-in-time | `macro_series` indexed by `pub_ts_utc` (release time), not by the reference period |
| Curve vector for analog search | `curve_par` tenors (e.g. 2y, 5y, 10y, 30y) or forward-grid points | daily, >= 10y for rich analogs | bp, one snap |
| Regime vector | `macro_series` z-scores (growth, inflation, financial conditions, vol/risk appetite) | monthly, >= 20y point-in-time | Revised series leak the future |
| Costs | bid/ask in `curve_par`, `bond_quotes`, `fut_quotes` | current | Net signal of costs before judging |
| Output | `signals` (`unit` bp or prob) | per decision date | A signal dated `t` is traded from `t+1` |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values.

## Method

### 0. Frame the problem before choosing a model
1. **Target.** Regression: `y_t = x_{t+h} - x_t` in bp (positive = package yield or spread widens). Duration direction:
   "rally" = yields fall = `y_t < 0` (receive-fixed / long duration profits). Classification label `1 = rally`.
   For mean-reversion packages, labels such as "reverts by k bp before stop" come from triple-barrier
   ([ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md)). For spreads and flies define the label
   against the package as written ("1 = package widens", positive size = long the package), not "rally". P&L per bp move `dx` of the
   package level: duration label (1 = rally) earns `-S x dx`; package label (1 = widens) earns `+S x dx`. Never mix the two.
   `y_t = x_{t+h} - x_t` assumes entry at the snap that produced the features. If the signal is only actionable the
   next day, use `y_t = x_{t+1+h} - x_{t+1}` (script `delay=1`) and lengthen the embargo to `h + 1`.
2. **Horizon and overlap.** With daily rows and horizon `h`, rows `t` and `t+1` share `h-1` days of outcome, so
   `n_eff ~ n/h`. Every t-stat or CV score uses `n_eff`, and an embargo of at least `h` rows sits between train
   and test (JPM drops the first `h` test days; J.P. Morgan, Do androids dream of electric bonds?, 22 Nov 2017).
3. **Features: point-in-time, ratio-like, few categories.**
   - Row `t` uses data known at the snap of `t`. Fit scalers, PCA and any screening on the training rows only.
   - Make inputs comparable: a variable against its own history (1w / 1m / 3m changes, 63d / 252d z-scores) or
     against a same-category variable (spread-to-spread). Mixing units ("returns + delta volume") is invalid
     (Tulchinsky et al., Finding Alphas, 2015).
   - Limit data categories, not only column count: native frequencies differ (policy monthly, prices daily,
     auctions irregular) and mixing many raises overfitting risk (Tulchinsky et al., 2015).
   - Template for a rates model (J.P. Morgan, 22 Nov 2017): yield level, carry, specialness/repo, spread levels,
     curve level/slope/curvature, swap realised vol, swaption vol and skew, breakevens, positioning, cross-asset
     (credit, equity, FX, commodity), surprise indices, binary event flags (policy meeting, payrolls, month-end).
     Raw features of about 1,250 were reduced by a global PCA to 40 dimensions for tree ensembles
     (J.P. Morgan, TradeRunner, 16 Aug 2018). De-trend and normalise before PCA, not binary flags.
   - Few parameters: roughly 252 data points per free parameter and five or fewer parameters per model
     (Chan, Quantitative Trading, 2009). With daily bars on 5-10y that means a handful of features, not hundreds.
4. **Baselines are mandatory.** Report every model against (i) zero-change / persistence, (ii) carry-only,
   (iii) AR(L) on lagged changes, (iv) an all-long or all-short benchmark for direction models (kurtosis is high, so
   the benchmark is a carry strategy, not zero; J.P. Morgan, 22 Nov 2017). Out-of-sample
   `R2_oos = 1 - sum(y - yhat)^2 / sum(y^2)` against the zero-change forecast (house convention).
   Example (equity volume series, but the lesson is general): persistence test R2 0.18, AR(5) 0.41, an RNN with 205
   parameters 0.42, a feedforward net 0.42. The nonlinear nets bought nothing over AR (James et al., ISLP, 2023).

### 1. Choose the family
| Question | First try | Why / defaults | Avoid |
|---|---|---|---|
| Few (<= 10) correlated, roughly linear predictors | **Ridge** | Smooth shrinkage; handles collinearity; no selection instability | Unregularised OLS on collinear yields |
| Many candidates, want a short list | **Elastic net**, then stability selection | Selects like lasso, keeps correlated groups like ridge | Single lasso path read as "the" model |
| Smooth latent factor (level/slope/curve) drives y | **PCR** (PCA then OLS) or PLS | Acceptable when the latent factor is a mix of the regressors | Hard-truncated PCs as a default over ridge |
| Interactions, thresholds, regime effects | **Boosted trees** (shallow) or **random forest** | Capture nonlinearity; bagging cuts variance | Deep single trees, unbounded boosting |
| Direction + confidence for sizing | **RF / GBM classifier, balanced**, plus logistic | Probability -> `S = 2P - 1` | Accuracy as the tuning metric |
| 3-factor "call or not" style decisions | **Logistic** | A 3-factor logit matched a random forest (J.P. Morgan, Taiwanese demand for US fixed income, 10 Jan 2020) | Complex models on a tiny sample |
| Small sample, want precedent | **Analog / KNN** (section 7) | Transparent; no fit | k = 10 (too noisy; k about 80 beat 10 for direction) |
| Text from central banks | see [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md) | Transformer pipeline lives there | Few-shot chat prompting (far worse and costly) |
| Neural nets | only with large, stable, high signal-to-noise data | Erratic across seeds and neighbouring hyper-parameters in the rates study | NN as a first model on daily rates |

### 2. Regularised linear models (the workhorse)
- **Ridge.** `b = argmin sum_i (y_i - b0 - x_i'b)^2 + lambda * sum_j b_j^2`; closed form on centred data
  `b = (X'X + lambda I)^-1 X'y` (Hastie, Tibshirani, Friedman, The Elements of Statistical Learning, 2009).
  Centre `X` and `y`, do not penalise the intercept, standardise predictors (ridge is not scale-equivariant) using
  train statistics only. Use QR/SVD or `solve`, not an explicit inverse.
- **Effective degrees of freedom:** `df(lambda) = sum_j d_j^2/(d_j^2 + lambda)` over the singular values `d_j` of
  centred `X`. It equals `p` at 0 and falls to 0. Use `df` as the complexity axis when comparing lambdas
  across windows. Example: `d = (10, 5, 1)`, `lambda = 25`: `0.80 + 0.50 + 0.04 = 1.34` of 3.
- **Choosing lambda.** Log-spaced grid (script: `c x n_train` with `c` in 0.01..10), chosen on a chronological
  validation block that sits after the fit rows and is separated by an `h`-row gap. Refit on all training rows.
  Never minimise the penalised error jointly over weights and lambda (returns lambda = 0). If the CV curve is flat,
  take the most regularised lambda within one standard error of the minimum (one-SE rule; Murphy, Machine Learning:
  A Probabilistic Perspective, 2012). Lambda is a fitted hyper-parameter: in a sparse-hedge study 1e-8, 1e-7 and 1e-6
  gave very different cardinality and tracking error (Palomar, Portfolio Optimization, 2025).
- **Lasso.** `argmin 1/2 sum (y - b0 - x'b)^2 + lambda * sum |b_j|`. No closed form; the whole path is cheap (LARS).
  CV-chosen lambda is prediction-optimal but keeps false positives; selection is unstable under small
  perturbations. Remedies: stability selection (bootstrap, keep variables chosen in a high share of fits; "bolasso"
  uses >= 90%) and a debiasing OLS refit on the selected support (Murphy, 2012). At most `n` variables are ever
  selected if `p > n`.
- **Elastic net.** Penalty `lambda * sum (alpha b_j^2 + (1 - alpha)|b_j|)`: groups of correlated regressors enter
  and shrink together. Default for correlated yield-curve features.
- **What each penalty does (orthonormal `X`, OLS coefficient `w`):** ridge `w/(1 + lambda)`; lasso
  `sign(w)(|w| - lambda)+` (for objective `1/2||y - Xb||^2`; some texts use `lambda/2`, check the parameterisation);
  best subset of size `M` keeps the `M` largest `|w|`. Example `w = (3.0, 1.2, 0.4)`, `lambda = 0.5`:
  ridge `(2.0, 0.8, 0.27)`, lasso `(2.5, 0.7, 0)`.
- **PCR / PLS.** PCR: standardise, `z_m = X v_m`, regress `y` on the first `M` scores; `M = p` is OLS. PLS picks
  directions maximising `Corr^2(y, Xa) Var(Xa)`; its variance term dominates, so it behaves like ridge. Ridge is
  usually preferred because it shrinks smoothly. Choose `M` by CV inside the loop, never by scree elbow.
- **Bayesian equivalents.** Ridge = zero-mean Gaussian prior with `lambda = sigma^2/tau^2`; lasso = Laplace prior;
  Cauchy/t priors regularise near-zero effects more and large ones less (Gelman et al., Bayesian Data Analysis,
  2014). See [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md).
- **Heteroskedasticity.** Rates changes are heteroskedastic: scale the row `x~ = x/||x||`, `y~ = y/||x||`
  (Burton, Dektor, Wheeler, Time Series Prediction of US Swap Rates, c.2008) or use WLS with `w_i = 1/sigma_i^2`
  (Shalizi, The Truth about Linear Regression, 2025). Use HAC (Newey-West) errors, since serially correlated
  residuals overstate significance.
- **Selection criteria** (for models within one family, same rows): `Cp = MSE + (2/n) sigma^2 (p + 1)`,
  `AIC = L - dim`, `BIC = L - (ln n / 2) dim`, `LOOCV = (1/n) sum ((y_i - yhat_i)/(1 - H_ii))^2`. LOOCV, Cp and
  AIC tend to pick models larger than the truth; BIC is consistent but predicts worse. Those shortcuts assume iid
  rows, so use them only for a quick scan and rely on walk-forward for the decision (Shalizi, 2025).

### 3. Trees, bagging, boosting
- **Error and bagging.** `E[(y - fhat)^2] = bias^2 + variance + noise`. Averaging `N` bagged learners with average
  pairwise correlation `rho` has variance `sigma^2 (rho + (1 - rho)/N)`: it helps only while `rho < 1`
  (Lopez de Prado, Advances in Financial Machine Learning, 2018). Bagging cuts variance, not bias, and cannot rescue
  a weak learner.
- **Random forest** for overlapping labels (AFML fixes): lower `max_features`; `min_weight_fraction_leaf` about
  0.05; `class_weight='balanced_subsample'`; `max_samples` = mean average uniqueness of labels; or bag
  `RF(n_estimators=1, bootstrap=False)`. OOB accuracy is inflated when samples overlap (about 2/3 of IID
  bootstrap draws are unique, far fewer for overlapping labels), so score with purged walk-forward, not OOB.
- **Gradient boosting.** Start from a stump predicting the modal class, fit successive trees to residuals, subsample
  rows and features. House defaults for daily rates: depth 2-3, learning rate 0.05, subsample 0.7, about 150
  trees (shallow weak learners because the signal is tiny). Finance prefers bagging over AdaBoost-style boosting
  because overfitting costs more than underfitting at low SNR (AFML, 2018), but shallow, subsampled GBM held its own
  in the rates studies.
- **Class weights are the dominant hyper-parameter.** Balanced weights make the model call selloffs as well as
  rallies, so it sells more often and is timid (modal conviction about 50%); unweighted models learn the secular
  rally, hold a long bias and fail in sustained selloffs (J.P. Morgan, TradeRunner, 16 Aug 2018). Class weights
  should sum to `J` or they act as a change of regulariser.
- **Red flags:** in-sample accuracy near 100% (memorisation); a "fluke" hyper-parameter cell with no similar
  neighbours; an ANN whose result changes with the seed. Prefer stable, explicable hyper-parameter trends
  (J.P. Morgan, 22 Nov 2017). Sample non-negative hyper-parameters (SVC `C`, RBF gamma) log-uniformly, density
  `1/(x ln(b/a))`; use randomised search for a fixed budget (AFML, 2018).

### 4. Classifier probability to position size
1. Use probabilities, not hard labels. Check calibration in 10 probability bins out of sample; forest and
   boosted-tree scores are not calibrated, and deep-net scores are poorly so.
2. Symmetric-payout Kelly: `S = 2P - 1` for `P = P(rally)` in `[0, 1]`, so `S in [-1, +1]`, positive = long
   duration (receive). Position DV01 = `S x` the risk budget from
   [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md). Conviction sizing
   "substantially" lifted Sharpe over fixed size, while a three-class buy/sell/hold only incrementally beat
   buy/sell (J.P. Morgan, 22 Nov 2017). Symmetric Kelly is ill-suited to skewed payoffs; for skew use the package's
   own payoff ratio `b` (average win / average loss): `f = P - (1 - P)/b`, then trade a fraction of it because `P`
   is estimated with error.
3. Score the model with **negative log-loss** (`L = -(1/N) sum_n sum_k y_nk ln p_nk`, sign-flipped so higher is
   better) or sample-weighted cross-entropy for confidence-sized strategies: accuracy treats a confident miss like a
   hesitant one. For rare positive labels (meta-labels) use F1, because an all-negative classifier has high
   accuracy and log-loss but zero recall (AFML, 2018).
4. Hit-rate-versus-conviction table: a model aware of alpha decay has hit rate below 50% only at low conviction
   (J.P. Morgan, Is bank convexity hedging lying in wait?, 31 May 2019).
5. Hit rate to IC: `IC = 2 x hit - 1` (hit = share of correct signs). IC 0.10 is about 55% right.

### 5. Stacking and soft voting
- **Stacking.** Train constituents ("solo" learners: GBM, RF, linear SVM, RBF SVM, logistic; each balanced and
  unbalanced) on the label, then an executive classifier on their probabilities (optionally plus a PCA-40 market
  feature set). Train the executive on in-sample constituent predictions and validate out of sample (the source's design; a
  safer variant feeds it purged out-of-fold constituent predictions, since in-sample probabilities are overconfident).
  It learns whom
  to trust, ignore or fade: a balanced GBM received negative weight in a logistic executive, i.e. used as a contrarian
  input (J.P. Morgan, #SquadGoals, 21 Sep 2018). Exclude KNN, single trees and simple ANNs from stacks (erratic).
- **Soft voting** averages the constituents' Kelly sizes. Example: 75% selloff probability gives `S = -0.5`; 85% rally
  gives `S = +0.7`; the vote is `+0.1` (J.P. Morgan, 21 Sep 2018). Correlated partners add nothing (GBM and RF are
  highly correlated); the less correlated the partner the better.

### 6. Feature importance (research tool, not backtest)
"Backtesting is not a research tool. Feature importance is." (AFML, 2018.) Run importance on purged, embargoed folds.
- **MDI** (in-sample, trees only): set `max_features = 1` to avoid masking; replace zero importances by NaN before
  averaging; importances sum to 1 and every feature gets some, even noise; substitutes split the credit.
- **MDA** (permutation, out of sample, any model): importance `= (s0 - s1)/(-s1)` for negative log-loss, or
  `(s0 - s1)/(1 - s1)` for accuracy, where `s0` is the score with intact data and `s1` with one feature shuffled;
  negative = detrimental. Two identical features can both look irrelevant.
- **SFI**: out-of-sample CV score of each feature alone. No substitution effects, but misses joint effects.
- **Substitution effects** (the ML version of multicollinearity): rotate to PCA components (keep the fewest
  explaining 95% of the variance after standardising) and run importance there.
- **Prove the tool first** on synthetic data with a known answer: 40 features (10 informative, 10 redundant, 20
  noise), 10,000 rows, bagged trees, purged 10-fold CV. If MDI/MDA/SFI do not recover the 10, do not trust them
  on real data.
- Collinearity diagnostics before any linear fit: `VIF_i = 1/(1 - R_i^2)` (flag > 5-10; the 10 rule is folklore),
  or eigenvalues of `Var[X]` near zero (example cutoff 1e-12) and inspect their eigenvectors. Pairwise correlations
  miss three-way collinearity.

### 7. Analog (nearest-neighbour) search
**What it answers:** "when did the curve (or macro state) last look like this, and what happened next?"
1. **Vector.** Curve analog: bp levels at 4-6 fixed tenors, or slope/fly features. Regime analog: z-scored macro
   variables (growth level and change, inflation level and change, financial conditions, risk appetite).
   For bp curves with very different tenor volatility, optionally divide each tenor by the standard deviation of its
   `h`-day changes.
2. **Distance.**
   - Regime vectors: Euclidean on z-scores.
   - Curve shape (parallel-shift invariant): `d(c1, c2) = min_k ||c1 - c2 - k||_2`. The optimal `k = mean(c1 - c2)`,
     so `d = ||demean(c1) - demean(c2)||`. Level is deliberately removed; add the level back as a separate feature
     if it matters. Stretch variant: `d = min_{k1,k2} ||c1 - k1 c2 - k2||` (J.H.M. Darbyshire, Coding Interest Rates,
     eq 6.1; described as anecdotal). Script clips `k1` to `[0.5, 2]` so a flat curve cannot match everything.
3. **Search rules (script defaults).** Candidates end at least `h` rows before the as-of date, so the forward
   outcome was already known then. Take `k = 20` analogs at least `max(10, h)` rows apart (one episode = one analog; without
   this, the neighbours are consecutive days and their forward windows overlap). Weight `1/(d + 0.05 x median d)`. Direction studies found larger
   `k` better (k about 80 beat 10; J.P. Morgan, 22 Nov 2017). Citi takes the 60 nearest months of regime vectors, similarity-weighted (Citi Research,
   Quantitative Framework for Regime Investing, 29 Oct 2021); the book says "five years (60 months) of data" is used
   (Willer and Saunders, Trading Global Macro Markets, 2026); the two are not reconciled. Citi's distance is Euclidean on
   the z-scored vector but its weighting formula is not stated, and the book states neither. Calibration: the regime-analog forecast scored IC 0.045 (levels), 0.055 (changes), 0.050 (both) and
   0.076 (plus risk-aversion variables, long-short IR 0.53) on 1979-2018 monthly data, i.e. IC of 0.05-0.08 is what a good
   macro analog model delivers (Citi Research, 29 Oct 2021).
4. **Forecast** = weighted mean of the analogs' forward changes per tenor. Always also report: dispersion, the share
   of analogs with the same sign, the number of distinct episodes, and the unconditional mean and Sharpe as the
   benchmark. Nearest months are usually the most recent (regime stickiness); a forecast built from one episode is
   an anecdote.
5. **Leela correlation analog** (Burton, Dektor, Wheeler, c.2008). `x~_t` = last `p` daily changes normalised to unit
   length; for history `i`, `rho_{i,t} = x~_t . x~_{t-i}` and `y~_i = d_{i+1}/||x_i||`;
   `signal_t = sum_i rho_{i,t} y~_i`, trade `sgn(signal_t)`. Defaults from the study: `p = 3-5`, window
   `n = 500-750` days (Sharpe of the multi-swap version peaked near 500), and for several instruments set
   `rho = 0` unless `x~_t . x~_i > 0.4` and trade the instrument with the largest `|signal|`. It assumes patterns are
   symmetric (a large sell mirrors a large buy). With `p = 1` the signal collapses to `sgn(d_t) x sum d_{i+1}/d_i`,
   a ratio estimator with heavy tails, so use `p >= 3`. Run it on PCA residuals rather than raw changes: fit 2 PCs
   on 63 days of daily bp changes (2, 3, 5, 7, 10y), regress each new day's cross-tenor changes on the scaled PC
   loadings and take (fitted minus actual) as that day's residual, known only at that day's close. Trading the
   factors alone gave Sharpe about 0.8, worse than residuals (same source). A residual is not a tradable
   instrument: trading the 7y outright returned a Sharpe near zero, so trade a fly (7y against 5y and 10y) with
   weights in the null space of the factor loadings, zero exposure to the two PCs (same source).
   The paper chose the window `n` to maximise Sharpe on the training period, so the quoted peaks are
   in-sample maxima.
6. **Walk-forward the analog itself.** An analog forecast is a model: score it with `ic_stats` on dates not used
   as analogs, using the h-row exclusion above.

### 8. Clustering and regime states
- **Instrument clustering** (choose representatives, avoid duplicate bets): `d_ij = sqrt(0.5 (1 - rho_ij))`,
  hierarchical linkage on those distances; assets in one cluster carry overlapping information (AFML, 2018;
  BofA, US Rates: CTAs impact on the rates market, 18 Aug 2020). Use only the first PC per cluster, since higher
  eigenvectors are unstable.
- **Macro regime clusters** (k-means on z-scored macro variables): 10 clusters under an 80/20 rule, 80% of data in
  intuitive common clusters, 20% in unusual/risk clusters kept for stress tests (Willer and Saunders, 2026). Cluster
  centroids and counts are in [case-studies](references/case-studies.md). Transition tables show persistent
  states; from "tightening financial conditions" the model gave about 7% to stagflation and 8% to a growth shock
  (Citi Research, Regime Model update, 13 Apr 2026). For HMM / Markov switching and break tests use
  [quant-regime-detection](../quant-regime-detection/SKILL.md); constant transition probabilities have little trading
  use, the question is when they spike (Chan, 2009).
- **Sparse mean-reverting baskets** (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008): cluster the
  penalised inverse covariance first, then search inside one cluster; most mean reversion came with 3-5 legs.
  See [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md).

### 9. Validation protocol (apply to every model above)
1. **Walk-forward, never shuffled k-fold.** Expanding train window, contiguous test blocks of about 1.5 years,
   first `h` test days dropped as embargo, expanded about 4 times, then a **quarantine** period never touched while
   tuning (J.P. Morgan, TradeRunner, 2018). Refit monthly (the 1995 yield-regression protocol re-estimated monthly
   on an expanding window; Salomon Brothers, Understanding the Yield Curve Part 4, Aug 1995). The whole pipeline,
   including screening, sits inside the loop (Hastie et al., 2009).
2. **Permutation ("dumb luck") threshold.** Shuffle the daily sizes in time (3,000 times in the studies; script
   default 1,000) so sell fraction and size distribution are fixed and only timing is destroyed. Daily decisions
   with an `h`-day hold give overlapping `h`-day P&Ls: annualise with `sqrt(252/h)`, not `sqrt(252)`. When the P&L
   is serially correlated (overlapping holds) and sizes are persistent, an i.i.d. shuffle destroys that dependence
   and understates the null spread; use `block >= h`. Residual Sharpe =
   predictor Sharpe minus the shuffled 95th (or 99th/99.9th) percentile. In CV demand the Monte Carlo maximum; on
   quarantine the 95th is enough (J.P. Morgan, 22 Nov 2017). Permutation p-value `= (1 + #{perm >= obs})/(B + 1)`.
3. **IC and breadth.** IC = correlation of predicted and realised change: 0.05 good, 0.10 great, 0.15 world-class;
   above 0.20 usually signals a faulty backtest (Grinold and Kahn, Active Portfolio Management, 1999).
   `IR = IC x sqrt(BR)` with `BR` the number of independent bets per year. Correlated packages are one bet and
   monthly rebalancing of an annual forecast is one bet, not 12. Illustrative: IC 0.05 across 10 truly independent
   packages decided weekly gives `0.05 x sqrt(520) = 1.1`; if effectively 3 independent packages, `0.05 x sqrt(156) = 0.6`.
4. **Trial count.** Log every configuration tried. With 20 independent tries there is a 64% chance of a `t >= 2` fluke
   (`1 - 0.95^20`); after about seven configurations a two-year backtest with Sharpe above 1 is expected even at
   true Sharpe 0 (Tulchinsky et al., 2015). When screening many candidate features, control
   the family-wise error (Holm) or the false-discovery rate (Benjamini-Hochberg under independence) instead of
   reading raw p-values (Hastie et al., 2009; James et al., ISLP). Hand the count to
   [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).
5. **Report uncertainty:** CV standard errors, one-SE rule between families (differences among shrinkage methods
   are often inside one SE; Hastie et al., 2009), and `n_eff`.
6. **Costs.** Subtract bid/offer before judging. A 1bp bid/offer "completely neutralised" the mean reversion in
   small swap baskets (d'Aspremont, 2008); 10y OTR bid/ask cut a Sharpe above 1.2 by just under 0.1 (J.P. Morgan,
   22 Nov 2017). See [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md).
7. **Invalid OOS designs:** the most recent N years as "OOS" with earlier years as training is not independent
   of regime; splitting instruments into IS and OOS sets fails because instruments are correlated
   (Tulchinsky et al., 2015). True OOS is live forward monitoring.

## Worked examples
Longer tables and case numbers: [case-studies](references/case-studies.md).

**1. Shape distance.** `c = (10, 25, 40, 48, 50)` bp at 2/5/10/20/30y. A curve `c + 37` has `d = 0` (pure parallel
shift); `2c + 5` has `d = 33.8` without the stretch term and `0` with it; the mirror image `(50, 48, 40, 25, 10)` has
`d = 65.3` (bundled self-test, illustrative).

**2. 10y direction classifier.** About 1,250 features, daily decision, 1-week hold, `S = 2P - 1`, CV mid-2008 to 2016,
quarantine 2017. RF CV Sharpe above 1.2; quarantine Sharpe of the balanced RF 1.35 versus 0.38 all-long; RF and RBF-SVM beat the
95th and 99th shuffled percentiles, the other methods did not; the best single ANN scored 1.72 but the other four were
about all-long or negative (J.P. Morgan, Do androids dream of electric bonds?, 22 Nov 2017). In 2018 stacking raised CV Sharpe 10-20% over the best solo GBM; in quarantine the stacked Sharpe only approached
0.5, yet shuffle significance was above 99% for the stacks versus 79% for the best solo GBM (J.P. Morgan, #SquadGoals,
21 Sep 2018). Retraining the 2016 model through
3Q18 with no change gave Sharpe 1.27 selling about half of the days, beyond 95% (J.P. Morgan, 31 May 2019).

**3. Ridge versus lasso versus PCR on a small sample** (prostate data, N = 67, 8 predictors; Hastie et al., 2009):
test error LS 0.521 (SE 0.179), best subset 0.492, ridge 0.492 (df 5.0), lasso 0.479, PCR 0.449 (SE 0.105), PLS 0.528.
All inside one SE. Lesson: choose the simplest model within one SE, and do not read a ranking into noise.

**4. Leela on PCA residuals** (US swaps, train about 1994 to late 2007, test late 2007 to late 2008, n = 750, p = 4):
Sharpe 2y 0.4, 3y 1.4, 5y 1.2, 7y 2.2, 10y 0.8 (Burton et al., c.2008; benchmarks in the paper: 10y buy-and-hold 0.25, rolling OLS 0.0-0.23, Burg AR 0.9). The paper does not state which period the per-tenor table covers,
costs are ignored and a daily-flipping sign trade is cost-heavy: an idea generator, not a benchmark.

## Signals & interpretation
- **Pass criteria** (house thresholds, all required): (a) beats persistence/AR on at least two non-overlapping test blocks;
  (b) quarantine Sharpe above the shuffled 95th percentile (CV: above the shuffled maximum); (c) IC between 0.03 and
  0.15 with `n_eff`-adjusted t above 2; (d) neighbouring hyper-parameters give similar results; (e) net of
  bid/offer the Sharpe stays positive; (f) the dominant features make economic sense (importance via MDA on
  purged folds, not MDI alone).
- **Direction of use.** The model output is an input to a trade, not the trade: a `bp` forecast or `S` size is
  combined with value (z-score, fair value), carry/roll and flow in
  [rv-composite-scoring](../rv-composite-scoring/SKILL.md) and
  [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md). Diversify with an old
  score if `IC_2 > rho x IC_1`, hedge with it if `IC_2 < rho x IC_1` (Grinold and Kahn, 1999).
- **Analog read** (house rule). Treat an analog forecast as supportive only if at least 3 distinct episodes agree in sign and the
  weighted mean exceeds the analog standard error; otherwise "no precedent".
- **Model decay** (house rule). Re-fit when rolling IC over the last 6-12 months falls to under half its walk-forward average,
  or when the PCA basis drifts (it drifts over a couple of years; Burton et al., c.2008).
- **Regimes.** Do not pool across breaks (zero lower bound, QE, yield-curve control, hiking cycles). The
  central-bank-text signal vs yield link broke at the zero bound, so a ZLB dummy interaction was needed
  (J.P. Morgan, Welcome to the machine, 26 Apr 2023).

## G10 notes
Almost all published evidence is USD. Do not extend a US result to another market without a fresh walk-forward.

| Market | What is evidenced / how to adapt |
|---|---|
| USD | 10y OTR direction, swap-spread and vol classifiers (2017-18); auction tail/through logistic (10y refunding); CTA-positioning replication; Fed hawk-dove score leads the 1y by about +14bp per +10 points (univariate; about +7bp after controlling lagged yield change). Core CPI above about 2.5% tends to turn the stock-bond correlation positive (Willer and Saunders, 2026) |
| EUR | ECB text score about +12bp per +10 points on the 1y. EGB issuers differ in credit and liquidity, so cluster or model them by issuer rather than pooling into one KNN (guidance, not from a source) |
| GBP | BoE text score about +12bp per +10; weaker fit (adjusted R2 0.11-0.19) than the Fed (0.26-0.45) |
| JPY | Guidance (not from a source): policy-controlled regimes make pooled training periods unreliable, so split them; cross-market analogs against USD must be FX-hedged |
| CAD, AUD, NZD, CHF, SEK, NOK | No ML evidence in the sources. Guidance (not from a source): shorter liquid swap history (NZD, NOK, SEK) means fewer features and stronger shrinkage; validate from scratch |

## Pitfalls
- **Fitting scalers, PCA, feature selection or lambda on all data.** Everything that learns must be inside the
  loop. The bundled self-test perturbs the future and checks past predictions are unchanged.
- **Overlapping labels in random k-fold or OOB.** Purge and embargo `h` rows; OOB is "grossly inflated" when
  uniqueness is low (AFML, 2018).
- **Tuning on accuracy** when sizing by confidence: "high accuracy on small bets and low accuracy on large bets will
  ruin you" (AFML, 2018).
- **Unbalanced classes learn the secular trend** (long bias after a 30-year rally). Balance weights, and benchmark
  against an all-long strategy rather than zero.
- **Correlation of changes is not a tradable spread.** For level relationships test cointegration
  ([quant-cointegration](../quant-cointegration/SKILL.md)); in-sample cointegration often disappears out of sample,
  so use time-varying hedge ratios and monitor (Palomar, 2025). Re-estimate hedge ratios when the regressor variance
  regime shifts (Shalizi, 2025).
- **Million-dart-players fallacy:** picking the best of many random predictors. "ML algorithms will always find a
  pattern, even if that pattern is a statistical fluke" (AFML, 2018). Test the method on random data and on
  simulated data with a known relationship first.
- **Inference after selection.** P-values and intervals computed on the data that chose lambda or the variables
  are optimistic; split the data (Shalizi, 2025).
- **Heavy-tailed or contaminated targets:** use Huber or LAD loss (`rho(u) = u^2` for `|u| <= c`, else
  `2c|u| - c^2`); robust loss does not cure nonlinearity or correlated noise.
- **High R2 or a tiny F p-value does not validate a linear model**; inspect residuals against fitted values,
  time and successive residuals.
- **PCA drift.** Loadings change over a couple of years; residuals from long-window PCA stop being comparable.
- **Analog recency and revisions.** Nearest analogs cluster in recent months; revised macro data (point-in-time only
  from about 1999 for OECD indicators) leak information (Citi Research, Regime Model update, 12 Aug 2026).
- **Option-model probabilities are not outcomes.** Call probabilities saturate near 100% yet issuers call
  non-economically; the empirical classifier expected about $30bn of redemptions versus $78bn from the raw model
  (J.P. Morgan, Taiwanese demand for US fixed income, 10 Jan 2020).
- **Few trades, few degrees of freedom.** Equity Sharpe benchmarks (for 3,000-name daily cross-sections) do not
  transfer to a handful of rates packages; state the IR annualisation (sqrt 252 vs 256).
- **Neural nets** are data-hungry, non-convex and seed-sensitive; use only if a linear or tree model with the same
  features is beaten across seeds (swapsball.net, Intuition and maths behind neural networks, 30 Jan 2018).

## Output
Return, for each model evaluated:
1. **Spec line:** target (definition, `h`, bp or label), feature list with categories, family, hyper-parameters,
   class weights, training span, number of configurations tried.
2. **Table:** model | n | `n_eff` | OOS IC | hit rate | `R2_oos` vs zero | Sharpe (gross/net) | shuffled p95/p99 |
   p-value, with the baselines (persistence, AR, all-long) as rows.
3. **Latest signal row(s) in the `signals` shape:** `date, snap, strategy_id, package_id, value, unit, zscore,
   horizon_days, model_version` (`unit = bp` for a forecast change, `prob` for `P(rally)`, with `S = 2P - 1`
   noted). The forecast is dated `t` and traded from `t+1`.
4. **For analogs:** table `date | dist | weight | forward change by tenor`, weighted forecast, same-sign share, number
   of distinct episodes.
5. **Verdict:** pass / fail against the criteria above, the main reason, and hand-off to
   [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) only for a pass; otherwise to
   [rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Scripts
- [`scripts/ml_baseline.py`](scripts/ml_baseline.py): leakage-safe walk-forward forecast of the forward `h`-day change of
  a bp package (ridge or GBM, train-only scaling, embargo = `h`, lambda picked on a chronological validation block),
  `ic_stats` (Spearman IC, hit rate, overlap-adjusted t), `kelly_size`, `shuffle_sharpe` (permutation threshold),
  `shape_distance` / `analog_search` (parallel-shift-invariant analogs with episode separation), `leela_signal`.
  CLI modes `walkforward` and `analog` read a canonical `curve_par` CSV/Parquet; `python scripts/ml_baseline.py --help`.
  Options: `--delay` (entry lag in rows), `--snap` (required when the file holds several snaps).
  `--selftest` checks ridge against the orthonormal closed form, the shape distance, a planted analog twin and its
  forward change, the Leela `p = 1` identity and a planted periodic pattern, the shuffle threshold (i.i.d. and block),
  point-in-time invariance of the walk-forward (a perturbed future must not move any earlier prediction, which fails
  if the embargo is shorter than `delay + h`), and a GBM-versus-ridge interaction case.

## Related skills
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): labels, sample weights, fractional differentiation, leakage audit
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): purged CV, CPCV, deflated Sharpe, PBO, multiple testing
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA factors and residuals used as features and analog prefilters
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): OLS, rolling and robust regression, hedge ratios
- [quant-regime-detection](../quant-regime-detection/SKILL.md): HMM, Markov switching, break tests, regime catalogue
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): using regime and analog results in scenario work
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): text-classifier scores as features
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): blending model output with other signals, IC decay
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores and screens used as features
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): turning `S` into DV01
- [bt-backtest-design](../bt-backtest-design/SKILL.md): signal to position to P&L, point-in-time data
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): stale data, outliers, roll stitching before modelling
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): where a model score enters the ranking

## References
- Lopez de Prado - Advances in Financial Machine Learning (John Wiley & Sons, 2018): bagging variance, RF with overlapping labels, class weights, log-loss scoring, MDI/MDA/SFI, log-uniform search, HRP distance.
- J.P. Morgan - "Do androids dream of electric bonds? Machine learning in interest rate markets" (Munier Salem, Younger, Zhao et al., US Fixed Income Strategy, 22 Nov 2017): RF/SVM/KNN/ANN comparison, permutation thresholds, time-series CV, Kelly sizing.
- J.P. Morgan - "TradeRunner: Ensemble learning-driven systematic trading in interest rate markets" (Salem, Younger, Huang, 16 Aug 2018): RF vs GBM, class-weight effects, walk-forward, Monte Carlo residual Sharpe, costs.
- J.P. Morgan - "#SquadGoals: Stacking and voting with machine learning classifiers" (Salem, Younger, Huang, 21 Sep 2018): stacking, soft voting, contrarian constituents.
- J.P. Morgan - "Is bank convexity hedging lying in wait?" (Younger, Salem, St John, Huang, US Fixed Income Markets Weekly, 31 May 2019): retrained 10y model, hit rate vs conviction.
- J.P. Morgan - "Taiwanese demand for US fixed income in 2020" (Younger, Beinstein, Salem, St John, 10 Jan 2020): empirical call-probability classifier, logistic vs RF.
- J.P. Morgan Global Economic Research - "Welcome to the machine: NLP of central bank speak" (Lupton, Aitas, Weitzenfeld, 26 Apr 2023) and "Listen up: Upgrading J.P.Morgan's central bank NLP machine" (Lupton, Weitzenfeld, 2 Jul 2024): hawk-dove score, lead regressions, ZLB break.
- Hastie, Tibshirani, Friedman - The Elements of Statistical Learning (2nd ed., Springer, 2009): ridge, lasso, elastic net, PCR/PLS, effective df, CV-loop rules, prostate comparison.
- James, Witten, Hastie, Tibshirani, Taylor - An Introduction to Statistical Learning with Applications in Python (ISLP): lambda by CV, AR benchmark, chronological split, VIF.
- Murphy - Machine Learning: A Probabilistic Perspective (MIT Press, 2012): ridge/lasso closed forms, stability selection, debiasing, one-SE rule.
- Shalizi - The Truth about Linear Regression (draft lecture notes, 20 Oct 2025): optimism, Cp/AIC/BIC/LOOCV, WLS, leverage, inference after selection.
- Bishop - Pattern Recognition and Machine Learning (Springer, 2006): regularised least squares, committees.
- Gelman et al. - Bayesian Data Analysis (3rd ed., CRC Press, 2014) and McElreath - Statistical Rethinking (CRC Press, 2016): shrinkage priors, information criteria cautions.
- Grinold, Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): IC, IR, breadth, signal combination with decay.
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): trial counting, OOS design, ratio-like inputs.
- Chan - Quantitative Trading (Wiley, 2009): parameter budget, regime-switching critique, cointegration.
- Burton, Dektor, Wheeler - Time Series Prediction of US Swap Rates (Stanford student project, c.2008): rolling OLS, Leela correlation analog, PCA residual prefilter.
- d'Aspremont - Identifying Small Mean Reverting Portfolios (arXiv:0708.3048, 2008): sparse baskets, cluster-then-search, bid/offer hurdle.
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): sparse regression, reweighted l1, cointegration decay.
- Willer, Saunders - Trading Global Macro Markets (Wiley, 2026): nearest-neighbour playbook, k-means macro clusters, ridge credit/equity model.
- Citi Research - Quantitative Framework for Regime Investing (Saunders, Willer, 29 Oct 2021) and Regime Model updates (Saunders, Rupert, 8 Apr 2025; Saunders, Vo, 13 Apr 2026 and 12 Aug 2026): KNN regime analogs, cluster centroids and transitions.
- BofA Securities - US Rates: CTAs impact on the rates market (Braizinha, 18 Aug 2020): top-down replication, clustering, positioning from betas.
- Citi Research - US Rates Weekly: Learning on the job (Mathai et al., 2 Aug 2019): auction tail/through regression and logistic models.
- Salomon Brothers - Understanding the Yield Curve, Part 4: Forecasting U.S. Bond Returns (Aug 1995): four-predictor regression, expanding-window protocol.
- Darbyshire - Coding Interest Rates: FX, Swaps and Bonds: curve-shape analog distance (eq 6.1).
- swapsball.net - Intuition and maths behind neural networks (30 Jan 2018): supervised learning as MLE, training pitfalls.
- Tibshirani, "Regression shrinkage and selection via the lasso", JRSS B, 1996 (external); Zou and Hastie, "Regularization and variable selection via the elastic net", JRSS B, 2005 (external); Breiman, "Random forests", Machine Learning, 2001 (external); Friedman, "Greedy function approximation: a gradient boosting machine", Annals of Statistics, 2001 (external).
