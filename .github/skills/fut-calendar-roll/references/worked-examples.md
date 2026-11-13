# Calendar roll: worked examples

Supporting file for [fut-calendar-roll](../SKILL.md). Prices are decimal unless written in 32nds.

## 1. Calendar implied repo (illustrative, computed)
Same CTD. Invoice price at d1 `Inv_f = CF x F + AI = 101.30`; one coupon of 2.00 paid 40 days before d2; gap d1 to d2 = 91
days; forward repo 4.20% (ACT/360).
- Fair back invoice: `Inv_b = 101.30 x (1 + 0.042 x 91/360) - 2.00 x (1 + 0.042 x 40/360) = 100.3661`.
- IRP: `(100.3661 + 2.00 - 101.30) / ((101.30 x 91 - 2.00 x 40)/360) x 100 = 4.20%`. At fair, calendar IRP equals the **forward** repo.
- Front 1 tick richer at CF 0.90 (`Inv_f` + 0.0281): IRP falls to 4.088%, 11bp below forward funding: calendar **rich**.
- Back invoice 0.03 lower (back futures cheaper, roll wider): IRP 4.082%: also rich.
- Forward vs spot-start repo: a flat 4% term repo over 51 days (to d1) and 151 days (to d2) implies a d1 to d2 forward of
  `((1 + 0.04 x 151/360)/(1 + 0.04 x 51/360) - 1) x 360/100 = 3.977%`, not 4.00% (checked in the script self-test).

## 2. Futures fair value from basis, and the enhanced-basis calendar (Burghardt, 2005)
4 Apr 2001, 5y: CTD 5-3/4% 11/05 at 105-02.5 (105.078125), theoretical June basis 13.8/32 = 0.43125, CF 0.9904:
`FV = (105.078125 - 0.43125)/0.9904 = 105.6612`, i.e. 105-21.2 (21.16/32 before rounding). On the same date the Sep 10y CTD
basis was about 4/32 under fair; entering it through the June/Sep calendar would add 2/32 to 3/32.

## 3. Equal-DV01 roll after a basket change (Citi, The long end basket case, 4 Feb 2015)
USH5 price 149-13, CTD 6.25% May-30, DV01 $166 per contract; USM5 price 167-17, CTD 4.5% Feb-36 (after the 5.375% Feb-31 left
the basket on low free float of $16bn), DV01 $252. Equal-DV01 ratio = 166/252 = 0.659, i.e. 34.1% fewer June contracts than a 1:1 roll.

## 4. BPV roll ratios (J.P. Morgan, 12 Aug 2026; back per 1,000 front = `1000 x DV01_f / DV01_b`)
WN 173.53/175.28 = 990; US 146.90/149.90 = 980; UXY 85.83/87.80 = 978 (printed 977); TY 64.43/67.11 = 960; FV 42.03/45.33 = 927;
TU 36.88/42.25 = 873 (printed 872). The ratio drifts with the basket and yield: the 2019 notes printed TU 875 and 854, FV 942
and 932 (J.P. Morgan, 31 May 2019; 23 Aug 2019).

## 5. Squeezes in the calendar (Burghardt, 2005)
- **March 2001 Bobl.** CTD 6.5% 10/05, old and illiquid, with a large BNOC gap to the second CTD 6% 1/06. OI peaked at EUR
  57bn two weeks before expiry; CTD BNOC reached -70 cents in early March; the Mar-Jun calendar widened from about 0 to 70
  cents as shorts rolled at any price.
- **December 1998 Bund.** The 6% Jul-07 was the December CTD but not deliverable into March 1999 (CTD 5.25% Jan-08). Into
  expiry the Jan-08 versus Jul-07 yield spread narrowed and the front underperformed the back.

## 6. JGB calendar (Citi, Japan Rates Weekly, 21 Aug 2026; Huggins & Schaller, 2024)
JB372/JB373 spread about 5bp (very steep): 1bp of flattening against adjacent issues lowers the calendar by 0.07-0.08 yen.
U6-Z6 core range 0.54-0.62 yen, U6 rich and expected to correct late; previous M6-U6 roll traded 1.20-1.26 yen. Roll-period
ask-minus-bid calendar volume exceeded bid by just under 40k contracts with limited price movement. The sensitivity table
(flatten/repo/parallel scenarios) has an unclear mapping in the source: do not reuse its numbers. CTD yield-spread vol into
delivery (annualised, chart read): about 1.4bp at 12M-9M, 2.1bp at 9M-6M, 2.0bp at 6M-3M (back month), 3.2bp from 3M to
delivery (front month): more than doubles in the year before delivery and is far higher in squeezes.

