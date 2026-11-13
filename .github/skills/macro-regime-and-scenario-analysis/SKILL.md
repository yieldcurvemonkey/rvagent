---
name: macro-regime-and-scenario-analysis
description: 'Classifies G10 rates regimes (bull/bear steepening and flattening move types, 55-day level regimes, growth/inflation quadrants such as goldilocks and stagflation, analogue and Markov-switching states, max-vol stress switches) and builds probability-weighted scenario trees and outcome maps (soft/hard/no landing, base/bull/bear case) for curve, vol and fair-value trades. Use when a trader asks about regime, scenario, outcome map, what happens if the Fed or ECB cuts or hikes, terminal rate paths, bear steepening, bull flattening, twist, recession or reacceleration odds, analogue years, risk-off or stress switch, or whether a steepener, fly or receiver works across paths. Use for regime conditioning of any curve, swap-spread or vol RV idea. Statistical regime models (HMM, breaks): quant-regime-detection; book shock P&L: port-scenario-and-stress-testing.'
---

# Macro regime and scenario analysis

A relative-value trade is a bet on a spread, and the spread's behaviour depends on the macro state. Regime
analysis labels the state (what kind of curve move dominates, whether yields sit above trend, which cycle phase
the data point to), and conditions every RV statistic on that label. Scenario analysis then writes the macro
paths out explicitly, gives each a probability and a curve, vol and fair-value outcome, and asks which structure
pays across most of them. Regimes are a conditioning tool, not a forecast: the sources report that the predictable
share of monthly bond returns is small and that relationships break when the policy regime changes.

## When to use
- A curve, fly, swap-spread or vol idea whose sign depends on the path of policy (cut timing, pace, terminal rate,
  hike or hold), e.g. 2s10s steepeners, 5s10s30s flies, receivers, 1y-forward curve trades.
- Before trusting an RV signal: is it working in the current regime, or only on average over history?
- Building an outcome map or probability-weighted scenario table for a trade review or book-level risk discussion.
- Choosing a structure that works across several paths, not just the base case.
- Deciding whether a fair-value residual is a regime break (the model is stale) or a real mispricing.
- Cross-asset stress: is risk-off building in rates, vol, oil or credit, and what does energy do to inflation?
- Not for: single-meeting pricing (see stir-policy-pricing-whats-priced-in), macro fair-value model construction
  (see macro-fair-value-models), chart-pattern overlays (see macro-technical-analysis), or a generic macro view with no
  trade consequence.

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap or OIS rates, 2y/5y/10y/30y, forward starts 0D and 1y/5y | `curve_par` | daily, one snap, >= 10y for move regimes; >= 15y for percentiles | rates in pct; convert moves to bp |
| Policy rate and meeting schedule | `rate_fixings`, `cb_meetings` | every decision since the last regime change | regime labels need the reaction function, not only the level |
| Meeting or cut/hike probabilities | `events_probs` | daily | used for the market-implied scenario check |
| Normal vol on expiries/tenors (for vol-regime gates) | `vol_surface` | daily, 1y expiry 10y tail | bp per year; ATM strikes only for gates |
| Macro releases with vintages (inflation, growth, labour, surveys) | `macro_series` | release vintages, >= 10y for z-scores | use `pub_ts_utc`; never revised values before release |
| FX spot and forward points (FX-hedged and USD regimes) | `fx_rates` | daily | needed for hedged cross-market regimes |
| Positioning and surveys | `positioning` | weekly (CFTC, Tuesday as-of) | a crowding gate, not a regime label |
| Cross-asset gauges: equity index, equity vol, oil, credit spreads, financial conditions | `macro_series` (`<CC>-EQ-<INDEX>-TR`, `<CC>-EQVOL-<INDEX>-<TENOR>`, `GL-BRENT-M1`, `<CC>-CREDIT-<GRADE>-OAS`, `<CC>-FCI`) | daily, >= 5y | if the adapter has none, treat as a gap and ask for a daily series |

If an input is missing, ask for it or hand off to the data adapter. Never invent values, and never rebase a
series whose history is shorter than the window you need.

## Method

1. **Frame the question and pick the regime family.** The regime must be able to change the trade's sign.

   | Question | Family | Default |
   |---|---|---|
   | Which kind of curve move is happening? | move-type shares (step 2) | 2s10s, 2 bp floor, 1-month window |
   | Are yields above or below their trend? | 55-day level flag (step 3) | 55 obs, 1-day lag |
   | Which cycle phase does the macro data suggest? | quadrant, analogues or clusters (step 4) | z-scores over 10y; k = 60 months |
   | Latent state with probabilities | Markov switching (step 5) | start with 2 states, filtered only |
   | Is risk-off building across markets? | max-z stress switch (step 7) | 252-day z, cut above 2, re-enter at 2 or below |

