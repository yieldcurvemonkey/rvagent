# Interpolation, solver, risk and curve operations (fi-curve-construction)

Detail behind Method steps 5, 7 and 8 of [SKILL.md](../SKILL.md). Sources are cited inline.

## 1. Interpolation catalogue (t = (m - m_i)/(m_{i+1} - m_i))
| Scheme | Formula | Properties |
|---|---|---|
| Linear in DF | `v = v_i + t(v_{i+1} - v_i)` | valid but unsuitable for DF curves; "extremely poor" (Ametrano & Bianchetti, 2013) |
| Log-linear DF | `v = exp(ln v_i + t(ln v_{i+1} - ln v_i))` | constant overnight forward between nodes, `r = (1/d)((v_i/v_{i+1})^{d/(D_{i+1}-D_i)} - 1)`; local and stable; step forwards |
| Flat forward / backward | `v = v_i` on `[m_i, m_{i+1})` / the reverse | for value (rate-projection) curves; unsuitable for DF curves |
| Linear in index (1/DF) | `1/v = 1/v_i + t(1/v_{i+1} - 1/v_i)` | default for index curves |
| Linear in zero rate | `r_cc = -ln v/D` interpolated linearly | undefined at first node, flat-backward first segment; invalid for value curves; not structure-preserving under translate; "not recommended for any purpose" (Darbyshire, Coding Interest Rates, c.2024) |
| Log-cubic DF spline | cubic B-spline in `ln v`, natural ends | smooth overnight forwards, C2 in log DF; **global** (one input moves all forwards, damped with distance) |
| Hyman monotone cubic on log DF | cubic spline with monotonicity filter | non-negative FRAs, no waviness; needs iteration to convergence (seed with previous grid), non-local delta |
| Raw (piecewise-constant instantaneous forwards) | linear in `r·t` | stable, forwards positive: use as the bug-catching benchmark (West, Interest Rate Derivatives lecture notes, 2010) |

Failure mode: linear on zeros/log-DF "produce[s] horrible FRA curves, with a sawtooth or piecewise-constant shape"; oscillations reach tens of bp in sparse sections while the zero curve looks fine (Ametrano & Bianchetti 2013). Log-DF is right for DF-based curves; linear/cubic on value (rate) curves.

**Mixed interpolation.** Log-linear on the dense instrument section (to the last IMM/meeting-dated instrument, ~2-3y), spline beyond; set the first spline knot at the last log-linear node (Darbyshire, PTIRD, 2022). EUR O/N: flat forwards to the last ECB-dated OIS (~2y) then Hyman monotone cubic on log DF; mixed equals log-linear on short-end errors, monotone cubic everywhere has higher errors on all excluded instruments (Ametrano, Bertocchi, Mazzocchi, 2016).
Step-then-spline hybrid: dates known ~2y out, so go step at the front and spline at the back (MIT 18.642, Sep 2024).

## 2. Locality and its consequences
- Log-linear (local): bumping one par rate moves only forwards between neighbouring knots; the overnight impact is constant between knots and discontinuous at them; only the bumped par rate moves.
- Log-cubic (global): all forwards change with distance-damped oscillation; intermediate par rates move; overnight impact continuous. Test: flat 2% curve, +0.1bp at 5Y: log-linear 3M forwards step up between 4Y and 5Y and down between 5Y and 6Y; log-cubic oscillates everywhere (PTIRD 2022).
- Key-rate risk of a near-par swap sits at its own node; off-par swaps leak through `(S - C)` and depend on the interpolator. Smoother interpolators give more dispersed forward perturbations.
- Hedges: bump size trades odd shapes (too big) against noise (too small); partial deltas need not sum to the parallel delta; smooth interpolation gives a smeared hedge; full partial gamma costs N², use parallel or PCA gamma (MIT 18.642).
- Interpolation mismatch cost (PTIRD 2022): €300mm 4.25y payer, analytic delta €122,115. Risk strip log-linear 4Y 86,663 / 5Y 35,453; log-cubic -231, 1,848, -10,478, 101,598, 38,234, -11,642, 3,635, -1,047, 197; unreliability €1 with the matching risk model vs €1,328 and €784 with the others.

