---
name: curve-butterflies
description: 'Build, weight and evaluate curve butterflies (flies) in G10 rates: 2s5s10s, 3s5s7s, 5s10s30s, 10s20s30s, forward-start flies (1y1y/2y1y/3y1y, 5y5y/10y5y/15y5y), bond and STIR flies. Covers 50/50 DV01-neutral (1:2:1), maturity-weighted, cash-and-duration-neutral, regression-weighted and PCA-weighted (PC3, PC1/PC2-neutral, minimal-change) weights, directionality adjustment, fly-vs-belly residuals and z-scores, carry/roll, convexity cost, sizing and stops. Use when asked if the belly is rich or cheap, how to weight or size a fly, whether a fly is directional, level/slope-neutral or PCA-neutral, PCA fly vs 50/50 fly, fly residual or mispricing, receive/pay the belly, curvature trade, condor, microfly. PCA mechanics: curve-pca-factor-model.'
---

# Curve butterflies (flies): weighting, directionality and residuals

A fly is a bet that one maturity (the belly) is mispriced against the line through two others (the wings), with the
level and slope risk removed as far as the weighting allows. It pays when the belly mean-reverts, when curvature
expectations change (easing cycles cheapen the belly, ZLB richens it), or from structural flows concentrated in one
point (variable-annuity and ALM demand at 15-25y, mortgage-servicer hedging at 7y). It is only as good as the weights:
a DV01-neutral fly is not factor-neutral and is often just a disguised outright or slope trade.

## When to use
- "Is 5y/10y/20y rich or cheap versus its wings?", "what weights for a 2s5s10s fly?", "PCA fly or 50/50?".
- A fly or curve trade looks directional and must be adjusted to level/slope neutrality.
- Ranking flies (spot or forward-start) by residual, z-score, carry/roll and convexity cost.
- Bond, futures or STIR flies (cash-neutral, microflies, condors). Option-based (conditional) flies: structuring is in
  [curve-conditional-trades](../curve-conditional-trades/SKILL.md); here only their diagnostics matter.

## Conventions (state them in every output)
| Item | Convention |
|---|---|
| Rates | `curve_par.par_rate_pct` is percent; flies, residuals, stops in **bp** (x100). |
| Fly | `fly(A,B,C) = 2*y_B - y_A - y_C`, A < B < C. **Positive = belly cheap (high yield)**; "receive the belly" is the trade that profits when it falls. 2s5s10s = 2*5y - 2y - 10y; Citi's -0.5:1:-0.5 is the same fly divided by 2. |
| Risk weights | `w = (w_A, w_B, w_C)` in DV01 terms for the **receive-belly** package, belly = +2, so 50/50 = (-1, +2, -1), weighted fly = `sum w_i*y_i`. Positive = receive fixed / long duration. |
| P&L | `P&L = -R * d(fly_w in bp)` where R = DV01 per bp of weight 1. Receive-belly gains when the fly falls. |
| Notionals | `N_i = w_i * R / dv01_i`, `dv01_i` = DV01 per unit notional (positive). Quote the weights AND the notionals. |
| Other houses | Clarus/Darbyshire/BNP "pay the fly" = pay the belly = profits when the fly (our sign) rises. Düring's *swap* fly = wings - 2*belly = minus ours; his *bond* fly = belly - 0.5*wings = half of ours (his "bond fly = -1/2 swap fly"). Clarus STIR microflies are quoted as 2*belly price - wing prices = minus our sign (positive = belly rich; buying one = receive belly). Citi's 2017-23 monitors quote -0.5:1:-0.5, i.e. half the 2*belly - wings scale; its 2010 trade note used the full scale. Check sign and scale before using any house fly number. |
| Forward flies | "3y 2s5s10s" = fly of swaps starting in 3y; or forward-point flies (1y1y/2y1y/3y1y, 10y10y/20y10y/30y10y). Quote levels in bp. Source screens often hide leg weights: rebuild them before trading. |
| Names | fly = 3 legs (2s5s10s), condor = 4 legs (+1,-1,-1,+1; 2s3s/4s5s), "pascal" = (-1,+3,-3,+1) = spread of flies, "badger" = 2y5y10y fly starting in 1y. |

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap/OIS rates for the 3 legs (spot and/or forward-start) | `curve_par` | daily close, >= 1y for residuals, 3-5y to test weight stability | Same `snap` for all legs. Constant-maturity govt par curves also fit (`<CCY>-GOVT-<issuer>`). |
| Bond yields/prices for cash flies | `bond_quotes`, `bond_static` | daily | Analyse on a fitted/constant-maturity curve, implement in actual bonds (benchmark roll creates fake flies). |
| STIR futures prices | `stir_quotes` | daily | Equidistant contracts for flies (3m/6m/1y gaps). |
| Leg DV01s / key-rate risk | from [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md) | live curve | Use forward DV01 matched to the holding period for aged trades. |
| Normal vols (diagnostics only) | `vol_surface` | daily | Fly/vol link, conditional-fly checks. |
| Optional drivers | `macro_series`, `positioning`, `flows_trades` | varies | Flow-adjusted residual, regime fair value. |

