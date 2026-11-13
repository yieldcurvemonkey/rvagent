---
name: fut-invoice-spreads
description: 'Computes and trades invoice spreads (bond future vs a forward-starting, CTD-maturity-matched swap/OIS), futures-implied CTD yield, futures asset swaps (Bund/Bobl/Schatz, JGB, AUD EFP) and sizes CTD-based futures hedges (CF vs DV01, option-adjusted, P-weighted, yield-beta, tail, stub risk). Also covers conditional invoice trades (listed Board option vs CTD-matched swaption) and term TED (bond future vs STIR strip). Use when asked about invoice spread, futures vs swap, futures ASW, EFP, "sell 2y futures vs receive OIS", Schatz spread, Treasury futures vs swap spreads, hedge ratio or contracts per $100mm for a bond, CF-weighted vs DV01 hedge, CTD-based hedging, Board vs swaption, conditional widener, French vs German invoice spread, TED, futures roll DV01 mismatch. Basis, IRR and CTD: fut-bond-basis-and-implied-repo.'
---

# Invoice spreads and CTD-based futures hedging

A physically delivered bond future is a forward on the cheapest-to-deliver (CTD) bond minus a delivery option. An
invoice spread prices that forward against a swap that starts on the delivery date and matures with the CTD, so
the package is a swap spread (government credit vs bank/RFR credit) with the futures leg as the liquid, margined,
DV01-clean instrument. It exists because futures carry flows (supply, custody demand, convexity hedging, margin
offsets) that the swap market has to absorb. The same machinery (futures DV01, CTD probabilities, forward yields)
gives hedge ratios for cash bonds and for the swap leg. Edges are a few bp, so conventions and DV01 matching decide
whether a signal is real.

