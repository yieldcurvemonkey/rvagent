---
name: quant-signal-combination-and-decay
description: 'Measures how well an RV or systematic rates signal predicts (IC and IR by horizon, Newey-West t, quintile spread) and how fast that power decays (IC half-life, best holding horizon, signal persistence vs turnover, smooth-or-difference rule). Combines several signals into one calibrated forecast with correlation-aware, shrunk weights (w = R^-1 IC, alpha = vol x IC x score, orthogonalisation, marginal IC). For fly, curve, spread and basis z-scores, PCA residuals, carry, momentum, value, macro and NLP scores on G10 swaps, bonds, futures and STIR. Use when asked: does this signal work, what is its information coefficient or information ratio, alpha decay, signal half-life, holding period, rebalance frequency, should I smooth or lag the signal, combine carry + momentum + value, signal weights, equal vs optimised weights, is a new signal redundant or additive, orthogonalise, turn a z-score or view into an expected bp move, turnover too high. Ranking RV trade candidates into one score: rv-composite-scoring.'
---

# Signal combination and decay (IC, horizon, half-life, weights)

An RV signal is only worth trading if it predicts the package's forward move. This skill measures that with the
information coefficient (IC) at each horizon. It then measures how quickly the IC decays (the information horizon),
which sets the holding period, rebalance rule and cost budget. Finally it combines several signals into one
forecast whose weights account for how correlated the signals are and how noisy their ICs are. The output is a
calibrated expected move in bp per package, plus the horizon and weights that the composite score and trade write-up
consume.

## When to use
- "Does the 2s5s10s z-score / PCA residual / carry-to-vol signal actually predict? What is its IC at 1w, 1m, 3m?"
- "How fast does this signal decay? What holding period and rebalance frequency? Is a one-day execution lag costly?"
- "Combine carry, momentum, value and the fly z-score into one score. What weights? Equal or optimised?"
- "Is this new signal additive or just the old one again?" (orthogonalise, marginal IC, uniqueness)
- "Turnover is too high. Should I smooth the signal or trade changes in it?"
- "Turn a z-score, or a qualitative 'very bullish' view, into an expected bp move."
- Before [rv-composite-scoring](../rv-composite-scoring/SKILL.md) fixes its weights, and before a signal is promoted
  to a backtest in [bt-backtest-design](../bt-backtest-design/SKILL.md).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Signal values per package | `signals` (`date, strategy_id, package_id, value, zscore, horizon_days`) | decision frequency (daily or monthly); ≥ 3y daily, ≥ 10y monthly | point-in-time: a value dated t uses data known at `snap` on t |
| Unit-package return | derived from `curve_par`, `bond_quotes`, `stir_quotes`, `swap_spreads` or `vol_surface` via the package definition | same dates and snap as the signal | one-period return of the package **always held on the same side**, in bp or P&L per unit DV01 or risk. Never the `pnl` of a strategy that already trades on the signal: its sign is the signal's |
| Package vol | from the unit return | rolling 1y | converts IC × score into bp |
| Round-trip cost per package | from `bid_rate_pct`/`ask_rate_pct`, `bid_px`/`ask_px`, or [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md) | current and stressed | cost hurdle vs expected move |
| Realised strategy P&L (optional) | `pnl` | ≥ 3y | IR decay under delayed implementation |

Schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If an input is missing, ask for it or
hand off to the `rv-data-engineer` agent. Never invent values.

**Conventions.**
- *Orientation.* Every score is oriented so that positive means expected positive unit-package return. Take the fly
  2s5s10s = 2·y5 − y2 − y10 (bp, positive = belly cheap) with a mean-reversion z-score of the fly level. If the target
  is the level change Δfly, use s = −z. If the target is the P&L of the receive-belly package, use s = +z. That
  P&L is ∝ −Δfly: −½·Δfly per unit of belly DV01 with −0.5/+1/−0.5 risk weights. Getting this wrong flips every IC sign and every combination weight.
