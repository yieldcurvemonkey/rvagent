# Carry, breakeven and convexity of curve trades

Detail behind the "Carry, roll and breakeven" and "Long-end flatteners" steps of [SKILL.md](../SKILL.md). Spread = longer - shorter, bp.
Generic carry/roll mechanics for single instruments live in [fi-carry-and-rolldown](../../fi-carry-and-rolldown/SKILL.md); option-based
versions in [curve-conditional-trades](../../curve-conditional-trades/SKILL.md); the long-end convexity valuation in
[vol-convexity-and-long-end](../../vol-convexity-and-long-end/SKILL.md).

## 1. Breakeven formulas

Forwards are breakevens, not forecasts: a DV01-weighted curve trade must move by its spot-forward gap over the horizon just to break even; a
negative-carry steepener behaves like theta on a short-dated option (Bassman, Sharp Curve Ahead, 25 Jan 2024; The Cost of Carry, 5 Mar 2024).

- Spread breakeven over horizon `T`: `BE_spread = fwd_spread(T) - spot_spread`, with `fwd_spread` built from the `T`-forward of each leg (same
  tenor remaining, i.e. `f(T, n-T)` for a spot `n`-year instrument, or the same forward start+tenor for a forward-start trade). A steepener needs the
  spot spread to rise by `BE_spread`; a flattener needs it to fall by `-BE_spread`. Positive `BE_spread` = steepener carries negatively.
- Per-leg (5y, 1y horizon; BofA, Rates basics: spot vs forward, 15 Feb 2024): rolldown = `5y spot - 4y spot`; carry breakeven = `5y spot - 1y4y fwd`; the source's "carry+roll"
  = `4y spot - 1y4y fwd`, which is the breakeven minus the rolldown, so it is the pure forward-vs-spot carry (breakeven = rolldown + that term). 3m: rolldown `5y - 4.75y`, breakeven `5y - 3m4.75y fwd`. Express breakevens as a fraction of the 1-sigma implied move over the horizon.
  For a duration-weighted trade the result depends only on the slope change; for a non-DV01-neutral trade on each leg's yield change.
