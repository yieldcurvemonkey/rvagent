---
name: fi-g10-market-conventions
description: >-
  G10 rates market-conventions reference for USD EUR GBP JPY CAD AUD NZD CHF SEK NOK. Gives the overnight RFR per market (SOFR, EFFR, ESTR, SONIA, TONA, CORRA, AONIA, NZIONA, SARON, SWESTR, NOWA), OIS/IRS/FRA leg frequencies, day counts, spot and payment lags, calendars and roll/stub rules, compounded-RFR and lookback/lockout math, STIR futures (SR3, SR1, SONIA, ESTR, CORRA, Euribor, bank bills) and bond futures (UST conversion factors and 32nds, Bund, Gilt, JGB, ASX, Nasdaq SGB, CONF), bond accrued/yield quoting, linker lags, spread sign conventions, central-bank effective dates and the legacy IBOR (LIBOR, EONIA, CDOR, BBSW) to RFR map. Use when pricing, validating or comparing any rate, curve, swap, FRA, futures contract, bond or linker across markets, or when numbers differ between sources: day count, ACT/360 vs ACT/365, T+0/T+2, payment delay, observation shift, CTD/CF, ASW sign, swap spread sign, meeting vs effective dates, IMM dates, 5Yx10Y or 6M9M notation.
---

# G10 market conventions

A rate, price or spread is meaningless without its conventions: day count, compounding, payment frequency and lag, calendar, business-day
rule, spot lag, quote basis and sign. Most "mispricings" across sources, vendors and markets are convention mismatches that are 1-30bp in
size. This skill is the lookup and audit layer: what each G10 market uses, the formulas that turn a quote into a number, and tests that back a
convention out of a discrepancy. Per-market tables, contract specs and schedule rules live in `references/`; everything is dated and is a
**seed to verify** against the adapter's `swap_conventions`, `rate_indices`, `bond_static` and `fut_static` rows or the CCP/exchange rulebook.

## When to use
- Building, checking or comparing curves, swaps, FRAs, futures, bonds or linkers in more than one market.
- Two sources disagree on a rate, DV01, accrued, yield, spread or futures price, and the cause may be a convention.
- Reading a quote ("SOFR 5Yx10Y", "2s10s", "Bund ASW", "TYZ6 basis", "XM", "SR3Z6", "EU HICP linker") and needing its unit, sign and timing.
- Choosing which dates apply: meeting vs effective date, spot lag, ex-dividend, last-trade and delivery days, month-code meaning.
- Migrating legacy LIBOR-era series (EONIA, CDOR, BAX, Euroyen TIBOR) to RFR analogues.

## Inputs (data-agnostic)
| Input | Canonical table | Notes |
|---|---|---|
| Index definitions (day count, fixing calendar, publication lag, status, fallback) | `rate_indices` | one row per RFR, IBOR, policy, repo and CPI index; legacy rows keep `ceased_date` |
| Leg conventions per curve, by tenor | `swap_conventions` | fixed/float frequency and day count, spot lag, pay lag, calendar, BDC, CCP. One row per `from_tenor` when the convention switches (AUD) |
| Holiday calendars | `calendars` | keep exchange calendars (CME_IR, EUREX, ICE_EU, JPX, MX, ASX) apart from cash calendars (USGS, GBLO, EUTA...) |
| Central-bank dates | `cb_meetings` | `effective_date` where it differs from `meeting_date` |
| Bond terms | `bond_static` | coupon, frequency, day count, settle days, ex-div rule, yield convention, linker lag/floor |
| Futures terms | `fut_static`, `fut_basket` | `quote_type` (price, rate_index, yield_index, yield), settlement type, tick size, notional coupon, reference method; deliverable baskets and CFs in `fut_basket` |
| Fixings | `rate_fixings` | both vintages where an index has two (TONA provisional/final, SOFR revisions) |

Canonical definitions: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If a convention is not in these tables, ask the
user or adapter. Never invent a day count or lag; show the seed values and the conflict instead.

## Method

