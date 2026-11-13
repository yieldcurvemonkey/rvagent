# Directionality, regimes and market notes for curve trades

Evidence tables behind the "Directionality" and "Regime" steps of [SKILL.md](../SKILL.md). Spread = longer yield - shorter yield, bp.
Bull = yields down, bear = yields up. Small-sample statistics are flagged; do not treat any single table as a strike or a signal on its own.

## 1. How much does the curve depend on the level?

| Evidence | Number | Source |
|---|---|---|
| UST monthly 1968-95: corr(steepness, 3m rate) / (steepness, 6y rate) / (curvature, steepness) | -0.43 / -0.04 / +0.79 | Salomon Brothers, Understanding the Yield Curve Part 7, Feb 1996 |
| Bull steepeners and bear flatteners more common than bear steepeners and bull flatteners (1968-95 monthly) | qualitative | same |
| 10y daily change on 5th-nearby short-rate future (USD, Mar 2022-Mar 2025) | beta 0.9, R2 just under 91% | Willer & Saunders, Trading Global Macro Markets, 2026 |
| 2s10s (bp) on 2y yield (%), last 2 months to 25 Feb 2020 | y = 52.361x - 55.756, R2 75.8% (positive slope: curve flattens in a rally) | J.P. Morgan, US Treasury Market Daily, 25 Feb 2020 |
| US monthly Jan 2015-Jan 2020: bull = 10y key rate -15bp or more, bear = +15bp or more, steepen/flatten = 2s30s moves > 5bp. Spot curve: bull-flat 6, bear-steep 5, bull-steep 1, bear-flat 3 | 11 of 16 directional months were bull-flatteners or bear-steepeners | Golub (ed.), BlackRock's Guide to Fixed-Income Risk Management, 2023 |
| Deliverable UST curve Sep 2000-Sep 2001: 10bp rise in the long yield came with 2.3bp flattening (1993 was an exception: 10y beta 0.46) | | Burghardt et al., The Treasury Bond Basis, 2005 |
| EUR swap PC1 explains 97-99% of curve movement; Bund PC1 (2010-11) peaks at 5y so 2s5s bear-steepens and 5s10s bear-flattens; in 1993-97 the 2y loading was as high as the 5y (active central bank) | | ING, Deconstructing the EUR yield curve, 15 Jan 2020; Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024 |
| EUR PC1 loadings largest 1y1y-5y1y, smallest 10y2y-30y10y: bear-flattening more likely than bear-steepening, bull-steepening more likely than bull-flattening | | Credit Suisse, PCA Unleashed, 24 Oct 2012 |
| Single-factor curve fits, 1Yx1Y vs 5Yx5Y curve on 1Yx1Y (Aug 2026): SONIA -0.55x + 2.9 (R2 89%, SE 7bp), ESTR -0.7x + 2.4 (93%, 7bp), SOFR -0.7x + 2.4 (93%, 9bp). Do not trade the residual when R2 is decaying (SONIA rolling 120d R2 ~100% to ~60%) | | J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026 |
| Correlation of daily changes, USD 1965-2024: 2s10s with 2s5s 0.82, 2s30s 0.88, 5s10s 0.63, 5s30s 0.47; 2s30s with 5s30s 0.76; 10s30s with 5s30s 0.76, with 2s30s 0.55; 1s2s about uncorrelated with everything (-0.17 to 0.01) | | Willer & Saunders 2026, Table 5.9 |

Curve sections and who drives them (Darbyshire 2022, Ch.16): 0-18m imminent central-bank action; 18m-5y forecast policy from growth/inflation;
5-15y benchmark futures maturities, volatile because of speculation and supply; 15-30y+ pensions and long-term funding, more stable, moved
only by significant events. Spreads and flies are directional because their legs respond in different proportions to the level.

## 2. Four move types (bull/bear x steepen/flatten)

Index = bp of curve move attributable to the mode over a window / sum of absolute curve moves over the same window; windows 2w, 1m, 2m, 3m
(BofA, US Rates Viewpoint: Understanding the yield curve dynamic, 23 Jul 2025; BofA, Monthly rates models, Apr/Aug 2025). Front-end driven =
bull-steepening + bear-flattening ("Fed footprint"); long-leg/belly driven = bull-flattening + bear-steepening. `scripts/curve_beta.py`
returns the same shares (`share_*`) from daily leg changes (bull/bear from the average leg change, steep/flat from the spread change).

