---
name: curve-pca-factor-model
description: 'PCA factor model of a rates curve (swap, OIS, govt, forward grid, futures strip, spread curve) - level/slope/curvature loadings, variance explained, stability, PCA-neutral (PC1/PC2/PC3) hedge weights and flies, PCA residuals as rich/cheap signals with z-scores, factor exposure of a book, and P&L attribution to PCs. Use when asked for PCA, principal components, eigenvectors/eigenvalues, loadings, PC1-neutral or PCA-weighted fly/butterfly/steepener (2s5s10s, 10s20s30s), "direction-neutral" or factor-neutral weights, PCA mispricing/fair value, curve residuals, is the 7y cheap on the curve, hedge ratios from PCA, DV01-neutral vs factor-neutral, level/slope/curvature risk, PC P&L explain, or whether the PCA is stable. Covers levels vs changes, covariance vs correlation, window and k choice, sign conventions, walk-forward checks, and G10 differences. Choosing between fly weightings: curve-butterflies; two-leg curve trades: curve-steepeners-flatteners.'
---

# Curve PCA factor model

A handful of orthogonal statistical factors (level, slope, curvature) explain 95-99% of curve variance, so a curve of N
points becomes three numbers per day. Mechanism for RV: (1) what is left after k factors is tenor-specific and tends
to mean-revert, so the **residual** is a direction-independent rich/cheap signal; (2) the loadings give **hedge
weights** that cancel level (PC1) and slope (PC2) risk instead of just DV01; (3) the same loadings split any book's
risk and P&L by factor. It pays when the factor structure is stable and the residual is larger than costs and carry
drag; it fails when loadings move (regime, central-bank pinning, QE) or the signal is a flow, not noise.

## When to use
- "Is the 7y cheap on the curve?", "PCA fair value / mispricing", "show curve residuals with z-scores".
- "Make this fly / steepener PC1-neutral (or PC1+PC2-neutral)", "PCA-weighted 2s5s10s", "direction-neutral weights".
- "Is this DV01-neutral package really neutral?", "what is my level/slope/curvature exposure?", "attribute P&L to PCs".
- "Is the PCA stable / how many factors / which window / levels or changes?"
- Building a PCA screen for the opportunity scan, or checking a research note's PCA claim.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap/OIS rates by tenor (spot `start=0D`) or non-overlapping forwards (`1Y1Y`, `2Y1Y` ...) | `curve_par` | daily, one snap, >= 3y (1y minimum for a levels fit) | store bp = `par_rate_pct` x 100; never mix snaps |
| Constant-maturity government par yields (fitted curve, `<CCY>-GOVT-<issuer>`) | `curve_par` | daily, >= 3y | avoids bond-ageing and benchmark-roll jumps in slope/fly series |
| Vol grid, spread curve, basis curve (when PCA is applied to them) | `vol_surface`, `swap_spreads`, `basis_swaps` | daily, 1-3y | see [extensions](references/extensions.md) |
| Book risk by tenor and daily P&L (exposure, attribution) | `positions`, `pnl` | daily | DV01 per bp, + = long duration |

Output of a screen is written to `signals` (`value` in bp, `unit=bp`, `zscore`). If an input is missing, ask for it or
hand off to `data-contract-and-adapters` / `data-quality-and-timeseries-hygiene`. Never invent values.

## Method

### 1. Choose the panel
- **Prefer non-overlapping series**: forwards (1y1y, 2y1y ... 10y2y, 15y5y ...) rather than overlapping spot tenors,
  which double-count the short-rate path. Credit Suisse used 17 non-overlapping EUR forwards on a 1y window
  (Credit Suisse, PCA Unleashed, 24 Oct 2012); ING uses generic quarterly Euribor futures as 1y forward equivalents
  (ING, No rise in rates but position for lower volatility, 4 Feb 2020). Spot tenors are fine for hedge ratios.
- Use constant-maturity or fitted-curve series for governments, not rolling bonds (Huggins & Schaller, FIRVA, 2024).
  Swap histories have breaks (IBOR to RFR); stitch via a fitted par curve, do not splice raw.
- Units bp. Same snap for every column. Drop dates with any stale column rather than filling zero (a zero corrupts
  demeaning; Tulchinsky et al., Finding Alphas, 2015).

### 2. Levels or changes, covariance or correlation
| Purpose | Fit on | Matrix | Window (default, source) |
|---|---|---|---|
| Hedge weights, factor exposure, P&L attribution, risk | daily **changes** (bp) | covariance, unscaled | 3y; 1y in fast markets (ING, Mar 2020); 5y rolling for PC3 fly weights (Citi, US Rates Weekly, 18 Jan 2019); 90bd to monitor complexity (Düring, FITRM, 2021) |
| Rich/cheap residual (RV) | **levels** | covariance | 1y = 252-261 obs (Credit Suisse, 2012); 6m window in the published UST example (BofA, Understanding the yield curve dynamic, 23 Jul 2025) |
| Rich/cheap residual when levels are non-stationary | changes, then cumulate | covariance | regress levels on cumulated factor scores, test the residual for stationarity (QF Stack Exchange, Levels from change-PCA, Jun 2015) |

