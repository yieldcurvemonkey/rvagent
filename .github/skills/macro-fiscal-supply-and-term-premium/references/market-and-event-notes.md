# Market and event notes: fiscal supply and term premium

Supplement to [SKILL.md](../SKILL.md). Figures are dated and attributed. Re-check them before reuse, because
debt-limit headroom, bill-share tolerance and the 30y levels all move with the cycle.

## Per-market differences

| Market | What differs | Practical rule | Source |
|---|---|---|---|
| USD | Bill share is the main issuance lever. Treasury can cut or lengthen the coupon mix, buy back 10-30y debt and move auction sizes. Swap spreads are the main expression of fiscal strain. | Trade fiscal and supply views in swap spreads and 20-30y, not in 2s10s or 5s10s. Watch the 30y level (5.3% and 5.5% are cited trigger levels). | Citi, US Rates Weekly (Can Secretary Bessent and Chair Warsh save the curve?, 21 Aug 2026); BofA, US Rates Viewpoint (Lower UST WAM => backdoor easing, 2 Jul 2025) |
| EUR (Germany, France, Italy, Spain) | Sovereign spreads (OAT-Bund, BTP-Bund) carry the fiscal signal. Solvency II (UFR 3.30%, convergence alpha 20% to 11% over 2027-32) drives long-end insurer demand. Use net cash requirement (NCR), not gross issuance, to measure supply net of ECB runoff. | Gross EGB supply overstates net supply in 2027 (gross EUR 1.5trn, NCR EUR 616bn, per the Citi note cited). Use the NCR and the ECB net position. | Citi, European Rates Strategy (Latest views, 20 Aug 2026); Citi, European Rates Weekly (What to do about OATs?, 1 Oct 2026); Citi, European Rates Weekly (A QT revolution, 17 Sep 2026) |
| GBP | DMO long-end cuts were short-lived in the 2022-26 episodes cited (12 cuts since the long share of net issuance fell
  from 28.4% to 9.1%: gilt curve about -2bp on average over 5 days; 5s30s about -5bp over 10 days in 75% of cases;
  J.P. Morgan, 21-22 Aug 2026). The BoE QT redesign (gilts beyond 2049 held permanently, sales to the DMO) is a one-off bull-flattening of ultras, not a repeatable trend. Linkers are about one quarter of debt but about two thirds of the interest bill in 2022-23 (BofA). | Fade the announcement-driven repricing, keep the core steepener. Fiscal risk shows up around the Autumn Budget. | J.P. Morgan, Global FI Markets Weekly (21-22 Aug 2026); Citi, European Rates Weekly (A QT revolution, 17 Sep 2026); BofA, Global Inflation-Linked Primer (2nd ed., 22 Jul 2025) |
| JPY | MoF cuts 20-40y issuance rather than buying back, which flattened 10s30s from mid-2025. BoJ holds about 48% of JGBs, so free float (debt less BoJ holdings, percent of GDP) is a swap-spread fair-value input. Yield-control or YCC talk would undo FX defence, because the price is a weaker currency. | Supply cuts support super-longs; a fiscal break higher is the risk. Free float of about +5pp is worth about 3bp tighter in fair-value 10y spread (GS). | Citi, Global Asset Allocation House Views (Bessent and the back end, 21 Aug 2026); GS, Global Rates Trader (Reaching Limits, 2 Oct 2026); JWS Macro (Duration is diseased, 4 Sep 2025) |
| AUD / NZD | Limited fiscal-supply material in the sources. One J.P. Morgan model uses government debt and private credit as inputs to the AUD 10y swap-spread model, with swap spreads moving semi-government spreads at a beta of about 0.6. | Use only the model stated in the source, and test beta on your own data. | J.P. Morgan, Global FI Markets Weekly (21-22 Aug 2026) |
| CAD / CHF / SEK / NOK | No fiscal-supply or term-premium material was extracted from the sources. CAD 10s30s sits inside the global curve factor (Citi, 3 Feb 2017). CHF is a classic debasement indicator (JPM FX dashboard). | Treat as cross-market context only. | - |

## Midterm and election priors

- Event study: cumulative change in 2y, 10y, 30y, 2s10s and 5s30s over plus or minus 125 business days around Election
  Day, from 1960. Conditioned on the outcome: trifecta lost (1994, 2006, 2010, 2018, 2022), trifecta held (1962, 1966,
  1978). Use as a prior to update. Citi, Quantitative Global Macro (How to trade US midterm elections, 14 Aug 2026).
- Uncertainty premium priced from about 50 business days before, peaking a few weeks before (same source).
- 30y swap spreads widened in the week after 4 of 5 midterms (exception 2014, already divided government). The median
  change fades back to 0bp within a month. 10s30s flattened over the following month in 3 of 5 (2006-2022). Citi, Multi-Asset
  Strategy (US midterms on the mind, 2 Oct 2026).
- Samples are small (five lost trifectas, one to three held, 1978 atypical). Treat as priors.
- A quarterly refunding that fell the day after an election (4 Nov 2026 in the cited note) is a catalyst. A cut to
  long-end coupon sizes in favour of bills would widen US spreads further (Citi, 2 Oct 2026).

