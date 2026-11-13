---
name: quant-regime-detection
description: 'Detects regimes and structural breaks in rates RV series (curve spreads, flies, swap spreads, ASW, basis, forwards, hedge ratios, realised vol) and turns them into a gate on mean-reversion trades. Covers Markov-switching and hidden Markov models (Hamilton filter, Kim smoother, EM, transition matrix, expected regime duration, MS-AR, switching hedge ratio), rule-based vol and trend regimes (log realised-vol z-score, 55dma, vol x dispersion, rolling-PCA concentration), change-point and break tests (Chow, Wald, sup-F, Bai-Perron, CUSUM, SADF), and the economic size of an equilibrium shift (Tuckman fly index). Use when asked whether a fly, spread or z-score signal is still valid, whether the beta or hedge ratio changed after an event, when a relationship broke, regime probabilities, regime switching, HMM, change point, structural break, break date, mean reversion vs trending, or before trusting a lookback window or a full-sample average. Macro and narrative regimes: macro-regime-and-scenario-analysis.'
---

# Regime detection: HMM, Markov switching, change points

Mean-reversion RV assumes a stable macro regime. Inside a regime a fly or spread reverts to its equilibrium. Across
regimes the equilibrium, the hedge ratio and the vol all move, and a z-score built on the old window reads each
step toward the new level as a cheapening. Tuckman put it as "Relative value trading assumes a stable macroeconomic
environment" and found the trade "nearly always off sides" across shifts (Lehman, Macro-Awareness in Relative Value
Trading, Oct 2003). This skill answers three questions:

1. What state are we in now?
2. Did the relationship break, and when?
3. Is the break big enough to change the trade?

The answer becomes a gate on the RV signal: ON, REDUCE, OFF or RE-ESTIMATE.

## When to use
- "Is the 2s5s10s fly still mean-reverting, or has its equilibrium moved?" "Is this z-score real, or a regime shift?"
- "Did the 5y vs 2s/10s hedge ratio change after the Fed pivot / the end of YCC / the benchmark switch?"
  For a known date, use Chow or Wald. For unknown dates, use Bai-Perron.
- "Are we in a high-vol regime? Should I cut size or stop out?" "Probability we are in the stress state?"
- "Fit an HMM or Markov-switching model to swap spreads or realised vol." "Expected duration of this regime?"
- Before any z-score, OU or cointegration signal: confirm the lookback sits inside one regime.
- To split a backtest's P&L by regime, which is part of validation. Also as a live alarm (CUSUM) on trade residuals.
- For a macro regime (growth/inflation, clusters, analogues), use
  [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md). Use this skill to test
  persistence and breaks in what that skill produces.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| RV series level (fly, spread, basis, ASW, forward) | `signals` (`value`, `unit`=bp) written by the curve/spread skills, or built from `curve_par` / `bond_quotes` | daily, one snap; ≥ 3y (750 obs) for HMM, ≥ 5y for multi-break search | sign convention from the producing skill, e.g. fly = 2·y5 − y2 − y10, positive = belly cheap |
| Underlying rates | `curve_par` (`par_rate_pct` × 100 = bp) | daily, one snap | use changes in bp/day for vol and HMM work |
| Implied normal vol | `vol_surface` (`nvol_bp`) | daily | cross-check the realised-vol regime; always bp vol, never lognormal. `nvol_bp` is bp per year: divide by √252 to compare with realised bp/day |
| Event dates | `cb_meetings`, user-supplied (policy-framework changes, benchmark switches) | dates | candidate break dates for Chow/Wald |
| Macro state variables | `macro_series` (point-in-time vintages) | monthly | only for regime filters on macro drivers |
| Strategy P&L | `pnl` | daily | per-regime performance split |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values. Schemas are in
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Method

