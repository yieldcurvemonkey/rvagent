---
name: rv-composite-scoring
description: 'Combine z-score (entry), PCA/fair-value residual, carry/vol, OU half-life, percentile and empirical hit-rate into ONE ranking score for G10 rates RV candidates (curves, flies, forwards, swap spreads, basis, vol), with J-score / P-score (carry/vol + z), gated weighted composite, carry-entry-trend frontier projection score, expected-Sharpe score, weight calibration and contribution report. Use when asked to rank or score trades, "composite score", "J-score", "P-score", "which trade is best", "combine signals", weight carry vs value vs momentum, build a scorecard or best-trades table, calibrate score weights or check a score''s hit rate. Statistical signal blending (IC weights, decay): quant-signal-combination-and-decay.'
---

# Composite scoring of RV candidates

A screen produces many metrics per candidate (level z-score, PCA residual, carry/vol, half-life, percentile, how often the
trade was in the money). A trader needs one number to sort by. Sell-side desks use two families: an additive
**J-score = carry/vol + z** (Nordea) and a **projection onto the frontier of attractive trades** (Goldman Carry/Entry/Trend).
This skill defines a gated, signed, unit-free composite that works for any structure, shows each component's contribution,
and says how to calibrate and distrust it. The score ranks candidates inside one screen. It is not a P&L forecast.

## When to use
- "Rank these trades", "what is the best RV idea today", "build a J-score / P-score / scorecard".
- The user wants carry, value (z), momentum and mean-reversion speed blended and asks what weights to use.
- Scores from two screens (two currencies, two vendors) disagree and need reconciling.
- Checking whether a score actually predicts forward P&L (bucket test, hit rate, payoff).