## 3. B-splines (log-cubic machinery)
- `ln v(x) = Σ α_i B_{i,4,t}(x)`; recurrence `B_{i,1}(x) = 1 if t_i ≤ x < t_{i+1}`, `B_{i,k}(x) = (x - t_i)/(t_{i+k-1} - t_i)·B_{i,k-1} + (t_{i+k} - x)/(t_{i+k} - t_{i+1})·B_{i+1,k-1}`; skip zero denominators; make the right end left-continuous; `dB_{i,k}/dx = (k-1)[B_{i,k-1}/(t_{i+k-1} - t_i) - B_{i+1,k-1}/(t_{i+k} - t_{i+1})]`. Positive on `(t_i, t_{i+k})`, partition of unity (Darbyshire, CIR; PTIRD).
- Knot sequence of length `n+4` with only the end knots repeated: `n-3` intervals, C2 at interior breakpoints, needs `n-2` data sites with at least one per interval (Schoenberg-Whitney: collocation solvable iff `t_i < τ_i < t_{i+k}`). E.g. `t = [3Y×4, 4Y, 5Y, 6Y×4]` → 3 intervals, 4 nodes. Natural spline: second-derivative rows zero at both ends.
- Curry-Schoenberg: an interior breakpoint repeated `k - ν` times for `ν` continuity conditions; dimension `n = kl - Σν_i`.
- Knot placement matters more than node placement inside the spline section. Knots at rolling par maturities change the polynomial daily, so the curve moves even if rates evolve exactly as forecast (test: 10 yearly par IRSs rebuilt on 73 dates, 6M swaps drift -0.1 to +0.15bp and some spreads ~0.25bp); strategic IMM knots do not (PTIRD 2022).
- Natural cubic on a *value* curve (Darbyshire, CIR Ex 3.3): values 1.50, 1.85, 1.80 at 2022/23/24 with 5 degrees of freedom gives a humped spline that overshoots: global splines overshoot between nodes.

## 4. Solver
- Variables `v` (DFs, `v_0 = 1` fixed), rates `r(v)`, market `S`, weights `W`: `min g = (r - S)ᵀ W (r - S)`, gradient `2 J W (r - S)`, `J_ij = ∂r_j/∂v_i`.
- Gauss-Newton: `J W Jᵀ δ = -J W (r - S)`; square case `Jᵀ δ = -(r - S)`. Converges in single or low double-digit iterations from yesterday's curve. LM: `(J W Jᵀ + λ I) δ = -½ ∇g`, λ0 = 1000, ×¼ on success, ×2 on failure (no accepted rule). Gradient descent with optimal step `α* = yᵀW(r - S)/(yᵀWy)` is stable but "very slow".
- Forward-mode AD (dual numbers) gives `J` exactly; reverse mode adds nothing for one layer. Graph sparse except under global interpolators. Pure-Python long-dated (50Y) log-cubic is the speed bottleneck.
- Completely specified toy (Darbyshire, CIR): nodes 1-Jan-23 (1.0), 1-Nov-23, 1-Feb-25; 1Y/2Y IRS at 2.5/3.5; Gauss-Newton in 3 iterations, objective 5.34e-18, `v = [0.982647, 0.928661]`.
- Regularise the under-specified case with low-weight calibrating instruments: zero-priced butterflies between policy periods (weights 1e-8 to 1e-4), or second-derivative proxy `SwapSpread(SwapSpread(mpc_1, mpc_2), SwapSpread(mpc_2, mpc_3)) = 0` (PTIRD 2022). They guide the fit and are not expected to solve to 0; ignore their risk.
- Number of instruments vs nodes: nodes at instrument maturities → exactly specified; extra policy-period nodes → add flies; layered curvesets add skew instruments (4Y -0.15bp ...) on top of a first-layer curve so that stable skews replace volatile inputs ("ten volatile inputs" become "six volatile and four stable").

## 5. Risk off the solved curve
- `∇_S P = ∇_S vᵀ ∇_v P`; `K = ∇_S vᵀ` is a property of the solved curve: store it and report any trade's risk as `K ∇_v P / 100`. Routes: (i) second-order AD with `∇_S v* = -(∇_S∇_vᵀ g)(∇_v∇_vᵀ g)⁻¹`; (ii) scale each calibrating trade so its analytic delta is 1bp and invert `∇_v Pᵀ` (pseudo-inverse if `n ≠ m`); (iii) finite differences with 0.1bp bumps re-solved by Gauss-Newton (least efficient).
- DF risk is not tradeable. Map to cc zero rates (`v_i = e^{-D_i Z_i}`, `∂f/∂Z_i = -D_i v_i ∂f/∂v_i`) or to par instruments. Par↔forward Jacobians are mutual inverses (0.493 × 2.030 ≈ 1 in the PTIRD example with par 1Y/2Y/5Y/10Y at 1.21/1.635/1.885/1.93).
- Rule: the risk model must share the pricing curve's interpolation and inputs; choose inputs around liquid hedge instruments. Details: [fi-risk-dv01-and-transforms](../../fi-risk-dv01-and-transforms/SKILL.md).
- Pillar re-map (QuantFinance Stack Exchange, 2021): `f0(q0, r_t) = 0 ⇒ dr = -(∂f0/∂q / ∂f0/∂r) dq0`; for a single curve with swaps 1/2/3% (DFs 0.99009901 / 0.96097845 / 0.91404629) `dr3 = 1.01442 dc` for the 3Y swap and `dr3 = 0.31705 df` for the 2→3 forward.

