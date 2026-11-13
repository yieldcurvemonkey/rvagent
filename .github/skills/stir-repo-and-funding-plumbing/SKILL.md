---
name: stir-repo-and-funding-plumbing
description: Repo and funding plumbing for G10 rates RV - GC vs special repo and specialness, act/360 repo cash, haircuts and term-repo carry; implied repo and net basis of futures; tri-party vs GCF vs cleared DVP vs bilateral segments; SOFR, TGCR, BGCR, EFFR and OBFR construction; SOFR-FF (SERFF) and SOFR/EFFR-IORB spreads; reserves, ON RRP, TGA and bill-supply drivers; SRF and discount-window ceilings; quarter, month and year-end turns; G-SIB, SLR and sponsored or cleared repo. Use when pricing or sizing repo financing or carry, asking why a bond is special or what the GC rate is, judging reserve scarcity or funding stress, interpreting a quarter-end, month-end or year-end repo spike, or checking SRF, RRP or IORB levels. SOFR-FF basis trades are in spread-tenor-and-index-basis; reserves and QT in stir-central-bank-balance-sheet-and-reserves; bill spreads in stir-bills-and-money-market-spreads.
---

# Repo and funding plumbing

Repo is the secured funding layer under every levered RV trade. It finances longs, covers shorts, and sets the carry on a bond, a futures basis or a swap-spread package. Repo rates move with cash versus collateral and with dealer balance-sheet capacity. They are read through published benchmarks that are volume-weighted medians of different segments, so the same move can mean different things depending on which segment drove it. This skill gives the repo arithmetic, specialness mechanics, the segment and benchmark map, the implied-repo identity, and the USD reserve, ON RRP and SRF diagnostics behind SOFR-FF, SOFR-IORB and turn premia. Regime tables are in [usd-funding-regimes.md](references/usd-funding-regimes.md); market-by-market detail is in [g10-repo-markets.md](references/g10-repo-markets.md); numeric examples are in [worked-examples.md](references/worked-examples.md).

## When to use
- Repo-financed carry or breakeven for a bond, futures-basis or swap-spread trade; a term repo rate for a given horizon.
- A short leg that may be special, or a long leg funded on term repo that may reset or be withdrawn.
- Implied repo, IRR, net basis or option-adjusted basis for a futures contract; whether the CTD repo is rich or cheap.
- SOFR-FF, SOFR/FF, SERFF, FF-SOFR, SOFR-IORB, EFFR-IORB or TGCR-RRP: the level, its regime, or a trade on it.
- Quarter-end, month-end, year-end, tax-date or coupon-settlement funding spikes; turn premia in a curve.
- Dealer balance-sheet or SLR, G-SIB and leverage limits on repo; sponsored or cleared repo; clearing-mandate effects on benchmarks.
- Not for: compounded RFR coupon mechanics ([stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md)), CTD option value ([fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md)), or bill-only supply analysis ([stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md)).

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Repo rates by collateral and term, GC and specific | `repo_rates` | EOD, ON to 3M, at least 1y | `specialness_bp = (gc - rate) x 100`; store `segment` and `haircut_frac` where known |
| Published fixings with percentiles and volume (SOFR, TGCR, BGCR, EFFR, OBFR) | `rate_fixings` | daily, at least 2y | Use `p25_pct`, `p75_pct`, `p99_pct`; `pub_ts_utc` gives point-in-time |
| Index composition and publication times | `rate_indices` | static | Confirm which segments each fixing contains |
| Policy levels: IORB, ON RRP, SRF minimum bid, discount rate, swap-line and FIMA rates | `rate_indices`, `cb_meetings` | effective dates | Put step curves on effective dates, not announcement dates |
| STIR futures (1M and 3M SOFR, 30-day fed funds, euro and sterling overnight-rate futures) | `stir_quotes`, `fut_quotes` | settle and intraday | `price = 100 - rate`; reject rows that break it |
| Futures deliverable baskets, conversion factors | `fut_basket`, `fut_static`, `bond_static` | by eligibility date | Only bonds eligible on date d enter the basket |
| Bond prices for implied repo | `bond_quotes` | same snap as repo | Clean, accrued and dirty kept separate |
| Balance-sheet series: reserves, TGA, ON RRP, FRP, bills outstanding, net bill issuance, dealer UST | `macro_series` (balance-sheet ids the contract defines) | daily or weekly, at least 2y incl. current regime | Use publication date for point-in-time work |
| OIS and swap par rates (3m OIS vs GC, SOFR swaps) | `curve_par` | daily | Needed for OIS-GC and term-repo comparisons |
| Swap spreads | `swap_spreads` | daily | Balance-sheet cross-check |
| Auction calendar: new issues and reopenings | `auctions` | per auction | Drives the specialness cycle |

If an input is missing, or a row has `data_ok = false`, ask for it or request it from the data adapter. Never invent a rate, spread or balance. A fixing without percentiles cannot support dispersion checks; say so in the output.

## Method

