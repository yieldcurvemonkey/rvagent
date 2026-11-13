---
name: fi-risk-dv01-and-transforms
description: Rates risk measurement and re-expression - DV01/PV01/BPV/PVBP and modified duration, par vs zero vs forward risk, key-rate (KR01/KRD) and bucketed risk ladders, Jacobian (change-of-basis) transforms of risk and market moves into spreads, flies, forwards or liquid hedge buckets, re-bucketing, hedge-instrument mapping and sizing (bond-equivalents, futures hedge ratio, CB01), gamma and cross-gamma P&L, and VaR-minimising (CoVaR) hedges. Use when sizing or hedging a swap, bond, future or STIR position in DV01 or 5y-equivalents, asking "what is my 2s5s10s / forward / par exposure", converting a risk ladder to another basis, comparing DV01-neutral vs PCA- or VaR-neutral hedges, partial DV01, bucketed delta, risk bleed, convexity, hedge ratio, yield beta, or explaining P&L from a risk strip.
---

# DV01, key-rate risk and Jacobian transforms

Risk is a vector of sensitivities to a chosen set of curve variables, and the same position has different numbers in
different coordinates (par swap rates, zero rates, forwards, spreads and flies, PCs, liquid hedge instruments). This
skill computes DV01 and bucketed risk consistently, moves it between coordinate systems without breaking P&L (the
Jacobian transform), maps it onto hedge instruments, and measures what is left (gamma, cross-gamma, VaR). Every other
RV skill sizes legs in DV01; this is where the units, signs and bases are fixed.

## When to use
- "Size / DV01-neutralise this spread, fly, swap-spread, basis or box", "hedge ratio", "bond-equivalents", "5y-equivalent".
- "What is my exposure to 5s10s, 5y5y, the belly, a PC?", "re-bucket this ladder to 2y/5y/10y/30y", "key-rate / partial DV01".
- "How do I hedge this off-the-run or odd-tenor trade with benchmark instruments?", "risk bleed", "unexplained P&L".
- "Is DV01-neutral also PCA-neutral?", "what trade best reduces the VaR of this book?", gamma and convexity of a position.
- Futures and STIR contract DV01s, CTD-switch DV01 jumps, meeting (CB01) risk: summary here, detail in
  [futures-and-stir-risk](references/futures-and-stir-risk.md).

## Conventions (read first)
- **DV01** = `-dPV/dy` per 1bp, in currency, **positive for long duration** (long bond, long future, **receive fixed**).
  Linear P&L = `-DV01 x change(bp)`. Modified duration = `10,000 x DV01 / V` (DV01 and V in the same units, e.g. per 100 face with V the full price); DV01 = `ModD x V x 0.0001`.
  Aliases: PV01, BPV, PVBP, dollar duration, "risk". PV01 strictly means the value of a 1bp annuity; for a par swap
  DV01 = PV01 (Burgess, Electronic Rates Markets, May 2022).
- **Risk strip** `S` = DV01 per bucket (currency/bp), same sign as `positions.dv01_ccy`. Rates and spreads in bp.
  Curve spread A-B = longer minus shorter; fly 2s5s10s = 2 x 5y - 2y - 10y; "receive the belly" fly strip = (2y -1, 5y +2, 10y -1).
- **Sources differ**: Darbyshire and many Stack Exchange answers quote delta positive for *paid* fixed. Flip the sign
  when importing (gamma is unaffected: receive fixed = positive gamma). Duration/convexity: some sources divide convexity by
  price (Tuckman), others do not (Darbyshire d2P/dy2). Never mix.
- **Second order**: `dP ~ -S . dr + 0.5 dr' G dr`, `G_ij = d2P/dr_i dr_j` (currency per bp^2).
- **Jacobian orientation** (used everywhere below): `J[i, j] = d r_A[j] / d r_B[i]`; risk `S_B = J S_A`; moves
  `dr_B = pinv(J)^T dr_A` (inverse-transpose); then `S_B . dr_B = S_A . dr_A` exactly.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Holdings, signed DV01 per leg | `positions` (`instrument_id`, `dv01_ccy`, `ccy`) | end of day | the bucket ladder is *derived* from these (not a canonical table): `tenor`, `dv01_ccy`, same sign convention |
