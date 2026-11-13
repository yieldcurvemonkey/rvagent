# Basis swap pricing, risk and futures weights: derivations and worked numbers

Detail for [SKILL.md](../SKILL.md). Notation: `d` accrual fraction, `r` simple forward for the period, `v` discount factor
at the payment date, `N` notional, `A = Σ d v` the annuity of a leg. All formulas are implemented and tested in
[`scripts/basis_tools.py`](../scripts/basis_tools.py).

## 1. Fair spread and its sign

Receiver of `leg_a + Z`, payer of `leg_b`:

    PV = N · [ Σ_i d_i (r_i + Z) v_i − Σ_j d_j r_j v_j ]

Set PV = 0:  `Z = ( Σ_j d_j r_j v_j − Σ_i d_i r_i v_i ) / Σ_i d_i v_i`  (the `leg_b` annuity-weighted rate minus the `leg_a` one, divided by the `leg_a` annuity).

- One practitioner text prints the numerator in the opposite order, which gives the opposite sign for the same PV expression. Always verify by repricing.
- Flat check: leg_a 3M forward 2.00%, leg_b 6M forward 2.10%, DF 1: `Z = (10 × 0.5 × 2.10 − 20 × 0.25 × 2.00)/5 = 0.10%` = 10bp.
- Spread on the other leg: PV equality gives `Z_b = Z_a · A_a / A_b` (spread subtracted from leg_b). Differences between the two quoting conventions are an annuity ratio,
  for example a spread on FRA conventions versus a difference of two par swap rates.
- Under ISDA or ISDA-flat spread compounding, PV is non-linear in `Z`; a +15mm PV on the float leg gives 362.23, 357.71 and 360.66bp under none, ISDA and ISDA-flat
  compounding (Darbyshire, Coding Interest Rates). Solve with the quadratic.
- IBOR/OIS: put the spread on the IBOR leg (the OIS leg compounds, `r_j = (Π(1 + d_k r_k) − 1)/d_j`). OIS example (Darbyshire, 3rd ed.): fixings Thu 2.00%,
  Fri 2.10% (applies over the weekend, DCF 3/365), Mon 2.15%; period Thu to Tue = 2.0902%. Weekend and holiday fixings can dominate short legs.

Basis DV01 (receiver of the spread): `dPV/ds = −N · A_a · 1e-4` per bp (negative: receiving the spread loses when the market spread widens). A quarterly leg, 5y,
$100mn, DF 1 gives −$50,000/bp. The analytic delta to the spread on the carrying leg is `−∂PV_leg/∂z`. Convention: positive basis risk "prefers the rates of the longer tenor index to increase relative to the shorter tenor index (per bp)".

## 2. Credit theory and the funding anchors

- Tenor basis (Lehman, Jun 2003): swapping default-free rates of different terms trades flat because a default-free FRN of any term is worth par. The observed spread is the premium of a term loan over rolling
  shorter loans. Counterparties to the swap bear no index credit risk; they value the certain receipt of one index against another.
- Decomposition (Huggins & Schaller, 2nd ed., 2024): (a) secured vs unsecured overnight is the **cost of capital** (`g · q · d`: g cost of equity, q interbank risk weight min 20%, d capital ratio 8%; q·d = 1.6%; g = 10% gives 16bp; a rise in d from 8% to 12% would move a Bund ASW against LIBOR/estr by 50%,
  e.g. −20 to −30bp); (b) unsecured overnight vs unsecured term is **credit** (same risk weight); other parts: expected rates (symmetric, not persistent), compounding (with overnight certain at 5% for a year 6M LIBOR is about 4–5bp higher), compounding convexity (below 1bp), term premium (unobservable).
- Repo-LIBOR model: secured profit `[1+R] − [1+b]` (b low-cost funding such as deposits); unsecured cost of funds `(1−qd)[1+b] + qd[1+g]`; unsecured expected return `pc[1+L] + (1−p)[1+L]` (p default probability, c recovery). Equating gives
  `L = R/(1 − p(1−c)) + p(1−c)/(1 − p(1−c)) + qd(g − b)/(1 − p(1−c))`: insurance on interest, on principal, and the capital charge. `L − R` rises with the rate level, cost of core capital and required capital ratios.
  Haircuts are ignored; a 2% haircut at SOFR + 5% costs about 10bp in a swap spread (implied marginal haircut cost 8bp in Sep 2023).
