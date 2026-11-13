# Worked examples: skew and tail hedging

Dated, sourced numbers behind [SKILL.md](../SKILL.md). They are historical illustrations of method and magnitudes, not current
levels or recommendations. Normal vol (nv, bp/yr) unless stated. Contract and market levels are as published.

## 1. Positive-carry long-dated OTM payer (static roll-up)

Method: price a fixed-strike payer at each expiry on today's surface; the roll is the price at shorter expiry minus price at
longer expiry. Roll-up exists when the long forward curve is flat/inverted and the vol surface is inverted.

**Oct 2008** (spot 10y swap 4.41%; 10y tail; 7.25% strike payer = +300bp OTM) (Merrill Lynch, RateLab: The "Positive Carry" Hedge, 31 Oct 2008):

| Expiry | ATM nv | +300 OTM nv | Fwd | 7.25% payer (bp) |
|---|---|---|---|---|
| 2y | 130 | 138 | 4.88% | 80 |
| 3y | 125 | 133 | 4.94% | 137 |
| 4y | 117 | 125 | 4.93% | 161 |
| 5y | 110 | 118 | 4.88% | 171 |
| 6y | 104 | 113 | 4.79% | 174 |
| 7y | 98 | 108 | 4.69% | 168 |
| 8y | 93 | 103 | 4.58% | 158 |
| 9y | 88 | 99 | 4.48% | 149 |
| 10y | 83 | 95 | 4.39% | 139 |

Buy the 10y10y 7.25% payer at 139bp; under unchanged markets it rolls to 171bp after 5y (~+6.5bp/yr). Context: 2s10s +169bp yet
the 10y swap 10y forward ~2bp below spot; 1y10y straddle 141nv vs 10y10y 83nv. The +300 OTM skew stayed ~8nv while ATM fell with
expiry, so relative skew rises with expiry.
**Outcome:** the 6% strike 10y10y payer bought 31 Oct 2008 at 209bp (projected roll-up 265bp over 3y) marked ~475bp a year later
as a 9y10y although spot 10y swap fell ~60bp (4.33% -> 3.73%): the gain came from vol and skew (BAS/ML, No Bad Bonds, 27 Oct 2009).

**Dec 2010 reprise** (spot 10y 3.11%, strike 6.00%) (BofA Merrill Lynch, The Positive Carry Hedge, A Reprise, 8 Dec 2010):

| Expiry | ATM nv | OTM nv | Fwd | Price (bp) |
|---|---|---|---|---|
| 2y | 111 | 136 | 4.04% | 130 |
| 3y | 110 | 129 | 4.42% | 246 |
| 4y | 109 | 122 | 4.69% | 344 |
| 5y | 107 | 117 | 4.86% | 410 |
| 6y | 104 | 112 | 4.95% | 441 |
| 7y | 101 | 108 | 4.99% | 459 |
| 8y | 98 | 104 | 5.01% | 454 |
| 9y | 95 | 100 | 4.99% | 445 |
| 10y | 92 | 97 | 4.97% | 433 |

4y->3y roll costs 98bp (28%). Buy the 10y10y 6.00% payer at 433bp; static roll over 3y to 459bp = +26bp. 10y options sold at a 17%
discount to 3y (92 vs 111nv per the source text, which puts the surface peak at the 3y expiry; the 2y/3y ATM cells in the table above may be transposed - use 111 for 3y). Risks: wide bid/offer ("a Princely bid/offer"), long vega (MOVE 103 = its 20y average), a Japan-type
scenario. A macro 2-3y investment, not RV. Spot vs forward vol: prefer spot long-dated vol for a hawkish tail.

## 2. Selling rich payer skew with ladders and 1x2s

**MBS skew ladder, Apr 2013** (Credit Suisse, Skewered by Skew, 17 Apr 2013): see SKILL.md example B. Vol-ratio variant: buy 100mm 18m5y
payer K 2.25% (79nv) vs sell 53mm 18m10y payer K 3.26% (88nv), zero cost at a 90% vol ratio; pre-ZIRP 6m5y/6m10y vol ratio averaged
105%, rarely < 1.00 (then 70%); target >= 10nv vega profit.