## Inputs (data-agnostic)
Candidates come from [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md); each row is one package (outright, curve, fly,
forward, spread, basis, vol structure) already priced from the canonical tables (`curve_par`, `bond_quotes`, `swap_spreads`,
`vol_surface`, `stir_quotes`) per [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Column (derived candidate table) | Meaning, unit | Source skill |
|---|---|---|
| `package_id`, `structure`, `ccy` | id as in `signals`/`positions` | scan |
| `level_bp` or `z` | level of the structure; z = (level - mean)/std, ddof=1, window >= 3y (default 756 business days) | [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md) |
| `pca_z` (optional) | residual of the structure vs a PCA fit, in residual std | [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md) |
| `carry_bp` | carry + roll over the horizon of the receive-type position, bp, positive = earns | [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md) |
| `vol_bp` | std of the level change of the whole package (DV01-weighted structure, not the sum of leg vols) over the SAME horizon, bp | same |
| `halflife_days` | OU half-life in CALENDAR days of the structure on constant-maturity data (convert a business-day half-life x 365/252; the OU skill reports business days) | [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md) |
| `pctile` | rank of today's level in its window, 0..1 | z-score skill |
| `hit_frac` (optional) | frequency the trade would have been in the money after the horizon vs history | this skill |
| `trend` (optional) | momentum z, same sign convention as `z` | [macro-technical-analysis](../macro-technical-analysis/SKILL.md) |
| `side`, `hist_days` (optional) | explicit +1/-1 override; days of history behind z (flag `thin_history` below 756) | this skill |
| `cost_bp` (optional) | round-trip bid/offer + slippage | [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md) |

At least 3y of daily history for z/half-life. If a metric is missing, leave it empty (it then contributes 0). Never invent it.

## Conventions (state them in every output)
- bp throughout. Structure level: curve A-B = longer - shorter; fly 2s5s10s = 2x5y - 2y - 10y (high = belly cheap).
- **side = +1 "receive-type"**: P&L rises when the structure's level falls (receive fixed, long bond, receive the belly = sell the fly).
  side = -1 pay-type. Default side = sign(z): fade the deviation. A momentum trade sets side explicitly; the z and percentile slots then score 0 because they disagree with it.
- `carry_bp` is the earn of the side=+1 position; the side=-1 position earns minus that.
- Orientation of z: z > 0 = level high vs its history = receive-type cheap. Goldman defines Entry z so that attractive = NEGATIVE z with
  positive carry for the same trade; check which orientation a source uses before mixing numbers.
- Carry/vol is horizon-dependent: carry_h / vol_h = (carry_ann / vol_ann) x sqrt(h in years). All candidates must use the same h
  (default 3m for trades, as in Goldman's 3m carry vs 3m delivered vol monitors; 12m for the Nordea-style monitor). Hurdles quoted
  below are on the annual basis; at horizon h apply them x sqrt(h) (0.25 annual = 0.125 at 3m).

## Method

1. **Normalise every component to [0, 1] and make it side-aware** (a component only counts if it agrees with the trade direction).
   Defaults, with reasons:

   | Component | Formula (side s = sign z) | Cap and reason |
   |---|---|---|
   | entry `z_n` | `max(0, min(s*z, 4)) / 4` (z = `pca_z` if present, see step 3) | 4 sigma cap: beyond 4 the distribution is not Gaussian and fat tails (regime break) dominate; extra sigma buys no extra score. Analogue: in Willer & Saunders' FX-carry stress switch the max-z bucket above 4 (3% of days) had IR -2.02 against +1.30 below 2 |
   | carry `c_n` | `max(0, clip(s*carry_bp / max(vol_bp, floor), -3, 3) / 3)` | counts only if it pays in the trade direction. Cap 3 on the candidate's own horizon basis: 1.7 (12m) is already top of a Nordea monitor, so 3 at 3m is extreme and usually a vol-floor artefact |
   | percentile `p_n` | `max(0, s*(pctile - 0.5)*2)` | rank-based, robust to non-normal levels. Highly correlated with z (see Pitfalls) |
   | speed `h_n` | `max(0, 1 - halflife_days/90)` | 90d = one quarter, the usual holding horizon. Half-life beyond the horizon means the trade is a macro view, not RV |
   | hit `f_n` | `max(0, (hit_frac - 0.5)*2)` | frequency in the money; weight 0 until you have 3 windows of history |

2. **Weighted sum.** Starting weights (a prior, not a fit): z 0.40, carry/vol 0.25, half-life 0.20, percentile 0.15, hit 0.
   `score = max(0, sum_i w_i * comp_i - cost_hurdle)`; the max is 1. `cost_hurdle` = (cost_bp / vol_bp) x w_z / z_cap: the round-trip
   cost in horizon sigmas, converted to score at the z slot's score per sigma (0.1 by default). Missing components contribute 0, so missing data lowers the score and never raises it.
3. **Separate the level signal from the confirmation.** One slot for "how far from fair": use `pca_z` when a PCA fit exists
   (for flies and curves), else the raw z. Do not add both (double count); side follows the slot in use. If sign(pca_z) != sign(z), flag `z_disagree`: the structure
   is off its own history but explained by the factors, so it is probably a directional view in disguise.
4. **J-score for receivers (Nordea convention):** `J = carry_adj/vol + z`, with convexity-adjusted carry (carry & roll + value of
   convexity, forward swaps only) and 36-month realised vol in the 2019 monitor (the 2024 trade box prints past-1y realised vol; never mix them; average the vols of the points spanned during the hold: 4y1y uses
   the 3y1y and 4y1y vols). For payers flip both signs (the CLI signs J by `side`, default sign(J), so a payer ranks on |J| and a carry-led trade with opposing z keeps its carry direction). The 2024 "P-score" prints as convexity-adjusted carry/vol + Z
   (1.70 + 0.64 = 2.34); its definition is not stated, treat as inferred. J is unbounded and additive, which is why it is good for a
   single-currency monitor and poor for mixing with other metrics. Use `--mode jscore`.
5. **Frontier projection score (Goldman):** put each trade at coordinates (carry/vol, z[, trend]). Keep only attractive trades:
   signs line up as (+carry, -z, +trend) or the exact opposite, in Goldman's orientation (low z = cheap to be long). In this skill's orientation
   (z > 0 = receive-type cheap, trend > 0 = level rising) the same test is (+carry/vol, +z, -trend); flipping an axis sign is an orthogonal map, so
   scores are identical (`--mode frontier` uses it). Fit the last coordinate on the others by least squares
   (z on carry/vol: a line through the origin for 2 factors, a plane for 3; keep all axes unit-free or the largest scale dominates) using ONLY attractive trades; score = length of the orthogonal projection of
   the trade on that line/plane. Reading: the fitted line is the "efficient frontier" of what is on offer today; the score says how
   far along the joint carry/value/momentum direction a trade sits. Non-attractive trades get no score. Refit per screen,
   so scores are only comparable within one screen. `--mode frontier`.
6. **Cross-asset expected-Sharpe score** (Citi, Huggins & Schaller) when candidates mix swaps, bonds and vol: rank on
   `ES = expected return / risk` with expected return = carry + roll + convexity (linear) or theta + vol slide + gamma (options).
   For a mean-reverting structure use the exact OU form, x = level, mu = mean, k = ln2/half-life, h in years:
   `ER = (x - mu)(1 - e^{-kh}) + carry`, `sd = sigma sqrt((1 - e^{-2kh})/(2k))`, `ES = ER/sd`.
   This is the receive-type position (x above mu); for pay-type use (mu - x) and the pay-side carry. Under OU the Sharpe annualised falls
   with horizon, so quote it at the horizon you will actually hold (default 3m, the repo-wide carry/roll horizon; label it). Huggins & Schaller add execution rules: target about half-way
   to the mean, stop on the moving 2-sigma band; testing them in the model can roughly double the expected Sharpe of the same trade.
7. **Rank, then vet.** Sort by score, attach flags: `carry_against` (carry/vol < 0 in the trade direction), `no_reversion`
   (half-life > 180d), `z_disagree`, `thin_history` (< 3y), `z>4`, `vol_floored` (vol at the floor: carry/vol is an artefact). A flag is a reason to look, not an automatic drop,
   except `no_reversion` for a pure mean-reversion thesis.
8. **Calibrate before trusting any weight** (see Calibration).

## Calibration (weights, thresholds, hit rate)
- Do not tune weights to maximise in-sample P&L. Compare the score against a naive benchmark: equal-weight z-score of the same
  components, and pure |z|. Keep a composite only if it beats both out-of-sample (walk-forward, purged) in
  [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md). Round weights to 0.05 and constrain all to be >= 0.
- **Bucket test** (`bucket_report`): sort historical candidates by score into quintiles, then show mean forward P&L in vol units
  and hit rate per bucket. A usable score is monotone and the top bucket's edge exceeds costs. A non-monotone score is a ranking
  with no information.
- **Report the payoff, not just the hit rate.** J.P. Morgan's rates-derivatives weeklies print 12m closed-trade scorecards of 43-58
  trades with 72-81% winners (2018-2020), yet single losers of -31bp (receive 3Mx1Y OIS vs pay 3Yx1Y IRS) and -16 abp
  (sell 1Yx(2s/10s) correlation) sit beside typical winners of +4 to +18bp. With n=50 and p=0.75 the 95% interval on hit rate is about
  +/- 12 points (1.96 x sqrt(0.75x0.25/50)), so never rank two score buckets on a few trades. The printed hit rate also differs from
  winners/trades in some issues (e.g. 55 trades, 41 winners = 75% vs 79% printed, 29 Mar 2019): rebuild from counts.
- **Frequency in the money** is the Nordea version of an empirical hit rate: add the carry (and convexity) to today's level and ask how
  often that level was beaten over the previous 1y/3y/5y/10y. The same trade printed 100% / 59% / 75% / 76% across those windows
  (Nordea, EUR rates: Pushing back, 17 Jan 2024): a short window flatters. Use the lowest of the windows >= 3y.
- **Overlapping observations.** Daily candidates with a 3m forward P&L overlap: independent trades are about n_dates / horizon, so bucket CIs
  and t-stats from raw n are too tight; use non-overlapping dates or a block bootstrap. Picking the best of many weight sets inflates the Sharpe:
  discount for the number of trials (Bailey & Lopez de Prado, Deflated Sharpe Ratio, 2014). To turn a score into a forecast use alpha = vol x IC x score
  (Grinold & Kahn, 2000), with IC from the bucket test.
- Stability: recompute weekly; if a top-5 name drops out on a +/-0.05 change of any weight, the ranking is fragile, so report it as a tier, not a rank.
- Move to [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md) for IC/IR-based weights and signal decay.

## Worked examples
**1. J-score on a EUR forward fly (Nordea, EUR rates: Pushing back, 17 Jan 2024).** Receive belly 1y2y/3y2y/5y2y: carry /12m = 79.2,
empirical value of convexity 0.0, convexity-adjusted carry 79.3, realised 1y bp vol 46.5 (units as printed in the trade box), so carry/vol = 79.3/46.5 = 1.70
(1.705 from the rounded inputs; printed 1.70). Z-score 0.64. J (P) = 1.70 + 0.64 = 2.34. Carry supplies 73% of the score: this is a carry trade with mild value support, and the
100% in-the-money count vs the last 1y (59% vs 3y) shows the carry is recent. Carry/vol 1.70 is above every hurdle below.

**2. Hurdle logic (Barclays, Swap spreads: The Bright Spot in US rates, 30 Sep 2026).** Carry/vol by tenor of the swap-spread curve
(spread bp, carry bp, 1y vol bp; ratios as printed, from unrounded inputs): 2y -14/11/10 = 1.15; 5y -27/7/10 = 0.76; 10y -38/5/13 = 0.40; 20y -63/5/19 = 0.26; 30y -66/4/17 = 0.24.
Imposing a hurdle carry/vol = 0.25 and solving for the spread at which it binds gives the widening room (5y: -8, +20bp; 10y: -23, +15bp;
30y: no room). Use the same idea as a **gate**: candidates below carry/vol 0.25 (annual basis; 0.125 at 3m) get a zero carry component and need
value alone to qualify (`--ctv-gate`, horizon basis).

**3. Composite by hand.** z = +2.0 (receive-type), carry +15bp vs vol 10bp (carry/vol 1.5), pctile 0.90, half-life 18d, no cost:
z_n 0.5, c_n 0.5, p_n 0.8, h_n 0.8 -> 0.40x0.5 + 0.25x0.5 + 0.15x0.8 + 0.20x0.8 = 0.605. Same trade with carry -15bp: c_n = 0 -> 0.480
(flag `carry_against`). Mirror trade z = -2, pctile 0.10, carry -15bp on the receive side (pay-type earns +15) -> 0.605. Reproduced by `--selftest`.

**4. Expected Sharpe (Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).** EUR 5y5y vs GBP 5y5y swaption vol spread,
OU fit: mean 1.046, vol 28.25, speed k = 16.5/yr (half-life 15.4 days), level 12.35. Sharpe = E(change)/sd: 1w 0.91 (annualised 6.56),
1m 1.78 (6.12), 3m 2.26 (4.5). The script reproduces 0.91 and 1.78. Best risk-adjusted return is at short horizons; but constant-vol
OU overstates Sharpe at extreme entries because vol is higher far from the mean: cap or haircut.
Citi (A Holistic Approach to Convexity Across Fixed Income, Jun 2022): paying EUR 5y5y-15y5y-25y5y fly had ER +34bp, risk 50bp, ES +0.7
(34/50 = 0.68) among the highest on the screen.

**5. Frontier score (toy, selftest, Goldman orientation).** Points (carry/vol, z) = (1,-1), (2,-2), (-3,3) lie on z = -x: scores 1.41, 2.83, 4.24 (distance
from the origin); (1, +1) has signs that do not line up and is not scored. Goldman prints scores of this kind per currency and
globally, and the same trade scores differently: EUR 10y2y/12y3y/15y5y is 2.64 in the EUR screen and 1.99 in the global screen
(Goldman Sachs, Global Rates Best Trade Report, 30 Sep 2026).

## Signals & interpretation
- Composite score >= 0.6: strong, all four components agree. 0.35-0.6: candidate, needs a catalyst or a second signal. < 0.35: do not
  trade on the score alone. These cut-offs are starting points; set them from the bucket test, not from this text.
- Nordea J: values near 2 or above (carry/vol 1.7 + z 0.6) were the top of the monitor in the examples above. For z alone, |z| > 2 is the usual entry,
  |z| > 4 triggers a regime check rather than more size.
- A high score driven >70% by one component is a single-signal trade (all carry, or all z): state that and size by that signal's risk.
- Agreement across independent families raises conviction: JPM's rates scorecard keeps fair-value residual, positioning (long investor
  positioning = short signal), hawk/dove macro and momentum separate, each mapped to -5..+5 by percentile rank in its own history and
  explicitly not comparable across markets (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026). Prefer a scorecard of
  orthogonal families to one number when the families disagree: show the disagreement.
- Vol and positioning stress (Willer & Saunders, Trading Global Macro Markets, 2026): carry/vol styles lost most when a vol spike
  coincided with crowded positioning; a max-z stress switch (cut when above 2) lifted an FX vol-adjusted carry basket's IR from 0.89 to 1.30, and the bucket above
  4 sigma had IR -2.02. Apply a stress overlay to carry-heavy scores: if front-end vol or policy uncertainty is up, require more roll-down for
  the same score (Citi STIRT Weekly, Aug 2026: carry trades should offer a larger discount to spot to balance Sharpe ratios).

## Pitfalls
- **Double counting.** z, percentile and `pca_z` are one signal in three costumes. In the default weights z + percentile = 0.55 of the score
  from a single piece of information. Treat z and percentile as one family (keep their combined weight <= 0.55; lower the percentile weight first when adding `hit`) and PCA as a replacement for z.
- **First-order carry/vol overstates.** Darbyshire (Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022) tells the reader to avoid the
  roll-down/vol matrix: it ignores gamma and the full P&L variance and overstates some ratios. Use convexity-adjusted carry for forwards
  and long-end flies, and treat carry/vol as a ranking input, not a Sharpe forecast. Reconcile with the OU expected Sharpe before sizing.
- **Low-vol denominators.** JPY, CHF and short-end structures with vol near zero explode carry/vol. Floor vol (default 0.5bp over the horizon)
  and cap c_n. Cross-currency comparison of carry/vol needs the same vol window and the same horizon.
- **Carry/vol arithmetic drift.** Mixed horizons or mixed bases (a 4.6bp/yr roll in one section and a 1bp carry in the ratio) give a different
  answer from the same trade: carry/vol 1/32 = 0.03 in a USD 5s30s swap-spread flattener, versus 0.14 with the roll (Ade Rhodes, Trade Idea:
  USD 5s30s Swap Spread Flattener, 9 Oct 2025). Print the inputs next to the score.
- **Long forwards and the very front** fall off the value/carry lines (ING, Deconstructing the EUR yield curve, 15 Jan 2020): the 20y1y+ points and
  1y1y are driven by other things (convexity, policy). Exclude or tag them.
- **Roll-down in the z series.** Compute z and half-life on constant-maturity series, not on a rolling-contract series (Huggins & Schaller). Vol
  changes also move the terminal level: condition on vol beta by regime before choosing between carry and defensive structures (Citi Research,
  European Rates Weekly, 17 Mar 2022).
- **Refit per screen.** Frontier and percentile scores change with the universe. Never merge ranks across screens or across vendors; if you
  must, re-score the union with one refit.
- **Rank and size consistently.** Ranking on carry/vol but sizing equally forfeits the low-vol carry: global carry ranked and sized by vol scored IR 0.89,
  ranked on carry/vol but equal-sized 0.66 (Willer & Saunders). Size the shortlist by risk ([port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md)).
- **Look-ahead.** `hit_frac`, half-life and the frontier fit may use only data up to the decision date (see `signals`: a value dated t uses
  data known at t, positions use it from t+1).
- **Score as target.** A trade is not good because it ranks first; check the thesis ([rv-devils-advocate](../rv-devils-advocate/SKILL.md)).

## Output
Return one table, sorted by score, and write it to `signals` with `unit = score`, `value = score`, `zscore = z`, `horizon_days`, `model_version = weights id`:

| rank | package_id | structure | side (receive/pay) | score | z | pca_z | carry/vol | half-life d | pctile | hit_frac | contrib z / carry / pctl / hl | flags |

Add: weights used, horizon, vol window, history length and the screen universe (scores are not comparable outside it); the bucket-test
result if one exists; the top 3 candidates each with its dominant component. Hand the shortlist to
[rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and sizing to
[port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).

## Scripts
- [`scripts/score.py`](scripts/score.py): `zscore`, `halflife_days` (AR(1)), `ou_expected_sharpe`, `j_score`, `composite` (gated weighted
  sum with `pca_z` slot, contributions, flags, `--ctv-gate`, `cost_bp` hurdle; NaN-safe), `frontier_score` (2/3-factor projection), `pctile_to_scorecard`, `bucket_report`.
  `python scripts/score.py metrics.csv --mode composite|jscore|frontier [--weights z=0.5,hit=0.1] [--out ranked.csv]` (weights are renormalised to sum 1;
  `halflife_days()` returns calendar days by default).
  `--selftest` checks hand-computed composites, NaN/pca_z/side handling, Nordea's 2.34, Huggins' Sharpe 0.91/1.78, exact half-life, and frontier geometry.
- Extra scheme details and a source-by-source table: [references/source-schemes.md](references/source-schemes.md).

## Related skills
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): produces the candidate table this skill ranks
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z, percentile, robust windows
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC/IR weights, orthogonalising, decay
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry/vol inputs and convexity-adjusted carry
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA residual z
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life, OU Sharpe, first-passage times
- [macro-technical-analysis](../macro-technical-analysis/SKILL.md): trend / momentum input
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): walk-forward test of the weights
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): sizing after ranking
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): challenge the top-ranked trades
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): trade note for the shortlist
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): positioning family for the scorecard
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): package vol and DV01-neutral weights behind `vol_bp`
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): `cost_bp`
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables

## References
- Nordea Markets - EUR Rates Flash, J. Vainikainen (23 May 2019): forward-swap monitor, J-score = convexity-adjusted carry/vol + z, 36m vol, sigma changes, RSI
- Nordea Markets - EUR rates: Pushing back, A. Svendsen (17 Jan 2024): trade box (carry, conv-adj carry/vol, frequency in the money, Z, P-score), worked numbers
- Goldman Sachs FICC and Equities (IRP Market Strats) - Global Rates Best Trade Report (30 Sep 2026): Carry/Entry/Trend projection score, attractive-quadrant regression, per-screen refit
- Goldman Sachs - Global Rates Trader: Reaching Limits (2 Oct 2026): carry/vol monitors by currency for outrights, curves and flies; positioning indicators
- Huggins, D. and Schaller, C. - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): OU ex-ante Sharpe, half-life, execution rules, PCA-then-OU monitoring pipeline
- Darbyshire, J. H. M. - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): why first-order carry/vol is misleading, second-order Sharpe
- Citi Interest Rate Volatility Trading, M. Parolari - A Holistic Approach to Convexity Across Fixed Income (Jun 2022): homogeneous expected-Sharpe across swaps, bonds and vol
- Barclays - Interest Rate Derivatives: Swap spreads: The Bright Spot in US rates, A. Mok, A. Nashikkar (30 Sep 2026): carry/vol hurdle 0.25, widening-room table
- J.P. Morgan - Global Fixed Income Markets Weekly (21-22 Aug 2026): percentile-mapped -5..+5 rates signal scorecard across fair value, positioning, macro, momentum
- Willer, D. and Saunders, A. - Trading Global Macro Markets (Wiley, 2026): vol-sized carry, carry stress switch by max z, positioning x vol interaction
- Citi Markets - STIRT Weekly: Tokyo, we have a problem (week of 7 Aug 2026): larger carry discount when policy uncertainty rises
- Citi Research - European Rates Weekly: A narrative shift looms (17 Mar 2022): vol-adjusted roll-down and vol beta by regime
- ING Global Markets Research - Rates Strategy: Deconstructing the EUR yield curve (15 Jan 2020): long forwards and the front fall off value/carry lines
- J.P. Morgan - North America Fixed Income Strategy, Interest Rate Derivatives weeklies, Younger/Salem/St John (3 Aug 2018 - 6 Mar 2020): 12m closed-trade scorecards, hit rates vs loss sizes
- Rhodes, A. - Trade Idea: USD 5s30s Swap Spread Flattener (9 Oct 2025): carry/vol arithmetic and the basis inconsistency
- BofA Merrill Lynch - Global Rates and FX Primer: FX Quant Primer (1 Oct 2018): scorecard-by-rank plus 1y z-score ranking models (method transfer)
- Grinold, R. and Kahn, R. - Active Portfolio Management, 2nd ed. (2000) (external): alpha = vol x IC x score, scaling scores to forecasts
- Bailey, D. and Lopez de Prado, M. - The Deflated Sharpe Ratio (2014) (external): discount a selected best score for the number of trials
