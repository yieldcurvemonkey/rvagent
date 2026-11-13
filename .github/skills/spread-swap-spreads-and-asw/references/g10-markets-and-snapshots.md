# G10 market notes, conventions and dated snapshots

Detail behind `SKILL.md`. **Every level below is an as-of snapshot from the cited publication, not a current value.** Sign tags:
**(S-G)** swap minus govt, **(G-S)** govt minus swap, **(as printed)** the publisher's own convention was not restated: describe legs
before reusing. Quote conventions, day counts and calendars live in `../../fi-g10-market-conventions/SKILL.md`.

## 1. Who quotes what (sign map)

| Family | Sign | Notes |
|---|---|---|
| US maturity-matched / spreadover, SOFR era (JPM, Citi, Barclays, Clarus, Conks) | S-G, negative across the curve | "long spreads", "widener", "buy spreads" = buy bond + pay swap = profits as S-G rises |
| BofA UST RV primer (2022) MMSS; GS UST ASW screen | G-S ("bond over SOFR", positive) | Same trade, opposite sign. BofA single-bond Treasury/OIS (2017-18): positive = Treasury cheap (G-S) |
| Citi OIS/UST MMS tables | S-G (2y -14.6 ... 30y -71.5) | |
| EGB / gilt / JGB ASW (BofA book, Citi, H&S) | G-S, positive = bond cheap to swaps | H&S "reference + X": Bund at EURIBOR -10 = ASW -10 (rich) |
| Barclays EUR/UK/JP forecasts (2 Oct 2026) | appear S-G (JGB 30y -50) | opposite to Citi JPY OIS ASW (+12.5 to +25) and the BofA JGB book: verify before comparing |
| Dealer-style "widener" | Clarus, JPM: buy bond + pay swap. Düring (2021): sell bond + receive (ties a short bond to "widening" even when a negative spread gets less negative) | always describe trades by legs |
| Data-vendor swap-spread series | often US sign applied to EUR/JPY | check by comparing to a known level |

## 2. USD

- Conventions (Clarus, Spreadovers vs SOFR, 23 Sep 2020): UST leg as before; swap spot-starting, SOFR compounded in arrears paid annually, fixed
  leg annual ACT/360, cleared, PAI at SOFR. LIBOR-era spreadover: 3M LIBOR float, semi-annual 30/360 fixed, PAI at EFFR until 16 Oct 2020.
  LIBOR-SOFR froze mid-2023. Check discounting/PAI before splicing history.
- Three forms (Clarus, What's the Deal with Invoice Spreads, 17 Sep 2014): spreadover (OTR bond vs spot-start standard-tenor swap, interdealer
  standard, ~70% of interdealer volume per one source; ~20% of USD on-SEF DV01 in May 2015); matched-maturity (swap maturity = bond maturity, hedge-fund
  standard); invoice spread (swap effective on futures delivery date, maturity = CTD maturity: see `../../fut-invoice-spreads/SKILL.md`).
  Invoice spread has the opposite sign to cash ASW (Citi, The long end basket case, 4 Feb 2015).
- SOFR-era levels (S-G): 2 Oct 2026 end-week (JPM): 2y -15.3, 3y -22.7, 5y -29.4, 7y -36.7, 10y -41.2, 20y -64.8, 30y -67.7. 21 Aug 2026
  (JPM): 2y -15.2, 5y -27.7, 10y -40.0, 30y -70.9. 16 Feb 2023 OIS/UST (Citi): 2y +9.1(as printed), 5y -20.1, 10y -28.4, 20y -59.3, 30y -68.5.
  25 Sep 2026 GS screen (G-S): 2y ~14, 5y 27, 10y 39, 20y 65, 30y 67-72; OIS-based ~4-6bp higher. 2y SOFR spread path (Conks, 1 Mar 2026,
  chart reads): -15/-16 early 2025, trough ~-28 Apr 2025, -22 to -25 mid-2025, ~-17 Mar 2026.
- Forecasts Q4 2026 (Barclays, S-G): 2y/5y/10y/30y -15/-25/-40/-70. US-Germany spread forecasts 4Q25 (BofA, 3 Jun 2025): 2y -14 to -10, 5y -24
  to -24, 10y -39 to -29, 30y -41 unchanged.