**Costless 1x2 illustration, Oct 2009** (BAS/ML, 27 Oct 2009): a year earlier buy +200bp 5y10y payer (K 6.75%), sell 2x K 7.85%, zero
cost, base 4.75%, terminal BE 8.95% (420bp range). Same structure at the later date: BE 11.35% (660bp, 57% wider) - a direct read of
skew steepening. Recommended 5y10y ladder at 4.90% forward: buy 100mm K 6.25% (458bp OTM, 138nv, 25.0% yield vol), sell 100mm K 7.75%
(280bp, 157nv, 25.5%), sell 100mm K 9.50% (178bp, 181nv, 26.4%). Delta ~0, gamma short ~2mm 1y10y straddles, vega short ~30mm ATM
5y10y straddles. Carry +$400k/yr on a flat roll; instant +200bp = -$500k; +200bp over 1y = +$600k; best case +200bp over a year with
skew rotating to flat 140nv = +$3.5mm; +500bp to 10% over 2y with a flat 150nv surface = zero. Diagnostic: 5y10y forward 4.88% a year
earlier vs 4.87% now, ATM vols ~11% higher but +300 OTM vols ~33% higher (anomalous: skew should compress as vol rises); 5y10y ATM
122nv (7.6bp/day) ~2 sd above the 15y average 98, +300 payer 159nv.
Why a short-skew ladder wins: (1) roll-up carry from heavier decay of high-skew OTM payers; (2) CMS-cap holders take profit after
+200-300bp, selling vol; (3) MBS hedging flips from extension to contraction and buys OTM receivers (skew inverts).
CMS-cap mechanics: a 6% bond earns $0.0743/bp at 6.00-6.01% but $0.0619/bp above 8% (DV01 falls as rates rise), so a dealer who sells
a 6% single-look CMS cap is "selling an entire string of options struck from 6% to +20%" and must buy a strip of OTM payers.

**Controlled-inflation payer ladder, Sep 2013** (Credit Suisse, How High is High?, 17 Sep 2013): buy 5y5y payer 4.85%, sell 5.60%, sell
6.90%, 100mm each, zero cost; ITM above 4.85%, gains capped at 5.60%, fade from 6.90%, gone at 7.65%, unlimited loss above. View: the
10y does not settle above a 7% handle. 5y5y ~4.50%. Deflation hedge: buy 5y10y receiver 3.50%, sell 5y10y payer 6.25%, zero cost;
favoured when the curve is steep, implied vol high and payer skew elevated.

**Citi 2026 structures** (Citi, US Rates Weekly, 21 Aug 2026; European Rates Strategy 20 Aug 2026; Morning Call 12 Aug 2026; European
Rates Weekly 1 Oct 2026):
- 3m2y receiver ladder, costless: $200mm ATMF 4.20%, sell A-17 and A-34; DV01 $37,846, vega -$5.3k; target $600k, stop -$300k.
- Payer calendar: sell 20mm 3m30y A+30bp payers, buy 20mm 9m30y A+30/A+60 1x1 payer spreads; net 2bp running premium; 3m30y ATMF
  4.575%, 9m30y 4.586%; net vega -$2,173, DV01 $32k; carry ~+2.7bp running if unchanged; breakeven ~42bp selloff over 3m; target
  $300k, stop -$200k.
- EUR 3m1y 1x2s (Aug 2026): payer skew rich vs receiver. A 1x2 payer spread loses at expiry only if 1s sells off 56bp (~2 more 25bp
  hikes); a 1x2 receiver spread loses after only a 16bp rally. Balance-of-risk gauge P - R (distance of the costless short strike,
  payer minus receiver, bp from ATMF): payer 1x2 distances ~20-45bp, receiver ~12-27bp; P-R ~16-17bp late March, ~2bp early July, ~7-8bp
  after the 7 Jul vol spike (3m1y vol +17 nv bp on 8 Jul), ~6bp mid-Aug. Long 3m1y payer vs 1x1 1y1y payer carried -5.7bp ex-costs; stop on
  the vol spread widened from -10 to -12bpv with the rationale "balance of risk still elevated". Sell 1x1.5 3m1y payer spreads, costless
  (10 Sep 2026): risk = a moderate gradual selloff.
- Other costless ratio trades: CMS cap ladder (buy $300mm 6m 10s/2s ATMF CMS caps, sell $300mm each of +11bp and +22bp OTM; target $330k,
  stop -$200k; risk = sharp near-term steepening); 1x2 put spread on a short-term-rate future for a 2.5c credit (target $625k, stop -$300k;
  costless version profits down to a 77bp selloff, max at 37.5bp) (Citi, Global Macro Trade Ideas Radar, 13 Aug 2026).

**Front-end receiver-skew sale, Mar 2018** (Citi Rates Vol Lab, The art of gamma hedging, 12 Mar 2018): buy $500mn 6m1y1y ATMF-15bp
receivers, sell $1bn ATMF-30bp; take-in $200K; loses terminally only if 1y1y < 2.38% at expiry; rationale: front-end receiver skew rich vs
payer skew while ~4.5 hikes were priced over 3y; 6m1y1y rich on PCA (+2.7, z 1.5).

## 3. Contingent and conditional tail hedges