- *Alignment.* Returns start after the signal date. `delay = 1` counts the period ending t+1 (trade at the close of t).
  `delay = 2` mirrors "signal at close t, execute at close t+1".
- *IC.* Spearman (rank) correlation by default, because it is robust to outlier prints. Use Pearson to calibrate
  vol·IC·score. For small Gaussian ICs, Spearman ≈ 0.955 × Pearson.
- *Units.* Horizon h and half-life are in the signal's periods (business days or months). Annualise IR as
  IR_period·√(periods per year), and state whether that is 252 or 12.

## Method

### 1. IC by horizon (information analysis before any backtest)
For horizons h ∈ {1, 5, 21, 63} business days, or {1, 3, 6, 12} months for monthly signals, with
F_h(t) = Σ_{j=0}^{h−1} r(t + delay + j):
- **Time-series IC, pooled within package** (the timing read). Rank and standardise s and F_h *per package* over time,
  then IC_TS = mean over (t, p) of z̃_s·z̃_F. Also report the median of the per-package ICs.
- **Cross-sectional IC** (the ranking read). On each date, compute the rank correlation across packages, then
  average. It needs ≥ 3 packages per date and has low power in typical RV universes: the internal backtest spec
  flagged even its 16-curve universe as low power.
- **Raw pooled IC.** Do not use it for decisions. It is inflated when packages earn different average returns
  (e.g. belly flies vs long-end pairs), which says nothing about timing (internal backtest spec, Oct 2026).
- **Significance.** Daily-sampled h-day returns overlap, so use a Newey-West t with lag h − 1, or sample every h
  days. The spec used start dates every 5 days with NW lag h/5.
- **Quintiles.** Sort the standardised score into 5 buckets and average F_h in each. Healthy: Q5 − Q1 > 0 and at
  least 3 of 4 steps increasing. Warnings: only the tails predict (lower effective breadth), or the middle buckets
  beat the top bucket (a weak, likely-degrading signal) (Finding Alphas, Ch.13).
- **Stability.** The IC should have the same sign in ≥ 2 of 3 subperiods and in each G10 block (USD, EUR, GBP,
  bloc/Scandi). Cross-market carry pairs ran at IR 0.34 in 1988-95 and 1.33 after 1996 (J.P. Morgan, A cross-market
  bond carry strategy, Mar 2006), so a single full-sample IC hides regime dependence.

Calibration of the numbers (Grinold & Kahn, Ch.10, Ch.12):
- IC tiers: 0.05 good, 0.10 great, 0.15 world-class. An IC above 0.20, or a realised IR above 2, means look for a
  bug or look-ahead first.
- For sign forecasts, IC = 2·hit − 1. A 55% hit rate is IC 0.10.
- SE(IR) ≈ 1/√years and t ≈ IR·√years. Proving IR 0.5 at t = 2 takes 16 years.

### 2. Decay, half-life and horizon
- **IC decay curve.** IC_k = IC(s_t, r_{t+k}) for k = 1..K. Use the *single-period* return k periods ahead, never
  overlapping cumulative returns, which double-count (G-K Ch.13). Fit IC_k = IC₁·δ^(k−1) by non-linear least squares;
  log-linear fits break as soon as a noisy IC_k ≤ 0. Then **half-life HL = ln 0.5 / ln δ**, equivalently
  δ = 0.5^(1/HL). A one-quarter half-life on monthly data gives δ = 0.7937.
- **Implementation-delay version.** Lag the positions by k periods and record IR(k). The IR half-life is the lag
  that halves the IR. Value added ∝ IR², so the value-added half-life is half the IR half-life (G-K example:
  1.2 years for IR, 0.6 years for value added).
- **Best evaluation and holding horizon: h\* ≈ 1.81·HL.** The score's correlation with the cumulative return over h
  is ∝ (1 − e^(−x))/√x with x = h·ln2/HL. It peaks at x = 1.257 with value 0.638, which G-K describe as "about twice
  the half-life". Default the `horizon_days` of the signal to h\*, and set the time stop near 2–3 × HL: by 3 × HL
  the per-period IC is down to 1/8 of IC₁.
