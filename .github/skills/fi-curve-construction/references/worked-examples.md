# Worked examples and numbers (fi-curve-construction)

All figures are quoted from the cited documents. Rates in percent, spreads in bp unless stated. They are test vectors for your own build, not current market data.

## 1. SOFR OIS bootstrap, 14-May-2021 (ACT/360, annual, spot T+2)
Source: Tuckman & Serrat, Fixed Income Securities (4th ed., Wiley, 2022), Table 2.1.

| Term (y) | Swap | Spot | 6m-forward at that term | DF |
|---|---|---|---|---|
| 0.5 | 0.0340 | 0.0348 | 0.0348 | 0.999826 |
| 1.0 | 0.0460 | 0.0466 | 0.0585 | 0.999534 |
| 1.5 | 0.0670 | 0.0681 | 0.1111 | 0.998979 |
| 2.0 | 0.1120 | 0.1136 | 0.2500 | 0.997732 |

Equations: `100(1 + 0.0340%·184/360)·d(0.5) = 100`; `100(1 + 0.0460%·365/360)·d(1) = 100`; `0.0670·(184/360)·d(0.5) + 100(1 + 0.0670%·365/360)·d(1.5) = 100`;
`0.1120·(365/360)·d(1) + 100(1 + 0.1120%·365/360)·d(2) = 100`. Schedule: tenors < 1y pay once; a non-integer tenor gets a front stub then annual payments (1.5y pays at 6m and 18m).
Check: spot ≈ average of forwards, (0.0348 + 0.0585 + 0.1111 + 0.2500)/4 = 0.1136. A 2y swap on $100mm pays 0.1120% × 365/360 × 100mm = $113,556 a year.

## 2. EUR OIS bootstrap, 24-Feb-2022 (Tuckman & Serrat 2022, App. A13)
Rate / DF: 0.25y -0.5695% / 1.0014099; 0.5y -0.5580% / 1.0028134; 0.75y -0.5110% / 1.0038902; 1y -0.4380% / 1.0044606; 1.25y -0.3380% / 1.0042784; 1.5y -0.2330% / 1.0035455; 1.75y -0.1400% / 1.0024888; 2y -0.0600% / 1.0012201
(DF above 1 for negative rates). Up to 1y one payment: `1 = (1 + r·days/360)·d(T)`. For 1.25-2y two fixed payments: `1 = r·(days to T-1y)/360·d(T-1y) + (1 + r·(days T-1y→T)/360)·d(T)`.
2y Euribor swap 0.078% vs 2y €STR / 3m Euribor basis 13.8bp: both legs of the 2y fixed vs 3m Euribor are worth 100.281 (the Euribor leg is par plus the PV of the basis stream), so a single-curve par assumption is wrong by 28c per 100.

## 3. SOFR curve 25-Feb-2022 from SR1 + SR3: bootstrap vs least squares
Source: Huggins & Schaller, SOFR Futures and Options (Wiley, 2022), Ch. 6.
Inputs (settlements). SR1 Jan22 99.95, Feb22 99.80, Mar22 99.635, Apr22 99.37, May22 99.225, Jun22 99.095, Jul22 98.935, Aug22 98.875, Sep22 98.735, Oct22 98.585, Nov22 98.475, Dec22 98.395, Jan23 98.30.
SR3 Dec21 99.9475, Mar22 99.4975, Jun22 99.02, Sep22 98.635, Dec22 98.345, Mar23 98.095, Jun23 97.95, Sep23 97.91, Dec23 97.92, Mar24 97.995, Jun24 98.06.
- Bootstrap steps: rest of Feb 0.0525%; from 17-Mar the Mar22 SR1 gives 0.35733% and the Apr22 SR1 gives 0.365% (least squares on both 0.36355%; 0.365% chosen, 16-Mar to 4-May); 4-May to 15-Jun 0.65574%; 15-Jun to 27-Jul 0.89426%;
  27-Jul to 21-Sep 1.00005% (taken from Aug22 because July has too few post-meeting days); 21-Sep to 2-Nov 1.18833%.
- Errors (price cents = bp of rate): bootstrap MAE 0.83c on the first nine SR1 and 1.36c on Mar/Jun SR3; skipped Sep22 SR1 misprices by nearly 7c. Least squares on the same segment: MAE 1.10c (SR1) and 0.50c (SR3), max 4.44c (Sep22 SR1), max SR3 0.65c, i.e. a lower maximum error than the bootstrap.
- Full fit to end-2025: SR1 errors about 0 for the first ~6 contracts then ±3-6c on contracts 7-13 (less liquid); SR3 Sep22/Dec22 about -3 to -4c, ~0 from the 6th SR3 on. Unregularised, the curve rises from ~0.05% to ~2.1% by late 2023 then oscillates (noise, not policy); with the smoothness penalty it plateaus ~2.05-2.1% in 2023-24 easing to ~1.85%.
- Rule: bootstrap if specific contracts must reprice exactly; otherwise fit. Penalty `Q = Σ(f_i - f̂_i)² + φ Σ_j (2θ_j - θ_{j-1} - θ_{j+1})²`; example forwards 0.05, 0.04, 0.05, 0.06, 0.04 give a butterfly penalty `0.0004 + 0 + 0.0009 = 0.0013`.

