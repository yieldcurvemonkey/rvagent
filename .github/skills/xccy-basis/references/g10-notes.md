# Cross-currency basis: G10 market notes, dated levels, trade log, official backstops

Companion to [SKILL.md](../SKILL.md). Levels are dated illustrations from published research, not current data:
re-read the live tables. Sign: bp on the non-USD leg vs USD flat, negative = USD premium. "Pay" and "receive" below
follow the source's own wording; by P&L, "pay basis" gains when the basis rises (less negative) and "receive basis"
gains when it falls (both checked against the quoted marks, e.g. a pay at -31 marked at -22 gained; a receive at -12.8
gained as the basis widened in March 2020).

## 1. Reference rates and conventions
| ccy | leg vs SOFR | notes |
|---|---|---|
| EUR | ESTR, ACT/360 both legs, quarterly | MTM swap, spread on the EUR leg; the IBOR-based EUR/USD swap was removed from standard quoting in Feb 2023 |
| GBP | SONIA ACT/365 vs SOFR ACT/360, quarterly, 3M-50Y | GBP swaps value T+0 |
| JPY | TONA ACT/365 vs SOFR ACT/360 | USD funding in JPY: most negative of the majors |
| CHF | SARON ACT/360 | SNB sight deposits proxy intervention |
| CAD | CORRA ACT/365 vs SOFR | USDCAD spot lag T+1; CDOR (ceased Jun 2024) historically carried a positive basis |
| AUD | 3M BBSW (term bank bill) vs SOFR | not overnight: adjust comparisons; BBSW-OIS about 8.5-10bp (Aug 2026) |
| NZD | 90-day BKBM (term) vs SOFR | liquidity-driven via settlement cash |
| SEK, NOK | leg index not specified in the sources; read `swap_conventions` | structural bank liquidity keeps funding negative |

Confirm index and day count in `rate_indices` and the leg setup in `swap_conventions` before computing an implied
basis. Snap times matter: London 4pm, NOK 4pm CET, SEK/DKK 4:15pm CET, NY 3pm, Tokyo 3pm, Sydney 4:30pm; comparing an
FX-implied basis with an OIS curve from a different snap contaminates the residual.
(Deutsche Bank Index Quant, Interest Rate Curve Creation Process, 2 Feb 2023)

## 2. What drives each currency (published views)
- **EUR/USD**: relative swap spreads (80-90% of levels), Fed vs ECB reserves and QT, Yankee (narrows) vs reverse-Yankee
  (widens) issuance, USD hedging by real money (widens; European investors hedge about 27% of US equities and 96% of US
  fixed income, vs a 2015-2020 equity average that would imply 56%). Tightening themes: Europe fixing its saving-investment
  imbalance, US fiscal concern vs Germany, de-dollarisation, rebalancing to pre-QE euro shares (about EUR1.7trn extra euro
  debt demand, hedged more than other assets), QT divergence. Widening offsets: higher hedge ratios, post-debt-limit TGA
  rebuild. (BofA, FX-Sofr and xccy: tightening themes, 3 Jun 2025)
- **USD/JPY**: large NFA gives a structural negative basis. Lifers hedge USTs/MBS with FX forwards and credit with
  forwards or matched xccy; banks fund UST/MBS in repo and credit plus the loan-deposit gap through matched xccy; GPIF does
  not hedge. About 50% of lifers' foreign bonds hedged (2024). Samurai issuance peaks May-Jul (widening). Yen
  appreciation tends to tighten. JBIC/NEXI financing of the US investment framework is too small to move the basis
  ($6.9bn financed by Aug 2026). (JPM, 2H25 and 4Q24 Outlooks; Citi, FX Basis Quarterly, 13 Dec 2024; Citi, Japan Rates
  Weekly, 21 Aug 2026)
- **GBP/USD**: tracks BoE reserves (about -0.1bp per GBP bn), roughly 40-48% beta to EUR; not a relative-policy trade;
  BPA buy-outs widen the 30Y and keep 10s30s flat. (JPM, 2H25 Outlook)
