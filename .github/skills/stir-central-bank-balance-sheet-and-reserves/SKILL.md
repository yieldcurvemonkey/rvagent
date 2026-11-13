---
name: stir-central-bank-balance-sheet-and-reserves
description: 'Central-bank balance sheet, reserves and money-market plumbing for G10 rates RV. Covers reserve ampleness and scarcity gauges (EFFR-IORB, SOFR-IORB, TGCR-RRP, reserves to bank assets, reserve demand elasticity), the reserve identity (ON RRP, TGA, SRF, discount window, FIMA and foreign repo pool), QE and QT end, reserve-management purchases, debt-ceiling TGA rebuilds, and how these drive SOFR-FF, fed funds, bill-OIS, FX-OIS and cross-currency basis and swap spreads. Use when asked about QE or QT, quantitative tightening, reserves ample or scarce, reverse repo drain, TGA rebuild, standing repo facility stigma, repo above IORB, quarter-end or year-end repo spikes, the lowest comfortable level of reserves, reserve management purchases, or whether the Fed, ECB, BoE, BoJ, RBA or BoC will end QT or add bills. Bill-side debt-limit trades: stir-bills-and-money-market-spreads.'
---

# Central-bank balance sheet and reserves

Central-bank liabilities (reserves, ON RRP, the TGA, currency) set how much cash banks hold. That sets where overnight
rates sit inside the administered corridor. With abundant reserves, repo and fed funds trade near the administered
rates and small reserve moves barely matter. With scarce reserves, the same move reprices funding sharply. This skill
covers the identity that links the balance sheet to reserves, the gauges that show which regime is live, the drains
(TGA rebuilds, bill supply) and policy responses (QT end, reserve-management purchases, technical adjustments), and
how each feeds front-end spreads and cross-currency basis. It pays when a QT stop, a TGA rebuild or a debt-limit
resolution moves reserves faster than the market has priced.

## When to use

- Pricing SOFR-FF, fed funds vs IORB, SOFR vs IORB, bill-OIS, an OIS stub or year-end fed funds around a QT end, a
  balance-sheet announcement or a large TGA move.
- Deciding whether repo pressure is scarcity or a reporting-date friction (quarter-end, year-end, mid-month settlement).
- Forecasting reserves, ON RRP and the TGA over 1-12 months with the liability identity and bill supply.
- Mapping a debt-limit episode (extraordinary measures, X-date, resolution rebuild) to funding spreads.
- Cross-currency (FX-OIS, xccy) basis against central-bank reserve differentials, or GBP, EUR, JPY, AUD and CAD
  balance-sheet tools and QT programmes.
- Swap-spread or long-end RV where QT, purchases or Treasury buybacks are the stated driver.

Not for: repo segment mechanics ([stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md)), bill
and MMF flows ([stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md)), policy-meeting
pricing ([stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md)), or how SOFR and EFFR are
fixed ([stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md)).

## Conventions (read first)

- **Spreads are rate minus rate, in bp.** EFFR-IORB = EFFR minus IORB (negative = reserves abundant on the historical
  scale). SOFR-IORB = SOFR minus IORB. SOFR-FF = SOFR minus EFFR (positive = SOFR above fed funds). TGCR-RRP = TGCR minus
  ON RRP rate (positive = excess collateral). GCF-TPR = interdealer GCF minus tri-party.
- **Futures-style "SOFR/FF" is the opposite sign.** BofA and Citi write the futures-style spread as SOFR/FF meaning FF
  minus SOFR, so it is negative when SOFR is above FF. Convert with SOFR-FF = minus (SOFR/FF). Check the sign against the
  note's own words: "SOFR/FF tightens" after a debt-limit resolution means SOFR rises against FF.
- **Identity check:** SOFR-FF = (SOFR-IORB) minus (EFFR-IORB). Example, 3 Oct 2025 prints: +3 minus (-6) = +9bp.
- **Units:** rates in %, spreads in bp, balances in $bn (same unit in every identity).
- **Levels go stale.** Every administered rate, facility size, balance and threshold here is a dated vintage. Pull the
  current values from the data before use. Sources disagree on several levels by a few bp.

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Overnight fixings: EFFR, OBFR, SOFR, TGCR, BGCR, IORB, ON RRP rate, SRF rate, discount-window rate | `rate_fixings` (indices in `rate_indices`) | daily, at least 3y; final prints | Use the final print. Policy rates are rows with `fixing_date` = effective date. |
| Repo by segment: tri-party, interdealer (GCF), cleared bilateral (DVP) | `repo_rates` | daily, at least 2y | Needed for GCF-TPR and cleared-minus-tri-party. |
| Balance-sheet aggregates: Fed assets, currency, TGA, ON RRP, foreign RRP pool, reserves, bank assets, custody holdings | `macro_series` | weekly or daily releases, vintage-stamped | Series ids follow `<CC>-<AGG>` (`US-TGA`, `US-RESERVES`; unit `ccy_bn`). The script expects a wide CSV that the adapter builds from these. Use first-release vintages for backtests. |
| Bill and coupon supply | `auctions` | per auction | Net bill supply = issuance minus maturities, from cash flows, not offering sizes. |
| Policy-meeting dates and decisions | `cb_meetings` | per meeting | Date-match QT ends and technical adjustments. |
| Cross-currency and tenor basis | `basis_swaps` | daily, at least 3y | `spread_bp` on `leg_a`; the sign convention is in the table. |
| Calendars: month, quarter and year-end, tax dates, settlement days | `calendars` | multi-year | Reporting-date windows are the main confound. |

