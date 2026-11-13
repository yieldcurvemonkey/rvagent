---
name: vol-gamma-vega-pnl
description: 'Explains, sizes and manages the P&L of delta-hedged rates options and convex linear packages in the normal (bp) model - gamma vs vega vs theta, implied vs delivered/realised vol, walk vol, break-even vol and move, delta-hedge policy (frequency, threshold, time of day, hedge vol, bid/offer), gamma maintenance, vanna/volga drift, gamma vs vega sector, and convexity of delta-hedged forward flatteners or futures-vs-swap (gamma decay). Bundles a normal-model greeks / daily P&L explain / hedge simulator. Use when asked: is straddle or swaption gamma rich or cheap, short gamma or short vega, implied vs realised, theta bleed, break-even, how often or when to delta hedge, 1m10y 3m10y 1y10y straddle, gamma scalping, why did a hedged option lose while vol fell, gamma sector vs vega sector, gamma upkeep of a hedged forward flattener, convexity adjustment as short gamma. Valuing convexity and breakeven vol of forward flatteners: vol-convexity-and-long-end.'
---

# Gamma, vega and theta P&L of rates options and convex packages

A delta-hedged option is a bet on realised variance against the implied variance paid at entry. The premium buys
"the right to be on the profitable side of delta hedging" (Huggins and Schaller, Fixed Income Relative Value Analysis,
2nd ed., 2024): P&L is zero when realised equals implied, positive when realised is higher for a long option, and
depends on the path, not the final level. Over a short horizon or a short expiry the P&L is gamma (realised vol). Over a
long expiry it is vega (changes in implied vol). Linear packages (swaps, flatteners, futures-vs-swap) have the same
gamma with carry and roll standing in for theta. This skill gives the decomposition, the break-even arithmetic, the
hedging policy and the maintenance rules, so a vol view can be turned into the right instrument and the right P&L expectation.

## When to use
- "Is 1m10y / 3m10y / 1y10y gamma rich or cheap?" Implied vs delivered or walk vol; what do I earn or lose per day.
- "Why did my short straddle lose although implied vol fell?" / "Why did my long vega not make money?" P&L explain.
- Choosing between a gamma trade (short expiry, delta-hedged) and a vega trade (long expiry, unhedged or lightly hedged).
- Hedge rules: daily, threshold, time of day, which vol to hedge at, effect of bid/offer, event days, expiry week.
- Sizing a calendar or a gamma-neutral / vega-neutral package; keeping it neutral as the market moves (maintenance).
- Convexity on linear books: delta-hedged forward flatteners (15y5y/20y10y), futures-vs-swap, convexity adjustment as short vol.
- Not for: surface/grid RV and listed-vs-OTC vol ([vol-rates-options-rv](../vol-rates-options-rv/SKILL.md)); skew and tail
  structures ([vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md)); correlation and curve options
  ([vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md)); long-end convexity value and
  MBS flows ([vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md)).

## Conventions (state them in every answer)
| Item | Convention |
|---|---|
| Vol | normal (Bachelier) vol, bp per year. Daily bp vol = annual / sqrt(252): 110bp = 6.93bp/day |
| Option value | bp of annuity. Cash = value_bp x pv01, pv01 = annuity x notional x 1e-4 (ccy per bp). ATM value = sigma sqrt(T/(2 pi)) |
| Payer / receiver | payer = call on the rate, receiver = put on the rate. Straddle = payer + receiver, same strike (ATMF: delta about 0) |
| Signs, long option | +gamma, +vega, -theta. A long payer is short duration: DV01 = -delta x pv01 (BofA: 100m 1y10y ATM payer DV01 -36,451 on pv01 about 77.8k). Hedge it by receiving fixed |
| Cash greeks | gamma = d(delta)/d(rate) = d2P/dr2, ccy per bp^2, positive for every long option (in DV01 terms a long option's DV01 FALLS by gamma per +1bp: a long payer's DV01 gets more negative as rates rise); vega = ccy per +1bp of normal vol; theta = ccy per day. Say which day basis |
| Time | variance clock: business days / 252. Desk theta is often per CALENDAR day (/365): 3m10y theta 9,104 in the cited primer equals 9,037 per calendar day or 13,089 per trading day on the same gamma. Weekend decay is real: Friday close to Monday close is three calendar days but one trading day of variance |
| Lognormal | normal vol is about F x lognormal vol for short expiry (110bp normal = about 30% on a 3.7% forward). Normal vol can move only because forwards moved, giving spurious directionality in signals built on lognormal vol (BofA, US Vol Primer, 11 Mar 2024). Use normal vol throughout |
| Sectors | expiry up to 1y = "gamma sector" (driven by realised vol), over 1y (certainly 3y+) = "vega sector" (driven by implied vol) |

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| ATM and strike normal vols by expiry x tail | `vol_surface` | daily, one `snap` only; at least 1y (3y for z-scores) | Interpolate to the remaining expiry of the specific option for a P&L explain |
| Listed STIR / bond-future option vols and prices | `opt_quotes`, `opt_static` | daily settle; bid/ask for cost | STIR option nvol in bp = futures-price vol in points x 100 |
| Forward rate of the underlying (ATMF) | `curve_par`, `curve_zero` | same snap as the vol, daily; intraday `snap` for hedge-time studies | Delivered vol needs the forward of the SAME underlying, not a spot swap |
| Annuity / pv01 of the underlying, day-count, calendar | `swap_conventions`, `calendars`, `curve_zero` | per option | Needed to convert bp to cash and expiry date to business-day T |
| Futures price for futures-vs-swap convexity | `fut_quotes`, `stir_quotes` | daily | |
| Positions, trades, costs, realised P&L | `positions`, `trades`, `pnl` | daily | `slippage_bp` gives the hedge cost per unit |

