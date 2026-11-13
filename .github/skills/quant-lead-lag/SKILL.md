---
name: quant-lead-lag
description: 'Measures which market, curve point, instrument or indicator moves first and how much of that move carries over - cross-correlation lag scans on changes, Granger causality, lead-lag betas with HAC errors, VAR with Cholesky impulse responses and variance-decomposition bounds, Hasbrouck information shares, rolling transmission betas/R2 to a global anchor (USD, JPY, Bund, PC1), Levy-area lead state. Use when asked who leads whom, does UST lead Bund / gilts / JGB / ACGB / NZGB / NOK / SEK, Fed leads G10 central banks, which leg to execute first, futures vs cash or swap vs bond price discovery, lagging market catch-up, spillover or contagion between markets, leading indicator timing (inversion to cut, breakevens or oil before a 10y peak), speech or sentiment score lead, global factor beta, or how stale an illiquid quote is. Posterior inference of an unprinted price: quant-bayesian-methods.'
---

# Lead-lag and cross-market transmission

A relative-value gap between two markets is only a trade if you know whether the *other* market is going to move to you
(the lagger catches up) or you are going to move to it (the leader is simply right). Lead-lag analysis answers three
questions with numbers: **who moves first** (sign of the best lag, Granger direction), **how much of the move carries
over** (lead-lag beta, R2, impulse response) and **how stable that is** (rolling betas, structural breaks, decay with the
lead). Most real leads in rates are small (the Fed leads the G9 policy rates by about three months with a peak correlation
of only about 0.10, Citi, Global Macro Views, 13 Aug 2026) and regime dependent, so the default stance is sceptical: a lead
must survive differencing, prewhitening, out-of-sample re-estimation and a cost check before it becomes a signal.