### 1. Convention checklist (run it before trusting any number)
For every rate/price write down: (1) index and tenor, (2) day count per leg, (3) compounding and fixing method (in advance, in arrears,
delay, shift, lookback, lockout), (4) payment frequency, (5) spot lag and payment lag, (6) calendar(s) and BDC, (7) quote basis (price, 100-rate,
yield, spread, bp vs %), (8) sign (who pays, which minus which), (9) dates (effective, meeting, delivery) and (10) vintage (settle vs close, provisional vs final, as-of date of the convention).
Rule: if two of the ten are unknown, the number is not comparable. Store sign and unit with the data (house rules: rates and spreads in bp; curve spread A-B = longer minus shorter;
`2s5s10s` fly = 2 x 5y - 2y - 10y; receive fixed = long duration = positive DV01).

### 2. Day counts and compounding
- DCF = days / year basis. ACT/360 (USD, EUR, CHF, SEK RFRs; Euribor), ACT/365F (GBP, JPY, CAD, AUD, NZD; NOWA is ACT/365), 30/360 bond basis (legacy USD fixed legs),
  30E/360 (EUR fixed, SEK/CHF bonds; NOK bonds and swap fixed legs plain 30/360), ACT/ACT ICMA (UST, gilt, Bund, OAT accrued). 30/360 vs 30E/360 differ only when the end date is the 31st and the start day is below 30
  (15-Jan to 31-Mar: 76 vs 75 days). Detail and the CFTC code map: [bond_and_linker_conventions](references/bond_and_linker_conventions.md).
- Simple `P = 100/(1 + r DCF)`; US bills discount `P = 100 - r DCF`, `r_simple = (1/(1 - r_disc t) - 1)/t`.
- Effective annual `(1 + r/n)^n - 1`; 100 to 102 is 2% annual = 1.9901% semi = 1.9819% monthly. Bond-equivalent `2 (sqrt(1 + y) - 1)`, about y^2/4 below the annual yield.
- Compounded overnight rate over a period (ISDA 2021 / NY Fed form):
  `R = [ prod_i (1 + r_i n_i / N) - 1 ] x N / d_c`, n_i = calendar days fixing i applies (Friday = 3), N = 360 or 365 per the index, d_c = calendar days. Not a simple average:
  constant SOFR of 5% compounds to 5.13% over a year (Huggins and Schaller, SOFR Futures and Options, 2022, Table 3.2).
- A compounded period of overnight rates equals a ratio of discount factors only for actual-day counts with a fixed denominator; it breaks for 30E/360.

### 3. Overnight RFRs and what each index is
| Ccy | RFR | Nature | Basis | ISDA 2021 rounding | Term index / swap anchor |
|---|---|---|---|---|---|
| USD | SOFR (EFFR = policy target) | secured, volume-weighted median of tri-party + GCF + cleared bilateral repo | 360 | 0.00001% | LIBOR ended 30-Jun-2023; SOFR OIS |
| EUR | ESTR | unsecured, trimmed mean (EONIA retired) | 360 | 0.0001% | Euribor still live; ESTR OIS and 6M Euribor IRS both trade |
| GBP | SONIA | unsecured, trimmed mean | 365F | 0.0001% | SONIA OIS |
| JPY | TONA | unsecured call rate; provisional and final prints | 365F | 0.00001% | TONA OIS; TIBOR continues |
| CAD | CORRA | repo-based (secured) | 365F, no leap adjustment | 0.00001% | CDOR ceased 28-Jun-2024; CORRA OIS |
| AUD | AONIA (= cash rate) | unsecured | 365F | 0.0001% | BBSW IRS and AONIA OIS side by side |
| NZD | NZIONA (OCR-linked) | unsecured | 365F | 0.0001% | 3M BKBM IRS standard |
| CHF | SARON | secured (repo + quotes), 18:00 reference | 360 | 0.0001% | SARON OIS |
| SEK | SWESTR (since Sep 2021) | deposit-based | 360 | not in the 2021 matrix | STIBOR 3M IRS standard, SWESTR OIS trades |
| NOK | NOWA | unsecured | 365 | 0.00001% | NIBOR 6M IRS standard |

Secured (SOFR, SARON, CORRA) rates can fall in stress and carry no bank-credit premium; unsecured RFRs and IBORs reflect bank funding. SOFR is a trimmed volume-weighted median (an index you cannot trade in cash);
TGCR is within BGCR is within SOFR. Construction, specials trimming and legacy IBOR mechanics: [rfr_indices_and_transition](references/rfr_indices_and_transition.md). Corridor levels and
repo hierarchies are signals, not conventions: see [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md).