### 0. Name the object that can change
| Question | What changes | Tool | Data form |
|---|---|---|---|
| Stress or calm? | variance | vol z-score rule (1); MS mean/variance on Δy (2) | daily changes, bp |
| Has the fly's fair level moved? | equilibrium μ | breaks in AR(1) form (3c); economic test (4) | levels, bp |
| Has the hedge ratio changed? | β of Δ-regression | Chow/Wald at a known date (3a); Bai-Perron (3c); MS regression (2) | changes |
| Reverting or trending? | AR coefficient φ | MS-AR (2); CSW / SADF (3d) | levels |
| How many factors drive the curve? | eigenvalue concentration | rolling-PCA Herfindahl (1) | changes |
| Does an anchor market still drive this one? | R² of factor on anchor | rolling R² plus a break test (Worked example C) | weekly changes |

### 1. Rule-based regime filters (start here: cheap, interpretable, stable)
- **Vol regime.** rv_t = sd of daily changes over 21 days, in bp/day. Then
  z_t = [ln rv_t − mean_504(ln rv)] / sd_504(ln rv).
  - State: high when z ≥ +1 (leave below +0.5); low when z ≤ −1 (leave above −0.5); normal otherwise.
  - Reasons: the log removes the right skew of vol (Citi, QIS Corner: Aggregate commodity regime indicators,
    20 Aug 2026). The 2y z-score window follows J.P. Morgan's high-vol regime definition (For cheap gamma, look to
    the long end, 23 Aug 2019). The 21-day window responds within the typical RV holding period. The hysteresis band
    stops day-to-day flicker. Without it, a reading near a threshold "can just depend on a rounding error", the first
    of Willer & Saunders' three complaints about hard quadrant regimes (Trading Global Macro Markets, 2026).
  - In a stable regime z > +1 on about 16% of days by construction. Use +1.5 (about 7%) for a stricter gate.
- **Break-scale vol check.** Tuckman measured 10y swap vol at 7.3bp/day inside 45-day windows around estimated
  breaks, against 5.2 outside, a ratio of 1.4. So when 21d realised vol is ≥ 1.4 × its trailing 1y median, run the
  break tests in step 3.
- **Trend regime.** A driver is above or below its 55dma, with the signal lagged 1 day (2 days across time zones).
  UST curve regimes come from the 2y and 10y each vs its own 55dma (Willer & Saunders, Trading Global Macro Markets,
  2026; Citi, The Messi Theory of Interest Rates, 31 Jul 2026).
- **Directionality and dispersion.** BofA's 6m curve directionality shares (bull-steep / bear-flat = front-led). A
  vol × dispersion 2x2: aggregate vol vs the cross-tenor or cross-market dispersion of vol-normalised changes.
- **Factor concentration.** H = Σe_i² / (Σe_i)² from a rolling 90-business-day PCA of curve changes (Düring, Fixed
  Income Trading and Risk Management, 2021). A falling H means more factors are moving, and one-instrument hedges
  get riskier.

Recipes, thresholds and published matrices: [references/regime-catalogue.md](references/regime-catalogue.md).

### 2. Markov switching / hidden Markov model
Model: y_t = x_t'β_{s_t} + σ_{s_t}·ε_t. The state s_t ∈ {0..K−1} is an unobserved Markov chain with
P[i, j] = Pr(s_t = j | s_{t−1} = i). Rows are "from" and sum to 1. Hamilton's book prints the transpose, with
columns summing to 1.
- Choices of x_t:
  - x_t = 1 gives a switching mean and variance, the vol regime on Δy.
  - x_t = [1, y_{t−1}] gives MS-AR(1). A state with φ near 1 is trending; a state with φ well below 1 is reverting.
  - x_t = [1, Δx_t] gives a switching hedge ratio.
- **Hamilton filter.** ξ_{t|t} = (ξ_{t|t−1} ⊙ η_t) / 1'(ξ_{t|t−1} ⊙ η_t), and ξ_{t+1|t} = P'ξ_{t|t}, where η_t
  holds the state densities. The log-likelihood is Σ_t ln 1'(ξ_{t|t−1} ⊙ η_t). Start from the ergodic
  probabilities.
