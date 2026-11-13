# Worked examples and printed numbers (fut-invoice-spreads)

All numbers are as printed in the cited documents; arithmetic checks are marked. Prices in decimal unless stated.

## 1. Hedge sizing
- **10y OTR vs futures (Burghardt, Belton, Lane, Papa, The Treasury Bond Basis, 3rd ed., 2005):** hedge $10mm of the 5% Feb-2011 (full price 101.222, modified duration 7.67, DV01 $77.624 per $100k = $7,762.40). CTD 5.5% Feb-2008: IRR 3.508%, futures 106-08, CF 0.9734, DV01 $59.14, modified duration 5.65. Futures DV01 = 59.14 / 0.9734 = $60.76 (check). Hedge ratio 1 = 7,762.40 / 60.76 = 127.8 (128). Rule 2 is printed as (10,122,200 x 7.67) / (106,250 x 5.65) = 126.9 (127), but those inputs compute to 129.3 (the book's printed figure does not reproduce; the book attributes the gap to applying full-price duration to a clean futures price): use rule 1. Option-adjusted DV01 66.13 vs rule-of-thumb 60.76 (Exh 5.10) gives 7,762.4 / 66.13 = 117.4 contracts, 8% fewer (the book says about 10%).
- **Exhibit 5.10, close 4/4/01 (rule-of-thumb / OA vs CTD / OA vs OTR / repo DV01):** Jun-01 10y 60.76 / 66.13 / 69.75 / -2.53; bond 121.86 / 122.42 / 132.92 / -2.46; 2y 38.63 / 39.06 / 39.07 / -5.06; 5y 42.84 / 43.20 / 43.20 / -2.50. Stub risk (repo DV01 / spot DV01): bond 2%, 10y 3.8%, 2y 13%.
- **Yield beta:** 7.5% 11/16 DV01 117.78, beta 1.1365; CTD DV01 145.45, beta 1.0857; futures DV01 122.42 vs the CTD yield, 132.92 vs the OTR (= 122.42 x 1.0857, check); HR = 1.007. OTR 30y $100mm: 1,265 (rule of thumb) vs 1,121 (yield beta).
- **CF vs DV01 hedge (Salomon Brothers, Understanding Treasury Bond Futures, Oct 1990):** $100mm 11.75% Nov-2014 vs Dec-90: CF 1.3608 -> 1,361 contracts; DV01 hedge (0.1103 / 0.0931) x 1,000 = 1,185 (check). The 7.5% Nov-2016 benchmark: forward DV01 $0.0880 at 8.92%, CF 0.9456 -> futures DV01 $0.0931; 1 futures point = 10.7bp yield (check 1/0.0931).
- **CF example (Salomon 1990):** 10.375% of 15-Nov-2012 (callable 2007): Dec-90 term 16 3/4y -> price 121.683 -> CF 1.2168 (reproduced by `scripts/invoice_spread.py` selftest); Mar-91 term 16 1/2y -> 121.550 -> 1.2155. The 8% yield and 15y minimum are 1990 specifics; today's contract uses 6%.
- **Tail buy-back:** $100mm at CF 1.2 = 1,200 contracts; 1,000 delivered, 200 bought back at delivery. If CF < 1, sell the extra.

## 2. P-weighted DV01 (J.P. Morgan, The switch and the spur, 29 Oct 2026; data 27 Oct 2026)
| Contract / yield | CTD | DOV | CTD BPV | BPV/CF | P-weighted |
|---|---|---|---|---|---|
| Dec-26 bond at 6.10% | 1 3/8% Aug-50 | 3/32 | 706 | 1675 (jumps from 1382 at the switch) | 1518 |
| Dec-26 bond at 4.28% | Nov-43 | 0 | 1249 | 1438 | 1442 |
| Dec-26 ultra-bond at 5.79% | Feb-52 | 1 (futures 101.1) | 845 | 1633 | 1584 |
Dec-26 bond: six bonds at >= 10% CTD probability within +-100bp, none above ~30% at current yields; a selloff makes 1 3/8% Aug-50 dominant, a rally 4 3/4% Nov-43. Ultra: 4% Nov-52 about 60%; a rally -> 4 3/4% Nov-53, a selloff -> 2 1/4% Feb-52. Switches are likely about 50bp either side. The model excludes wildcard, end-of-month and when-issued bonds. Jump risk is milder for the ultra contract because its deliverables are more alike in BPV/CF.

## 3. Invoice spread levels and mechanics
- **Citi, 4 Feb 2015:** Mar-15 bond future 149-13, DV01 $166 per contract; Jun-15 167-17, DV01 $252: an equal-DV01 roll needs 252/166 -> 34.1% fewer Jun contracts. Invoice-spread changes correlate 34% with open-interest changes. The CTD jump: no long bonds issued Feb 2001-Feb 2006; CME excluded the 5.375% Feb-31 (free float $16bn); CTD from 6.25% May-30 to 4.5% Feb-36; the Fed held ~51% of the May-30s.
- **Invoice vs matched swap spread (Goldman Sachs, US Treasury Asset Swap Spreads, 25 Sep 2026):** 7y 5% Sep-33 matched 34.1; CTD 4.5% Aug-33 matched 33.8, fitted -0.8 (z -2.2), invoice 35.6; 20y CTD matched 64.9, fitted +2.1 (z 2.9), invoice 68.3; Ultra CTD 4% Nov-52 matched 69.6, invoice 72. Gaps 1.8, 3.4, 2.4bp.
- **JGB futures ASW (J.P. Morgan, 29 Jan 2015):** invoice-type spread 0.150 - 0.330 = -18bp (CTD-implied yield minus forward swap yield); front contract moved from about -11.5/-12 (17 Sep 2014) to about -20.8 (early Dec), about -18 at end; CTD ASW 0.5-1bp below; IRR -0.3% to +0.6%.
- **Bobl ASW (swapsball.net, 12 Dec 2017):** spot 53.1; carry 53.7 - 53.1 = 0.6bp/3m; roll 55.8 - 53.7 = 2.1bp over 6m -> 1.0bp/3m.
- **AUD 3y EFP (swapsball.net, illustrative):** long the Mar-18 contract at 98.03/98.035 = 1.9675%; swap-leg carry and roll about -5.1bp; futures carry 1.9675 - 1.9625 = +0.5bp; roll about +3.5bp per 3m; total -1.1bp per 3m.
- **Breakeven arithmetic (RiskVal, Future CTD Scenario Analysis, 25 Apr 2024):** ultra-10y Mar-21, 9 Mar 2021, last delivery 31 Mar 2021: futures 148-02 7/8, gross basis 0.326 (32nds), CF 0.6226. B/E = (148 + 2.875/32) + (0.326/32) / (1 - 0.6226) = 148.0898 + 0.0270 = 148.1168 (check). Jun B/E = 148.1168 - (1 + 20.875/32) = 146.4645.

## 4. Conditional invoice trades (Board option vs CTD-matched swaption)
Pick-up = invoice spread - strike spread (strike spread = costless swaption strike - Board strike yield). Printed values:

| Trade | Board strike | Invoice | Strike spread | Pick-up | Board vs swaption vol | Source |
|---|---|---|---|---|---|---|
| 5y note, May-18 option expiry (note dated 12 Mar 2018) | 113.75 put (2.74%) vs payer 2.85% | 11.6 | 10.8 | +0.8 | 66.0 vs 64.0 (1.03) | Citi, 12 Mar 2018 |
| 10y Jun-23 | 114.00 put (3.68%) vs payer 3.43% | -29.8 | -24.6 | -5.2 | 121.8 vs 127.5 (0.96) | Citi, 12 Jun 2023 |
| 5y Jun-23 (DV01 4.22/3.84, $109.8mn) | 109.00 put (3.76%) vs payer 3.56% | -25.0 | -19.6 | -5.4 | 142.8 vs 142.5 | Citi, 12 Jun 2023 |
| 10y Dec-26 (expiry 23 Oct 2026) | 104.00 put | -38.4 | -41.0 | +2.6 | 122.6 vs 116.5 (1.05) | J.P. Morgan 29 Oct 2026; Citi 5 Oct 2026 |
Check: 11.6 - 10.8 = 0.8; -29.8 + 24.6 = -5.2; -25.0 + 19.6 = -5.4; -38.4 + 41.0 = 2.6. The 5y May-17 example: futures 118-13, DV01 4.77/4.01, $119.1mn, invoice 11.9bp (Citi, 1 May 2017).
- **Notionals per 1,000 contracts, Jan 2017:** 5y $117.7mn (invoice 1.0bp); 10y $120.3mn (-12.6bp); bond $127.4mn (-25.6bp) (Citi, 9 Jan 2017).
- **Jul-19 call example:** buy 1,000 Jul-19 10y 126.5 calls at 19/64, sell $124.1mn receivers on the 30-Sep-2019 to 30-Apr-2026 swap expiring 26-Jul-2019, strike 2.03% at 26.3 cents, delta-hedged daily at 3pm New York (Citi, US Rates Weekly, 17 May 2019).
- **Board/swaption ratios:** 9 Jun 2023: 5y 1.01, 10y 0.98, bond 1.03 (Board/1m realised 1.16-1.22, /3m 0.77-0.93; Citi, 12 Jun 2023). 27 Mar 2020: 5y 67.1 vs 77.8 (0.86), bond 106.9 vs 120.5 (0.89), 10y 96.7 vs 95.1 (1.02) (Citi, 30 Mar 2020). 2 Oct 2026: 5y 1.03, 10y 1.06, bond 1.07-1.08; Board/3m-realised 1.57-1.73 vs futures/swap 3m-realised 1.04-1.08 (Citi, 5 Oct 2026). 2019: 10y Jul 60.1 vs 58.5 (3% rich) (Citi, 9 May 2019).
- **Listed vs OTC widener (BofA, US Vol Primer, 11 Mar 2024):** pay 10y SOFR vs buy 10y note futures, each $100k per bp; conditional = buy 7m10y payer (Sep expiry) vs sell the Sep put, notionals matched so the terminal swap DV01 = CTD DV01 at the invoice yield implied by the option strike. Directional: wider on selloffs, tighter on rallies.

## 5. Front-end and STIR-linked packages
- **2y-futures/OIS (J.P. Morgan 28 Feb and 6 Mar 2020):** sell 2,500 2y futures vs receive $576mn SOFR OIS (6-Jul-20 to 15-Mar-22) at +13.9bp (quote sign not stated in the note): P&L +2.0bp (28 Feb), +4.1bp (6 Mar). Received 10y invoice at -5.95bp (short 1,000 futures vs receive $133mn swap 31-Mar-20 to 15-Nov-26): -2.5bp, -5.4bp. Front-end basis beta is a daily-horizon artefact: test across horizons and >1 sigma subsets.
- **Schatz spread (Clarus, Dummies Guide to IRS, 19 Jun 2024):** futures 105.76; Schatz yield 2.669; swap 3.035 -> 36.6bp; 2y IMM swap 2.98 -> gadget 31.1bp. A bid empties and the spread jumps a futures tick (~0.25-0.5bp) vs ~0.1bp for the swap tick.
- **Cash term TED (Aikin 2012):** Schatz 0.25% Dec-2013, 20 Dec 2011, settle 23 Dec 2011: strip yield 1.1063%, cash yield 0.2118%, TED 0.8945%. Derivative 2y TED (11 Jan 2012): strip yield 0.92%; Schatz 110.405 x CF 0.906868 = 100.123 -> yield 0.18%; TED 0.74%. 2y TED vs 2y swap spread about 85% correlated.
- **Term-spread trades (Aikin 2012):** buy 10 Schatz Dec-05 at 105.70, sell 1 bundle at 97.2281; gain EUR 650 over six days (book prints 105.70 in the table but 105.64 in the P&L). Buy 20 Euribor Mar-07 (BPV EUR 500), sell 25 Schatz (500/19.99): gain EUR 2,375.
- **Schatz/Euribor 4:5 lots and gilt/Short Sterling 1.6** (about GBP 20 / 12.5) are exchange/LCH margin or rough DV01 ratios (Aikin forum).

## 6. Margin, flow and structure facts
- **SDR method (Clarus, 17 Sep 2014):** 25,871 USD trades in Aug 2014, 3,652 "previous"-start removed, 744 matched to delivery/CTD pairs (about 3%; 614 front, 130 next); by contract 2y 146, 5y 329, 10y 196, bond 62, ultra 11; 163 blocks. Exact-date matching undercounts.
- **Delivery-date pairs (2014):** 2y Sep-14 3-Oct-14 / 30-Jun-16; Dec-14 6-Jan-15 / 30-Sep-16; 5y 3-Oct-14 / 30-Nov-18; 10y 30-Sep-14 / 15-May-21; bond 30-Sep-14 / 15-May-30; ultra 30-Sep-14 / 15-Feb-40.
- **Margin offsets (Coalition Greenwich Q4 2024; hypothetical maxima, vendor-sponsored):** futures vs swaps sized DV01-neutral against $100mm swap notional: SOFR futures 2y receive 1,558 -> 349 (78%), 5y 3,753 -> 870 (77%); Treasury futures 10y receive 6,630 -> 2,646 (60%), 30y 12,924 -> 6,496 (50%). CME reported $8.2bn/day savings in H1 2025, about 90% from USD swaps vs USD futures/options (Crisil Coalition Greenwich, Q3 2025). Offsets are capped across CCPs. Margin offset can outweigh a CCP basis: compare before splitting.
- **New contract effects (Credit Suisse, 28 Sep 2009):** launching the ultra bond contract: delivery option about 2.5 ticks, about a quarter of the classic bond contract, with 9 deliverable issues; CTD 4.5% Feb-2036 (90% delivery probability); DV01 56% above and convexity ~4x the classic contract. Fewer deliverables, smaller delivery option, futures closer to the CTD forward.
- **Squeeze history:** the 1986 squeeze of the 9.25% Feb-2016 widened the basis about 6 points ($60,000 per $1mm); drivers: a crowded obvious short, an unborrowable issue (reverse repo near 0%), forced sales of cheap-to-deliver issues. June-2005 10y CTD traded at -15% overnight repo in late May 2005 (Burghardt 2005).

## 7. Treasury futures primer examples (BofA, US Treasury futures and basis primer, 10 Jul 2025)
- **Wildcard on a CF-weighted hedge (WNU5):** long $100mm T 4.75% 11/15/53 against short 734 WN (CF 0.7342); gross basis 5 ticks, net 4. The market rallies 1 point after the 3pm settle. Rule check: `5/32 * 0.7342 = 0.115 < 1 * (1 - 0.7342) = 0.266`, so deliver. Delivering 734 contracts forfeits `734 * 5 * $31.25 = $114,688` (check: 114,687.5). The tail is `$100mm - 734 * $100k = $26.6mm` face, and selling it 1 point higher gains `$266,000` (check). Net profit about $151k.
- **FVU5 basket (5y, Sep-25):** 8 deliverables (11/30/2029 to 6/30/2030, plus the 7/31, 8/31 and 9/30/30 issues still to be auctioned); first delivery 9/2/2025, last 10/03/25; CTD the Nov-2029 note with net basis -0.5 ticks and the highest IRR, GC repo used for all bonds. A -0.5 tick net basis is about -0.5 * (1/32) / DV01_fwd bp of gap.
- **USU5 CTD scenarios (bond contract, Sep-25):** CTD 11/43. +50bp: CTD becomes 11/44 and the 11/43 basis goes to about 6 ticks (from 7). +100bp: CTD becomes 8/50 and the 11/53 basis is worth 61 ticks. -50bp or more: CTD becomes 2/41. A long CTD basis behaves like a straddle; the scenario grid also gives P(CTD) for the futures PV01.
- **Futures conversion factors:** WNU5 factors run from 0.43 (1.625% coupon) to 0.83 (4.75%); factors well below 1 give the wildcard its value.
