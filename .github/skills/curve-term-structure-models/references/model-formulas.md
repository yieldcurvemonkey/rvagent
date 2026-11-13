# Term-structure model formulas (reference for curve-term-structure-models)

Formulas the agent needs when it implements or checks a model. Notation: `τ` = maturity in years, `r` = short
rate (decimal), `σ` = normal (absolute) short-rate vol (decimal per √year; 0.01 = 100bp), `k` or `a` = mean
reversion per year, `P(t,T)` = zero-coupon price, `f` = instantaneous forward, `B(τ) = (1 − e^{−kτ})/k`.

## 1. Nelson-Siegel family

| Form | Formula | Source |
|---|---|---|
| NS zero, time-scale λ | `z(τ) = β0 + β1·(1−e^{−τ/λ})/(τ/λ) + β2·[(1−e^{−τ/λ})/(τ/λ) − e^{−τ/λ}]` | Düring (2021) eq. 19.18 |
| NSS zero | add `β3·[(1−e^{−τ/λ2})/(τ/λ2) − e^{−τ/λ2}]` | Düring eq. 19.19 |
| NS forward | `f(τ) = β0 + β1·e^{−τ/λ} + β2·(τ/λ)·e^{−τ/λ}` | BofA UST RV Primer (2022) |
| NSS forward | add `β3·(τ/λ2)·e^{−τ/λ2}` (second hump, captures the long-end convexity hump) | BofA UST RV Primer |
| Par yield from DFs (semi-annual) | `y_par(n) = 2·(1 − d(n)) / Σ_{i=1..2n} d(i/2)` | BofA UST RV Primer |

- `z(τ) = (1/τ)∫₀^τ f(s) ds`, so the zero and forward forms carry the same betas. Limits: `z(0+) = f(0) = β0 + β1`
  (instantaneous short rate), `z(∞) = β0`. At `τ = λ` the slope loading is `1 − 1/e = 0.6321` and the curvature
  loading is `1 − 2/e = 0.2642`. The curvature loading peaks at `τ ≈ 1.793·λ`.
- Rate-parametrised form (Diebold-Li style): loadings in `λ_r·τ` with `λ_r = 1/λ`. Diebold-Li fix `λ_r = 0.0609` per
  month, which puts the curvature peak at about 30 months. In years that is `λ = 1/(0.0609·12) = 1.368y` (external).
- Identification: with NSS, if `λ1` and `λ2` are close, `β2` and `β3` are not separately identified (Düring).
  Freeze both decays on a pooled sample and refit only the betas daily.
- Classification (Huggins & Schaller, 2024, Ch.3): NS is a "first-category" factor model. The loadings are fixed a
  priori, so any market move whose shape does not match them (e.g. a steepening with a different pivot) ends up in
  the residuals. PCA is "second-category": the data choose the loadings.

## 2. One-factor short-rate models

### Vasicek (equilibrium): `dr = k(θ − r)dt + σ dW`
- `E[r_t] = r0·e^{−kt} + θ(1 − e^{−kt})`, `V[r_t] = σ²(1 − e^{−2kt})/(2k)`, half-life `h = ln2/k`
  (Tuckman & Serrat 2022, eqs. 9.4, 9.5, 9.8).
- Instantaneous forward: `f(t) = θ + e^{−kt}(r0 − θ) − (σ²/2k²)(1 − e^{−kt})² = E^Q[r_t] − ½σ²B(t)²` (eq. 9.6).
- Spot: `r̂(t) = θ + [(1 − e^{−kt})/(kt)](r0 − θ) − (σ²/2k²)[1 + (1 − e^{−2kt})/(2kt) − 2(1 − e^{−kt})/(kt)]` (eq. 9.7).
- Bond price `P(t,T) = A(t,T)·e^{−B(t,T)r}`, `B = (1 − e^{−a(T−t)})/a`,
  `ln A = (B − T + t)(a²b − σ²/2)/a² − σ²B²/(4a)` (Hull, 9th ed., Ch.31, Vasicek with `a = k`, `b = θ`).
  If `a = 0`: `B = T − t`, `A = exp(σ²(T−t)³/6)`.
- Zero yield is linear in `r`: `R(t,T) = −ln A/(T−t) + B·r/(T−t)`. `dP/dr = −B·P`, so `B(τ)` is the duration with
  respect to the short rate (factor duration). It tends to ordinary duration as `k → 0` (Ilmanen & Iwanowski, 1996).
