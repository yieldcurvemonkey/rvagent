---
name: port-scenario-and-stress-testing
description: Scenario and stress testing of a G10 rates RV book. Builds deterministic shocks (parallel grid, bull/bear steepener/flattener, pivot twists, PCA shocks in standard deviations, historical-window replays, hypothetical events via conditional core/peripheral shocks), computes P&L from key-rate DV01 and gamma ladders, scores each scenario's plausibility (Mahalanobis Z, correlation z-score, risk ruler), adds tail measures (historical VaR/ES, CoVaR, mixed-normal fat-tail stress) and reverse stress tests, and stresses funding, margin, haircut, CCP-basis and liquidity for levered basis/swap-spread/curve books. Use when asked for stress test, scenario analysis, what-if, worst case, tail risk, PCA shock, reverse stress, VaR vs stress, March 2020 / 2022 / SVB replay, "how much do we lose if curve bear-flattens 50bp", margin or haircut shock, correlation breakdown, or to size a trade against a loss limit.
---

# Portfolio scenario and stress testing

Linear DV01 limits and VaR describe a book on a normal day. A stress test asks what the book loses when the
assumptions behind the hedge ratios (parallel moves, stable correlation, orderly funding) fail. This skill turns
a risk ladder into scenario P&L, says how plausible each scenario is, finds the worst plausible shock, and
stresses the non-market channels (repo, margin, haircuts, CCP basis, liquidity) that sink levered RV.

## When to use
- "What does this book lose in a +50bp bear flattener / 2022 / March 2020 / SVB replay?"
- A trade or book is DV01-flat but you need its PCA, curvature, vol, basis or funding exposure.
- Sizing a trade against a loss limit; comparing stress loss to VaR; "is this scenario realistic?".
- Reverse stress: which plausible shock hurts most? Tail check on a short-vol-like carry book.
- Pre-trade review of leveraged structures (bond basis, swap-spread arb, on/off-the-run, curve at 10x+ leverage).

## Inputs (data-agnostic)
Definitions of every table are in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Holdings, signed DV01 per leg | `positions` | EOD, current | `dv01_ccy` > 0 = long duration (receive fixed / long bond). Needs a key-rate ladder (see [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md)); gamma and cross-gamma per bucket or full revaluation for options |
| Par swap / OIS / government curve history | `curve_par` (`curve_zero` for forwards) | daily, >= 3y (>= 5y for a risk ruler), same snap every day | rates in % -> convert to bp; use **changes**, not levels |
| Vol surface | `vol_surface` | daily | normal (bp) vol; needed for option books and the CTD scenarios |
| Futures, baskets, repo | `fut_quotes`, `fut_basket`, `repo_rates` | daily | CTD grids, implied repo, term vs overnight repo |
| CCP / swap-spread / tenor basis | `ccp_basis`, `swap_spreads`, `basis_swaps` | daily | cross-CCP and basis legs |
| Realised P&L history | `pnl` | daily | HVaR, MtM attribution (actual vs factor-implied) |
| Event dates and probabilities | `events_probs`, `macro_series` | event-dated | scenario weights, named windows |

Ask for (never invent): the book's bucket DV01/gamma ladder, funding terms (tenor of repo, haircut, who can change
it, margin model), and the currency/CCP split. If only bond/swap DV01 totals exist, say so and run parallel
scenarios only.

## Method

### 1. Conventions
- Shock = change in yield/rate in **bp**, + = sell-off. Spread shock A-B: 2s10s = 10y - 2y, so a bear flattener
  has the 2y shock larger than the 10y shock. Fly 2s5s10s = 2x5y - 2y - 10y.
- **P&L = -sum_i DV01_i * dy_i + 0.5 * sum_ij Gamma_ij * dy_i * dy_j** (DV01 ccy/bp, positive long duration;
  Gamma = d2P/dy2 in ccy/bp^2, positive long convexity). A receiver in a rally gains: dy < 0, DV01 > 0.
- Instantaneous shock vs horizon return: instantaneous shocks ignore carry, rolldown and option decay and flatter
  short-dated optionality. Use instantaneous for gap/liquidity events; use horizon return (carry + rolldown +
  shock P&L, constant-maturity yield change, end-of-horizon duration/convexity) for held trades and option books.
  Horizon approximation: h_n ~ f + (1 + f/100) * [-Dur*ds + 0.5*Cx*ds^2] with f the rolling yield in %, ds the
  constant-maturity yield change in percentage points, Dur in years, Cx = (d2P/ds2)(100/P) and end-of-horizon Dur, Cx
  (Salomon Brothers, Understanding the Yield Curve Part 6, Nov 1995).