## 4. Mismatched-date hedge with a step curve (Huggins & Schaller 2022, Ch. 7)
Lending 2-Dec-2019 to 28-Feb-2020; FOMC 11-Dec-2019, 29-Jan-2020, 18-Mar-2020. Fit to SR1 Dec19/Jan20/Feb20 at 98.37 / 98.375 / 98.425 gives steps 1.6300% / 1.6250% / 1.5750%. A +1bp bump moves the exposure by 1,226.95;
SR3 price change 0.01004, so 1,226.95/(0.01004 × 2,500) = 48.88 lots. A 50-lot SR3 hedge gained 15,575 against a 6,742.88 shortfall (date-mismatch risk); an SR1 strip (per-period DV01 403.27 / 432.26 / 391.42, BPV 41.67) cut the hedge error to 4.3%.
Lesson: date mismatch dominates hedge error; match the futures reference periods to the exposure and close the hedge at the end of the exposure period.

## 5. Meeting sensitivities and meeting-neutral hedge (Huggins & Schaller 2022)
- SR1 move = hike × (calendar days of the month after the effective date)/(days in month): 25bp effective 5-May-2022 → 25 × 27/31 = 21.8bp.
- SR3: reprice with post-meeting fixings bumped: `100 - F_k = [Π_pre(1 + r_i d_i/36000) · Π_post(1 + (r_i + j_k)d_i/36000) - 1] · 360/D · 100`; Mar-22 SR3 moves 11.3bp.
- Meeting-neutral hedge: Mar-22 SR3 sensitivity to level s_l = -25.02 USD/bp and to the jump s_j = -11.27 USD/bp; May SR1 jump sensitivity (27/31)×41.67 = -36.29; n_May = 0.31, n_Apr = 25.02/41.67 - 0.31 = 0.29, so sell 3.1 May + 2.9 Apr SR1 per 10 SR3 (vs the standard 3 + 3). Sep-2018: 2.24 Oct + 3.79 Nov per 10 SR3.
- Hedging a 6M term rate from 1-Jan-2022 with 4 meetings: 5 parameters (start level + 4 jumps); 7 candidate contracts, overdetermined; chosen Jan, Feb, Mar, Jun SR1 + Mar SR3 with bp-risk weights 0.17 / 0.14 / 0.19 / 0.17 SR1 + 0.33 SR3 per 1bp of term rate.

## 6. SR3 stub and 6M strip (Huggins & Schaller 2022)
In-period SR3 as a stub: `R_unknown = [(R·D/360/100 + 1)/Π_known(1 + SOFR_i d_i/360/100) - 1]·360/D_unknown`. 6M strip from 3-Oct-2022: known Sep-22-quarter SOFR 95bp; prices 99, 98.5, 98 for Sep-22, Dec-22, Mar-23; last period 15-Mar-2023 to 3-Apr-2023 → annualised 6M strip 1.34%.
Gross factor: `S = (1 + R_unknown D_unknown/360) Π_j (1 + R_j D_j/360)`; annualise from `S = (1 + S_ann·365/360)^N (1 + S_ann·F/360)`.

## 7. Strip to IMM OIS (CME Group, Pricing and Hedging USD SOFR Swaps with SOFR Futures, Jun 2025)
Prices M5 95.895, U5 96.290, Z5 96.605, H6 96.815, M6 96.940, U6 96.985, Z6 96.965, H7 96.910 (91-day periods); CDFs 0.989730, 0.980535, 0.972191, 0.964427, 0.957024, 0.949786, 0.942555, 0.935249; Σ discounted float 0.0647505; Σ discounted daycount 699.926;
fixed = 23.310/699.926 = 3.3304%. Bump all futures by 1bp → 3.3204%; ΔPV $19,480.69 vs 779 × $25 = $19,475; per-contract hedge M5 100 ... H7 95 (total 779). Decompounding a 3M future at 95.705 (4.295% for 3m) to an overnight rate assuming a constant rate gives about 4.2725%.
Futures prices used here are finer than tradeable ticks; the dealer pays part of the bid/offer out of the swap edge.

