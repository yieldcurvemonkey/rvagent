# USD reserves, regressions and analogs (detail)

Companion to [SKILL.md](../SKILL.md). Every level is date-stamped. Administered rates, facility sizes and
balances move; pull current values from the data before using any of them. Sign conventions follow the body:
spreads are rate minus rate, in bp; SOFR-FF = SOFR minus EFFR. Where a source wrote a futures-style "SOFR/FF"
or "FF-SOFR", the sign is flipped and the flip is stated.

## 1. Liquidity regressions (dated vintages, not one model)

The published fits are not one model. Each vintage has its own sample, regressors and regime weights. Use them to
understand the shape (the slope steepens as reserves get scarcer), not as coefficients to hard-code.

| Vintage (source, date) | Dependent (bp) | Regressor | Fit | Note |
|---|---|---|---|---|
| BofA, Fed QT Beyond Taper (22 Oct 2021), linear, from Jun 2020 | SOFR-IOER | reserves/GDP | -2.3505 x + 31.678, R2 0.85 | cash proxy |
| same | SOFR-IOER | marketable debt ex-Fed / GDP | 1.2102 x - 95.008, R2 0.67 | collateral proxy |
| same | FF-IOER | reserves/GDP | -1.0997 x + 14.363, R2 0.72 | |
| BofA, Fed QT Beyond Taper, log, 2015-19 | SOFR-IOER | reserves ($bn) | -42.29 ln x + 314.47, R2 0.60 | pre-2020 regime |
| same, Jun 2020 onward | SOFR-IOER | reserves ($bn) | -25.59 ln x + 202.56, R2 0.91 | beta falls as reserves get abundant |
| same, 2015-19 | FF-IOER | reserves ($bn) | -30.24 ln x + 224.36, R2 0.91 | |
| same, Jun 2020 onward | FF-IOER | reserves ($bn) | -12.26 ln x + 96.632, R2 0.74 | |
| BofA, Monthly rates models Apr 25 (7 Apr 2025) | SOFR-IORB | ln(x), x = (ON RRP + reserves)/GDP in % | regime 1 (3Q20-1Q21): -34.59 ln x + 88.95, R2 0.73 | equal-weighted regimes |
| same | SOFR-IORB | same | regime 2 (2Q21-3Q23): -4.96 ln x + 4.53, R2 0.06 | |
| same | SOFR-IORB | same | regime 3 (4Q23-18 Dec 24): -9.16 ln x + 16.6, R2 0.17 | |
| same | SOFR-IORB | same | regime 4 (19 Dec 24 on): -45.02 ln x + 100.13, R2 0.12 | unstable, see below |
| BofA, Repo sensitivity May 25 (8 May 2025) | SOFR-IORB | same | regime 4 re-fit: -11.58 ln x + 20.96, R2 0.04 | reweighted 30/10/30/30 |
| BofA, Repo jump & Fed bill backfill (20 Oct 2025) | SOFR-IORB | ln(x), x = (reserves + ON RRP)/GDP in % | -8.065 ln x + 13.912, R2 0.34 | EFFR-IORB: -0.448 ln x - 5.8136, R2 0.14 |
| BofA, Monthly rates models Aug 25 (4 Aug 2025) | EFFR-IORB | Fed liquidity/GDP | sensitive 3Q20-3Q21: -10.55 ln x + 26.54, R2 0.74; sticky 4Q21 on: -0.074 ln x - 6.82, R2 0.02 | EFFR sticky about 7bp below IORB |

Notes on these fits:

- **Regime weights differ by edition.** Aug 25 edition: 45/10/45 over three regimes. Apr 25: four equal regimes.
  May 25: 30/10/30/30. Treat any blended forecast as edition-specific.
- **Regime 4 is unidentified.** The Apr 25 and May 25 fits differ in sign and size (-45.02 vs -11.58), and a third
  extraction reads +8.92 ln x - 29.16 (R2 0.01). The source excluded that window as distorted by the debt limit.
  Do not fit or forecast with it.
- **Sign caveat.** One text extraction of the Apr 25 note dropped minus signs. The fitted slopes must be negative:
  less liquidity means more SOFR above IORB. A positive log slope would reverse the economics.
- **Mapping.** The equation-to-period mapping in some extractions is inferred from order. Verify against the
  original period labels before relying on a specific regime's number.