- **Kim smoother.** ξ_{t|T} = ξ_{t|t} ⊙ P·(ξ_{t+1|T} ⊘ ξ_{t+1|t}). It uses future data, so it is for diagnosis
  only and never for signals.
- **EM.**
  - p̂_ij = Σ_t Pr(s_{t−1}=i, s_t=j | Y_T) / Σ_t Pr(s_{t−1}=i | Y_T)
  - β̂_j = OLS weighted by Pr(s_t=j | Y_T)
  - σ̂_j² = the probability-weighted residual variance

  Each iteration raises the likelihood (Hamilton, Time Series Analysis, 1994, Ch.22).
- **Chain facts.**
  - Expected duration of state j = 1/(1 − p_jj).
  - Two-state ergodic share π_1 = (1 − p_22)/(2 − p_11 − p_22).
  - m-step forecast ξ_{t+m|t} = (P')^m ξ_{t|t}.
  - Persistence λ_2 = p_11 + p_22 − 1. If λ_2 ≤ 0 the states flip faster than they persist, and they are not
    regimes.
- **Defaults and reasons.**
  - K = 2, at most 3. You cannot test K against K−1 with an LR χ² because the extra state is unidentified under
    the null.
  - Switching mean and variance on daily bp changes.
  - 5 starting values, because the likelihood is multimodal.
  - Floor σ² at 1e-4 × var(y), because the mixture likelihood is unbounded as σ_j → 0.
  - Label states by ascending σ, so state 0 is the calm state. This avoids label switching between refits.
  - ≥ 750 observations, with each state visited at least 3 times.
- **Backtests.** Re-estimate on an expanding window, monthly. Filtered probabilities from a full-sample fit still
  carry parameter look-ahead.
- **Stability check.** Refit on the first and second halves. If σ_j, p_jj or the dated episodes move materially,
  fall back to the rule-based filter. Willer & Saunders (2026) note HMMs "can struggle to estimate out-of-sample or
  across training windows". Chan (Quantitative Trading, 2009) says constant transition probabilities are "useless
  to traders who want to know when ... the transition probability will suddenly peak". Both point to using MS to describe the current state, not to forecast switches.
  Transition probabilities can be made functions of observables (time-varying transition probabilities) when
  switch timing matters.

### 3. Change points and structural breaks
a. **Known date** (policy-framework change, benchmark switch, QT start). Use the Chow test,
   F = [(S* − S1 − S2)/k] / [(S1 + S2)/(T − 2k)] ~ F(k, T − 2k). If the variances differ across the date, which is
   usual, use Wald, W = (b1 − b2)'(V1 + V2)⁻¹(b1 − b2) ~ χ²(k), with HAC V (Greene, Econometric Analysis, 2018).
   For a Kalman hedge ratio, raise the state noise Q at the known date so the filter re-adapts at once instead of
   drifting for weeks (Bentz, in Dunis, Laws & Naim (eds), 2003). Use this only to inject a real event date.
b. **One unknown date.** Use sup-F over [0.15T, 0.85T] with Andrews (1993) critical values, not F tables.
c. **Several unknown dates (Bai-Perron).** Partition the sample to minimise total SSR; dynamic programming gives the
   global optimum.
   - Every regime gets its own coefficients. Minimum regime length h = 0.15T. Pick the number of breaks by BIC or
     by sequential sup-F.
   - Run it on the Δ-regression to date hedge-ratio breaks, as Tuckman did: Δ5y on Δ(3rd Eurodollar), Δ2y and Δ10y
     over about 10 years.
   - Run it on y_t = c + φ·y_{t−1} to date shifts in the equilibrium μ = c/(1 − φ). Do **not** search for mean
     breaks in raw persistent levels with an iid-error criterion: a fly with φ = 0.95 will show spurious breaks.
   - The last h observations cannot hold a dated break. For recent breaks use (a) at a candidate date, or (d).
d. **Online and recent.**
   - Symmetric CUSUM filter on daily changes: S±_t accumulates Δy and fires at |S| ≥ h, with h = 2 × the trailing
     daily sd. The event is a prompt to re-test, not a verdict.
   - Chu-Stinchcombe-White: S_{n,t} = (y_t − y_n)/(σ̂_t·√(t − n)) against √(4.6 + ln(t − n)) at 5% one-sided. A
     breach means the spread has run further than a random walk should, so trending has replaced reversion. Run it
     on y and on −y (sup |S|, about 10% two-sided), because a spread can trend either way.
   - SADF for explosive runs (López de Prado, Advances in Financial Machine Learning, 2018, Ch.2 and Ch.17).

   Full formulas: [references/break-tests.md](references/break-tests.md).

### 4. Economic significance: is the break big enough to matter?
A statistically different coefficient need not change the trade. Use Tuckman's fly index:

    shift_{n+1} = mean(fly over regime n+1) − mean(fly over regime n)

Both means use regime-n hedge weights, and regime 1 = 0. The shift is how far a mean-reversion rule calibrated in
regime n is mis-centred in regime n+1. Compare |shift| with the entry band:
- If |shift| is at least the band (or at least 1 × the regime-n residual sd), the old z-score is invalid. Re-centre
  on post-break data.
- If it is smaller, the break is statistical, not economic. Keep the signal, and note the break in the write-up.

### 5. Gate the RV signal
Combine 1-4 into one decision per trade or candidate (thresholds under Signals & interpretation). Size
asymmetrically, following Tuckman. If the likely regime shift moves the trade's way, it can be full size. If it
moves against, size smaller, or buy option protection for the shift at book level. A desk's RV trades tend to share
one regime exposure. Cut size while realised vol is rising rather than waiting for the high state: Willer & Saunders
"prefer to reduce sizing in fixed income markets when volatility is moving up", and only the extreme vol quintiles
hurt bonds.

## Worked examples
**A. 2s5s10s fly across regimes** (Lehman, Macro-Awareness in Relative Value Trading, Oct 2003).
- Setup: fly = y5 − 0.45·y2 − 0.60·y10 + c, weights from Δ-regressions Jun-1997 to Jun-1999, and c a constant that
  centres the fly on 0. High = 5s cheap. Rule: buy 5s above +5bp, sell below −5bp.
- History: it earned about 5bp a turn to Mar-2001. The same "5s cheap" signal in Mar-2001 then lost about 15bp in
  five months as the fly trended to about +20bp.
- Bai-Perron map: tranquil from early 1996 to late 2000, then several large shifts from late 2000 to early 2003, with
  the fly index stepping to about +15 to +38bp.
- Economic test (Tuckman's stylised numbers): regime 1 averages 10bp and regime 2 averages 4bp, a shift of −6bp,
  larger than the 5bp band. A fly at 7bp in regime 2 reads 3bp rich against the old mean (sell 5s) but is 3bp cheap
  against the new mean (buy 5s). The sign of the read flips, so any move beyond the band trades the wrong side.
- Model view: a faster perceived recovery moves the model fair value of the 34/66 fly from 0 to 4.8bp. An observed
  4bp then looks cheap against the old 0 but is about 1bp rich against the new model.

**B. Reading a fitted chain.**
- Hamilton GNP: p_11 = 0.90 and p_22 = 0.75 give durations of 10 and 4 quarters. Ergodic shares are
  0.25/0.35 = 71% and 29%; λ_2 = 0.65 (Hamilton, Time Series Analysis, 1994, Table 22.1).
- USD/DEM vol switching: σ = 0.6351 vs 0.2486 %/day, p_00 = 0.8049 (high vol), p_11 = 0.6348. The high-vol state
  lasts 1/0.1951 = 5.13 days and the low-vol state 2.74 days. The ergodic high-vol share is
  0.3652/0.5603 = 65%, and λ_2 = 0.44.
- These states flip within days, so they work as an entry or sizing filter, not a regime for a 3-month trade. Even
  so, an EMA(50) trend rule reversed in filtered high vol earned 5.1% p.a. against −1.6%, with max drawdown 10.4%
  against 19.4% after costs (Roche & Rockinger, in Dunis, Laws & Naim (eds), Applied Quantitative Methods for
  Trading and Investment, 2003).
- Monthly macro quadrants: diagonals of 0.88-0.92 give durations of 8-12 months, while 3-month-change quadrants
  (0.73-0.76) give about 4 months (Citi, Quantitative Framework for Regime Investing, 29 Oct 2021). Do not condition
  a 6-month trade on a 4-month regime.

**C. Full-sample statistics hide breaks** (Citi, Decomposing Global Rate Drivers Across EM Asia 5y5y,
13 Aug 2026).
- Weekly Wednesday closes and rolling 52-week PCA, with AUD and NZD in the USD-anchored bloc.
- R²(PC1 ~ USD 5y5y) was 0.59 over the full period, but about 0.47 before the Jan-2023 break and 0.76 after.
- Dropping the pegged HKD cut the full-period R² to 0.24.
- Takeaway: test for a break, and drop mechanically linked series, before using an anchor's beta as a hedge ratio.

**D. Regime-dependent directionality** (Citi, European Rates Weekly: Higher yields are here to stay,
24 Sep 2026). The factor correlation of a EUR 5y5y/10y5y forward steepener was −0.60 when duration cheapened with
rising vol, against −0.14 when duration richened with falling vol. A full-sample hedge ratio is wrong in both
regimes. Condition the hedge on the vol regime, or neutralise the leg that carries the asymmetry.

## Signals & interpretation
| Condition | Read | Action (default) |
|---|---|---|
| Vol z ≥ +1, or filtered Pr(high-vol) ≥ 0.8 (exit ≤ 0.2) | stress state; RV relationships break and de-risking spills over (BofA, Start of rates bite, 2 Oct 2026) | no new MR entries; halve size on open MR trades; stop out spread/steepener trades on a vol regime shift even if the thesis holds (J.P. Morgan, 6 Mar 2020) |
| 21d realised vol ≥ 1.4 × 1y median | break-scale vol (Tuckman 7.3 vs 5.2bp/day) | run 3a-3d now |
| Confirmed break (BIC picks ≥ 1 break in AR(1) or Δ-regression form) inside the signal's lookback | the old mean and hedge are stale | RE-ESTIMATE on post-break data only; no MR trade until ≥ max(60 obs, 3 half-lives) post-break |
| \|equilibrium shift\| ≥ entry band | economically meaningful | re-centre; the old rich/cheap call may flip (Example A) |
| \|shift\| < band and < 1 × residual sd | statistical only | keep the signal; note it in the write-up |
| CSW sup \|S_{n,t}\| > √(4.6 + ln(t−n)), or SADF above its 95% critical value | trending or explosive | OFF for mean reversion; momentum logic only |
| Current state's expected duration < intended holding period | transient state | use it for entry timing only; do not gate the whole trade |
| λ_2 ≤ 0, or states shift between half-sample refits | model not identifying regimes | ignore the HMM; use the rule-based filter |
| Rolling-PCA H falls by > 0.1 vs its 1y average | more factors driving the curve | re-weight hedges (PCA / regression); avoid single-hedge structures |

A filtered probability is a nowcast, not a forecast. Act on a change of state, not on the level of a probability
that has sat at 0.6 for months. The gate thresholds above are house defaults. Validate them with per-regime
backtests, and count every threshold you tried as a trial.

## G10 market notes
- **JPY.** Yield-curve control ran Sep 2016 to Mar 2024, with band changes in Dec 2022, Jul 2023 and Oct 2023. JGB
  vol and curve breaks in that period are policy-administered. Split the sample at those dates instead of fitting
  one HMM across them. The low-vol state was mandated, not a market regime.
- **EUR, CHF, SEK, JPY negative-rate eras** (ECB 2014-22, SNB 2015-22, Riksbank 2015-19, BoJ 2016-24). Front-end
  bp vol was compressed near zero. A 2y log-vol z-score spanning lift-off flags "high vol" mechanically. Condition on
  the policy-rate regime first, and always use normal (bp) vol.
- **Benchmark transitions create fake breaks.** USD LIBOR to SOFR, GBP to SONIA, CHF to SARON, JPY to TONA,
  EONIA to €STR, and CAD CDOR to CORRA (CDOR ceased 28 Jun 2024). Check `data_ok`, `dq_reason` and curve_id switch
  dates before calling a break a market regime.
- **AUD, NZD.** USD anchoring strengthened after the Jan-2023 break (Example C). Cross-time-zone panels need
  weekly mid-week closes, or a 1-day lag, to avoid T/T+1 artefacts.
- **GBP.** The Sep-Oct 2022 LDI episode is a short extreme state. Fit with it, then confirm that the calm state's
  parameters do not move when it is dropped.
- **NOK, SEK, NZD, CHF.** Thinner markets have more stale prints, which create fake low-vol states. Run
  [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md) first.

## Pitfalls
- **Look-ahead.**
  - Smoothed (Kim) probabilities and full-sample break dates use the future.
  - Signals use filtered probabilities from parameters estimated up to t, and breaks dated with data up to t.
  - Rolling thresholds only. Willer & Saunders "avoid like the plague" full-sample percentiles.
- **Spurious regimes in persistent series.** Mean breaks on raw levels, or an HMM on levels of a near-unit-root
  spread, find "regimes" in random walks. Work in changes, or in AR(1) form, and run a random-walk placebo.
- **Statistical vs economic.** With 2,000 daily observations almost any coefficient difference is significant.
  Always report the equilibrium shift in bp against the entry band (step 4). Citi found the JPY anchor statistically
  significant but economically "moderate".
- **Number of states and local optima.** No LR χ² test for K. Restart EM from several starts and floor the
  variances. A state holding < 5% of observations, or with duration < 2 periods, is usually outliers. Fix the data
  instead of adding a state.
- **Label switching.** Order states by σ or by mean on every refit before comparing probabilities across time.
- **Break tests are ex post.** Break dates arrive late, and their confidence bands are wide when the shift is small
  relative to σ/(1 − φ). Bai-Perron cannot date a break in the last 0.15T. Pair it with CUSUM / CSW for live use.
  Power is low for small shifts: in simulation, a 6bp equilibrium shift in a φ = 0.95 fly (innovation sd 1bp) was
  found in 6 of 10 runs, so "no break found" is weak evidence
  ([references/break-tests.md](references/break-tests.md)).
- **Chow under heteroskedasticity.** Regime breaks usually change variance too, so use the Wald form with HAC.
- **Rolling-PCA artefacts.** Sign flips and rank swaps look like regime changes. Sign-normalise the loadings, track
  factors by identity, and cross-check with static loadings (Citi, 13 Aug 2026).
- **Mechanical links.** Pegs, benchmark splices and stale prices inflate or invent regimes. Drop them and re-run.
- **Overfitting the gate.** Each extra filter, threshold or window is a trial. Report the trial count and use
  deflated statistics ([bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md)).
- **"Ten-sigma" framing.** A loss across a regime shift is usually an identifiable macro change, not an unlikely
  random shock (Tuckman). Name the macro driver of each break.

## Output
1. **Regime table**, one row per series or trade:
   `series | as_of | rule_state (low/normal/high) | vol_z | hmm_state | p_high (filtered) | exp_duration_obs |
   days_in_state | last_break_date | break_test (stat, p) | pre_mu_bp | post_mu_bp | mu_shift_bp | entry_band_bp |
   half_life_pre/post | gate (ON/REDUCE/OFF/RE-ESTIMATE) | reason`.
2. **Chart.** Series level with regime shading and break lines, a filtered Pr(high-vol) panel, and the vol z-score
   panel with the ±1 bands
   ([eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md)).
3. **Fitted model card.** P (rows = from), σ and β per state, durations, ergodic shares, BIC, estimation window, and
   whether the half-sample refit was stable.
4. **Hand-offs.**
   - The gate to [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md) and
     [rv-composite-scoring](../rv-composite-scoring/SKILL.md).
   - Post-break re-estimation to [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md) and
     [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md).
   - Regime risk to [rv-devils-advocate](../rv-devils-advocate/SKILL.md) and
     [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).
   - Live alarms to [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md).
   - Persist Pr(high-vol) as `signals` rows with `unit` = `prob`.

## Scripts
- [`scripts/regimes.py`](scripts/regimes.py): numpy/scipy only, no statsmodels needed. It contains:
  - `fit_markov_switching`: EM with the Hamilton filter and Kim smoother. Switching mean, variance or regression
    coefficients, so it covers MS-AR and switching hedge ratios.
  - `vol_regime`: the log realised-vol z-score with hysteresis.
  - `find_breaks`: Bai-Perron dynamic programming with BIC, in mean or regression form.
  - `chow_test` and `cusum_events`.
  - `ergodic_probs` and `expected_durations`.

  The CLI reads canonical `curve_par` or `signals` (CSV/Parquet). On levels, `--model breaks` fits the AR(1) form
  and reports μ, φ and half-life per regime.
  `python scripts/regimes.py --input signals.csv --package-id USD-SOFR:2Y5Y10Y:fly --model breaks`.
  `--selftest` checks:
  - Hamilton's durations and ergodic shares
  - recovery of a simulated 2-state switching regression
  - a simulated vol shift, log-vol z symmetry (vol × 3 vs ÷ 3), and the hysteresis entry/exit rule
  - simulated mean and AR(1)-equilibrium breaks, with a random-walk placebo
  - Chow F against the dummy-interaction F
  - a deterministic CUSUM case

## Related skills
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): unit roots, GARCH, HAC, the general
  break-testing toolkit
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): re-fit half-life and bands inside the current regime
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): lookback choice; z-scores that
  respect breaks
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): rolling and Kalman betas as
  the continuous alternative to discrete breaks
