---
name: quant-cointegration
description: Tests whether a combination of rates levels (curve spread, fly, cross-market spread, swap spread or ASW, bills vs OIS, futures or CCP basis) is cointegrated, estimates its weights and turns them into a residual in bp plus DV01 hedge weights. Covers integration-order checks, known-vector ADF for fixed 1:-1 spreads and -1:2:-1 flies, Engle-Granger with MacKinnon critical values in both orderings, DOLS inference on the hedge ratio, Johansen trace and max-eigenvalue rank tests with a restricted constant, VECM loadings (which leg adjusts), LR tests of hypothesised weights, threshold cointegration inside cost bands and sparse mean-reverting baskets. Use when asked whether 2s10s, 5s30s, a 2s5s10s fly, UST-Bund, BTP-Bund, SOFR swap spreads, bills-OIS, a futures calendar spread or a cross-currency spread is cointegrated, stationary or mean-reverting in levels, or for level hedge ratios, error-correction models, spurious regressions, unit roots, ADF, Engle-Granger, Johansen, pairs trading or stat-arb on rates.
---

# Cointegration for rates RV

Two yield series that each wander like random walks (integrated of order 1, I(1)) are cointegrated when a
fixed linear combination of their levels is stationary (I(0)). That combination is the RV spread, and its
weights are hedge ratios in yield space, i.e. DV01 ratios. This skill decides whether a level relationship is
real enough to fade, estimates the weights, and builds the residual that
[quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md) then times. It pays when an economic force
(arbitrage, rate expectations, a common curve factor) pulls the levels back and the residual swings by several
round-trip costs within the holding horizon. It fails when the vector drifts with the regime, which is the norm
rather than the exception.

## When to use
- "Is 2s5s10s (or 3s4s5s, 5s30s) mean-reverting in levels, or does it trend with the level of rates?"
- "50/50 fly or regression-weighted fly: which weights make the residual stationary? Is -1:2:-1 rejected?"
- Pairs and baskets: UST-Bund, BTP-Bund, OAT-Bund, ACGB-UST, swap spread vs bond spread, bills vs OIS,
  3m vs 6m bills, futures calendar spreads, CCP basis, ASW vs swap spread.
- A level regression has a high R² and someone wants to fade its residual. Check that it is not spurious.
- PCA was run on changes and the rich/cheap call must be made in levels (cumulated factors plus a residual test).
- Deciding which leg does the adjusting (VECM loadings), and whether adjustment only happens outside a cost band.

