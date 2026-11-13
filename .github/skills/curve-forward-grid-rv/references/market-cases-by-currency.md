# Market cases and G10 differences (forward grid)

Detail for the Worked examples and market notes of [SKILL.md](../SKILL.md). Chart reads are marked (approx.).

## G10 differences that change forward levels or trades
| Market | Forward-grid specifics |
|---|---|
| USD (SOFR) | Very-long forward curve normally inverted; 15y5y vs 20y10y steepness driven by VA receiving in the 20y sector during equity sell-offs. Front forwards (< 2y) are the FOMC calendar. UST term repo rarely beyond about 3 months, so long forwards come from swaps. Real-time neutral from flat 1y1y/5y5y about 4.10% (Jun 2026). SOFR forwards rose to about 12y then declined but stayed above spot (May 2021). |
| EUR (ESTR) | 1y forwards peak around 14-15y start (about 0.78-1.05% in Jan-Feb 2020), negative beyond about 41y; long end structurally negative forward-spot roll; Dutch pension reform distorts 20y+ forwards; PCA set of 17 forwards; bear-flattening more likely than bear-steepening (PC1 loadings largest 1y1y-5y1y). TARGET calendar, modified following. |
| GBP (SONIA) | T+0 spot: forward starts measured from today. Lowest BE/RV of the big five in Dec 2019 - Jan 2020, several positive-carry long forward flatteners; 20y rich on ALM receiving; 30s/50s convexity underpriced vs swaptions (2018); 30y10y-40y10y near all-time flats in 2012 and at a 5y inversion extreme (z -2.00) in the Sep 2026 screen. SONIA curve highly directional to ESTR 1Yx1Y (beta 1.09). Act365F vs ESTR Act360: align before comparing. |
| JPY (TONA) | Convexity expensive (30s/50s negative expected payoff 2018); realised vol on long forward curves only 2.4-3.1bp/day (Jan 2020); rhetoric response concentrated in the long end; forward levels and shape converging with overseas markets (2026), so overseas moves transmit more; 1-April turn must be stripped. |
| CAD (CORRA) | Semiannual fixed leg (check convention): annual-leg screening error larger; BE/RV 0.45-1.82 on long forward curves (Jan 2020); front end followed Fed rhetoric less. |
| AUD / NZD | Bank-bill swaps (BBSW/BKBM), quarterly or semiannual legs by tenor: use the real curve for levels; AUD/NZD 5y5y anchored to USD 5y5y (R^2 0.47 pre-2023 to 0.76 post, test for breaks); GS Sep 2026 picks: AUD receive 1y 2s5s10s, NZD 15y5y/20y5y and 10y5y/15y5y/20y5y. |
| CHF (SARON) | Forwards below spot beyond about 22y (May 2021): spot declines with term; CHF 1y1y/2y1y carry Sharpe 1.26 (Sep 2026). |
| SEK / NOK | Liquid to about 10y: grids use 1y-3y starts and 2y-tenor flies (SEK 4y1y/5y2y; NOK 5y1y/6y2y/8y1y); 30/360 annual fixed leg vs 3m/6m floating (basis in the forward); rhetoric beta negative for own-economy; SEK 1Yx1Y-3Yx1Y richest vs US (about -105 to -115bp, May 2024). |
Verify every convention in [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md) before building levels.

## EUR cases
- **Top of the forward curve (Nordea, EUR Rates Flash, 24 Jan 2020 / 5 Feb 2020)**: 1y forwards peak about 0.92% (Jan) / 0.78% (Feb) around
  a 14-15y start; 12m roll positive to about 15y (max about 12.8-13bp around 6-8y), negative beyond (min about -4.6 to -5bp around
  21-22y) (approx.). Receive 6y2y or 5y5y for carry; risk-adjusted 5y5y/15y5y; "brain-dead" receive 10y5y / pay 15y5y. 5/10y "looks too
  flat" partly because participants receive 5y5y for carry and roll. 17 Mar 2020: local trough about 28y, hump about 35-37y; 1y roll
  about +14bp at 3y, about -7bp from 14-28y; view 25-30y rich, 10y, 35y and 50y cheap; 3/6m forward basis negative beyond 7-8y (to
  about -2.5bp): pay 3/6m basis. Flow-driven sections (25-35y in Mar 2020) keep PCA/forward signals stretched.
