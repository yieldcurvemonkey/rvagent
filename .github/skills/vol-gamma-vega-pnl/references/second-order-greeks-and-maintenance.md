# Second-order Greeks, hedge-vol choice and book maintenance

Detail behind SKILL.md sections "Method 6-8". Units as in SKILL.md (normal vol in bp, cash greeks per bp).

## 1. Full P&L expansion and where the residual comes from
dP ~ Delta·dS + ½Gamma·dS² + Vega·dσ + ½Vomma·dσ² + Vanna·dS·dσ + (1/6)Speed·dS³ + (1/6)Ultima·dσ³ (Ade Rhodes, Trade Idea:
USD 3m2y Payer Skew Steepener, 8 Oct 2025). In the normal model with vol independent of the rate:
- Vomma = Vega·d²/σ with d = (F-K)/(σ√T): wings carry more vomma than ATM, ATM vomma is 0.
- Vanna = -Vega·d/(σ√T) is the standard Bachelier sensitivity of vega to the forward; ATM it is 0. Check sign by finite
  difference in your own pricer rather than trusting a convention (the P&L explain script reports vanna/volga together
  in `residual`).
- Drift: gamma turns into delta drift after a rate move, vomma into vega drift after a vol move, vanna into vega drift
  after a rate move. Re-flatten each with the ATM straddle (vega) or the swap (delta).
- Stochastic-vol extension of the delta-hedged increment: P&L = ½ΓS²((dS/S)² - σ̃²dt) + Vega·dσ + ½Volga·ξ²σ²dt +
  Vanna·σSρξdt. (Jacquier and Slaoui, Variance Dispersion and Correlation Swaps, working paper, undated)
- Backbone: implied vol is roughly the gamma-weighted average of instantaneous vol along paths from forward to strike,
  so it depends on the rate level. A constant-vol delta captures only the direct effect; the indirect effect (vol moves
  with the rate) is missed. Constrain SABR to the empirical backbone (ATM bp vol vs forward). Constant-vol BSM delta on
  bond-futures options also ignores CTD switches. (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022, Ch.16)
  When rates and vol have been positively correlated, a long-vega package that is short parallel shifts gets partial MTM
  protection in a sell-off. (Nomura, Derivative Focus: Erratum: Conditional Euribor bull flatteners, 19 Jun 2014)

## 2. Which vol to hedge at
- Market practice: hedge with the current market implied vol. Re-marking to a new vol gives instant vega P&L, a change in
  delta (vanna), a higher theta bill and lower gamma going forward; vega P&L can be locked in by selling the option.
  (Quantitative Finance Stack Exchange, Delta Hedging with fixed or floating IV, Oct 2015)
- Hold-to-expiry trade-off: the expected P&L is nearly independent of the hedge vol; the distribution is not. A higher
  hedge vol (more upfront vega P&L, higher theta, less gamma) does better when realised moves are evenly spread in time
  and size; a lower hedge vol (more gamma, lower theta) does better when large moves arrive near the strike close to expiry.
  Each spot hedge trade has zero expected value, so a hedge vol far from implied widens the distribution and makes it
  path-dependent. Verify by simulation (`gamma_pnl.py` `hedge_sim(hedge_sig=...)`). (QSE, Delta Hedging with fixed IV to
  get rid of vega, Jun 2017; QSE, Delta Hedging with fixed or floating IV, Oct 2015)
- Hedging at a fixed vol means the position is no longer marked to the market, which may collide with risk. At book level,
  an option whose vol is not re-marked makes portfolio delta wrong: "using the correct implied volatility for your delta is
  as important as using the correct spot price". You cannot remove vega with the underlying; that needs another
  vol-sensitive instrument. (QSE, Jun 2017, Oct 2015)
- Known RV > IV, two ways to book it: (1) re-mark to RV now, P&L = Vega·(RV - IV), then hedging at RV offsets theta;
  (2) keep the IV mark and hedge at IV, expected P&L ~ ½·$Gamma·(RV² - IV²), path-dependent. They are similar, not equal,
  because vega depends non-linearly on σ through d1. Numeric: pay 100c at IV = 2bp/day; RV 2.1bp/day gives 10c, RV 2.2bp/day
  gives 30c (non-linear). (QSE, Realizing the same PnL as Gamma Vs Vega, Jan 2022)
- Ex-ante vs ex-post: ½Γ·S²(σ_r² - σ_i²)dt is the average (ex-ante) P&L; the actual daily increment is
  ½Γ·S²((dS/S)² - σ_i²dt), the replication error vs a self-financing hedge. Attribute with realised squared returns per
  period, not averaged σ_r²; daily noise is large. Even with σ_r > σ_i the hedged P&L depends on where spot spends its time
  relative to the strike (largest on paths that oscillate around it). (QSE, Delta hedge value formula, Mar 2017; QSE,
  Continuous delta hedge formula, Mar 2017)