- Bucket-delta P&L is linear. Reprice fully when |shock| >= 50bp, when the gamma term exceeds ~10% of the delta
  term (default, calibrate), or for any option/CTD/callable leg. Receiving a 100mm 5Y swap has zero net cross-gamma
  in a parallel move but changes the 2Y/10Y bucket risks in a twist (diagonal 2/8/18/32/48, off-diagonal
  -2/-6/-12/-20), which a linear ladder misses (Darbyshire, Pricing and Trading IR Derivatives 3rd ed., 2022, Ex 22.6).

### 2. Build the scenario suite (defaults; each is a function in `scripts/scenarios.py`)
| # | Scenario | Definition | Why this default |
|---|---|---|---|
| a | Parallel grid | 0, +-25, +-50, +-75, +-100, +-150bp, full reval | BlackRock grid; with a 1-SD annual parallel of 75-110bp typical (60bp in Jan 2020, 92bp in Sep 1996), +-100 ~ 1 SD and +-150 ~ 1.4-2 SD (2.5 SD in Jan 2020) |
| b | Seven curve scenarios | forwards; +-50 parallel; bull steepener (<=2y -50, 5y -25, >=10y 0); bull flattener (0,-25,-50); bear steepener (0,+25,+50); bear flattener (+50,+25,0); 3m horizon, spreads unchanged (Citi Research, Agency MBS Weekly, 21 Aug 2026) | covers level and the four reshapings with one rule |
| c | Pivot twist | anchor tenor (5y), wings +-0.5bp/unit or +-X bp, linear in between; **Delta(DV01) under the twist = curve gamma** | one number for steepener exposure and its drift (QSE, steepener 01 thread, Oct 2021). Parallel x twist matrix: -50bp with 8bp flattening = shortest -50, longest -58, linear between (RiskVal, Future CTD Scenario Analysis, 25 Apr 2024) |
| d | PCA shocks | +-1, +-2, +-3 SD of PC1, PC2, PC3, plus the three joint "worst sign" combos; loadings in bp per 1 SD | realistic shapes; reports exposure in standard units (see 3) |
| e | Historical replay | level change per tenor over a named window, held in key-rate space | tests the book against shapes that really happened; see [scenario library](references/scenario_library.md) |
| f | Hypothetical event | 2-4 core shocks, rest implied by regression (see 4) | consistent by construction |
| g | Instrument grids | CTD: shift reference bond -120..+120bp (20bp) or +-60 (10bp), others by yield beta; add +-1.5 SD twist about the CTD. STIR futures: price change = round(-df, tick) x BPV with constant convexity adjustment | basis, delivery-option and tick-rounding effects |
| h | Funding / margin / liquidity | haircut, repo spread, VM, CCP basis, correlation break, exit cost (see 6) | where levered RV actually dies |

### 3. PCA shocks
- PCA of daily yield **changes** in bp (not of PV01s; not of levels for risk). Keep the covariance **un-demeaned**
  for risk. Loadings L = eigenvector x sqrt(eigenvalue) = bp per +1 SD of that PC. Shock = L @ sd_vector.
- Window: 3y of daily changes (EWMA with a 40-day half-life or 1y when the regime has just changed). Check
  explanatory power first: need PC1 > ~95% to treat the book as one-factor; EUR swap forwards: PC1 > 80%, PC2 10%, PC3 4%
  (Credit Suisse, PCA Unleashed, 24 Oct 2012). PC1 is **not** guaranteed parallel and is regime dependent (Bund PC1
  peaked at 5Y in 2010-11; it was flat 2Y-5Y in 1993-97; Huggins & Schaller, Fixed Income RV Analysis 2nd ed., 2024).
- Report sensitivity to +-1 SD of PC1 (level), PC2 (slope), PC3 (curvature), not a fixed bp. Sign convention used
  here: PC1 sum > 0, PC2 long end minus short end > 0 (steepening), PC3 belly minus wings > 0.
- 3 PCs for the report; **6-8 PCs for tail Monte Carlo** below 1% (QSE, advanced bond risk transformations, Mar 2021).
  Beyond 3y 3 PCs explain >99%, but only 74.5% of the 1y point, so front-end books need more factors (Tuckman &
  Serrat, Fixed Income Securities 4th ed., 2022).
- Zeroing PC1 and PC2 does not make a book riskless. Residual (flylet) risk stays; keep a separate residual limit
  ([curve-pca-factor-model](../curve-pca-factor-model/SKILL.md)). Hedge ratios from PC1 only blow up where level
  loading ~ 0 (e.g. 30y10y vs 1y1y hedge ratio 7.88; Credit Suisse 2012).