### 4. Fixing methods and payment timing
- **Payment delay** (OIS and cross-currency standard): accrual = observation period, pay n BD later. **Observation shift** (FRN standard; 2 or 5 BD, European FRNs 5). **Lookback** and **lockout**:
  rarely used for swaps, lumpy fixing risk (about 3x and one third of notional around weekends), mismatch with futures grows with n. ISDA 2021 default shift/lookback/lockout is 5 BD if unspecified.
- Payment lags (seeds): SOFR 2 BD (cleared; a one-day lag is shown only as a stylised case), SONIA 0, ESTR 1 or 2 **[CONFLICT]**, TONA 2, SARON 2, CORRA 1, NZIONA 1, SWESTR 1, AONIA conflicting inside AFMA.
  Spot lags: GBP T+0, CAD T+0 or T+2 **[CONFLICT]**, AUD T+1, others T+2 (USDCAD FX T+1). Verify per curve: [market_matrix](references/market_matrix.md).
- Margin on a compounded leg is added without compounding for FRNs; for swaps, "spread-exclusive", ISDA-compounded and flat compounding give different mid spreads (362.23 / 357.71 / 360.66bp in one case), so solve numerically.
- In-period fixings: use realised fixings for past days and forwards for future days: `R_unknown = [(1 + R D/360)/prod_known(1 + r_i d_i/360) - 1] x 360/D_unknown`.

### 5. Swap, FRA and notation conventions
- Direction is quoted on the fixed leg: payer pays fixed (short duration), receiver receives fixed (long duration). For inflation swaps say long/short inflation.
- Fixed leg standards (seed, Nov 2026): USD SOFR and EUR ESTR OIS annual ACT/360 vs annual compounded; GBP, JPY annual ACT/365F; CHF annual ACT/360; CAD semi-annual ACT/365F; AUD IRS quarterly to 3y and
  semi-annual from 4y vs 3M/6M BBSW (ACT/365F, T+1); NZD semi-annual vs 3M BKBM; EUR IRS annual 30/360 vs semi-annual 6M Euribor ACT/360; SEK annual 30/360 vs 3M STIBOR; NOK annual 30/360 vs 6M NIBOR.
  Long USD swaps can instead be semi-annual 30/360 ("bond basis"), short swaps annual/quarterly ACT/360 (CME). Under 1y, OIS pays once at maturity.
  Comparing an ACT/360 swap coupon with an ACT/ACT bond coupon needs a factor 365/360.
- Notation: `5Yx10Y` = starts in 5y, runs 10y (first fixed flow at 6y on an annual fixed leg: EUR, SOFR/SONIA/TONA OIS; 5.5y on a semi-annual one: legacy USD/GBP/JPY LIBOR swaps, CAD). FRA `6M9M` = starts 6M, ends 9M. A FRA buyer pays fixed and gains when rates rise; **buying a FRA = selling a STIR future**.
  FRA settles at the start of the period, discounted: `N (r_fix - r_FRA)(t/360)/(1 + r_fix t/360)` (365 for GBP).
- Schedules are built backward from the unadjusted maturity; effective and termination dates are unadjusted by default and payment dates modified following. Rolls, stubs, IMM and EOM rules, and calendar
  differences (CME vs federal; UK substitute days): [schedules_and_calendars](references/schedules_and_calendars.md).

### 6. STIR futures
- Price = 100 - rate. 3M RFR futures (SR3, SONIA, ESTR, CORRA, SARON) settle on the daily-compounded rate over the IMM-to-IMM reference quarter, `R = [prod(1 + d_i R_i/(Y x 100)) - 1] x (Y/N) x 100`, with Y = 360 or 365.
  1M SOFR and Fed Funds futures settle on the **arithmetic** monthly average over calendar days (weekends carry the prior BD). SR3 = $25/bp, SR1 = $41.67/bp.
