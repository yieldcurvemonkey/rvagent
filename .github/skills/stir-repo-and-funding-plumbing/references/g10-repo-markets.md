# G10 repo and funding markets: what differs by market

Companion to [SKILL.md](../SKILL.md). Each block says what the benchmark is, where the funding floor and ceiling sit, the turn calendar, and the specials and fails regime. Evidence depth varies: USD is covered in depth; CHF and SEK/NOK are thin in the source set and are marked as such.

## USD

- **Benchmarks.** SOFR = tri-party + GCF + cleared bilateral (incl. sponsored), excluding uncleared bilateral and Fed operations. TGCR = tri-party only. BGCR = TGCR + GCF. EFFR = fed funds (thin, roughly $80-160bn/day vs SOFR at $2-3tn/day). OBFR adds eurodollars and deposits. All are volume-weighted medians with published percentiles (BofA primer 2025; Conks 2025).
- **Specials trim.** Historically, DVP trades below the 25th volume-weighted percentile were removed. The 2024 methodology trims the lowest-rate 20% of DVP volume. Heavy specials can still drag SOFR down; check the administrator's current rule.
- **Floor and ceiling.** IORB anchors; ON RRP is a leaky floor (MMFs accept lower rates for early cash; not all eligible lenders have access; $160bn per-counterparty limit). SRF is a soft ceiling (minimum bid = top of range; $500bn daily cap; 1:30-1:45pm). Discount rate sits at the top, stigmatised.
- **FF structure.** FHLBs (about 95% of lending) fund foreign-bank branches that arbitrage IORB. FDIC assessments make the same arbitrage unattractive to US banks, whose share of FF volume fell from about 35-38% (2019) to 5-10% (2024-25, chart readings). EFFR has been sticky about 7bp below IORB since mid-2022 (BofA; Barclays; Conks).
- **Clearing mandate.** SEC rule (Dec 2023): cash from 31 Dec 2025, repo from 30 Jun 2026 as first stated; later sources cite up to June 2027. Expect uncleared repo to migrate into FICC DVP and GCF, with possible SOFR and TGCR-to-SOFR changes (Barclays 2025; Conks 2026).
- **Turns.** Year-end > quarter-end > month-end. US G-SIB score is a year-end snapshot; US leverage ratio is a daily average. Proposed averaging of G-SIB inputs (2026) would smooth the cliff; the year-end turn already sat at multi-year tights in several currencies before that (Citi, Aug 2026). Check the final rule.
- **Specials.** Auction-cycle specials on the 10y OTR peak about 156bp the day before the first reopening. Fed securities lending: 5bp fee, 25% of an issue's holdings per dealer, $5bn across issues (Tuckman & Serrat 2022; Barclays 2025).

## EUR

- **Benchmarks.** EUR repo is quoted in GC baskets; €STR is an unsecured overnight rate (SARON, SOFR are secured). ECB MRO (1 week) and LTRO (3 months) and TLTRO are repo operations (Düring 2021; Tuckman & Serrat 2022).
- **Floor.** Under excess liquidity €STR trades below the deposit facility rate (DFR), and has done so since it was produced. Read that as structural, not stress (Düring 2021).
- **Corridor.** Simultaneous use of the lending and deposit facilities signals interbank distrust (Düring 2021).
- **Specials and fails.** Bonds trading 5%+ special is "not uncommon", so negative specials repo happens. Fails charges and CSDR buy-ins apply from 1 Feb 2021 (Düring 2021). Italian GC trades marginally above German GC (Düring 2021).
- **Quarter-end richening.** German 1-day GC richens into every quarter-end and reverses the next month (end-December change averaged -188bp over eight years, minimum -445bp, per BofA, Bond market seasonality, Jun 2022). Euro-area leverage ratio uses quarter-end snapshots, so window dressing persists (BofA FX-Sofr primer, Oct 2023).
- **Schatz/€STR anchor.** Schatz swap spreads sat near -10bp versus €STR as DU CTD S/N repo responded little to growing sovereign collateral (Citi, Euro latest views, Aug 2026). Treat as a 2026 observation.
- **Bund ASW and capital basis.** Bund ASW versus €STR includes a g x q x d capital basis and is more volatile than UST SOFR-ASW (Huggins & Schaller 2024). The February 2022 Bund repo squeeze is the standard case for a CTD squeeze through repo (Huggins & Schaller 2024).
- **Haircuts.** ECB haircuts are steep for BTPs: 5Y Bunds 98.5 lend value per 100, 30Y Bunds 95, 30Y BTPs 86.5 (Huggins & Schaller 2024). BTP haircut costs far exceed DE/FR/ES.
- **Recent flows.** ECB QT moves the euro closer to a steeper part of the reserve-demand curve; a minimum-reserve-ratio tweak could pull that forward by 4-5 months (Citi, Aug 2026). Also, 10y EUR swap spreads turned negative for the first time in Nov 2024 (Conks, Nov 2024).
- **Turn-of-year.** Euribor 1M turn-of-year was +64bp (29 Nov 2007) and +22bp (27 Nov 2008); on the IBOR-era curve, the 1M-curve 2014 turn was about 1/20 of the O/N turn and the 3M-curve about 1/3 of the 1M turn (Ametrano & Bianchetti, 2013).

## GBP

