# Forward conventions, curve-build artefacts and risk transforms

Detail behind sections 1, 4 and 7 of [SKILL.md](../SKILL.md). Check every "kink" here before trading it.

## 1. Forward-start schedule ("the 1Y1Y problem")
A forward given as tenor x tenor is ambiguous. Three schedule methods (Darbyshire, Coding Interest Rates, c.2024):
- **Swaps aligned** (dealer-swap convention): 1Y1Y is the second half of the 2Y, so `2Y = 1Y + 1Y1Y`; 1Y and 2Y share the roll day
  measured from the evaluation (spot) date. Unadjusted effective = spot date + 1Y; termination = effective + 1Y; infer the roll, then
  adjust. Hedges exactly with the 1Y and 2Y benchmark swaps.
- **Swaption expiry**: expiry = today + 1Y; effective = expiry + spot lag; termination = effective + 1Y. Exact for swaption market
  makers; rarely seen in the interdealer swap market.
- **Swaptions aligned**: unadjusted effective = spot date + 1Y, adjusted for effective; termination = effective + 1Y.
Spot date is T+2 in most currencies and T+0 in GBP (see [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md)).
Over the 262 business days of 2024 all three methods agreed on 192 days (73.2%) and all differed on 9 (3.4%); swaps-aligned equalled
the swaption-expiry swap about 75% of the time, swaptions-aligned about 95%. Example (weekend-only calendar), today Wed 17 Jan 2024
(spot Fri 19 Jan): swaps aligned effective Mon 20 Jan 2025, roll 19; swaption expiry Fri 17 Jan 2025, effective Tue 21 Jan 2025, roll 21;
swaptions aligned roll 20. **Always record the evaluation date, schedule method, calendar and modifier** when comparing forward-swap
levels across sources or pairing a forward swap with a swaption.

## 2. Discount-factor and forward algebra
- `v_i = v_{i-1}/(1 + d_i r_i)`; `r = (v_0/v_n - 1)/sum d_i` valid only for ACT/360 or ACT/365F (fixed denominator), not 30E/360.
- Simple-yield forward `r(t1,t2) = (1/DCF12) * [(1 + r02*DCF02)/(1 + r01*DCF01) - 1]`; discount-rate forward differs subtly.
- Continuous: `f(t) = -d ln DF/dt`, `z(t) = -ln DF(t)/t`, spot approximately average of forwards `r(1) ~ [f(0.5)+f(1)]/2`; spot rises
  while forwards exceed spot even if forwards are falling; with an upward spot curve par sits below spot (Tuckman & Serrat,
  Fixed Income Securities, 4th ed., 2022, App. A2, Ch.2).
- Table 2.1 style check (SOFR, 14 May 2021): swap/spot/forward 0.5y 0.0340/0.0348/0.0348; 1y 0.0460/0.0466/0.0585; 1.5y
  0.0670/0.0681/0.1111; 2y 0.1120/0.1136/0.2500 (%); `0.2500 = 2*(DF(1.5)/DF(2) - 1)` (the 6m forward, annualised semiannually) and spot 2y about the average of the four forwards.
- Annual bootstrap table (USD swaps 5 Jun 2020, par / DF / zero / 1y forward, %): 1y 0.307/0.996939/0.307/0.307; 2y 0.299/0.994047/
  0.299/0.291; 3y 0.346/0.989687/0.346/0.441; 5y 0.517/0.974469/0.519/0.895; 7y 0.704/0.951749/0.709/1.262; 10y 0.915/0.911883/
  0.927/1.498 (Duering, Fixed Income Trading and Risk Management, 2021, Ch.19).
- Policy path to term rates: an X-year rate is approximately the (compounded) average of the forward overnight path; average 24
  one-month forward policy rates for the 2y, 60 for the 5y, 120 for the 10y. Near-term cut timing dominates 2-3y, terminal level
  dominates 4y+ (BofA, Rates basics: fixed versus float, 24 Apr 2024).
- 1980-2019: 5y fixed averaged about 150bp above the realised 5y average overnight rate (same source): a persistent premium, not a
  forecast error.