| Mode | Typical macro reading (BofA) |
|---|---|
| bull-steepening | front-end/Fed driven, recession, pricing cuts |
| bear-flattening | expansion, pricing hikes |
| bull-flattening | late cycle, Fed restrictive, duration grab |
| bear-steepening | early cycle, Fed on hold, or supply/demand pressure on the back end, term premium |

Data points: 2s10s 2w split (bull-steep/bear-flat/bull-flat/bear-steep) 11/13/32/44% (22 Jul 2025 for the 2w window), 19/23/24/34% (1m), 23/18/33/27%
(2m), 20/20/30/30% (3m); 7 Apr 2025 2s10s front end drove about 43% of the last 2 weeks vs 48-62% over 2 months, while 5s30s was belly driven
(about 60%). Scenario likelihood use: recession roughly equals bull-steepening frequency, reacceleration roughly equals bear-flattening
frequency.

US 1-week annualised sovereign returns by mode since Jan 1993: bear-flat -0.8%, bull-steep +20.8%, bull-flat +23.3%, bear-steep -17.2%
(BofA, To everything there is a season, 23 Jan 2022). Equity (1m-change classifier, 1-day lag): bull-flat IR 0.99 (on 30.8% of the time), bear-steep 0.44,
bull-steep 0.38, bear-flat -0.12 (Willer & Saunders 2026, Fig 8.12). These returns are concurrent, not predictive. The twist-steepening state
(2y below and 10y above its 55-day average) is rare (about 6-7% of days), so its statistics rest on a small sample (Citi, The Messi Theory of Interest
Rates, 31 Jul 2026).

Zone diagnosis for each session: where did the curve move (front, belly, long end), how (parallel, twist, belly vs wings), why (policy path, growth
or inflation, term premium or supply)? Front-end leading is a policy day; belly driving means uncertainty and vol rising; long-end leading
is term premium, supply or long-run beliefs. If you cannot name the repricing, trade smaller or not at all; belly-led moves are messier, so size down
(Global Macro Method, STIR (Rates) Application Process, 25 Feb 2026). "One day does not make a trend" before re-weighting.

## 3. Cycle and policy-phase map (USD, applies by analogy to the other G10 central banks)

BofA cycle mapping (To everything there is a season, 23 Jan 2022): early expansion = bear-steepening (Fed anchors the front end; exhausts when
long rates reach the neutral-rate view, about 150-160bp of 2s10s in that cycle); mid-cycle = bear-flattening when a significant probability of
hikes in the next 6-12m is priced (2s10s flattening bias stronger 6m ahead of liftoff, Jun-04 and Dec-15 cycles); late cycle = bull-flattening
(inversion; collapse in dispersion of 1y forward rates is the late-cycle signal); end of cycle = bull-steepening with size set by the consensus terminal rate.

Willer & Saunders 2026 Ch.5: hiking cycles bear-flatten and easing cycles bull-steepen (beta 0.9); DV01-neutral 2s10s flatteners are profitable from about
50 trading days before the first hike (median from about -2.5% at -50d to 0 at day 0 and +2-3% by +100d); bear-steepeners come from a Fed seen behind
the curve (2021) or fiscal fears; late-cycle/on-hold bear-steepeners can stop out receivers placed around the last hike (largest: 2006 36bp, 2007
28bp, 2023 93bp; ended when the Fed turned dovish or equities weakened); 5s30s peaks and flattens earlier than 10y (30s lag the sell-off); supply does
not explain the curve (it explains swap spreads); rate vol spikes at the first cut, last cut, first hike and when the Fed accelerates and is quiet late in hikes and during the pause.

BoJ (same source): position in the front end, which is less driven by US rates; in a hawkish BoJ cycle flatteners often work, "though only if fiscal worries
do not take center stage"; Japan can take longer than the US to price policy peaks.

Consistency check on a flattening: normally short rates up a lot and long rates up less. A rotation (short up, long down) is a late-cycle event that
should not appear before the first hike; a flat curve with a wide MBS spread and high MOVE is "artificially flat" (Feb 2022: 5s30s +8bp, MBS-10y spread 85bp,
MOVE 94) (Bassman, Dangerous Curves Ahead, 15 Feb 2022).

