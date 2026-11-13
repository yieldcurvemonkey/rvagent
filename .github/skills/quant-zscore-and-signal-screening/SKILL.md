---
name: quant-zscore-and-signal-screening
description: Standardise and screen relative-value series (curve spreads, flies, forwards, swap spreads, ASW, basis, vol ratios, positioning) with causal z-scores, percentiles and robust median/MAD statistics over several lookbacks, residual z-scores from fair-value or PCA models, and cross-sectional ranking tables; then test whether a z-score is tradable (reversion speed, persistence across windows, multiple testing). Use when asked "is this cheap or rich vs history", z-score, standard deviations from the mean, percentile, 3m/1y/3y/since-2000 lookback choice, sigma move, rank the cheapest across curves or markets, rich/cheap heatmap or screen, top-N flags, winsorize, MAD, EWMA z, dislocation index, residual z, or how to avoid look-ahead and data-snooping in a screen.
---

# Z-scores and signal screening

A z-score says how far a series sits from its own recent history, in units of that history's noise. It is the common
currency of every rich/cheap screen, but on its own it is only a *distance*, not a forecast: it ignores how fast the
series reverts, which window defined "normal", and how many other series were scanned. This skill fixes the
definitions (causal, sign, window, robust variants), gives the decision rules for lookbacks and thresholds, and says
what must be true before a flagged z becomes a trade candidate. Detailed per-source conventions and extra worked
tables are in [references/](references/).

## When to use
- "Is 5s30s / this fly / 5y5y / the 10y ASW cheap vs history?", "what is the 1y z and 3y z?", "show percentile".
- Building or reading a rich/cheap grid (3m z colour buckets, top-3 per column, heatmaps) across curves, flies,
  forwards, bonds, vol points or markets.
- Choosing a lookback (3m, 1y, 3y, since-2000), a threshold (1.5, 2, 3) or a robust variant (median/MAD, winsorise,
  EWMA, log-then-z).
- Residual z of a model (PCA, regression, fitted bond curve, macro fair value): which z to quote and how to demean.
- Cross-sectional ranking: cheapest/richest across tenors, EGBs, G10 markets; ranking with vol-matching or neutralising.
- Deciding whether a screen hit deserves a trade, or auditing a screen for look-ahead, ratio artefacts and
  multiple-testing.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap/OIS rates (spreads, flies, forwards are derived in bp) | `curve_par` | daily, one `snap`, >= 3y (>= 5y for a since-start window) | `par_rate_pct` x 100 = bp; never mix snaps inside one series |
| Swap spreads / ASW / bases | `swap_spreads`, `basis_swaps`, `ccp_basis` | daily, >= 1y | state the spread convention of the series (see `fi-g10-market-conventions`) |
| Bond yields vs fitted curve, constant-maturity series | `bond_quotes`, `curve_par` (`<CCY>-GOVT-<issuer>`) | daily, >= 1y | screen constant-maturity or fitted series, not rolling individual bonds |
| STIR packs, futures spreads | `stir_quotes`, `fut_quotes` | daily | roll-adjusted; drop roll-window days |
| Normal vol points, vol ratios | `vol_surface` (`nvol_bp`) | daily, >= 1y (>= 3y for regressions) | de-trend rate directionality before z-scoring a vol residual |
| Positioning, flows | `positioning`, `flows_trades` | weekly/daily, 3-5y | publication lag must be modelled |
| Model residuals | output of the model skill | same as the model | actual minus model fair value, in bp |
| Results | `signals` (`value`, `unit`, `zscore`, `horizon_days`) | one row per package per date | a signal dated t uses data known at t; positions start t+1 |

If a series is shorter than the longest lookback, say so and leave that window blank; do not shrink the window
silently. Missing observations stay missing (never forward-filled, never 0). Ask the user or the
`rv-data-engineer` agent for missing history. Never invent numbers.

## Method

### 1. Decide what is being z-scored (this matters more than the window)
| Quantity | z-score it? | Why / fix |
|---|---|---|
| Spread, fly, forward-spread, swap spread, basis (in bp) | yes, level | roughly stationary; check half-life (step 7) |
| Outright yield level | prefer z of h-day changes | levels are not Gaussian and trend; "z-scores on 5-day changes are perhaps better" (BofA, UST RV Primer, May 2022) |
| Ratio (q = A/B) | only if B is not a common factor | a shared denominator moves every ratio at once (step 5) |
| Model residual (actual - model) | yes, **after subtracting the residual's own mean** | step 4 |
| Skewed positive series (realised vol, CDS) | log first, then z | removes positive skew (Citi, QIS Corner, Aug 2026) |
| Vol residual | regress out rate direction first | normal vol ~ F x lognormal vol, so it moves with forwards (BofA, US Vol Primer, Mar 2024) |
| Positioning | z and percentile, both | aggregate z can hide offsetting legs; decompose by contract (JPM, Canary in a coal mine, Feb 2020) |