### 0. Conventions (state them in every output)
- Rates in percent per annum; spreads in bp. Repo and SOFR are act/360 in USD; check the currency convention before reusing (see [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md)).
- `SOFR-FF` here means SOFR minus EFFR (positive = SOFR above FF). Sources invert it. BofA's FF-SOFR is EFFR minus SOFR; Citi's "SOFR/FF" goes negative when SOFR rises. Restate the sign before comparing any levels.
- Futures basis = 1M SOFR future price minus 30-day fed funds future price (same month), in bp. It equals (EFFR - SOFR), so it is the negative of the realised SOFR-EFFR. A positive futures basis means SOFR priced below EFFR.
- "Long SOFR-FF basis" (bet SOFR rises vs EFFR) = short the 1M SOFR future vs long the fed funds future.

### 1. Locate the rate: segment and benchmark

| Segment | Who lends / borrows | Collateral | Settlement | Feeds |
|---|---|---|---|---|
| Tri-party (TPR) | MMFs lend to dealers; ON RRP runs here | Basket (UST, agency MBS, equities, corporates); no specific bond | Custodian; settles about 3:30pm | TGCR (UST-only), BGCR, SOFR |
| GCF | Interdealer, blind, via brokers, FICC-netted | Generic baskets (UST < 10y, < 30y, agency MBS), FRNs eligible in some | Net-of-net next day | BGCR, SOFR |
| DVP (cleared bilateral, incl. sponsored) | Dealers to hedge funds, via FICC | Specific bonds, often the CTD; specials trade here | Fedwire DVP | SOFR |
| Uncleared bilateral (NCCBR) | Dealer to hedge fund, no CCP | Specific | Bilateral | No official benchmark |
| Fed facilities | ON RRP (floor), SRF (ceiling), FIMA repo, discount window | UST | Tri-party or Fedwire | Floor and ceiling rates |

- **SOFR** = volume-weighted median of tri-party, GCF and cleared bilateral (incl. sponsored). It excludes uncleared bilateral and Fed operations, and trims the lowest-rate DVP trades (specials). The trim historically used the 25th volume-weighted percentile; the 2024 methodology removes the lowest 20% of DVP volume. Check the administrator's current rule.
- **TGCR** = tri-party only. **BGCR** = TGCR + GCF. **EFFR** = volume-weighted median of fed funds (thin, roughly $80-160bn a day against SOFR at $2-3tn). **OBFR** adds eurodollar and deposit volume.
- Typical rate order, cheapest to dearest: tri-party < GCF and DVP < uncleared bilateral. GCF is the most volatile segment. Read dealer balance-sheet capacity as GCF minus tri-party: a wide spread means inflexible dealer balance sheets.
- SOFR is bimodal: one mode near the tri-party (cash-lender) rate and one near the cash-borrower rate, proxied by the 75th percentile. When the 75th-25th percentile gap widens (large coupon settlements, balance-sheet dates), the median is pulled toward the upper mode; SOFR minus the 25th percentile explained about 68% of variance against the 75th-25th gap (Citi, FX Basis Quarterly, Dec 2024). Track the percentiles, not only the median.
- A segment that moves alone is a plumbing or classification question first, not a funding signal. Example: tri-party printing below ON RRP in Jul-Aug 2024 was a benchmark anomaly while TGCR and other repo stayed normal. Decompose by segment before reading a move (Conks, Repo dislocation, Aug 2024).

### 2. Repo arithmetic
- Repurchase: `P_rp = P_cash x (1 + r x d/360)`.
- Interest: `I = MV x (1 - h) x r x d/360`, with MV the dirty value of collateral. Cash lent is `MV x (1 - h)`.
- Rate from prices: `r = (P_rp - P_cash)/P_cash x 360/d`.
- Haircut: `h = 1 - cash/MV`; margin held = `MV - cash`. Variation margin re-marks daily to restore it.
- Haircut medians, tri-party (Tuckman & Serrat 2022): UST and agency 2%; agency CMO 4%; IG corporates and money-market 5%; ABS IG 7%; equities, HY and munis 8%. Haircuts rise with maturity and with weaker credit quality. They reprice in stress: Irish and Portuguese haircuts at MF Global went from 3% to 80% in Jul 2011.
- Zero haircuts matter for leverage. About 70% of non-centrally-cleared bilateral repo is at zero haircut (OFR 2023 pilot, cited by Yadav & Younger 2025); about 74% of hedge-fund UST repo borrowing had zero or negative haircut (Banegas & Phillip, Fed, cited by Huggins & Schaller 2024). Leverage on zero-haircut repo is limited only by the dealer's risk tolerance.
- Haircut cost: a haircut costs `h x MV x (funding rate - repo rate)` per year, and only if the gap is funded above repo. Example: a 2% haircut funded at SOFR + 5% on a 5y UST SOFR-ASW gave about 10bp (Huggins & Schaller 2022).

