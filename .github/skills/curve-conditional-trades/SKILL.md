---
name: curve-conditional-trades
description: 'Structure, price and screen option-based conditional curve trades in G10 rates - conditional (costless/zero-premium) bear or bull steepeners and flatteners, conditional flies, payer/receiver ladders, 1x2s and payer spreads, curve caps/floors and CMS spread-option alternatives, futures-option vs swaption conditional spreads. Covers DV01-matched notionals, costless-strike (strike-shift) vs vol-weighted premium neutrality, curve/vol/total pick-up to forwards, implied vs delivered directionality, the three-to-one carry/premium rule, carry of option packages. Use when asked for a conditional steepener, conditional flattener, costless strike, zero-cost or premium-neutral curve trade, payer/receiver spread, ladder, 1x2, curve cap, "steepener funded by selling vol", midcurve or left-side vs right-side vol, or whether option vol makes a 2s10s, 5s30s, 10s30s or fly trade cheaper than swaps or forwards. Outright skew and tail hedges: vol-skew-and-tail-hedging; curve-cap correlation: vol-correlation-and-curve-options.'
---

# Conditional curve trades (option-based steepeners, flatteners, flies and zero-cost structures)

A conditional curve trade buys an option on one tail and sells an option on the other so that a curve (or fly) exposure
exists at expiry only if yields move in the chosen direction, usually for zero premium. It pays because options on
different tails price different vols and different directionality: the strike at which the curve position is struck is
the "costless strike", and the edge is how much better that strike is than the forward curve (the pick-up). The trade is
Type 1 in Huggins' classification (terminal-level exposure, no delta hedge); it is not a realised-vol trade.