### 4. Hypothetical events and conditional shocks
- Choose K core ("policy") factors (rates, equity, FX, vol; adjusted R^2 among them < 90% to avoid collinearity).
  Shock them; imply the other M-K by regression: **s_j = sum_k beta_jk * s_k**, beta from the covariance matrix
  (BlackRock's Guide to Fixed-Income Risk Management, 2023, eq 5.1-5.2). Fully revalue options.
- Scale the event by **attention multiplier**: dampen when markets already price it, amplify when attention has
  waned (BlackRock 2023). Write down escalation triggers and what is already priced.
- Choose the regime-consistent covariance (crisis shocks use a crisis covariance, not a calm one).

### 5. Plausibility score every scenario
Using horizon-matched covariance Sigma of changes (n factors):
- **SD multiple** S = |z|^2 / sqrt(z' Sigma z) (z = shock vector). One-sided probability = 1 - Phi(S).
- **Mahalanobis** MD = sqrt(z' Sigma^-1 z); **Z = MD / sqrt(n)**. Lower Z = more probable (elliptical case).
- **Correlation z-score** C = Z / V with V = sqrt(sum (z_i/sd_i)^2 / n). **C > 1 means the signs/relative sizes
  contradict the correlations** (a flipped sign usually does it). Fix the scenario or label it a deliberate
  inconsistency (BlackRock 2023, Kinlaw-Turkington decomposition).
- **Risk ruler**: Z of past events on a 5y weekly covariance before the event: US downgrade 1.8, Fed taper 2.5,
  China crash 3.1, GFC 5.2, credit crisis 5.3 (BlackRock 2023). Scale new scenarios so Z sits where you believe it
  belongs on that ruler. Soft Brexit (Feb 2016) was 1.5 on it.
- **Shape plausibility** (Golub & Tilman 2000): PC1/parallel shocks score 80-90%; typical steepener shocks 30-45%,
  i.e. historically implausible. Implausible shocks still belong in the suite; label them.
- Exceedance frequency: non-parametric F(Z*) over overlapping h-period history with each period's ex-ante Sigma_t.

### 6. Funding, margin, liquidity (levered RV)
- **Haircut shock**: extra cash = position_value x (haircut_stress - haircut_now). Size leverage so the worst
  haircut jump can be met from cash, especially if the counterparty or CCP can change terms unilaterally. Price
  hedges do not hedge margin (MF Global: IE/PT haircuts 3% -> 80% in July 2011; limit $4.75bn sized to 15%
  average haircut; Tuckman & Serrat 2022).
- **Repo**: stress overnight and term separately. 99th-percentile repo - SOFR was 10-11bp in Feb 2020, 20-50bp on
  several March days, peak 174bp on 16 Mar 2020 (Tuckman & Serrat 2022). Model financing withdrawal, not only a
  higher rate. Trade turns unprofitable when implied repo < repo cost.
- **Basis book checklist** (CFTC MRAC, Treasury Cash-Futures Basis Trade, Dec 2024): replay March 2020 and 2008; extreme
  but plausible correlation change cash/futures/funding (small correlation changes -> large margin calls at
  high leverage); CTD change under vol scenarios; actual vs factor-implied MtM; liquidity buffers and unwind plan.
  Only ~2.8% of futures go to delivery, so the trade is a rolled dynamic strategy.
- **CCP basis**: a DV01-flat book split across CCPs carries basis risk. Example: CME 5Y 01 = -$1m with the 5Y basis (CME minus LCH, Clarus
  convention; canonical `ccp_basis` defaults to LCH minus CME, so flip sign) moving +1.2bp = ~$1.2m loss (source rounds to $1m),
  $7.5m across tenors (Clarus, Hedging the CME-LCH Basis, 26 May 2015). Basis widened 0.15 -> up to
  1.9bp by tenor; cross-CCP bases can persist > 1 year ([spread-ccp-basis](../spread-ccp-basis/SKILL.md)).
- **Liquidity**: charge exit costs, not mid. Small-trade execution cost was ~10x normal in March 2020; ~two-thirds
  of 30y interdealer volume on 9 Mar 2020 filled wider than one tick while optical depth looked normal. Use fills
  vs minimum tick, not displayed depth ([bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md)).
- **Strategy vulnerability map** (FT Alphaville 14 Aug 2026, quoting Fed work): basis -> basis widening, margin,
  repo; swap-spread arb -> swap-spread widening, no mechanical convergence; on/off-the-run -> flight to quality;
  curve trades -> macro/policy surprise, lower leverage.
- **Flow overlays** for convexity events (MBS, bank ALM): hedge need = old 10y-eq - new 10y-eq, where
  10y-eq = duration x $ / 10. Example duration 7, $100bn, convexity -2: +25/+50/+100bp -> hedge need -5/-10/-20bn
  10y-eq (BofA, MBS convexity hedging primer, 18 Mar 2021). Do not over-attribute: flow was 0.5% of the UST market in
  2021 vs 10% in 2003. See [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md).

### 7. Tail measures (use next to, never instead of, the scenarios)
- **Historical VaR/ES**: with n days, VaR_a = k-th worst P&L, ES_a = mean of the k worst, k = ceil(a n). 400 days: 4th worst is
  VaR 1%, mean of 10 worst is ES 2.5%. Under normality VaR 1% (2.326 sd) ~ ES 2.5% (2.338 sd) and
  linear IRD books gain little from ES (Darbyshire 2022).
- **Vol-scaled (filtered) HVaR**: standardise by ex-ante vol, rescale by current vol (e.g. 5-day overlap, 40-day
  half-life, 252-day window). 99% backtest 2003-2019: analytic >2.9% violations, equal-weight HVaR 1.6%, filtered 1.2%,
  filtered with gamma scaling 1.06% (BlackRock 2023). Violations still cluster.
- **CoVaR**: c = sqrt(S' Q S), S = par risk strip (ccy per bp), Q = covariance of bp changes; VaR_5% = 1.645c,
  VaR_1% = 2.326c. Linear: ignores gamma, use short horizons. Euler allocation S_i (QS)_i / c sums to c; a negative
  contribution diversifies.
- **Mixed-normal tail on PC risk** (Musaelian, Nagarajan, Villani, SSRN 2777026, 2016): with PC delta J and Hessian H,
  E[dPi^2] = |J|^2 + 0.5|H|_F^2 + 0.25 Tr(H)^2 for iid N(0,1) PCs; with all PCs jumping together to N(0,theta^2) (SD x theta) with
  prob p: linear term x (1 + p(theta^2-1)), gamma term x (1 + p(theta^4-1)). p = 10%, theta = 5 gives risk x1.84
  for swaps (~2) and x7.96 for straddles (~8). Linear risk scales with theta^2, gamma risk with theta^4.
- **Frequency check**: under normality a |move| > 2 sigma occurs ~1 in 22 days (57 in 1260), > 3 sigma ~1 in 370
  (Barclays, Global Rates Weekly, 2 Oct 2026). Count exceedances per month; > 2x expected = fatter tail regime (they
  saw 5 two-sigma days in March 2026). Excess kurtosis of PC coefficients (1y trailing): PC1 1.2, PC2 6.4, PC3 8.8,
  higher PCs 18-140 (Musaelian 2016).
- **Heavy tails**: if tail index < 2 variance is infinite and sigma-based stress sizing understates tails (Shafer & Vovk,
  Probability and Finance, 2001); with only mean and variance, one-sided Chebyshev P(X >= mu + a) <= s^2/(s^2 + a^2)
  caps the tail probability (Ross, A First Course in Probability 8th ed., 2010). IRS monthly returns: average excess
  kurtosis 2.6 and vol targeting raised it (Macrosynergy, IRS swap returns, 2025).
- **Estimator size**: CVaR at 99% from ~200 observations uses ~2 points; max drawdown hinges on one path point.

### 8. Reverse stress and risk-budget calibration
- Linear closed form: worst shock on the ellipsoid d' Sigma^-1 d = MD^2 is **d\* = MD * Sigma * DV01 / c**, loss =
  **MD * c** with c = sqrt(DV01' Sigma DV01). Set MD = Z * sqrt(n) with Z ~ 3. This is `reverse_stress` in the script.
  It ignores gamma; for non-linear books run the same search by Monte Carlo over the first 6-8 PCs rather than the
  raw curve-building instruments (that produces implausible curves; QSE, steepener thread).
- Reverse from a loss: find scenarios producing the loss limit and read their Z. Loss-limit scenario with Z < 1.5 = book
  too big.
- Leverage cap from worst history: max leverage = tolerable one-period drawdown / worst historical one-period loss;
  take min(half-Kelly, that cap) (Chan, Quantitative Trading, 2009).

### 9. Probability-weighted scenarios for trade expected return
Two steps (Salomon Brothers, Understanding the Yield Curve Part 6, Nov 1995): (1) horizon return per scenario; (2) assign
probabilities. **Always back out the implied mean shock, bp vols and correlations** (`implied_view`) and check them
against your own view: a scenario set carries a hidden mean (curve view), vol (convexity value) and correlation.
Viewless decomposition: subtract the weighted mean shock from every scenario; duration impact of view = with-view
return - viewless return; value of convexity = viewless - neutral zero-vol return. A single base scenario assumes
zero vol and understates positive convexity. Value of convexity = 0.5*Cx*sigma_bp^2 with a **normal (bp) vol**; bp vol over
a 3m horizon = relative implied vol x yield / 2 (de-annualise sqrt(1/4)). 30y zero at 8% (price 9.50), +-200bp: 5.40 / 17.00, mean
11.20, so $1.70 is the convexity value (Salomon Brothers Part 5, Sep 1995). It is only as good as the vol forecast: including the
1980s more than doubles it.

### 10. Hedge, trim, re-run
- Add stress constraints to hedge optimisation: w'L <= e1 and (w - w_b)'L <= e2 (L = scenario loss vector).
- VaR-minimising trade in one bucket: only one is valid at a time; trade ~50% of each suggestion and re-run.
  Multi-instrument: S_trade = -Q_MM^-1 Q_M S over the M allowed buckets (Darbyshire 2022). If the best single hedge cuts
  VaR by only ~15%, the risk is RV/combination risk, not direction; hand to [port-portfolio-construction](../port-portfolio-construction/SKILL.md).
- Correlation add-on for multi-leg packages: charge k x (c_corr - c_zero_corr), k = 15% in the source; floor it when
  correlations are negative (Darbyshire 2022).

## Worked examples
1. **Is 150bp a lot?** 31 Jan 2020, 11 tenors: sigma(xi) = 199 so the 1-SD parallel = 199/sqrt(11) = 60bp/yr, 150bp = 2.5 SD,
   P(>= +150bp in 1y) = 0.00621 (BlackRock 2023). On 30 Sep 1996 the 1-SD parallel was 92bp, so 200bp = 2.17 SD
   (Golub & Tilman 2000). The script's `sd_multiple` reproduces 2.5 with a rank-1 60bp covariance.
2. **Which direction of the same equity shock?** S&P -500bp with 10y -30bp (risk-off): Z = 1.94, exceedance 4.02%;
   S&P -500bp with 10y +30bp (taper-tantrum type): Z = 2.79, exceedance 0.96%. Risk-off is >3x as likely because
   stock-bond correlation was negative (BlackRock 2023). The sign of the rates leg decides plausibility.
3. **Non-unique fly 01.** Bucket risks -10 (2y), +20 (5y), -30 (10y). Scenario 1 (2s, 10s flat, 5s +0.5bp) and
   Scenario 2 (2s, 10s each -0.5bp, 5s flat) both move the fly +1bp but make $10 vs $20 (risks here are P&L per +1bp, i.e. -DV01 in this skill's convention).
   State the leg moves behind any spread or fly shock (QSE, steepener thread, 2021). Curve gamma: a duration-flat book
   with +100k/bp 2s30s steepener risk and curve gamma -5k per bp of spread, after 2s30s falls 10bp (inverts), has
   100k + (-5k)(-10) = +150k steepener risk, and the loss exceeds $1mm.
4. **CoVaR and the VaR-minimising hedge** (Darbyshire 2022, Ex 14.5 / 14.6): Q = [[8.7,7.4,5.1,2.2],[7.4,7.3,4.7,2.2],
   [5.1,4.7,4.9,1.8],[2.2,2.2,1.8,1.9]] (2y/5y/10y/30y daily bp), S = (-10000, 2500, 10000, -4000). Source c = 16,174,
   VaR 1% = 37,620; best single trade 2Y +2,948 (c down 15.6%); best pair 2Y +8,562 and 10Y -9,476 cuts c ~70%. With the
   printed (rounded) Q the script gives c = 16,402 and pair 8,536 / -9,405 (within 3%).
5. **Implied views of a scenario set** (Salomon Brothers Part 6, Fig 7): five zeros 1-5y at 6.00-7.00%, scenarios
   +100, -100, 0, bear flattener (+100..+50), bull steepener (-50..0), equal weights. Implied mean +10bp at every tenor
   (mild bear bias), implied vols 80/76/72/69/66bp (inverted vol term structure), correlations >= 0.92, E(h) = 6.82% =
   6.50 yield income + 0.50 rolldown + 0.02 convexity - 0.20 duration impact. `implied_view` reproduces the shocks'
   statistics.
6. **Barbell vs bullet breakeven**: sell 10y par, buy 0.53x30y + 0.47x1y, carry give-up 71bp. Breakevens: 11bp of 10s30s
   narrowing with no parallel move, or a 138bp parallel shift. History: 10s30s narrowed >= 11bp within a year 30% of
   the time, 10y moved > 138bp 17% (Salomon Brothers Part 5, Sep 1995). Barbell-bullet P&L is 99% reshaping: a curve trade,
   not a convexity trade.
7. **Funding stress arithmetic**: assume half of a $600bn gross levered short is basis and half of that unwinds
   (~$150bn): < 5% of government MMF assets, futures richen, Treasuries cheapen vs OIS/SOFR so swap spreads tighten
   (J.P. Morgan, When market risk meets operational risk, 10 Mar 2020). Margin $170mm (2.9%) -> $665mm (10.6%) in five
   months at MF Global with the position at $11.5bn vs a $4.75bn limit (Tuckman & Serrat 2022).

## Signals & interpretation
Thresholds are defaults to calibrate with the user's risk limits.
- **Scenario Z**: < 1.5 is a mild move, not a stress; 2.5-3.5 = severe plausible (taper 2.5, China crash 3.1);
  >= 5 = GFC class. The headline stress loss should be quoted at Z ~ 3 and at the worst named historical window.
- **C > 1**: inconsistent scenario. Re-sign a factor or re-run with the conditional (regression) shock.
- **Stress/VaR ratio** = worst scenario loss / 99% historical VaR (same horizon). Ratio > ~3 (heuristic): the book has
  gamma, funding or correlation risk that VaR cannot see; trim, add convexity, or lengthen funding.
- **Risk decomposition**: if > 50% of the worst loss is in one PC, hedge that PC; if the book is PC1/PC2/PC3 neutral
  but the loss comes from replay windows, the residual (flylet) or funding channel dominates.
- **DV01-flat is not shock-flat**: long 50k/bp 5y vs short 25k/bp in 2s and 10s wins in rallies (belly outperforms)
  and 10s30s tends to flatten in a sell-off (Credit Suisse 2012; Tuckman & Serrat 2022). Always cite the sign of the worst
  shock (rally or sell-off, steepen or flatten).
- **Convexity-event risk** rises as the mortgage P/S spread compresses toward ~105bp and beta of mortgage rates to
  USTs rises (BofA 2021). Bank rebalancing is threshold-based and infrequent, so flows catch up in size
  (J.P. Morgan, Is bank convexity hedging lying in wait?, 31 May 2019).
- **Stress-regime read**: a long-convexity side should do well in COVID, 2022, SVB; its weak spot is long calm
  stretches. A short-vol-like carry book (steepener carry, EGB carry, short CTD basis) has a high hit rate that is not
  evidence of richness: 23 of 25 short CTD basis trades won, keeping 4.9/32 of 6.7/32 sold, with a 17/32 stress case
  (Burghardt et al., The Treasury Bond Basis 3rd ed., 2005).

## Pitfalls
- Summed DV01 assumes parallel moves; fine for 9.5y vs 10y, not 2y vs 10y. A DV01-neutral hedge can give the opposite of
  the intended exposure (Huggins & Schaller 2024).
- Instantaneous shocks flatter option and carry books; carry matters for the less extreme scenarios.
- PCA loadings and signs drift with regime (Jan vs Mar 2020); a calm window gives small J, H and false comfort: always run
  the mixed-normal tail. In-sample variance identities fail out of sample. A calm Treasury market hides fragile demand:
  normal-time prices show total depth, not the part that survives stress (Delao & Li, NBER WP 35612, Aug 2026).
- Naive EWMA lags a vol spike; long history overstates risk in benign years. Fall-1998 swap-spread widening was a 7-10 SD event on
  EWMA vol at 31 Jul 1998 but ~3 SD on 10y history. Supplement VaR with deterministic stress and avoid fixed VaR limits
  that force selling at the worst time (Golub & Tilman 2000).
- "Existing VaR methodologies are neither capable of, nor should they be used for, predicting losses from catastrophic
  events" (Golub & Tilman 2000). Spread vol does not scale with sqrt(t) because yield changes are positively correlated:
  use empirical horizon-specific slope SDs (30y-15y 3.7/4.9/6.0/7.3/9.3bp at 2w/1m/2m/3m/6m; Burghardt et al. 2005). The
  script's horizon scaling is sqrt(h): crude, say so.
- Do not demean returns for the risk covariance. Short half-lives shrink the effective sample (8-day half-life ~ 23
  observations). Stale or asynchronous prices understate correlation (blend daily with weekly).
- Scenarios from curve-building instruments (Monte Carlo) create implausible curves; simulate in PC space.
- Crowded one-way positioning after prolonged low vol plus VaR limits amplifies sell-offs: JGB "VaR shock", Jun-Aug 2003, stop-loss
  feedback on depleted market-maker balance sheets (During, Fixed Income Trading and Risk Management, 2021).
- A duration-neutral 10s30s flattener needs at least 2 PCs; its worst case is a rally plus steepening, which PC1-only risk misses (Golub &
  Tilman 2000).
- Conditional-stress betas estimated in one regime may not hold in another (Shalizi, Truth about Linear Regression, 2025).
- One-factor correlation breakdown: the linear hedge residual is sigma_y^2 (1 - rho^2); stress rho, not just shocks (Ross 2010).
- Basis: convergence holds only for the CTD; WI bonds enter baskets in big moves; lock-the-CTD hedge ratios jump where
  candidates bunch (use probability-weighted BPV/CF). Scenario CTD maps rest on yield betas that "vary greatly over time".
- Vol targeting on trailing vol failed to contain fat tails (kurtosis 2.4 -> 2.9) and fails where vol is low just before a
  crisis; vol-normalised relative positions keep directionality to global risk (Macrosynergy; Willer & Saunders, Trading
  Global Macro Markets, 2026).
- Treasuries are not a reliable equity hedge when core inflation is high (positive stock-bond correlation above ~2.5% core CPI, the
  authors' rule of thumb); 2022 was the example (Willer & Saunders 2026).
- Source inconsistencies to avoid copying: FOMC-day vol multiplier (x3 vs x2), wildcard window (6 vs 15 hours).
- Never present a stress number without its horizon, shock vector (bp per tenor), covariance used and what was excluded
  (carry, funding, margin, bid/offer).

## Output
Return, in this order:
1. **Scenario table**: scenario, shock per bucket (bp), P&L (ccy), % of risk capital, Z, C, SD multiple, horizon, instant
   vs horizon return. Sorted worst first. Mark deliberately implausible rows.
2. **Factor exposure**: P&L per +1 SD of PC1/PC2/PC3 (horizon), per-bucket DV01/gamma/cross-gamma, curve gamma, and the
   residual after PC1-3.
3. **Replay table**: named windows (loss, worst day, what drove it), plus the 1/5/10-day worst historical P&L.
4. **Tail table**: HVaR, filtered HVaR, ES, CoVaR at 99% and the mixed-normal (p = 10%, theta = 5) multiplier; stress/VaR ratio.
5. **Funding table** (levered books): haircut +X -> cash call, repo spread +Y bp overnight and term, margin change, CCP
   basis loss, exit-cost assumption, days to unwind.
6. **Reverse stress**: the shock at Z = 3 and the Z of the loss-limit breach.
7. **Verdict**: top three loss drivers, the cheapest hedge or trim (re-run after it), and a kill / de-gross trigger.
Hand the verdict to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) (risk section),
[rv-devils-advocate](../rv-devils-advocate/SKILL.md) (what breaks it) and
[port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md) (size to the stress loss).

## Scripts
- [`scripts/scenarios.py`](scripts/scenarios.py): shock builders (knot/twist/Citi-7), PCA loadings in bp per SD, ladder P&L
  with gamma/cross-gamma, window replays, rolling-window P&L, historical VaR/ES, CoVaR and allocation, SD multiple,
  Mahalanobis Z and correlation z, conditional shocks, reverse stress, implied-view of a scenario set, invariant
  PC risk with mixed-normal tail. CLI: `python scripts/scenarios.py --ladder ladder.csv --curve curve_par.csv --curve-id USD-SOFR
  --window covid:2020-02-20:2020-04-30`. `--selftest` checks 14 groups of known-answer cases (analytic P&L, BlackRock 2.5 SD,
  Darbyshire VaR/ES, Ilmanen implied vols, PCA recovery of known loadings, Monte Carlo check of the invariant-risk
  formulas) and exits non-zero on failure.

## Related skills
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): key-rate ladder and risk transforms that feed this.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA construction, stability, PCA-neutral hedges.
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): EWMA/shrinkage covariance for Z and CoVaR.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): scenario trees and regime weights. See also [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md) and [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md) for event shocks and probabilities.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll in horizon returns.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md), [curve-butterflies](../curve-butterflies/SKILL.md): leg moves behind spread and fly shocks.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR futures conventions (tick, BPV) for the grids.
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): CTD scenario grids.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): implied repo and basis funding.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo stress, term vs overnight.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): cross-CCP basis stress.
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): tail hedges once a scenario hurts.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md), [port-portfolio-construction](../port-portfolio-construction/SKILL.md): sizing and combination against the stress loss.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): stress windows in backtests.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables.