### 2. Causal z-score (default)
`z_t(L) = (x_t - mean(x_{t-L+1..t})) / std(x_{t-L+1..t}, ddof=1)`

- Signal at close of t, trade at t+1 (lag 1; test lag 2 and 5). Warm-up: no value until L observations exist
  (internal backtest spec, Oct 2026).
- A full-sample or since-inception mean/std is look-ahead: use rolling or expanding windows only (Palomar, Portfolio
  Optimization, 2025; Willer and Saunders, Trading Global Macro Markets, 2026). A sell-side "since 2000" z that was
  computed once on the full history is legitimate for a *live* read but not for a backtest.
- **Window includes today (dashboard convention) vs excludes today (entry-signal convention).** Including x_t caps
  |z| at (L-1)/sqrt(L): 4.36 for L=21, 7.81 for L=63, 15.8 for L=252, and shrinks every z by roughly 1/L. Use inclusive
  to match published screens; use `exclude_current=True` when judging "is today's print abnormal vs the past" or
  backtesting entries. Always state which.
- Std floor: if std is ~0 (frozen series), return NaN, not a huge z. Report `stale_days`.
- EWMA variant: `mu_t, var_t` exponentially weighted with halflife 21 (lambda ~0.97), computed on data to t-1. Use for
  vol-normalised sigma moves (BofA, Systematic Flows Monitor, Jun 2025 use lambda 0.97).
- Do not centre a z of *returns* on a short-sample mean: the SE of a 1y daily mean is about 2.5x the true mean, so a
  zero mean is the better centre for second-moment scaling (Hasbrouck, Empirical Market Microstructure, 2004 notes).

### 3. Lookback ladder (report several, never one)
| Window | Obs (daily) | Answers | Typical use |
|---|---|---|---|
| 1m / 3m | 21 / 63 | "is it stretched *now*"; fast dashboards | tie-breaker, event days, fly tables 1m/3m/6m (Citi, US Rates Weekly, Jan 2019) |
| 1y | 252 | default RV window for spreads, flies, forwards, ASW | primary z (Citi, BofA, GS use 3m-1y) |
| 3y | 756 | "is it stretched in this regime" | break ties between candidates |
| since-start (>= 5y, 2000/1997/2002) | all | "is the *level* extreme historically" | entry level judgement; regime-consistent sample only |

Rules:
- The long window judges entry level; the recent window breaks ties (Citi, Forward steepener and vol divergence,
  Jun 2023). Disagreement is information (worked example A).
- Shorten to 1y when markets are moving fast (ING switched 3y to 1y in Mar 2020; ING, EUR crisis trades, Mar 2020).
  A short window gives a volatile estimate, a long window is slow to detect breaks (During, FITRM, 2021).
- Fit/regress on a regime-consistent sample: exclude the zero bound for USD macro-vol, use the negative-rate period
  for EUR (Citi, Rates Vol Lab, 2019-2020). Check the relationship is still on: GBP basis vs policy spread R2 was 67% in
  1H24 and 0% after June (JPM, Cross currency basis 4Q24 Outlook, Sep 2024).
- Structural drift (yields fell for 40 years): use rolling 3y z, and confirm results hold for 3-10y windows
  (Willer and Saunders, 2026, Ch15).
- Short windows inflate z in calm periods: a 62-day window made a 4bp EUR 10y swap-spread move a 5.7 sd event
  (GS, Market Movers, 30 Sep 2026). Always print the raw move next to the z.
- Rule of thumb (practitioner, not sourced): window >= 3-5x the half-life of the series, otherwise the "mean" is the
  reversion path itself and z is always near 0.

### 4. Residual z-scores (model-based)
`resid_t = actual_t - model_t` (bp; positive = high yield/spread vs model = cheap for a receiver)
`z_t = (resid_t - mean_L(resid)) / std_L(resid)`

- **Subtract the residual's own mean.** A persistently rich or cheap line has a large raw residual and a small z
  (worked example C). Residual z, not raw residual, is the screen statistic; keep both columns.
- Use 2-3 PCs, never all n (all n gives zero residuals). Trust a PCA residual only if it persists across 1m/3m/6m/12m
  windows (BofA, Understanding the yield curve dynamic, Jul 2025). PCA residuals are relative value within the
  curve, not an outright level view (ING, Deconstructing the EUR yield curve, Jan 2020).
- Weak models inflate trust: print model R2 and residual sd next to z. Fair-value z with R2 falling (rolling 120d R2 from
  ~100% to ~60%) is a reason not to fade (JPM, Global Fixed Income Markets Weekly, Aug 2026).
- Calibrate the model to a vol-consistent regime before z-scoring: part of any wide spread is justified by higher vol
  (Citi, Convexity Meets Steepeners, Apr 2018).
- Residuals <= 0.5 sd (or ~1bp for PCA residuals) are tilts, not signals (BofA, A new UST macro framework, Oct 2024).
- Check *which leg moved* before reading a spread z (Citi, European Rates Morning Call, Aug 2026).