- Convention in the literature: level PCA for rich/cheap, change PCA for risk (QF Stack Exchange, Levels from
  change-PCA, Jun 2015). Darbyshire insists on changes for any covariance estimate (Darbyshire, PTIRD, 3rd ed., 2022).
- **Covariance for curves, not correlation**: the vol term structure is part of the information. PC1's shape mirrors
  it, so PC1 is humped/non-parallel (Golub, BlackRock Guide to Fixed-Income Risk Management, 2023). Use correlation
  only when scales are artefacts (mixed units, index levels). With correlation-PCA the risk map must rescale by the
  column vols; the script does this.
- Zero-mean covariance is the risk convention: a 10bp/day trend has zero sample vol around its own mean but real risk
  (Golub, 2023). Script: `PCAFit(..., demean=False)` / `--no-demean` for risk fits; the default demeans, which is fine
  for an RV residual fit.
- Short half-lives shrink the effective sample: an 8-day half-life is about 23 observations (Golub, 2023). Paleologo:
  vols change fast, correlations are stable, so use a fast half-life for vols and a slow one for the correlation structure
  (Paleologo, Elements of Quantitative Investing, 2025). See `quant-covariance-estimation`.
- Need at least ~100 observations per instrument and the window must sample a regime like the one you will trade in
  (Darbyshire, 2022). Nine daily moves is not a covariance matrix.

### 3. Decompose and scale
`Sigma = E diag(lambda) E'`, columns of E = unit eigenvectors (PC loadings), lambda = PC variances, share_i =
lambda_i / sum(lambda). Score of a day: `f = E'(x - mean)`. PCs are uncorrelated by construction (if your PC scores
are correlated, the code is wrong: Darbyshire, 2022).
- **Pin the signs** (x and -x are both eigenvectors; "many analysts have fallen into this trap", Huggins & Schaller,
  2024): PC1 sum > 0; PC2 long end above short end; PC3 wings above belly; refit-to-refit flip if cosine with the previous
  vector < 0 (otherwise scores, loadings and exposures flip sign between dates; k-PC residuals are sign-invariant). Rotating new
  loadings onto the old (Procrustes) is the stricter alignment (Paleologo, 2025).
- **Scaled loadings = bp per +1 sd of the PC**: `L_i = sqrt(lambda_i) * e_i`. Tenor vol = sqrt(sum_i L_ij^2); PC i's
  share of tenor j's variance = L_ij^2 / sum_i L_ij^2. Example in Worked example 1.
- **Number of factors k.** PC1 > 95% means one factor is adequate for a directional book; otherwise 2-3. Three PCs
  typically 95-99% (Golub, 2023). For hedging and risk err towards more factors (too few understates risk; too many
  costs little: Paleologo, 2025). Tail simulation (VaR/ES at < 1%) needs 6-8 PCs (QF Stack Exchange, Bond risk
  transformations, Mar 2021). For RV residuals choose k to decide what you *want* in the residual: keep PC3 out of the
  model (k = 2) when curvature is the trade; Credit Suisse deliberately excluded PC3 for core govts and FRA-Eonia bases
  so curvature stays in the residual (2012). k = n gives zero residual, so z-scores are undefined.
- **Factor count by region** (USD swaps, 2020-21): 8-10y is one-factor; 3-6y and the long end need two; the very front
  needs three (the 3 PCs explain 99%+ beyond 3y but only 74.5% of the 1y) (Tuckman & Serrat, Fixed Income Securities,
  4th ed., 2022). Check the explained-variance of each tenor, not only the total.
- **Label on the loadings, not by assumption**: PC1 all one sign (level, not parallel); PC2 one sign change (slope);
  PC3 two (curvature). Validate against PC1 vs 10y, PC2 vs 2s10s, PC3 vs a fly (Credit Suisse, 2012). If no sensible
  interpretation exists, PCA may not suit that market (Huggins & Schaller, 2024).

### 4. Residual as a rich/cheap signal
`resid_i = actual_i - model_i`, model from the first k PCs (levels fit) in bp. **Positive = yield above model = cheap
(receive / buy bond); negative = rich.** Conventions differ across publishers (BofA curve: + cheap; Nordea, ING: + = rate
too high = cheap; BofA macro DFM: - rich); state yours and never mix a "par minus fair value" with a trade-direction-signed
z in one screen (Nordea convention caveat, Nordea, The quiet game, 12 Aug 2025).
1. Fit on the window (`pca_curve.py screen`), compute the residual for every date in the window, then
   `z = (resid - mean60)/std60` (60d, ddof=1; also a 252d percentile rank).
2. **Walk-forward check** (`--walk-forward`: for each date fit on the window strictly before it, then score that date): the
   in-sample residual is flattering because the date is in the fit (a one-day spike on a short window is absorbed into its own PC).
   Report both; a large gap means you are trading the estimator. Loadings frozen at a past date give the same
   out-of-sample residual (practitioner code notes, unpublished).
3. **Robustness**: compute the signal over 1m/3m/6m/12m lookbacks and trust only what persists in all (BofA, 2025).
4. Residual ~= the next factor: after k factors `resid ~ alpha_{k+1} e_{k+1}`, so a residual is "PC(k+1) is stretched"
   and any fly is a re-mix of the same few signals (Huggins & Schaller, 2024).
