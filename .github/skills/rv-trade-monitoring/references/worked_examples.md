# Worked examples for trade monitoring

Numbers as printed in the cited notes. Where a source's arithmetic does not reproduce, that is flagged. Use these to
calibrate the monitor output format and the rules in [SKILL.md](../SKILL.md); do not reuse levels as current market data.

## A. Delta-hedged convexity flattener (USD 15y5y/20y10y, Citi series)

- Structure: DV01-neutral forward flattener, long 15y5y and short 20y10y, with the long-end leg delta-hedged each time
  rates move about 20bp. Opened early May 2019 at $50K DV01, spread -11.8bp.
- 16 Oct 2019: 15y5y notional $149.5mn, longer leg $81.97mn. Mark-to-market +$105K despite about 2bp of steepening.
  Beta 1.025 applied: longer leg raised to about $84mn (81.97 x 1.025 = 84.02). (Citi, Reweighting delta-hedged
  15y5y/20y10y flatteners, 16 Oct 2019.) The note calls the longer leg "25y10y" once; it is 20y10y (source flag).
- Monitor screen, 5 Dec 2019 (USD 15y5y/20y10y): curve -12.54bp, 1y z -0.91, 1y carry -2.09bp, daily breakeven 3.33bp,
  BE/RV 0.80. GBP on the same date: curve -8.27bp, 1y z 0.70, carry -0.24bp, BE 1.13bp, BE/RV 0.26, judged better value.
  (Citi, Taking profits on delta-hedged 15y5y/20y10y flatteners, 5 Dec 2019.)
- Exit: with the curve at -12.5bp, P&L was about $187K at mid; booked +$155K net of costs. Exit reason was carry deterioration and
  BE/RV rising toward 1, even though the curve thesis was intact. (Citi, 5 Dec 2019.)
- Implied daily RV from the same screen: BE 3.33bp / 0.80 = about 4.2bp per day.
- Watch for P&L with no curve move: realised vol delivered about $187K while the curve steepened about 2bp (Citi, 5 Dec 2019).
- Closed flatteners: USD 15y5y/20y10y May to Dec 2019, -12 to -13bp, +$155K. GBP 15y10y/25y10y opened 17 Jan 2020 at -11bp,
  closed 26 Mar 2020 at -19bp, +$542K (Citi, Eat, pay, spend, 27 Mar 2020). A later note splits a GBP 15y10y/25y10y exit of
  +$445K net into about $115K curve and $330K convexity; in a vol spike about three quarters of P&L came from convexity
  (Citi, Taking profits on GBP 15y10y/25y10y flatteners, 26 Mar 2020).

## B. Skew package: vega, gamma and vomma drift (USD 3m2y, Rhodes, 8 Oct 2025)

- Package: long $100mm 3m2y payer 50bp OTM, short $100mm receiver 50bp OTM, long $9.71mm ATM straddle, delta-hedged with the
  3m2y swap. Exposure is payer vol minus receiver vol.
- Vega-neutral: `V_payer - V_receiver + V_ATM = 0` gives the straddle size.
- Swap hedge: `N_swap = -(N_p Delta_p + N_r Delta_r + N_str Delta_ATM) / DV01_swap`.
- Second-order drift: `dP ~ Delta dS + 1/2 Gamma dS^2 + Vega dsigma + 1/2 Vomma dsigma^2 + Vanna dS dsigma`.
- Worked drift: net vega 0, net vomma 0.9. A +5 abpvs vol move gives second-order P&L `1/2 x 0.9 x 5^2 = +11.25`, and net
  vega becomes about `0.9 x 5 = +4.5`. Trim the ATM straddle to re-flatten.
- Rebalance triggers (source): resize when |net vega drift| > 5 abpvs or net rate move > 5bp; re-strike a wing that drifts
  more than 5bp from target; after a +/-5bp shift, re-centre the wings and refresh the ATM hedge.
- Scenarios at entry (source): parallel vol +10 gives +$3,240; payer +10 with receiver -10 gives +$37,840; payer -10 with
  receiver +10 gives -$31,360. Stop: skew breaks prior lows, cuts deepen, liquidity deteriorates. Target skew -23 to 0 abpvs.

## C. Stop breach and holding the loser (Citi, Global Macro Trade Ideas Radar, 13 Aug 2026)

- 1y forward 5s30s swap steepener, 50k DV01 at 75.5bp; target a 45bp move; stop 30bp of flattening. Current 42.3bp,
  -$1,662k. The curve had flattened about 33bp, beyond the stop. The note records it as a breach, not a reason to re-size.
- Lesson from the same publication: "we underestimated the extent of short positioning"; "the trade took longer than
  expected to develop". Both are process-review entries (see SKILL.md, journal).

## D. Stop placement, targets and re-targeting

- 2:1 reward-to-risk on a short convexity hedge (Citi, Turning Green from Blue on short convexity, 6 Jun 2017): target
  +$450K, stop -$225K. Closed 8 Aug 2017 at 2.65bp with about +$476K (Citi, Target achieved on short Greens convexity,
  8 Aug 2017; the 4 Oct 2019 appendix gives the same close). The note says the trade was closed early because it was still
  rich but the dislocation had normalised, with hawkish-Fed event risk into Jackson Hole.
- Re-target as the trade nears target: ING moved an EUR 2s7s10s target from 91 to 101bp and tightened the stop from 61
  to 86bp (ING, EUR crisis trades, 3 Mar 2020).
- Stop tightened after the trade moved your way: BNP set the stop at -4bp, just above the -5bp entry, on a pay EUR 5s10s30s
  fly (BNP, EUR curve convexity: lessons from history, 25 May 2021). Carry was +0.8bp per month at that point.
