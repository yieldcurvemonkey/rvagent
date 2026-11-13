# G10 issuance calendars, redemption mechanics and central-bank supply operations

Per-market detail behind `SKILL.md`. Calendars change: confirm the current issuance calendar with the user or the debt
office data before building an event list (the `auctions` table is the source of truth, `calendars` for settlement days).

## EUR

### Germany (Finanzagentur)
- Quarterly calendar published in the last 10 days of the prior quarter: issues, sizes and a 10-day window, not exact dates.
  Only Germany pre-commits issuance far ahead (annual outlook plus quarterly calendars). Wednesday auctions, Friday
  settlement, bids by 11:00, results about 30 minutes later; Bubills Monday, linkers Tuesday. 2004-05 pattern: Schatz
  Mar/Jun/Sep/Dec, Bobl Feb/May/Aug/Nov, Bund roughly Jan/Apr/Jul/Oct (Burghardt et al., The Treasury Bond Basis, 3rd ed.,
  2005). Later: two 10Y a year with 2-3 taps each (about 25bn), OBL twice a year (about 20bn), BKO four a year (about 12bn),
  Bubill monthly (about 6bn) (Düring, Fixed Income Trading and Risk Management, 2021).
- **Auction demand cannot be read from prices.** No primary dealers; a bidding group (ejected below 0.1% of annual supply,
  duration-adjusted). The agency retains part of each auction and taps anonymously on interdealer platforms; with weak bids it
  raises the cut-off, allocates more non-competitively or retains more. Do not build tail/cover signals for DE.
- BKO mid-month maturities: BKO swap spreads can be traded with Euribor contracts with little basis risk. The Schatz CTD is
  usually a BKO; every other Bobl has an OBL CTD. Bund deliverables yield about 2-4bp less (fitted 2012; Huggins & Schaller,
  Fixed Income Relative Value Analysis, 2nd ed., 2024).
- On-the-run premium "more or less absent" because futures dominate the liquidity hierarchy; futures and CTDs cheapen first
  under selling pressure (Düring 2021).

### Other EGB
- **France (AFT)**: 10Y+ OATs first Thursday; 2Y/5Y/linkers third Thursday; about two new 10Y and one 30Y a year; active
  buybacks of the shortest lines, active swap user. 2026: state financing EUR311.7bn; EUR31bn bought back YTD to end-Aug (EUR7-8bn per
  month, nearly all 2027s), EUR50-60bn in 2026; next-two-year redemptions EUR196bn (2027), 250bn (2028), 293bn (2029) so 2027
  buybacks risk EUR60bn+; 30y taps 10 (2024), 8 (2025), 3 YTD 2026; long-term auction size cap EUR12bn vs EUR13.5-14bn typical
  (Barclays, Global Rates Weekly, 2 Oct 2026). The French 2001 swap programme "almost immediately repriced" French swap
  spreads: swap programmes have limited capacity (Düring 2021).
- **Italy**: two auctions a month (mid-month 5/15/30Y; month-end 3/10Y), lines EUR10-30bn. Redemption and coupon dates coincide
  with supply, so the auction cycle dominates reinvestment.
- **Spain**: Bonos 3/5Y first Thursday, Obligaciones 10/15/30Y third Thursday, monthly except August, about EUR10bn.
- **Netherlands (DSL)**: Tuesday after the first Wednesday; Dutch Direct Auction (up to 1h window, adjusted offer price); a
  repo facility for bonds below EUR5bn to avoid new-issue squeezes; quarterly pre-announced calendar. **Belgium**: exchange
  auctions swap bonds within 1y of maturity into long benchmarks to smooth redemptions; OLOs EUR7.5-15bn. **Austria/Ireland/
  Portugal**: monthly auctions or syndication. **Finland**: syndication then taps, auctions often skipped; hedges issuance with
  IRS and fixed/fixed cross-currency swaps. Smaller issuers syndicate a large first tranche (minimum listing EUR5bn).
- **Syndication**: spread guidance (e.g. "23-25bp over benchmark"), book-building, fixed-price reoffer, stabilisation. Pot deals
  (one book, formula fees) stop a syndicate bank inflating demand then dumping its allocation after stabilisation.
