# Worked examples: repo, specialness, implied repo, funding and turns

Companion to [SKILL.md](../SKILL.md). Every number is either re-computed with [scripts/repo_funding_math.py](../scripts/repo_funding_math.py) or copied from the cited source. Items marked **illustrative** are constructed for teaching and are not market data.

## A. Repo arithmetic (act/360)

1. **Repurchase amount.** $109,898,438 borrowed for 44 days at 0.015% repays $109,900,452 (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022, Ch.10). Check: 109,898,438 x (1 + 0.00015 x 44/360) = 109,900,452.8. Script: `repurchase_amount`.
2. **Haircut split.** Same $109,898,438 of collateral at a 3% haircut: cash $106,601,485, margin $3,296,953 (Tuckman & Serrat, 2022, Ch.10). Script: `haircut_split`.
3. **Repo rate from prices.** Invoice $101,000,000 repurchased at $101,000,280.56 next day is 0.1% (Huggins & Schaller, SOFR Futures and Options, 2022, Introduction). Script: `repo_rate_pct`.
4. **Repo interest.** $100 dirty, 1% haircut, 2% repo, 30 days: 99 x 2% x 30/360 = **$0.165**. The BofA-style primer prints $0.166 (BofA, US Treasury repo primer, Jul 2025); the arithmetic gives 0.165. Use the formula, not the printed figure. Script: `repo_interest`.
5. **Compounded SOFR index.** USD 1mm from 15 Sep 2021 to 15 Dec 2021 earns $82.78 (Huggins & Schaller, 2022, Ch.3), with index levels 1.04227169 and 1.04235797. Script: `sofr_index_interest`.

## B. Haircuts and funding stress

1. **Median tri-party haircuts** (Tuckman & Serrat, 2022, Ch.10): UST and agency 2%; agency CMO 4%; IG corporates and money-market 5%; ABS IG 7%; equities, HY and munis 8%.
2. **Fed haircuts, Oct 2023** (Huggins & Schaller, 2024, Ch.18): bills <10Y 1.0; notes <10Y 2.0; notes 10-20Y 2.9; notes 20-30Y 2.9; STRIPS 3.8 to 9.9 by tenor.
3. **MF Global, 2011** (Tuckman & Serrat, 2022, Ch.10). Position peaked at $11.5bn. Irish and Portuguese haircuts went 3% to 80% in July 2011. Margin path: $6.3bn position at $417mm margin (6.6%) on 30 Sep; $6.3bn at $665mm (10.6%) on 27 Oct. Chapter 11 followed. Lesson: a haircut can rise to a level that makes the position unfundable.
4. **Repo tail, 2020.** The 99th-percentile repo minus SOFR was 10-11bp in Feb 2020, 20-50bp on several March days, and 174bp on 16 Mar 2020 (Tuckman & Serrat, 2022, Ch.11). Use these as a stress ceiling for funding-availability scenarios.
5. **Basis trade margin, Mar 2020** (Tuckman & Serrat, 2022, Ch.11). A $1bn long basis position (short about 7,978 tailed contracts) lost about $3.17mm on 9 Mar, with a $0.80mm margin call; margin rose 1,275 to 1,375 per contract, then to 1,600 by 11 Mar. Net P&L turned positive, +$2.46mm, by 12 Mar. The cash calls arrived within days, before the position turned profitable.
6. **Leverage on a basis trade** (Tuckman & Serrat, 2022, Ch.11): at 20:1, $50mm earning 2.5% over 141 days is about 6.5% annualised; at 40:1, about 13%. Repo haircut near 2%, but prime brokers can ask for more.

## C. Specialness

1. **Drag on a short** (illustrative): GC 5%, 5y special 3%, short $100mm bleeds $2mm a year. A steepener with neutral carry can lose money while correct on the curve (Q&A note on 2s5s and repo specialness; undated, use as illustration). Script: `specialness_drag`.
2. **Auction-cycle specialness, 10y OTR** (Tuckman & Serrat, 2022, Ch.10; averages over 51 notes, Nov 2008 to Jul 2021): peak 156bp the day before the first reopening (2-sd band 116-196bp); 85bp 13 days before; 48bp before the second reopening; below 20bp before the next new issue.
3. **Overnight specials, 27 May 2021** (Tuckman & Serrat, 2022, Ch.10), bp by issue age on 2y, 3y, 5y, 7y, 10y, 20y, 30y: on-the-run 5, 1, 13, 9, 3, 2, 4; old issue 2, 2, 2, 1, 11, 2, 12; double-old 2, 10, 6, 8, 10, 2, 3; triple-old 2, 12, 2, 3, 3, 2, 2. Specialness sits in different issues at different tenors, so model it per issue.
4. **Term specials horizon** (Düring, Fixed Income Trading and Risk Management, 2021, Ch.14): for example, 100bp special overnight but 10bp special for one month. Price the term rate, not the overnight.
5. **Expected specialness by maturity, German curve** (Huggins & Schaller, 2024, Ch.12; chart reading, approximate, ABN Amro note of Apr 2002): about 0.1bp at 1Y, 0.7bp at 3-4Y, about 3.0bp at 5Y (Bobl deliverable), about 4.3bp at 9Y, about 5.9bp at 10Y (Bund deliverable and benchmark).
6. **10Y Bund ESTR-ASW fair value** (Huggins & Schaller, 2024, Ch.12): -16bp (unsecured-secured basis at g = 10%), +15bp (adjusted 10Y German CDS), -6bp (average specialness), giving -7bp.