5. A residual is not tradable as such. Trade it with a structure in the **null space of the retained factors** (e.g.
   buy 7y, sell 5y and 10y): trading the 7y outright gave Sharpe ~0, while the residual model's ex-post Sharpe by tenor was 0.4-2.2 (7y best)
   (Burton, Dektor, Wheeler, Time Series Prediction of US Swap Rates, c.2008, no costs; treat as indicative).
6. Add carry: when carry+roll of the structure is a cost (negative), `months_to_breakeven = |resid| / (|carry+roll| per
   month)`; reject if it exceeds the expected reversion time (positive carry: no hurdle, it adds to the edge). ING rejected a
   14bp "too flat" EUR 1y1y-10y1y steepener because roll was -15.5bp per 3m (about 5.2bp/month): break-even only if the residual
   closed within about 2.6 months (ING, Deconstructing the EUR yield curve, 15 Jan 2020).
   See `fi-carry-and-rolldown`, `quant-mean-reversion-ou` for half-lives.
7. Exit: residual back through zero (Credit Suisse, 2012). Scale down when the edge shrinks even if direction holds
   (Citi, US Rates Vol Lab, 14 Jan 2019).

### 5. PCA-neutral weights (script: `pca_curve.py neutral`)
Work in DV01 space: `s` = DV01 per bp, + = long duration, P&L = -s . dy. Exposure of a package to PC i is `(E' s)_i`
(with correlation-PCA use `E'(sigma * s)`). Neutral means exposure = 0 to PC1..PCm. The hedging order rule: hedge every
factor of lower order than the one you want exposure to (Huggins & Schaller, 2024).
- **Fly, body fixed (exact):** legs wing a, belly b, wing c; for m = 2 solve the 2x2 system
  `w_a e_a,k + w_c e_c,k = - w_b e_b,k` (k = 1,2). With the belly fixed at +1 (receive) and a PC1/PC2-neutral result
  the package is a pure PC3 bet. Warn if cond(M) > 1e8 and review if any |wing weight| > 3x belly (a highly asymmetric
  fly is a disguised slope trade: Düring, 2021); skip if > 20 (practitioner code notes, unpublished). Neutrality does
  not depend on whether loadings are scaled by sqrt(lambda).
- **Two legs, PC1-neutral:** `w_short = - w_long * e1_long / e1_short` (long leg +1). Not DV01-neutral by design.
- **Fly from PC3 loadings:** PCA on just the three points; weights = PC3 loadings, normalised belly = +1. Orthogonal to
  that PCA's PC1/PC2, generally not DV01-neutral (QF Stack Exchange, Fly to eliminate PCA exposures, Nov 2018).
- **Minimal-adjustment projection (any package t, any set H of PCs):** `min ||x||^2 s.t. E_H'(t + x) = 0`, closed form
  `x = - E_H E_H' t` for orthonormal E; to keep chosen buckets fixed, restrict x to the free buckets (do NOT
  sub-select the covariance matrix: that changes the eigenvectors) (Darbyshire, 2022, section 23.1). Preferred over
  "divide by PC1 loading", which needs sum(t) = 0 and gives absurd weights such as [1, inf, -1] when PC1 = [-1, 0, 1]
  (QF Stack Exchange, 2s5s10s directionality, Jun 2018).
- **Degrees of freedom:** each neutralised PC removes one. Three instruments, PC1 and PC2 neutral: only a multiple of
  PC3 remains. To neutralise PC3 add a fourth leg; for small residual PC3 exposure it is not worth the cost (Worked
  example 1: PC3 residual 0.007 per 100).
- **Rescale to bond/futures DV01s** after estimating on constant-maturity series (Huggins & Schaller, 2024).
- **Method comparison (EUR 2s5s10s, in-sample Jan-Jun 2016, out-of-sample Jul-Dec 2016):** PCA -2.215/2/-0.648,
  min-variance -1.650/2/-0.794, regression -1.960/2/-0.756; OOS daily-change stdev raw 0.8399, regression 0.7609,
  min-variance 0.7628, **PCA 0.8689 (highest)** (QF Stack Exchange, 2s5s10s directionality, 2018). PCA weights are an
  exposure statement, not a variance-minimiser: compare against `quant-regression-and-hedge-ratios` and `curve-butterflies`.
- **DV01-neutral is not factor-neutral.** With a humped PC1 (0.279 at 2y, 0.334 at 7y, 0.272 at 50y), DV01-neutral
  pairs keep 3.8-16.7% of an outright's level exposure (internal research note, 2026). 50/50 flies (2s5s7s to 3s5s30s)
  had R^2 of 43-69% with the belly (BofA, 23 Jul 2025). A DV01-neutral steepener is not PC1-neutral.
- **Tight pairs: neutralise PC1. Wide pairs (5y/30y): neutralising PC1+PC2 removes the slope bet that *is* the trade**
  (5y/30y PC1+PC2-neutral: P&L -739.8bp, hit rate 0.53 to 0.20) (internal research note, 2026). State the factor
  exposure of the sizing rule before quoting P&L.

