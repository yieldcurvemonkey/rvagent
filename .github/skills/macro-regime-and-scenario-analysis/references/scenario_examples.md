# Scenario analysis: worked examples and outcome maps

Companion to `SKILL.md`. Figures are as printed in the cited source unless marked "our arithmetic" (recomputed
here from the printed inputs). Bp = basis points; returns in percent.

## 1. Two-step scenario analysis and view decomposition

Procedure (Salomon Brothers, Understanding the Yield Curve Pt 6: A Framework for Analyzing Yield Curve Trades,
Ilmanen, Nov 1995):

1. Specify curve scenarios and compute each scenario's return.
2. Assign probabilities and compute the probability-weighted return. The author insists on this second step.
3. From the probabilities, back out the implied mean yield change (the curve view), the implied bp vol (dispersion,
   so the value of convexity) and the implied correlations. Check them against your own views.
4. Decompose:
   - viewless set: subtract the mean yield change from each scenario;
   - duration impact = with-view return - viewless return (use horizon-end duration and the constant-maturity yield change);
   - value of convexity = viewless return - zero-volatility (neutral) return.

Printed example (same source): five equally weighted zeros, 1-5y yielding 6.00-7.00%, 3y Macaulay duration, 1y horizon;
scenarios bear +100bp, bull -100bp, neutral, bear-flattener, bull-steepener return 5.02 / 9.06 / 7.00 / 5.51 / 7.51%, so E[R] = 6.82%.
The implied mean yield change is +10bp. Duration impact = 6.82 - 7.02 = -20bp (= -2y x 10bp, horizon-end duration 2y);
value of convexity = 7.02 - 7.00 = 2bp. Read: the mild bearish view cost 20bp through duration, and the scenario dispersion
added only 2bp of convexity value.

`scenario_summary()` in `scripts/regime_tools.py` implements steps 2 and 4 (its self-test reproduces the printed 6.82 / -0.20 / 7.02 / 0.02).
A horizon-end duration of D years and a mean yield move of ybar bp give duration impact = -D * ybar / 100 (in percent). Self-test case: p = (0.5, 0.5), dy = (20, 0) bp,
D = 5, returns (-1.0, 0.0)% gives expected return -0.5%, duration impact -0.5%, viewless return 0%.

## 2. Market-implied scenario probabilities

Citi (5s10s30s, Dec 2010): back out implied future fed funds rates. Posit tightening cycles starting in staggered
half-year increments, each reaching 3.5% fed funds after two years. A constrained minimisation chooses scenario
probabilities so the probability-weighted fed funds path matches the market-implied path. The output is a
probability distribution the desk can compare with its own view. The source also reports 30%, 42% and 28% market
probabilities for hike starts in 2011, 2012 and 2013.

Probability-weighted fair value of a belly-fly from regime averages (Citi, Flying Too High: Receive Belly of 1-Year
Forward 5s10s30s Fly, 20 Dec 2010):

| Regime (2y path) | Probability | 5s10s30s fly, bp |
|---|---|---|
| on hold after a cut | 70% | 24 |
| start of hiking | 21% | 10 |
| six months into hiking | 9% | 6 |

Fair value = 0.70 x 24 + 0.21 x 10 + 0.09 x 6 = 19.4bp, about 19bp (our arithmetic, matching the source). The
forward fly traded 48bp, above the 98th percentile of the history. Profit target 20bp (the 28bp gap less 8bp of convexity
cost), stop-loss 10bp. The weights map market-implied hike-start timing (30% in 2011, split 9% 1H and 21% 2H; 42% 2012 and
28% 2013 count as on hold) to the regime in force at the 1y-forward date. A 10s30s steepener alternative offered +27bp/a carry against 11bp/a convexity at 120bp/a realised
vol and was rejected (same source).

House rule (our practice, not from the source): a regime-conditional average is a fair value only if the regime
probabilities are themselves defensible. Any shift in the probabilities moves the target. Show the sensitivity to the probabilities
in the output.

## 3. Outcome maps and four-scenario grids