- A delta-hedged long option can lose more than the premium: a 3m 37 call bought at 0.05 with spot at 35, spot sideways, then
  a jump to 36.99 into expiry: the call expires worthless and the hedge also loses. (QSE, Delta Hedging with fixed or
  floating IV, Oct 2015)

## 3. Maintaining a vol package (skew package example)
Package: long $100mm 3m2y payer 50bp OTM, short $100mm 50bp OTM receiver, long $9.71mm ATM straddle, delta-hedged with a
3m2y swap. Vega-neutral condition: V_payer(long) - V_receiver(short) + V_ATM(long) ~ 0; solve for the straddle notional.
Delta hedge: N_swap = -(N_p·Δ_payer + N_r·Δ_receiver + N_str·Δ_ATM)/DV01_swap. Scenario P&L: parallel vol +/-10 abpvs
gives +/-$3,240 (about neutral); payer +10 / receiver -10 gives +$37,840; the reverse -$31,360. Hypothetical vomma drift:
payer vega +40 vomma +2.0, receiver vega -41 vomma -1.4, straddle vega +1 vomma +0.3: net vega 0, net vomma 0.9; vols +5
abpvs give ½·0.9·5² = +11.25 and new net vega 0.9·5 = +4.5, so trim the straddle. Rebalance rules used: resize the
straddle or swap when |net vega drift| exceeds 5 abpvs or the net rate move exceeds 5bp; keep wings symmetric at +/-50bp
by re-striking when a wing drifts more than 5bp; after a +/-5bp shift re-centre the wings and refresh the ATM hedge or
vanna builds vega; for larger drifts roll to ATMF. A long ATM straddle's P&L is independent of skew but the ATM-wing
curvature matters; a risk reversal plus straddle can be vega-neutral and still have positive net vomma, gaining from
a broad richening of vol. (Ade Rhodes, 8 Oct 2025)
Skew trades: with 0.2 vol-point bid/offer per leg, daily unwind and restart wipes out the P&L; if you do not roll, gamma
speed turns the position into a leveraged directional bet. Theta can be split slice by slice into gamma, vanna and volga
parts to derive implied break-even levels. (QSE, Bergomi: Skew arbitrage, Nov 2020)

## 4. Option-spread and listed-option greeks
- Euribor option spread (5,000 lots, EUR 25/tick/lot): sell a Mar-25 Euribor call struck 99.875, buy a mid-curve call struck 99.375, net debit 15.5 ticks (EUR
  1.937mn). Columns premium / delta per bp / vega per bp / theta per day / gamma per bp² (EUR): short leg -312,500 /
  52,180 / -37,353 / 1,305 / -5,531; long leg 2,250,000 / -81,763 / 43,311 / -4,111 / 1,763; total 1,937,500 / -29,584 /
  5,958 / -2,806 / -3,768: long vega, short gamma, short theta, modestly short parallel shifts. A full-rate model not
  calibrated to the far contract gives different greeks; in a Bachelier model a spread's delta and gamma depend on the
  leg correlation. The original note mis-stated risks for a 1000-lot trade: check lot size, greeks and notional agree.
  (Nomura, Erratum: Conditional Euribor bull flatteners, 19 Jun 2014)
- SOFR cap/floor hedged with futures options: floating-strike adjustment S = (S_t - A·n_k/n_t)·n_t/(n_t - n_k) (n_k known
  days, A average of known SOFR, n_t total days, S_t = 100 - strike). Unlike plain delta hedging, skew matters and skew
  exposure can become substantial near expiry; the adjusted strike diverges near expiry like ATM gamma. Daily-floor premium
  vs the whole-period floor was 44% (one pure-jump meeting), 72% (two meetings), 129% (a certain cut then hike); under
  diffusion overhedge by about 10%. In the reference month 1m SOFR futures options become arithmetic American Asians and 3m SOFR futures options
  stop before the reference quarter, so a cap hedger can only delta-hedge with the front future and stays exposed to
  vol. A pure-jump process can value an option at 0 where diffusion gives a positive value: stress with alternative
  processes before selling optionality cheaply. (Huggins and Schaller, SOFR Futures and Options, 2022, Ch.5 and 10)
- Variance swap greeks (transferable maths): Gamma = 2/(S²T), Theta = -σ²/T, vega_σ = 2στ/T, vega_σ² = τ/T; constant cash gamma;
  a gamma swap (weighted by S_t/S_0) has constant share gamma and is jump-robust. Vanillas far from ATM are weak variance
  hedges (flat sensitivity, large notionals, high costs). (Jacquier and Slaoui, working paper, undated; Shafer and Vovk,
  Probability and Finance, 2001, Part 3)

