# Microstructure and liquidity metrics: formulas, inputs, thresholds

Group A needs bid/ask quotes, B needs only trade prices or daily bars, C needs an order book or a trade tape with
signed flow, D builds regime monitors from those, E measures toxicity. Pick the cheapest group the data allow.
All spreads here are quoted in the unit of the formula (price fraction, price points or bp); convert to yield bp with
`bp = pts / (ModDur x Price / 10000)` before comparing across instruments.

## A. Quote-based cost measures

- **Quoted spread** = ask - bid. **Customer one-way cost = half the quoted spread** (Tuckman and Serrat, Fixed Income
  Securities, 4th ed., 2022). A round trip is two transactions.
- **Effective spread** = 2 x D x (P_trade - P_mid), D = +1 buyer-initiated, -1 seller-initiated. **Realised spread**
  uses the mid a few minutes later instead of the pre-trade mid and removes the permanent-impact part: effective =
  realised + 2 x permanent impact. Use the aggressor flag where the tape has it; otherwise sign by trade vs mid
  (Hasbrouck, Empirical Market Microstructure, 2004). Midpoint trades and mis-sequencing are known problems.
- **Duration-normalised effective spread (EBA)** = 2 x |P_trade - P_fair| / (ModDur x Price) x 10,000, in yield bp. The factor
  2 puts it on the scale of a quoted spread. Fair value for an off-the-run bond = PV on a curve fitted to firm
  on-the-run quotes plus an idiosyncratic financing and liquidity component from the latest indicative snapshot.
  Keep a security-day only if the model error is under half the indicative spread at every snapshot. Filters used:
  dealer-to-client, at least $10mm, at most $250mm, 08:40-17:00, at least 50 trades per security-day, median per
  size bin (Federal Reserve Board, FEDS 2025-049, 7 Jul 2025).
- **Price improvement vs indicative**: IMPRVT = 1 - median(EBA / IBA), IBA = indicative bid-ask at the latest prior
  snapshot. 1 is the maximum; negative means the trade paid more than the screen. Median 0.50 overall, 0.20 above
  $50mm in the 2018-24 sample (same paper). Indicative quotes are advertising (Duering, Fixed Income Trading and
  Risk Management, 2021): wider than achievable for small size, but can understate large-size cost (95th percentile
  12.41bp vs 4.15bp indicative above $50mm).
- **Time-weight every book statistic** (seconds, not events). Median spread = the smallest observed spread whose
  cumulative time reaches half the window. Sample the top of book only at packet boundaries (mid-packet books can be
  crossed). The prevailing mid for a trade is the book strictly before the trade's own update.
- **Mid algorithms** (Darbyshire, 2022, Ch.19): afda = (bid + ask)/2, unstable on wide-tick contracts; wfda =
  size-weighted, can be spoofed; ida = average price to fill z units on each side (z by cross-validation), robust.
  Example, Bund future z = 65 with book 36 @ 169.70 / 169.71 @ 53 / 78 @ 169.69 / 169.72 @ 88: p_bida = (169.70 x 36 +
  169.69 x 29)/65 = 169.6955; p_aida = (169.71 x 53 + 169.72 x 12)/65 = 169.7118; p_ida = 169.7037. Last traded
  price is unreliable in rates. A least-squares mid across outrights plus listed spreads and flies (weights
  down-weighting spreads) uses all the information in the structure book.
- **Leg-implied structure book**: implied ask = sum over positive weights of w x ask + sum over negative weights of
  w x bid; implied bid the mirror image; size = min over legs of floor(size_i / |w_i|). Fit both sign orientations
  against the listed mid rather than trusting the sign convention.
- **Displayed depth can be fake.** Spoofing is a large order meant to be cancelled plus a small order on the other
  side meant to fill, across futures and cash (FT Alphaville, Another reminder that dealers can spoof, too, 20 Jan 2017).
  Do not treat order-book imbalance in futures as reliable without checking cancel rates.

## B. Spreads and illiquidity from prices or daily bars only

- **Roll (1984)**: p_t = m_t + c q_t, q = +/-1 equally likely. Var(dp) = 2c^2 + s_u^2 and Cov(dp_t, dp_{t-1}) = -c^2.
  Estimator: c = sqrt(max(0, -Cov(dp_t, dp_{t-1}))), full spread = 2c, s_u^2 = Var(dp) + 2 Cov. It is zero whenever
  the autocovariance is non-negative, usually low (sampling error, varying spreads, price improvement) and invalid
  when adverse selection dominates (Hasbrouck, 2004; O'Hara, Market Microstructure Theory, 1995). Example (an
  equity, 821 trades): c = 0.005, Roll spread 0.01 vs time-weighted quoted 0.022 and effective 0.0158.
  Use for rarely quoted instruments (small govies, linkers). Discard overnight changes; treat each day separately.