- Stop widened only with a written rationale: a 3m1y payer vs 1x1 1y1y payer vol spread went from -10 to -12bpv because
  the 3m balance of risk was still elevated (Citi EUR, Morning Call, 12 Aug 2026).
- A stop and target pair that fails the screen: a 1y30y vs 3y30y ATMF straddle at 3.6bp to 1.0bp, P&L -$124k, target
  $250k, stop -$175k (Citi, OAT of the blue, 2 Oct 2026). Check the risk-to-reward before accepting it.
- Overlay (illustrative, not from sources): spread mean 0, 2 stationary sd = 10bp, entry -6bp. Halfway target = -3bp,
  stop = -10bp, so reward 3bp vs risk 4bp: ratio 0.75, below the 1.5:1 screen. Wait for a better entry, or reject.

## E. Mean-reverting spread exits: half-life and the bands

- BNP history (EUR 5s10s30s fly, 25 May 2021): seven rich-fly episodes since 2013 (residual below -5bp for more than a week).
  Normalisation came with a flatter 10s30s six times out of seven; overshoot to +5bp or more six times out of seven; average
  3.1 months to fair value and 2.7 months from fair value to overshoot. Mechanical exit at zero residual is wrong.
- JPM (Impossible to walk in this muck, 6 Mar 2020): took profit on a 30y/10y x 10y flattener at +21.3bp (spread -39bp,
  slide -4bp per year). Scorecard in the same note: 47 closed trades, 34 winners, 72% hit rate over 12 months.
- Leung-Li stop experiment (model): L = 0.4834 is two stationary sd below the mean; printed b_L* = 0.5570 (take profit)
  and d_L* = 0.4978 (entry). Path (a) enters about day 30 and exits near b_L* about day 85; path (b) enters about day 8 and
  is stopped shortly after. Source flags the printed cost parameter; re-check before reuse.

## F. Hedge drift and bleed

- Futures strip hedge without rebalancing, Treasury note (Huggins and Schaller, SOFR Futures and Options, 2022): total lots
  -717 on 2 Jan 2020, -632 on 18 Mar 2020, -531 on 17 Jun 2020. On 18 Mar 2020 the futures lost 1,959,518 against the note's
  gain of 1,631,250: net loss 328,268, about 20% of the move. The note's ASW widened; the Treasury-to-SOFR basis did not
  stay stable enough for the hedge to hold.
- Risk bleed (Darbyshire, 2022, example 9.10): a pay 11.5y swap hedged 25% in 10y and 75% in 12y under log-linear discount
  factors, untouched for 1.5 years, then re-risked with strips (8y -12.50, 9y -12.50, 10y +43.75, 12y -18.75).
- Date mismatch (Huggins and Schaller, SOFR, 2022, ch.7): a matched-date SR3 hedge of USD 50m ended within USD 413.45 of
  target; a mismatched 89-day deposit hedged with a 91-day future over-hedged. Closing the hedge at the end of the lending
  period was better than holding it past the period.
- Hedge ratio of about 1.18 unwound for +$70.5k (Citi, Take off the hedge on short Greens convexity, 13 Jul 2017): the view on
  gamma changed, so the vol hedge came off. Note that two Greens notes describe the two hedge legs with different contract
  months and prices; verify before reusing.

## G. Repo and special monitor (Burghardt et al., 2005, worked examples)

- May to June 2000: a new 5y 6-3/4% (5/05) went special, averaging a 5.48% reverse repo versus 6% for the 11/04 issue.
  Short $10mm 11/04 basis: total +$14,211. Short $10mm 5/05 basis: coupon paid $64,198, reverse RP earned $53,360,
  cash/futures -$3,438, total -$14,276. About $11,000 of the loss came from the lower reverse RP rate.
- 1986 squeeze: a crowded short of the old long bond; reverse RP near 0% and the issue unborrowable; the basis widened
  about 6 points, $60,000 per $1mm.
- March 2020 (CFTC MRAC, Dec 2024): Treasury cash-futures basis selling by leveraged investors estimated at $35bn to $173bn,
  with studies assuming about 20x leverage. About 2.8% of Treasury futures go to delivery, so the basis trade is rolled
  rather than held.

## H. Daily P&L explain (Tuckman and Serrat, 2022, worked attribution, realised-forward scenario)

Bond 7.625s of 15 Nov 2022, 13 Nov 2020 to 14 May 2021, financing ignored. Start price 114.87654 at spread -1.16bp.

| component | value (price points) | how computed |
|---|---|---|
| carry-roll-down | -3.76099 | reprice on realised forwards, spread fixed at -1.16bp |
| rates | +0.18292 | reprice on the actual end-date curve, spread still fixed |
| spread | +0.09843 | reprice at the actual end-date spread (-7.27bp) |
| cash carry | +3.81250 | 15 May coupon |
| total | +0.33286 | sum of the four; check passes |

The identity check: cash carry plus carry-roll-down equals (6m short rate + spread) over six months (Tuckman and Serrat, 2022).

## I. Exits that the source treats as wrong

- Scale-down rather than exit: a short 3m10y straddle book was halved from $100mn to $50mn at 59 normals, rich by about 3
  normals (Citi, US Rates Vol Lab: Gamma and Vega RV, 14 Jan 2019).
- Exit at the peak mark is not realisable when costs blow out: a long-end forward fly peaked in March 2020, but the
  executable exit came on 15 Jun 2020 at a 10bp offer with costs back to about 3bp, P&L $360k (Citi, Taking profits on long
  end butterfly trade, 15 Jun 2020).
- Holding a stopped loser for a better outlook without re-underwriting: the source's rule is "look for a better re-entry"
  after a stop whose bearish view is unchanged (Citi, Global Commodities: Taking Profit on Sugar Trade and Closing Coffee Trade, 19 Aug 2026; a non-G10 example).
