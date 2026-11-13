# Trade and data examples (inflation)

Reference for [SKILL.md](../SKILL.md). Published trade books are dated snapshots: levels show structure and sizing logic
(entry, target, stop, one named risk), not current value. Quote them as examples, never as live recommendations.

## UK linker curve: same-month forward real yields (BofA, UK Rates Viewpoint: Back to school, 5 Sep 2024)

Plot UKTi real yields against modified duration and compute forward real yields *between issues of the same maturity
month* (November only), which removes the need for a seasonal adjustment. Forward real yields: 2027s-32s 49bp; 2032s-36s
129bp; 2036s-47s 190bp. The first step (+80bp) is mostly RPI-reform pricing (2030). The second step (+61bp) is "almost
wholly about asset swap cheapening" and is not in the real swap curve. Forwards step down beyond 2047, so the 2036-47
plateau is a longstanding habitat anomaly.

Book (entry, target, stop, one risk each):
- New: 2032-36-47 barbell, long the wings, risk weights +43.8% / -100% / +56.2%, pick-up 14.8bp, target 5, stop 20. Risk:
  supply events in illiquid conditions.
- Kept: sell UKTi 2036 vs UKT 2042 on ASW at -21 (target -8, stop -28); pay 5y real SONIA at 1 (target 60, stop -30);
  UKTi 2052/68 yield flattener at -13 (target -35, stop 0; light ultra supply, convexity).
- Closed: 2036s/2047s real-yield flattener 55 to 51 (target 30, stop 70); pay 2034-46 fwd / receive 2036-47 fwd 24 to 16;
  2032-36-42 barbell 13.6 to 11.8; UKTi 2029 short 21 to 30; UKTi 2033 into OATei 2034 switch 26 to 53; UKTi 2026 iota
  narrower 38 to 15.
- Context: bank linker holdings fell from GBP 59bn (42bn sub-5y) end-Feb to 40bn (23bn sub-5y) end-July after redemptions;
  gradual reinvestment points to more front-end iota compression. Linker redemptions and the pace of bank reinvestment
  distort short-dated RV, so express macro real-rate views through real swaps.

## US inflation book (Citi, US Rates Weekly: Pension plan for 20s?, 9 Oct 2026)

- 5y IOTA widener (Oct30s), 40k DV01 at 5bp, now 2.7, target 13, stop 0.
- Short 2y BEs (Jul28) hedged by buying 36 May-27 gasoline futures at 270.70: 15k DV01 at 2.28%, target 40bp, stop -20bp. The
  energy hedge isolates the non-energy part of front-end BE.
- Long 5y TIPS ASW 20k DV01 at 34bp, now 33, target 14, stop 49. Risk: 5y nominal swap spreads tighten.
- Long-belly 5s10s30s inflation-swap fly 40k DV01 at 2.85bp, target 10, stop -4.
- Flow facts used: October new-issue 5y TIPS auctions usually tail (1 of 6 traded through; last three averaged a 2bp
  tail); about USD 11.6bn into the 5 largest TIPS ETFs YTD (two-thirds in 0-5y) against about USD 50bn of 5y supply; funds
  hold about USD 2.7bn of Oct26s/Oct27s leaving the index; IOTA near its tightest, off-the-run 5y IOTAs historically
  widened slightly after October auctions.
- Fixings facts used: ex-gasoline inflation implied by BEs about 2.8% over Oct26-Oct27 vs realised ex-gasoline 2.2% YoY;
  fixings priced 0.52% m/m headline NSA, about 0.21-0.23% core SA; headline printed below fixings in 8 of the last 10
  months.

## Earlier TIPS cases

- TIPS ASW screen (Citi, US Rates Weekly: All it takes is a little push, 4 Oct 2019): Jan20s 22.1bp (3m z 3.1, 1y z 4.4)
  vs nominal Jan20 at -20.8; Jul20s 17.6 (1.5/1.9); Jan21s 27.2 (1.1/2.4); Apr21s 25.6 (1.2/2.4). Drivers named: index
  exits (under 1y to maturity), dealer balance-sheet stress, carry trades stopped out after a repo spike, foreign official
  selling. Book: long 5y TIPS BEs hedged with a short 1y1y inflation swap, 1.69% to 1.12%, -2,260k.
- Scenario mapping (Citi, Deal or no deal, 10 May 2019): in a trade-war escalation long BE is the most vulnerable; 30y TIPS
  is fine because the BE drop is offset by the real-yield drop (30y TIPS 1.347% to 0.97%: +1,728K; 5y BE: -562K).

