# G10 operating frameworks and balance-sheet tools (detail)

Companion to [SKILL.md](../SKILL.md). The USD mechanics are in [usd_regimes_and_analogs.md](usd_regimes_and_analogs.md).
Non-USD coverage in the knowledge base is thin for CHF, SEK and NOK; each gap is marked. Levels are dated; pull current
values before use. Sources are cited by publisher, title and date in the body's References list.

## 0. The two frameworks

- **Floor system.** Reserves are abundant. Small changes in reserve quantity do not move overnight rates. The
  deposit rate is the operative tool and standing lending facilities are a secondary backstop. Floors became common
  after the GFC because of large-scale asset purchases and regulation that raised reserve demand (BofA, Global policy
  implementation: a short guide, 9 Jul 2025).
- **Corridor system.** Reserves are scarce, so small moves have a large rate impact. The central bank keeps the
  banking system short of liquidity, traditionally through reserve requirements, so that standing facilities are used
  (Düring, Fixed Income Trading and Risk Management, Ch.6). Pre-crisis scarce-reserves mechanics: the discount window
  sat at target plus 100bp, reserves were monitored every two weeks, and intraday balance management drove fed funds
  (Duffie, Dark Markets, 2012).
- **Symmetric corridor (Düring, Ch.6).** At least three tools: the centre supplies most liquidity, the
  floor absorbs excess (deposit facility), the ceiling covers shortfalls (lending facility). Simultaneous use of both
  standing facilities is "more concerning" because a bank with surplus is not lending to a bank that is short.
- **Asymmetric corridor (Düring, Ch.6).** Asset purchases from non-banks create surplus liquidity, so market rates
  get pinned to the liquidity-absorbing floor. Euro short-term rates have been below the deposit facility rate since
  the series was produced (textbook, Fig 6.2; chart not viewed).

## 1. Currency table

