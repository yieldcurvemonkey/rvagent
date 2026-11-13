# Instrument formulas, futures inputs and multi-curve algebra (fi-curve-construction)

Detail behind Method steps 2-5 and 9 of [SKILL.md](../SKILL.md). Rates as decimals inside formulas unless a `%` is shown.

## 1. Money-market and overnight building blocks
- Deposit / simple interest: `P = 1/(1 + r·τ)`, `r = (1/P - 1)/τ`; discount-rate method (T-bills) `P = 1 - r·τ`. MM year base 360 (USD, EUR), 365 (GBP). An instrument >1y straddling a leap year is split into a final exact-1y piece plus a front stub (Duering, Fixed Income Trading and Risk Management, 2021).
- Forward from DFs: `Fwd(t_n, t_{n+1}) = [Df(t_n)/Df(t_{n+1}) - 1]/τ`. Simple-yield and discount-rate forwards are "subtly different" (Duering 2021). Annual compounding: `f_{m,n}` with `(1 + f)^{n-m} = (1 + s_n)^n/(1 + s_m)^m`, linear approximation `(n s_n - m s_m)/(n - m)`; one-year forward `f ≈ s_n + (n-1)(s_n - s_{n-1})` (10.16 vs 10.20 exact in Ilmanen's example, May 1995).
- Compounding: `r_eff = (1 + r/n)^n - 1`; `1 + y_sab/2 = exp(y_cc/2)`, so `dy_sab/dy_cc = 1 + y_sab/2` (Coleman, A Guide to Duration, DV01 and Yield Curve Risk Transformations, 2011).
- ISDA compounded overnight coupon: `[Π(1 + r_i n_i/N) - 1]·N/d_c`; simple (arithmetic) `[Σ r_i n_i/N]·N/d_c`; `n_i` = days the rate applies (3 on Friday), `N` = 360 (USD, EUR, CHF) or 365 (GBP, CAD, JPY by index convention), `d_c` calendar days. Do not compound consecutive daily values of a term (IBOR) curve.
- Weekend accrual is linear, no compounding on non-business days: 2-week ACT/360 `N(1 + r/360)^8 (1 + 3r/360)^2`, not `N(1 + r/360)^14` (Duering 2021).
- OIS breakeven: `[Π(1 + r_i d_i/360) - 1]·360/D`. 1-week FF OIS 6-12 Jan 2010, fixings 0.12, 0.13, 0.14 (3-day), 0.13, 0.10% → product 1.0000250 → 0.0000250 × 360/7 = 0.1286% (Credit Suisse, Basis Points, Feb 2010).
- Lagged compounding: observation period `p`, lag `l`; with `l = 2` the payment equals the OIS rate; European FRNs use `l = 5` (observation shift 2 or 5 business days). Averaging overnight rates never contains a term premium (Duering 2021).
- SOFR Index (NY Fed, base 1 on 2-Apr-2018): `Index = Π(1 + SOFR_i d_i/360)`; term rate `(I_end/I_start - 1)·360/D·100`.
- Compounded vs simple averaging grows with rate level: 1y at constant SOFR 0/100/200/300/400/500bp compounds to 0/101/202/305/408/513bp (Huggins & Schaller, 2022).

## 2. Futures settlement (reference periods)
| Contract | Settlement rate | Notes |
|---|---|---|
| SR3 (3M SOFR) | `R = [Π(1 + SOFR_i d_i/360) - 1]·360/D`; price `100 - R·100`; rounded 0.01bp | reference quarter = 3rd Wednesday of the contract month (incl.) to 3rd Wednesday 3 months later (excl.); $25/bp |
| SR1 (1M SOFR) | arithmetic average over calendar days (weekend/holiday = prior business day); rounded 0.1bp | $41.67/bp; ~13 months listed |
| 3M SONIA (ICE) | compounded ACT/365F | stops trading 8:30am on the last day; 25 listed; futures strips for curves use the 2nd to 13th |
| CORRA futures | compounded, base 365 | |
| FF futures | arithmetic monthly average, 5mm notional, 36 months | |
| Bank-bill futures (AUD, NZD) | yield quoted, `100 - yield` | AUD bills physically delivered with a CTD option (85-95 days) |

Code semantics: IBOR codes name the expiry month; RFR codes name the start of the reference quarter (a December-coded RFR contract starts in December). Mixing shifts dates by a quarter (FactSet, Interest Rate Future, Mar 2023).
In-period contracts: past days use fixings, future days the curve: `Π_hist·Π_future`, solve flat remaining `R` with a root finder (Quantifi, Mastering Interest Rate Curve Construction, c.2023).
Futures NPV is always zero (a quote); fixed `= 100 - price`, payment lag 0, 1M = Average with rate cutoff 0 (a 2-day arithmetic-OIS cutoff is wrong for 1M futures) (Deriscope, Feb 2024).

## 3. Futures strip algebra
- Strip → IMM-dated OIS rate (CME Group, Jun 2025): `DF_i = 1/(1 + R_i d_i/360)`, `CDF_i = Π DF`, `PV_float = Σ CDF_i R_i d_i/360`, fixed `= PV_float/Σ(CDF_i d_i/360)`; use the fixed leg's own day counts if different.
- Strip gross factor and annualisation (Huggins & Schaller 2022): `S = (1 + R_unknown D_unknown/360)·Π(1 + R_j D_j/360)`, `S = (1 + S_ann·365/360)^N (1 + S_ann·F/360)`.
- Strip zero ("stringing"): `Z_n = (1/DF_t)^{1/Σacc} - 1`; futures strip zero `= Π(1 + IFR_k·0.25) - 1`. Stringing compares zero rates and avoids forward-by-forward sensitivity to interpolation (Aikin, STIR Futures, 2012).
- Futures-strip DF chain for a coupon bond: `DF_stub = 1/(1 + IBOR·accrual)`, `DF_n = DF_{n-1}/(1 + IFR_n·days/360)`, `IFR = 100 - P`; interpolate DFs to cash-flow dates.
- Realistic SOFR OIS vs an SR3 strip: ACT/360 on both legs multiplies the coupon by 365/360; a 2-day payment delay extends discounting (if only the floating leg is delayed two DFs are needed and floating PV ≠ 100); the front-contract divisor is not 25 because part of its quarter is known (Huggins & Schaller 2022, Ch. 9).
- SR1/SR3 averaging vs compounding sensitivity: arithmetic `dR/dr_k = d_k/D`; compounded `dR/dr_k = [Π_{i≠k}(1 + d_i r_i/360)]·d_k/D`; compounded ≥ averaged when all rates ≥ 0; gap ≤ ~0.1bp at the 2021-22 lows, ~1bp near 5%. SR1-SR3 fair-value gap over a quarter (SOFR level / in-quarter slope, bp): 0/0 → 0.00; 0/+50 → 2.67; 100/0 → 0.12; 500/0 → 3.11; 500/+50 → 6.09.
- Typical sets: cash, 2×1M + 7×3M futures, swaps from 2Y (QuantFinance Stack Exchange, 2023); CME transition curve: 1M from SR1, 3M-2Y from SR3 with CA, 3Y-50Y from FF-SOFR basis swaps (CME Group, Jun 2020 transition presentation); index-provider strips start at the 2nd contract (reason unstated).

## 4. Convexity adjustments (inputs only; models in stir-convexity-adjustment)
- `futures rate = forward + CA`; `P = 100 - f - CA`. Ho-Lee: `r_fwd = r_fut - σ² T1 T2/2` (σ normal short-rate vol); Hull-White: `CA = [B(T1,T2)/(T2 - T1)]·[B(T1,T2)(1 - e^{-2aT1}) + 2a B(0,T1)²]·σ²/(4a)`, `B(t,T) = (1 - e^{-a(T-t)})/a`. Ho-Lee beyond 2y systematically over-corrects (BSIC, Mar 2026).
- Sizes: EUR 11-Dec-2012 HW 3%/0.3526%: Z4 0.0030%, Z5 0.0060%, Z6 0.0100%, U7 0.0136% (~1.4bp at 5y) (Ametrano & Bianchetti 2013). HW at 5y ≈ 3 / 12-13 / 45bp for σ = 0.5 / 1 / 2% (Henrard, Interest Rate Futures and their Options, 2012, chart read). SOFR 3M (Vasicek 65bp/3%, Mar 2019): up to 4-4.5bp on 2024 contracts, avg-vs-compounded gap ≤ ~⅓bp; 1M 0-0.07bp (FINCAD 2019).
- Workflow: bootstrap a convexity-free pre-curve, calibrate the model, compute CA, re-bootstrap. A 1F model "will slightly overestimate the convexity" (ignores decorrelation); calibrate to caps ATM; fixing mean reversion (e.g. 3%) and solving σ is more stable than Nelder-Mead on caplets (West 2010).
- Implied (market) convexity: calibrate a smooth parametric convexity curve to traded short swaps; composite design `stir_curve (monthly nodes) + convexity curve (3 spline nodes) → swaps curve`; solver instruments = 12 one-month IRS priced on the STIR curve as futures proxies + 6M and 12M IRS on the swaps curve (QuantFinance Stack Exchange, Jun 2025). Residual-implied CA = convexity + future/cash basis.
- Alternative framework (Henrard, My Future Is Not Convex, 2012): build the forward curve directly from futures (`Φ = 1 - (P(t,t1)/P(t,t2) - 1)/δ`) so futures need no CA and the adjustment moves to FRAs/swaps; using futures implicitly assumes a term-structure model (usually 1F Gaussian HJM); building from FRAs implicitly assumes a constant spread.

## 5. Swap / FRA / deposit instruments in multi-curve builds (Ametrano & Bianchetti, 2013)
- Deposit: `P_x(T0,Ti) = 1/(1 + Rτ)`, uncollateralised, hard to transact for a swaps desk; prefer FRAs (unfunded, collateralised) over deposits.
- FRA: `R = (1/τ){[1 + Fτ]e^{C^FRA} - 1}`, `C^FRA` below 1bp even for long maturities, so `R_FRA ≈ F`; bootstrap `P_x(Ti) = P_x(T_{i-1})/(1 + R_FRA τ)`.
- Futures: `R_fut = F + C^Fut`; bootstrap `P_x(Ti) = P_x(T_{i-1})/(1 + [R_fut - C^Fut]τ)`.
- IRS: `R = Σ P_c(Ti) F_{x,i} τ_i / A_c`; the telescoping `P_c(T0) - P_c(Tn)` identity does not hold for a tenor leg even approximately, so each pillar needs interpolation within the last fixed period and a numerical solve.
- OIS: coupon `Π(1 + R_on τ_k) - 1`; under perfect collateral float leg `= P_c(T0) - P_c(Tn)` so `R = [P_c(T0) - P_c(Tn)]/A_c`.
- Basis swaps: two conventions (two IRS, fixed-rate difference, standard in EUR since 2008; or float-vs-float + spread); quote = higher-frequency leg minus lower-frequency, normally positive; `R_IRS,x = R_IRS,6M + Δ(x vs 6M)`; basis quoted to 30Y vs IRS to 60Y, so extrapolate beyond 30Y. AUD 3s6s = semi 6M swap minus quarterly 3M swap, 1Y-30Y (Deutsche Bank, DBIQ, Feb 2023).
- Synthetic instruments: interpolate quotes (monotone cubic; extrapolation subjective); synthetic deposit `R_FRA,x τ_x = R_OIS τ_on + Δ_on,x` with `Δ(T1,t) = α + β(t - T1) + γ(t - T1)²` (β tiny: a constant FRA-OIS basis suffices); synthetic FRA = OIS on the same dates + interpolated FRA-OIS spread.
- Exogenous vs endogenous: forward curves bootstrapped on a predetermined OIS discount curve (exogenous) vs self-discounted (endogenous: misprices non-inputs by 0 to a couple of bp, "still used in old-style libraries ... sometimes unconsciously").
- EUR recipes (11-Dec-2012): C_1M = synthetic deposits, 1M deposit, IRS1M to 1Y, IRS6M + 1s6s to 30Y, flat basis 35-60Y; C_3M = synthetic deposits, Tom FRA, 8 futures to 2Y, IRS3M 3-30Y, IRS6M + 3s6s 35-50Y; C_6M = synthetic deposits, 19 FRA 6M (to 18x24), IRS6M 3-60Y; C_12M = FRA 12M (only 12x24 quoted), IRS6M + 6s12s to 30Y.
- Single-curve failure (EUR 11-Dec-2012): FRA3M 1x4 0.165%; compounded implied 1x7 0.146% vs FRA6M 1x7 0.293%, a 14.7bp inconsistency. Basis levels: 1s6s 22.2bp (1Y), peak 25.0bp (5-6Y), 16.3bp (30Y); 3s6s 14.5/12.5/7.0/5.4 (1/10/30/50Y); 6s12s 26.2/11.3/6.6; 1M deposit 0.110% vs OIS 0.074% (3.6bp).

## 6. Two-curve algebra (Tuckman & Serrat, 2022)
- With an RFR-vs-tenor basis you cannot have simultaneously the RFR leg at par, `RFR + basis` fair vs the tenor leg, and the tenor leg at par. Discount on RFR OIS DFs and value the tenor leg as par + PV of the basis stream.
- Pricing condition: `c Σ(annual accrual × d) + d(T) = 1 + x Σ(quarterly accrual × d)`. Adjusted forwards `L'`: `Σ L'(s) d(s) + (1 + L'(t)) d(t) = 1 + x(t) Σ d(s)`, bootstrapped from swap rates alone; project with `L'`, discount at RFR DFs.
- Collateral defines the discount RFR: if collateral earns SOFR the SOFR leg is par. In a SOFR-vs-€STR xccy basis only one leg can be par.
- Rate/spread segregation (Darbyshire, PTIRD 2022): indexed forward zero rates `r_i`, discount spread `s_i`, forecast spread `z_i`: `v_i = v_{i-1}/(1 + d_i(r_i + s_i))` (CSA discount), `w_i = w_{i-1}/(1 + d_i r_i)` (outright), `x_i = x_{i-1}/(1 + d_i(r_i + z_i))` (forecast); `dP/dr_j = dP/ds_j + dP/dz_j`. With a single RFR curve `z = 0` and only `d²P/dr²` remains. DF derivatives: `dv_i/dr_j = -α_j^i d_j v_i` (a DF is unaffected by rates after its own date). A 3Y1Y forward +1bp takes `v_10 = 0.70000` to 0.69993; a 10Y IRS +1bp takes it to ~0.69930.
- Cross-CSA / xccy: `w_i = (v_i/w*_i)·v*_i`, forward FX `f_i = (w*_i/v_i)F0` must not depend on CSA; `w*_i = (1 + z^fx_i/f_{i-1})(v_i/v_{i-1})w*_{i-1}` from FX swaps; mid XCS spread `Z* = [Σ w*_{i-1} - Σ(1 + r*_i d*_i)w*_i]/Σ d*_i w*_i`. n currencies need n local curves + n-1 cross-collateral curves; CSA curves affect DFs, not forwards. Detail: [fi-collateral-csa-and-xva](../../fi-collateral-csa-and-xva/SKILL.md).
- Multi-desk dependency: chain solvers (pre-solvers) rather than one giant solver or rebuilding another desk's curves; cyclic dependency (solver → curves → FX forwards → instruments → solver) is handled by refreshing FX forwards inside the iteration (Darbyshire, Coding Interest Rates, c.2024).

## 7. Bond-based curves (reference)
- Bootstrapping DFs from bonds: choose bonds maturing at ~6-month intervals, use the most recently issued where several share a maturity; solve sequentially, e.g. `101.4297 = (100 + 2.875/2)·d(0.5)`; matrix form `d = (C')⁻¹ p` when at least one bond pays on each date (Tuckman & Serrat 2022). Rich/cheap = market price - PV at the benchmark DFs; only P-STRIPS inherit the bond's richness.
- Fitted forms (Nelson-Siegel, Svensson, exponential splines `Df(t) = Σ b_i e^{-iαt}`, `Σb_i = 1`, linear least squares; Vasicek; composite spread curves `Df = Df_B·Df_S`) and the yield-space weighting `w_i = 1/(P_i D_i)` belong to [bond-rich-cheap-fitted-curve](../../bond-rich-cheap-fitted-curve/SKILL.md) and [curve-term-structure-models](../../curve-term-structure-models/SKILL.md). Discount-function criteria `φ(τ) = e^{-h(τ)}`, `lim_{τ→∞} φ = 0`, `lim_{τ→0} φ = 1` (Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).