If an input is missing, ask for it or hand off to the data engineer ([data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)). Never invent values.
Constraints: body strictly between the wings; legs >= 2 grid points apart; very uneven weights (a 2y-4y-30y fly)
are a disguised steepener or flattener, so use [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md).

## Method

### 1. Pick the weighting by purpose
| Scheme | Weights (risk, belly 2) | Neutral to | Use |
|---|---|---|---|
| 50/50 DV01 (1:2:1) | (-1, 2, -1); wing risk equal, sum 0 | parallel shift only | Monitor, liquid execution (interbank trades 50:50), view that includes directionality |
| Maturity-weighted | `(-r_A, 2, -r_C)`, `r_A = 2(m_C-m_B)/(m_C-m_A)`, `r_C = 2(m_B-m_A)/(m_C-m_A)` | parallel + linear steepening | Puts more risk on the wing nearer the belly; 2-5-10 gives 1.25/0.75 |
| Regression (direction-adjusted) | `(-(1-b1), 2-b2, -(1+b1))`, betas below | slope and belly level (in sample) | Default when the fly is also traded as a pure curvature RV; lowest out-of-sample vol in Example 2 |
| Belly-on-wings OLS / min-variance | `(-b_A, 1, -b_C)` or `-Q_ww^-1 Q_wb` | minimises hedged variance | Sizing from residual risk; in the EUR 2016 test (Example 2) within 0.3% of the lowest out-of-sample vol |
| PCA, PC3 of the 3 legs | 3rd eigenvector scaled to belly = 2 | PC1 and PC2 exactly (in sample) | Monitor on a long window (Citi: 5y rolling); not DV01-neutral |
| PC1+PC2-neutral with DV01s | solve below | PC1, PC2 incl. DV01 weighting | Larger fly (4+ legs) or when the belly is pinned |
| PC1-only (min-change / divide) | project (-1,2,-1) off PC1 | PC1 | Keep the 50/50 look, remove most level exposure |
| Cash- and duration-neutral (bonds) | `MV_A+MV_C = -MV_B`, `D_A MV_A + D_C MV_C = -D_B MV_B` | cash and duration | Bond barbell vs bullet; wings then not 50/50 |

Default: build the signal from the **regression residual of the 50/50 fly** (Step 3) and execute either the 50/50
package (liquid, dealers quote wider on PCA weights) or regression/PCA weights if |beta| is material. Never choose
weights to make carry look better, and never force wing signs to "negative": report and keep what the fit gives.

### 2. Weight formulas (all in risk terms; `scripts/fly_weights.py` implements each)
- **Regression weights (A)**, changes in bp, rolling window: fit `d(fly) = a + b1*d(slope) + b2*d(y_B)`, `slope = y_C - y_A`,
  `fly = 2y_B - y_A - y_C`. Then `w = (-(1-b1), 2-b2, -(1+b1))`; rescale belly to 2. By construction the package is
  uncorrelated in sample with slope and belly. Weights come from the fit, never hard-coded: they drift (wings -0.73/-0.47 on 13 Jan 2017,
  -0.705/-0.465 on 9 Feb 2017, -0.70/-0.46 on 6 Jun 2017 for belly 1; Citi, Swearing in huge expectations, Sell Blues convexity adjustments, hedged, Turning Green from Blue).
- **Belly-on-wings (B)**: `d(y_B) = a + b_A d(y_A) + b_C d(y_C)`; risk weights = the betas, receive belly 100% vs wings
  `b_A, b_C` (they sum above 100% when a joint wing move moves the belly by more than 1bp). Hedged P&L vol = belly DV01 x
  residual SD (Tuckman and Serrat, Fixed Income Securities, 4th ed., App. A6). This gives the same weights as min-variance.
- **PC3 weights**: covariance (not correlation) of 3-leg yield changes; `w = eigvec(lambda_min)/eigvec_B * 2`. Dividing
  by the belly element removes the sign ambiguity.
- **PC1+PC2-neutral with DV01s**: for belly notional N_B fixed, solve `sum_i N_i*dv01_i*L_k,i = 0`, k = 1,2 for the two
  wing notionals. Loadings `L` are of the PCA on yield changes. Exact for 3 legs; the result is proportional to PC3 in risk
  space. With more legs use the min-norm solution.
- **PC1-only**: minimal change `w = x - p(p'x)/(p'p)` with x = (-1,2,-1), p = PC1 loadings, then rescale belly to 2.
  "Divide by loadings" `x_i/p_i` is PC1-neutral only if `sum x = 0` and explodes when a loading is near 0.
- **Min-variance**: pin belly = 2, `w_wings = -Q_ww^-1 Q_wb * 2`; guard condition number (< 1e10) and use covariance of
  *changes*. Details, closed forms, 4-leg versions: [weighting-methods](references/weighting-methods.md).

### 3. Directionality diagnostics (always report)
1. **R^2 and beta of the fly level vs its belly level** over 6m-1y (BofA flags 50/50 R^2 of 43-69% as directional; up to 89%
   in 2022). 3m correlations of the fly with 10s, 2s10s and 5s30s (Citi monitor columns).
2. **Horizon**: correlation in changes at daily, weekly and 2-weekly frequency. A BTP BPV-neutral fly had -0.88 vs the
   average yield in levels but +0.06 daily, -0.27 weekly, -0.57 two-weekly changes (Huggins and Schaller, 2nd ed., 2024).
   Hedge with the horizon you will hold, not the one the data happens to be sampled at.
