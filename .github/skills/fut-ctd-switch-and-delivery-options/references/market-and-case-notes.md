# Market differences and dated cases

Companion to [SKILL.md](../SKILL.md). Numbers are as printed in the cited documents (prices in 32nds or decimals as stated); none is current market data.
Contract terms must be re-read from `fut_static` / `fut_basket`; this table is orientation only.

## 1. Which options exist where

| Market / contract | Delivery rule | Options the short holds | Notes |
|---|---|---|---|
| USD CBOT TU, 3Y, FV | Any business day of the month; last trade = last business day of the month | Switch, timing, wildcard, EOM (short window) | TU is a double-notional contract; FV is the only one with negative carry in Aug 2026 (early delivery); TU/FV/TY grids show little or sell-off-only switch option in 2025 |
| USD TY, TN, UXY | Last trade 7 business days before month-end | Switch, timing, wildcard, EOM (~7-day window) | UXY basket of 3: wildcard only; WIs can be CTD in TY |
| USD US, UB/WN (>= 25y) | same | Switch (two-sided in US), wildcard (largest in WN/UB: CF 0.43-0.83) | US keeps extending duration in sell-offs; WN anchors to the shortest-maturity bond; Ultra launch (2009) had 9 deliverables vs 22 for US and ~1/4 the option |
| EUR Eurex Schatz/Bobl/Bund/Buxl, OAT, BTP | Single delivery day (10th calendar day); LTD 2 exchange days before | Switch (and EOM-like window only to the single day); no timing, no wildcard | Notional 6% (OAT, BTP, Bund family), Buxl 4%; baskets can be tiny (Mar-03 Bund: 2 deliverables); squeezes more common (OI large vs supply, repo fails) |
| GBP ICE Long Gilt | Any business day (seller's choice); LTD 2nd business day before last business day | Switch, timing, EOM | Ex-dividend period bars delivery: a CTD can drop out mid-month and futures jump to the next CTD. Notional 7% in 2005 text; 4% in the canonical spec table: use `fut_static` |
| JPY JGB 10y | Single delivery day (20th); LTD 7th business day before | Switch only | Large basket (~26 bonds Mar-03); at low yields the shortest bond is CTD but several bonds share maturity, coupon and BPV, so the multi-factor option (7 sen) >> one-factor (< 1 sen); calendar driven by CTD slope, IRR vs OIS, securities-lending fee/CTD supply |
| CAD CGB 10y | Any business day; LTD 7th business day before last business day | Switch, timing | Notional 6% |
| AUD SFE 3y/10y | Cash-settled vs mean yield of 10 randomly chosen dealers | None (no physical delivery, no squeeze) | AUD bank-bill futures are physically settled in some designs: cheapest-to-deliver option over 85-95 day bills of eligible issuers (Henrard, OpenGamma, 2012) |
| CHF, SEK (designated bond), NZD, NOK | Not covered in the source material | Check `fut_static.settlement_type`, `is_designated` | Single designated deliverable (Nasdaq SGB) means no switch option; treat NZD/NOK as unavailable unless `fut_static` has a physical contract |

Process dates (CBOT, Burghardt 2005): first tender day 2 business days before the delivery month; Tender/Position Day (notice by 8pm CT);
Notice/Intention Day (issue named by 2pm); Delivery Day (by 1pm; 9am to the clearing bank). March 2004 example: first tender Thu 26 Feb, first delivery Mon 1 Mar, LTD Mon 22 Mar,
last tender Mon 29, last notice Tue 30, last delivery Wed 31. 2026 roll mechanics (Citi, Aug 2026): longs roll before the first day they can be noticed (31 Aug) and shorts' first intent day is
28 Aug; US and WN rolls 100% pro-rata, TU/FV/TY/UXY 20% FIFO / 80% pro-rata.

## 2. Dated cases (switch option)

- **CME teaching table (Dec-17 TY, 10 Oct 2017).** CTD 2.375% Aug-24 (CF 0.8072, NB -0.1185, IRR 1.42%); 2.25% Aug-27 (CF 0.7314, NB 14.48, IRR -31.73%): IRR falls monotonically with maturity (CME, Understanding Treasury Futures, 2017).
- **Crossovers, 5 Apr 2001, June bond (Burghardt 2005).** On the 7-5/8% 11/22's yield (5.64%): below 4.98% the 8-7/8% 8/17 is CTD; 4.98-6.13% the 7-5/8% 11/22; above 6.13% the 5-1/2% 8/28.
  Screen: last-delivery IRRs from -8.68% (5-3/8% 2/31) to +4.06% (CTD); CTD basis 18.09, carry 13.56, BNOC 4.53/32; only the 6-1/4% 5/30 and 5-3/8% 2/31 were special (term RP 4.43/4.45% vs 4.54% GC).
  Scenario grid (+/-60bp in 10bp steps, horizon 20 Jun 2001): unchanged -> 7-5/8% BNOC 1.5/32; rally -10..-40bp the 8-1/8% 5/21, -50bp the 8-3/4% 8/20, -60bp the 8-7/8% 2/19; sell-off +10/+20bp the 6-1/4% 8/23,
  +30/+40bp the 6% 2/26, +50/+60bp the 5-1/4% 2/29; projected basis 11.5/32 at -60bp, 24/32 at +60bp (straddle-like). Long CTD basis bought at 18.09 makes about -3/32 unchanged, +7/32 at -60bp, +19.5/32 at +60bp; a short makes at most ~+3/32.
- **EOM (Burghardt 2005, Exh 3.9).** 6-1/4% 8/23: BNOC 1.0, BPV 4.25/32; 7-1/4% 8/22 (CTD) BNOC 0, BPV 4.50; 8-3/4% 8/20 BNOC 1.5, BPV 4.70. Crossovers `+7.5bp = 1.5/(4.70-4.50)` and `-4bp = 1.0/(4.50-4.25)`.
  +10bp gains 0.5/32, -10bp gains 1.5/32 (= $46.88 per $100k). $100mm of the CTD basis ~ short 38 futures as yields rise (~$5,000/bp) and ~ long 51 as yields fall.
- **Buyback switch, Jan-Feb 2000 (Burghardt 2005).** The 6-3/8% 8/27 vs 9% 11/18 spread traded -13 to -7bp (8/27 CTD); at -17bp the 11/18 became CTD: 8/27 BNOC 7 -> 28/32 and 11/18 BNOC 50 -> 8/32 (13 Jan to 3 Feb). 22 different bonds were CTD at some point in Q1 2000;
  10s/30s went from ~0 to almost -40bp. Oct 2001 30y suspension: 6% 2/26 net basis 9/32 -> 50/32 as 10s/30s flattened.
- **Basket gap, 2015 (Citi, The long end basket case, 4 Feb 2015).** CME excluded the 5.375% Feb-31 ($16bn float); CTD jumped from 6.25% May-30 (USH5, DV01 $166, price 149-13) to 4.5% Feb-36 (USM5, DV01 $252, price 167-17); equal-DV01 roll needs 34.1% fewer Jun contracts; 2/36 vs 5/30 ASW moved ~12bp;
  May-30 3.9 sd cheap to an ASW-on-10s30s regression (R^2 0.65); invoice spread widened 10bp.
- **Long May-37 basis as rally option (Citi, Summer lull, 17 Jul 2015).** Long $100mm 5% May-37 vs short 911 USZ5; net basis 4.2 ticks (GC 27bp); gamma $420 for ~$130K vs the same gamma via a 1m25y swaption for $187K (~1.4x); risk/reward at +/-40: swaption 1.3, basis 1.56. If forward yields fall ~30bp the Feb-36s are likely CTD again.
- **USD 2025 grids (BofA, Futures Basis Report, 7 Aug 2025).** USU5 CTD 4.75% 11/43 at 69.6% (4.75% 2/41 20.6%); scenario CTD with zero twist: 2/41 in rallies (-150..-20), 11/43 at 0, 11/44 at +30..+50, 2/48 at +60..+80, 8/49 at +90, 8/50 at +100..+150; net basis of the current CTD 77.5 (-150), 45.0 (-100), 17.2 (-50), 2.6 (-20), 0 (-10..+20), 6.1 (+50), 40.9 (+90), 57.8 (+100), 146.5 (+150): strongly two-sided.
  FVU5 CTD 100% (no switch in grid); TYU5 CTD 99.9% (rally -> 3/32; sell-off >= +100 another 5/32 or 5/33; NB 4.7 at -150, 6.4 at +150); TYZ5 88.1% with 2.75% 8/32 at 11.7%; TUZ5 CTD 92.1%. Header "Repo Sensitivity" = model price change for +100bp repo.
- **USZ6 trade (J.P. Morgan, Born(e) in the US(A), 31 Jul 2026).** CTDs priced to last delivery day; USZ6 CTD 4 7/8% Aug-45 CF 0.8753, BNOC 1.4, BPV/F 1345; five near-CTDs within 0.5/32; basket BPV/F 1271 to 2039 (1 1/4% May-50). WNZ6 CTD 4% Nov-52 CF 0.7393, BNOC 1.7, BPV/F 1689.
  Trade: buy $100mn 4.625% Nov-44 vs sell 851 USZ6 (notional/100k x CF 0.851), gross 16/32, term repo 3.87% to 31 Dec 2026, net ~2/32. DOV ~17/32 USZ6 and ~6/32 WNZ6 vs net basis ~15/32 USZ6 on 2 Oct 2026 (J.P. Morgan, Near, far, wherever yields are): long basis at ~15/32 is not attractive when funding may tighten.
- **Roll outlook (J.P. Morgan, 12 Aug 2026, front/back).** US BNOC 2.3/4.4, switch option 4.6/14.8, gross 7.8/18.7; WN BNOC 2.0/1.6, switch 0.8/3.8; TY BNOC 0.0/0.4, switch 0.4/4.7; UXY switch 0.0/0.1. US front ~2+/32 vs option ~4+/32, back ~4+/32 vs ~15/32 (underpriced -> calendar wider/bullish); WN front 2/32 vs 1/32 (overpriced).
  Carry to optimal delivery (ticks): TU 1.6, FV -0.3 (early), TY 2.3, UXY 2.2, US 5.5, WN 3.8.
- **CTD by parallel shift (Barclays, The urgency question, 2 Oct 2026, US).** -40..-10 4.75% Feb45; 0/+10 2.5% Feb45; +20 2.25% Aug49; +30..+50 1.625% Nov50; +60..+100 1.375% Aug50: anchored to the Aug50 beyond +50bp, and no further extension once the long end is near 6%.
- **Morgan Stanley (27 Aug 2026).** 106 USZ6 put at 51/64; long CF-weighted 5% May-45 basis, gross 17.02 ticks, net 5.52 at 3.95% term repo; futures-option skew on the CTD ~ in line with 3m20y swaption skew, so sell-off convexity is not priced.
- **Eurex (J.P. Morgan, 1 Oct 2026).** 10Y OAT CTD FRTR 3.7% Nov36 62%, CF 0.831189; DOV ~10c, OA net basis ~0; `DOV(c) = 14.50 x (10Y France yield %) - 56.14` (R^2 90%, 1M) - a local fit, do not extrapolate; scenario CTD/DOV(c): -50bp Nov35/10, -20bp Nov36/15 (peak), 0 Nov36/10, +50bp Nov36/3.
  10Y BTP CTD 3.65% Aug35 58%, CF 0.848511; 3.8% Jul36 36% needs +24.2bp or 1.2bp steepening (sd 1.2bp), +8% DV01; DOV ~7c. Schatz/Bobl/Bund switch risk minimal.
- **Switch and spur, Oct 2026 (J.P. Morgan).** USZ6 ~20bp sell-off adds ~4/32 DOV; DOV falls above ~6% and is ~0 after a >100bp rally. UB (WN) Dec CTD 4% Nov52 over -20..+20bp; 4 3/4% Nov53 in rallies of 40bp+, 2 1/4% Feb52 in sell-offs of 40bp+; twists shift the zone ~20bp.
- **Ultra launch (Credit Suisse, 28 Sep 2009).** ULH0 delivery option ~2.5 ticks, ~1/4 of USH0's, with 9 deliverables (~62% of outstanding of USH0's 22 eligible issues). DV01/convexity: USH0 1,331/112; ULH0 2,079/442 (DV01 +56% from low CFs). DV01 change for +/-100bp: ULH0 -18%/+24% vs USH0 -6%/+12%.
- **MS PC scenario (Aug 2026).** ~50bp parallel sell-off moves USZ6 CF-adjusted forward DV01 from ~12.3 to ~18.

