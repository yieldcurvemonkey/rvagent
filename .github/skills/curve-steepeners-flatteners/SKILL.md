---
name: curve-steepeners-flatteners
description: 'Constructs, weights and evaluates two-leg curve trades (steepeners and flatteners such as 2s5s, 2s10s, 5s30s, 10s30s, 30s50s, forward-start 15y5y/20y10y, futures inter-commodity spreads) across G10 rates. Covers DV01-neutral vs vol/beta/level/PCA-weighted ratios, how directional a "curve" trade really is (bull/bear steepening and flattening, correlation to the 10y), carry/roll and forward breakeven, convexity cost of long-end flatteners, and regime-conditional behaviour (policy phase, inversion, rate-vol co-movement, flows). Use when asked to size or hedge a steepener or flattener (curve trade, slope trade, curve spread), "is this curve trade just duration", hedge ratio, spread beta, beta-weighted or level-neutral weights, bull flattener, bear steepener, twist, curve breakeven, months to breakeven, rolldown of a slope trade, delta-hedged forward flattener, or which way the curve should go in a given cycle phase. Forward-grid shape: curve-forward-grid-rv; PCA weights: curve-pca-factor-model.'
---

# Curve steepeners and flatteners

A curve trade is a bet on a *spread* `s = y_long - y_short`, not on the level. Whether it is one depends on the weights: DV01-neutral
legs cancel a parallel move only to first order, while real curves move with the level (hiking cycles bear-flatten, easing cycles bull-steepen,
and long-end spreads co-move with vol). This skill decides the weights, measures the residual directionality, prices the carry hurdle, and
conditions on regime so that a "steepener" is a view on shape and not a disguised outright or short-vol position.

Conventions used throughout (and by `scripts/curve_beta.py`): rates and spreads in bp; `2s10s = y10 - y2`; positive spread = upward-sloping;
**steepener = receive short leg / pay long leg** ("long the curve"; a flattener has the opposite signs); DV01 in currency per bp, positive for long
duration; `h` = DV01 risk on the long leg per unit of DV01 risk on the short leg, so steepener P&L per unit of short-leg risk `R` is
`R * (h * dy_long - dy_short)` and `h = 1` is DV01-neutral. Bull = yields down, bear = yields up. Packaging convention: name the trade by the longest leg
("paying 5s30s" = paying the 30y), and set both swap legs at market so there is no convexity from off-market coupons.