## When to use
- "Is the 10y futures vs swap spread cheap?", "sell 2y futures vs receive OIS", "Bund/Bobl/Schatz asset swap", "AUD 3y/10y EFP".
- "How many futures hedge $100mm of this bond/swap?", "CF hedge or DV01 hedge?", "futures DV01 near a CTD switch".
- Comparing the invoice spread with the CTD's cash swap spread, or carry/roll of a futures-vs-swap package.
- Conditional invoice trades (Board option vs swaption), term TED (bond future vs STIR strip), cross-country invoice spreads.
- Not here: implied repo, net basis, CF mechanics ([fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md)); CTD switch and delivery-option valuation ([fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md)); cash swap spreads ([spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Contract terms, delivery dates, notional coupon | `fut_static` | per contract month | use `last_delivery_date` (and `first_delivery_date`) as the swap effective date; check `settlement_type` (cash-settled yield contracts use the EFP form) |
| Basket and conversion factors | `fut_basket` (+ `bond_static`) | per contract, point-in-time | exchange CF, never recomputed unless validating; eligibility by date |
| Futures settles | `fut_quotes` | daily, one `snap` | settle for settle, never mixed with swap closes; record snap |
| Bond prices, yields, accrued | `bond_quotes` | daily, same snap | clean/accrued/dirty separate; `settle_date` |
| Term/specific repo | `repo_rates` | to delivery date, CTD's own `collateral` | own-issue repo for the forward, not GC (see Pitfalls) |
| Swap curve to build the forward-start swap | `curve_par` or `curve_zero` (+ `swap_conventions`) | start = delivery date, tenor = CTD remaining term | same snap as futures |
| Output / history of spreads | `swap_spreads` (`measure=invoice`) | daily, >= 2y for z-scores | store `sign_convention=swap_minus_govt` |
| Listed option and swaption vols | `opt_quotes`, `opt_static`, `vol_surface` | daily, >= 1y | normal vol in bp; Board vs CTD-matched swaption |
| Hedged bond/portfolio DV01 | `positions` | | signed DV01, positive = long duration |

If an input is missing, ask for it or hand off to the data adapter (see [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)). Never invent values. The basket file for the script is a join of `fut_basket`, `bond_static` and a forward yield per bond.

## Method

### 1. Conventions (fix these first)
- **Invoice spread (bp) = forward swap par rate (effective on the delivery date D, maturing on the CTD's maturity) minus the futures-implied forward yield of the CTD**: `inv = 100 * (S_fwd - y_F)`, `swap_minus_govt`. US: negative when swaps are below Treasuries. Positive = futures rich to swaps. This is the Citi and Bund-ASW convention (Citi, US Rate Strategy Notes, 4 Feb 2015; swapsball.net, Bobl ASW carry, 12 Dec 2017).
- **Cash ASW in EGB markets is govt minus swap, so the invoice spread has the opposite sign**; a wider ASW is a lower swap_minus_govt invoice spread (Citi, 4 Feb 2015). One source quotes the JGB futures ASW as CTD yield minus swap (0.150 - 0.330 = -18bp; J.P. Morgan, JGB future asset swap, 29 Jan 2015). Convert to `swap_minus_govt` on ingest and say which you used.
- Rates in %, spreads in bp, futures prices per 100, DV01 in currency per bp per contract (positive = long duration). Contract DV01 = DV01 per 100 face x contract face / 100 (the 2y note is $200k face, double the others).
- P&L of the package, in bp of invoice spread: **short futures + receive swap gains when `swap_minus_govt` falls; long futures + pay swap gains when it rises.** (J.P. Morgan, 28 Feb 2020, printed +2.0bp P&L on a short-futures/receive-OIS package entered at +13.9bp; that note's quote sign for the 2y package is not stated, so do not read +13.9 as swap_minus_govt. Its received 10y invoice at -5.95bp lost 2.5bp as the spread rose, consistent with the rule.)

### 2. Pick the CTD and the delivery date
- CTD = highest implied repo (equivalently the lowest forward price / CF; in the delivery month the lowest converted cash price). Never the lowest price, highest yield or lowest basis (Salomon Brothers, Understanding Treasury Bond Futures, Oct 1990). Mechanics live in [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md).
- Delivery date: the swap effective date is the date the CTD would be delivered. Positive carry -> last delivery day, negative carry -> first (BofA Global Research, US Treasury futures and basis primer, 10 Jul 2025). In a 2014 SDR study 2y/5y packages used the early-next-month date and 10y/Bond/Ultra the month-end date (Clarus, What's the Deal with Invoice Spreads, 17 Sep 2014). Take the dates from `fut_static`, confirm which the desk/CCP uses.
- A CTD tagged wrongly gives a wrong spread of the order of the CTD-vs-neighbour cheapness. Near a CTD cusp, compute the spread for the two leading candidates and report both (see section 7).

### 3. Futures-implied forward yield of the CTD
1. Invoice price = `F * CF + accrued`; clean = `F * CF` at the delivery date D.
2. Yield `y_F` solves `clean_price(y_F, coupon, n, w) = F * CF`, where n = coupons left after D, w = days to next coupon / days in the period (street compounding, `freq` coupons per year; accrued = coupon/freq * (1 - w)).
3. `python scripts/invoice_spread.py invoice ...` does steps 1-3 and the spread. Check by repricing: `clean_price(y_F) == F*CF`.

### 4. Matched forward swap and the "true" invoice spread
- Quick form: `S_fwd` = par rate of the swap with effective D and maturity = CTD maturity, from `curve_par` (start = D) or built from `curve_zero`, using the fixed-leg conventions in `swap_conventions`. Interpolate in maturity; do not round to the nearest tenor (a 3-month mismatch is several bp of curve slope).
- Compounding trap: UST yields are semi-annual ACT/ACT, SOFR/ESTR swaps annual ACT/360, BTPs pay semi-annually while EUR swaps pay annually over 2y (Alexander Düring, Fixed Income Trading and Risk Management, 2021). The yield form is only a screen. The consistent form is a forward par/par asset swap on the invoice price: with `DF(D,t) = DF(t)/DF(D)` from the RFR curve,
  `s_bp = 100 * [ sum_i CF_i * DF(D,t_i) - (F*CF + accrued) ] / A_D` (cash flows per 100 face; `A_D` = floating-leg annuity in years from D to the CTD maturity; 1 price point over a 6.5y annuity = 15.4bp); `inv_bp(swap_minus_govt) = -s_bp` (a bond cheap to the curve has s > 0, i.e. swaps below govt). The curve-consistent version (RiskVal's "true invoice spread") solves the floating spread so the NPV equals forward dirty price - 100, with Z-type variants discounting CTD cash flows from D on an RFR/OIS curve (RiskVal, Future CTD Scenario Analysis user guide, 25 Apr 2024). Verify the sign by checking that a bond priced exactly on the curve gives 0 (cross-check [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md)).
- AUD (cash-settled, quoted 100 - yield): EFP = spot-starting swap yield minus futures-implied yield, with no CTD; carry and roll are computed separately for the swap and basket legs because the dates differ (swapsball.net, 12 Dec 2017). The future's PVBP is a constant, so the hedge ratio vs the basket is not constant (Düring 2021).

### 5. Decompose before calling it rich or cheap
- **Identity (swap_minus_govt):** `inv = matched_fwd_spread - NB / DV01_fwd`, where `NB = forward CTD clean price - F*CF` (net basis, repo-adjusted, includes option value) and `DV01_fwd` is price per bp per 100 of the CTD at D. One tick (1/32) of net basis is about 0.45-0.5bp for a 7-10y CTD (DV01 about 0.064-0.07 per 100). In the ASW sign the invoice spread reads above the CTD's matched swap spread by the same amount. A Goldman Sachs UST asset-swap report shows exactly that gap: 7y CTD matched 33.8 vs invoice 35.6, 20y 64.9 vs 68.3, Ultra 69.6 vs 72 (GS, US Treasury Asset Swap Spreads, 25 Sep 2026; magnitudes quoted positive, so ASW sign; methodology not documented).
- So the invoice spread splits into (a) the CTD's swap spread (balance-sheet, supply, credit-of-government driver, handled in [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md)) and (b) the futures basis (delivery option, repo, squeeze). A gap between the two of 1-4bp is the normal basis; a gap far outside that range is a futures-basis or CTD-tag problem, not a swap-spread signal.
- Futures-leg "carry" is only MTM: improper futures carry = futures-implied forward yield - spot CTD yield; a 1-month futures roll equals the 1-month CTD roll (swapsball.net 2017; BofA 2025). Swap-leg carry = (swap rate - first fixing) / forward modified duration. Total package carry = both legs; omitting the futures leg because "a future is already a forward" is "very wrong" (swapsball.net 2017). Details in [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md).

### 6. Size the package (DV01-neutral)
- `N_fut = N_swap * DV01_swap_per_mm / DV01_fut_contract`, where the swap DV01 is that of the forward-starting swap and `DV01_fut` is from section 7. `python scripts/invoice_spread.py contracts ...`.
- Rule of thumb #1: `DV01_fut = DV01_fwd(CTD) / CF` (from F ~ forward price / CF). Burghardt: CTD DV01 59.14 per $100k, CF 0.9734 -> 60.76; hedging $10mm of a 10y with DV01 $7,762.40 -> 127.8 contracts (Burghardt, Belton, Lane, Papa, The Treasury Bond Basis, 3rd ed., 2005).
- Roll DV01 mismatch: the next contract has a different CTD and DV01 (long-end basket gap: 166 vs 252 per contract, so an equal-DV01 roll needs 34.1% fewer of the back contract; Citi, 4 Feb 2015). Re-size every roll, and record the CTD of both contracts.
- Variation margin accrues interest, so tail by the PV factor to the horizon; at delivery of a CF-weighted hedge buy back (CF > 1) or sell (CF < 1) the tail (Salomon 1990).

### 7. CTD-based hedging of a cash bond or swap with futures
1. **DV01 hedge:** sell `N = DV01_position / DV01_fut` contracts (long-duration position, DV01 > 0). For a bond that is not the CTD this is a **curve-and-basis trade versus the CTD**, not a clean hedge.
2. **CF is not the hedge ratio.** CF-weighting locks the cash-and-carry IRR but is DV01-neutral only for the CTD. Salomon's 11.75% Nov-2014 vs Dec-90: CF 1.3608 -> 1,361 contracts per $100mm, DV01 hedge `(0.1103/0.0931) * 1,000 = 1,185`. Lower-duration bonds need fewer contracts than CF implies. A CF-weighted basis tilts directionally, a DV01-neutral one does not (Salomon 1990; Burghardt 2005).
3. **Futures DV01 choice (defaults, with reason):**
   - Top CTD probability >= 80% and yields well away from a cusp: rule of thumb #1 (`CTD DV01 / CF`). Salomon: the futures track the CTD when vol is very low or yields are far from the notional coupon with one dominant CTD.
   - Otherwise **switch-adjusted DV01**: central difference of the zero-time-value futures price `min_i (fwd_i / CF_i)` over +-5bp parallel shifts (the script's `OA`; it ignores time value and is only smoothed by the +-5bp window; a full option-adjusted DV01 needs a delivery-option model, see [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md)); or **P-weighted DV01 = sum_i P(i is CTD) * DV01_i / CF_i** (J.P. Morgan, The switch and the spur, 29 Oct 2026). The script returns both (`basket`). Use the P-weighted form for hedge ratios near cusps.
   - Default trigger (own, from Burghardt Exh 5.10 where Jun-01 rule-of-thumb DV01 was ~9% off OA for the 10y near a crossover and 0.5-1% off for 2y/5y/bond; Sep-01 2y 3.7%, bond 1.8%): if `|RoT/OA - 1| > 3%`, hedge on OA/P-weighted.
   - The rule of thumb jumps at switches (to higher duration raises BPV discontinuously; convexity lowers it). Option-adjusted and P-weighted DV01 are smooth (the script's switch-only version only within its shift window). Near crossovers futures are negatively convex.
4. **Yield-beta hedge** for a bond with different yield sensitivity than the CTD: `HR_i = DV01_i * beta_i / (DV01_fut * beta_ctd)`. Burghardt: 7.5% 11/16, DV01 117.78, beta 1.1365, CTD DV01 145.45, beta 1.0857, futures DV01 122.42 vs the CTD yield -> HR 1.007. OTR 30y $100mm: 1,265 contracts (RoT) vs 1,121 (yield beta). Regression betas overcorrect when correlation < 1; choose the objective explicitly (zero DV01, minimum variance, or yield-delta).
5. **Stub (repo) risk:** the futures hedge leaves exposure to the term repo to delivery, repo DV01 / spot DV01 = 2% (bond), 3.8% (10y), 13% (2y); the 2y hedge needs a term-funding hedge (short-dated rate futures or term repo) (Burghardt 2005). Weekly changes in term repo and spot yields are almost unrelated (R^2 0.0018-0.025), so the two risks are independent.
6. **After the last trading day** the hedge is 1 par per contract; plan to fail in cash rather than in futures (Burghardt 2005).
7. For a hedged package with futures + swap legs, validate the DV01 match on forward-starting swap DV01 at D, not spot-starting swap DV01.
8. **Bond between two contracts:** hedge with two futures (they need not bracket the bond): `N1*DV01_F1 + N2*DV01_F2 = DV01_B` and `(m_B - m_F1)*N1*DV01_F1 = (m_F2 - m_B)*N2*DV01_F2` with m = CTD/bond maturity (Duering 2021). Zero-DV01 and zero-slope in maturity, not a full curve hedge.

### 8. Conditional invoice trades (Board option vs CTD-matched swaption)
- Structure: buy a Board put (call) and sell a payer (receiver) swaption on the CTD-matched swap, or the mirror. **Swaption notional ($mn) per 1,000 Board contracts = 100 * DV01_fut / DV01_swap, both DV01s per 100 face** (equivalently 1000 * $DV01 per contract / $DV01 per $1mm of swap; 4.72/4.01 -> 117.7; 7.52/6.25 -> 120.3; 20.94/16.44 -> 127.4; Citi Rates Vol Lab, 1 May 2017 and 9 Jan 2017). Delta-hedge daily at one snap.
- **Strike mapping:** swaption strike yield = Board strike yield + invoice spread. Compare vols only on the mapped strike (skew differs: Board puts trade above payers, Board calls below receivers; Citi, 12 Jun 2023).
- **Costless strike spread** = costless swaption strike - Board strike yield (bp). **Pick-up = invoice spread - strike spread** (all four printed examples use this sign although one source's text states the reverse; Citi 12 Mar 2018, 12 Jun 2023; J.P. Morgan 29 Oct 2026). Positive pick-up means the Board put is rich against the payer at the mapped strike (a lower payer strike is needed to fund it): it favours selling Board optionality and buying the swaption; negative favours buying Board vs selling the swaption. In the four printed examples both positive pick-ups had Board vol above payer vol (1.03, 1.05); the negatives had Board below (0.96) or level (142.8 vs 142.5), so the vol ratio and the pick-up are related but not interchangeable.
- **Vol comparison:** ATM Board normal vol (interpolated) vs CTD-matched swaption vol, each against its own 1m and 3m realised; compare the implied ratio with the recent realised futures/swap ratio. Implied above realised -> Board rich. Past Board-cheap episodes reverted quickly (Citi, 17 May 2019; 12 Dec 2016).
- Listed rates options are liquid to about 6m expiry; longer expiries trade OTC (BofA US Vol Primer, 11 Mar 2024).
- Table of printed examples: [references/worked_examples.md](references/worked_examples.md). Vol RV: [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md), [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md), [curve-conditional-trades](../curve-conditional-trades/SKILL.md).

### 9. Other futures-vs-swap/STIR structures
- **Term TED** (bond future vs STIR strip): strip yield `SY = [prod (1 + IFR_k * 0.25)]^(1/years) - 1`; futures-implied yield from `F*CF` settling at the futures delivery date; `TED = SY - y_F`. Widening view = buy the bond future/sell the STIR strip. A credit spread in disguise: stacks credit, forward start, CTD switch and curve risk; ~85% correlated with the 2y swap spread. Short term-TED positions are asymmetric (flight-to-quality blow-outs), and equal-weighted strip yields are not comparable with front-weighted bond yields (Stephen Aikin, STIR Futures, 2nd ed., 2012). Schatz/Euribor 4:5 lots is the exchange-margin approximation of DV01 neutrality, not exact (Aikin forum Q&A).
- **Schatz spread** = swap yield - Schatz CTD yield; "gadget" uses the 2y IMM swap (Clarus, Dummies Guide to IRS, 19 Jun 2024).
- **Cross-country invoice (EUR):** long French invoice vs 0.6x short German invoice, beta from a regression of French on German invoice spreads; in credit stress France trades as a hedging name (Astor Ridge, Trade Radar, 6 Mar 2022; marketing communication).
- **Ultra-10y/bond-future spread vs 5s30s:** 0.3294 * 5s30s - 6.55, R^2 0.948 (2016 onward; Citi, US Rates Weekly, 27 Mar 2020).
- **Inter-commodity spreads** use fixed DV01-derived ratios with margin offsets; absolute spread = curve spread / back yield; tail with an outright ([references/market_notes.md](references/market_notes.md)).

## Worked example
Illustrative, not market data: Dec-26 delivery D = 2026-12-31, CTD 4.25% 15-Aug-2034, CF 0.9000, futures 110.00. Clean invoice price 99.000, 16 coupons left, w = 0.25.
`python scripts/invoice_spread.py invoice --fut-price 110 --cf 0.9 --coupon-pct 4.25 --maturity 2034-08-15 --delivery 2026-12-31 --swap-fwd-pct 3.95` -> futures-implied yield 4.405%, `inv = 100*(3.95 - 4.405) = -45.5bp`. If the CTD's matched forward spread is -43.5bp the gap is 2.0bp, equal to about 4 ticks of net basis at DV01 0.064 per 100 (script output): normal. A -49bp matched spread would give gap = -49 - (-45.5) = -3.5bp (negative net basis): a basis or CTD-tag problem, not a swap-spread signal.

From sources:
- **Bobl ASW carry/roll (12 Dec 2017):** spot ASW 53.1bp; carry 53.7 - 53.1 = 0.6bp over 3m; roll from the Oct-22 bond toward Apr-22 55.8 - 53.7 = 2.1bp over 6m = 1.0bp per 3m (swapsball.net, 12 Dec 2017).
- **Short-futures/receive-OIS (26-28 Feb 2020):** sell 2y futures vs receive $576mn SOFR OIS at +13.9bp: +2.0bp (28 Feb), +4.1bp (6 Mar). Citi's sell-2y-futures vs OIS tightener: 50K DV01, entry -12.8bp, target -24bp, stop -7bp, thesis fed custody holdings -$109bn in a month (J.P. Morgan, 28 Feb and 6 Mar 2020; Citi, US Rates Weekly, 27 Mar 2020).
- **CTD jump (2015):** no long bonds were issued Feb 2001-Feb 2006; CME excluded the 5.375% Feb-31 (announced Dec 2013); CTD moved from 6.25% May-30 to 4.5% Feb-36; ASW differential moved ~12bp and the Jun vs Mar invoice spread widened 10bp (Citi, 4 Feb 2015).
- More: [references/worked_examples.md](references/worked_examples.md).

## Signals & interpretation
- **Rich/cheap rule:** compute `inv`, `matched_fwd_spread`, and `gap = matched - inv` (swap_minus_govt, so gap = NB/DV01). Signal the swap-spread leg only when the gap is inside its normal 1-4bp range; if outside, resolve the basket/repo/CTD cause first.
- **z-score and reversion:** z over >= 2y of daily data, with an estimated half-life (see [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md), [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md)). Z without a reversion speed is uninformative.
- **Stops:** set the stop wider than a CTD-switch jump (10-12bp in the 2015 example) if a switch is plausible before the horizon; exit on regime change even if the thesis holds: when the daily realised vol of a spread doubles (1.2 -> >2bp), add a swap-spread overlay or switch to same-issuer liquid positions (Astor Ridge 2022; J.P. Morgan 6 Mar 2020).
- **Flow drivers:** front-end futures lightened by bill and coupon supply, custody demand and flight-to-quality bids; the 2s/OIS leg should price off GC, not tri-party (SOFR is >55% tri-party by volume) (J.P. Morgan, 26 Feb 2020).
- **Board vs swaption:** implied Board/swaption ratios of 0.86-1.08 observed (27 Mar 2020: 5y 0.86, 30y 0.89, 10y 1.02; 2 Oct 2026: 1.03-1.08). Treat a ratio as a signal only against the matching realised ratio (Oct 2026: Board/3m-realised 1.57-1.73 vs futures/swap 3m-realised 1.04-1.08).
- **Priced-story check:** before trading a flow or supply view, check whether it is already in the vol ratio, in the expiry and in the tail switches (Citi, Rates Vol Lab, 5 Oct 2026).

## Pitfalls
- **Sign confusion** is the most common error: invoice spread (swap - govt) vs ASW (govt - swap); one JGB source prints the ASW sign. Write the convention into every output.
- **Net basis can be negative** (futures rich to forwards) from basis selling by asset managers to levered funds limited by dealer repo funding (BofA 2025); it is not free money when supply is tight: price it as P(fail) x gap.
- **Specials and term vs overnight repo** flip basis P&L sign; use the CTD's own term repo to delivery, and price the reverse repo on the short leg. Squeezes show as an IRR near funding rates, not only as negative net basis (Burghardt 2005; Düring 2021).
- **Option value** lowers futures; ignoring it makes futures look cheap. The switch option is the most valuable, wildcard and end-of-month smaller; valuation in [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md). Short CTD basis is short OTM options: a high hit rate is not evidence of richness.
- **Benchmark/CTD changes contaminate histories** (a benchmark change jumps a spread by the yield gap between old and new). Use constant-maturity or fixed-contract series and record the CTD.
- **Delivery quirks:** US 6% notional CF (the 1990 contract used 8%); Bund-type contracts have maturity buckets; gilt ex-dividend rules can remove a CTD mid-month; small baskets raise squeeze risk (Burghardt 2005 notes; BofA 2025).
- **Hedge ratios decay** as DV01s age: re-size on forward DV01 over the holding horizon; calibrate to minimise unexplained daily P&L, not today's fit. Duration-neutral across markets is meaningless (Düring 2021).
- **Margin and clearing:** futures vs swap packages gain portfolio-margin offsets (hypothetical maxima: 10y receive 60%, 30y receive 50%, SOFR futures vs swaps 77-78%; vendor-sponsored, units unverified; Coalition Greenwich, Portfolio Margining Imperative, Q4 2024). Offsets are capped across different CCPs; compare against the CCP basis ([spread-ccp-basis](../spread-ccp-basis/SKILL.md)).
- **Liquidity:** use DV01, not trade count; futures bid/offer gaps (Schatz tick 0.25-0.5bp vs swap tick ~0.1bp) show up as spread jumps; never leg a closing spread, go to the point of least liquidity first (Clarus 2024; Aikin 2012).
- **Source conflicts:** one vendor guide gives two wildcard intervals (6 vs 15 hours) and two forms of its wildcard formula, and uses a x3 FOMC-day vol multiplier as a default. Do not hard-code them.

## Output
Return a table per contract: `fut_id, delivery_date, CTD (+ runner-up), CF, F, y_F, S_fwd, invoice_bp (swap_minus_govt), matched_fwd_spread_bp, gap_bp, NB_ticks, z, half_life, carry_bp (swap, futures, total, 3m), roll_bp`, plus a hedge block `DV01_swap, DV01_fut (RoT / OA / P-weighted), contracts, tail, P(CTD) by bond`, and for conditional trades `strike_mapped, strike_spread, pick_up, Board vol, swaption vol, ratio vs realised`. State the sign convention, snaps, repo used and CTD tag. Write the series to `swap_spreads` (`measure=invoice`). Hand off the trade to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and the package to [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md).

## Scripts
- [`scripts/invoice_spread.py`](scripts/invoice_spread.py): pricer with street compounding, conversion factor, futures-implied yield, invoice spread (swap minus govt), futures DV01 (rule of thumb, option-adjusted, P-weighted from a joined basket file), contracts and swaption notional. `python scripts/invoice_spread.py --help`; `--selftest` checks a closed-form bond price, the published CF 1.2168 for the 10.375% bond, round trips and the sourced hedge arithmetic. OA and P-weighted use zero option value and a one-factor parallel/beta shift: they cover the switch option only.

## Related skills
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): CTD, IRR, net basis, forward prices feeding the futures leg
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): switch probabilities, delivery option value behind OA/P-weighted DV01
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): rolling the package between contracts
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): the cash swap spread leg and ASW definitions
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll of swap and futures legs
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 and key-rate risk of the swap leg
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market swap/bond/futures conventions
- [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md): futures basis as embedded vol vs option vol
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-based conditional structures
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR strips for term TED
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): GC vs special, tri-party, funding drivers
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): cross-CCP margin and basis for packages
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): legging and package execution
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): cross-country invoice spreads (French vs German) and betas
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): yield-beta and minimum-variance hedge ratios (regression direction)
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): RFR compounding in the swap/STIR-strip legs