### 3. Specialness
- `specialness_bp = (GC - special repo) x 100`. Positive when the bond is special. It is term-specific: the same bond can be 100bp special overnight but 10bp special for a month (Düring 2021).
- Drag on a short: `drag per year = notional x (GC - special)`. Illustrative: GC 5%, special 3%, $100mm short costs $2mm a year.
- Auction cycle, 10y on-the-run, averaged over 51 notes (Nov 2008 to Jul 2021; Tuckman & Serrat 2022): about 156bp the day before the first reopening (2-sd band 116-196bp); 48bp before the second reopening; below 20bp before the next new issue. Dealers short the on-the-run to hedge the upcoming auction; that short demand disappears after the reopening.
- Specialness is non-negative against GC (bar fails) and right-skewed: it jumps in squeezes and decays slowly. Do not price it as symmetric noise.
- Fair repo-GC basis of a bond = the discounted expected overnight specialness over its remaining life (Duffie 1996, external; Huggins & Schaller 2024). Estimate it from predecessor issues by rank and age. A bond never expected to be special has no funding component.
- Specials volume is defined as UST trading more than 10bp below GC (Barclays, Short-rate primer, Jan 2025). Larger auction sizes add supply and reduce specials; a steeper curve raises them.
- Fed SOMA securities lending: 5bp fee; each dealer may borrow up to 25% of an issue's holdings, and $5bn across issues. Reopenings cut specialness risk (BofA, Auction primer, Mar 2024).
- Fails: a failing seller pays the coupon and earns no repo interest, so special repo is floored near 0%. The US fails charge is max(0, 3% - fed funds) per Tuckman & Serrat, which pushes the floor to about -(3% - fed funds): 0% when fed funds are above 3%, negative below it (special rates went negative in Mar 2020). Düring describes a flat 3% from May 2009. Check the rule in force. EU CSDR buy-ins apply from 1 Feb 2021.

### 4. Implied repo, net basis and carry (futures)
- Implied repo (approximation): `IRR = r_CTD,term - BNOC / P_dirty x 360/n`. BNOC is the basis net of carry in price points per 100 face; n is calendar days from settlement to the assumed delivery date. Use the CTD's term repo to delivery (JPM, Special delivery, Dec 2019).
- Option-adjusted: `OA IRR = IRR + OV / P_dirty x 360/n`, where OV is the value of the delivery options. Compare OA IRR with CTD term repo.
- Reading: IRR above term repo means the long-bond, short-future position (long basis) earns more than it funds. IRR below repo means the opposite. A negative net basis means the IRR exceeds the repo used, so check which repo rate the basis assumes.
- Delivery date: IRR is poorly behaved as n shrinks, because the denominator is small and the delivery day is unknown. Test first, mid and last delivery. Early delivery becomes likely when financing exceeds the CTD coupon (negative gross basis, JPM Wildcard, May 2018).
- Funding barometer: when implied repo exceeds 1-3m bank CP or FX-forward USD yields, real money reallocates into the basis (JPM, Why we should all care about basis, Mar 2020).
- Squeeze signal: a CTD IRR that approaches central-bank or unsecured funding rates, equivalently a very negative net basis, means the CTD is being controlled through repo (Düring 2021).
- Carry over d days (price points per 100 face): `carry = accrued coupon over d days - (P + AI) x r x d/360`, with accrued coupon = c x d/(365 or actual period) for an annual coupon rate c. Locking carry needs term repo; overnight repo leaves the carry tied to the O/N path.
- Repo sensitivity of a forward: `dF/dr = (P + AI) x n/360` per 1.00 (100%) of rate, so divide by 10,000 for price points per bp. Higher repo raises the forward price.
- Futures calendar spreads: a parallel move in funding changes a three-month-apart calendar spread (front minus back) by about minus the funding move divided by four (JPM, US Bond Futures Rollover Outlook, Aug 2026).

### 5. Term vs overnight financing and stub risk
- Term repo locks cost for the horizon; overnight is cheaper on a positive curve but leaves the position exposed to O/N path changes. Long basis loses if O/N repo rises; short basis loses if O/N reverse rate falls (Burghardt et al., Treasury Bond Basis, 2005).
- An un-termed overnight-funded CTD position is effectively a roughly three-month duration exposure to short rates. Hedge with FF or SOFR futures, or term the repo (Quantitative Finance Stack Exchange, Aug 2023).
- Synthetic term repo: pay fixed OIS and fund overnight at GC. Cost = OIS fixed + average(GC - EFFR). Example: 1y OIS 0.45%, GC 8bp under EFFR, gives 0.37% (Credit Suisse, Basis Points, 2010). Residual risks: realised GC-EFFR, the bond's own specialness, and simple vs compound interest.
- Term reach: UST term repo rarely extends beyond about three months (average around 1.5 months). Beyond 1y, SOFR swaps are more liquid than term repo, so mark term repo off SOFR swaps (BofA, Spot vs forward, 2024; Stathakopoulos, ICMA, 2021).
- Rollover risk: lenders can refuse to roll; a repo tenor shorter than the trade creates rate and availability risk (CFTC MRAC, Dec 2024). Re-margining from term repo plus futures variation margin changes realised carry (Huggins & Schaller 2024).
- Stress: 99th-percentile repo minus SOFR reached 174bp on 16 Mar 2020 (Tuckman & Serrat 2022). Use this as a stress ceiling for availability scenarios.

