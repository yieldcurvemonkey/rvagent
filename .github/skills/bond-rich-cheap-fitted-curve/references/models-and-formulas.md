# Fitted-curve models and formulas (reference)

Linked from [SKILL.md](../SKILL.md). Rates in decimals inside formulas, bp in outputs. `t` in years. `d(t)` = discount
factor, `z(t)` = continuously compounded zero rate, `f` = instantaneous forward.

## 1. Curve identities

- `f(t) = -d/dt ln d(t)`; `d(t) = exp(-∫0..t f)`; `d(t) = exp(-t·z(t))`; `z(t) = -ln d(t)/t`.
- Par rate for coupon frequency `n` and maturity `T`: `par(T) = n·(1 - d(T)) / Σ_i d(t_i)`, `t_i = i/n`. Semiannual form
  `y_par(T) = 2(1 - d(T)) / Σ_{i=1..2T} d(i/2)`. A par curve depends on conventions (frequency, calendar, day count);
  the discount curve does not (Düring, Fixed Income Trading and Risk Management, 2021, Ch.19; BofA, UST RV Primer, 2 May 2022).
- Annual zero/forward: `d(t) = 1/(1+z)^t`; `f(t1,t2) = [(1+z2)^t2 / (1+z1)^t1]^(1/(t2-t1)) - 1`.
- Generic notional par benchmark from a fitted curve: `C = 100·(1 - Z_T)/A_T` (Z_T zero price at T, A_T annuity on the
  notional coupon dates) (Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024, Ch.8).
- Yield is a nonlinear transform of price and time, not an average of zero rates; it equals realised return only under
  reinvestment at the yield (Huggins & Schaller 2024, Ch.5). Hence rank bonds on spreads to a discount curve, not on yield.
- Annual bootstrap (par `p_i`): `d_1 = 1/(1+p_1)`, `d_i = (1 - p_i·Σ_{j<i} d_j)/(1 + p_i)`. For bonds maturing about every
  6 months, bootstrap sequentially and where several bonds share a maturity use the most recently issued (Tuckman & Serrat,
  Fixed Income Securities, 4th ed., 2022, Ch.1). A bootstrap reprices every input exactly, so its residuals are zero by
  construction and it passes every idiosyncratic quirk into the forwards. Use it only for swaps, never for issue RV.
- Bootstrapped USD swap curve example, 5 Jun 2020 (annual): par / d / zero / 1y fwd: 1y 0.307%/0.996939/0.307%/0.307%;
  5y 0.517%/0.974469/0.519%/0.895%; 10y 0.915%/0.911883/0.927%/1.498% (Düring 2021, Ch.19). Use as a unit-test vector.

## 2. Parametric and spline families

**Nelson-Siegel (NS), zero-rate form** (Düring 2021, eq. 19.18):
`z(t) = b1 + b2·(1-e^{-t/λ})/(t/λ) + b3·[(1-e^{-t/λ})/(t/λ) - e^{-t/λ}]`
Level `b1`, slope `b2`, hump `b3`, time-scale `λ`. Forward form: `f(n) = b0 + b1·e^{-n/τ} + b2·(n/τ)·e^{-n/τ}`
(BofA 2022). Forward starts at `b0+b1`, converges to `b0`.

**Svensson (NSS)** adds `b4·[(1-e^{-t/λ2})/(t/λ2) - e^{-t/λ2}]` (eq. 19.19). Six parameters, two humps. Defaults used by
the bundled script: `λ ∈ [0.05, 30]`, four multi-starts `(λ1,λ2) = (2,5), (1.5,4), (3,8), (1,10)`, keep the lowest cost.
Identification warning: `b3` and `b4` are poorly identified when `λ1 ≈ λ2` (Düring 2021, Ch.19). Check `|λ1-λ2|`
and the size of `b3, b4`; if `b3 ≈ -b4` with huge magnitudes, refit NS.

**Exponential spline**: `d(t) = Σ_{j=1..n} β_j e^{-j·α·t}` with `Σ β_j = 1` (eq. 19.24-19.25). Prices are linear in `β`
for fixed `α`, so least squares is linear and fast. It has a defined limit as `t → ∞`, so it is the only sensible choice when
extrapolating (e.g. pricing a first 50y bond with a curve that stops at 30y). Seven exponentials is a good start: too few
makes the curve sticky, too many chases outliers (Huggins & Schaller 2024, Ch.8).

