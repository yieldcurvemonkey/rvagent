# G10 per-market convention matrix

Detail behind `SKILL.md`. Every block carries an as-of stamp. **Seeds, not truth**: before hard-coding a value, compare it
with the `swap_conventions`, `rate_indices`, `bond_static` and `fut_static` rows the adapter delivers and with the CCP or
exchange rulebook. Where two sources disagree both values are shown with the tag **[CONFLICT]**. Items tagged **[UNVERIFIED]**
come from desk practice that no primary document confirmed.

Abbreviations: BD business day, MF modified following, A/360, A/365F = ACT/365 Fixed (no leap-year adjustment), ON overnight.

## 1. Overnight RFR and term-index status (as of Nov 2026)

| Ccy | RFR (admin) | Secured? | Day count | Legacy term index and status | Does the term index still anchor the swap market? |
|---|---|---|---|---|---|
| USD | SOFR (NY Fed); EFFR is the policy target | SOFR secured (UST repo); EFFR unsecured | A/360 | USD LIBOR: lesser tenors ended 31-Dec-21, the rest 30-Jun-23. CME Term SOFR exists (1M/3M/6M/12M) but is little used as a swap reference | No: SOFR OIS |
| EUR | ESTR (ECB), published 08:00 CET next TARGET day | unsecured | A/360 | EONIA discontinued; Euribor (EMMI) reformed to a hybrid methodology, still published | Both: ESTR OIS and 6M Euribor IRS |
| GBP | SONIA (BoE), 7:00 contribution cut-off, published next London BD | unsecured | A/365F | GBP LIBOR ended (synthetic LIBOR only for a short tail) | No: SONIA OIS |
| JPY | TONA/TONAR (BoJ), provisional about 17:15 JST same day, final about 10:00 JST next BD | unsecured call rate | A/365F | JPY LIBOR ended; (D-)TIBOR continues; Euroyen TIBOR stopped 30-Dec-2024; TORF (QUICK) is a TONA-OIS-based term rate | TONA OIS dominant |
| CAD | CORRA (BoC), published 9:00-11:00 ET, index 11:30 ET | secured (GC repo) | A/365F (no leap adjustment) | CDOR ceased 28-Jun-2024; BAX futures converted to CRA at BAX = CRA - 32.138bp | No: CORRA OIS |
| AUD | AONIA = RBA cash rate (unsecured interbank) | unsecured | A/365F | BBSW (ASX) alive and robust | Both, split about evenly: BBSW IRS and AONIA OIS |
| NZD | OCR / NZIONA (OIS index) | unsecured | A/365F | BKBM (NZFMA), EU recognition renewed Oct 2025 | 3M BKBM IRS is standard; OIS growing |
| CHF | SARON (SIX), fixings 12:00, 16:00, reference 18:00 | secured (repo + binding quotes) | A/360 | CHF LIBOR ended; TOIS discontinued 2017 | No: SARON OIS |
| SEK | SWESTR (Riksbank, since 1-Sep-2021, deposit-based) | unsecured | A/360 | STIBOR continues (administrator SFBF has no plan to stop) | STIBOR 3M IRS remains standard; SWESTR OIS trades |
| NOK | NOWA (Norges Bank since 1-Jan-2020) | unsecured | A/365 | NIBOR continues (A/360, administered by NoRe) | NIBOR 6M IRS standard |

Sources for the table: NY Fed/ECB/BoE/BoJ index pages and an open-source convention list (day counts), the RBA benchmark-reform page,
SIX reference-rate page, Riksbank SWESTR pages, Norges Bank NOWA conventions note, MX CDOR/BAX notices (all retrieved Nov
2026 as research notes, see References). Euroyen TIBOR cessation: ISDA statement of 6-Mar-2024.

Only SARON and SOFR (and CORRA) are secured; ESTR, SONIA, TONA, SWESTR, NOWA, AONIA are unsecured, so the first group can fall
in stress while the second reflects bank funding conditions (Tuckman and Serrat 2022, Ch.12).

