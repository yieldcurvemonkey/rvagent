# Rates ML case studies: design choices and what happened

These are detailed numbers behind the methodology in [../SKILL.md](../SKILL.md). Every item comes from a cited
document. The desk studies are directional UST and swap-spread models, but their pipeline choices carry over to RV
packages.

## 1. J.P. Morgan - "Do androids dream of electric bonds?" (Salem, Younger, Zhao et al., 22 Nov 2017)

**Task.** The structure and horizon are fixed (1 week or 1 month) and a new trade starts each day. The model chooses
only direction and size. The instruments are:
- the 10y on-the-run UST, financed in overnight repo including specials, held without rolling to a new OTR;
- the 10y matched-maturity swap spread: long the OTR 10y, paying fixed on a PVBP-weighted on-market swap, with carry
  from both legs;
- the 1Mx10Y ATMF straddle, not delta-hedged. A 1-week hold uses the premium change; hold-to-expiry uses payoff minus premium.

**Features.** About 1,250 daily closes:
- UST: yield, fitted-curve error, carry, specialness, MMS and OIS spreads, depth, repo, term premium.
- Swaps and swaptions: realized vol, carry, vol surface, skew.
- OIS, TIPS breakevens, and MBS (basis, hedge-adjusted carry, OAS, OAD, convexity, positioning).
- Cross-asset: credit, equities and vol, FX, commodities, economic and surprise indices.
- Transforms: 1w/1m/3m changes and 3m/6m/1y/2y trailing z-scores.
- Binary date flags for FOMC, payrolls and month-end, which are not normalised.

Continuous variables are de-trended and normalised, then reduced by PCA:
- 10 PCs explain about half the variance on 2008–16 and about 80% on 2000–16.
- About 100 PCs are needed for about 90% on 2008–16.
- The number of PCs is a hyperparameter.

**Samples and CV.**
- Post-crisis sample: mid-2008 to 2016, about 1,500 test days. Long sample: 2000–16, about 3,500.
- Overlapping holding-period returns make the effective sample much smaller.
- Walk-forward CV: each test block is contiguous and follows an expanding train set. The first *n* test days are
  removed, where *n* is the holding period.
- The train window was expanded 4 times, with test blocks of about 1.5 years from early 2010 to 30 Dec 2016.
- 2017 (10 months) was quarantined until final selection.

**Significance via permutation.** Shuffle the predictor's daily sizing decisions 3,000 times at a fixed sell fraction.
Residual Sharpe = predictor Sharpe − permutation percentile, and it acts like a one-sample t-stat. For the 10y UST,
1-week hold, 2010–16:
- the median threshold is about 0.6 all-long, 0.0 at 50/50 and −0.6 all-short;
- the max over 3,000 trials peaks just under 0.95 near a 20% sell fraction;
- in CV, demand results well above the MC max; in quarantine, the 95th percentile is enough.

**Models.**
- KNN: k ≈ 80 beat 10.
- Decision trees: low depth and pruning helped.
- SVM: linear, polynomial, RBF and sigmoid kernels were tried.
- Random forest was the clear winner.
- ANNs were erratic: sensitive to neighbouring hyperparameters and to the random seed.

**Classification and sizing.** A binary rally/sell-off classifier sized as `S = 2P − 1`. Conviction sizing
substantially lifted Sharpe. A buy/sell/hold multinomial added only a little over buy/sell at equal size.

**Balanced vs non-balanced RF.**

| | Balanced | Non-balanced |
|---|---|---|
| Short | 30–40% of the time | low sell fraction |
| Modal conviction | about 50% (timid) | about 56% |
| Sharpe | > 1 | > 1 |

- Conviction tracked the realised hit rate.
- The out-of-sample hit rate saturated near 57% for non-balanced, while Sharpe kept rising through better sizing.

**Results.**
- Random forest on 10y UST: Sharpe > 1.2 in CV.
- 2017 quarantine: balanced RF 1.35 against 0.38 for always-long.
- The best single ANN scored 1.72, but four other ANNs sat near always-long and one was negative.
- RF and RBF-SVM beat the 95th and 99th permutation thresholds; the others did not.
- Typical 10y bid/ask lowers Sharpe by just under 0.1.
- Swap spreads: RF beat the baseline modestly. The baseline is ambiguous: narrowers won historically, while wideners
  are the positive-carry default. Results were above the 95th percentile but within the MC max ("tepid").
- Vol: the non-balanced RF converged to systematic short gamma. Symmetric Kelly sizing suits skewed straddle payoffs badly.

**Vol-strategy metrics for non-linear payoffs.** The average of:
- a non-parametric Sharpe (median / IQR);
- a Sterling-type ratio (median return / median loss);
- a drawdown ratio (returns vs the 5th percentile).

**Red flags.**
- In-sample accuracy near 100% indicates memorisation.
- A "fluke" optimum has no cluster of similar neighbouring hyperparameters.
- Picking the max-Sharpe predictor from a large random spread is the "million dart players" fallacy.

## 2. J.P. Morgan - "TradeRunner" (Salem, Younger, Huang, 16 Aug 2018)

**Setup.**
- UST 2s, 5s, 10s and 30s, each held 5 days on the OTR note with repo including specialness.
- Labels: rally or sell-off by the subsequent 5-day move.

**Models and class weighting.**
- RF vs gradient boosting. GBM starts from a stump that predicts the modal class, then fits successive trees to residuals.
- Class weighting is the key hyperparameter.
- RF sell fraction: 15–20% non-balanced, 40–45% balanced.
- GBM sell fraction: 20–48% non-balanced, 40–52% balanced.

