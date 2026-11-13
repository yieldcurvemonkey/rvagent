# Cases for the adversarial review

Each case is a failure or near-failure pattern with the numbers a reviewer can reuse as a template. Parent skill:
[rv-devils-advocate](../SKILL.md).

## 1. Right thesis, forced exit: March 2020 Treasury basis (financing lens)
(Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022, Ch.11.) Long $1bn of the June 2020 10y note-futures CTD
basis, opened 6 Mar 2020 at net basis -8.33 ticks; interest on the repo financing 1.10%, 116 days to delivery.
- Hedge ratio = 10,000 x CF / (1 + repo x days/360) = 10,000 x 0.8006 / (1 + 0.0110 x 116/360) = 7,978 contracts. Recompute this independently; a wrong day count here is a hidden directional position.
- Target if net basis goes to 0: (8/32)% x $1bn = $2.5mm.
- 9 Mar: net basis -18.48; daily P&L (change in net basis x $1bn) -$3,172,148; exchange margin 1,275 -> 1,375 per contract, call -$797,772; cumulative cash out -$14.1mm (including the initial margin of a bit over $10mm).
- 11 Mar: margin 1,600, call -$1,794,988. 12 Mar: net basis -0.47, cumulative P&L +$2,455,330.
- Lesson for the review: the loss limit is hit before convergence. A $2.5mm target with a $4mm one-day cash need is a funding-survival problem, not a view problem. Overnight (not term) financing adds rate risk both ways and the risk that the prime broker cuts lending or raises haircuts; the 99th-percentile repo minus SOFR spread reached 174bp on 16 Mar 2020.
- Context (CFTC OCE 2024-007, CFTC MRAC Dec 2024): in this data Select Funds' futures shorts shrank in Q1 2020 and regulators concluded basis unwinds amplified but did not cause the stress; sale estimates range $35-173bn. Do not over-attribute.

## 2. Haircut risk: MF Global repo-to-maturity (Tuckman & Serrat, 2022, Ch.10)
Buy a European sovereign bond, repo it to near maturity (no roll risk), earn the carry. Hidden risk: the clearing counterparty can change haircuts at any time.
| Date | Position | Margin | Margin % of position |
|---|---|---|---|
| 6 Jun 2011 | at least $5.8bn | $170mm | 2.9% |
| 20 Jun 2011 | $11.5bn | $550mm | 4.8% |
| 30 Sep 2011 | $6.3bn | $417mm | 6.6% |
| 27 Oct 2011 | $6.3bn | $665mm | 10.6% |
Haircuts on IE/PT rose from 3% to 80% (Jul 2011); the limit ($4.75bn) had been set so a 15% average haircut could be met from cash; Chapter 11 at end-October 2011; liquidation loss over $400mm. Review test: cash call = notional x (haircut_stress - haircut_now); with $11.5bn and 3% -> 15% that is $1.38bn, and the actual move was far larger.

## 3. Squeeze on a crowded short: 1986 old long bond (Burghardt et al., The Treasury Bond Basis, 2005, Ch.6)
- 9-1/4% 2/16 traded 25-40bp through a cheap CTD in April; the spread passed 100bp in May; basis widened about 6 points ($60,000 per $1mm). Causes: an obvious crowded short in the old long bond; Japanese holders would not lend, reverse repo went to about 0% and the issue became unborrowable; funds sold older CTDs at historical cost.
- Warning signs listed: falling RP special rate, large short sales in the issue, yield-spread change versus similar issues. Control: borrow-and-buy-back-able issue; check overnight and term reverse RP, issue size and unstripped amount; a stop-loss, because a squeezed basis short has no theoretical maximum loss.
- Specials have no floor: the June 2005 10y CTD traded in overnight repo at -15%.

## 4. Short-leg financing arithmetic: 2000 repo special (Burghardt et al., 2005, Ch.6)
May-June 2000: the new 5y 6-3/4% 5/05 averaged a 5.48% reverse repo vs 6% for the 11/04. Short $10mm of the 5/05 basis: coupon paid $64,198, reverse repo earned $53,360, cash/futures -$3,438, total -$14,276; the same short in the 11/04 made +$14,211. Check: 64,198 - 53,360 = 10,838 of the loss was financing (lower reverse repo). Test: price the short leg at its own-issue repo.

## 5. Stress-testing a short basis: December 2001 (Burghardt et al., 2005, Ch.6)
As of 20 Sep 2001: CTD 6-1/2% 2/10, basis 46.9, carry 36.8, BNoC 10.1 (32nds). A +60bp selloff with 7s10s steepening 1.5 sd gives a projected net basis of 17/32, judged low probability "because the curve typically steepens in a rally". Template: choose one yield-level shock and one yield-spread shock that switches the CTD, then report the net-basis outcome and its probability class. Backtest of the short 10y CTD basis (Jun 1998 - Jun 2004, 25 contracts, sold 3 months before expiry): BNoC fell in 23 of 25; average entry 6.7/32, average kept 4.9/32; worst cases Dec-03 (BNoC +13.4 to -0.5) and Sep-00 (11.0 to 0.4). High win rate, fat left tail: not evidence of richness.