## When to use
- "Cheaper way to be steeper/flatter than swaps?", "costless 3y 10s30s bear steepener", "sell rich 2y vol to fund 10y payers".
- Choosing between bear/bull and steepener/flattener expressions given what the curve does in sell-offs and rallies.
- Zero-premium payer spreads, ladders, 1x2s, conditional flies, curve caps/floors, or a futures-option vs swaption spread.
- Screening a grid of expiry x tail pairs by pick-up, percentile and implied-vs-realised beta.
- Not here: unconditional (swap/bond) steepeners and weights ([curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md)); delta-hedged realised-vol curve trades ([vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md)); implied correlation and spread-option pricing ([vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Swaption normal vols, expiry x tail x strike offset (needs ATMF forward and >= 2 strikes per tail for skew) | `vol_surface` | daily snap, >= 3y; since 1990 for strike-curve percentiles where available | nvol in bp/yr, strikes as offsets from ATMF |
| Spot and forward-start par swap rates | `curve_par` | daily, same snap as the vols | curve = long tail - short tail, bp |
| Listed STIR / bond-futures options (conditional futures-option legs, midcurve) | `opt_static`, `opt_quotes` | daily settle | STIR nvol of the rate in bp = price-point vol x 100 |
| Fwd/strike curve history for z-scores, percentiles; beta windows | derived from above | 1y levels, 3m changes | never mix snaps |

Never invent a vol or forward. If the ATMF vol of either tail or its forward is missing, ask the user or data adapter.
See [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) and [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md) (annuity, day count, cash-vs-physical settlement per market).

## Method

### 1. Conventions
- Rates/strikes in pct, spreads in bp. Curve = long tail - short tail (2s10s = 10y - 2y). Normal (bp/yr) vols throughout.
- Structures (BofA, US Vol Primer, 11 Mar 2024):

| Structure | Buy | Sell | Driver (BofA) |
|---|---|---|---|
| bear steepener | long-tail payers | short-tail payers | macro |
| bear flattener | short-tail payers | long-tail payers | policy |
| bull steepener | short-tail receivers | long-tail receivers | policy |
| bull flattener | long-tail receivers | short-tail receivers | macro |

- Bear trades use payers, bull trades use receivers. Terminal payoff when both options are ITM is +-(curve - K): steepener = curve - K, flattener = K - curve, with K = K_long - K_short (the strike curve). If only one option is ITM it is a naked option: a gain if the long leg, but a loss that grows one-for-one with the yield if the short leg (no cap); if neither, it expires worthless. The long leg's downside is limited to its premium, the short leg's is unlimited if directionality fully reverses (JPM Euro conditional-trades primer, 26 May 2016).
- Sizing: terminal DV01-matched notionals, N_short = N_long x A_long / A_short (A = annuity, PVBP). Citi writes the pair as "100/x" with the SHORTER tail = 100 and x = longer-tail notional (e.g. 100/22.7 for 2y10y); BofA/JPM put 100 on the longer tail (e.g. 100m 1y10y vs 430m 1y2y). State which. Annuities drift, the short leg faster in relative terms: for a long holding period use forward PVBPs at the intended exit date (Duering, Fixed Income Trading and Risk Management, 2021, Ch.31).
- Use DV01-neutral weights, not PCA/beta-neutral: with swaps you neutralise directionality, with swaptions you want to exploit it (Huggins & Schaller, 2024, Ch.19). With both legs ATMF (delta 0.5) the option hedge ratio equals the swap curve ratio; with OTM legs scale by delta: (BPV_L x delta_L)/(BPV_S x delta_S).

### 2. Pick the conditionality (classification and directionality)
1. Type 1 (no delta hedge, gamma-sector): terminal-level exposure, implied vol matters only at entry. Type 2 (delta-hedged to expiry) is realised vol; Type 3 is trading implied vol. Conditional trades are Type 1 (Huggins & Schaller, 2024, Ch.19).
2. Match to the curve's directionality: if 2s10s bear-flattens (2y yield moves more than 10y in sell-offs), express a flattener with payers (ITM only in a sell-off; in a rally, where steepening would hurt, both options are OTM). Receivers give the flattener conditional on a rally. Directionality is usually already priced (2y realised vol > 10y), so the "right" conditionality usually costs pick-up; look for where it does not (Huggins & Schaller, 2024, Ch.19).
3. Implied directionality of the curve to the long yield = 1 - vol_S/vol_L (JPM: 3y vol 25 vs 20y vol 63.4 -> 61%). Delivered directionality = regression beta of curve changes on long-yield changes (use 1y; check levels vs changes and the lookback, dummy out one-off policy jumps). Delivered = 1 - beta of the short-tail yield on the long-tail yield (JPM windows: 3m; its table row: 1y), the same number as the curve-on-long-yield beta. Edge = delivered - implied: positive means the options under-price how much the curve moves with the long yield (JPM, 26 May 2016; 2s10s 72% delivered vs 61% implied = +11%, R2 79%). `delivered_directionality` in the script.
4. Directionality is regime dependent: a hiking cycle tends to bear-flatten, the onset of easing bull-steepens (JPM, 26 May 2016), so re-estimate it inside the current policy phase.
5. No view on direction but expect directionality to persist: straddle vs straddle unhedged (JPM, 26 May 2016). Policy-driven pairs are bear flattener / bull steepener, macro-driven pairs are bear steepener / bull flattener (BofA, 11 Mar 2024).

### 3. Premium neutrality: three ways (all JPM, 26 May 2016 unless stated)
- **A. Costless strike (strike shift)**: keep the lower-premium leg ATMF; strike the higher-vol (higher DV01-matched premium) leg OTM (payer above / receiver below the forward) until net premium = 0. Premium of an ATMF option: P = sigma x A x sqrt(T/(2*pi)) (T years, sigma bp/yr, A annuity in years -> P in bp of notional). The closed form for the shift solves delta*(-x) + 0.5*gamma*x^2 = -dP and is exact only at zero skew; with skew re-vol the shifted strike and solve numerically (`zero_cost_conditional` does this from a vol-vs-offset function).
- **B. Vol-weighted**: both legs ATMF; scale the long-tail notional by W = sigma_S/sigma_L (JPM cuts the rich long-tail leg, W < 1; if the short tail is rich, W > 1 gives the same premium match). Exposure is to W x Y_L - Y_S, entry W x F_L - F_S. If options are fairly priced this weighted curve is non-directional; its beta on the long yield = W - beta_S = delivered - implied directionality, where beta_S = beta of the short-tail yield on the long-tail yield. Payoff slope once both options are ITM is (W - beta_S): profitable if beta_S < W.
- **C. Structures made costless by taking unlimited loss**: 1x2 (1,-2), ladder (1,-1,-1): see step 7. (A payer spread (1,-1) or payer fly (1,-2,1) has capped loss but always costs a net premium.)
- A vs B: weighted wins on small moves, strike shift on large shocks (when delivered directionality outpaces implied). Breakeven long-yield move for A is delta_shift / (1 - W) + C_L (C_L = rate carry of the long-tail swap, ATMF forward minus spot rate), independent of realised beta. Larger vol differential -> larger shift -> larger breakeven -> prefer B. Equal vols: both coincide.
- Cushion rule (BofA): spend excess premium on moving the short-leg strike OTM ("lose money later in a sell-off rather than make money sooner"), not on moving the long strike ITM.

### 4. Screen metrics (Citi conditional-curve screen; same definitions 2016-2026)
Per trade: spot curve S; forward curve F (3m z-score); costless-strike curve K (1m change, 3m z-score, percentile since 1990); implied beta of the curve on the average of its end points implied by vols vs realised beta over 3m (report realised - implied); 3m roll (running-yield bp, unchanged curve and vol cube).

| Metric | Steepener | Flattener |
|---|---|---|
| Curve pick-up | S - F | F - S |
| Vol pick-up | F - K | K - F |
| Total pick-up | curve + vol | curve + vol |

- Grid: expiries 3m, 6m, 1y, 2y, 3y x tails 1y2y ... 10y30y (1y2y, 1y3y, 1y5y, 2y5y, 2y10y, 2y30y, 3y5y, 3y10y, 3y30y, 5y10y, 5y30y, 10y30y); separate bear-steepener/bull-flattener and bull-steepener/bear-flattener tables. Flag top three of each; Citi stresses flagged rows are "backward looking ... illustrative only", not recommendations.
- Look-ahead: z-scores and percentiles of K and F use history up to the snap only (expanding window); K history needs the same constant expiry x tail grid every day. Delivered-beta regressions on overlapping 3m windows overstate R2 and t-stats: use non-overlapping changes.
- Percentile test: K in a low historical percentile (strike curve low or inverted vs history) is an attractive terminal entry (Citi, 3y 10s30s Dec 2016: K -5.0bp, 1st percentile).
- Check arithmetic against the screen (Citi, 1y 2s10s, 12 Jun 2023: S -102.3, F -23.3, K -57.6 -> curve -78.9, vol +34.3, total -44.7). The script's `pickups` reproduces this.
- `solve` CLI: ATMF forward and vol per tail from `vol_surface`, flat-yield annuity (approximation), spot curve from `curve_par` (one snap only); prints notionals, costless strikes, strike curve, vol pick-up, net delta (rate-delta sign: long payer > 0, so DV01 sign is opposite) and vega, and curve pick-up if spot is supplied.

### 5. Entry rules and thresholds
- Trade when the structure sells rich vol and buys cheap vol so the costless strike is better than forwards (positive total pick-up); normally avoid structures that give up to the forwards (BofA, 11 Mar 2024). Left-side (short-tail) vol rich vs right-side vol implies pick-up for bear steepeners and bull flatteners and give-up for bear flatteners and bull steepeners.
- Pick-up in context (BofA, 23 Feb 2024 levels, costless ATM conditional curve trades, bp): bear steepener 1y expiry 2s5s 10.6, 2s10s 17.3, 2s30s 26.5, 5s10s 6.7, 5s30s 16.9, 10s30s 10.8; bull flattener 10.4 / 15.7 / 24.1 / 6.2 / 15.3 / 9.7. Citi's 3y bear-steepener rows in 2016-2020 showed 13-37bp total pick-up (6bp in Sep 2019, 19bp in Mar 2019) with 3m roll of 0.8-1.2bp.
- Carry-vs-entry: the trades with best carry usually have the worst entry. Use pick-up, percentile and z-score together, and check lookback sensitivity (3y vs since 2000). Prefer the tighter market among near-equivalents.
- Vol-curve coupling: when the curve behaves as a one-factor function of vol, bull flatteners/bear steepeners become expensive when top-left vol cheapens vs other vols (Citi, European Rates Strategy, 20 Aug 2026). Check where the vol grid sits first.
- Event timing: wait for a hawkish-skip FOMC to pass before entering long-end steepeners (knee-jerk bear flattening with muted vol) (Citi, 12 Jun 2023).

### 6. Conditional flies
- Buy (sell) payers or receivers in the belly vs sell (buy) on the wings, wings ATMF at 50/50 DV01 weights, belly strike solved for zero cost. Citi quotes spot/forward/strike fly with weights -0.5 / 1 / -0.5 (belly less the average of the wings; positive = belly cheap). That is HALF the 2s5s10s = 2x5y - 2y - 10y convention used elsewhere in this repo: state which one and double before comparing with cash flies.
- Diagnostics: correlation of the forward fly with the belly (3m on changes, 1y on levels); 1y levels regression of the forward fly on the belly -> rich/cheap bp and z; belly OTM distance; percentile of strike fly since 1990; curve, vol, total pick-up; 3m roll. Main risk: fly and rates decorrelate (Citi, 25 Sep 2019: 34% in changes, 92% in levels).
- Huggins: if 5y underperforms 2y and 10y in sell-offs, long 5y payers vs short 2y and 10y payers (or the receiver/straddle versions); only pays if the 2-5-10 implied-vol curvature is negative. In his screen (R2 of directionality regression vs premium pick-up) only 7s10s20s (R2 ~0.84, ~+0.5bp) and 5s10s20s (R2 ~0.55, ~+1.3bp) had positive pick-up for the right conditionality; the rest were -3 to -15bp. Look upper-right (strong directionality, zero/positive cost).
- Risk-weighted option flies: 2s/10s/30s receiver fly with risk weights 0.577 / -1.0 / 0.228 (JPM, 14 Sep 2018); 6Mx20Y payers vs 6Mx10Y and 6Mx30Y with 50% risk on the belly and equal-delta wings (JPM, 23 Aug 2019).

### 7. Premium-neutral directional structures (unlimited-loss family)
- Payer spread (1,-1): max payoff = strike gap, loss = premium (never costless). Payer fly (1,-2,1) gives a tent with the same maximum, loss capped at premium.
- 1x2 (1,-2) and ladder (1,-1,-1) can always be made costless. Both are long duration (positive DV01) and short vol at inception, the opposite of an outright payer: they lose mark-to-market on sharp early moves and suit gradual under-performance vs forwards. Costless 1y10y 1x2 gap ~60bp: vega -23.4k, DV01 +8.1k, gamma -175, theta +3,869; costless ladder gap 42bp: vega -22.3k, DV01 +7.5k (BofA, 11 Mar 2024).
- Ladder arithmetic (Bassman, "How High is High", 17 Sep 2013): buy 5y5y payer 4.85%, sell 5.60%, sell 6.90%, all 100mm, zero cost: payoff 0.75 flat between 5.60% and 6.90%, gone at 7.65%, unlimited loss above. Size and strike to a level you are confident will not be breached. The payoff function in the script reproduces this.
- Floor/cap ladders on the curve (costless forward 2s10s floor ladder, BofA 23 Jul 2025; costless 10s/2s CMS cap ladder buy ATMF, sell +11bp and +22bp OTM, Citi 13 Aug 2026) monetise elevated curve-cap skew; risk is a sharp move beyond the downside breakeven.
- Contingent payer spreads (rates option funded by a stock-index trigger) are an economic sale of stock-bond correlation, need an ISDA and are professional-only (Bassman, "For Propeller Heads Only", 17 Jun 2019).

### 8. Carry/premium three-to-one rule (outright or curve-hedged receivers)
ratio = 1y pure roll-down (spot vs forward curve, DV01-scaled) / premium of the 1y-expiry receiver swaption, same units. Trigger as it nears 3:1; 2.75-2.85 "acceptable". Logic: with no view on spot vs forward being realised, fair payoff is 2:1; an option costing 1 that pays 3 if the curve is unchanged is 3:1 payoff on 2:1 risk. The ratio usually stays below 2:1 because curve and vol are tightly correlated; it normalises via a flatter curve or higher implied vol. It is the author's rule of thumb, not a backtested statistic (Bassman, "Your Ace in the Hole", 16 Jul 2014; "Paying Nickels for Dimes", 21 Jan 2010). `carry_to_premium` in the script.

### 9. Alternatives and carry
- Spread vol: sigma_spread = sqrt(sigma_A^2 + sigma_B^2 - 2 rho sigma_A sigma_B); low implied correlation = rich curve-spread vol (curve-cap demand). Curve caps lose at most the premium, are bets on implied correlation, and pay whenever the final curve is through the strike whatever the level did, while a conditional bear steepener expires worthless in a bull steepening - prefer conditionals when directionality is strong and persistent (JPM, 26 May 2016; Bassman, "Yield Curve Options", 8 Dec 2006). A printed formula in the BofA primer carries "+2 rho"; the correct sign for a spread is minus.
- Package carry (Nomura, 19 Jun 2014): leg carry = aged price (3m less to expiry, underlying rolled) - today's price; package carry = long leg - short leg; quote over several horizons and to expiry because carry is non-linear in time.
- Futures-option vs swaption spread (Treasury futures options, Citi 2016-2026): swaption notional sized for 1,000 option contracts, swaption strike solved for zero cost, swaption strike = futures-option strike yield + invoice spread, "bp pick-up" = costless strike spread - invoice spread as defined. Printed signs in the 2023 and 2026 notes contradict that definition (see Pitfalls); confirm the convention before quoting. Delivery options/CTD move the futures leg: price the wildcard (JPM, 6 Mar 2020) - see [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md).
- Delta-hedged curve trades (realised-vol alternative): daily breakeven BE = daily move whose convexity gain 0.5 x gamma x m^2 offsets negative daily carry (0 if carry >= 0), RV = 1y realised daily vol. Long-convexity flatteners: convexity must pay for the carry, so LOW BE/RV is better (Citi, 9 May 2019: BE 1.3 / RV 3.0 = 0.42 chosen; carry-positive GBP rows show 0). Short-convexity forward steepeners earn positive carry and lose convexity, so the mirror applies: BE is the move that eats the carry and BE/RV > 1 is the cushion (Citi, 12 Jun 2023: 10y10y/15y15y BE 6.18 / RV 5.30 = 1.17; 10y10y/25y10y 0.85); the positive "carry" printed next to a non-zero BE in that table is this mirror. Hedge every 15-30bp. Detail belongs to [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md).

## Worked examples
1. **USD 1y 2s10s bear steepener, costless strike (BofA, US Vol Primer, 11 Mar 2024; Feb 2024 levels).** Buy 100m 1y10y ATM payer (K 3.727%, vol 110bp, DV01 -36,451 as printed, vega 31,203) vs sell 430m 1y2y payer (vol 132bp, ATMF 3.837%): net receive ~0.68m premium. Move the 1y2y strike +17bp (to 4.007%) to make it costless: entry 17bp flatter than forwards (vol pick-up +17), residual DV01 -2.8k, vega +309. `solve` on a synthetic surface with the same vols and forwards gives a shift of 18.6bp and notional ~435m for the short leg (flat-yield annuities vs BofA's exact ones; 17bp and 430m printed).
2. **EUR 3s20s bear steepener, 3M payers: strike shift vs weighted (JPM, 26 May 2016, Exhibit 8).** 3Mx3Y vol 25bp, PVBP 301, ATMF -0.10%; 3Mx20Y vol 63.4bp, PVBP 1790, ATMF 1.10% (the exhibit labels vols bp/day, but 25 x 3.01 x sqrt(0.25/2pi) = 15bp reproduces the printed premium, so they are per year). Notionals 595m (3y) / 100m (20y). Strike shift: 20y strike +23bp -> 1.33%, entry 143bp vs forward ~120bp, i.e. a 23bp give-up for the steepener (a pick-up for the mirror flattener). Vol-weighted: weight 39%, notional 39m, ATMF strikes, entry 0.39 x 1.10% + 0.10% = 53bp. The long-tail (higher-vol) leg is struck OTM here because its vol is higher. Script reproduces the shift within ~3bp (flat-vol Bachelier, rounded inputs) and W = 0.39.
3. **Screen row with a pick-up (Citi, Dec 2016, 9 Dec close).** 3y 10s30s bear steepener, notionals 100/41.9; spot 31.7, forward 3.8, K -5.0 (1m chg -11.0, 3m z -1.5, 1st percentile); implied beta -0.07 vs realised 0.04; curve pick-up 27.9, vol pick-up 8.8, total 36.7, 3m roll +1.0. (Citi, US Rates Vol Lab, 12 Dec 2016.) Jan 2017 version: 24.4 / 1.7 / -10.9, total 35.2 (Citi, 17 Jan 2017).
4. **Negative curve pick-up case (Citi, 25 Sep 2019).** 3y 5s30s steepener: spot 21.8, forward 23.2, K 15.9: curve pick-up -1.4, vol pick-up +7.3, total +5.9 - the entry is paid for by vol, not by the curve.
5. **Costless swaption steepener vs CMS cap (Citi, US Rates Weekly, 3 Feb 2017).** Buy $41.7mn 3y30y ATMF+40bp payers vs sell $100mn 3y10y ATMF+57bp payers: costless strike spread ~-15.5bp (inverted), carry ~+$215K in year 1. CMS-cap version ($1bn 3y30y cap ATM+30bp vs $1bn 3y10y cap ATM+44bp) costless strike spread ~0bp and avoids the payer version's negative convexity.
6. **Bull flattener from STIR options, a net-debit (not premium-neutral) example (Nomura, 19 Jun 2014 erratum).** Sell 5,000 near white-pack calls (99.875) vs buy 5,000 2y mid-curve green-pack calls (99.375), net debit 15.5 ticks (EUR 1.94mn); 3m package carry = 0.82 - (-0.97) = 1.79 ticks (EUR 224k, 11.5% of price; printed 11.6%); vega +5,958, gamma -3,768, theta -2,806 per day: positive vega but short gamma and short theta at inception. More cases (JPM trade lists, Citi flatteners, Bassman structures, per-market notes) in [references/trade_examples.md](references/trade_examples.md).

## Signals & interpretation
- Total pick-up > 0 with positive vol pick-up and K in the bottom decile of its history since 1990: strike is attractive; prefer curve pick-up >= -2bp or have a thesis for paying it away, example 4 (working rule, not from the sources). Total pick-up < 0 means the structure gives up to forwards: skip unless you want the conditionality as insurance.
- Realised - implied beta > 0 (curve more directional than options price) supports the "right" conditionality; check with levels and changes and over at least two lookbacks before trusting it.
- Low 3m z of the costless strike plus positive forward z on a fly with high forward-fly/belly correlation: fly entry is cheap; use the 1y regression rich/cheap as confirmation, not the trigger.
- Roll: the cited 3y curve rows show a 3m roll of +0.5 to +1.2bp (-6.6bp on the Jun 2023 inverted 1y 2s10s row); costless structures are not roll trades, so do not pay for it.
- Three-to-one ratio >= 2.75 on a receiver/bull-flattener overlay: cheap convexity vs curve risk. Ratio < 2: the option is fairly priced; do not buy for carry.
- Stop when the vol regime shifts even if the curve thesis holds (weighted steepeners were stopped out by vol in March 2020, JPM, 6 Mar 2020). The 2026 Citi trade ideas set stops at about 50-60% of target; set P&L stops, not only level stops.

## Pitfalls
- Directionality is usually priced; right conditionality typically costs pick-up. Never assume a "free" structure: check delivered vs implied beta.
- Strike shift loses on small moves in the favoured direction (short option ITM first) and wins on large shocks; weighted trade exposure is to the weighted curve and can lose even if the quoted 1:1 curve steepens (if beta_S > W).
- Ladders, 1x2s, floor ladders: unlimited loss; opposite Greeks to an outright option (long duration, short vol); sharp early moves hurt.
- Closed-form strike shift is exact only at zero skew. With skew, vol of the OTM strike differs from ATM: re-solve (the script interpolates vol over strike offset).
- Pick-up sign conventions: Citi's 2023 and 2026 futures-option rows print pick-ups with the opposite sign to the stated definition (costless strike -24.6 vs invoice -29.8 printed -5.2 where the definition gives +5.2; -41.0 vs -38.4 printed +2.6, definition gives -2.6). Confirm with the user which sign they quote. A 2019 note also prints 3.6 sigma in text and 2.6 in the table for one richness read: recompute z-scores yourself.
- Benchmark switches create artificial slope jumps; adjust before using curve screens (Duering, 2021, Ch.31). Linear slope trades can be non-linear at pivot levels (e.g. JGB 10y/30y break near 0.75% / 2% from insurer buying) - needs structural analysis.
- Vol-rate beta flips on flight-to-quality days (e.g. 6Mx30Y beta -3.13 vs +2.1-2.4 earlier, JPM, 2 Oct 2026); delta hedges and regressions built on a recent beta fail. Regression of vol on rates: exclude ZIRP (USD) and pre-2016 negative-rate (EUR) periods.
- Rate-vol spikes break RV relationships and force de-risking; positioning can override valuation (BofA, 2 Oct 2026; Citi, 13 Aug 2026).
- Liquidity: do not initiate attractive conditional RV in illiquid markets; check bid/offer on both legs and that lots, Greeks and notionals are consistent (the Nomura erratum corrected a 1,000-lot table to 5,000 lots) (Citi, 30 Mar 2020; Nomura, 19 Jun 2014). Do not sell gamma at a zero-lower-bound onset; sell vega in longer expiries instead.
- Crowding: when positive-carry steepeners are widely held and slopes sit at multi-decade extremes, positive-carry flatteners are the diversifier (Nomura, 2014).
- Conditional-trade screens are backward looking; hedge-timing (time of day) changes realised vol of any delta-hedged alternative.
- STIR spread as slope proxy: verify it tracks the swap slope (98% with 2s5s in the Nomura example) and is not driven by a stretched fly.

## Market notes (G10)
- USD: richest data (SOFR/CMS swaption grid, Treasury futures options). Callable-supply (Formosa-type) selling flattened the long end in 2017-2020 and cheapened 30y-tail vol after the 2016 election; "no natural payer" at the ultra-long end (JPM, 21 Feb 2020; see [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md)). Insurer/variable-annuity receiving steepens the >20y curve (Citi, 9 May 2019; see [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md)).
- EUR: swaption tails plus mid-curve Euribor options (bull flattener template above); EUR 3s20s example; 1m10y gamma persistently cheap vs 1m5y and 1m30y in 2026 (Citi Markets email, 29 Jul 2026).
- GBP: SONIA conditionals in closed-trade logs (3m10s30s bearish, 3m 2s5s10s tightener, 6m 2s10s bear steepener stopped at -16bp) (Citi, European Rates Weekly, 1 Oct 2026); long-end forward curve steep because 20y is rich on ALM receiving.
- JPY: vols collapsed after 2016 curve control; conditionals carry regime-change risk; realised vol 2.4-3.1bp/day vs 3.9-4.7 elsewhere (2020).
- CAD, AUD, NZD, CHF, SEK, NOK: no conditional-structure material in the sources; swaption/cap markets are far thinner than USD/EUR/GBP, so first verify vol quotes exist and bid/offer is workable. If not, fall back to unconditional curve trades ([curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md)).

## Output
Return per candidate: structure (bear/bull x steepener/flattener or fly, expiry, tails, expressions), notionals (state which tail = 100), strikes and ATMF forwards, premium per leg and net, method (strike shift / weighted / ladder), table with spot S, forward F, strike K, curve pick-up, vol pick-up, total pick-up, 3m roll, K percentile and 3m z, implied vs realised beta, net delta DV01 and vega at inception, breakeven and loss profile (maximum loss; flag unlimited), what the trade is conditional on, liquidity (bid/offer, venue), catalysts and stop rules (P&L stop and vol-regime stop). Flag sign conventions used and any data gap. Hand off the structure to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md); size with [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).

## Scripts
- [`scripts/conditional_curve.py`](scripts/conditional_curve.py): Bachelier premium/delta/vega, zero-cost strike (`zero_cost_conditional`, skew-aware), vol-weighted curve, pick-ups, option-package payoff (ladders), three-to-one ratio, spread vol/implied correlation, daily breakeven, delivered directionality. `python scripts/conditional_curve.py --help`; `solve` takes canonical `vol_surface` / `curve_par` CSVs. `--selftest` checks ATMF closed form, put-call parity, quadrature, zero-cost identity and pick-up signs for all four structures, the JPM and Citi numbers above, the ladder payoff, and a simulated directionality beta. Annuity in the CLI is a flat-yield approximation; supply exact annuities in code when it matters.

## Related skills
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): unconditional DV01/beta-weighted spreads and regime behaviour; the swap-based benchmark for pick-up
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weights, residuals and directionality for the cash-curve fly
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): curve caps, CMS spread options, implied correlation
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): delta-hedged flatteners, BE/RV screen, convexity harvesting
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): vol grid richness, PCA vol residuals, listed vs OTC
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): skew that makes ladders and OTM strikes cheap or rich
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): Greeks and P&L of the packages
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): forwards, roll, carry/vol ratios
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): annuity/PVBP, hedge ratios
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): percentiles and z-scores of K and F
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA vol and curve residuals
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): delivered-directionality regression, overlap, regression direction
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): CTD and wildcard effects on futures-option legs
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR futures and mid-curve legs
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): annuity, day count, settlement per market
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md): stops and vol-regime exits
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): pre-mortem before sizing an unlimited-loss structure
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-grid RV, kinks and aged forwards.
- [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md): basis as embedded vol vs options.

