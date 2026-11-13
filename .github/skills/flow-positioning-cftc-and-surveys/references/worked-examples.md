# Worked examples and numbers: positioning and flows

Companion to [SKILL.md](../SKILL.md). Every number is as stated in the cited source; arithmetic checks are marked
"(own)". Use these to calibrate what a reading looks like, not as current data: dates matter, and several figures
come from chart reads in the source.

## 1. Roll views, close 8 May 2019 (Citi, Deal or no deal, 10 May 2019)

| Contract | Roll view (ticks) | Positioning detail |
|---|---|---|
| TU (M9-U9) | -5.875, bearish | 10.7% rolled vs 3.2% average pace |
| FV | -3.25, slightly bearish | AM 31% of OI vs 34% prior; 43% high; regression said more than 1 tick too cheap |
| TY | -7.5, slightly bearish | AM 16% of OI vs 21% prior |
| UXY | -19, neutral | AM collapsed to 1% of OI |
| US | +21.0, neutral | same CTD in both contracts |
| WN | -20.0, bearish | AM 58% vs 55%; 3 ticks cheap to carry but about 1 tick rich vs the positioning regression; roll early |

Lesson: the sign of the view and the sign of the residual can differ. WN was cheap to carry and still rich to positioning.

## 2. Roll views, 18 Aug 2026 (Citi, Treasury Futures Roll Sep26-Dec26)

| Contract | Roll view (ticks) | AM % of OI |
|---|---|---|
| TU | 3.875, slightly bullish | about 38.5%, smallest since the H4-M4 roll |
| FV | 4.25, bearish | 44.8%; roll near FV whereas past rolls traded cheap |
| TY | 9, bearish | 36% to 46.8%, largest since 2007 (the source labels this "roll slightly rich" as well) |
| UXY | 10.25, slightly bullish | 27%, stable |
| US | 10.5, slightly bearish | 29.1% vs 25% and 26.3% prior |
| WN | 13.25, neutral | 43.6%; peaked at 47.4% in February; shorts fell from 31% to 19% of OI |

Lesson: a source's roll label can contradict its own bullet on the same contract. Record the label and the number side by side.

## 3. Form PF swap-trade path and a dating caution (BIS, Dec 2025; Conks, Nov 2025)

BIS (Q2 2025 data, $bn): hedge-fund longs 2,379; shorts 1,748 (1,060 basis futures shorts matched to cash; 688 other RV).
Upper bound on the swap trade: 2,379 - 1,748 = 631 (own check). Path of the upper bound: 281 (Q1 2024), 707 (Mar 2025),
631 (Jun 2025). The -11% in April 2025 was the turbulence that caught funds wrong-footed.

A chart-read table elsewhere in the library tags the same 2,379 / 1,748 pair with a November 2025 date, and shows CFTC
hedge-fund UST futures of 1,078 short / 200 long. Those are a different measure and a later publication date. Always
record the data date and the publication date separately; cite the BIS date for the BIS figures.

## 4. Positioning dashboard, 25 Feb 2020 (J.P. Morgan, Canary in a coal mine)

1y z-scores: survey net longs -1.30; CFTC net longs (ED plus UST futures) -1.45; CTA beta to 10y -0.14; core-fund
beta -0.97; macro hedge-fund beta -0.64; T-note put/call -0.95. Read: the dashboard is short-leaning across the board,
but the CFTC headline was driven by WN (see SKILL.md, worked example D).

Per-contract CFTC non-commercial positions (000s of TY-equivalents, as stated):

| Contract | Current | YTD change | 5y mean | 5y sd | 5y z |
|---|---|---|---|---|---|
| ED | 616 | +154 | -326 | 540 | 1.7 |
| TU | -91 | +65 | -51 | 69 | -0.6 |
| FV | -145 | +30 | -161 | 124 | 0.1 |
| TY | -306 | -72 | -140 | 233 | -0.7 |
| US | -126 | +103 | 2 | 120 | -1.1 |
| TN | -113 | -108 | 1 | 37 | -3.1 (since inception) |
| WN | -1,891 | -205 | -594 | 433 | -3.0 |
| Total | -2,056 | -33 | -1,267 | 920 | -0.9 |