- **Benchmarks.** SONIA is unsecured; it can fix below Bank Rate, because institutions without BoE access lend to banks that have it (Darbyshire 2022). Gilt repo is the secured leg.
- **Floor and ceiling.** Bank Rate remunerates reserves. The Short-Term Repo (STR) facility and the ILTR set the ceiling; ILTR minimum spreads of 3, 5 and 15bp by level (BofA Global policy implementation, Jul 2025). BoE reserves were roughly £640bn to year-end 2026 (BofA, Oct 2026).
- **QT and gilt specialness.** A passive run-off of front-end issues removes collateral; the BoE's long-gilt portfolio (about 27% of sector outstanding) is lent via the DMO, so long gilts are vulnerable to repo specialness and ASW richening (Barclays, Oct 2026).
- **Turns.** Quarter-end premium was about -0.25 to -1bp in 2021 (Darbyshire 2022). PRA bans short-term window dressing and requires quarterly reporting (BofA FX-Sofr primer, 2023).
- **Haircuts.** BoE haircuts rise more steeply with maturity than Fed haircuts (floating 0.5/0.5; 5-10Y 3.0/3.5; 10-20Y 5.5/6.5; 20-30Y 7.0/9.5; >30Y 8.5/15.0 for coupon/zero, Huggins & Schaller 2024). The BoE often lends more against a bullet than against strips that replicate it.
- **Collateral choice.** Gilt repo at RFR + 8bp with no haircut can make short gilts the CTD collateral over cash, even after CSA haircuts (Darbyshire 2022, Ex 5.5).

## JPY

- **Benchmarks.** TONAR is unsecured overnight. The BoJ uses gensaki repo and outright purchases (formerly rinban) (Düring 2021; Tuckman & Serrat 2022).
- **Securities lending.** The BoJ facility caps the selling yield relative to the o/n Tokyo repo rate, with a minimum fee of 0.25% below it; each issue can roll up to 21 times, and the repurchase amount can be cut by up to 100% when the borrower lacks bonds, including CTD issues (BofA, JGB market guide, Apr 2023). Check the current terms before use.
- **Turns.** The balance-sheet turn falls on 1 April (fiscal year-end), not 31 December (Düring 2021). Year-end turn basis was at multi-year tights in mid-2026 (Citi, Aug 2026).
- **Dollar side.** JPY-side USD funding is repo-led; post-intervention softness normalises in 1-2 weeks (Citi, Aug 2026). MoF intervention funds from T-bills, FIMA repo (up to $60bn of UST) and deposits (Citi Macro, Aug 2026).
- **Basis.** The USD/JPY xccy basis recovered in Aug 2024 and very short (<=6m) basis is avoided near multi-year tights (Citi, 2026; Conks, 2024).

## CHF

- **Benchmark.** SARON is secured by government collateral (Tuckman & Serrat 2022). The source set has almost no CHF funding material for 2026. Do not build CHF repo signals on this skill's evidence without a fresh source.

## CAD

- **Benchmark.** CORRA is the reference rate; the Bank of Canada offers cash accounts to reserve managers at the deposit rate; CORRA is also the FX-swap reference (BofA FX-Sofr primer, 2023).
- **Turns.** Canadian banks (RBC, BNS, CIBC, BoM, TD) cut US repo at their quarter-ends (April is their Q2 end) (BofA Repo sensitivity, May 2025). Month-end FXOIS round trips of about 40bp occurred in Jul-Aug 2026 (Citi).
- **Floor and ceiling.** Band 2.70-3.00% (2025 snapshot); deposit 5bp below target; standing repo at target + 25bp; term facility to 30 days at 1M CAD OIS + 35bp (BofA Global policy implementation, Jul 2025).
- **Caution.** Be cautious paying CAD basis near historical tights given funding volatility (Citi, Aug 2026).

## AUD

- **Benchmarks.** AONIA is the overnight secured reference; FX-swap references are term bank bills (AUD 3M BBSW), not overnight RFRs. Adjust comparisons (BofA FX-Sofr primer, 2023).
- **Liquidity.** ES balances earn the cash rate minus 10bp; SF repo cash is at +25bp; RBA-AOFM securities lending is at the ES rate minus 25bp; the RBA no longer sterilises ES balances. The policy floor moved to a corridor from Apr 2025 (BofA, Jul 2025).
- **Seasonal.** AOFM deposit run-downs (liquidity injection) are largest in January and July (BofA Bond market seasonality, Jun 2022). Three of four major banks' funding needs after 30 Sep widen Oct-Nov swap spreads (same source).
- **Recent.** BBSW +10bp over OIS in Aug 2026; FX funding TN -15bp AONIA/SOFR (Citi, Aug 2026). RBA reserve drain via TFF maturity cut excess reserves by more than 50% from the early-2022 peak (JPM, Cross currency basis 4Q24, Sep 2024).

## NZD

- **Benchmark.** NZIONA. The NZIONA/SOFR basis is driven by settlement cash of about NZ$27bn; a tax outflow can cut it to about NZ$24bn. Watch OMO replenishment and reverse-repo maturities (Citi, Aug 2026).

## SEK, NOK, DKK

- **Liquidity.** NOK structural liquidity above NOK150bn; SEK certificate auction left SEK112bn; DKK current-account deposits about DKK380bn, near peak since 2024. Funding about -20bp FXOIS (Citi, Aug 2026).
- **Regulation.** The Swedish stability fee on bank liabilities influences SEK/USD cross-currency and FX rates (Darbyshire 2022).
- **Caution.** Thin evidence beyond the 2026 Citi weekly. Treat the levels as dated.

## Cross-market transmission (applies everywhere)

- **Repo to FX swap.** Cross-currency arbitrage borrows collateral in one currency, swaps it, and lends in another repo market; it earns the FX-swap premium and the repo gap, and tightens the basis until it reverses (BofA FX-Sofr primer 2023). Reverses when the US repo rate is relatively high.
- **Regulatory spillover.** US G-SIB leverage ratio influences euro repo liquidity (Darbyshire 2022).
- **Repo to equity.** Equity financing competes with UST repo for dealer balance sheet; fatter equity financing spreads push cash out of UST repo and widen SERFF shorts (Conks, Equity repo, Jul 2026).