- Swap form (Nordea Research, Carry & Roll, 12 Jul 2013): `Carry(6M) = [SR(0,5Y) - F(0,6m)] / dv01(Swp(6m,4.5Y))` (times coverage and the 6M discount
  factor); approximation `Carry(6M) ~ SR(6m,4.5Y) - SR(0,5Y)` valid only for horizons up to the fixing period ("never use the carry approximation for horizons in
  excess of the fixing period"). Roll of a spot swap `SR(0,5Y) - SR(0,4.5Y)`; roll of a forward starter `SR(6m,5Y) - SR(0,5Y)`; forward-starting swaps have no carry. For a
  DV01-neutral spread, leg rolls in bp net as a difference without scaling because both legs carry the same initial risk.
- Forward relations in zero space (Salomon Brothers, Understanding the Yield Curve Part 2, Jun 1995): `f(m,n) ~ (n s_n - m s_m)/(n - m)`, rolling yield
  `f(n-1,n) ~ s_n + (n-1)(s_n - s_{n-1})`, and the forward-spot premium equals term spread plus rolldown. Breakevens must include rolldown, which makes the
  rolling-yield curve more concave than spot. A duration-neutral flattener earns negative carry in a concave curve and pays only if flattening exceeds what forwards
  imply; "the amount of spread change implied by the forwards is a useful cheapness indicator".
- Forwards are poor predictors: long rates tend to move away from forward-implied direction; net a risk premium (and convexity at the long end) before reading forwards as
  expectations. Rolldown is an unchanged-curve scenario, not an arbitrage; it is effectively short vol and long theta, crowded among reactive users, and failed badly in 2021-22
  ("when the IR curve is expected to change dramatically this is precisely the point at which roll-down becomes unappealing", Darbyshire, Pricing and Trading Interest Rate
  Derivatives, 3rd ed., 2022).
- Months to breakeven = mispricing (bp) / carry per month. ING rejected a EUR 1F1Y-10F1Y steepener that was about 14bp too flat but rolled -15.5bp per 3 months (breakeven only
  if the residual closed in under 2.6 months) in favour of a direction-neutral fly whose carry (-2bp/3m) would take more than 36 months to erase the profit (ING, Deconstructing the
  EUR yield curve, 15 Jan 2020). Include execution cost in the entry level.
- Convexity-adjusted expected return in yield bp (J.P. Morgan, Valuing convexity in the long end of the yield curve, 9 Feb 2018): `E(R) = (Y - F)*T/PVBP [carry] + (Y_M - Y_{M-T}) [slide] + 0.5*gamma*sigma^2*T/PVBP [convexity]`;
  doubling vol quadruples the value of convexity. Use normal (bp) vol, not lognormal; bp vol = relative vol x yield (Salomon Brothers, Understanding the Yield Curve Part 5, Sep 1995).
- Steepener vs outright: if the curve slopes up just before the 30y point, a 30y payer carries negatively; a 5y receiver carries positively, so a 5s30s steepener has less
  negative carry than an outright 30y payer. Check which carry a source quotes: financing-based, forward-vs-spot, or carry plus rolldown (Quantitative Finance Stack Exchange, Carry of a 5s/30s
  steepener relative to that of an outright long, Sep 2024). Steepeners therefore trade like cheaper duration with better carry; 5s30s is correlated with being long the market.
- Steepeners roll positively when the forward par curve is flatter than spot (During, Fixed Income Trading and Risk Management, 2021). Select among forward pairs by net roll-down: receive
  the shorter, pay the longer, and keep the pair whose net roll-down is positive (Darbyshire 2022, Ex 23.10: of five pairs only 15M6M vs 21M6M, spread +23bp, net roll +3bp, qualified).
- Second-order Sharpe for spreads: do not use first-order "roll-down / vol of the spread" matrices, which omit gamma and overstate some ratios (Darbyshire 2022, Ch.23). EUR IRS example (Aug 2016):
  pay 10Y20Y / receive 5Y5Y first-order +0.80 becomes +0.42 with gamma; pay 10Y20Y / receive 2Y3Y +0.25 becomes -0.01.

### Worked examples

1. USD 5s30s steepener breakeven, 9 Feb 2024 (BofA, Rates basics: spot vs forward, 15 Feb 2024). 5y 4.15% spot / 3.93% 1y forward (-22bp); 30y 4.38% / 4.35% (-3bp). Spot 5s30s = 4.38 - 4.15 = 23bp,
   forward = 4.35 - 3.93 = 42bp, so the DV01-neutral steepener needs +19bp in a year. The 22bp 5y breakeven is about a third of a 1-sigma move (1y 5y implied vol 65bp); the 30y 3bp about 6%
   (the source rounds the 5y figure to about 30%). A trader with a view that 1y term financing is too high rolls the 5y on overnight repo and term-finances the 30y short; with no view, the forward
   trade locks carry and fixes the threshold.
2. USD 2s10s steepener, 5 Mar 2024 (Bassman, The Cost of Carry): 2y 4.53%, 10y 4.18% (-35bp); DV01 weighting is $430 of 2y per $100 of 10y; the curve must steepen 58bp (to +23bp) in a year to break even;
   a $100mm curve trade costs about $390,000 per month to hold. Jan 2024: at -20bp (2y 4.35%, 10y 4.15%) the curve needs +60bp within a year.
3. EUR 2s5s 6m-forward flattener, 100m in 6M5Y, DV01 ratio 1:2.48 (Nordea, Carry & Roll, 12 Jul 2013): `SR(6M,5Y) 1.195%, SR(0,5Y) 1.023%, SR(6M,2Y) 0.632%, SR(0,2Y) 0.498%`. Roll = (1.195 - 1.023) - (0.632 - 0.498)
   = 17.2 - 13.4 = 3.8bp (the source prints 3.7bp from unrounded inputs); at the printed 3.7bp and 4.93 dv01 per 100 the unchanged-curve P&L is 3.7 x 4.93 = 18.2bp of notional, 182,400 on 100m against 248m. A single 5y position: roll 9.5bp, carry 7.9bp.
4. Zero-coupon barbell flattener (Salomon Brothers, Understanding the Yield Curve Part 2, Jun 1995): s1 6.00, s3 7.75, s5 8.73 gives barbell carry `0.5*(6.00-7.75) + 0.5*(8.73-7.75) = -0.875 + 0.49 = -0.385 pct = -39bp`; the 2s4s spread must narrow 52bp in a year to break even.
   Dec 1994 (same series, Part 1, May 1995): 3m-2y 200bp, 2y-30y 20bp, forwards implied a 2s30s inversion by March; the 2y bullet (steepening position) was cheap and outperformed; by end-March the front end had flattened 108bp and the long end steepened 45bp.

## 2. Long-end flatteners are positively convex (and cost carry)

- A DV01-neutral long-end flattener (receive the longer tenor) has positive P&L in a large parallel move either way because convexity per DV01 grows with maturity
  (zero coupon: `P = e^{-yT}`, `dv01 = T e^{-yT}`, convexity `= T^2 e^{-yT}`, so convexity/dv01 is proportional to `T`). If 40y and 30y yielded the same, DV01-neutral long 40y vs short 30y would
  make money on any move; "the market does not give this for free", so the longer yield is lower (ultra-long inversion) (Quantitative Finance Stack Exchange, Why does the ultra long-end of a yield curve invert?, Aug 2019;
  J.P. Morgan, An option by any other name, 3 Feb 2017). Gamma of a $1,000-PV01 swap: 10Y $1.1, 10Y10Y $3.1, 20Y10Y $5.1, 30Y10Y $7.1, 40Y10Y $9.1, so at 50bp/yr vol the one-year convexity value `0.5*50^2*gamma` is 1.4 / 3.9 / 6.4 / 8.9 / 11.4bp.
- Delta-neutral long-end spread: `E[dP] = 0.5 * G_net * sigma_N^2` for a parallel move; example 29y/30y pay-receive at the same delta `S`: `G = S/10,000`, with 60bp/yr vol worth `0.18 S` a year (Darbyshire 2022, Ex 22.8). Forward-swap gamma `G ~ -(h+i)*S/10,000`.
- Works only if the legs move nearly in parallel: 10s tend to move more than 30s, offsetting the convexity in 10s30s; gamma is best sourced in the very long end where shifts are more parallel and carry cost is lower; if the curve itself is volatile, slope moves dominate (QFSE 2019; J.P. Morgan 2017).
  A flattener has no defined downside and convexity per DV01 falls (curve vol rises) as it ages, so close or roll and realise the curve P&L (Citi, Trading long-dated convexity, 9 May 2019).
- **Curve-implied (breakeven) vol**: the std dev of normal parallel shifts that gives zero probability-weighted payoff after carry over the horizon. If it is below the ATMF swaption vol, the curve is the cheaper long gamma. J.P. Morgan rule:
  if expected payoff > 0 put on the flattener and sell 1Yx30Y ATMF straddles sized so premium = carry; reverse when < 0. Cheap-gamma share, backtest after Jan 2009, 1y horizon: 25Y/20Yx5Y forward flattener 100% vs 30s/50s 70%, hit 86% vs 56%, average P&L 11.4 vs 10.4bp of notional,
  carry +1.1 vs -100.6bp. A replication over 2019-2026 did not reproduce the carry (30s50s +1.36bp under SOFR vs -100.6bp under LIBOR) and showed the signal permanently on for the long pairs (97% of days), with 76 monthly cohorts of 1y holds spanning only about 7.6 calendar years, i.e. fewer than 8 independent annual outcomes (own replication; data to Aug 2026).
- Gilt 30s/50s regression: `30s50s par gilt = 0.6 x 1Y value of convexity + 5.3 x 50Y par gilt yield - 31`, R2 56%, s.e. 4bp (since Jan 2016) puts the curve about 5bp too flat; long-end convexity looked expensive in EUR and JPY (Feb 2018) (J.P. Morgan, 9 Feb 2018).
- Quantifying on a screen (Citi, 9 May 2019, 17 Jan 2020, 5 Dec 2019): columns level, 1y/3y/since-2000 z, 1y carry, daily breakeven BE ("the daily move in rates that yields a convexity gain offsetting a negative daily carry"; 0 if carry is positive), 1y realised vol (bp/day), BE/RV. Smaller BE/RV = cheaper embedded convexity.
  Delta-hedge by re-adjusting the longer leg to DV01-neutral at every 20-25bp move in its rate (15-30bp is the plateau: tighter loses to costs, wider adds variance).

  | Screen 8 May 2019 (USD) | level | 1y z | 1y carry | BE | RV | BE/RV |
  |---|---|---|---|---|---|---|
  | 10y5y/15y15y | -10.1 | 2.50 | -2.91 | 3.5 | 3.2 | 1.07 |
  | 10y10y/20y10y | -13.2 | 1.87 | -1.75 | 2.6 | 3.1 | 0.84 |
  | 10y10y/25y10y | -20.1 | 2.38 | -1.83 | 2.2 | 3.0 | 0.72 |
  | 15y5y/20y10y | -11.3 | 1.16 | -0.31 | 1.3 | 3.0 | 0.42 |
  | 20y5y/25y10y | -9.1 | 1.95 | +0.13 | 0.0 | 3.0 | 0.00 |

  Backtest ($100K DV01, yearly roll, 25bp hedge; average daily P&L $K / daily vol $K / Sharpe): 10y10y/25y10y 5.40/247.6/0.35; 20y5y/25y10y 4.09/219.3/0.30; 15y5y/20y10y 2.92/251.5/0.18. Monthly P&L of 10y10y/25y10y correlates about 26% with 1y10y vol changes, skew about 0, versus delta-hedged short 1m10y straddles with Sharpe about 0.84 but skew about -3.
  A convex payoff must show a smile, not a ramp: bucket P&L by size of the underlying move; carry/slope and level/convexity are collinear at trade horizon; never generalise one structure to a strategy.
- Lifecycle of a USD 15y5y/20y10y delta-hedged flattener (Citi, 10 May, 30 Sep, 4 Oct, 16 Oct, 5 Dec 2019): entry 9 May 2019, 50K DV01, $148.8mn 15y5y vs $90.3mn 20y10y at -11.8bp (curve at its upper bound since 2002), carry -0.31bp/yr, BE 1.3bp vs RV 3.0bp (BE/RV 0.42), hedge every 20bp.
  30 Sep: -10.59bp, P&L about +$70K despite steepening (convexity). 16 Oct reweight: notionals $149.5mn / $81.97mn, 20y10y raised to $84mn for an empirical beta of 1.025 (the spread had become directional: steepening in rallies, flattening in sell-offs, attributed to insurer flows) rather than closing the trade, delta-hedging the 20y10y leg at the same beta.
  5 Dec exit at -12.5bp: P&L about $187K at mid, $155K net of costs, closed because carry worsened to as low as -2bp/yr and BE/RV rose to 0.8 even though the thesis was unchanged. Main risk: VA/insurer receiving in risk-off (stocks down, insurers receive about 20y, curve steeper). A 26 Mar 2020 repeat (-5.21bp, z 4.21) was not initiated: poor liquidity and wide bid-offer.
- GBP 15y10y/25y10y delta-hedged flattener: 24-30 Sep 2019 -3.3/-3.5bp, z 2.1-2.4, carry +0.91bp, BE 0 ("effectively a free long convexity buy"); entered Jan 2020 at 50K DV01 hedged every 25bp, closed 26 Mar 2020 for GBP 445K net of costs, about 115K from the curve move and 330K from convexity (about 3/4 in a vol spike), because BoE QE had flattened the curve and supply could re-steepen it.
- Systematic sigma_BE vs sigma_imp spec (own research specification, Oct 2026): side +1 = DV01-neutral flattener on a forward strip (receive later start, pay earlier) = long curve gamma, enter when `sigma_BE < sigma_imp`; side -1 = steepener = short curve gamma, enter when `sigma_BE > sigma_imp`.
  Require duration difference `dD >= 4.0` (small `dD` makes sigma_BE explode); persistence gate: share of the last 252 days with the same signed signal <= 0.6, otherwise treat as structural carry. In the belly the hump's term-premium roll-down dominates, so high sigma_BE there is a belly carry trade, not rich curve gamma.
  Compare carry/yr with theta/yr at matched gamma and horizon (comparing carry with premium makes sigma_BE look about sqrt(2) too high). Measure carry by repricing the aged package on a rolled curve (a running carry-and-roll field had the wrong rank order); a curve "translate" does not age a struck swap.
  USD map 2015-2026: 10y5y/15y5y sigma_BE > sigma_imp on 75-85% of days (persistent belly carry), 10y5y/20y5y and 10y10y/15y10y 15-36% (transient, genuine RV), 10y10y/20y10y near fair (92 vs 91bp, dD about 9.9), flattener side only for the very long forwards (below 1% of days). Implied vs realised on long forwards about 91 vs 61bp/yr (Oct 2026).
- EUR 30s50s (Citi Markets, EUR 30s50s steepener vs 5y10y vol, 27 Jul 2026): pay EUR 30s50s (100k bpv, -28.8bp) and buy a 5y10y straddle to "orthogonalise" against vol; expected vol return about -2bpv/yr partly offset by about +1bp/yr on the curve; long expiries (7-10y) about zero net carry, short expiries (1-2y) punitive (implied/realised above 100%).

## 3. Option-like non-linearity of "linear" slope trades

- Slope-vs-level parabola: locating the curve on its slope-on-level quadratic shows whether a flattener or steepener is convex proxy (J.P. Morgan, Drivers of cross currency basis, 11 Mar 2015, basis curve `y = 0.0072x^2 + 0.047x + 1.40`, R2 84%; Monthly Inflation Outlook 13 Aug 2026,
  5Yx5Y/15Yx15Y RPI `y = -329.63x^2 + 2137.6x - 3447.6`, R2 76%: concave, so a fall toward 3.00% flattens materially and the flattener is a convex proxy short). A PC1-neutral fly or slope can still be non-linear in the level (ING, 15 Jan 2020).
  Japan: life-insurer target yields gave linear trades an option-like payout near the 10y 0.75% / 30y 2% pivot (During 2021).
- Hedge the convexity of a vol-sensitive position with a weighted steepener: ED convexity adjustment "Blues" with a 0.74/-1.0 DV01 weighted steepener (calibrated pre-2008, relation broke at the lower bound), "Greens" with -1/1.18; steepener carry about +2bp/3m, "a more efficient hedge than buying vol" (Citi, Rates Vol Lab, 8 Jan 2018 and 15 May 2017).
- Curve vs swaption cost: a steepener with negative convexity is short vol; add positively convex trades (e.g. receive 20y5y/25y5y) to a steepener book (Nordea, EUR rates: The quiet game, 12 Aug 2025: at -9bp, target -15, stop -7, 12m carry+roll 3.4bp, ratio carry/vol 0.30).