- Forward vol term structure `σ·e^{−kt}`: always downward sloping, so Vasicek cannot produce the empirical hump.
- Risk premium: under the true measure `dr = k(r∞ − r)dt + λdt + σdW`, so `θ = r∞ + λ/k`. Infinitely many
  `(r∞, λ)` pairs give the same prices (Tuckman eq. 9.3).
- Discrete estimation (Hull Example 31.2): regress weekly `Δr` on `r`. A slope of −0.004, an intercept of 0.00016
  and a residual s.e. of 0.001 give a = 0.21, b = 0.04, σ = 0.0072 (annualised), as printed.

### CIR: `dr = a(b − r)dt + σ√r dW`
- `B = 2(e^{γτ} − 1)/[(γ + a)(e^{γτ} − 1) + 2γ]`, `A = [2γe^{(a+γ)τ/2}/((γ + a)(e^{γτ} − 1) + 2γ)]^{2ab/σ²}`,
  `γ = √(a² + 2σ²)`. Zero is unreachable if `2ab > σ²`. Vol comparison: `σ_Vasicek ≈ σ_CIR·√r` (r = 4%,
  σ_vas = 0.01 → σ_CIR = 0.05) (Hull Ch.31).
- Level dependence (Ilmanen & Iwanowski, 1996): CKLS `dr = k(l − r)dt + s·r^γ dz`. γ = 0 is Vasicek (bp vol
  independent of level), γ = 0.5 is CIR, γ ≈ 1 is BDT (relative vol independent of level). Fitted γ was 1.44 on
  1977-94 3m bills but 0.71 on 1983-94; with GARCH it was 0.37 / 0.17. Since 1983, vol has been much less tied to
  the level, which supports normal (bp) vol.

### No-arbitrage (fit today's curve exactly)
- Ho-Lee: `dr = θ(t)dt + σdW`, `θ(t) = F_t(0,t) + σ²t`. All rates are equally volatile.
- Hull-White 1F: `dr = [θ(t) − a·r]dt + σdW`, `θ(t) = F_t(0,t) + a·F(0,t) + (σ²/2a)(1 − e^{−2at})`.
  `ln A = ln[P(0,T)/P(0,t)] + B·F(0,t) − (σ²/4a³)(e^{−aT} − e^{−at})²(e^{2at} − 1)` (Hull Ch.31; West 2010).
- Zero-bond option (Vasicek/HW): call `= L·P(0,s)N(h) − K·P(0,T)N(h − σ_P)`,
  `h = (1/σ_P)ln[L·P(0,s)/(P(0,T)K)] + σ_P/2`, `σ_P = (σ/a)[1 − e^{−a(s−T)}]·√((1 − e^{−2aT})/(2a))`.
  For Ho-Lee, `σ_P = σ(s − T)√T`. Caps and floors are portfolios of these (Hull Ch.31).
- Lognormal family (BDT, Black-Karasinski `d ln r = [θ(t) − a ln r]dt + σdW`): positive rates, no analytics, and
  poor at low rates because one vol cannot fit both low and high rate levels (Hull Ch.31).
- 2F Hull-White: `dx = [θ(t) + u − a·x]dt + σ1dW1`, `du = −b·u·dt + σ2dW2`, correlation ρ.
- HJM view (Brenndoerfer, 2025): `df(t,T) = α(t,T)dt + σ(t,T)dW` with drift condition
  `α(t,T) = σ(t,T)·∫_t^T σ(t,s)ds`. Ho-Lee is constant σ (α = σ²(T − t)). Hull-White is `σ(t,T) = σe^{−κ(T−t)}`,
  so with σ = 1% and κ = 0.1 the 10y forward vol is about 0.37%.

### Calibration notes
- Fix mean reversion and solve σ to an option price. The joint (a, σ) minimum is often unstable, and a ≈ 3% is a
  common fixed choice (West, 2010; Ametrano & Bianchetti, 2013 use a = 3%, σ = 0.3526% for EUR; Henrard's SOFR
  futures example uses Vasicek vol 65bp with 3% reversion, per FINCAD, 2019).