### 5. Ratios, composites and the common-factor trap
- For q = sigma_BE / sigma_imp the z(q) was about -2.3 on all 16 pairs on the same day because sigma_imp moved and is
  shared by every q (internal backtest spec, Oct 2026). A ratio z measures the common factor, not cross-sectional RV.
  Fix: (a) require both legs: `D = min(-z(A), z(B))` for the +1 side (and mirror); (b) z-score a spread (A - B)
  instead of the ratio; (c) cross-sectionally demean before ranking.
- Ratios with a denominator near zero explode (basis/spread 1206%, -424%): floor or drop small denominators before
  ranking (JPM, HG CDS Bond Basis Report, Oct 2025).
- Composite = simple average of component z-scores with signs aligned so higher = same meaning (invert depth, HFT share
  in a liquidity index) (JPM, Are we there yet?, Apr 2020). Never add quantities with different units.
- A **max** of k z-scores exceeds 2 far more often than one z (42% of days for a six-input vol switch): set the
  threshold for the max, not per input (Willer and Saunders, 2026).
- Dislocation index of a curve: `DI_t = MA10( sqrt(mean_i z_i,t^2) )` over tenors i, comparable across markets
  (BofA, A simple framework for swap spread RV, Jun 2016). High DI = whole curve dislocated; trade the cheapest vs richest.

### 6. Percentiles and robust variants
- **Percentile** `pct_t = share of window values <= x_t`. Rolling only. Bounded, no sd assumption: use for skewed
  series and to report "99th pct" next to z. Percentile scores are NOT comparable across markets (JPM, Aug 2026).
- Bounded score: `score = 10 x (pct - 0.5)` maps to -5..+5; position rule `4 x (pct - 0.5)`, with pct the 10-year percentile of carry-to-risk, gives +2 at a 10-year
  high, -2 at a 10-year low (JPM, Simple rules to trade duration, Oct 2012).
- **Robust z** `(x - median) / (1.4826 x MAD)` for outlier-prone series (turn/roll spikes, fat tails). Median
  (breakdown point ~0.5 vs 1/T for the mean; Palomar, 2025) beats mean; the median is "the most appropriate statistic" for seasonal tests (swapsball.net, 2017).
  NaN when MAD = 0; fall back to IQR/1.349.
- **Winsorise** the series at +/-2.5 sd before building bands; or clip the *z* at +/-4 (single screen) / +/-2
  (cross-sectional multi-factor) (Rhodes, USD 5s30s Swap Spread Flattener, Oct 2025; JPM, FX Markets Weekly, Aug 2026).
- Fat tails: under normality a 2 sd daily move occurs ~1 in 22 days, 3 sd ~1 in 370; count actual frequency
  (Barclays, Global Rates Weekly, Oct 2026). Distribution-free ceiling (Chebyshev): P(|z|>=2) <= 25%, P(>=3) <= 11%,
  P(>=4) <= 6% (Hajek, ECE 313 notes, 2025). A window-based z is really a t-statistic (dof = L-1) because sd is estimated (Huggins and Schaller, 2024).
- Level-dependent variance (vol rises with the level) cannot be fixed by one global sd: bucket the level, average the
  next change and its sd per bucket (Stanton diagnostic; Huggins and Schaller, 2024) or z-score changes instead.
- Percentile-extreme recipe: detrend (remove drift/carry), enter at the 90-95th / 5-10th percentile of a few years of
  history, cover at the mean or half-way, add a momentum filter for range breaks (QF Stack Exchange, Mean reverting
  strategies, 2011; partial source, low weight).
- Do not stack transforms blindly: rank/winsorise/neutralise change what a score means; apply neutralise first, then
  scale, then trim (Grinold and Kahn, Active Portfolio Management, 1999, Ch14).

### 7. Is the z tradable? (gate before it becomes a candidate)
A z with no reversion speed says almost nothing: if the series is i.i.d. tomorrow's expectation is the mean whatever z
is; with a 200-day half-life tomorrow's expectation is about today's level (Huggins and Schaller, 2024).
`E[z_{t+h}] = z_t x 2^(-h/HL)`. Required checks:
1. **Half-life** (OU/AR(1)) <= ~90 days (default gate) and much shorter than the holding horizon; skill [`quant-mean-reversion-ou`](../quant-mean-reversion-ou/SKILL.md). PCA-weighted 3s5s10s fly: z = -2.15, half-life 11 business days, ~+5bp expected from reversion before carry (bquanttrading, Principal Component Analysis Part II, 2015; illustrative).
2. **Stationarity / crossing frequency**: ADF or KPSS, and number of mean crossings in 3m. "Not all spreads mean revert."
3. **Persistence**: share of days the sign has held. 75-85% of days with the same sign = structural carry or term
   premium, not RV; 15-36% = transient (internal backtest spec, Oct 2026).
4. **Months-to-breakeven** = mispricing / monthly carry. 14bp too flat against -15.5bp/3m roll (about 5.2bp/month)
   breaks even only if it closes within ~2.7 months (ING quotes 2.6; Deconstructing the EUR yield curve, Jan 2020).