- **Persistence vs decay** (this decides smoothing):
  - ρ_s = lag-1 autocorrelation of the score.
  - δ = IC decay per period.
  - δ = ρ_s → use the latest score.
  - δ > ρ_s → average in older scores (smooth): information outlives the score's own noise.
  - δ < ρ_s → subtract part of the older score, i.e. trade the change or innovation, to hedge persistent noise.
  - Two-period version: add the lagged score if IC₂ > ρ·IC₁, subtract it if IC₂ < ρ·IC₁. For example, IC₁ 0.15 and
    IC₂ 0.075 break even at ρ = 0.5.
  - If IC₂ > IC₁, check the package returns for autocorrelation before believing it (G-K Ch.13).
- **Smoothing operators.** decay_linear(x, n) and decay_exp(x, f, n) cut turnover. They raise IR only when δ > ρ_s,
  and they never change the half-life: "attempts to improve the signal using its temporal dimensions ... will have
  little or no effect on the strategy's half-life" (G-K Ch.13). Operator definitions are in
  [references](references/derivations-and-tables.md#6-signal-operators-finding-alphas-ch28-29).
- **Turnover of proportional sizing.** For an AR(1)-like score, mean|Δs|/mean|s| = √(2(1 − ρ_s)) per period
  (derived). A score with a 60-day half-life (ρ_s 0.989) still turns over about 15% of gross per day if sized
  proportionally.
  Use entry and exit thresholds or no-trade bands instead (section 6).
- **Settling old scores.** If the predicted move already happened, the old score is spent. Add last period's
  standardised package return as an extra predictor, or regress the score on past returns and use the residual.
  Momentum scores rise with past returns and value scores fall with them (G-K Ch.13).

### 3. Refine each signal into an expected move
**α = σ_h · IC_h · z** (G-K: "The refined forecast has the form volatility · IC · score"):
- σ_h is the vol of the package's h-day return in bp.
- IC_h is the Pearson IC at that horizon, after shrinkage (section 4).
- z is the *time-series* score of the signal.
- *Cross-sectional scores.* Multiply by package vol only if the signal's dispersion does not already scale with
  vol. Regress each package's signal sd on its return vol; G-K found R² of 0.31–0.77 for vol-proportional signals.
  A z-score already divided by its own vol has time-series sd ≈ 1 everywhere, so α = σ·IC·z is right. A signal
  quoted in bp (PCA residual, carry in bp) already scales with vol, so use α ∝ IC·z_CS and do not multiply by vol
  again.
- *Qualitative or binary views.* Map them to standardised scores before applying IC: very positive / positive /
  none / negative / very negative → +1.73 / +0.87 / 0 / −0.87 / −1.73 at frequencies 0.11 / 0.22 / 0.33 / 0.22 / 0.11
  (G-K Table 19.3).
- *Risk.* Forecasting returns barely changes risk: σ_post = σ·√(1 − IC²), so 18% becomes 17.91% at IC 0.10. Never
  rewrite a correlation because you forecast divergence.
- *Scale and trim.* Check that Std(α) ≈ σ_h·IC_h. Inspect any |α| above 3× that scale: zero it if it is bad data,
  otherwise pull it back to 3× (G-K Ch.14). Choose neutralisations (e.g. to curve factors) a priori, not by trying
  all and keeping the best.

### 4. Combine signals
- **Score level.** For standardised scores z_i with correlation matrix R and IC vector IC at the target horizon:
  **w = R⁻¹·IC**, **IC_comb = √(ICᵀR⁻¹IC)**, and the combined expected move is α = σ_h·wᵀz.
  - Two signals: w₁ = (IC₁ − ρIC₂)/(1 − ρ²) and IC_comb² = (IC₁² + IC₂² − 2ρIC₁IC₂)/(1 − ρ²).
  - Equal ICs: IC_comb = IC·√(2/(1+ρ)).
  - Three equal-IC signals of which two are highly correlated: the correlated pair counts as about one signal.
  - Derivations are in [references](references/derivations-and-tables.md#1-combining-n-standardized-signals).
- **Strategy level.** When only unit-risk strategy returns exist: risk weights ∝ R⁻¹·IR and
  IR_comb = √(IRᵀR⁻¹IR). Independent sources add in squares (IR² = ΣIR_i²). Equal risk weights give
  IR_EW = mean(IR)·√N/√(1 + (N−1)ρ̄).
- **Shrink before weighting.** Multiply each IC by T·IC²/(1 + T·IC²), with T = independent observations ≈ dates/h.
  At 60 monthly observations and IC 0.10 the factor is 0.38; at 36 months and IC 0.05 it is 0.08 (G-K Table 11.4).
  With several signals, use each signal's *marginal* R², which "places a premium on parsimony". Shrink R toward the
  identity with [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md).
- **Default weighting.** Start from equal risk weights. Move to shrunk R⁻¹·IC only if the combined IC beats equal
  weights *out of sample* in [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md). Give extra
  weight to the least-correlated signal: JPM gave carry-to-risk 35%, its largest weight, because it was the least
  correlated signal (J.P. Morgan, Systematic fixed income trading strategies, Apr 2015).
- **Model averaging.** Averaging the predictions of several models (e.g. with Akaike weights) is a conservative
  alternative. It never makes a predictor look more influential than it does in any single model (McElreath,
  Statistical Rethinking, 2016).
- **Orthogonalise.** Regress a new score on the existing pool, plus level/slope/curvature PCs
  ([curve-pca-factor-model](../curve-pca-factor-model/SKILL.md)), carry and the lagged package change. The residual
  is the incremental information.
  - Marginal IC² = IC_comb(all)² − IC_comb(without it)².
  - Uniqueness = max |corr| with the pool. Above 0.7 the signal "will probably not add value" (Finding Alphas,
    Ch.30, pool cap 0.5–0.7).
  - A negative combination weight means the signal is a noise hedge for a correlated stronger signal, not a view.
    Keep it only if it survives out of sample.
- **Regime complements.** Value-type (carry) and momentum returns are typically negatively correlated, in
  government bonds too (J.P. Morgan, Apr 2015, citing Asness et al., 2014; see also Asness, Moskowitz & Pedersen,
  2013), which is why they pair well. Combine signals that work in different regimes. Bond momentum earns in
  rallies and is about zero in sell-offs; equity momentum earns in sell-offs. Without the equity-momentum and revision signals,
  the combined duration signal would have had slightly negative IR in sell-offs (J.P. Morgan, Apr 2015). Measure a
  regime filter as active IR vs the unconditional IR, together with the % of time it is on (Willer & Saunders, 2026).
- **Use as a risk scalar.** Read a combined score in [−1, 1] as a fraction of the risk budget: "a coefficient of
  −0.2 would signal a short of 20% of risk limit" (J.P. Morgan, Systematic rule based trading strategies, Jul 2017).

### 5. Breadth and expected IR
- **IR ≈ IC·√BR** (G-K Ch.6), where BR = independent bets per year. Equivalently IR = IC·√(nT) = √(R²·n·T) for n
  assets over T periods (Paleologo, 2025).
- Back out breadth as BR = (IR/IC)².
- Re-trading an unchanged view is not breadth: "If you reassess your industry bets ... each year, but rebalance
  your portfolios monthly, you shouldn't think that you make 12 industry bets per year" (G-K).
- G10 RV breadth is small and correlated. USD, EUR and GBP structures often share a global factor, so count
  markets after neutralising it.
- Equal market weights overstate what is implementable. JPM equal-weighted 10 markets but noted that the liquid G4
  likely need more weight in practice. Adding NZD and NOK and moving to swap total-return indices lifted the
  combined IR from 1.1 to 1.3 (J.P. Morgan, Apr 2015).

### 6. Costs vs half-life and turnover
- **Amortise cost.** Annualised cost = round-trip cost / holding period in years. A trade worth 2% every 6 months
  vs one worth 8% over 24 months, at 0.75% per one-way trade, nets 1%/yr vs 3.25%/yr (G-K Ch.14).
- **Cost hurdle.** Expected move α = σ_h·IC_h·z must exceed the package round trip by a margin. Short half-lives
  lose twice: they pay more costs, and costs make you "less eager" ("lose by intimidation", G-K Ch.14).
- **No-trade band.** Hold while −sale cost ≤ marginal value added ≤ purchase cost, and trade back to the band edge,
  not the target. Prorating trades keeps ≥ 75% of value added (≥ 87% of IR) at 50% of turnover (G-K Ch.14, Ch.16).
  The slope of that frontier at a turnover cap is the round-trip cost the cap implies: check it against the real cost.
- **Margin.** P&L per unit traded. Low-margin signals add value only if they are very different from the pool
  (Finding Alphas, Ch.4, Ch.9).

## Worked examples
1. **Two forecasts, one asset (exact).**
   - Inputs: return vol 9; IC_g = 3/36 = 0.0833 and IC_g′ = 4/45 = 0.0889; score correlation 5/(4·5) = 0.25.
   - Result: combined IC 0.1090, against 0.1218 if the correlation is ignored (√(IC₁² + IC₂²)). In raw units the
     regression weights are 0.1467 and 0.1307 (Grinold & Kahn, Active Portfolio Management, 1999, Ch.10).
   - Equal ICs of 0.0816 at correlation 0.5 combine to 0.0942, not the 0.1154 an independent pair would give (Ch.6).
2. **G10 duration signals (our computation from published inputs, J.P. Morgan, Systematic fixed income trading
   strategies, Apr 2015).**
   - Inputs: five signals on 10y swaps in 10 markets with IRs 0.59, 0.84, 0.64, 0.66 and 0.59; return correlations
     from −0.42 to 0.62 (carry-to-risk is negative against all four others).
   - Result: √(IRᵀR⁻¹IR) = 1.34 against a published combined IR of 1.31. Equal risk weights give 1.17 and
     independence would give 1.50. The optimal risk weights (about 10/20/20/13/37) sit close to the note's
     15/15/20/15/35.
   - The JPM vol rules (IRs 1.90, 1.68, 1.44, 1.54) combine equal-weighted to 2.45. Inverting IR_EW implies an average
     correlation of about 0.26 (J.P. Morgan, Update on systematic rule based trading strategies, Feb 2017).
   - Combining raised IR even though the combined return (2.1%) was below every component's (2.2–3.8%)
     (Feb 2017 update). The gain came mainly through lower vol and drawdown (Jul 2017 update). Inputs and
     assumptions are in [references](references/derivations-and-tables.md#5-jpm-duration-signals-combination-check-our-computation-from-published-inputs).
3. **IC to IR and implied breadth (Citi Research, Quantitative Framework for Regime Investing, Oct 2021).**

   | Specification | IC | IR | Implied BR = (IR/IC)² (our computation) |
   |---|---|---|---|
   | Levels | 0.0448 | 0.29 | 42 |
   | Changes | 0.0545 | 0.33 | |
   | Levels + changes | 0.0495 | 0.35 | |
   | Full model | 0.0758 | 0.53 | 49 |

   Combining correlated inputs did not raise IC: levels + changes came out below changes alone. The authors score
   forecasts by IC rather than optimiser backtests, which "can be sensitive to small forecast changes, risk models,
   constraints".
4. **Decay in rates.**
   - A central-bank hawk-dove text score predicts 1y yield changes for up to about 8 weeks, and the effect is gone by
     about 13 weeks. A 10-point score rise maps to +14bp on the 90-day change in the US 1y, which halves to +7bp after
     controlling for the lagged rate change. The orthogonalised effect is the tradable one: "the added information
     to current market pricing" (J.P. Morgan, Welcome to the machine: NLP of central bank speak, Apr 2023).
   - Lead-decay profile (bp per 10 points, approx from chart): about 12 at a 1-week lead, 7–9 at 4 weeks, 3–4 at
     8 weeks, about 0 at 13 weeks. That implies a half-life of roughly 4 weeks beyond the 1-week baseline (our
     reading: under exponential decay a fixed-window coefficient decays with lead at the per-period rate).
   - Set `horizon_days` from your own fitted δ on this score, not from the note's rule of thumb.
5. **Processing chain (Finding Alphas, Ch.6, equity illustration).** A 5-day reversal signal improved step by step:

   | Step | IR | Daily turnover |
   |---|---|---|
   | raw | 1.00 | 63% |
   | group-neutralised | 1.37 | 63% |
   | ranked | 1.76 | 59% |
   | 3-day decay | 1.82 | 42% |

   Drawdown *rose* from 5.8% to 7.7% at the decay step even though the text says it fell. Read the table, not the
   prose. The rates analogue: neutralise to curve factors, then rank, then decay.
6. **Expected move (illustrative numbers, not market data).** A 2s5s10s fly has a 63-day change vol of 12bp, a
   shrunk Pearson IC_63 of 0.08, and a fly z-score of +2 (belly cheap).
   - Receive-belly score s = +2, so α = 12 × 0.08 × 2 ≈ 1.9bp of expected fall in the fly (belly richening) over
     63 days. On the −0.5/+1/−0.5 package that is ≈ 0.96bp of P&L per unit belly DV01 (P&L = −½·Δfly).
   - A 0.5bp round trip, quoted in fly bp, uses a quarter of the edge. Keep cost and move in the same units.
   - Size by IR and breadth, not by the size of the z-score.

## Signals & interpretation
- **Promote a signal** when, at the intended horizon:
  - within-package IC > 0 with NW t ≥ 2;
  - Q5 − Q1 > 0 with t ≥ 2 and ≥ 3 of 4 quintile steps rising;
  - same sign in ≥ 2 of 3 subperiods;
  - median per-package IC > 0;
  - each side (long/short) has the right sign.
  Adapted from the Stage A gates of the internal backtest spec, which tests the *pooled* IC at h = 63 and asks for
  per-side |t| ≥ 2; use the within-package IC here, per the spec's own pooled-IC caution. Then run the full checks in
  [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).
- **IC by horizon:**
  - rising then flat → slow information, so hold longer;
  - peaking at h = 1 and decaying fast → short half-life, and costs will dominate;
  - collapsing from delay 1 to delay 2 → suspect bid/offer bounce or stale prints, not information.
- **Half-life** sets `horizon_days` ≈ 1.81·HL, a time stop at about 2–3 × HL, and the re-underwriting cadence in
  [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md). The internal spec exits when the signal decays to 20% of
  its entry threshold.
- **Combination weights:**
  - weight > 0 and marginal IC² > 0 → additive;
  - weight ≈ 0 → redundant: drop it;
  - weight < 0 → hedge: keep only if it holds out of sample;
  - max correlation to the pool > 0.7 → reject.
- **Expected IR** = IC_comb·√BR with honest breadth. Above 2 means an error, not an edge.

## Pitfalls
- **Wrong target.** The P&L of a strategy that trades the signal already carries the signal's sign. Use always-long
  unit-package returns.
- **Pooled IC across packages.** It mixes timing with differences in average return. Read the within-package IC and
  the cross-sectional IC.
- **Overlapping returns.** Plain t-stats on overlapping h-day returns overstate significance by about √h. Use NW
  lag h − 1 or non-overlapping samples. Decay curves need single-period returns.
- **Look-ahead.** Full-sample standardisation is fine for measuring IC but not for a live score: use expanding or
  rolling statistics. Respect publication lags: a SOFR fixing for t is public on t+1, macro releases carry
  `pub_ts_utc`, and CFTC data are released on Friday. A t vs t+1 off-by-one that leaks the next return into the
  score is the classic source of an implausibly high IC (Paleologo, 2025).
- **Price errors masquerade as mean reversion.** A bad print "realises" when it is corrected (G-K Ch.12). Test with
  `delay = 2` and on traded prices.
- **Optimised in-sample weights.** R⁻¹·IC amplifies estimation error when signals are correlated. JPM found
  optimised weights beat equal weights "only marginally". Shrink first, then validate out of sample.
- **Constraints.** Constraints silently shrink the effective IC: a long-only cap cut it by 62% in G-K's example
  (Ch.14). Make the shrink explicit in the alpha rather than hiding it in limits.
- **Secular trends.** A 1998–2015 duration backtest has a bond-bull tailwind: bond momentum was long about 80% of the
  time. Compare the signal's IR with simply being long (combined 1.3 vs 0.84 long G4) before crediting skill
  (J.P. Morgan, Apr 2015).
- **Policy-pinned markets.** Under BoJ yield-curve control, curve signals in JPY stop carrying information. The JPM
  overlay replaced JPY with the next-lowest-carry market (Jul 2017). Expect the same at the zero bound: the hawk-dove
  score's link to rate levels broke there (J.P. Morgan, Apr 2023).
- **Calendar alpha decay.** Signals and models lose power over calendar time. In JPM's 10y Treasury model, the
  version trained to end-2016 reached Sharpe 1.1; retraining through 3Q18 lifted it to 1.27 with no new features
  (J.P. Morgan, Is bank convexity hedging lying in wait?, May 2019). Track a rolling 3-year IC.
- **Data mining.** Twenty informationless signals give a 64% chance that at least one shows t ≥ 2 (G-K Ch.12).
  Log every variant tried and haircut the best one ([bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md)).
- **Mixed units.** Adding a bp signal to a z-score is invalid. Standardise first.

## Output
1. **Per-signal table.** Columns: strategy_id, horizon h, IC_within, NW t, median per-package IC, CS IC, Q5 − Q1,
   quintile steps up, shrink factor, IC₁, δ, IC half-life, h\* = 1.81·HL, ρ_s, score half-life, turnover per
   period, smoothing verdict (smooth / latest / hedge), max correlation to the pool, marginal IC².
2. **Combination block.** Score correlation matrix, shrunk ICs, weights normalised to Σ|w| = 1, IC_comb, equal-weight
   IC, IC if independent, and expected IR = IC_comb·√BR with BR stated.
3. **Per-package expected move.** α = σ_h·wᵀz in bp, set against the round-trip cost.
4. **Write-back.** Write the combined score to `signals` with a new strategy_id (e.g. `combo_<name>_v1`),
   `unit = score`, `zscore` = combined standardised score, and `horizon_days` = h\* converted to days (×21 or
   ×30.4 for a monthly signal; state which).
5. **Hand-offs.** Weights and IC to [rv-composite-scoring](../rv-composite-scoring/SKILL.md); expected move,
   horizon and time stop to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md); IR and breadth to
   [port-portfolio-construction](../port-portfolio-construction/SKILL.md).
6. **Chart.** IC vs lag with the fitted δ curve, plus the quintile bars, via
   [eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md).

## Scripts
- [`scripts/signal_ic.py`](scripts/signal_ic.py) computes:
  - IC by horizon: within-package, cross-sectional, NW t and quintiles;
  - the IC decay fit and half-life, plus h\*;
  - score persistence and turnover with the smooth/hedge rule;
  - IC shrinkage and correlation-aware combination weights with marginal IC².

  Run `python scripts/signal_ic.py --signals signals.parquet --returns unit_returns.csv --strategy a,b --flip a --horizons 1,5,21,63`.
  `--selftest` asserts the Grinold-Kahn worked numbers (0.1090, 0.1467/0.1307, 0.0942, Now/Later 81.5/18.5,
  δ 0.7937, 0.6382 at 1.257, Table 11.4), recovers a planted IC and half-life from simulation, and checks AR(1)
  turnover.
- The script does **not** compute the t-stat on Q5 − Q1, the long/short side split, the subperiod sign check or the
  implementation-delay IR. Do those by hand: rerun on date or side subsets, or use
  [bt-backtest-design](../bt-backtest-design/SKILL.md).

## Related skills
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): builds the raw z-scores and ranks this skill evaluates
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): rule definitions for carry, momentum, value and macro signals
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): consumes the weights, IC and half-life
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): the OU half-life of a *level*, which is not the IC half-life of a *signal*
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): IC shrinkage and hierarchical pooling across markets
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): shrinking the score correlation matrix R
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): orthogonalisation regressions and HAC errors
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): factor-neutralising signals before combining
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): text scores with week-scale decay
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): out-of-sample gates, deflated Sharpe, multiple testing
- [bt-backtest-design](../bt-backtest-design/SKILL.md): signal → position → P&L once a signal passes
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): round-trip costs for the hurdle
- [port-portfolio-construction](../port-portfolio-construction/SKILL.md): IR = IC·√BR at book level
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md): time stops and signal-decay exits
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag and transmission between markets.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): calendar and seasonal effects.