- **ING xF1Y grid (15 Jan 2020)**: forwards peak about 1.05% at 14F1Y-15F1Y, about 0.5% at 30F1Y. PC1 residuals: 1F1Y-5F1Y cheap +5 to +11bp
  (1F1Y near 3y cheapest), 10F1Y near richest, 7F1Y-15F1Y mostly slightly negative, 20F1Y about +4. 2F1Y/3F1Y cheap +20 to +27bp in Jan and Oct
  2018, range -20 to +27bp over 2017-2019. Pay direction-neutral 2s7s10s fly (weights 3-2-0.84 as printed, uncertain first digit):
  entry 71bp (0.5bp off 70.5 mid), target 91, stop 61, carry -2.5 / roll +3.2 = +0.7bp/3m; 9bp from 3y mean; risk: ECB reaction
  function. Check non-linear exposure of a PC1-neutral fly with a quadratic fit (7Y EUR swap inflection near 0%).
- **PCA trades (Credit Suisse, PCA Unleashed, 22-24 Oct 2012)**: receive 1s2s3s 1y-forward (1y1y-2y1y-3y1y) at the top of its -7/-2bp range;
  pay 10y10y-20y10y-30y20y fly (10y10y as weighted average of 10y2y, 12y3y, 15y5y cheap; 20y10y rich); GBP 30y10y-40y10y steepener near
  all-time flats. Selected loadings (PC1/PC2/PC3): 1y1y 0.2469/-0.16/0.22; 5y1y 0.3205/0.00/0.02; 9y1y 0.2346/0.14/-0.21; 30y10y
  -0.0559/0.44/0.36; 40y10y -0.0305/0.52/0.48. PC-neutralisation of a book (net DV01 -85k/bp: PC1 -16.09, PC2 -23.34, PC3 +20.76) used
  5y1y +50.19k for PC1; 1y1y -74.01 and 9y1y +78.75 for PC2; three hedges for PC3. Long 100k/bp 1y1y hedged with short 95k/bp 9y1y.
- **Nordea forward flies and trade box (Nordea, EUR rates: Pushing back, 17 Jan 2024)**: receive 1y2y/3y2y/5y2y 6s fly at -8bp (target -25bp +
  roll, stop +5bp); box: carry/12m 79.2, convexity value 0.0, realised vol 46.5, carry/vol 1.70, frequency in the money after 1y vs prior
  1y/3y/5y/10y 100%/59%/75%/76%, z 0.64, P-score 2.34; 1Y correlations to 10y -0.08, 5/10/30 fly 0.42. Expected cuts erode front-end
  roll ("some but not all of the roll").
