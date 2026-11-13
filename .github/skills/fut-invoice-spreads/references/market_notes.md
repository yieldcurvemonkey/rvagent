# Market notes by currency (fut-invoice-spreads)

Only facts that appear in the cited documents. Contract terms (CF yield, delivery rules, tick) come from `fut_static` / `fut_basket` and [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md): verify them there.

## USD (Treasury futures: 2y, 5y, 10y, ultra 10y, bond, ultra bond; SOFR/OIS swaps)
- CF uses a 6% notional coupon (adopted 2000, replacing 8%); below 6% low-duration bonds tend to be CTD, above 6% high-duration, subject to slope (BofA Global Research, US Treasury futures and basis primer, 10 Jul 2025; Burghardt 2005).
- Delivery: T+2 (intent, notice, settle). Wildcard window (RiskVal, 25 Apr 2024): futures stop 3pm, notice by 9pm New York. End-of-month for 2y/3y/5y = last business day; 10y, ultra 10y, bond, ultra bond = 7 business days before it. The 2y contract has double notional ($200k).
- Basket gap: no long bonds issued Feb 2001-Feb 2006, so contracts expiring Feb 2011-Feb 2016 had a 5y gap and a CTD jump in 2015 (Citi, 4 Feb 2015).
- Invoice-spread packages concentrate in the front contract; 2y and 5y packages were more frequent than 10y/bond/ultra in 2014 (Clarus 2014).
- Funding: SOFR is >55% tri-party by volume; 2s/OIS prices off GC collateral (dealer repo), not tri-party (J.P. Morgan, 26 Feb 2020). The 2y invoice spread tightens/lightens with bill and front-end coupon supply, foreign custody demand and flight-to-quality bids in futures.
- Board (listed Treasury futures options) vs swaptions: conditional invoice structures, strike mapping and costless strike (SKILL.md section 8). US Board vol traded rich to swaptions in 2026, FV and bond Board cheap in March 2020.
- Margin: CME portfolio-margining offsets are mostly USD swaps vs USD futures (Coalition Greenwich).

## EUR (Schatz, Bobl, Bund, Buxl; OAT, BTP, Bono futures; Euribor/ESTR swaps)
- Bund-type futures ASW: swap starting on the delivery date and ending at the CTD maturity minus the futures-implied forward yield of the CTD; positive = future rich vs swap; use the matched-maturity quote from the spot ASW curve (swapsball.net, 12 Dec 2017; 19 Nov 2017).
- Schatz spread = swap yield - Schatz CTD yield; gadget on the 2y IMM swap (Clarus 2024). Schatz/Euribor swap-spread future quoted 2 x Euribor - Schatz with 4:5 lots; a 2y Euribor bundle is the DV01-matched proxy and single-contract stacks add curve risk (Aikin forum).
- Deliverability premia in a fitted Bund curve (7 Dec 2012): bonds deliverable into Schatz +3.6bp, Bobl +2.8bp, Bund +2.1bp, Buxl +2.4bp (Huggins & Schaller 2024).
- Compounding: BTPs pay semi-annually while EUR swaps pay annually over 2y, so BTP-vs-swap par spreads mislead (Duering 2021); match frequencies or use the par/par form in SKILL.md section 4.
- Cross-country invoice: long French vs 0.6x short German invoice spreads (OAT 1.5% 25-May-31 vs Bund 0% 15-Feb-31); beta 0.6 from a regression; chart last 19.04 vs a peak near 28; France behaves as a hedging name in credit stress and the 2-10y ESTR swap becomes the only effective hedge (Astor Ridge, 6 Mar 2022).
- STIR bundles: 8-contract bundle is a close proxy; 7 futures plus the front-month stub is ideal; never use the front-month STIR contract as a bond-future partner (Aikin 2012; forum).

## GBP (long gilt; Short Sterling / SONIA futures)
- Gilt future DV01 / GBP 12.5 (Short Sterling DV01) is about 1.6 (GBP 20 / 12.5) (Aikin forum). Gilts: ex-dividend rules can remove a CTD mid-month; small deliverable sets raise squeeze and fail risk (Burghardt 2005 notes). Check the `ex_div_rule` in `bond_static` when tagging the CTD. No invoice-spread data in the sources.

## JPY (JGB futures, basket 7-10.5y)
- At low yields the shortest bond is CTD, but several bonds share the maturity with near-identical coupons, so a one-factor delivery option is ~0; a multi-factor model gave 7 sen vs under 1 sen. Holders of short net basis fear delivery of the new CTD, so they sell the new and buy back the old, widening the spread (Huggins & Schaller 2024).
- Spread vol rises into delivery: about 1.4bp at 12-9 months, 2.1bp at 9-6, 2.0bp at 6-3, 3.2bp in the final 3 months (approximate bar readings): vol more than doubles in the year before delivery.
- JGB futures ASW is quoted in the ASW sign (CTD yield - swap yield; J.P. Morgan, 29 Jan 2015): convert to swap_minus_govt (a -18bp ASW is +18bp swap_minus_govt).

## AUD (3y and 10y cash-settled yield futures, 100 - yield)
- Settled against a non-deliverable basket average yield; the future's PVBP is a constant, so the hedge ratio vs the basket is not constant. EFP = spot-starting swap yield - futures-implied yield; the daily-margin convexity adjustment is too small to apply (Duering 2021). Carry and roll are computed per leg since dates differ (swapsball.net 2017).

## CAD, CHF, NZD, SEK, NOK
- No invoice-spread-specific material was read. Contract terms in `fut_static` (the single-designated-deliverable and yield-quoted contracts have no delivery option, so the futures-implied yield equals the designated bond's forward yield and the spread is a plain matched forward swap spread). Check settlement type and `is_designated` in `fut_basket` before applying the CTD/OA machinery.

## Fixed-ratio inter-commodity spreads (USD)
- CME ICS quantities come from CTD DV01s; buy = steepener (buy front, sell back); the price ratio = front quantity / back quantity (doubled for the 2y). Fixed ratios (June 2013): 2y/5y 1:1, 2y/10y 2:1, 2y/ultra bond 6:1, 5y/10y 3:2, 5y/bond 3:1, 10y/bond 2:1 and similar (CurveTrades, Yield Curve Spread Trades, June 2013). Margin: total IM = larger leg IM - offset% x smaller leg IM (CME, US Treasury Futures Inter-Commodity Spreads, Feb 2024).
- A fixed-ratio spread plus a small outright makes it DV01-neutral: sell 242 10y / buy 100 bond vs sell 100 of the 2:1 spread = -200 10y / +100 bond leaving a 42-contract tail. Net-change quotes hide the level. Absolute spread = curve spread / back yield (cash 2s10s: 79% in Feb 2010, 78% in Feb 2011, 87% in Jul 2012).
- Return about = bp change x DV01: $10mm bond-vs-10y flattener, 155bp -> 111bp (44bp), DV01/spread $165 -> $7,260. Delivery-implied credit (DSF) = (DSF - ZN spread) - (cash 10y - ZN spread); examples 58 - 40 = 18bp (DV01-neutral) and 92 - 76 = 16bp (1:1).