| Par OIS/swap rates by tenor (spot-starting 0D, 3M..30y, more if long-dated liabilities) | `curve_par` | daily, one `snap`, >= 100 daily changes (default 250 = 1y) | for `Q`; percent x 100 = bp |
| Built curve nodes (DFs) to reprice and bump | `curve_zero` (`build_id`, `interpolation`) | as-of snap | bump and re-solve through the *same* build used for pricing |
| Day counts, payment lags, float-leg conventions | `swap_conventions`, `rate_indices` | static | decide float-leg DV01 and fixing exposure |
| Bond cash flows, yields, dirty prices | `bond_static`, `bond_quotes` | daily | use dirty price in duration and hedge ratios |
| Futures, CTD basket, conversion factors | `fut_static`, `fut_basket`, `fut_quotes`, `stir_quotes` | daily | DV01 of a future = CTD DV01 / CF (see reference) |
| FX for multi-currency books | `fx_rates` | daily | convert P&L, not sensitivities (pitfalls) |

If an input is missing, ask for it or hand off to the data adapter (see [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)).
Never invent values.

## Method

### 1. DV01 of a single instrument
1. **Central difference, +-1bp**: `DV01 = -(P(y+1bp) - P(y-1bp)) / 2`. One-sided 0/+1bp is biased by convexity
   (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022). If gamma matters for the use, bump below 1bp and scale up,
   or use analytic/automatic derivatives; central difference doubles the cost for little gain (Darbyshire, Pricing and
   Trading Interest Rate Derivatives, 3rd ed., 2022).
2. **Bonds**: yield-based closed forms are fine for fixed cash flows (table in
   [gamma-and-var](references/gamma-and-var.md)). Rules of thumb at 2% yield: par 10y duration 9.0, 30y 22.5; DV01 per 100 face
   10y 0.09, 30y 0.22. Hedge in dirty price x ModD, never ratio of durations alone.
3. **Swaps**: par swap DV01 = fixed-leg annuity x 1bp x notional (PV01); off-market swaps need full revaluation because DF01 no
   longer nets out (receive 100mm 10y at 4% vs a 2% mid has DV01 99,000, not 90,000). Hedge fixed and floating legs **separately**:
   an overnight-compounded float leg has about zero DV01 (SOFR 0); a Euribor float leg is about zero to the next reset
   (0.005 for 6m vs 0.09 for a 10y 2% fixed leg) (Tuckman and Serrat, 2022).
4. **Futures and STIR**: bond future DV01 = CTD DV01 / CF (jumps at CTD crossovers: use option-adjusted or CTD-probability
   weighted); 3M STIR contract = notional x 0.0001 x 90/360 = 25 (USD or EUR) per bp, 1M SOFR 41.67. Numbers and traps in
   [futures-and-stir-risk](references/futures-and-stir-risk.md).
5. **Options**: use delta-adjusted DV01 plus gamma and vega (see [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md)).
6. **Aggregation**: DV01s add across positions; durations are MV-weighted; futures add DV01 but no market value.
   Express size in DV01 or 5y-equivalents (`notional x DV01 / DV01_5y`), never gross or net notional (CFTC data, Sep 2020, in
   Tuckman and Serrat, 4th ed., Table 13.1: USD 210.7tn notional is 137.1tn 5y-equivalents).

### 2. Choose the coordinates: par, zero or forward
| Basis | Best for | Weakness |
|---|---|---|
| **Par swap/bond rates** (calibrating instruments) | swap desk P&L explain, "bond-equivalent" hedges (hedge matrix is diagonal), liquid-hedge reading | leveraged: par risk of a forward is large and offsetting |
| **Zero rates / DFs** | model internals | not hedgeable; per-DF numbers look nonsensical |
| **Forward buckets** (1y1y, 5y5y; IMM forwards) | curve-shape exposure, RV sizing, options | does not map directly to liquid hedges; N buckets need N instruments and N equations |
| **Spreads/flies, PCs** | trade intent, factor limits | correlated (spreads) or sample-dependent (PCs) |

Rule: compute risk in the calibrating-instrument (par) basis, then transform to the basis the decision needs. State
the basis on every number. A parallel shift in one basis is not parallel in another (10y par swap 8.50 vs 8.38 for
forward vs par shifts), so totals compare only inside one basis. Coleman's 10y zero has par partials (-0.026, -0.105, -0.54, 7.597)
at (1y, 2y, 5y, 10y) summing to 6.926 versus zero-yield partials (0, 0, 0, 6.904) (Close Mountain Advisors, A Guide to Duration, DV01, and
Yield Curve Risk Transformations, 20 May 2011).

### 3. Bucketed (key-rate) ladder
1. **Standard grid, constant across time and books**: 3M (or t+2 3M), 6M, 1y, 2y, 3y, 4y, 5y, 7y, 10y, 15y, 20y, 25y, 30y;
   add 40y/50y where long-dated GBP/EUR liabilities swaps exist. Government key rates: 6m, 1, 2, 3, 5, 7, 10, 20, 30y.
   More keys than liquid hedges makes the ladder costly, fewer lets moves escape the framework.