Not this skill: entry and exit timing on a validated spread ([quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md)),
time-varying or Kalman hedge ratios ([quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md)),
cross-sectional z-score ranking ([quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap, OIS or constant-maturity govt yields by tenor | `curve_par` | daily, one snap, ≥ 2y (≥ 500 obs); 3-5y preferred | `par_rate_pct` × 100 = bp |
| Specific bond yields (on/off-the-run, cross-market) | `bond_quotes` (`ytm_pct`), `bond_static` | daily, ≥ 2y | build roll-adjusted or constant-maturity series first |
| Swap spreads, ASW | `swap_spreads` (`value_bp`, `sign_convention`) | daily | align sign conventions before combining |
| STIR futures | `stir_quotes` (`rate_pct`, not `price_px`) | daily settle | price = 100 − rate flips the sign of the weight |
| Bond futures | `fut_quotes`, `fut_basket` | daily settle | convert to CTD yield or DV01-scaled moves; never mix price and yield legs |
| Tenor or cross-currency basis | `basis_swaps` (`spread_bp`) | daily | pivot to a wide bp CSV for the script |
| CCP basis (same swap at two clearing houses) | `ccp_basis` (`basis_bp`, LCH − CME default) | daily | pivot to a wide bp CSV for the script |
| FX forwards (FX-hedged cross-market yields) | `fx_rates` | daily | only when comparing hedged yields |
| Policy meeting dates, regime boundaries | `cb_meetings` | | to segment samples |

Schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). Clean holidays, stale marks and
roll splices first ([data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md)). If an
input is missing, ask for it or hand off to the data adapter. Never invent values.

## Conventions
- **Units.** Every level is in bp (pct × 100), so every residual is in bp.
- **Leg order and normalisation.** The first leg gets weight +1. Put the longer tenor first for curve spreads
  (2s10s: `s = y10 − γ·y2`, positive = steep) and the belly first for flies (`s = y5 − b2·y2 − b10·y10`, the
  `2·y5 − y2 − y10` shape scaled by 1/2, positive = belly cheap). Also report gross-DV01 weights
  `w = a / Σ|a_i|`.
- **Yield-space weights are DV01 ratios, not notionals.** Notional of leg i = `DV01_i / DV01_per_unit_i`, with
  `DV01_i = K·a_i` (K = leg-1 DV01) or equivalently `w_i·G` (G = gross DV01).
- **Receive the spread** = hold `DV01_i = K·a_i` (positive = receive fixed or long bond). P&L = `−K·Δs`, so you
  receive the spread when `s` sits above its equilibrium, i.e. when leg 1 is cheap against its hedge basket.
  For 2s10s that is a flattener; for a fly it is receive belly, pay wings.
- **Price-quoted legs.** Equity-style pairs work in prices or log prices (Palomar 2025, Ch.15). In rates that
  choice becomes a units question: a vector estimated on bond or futures prices gives contract ratios that drift
  as DV01s change. Test on yields or rates.
- **Swap spreads.** US is quoted swap − Treasury and EGB ASW is bond − swap. Convert to one convention first.

## Method

### 0. Name the force before testing
"If there is no force, there is no trade opportunity" (swapsball.net, Regression in finance: friend or foe?, Oct 2017).
Choose candidates from finance theory, not data mining (Tsay 2010, §8.8).

| Relationship | What ties the levels | Typical break |
|---|---|---|
| Adjacent tenors on one curve (flies, 3s4s5s) | one or two common factors (level, slope) drive all tenors | policy-cycle turns, supply shifts |
| 3m vs 6m bills, bills vs OIS | expectations hypothesis, investors switching maturity | debt-limit episodes, MMF or QT shifts |
| Same issuer, different maturities; futures calendar spreads | same credit and underlying (Chan 2009, Ch.7) | roll and delivery mechanics |
| Long rate vs expected short rates | a rational forecast is cointegrated with what it forecasts (Campbell-Shiller, via Hamilton 1994, §19.1) | term-premium regime |
| Futures vs CTD, same swap at two CCPs, xccy basis | arbitrage, but only beyond costs: a threshold relation (step 8) | balance-sheet stress |
| Cross-market govies, swap spreads, ASW | weak: macro co-movement, relative supply | policy divergence, QE/QT, redenomination |

### 1. Integration order of each leg
- ADF with a constant and no trend: `Δy_t = c + ρ*·y_{t−1} + Σ_{i=1..p} φ_i·Δy_{t−i} + e_t`. The test statistic is the
  t-stat on ρ*. Critical values 1% −3.43, 5% −2.86, 10% −2.57.
- Lags p by AIC over `0..ceil(12·(T/100)^0.25)` on a common sample. Use at least 12 lags on monthly data
  (Hamilton 1994, §19.2).
- Call a leg I(1) when the level ADF does not reject at 10% and the differenced ADF rejects at 1%. Rule of thumb:
  first-order autocorrelation above 0.9 means treat it as I(1) (Wooldridge, §11.3).
- KPSS (null = stationary) is the cross-check: I(1) when ADF fails to reject and KPSS rejects. If they conflict,
  the root is near 1 and the test has no power. Treat any conclusion as weak.
- A leg that is already I(0), such as a pinned policy rate or a capped yield, is not a cointegration problem. Model
  the spread directly as OU.
- Calendar span drives power, not sampling frequency (Shiller-Perron 1985). Default: the span covers at least 10
  times the half-life you hope to trade.

### 2. Known vector: preferred whenever the trade fixes the weights
If the structure gives `a` (1:−1 spread, −1:2:−1 fly, or weights estimated on an earlier window), form
`s_t = a'y_t` and run an ordinary ADF with a constant against the one-series critical values above. No parameter
is estimated, so no Engle-Granger penalty applies. Hamilton calls this "by far the best method" when the vector
is given (1994, §19.2). Weights estimated on window 1 and tested on window 2 count as known: this is the cleanest
out-of-sample test.

### 3. Engle-Granger: a pair, or one target against a few hedges
1. OLS in levels: `y1_t = α + γ'·y2_t + u_t`. The estimate of γ is superconsistent (it converges at rate T), but
   its OLS standard errors and t-stats are invalid, and R² tends to 1 by construction. Ignore both (Hamilton 1994, §19.2).
2. ADF on `û_t` **without** a constant, lags by AIC. Compare with Engle-Granger critical values, not DF tables:
   OLS makes residuals look stationary, so the bar is higher (Wooldridge, §18.4; Greene 2018, §21.3).

| Variables N (incl. y1) | 1% | 5% | 10% | 5%, with trend |
|---|---|---|---|---|
| 2 | −3.90 | −3.34 | −3.04 | −3.78 |
| 3 | −4.29 | −3.74 | −3.45 | −4.12 |
| 4 | −4.64 | −4.10 | −3.81 | −4.43 |

These are MacKinnon (2010) asymptotic values. Wooldridge prints the same N = 2 row: −3.90 / −3.34 / −3.04, and
−3.78 with a trend.

3. **Run both orderings.** Regressing y2 on y1 does not give 1/γ unless R² = 1: Palomar's pair gives 0.74 one
   way and 1.27 the other, not 1/0.74 = 1.35 (2025, Ch.15). If only one ordering passes, the evidence is weak.
   Use Johansen, or the economically motivated orientation.
4. **Inference on γ** (for example "is the slope 1?") uses DOLS:
   `y1_t = α + γ·y2_t + Σ_{j=−2..2} φ_j·Δy2_{t−j} + e_t` with HAC standard errors. Newey-West lag =
   `int(4·(T/100)^(2/9))` (Tsay 2010, §2.10).
5. Add a deterministic trend only when a leg visibly drifts over the window, and then use the trend column.
6. **Collinear hedges** (adjacent tenors) blow up gross weights. Ridge-regularise and watch `Σ|γ|`, or prefer a
   sparse basket (step 7). In Burgess's 49-regressor equity hedge, plain OLS gave gross weights of 404% and a 53%
   out-of-sample variance reduction; ridge λ = 0.01 gave 166% and 67%, while λ = 0.1 over-smoothed to 103% and 46%
   (Burgess 2003). An alternative weight choice is the γ that maximises the OU likelihood of
   the spread (Leung & Li 2016, Ch.2).

### 4. Johansen: three or more legs, or to remove the ordering problem
- VECM: `Δy_t = Π·y_{t−1} + Σ_{i=1..k} Γ_i·Δy_{t−i} + μ + ε_t`, with `Π = α·β'`. The rank r of Π is the number
  of cointegrating vectors (columns of β). `g = n − r` is the number of common trends (level, slope, ...).
- **Deterministic case: a restricted constant for rates.** The constant sits only inside `β'y`, so yields have no
  drift. Tsay chose this for T-bills because "there is no reason a priori to believe the existence of a drift in
  the U.S. interest rate" (2010, §8.6). Use an unrestricted constant only when levels drift within the window.
- **Lags.** `k = p − 1`, where p is the BIC order of the levels VAR. Tsay's BIC picked VAR(3), so 2 lagged
  differences. For daily data start at k = 1-2 and check the residual autocorrelation.
- **Statistics.** λ are the eigenvalues of `S11⁻¹·S10·S00⁻¹·S01`, the moment matrices of the residuals after the
  lags are partialled out.
  - `trace(r) = −T·Σ_{i=r+1..n} ln(1 − λ_i)`
  - `maxeig(r) = −T·ln(1 − λ_{r+1})`
- **Rank.** Test r = 0, 1, ... and stop at the first non-rejection. The two statistics can disagree (worked
  example 4). This skill's rule when they do: take the smaller rank and treat the extra vector as unproven.

95% critical values, restricted constant, g = n − r:

| g | trace | max-eig |
|---|---|---|
| 1 | 9.2 | 9.2 |
| 2 | 20.4 | 16.0 |
| 3 | 35.3 | 22.3 |
| 4 | 54.0 | 28.6 |
| 5 | 77.2 | 34.8 |

These are simulated, not published. They come from the bundled script's `johansen()` with zero lagged differences
under the rank-0 null (driftless random walks, T = 1000, 20,000 draws), so treat them as large-sample values. For
g = 1-2 they agree within 2.5% with the Osterwald-Lenum values printed in Tsay (9.24, 19.96 trace and 15.67
max-eig).

**Trap:** a commonly used setting is an unrestricted constant, with 95% values of 3.84 / 15.49 / 29.80 for
g = 1/2/3. Those values assume drifting levels. On driftless yields the same simulation puts the true 95% points
near 8.2 / 18.3 / 31.9, so that setting overstates the rank.

- **β.** Normalise leg 1 to 1. With r ≥ 2 individual vectors are not unique: any rotation spans the same space.
  Test economically meaningful vectors against that space rather than reading eigenvectors one by one.
- **α loadings.** With `w = y1 − γ·y2`, error correction needs α1 < 0 and/or α2 > 0, and the spread's own speed
  `α1 − γ·α2` must be negative. Tsay's BHP/VALE pair has opposite signs (−0.067, +0.026); his T-bill pair has one
  insignificant loading (2010, §8.6-8.8). The leg with the significant loading moves back to equilibrium: it is
  the follower. Trade it, and hedge with the leader
  ([quant-lead-lag](../quant-lead-lag/SKILL.md)). Treat this as a hint, not proof: Hasbrouck warns that the econometrics does not
  generally support attributing the adjustment to one market. With r ≥ 2, α and β are identified
  only up to rotation, so use impulse responses rather than individual loadings (Hasbrouck 2004, Ch.17).
- **LR test of a hypothesised vector** (rank 1):
  - `LR = T·[ln(1 − λ̃_1) − ln(1 − λ_1)] ~ χ²(n − 1)`, with 5% critical values 3.84 (n = 2) and 5.99 (n = 3).
  - λ̃_1 solves the same eigenproblem with the levels restricted to `a0'y` plus the constant.
  - This answers "is the −1:2:−1 fly the right weighting, or do I need regression weights?".
  - Hamilton's example: the PPP vector (1, −1, −1) gives LR 13.92 > 5.99 and is rejected; excluding FX gives
    0.97 < 3.84 and is accepted (1994, §20.3).
  - With rank ≥ 2, test the known vector by ADF (step 2) instead.

### 5. Build the residual and read its speed
- `s_t = a'y_t` in bp. With Johansen, include the restricted constant or demean.
- Speed from the VECM: `Δs_t ≈ (a'α)·s_{t−1}`. Or fit AR(1) `s_t = c + b·s_{t−1} + e_t`, then
  `half-life = ln 0.5 / ln b` in periods. If b ≥ 1 or b ≤ 0 there is no half-life.
- Convert to DV01 as in Conventions, then hand off for thresholds, sizing and the write-up.

### 6. Tradability: stability and cost gates
- **Rolling re-estimation.** 250-day window stepped 20 days. Report the share of windows that pass at 5% and the
  range of γ. Adjacent windows share 230 of 250 days, so the pass rate is a stability description, not an
  independent-sample probability.
- **Cost.** Residual sd at least 2× the round-trip cost, and the out-of-sample range at least 4×. Tsay's band rule
  (2010, §8.8): enter at `μ − Δ`, exit at `μ + Δ`, and require `2Δ > η`, where η is the cost of a round trip
  (profit `2Δ − η`). The variant that exits at μ needs `Δ > η` and earns `Δ − η`: more trades, shorter holds.
- **Half-life between 3 and 120 business days.** Faster than 3 is noise or bid-ask bounce. Slower than about 6
  months, carry and regime risk dominate and the tests lose power.
- **Multiple testing.** Screening 100 candidates at 5% passes about 5 by chance. Confirm each on a hold-out window
  with a known-vector ADF, or tighten to 1%
  ([bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md)).

### 7. Many tenors: sparse mean-reverting baskets
- Box-Tiao (or smallest-eigenvalue) baskets are the most mean-reverting combination, but they are dense, have tiny
  variance and often move inside the bid/offer (d'Aspremont 2008).
- Constrain the basket to 3-4 legs and impose a variance floor of at least 0.2-0.3 × the median leg variance
  (Cuturi & d'Aspremont 2015).
- Greedy forward search works: start with the best single leg, then add the leg that most increases mean
  reversion. d'Aspremont found it more reliable than the SDP relaxation on US swaps.
- **PCA-on-changes route.** Cumulate the factor scores, regress levels on the cumulated factors, then test the
  residuals for stationarity before reading them as rich/cheap (Quantitative Finance Stack Exchange Q18301, 2015).
  See [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md).

### 8. Arbitrage-bound spreads: threshold cointegration
Futures vs cash, CCP basis, invoice spreads and bills vs OIS near their limits error-correct only outside a
no-arbitrage band: "there may be no adjustment at all until the error reaches the transaction cost bounds of the
marginal trader" (Hasbrouck 2004, Ch.17). Tsay's S&P futures-cash model is significant in the outer regimes
(t = 10.47 and 9.75) and insignificant in the middle one (2010, §8.7). Linear tests lose power here. A raw
futures-cash basis also has a carry term that decays to delivery and jumps at the roll, so its mean is not constant:
test the carry-adjusted (net) basis (Hasbrouck 2004, Ch.17). Grid-search
the band, or measure the ECM speed only when `|s − μ|` exceeds it, and trade only outside the band
([fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md),
[spread-ccp-basis](../spread-ccp-basis/SKILL.md)).

## Worked examples

**1. 3m vs 6m T-bills: Johansen, loadings and DV01** (Tsay, Analysis of Financial Time Series, 2010, §8.6)
- Data: weekly, Dec 1958 to Aug 2004, 2,383 observations. The ADF on each rate is −2.34 / −2.33 (p ≈ 0.16), so
  both are I(1). BIC picks VAR(3), and the constant is restricted.
- Trace H(0) = 83.27 vs a 95% critical value of 19.96. H(1) = 5.49 vs 9.24. So rank 1.
- Vector: `w = tb3m − 1.0124·tb6m` (se 0.0086). Its mean is about −0.225% = −22.5bp.
- Loadings: −0.0949 on Δtb3m (t −4.76) and −0.0211 on Δtb6m (t −1.18). The 3m leg does the adjusting.
- *Derived here, ignoring the lagged-difference terms:* `Δw ≈ (−0.0949 + 1.0124·0.0211)·w = −0.0735·w` per
  week, so the half-life is `ln 0.5 / ln(0.9265) ≈ 9.1 weeks`.
- Trade reading: if `w` printed −10bp, it would be 12.5bp above equilibrium, meaning 3m is cheap against 6m.
  Receive the spread: long 3m bills for DV01 +K and short 6m bills for DV01 −1.0124K. P&L = `−K·Δw`, and most of
  the move should come from the 3m yield falling.

**2. Known vector beats estimation** (Wooldridge, Introductory Econometrics, §18.4)
- The 6m − 3m bill spread with weights fixed at 1:−1 gives DF t = −7.71 (AR coefficient 0.33 per quarter), so the
  rates are cointegrated.
- DOLS with 2 leads and 2 lags gives a slope of 1.038 (se 0.0081). The t-stat against 1 is 4.69: statistically
  not 1, but economically 1. Plain OLS gives 1.026, and its t-stat is not valid.
- Trade the 1:−1 spread and use the DOLS number only to check that the hedge is not grossly wrong.

**3. Spurious levels regression** (Tsay 2010, §2.9-2.10)
- Weekly 3y on 1y UST yields, 1962-2009: `r3 = 0.832 + 0.930·r1`, R² = 96.5%. The residuals are strongly
  autocorrelated, so the regression is "seriously inadequate".
- In changes the slope is about 0.79, and its OLS t of 107.9 falls to 39.9 with HAC errors.
- Use the changes beta for hedging. The levels residual is not a fair value until it passes step 3.
- In simulations of two independent random walks, the naive 5% t-test rejects β = 0 in 66.2% of samples at n = 50
  and in 84.7% at n = 250 (Wooldridge, §18.3).

**4. Tests disagree: report it, don't pick the convenient one** (Hamilton 1994, Ch.19-20)
- On the same PPP data, Engle-Granger says no cointegration: Z_t −2.02 and ADF −2.73, both against −3.80.
- Johansen says yes: trace 38.85 > 29.5 and max-eig 22.12 > 20.8.
- For a second vector, trace says yes (16.73 > 15.2) and max-eig says no (10.90 < 14.0).
- Verdict: rank 1, held with low confidence.

**5. Most mean-reverting swap basket vs bid/offer** (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008)
- On 100 days of US swap rates (1y-30y), greedy sparse search raises the OU mean-reversion coefficient λ from 35
  with 2 legs to 128 with 3 legs and 178 with 4. λ is per year: the paper equates λ = 238 with a half-life of
  about one day.
- *Derived:* λ = 128 means a half-life of `ln2/128` years: 1.4 days on a 252-day year, 2.0 on a 365-day year
  (the paper's "238 ≈ one day" matches the 365-day reading).
- In a separate 1998-2005 study (200-day windows, re-estimated every 50 days), the optimal 3-leg portfolio is a
  local fly: 3y −0.288, 4y +0.806, 5y −0.517.
- Estimated on 100 days and traded on the next 50, "even minuscule transaction costs (a bid-ask spread of 1bp) are
  sufficient to completely neutralize these market inefficiencies".
- The cost gate in step 6 is not optional.

**6. Levels vs changes in a fly** (Huggins & Schaller, Fixed Income Relative Value Analysis, 2024, Ch.4)
- BTP 1.65% Mar-32 / 2.25% Sep-36 / 5% Sep-40, Jan 2017 to Jan 2019.
- The fly correlates −0.88 with the average yield level, but its changes correlate +0.06 daily, −0.27 weekly and
  −0.57 two-weekly.
- Directionality depends on the horizon.
- *This skill's reading, not the book's:* a hedge ratio from daily changes misses the long-run link that a levels
  (cointegration) estimate captures.

## Signals & interpretation
| Gate | Pass | If it fails |
|---|---|---|
| Every leg I(1) | level ADF p > 0.10, difference ADF p < 0.01 | I(0) leg: model the spread as OU; I(2)-like: check the data |
| Residual stationarity | known-vector ADF < −2.86, EG ADF < the table value, or Johansen rank ≥ 1 on trace **and** max-eig | no level trade; at most a short-horizon changes hedge |
| Orderings and methods agree | EG both ways and Johansen same verdict | label "weak", halve the size or skip |
| Loadings | error-correcting sign, `a'α < 0`, at least one significant | no error correction: the residual is drifting, not reverting |
| Hypothesised weights | LR < χ² 5% value | use the estimated weights, or explain the economic gap |
| Rolling stability | ≥ 70% of 250d windows pass; γ within ±30% of full sample | vector unstable: shorten the window or go to a time-varying hedge |
| Speed | half-life 3-120 business days | too fast: inside costs; too slow: carry and regime risk |
| Cost | residual sd ≥ 2× round-trip, OOS range ≥ 4× | not tradable however significant |

- **Positive residual** (with leg 1 normalised to +1): leg 1 yields too much against its basket, so it is cheap.
  Receive leg 1 and pay the basket in the DV01 ratios given by `a`.
- A pass means the level gap has historically closed. It does not mean it will close inside your horizon or
  before your stop. Timing and stops belong to the OU and monitoring skills.
- Failing to reject does not prove there is no cointegration: power is low near a unit root (Greene 2018, §21.3;
  Wooldridge, §18.2). Rejecting is not evidence of tradability either.

## G10 market notes (segment samples at these breaks)
- **USD.** Never splice LIBOR swaps (panel ended 30 Jun 2023) and SOFR swaps into one level series. The standing
  repo facility, permanent since Jul 2021, changed SOFR dynamics: re-estimate SOFR relationships on post-Aug 2021
  data (Huggins & Schaller, SOFR Futures and Options, 2022). Debt-limit episodes distort bills vs OIS.
- **EUR.** The negative deposit rate (Jun 2014 to Jul 2022) compressed front-end variance. BTP-Bund and other
  sovereign spreads have no stable vector through redenomination scares. QE trends broke ASW relationships: a
  Bobl ASW model fitted on 2013-14 data worked briefly, then failed when the QE-driven ASW trend began (swapsball.net, 2017).
- **JPY.** Yield curve control (Sep 2016 to Mar 2024) capped 10y JGB yields, so capped series pass stationarity
  tests for policy reasons. Exclude or segment those years.
- **GBP.** The GBP LIBOR panel ended at end-2021. The Sep-Oct 2022 LDI episode is a break for long-end gilt and swap-spread
  relationships.
- **CHF.** Negative policy rate from Jan 2015 to Sep 2022: the same pinned-front-end problem as EUR.
- **CAD.** CDOR ceased in Jun 2024, so CORRA swap histories are short.
- **AUD, NZD.** AUD swaps move from 3m to 6m BBSW at about 4y; do not mix basis conventions inside one vector.
  ASX bond futures quote 100 − yield.
- **SEK, NOK.** Short, thin histories and wider bid/offer, so the cost gate usually binds before the statistics do.

## Pitfalls
- **Correlation is not cointegration.** Palomar's simulated pairs: return correlation 0.111 while cointegrated,
  and 0.947 while not (2025, Ch.15). Chan's KO/PEP: daily correlation 0.4849, CADF t −2.14, not cointegrated (2009, Ch.7).
- **A changes regression gives a hedge ratio, not a fair value.** "Moved more than predicted" is no reason to fade
  (swapsball.net, 2017).
- **Using DF tables on Engle-Granger residuals, or reading OLS t-stats on γ.** Both overstate significance.
- **Wrong deterministic case.** An unrestricted constant on driftless yields overstates the Johansen rank (step 4).
  A trend term you don't need costs power.
- **In-sample cointegration disappears out of sample.** Cointegrating vectors are "notoriously unstable"
  (López de Prado 2018, Ch.5), and spreads take "a steady stream of permanent shocks" (Palomar 2025, Ch.15).
  Always run the hold-out test from step 2.
- **Look-ahead in backtests.** A vector and mean estimated on the full sample and applied to earlier dates make the
  historical residual look stationary by construction. In a backtest, estimate the weights, mean and sd on data up
  to t − 1 only, and shift them one day before they set positions.
- **Differencing a cointegrated system.** A VAR in differences is misspecified; use the VECM (Hamilton 1994, §19.1).
- **Bid-ask bounce and stale marks** can make a random walk look stationary (Hasbrouck 2004). Use mids at a single
  snap and drop stale prints.
- **Roll splices.** Generic futures and on-the-run bond series jump at rolls, which can create or hide
  cointegration. Test roll-adjusted or constant-maturity series.
- **Horizon-dependent correlation** (worked example 6). Size with the horizon you will actually hold.
- **Price vs yield legs.** Cointegration in prices is not cointegration in yields. Convert first.
- **Too many legs.** Johansen with 5 or more legs on 2-3 years of data has little power, and its baskets cost more
  to trade than they revert. Prefer 2-4 legs.

## Output
One row per candidate:

`candidate, legs (ids in order), window, n_obs, method (known | EG | Johansen), det, k, leg_I1_flags, stat,
cv_5pct, rank_trace, rank_maxeig, vector (leg 1 = 1), dv01_weights (gross 1), lr_vs_hypothesis (LR, df, cv),
loadings (which leg adjusts), resid_now_bp, resid_mean_bp, resid_sd_bp, dev_sd, half_life_days,
rolling_pass_rate, gamma_range, cost_ratio (sd / round-trip), verdict, reason`

- **Verdict** is one of `tradable`, `statistical only` (passes the tests, fails cost or stability), `weak`
  (methods disagree) or `reject`.
- **Chart:** the residual with its mean and ±1/±2 sd bands, plus the rolling γ.
- **Hand-off:**
  - `tradable` rows go to [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md) for entry and exit
    levels, then [rv-composite-scoring](../rv-composite-scoring/SKILL.md) and
    [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).
  - State the regime window that was used and the break that would invalidate it.

## Scripts
- [`scripts/coint.py`](scripts/coint.py) covers the full method:
  - per-leg ADF (level and difference);
  - Engle-Granger with MacKinnon critical values, in both orderings for pairs;
  - Johansen trace and max-eig with a restricted (default) or unrestricted constant;
  - LR test of a hypothesised vector;
  - known-vector ADF;
  - DV01 weights and the AR(1) half-life.

  It reads `curve_par`, `bond_quotes`, `stir_quotes`, `swap_spreads` or a wide bp CSV, and prints ASCII JSON.
  Example:
  `python scripts/coint.py --file curve_par.parquet --snap eod_ny --series "USD-SOFR|0D|5Y,USD-SOFR|0D|2Y,USD-SOFR|0D|10Y" --test-vector=2,-1,-1`.
  - Put the leg you want at +1 first.
  - `--test-vector` weights follow the `--series` order. With the belly listed first, the −1:2:−1 fly is
    `2,-1,-1`.
  - Pass a vector that starts with `-` as `--test-vector=...`.
  - Rows with any missing leg are dropped. Fewer than 100 complete rows, or more than 5 legs, is an error;
    `short_history_lt_500` flags samples below the 500-observation default.
  - The LR result is meaningful only at rank 1 (`rank1_assumption_holds` in the JSON). At higher rank, use the
    known-vector ADF block.
- `--selftest` runs these checks and exits non-zero on any failure:
  - a simulated pair with γ = 1.5 and AR 0.9 must recover γ, reject no-cointegration and give a half-life near 6.6;
  - independent walks must not reject, and an EG residual t between the DF and EG 5% values must not reject;
  - DV01 weights must be gross-normalised, and the end-to-end `analyse()` must reproduce the known-vector ADF,
    drop NaN rows and refuse too-short or one-leg inputs;
  - a 3-tenor one-trend curve must give rank 2, its −1:2:−1 fly must test stationary and its wing spread must not;
  - an exact Johansen/ADF identity must hold;
  - the loader must scale pct to bp and filter by snap and `data_ok`;
  - when statsmodels is present, the EG statistic and the Johansen statistics (unrestricted constant) must match
    it exactly.

## Related skills
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life, OU fit and optimal entry/exit on the residual
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): changes betas, TLS, rolling and Kalman hedge ratios
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): unit-root tests, VAR, HAC, structural breaks
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): causal z-scores of the residual
- [quant-lead-lag](../quant-lead-lag/SKILL.md): leader/follower and Granger tests alongside VECM loadings
- [quant-regime-detection](../quant-regime-detection/SKILL.md): where to cut samples when the vector breaks
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): factor residuals and cumulated-factor level tests
- [curve-butterflies](../curve-butterflies/SKILL.md) and [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): the structures whose weights this skill tests
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md), [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md), [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): common pair universes
- [stir-futures-rv](../stir-futures-rv/SKILL.md) and [fut-calendar-roll](../fut-calendar-roll/SKILL.md): futures calendar spreads and roll-adjusted series
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market index transitions and quoting conventions behind the G10 notes
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): turning yield-space weights into DV01 and notionals
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md) and [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): hold-out tests and the cost gate
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): fractional differencing when features, not trades, need stationarity
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): stress the "force" and the regime before trading
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): covariance and correlation estimation.

