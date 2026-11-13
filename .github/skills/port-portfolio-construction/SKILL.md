---
name: port-portfolio-construction
description: 'Combines individual relative-value trades (curve spreads, flies, swap spreads/ASW, cross-market govies, basis, futures, STIR, vol packages) into one G10 rates book. Covers the Fundamental Law (IR = IC x sqrt(breadth), effective independent bets), alpha refinement and neutralisation, screening a candidate against the existing book, equal-risk / inverse-vol / risk-parity / HRP / constrained mean-variance weights, PCA (PC1/PC2) factor and directionality neutrality, Euler risk contributions (CTR, MCTR, risk share), VaR-minimising and compression hedges, and turnover/cost-aware rebalancing. Use when asked about portfolio construction, how to weight or combine several trades or signals, whether a new trade diversifies the book, risk parity vs mean-variance, hidden duration or steepener exposure, correlation and diversification, marginal risk, book-level hedge, effective number of bets, or why an optimiser gives extreme weights. Per-trade DV01 size, stops and Kelly: port-position-sizing-and-risk-budget.'
---

# Portfolio construction for RV books

A book of RV trades earns its Sharpe from the number of *independent* bets, not from the cleverness of the weights.
This skill turns a shortlist of trades (each with a view, a risk vector and a P&L history) into one set of risk
weights, checks that the result is not secretly one directional or one-factor bet, and decomposes where the risk
sits. Defaults are deliberately simple (equal risk, shrunk covariance, small explicit constraints), because
optimised weights add little over equal weights and carry look-ahead.

## When to use
- "How should I weight these 6 trades?", "does adding this fly diversify the book?", "risk parity or mean-variance?"
- "Is my book just a steepener?", "what is my net PC1 / duration exposure?", "which trade contributes most risk?"
- Combining several signals or models into one position per trade (see also [signal combination](../quant-signal-combination-and-decay/SKILL.md)).
- Hedging a book with a few liquid instruments, or compressing a risk ladder onto 2y/5y/10y/30y.
- Setting turnover limits, no-trade bands and constraint sets for a systematic RV book.
- Not for single-trade sizing, vol targeting, Kelly and stops ([sizing](../port-position-sizing-and-risk-budget/SKILL.md)) or for shocks and tails ([stress](../port-scenario-and-stress-testing/SKILL.md)); those take this skill's output.

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) (`references/schemas.md`).
- `positions`: current legs per `package_id` with signed `dv01_ccy` (positive = long duration / receive fixed), `ccy`, `weight`.
- `pnl`: daily `total_ccy` per `package_id` (realised, or backtest P&L for candidates that have not traded). At least
  max(100, N+1) complete overlapping days for N trades. Young trades use backtest series, never zero-fill.
- `signals`: `value`, `zscore`, `horizon_days` per package, for alpha scaling and breadth counting.
- `curve_par` or `curve_zero` history for the PCA / factor risk model (daily changes in bp, >= 3y, several regimes).
- Optional: bid/offer and impact estimates per instrument (see [transaction costs](../bt-transaction-costs-and-liquidity/SKILL.md)).
If anything is missing, ask the user or the data adapter. Never invent covariances or alphas.

Conventions: DV01 in currency per bp, positive for long duration / receive fixed. Curve A-B = longer minus shorter
yield, fly 2s5s10s = 2x5y - 2y - 10y (positive = belly cheap), receive-belly risk vector (-1, +2, -1). Covariance
inputs are daily bp *changes*, never levels. A trade's P&L series is signed in its intended direction, so "weight
>= 0" means "as traded". Several source books use the opposite sign (paid = positive); flip when reusing their numbers.

## Method

### 1. Pipeline (order matters)
1. Refine each view into an expected P&L per unit risk (step 3). 2. Screen candidates against the book (step 4).
3. Build the risk model (step 5). 4. Pick the combiner (step 6). 5. Neutralise unwanted factors (step 7).
6. Decompose and run the diagnostics (step 8). 7. Apply costs, bands and caps (step 10). 8. Hand to sizing and stress.
Neutralise, then scale, then trim: alpha analysis in that order, with the neutralisation choice fixed a priori and
not chosen by trying all and keeping the best (Grinold & Kahn, Active Portfolio Management, 1999).

### 2. Breadth, skill and the Fundamental Law
- **IR = IC x sqrt(BR)**. BR = number of *independent* forecasts per year, IC = correlation of forecast with outcome.
  IR is annualised residual return / residual risk; quarterly IR = annual/2, monthly = annual/sqrt(12). SE(IR) ~ 1/sqrt(years).
  (Grinold & Kahn, 1999)