### 6. Funding spreads and the reserve regime (USD first)
- Measures: `SOFR-IORB`, `EFFR-IORB`, `SOFR-EFFR`, `TGCR-RRP`, `GCF-TPR`. Read each against its regime (table in [usd-funding-regimes.md](references/usd-funding-regimes.md)).
- Marginal lender rule (Citi, Dec 2024): with ON RRP above zero, MMFs set the tri-party price (they need RRP plus a spread). With ON RRP near zero, banks are the marginal lender and tri-party trades closer to IORB.
- Two-regime heuristic (BofA, Jul 2025): ON RRP at or above $500bn anchors SOFR near RRP. Below $500bn, SOFR is pushed up, SOFR-FF tightens, and SOFR becomes more volatile.
- Scarcity gauges: EFFR above IORB is the Fed's trigger to add reserves; SOFR above IORB means banks are lending reserves into repo, a drag on fed funds. Bank lending into repo typically increases when repo is 5-10bp or more above IORB (BofA, Jul 2025).
- Reserve-demand elasticity (NY Fed, via Barclays Jan 2025): change in EFFR-IORB per 1pp change in reserves/bank assets. Near zero means ample; about -1.3 to -1.5 in 2019.
- Level regressions take the form `spread_bp = a x ln(L) + b`, with `L = (reserves + ON RRP)/GDP` or reserves in $bn, fitted per regime. Recent R-squared is often below 0.2. Use them for direction and scale and refit on current data.
- Bills: on settlement dates, each $1bn of net new bills cut ON RRP by about $0.5bn (BofA, Aug 2025, R-squared 0.20). Bills reach reserves only once RRP is nearly exhausted.
- TGA: a $1 rise in TGA reduces reserves (or ON RRP) by $1, all else equal. Repo impact depends on the pace of the TGA rebuild and on reserve demand, not on the bill stock alone.
- FF market: FHLBs (about 95% of lending) prefer FF for its early return and shift to repo when repo yields more. Foreign-bank branches run the IORB arbitrage. EFFR sat about 7bp below IORB from mid-2022 and had narrowed to 1-4bp by late 2025 to Mar 2026 (see regime snapshots), so level and drift both matter and EFFR is not a pure liquidity gauge.

### 7. SOFR-FF (SERFF) and the futures basis
- For a contract month: `futures_basis_bp = (SOFR1M price - FF30d price) x 100 = -(SOFR avg - EFFR avg) x 100`. Realised SOFR minus EFFR (bp) = `(FF30d - SOFR1M) x 100`. Example: SOFR future 96.00, fed funds future 96.15 means SOFR 15bp above FF (Conks, Jun 2026).
- Fair value splits into three parts: the policy path (read off the fed funds futures strip, never regressed); a spread level, which is the liquidity and TGA model; and a month-end or quarter-end turn. One futures price gives one flat add-on, and the split between basis and turn is a model choice.
- Path model (Citi, Jun 2025): regress SOFR/FF on reserves and bills outstanding with month-end controls; apply the betas to projected TGA and bill paths; overlay turn effects; compare month by month with futures.
- Hedge ratio: use DV01 per contract (the 1M SOFR and 30-day fed funds contracts carry the same per-bp value). When hedging an FF position against SOFR/FF exposure, a ratio near 4x between SOFR-IORB and FF-IORB moves was observed on 16 Sep 2019, when SOFR moved more than FF (Citi, Sep 2019). That is one episode, not a constant.
- Turns and events: the Fed's decisions take effect the day after the FOMC, so a stub window ending the day of a meeting carries no exposure to that meeting (Citi, Aug 2019). Tax dates and coupon settlements can lift repo by several bp for a day; keep those days out of trend fits.
- Trade-level sources give levels only as examples: for instance, a short Oct 2025 SOFR/FF was entered at -4bp with a -8bp target and -1bp stop, quoted as FF minus SOFR (BofA, Jun 2025). These are not recommendations. Any entry must be rebuilt from current data.