## 3. Interpolation and kinks that are not market information
- Bumping the 5Y par by 0.1bp on a flat 2% curve: log-linear DFs step the 3m forwards up between 4-5Y and down 5-6Y; log-cubic
  oscillates across all dates with ripples in neighbouring par rates (Darbyshire, Pricing and Trading Interest Rate Derivatives,
  3rd ed., 2022, Ex.9.8).
- Log-linear DFs give **step** O/N forwards jumping at nodes; log-cubic gives smooth forwards; linear zero rate is not recommended
  (not preserved under translate); flat-forward/backward are valid but unsuitable for DF curves (Darbyshire, Coding Interest Rates).
- Under-specified curves (more nodes than instruments) oscillate (O/N forwards +-40%); regularise with low-weight curvature
  instruments (butterflies at zero with weight 1e-4 to 1e-8): "setting butterfly prices to zero promotes a curve with minimum
  curvature". Ignore risk to these constraints.
- Step-forward front end: log-linear DF nodes on the dates new CB rates become effective (not announcement dates); mixed
  interpolation (log-linear front, log-cubic spline beyond), first spline knot at the last log-linear node.
- Turns (quarter/year-end) are genuine forward kinks: node each side, calibrate as a single spread instrument, composite a
  log-linear turn curve with the spline; matter much less for RFR than IBOR curves. SONIA quarter-end turns about -3bp quarterly,
  -5bp half/year-end (Darbyshire, 3rd ed., 2022, ch.12).
- Knots at rolling par maturities make forwards drift up to about 0.25bp between pairs even when the market moves exactly as
  forecast (spurious systematic P&L); use static IMM knots. Avoid IMM strip lengths of 6, 7, 10, 11 or 14 contracts (leveraged
  stub forwards); prefer 8 (small currencies) or 12.
- Interpolated broker quotes: electronic IRS portals may interpolate non-benchmark tenors (outside 2, 3, 5, 7, 10, 30Y) linearly;
  over 10Y-30Y that can show false arbitrage (Burgess, Electronic Rates Markets and Low Latency IRS Calculations, May 2022).
- Thin tenors (6y, 12y, 25y) add noisy peaks and troughs; build the forward curve from benchmark tenors.
- Futures-implied forwards: convexity-adjust (grows with sigma^2 t^2); strip year-end turns and Japan's 1-April turn before reading
  policy; a flat front end can hide cuts offset by term premium (Duering, 2021).
- Exact-fit bootstrap curves "may lead to non-intuitive forwards"; a parametric/spline fit to par yields is hedgeable with node
  instruments.
- **Roll tests for your own implementation**: `roll(tenor)` shifts the curve forward keeping the term structure (rate at m+30d on the
  rolled curve equals rate at m on the original); `translate(date)` moves the initial date without changing forwards (preserved for
  linear, log-linear and flat interpolations, **not** for linear-zero-rate); `shift(bp)` is a parallel shift. Use these as unit tests
  of any aged-forward routine.

## 4. Par versus forward risk (Jacobians)
- `R_{i+j} A_{i+j} = R_i A_i + R_j A_j` (aligned schedules). Forward move from par moves:
  `d(fwd) = [dR_{i+j} A_{i+j} - dR_i A_i] / A_fwd`. Example: 10Y -4.1bp to 1.46% and 20Y +1.4bp to 1.88%, annuities 0Y10Y 9.27,
  10Y10Y 7.38, 0Y20Y 16.65 give 10Y10Y +8.3bp (Darbyshire, 3rd ed., 2022, Ex.10.3). 5Y unchanged and 10Y +1bp gives 5Y5Y
  +2.11bp (annuities 4.8415, 4.3790, 9.2205).
- Par -> forward Jacobian entries `A_fwd/A_par` where the forward lies inside the par swap, else 0 (par A-delta 1Y 0.988, 2Y 1.956,
  5Y 4.747, 10Y 9.043; forward 0Y1Y 0.988, 1Y1Y 0.968, 2Y3Y 2.791, 5Y5Y 4.296; so the 5Y5Y row is 4.296/9.043 = 0.47 on the 10Y).
  Forward -> par is the inverse with alternating signs: 5Y5Y = 2.109 x 10Y - 1.106 x 5Y (Ex.10.5, 11.1). 5Y5Y receiver on 100mm
  risked in par: 1Y -5, 2Y -19, 5Y -47,447, 10Y +90,594.