- **Generalised Roll**: m_t = m_{t-1} + lambda q_t + u_t, p_t = m_t + c q_t, spread = 2(c + lambda). Only the
  random-walk variance s_w^2 = Var(dp) + 2 Cov is identified without signs; with observed trade signs regress dp_t on
  q_t and q_{t-1}. Use cumulative impulse response, not a single coefficient (Hasbrouck, 2004).
- **Corwin-Schultz high/low spread**: S = 2(e^a - 1)/(1 + e^a), with a = (sqrt(2 b) - sqrt(b))/(3 - 2 sqrt 2) -
  sqrt(g/(3 - 2 sqrt 2)), b = sum over the two bars of (ln(H/L))^2, g = (ln(H_two-bar / L_two-bar))^2. Floor negative
  a at 0. Noisy, needs rolling averaging; High/low data almost always inflate returns (Lopez de Prado, Advances in
  Financial Machine Learning, 2018; Chan, Quantitative Trading, 2009).
- **Amihud (2002)**: I = mean over days of |r_d| / Volume_d (days with volume > 0). The source used a 40-day window.
  Bar form: |dlog p| = lambda x sum(p_t V_t). Amivest ratio is the inverse (volume per unit |return|) and misreads
  news-driven days. Pastor-Stambaugh gamma (r_{d+1} = theta + phi r_d + gamma sign(r_d) vol_d) measures reversal:
  gamma < 0 means the flow over-reacted and reverses (Bank of England SWP 580, 2016; Hasbrouck, 2004). For
  swaps use DV01 volume, not notional or trade count, and strip compression, IMM-roll and CCP-basis packages first.
- **Price dispersion (Jankowitsch-Nashikkar-Subrahmanyam)** for prints without quotes: Disp = sqrt(sum_k (V_k/V) x
  ((P_k - m)/m)^2), m = end-of-day mid, or the VWAP variant (use when intraday vol is high; needs at least 4 trades).
  Percentage deviations compare across currencies; low dispersion = low trading cost (Bank of England SWP 580, 2016).
- **Kyle lambda**: dp_t = lambda x signed volume + e. Equilibrium lambda = 0.5 x sqrt(S0 / s_noise^2): illiquidity
  rises with uncertainty about value and falls with noise volume. **Hasbrouck lambda**: dlog p = lambda x sum b_t
  sqrt(p_t V_t). Prefer the t-statistics of regression lambdas as features (Lopez de Prado, 2018). Do not count workup
  matches as separate trades.
- **Round-trip cost from the opposite-side trade (RFQ markets)**: cost = p - p_prev_opposite when the client buys,
  p_prev_opposite - p when selling, where p_prev_opposite is the latest trade on the same contract on the other side.
  10-25% of measured values are negative (noise): average, do not read single prints (Riggs, Onur, Reiffen and Zhu,
  Journal of Financial Economics 137, 2020).
- **Bid-ask bounce** inflates measured volatility of illiquid prices, pushes variance ratios above 1 and can make a
  random walk look stationary: clean or mid-mark before running mean-reversion tests (Hasbrouck, 2004; Duering, 2021).

## C. Impact models (need a book or signed flow)

- **Square-root law**: price move / volatility proportional to (Q/V)^g with g about 0.5. Total cost of an order then
  grows as size^1.5. For 10y USTs, log-log fits gave slopes 0.56-0.57 (NY), 0.56-0.61 (London), 0.61-0.62 (Tokyo) for
  $50-200mn buckets; slope below 1 means "burnout", the linear Kyle model is rejected (J.P. Morgan, Drivers of price
  impact and the role of hidden liquidity, 13 Jan 2017). The same note: FOMC-day slope 0.83 (morning 1.08) vs 0.58 on
  all days, and about 1 in 5 buckets move against the imbalance (impact is a statistical bias, not a law).
  Grinold-Kahn rule of thumb: it costs roughly one day's volatility to trade one day's volume; cost per unit
  proportional to sigma x sqrt(V_trade / V_daily) (Active Portfolio Management, 2nd ed., 1999). Almgren et al. fit an
  exponent beta about 0.6 for temporary impact (Paleologo, The Elements of Quantitative Investing, 2025).