## References
- Ruey S. Tsay - Analysis of Financial Time Series, 3rd ed. (Wiley, 2010): §8.5-8.8 cointegration, Johansen with a restricted constant, the 3m/6m T-bill VECM, threshold cointegration and the pairs band rule; §2.9-2.10 spurious 1y/3y regression and HAC
- James D. Hamilton - Time Series Analysis (Princeton University Press, 1994): Ch.19-20 known-vector tests, residual-based critical values, Johansen ML, LR tests on vectors, and the EG vs Johansen conflict example
- Jeffrey M. Wooldridge - Introductory Econometrics: A Modern Approach, 2nd ed. (c. 2002): §11.3 the ρ̂ > 0.9 differencing rule; §18.2 unit-root test power; §18.3-18.4 spurious-regression rejection rates, 6m-3m bill spread, DOLS, Engle-Granger critical values, holding-yield ECM
- Daniel P. Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025), Ch.15: correlation vs cointegration, EG ordering, VECM and multi-vector spreads, persistence caveats
- Alexandre d'Aspremont - Identifying Small Mean Reverting Portfolios (arXiv 0708.3048, 2008; Quantitative Finance, 2011): Box-Tiao and sparse baskets on US swaps, the 1bp cost result
- Marco Cuturi, Alexandre d'Aspremont - Mean-Reverting Portfolios: Tradeoffs Between Sparsity and Volatility (arXiv 1509.05954, 2015): variance floor and cardinality constraints
- Doug Huggins, Christian Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024), Ch.4: multivariate mean reversion, horizon-dependent correlation, BTP fly example
- William H. Greene - Econometric Analysis, 8th ed. (Pearson, 2018), §21.2-21.3: spurious regression, adjusted EG critical values, Johansen via canonical correlations
- A. Neil Burgess - Using Cointegration to Hedge and Trade International Equities, in Dunis, Laws & Naim (eds), Applied Quantitative Methods for Trading and Investment (Wiley, 2003): ridge-regularised cointegration hedges and gross-weight blow-up
- Joel Hasbrouck - Empirical Market Microstructure (NYU Stern teaching notes, 2004), Ch.17: VECMs for linked prices, basis-invariant impulse responses, adjustment only beyond cost bounds, bid-ask bounce
- Ernest P. Chan - Quantitative Trading (Wiley, 2009), Ch.7: CADF test, cointegration vs correlation, calendar spreads and same-issuer bonds as natural pairs
- swapsball.net - Regression in finance: friend or foe? (27 Oct 2017): levels vs changes, "no force, no trade", the Bobl ASW regime failure
- Quantitative Finance Stack Exchange - Reproducing levels when PCA has been done on changes (Q18301, Jun 2015): cumulated-factor level regression with a residual stationarity test
- Doug Huggins, Christian Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): the standing repo facility as a regime break for SOFR relationships
- Marcos López de Prado - Advances in Financial Machine Learning (Wiley, 2018), Ch.5: instability of cointegrating vectors; fractional differencing as the ML alternative
- Tim Leung, Xin Li - Optimal Mean Reversion Trading (World Scientific, 2016), Ch.2: hedge ratio chosen by maximum OU likelihood
- R.F. Engle, C.W.J. Granger - Co-integration and Error Correction: Representation, Estimation, and Testing (Econometrica, 1987) (external): the two-step method
- S. Johansen - Estimation and Hypothesis Testing of Cointegration Vectors in Gaussian Vector Autoregressive Models (Econometrica, 1991) (external): trace and max-eigenvalue tests
- J.G. MacKinnon - Critical Values for Cointegration Tests (Queen's Economics Department Working Paper 1227, 2010) (external): the EG critical values used here
- M. Osterwald-Lenum - A Note with Quantiles of the Asymptotic Distribution of the Maximum Likelihood Cointegration Rank Test Statistics (Oxford Bulletin of Economics and Statistics, 1992) (external): restricted-constant quantiles
- J.H. Stock, M.W. Watson - A Simple Estimator of Cointegrating Vectors in Higher Order Integrated Systems (Econometrica, 1993) (external): DOLS
- N.S. Balke, T.B. Fomby - Threshold Cointegration (International Economic Review, 1997) (external): error correction outside a band
- J.Y. Campbell, R.J. Shiller - Cointegration and Tests of Present Value Models (Journal of Political Economy, 1987) (external): yields cointegrated with expected short rates
- R.J. Shiller, P. Perron - Testing the Random Walk Hypothesis: Power versus Frequency of Observation (Economics Letters, 1985) (external): power depends on span, not frequency