- **Month code = month in which the reference period starts**, for 3M RFR and IBOR futures alike (1M SOFR: delivery month). RFR futures settle at the END of the period (SR3 Mar covers Mar-Jun and settles in Jun), IBOR futures expire at the START (Eurodollar/Euribor Mar expires in Mar); mixing the two is a one-quarter error.
- AUD/NZD bill futures and ASX bond futures are quoted 100 - yield but are not valued linearly; Nasdaq SGB futures quote the yield directly.
- Futures-implied rates need a convexity adjustment before comparison with swap or FRA forwards ([stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md)); overlap days must be weighted when
  spreading monthly vs quarterly contracts; the SR1/SR3 ratio 6:10 (written (3+3):10) is almost BPV-neutral (6 x 41.67 = 250 vs 10 x 25).
- Full spec table (size, tick, last trade, settle), packs/bundles, colours, legacy IBOR contracts: [futures_specs](references/futures_specs.md).

### 7. Policy dates: which rate is priced
Use the OIS-implied index, not the policy rate, and the **effective date**, not the meeting date: ECB effective the Wednesday after the meeting; BoE MPC-dated OIS from publication to publication
(decision published the following Thursday); BoJ changes take effect at the start of the reserve period (16th); Norges Bank decisions can take effect a couple of days later; SEK meeting-dated OIS is illiquid so the path is
a best guess; Fed meeting dates. Stub = market OIS up to the next meeting. Hike probability for a 25bp move = (meeting-dated OIS - current rate)/25bp. Details: [market_matrix](references/market_matrix.md), and
[stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md).

### 8. Government bonds and bond futures
- Clean + accrued = dirty. Accrued uses the bond day count (UST, gilt, Bund ACT/ACT ICMA; Canada ACT/365F; JGB ACT/365; SEK/CHF 30E/360; NOK 30/360). Gilts go ex-dividend 7 BD before coupon (negative accrued); ACGB 7 days.
- UST prices in 32nds: 99-24+ = 99.765625; third digit = eighths of a 32nd on cash, truncated decimals on futures (cash 97-186 = futures 97-187). Tick: TU 1/8 of 1/32 ($7.8125), FV 1/4 of 1/32 ($7.8125),
  TY and Ultra 10y 1/2 of 1/32 ($15.625), US/WN 1/32 ($31.25). TU and the 3-year are USD 200k face, the rest USD 100k.
- Yield methods differ (JGB simple yield, German Moosmuller, ISMA annual, US street semi-annual, DMO quasi-coupon): convert to one standard before comparing and never rank bonds by yield.
- Settlement (seed, Nov 2026): UST T+1, gilt T+1, JGB T+1 since 1-May-2018, CAD T+1 since 27-May-2024, EUR sovereigns T+2, SEK/NOK/CHF T+2.
- **Conversion factor** = price of 1 par of the bond at a 6% yield, remaining life from the first day of the delivery month rounded down to whole quarters for TY, Ultra 10y, US and Ultra bond but to whole **months** for TU, 3-year and FV (6% since 2000; 8% before). Gross basis `GB = P - F x CF`;
  invoice `= F x CF + AI(delivery)`; IRR `= (Invoice/Purchase - 1) x 360/n` (both dirty, no coupon in the holding period, convention-sensitive); CTD = highest IRR = lowest net basis; futures DV01 = CTD DV01 / CF.
- Delivery windows decide optionality: US, UK, Canada seller picks any BD of the month; Eurex (10th) and JPX/OSE (20th) have one delivery day. ASX contracts are **cash-settled** on a basket of bonds at 100 - yield with a
  level-dependent tick value; Nasdaq SGB futures deliver one designated bond (no CTD). Notional coupons: 6% UST/Eurex/OSE/MX/ASX, Gilt 4% (7% in 2004), Buxl 4%, CONF 1%, SGB 1%.
  Full tables and formulas: [futures_specs](references/futures_specs.md).

### 9. Inflation-linked conventions
Index ratio `I_t/I_0` multiplies every cash flow; reference index `CPI_{m-3} + ((d - 1)/ND)(CPI_{m-2} - CPI_{m-3})` for 3-month-lag interpolated linkers. Linkers quote real price (UK per BofA 2025, but Duering 2021 says UK quotes include inflation: **[CONFLICT]**, check the DMO
convention; AUD and SEK quote adjusted price). Lags: US 3m interpolated; EUR/FR 3m swap lag without interpolation; UK RPI swaps 2m without interpolation; JGBi modified 10th-of-month lag; ACGB 6m. Floors: none for UK and Canada linkers,
floors for US, EUR, JPY (2013 series), AUD, SEK. ZC swap fixed leg `(1 + K)^T - 1` vs `I_end/I_start - 1`. Table and swap/linker lag basis: [bond_and_linker_conventions](references/bond_and_linker_conventions.md) and
[infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md).

