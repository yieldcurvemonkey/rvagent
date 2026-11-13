# Curve solver, interpolation and sensitivity transforms (implementation detail)

Finance semantics (which instruments, which conventions) live in [fi-curve-construction](../../fi-curve-construction/SKILL.md)
and [fi-risk-dv01-and-transforms](../../fi-risk-dv01-and-transforms/SKILL.md). This file is the numerics: how to code
the solve and the Jacobians so that results are reproducible and testable. Fixture sign note: Darbyshire's examples quote
"positive pv01 = paid fixed"; this repo uses DV01 > 0 for receive/long duration. Flip the sign when comparing.

## 1. Solve as weighted least squares
- Objective `min_v g = (r(v) - S)' W (r(v) - S)`; `v` = node discount factors (v0 = 1 excluded) or their logs, `S` market
  rates, `W = diag(w)`. n nodes, m instruments (Darbyshire, Pricing and Trading IRD 3e, 2022, ch.11-12).
- n = m with nodes at instrument maturities: exactly specified, `g_min = 0`. n < m: over-specified (LS compromise, residuals
  non-zero). n > m: under-specified, spurious shapes; regularise with extra low-weight calibrators, not by changing solver
  (Darbyshire, Coding Interest Rates, c.2024, s.11, s.13.4).
- Bootstrapping is valid only for single, sequential curves; co-dependent curves (multi-curve, discount vs forecast) need the
  simultaneous solve.
- Minimum validity test: every input reprices to ~0 NPV. Healthy residuals are 1e-13 to 1e-17 (Deriscope, SOFR curve build,
  18 Feb 2024). If max |residual| > 1e-10 the curve is not a valid input to anything else.

## 2. Algorithms (J = dr'/dv, `[J]_ij = dr_j/dv_i`)
| Algorithm | Step | Use |
|---|---|---|
| Gradient descent | `v -= 2a J W (r-S)` | teaching only; very slow near the optimum |
| Gauss-Newton (default) | `J W J' d = -J W (r-S)` | start from yesterday's solved curve; converges in single to low double-digit iterations |
| Levenberg-Marquardt | `(J W J' + lam I) d = -J W (r-S)`, lam0 = 1000 | only when the start is poor (first build, after a data repair) |

- Books disagree on the lam update (x1/4 on success, x2 on failure in one; `lam *= 2 if f_prev < f else 0.5` in the code of
  the other). Verify against whichever implementation you copy.
- Code: do not form `J W J'` explicitly. `np.linalg.lstsq(sqrt(W) J', -sqrt(W) (r - S))` solves the same step through SVD without
  squaring the condition number (the bundled `solve_curve_gn` does this).
- Converge on `max|r-S| < tol` (exact or under-specified) OR on the weighted gradient `J'W(r-S) ~ 0` (over-specified). A residual-only
  test never terminates on an over-specified build; the bundled script hit exactly this.
- Fixtures as printed (annual IRS, real date schedules, ACT/365F): Gauss-Newton, 2 nodes, 1Y/2Y IRS at 2.5/3.5 gives DFs
  0.982647/0.928661 in 3 iterations, f = 5.3e-18 (Darbyshire, Coding Interest Rates, Ex 12.5). Four nodes with 1Y/2Y/5Y/10Y at
  1.21/1.635/1.885/1.93 needs 9 LM iterations (Darbyshire, PT3e, Ex 11.1). The bundled script's 1Y/2Y check uses a
  simplified DCF = 1 schedule, so its DFs (0.97561/0.93319) differ from the book's and are checked against the analytic bootstrap instead.

## 3. Regularisation and under-specification
- Zero-priced flies between policy periods at weight 1e-8 (others 1.0) remove "uncontrolled highs and lows" in a policy-step curve
  (Darbyshire, Coding Interest Rates, s.13.4).
- Curvature guides at weight 1e-4: first-derivative proxy = spread of (1d swap after node k, 1d swap after node k+1); second-derivative
  proxy = spread of those spreads, target 0. Guiding, not solved to 0. Without them a log-linear under-specified curve swings overnight
  forwards about +/-40%; LM converged in 13 iterations (Darbyshire, PT3e, s.12.6).
- Node-grid rule of thumb: max tenor >= 3 x n_instruments + 6 months, else the last instrument is extrapolated and error bleeds backward.
- Wide bid/ask on closely spaced pillars gives front-end zig-zag (few free dates, big DF adjustments). Usually a stale quote; use futures at the front.
- Fitted bond curves: minimise `sum_b |sum_i CF_i df(t_i) + sum_k gamma_k k(b) - dirty_b|^p`; try p = 1 and p = 2 (squared loss over-weights outliers);
  weights = BPV, deliverability, specialness (Huggins & Schaller, Fixed Income RV Analysis 2e, 2024, ch.8). Bund fit with 13 cubic knots: mean abs residual 0.9bp, extremes +2.3/-2.2bp.