2. **Curve-move regime.** For a 2y/10y pair with moves d_f and d_b (bp) over the window:
   - level L = (d_f + d_b)/2, slope S = d_b - d_f
   - bull-steepening: L < 0, S > 0; bear-flattening: L > 0, S < 0; bull-flattening: L < 0, S < 0; bear-steepening: L > 0, S > 0
   - a move with max(|d_f|, |d_b|) below 2 bp is excluded. Willer and Saunders classify on the 2y move alone, count it only
     above 2 bp and only while the 2y is above 1%; the max-of-legs floor and the average-level rule here are house variants
     (the larger-moving leg decides bull versus bear), so their base rates are indicative, not like-for-like
   - report the share of each type over 2 weeks, 1 month and 2 months (10, 21 and 42 daily observations), over directional
     moves only; below about 10 directional moves in a window the shares are noise
   - Fed footprint = share(bull-steepening) + share(bear-flattening): front-end-led moves
   - tail proxies: count only material moves (daily move above the standard deviation of daily moves)
   - conviction (house default) = 1 - H/ln(4), H the entropy of the four shares; 0 when equal, 1 when one type is 100%
   - implemented by `curve_move_regime()`, `move_shares()` and `conviction_from_shares()` in `scripts/regime_tools.py`

   Mapping to drivers (BofA, Understanding the yield curve dynamic, 2025): bull-steepening goes with pricing cuts or a
   hard landing; bear-flattening with pricing hikes or reacceleration; bull-flattening with a late-cycle slowdown while
   the Fed is restrictive; bear-steepening with early-cycle recovery or back-end supply. Use the base rate before
   reading a shift: in the cited US sample (2y above 1%, 2y-based classification), about 36% of counted moves were "off-script"
   (bear-steepening or bull-flattening; Willer and Saunders, Trading Global Macro Markets, 2026).

3. **Level regime (trend).** Flag a driver above or below its 55-day average, lagged one day (two when a leg trades in
   another time zone). Use the 200-day average as the slower trend filter. Name combinations by the source's
   vocabulary: bear steepening (both 2y and 10y above their averages), twist steepening (2y below, 10y above; implied by the source, not printed). The level
   regime is concurrent, not predictive, so use it to condition, not to time. Keep it separate from step 2: a
   bull-steepening move can occur inside a bear-steepening level regime. `above_ma_flags()` implements the lag.

4. **Macro state (cycle phase).** Choose one and check the other two.
   - **Quadrant:** growth (a leading indicator averaged with the ISM manufacturing PMI, a timely unrevised series)
     against G7 CPI, each z-scored on a rolling 10-year window, threshold z = 0. Split recession early or late by
     growth against its 3-month average. Limit: near-trend months are classified almost at random, so do not build a
     trade on a reading close to zero (house default band of 0.25 standard deviations; the sources give no band).
   - **Analogues (kNN):** seven z-scored variables (growth level, inflation level, financial conditions, risk appetite,
     and the changes in growth, inflation and financial conditions). Euclidean distance to every month, keep the 60
     nearest, average their next-month returns. The source gives no kernel; house default is inverse-distance weights.
     Always print the nearest dates. Analogues cluster in recent months, which biases the output toward stickiness. No look-ahead:
     candidates are only months whose next-month return is already known, and z-scores use data up to the decision date.
   - **Clusters:** k-means on the equivalent inputs (ten clusters in the cited model). Clusters persist, and a full
     recession moves next to stagflation or a growth shock. Centroids and episodes are in
     `references/scenario_examples.md`, section 6. Treat cluster labels as a second opinion on the quadrant.
   - Point-in-time data only: use release vintages and publication lags (`macro_series.pub_ts_utc`).

5. **Latent regime (Markov switching).** For a regime-dependent AR(1), y_t = c_s + phi_s y_{t-1} + e_t with a two-state
   chain P (row-stochastic), the filter is
   `xi_{t|t} = (xi_{t|t-1} * eta_t) / sum(xi_{t|t-1} * eta_t)`, `xi_{t+1|t} = xi_{t|t} P`, and the log-likelihood is the
   sum of log(sum(xi_{t|t-1} * eta_t)). Expected duration of regime j is 1/(1 - p_jj) periods. Hamilton's US real GNP
   example (a mean-switching AR(4) on growth, not this AR(1)) gives 10 quarters for expansions (p = 0.90) and 4 for contractions (p = 0.75). Use filtered probabilities
   for any live signal; the smoothed (Kim) probabilities use future data. The standard likelihood-ratio test cannot
   choose the number of regimes; compare specifications out of sample. Implemented by `hamilton_filter()`.