- [quant-cointegration](../quant-cointegration/SKILL.md): threshold and broken cointegration of spreads
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): regime-weighted covariance for risk
- [curve-butterflies](../curve-butterflies/SKILL.md) and [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md):
  the series and factors most often gated
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): macro regimes, clusters and
  analogues
- [ml-models-for-rates](../ml-models-for-rates/SKILL.md): clustering and nearest-neighbour regime alternatives
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): vol-regime sizing
- [bt-backtest-design](../bt-backtest-design/SKILL.md): point-in-time re-estimation and per-regime P&L splits
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): trial counts and deflated statistics
  for gate thresholds
- [macro-technical-analysis](../macro-technical-analysis/SKILL.md): moving-average and ADX trend regimes
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): stale prints, splices and
  benchmark switches that fake regimes
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): shrinkage, priors and Bayesian updating.
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag and transmission between markets.

## References
- Bruce Tuckman (Lehman Brothers, LMR Quarterly) - Macro-Awareness in Relative Value Trading - Oct 2003: Bai-Perron
  on 2s5s10s, fly index for economic significance, vol around breaks, asymmetric sizing
- James D. Hamilton - Time Series Analysis (Princeton University Press, 1994), Ch.22: Markov chains, Hamilton
  filter, Kim smoother, EM, durations, GNP example, testing the number of states
