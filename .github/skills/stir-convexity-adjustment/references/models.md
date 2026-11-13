# Convexity adjustment: model formulas, variants and known inconsistencies

Companion to [SKILL.md](../SKILL.md). Rates and vols in decimals here unless stated; sigma = normal short-rate vol per year,
T1 = futures reference start, T2 = T1 + tau (tau = 0.25), t = time to start. Numbers are checked in
[../scripts/convexity_adj.py](../scripts/convexity_adj.py) (`--selftest`).

## 1. Ho-Lee, derived
dr = theta(t) dt + sigma dz. HJM drift of the instantaneous forward f(t,T) is sigma^2 (T - t). Averaging over (T1, T2) and
integrating 0..T1: forward-rate drift `sigma^2 (T1 + T2 - 2t)/2`, so `futures - forward = sigma^2 T1 T2 / 2` for the
continuously compounded rate (BSIC, Understanding Convexity Bias in STIR Futures Markets, 29 Mar 2026; West, Interest
Rate Derivatives lecture notes, 2010).

Simple/compounded rate (the quantity SR3, ED and Euribor actually settle on). With X(T) = integral_0^T r du and
Y = X(Te) - X(Ts), the gap is `ln E_B[exp(Y)] - ln[P(0,Ts)/P(0,Te)] = Cov(X(Te), Y)`. Under Ho-Lee
`Cov = sigma^2 [tau Ts (Ts/2 + tau) + tau^3/3]`, giving the rate CA (F -> 0, small sigma)
`CA = sigma^2 [Ts^2/2 + Ts tau + tau^2/3] = sigma^2 (T2^2 - tau^2/3)/2` (derived here and confirmed numerically in the
selftest). The dominant part, `sigma^2 Ts tau (tau + Ts/2)`, is the exponent in Citi's printed form
`CA = (Fwd + 1/D)[exp(sigma^2 T D (D + T/2)) - 1]`, D = tau (Citi, Rates Vol Lab: Left-side vols' outperformance, 22 Jun 2021).
Setting D -> 0 gives `sigma^2 T^2 / 2`, the form used in the pack screens.

Three forms, difference at T1 = 3.1y, tau = 0.25: `T1sq` 4.8, `T1T2` 5.2, `simple` 5.6 (CA / sigma^2 in 1/yr^2 units, i.e. T1^2/2, T1 T2/2, (T2^2 - tau^2/3)/2).
Convention trap: a `T1T2` implementation fails to reproduce the sell-side pack tables; a `T1sq` one reproduces them to
about 0.2% in implied vol (Blues H6-Z6: 147.4 vs 147.6 published).

Pack form: `CA_pack = sigma^2/2 * mean_i(T1_i^2)`, inversion `sigma = sqrt(2 CA / mean(T1^2))`, vega `dCA/dsigma = sigma w / 1e4`
with w = mean(T1^2) and sigma in bp. The CA is a variance quantity: 3y1y vol is the matching market vol (Blues about 3.25y).

## 2. Hull-White (mean reversion a)
`B(s,t) = (1 - exp(-a(t-s)))/a`.
- Continuous-rate form (BSIC 2026, West 2010): `CA = [B(T1,T2)/(T2-T1)] [B(T1,T2)(1 - exp(-2aT1)) + 2a B(0,T1)^2] sigma^2/(4a)`,
  limit a -> 0 is `sigma^2 T1 T2 / 2`.
- Simple-rate (term-rate futures) form, Henrard (OpenGamma, Interest Rate Futures and their Options, 2012):
  `CA = (1/tau)(gamma - 1)(1 + tau F)`, `ln gamma = integral_0^T1 nu(s,T2)(nu(s,T2) - nu(s,T1)) ds`, `nu(s,u) = sigma B(s,u)`.
  Closed form: `ln gamma = sigma^2 B(tau)/a [ (1 - e^{-aT1})/a - (e^{-a tau} - e^{-a(T1+T2)})/(2a) ]`. At a = 0 equals Citi's
  printed formula. Reproduces Ametrano and Bianchetti's EUR numbers (Dec 2012, a 3%, sigma 0.3526%): Z4 0.30, Z5 0.60,
  Z6 1.00, U7 1.36bp (the continuous-rate form gives 1.29 at U7).
- HW < Ho-Lee for any a > 0 within the same form; at 3% and T1 = 3, 4.8bp vs 5.3bp; at 5y, 11.8 vs 13.8 (sigma 100bp).
- Calibration: caplet ATM normal vol `sigma_HW(T) = sigma B(0,T)/T` as printed by BSIC (exact: sigma (B(tau)/tau) sqrt((1 - e^{-2aT})/(2aT)); the two agree to under 0.1% for a = 3%, T = 3); fit (a, sigma) by least squares over expiries. A steeper
  decline of vol with expiry means higher a; a flat surface means Ho-Lee. Fix a (e.g. 3%) if the optimiser is unstable.
- Sensitivity: HW vol 0.5% / 1% / 2% gives roughly 3 / 12-13 / 45bp at 5y (chart reading, Henrard 2012), quadratic in
  maturity and in sigma.

## 3. Tuckman-Serrat normal model (t = time to START of the period, beta = underlying term)
| Futures type | CA |
|---|---|
| term rate (3m Euribor) | sigma^2 t^2/2 + sigma^2 t beta/2 |
| average overnight (1m FF/SOFR, beta = 1/12) | sigma^2 t^2/2 + sigma^2 t beta/2 + sigma^2 beta^2/6 |
| compounded overnight (3m SOFR) | sigma^2 t^2/2 + sigma^2 t beta/2 + sigma^2 beta^2/3 |
Table 12.12 (sigma 80bp), t = 1/2/5/10y: Euribor 0.4/1.4/8.4/32.8; 1m average 0.3/1.3/8.1/32.3; 3m compounded 0.4/1.5/8.4/32.8
(Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022). The term row is exactly the `T1T2` form.
Known inconsistency: the compounded row carries the cross term t beta/2, whereas the simple-rate derivation above gives
t beta (compounded-in-arrears Ho-Lee `0.5 sigma^2 (T2^2 - tau^2/3)`), a difference of about 0.8bp at t = 10, sigma = 80bp. The
two probably differ because Tuckman measures against a continuously compounded forward. For a pack screen the effect is below the
vol-source uncertainty; for a curve build state the convention.
Dominant term: `sigma^2 t^2/2` (32bp at t = 10, sigma = 80bp).

## 4. Overnight (RFR) futures
- Collateral Gaussian HJM, 3m compounded (Henrard, Overnight Futures: Convexity Adjustment, Feb 2018): `P(0) = 1 - (1/delta)[(P(0,Ts)/P(0,Te)) prod gamma_i - 1]`,
  `gamma(s,t,u,v) = exp(integral_s^t nu(x,v)(nu(x,v) - nu(x,u)) dx)`. The dominant factor is `gamma(0,Ts,Ts,Te)`; the other
  one-day factors are about 0.01bp each. Futures price uses a zero collateral rate. Once k days are fixed their part carries no
  convexity, so CA decays through the reference period. HW 65bp vol, a 3% (GBP): about 7.3bp at the last 6y contract.
- Averaged vs compounded (Rosen, FINCAD, 2019): `C_avg(T0,Tn) = sum_k (delta_k/delta) C_ED(T_{k-1}, T_k)`; averaged is
  close to compounded (at most about 1/3bp at 5y, compounded larger). SOFR 1m: 0-0.07bp; 3m furthest (2024): 4-4.5bp (Vasicek,
  vol 65bp, a 3%, Mar 2019).
- Contract payoffs (Huggins and Schaller, SOFR Futures and Options, 2022): SR3 pays `N tau (R0 - R_T)` at T with R_T
  compounded, so no nonlinearity term, only a financing (daily-margin) bias; SR1 pays on the arithmetic average, and
  overnight reinvestment of the daily balance compounds, so `B_T = N(1 + tau gamma0) + N tau (psi_T - gamma_T)`: gap at most
  0.1bp at 2021-22 rates, about 1bp near 5%. Fed funds futures: notional USD 5mm; each daily rate adjusted separately, fixed days
  carry none (Henrard 2012).
- The ED-style future with payout at S (not T): `B_T = N(1 + tau r0) + N tau^2 r0 R_S - N tau^2 R_S^2`, a concave parabola in
  R_S; Jensen sets the futures rate above the FRA's. Size rises with sd(R_S), i.e. with time to expiry and vol.
- Sign/ordering proof by Jensen (Tuckman and Serrat, App. A12): compounded > average > term > forward.
- Choice of process matters for futures fair value in SOFR: jump probabilities and mean/speed dominate; including spikes in an
  OU calibration moved the price by about 32bp (Huggins and Schaller, 2022). Rule: for CA only, use a calibrated one-factor
  model for consistency with the rest of the desk.

## 5. Replication and hedged-package views
- FRA settlement `P = v N d (r - R)/(1 + d r)`, v = OIS discount factor to settlement. Hedge with futures Ntilde:
  `P_hedged = v N d (r - R)/(1 + r d) - d (F - r) Ntilde`, impose P = 0 and dP/dr = 0. Futures risk per bp is constant
  (d Ntilde); FRA risk `v N d/(1 + dr) [1 - d(r - R)/(1 + dr)]` varies with r and, through v, with the OIS curve (Quantitative
  Finance Stack Exchange, "Why are FRA/futures convexity adjustments necessary?", 2019-2025). A paid FRA hedged with bought
  futures buys more FRA as rates rise and sells as they fall, so it loses with vol: FRA rate < futures rate.
- Darbyshire's FCA (Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022): sell the future, receive a single-period IMM
  IRS; hedge `N* = N (d_i/d*_i) prod B_k^-1`; second-order PV `N prod A_k^-1 sum x_i x_k / A_k` (RFR case); expected P&L over n
  business days with daily vol sigma_BP: front contract `n N d1^2 Var(dr1)/A1^2`. Example: 63 business days, 3bp/day, USD 1bn: front
  0.014bp, whole package 0.057bp for the second contract incl. the front's last three months (printed inputs imply 4bp and
  correlation 0.95). Model choice and vol inputs "have a big impact". Table 21.1 maps hedge mismatches to the adjustment they
  create: STIR futures vs IMM IRS gives FCA; zero-coupon vs IRS gives ZCA; misaligned schedules give IRD convexity bias.