6. **Condition every RV statistic on the regime.** For each candidate trade and each regime label:
   - active information ratio = IR computed over only the days the rule holds a position (Willer and Saunders; their
     return and vol columns are full-period, so IR is not return/vol), against the unconditional IR of the same asset;
   - report "% on" (share of time the rule is active) and max drawdown next to the IR;
   - test a one-day lag. A rule that works contemporaneously and breaks with a one-day lag is not tradable;
   - split into sub-periods and require the sign to hold in each (a single regime is a regime bet, not a signal);
   - rolling percentile thresholds only (12 months, 2 years, 30 years, depending on the series); full-sample
     percentiles leak information;
   - when conditions are combined, require both to improve the IR: two conditions that each add value are stronger
     evidence than one doing all the work.

7. **Stress switch.** For a set of implied-vol or stress gauges (equity vol, bond vol, oil vol, FX vol, credit spreads),
   compute the trailing 252-day z-score of each and take the maximum: `max_z_switch()`. Cut risk when max z > 2, re-enter
   when max z is back at or below 2, hold at least one month for illiquid assets. The max (rather than the average) is
   deliberate: stress can strike in any corner. Use implied vol rather than trailing realised vol for assets whose vol is
   low just before crises (investment-grade credit).

8. **Scenario tree.** Write 3 to 5 mutually exclusive, collectively exhaustive scenarios. Each one specifies:
   - the policy path (dated changes in bp, end level, pace), growth and inflation, and the central bank's reaction;
   - the levels of 2y, 5y, 10y, 30y and the 3y1y forward, and the curve shape;
   - the vol regime (higher gamma, lower intermediate vol, etc.);
   - a probability, with a range, that sums to 1 at the midpoints.
   Then:
   - compute each candidate trade's P&L per scenario (carry and roll included, because scenarios that ignore carry
     over-state the damage of mild paths);
   - probability-weight it, and decompose the view with `scenario_summary()`: duration impact = with-view minus viewless
     expected return = -D * mean(dy)/100, with D the horizon-end duration (not the starting duration); convexity value = viewless minus zero-vol return;
   - when news rules scenarios out, renormalise the survivors with `collapse_probs()`; do not re-weight by hand;
   - pick the structure with the best worst-case over the paths you judge plausible, or the one that is positive in the
     most of them (the source's robust-across-paths method), and state which scenario kills it.

9. **Policy path to swap rates.** Average the one-month forward policy rates: 24 months for a 2y rate, 60 for 5y,
   120 for 10y (an approximation to the compounded rate). Decompose the path: cut timing and pace dominate 2-3y;
   the terminal level dominates 4y and beyond. In Euro-area scenario work, the number of moves and the end point matter
   more than the timing of the first move. A terminal-curve rule for a quick shape (Bassman, Sharp Curve Ahead, 2024): fed funds = inflation target + 50bp, 2y = fed
   funds + 50bp, 10y = 2y + 75bp (a shape, not a forecast).

10. **Fair-value cross-check.** A macro model gives a fair value and a residual. Residual = current minus fair value
    (positive = cheap); z = residual / residual standard deviation estimated over 10-15 years. Read a z of about +/-0.5
    as a tilt, not a signal. A residual that persists while the regressors' relationship changes is a regime break:
    add a dummy and interaction terms for the break, or fit the short and long windows and compare. Do not drop the
    break year silently.

11. **Cross-asset gates.** Use these as filters on an RV idea, not as separate trades:
    - real yield vs breakeven: both up = growth; real up, breakeven down = hawkish central bank; real down, breakeven up
      = stagflation; both down = recession (BofA, Welcome to the real world, 2025). Use a long breakeven to isolate inflation;
    - energy pass-through: about 30bp on near-term year-on-year euro-area HICP per $10 of Brent (JWS Macro, Iran & Front End Rates, 8 Mar 2026);
      rank countries by energy share of CPI before reading an energy-driven move;
    - growth/policy PCA: PC1 above 1.5 with PC2 below zero preceded Treasury rallies in a 2026 study (Citadel
      Securities); treat it as a gate, not a trigger;
    - equity beta: about 2.5bp of yield change per 1% SPX on a three-month regression with R-squared 0.18, so a
      scenario based on equities is a rough mapping only.

G10 differences matter at every step. The reaction function, the energy weight in CPI, the funding plumbing and
the positioning differ by market. See [`references/g10_regime_notes.md`](references/g10_regime_notes.md) for the
USD, EUR, GBP, JPY, CAD, AUD/NZD, SEK/NOK and CHF notes, including the end-point rule (EUR), the oil-keyed scenarios
(GBP), the intervention thresholds (JPY) and the energy-exporter ranking (AUD, NOK).

## Worked examples

**Move-type shares (2s10s, Jul 2025).** Shares of bull-steepening / bear-flattening / bull-flattening / bear-steepening over
two months were 23 / 18 / 33 / 27% (as printed; they sum to 101% by rounding), so the Fed footprint was 41% (BofA, Understanding the yield curve dynamic, 23 Jul 2025).
Over two weeks the bear-steepening share was 44%. A 44% bear-steepening share in two weeks, against a 27% two-month
share, is a short-window shift to confirm over the next month before re-weighting the book.

**Scenario decomposition.** Five equally weighted zeros (1-5y, 3y Macaulay duration, 1y horizon) under bear +100bp, bull -100bp,
neutral, bear-flattener and bull-steepener scenarios (Salomon Brothers, Understanding the Yield Curve Part 6, Nov 1995): expected
return 6.82% with the view, 7.02% viewless, 7.00% at zero vol. The mean yield change is +10bp, so duration impact =
-2 x 10/100 = -0.20% (-20bp; horizon-end duration 2y, not 3y) and convexity value = 0.02% (+2bp). The mild bearish view,
not the scenario dispersion, cost the return. The script self-test reproduces these numbers; our own check: p = (0.5, 0.5),
dy = (20, 0) bp, D = 5 gives a duration impact of -0.5%.

**Probability-weighted fair value.** Regime-conditional averages for a 1y-forward 5s10s30s fly were 24bp on hold after a
cut (70%), 10bp at the start of hiking (21%) and 6bp six months into hiking (9%). Fair value = 0.70 x 24 + 0.21 x 10 +
0.09 x 6 = 19.4bp, against a forward fly at 48bp (Citi, Flying Too High, 20 Dec 2010). Profit target 20bp (the 28bp gap less 8bp convexity cost), stop-loss 10bp (Citi). The weights are market-implied hike-start
timing: 70% no hike before 2012, 21% start of hiking in 2H11, 9% six months into hiking at the 1y-forward date. Show the
fair value's sensitivity to the split: moving 10 points of probability from hold to the start of hiking
lowers the fair value by 0.10 x (24 - 10) = 1.4bp (our arithmetic).

**Bayesian collapse.** Aug 2024 four-door grid midpoints: hard landing 22.5%, soft landing 40%, no landing 35%,
reacceleration 2.5% (BofA, 10y rates and the Monty Hall problem, 6 Aug 2024). A fact that rules out a hard landing
renormalises the survivors to soft 51.6%, no landing 45.2%, reacceleration 3.2% (our arithmetic). The source's
caveat: early hard-landing data can look like a soft landing, so the range bias should lean bullish before a hard
landing is called outright.

**Conditional stress switch.** Holding credit only while the max z is below 2: information ratio 1.11, on 58% of the
time, vs 0.42 for buy-and-hold; above 2 sigma the information ratio was -0.21 (Willer and Saunders, 2026). Treat the
threshold as a default to test in your own sample, not a constant.

## Signals & interpretation
- Move shares: a window's share of one move type more than one standard deviation above its own history is a regime
  candidate. Confirm with the 1-month and 2-month windows agreeing before re-weighting ("one day does not make a trend",
  JPMorgan, Canary in a coal mine, 25 Feb 2020).
- Conviction (house default): below 0.2 is low conviction, act tactically with smaller sizes; above 0.5 supports a
  structural stance. Calibrate the cut-offs to the instrument's own history before use.
- Level regime: use the 55-day flag to filter entries (for example, a rule that only holds JGBs when US rates are below
  their 55-day average had an active information ratio of 0.90 vs 0.28 above it and 0.60 unconditional, Willer and Saunders, 2026). Do not read it as a
  forecast.
- 3m/5y5y inversion (below zero) warns of over-tight policy. The implied 12-month probability of a cycle turn (recession model) was 37-45% at
  the 2019 reading, and a recession followed each time the model probability reached about 40% in three cycles (Citi,
  Vol cycle, steepeners and SOFR, Mar 2019). Use it to change vol and sizing, not as a single-signal trade.
- Inversion to first cut: 2s10s inversions (12.5bp or more) led to a cut within 12 months in 57% of cases, 24 months in 86% (Willer and
  Saunders, 2026). Inversion forecasts cuts better than recessions.
- Front-end moves: regressing 2s10s (bp) on the 2y yield (%) over two months gave slope 52 and R-squared 0.76 in one 2020
  sample (JPMorgan, Canary in a coal mine, 25 Feb 2020): the curve flattens in rallies. A persistent bull steepening that
  breaks this pattern is an easing signal, not flight to quality; confirm it before re-weighting.
- Stress switch: max z above 2 means cut; a max z back at or below 2 is re-entry. The rule keeps exposure on about
  58% of the time in the cited sample.
- MOVE (bond implied vol) regime: a low-vol boundary near 80 usually breaks upward to 125 or more rather than reverting
  to 100 (Merrill Lynch RateLab, Oct 2008). Use it for long-gamma timing, with the data and not the level as the trigger.
- Stock-bond correlation: core CPI below about 2.5% = duration hedges equities; above it, the hedge fails (Willer and
  Saunders, 2026).
- Repricing type: ask where the move happened (front, belly, long end), how (parallel, twist, belly vs wings) and why
  (policy path, growth/inflation, term premium/supply/positioning). A front-end move is meeting risk; a belly move is
  uncertainty; a long-end move is term premium (GMM, STIR application process, Feb 2026).

## Pitfalls
- **Sample size.** Event studies rest on three to five cycles, and many results rest on fewer than 25 events (Willer and
  Saunders, 2026). Report the count and the hit-rate granularity (20% steps at n = 5). Use the result as a prior,
  not a trade.
- **Concurrent is not predictive.** Level regimes and move-type shares are measured over the same window as the
  return. Test them with a lag before using them to predict.
- **Regime shifts change the fair value.** A shift in the perceived speed of recovery or in the curvature of volatility
  changes the model, not just the position. Tuckman (Macro-Awareness in Relative Value Trading, 2003) shows an observed 4bp
  fly that looked cheap against the old fair value of 0 was about 1bp rich against the new model.
- **Relationships break across regimes.** The 5y5y CPI-to-Brent regression fell from R-squared 0.64 to 0.08 after a
  change in Fed communication (JPMorgan, 13 Aug 2026). Refit within the regime; do not extrapolate a regression across it.
- **Macro fair values are linear.** They miss non-linear stress, non-economic buying (QE, large FX-hedged foreign
  pickups) and fiscal regimes with a larger supply beta than history. Add the Fed balance sheet and a global factor, or
  use Bayesian sign priors.
- **Recent-window bias.** Analogues and cluster memberships cluster in recent months, which favours stickiness; a
  Markov regime can be fitted to noise if states are not stable out of sample.
- **Smoothed probabilities use the future.** Kim-smoothed probabilities are valid for history, not for a live signal.
- **Scenario probabilities drift.** In BofA's monthly outcome map, the soft-landing likelihood fell from 70-75% (April 2025)
  to 25-30% (August 2025), and recalibration rose from 5-10% to 40-45% over the same four months. Re-estimate on a
  schedule and show the drift.
- **Forwards are breakevens, not forecasts.** A forward 5s30s that is flat is not a predicted inversion. Check
  whether a flat curve is artificially flat (Bassman, Dangerous Curves Ahead, Feb 2022).
- **Bimodal priced paths.** An average priced path can hide a bimodal distribution. Check the option-implied distribution
  (see [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md)) before reading a 115bp cut as a central case:
  it could be 90% unchanged plus a 10% lottery ticket of deep cuts (Bassman, The Big 'O', 22 Aug 2023).
- **Overlapping windows.** Regime-conditional forward changes over 60 or 120 days sampled daily overlap, so t-statistics from them
  are overstated (the Citadel episode study quotes t = -8.3 at 120 days). Use HAC (Newey-West) errors or one observation per
  episode and state the overlap treatment (Citadel Securities, Out of the Woods?, 2026).
- **Conditional probability trees.** Writing the branches out moved one geopolitical estimate from 15% subjective to 4%; tie
  each probability to dated, checkable conditions and attach an expiry or catalyst (Papic, Geopolitical Alpha, 2021).
- **Passing sub-samples is not proof.** A curve trade whose spread passed all four sub-regime checks still hit its stop
  within weeks (ING, Feb 2020). Treat sub-sample agreement as necessary, not sufficient.
- **Neutral-phase trap.** Once central banks reach neutral, front-end receivers are wrong-way risk: curves that
  oscillate around neutral prove prone to traps. Running meeting risk when a meeting is fully priced is fruitless
  (JWS, Autumn 2025).
- **Stock-bond correlation rule.** The 2.5% core CPI threshold is a rule of thumb. The fitted line crosses zero near 3.1%.
  Do not read the threshold as a constant.
- **Vol-driven degrossing.** In a vol shock, risk-based deleveraging hits exposures regardless of fundamentals;
  cross-sectional betas are distorted in the first week.
- **Scenario P&L must include carry and roll.** Mild scenarios are dominated by carry; an analysis that omits it
  mislabels a robust structure as fragile.
- **Real-yield regime in inflation trades.** Owning a linker is not owning inflation: in 2022 TIPS lost while CPI was
  high, because real yields rose more than nominals (BofA, Welcome to the real world, 2025).

## Output
Return one set of tables per question, with the data gaps listed first.

1. **Regime table.** Date; move-type shares (2w, 1m, 2m) with the Fed footprint and conviction; level regime
   (55-day flags, lag stated); macro state (quadrant or nearest analogue dates, cluster label); filtered regime
   probabilities if Markov switching is used; the cross-asset gates that are on.
2. **Scenario table.** One row per scenario: name, probability (midpoint and range, sum shown), policy path (dated bp
   moves), growth and inflation, 2y/5y/10y/30y levels, curve shape, vol regime, trade P&L in bp including carry and roll,
   and the probability-weighted expected P&L with the duration-impact and convexity-value decomposition.
3. **Probability sensitivity.** Expected P&L of each candidate when the probability of the key scenario moves up and
   down by 10 points, with the other scenarios rescaled.
4. **Structure ranking.** Each candidate structure with its worst scenario, the scenarios where it is positive, and
   whether it is robust across paths.
5. **Invalidation and watch list.** One invalidation condition for the chosen structure (a level, a regime change or a
   data print), and the repricing signal that would change the regime label.
6. **Hand-off.** Pass the scenario table to `rv-trade-idea-writeup` for the trade note, to `port-scenario-and-stress-testing`
   for book-level shocks, and to `rv-devils-advocate` for the pre-mortem. Any number that depends on a model input must
   name the input and its vintage.

## Scripts
- [`scripts/regime_tools.py`](scripts/regime_tools.py): curve-move labels (`curve_move_regime`), rolling shares
  (`move_shares`), conviction (`conviction_from_shares`), 55-day flags (`above_ma_flags`), trailing z and the max-z stress
  switch (`rolling_z`, `max_z_switch`), scenario expectation and view decomposition (`scenario_summary`), Bayesian collapse
  (`collapse_probs`), stationary distribution and expected durations (`stationary`, `expected_duration`), the Hamilton
  filter (`hamilton_filter`) and Gaussian AR(1) regime densities (`ar1_regime_densities`). Needs numpy and pandas only.
  `python scripts/regime_tools.py --curve <wide.csv>` prints move-type counts and latest shares from a wide extract with
  columns `date,y2_pct,y10_pct`. `python -I scripts/regime_tools.py --selftest` runs known-answer checks (hand-computed
  labels, z-scores, the 55-day lag, the stress switch, the scenario decomposition and the Hamilton filter).

## Related skills
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): building and refitting the macro fair values used in step 10.
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): the reaction function behind the policy paths in step 8.
- [macro-technical-analysis](../macro-technical-analysis/SKILL.md): trend and range overlays, which this skill does not cover.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event probabilities for scenario weights.
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): the term-premium and supply branches of the scenario tree.
- [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md): energy pass-through for the oil-keyed scenarios.
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): constraints-based shocks for the stress scenarios.
- [quant-regime-detection](../quant-regime-detection/SKILL.md): HMM and change-point methods in more depth than step 5.
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): rule-based duration and curve signals to condition on regimes.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): what the market already prices, to compare with each scenario.
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): option-implied path distributions for bimodal or skewed scenario weights.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-space (1y1y, 5y5y, 1y-forward fly) trades whose fair value is regime-conditional.
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): real-yield and breakeven regimes behind step 11.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): the structures most often tested across regimes.
- [curve-butterflies](../curve-butterflies/SKILL.md): fly structures tested in scenario tables.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): book-level application of the scenario table.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): where scenario tables land in a trade note.
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): pre-mortem of the regime call and the kill criteria.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): testing regime-conditional rules out of sample.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables named in the Inputs section.