- History (S-G): 30y negative since Nov 2008 (before leverage/GSIB rules, so structural), 10y breached zero Sep 2015, 5y Oct 2015, 2y positive
  until the post-2020 era; 10y averaged +38bp before Oct 2015 and -11bp after (FRBNY EPR, Oct 2018). 2y peaked +165bp in the GFC (Bassman, Finding Sea-Level, 27 Jan 2016).
- Front-end Treasury/OIS drivers (BofA, 27 Sep 2017 and 30 May 2018): coupon sizes, foreign official demand (NY Fed custody vs DXY, inverted),
  HQLA demand, Fed framework (corridor: FF >6bp above GC makes Treasuries rich vs OIS; floor: early runoff stop richens them), FHLB fed-funds lending.
  Bills: define 1y spreads on off-the-run original 2y notes, not bills (Citi, 9 Oct 2026). Debt-ceiling resolution: 2y/5y biased cheaper after
  (BofA, Funding & debt limit: history lessons, 27 Jun 2025: avg 1m/3m/6m 2y change +0.5/-0.8/+3.5bp, sign as printed); 2021 was an outlier.
- Event windows: Jan corporate/financial supply (13% of annual financial supply, avg Jan fixed-rate maturity 8.4y) tightens longer spreads;
  5y-median 10y change around year-end -0.6 (10d before) -0.4 (5d before) -3.0 (5d after) -2.0 (10d after) -0.2 (20d after) (Citi, Corporate supply to
  bring spreads tighter, 3 Jan 2017). ~2bp median tightening by mid-October on post-earnings bank issuance (Citi, 4 Oct 2019). Midterms: 30y spreads
  widened in the following week in 4 of 5 (median back to 0 within a month) (Citi, US midterms on the mind, 2 Oct 2026). With n of 5-20 these are weak.
- Rate-locks, pensions, VA: pension funded plans defease with Treasuries/STRIPS not swaps; VA hedgers pay when equities rally (hurts long-end
  narrowers); 1% S&P fall ~0.77bp 30y tightening (Citi, 4 Oct 2019; JPM, Issuance, pensions, and long-end spreads, 14 Sep 2018). Structural flow
  balance Apr-YE 2020: buyers ~$1.1-1.3tn 10y-eq vs sellers ~$2tn, net narrowing (JPM, What about Bonds?, 2 Apr 2020).
- FX reserves: JPY intervention (event study, BofA, FX intervention primer, 8 Jul 2024): USD-buying episodes lower 2/5/10y yields ~2-3bp per
  JPY 1tn and usually widen spreads (intercept +1.4 to +1.5bp); USD-selling episodes usually narrow spreads (intercept -0.7 to -2.2bp, R2 0-0.07):
  weak but intuitive.
- Hedge-fund swap trade size (BIS Quarterly Review, Dec 2025): upper bound = HF long UST exposure - all short UST exposure (Form PF counts no IRS):
  $631bn at Q2 2025 (from $707bn Mar 2025, $281bn Q1 2024). Crowding on SLR relief: Apr 2025 spreads moved 4.5-7bp more negative on record volume,
  10y VWAP -7bp over two weeks (Clarus, Swapalypse Now, 14 Apr 2025). Swaps-vs-futures cross-margining reduces the cost of spread trades (Crisil Coalition Greenwich, Q3 2025).
- Agency vs Treasury (Citi, The rocky road to a steeper curve, 18 Jan 2019; US agency benchmark): breakeven spread = widening needed for an agency to underperform
  the like-maturity Treasury over the horizon; modified BE change over 6m = curve-implied spread change + OAS-constant breakeven change; divide by 6m
  spread vol (1y std dev). Table 2/3/5/7/10y: OAS to Tsy 2/5/3/13/23bp, spread vol 1.5/1.8/3.4/3.9/4.7, BE/vol 1.09/1.69/-0.03/0.93/0.65, so 3y best.
  Driver: low benchmark issuance. Duration-adjust before comparing across the agency curve.

## 3. EUR

- Swap spread (LIBOR era) = swap - on-the-run AAA govt (credit spread AA vs AAA); interpolating the swap to bond maturity gives the I-spread (Aikin, STIR
  Futures, 2nd ed., 2012). BTPs pay semi-annual coupons, EUR swaps over 2y pay annual fixed: a BTP-vs-swap par spread is misleading unless
  frequencies are matched (Düring, 2021).