If an input is missing, ask the user or hand off to [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).
Never invent balances or rates. For supply, use cash flows, not offering sizes.

## Method

### 1. Reserve identity: forecast the drain before the market does

Reserves = Fed total assets - currency - TGA - ON RRP - foreign RRP pool - other liabilities and capital.

- All else equal, +$1 in the TGA, ON RRP, foreign RRP or currency is -$1 of reserves. Asset changes come from SOMA:
  QT lowers assets, and so reserves, unless the TGA or RRP absorbs the change.
- Closure check (BofA, Eliminating IORB, 13 Jun 2025 vintage): assets 6,728 minus currency 2,390, TGA 277 and ON RRP 576
  leaves 3,485. Printed reserves are 3,430, so other liabilities and capital are 55. A residual that does not close
  means a series is stale or mis-mapped.
- Drain order: the TGA rebuild and bill issuance drain ON RRP first and reserves second (Conks, Plumbing Notes, 9 Jul 2025).
  Reserves fall in earnest once RRP is near zero. Conks puts the "fireworks" point at about $500bn of reserves, including
  neutralised RRP, being used up.
- Pure vs neutralised: reserves parked in ON RRP are neutralised liquidity. After RRP is empty, every QT dollar is a pure
  reserve drain (Conks, Reckoning Part I, 9 Sep 2025).
- Forecast the TGA on its rebuild path, not as a step. Averaged over seven 2013-2023 episodes, the mean time to close
  half the gap is 28 business days and all of it about 51; the mean share closed at day 20 is 49% (BofA). The two
  averages are taken differently and dispersion is wide (2017: 112% at day 20; 2019: 0%), so use a range, not a schedule.
  See the [USD reference](references/usd_regimes_and_analogs.md).
- While ON RRP is positive, a TGA rise or bill issuance first drains RRP. Only the part that exceeds the RRP balance
  (or that MMFs cannot fund from RRP) comes out of reserves.

### 2. Corridor map: where each rate sits

- **Floor vs corridor.** Floor system (abundant reserves): small reserve moves do not move rates; the deposit rate is the
  tool. Corridor (scarce reserves): the same move has a large rate impact. Use the regime tests in Method 3 to see which is live.
- **USD ordering in normal times, highest to lowest** (Conks, 2024-25 notes): FIMA repo rate (public offshore ceiling);
  swap-line rate at OIS + 25bp (private offshore ceiling); FX-implied dollar rate; SRF rate (ceiling for secured repo) and
  discount-window rate (onshore ceiling for EFFR); IORB; EFFR; secured complex (GCF, then SOFR, then tri-party); foreign repo
  pool rate (public floor); ON RRP (private floor for SOFR, TGCR and EFFR); DVP specials below the floor. The sources
  stress that each ceiling and floor holds "in theory, not always in practice".
- **Local jaws** are the target range (SRF upper, ON RRP lower). **Global jaws** are the full corridor, FIMA down to ON RRP.
- **The SRF is an impaired ceiling.** Causes given in the sources: stigma; settlement timing (about 70% of trading happens
  between 7:00 and 8:30am, before morning SRF cash settles by 9am); no central clearing, so no netting; haircuts against about 0% in private markets; and
  dealers needing repo up to about 25bp over the top of the range to justify on-lending. The NY Fed (Perli, Nov 2024) says
  it is meant to cap EFFR, "not repo rates". Sell-side notes call it a soft repo ceiling. Use the observed share of SOFR
  volume above the SRF rate, not the design intent.
- **ON RRP is a leaky floor.** Counterparty cap $160bn per fund per day. Many lenders have no access (Treasury-only funds,
  corporates, non-2a-7 funds). MMFs accept a discount to keep dealer relationships. Cash returns late. RRP can stay
  positive for reasons unrelated to scarcity: counterparty limits, quarter-ends and year-end window dressing.
- **IORB** anchors EFFR. Non-banks cannot earn IORB, so GSEs lend below it. Technical adjustments are usually 5bp. The Fed
  signalled concern when EFFR traded within 5bp of the top of the range (Barclays, US short interest rate primer, Jan 2025).
- Other G10 corridors and their facilities are in the [G10 reference](references/g10_operating_frameworks.md).

### 3. Regime tests: read four gauges together

No single gauge decides the regime. Compute these together and date-stamp the vintage used.