## 4. Interpolation (value stored per node; interpolate in the right space)
With `t = (m - m_i)/(m_{i+1} - m_i)`:
- log-linear DF: `v = exp(ln v_i + t (ln v_{i+1} - ln v_i))`: constant overnight forward between nodes. Default for DF curves and policy-step fits.
- linear value: default for rate (LineCurve-style) series. Flat forward / flat backward: step functions. Linear index: `1/v` linear (index curves).
- linear zero rate: not structure-preserving. After translating a curve by 14 days the 1d rate on 15 Feb moved 3.89710 -> 3.90526 for linear-zero while log-linear stayed 3.87090 (Darbyshire, Coding Interest Rates, ch.6). Do not use.
- log-cubic spline of DFs: only for sparse par tenors; B-spline basis with repeated end knots (length n+4 knot vector gives n-3 intervals), collocation matrix, one data site per knot interval (Schoenberg-Whitney) or the system is singular. Natural ends are a convention, not a fact.
- Mixed: log-linear to the end of the policy-dated section, spline beyond; the first spline knot is the last log-linear node.
- Knots static on strategic dates (IMM). Knots at rolling par maturities make forwards drift up to ~0.25bp between builds even when markets move exactly as forecast, i.e. spurious P&L. Change knot structure only between close and next open (Darbyshire, PT3e, Ex 12.5-12.6).
- Performance: compounding a 1y RFR period from a rate series costs ~252 lookups; from a DF curve only 2. Build index/compounded measures off DFs.
- Unit tests that need no market data: DFs `1.000, 0.983, 0.964` on 1 Jan 2022/23/24 give log-spline coefficients `[0, -0.0055, -0.0166, -0.0299, -0.0366]` (Darbyshire, Coding Interest Rates, ch.3). 2 DFs `1.0, 0.9975, 0.9945` at 0/90/181 days give DF(73d) = 0.99797174 (log-linear), asserted in the bundled selftest.

## 5. Sensitivity to calibrating instruments (the K matrix)
- `grad_S P = K grad_v P`, `K = grad_S v'`, `[K]_ij = dv_j/dS_i`. Portfolio risk is a linear sum, so compute K once per solved curve and store it.
- Three routes (Darbyshire, PT3e, s.12.6):
  1. second-order duals: `grad_S v' = -(grad_S grad_v' f)(grad_v grad_v' f)^-1` at the optimum;
  2. exactly specified: `K = J^-1`; over-specified with weights: `K = pinv(sqrt(W) J) sqrt(W)`, i.e. `(J'WJ)^-1 J'W` with the script's m x n Jacobian `J = dr/dv` (the n x m convention above reads `(J W J')^-1 J W`); plain `pinv(J)` is wrong unless W = I; the bundled selftest checks this against a bump-and-re-solve); in the linear-system form, scale each calibrator-equivalent trade so `grad_S P' = I`;
  3. re-solve with a +0.1bp forward bump from the solved nodes (a few Gauss-Newton iterations); central differences double the cost.
- The identity `dx*/ds = -(d2g/dx ds)/(d2g/dx2)` does not involve the algorithm or its step size: switching solver cannot change risk.
- Risk to raw DFs is not hedgeable (and numerically huge). Convert to zero or par risk. Cc zero: `v = exp(-D Z)`, `dv/dZ = -D v`.
- Par <-> forward Jacobian fixture (calibrators 1Y, 2Y, 5Y, 10Y at 1.21/1.635/1.885/1.93; forward curve on 1Y, 1Y1Y, 2Y3Y, 5Y5Y; Darbyshire, Coding Interest Rates, Ex 12.6):
  `d(fwd)/d(par)` rows = [1, 0.505, 0.208, 0.109], [0, 0.493, 0.203, 0.106], [0, 0, 0.586, 0.307], [0, 0, 0, 0.474]; the reverse Jacobian has 2.030, 1.707, 2.109 on the diagonal (0.493 x 2.030 = 1.00, 0.586 x 1.707 = 1.00, 0.474 x 2.109 = 1.00). Always assert that the two Jacobians multiply to I.
- Covariance transform between bases: `Q_B = A Q_A A'`; the scalar `c = sqrt(S'QS)` must be identical in either basis. Caveat: Q is historical but J depends on today's levels.
- Turns: a node on each side of the turn date and a +/- spread pair (e.g. 30 Mar 1d -> 31 Mar 1d = -0.03, 31 Mar 1d -> 1 Apr 1d = +0.03); weight 1; keep clear of curvature guides; no turns inside a spline (use a composite of a log-linear turn curve and a spline curve). Read turn risk as left minus right.
- Between full rebuilds (~10 ms in a background thread) update `L_new = L_old + (dL/dP) dP`; real-time DV01 = `1bp x (dPV/dL) x (dL/dP)` (Burgess, Low Latency Interest Rate Markets, undated deck).