- **Supply arithmetic (EA)**: `NCR = gross supply - redemptions - free-float coupons - net change in ECB holdings`. 2026 EA net
  supply to the private market about EUR675bn (EUR338bn had the ECB reinvested instead of QT); 2027 NCR EUR619bn (EUR329bn without
  QT), gross a record EUR1,500bn, redemptions EUR997bn, net ECB change -EUR290bn; per country gross/NCR 2027 DEU 375/184, FRA
  373/155, ITA 350/102, ESP 187/59. French October redemptions EUR87bn (lowest since 2017). EMU-11 2026: EUR1,066bn issued YTD, EUR389bn
  left (75% complete, in line with the 3y average); Sep-Dec NCR EUR138bn (20% of the annual) (Citi, European Rates Weekly, 1 Oct
  2026; European Rates Strategy: Latest views, 20 Aug 2026). Rotation by issuer: France October NCR non-supportive then
  November most supportive; Spain the reverse; Italy flat then non-supportive in December. Remaining supply higher in notional but
  similar in DV01 means little extra duration to absorb. SSA funding completion rates (e.g. KfW 98%, CADES 100%, UNEDIC 100%,
  BPIFrance 52%, BNG 76%, Kuntarahoitus 73%) matter into Nov-Dec when year-end balance sheets widen SSA-EGB spreads.
- **EUR supply WAM**: EGBs about 10y slightly declining; EU 11.6y (lowest since 2020); other SSAs 7.7y (lowest since 2015),
  supportive for long-end swap spreads (Citi, A QT revolution, 17 Sep 2026). Weekly EGB supply typically EUR18-25bn.
- **Seasonality** (BofA Securities, Bond market seasonality explained, 6 Jun 2022): German 30s10s steepens in February (long-end
  syndications), spreads tighten into January-February syndications, 2s10s flattens in March/May on April coupon and
  redemption reinvestment.
- **Pre-supply concession**: Bunds sold off more than 6bp with 2s10s ~3.5bp steeper on no catalyst ahead of September supply,
  attributed to positioning and accounts paying back-end rates (Citi Markets, Euro Govies Commentary, 14 Aug 2026).
- **Taps and identifiers**: a tap may get a temporary ISIN for non-standard settlement (e.g. T+5), funged into the main line later.
  Aggregate outstanding by line, not by ISIN (Düring 2021).
- **CTD squeezes** are more common in Europe because open interest is large vs deliverable supply; Mar 2001 Bobl: CTD an old,
  illiquid Bund with small float, OI peaked at EUR57bn two weeks before expiry, CTD BNOC reached -70 cents, calendar widened
  (Burghardt 2005). Feb 2022 Bund repo squeeze: repo plunged after a hawkish ECB signal; if short-lived position for relative
  Bund cheapening (Huggins & Schaller 2024). Fitted Bund curve 7 Dec 2012: +2.5 cents per extra EUR1bn outstanding, bonds cheapen
  2.7 cents per year of issue age, deliverables richer (Schatz 3.6bp, Bobl 2.8bp, Bund 2.1bp, Buxl 2.4bp).
- **Expected specialness by maturity** (ABN Amro 2002, chart reading in Huggins & Schaller): German about 3.0bp at 5Y, 5.9bp at 10Y;
  Italian 2-2.5bp; French 1.0-1.3bp; Dutch 0.6-0.8bp; Spanish 0-0.5bp.
- **OTR premium by market** (Düring 2021): pronounced in US, Italy, Spain; smaller in France; none meaningful in DE/JP.
  Benchmark switches create fake slope and fly jumps (the 25 Jul 2018 two-year switch created fake 2s5s steepening and 5s10s
  flattening): use spline or constant-maturity series.
- **ECB QE constraints** (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022): capital keys; one-third issue/issuer limit
  from 2015; PEPP removed the one-third limit, minimum maturity 28 days, sub-IG eligible. Supras: ECB max 10% of portfolio in
  supras and 50% of any one supra issuer. Jun-Jul 2021 the ECB bought EUR134.7bn FR/DE/IT/ES vs EUR89bn net issuance.

## GBP (DMO and BoE)

- DMO publishes the annual remit in March (financing arithmetic: `funding need = CGNCR(ex) + redemptions + carry-forward`,
  funded by bills, NS&I and gilts) and a quarterly calendar with exact dates; auctions one or two a month, about GBP10bn a line,
  linkers (RPI, 3-month lag) roughly monthly about GBP6bn.
  Historical monthly seasonal averages of CGNCR(ex) outturns beat the official OBR monthly profile (Sep-Jan forecast error
  -GBP0.4bn vs OBR -GBP56.3bn); March CGNCR historically +GBP18-23bn vs OBR -GBP4bn. FY22-23 remit: CGNCR(ex) GBP83.0bn +
  redemptions GBP107.1bn + carry-forward GBP34.6bn; range GBP75-140bn; split Shorts 29%, Mediums 27%, Longs 30%, Linkers 14%
  (Citi, European Rates Weekly, 17 Mar 2022). The DMO does not hedge issuance with swaps; its size would dominate the market.
- **DMO long-end issuance-cut event study**: long-end share of net issuance cut from 28.4% (Apr 2022) to 9.1%; 12 instances;
  gilt curve flattened 2bp on average in 5 days; 5s/30s flattened 5bp on average in a 10-day window in 75% of instances;
  Nov 2022 maximum 35bp over 30 days; successive announcements had smaller effects (J.P. Morgan, Global Fixed Income Markets
  Weekly, 21-22 Aug 2026).