**US outcome map, Aug 2025** (BofA, Monthly rates models: August '25 edition, 4 Aug 2025):

| Scenario | Growth / inflation | Fed | 10yT | 3y1y OIS | Curve | Vol | Likelihood |
|---|---|---|---|---|---|---|---|
| Hard landing | <0% / <=2% | cuts >1 per quarter | 3-3.25% | 1.5-2% | bull steepening, 2s10s to 75-100bp | higher gamma | 15-20% |
| Soft landing | 0-2% / 2% | 1 cut per quarter | 3.75-4% | 3-3.5% | marginally steeper | lowest | 25-30% |
| Recalibration | ~2% / 2% | hold near 4% | 4.25-4.75% | max near 4% | potential bear steepening | slightly higher | 40-45% |
| Reacceleration | — | hold or tighter | max near 5.5% | 4-4.25% | bear flattening (macro), bear steepening (supply) | highest | 10-15% |

Likelihood drift across editions of the same source: Apr 2025 hard landing ~15%, soft ~70-75%, recalibration 5-10%;
May 2025 15 / 45-50 / 20-25 / 15%; Aug 2025 15-20 / 25-30 / 40-45 / 10-15%. The drift is the point: a scenario
probability is a state variable, to be re-estimated on a schedule.

**Four-door grid, Aug 2024** (BofA, 10y rates and the Monty Hall problem, 6 Aug 2024):

| Scenario | Growth / inflation / Fed | 10yT | 3y1y OIS | Curve / vol | Likelihood (range) | Midpoint |
|---|---|---|---|---|---|---|
| Hard landing | growth <0%; inflation <=2%; >1 cut per quarter | ~3% | 1.5-2% | bull steepening, 2s10s to 75-100bp; higher gamma | 20-25% | 22.5% |
| Soft landing | growth 0-2%; inflation 2%; 1 cut per quarter | ~4% | 3-3.5% | inverted for longer, steepening to 0bp; lowest vol | 37.5-42.5% | 40% |
| No landing | growth ~2%; higher for longer | max 5-5.25% | max 4.5-4.75% | bear steepening to flat | 32.5-37.5% | 35% |
| Reacceleration | hikes | max 5.5-5.75% | 4-4.25% | bear flattening | 0-5% | 2.5% |

Midpoints sum to 100%. The source's breakeven-move frequency at the time was 60-65% slowdown vs 30-35% expansion.

**Bayesian collapse** (our arithmetic on the midpoints). A fact that rules out the hard landing removes its 22.5%.
`collapse_probs()` renormalises the survivors: soft 40/77.5 = 51.6%, no landing 35/77.5 = 45.2%, reacceleration
2.5/77.5 = 3.2%. The source's rule: when a new fact rules out scenarios, their mass moves to the scenarios that
remain; reset the range from the survivors. Its caveat: early hard-landing data can look like a soft landing, so
prefer a bullish range bias to calling a hard landing outright.

**Range reset and likelihood sources** (BofA, 10y rates and the Monty Hall problem, 6 Aug 2024). The first Fed cut was
pulled forward to September, a fact inconsistent with reacceleration and partly with no landing, so doors 3 and 4 collapse.
The new 10y range comes from the survivors: top = the soft-landing level (about 4-4.25%), bottom = the midpoint of the
hard-landing level (3%) and the soft-landing level, about 3.5%. Result: range 3.5-4.25%, buy dips in the lower half; a
break below 3.5% needs a hard landing as the baseline. Earlier, with soft and no landing as the baseline, the 10y traded
4-5% and the range midpoint (about 4.4-4.5%) separated expansion-biased periods (most of 1H24) from slowdown-biased ones
(since late May). Likelihood sources: hard landing (20-25%) from the option-implied 10y distribution at end-2024 and the
bull-steepening share of 2s10s moves (hard landing about 20% vs reacceleration about 0%); soft landing (37.5-42.5%) from
the breakeven dynamic. A Sahm-rule reading of about 0.53 was at the level that has historically coincided with recessions.

**Scenario-to-curve mapping (choose a structure that pays in both branches).** Barclays (Global Rates Weekly: The
urgency question, 2 Oct 2026): when duration risks are two-sided but curve risks are asymmetric (the bear case and
the fiscal wild card are 10-30y risks; the bull case benefits the belly and front end), a 1y-forward 2s10s steepener
profits if the economy absorbs higher rates (bear steepening) or inflation undershoots (bull steepening).

**Robust-across-paths selection** (Citi, All it takes is a little push, 4 Oct 2019). Score candidate curve trades on
(a) risk-adjusted returns in full historical easing cycles (six months after the first cut in 2001 and 2007) and
(b) returns in a hypothetical zero-bound path over six months. Keep the structure that works both in "grind to zero"
(25bp steps) and in "fast break" (50bp cuts). The source's chosen trade: a 2y-forward 2s10s steepener, 50k DV01 at
26bp, roll-down about -4.7bp per year, risks bear flattening on a trade truce and bull flattening if the Fed is
tentative. Terminal mapping (1% fed funds by end-2020, zero bound by end-2021): 2y 0.75%, 5y 0.8%, 10y 1.25%, 30y 1.75%.

## 4. Policy-path scenarios and term rates

**Policy-path overlay (EUR, Nordea, Pushing back, 17 Jan 2024).** Three step-function paths against market pricing
(about 207bp terminal at the time): base, one cut every second meeting from June to 2.25% deposit rate (about 215.5
on the reference rate); late, slow, high (September start, every fourth meeting, stop at 3%, about 290.5); early,
fast, low (March start, every meeting, stop at 1.5%, about 140.5). Source findings:

- "For the EUR swap curves, the end point is even more important than the timing of the first rate cut."
- "The number of policy rate cuts is more important than the timing of the first cut or the pace of subsequent cuts."

Trade in the same note: receive the 1y2y/3y2y/5y2y 6s fly at -8bp, target -25bp plus roll, stop +5bp. Carry 79.2bp
per year, 1y realised vol 46.5bp, carry/vol 1.70 (our arithmetic: 79.2/46.5 = 1.70), in-the-money after one year
100% / 59% / 75% / 76% on 1, 3, 5, 10-year history.

**Path vs market (bp change from current; JPMorgan, Economic Activity Tracking, 14 Aug 2026)**: policy rate paths
by central bank, as printed, "JPM / market" at end-3Q26, end-4Q26, end-2Q27, end-4Q27. US from 3.75%: 0/8,
25/22, 25/35, 25/29. Euro area from 2.25%: 25/27, 25/41, 25/54, 0/52. UK from 3.75%: 0/15, 25/36, 0/55, -25/54.
Use the table to check which scenario the market already prices before adding one.

**Term rates from a path** (BofA, Rates basics: fixed versus float, 24 Apr 2024). Build the path of one-month forward
policy rates. Average 24 of them for the 2y rate, 60 for the 5y and 120 for the 10y. Strictly the rate compounds; the
average is the approximation. Decompose the path into cut timing and pace (they dominate 2-3y) and terminal level
(it dominates 4y and beyond). Views to trades: stickier inflation favours paying 2-3y; a terminal rate too high favours
receiving long fixed; agreeing with pricing means no view.

Printed UST scenario outputs (same source), 2y / 5y / 10y / 30y: market 4.93 / 4.62 / 4.60 / 4.73; first cut December
2024 then 25bp a quarter to 3.5%: 5.01 / 4.43 / 4.31 / 4.64; start March 2025 same terminal: 5.28 / 4.80 / 4.69 / 4.75;
terminal +25bp: 5.28 / 4.90 / 4.86 / 4.98; terminal +50bp: 5.32 / 5.05 / 5.06 / 5.21. In 1980-2019 the 5y fixed rate
averaged about 150bp above the realised overnight average.

**Terminal-curve rule** (Bassman, Sharp Curve Ahead, 25 Jan 2024): fed funds = inflation target + 50bp; 2y = fed funds
+ 50bp; 10y = 2y + 75bp. Rotate the curve to that shape and reprice forward-sensitive assets. "Forwards are
breakevens, not forecasts."

## 5. Historical analogues and nearest neighbours

- **Similar-moves distribution** (Citi, Can Secretary Bessent and Chair Warsh save the curve?, 21 Aug 2026). Define
  analogues on the input variables (2y yield, 5y yield, front oil future). Distance = Euclidean on equally weighted
  inputs and their change over the event window. Sample monthly changes since 1990, take the 50 closest, plot the
  distribution of the target (here the 5s30s monthly change) and mark the actual move. A move in the tail is an
  anomaly to explain: the source read a twist steepening as term-premium driven.
- **Analogue overlay in time** (Citi, Rates Vol Lab: Left-side vols' outperformance, 22 Jun 2021): plot today's
  indicator against the same indicator lagged to an analogue event. The 2013 taper analogue put the vol-ratio peak
  about three quarters after the taper started. Trends can run long after the event.
- **Nearest-neighbour call** (Willer and Saunders, 2026; Sep 2025 call): inflation below its 10-year average after a
  surge, growth near trend, loose financial conditions and subdued vol gave analogues 1976-77, the mid-1980s and
  2010-12, implying an equity-positive setting that "played out".

## 6. Cluster centroids (regime model, standardised inputs)

Columns: inflation, leading indicators, CPI 3-month change, leading-indicator 3-month change, cross-asset vol,
financial conditions, financial-conditions 3-month change (Citi, Quantitative Global Macro Strategy: Regime Model
update, Apr 2026; Citi, QIS Corner: Aggregate commodity regime indicators, 20 Aug 2026).

| Cluster (n months) | Infl | LEI | CPI 3m | LEI 3m | X-vol | FCI | FCI 3m |
|---|---|---|---|---|---|---|---|
| Normal (162) | 0.27 | 0.26 | 0.11 | 0.03 | -0.68 | -0.60 | 0.00 |
| Recovery (128) | -1.09 | -0.33 | -0.16 | 0.00 | -0.39 | -0.85 | -0.09 |
| Goldilocks (113) | -1.19 | 1.35 | 0.16 | 0.27 | 0.21 | -0.39 | -0.02 |
| Growth shock (63) | -0.23 | -1.44 | -0.11 | -0.48 | 0.22 | 0.09 | -0.10 |
| Tightening fin. cond. (58) | 0.49 | -0.37 | -0.02 | -0.18 | 0.28 | 1.22 | 0.46 |
| Stagflation, no Fed (27) | 2.43 | -0.86 | -0.31 | -0.07 | 1.73 | 0.32 | -1.06 |
| Stagflation with tightening (24) | 2.35 | -1.30 | -0.20 | -0.70 | 1.63 | 3.39 | 1.43 |
| Inflationary boom (24) | 3.14 | 0.90 | 1.14 | -0.21 | 0.05 | 0.13 | 0.55 |
| Recession (17) | -2.25 | -0.67 | -1.05 | 1.50 | 1.40 | 1.16 | -1.67 |
| Financial market shock (15) | -1.08 | 0.98 | 0.01 | -0.22 | 3.72 | -0.12 | 0.20 |

Current state (Aug 2026, same source) maps to "Normal", in which the model was overweight equities and commodities
and underweight bonds and credit. Episodes: Normal 2024 and 2017-18; Recovery 2002-04 and 2013-15; Growth shock
1990-91, 2001-02, 2018-19; Tightening financial conditions 2000, 2023, early 1980s; Stagflation with tightening 2008
and 2022; Recession 1982, 2009, 2020.

## 7. Stress and shock-based scenarios

**Conditional stress** (Golub, BlackRock's Guide to Fixed-Income Risk Management, 2023). Shock K core policy factors
and imply the other M-K by regression, r_j = sum_k beta_jk r_k + e (eq. 5.1), betas taken from the covariance
matrix. Linear P&L = sum_k L_k S_k + sum_j L_j sum_k beta_jk S_k (eq. 5.2). Fully revalue optional positions.

**Five-step recipe** (same source): (1) define the event: small but not impossible probability, a precise definition,
predictable market impact, clear catalyst; (2) pick parsimonious policy variables, never adding one whose adjusted
R-squared against those already chosen exceeds 90%; (3) size shocks from analogue periods or a target exceedance
frequency; (4) imply non-policy shocks with a scenario-consistent matrix; (5) compute P&L.

**Plausibility ruler** (same source): score each scenario's z and Mahalanobis distance against reference scenarios
(examples in the source: remain 1.2, soft Brexit 1.5, adverse Brexit 3.5). A correlation z above 1 means inconsistent
signs.

Worked stress numbers (same source): a trade-tension shock (June 2018) with US 10y -35bp, Mexico 10y +80bp, US 10y
breakeven +20bp, China equities -20% (3 sd) implied UK 10y -30bp, German 30y -24bp, Japanese 10y -4bp, Spain 5y +15bp,
Italy 5y +59bp. A soft-Brexit stress (23 Feb 2016 analogue): FTSE -5%, GBP 10y -10bp, GBP 2y -25bp, GBP/USD -5%, UK
credit +20bp, Z 1.5, Mahalanobis 4.5 implied UST 10y -9bp, German 30y -19bp, JGB 30y -13bp, EUR/USD -2.9%, Italy 5y
+7bp. Inflation stress: +30bp monthly US 10y breakeven (about 1% probability on the 10-year history) costs a
10-ETF bond portfolio 96bp; allowing 22bp of tracking error cuts the loss by 16bp.

**Equity-beta mapping** (Citi, Deal or no deal, 10 May 2019). With about 2.5bp per 1% SPX, SPX falling from 2870 to the
200-day average of 2775 (-3.3%) implies about 8bp of further yield decline (our arithmetic).

**Shock-type correlation regimes** (Macrosynergy, Interest rate swap returns: empirical lessons; data through Feb 2018):
inflationary or monetary shocks give positive correlation of risk and duration; growth and financial-system shocks
give negative. Betas show "pronounced seasons", so re-estimate the shock mix before using a historical beta.

## 8. Cycle, scenario-tree and policy-regime examples

**QT scenario tree** (BofA, Fed QT Beyond Taper & Funding Impact, 22 Oct 2021). Branches: no QT, Q4 2023 QT start, early
2023 QT start. Funding spread paths (EFFR-IOER / SOFR-IOER, bp):

| | No QT | Q4 2023 QT | Early 2023 QT |
|---|---|---|---|
| Dec 2023 | -3 / -6 | -3 / -5 | -1 / -2 |
| Dec 2024 | -2 / -4 | 0 / 0 | 1 / 3 |
| Dec 2025 | -1 / -2 | 2 / 5 | 3 / 9 |
| Dec 2026 | 0 / 1 | 5 / 12 | 6 / 17 |

Method: project reserves and the ON RRP per branch, then push the paths through regime-specific funding-spread
regressions. Caps of $40bn a month Treasuries and $30bn a month MBS. Early-QT effects: a steeper curve (term premium
and supply), wider MBS-UST, risk-asset headwinds, more volatile dollar funding.

**Structural scenario tree on Fed institutional change** (JWS, Central Casting #6.1, 21 Jun 2026). Radical hard-money
change: stronger USD, flatter curve. Radical but messy (no Fed put): term premium and vol up, curve steeper. Dovish
(trimmed-mean inflation target, nominal GDP targeting, "just behind the curve"): steeper curve, weaker USD. The
source's guide: "count votes not dots."

**Fed-chair scenario map** (JWS, USD and Global Rates Thoughts #2, 13 Nov 2025): one nominee view implied the front end
lower, the back end higher, a steeper curve and a weaker USD (terminal 2.5-3.25%). The other implied the front end
mildly higher, the long end lower, a flatter curve and a stronger USD (terminal 2.75-3.5%). Map each candidate to
its signed curve and USD outcome before the decision.

**Oil scenario rules** (JWS, Iran and Front End Rates, 8 Mar 2026; JWS, Global Rates Outlook #5, 10 May 2026; Citi,
Global Economic Outlook, 20 Aug 2026):

- rule of thumb: about 30bp on near-term year-on-year euro-area HICP per $10 Brent move;
- a Brent level of about $110 is where euro-area HICP breaks 3% (same source); scenarios for the ECB: baseline about $75,
  adverse about $92, severe $115-120, with the response non-linear;
- Brent above $100 means downside growth and upside inflation; a sustained reopening (at or below $80) means growth up
  and inflation down (Citi, Aug 2026);
- energy-weight screen: rank countries by energy share of CPI (the beta of CPI to energy). Global average about 10%;
  Switzerland, Australia and Norway near 5%. Residual of the market move vs fundamental beta is a positioning signal.

**Second-round checklist for an energy shock** (JWS, Iran and Front End Rates, 8 Mar 2026): (1) FX pass-through
(terms-of-trade shock: short energy importers, long producers; the FX divergence emerged about one month after the
shock once risk stabilised); (2) fiscal response (tax cuts, price caps, cash support mean more issuance and pressure
on asset-swap spreads); (3) activity hit (direction negative, size unclear).

**Price vs quantity** (JWS, Global Rates Outlook #5, 10 May 2026): who absorbs a supply shock through prices and who
through quantities, and what the central bank must do. Domestic variables: labour tightness and wage catch-up
(tight means price, real-wage compression means quantity), household balance sheets, corporate pricing power,
fiscal cushioning (less quantity now, more price risk later), and the reaction function and credibility. External:
free-float FX, current account, reserves and net energy import position. The source ranks AUD and NOK toward price
and CAD, NZD and SEK toward quantity.

**Growth/Policy PCA regime** (Citadel Securities, Out of the Woods?, 25 Aug 2026): principal components on a range of
cross-asset inputs; PC1 is a growth factor, PC2 a monetary-policy factor. PC1 above 1.5 with PC2 below zero (growth
priced high, policy benign) preceded meaningful Treasury rallies, especially near the top of the cycle range. In 64
comparable episodes since 2003, yields fell on average 12bp over 60 days and 25bp over 120 days, lower in 71% of
episodes. With yields above 4.5%, 16 episodes averaged -48bp (60d) and -67bp (120d). Small conditional samples:
state the overlap treatment in any t-statistic.

**Real-yield vs breakeven matrix** (BofA, Welcome to the real world: global inflation-linked primer, 2nd ed., 22 Jul 2025):
real yield up with breakevens up = high growth (linkers outperform, nominal returns negative); real up with breakevens
down = hawkish central bank (nominals outperform); real down with breakevens up = stagflation (linkers outperform); real
down with breakevens down = recession (nominals outperform). "Owning a linker is not the same as owning inflation."
Use a long breakeven to isolate inflation. Prefer real-rate swaps to cash real yields when swap-spread distortion is
large (Barclays, Global Rates Weekly, 2 Oct 2026).

**Event-study priors** (Citi, How to trade US midterm elections, 14 Aug 2026): cumulative change in the Treasury
2y, 10y, 30y, 2s10s and 5s30s over plus or minus 125 business days around the event, conditioned on the outcome type.
Treat the history as a prior to update with current information. Samples are small.

## 9. Regime shifts as model changes (Tuckman, 2003)

Two-factor model: rates = long-lived factor (long-run real rate plus inflation) + business-cycle factor, ignoring
risk premium and convexity. A change in the long-run level is a parallel shift; a change in current conditions is
mostly front-end and flattens. Printed 2s5s10s fly, 34/66-weighted (fly = y5 - 0.34 y2 - 0.66 y10, positive = 5y cheap; not the 2/-1/-1 weighting) (Tuckman, Macro-Awareness in Relative Value Trading, Oct 2003):
base 2.971 / 3.952 / 4.460% with fly 0; long-run +50bp fly 0; current weakness +100bp fly 0; faster perceived recovery
fly +4.8bp. An observed 4bp fly looks 5s-cheap against the old fair value of 0 but is about 1bp rich against the new
model. The regime shift changed the fair value, not the trade.

Recovery half-life from a term-structure model (same source): 4 Sep 2001, short rates expected to rise from 3.50% to
4.50% (halfway to 5.50%) in about 1.5 years; 23 Mar 2003, about 3 years for 1.25% to 2.75% (halfway to 4.25%).

Fly regime map, USD 2s5s10s (same source): mild shifts before early 1996; tranquil from early 1996 to late 2000; large
shifts from late 2000 to early 2003. A mid-1999 "5s cheap" rule plus or minus 5bp made about 5bp per turn in 1999-2001,
but a March 2001 long 5s lost about 15bp over five months. Stylised regimes with means 15, 35 and 25bp leave a
mean-reversion trader "nearly always off sides".

## 10. Trend-follower (CTA) flow branch

Sources: BofA, More CTA Models = Better Impact Estimates (2 Jun 2025) and BofA, CTAs impact on the rates market
(18 Aug 2020).

**Bottom-up replica (2025 source).** The four parameters that matter are the investment universe, the trend lookback,
the sizing rule and the stop-loss rule. The replica that tracked a trend-follower index best used a broad cross-asset
futures universe, a medium-term lookback, risk-parity sizing and a moderately aggressive stop. Output is a z-score
allocation per market (absolute sizes are not published; the cap per asset in the model is 10%).

| Item | Rule |
|---|---|
| Short-term trend | collection of moving-average crosses from 21 to 100 trading days |
| Long-term trend | crosses between 50 and 252 trading days |
| Medium-term | equal weight of the short and long windows |
| Stop | a prescribed loss from the high-water mark closes the position entirely; the level barely changes long-run performance because stops are rare and trends reverse anyway |
| Ensemble | 3 lookbacks x 4 stop thresholds = 12 models (thresholds not given in the source) |
| Sigma move | daily return / prior-day EWMA vol (lambda 0.97), de-annualised |
| Correlation to the index | EWMA, lambda 0.97 |
| Projected paths | bear / median / bull = 2.5th / 50th / 97.5th percentile of historical 5-day return paths at current vol; show only the unwind triggers inside the path |

Findings to reuse:
- Impact is largest when the average allocation is stretched and similarly positioned across lookbacks, and a reversal
  trips many stops together. The biggest flows come from unwinds, not accumulation.
- Count rule: 4 or more of 12 models stopped out on the day means an above-average absolute sigma move, shown for equity
  index futures (S&P 500, EURO STOXX 50, Nikkei), 10y Treasury futures, Bund futures, crude, gold and three FX pairs
  (2010 to May 2025). Three stop-outs came with large moves but not reliably.
- Equity case: of the 15 largest one-day sigma declines since 2010, 9 coincided with stop-loss unwinds and the 3 largest
  coincided with consensus longs stopped out across models. The exceptions (Aug 2011 downgrade, Covid, April 2025) were
  fundamental stress; April 2025 was the only one with no unwind contribution.
- Regime drift: before 2013 the short-term model correlated more with the index; since then the long-term model has been
  more stable, so trend followers shifted to longer lookbacks. The medium-term model correlates highest and most stably.
  Of 14 listed managed-futures funds (correlation to the index at least 0.7, about 13bn USD), 10 were most often closest to
  the medium-term model. After 3 Apr 2025 the long-term model correlation rose, the short and medium fell, and the average
  pairwise model correlation hit its second-lowest on record (dispersed positioning).
- Worked case, 30 May 2025 (equity index): trend followers long across models, largest from the medium model; unwind range
  5200 to 4963; in the bearish path 3 of 12 models (2 medium, 1 short) would stop out, below the 4-model rule.
- Scale: trend-follower hedge-fund AUM 339bn USD (2024 Q4), gross notional often above 3x AUM.
- Monitor a range of lookbacks and stops: the medium model alone may suffice for monitoring, the consensus of all gives
  conviction.

**Top-down replica of duration and curve bias (2020 source).**
1. Cluster assets to a representative set per class (equities, longer-duration bonds, shorter-duration bonds, metals,
   energy, FX), because assets in a cluster carry overlapping information. Use assets, not broad benchmarks (too broad,
   rebalancing rules interfere, hidden long/short bias).
2. Take only the first principal component of each set as the feature (higher eigenvectors are unstable). For FX the dollar
   index replaced the FX component: average R-squared 66% on 2-month windows since 2015.
3. Rolling OLS of the index return on the 6 features over 2 months; project the feature betas back to assets through the
   inverse PC1 transform.
4. Read: long-duration beta = duration bias; long-duration beta against short-duration beta = curve bias (long the long
   feature and short the short feature = flattener). Long-duration betas are more stable; short-duration betas depend on
   the policy path. Flow signal = weekly change in betas (duration first order, curve second order). Beta z-score against
   the average 3-month beta.
5. Validate: correlation with a multi-crossover momentum signal is significant for the equity index, 10y and crude, lower
   for gold and lowest for the dollar, with a lead/lag of 15-20 days; the 10y beta trend correlated about 60% with net
   non-reportable 10y futures positions and about 20% with other reportable; levels and long/short implications do not
   match.

History as regime labels (same source): 2016 long duration plus flatteners (Fed tightening while the neutral rate was cut),
then steepeners after the US election (fiscal easing); 2019 flattening bias (neutral-rate downgrade); early 2020 betas
decayed in the dash for cash (Treasuries and gold sold), which supports a short window; in Aug 2020 a long-duration bias
since February, longs built in the week of 10 July and lightened in early August, flattening bias peaked 24 July. Limits:
the index has survivorship bias, and more diverse models limit what a top-down average can capture.

## 11. Futures CTD scenario grid and the wild card

Source: BofA, Primer: US Treasury futures and basis (10 Jul 2025).

**CTD regime rules.** Conversion factor = price at a 6% yield. Below 6% the low-duration bond tends to be CTD, above 6%
the high-duration one. Flat-6% thought experiment: a parallel rally makes the shortest-duration deliverable CTD, a sell-off
the longest. An upward-sloping basket makes the longest bond CTD, an inverted one the shortest. Futures price = CTD forward
price / factor less total option value; futures track the worst performer, so they shorten in rallies and lengthen in
sell-offs (lower convexity than cash, possibly negative). Factors in the long-bond contract range from 0.43 (1.625% coupon)
to 0.83 (4.75%), and factors well below 1 give the wild card its value.

**Scenario grid for a long CTD basis (Sep 2025 long-bond contract, CTD the 11/43 bond).**

| Yield shift | CTD becomes | Basis effect |
|---|---|---|
| base | 11/43 | long 11/43 basis worth about 7 ticks |
| +50bp | 11/44 | 11/43 basis falls to about 6 ticks |
| +100bp | 8/50 | the 11/53 basis is worth 61 ticks |
| -50bp or more | 2/41 | CTD switches to the short-maturity end of the basket |

Read: the long CTD basis pays like a straddle in the shift, flat near the base and long the switch in either direction. Fair
value of a net basis = probability-weighted terminal payoff across such a grid (simulate shifts and twists); compare with a
replicating futures option and, if the basis is cheaper, buy the basis and sell the put. Futures PV01 = sum over deliverables
of P(CTD) x forward PV01, with the CTD probabilities taken from the grid.

**Wild-card rule.** The 3pm settle fixes the invoice and the short can declare delivery before 7pm while cash trades.
Exercise when gross basis x factor < (current cash price - 3pm cash close) x (1 - factor): a 3-hour call on (1 - factor) of
the bond, paid for with the gross basis on factor-weighted bonds. Exercising forfeits the remaining net basis. Worked case
(source): long 100mm face of a 4.75% Nov 2053 bond against short 734 long-bond contracts (factor 0.7342), gross basis 5
ticks, net 4; the market rallies 1 point after 3pm. Delivering 734 contracts costs 734 x 5 x 31.25 = 114,688 USD; selling
the 26.6mm tail (100 - 73.4) 1 point higher gains about 266,000 USD. Our check of the rule: 5/32 x 0.7342 = 0.115 is below
1 x (1 - 0.7342) = 0.266, so exercise. The option matters most in FOMC delivery months (press conference at 2:30pm). Buying
the net basis normally loses the premium (about 1 tick if bought at 1 tick and delivered optimally, more on a non-CTD),
and basis risk is live from inception, not only in the delivery month.