- Basis sensitivity: +5% in the cost of equity widens LIBOR-repo by about 8bp. Expected ordering ceteris paribus of CCBS types: SOFR vs foreign unsecured overnight more negative than LIBOR/LIBOR, SOFR vs foreign term rate more negative still
  (illustration −20bp and −28bp). A general rise in all CCBS tends to come with wider spreads between types.
- 10y Bund estr ASW fair value = −16bp (unsecured-secured basis, g = 10%) + 15bp (adjusted CDS) − 6bp (specialness) = −7bp. The SOFR basis itself is unaffected by g, q, d.
- Pricing any CCBS type via intra-currency basis: SOFR-Euribor CCBS = LIBOR/LIBOR CCBS + fair value of SOFR-USD LIBOR basis (+ foreign LIBOR-overnight basis if needed). The SOFR-vs-FF futures spread gave a market price for the secured-unsecured piece.

## 3. Multi-curve consistency (Tuckman & Serrat, 2022; Ametrano & Bianchetti, 2013)

- Identity (A13.2): `c · Σ(acc_ann · d) + d(T) = 1 + x · Σ(acc_q · d)`, `d` = RFR discount factors, `c` = fixed rate vs 3M Euribor, `x` = estr + x vs 3M Euribor. Published inputs (24 Feb 2022, ACT/360):
  quarterly DFs 1.0014099, 1.0028134, 1.0038902, 1.0044606, 1.0042784, 1.0035455, 1.0024888, 1.0012201 (printed 1.25y rate 0.3880% should read 0.3380%). With ACT/360 accruals ≈ 365/360 per year, c = 0.078% solves `x` = 13.80bp and both sides equal 100.281.
- Two-curve method: starting from `c(t)Σd + d(t) = 1 + x(t)Σd`, define adjusted IBOR forwards `L'` by `ΣL'd + (1 + L'(t))d(t) = same RHS`. (1) Bootstrap `L'` from IBOR swap rates alone, (2) project floats with `L'`, (3) discount both legs on the RFR curve.
  If IBOR swaps are priced fairly relative to RFR OIS you need no basis quotes; the method implies fair basis spreads and is preferred when basis swaps are illiquid.
- Multi-curve IRS: `R_IRS = Σ P_c(T_i) F_{x,i} τ_i / A_c`; the single-curve telescoping `P_c(T0) − P_c(Tn)` fails, even approximately. OIS under perfect collateral keeps `[P_c(T0) − P_c(Tn)]/A_c`.
- Procedure: one discount curve from instruments matching the collateral rate; one forwarding curve per tenor from homogeneous instruments (1M/3M/6M/12M); forwards from the tenor curve, discount factors from the discount curve.
  Exogenous (forwarding on a predetermined OIS discount curve) is the only consistent method.
- Synthetic FRA-OIS: `R_FRA,x τ_x = R_OIS τ_on + Δ`, basis polynomial `Δ(T1,t) = α + β(t−T1) + γ(t−T1)²…`; β was found very small so a constant FRA-OIS basis suffices. Forward basis curve = FRA_x − FRA_OIS; build it with length equal to the tenor (smooth)
  rather than overnight length (spiky at the turn of year).
- Single-curve failure (EUR, 2012): FRA 1x4 = 0.165%; compounded implied 1x7 6M = 0.146% vs market 6M FRA 1x7 = 0.293%, a 14.7bp gap (price of liquidity and credit between 6M and 2×3M).
- Synthetic swaps: a 10y fixed/IBOR swap plus a 10y IBOR/OIS basis swap is a synthetic fixed/OIS swap and reduces the problem to a single curve; if curves are interconnected (AUD) use a global optimiser (Quantifi, Mastering Interest Rate Curve Construction).
- Cross-currency footnote: in a SOFR vs estr CCBS only one leg can be at par; the collateral currency's RFR defines it.

## 4. Risk transforms

- **Instrument bump + inverse Jacobian** (QF Stack Exchange, Dec 2020): bump each curve-building instrument and refit; the per-instrument delta × the instrument move = P&L. Report sensitivities of reporting instruments (swap rates) to hedging instruments (futures), then
  multiply the book's hedging sensitivities by that matrix; aggregate to parallel DV01 per curve or n-sd moves in the first three PCs.
- **Delta = discounting + forecasting basis:** `dP/dr_j = dP/ds_j + dP/dz_j`. Recursions: CSA discount `v_i = v_{i−1}/(1 + d_i(r_i + s_i))`; outright `w_i = w_{i−1}/(1 + d_i r_i)`; forecast `x_i = x_{i−1}/(1 + d_i(r_i + z_i))`.
  A discount factor never depends on rates or spreads after its own date. Worked: receive 5y IRS, 830mm, fixed 25%: 1y dP/dz −82,178, dP/ds −94,111, dP/dr −176,289 (Darbyshire, Ex 22.4).