## 8. GBP MPC step curve, 21-Nov-2022 (Deriscope, Feb 2024; ICAP data)
Inputs: stub to the first MPC 2.9275% and 7 forward MPC-dated SONIA OIS: 15Dec22-2Feb23 3.511, 2Feb-23Mar 3.99, 23Mar-11May 4.362, 11May-22Jun 4.544, 22Jun-3Aug 4.5885, 3Aug-21Sep 4.605, 21Sep-2Nov23 4.6045.
Settings that matter: backward-flat interpolation on forwards with nodes at meeting dates; SONIA settle 0 days, payment lag 0; term-structure day count ACT/365F; daily forwards read with simple compounding ACT/365F.
Result: overnight 2.9248% to 14-Dec-2022, 3.5029% from 15-Dec (+57.81bp), later steps about 3.99, 4.35, 4.54, 4.58, 4.60%.
Consistency: implied spot OIS minus market spot (1w..11m) 0.07, 0.05, 0.24, 0.17, -0.74, 0.41, 0.42, 0.50, 0.16, 0.58, 0.53, 0.48, 0.44, 0.12bp ("the market trades forward swaps at a premium relative to spot swaps"; the two curves agree within 1bp).
Market spot OIS: 1m 3.0424, 3m 3.461375, 6m 3.876385, 11m 4.2569.

## 9. Step curve with CB01 risk: RBA, 10-Apr-2007 (Lehman Brothers, The Short-End of the Curve, Jul 2007)
Policy 6.25%. Step curve: 2-May 6.36 (+11), 6-Jun 6.43 (+7), 4-Jul 6.43 (0), 8-Aug 6.47 (+4), 15-Sep 6.49 (+2), 3-Oct 6.51 (+2); implied probability of a hike 44%, 28%, 0%, 16%, 8%, 8%.
DF-vs-meeting Jacobian diagonal 2.44, 1.61, 1.86, 1.31, 1.04, 1.54 (per AUD 1m). Paying a 1M OIS for a 2-May hike: +14bp if hike, -11bp if not. CB01 -AUD 11,134/bp → AUD 4.563bn of 1M OIS hedges it; the 1M OIS DV01 of -AUD 38,323 overstates the risk by 244% versus CB01.
Bucketing AUD 1bn of cash flow on 26-Jun-2007: traditional deposit/future/swap bucketing -19,736 vs step -14,781 (2-May -9,402; 6-Jun -5,379): the traditional method over-estimates risk in the deposit region.

## 10. ECB step curve regularised with flies, 31-Jan-2024 (Darbyshire, Coding Interest Rates, c.2024)
Effective dates 31 Jan, 2 Feb, 13 Mar, 17 Apr, 12 Jun, 24 Jul, 18 Sep, 23 Oct, 18 Dec 2024, 29 Jan 2025. Inputs: O/N 3.899; 1st policy period 3.904; 2nd 3.859; Mar IMM 3.692; Jun 3.215; Sep 2.725; Dec 2.370.
10 degrees of freedom vs 7 instruments, so add 3 flies (periods 3-4-5, 5-6-7, 7-8-9) priced 0bp with weights [1.0]×7 + [1e-8]×3. Log-linear ACT/360; converged in 6 iterations, objective 1.45e-15; the curve steps monotonically from ~3.9 (Feb 2024) to ~2.3 (early 2025). A 6-week central-bank delay costs a receiver ~14bp (3.701117 → 3.840582).

## 11. A 13-knot RFR curve under three interpolators (Darbyshire, PTIRD, 2022, Tables 6.1-6.2)
1-Jan-2022 inputs: 3M deposit 1.00%; IMM IRS 15-Mar-22 1.05%, 15-Jun-22 1.12%, 21-Sep-22 1.16%, 21-Dec-22 1.21%, 15-Mar-23 1.27%, 21-Jun-23 1.45%, 20-Sep-23 1.68%, 20-Dec-23 1.92%; IRS 3Y 1.68%, 5Y 2.10%, 7Y 2.20%, 10Y 2.07%.
Solved DFs (log-linear / log-cubic / mixed): 15-Mar-22 0.998028/0.998014/0.998028; 21-Sep-22 0.992409/0.992391/0.992409; 20-Dec-23 0.975832/0.975794/0.975832; 1-Jan-25 0.950978 (all); 1-Jan-27 0.900403/0.900403/0.900383; 1-Jan-29 0.857393/0.857432/0.857419; 1-Jan-32 0.814368/0.814484/0.814464.
All three reprice every input ("equally valid"). Overnight forwards: log-linear is a step function; log-cubic is smooth but over/undershoots around the 3Y-10Y knots; mixed is stepped in the IMM section and smooth after.
A SONIA curveset with 12 IMM futures plus par 5Y-50Y: unregularised log-linear swings O/N forwards ~±40%; with curvature constraints (weight 1e-4) LM converges in 13 iterations to smooth steps of ~1-2.7%; adding 8 quarter-end turns (-3bp quarterly, -5bp half/year-end) also takes 13 iterations.
Log-linear check: DFs 1.00 (1-Jan-22), 0.9975 (1-Apr-22), 0.9945 (1-Jul-22) give DF(15-Mar-22) = 0.99797174.