## 3. Wildcard and timing cases
- **Burghardt wild card.** Long $100mm 8-3/4% 8/20 (CTD, CF 1.3093) vs short 1,309 futures leaves a $30.9mm tail (CF > 1 so the after-hours move that pays is a fall); futures 104-10, basis 6/32; giving up the basis costs $187,500 (6/32 x $31.25 x 1,000);
  invoice ex-AI `1.3093 x 104.3125 = 136.576`; the tail must be bought 0.6068 pt below invoice, so a total aftermarket fall of 25.4/32 is needed (6/32 / 0.3093 = 19.4/32 plus the 6/32).
  Tuckman & Serrat version: short 8,338 futures per $1bn; if the CTD rallies after settlement, sell $166.2mm at the higher price and deliver $833.8mm at the stale settlement.
- **Wildcard value history (J.P. Morgan).** 8 May 2018: ~0.75 tick TUM8, 0.5-1 tick FVM8; TUM8 gross basis -1 to -2 ticks (1.375% Mar-20 CTD) so early delivery optimal unless GB > ~-0.75 tick; FVM8 basis ~0 with option ~1/2 tick -> late delivery stays optimal for CTD basis down to -3.5 ticks.
  Late 2019: ~3 ticks of WN net basis, 0.5-1.5 ticks elsewhere (TN most often, then FV, TY); elevated vol adds 50-100%; WNH0 CF 0.6141; majority of WN deliveries mid-month since 2016; option value distorted implied/term repo by ~10-30bp in TYZ9, UXYZ9, USZ9, and WN implied repo sat 50-100bp below CTD term repo into delivery.
  Mar-Apr 2020: WN net basis underpriced by ~4-8 ticks; WN short leg embeds ~4 ticks of wildcard normally, >10 ticks if recent post-close vol persists.