### 10. Spread and quote signs
Curve spread A-B = longer minus shorter. Swap spread: US quoted as swap minus Treasury (higher = richer Treasury); EGB asset-swap spread = bond yield minus swap (higher = cheaper bond); JGB and EUR vendor series often
carry the US sign by mistake, so test the sign on a known date. ASW = X in "reference rate + X" (richer bond = lower ASW). CCBS spread sits on the non-USD leg; futures-price spreads have the opposite sign to rate spreads
(SOFR-FF). Normal (bp) vol for rates options. Variants and worked ASW cases: [bond_and_linker_conventions](references/bond_and_linker_conventions.md) and
[spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md).

### 11. IBOR to RFR translation
Map the logic, not the label: EONIA to ESTR, GBP/USD/JPY/CHF LIBOR to SONIA/SOFR/TONA/SARON, CDOR to CORRA (BAX converted to CRA at CRA - 32.138bp), Eurodollar to SR3 (fixed +26.161bp), FF/LIBOR basis to SOFR-FF.
Term indices that survive: Euribor, TIBOR, BBSW, BKBM, STIBOR, NIBOR. Fallback spread for USD LIBOR = 5-year median of LIBOR minus compounded SOFR (fixed 5-Mar-2021). Histories carry structural breaks at each cessation
and at the Aug-2021 SOFR facility change: stitch with a documented break date or use fitted constant-maturity yields. Table: [rfr_indices_and_transition](references/rfr_indices_and_transition.md).

## Worked examples
1. **3M SOFR contract by compounding.** Jun-2022 contract, 98-day period, 42 days at 0.51% then 56 days at 0.76%: `R = [(1 + 0.51%/360)^42 (1 + 0.76%/360)^56 - 1] x 360/98 = 0.653%`, price 99.347 against a
   market 99.350 (Tuckman and Serrat, Fixed Income Securities, 2022, Ch.12). `compound` in the script reproduces it.
2. **2y IMM OIS from an SR3 strip.** Eight 91-day contracts at 95.895, 96.290, 96.605, 96.815, 96.940, 96.985, 96.965, 96.910: `DF_i = 1/(1 + R_i d_i/360)`, cumulative product, `fixed = sum CDF_i R_i d_i/360 x 360/sum CDF_i d_i`
   = 0.0647505 x 360 / 699.926 = **3.3304%** (CME, Pricing and Hedging USD SOFR Swaps with SOFR Futures, Jun 2025).
3. **Weekend weighting.** USD FF OIS 6-Jan-10 to 13-Jan-10 with fixings 0.12, 0.13, 0.14 (Friday, 3 days), 0.13, 0.10 gives a product 1.0000250 and breakeven 0.0000250 x 360/7 = **0.1286%**, not the 0.124% plain average
   (Credit Suisse, Basis Points, Feb 2010).
4. **Day-count slip.** 100mm for 1-Jun-16 to 1-Sep-16 at 10%: 1/1 10,000,000; ACT/ACT 92/366 2,513,661.20; 30/360 2,500,000.00; ACT/365F 2,520,547.95 (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022).
   ACT/365 where ACT/360 applies understates accrual by about rate x 1.4%: about 5.5bp at 4%.
5. **Conversion factor, basis, IRR.** 7.5% of 11/15/16 in the Jun-2001 contract: 15y 5.5m rounds to 15y3m, CF = 1.1484; cash 120-20, futures 103-30: `GB = 120.6250 - 103.9375 x 1.1484 = 1.2632` (40.4/32).
   Invoice with AI 0.91712 on 29-Jun-01: 103.9375 x 1.1484 + 0.91712 = 120.2789. IRR is a different bond in the same source: the 7.25s of 8/15/22 (CF 1.1481) bought 6-Apr-01 at clean 119-28 + AI 1.0014 = 120.8764 and delivered 84 days later on 29-Jun-01 with AI 2.683702, invoice 103.9375 x 1.1481 + 2.683702 = 122.0143: **4.03%** (Burghardt et al., The Treasury Bond Basis, 2005). Computed by `ust_conversion_factor` and `implied_repo`.