- Roche & Rockinger, "Switching Regime Volatility", in Dunis, Laws & Naim (eds) - Applied Quantitative Methods for
  Trading and Investment (Wiley, 2003): MS-volatility on USD/DEM; vol-filtered trend rule. Same volume, Bentz,
  "Time-Varying Factor Sensitivities": Kalman intervention at a known event
- Marcos López de Prado - Advances in Financial Machine Learning (Wiley, 2018), Ch.2 and Ch.17: CUSUM filter,
  BDE/CSW CUSUM tests, SDFC, SADF/QADF/CADF, sub/super-martingale tests
- Ruey S. Tsay - Analysis of Financial Time Series (3rd ed., Wiley, 2010): MS-AR, TAR, threshold cointegration
- William H. Greene - Econometric Analysis (8th ed., Pearson, 2018): Chow test, Wald test with unequal variances
- Sheldon M. Ross - Introduction to Probability Models (10th ed., Academic Press, 2010), 4.11: HMM forward/backward,
  Viterbi, decoding objectives
- Citi Research (Goh, Garg) - Decomposing Global Rate Drivers Across EM Asia 5y5y - 13 Aug 2026: rolling-PCA anchor
  R², Jan-2023 break, sign normalisation, pegged-market bias
- Citi Research (Saunders, Willer) - Quantitative Framework for Regime Investing - 29 Oct 2021: monthly regime
  transition matrices, persistence
