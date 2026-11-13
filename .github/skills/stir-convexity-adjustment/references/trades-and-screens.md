# CA trades, screens and funding numbers (sell-side record)

Companion to [SKILL.md](../SKILL.md). All rows are historical and illustrative ("not necessarily trades that we would
recommend"). USD, CME-cleared forward swaps, pack CA in bp, short convexity unless stated. "vs model" = CA minus Ho-Lee
fair value on cap/floor vol. Impl/Rlzd = CA-implied vol over 3m realised pack vol.

## 1. Trade log
| Date | Trade | Entry | Result / notes | Source |
|---|---|---|---|---|
| 9 Feb 2017 | Sell Blues H0-Z0, USD 200k DV01: buy 2,000 of each, pay USD 2bn CME swap; hedge pay belly of 2s5s10s fly USD 147mm / -85.6mm / 20.89mm (0.705/-1/0.465) at -18.2bp | CA 8.8bp, about 4bp (2 sigma) wide to model and 3bp wide to the fly; target +USD 600k, stop -USD 350k; carry +USD 380k/3m; CA roll +1.3bp | closed 6 Jun 2017 at 6.6bp, fly -16.5bp; about +USD 0.5mm after costs; closed early for Greens | Citi, Sell Blues convexity adjustments, hedged, 9 Feb 2017; Turning Green from Blue, 6 Jun 2017 |
| 13-17 Jan 2017 | Original Blues sizing, USD 100k DV01: 1,000 H0-Z0 packs vs USD 1bn swap; fly USD 79mn / -44.4mn / 10.9mn | CA 10.02bp, +4.61bp vs model (3m z 2.66), roll 1.30bp, implied vol 125.5 vs realised 95.1, cap vol impl/rlzd 0.9; carry about +USD 206k/3m (130k CA + 76k hedge); a 3y1y straddle hedge (USD 96mn) carries only +USD 65k | | Citi, Swearing in huge expectations, 13 Jan 2017; Buy long expiries, 17 Jan 2017 |
| 15 May 2017 | Sell Greens M9-H0, USD 100k DV01, pay USD 1bn M19-M20 CME swap; hedge sell 167 EDM9 / buy 141 EDM8 | about 4.5bp; CA 4.91, +3.43 vs model (3m z 0.82, 1y z 1.48), roll 0.81, implied 125.6 vs 73.7 (1.7) | | Citi, Value in Greens convexity, 15 May 2017 |
| 6 Jun 2017 | Sell Greens M9-H0, USD 300k DV01, USD 3bn swap; hedge sell 500 EDM9 at 98.215 / buy 424 EDM8 at 98.46 (ratio 1.18) | 4.3bp; target +USD 450k, stop -USD 225k; roll 0.7bp | hedge removed 13 Jul at CA 3.35bp, +USD 70.5k; closed 8 Aug at 2.65bp, +USD 475.5k net of costs | Citi, Alert: Take off the hedge on short Greens convexity, 13 Jul 2017; Alert: Target achieved on short Greens convexity, 8 Aug 2017 |
| 8 Jan 2018 | Sell Blues H1-Z1, USD 100k DV01; hedge buy 130 EDM9 (ED6) / sell 176 EDZ1 (ED16) | CA 7.13 (3m z 2.44), +4.26 vs model, roll 1.32 (highest), implied 105.4 vs 50.4 (2.1); carry +USD 140k/3m | | Citi, Sell Eurodollar convexity in Blues, 8 Jan 2018 |
| 18 Apr 2018 | Sell Blues outright; alternative hedge ED6/ED16 steepener 0.74/-1 | 7.2bp, Blues/Golds about 2 sigma wide to model; Blues preferred to Golds for liquidity | | Citi, What to expect when you're expecting a turn, 20 Apr 2018; Convexity Meets Steepeners, 19 Apr 2018 |
| 11 Jun 2021 | Sell Blues M4-H5, 1,000 packs vs USD 1.01bn CME 6/17/24-6/16/25 swap | 7.9bp; carry +1.2bp/3m; target 4bp tighter, stop 3bp wider | closed 3 Dec 2021 at 3.4bp, +USD 389k (as recorded in the Feb 2023 weekly) | Citi, Left-side vols' outperformance, 22 Jun 2021; Time for moderation, 17 Feb 2023 |
| 12 Jun 2023 | Short Blues thesis: if vol stays near lows, Blues compress about 5bp to model | M6-H7 CA 15.40, model 9.98, +5.42, roll 1.70, implied 163.1 vs realised 130.9; M7-H8 22.29/14.50/+7.79, roll 2.21 | back packs implied/realised 1.1-1.3, front packs below 1 | Citi, Forward steepener and vol divergence, 12 Jun 2023 |
| 17 Feb 2023 | Sell Blues H6-Z6, 1,000 packs vs USD 1.17bn CME swap | 12.7bp, ATMF 3.14%; carry +1.5bp/3m; target 4bp, stop 2.5bp | | Citi, Short Blues convexity via futures/swaps, 21 Feb 2023 |
| 9 Oct 2026 | Long CA: sell 1,000 Blue pack, receive USD 1.19bn CME 12/19/29-12/17/30 swap at 5bp (ATMF 4.7%); vs sell EUR 300mm 6m1y ATMF straddles (premium EUR 1.61mm, vega -EUR 16k); delta-hedge beyond net 25 delta | Blues/Golds CA 3bp/5bp below model, near multi-year lows despite higher implied vol; target +USD 300k, stop -USD 200k; risk: ECB hikes aggressively | | Citi, Pension plan for 20s?, 9 Oct 2026 |
| 3 May 2017 | Sell H9 and M9 CME-based CA: buy H9/M9 EDs vs pay CME-cleared FRAs, pvbp-weighted | monetises rich CA and positions for a wider front-end CME/LCH basis | | J.P. Morgan, A better way to sell vol, 3 May 2017 |

Entry rule published for the 2017 trade (all five): about 4bp (2 sigma) wide to model; about 3bp (2 sigma) wide to the fly;
roll pays the short (+1.3bp/3m); implied vol about 30% rich to 3m realised; dealer positioning stretched. Targets/stops in bp
of spread: +3.0/-1.75, +4/-2.5, +4/-3.

## 2. Screen snapshots (CA / vs model)
| Date | Observation | Source |
|---|---|---|
| 9 Dec 2016 | Z0-U1 CA 11.86, +2.92 (1y z 1.01), impl 110.5 vs rlzd 86.0, roll 1.07; Golds about 3bp (1 sigma) rich | Citi, Year-Ahead: Bumpy road for vol, 12 Dec 2016 |
| 6 Jan 2017 | Blues H0-Z0 10.20, +4.31 (3m z 3.15, 1y z 2.81), roll 1.27, impl 126.1 vs 94.2 | Citi, Long Live Formosa, 9 Jan 2017 |
| 13 Jan 2017 | Greens H9-Z9 5.32 (+2.93); Blues H0-Z0 9.96 (+4.48, z 2.73), widest since 2015; Golds H1-Z1 13.26 (+4.22) | Citi, Buy long expiries, 17 Jan 2017 |
| 2 Feb 2017 per contract | H8 1.12 (+0.92), Z8 2.65 (+1.74), Z9 6.21 (+2.96), H0 6.44 (+2.40), U0 9.12 (+3.58), Z0 11.05 (+4.64), H1 10.65 (+3.37), Z1 14.86 (+5.00, z 2.52): EDZ9, EDZ0 cheap to neighbours | Citi, Going nuclear (on the curve), 3 Feb 2017 |
| 28 Apr 2017 | H0-Z0 6.76, +3.27, impl 112.3 vs rlzd 76.6 | Citi, Fair value vs seasonality, 1 May 2017 |
| 12 May 2017 | front packs fair (M7-H8 +0.20, U7-M8 +0.42) | Citi, Value in Greens convexity, 15 May 2017 |
| 9 Mar 2018 | Z9-U0 1.96 (model +0.86); H1-Z1 6.00 (model 2.48); would sell Blues if wider | Citi, The art of gamma hedging, 12 Mar 2018 |
| 11 Jan 2019 | H0-Z0 0.79, +0.16 (3m z -2.85, 1y z -4.29): compressed to fair on short covering | Citi, Gamma and Vega RV, 14 Jan 2019 |
| 22 Mar 2019 | M9-H0 -0.02 vs model; Z1-U2 to M2-H3 -0.55 to -1.44 (3m z about -3) | Citi, Vol cycle, steepeners, and SOFR, 25 Mar 2019 |
| 8 May 2019 | M9-H0 0.01, H1-Z1 0.95, H2-Z2 2.12, M3-H4 4.93; Golds slightly rich, Blues cheap | Citi, Trading long-dated convexity, 9 May 2019 |
| 24 Sep 2019 | H2-Z2 3.00 (+0.96, 3m z 1.25), Z2-U3 5.11 (+1.90), M3-H4 6.09 (+1.94), Z3-U4 7.03 (+1.81); impl 85-88 vs rlzd 90-93; cause: asset-manager positioning shift | Citi, Buying vol for less, 25 Sep 2019 |
| 16 Jan 2020 | H2-Z2 1.93, +0.49, 3m z 2.05 | Citi, In search of cheap vol, 17 Jan 2020 |
| 27 Mar 2020 | CA about 0.03 (M0-H1) rising to 7.25 (M4-H5); M4-H5 model gap 2.79, roll 0.72, implied 82.5 vs rlzd 131.3 (COVID, zero bound) | Citi, Liquidity, vega, and convexity, 30 Mar 2020 |
| 16 Feb 2023 (SOFR) | H4-Z4 2.67 (+0.46); H5-Z5 8.45 (+3.28); H6-Z6 13.09 (+3.65, roll 1.53, impl 147.6/rlzd 134.9); Z6-U7 19.37 (+6.70); H7-Z7 21.24 (+7.37); CA rises monotonically with maturity; implied/realised 1.1, cap-vol impl/rlzd 0.9 | Citi, Short Blues convexity via futures/swaps, 21 Feb 2023 |
| 11 Sep 2026 | U7-M8 0.88 vs model 1.39 (-0.51); H9-Z9 3.86 vs 4.96 (-1.10); Golds U0-M1 7.93 vs 10.04 (-2.11); implied 90-95 vs realised 67-81 | Citi, Slow and steady wins the short gamma race, 14 Sep 2026 |
| 2 Oct 2026 | Golds about -5bp vs model, Blues -4 to -5bp, model rebounded with higher vol; pack labels in the table look stale | Citi, Fading vega dislocations, 5 Oct 2026 |

Reading across years: the sign of CA - model flipped from rich (2017-18, 2023) to cheap (2019 pockets, 2026). Do not
hard-code a direction.

## 3. Funding, margin and CCP numbers
- Implied 2y funding spread (rolling 8th ED vs LCH FRA) rose from L+50-100bp (2016) to about L+300bp as dealer net ED longs rose toward
  4,000-4,500k contracts. LCH IM about USD 1.2-1.5mm per USD 1bn (Z7-Z9) vs CME netted USD 0.15-0.45mm (70-80% saving); yet CME excess CA was
  about 80% of LCH's. Implied funding: LCH about 150-290bp/yr, CME rising to about 1,000bp/yr at M9 vs typical about 100bp. Front-end CME/LCH basis
  about 0.25bp, 30y about 3.8bp (J.P. Morgan, A better way to sell vol, 3 May 2017).
- Frictionless convexity: ED vs FRA P&L is a "smiley face"; with VM funded overnight at a 25bp spread and IM term-funded, the convex
  payoff survives only under CME portfolio margining; ED-CME vs FRA-LCH shows humps from funding two lots of VM. Uncleared FRAs made convexity "much
  sweeter". LCH IM on an example FRA is itself slightly convex (Clarus Financial Technology, CME-LCH Basis: Convexity in Eurodollar
  Futures, 1 Jul 2015; stylised).