Context for WN: a record net short, up 60% in six months; the 25s/30s regression (R^2 84.4%) made it an RV leg.

## 5. Momentum vs contrarian by positioning percentile (BofA, Apr 2024; BofA, Mar 2025)

Average next-10y move by 5y positioning percentile bucket (the source says "presumably bp"; 1, 4, 8, 12, 16 weeks, Apr 2024):
- Non-commercial ex-LF, 0 to 10th percentile: +2, +1, +1, +2, +3. 90th to 100th: -1, -2, -2, -1, -2.
- LF, 0 to 10th: -1, -1, -1, -1, -2. 10 to 20th: +4, +4, +5, +5, +5. 90th to 100th: -1, -2, -1, 0, 0.

Fund duration bucket (BofA, Mar 2025; 10y move vs average at 1, 2, 3, 4, 5, 6 months):
- 80 to 90th percentile (long duration): -17, -28, -43, -58, -65, -88 bp: rates rallied after high duration, so this is a follower.
- 10 to 20th percentile: +19, +37, +43, +36, +35, +41 bp.

Dials on 10 Mar 2025 (5y percentiles): duration 48; curve 64 (a higher curve percentile means flatter). Read the sign per
indicator: the same test gave follower for fund regressions and contrarian for the futures proxy.

## 6. Options-flow sentiment, 2020 (BofA, SDR: what do FX options flows tell us, Feb 2021; FX, not rates)

Cumulative put/call since January 2020, most bullish to most bearish for the currency against USD, as stated: NOK about 50%;
JPY about 81%; EUR about 82%; GBP about 98%; CHF, CAD, AUD, NZD about 106%; SEK about 122%. NOK and SEK volumes were low
and were excluded from the main analysis.

Notional-weighted average strike: February 2021 averages were 1.2220 for EURUSD and 1090.25 for USDKRW; the authors
expected spot to converge on these. The strike signal gave a 64% hit rate for the direction of next month's average
spot (2020), and 59% for next month-end spot, against 58% for the change in cumulative put/call.

Noise filter: mean absolute error of monthly average strike vs average spot, divided by spot. Below 1% (most reliable):
EURCHF, USDJPY, USDSGD. Noisiest: USDPLN, USDZAR, USDBRL, at about 6% to 7.5%.

## 7. CTA stop-loss episodes (BofA, Systematic Flows Monitor, Jun 2025)

- 10 Oct 2018: 9 of 12 models stopped. 24 Jun 2016: 7 stopped. Both produced large sigma moves.
- 3 Apr 2025: no stops, and the move was fundamental (tariff shock).
- Rule of thumb in the source: 3 stops are unreliable; 4 or more of 12 is the empirical threshold for an above-average
  sigma move. Nine of the 15 largest one-day sigma declines since 2010 coincided with stop waves.

## 8. Convexity-adjustment trades (Citi; positioning-driven CA residual)

| Trade (date) | Structure | Entry CA (bp) | Exit / result | Note |
|---|---|---|---|---|
| Sell Blues, hedged (9 Feb 2017) | buy 2,000 H0-Z0 ED; pay $2bn matched swap; pay 2s5s10s belly | 8.8 | closed 6 Jun 2017 at 6.6bp, +$552k | target +$600k, stop -$350k; $200k DV01 |
| Sell Greens (15 May 2017) | buy 1,000 M9-H0 packs; pay $1bn swap | about 4.5 | closed 8 Aug 2017 at 2.65bp (from 4.3), +$476k | roll about 0.88bp per 3m; short covering confined to Blues and beyond |
| Sell Blues (8 Jan 2018) | buy 1,000 H1-Z1 packs; pay $1bn swap | 6.5 | carry about +$140k per 3m | CA 7.13bp vs model +4.26bp; CA-implied vol 105.4 vs 3m realised 50.4 (ratio 2.1) |
| Sell Blues (11 Jun 2021) | buy 1,000 EDM4-H5; pay $1.01bn swap ($100k DV01) | 7.9 | closed 3 Dec 2021 at 3.4bp, +$389k | target 4bp tightening, stop 3bp widening |
| Sell Blues (17 Feb 2023) | buy 1,000 SFRH6-Z6; pay $1.17bn swap ($100k DV01) | 12.7 | target 4bp, stop 2.5bp | Blues CA 13.09 vs model 9.44; Golds 21.24 vs 13.87; CFTC data stale at entry |