### 6. Book exposure and neutralisation
`exposure_i = sum_buckets s_bucket * loading_i,bucket`. Neutralise each PC with a dedicated trade: one point for PC1,
a pair for PC2, three points for PC3 (Credit Suisse, 2012). Check with the identity: risk = 1000 x PC1 loadings must map to
PC risk [1000, 0, ...]. Scaled risk: report sensitivity to a +1 sd move of PC1/PC2/PC3 instead of a fixed bp (QF Stack
Exchange, Steepener/Flattener/Butterfly sensitivity, 2021-2023); `risk_in_pc(..., per_sd=True)`. Targeted risk split: with
`beta = W'w` (W = eigenvectors), PC n carries `R_n = beta_n^2 lambda_n / sigma^2` of the variance; set `beta_n = sigma sqrt(R_n / lambda_n)` and
`w = W beta` to build a package with a chosen risk distribution across PCs (all risk in the last PC gives a PC-neutral structure; Lopez de Prado, 2018). Concentration: risk share
`theta_i = f_i^2 lambda_i / sum f^2 lambda`, `H = 1 - exp(-sum theta log theta)/N` tells whether "diversified" RV
trades are one PC bet (Lopez de Prado, Advances in Financial Machine Learning, 2018).

### 7. P&L attribution to PCs
- Linear P&L is invariant if risk and moves transform with inverse-transpose matrices; for orthonormal E:
  `P&L = -sum_i (E's)_i (E'dy)_i`, one term per PC (script `pc_pnl`). Use **raw, non-demeaned** moves (Darbyshire, 2022).
  Truncating to 3 PCs leaves a remainder; report it (PCs 4-7 carried material P&L in the QF example).
- Do not run PCA on standardised data and then push unstandardised DV01/bp through its eigenvectors: P&L will not sum
  (QF Stack Exchange, Attribute P&L to PCA vectors, Jan 2022).
- For trade-level attribution regress daily P&L on dPC1, dPC2, dPC3 **plus a squared-move (gamma) term and carry**, so
  convexity does not leak into the residual. Daily convexity is unidentified (t 0.9-2.1); read it at trade level
  (t 2.1-5.4) and use incremental R^2 because carry/slope and level/convexity are collinear (internal research note, 2026).
- Convex payoffs must show a smile, not a ramp: bucket P&L by size of the underlying move (same note).
- Non-linear books: sequential full revaluation. Move the curve along PC1, then PC2, ..., choosing each step so the path lands on the
  end curve, and reprice after each step; the P&L differences are the PC attribution including convexity. Report the unexplained
  remainder (QF Stack Exchange, Attribute P&L to PCA vectors, Jan 2022).

### 8. Stability gate (run before trusting any weight)
1. `rolling_stability`: variance shares and cosine of each PC with the prior window. PC1 is very stable; higher PCs
   have rare large jumps when neighbouring eigenvalues are close (Paleologo, 2025). Flag cosine < 0.9 (house default).
2. **Walk-forward vs full-sample**: PC1-neutral 5y/30y printed +1408bp walk-forward vs -66bp full-sample (1,474bp gap);
   walk-forward 5y leg ranged $70.6k-$134.9k across 2020-22 ZIRP (internal research note, 2026). Fit weights walk-forward,
   measure exposure on one fixed ruler, reject sizings whose two results diverge.
3. Weight drift is normal: USD PC3 2-5-10 weights -0.9:1:-0.7 (3 Feb 2017), -0.52:1:-0.57 (20 Apr 2018), -0.36:1:-0.72
   (4 Oct 2019), -0.32:1:-0.73 (17 Feb 2023) (Citi US Rates Weekly, dates as listed). Re-estimate on a schedule.
4. Complexity: Herfindahl `H = sum lambda^2 / (sum lambda)^2` on a 90bd rolling PCA. High H: one factor dominates and one
   hedge instrument suffices; falling H means more hedge instruments (Düring, 2021; US/DE 2014-20 range 0.57-0.95).
5. Regime: fit within the relevant policy regime. Models break near the lower bound (Fed funds <= 50bp, Citi, US Rates Vol Lab, 1 May 2017); exclude ZLB for
   USD, use the negative-rate period for EUR (Citi, Rates Vol Lab, 17 Jan 2020). Credit shifts correlate PC1 and PC2: use
   yield minus CDS or shadow rates as input near regime breaks (Huggins & Schaller, 2024).
6. PCA bases drift with a characteristic time of a couple of years, so residuals stop being like-for-like over longer windows;
   pick the window from a broad range, not a local optimum (Burton, Dektor, Wheeler, c.2008).
7. Hedge ratios drift with macro regime; mean-reversion trades are "nearly always off sides" across regimes
   (Tuckman, Macro-Awareness in Relative Value Trading, Lehman, Oct 2003).

## Worked examples