5. **Absolute gate**: relative z and absolute edge disagree; require side x edge > 0, because z>1 days almost never had
   positive absolute edge on long-end pairs (internal backtest spec, Oct 2026). Check value-to-rates and
   implied-vs-realised too (Citi, Fair value vs seasonality, May 2017).
6. **Why is it cheap?** Supply, ALM/pension receiving, ELB risk: "cheap for a reason" (Citi, Fixing the plumbing,
   Sep 2019). A large residual is not a timing signal (Citi, European Rates Weekly, Oct 2026).
7. **Liquidity/cost**: edge must exceed 2x bid/offer; wide long-end bid/offer vetoed a top-ranked screen hit (Citi,
   Liquidity, vega, and convexity, Mar 2020).

### 8. Thresholds and exits
| |z| (primary window) | Action |
|---|---|
| < 1 | nothing |
| 1.5 | watch list (more, smaller trades if used as entry) |
| 2 | flag: run the step-7 gate. Standard colour cut in sell-side screens (GS, Treasury RV Report, Sep 2026) |
| 2.5 | fewer, higher-conviction entries |
| >= 3 | **verify data and regime first** (roll artefact, stale leg, break); a 1,000-day extreme is an alert, not an entry (Willer and Saunders, 2026) |
| >= 4 | treat as a regime signal: months with a max vol z > 4 had a vol-adjusted FX carry IR of -2.02 vs 0.89 unfiltered (Willer and Saunders, 2026) |

- Entry at |z| >= 2 then exit at the mean (or +/-0.5) is the common default (Brenndoerfer, Mean Reversion and Statistical Arbitrage, 2025); derived (OU-optimal) bands are asymmetric and
  depend on costs, speed and stop, so ad hoc +/-1 or +/-2 bands ignore them (Leung and Li, 2016). Cost-aware rule:
  enter at |dev| = Delta only if 2 x Delta > round-trip cost eta (Tsay, 2010).
- Linear sizing: `position = -clip(z / s0, -1, 1)` with s0 ~ 2-3 scales in gradually; thresholded is all-in/all-out
  (Palomar, 2025). Do not optimise s0 on the same data (hyper-parameter); smooth and validate out of sample.
- Exit mean-reversion trades on **target or time (2-3x half-life)**, not on a z-stop; use a bp loss limit from
  [`port-position-sizing-and-risk-budget`](../port-position-sizing-and-risk-budget/SKILL.md). Fixed-bp thresholds (buy
  5s when 2s5s10s fly > +5bp) worked Jun 1999-Mar 2001 (~5bp/turn) then lost ~15bp in five months as the fly trended
  to +20bp (Tuckman, Macro-Awareness in RV Trading, Oct 2003).
- Scale down when the valuation edge shrinks even if direction is unchanged (3m10y vol 66 -> ~59 normals, position
  halved) (Citi, Gamma and Vega RV, Jan 2019).

### 9. Cross-sectional ranking
1. Build a comparable universe (same convention, sign, units, vol class). Duration-matched or vol-matched pairs hedge
   better (JPM, Rule-based Fixed Income Monthly, Nov 2012).