6. **Linker.** OATei 1.85% 2027, value 22-Jul-2025: reference value 128.16 + (21/31)(128.08 - 128.16) = 128.10581, base 93.72591, index ratio 1.36681; real price 103.141 on 1mm gives principal 1,409,741.50 plus accrued
   25,078.15 = 1,434,819.65 (BofA, Global Inflation-Linked Primer, Jul 2025).
7. **ASX bond future value.** 10y at 95.00 (5% yield): `1000 x [3 (1 - v^20)/i + 100 v^20]`, i = 0.025, = AUD 107,794.58; a 1bp move is AUD 81.63, falling to 61.93 at 8% yield and rising to 89.65 at 4%
   (Burghardt et al. 2005, Exh 9.5, whose printed 107,795.58 is a typo; ASX pricing guide formula).
8. **FX forward with basis.** EURUSD 1.2960, 92 days, EUR 1.12%, USD 0.56%: F = 1.2942 (-18.5 pips); a -75bp basis on the **non-USD** rate gives 1.2966 (+6 pips, as quoted) (Aikin, STIR Futures, 2012).

## Signals & interpretation (convention-mismatch diagnostics)
Back the convention out of the discrepancy before blaming the market. Typical sizes at a 4% rate unless stated:
| Observed gap | Likely convention error |
|---|---|
| about 5.5bp (rate x 5/360 to 5/365) between two otherwise equal rates | ACT/360 vs ACT/365 (or 365F vs 360) |
| 4bp (y^2/4) on yield; 25bp at 10% | semi-annual vs annual or bond-equivalent vs annual compounding |
| up to 13bp at 5% on a 1y rate; about 3bp over a quarter | compounded vs simple (arithmetic average) overnight rates |
| a quarter-sized shift in expiry/settlement date on a futures strip | RFR (settles at period end) vs IBOR (expires at period start) month-code semantics |
| 2x the spread level, or sign flip of a swap or ASW spread | bond-minus-swap vs swap-minus-bond |
| step of a policy path displaced by about a week | meeting date used instead of effective date (ECB, BoJ, BoE) |
| tens of bp on a bond future basis | wrong notional coupon (8% vs 6%, old Gilt 7% vs 4%), rounding of maturity to quarters, or wrong CF month |
| 1-3 days of accrual, or weekend jumps in a short OIS | Friday weighting missing, wrong calendar, payment lag ignored |
| gap of a fraction of a bp between a futures settle and a swap/curve close | settle vs close snap |
| gap under 0.5bp between rebuilt and vendor OIS (implied-minus-market) | within tolerance (Deriscope); investigate above 1bp |
Decision rules: (a) reprice one instrument from raw inputs under each candidate convention and keep the one that matches to under 0.5bp; (b) validate any calendar against a published fixings series
(fixing dates must equal the business days); (c) check futures prices land on the exchange tick grid; (d) if two sources conflict, record both and ask for the CCP or exchange sheet rather than choosing.

## Pitfalls
- Convention tables age: LIBOR-era day-count lists (2010), SEF floating-rate-option lists (2021), futures specs (2004) and bond tables (2001) are history. Use the dated stamps in `references/`.
- Do not assume uniform spot lags (GBP T+0, AUD T+1, CAD conflicting) or payment lags (SONIA 0, ESTR 1/2, SOFR 2).
- Do not confuse 1M arithmetic and 3M compounded futures in one bootstrap; do not use the 2-day cut-off of old FF/LIBOR averaging for OIS (geometric).
- A repo fixing is not a bank-funding rate: SOFR can print below the policy range and spike at turns; read year-end and quarter-end prints separately.
- US Treasury futures: the TU contract is USD 200k face; cash and futures 32nds digits differ; after the last trading day the futures price is fixed while cash trades on.
- Linker quotes: UK/Canada linkers have no floor; AUD/SEK quote adjusted price; a seasonality adjustment is required across maturity months.
- Benchmark rolls (a new Bobl/Bund replaces the old on a date) create fake curve moves in generic series.
- CME and federal US holiday calendars differ; UK moves weekend holidays, Europe loses them.
- A vendor "mapping" of a LIBOR floating-rate option to an RFR is a common benchmark, not an identical rate.
- Policy-rate and corridor levels quoted in sources are dated snapshots: read them from `rate_fixings`, never from this skill.