2. **Per bucket**: bump one calibrating par rate by +-1bp, hold the others, re-solve through the production curve build,
   reprice, central-difference. New hedge swaps are at par, so each partial is hedged independently by the swap at that tenor.
   Prefer par rates to forwards for transparent P&L explain.
3. **Checks (house heuristics)**: bucket DV01s sum to the parallel DV01 within about 0.5% (investigate beyond ~1%; "up to some
   noise", material for unusual curve shapes); a par instrument on a node shows risk only at that node (script selftest); a
   seasoned or off-market swap leaks a little to other nodes via `(S - C) x` annuity change.
4. **Locality decides meaning**: log-linear DF is local, log-cubic is global (damped ripple through all forwards). A non-local
   fitter gives a 6y swap spurious 10y risk and a hedge containing 10y swaps by artifact. Use a local fitter or forward buckets.
5. **Short end**: use IMM forwards (8 contracts for small currencies, 12 for the most liquid; 6, 7, 10, 11, 14 are worst
   because of roll + leverage), static strategic knots (rolling knots create spurious P&L), then annual par 4y-10y, 12y...50y.
6. **Risk bleed**: as time passes a 4y swap becomes 3.5y and splits about 50/50 across 3y and 4y. It does not show in VaR;
   monitor `Open` vs `Close(t-1)` ladders. Reduce with wider input spacing or by timing hedges to tenor alignment.

### 4. Transform risk and moves (Jacobian)
1. Build `J` between two bases of the same size on the same instruments (columns = source instruments, rows = target
   coordinates, `J[i,j] = d r_A[j]/d r_B[i]`). Then `S_B = J S_A`, `dr_B = pinv(J)^T dr_A`, `Q_B = (J^+)^T Q_A J^+`;
   `c = sqrt(S' Q S)` is invariant. For P&L to add up risk and moves must transform as **inverse-transposes**.
2. **Par to forward**: `J[i,j] = A_fwd,i / A_par,j` where forward i lies inside par swap j, `A` = annuity (analytic delta) per
   bp; the inverse has entries `A_par/A_fwd` with alternating signs. Pricing identity `R_{i+j} A_{i+j} = R_i A_i + R_j A_j`.
   The longer the par tenor and the shorter the forward, the more leverage (long-end short forwards about 10x). Use numeric
   bumps when dates misalign or discount basis matters. Script: `par_to_fwd_jacobian`.
3. **Trader model (spreads, flies)**: unit strips as columns of `U`, `J = U^-1`; valid if square, all buckets covered, full rank. Use
   one personal model; the coordinates are correlated, so add VaR minimisation (step 8). Examples in
   [jacobian-and-bucketing](references/jacobian-and-bucketing.md).
4. **Onto instruments that are on the curve's knots** (Coleman): scale the price-Jacobian rows by 1/yield-DV01 and invert; revalue only
   the handful of vanilla instruments, not the portfolio. Instruments off the knots need a new curve.
5. **Lossless vs lossy**: lossless iff `J_B->A = J_A->B^-1`. Map complex to simple only, never simple to complex, never
   chain unless lossless, avoid very different models (knots, interpolation). Non-square: pseudo-inverse, validate on P&L.
6. **Across instrument types** (swaps onto bonds or futures with different discount curves): the map is subjective. Start with
   (multi-)linear regression of daily changes (beta Jacobian), expect multicollinearity, validate out of sample.
7. **Multi-curve/CSA**: express risk to calibrating instruments, bump every component of a max-rate (multi-CSA) curve; under a
   single RFR curve outright delta dominates, basis risk returns with foreign or cash-only CSAs
   ([fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md)).

### 5. Re-bucket / compress `r = M s`
- Default **linear-interpolation allocation** (each source bucket split between the adjoining target pillars; columns sum to
  1, total DV01 preserved; script `linear_rebucket`). Use non-linear curve re-bucketing (bump the target pillar through the real
  curve build) when the hedge must be accurate; PCA rows give factor risk, not tenor risk.
- Validate a reduced set **out of sample**: choose in sample, then compare P&L of reduced vs full strip over the next ~100 days.

### 6. Hedge-instrument mapping and sizing
1. **Two legs**: `F_B = -F_A x DV01_A / DV01_B`, in DV01 never duration ratio. If the legs have different yield betas the
   DV01 hedge implicitly assumes beta = 1; test it by regressing daily yield changes of the hedged leg (y) on the hedge
   instrument (x): `beta = rho sigma_y / sigma_x`, then `F_B = -F_A x beta x DV01_A / DV01_B`. This is the minimum-variance
   ratio; regressing x on y gives a different (wrong) ratio unless |rho| = 1 (Tuckman and Serrat, 2022, App. A6). Four defensible ratios: conventional (DV01), yield-beta, yield-delta,
   minimum variance (spread trades use conventional; formulas in the futures reference).
2. **n legs need n equations**: the first sets size (`N x DV01 = R`), the others hedge against every sub-trade (a fly hedged against
   outright and slope). Fly 50/50 DV01 split: wings `N_1 = (D_2/D_1) N_2 / 2`. State the direction (spreads: relative to the longest
   leg; flies: belly). Equal notionals leave net duration (10y DV01 is about double 5y). Highly asymmetric weights are a disguised
   slope trade. Weighting beyond DV01-neutral: [curve-butterflies](../curve-butterflies/SKILL.md),
   [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md).
3. **Exact bucket hedge**: solve `H n = -S` (`H` columns = unit DV01 strips of hedge instruments); with par partials and par
   hedges at the key tenors `H` is diagonal (script `hedge_exact`; bond-equivalents). A total-DV01 ("bond-equivalent") hedge
   leaves curve risk: $100 of a 10y annuity (DV01 1.46) hedged with about $32 of the 5y bond (1.46/4.61; the source prints 4.64, giving 0.3147) leaves
   forward-bucket exposure (-0.02, -0.05, -0.29, +0.36) with total 0 (Coleman 2011).
4. **Off-the-run or odd-tenor trades**: map the ladder onto benchmark buckets (step 5) or the min-cost hedge LP; residual
   interpolation risk and risk bleed remain, so charge for them.
5. **Horizon**: both legs' DV01 decay with time, short legs faster; size in forward DV01 over the holding period or rebalance. Re-hedge
   after about 20-25bp of rate move (CME); carry should be judged on the hedged position, not by re-weighting to manufacture carry (Düring,
   Fixed Income Trading and Risk Management, 2021; CME Group, Understanding Treasury Futures, Nov 2017).
6. **Factor-neutral** (PC1, PC2) hedges and PCA-weighted flies: formulas in [gamma-and-var](references/gamma-and-var.md) and
   [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md). DV01-neutral is not PC1-neutral (5y +1bp goes with 10y +0.87bp in the
   Bund example); hedge against all factors of lower order than the exposure wanted.

### 7. Second order
- Receive fixed has positive gamma, pay negative; longer tenor and more forward start means more gamma; off-market trades have
  an extra annuity (MTM) gamma. Single-figure swap gamma: `G ~ (h + i) x S / 10,000` per bp for annual forwards h..i (5y5y, S 50,000:
  16 x 5 = 80; DF-weighted 79.8) (Darbyshire, 2022). A single figure assumes a parallel move.
- Taylor explain `-S.dr + 0.5 dr'G dr` is "very accurate" for daily moves; reprice fully for large moves or long horizons. Hedging with a
  different product (swap vs future, ZCS vs IRS, other CSA) hedges delta not gamma. Cross-gamma grids, aggregation and the analytic
  route from forward-zero risks: [gamma-and-var](references/gamma-and-var.md).
- Duration drift `OAC - OAD^2`: hedged books with positive drift must sell rallies, so such securities usually cost carry.

### 8. VaR-style hedge optimisation
1. `Q` = covariance of daily bp changes of the par buckets (changes, not levels; >= 100 observations, default 250; one snap),
   `c = sqrt(S'QS)`, VaR95 = 1.645 c, VaR99 = 2.326 c. Allocation `diag(S) Q S / c` sums to c; a negative allocation is a
   diversifier, do not cut it. Linear only: ignores gamma.
2. **Single best trade** in bucket i: `t_i = -(QS)_i / Q_ii`; **restricted set h**: `-Q_hh^-1 Q_h. S`; **general hedge matrix**:
   `n = -(H'QH)^-1 H'QS` (script `varmin_hedge`, `single_trades`). Default hedge universe: the most-traded buckets
   (2y, 5y, 10y, 30y).
3. **Execute one at a time or at about 50% of each** and re-run: several full-size single-instrument trades can raise VaR.
4. If the best single hedge cuts c by only about 15%, the risk is relative-value (curve/fly) risk: hedge with spreads/flies from a
   trader model, not outrights. Directionality of an RV trade: PC-neutral, minimal-norm or CoVaR trade; more degrees of freedom
   lower VaR but move the trade away from its intended structure.
5. Hedge calibration criterion: minimise **unexplained daily P&L of the hedged position**, not best fit to today's curve. Exact
   multi-factor KRD hedges are unstable and ignore transaction costs; use optimisation with costs and constraints.

## Worked examples

**A. DV01, DV01-neutral hedge, convexity** (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022). Prices at -1/0/+1bp for the
NSC 4.10s of 2121: 100.1801 / 99.9390 / 99.6990, DV01 0.241 per 100, duration 24.1; UST 1.625s of 11/15/50: DV01 0.199. Long $10mm NSC
is hedged by selling 10mm x 0.241/0.199 = $12,110,553 of the Treasury; at +5bp the loss and gain are each about $120,500. For -100bp
duration alone gives +24.1%, with convexity 1,101 adds 5.5 to 29.6%, actual 30.978%: the DV01-matched long-NSC position profits in both
directions. Check by hand: Coleman's 10y 3.5% par bond (99.1664 at 3.6%, 100.8417 at 3.4%) has DV01 (100.8417 - 99.1664)/0.2 = 8.38 per
100bp, i.e. 0.0838 per bp (the script's `bond_dv01` reproduces it).

**B. Total-DV01 hedge leaves curve risk** (Coleman 2011). $100 of a 10y annuity: DV01 1.46 per 100bp, par-rate partials (0.03, 0.11,
0.54, 0.78) at (1y, 2y, 5y, 10y). Hedge instruments 1y 0.98, 2y 1.94, 5y 4.61, 10y 8.38 give a diagonal hedge matrix, so bond-equivalents
are partial / instrument DV01 = 0.03, 0.05, 0.12, 0.09 as printed (sell $0.09 of 10y, $0.12 of 5y, $0.05 of 2y, $0.03 of 1y per $1 of annuity; the
rounded partials give 0.057 for the 2y). A single 5y hedge (1.46/4.61 = $0.32 per $1 of annuity) only works if yields move together.

**C. Same trade, three bases, same P&L** (Quantitative Finance Stack Exchange, "Calculating PnL on Swap Spread Trade", Jul 2018; house signs). Short
bond DV01 -102, receive swap +99; yields +2.0bp (bond) and +1.7bp (swap): P&L = 102 x 2.0 - 99 x 1.7 = 35.7. In (bond-swap spread, swap) coordinates
`T = [[1,0],[1,1]]`: risk (-102, -3), moves `T^-T dr = (0.3, 1.7)`, P&L 30.6 + 5.1 = 35.7. Transforming only the risk, not the move, breaks it. Swap
traders prefer the spread+swap basis, bond traders spread+bond (delta in their native hedge). Wrong-way variant: mapping DV01 and bp moves through
standardised-data eigenvectors gave -131,025 where the correct self-check P&L was -6,280 (Quantitative Finance Stack Exchange, "Attribute P&L to PCA vectors (swaps)", Jan 2022).

**D. Par to forward** (Darbyshire, 3rd ed., Ex 10.1 and 10.4-10.5). Par analytic deltas 1y/2y/5y/10y = 0.988, 1.956, 4.747, 9.043, forward annuities
0.988, 0.968, 2.791, 4.296: entries 0.51 = 0.988/1.956 and 0.48 = 4.296/9.043 (source prints 0.47); inverse entries -1.02 = -0.988/0.968 and 2.10 = 9.043/4.296 (the script's `par_to_fwd_jacobian` reproduces them). With
J rows [1, .513, .346], [0, .487, .329], [0, 0, .325] a par strip (1y -820, 2y -1,100, 3y +4,000) becomes forwards (0, 780, 1,300) (source signs).

**E. VaR-minimising proxy hedge** (Darbyshire, 3rd ed., Ex 21.9; buckets 3M 10y, 3M 30y, OIS-basis 10y, OIS-basis 30y; legacy IBOR-era,
technique unchanged; house sign S = (+4,000, +18,000, +110,000, +290,000) pv01). `c = 133,153`. Restrict the hedge to the two 3M buckets:
pay 5,790 and 19,838 in those buckets: c falls from 133,153 to 101,958 (-23%; the script's selftest checks both numbers). The remaining risk
sits in the basis buckets the instrument set cannot reach.

**F. Futures and strips** (details in the reference). 10y-note future: $10mm bond with BPV $8,558 vs CTD BPV $63.78 per $100k, CF 0.8072: `0.8072 x 8,558 / 63.78 =
108.31`, sell 108; a CF-only ratio would give 75 (CME Group, Understanding Treasury Futures, Nov 2017). Receive USD 100mm 2y OIS vs 8 quarterly SOFR futures:
100/99/99/98/97/96/95/95 = 779 contracts, bump-and-reprice dPV 19,480.69 vs 779 x 25 = 19,475 (CME Group, Pricing and Hedging USD SOFR Swaps, 4 Jun 2025).

## Market differences that change the numbers
| Market | What differs for DV01 and hedging |
|---|---|
| USD | SOFR float leg DV01 0; OIS payment lag 2 business days; 3M SOFR future 25/bp, 1M 41.67; Treasury futures DV01 = CTD/CF with jump and negative convexity near switches; cleared-swap discounting moved from fed funds to SOFR at COB 16 Oct 2020 (older discount-curve risk differs); SOFR statistics have a break after Aug 2021, so estimate Q on later data |
| EUR | Euribor float leg is about zero to next reset (6m: 0.005), risk of Euribor swaps splits between ESTR discounting and Euribor forecasting; ESTR lag 1 day; Euribor future EUR 25/bp; Schatz/Bobl/Bund CTD-switch risk is minimal but a Buxl switch moved CF-adjusted DV01 +37% (OAT -7%, BTP +8%); Dutch/other EGBs hedged with German futures keep relative slope risk |
| GBP | SONIA lag 0; ACT/365 (vs ACT/360); 3M SONIA future GBP 12.50/bp (GBP 500k notional); IBOR-era basis cross-gamma gone after the move to SONIA; cross-CSA (USD cash CSA) cross-gamma remains; gilts ex-dividend accrued can be negative; a cited GBP bucketing study used 1y-60y swaps with 2y/5y/10y/30y hedge buckets (the most traded) |
| JPY | JGB futures basket (7-10.5y) has near-identical BPVs, CTD switches are common while the one-factor delivery option is about zero |
| AUD | cash-settled, yield-formula bond futures: DV01 per contract falls with the rate level (A$89.65 at 4% to 61.93 at 8%); meeting-step CB01 can differ from DV01 by more than 200% around a meeting (RBA example, 2007) |
| CHF | negative rates and a SARON forward curve below spot beyond about 22y (May 2021): forward-vs-spot DV01 drift can have the opposite sign |
| CAD, NZD, SEK, NOK | no market-specific material in the sources; take conventions from [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md). For FX-denominated risk compute P&L in the local currency, then convert (a NOK cash flow under EUR collateral has no sensitivity to the local NOK curve) |

## Signals & interpretation
- **Net vs gross**: gross/net DV01 ratio large means curve risk hidden inside a flat book; always show the ladder, not only net DV01.
- **Ladder reading**: small net delta can hide large opposing buckets; check sign convention before hedging.
- **Hedge adequacy (house heuristics)**: post-hedge c falls by at least 50% with at most 2-3 liquid instruments = mostly directional book;
  best single hedge under about 15% = relative-value risk (use spreads/flies); a hedge with low correlation to the book is a red flag even if
  partials match.
- **Unexplained P&L**: persistent unexplained P&L from a ladder-based explain means the risk model is mis-specified (interpolation,
  knots, missing foundation); investigate when unexplained exceeds about 5% of |P&L| over a week, or whenever it has a consistent sign.
- **Futures (house heuristic)**: if CF-adjusted DV01 of the next-best deliverable differs by more than about 5%, hedge with option-adjusted or
  CTD-probability-weighted DV01 and pre-plan the resize (Buxl +37% on a switch).
- **Meeting dates**: size meeting trades by CB01, not DV01, when a policy meeting sits inside the hedged period.

## Pitfalls
- **Total DV01 sizes the risk, not where it is**: equal-DV01 hedges leave curve risk (summed DV01 is wrong for a fly: long 50k/bp 5y vs
  25k each 2y and 10y is DV01-flat yet belly outperforms in a rally).
- **Move vs risk transforms**: transforming risk without the inverse-transpose of the moves breaks P&L; PCA of standardised data lives in
  z-space; run PCA on rate changes, not on PV01 of the book; a 3-PC truncation leaves a residual to report.
- **Lossy maps** (compression, off-knot instruments, swaps onto bonds) are one-way and model-dependent; never chain them.
- **Bases**: par partials, zero partials and forward buckets of one position all differ; check which one a limit or hedge ratio is in.
- **Duration is unstable for swaps** (PV near 0): use DV01; a float leg's duration is at most the time to the next reset.
- **Futures DV01 jumps** at CTD crossovers; repo DV01 (negative) is a separate risk, and spot and repo yields are nearly uncorrelated; tail
  by `1/(1 + r d/360)`; CF weighting matches only the CTD.
- **Yield beta unstable** (OTR 10y beta 2.88 in 1991, 0.46 in 1993); with rho < 1 yield-beta overcorrects; do not force PC1 to be parallel.
- **DV01-matched unwind** leaves curve risk and both counterparties' credit risk; hedging by adding offsets rather than unwinding grows gross size.
- **Hedges are dynamic**: DV01 falls as rates rise and with ageing; neutrality is instantaneous. Backward-looking betas may not hold over the
  hedge period.
- **VaR hedges**: covariance regime shifts (calm periods shrink PC vols = false comfort), netting vanishes in stress; use changes, matched
  horizon, positive-definite Q; smoothing lowers VaR artificially; VaR is linear (no gamma).
- **Cross-asset FX**: converting delta and gamma into another currency before computing P&L misstated EURSEK P&L by more than 5%; revalue in local
  currency and convert after.
- **Notional is not risk**; short-dated swaps inflate notional but carry little DV01.
- **Strip hedges of bonds** (SOFR futures vs Treasuries) work only while the bond-swap spread is stable (Mar 2020 miss about 20%).

## Output
Return, in this order, stating currency, DV01 sign convention and basis on every table:
1. **Risk ladder** table: bucket | DV01 (ccy/bp) | % of gross | cumulative; plus net DV01, gross DV01, 5y-equivalent notional, bucket-sum vs parallel check.
2. **Transform** (if asked): source basis, target basis, `J` (or its construction), `S_B`, whether lossless, and `S_B . dr_B = S_A . dr_A` check.
3. **Hedge proposal**: instrument | direction | notional | DV01 | residual strip | residual c and % cut | rebalance trigger (bp or date).
4. **Second order / VaR**: net gamma (and cross-gamma flag), `c`, VaR95/99 with lookback and snap, allocation, best single trade.
5. **Caveats**: interpolation/locality, bleed, futures switch exposure, meeting dates, parameters that were assumed.
Hand off sizing to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).

## Scripts
- [`scripts/risk_transform.py`](scripts/risk_transform.py): `transform_risk`/`transform_moves` (Jacobian), `par_to_fwd_jacobian`,
  `linear_rebucket`, `hedge_exact`, `covar` (c and Euler allocation), `varmin_hedge`, `single_trades`, `pnl_explain` (delta + gamma),
  `bond_dv01`, `bootstrap_annual`/`par_partials` (key-rate DV01 by bump and re-solve), `cov_from_curve_par` (Q from the canonical `curve_par`).
  CLI: `python scripts/risk_transform.py --risk ladder.csv --curve-par curve_par.parquet --curve-id <id> --snap <snap> --hedge-tenors 2Y,5Y,10Y,30Y`.
  `--selftest` checks published numbers (swap-spread P&L invariance, par-forward Jacobian, trader-model strips, VaR-minimising hedge,
  delta-gamma P&L, bond DV01, par-partial known answers) and exits non-zero on failure.

## Related skills
- [fi-curve-construction](../fi-curve-construction/SKILL.md): the curve build, interpolation and calibrating instruments that define "par risk".
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts, payment lags, float-leg and futures conventions per market.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): discounting/basis risk under CSA choices.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll compared per unit DV01.
- [curve-butterflies](../curve-butterflies/SKILL.md), [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): leg weights beyond DV01-neutral.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA loadings, PC-neutral hedges, P&L attribution to PCs.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-space RV that uses the par-to-forward transform.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md), [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md), [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md), [fut-calendar-roll](../fut-calendar-roll/SKILL.md): futures DV01, CTD risk and BPV-neutral rolls.
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md), [stir-futures-rv](../stir-futures-rv/SKILL.md), [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md), [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): STIR strips, fixing ladders, futures-vs-swap convexity, meeting (CB01) pricing.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md), [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md), [xccy-basis](../xccy-basis/SKILL.md): swap-spread and basis DV01.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md), [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): gamma, convexity value.
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md), [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): estimating Q and betas.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md), [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md), [port-portfolio-construction](../port-portfolio-construction/SKILL.md): DV01 budgets and scenarios.
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): P&L explain from risk.
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md), [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): packages and write-ups.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md), [eng-python-analytics-stack](../eng-python-analytics-stack/SKILL.md): inputs and coding conventions.

