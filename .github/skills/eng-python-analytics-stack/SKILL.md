---
name: eng-python-analytics-stack
description: "Coding conventions and tested numerical building blocks for G10 rates analytics in Python: unit and sign contract, numpy/pandas/scipy core with guarded statsmodels/sklearn and optional rateslib/QuantLib, curve solves (Gauss-Newton, weights, Jacobians), forward-mode automatic differentiation versus bump-and-revalue, schedules and day counts, bp-change covariance, CoVaR, min-VaR hedge, PCA, ridge by QR, Bachelier swaption price and implied vol, multiprocessing, run manifests, look-ahead truncation test, mutation-tested selftests. Use when writing or reviewing Python analytics code, a bundled script, pricer, risk or VaR calculation, PCA, covariance or hedge ratio code, DV01/Jacobian transform, interpolation, date logic, unit test, parallel sweep or Monte Carlo, or when results are not reproducible, a sign or bp-versus-percent mix-up is suspected, or a number disagrees with a reference."
---

# Python analytics stack for rates RV

Every other skill that computes something (a fly weight, a PCA residual, a VaR, a roll-down, a swaption vol) leans on the
same few numerical patterns, and the same few bugs: sign flips, percent-vs-bp mixing, explicit matrix inverses, a solver that
never terminates on an over-specified curve, look-ahead through a centred window, a date rule that is wrong on one holiday.
This skill fixes the conventions, names the default tool for each job, and bundles one tested module
(`scripts/analytics_kit.py`) so skills do not each reinvent them. Heavier derivations and fixtures are in `references/`.

## When to use
- Writing, extending or reviewing any script under `scripts/` of any skill, or ad-hoc analytics code in a session.
- "Why does my curve / VaR / hedge ratio / vol not match the reference?" or "the numbers change from run to run".
- Choosing between bump-and-revalue and automatic differentiation; between explicit inverse, `solve`, `lstsq`, QR or SVD.
- Setting up a parameter sweep, Monte Carlo or large panel computation (parallel, memory, storage).
- Adding a test for a convention-heavy function (schedules, day counts, interpolation, sign of DV01).
- Deciding whether to depend on an optional pricing library.

## Inputs (data-agnostic)
Tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) (`references/schemas.md`).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap / OIS rates | `curve_par` | daily snap, >= 100 daily changes for covariance | percent in the table; convert to bp for risk |
| Built curve nodes | `curve_zero` | per date, snap, curve_id | store nodes + `interpolation` + `build_id`, never pickled pricer objects |
| Fixings | `rate_fixings` | daily | calendar must match the curve's calendar |
| Calendars / conventions | `calendars`, `swap_conventions` | static | day count, spot lag, roll, payment lag per curve_id |
| Positions / sensitivities | `positions` | per run | currency per bp, positive = long duration (receive fixed) |
| Option quotes | `opt_quotes`, `vol_surface` | per snap | carry distribution (normal/log), shift, day count |

If an input is missing, ask for it or hand off to the data adapter. Never invent values, never forward-fill a signal.

## Method

### 1. Unit and sign contract (apply at every function boundary)
- Rates and spreads: percent in tables, **bp in risk maths** (`x100`). Convert once, at the edge, and put the unit in the argument name (`par_rate_pct`, `vol_bp`).
- Curve spread A-B = longer minus shorter; fly 2s5s10s = 2 x 5y - 2y - 10y. DV01 = currency per bp, **positive for long duration (receive fixed / long bond)**.
- Caution: the Darbyshire texts print "positive pv01 = paid fixed", and some book code flips signs (`diff(-1)`). When a fixture comes from a book, state its sign convention next to it and flip explicitly.
- Covariance is of daily **changes** in bp, never levels, >= 100 observations, horizon matched to the VaR horizon. Normal (bp) vol for rates options; a vol travels with (distribution, shift, day count).
- Missing = NaN, never 0. Drop and log stale rows; never forward-fill. Keep `snap` in the key and never difference across snaps.