## Output
Return, for each instrument or series examined: a **convention card** (table: index, day count by leg, frequency, compounding/fixing method, spot lag, pay lag, calendar, BDC, quote basis and sign, key dates, source and
as-of date of each value, and a verified/seed/conflict flag), the recomputed number under the confirmed convention, and where relevant the discrepancy diagnosis (gap in bp, candidate cause, test that confirmed it).
Flag every seed that was not verified against `swap_conventions`/`rate_indices`/`fut_static` or a rulebook. Hand off sign and unit statements to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts
- [`scripts/conventions.py`](scripts/conventions.py): `year_fraction` (ACT/360, ACT/365F, 30/360, 30E/360, ACT/ACT ISDA, 1/1), `adjust` (F, MF, P, MP), `compounded_rate` and `compound_from_fixings`,
  `ois_from_future_strip`, `compounding_equivalent`, `bill_discount_to_simple`, `accrued`, `px32` (cash and futures 32nds), `ust_conversion_factor`, `implied_repo`, `au_bond_future_value`, `linker_ref_index`.
  CLI: `dcf`, `compound` (reads `rate_fixings`; `--asof` drops later-published vintages), `px32`, `cf` (`--monthly` for TU/3-year/FV). `ust_conversion_factor` takes `monthly=True` for those. `python -I scripts/conventions.py --selftest` checks 61 cases with published or by-definition answers.

## Related skills
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables holding these conventions
- [fi-curve-construction](../fi-curve-construction/SKILL.md): uses the leg, lag and calendar conventions to bootstrap curves
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry needs day counts, repo basis and delivery dates
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 depends on the day count and compounding used
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): fixing-risk consequences of lag, lookback and lockout
- [stir-futures-rv](../stir-futures-rv/SKILL.md): trading futures once the contract definitions are right
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-date and effective-date pricing
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): CF, basis and IRR analysis
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): delivery windows and CTD optionality that the contract specs create
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): last-trade and roll dates by contract
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures vs FRA/OIS rate comparison
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo-rate hierarchy and corridor signals
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CSA discounting and curve naming
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread and ASW sign conventions in use
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): basis-swap quoting
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): linker and inflation-swap conventions in trade
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): calendar, stale-data and roll-stitching checks
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): balance-sheet and regulatory shadow costs.