**1. Scaled loadings and a PC1/PC2-neutral 10s20s30s fly (Tuckman & Serrat, 4th ed., 2022, Ch. 6, Table 6.5-6.6).**
USD 3m-LIBOR swaps, daily changes 1 Jun 2020-16 Jul 2021. Scaled loadings (bp per 1 sd; level / slope / short-rate):
10y 3.44/0.07/-0.23; 20y 3.73/1.02/0.17; 30y 3.77/1.35/0.36. Tenor vol of the 5y = sqrt(2.28^2+1.12^2+0.02^2) = 2.54bp/day.
Receive 100 of 20y (DV01 0.17064 per 100); DV01s per 100: 10y 0.09347, 30y 0.23600. Solve level and slope exposure to zero:
**pay 49.56 of 10y and 53.60 of 30y** (risk weights vs the 20y DV01: 27.1% and 74.1%, total 101.2%). Most of the hedge sits
in the 30y because its loadings resemble the 20y; the extra DV01 is needed because 10y moves little with level/slope.
Residual PC3 exposure = 0.007 per 100 (< 1 cent), so a fourth leg is not worth its cost. `--selftest` reproduces -49.6/-53.6
from the rounded loadings.

**2. Minimal-adjustment PC1 hedge (Darbyshire, PTIRD, 3rd ed., 2022, Ex. 23.1).** Buckets 2y/5y/10y/30y, PC1 =
[0.65, 0.59, 0.44, 0.20], trade pay 5y / receive 2y and 10y; source risk sign (+ = pay) t = [-1, 2, -1, 0], sum 0 (in this skill's
+ = receive convention s = -t; PC1-neutrality is sign-invariant). Divide-by-loading gives [-0.89, 1.94, -1.30, 0]. Minimal adjustment with the 30y locked: [-1.07, 1.94, -1.05, 0], "closer to the original 2s5s10s".
Unlocked, the adjustment also touches the 30y (about -0.02 there). Check: PC1 . result = 0.

**3. Factor neutralisation of a book (Credit Suisse, PCA Unleashed, 24 Oct 2012, Exhibit 31).** Net DV01 -85k/bp,
PC1/PC2/PC3 exposures -16.09/-23.34/+20.76. Hedges: PC1 +50.19k/bp in 5y1y (loading 0.3205: 50.19 x 0.3205 = 16.09 -> PC1 = 0);
PC2 -74.01k in 1y1y and +78.75k in 9y1y; PC3 -32.14k in 1y1y, +28.80k in 9y1y, -21.10k in 30y10y. Loadings (PC1/PC2/PC3):
1y1y 0.2469/-0.16/0.22; 5y1y 0.3205/0.00/0.02; 9y1y 0.2346/0.14/-0.21; 30y10y -0.0559/0.44/0.36. PC1-only hedges blow up where
PC1 is near zero (the EUR long end, hedge ratios 6-8x), so use PC1+PC2 there.