Arithmetic (own): 2017-02 entry to exit is 2.2bp x $200k/bp = $440k, against +$552k reported (carry and hedge
make up the rest). 2021-06 is 4.5bp x $100k/bp = $450k, against +$389k reported.

Snapshot, 13 Jan 2017 (Citi): Blues H0-Z0 CA 9.96bp vs model +4.48bp (1y z 2.73); implied vol 125.2 vs realised 95.2;
AM and LF added more than $12.5mn DV01 of ED shorts post-election; OI rose 500k contracts after the 10 Jan CFTC report
even as swap rates fell, so shorts were stretched.

## 9. Callable and vega supply (Citi 2017, 2023, 2026; J.P. Morgan 2020)

- 2016 gross callable issuance $57.9bn, net $37.1bn, vega $104.2mn. 2017 year to April: gross $24.5bn, net $23.5bn,
  vega $39.7mn.
- 2022 year to June: gross $14.30bn, vega $36.0mn. 2023 year to June: gross $2.44bn, vega $2.6mn.
- 2026 year to October: gross $18.14bn, redeemed $2.42bn, net $15.71bn, vega 16.6 ($mn). 2025: gross $13.88bn,
  net $10.99bn, vega 13.9.
- Taiwanese lifers, Q1 2020: vega supply about $20mn per bp of vol, vs $40mn from the raw Bermudan pricer. About $85bn
  of notional was up for call in 2020; the empirical model expects about $30bn redeemed, vs $78bn from the raw pricer.
  Call efficiency was about 50%; raw models overstate supply by about 2.5x. Quarterly empirical / raw ratio: Q1 47%,
  Q2-Q3 about 32%, Q4 24%.

Callable vega is a supply flow for vol and the long end; the mechanics belong in
[vol-structured-flows-and-vega-supply](../../vol-structured-flows-and-vega-supply/SKILL.md).

## 10. Convexity and bank duration flows (J.P. Morgan, Sep 2019 to Mar 2020)

- Week with swap rates up 21 to 26bp: hedgers delivered about $90bn of 10y-equivalents (Sep 2019).
- Banks' duration gap: up to about $1.5tn of 10y-equivalent short duration delivered to banks since 2 Jan 2019; pinning
  the swap curve at 0% adds only about $230bn through year-end; banks receiving swaps is "a very bearish setup for
  intermediate swap spreads" (Mar 2020).
- COVID rally: banks' duration contracted about $161bn of 10y-equivalents in one month; VA duration contracted $23bn in a
  week (Feb 2020).

## 11. Official flows: FX intervention and UST swap spreads (BofA FX primer, Jul 2024)

| Episode | Size (JPY bn) | 2y / 5y / 10y yield change (bp) | 2y / 5y / 10y swap spread change (bp) |
|---|---|---|---|
| 22 Sep 2022 | 2,838 | +7 / +25 / +18 | -2 / 0 / -2 |
| 21 Oct 2022 | 6,350 | -11 / +14 / +1 | -1 / -3 / -1 |
| May 2024 | 9,789 | -25 / -17 / -26 | -3 / -1 / 0 |

Expected direction for USD-selling intervention: cheaper USTs and tighter front-end and intermediate swap spreads.
About 65% of official holdings are under 5y; foreigners held 38% of USTs ex bills, down from 48% at end-2019.

## 12. Holder and TIC readings (Citi, Aug 2026; J.P. Morgan, Aug 2026)