**CV.**
- Train from mid-2008 and test from 2009.
- Drop the first 5 days of each test window, the embargo for a 5-day label.
- About 1.5-year test blocks, expanded 4 times to 30 Dec 2016.
- 2017–18 quarantined.

**Costs.** Time-weighted top-of-book width per year: about 0.4bp in 2s, 0.2–0.3bp in 5s and 10s, 0.1–0.2bp in 30s.

**Results.**
- 10y CV: best GBM Sharpe about 1.1–1.2 against about 1.0 for RF.
- Sell fraction rises out the curve: 30–35% in 2s, about 45% in 10s and 30s.
- In the 2017–18 quarantine:
  - 2y passive Sharpe was about −2.0 with costs, against about −0.8 for the classifiers.
  - Confidence of outperformance was about 70% in 2y and 10y, about 95% in 5y, and 90%+ in 30y.

**Lesson.** A long bias learned in a secular rally fails in a sustained sell-off. Label balance and class weights
drive behaviour more than model choice does.

## 3. J.P. Morgan - "#SquadGoals: stacking and voting" (Salem, Younger, Huang, 21 Sep 2018)

**Setup.** 10y UST with a 5-day hold, `S = 2P − 1`. CV from mid-2008 to 2016; quarantine 2017–18, which includes the
late-2017 to early-2018 sell-off.

**Sample weights by move size** (σ = global std of 5-day 10y moves):
- Gaussian: `w = 1 − (1−b)·exp(−dy²/(sσ)²)`.
- Piecewise: `w = min(1, |dy/(2sσ)| + b)`.
- `b = 1` is uniform; `b = 0` removes zero-move days.
- Lowering `b` raised the sell fraction above 50%.
- `s = 1` (about 10bp) was roughly optimal.
- Profile: symmetric in CV, but generalised worse in quarantine (about 0.2 lower Sharpe).

**Stacking.**
- Twelve constituents: balanced, non-balanced and sample-weighted variants across RF, GBM, linear SVM and logistic.
- A GBM or logistic executive combines them.
- Stacked quarantine Sharpe was up to about 0.5. Significance was > 99% for the stack against 79% for a solo GBM.

**Lessons.**
- Diversity of constituents matters more than the choice of executive. Correlated learners such as GBM and RF add nothing.
- Balanced learners can act as contrarian inputs, and got negative executive betas.
- Leave out erratic learners: KNN, single trees and simple ANNs.

## 4. J.P. Morgan - "Welcome to the machine: NLP of central bank speak" (Lupton, Aitas, Weitzenfeld, 26 Apr 2023)

These are labelling lessons for text features.

**Ordinal labels.** Sentences are scored on a 5-point hawk/dove scale plus "irrelevant". The hawk/dove head is trained
as 4 binary "greater-than" classes: `P(y=1) = 1 − P(y>1)`, `P(y=2) = P(y>1) − P(y>2)`, and so on.

**Active learning.**
- Start from noisy rule labels, then hand-label sentences near 50/50 predicted probability.
- Because deep-net probabilities are poorly calibrated, the team moved to gradient-diversity selection (BADGE).

**Sample size.**
- Out-of-sample log loss fell from about 0.75 with 1,000 labels to about 0.56 with about 4,000. Returns beyond
  4,000 were limited.
- Target: at least 4,000 labelled sentences per central bank.

**Accuracy.**
- Relevance: 83%, flattered by 67% of sentences being relevant.
- Hawk vs dove: 80%.
- All 5 classes: 48%.

**Regimes.** Label both the low-inflation (post-GFC to 2020) and high-inflation (post-2021) regimes, and each bank's
vocabulary. The score-to-rate fit breaks at the ZLB unless you add a ZLB dummy or interaction.

## 5. Hastie, Tibshirani, Friedman - ESL 2nd ed. (2009), Sec 7.10.2

**Simulation.** N = 50 samples, two classes, 5,000 pure-noise predictors.

**Wrong way.**
1. Choose the 100 predictors most correlated with the labels on all the data.
2. Then cross-validate a 1-NN classifier.
3. Result: CV error 3% against a true 50%. The selected predictors kept a correlation of about 0.28 with labels in the held-out folds.

**Right way.** Split the folds first, then screen inside each training fold.

**Exception.** Unsupervised screening, such as keeping the highest-variance predictors, may precede CV.

## 6. López de Prado - AFML (2018), Ch.13: OU exit rules (non-annualised Sharpe from simulated heat-maps)

| Equilibrium | Half-life 5 | 10 | 25 | 50 | 100 |
|---|---|---|---|---|---|
| 0 (market-maker) | best ≈ 3.2: small profit-take, wide stop | lower, regions spread | flatter | flatter | no optimum |
| +5 (position-taker) | ≈ 12, profit-take ≈ 6, stop 4–10 | ≈ 9, profit-take ≈ 5, stop 7–10 | 2.7 | 0.8 | 0.32 |
| −5 (stop-out case) | worst ≈ −12 | ≈ −9 | flatter | flatter | flatter |

Reading: symmetric barriers are near neutral for zero-equilibrium mean reversion. The longer the half-life, the
flatter the surface, and calibrating barriers on history then fits noise. Use the OU fit from
[quant-mean-reversion-ou](../../quant-mean-reversion-ou/SKILL.md) to simulate exits rather than back-fitting them.
