---
name: bond-rich-cheap-fitted-curve
description: 'Fits a smooth government-bond curve (Nelson-Siegel-Svensson, exponential or cubic spline on the discount function, optional coupon/deliverability/age/size regressors) and turns each bond''s residual into a rich/cheap number in bp with z-score, leave-one-out check and switch/fly construction. Covers par and zero curves, spline spread vs z-spread vs ASW, on/off-the-run and benchmark premium, repo specials, CTD richness, coupon and tax effects (low-coupon gilts), linker seasonality and RMSE dispersion. Use when asked whether a bond is rich or cheap, for fitted-curve or spline residuals, bond switches, olds vs currents, benchmark discount/roll, auction RV vs fitted curve, coupon-adjusted spread, par curve model, curve dispersion, or issue selection for a curve trade. ASW and z-spread screens by bond: spread-swap-spreads-and-asw.'
---

# Bond rich/cheap versus a fitted curve

A fitted curve is a smooth, tradable-ish price of time. Each bond's gap to it is that bond's rich/cheap, and the gap
mean-reverts only when it is driven by something transient (supply, flow, a dealer position) rather than something
structural (coupon, tax, specialness, deliverability, free float). The craft is therefore (1) a basket and model that do not
manufacture residuals, (2) a spread measure that matches the hedge, and (3) an honest filter for the structural explanations
before any switch or fly is proposed.