## References
- Citi Research, Rates Vol Lab series (Bikbov, Williams, Chang, Appeddu et al.), 2016-2026 (Year-Ahead "Bumpy road for vol", 12 Dec 2016; "Buy long expiries", 17 Jan 2017; "Long Live Formosa", 9 Jan 2017; "Fair value vs seasonality", 1 May 2017; "Value in Greens convexity", 15 May 2017; "The art of gamma hedging", 12 Mar 2018; "Gamma and Vega RV", 14 Jan 2019; "Vol cycle, steepeners, and SOFR", 25 Mar 2019; "Trading long-dated convexity", 9 May 2019; "Buying vol for less", 25 Sep 2019; "In search of cheap vol", 17 Jan 2020; "Liquidity, vega, and convexity", 30 Mar 2020; "Forward steepener and vol divergence", 12 Jun 2023; "Slow and steady wins the short gamma race", 14 Sep 2026; "Fading vega dislocations", 5 Oct 2026): screen definitions, pick-up formulas, rows and ranges
- J.P. Morgan European Rates Strategy - "A primer on Conditional Trades" (Gupta, Bassi, Vijay, 26 May 2016): strike shift vs vol-weighted neutrality, directionality, breakevens (core source)
- BofA Global Research - "US Vol Primer: A Guide for the Perplexed" (Braizinha, 11 Mar 2024): four structures, costless pick-up table, ladders and 1x2 Greeks; "Understanding the yield curve dynamic" (23 Jul 2025): floor ladder, move-type frequencies
- Huggins & Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024), Ch.19: Type 1/2/3 classification, conditionality vs directionality, BPV hedge ratio, conditional fly screen
- Nomura, Derivative Focus: Erratum "Conditional Euribor bull flatteners" (Firoozye, Zhang, 19 Jun 2014): aged-price package carry, Greeks table
- Bassman (Convexity Maven, Merrill Lynch / Credit Suisse): "Yield Curve Options" (8 Dec 2006), "Paying Nickels for Dimes" (21 Jan 2010), "Skewered by Skew" (17 Apr 2013), "How High is High" (17 Sep 2013), "Your Ace in the Hole" (16 Jul 2014), "Another Fine Mess" (11 Jun 2008), "For Propeller Heads Only" (17 Jun 2019): spread vol, three-to-one rule, ladders, contingent spreads
- J.P. Morgan North America Interest Rate Derivatives (Younger, Salem, St John), 3 Aug 2018, 14 Sep 2018, 23 Aug 2019, 13 Sep 2019, 31 Jan 2020, 21 Feb 2020, 28 Feb 2020, 6 Mar 2020: premium-neutral trade lists, risk weights, stop discipline
- Citi Research US Rates Weekly (3 Feb 2017, 20 Apr 2018, 18 Jan 2019, 17 Feb 2023, 2 Oct 2026) and Global Macro Trade Ideas Radar (13 Aug 2026): swaption vs CMS-cap steepeners, cap switches, costless ladders
- Duering - Fixed Income Trading and Risk Management (Wiley, 2021), Ch.31: duration-neutral sizing, benchmark-switch and slope non-linearity
- J.P. Morgan - US Interest Rate Derivatives (Ozil et al., 2 Oct 2026); Citi European Rates Weekly (1 Oct 2026) and Strategy (20 Aug 2026); BofA Global Rates Weekly (2 Oct 2026): regime breaks of vol/rate betas, GBP/EUR conditional trade logs
- Citi Markets hedge-fund sales email (29 Jul 2026): EUR 1m10y gamma vs 1m5y/1m30y
- JWS Macro (Substack), "USD Rates & Fed outlook #1: Summer 2025" (21 Aug 2025): conditional bull steepener on STIR call spreads