- **Low coupon vs high coupon**: UK retail is taxed on income not gains, so low-coupon gilts are tax-efficient and trade at much
  lower z-spreads. After-tax yield = gross yield adjusted for 40% tax on coupon (1/8% coupon: about 5bp tax a year). Maturing low
  coupons shrink the pool (four 1/8% gilts down to two) so scarcity builds. Trades: sell 4.125% 2027 / buy 0.125% 2028 on ASW
  (OIS z-spread), entry +1.8bp pick-up (10 Nov 2022), target -25bp, stop +12bp, closed -25.4bp Aug 2024; main risk: a new
  issue in the high-coupon leg's maturity accrues benchmark premium (BofA, Low coupon/high coupon Gilt spread trade hits target, 5
  Aug 2024; Liquid Insight: Will retail discover Gilts?, 10 Nov 2022). Later: sell 4.5% 2028 / buy 0.5% 2029 on z-spread entry -8bp,
  target -20bp, stop +4bp (BofA, UK Rates Viewpoint, 5 Sep 2024). Linker redemptions and the pace of bank reinvestment distort
  short-dated linker RV (BofA, 5 Sep 2024).
- **BoE QT** (all as published): QT auction clearing spread vs market mid turning positive = concession; first GBP20bn of active
  sales from the longest of a 2034-49 basket (UKT 1.5% Jul47 GBP7.1bn, part of 1.75% Jan49 GBP12.0bn), about GBP7mn/bp vs GBP65mn/bp
  total, next GBP20bn GBP13.8mn/bp; passive run-down of 2026-34 issues removes GBP222bn of front-end collateral which supports <5y
  and 20y+ ASW; active sales paused until at least April 2027 (Barclays, Global Rates Weekly, 2 Oct 2026). Redesign (Sep 2026):
  complete by Sep 2034; GBP120bn of gilts maturing beyond 2049 held permanently; remaining GBP368bn = passive GBP221.7bn + active
  GBP20bn a year of 2035-53 gilts; no sales below 9y; sales to the DMO (gilts cancelled via the National Loans Fund, an index
  implication); QT year aligned to the fiscal year restarting April 2027; ultras rallied (73s -18bp on the day), judged a one-off
  bull-flattening (Citi, A QT revolution, 17 Sep 2026). QT pace expected GBP50bn from GBP70bn (Oct26-Sep27), split 40/40/20
  shorts/mediums/longs; BoE estimates cumulative QT impact on the 10y at 20-30bp (from 15-25bp a year earlier) (Citi, European
  Rates Strategy: Latest views, 20 Aug 2026). Short-gilt sales went mostly to low coupons (July 2024 GBP1.1bn market value to 0.125% 2028),
  so the source "will slow to a trickle" at GBP100bn QT.

## JPY (MoF and BoJ)

- **Calendar**: JGBs issued monthly, size announced about a week before, coupon set near the when-issued yield on auction day;
  MoF FY2023 plan (JPY tn): 40y 0.7x6, 30y 0.9x12, 20y 1.2x12, 10y 2.7x12, 5y 2.5x12, 2y 2.9x12, TBs 50.7, JGBi 1.0,
  liquidity enhancement 12.0, total 190.3 (BofA, Japan Rates Basics, 24 Apr 2023). 2026-27: expected first 2y FRN JGB
  (JPY1.0-1.5tn), retail JGB sales reduce fixed-coupon need, liquidity taps 5-11y JPY650bn to 500bn, 2y/5y up to +JPY100bn a month,
  10y and super-longs unchanged with possible JPY100bn cuts (20y first) (Citi, Japan Rates Weekly, 2 Oct 2026). MoF
  preferred cutting super-long issuance to buybacks: "partially why 10s30s have been flattening since mid-2025" (Citi, GAA House
  Views, 21 Aug 2026).
- **Auction evaluation (MoF)**: bid-to-cover; tail = gap between the lowest-accepted (pro-rata) yield and the average successful yield (reported as a
  spread, so >= 0), fat tail = weak; a different quantity from stop-minus-WI; lowest accepted price vs consensus survey. Multiple-price for 2-30y, Dutch for 40y and linkers; WI trades from
  announcement. Overseas investors cannot bid directly.
- **BoJ rinban**: competitive auction where bids are desired yield spreads over the prior-day reference yield, highest yield
  accepted first. High bid-to-cover in rinban = strong selling demand (bearish JGBs), a fat tail = weak selling demand: the
  semantics of cover flip vs MoF auctions. April 2023 details (YCC fixed-rate ops) are outdated: structure only. Reading
  rinban: ops per month by bucket (2Q2023: 1-3y 4 ops JPY350-650bn, 5-10y 4 ops JPY475-875bn, >25y 3 ops JPY50-350bn).