- June 2026 valuation-adjusted foreign long-term holdings: -$28bn; officials -$28.3bn; private +$0.4bn; Cayman -$32.1bn
  (z -3.03); Canada +$29.5bn (z 1.57). Custody distorts the country split: wait for a string of months.
- J.P. Morgan (Aug 2026) cut its 2026 foreign demand forecast from $500bn to $450bn; foreign share of bills was 5.4%.

## 13. Pension funded ratio and rates (J.P. Morgan, Sep 2018 and Apr 2020)

| Date | Assets ($bn) | Liabilities ($bn) | Funded ratio (own check) |
|---|---|---|---|
| 29 Dec 2017 | 1,555 | 1,775 | 87.6% |
| 31 Aug 2018 | 1,547 | 1,657 | 93.4% (nowcast 93.9%) |
| Feb 2020 | 1,602 | 1,949 | 82.2% |
| Mar 2020 projection | 1,524 | 1,899 | 80.3% |

Between Dec 2017 and Aug 2018 the 30y swap rose from 254bp to 295bp. Higher long yields cut liabilities by $118bn while
assets fell $8bn, so the funded ratio rose. A full credit-spread reversal would take the 2020 ratio to about 76%.
Profit-taking on hedges is "secondary market supply of Treasury duration, and bearish for long-end spreads".

## 14. Survey and sentiment mechanics (BofA, Nov 2024; BofA, Sep 2024)

- Bull-bear index scaled -100 to +100 (0 neutral), computed separately for exposure and view. Plot exposure minus view.
- Sentiment turning constructive without exposure following means investors stay cautious.
- A 1y z of survey net longs below -1.3 with neutrals near the top of their range (J.P. Morgan 2020) meant a short base
  not yet crowded, not a squeeze setup.

## References used here
- BofA Global Research - US Rates Watch, Mixed UST positioning picture (22 Apr 2024); Long UST outflows and dealer holding highs (10 Mar 2025); US Rates Viewpoint, UST supply and demand in '25 (26 Nov 2024); UK Rates Viewpoint, Back to school (5 Sep 2024); FX Viewpoint, SDR: What do FX options flows tell us? (1 Feb 2021); Systematic Flows Monitor, More CTA models = better impact estimates (2 Jun 2025); FX Primer, FX intervention primer: G10 (8 Jul 2024).
- Citi Research - Deal or no deal (10 May 2019); Treasury Futures Roll Sep26-Dec26 (18 Aug 2026); Sell Blues convexity adjustments, hedged (9 Feb 2017); Swearing in huge expectations (13 Jan 2017); Buy long expiries (17 Jan 2017); Fair value vs seasonality (1 May 2017); Value in Greens convexity (15 May 2017); Sell Eurodollar convexity in Blues (8 Jan 2018); Left-side vols' outperformance (22 Jun 2021); Time for moderation (17 Feb 2023); Short Blues convexity via futures/swaps (21 Feb 2023); Forward steepener and vol divergence (12 Jun 2023); Fading vega dislocations (5 Oct 2026); Can Secretary Bessent and Chair Warsh save the curve? (21 Aug 2026).
- J.P. Morgan - Canary in a coal mine (25 Feb 2020); Taiwanese demand for US fixed income in 2020 (10 Jan 2020); Will mortgages bail banks out of their duration short? (27 Mar 2020); Dynamic hedgers are long, banks are short, and both are buyers of spreads (13 Sep 2019); Markets struggle to feed the convexity beast (28 Feb 2020); Issuance, pensions, and long-end spreads (14 Sep 2018); Pension re-risking and long-end swap spreads (3 Apr 2020); US Bond Futures Rollover Outlook (12 Aug 2026); Global Fixed Income Markets Weekly (21-22 Aug 2026).
- BIS Quarterly Review - Goodbye Libor, hello basis traders (Dec 2025); Conks (Monetary Mechanics, Substack), Plumbing Notes: The Post-QT Era (24 Nov 2025).