- CME IM example: futures hedge USD 569,910 vs swap USD 1,568,352 (about 36%); separately USD 2,138,262 vs portfolio-margined USD 46,161
  (about 98% lower). Futures margin period of risk 1 day vs 5 for IRS (CME Group, Pricing and Hedging USD SOFR IRS with SOFR Futures, 4 Jun 2025).
- CME-LCH 10y basis ranged about 1-4.5bp (Nov 2015 to late 2018); a 26 Jun 2017 screen showed 0.10 (1y), 2.45 (10y), 3.55 (50y) (Citi, Shorts increasing?
  An alternative view of positioning, 16 Jan 2019).

## 4. Skew as a capitulation signal (Citi, Sell Blues convexity adjustments, hedged, 9 Feb 2017)
3m change in the 3m10y 25bp-out risk reversal, Jan 2006 to Nov 2016, bucketed; next-month 10y yield change (mean / median / % up):
lowest quartile -11.5bp / -5.0 / 36%; 25-50th -2.1 / -1.1 / 48%; 50-75th 0.2 / -4.2 / 45%; top quartile +8.8 / +11.1 / 69%. Flatter
skew precedes rallies, shorts capitulate, CA tightens. Use the extremes only.

## 5. Internal backtest of pack CA (unpublished replication, treat as indicative)
Short pack CA (buy pack, pay matched 1y swap, DV01-neutral) vs beta-sized 2s5s10s fly, SOFR, Aug 2020 to May 2024 (3.76y), USD 100k/bp,
zero cost: unhedged +USD 5.05mm (Sharpe 0.47, max drawdown -USD 1.69mm); hedged +USD 4.45mm (Sharpe 0.41, -USD 1.66mm). 1bp round-trip
cost cuts to +USD 1.15mm / +0.55mm; 2bp removes both. Break-even costs 1.2-1.6bp per leg vs 0.25bp assumed. Fly hedge: R^2 0.000-0.010,
sign-flipping beta; positive variance reduction in 15.8% of 1,890 fly-hedge cells; best-cell deflated-Sharpe p = 0.924 vs a 0.95 bar. Deep
packs (ranks 9-14) did better than front packs; noise/CA level 30% on ranks 1-8 vs 7% on ranks 13-17. Lesson: the unhedged carry/convergence edge
is real but thin versus costs, and the common fly hedge mostly hedges curve shape, not vol.

## 6. Data traps observed in building CA series
- Snap mismatch: an end-of-day snap near 17:00 NY against a futures settle near 15:00 ET produced 1.82bp/day noise on near packs (true CA moves
  about 0.55bp/day). Use settlement prices throughout.
- Roll detection: SR3 trades on a 0.0025 grid while its final settle (100 - compounded SOFR) is off-grid: the ending contract is off-grid, the new contract on-grid.
- Node coverage: with curve nodes starting after the window the terminal pack instrument is extrapolated. Rule: maximum curve tenor >= 3 x instruments + 6 months.
- Deep strip settles become sparse (contracts beyond rank 16 priced on few dates per year in 2023-24): require a settle on the date, never forward fill.
- CFTC positioning: lag to the publication date (3 business days after the Tuesday position date); during releases gaps (e.g. government shutdown, or a
  gap after 24 Jan 2023) extrapolate with open-interest changes and yield moves, or read the CA as the gauge.