### 2. Which tool for which job
| Job | Default | Why / limit |
|---|---|---|
| Arrays, curves, covariance, PCA | `numpy`, `pandas`, `scipy` | always available; the bundled module needs nothing else |
| Regression diagnostics, ADF, HAC, GARCH | `statsmodels` (guarded import) | rolling/robust betas: see [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md) |
| PCA on large panels, CV, ridge/lasso | `scikit-learn` (guarded import) | fit on data through t-1 only (expanding window, as in BofA, Satko, Mar 2018); fix `random_state` |
| Curve builds, swap/bond/FX pricing with risk | own light code first; `rateslib` or `QuantLib` optional | a cross-check, never a hard dependency |
| Charts | `matplotlib` (guarded) | see [eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md) |

Guard optional imports so a script still runs without them:
```python
try:
    import statsmodels.api as sm
except ImportError:  # optional; fall back or raise a clear message
    sm = None
```
- `rateslib` is source-available with a **non-commercial default licence**: do not make it a requirement of any bundled script. Use it (or `QuantLib`) as an independent reference when validating your own curve or swap numbers, and as a source of call patterns. Its function and argument names change between releases: verify against the installed version before copying.
- Never serialise pricer objects as data. Store the inputs (`curve_par`) and the outputs (`curve_zero` nodes with `build_id`) and rebuild.

### 3. Linear algebra rules
1. Never `np.linalg.inv(A) @ b`. Use `np.linalg.solve(A, b)` for square well-conditioned systems; `np.linalg.lstsq` or QR for least squares; SVD / `pinv` when rank-deficient (hedge Jacobians, K matrices, collinear regressors).
2. Do not form normal equations `X'X` when `lstsq` works: it squares the condition number. Ridge = least squares on the augmented system `[X; sqrt(lam) I] w = [y; 0]`, solved by QR (`ridge_qr`). Standardise columns first.
3. Symmetric matrices: `np.linalg.eigh` (not `eig`), sort descending, apply a deterministic sign rule to eigenvectors (largest-|loading| entry positive); strip NaN/INF first.
4. Hedge in a subset of instruments `h` by `np.linalg.solve(Q[h,h], -(Q @ S)[h])`, not by inverting.
5. Check conditioning (`np.linalg.cond`) before trusting a Jacobian: a trader-model Jacobian must be square, full rank and cover every bucket.

### 4. Curve solve (summary; detail in [references/curve-solver-and-sensitivities.md](references/curve-solver-and-sensitivities.md))
- Minimise `(r(v) - S)' W (r(v) - S)` over log-DF nodes. Default **Gauss-Newton from yesterday's solved curve**; Levenberg-Marquardt (lam0 = 1000) only for a poor start. Solve each step with `lstsq(sqrt(W) J, -sqrt(W) res)`.
- Terminate on `max|res| < 1e-13` **or** weighted gradient `|J'W res| < 1e-14`; the second is the only valid test for an over-specified build. Raise after 50 iterations, never return silently.
- Validity gate: every input reprices to |NPV| < 1e-10 (healthy builds show 1e-13 to 1e-17). Else the curve is rejected.
- Under-specified (more nodes than quotes): add low-weight calibrators (zero-priced flies at 1e-8, curvature guides at 1e-4 versus 1.0 for quotes). Do not change the solver.
- Interpolate DFs log-linearly (flat overnight forward) or log-cubic; never linear in zero rates. Knots static on IMM dates. Details in the reference and in [fi-curve-construction](../fi-curve-construction/SKILL.md).
- Sensitivities: compute `K = dv/dS` once per solved curve (`K = J^-1` if exactly specified; weighted least squares `(J'WJ)^-1 J'W` if over-specified, never a plain `pinv(J)` under unequal weights), store it, and check `K` against a 0.01bp bump-and-re-solve (the selftest does). Risk to raw DFs is not hedgeable: transform to par or zero risk ([fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md)).