More: [scenario library](references/scenario_library.md) (named windows, hypothetical templates, per-market notes) and
[tails, funding and liquidity detail](references/tails_funding_and_liquidity.md).

## References
- BlackRock's Guide to Fixed-Income Risk Management (B. Golub ed., Wiley, 2023): curve-shock probability, conditional stress, Mahalanobis Z and risk ruler, HVaR/EHVaR backtest, Brexit and trade-tension scenarios.
- Golub & Tilman, Risk Management: Approaches for Fixed Income Markets (Wiley, 2000): explanatory power, magnitude/shape plausibility, stress-test design rules, EWMA vs long history.
- Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): CoVaR, VaR-minimising hedges, PCA scenario draws, cross-gamma, correlation add-on.
- Salomon Brothers (A. Ilmanen), Understanding the Yield Curve Part 6: A Framework for Analyzing Yield Curve Trades (Nov 1995): probability-weighted scenarios, implied views, viewless decomposition.
- Salomon Brothers (A. Ilmanen), Understanding the Yield Curve Part 5: Convexity Bias and the Yield Curve (Sep 1995): barbell breakevens, value of convexity under vol scenarios.
- Musaelian, Nagarajan, Villani, PCA: invariant risk metrics and representation of residuals for bond returns (SSRN 2777026, 2016): delta+gamma PC risk, mixed-normal tail stress, flylets.
- Credit Suisse, PCA Unleashed: PCA across European Rates markets (24 Oct 2012): PC exposure, neutralisation, regime-dependent loadings.
- Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): PCA reconstruction scenarios, horizon-dependent correlation.
- Burghardt, Belton, Lane, Papa, The Treasury Bond Basis, 3rd ed. (McGraw-Hill, 2005): CTD scenario method, level x slope grid, slope vol by horizon.
- J.P. Morgan, Basis Scenario Analysis Report (28 Oct 2026) and The switch and the spur (29 Oct 2026): beta-weighted CTD grids, twist overlays.
- RiskVal, Future CTD Scenario Analysis user guide (25 Apr 2024): PCA-SD shocks, twist matrix, delivery probability.
- CFTC Market Risk Advisory Committee, The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): required stress scenarios, March 2020 figures.
- Tuckman & Serrat, Fixed Income Securities, 4th ed. (Wiley, 2022): MF Global haircut stress, repo tails, PCA front-end coverage.
- J.P. Morgan, When market risk meets operational risk (10 Mar 2020): unwind arithmetic, stress liquidity.
- J.P. Morgan, Are we there yet? Fixed income market liquidity (1 Apr 2020) and Fast and furious (20 Nov 2018): liquidity index, liquidity-to-vol chain.
- Clarus Financial Technology (A. Khwaja), Hedging the CME-LCH Basis (26 May 2015): CCP basis scenario and switch economics.
- BofA Global Research, MBS convexity hedging and TSY market (18 Mar 2021); J.P. Morgan, Is bank convexity hedging lying in wait? (31 May 2019): hedge-need formula, bank convexity model.
- Citi Research, Agency MBS Weekly: The Summer Lull (21 Aug 2026): seven-scenario curve template.
- Quantitative Finance Stack Exchange, steepener/flattener/butterfly sensitivity (Oct 2021), advanced bond risk transformations (Mar 2021): bucket scenario P&L, curve gamma, tail PCs.
- Barclays Research, Global Rates Weekly: The urgency question (2 Oct 2026): tail-frequency check.
- Macrosynergy, Interest rate swap returns: empirical lessons (2025): fat tails, vol-targeting failure, cross-market correlations.
- Financial Times Alphaville, The Treasury market's toxic codependency (14 Aug 2026): strategy-specific vulnerabilities, positioning sizes.
- Delao & Li, Beliefs about Government Debt Valuation and Sustainability (NBER WP 35612, Aug 2026): normal-time prices vs stress capacity.
- Willer & Saunders, Trading Global Macro Markets (Wiley, 2026): hedges in drawdowns, stress clusters, trailing-vol targeting.
- Ross, A First Course in Probability, 8th ed. (2010): one-sided Chebyshev, linear hedge residual. Shafer & Vovk, Probability and Finance (2001): heavy tails.
- Chan, Quantitative Trading (Wiley, 2009): leverage cap from worst historical loss. Shalizi, The Truth about Linear Regression (CMU draft notes, Oct 2025): regime dependence of regression betas, bootstrap choices.
- Also cited in the reference files: BNP Paribas, EUR curve convexity: lessons from history (25 May 2021); Yadav & Younger, Central Clearing the U.S. Treasury Market (Univ. of Chicago Law Review, 2025); BofA, Debt limit FAQ: spring 2025 update (12 May 2025) and Eliminating IORB (13 Jun 2025); BofA, Understanding Principal Components (21 Aug 2020); FactSet, Interest Rate Future (23 Mar 2023); Treasury Borrowing Advisory Committee, Treasury futures positions across investor types (30 Jan 2024); Duering, Fixed Income Trading and Risk Management (Wiley, 2021); Palomar, Portfolio Optimization (CUP, 2025); Citi Research, EM Strategy Weekly (20 Aug 2026); Financial Times, quant hedge funds worst day in 2 years (20 Aug 2026).
- Litterman & Scheinkman, Common factors affecting bond returns (Journal of Fixed Income, 1991) (external): three-factor PCA of the curve.
- Hull & White, Incorporating volatility updating into the historical simulation method for VaR (Journal of Risk, 1998) (external): filtered historical VaR.
