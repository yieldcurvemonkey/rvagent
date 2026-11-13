# Published swap-spread and ASW trades: structure, levels, risk, outcome

Use as templates for trade structure, sizing and stop/target logic, not as current ideas. Sign tags: **(S-G)** swap minus govt, **(G-S)**
govt minus swap, **(printed)** publisher's sign, leg description is authoritative. "W" = widener (buy bond + pay swap, profits as S-G rises),
"T" = tightener. Entry / target / stop in bp unless stated.

## USD outright and curve

| Date, source | Structure | Levels | Result / note |
|---|---|---|---|
| 29 Mar 2019, JPM Interest Rate Derivatives, A comprehensive look at convexity hedging | 5y MMS: long $100mn 2.625% Dec-23 vs pay $101mn swap to 12/31/23 | +6.75 (S-G) | 3M carry + slide +1bp; P/L -3.9bp |
| 31 May 2019, JPM, Is bank convexity hedging lying in wait? | T: sell $200mn 2.00% May-24, receive $200mn OIS to 5/31/24 | 23.3 (printed) | carry ~-1bp/3M, slide ~flat; rationale bank receiving, FX reserve outflows, dealer inventory, fiscal. Unwound 2Yx5Y wideners at -3.91bp |
| 3 Aug 2018, JPM, The long and short of it | 30y T hedged for curve: sell $25mn 3.125% May-48, receive $47.6mn swap at 4.54, sell $57.8mn 2.875% May-28 (50% matched-duration 10s/30s) | 4.54 (S-G) | 1M carry+roll -0.5bp; profit taken at +1.0 |
| 14 Sep 2018, JPM, Issuance, pensions, and long-end spreads | short $300mn 2.625% Jun-21 vs receive OIS | -15 | carry ~0/3M, slide -1.3bp; result -1.5bp |
| 2 Apr 2020, JPM, What about Bonds? | 30y MMS vs fair value | actual -40 vs FV -54, 6M projection -57, target ~-60 | earlier -80 judged illiquidity overreaction |
| 3 Jan 2017, Citi, Corporate supply to bring spreads tighter | tactical 10y T for first two weeks of Jan | no levels | 10y ~2bp wide to 30y per 0.41 x 30y + 6.71; 30y already -4bp in last week of Dec |
| 4 Oct 2019, Citi, All it takes is a little push | 30y T | -38.9 | risk: more aggressive QE. Steady-state private supply ~$500bn implies 2y OIS/UST near -15 vs -24 (W) |
| 18 Jan 2019, Citi, The rocky road to a steeper curve | TU/OIS W | -20 (14 Dec 2018) to -16.2 (17 Jan 2019) | +$210k. Bill paydown ~$130bn (Apr/Jul) +2 to +5bp; +$220bn bills Aug-YE -3 to -8bp |
| 2 Aug 2019, Citi, Learning on the job | TU OIS T | -23.6 entry, -26.5 now, target -28 | model ~3bp wide |
| 17 Feb 2023, Citi, Time for moderation | short TU SOFR invoice spread 50k DV01 | +3.125, target -7, stop 9 | now 6.3, -$134k; hedged with long 10y spreads |
| 21-22 Aug 2026, JPM, Global FI Markets Weekly | 2y W: buy $100mn T 4.25% Jul-2028 (4.232%, PVBP 184.0), pay $96.2mn SOFR swap (4.083%, PVBP 191.3) | -14.9 (S-G) | ~4bp 3M carry vs 2.3bp/3M delivered vol |
| 9 Oct 2026, Citi, Pension plan for 20s? | long 5y MMS 50k DV01 | -26.5, target -18, stop -34 (now -29) | long 10s20s spread curve 20k DV01 -30, target -15, stop -40 (now -22, +152k); debt-ceiling cheapening of 1y spreads 5-10bp expected |
| 2 Oct 2026, JPM, Near, far, wherever yields are | unwound 2Y MMS wideners at -1.9bp; neutral | TFP/ZDS below fair value but flow headwinds | rule: when valuations conflict with flow headwinds, go neutral |
| 19 Aug 2026, JPM, Buying back time | 10s/30s spread-curve steepeners off at +1.4 | 2s/30s spread moved -60 to -55 intraday on upsized buybacks | neutral because TFP ~1 sd above FV |
| 5 Nov 2025, JPM, No alarms and no surprises | unwound 5s/30s MMS flatteners at +0.2 (opened 31 Oct 2025); kept 2s/3s, 3s/5s | TFP within 1 SE of model | refunding pushed back on coupon cuts: 30y ~1.5bp narrower, 2y flat |
| 9 Oct 2025, Rhodes, USD 5s30s Swap Spread Flattener | 30y-5y diff flattener | entry -43.1 (z +2.1), target < -53, stop > -40; risk ~3 vs reward 8-12 (~2.5:1) | OLS residual of 5y on 30y -6.3bp (~-1.5 sigma); back-test since 2023: >40d hold hit rate 100% (small sample), avg +14bp, optimum hold 40-80 trading days; diff range -36 to -55 over 2022-25 |
| 2 Jul 2025, BofA, Lower UST WAM => backdoor easing | 3y-20y spread-curve steepener (rotated short from 30y to 3y) | -51, target -30, stop -65 | front-end spreads cheapen on bill supply and debt-limit resolution; back-end (20y) richens on WAM shortening |
| 2 Oct 2026, BofA, Global Rates Weekly | open book: long 30y ASW spread -71/-55/-80 (entry/target/stop), latest -67; long 2y ASW -14/-10/-19, latest -15 | (printed) | rates-vol spike causes breakdown in RV relationships and de-risking: risk to 2y/30y wideners |
| 30 May 2018, BofA, buy 2y Treasury vs OIS | buy T 1.75% 11/15/2020 vs OIS | 18 cheap (UST - OIS), target 0, stop 25 (risk 7 to make 18) | scenario-robust: Treasuries richen vs OIS in either Fed framework; risks foreign reserve selling, front-end issuance, HQLA rewrite, FHLB FF lending |
| 27 Sep 2017, BofA, sell 2y spreads | sell T 1.375% 9/30/2019 vs OIS | -3.5, target +5, stop -8 (risk 4.5 to make 8.5) | custody holdings +$260bn YTD to $3.05tn; 2y coupon forecast $26bn to $35bn |
| 2 Oct 2026, Citi, OAT of the blue | long 5y TIPS ASW 34bp to 31, +$182k | target 14, stop 49 | T-bill swap spreads 4m/6m tightened sharply (1y z -3.4/-3.2) |