### 5. Derivatives: AD vs bump-and-revalue
- Forward-mode dual numbers give exact gradients with cost `T_ops x ~17-37` once per run; bumping costs `(#variables x T_func)` and carries truncation error (forward differences cost n+1 evaluations, central 2n+1: 4 vs 7 at n = 3). Use AD for many-parameter curve Jacobians; bump for non-smooth payoffs and as a cross-check.
- Static edits (node shifts, translate, roll) break AD links and silently zero risk. Use dynamic (composite) shifts if risk must stay live.
- Rules, tests and cost model: [references/ad-dual-numbers.md](references/ad-dual-numbers.md). Always test AD on a function with a product of two variables (`x*y*z`): a pure `x^6 + exp(x/y) + ln z` test misses a wrong product coefficient.

### 6. Dates, schedules, day counts
- Generate unadjusted schedule -> adjust with calendar and modifier. Pass IMM and end-of-month rolls explicitly (`roll`, `eom`); never infer them. Drop null stubs (<= 1 business day after adjustment).
- Day-count/compounding identity `(1 + r sum d_i) = prod(1 + d_i r_i)` holds for ACT/360 and ACT/365F only. ESTR is ACT/360, SONIA ACT/365F. Swap spot lag is T+0 for GBP, T+1 for AUD, T+2 for most others and disputed for CAD (read it per curve from `swap_conventions`); FX spot USDCAD is T+1. Carry the day count and lag with the data.
- Pin evaluation date, calendar, modifier and spot lag when comparing tenor-specified forwards: three 1Y1Y date methods agreed on only 73.2% of days in 2024 (Darbyshire, Coding Interest Rates, c.2024).
- Test every date rule against a published list (exchange expiries, central-bank meetings), not against itself. Full detail: [references/dates-schedules-swap-code.md](references/dates-schedules-swap-code.md); market conventions: [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md).

### 7. Risk aggregation and option maths (summary; fixtures in [references/risk-and-pricing-numerics.md](references/risk-and-pricing-numerics.md))
- `c = sqrt(S'QS)` (S in currency/bp, Q in bp^2), `VaR_a = z_(1-a) c` (1.645 at 5%, 2.326 at 1%), Euler allocation `S_i (QS)_i / c` sums to c; negative = diversifier.
- Min-VaR trade in subset h: `S_trade = -Q_hh^-1 (QS)_h`. Trade about 50% and re-run: several full-size single-instrument trades can raise VaR.
- PCA: eigendecompose Q (covariance keeps scale; correlation removes it); eigenvalue = variance of that PC; drop PCs then rescale; minor PCs are unstable.
- Bachelier payer `= (F-K) Phi(x) + s phi(x)`, `s = sigma_bp sqrt(T)/100`, `x = (F-K)/s`, F and K in percent, price in percent of annuity; receiver = payer - (F-K) (physical settlement). Implied vol by Newton from 20bp, vega `= sqrt(T)/100 phi(x)`.

### 8. Performance and parallelism
- Order of attack (Lopez de Prado, AFML, ch.20 and 22; Chan, Quantitative Trading, appendix): (1) fix the algorithm, (2) vectorise, (3) store as Parquet/HDF5, (4) only then processes. A curve build is ~10 ms; parallelise parameter sweeps and simulation, not builds.
- `mp_map(func, jobs, num_threads)`: `num_threads = 1` is a plain loop for debugging; parallel path uses a process pool, `func` must be module-level (Windows spawn), results are unordered so jobs carry a key. Partition with `lin_parts` or `nested_parts` (triangular loops); make jobs a multiple of cores, heavy ones first. Seed children with `SeedSequence.spawn`.
- Detail: [references/performance-and-reproducibility.md](references/performance-and-reproducibility.md).

### 9. Reproducibility and checks
1. **Manifest** per run: versions, platform, seed, sha256 of every input, config (`run_manifest`, CLI `manifest`). Store it next to the output.
2. **Truncation test** for look-ahead (and run the same code in backtest and production, Paleologo, 2025): a causal signal at t is identical on the full panel and on the panel cut at t (`lookahead_check`). It flags `rolling(center=True)`, `shift(-1)`, full-sample z-scores and full-sample PCA.
3. **Known-answer test first**: every numerical function gets a case whose answer is analytic, hand-derived or taken from a cited source, with the source's sign convention noted.
4. **Mutation test** each check: break the formula in a temp copy; the check must fail. Delete the copy.
5. **Reference cross-check** against an independent route (loop vs vectorised, bump vs AD, optional library vs own code) before trusting a new pricer.
6. Printed numbers in books and notes can disagree with their own code; re-run before using one as a test target. Record anomalies in the test comment (e.g. CoVaR below).
7. Log every parameter variant tried; N = number of trials feeds deflated-Sharpe style corrections ([bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md)).