**4. P&L by PC (QF Stack Exchange, Attribute P&L to PCA vectors, Jan 2022).** Seven USD swap tenors 2y-30y; book sensitivities
dPV/dy (in $k, source sign) +10, +30, -5, +20, -10, +20, -60; moves +1, -1, -1, -2, -3, -4, -5bp. Tenor P&L = +195.
By PC (risk in the source's dPV/dy sign, so P&L = risk x move; move; P&L): PC1 -2.8, -6.28, +17.6; PC2 -33.1, -3.29, +108.9; PC3 -22.3, -1.60, +35.6; PC4 +7.2; PC5 -8.4;
PC6 +9.4; PC7 +24.6; sum 195. Reading: the book made money on slope (PC2), not level. Truncate at 3 PCs and 32.8 of 195 sits in
PCs 4-7: report it as unexplained. The asker's wrong (rescaled-eigenvector) method gave -131,025. `--selftest` reproduces the sum.

**5. From residual to trade, and why carry decides (ING, Rates Strategy, 4 Feb-9 Mar 2020).** EUR 4y-30y PC1-neutral steepener,
weights 2.1:1 (receive 4y, pay 30y): entry 103.75bp, target 123.75, stop 93.75; "18bp too flat" on PC1 residual; carry +0.7 + roll
+0.8 = +1.5bp/3m. Outcome: half cut at 102.75, rest exited 85.0 (loss) as the crisis re-priced the long end. Lessons: PC1-neutral
over 3y can still be directional within a regime (sub-sample, hedge the identified factor separately); in a crisis use DV01
weights and simple spreads for executability; shorten the window 3y to 1y.

More worked data (UST 6m PCA loadings and residual z-scores, PCA vs 50/50 fly table, swap-spread and EGB PCA, Nordea
fair-value fields, Citi PCA-fly weight history): [references/worked-examples.md](references/worked-examples.md).

## Signals & interpretation
- Residual is a **dislocation, not a trade**. Ask why (Darbyshire rejected a 9-day PCA residual: covariance insignificant, PC3/4
  carried 24% of variance, residual inside daily ranges, possible reversal of an earlier outlier). Dutch pension reform (FTK II)
  moved EUR 20y+ residuals in 2012 for structural reasons (Credit Suisse, 2012); flow-driven sectors (EUR 25-35y in Mar 2020)
  can stay off the model (Nordea, EUR Rates Flash, 17 Mar 2020).
- Screen thresholds (house defaults, label as judgement): candidate when |z60| >= 2 **and** the sign agrees on 1m/3m/6m/12m
  lookbacks **and** |resid| >= max(1.5bp, 2x round-trip cost). A residual near 1bp is "very moderate/weak" (Nordea, EUR Rates Flash,
  23 May 2019); |z| below 0.5 sigma is small versus model error (BofA, A new UST macro framework, 15 Oct 2024); a 1bp bid-offer
  killed sparse-fly convergence trading (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008).
- Stronger when several lenses agree: value (PC residual) + carry/roll + z-score + macro/flow reason. Plot value vs carry for
  PC1-neutral structures: the frontier slope roughly doubled (-1.27 to -2.70) on a direction-neutral basis (ING, 15 Jan 2020).
  Simple z-scores and PC-relative value can point opposite ways; check both (Citi, US Rates Vol Lab, 12 Dec 2016).
- PCA-weighted flies: report 3m correlations to 10y, 2s10s, 5s30s (Citi, All it takes is a little push, 4 Oct 2019). Equal-weight 10-20-30
  had 96% correlation to 5s30s vs mostly low (34%) for the PCA fly (Citi, 18 Jan 2019). Pre-trade check: rolling 126d beta of the
  structure's P&L to dPC1; |beta| > 0.2 means it is not PC1-neutral in recent data (practitioner code notes, unpublished).
- Sign of factor moves: a score vector [0.42, -0.35, -0.15] on a day is a bear-flattening day (Credit Suisse, 2012). The
  directional bias comes from where PC1 peaks, so read it from the current loadings: EUR forwards with PC1 largest at
  1y1y-5y1y imply bear-flattening and bull-steepening are more likely (Credit Suisse, 2012); for USD 2015-20, with PC1
  heavier at the long end, 11 of 16 directional months were bull-flat or bear-steep (Golub, 2023).
- Cross-check with a macro layer: regress PC1/PC2 on policy rate and macro PCs for level (`macro-fair-value-models`); PCA alone
  says nothing about the level of the whole curve.

## G10 differences
- USD: PC1 humped (peak near 7y in the SOFR example), so DV01-neutral is clearly not PC1-neutral; stitch history across LIBOR/SOFR.
- EUR: use non-overlapping forwards; PC1 > 80-99% depending on window; long end is flow/regulation-driven; EGB panels exclude PC3.
- GBP: very similar shape to USD; EUR-GBP spread PCA flags cross-market kinks. JPY: PC1 mostly long end (YCC), regime-split.
- CAD/AUD/NZD/CHF/SEK/NOK: short or policy-divergent samples flip betas; use rolling fits, k = 2, and cross-market residuals.
- Per-market numbers and sources: [references/g10-market-notes.md](references/g10-market-notes.md).

## Pitfalls
- Wrong input: PCA on PV01 or on price levels (it describes your risks, not market moves); on overlapping spot tenors for
  rich/cheap; on rolling bonds (roll jumps) instead of constant maturity.
- Sign flips and rank swaps between refits (neighbouring eigenvalues close, esp. vol surfaces: PC2 and PC3 can swap). Align or
  track factors by identity (Citi, Asia FX and Rates Strategy, 13 Aug 2026).
- Eigenvalues/eigenvectors from a short window are noisy (Paleologo: with n series, T observations and eigenvalues in units of the noise variance, a factor below the 1+sqrt(n/T)
  threshold is not detectable and its eigenvector is noise; sample eigenvalues are biased up, so shrink them). PCA weights "might be very unstable with small covariance changes" (QF Stack Exchange, Nov 2018); near-zero
  determinant gives explosive weights.
- When one leg is pinned (2y barely moving before hikes) a 2s/x/y fly behaves like an x/y curve trade whatever the weights.
- Regimes: ZLB, QE/YCC, forward guidance, Fed on hold (suppresses front-end PC1 loadings; BofA, UST RV Primer, 2 May 2022). PC shapes
  in Jan vs Mar 2020 differed materially (Golub, 2023: 3m-point PC1 shock -8bp on 31 Jan vs +138bp on 16 Mar, annualised 1 sd).
- PC1-neutral can still be convex in level: EUR PC1-neutral 2s7s10s vs PC1 quadratic R^2 0.617, fly cheapens both sides of an
  inflection near spot 7y ~ 0% (ING, 15 Jan 2020). Scatter before trading.
- PCA-neutral != tradable: PCs cannot isolate local positions (e.g. 20s25s30s); PC risk buckets are hard to hedge; for desk
  ladders prefer Jacobian/bump transforms (`fi-risk-dv01-and-transforms`) (QF Stack Exchange, PCA ladder transform, Sep 2023).
- Look-ahead: historical fly series built with today's fixed weights; rolling betas/z-scores must be lagged to t-1.
- Mean-reverting basket of the smallest eigenvalue is low variance, wide support and cost-dominated; stationarity does not
  imply profit (Cuturi & d'Aspremont, 2015).
- One regime-specific measurement is not a strategy result: with n_eff ~ 7.5 per structure, quote sizing comparisons as exposure
  results (internal research note, 2026).

## Output
For a screen: a table with columns `tenor/structure | actual | model | resid_bp (+ = cheap) | z60 | pctl252 | resid 1w ago |
resid 1m ago | carry+roll 3m | months_to_breakeven | walk-forward resid`, plus fit metadata (`mode`, window, k, share of PC1/2/3,
cosine with previous window, number of obs). For a hedge: DV01 weights (+ = receive), notionals (weight / DV01 per unit),
factor exposure of the final package to PC1/PC2/PC3 in DV01-bp, cond number, leftover 3m correlations to 10y / 2s10s / 5s30s,
walk-forward vs full-sample weights. For attribution: per-PC table (risk, move, P&L) with the unexplained remainder. Charts:
residual bars by tenor with 1y range whiskers, loadings of PC1-3 with variance shares, fly weight history. Write signals to the
`signals` table and hand candidates to `rv-trade-idea-writeup`, ranked via `rv-composite-scoring`.

## Scripts
- [`scripts/pca_curve.py`](scripts/pca_curve.py): `PCAFit` (levels/changes, covariance/correlation, optional zero-mean, sign pinning, scaled loadings,
  k-factor model/residual), `resid_series` (in-sample and out-of-sample walk-forward), `level_resid_from_changes`, `neutral_weights` (exact PC
  neutral flies), `min_norm_neutral` (minimal adjustment with locked legs), `pc3_weights`, `risk_in_pc`, `pc_pnl`,
  `rolling_stability`, `herfindahl`. CLI `fit | screen | neutral` reads a canonical `curve_par` CSV/Parquet (`--start 0D` spot grid, or e.g. `--start 1Y,2Y` for forward columns
  `1Yx1Y` ...; filter the table to a non-overlapping set first).
  `python scripts/pca_curve.py --help`. `--selftest` checks a simulated 3-factor curve with known loadings/vols, the injected
  residual size (in-sample and out-of-sample, the latter on a spike an in-sample fit absorbs), the Tuckman & Serrat 10s20s30s weights, the
  Darbyshire minimal-adjustment hedge (locked and unlocked), zero-mean PCA, P&L-by-PC additivity and the CLI paths.

## Related skills
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weighting alternatives (50/50, DV01, regression) and fly residuals.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): beta-weighted spreads and directionality by regime.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): non-overlapping forward panels that feed the PCA.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): parametric (Nelson-Siegel, affine) alternatives and term premium.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 conventions, key-rate/Jacobian transforms vs PC buckets.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry/roll and months-to-breakeven.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life of PCA residuals and fly series.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score windows and ranking.
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): EWMA/shrinkage covariance feeding the PCA.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): regression and min-variance hedges to compare with PCA weights.
- [quant-regime-detection](../quant-regime-detection/SKILL.md): choosing and splitting estimation regimes.
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): P&L explain across carry/roll/factors.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): walk-forward and multiple-testing control for PCA screens.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): PC-shock scenarios and plausibility.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro regression on curve PCs for level.
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): vol-surface PCA and macro-vol regressions.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md) and [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): PCA on spread curves and EGB cross-sections.
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): fitted constant-maturity inputs and bond selection after the PCA.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): curve ids, tenors, day counts per market.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) and [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): input tables and hygiene.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and [rv-composite-scoring](../rv-composite-scoring/SKILL.md): hand-off and ranking.
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): where the PCA screen plugs into the end-to-end scan.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-structure curve trades, where PCA-neutral weights remove the exposure being traded.
- [xccy-basis](../xccy-basis/SKILL.md): PCA on cross-currency bases.
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): implied correlation and curve options.