### Inversion studies

- 10y receiver returns after an inversion (1m/3m/6m; hit rate), US (Willer & Saunders 2026 Table 5.7): 6m2s +0.78/+1.71/+0.48%, hit 70/70/60; 3m10s
  +0.26/+1.11/+1.03%; 6m5s +0.45/+0.76/+1.66%; 2s10s -0.79/-1.74/-2.15%, hit 40/33/33; 2s30s, 5s10s, 5s30s, 10s30s all negative. A 3m or 6m short leg
  works, a 5y/10y short leg does not, and the common 2s10s scores poorly. Probability a cut follows an inversion of at least 12.5bp within 6/12/24m:
  6m2s 58/74/84%, 2s5s 53/73/93% (shortest average, 7.7 months), 2s10s 50/57/86%, median over segments 44/65/93% (Table 5.8). Many results rest on fewer
  than 25 events and ignore costs; high-inflation cycles lengthen the inversion-to-cut lag.
- First front-end inversion to first cut (1-year forward swaps; slope change in bp, 2s10s / 5s30s), episodes May-95, Dec-97, Sep-00, Mar-06, Sep-08: the
  story ends with a steeper curve but timing is tricky; 1y after the signal 2s10s +55/+14/+190/-30/+151 and 5s30s -2/+32/+108/+15/+88; 1m-6m paths
  are mixed, so there is time even 6m after the first inversion to initiate steepeners or use options (Citi, The rocky road to a steeper curve, 18 Jan 2019). First
  3m/5y5y inversion (Aug 2019): 2s10s was steeper one year later in all three prior hiking cycles (Citi, Fixing the plumbing, 30 Sep 2019).