### 8. Turns: month-end, quarter-end, year-end
- Window metrics. Quarter-end: SOFR minus ON RRP over the quarter-end window of plus or minus two business days (Fed, FEDS Notes, Jun 2025). Month-end: the maximum of SOFR minus ON RRP within the five-day window centred on the last business day (FRBNY, Perli, Nov 2024).
- Magnitudes. In 2019 month-end changes reached about 50bp, and the ex-month-end spread averaged up to about 35bp (Fed, Jun 2025). SOFR-RRP was up to about 25bp at the Sep 2024 and year-end 2024 turns (Fed, Jun 2025). Pre-COVID month-end SOFR ran 5-10bp over RRP.
- Causes. US G-SIB scores use year-end snapshots, so year-end is the sharpest. Some jurisdictions (euro-area leverage reporting, for example) use quarter-end snapshots, while the US leverage ratio uses daily averages. Japanese turns fall on 1 April. UK rules ban short-term window dressing. Canadian banks cut US repo at their quarter-ends. GSE P&I cash sits in repo until about the 25th-26th.
- Coupon settlement: track the change in SOFR-IORB on coupon settlement dates against the prior three days, versus net coupon issuance; the sensitivity rose in 2025 (BofA, Repo jump, 2025). Pre-2008 fed funds seasonals: above target on Thursdays (bill settlement), month and quarter-ends, tax dates, refunding settlement and the 25th (mortgage settlement); below at year-end (Credit Suisse, Basis Points, 2010).
- Ordering: year-end > quarter-end > month-end. GCF and DVP spike most; tri-party stays below the SRF at quarter-end (FRBNY, Nov 2024), so judge the ceiling segment by segment.
- Turn premium in a curve: `turn = F(31 Dec -> 1 Jan) - neighbouring O/N rates`. Positive when banks withhold lending over the turn; negative when non-central-bank-access lenders lend to banks that have access (SONIA; Darbyshire 2022). Install with two nodes, `1d(30 Dec) -> 1d(31 Dec)` and `1d(31 Dec) -> 1d(1 Jan)`. Read the risk net across the left and right pair.
- Remove turns before fitting, and add them back afterwards. Ametrano & Bianchetti (2013) model the turn as a multiplicative factor on discount factors after the jump date, with jump size scaling with the crossing O/N rate's weight. Turns smear into the curve if left in.
- Turn size tracks base tightness, not a fixed premium. Under a Fed quarter-end pattern, composition moves matter: sponsored reverse repo and ON RRP both rose at quarter-end in 2023-24 (Fed, Jun 2025).

### 9. Dealer balance sheet, capital and regulation
- The binding constraint per bank is the larger of the risk-based and leverage requirements, not their sum. Example: RWA needs $100 of capital and SLR needs $60; holding $100 is correct, and cutting the SLR to $50 changes nothing (Conks, Faulty Relief Valve, Dec 2025). Compute each bank's excess over each constraint.
- Leverage ratio = Tier 1 / exposure measure. Basel minimum 3%. US G-SIB enhanced SLR 5% at holding company, 6% at IDI (Conks, 2025). The 2025 eSLR proposal would cut the buffer to half the method-1 surcharge; verify the final rule.
- Repo grosses up the balance sheet: funding $25 of UST in repo takes the balance sheet from 100 to 125 (BofA, Jul 2025). Netting needs the same counterparty, the same settlement date and location, and a netting agreement. Novation to a CCP raises netting and cuts exposure.
- Repo-funded RV hurdle: `P&L >= LR x notional x RoCE x years`. $100mm for 3m at 6% LR and a 10% RoCE target needs $150,000 (QFSE, Apr 2019); at 3% LR it needs $75,000.
- Capital-cost basis: unsecured-minus-secured O/N basis is approximately `g x q x d`, with g the cost of equity, q the BIS risk weight (20% for interbank), d the capital ratio (8%). Example: 10% x 20% x 8% = 16bp. The basis scales linearly with d: 8% to 12% is +50%. SOFR-ASW is not affected by g, q or d; OIS-ASW and LIBOR-ASW are (Huggins & Schaller 2024).
- Matched book: dealers borrow in repo and lend in reverse; hedge funds pay the widest spread, large dealers the tightest (Conks, Money markets, Jun 2023).
- Dealer congestion: primary-dealer net UST ex-TIPS rose to about $400-500bn in 2025-26, and the balance-sheet cost of holding it pushes O/N rates up (Conks, 2025-26).
- Clearing mandate (SEC, Dec 2023): cash trades from 31 Dec 2025; repo from 30 Jun 2026 as first stated. Later sources cite a June 2027 repo deadline. Expect migration of uncleared repo into FICC DVP and GCF, with possible SOFR changes and higher fees and capital cost for levered basis financing. Cross-margining between futures at CME and cash at FICC can double-count margin (Yadav & Younger 2025).

### 10. Corridor, facilities and ceilings
- Global ladder, normal times (Jul 2025 levels), top to bottom: FIMA repo rate (public offshore ceiling) > swap-line rate = OIS + 25bp (private offshore ceiling) > FX-swap implied USD rate > SRF rate (ceiling for SOFR, GCF, TPR) and discount rate (onshore ceiling for EFFR) > IORB > EFFR > GCF > SOFR > TPR > FRP rate (public floor) > ON RRP (private floor) > specials. Ceilings and floors hold "in theory, not always in practice"; in Mar 2026 GCF and SOFR printed above IORB (see the regime file), so the middle of the ladder reorders with reserve scarcity.
- SRF: $500bn aggregate cap as of Jan 2025 (the Fed has since changed the limit; verify the current terms); minimum bid at the top of the range; auction 1:30-1:45pm; settles via tri-party at 3:30pm. Stigma and timing make it a soft ceiling. Repo can print above the minimum bid with no take-up (Sep 2024: over $600bn above the minimum, $2.6bn taken). Bids above the minimum signal a genuine shortage.
- Technical adjustments: usually 5bp. The Fed becomes concerned when EFFR sits within 5bp of the top of the range (Barclays, Jan 2025). JPM's rule is repo persistently within 5bp of the top.
- ON RRP is a leaky floor: not every eligible lender has access, and MMFs accept lower rates for earlier cash. Specials can trade below it.
- Fed liquidity: the sum of reserves and ON RRP, scaled by GDP or bank assets. See the regime file for zones, which differ by source.