- **Swap-book add-on** (Darbyshire, 2022, Ch.19.4): impact_i (bp) = a x sqrt(|x_i|) with x in DV01 (alpha default
  1/1000: 1bp for 1mm); average incremental cost (2/3) a sqrt(|x|); total (2/3) a |x|^1.5. Inventory aware: add-on for
  a new request D given inventory I is (2/3) a (|I + D|^1.5 - |I|^1.5), negative when the trade reduces inventory;
  floor negative add-ons (liquidity can vanish before the next trade). Numbers: 100,000 DV01 from flat: 21,081
  (0.21bp); 50k then another 50k: 7,454 then 13,628; the average of the two quotes equals the single full-size price,
  which is why splitting a block does not save cost against an inventory-aware dealer. Implemented in
  `scripts/costs.py` (`impact_addon_ccy`, `quote_cost_ccy`).
- **Imbalance-bucket logit** (J.P. Morgan, 2017): bucket aggressor trades into fixed notional (about $100mn for 10y),
  v = |V_bid - V_ask| / (V_bid + V_ask), sign-correct dP so a bid-dominated bucket counts a rise as positive; classify
  outcome on a half-tick grid (drop, flat, +1 half-tick, jump) and fit a multinomial logit on v. Price impact = expected
  move at v = 0.5 on a rolling 5-day window; jump risk = P(jump) at v = 0.5.
- **Hasbrouck structural VAR** (FRBNY SR 381): variables r_t (mid change per transaction) and signed volume; 5 lags,
  permanent impact = cumulative impulse response truncated at 50 transactions, bootstrap bands. Add net limit-order
  flow at the inside or the trade-only model overstates impact by 20-50%. Post-FOMC (60 minutes) impact rises 24-134%.
- **Slow vs fast flow mix** (J.P. Morgan, Fast and furious, 20 Nov 2018): aggregate impact = f x impact_fast + (1 - f) x
  impact_slow, f = share of $5mn flows completed in under 0.05s. Rule of thumb from the note: +10 points of fast
  share goes with about -10bp annualised realised vol; a 3Mx10Y implied shock of 50bp maps to fast fraction 34% and a
  28% rise in impact. Overstates amplification if fast flow is mostly hot-potato trading between fast firms.

## D. Regime and liquidity monitors

Build each as a rolling z-score (1y or 2y, sign-aligned so higher = less liquid) and monitor the set together.
Pay as much attention to divergences as to commonalities (Duering, 2021): in 2015-16 quoted b/o looked fine while
curve dispersion rose.