## When to use
- "Does UST lead Bunds / gilts / JGBs / AUD / NZD / CAD, and by how long?" or "has the global driver switched (USD to JPY)?"
- Futures vs cash, swap vs bond, venue A vs venue B: which price moves first, which leg to execute first, which is the hedge driver.
- A lagging market looks cheap after a leader move: how much catch-up should we expect (beta x leader move) and how fast does it decay.
- A thin or closed market (NOK, SEK, NZD, AUD in the wrong time zone, off-the-run) needs a fair-value estimate from liquid markets.
- Leading-indicator timing: does an inversion, breakeven, oil, credit, positioning or speech-score move precede the rates move, with what lead and hit rate.
- Checking a published "X leads Y" claim before it goes into a trade note (see [rv-research-digest](../rv-research-digest/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Yields, par/OIS rates or constant-maturity curve points by market (bp changes are derived) | `curve_par`, `curve_zero` | daily on ONE `snap`, >= 500 obs (>= 250 minimum); weekly for cross-time-zone blocs | Never mix snaps in one series. Tenor and forward start identical across markets (10y vs 10y, 5y5y vs 5y5y) |
| Bond or futures prices for cash-vs-futures or on/off-the-run leads | `bond_quotes`, `fut_quotes`, `stir_quotes` | daily or intraday bars on a common clock | Generic futures must be roll-adjusted before differencing (see [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md)) |
| Spreads (swap spread, ASW, basis) as the lagger | `swap_spreads`, `basis_swaps` | daily | Sign convention of the spread must be stated by the caller |
| FX for rate-differential-to-FX leads | `fx_rates` | daily/weekly on the same snap | `EURUSD` = USD per EUR |
| Macro releases, central-bank text scores | `macro_series` | per release vintage (`pub_ts_utc`) | Measure leads from release time; use first-release vintages (`is_first_release`) to avoid look-ahead |
| Positioning and flow | `positioning`, `flows_trades` | weekly (positioning), daily | Positioning is published with a delay; lag from publication, not reference date |
| Output candidate for a rule | `signals` | daily | `value` in bp or z |

If an input is missing, ask for it or hand off to the data adapter (see [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)). Never invent values.

## Method

### 0. Name the question and pick the tool
| Question | Tool | Section |
|---|---|---|
| Which of two series leads, and at what lag? | cross-correlation scan of changes + Granger both ways | 2, 3 |
| How much of leader's move does the lagger deliver, and over how many days/weeks? | lead-lag beta (HAC), decay with lead length | 4 |
| Several markets, shocks correlated: who explains whose variance? | VAR, Cholesky IRF, FEVD min/max | 5 |
| One security in several venues (future vs cash, swap vs bond): price-discovery share | information-share bounds (VECM if cointegrated) | 5, `references/microstructure-and-price-discovery.md` |
| Has the global driver or beta changed? | rolling beta/R2 to anchors, structural break | 6 |
| Illiquid market, estimate where it would print | Bayesian conditional mean | 7 |
| Does an indicator precede a rates turn? | event study with lead-time distribution | 8 |

### 1. Prepare the series (this step creates or destroys most "leads")
1. **Differences, not levels.** Work in first differences in bp (or log-returns for prices). Two trending levels show a spurious lead at every lag. Differencing alone is not a cure for non-stationarity ("you don't make a nonstationary time series stationary simply by first-differencing it", Hasbrouck, Empirical Market Microstructure, 2004); if the levels are cointegrated (same security in two markets, futures vs cash) a VAR in differences is misspecified: use an error-correction model (see [quant-cointegration](../quant-cointegration/SKILL.md)).
2. **One clock.** Align to a common snap. Across time zones use one weekly close (Citi used the Wednesday close for Asia 5y5y vs USD, so a US move on day T is not read as an Asian move on T+1, Citi, Decomposing Global Rate Drivers Across EM Asia 5y5y, 13 Aug 2026). With daily data, a "lead" of exactly one day between NY and an Asia-Pacific market is mostly a clock artefact: compare NY day T with the local close on T+1, or use weekly data.
3. **Do not chain overnight into intraday.** Treat each session as its own sample and drop its first change (Hasbrouck 2004).
4. **Clean traded prices.** Bid-ask bounce inflates short-horizon variance and creates negative first-order autocorrelation; use mids or settlement snaps, never last trade in rates.
5. **Publication time for macro or positioning.** The lead starts when the number was public (`pub_ts_utc`), not at the reference period.
6. **Standardise or work in bp consistently.** Cross-correlation is scale-free; betas are in bp of lagger per bp of leader, so keep both legs in bp and the same tenor.

### 2. Cross-correlation lag scan
For lag k = -L..L compute `rho(k) = corr(x_t, y_{t+k})` on the (prewhitened) changes. **k > 0 means x leads y** by k bars; the scan is symmetric so the sign of the best lag tells direction. Defaults:
- L = 10 bars for daily data, 12 for weekly or monthly (Citi scanned +/-12 months for Fed vs G9). Larger L multiplies chances of a false peak.
- **Prewhiten**: fit an AR(p) (p by BIC, <= 5) to x and apply the same filter to y. Without it, autocorrelated series give a broad hump of significant cross-correlations around zero that look like a lead.
- **Significance with multiplicity**: `crit = z_{1 - alpha/(2(2L+1))} / sqrt(n)` (Bonferroni over 2L+1 lags, alpha = 5%). For n = 1000 daily bars and L = 10 (21 lags, z = 3.04) this is about 0.096. A peak below `crit` is noise; a single significant spike with neighbours near zero is still fragile ("it is not generally a good practice to pick one particular coefficient at one particular lag", Hasbrouck 2004).
- Compare `|rho(k*)|` with `|rho(0)|`: a real lead has `|rho(k*)|` clearly above the coincident value (Fed vs G9: peak about 0.10 at +3 months, above the coincident value, but the +2 month value was negative, so "often leads but behaves idiosyncratically", Citi 2026).
- **Variance explained = rho^2.** rho = 0.10 explains 1% of the variance: a statistically real lead can be economically useless as a standalone trade.
- Lag selection when the lead length itself is the question (speech score to yields): re-estimate for leads 0, 1, 4, 8, 13 weeks and report where significance disappears (JPM Lupton, NLP of central bank speak, 26 Apr 2023: usable to about 8 weeks, gone by 13).

### 3. Granger causality
For y (the candidate lagger) and x (the candidate leader), with p lags:
- restricted: `y_t = c + sum_{i=1..p} a_i y_{t-i} + e`; unrestricted adds `sum b_i x_{t-i}`.
- `F = ((RSS_r - RSS_u)/p) / (RSS_u / (n - 2p - 1))` with n = bars actually used in the regression (T - p), ~ F(p, n-2p-1) under H0 "x does not Granger-cause y" (assumes homoskedastic errors: rate changes are not, so confirm with a heteroskedasticity-robust Wald test or the rolling version).
- Run **both directions** and report `F`, p-value and p for each. Choose p by BIC on the unrestricted equation (default cap 6 daily, 12 monthly) and show neighbouring p for robustness.
- Meaning: lagged x improves the *forecast* of y. It is not economic causation: a common driver arriving at different speeds produces Granger "causality" (a UST-to-Bund result may just be a US-driven global factor that Bunds price with delay). Where sub-monthly windows cannot separate "following the Fed" from common global responses, use the first principal component of the bloc as the leader rather than one market (JPM Jarman and Bassi, Talk is Cheap, 30 May 2024).
- Published illustration of the method: a Bund-factor-vs-inflation VAR gave Granger F = 6.12 (p = 0.03) with a peak cross-correlation of about 0.75 at the 4th lead (Dunis, Laws, Naim, 2003); a peak that large is more typical of persistent series: re-test on differences before believing it.
- **Failures are informative.** In that study Granger tests from the Fed to the other central-bank scores mostly failed except for the ECB, and lags beyond one month added nothing, even though a Fed shock raised other banks' scores in the same month. Treat "no Granger result" as "no incremental predictability at this frequency", not as "no relationship".
- Always **control for the lagged dependent change**: adding the lagged 90-day rate change roughly halved the speech-score effect (JPM Lupton 2023).
- Decide what the answer is *for*: which leg to execute first, which leg is the hedge driver, which leg is the forecast target. If both directions reject, the pair is jointly determined: use VAR/IRF (section 5) or treat as contemporaneous.

### 4. Lead-lag beta and decay
`y_{t+k} = a + b x_t + e`, k = best lag, Newey-West (Bartlett) standard errors with `L_nw = floor(4 (n/100)^(2/9))` (use `max(L_nw, h-1)` when the dependent variable is an overlapping h-bar change). Output b (bp per bp), t, R2, n.
- `b(k)` is the response exactly k bars later, not the cumulative one. Expected remaining catch-up of the lagger after a leader move `dx` it has not yet printed: `sum_{j>=0} b(j) x dx` over the remaining lags (valid on prewhitened x; or regress the cumulative change `y_{t+k} - y_t` on `x_t`). The trade edge is the residual `gap = expected catch-up - (observed lagger change since last sync)` in bp (positive: lagger yield should still rise), compared with the round-trip cost and the DV01 mismatch between the two legs.
- Estimate the **decay profile**: b(k) for k = 0..K. Report the first k where |t| < 1.96. The Lupton speech-score effect fell from about 12-13 bp per 10 score points at lead 0 to about 7-9 at 4 weeks, 3-4 at 8 weeks and about 0 at 13 weeks.
- Re-estimate in rolling windows (below) and require the sign to be the same in each sub-sample before using it.
- Add a zero-lower-bound or regime dummy interaction when the relation depends on regime (US speech effect +22 bp outside the ZLB vs +11 bp inside; without the interaction the effect is biased down, JPM Lupton 2023).

### 5. VAR, impulse responses, variance decomposition
Use when several markets move together and shocks are correlated (e.g. UST, Bund, gilt 10y changes).
1. Fit a VAR(p) on changes by OLS, p by BIC (cap p so parameter count << n; a VARMA or high-dimensional VAR has many parameters, Palomar, Portfolio Optimization, 2025).
2. Convert to the vector moving average by feeding unit shocks: `Theta_0 = I`, `Theta_h = sum_{j=1..min(h,p)} A_j Theta_{h-j}`.
3. **Cholesky orthogonalisation**: `Omega = F F'` with F lower triangular; orthogonalised responses are `Theta_h F`. For two variables `F = [[s1, 0], [rho s2, s2 sqrt(1 - rho^2)]]`. The first-ordered variable gets all of the common shock: **the ordering is an assumption, not a result.** Default ordering: most exogenous / largest economy / earliest-closing market first (Fed first, then others by economy size in JPM Jarman and Bassi 2024); re-run in reverse order.
4. Plot **cumulative** IRFs (`sum_{j<=k} E[dp_{t+j} | shock]`) for price changes; individual VAR coefficients are not price impact.
5. **Forecast-error variance decomposition** at horizon h: `sum_{j<h} Theta_j Omega Theta_j'`; shares are order dependent when Omega is not diagonal. Report the **minimum and maximum share over all orderings** (n! orderings, n <= 6; bounds are wide when correlation is high). Do not reduce to one point estimate.
6. **Information share** (one security in several markets): `IS_j = (psi F)_j^2 / (psi Omega psi')` where psi is the common long-run row of the VMA; bounds again over orderings. In the diagonal case `IS_j = psi_j^2 omega_jj / sum_k psi_k^2 omega_kk`; a market with less pricing noise (a more precise price) earns a higher share. Under cointegration estimate psi from a VECM, not a VAR in differences (derivations and the 2x2 closed form in [references/microstructure-and-price-discovery.md](references/microstructure-and-price-discovery.md)).
7. Random-walk (permanent) variance from an MA: `sigma_w^2 = theta(1)^2 sigma_e^2`, `theta(1) = 1 + theta_1 + ...`; it is *not* `sum_j Theta_j Omega Theta_j'`.

### 6. Transmission regime monitor (rolling beta/R2)
1. For each market i and tenor/forward bucket (1y1y, 5y5y, 10y), regress **daily changes** on the anchor's equivalent changes (USD; JPY; the bloc PC1): `dy_i = a + b dy_anchor + e`, over a **short** window (1 month) and a **longer** window (3 months); report b and R2 for both.
2. The signal is the *change* in R2 and b between windows, not the level. A 1-month window is only about 21 daily bars: R2 below about 0.18 is not distinguishable from zero at 5% (|r| < 0.43), so read the 1-month R2 together with its t-stat and the 3-month window. Example below: R2 of EUR/GBP/AUD 5y5y on JPY changes rose from about 0% to 20-50% in a month, i.e. the marginal global driver switched.
3. **Orthogonalise secondary anchors**: regress the secondary anchor (JPY) on the dominant one (USD) and use the residual as the clean JPY factor; report its *incremental* R2.
4. For a block of markets use rolling PCA (52 weeks weekly). Rolling PCA flips signs and swaps ranks: fix by (a) sign-normalising each PC so the anchor bloc's mean loading is positive, (b) projecting onto fixed full-period loadings for the headline R2, (c) tracking factors by bloc identity, not by PC label (Citi 2026).
5. **Pegged or mechanically linked markets inflate anchor R2** (an HKD-type peg lifted the USD-anchor R2 of PC1 from 0.24 to 0.59; rerun without them).
6. Test for structural break: split-sample R2 (0.47 before 2023, 0.76 after in the Asia example). A full-period average hides it. Hand regime labelling to [quant-regime-detection](../quant-regime-detection/SKILL.md).
7. Statistical significance is not magnitude: JPY was a significant anchor for SGD/KRW/THB yet moderate and fading. Read-off anchor thresholds used by the source (chart small print): USD "strong" R2 >= 0.70, "moderate" >= 0.50, "weak" < 0.10; secondary anchor "meaningful" >= 0.30, "modest" >= 0.10, "weak" < 0.05 (Citi 2026).

### 7. Bayesian inference of an illiquid market from liquid ones
Model moves `dR ~ N(mu, Q)`; partition into transparent markets x (known) and opaque Y (unknown). The maximum-likelihood / conditional-mean move solves
`(Q^-1)_YY (Y - mu_Y) = -(Q^-1)_Yx (x - mu_x)`, equivalently `Y = mu_Y + Q_Yx Q_xx^-1 (x - mu_x)` (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022). Use a linear solve on sub-blocks, never invert the whole matrix. Conditional covariance `Q_YY - Q_Yx Q_xx^-1 Q_xY` gives the uncertainty of the inferred move.
- **Reset rule**: whenever the opaque market actually trades or prints, reset the reference point for *all* moves to that time. Otherwise the inferred move accumulates a stale offset.
- Assumes multivariate normality and a stable covariance: check both. The inferred move is a model output, not a quote; for thin markets (NOK, off-the-run, wide or one-sided markets) it is a fair-value *prior*.
- Q: use a robust or shrunk covariance of the same-horizon changes (see [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md)); a unit-diagonal correlation matrix returns answers in the units of x (the published example does this). With a real covariance the answer scales with vols.
- Fast deterministic alternative along a curve: `R3 = R1 + J dR_anchor`, with J the static weights of each curve point on two anchors (rows sum to 1).

### 8. Leading-indicator timing (event study)
For indicator I and target move M: list the dated events (first inversion, 2-sigma move, score extreme), compute the **lead time distribution** (median, range, n), the **hit rate within a fixed window** (e.g. 12 and 24 months) and the average magnitude. Report n explicitly; most such samples have n < 30 (recession-linked ones n < 10). Other published leads worth testing the same way (numbers in [references/evidence-tables.md](references/evidence-tables.md)): rates to FX (2y differentials beat outrights, rates-FX rank correlation peaks at about 2 months and breaks down in some years, BofA FX Quant Primer, 2018); time-zone dominance of FX returns; CTA beta lead of 15-20 days on a momentum signal (BofA, 18 Aug 2020); HFT depth leading 5-25 minutes (JPM, 5 Mar 2020); conditioning a follower rule on the leader's state (long JGB only when UST yields are below their 55-day average, IR 0.90 vs 0.28, Citi, 21 Aug 2026). Hand the hit-rate and decay into [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md) and validate in [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).

### 9. Levy-area lead state (optional, heuristic)
For two level paths x, y over a window w, anchored at the window start: `A_t = 0.5 sum_i (x'_i dy_i - y'_i dx_i)`; `A > 0` means x leads y (x = cos t, y = sin t gives A > 0). The state is known at the close of bar t: act from t+1. Normalise `z = A / rolling std(A)` over 5w; state flips to "x leads" at z > 1.5, to "y leads" at z < -1.5, to flat at |z| < 0.5, and holds in between (hysteresis). w = 20 daily bars as a starting point. This is a heuristic, robust to non-integer lags but unvalidated on rates here: use it as a monitor to compare against the lag scan, never as a stand-alone entry rule.

## Worked examples
**A. Bayesian inference for a closed NOK 2y (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022, Ex 19.6).** Previous close 16:15 CET 2y: USD 2.20, EUR 0.43, GBP 1.54, NOK 2.02 (%). Before the NOK 09:00 open: USD 2.22, EUR 0.44, GBP 1.56, so x = [+2.0, +1.0, +2.0] bp. Q (order USD, EUR, GBP, NOK): [1, .80, .85, .75], [.80, 1, .87, .84], [.85, .87, 1, .82], [.75, .84, .82, 1]. Conditional mean `Y = Q_Yx Q_xx^-1 x = +1.294 bp`, so NOK 2y inferred at 2.0329%. NOK then prints 2.0275%: **reset** to that print. About 45 minutes later x = [+0.5, -1.5, 0.0] bp (measured from the reset): `Y = -0.710 bp`, inferred NOK 2y 2.0204% (2.0275 - 0.0071). Verified with `scripts/lead_lag.py` (`bayes_infer`, selftest). Reading: the inferred move is a quote *prior*; the 1.29 bp first estimate was 0.54 bp above where NOK actually printed (2.0275 vs 2.0329); the conditional sd from this correlation input is 0.51 (in the units of x, i.e. unit vols assumed), so a miss of about one sd is the size of error to budget when quoting a thin market from liquid ones.

**B. Fast Jacobian curve update (Darbyshire 2022, Ex 19.7).** 4y-10y IRS: 0.750, 0.765, 0.779, 0.782, 0.783, 0.782, 0.781 (%). Bobl moves +0.05 bp (0.5000 to 0.5005%) and Bund +0.15 bp (1.0000 to 1.0015%). Weights (bobl, bund): 6y [0.8, 0.2]: `0.779 + 0.8 x 0.0005 + 0.2 x 0.0015 = 0.7797%`; 8y [0.4, 0.6]: `0.783 + 0.4x0.0005 + 0.6x0.0015 = 0.7841%`. Each row sums to 1 so a parallel anchor move shifts the curve in parallel.

**C. Magnitude check on a "real" lead (Citi, Global Macro Views, 13 Aug 2026).** Fed vs G9 policy-rate changes: peak cross-correlation about 0.10 at a 3-month Fed lead, higher than coincident, but the +2 month value is negative and the G9 net-hiked while the Fed held or cut in 2006-08 and 2010-12. Variance explained = 0.10^2 = 1%. Conclusion: use as a regime tilt on EUR/GBP/AUD front-end positioning, never as a timing signal by itself.

**D. Speech score leads rates (JPM, Welcome to the machine: NLP of central bank speak, 26 Apr 2023).** Dependent: 90-day change in the 1y sovereign yield (bp); regressor: 3-month average speech score lagged 7 days. Univariate: +10 score points gives +14 bp (US), +12 bp (EA), +12 bp (UK). Adding the lagged 90-day rate change roughly halves the Fed effect to about +7 bp (more than 25 pp of probability of a 25 bp hike); full model with ZLB interaction: +11 bp outside, +10 bp in ZLB; residual s.e. 30-40 bp. Lead decay: about 12-13 bp at 0 weeks, 11-12 at 1, 7-9 at 4, 3-4 at 8, about 0 at 13. Read: a 4-8 week modest-R2 tilt, "a better guide to changes in rates rather than the level".

**E. Rolling anchor regression flags a driver switch (JPM, Global Fixed Income Markets Weekly, 21-22 Aug 2026).** Regress daily changes of 5y5y OIS in EUR, GBP, SEK, AUD on JPY changes, past 1 month vs previous 3 months: R2 to JPY rose from about 0% (10y vs JPY 0-4% over the prior 3 months) to 20-50% (5y5y: EUR beta 0.5, R2 30%; GBP 0.5, 21%; AUD 0.7, 50%); EUR 10y vs USD beta 0.7, R2 38%; SEK 10y vs USD beta 0.8, R2 56%. Reading: JPY became a marginal global driver of long-forward rates; a UST-only lead model would have understated EUR/AUD risk.

**F. MA(1) random-walk variance (Hasbrouck 2004).** Autocovariances gamma_0 = 1, gamma_1 = -0.2 (bid-ask bounce). Invertible root: `theta/(1+theta^2) = -0.2` gives theta = -0.2087, `sigma_e^2 = 1/(1+theta^2) = 0.958`; permanent variance `(1+theta)^2 sigma_e^2 = 0.600 = gamma_0 + 2 gamma_1`. Using the non-invertible root (-4.79) gives the same autocovariances but wrong impulse responses: pick the invertible one.

**G. Indicator lead times (Willer and Saunders, Trading Global Macro Markets, 2026).** First 3m10y inversion to recession: median 14 months; to first Fed cut: median 18 months (range 1-23; Oct-2022 inversion to Sep-2024 cut = 23). Cut within 12 / 24 months after inversion, average months to cut: 3m10s 52.2% / 100% / 10.3; 6m2s 73.7% / 84.2% / 12.0; 2s5s 73.3% / 93.3% / 7.7; 2s10s 57.1% / 85.7% / 11.4. Before a 10y sell-off peak: 2y breakevens turn down about 1 month ahead, 5s30s flattens and peaks earlier than 10s, oil often breaks after a more than 20% three-month rally (median sell-off 120 bp over about 135 days, n = 20 since 2000). More evidence tables: [references/evidence-tables.md](references/evidence-tables.md).

## Signals & interpretation
| Reading | Interpretation | Action |
|---|---|---|
| `|rho(k*)|` > Bonferroni band, k* != 0, same sign in both halves of the sample, Granger rejects in one direction only | Candidate leader/lagger | Trade the *lagger* toward `b x dx_leader`; execute the leader leg (or hedge driver) first |
| Peak only at lag 0 | Contemporaneous co-movement | No lead trade; treat as hedge ratio/beta (see [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md)) |
| Granger rejects both ways | Jointly determined / common factor | Use VAR/IRF or PC1 leader; do not label a leader |
| Lead present but R2 < 2% | Real but economically small | Tilt only; combine with other signals |
| Rolling R2 to a new anchor up by > 0.2 in one month and a break test confirms | Global driver has switched | Re-hedge with the new anchor; widen stops on RV trades hedged only vs the old anchor |
| Lead length shrinks across rolling windows, or flips sign | Regime change or crowding | Stand aside; re-estimate (a lead that works "will shrink", WorldQuant, Finding Alphas, 2015) |
| Inferred illiquid-market move vs print differs by > conditional sd | Model failure (covariance break, news specific to that market) | Quote off the print, not the model |
| Neighbour-pair (AUD/NZD, SEK/NOK, CAD/US) at a 1000-day extreme | Alert for reversal, not an entry | Wait for catalyst (Willer and Saunders 2026) |

Hard rules: require the **same sign and lead** in at least two non-overlapping sub-samples, **n >= 250** independent bars per estimate, and a catch-up edge larger than round-trip cost plus 1 s.e. of the beta uncertainty. Report the lag decay, not one lag.

## G10 differences that matter
| Market | Lead-lag role / fact | Source |
|---|---|---|
| USD | Global leader: US contributed about 35% of global growth since 2001; at most turning points the Fed moved first; "US rates set the tone for global rates even in the face of large local shocks". Global-factor beta of 0Yx1Y about 32 bp per 1 sd PC1 | Willer and Saunders 2026; JPM Jarman and Bassi 2024 |
| EUR | Follower (Fed-to-ECB the only Granger rejection in the central-bank VAR). Barbell beta to global PC1 (0Yx1Y about 8.5 bp, 3Yx1Y about 3.3, 10-15Yx1Y about 4.8). ECB asset purchases suppressed US-DE PC1 correlation in 2014-2020; BTP/OAT asset-swap stress fed back into USD swap spreads | JPM 2024; During, Fixed Income Trading and Risk Management 2021; GS cuRated 3 Oct 2026 |
| GBP | Imported moves: much of a recent gilt yield rise came from abroad; 1Yx1Y PC1 beta rose most (5y about 29 bp per sd) | GS Reaching Limits 2 Oct 2026; JPM 2024 |
| JPY | Follows UST for now; response to global PC1 concentrated at the long end; JPY became the marginal driver of EUR/GBP/AUD long-forwards in the recent window | Citi Japan Rates 21 Aug 2026; JPM Global FI Weekly 2026 |
| CAD | Front end followed Fed rhetoric less this cycle; neighbour pair CAD/US | JPM 2024 |
| AUD / NZD | Co-move with USD bloc; NZD had the largest PC2 beta rise; AUD 5y5y R2 to JPY about 50% in the past month; Asia-Pacific closes before Europe/NY so use T+1 alignment | Citi 2026; JPM 2024, 2026 |
| SEK / NOK | SEK 10y R2 to USD 56% (1 month). NOK is thin and opaque (few contributors, wide, no-trade periods): the textbook case for conditional-mean inference | JPM 2026; Darbyshire 2022 |
| CHF | No published lead-lag numbers in the reviewed sources; estimate before use; SNB communication can carry information for other curves through the common factor | JPM 2024 |

## Pitfalls
- **Levels, not changes** produce spurious leads; **over-differencing** a stationary series gives a non-invertible MA (fits look fine, impulse responses are wrong).
- **Unprewhitened cross-correlation** of autocorrelated series: hump of "significant" lags. Always compare with the prewhitened scan.
- **Pick-a-lag overfitting**: choosing the max over 21 lags and testing it at 5% finds a "lead" about 2 times in 3 under the null (1 - 0.95^21 = 66%); use the Bonferroni band and out-of-sample confirmation.
- **Asynchronous closes** (Tokyo/London/NY, futures vs cash settlement times): a 1-day lead can be the clock. Align first.
- **Common driver mistaken for a leader**; **peak correlation small** (0.10) is still labelled "lead".
- **Cholesky ordering drives the answer**; one ordering is a hidden assumption. Report min/max.
- **Cointegrated pair in a VAR of differences**: misspecified; use an error-correction model. Cointegration tests are unreliable in short samples; assume the relationship from economics instead of testing for it.
- **Bid-ask bounce** and stale quotes inflate negative autocorrelation and fake leads at lag 1; **queued orders can move a depth-weighted futures mid** (a 3,000-lot offer added behind 4,500 moved the mid from 98.0131 to 98.0121, Darbyshire 2022, Ex 19.3): check queue depth before using futures mid as a lead signal.
- **Unstable betas**: rolling betas flip with regime (FX-rates and FX-equity correlations broke down in 2011, 2013, 2017, BofA FX Quant Primer, 1 Oct 2018). Non-standard policy suppresses cross-market correlation (During 2021).
- **Rolling PCA sign flips and rank swaps** create false lead-lag: sign-normalise, use static loadings.
- **Pegged markets** inflate anchor R2.
- **Methodology changes** (e.g. PCE methodology shifts moving core YoY by about 0.36 pp) create false leads in macro indicators; and robust-vs-headline measures lag differently by regime (median PCE lagged headline by 8 months in 2022-26 vs 0 in 1978-2001, JPM, US Focus, 13 Aug 2026), so "the lead varies over time and depends on the shock".
- **Lead-lag in high-inflation regimes** breaks rules calibrated in low-inflation cycles (inversion-to-cut lag lengthens).
- **Flow leaks information**: large sustained trades move other markets (a 200mm 10y GBP IRS request moved the 10y about 2 bp across brokers and gilt futures; repeat requests were priced wider, Darbyshire 2022, Ex 18.3). A lead measured from your own flow is not a lead.
- **Crowding**: a lead that works gets traded; withdrawals from a factor are precipitate, infusions slow (WorldQuant, Finding Alphas, 2015).
- **Granger is predictive, not causal**; HAC errors with overlapping horizons need `L_nw` >= horizon - 1.
- **Multimarket splitting**: small traders that split orders across venues remove most of the clean price-discovery results; model order splitting before concluding on price-discovery share (O'Hara, Market Microstructure Theory, 1995).

## Output
Return, for each pair/market tested:
1. **Lead-lag table**: pair (leader x, lagger y), frequency, sample, n, best lag k*, `rho(k*)`, `rho(0)`, Bonferroni band, significant flag, Granger F and p both ways at chosen p, beta (bp/bp), HAC t, R2.
2. **Stability**: best lag and beta per half-sample and in rolling windows; first break date if any; lag decay profile (b(k), t(k)).
3. **VAR block (if used)**: ordering(s), cumulative IRF at 1, 5, 10 bars, FEVD min and max shares at the stated horizon; information share bounds for same-security markets.
4. **Verdict**: LEADER / LAGGER / JOINT / NO LEAD, with one-line reason and the confidence caveats (small R2, regime, clock alignment).
5. **Trade hand-off** (if any): lagger leg, expected catch-up `b x dx` in bp, residual `gap` in bp, cost in bp, expected holding period (pass the gap to [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md) for half-life), the leg to execute first, kill condition (rolling R2/beta breach, lead flips sign). Pass to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).
For opaque-market inference: transparent inputs, covariance used, inferred move and conditional sd, reset time and last print.

## Scripts
- [`scripts/lead_lag.py`](scripts/lead_lag.py): `xcorr_scan` (prewhitened, Bonferroni band), `rolling_best_lag`, `granger` / `granger_table` (matches statsmodels' F-test), `lead_lag_beta` (Newey-West), `var_fit` / `irf_chol` / `fevd_bounds` / `information_share_bounds`, `bayes_infer` (conditional mean and sd), `levy_signal`. NaN-safe: interior gaps keep the longest contiguous block (with a warning) rather than dropping rows, and short samples raise. CLI: `python scripts/lead_lag.py scan FILE --x A --y B --max-lag 10` on a wide CSV/Parquet (date plus one column per series on one snap; differenced by default). `--selftest` checks a simulated 3-bar lead, Granger direction and F against statsmodels, VAR/IRF identities, analytic information shares, Newey-West se against statsmodels, the published NOK +1.294 / -0.710 bp example and Levy-area sign; exits non-zero on failure.

## Related skills
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): ARIMA/VAR/HAC detail, structural breaks.
- [quant-cointegration](../quant-cointegration/SKILL.md): when the pair is cointegrated, use ECM/VECM instead of a VAR in differences.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): contemporaneous betas and rolling or Kalman hedge ratios.
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): the Q used in Bayesian opaque-market inference.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PC1 as the global leader; PCA loadings stability.
- [quant-regime-detection](../quant-regime-detection/SKILL.md): when the lead switches on or off.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life of the catch-up gap.
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): lead length vs holding period, decay, combining leads with value/carry.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): UST-Bund, EGB, gilt, JGB, ACGB betas where leads are applied.
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): building the speech scores that are tested as leading signals.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): the round-trip cost the catch-up edge must clear.
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): positioning series tested as leading indicators (lag from publication).
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): snap alignment, stale quotes, roll stitching.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): walk-forward and multiple-testing control for lead-lag rules.
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): trade-flow data for dealer-direction leads.
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): shrinkage, priors and Bayesian updating.