## References
- Tuckman and Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): RFR table, ON-loan structures, SR3/SR1 and Euribor FRA mechanics, OIS vs IRS legs, accrued and compounding examples, TYU1 basis table.
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): day-count and frequency examples, RFR table, IRS/OIS/FRA/XCS/ASW conventions, curve naming.
- Darbyshire - Coding Interest Rates: FX, Swaps and Bonds (c.2024): schedule/roll/stub rules, calendars and holiday observance, compounding and fixing methods, accrued, bills, inflation indexation.
- Duering - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): day counts, yield methods, FRN conventions, spread signs, linkers, per-market bond conventions.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): CF, basis, IRR, 2001 bond conventions table, 2004 futures specs, ASX bond-future valuation.
- Huggins and Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): SOFR construction, SR3/SR1 specs and settlement, lookback/lockout, Term SOFR, transition dates.
- Huggins and Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): reference-rate map, ASW and CCBS conventions, structural breaks from LIBOR cessation.
- CME Group - Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures (Rogerson, 4 Jun 2025): SR3 spec, SOFR OIS day counts, strip-to-OIS bootstrap, packs and bundles.
- CME Group - Understanding Treasury Futures (Johnson, Kerpel, Kronstein, Nov 2017): 32nds, deliverables, delivery cycle, CF. BofA Global Research - US Treasury futures and basis primer (Axel, 10 Jul 2025): 2025 contract table.
- BofA Global Research - Global Inflation-Linked Primer, 2nd ed. (Capleton, Swiber, 22 Jul 2025): index ratio, reference value, per-market linker and swap lags. BofA - FX-Sofr primer (31 Oct 2023): FX-swap reference rates, basis convention.
- BofA Global Research - US Treasury auction primer (Craig, Cabana et al., 8 Mar 2024) and Japan Rates Basics (Yamashita, Yamada, 24 Apr 2023): issuance calendars, JGB auction formats and JGBi indexation.
- Heitfield and Park - Inferring Term Rates from SOFR Futures Prices (Federal Reserve Board FEDS 2019-014, Feb 2019); Bowman - Historical Proxies for the Secured Overnight Financing Rate (FEDS Notes, 15 Jul 2019): futures pricing equations, SOFR construction and backfill.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): tick/BPV math, legacy contract specs, FX forward with basis. Aikin - Welcome to STIR futures blog, "Interest rate change probabilities" (30 Jan 2014).
- Credit Suisse Fixed Income Research - Basis Points: A Guide to the Front-End and Basis Swap Markets (Lantz, Chang, Dorji, 18 Feb 2010): LIBOR fixing and spot rules, FRA notation, OIS breakeven.
- Henrard - Interest Rate Futures and their Options: Some Pricing Approaches (OpenGamma, v1.3, 23 Feb 2012) and Overnight Futures: Convexity Adjustment (SSRN, Mar 2018); FactSet - Interest Rate Future white paper (23 Mar 2023): futures settlement, month-code semantics.
- ISDA - 2021 IRD Definitions Matrix for Overnight Rate Compounding/Averaging/Index Methods (v1.0, 11 Jun 2021) and 2021 FRO Mapping Tables (v3, Oct 2021): rounding, default lags, IBOR to RFR floating-rate-option map.
- CFTC - Technical Specification, Parts 43 and 45 (v3.0, Sep 2021; v3.1, Aug 2022): day-count codes, payer/receiver direction, frequency and unit encoding.
- Tradeweb SEF Rulebook Ch.9, Rule 901 swap specifications; tpSEF Rulebook Appendix B (May 2021); LCH SwapClear USD product eligibility (Oct 2019): default date rules, spot lags, cleared OIS parameters (LIBOR/EONIA era lists, dated).
- Ametrano and Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping (SSRN, Apr 2013); Burgess - Electronic Rates Markets and Low Latency IRS Calculations (SSRN, May 2022): EUR curve conventions, tenor-basis quoting, schedule and MAC/IMM rules.
- Citi Research - G10 What's Priced In (Dolega, 14 Aug 2026; Purcell, Aug 2026): which rate and which date each central bank path is priced on.
- Rigopoulos (Deriscope) - Yield curve building with central-bank meeting dates, the GBP SONIA case (18 Feb 2024) and How to build a SOFR yield curve (18 Feb 2024): SONIA T+0/ACT/365F, MPC-dated OIS, 1M/3M futures definitions.
- Gunstensen - MIT 18.642 Lecture 7: Linear Rates Models (26 Sep 2024): schedule roll-out, SOFR averaging, date-arithmetic warning. Deutsche Bank - Interest Rate Curve Creation Process (2 Feb 2023): G10 curve instruments and snap times.
- J.P. Morgan - Asset Swaps (Salford, Feb 2006): par/par, optical and market-value ASW types. Bassman - Finding Sea-Level (Convexity Maven, 27 Jan 2016): swap-spread sign, normal-vol quoting. Quantitative Finance Stack Exchange - Ten Year Note futures implied repo calculation (5 Jul 2022): IRR convention sensitivity.
- Conks (Monetary Mechanics) - Primers and Plumbing Notes, 2023-2026: TGCR/BGCR/SOFR composition, SOFR trimming change, SERFF futures sign convention.
- Web-retrieved exchange, administrator and association documents, Nov 2026 (external): ASX Treasury bond futures factsheet and IRD pricing guide; AFMA Interest Rate Derivative Conventions; Eurex, ICE, MX and Nasdaq contract pages; OpenGamma open-source swap convention definitions; TP ICAP swap-convention templates; Norges Bank NOWA conventions; SIX, Riksbank, RBA, BoC, ECB, BoE and BoJ benchmark pages; Bank of England Bank Overground (2025) on repo-led framework.