| Gauge | Definition | Reading (sources' thresholds) |
|---|---|---|
| EFFR-IORB (bp) | EFFR minus IORB | Negative = abundant (about -7bp through 2022-25). Positive = scarce. 0 is the warning line. |
| SOFR-IORB (bp) | SOFR minus IORB | Above 0 = banks deploying reserves into repo, "reducing liquidity elsewhere". A reading above about +5bp is repo pressure. |
| TGCR-RRP (bp) | TGCR minus ON RRP rate | Below 0 = cash in excess (Citi: TGCR at or 2-3bp below RRP on two days signals abundant cash). +5 to +15bp = excess collateral, the 2025 range, with a YE2024 spike of about 25bp. |
| GCF-TPR (bp) | Interdealer GCF minus tri-party | Up = dealer balance sheets tight. Typically 0-10bp, spikes near 60bp. |
| Liquidity ratio | (reserves + ON RRP) / bank assets | Above 13% abundant (some editions 14%); 11-13% ample; below 11% scarce. Soft bands. |
| RDE | Change in FF-IORB (bp) per 1% of bank assets of reserves | Near 0 = ample. Increasingly negative = scarce (about -1.5 in 2019-20). |
| Cleared repo above IORB | Share of cleared bilateral volume trading above IORB | Close to 100% in 2019 scarcity; peak about 45% in mid/late 2024; about 10% at the end of the sample (Barclays, Jan 2025; read off a chart). |
| Reserves vs LCLoR | Reserves minus the lowest comfortable level | LCLoR estimates run $2.2-2.9tn across vintages (Fed about $2.7tn and Conks about $2.9tn in late 2025). |

Decision rules:

- **Scarcity is confirmed** only when EFFR-IORB and SOFR-IORB stay positive beyond a reporting date and ON RRP is near
  zero. A quarter-end spike alone is a friction, not scarcity (Conks, Oct 2024; Perli, Nov 2024).
- **Canary sequence** (Conks, Reckoning Part II, 30 Sep 2025): (1) SOFR above IORB, when large clearers divert reserves
  into repo; (2) EFFR rising above IORB; (3) EFFR above the SRF minimum bid. Early SRF bids above the minimum and
  daylight overdrafts at smaller banks are stress signals.
- **Excess cash vs excess collateral.** Excess-collateral regimes "have proven to be short and spicy" (Conks, QT Enigma, Oct 2025).
- **Stress** = EFFR-IORB, SOFR-IORB and SRF take-up moving together. Repo spiking with EFFR flat is a friction (Conks, Oct 2024).

### 4. ON RRP, bills and the drain

- **Bills drain RRP.** Empirical slope: change in ON RRP ≈ -0.52 x change in net bill supply ($bn), since Aug 2023, R2 0.20
  (BofA, Funding notes, 8 Aug 2025). Citi uses an 80% beta; Conks argues about half. Report the range, not one value.
  Implemented as `rrp_change_from_net_bills`.
- **MMF exit threshold.** MMFs leave ON RRP when 1m bill-to-fed-funds OIS spreads reach 2-5bp (BofA, 8 Aug 2025).
- **Low RRP is a regime signal.** Below about $500bn of ON RRP, SOFR pressure is non-linear and the fit is steeper. Above it,
  SOFR and TGCR anchor near ON RRP and fed funds has room to rise against SOFR (BofA, US Treasury repo primer, 7 Jul 2025).
  Do not extrapolate the calm of the large-RRP regime.
- **RRP at zero is not a doom signal on its own.** It means spare cash is invested in non-Fed assets. The next level of the
  repo hierarchy takes over: banks lend reserves into repo once repo pays more than IORB (Conks, Feb 2025).
- **TGCR and IORB.** TGCR trades closer to IORB once RRP is zero, because bank portfolios become the marginal lender
  (Citi, FX Basis Quarterly, Dec 2024).

### 5. TGA and the debt-limit cycle

Sequence (BofA, Funding and debt limit, 27 Jun 2025; Conks, Blindspot Part I, 23 Jan 2025):

1. **Limit binds.** Extraordinary measures (about $300bn or more of capacity) and a TGA drawdown. Bill supply falls, MMFs
   move back into ON RRP and reserves rise. Conks calls the inflated reserves and RRP a "liquidity mirage".
2. **Tax hump.** Mid-April receipts lift the TGA for a while.
3. **Resolution.** The TGA rebuild plus a bill deluge drains RRP, then reserves, and tightens funding. SOFR rises against
   FF and IORB. Treasury can also suspend issuance piecemeal (2017: two months, Sep-Dec), which delays the rebuild.

- **Analog choice.** Match on limited ON RRP buffer and similar percentage bill-supply growth. Exclude 2021 and 2023 (large
  buffers). Averages after the 2017-19 resolutions: SOFR-FF +7.7, +4.4, +5.1bp at 1m, 3m, 6m; SOFR-IORB +3.0, +5.1, +5.7;
  1m bill-OIS -7.5, -4.0, -9.3 (converted to this skill's sign convention; see section 4b of the [USD reference](references/usd_regimes_and_analogs.md)).
- **Date risk.** A later resolution, a slower rebuild or a suspension moves the drain. Debt-limit trades carry timing risk.
- **Current outlook (vintages that disagree).** Citi, 21 Aug 2026: limit about $41.1tn against about $39.9tn of debt
  subject to it, X-date likely Q4 2027. Citi, 2 Oct 2026: limit "expected to bind in Q1/Q2 2027". State which vintage you use.

### 6. QT end, reserve-management purchases and "not QE"

- **The Fed watches fed funds, not repo.** Officials will only consider ending QT when EFFR starts moving up with SOFR
  (Conks, Oct-Dec 2024). Front-run through a narrowing IORB-EFFR, not through SOFR alone. The announcement effect is often
  bigger than the mechanical one.
- **Reserve-management purchases (RMPs/RMOs)** add reserves to offset non-QT drains. They are bill purchases with no intent
  to absorb duration, so they are not QE (Conks, It's Not QE, 9 Nov 2025). Sizing from the sources: Conks put RMOs at
  $20-30bn a month needed in late 2025. BofA put post-QT bill buying at $300-450bn a year, from MBS reinvestment
  $120-240bn, liability growth about $200bn (may lag) and reserve backfill about $150bn (less certain). The printed
  components sum to more than the printed total, so quote the total with that caveat (BofA, Bill demand gap, 22 Oct 2025).
- **Backfill sizing.** One BofA vintage put a TGCR-below-IORB regime at reserves of about $3.15tn, a backfill of about
  $150bn. Re-derive with the current LCLoR and liquidity ratio.
- **Treasury buybacks are not QE.** They are bill-funded, add no durable reserves, and the 30y yield effect in Aug 2026
  had a half-life of about one day (JPM, FX Markets Weekly, 21 Aug 2026; Financial Times, 20 Aug 2026).
- **QE is a vol sale.** QE that buys convexity-bearing assets without delta hedging sells implied vol. BofA's Bassman (2010)
  equated the Fed's $1.25tn of MBS purchases to $625bn of 3y x 10y straddles sold. Treat start, stop and QT announcements as vol events
  (see [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md)).
- **Non-USD QT programmes** (BoE redesign, ECB net cash requirement, BoJ free float, RBA and BoC reserve tools) are in
  the [G10 reference](references/g10_operating_frameworks.md).

### 7. Mapping reserves to front-end spreads

- **SOFR-FF.** Since the pandemic, reserves are the main driver and bills alone are insignificant, but bills capture
  non-linear moves, so keep them in before a TGA rebuild. Citi's weekly-change betas for 2021-25 are about -0.38 per $100bn
  of reserves for SOFR-FF. Full-sample betas are much larger, so do not pool regimes.
- **SOFR-IORB.** Log-liquidity fits (see the [USD reference](references/usd_regimes_and_analogs.md)). The slope is steep when liquidity is scarce (R2 0.73 in the scarce period) and near zero when abundant (R2 0.01-0.17). A flat fit in the current regime means do not extrapolate.
- **EFFR** is sticky: about 7bp below IORB in 2022-25, because foreign banks borrow fed funds to earn IORB and FHLBs
  lend (BofA, Monthly rates models, Aug 2025). Forecast fed funds with low conviction.
- **Bill-OIS.** Use the supply flow (three-month change), not the stock. The bill-share-of-debt level is only loosely
  correlated with spreads (Barclays, Jan 2025).
- **FX-OIS and xccy basis.** A reserve surplus tightens the USD basis; a shortage widens it (BofA, FX-Sofr primer, Oct 2023).
  Relative balance sheets (Fed vs ECB, BoE or BoJ) drive the basis more than policy spreads. See the
  [xccy-basis](../xccy-basis/SKILL.md) skill for the basis itself.
- **Swap spreads.** Central-bank excess reserves shift interbank funding and term supply. Citi's 2019 estimate: $250-400bn
  of QE would widen 30y spreads by 2-5bp (Citi, All it takes is a little push, 4 Oct 2019).
- **Macro fair value.** Non-economic buying (QE, FX-hedge-driven foreign demand) breaks Taylor-type fits. Add the Fed balance
  sheet as a regressor (BofA, Monthly rates models, Apr 2025).

### 8. Quarter-end and year-end premia

- **FF year-end premium.** Monthly fed funds averages for Nov, Dec, Jan and Feb separate the Dec and Jan FOMC steps from
  the year-end premium. The inversion is in `year_end_premium`. Its day-count weights depend on the FOMC calendar (days
  at the old rate in Dec and Jan; defaults 11 and 29 are the Dec 2019 and Jan 2020 meetings), so set them for the year. Citi's 2019 fade structure had no FOMC exposure and a
  realised maximum year-end drop of -2.65bp, against an implied -4.5bp that was historically rare.
- **Repo normalisation lags.** Repo can take several days to normalise after quarter-end, because trimming balance sheet is
  easier than rebuilding it under daylight overdraft charges (Barclays, Jan 2025).
- **GSIB dieting** shows up in short-dated cross-currency trades at year-end, much less in repo, which is averaged in the score.

### 9. G10 at a glance (short; full table in the reference)

| Ccy (CB) | Framework | Reserve tools and status (date-stamp) | Gauges |
|---|---|---|---|
| USD (Fed) | Floor with IORB anchor; soft ON RRP floor; soft SRF ceiling | QT ended late 2025; RMPs paused or announced to end in 2026 (vintages conflict) | EFFR-IORB, SOFR-IORB, TGCR-RRP, liquidity ratio, RDE |
| EUR (ECB) | Floor at the deposit rate (DFR, the steering rate since the Sep 2024 framework change; MRO = DFR + 15bp, MLF = DFR + 40bp (external)); MLF is the standing ceiling | APP/PEPP run-off; net private supply about €675bn in 2026 vs €338bn without QT (Citi, 1 Oct 2026) | Excess liquidity, €STR vs DFR, German GC vs DFR, EURUSD basis |
| GBP (BoE) | Floor; Bank Rate remunerates reserves; STR and ILTR | QT paused to Apr 2027, then £20bn a year of active sales; £120bn of post-2049 gilts held permanently | SONIA vs Bank Rate, STR usage, 1Yx1Y SONIA/SOFR vs reserves |
| JPY (BoJ) | Floor (deposit facility floor; lending facility ceiling) | BoJ QT raises JGB free float, tightening 10y swap spreads (Goldman, 2 Oct 2026) | JGB free float, USD/JPY basis |
| CAD (BoC) | Flooridor, 30bp operating band | Standing repo and term liquidity facility; reserve target CAD 50-70bn | CORRA vs target |
| AUD (RBA) | Floor; exchange settlement balances pay cash rate minus 10bp | TFF maturity drained over half of excess reserves (JPM, 4Q24) | BBSW-OIS, bills-OIS |
| NZD, CHF, SEK, NOK, DKK | Thin or no coverage in the sources | See the reference section 5 | Do not add mechanics without a source |

## Worked examples

1. **Liability identity (BofA, Eliminating IORB, 13 Jun 2025).** Assets 6,728, currency 2,390, TGA 277, ON RRP 576. Reserves
   = 6,728 - 2,390 - 277 - 576 - 55 (other) = 3,430. A $100bn rise in the TGA that RRP cannot absorb (RRP near zero) takes reserves to about
   3,330 with all else equal.
2. **Regime read, 3 Oct 2025 (Conks, Takeoff Begins, 6 Oct 2025).** SOFR 4.18, TGCR 4.16, IORB 4.15, EFFR 4.09, ON RRP
   4.00. Gauges: SOFR-IORB +3bp, EFFR-IORB -6bp, SOFR-FF +9bp, TGCR-RRP +16bp. Reserves $2,966bn sit above both LCLoR
   estimates ($2.9tn Conks, $2.7tn Fed), "not breached". Reading: repo above IORB with EFFR below it is a repo-pressure
   regime, not fed-funds scarcity. Confirm with EFFR-IORB above 0 before calling scarcity. The script reproduces these gauges.
3. **Repo pressure without fed-funds scarcity, 23 Oct 2025 (Conks, 26 Oct 2025).** SOFR 4.24 (SOFR-IORB +9bp), EFFR 4.11
   (EFFR-IORB -4bp), reserves $2,933bn, ON RRP $2.4bn, liquidity ratio about 12% (ample band). The source's monitor
   reads SOFR-IORB "reached" and EFFR-IORB "not exceeded", with stress "mild".
4. **ON RRP drain from bills (BofA, Funding notes, 8 Aug 2025).** Net new bills of $100bn: RRP falls by about $52bn (slope
   -0.52). Citi's 80% beta gives -$80bn; Conks' half-drain gives -$50bn. While RRP absorbs the drain, reserves are unchanged.
   Once RRP is near zero, the same $100bn comes out of reserves.
5. **TGA rebuild pace (BofA, Short July SOFR-FF, 30 Jun 2025).** On average 49% of the TGA gap closes in 20 business days,
   60% in 30 and 100% by about day 51 (mean time to 100%). With ON RRP near zero, a $300bn gap therefore drains about
   $150bn of reserves by day 20 and about $180bn by day 30, with wide dispersion (2017 closed 112% by day 20; 2019
   closed 0%). The day-20 and day-28 figures (49% vs 50%) come from different averages and are not a smooth schedule.
6. **Debt-limit trade structure (BofA, Funding and debt limit, 27 Jun 2025).** Short the October 2025 futures-style SOFR/FF
   spread at -4bp, target -8bp, stop -1bp. In this skill's convention: SOFR-FF entry +4, target +8, stop +1. Rationale given:
   4-5bp of tightening after resolution; the position owns a larger SOFR spike. Historical trade, not a recommendation.
7. **Year-end premium split (Citi, Fixing the plumbing, 30 Sep 2019).** Given fed funds month averages for Nov, Dec, Jan
   and Feb, `year_end_premium` returns the Dec step, the Jan step and the year-end premium. The published inverse weights
   are 31/29 and 2/29 for the January terms and 31/20 and 11/20 for the December terms.
8. **September 2019 anatomy (Conks, Repo Defensive Part I, 20 Oct 2024).** Reserves fell from about $2.5tn to $1.3tn under QT.
   The 16 Sep tax date, about $80bn of coupon settlements and top-four bank retreat pushed some SOFR prints to nearly four
   times the 2.25% upper bound. The Fed responded with daily repo up to $75bn, technical adjustments and $60bn a month of
   bill purchases. Use it as the template for "reserves plus settlement plus tax date".

9. **QT absorbed by RRP and TGA (BofA, Rates teach-in, 4 Jul 2025).** From QT start (25 May 2022) to 2 Jul 2025, Fed assets
   fell $2,250bn (UST -1,557, MBS -569). Against that, ON RRP fell $1,785bn and the TGA $467bn, currency rose $119bn, and
   reserves rose $32bn (other items about -149 by difference). QT only drained reserves once RRP was empty, so stable
   reserves during QT reflected neutralised cash, not abundance.

## Signals & interpretation

- **EFFR-IORB above 0 persisting beyond month-end** means scarcity. The Fed's stated reaction is to add reserves once
  EFFR is above IORB (Conks, Money Market Update, 2024-25). "Three or more days" is a house persistence choice.
  Expect technical action or bill buying. Confirm with the liquidity ratio and RDE before acting.
- **SOFR-IORB above 0 on a non-reporting date while ON RRP is below about $500bn** means repo scarcity is building.
  Watch TGCR-RRP for the move from excess cash to excess collateral.
- **TGCR-RRP below 0 with ON RRP above about $500bn** means cash excess. SOFR runs low in the range and SOFR-FF can be
  zero or negative. Do not position for SOFR-FF to widen until ON RRP has drained.
- **Liquidity ratio below 11%, or RDE increasingly negative**: scarce regime. QT end and bill buying become likely.
  Above 13%: abundant, and reserve moves barely change rates.
- **QT end is priced when EFFR starts rising toward IORB.** A narrowing IORB-EFFR is the tell.
- **A TGA rise of $100bn or more in a month with RRP near zero** takes reserves down roughly one-for-one. Expect SOFR-IORB
  to rise and SOFR-FF to widen within days.
- **Confirm a stress call with four signals together:** SRF take-up and bids above the minimum, daylight overdrafts at
  smaller banks, rising IBDA volumes, and swap-line draws. Quarter-end alone is not a stress call.
- **House rule:** do not state a point forecast from a regression with R2 below about 0.2. Give a range.

## Pitfalls

- **The same reserves can be ample on one date and scarce on another.** Tax dates, coupon settlements and GSIB year-end
  move demand. Model reserve demand as time-varying, never as a fixed threshold.
- **Sign flips reverse trades.** The futures-style "SOFR/FF" in sell-side notes is FF minus SOFR. Check against the note's text.
- **Debt-limit distortion.** Inflated reserves and RRP during a drawdown make scarcity models look loose ("liquidity mirage").
  Do not read RDE or reserve levels at face value in those windows.
- **Regime-dependent betas.** The 2015-19 and 2020+ fits differ. Regression signs can flip. Check sign stability before
  trusting a fair value.
- **The fourth SOFR-IORB regime is unidentified.** Its equation has three different values across editions (-45.02, -11.58
  and +8.92 in the log slope), with R2 0.01-0.12. Do not forecast from it.
- **Levels regressions on trending series overstate fit.** Daily or monthly levels of reserves and spreads are
  autocorrelated, so R2 and t-statistics from the log fits are inflated. Prefer changes (weekly betas) for inference
  and use Newey-West errors if you must regress levels.
- **Look-ahead in backtests.** LCLoR estimates, regime weights and bank-asset denominators are revised or published
  late. Use first-release balances and only the threshold vintage available at the time.
- **Liquidity-ratio definition.** Some editions put reserves alone over bank assets, others reserves plus ON RRP. The
  13% and 11% bands are quoted for the RRP-inclusive form (Conks, 26 Oct 2025). Compare like with like.
- **Small analog samples.** The post-resolution averages rest on about two independent episodes (2017-18 count as one,
  plus 2019, which Fed intervention distorted). Treat them as an order of magnitude, not an estimate.
- **Thresholds are soft.** The abundant line is 13% or 14%. LCLoR runs $2.2-2.9tn. The ample band is 10-13% or 11-13%.
  Use the latest vintage and say which.
- **The SRF is not a hard ceiling.** SOFR can exceed the top of the range at quarter-end with little take-up. Sep 2024: more
  than $500bn traded above the SRF minimum bid (NY Fed), or more than $600bn (Conks), with take-up of about $2-3bn.
- **Benchmark dislocations.** The OFR tri-party rate printed below ON RRP from 18 Jul 2024 on one collateral sub-rate while TGCR was normal.
  Decompose by collateral sub-rate before reading a benchmark move as a reserve signal (Conks, Repo Market Dislocation, Aug 2024).
- **SOFR composition.** Adding uncleared trades shifts SOFR only if its distribution shifts. Barclays estimates about +1bp
  from clearing. Do not assume a large mechanical move.
- **Conflicting 2026 policy vintages.** RMP status (paused, to end, or $10-20bn a month possible) and the debt-limit binding
  date differ across notes. Confirm against the latest official statement.
- **Buybacks, FIMA repo and foreign official deposits are not QE.** Do not count them as reserve injections without checking
  the H.4.1 release.
- **Regulatory reserve demand** (LCR, SLR, GSIB) drifts. Catalysts are slow and their outcomes were uncertain at the time
  of the sources. Do not model a sudden switch.
- **CHF, SEK and NOK have no balance-sheet mechanics in the knowledge base.** Do not write them from memory.

## Output

Return one block per request, with every level date-stamped:

1. **Regime line:** abundant, ample or scarce, with the four spread gauges (latest print, 20-day change), the liquidity
   ratio and the RDE vintage.
2. **Liability bridge:** starting reserves; changes in TGA, ON RRP, currency and other; ending reserves; residual shown.
   Name the forecast vintage.
3. **Drain path:** net bill supply and TGA path, ON RRP change as a range (beta 0.5-0.8), reserves path, and the date of the
   first scarcity-threshold breach if any.
4. **Front-end read:** SOFR-FF, SOFR-IORB and FF-IORB direction and size over 1, 3 and 6 months from the regime-appropriate
   fit. State confidence, and mark it low if the regime is unidentified.
5. **Signal and hand-off:** the trade or risk, entry, target and stop in SOFR-FF bp, the QT-end or debt-limit date risk,
   and a hand-off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts

- [`scripts/reserve_monitor.py`](scripts/reserve_monitor.py): reserves from the identity; ampleness ratio and zone; spread
  gauges in bp; ON RRP change from net bills; log-liquidity fit; year-end premium split. `python -I scripts/reserve_monitor.py --selftest`
  checks known answers (Jun 2025 identity, 3 and 23 Oct 2025 spreads, a synthetic log fit with known parameters, a
  year-end round trip on two FOMC calendars, and NaN handling: missing data gives `n/a` or `<NA>`, never "ample"). `python -I scripts/reserve_monitor.py --wide PATH` prints the latest gauges from a wide CSV
  (columns in the script's docstring).

## Related skills

- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo segments and SRF and RRP mechanics in detail
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bill supply, MMF flows and bill-OIS
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): policy-meeting pricing around QT ends and technical adjustments
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): how SOFR and EFFR are built and fixed
- [stir-futures-rv](../stir-futures-rv/SKILL.md): SOFR-FF and fed funds futures spreads
- [xccy-basis](../xccy-basis/SKILL.md): FX-OIS and cross-currency basis drivers
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): SLR, LCR, GSIB and NSFR effects on reserve demand
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): repo specialness and cash-futures basis
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread drivers from QT and purchases
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): reaction functions and balance-sheet tools
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): Treasury financing, debt limit and term premium
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): QT runoff as net supply, auctions and buybacks
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): QE as a volatility event
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used in Inputs
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): writing up a trade idea
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): tenor and index basis, including SOFR-FF.