- **AUD/USD**: positive, wide to NFA; domestic banks issue about USD 100bn of term funding a year and pay basis for it;
  pension funds (about A$4tn, low hedge ratio) raising hedge ratios would steepen the front; Kangaroo issuance narrows,
  semi offshore issuance adds pay-side flow. Long-end receiving inverts the 20Yx5Y. (JPM, 2H25 and 4Q24 Outlooks)
- **NZD**: settlement cash (about NZ$24-27bn) and OMO replenishment drive the basis; a tax outflow cut cash 26.5bn to 24bn
  and moved 1w-1m NZIONA/SOFR 5-7.5bp tighter while forward-forwards stayed stable. (Citi, STIRT Weekly, 14 and 21 Aug 2026)
- **CHF**: deeply low to NFA (residual -36bp); SNB balance sheet rather than front-end yields; practical lower bound
  about -75bp (2015). (JPM, FX basis, 20 Feb 2020; JPM, 11 Mar 2015)
- **CAD**: high to NFA (residual +29bp, 100% positive), but funding is volatile: a Jul/Aug 2026 month-end turn did a
  40bp round trip (FXOIS -20 from +20; overnight FXOIS +60). Do not pay the front-end CAD basis at historical tights.
  (Citi, STIRT Weekly, 7 Aug 2026)
- **SEK, NOK, DKK**: structural liquidity (NOK above NOK150bn; SEK certificate auction left SEK112bn; DKK current account
  about DKK380bn) kept funding near -20bp FX-OIS in Aug 2026. The Swedish stability fee on bank liabilities has influenced
  SEK/USD xccy. (Citi, STIRT Weekly, 7 Aug 2026; Darbyshire, Pricing and Trading IR Derivatives, 2022)
- **Cross-currency (non-USD) bases** are built from two USD legs (EURJPY basis = EURUSD basis and USDJPY basis); the
  EUR-JPY 10y relationship is strong enough to map a EUR view onto JPY. A 1.5 : 1 : 1 DV01 package, pay 1y1y JPYUSD vs
  receive 1y1y EURUSD and CHFUSD, flat at -25bp, was run in Aug 2019 because JPY/EUR/CHF are the most correlated bases;
  closed because 3bp of 3m carry did not cover quarter-end hedging-flow risk. (Citi, US Rates Weekly, 2 Aug 2019)

## 3. Dated level snapshots (illustrations)
| as of | pair | curve (bp) | source |
|---|---|---|---|
| 27 Mar 2015 | EUR/USD | 3M -24, 1Y -28, 2Y -32, 3Y -35, 5Y -38, 10Y -38, 5Yx5Y -39 | JPM, Stretched EUR/USD valuations, 27 Mar 2015 |
| 25 Sep 2024 | EUR/USD | 3M -2, 1Y -6, 2Y -8, 5Y -11, 1Yx1Y -10, 5Yx5Y -18, 10Yx10Y -11 | JPM, 4Q24 Outlook |
| 22 Sep 2024 | USD/JPY | 1Y -36, 2Y -41, 5Y -53, 10Y -60 | JPM, 4Q24 Outlook |
| Sep 2024 | GBP/USD | 1Y 0, 5Y -5, 10Y -9, 30Y -28 | JPM, 4Q24 Outlook |
| 21 Feb 2025 | USD/JPY | 1y -32, 5y -40, 10y -42 (1s5s about -8, steepest in a decade) | JPM, Japan Weekly, 21 Feb 2025 |
| 5 Jun 2025 | 1Y / 5Y | EUR -4/-5, JPY -33/-44, GBP +3/0, AUD +2/+5, CHF -17/-19, SEK +4/+3 | JPM, 2H25 Outlook |
| Aug 2026 | USD/JPY | 1Y about -20, 5Y narrowed about 10bp over the year | JPM, Global FI Weekly, 21 Aug 2026 |