## Event and regime examples

- **UK, Sept 2022 (Truss mini-budget).** About GBP 45bn of unfunded tax cuts and energy support, about GBP 72bn of extra
  borrowing over six months (about 3% of GDP). Gilts sold off more than 100bp in a week. The curve first flattened
  (more BoE hikes priced), then steepened sharply (fiscal fear). GBP fell, which is unusual for a fiscal shock. The
  BoE bought up to GBP 65bn of gilts (28 Sep to 14 Oct). The authors read forced selling by levered LDI funds (margin
  calls) as the bigger driver, not the fiscal news alone. Source: Willer and Saunders, Trading Global Macro Markets
  (2026), Truss box.
- **UK, 1976 rollover turmoil** (cited in Delao and Li, NBER 2026 as a vignette). Long gilts fell about 20% within
  months. Respondents downweighted rollover risk by 17pp (investors) and 18pp (voters).
- **Euro crisis, 2010-12 (cited in Papic, Geopolitical Alpha, 2021).** Bond-market pressure forced policy (EFSF, LTROs,
  "whatever it takes"). Use this as the precedent for "market constraint forces policy", not as a template for timing.
- **Euro area, Mar 2020 (Nordea, EUR Rates Flash, 17 Mar 2020).** Sovereign credit risk appeared in ultra-long ASW.
  Long-dated French (2066) and Austrian (2117) ASW reached roughly 115bp and 150bp respectively (levels, read from a
  chart), while the long German Bund cheapened far less. Use as a crisis analogue for sovereign credit premium, not
  as a level.
- **US, Aug 2026 buyback episode.** Long-end buybacks doubled from USD 2bn to at least USD 4bn per operation on 19 Aug
  2026, after the 30y reached about 5.2-5.3%. Yields fell within minutes and round-tripped the next day (30y +6bp to
  5.24%, reversing most of the 9bp fall). Measured half-life about one day (Financial Times, 20 Aug 2026). The
  dollar, gold and breakevens reacted more durably than the curve.
- **US, Feb 2017 (Citi, Going nuclear on the curve, 3 Feb 2017).** A fiscal 10s30s model put the curve 28bp too flat with
  no fiscal expansion and 35bp too flat with a 2pp deficit/GDP increase. The SOMA taper announcement was worth about
  10-15bp of sell-off. Use as an example of how fiscal fair value is scenario-based.

## Solvency and debasement narratives (what to check)

- **Debasement basket (Citi Macro Brief, 21 Aug 2026).** Five gauges: higher gold, lower USD, steeper UST curve, higher
  breakevens, higher S&P 500. The basket was near record highs in Jan and June 2026. It is a monitor, not a trigger.
- **Good and bad debasement (same source).** Good: long-end yields stabilise under a hawkish chair. Bad: acute
  long-end weakness plus a dovish chair, with higher gold, lower USD, higher breakevens, an acute bear steepener and
  a falling S&P.
- **Gate for a fiscal-dominance or debasement call (J.P. Morgan, FX Markets Weekly, 21 Aug 2026).** Require all of:
  widening breakevens; outperformance of the fiscal-basket currencies (good-fiscal minus bad-fiscal); and a dovish
  Fed. In Aug 2026 none was present.
- **Solvency beliefs and flows (Delao and Li, NBER WP 35612, Aug 2026).** Stated probability of a US debt crisis within
  10 years averaged about 50%. Showing CBO projections raised it by 14.9pp (se 2.7) but changed planned Treasury
  holdings by only 4.2pp (se 4.1, insignificant). 72% of concerned investors made no concrete portfolio change.
  Use: fiscal news moves risk perception far more than holdings.
- **Yield suppression and the currency (Citi GMS, 19 Aug 2026; Bloomberg, 21 Aug 2026).** Suppressing long yields
  without fixing deficits or inflation moves pressure to gold, the dollar and breakevens. Trade the transmission, not
  the yield.
- **Official-versus-private holder shift (FT Alphaville, 20 Aug 2026).** Fed SOMA Treasuries peaked near USD 6trn and
  are about USD 4trn now. Official holders went from about 50% of marketable debt in 2006 and 2016 to about 27% in
  2026. Private holders are more valuation-sensitive, so the term premium needs higher yields to clear.
- **Bond glut (Willer and Saunders, 2026).** Each crisis socialises losses, so public debt jumps, stabilises and jumps
  again until markets become a binding constraint. Index-weight headwind: market-cap-weighted debt indices overweight
  the largest issuers.

## Supply cut and buyback signal ladder (Citi, 21 Aug 2026, as cited)

1. Bigger buybacks.
2. Signal no coupon size increases (private bill share about 21% at the time).
3. Shift 20y and 30y issuance shorter.
4. End the 20y, "unlikely unless 30y yields surpass 5.5%".

The 20y benefits most, because it trades poorly against 10s and 30s. Read each rung against the 30y level, not against
the buyback size. A price-level trigger that defends a yield tends to make every later rise a test.