## When to use
- "Is the 10y Gilt/Bund/UST cheap?", "which 7-10y bond is cheapest?", "rank the curve by spline residual".
- Bond switch (cheap vs rich bond, same sector), olds-vs-currents, OTR vs off-the-run, benchmark discount / benchmark roll.
- Auction screens: new line vs fitted curve, vs surrounds (fly), vs peer issuer.
- Coupon-effect questions: low-coupon vs high-coupon gilt, tax-driven richness, coupon-adjusted spread.
- Choosing the instrument for a curve trade (buy the cheap 10y, not the benchmark 10y).
- Monitoring curve dispersion (RMSE) as a liquidity gauge.
For swap-vs-bond levels use [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md); for futures/CTD mechanics
[fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Bond reference (coupon, frequency, day count, issue/maturity, amount out, ex-div rule) | `bond_static` | point-in-time (`valid_from`) | universe on date d: `issue_date <= d < maturity_date` |
| Clean price, accrued, dirty price, settle date | `bond_quotes` | daily, one snap per series, ≥ 3m (≥ 1y for z-score stability) | never mix snaps; `abs(dirty − clean − accrued) < 1e-4` |
| GC and bond-specific repo | `repo_rates` | daily, terms ON-3M | specialness_bp = (GC − rate)·100; needed for specials filter and carry |
| Deliverable baskets, conversion factors | `fut_basket` | per contract | deliverability regressor, CTD flag |
| Auction results and reopenings | `auctions` | event | OTR/rank and auction-cycle clock |
| Swap/ASW levels (optional) | `swap_spreads`, `curve_par` | daily | alternative hedge-based measure; carry on fitted curve |
| Free float = outstanding − central-bank holdings − stripped amount | `bond_static` (`amount_out_ccy`), `bond_holdings` (`holder` = central_bank, stripped) | monthly | use the holdings known at the date (`pub_ts_utc`); if absent, weight by `amount_out_ccy` and say so |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values. Minimum per fit: ≥ 8 bonds
spanning the target sector (≥ 12 for a 6-parameter NSS; a 12-knot spline needs ~60+). Details of the contract:
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Method

### 0. Sign and unit conventions (state them in every output)
- `spread_bp = y_mkt − y_model` (fitted-yield residual, bp). **Positive = cheap** (yield above curve, bond price below curve).
  Same as spline spread / z-spread (Düring, Fixed Income Trading and Risk Management, 2021, Ch.22).
- `price_gap = P_mkt − P_model` per 100 face, dirty. **Positive = rich.** (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022, Ch.1.)
  Link: `spread_bp ≈ −1e4·price_gap / (P_dirty·D_mod)`.
- Forward-curve bond spread (Tuckman): negative = rich. OAS: positive = cheap. Sources disagree, so print the sign next to every number.
- DV01 positive for long bond. "Buy the cheap bond" = long positive-`spread_bp` bond. ASW sign per `swap_spreads.sign_convention`.
- Rates and spreads in bp, prices per 100, times in years (ACT/365.25 is fine for fitting; use the bond's own day count for accrued and yield).

### 1. Pick the purpose, then the basket
Purpose changes the basket (J.P. Morgan par-curve notes 2018/2024; Huggins & Schaller 2024):
- **Issue RV / switches**: exclude what carries a liquidity or financing premium so the curve is a clean "ordinary bond" price, then
  read the excluded bonds as spreads to it (their premium is the signal).
- **Benchmark par curve for carry/rolldown/ASW input**: include benchmarks, because the "true" curve sits between the most- and
  least-liquid curves and mixing all bonds is likely closer than either extreme (Düring 2021, Ch.19).

Default filter (USD, derived from the J.P. Morgan par curve): drop (1) on-the-runs, olds and double-olds in 2/3/5/7/10y (20y too from
2024); keep old 30y, drop the current 30y; (2) bonds special in repo (6m repo ≥ 25bp below GC); (3) < 1y to maturity (money-market
holders, different supply/demand) and anchor the short end with GC repo (linear in the 0-6m region, `d(0.5)` pinned to the 6m GC
factor); (4) FRNs, strips, callables, linkers; (5) **very low free float**: original-issue 30y bonds issued > 20y ago with free float of ~US$5bn or less. Removing this class cut
average RMSE 3.8bp to 2bp (J.P. Morgan, The (par) curves they are a-changin', 23 Jul 2024). Every bond in the 2024 list of < $8bn float was
rich vs the curve (−84bp for $2.5bn float, −58bp $2.3bn, −47bp $3.2bn): scarcity, not RV.
In EUR and JPY keep benchmarks/CTDs in the fit and use a deliverability regressor instead: there is no OTR premium and the most
liquid bonds are the CTDs (Düring 2021, Ch.18, 28). Excluding OTRs/CTDs biases the curve (Düring 2021, Ch.19).

### 2. Pick the model (and check it)
| Situation | Default | Why |
|---|---|---|
| 10-40 bonds (CAD, AUD, NZD, SEK, NOK, CHF, small EGBs) | NSS, 6 params, `λ ∈ [0.05, 30]`, 4 multi-starts | few bonds, smooth, hump-limited |
| 60+ bonds (UST, Bund, OAT, BTP, gilt, JGB) | cubic spline on discount function, **12 knots at benchmark maturities and midpoints**, fit `ln d` | RMSE falls to ~10-15 knots then overfits (curvature jumps between 15 and 20) |
| Extrapolation beyond last bond (new 50y) | exponential spline, ~7 terms | well-defined limit as t→∞ |
| Thin issuer (agency, province) | sovereign curve × composite spread spline (polynomial zero spread, k=2) | avoids overfitting |
| Fly screening on dense bonds | local fit in a ~10y window, Huber IRLS (c=1.5, ~6 iterations), coupon as regressor | whole-curve splines have too few knots at the long end |

NSS check: if `|λ1 − λ2| < 1y` or `b3 ≈ −b4` with large magnitude, refit NS (poor identification; Düring 2021, Ch.19).
Spline check: every knot interval must contain data (Schoenberg-Whitney) or the fit is singular.
Exact-fit bootstraps are for swaps; for bonds they pass noise into forwards and zero out the residual you want.
Equations and parameter defaults: [references/models-and-formulas.md](references/models-and-formulas.md).

### 3. Objective: fit yields, not prices
`P̂_i = Σ_j CF_ij·d(t_ij)` on dirty price with actual cash flows from the settlement date; drop the next coupon if ex-div.
Minimise `Σ_i [ (P̂_i − P_i) / (P_i·D_i) ]²` (≈ squared yield errors; Düring 2021, eq. 19.33 uses `/DV01²`). Equal price
weighting lets long bonds dominate and left −8bp yield errors at ~1.5y in the legacy J.P. Morgan model.
Optional liquidity weights: `DV01 × free float` (US), `issue size × DV01` (EUR, no holdings data). Robustness: soft-L1 or Huber so
the dislocated bond does not pull the curve to itself; avoid iterative trimming (changes the sample daily). Prefer flagging outliers for
manual check.

### 4. Explain before you trade: joint fit with regressors
Add `γ_k·x_ik` to the pricing equation and fit curve and `γ` together (Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024, Ch.8):
- **Deliverability**: `x = BPV` if deliverable into the near contract else 0; `γ` reads "bp rich when deliverable".
- **Issue size** (benchmark effect), **age** (cheapens with time), **repo specialness**, **coupon** (or fit on duration, not maturity).
Bund, 7 Dec 2012: deliverables 2-4bp rich (Schatz 3.6, Bobl 2.8, Bund 2.1, Buxl 2.4bp), +2.5 cents per extra EUR 1bn outstanding,
−2.7 cents per year of age, mean absolute residual 0.9bp. A bond whose residual vanishes once these are in is a known premium, not RV.

### 5. Residual measure (match the hedge)
| Bond | Measure | Why |
|---|---|---|
| Govvy vs govvy | spline spread / fitted-yield residual (default) | hedge is other govvies |
| SSA, agency | Z-spread vs govt spline (most euro SSAs vs French, not German) | G-spread not comparable across benchmarks |
| Covered, senior bank, corporate | ASW / I-spread | hedged with swaps |
| Linker | linker z-spread / seasonally adjusted real yield | see Pitfalls |
| Govvy hedged with swaps | ASW-Z, then fit a spline through ASW-Z and use the residual to that | removes always-rich/always-cheap bonds |
Price distance alone ignores duration; yield spreads between different coupons are contaminated (see step 6).

### 6. Coupon and curve-shape effects
On an upward-sloping curve the higher-coupon bond yields less (0%: 10.0000%, 5%: 9.7203%, 9.5023% par: 9.5023%, Tuckman & Serrat 2022, Ch.3). So
a raw yield, interpolated swap spread or par ASW comparison makes the high coupon look rich. Defences, in order: fitted-curve residual
(prices cash flows individually); coupon regressor; original issues only; yield against duration (not maturity) as the plot axis;
STRIPS-based coupon adjustment where a strip market exists.

### 7. Standardise and test persistence
Per bond, rolling z of `spread_bp`: default window 63 business days (one quarter; short enough to follow regimes), min 20 observations; report
median and percentile alongside. A z of 2 says little by itself (Huggins & Schaller 2024, Ch.8): also compute OU half-life and
ex-ante reversion Sharpe over the intended horizon (see [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md)), and bucket by level if
residual variance depends on maturity. Run mean-reversion tests on constant-maturity series or fixed bonds, never on rolling generics. The z at close `t` includes day `t`: act on it from `t+1`
and size tests for autocorrelated residuals (daily residuals are not independent; overlapping windows overstate significance).
Also check "mean-reversion frequency" (times the spread crossed its mean in 3m): a bond that never crosses is persistently rich/cheap,
a level not an event (RiskVal, Overview 201, 12 Nov 2021).

### 8. Leave-one-out and robustness
Re-price each bond off a curve fitted without it (n+1 fits). A discrepancy in-sample may be curve-estimation error. Treat the first
and last bonds as extrapolations. Re-run with shifted knots or a different family: if the signal moves, node placement created it
(Citi, Going nuclear on the curve, 3 Feb 2017). If every bond in a "cheap sector" is rich, the model is wrong.

### 9. From residual to trade
- **Micro switch**: long cheap / short rich bond, duration gap small (< ~6 months), same sector, `N1·DV01_1 = −N2·DV01_2`. Use several
  metrics, plus carry, plus a reason (BofA, UST RV Primer, 2 May 2022). DV01-neutral is not convexity-neutral.
- **Fly** (cheap belly): `w = [−a, +1, −(1−a)]`, `a = (M_back − M_belly)/(M_back − M_front)` is maturity-neutral; use DV01 or PCA weights when the
  legs differ in duration. Picking the wings that maximise the richness gap is a selection step: it inflates the in-sample gap, so test the rule out of sample. Keep all legs in one curve sector.
- **Curve-hedged bond spread** (Düring 2021, Ch.32): `N1·PVBP1 = −N2·PVBP2`, `N_F1·PVBP_F1 = −N_F2·PVBP_F2`, `N1·PVBP1 = −N_F1·PVBP_F1`,
  e.g. a 3y vs 4y bond spread hedged with 2y and 5y futures.
- **Instrument selection overlay**: a 2s10s steepener in bonds = sell the expensive 10y, buy the cheap 2y.
- **Expected return** (Salomon, Understanding the Yield Curve Part 6, Nov 1995): local rich/cheap = financing advantage (GC 3m − special 3m)/4 +
  spread to model par/4 + expected cheapening; the 10y OTR was positive only because its repo advantage (0.463) beat richness (−0.037) and
  expected cheapening (−0.401). Always include bond-specific repo in carry; carry+roll compared raw within one curve, vol-normalised only across issuers.
- **Cost gate**: expected reversion must beat round-trip cost. Half-spreads by maturity (public bid/offer, yield bp, illustrative): 0-3y 0.6, 3-5y 0.24,
  5-7y 0.16, 7-10y 0.11, 10-20y 0.37, 20y+ 0.16; a 3-leg fly ≈ 1.3bp round trip. Real trades > $50mm cost ~1.7× the median
  (Federal Reserve FEDS 2025-049, 7 Jul 2025: effective bid-ask, a full spread, median 0.37bp, 0.62bp above $50mm, 95th percentile 12.4bp).

## Worked example
1. **Law-of-one-price table** (Tuckman & Serrat, Fixed Income Securities, 2022, UST 14 May 2021): rich(+) per 100 face of 2.0s Nov-21 +0.0030, 8.0s Nov-21
   +0.0984, 1.75s May-22 +0.0017, 7.625s Nov-22 +0.1172, 1.75s May-23 −0.0026, 7.5s Nov-24 +0.2314. Old high coupons rich (income demand at low rates).
   The 7.625s Nov-22 replicates with three on-the-run-like bonds for 111.2797 vs market 111.3969: 0.1172 per 100 or $586k on $500mm, before bid-ask,
   financing and idiosyncratic demand. Not an arbitrage. Its bond spread is −7.27bp.
2. **Coupon switch, gilts** (BofA, Liquid Insight 10 Nov 2022; UK Rates Alpha 5 Aug 2024): sell 4.125% 2027 / buy 0.125% 2028 as the spread of OIS z-spreads
   (low minus high coupon): entry +1.8bp, target −25bp, stop +12bp; closed −25.4bp. Driver: 5bp a year of tax on a 12.5bp coupon (40% taxpayer);
   scarcity (four 1/8% gilts at entry, two by Aug 2024). Risk: new issue accrues benchmark premium; retail tax change. Check: `spread_bp` of
   each leg to a coupon-regressed fit should explain most of the z-spread gap.
3. **Joint fit** (Huggins & Schaller 2024, Ch.8, Bund 7 Dec 2012): above. After deliverability, size and age, residuals: mean absolute 0.9bp, extremes
   +2.3/−2.2bp. A raw 2-4bp "cheap" read on a non-deliverable Schatz/Bobl-sector bond is mostly the missing deliverability premium; it is not RV until it survives the regressors.
4. **Expected-return framing** (Salomon 1995, 26 Sep 1995, 3m): 10y local rich/cheap = 0.463 − 0.037 − 0.401 = +0.025.
5. More tables (RMSE by bucket, OTR yield-error spreads, specials cycle, CTD premium, auction dashboards): [references/evidence-and-numbers.md](references/evidence-and-numbers.md).

## Signals & interpretation
| Observation | Reading | Action |
|---|---|---|
| `|z_3m| > 2` and residual > 1.5 × typical dispersion (RMSE) | candidate (flag rule used on dealer screens: red below −2, green above +2) | run steps 4-8 before anything else |
| Residual large, z small | persistently rich/cheap (scarcity, specials) | do not fade; consider the structural premium as the carry |
| Residual explained by deliverability/age/size | known premium | adjust fair value, no trade |
| `|z|` shrinking (turn started) with signal `|z|·σ` ≥ ~3bp (σ = EWM std of the fly level, bp) | entry window: buy the turn, not the extreme (one cash-bond fly study) | size by liquidity and half-spread |
| Exit | z back inside 0.5, or signal `|z|·σ` at or below the carry/financing hurdle (2.5bp repo penalty in that study; round-trip cost of a 3-leg fly is ~1.3bp) | take profit; mean reversion has worked |
| Fit RMSE up while bid-offer flat | macro depth fading or basket artefact | check basket (low float inflates RMSE) before calling stress |
| CTD rich vs fitted by ~0.6-1.2bp | expected CTD premium | no trade unless above the range; it should cheapen into the roll |
| Whole sector residual moves together | slope/sector effect, not issue-specific | regress on sector slope (R² 0.65 for May-30, 3.9sd residual = idiosyncratic) |
Normal UST par-curve RMSE 1-3.5bp, crisis peak ~16bp (J.P. Morgan 2016); Düring's 7-15y spline-dispersion indicator is typically 1-2bp, 4-5.5bp in 2010-11, ~9bp spike in 2019 (Düring 2021, Ch.18; chart reads). OTR premium is largely gone post-2008 (10y excepted);
do not assume OTR rich (Fleckenstein & Longstaff, Treasury Richness, 2023). Monthly 2/3/5/7y OTRs cheapen into the next auction (~0.7bp in the last two weeks),
10s/30s the opposite; roll ranges 1-2.5bp (J.P. Morgan, Times like these, 10 Feb 2016).

## Pitfalls
- **Basket artefact**: a handful of tiny-float bonds inflate RMSE and the curve kinks around them. Check free float before interpreting dispersion.
- **Sign mix-ups**: price gap (+rich) vs fitted-yield residual (+cheap) vs forward-curve spread (−rich). Print the sign. Report ASW definition (MMS vs proceeds can differ ~50bp for deep discounts and zeros).
- **Scarcity is not RV**: small-float or never-reopened lines (a $5bn linker) look rich; "we would not regard this richness as an RV opportunity" (BofA, 22 Jul 2025).
- **Crowded short**: the most obviously rich bond is the most squeezable; model own-issue repo, not GC (Burghardt et al., The Treasury Bond Basis, 2005, Ch.6). Specialness is call-like (asymmetric).
- **Persistent residuals** are normal: require evidence convergence has begun (momentum of the error) and pool trades to cancel factor exposure (Tuckman & Serrat 2022, Ch.9).
- **Benchmark rolls** create fake slope/fly jumps; use fitted constant-maturity yields for histories (Düring 2021, Ch.31). Generic "old 10y" series splice at auctions: pin bonds.
- **Dislocation continuation**: a small dislocation can be a harbinger; understand it before fading (Düring 2021, Ch.30).
- **Long-end convexity**: ultra-long "rich vs model" is mostly convexity (Düring 2021, Ch.19-20); low long forwards reflect convexity bias (Salomon, Part 1, May 1995).
- **Linkers**: July vs April maturities distort a non-seasonal real curve (US 15 July rich, 15 April cheap; France July advantaged, Germany disadvantaged); deflation (par) floor option on TIPS and euro linkers, none on UK linkers; exclude < 1y (lag).
- **Fair-value scoring**: judging a model by the next print rewards overfit models (last trade apparent error 0.020 vs actual 0.056) (Cotton, NYU seminar, 27 Apr 2016).
- **Data**: clean, accrued and coupon cash separate; dirty price for the fit; point-in-time universe (`issue_date <= d`); funged taps can carry temporary ISINs; closes on the 1/32 grid are dealer quotes, not matrix prices; check null gating columns do not silently empty the universe.
- **Costs**: half-spread profile is U-shaped by maturity; charge all legs by |weight|; a belly-only cost flatters results.
- **Model-specific**: output depends on the fitter's locality; smooth interpolation smears hedges and partial DV01 ladders (MIT 18.642, Lecture 7, 26 Sep 2024).

## Output
Return (and save for the trade write-up):
1. **Fit summary**: date, snap, model, n_bonds, basket filters applied (with counts removed per filter), parameters (`λ1, λ2`, knots), `fit_rmse_bp`, RMSE by bucket vs its 1y range.
2. **Issue table** (sorted cheapest first): `instrument_id`, `ttm_years`, coupon, `ytm_pct`, `model_ytm_pct`, `spread_bp` (+ = cheap), `price_gap` (+ = rich), `mod_dur`,
   `z_3m`, `median_3m`, `pctile_3m`, LOO `spread_bp`, flags (OTR/rank, CTD, special bp, low float, coupon bucket, linker month).
3. **Explained vs unexplained**: regression coefficients (deliverability, size, age, coupon) and the post-regression residual.
4. **Candidate trades**: leg weights (DV01-neutral), net `spread_bp`, carry+roll with bond repo, round-trip cost, z, half-life, entry/target/stop, what would make it wrong.
5. A chart: residual vs maturity (or duration), colour by z. Hand off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and
   [rv-devils-advocate](../rv-devils-advocate/SKILL.md). State all signs and the as-of snap.

## Scripts
- [`scripts/fit_curve.py`](scripts/fit_curve.py): NSS fit to `bond_static` + `bond_quotes` (CSV/Parquet) in yield space, 4 multi-starts, optional soft-L1 (`--robust`) and
  leave-one-out (`--loo`); outputs `spread_bp` (+cheap), `price_gap` (+rich), 63-day z, median, percentile, fit RMSE. `python scripts/fit_curve.py --help`.
  `--selftest` checks a published price/yield pair, an exactly flat curve, and a planted +3bp bond (with and without LOO). Simplifications: ACT/365.25 times, schedule rolled back from maturity
  (no stubs/ex-div), no regressors, no repo anchor; use it for ranking and screening, not for sub-0.1bp work.

## Related skills
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): ASW definitions and swap-spread drivers; swap-hedged residuals.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): CTD, gross/net basis, deliverability; futures-driven issue richness.
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): basket exit and CTD switch effects on issue residuals.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): auction concession, buybacks, QT supply effects on residuals.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): specialness, GC vs special repo, fails.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA on fitted constant-maturity series; PCA residuals as an alternative rich/cheap.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): NS dynamics, affine fair value.
- [fi-curve-construction](../fi-curve-construction/SKILL.md): bootstrapping and interpolation.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry/roll and buffer from the fitted curve.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts, ex-div, settlement, benchmark definitions.
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): linker seasonality and z-spread.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): cross-issuer residuals and switches.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score windows and ranking.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life and entry/exit for residuals.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): costs and capacity of switches and flies.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables.
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weighting, residuals and sizing.
- [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md): sovereign CDS and CDS-bond basis.