- **Net supply**: `issuance - rinban (+/- not-settled/reduced) - redemptions`, by sector; market-held supply = gross issuance
  - redemptions - BoJ net purchases (gross less redemptions of BoJ-held bonds). BoJ net purchases falling raises market-held supply
  mostly below 10y: next year market-held JGBs +JPY65tn (outstanding +17tn, BoJ -48tn): <5Y +23tn, 6-10Y +28tn, 11-20Y +2, 21-30Y
  +3, 31-40Y -1; lifers' JGBs -8.6tn FY25 (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026). Monthly net
  supply projected JPY6.5tn (Q3-26) to JPY5.6tn (Q4-26) (BofA, Global Rates Weekly, 2 Oct 2026).
- **BoJ April 2013 QE**: the BoJ bought about 70% of gross issuance (more than net supply); operations of about JPY1tn each
  (JPY300bn in the long end) set against auctions of JPY2.3tn (10Y) and JPY700bn (30Y) looked too large for dealers to supply, so
  an initial rally became a sell-off; schedule cut 18 Apr and 30 May 2013 (Düring 2021). 2006 exit: liquidity withdrawn faster
  than injected, JGB yields rose from about 1.5% to 2%; weaker credits (sub-sovereigns) reacted first.
- **Seasonality**: March bull flattening on lifer fiscal-year-end super-long buying, April net selling; new-fiscal-year (April/
  May) buying; life-insurer target buying makes 20s30s bear-flatten or bull-steepen; the 10Y has no natural investor base (too long
  for banks, too short for lifers). <=10y JGBs may richen around futures rolls (BofA, Seasonality 2022; Düring 2021; Citi,
  CitiFX Wire Cheatsheet, Aug 2026). Japanese banks' JGB carry portfolios (maturity slightly longer than deposits) hit capital when
  2Y-5Y volatility rises; large banks sold intermediates.

## CAD, AUD, NZD, SEK, NOK, CHF

- **CAD**: net issuance negative in March, June, September, December; foreigners buy in October and sell in December (BofA,
  Seasonality 2022). Canada May/August rally despite issuance: supply seasonality mostly informs curves and spreads, not
  direction.
- **AUD**: May Budget/AOFM programme with lower net supply and Japanese new-fiscal-year buying (6 of the last 8 Mays) rallies ACGBs,
  10s20s steepens 88% of the time; June lowest net supply since 2013; July AOFM issues further out (10s20s steepens ~63%); 10y swap spread
  tightens in March as Kangaroo supply steps up and widens May-July as it eases (BofA, Seasonality 2022). Kangaroo and offshore
  AUD issuance swapped back narrows the (positive) AUD/USD basis; Australian banks issuing offshore widen it; 2014 issuance mix SSA 49%,
  financials 42%, corporates 9%; Q1 seasonally strong for SSA; the 10Y basis beta to Kangaroo flow had collapsed by 2024 (J.P. Morgan,
  Drivers of cross currency basis, 11 Mar 2015; Cross currency basis 4Q24 Outlook, 26 Sep 2024). RBA TFF maturities cut
  excess reserves by more than 50% from the early-2022 peak.
- **NZD**: tax outflows cut settlement cash from NZ$26.5bn to 24bn, moving the short NZIONA basis 5-7.5bp (Citi, STIRT Weekly,
  21 Aug 2026). New Zealand already sells QT bonds to its debt office.
- **SEK**: government bonds auctioned twice a month (Düring 2021). **NOK, CHF**: no supply or cash-flow material in the source
  library; ask for the debt-office calendar before building event windows.

## Cross-currency basis supply regressors (use in xccy-basis)

- EUR/USD intermediate basis, Libor era (J.P. Morgan 2015): `5Yx5Y = 0.01 (1Yx1Y)^2 + 0.93 (1Yx1Y) - 7.5 (3m MA EUR issuance by USD
  names) + 5.1 (3m MA USD issuance by EUR names) - 0.89`, R2 71%: widens ~7bp per EUR1bn/day of reverse-Yankee flow, narrows ~5bp per
  EUR1bn/day of euro-area USD issuance. Since Jan 2023: `1Yx1Y/5Yx5Y ESTR/SOFR basis curve = -0.23 (1Yx1Y basis) - 1.15 (1m MA
  Yankee issuance) - 8.27`, R2 57%; Yankee significant, reverse-Yankee not; hedge for front-end beta because the curve is
  directional (J.P. Morgan 2024). Samurai issuance widens the USD/JPY basis, peaks June-July; Japanese non-yen issuance abroad
  narrows it (July, September). Yankee/reverse-Yankee issuance stays high Oct-Nov and falls in December.