**ISDA 2021 rounding of compounded RFR rates** (ISDA 2021 matrix): 0.0001% for AONIA, SARON, ESTR, SONIA, NZIONA (also EONIA,
RONIA); 0.00001% for CORRA, TONA, NOWA, SOFR; SEK was not listed in that matrix. ISDA 2021 default for shift/lookback/lockout, if
parties give no value: 5 business days.

## 2. Swap leg conventions (seed table, as of Nov 2026)

| Curve | Fixed leg | Float leg | Spot | Pay lag | Calendar | Notes |
|---|---|---|---|---|---|---|
| USD SOFR OIS | annual A/360 (alt: semi-annual 30/360 "bond basis" for long swaps, CME) | annual compounded SOFR A/360; under 1y single payment | T+2 | 2 BD (CME/LCH cleared) | USGS (US Government Securities) | Tuckman and Serrat show a one-BD delay as a stylised case (SOFR published next morning). Cleared swaps use 2 BD. IMM-dated swaps start on the third Wednesday of Mar/Jun/Sep/Dec |
| USD EFFR OIS (legacy) | annual A/360 | annual compounded EFFR A/360 | T+2 | 2 BD | Fed calendar | Meeting-date forwards start on FOMC dates. Cash-collateral discounting (PAI) moved from EFFR to SOFR after 16-Oct-2020 |
| EUR ESTR OIS | annual A/360 | annual compounded ESTR A/360; under 1y single payment | T+2 | **[CONFLICT]** 1 BD (Darbyshire) vs 2 BD (open-source convention list) | TARGET | Verify against the CCP sheet |
| EUR IRS vs 6M Euribor | annual 30/360 | semi-annual A/360 | T+2 | 0 (rates known in advance) | TARGET | Fixing 2 TARGET days before the period. 3M Euribor used up to 1y **[UNVERIFIED]** |
| GBP SONIA OIS | annual A/365F | annual compounded SONIA A/365F; under 1y single payment | **T+0** | 0 | GBLO (London) | Spot T+0 and pay lag 0 are the GBP outliers. Cash-settled swaptions and early terminations value same day (others 2 BD before) |
| JPY TONA OIS | annual A/365F | annual compounded TONA A/365F | T+2 | 2 BD | JPTO | |
| CHF SARON OIS | annual A/360 | annual compounded SARON A/360 | T+2 | 2 BD | CHZU | |
| CAD CORRA OIS | semi-annual A/365F | semi-annual compounded CORRA A/365F | **[CONFLICT]** T+0 (broker template) vs T+2 (CARR recommended terms) | 1 BD | CATO (Toronto) | Schema seed uses 6M. Check LCH SwapClear CAD sheet |
| AUD IRS vs BBSW | quarterly to 3y, semi-annual from 4y (3y-4y negotiated) | 3M BBSW to 3y, 6M BBSW from 4y | T+1 | 0 | AUSY | A/365F both legs. Often dealt as EFP against ASX bond futures (quote vs the first futures expiry until 2 BD before expiry, then the second) |
| AUD AONIA OIS | A/365F, under 12m at maturity, over 12m annual | compounded AONIA | T+1 | **[CONFLICT inside AFMA]** 2 BD vs 1 day after termination | AUSY | |
| NZD IRS vs BKBM | semi-annual A/365F | quarterly 3M BKBM A/365F | T+2 | 0 | NZAU and NZWE (both) | Cleared at LCH |
| NZD NZIONA OIS | annual A/365F | annual compounded NZIONA A/365F | T+2 | 1 BD | NZAU and NZWE | |
| SEK IRS vs STIBOR | annual 30/360 | quarterly 3M STIBOR A/360 | T+2 | 0 | SEST | |
| SEK SWESTR OIS | annual A/360 | annual compounded SWESTR A/360 | T+2 | 1 BD | SEST | |
| NOK IRS vs NIBOR | annual 30/360 | semi-annual 6M NIBOR A/360 | T+2 | 0 | NOOS | NIBOR fixes 2 Norwegian BD before the period. 6s3s basis = fixed-rate difference of the 6M and 3M swaps |
| NOK NOWA OIS | annual (proposal) | compounded NOWA A/365, delayed payment, spread added without compounding | T+2 (proposal) | delayed payment | NOOS | Working-group recommendations |