2. Per series, compute z for each lookback (step 3) and the raw level; flag the top 3 per metric ("illustrative, not
   recommendations", Citi, Taking profits on 15y5y/20y10y flatteners, Dec 2019).
3. Cross-sectional standardise `x_std = (x - mean_xs) / std_xs`, trim at +/-2, then **neutralise before scaling**
   (Grinold and Kahn, 1999). Demean cross-sectionally before pooling regressions (JPM, Nov 2012).
4. Do not multiply by vol if signal dispersion already scales with vol (Grinold and Kahn, Ch11). Rank on carry/vol
   only if you also size by vol (IR 0.89 ranked-and-sized vs 0.66 ranked, equal-sized) (Willer and Saunders, 2026).
5. Two-axis screens beat one metric: carry or BE/RV (y) vs level z (x); best-carry curves usually have the worst entry;
   pick from the frontier, break ties on 3y z (Citi, Forward steepener and vol divergence, Jun 2023).
6. Directionality filter: `Carry/R = Sharpe / (1 + |R|)`, R = Spearman correlation of 3-day changes with the 10y
   swap rate (3m). USD 10y5y/15y5y/20y5y Sharpe 1.20, R 0.26 gives 0.95; outright forwards R ~0.85-1.0 show Carry/R near 0 (GS, Global
   Rates Best Trade Report, Sep 2026). Also read correlations with the belly, 2s10s, 5s30s for flies.
7. Ranking per-series statistics (mean-reversion level, beta) from short or noisy histories: shrink each toward the
   cross-sectional mean, more for noisier series (empirical Bayes, Murphy, Machine Learning, 2012).
8. A permanent extreme market biases a ranking (JPY lowest real yield: beta 0.4 -> 0.0 ex-Japan); drop or neutralise it
   (JPM, Nov 2012). Universes of different size (SEK, NOK shorter) give less comparable scores.
9. Hand the ranked table to [`rv-composite-scoring`](../rv-composite-scoring/SKILL.md) to combine with carry/vol, PCA
   mispricing and half-life; z-scores rank within a screen date, not across dates or screens.

### 10. Evaluate and de-bias the screen
- **IC**: Spearman correlation of the signal with the *next-period* change (more robust than optimiser backtests;
  Citi, Quantitative Framework for Regime Investing, Oct 2021). IC 0.05 good, 0.10 great; IC > 0.20 = suspect leakage
  (Grinold and Kahn, 1999). Hit rate = (IC + 1)/2 for a binary (sign) signal; for a continuous signal it is smaller, about 0.5 + arcsin(IC)/pi.
- **Percentile-bucket forward table**: bucket the causal signal (deciles/terciles/5-tiles), tabulate mean, median and
  % positive of the next h-day change, less the overall average. Edge sits in the tails; middle buckets are non-monotonic
  (worked example F). Overlapping forward windows need HAC errors
  ([`quant-time-series-econometrics`](../quant-time-series-econometrics/SKILL.md)).
- **Conditional vs base rate**: always show the unconditional hit rate beside the conditional one (SPX January up
  then year up 80% vs 67% unconditional = +13pp lift, not 80%) (BofA, Technicals Explained, Jan 2025).
- **Multiple testing**: scanning M structures flags ~alpha x M by chance (alpha = 5%: 1 in 20); FWER = 1 - (1-alpha)^M
  (0.994 at alpha = 5%, M = 100). Use Holm (few tests) or Benjamini-Hochberg (large screens); permute dates for the null. 20 tries give a 64%
  chance (1 - 0.95^20) of a t >= 2 fluke (James et al., ISLP; Grinold and Kahn, 1999). Screening on all data then cross-validating
  is the wrong-CV error (Hastie et al., ESL, 2009). Hand off to
  [`bt-validation-and-overfitting`](../bt-validation-and-overfitting/SKILL.md).
- **Controls**: inject look-ahead (Sharpe must jump), permute dates (Sharpe ~0), invert the signal (must lose), lag the
  signal 1-2 days (a rule that "completely breaks" with one-day lag is suspect) (internal backtest spec, Oct 2026;
  Willer and Saunders, 2026). Choose the parameter plateau (median over +/-1 grid step), not the peak; <= 6 tuned
  parameters; log every trial.
- Sample size: a +/-0.1 band on a hit rate at 96% confidence needs n >= 625 (Hajek, ECE 313 notes, 2025); seasonality
  or event tables on 8-20 observations are soft priors only.

## Worked examples

**A. Lookback disagreement (USD 15y5y/20y10y convexity flattener, 26 Mar 2020).** Curve -5.21bp; z = 4.21 (1y),
3.58 (3y), 1.02 (since 2000); 1y carry +0.11bp, BE 0. Read: a 4 sigma move on 1y but only 1.0 sigma against 20 years,
so the *recent* dislocation is large while the *level* is ordinary. The trade was not initiated: poor liquidity and wide
bid/offer (Citi, Liquidity, vega, and convexity, Mar 2020). Contrast the Dec 2019 close for the same curve:
-12.54bp, z = -0.91 (1y), 0.70 (3y), 0.64 (since 2000), BE/RV 0.80 (Citi, Taking profits on 15y5y/20y10y flatteners,
Dec 2019). Similar structure in GBP 15y10y/25y10y, 17 Jan 2020: since-2000 z 1.84, 3y 1.15, 1y -0.01, carry +0.52bp, BE 0,
"effectively free convexity" (Citi, In search of cheap vol, Jan 2020).

**B. Why subtract the mean residual (global 10y fair-value table, 4 Aug 2025).** z = (resid - avg)/SD.
Ireland: resid +38.8bp, avg +44.4, SD 74.8 -> z = (38.8-44.4)/74.8 = -0.07 (printed -0.1): "cheap" in raw bp,
normal in z. Japan: (78.1-0.8)/23.4 = +3.3, the cheapest. US: (-21.7-0.3)/31.6 = -0.7; Switzerland -1.8 richest (BofA,
Monthly rates models, Aug 2025). In JPM's 1Yx1Y screen (May 2024) all nine G10 markets were above +2: USD +186bp z 2.80,
JPY +53bp z 3.82, AUD +194bp z 3.15, NZD z 2.73. Ranking by bp and by z disagree (JPY smallest in bp, largest in z; its
model R2 is 0.51 vs 0.81-0.89 elsewhere), and when every market's z moves together the signal is a common factor, not market-specific
RV (inference) (JPM, Talk is Cheap, May 2024).

**C. A big gap with a small z (US Treasury, 25 Sep 2026).** Long P-STRIPS (2054-56) sit 7-11bp rich to the fitted curve
but z is only -0.5 to -1.3, consistent with a long history of trading rich; the TY CTD at -0.8bp fitted has z -2.2 (flagged), the US CTD
at +2.1bp has z +2.9. Flags at |z| > 2 on the *fitted* spread; also check the direct tradable spread (2.7 sd
theoretical vs 1.8 sd tradable in a RiskVal example) (GS, Treasury RV Report, Sep 2026).

**D. Common-factor ratio.** q = sigma_BE/sigma_imp: z(q) ~ -2.3 on all 16 pairs on 17 Oct 2026 because sigma_imp (~91
vs realised ~61 on long forwards) moved, so the score could not discriminate between pairs. Rebuild with `D = min(-z(sigma_BE), z(sigma_imp))`
and the absolute gate side x E > 0 (internal backtest spec, Oct 2026).

**E. Mean and sd from the sell-side screen check.** Astor Ridge, EUR 10y5y-15y5y: last 0.4275, mean 0.0542, sd 0.0697 ->
(0.4275-0.0542)/0.0697 = 5.36 sd, 99.65th percentile (Dec 2019-Mar 2022); caveat: daily vol of the spread "sky rocketed",
so the denominator was stale (Astor Ridge, Trade Radar, Mar 2022). Reproduce any quoted z this way before relying on it.

**F. Percentile-bucket table (next-1m change in 10y by bucket of 3m change in 3m10y 25bp risk reversal, 2006-2016).**
< 25th: avg -11.5bp, median -5.0bp, 36% up (10y yield rose); 25-50: -2.1/-1.1/48%; 50-75: +0.2/-4.2/45%; > 75th: +8.8/+11.1/69%
(Citi, Flatter skew warning, Jan 2017). Low skew change precedes a 10y rally. Mean and median disagree in the middle bucket; only the tails carry signal.

**G. Holm vs Bonferroni vs BH.** Five tests, p = 0.006, 0.012, 0.601, 0.756, 0.918, alpha 0.05: Bonferroni threshold
0.01 rejects 1; Holm (0.006 < 0.01, 0.012 < 0.0125, 0.601 > 0.0167) rejects 2; BH rejects 2 (James et al., ISLP).
Implemented and self-tested in `holm`, `bh` of `scripts/zscore.py`.

**H. When fading extremes loses.** 3Mx10Y vol, since 2000: "fade 1y-z extremes" (buy z < -1.5, sell z > 1.5) IR -0.3
(-37bp/yr); vol momentum IR 1.90, carry 1.68, combined 2.45 (JPM, Update on systematic rule based trading strategies,
Feb 2017). Valuation z on equity yield gap vs bonds: z < -2 active IR -0.01, z > 2 IR 0.24, "a risk overlay, not a timing
signal" (Willer and Saunders, 2026, Ch15). Use z as a filter on top of carry/momentum/regime, not alone.

More tables (skew/supply/2s10s percentile buckets, CFTC positioning z, swap-fly tables, forward-vol frontier,
FORTE/OCTAVE rank scorecards, auction RV colour buckets): [references/worked-tables.md](references/worked-tables.md).
Window conventions by source, sign conventions, per-market notes: [references/conventions-and-markets.md](references/conventions-and-markets.md).

## Signals & interpretation
- Quote **at least three windows** (e.g. 63, 252, 756) plus percentile and raw bp. Verdict language:
  - same sign, all |z| >= 1: "agree": candidate.
  - short |z| >= 2, long |z| < 1: recent dislocation in a normal level: candidate for a tactical trade; confirm
    liquidity and why it moved; expect larger drawdown risk.
  - long |z| >= 2, short |z| < 1: it has been extreme for a long time and is stabilising; check structural story.
  - signs differ: no signal; the series is mid-range of one regime and the other.
  - script label `window_view`: `agree` = all finite |z| >= 1 same sign; `disagree` = big z of opposite sign, or
    shortest |z| >= 2 with longest |z| < 1 (read as above); otherwise `mixed`.
- z is "high vs history". Map to rich/cheap by convention: spread/yield high = cheap for the receiver/long-bond;
  Citi fly tables positive = belly cheap; GS entry z is payer-perspective (positive z attractive to a *receiver*);
  Nordea receiver-perspective; PCA mispricing can be unsigned (par - fair value). Normalise to one convention before
  combining (references/conventions-and-markets.md).
- Pair a z with its mean-reversion evidence: half-life, crossing frequency, persistence share, months-to-breakeven.
- Persistent extremes are usually structural; transient ones are RV. Positioning z: bonds show follow-through at
  extremes (not mean reversion), equities mean-revert (Willer and Saunders, 2026).
- A strong z with price already moving against you with R ~ 1 to the 10y is a duration trade in disguise (JPY
  receivers z ~2.9 dominated a carry-plus-entry screen while being adverse-trend duration) (GS, Sep 2026).

## Pitfalls
- Full-sample or centred windows (look-ahead). `pandas rolling(center=True)`, `qcut` on the whole sample, a std
  from the future. The script's self-test changes future data and requires an identical z at t.
- Forward-filling stale quotes: z of a frozen series is 0/NaN, then a spike. Report `stale_days`.
- Rolling-instrument artefacts: benchmark switches and futures roll days create fake slope/fly jumps (OBL177 to OBL178;
  drop roll-window days). Screen constant-maturity/fitted series. Swap-rate history carries structural breaks
  (LIBOR to SOFR): long-history z on swap rates is imprecise; prefer fitted government par curves for since-2000 z
  (Huggins and Schaller, 2024; During, 2021).
- Regime change makes the denominator stale: when daily vol doubled (1.2 to > 2bp) the z denominators were stale
  (Astor Ridge, Mar 2022); low-vol regimes end violently, calm-window z understates tail risk (ML RateLab, Oct 2008).
- Expanding windows adapt slowly; rolling windows move the target you revert to (a backtest "since 2023" with a 100%
  hit rate is a small sample) (BofA, Jun 2016; Rhodes, Oct 2025).
- Reading z of a leg that is itself driven by a global/term-premium factor with decaying R2.
- Model bias: record a model's bias factor next to every model-derived quantity before z-scoring (5% bias ~4.5 vol,
  as large as the edge on fairly priced pairs) (internal backtest spec, Oct 2026).