## D. Implied repo and synthetic term funding

1. **IRR identity.** Implied repo = CTD term repo - BNOC / dirty x 360/n. Example (illustrative): dirty 100, term repo 3.50%, BNOC 0.25 points, 90 days gives 2.50% (script: `implied_repo_pct`). Round trip: BNOC 0.25 recovers exactly (script: `bnoc_from_irr`).
2. **Dollar roll implied financing** (Tuckman & Serrat, 2022, Ch.15.10): UMBS 30y 2.5% Jan/Feb 2022 with repo at 10bp. Net roll worth $622 on $1mm, implied financing -58.4bp, specialness about 68bp relative to 10bp repo. Implied rates overstate value because of the delivery option and prepayment assumptions.
3. **Option-adjusted IRR** (JPM, Special delivery, Dec 2019): OA IRR = IRR + option value / dirty x 360/n; compare OA IRR with the CTD repo. Options distorted implied-minus-term repo by 10-30bp in the 10y, Ultra 10y and bond contracts in late 2019.
4. **Synthetic term repo.** Pay 1-year OIS fixed at 0.45% and fund overnight at GC; GC averages 8bp below EFFR, so the cost is about 0.45% + (-0.08%) = **0.37%** (Credit Suisse, Basis Points, Feb 2010). Script: `synthetic_term_cost_pct`.
5. **Futures sign.** The 1M SOFR future at 96.00 and the fed funds future at 96.15 means SOFR 4.00 and FF 3.85, so SOFR-FF realised +15bp and the futures basis reads -15bp (Conks, SOFR/FF primer, Jun 2026). Script: `futures_basis_bp` and `sofr_minus_ff_bp_from_futures`.
6. **Calendar sensitivity** (JPM, U.S. Bond Futures Rollover Outlook, Aug 2026): a parallel +25bp move in funding changes a futures calendar spread (front minus back) by about -0.0625 points (-2/32nds), i.e. minus the funding move divided by four.

## E. Capital and balance sheet

1. **Repo-funded RV hurdle** (QFSE, Funding Treasury net basis trades, 6 Apr 2019). $100mm for 3 months at 3% leverage ratio needs $3mm of capital; at a 10% RoCE target it needs $75,000 of P&L. At 6% (US G-SIB), $150,000. Script: `capital_hurdle_pnl`.
2. **Breakeven swap spread by SLR and ROE** (FRBNY, Boyarchenko et al., Negative Swap Spreads, Oct 2018): at a 15% ROE the breakeven 10y swap spread is 11, -6, -22, -38, -54, -70bp for SLR 1-6%. Headline: 15% ROE at a 5% SLR needs -54bp.
3. **Capital-cost basis** (Huggins & Schaller, 2024, Ch.11): g = 10%, q = 20%, d = 8% gives 16bp. Moving d from 8% to 12% lifts the basis by 50%. Script: `capital_cost_basis_bp`.
4. **Haircut cost in a swap spread** (Huggins & Schaller, 2024, Ch.11-12): a 2% haircut funded at SOFR + 5% gives about 10bp on the 5y UST SOFR-ASW. Run backwards, the implied marginal haircut cost was 8bp in Sep 2023.
5. **Repo balance sheet** (BofA, US Treasury repo primer, Jul 2025): funding $25 of UST in repo grows the balance sheet from 100 to 125 under the leverage ratio.

## F. Turns and funding spikes