- Structure: ASW vs ESTR carries a capital basis (~16bp at g = 10%) and is more volatile than UST SOFR-ASW; most of its volatility is absorbed by basis swaps (H&S 2024).
  Bund ASW co-moves with senior-financials credit (Nordea, EUR Rates Flash, 5 Feb 2020): ECB exempt tier keeps German repo ~4-5bp below DFR, so Schatz vs EONIA stayed range-bound.
  10y EUR swap spread turned negative for the first time in Nov 2024 (S-G; Conks, 27 Nov 2024).
- Snapshots: 10y EUR swap spread ~+10.5bp, 12-month high, +8bp since mid-Sep, partly quarter-end; Citi forecast 0bp 4Q26 then -4, -8, -10, -10 (Citi, What to do about OATs?,
  1 Oct 2026; sign as printed). Barclays EUR vs ESTR Q4 26: -10/-15/-20/-50 (2y/5y/10y/30y, appear S-G). Schatz swap spread sticky ~-10bp vs ESTR, neutral because
  short-dated repo has barely responded to growing collateral (Citi, European Rates Strategy: Latest views, 20 Aug 2026). 10y OATs >160bp cheap on ASW (Barclays, 2 Oct 2026).
- SSA / covered / agencies (Citi, 20 Aug 2026; 24 Sep 2026): German agencies, Laender and Nordics trade vs swaps (OIS swap spread); French agencies and Belgian regions trade vs OATs/BGBs; match duration
  across SSA sub-sectors (WA duration supras 7.3y, agencies 4.3y, covered 4.0y). SSA swap spreads held a 6bp range since Feb 2026; index asset-swap spreads: supras 41bp, agencies 29bp, covered 26bp (above
  post-QE peak 25.5bp Jan 2019, ~7bp below Covid peak 33.3bp). KfW 12-19bp over Bunds. Expect year-end widening of SSA-EGB/covered in Nov-Dec; track net covered-bond supply (net supply - coupons - QE purchases),
  not gross. Rating-implied RV (Austria rich vs EU) failed repeatedly: supply and funding dominate; measure supply in DV01 and net-supply terms (Citi, 1 Oct 2026).
- Solvency II reform (effective 30 Jan 2027): final-smoothing-point replaces the last-liquid-point (20y EUR), UFR 3.30%, convergence alpha 0.20 falling to 0.11 by 2032; the volatility adjustment and lower
  risk-margin cost of capital reduce the need to receive long-end swaps, so govies become "considerably more palatable than swaps" for ALM: a potential EUR long-end spread driver. The published cost-of-capital
  end point differs across sources (4.5% vs 4.75%): do not quote it (Citi, 1 Oct 2026; 17 Sep 2026).
- Seasonals (BofA, Bond market seasonality explained, 6 Jun 2022; EUR swap minus bond): Jan 2y up in 25% of years (avg -3.5bp, year-end repo reversal), Mar 10y up 70%, Jul 30y up 70%, Aug tighter; n=20 so weak.
  A direct test of Bund-futures ASW found no support for January or September tightening (swapsball.net, Testing for seasonality, 19 Nov 2017: p 0.75, 0.14).
- Cross-market: relative US-German swap spread explains 80-90% of EUR/USD xccy basis levels (BofA, 27 Mar 2025; Citi, FX Basis Quarterly, 13 Dec 2024); the link is weak for JPY. Handled in
  `../../xccy-basis/SKILL.md`. $ASW (G-S vs SOFR, Dec 2024): 2y JP/US/DE/FR/ES/IT 38/20/8/21/21/43; 10y 70/50/9/91/81/130; 30y 120/82/34/161/172/229.

## 4. GBP

- Gilts are the credit benchmark; reopenings give off-tenor benchmarks, so matched-maturity asset swaps are used; swap-spread curve slopes down from ~5y (ALM demand); UK DMO runs an unhedged programme
  (Clarus, Mechanics of Asset Swaps, 18 May 2015; Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022).
- Low-coupon richening: UK retail taxed on income not gains, a 40% taxpayer pays ~5bp tax on a 12.5bp coupon; a 0.125% 2028 gilt had the highest net yield; switch sell 4.125% 2027 / buy 0.125% 2028 on ASW
  (monitored as the spread of OIS z-spreads) entered +1.8bp, target -25bp, hit -25.4bp (BofA, Will retail discover Gilts?, 10 Nov 2022). Scarcity richness is not RV; watch QT and DMO launches (BofA, Back to school, 5 Sep 2024).