- Citi Research (Saunders, Vo) - QIS Corner: Aggregate commodity regime indicators and systematic carry trades -
  20 Aug 2026: log-vol and dispersion z-score regimes, IR by regime
- Citi Research (Saunders, Rupert) - Model update: A tale of two horizons - 8 Apr 2025: cluster transitions
- Citi Research (Saunders, Vo) - Regime Model update: Selectively adding back risk through regional RVs -
  12 Aug 2026: cluster transition matrix
- Citi Research (Searle et al.) - European Rates Weekly: A QT revolution - 17 Sep 2026: level/slope relationship
  as a high-vol-regime effect
- Dirk Willer, Alex Saunders - Trading Global Macro Markets (Wiley, 2026): critique of quadrants and HMMs,
  early/late recession, 55dma filters, rolling-percentile discipline
- BofA Global Research (Braizinha, Craig) - US Rates Watch: Monthly rates models - 4 Aug 2025: 4-state transition
  matrix
- BofA Global Research (Zhang, Braizinha, Axel) - UST RV Primer - 2 May 2022: curve directionality indices
- Alexander Düring - Fixed Income Trading and Risk Management (Wiley, 2021), Ch.33: rolling-PCA Herfindahl
- Ernest P. Chan - Quantitative Trading (Wiley, 2009): limits of constant-transition MS models; mean-reverting vs
  trending regimes