- Percentile conditioning (Citi, What to expect when you're expecting a turn, 20 Apr 2018; days when the last Fed move was a hike, 1971-2017): curves kept
  flattening 10-20 weeks after entering the flattest decile; in the 30-40 percentile bucket (2s10s 43-62bp) a flattener had hit rate 0.66 (6m) / 0.74 (1y),
  median 13bp / 54bp; in the 70-80 bucket 0.82 / 0.73.
- Regime-average fair value (swap, bp; 2s5s/5s10s/10s30s/2s5s10s/5s10s30s): on hold after cuts 129/93/69/36/24; start of hiking 106/74/63/32/10; 6m
  into hiking 69/55/49/14/6. Predicted 1y-forward value = sum over regimes of P(regime) x regime average, then subtract convexity cost (Citi, Flying Too High,
  20 Dec 2010). Regime averages rest on few cycles.
- Entry level has almost no predictive power for steepener P&L: EUR 10s30s 3m P&L regressed on entry level gives negligible pricing power (slope is highly persistent), initial roll
  also weak, "no such thing as a single strike predicting positioning washouts for steepeners" (Citi, A QT revolution, 17 Sep 2026).

## 4. Rate/vol co-movement (the dominant risk of long-end steepeners)

- Curve vs implied vol: higher-vol days bring flatter curves and belly underperformance, strongest in 2s5s30s, 5s30s, 5s10s30s (daily correlation with 3m implied
  vol, EUR: 2s10s -0.35 up-vol days / -0.52 down-vol days, 5s30s -0.61 / -0.68) (Citi, The Morning Call, 12 Aug 2026). Falling vol steepens the curve, ceteris
  paribus, because convexity of received long-dated rates is worth less (Nordea, EUR Rates Flash, 24 Jan 2020). 6m 2s10s vol (nv) = 0.19 x 2s10s (bp) + 34.44,
  R2 0.60 (Citi, Buying vol for less, 25 Sep 2019; calibrate outside zero-lower-bound regimes).
- EUR long-end steepeners (since 2022, 1m horizon): P&L correlation with the 10y rate and 3m10y vol is meaningfully negative for forward starts of 15y or more, mostly
  in same-direction (rates and vol both up) regimes; "steepening the long-end is somewhat similar to selling payer skew on belly rates". Same-sign sub-sample 3m
  steepener P&L = -0.24x + 2.47, R2 0.47 (unconditional -0.22x + 4.13, R2 0.36). Most of the asymmetry disappears once the received 5y leg is neutralised; correlations of
  the received leg with 10y5y/15y5y/20y5y/25y5y paid legs fall from about -0.60 (5y5y received) to -0.10 (20y5y received) (Citi, Euro Rates Weekly, 24 Sep 2026; A QT revolution, 17 Sep 2026).
  Washout case 23 Jul-8 Sep 2026: 10s cheapened > 25bp, vol unchanged, 10s30s barely moved; vol bounced and 10s30s flattened about 17bp in 4 sessions (carry-steepener stop-out).
- Directionality screen for conditional structures: scatter R2 of the directionality regression against the premium pick-up for the right conditionality
  and look for the upper-right corner (Huggins & Schaller 2024). See [curve-conditional-trades](../../curve-conditional-trades/SKILL.md).
- Carry/R filter: `Carry/R = Ex Ante Sharpe / (1 + |R|)`, `R` = correlation with the 10y outright; many curve trades have R of -0.5 to -0.9
  (USD 10s30s R -0.89), outrights near 1. USD 10y5y/15y5y/20y5y Sharpe 1.20, R 0.26, Carry/R 0.95; GBP 15y5y/20y5y Sharpe 0.90, Carry/R 0.70 (Goldman Sachs, Global Rates
  Best Trade Report, 30 Sep 2026). In a trending market z-score "best entry" screens are dominated by outright duration.

## 5. Flows that make slope directional

USD: variable-annuity/insurer receiving concentrated in 15-25y, corr(stocks, 15y5y/20y10y) about -23% (Citi, Trading long-dated convexity, 9 May 2019); callable
(Formosa) issuance hedged by receiving at the ultra-long end flattens it, more so as the curve flattens (calls deeper in the money) (J.P. Morgan, Renewed Formosa supply, 21 Feb 2020);
MBS convexity hedging creates level-dependent flows; fixed-to-ARM refi flattens the curve (Bassman, The Largest Volatility Sale Ever, 23 Mar 2010); the Fed, not Treasury
supply, dominates the curve (30y reintroduced 2006, 10s30s kept flattening under hikes) (Citi, US Rates Weekly, 21 Aug 2026). See
[flow-mbs-convexity-hedging](../../flow-mbs-convexity-hedging/SKILL.md) and [flow-structural-alm-demand](../../flow-structural-alm-demand/SKILL.md).
Japan: life-insurer target yields produced a 10s30s pivot (about 0.75% / 2%, 2010-15) and predictable 20s30s bear-flattening or bull-steepening until BoJ QE changed the regime
(During 2021). Pension regulation (NL, DK: market-rate discounting with UFR) makes funds short convexity, which flattens the long end in rallies. Banks are not natural buyers of
super-long duration, so bank-driven long-end flattening can fade once crowded (J.P. Morgan, Japan Fixed Income Markets Weekly, 21 Feb 2025).

## 6. Per-market notes (G10)

| Market | What matters for steepeners and flatteners | Source |
|---|---|---|
| USD | Fed-cycle map above. 5s30s preferred to 2s10s for steepeners because of lower negative carry. A Fed balance-sheet tightening implies a steeper 5s30s. Seasonality: curve flattens in May and November (Nov average 10s2s -3.8bp, 30s5s -4.2bp), 30s10s up in January 70% of years. 5s30s steepeners are crowded ("consensus winner of 2025"; twist-flattening risk). | Citi Global Macro Trade Ideas Radar 13 Aug 2026; Citi Global Economic Outlook 20 Aug 2026; BofA, Bond market seasonality explained, 6 Jun 2022; JWS Macro 13 Nov 2025 |
| EUR | PC1 loading pattern gives a bear-flattening / bull-steepening bias; long-end curve has structurally negative forward-spot roll; steepeners hurt in rates-plus-vol-up regimes; 30s50s most inverted despite lowest vols (Jul 2026 EUR -28.8bp, USD -26.6bp, GBP +16.8bp); Dutch pension reform (about EUR 400mn DV01 of payers over 2 years) supports 10s30s steepening with year-end receiving risk; German spline 6m forward roll +4 to +6.5bp (Sep 2018) so steepeners roll positively; benchmark switches distort 2s5s/5s10s history. Seasonality: July 10s5s up 75%, Feb 30s10s up 70%, 2s10s flattens Mar/May (late-April coupon reinvestment). | Citi Euro Rates Weekly 24 Sep 2026; Citi Markets 27 Jul 2026; JWS Macro 4 Sep 2025; Nordea 26 Sep 2025; During 2021; BofA seasonality 6 Jun 2022 |
| GBP | LDI/pension demand drives 30y+ anomalies and is pro-cyclical (lower yields, more hedging); 30s50s turned upward-sloping mid-2019; post-LDI loss of about GBP 500mn DV01 of long-end demand; DMO cutting long-end share of net issuance (28.4% to 9.1%) flattened 5s30s by an average 5bp in 10 days in 75% of 12 cases with short half-life; BoE QT redesign (permanently holding 2049+ gilts) a one-off bull-flattening; 10s/30s on 2s/10s regression y = 0.4x + 34.9 R2 75%; budget-risk steepeners. | Citi/QFSE Aug 2019; J.P. Morgan 21-22 Aug 2026; Citi 17 Sep 2026; JWS 4 Sep 2025 |
| JPY | 2s10s about 63bp vs 10s30s about 91bp near record lows (Feb 2025); flow-driven long-end flattening is a fade candidate once crowded; 5y anchors to the perceived terminal rate; consecutive BoJ/Fed/ECB hikes twist-flatten forwards; March bull-flattening from lifer superlong buying before the fiscal year-end (5s30s and 10s30s narrowed in 8 of 10 years), August 30s10s up 80%. | J.P. Morgan 21 Feb 2025; Citi Japan Rates Weekly 2 Oct 2026; BofA seasonality 6 Jun 2022 |
| CAD | Global direction dominates; seasonality: May and August curve flattens, January 30s10s up 70%; long-dated 15y5y/20y5y flattener was the most expensive convexity in the Sep 2019 screen (BE/RV 2.00). | BofA 6 Jun 2022; Citi 25 Sep 2019 |
| AUD | May 2s5s flattens about 70-75% of years, 20s10s up 88% (Budget/AOFM, Japanese buying), July 10s20s steepens about 63% (AOFM issues further out); 1y 2s5s10s screened in Sep 2026. | BofA 6 Jun 2022; Goldman Sachs 30 Sep 2026 |
| NZD | "Steepest curve in the world (adjusting for vol)": carry/roll harvester; 15y5y/20y5y screened top (score 1.39, Sep 2026). | JWS Macro 13 Nov 2025; Goldman Sachs 30 Sep 2026 |
| CHF | Sources are thin: a 1y 2s5s was a Sep 2026 screen pick. Apply the generic method; check swap-curve liquidity and the history of negative rates before trusting betas. | Goldman Sachs 30 Sep 2026 |
| SEK / NOK | 1Yx1Y/5Yx5Y curve SEK +81bp, NOK -42bp (Aug 2026); betas to 1Yx1Y about -0.6 (R2 86% / 83%); shorter forward grids (to about 1y10y / 5y5y); screened picks SEK 4y1y/5y2y, NOK Mar7/Mar8 flattener. | J.P. Morgan 21-22 Aug 2026; Goldman Sachs 30 Sep 2026 |

Seasonal tables are small samples (n about 20 years, 10 for Japan): a 70% up-ratio in 10 observations is weak evidence. See
[quant-seasonality-and-calendar-effects](../../quant-seasonality-and-calendar-effects/SKILL.md).

## 7. Supply and event studies

- Auction grid (BofA, US Treasury auction primer, 8 Mar 2024): 2s10s around 10y auctions 2023-24 sample, best steepener entry 9 days before and exit 3 days before +3.5bp, hit 55-58%;
  exit after the auction loses; 2022 sample mostly negative; only 12 observations, regime sensitive.
- Midterms (Citi, How to trade US midterm elections, 14 Aug 2026): 2s10s flattens into the election and troughs about 50 days after; 5 lost-trifecta and 1-3 held cases, short-lived.
- Treasury long-end buybacks funded with bills look Twist-like but are far smaller and are not QE; the market priced extra bill issuance and the front curve flattened (FT, 20 Aug 2026;
  J.P. Morgan FX Markets Weekly, 21 Aug 2026). Policy support may cap the back end only temporarily if fiscal and real-yield drivers persist.
