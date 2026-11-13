# G10 RFR and 3M RFR futures conventions (quick sheet)

Compiled from exchange, administrator and market-convention pages that were read as excerpts, plus the textbooks cited in the main skill. Verify every tick, size and last-trade
rule against the primary contract specification before sizing. Rows marked (v) are from general knowledge or a single excerpt and need verification. The trade's own
`swap_conventions` row always wins over this sheet.

## Overnight rates
| Ccy | RFR | Administrator / nature | Day count B | OIS payment lag (BD) | Notes |
|---|---|---|---|---|---|
| USD | SOFR | NY Fed, secured | 360 | 2 | OIS ACT/360 both legs, spot T+2 or forward-start on an FOMC date; prints next BD |
| EUR | ESTR | ECB, unsecured | 360 | 1 (another source: 2) | published each TARGET day for the prior day; euro term unsecured rate is Euribor |
| GBP | SONIA | BoE, unsecured | 365 (ACT/365F) | 0 | single dominant RFR after LIBOR; FRN observation shift 2 or 5 |
| JPY | TONA | BoJ, uncollateralised call | 365 (v) | n/a in sources | provisional and final prints; Tibor continues alongside |
| CAD | CORRA | Bank of Canada, overnight repo | 365 | not in sources | OIS ACT/365 both legs, Toronto calendar, Modified Following, spot T+0 (other sources differ); published 9:00-11:00 ET next BD, index 11:30 ET |
| AUD | AONIA | RBA overnight cash | 365 (A/365F) | conflicting in one convention document (2 BD after maturity vs 1st day after termination) | under 12m paid at maturity, over 12m annually in arrears after any front stub; most AUD IRS still reference BBSW |
| NZD | NZIONA | RBNZ overnight | (v) | n/a | rounding 0.0001%; no futures detail in sources |
| CHF | SARON | SIX, repo trades plus binding quotes | 360 | n/a | fixings 12:00, 16:00, 18:00 (18:00 is the reference fixing); compounded rates and index published for 1w to 12m |
| SEK | SWESTR | Riksbank, deposit-based (not repo) | 360 (v) | n/a | since 1-Sep-2021; compounded 1w-6m averages and index published |
| NOK | NOWA | Norges Bank, since 1-Jan-2020 | 365 | OIS working group: delayed payment | index published from end-Q1 2021; margin added without compounding; interdealer OIS proposal spot T+2, annual; NIBOR fallback = NOWA compounded in arrears, 2-day observation shift, spread adjustment, rebased to ACT/360 |

## 3M compounded RFR futures (reference quarter 3rd Wednesday to 3rd Wednesday, exclusive; price = 100 - R)
| Contract | Venue | Value per bp | Tick | Notes |
|---|---|---|---|---|
| SR3 (USD SOFR) | CME | USD 25 | 0.25bp front, 0.5bp otherwise | last trade the BD before the 3rd Wednesday of the delivery month; options last trade the Friday before the 3rd Wednesday of the contract month |
| SR1 (USD SOFR 1M) | CME | USD 41.67 | not in sources | arithmetic monthly average; settles to 0.1bp |
| SO3 (GBP SONIA) | ICE | GBP 25 | 0.25bp front, 0.5bp otherwise | EDSP compounded SONIA, ACT/365F |
| FST3 (EUR ESTR) | Eurex | EUR 25 (EUR 2,500 per index point) | not in sources | final settlement price set 09:00 CET |
| TONA 3M (JPY) | JPX (OSE), launched 29-May-2023; also TFX | about JPY 2,500 | not in sources | IMM-dated |
| CRA (CAD CORRA) | Montreal Exchange | CAD 25 | 0.25bp front, 0.5bp otherwise | nearest 12 quarterly months listed; CDCC cleared; Y = 365 in the settlement formula |
| SW3 (SEK SWESTR) | ICE | not in sources | not in sources | 100 - SWESTR compounded in arrears over the IMM quarter |
| FSR3 (CHF SARON) | Eurex | not in sources (v) | not in sources | SARON compounded over the reference quarter |
SR3 lists the 39 nearest quarters (older 2019 listing: 20 consecutive quarters); block minimum 250 / 500 / 1000 in Asian / European / regular hours. No NZD or NOK 3M RFR futures appear in the sources.

## Transition facts that still matter for history
- Legacy USD Eurodollar futures converted to SOFR futures at a 26.161bp spread; fallback spreads were fixed on 5-Mar-21 as the 5y median of LIBOR minus compounded SOFR; the
  lesser USD LIBOR tenors ceased 31-Dec-21, the rest 30-Jun-23 (Huggins & Schaller, SOFR Futures and Options, 2022, Ch.1).
- Legacy IBOR futures: month code = expiry month, point value USD 2,500 (3M), tick usually 0.5-1bp; do not mix with RFR month codes.