## When to use
- "Size / weight a 2s10s (5s30s, 10s30s, 2s5s...) steepener or flattener", "what hedge ratio", "DV01-neutral or beta-weighted?".
- "Is this curve trade really a curve trade?", "how directional is it", "bull flattener vs bear steepener", "does the curve flatten when yields rise?".
- Carry and breakeven of a slope trade, "months to breakeven", "how much must the curve move to break even", spot vs forward-start expression.
- Long-end flatteners as cheap convexity (delta-hedged 15y5y/20y10y, 30s50s, 10y10y/20y10y); steepeners as short-vol positions.
- Which shape move to expect given the policy phase, an inversion, a flow event or a rates-vol regime.
- Not here: three-leg flies ([curve-butterflies](../curve-butterflies/SKILL.md)), option-based conditional curves
  ([curve-conditional-trades](../curve-conditional-trades/SKILL.md)), full PCA machinery ([curve-pca-factor-model](../curve-pca-factor-model/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap/OIS rates, both legs, spot and forward-start | `curve_par` (`curve_id`, `start`, `tenor`, `par_rate_pct`) | daily close, one snap only, >= 3y (5y+ for z-scores, a full policy cycle for regime stats) | `par_rate_pct` is percent; multiply by 100 for bp. Government constant-maturity curves sit under `<CCY>-GOVT-<issuer>` |
| Bond yields for cash legs | `bond_quotes` (`ytm_pct`), `bond_static` | daily | use constant-maturity/spline yields for history, not on-the-run series (benchmark switches fake slope jumps) |
| Futures legs / spreads | `fut_quotes`, `fut_static` | daily settle | quote the CTD yield differential, not the net-change price |
| Leg DV01 (and bucketed DV01) | from [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md) | at trade date and at horizon | needed for notionals; use bucketed (key-rate) DV01 for hedging |
| Implied normal vol of the legs / the curve | `vol_surface` | daily | for breakeven-in-sigma, curve-implied beta, convexity screens |
| Forward-start curves for carry | `curve_par` with `start` = horizon, or `curve_zero` | daily | forward = implied by the same curve, not a separate quote |
| Policy-path / regime inputs | `stir_quotes`, `cb_meetings`, `macro_series` | daily | for the regime tag only |

If an input is missing, ask for it or hand off to the data adapter. Never invent values. Conventions per market (day counts, swap index,
benchmark bonds): [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md); schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Method

### 1. Pick the expression
| Expression | Use when | Caveat |
|---|---|---|
| Spot-start swap spread | general; liquid benchmark 2/5/10/30y | first float period is fixed, so 2y/10y behaves like 1.5y/9.5y and carries an outright delta overlay ("a common source of unexplained P&L"); ages (5s10s becomes a 5y outright after 5 years) |
| Forward-start swap spread (e.g. 1y fwd 5s30s) | you want a clean spread with no financing component; carry locked and the threshold known | no carry on a forward starter; roll is the whole story |
| CMS steepener | you want no ageing | CMS convexity pricing, see [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md) |
| Cash bonds | view is bond-specific | the sold leg (the long tenor in a steepener) needs borrow, pays accrued, rolls to on-the-run; own-issue repo on the sold leg; term vs overnight financing adds money-market slope exposure |
| Futures inter-commodity spread | capital efficiency, margin offset | fixed contract ratios leave a DV01 tail (e.g. selling 100 of a 2:1 10y/bond spread leaves a 42-lot tail in a DV01-neutral 242:100); CTD switches shift the effective tenor |
| Calendar spread of short-rate futures | front end (<= 2y), e.g. a Dec-Dec spread | longer intervals are more volatile; white-pack spreads can be twice as volatile as red-pack spreads; see [stir-futures-rv](../stir-futures-rv/SKILL.md) |

Details and futures/cash packaging: [references/weighting-and-packaging.md](references/weighting-and-packaging.md).

### 2. Weight the legs (the core decision)
Estimate on **changes** (levels give serially correlated errors; US 1y vs 3y levels regression was spurious with a unit-root-like residual), on daily or
weekly data. Default window: last 250 daily changes (one year, enough points, spans a regime) plus a 60-change recent window as a stability check.

| Rule | `h` (long-leg risk per unit of short-leg risk) | Use for |
|---|---|---|
| DV01-neutral | `1` | trading the quoted spread, benchmark/RFQ packages, when directionality is *wanted* (conditional swaptions use BPV-neutral weights), carry maths that assume parallel |
| Vol-weighted ("yield beta") | `sigma_s / sigma_l` | assumes `rho = 1`; over-corrects when `rho < 1` |
| Regression on long leg ("yield delta") | `beta_{s\|l} = rho * sigma_s / sigma_l` | zero expected P&L for a given long-leg move; also the variance-minimising `h` when the short-leg risk is the fixed position |
| Minimum variance | `sigma_s / (rho * sigma_l)` = 1 / `beta_{l\|s}` | lowest P&L variance when the long leg is the fixed position and the short leg the hedge (Burghardt's setting); the largest `h` of the four, i.e. least short-leg hedge per unit of long-leg risk |
| **Level-neutral (default for a pure shape view)** | `beta_{s\|x} / beta_{l\|x}`, `x` = 10y yield or PC1 score | zero expected P&L for a move in the level; weighted spread `s_w = h*y_l - y_s` is uncorrelated with the level |
| PCA-neutral | solve `E'(t + x) = 0` for PC1 (and PC2); see [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md) | multi-leg or cross-market trades; needs PC stability |

Procedure:
1. Compute `sigma_s, sigma_l, rho` and level betas on the estimation window of yield changes in bp (script: `analyse`). Report the whole menu of `h`, not a single number.
2. Test stability: recompute `beta_{s|x}/beta_{l|x}` on the recent 60 changes. If it differs from the 250-change value by more than 25% (relative), flag `h_unstable` and prefer the DV01-neutral
   weights plus an explicit directional overlay, or re-estimate on a regime-matched window. Betas flip: the OTR 10y beta ranged from 2.88 (1991) to 0.46 (1993) (Burghardt et al., The Treasury Bond Basis, 2005).
3. Choose: pure shape view (you do not want to own the level) -> level-neutral `h`; "the curve in a hiking/easing regime" view where you *want* the direction -> DV01-neutral, or express it
   with payers/receivers (see [curve-conditional-trades](../curve-conditional-trades/SKILL.md)); distant legs (30y vs 5y) need the correlation adjustment, adjacent legs do not.
4. Convert to notionals: steepener short-leg notional `R / dv01_short`, long-leg notional `-h * R / dv01_long` (script: `notionals`). Re-hedge when the longer leg's rate has moved
   20-25bp or `h` has moved > 25%; both PVBPs also decay with ageing, so for holds of months size with forward PVBP at the horizon.
5. A regression estimate says nothing about *why* the beta exists. Check which leg is the dependent variable (direct and reverse regressions differ) and that the window is relevant to the current regime.

DV01-neutral is not direction-neutral: "BPV-neutral hedging may give any exposure, by chance the right one, a completely different one ... or even an exposure which is opposite to the intended one"
(Huggins & Schaller, Fixed Income Relative Value Analysis, 2024). Summed total DV01 is also not factor-neutral: partial (bucket) DV01s must be hedged, and a parallel move in par space is not parallel
in zero or forward space (Coleman, A Guide to Duration, DV01 and Yield Curve Risk Transformations, 2011).

### 3. Measure directionality of the resulting package
On the same window compute: `beta_dir` = OLS slope of the weighted-spread change on the level change (0 by construction for level-neutral weights; for DV01-neutral weights and level = long leg, `1 - beta_{s|l}`); `R` = correlation of
spread changes with the 10y change; `R2`; and the four move-type shares (bull-steep, bear-flat, bull-flat, bear-steep; front-driven = bull-steep + bear-flat, back-driven = bull-flat + bear-steep; sum of |bp| weights).
Defaults and meaning (judgement bands calibrated to the source numbers; the cited anchor is that many curve trades show `R` of -0.5 to -0.9 against the 10y, outrights near 1 (Goldman Sachs, Global Rates Best Trade Report, 30 Sep 2026)):
- `|R| < 0.3`: genuinely shape-driven; `0.3-0.6`: moderate, beta-weight or hedge; `> 0.6`: disguised outright. Screen with `Carry/R = ExAnte Sharpe / (1 + |R|)`.
- Sign tells the regime: spread falling when the level rises (negative `beta_dir`) is the normal hiking/bear-flattening pattern; the sign can flip by section and period.
- A day when the curve steepens in a rally against a 60-day pattern (JPM 2s10s on 2y: `y = 52.361x - 55.756`, R2 75.8%, 25 Feb 2020) is a regime hint, not a trend: "one day does not make a trend".
- Level-orthogonal slope: the residual of the long spread (e.g. 5s30s) regressed on the short leg (5s) over a rolling 5y window is a term-premium proxy that strips the level (Citi, The Messi Theory of Interest Rates, 31 Jul 2026); it is a levels regression, so use it descriptively and check the residual is stationary before trading it.
- Risk in spread basis: map the bucketed DV01 ladder into spread instruments (5y, 2s5s, 5s10s, 10s30s) with a Jacobian: lossless, gives an intuitive P&L explain, and the transformed instruments are correlated, so add a VaR overlay (Quantitative Finance Stack Exchange, Can PCA be used to transform a ladder of interest rate risk?, Sep 2023).
- Decompose a spot spread into non-overlapping forward spreads (5s30s into 5y5y-5y, 10y5y-5y... buckets) to see where the move happened and avoid spot-vs-spot double counting.

Evidence tables, regime studies and G10 market specifics: [references/directionality-regimes-and-markets.md](references/directionality-regimes-and-markets.md).

### 4. Carry, roll and breakeven (the hurdle)
- **Breakeven**: `BE = fwd_spread(T) - spot_spread` using the `T`-forward of each leg. A DV01-neutral steepener needs the spot spread to rise by `BE`; positive `BE` = negative carry. Express as a fraction of
  the horizon's 1-sigma spread move; flag if `BE` > 0.5 sigma (judgement default). For non-neutral weights the hurdle depends on each leg's yield change, not only the slope.
- **Per leg** (BofA labels, 1y horizon): rolldown `5y - 4y`; carry breakeven `5y spot - 1y4y fwd` = rolldown + `(4y spot - 1y4y fwd)`, so the last bracket is the pure forward-vs-spot carry and the breakeven is the total cushion (check which of the two a source calls "carry+roll"). For a DV01-neutral spread, leg rolls in bp net as a difference (steepener: received short-leg roll minus paid long-leg roll) without scaling. Never apply the
  carry approximation `SR(6m,4.5y) - SR(0,5y)` beyond the fixing period. Forward starters have no carry; steepeners roll positively when forwards are flatter than spot.
- **Months to breakeven** = mispricing (bp) / carry per month. Compare it with the realistic reversion time (about 3 months in ING's work): if the mispricing must close faster than that just to cover the roll, skip it
  (ING rejected a 14bp-too-flat steepener rolling -15.5bp/3m, which broke even only if the residual closed within 2.6 months) and prefer a positive-carry expression (fly, forward).
- **Convexity**: `E(R) = carry + slide + 0.5*gamma*sigma^2*T/PVBP` in yield bp (`sigma` normal bp per year, `T` years, `gamma` currency per bp^2, `PVBP` currency per bp); doubling vol quadruples convexity value. A DV01-neutral flattener is long convexity, a steepener short; deduct realised-vol convexity cost from a
  steepener target (1y fwd 10s30s steepener carry +27bp/yr vs convexity cost 11bp/yr at 120bp/yr vol: margin too thin, Citi, Flying Too High, 20 Dec 2010).
- Carry is not a signal on its own: roll/carry at entry is a weak predictor of steepener P&L (Citi, A QT revolution, 17 Sep 2026); inverted-curve steepeners bleed like theta, so timing matters.

Long-end flattener convexity screens (breakeven vs realised vol, curve-implied vol, delta-hedge band), the 15y5y/20y10y lifecycle and the systematic `sigma_BE` vs `sigma_imp` rule:
[references/carry-breakeven-and-convexity.md](references/carry-breakeven-and-convexity.md).

### 5. Regime and flow conditioning
1. Tag the current mode from the four move-type shares over 2w/1m/3m (front-driven vs belly-driven) and from the policy phase (hiking -> bear-flattening bias, easing -> bull-steepening bias, on hold -> long end drives,
   late cycle -> bull-flattening). Pre-first-hike (about 50 trading days) DV01-neutral 2s10s flatteners worked; after a front-end inversion the story ends with a steeper curve but timing is poor, so wait or use options.
2. Rates/vol: long-end steepeners are exposed to rates-up-vol-up regimes ("similar to selling payer skew on belly rates"); check the sign of correlation of the package with the 10y and with 3m10y implied vol on a 1m horizon,
   and neutralise the received short leg if the asymmetry comes from it.
3. Flow: insurers/VA (USD 15-25y), callable supply (USD ultra-long), LDI and pension reform (GBP, EUR, NL), life insurers and BoJ (JPY), MBS convexity. Name the flow, its sign and what ends it
   ([flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md), [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md)).
4. Sanity check: flattening with short rates up a lot and long rates up less is normal; short up and long down before the first hike is "artificially flat".

## Worked examples
**A. Hedge-ratio menu with known numbers.** $100mm OTR 30y vs the 5y; `sigma_5 = 101.9bp`, `sigma_30 = 81.7bp`, `rho = 0.88` (annualised weekly changes, 1990-97); conventional (DV01) hedge $341.2mm of 5y
(Burghardt et al., The Treasury Bond Basis, 2005). Yield beta 341.2 / (101.9/81.7) = 273.6; yield delta 273.6 / 0.88 = 310.9; minimum variance 273.6 x 0.88 = 240.7 ($mm of 5y, matches the source). The net
DV01 left unhedged is 29.5 / 13.2 / 43.9 ($k/bp): only the conventional hedge is zero-DV01, but its net *expected* DV01 is -14.6 ($k/bp): because the 5y yield moves about 1.10x the 30y yield (`rho * sigma_5 / sigma_30`), it is over-hedged in expectation.
`python scripts/curve_beta.py --selftest` reproduces the three ratios.

**B. What DV01-neutral hides (illustrative, shows the arithmetic).** Daily changes 2y vs 10y with `sigma_2 = 3.6bp`, `sigma_10 = 5.0bp`, `rho = 0.82` (assumed). Then `h_vol = 0.72`, `h_reg_long = h_level = 0.82 x 0.72 = 0.59`, `h_reg_short = 0.72/0.82 = 0.88`.
The DV01-neutral steepener has `beta_dir = 1 - 0.59 = +0.41`: a 10bp rise in the 10y is accompanied by an expected +4.1bp in the spread, i.e. at $50k/bp it is really a bear-steepener bet worth about +$205k per 10bp before any
shape view. Level-neutral notionals at illustrative DV01s of 190 (2y) and 880 (10y) per $1mm: receive $263mm 2y, pay $33.5mm 10y (versus $56.8mm 10y if DV01-neutral).

**C. Weighted spread from vols.** EUR 3s20s conditional trade: normal vols 25.0bp/day (3y) and 63.4bp/day (20y) give a vol ratio 0.39, so risk weights 100% / 39% and notionals EUR595mn (3y) / EUR39mn (20y), versus 595 / 100 for the
DV01-neutral strike-shift version; the weighted spread is `1.10 x 0.39 - (-0.10) = 53bp`, and it loses when the realised beta of 3y to 20y moves exceeds the 0.39 vol ratio (J.P. Morgan payoff study: beta 22% never loses, 40% saturates, 80% loses) (J.P. Morgan, A primer on Conditional Trades, 26 May 2016).

**D. Carry hurdle.** USD 5s30s, 9 Feb 2024: spot spread 4.38 - 4.15 = 23bp, forward 4.35 - 3.93 = 42bp, so a DV01-neutral steepener needs +19bp in a year; the 5y leg's own carry breakeven (22bp) is about a third of a 1-sigma
1y move (65bp) (BofA, Rates basics: spot vs forward, 15 Feb 2024). 2s10s at -35bp (2y 4.53%, 10y 4.18%) needed +58bp and cost about $390k a month on $100mm (Bassman, The Cost of Carry, 5 Mar 2024). More examples (EUR 2s5s forward roll,
zero-coupon barbell, 15y5y/20y10y lifecycle) in the reference files.

**E. Empirical reweighting instead of closing.** USD 15y5y/20y10y delta-hedged flattener: after the spread turned directional (steepening in rallies, flattening in sell-offs), the 20y10y notional was raised from $81.97mn to $84mn
(beta 1.025) and the position kept; the flattener made about $155K net of costs over May-Dec 2019 as the spread fell to -12.5bp (Citi, Reweighting delta-hedged 15y5y/20y10y flatteners, 16 Oct 2019; Taking profits, 5 Dec 2019).

## Signals & interpretation
| Observation | Reading / action |
|---|---|
| Spread z-score (1y, 3y; see [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md)) extreme but `\|R\|` > 0.6 | the trade is mostly the level; hedge the level or trade the outright |
| Level-neutral weights stable (recent vs 250 window within 25%) and `\|R\|` < 0.3 | clean curve view; size on spread vol |
| Carry/R (or Carry per month vs mispricing) favourable, BE under 0.5 sigma | positive-carry expression, accept |
| Months to breakeven below reversion time | skip; look for a forward-start or fly alternative |
| Long-end flattener with BE/RV below 0.5 and positive carry | cheap convexity ("free long convexity buy"); exit when BE/RV climbs towards 0.8-1 even with an unchanged thesis |
| Long-end steepener: rates and implied vol rise together | main loss path (carry-steepener stop-outs); size down, hedge with payers or a positively convex pair |
| Front-end inversion, then first cut | curves ended steeper in 4 of 5 US episodes, but 1m-6m paths mixed; require a catalyst, not a level |
| Curve level looks cheap on a fair-value model but expectations are repricing, flow is one-way or event risk is asymmetric | do not fade yet; understand why the dislocation occurred |
| Residual from a single-factor curve fit with decaying R2 (e.g. 100% to 60%) | do not trade the residual (driver is global/term premium) |

## Pitfalls
- Equal notionals are not a curve trade (10y DV01 is almost double the 5y); DV01-neutral is not factor-neutral; total DV01 hides curve risk, so hedge bucketed DV01.
- Betas from levels, from one day, or from a window that straddles a regime break. Check subperiods; PC shapes change (Jan vs Mar 2020); long windows are slow to detect breaks, short ones are noisy and over-trade hedges.
- Benchmark switches and on-the-run roll artefacts create fake slope moves; use constant-maturity or spline series.
- Spot-vs-spot comparisons double count the short-rate path; use non-overlapping forwards. Long-dated forwards (20y+) and the very front fall off value/carry lines.
- Spot-start IRS carry a fixed first period (2y/10y is really 1.5y/9.5y): hidden outright delta.
- Using the 6m carry approximation for horizons beyond the fixing period; mixing carry definitions (financing, forward-vs-spot, carry+roll).
- Roll-down is a scenario, short vol and crowded ("failed badly in 21-22"); negative roll-down needs high conviction or a quick exit; do not re-weight legs to manufacture carry.
- Steepeners are crowded; steepeners that harvest carry in the long end hide a short-vol/short-skew profile; recent small samples (since 2022) have few independent observations. Positioning can stay stretched while supply continues.
- Long-end flatteners are not clean options: no defined downside, convexity per DV01 falls with ageing, parallel-move assumption fails when the curve itself is volatile, VA/insurer flows can persist. Do not initiate in illiquid markets even when screens flag it.
- Overlapping holding-period cohorts inflate Sharpe (76 monthly cohorts with 1y holds span only about 7.6 calendar years, i.e. fewer than 8 independent annual outcomes); a Sharpe from one structure does not generalise to a strategy; carry/slope and level/convexity are collinear.
- Event/seasonal patterns (auction grids n = 12, monthly up-ratios n = 20, midterms n = 5) are tiny samples; supply explains swap spreads better than the curve.
- PCA-residual curve trades need meaningful covariance, non-trivial dominance in the neglected PCs and residuals outside everyday norms (a 9-day covariance residual was rejected, Darbyshire, 2022).
- Backtest spreads as $1-invested total-return series with costs as negative dividends, not the raw spread. See [bt-backtest-design](../bt-backtest-design/SKILL.md).

## Output
Return, for each candidate (table), then a short narrative:

| Column | Content |
|---|---|
| trade | direction by longest leg, curve_id, `start`, short/long tenor, expression (swap/cash/futures) |
| spread_bp, spread_w_bp | quoted `y_l - y_s` and weighted `h*y_l - y_s` |
| h menu | `dv01`, `vol`, `reg_long`, `reg_short`, `level`; chosen `h` and why; `h_unstable` flag |
| sizing | short-leg risk (ccy/bp), leg notionals, bucketed DV01 residual, re-hedge trigger (bp move) |
| directionality | `R`, `beta_dir` (DV01-neutral and weighted), R2, move-type shares, regime tag |
| hurdle | carry+roll 3m and 12m (bp), forward breakeven (bp and in sigma), months to breakeven |
| value | z-score 1y/3y (and since a regime start), fair-value residual if available, convexity BE/RV for long-end |
| risks / invalidation | one invalidation condition, the flow or event that would hurt, rate/vol co-movement sign, liquidity |
| data flags | stale legs, benchmark switches, window length, sample size |

Hand off the chosen trade to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) (entry/target/stop in spread bp, carry, scenarios), pre-trade challenge to
[rv-devils-advocate](../rv-devils-advocate/SKILL.md), packaging to [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md).

## Scripts
- [`scripts/curve_beta.py`](scripts/curve_beta.py): reads a canonical `curve_par` table (CSV/Parquet) or pandas series, returns the hedge-ratio menu (`dv01`, `vol`, `reg_long`, `reg_short`, `level`), leg vols/correlation,
  beta of the spread to the level, weighted-spread directionality, a recent-window stability flag, rolling level-neutral `h` (lagged one observation; `spread_w` applies the current `h` to history, descriptive only), and the four move-type shares; also `notionals()`. Needs >= 30 clean changes; horizons > 1 are non-overlapping and anchored on the last date. Example:
  `python scripts/curve_beta.py --curve-par curve_par.parquet --curve-id USD-SOFR --short 2Y --long 10Y --level 10Y --window 250`. `--selftest` reproduces the published
  hedge-ratio case, a simulation with known betas, the move-type bookkeeping, horizon anchoring and the short-history refusal.

## Related skills
- [curve-butterflies](../curve-butterflies/SKILL.md): three-leg versions; a rich fly often normalises with the wings flattening, so choose fly vs slope.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): options-based conditional steepeners/flatteners that monetise directionality.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PC1/PC2-neutral weights and residuals.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-space spreads (5y5y, 15y5y/20y10y) and roll-adjusted forwards.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): term-premium decomposition of slope moves.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll mechanics for the legs.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): par vs zero DV01, bucketed hedges, Jacobians.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): OLS vs TLS, rolling and Kalman betas.
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): long-end convexity value behind flatteners.
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): curve vol, CMS spread options, implied correlation.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md) and [quant-regime-detection](../quant-regime-detection/SKILL.md): regime classification.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): policy path priced in the front-end legs.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md), [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): flow drivers of long-end slope.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): size on spread vol and DV01 budgets.
- [stir-futures-rv](../stir-futures-rv/SKILL.md), [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): short-rate calendar spreads; CTD switches in futures curve spreads.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md), [bt-backtest-design](../bt-backtest-design/SKILL.md): spread z-scores; total-return backtests of weighted spreads.
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): reaction functions and policy-path fair value.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): scenario and stress tests.
- [quant-cointegration](../quant-cointegration/SKILL.md): cointegration tests and level hedge ratios.
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): covariance and correlation estimation.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): OU half-life, entry and exit bands.