- Pooled IC high only because names have different mean returns; check per-name time-series IC (same spec).
- Screens are backward-looking and "illustrative": a top-3 flag is not a recommendation; liquidity can veto.
- Mixed sign conventions, units (bp vs %), snaps, or normal vs lognormal vol in one score. Normal vs lognormal can flip
  the sign of a z (CS blended vol index cheap on normal, +2.02 sd rich on lognormal) (Credit Suisse, Wall Street Babylon,
  Nov 2011 - Bassman).
- Treating NaN as 0 (0 is a valid value); cross-sectional demeaning then invents positions.
- Reporting only the best of many screens; counting the number of screens and parameters tried.

## Output
1. **Screen table** (one row per series, latest date): `series, last (bp), z_63, z_252, z_756, z_long (if available),
   robust z, EWMA z, percentile, raw 5d move + move score, half-life (from quant-mean-reversion-ou), stale_days, window_view (agree/mixed/disagree),
   flag, rank_z, rank_abs`. Mark the top 3 per metric as "illustrative". Run it with `scripts/zscore.py`.
2. **Gate checklist** for each flagged name (step 7): half-life, persistence, months-to-breakeven, absolute edge, why
   cheap, bid/offer.
3. **`signals` rows** (canonical table): `date, snap, strategy_id, package_id, value (bp), unit, zscore (primary window), horizon_days`.
   State the primary window, inclusive/exclusive convention and sign convention in `model_version`/notes.