If an input is missing, ask the user or hand off to the data adapter ([data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)).
Never invent vols, bid/offers or notionals. Never mix snaps in one series (a 3pm vol against a close forward misstates delivered vol).

## Method

### 1. Normal-model greeks
With d = (F - K)/(sigma sqrt T), phi the standard normal density, Phi its cdf, w = +1 payer, -1 receiver:
- value = w(F-K) Phi(w d) + sigma sqrt(T) phi(d);  delta = w Phi(w d);  gamma = phi(d) / (sigma sqrt T) per bp;  vega = sqrt(T) phi(d) per bp of vol.
- theta = -1/2 sigma^2 gamma per year (exact in the normal model). Hence **vega = sigma T gamma**: vega is the time-integral of gamma, gamma is "realised vol", vega is the "gamma reserve" (Quantitative Finance Stack Exchange, Option: link between Vega and Gamma, 2024).
- ATM: delta 50%; gamma and theta are highest ATM and at short expiry; vega rises with expiry and with tail length (vega falls as expiry nears). Gamma also rises when implied vol falls: low vol means more gamma, hence the "accelerant" of convexity-hedging flows in a shock (Convexity Maven, It's Never Different This Time, 29 Jan 2018).
- Cash: gamma_cash = gamma x pv01, vega_cash = vega x pv01, theta_cash/day = theta x pv01 / 252 (trading) or / 365 (calendar).
- Reconcile any desk number to the analytic one before using it: ATM vega is about 0.399 sqrt(T) pv01. A textbook's printed $ vega and theta for a 1y10y payer were about 100x too small against this check (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, Ch.20). Run `scripts/gamma_pnl.py greeks`.

### 2. One-day P&L of a delta-hedged long option
```
P&L = theta dt + 1/2 gamma dF^2 + vega d(sigma) + vanna dF d(sigma) + 1/2 vomma d(sigma)^2 + higher order
gamma + theta part = 1/2 gamma [dF^2 - sigma_i^2 dt] = |theta| dt (n^2 - 1),   n = dF / (sigma_i sqrt(dt)),  theta per year
```
Break-even daily move for a hedged option is therefore |dF| = sigma_i / sqrt(252): P&L is zero at one implied standard
deviation, quadratic in the move (half the move earns a quarter). The sign flips for a short option.
- Over the option's life, hedged at implied: dPi = 1/2 (sigma_r^2 - sigma_i^2) Gamma dt (normal model; the lognormal source form carries S^2), an "ex-ante average"; the true
  increment is 1/2 Gamma ((dF)^2 - sigma_i^2 dt). The total is path-dependent: larger when the forward oscillates around the strike
  where gamma is high (QSE, Continuous delta hedge formula, 2017; Delta hedge value formula, 2017).
- Attribute with realised squared moves per period, not an averaged sigma_r^2; daily attribution is noisy, weekly or per hedge interval is cleaner.
- Expected value at the strike, driftless, continuous hedge at implied: **E[P&L] = value(sigma_r) - value(sigma_i) = vega x (sigma_r - sigma_i) = (sigma_r - sigma_i) sqrt(T/(2 pi))**, independent of hedge frequency (every hedge trade has zero expected value); frequency changes only the dispersion before costs (replication error falls as 1/sqrt(n hedges)). Verified by Monte Carlo in the script's selftest.

### 3. Gamma P&L or vega P&L: pick by horizon
- Held to expiry: P&L is about vega_0 x (RV - IV_0) at the strike. Entry implied is what you bought.
- Sold or re-marked before expiry: P&L = realised gamma-minus-theta over the holding period + vega x change in implied. For
  expiries well beyond the horizon, delta hedging barely matters and the trade is a view on implied vol (vega sector);
  large underlying moves over long horizons can still break the "no delta hedge" premise, and theta differences between
  legs matter on long holds (Huggins and Schaller, FI RV Analysis, 2024, Ch.19).
- A short-gamma position can lose while implieds fall: P&L is delivered vol against implied at entry. Dec 2017: delivered
  vol jumped by more than long-end implieds fell (J.P. Morgan, Update on systematic rule based trading strategies, 8 Jan 2018).
- Gamma-vega equivalence is local: ATMF, small vol gap. Away from ATM or for big gaps vega depends non-linearly on sigma
  and the two P&Ls diverge (QSE, Option: link between Vega and Gamma, 2024; QSE, Realizing the same PnL as Gamma Vs Vega, 2022).
- Isolating one: long gamma with flat vega = buy a short-dated option vs sell a longer one, vega-weighted: net long gamma and
  net short theta (the short-dated leg decays faster per unit vega); an equal-notional version is also short vega (the BofA
  3m10y-vs-1y10y calendar: short delta, long gamma, short vega, short theta; the short-gamma side collects the carry). Long
  vega with flat gamma = buy the long-dated option, sell short-dated gamma-weighted (collects theta). Use vega-weighted ratios
  where the aim is pure gamma (BofA: 195m 3m10y straddles vs 100m 1y10y). Vanilla
  calendars are not forward vol because their gamma profiles differ (details in
  [second-order-greeks-and-maintenance](references/second-order-greeks-and-maintenance.md)).

### 4. Break-evens
- Hedged: |dF_BE| = sqrt(2 theta dt / gamma) = sigma_i sqrt(dt) between re-hedges; compare with the realised move per
  hedge interval, not the sum of intraday increments. Hedging more often over small moves needs a larger total path length to break even.
- Unhedged ATM straddle held to expiry: premium = 2 sigma sqrt(T/(2 pi)) must be covered by |F_T - K| (the BofA 1y10y ATM payer
  alone breaks even at 44.1bp of move). Average daily absolute move needed: sqrt(2/pi) x sigma/sqrt(252) = 0.80 x daily vol (Darbyshire, 2022, Ch.20).
- Compare **carry or roll against theta at matched gamma and horizon, never against premium**: a gamma-matched ATM
  straddle's premium is twice its horizon theta (ATM gamma grows as 1/sqrt(tau)), so premium-based breakevens are sqrt(2) too high ([convex-linear-packages](references/convex-linear-packages.md)).

### 5. Measure realised vol the way the hedge experiences it
1. Delivered vol (default): root-mean-square (zero-mean) of daily changes of the underlying forward (same snap, bp) x sqrt(252), over 21 business days (1m) and 63 (3m). BofA use the plain standard deviation; the two differ only in a strong trend, and gamma P&L follows dF^2, so zero-mean is the hedger's number. Pair with the implied vol of the matching expiry and tail; for a fixed option use its own forward. `scripts/gamma_pnl.py realized`.
2. Ratios and z-scores: implied / 1m delivered and implied / 3m delivered, each with a 1y z-score. Cross-check with a second measure: intraday-sampled realised (30-minute snapshots 7am-4pm local; NY for USD, London for EUR) and the intraday / close-to-close ratio (above 1 = whipsawing, illiquid; below 1 = trending). A normalising ratio signals returning liquidity (Citi, Liquidity, vega, and convexity, 30 Mar 2020).
3. **Walk vol** for expiries beyond a month: a held 1y10y becomes a 9m10y, 6m10y, ... option, so benchmark against the time-weighted delivered vol (same window, e.g. 3m) of the same underlying at each intermediate expiry from spot to the option's expiry: walk vol = sqrt(sum_i w_i sigma_i^2), sigma_i = delivered vol of the forward at expiry point i, w_i = time weights (half the gap to each neighbour / horizon, sum 1). Implied / walk vol is a fairer gauge than implied / plain delivered (BofA); when delivered vol rises with expiry, walk < plain delivered and implied / walk is the higher ratio.
4. Event days: put the whole event premium on one day and run the other days at base daily vol. Forward vol between adjacent expiries f < t is sqrt([t sigma_t^2 - f sigma_f^2]/(t - f)); subtract the base-day variance of the window to leave the event-day variance.
5. Realised vs implied as a forecast: expect implied above realised on average. 3y10y implied / 6m realised long-run average about 107% was called "risk-adjusted fair value" (Merrill Lynch, RateLab: Professional Javelin Catching, 16 Feb 2007), so 1.0 is not the fair ratio and a ratio of 1.05-1.10 is not a signal by itself.

### 6. Delta-hedge policy (defaults, with reasons)
1. **Hedge vol**: delta from the current market implied vol (that is what the book is marked to). Expected P&L is almost independent of the hedge vol; the distribution is not (a higher hedge vol pre-books vega P&L and pays more theta; a lower one keeps gamma for late large moves). Hedge at your own anticipated vol only as a deliberate, simulated choice, and never mix marks inside one book (portfolio delta becomes wrong).
2. **Frequency / threshold**: set by bid/offer. Rule: simulate `gamma_pnl.py sim` with the actual half-spread and trade size. Evidence (USD, 1997-2017, sell 1m10y straddle): daily-hedged Sharpe 0.48, 25%-delta-threshold 0.84, unhedged 0.43; threshold optimum 3-7% of delta at 0.5bp swap bid/offer, daily at 0.3bp (Citi, The art of gamma hedging, 12 Mar 2018). Threshold is in delta units (fraction of option notional; `sim --thresholds 0.15` = 15%). Default when no costs are known: hedge once a day at a fixed liquid time; one live desk rule was to hedge only when delta had moved more than 15% since the last hedge (Citi, Gamma and Vega RV, 14 Jan 2019), a practice not a backtested optimum, since at 0.3bp costs daily hedging was best. Delta-hedged flatteners: every 20-25bp in the longer forward, plateau 15-30bp.
3. **Time of day**: hedge short gamma at the hour of lowest realised vol between hedges (peak liquidity); long gamma prefers the opposite. The answer changed by period (USD 10y: 9am, noon-1pm, 10am-12pm, 7am at different dates), so re-measure over the last 3m, 6m and 1y and do not hard-code ([hedging-policy-evidence](references/hedging-policy-evidence.md)).
4. **Expiry and events**: ATM gamma explodes near expiry and cash-settled risk is replaced at expiry. Expect to widen the hedge tolerance and size down into expiry week and event days; check whether the event premium is already priced (event-day vol).
5. **Costs**: P&L net = gross - half-spread x total delta traded. Gamma-scalping income per hedge is 1/2 gamma dF^2; the hedge is worth doing only when it exceeds the cost, which is what the threshold encodes.

### 7. Maintenance of option books and packages
- Greeks drift: gamma becomes delta drift after a rate move, vomma becomes vega drift after a vol move, vanna becomes vega drift after a rate move. Re-flatten with the swap (delta) or the ATM straddle (vega). Skew-package example: resize when |net vega drift| exceeds 5 abpvs or the net rate move exceeds 5bp; re-strike wings when one drifts more than 5bp from target; roll to ATMF for larger drifts (Ade Rhodes, Trade Idea: USD 3m2y Payer Skew Steepener, 8 Oct 2025).
- Compute greeks of every package by bump-and-reprice on the full curve and surface, not from bucketed linear risk; hedge across many curve moves, not just those a one-factor model allows (Hull, Options, Futures, and Other Derivatives, 9th ed., Ch.31). Hedging with a different product type fixes delta but leaves gamma: read the cross-gamma grid or run scenarios.
- Package greeks depend on the model: in a Bachelier model a spread's delta and gamma depend on leg correlation. Check lot size, greeks and notional agree.

### 8. Linear products (swaps, futures-vs-swap, forward flatteners)
- Value of gamma: E[P&L] = 1/2 x gamma_cash x (sigma sqrt T)^2. Model gamma decay: the constant-gamma figure overstates (9.6bp vs about 6bp in the SOFR example below). Script: `convexity_value(gamma, sigma, T, gamma_end)`.
- Receive fixed + short futures = long convexity; pay fixed + long futures = short convexity; swap rate < futures-implied rate by the convexity adjustment.
- Delta-hedged forward flattener (receive longer forward, DV01-neutral, resize at each 20-25bp move): daily breakeven (the parallel move whose convexity gain offsets negative daily carry; 0 if carry is positive) divided by 1y realised daily vol of the longer forward = BE/RV. BE/RV below about 0.8 = cheap convexity (flattener), above about 1.2 = rich (steepener; short convexity, positive carry). Full mechanics, screens and package math in [convex-linear-packages](references/convex-linear-packages.md).

## Worked examples
**1. Greeks of a 100m 1y10y ATM payer and a 3m10y (BofA, US Vol Primer, 11 Mar 2024, levels 23 Feb 2024).** Forward 3.727%, pv01 about 77.8k, 110bp vol, premium $3.432m = 44.1bp. Script check: value 110 x sqrt(1/(2 pi)) = 43.9bp ($3.414m), daily vol 6.93bp (matches), vega 0.399 x 77.8k = $31.0k per bp (primer 31,203), DV01 -38.9k (primer -36,451), gamma $282 (primer 230), theta $4,677 per calendar day (primer 4,107): the 1y10y delta, gamma and theta differ from the primer by 7-23% (cause not shown in the source) while premium and vega match to under 1%; trust the analytic numbers and flag the gap. 3m10y at 106bp (strike 3.830%, pv01 about 78k): premium $1.65m (primer 1.68m), gamma $587 (primer 559), theta $9,037 per calendar day (primer 9,104): within 5%.

**2. What does a day pay? 3m10y, 106bp implied (illustrative, using the primer's gamma 559 and trading-day clock).** Implied daily vol 106/sqrt(252) = 6.68bp, cash gamma 559 per bp^2. P&L per day = 1/2 x 559 x (dF^2 - 44.6). A 5bp day: -$5.5k; 6.68bp: zero; 8bp: +$5.4k; 10bp: +$15.5k. Theta bleed of about $12.5k per trading day (about $8.6k per calendar day) is what a long holder must beat; the unhedged straddle breaks even on a mean absolute move of 5.3bp/day over the life.

**3. Walk vol 1y1y, 3m delivered (BofA primer).** 3m delivered vol of the 1y forward at each expiry point, with time weights: spot 87.5 (0.0417), 1m1y 101.8 (0.0833), 2m1y 113.8 (0.0833), 3m1y 122.8 (0.1667), 6m1y 141.5 (0.25), 9m1y 143.8 (0.25), 1y1y 142.8 (0.125). walk vol = sqrt(sum w sigma^2) = sqrt(17,501) = 132.3bp against the plain 142.8 delivered: the benchmark is 7% lower, so implied / walk is 8% higher than implied / plain (142.8/132.3 = 1.08). Implied / 21d delivered was at or below 100% across the grid (1m1y 100%, 1y10y 90%), 3m z-scores -0.2 to -1.3: no short-gamma signal.

**4. Hedging policy backtest (Citi, The art of gamma hedging, 12 Mar 2018).** Selling 1m10y straddles daily, 1997-2017: daily hedge Sharpe 0.48; 25% threshold 0.84 (1.41bp/day, yearly hit 0.81); unhedged 0.43; 3m10y 0.71 (threshold); 1m30y 0.40; 3m2y -0.59 daily / -0.45 threshold. The 10y tail is the liquid pivot; short tails lose to hawkish regime shifts. Threshold only won because 2y/5y/10y swap bid/offer was wide for most of the sample (0.3-2.0bp by sub-period, 1.2-2.0bp before 2005); at 0.3bp (Mar 2018) daily was best.

**5. Gamma decay on a futures-vs-swap convexity (Quantitative Finance Stack Exchange, Why are FRA/futures convexity adjustments necessary, 27 Jul 2023).** Receive Jun-25 IMM to Sep-25 SOFR swap (notional 1.134bn, delta $25k/bp) vs 1,000 short Jun-25 3m SOFR futures; gamma $12.2 per bp; normal vol 139.38bp from the 96.375 call at 0.75. Constant gamma: 1/2 (140 sqrt2)^2 x 12.2 = $240k = 9.6bp. With gamma falling to about 7 after a year: about $150k = 6bp. The script's linear-decay value ($136k) lands in the same range. Check on the CME table: receive $100mm 2y swap vs 779 3m SOFR futures, -100bp earns $22,292 against the linear 1/2 x 18 x 100 x 25 = $22,500 (CME, Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures, 4 Jun 2025).

**6. Delta-hedged flattener lifecycle (Citi, Taking profits on delta-hedged 15y5y/20y10y flatteners, 5 Dec 2019).** Screen: carry -0.31bp/yr, daily breakeven 1.3bp vs 1y realised 3.0bp: BE/RV 0.42. Entered 9 May at -11.8bp, $50K DV01, hedged every 20bp. Closed 5 Dec at -12.5bp: about +$187K mid, attributed to realised vol (the curve itself was only 0.7bp flatter) and +$155K net of costs, with carry at -2bp/yr and BE/RV 0.8, the exit trigger.

## Signals & interpretation
| Observation | Reading / action |
|---|---|
| Implied / delivered (1m or 3m) above about 1.25 and 1y z-score above 1 | Gamma rich; candidate short gamma, but only with filters below. EUR 3Mx10Y rule: short above 125%, long below 66% (alone IR 0.8) |
| Same ratio about 1.0-1.1 | Fair: implied normally carries a premium (107% for 3y10y vs 6m realised). No trade |
| Implied / walk vol vs implied / delivered | Walk is the fairer gauge beyond 1m. When delivered vol slopes up with expiry, plain delivered UNDERSTATES richness (walk < plain, ratio about 8% higher in the BofA 1y1y case); for a short, require both ratios to be rich |
| Implied / realised rich on short tails but jump-prone (1M1Y 1.38, 1M2Y 1.39; 1M30Y 1.06 USD Aug 2026) | Not a sell on the left side; right side (5y-30y tails) is the better place to own gamma |
| Fading 1y z-score extremes of implied alone | Negative long-run IR (-0.3): needs momentum, carry or macro filters (combined EUR rule IR 2.45) |
| Excess-kurtosis significance above 1.3 (-log10 p, 1m daily moves) | Favour selling vega (3Mx10Y held a month) over selling gamma held to expiry |
| Realised just spiked | Do not sell vol right after the spike if more realised is expected; scale down short gamma as the edge shrinks (halved at about 3 normals rich) |
| Policy-easing cycle onset / zero lower bound | Do not sell gamma; sell vega in longer expiries (2y2y) until realised settles and bid/offer normalises |
| Inverted vol term structure (1m10y above 1y10y) | Gamma looks rich but stress periods are poor times to harvest it; inversions usually fade quickly |
| Intraday / close-to-close ratio above 1 | Whipsaw, thin liquidity: infrequent hedging benefits shorts; below 1: trending, hedge more |
| Carry-to-premium about 3:1 on a long option | Buy the option (long gamma with positive carry); personal rule, not backtested (BofAML, Paying Nickels for Dimes, 21 Jan 2010) |
| BE/RV below 0.8 (flattener) / above 1.2 (steepener) | Cheap / rich convexity, subject to carry sign, liquidity and trend filters |

Confirm before sizing: edge persists on both implied/realised and implied/walk; hedge cost does not erase the expected
P&L (use `sim` at the actual spread); the P&L explain of the last 20 days is dominated by the intended Greek.

## Pitfalls
- Wrong clock: theta quoted per calendar day vs gamma on a trading-day variance clock; weekends and holidays. Be explicit, and for short expiries the business-vs-calendar choice moves T by about 12% (31 calendar days across Easter: 0.0849y vs 0.0754y).
- Unit slips: normal vs lognormal; bp vs %; cash vs bp of annuity; vega per 1bp vs per 1 vol point (100x); a vendor field "theta" that includes carry/roll.
- Comparing carry with premium (sqrt(2) error above) and treating the straddle's "premium recovery" as theta.
- Skew and smile: short straddle losses after big moves are larger than 1/2 gamma sigma^2 suggests; vanna and volga sit in the residual. A skew-blind model understates short-gamma risk.
- Selling gamma into jumps: central-bank rhetoric shifts (hawkish ECB, June 2017) and policy repricing (BoE MPC) erode theta gains; short-dated left-side vols are prone. A high hit rate from selling OTM options is not evidence of richness ("you can expect to make money most of the time"; Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005).
- Overlapping observations: a 63-day delivered-vol ratio sampled daily has about 4 independent points per year, so its 1y z-score is a weak statistic, and the backtest Sharpes above come from roughly 21 (1m) or 63 (3m) overlapping options a day. Treat t-stats and hit rates as optimistic; use non-overlapping or block-bootstrap inference.
- Short gamma needs a floor under implieds as well as realised below implied: if implieds are unlikely to fall, all the P&L must come from realised, and jump risk erodes theta (J.P. Morgan, Global Fixed Income Markets Weekly, Aug 2026). Long-gamma dealer delta hedging (receive sell-offs, pay rallies) pins the underlying and reinforces ranges until a gap (BofA, US Vol Primer, 2024).
- Hedge-time mis-measurement: close-to-close realised can be inflated by algos at the close; and a short-hedge-interval realised understates what a daily hedger gets. Use the interval you will trade.
- Delta-hedge at a fixed vol hides MTM from risk; delta of a position with a stale vol is wrong.
- Constant-gamma convexity estimates overstate by about 60% (9.6 vs 6bp); futures-vs-swap convexity grows non-linearly and assumes parallel moves.
- Cheap can stay cheap: callable vega supply, VA/insurer receiving in 15-25y, ELB convergence. Do not buy on z-score alone; delta-hedged flatteners pick up directionality from those flows (stocks vs 15y5y/20y10y about -23%).
- Long-expiry straddle evidence (EUR 10y10y, 2005-2021, no premium for being short long-expiry convexity) does not carry to short expiries; source is marketing material (Nordea, Bonds and bold, 5 Nov 2021).
- Pre-Aug-2021 SOFR realised vol overstates the future (SRF cap); estimate on post-SRF data. In-period SOFR futures lose vol as fixings arrive, which offsets expiry gamma (intuition only).
- Options on bond futures expire about a month before the futures' last trading day: the delivery option can carry more vega than the hedge option; CTD switches break a constant-vol delta.
- Liquidity feedback: more fast-flow (HFT) share is "bearish for gamma"; +10% fast share about -10bp realised vol (UST 10y 2018), overstated if flow is hot-potato (J.P. Morgan, Fast and furious, 20 Nov 2018).

## G10 market differences
- USD: hedge-time results vary by year; ZLB onset 2020.
- EUR: negative-rate period requires normal or shifted vols; 10y hedge-time about 7-8am London or 1pm depending on period.
- GBP: 20y driven by ALM receiving; long flatteners can show positive carry (free convexity, BE 0).
- JPY: realised vol only 2.4-3.1bp/day vs 3.9-4.7 elsewhere; vega-sector border tilts right; YCC (2016) collapsed 1y2y/1y10y vols; delta-hedged 10y10y/20y10y trades are executed almost daily.
- CAD: long-dated flattener convexity is expensive (BE/RV up to 2.0).
- AUD, NZD, CHF, SEK, NOK: the source material has no gamma/vega studies; apply the same formulas, but expect wider bid/offer and thin option markets, so re-derive the hedge threshold from observed costs and ask the user for vol data before quoting any level.

## Output
1. **Header**: ccy, instrument (expiry x tail, strike offset), snap, normal vol, pv01, convention (day basis, units).
2. **Greeks table** (bp and cash): value, delta/DV01, gamma, vega, theta per trading and per calendar day, break-even daily move.
3. **Vol comparison**: implied, 1m and 3m delivered, walk vol, intraday/close-to-close ratio, each ratio with 1y z-score and a verdict (rich / fair / cheap) with the threshold used.
4. **P&L expectation** per day and to horizon under: realised = delivered, +/- 20% realised, and implied +/- 3 normals; split into gamma, vega, theta, costs.
5. **Hedge plan**: hedge vol, trigger (threshold or fixed time), time of day tested, half-spread assumed, simulated net mean/std (from `sim`).
6. **Realised P&L explain** if positions exist: columns gamma, vega, theta, residual (vanna/volga), costs; tie out to `pnl` within the residual and report the residual share.
7. Caveats: skew/jump exposure, liquidity, data gaps. Hand the trade to rv-trade-idea-writeup with the entry, breakeven, stop and exit rules (BE/RV drift, vol move).

## Scripts
- [`scripts/gamma_pnl.py`](scripts/gamma_pnl.py): normal-model greeks (`greeks`), one-day and series delta-hedged P&L explain into gamma / vega / theta / residual (`explain`), zero-mean delivered vol (`delivered_vol`) and implied/delivered (`realized`), walk vol (`walk`), delta-hedge simulation with threshold and bid/offer (`sim`), plus `convexity_value` for linear gamma with decay. `python scripts/gamma_pnl.py --help`. `--selftest` checks exact identities (theta = -1/2 sigma^2 gamma, vega = sigma T gamma, finite-difference greeks, put-call parity), the Monte Carlo mean P&L (sigma_r - sigma_i) sqrt(T/(2 pi)), the walk-vol, delivered-vol (incl. NaN and short history), explain-series (flat forward, gapped dates) and convexity known answers, and fails non-zero on any mismatch.

## Deeper detail
Bundled references: [hedging-policy-evidence](references/hedging-policy-evidence.md) (backtests, cost tables, hedge time by market and period, regime filters), [convex-linear-packages](references/convex-linear-packages.md) (gamma of linear products, futures-vs-swap, convexity adjustment, delta-hedged flatteners, package math), [second-order-greeks-and-maintenance](references/second-order-greeks-and-maintenance.md) (vanna/volga, hedge-vol choice, package maintenance, sectors, forward vol).

## Related skills
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): grid-level implied vs realised RV, listed vs OTC vol; this skill supplies the P&L arithmetic for those trades.
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): long-end convexity value, MBS convexity flows, synthetic vol via DV01-neutral packages.
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): smile effects, vanna and volga exposure of skew structures.
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): midcurves and curve options, forward vol from midcurves.
- [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md): futures basis as a short option; hedged bond = long straddle.
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable/structured vega supply behind persistent cheap or rich vol.
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): convexity-hedger flows as the source of cheap or rich long-end gamma.
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): CTD switches that break a constant-vol delta on bond-futures options.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores of implied/realised ratios.
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures vs FRA/OIS convexity as short gamma.
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): implied distributions from STIR options.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-space RV that underpins delta-hedged forward flatteners.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll as the theta of linear trades.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 and pv01 conventions, bucketing, hedge ratios.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market swap and option conventions.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): bid/offer and liquidity regimes that set the hedge threshold.
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): P&L explain framework.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used above.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): where the resulting trade goes.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-based conditional curve trades.