## References
- Salomon Brothers (Bond Portfolio Analysis Group) - Understanding Treasury Bond Futures: Questions and Answers (Oct 1990): CF procedure and example, IRR/CTD rules, CF vs DV01 hedge, delivery options; 1990 parameters are historical.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): hedge algebra, rule-of-thumb vs option-adjusted DV01, yield beta, repo/stub risk, specials and squeezes.
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): delivery-option model, OABPV, spread vol, deliverability premia, JGB case.
- Alexander Duering - Fixed Income Trading and Risk Management (Wiley, 2021): DV01-neutral packages, par spreads, Italian coupon pitfall, AUD futures, squeeze and dislocation notes.
- Stephen Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): term TED, strip yield, execution rules.
- Stephen Aikin - "Welcome to STIR futures" forum Q&A archive (2006-2014): Schatz/Euribor and gilt/Short Sterling DV01 ratios.
- BofA Global Research - US Rates: Primer: US Treasury futures and basis (R. Axel, 10 Jul 2025): futures pricing with option value, IRR, wildcard rule, delivery-date convention, tail.
- J.P. Morgan - The switch and the spur: CTD switches in the Dec-26 bond and ultra-bond contracts (I. Ozil et al., 29 Oct 2026): P-weighted BPV, switch probabilities, conditional example.
- RiskVal Financial Solutions - RVFI user guide: Future CTD Scenario Analysis (25 Apr 2024) and Overview 201: Cash and Futures (12 Nov 2021): true invoice spread, Z-type spreads, calendar-roll fair value.
- Citi Research - US Rate Strategy Notes: The long end basket case (J. Mathai et al., 4 Feb 2015): invoice sign, CTD jump, roll DV01 mismatch.
- Clarus Financial Technology - What's the Deal with Invoice Spreads and How Active Are They? (T. Skarecky, 17 Sep 2014): three ways to trade, SDR counts, delivery-date pairs.
- Goldman Sachs - US Treasury Asset Swap Spreads (Macro Sales & Trading Strats, 25 Sep 2026; partial): invoice vs matched swap spread by CTD.
- swapsball.net - How to calculate carry and roll-down for a bond future's asset swap (12 Dec 2017) and Testing for seasonality (19 Nov 2017): Bund/Bobl ASW definition, AUD EFP carry/roll.
- Citi Research - Rates Vol Lab series (R. Bikbov, J. Williams et al.): Long Live Formosa (9 Jan 2017), Fair value vs seasonality (1 May 2017), The art of gamma hedging (12 Mar 2018), Convexity Meets Steepeners (19 Apr 2018), Year-Ahead (12 Dec 2016), Forward steepener and vol divergence (12 Jun 2023), Fading vega dislocations (5 Oct 2026): conditional invoice mapping, notionals, Board/swaption ratios.
- Citi Research - US Rates Weekly: Trade worries linger (17 May 2019) and Eat, pay, spend (27 Mar 2020): conditional Board-vs-swaption example; 2y-futures/OIS tightener and regressions.
- Citi Research - Rates Vol Lab: Liquidity, vega, and convexity (R. Bikbov, J. Williams, 30 Mar 2020) and Trading long-dated convexity (9 May 2019): Board/swaption levels and ratios.
- BofA Global Research - US Rates Primer: US Vol Primer: A Guide for the Perplexed (B. Braizinha, 11 Mar 2024): listed-vs-OTC conditional widener, ~6m listed liquidity.
- J.P. Morgan - North America Fixed Income Strategy: Renewed Formosa supply (21 Feb 2020), Markets struggle to feed the convexity beast (28 Feb 2020), A dollar funding market riddle (26 Feb 2020), Impossible to walk in this muck (6 Mar 2020): received-invoice and 2y-futures/OIS trades and P&L, SOFR composition.
- J.P. Morgan - Japan Rates Research: JGB future asset swap, front contract (29 Jan 2015): JGB futures ASW definition and level.
- Clarus Financial Technology - A Dummies Guide to Trading Interest Rate Swaps (C. Barnes, 19 Jun 2024): Schatz spread, gadget, friction.
- Astor Ridge - Trade Radar (6 Mar 2022; marketing communication): French vs German invoice regression and stress behaviour.
- Credit Suisse Fixed Income Research - US Treasuries Futures Focus: New Ultra Long Contract (A. Li, M. Chang, 28 Sep 2009): effect of basket size on delivery option, DV01 and convexity.
- CME Group - US Treasury Futures Inter-Commodity Spreads (Feb 2024) and CurveTrades - Yield Curve Spread Trades (A. Shook, Jun 2013): fixed-ratio spreads, margin offsets, tail.
- Coalition Greenwich - The Portfolio Margining Imperative for Interest-Rate Derivatives (Q4 2024) and Crisil Coalition Greenwich - Fixed-income cross-margin opportunities (Q3 2025): margin offsets, CCP basis.
