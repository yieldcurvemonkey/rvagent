---
name: spread-swap-spreads-and-asw
description: Values government bonds against swaps in G10 rates. Covers swap spreads (spreadover, matched-maturity MMS, I-spread), asset-swap spreads (par/par, proceeds, yield-yield, z-spread) on SOFR/OIS/ESTR/SONIA/TONA, spread curves (TFP, zero-duration spread, PCA dislocation, 5s30s) and the balance-sheet, SLR, repo, supply and flow drivers behind them. Computes and signs the spread, sizes the DV01-neutral package, builds fair value (funding + adjusted CDS + haircut, ROE breakeven, carry/vol hurdle) and returns trades with carry, entry/target/stop. Use when asked about swap spreads, spreadovers, widener/tightener, asset swap, ASW, MMS, I-spread, z-spread, Treasury vs SOFR/OIS, Bund/gilt/JGB/OAT ASW, SSA or agency vs swaps, spread curve box, TFP, ZDS, "why is the swap spread negative", SLR relief, swap-spread curve steepener/flattener, SOFR-ASW.
---

# Swap spreads and asset swaps (ASW)

A swap spread compares a government bond yield with the swap rate for the same cash flows. It is a carry trade that needs balance sheet, stable funding
and a working Treasury market, so it prices dealer capacity, repo, supply and end-user flows rather than government credit. Front-end spreads follow funding and
regulation; long-end spreads follow supply, deficits and structural receivers (pensions, insurers, issuers). The skill computes the right measure with explicit signs,
tests whether a level is rich/cheap against fundamentals and the spread curve, and packages a hedged trade.

## When to use
- "Is the 10y swap spread cheap?", "why is the 30y spread -70bp?", "buy 5y spreads", "5s30s spread flattener", "2y widener", "SLR relief trade".
- Bond-level asset swap screens: which Treasury/gilt/JGB/OAT/Bobl is rich or cheap on ASW or z-spread; SSA/agency vs swaps or vs govies; low-coupon switches on ASW.
- Fair-value work on a spread: funding, credit, haircut/ROE breakeven, TFP/ZDS, supply regressions, PCA residuals, carry/vol.
- Sizing and signing a spread package, or reconciling two published spreads that disagree in sign or definition.

Not here (use the linked skill): invoice spreads and CTD ([fut-invoice-spreads](../fut-invoice-spreads/SKILL.md)); SLR/GSIB/haircut mechanics ([fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md));
CDS-bond basis and CDS adjustment ([spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md)); linker ASW and iota ([infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md));
MBS hedge arithmetic ([flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md)); EUR/USD xccy and $ASW ([xccy-basis](../xccy-basis/SKILL.md));
bill ASW ([stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md)); PCA/OU mechanics ([curve-pca-factor-model](../curve-pca-factor-model/SKILL.md), [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md)).