- Model (JPM, 21-22 Aug 2026): 10y SS 1bp narrow vs fair value, narrowing bias into the late-Oct budget. QT rundown of 2026-34 issues removes front-end collateral: long gilts vulnerable to repo specialness and ASW
  richening (Barclays, 2 Oct 2026). Short gilts acutely rich vs SONIA in 2022; banks buy gilts only once short yields rise vs SONIA (BofA, 10 Nov 2022). Barclays UK OIS ASW forecast Q4 26 -10/-15/-55/-70 (appear S-G).

## 5. JPY

- JGB swap spread vs TONA/OIS (G-S for ASW). Citi: 10y OIS ASW 12.5bp (3Q26) to 25bp (1Q28), 2y -4.0 to +5.0 (Citi, Japan Rates Weekly, 14 Aug 2026); a later note: 10y 15 (4Q26) to 20, 2y -1.0 to 2.5 (2 Oct 2026).
  JPM (21 Feb 2025): 10y narrower (receive 10Y JSCC-cleared swap 0.940% vs short JB 0.960%, +9.4bp), 30y narrower -1.5bp, closed 10y +12bp, 2y +4bp. Fair value: GS sees spreads tracking free float (debt less BoJ holdings); +5pp
  free float means ~3bp tighter 10y spreads (GS, Global Rates Trader, 2 Oct 2026). xccy link: a sharp back-end xccy-basis tightening prompts foreigners to unwind JGB xccy-ASW, supporting narrowers.
- 3M T-bill ASW model: regress on 3M USD/JPY xccy basis, net bill issuance, 3M GC/OIS (12m); residual ~-4bp (rich); JGB$ASW year-end turn ~+15bp Oct-Dec (JPM, 21 Feb 2025; 5 Jun 2025). Bills: `../../stir-bills-and-money-market-spreads/SKILL.md`.
- Futures ASW (JGB): front-future ASW ~-11.5 (Sep 2014) to ~-20.8 (Dec 2014), CTD ASW 0.5-1bp below (JPM chart sheet, Jan 2015). BofA book Oct 2026: long 30y JGB ASW 45/35/52 (entry/target/stop, G-S), selling 10y JGB ASW after sharp richening (Barclays).
  H&S: JGB ASW vs USD SOFR mirrors the JPY CCBS; local ASW stable (domestic holders). Raw Japan CDS overstates fair ASW: use adjusted CDS.

## 6. CAD, AUD, NZD, CHF, SEK, NOK

- **CAD**: swap-spread transaction type "spread vs Government of Canada securities" exists on the SEF rulebook (Tradeweb, SEF Rulebook Ch. 9). CDOR is legacy (replaced by CORRA); fixed-leg frequency and day count
  sources disagree: take them from `swap_conventions`/`fi-g10-market-conventions`. No sourced CAD spread levels. Cross-region note: UK, Canada and Germany co-moved post-2008 via excess reserves (BofA, UST RV Primer, 2 May 2022).
- **AUD**: bond futures (3y, 10y) are cash-settled in yield terms (100 - yield) vs a non-deliverable weighted basket; swaps quoted as EFP = generic swap - futures-implied yield (S-G). Start and end dates do not match, so carry/roll
  is computed separately for swap and bond legs (swapsball.net, How to calculate carry and roll-down for a bond future's asset swap, 12 Dec 2017: illustrative long 3y EFP C&R = -5.1 + 0.5 + 3.5 = -1.1bp/3m). Pay AUD 10y spread vs XM at
  +5.25bp with model ~5bp tight (25k DV01 per leg, JPM 21-22 Aug 2026). Seasonals (BofA, 6 Jun 2022): 3y up 70% Nov; 10y up 75% Feb. OIS ~half of AUD/NZD swap turnover.
- **NZD**: 5y spread = own NZGB vs pay 5y IRS (May-31 NZGB 4.138% vs 3.923% at -21.55bp, +7.4 P/L, JPM 21-22 Aug 2026). No other sourced material.
- **CHF**: only that SARON is secured like SOFR, so a SARON ASW carries no capital basis (Tuckman & Serrat, 4th ed., 2022; H&S 2024). **No sourced CHF spread material: do not infer levels.**
- **SEK**: swaps rather than government bonds are the credit benchmark (too few SGBs) (Darbyshire, 2022). **NOK**: no sourced material. Ask the user/data adapter; never fill from memory.