Sources: OpenGamma open-source fixed-overnight swap convention definitions (USD, EUR, GBP, JPY), TP ICAP MET templates (CAD, CHF, SEK, NZD, NOK),
AFMA Interest Rate Derivative Conventions (AUD), Tradeweb SEF rule book and LCH SwapClear USD eligibility, Darbyshire (2022, c.2024),
Tuckman and Serrat (2022), CME SOFR pricing paper (Rogerson 2025). All as retrieved in the notes; see References.

Rules that hold across the table:
- **Direction is quoted on the fixed leg.** Payer = pays fixed = short duration; receiver = receives fixed = long duration. Say
  "long/short inflation" for inflation swaps because "receiver" is ambiguous there.
- **Spot lag differs.** T+0 for GBP (and possibly CAD), T+1 for AUD, T+2 elsewhere. FX spot is T+1 for USDCAD, otherwise T+2.
  A cross cannot be built from pairs with inconsistent settlement without first moving to a common date.
- **Default date rules** (Tradeweb/tpSEF, ISDA): effective and termination dates unadjusted; period-end = payment dates;
  payment BDC modified following; compounding "inapplicable" unless stated; spread compounding straight, flat or spread-exclusive.
- **Minimum sizes** (tpSEF, uncleared fixed/float, standard / minimum increment): USD, CAD 25mm/1mm; EUR, GBP, AUD 25mm/100k;
  JPY 2.5bn/100mm; CHF, SEK, NOK, NZD, DKK 5mm/100k.
- **Cleared lags**: LCH SwapClear USD OIS: publication/fixing T+1, payment lag 2 days, spread-exclusive compounding allowed,
  max tenor 51y, IMM rolls eligible, front or back stub but not both.
- **FRAs**: buyer pays fixed. EUR Euribor FRA: T+2, fixing 2 TARGET days before the effective date, A/360. GBP FRA settlement uses
  a 365 denominator. AUD FRAs discount with the AFMA "FRA yield" method, other currencies use ISDA FRA discounting.
- **Single-period swaps** (FRA-like on an RFR): USD SOFR 1M/3M/6M forward-starting, floating = compounded SOFR, A/360.

## 3. Government bond conventions

### 3a. Current sources (as of Nov 2026)