4. Hand-off: ranked table to [`rv-composite-scoring`](../rv-composite-scoring/SKILL.md);
   shortlisted names to [`rv-trade-idea-writeup`](../rv-trade-idea-writeup/SKILL.md) quoting z, window, percentile and
   half-life; the full set of scans (count of tests) to [`bt-validation-and-overfitting`](../bt-validation-and-overfitting/SKILL.md).

## Scripts
- [`scripts/zscore.py`](scripts/zscore.py): `rolling_z` (inclusive/exclusive, std floor, clip), `ewma_z`, `robust_z`
  (median/MAD), `rolling_pctile`, `move_score`, `cs_zscore` (trimmed cross-sectional), `screen` (multi-lookback table
  with ranks and window agreement), `bucket_table` + `fwd_change` (percentile-bucket forward study), `holm`, `bh`,
  `z_to_p`. `python scripts/zscore.py --input panel.csv --lookbacks 63,252,756` (wide CSV/Parquet with a `date` column, or
  long with `--id-col/--value-col`). `--selftest` checks hand-computed z, the (L-1)/sqrt(L) cap, MAD z, percentiles,
  causality under future shocks, iid N(0,1) calibration, Holm/BH on a published example and the bucket table; exits
  non-zero on failure.

## Related skills
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life, ADF/KPSS, optimal entry/exit bands (step 7-8).
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC/IR, decay, turning a z into a forecast (alpha = vol x IC x score).
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): combining z, carry/vol, PCA mispricing and half-life into one rank.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md) and [curve-butterflies](../curve-butterflies/SKILL.md): PCA residuals and fly weightings that feed the screen.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro fair values whose residual z is screened here.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): rolling betas used to build residual series.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): up-ratio and calendar tables (conditional vs base rate).
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): walk-forward, multiple testing, deflated Sharpe.
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): HAC t-stats for overlapping forward windows.
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md) and [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): stale data, roll stitching, canonical tables.
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): rule-based signals (carry, momentum, value) that use these z-scores.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md) and [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): forward-curve and fitted-curve screens that feed the z tables.
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): the end-to-end workflow that calls this screen.
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): shrinkage, priors and Bayesian updating.
- [quant-cointegration](../quant-cointegration/SKILL.md): cointegration tests and level hedge ratios.
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): covariance and correlation estimation.
- [quant-regime-detection](../quant-regime-detection/SKILL.md): statistical regimes and structural breaks.