## References
- BofA Global Research (Braizinha) - US Vol Primer: A Guide for the Perplexed (11 Mar 2024): Bachelier/Black greeks, delivered and walk vol, calendars, short-gamma practice, levels and worked numbers.
- Citi Research (Bikbov, Williams) - Rates Vol Lab: The art of gamma hedging (12 Mar 2018): systematic short-gamma backtest, threshold vs bid/offer, time of day, cost tables.
- Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch and Dee, 2022), Ch.20-23: swaption greeks, break-even vol, event vol, IRD gamma and cross-gamma, value of gamma, second-order Sharpe.
- Huggins and Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024), Ch.19: delta-hedging intuition, gamma vs vega sector, realised-vol curve trades.
- Huggins and Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): STIR gamma/vega split, floating-strike hedging, realised-vol curve.
- J.P. Morgan (Younger, Salem, Zhao) - Zen and the art of gamma maintenance (9 Mar 2018): kurtosis regime signal, programmatic short gamma, calendar trade.
- J.P. Morgan - A comprehensive look at convexity hedging in interest rates (29 Mar 2019): hedge thresholds and delta delivery.
- J.P. Morgan (Gupta, Inkinen, Vijay) - Update on systematic rule based trading strategies (6 Feb, 10 Jul 2017; 8 Jan 2018): EUR 3Mx10Y short-gamma timing rules and backtests.
- J.P. Morgan - Global Fixed Income Markets Weekly (21-22 Aug 2026): implied/realised grid, short-gamma jump risk, GBP vs EUR gamma spread.
- J.P. Morgan - An option by any other name: sourcing cheap convexity in the long end (3 Feb 2017): curve as gamma source, curve-implied vol.
- Citi Research - Trading long-dated convexity (9 May 2019) and Deal or no deal (10 May 2019): delta-hedged flattener backtest, thresholds, costs.
- Citi Research - Taking profits on delta-hedged 15y5y/20y10y flatteners (5 Dec 2019), Reweighting (16 Oct 2019), Fixing the plumbing (30 Sep 2019), Buying vol for less (25 Sep 2019): daily BE/RV, lifecycle, cross-market screens, hedge time.
- Citi Research - Gamma and Vega RV (14 Jan 2019), In search of cheap vol (17 Jan 2020), Liquidity, vega, and convexity (30 Mar 2020), Eat, pay, spend (27 Mar 2020): hedge rules, intraday ratio, ZLB short gamma.
- Citi Research - Left-side vols' outperformance (22 Jun 2021), Short Blues convexity via futures/swaps (21 Feb 2023): convexity adjustment as short delta-hedged straddle.
- Citi (Parolari) - A Holistic Approach to Convexity Across Fixed Income (Jun 2022): unified P&L decomposition, ex-ante expected return and Sharpe.
- Salomon Brothers (Ilmanen) - Understanding the Yield Curve Part 5: Convexity Bias and the Yield Curve (Sep 1995): value of convexity, static vs dynamic hedge, barbell as straddle.
- CME Group (Rogerson) - Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures (4 Jun 2025): futures-vs-swap convexity P&L table.
- Quantitative Finance Stack Exchange - Gamma Pnl vs Vega Pnl; Gamma PnL Formula and Break-Even volatility; Continuous delta hedge formula; Delta hedge value formula; Delta Hedging with fixed or floating IV; Delta Hedging with fixed IV to get rid of vega; Realizing the same PnL as Gamma Vs Vega; Option: link between Vega and Gamma; Long Gamma vs Vega; Vol, Gamma, Vega - essentially all the same; Bergomi: Skew arbitrage; How to measure Steepener/Flattener/Butterfly sensitivity; Why are FRA/futures convexity adjustments necessary (2015-2025): P&L identities, break-even move, hedge-vol choice, curve gamma, gamma decay.
- Credit Suisse (Bassman) - The Convexity Maven: Building a Better Volatility Mousetrap (6 Sep 2012) and The FVA (27 Aug 2013): calendars vs forward vol.
- Ade Rhodes - Trade Idea: USD 3m2y Payer Skew Steepener (8 Oct 2025): Taylor expansion, vomma, maintenance thresholds.
- Merrill Lynch RateLab - Professional Javelin Catching (16 Feb 2007) and BofAML - Paying Nickels for Dimes (21 Jan 2010): implied/realised fair value 107%, 3:1 carry rule.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis, 3rd ed. (McGraw-Hill, 2005): hedged bond as long straddle, basis as short option.
- Hull - Options, Futures, and Other Derivatives, 9th ed. (Pearson), Ch.31: bump-and-reprice greeks, hedging outside the model.
- Convexity Maven (Bassman) - It's Never Different This Time (29 Jan 2018): low vol raises gamma, convexity-hedging accelerant.
- J.P. Morgan (Salem, Younger, St John) - Fast and furious: the link between rapid trading and volatility in US rates (20 Nov 2018); J.P. Morgan - Issuance, pensions, and long-end spreads (14 Sep 2018): fast-flow share vs realised vol, hurricane gamma event study.
- Nordea Markets (Aalund) - Bonds and bold (5 Nov 2021): systematic EUR 10y10y long-straddle backtest (marketing material).
- Citi Research - Forward steepener and vol divergence (12 Jun 2023), Vol cycle, steepeners, and SOFR (25 Mar 2019), Year-Ahead: Bumpy road for vol (12 Dec 2016), Fair value vs seasonality (1 May 2017), Convexity Meets Steepeners (19 Apr 2018): hedge time, forward-steepener BE/RV, front-end slope and May seasonality of short gamma, intraday vs close-to-close realised.
- Nomura (Firoozye, Zhang) - Derivative Focus, Erratum: Conditional Euribor bull flatteners (19 Jun 2014): option-spread greeks and model dependence.
- Tuckman and Serrat - Fixed Income Securities, 4th ed. (Wiley, 2022), Ch.15-16: backbone and constant-vol delta, negative convexity as short vol.
- Jacquier and Slaoui - Variance Dispersion and Correlation Swaps (working paper); Shafer and Vovk - Probability and Finance (Wiley, 2001); MIT OpenCourseWare 18.642, Lecture 7: Linear Rates Models (26 Sep 2024): second-order P&L, variance-swap greeks, finite-difference gamma.