## Inputs (data-agnostic)
Schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). Conventions per market: [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Nominal coupon bond static (coupon, freq, day count, maturity, ex-div) | `bond_static` | point-in-time (`valid_from`) | filter `bond_type = nominal`; bills, strips, linkers, FRNs need other treatment |
| Clean/dirty price, accrued, yield at the settle date | `bond_quotes` | daily, one `snap` | use `accrued_px` (negative for gilts ex-dividend); never mix snaps |
| Swap/OIS discount factors, same RFR as the bond's currency | `curve_zero` | daily, same snap | par rates in `curve_par`; need nodes to the longest bond |
| Generic par swap rates by tenor, spot and forward start | `curve_par` | daily, >= 3y (>= 1y for PCA/TFP windows) | for spreadover/OTR spreads |
| GC and special repo by term | `repo_rates` | daily | carry, specialness drag, 3M GC/OIS driver |
| Swap leg conventions per `curve_id` | `swap_conventions` | static | fixed/float frequency and day count drive the annuities |
| Stored result | `swap_spreads` | daily | `measure`, `value_bp`, `sign_convention` travel together |

Driver inputs without a canonical table (ask the user/adapter, never invent): Treasury WAM and net supply ex-central bank, 10y-ahead deficit projection, dealer UST inventory,
excess deposits/reserves, 1Yx10Y normal vol, bank/insurer/MBS/VA flow estimates, haircut schedules, sovereign CDS. If missing, run the measures and say the fair-value step was skipped.

## Conventions and signs (state them every time)
Stored defaults (`swap_spreads` schema): `spread_mm`/`spread_otr` = **swap minus govt (S-G)**, negative when swaps trade below the bond (USD since 2015 at 10y);
`asw_*` and `zspread` = **govt minus swap (G-S)**, positive = bond cheap to swaps (EGB convention). In bp, spread on the floating leg for ASW.
Publishers differ, so tag every quoted number:

| Family | Sign | Direction words |
|---|---|---|
| US MMS / spreadover (JPM, Citi, Barclays, Clarus) | S-G | "long/buy spreads", "widener" = buy bond + pay swap; profits as S-G rises (less negative) |
| BofA UST MMSS (2022), GS UST ASW screen | G-S (positive) | same trade, opposite sign |
| Single-bond Treasury vs OIS (BofA 2017-18) | UST - OIS: positive = cheap | "sell spreads" = sell bond vs receive OIS profits as it cheapens |
| EGB/gilt/JGB ASW, H&S "reference + X" | G-S | long ASW = long bond on asset swap; Bund at EURIBOR -10 is rich |
| Düring (2021) | widener = sell bond + receive | opposite to Clarus/JPM: always describe by legs |

Rules: (1) describe every trade by its legs (buy/sell bond tenor, pay/receive swap tenor); (2) record `sign_convention` with every value; (3) vendor series often apply the US sign to EUR/JPY: verify
against a known level; (4) "tight" is ambiguous (a tight xccy basis = looser USD funding, a tightening US swap spread = worse plumbing). Rates in %, spreads and ASW in bp, DV01 in currency per bp
(long bond / receive fixed positive), notionals per 100.

## Method
1. **Pick the measure for the question** (formulas in [asw-structures-and-hedging](references/asw-structures-and-hedging.md)):
   - curve-level rich/cheap, flows, regulation: matched-maturity swap spread `S_mm = par swap(to bond maturity, front stub, bond's frequency) - bond yield` (S-G), or generic spreadover vs the on-the-run;
   - bond-level rich/cheap vs the swap curve: **z-spread** (default), then par/par ASW; use proceeds ASW when price is far from par (low coupon, zeros, linkers);
   - hedge quality on a held bond: par/par; short-term hedge or fast execution: I-spread (bond yield - interpolated swap); futures-based: invoice spread (other skill).
2. **Compute with `scripts/asw.py`**: curve rebased to the settle date (DF(t)/DF(settle)); `par_par = 1e4 (PV(coupons+principal on swap curve) - dirty)/(100 A_flt)`;
   `proceeds = par_par x 100/dirty`; `z` solves PV(z) = dirty (continuously compounded, so it differs from a periodic-compounding quote by a few bp at wide spreads). Set `--fixed-freq/--float-freq/--dc` from `swap_conventions` per curve (ACT/365F for GBP/JPY, ACT/360 for USD/EUR/CHF).
   `spread_mm` is a straight difference of the swap rate and the bond yield in their own bases: swap fixed legs on ACT/360 vs bond ACT/ACT differ by 1.4% of the rate (about 4bp at 3%), so convert before comparing across markets (BTPs pay semi-annual, EUR swaps >2y pay annual).
3. **Hygiene**: single snap; settle-date prices; point-in-time static; exclude when-issued and tiny lines; splice histories only on a constant-maturity fitted curve (benchmark roll in the OTR
   spread jumps the series by about the old-new yield difference, at different dates per tenor); breaks at LIBOR to SOFR (and SOFR pre/post standing repo facility): never mix.
4. **Decide whether a bond-level ASW is an RV signal.** Default to SOFR-ASW or z-spread; LIBOR/OIS-ASW embed the unobservable bank cost of equity. Do not rank bonds with different coupons by par ASW or
   I-spread (a 10% bond at 4.98% vs a 5% bond at 5.00% on a 5.35% swap shows -37 vs -35 although both are fair). Compare within a coupon/maturity bucket, against a spline of the ASW z-spread, or
   use fitted-curve residuals ([bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md)). A EUR investor asset- and basis-swaps to EUR fixed and fits a curve rather than using spreads to EURIBOR/ESTR.
5. **Fair value, three lenses** (detail and coefficients: [fair-value-and-capital-models](references/fair-value-and-capital-models.md)):
   - *Funding + credit + capital*: ASW (G-S) = - expected specialness (GC - repo, discounted; positive number) + adjusted CDS (0.45 x CDS cash-settled, 0.39 physical) + haircut cost - capital basis g x q x d (~16bp at g = 10%, OIS/IBOR references only).
     SOFR-ASW has no capital basis; UST SOFR-ASW starts near 0 and rises with maturity.
   - *Balance sheet*: breakeven spread for a target ROE: `S_BE (bp) = -(ROE x Equity - K)/(notional x 1bp)`, K = net carry excluding spread income, Equity = SLR x (notional + haircut + IM + PFE). Capital is max(risk-based, leverage), so check
     which constraint binds before trading a regulatory headline.
   - *Drivers by tenor*: front end (<=3y) = funding (3M GC/OIS, SOFR-FF, reserves, bill supply, dealer inventory, HQLA); belly = convexity (MBS, banks), issuance swapping, bank AOCI;
     long end (>=20y) = deficits, WAM/buybacks, pensions/insurers/VA, SLR. "Repo drives shorter spreads, deficits drive longer spreads."
6. **Spread curve and cross-section** (never read one tenor as the signal for all):
   - Regress daily `S_mm_m = ZDS - TFP x ModDur_m` across 2/3/5/7/10/20/30y; TFP (bp per year of duration) is the term funding premium, ZDS the zero-duration spread. A large daily fall in ZDS signals deleveraging.
   - PCA on a 1y window of the spread curve (2 PCs), z-score residuals over 250d (3m for quick screens), dislocation index = 10d MA of RMS z (`dislocation_index`).
   - Spread-curve differentials (30y - 5y, 20y - 10y) trade the term premium; check the TFP exposure of the trade.
   - Carry/vol hurdle: carry per 1y vol per tenor; hurdle 0.25; the spread at which C/V = hurdle gives the widening room.
7. **Carry and roll** ([fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md)): swapped-bond carry = bond yield - repo (term repo where available) vs swap fixed - float over the same horizon, divided by modified duration to express in bp;
   forward spread minus spot spread is the repo-carry breakeven; front-end spreads have positive roll-down (Treasuries richen vs swaps as they roll). Shorting a special bond bleeds (GC - special repo) x notional (GC 5%, special 3%, short $100mm = $2mm/yr, illustrative).
   Swap-spread carry is small (-1 to +4bp per 3M in the published trades): it is a flow/regulation view, not a carry trade.
8. **Construct**: DV01-neutral package, swap notional = bond DV01/swap DV01 (e.g. 184.0/191.3 = 0.962); rebalance after large moves; hedge long-end narrowers with a 50% matched-duration Treasury flattener and a 10% risk-weighted
   long 30y UST; pick the risk basis explicitly (outright, spread + swap, or spread + bond: same total P&L). Fund bond legs in term repo where possible; check haircut and margin financing.

## Worked examples
**A. Par/par vs proceeds ASW** (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022). Genworth 4.90s of 15 Aug 2023, priced 15 Aug 2021 at 98.70 (yield 5.596%, 2y swap 0.288%): yield spread 530.8bp, par/par 526.4bp,
market-value 533.3bp (= 526.4 x 100/98.70). On a flat 0.288% semi-annual curve `scripts/asw.py` gives 526.43 and 533.37, confirming both the formula and the 1.3% gap that comes only from the price below par.

**B. US 2y widener** (JPM, Global FI Markets Weekly, 21-22 Aug 2026; S-G). Buy $100mn T 4.25% Jul-2028 at 4.232% (PVBP 184.0 per mn), pay fixed on $96.2mn matched SOFR swap at 4.083% (PVBP 191.3): spread 4.083 - 4.232 = -14.9bp,
hedge ratio 184.0/191.3 = 0.962, DV01 about $18.4k/bp each leg. Carry ~4bp per 3M against 2.3bp per 3M delivered vol (carry/vol ~1.7 on that 3M basis).

**C. Why a negative spread persists** (Boyarchenko et al., Negative Swap Spreads, FRBNY EPR, Oct 2018). $10mm 10y widener, 1y: IM 3.9% funded at 0.5% (-$1,950), float +$60,000, repo -$29,160, haircut funding -$1,400 = $27,490 before spread income
($1,000 per bp). At SLR 5% equity is $536.5k, so 15% ROE needs spread income $52,985, i.e. S about -53bp (table: -54); at SLR 3% and 10% ROE the table gives -6bp. A 10y MMS near -40bp (JPM, Aug 2026) is about what 15% ROE needs at a 4% SLR (-38bp) on these 2015 inputs:
capital explains the order of magnitude, so a negative spread is not an arbitrage once capital, haircut, IM and PFE are costed. Refresh repo, IM and haircut inputs before using the grid.
Funding check (Clarus, Swap Spreads for Dummies: The LIBOR Joke, 23 Nov 2015): 5y UST 1.688% vs 5y swap 1.578% looks like +11bp, but 3M term repo at 0.45% against 3M LIBOR received at 0.34% costs 11bp, before haircut, margin and capital.

**D. EUR ASW fair value** (Huggins & Schaller, Fixed Income RV Analysis, 2nd ed., 2024; G-S). 10y Bund vs ESTR: capital basis -16bp (g = 10%, q = 20%, d = 8%) + adjusted 10y German CDS +15bp - average specialness 6bp = **-7bp**. The same fair-value logic on
a SOFR reference removes the capital basis: Oct 2023 chart reads of Bund SOFR-ASW (10y -22bp, 20y -3bp) against UST (+29, +64) looked too rich at the long end versus CDS and haircut effects, a reversion idea only if the imbalance is judged ephemeral.

**E. Spread curve and hurdle** (JPM 21 Aug 2026; Barclays, Swap spreads: The Bright Spot in US rates, 30 Sep 2026). MMS (S-G) 2y -15.2, 5y -27.7, 10y -40.0, 30y -70.9; published TFP 4.4, ZDS -8.0. Re-fitting with par-bond durations at 4.2% gives
TFP 3.8, ZDS -10.0: the regression is sensitive to the duration inputs, so track your own series. Barclays carry/vol: 2y 1.15, 5y 0.76, 7y 0.52, 10y 0.40, 20y 0.26, 30y 0.24 vs hurdle 0.25; implied widening room 13/20/19/15/1/none bp: long belly (7y) widener, nothing in 30y.

More examples (PCA back-test, Rhodes 5s30s flattener roll, SSA switches) in [fair-value-and-capital-models](references/fair-value-and-capital-models.md) and [trade-log](references/trade-log.md).

## Signals & interpretation
- Timing: z-scores, PCA residuals and DI are computed on the close of day t and traded at t+1 (shift before trading); fit PCA/regressions only on data up to t.
- Screen: 3m z-score of S_mm and of proceeds ASW per bond; flag |z| >= 2 (GS screen: red below -2, green above +2). Require the same sign in the fitted-curve residual or the z-spread vs ASW-spline before calling a bond idiosyncratic.
  Idiosyncratic = residual vs the ASW-curve slope (e.g. 3.9 s.d. cheap, R2 0.65) and neighbours not moving; sector effect otherwise.
- Dislocation index: trade only when DI exceeds the threshold (US best Sharpe at 1.0-1.2, Germany stronger at 1.6-2.0; residual half-life ~20 days); buy the cheapest-z spread and sell the richest, then stop when DI falls below.
- TFP vs model: within 1 standard error (0.3) of the TFP fair value, go neutral and unwind curve trades positioned for the TFP correction; ~1 sd above fair value with conflicting flow headwinds: neutral.
- Implied-expectations inversion: divide the spread move by a driver's coefficient; if the required driver shift is implausible (a -0.3 TFP move = WAM 3 months shorter), fade the move.
- Regulation: widening on a headline then failing to deliver is the "rug pull" risk; check holdco vs bank-subsidiary and leverage vs risk-based binding. Consensus positioning into a catalyst (April 2025) is the pain trade.
- Flow tests: positive rolling-3M beta of weekly spread changes on yield changes (2019: +0.10 to +0.15, strongest long end) means convexity payers are active; hedgers act on net moves above ~20bp, later in a repricing.
- Stress (post-2015 regime): spreads tighten (more negative) in a dash for cash and when vol spikes; in the LIBOR/GFC era stress widened them (2y +165bp in the GFC), so the sign of the stress response is regime dependent; widening with a sell-off means crowded long-spread positions (stop-driven unwind risk). A one-day ZDS collapse = deleveraging: de-risk wideners.
- Risk/reward: published trades use 2:1 to 3:1 (e.g. entry -43.1, target -53, stop -40 = 3.2:1); size stops from tenor vol (1y vol 10-19bp across the US curve; spread-curve diff ~32bp/yr) and cut if realised vol doubles.
- Seasonals (year-end, January supply, quarter-end turns) are tactical: use the ex-month-end base for turns and treat n of 5-20 as weak evidence.

## Pitfalls
- Sign and direction: "widener/tightener" and "long spreads" differ by publisher; BofA/GS bond-minus-swap vs JPM/Citi swap-minus-bond. Reconcile legs before comparing.
- Definition drift: yield-yield (40bp) vs par/par (37.6bp) for the same bond; MMS and proceeds ASW diverge for low-price and zero-coupon bonds (P-STRIP May-50: MMS 69.9 vs proceeds ASW 122.6, GS screen Sep 2026); par ASW of two fair bonds differs by coupon unless swap and govt curves coincide.
- LIBOR-era ASW and OIS-ASW are not clean RV indicators (capital basis); a repo-vs-LIBOR "fair" ASW is a floor, not a point estimate.
- Specialness and benchmark effects create false outliers in SOFR-ASW and OTR spreads; a short in a special bond is negative carry ("right on the curve and still losing money").
- Regressions: published t-stats on overlapping changes (6M changes sampled daily/weekly) and on levels of persistent drivers (deposits, WAM, debt/GDP) are overstated: use HAC errors or non-overlapping data, and test the residual for stationarity before treating it as mean-reverting ([quant-cointegration](../quant-cointegration/SKILL.md)). In-sample, regime-dependent, short windows: 100% hit rates on small samples, rolling-mean targets drift, back-tests exclude costs, carry and stops; do not trade a residual when R2 is decaying.
- Ex-dividend gilts: accrued is negative and the next coupon belongs to the seller; drop it from the cash flows (`run()` does) or ASW is overstated by tens of bp.
- Funding legs: SOFR is an index (tri-party-like), actual repo is not always available (Sep 2019: 10% prints); hedging GC with SOFR leaves basis risk; term repo reduces funding volatility; haircuts and margin can change at short notice.
- Quarter-end/year-end and GSIB scoring distort repo and dealer behaviour: do not read a turn as trend. Clearing-mandate and SLR rules change: check the current status, do not quote deadlines from memory.
- Structural vs technical: regulation, buybacks and deficits persist; MBS/CTD/convexity sell-offs self-limit. Do not over-attribute to MBS (hedge need 0.5% of the UST market in 2021 vs 10% in 2003).
- Mean reversion is not guaranteed: 30y spreads went negative in 2008 before leverage rules and stayed there. Price a possible permanent regime shift.
- Mixing markets: EUR/UK/JP ASW levels embed local capital and haircut regimes; ECB haircut differences (Italy vs Germany ~47bp at 10y) and BoE haircut slope explain part of cross-market ASW differences.
- No sourced CHF, NOK or CAD spread levels in the knowledge base: ask for data rather than infer (see [g10-markets-and-snapshots](references/g10-markets-and-snapshots.md)).

## Output
Return (and write `swap_spreads`-shaped rows with `sign_convention`):
1. Table per instrument or tenor: measure, level bp (state S-G or G-S), 3m z, fitted/PCA residual, carry and roll per 3M (bp), 1y vol, carry/vol, fair-value gap with the model name, driver tags (funding / supply / regulation / flows).
2. The package by legs with DV01-neutral notionals, funding assumption, entry / target / stop and reward-to-risk, catalysts and the regime that kills the trade (see `rv-devils-advocate`).
3. Charts: spread by tenor with 1y percentile bands; spread curve (current vs 3m ago); TFP/ZDS history; residual z heatmap.
4. Hand-off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and [rv-devils-advocate](../rv-devils-advocate/SKILL.md). Label every historical number with its date and convention.

## Scripts
- [`scripts/asw.py`](scripts/asw.py): par/par and proceeds ASW, z-spread, matched-maturity spread, DV01 hedge ratio, TFP/ZDS cross-section, dislocation index; `run()` prices canonical `bond_static`/`bond_quotes`/`curve_zero` rows (nominal coupon bonds,
  curve rebased to settle) and emits `swap_spreads` rows. `python scripts/asw.py --help`. `--selftest` checks the Genworth 526.4/533.3 case, z-spread recovery, on-curve zero ASW through `run()`, TFP/ZDS recovery and the hedge ratio.

## Related skills
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md), [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): reserves/RRP drivers of front-end spreads; SOFR-FF and tenor basis legs.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md), [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md), [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md), [quant-cointegration](../quant-cointegration/SKILL.md), [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): PAI/IM discounting, forward spread grid, turns, residual stationarity, back-test hygiene.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): SLR, GSIB, haircut, margin and shadow cost of balance sheet.
- [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md): adjusted CDS, ASW vs CDS inequality.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): UST-Bund, EGB spreads, FX-hedged carry.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CME-LCH basis that sits inside swap-spread legs.
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): futures vs swaps, CTD-based hedging.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): GC vs special repo, SOFR-FF, quarter-end.
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): spline residuals, coupon effects, on/off-the-run.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md), [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): supply, buybacks, WAM.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md), [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): pensions, insurers, VA, convexity payers.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md), [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): spread-curve trades and PCA residuals.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md), [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md), [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): carry, DV01 bases, conventions.
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md), [xccy-basis](../xccy-basis/SKILL.md), [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): linker ASW, xccy link, bills.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md), [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md), [macro-fair-value-models](../macro-fair-value-models/SKILL.md): z-scores, half-lives, regression fair values.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), [rv-devils-advocate](../rv-devils-advocate/SKILL.md), [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

Reference files: [asw-structures-and-hedging](references/asw-structures-and-hedging.md) (measures, formulas, P&L bases, futures replication), [fair-value-and-capital-models](references/fair-value-and-capital-models.md)
(funding/credit/capital model, ROE grid, regressions, PCA, carry/vol), [g10-markets-and-snapshots](references/g10-markets-and-snapshots.md) (per-market notes, agency/SSA, dated levels), [trade-log](references/trade-log.md) (published trades with entry/target/stop).
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): CFTC, survey and real-money positioning.
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): swap-tape and dealer-flow inference.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): regression hedge ratios and fair values.