## References
- Citi Research - Taking profits on delta-hedged 15y5y/20y10y flatteners (Bikbov, 5 Dec 2019): multi-lookback z, BE/RV, top-3 flags.
- Citi Research - Liquidity, vega, and convexity (Bikbov, Williams, 30 Mar 2020): lookback disagreement (4.21 vs 1.02), liquidity veto.
- Citi Research - Forward steepener and vol divergence (Chang, Williams, Appeddu, 12 Jun 2023): carry vs entry-level frontier, 3y tie-break.
- Citi Research - In search of cheap vol (Bikbov, Williams, 17 Jan 2020): cross-market BE/RV, forward-vol frontier, regime-consistent fits.
- Internal research spec - Forward Curve vs Straddle Systematic Backtest Spec v0.4 (23 Oct 2026) and its implementation prompt: causal z, common-factor ratio trap, gates, persistence, IC/quintile tests, controls.
- BofA Global Research - Monthly rates models, August 2025 (Braizinha, Craig, 4 Aug 2025): residual z = (resid - avg)/SD, global 10y table.
- J.P. Morgan - Talk is Cheap: Valuing DM Rates Markets with Central Bank Speak (Jarman, Bassi, 30 May 2024): residual z heatmap, 1Yx1Y cheapness across G10.
- Huggins and Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): z-score critique (half-life, t vs z), L1 fits, structural breaks.
- Goldman Sachs FICC - Global Rates Best Trade Report (desk material, 30 Sep 2026): entry z, Carry/R, regression-plane composite, G10 numbers.
- Goldman Sachs FICC - Market Movers (30 Sep 2026): normalised-move score, short-window inflation.
- Goldman Sachs FICC - US Treasury Relative Value Report (25 Sep 2026): 3m z with +/-2 flag, level-vs-z examples.
- BofA Global Research - UST RV Primer: A hitchhiker's guide to RV on the UST curve (Zhang, Braizinha, Axel, 2 May 2022): 3m z, changes vs levels.
- BofA Global Research - Understanding the yield curve dynamic (Braizinha, 23 Jul 2025): PCA residual z across 1m/3m/6m/12m windows, fly z.
- BofA Merrill Lynch - A simple framework for swap spread relative value (Axel, Satko, Cross, 2 Jun 2016): residual z, RMS dislocation indicator.
- BofA Merrill Lynch - Many EGBs, one simple value tool (Satko, 21 Mar 2018): cross-sectional dislocation z, cheapest vs richest ranking.
- Willer and Saunders - Trading Global Macro Markets (Wiley, 2026): rolling percentiles, max-z switch, CFTC z, decile rules, lag tests.
- Grinold and Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): score to alpha, IC tiers, neutralise-scale-trim, data-mining.
- Citi Research - Flatter skew is a warning signal for duration shorts (Bikbov, 12 Jan 2017): percentile-bucket forward table.
- Citi Research - What to expect when you're expecting a turn (Mathai et al., 20 Apr 2018): decile/tercile conditional returns.
- J.P. Morgan - Update on systematic rule based trading strategies (Gupta, Inkinen, Vijay, 6 Feb 2017): vol z-fade lost money, IRs.
- J.P. Morgan - Simple rules to trade duration (Mac Gorain, 2 Oct 2012) and Rule-based Fixed Income Monthly (2 Nov 2012): percentile position rule, cross-sectional demeaning, Japan bias.
- Lehman Brothers - Macro-Awareness in Relative Value Trading (Tuckman, Oct 2003): fixed threshold failing out of sample.
- ING Global Markets - Deconstructing the EUR yield curve (Bouvet, Schroeder, Garvey, 15 Jan 2020): percentile bands, months-to-breakeven.
- Leung and Li - Optimal Mean Reversion Trading (World Scientific, 2016): OU-optimal asymmetric bands, stop shapes entry.
- Palomar - Portfolio Optimization: Theory and Application (Cambridge UP, 2025): causal rolling z, linear vs thresholded positions.
- bquanttrading - Principal Component Analysis Part II (blog, 2015): PCA fly z with OU half-life.
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): rank/winsorise/neutralise/decay, NaN hygiene, overfitting facts.
- Hastie, Tibshirani, Friedman - The Elements of Statistical Learning (2nd ed., 2009) and James et al. - Introduction to Statistical Learning with Python (external): wrong-CV error, Holm, Benjamini-Hochberg, permutation p-values.
- Murphy - Machine Learning: A Probabilistic Perspective (MIT Press, 2012): empirical-Bayes shrinkage of per-group statistics.
- Further documents cited inline (Citi, BofA, J.P. Morgan, Barclays, Nordea, GS, Hajek, Tsay, Hasbrouck, During and others) are listed with dates in [references/conventions-and-markets.md](references/conventions-and-markets.md).