Year-end: the turn premium is customarily priced but "rarely realised", overnight often collapses on the day (Lehman, The
Short-End of the Curve, 10 Jul 2007). Year-end 2024 was benign relative to the prior-year average turn (JPM 4Q24; the chart units are not legible, so no level is quoted).
Year-end turn basis was at multi-year tights in EUR, JPY and CAD in Aug 2026 before any G-SIB change (Citi, 14 Aug 2026).

## 4. Trade log (as published; not recommendations)
- Receive USD25k/bp 2Yx1Y EUR/USD at -12.8 (set 20 Feb 2020): basis had narrowed on light flows, rich vs FRA/OIS and
  GC/OIS FV; structural G-SIB daily-averaging cuts FX-lending capacity; hedges paid SOFR/FF and FRA/OIS shorts. P&L in
  bp: -0.2 (21 Feb), +2.7 (28 Feb), +4.3 (6 Mar). (JPM, 20 Feb 2020 and 6 Mar 2020)
- Pay USD25k/bp 10Yx10Y AUD/USD at +41.5 (Yankee and stimulus-driven issuance paying): P&L in bp -1.9 (28 Feb), -6.3 (6 Mar
  2020). (JPM, 28 Feb 2020 and 6 Mar 2020)
- Pay 1y1y SOFR/TONAR USD25k DV01 at -31, marked -22 (+USD226k), target -23, stop -37 (Aug-Oct 2026). Same trade in Feb
  2023 opened at about -63, carry +5bp per 6m. Pay 3m1y SOFR/TONAR at -38 (13 Dec 2024), carry about 3bp per 3m, risks
  VaR shock/bank stress in Q1. (Citi, US Rates Weekly, 21 Aug and 9 Oct 2026; Citi, 17 Feb 2023; Citi, FX Basis Quarterly,
  13 Dec 2024)
- Receive 3Mx3M EUR/USD OIS/OIS basis at -59, USD50k DV01, for a more punitive year-end (Sep 2019). (JPM, 13 Sep 2019)
- Hold the 3s/10s EUR/USD basis steepener (3Y -35, 10Y -38, 27 Mar 2015): front end widens on balance-sheet divergence,
  long end supported by soft EUR issuance by US names; no stop given. (JPM, 27 Mar 2015)
- JPM 4Q24 EUR views: 1Yx1Y/5Yx5Y flatteners near -8; 2H25: front-end widening bias, 1Yx1Y ESTR/SOFR widener with modest
  positive carry. Citi (Aug 2026): structural paid 1y1y GBP xccy, wait for levels; received front-end EUR near range tops.
- Pay 1y10y ESTR/SOFR (12 Dec 2023 to 12 Dec 2024) accrued nearly 25bp, about 60% in the last two months. (Citi, FX Basis
  Quarterly, 13 Dec 2024)
- Synthetic AUD bond: buy JGB or T-bill, asset-swap to JPY, convert to BBSW + basis with AUD/JPY basis swap, receive AUD
  fixed. Pickup over ACGB about 40bp at 1Y rising to about 120bp at 6-7Y; mark-to-market volatility comes from three legs,
  the basis largest. (JPM, 11 Mar 2015)
- Basis as an expression of a funding view: hawkish-Fed funding tightening is better expressed in basis than in a steepening
  front end; in flat curves (EUR, CHF, CAD) receive SOFR/FF and the basis; FX-OIS neutralises SOFR coupon exposure. Receiving
  basis hedged other excess-cash positions (FRA/OIS shorts, paid SOFR/FF). (Citi, STIRT Weekly, Jun 2026; JPM, 20 Feb 2020)