- Gamma sizing: `CA_bp = integral 0.5 Gamma(t) sigma^2 dt / DV01_futures` with Gamma in USD/bp per bp. Constant gamma
  overstates. Normal vol of a listed option: `nvol_bp` of the rate = price-point vol x 100.

## 6. Other formulations
- Duering, Fixed Income Trading and Risk Management (2021): `Delta r = -0.5 sigma^2 t^2` (forward = futures + Delta r), sigma = implied vol of
  options on the contract; quadratic in vol and expiry, so important for long-dated USD contracts and small for short EUR/JPY strips.
- Malliavin/Cheyette closed forms (Garcia-Lorite and Merino, 2023): futures vs FRA
  `CA ~ sigma^2 e^{-k t0} P_E(0,t1)/(delta P_E(0,t2)) [(1 - e^{-k t0})/k^2 - t0 e^{-k t2}/k]`; exact for time-only eta, handles valuation
  inside the accrual period; mean reversion k matters strongly.
- Multi-curve LMM: `C ~ F[exp(integral mu) - 1]` needs the FRA vol and its correlation to spot rates; Kirikos-Novak
  "Convexity conundrums" is the common practitioner recipe (Ametrano and Bianchetti, 2013). Market FRA convexity (paid at start) is below
  1bp, so `R_FRA ~ F`.