| Monitor | Definition | Reading | Source |
|---|---|---|---|
| Depth | total size at the best three levels, averaged over bid and ask, sampled every $100-500mn traded (volume-weighted), or the average over 08:30-10:30 NY | 2y z-score; fell to about 3 sigma below average in Aug 2019 as 3M expiry vol rose about 25bp | J.P. Morgan, For cheap gamma, look to the long end, 23 Aug 2019 |
| Price impact | expected mid move per $100mn of net aggressor flow, sign-corrected (logit above) | inverted z for combining with depth | J.P. Morgan, 2017; The return of convexity hedging, 31 Jan 2020 |
| Fast-participant share of depth | depth from participants reacting in under 300 microseconds (electronic 0.3-300 ms, human slower). Cutoffs arbitrary | share rose from about 20% to about 80% of 10y depth 2011-19 while human plus electronic depth stayed near $60mn. Falls ahead of slower participants by 5-25 minutes in stress; into 8:30 payrolls falls from about 80% to about 50% | J.P. Morgan, Far from the shallow now?, 12 Apr 2019; Flash Rally, 5 Mar 2020 |
| Event depth | recovery time = minutes after 08:30 until depth regains its 08:00-08:15 average; drawdown = % fall from the 30-15 minute pre-release average to the minimum; bedrock = the minimum | payrolls: depth below a quarter of base into the release; recovery lengthened from 1-2 minutes to 15-30 (1h+ on worst days) | J.P. Morgan, When the going gets tough, the tough get going, 5 Nov 2019 |
| Intraday / close-to-close realised vol | 10-day close-to-close vs 30-minute-snapshot intraday vol, 7am-5pm NY (USD) or London (EUR) | ratio intraday/close well above 1 = whipsawing illiquid market; the inverse ratio fell to 0.5-0.6 in Mar 2020 and normalised after | Citi Research, Liquidity, vega, and convexity, 30 Mar 2020 |
| Curve dispersion, RMSE form | RMSE of yields vs a fitted par curve, 1-month moving average | about 1-3.5bp in 2010-16, crisis peak about 16bp. Driven by dealer inventory (each -$100bn adds about 0.3bp), depth and GCF/OIS spread | J.P. Morgan, Times like these, 10 Feb 2016 |
| Curve dispersion, spline form | Nelson-Siegel spline fit to the govt curve; spreads of the 7-15y bonds re-centred to zero mean each day; mean absolute deviation in bp | about 1-2bp normal; UST/Bund/JGB about 1bp in Jan 2020, 4-7bp in Mar 2020 (read from a chart). Different definition from the RMSE form: do not mix thresholds | Duering, 2021 |
| On-the-run premium | spline spread of the on-the-run 10y | price paid for liquidity; differs from dispersion (unexploited arbitrage); contains specialness | Duering, 2021 |
| Effective vs optical | share of $100mn gross flow executed wider than 0.5 tick, NY session | jumped to about two-thirds on 9 Mar 2020 with normal-looking depth: measure fills against the tick, not only depth | J.P. Morgan, When market risk meets operational risk, 10 Mar 2020 |
| Composite index | simple average of six 5-year z-scores, higher = less liquid: price impact for fixed imbalance, depth (inverted), fast-share (inverted), 1Mx10Y / 1Yx10Y ATMF vol slope, futures richness (inverted; CTD yield error vs par curve, basis adjusted), overnight GC minus EFFR | 2.44 on 31 Mar 2020, 5.32 at the 13 Mar 2020 peak, 0.95 a month earlier, 0.05 two months earlier | J.P. Morgan, Are we there yet?, 1 Apr 2020 |
| Futures vs cash gap | futures can trade rich vs cash in stress (liquidity tiering); swaps lag market moves, so swap-spread directionality turns negative | adjust CTD yield error for the basis before reading richness | J.P. Morgan, 10 Mar 2020; 1 Apr 2020 |

Calendar structure to model rather than average away: depth thins into 08:30 releases, auctions and FOMC; worst in
Tokyo hours, then London, best in NY; year-end holidays are a seasonal low (J.P. Morgan notes above); EUR swap
volume peaks around 16:00-16:15 CET; depth rises into September (about 5bp lower 3Mx10Y implied on average in 7 of 9
years to 2018, J.P. Morgan, 23 Aug 2019). Prolonged low vol leads banks to disinvest from market making, so the next
vol shock meets thin balance sheets (Duering, 2021).

## E. Flow toxicity and adverse selection

- **PIN / VPIN**: PIN = a x mu / (a x mu + 2 e). On volume bars of size V, VPIN = a x mu / V, estimated as
  E[|2 v_B - 1|] with v_B the buy share of each bar. A persistent imbalance is necessary but not sufficient: it must
  also be unpredictable to market makers. Interest-rate futures show among the lowest VPIN false-positive rates
  (Lopez de Prado, 2018). Tick rule: b_t = b_{t-1} if the price is unchanged, else sign of the price change.
- **Imbalance and runs bars**: bar closes when |sum b_t v_t| exceeds its EWMA expectation; bars form faster when flow
  is one-sided. Runs bars detect sweeping and sliced parent orders. Tick bars are distorted by auction prints.
- **Order-flow imbalance (OFI)** from book changes (including cancels) differs from signed trades on the tape.
  Multi-level OFI is highly collinear across levels: fit it with ridge regression and cross-validation, not OLS.
  The sign and size of its link to the mid change depend on the sampling horizon, so fix the horizon before comparing.
  Iceberg size is right-censored by cancels (use a survival estimator).
- **Fill as information**: conditional on being filled, ask whether the expected value is still attractive; an easy
  fill on a hard-to-value package should prompt re-underwriting (Jane Street, Probability and Markets primer).
  Price-insensitive counterparties are benign, value-motivated peers are dangerous. Dealer matched-book economics:
  earn the inside spread from uninformed flow, lose the outside spread to informed flow (Conks, The Rise of the Secured
  Standard, 25 Aug 2023).
- **Toxic flow defence for a dealer**: mean-revert prices that deviated from recent history; especially effective on
  hedge-fund RV requests in GBP and EUR (Darbyshire, 2022). Implication for the client: repeated requests from one
  firm across several venues raise the informational value of its flow and widen quotes.