- **Timing evidence.** Mar 2001 (curve inverted 0-2y, upward beyond): 2y delivered 14 Mar to 3 Apr; 5y, 10y and bond all on the last day. 2026: >90% of TY/UXY/US/WN June deliveries in the last week, late delivery cheaper for all but FV (Aug 2026); Feb 2023: high financing made early delivery optimal in all six contracts.
- **Negative net basis in TU, Nov 2019 (QFSE discussion).** TUH0 IRR ~25bp above term repo to March, NB -2 to -3 ticks, because of year-end balance-sheet cost; return on capital with a 6% leverage ratio ($60mm per $1bn): profit 2-3 ticks (~$200K per $1bn) = 0.33%.
  Vendor monitor (~Aug/Sep 2023): in every row IRR > repo paired with negative NB (e.g. TWE: IRR 8.593 vs repo 5.370, NB -4.353).

## 4. Squeeze and fail cases (Burghardt 2005)
- **June 2005 10y.** CTD 4-7/8% 2/12 had a net basis a full point below the 2nd CTD 4-3/8% 8/12; 10y OI 2.1mm (+50% y/y); the CTD BNOC averaged -2/32 in early May 2005; overnight repo on the CTD traded at -15% in late May. Fair value at `P(fail) = 0.10` with a 1-pt gap: `-3.2/32`.
- **March 2001 Bobl.** CTD DBR 6.5% 10/05 (old, illiquid, small float) with a large BNOC gap to the 2nd CTD DBR 6% 1/06; OI peaked at EUR 57bn two weeks before expiry; CTD BNOC hit -70 cents and the Mar-Jun calendar widened from ~0 to 70 cents as shorts rolled.
- **Specials flip short-basis P&L.** Reverse repo for scarce collateral is typically 10-25bp below GC and has no floor: May-Jun 2000 a short 5y 5/05 basis was -$14,276 vs +$14,211 on the 11/04, with nearly $11,000 from the lower reverse-repo rate.
- **Cap on squeeze profit.** Tuckman & Serrat: TYU1 at LTD (21 Sep 2021, F 133.85938) cost of delivery CTD 2.875% 5/28 0.00524, next 0.91225, longest 1.125% 2/31 10.54663; squeeze profit is capped by the cost of delivering near substitutes (~100c over the CTD).

## 5. CTD richness and basket changes in cash
Bonds richen when they become CTD and cheapen when they fall out of the basket; CTDs often trade at negative OAS to a fitted Treasury curve (liquidity premium; Treasury Borrowing Advisory Committee, 2024). Estimated TY CTD premium vs a fitted curve 0.6-1.2bp (median vs mean) and it
tends to start rich and cheapen through the roll (Citi, Fixing the plumbing, 30 Sep 2019). Regression-weighted flies of neighbouring bonds and regressions of the CTD ASW on curve slope separate idiosyncratic from common factors; the contract's own positioning
can be a CTD-sector RV leg (WN shorts vs 25s/30s, R^2 84%; J.P. Morgan, Canary in a coal mine, 25 Feb 2020).