## References
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis, 3rd ed. (McGraw-Hill, 2005): four hedge ratios and worked numbers, yield betas and their instability, UST correlations, futures curve hedges.
- Düring (Alexander) - Fixed Income Trading and Risk Management (Wiley, 2021): steepener/flattener hedge equations, PVBP drift and forward-PVBP sizing, benchmark-switch artefacts, preferred-habitat flows, curve-hedged spreads.
- Huggins & Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): PC1 pivot and directionality, BPV-neutral warning, swaption-expressed conditional curves and the R2-vs-premium screen.
- Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): directionality hedge methods, benchmark spread conventions, roll-down steepener selection, second-order spread Sharpe, curve sections.
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): curve trades by Fed phase, segment correlations, inversion tables, 1m-change and 55-day regime classifiers, BoJ-cycle rules.
- Tuckman & Serrat - Fixed Income Securities, 4th ed. (Wiley, 2022): DV01 hedge assumes beta = 1, regression hedges, PCA coverage.
- Golub & Tilman - Risk Management: Approaches for Fixed Income Markets (Wiley, 2000), and Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): PC1-neutral curve trades, two-PC risk, bull-flatten/bear-steepen test.
- Coleman - A Guide to Duration, DV01, and Yield Curve Risk Transformations (SSRN, 20 May 2011): partial DV01s, basis-dependent parallel shift.
- Salomon Brothers - Understanding the Yield Curve Parts 1, 2, 3, 5, 7 (Antti Ilmanen, 1995-96): forward breakevens, barbell/bullet as flattener, steepness/short-rate dynamics, convexity value.
- J.P. Morgan - An option by any other name: sourcing cheap convexity in the long end (Younger, Sarkar, Salem, 3 Feb 2017) and Valuing convexity in the long end of the yield curve (9 Feb 2018): curve-implied vol, flattener breakevens and backtests.
- J.P. Morgan - A primer on Conditional Trades (Gupta, Bassi, Vijay, 26 May 2016): vol-weighted curve, implied vs delivered directionality, EUR curve report.
- Citi Research - Trading long-dated convexity (9 May 2019), Reweighting 15y5y/20y10y flatteners (16 Oct 2019), Taking profits (5 Dec 2019), Liquidity, vega and convexity (30 Mar 2020): delta-hedged forward flattener screen, lifecycle, 25bp re-hedge.
- Citi Research - European Rates Weekly (A QT revolution, 17 Sep 2026; Higher yields are here to stay, 24 Sep 2026): EUR steepener rate/vol asymmetry, entry-level non-predictability, leg neutralisation.
- BofA Global Research - Understanding the yield curve dynamic (23 Jul 2025), To everything there is a season (23 Jan 2022), Rates basics: spot vs forward (15 Feb 2024): four move types, cycle map, breakeven formulas.
- Credit Suisse - PCA Unleashed (24 Oct 2012) and ING - Deconstructing the EUR yield curve (15 Jan 2020): PCA hedge ratios, bear-flattening bias, months-to-breakeven discipline.
- Goldman Sachs - Global Rates Best Trade Report (30 Sep 2026): Carry/R directionality filter, G10 curve picks.
- Nordea Research - Carry & Roll (12 Jul 2013), Convexity Maven (Bassman) - The Cost of Carry (5 Mar 2024), Sharp Curve Ahead (25 Jan 2024): carry/roll formulas, 2s10s steepener breakeven.
- CME Group - U.S. Treasury Futures Inter-Commodity Spreads (Feb 2024); CurveTrades LLC - Yield Curve Spread Trades (Shook, Jun 2013); Clarus Financial Technology - Mechanics and Definitions of Spread and Butterfly Swap Packages (Barnes, 14 Oct 2014): packaging, ratios, tails, DV01-neutral sizing.
- Quantitative Finance Stack Exchange threads on PCA-neutral hedging (Nov 2019), measuring steepener sensitivity (Oct 2021), expressing a 2s10s steepener (Mar 2018), ultra-long-end inversion (Aug 2019), PCA and risk ladders (Sep 2023): PC1 projection, bucketed risk, curve gamma, first-fixing pitfall, spread-basis Jacobian.
- Citi Research - Flying Too High (20 Dec 2010) and The Messi Theory of Interest Rates (31 Jul 2026): regime-average curve fair values and convexity cost; term-premium proxy and twist regimes. J.P. Morgan - US Treasury Market Daily (25 Feb 2020): 2s10s directionality regression.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed. (Harriman House, 2012): calendar-spread volatility by pack. Tsay - Analysis of Financial Time Series, 3rd ed. (Wiley, 2010): changes vs levels regression.
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): total-return series for spread backtests.