- J.P. Morgan (Younger, Salem, St John) - For cheap gamma, look to the long end - 23 Aug 2019: 2y z-score of
  realised vol as the high-vol regime
- J.P. Morgan (Younger, Salem, St John) - Impossible to walk in this muck - 6 Mar 2020: stop out spread trades on
  vol regime shifts
- J.P. Morgan (Ozil, Hayward, Alptuna) - Comfortably numb - 24 Jul 2026: regime split of headline sensitivity,
  random-window control
- Citi Research - European Rates Weekly: Higher yields are here to stay - 24 Sep 2026: regime-conditional
  forward-steepener correlations
- BofA Global Research - Global Rates Weekly: Start of rates bite - 2 Oct 2026: vol spike breaking RV relationships
- Citi Research (Pickett, Willer, Saunders et al.) - The Messi Theory of Interest Rates - 31 Jul 2026: 55dma UST
  curve regimes
- Bai, J. and Perron, P. - Computation and Analysis of Multiple Structural Change Models - Journal of Applied
  Econometrics 18 (2003) (external): multiple-break DP and tests
- Andrews, D.W.K. - Tests for Parameter Instability and Structural Change with Unknown Change Point - Econometrica
  (1993) (external): sup-F critical values
- Hamilton, J.D. - A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle -
  Econometrica (1989) (external): the original Markov-switching model
- Phillips, P.C.B., Wu, Y. and Yu, J. - Explosive Behavior in the 1990s Nasdaq: When Did Exuberance Escalate Asset
  Values? - International Economic Review 52 (2011) (external): SADF