## Worked examples
- **CoVaR, rounded vs unrounded matrix.** Q (bp^2) = [[8.7, 7.4, 5.1, 2.2], [7.4, 7.3, 4.7, 2.2], [5.1, 4.7, 4.9, 1.8], [2.2, 2.2, 1.8, 1.9]], S on 2/5/10/30Y = (-10,000, 2,500, 10,000, -4,000) per bp. The book prints c = 16,174 (VaR 5% 26,590, 1% 37,620) from the unrounded covariance (Darbyshire, Pricing and Trading IRD 3e, 2022, ch.14); the printed rounded matrix gives c = 16,402, VaR 1% = 38,157. The selftest asserts 16,401.98 and "within 2% of the book", and does not claim 16,174. Allocation: sums to c, 2Y dominates. Min-VaR with the 2Y only: trade +3,023 and c down 16.1% on the rounded matrix (book, unrounded: +2,948 and 15.6%).
- **Taylor in local currency.** 1mm NOK at USDNOK 8 is 125,000 USD; delta `-1e6/x^2 = -15,625` per +1.0; gamma `2e6/x^3 = 3,906.25`. Move to 9.0: first order -15,625; with gamma -13,672; exact `1e6/9 - 125,000 = -13,889` (Darbyshire, Coding Interest Rates, ch.7). The second-order term recovers ~87% of the first-order error on a 12.5% move, not all of it. Convert P&L in local currency first, then FX.
- **Compounding.** Overnight 1% then 2%, ACT/365F, two days: `((1 + .01/365)(1 + .02/365) - 1) x 365/2 = 1.50003%`. Daily 12/13/14% over 3 days = 13.0046% (ACT/365F; Darbyshire, Coding Interest Rates, ch.6, 9). Quick unit test for any compounding helper.
- **Swaption.** Payer F 1.325%, K 1.500%, T 5y, 52bp normal vol: 0.3816% of annuity (38.16bp); parity and implied-vol round trip asserted (Darbyshire, PT3e, Ex 20.1). With pv01 $230,500 that is about $8.8mm upfront.
- **Curve solve.** Annual par 1Y/2Y at 2.5/3.5 (DCF = 1): bootstrap `v1 = 1/1.025 = 0.97561`, `v2 = (1 - 0.035 v1)/1.035 = 0.93319`; Gauss-Newton reproduces both to 1e-12 in 4 iterations. With real schedules the book gets 0.982647 / 0.928661 (Darbyshire, Coding Interest Rates, Ex 12.5): a different schedule, not a different answer.
- **Swap identities.** `PV = (r - p) A`, `PV01 = A x 0.01%`, par `p = PV(float)/A`, receive-fixed positive (Burgess, Low Latency Interest Rate Markets, undated deck): 5Y, N = 1mm, fixed 5%, `A` = 4,863,971.74, par 1.5482% gives PV01 486.40 and PV 167,892 = (5% - 1.5482%) A. The slide's PV line prints 1.59% for par; only 1.5482% reproduces 167,892. DF = 1 (`A` = 5) gives PV about 175k, a sanity check only.
- **AD.** `f = x^6 + exp(x/y) + ln z` at (2, 1, 2): 72.08220328, gradient (199.389056, -14.778112, 0.5) (Darbyshire, Coding Interest Rates, ch.2).