## References
- Thomas S. Coleman (Close Mountain Advisors) - A Guide to Duration, DV01, and Yield Curve Risk Transformations (20 May 2011): definitions, partials in par/zero/forward bases, inverse-Jacobian transform, compression.
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): risk-model design, par-forward Jacobians, trader models, gamma/cross-gamma, CoVaR and VaR-minimising hedges.
- J H M Darbyshire - Coding Interest Rates (c. 2024): par risk via curve Jacobian pseudo-inverse, analytic deltas, fixing exposure, FX P&L, automatic differentiation.
- Bruce Tuckman, Angel Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): DV01/convexity closed forms, key-rate '01s and hedging, forward-bucket and futures DV01.
- Alexander Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): n-leg sizing, curve-model hedges, forward PVBP, converted PVBP for futures.
- Doug Huggins, Christian Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): PCA hedge ratios, BPV vs factor neutrality, option-adjusted futures BPV.
- Doug Huggins, Christian Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): STIR BPVs, FOMC-neutral and jump-parameter hedges, strip hedges.
- Galen Burghardt, Terrence Belton, Morton Lane, John Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): OA vs rule-of-thumb futures DV01, repo DV01, yield-beta hedge ratios, augmented duration.
- CME Group - Understanding Treasury Futures (Nov 2017), Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures (4 Jun 2025) and SOFR Discounting Transition Process for Cleared Swaps (2 Jun 2020): BPV hedge ratios, bump-and-reprice strip hedge, convexity P&L, discounting change.
- Salomon Brothers - Understanding Treasury Bond Futures: Questions and Answers (Oct 1990), Understanding Duration and Volatility (R. W. Kopprasch, Sep 1985) and Understanding the Yield Curve Parts 5 and 7 (A. Ilmanen, Sep 1995 and Feb 1996): forward-DV01/CF hedges, PVBP with yield beta, convexity and bp-vol.
- Bennett Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023, partial): KRD shock shapes, duration drift, unstable exact hedges.
- Bennett Golub, Leo Tilman - Risk Management: Approaches for Fixed Income Markets (Wiley, 2000, partial): KTRD vs KRD, optimised futures hedges, PC rules.
- K. Musaelian, S. Nagarajan, D. Villani - PCA: invariant risk metrics and representation of residuals for bond returns (SSRN, 2016): delta-gamma invariant metric, flylets.
- Credit Suisse Fixed Income Research - PCA Unleashed: The application of PCA across European Rates markets (24 Oct 2012) and US Treasuries Futures Focus: New Ultra Long Contract (28 Sep 2009): PCA hedge ratios, futures vs swap DV01/convexity.
- Lehman Brothers - The Short-End of the Curve (Chris Pulman, 10 Jul 2007): CB01 meeting Jacobian, bucketing comparison.
- Stephen Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): BPV hedges, tailing factor, strip hedges.
- J.P. Morgan Global Markets Strategy - The switch and the spur (29 Oct 2026) and Eurex CTDs wobble with higher yields (2 Oct 2026): CTD-probability-weighted BPV, CF-adjusted DV01 jumps.
- Nicholas Burgess - Electronic Rates Markets and Low Latency Interest Rate Swap Calculations (SSRN, May 2022): DV01 = PV01 + DF01, USD PV01 table.
- McPhail, Schnabl, Tuckman - Do Banks Hedge Using Interest Rate Swaps? (CFTC OCE Staff Paper 2019-011, 10 Apr 2023): DV01 as the risk measure for bank swap books, DV01 to P&L volatility.
- Ametrano, Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping (SSRN, 2 Apr 2013): curve Jacobian, hedge redistribution.
- Quantitative Finance Stack Exchange threads (2016-2024): "Attribute P&L to PCA vectors (swaps)", "Calculating PnL on Swap Spread Trade", "Can PCA be used to transform a ladder of interest rate risk?", "PCA for Risk bucketing", "PCA and risk bucketing" (Nov 2019), "How to measure Steepener/Flattener/Butterfly sensitivity? (in 01)" (Oct 2021), "Projecting swap risk on bonds and futures", "DV01 on LIBOR vs. SOFR basis Swaps": basis-change P&L invariance, custom Jacobian ladders, bucket re-mapping, restricted-bucket VaR hedges.
- Clarus Financial Technology - Mechanics and Definitions of Spread and Butterfly Swap Packages (14 Oct 2014) and of Spreadovers (11 May 2015): DV01-neutral package sizing.
- Convexity Maven (Harley Bassman) - "Got Duration ?" (19 Feb 2025): risk = duration x price.
- John C. Hull - Options, Futures, and Other Derivatives, ch. 31 (9th ed., Pearson): short-rate duration.
