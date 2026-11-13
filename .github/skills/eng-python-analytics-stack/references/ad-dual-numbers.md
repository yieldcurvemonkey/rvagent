# Forward-mode automatic differentiation (dual numbers)

When to read: you need exact first (or second) derivatives of a pricing or calibration function with respect to many curve
parameters, and bump-and-revalue is too slow or too noisy. The bundled `Dual` class in `scripts/analytics_kit.py` is the
first-order version (about 70 lines); this file gives the rules for extending it.

## Arithmetic
Dual: `z = x + b' eps`, `eps_i eps_j = 0`; `x` is the value, `b` the gradient (Darbyshire, Coding Interest Rates, c.2024, ch.2; Pricing and Trading IRD 3e, 2022, s.11).
- add: `(x1+x2) + (b1+b2) eps`; mul: `x1 x2 + (x2 b1 + x1 b2) eps`; div: `x1/x2 + (b1/x2 - x1 b2/x2^2) eps`.
- exp: `e^x (1 + b eps)`; ln: `ln x + (b/x) eps`; power: `x^n + n x^(n-1) b eps`.
- Lift any smooth `f` with known `f'`: `f(z) = f(x) + f'(x) b' eps`. Normal CDF: `Phi' = pdf`. Needed for swaption and Black formulas.
- Dual2 adds `eps' gamma eps` (Hessian = 2 gamma): product `gamma = x1 gamma2 + (b1 b2' + b2 b1')/2 + x2 gamma1`; exp `gamma' = e^x (gamma + b b'/2)`;
  ln `gamma' = (gamma - b b'/(2x))/x`; power `n x^(n-1) gamma + n(n-1) x^(n-2) b b'/2`.
- Upcasting: duals over different variable sets must be extended to the union of tags before combining (missing tag = 0). The bundled class does this by dict union.
  Cost: upcasting is ~37x a float op; pre-declaring the variable list ~17x; Dual2 ~60x (Darbyshire, Coding Interest Rates, ch.2: 1.22 us float, 45.4 us / 21.3 us / 72.8 us).

## Known-answer checks (write these before the pricer)
- `f = x^6 + exp(x/y) + ln z` at (2, 1, 2): value 72.08220328; gradient (199.389056, -14.778112, 0.5); Dual2 Hessian dxdx 487.389056, dxdy -22.167168, dydy 59.112449, dzdz -0.25. Asserted in the bundled selftest (gradient).
- Upcasting: `Dual(11,[x,y],[3,8]) + Dual(-3,[y,z],[-2,5]) + 2.65` = 10.65 with gradient [3, 6, 5] over [x, y, z].
- Product/sub/reverse-divide: `x*y*z + 2x` at (2,3,5) gives 34 with gradient (17, 10, 6); `2/(x-1)` at 3 gives 1 and -0.5. These caught a mutant (wrong product coefficient) that the book's function alone could not, because it contains no product of two variables.

## Linear algebra with duals
- NumPy `matmul/dot/inner/tensordot` work on object arrays of duals; `np.linalg.solve` does not. Write a Doolittle LU with partial pivoting ("dual_solve") when the solve itself must carry derivatives (curve gradients, cubic-spline coefficients).
- `math.exp/log` must be replaced by dispatching wrappers (`dexp`, `dlog`); this is "one of the largest challenges" of the approach.

## Why AD and when not
- Bump-and-revalue costs (#variables x function time), has truncation error, and forward differences need n+1 evaluations and central 2n+1 (4 vs 7 for the 3-variable test function). AD raises only the operation cost. A bank deployment reported a 100x to 1000x speed-up for delta risk (Darbyshire, Coding Interest Rates, ch.1-2).
- Tangent-linear (forward) AD gives one risk per pass; adjoint gives all risks at ~4x pricing time (Burgess, Low Latency Interest Rate Markets, undated deck). At desk scale (a few dozen nodes) native forward-mode is simplest. Plan an adjoint library (JAX, TensorFlow, Audi) only if you need thousands of parameters; their setup overhead dominates small problems.
- Do not use AD through: an iterative solver's internals (differentiate the converged fixed point with the implicit function theorem, `K` in the curve reference), or non-smooth payoffs (barriers, digitals) - bump those.
- Static curve edits (node shifts, translate, roll) break AD links, so risk computed through them is silently zero. Use a composite (dynamic) shift when risk must stay live through solver iterations; it costs speed (a two-curve composite DF lookup took 280 us vs 3.9 us for a plain curve).

## Second-order checks
- Taylor check (local-currency first): 1mm NOK at USDNOK 8 is 125,000 USD; delta -15,625 USD per +1.0 USDNOK; gamma 3,906.25. Move to 9.0: first order -15,625, second order -13,672, exact -13,889 (Darbyshire, Coding Interest Rates, ch.7). Verify with `1e6/x**2` and `2e6/x**3`.
- Convert P&L in local currency, then convert to the reporting currency; the naive FX-converted Taylor gave a >5% error on a 10Y EUR IRS vs EURSEK 10.00 -> 10.50 (Darbyshire, Coding Interest Rates, s.12.3.2). That chapter also has a printed anomaly (eq. 12.23 vs table value 0.00086): treat as "verify".