3. **Non-linearity**: scatter fly vs PC1 score with a quadratic fit. A PC1-neutral EUR 2s7s10s had R^2 0.62 to level with an
   inflection near a 0% 7y swap rate (ING, Deconstructing the EUR yield curve, 15 Jan 2020).
4. **Factor exposure**: regress the fly's P&L on PC1/PC2/PC3 scores; PCA weights are PC1/PC2-neutral only in the estimation sample;
   out of sample they reduce but do not remove the exposure (Citi keeps correlation columns for that reason).
5. **Pinned leg**: when the 2y is pinned (pre-hike), a 2s/x/y fly behaves like an x/y curve trade whatever the weighting.

### 4. Fair value and residual (the signal)
- **Residual vs belly (and slope)**: regress the fly on the belly level (optionally plus slope) over a trailing window,
  residual (bp) and its z are the signal; negative residual = belly rich, positive = cheap. Windows: 6m (JPM, BofA), 1y
  (Citi). Fit on the window ending at t and take the residual at t (trailing window, no future data, `residual_z` in the script); act from t+1.
  Levels regressions are serially correlated: use them to *rank* rich/cheap and never as a hedge ratio ("moved more or
  less than predicted" is not a fade signal); hedge weights come from changes.
- **PCA residual**: PCA on levels or non-overlapping forwards (1y window, 3 PCs), residual = data - reconstruction, positive =
  yield above model = cheap. A very positive residual flanked by negatives is a fly (Credit Suisse, PCA Unleashed,
  24 Oct 2012). The number of PCs is a design choice: leaving PC3 out keeps curvature in the residual (CS did so for core govt bonds and FRA-OIS bases); keeping it absorbs curvature, so flies then show up only in what is left. The residual of the same maturity is not tradable outright: express it as a fly through the null space of
  the retained factors (Burton, Dektor and Wheeler, c.2008). See [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md).
- **Regime-conditional fair value** for forward flies: `E[fly] = sum_regime P(regime at horizon) * regime average`, e.g.
  9%*6 + 21%*10 + 70%*24 = 19bp for the 1y-forward 5s10s30s (Citi, Flying Too High, 20 Dec 2010); target = (current forward -
  predicted) - convexity cost. Regime averages rest on few cycles. A regime change mis-centres any mean-reversion rule: a
  7bp fly looked rich vs a 10bp old mean but was cheap vs the new 4bp mean (Lehman, Macro-Awareness in RV Trading, Oct 2003).
- **Flow-adjusted residual**: add structural-flow regressors (variable-annuity liability durations, pension demand) so the
  residual times the trade rather than just flags it: 10s20s30s on 10s30s + VA durations gave R^2 98%, SE 0.5bp, 20s rich
  (J.P. Morgan, For cheap gamma, look to the long end, 23 Aug 2019). See [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md).
- **Single-bond check** before a cash fly: regress the issue's asset-swap spread on the sector curve slope; a 3.9 sd miss
  with R^2 0.65 was "idiosyncratic" and traded as a fly (Citi, The long end basket case, 4 Feb 2015).

### 5. Signal thresholds (starting defaults; recalibrate per market and regime)
| Test | Default | Reason |
|---|---|---|
| Residual z (window 126d, z over same window) | enter at abs z >= 1.5 | below ~1 the edge is inside bid/offer |
| Residual size | abs residual >= 4bp for 3-leg swap flies, and expected profit / round-trip cost >= 2 | generic scanner default; assume ~0.5bp per leg and replace with your own quotes |
| Regression quality | R^2 >= 0.60 on the 126d window | otherwise the belly/slope explain too little to define "fair" |
| Beta stability ("traffic light") | rolling-63d std of each beta z-scored over 126d, `TLI = sqrt(z_b^2 + z_w^2)`; > 3 red, < 2 green | weights that move are not hedges |
| Mean reversion | half-life 3-120 days, ADF p <= 0.10 (<= 0.05 strict); hold to ~3 half-lives (87.5%) | z without a reversion speed says "almost nothing" (Huggins and Schaller). ADF on a *fitted* residual is too lenient with standard critical values: use Engle-Granger values ([quant-cointegration](../quant-cointegration/SKILL.md)) |
| Multi-window agreement | 1m, 3m, 6m z-scores same sign | avoids chasing a one-month spike (a 62-day window flagged a 4bp move as 5.7 sd, Goldman Sachs, 30 Sep 2026) |
| PCA scanner | belly abs z >= 1.5 and each wing abs z >= 0.5 on the opposite side | the residual should be concentrated in the belly |
| Weight stability | wing weights (belly 2) move < 0.15 and keep sign across 3m/6m/1y/3y windows | judgement rule of thumb, not sourced |

### 6. Carry, roll, convexity, breakeven
- Report 3m carry+roll in bp **and** money for the weighted package (PCA/regression fly carry must be in money terms; a
  bp carry must name its maturity). Receive-belly roll-down = fly level minus the level of the fly one slot shorter (what it becomes
  after the roll). STIR microfly, Clarus sign (2*belly - wings, positive = belly rich): 8th +1.5bp vs 7th +3.0bp, so buying the
  8th (long belly; our sign -1.5 vs -3.0) earns +1.5bp over 3m (Clarus, A Dummies Guide to Trading IRS, 19 Jun 2024).
- **Breakeven months = mispricing / monthly carry**: a forward fly 23bp rich with carry -2bp/3m (-0.67bp/month) loses on carry only
  if reversion takes > ~3 years (ING, Deconstructing the EUR yield curve; its spot equivalent had carry -2.5 + roll 3.2 = +0.7bp/3m,
  so no carry breakeven). If carry is negative, compute carry to the 90% quantile of the first-passage time (Huggins and Schaller).
- **Convexity**: a duration-neutral fly long wings / short belly (pay belly) is long convexity at a yield give-up; the receive-belly
  package earns the belly's yield pickup as compensation for being short convexity (Düring). Convexity cost scales with realised
  vol: 11bp/a vs 8bp/a for 10s30s steepener vs 5s10s30s fly at 120bp realised (Citi, Flying Too High). Value ~ 0.5 x C x sigma^2
  (C in years^2, sigma = normal vol in decimal yield per year, result in yield units). Ultra-long "richness" is convexity, not a
  trade. In a 1980-94 monthly-rolled 5s/30s barbell backtest 99% of return volatility came from reshaping and reshaping beat convexity in every subperiod (Salomon, Ilmanen, Part 5, Sep 1995). Deduct convexity
  cost from the target; deeper treatment in [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md).
- Receive-belly 5s10s30s flies behave like short-vol positions; size them as short gamma, and expect crowding to be shaken
  out when vol spikes (Citi, US Rates Weekly, 2 Oct 2026).

### 7. Sizing, stops, execution
- Hedged-fly P&L vol = R x SD(d fly_w), R = risk per unit weight (belly DV01 = 2R at belly weight 2). For the belly-on-wings hedge
  (belly weight 1, R = belly DV01) this is belly DV01 x SD of the regression residual on changes (OLS min-variance, Tuckman and
  Serrat A6). Stop at 2 residual SD or at the level where the thesis breaks (regime change); target at zero residual **plus** expected overshoot:
  after residuals < -5bp, 6 of 7 EUR 5s10s30s episodes overshot to +5bp ~2.7 months after reaching fair (BNP, EUR curve
  convexity: Lessons from history, 25 May 2021), so do not take profit mechanically at 0.
- Put costs in the entry level (0.5bp off mid per fly in ING examples). Size by liquidity of the thinnest leg.
- Express through the cleanest package; a fly at its extreme can be unexitable: in March 2020 the peak mark could not be
  realised until costs fell back to ~3bp (Citi, Alert: Taking profits on long end butterfly trade, 15 Jun 2020).
- Use direction-neutral weights to offset existing book exposure, halve size when vol is high, cap downside with an explicit
  extreme-curve scenario (ING, March ECB: QE or bust, 9 Mar 2020).
- Packaging detail (agree belly notional, wings from DV01 ratios, market coupons, imply one wing from the fly price):
  [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md).

### 8. Bond, futures, STIR
- Cash: run the model on constant-maturity/fitted yields and implement with the bonds your fitted curve flags (cheapest
  belly, richest wings, same curve sector). Choose DV01-neutral (wings equal risk) or, if the package must also be funding-neutral, cash- and duration-neutral market
  values (script `w_cash_duration`; wings then not 50/50 in risk). Benchmark rolls fake fly moves (a Bobl benchmark switch created a false 2s5s steepening): use spline yields.
- Futures-implied bond flies around CTDs: see [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md).
- STIR: fly = `P1 + P3 - 2*P2` of equidistant contracts (price points; = S1 - S2 in spreads; since price = 100 - rate this equals our
  `2*y_B - y_A - y_C`, so buying it = pay belly), condor = sum of two adjacent
  flies. Leg in one contract at a time: do not hit the whole 3-leg bid/offer. Microflies "are not an arbitrage strategy".
  See [stir-futures-rv](../stir-futures-rv/SKILL.md).

## Worked examples
Full tables and more cases: [published-fly-data](references/published-fly-data.md).

**1. PC3-weighted USD 3s5s10s from a covariance matrix (bquanttrading, Principal Component Analysis Part II, 2015/16).**
Covariance of swap *levels* 3y/5y/10y (%; the source ran PCA on levels, the script and this skill's default use changes): 7.1 8.9 5.5 / 8.9 14.0 13.0 / 5.5 13.0 17.5; PC3 = (0.63, -0.70, 0.32);
divide by the belly loading: **(-0.90, +1, -0.46)**. The script recomputes (-0.898, 1, -0.461). PV01 per 1mm of 274 (3y),
482 (5y), 903 (10y); for 50k belly PV01, pay 50k/482 = 103.7mm 5y, receive 50k*0.90/274 = 164mm 3y, receive
50k*0.46/903 = 25.5mm 10y. The 50:50 version is correlated with the 5y level and 3s10s; the PCA version shows flat scatters.
Fly about -47bp (range -36 to -50), z -2.15, OU half-life 11 business days, carry+roll 6.25bp/3m (belly rich: pay it).

**2. Same fly, five directionality fixes (2s5s10s, body = 2) (Quantitative Finance Stack Exchange, How to adjust butterfly
2s5s10s swaps trade for directionality?, 2018/2021; Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022).**
With PC1 = (0.660, 0.604, 0.447): divide-by-loadings (-0.91, 2, -1.35); minimal change (-1.1002, 2, -1.0780) (script
reproduces both). Regression/min-VaR weights depend on the sample: EUR 2016 fit Jan-Jun, test Jul-Dec (116 days):

| Weights (2y, 5y, 10y) | PCA | Min-VaR | Regression | raw 50/50 |
|---|---|---|---|---|
| fit | -2.215, 2, -0.648 | -1.650, 2, -0.794 | -1.960, 2, -0.756 | -1, 2, -1 |
| out-of-sample SD of daily changes | 0.8689 | 0.7628 | 0.7609 | 0.8399 |

Regression and min-VaR cut out-of-sample vol by ~9%; PCA weights were *worse* than 50/50 (PCA does not minimise variance,
it removes a factor). Choose by purpose: variance vs factor neutrality.

**3. 10s20s30s: regression vs PCA hedge (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022, Ch.6).**
UST 82 daily obs: `dy20 = 0.019 + 0.465*dy10 + 0.669*dy30`, R^2 94.7%, SE 1.15bp (out-of-sample 0.70bp). Risk weights
46.5% (10s) and 66.9% (30s): sum 113.4%, above 100% because a joint wing move moves the 20y by more than 1bp. USD swap
PC1/PC2-neutral (loadings level 3.44/3.73/3.77, slope 0.07/1.02/1.35; DV01 0.09347/0.17064/0.23600): receive 100 of 20y,
pay 49.56 of 10y and 53.60 of 30y = risk weights 27.1% / 74.1%, sum 101.2%. The 30y takes most of the hedge because the
20y loadings resemble the 30y's. Residual PC3 per 100 is 0.007, not worth a fourth leg. Check: the script returns
(-49.60, -53.61) from the rounded loadings.

**4. PCA vs 50/50 on UST around 5y (BofA, US Rates Viewpoint: Understanding the yield curve dynamic, 23 Jul 2025).**
6m window, 2s5s10s: PCA fly last -98.9 (z -1.3), 50/50 fly z -1.6, R^2 of 50/50 vs belly 65.4%, residual -7.3bp (z -1.3);
2s5s30s: R^2 68.7%, residual -17.0bp (z -1.5). Conclusion: 5y rich vs wings, and 43-69% of the 50/50 fly is just the
belly level. In 2022 (3m window) z-scores disagreed sharply (2y/3y/5y: PCA -3.1, 50/50 -0.1; R^2 80.8%) (BofA, UST RV
Primer, 2 May 2022): when PCA and 50/50 disagree, the story is the directional component, so trade the residual.

**5. Forward fly with regime fair value (Citi, Flying Too High: Receive Belly of 1-Year Forward 5s10s30s Fly, 20 Dec 2010).**
1y-forward 5s10s30s at 48bp vs predicted 19bp (regime-weighted); above the 98th percentile even within on-hold periods.
Legs (ATMF 1y forward): pay 1y5y $180mm, receive 1y10y $200mm, pay 1y30y $50mm, net delta +198 (~DV01-neutral), net
gamma -88 (short convexity). Target 20bp gain = 28bp gap - 8bp convexity cost; stop 10bp.

## Signals & interpretation
- **Rich/cheap**: residual z <= -1.5 with R^2 >= 0.6 and a green beta-stability light = belly rich -> pay belly (or sell it
  against the wings); z >= +1.5 = belly cheap -> receive belly. Confirm with the PCA fly and the regression fly agreeing in
  sign, and with 1m/3m/6m z-scores aligned.
- **Disagreement table**: 50/50 residual and PCA residual disagree -> directional component dominates; trade the one whose
  correlation to 10s/2s10s/5s30s is lowest. All fly z-scores clustering across the curve (many PCA flies at -1.2 to -2.0 z in
  Feb 2017) means one common factor moved: that is one trade, not many.
- **Fly vs curve**: normalisation of a rich 10y belly came with a flatter 10s30s 86% of the time (6 of 7 episodes) (BNP); a
  belly that leads a sell-off (2s5s bear steepening with belly leading) is rare "if you were truly above neutral"
  (JWS Macro, Global Rates Outlook #6, 7 Jun 2026). Fly vs vol: 5s10s30s co-moves with vol (daily correlation +0.56/+0.65
  in vol-up/vol-down days) while 2s5s10s does not (+0.09) (Citi, European Rates Morning Call, 12 Aug 2026).
- **Cycle priors**: belly cheapens in easing cycles and richens at the ZLB; fly averages fall as hiking progresses
  (2s5s10s 36 / 32 / 14bp: on hold / start / 6m into hiking, Citi, Flying Too High).
- **Carry filter**: favour flies whose short-term correlations to curvature and to 10s30s have opposite signs, then decompose
  P&L (curvature, vol decline) before attributing it (Nordea, EUR rates: The quiet game, 12 Aug 2025).
- **Screens rank, they do not decide**: Carry+Entry screens get dominated by outright forwards with R ~ 1; penalise
  disguised duration with `Carry/(1+|R|)`, R = correlation to outright rates (Goldman Sachs, Global Rates Best Trade Report,
  30 Sep 2026). Feed rankings to [rv-composite-scoring](../rv-composite-scoring/SKILL.md).

## Pitfalls
- **DV01-neutral is not factor-neutral.** Long 50k/bp 5y vs 25k each in 2s and 10s is DV01-flat but outperforms in rallies
  (Credit Suisse, PCA Unleashed). BPV neutrality implicitly assumes equal PC1 loadings (Bund 5y +1bp goes with 10y +0.87bp).
- **PCA weights are unstable and not DV01-neutral.** Citi's 2s5s10s wing weight went -0.9 (2017) to -0.36 (2019); small
  covariance changes swing neutral weights; re-estimate on a rolling window, never backtest with today's weights (look-ahead).
  Eigenvector sign is arbitrary; PC3+ are unstable as tenors are added; 3 PCs explain >99% beyond 3y but only ~75% of the 1y
  point, so the front end needs more factors. Using all PCs gives zero residuals.
- **A PC1-neutral fly can remain directional**: in a regime, at a policy turn, or non-linearly; shorten the lookback (3y to 1y)
  in high vol, sub-sample by regime, hedge the factor separately.
- **Ill-conditioning**: neutral solves blow up when `D = e5,1*e10,2 - e5,2*e10,1 ~ 0`; multi-leg regressions are collinear
  (VIF = 1/(1-R^2), condition number > 20 is a problem) (Greene, Econometric Analysis, 8th ed.). Check weights across windows.
- **Regression pitfalls**: levels have serially correlated errors; the dependent variable matters (reverse regression gives a
  different hedge unless |rho| = 1); "the hedge is always as good as the calibration" (swapsball.net, Regression in finance:
  friend or foe?, 27 Oct 2017). Hedge ratios embed macro assumptions; a statistically different coefficient needs an
  economic-significance test.
- **Regime shifts** put mean-reversion offside: 1999-2001 +-5bp rule paid ~5bp per turn, then a long-5s trade lost ~15bp as the
  easing regime moved the mean (Lehman, Tuckman, Oct 2003). Include a short-end factor (e.g. a 3rd front STIR contract) to
  stabilise 2s5s10s.
- **Mean reversion is not guaranteed**: models can stay cheap/rich ("convergence is not expected in the short run"): require
  evidence it started (momentum of the fitting error). Residuals of a few days of data (9 daily moves), within everyday
  ranges, or just reversing a prior outlier are not signals (Darbyshire).
- **Statistically optimal flies die in bid/offer**: sparse mean-reverting baskets concentrate in 3-5 adjacent points, but a
  1bp bid-ask erased the profits (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008/2011).
- **Structural flows** can keep a fly stretched for months (VA/insurers receiving 15-25y, UK pension/ALM at 20y, mortgage
  servicer hedging). Use flow-adjusted residuals for timing; a residual is a dislocation, not necessarily a trade
  (e.g. Dutch pension reforms caused 15y5y/25y5y residuals).
- **Idiosyncratic vs sector**: stop cascades in 5s10s30s dislocate neighbouring points; an illiquid 20y OAT fly was "too
  illiquid to get on in size" (Astor Ridge, Trade Radar, Mar 2022); positioning can override valuation (Citi, Global Macro Trade Ideas Radar, 13 Aug 2026).
- **Fly "01" is not unique**: a 1bp fly move can come from different leg moves with different P&L (10 vs 20 in one example):
  check scenario plausibility with the bucket risks and reprice fully for big moves (Quantitative Finance Stack Exchange, How to measure Steepener/Flattener/Butterfly sensitivity (in 01), 2021).
- **Roll and cut-offs**: carry in a fly shrinks when expected cuts erode front-end roll; compare the forward-implied fly
  against the historical fly-vs-level scatter (forwards can over-price belly cheapening).
- **Backtests of event grids** (auction entry/exit) rest on ~12 observations and are regime-sensitive.
- **Screens are illustrative**: backward-looking sell-side screens are not recommendations; rebuild weights and re-test.

## Output
Return, per candidate fly (spot or forward-start), one table row plus the weight block:
- `fly` (legs, tenors, start), `scheme`, `window`, risk weights (belly 2) **and** notionals per R, DV01 per leg, and the
  net DV01 (non-zero for PCA/regression weights).
- Level (bp, receive-belly sign), 3m high/low, residual (bp) and z (1m/3m/6m), R^2 vs belly, 3m correlations to 10s, 2s10s,
  5s30s, beta-stability light, half-life, ADF p.
- 3m carry+roll (bp and money), convexity cost, breakeven months, scenario P&L (level +-50bp, 2s10s +-25bp, 10s30s +-15bp),
  proposed entry (with cost), target, stop, return on risk (P&L over the largest two-week move since the start of the sample).
- Flags: directional (R^2 of the traded package vs belly > 0.6 or non-zero PC1 exposure; the residual signal already strips it, so execute with regression/PCA weights or hedge the belly beta), regime-stale weights, flow-driven, liquidity of thinnest leg.
- Signals table in canonical form (`signals`: `package_id` like `USD-SOFR:2Y5Y10Y:fly`, value in bp, z, horizon_days). A signal dated t uses data to t only; positions start at t+1.
Hand the shortlist to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and the weights to
[rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md); run
[rv-devils-advocate](../rv-devils-advocate/SKILL.md) before sizing.

## Scripts
- [`scripts/fly_weights.py`](scripts/fly_weights.py): risk weights for 50/50, maturity, regression (with betas),
  belly-on-wings, min-variance, PC3, PC1/PC2-neutral notionals, minimal-change and divide-by-loadings PC1 hedges,
  cash-and-duration neutral market values; weighted fly series, directionality (R^2, correlations) and trailing-window
  residual z. CLI: `python scripts/fly_weights.py --curve curve_par.csv --curve-id USD-SOFR --legs 2Y,5Y,10Y --dv01 a,b,c`
  prints all schemes side by side. `--selftest` checks published known answers (PC3 weights from a covariance, PC1
  min-change, PC1/PC2-neutral 10s20s30s notionals), a simulation with known betas and loadings, bp-unit and directionality checks, and the residual z.
  Weighted fly levels for weights whose sum is not zero carry a level component: use them for residual/z only.

## Related skills
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA construction, loadings stability, residuals and P&L attribution to PCs.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): two-leg curve trades; uneven flies reduce to these.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-based and premium-neutral flies.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-space flies, kinks, roll-adjusted forwards.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): model-implied fair value and term premium.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): leg DV01s, key-rate risk, Jacobian transforms to flies.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry, roll and forward breakevens for packages.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market indices, day counts and benchmark tenors.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): OLS/TLS/Kalman betas and residual diagnostics.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life, ADF, entry/exit timing for residuals.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score windows, percentiles, ranking.
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): shrinkage/EWMA covariance behind PCA and min-variance weights.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR microflies, condors, kink fades.
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): convexity value and cost in flies and 30y.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): structural drivers of long-end flies.
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): choosing the bonds for a cash fly.
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md), [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md), [rv-devils-advocate](../rv-devils-advocate/SKILL.md): ranking, write-up, packaging, pre-mortem.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md), [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md), [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md), [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md), [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md), [quant-cointegration](../quant-cointegration/SKILL.md): canonical tables, scan context, monitoring, look-ahead/overfit checks, leg costs, residual stationarity tests.
- Per-market notes: [g10-market-notes](references/g10-market-notes.md). Published weight history and trade records: [published-fly-data](references/published-fly-data.md).
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): regimes and scenario trees.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): scenario and stress tests.
- [quant-regime-detection](../quant-regime-detection/SKILL.md): statistical regimes and structural breaks.