- **Discount-delta approximations:** annuity IRS `DP/Ds ≈ −P · tenor/(2 · 10,000)`; ZCS `−P · tenor/10,000`; forward-starting `−P · fwd tenor/10,000` plus the IRS term. CSA mismatch example (Ex 21.4): receive $1mm pv01 30y GBP IRS under a USD CSA, pay under a GBP CSA: a +1bp GBP rate move shifts the discounting risks by ±$1mm × 30/(2 · 10,000) = ±$1,500 pv01 (GBP 3M/OIS +1,500, GBP/USD xccy −1,500, USD 3M/OIS −1,500), i.e. a cross-gamma.
- **Cross-gamma types (single currency):** (i) delta/basis, (ii) inter-curve delta/delta, (iii) inter-curve basis/basis, (iv) multiple basis/basis (6M/3M basis moves change 3M/OIS risk). Symmetric: `d²P/dr_j dz_k = d²P/dz_k dr_j`. Second-order risk is a linear combination of first-order forward zero-coupon risks;
  transform with `G* = J G Jᵀ`; `ΔP ≈ S·Δx + ½ Δxᵀ G Δx`. Cross-gamma is about 1e-4 of first-order risk but grows with the square of the move and with grid size.
- **Aggregation:** (1) sum by risk type (3M outright, 6M/3M, 3M/OIS) optionally bucketed < 5y, 5–10y, > 10y; (2) PCA-weighted scenario summation with a separate PCA per category. Worked grid (Darbyshire, Ch 21): 3M/3M 117, 3M × 3M/OIS −279, 3M/OIS × 3M/OIS −62; PC1 loadings 3M (0.20, 0.75, 0.63) with sd 7.0 and 3M/OIS (0.55, 0.60, 0.58) with sd 0.9.
  Reading: a 4y1y diagonal +12 means long gamma; a cross element −101 means +1bp in 4y1y cuts 15y5y 3M/OIS basis risk by 101 pv01.
- **VaR-minimising proxy hedge:** `c = sqrt(Sᵀ Q S)`; minimum-variance post-trade delta `x* = −Q_hh⁻¹ Q_hb S_basis` (note-taker reconstruction; the book gives only the result). Worked (Ex 21.9): book 3M 10y −4,000, 3M 30y −18,000, 3M/OIS 10y −110,000, 3M/OIS 30y −290,000;
  covariance (order 3M10Y, 3M30Y, OIS10Y, OIS30Y) rows [30.3, 13.1, 0.29, 0.16], [13.1, 8.41, 0.09, 0.10], [0.29, 0.09, 0.16, 0.07], [0.16, 0.10, 0.07, 0.05]; c = 133,153. Trading only 3M delta (+5,790 at 10y, +19,838 at 30y) cuts c about 25% to 101,958.
- **Spot-start vs forward-start:** a basis swap with known first fixings carries directional stub risk; hedge the stub with the short-tenor IRS (legacy CS note).

## 5. Futures weights and fair values (USD)

- Bp value: 1M contract = $5mn × 30/360 × 1e-4 = $41.67; 3M contract = $1mn × 90/360 × 1e-4 = $25. Equal-risk ratios: 10 three-month vs 6 one-month (3 + 3 consecutive months, 250.02 vs 250); 1:1 for one-month vs FF and 3M SOFR vs the legacy 3M Eurodollar contract (equal bp value).
  Contracts = weight × exposure bp value / contract bp value.
- Averaged vs compounded: arithmetic `dR/dr_k = d_k/D`; compounded `dR/dr_k = [Π_{i≠k}(1 + d_i r_i/360)] d_k/D`. Compounded 1y of constant SOFR (bp → bp): 0→0, 100→101, 200→202, 300→305, 400→408, 500→513. Three-month contract settlement: `R = [Π(1 + SOFR_i d_i/360) − 1] · 360/D · 100`.
- **FOMC-neutral weights** (Huggins & Schaller, SOFR Futures and Options): a one-month average contract's sensitivity to a hike at a meeting = hike × (days after meeting / days in month), e.g. 25 × 27/31 = 21.8bp for the May-2022 contract. Two-step hedge of a March-2022 three-month contract whose period contains the 4 May 2022 meeting:
  level sensitivity −25.02 $/bp, jump sensitivity −11.27 $/bp; May one-month jump sensitivity (27/31) × 41.67 = 36.29; `n_May = 11.27/36.29 = 0.31`; `n_Apr = 25.02/41.67 − 0.31 = 0.29`, i.e. sell 3.1 May + 2.9 April one-month per ten three-month (not 3 + 3). Sep-2018 example: 2.24 Oct + 3.79 Nov.