## Signals & interpretation (diagnostics, not trade signals)
- Curve residual > 1e-10 on any input: reject the curve, do not "use it anyway".
- AD vs 0.01bp bump differ by more than ~1e-4 relative: a link is broken (static shift) or a branch is non-smooth.
- Gauss-Newton needs > ~15 iterations from yesterday's curve: bad quote or knot problem; check bid/ask on closely spaced pillars (zig-zag at the front end).
- Truncation test flags a date: the signal looks ahead; fix before reading any backtest.
- Covariance from < 100 changes, or built on levels: results are not VaR. Overlapping h-day changes carry only about N/h independent observations: 100 of them at h = 5 is ~20 effective points. Min-VaR trade that is large relative to the book on a poorly conditioned Q: check `cond(Q_hh)`.
- Serial and parallel results differ: unordered results mis-joined, shared RNG state, or a non-picklable closure.
- If the best single hedge removes only ~15% of c, the book is dominated by RV risk, not direction.

## Pitfalls
- Percent vs bp (x100) and per-percent vs per-bp vega/theta (the book's helpers are per percent: 100x). Annualised vs daily vol (`/sqrt(252)`).
- Positive-for-receive (this repo) vs positive-for-paid (book fixtures) sign.
- `x_t - x_{t-1}` vs a negative `diff`: covariance unchanged, signed P&L flipped.
- Residual-only termination on an over-specified curve loops forever.
- Linear-in-zero interpolation, rolling-maturity knots: spurious forwards and P&L.
- A tree or Monte Carlo that does not converge to the analytic value as steps grow (Hull's 3Y put on a 9Y zero: 1.8468 / 1.8128 / 1.8091 vs 1.8093 at 10 / 100 / 500 steps) is wrong, not noisy.
- Python threads for CPU-bound work (GIL); global RNG in workers; unpicklable lambdas on Windows.
- Copying Python 2 or removed pandas APIs from books.
- Unit-test anchors copied from prose instead of printed output or an independent computation.
- A last-traded price is not a mid. For a consistent set of mids, stack outrights, spreads and the fly as rows of `A p = s` and solve weighted least squares (weights 1, 0.2, 0.1) rather than trusting one book (Darbyshire, PT3e, ch.19).
- Equity-platform Sharpe thresholds (2.5-6, thousands of names) do not apply to a few dozen rate series.
- Making an optional library (licence, API drift) a hard dependency.

## Output
For any analytics deliverable return: (1) the numbers with units and sign convention in the column or argument names; (2) the inputs used (table, date, snap, curve_id) with the manifest (versions, seed, input hashes); (3) the checks that ran and passed (curve residual, AD-vs-bump, truncation test, parity/round trip, reconciliation against a reference), with any that were skipped and why; (4) known approximations (extrapolated nodes, unshifted log vol, constant-gamma, rounded covariance). Hand risk numbers to [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md) or [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md) and trade write-ups to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts
- [`scripts/analytics_kit.py`](scripts/analytics_kit.py): `Dual`/`dexp`/`dlog` forward-mode AD; `solve_curve_gn` (weighted Gauss-Newton on annual par swaps with AD Jacobian, weighted-LS `K`); `cov_bp`, `covar` (CoVaR + Euler allocation), `min_var_trade`, `pca_cov`; `ridge_qr`; `swaption_normal`, `implied_nvol_bp`; `df_loglinear`; `clean_levels`; `lookahead_check`; `lin_parts`, `nested_parts`, `mp_map`; `run_manifest`.
  - `python -I scripts/analytics_kit.py --selftest` runs 35+ known-answer checks and exits non-zero on failure.
  - `python scripts/analytics_kit.py var --curve-par curve_par.csv --curve-id USD-SOFR --sens "2Y:-10000,5Y:2500,10Y:10000"` computes CoVaR, allocation and PC1 from a canonical `curve_par` table (CSV or Parquet; one `snap` only; spot-start rows).
  - `python scripts/analytics_kit.py manifest data/curve_par.csv --seed 7` prints a run manifest.
  - Scope: annual fixed vs single-curve float, DCF = 1, log-linear DFs; it is a test bench and pattern library, not a production pricer. Mutation-tested: breaking the swaption parity sign, the CoVaR scale, the par-rate annuity, the DF interpolation, the AD product rule, the Gauss-Newton weights, the weighted `K`, the `cov_bp` bp scale, the look-ahead tolerance and the non-finite guards each makes `--selftest` fail.

## Related skills
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables and validation these functions read
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): stale data, holidays, snap times, outliers
- [fi-curve-construction](../fi-curve-construction/SKILL.md): curve instruments, turns, multi-curve semantics for the solver
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): Jacobian transforms, par/zero risk, gamma and cross-gamma
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts, spot lags, calendars per market
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA use (loadings, residuals, hedges) built on `pca_cov`
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): shrinkage/EWMA alternatives to the sample covariance
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): OLS/TLS/Kalman hedge ratios
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): normal-vol conventions and swaption RV
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): gamma-based convexity sizing
- [bt-backtest-design](../bt-backtest-design/SKILL.md): lagged signals, engine ownership of marks
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): trial counting, deflated Sharpe
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): compounded RFR, lookback and fixing conventions
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): roll-down definitions the repricing checks must reproduce
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): ADF, HAC and overlapping-observation inference
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): purged cross-validation for ridge/lasso
- [eng-skill-authoring](../eng-skill-authoring/SKILL.md): script rules every skill follows
- [eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md): charts of the outputs

