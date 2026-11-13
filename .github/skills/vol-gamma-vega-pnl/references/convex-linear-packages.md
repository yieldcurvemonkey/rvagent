# Gamma in linear products and delta-hedged packages

Detail behind SKILL.md section "Linear products". Swaps, bonds, FRAs and curve packages have gamma but no premium and no
theta line: the "theta" that pays for the gamma is carry and roll. Same identity, different bookkeeping.

## 1. Gamma of a linear position
- Definition: gamma is the change of delta per 1bp: P ~ (dP/dr)·dr + ½(d²P/dr²)·dr². Receiving fixed has positive gamma,
  paying negative; longer tenor and later forward start mean more gamma. Two sources: the level of rates (lower rates, higher
  discount factors) and MTM (an off-market swap embeds an annuity). (Darbyshire, Pricing and Trading Interest Rate
  Derivatives, 3rd ed., 2022, Ch.21)
- One cash flow: PV = e^(-rt), delta = -t·e^(-rt), gamma = t²·e^(-rt), so gamma/delta is proportional to t and independent
  of r. Approximately true for swaps and bonds: longer instruments are more convex, convexity is about constant as rates
  move, and it decays linearly with time. (Citi, A Holistic Approach to Convexity Across Fixed Income, Jun 2022)
- Par IRS gamma rule of thumb: G ~ -(1+i)/10,000 · S for a par swap of tenor i years, S = pv01; forward swap starting at h and ending at i years:
  G ~ -(1+h+i)/10,000 · S (this reproduces the printed 8, 16, 41, 81 for 2y3y, 5y5y, 10y20y, 30y20y; it is 2 x the average payment time).
  Example: 5y5y (h=5, i=10) with delta $50,000: G ~ -16 x 50,000/10,000 = -$80 of pv01 per bp (DF-weighted
  version -$79.8). S is the signed pv01 in the source convention (positive for pay-fixed, so the receiver's gamma comes out positive). (Darbyshire, Pricing and Trading
  IRDs, 3rd ed., 2022, Ch.22 tail)
- Cross-gamma is symmetric. A first-order hedge with a different product type leaves gamma unhedged and the leak is only
  visible in scenarios. Single-figure gamma = sum of all delta/delta cross-gammas and assumes a parallel move. For a
  curve view use curve gamma: anchor one tenor and twist the wings by -/+0.5bp; the P&L change is the steepener
  position and the change in dv01 is the curve gamma. Example: +100k dv01 2s30s with curve gamma -5k leaves +150k after a
  10bp inversion. (Darbyshire, IRDs, Ch.21-22; Quantitative Finance Stack Exchange, How to measure
  Steepener/Flattener/Butterfly sensitivity, 2021)
- Compute gamma by bump-and-reprice, never from bucketed linear risk: second differences [PV(r+e) - 2PV(r) + PV(r-e)]/e^2
  (full partial-gamma matrices need O(N²) revaluations, so use parallel or PCA-factor gamma). (MIT OpenCourseWare 18.642,
  Lecture 7: Linear Rates Models, 26 Sep 2024; Hull, Options, Futures, and Other Derivatives, 9th ed., Ch.31)
- Value of gamma: E[P&L] = ½·G·σ_N²·T (add μ² if a drift such as roll-down is assumed). Matching strip of OTM payers (right
  of ATM) and receivers (left) values it consistently; too few strikes overstate it, a smile raises it, and short gamma
  "tends to have a higher cost than initially presumed". (Darbyshire, IRDs, Ch.22 tail, Ch.23)
- Second-order expected P&L and Sharpe: E[P] = S'mu + ½tr(GQ) + ½mu'G mu; Var[P] = S'QS + ½tr(GQGQ) + mu'GQGmu + 2S'QGmu
  for dx ~ N(mu, Q). Rank trades on roll-down over vol of P&L including gamma, not roll-down over vol of the spread (the
  first-order matrix is a "false lure"); Sharpe above 1.0 is "reasonably attractive". EUR Aug 2016 example: gamma per
  10,000 pv01: 2y3y 8, 5y5y 11 (printed; the rule gives 16), 10y20y 41, 30y20y 81; with gamma, pay 10y20y / receive 2y3y goes from +0.25 to -0.01.
  (Darbyshire, IRDs, Ch.23)