- Defining the forward curve from futures makes futures need no CA and moves the adjustment onto FRAs/swaps ("concavity
  adjustment"); zero-rate collateral is equivalent to futures margining (Henrard, My Future Is Not Convex, 2012).
- Term-structure model with a convexity term (Gauss+): at 10y the convexity term is about 24bp against a term premium of about 63bp;
  expected short rate = forward + convexity - term premium (Tuckman and Serrat, App. A9). Using a term-structure model
  for pricing makes separate convexity adjustments unnecessary (Hull, OFOD).
- Implied CA (model-free): `CA(t) = 100 - f_curve(t,S,T) - P_market(t)` contains the true CA and future/cash basis (FactSet, Interest Rate Future
  white paper, 2023). Estimation routes: (1) short-rate model, (2) hedged package with swaption covariance, (3) same with historical
  covariance, (4) imply from the market with a smooth parametric convexity curve; route 4 is what practitioners use because
  supply/demand, CCP margin and venue "can engulf the theoretical prices". Liquidity: little pricing past the Reds; use futures
  at the front, swaps beyond (Quantitative Finance Stack Exchange, STIR Futures convexity adjustment, 2025).

## 7. Source inconsistencies to keep in mind
- Margin-reinvestment vs gamma explanations: sources disagree on mechanism; they agree on sign and on sigma^2 T^2 scaling. Size with gamma x
  variance or Ho-Lee, not with a reinvestment story.
- Huggins and Schaller say SR3 has no nonlinearity and a possible financing bias, "best viewed as an empirical matter",
  and that it matters only if price-setters earn margin interest in P&L; sell-side CA monitors treat the whole gap as
  convexity vs a CCP-specific curve. In practice measure CA against the CCP curve you can trade and let the market-implied number decide.
- A 2013 EUR bias turned slightly negative when futures and FRA margins could not be netted (Aikin, 2013): after 2011, USD CA
  largely vanished with CME cross-margining, then re-opened as positioning and dealer balance sheet shifted (2016-18) and again in 2023.
- Printed-number inconsistencies in secondary sources: Euribor U4 bias 4.6bp gives 2.049% (the text says 2.045%); Darbyshire's front-contract
  354 omits the 1/1.005^2 factor (350.8, same 0.014bp).