## References
- Grinold, R. C. & Kahn, R. N. - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): fundamental law, vol·IC·score, two-signal and multi-signal refinement, IC shrinkage (Table 11.4), information horizon and half-life, lagged-score diversify/hedge rule, turnover-value frontier, no-trade bands, data-mining guards
- Tulchinsky, I. et al. (WorldQuant) - Finding Alphas: A Quantitative Approach to Building Trading Strategies (Wiley, 2015): signal operators (rank, decay_linear, decay_exp, neutralise), turnover and margin, uniqueness cap 0.5–0.7, quintile shapes, the neutralise → rank → decay chain
- J.P. Morgan (Inkinen, Bassi) - Systematic fixed income trading strategies (13 Apr 2015): G10 duration and cross-market signals, signal-return correlations, weights, equal vs optimised weights, regime asymmetry and long bias
- J.P. Morgan (Gupta, Inkinen, Vijay) - Update on systematic rule based trading strategies (06 Feb 2017): component vs combined IRs for duration and EUR vol rules
- J.P. Morgan (Gupta, Inkinen, Vijay) - Update on systematic rule based trading strategies (10 Jul 2017): combined signal as a risk-budget scalar, IR gains through lower vol and drawdown, JPY override under YCC
- Citi Research (Saunders, Willer) - Global Macro Strategy: Quantitative Framework for Regime Investing (29 Oct 2021): IC horse race of forecast specifications, IC vs IR, preferring IC to optimiser backtests
- J.P. Morgan (Lupton, Aitas, Weitzenfeld) - Welcome to the machine: NLP of central bank speak (26 Apr 2023): 8–13 week decay of a rates signal, effect halving after controlling for lagged rates, zero-bound breakdown
- Internal research spec - Forward curve vs straddle: systematic backtest specification (v0.4, Oct 2026): Stage A IC tests and pass gates, pooled-IC caution, NW lags, signal-decay exit rule
- Paleologo, G. A. - The Elements of Quantitative Investing (Wiley, 2025): IR = IC·√(nT) = √(R²nT), multiple-testing haircuts on ICs
- J.P. Morgan (Panigirtzoglou) - Investment Strategies No. 15: A cross-market bond carry strategy (09 Mar 2006): subperiod instability of signal IRs
- J.P. Morgan (Younger, Salem, St John, Huang) - Is bank convexity hedging lying in wait? (31 May 2019): alpha decay and retraining of a 10y Treasury model, hit rate vs conviction
- Willer, D. & Saunders, A. - Trading Global Macro Markets (Wiley, 2026): active IR of conditioned signals vs unconditional IR, % time on
- McElreath, R. - Statistical Rethinking (CRC Press, 2016): model averaging of predictions as a conservative combination
- Newey, W. K. & West, K. D. - A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix (Econometrica, 1987) (external): HAC t-stats for overlapping-horizon ICs
- Asness, C., Moskowitz, T. & Pedersen, L. - Value and Momentum Everywhere (Journal of Finance, 2013) (external): negative value-momentum correlation across asset classes including government bonds
- Asness, C., Frazzini, A., Israel, R. & Moskowitz, T. - Fact, Fiction and Momentum Investing (Journal of Portfolio Management, 2014) (external): cited by J.P. Morgan (Apr 2015) for the negative momentum-value return correlation