## 2. Value of convexity and gamma decay
- Constant gamma: E[P&L] = ½·Gamma·(σ√T)². SOFR example (27 Jul 2023): receive the Jun-25 IMM to Sep-25 SOFR swap,
  notional 1,133,694,000, fixed 4.66632%, delta $25k/bp hedged with 1,000 short Jun-25 3m SOFR futures; swap gamma $12.2 per bp, futures
  gamma 0; normal vol 139.38bp from a 96.375 call at 0.75; expected P&L = ½·(140·√2)²·12.2 ~ $240k = 9.6bp. With gamma
  decaying (12.2 to about 7.0 after one year) the value is about $150k or 6bp, closer to market estimates: ignoring decay
  overstates by about 60%. Using the script's linear decay to 1.8 at T = 2 gives $136k (5.4bp), the same order.
  (Quantitative Finance Stack Exchange, Why are FRA/futures convexity adjustments necessary, answer updated 27 Jul 2023)
- Bond analogue: value ~ ½·Cx·Vol(dy)², vol in bp (normal). 30y zero at 8% priced $9.50; plus/minus 200bp gives $5.40 and
  $17.00, mean $11.20, so $1.70 of convexity value. Fig. 9 (1 Sep 1995): 10y par convexity value 0.27 of a 7.21%
  convexity-adjusted return; 30y par 0.88 (7.55%); 30y zero 2.53 (8.46%), about 30% of its expected return. Barbell vs
  bullet is a long straddle: give-up 71bp (0.53·6.67 + 0.47·5.73 - 6.94), breakevens an 11bp 10s30s flattening or a
  138bp parallel shift, but about 99% of P&L variance is reshaping and over 1980-94 the pickup rarely covered the yield
  give-up. (Salomon Brothers, Understanding the Yield Curve Part 5: Convexity Bias and the Yield Curve, Sep 1995)
- Static vs dynamic hedge are two different vol bets: a horizon-duration-matched, never rebalanced barbell-bullet is a
  held straddle (P&L depends on start and end yields); one rebalanced often is a delta-hedged straddle (P&L depends on
  realised vol along the path, positive if realised exceeds the initial implied even when yields end unchanged).
  (Salomon Brothers, Ilmanen, Sep 1995)
- Hedged bond = long straddle: DV01-neutral long bond / short futures pays the net basis, which decays as futures converge,
  and gains if yields move enough to switch the CTD; the seller of the basis has sold an option on rate vol. Options on bond
  futures expire about a month before the futures' last trading day, a vega/horizon mismatch. (Burghardt, Belton, Lane,
  Papa, The Treasury Bond Basis, 3rd ed., 2005, Ch.2, 5, 7)

## 3. Futures vs swap and FRA convexity as gamma
- Mechanism is risk-based, not margin reinvestment. FRA payer settlement P = v·N·d·(r-R)/(1+d·r); the futures hedge has
  constant risk d·N~ per bp, the FRA's risk varies with r and with the discount term. A paid FRA hedged with bought futures
  must buy more FRA as rates rise and sell as they fall, losing in proportion to vol; FRA rate = futures rate - CA; the
  edge belongs to the short-futures side. Most of the convexity comes from the OIS discount term. (Quantitative Finance
  Stack Exchange, Why are FRA/futures convexity adjustments necessary, 2019-2025)
- CME example: receive $100mm 2y SOFR IMM swap at 3.3304% vs short 779 3m SOFR futures ($25/bp each). Net P&L for rates -10/-25/-50/
  -100bp: +253/+1,451/+5,638/+22,292; for +10/+25/+50/+100: +182/+1,269/+5,241/+21,226. At -100bp DV01 moves $19,480 to
  $19,921 and the hedge from 779 to 797 contracts; linear approximation ½·18·100·25 = $22,500. Receive fixed + short
  futures = long convexity (profits either way); pay fixed + long futures = short convexity. Growth is non-linear and
  assumes parallel moves. (CME Group, Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures, 4 Jun 2025)