## JPM inflation trades and hit rates (JPM, Monthly Inflation Outlook, 13 Aug 2026)

- EUR 2s/5s HICP flattener (buy 2Y, sell 5Y) at -20bp. 5Yx5Y FCPI-HICP widener at -3.8bp, expected to oscillate around 0
  with a modest positive bias. New 10Yx10Y HICP minus US CPI narrower at -1bp (10Yx10Y HICP range-bound about 2.35%).
- UK 5Yx5Y/15Yx15Y RPI flattener at 21bp; UK long 10Y real (receive 10Y SONIA, buy 10Y RPI swap) at 127.5bp; the 10Y real
  swap was about 1.30%, within 5bp of multi-decade highs.
- US long 5Yx5Y ZCIS (100% risk) and a 5s/10s/30s ZCIS fly labelled "belly-cheapening" by the source (long 5Y 50% risk, long 30Y 50%, short 10Y
  100%; in this skill's convention, fly = 2x10Y - 5Y - 30Y rate, it profits when the belly rate falls vs the wings: read the legs, not the label); fly plus 5Yx5Y long is roughly a 30Y long. BEs have positive beta to the nominal curve.
- Hit rates: 2026 US 6 trades 50% avg -17; UK 2 trades 100% avg +10. 2025 US 16 trades 75% avg +24; Euro 4 trades 50% avg
  -3; UK 5 trades 40% avg +2.
- BE forecasts: US 10Y 217 to 205/200/195/195 (Sep-26 to Jun-27); UK 10Y 339 to 330/330/330/320; France 10Y 227 to 225-240.
- Closed: OATei40 IOTA widener +3; long 10Y real EUR via swap -12; UK 10s/30s RPI flattener +17; long 1Yx1Y RPI +11; tactical
  short 5Yx5Y RPI +7.
- Rich IOTA stays rich when flows dominate: 15Y+ OATei IOTAs rich (z up to about +3 at OATei56) with a medium-term widening
  bias.

## Euro and UK auction dashboards

- OATei 3.15% Jul32 (18 Aug 2026): RY 1.26% (+1bp), BEI 229bp (+11), z 1.10/0.76, fly Jul30-Jul32-Jul34 2.19/-0.72. OATei
  0.95% Jul43: 2.23% (+8), BEI 233 (+6). OATei 0.1% Jul47: 2.37% (+10), BEI 236 (+5). Column mapping approximate (Citi, Morning
  Call: EU: Improved RV after the rates sell-off, 19 Aug 2026).
- UKTi 1.125% Sep35, GBP 1.5bn (12 Aug 2026): RY 1.73% (+0bp), BEI 316bp (+5); z RY 0.74; vs surrounds Mar34-Sep35-Nov36
  -0.68; spread to nominals 1.20 (Citi, Morning Call: Extending the dovish momentum, 12 Aug 2026).
- Month-end index extension: euro linker index +0.02y; UK linker index -0.02y (same source).
- SPGBei27 vs BTPei28 BE trade stopped out (SPGBei27 IOTA 34.5bp vs BTPei28 25.4bp); book: long 10y10y US CPI vs 10y10y HICP,
  entry 0.14 / target 0.32 / stop -0.10 (Citi, European Rates Weekly, 17 Mar 2022).

## Fixings tables

| Source and date | Reading |
|---|---|
| JPM, Monthly Inflation Outlook, 13 Aug 2026 | HICPxT swap-implied 2026 average 2.9%, 2027 average 2.5% vs forecast 2.7%/2.1%. UK RPI implied 2026 average 3.7% and 1H27 4.2% vs forecast 3.8%/4.7%. |
| Citi, US Economics Weekly, 14 Aug 2026 | Market CPI NSA (YoY) vs house: Aug-26 334.840 (3.4) vs 334.808 (3.3); Mar-27 338.310 (2.5) vs 337.051 (2.1); Apr-27 339.390 (1.9) vs 338.029 (1.5); Aug-27 342.303 (2.2) vs 340.206 (1.6). Market-implied core m/m 0.20-0.35 vs house 0.15-0.18 almost every month. From spring 2027 the house sits 0.4-0.6pp YoY below the market: fixings rich vs economists. |
| Citi, Inflation Weekly, 17 Aug 2026 | Same comparison three days later: Aug-26 market NSA moved 334.840 to 334.890. Fixings marks move; timestamp every comparison. |
| Barclays, Diesel's long haul, 1 Oct 2026 | Fixings-implied tracking (bp m/m, SA / ex-energy SA / core forecast): Sep26 55/19/20; Oct26 18/21/23; Dec26 24/23/23; Jan27 13/41/21; Apr27 13/7/19; Jul27 14/21/19. Implied core 18-23bp in 9 of 11 months; Jan/Apr 2027 distorted by the gasoline curve shape and energy seasonals. |
| Citi, US Economics Weekly, 2 Oct 2026 | Market-implied core CPI m/m: Sep-26 0.39; Oct 0.16; Nov 0.13; Dec 0.20; Jan-27 0.29 vs house 0.13-0.24. |

Gasoline decomposition (JWS Macro, Global Rates Outlook #4, 8 Apr 2026): March headline priced at 0.84% m/m (economists
about 1%), about 110% of the implied change attributable to gasoline, then only 0.1-0.2% m/m SA from May (no second-round
effects priced). Sanity check (JWS Macro, Global Rates Update #7, 19 Jul 2026): the July US CPI fixing at 333.95/96 was
flat to June (0.0% m/m NSA) despite gasoline +15% since mid-June; July has the smallest NSA/SA residual; Aug/Sep priced
0.4/0.3% m/m. Possible cause: retail gasoline lagging futures.

Oil to fixing to policy chain (JWS Macro, Global Rates Outlook #5, 10 May 2026): Brent Dec future to the Dec-26 inflation
fixing to the Dec-26 implied policy rate. As of 8 May 2026: Brent Dec 87 USD, Dec-26 HICP fixing 3.6%, RPI 5.1%; implied ECB
scenarios baseline about 75, adverse about 92, severe 115-120 USD Brent (non-linear). UK market-implied CPI = RPI swaps
minus the 0.8% median RPI-CPI wedge. JPY consumption-tax cut on food (8% to 1% from Apr 2027) mechanically lowers core CPI by
20.1% x (1 - 101/108), about 1.3pp (JPM, 13 Aug 2026).

## Basis and linker-ASW context (BofA, Welcome to the real world, 22 Jul 2025)

- UK 4y: RPI swap 3.38% vs UKTi BE 3.25%, basis (swap - BE) +13bp, i.e. cash BE cheap to swaps.
- US 10y basis: compressed in 2021 (TIPS fund inflows; Fed QE bought over 80% of gross TIPS issuance), widened in 2022 (Fed exit, higher liquidity premium), compressed again since 2024 (nominal USTs cheapening vs ASW). UK and EUR linkers often trade rich to nominals on z-spread; UK linkers are cheap only at the long end; OATei are all expensive vs OATs.
- Scarcity is not RV: the Apr-2032 TIPS (tiny USD 5bn issue, never reopened) screens rich on SARY at 6.75y.

## Real-rate and policy views

- Market-implied r* = 2y1y nominal swap minus 2y1y inflation swap: about 0 in Jan 2024 vs about +250bp in 2007-08 and about
  -200bp in 2021 (chart reads) (Nordea, EUR rates: Pushing back, 17 Jan 2024).
- 5y5y real fed funds = 5y5y OIS minus 5y5y BE: 2.0-3.0% from mid-2009 to early 2010, ending near 2.4%. Policy rules put
  equilibrium at 2-3%; above 3%, receive 5y5y OIS and go long 5y5y BE (Credit Suisse, Basis Points, 18 Feb 2010).
- Real vs inflation quadrant on 1y1y swaps: both up/down = growth shock; real down + inflation up = dovish Fed impulse;
  real up + inflation down = hawkish shock; real up with flat inflation = neutral-rate reassessment (Barclays, 2 Oct 2026).
- Strip a ZC curve into an implied CPI path: compare today's curve with a pre-shock curve, derive the implied NSA CPI level
  over 10y and the sequence of "X-year forward 1-year" rates; the pre minus post-shock difference of implied fixings is the
  accumulated price-level impact. Example: implied CPI path about 1% higher by 2028, accumulated difference peaking about 2030
  (JWS Macro, Global Rates Outlook #4, 8 Apr 2026).
- Range break: 1y1y CPI swaps traded a 14bp range in Q3 2026 (2.493-2.635%), the tightest since 2013; focus beyond 1y to
  reduce spot-energy exposure (Barclays, 2 Oct 2026).
- July and October are the most bullish months for US forward CPI swap total-return trackers (2014-2025); not carried to TIPS
  outright (October 10y: 5 up/5 down) or to nominal USTs (sold off in 8 of 10 Octobers, average -0.7%). The authors overrode
  the seasonal that time (Barclays, 2 Oct 2026).