- **Hybrid payer spread, Jun 2019** (Convexity Maven, For Propeller Heads Only, 17 Jun 2019): 6m payer on 2y costs ~46c vs 31c roll-up carry
  on paying 6m-forward 2y (forward 1.696%, 16.2bp below spot 1.858%). ATM/OTM payer spread 26c (+25bp short leg) or 36c (+50bp). Buy
  1.696% / sell 2.196% payers contingent on SPX >= 5% lower at expiry: cost falls 78% to 8c; if rates unchanged and SPX -5% (to 2743) payout
  3.75x. Compare premium with the carry being protected; the trade is a sale of stock-bond correlation.
- **SPX-contingent 30y payer, Sep 2026** (Citi Rates Vol Lab, 14 Sep 2026): SKILL.md example E. Evidence: 1m realized correlation of daily 30y
  yield changes vs SPX returns centres near 0% and inversely tracks the 3m change in the 30y yield; selloffs coincide with more negative
  correlation. Target $500k, stop -$147k. Opposite-side hybrid: 1y CMS 30s/5s curve cap contingent on SPX > 110% at 5.05c.
- **Receiver fly, Jan 2020** (JPM, The return of convexity hedging, 31 Jan 2020): $100mn 1Yx10Y 20-delta receivers (88c) vs $258mn 1Yx2Y
  25-delta receivers (22.7c) and $11.2mn 1Yx30Y 25-delta; term-premium tail hedge; risk-off week 3M expiries +7.1/7.4/6.5/6.3 abp on
  2/5/10/30Y tails with upper-left outperforming.
- **Conditional flies:** costless 3m 10s20s30s payer fly (notionals 89.0/100/37.2) to be short while protected in a rally; 3m 2s3s5s receiver
  fly with positive carry and terminal protection (74.5/100/30.6; spot -2.4, fwd -2.0, > 2 sigma cheap on 3m z) (Citi Rates Vol Lab, Dec 2016,
  Jan 2017).
- **Cross-asset cheaper hedge, Jan 2020** (Citi Rates Vol Lab, In search of cheap vol, 17 Jan 2020): buy $30mn 6m USDJPY 108/105 put spreads vs
  sell $50mn 6m10y payers ATMF+45bp (2.2%), net cost $35K; rates vol rich to FX vol; risk: 10y above 2.2% at expiry.
- **Liability-manager collar, Feb 2010** (BofA Merrill Lynch, "Look Right...", 19 Feb 2010): buy $20bn 5y20y 4.00% receiver, sell $20bn
  5y20y 7.00% payer, zero cost; a near-identical event in late 2004 hurt dealers short long-dated OTM receivers. Tail hedge core:
  long 5% and 10% delta calls on 15-20y rates (bond-futures calls) as a bull-flattener hedge. Skew read then: 1y10y +/-100bp put-minus-call
  (bond language: put = payer, call = receiver, i.e. RR as defined here) RR fell 33 -> 22 nv while rates rose ~70bp, 15-delta futures put-call skew 20% -> 12% via OTM call vol rising.
- **Long-end receiver skew vs bull-flattening, May 2021** (BNP Paribas, EUR curve convexity, 25 May 2021): delta-hedged long low-strike 30y
  receiver vs short high-strike 30y payer (long receiver skew); 30y payer skew above receiver read as "not yet near a level where bear-flattening".

## 4. Tail-strike flows and CTD-switch convexity

**Who buys the tail** (MS, Investors Are Paying for Protection Against 6% Rates, 2 Jul 2026): swaption prints with strike >= 6% (typically
> 200bp above forwards; 10y SOFR in a 3.2-4.2% range since 2024); classify buy / sell / uncertain; drop likely packages; aggregate by
underlying DV01. Regimes: 2024 quiet; Jan 2025-Apr 2026 net sellers (selling comfortable once rates stabilised; legacy callable exposure
had linked rates to long-dated vega); from May 2026 net buyers. Flow DV01 peaks ($mm): selling 20y10y 6.5, 10y10y 5.8, 1y5y 4.1, 1y10y 3.3,
5y5y 2.8; buying 3y10y 3.9, 2y10y 2.2, 5y20y 1.2, 10y10y 1.2. Selling clustered at 6%, buying spread out with 7% largest. "Selling
high-strike swaptions is better viewed as a volatility trade than a macro view that rates cannot exceed 6%." Trades: 1y1y F/F+25/F+50 payer
ladder costless; 3m30y F/F+25 payer spread 135c; 6m5y F-25 receiver 60c. Skew Signal Monitor: 3m10y 21-day skew change mapped to a duration
position (flipped to long at 15% of max allocation).