- Leverage: if 2Y rises and 3Y is unchanged, 2Y1Y must move to compensate. The greater the par tenor and the shorter the forward
  tenor, the more leverage; 30Y5Y is about 10x par (rows 30Y/35Y/40Y vs 30Y5Y, 35Y5Y: -8.62, 9.62, -10.60, 11.60). Size RV in forward
  risk; use par risk for liquidation cost and hedging with traded instruments.
- Rules: transform complex -> simple only; never chain; avoid between very different models; non-square Jacobians use the
  Moore-Penrose pseudo-inverse (not lossless); for P&L explain use `dr*_B = (J+)^T dr_A`. Today's Jacobian on historical covariance is
  only approximate. Risk to curve parameters (DFs) is not hedgeable: express risk against calibrating instruments.
- Risk bleed: off-grid trades hedged on-grid drift as they age (an 11.5Y hedged 25% 10Y/75% 12Y re-risks after 1.5y to 8Y -12.5,
  9Y -12.5, 10Y +43.75, 12Y -18.75).

## 5. Fair-value fit and kink-ledger details (grid screen)
- Grid: 17 forward-swap points (dense 1y tenors over the front 10y, widening to 40y10y); abscissa = start + tenor/2 (segment midpoint).
- Fair value = per-day cross-sectional smooth fit (cubic polynomial in k, or least-squares cubic B-spline with fixed knots, e.g. 1, 3, 7,
  15, 29; clamp boundary knots to the data range; >= 8 strictly increasing points; rank check). Residual = `(I - H) @ levels` (hat
  matrix): exact linear projection; use leverages/degrees of freedom to scale-match placebo tests. Missing integer par tenors are
  interpolated linearly in par space with a minimum number of printed tenors required.
- Time-series alternative: walk-forward rolling PCA on forward levels (window 756, min 504, monthly refit, loadings frozen within the
  month, greedy eigenvector matching for sign/ordering continuity), residual in bp, trailing percentile bands with the current day
  excluded. Use together with the cross-section: require sign agreement and |resid| >= 0.5bp.
- Stats per point: z, percentile and OU fit over 756 days (min 252). OU first-passage-time by Monte Carlo (2000 simulations, 504 steps,
  exact transition `phi = exp(-k dt)`, step sd `sigma*sqrt((1 - exp(-2 k dt))/(2k))`, fixed seed) gives P(hit) and P(tau >
  breakeven horizon). Carry over a 1y horizon (3m in the meeting zone).
- Two books: **harvest** if BE/RV >= 1.17, z >= -0.5 (receive side not rich) and the holder's risk-adjusted carry net of reversion drag is
  positive; **dislocation** if |z| >= 2, expected net edge > 1.0bp, zone clean and residual signs agree (dislocation takes precedence).
  Anchors from the Citi screens: curve pairs exit near 0.8, enter shorts near 1.17-1.38.
- Fail-closed gates: realised vol >= 0.25bp/day (legs spanning no curve node give near-constant levels and exploding ratios);
  composed vs priced level within 3.0bp; never price outside the day's quoted vol envelope; eigenvector continuity |cos| gate;
  trailing 126d correlation of structure changes with PC1-score changes <= 0.45 (>= 63 obs) (Huggins & Schaller cloud diagnostic;
  reported hit-rate improvement 82% -> 90%).
- Measured dead ends: liquid-tenor cross-sectional fades (median 63d reversion +0.81..+1.14bp vs about 1bp round-trip cost); carry
  harvests that did not beat a null; flow-mark fades.

## 6. Curve distance for historical analogues
Curves on the same dates and metadata form a vector space: `||C||_1 = sum|r_i|`, `||C||_2 = sqrt(sum r_i^2)`, `||C||_inf = max|r_i|`.
Use demeaned forward shapes to find past periods where the level differs but the term structure is similar; curves with different
dimension, dates, value kind or metadata (Act365F SONIA vs Act360 ESTR) are not comparable (Darbyshire, Coding Interest Rates).