1. **Sep 2019 spike** (Citi, Fixing the plumbing, 30 Sep 2019; Tuckman & Serrat, 2022, Ch.0). O/N repo jumped from about 2.4% to intraday prints near 10%. Reserves fell by about 9% on corporate tax and Treasury settlements. The Fed injected $75bn initially, and more than $250bn by end-October (Düring, 2021, Ch.28). Lesson: several coincident drains, not one.
2. **Year-end 2024** (Conks, MMU, 5 Jan 2025). SOFR 4.46 on 27 Dec, 4.37 on 30 Dec, 4.49 on 31 Dec, 4.40 on 2 Jan, with IORB 4.40 and EFFR 4.33. GCF about 4.86-4.87 at the turn against TPR 4.25-4.33. GCF-TPR spike above 0.6. Read as funding-related, not reserve scarcity.
3. **Sep 2024 quarter-end** (Conks, Repo Defensive II, Nov 2024; MMU, Oct 2024). Over $600bn traded above the SRF minimum bid of 5.00%; $2.6bn was taken. The 5.01% bids were a real shortage signal.
4. **Mid-month squeeze, 15 Sep 2025** (Conks, QT for a little longer, Sep 2025). Corporate tax date plus coupon settlements pushed repo above IORB and above the SRF minimum bid; the SRF was not tapped in size.
5. **Tax day, 15 Apr 2025** (Conks, MMU, 17 Apr 2025). SOFR and TGCR about 4.35-4.36 against EFFR 4.33, reverting to 4.31 by 16 Apr. TGA rose $184.8bn on the day ($415.7bn to $600.5bn).
6. **Turn in a 2022 SONIA curve** (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, Ch.12): quarterly turns about -3bp, half-year and year-end about -5bp. A 1-day swap from 31 Mar 2022 on £10bn had DV01 about £2,740/bp, with net turn risk of £2,703.6/bp across the left/right pair.
7. **Euro 1-day GC at quarter-ends** (BofA, Bond market seasonality, Jun 2022): end-December change in 1-day GC vs Eonia averaged -188bp over eight years (minimum -445bp); end-January +138bp.
8. **Month-end jumps, 2019** (Fed staff, Quarter-end repo, Jun 2025): month-end changes up to about 50bp, ex-month-end spread averaging up to about 35bp. Pre-COVID month-end SOFR ran 5-10bp over ON RRP; H2 2024 base spread was 3-5bp.
9. **Feb 2023 Q4 SOFR-FF** (Citi, Time for moderation, 17 Feb 2023): market priced about -0.5bp; Citi estimated SOFR 1-3bp above FF after about $900bn of post-debt-ceiling bill supply. High financing made early delivery optimal in all six contracts.
10. **Facility ceilings on funding spreads** (Citi, Eat, pay, spend, Mar 2020). In 2008, CPFF priced tier-1 CP at OIS + 210bp (100 + 10 fee + 100 credit surcharge), and L/OIS stayed near that clearing level about two months after prime-fund outflows slowed. In 2020 the CPFF price was cut from OIS + 210bp to OIS + 110bp for tier-1 CP, which set the ceiling a 3m L/OIS of 112bp was judged against.

## G. Standing facility economics

1. **Corridor, 2026** (Conks, Nothing Ever Happens, Mar 2026): FIMA repo 4.00; swap lines 3.90; T/N FX-swap implied 3.76; AA CP 3.75; SRF and discount 3.75; GCF 3.73; SOFR 3.67; IORB 3.65; OIS 3.65; EFFR 3.64; FRP and RRP 3.50.
2. **SRF dealer economics** (Conks, Repo Fortification, Dec 2025): dealers need up to about 25bp over the top of the range to justify stigma, timing (1:30pm auction vs a 7-8:30am trading peak) and the balance-sheet cost of SRF borrowing plus onward lending.
3. **Facility lag** (Citi, Eat, pay, spend, Mar 2020): the first 2008 CPFF operation came about 20 days after announcement; L/OIS was expected to fall only about two months after facility operations began. Do not front-run normalisation.

## Verification notes on sources

- **Interest rounding.** One primer prints a $0.166 interest figure; the formula gives $0.165 (A.4).
- **Synthetic term repo sign.** One source writes cost = OIS fixed minus average(GC - EFFR); its own example (0.45% to 0.37%) only works as OIS fixed plus average(GC - EFFR). Use the sign that matches the example (D.4).
- **Fails charge.** Tuckman & Serrat describe the US fails charge as max(0, 3% - fed funds). Düring describes a flat 3% from May 2009. Check the rule in force before modelling fails.
- **Turn sign.** Düring says turns are always positive; Darbyshire documents negative turns for SONIA, where lenders without central-bank access lend to banks that have it. Both are right for different instruments: bank-driven year-end turns are positive, and non-bank-access lending gives negative premia.
- **SOFR trim.** Sources give three trimming rules (25th volume-weighted percentile, lowest 25% of DVP volume, lowest 20% of DVP volume from 2024). Check the administrator's current rule before using a historical level.