## 6. Recompute template: long-basis P&L (Burghardt et al., 2005, Ch.1-5)
Buy $10mm 7-1/2% 11/16 at 120-20, sell 115 June futures at 103-30, 5-19 Apr 2001, repo 4.5%. Net basis 40.4 -> 39.7 (32nds). Bond -$396,875; futures +$395,312.50; coupon +$29,005.52; repo -$21,624.23; total +$5,818.80 = basis -$1,562.50 + carry +$7,381.29. Use as an arithmetic check that the P&L explain ties to the legs.

## 7. Regime shift of the fair value: fly (Lehman, LMR Quarterly, Oct 2003)
2s5s10s 34/66 fly at 0bp at base; after a faster-recovery shift (2y/5y/10y 4.326/4.729/4.865%) the fly is 4.8bp. An observed 4bp fly looks 5s-cheap against the old fair value of 0 but is about 1bp rich against the new. Long 5s lost about 15bp over five months in 2001. Selling 5s against a 50/50 2s10s on 23 May 2003 presumed very slow recovery: state that assumption in the ticket.

## 8. Crowded unwinds
- Aug 2007 quant meltdown: crowded unwind pushed correlations from 0.1-0.3 to 0.7-0.95 (Brenndoerfer, Dec 2025); published factors carry liquidation-spiral risk (Tulchinsky et al., Finding Alphas, 2015).
- April 2025 swap spreads: in the week to about 11 Apr 2025 swap spreads moved 4.5-7bp more negative on record volume; 10y at least $31bn over 600 trades vs a typical 250 a week, VWAP 7bp more negative; 30y at least $10bn over 425 trades vs 135, VWAP 4.5bp more negative, with a -100bp print on 8 Apr (Clarus Financial Technology, Swapalypse Now, Apr 2025). Hedge-fund swap-trade residual fell 11% in the turbulence, funds "caught wrong-footed" (BIS Quarterly Review, Dec 2025, Box B). "A couple of large players rumored to have been caught on the wrong side" while money markets were "not significant" (Conks, Money Market Update, Apr 2025). Lesson: positioning, not macro, was the driver; the review should have a crowding gauge reading before entry.
- SCP (London Whale), index/constituent: book grew $76.5bn (2007) to $365bn (2011); gross notional rose $51bn -> $157.1bn by Mar 2012; IG.9 position over 10 days of ADV; losses $718m Q1 2012, $5.8bn cumulative through Jun 2012; cutting RWA by $25bn costs $400-590m (Tuckman & Serrat, 2022, Ch.14, targeted read). Exit cost scales with size/ADV.

## 9. Honest-RV outcome (Huggins & Schaller, 2024, Ch.19)
JPY vega sector screen: only 7s10s20s (R^2 ~0.84, ~+0.5bp pick-up) and 5s10s20s (R^2 ~0.55, ~+1.3bp) had a positive pick-up; all others about -3 to -15bp. A single outlier on 1 Mar 2010 would have given an excellent trade; the authors read that as a survivorship warning, not a signal. Realised vs implied (JPY 5y): current implied 19bp vs recent realised 16bp; implied above realised at every tenor (2y 7/16, 5y 16/19, 10y 27/34, realised/implied). The expected answer of a good review is often "no".

## 10. Carry decomposition recompute (Tuckman & Serrat, 2022, Ch.3)
7.625% of 11/15/22, 13 Nov 2020 - 14 May 2021, realised-forwards scenario: start price 114.87654 at spread -1.16bp; carry-roll-down -3.76099 (-3.2739%); rates +0.18292; spread +0.09843 (spread moved to -7.27bp: the bond richened); cash carry +3.81250; total +0.33286 (0.2898%). Check the four parts sum to the gross return before quoting carry in a ticket.

## 11. Binary-event and consensus examples
- Brent $70 to $90 in one week (from about $60 at the start of the year): a 1y1y at 60-100bp higher in a week in one market and a 70-85bp higher euro-area 2026 HICP path (JWS Macro, #3 Iran & Front End Rates, Mar 2026). Degrossing: "sharp increases in volatility will often see DEGROSSING of exposures regardless of their immediate performance".
- "The most dangerous trade in macro is assuming the thing that has happened for three years cannot happen for a fourth" (JWS Macro, #8, Aug 2026).
- Treasury buyback doubling (19 Aug 2026): yields fell within minutes and round-tripped by the next afternoon; off-cycle, doubled, post-high announcements read as price management (Druckenmiller, WSJ, Aug 2026).