## Worked examples

- **Repo arithmetic (Tuckman & Serrat 2022, Ch.10).** $109,898,438 borrowed for 44 days at 0.015% repays $109,900,452. At a 3% haircut on the same collateral, cash is $106,601,485 and margin is $3,296,953.
- **Synthetic term funding (Credit Suisse, Basis Points, 2010).** 1y OIS 0.45% with GC 8bp under EFFR gives about 0.37% expected funding cost.
- **Implied repo identity (illustrative).** Dirty 100, term repo 3.50%, BNOC 0.25 points, 90 days gives IRR 2.50%. Script: `implied_repo_pct`.
- **Sep 2019 spike (Citi, Fixing the plumbing, Sep 2019; Düring 2021 Ch.28).** O/N repo rose from about 2.4% to intraday prints near 10%, with the Fed injecting $75bn at first and over $250bn by end-October. Lesson: several coincident drains (tax date, settlement, TGA rebuild), not one.
- **Year-end 2024 (Conks, MMU, Jan 2025).** SOFR 4.46 on 27 Dec, 4.49 on 31 Dec, 4.40 on 2 Jan against IORB 4.40 and EFFR 4.33. GCF-TPR spiked above 0.6, read as balance-sheet funding rather than reserve scarcity.
- **SOFR-FF futures sign (Conks, SOFR/FF primer, Jun 2026).** 1M SOFR future 96.00 and fed funds future 96.15 gives realised SOFR 15bp above FF; the futures basis reads -15bp.
- **Haircut stress (MF Global 2011, Tuckman & Serrat 2022).** Haircuts on peripheral sovereign collateral moved from 3% to 80% in July 2011. A position that was fundable at 3% became unfundable.

More examples with full citations are in [worked-examples.md](references/worked-examples.md).

## Signals & interpretation

| Signal | Threshold | Read | Action |
|---|---|---|---|
| EFFR - IORB | > 0 | Reserve scarcity; Fed likely adds reserves | Strongest funding-stress flag; re-check after 1-2 weeks |
| SOFR - IORB | > 0 sustained; > 5-10bp | Banks lending reserves into repo | Drag on FF and on ON RRP; watch the 75th and 99th percentiles |
| TGCR - RRP | > 0 | Excess collateral | Repo above RRP; SOFR pressure |
| TGCR - RRP | < 0 | Excess cash | MMFs chasing collateral; SOFR softening |
| GCF - TPR | > 0.10 (10bp) | Dealer balance-sheet capacity constrained | Rising intermediation cost; check year-end |
| SOFR - EFFR | roughly -5 to +15bp in 2024-25 | FHLB repo demand | Above +15bp: FHLBs moving cash into repo |
| ON RRP | $500bn threshold | Anchor regime | Below $500bn: SOFR pressure, SOFR-FF tightens |
| SRF take-up | > 0 at the minimum bid | Shortage, not arbitrage | Treat as a stress event |
| Reserves / bank assets | < 11% scarce; 11-13% ample; > 13% abundant | Fed-internal zones quoted by Conks | Thresholds drift; use your own |
| Specialness, 10y OTR | Peaks near 156bp before the first reopening; 48bp before the second; below 20bp before the next new issue. 100bp+ overnight | Cycle peak or squeeze | Shorts costly near the peak; check the auction calendar |
| Quarter-end SOFR - RRP | 20-25bp+ | Turn spike | Filter from trend; do not extrapolate |
| Net basis | Negative, or IRR above repo | CTD squeeze or rich futures | Check the repo assumption and delivery date |

Stress is confirmed only when EFFR-IORB, SOFR-IORB, the share of prints above IORB and SRF take-up move together. A quarter-end repo spike on its own is not stress. Trade-on signals are rules-of-thumb; set thresholds from your own history.