- **Weekly-change betas (Citi, Time for moderation 17 Feb 2023; SOFR/FF spiking into quarter-end, 27 Jun 2025).**
  Beta per $100bn, t-stat in brackets. Each regressor entered on its own.

  | Series, sample (as printed) | Reserves | T-bills | T-bills minus reserves |
  |---|---|---|---|
  | SOFR minus RRP, 2013-25 | -0.67 (-3.3) | 0.27 (0.7) | 0.62 (3.3) |
  | SOFR minus RRP, 2021-25 | -0.39 (-2.4) | 0.07 (0.2) | 0.33 (2.3) |
  | SOFR/FF, 2010-25 (printed; FF minus SOFR) | 0.84 (3.7) | -0.41 (-0.9) | -0.79 (-3.8) |
  | SOFR/FF, 2021-25 (printed; FF minus SOFR) | 0.38 (2.3) | -0.07 (-0.2) | -0.32 (-2.1) |

  The two SOFR/FF rows are in FF-minus-SOFR form. Their SOFR-FF betas are the negatives: 2010-25 reserves -0.84,
  T-bills +0.41, T-bills minus reserves +0.79 per $100bn; 2021-25 reserves -0.38, T-bills -0.07 (sign flips to +0.07),
  T-bills minus reserves +0.32.

  Since the pandemic, reserves are the main driver and bills alone are insignificant. Bills still capture non-linear
  moves (summer 2023: reserves flat, bills surged, SOFR volatility followed), so keep them in ahead of a TGA rebuild.
  Full-sample betas are much larger than post-2021 betas: do not pool them.

- **Bills-minus-reserves level (Citi, Feb 2023 and Aug-Oct 2026).** Earlier fit, in the source's FF-minus-SOFR form:
  y = -0.011 x + 5.084 (R2 0.59), x = bills minus reserves in $bn, roughly 1bp per $100bn. The beta changed with policy stance: it was
  much lower when a hawkish Fed pulled cash into the front end. In Aug 2026 the stock of private bills minus reserves
  hit a record while SOFR fixed below IORB on most days. Citi read that as a structural change in liquidity needs.
  The stock is not the signal; the TGA rebuild pace and reserve demand are.

- **Reserve-to-spread table (BofA, Repo jump 20 Oct 2025; monthly averages, bp; reserves + ON RRP in $bn).**

  | Month | TGCR minus IORB | SOFR minus IORB | FF minus IORB | Reserves + ON RRP |
  |---|---|---|---|---|
  | Jun 2025 | -10.0 | -8.0 | -7.0 | 3,558 |
  | Jul 2025 | -7.9 | -6.3 | -7.0 | 3,527 |
  | Aug 2025 | -7.0 | -5.6 | -7.0 | 3,367 |
  | Sep 2025 | -1.8 | +0.6 | -6.7 | 3,135 |
  | 1-16 Oct 2025 | +0.2 | +3.3 | -5.3 | 2,997 |

  The fall in reserves plus RRP from about 3.56tn to 3.0tn moved SOFR from 8bp below IORB to 3bp above it. FF
  barely moved. That is the pattern to expect: repo reprices first, the policy-rate-based fed funds rate lags.

## 2. Facility and administered-rate levels (dated)