## Non-USD

| Date, source | Structure | Levels | Result / note |
|---|---|---|---|
| 24 Sep / 1 Oct 2026, Citi, European Rates Weekly | buy KUNTA 2.625% Dec29 / sell RFGB 2.5% Apr30 on OIS swap spread (G-S) | 17.4, target 6, stop 24; 3m carry 2.2 | later 18.0; SSA OIS spread stayed within ~2bp in a sell-off |
| same | buy KFW 2.75% Feb31 / sell DBR 0% Feb31 | 26.0, target 18, stop 32; carry 1.9 | later 29.7 (P&L -4) |
| same | buy BERGER 2.875% Apr29 / sell KFW 0% Sep28 | 15.0 / 17.6 now, target 5, stop 21; carry 0.4 | |
| 19 Aug 2026, Citi, The Morning Call | buy EU 0.7% Jul51 / sell RAGB 0.75% Mar51 | 25.3, now 27.5 | EU vs swaps ~1bp wider up to 10y, 2-3.5bp 15-30y in the sell-off |
| 2 Oct 2026, BofA, Global Rates Weekly | long 30y JGB ASW (G-S) | 45/35/52, now 47-49 | long UKT 0.875% 2033 on ASW (monitored on z-spread) 38.3/25/45, now 35.6-37; UKTi 2031-38 forward ASW richening 101/70/115/93; EUR short 10y Bunds vs swaps stopped 4.7 / 1 / 7, closed 8 |
| 5 Sep 2024, BofA, UK Rates Viewpoint: Back to school | sell UKTi 2036 vs buy UKT 2042 on ASW (matched-duration, 6y apart in maturity, 0.4 in duration) | -21 (UKTi less UKT), target -8, stop -28 | buy UKT 4 3/8 2054 vs T 4 5/8 05/15/54 on ASW 1.0 / -15 / 10; buy UKT 5/8% 2050 vs 4 5/8% 2034 on ASW 33.5 / 13 / 45; sell UKT 4.5% 2028 / buy 0.5% 2029 on z-spread -8 / -20 / +4 |
| 10 Nov 2022, BofA, Will retail discover Gilts? | sell UKT 4.125% 2027 / buy UKT 0.125% 2028 on ASW (OIS z-spread difference) | +1.8, target -25, stop +12 | closed at -25.4 in Aug 2024 |
| 17 Mar 2022, Citi, A narrative shift looms | sell gilt Oct50 ASW vs SONIA 26/40/26; take profit long BANCAR Oct28 ASW 54 to 26.5 (+28bp) | | covered NCR 2022e -EUR 11bn vs -61bn 2020, -57bn 2021 |
| 21 Feb 2025, JPM, Non-Stop Dynamics | JGB narrowers: receive 30Y swap 1.848% vs short 30Y JGB 2.251%; receive 10Y swap 0.940% vs short 10Y 0.960% | P/L -1.5bp (30y), +9.4bp (10y) | closed 10Y +12bp (Jan to Mar 2024), 2Y +4bp |
| 21-22 Aug 2026, JPM | pay AUD 10Y spread (pay 10Y IRS, buy 10Y bond future) 25k DV01 per leg | +5.25 (S-G), model ~5bp tight | NZD 5Y: own NZGB May-31 4.138% vs pay 5Y IRS 3.923% at -21.55, +7.4 |
| 6 Mar 2022, Astor Ridge, Trade Radar | FRTR 40 vs BGB 41 EGB spread | realised daily vol 1.2bp (90d) to >2bp in a week, z 5.84 | response: overlay swap spreads / move to same-issuer liquid positions |

## Patterns across the log

- Entry/target/stop: typical reward-to-risk 2:1 to 3:1 (Rhodes ~2.5:1; BofA 2018 2.6:1; BofA 2017 1.9:1; Citi SSA switches ~2:1).
- Targets are set from a fair-value gap (JPM 30y regression, Citi 10y-on-30y regression), a historical range, or a catalyst (supply/QE/regulation), and abandoned when
  the move implies an implausible shift in fundamentals (JPM implied WAM inversion).
- Carry and slide are quoted per 1M/3M and are usually small versus the spread move (-1 to +4bp): the trade is a view on flows and regulation, not carry.
- A spread-narrower hedge is the Treasury curve (long-end narrowers vs a 50% matched-duration flattener); a front-end widener is hedged against bill supply and repo.