**Cubic spline on the discount function** (JPM par curve): `d(t) = x0 + Σ_{i=1..3} x_i (t-0.5)^i/10^i + Σ_{k} x_k (t-t_k)^3_+ / 10^3`
for `t ≥ 0.5`; for `t < 0.5` linear interpolation of GC repo rates (O/N, 1m, 3m, 6m); `d(0.5)` pinned to the 6m GC repo
discount factor. Knots: 12, placed at on-the-run benchmark maturities and the midpoints between them (where off-the-runs
switch from trading off one benchmark to the next), reaching 10/15/20/25y. RMSE falls with more knots but with diminishing
benefit beyond 10-15; 20 knots overfits (J.P. Morgan, The (par) curves they are a-changin', 23 Jul 2024).
Mechanics (Darbyshire, Coding Interest Rates, c.2024, Ch.3): fit `ln d` (log-DF interpolates better than DF); use a B-spline
basis; Schoenberg-Whitney requires data in every knot interval (`t_i < τ_i < t_{i+k}`), otherwise the collocation matrix is
singular; natural ends = zero second derivative; knot placement "directly impacts the spline shape". Natural cubic splines
overshoot: through 1.50/1.85/1.80 (three dates) the interpolant humps after the middle point.

**Composite (spread) spline for thin issuer curves**: `d(t) = d_B(t)·d_S(t)`, `d_S(t) = exp(-t·Σ_{i=0..k} c_i t^i)`; fit the base
govt curve first, then the polynomial zero-spread (k = 2, three parameters per issuer, worked for Tokyo Metropolis and Chubu
Electric 1-10y over a JGB NSS on 24 Jan 2019). Avoids overfitting and an agency spline dipping below the sovereign (Düring 2021, Ch.19).

**Vasicek / affine "spline"**: daily-fitted sigma against UST implied vol gave R² < 0.1 (2014-19): structural models cannot be
made self-consistent with vol, so use them for term-premium work, not for issue RV (Düring 2021, Ch.19; see
[curve-term-structure-models](../../curve-term-structure-models/SKILL.md)).

**Kernel-ridge / on-the-run curve** (Federal Reserve FEDS 2025-049): fit a kernel-ridge curve (Filipovic-Pelger-Ye) to firm
on-the-run quotes (smoothness λ=1, maturity weight α=0.05, tension δ=0.001); price off-the-runs as PV on that curve plus an
idiosyncratic spread taken from indicative quotes at four intraday snapshots. It beat Fama-Bliss, NS and Tanggaard/Andersen
tension splines on yield forecasting. Keep a bond-day only if `|P_fair - mid| / (ask - bid) < 1/2` at every snapshot.

## 3. Fitting objective

Fit on **dirty price with actual cash flows**, in **yield space**:

```
P_hat_i = Σ_j CF_ij · d(t_ij)                      (settlement-date cash flows; drop the next coupon if ex-div)
e_i     = P_hat_i - P_i                            (price error, dirty)
ε_i^Y   = e_i / (P_i · D_i)                         (≈ yield error; D = modified duration)   [JPM 2018/2024]
min Σ ε_i^Y²        or, speed trick: Σ e_i² / DV01_i²    [Düring 2021, eq. 19.33; no yield root-search per bond]
```

Equal price weights let long-duration bonds dominate (more price vol); short bonds then carry large yield errors. In the
legacy J.P. Morgan model, front-end yield errors reached about -8bp at ~1.5y duration before the switch to yield weights
(J.P. Morgan, The new and improved Treasury par curve model, 16 Jul 2018).

Weighting menu (Huggins & Schaller 2024, Ch.8): (a) BPV, since with equal yield-error variance the price-error variance is about
proportional to BPV; (b) deliverability (deliverables are more volatile); (c) episodic repo specialness. Liquidity weights used
in a CMT fit: US `DV01 × free float` (free float = outstanding − central-bank holdings); EUR `issue size × DV01` (no holdings data)
(RiskVal, Overview 201: Cash and Futures, 12 Nov 2021). Try exponent 1 (`|e|` not `e²`) or soft-L1/Huber, because quadratic loss
gives outliers too much influence.

Heteroskedasticity and MLE: with independent, normal, zero-mean errors of equal variance MLE = OLS; otherwise WLS with weights
`1/U_i`, `U_i ∝ Var(ε_i)`. Weights are an empirical judgment.

**Joint fit with external regressors** (Huggins & Schaller 2024, Ch.8):
`P_i = Σ_l C_il·d(τ_il) + Σ_k γ_k · x_ik + ε_i`; minimise over curve parameters and `γ` together. Regressors: deliverability
(= BPV if deliverable else 0, so `γ` reads "bp rich when deliverable"), time since issuance, issue size, repo specialness,
coupon. Signs are empirical (easier-to-short benchmarks can be cheaper). Fitting the curve first and regressing residuals later
is biased because the curve absorbs part of the effect.

**Leave-one-out fair value**: `P_i^fair = Σ CF_ij · d^{(-i)}(t_ij)` with `d^{(-i)}` fitted without bond i (QF Stack Exchange,
fair value of off-the-run Treasuries, Jan 2022). n+1 fits per date; the first and last bonds are extrapolations and unreliable.

**Outliers**: iterative trimming (refit after dropping bonds beyond X bp) keeps the curve clean but changes the sample daily;
prefer a robust loss and flag outliers for manual check ("it is a bad idea to preserve tainted data and rely on post-processing
to remove it") (Düring 2021, Ch.19).

## 4. Spread definitions (all per bond, state the sign)

| Measure | Formula | Sign | Use |
|---|---|---|---|
| Price distance | `P - Σ CF_i d(t_i)` | + = rich | ignores duration; Tuckman table |
| Fitted-yield residual / spline spread | `y(P) - y(Σ CF_i d(t_i))` | + = cheap | default RV measure (Düring eq. 22.2) |
| Bond (forward-curve) spread | `s` solving `P = Σ CF / Π(1 + (f_i + s)/2)` | − = rich | equals OAS when no options (Tuckman & Serrat 2022, Ch.3) |
| Z-spread to a swap/RFR curve | `P = Σ C_i Z(t_i) e^{-s t_i} + Z(t_n) e^{-s t_n}` | + = cheap | aggregating with swap delta ladders |
| ASW (par/par, proceeds, matched-maturity) | see [spread-swap-spreads-and-asw](../../spread-swap-spreads-and-asw/SKILL.md) | store convention | hedge-based view |
| Premium (credit-adjusted richness) | `YTM(R) - YTM(P)`, R = risk-free replicating bond paying c − s | + = rich | academic; see evidence file |

Conversion: `spread_bp ≈ -1e4 · price_gap / (P_dirty · D_mod)`. Check on the Tuckman 7.625s Nov-22 (price gap +0.1172 per 100,
dirty ≈ 111.4, bond spread -7.27bp) implies D ≈ 1.45y, consistent with a 1.5y 7.6% coupon bond (own arithmetic).

Z-spread without an optimiser (Darbyshire c.2024, s10.11.2): three price evaluations (`z1` from a Newton step, `z2` from the
quadratic correction, `z3` a final Newton step on `dP/dz` at `z1+z2`). The printed quadratic root (eq. 10.30) appears to give
`1/z2`, so verify against a Brent solve before relying on it. Some libraries report convexity as `d²P/dy²` undivided by P.

## 5. Coupon effect (why yield spreads lie)

Spot 1y = 0%, 2y = 10% (annual), three fairly priced 2y bonds: 0% coupon price 82.6446, yield 10.0000%; 5% coupon price 91.7769,
yield 9.7203%; 9.5023% coupon price 100, yield 9.5023% (Tuckman & Serrat 2022, Ch.3). On an upward-sloping curve higher
coupons have lower yields; downward-sloping the reverse. Consequences:
- Interpolated swap spread (bond yield − interpolated par swap): on an upward curve the high-coupon bond always looks richer
  (Huggins & Schaller 2024, Ch.17). Example: 10% bond yields 4.98%, 5% bond 5.00%, swap 5.35%: spreads −37bp vs −35bp.
- Par ASW also carries a coupon effect even on a flat curve unless swap curve = govt curve: raising a 5% coupon to 5.10%
  adds 70c to bond price but only 65c to swap-curve PV, and the 5c gap raises the par ASW.
- Coupon-adjusted spread via STRIPS: `(note price − principal-strip price)/coupon` = price per 1% coupon; reprice a 1% note as a
  2% note and compare yields. Without a strip market, plot against duration, not maturity (QF Stack Exchange, Coupon Adjusted
  Spread vs Z-Spread, Apr 2021; QF Stack Exchange, Bond RV YTM vs maturity or duration, Aug 2023).
- Dollar-price adjustment in spread curves (credit): 1bp per price point for 10y A-and-better, 1.25bp for 30y, 1.625bp for 10y
  BBB, 2bp for 30y BBB (Citi, The High-Grade Beat, 19 Aug 2026). Not for govvies.
- Different coupon frequencies are not comparable until converted (BTP 0% semiannual, OBL 0% annual) (Düring 2021, Ch.16).

## 6. Fitted curve to expected return

- Forward yield = yield of the forward price using the **bond-specific repo**. Expected yield = spot yield + (curve fair-value yield
  at the forward date − curve fair-value yield at the spot date). **Buffer = forward yield − expected yield**: how far the whole
  curve must shift up by the horizon to wipe out carry and roll. Germany Aug 2014 (NSS, depo -0.10%): buffer plateau about 6-7bp
  over 6-9y, about 2-3bp at 25-30y (chart read) (Düring 2021, Ch.21).
- Total expected return = yield income + rolldown + convexity value + duration impact of the view + local rich/cheap, where local
  rich/cheap = financing advantage `(3m GC term − 3m special term)/4` + `(OTR yield − model par yield)/4` + expected cheapening
  (Salomon Brothers, Understanding the Yield Curve Part 6, Nov 1995). Convexity value ≈ `0.5·C·(σ·√h)²·(1 + y/100)` with `C` = (1/P)·d²P/dy² and σ the yield vol in decimals per year (bp/1e4), y in % (Salomon scaling).
- Under realised forwards any bond earns the short rate plus its (constant) spread; excess return comes only from rate or spread
  moves, which is why the spread is the rich/cheap state variable (Tuckman & Serrat 2022, Ch.3).

## 7. Linker (real) curves

Fit a real-yield curve (piecewise cubic, yield-space errors). Adjust prices for (i) the deflation-floor option (swaption-style
value subtracted from real price; TIPS, and euro linkers redeem at no less than par; UK linkers have no principal floor) and (ii) CPI seasonality: seasonal index centred at
1 (or 100), lagged and interpolated like Reference Values, `SAP = P · S_v/S_m` (value-date over maturity-date index), yield from
SAP; exclude sub-1y issues (J.P. Morgan 2024; BofA, Global Inflation-linked Primer, 22 Jul 2025). Composite inflation discount factor
`Rf(t) = d(t)·(s_t/s_0)·e^{ιt}` (Düring 2021, Ch.23). On a non-seasonal spline July-maturity TIPS look rich (pay on the seasonally
high April CPI), April maturities cheap; naive spreads span about -30 to +13bp at short maturities versus a few bp after adjustment.
Linker z-spread: project nominal flows from inflation-swap-implied reference values, discount on the RFR curve, solve for the
parallel spread to the dirty price (BofA 2025). Details in [infl-breakevens-and-linkers](../../infl-breakevens-and-linkers/SKILL.md).

## 8. Dynamic fair value (state-space)

A Kalman filter with one curve state fitted to all issues is a dynamic fitted curve; each issue's residual to it is its rich/cheap
(Cotton, Filtering bond and CDS markets, NYU Tandon seminar, 27 Apr 2016). Simulation: scoring against the next print rewards
overfit models (last trade: apparent error 0.020, actual 0.056; univariate KF 0.0377 / 0.0512; multivariate KF 0.0383 / 0.0286).
Evaluate fair-value models against the true/consensus value or a size-and-time-weighted target, not the next print.