| Ccy / CB | Framework | Floor and ceiling as sources describe them | Balance-sheet tools | Gauges and dated facts |
|---|---|---|---|---|
| USD (Fed) | Floor with an IORB anchor and a soft RRP floor; SRF as a soft repo ceiling | IORB anchors EFFR; ON RRP floor for MMFs and GSEs; SRF minimum bid = top of range; discount window at top of range; swap lines at OIS + 25bp | QT ended late Dec 2025 (Conks); reserve-management purchases of bills (about $40bn front-loaded, then about $10bn a month in 2026); MBS reinvested into bills | EFFR-IORB, SOFR-IORB, TGCR-RRP, GCF-TPR, reserves/bank assets, RDE, LCLoR. See the USD reference file. |
| EUR (ECB) | Floor: deposit facility rate (DFR), the rate that steers the stance since the Sep 2024 operational-framework change (external); MRO = DFR + 15bp and MLF = DFR + 40bp. Marginal lending facility is the standing ceiling | BofA (Jul 2025) calls the MRO the ceiling; that is a summary, not the standing facility. Treat the MLF as the ceiling | QT: APP and PEPP run-off; net private-market supply about €675bn in 2026 vs about €338bn if reinvested (Citi, European Rates Weekly, 1 Oct 2026); 2027 NCR €619bn vs €329bn without QT (Citi's later 20 Aug 2026 note has €616bn: different vintages) | ECB QT ran at about €125bn a quarter in 2025 (JPM, XCCY 2H25). Reserve-demand curve: QT moves the system toward the steeper part; an MRR tweak could accelerate that by 4-5 months (Citi, STIRT Weekly, 14 Aug 2026). Securities lending and exempt tier anchored German repo 4-5bp below the DFR (Nordea, 5 Feb 2020). |
| GBP (BoE) | Floor. Bank Rate remunerates reserves. STR: one-week at Bank Rate against Level A collateral. ILTR: six-month, minimum spreads 3bp (Level A), 5bp (B), 15bp (C) over Bank Rate | Floor is the deposit (reserve) rate; the lending facilities bracket above | APF QT: passive run-off of redemptions plus active sales of 2035-53 gilts; QT paused until Apr 2027 (Citi, Higher yields, 24 Sep 2026); pace £50bn a year from £70bn was the expectation before the Sep 2026 decision (Citi, Aug 2026); £120bn of post-2049 gilts held permanently; gilts sold to the DMO and cancelled via the NLF | Reserves about £640bn to YE26, £615bn YE27 (BofA, Start of rates bite, 2 Oct 2026). PMRR £385-530bn (JPM XCCY 2H25). 1Yx1Y SONIA/SOFR = -0.1 x reserves (£bn) + 71.5, R2 84% (JPM XCCY 2H25): £10bn fewer reserves gives about +1bp. BoE estimate of cumulative QT effect on 10y: 20-30bp (Citi, Aug 2026). |
| JPY (BoJ) | Floor. Complementary deposit facility is the floor; complementary lending facility is the ceiling (BofA, Jul 2025) | Foreign official deposits pay JGB repo rate minus 5bp, or 0% on request (BofA, FX-Sofr, 31 Oct 2023) | BoJ QT raises the free float of JGBs; about 48% of JGBs owned by BoJ (JWS Macro, Sep 2025). A free-float rise of about 5pp would tighten fair-value 10y JGB swap spreads by about 3bp (Goldman, Global Rates Trader, 2 Oct 2026) | MoF intervention financing: T-bills (about $90bn at end-May 2025, now running low), FIMA repo (up to $60bn of UST), and about $160bn of deposits at the Fed's foreign RRP (Citi, Macro tapas, 7 Aug 2026). BoJ current-account reserves enter the 1Y USD/JPY basis model at -0.25bp per JPY1tn (JPM, Drivers of xccy basis, 11 Mar 2015). BoJ stopped its 3M USD operations in Apr 2014. |
| CAD (BoC) | Floor, a "flooridor". Operating band 30bp | Deposit rate 5bp below target; standing lending and overnight repo at target + 25bp; term liquidity facility up to 30 days at 1M CAD OIS + 35bp (BofA, Jul 2025; range 2.70-3.00 at that date) | Overnight repo is the main tool against upward CORRA pressure; a response was usually triggered when CORRA settled 5bp above target (Goldman, 2 Oct 2026). Reserve target CAD 50-70bn (Goldman, 2 Oct 2026) | Month-end FX-OIS swing of 40bp in Aug 2026 (Citi, STIRT Weekly, 7 Aug 2026). |
| AUD (RBA) | Floor. Overnight standing facility at target + 25bp; exchange settlement balances pay the cash rate minus 10bp (BofA, Jul 2025, partly legible) | RBA does not allow foreign official deposits (BofA, FX-Sofr, 31 Oct 2023) | Terminal funding facility (TFF) maturity drained more than 50% of excess reserves, widening the front-end basis and AUD FRA-OIS (JPM XCCY 4Q24). Speech "The Road to Ample" expected to affirm a reserve drain and smaller repo presence (Citi Sales and Trading, 21 Aug 2026) | BBSW about 10bp over OIS lifted bills-OIS (Citi, 7 Aug 2026). 1Y BOB stays 4-9bp and 6s3s 16-24bp (JPM XCCY 4Q24, 2024). |
| NZD (RBNZ) | Not covered beyond the points below | RBNZ does not allow foreign official deposits (BofA, FX-Sofr, 31 Oct 2023) | No balance-sheet facility detail in the sources | NZIONA/SOFR basis tied to settlement cash, about NZD 27bn (Citi, STIRT Weekly, 7 Aug 2026). |
| CHF (SNB) | **Gap.** No reserve, facility or balance-sheet material in the knowledge base. SNB policy path shown at 0% in Aug 2026 OIS tables only | | | Do not add SNB mechanics from memory without a cited source. |
| SEK (Riksbank) | **Gap for mechanics.** Only policy-path pricing in the knowledge base | | | SEK certificate auction left SEK 112bn of liquidity (Citi, 7 Aug 2026). |
| NOK (Norges Bank) | **Gap for mechanics.** Only policy-path pricing | | | Structural liquidity above NOK 150bn (Citi, 7 Aug 2026). |
| DKK (Danmarks Nationalbank) | Not covered beyond the points below | | | Current-account deposits about DKK 380bn, funding about -20bp FX-OIS (Citi, 7 Aug 2026). |

## 2. ECB reaction-function ladder (balance sheet last)

BofA, Global Economic Weekly: "The fog of war" (2 Oct 2026). Ranked from most used to least:

1. Tight financial conditions handled with short rates; guidance first.
2. Balance sheet used only for disorderly moves in speed or magnitude of spread.
3. QT fine-tuning, a high bar.
4. New LTROs or a structural securities portfolio, unlikely: they need banks to borrow about €40bn more a month,
   while under €40bn is borrowed across all operations at the time.
5. TPI for disorderly, unwarranted spread moves, with OMT as fallback.
6. A possible TPI-like tool for disorderly long-end moves.

Citi (1 Oct 2026) ranks the ECB levers by ease: push back on hike pricing; revisit QT or make reinvestments flexible
as with PEPP; TPI with a very high bar.

## 3. QT programmes and the duration question

- **BoE redesign (Citi, European Rates Weekly, 17 Sep 2026).** QT completes by Sep 2034. £120bn of gilts maturing
  beyond 2049 are held permanently (backing banknotes): no sales of 20y+ gilts and the free float is never restored.
  The remaining £368bn is a passive unwind of redemptions (£221.7bn) plus fixed active sales of £20bn a year of
  2035-53 gilts (£146.5bn), with no active sales under 9y. Sales go to the DMO and are cancelled through the NLF,
  aligned to the fiscal year from Apr 2027. The 17 Sep 2026 announcement moved 73s +18bp on the day; treat the
  one-off as a repricing, not a trend.
- **BoE modalities (Barclays, The urgency question, 2 Oct 2026).** Auction weighted-average spread (clearing vs market
  mid) turned positive, a concession. First £20bn of sales from the longest 2034-49 basket, about £7mn/bp against
  £65mn/bp for the whole programme. Repo operations about £220bn with a WAM of about 42 days. Passive rundown of 2026-34
  issues removes £222bn of front-end collateral: this supports under-5y and 20y+ ASW and leaves long gilts exposed
  to repo specialness.
- **BoE alternate path (Citi, 24 Sep 2026).** QT paused until Apr 2027, then £20bn a year. 10y gilt-Bund about 175bp,
  forecast under 150bp by mid-2027 on net-supply metrics.
- **ECB net-cash-requirement arithmetic (Citi, European Rates Weekly, 1 Oct 2026).** NCR = gross supply - redemptions -
  free-float coupons - (assumed) net change in ECB holdings, also expressed in DV01 terms (€mn per bp). Covered bonds:
  NCR = net supply - coupons - QE purchases. 2027 EMU-11 gross supply is a record €1.5tn; NCR falls to €616bn as
  redemptions rise to €997bn and ECB QT moderates (Citi, European Rates Strategy: Latest views, 20 Aug 2026).
- **BoJ.** Continued QT and halved JGB purchases raise market-held JGB supply; JPM expects 6-10y JGBs to
  underperform (JPM, Global Fixed Income Markets Weekly, 21-22 Aug 2026).
- **Divergence trade logic (Conks, A Global Compression, 1 Feb 2026).** Fed easing and reserve-management purchases
  against ECB and BoE QT and BoJ hikes give tighter USD cross-currency bases; the 3m EUR/USD basis turned positive
  through year-end 2025.

## 4. Cross-currency basis links to reserves (one line each)

- **Reserves-differential principle (JPM, 11 Mar 2015).** If reserves are greater in market A than B, the incentive to
  raise funding in A is weaker, so the basis moves against A.
- **Sign convention for the basis:** negative = USD premium, quoted as a spread added to the non-USD leg. A
  reserve surplus in USD tightens FX-SOFR (basis less negative); a shortage widens it (BofA, FX-Sofr primer, 31 Oct 2023).
- **1Y USD/JPY reserves model (JPM, 2015):** Fed reserves +0.31bp per $10bn (t 16.2); BoJ current-account reserves
  -0.25bp per JPY1tn (t -12.8); R2 about 60%. The source describes the BoJ effect as widening the basis by about
  0.25bp. Read this with the sign convention above: more BoJ reserves push the (negative) basis more negative.
- **2Y EUR/USD fair value (JPM, 2015):** 2Y basis = 1.90 x (Fed balance sheet - ECB balance sheet, % GDP) + 20.63 x
  (5th Eurodollar minus Euribor futures spread) - 9.43; R2 71%. Each 1% of GDP of ECB balance-sheet growth relative to
  the Fed widened the 2Y basis by about 2bp. The source warns the relation can turn non-linear. The 2015 vintage is
  old; re-estimate before use.
- **GBP (JPM, XCCY 2H25 and 4Q24):** the front-end basis is driven by BoE reserves, not relative policy. The
  regression of 1Yx1Y SONIA/SOFR on the policy spread had R2 67% in Jan-May 2024, 0% in Jun-Sep 2024 and 0% in 2025.
  The source names relative balance sheets (Fed vs BoE QT) as the driver, so the policy spread is not a safe regressor.
- **Basis overshoot in risk-off (JPM, 2015).** A 2008-11-style USD shortage is a different regime from a reserves
  differential. Do not use a reserves model during a dollar-funding shock.

## 5. Gaps and what to add

- CHF, SEK, NOK: no reserve, facility or balance-sheet mechanics in the knowledge base. Add a source before writing
  any mechanics for these currencies.
- NZD, DKK: thin coverage; only settlement-cash and funding levels.
- Pre-2020 euro-area reserve-demand regressions and the ECB's tiering rules are background, not current mechanics.
  The ECB's facility settings must be confirmed from the current policy document, not from this file.