## References

- Conks (Monetary Mechanics) - Plumbing Notes: The Fed's Reckoning, Part II (30 Sep 2025): jaws framework, RRP half-drain rule, canary sequence.
- Conks (Monetary Mechanics) - Plumbing Notes: The QT Enigma, Money Market Commentary with chartbook (26 Oct 2025): regime and stress monitors, Fed liquidity ratio, RDE, QT-end policy options.
- Conks (Monetary Mechanics) - Plumbing Notes: It's Not QE (9 Nov 2025): RMOs vs QE, reserve drains and sizing.
- Conks (Monetary Mechanics) - Plumbing Notes: The Fed's Repo Defensive, Part I (20 Oct 2024): Sep 2019 anatomy and the Fed's response template.
- Conks (Monetary Mechanics) - Money Market Blindspot, Part I (23 Jan 2025): debt-limit sequence and the liquidity mirage.
- NY Fed, Roberto Perli - Speech: Facing Quarter-End Pressures: Understanding the Repo Market and Federal Reserve Tools (12 Nov 2024): ample-reserves framework, SRF design limits, segment map.
- BofA Global Research - US Rates Primer: Fed policy plumbing '25 edition (Mark Cabana, Katie Craig, 8 Jul 2025): corridor, leaky floor, SRF, technical adjustments, liability identity.
- BofA Global Research - US Treasury repo primer: 2025 edition (Mark Cabana, Katie Craig, 7 Jul 2025, corrected): two-regime SOFR model keyed to ON RRP size; bank lending soft cap at IORB plus 5-10bp.
- BofA Global Research - US Rates Watch: Funding and debt limit: history lessons (Mark Cabana, Katie Craig, 27 Jun 2025): debt-limit analog method and trade structure.
- BofA Global Research - US Rates Viewpoint: Lower UST WAM => backdoor easing (Meghan Swiber, Mark Cabana, Katie Craig, 2 Jul 2025): TGA rebuild speed, analog spreads, transmission chain.
- BofA Global Research - US Rates Watch: Funding notes: bill tracking and repo (Mark Cabana, Katie Craig, 8 Aug 2025): ON RRP beta to net bills, MMF exit threshold, post-QT bill buying.
- BofA Global Research - US Rates Watch: Monthly rates models, Apr 2025 edition (Bruno Braizinha, Katie Craig, 7 Apr 2025): regime-weighted SOFR-IORB model and log fits.
- BofA Global Research - US Rates Watch: Eliminating IORB: low odds but high impact (Mark Cabana, Katie Craig, 13 Jun 2025): balance-sheet identity vintage and Fed income accounting.
- BofA Global Research - US Rates Watch: Repo jump and Fed bill backfill risk (Mark Cabana, Katie Craig, 20 Oct 2025): spread-to-reserves table, liquidity-per-GDP fits, backfill sizing.
- Citi Research - US Rates Weekly: Fixing the plumbing (J. Mathai, R. Bikbov, S. Kang, J. Williams, S. Li; 30 Sep 2019): LCLoR scarcity point and buffer, reserve scenarios, year-end premium decomposition.
- Citi Research - US Rates Weekly: Time for moderation (J. Mathai, J. Williams, M. Chang, S. Li, R. Datla, A. Vazquez Plata; 17 Feb 2023): SOFR-FF vs bills minus reserves, RRP model, TGCR-RRP signal.
- Citi Research - FX Basis Quarterly: Paying the basis (again) into 2025 (Jason Williams, Tomohisa Fujiki, Andrea Appeddu; 13 Dec 2024): RRP model, the 5bp RRP adjustment, marginal lender.
- Barclays Research - Global Rates Weekly: The urgency question (A. Pradhan, R. Khanna, S. Kadota et al.; 2 Oct 2026): TGA-to-bills-to-repo chain, BoE QT modalities.
- Barclays (Joseph Abate) - US short interest rate primer (Jan 2025): Fed reaction function, SRF design, debt-ceiling mechanics, repo segments.
- J.P. Morgan - Global Rates Strategy: Cross currency basis 2H25 outlook (Francis Diamond, Khagendra Gupta, Takafumi Yamawaki et al.; 5 Jun 2025): TGA-RRP basis channel, BoE PMRR, Fed balance-sheet projection.
- J.P. Morgan - Drivers of cross currency basis in EUR, GBP, JPY, AUD and CHF (F. Bassi, F. Diamond, K. Gupta et al.; 11 Mar 2015): reserves-differential basis models.
- J.P. Morgan - The financial stability benefits of very abundant reserves (Younger, Roever, Salem, St John, White; 21 Feb 2019): reserve demand sizing and overdraft regression.
- Düring, Alexander - Fixed Income Trading and Risk Management: The Complete Guide (Wiley Finance, 2021): corridor frameworks, asset-purchase channels (Ch. 6-9).
- BofA Global Research - Global policy implementation: a short guide, summer 2025 edition (9 Jul 2025): floor vs corridor, G10 facility details.
- BofA Global Research - Global Rates Viewpoint: FX-Sofr primer (Ronald Man, Mark Cabana, Katie Craig et al.; 31 Oct 2023): reserves accounting for the basis.
- Citi Research - European Rates Weekly: A QT revolution (J. Searle, A. Appeddu, J. Harju, P. Sawant, D. Lanre-Ojo; 17 Sep 2026): BoE QT redesign and the one-off repricing rule.
- Goldman Sachs - Global Rates Trader: Reaching Limits (George Cole, William Marshall et al.; 2 Oct 2026): BoJ QT and JGB free float; BoC reserve framework.
- Conks (Monetary Mechanics) - Plumbing Notes: The Fed's Reckoning, Part I (9 Sep 2025): pure vs neutralised reserves, RRP de-neutralisation trigger.
- Conks (Monetary Mechanics) - Plumbing Notes: No Limits (9 Jul 2025): RRP-then-reserves drain sequence, foreign repo pool.
- Conks (Monetary Mechanics) - Plumbing Notes: A Global Compression (1 Feb 2026): barely ample vs near-abundant regimes, central-bank divergence and the basis.
- Conks (Monetary Mechanics) - Plumbing Notes: The Fed's Global Put, Part II (28 Sep 2024): QT-end checklist, interest-bearing deposit accounts at large banks.
- Conks (Monetary Mechanics) - Plumbing Notes: The Repo Market Dislocation, Part I (17 Aug 2024): benchmark decomposition by collateral sub-rate.
- Conks (Monetary Mechanics) - Plumbing Notes: A Faulty Relief Valve (8 Dec 2025): leverage ratio vs risk-based capital and reserve demand.
- Conks (Monetary Mechanics / Concoda) - Plumbing Notes: Money Market Update series (May 2024 to Oct 2025): monitors, rate hierarchy, dated snapshots, year-end and quarter-end behaviour.
- BofA Global Research - Rates teach-in series 2025: Fed plumbing and balance sheet (Mark Cabana, Katie Craig, 4 Jul 2025): corridor levels, QT absorption table.
- BofA Global Research - US Rates Alpha: Short July SOFR/FF: debt limit => bills (Mark Cabana, Katie Craig, 30 Jun 2025): TGA rebuild-speed tables.
- BofA Global Research - US Rates Watch: Bill demand gap: Fed help likely needed (Mark Cabana, Katie Craig, Meghan Swiber, 22 Oct 2025): post-QT bill-buying channels.
- BofA Global Research - US Rates Viewpoint: Primer: SOFR rate and SOFR spreads (Ralph Axel, Mark Cabana, Katie Craig, 8 Feb 2022): cash vs collateral, reserve log fits.
- BofA Global Research - US Rates Watch: Fed Negative Equity: No Tightening Limit (Mark Cabana, Katie Craig, 24 Feb 2022): Fed income breakeven.
- BofA Global Research - US Rates Watch: Fed's SLR proposal: underwhelming (Ralph Axel, Mark Cabana, 25 Jun 2025): leverage ratio and reserves.
- BofA Global Research - Global Economic Weekly: The fog of war (Claudio Irigoyen, Antonio Gabriel et al.; 2 Oct 2026): ECB reaction ladder.
- BofA Global Research - Global Rates Weekly: Start of rates bite (2 Oct 2026): BoE reserves path.
- Citi Research - US Rates Weekly: All it takes is a little push (J. Mathai, R. Bikbov, S. Kang, J. Williams, S. Li; 4 Oct 2019): QE and swap spreads.
- Citi Research - US Rates Weekly: Can Secretary Bessent and Chair Warsh save the curve? (J. Williams, M. Chang, R. Datla, A. Vazquez Plata; 21 Aug 2026): debt-limit path and bills minus reserves.
- Citi Research - European Rates Weekly: What to do about OATs? (J. Searle, A. Appeddu, J. Harju et al.; 1 Oct 2026): ECB net cash requirement with and without QT.
- Citi Research - European Rates Weekly: Higher yields are here to stay (J. Searle, A. Appeddu, J. Harju et al.; 24 Sep 2026): BoE QT pause.
- Citi Research - European Rates Strategy: Latest views, summer updates (J. Harju et al.; 20 Aug 2026): 2027 EGB net supply.
- Citi Markets - STIRT Weekly (M. Covre De Menezes et al.; 7, 14 and 21 Aug 2026): ECB reserve-demand curve, CAD, NZD, SEK, NOK, DKK liquidity, RBA reserves.
- Citi Research - Global Macro Strategy: Macro tapas (7 Aug 2026): foreign-official funding channels.
- J.P. Morgan - Global Markets Strategy, FX Markets Weekly (M. Chandan et al.; 21 Aug 2026): Treasury buybacks are not QE.
- J.P. Morgan - Global Fixed Income Markets Weekly (F. Diamond et al.; 21-22 Aug 2026): BoJ QT and supply.
- Nordea Markets - EUR Rates Flash (J. Vainikainen, 5 Feb 2020): ECB exempt tier and German repo.
- Financial Times - US long-term bonds slide as Treasury secretary Bessent's intervention fails to soothe investors (R. Hodgson, C. Jones, M. McCormick, 20 Aug 2026): buyback half-life.
- JWS Macro (Substack) - Duration Is Diseased: What Can Stop the Rot? (4 Sep 2025): BoJ JGB ownership.
- Bank of America Merrill Lynch - Musings from Harley Bassman, The Convexity Maven: The Largest Volatility Sale Ever (H. Bassman, 23 Mar 2010): QE as an unhedged vol sale.
- Duffie, Darrell - Dark Markets: Asset Pricing and Information Transmission in Over-the-Counter Markets (Princeton University Press, 2012): pre-crisis scarce-reserves mechanics.
- Yadav, Yesha and Younger, Joshua - Central Clearing the U.S. Treasury Market (University of Chicago Law Review, vol. 92, 2025): Sep 2019 repo spike.
- Conks (Monetary Mechanics) - Plumbing Notes: Takeoff Begins (6 Oct 2025): 3 Oct 2025 snapshot, takeoff mechanics, stress-monitor thresholds.