- Trade-offs: IR 0.5 -> 1.0 needs 2x skill or 4x breadth; +50% breadth ~ +22% skill. Hit rate p and IC: IC = 2p - 1
  for a binary call (IC 0.10 = right 55% of the time; IC 0.0577 = 52.9%).
- Back out realised breadth: BR = (IR/IC)^2. IR 0.27 at IC 0.01 means ~700 independent bets, not the 6,000 data items.
  Reassessing an annual view monthly is 1 bet, not 12.
- **Independent strategies add in squares**: IR^2 = sum IR_i^2. IR 0.8 plus an independent IR 0.43 source gives IR^2 0.64 -> 0.82
  (+28% value added). Two sources with equal IC and correlation gamma: IC_com = IC x sqrt(2/(1+gamma)); gamma = 0.5 and IC 0.0816 -> 0.0942.
  Two equal-risk sleeves with Sharpes SR1, SR2 and correlation rho: SR = (SR1+SR2)/sqrt(2(1+rho)).
- Realism ceilings: IC 0.05 good, 0.10 great, 0.15 world-class; IC > 0.20 or IR > 2 signals a faulty backtest. A track
  record proves IR 0.5 only after ~16 years (t = IR x sqrt(years)); 20 independent tries give a 64% chance (1 - 0.95^20) that at least one clears a 5% one-sided bar by luck
  (use [validation](../bt-validation-and-overfitting/SKILL.md) and deflate).