- **Period spread fair value (one-month vs three-month averaging, bp):** SOFR 0%, slope 0/+25/+50bp within the quarter: 0.00/1.33/2.67; SOFR 100: −50/−25/0/+25/+50 → −2.59/−1.24/0.12/1.49/2.85; SOFR 500: → 0.15/1.62/3.11/4.59/6.09. CME's price convention differs from the true weighted spread by < 1bp.
- **Legacy 3M SOFR vs Eurodollar spread regression** (Eurodollar contracts ended Jun 2023; method only): `spread (bp) = 4.825 + 2.322 × SOFR(%) − 0.394 × CCBS(bp)`; R² 0.51–0.67. OU fit to the residual: half-life 2.6–3.7 weeks, 90% performance 8.5–12.3 weeks, 1-week Sharpe at a 10bp residual 5.4–7.7.
  The residual was seldom large enough to stand alone after costs; use it as an overlay and as timing for swapping xccy exposure into the spread futures. The proxy works for CCBS moves, not for FX-hedged purchase cash flows.
- **Exchange spread pricing** (CME, Apr 2024): `Spread = avg front-leg price − back-leg price`. Buying one FF/3M spread = sell 10 three-month SOFR, buy 3 + 3 one-month contracts; last trading day is the earliest leg's; margin offset applies.
  FF vs 3M SOFR Jun-2024: (94.890 + 94.735)/2 − 94.7775 = 0.035 = 3.5bp. Liquidity tracks basis exposure: in 2021 the SOFR-vs-Eurodollar spread traded about 530k, the one-month SOFR vs FF about 50k.
- **Term SOFR hedge** (27 Jan 2022, 2y $100mn loan on 3M Term SOFR): hedging the second payment (forward 0.5485%, payment $136,992.80) with a global fit sold 45 one-month + 25 three-month contracts; +25bp stress after 16 Mar 2022 misses by $433 (< 0.7%), −40bp by 1.4%.
  Term SOFR smoothness penalty = sum of squared second differences of forwards with lambda about 0.33 (1/√(number of FOMC meetings)); the authors suspect an upward bias (6M term rate 0.42% at lambda 0 vs about 0.73% at 200) and flag governance concerns. The source gives two different forward values (0.54195% and 0.54850%); use the second only with its inputs.
- FF vs Eurodollar overlap weighting (Aikin, 2012): a 1,000 H2 Eurodollar vs 600 FF = 67 Mar + 200 Apr + 207 May + 127 Jun by overlap days. Swapnote vs Euribor bundle: BPV-neutral sizing from Swapnote BPV = €100,000 × 109.19/100 × 1.921 × 0.01% = €20.975; 100 Swapnotes ≈ 10.485 bundles. The forward swap rate (0.996472/0.969603)^(1/2) − 1 = 1.376% vs Swapnote-implied 1.314% (about 6bp below) is a 3s6s tenor effect.

## 6. Issuance and hedge-index mapping

- Adjusted cross-border issuance spread = unadjusted credit spread + xccy basis + 3s6s basis; a US issuer in EUR receives fixed EUR IRS and pays 6M Euribor, converts to 3M with a 3s6s basis swap and to USD with the xccy swap. Sep 2024 table (0–3/3–6/6–10/10+y): unadjusted USD-EUR 13/14/23/31; xccy −8/−11/−13/−15; adjusted −1/−2/7/17,
  so cheaper in USD for short tenors and in EUR for long (JPM, Cross currency basis 4Q24 Outlook, 26 Sep 2024).
- Hedging corporates with secured-RFR swaps or futures leaves the unsecured-secured basis; use unsecured-index hedges unless you want that view. Use SOFR swaps for governments and FF swaps for corporates, linked by the SOFR-FF basis (Huggins & Schaller).
- Strip-vs-swap: strip zero `Π(1 + IFR_i × 0.25) − 1` vs swap zero `(1/DF)^(1/Σacc) − 1`; compare zeros not forwards; the 3M strip vs 6M-based swap gap is tenor basis plus forward-start mismatch. Nov 2011 case: futures 98.00/97.90/97.80/97.70 gave strip zero 2.167% vs swap zero 2.564% (Aikin, 2012).