- For futures convexity, 1F models are calibrated to a cap or swaption ATM normal vol (QF Stack Exchange, "SOFR
  futures options", 2023). The convexity-adjustment formulas themselves are in `stir-convexity-adjustment`.

## 3. Gauss+ (Tuckman & Serrat, 2022, Ch.9 and Appendix A9.2)

Risk-neutral cascade dynamics. They are written here in mean-reverting form: the text says r is pushed toward m,
m toward l, and l toward μ.
```
dr = α_r (m − r) dt                                  (no shock: policy rate pegged between moves)
dm = α_m (l − m) dt + σ_m (ρ dW1 + √(1−ρ²) dW2)       (business cycle / policy)
dl = α_l (μ − l) dt + σ_l dW1                         (long-run inflation + real rate; μ includes risk premium)
```
- Reduced form: `x = A(α)X + μ`, `dX = −diag(α)X dt + A⁻¹Ω dW`. Zero yield
  `y(τ) = μ(1 − Υ(τ)·1) − C(τ, α, σ) + Υ(τ)x`, `Υ = B(τ)A⁻¹`, `B_i(τ) = (1 − e^{−α_iτ})/(α_iτ)`. `C` is the
  convexity term. It is zero at τ = 0, grows roughly with τ², and pushes forwards below the risk-neutral
  expectation ("fair futures rate").
- Estimation, US Treasury zeros 2014-2022, daily, with 8 years of history weighted by an annual decay of 0.8:
  1. `r_t` = policy-rate target (not GC repo, whose spikes are unrelated to policy expectations).
  2. Mean reversions: `min_α ‖Υ(α)Υ_b(α)⁻¹ − β̂‖`, where `β̂` are the OLS betas of each zero-yield change on 2y and
     10y zero-yield changes. Model betas depend only on α. Empirical examples: 3y = 0.91·Δ2y + 0.22·Δ10y;
     15y = −0.20·Δ2y + 1.10·Δ10y.
  3. `σ_m, σ_l, ρ`: match the realised yield-vol term structure (annualised bp vol by maturity).
  4. `μ`: minimise squared yield errors over the sample.
  - Estimates: α_r 1.0547 (half-life 0.66y), α_m 0.6358 (1.09y), α_l 0.0165 (42.01y), σ_m 109.2bp,
    σ_l 96.4bp, ρ 0.212, μ 10.555%.
- Daily state: hold `r` at the policy target and solve `(m_t, l_t)` so the model fits exactly the 1y rate 2y forward
  and the 1y rate 10y forward. The authors prefer this to Kalman or least-squares filtering for trading.
- Loadings on 1y forwards: r affects only the very front. m peaks at 2-3y (the "monetary policy" factor). l peaks
  at 6-8y (the 7y forward moves 0.9bp per bp of l) and is the only driver beyond 10y.
- Long-factor plot: `L(l_t) = μ(1 − e^{−10α_l}) + l_t·e^{−10α_l}` ≈ expected short rate in 10 years.

### Term premium from Gauss+ (A9.26-A9.29)
- Only the long factor is priced: `E[dP/P] = r + λ_t·(τ − t)·Υ_3(τ − t)·σ_l`, with λ_t very persistent.
- The expected return of long `τ+Δτ` zero vs short `τ` zero = forward − expected short rate = `λ_t·RP(t, τ, Δτ)`.
- Identifying assumption: the true expected short rate is flat beyond some long maturity. Then
  `λ_t = [f_t(τ′) − f_t(τ)] / [RP(τ′)/Δτ − RP(τ)/Δτ]` (use the 14y and 15y forwards; results are insensitive to
  longer choices), and `E_t(r_τ) = f_t(τ) − λ_t·RP(t, τ, Δτ)` (as printed). The worked example below shows the
  convexity term explicitly: `E = f + CX − TP`.
- Back-of-envelope: λ = 0.09 (sample average), 10y zero loading on l = 0.7, σ_l ≈ 100bp →
  10y risk premium ≈ 0.09 × 0.01 × 10 × 0.7 = 63bp, convexity ≈ 24bp, and with a 3% 10y forward the expected rate
  is 3% + 0.24% − 0.63% = 2.61%.
- External check: compare `E_t(r_10)` with a survey or real-rate-plus-inflation-trend estimate. Tuckman averages
  three long-run inflation measures and adds a real-rate forecast. An EMA trend with decay 0.987 is one of them.

## 4. One-factor risk premium and the forward identity

- Hedged-portfolio argument (Tuckman A8): `E[dP/P] = r·dt + λ·D·dt`, i.e. expected excess return = market price of
  risk × factor duration.
- Ilmanen & Iwanowski (1996), one factor F = own yield: `E[dP/P] = rolling yield − Dur·E(Δy) + ½·Cx·var(Δy)`, so
  `forward = rate expectation + risk premium − convexity bias`. Across bonds this holds only under parallel shifts,
  so bond-by-bond forecasts are not guaranteed to be arbitrage-free.
- No-arbitrage condition: `(μ1 − r)/σ1 = (μ2 − r)/σ2 = λ`. Pricing PDE:
  `∂P/∂t + ∂P/∂F·(mF − λsF) + ½·∂²P/∂F²·s²F² = rP`.

## 5. Discrete-time Gaussian affine models (Cassola & Luis, in Dunis, Laws & Naim, 2003)

- Duffie-Kan affine kernel, log bond price `−p_{n,t} = A_n + B_n′s_t`, yield `y_{n,t} = (A_n + B_n′s_t)/n`, with
  `A_0 = B_0 = 0` and recursions in n. One-period term premium:
  `Λ_{n,t} = −λ′V(s_t)B_n − B_n′V(s_t)B_n/2`, i.e. a pure risk premium plus a Jensen term. At least one market price
  of risk must be negative for the term premium to be positive.
- Gaussian k-factor case (`s_{i,t+1} = φ_i·s_{i,t} + σ_i·ε`, `y_{1,t} = δ + Σ s_{i,t}`, `B_{i,n} = 1 + B_{i,n−1}φ_i`):
  `f_{n,t} = δ + ½Σ[λ_i²σ_i² − (λ_iσ_i + σ_i(1 − φ_i^n)/(1 − φ_i))²] + Σ φ_i^n s_{i,t}` and
  `E_t(y_{1,t+n}) = δ + Σ φ_i^n s_{i,t}`, so `f_{n,t} = E_t(y_{1,t+n}) + Λ_n` with a constant Λ_n.
  With constant prices of risk, the term premium cannot vary over time. A time-varying premium needs prices of risk
  that are affine in the state (the ACM / Kim-Wright class, external).
- Diagnostic (forward-rate regression): `f_{n−1,t+1} − y_{1,t} = const + c_n(f_{n,t} − y_{1,t}) + e`, H0: c_n = 1,
  with Newey-West s.e. Bund 1986-98: c_n = 0.953 (3m), 0.965 (12m), 0.975 (24m), 0.980 (36m), 0.981 (48-60m),
  0.979 (120m), s.e. 0.012-0.029. A constant premium was a fair approximation for the Bund in that era.
- State-space estimation: a measurement equation in 9 zero yields and diagonal AR(1) transitions. Stack the
  model-implied (constant) vol curve as 9 extra measurement equations, because fitting yields alone gave
  "unreasonable" vol estimates. Constrain 0 < φ < 1, σ > 0 and one negative price of risk. Start from
  `vec(P) = (I − F⊗F)⁻¹(G⊗G)vec(Q)`. Suspiciously small Kalman-ML standard errors signal parameter sensitivity,
  not precision.
- Bund estimates (2F, 1986-98): δ = 0.00489, σ1 = 0.00078, φ1 = 0.95076, λ1σ1 = 0.22192, σ2 = 0.00173,
  φ2 = 0.98610, λ2σ2 = −0.09978. Term premium ≈ 1.5pp at 5y and ≈ 1.6pp at 10y (3F: 1.25pp). Monthly yield
  autocorrelation is > 0.98, so yields are "close to being non-stationary".

## 6. Shadow-rate (lower-bound) model (Huggins & Schaller, 2024, Ch.6)

- The shadow rate SR follows Vasicek, and the observed rate is `max(SR, LB)`. LB may vary by maturity (e.g. a
  central-bank purchase-programme yield floor). The market rate equals the average over simulated paths of
  `max(LB, SR_path)`.
- Scenario use: change LB, re-simulate, and read the curve change. The authors' example: an ECB APP yield floor cut
  from −25bp to −50bp, and its effect on 2s10s.
- Estimation is badly behaved: near-identical fits come from very different (σ, θ, k), so parameter histories jump.
  Staged fix: (1) fit all parameters through history; (2) average θ and k, then refit only the start point and σ;
  (3) fix the average σ and refit only the start point. EUR O/N shadow rate from the 1Y-10Y curve fell below −15% in
  2014.
- Shadow-rate curves keep their vol at the bound, so PCA on them has stable eigenvectors. The caveats are that this
  stability comes from Vasicek's level-independent vol, and that shadow rates are not tradable.

## 7. Policy-date jumps (front end)

- The front end needs jumps at scheduled meetings plus diffusion. A purely deterministic process values every OTM
  STIR option expiring before the next meeting at zero. A one-factor Hull-White with jumps in both the rate and its
  reversion level on meeting dates gives consistent futures and option prices (Huggins & Schaller, SOFR Futures and
  Options, 2022). Unscheduled meetings remain the main failure. Meeting-path construction itself belongs in
  `stir-policy-pricing-whats-priced-in`.