## 12. Turns
- Turn on a spline by composition (Darbyshire, CIR): turn curve plus spline (knots 4× 1-Dec-22, 21 Dec, 11 Jan, 4× 1-Feb-23) with 20d IRS at 2.01, 2.175, 2.35 solved in one solver (2 iterations, objective 7.06e-15): smooth ~2.0 → 2.4 with a -50bp year-end dip.
- Fading STIBOR-style turn: values [0, 0, -0.20, -0.04, 0, 0, 3.5, 3.7, 4.05], solved in one iteration; SEK 3M STIBOR year-end turns of 2021/22 appeared large in autumn and faded before January expiry.
- SONIA 2021 publications showed a negative premium of ~0.25-1bp on the day before each quarter end (PTIRD 2022). A 1d swap on 10bn starting 31-Mar-22 (analytic delta ~£2,740/bp): turn pair left 1,681.8 / right -1,021.8, net £2,703.6/bp.
- EUR turn-of-year (Ametrano & Bianchetti, 2013): Euribor1M 2007 +64bp, 2008 +22bp, end-semester 2008 +9bp; at 11-Dec-2012 ON turn 2013 +10.2bp, 2014 +8.5bp; 1M curve +1.8 / -1.6bp (~1/20 of ON); 3M +0.6 / -0.5bp (~1/3 of 1M). The ON FRA was negative in the 3M-12M window (min ~-1.8bp) and DFs were non-monotone.
- US quarter-end repo (Fed Board FEDS Notes, Jun 2025): SOFR-ON RRP +7bp Mar 2023 quarter-end, up to ~+25bp Sep 2024 and year-end 2024 (SOFR above IORB); sponsored reverse-repo quarter-end volume ~$25bn (2021Q1) → ~$290bn (2024Q3); composition effect ~2bp of the Dec 2024 move.
- SOFR index (NY Fed, base 1 on 2-Apr-2018): interest on USD 1mm 15-Sep-21 to 15-Dec-21 = 1,000,000 × (1.04235797/1.04227169 - 1) = USD 82.78.

## 13. Short-end deposit/futures consistency (Aikin, STIR Futures, 2nd ed., 2012)
Deposit forward: 9M 4.62% and 12M 4.66% (ACT/360): 12M earns 4.725, 9M 3.465, forward = 1.26/(103.465 × 90/360) = 4.87% vs future 95.15 (4.85%), value basis +0.02%.
EUR 28-Oct-2011 swap-DF curve (3M 0.995948, 1Y 0.983574, 5Y 0.902679, 10Y 0.763565) versus convexity-adjusted futures forwards: X1 1.535/1.362; Z1 1.400/1.582; H2 1.213/1.850 - "not much of a link". Stringing (compare strip zero with swap zero) still showed ~0.25% at 2y "due to term risk".
Stringing toy: Z1/H2/M2/U2 at 98.00 / 97.90 / 97.80 / 97.70 → strip zero 2.167% vs swap zero 2.564%: strip "appears cheap" in rate terms. Strip-vs-swap "arbitrage" is usually tenor basis plus forward-start mismatch.

## 14. Treasury par-curve fit quality (J.P. Morgan, The new and improved Treasury par curve model, Jul 2018; The (par) curves they are a-changin', Jul 2024)
Spline on the discount function, GC-repo anchored below 0.5y, 12 knots at on-the-run maturities and midpoints, yield-weighted objective `w_i = 1/(P_i D_i)`. Removing very-low-free-float bonds cut average RMSE from 3.8 to 2bp (std 0.66 → 0.21bp); 6 → 12 knots about -0.5bp; net -2.5bp (-65%). 0-2y bucket RMSE legacy 12.4/23.1 (last/avg) vs new 0.9/1.2bp.
Overfitting test: percent change in curvature after refitting with a N(20,5) shock on 5% of bonds; curvature jumps between 15 and 20 knots. Use for bond RV: [bond-rich-cheap-fitted-curve](../../bond-rich-cheap-fitted-curve/SKILL.md).

## 15. Futures-strip hedges of OIS and Treasuries (Huggins & Schaller 2022, Ch. 9)
An ideal 1y IMM receiver (1%, USD 100m, start 16-Jun-21) hedges with 102/102/101/101 SR3; the realistic 1y SOFR OIS (annual pay, ACT/360 both legs, 2-day delay) with 101 each, "likely to change when the curve is not flat and close to zero".
UST 1.5% Sep-30-2021 hedged on 2-Jan-2020 with SR3 Dec19-Sep21: +1bp → bond -USD 17,568 vs hedge +17,517; lots -101, -101, -100, -100, -100, -99, -99, -17 (total -717); the front SR3 has 0.8384 of full sensitivity.