## 5. Official backstops and the dollar-rate hierarchy
- Standing Fed swap lines with the ECB, BoE, BoJ, BoC and SNB, priced OIS + 25bp (cut from OIS + 50bp in March 2020, with
  temporary lines of USD30-60bn to nine more central banks); near-zero usage outside crises (cost, tenor, stigma); usage now
  spikes at period ends and about USD1bn outside period ends has been a sign of tight interbank conditions. (BofA, FX-Sofr
  primer, 31 Oct 2023; Conks, The Fed's Global Put Part I, 16 Sep 2024)
- Normal-times ordering, highest to lowest: FIMA repo facility rate, swap-line rate (OIS + 25bp, "private offshore
  ceiling"), FX-swap-implied T/N USD rate, repo-facility and discount-window rates, IORB, EFFR, GC repo, SOFR, tri-party
  repo, foreign repo pool and ON RRP floors. Conks stresses the bounds hold "in theory (not always in practice)": very
  short-end USD/JPY traded well below -50bp on non-period-end dates in Sep 2024. Diagnostic: the gap between the T/N
  FX-swap-implied USD rate and the swap-line rate (4.13 vs 4.14 in Nov 2025, about 1bp from the ceiling; 3.76 vs 3.90 in Mar
  2026, 14bp). (Conks, Plumbing Notes, 24 Nov 2025 and 1 Mar 2026)
- FIMA repo (UST collateral for USD, USD60bn per counterparty, 7-day, 1-5% haircut by maturity) avoids forced Treasury sales.
  Foreign official dollars earn the ON RRP rate in the foreign repo pool; BoJ deposits JGB repo minus 5bp; RBA and RBNZ take
  no foreign deposits; BoC CAD accounts at the overnight deposit rate. (BofA, FX Intervention primer, 8 Jul 2024; BofA,
  FX-Sofr primer, 2023)
- FX intervention effects on funding fade in about 1-2 weeks; Japan intervention is sterilised but can cause temporary yen
  shortages that lift domestic money rates (Sep/Oct 2022 JPY9.2trn over 3 days; Apr/May 2024 about JPY9.8trn over 2 days).
  (Citi, STIRT Weekly, 7 Aug 2026; BofA, FX Intervention primer, 8 Jul 2024)
- Stress episodes: GFC (3M Libor-OIS after Lehman, 15 Sep 2008; unlimited swap lines 13 Oct 2008); Covid (swap lines
  15 Mar 2020: dealers, then foreign banks, then US megabanks pulled back before the Fed acted); Aug 2024 yen-carry
  unwind (USD/JPY basis barely moved, other bases flat, recovered by 26 Aug); Mar 2023 (AUD/NZD bases can tighten in global
  USD stress while EUR/JPY widen because banks fund abroad and swap back). In a war/stress regime onshore funding can stay lax
  (MMF inflows) while offshore bases widen; convergence only after resolution. (Conks, Plumbing Notes, 11 Mar 2026; Conks,
  Money Market Update, 12 Aug 2024; BofA, FX-Sofr primer, 2023)

## 6. Regulatory calendar effects
- US G-SIB score measured at year-end (Q4 shrinkage), SLR a daily average; euro-area leverage ratio reported at quarter-end
  and as a daily average (window dressing persists); JPY quarter-end widening comes from the USD side; the UK PRA bans
  short-term window dressing. G-SIB snapshots hit FX swaps more than repo (four G-SIBs' FX-swap notional -6.2% q/q in 4Q19
  vs -0.4% in 2018); repo enters the score as annual averages, so year-end shows up most in the basis. Money-market funds
  cannot lend in FX swaps. Reform (daily/monthly averaging, 10bp surcharge increments) would compress the turn; Citi saw it as
  a 2026 story. Avoid taking exposure over a year-end before reform clarity. (BofA, FX-Sofr primer, 2023; Barclays, US Short
  Interest Rate Primer, Jan 2025; JPM, 20 Feb 2020; Citi, STIRT Weekly, 14 Aug 2026)
- Quarter-end widening is technical and reverts: use it for entry timing, not for a view. A forward-starting pay of a
  basis that rolls down positively is the common carry expression; the 5y-reverts-to-3m-roll rule broke after the GFC.
  (JPM, 11 Mar 2015; Clarus Financial Technology, Mechanics and Definitions of Carry in Swap Markets, 16 Jan 2019)