## Pitfalls
- Sign flips across sources (FF-SOFR vs SOFR-FF; bill-OIS vs OIS-bill; futures quoted as 100 minus rate). Restate the sign before comparing.
- SOFR is a segment blend, not one repo rate. Check whether DVP, GCF or tri-party drove a move; rolling betas differ by segment.
- Fixed historical levels go stale: SOFR trimming changed in 2024, clearing migration changes the mix, and the SRF break in Aug 2021 means pre-SRF SOFR history mixes regimes. Re-estimate on post-break data.
- Regressions are regime-dependent. The 2015-19 and post-2020 fits differ strongly. Exclude debt-limit distorted periods and watch revisions to forecasts, not just the levels.
- Reserve levels are estimates. Conks and the Fed differ by $0.1-0.2tn on LCLoR, and the zones differ by about 1pp. A scarcity date depends on the threshold chosen.
- Repo can stress while fed funds is calm, and secured rates above unsecured are a feature of the post-Basel III regime, not stress on their own.
- EFFR is a thin market (about $80-160bn/day); its spikes are noisy. Do not read EFFR as a clean liquidity gauge.
- Un-termed repo on a CTD position is a duration bet. Termed repo removes it but adds a fixed-rate cost; compare with the expected O/N path.
- Implied repo near delivery is unreliable. Use option-adjusted net basis and test delivery dates.
- Year-end basis looks cheap for balance-sheet reasons (G-SIB snapshot, roll liquidity). Do not confuse a balance-sheet discount with a mispricing that will converge.
- Haircuts and margins move in stress. A position sized at today's haircut can become unfundable; size for the worst-case haircut you can meet in cash.
- Specialness is right-skewed; a short squeeze can intensify before it eases. Confirm why a bond is rich before fading it.
- Negative swap spreads are not free carry once capital, haircut, IM and PFE are included.
- Clearing migration changes SOFR and the segment mix at a known date; benchmark breaks are not funding moves.
- Dates: check day count (act/360 vs act/365), publication time (SOFR published about 8am next business day), and whether a turn sits inside the contract period.

## Output
Return one table per date and currency with these columns:
- Date; benchmark prints (SOFR, TGCR, BGCR, EFFR, OBFR) with the 25th, 75th and 99th percentiles where published.
- Policy levels in force on that date: IORB, ON RRP, SRF minimum bid, discount rate, swap-line rate.
- Spreads: SOFR-IORB, EFFR-IORB, SOFR-EFFR, TGCR-RRP, GCF-TPR, SOFR-RRP, all in bp.
- Regime label: ON RRP above or below $500bn; reserves / bank assets zone; RDE sign.
- Calendar flags: month-end, quarter-end, year-end, tax date, coupon settlement, GSE float.
- Funding for a trade: repo rate for the collateral, term repo to horizon, specialness per issue, implied repo and net basis with the repo assumed and the delivery date.
- Data flags: any row with `data_ok = false`, missing percentiles, or an unchecked sign.

Then a short paragraph of conclusions and a list of assumptions. If the output feeds a trade note, hand the funding numbers to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and state the funding carry explicitly.

## Scripts
- [`scripts/repo_funding_math.py`](scripts/repo_funding_math.py): repo cash and interest, haircut split, specialness and its drag, implied repo and its inverse, synthetic term repo, compounded index interest, futures-basis sign, capital hurdle, and the g x q x d basis. `python -I scripts/repo_funding_math.py --selftest` checks each against a known source value. The `specialness --csv PATH` subcommand summarises `specialness_bp` from a canonical `repo_rates` CSV.

## Related skills
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): gross and net basis, implied repo, and CTD carry in full.
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): delivery options and CTD switches that sit on top of the implied repo.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): QE/QT mechanics, reserve ampleness, RRP and SRF design.
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bill supply, MMF demand, and debt-limit dynamics in detail.
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): compounded RFR conventions and fixing risk.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): SOFR, SOFR-FF futures basis and strip relative value built on the basis here.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): policy path extraction that must strip out the funding spread and turns.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): SLR, G-SIB and leverage costs in depth.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap spreads and asset swaps as repo bases.
- [xccy-basis](../xccy-basis/SKILL.md): cross-currency basis and FX-swap funding.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CCP and margin funding effects on basis.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts, benchmarks and calendars for each G10 market.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): collateral choice and CSA discounting.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): turn and calendar screens.
- [fi-curve-construction](../fi-curve-construction/SKILL.md): inserting turns into curve bootstraps.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables and point-in-time rules.
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): tenor and index basis, including SOFR-FF.