**CTD-switch convexity** (MS, Buy Higher Rates Protection at a 30% Discount, 27 Aug 2026): in a ~50bp parallel selloff the Dec-26 20y futures
CTD switches from the 5% May-45s to the 1.375% Aug-50s and futures duration rises ~47% (CTD forward DV01 per CF x 100 from ~12.3 to ~18;
spot duration per CF: May-45s 13.24, 4.75% Nov-43s 12.74, 1.25% May-50s 20.36, 1.375% Aug-50s 20.12). Method: simulate PC1 (level) and
PC2 (slope) in +/-4 sd; CTD per scenario; probability-weight futures DV01; repo = interpolated SOFR + 15bp. Replicate short 1 future =
short $115,075 4.75% Nov-43s (CF-sized) + payer swaptions fitted to the residual payoff (long ATMF+20bp $17,502; long ATMF+30bp $30,596);
value 12.4 ticks vs Nov-43 net basis ~8.7 ticks = ~30% cheap before other delivery options. Three conditions: yields near the 6%
notional coupon, wide coupon dispersion (~5% originals vs ~1.5% 2020-issued), rich payer skew. Net basis stayed below quality-option value
(model peak ~14 ticks vs net basis ~8). Trade: buy a 106 put at 51/64, expiry 20 Nov 2026 (risk: not enough selloff); alternatively long 5%
May-45s vs short futures CF-weighted, gross basis 17.02 ticks, net 5.52 at 3.95% term repo. Caveats: current-CTD approximation understates
duration after a switch; swaption theta decays but the switch payoff does not; leaves swap-spread risk. JPM (US IRD, 2 Oct 2026): delivery
option ~17/32 (Dec-26 20y), ~6/32 (ultra); sort basket by BPV/CF, in a selloff/steepening the CTD moves up the table; near the 6% notional
coupon (cut from 8% in 2000) all bonds look near-CTD.

**Board vs swaption rows** (Citi Rates Vol Lab, Jun 2023, Oct 2026, Sep 2019): 10y-note Jun-23 114.00 put (strike yield 3.68%) vs
costless payer 3.43%: strike spread -24.6bp vs invoice spread -29.8bp; put vol 121.8 vs payer 127.5 (0.96). 5y-note 109.00 put (3.76%) vs
payer 3.56%: strike spread -19.6, invoice -25.0; put 142.8 vs payer 142.5. Oct 2026 long-bond put: invoice -38.4bp, costless strike spread
-41.0bp; put vol 122.6 vs payer 116.5 (1.05). Calls vs receivers (Sep 2019): call/receiver vol ratio 0.87-0.90. The source defines the bp
pick-up as costless strike spread minus invoice spread but its printed numbers are consistent with the opposite sign; fix your own sign and
check on one row before use. Board/swaption vol ratios 2026: 5y 1.01, 10y 1.03, long bond 1.14, ultra 1.17.

## 5. Value of gamma, jumps and other numeric checks

- **Value of gamma with smile** (Darbyshire, 2022): gamma P&L 1/2 G (dr)^2, expectation 1/2 G sigma_N^2 (add mu^2 if mean move non-zero).
  Smile-aware value = up-front premium of a strip of OTM payers (right of ATM) and receivers (left) replicating the convex payoff; equals
  1/2 G sigma^2 with no smile and rises with kurtosis; too few strikes overestimates. Single-figure IRS gamma: G ~ -(h+i) x delta/10,000
  per bp (5Y5Y: 16; delta $50,000 pv01 -> -$80), refined DF-weighted -$79.8.
- **Policy-step underlyings** (Huggins & Schaller, 2022): simulated 100-strike SOFR call payoff (annualised bp) by P(+25bp) and diffusion SD:
  SD 1% -> 1.9 (0% hike) to 1.0 (100%); SD 2% -> 6.3 to 4.3; SD 5% -> 20.2 to 16.6; pure jump with no cut = 0. Daily-floor premium vs a
  whole-period floor under jumps: 44%, 72%, 129%. Rule of thumb: over-hedge ~10% under diffusion; skew exposure becomes substantial near expiry in
  strike-adjusted hedges.
- **Straddle breakevens to policy outcomes** (Citi Markets, 21 Aug 2026): compare straddle breakevens with futures settlement under each
  discrete outcome; if breakevens sit at the outcomes, the straddle is fair for a binary event. Short-dated realized vs implied breakeven: beat 3
  of 5 days by an average 1.3 ticks = "tough to be long premium".
- **Option-implied VaR bound** (Shafer & Vovk, 2001): one unit plus a put struck c costing P(0): VaR <= S(0) - c + P(0)/alpha. Far-OTM vanillas are
  weak variance hedges (flat sensitivity, large notionals).
- **Zero-strike receiver** (JPM, 28 Feb 2020): Feb 2020 ~12% market-implied vs ~9% normal-implied probability of 2y swap < 0 within a year; the gap
  not rising as rates fell suggests NIRP risk may cap in option pricing.