## References
- J. H. M. Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): curve solve, AD, Jacobians, VaR/PCA fixtures, swaption code, schedule code
- J. H. M. Darbyshire - Coding Interest Rates (rateslib companion, c.2024): solver algorithms, dual numbers, interpolation and schedule mechanics, library design, known-answer numbers
- D. Huggins and C. Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): joint-fit objective, spline routine, deliverability regressors
- M. Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018), ch.20 and ch.22 (K. Wu, H. Simon): multiprocessing, molecules, HDF5 and HPC timings
- N. Burgess - "I Feel the Need, the Need for Speed" (SSRN, May 2022): consolidated schedule pricing
- N. Burgess - Low Latency Interest Rate Markets: Theory, Pricing & Practice (slide deck, undated): PV/PV01 identities, curve-Jacobian real-time risk, tangent vs adjoint AD
- J. C. Hull - Options, Futures, and Other Derivatives (9th ed., Pearson), ch.31: short-rate trees and closed forms, tree convergence test
- K. P. Murphy - Machine Learning: A Probabilistic Perspective (MIT Press, 2012), s.7.5: ridge by QR and SVD
- I. Tulchinsky et al. - Finding Alphas (Wiley, 2015): metric definitions, NaN and timestamp rules, coding pitfalls
- Quantitative Finance Stack Exchange - "Why are FRA/futures convexity adjustments necessary?" (2019, updated 27 Jul 2023): gamma-based convexity estimate
- Quantitative Finance Stack Exchange - "STIR Futures convexity adjustment" (Jun 2025): parametric convexity calibration pattern
- Quantitative Finance Stack Exchange - "How to adjust butterfly 2s5s10s swaps trade for directionality?" (2018, edited 2021): PCA, min-VaR and regression fly weights
- Quantitative Finance Stack Exchange - "Calculating swap rolldown using the RatesLib Python Library" (Jun 2024): roll-down on a static curve
- Quantitative Finance Stack Exchange - "Step-by-Step PCA algorithm (checking correctness without math packages)" (Jan 2014): PCA numerics
- Deriscope blog - "How to build a SOFR Yield Curve in Excel using QuantLib and Deriscope" (I. Rigopoulos, 18 Feb 2024): repricing-to-zero validity test
- BofA Merrill Lynch Global Research - European Rates Viewpoint: "Many EGBs, one simple value tool" (E. Satko, 21 Mar 2018): expanding-window, backward-looking PCA
- M. Brenndoerfer - Advanced Interest Rate Models: HJM and LMM (7 Dec 2025): printed output vs prose discrepancies
- G. A. Paleologo - The Elements of Quantitative Investing (Wiley, 2025): pre-registered protocol, identical code in backtest and production
- E. P. Chan - Quantitative Trading (Wiley, 2009), appendix: vectorised array-processing habits