## 6. Curve operations (Darbyshire, Coding Interest Rates, c.2024)
- **Shift** (parallel): `r_i → r_i + k/100`; dynamic = composite with a flat k-bp curve (keeps automatic differentiation); static DF: `v_{i+1,new} = v_{i,new}/((v_i/v_{i+1})^{1/n} + d̄ k/100)^n`.
- **Translate** (move the initial node forward; build the next-day opening curve): rates preserved, DFs rebased `v_i* = v_i / v(m0*)`. Structure-preserving for linear, log-linear, linear-index, flat-forward, flat-backward; NOT linear-zero (1d rate 3.87090 → 3.87090 log-linear but 3.89710 → 3.90526 linear-zero). Splines need `m0*` inside the first interval.
- **Roll** (roll-down): `C_new[x] = C[x - j]`, `C_new[x] = C[0]` for `x < j`; DF values scaled by `1/(1 + d̄ r0)^j`; knots shifted. Static roll-down = rate on the rolled curve minus today's rate; no recalibration.
- **Composite DF curves** (turns, spreads): `(1 + d̄ r̄)^{ñ}` geometric approximation of `Π(1 + d_i(r_{1,i} + r_{2,i}))`, error ≤ 1/100 bp and >1000× faster; **multi-CSA** (max overnight rate across collateral curves) approximated by sigmoid-stepped comparisons, approx DF ≥ true DF.
- **Fast layer**: `R_new = R_old + J ΔR̂`; example: 4Y..10Y IRS 0.750 0.765 0.779 0.782 0.783 0.782 0.781 with 5Y/10Y-proxy futures moves +0.0005/+0.0015 → 0.7505 0.7655 0.7797 0.7829 0.7841 0.7833 0.7825 (PTIRD, Ex 19.7).

## 7. Turns: implementation recipes
- Version A (local interpolator): nodes 31-Dec and 1-Jan; `IRS 1d(1 Dec) = 0`, `Spread(1d 30 Dec, 1d 31 Dec) = -50bp`, `Spread(1d 31 Dec, 1d 1 Jan) = +50bp`. **Version B (preferred)**: `IRS 1d(1 Dec) = 0`, `Spread(30 Dec, 31 Dec) = -50bp`, `IRS 1d(1 Jan) = 0`, because "the turn is assigned to precisely one calibration parameter". Add exactly as many nodes as calibrating instruments (-50bp illustrative).
- Spline: composite `turn_curve + spline_curve` in one solver. Cubic splines cannot take the turn directly (continuity forces oscillation).
- Fading tenor turn: nodes 30-Sep 0, 1-Oct -0.20, 31-Dec -0.04, 1-Jan 0 composited with a linear base curve.
- Transient jump (Deriscope, Turn-of-the-Month Effect in SOFR Curve, Feb 2024): raise the overnight forward only on the jump date; calendar sets the span (31-Dec-2020 covers to 4-Jan-2021); visible in overnight forwards, tiny in 3M forwards (1 of ~65 days).
- Which EUR quotes carry the year-end turn (Ametrano & Bianchetti, 2013): O/N on the last working day; TN/SN 1-2 days before; the 1M deposit from 2 business days before the 1st business day of December; 12M deposits always; the Dec IMM future and Oct/Nov serials; 2Y swaps carry two turns. Estimate by interpolating non-crossing forwards and differencing against the quoted crossing one; sources: 3M futures (first turn only), 6M FRA strip, 1M IRS strip, broker FRA strip.
- Funding drivers for daily forwards (Lehman 2007; Credit Suisse, Basis Points, Feb 2010): corporate tax days up, financial year-end up, month-end up (quarter-end larger), Fridays up (3-day roll), Mondays down, reserve-maintenance periods (in a hiking cycle FF effective creeps up pre-meeting, falls after; reverse in cutting), maturing central-bank repo (ECB MRO maturing Tuesday after a Governing Council averaged ~30bp below refi), catastrophes (Y2K turn +45bp). Large excess reserves damp these.