## References
- Citi Research - US Rates Weekly (Mathai, Williams, Chang et al.), "Time for moderation" (17 Feb 2023) and "OAT of the blue" (2 Oct 2026): fly RV table definition, PCA-fly weights (5y window), correlation columns, residual sign rule, forward 5s10s30s trades.
- Citi Research - US Rates Weekly series (Mathai, Bikbov, Kang, Williams, Li): "Swearing in huge expectations" (13 Jan 2017), "Going nuclear (on the curve)" (3 Feb 2017), "What to expect when you're expecting a turn" (20 Apr 2018), "The rocky road to a steeper curve" (18 Jan 2019), "Deal or no deal" (10 May 2019), "Trade worries linger" (17 May 2019), "Fixing the plumbing" (30 Sep 2019), "All it takes is a little push" (4 Oct 2019), "Eat, pay, spend" (27 Mar 2020): PCA weight history, PCA vs equal-weight correlations, fly tables.
- Citi Investment Research and Analysis - US Rates Trade Recommendation, "Flying Too High: Receive Belly of 1-Year Forward 5s10s30s Fly" (Arora, Chen, 20 Dec 2010): regime-conditional forward fly fair value, convexity cost, full trade.
- Citi Research - Rates trade ideas: "Sell Blues convexity adjustments, hedged" (Bikbov, Williams, 9 Feb 2017), "Turning Green from Blue on short convexity" (6 Jun 2017), "Alert: Taking profits on long end butterfly trade" (15 Jun 2020), "Global Macro Trade Ideas Radar" (13 Aug 2026), "The long end basket case" (4 Feb 2015): regression-fitted fly hedge, exit-cost lesson, AUD/OAT flies, single-issue cheapness test.
- Citi Research - Vol Lab and European Rates: "Vol cycle, steepeners, and SOFR" (25 Mar 2019), "Fading vega dislocations" (5 Oct 2026), "Gamma and Vega RV" (14 Jan 2019), "Buying vol for less" (25 Sep 2019), "Forward steepener and vol divergence" (12 Jun 2023), European Rates Weekly (17 Mar 2022) and Morning Call (12 Aug 2026): fly-vs-belly diagnostics, vol flies, fly/vol link.
- BofA Global Research - "Understanding the yield curve dynamic" (Braizinha, 23 Jul 2025), "UST RV Primer: A hitchhiker's guide to RV on the UST curve" (2 May 2022), "US Treasury auction primer" (8 Mar 2024): PCA vs 50/50 diagnostics tables, auction fly grids.
- BofA Global Research - UK Rates Viewpoint, "Back to school: tough tests this term" (Stengeryte, Capleton, 5 Sep 2024): SONIA 3s5s7s fly, cash- and duration-neutral gilt barbells.
- Credit Suisse Fixed Income Research - "PCA Unleashed: The application of PCA across European Rates markets" (Pelata, Giannopoulos, Haworth, 24 Oct 2012) and US Treasuries Futures Focus (28 Sep 2009): PCA algorithm, residual flies, hedge ratios, EUR/GBP flies; regression-weighted cash fly vs CTD.
- ING Global Markets Research - Rates Strategy (Bouvet, Schroeder, Garvey): "Deconstructing the EUR yield curve" (15 Jan 2020), "No rise in rates but position for lower volatility" (4 Feb 2020), "EUR crisis trades: let's get tactical" (3 Mar 2020), "March ECB: QE or bust" (9 Mar 2020), "March ECB: taking out the ECB put" (12 Mar 2020): direction-neutral flies, non-linearity vs PC1, multi-factor fair value.
- BNP Paribas - G10 Interest Rates Focus, "EUR curve convexity: Lessons from history" (Oynoyan, Meijer, 25 May 2021): residual episode study, overshoot, risk-off behaviour.
- Nordea Markets - EUR Rates Flash (Vainikainen, 23 May 2019, 24 Jan 2020, 5 Feb 2020) and EUR rates "Pushing back" (Svendsen, 17 Jan 2024), "The quiet game" (12 Aug 2025): carry/vol and PCA mis-pricing scores for forward flies.
- Goldman Sachs FICC and Equities (IRP Market Strats) - Global Rates Best Trade Report and GS Market Movers (30 Sep 2026): fly screen (Ex Ante Sharpe, Entry, Carry/R), normalised-move screen.
- J.P. Morgan - "A primer on Conditional Trades" (Gupta, Bassi, Vijay, 26 May 2016); "For cheap gamma, look to the long end" (Younger, Salem, St John, 23 Aug 2019); Forward Treasury, Asset Swap and Funding Report (29 Jan 2015); Monthly Inflation Outlook and Global Fixed Income Markets Weekly (Aug 2026): conditional-fly directionality, flow-augmented regression, forward fly levels, residuals, bond flies.
- Barclays Research - Global Rates Weekly, "The urgency question" (2 Oct 2026); JWS Macro - Global Rates Outlook #6 (7 Jun 2026); Astor Ridge - Trade Radar (Mar 2022): desk views on paying the 5s10s30s belly, belly-led sell-offs, EGB bond flies.
- Lehman Brothers - LMR Quarterly 2003-Q3, "Macro-Awareness in Relative Value Trading" (Tuckman, Oct 2003): regression fly, regime-shift fly index, vol-curve-driven wing weights.
- Tuckman and Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): regression and PCA-hedged 10s20s30s, OLS minimum-variance hedge, convexity of barbells.
- Huggins and Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): PCA fly hedge ratios, Bund 2-5-7 trade, horizon-dependent directionality (MVOU), conditional flies.
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch and Dee, 2022): benchmark fly/condor/pascal, directionality hedges (naive/minimal PCA, CoVaR), PCA residual critique.
- Duering - Fixed Income Trading and Risk Management (Wiley, 2021): n-leg sizing, 50/50 and maturity-weighted equations, PCA-neutral matrix form, convexity bias in 2-5-10.
- Salomon Brothers - Ilmanen, Understanding the Yield Curve Parts 1 and 2 (1995), 5 (Sep 1995), 6 (Nov 1995), 7 (with Iwanowski, Feb 1996); Kopprasch, Understanding Duration and Volatility (Sep 1985): barbell-bullet economics, curvature measures, yield-beta hedge ratio.
- Quantitative Finance Stack Exchange - "How to adjust butterfly 2s5s10s swaps trade for directionality?" (2018, edited 2021), "How to measure Steepener/Flattener/Butterfly sensitivity? (in 01)" (2021), "Construct a butterfly interest rate portfolio to eliminate PCA exposures" (2018-2020), "Hedging a trade for PCA component neutrality" (2019), "Calculating PCA hedge ratio for 3-leg spread" (2016), "Can PCA be used to transform a ladder of interest rate risk?" (2023): closed-form PC-neutral weights, out-of-sample comparison.
- bquanttrading - "Principal Component Analysis - Part II" (2015/2016): PC3-weighted 3s5s10s, sizing, OU z-score signal; swapsball.net - "Regression in finance: friend or foe?" (27 Oct 2017): regression-hedge limits.
- Clarus Financial Technology - "Mechanics and Definitions of Spread and Butterfly Swap Packages" (Barnes, 14 Oct 2014) and "A Dummies Guide to Trading Interest Rate Swaps" (19 Jun 2024); Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): package pricing and sizing, microflies, futures fly/condor.
- d'Aspremont - Identifying Small Mean Reverting Portfolios (arXiv 0708.3048, 2008; Quantitative Finance 11(3), 2011); Musaelian, Nagarajan, Villani - PCA: invariant risk metrics and representation of residuals for bond returns (SSRN, 2016); Burton, Dektor, Wheeler - Time Series Prediction of US Swap Rates (Stanford student project, c.2008): sparse baskets, flylets, PCA-residual fly via null space.
- Golub and Tilman - Risk Management: Approaches for Fixed Income Markets (Wiley, 2000); Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018); Greene - Econometric Analysis (8th ed., Pearson, 2018): PC durations, risk-target PCA weights, multicollinearity diagnostics.