| Ccy | Coupon, day count | Settlement | Ex-div / negative accrued | Notes |
|---|---|---|---|---|
| USD UST | semi-annual, ACT/ACT, 32nds quote | T+1 | none | Notes 2/3/5/7/10y, bonds 20/30y, TIPS 5/10/30y, FRN 2y. Single-price auctions. Bills A/360 discount basis |
| EUR DE | annual, ACT/ACT (ICMA) **[UNVERIFIED]** | T+2 | none since 1994 | Schatz 2y, Bobl 5y, Bund 10/30y (7, 15, 20y exist). Multiple-price auctions on Wednesday, value Friday. Green twins have own ISIN, same maturity and coupon as the conventional twin |
| EUR FR/IT/ES/NL/AT/BE | OAT annual; BTP semi-annual (bond-equivalent street yield); SPGB annual | T+2 | none | CTZ (IT) zero is A/365; BTF A/360 T+1 (FR); older Spanish Obligaciones had an initial zero-coupon period |
| GBP gilts | semi-annual, ACT/ACT since Nov 1998, accrued linear in calendar days over the coupon period | T+1 | 7 BD before coupon (10 for War Loan); settle inside ex-div gets negative accrued | Conventional auctions are multiple-price (bid price, 2dp), linkers uniform price |
| JPY JGB | semi-annual, usually the 20th, accrued A/365 (366th day counted), simple-yield quoting in half-bp | T+1 since 1-May-2018 (older sources T+2/T+3) | settlement blocked for a short ex-coupon window, so no negative accrued | 2/5/10/20/30/40y. 40y and JGBi use Dutch auctions. Reopenings keep coupon and dates |
| CAD GoC | semi-annual, accrued ACT/365 | T+1 for long-term debt since 27-May-2024 **[UNVERIFIED for every GoC trade]** | none | 2/5/10/30y benchmarks. Canada switches yield method at 1y |
| AUD ACGB | semi-annual (15th), ACT/ACT, semi-annual yield | T+2 **[UNVERIFIED]** | 7 calendar days | Quoted in yield. Tenders through a dealer platform |
| NZD NZGB | semi-annual, ACT/ACT, Wellington BD, following | tender Thursday, settle the next week | none | Syndications used for new lines |
| CHF Confed | annual, 30E/360 **[UNVERIFIED for Confed specifically]** | T+2 | none | Monthly auctions except August, 2nd Wednesday |
| SEK SGB | annual, 30E/360, yield quoted (ISMA), full first coupon | T+2 | 5 days (2001 table) | Linkers (SGBi) mostly share one base CPI |
| NOK NGB | annual, 30/360 (not modified), short first coupons | T+2 for reopenings, T+5 to T+7 for syndications | n/a | Primary dealers only |

### 3b. Dated blend: Burghardt et al. 2005 (Appendix C table of Oct 2001, Exh 9.7, Appendices D-F). Historical, do not use as current
Rows are taken from different exhibits of one book, which disagree in places; the source is noted per cell.

| Market | Coupon | Ex-div | Day count | Settle | Quote | Yield |
|---|---|---|---|---|---|---|
| US | semi | none | ACT/ACT | T+1 | price, 32nds | US street |
| UK | semi | 7 BD | ACT/ACT | T+3 in Appendix C and Exh 9.7; T+1 (or T+0) in Appendix F | price | DMO |
| Germany | annual | none | ACT/ACT | T+2 domestic, T+3 international (Exh 9.7, App D) | price | ISMA |
| France OAT | annual | none | ACT/ACT | T+3 (App C); T+2 in later sources | price | ISMA |
| Japan | semi (20th) | registered bonds cannot settle within 7 BD of payment | ACT/365 | T+3 (RTGS from 2001) | simple yield | simple |
| Canada | printed "Ann" in the table (semi-annual in current sources) | none | ACT/365 | T+2/T+3 | price | US s.a. |
| Australia | semi (15th) | 7 days | ACT/ACT | T+3 | yield (bp tick) | US s.a. |
| New Zealand | semi (15th) | 10 days | ACT/ACT | T+2 | semi-annual yield | US s.a. |
| Switzerland | annual | none | 30E/360 | T+3 | price | ISMA |
| Sweden | annual | 5 days | 30E/360 | T+3 | annual yield | ISMA |

Euro area: the 1999 redenomination "reconventioned" every legacy market to ACT/ACT. Residual local quirks remain (Italian accrued
rounding, Greek 30/360 or ACT/ACT).

### 3c. Issuance calendars (benchmarks, not forecasts)
- US: refunding announcement first week of Feb/May/Aug/Nov; bills 4/8/13/17/26-week weekly, 52-week every four weeks; 2y/5y/7y
  issue at month-end, 3y on the 15th, 10y and 30y issue on the 15th with new issues in Feb/May/Aug/Nov; 20y auctions next-to-last
  Wednesday; TIPS auctions on the next-to-last Thursday (BofA, Treasury auction primer, Mar 2024). 5y TIPS new in Apr/Oct, 10y TIPS
  new in Jan/Jul, 30y TIPS new in Feb. 2y FRN new in Jan/Apr/Jul/Oct, coupon = 13-week bill high discount rate + fixed spread.