## 7. US roll levels
- **Citi, 8 May 2019 close (M9-U9), ticks:** TU -5.875 bearish (10.7% rolled vs 3.2% average); FV -3.25 slightly bearish (AM 31%
  of OI vs 34% prior); TY -7.5 slightly bearish (AM 16% vs 21%); UXY -19 neutral (AM 1%); US +21.0 neutral (same CTD 4.5% Feb-36);
  WN -20.0 bearish (AM 58% vs 55%).
- **Citi, 15 Feb 2023 close (H3-M3):** TU -9.375, ~2 ticks cheap to fair, CTD slope 1s3s fit `y = 0.1383x - 3.9801`, R^2 0.91
  (1bp CTD steepening about 0.65 tick of roll); FV -14.75 (CTD slope on 3s7s: 10bp steepening about 1.2 ticks); UXY +1 with the
  same CTD in both months so the curve is irrelevant (Citi, US Rates Weekly, 17 Feb 2023).
- **Citi, 18 and 21 Aug 2026 (U6-Z6):** scorecard in the main file; 50% rolled Tue 25 Aug, peak Wed 26 Aug, UXY 22.6% rolled
  (about 10% ahead of typical pace), WN 7% ahead, Dec holding 19% of OI on 21 Aug; WN roll volume 26k (5x average) and US
  26k (2x); TY AM net long fell 40k to 46% of OI (4% below the record); TU net long -60k to 36% (smallest since Apr 2024).
  Allocation: 100% pro-rata (US, WN), 20% FIFO + 80% pro-rata (TU, FV, TY, UXY) (Citi, 14 and 21 Aug 2026).

## 8. SOFR (Huggins & Schaller, 2022)
- **Strip with known fixings.** 6M strip from 3 Oct 2022, known SOFR in the Sep-22 quarter 95bp, prices 99, 98.5, 98 for
  Sep-22, Dec-22, Mar-23: annualised 6M strip rate 1.34%.
- **Roll cost.** Dec-19 into Mar-20: 138bp at the end of the reference quarter vs 4bp at the start: roll the 2nd into the 3rd.
- Spread table and SR1 hike sensitivity: [market-specs-and-conventions.md](market-specs-and-conventions.md).

## 9. Swap-curve IMM roll (Clarus, 31 Mar 2015)
USD 5y: $15.999bn started on the March IMM vs $13.25bn on the June IMM; naive roll estimate = 2 x $13.25bn = $26.5bn.
Across tenors $101.1bn of March-to-June rolls = $73.5m DV01 naively; trade-by-trade package detection gave $39.9m DV01, 39%
of the naive figure (about 40% of March risk was roll-related). Roll volume concentrates in the last sessions: the Friday
before expiry is the busiest (over 21% of rolled risk), the four busiest sessions exceed 71%.

## 10. Wild card and CTD scenarios (BofA, US Treasury futures and basis, 10 Jul 2025)
- **Wild card (WNU5).** Long $100mm 4.75% 11/15/53 against short 734 WN (CF 0.7342); gross basis 5 ticks, net 4. The market
  rallies 1 point after the 3pm settle. Delivering 734 contracts forfeits 734 x 5 x $31.25 = $114,688 of gross basis; the
  unhedged $26.6mm tail (face x (1 - CF)) sold 1 point higher gains $266,000 (derived net +$151,312). Rule: delivery pays when
  (cash - 3pm close) x (1 - CF) > gross basis x CF; it is a 3-hour call on (1 - CF) of the CTD, paid for with the gross basis on CF of the bond.
  WNU5 conversion factors run from 0.43 (1.625% coupon) to 0.83 (4.75%): factors well below 1 are what give the wild card value.
- **CTD scenarios (USU5, CTD 11/43).** +50bp: CTD becomes 11/44 and the 11/43 basis goes to about 6 ticks (from 7); +100bp: CTD
  becomes 8/50 and the 11/53 basis is worth 61 ticks; -50bp or more: CTD becomes 2/41. The long-CTD basis pays like a straddle,
  so a calendar whose back CTD can move this far has switch risk the carry model does not see.
- **FVU5 basket.** 8 bonds (11/30/2029 to 6/30/2030, plus the coming 7/31, 8/31 and 9/30/30 issues, i.e. a back basket with
  when-issued bonds); first delivery 2 Sep 2025, last 3 Oct 2025; CTD the Nov-2029 note with net basis -0.5 ticks and the
  highest implied repo, GC repo used for every bond (so special-repo bonds are not captured).