## References
- Bruce Tuckman & Angel Serrat - Fixed Income Securities: Tools for Today's Markets, 4th ed. (Wiley, 2022): repo mechanics, haircuts, auction-cycle specialness, fails, SLR and LCR, MF Global and Mar 2020 cases.
- Alexander Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley Finance, 2021): repo segments and specials, turns, corridor and floor economics, VM and IM liquidity transformation, Sep 2019 episode.
- Doug Huggins & Christian Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): capital-cost basis g x q x d, specialness in asset swaps, haircut-cost test, shadow cost of balance sheet.
- Doug Huggins & Christian Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley Finance, 2022): SOFR construction and percentile fit, SRF break, fixing risk, SOFR-EFFR arbitrage condition, CCBS and SR3:ED basis.
- Galen Burghardt, Terrence Belton, Morton Lane, John Papa - The Treasury Bond Basis, 3rd ed. (McGraw-Hill, 2005): repo versus reverse asymmetry, term vs overnight financing, stub DV01, squeezes and CTD short supply.
- J.P. Morgan (Younger, Salem, St John) - Special delivery: how delivery options distort rich/cheap metrics for Treasury futures (4 Dec 2019): IRR vs term repo identity, option-adjusted IRR, turn effects.
- J.P. Morgan (Younger, Salem, St John) - Why we should all care about Treasury futures basis (12 Mar 2020): implied repo as a funding barometer, dealer balance sheet and Fed repo limits.
- J.P. Morgan (Salem, Younger, Zhao) - Good things come to those who wait: the wildcard option in early delivery (18 May 2018): negative gross basis when financing exceeds the CTD coupon.
- Barclays Research (Joseph Abate) - US short interest rate primer (Jan 2025): administered rates, reserve demand elasticity, SRF design, specials volume, Fed securities lending, segment spreads, clearing and regulation.
- BofA Global Research (Mark Cabana, Katie Craig) - US Treasury repo primer: 2025 edition (7 Jul 2025): segments, SOFR construction, two-regime heuristic, facilities, dealer SLR and sponsored repo.
- BofA Global Research (Mark Cabana, Ralph Axel et al.) - FX-Sofr primer (31 Oct 2023): reserve accounting, national reporting-date conventions, CAD, JPY, AUD and GBP specifics.
- Citi Research (J. Mathai, R. Bikbov, S. Kang, J. Williams, S. Li) - Fixing the plumbing (30 Sep 2019): reserve scarcity point, year-end FF turn extraction, SOFR/FF sensitivity.
- Citi Research (Alejandra Vazquez Plata, Jason Williams) - Short-end notes: SOFR/FF spiking into quarter-end (27 Jun 2025): weekly-change betas and the path-model method.
- Citi FX Basis Quarterly (Jason Williams et al.) - Paying the basis (again) into 2025 (13 Dec 2024): marginal-lender regime rule, TGA and RRP transmission.
- Federal Reserve Board (Bostrom, Bowman, Rose, Xia) - FEDS Notes: What happens on quarter-ends in the repo market (6 Jun 2025): quarter-end metric, event study, net supply-demand.
- Federal Reserve Bank of New York (Roberto Perli) - Facing quarter-end pressures (slides, 12 Nov 2024): month-end metric, segment distribution against the SRF.
- Boyarchenko, Gupta, Steele, Yen - Negative swap spreads (FRBNY Economic Policy Review, Oct 2018): repo-financed carry and SLR-driven breakeven swap spreads.
- CFTC Market Risk Advisory Committee - The Treasury cash-futures basis trade and effective risk management practices (Dec 2024): basis financing, zero haircuts, sponsored margin, rollover risk.
- J.H.M. Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): turn installation and risk, SONIA quarter-end premium, leverage ratio binding on repo.
- Ferdinando Ametrano & Marco Bianchetti - Everything you always wanted to know about multiple interest rate curve bootstrapping (SSRN 2219548, 2013): turn-of-year estimation and removal.
- Vasileios Stathakopoulos (Credit Suisse) - The interaction between repo and interest rate swaps (ICMA workshop, 27 Sep 2021): SOFR build, term repo curve, specials.
- Credit Suisse (Carl Lantz, Michael Chang et al.) - Basis Points: a guide to the front-end and basis swap markets (18 Feb 2010): synthetic term repo, EFFR seasonals.
- Yesha Yadav & Joshua Younger - Central clearing the U.S. Treasury market (University of Chicago Law Review, 2025): clearing mandate, netting, haircuts, cross-margining.
- Conks (Monetary Mechanics, Substack) - Plumbing notes, 2023-26, e.g. Money market update (Jan 2025), Repo fortification (Dec 2025), Nothing ever happens (Mar 2026): benchmark construction, monitors, SRF stigma, year-end dashboards. Commentary; treat as the author's view.
- Duffie, D. (1996), "Special repo rates", Journal of Finance (external): a special bond's repo-GC basis as the discounted expected future specialness.
- Further sources cited in the reference files and worked examples: BofA Global Research - Fed QT beyond taper and funding impact (22 Oct 2021); Fed plumbing and balance sheet teach-in (4 Jul 2025); US repo sensitivity: higher than expected (8 May 2025); Monthly rates models (Apr and Aug 2025); Rates basics: spot vs forward (15 Feb 2024); US Treasury auction primer (8 Mar 2024); Global policy implementation guide (9 Jul 2025); Repo jump and Fed bill backfill risk (20 Oct 2025); Bond market seasonality explained (6 Jun 2022); Japan Rates Basics, JGB market guide (24 Apr 2023). Citi Research - US Rates Weekly: Learning on the job (2 Aug 2019), Eat, pay, spend (27 Mar 2020), Time for moderation (17 Feb 2023); Short-End Notes, SOFR/FF to go negative in Q3/Q4 (13 Jun 2025); European Rates Strategy: Latest views (20 Aug 2026). J.P. Morgan - US Bond Futures Rollover Outlook (12 Aug 2026); Cross currency basis 4Q24 outlook (26 Sep 2024). Conks (Monetary Mechanics) - Money Market Update (Aug 2024, Jan 2025), Repo Fortification (Dec 2025).