## References
- Huggins & Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): ASW as basis swap plus adjusted CDS, g x q x d capital basis, haircut costs, validity of spread measures, CCBS link.
- Huggins & Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): SOFR-ASW = expected specialness, repo-LIBOR sensitivity, Treasury vs SOFR futures strip.
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets, 4th ed. (Wiley, 2022): par/par and market-value ASW formulas, Genworth example, bond (forward-curve) spread.
- Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): sign conventions, par spread, I-spread, ASW types, repo-LIBOR floor, which spread to use.
- Boyarchenko, Gupta, Steele, Yen - Negative Swap Spreads (Federal Reserve Bank of New York Economic Policy Review, Oct 2018): SLR equity charge, ROE breakeven grid, widener carry.
- Fleckenstein & Longstaff - Treasury Richness (Journal of Finance, 2023): credit-adjusted convenience premium, SLR natural experiment.
- Treasury Borrowing Advisory Committee - Charge: Swap Spreads (Feb 2021): drivers by tenor, index choice, balance-sheet breakeven.
- J.P. Morgan - Buying back time (19 Aug 2026) and Global FI Markets Weekly (21-22 Aug 2026): TFP definition and fair-value model, 2y widener with PVBP hedge, GBP/AUD models.
- J.P. Morgan - Near, far, wherever yields are (2 Oct 2026); No alarms and no surprises (5 Nov 2025): ZDS/TFP signals, exit rule, deleveraging.
- J.P. Morgan - What about Bonds? SLR relief, Treasury supply, and long-end spreads (2 Apr 2020); The long and short of it (3 Aug 2018): 30y regressions, structural flow balance.
- J.P. Morgan - Is bank convexity hedging lying in wait? (31 May 2019); Dynamic hedgers are long, banks are short (13 Sep 2019): directionality beta, Tsy/OIS trades.
- BofA - A simple framework for swap spread relative value (2 Jun 2016): PCA fair value, dislocation indicator, back-test.
- BofA - Taking a look at SOFR spreads (6 Oct 2020); UST RV Primer (2 May 2022): spread decomposition, MMSS, drivers, ASW types.
- BofA - US Rates Alpha: buy 2y Treasury vs OIS (30 May 2018) and sell 2y spreads (27 Sep 2017): front-end drivers, trade levels, Fed framework mapping.
- BofA - Global inflation-linked primer, 2nd ed. (22 Jul 2025); UK Rates Viewpoint: Back to school (5 Sep 2024): linker/proceeds ASW, z-spread, gilt ASW switches.
- Barclays - Swap spreads: The Bright Spot in US rates (30 Sep 2026); US short interest rate primer (Jan 2025); Global Rates Weekly: The urgency question (2 Oct 2026): carry/vol hurdle, regulation, buybacks, forecasts.
- Citi Research - US Rates Weekly: Pension plan for 20s? (9 Oct 2026); All it takes is a little push (4 Oct 2019); The rocky road to a steeper curve (18 Jan 2019): spread screens, supply regressions, TIPS ASW, agency breakeven.
- Citi Research - European Rates Weekly: What to do about OATs? (1 Oct 2026); Higher yields are here to stay (24 Sep 2026); European Rates Strategy: Latest views (20 Aug 2026): EUR spreads, SSA/covered, Solvency II.
- Citi Research - Short-End Notes (21 Aug 2026) and FX Basis Quarterly (13 Dec 2024): 2y fair value, forward spread grid, PCA residuals, $ASW table.
- Clarus Financial Technology - Mechanics and Definitions of Spreadovers (11 May 2015); Mechanics of Asset Swaps and Government Bond Swap Spreads (18 May 2015); Spreadovers vs SOFR (23 Sep 2020): spreadover definition, sizing, direction.
- Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): ASW types worked example, capital by product, benchmarks by country.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed. (Harriman House, 2012): term TED replication, hedge ratios.
- swapsball.net - How to calculate carry and roll-down for a bond future's asset swap (12 Dec 2017): futures ASW and EFP carry/roll method.
- Conks - The Fed's Relief Valve: Part I (7 Mar 2025): swap spread as regulatory-cost gauge, binding-constraint logic.
- Golub & Tilman - Risk Management: Approaches for Fixed Income Markets (Wiley, 2000): swap-spread duration, directionality.
- BIS Quarterly Review - Goodbye Libor, hello basis traders (Dec 2025): hedge-fund swap-spread trade size bound.
- Quantitative Finance Stack Exchange - Calculating PnL on Swap Spread Trade (2018); Nomenclature for Swap Spreads (Nov 2024): risk-basis P&L, box naming.
- Also cited inline in the reference files: Rhodes - Trade Idea: USD 5s30s Swap Spread Flattener (9 Oct 2025); Willer & Saunders - Trading Global Macro Markets (Wiley, 2026); Burgess - Low Latency Interest Rate Markets (c. 2022);
  Shook - Yield Curve Spread Trades (CurveTrades/CME Group, Jun 2013); Federal Reserve Board - FEDS Notes: What Happens on Quarter-Ends in the Repo Market (6 Jun 2025); Bassman - Finding Sea-Level (27 Jan 2016);
  J.P. Morgan - The return of convexity hedging (31 Jan 2020), Asset Swaps (Feb 2006), Non-Stop Dynamics (21 Feb 2025); Citi Research - Corporate supply to bring spreads tighter (3 Jan 2017), Learning on the job (2 Aug 2019),
  The long end basket case (4 Feb 2015), US midterms on the mind (2 Oct 2026), Short-End Notes (27 Jun 2025); BofA - Fed's SLR proposal: underwhelming (25 Jun 2025), Bond market seasonality explained (6 Jun 2022),
  Funding & debt limit: history lessons (27 Jun 2025), Will retail discover Gilts? (10 Nov 2022), Scope for 10y EURUSD xccy basis tightening (27 Mar 2025); Goldman Sachs - Global Rates Trader (2 Oct 2026);
  Nordea - EUR Rates Flash (5 Feb 2020); Clarus - A Dummies Guide to Trading Interest Rate Swaps (19 Jun 2024), Swap Spreads For Dummies: The LIBOR Joke (23 Nov 2015), Swapalypse Now (14 Apr 2025);
  Crisil Coalition Greenwich - Fixed-income cross-margin opportunities (Q3 2025); swapsball.net - Testing for seasonality (19 Nov 2017); Tradeweb SEF Rulebook ch. 9.