- **Euribor futures spread ageing (Nomura, Conditional Euribor bull flatteners, 19 Jun 2014)**: spot / forward / strike spreads 11.7 / 40.0 / 50.0bp
  (the Mar-25/Mar-27 Euribor futures spread at 40bp ages into the Dec-24/Dec-26 spot spread at 11.7bp): a steep forward spread ages into a flatter spot spread, so forward positioning earns
  curve carry. the Dec-26/Dec-27 Euribor fwd-fwd spread about +12.5bp seen inverting to about -12.5bp (JWS Macro, #3: Iran & Front End Rates, 8 Mar 2026).

## USD cases
- **Forward swap-spread grid (Citi, Short-End Notes, 21 Aug 2026)** level (3m z) / rich-cheap vs first 2 PCs (z) / 1y rolldown, 20 Aug 2026:
  1y1y -18.9 (1.0)/2.8 (0.9)/8.8; 2y1y -30.8 (0.0)/-2.1 (-0.7)/9.3; 3y2y -39.6 (0.6)/0.1 (-1.2)/1.8; 5y2y -54.4 (1.6)/1.9 (1.3)/6.2; 7y3y
  -52.9 (0.8)/-2.9 (-0.4)/-3.4. Forwards built from the same original-issue bond. Trade idea: long 5y spreads, small 2y short as a hedge:
  dislocation between 3y2y forward spreads and spot 2y spreads. Spread signs: [spread-swap-spreads-and-asw](../../spread-swap-spreads-and-asw/SKILL.md).
- **UST forward curve report (J.P. Morgan, Forward Treasury, Asset Swap and Funding Report, 29 Jan 2015)**: spot / 6m forward 2-5 76.3/77.5;
  2-10 123.4/121.8; 5-10 47.1/44.4; 2-30 180.0/174.2; 5-30 103.7/96.7; 10-30 56.6/52.3; flies 2-5-10 29.2/33.1; 2-5-30 -27.4/-19.3;
  2-10-30 66.8/69.5; 5-10-30 -9.5/-7.9; 10y Nov-24 spot 1.752, 1m 1.768, 3m 1.801, 6m 1.849 (fwd-spot 1.6/4.9/9.7bp). Forward vs spot = repo
  carry breakeven; specials carry better, so forwards differ from GC-based forwards.
- **Forward 2s10s carry (Clarus, Mechanics and Definitions of Carry, 16 Jan 2019)**: spot 2y 2.696%, 10y 2.73% (3.82bp); 3m2y 2.662%, 3m10y
  2.738% (7.64bp): receiving forward 2s10s earns about 3.82bp over 3m. EUR: 3m10y 0.8452% vs spot 0.7944% = 5bp/3m.
- **2y forward 2s10s steepener (Citi, All it takes is a little push, 4 Oct 2019; Eat pay spend, 27 Mar 2020)**: 50k DV01 at 26bp, rolldown about
  -4.7bp/yr, to 32.6bp by 26 Mar 2020. Selection: score spot and forward-start curves (1y/2y/3y 5s30s, 2y 2s10s, 3y 2s5s, 2y/3y 10s30s)
  on risk-adjusted returns in past easing cycles (6m after first cut in 2001 and 2007) and in a hypothetical 6m ZLB scenario; pick the
  structure that works in both "grind to zero" and "fast break" paths. Forward steepening starts earlier than spot (Willer & Saunders,
  Trading Global Macro Markets, 2026, Ch.5). Supply is better traded in swap spreads than in forward-curve shape (5y5y-2y1y unrelated to
  net supply, same chapter).
- **1y forward 5s10s30s fly (Citi, Flying Too High, 20 Dec 2010)**: spot / 1y fwd / predicted 2s5s 132/129/119; 5s10s 126/94/85; 10s30s 73/46/66;
  2s5s10s 6/35/33; 5s10s30s 53/48/19. Receive belly: pay 1y5y -$180mm 2.971%, receive 1y10y $200mm 3.908%, pay 1y30y -$50mm 4.344%.
  Entry 48bp (above 98th percentile even in on-hold regimes), target 20bp profit (28bp gap - 8bp convexity), stop 10bp. Rejected 1y fwd 10s30s
  steepener: +27bp/a carry but 11bp/a convexity and Fed-timing directionality. Regime averages (on hold after cut / start hiking / 6m into
  hiking, bp): 2s5s 129/106/69; 5s10s 93/74/55; 10s30s 69/63/49; 2s5s10s 36/32/14; 5s10s30s 24/10/6.
- **Long-end forward fly (Citi, Taking profits on long end butterfly trade, 15 Jun 2020)** and GBP/USD flatteners: see the long-end reference.
- **Cycle markers**: Fed funds touching or crossing 5y5y is a late-cycle signal (Feb 2019 call; FF 3.88% vs 5y5y 3.85% in Nov 2022; Convexity
  Maven, Dangerous Curves Ahead, 15 Feb 2022). Collapse of 1y-forward dispersion (1y1y, 3y1y, 5y1y vs median LT dot) marked late cycle in 1Q18
  (BofA, To everything there is a season, 23 Jan 2022). 7y vs 7y-forward-20y spread never inverted until early 2022 (-32bp) (Convexity Maven,
  Leverage is NOT a four-letter Word, 26 Jan 2023). 3y-forward 10y fell below spot 10y in Jan 2024, the first time on the author's record
  (Convexity Maven, Sharp Curve Ahead, 25 Jan 2024).
- **Breakeven framing (Convexity Maven)**: 2y 4.20% vs its 1y-forward 2y 3.50% (70bp lower); UST 2s10s at -20bp needs 60bp of steepening
  to +40bp in a year to break even; at -35bp DV01-weighted ($430 2y per $100 10y) needs 58bp, and $100mm costs about $390,000/month
  (The Cost of Carry, 5 Mar 2024). Fully-margined forward: 2y 4.45% financed at 5.00% => 1y1y breakeven 3.90%.

## Cross-market forward spreads and G10 screens
- **Forward-on-rhetoric model (J.P. Morgan, Talk is Cheap, 30 May 2024)**: `fwd = B0 + B1*PC1 + B2*PC2 + B3*home + B4*US growth-surprise score + B5*US inflation-surprise score`, levels,
  daily, samples full / 10Y / 5Y, no lagged dependent variable. 1Yx1Y residual bp (z) on 5Y model: USD 186 (2.80), EUR 142 (2.12), JPY 53
  (3.82), CAD 146 (2.54), GBP 192 (2.48), SEK 134 (2.18), NOK 142 (2.46), AUD 194 (3.15), NZD 175 (2.73): all cheap, a year earlier mildly
  rich. PC1 betas (bp per sd): USD 0Yx1Y about 32, 1Yx1Y about 17, rest about 11-12 (textbook bear-flattening); EUR barbell (0Yx1Y 8.5, 3Yx1Y
  3.3, 10-15Yx1Y 4.8); JPY from 0.6 to about 8 at 15Yx1Y. Cross-market residuals to the US: cheapest GBP 0Yx1Y about +200, AUD +185, CAD +150;
  richest JPY 1Yx1Y about -145, SEK 1Yx1Y about -115. Regime change confounds the model (2020 residual was policy-intended). With high neutral
  uncertainty, cross-market forward spreads are more comfortable than outrights.
- **Goldman Sachs desk screen (30 Sep 2026)**: ultra-long forward spreads at 5y extremes of inversion: 30y10y/40y10y EUR 0.615% (z -2.00),
  GBP 0.991% (-2.00), USD 0.803% (-2.29); 25y5y/30y10y EUR 0.460% (-2.38), GBP 0.700% (-1.93). USD 10y5y/15y5y/20y5y fly: carry 1.8bp, vol
  3.0, Sharpe 1.20, R 0.26, Carry/R 0.95; USD outrights R about 0.85-1.0, Carry/R about 0. GBP 15y5y/20y5y carry 1.3bp, Sharpe 0.90, Carry/R
  0.70. Typical realised vols: outrights 25-55bp, curves 2-23bp, flies 2-18bp. Normalised-move screen (move / sd of horizon changes; 1d and 1w
  on 62 days, 1m on 252): 1w USD 10y20y +32bp (4.6sd), USD 5y5y +29bp (4.5sd), 1m EUR 2y3y/10y20y -45bp (2.8sd): bear-flattening across
  forwards. Short windows inflate z.
- **Citi cross-market 5y5y panels (Citi, Asia FX and Rates Strategy, 13 Aug 2026)**: use weekly Wednesday closes to avoid time-zone lag and payroll-day
  noise; pegged markets inflate factor R^2 (re-run without them); test for breaks.
- **EM forward trade log (Citi, EM Strategy Weekly, 20 Aug 2026)**, entry -> exit, P&L: 1y1y Taiwan NDIRS receiver 1.69 -> 1.31% (+38bp, 7 days);
  3m fwd 1s5s INR steepener 28.3 -> 46bp (+21.7); 1y fwd 1s10s KRW steepener 12.5 -> 19.5 (+7); pay PLN 5y5y vs US 218 -> 188 (-30); receive HUF 5y5y
  vs EU 375 -> 347 (+28). Forward legs 1y1y, 2y2y, 5y5y and cross-market forward spreads are common; holding periods days to months;
  model-portfolio replication shows slippage from costs and publication delay. Low G10 relevance.
- **JPY (J.P. Morgan, Japan FI Weekly, 21 Feb 2025)**: pay 2Y1Y 0.826% vs receive 1Y1Y 0.750% steepener +2.9bp; if forwards already price the house
  terminal rate the market is "priced for perfection". JPY OIS strip convergence to overseas: Citi, Japan Rates Weekly, 14 Aug 2026.
- **Inflation forwards (J.P. Morgan, Monthly Inflation Outlook, 13 Aug 2026)**: 1Yx1Y/5Yx5Y HICP on 1Yx1Y HICP over 3M: `Y = -86.82*X + 184.24`, R^2
  92%; EUR 5Yx5Y FCPI-HICP widener -3.8bp (+1.5); 10Yx10Y HICP range-bound about 2.35%; UK 5Yx5Y/15Yx15Y RPI flattener 21bp (-4.5). Real
  5y5y fed funds fair 2-3% (Credit Suisse, Basis Points, 18 Feb 2010). Falling 5y5y inflation after a front-loaded shock: JWS Macro, Global Rates
  Outlook #4, 8 Apr 2026. 2y2y EUR real about 0.5% trending up (JWS Macro, Global Rates Outlook #6, 7 Jun 2026).
- **UK linker forward real-yield steps (BofA, UK Rates Viewpoint, 5 Sep 2024)**: forwards 2027s-32s 49bp; 2032s-36s 129bp; 2036s-47s 190bp; the first step
  (+80bp) is the 2030 RPI reform, the second (+61bp) is almost wholly asset-swap cheapening (absent in the real swap curve); the 2036-47
  plateau is a habitat anomaly. Restrict to one maturity month (Nov) to avoid seasonals.
- **Distant forwards cross-market (BAS/ML, Musings from Harley Bassman, 19 Feb 2010)**: USD-EUR 10y-forward 20y spread 122bp vs decade maximum 131bp;
  forwards go irrational under forced flows (Jun 2008: EUR 30y below 10y; 10y-forward 30y nearly touched 2.0%, below JGB 30y; reverted when
  positions were squared) (Convexity Maven, Forwards are NOT a Prediction, 12 Aug 2013).