## References
- J.P. Morgan - The new and improved Treasury par curve model (Barry, Fang, White, Chang, 16 Jul 2018): spline discount function, basket filters, yield-weighted objective.
- J.P. Morgan - The (par) curves they are a-changin' (Barry, White, Borges, Wash, 23 Jul 2024): free-float filter, knot selection and overfitting test, RMSE by bucket, TIPS curve.
- J.P. Morgan - Times like these: structural changes in off-the-run Treasury pricing and liquidity (Barry, Sun, White, 10 Feb 2016): RMSE dispersion and drivers, yield-error spreads, roll cycle.
- Huggins, Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): rich/cheap as regression residual, joint curve and regressor fit, WLS, Bund 2012 fit, coupon effects, global SOFR-ASW fit.
- Düring - Fixed Income Trading and Risk Management (Wiley, 2021): curve families, fitting objective, spline spread, buffer, OTR premium, liquidity indicator, composite splines, linker seasonality.
- Tuckman, Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): law-of-one-price rich/cheap, bond spread, coupon effect, specials cycle, P&L attribution.
- Fleckenstein, Longstaff - Treasury Richness (Journal of Finance, 2023): convenience premium, OTR and maturity-crossing effects, age effects.
- BofA Global Research - UST RV Primer: a hitchhiker's guide to RV on the UST curve (Zhang, Braizinha, Axel, 2 May 2022): NS/NSS, z-spread, ASW, OAS, micro switches.
- BofA Global Research - Global inflation-linked primer, 2nd ed. (Capleton, Swiber, 22 Jul 2025): seasonality-adjusted real yields, linker z-spread.
- BofA Global Research - UK Rates Viewpoint (5 Sep 2024), UK Rates Alpha (5 Aug 2024) and Liquid Insight (10 Nov 2022): low-coupon tax effect and coupon switch outcome.
- BofA Global Research - US Treasury auction primer (8 Mar 2024) and US Treasury futures and basis primer (10 Jul 2025): reopenings, buyback exclusions, CTD-driven richness.
- Salomon Brothers - Understanding the Yield Curve, Parts 1 and 6 (Ilmanen, May and Nov 1995): forward-rate cheapness, local rich/cheap in expected return.
- Federal Reserve Board - FEDS 2025-049: Trading costs v. indicative liquidity in the off-the-run Treasury market (Sokolinskiy, 7 Jul 2025): OTR-curve fair value, effective bid-ask.
- RiskVal - Overview 201: Cash and Futures (12 Nov 2021) and Generic Time Series Data & Roll Adjustment (28 Jul 2020): liquidity-weighted CMT fit, RV column set, roll adjustment.
- Citi Research - US Rates Weekly (Fixing the plumbing, 30 Sep 2019; Going nuclear on the curve, 3 Feb 2017; Deal or no deal, 10 May 2019; The rocky road to a steeper curve, 18 Jan 2019; Treasury Futures Roll Sep26-Dec26, 18 Aug 2026) and US Rate Strategy Notes (The long end basket case, 4 Feb 2015): CTD premium, basket exit, node-placement robustness, Treasury RV monitor.
- Citi Research - European Rates, The Morning Call (12 and 19 Aug 2026): auction RV dashboard (vs fitted curve, surrounds, peer).
- J.P. Morgan - Global Fixed Income Markets Weekly (21-22 Aug 2026): benchmark discount/roll, German fly regression, buyback score. Barclays - Interest Rate Derivatives, Swap spreads: the Bright Spot in US rates (30 Sep 2026): buybacks and long-end spline errors.
- Goldman Sachs - US Treasury Relative Value Report (25 Sep 2026): fitted-curve spread with 3m z, |z| > 2 flags, STRIPS, ASW definition gap.
- Treasury Borrowing Advisory Committee - Discussion of Treasury Futures Positions Across Different Investor Types (30 Jan 2024): CTDs at negative OAS to the fitted curve.
- Astor Ridge - Trade Radar (6 Mar 2022): BTP fitted-curve anomaly screen, cross-issuer switch.
- Citi Research - The High-Grade Beat (19 Aug 2026): dollar-price adjustment of credit spread curves (not for govvies).
- MIT OpenCourseWare 18.642 - Lecture 7, Linear Rates Models (Gunstensen, 26 Sep 2024): z-spread vs swap curve, smeared hedges.
- J.P. Morgan - Japan Fixed Income Markets Weekly (21 Feb 2025): 10y JGB fair-value regression and why the residual was not faded.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): new-issue cycle, RP-special P&L, squeeze risk of rich issues.
- Darbyshire - Coding Interest Rates (c.2024): B-spline log-DF fitting, Schoenberg-Whitney, z-spread algorithm.
- Cotton - Filtering bond and credit default swap markets (NYU Tandon seminar slides, 27 Apr 2016): Kalman fair value, overfitting illusion.
- Conks (Substack) - Demystifying the Repo Market Part III (28 May 2024) and The Repo Market Dislocation Part II (31 Aug 2024): leveraged OTR/OFR trade, specialness dynamics.
- Quantitative Finance Stack Exchange - fair value of off-the-run Treasuries (Jan 2022); Coupon Adjusted Spread vs Z-Spread (Apr 2021); Bond RV YTM vs maturity or duration (Aug 2023); Reproducing levels when PCA has been done on changes (Jun 2015): leave-one-out fair value, coupon adjustment, duration axis, level-regression residuals.
- Gurkaynak, Sack, Wright - The U.S. Treasury yield curve: 1961 to the present (Journal of Monetary Economics, 2007) (external): NSS Treasury yield-curve reference.