## 5. Gamma and vega sectors, STIR options
Short expiries (high gamma, very negative theta) are driven by realised moves: delta-hedge. Long expiries (low gamma, high
vega) are driven by changes in implied vol: delta hedging barely matters. Swaptions: gamma sector to about 6M (sometimes 1Y),
vega sector from about 3Y expiry, about 2Y grey, market-specific and often tilted to the right. JPY PCA: at 2Y expiry only
underlyings above 5Y are clearly vega, at 5Y expiry everything is vega; tilted border about 4Y expiry for 1Y swaps, 3Y for 2Y
swaps, 2Y for 5Y swaps. STIR options: about 3M expiry high gamma (buy and delta-hedge if realised > implied); about 5Y expiry
low gamma, high vega, suited to views on future implied vol. Trade types on one underlying: level of the underlying
(unhedged), level of realised vol (delta-hedged), level of implied vol (long expiry); with two or more underlyings, a
delta-hedged straddle spread trades the realised-vol curve against the implied-vol curve, a long-expiry spread trades the
future implied curve against the current one. Vega-sector caveats: large underlying moves over long horizons break the
"no delta hedge" premise; theta differences between legs matter on long holds. (Huggins and Schaller, Fixed Income Relative
Value Analysis, 2nd ed., 2024, Ch.19; Huggins and Schaller, SOFR Futures and Options, 2022, Ch.5)
JPY examples: 5Y swaption implied 19bp vs recent realised 16bp (18 Jun 2012), implied near the historical minimum of
realised, as a cheap shock hedge. Realised/implied (bp) 3M expiry: 2Y 7/16, 3Y 9/15.5, 5Y 16/19, 10Y 27/34; buying 3M5Y and
selling 3M2Y delta-hedged straddles: realised 5Y-2Y spread ranged 6-27bp over 2007-12 vs implied 3bp, "would always have made
money (on average 10bp)"; sell 1.23 2Y straddles per 5Y straddle to be neutral to the realised-vol level (derivation not
given). (Huggins and Schaller, FI RV Analysis, 2024, Ch.19)
Separating the two: long gamma with flat vega = buy short-dated and sell long-dated options against them for
vega (calendar); long vega with flat gamma = buy long-dated and hedge the gamma with short-dated. A calendar of long short-dated ATM and short
longer-dated ATM is long gamma, short vega: it profits if realised rises before the short expiry or implied falls.
(QSE, Long Gamma vs Vega, Feb 2018; QSE, Vol, Gamma, Vega -- essentially all the same, Aug 2021)

## 6. Calendars are not forward vol; forward-vol arithmetic
- Vanilla calendars have different gamma profiles, so they are not pure forward vol: spot 550, sell Sep 550 straddle at 66,
  buy Dec 550 at 94 (28 spread, flat 30% IV); after a rally to 675, Sep = 125 intrinsic and Dec 132, so the spread is 7;
  with IV +20% Dec is 139, spread 14. A forward-vol agreement (FVA) is pure vega: strike set at the look date, practically no
  delta/gamma/theta/skew. A short FVA is dangerous in gaps: it becomes short an ATM option just as vol explodes. (Credit
  Suisse, The Convexity Maven: Building a Better Volatility Mousetrap, 6 Sep 2012)
- Forward vol: (T2-T1)σ_f² = (T2-T0)σ_{T2}² - (T1-T0)σ_{T1}². Example: buy 1y 2s10s straddles at 34nv, sell 6m 5s10s at
  21.5nv with 1.7x notional: implied 6m-forward-6m vol = √(2·34² - (1.7·21.5)²) = 31.2nv. FVA 6m1y10y: 100k/nv, vols 6m1y 37,
  6m11y 99, 1y10y 100, 18m10y 99, midcurve 107 -> buy 160k/nv of 18m10y, sell 60k/nv of midcurve; use vega-weighted, not
  notional-neutral. Forward at 95nv vs spot 100. (Credit Suisse, The FVA: Forward Volatility Agreement, 27 Aug 2013; Citi,
  Buying vol for less, 25 Sep 2019)
- Expiry-curve and vol-curve steepeners (3Mx2Y/1Yx2Y, 3Mx2Y/3Mx10Y) are low-beta short-gamma proxies with less jump
  exposure; avoid them when the expiry curves are near medium-term highs. Vol-curve steepener = long vega, flat gamma:
  buy 3y10y/5y10y vs gamma-weighted sale of 3m10y/6m10y. (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026;
  Merrill Lynch, RateLab: Professional Javelin Catching, 16 Feb 2007)
