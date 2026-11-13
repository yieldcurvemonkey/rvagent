# Jacobian transforms, key-rate buckets and risk-model design (detail)

Convention used throughout (house): `S` = risk strip, DV01 per bucket in currency per bp, **positive = long duration
(receive fixed / long bond)**. Linear P&L = `-S . dr` (dr in bp). Several sources (Darbyshire, Stack Exchange answers)
quote delta positive for *paid* fixed; where an example below carries a sign it has been flipped to the house
convention and says so. Totals, ratios and Jacobian entries are sign-free.

## 1. The same risk in different coordinates (Coleman)

All numbers per 100 face per 100bp unless stated (Close Mountain Advisors, A Guide to Duration, DV01, and Yield Curve
Risk Transformations, 20 May 2011).

| Instrument | Price | DV01 | ModD | MacD |
|---|---|---|---|---|
| 2y 2.5% bond | 100 | 1.94 | 1.94 | 1.96 |
| 5y 3% bond | 100 | 4.61 | 4.61 | 4.68 |
| 10y 3.5% bond | 100 | 8.38 | 8.38 | 8.52 |
| 10y annuity | 29.72 | 1.46 | 4.91 | 4.98 |
| 10y zero | 70.28 | 6.90 | 9.82 | 10.00 |

10y zero, same exposure in three bases: zero-yield partials (0, 0, 0, 6.904), total 6.904; par-yield partials
(-0.026, -0.105, -0.54, 7.597), total 6.926; forward-rate partials (0.70, 0.70, 2.11, 3.51), total 7.03. Totals differ
because a "parallel shift" is a different shift in each basis (10y par swap: 8.50 for a parallel shift of
continuously-compounded forwards vs 8.38 for par yields). Only compare totals inside one basis.