- Germany: auctions Wednesday, Bubills Monday, linkers Tuesday; OAT: 10y+ first Thursday monthly, 2y/5y/linkers third Thursday;
  Netherlands: Tuesday after the first Wednesday; Spain: Bonos first Thursday, Obligaciones third Thursday, monthly except August;
  Italy: two auctions a month (Duering 2021, Ch.39, partly dated).
- UK: gilt auctions mainly on the last Wednesday of the month in older material, DMO publishes an annual remit in spring plus
  quarterly exact dates (current auction days: use the DMO calendar).
- Japan: MOF 2/5/10/20/30y monthly, 40y every two months; multiple-price auctions 2-30y, Dutch for 40y and JGBi; liquidity
  enhancement auctions by bucket (BofA, Japan Rates Basics, Apr 2023).

## 4. Central bank dates and "which rate is priced"
(Citi G10 What's Priced In, Aug 2026; central-bank pages, Nov 2026.)

| CB | Priced on | Date convention | Meetings per year / quirks |
|---|---|---|---|
| Fed | SOFR/EFFR OIS | FOMC meeting dates, known about 6 months ahead | 8. IORB (set by the Board, not the FOMC) is the main tool; ON RRP floor, standing repo ceiling |
| ECB | ESTR OIS (not the policy rate) | **effective dates** = the Wednesday after the meeting | 8. Floor system on the deposit facility rate; MRO is DFR + 15bp since Sep 2024 |
| BoE | SONIA OIS (not Bank Rate) | MPC-dated OIS run from one publication date to the next, effective dates not meeting dates | 8 meetings, 9 members; decision published 7am the following Thursday (Deriscope, 2024). Reserves remunerated at Bank Rate; moving to repo-led framework |
| BoJ | TONA OIS | meeting dates, but a new rate takes effect at the start of the reserve maintenance period (16th to 15th) | 8. Call-rate target; complementary deposit and lending facilities |
| BoC | CORRA OIS | announcement dates | 8, decision 9:45 ET; deposit rate target minus 5bp, standing facility target plus 25bp |
| RBA | AONIA/cash rate | meeting dates | 8, decision 2:30pm day 2; moving floor to corridor |
| RBNZ | OCR/NZIONA | meeting dates | 7 in 2026, 8 from 2027 |
| SNB | SARON OIS | quarterly assessments (Mar/Jun/Sep/Dec) | 4; sight deposits tiered (policy rate up to threshold, policy rate minus 25bp above) |
| Riksbank | SWESTR; path is a best guess via STINA because meeting-dated SEK OIS is illiquid | meeting dates | 8 |
| Norges Bank | NOWA OIS | decision day; the new rate can take effect a couple of days later (Sep 2026: decided Wed 23, effective Fri 25) | about 8 **[UNVERIFIED count]** |

"Stub" or "current" = market OIS up to but not including the next meeting; hike probability for a 25bp move =
(meeting-dated OIS - current rate) / 25bp, so 0.700% against 0.50% = 80% (Aikin, STIR futures blog, Jan 2014). Policy levels and
paths are snapshots: take them from `rate_fixings` and `cb_meetings`, never from this file.

## 5. Snap and fixing times
House end-of-day curve snaps (Deutsche Bank, Interest Rate Curve Creation Process, Feb 2023): London close 4pm London for most curves; NOK 4pm CET; DKK and SEK 4:15pm CET (since 27-Apr-2018); New York 3pm; Sydney 4:30pm;
Auckland/Wellington 4:30pm; Tokyo 3pm. Match the snap to the instrument's own close before comparing a futures settle with a swap
close: an exchange settlement price and a near-close snap of the same SOFR future can differ by a fraction of a bp, so keep `settle` and `close` as separate sources.