## References
- Ilmanen, Antti - *Understanding the Yield Curve, Part 6: A Framework for Analyzing Yield Curve Trades* (Salomon Brothers, Nov 1995): two-step scenario analysis and view decomposition.
- Hamilton, James D. - *Time Series Analysis* (Princeton University Press, 1994): Markov-switching filter, smoother, EM, durations, GNP example.
- Braizinha, Bruno - *US Rates Viewpoint: Understanding the yield curve dynamic* (BofA Global Research, 23 Jul 2025): move-type shares, Fed footprint, tail proxies, conviction, macro fair value.
- Braizinha, Bruno, Craig, Katie - *US Rates Watch: Monthly rates models: August '25 edition* (BofA Global Research, 4 Aug 2025): four-scenario outcome map, factor momentum, directionality likelihoods.
- Braizinha, Bruno - *US Rates Watch: 10y rates and the Monty Hall problem* (BofA Global Research, 6 Aug 2024): four-door scenario grid, market-implied likelihoods, Bayesian collapse.
- Braizinha, Bruno - *US Rates Viewpoint: Introducing a new UST macro framework* (BofA Global Research, 15 Oct 2024): dynamic-factor macro fair value, residual z-scores.
- Saunders, Alexander and Willer, Dirk - *Global Macro Strategy: Quantitative Framework for Regime Investing* (Citi Research, 29 Oct 2021): quadrants, kNN analogues, backtest conventions.
- Willer, Dirk and Saunders, Alex - *Trading Global Macro Markets* (Wiley Finance, 2026): 55-day regime method, max-vol switch, cycle dating, inversion statistics, stock-bond correlation rule.
- Saunders, Alex, Vo, Vinh - *Quantitative Global Macro Strategy: Regime Model update* (Citi Research, 13 Apr 2026): ten-cluster regime model and centroids.
- Bikbov, Ruslan and Williams, Jason - *US Rates Vol Lab: Vol cycle, steepeners, and SOFR* (Citi Research, 25 Mar 2019): 3m/5y5y cycle indicator, recession probability, post-inversion behaviour.
- Mathai, J. et al. - *US Rates Weekly: All it takes is a little push* (Citi Research, 4 Oct 2019): robust-across-paths trade selection, terminal mapping.
- Mathai, J. et al. - *US Rates Weekly: Deal or no deal* (Citi Research, 10 May 2019): equity-beta mapping, trade outcome maps.
- Arora, Amitabh and Chen, Dan - *Flying Too High: Receive Belly of 1-Year Forward 5s10s30s Fly* (Citi Research, 20 Dec 2010): regime-conditional averages, probability-weighted fair value.
- Citadel Securities - *Global Macro Strategy: Out of the Woods? A More Constructive Outlook for Fixed Income* (25 Aug 2026): growth/policy PCA regime and episode statistics.
- Tuckman, Bruce - *Macro-Awareness in Relative Value Trading* (Lehman Brothers, LMR Quarterly, Oct 2003): regime shifts as model changes, two-factor macro curve model.
- Bassman, Harley (Convexity Maven) - *Dangerous Curves Ahead* (15 Feb 2022), *Sharp Curve Ahead* (25 Jan 2024), *It's Never Different This Time* (29 Jan 2018) and *The Big 'O'* (22 Aug 2023): inversion lead, forwards as breakevens, terminal-curve rule, bimodal priced path.
- Merrill Lynch US Rates Strategy - *RateLab: Implied Volatility: A Measurement of Fear* (7 Oct 2008): MOVE range and low-vol boundary.
- Citi Research - *Quantitative Global Macro Strategy, QIS Corner: Aggregate commodity regime indicators* (20 Aug 2026): volatility-dispersion 2x2 and centroid table (rates transfer is an extrapolation).
- Nordea Markets - *EUR rates: Pushing back* (17 Jan 2024): policy-path scenarios, end point over timing.
- Capleton, Mark, Swiber, Meghan - *Global Rates Viewpoint: Welcome to the real world: Global inflation-linked primer* (BofA Global Research, 22 Jul 2025): real-yield and breakeven regime matrix, owning a linker is not owning inflation.
- J.P. Morgan North America Fixed Income Strategy - *US Treasury Market Daily: Canary in a coal mine* (25 Feb 2020): curve directionality regression and "one day does not make a trend".
- J.P. Morgan Global Markets Strategy - *Monthly Inflation Outlook: A mixed bag of inflation market views* (13 Aug 2026): 5y5y CPI-to-Brent regression split by regime.
- ING Global Markets Research - *Rates Strategy: No rise in rates but position for lower volatility* (4 Feb 2020): regime sub-sample checks that passed before a stop-out.
- JWS Macro (Substack) - *USD & Global Rates Thoughts #2: Autumn 2025* (13 Nov 2025): neutral-phase trap for front-end receivers; Fed-chair scenario map.
- Global Macro Method (Substack) - *STIR (Rates) Application Process (Lite)* (25 Feb 2026): daily repricing diagnosis (front, belly, long end) and invalidation condition.
- Papic, Marko - *Geopolitical Alpha: An Investment Framework for Predicting the Future* (John Wiley & Sons, 2021): decision trees with explicit probabilities, constraints over preferences.
- JWS Macro (Substack) - *#3: Iran & Front End Rates* (8 Mar 2026); *Global Rates Outlook #5: Price Vs. Quantity & A New Era For Central Banking* (10 May 2026); *Central Casting #6.1* (21 Jun 2026); *USD Rates & Fed outlook #1: Summer 2025* (21 Aug 2025): energy pass-through, price-versus-quantity ranking, Fed-institution scenario tree, option-implied recession proxy.
- Citi Research - *Global Macro Strategy: The Messi Theory of Interest Rates* (31 Jul 2026), *No inflation trouble, in a SOX bubble?* (13 Aug 2026), *Our Take on US Treasury Announcement: Buy Gold* (19 Aug 2026), *House Views August 2026: Bessent And The Back End* (21 Aug 2026): 55-day curve regimes, BoJ pricing heuristics, cross-market "one bet", surprise regimes.
- Citi Research - *Quantitative Global Macro Strategy: Regime Model update* (12 Aug 2026) and *How to trade US midterm elections* (14 Aug 2026): extended cluster model, event-study priors.
- Citi Research - *US Rates Weekly: Can Secretary Bessent and Chair Warsh save the curve?* (21 Aug 2026); *Rates Vol Lab: Left-side vols' outperformance* (22 Jun 2021): nearest-analogue distribution, analogue overlay in time.
- Citi Research - *US Rates Weekly: The rocky road to a steeper curve* (18 Jan 2019), *What to expect when you're expecting a turn* (20 Apr 2018), *Time for moderation* (17 Feb 2023); *US Rates Vol Lab: Buying vol for less* (25 Sep 2019): inversion and final-hike event studies, curve-percentile returns.
- Citi Research - *European Rates Weekly: A narrative shift looms* (17 Mar 2022) and *Higher yields are here to stay* (24 Sep 2026): curve-on-vol regressions by 2y regime, steepener correlation regimes.
- Citi Research - *Japan FX: Recent changes in USD/JPY price formation* (15 Jun 2026) and *Japan FX: What are Secretary Bessent's plans to assist PM Takaichi's JPY defense?* (13/14 Aug 2026); *Canada Economics Weekly: More positive growth developments* (21 Aug 2026); *Global Economic Outlook & Strategy: Global Resilience* (20 Aug 2026): regime-break dummies, JPY intervention and political map, CAD pattern, Brent scenarios.
- J.P. Morgan - *Economic Activity Tracking* (14 Aug 2026), *FX Markets Weekly: Currencies amid long-end UST shenanigans* (21 Aug 2026), *Global Fixed Income Markets Weekly* (21-22 Aug 2026): policy path versus market, term-premium and terminal quadrants, 5y5y OIS fair-value regressions.
- Barclays Research - *Global Rates Weekly: The urgency question* (2 Oct 2026): scenario-to-curve-sector mapping.
- BofA Global Research - *US Rates Watch: Fed QT Beyond Taper & Funding Impact* (22 Oct 2021) and *Rates basics: fixed versus float* (24 Apr 2024): QT scenario tree, term rates from a policy path.
- Golub, Bennett W. (ed.) - *BlackRock's Guide to Fixed-Income Risk Management* (John Wiley & Sons, 2023): conditional stress, scenario recipe, plausibility ruler.
- Salomon Brothers - *Understanding the Yield Curve, Part 4: Forecasting U.S. Bond Returns* (Aug 1995): four-predictor excess-return model.
- Nordea Markets - *EUR Rates Flash* (5 Feb 2020) and BNP Paribas - *EUR curve convexity: Lessons from history* (25 May 2021): fair-value cross-checks, episode-study template, seasonality windows.
- Macrosynergy - *Interest rate swap returns: empirical lessons* (web article, data through Feb 2018); During, Alexander - *Fixed Income Trading and Risk Management* (John Wiley & Sons, 2021); Bank of England - *Monetary Policy: Practice Ahead of Theory* (Mais Lecture, Mervyn King, 17 May 2005); Financial Times - *The Long View: Bossing the bond market around never works* (about 22 Aug 2026): shock-type correlation regimes, JGB pivot, anchoring gauges, haven roles.