Par partials of a zero are negative at short nodes and larger than the zero's own DV01 at its maturity node: a zero
is a 10y par swap minus a hedge in the shorter par swaps (the script's `par_partials` reproduces this pattern).

Coleman's **inverse-Jacobian recipe** (needs same count of variables, invertible Jacobian, instruments that match the
curve's knots):
1. Pick traded instruments that sit on the curve knots (the target risk basis).
2. Compute their risk to the curve variables, `DxDv` (rows = instruments).
3. For yield coordinates scale each row by 1/(its yield-DV01) and invert: `DvDy = [ (dx_i/dy_i)^-1 dx_i/dv_j ]^-1`.
4. Any portfolio's risk in the new basis = `DpDv . DvDy`. Only a handful of vanilla instruments are revalued, never
   the portfolio.

Worked rows (forward-rate variables f0y1y, f1y2y, f2y5y, f5y10y; Jacobian of par swaps to forwards): 1y (1.01, 0, 0, 0);
5y (0.214, 0.208, 0.587, 0); 10y (0.117, 0.113, 0.315, 0.456). Reproducing the brute-force bump results exactly is the
validation test.

What goes wrong: transforming onto instruments that are **not** on the curve's knots gives "peculiar but correct"
numbers (1/2/5/10 curve to 1/3/5/10 swaps: 2y swap risk (0, 4.39, -2.45, 0), whereas a rebuilt 1/3/5/10 curve gives
(0.48, 1.46, 0, 0)); build a new curve instead. Compression to fewer variables (1/2/5/10 to 1/5/10) has no square
inverse; rebuild the reduced curve and chain through k intermediate instruments, and know the dropped bucket is
redistributed according to both curves' functional form (2y swap goes to (0.72, 1.21, 0)).

## 2. Par <-> forward Jacobians from analytic deltas (Darbyshire)

Pricing identity `R_{i+j} A_{i+j} = R_i A_i + R_j A_j` (A = annuity / analytic delta per bp; 10y = 5y + 5y5y), so
`d(fwd) = [dR_{i+j} A_{i+j} - dR_i A_i] / A_fwd`, and the forward annuity is the difference of par annuities. Hence
`J_par->fwd[i, j] = A_fwd,i / A_par,j` when forward i lies inside par swap j, else 0 (the script's
`par_to_fwd_jacobian`); the inverse has entries `A_par/A_fwd` with alternating signs.

- Ex (par 1y/2y/5y/10y analytic deltas 0.988, 1.956, 4.747, 9.043; forward 0.988, 0.968, 2.791, 4.296): entries
  0.51 = 0.988/1.956 and 0.48 = 4.296/9.043 (source prints 0.47); inverse -1.02 = -0.988/0.968 and 2.10 = 9.043/4.296 (Darbyshire, Pricing
  and Trading Interest Rate Derivatives, 3rd ed., 2022, Ex 10.4-10.5).
- Leverage: "the greater the tenor of the par instrument and the shorter the tenor of the forward, the more leverage".
  A short forward at the long end carries about 10x the par risk (30y5y vs 30y/35y par).
- Lossless iff `J_B->A = J_A->B^-1`. Non-square J is lossy; use the Moore-Penrose pseudo-inverse. Ex 10.2: models A
  (2y,3y,4y,5y) and B (2y,2.75y,4.25y,5y); a 3.25y position S_A = (0, 75, 25, 0) maps to S_B = (0, 67, 33, 0) via
  J_A->B, but J_B->A gives (17, 50, 25, 8): poor.
- Rules: map complex -> simple, never simple -> complex ("lost information cannot be recreated"); do not chain
  transforms unless known lossless; avoid transforms between models with very different knots or interpolation.
- P&L explain in model B: use transformed moves `dr_B = pinv(J_A->B)^T dr_A` (this guarantees `S_B . dr_B = S_A . dr_A`),
  not real model-B moves. Ex 10.6: S_A = (5,7,8,4), dr_A = (2.0, 2.0, 2.2, 3.0), true 53.6; compress to 1y/4y,
  reverse-Jacobian moves give 63.8, pseudo-inverse moves 56.7 (closer). Validate: if two models explain P&L equally
  well and transformed moves match real moves, the transformed risks are accurate.
- Covariance: `Q_B = (J^+)^T Q_A J^+`; `c = sqrt(S_B' Q_B S_B)` is invariant. Today's Jacobian on historical
  covariance is an approximation (J depends on the rate level).
- Forward vol via the same transform: in house orientation `Q_fwd = (J^+)^T Q_par J^+`; the source writes `Q_fwd = J^T Q_par J` with its J
  the *inverse* (forward-to-par) of the house J. 1y5y5y from 1y5y and 1y10y: source J = [[1, 1-L],[0, L]], L =
  A_1y10y / A_1y5y5y; sigma_5y5y = sqrt(((1-L) s5)^2 + 2(1-L) L rho s5 s10 + (L s10)^2). With 1y5y 39bp, 1y10y 59bp,
  L 2.10, rho 0.95: 84bp (a naive 50/50 split gives 79bp); very sensitive to rho.

## 3. Trader risk models (spreads, flies, forwards, IMM strips)

Define each coordinate as a **unit strip in the par buckets** (house signs, DV01 per bp):

| Coordinate | Unit strip | Reading |
|---|---|---|
| `2Y` | (2y +1) | receive 2y |
| `2s5s` | (2y -1, 5y +1) | receive 5y, pay 2y (a flattener) |
| `5s10s` | (5y -1, 10y +1) | receive 10y, pay 5y |
| `2s5s10s` | (2y -1, 5y +2, 10y -1) | receive the belly |

Place the unit strips as columns of `U`; coordinates `c` solve `U c = S`, i.e. `J = U^-1`, `S_B = J S_A`.
Darbyshire Ex 16.3 (strip in the same unit convention): S = (2y -65, 5y +100, 10y -15) equals
(2y 20, 2s5s 85, 5s10s -15), and equals (2y -15, 2s5s10s 50, 10y 35), and equals (2s5s 65, 5s10s -35, 10y 20) (the
script's selftest checks the first two).

Validity: J square, every underlying bucket covered, columns independent (full rank). Counter-examples (Ex 16.5):
{2s5s, 5s10s, 2s10s} is rank-deficient (no outright); {5y, 5s10s, 10y} omits 2y. Use ONE personal trader model, not
several views. Misaligned instruments cause inversion precision problems; the pseudo-inverse is "not recommended unless
experienced".

Transformed coordinates are correlated (5s6s7s vs 5s10s about 5%): overlay VaR minimisation, or define a custom
"5s6s7s, 5s10s-hedged" instrument. Custom ladders lose no information when square: map 5y..10y to
{5y, 5s10s, 5s7s10s, 5s6s7s, 7s8s9s, 8s9s10s} and P&L explain stays exact and intuitive (Quantitative Finance Stack
Exchange, "Can PCA be used to transform a ladder of interest rate risk?", 20 Sep 2023). Layered ladders (layer 1:
1,2,5,30; layer 2 adds 7,20,50; layer 3 adds 15,25,40) show how deeper layers trade in terms of the coarse ones.

A fly's "01" is not unique: risks (2y -10, 5y +20, 10y -30) - a 5y +0.5bp move is a fly +1bp (P&L 10 in magnitude) and a
2y/10y -0.5bp move is also a fly +1bp (P&L 20 in magnitude). Quote the fly's bucket strip, not a single "fly 01".

## 4. Re-bucketing / compression `r = M s`

`s` = original buckets (n), `r` = target buckets (k), `M` is k x n and "can be designed any way you like":
1. **Linear-interpolation allocation** (default): each source bucket split linearly between adjoining target
   pillars; columns sum to 1 so total DV01 is preserved. Stable, transparent. Example 5,6,7,8,9,10y to 5y/7y/10y: rows
   [1, .5, 0, 0, 0, 0], [0, .5, 1, .667, .333, 0], [0, 0, 0, .333, .667, 1] (Quantitative Finance Stack Exchange, "PCA
   and risk bucketing", Nov 2019).
2. **PCA rows** (`M` = eigenvectors transposed): risk to level/slope/curvature. Sample-dependent, a single PC is hard
   to hedge, and it gives factor risk not tenor risk. PCA is a basis change, not dimension reduction, until PCs are
   discarded; run it on rate changes, not on the book's own PV01 (that only describes the pattern you hold).
3. **Non-linear curve re-bucketing**: `m_ij` = numerically computed move of source instrument i when only the 5y, 7y
   or 10y rate is bumped through the actual curve build. Most accurate; needs a reliable build.
4. **Regression Jacobian** for bond-by-bond DV01 to liquid points: `S_B = J S_A`, `J_ij` = beta of daily changes of
   bond j on liquid bond i (separate univariate regressions; collinearity among liquid points not addressed). Mapping ~55
   gilts to 5y/10y/30y is the cited use. Across instrument types (swaps to bonds/futures) the mapping is "entirely
   subjective": start with (multi-)linear regression, expect multicollinearity.

Validate a reduced bucket set **out of sample** (define in-sample, test the P&L error of the reduced vs full strip
over the next ~100 days). PCA is inadmissible when the reduced set must be a subset of the original buckets.

## 5. Key-rate (KR01 / KRD) mechanics

- Tuckman key-rate shift: each key-rate shift moves only par rates between adjacent keys, declining linearly to zero
  at the neighbours (first key flat to shorter terms, last key flat to longer), so KR01s sum to the 1bp parallel DV01.
  Popular key grid for governments: 6m, 1y, 2, 3, 5, 7, 10, 20, 30y. Too few keys and moves escape; too many and it is
  costly (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022).
- With par hedge bonds on the key tenors each hedge has only its own key exposure: `F_k = KR01_k(liability) / KR01_k(per
  100 hedge)`. With off-par, off-tenor hedges the KR01 matrix is upper-triangular: solve simultaneously, spreads held
  constant.
- Example (liability KR01 at 10/20/30/40y = $33,192 / $52,969 / $57,786 / $88,766, total $232,713): par-bond hedge
  faces $36.4mm / $34.7mm / $29.6mm / $39.6mm.
- BlackRock-style KRD: `krd_i = -(1/P)(P_up - P_down)/(2 dr)` holding OAS constant; grid 3m,1,2,3,5,7,10,15,20,25,30y;
  shock 20-50bp for nonlinear instruments. **Triangular** shocks create sharp forward oscillations (forwards can go
  negative) and distort option/MBS models; **wave** shocks (zero before i, ramp to full at j, flat after) give smoother
  forwards: `KRD_j = WKRD_ij - WKRD_jk`. For nonlinear instruments the sum of KRDs need not equal OAD; rescale each by
  OAD/sum (no published validation). KRD and PC durations differ only in the coordinate system (BlackRock's Guide to
  Fixed-Income Risk Management, 2023).
- Key *Treasury* rate durations (par/OTR curve) differ from KRD (spot-curve) when OTR liquidity premia are large (2y 11,
  5y 18, 10y 23, 30y 21bp at end-1998, up to 40bp). A 50bp par shock at 10y moves the 10y spot about 60bp and all spot
  rates beyond (some negatively) (Golub and Tilman, Risk Management: Approaches for Fixed Income Markets, 2000).
- Matching partials does not guarantee risk reduction; a low hedge/portfolio correlation is a red flag (same source).

## 6. Where the numbers come from: curve model vs risk model (Darbyshire)

- Par-instrument risk is computed by bumping calibrating inputs and re-solving, or by the chain rule through the curve
  Jacobian: `grad_S P = (grad_S v)^T grad_v P`, with `grad_S v^T = pinv(J)` where `J = dr/dv` of the final solver
  iteration (exact for an over- or exactly specified curve; independent of the solver's step size). Express risk against
  calibrating instruments, never against discount factors (not hedgeable; per-unit-DF numbers look nonsensical).
- Interpolation locality decides what "bucket" means: log-linear DF is local (only forwards between the knots around
  the bumped instrument react); log-cubic DF is global (all forwards can move, damped with distance). A non-local fitter
  gives a 6y swap spurious 10y sensitivity and the hedge then wrongly contains 10y swaps; prefer a local fitter or
  forward-bucket '01s.
- A trade identical to a calibrating instrument shows risk only in that bucket (non-overspecified curves). Seasoned or
  off-market swaps leak a small amount to other nodes through `(S - C)` times the annuity change.
- Ex 9.9 (pay EUR300mm 4.25y, analytic delta 122,115): log-linear bucket strip 86,663 (4y) + 35,453 (5y); log-cubic
  spreads it across 1y..9y (-231, 1,848, -10,478, 101,598, 38,234, -11,642, 3,635, -1,047, 197); all sum to 122,115.
  Hedging a log-cubic strip with 4y/5y gave a day's P&L estimate within 1 of the official figure; the other models
  were 1,328 and 784 against 1,178.
- Risk-model design rules: replicate the curve model's foundation, knot placement and interpolation; misaligned inputs
  or fewer inputs add unreliability; build around liquid products. "Regular unexplained P&L = badly designed risk
  model": a hedged book whose risk model explains zero P&L can still lose (Ex 9.5: hump becomes trough when 2y and 3y
  fall together against the rest).
- Layered curvesets: layer 1 liquid inputs, layer 2 stable skews at less observable tenors; a risk model on layer 1 alone
  is nearly as reliable unless the skews move.
- Risk grid (author's practical choice): t+2 3M, IMM forwards 1f..12f (8 contracts for small currencies, 12 for the
  most liquid; 6, 7, 10, 11, 14 are worst because a roll plus leverage creates e.g. a 2.75y0.25y bucket), then annual
  par 4y..10y, 12y, 15y, 20y, 25y, 30y, 40y, 50y. Use static (strategic) IMM knots; rolling knots create spurious
  systematic P&L (forwards drift about 0.25bp between pairs).
- **Risk bleed**: as time passes a 4y swap becomes a 3.5y swap and under log-linear DFs shows about 50% in each of the
  3y and 4y buckets; large positions between inputs hedged by inputs bleed. It does not show in VaR. Mitigate with wider
  input spacing, removing the offending positions, or timing hedges to when tenors align. Monitor the Open vs Close(t-1)
  "bleed" column.
- Delta vs basis (legacy multi-curve): total delta `dP/dr = dP/dz (forecast basis) + dP/ds (discount basis)`. With RFR
  forecast and discount curves the same, outright delta dominates and basis risk "has predominantly disappeared"; it
  returns when discounting differs from forecasting (foreign-currency CSA, cash-only CSA) - see
  [fi-collateral-csa-and-xva](../../fi-collateral-csa-and-xva/SKILL.md). Under multi-CSA (max-rate) curves every
  component curve must be bumped; do not segment risk sharply at the CTD-currency switch when two currencies are about
  equally cheap.
- Cross-currency: express all risk in one currency; risk to XCS basis is a 1bp move in the spread (paying the spread =
  positive in the source convention). Compute P&L in the local currency then convert at the FX move in post-processing;
  converting delta and gamma first misstates P&L by more than 5% (EURSEK example: true 88,393.61 SEK vs 83,707).

## 7. DV01 definitions that trip people

- **DV01 vs PV01 vs DF01**: DV01 = PV01 (annuity effect of a 1bp shift of forwards) + DF01 (effect on discount
  factors). A par swap has zero NPV so DF01 nets out and DV01 = PV01 = annuity x 1bp x notional. Off-market swaps need
  full revaluation (Burgess, Electronic Rates Markets and Low Latency Interest Rate Swap Calculations, SSRN, May 2022).
  PV01 of a USD 1.00% receiver, 1,000,000 notional: 1y 99, 2y 198, 5y 486, 10y 949, 15y 1,389, 20y 1,808, 30y 2,585 (same
  source, Mar 2019 curve). Rule of thumb DV01 ~ 100 x N(mm) x T (USD per bp); exact 5y 1.5482% par: 486.40.
- **Analytic delta** (own fixed rate, per bp) is exact for near-mid trades and for margin quotes, but ignores trade PV
  and curve shape; use numeric (bump) risk for hedging. Off-market effect: receive 100mm 10y at 4% when the mid is 2%:
  DV01 99,000 vs 90,000 at-market (house sign): extra = PV x tenor / (2 x 10,000) = 18mm x 10 / 20,000 = 9,000.
- **Macaulay vs modified vs Fisher-Weil**: modified = Macaulay / (1 + y/f); Macaulay is the PV-weighted average time
  only if every cash flow is discounted at the bond's own yield; Fisher-Weil discounts each at its zero rate and is
  recommended by Huggins and Schaller (2024) but rarely used. Do not mix: 10y annuity has ModD 4.91 but risk out to 10y.
- **Duration is not price risk away from par**: compare bonds by risk = duration x price; 7.5% coupon at 143.99 and
  duration 7.63 has risk 10.98 vs 8.80 for a 2.5% par bond with duration 8.80 (Convexity Maven, "Got Duration ?", 19
  Feb 2025).
- **Convexity scale**: some sources divide by price (Tuckman) and some do not (convexity = d2P/dy2, mapping to digital
  gamma). Rescale before comparing.
- **Short-rate duration** (Vasicek/Hull-White) of a zero is B(t,T) = (1 - e^{-a(T-t)})/a: with a = 0.1 a 4y zero has
  3.30 vs parallel duration 4.0, so a 10bp short-rate rise costs 0.33% not 0.40% (Hull, Options, Futures, and Other
  Derivatives, ch. 31).
- **5y-equivalents / 10y-equivalents**: `notional x DV01 / DV01_5y`; static OAD ratios are used for 10y-equivalent sizing.
  Notional overstates risk (CFTC data, Sep 2020, in Tuckman and Serrat, 4th ed., Table 13.1: USD 210.7tn notional vs USD 137.1tn 5y-equivalents); gross notional is the worst
  measure, a zero-MV book can carry large risk, and net notional (receive minus pay) still ignores tenor.
- **DV01 to P&L volatility**: daily sd 5bp gives quarterly sd about 5 x sqrt(63) = 40bp, so quarterly P&L sd =
  40 x DV01 (McPhail, Schnabl and Tuckman, CFTC OCE Staff Paper 2019-011, Apr 2023).

## 8. Packages and equivalence

- 5y5y receive 100mm = pay 100mm 5y + receive 100mm 10y (annuity effects aside) = receive 5s10s (100mm 5y vs 50mm 10y) +
  receive 50mm 10y. A risk or margin model must give identical risk and margin to each presentation (Darbyshire, 3rd
  ed., s19.3.1).
- Hedge cost LP on a bucket strip: `min c'x s.t. x reproduces the strip`, c = cost per unit of each candidate hedge
  including spreads and flies (spread margins must be strictly sub-additive). Ex 19.9: 100mm 5y5y strip (2y 23, 5y
  47,433, 10y -90,529) hedged by 10y -43,073, 2s10s -22, 5s10s -47,433, cost 33,405 = 0.78bp of the analytic delta.
  Market impact enters as a decoupled add-on `alpha sqrt(|x|)` (average cost 2/3 of the marginal), not inside the LP.
- Fast curve update between full builds: `R_new = R_old + J dR_hat` (Ex 19.7: 4y..10y IRS driven by two bond-future
  yields with static rows (1,0), (1,0), (.8,.2), (.6,.4), (.4,.6), (.2,.8), (0,1)). Real-time DV01 = 1bp x pricing
  Jacobian x curve Jacobian; adjoint differentiation gives all risks at about 4x one pricing.