- Convexity adjustment as short vol: CA = SOFR futures rate - matched FRA/forward rate; holding the FRA against the
  futures is like holding an option against its premium; held to maturity, P&L is realised moves against the breakeven
  embedded in the CA. A short CA position (buy the futures pack, pay the forward swap) is a short delta-hedged straddle:
  E[P&L] = E[integral of (T - t)·(σ_implied²(t) - σ_realised²(t)) dt] in bp of yield, so implied/realised of the CA is the
  analogue of premium over gamma breakeven; roll-down plays theta; MTM/PAI flows play delta-hedging losses. (Citi, Left-side
  vols' outperformance, 22 Jun 2021; Citi, Short Blues convexity via futures/swaps, 21 Feb 2023)
- Examples: sell Blues, buy a 1000-lot Jun-24 to Mar-25 Eurodollar four-contract pack and pay $1.01bn forward swap at 7.9bp ($100K DV01), carry +1.2bp/3m, CA-implied
  vol 102.8 vs realised 84.2 (1.2), target 4bp, stop 3bp; earlier H0-Z0 at 6.76bp with implied 112.3 vs 76.6 (1.5) went
  8.8 to 6.6bp for +$552K. Feb 2023 Blues row: CA 13.09, model 9.44, CA-model 3.65, CA-implied vol 147.6 vs realised 134.9.
  CA rising while vols fall is positioning-driven; CA-implied vs realised is a cushion gauge, not a forecast. (Citi, Left-side
  vols' outperformance, 22 Jun 2021; Citi, Short Blues convexity via futures/swaps, 21 Feb 2023)
- FCA from IRS gamma (IBOR-era formula, constant σ_BP, re-hedged at the close at nil cost): front contract E[P] ~
  63·N·d1²·Var(dr1)/A1². 16 Mar 22 example, 63 business days, σ_BP 3bp, N = 1bn: 354, about 0.014bp front, 1,063 or
  0.043bp second. "The whites have convexity values of 0 to 0.5bp, the greens 1.5 to 12bp." (Darbyshire, IRDs, Ch.22 tail)

## 4. Delta-hedged forward flatteners (long convexity, "strikeless vol")
- Mechanism: PV01-weighted flatteners are positively convex under large parallel moves; like an option, they usually
  carry negatively. Receive the longer forward (e.g. 20y10y) vs pay the shorter (15y5y) DV01-neutral; re-hedge the longer
  leg back to DV01-neutral at each threshold move in its forward rate (receive more if rates rise, pay if they fall). The
  resize is where the gamma is harvested; P&L accrues from realised vol, even if the curve steepens against you.
  (J.P. Morgan, An option by any other name, 3 Feb 2017; Citi, Trading long-dated convexity, 9 May 2019)
- Daily breakeven: the parallel daily move whose convexity gain offsets the negative daily carry (0 if carry is positive).
  Compare with 1y realised daily vol of the longer forward. BE/RV below 1 = cheap embedded convexity; exit when carry
  deteriorates and BE/RV rises toward 1. For forward steepeners (net short convexity, positive carry) the ratio above 1
  is attractive. (Citi, Taking profits on delta-hedged 15y5y/20y10y flatteners, 5 Dec 2019; Citi, Forward steepener and vol
  divergence, 12 Jun 2023)
- Curve-implied vol: assume a normal terminal distribution of parallel shifts and solve σ giving zero expected payoff of the
  aged flattener (fixed coupons = forwards) over the horizon; below the ATMF swaption vol means the curve is cheaper long
  gamma. Convexity P&L attribution of an aged forward flattener: carry = ex-ante spot - forward; curve = change in spot
  curve; convexity = remainder. (J.P. Morgan, An option by any other name, 3 Feb 2017)
- Hedge threshold: 15-30bp plateau (Sharpe flat), "20-25bp offers an attractive balance"; USD at 20bp, GBP at 25bp. Costs,
  one way: initiation 0.75bp (1.0 for the others), hedge and roll 0.3bp (0.4). Roll the package annually: convexity per DV01
  falls and curve vol rises as it ages. (Citi, Trading long-dated convexity, 9 May 2019; Citi, In search of cheap vol,
  17 Jan 2020)
- Backtest ($100K DV01, annual roll, 25bp hedge; average daily $K / daily vol $K / Sharpe): 10y10y/20y10y 2.28/222.1/0.16;
  10y10y/25y10y 5.40/247.6/0.35; 15y5y/20y10y 2.92/251.5/0.18; 20y5y/25y10y 4.09/219.3/0.30. 10y10y/25y10y monthly P&L
  correlation with 1y10y vol about 26%, daily skew about 0 against about -3 for a short delta-hedged 1m10y straddle
  (Sharpe about 0.84); flat since 2013 despite 1y10y vol falling 50 normals. (Citi, Trading long-dated convexity,
  9 May 2019; Citi, Deal or no deal, 10 May 2019)
- Lifecycle, USD 15y5y/20y10y: screen 8 May 2019 curve -11.3bp, 1y carry -0.31bp, daily BE 1.3bp vs 1y RV 3.0 (BE/RV
  0.42); entered 9 May at -11.8bp, $50K DV01 ($148.8mn 15y5y vs $90.3mn 20y10y), hedge every 20bp; +$105K MTM by 16 Oct
  despite about 2bp steepening, reweighted 20y10y from $81.97mn to $84mn (empirical beta 1.025); closed 5 Dec at -12.5bp,
  about +$187K mid and +$155K net of costs, with carry at -2bp/yr and BE/RV 0.8. (Citi, Reweighting delta-hedged
  15y5y/20y10y flatteners, 16 Oct 2019; Citi, Taking profits..., 5 Dec 2019)
- Cross-market screens (BE/RV): 4 Dec 2019 USD 0.45-1.09 (15y5y/20y10y -12.54bp, carry -2.09, BE 3.33, RV about 4.2, 0.80),
  GBP 0.00-0.84 (carry up to +0.89bp); Sep 2019 USD 15y10y/25y10y 0.50, EUR 10y10y/15y15y 1.44 (expensive, carry -6.31),
  CAD 15y5y/20y5y 2.00 (most expensive); Jan 2020 EUR 0.60-1.48, JPY 0.76-1.50 (JPY realised vol only 2.4-3.1bp/day vs
  3.9-4.7 elsewhere), CAD 0.45-1.82; Jun 2023 steepeners 10y10y/20y5y carry 10.31bp, BE 7.22, RV 5.24, BE/RV 1.38.
  GBP 15y10y/25y10y (Jan 2020): 1y carry +0.52bp, BE 0, hedged every 25bp, closed 26 Mar 2020 at -19bp for +$542K.
  Not initiated when liquidity is poor (USD 15y5y/20y10y, 26 Mar 2020: -5.21bp, z 4.21, carry +0.11, RV 6.40bp).
  (Citi, Taking profits..., 5 Dec 2019; Citi, Buying vol for less, 25 Sep 2019; Citi, In search of cheap vol, 17 Jan 2020;
  Citi, Forward steepener and vol divergence, 12 Jun 2023; Citi, Liquidity, vega, and convexity, 30 Mar 2020)
- Why convexity is cheap: no well-defined downside, hard to hold terminally; insurer/VA receiving in 15-25y keeps the
  >20y curve steep (stocks vs 15y5y/20y10y correlation about -23%); the spread between 10y10y and 20y10y rates is
  "akin to implied volatility". Best carry among steepeners usually comes with the worst entry. (Citi, Trading long-dated
  convexity, 9 May 2019; Citi, Forward steepener and vol divergence, 12 Jun 2023)

## 5. Matched-straddle comparison and package screens (working formulas)
For a package with curve DV01 weight ΔD (per 1 unit) compared with a gamma-matched ATMF straddle, rates in bp, normal
vols in bp/yr, horizon τ0 in years:
- Gamma match: straddle underlying DV01 per curve DV01 k = 1e-4·ΔD·σ_imp·√τ0/φ(0).
- Straddle theta over the horizon = 1e-4·ΔD·σ_imp²·τ0 and gamma-matched straddle premium = 2e-4·ΔD·σ_imp²·τ0: the premium is
  TWICE horizon theta because ATM gamma grows as 1/√τ. Never compare package carry with straddle premium: it inflates the
  breakeven vol by √2.
- Breakeven vol σ_BE solves |carry| = 1e-4·ΔD·σ_BE²·τ0 (carry negative). σ_BE/σ_imp below 1 = package cheaper long gamma than
  the straddle. A small ΔD makes σ_BE explode (require ΔD about 4 or more and σ_BE below about 300); a persistent "cheap"
  belly reading is usually term premium, so check that sign(carry) is not constant over the last 252 days.
- Side: flattener (long curve gamma) plus sell straddle when σ_BE < σ_imp; steepener plus buy straddle when σ_BE > σ_imp.
  Skip when σ_imp has risen more than about 8bp in 10 days (do not sell into a spike). The model has no smile: short-straddle
  losses after big moves are understated.
- Verify any claim of "long vega, short gamma" for a linear package with computed DV01 and gamma under parallel shifts,
  expressed per day; reprice the aged package on shifted curves rather than using analytic greeks (a repriced 1y roll
  matched published carry, correlation +0.99, whereas a running carry-and-roll field correlated -0.14); "a convex payoff
  must show a smile, not a ramp": bucket P&L by the size of the underlying move.
- Placebo: Sharpe is a poor ranking key for these packages (placebo pairs can out-Sharpe real ones); test convexity by
  bump-and-reprice gamma and realisation by the harvest bucket; around 96% of daily P&L variance is first-order slope, so
  daily skew and vol correlation do not distinguish long from short convexity.

## 6. Cross-asset expected return from carry, roll and convexity
Linear: ER = theta·dt + Delta·rateRD + ½Gamma·σ_real²; options: ER = theta·dt + Vega·volRD + ½Gamma·σ_real². Gamma from
realised vol, delta and vega from a static spot curve and vol surface (rate roll-down and vol roll-down). Expected Sharpe =
ER/σ_trade ranks swaps, bonds and vol on one frontier. Example: paying the EUR 5y5y-15y5y-25y5y fly, ER +34bp, risk 50bp,
expected Sharpe +0.7. Decompose realised P&L into delta, carry and convexity before reading a price chart of a structurally
convex trade. (Citi, A Holistic Approach to Convexity Across Fixed Income, Jun 2022)