- **Effective bets of a book** (agent heuristic for BR): N_eff = exp(-sum theta_i ln theta_i), theta_i = PC risk share of the
  *book* (eigen-decompose V, f = W'w, theta_i = f_i^2 lambda_i / sum). N for N equal uncorrelated trades, 1 for one factor
  (Meucci, via Lopez de Prado, Advances in Financial Machine Learning, 2018). Annual breadth ~ N_eff x (independent
  re-underwrites per year, ~ 1 / holding period in years). Quote N_eff next to the trade count.
- Evidence that breadth across *themes* beats the best theme: top-2 curve carry-to-risk pairs plus top-2 cross-market pairs,
  equal risk: IR 1.33 vs 1.06 for the best 4 pooled (correlation between themes 0.06) (J.P. Morgan, Investment Strategies 31, Jan 2007).

### 3. From views to alphas
- Refined forecast alpha = vol x IC x score, score z = (g - E g)/Std g. IC = 0 means alpha 0; vol gives units
  (Grinold & Kahn, 1999). If the signal dispersion already scales with each asset's vol (e.g. a carry-to-vol ratio), do not
  multiply by vol again. Check whether dispersion scales with vol first.
- Qualitative views to scores (mean 0, sd 1): very positive +1.73 (11%), positive +0.87 (22%), none 0 (33%), negative -0.87, very negative -1.73.
- Scale: Std(alpha) ~ vol x IC. Trim: inspect |alpha| > 3x scale, zero bad data, pull genuine outliers to 3x. Missing = NaN, never 0.
- IR is linear in alpha scale: if alphas imply IR 2.46 and you believe 0.75, multiply alphas by 0.75/2.46. Optimal aggressiveness
  omega* = IR/(2 lambda), value added IR^2/(4 lambda); lambda 0.05/0.10/0.15 = low/moderate/high risk aversion (IR 0.75: 7.5/3.75/2.5% residual risk).
- Return forecasts barely change risk: sigma_post = sigma_prior x sqrt(1 - IC^2). Do not replace a 0.95 correlation by a negative one
  because you forecast divergence. Keep the risk model independent of the alpha process.
- Five ways to form the expected move of an RV trade: status quo / roll-down, oppose overbought, momentum, RV (PCA residual or model deviation), macro regime
  shift. E[P] dominates the Sharpe and is the hardest to forecast (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022).
- Hold *constant* risk per trade unless you have evidence otherwise: scaling risk by carry-to-risk level cut IR from 0.94 to 0.60 (3-trade case 1.00 -> 0.45)
  in the cross-market and curve study (J.P. Morgan, Investment Strategies 31, Jan 2007). Equal weights ~ optimised weights for 5 duration signals: IR ~1.03 vs 1.07, the latter in-sample
  (J.P. Morgan, Investment Strategies 74, Oct 2012). A combined signal is a risk-budget scalar (-0.2 = short 20% of the limit).

### 4. Screen a candidate against the existing book
Run before optimising; it is cheaper than any optimiser and catches most mistakes.
1. **Loadings**: correlation (daily and weekly changes) and regression beta of the candidate's P&L to the standard factors:
   outright level (10y), 2y1y or front end, 2s10s, 10s30s, 5s10s30s, plus the book's own P&L. Prefer candidates that do not load on
   what the book is already long. Example: receiving EUR 2y1y has correlation -0.54 to the 10s30s steepener, so it is more steepener
   risk; receiving 2s5s (10s30s correlation -0.06) is the complement (Nordea, EUR rates: How about that outright receiving, 26 Sep 2025).
2. **Pool correlation**: |rho| of candidate P&L to book P&L, or to the most similar existing trade. > 0.7 = duplicate; take it only if its own IR is clearly higher
   (equity-derived rule, 0.5-0.7 cap; Tulchinsky, Finding Alphas, 2015; treat as a screen, not a law, for a small universe).
3. **Marginal risk**: MCTR of the candidate at a small weight. Negative MCTR = diversifier, rank it above a higher-alpha duplicate.
4. **Opposite-sign pairs**: carry flies with opposite correlation to curvature and 10s30s hedge each other's vol/curvature view
   (Nordea, EUR rates: The quiet game, 12 Aug 2025). Decompose realised P&L before crediting the curve view.
5. **Similar-vol legs** in cross-market pairs hedge better to market direction (CAD vs EUR 10y chosen for this reason)
   (J.P. Morgan, Rule-based Fixed Income Monthly, Nov 2012).
6. **Different signal on the same universe diversifies** (outright vs spread carry-to-risk picked the same pair 6% of the time, return correlation 0.39).
   Same dataset means correlated errors even when ideas differ.
7. Second trade chosen to *optimise* ex-ante combined carry-to-risk did not beat the plain top-2 ranking (1.00 vs 1.10). Do not over-engineer pair selection.

### 5. Risk model for construction
- Build V from P&L (or bp changes) over the **holding horizon**, non-overlapping if > 1 day; correlations are horizon dependent (a BTP fly vs average-yield:
  -0.88 in levels, +0.06 daily, -0.27 weekly, -0.57 two-weekly) (Huggins & Schaller, Fixed Income Relative Value Analysis, 2024). A book built on a long-horizon correlation shows higher short-horizon vol than planned.
- Hygiene: changes not levels; no demeaning; T > N is the rank minimum, >= 100 points and >= 3N the working floor (below 3N lean on shrink >= 0.5 or a factor covariance); a short half-life shrinks the effective sample (8-day half-life ~ 23 obs);
  stale prices understate vol/correlation; smoothing inflates correlation and lowers VaR (Darbyshire, 2022; BlackRock's Guide to Fixed-Income Risk Management, 2023).
- Defaults (house, validate in [covariance estimation](../quant-covariance-estimation/SKILL.md)): 260-day equal-weight covariance, or EWMA with half-life 63 days (`--halflife 63`), then shrink 0.2-0.3 toward
  the diagonal (`--shrink 0.3`). Optimisers exploit covariance errors; underestimating vol is worse than overestimating (Grinold & Kahn, 1999).
- For many trades use a **factor covariance**: PCA on daily bp changes with K >= 3 (err toward more factors) plus trade-specific variance. Run separate PCAs for outright and basis risk, or the outright variance dominates.
- **Stress overlay**: re-run the final book with all same-sign off-diagonals set to 0.7 and report the vol uplift. Crowded unwinds moved correlations from 0.1-0.3 to 0.7-0.95 (Brenndoerfer, Mean Reversion and Statistical Arbitrage, Dec 2025). If stressed vol > 2x normal, the diversification is cosmetic (house threshold).
- Cross-country legs: size by relative vol, SD(local IRS receiver) / SD(USD IRS receiver), EWMA 11-day half-life; this cut the max/min SD ratio across markets from 4.5 to 2.9, but does not remove directionality to global risk (Macrosynergy, Interest rate swap returns, 2025).

### 6. Choose the combiner
| Situation | Use | Why |
|---|---|---|
| N <= 5, no reliable alphas | **Equal risk** (inverse vol, w_i ~ 1/sigma_i) | robust to bad data; adverse selection avoided (largest signals come late in trends) |
| 5 < N <= 30, correlated, alphas weak | **Risk parity** (equal risk contribution) or **HRP** | no mu needed; HRP avoids covariance inversion |
| N large or covariance near-singular (condition number high) | **HRP** | out-of-sample variance 0.067 vs 0.116 for critical-line mean-variance (Lopez de Prado, 2018) |
| Credible alphas, N <= 30 | **Constrained mean-variance with ridge to the equal-risk prior** | alphas used, instability tamed |
| Hidden common factor | neutralise first (step 7), then any of the above | |
Formulas (all in `scripts/portfolio.py`):
- Mean-variance: max mu'w - (lambda/2) w'Vw; unconstrained w = V^-1 mu / lambda; fully invested: w = (1/lambda) V^-1 (mu + nu 1). Max-Sharpe: min y'Vy s.t. y'(mu - rf) >= 1, y >= 0, w = y/1'y (Schaible).
  Two assets: vol allocation v1 ~ (s1 - rho s2)/(1 - rho^2); asset 2 is *shorted* if s2/s1 < rho even with s2 > 0, as a hedge.
- Inverse-variance w_i = V_ii^-1 / sum V_jj^-1 is the minimum-variance, fully invested solution when V is diagonal (equal expected returns). Inverse-vol is equal stand-alone risk and ignores correlation.
- **Risk parity / budgeting**: w_i (Vw)_i = b_i w'Vw, b = 1/N default. Solve by cyclical coordinate descent x_i = (-a_i + sqrt(a_i^2 + 4 V_ii b_i)) / (2 V_ii), a_i = sum_{j != i} V_ij x_j, then w = x/sum x (Spinu). For trades with fixed
  direction run it on the *signed trade P&L* covariance so w >= 0 (Spinu sign trick). Equal correlations: w_i ~ 1/sigma_i.
- **HRP** (Lopez de Prado): d_ij = sqrt(0.5(1 - rho_ij)); distance of distances; single linkage; quasi-diagonalise; recursive bisection, split alpha = 1 - V1/(V1+V2) with cluster variance from inverse-variance weights. 0 <= w <= 1; equals inverse-variance for diagonal V.
- **Estimation error**: sample means are nearly useless (error > 100% at N = 100, T = 500); a forecast-Sharpe error of 0.5 costs 10-50% of Sharpe in naive MV (Paleologo, The Elements of Quantitative Investing, 2025; Palomar, Portfolio Optimization, 2025). Mitigate with caps, ridge to the equal-risk prior (house default: ridge weight 1-10 x lambda), shrinkage, or bagging (200 bootstrap re-optimisations averaged, block bootstrap for dependent data).
- **Constraints are modified alphas**: a constrained optimum equals unconstrained MV on shrunk alphas (62% effective-IC loss in the book's example). State the cap's implied shrink instead of hiding it. QP-based construction averaged ex-post IR 1.88 vs 0.86 for equal-weight top-N screens when the model was right (law: 2.24).
- Practical constraint set (house starting point for a rates RV book): gross risk 1.0, per-trade |w| <= 0.35, min |w| 0.02 (drop dust), net PC1 and net DV01 inside bands (step 7), turnover L1 <= limit.
- Mean-variance is single-period, while RV trades have different horizons, non-normal payoffs and correlations that change on reversion; treat it as a rationing tool, not an oracle (Duering, 2021).
- Kelly / leverage: multi-strategy F* = C^-1 M, half-Kelly, capped by tolerable drawdown / worst one-period loss. Kelly is a sizing step: take the final weights to [sizing](../port-position-sizing-and-risk-budget/SKILL.md).

### 7. Factor neutrality and hidden directionality
- PC exposure of a risk vector t: E't with E the eigenvectors of the bp-change covariance. Goal: x with E'(t + x) = (0, 0, alpha...)'.
- **Method B (preferred), minimum-norm adjustment**: x = -E (E'E)^-1 E't, i.e. t + x = (I - ee'/e'e) t for PC1. Restrict the instruments allowed to change (keep 30y fixed) by solving on the free rows only (`pca_neutralise(t, E, free=...)`). Each PC neutralised removes one degree of freedom; with three instruments PC1+PC2-neutral leaves only PC3, a "fatality" (QFSE, "Hedging a trade for PCA component neutrality", Nov 2019).
- **Target a PC risk distribution** (Lopez de Prado): with V W = W Lambda and beta = W'w, risk share of PC n is R_n = beta_n^2 Lambda_n / sigma^2; for a target R set beta_n = sigma sqrt(R_n / Lambda_n), w = W beta. Putting all risk on the smallest-eigenvalue PC is the default solution; inverse-variance weights instead spread risk over PC1-PC2 too.
- **Method A, divide by loadings** t / e1: valid only if sum t = 0; transparent but not unique.
- **A DV01-neutral steepener is not PC1-neutral.** Use PC1 duration, not parallel/OAD, for curve trades; check one-factor explanatory power > 95% before trusting it, and use >= 2 PCs for duration-neutral curve books (Golub & Tilman, Risk Management: Approaches for Fixed Income Markets, 2000).
- **Partial hedge**: with uncertain betas hedge less than fully (optimal factor-mimicking hedge is below full neutralisation). Hedging reduces correlation to the factor, not necessarily volatility. More hedge degrees of freedom lower VaR but move the trade further from its intended structure; track the hedged trade by residual P&L with the PC1 move stripped (Darbyshire, 2022).
- **Neutrality is instantaneous**: DV01 decays with ageing and convexity; use forward DV01 over the holding horizon. Matching partial durations exactly is unstable; add costs and diversify hedges (Duering, Fixed Income Trading and Risk Management, 2021).
- **Hidden directionality check** (always): regress book P&L on outright duration (e.g. 10y level) and on PC1-3; report beta (t-stat from non-overlapping or Newey-West errors) and the long/short split. The 5-signal duration overlay was 57% long / 43% short with ~0 beta, but the long bias came entirely from bond momentum (J.P. Morgan, IS74, Oct 2012). A single low-vol market (JPY) can create a long-duration bias in a cross-market basket (J.P. Morgan, Rule-based Fixed Income Monthly, Nov 2012). Vol-normalisation can *increase* risk-on directionality (Macrosynergy, 2025).
- Global directional beta-hedge for cross-market books: basket of global equity futures, credit and carry/EM FX; WLS betas, average of weekly (26-week half-life) and daily (63-day half-life) estimates. Out-of-sample absolute risk correlation fell 0.23 -> 0.12 but hedged return SD did not fall.

### 8. Decompose and diagnose
- sigma_p = sqrt(w'Vw). Stand-alone risk SAR_i = |w_i| sigma_i (ignores correlation). **MCTR_i = (Vw)_i / sigma_p. CTR_i = w_i MCTR_i, sum CTR = sigma_p.** Risk share RRC_i = CTR_i / sigma_p, sum 1. Factor CTR: (B'w)_f (Sigma B'w)_f / sigma_p. Implied block correlation from the 2x2 ANOVA table.
- Aggregation test (c is subadditive): c = sqrt(S'QS); compare c_book with the sum of sleeve c (sleeves perfectly correlated) and with sqrt(sum c^2) (uncorrelated). Between the two = partial diversification; below sqrt(sum c^2) = offsetting. Implied sleeve correlation rho = (c_book^2 - c1^2 - c2^2)/(2 c1 c2). Desk example 529 vs 627 (sum) and 445 (uncorrelated): rho ~ 0.4, only modest diversification.
- A structurally long-vol or long-convexity sleeve offsets a short-vol carry book (monthly P&L correlation ~0.26 with vol changes, skew ~0 vs about -3 for systematic short straddles; Citi Vol Lab, 9 May 2019).
- **Negative CTR is a diversifier**: do not cut it for risk reduction. Reconcile intended vs actual bets with a stepwise VaR (add factor clusters one by one, watch cumulative risk) and attribute risk changes to "economy" (covariance) vs "exposure" (positions).
- Checks (house thresholds): N_eff / N < 0.5 -> book is one or two bets; any single trade RRC > 35% with N >= 5; |net PC1 DV01| > 10% of gross DV01; book P&L beta to outright duration significantly != 0 without a stated view.

### 9. VaR-minimising trades and compression (what to add or trade next)
All from c = sqrt(S'QS), S = par risk strip (DV01 per bucket), Q = covariance of daily bp changes (Darbyshire, 2022).
- VaR_5% = 1.644c, VaR_1% = 2.326c (zero mean, normal). Euler allocation c_alloc = (1/c) diag(S) Q S.
- **Single-instrument trade** T_i = -(QS)_i / q_ii; new c = sqrt(c^2 + 2 (QS)_i T_i + q_ii T_i^2). **Only one of the N suggestions is valid at a time**; to do several at once trade ~50% of each and recompute.
- **Subset hedge / compression**: T_hat = -Q_hh^-1 Q_h: S, where h indexes allowed instruments (`var_min_subset`). Residual c after the hedge measures how well 2y/5y/10y/30y represent the book. Always at least as good as any single trade.
- Diagnostic: if the best single trade cuts risk < ~15-20%, risk is RV/combination-driven; if every suggestion has the same sign, outright direction dominates. A par-model hedge only offsets direction; use a trader model (spreads, flies) to see independent RV risks. A position that makes P&L with no VaR contribution is a take-profit candidate.
- Hedge-instrument VaR minimisation uses liquid instruments when the risky bucket is costly; custom Jacobian buckets (5s6s7s, 5s10s) are exact for P&L explain but are correlated, so overlay a VaR-minimisation (QFSE, "Can PCA be used to transform a ladder of interest rate risk?", Sep 2023).
- Include transaction costs and diversify across correlated hedges; a convex impact term (impact ~ sqrt(size), total cost ~ size^1.5) makes the hedge basket unique (BlackRock, 2023). Low correlation between hedge and book is a red flag.

### 10. Costs, turnover and rebalancing
- Annualised cost = round-trip cost / holding period in years. Impact ~ sqrt(size): roughly one day's volatility to trade one day's volume. For quoting and margin keep impact as a decoupled add-on (Darbyshire, 2022); inside a hedge or rebalance optimiser a convex impact term is what forces diversification across correlated hedges.
- Value added vs turnover is concave: >= 75% of the incremental value added at 50% of the turnover (>= 87% of IR). The implied cost of a turnover cap is the slope at the cap; if round-trip cost exceeds the initial slope, do not trade. Trade the highest-value changes first (Grinold & Kahn, 1999).
- Prefer a **tracking band**: rebalance only when tracking error to target > epsilon, trade to the band edge. Use ridge to the *current* weights rather than to the prior when turnover matters. A chain of static optima is not the dynamic optimum under costs.
- Signal decay: half-life = ln 0.5 / ln gamma; monthly decay with a one-quarter half-life gives gamma 0.7937. Mixing current and lagged scores diversifies if IC_2 > rho IC_1. Linear decay (weights n, n-1, ..., 1) cuts turnover cheaply.
- Roll-down is a scenario, not an arbitrage: effectively short vol and long theta, crowded, and it failed in 2021-22. Re-underwrite rather than hold when the thesis changes.

## G10 differences that matter for construction
- **USD**: highest IRS receiver return vol among DM (~3.5% annualised); UST PC1 typically 85-95% of variance, first two 93-99% (Golub & Tilman, 2000), so a 2-factor model is adequate for outright books but not for duration-neutral curve books. Stock-bond correlation turns positive above ~2.5% core CPI (fit 7.43x - 0.23, R^2 0.22, which crosses zero nearer 3.1%; the source calls it unstable), so duration stops diversifying equity-like books (Willer & Saunders, Trading Global Macro Markets, 2026).
- **EUR / GBP / CHF / SEK**: IRS return correlations ~0.8 (monthly 5y receiver, 1999-2018); treat cross-market trades inside this block as one factor. In 2025 steepeners were the EUR consensus; add risk orthogonal to the crowd (Nordea, 26 Sep 2025).
- **CAD / USD, AUD / NZD**: ~0.8 correlated; pair the similar-vol legs. Relative SD vs USD ~0.8-0.9 (AUD), 0.6-0.7 (NZD).
- **NOK**: correlations 0.5-0.7 with USD, NZD, SEK, and thin benchmark liquidity: widen cost assumptions and shrink alphas.
- **JPY**: lowest vol (~1%, relative SD vs USD ~0.3) and least correlated (0.2-0.3); vol-normalised baskets overweight it and acquire long-duration bias. Carry signals break under yield-curve control: substitute the next-ranked market. JGB duration signals are weak (IR ~0.3) but uncorrelated, so little drag.
- Equal country weights ignore liquidity: G4 overweight may be needed for capacity (J.P. Morgan, Systematic fixed income trading strategies, Apr 2015).
- EGB spread legs and swap spreads carry sign conventions of their own (US: swap - Treasury yield; EGB ASW: bond yield - swap). Convert every leg to signed DV01 first ([DV01 and transforms](../fi-risk-dv01-and-transforms/SKILL.md)).

## Worked examples
1. **Theme breadth** (J.P. Morgan, Investment Strategies 31, Jan 2007). Curve top-2 IR 1.05, cross-market top-2 IR 0.93, correlation 0.06. Equal-risk SR formula: (1.05 + 0.93)/sqrt(2 x 1.06) = 1.36; realised 50/50 of both = 1.33. Squares rule: sqrt(1.05^2 + 0.93^2) = 1.40 at zero correlation. Both agree; the diversification dominated "higher alpha discovery".
2. **Risk parity by hand** (illustrative). Three trades, daily vols 1, 2, 4 (k$), all pairwise correlations 0.3. Equal correlation, so w ~ 1/sigma = (0.571, 0.286, 0.143); each RRC = 1/3. Inverse variance would give (0.762, 0.190, 0.048), which under-allocates risk to the noisy trades. A printed two-name "equal risk" exhibit with vols 2.5% and 2.0% shows 39/61, but inverse-vol of those is 44/56 (39/61 is inverse-variance), so recompute rather than copy.
3. **PCA-neutral 2s5s10s** (Darbyshire, Ex 23, 2022; the printed vector, read with receive = positive, is the receive-belly fly). PC1 loadings (2y,5y,10y,30y) = (0.65, 0.59, 0.44, 0.20); receive-belly t = (-1, +2, -1, 0), e1't = 0.09 (DV01-neutral but not PC1-neutral). Divide-by-loadings, belly rescaled to 1.94: (-0.89, 1.94, -1.30, 0). Minimal adjustment with 30y fixed: (-1.07, 1.94, -1.05, 0) as printed (the rounded loadings above give -1.06, 1.94, -1.04), closer to the original fly. Script reproduces both.
4. **Where does the risk sit?** (Darbyshire, Ch 14, 2022; source sign, paid = positive, so flip signs for this skill's convention). S = DV01 strip (2y,5y,10y,30y) = (-10,000, 2,500, 10,000, -4,000), c = 16,174, VaR_5% 26,590. Allocation (15,787; -2,602; 1,437; 1,552) sums to c, so 5y is a diversifier. Best single trade 2y +2,948 cuts only 15.6%, so risk is RV-driven; 2y and 10y together (+8,562, -9,476) cut ~70%, the dominant risk. Details and the rounded-Q reproduction in [worked examples](references/worked-examples.md).
5. **Signal combination** (J.P. Morgan, Update on systematic rule based trading strategies, Mar 2017). Five signals, each IR 0.5-0.8, vol 4.0-5.2%, max drawdown -4.4% to -13.5%; combined return 2.0%, vol 1.7%, IR 1.2, max drawdown -1.8%: the gain is lower vol and drawdown, not higher return. More tables in [evidence and benchmarks](references/evidence-and-benchmarks.md).

## Signals & interpretation
| Reading | Meaning | Action |
|---|---|---|
| N_eff << N | trades load on the same PCs | cut the duplicate; or accept and size as one bet |
| RRC concentrated in one trade | stand-alone risk hides in correlation | re-weight; check its P&L is not a directional proxy |
| book beta to 10y level significant | hidden directionality | PC1-neutralise (step 7) or declare it as a view |
| best VaR-minimising trade < 20% | RV-driven risk | fine; do not force a hedge |
| stressed vol > 2x normal | correlation-sensitive diversification | lower gross or add a convex/long-vol sleeve |
| optimiser returns corners / 100% in one trade | covariance noise or alpha scale | ridge to prior, cap, HRP |
| IC > 0.2 or book IR > 2 in backtest | probable leak or overfit | back to validation |

## Pitfalls
- Dependent signals masquerade as breadth; momentum and carry were the diversifying pair (negative correlation) while PMI, revisions and equity momentum correlated 0.4-0.6.
- Diversification fails in crises: crowded unwinds push correlations toward 1. Size on stressed, not average, correlation.
- Carry books fail on vol spikes and crowding, not lack of carry: high rolling beta of hedge-fund indices to the strategy preceded the LTCM and 2001 drawdowns, so use it as a kill signal (J.P. Morgan, IS31, 2007).
- Optimiser as estimation-error maximiser: critical-line solutions concentrate (92.7% in 5 of 10 assets) and churn. Many correlated sleeves: HRP or shrinkage, not inversion.
- Using a correlation from a different horizon, or from stale or smoothed series, to build the book.
- Equity-centric thresholds (Sharpe 2.5-6, pool correlation 0.5-0.7, turnover < 40%) do not transfer to a 20-trade rates book; small universes need deeper per-trade research and stricter out-of-sample discipline.
- Re-weighting risk-neutral legs to manufacture positive carry, or highly asymmetric fly weights, is a disguised slope trade. Over-engineered multi-leg trades blur attribution.
- First-order "carry/vol" matrices overstate ratios; use second-order expected P&L and variance with gamma for a ranking across trades.
- Long-only constraints and institutional limits cut returns; factor neutrality needs opposite-sign assets and weights large relative to costs.
- Single-instrument VaR-minimising trades executed together can raise risk (use 50% each, recompute).
- Always say whether an IR/Sharpe is daily or annualised and which sample; the same 60/40 benchmark shows 0.49-0.65 depending on sample.
- Tracking error realism: compare ex-ante with ex-post TE; one check showed ex-ante 0.61% vs ex-post 0.72% (Citi, Aug 2026), so treat ex-ante as a floor, not a forecast.

## Output
Produce, in this order:
1. **Book table**: `package_id`, direction, risk weight (multiple of reference size and DV01 in ccy), stand-alone vol, MCTR, CTR, RRC, correlation to rest of book, signed DV01 by bucket (2y/5y/10y/30y), PC1-PC3 exposure.
2. **Book summary**: sigma_p (daily, ccy and annualised), N trades, N_eff, expected IR with its basis (IC x sqrt(BR) or backtest), net DV01, net PC1, beta to outright duration, stressed-correlation vol, c_book / sum of sleeve c.
3. **Method record**: combiner, covariance window/half-life/shrink, constraints, parameters, trials run (for deflation).
4. **Trade list** vs current `positions` in `trades` form (signed DV01 and notional), with estimated round-trip cost and turnover as % of the cap.
5. **Warnings**: duplicates, hidden directionality, concentrated RRC, thin history, tail-correlation sensitivity; hand-offs to sizing and stress.

## Scripts
[scripts/portfolio.py](scripts/portfolio.py): `risk_decomp`, `effective_bets`, `inverse_vol`, `risk_parity`, `hrp`, `mean_variance` (cap, gross, ridge, turnover cost),
`pca_neutralise`, `var_allocation`, `var_min_trades`, `var_min_subset`, `fundamental_law`, `cov_from_pnl`. CLI: `python scripts/portfolio.py --pnl pnl.csv --method rp|hrp|ivp|mv` (ivp = inverse-vol);
verify with `python -I scripts/portfolio.py --selftest` (known-answer checks: equal-vol uncorrelated gives 1/N, equal correlation gives inverse vol, analytic MV, HRP distances, PC1 projection, VaR identities).

## Related skills
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): shrinkage, EWMA and factor covariance used in step 5
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): loadings, stability and PCA-neutral hedges
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC/IR, orthogonalisation, decay
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): per-trade scores that feed the alphas
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): vol targeting, Kelly, stops
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): shocks and tails on the finished book
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01, key-rate and Jacobian risk
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weights and directionality
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): deflating the best of many tries
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): cost and impact inputs
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): crowding and what would make the book wrong
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables

## References
- Grinold & Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): Fundamental Law, alpha refinement, constraints as modified alphas, turnover frontier, construction comparison
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): MV, max-Sharpe, risk parity algorithms, HRP, robust and resampled portfolios
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): estimation-error loss, partial hedging, factor count, fractional Kelly
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): HRP, Markowitz's curse, PCA risk entropy, deflated Sharpe
- Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): CoVaR, VaR allocation and minimisation, directionality hedging, second-order Sharpe, capital allocation
- Golub & Tilman - Risk Management: Approaches for Fixed Income Markets (Wiley, 2000): PC1 duration, return-space PCA, stepwise VaR, hedge optimisation
- Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): CTR/MCTR decomposition, cost-aware hedging, covariance hygiene
- Quantitative Finance Stack Exchange - "Hedging a trade for PCA component neutrality" (Nov 2019) and "Can PCA be used to transform a ladder of interest rate risk?" (Sep 2023): minimum-norm PC1 projection, Jacobian buckets, subset VaR minimisation
- Huggins & Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): horizon-dependent correlation, PC1-neutral hedge ratios
- Duering - Fixed Income Trading and Risk Management (Wiley, 2021): risk rationing critique, k-factor hedges, neutrality limits
- J.P. Morgan - Investment Strategies No. 31: Exploiting carry with cross-market and curve bond trades (Panigirtzoglou, 11 Jan 2007): theme breadth, constant risk, crowding
- J.P. Morgan - Investment Strategies No. 74: Simple rules to trade duration (Mac Gorain, 2 Oct 2012): signal correlations, equal vs optimised weights, directionality check
- J.P. Morgan - Rule-based Fixed Income Monthly (Mac Gorain, 2 Nov 2012): similar-vol pair choice, JPY bias, signal weights
- J.P. Morgan - Systematic fixed income trading strategies (Inkinen, Bassi, 13 Apr 2015): momentum vs value, 10-market signal correlations
- J.P. Morgan - Update on systematic rule based trading strategies (Gupta, Inkinen, Vijay, 6 Mar and 10 Jul 2017): per-signal vs combined statistics, vol-signal combination
- Nordea Markets - EUR rates: The quiet game (Svendsen, 12 Aug 2025) and How about that outright receiving (26 Sep 2025): pairing carry flies by correlation sign, complementing a crowded steepener
- Citi Research - US Rates Vol Lab: Trading long-dated convexity (Bikbov, Williams, 9 May 2019): long-vol sleeve as diversifier
- BofA Global Research - US Rates Viewpoint: To everything there is a season (Braizinha, Jones, 23 Jan 2022): regime-conditional mean-variance by curve regime
- Macrosynergy - Interest rate swap returns: empirical lessons (Sueppel, 2025): relative vol normalisation, risk-basket beta hedge, cross-market correlations
- Chan - Quantitative Trading (Wiley, 2009): multi-strategy Kelly, half-Kelly, leverage caps
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): neutralisation pipeline, pool correlation, uniqueness
- Narang - Inside the Black Box, 3rd ed. (Wiley, 2024): rule-based vs optimiser construction, blending taxonomy, correlation instability
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): composite sub-models, stock-bond correlation vs core CPI, risk parity vs 60/40
- Citi Research - Global Asset Allocation: House Views August 2026 (21 Aug 2026): relative duration inside a neutral-duration book, ex-ante vs ex-post TE
- Brenndoerfer - Mean Reversion and Statistical Arbitrage (Dec 2025): sqrt(n) Sharpe scaling, correlation spike in crowded unwinds
- Markowitz - Portfolio Selection, Journal of Finance (1952) (external): mean-variance
- Spinu - An Algorithm for Computing Risk Parity Weights (SSRN, 2013) (external): convex formulation and coordinate descent
- Ledoit & Wolf - A well-conditioned estimator for large-dimensional covariance matrices, Journal of Multivariate Analysis (2004) (external): shrinkage covariance