| Date (source) | Target range | IORB | ON RRP | SRF rate | Discount window | EFFR | Other |
|---|---|---|---|---|---|---|---|
| 12-17 Sep 2024 (Conks 19 Sep 2024) | 5.25-5.50 | 5.40 | 5.30 | 5.50 min bid (top of range) | 5.50 | 5.33 | |
| 26 Nov 2024 (Conks 27 Nov 2024) | 4.50-4.75 | 4.65 | 4.55 | | | 4.58 | |
| 27 Dec 2024-2 Jan 2025 (Conks 5 Jan 2025) | 4.25-4.50 | 4.40 | 4.25 | | | 4.33 | |
| 1 Jul 2025 (BofA, Primer Fed policy plumbing '25, 8 Jul 2025) | 4.25-4.50 | 4.40 | 4.25 | 4.50 | 4.50 | 4.33 | SOFR 4.44 in that note |
| 3 Oct 2025 (Conks 6 Oct 2025) | 4.00-4.25 | 4.15 | 4.00 | 4.25 | | 4.09 | SOFR 4.18, TGCR 4.16 |
| 23 Oct 2025 (Conks 26 Oct 2025) | 4.00-4.25 | 4.15 | 4.00 | | 4.25 | 4.11 | SOFR 4.24, TGCR about 4.21 |

Other facility facts (as stated in the sources; check current terms):

- **ON RRP:** soft floor for MMFs, GSEs and some others. Counterparty cap $160bn per counterparty per day (per fund,
  not per family). About 90% of balances are MMFs. Window closes 1:15pm. About 160-177 counterparties across sources.
- **SRF:** daily fixed-rate repo with primary dealers and banks against Treasuries, agency debt and agency MBS.
  Aggregate offering $500bn. Two operations: morning 8:15-8:30am (regular from 26 Jun 2025, settling by about 9am)
  and afternoon 1:30-1:45pm (tri-party, settling about 3:30pm). Per-dealer capacity about $120bn/day in Treasuries
  (Barclays, US short interest rate primer, Jan 2025). Foreign counterparties face a $60bn cap.
- **FIMA repo:** standing facility since Jul 2021, rate at the top of the range, public offshore ceiling for dollars.
  Up to $60bn of UST collateral was cited in Aug 2026 (Citi, Macro tapas, 7 Aug 2026).
- **Foreign repo pool (FRP):** about $330-410bn across 2024-26. Public floor for foreign official holders. A
  Fed cut to its rate or a usage cap would release reserves into the system. Conks judged this possible but
  "other less politically sensitive options exist".
- **Swap lines:** priced at OIS + 25bp. Private offshore ceiling for dollar funding.
- **Discount window (primary credit):** top of range. Stigma keeps it from working as a ceiling in a crisis; ad hoc
  facilities (BTFP in 2023, term repo in 2019) did that job.
- **Technical adjustments:** usually 5bp. The Fed signalled concern when EFFR traded within 5bp of the top of the range
  (Barclays, Jan 2025, citing Fed behaviour). The 19 Dec 2024 ON RRP cut of 5bp, inside the range, cleared the last
  few hundred billion out of ON RRP and pushed SOFR and EFFR lower (BofA, Repo sensitivity May 2025).

## 3. Dated snapshots (use as known answers and calibration points)

Each row is a source print. Computed columns use the body's conventions.

| Date (source) | SOFR-IORB | EFFR-IORB | SOFR-EFFR | TGCR-RRP | Reserves ($bn) | ON RRP ($bn) | TGA ($bn) |
|---|---|---|---|---|---|---|---|
| 13 Mar 2025 (Conks 15 Mar 2025) | | | | | 3,400.2 | 126.2 | 412.4 |
| 8 Jul 2025 (Conks 9 Jul 2025) | | | | | 3,226.0 | 227.3 | 343.0 |
| 13 Aug 2025 (Conks 14 Aug 2025) | -7 (SOFR 4.33) | -7 (EFFR 4.33) | 0 | about +8 (TGCR 4.32-4.34) | ~3,320 | ~29 | 515.5 |
| 3 Oct 2025 (Conks 6 Oct 2025) | +3 | -6 | +9 | +16 | 2,966 | 21.8 | 798.4 |
| 23 Oct 2025 (Conks 26 Oct 2025) | +9 | -4 | +13 | about +21 (TGCR 4.21) | 2,933 | 2.4 | 945.0 |

Recompute every spread from the printed rates rather than copying the table. Sources disagree on several 2025 prints
by a few bp; trust the H.4.1 and fixings data over chart labels.

Other calibration points:

- **Sep 2024 quarter-end:** SOFR traded more than $500bn above the SRF minimum bid on one day (NY Fed, Perli, Nov 2024).
  Conks counted more than $600bn. SRF take-up was about $2-3bn. Repo traded about 15bp above the prior week's average.
  Quarter-end pressure of this size does not by itself mean scarcity.
- **Year-end 2024:** hundreds of billions of repo traded above the SRF minimum bid, yet nobody tapped the SRF
  (Conks, 5 Jan 2025).
- **Sep 2019 repocalypse:** reserves fell from about $2.5tn to $1.3tn under QT. The 16 Sep corporate tax date drained
  reserves into the TGA. About $80bn of coupon settlement landed on dealers that were already full. Some SOFR prints
  reached nearly four times the 2.25% upper bound. The Fed responded with daily repo up to $75bn, IORB and RRP
  technical adjustments, term repo, and $60bn a month of bill purchases (Conks, Repo Defensive I, 20 Oct 2024; Yadav and
  Younger, 2025).
- **2018-19 scarcity template (Barclays, Jan 2025):** RDE below -1bp, fed funds 3-5bp above IORB, reserves below 10%
  of bank assets, almost all cleared repo trading above IORB, then the Sep 2019 spike.
- **Reserves relative to LCLoR:** Conks put LCLoR at $2.9tn in late 2025 and the Fed's own figure at $2.7tn. Earlier
  Fed editions said $2.2tn. Reserves were $2,966bn on 3 Oct 2025 and $2,933bn on 23 Oct 2025, above both the Conks
  ($2.9tn) and Fed ($2.7tn) measures, so "not breached" on either.

## 4. Debt-limit analogs and the TGA rebuild

### 4a. How to pick an analog

Match the state, not the calendar (BofA, Funding and debt limit: history lessons, 27 Jun 2025):

1. Similarly limited excess liquidity in ON RRP (exclude 2021 and 2023, when the ON RRP buffer was very large).
2. Similar percentage growth in expected bill and total UST supply.

This selects the 2017-2019 resolutions. The 2017 and 2018 resolutions were five months apart and count as one episode.
Measure averages 1m, 3m and 6m after resolution, using a 1m moving average.

### 4b. Analog averages and per-episode rows (BofA, Funding and debt limit, 27 Jun 2025; Lower UST WAM, 2 Jul 2025)

These are the printed values, with the SOFR convention converted. The source wrote the futures-style spread as
SOFR/FF (FF minus SOFR), so the printed -7.7 is SOFR-FF = +7.7. Confirm the sign with the source's own statement
that SOFR/FF tightens 4-8bp after resolution. Each cell is the average change in the 1m, 3m or 6m window after the
resolution, measured on a 1m moving average of the spread.

| Measure (bp change after resolution) | 1m | 3m | 6m |
|---|---|---|---|
| SOFR-FF, 2017 (printed SOFR/FF 1.9 / -0.4 / -9.6) | -1.9 | +0.4 | +9.6 |
| SOFR-FF, 2018 (printed -10.0 / -11.7 / -7.7) | +10.0 | +11.7 | +7.7 |
| SOFR-FF, 2019 (printed -14.8 / -1.0 / +2.1) | +14.8 | +1.0 | -2.1 |
| **SOFR-FF, average of the three rows** (printed -7.7 / -4.4 / -5.1) | +7.7 | +4.4 | +5.1 |
| SOFR-IORB, 2017 | -2.0 | +0.7 | +11.2 |
| SOFR-IORB, 2018 | +10.5 | +15.0 | +12.4 |
| SOFR-IORB, 2019 | +0.7 | -0.5 | -6.4 |
| **SOFR-IORB, average of the three rows** | +3.0 | +5.1 | +5.7 |
| 1m bill-OIS, average (printed as OIS minus bill: negative = bill cheaper) | -7.5 | -4.0 | -9.3 |
| 3m bill-OIS, average (same print) | -3.6 | -1.5 | -4.2 |
| 2y UST-OIS, average (printed as OIS minus UST) | +0.5 | -0.8 | +3.5 |
| 5y UST-OIS, average (printed as OIS minus UST) | -0.1 | +0.2 | +3.3 |

Reading the table:

- **The averages are plain means of three rows.** The 2017 and 2018 rows come from resolutions five months apart, so
  the effective sample is two episodes. Checks: (-1.9 + 10.0 + 14.8) / 3 = 7.6 and (-2.0 + 10.5 + 0.7) / 3 = 3.1,
  which match the printed 7.7 and 3.0 to rounding.
- **Dispersion is the point.** SOFR-IORB at 1m is -2.0 in 2017 and +10.5 in 2018. The 2017 SOFR-FF 1m row is
  negative (SOFR did not rise against FF in the first month) and only widens by 6m. Quote the range, not the mean.
- **Bill-OIS sign.** The two bill-OIS rows are printed as OIS minus bill, so negative means the bill cheapened. In a
  bill-minus-OIS convention (positive = bill cheap) they read +7.5, +4.0, +9.3 for 1m and +3.6, +1.5, +4.2 for 3m.
  State the sign next to every figure. The UST-OIS rows are printed as OIS minus UST; they are small (within about
  4bp) and mixed in sign, so the headline "biased cheaper" is not a precise claim.
- The 2019 3m and 6m figures are distorted by Fed intervention after Sep 2019.

**Stated expectation for a resolution** (BofA, 27 Jun 2025): SOFR-IORB up at least 5-12bp; SOFR-FF wider by 4-8bp;
3m bills against fed funds OIS cheaper by 2-4bp; 2y and 5y UST-OIS mixed. The 5-12bp SOFR-IORB range is
wider and higher than the three-row averages (3.0 to 5.7bp); the individual rows run from -6.4 to +15.0.

### 4c. TGA rebuild speed (BofA, Short July SOFR/FF, 30 Jun 2025; Lower UST WAM, 2 Jul 2025)

Average business days to close X% of the TGA gap, over 2013, 2015, 2017, 2018, 2019, 2021 and 2023:

| Share of gap closed | 5% | 10% | 20% | 30% | 40% | 50% | 60% | 70% | 80% | 90% | 100% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Business days | 3 | 5 | 10 | 13 | 21 | 28 | 30 | 31 | 34 | 43 | 51 |

Average share closed after N business days: 5d 19%, 10d 25%, 15d 30%, 20d 49%, 30d 60%, 50d 68%, 100d 106%.
Dispersion is wide: at 20 days, 2017 closed 112% and 2019 closed 0%. Per-episode days to 100% were 54, 43, 20, 51,
41, 75 and 74. Rule of thumb in the source: about 51 business days to rebuild to target.

Implication for a drain estimate: a rebuild that is half done in 28 business days is most of the reserve drain in a
month. Model it with the path, not a single step.

### 4d. Analog supply tables (BofA, Funding and debt limit, 27 Jun 2025)

| Episode | Bills 1m / 3m / 6m after resolution, % change |
|---|---|
| 2017 | 1 / 8 / 29 |
| 2019 | 4 / 3 / 5 |
| 2023 | 11 / 25 / 49 |
| 2025 projection | 6 / 6 / 2 |

ON RRP one month before and after: 2017 96 to 120; 2023 2,218 to 1,910; 2025 projection 143 to 80 ($bn).
Bills outstanding six months before and after resolution: 2017 1,750 to 2,266; 2019 2,358 to 2,474; 2023 3,915 to 5,838.
The 2023 episode is a poor analog for ON RRP buffer reasons (the buffer was about $2.2tn).

More analog inputs (BofA, 27 Jun 2025): the 2025 projection has bills outstanding of about $5.8-6.5tn, running
6,380 to 6,497 ($bn) between six months before and six months after resolution. Total
marketable debt in the 2025 projection grows +2% / +4% / +5% at 1m / 3m / 6m after resolution. ON RRP in 2019 was
near zero; the 2025 projection takes ON RRP from 143 to 80 one month either side of resolution and from 138 to 0 at
3m, and 2017 fell from 233 to 3 over six months. A small buffer that empties within months is the state the 2017-19
rows share with the 2025 projection.

### 4e. The 2025 episode and the 2026-27 outlook (vintages, not a forecast)

- **July 2025:** the OBBBA raised the limit by $5tn. Pre-resolution forecasts: TGA $575bn at end-July, $850bn by mid-September,
  implying about $234bn of bills in July, $479bn in Q3 and $270bn in Q4 (BofA, Lower UST WAM, 2 Jul 2025). The rebuild of about
  $600bn over two months from mid-July 2025, together with QT, pushed repo toward the top of the funds range in
  autumn 2025 (Citi, US Rates Weekly, 21 Aug 2026).
- **Aug 2026 Citi (21 Aug 2026):** limit $41.1tn, debt subject to limit about $39.9tn, headroom about $1.1-1.2tn. Extraordinary
  measures and TGA drawdown from about May 2027. X-date likely Q4 2027. Private bills minus reserves reach a local low
  of about $3tn by Oct 2027, so SOFR fixes below IORB through 2027. After resolution, the rebuild could push private
  bills minus reserves to $4tn by Dec 2027.
- **Oct 2026 Citi (2 Oct 2026):** the same limit "expected to bind in Q1/Q2 2027". The two Citi vintages disagree on the
  binding date and the X-date by about two quarters. Use the latest and state which.
- **Offsets named by Citi:** piecemeal suspensions (the 2017 precedent was a two-month suspension, Sep-Dec 2017)
  keep the TGA low and push the rebuild out; LCR reform could cut reserve demand by $200-600bn; growth in MMF and bank
  assets raises bill demand.
- **Oct-Nov 2026 path (Barclays, 2 Oct 2026):** TGA rebuild to about $1.05tn by end-October, net bill settlements of
  $20-40bn per settlement day, issuance about $225bn in October and $160bn in November, paydowns in December.
  Three-month bills about SOFR OIS +9bp, six-month about +13bp. MMFs hold about $2.8tn of bills (about 38% of outstanding).

### 4f. Debt-limit trade structure (for reference only; not a recommendation)

BofA (Funding and debt limit, 27 Jun 2025) proposed shorting the October 2025 SOFR-FF futures-style spread: entry at
-4bp, target -8bp, stop -1bp in the source's convention. In this file's convention that is SOFR-FF entry +4bp,
target +8bp, stop +1bp. Rationale given: history shows 4-5bp or more of tightening after resolution; the position
owns a larger SOFR spike; SOFR leads FF. Risks: later resolution or a slower TGA rebuild. Conks (14 Aug 2025) separately
expected SOFR to print 6bp over EFFR by October 2025, on the same TGA-rebuild logic. Both are historical calls.

Why that expression (BofA, 27 Jun 2025):

- **Outright over curve.** An outright position in one contract was preferred to a SOFR-FF curve trade. The whole
  SOFR-FF strip should cheapen as SOFR shifts up, and the timing of any Fed liquidity add (ending QT, bill buying) is
  hard to call. An add would anchor the later dates, so a curve trade would be hurt at the back.
- **SOFR leads, FF lags.** Fed funds does move; it follows SOFR with a delay, against the market belief that FF stays
  put. A trade that is right on direction can look early on FF-based legs.
- **Quarter-end in the window.** The October contract also covers the Q3 quarter-end, and the Q2 quarter-end SOFR jump
  with a low TGA supports the case. A reporting date inside the contract period adds convexity to a funding-stress
  position, but it also makes a mid-contract print a poor read of the resolution effect alone.
- **Timing.** Enter before the resolution if the risk is that it passes earlier than the base case (early July against
  a late July or early August base in that note).

### 4g. Resolution scenario ladder from the 2019 regimes (BofA, Funding and debt limit, 27 Jun 2025)

Average levels in the 2019 episode, in bp, in the source's Exhibit 5 sign (positive SOFR-IORB and SOFR-FF = SOFR higher).
Pre = end-April to end-July 2019; peak stress = end-July to end-September 2019; normalisation = end-September 2019 to
end-January 2020.

| Measure | Pre | Peak stress | Normalisation |
|---|---|---|---|
| 3m bill-OIS (as printed; peak-stress value is negative, which conflicts with the exhibit's stated sign) | -1.2 | -8.6 | +0.2 |
| SOFR-IORB | +7.2 | +15.1 | +2.1 |
| SOFR-FF | +3.1 | +10.6 | +1.2 |

Starting from the June 2025 level, the source gave the move needed to reach each regime. The scenario level is the start
plus the move, and each reproduces the 2019 average:

| Measure | Level, Jun 2025 | Move to normalisation | Level reached | Move to peak stress | Level reached |
|---|---|---|---|---|---|
| 3m bill-OIS | -1.6 | +1.8 | +0.2 | -7.0 | -8.6 |
| SOFR-IORB | -10.0 | +12.0 | +2.0 | +25.1 | +15.1 |
| SOFR-FF | -2.8 | +3.9 | +1.1 | +13.4 | +10.6 |

Use: price the base case at the normalisation row (SOFR-IORB +12bp, SOFR-FF +4bp from the starting level) and treat the
peak-stress row as the tail. The +12bp SOFR-IORB move to normalisation is the top of the 5-12bp stated expectation.
Do not use the stress row as a forecast: it is a single episode in which a Fed intervention followed. The exhibit's
bill-OIS and spread signs differ from the averages table above; normalise before combining.

## 5. Bank balance-sheet and regulatory drivers of reserve demand (USD)

Keep these short here; the balance-sheet regulatory mechanics belong to [fi-balance-sheet-and-regulatory-costs](../../fi-balance-sheet-and-regulatory-costs/SKILL.md).

- **Reserves as HQLA.** Reserves, UST and GNMA carry 0% risk weight and are Level 1 HQLA at 100% LCR weight. "Swapping
  reserves for Treasuries does not reduce SLR exposure, even if eSLR were set to 0%" (BofA, Fed's SLR proposal, 25 Jun 2025).
- **Banks hold the larger of risk-based or leverage capital, not the sum.** A risk-bound bank does not change behaviour
  when the SLR changes (Conks, A Faulty Relief Valve, 8 Dec 2025).
- **Liquidity needs.** The payment system needs about $200-300bn of excess reserves on pre-crisis overdraft patterns
  (JPM, Financial stability benefits of very abundant reserves, 21 Feb 2019). Primary dealers said "comfortable" with
  about $600bn in a survey, implying about $900bn system-wide with stress demand.
- **FHLB and IBDA channel.** Interest-bearing deposit accounts give FHLBs continuous cover at 5-10bp over the top of the
  range (Conks, Global Put Part II, 28 Sep 2024). IBDA volumes rise as reserves get scarcer.
- **GSIB year-end dieting.** Short-dated cross-currency trades are cut at year-end and switched back on in January; repo
  is averaged in the GSIB score and shows less Q4 effect (Barclays and BofA sources).
- **LCR outflow assumptions** (as cited by BofA and Barclays, 2025): overnight FHLB advance 25%; overnight FF from FHLB 40%;
  secured funding against Level 1 collateral 0%; against Level 2A 15%; against Level 2B 50%.

## 6. Fed balance-sheet path (vintages)

| Vintage (source) | Reserves ($bn) | ON RRP | TGA | Other |
|---|---|---|---|---|
| Jun 2025 BofA Eliminating IORB | 3,430 at 4.40% | 576 at 4.25% | 277 | currency 2,390 at 0%; UST 4,212; MBS/CMBS 2,156 |
| Aug 2025 BofA Funding notes | 3,286 (Jul-25) to 2,872 (Dec-25) | 85 (Jul-25) to 0 (Aug-25) | 500 (Jul-25), 850 (Sep-25), 875 (Dec-26) | QT ends Dec 2025 in that forecast |
| Dec 2025 JPM XCCY 2H25 projection | 2,843 | 50 | 850 | |
| 2 Oct 2026 BofA | 2,881.7 (actual, as of 2 Oct 2026) | 11.5 | 984.0 | Fed announced plans to end RMPs |
| Jun 2026 Conks, The Repo Rebound | | | | RMOs at $10bn/month, front-loaded at $40bn |

The Fed's net interest margin on the balance sheet was about -0.16% in 2025 (about -$11bn a year, BofA, Eliminating
IORB, 13 Jun 2025; another vintage gives -0.11%). Breakeven rate on interest-bearing liabilities = asset income divided
by the interest-bearing share: BofA's 2022 example, 2.43% over 64%, gives about 3.8%. The sources treat IORB and RRP as
an income question as well as a liquidity question (BofA, Fed Negative Equity, 24 Feb 2022).

## 7. Items the sources disagree on

- **Abundant line:** 13% (Conks Oct 2025, JPM citing Fed) vs 14% (Conks 9 Dec 2024). Ample band 10-13% (Afonso et
  al. as cited in Barclays, Jan 2025) vs 11-13% (Conks 2025) vs 11-14% (Conks Dec 2024).
- **LCLoR:** $2.2tn (Fed, early editions) to $2.9tn (Conks, late 2025). Conks' figure is the Fed's adjusted upward for
  reserve hoarding for intraday liquidity.
- **RDE:** defined as the change in FF-IORB in bp for a change in reserves equal to 1% of bank total assets (Conks,
  Feb 2025), or as the change in EFFR per percentage point of reserves over bank assets (Barclays, Jan 2025), or per a
  few billion of reserves (Conks, Oct 2025). Check the units before comparing a printed value with a threshold.
- **SRF role:** NY Fed (Perli, Nov 2024) says it is meant to cap EFFR, "not repo rates". Conks and other sell-side
  notes call it a soft repo ceiling. Barclays (Jan 2025) says it caps EFFR and uncleared tri-party better than broad repo.
  All agree it is not a hard ceiling in practice.
- **QT end in 2025:** Conks put it a week before year-end 2025. BofA's Aug 2025 forecast put it at Dec 2025. JPM's Jun 2025 note
  said 1Q26. Actual reserve-management purchases started in late 2025 and were later paused, then announced to end (BofA,
  2 Oct 2026).
- **Repo rate and Sept 2024:** SOFR above the SRF minimum bid by more than $500bn (NY Fed) vs $600bn (Conks). Treat as
  "hundreds of billions".