## References
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): Bayesian opaque-market inference (Ch. 19), NOK worked example, reset rule, Jacobian fast update, spillover anecdote (Ex 18.3), queue-driven mids.
- Joel Hasbrouck - Empirical Market Microstructure, teaching notes (NYU Stern, 2004): VMA/IRF, Cholesky bounds, information shares, VECM, differencing and bid-ask-bounce cautions.
- Maureen O'Hara - Market Microstructure Theory (Blackwell, 1995): multimarket Kyle split, informativeness and cross-market correlation, cash-futures price gap, fragmentation.
- J.P. Morgan - Welcome to the machine: NLP of central bank speak (Lupton, Atlas, Weitzenfeld, 26 Apr 2023): speakers lead statements and rates, lead decay, ZLB interaction.
- J.P. Morgan - Talk is Cheap: Valuing DM Rates Markets with Central Bank Speak (Jarman, Bassi, 30 May 2024): Fed VAR and Granger test, PC1 betas by market.
- Citi Research - Decomposing Global Rate Drivers Across EM Asia 5y5y (Goh, Garg, 13 Aug 2026): rolling PCA with anchors, orthogonalised proxies, structural break, weekly-close alignment.
- J.P. Morgan - Global Fixed Income Markets Weekly (Diamond et al., 21-22 Aug 2026): cross-market beta/R2 spillover table, JPY driver switch.
- Citi Research - Global Macro Strategy Views and Trade Ideas (Willer et al., 13 Aug 2026): Fed vs G9 lead-lag correlation.
- Dirk Willer, Alex Saunders - Trading Global Macro Markets (Wiley Finance, 2026): leading indicators, inversion-to-cut lags, 10y peak leads, global transmission, rate-to-FX tests.
- Goldman Sachs - Global Rates Trader: Reaching Limits (Cole et al., 2 Oct 2026): heteroskedasticity-identified G4 yield spillover (US about 40 bp bearish impulse).
- Goldman Sachs - GS Macro cuRated (Lee et al., 3 Oct 2026): EGB asset-swap spillover to USD spreads; PCE methodology caveat.
- J.P. Morgan - US Focus: Lags in robust PCE cores challenge policy (Hanson, 13 Aug 2026) and US Weekly Prospects (14 Aug 2026): lag-maximising scan, inconsistent Granger results.
- Daniel P. Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): VARMA parameter-count caution.
- J.P. Morgan - Did US rates markets just experience a mini Flash Rally? (Salem, Younger, St John, 5 Mar 2020): HFT depth leads 5-25 minutes, depth lead-lag construction.
- BofA Securities - US Rates: CTAs impact on the rates market (Braizinha, 18 Aug 2020): rolling-regression betas, 15-20 day lead.
- BofA Merrill Lynch - FX Quant Primer (Iaralov, Leng, Vamvakidis, 1 Oct 2018): rates-FX rank correlation by horizon, time-zone decomposition, factor breakdowns.
- Alexander During - Fixed Income Trading and Risk Management (Wiley, 2021): PC1 cross-market correlation regimes (ECB PSPP).
- Citi Research - Japan Rates Weekly: Ball is back in the US court (Fujiki, 21 Aug 2026): JGBs following USTs.
- Dunis, Laws, Naim (eds) - Applied Quantitative Methods for Trading and Investment (Wiley, 2003): Granger/VAR example (Bund factor vs inflation, F = 6.12).
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): crowding and overfitting hygiene.
- James D. Hamilton - Time Series Analysis (Princeton, 1994) (external): Granger tests, impulse responses, variance decomposition (Ch. 11).
- C. W. J. Granger - Investigating causal relations by econometric models and cross-spectral methods (Econometrica, 1969) (external): definition of Granger causality.
- Joel Hasbrouck - One security, many markets: determining the contributions to price discovery (Journal of Finance, 1995) (external): information shares.