## References
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022), Ch. 6 and App. A6: USD swap PCs by tenor, PCA hedge recipe, 10s20s30s PCA fly, 3-rate PCA construction, factor count by region.
- Credit Suisse Fixed Income Research - Interest Rate Strategy: PCA Unleashed (Pelata, Giannopoulos, Haworth, 24 Oct 2012): algorithm, residual convention, hedge formulas, factor neutralisation, EUR/EGB/GBP trades.
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022), Ch. 14-16, 21, 23: PCA procedure, residuals, P&L attribution, minimal-adjustment PCA hedge, honest limits.
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): factor-model maths, residual ~ next factor, hedge-order rule, CDS-adjusted and shadow-rate inputs, higher-PC trades.
- Düring - Fixed Income Trading and Risk Management (Wiley, 2021): covariance vs correlation, k-factor residuals, factor-model hedge equations, rolling Herfindahl.
- Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023); Golub & Tilman - Risk Management: Approaches for Fixed Income Markets (Wiley, 2000): scaling, PC1 as vol term structure, PC durations, shock plausibility.
- BofA Global Research - US Rates Viewpoint: Understanding the yield curve dynamic (Braizinha, 23 Jul 2025); Introducing a new UST macro framework (Braizinha, 15 Oct 2024); Understanding Principal Components (Braizinha, 21 Aug 2020); Fund duration & curve positioning: a PCA regression approach (Swiber, Zhang, Braizinha, 4 Jun 2024): PCA residual z-scores across lookbacks, PCA vs 50/50 flies, macro layer, return-based PCA regression.
- BofA Global Research - US Rates Primer: UST RV Primer: A hitchhikers guide to RV on the UST curve (Zhang, Braizinha, Axel, 2 May 2022); US Rates Watch: Monthly rates models (7 Apr 2025, 4 Aug 2025); Global Rates Weekly: Start of rates bite (Cabana et al., 2 Oct 2026): illustrative eigenvectors, PCA/macro fair value, EGB spread residual.
- ING Global Markets Research - Rates Strategy: Deconstructing the EUR yield curve (15 Jan 2020); No rise in rates but position for lower volatility (4 Feb 2020); EUR crisis trades (3 Mar 2020); March ECB: QE or bust (9 Mar 2020): PC1 residuals on non-overlapping forwards, value vs carry, PC1-neutral trades and outcomes.
- Citi Research - US Rates Weekly (Mathai et al.): Going nuclear (on the curve) (3 Feb 2017), What to expect when you're expecting a turn (20 Apr 2018), The rocky road to a steeper curve (18 Jan 2019), Deal or no deal: Rates implications (10 May 2019), All it takes is a little push (4 Oct 2019), Eat, pay, spend (27 Mar 2020), Time for moderation (17 Feb 2023): PCA-weighted fly weights (PC3, 5y window) and correlation checks.
- Citi Research - Short-End Notes (Vazquez Plata, Williams, 21 Aug 2026); Asia FX and Rates Strategy: Decomposing Global Rate Drivers Across EM Asia 5y5y (Goh, Garg, 13 Aug 2026): swap-spread PCA residuals; rolling PCA hygiene, factor identity across refits.
- Citi Research - Rates Vol Lab: In search of cheap vol (17 Jan 2020) and US Rates Vol Lab notes (Fair value vs seasonality, 1 May 2017; 2016-2019 notes): vol-surface PCA, regression on curve PCs, regime samples.
- BofA Global Research - A simple framework for swap spread relative value (Axel, Satko, Cross, 2 Jun 2016); Many EGBs, one simple value tool (Satko, 21 Mar 2018): PCA on spread curves and cross-sections, dislocation indices.
- BofA Global Research - US Vol Primer: A Guide for the Perplexed (Braizinha, 11 Mar 2024): hierarchical PCA of the vol grid, de-directionalising vol residuals.
- Nordea Markets - EUR rates: The quiet game (Svendsen, 12 Aug 2025); How about that outright receiving (26 Sep 2025); Pushing back (17 Jan 2024); EUR Rates Flash (Vainikainen, 23 May 2019, 17 Mar 2020): PCA fair value/mispricing fields, loadings of structures, sign conventions.
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025), Ch. 7: eigenvalue bias, factor-count rules, eigenvector turnover and Procrustes alignment.
- Tuckman - Macro-Awareness in Relative Value Trading (Lehman Brothers LMR Quarterly, Oct 2003): hedge ratios drift with macro regime.
- Salomon Brothers - Understanding the Yield Curve, Part 7 (Ilmanen, Iwanowski, Feb 1996): factor counts and caveats on PCA interpretation.
- Burton, Dektor, Wheeler - Time Series Prediction of US Swap Rates (Stanford project paper, c.2008): residual via factor-null-space fly, ex-post Sharpe by tenor.
- d'Aspremont - Identifying Small Mean Reverting Portfolios (Quantitative Finance, 2011; arXiv 2008) and Cuturi & d'Aspremont - Mean-Reverting Portfolios: Tradeoffs Between Sparsity and Volatility (2015): sparse baskets and cost hurdles.
- Musaelian, Nagarajan, Villani - PCA: invariant risk metrics and representation of residuals for bond returns (SSRN, 2016): rotation-invariant PC risk, flylets.
- Quantitative Finance Stack Exchange threads: "How to adjust butterfly 2s5s10s swaps trade for directionality?" (2018/2021), "Attribute P&L to PCA vectors (swaps)" (Jan 2022), "Hedging a trade for PCA component neutrality" (Nov 2019), "Construct a butterfly interest rate portfolio to eliminate PCA exposures" (Nov 2018), "Reproducing levels when PCA has been done on changes" (Jun 2015), "What are some advanced methods for bond risk transformations?" (Mar 2021), "Can PCA be used to transform a ladder of interest rate risk?" (Sep 2023), "PCA and risk bucketing" (Feb 2019): community-derived formulas and worked numbers (treat as secondary).
- bquanttrading blog - Principal Component Analysis, Part II (2015, updated 2016): level-covariance PCA fly, sizing and OU half-life (secondary).
- Rates traders' chat on 10y10y vs 20y10y (21 Jan 2026): informal, unverified PCA 5:1 weighting idea.
- JPM Global Rates (Talk is Cheap, 30 May 2024; Cross currency basis outlooks, 26 Sep 2024 and 5 Jun 2025), Goldman Sachs Global Rates Trader (2 Oct 2026), Citadel Securities (25 Aug 2026), Clarus Financial Technology (1 Jul 2014), RiskVal (Future CTD Scenario Analysis, 25 Apr 2024): cross-market, spread, scenario and benchmark-hedge extensions used in the reference files.
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): PCA risk-share concentration, risk-targeted PCA weights, variance-threshold selection.
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): missing data must be NaN, not zero; Ait-Sahalia & Xiu - Principal Component Analysis of High-Frequency Data (JASA, 2019): realised PCA.
- Internal research note on factor-neutral sizing and loading instability (unpublished, 2026): DV01-neutral vs factor-neutral, walk-forward instability, PC P&L attribution.
- Litterman & Scheinkman - Common Factors Affecting Bond Returns (Journal of Fixed Income, 1991) (external): the three-factor result.
