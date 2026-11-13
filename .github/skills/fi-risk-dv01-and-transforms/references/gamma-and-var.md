# Convexity, gamma, cross-gamma, VaR-minimising and factor-neutral hedges (detail)

House signs: `S` = DV01 per bucket, positive = long duration. `dP ~ -S . dr + 0.5 dr' G dr` with `G_ij = d2P/dr_i dr_j`
(currency per bp^2); `G` is the same in either delta convention (receive fixed = positive gamma, pay fixed = negative).
A receiver's DV01 rises by about G per 1bp fall in rates.

## 1. Yield-based closed forms (semi-annual, fixed cash flows; Tuckman and Serrat, 4th ed., 2022)

| Instrument | DV01 (per 100 face, per bp) | D | C |
|---|---|---|---|
| zero | `T / (100 (1+y/2)^(2T+1))` | `T/(1+y/2)` | `T(T+0.5)/(1+y/2)^2` |
| par bond (c = 100y) | `(1/(100 y)) [1 - (1+y/2)^(-2T)]` | `(1/y)[1 - (1+y/2)^(-2T)]` | `(2/y^2)[1-(1+y/2)^(-2T)] - 2T/(y(1+y/2)^(2T+1))` |
| perpetuity | | `1/y` | |

- DV01 = P x D / 10,000 (P = full price per 100); position DV01 = face x DV01(per 100) / 100. Compute DV01 by a
  **central difference at +-1bp**, not 0/+1bp; DV01 is local. Convexity from the change in first derivatives at +-0.5bp.
- Second order: `dP/P ~ -D dy + 0.5 C dy^2`; correction for a 100bp move = `C / 2 / 10,000`. Duration is roughly linear in
  term and convexity roughly quadratic, so at equal duration more spread-out cash flows have more convexity: a 50/50
  5y + 15y zero pair (D 10) has convexity 130 vs 105 for a 10y zero (T(T+0.5) form; the source prints 127.5 from a 22.5 slip for the 5y).
- Rules of thumb at 2% yield (par): duration 10y 9.0, 20y 16.4, 30y 22.5, 40y 27.4; DV01 5y 0.047, 10y 0.09, 20y 0.16,
  30y 0.22, 40y 0.27. At 0.5%: 10y 9.7, 30y 27.8; at 5%: 10y 7.8, 30y 15.5. Higher coupon means lower duration but
  higher DV01 for a premium bond; higher yield lowers both.
- Worked example: NSC 4.10s of 2121 (DV01 0.241, convexity 1,101) for -100bp: duration only +24.1%; plus
  0.5 x 1,101 x (1%)^2 = 29.6%; actual 30.978% (price 130.898). A DV01-matched long $100mm NSC / short $121mm 1.625s-50
  profits on both sides, the net largest for big rallies (NSC +$30.96mm vs Treasury leg $27.7mm). Positive convexity
  means DV01 falls as rates rise; the long-convexity side is long volatility and "more convex positions tend to earn
  less over time" (not an arbitrage; see [vol-convexity-and-long-end](../../vol-convexity-and-long-end/SKILL.md)).
- Convexity value ~ 0.5 x C x sigma_bp^2 with bp (normal) vol; bp vol = relative vol x yield. Return vol = bp yield vol x
  duration, so duration overstates long-bond risk when the bp-vol term structure is inverted or humped (Salomon Brothers,
  Understanding the Yield Curve Part 5, Sep 1995 and Part 7, Feb 1996).
- Duration drift (BlackRock Guide, 2023): `drift = -dOAD/dr = OAC - OAD^2`. Non-callable government bonds always have
  positive drift (duration lengthens in a rally); a hedged book with positive drift must sell after rallies and buy after
  sell-offs, so such securities usually imply a carry give-up; callables/MBS usually have negative drift. Use drift to price
  the cost of rebalancing a hedge. Neutrality is instantaneous: it decays with ageing (DV01 falls) and with gamma
  (Düring, Fixed Income Trading and Risk Management, 2021).
- Equal-odds convexity asymmetry (Bund 3.25% Jul-2032, yield 2.197%): -25bp +6.36, +25bp -5.96; expected return with
  equal odds of +-100bp is +2.6%; a 500y zero would "earn" 7,320% - the equal-odds assumption fails; yield distributions
  must adjust (Huggins and Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).

## 2. Gamma of a swap (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, ch. 21-22)

- Receiving fixed has positive gamma, paying negative (IRS and ZCS); longer tenor and more forward start mean more gamma.
  Total gamma `D2P/Dr2 = sum_ij d2P/(dr_i dr_j)`.
- Two sources: (i) the level of rates (lower rates, higher DFs, amplified sensitivity); (ii) mark-to-market: an off-market
  trade embeds an annuity whose PV is itself rate-sensitive (receive 100mm 10y at 4% when the mid is 2%: DV01 99,000 vs
  90,000 at the money).
- **Simple single-figure gamma** for an IRS covering annual forwards h..i with DV01 S: `G ~ (h + i) x S / 10,000` per bp
  (receiver positive). 5y5y (h = 6, i = 10), S = 50,000: 16 x 50,000 / 10,000 = 80 per bp.
- **DF-weighted** (preferred): `A_j = d_j v_j`, `a_j = v_j / sum_{k=h..i} v_k`, forward-j gamma `2j S a_j / 10,000`,
  `G = (S/10,000) sum_{j=h..i} 2j A_j / A`. For the 5y5y: A_j 0.990/0.985/0.980/0.970/0.960 (sum 4.885) gives 79.8, under 0.5%
  from the simple figure; at longer tenors and higher rates they differ by about 10%. Both assume a parallel move; a
  non-parallel move needs the full grid plus scenario or Monte Carlo. A smile makes short gamma costlier than
  `0.5 G sigma^2` suggests.
- Worked second-order check (Darbyshire, Coding Interest Rates, Ex 12.2): paid 10y EUR IRS, 1mm at 3.5%: DV01 -841.37
  (payer), gamma -0.86 per bp^2; +10bp re-solved NPV 8,370.82 vs Taylor `841.37 x 10 + 0.5 x 100 x (-0.86)` = 8,370.70.
  "Very accurate" for daily moves; less so over months.
- Numerical gamma `[PV(r+e) - 2 PV(r) + PV(r-e)] / e` (delta change per bp as written; divide by e again for per bp^2); a
  full partial-gamma matrix costs O(N^2) revaluations, so use parallel or PCA-factor gamma. Forward-difference delta
  `S_i ~ dP(e)/e - 0.5 e G_ii` carries gamma; central cancels it "but gains little in practice and doubles the cost"; use a
  bump below 1bp and scale (not so small that machine precision bites). Forward-mode dual numbers give exact first and
  second derivatives (Dual2: Hessian = 2 x gamma-coefficient) and, at a bank, cut delta calculation 100-1,000x.
- Curve gamma: anchor one tenor (e.g. 5y), twist the wings -/+0.5bp with interpolation between; the P&L gives the
  steepener position as one number and the change in DV01 gives curve gamma. A 2s30s steepener of +100k DV01 with curve
  gamma -5k leaves +150k after a 10bp inversion (Quantitative Finance Stack Exchange, "How to measure Steepener/
  Flattener/Butterfly sensitivity?", Oct 2021).

## 3. Cross-gamma

- `d2P/(dr_i dr_j)` is symmetric. Single-currency kinds: delta/basis, inter-curve delta/delta, basis/basis; plus FX/
  delta and FX/basis for XCS and foreign-CSA trades. After the RFR transition a single RFR curve per currency negates the
  IBOR-era basis effects; cross-gamma remains from (a) off-market annuity effect (MTM), (b) cross-CSA (a GBP IRS under
  a USD cash CSA hedged by GBP-CSA trades: a USD 1mm-pv01 30y trade shows discounting risk of
  1mm x 30/(2 x 10,000) = 1,500 pv01 in each of three instruments, GBP 3M/OIS basis, GBP/USD XCS and USD 3M/OIS basis,
  with alternating signs, in the IBOR-era source), (c) FX (pay EUR 1bn 5y MTM XCS, spot
  1.20 -> 1.25: USD 50mm payment, discounting-basis risk about USD 25,000 pv01).
- **Grids**: each instrument's DV01 change for a 1bp move in any other; gamma on the diagonal. Positive cross-gamma is
  favourable when the two are positively correlated, unfavourable when negatively correlated. Grid size grows
  quadratically (6 risk types x 30 buckets = 180 x 180 = 32,400 elements per currency).
- **Aggregation**: (1) simple summation by risk type (optionally by <5y, 5-10y, >10y): quick, no relative-vol view; (2)
  PCA-weighted scenario summation: weight grid elements by PC1 x sd, **separate PCA per risk type** (a single PCA is
  dominated by outright variance), `dS_i = sum_j G_ij dx_j`.
- **Analytic cross-gamma from first-order risks**: "second order risks can be determined from a linear combination of the first
  order risks" provided those first-order risks are **forward zero-coupon** risks split into discounting, forecasting
  (non-compounded) and forecasting (compounded) - not par risks (transform par to forward zero first). Rules of thumb for
  discounting delta from PV `P`: IRS/annuity `P x tenor / (2 x 10,000)`; ZCS `P x tenor / 10,000`; forward-starting adds the
  forward tenor; discounting risk exists only for future net cash flows. A DF is never affected by rates after its own
  date. Single RFR curve: only the rate-rate block is needed (ZCS vs IRS convexity vanishes).
- Magnitude: cross-gamma is about 1e-4 of first-order risk per element, but P&L scales with the square of the move and
  the grid with maturity: "during periods of volatility cross-gamma can dominate some portfolios". Cross-gamma transforms
  between bases like `G*_B = J G_A J^T`.
- Consistency trap: forward zero-coupon deposit risks versus multi-period IRS risks differ by `beta_i ~ (1 + R_i/n)^(1-n)`;
  build the grid from IRS risks with ZC formulae unscaled and P&L explain shows "a regular small mismatch".
- **Hedge mismatches leave gamma**: hedging with a different product (swap vs STIR future, ZCS vs IRS, misaligned payment dates,
  cash vs physical swaption settlement, different CSAs) hedges delta not gamma; check grids or scenarios. "It is always more
  favourable to receive an IRS and sell a STIR future as a hedge" (futures imply higher rates) - the futures convexity
  adjustment is the upfront value of expected re-hedging P&L, heavily model-dependent. Example: a USD 1bn 30y IRS paying 5
  business days late: -0.03bp on the customised rate. See [stir-convexity-adjustment](../../stir-convexity-adjustment/SKILL.md)
  and [vol-gamma-vega-pnl](../../vol-gamma-vega-pnl/SKILL.md).
- Futures vs swaps (Credit Suisse, US Treasuries Futures Focus, 28 Sep 2009), DV01 / convexity: 15y swap 1,107/164; 25y
  1,531/342; 30y 1,684/432; classic bond future 1,331/112; ultra bond future 2,079/442. +-100bp DV01 change: 30y swap
  -22%/+29%; ultra future -18%/+24%; classic bond future -6%/+12%. Low conversion factors raise contract DV01 and convexity.

## 4. Invariant risk metrics (Musaelian, Nagarajan and Villani, PCA: invariant risk metrics, SSRN 2016)

In PC space `dPi = J'a + 0.5 a'Ha`, `J_j = dPi/dPC_j`, `H_ij = d2Pi/dPC_i dPC_j`. With iid N(0,1) PC moves
`E[dPi^2] = ||J||_2^2 + 0.5 ||H||_F^2 + 0.25 [Tr H]^2`: one rotation-invariant, aggregatable limit capping linear and
convexity risk. Fat tails (mixed normal, prob p, scale theta): factor `(1 + p(theta^2 - 1))` on the linear and
`(1 + p(theta^4 - 1))` on the convexity part (p = 10%, theta = 5: net risk x2 for swaps, x8 for straddles). Flylets
(basis orthogonal to PC1/PC2 on three adjacent nodes) keep locality that projecting off PCs loses; keep PC and flylet
measures separate. PC1/PC2-neutral books can hide large notional and residual risk, PC vols drift down after calm
periods (false comfort), and the in-sample variance identity fails out of sample.

## 5. VaR-style hedge optimisation (Darbyshire, 3rd ed., ch. 14-16, 21, 23-24)

Setup: `Q` = covariance of **daily bp changes** (never levels; >= 100 observations, default 250; horizon matched to
liquidation; one snap), `c = sqrt(S' Q S)` = 1-sd P&L ("CoVaR multiplier"). VaR(95) = 1.645 c, VaR(99) = 2.326 c; loss > c on
about 16% of days for zero-mean normal P&L; ES(2.5%) ~ VaR(1%) under normality (2.338 vs 2.326) and ES "is not practically useful
for IRD portfolios"; CoVaR is linear in S, so it ignores gamma/cross-gamma (use short horizons). Event days: daily 4bp sd, week with
Friday payrolls twice as volatile: variance 16 x 4 + 4 x 16 = 128, 95% bound 18.6bp. Covariance must be positive
definite; smoothing lowers VaR for books with oscillating bucket risk (inflated correlations).

- **Allocation** (Euler / Aumann-Shapley): `c_alloc = diag(S) Q S / c`, sums to c. A negative allocation means the bucket
  diversifies the book: do not cut it. Desk aggregation: Alpha c 336, Bravo c 291, collective 529 vs sum 627.
- **Single-instrument VaR-min trade** in bucket i: `t_i = -(Q S)_i / Q_ii`, `c_min = |S| sqrt(q11 - q12^2/q22)` for the two-bucket
  case (hedge `S_f = -S_0 q12/q22`). Only one single-instrument trade is valid at a time; doing several at full size can
  increase VaR - trade about 50% of each and re-run.
- **Multi-instrument (M of N buckets)**: `S_trade = -Q_hh^{-1} Q_h. S` (rows h of Q for the allowed buckets), post-trade
  strip in those buckets `x* = -Q_hh^{-1} Q_hb S_b`; code: `solve(Q[h,h], -Q[h,:] @ S)`. Always at least as good as any
  single trade. For a general hedge matrix `H` (columns = DV01 strips of one unit of each hedge): `n = -(H'QH)^-1 H'QS`
  (the script's `varmin_hedge`). Residual `c*^2 = (P - H)' Sigma (P - H)` (P = portfolio strip, H = hedge strip) also judges whether a bucket set is adequate;
  more instruments give a smaller residual.
- **Example (house sign; legacy IBOR-era buckets, technique unchanged)**: Darbyshire Ex 21.9, buckets (3M 10y, 3M 30y,
  3M/OIS 10y, 3M/OIS 30y), S = (+4,000, +18,000, +110,000, +290,000) (the source quotes the negatives), Q = [[30.3, 13.1,
  0.29, 0.16], [13.1, 8.41, 0.09, 0.10], [0.29, 0.09, 0.16, 0.07], [0.16, 0.10, 0.07, 0.05]]: c = 133,153. Trading only
  the two 3M buckets: pay 5,790 and 19,838 (post-trade strip -1,790 and -1,838 in the 3M buckets, house signs) cuts c by about 23% to
  101,958. Both numbers are checked by the script's selftest.
- **Reading the cut**: a swap par strip (2y/5y/10y/30y, DV01 -10,000/+2,500/+10,000/-4,000 in the source's paid-positive signs, covariance
  from nine daily changes; Darbyshire, 3rd ed., ch. 14-16). The printed rounded covariance does not reproduce the printed multiplier (c 16,402 recomputed vs
  16,174 printed), so rely on the ranking only: best single hedges that cut c by about 16% (2y), 8% (5y), 0.2% (10y) and
  4% (30y) (recomputed; the source prints 15.6/7.7/0.2/4.1), a 2y+10y pair cut more than 70%.
  If the best single hedge cuts only about 15%, the book is relative-value risk: use a trader model (spreads/flies), not outright hedges.
- Hedging directionality of an RV trade (same Q and PCs for every method; buckets 2y/5y/10y/30y, initial receive-belly
  fly S = (-1, +2, -1, 0), PC1 = (0.65, 0.59, 0.44, 0.20)): naive PCA-neutral (divide by loadings) S ~ (-0.89, +1.94, -1.30, 0);
  minimal-adjustment (minimal-norm change, 30y held) (-1.07, +1.94, -1.05, 0); CoVaR on 5y only: trade 5y -0.344; CoVaR on
  2y and 10y: trade (-0.476, 0, +0.616, 0); regression on PC1: (-1.07, +1.94, -1.04, 0). More hedge degrees of freedom lower
  VaR but move the trade further from its intended structure; track PC-hedged trades by residual P&L.
- Optimised portfolio hedges (Golub and Tilman, 2000): rates risk `IntRR = sqrt(krd' Sigma krd)`, tracking error
  `sqrt(dkrd' Sigma dkrd)`; objective = weighted IntRR + KRD-profile mismatch + transaction cost, with hard constraints (e.g.
  OAD = 0). $100mm 30y mortgage pass-through hedged with 2y/5y/10y/bond futures: IntRR 257 -> 75bp/yr; adding OTR Treasuries
  18bp/yr; constraining the long-bond future to 30 contracts 29bp. Exact multi-factor KRD hedges (BlackRock eq. 8.9) are
  "notoriously unstable", ignore transaction costs and can amplify omitted-factor risk; convexity-matching hedges are
  unstable and non-intuitive. "Hedging is not a purely scientific process."
- Overly responsive risk matrices or fixed VaR limits can force selling at the worst time; netting benefits vanish in
  stress; reset (fixing) risk is invisible to standard VaR and dominated by central-bank meeting dates.

## 6. PCA and factor-neutral hedge algebra

- Factor exposure of a ladder: `sum_k position_k (per bp) x loading_k`; neutralise each PC with one trade. Variance
  `Var = sum_p lambda_p^2 (u_p^x)^2` (Credit Suisse, PCA Unleashed, 24 Oct 2012).
- Two-factor hedge ratio of x with y, `min Var(x - g y)`: PC1 only `g = u1x/u1y` (blows up where PC1 loadings are near
  zero, e.g. the long end); PC1+PC2 `g = (u1x u1y l1^2 + u2x u2y l2^2) / ((u1y)^2 l1^2 + (u2y)^2 l2^2)`.
- PC1-neutral 5s10s: `n5/n10 = (BPV10/BPV5)(e_{1,10}/e_{1,5})`; Bund example 5y +1bp goes with 10y +0.87bp on PC1, so a
  BPV-neutral "hedge" may carry any exposure "or even the opposite". Fly neutral to PC1 and PC2 given `n5`:
  `(n2, n10)' = [[BPV2 e_12, BPV10 e_{1,10}], [BPV2 e_22, BPV10 e_{2,10}]]^-1 (-n5 BPV5 e_15, -n5 BPV5 e_25)'`.
- PCA-neutral fly on risk array S (5y w1, 7y -1, 10y w2): `w1 e_{5,k} + w2 e_{10,k} = e_{7,k}` for k = 1,2;
  `D = e_{5,1} e_{10,2} - e_{5,2} e_{10,1}`, `w1 = (e_{7,1} e_{10,2} - e_{7,2} e_{10,1})/D`,
  `w2 = (e_{5,1} e_{7,2} - e_{5,2} e_{7,1})/D` (verified numerically); express weights in PV01 not notional. Weights are
  unstable when D is near zero.
- Directionality hedge: divide the trade element-wise by PC1 loadings (works only if the risks sum to zero); the robust
  version is minimal-norm: `x = -(e e' / e'e) t`, i.e. `t + x = (I - e e'/e'e) t`, projection off PC1; each extra neutralised
  PC removes a degree of freedom (3 instruments PC1+PC2-neutral forces a pure PC3 position).
- Hedge "against all factors of lower order than the one to which exposure is wanted" (Huggins and Schaller, 2024);
  a 1-3-5 fly may be 70/25/5% PC1/2/3 and a 2-7-10 fly 80/10/10%; for curve hedges use covariance not correlation PCA, with
  a window trade-off (long reacts slowly, short gives volatile matrices and unwarranted hedge adjustments).
- Regression hedge ratios depend on the dependent variable unless |rho| = 1; PCA/orthogonal regression does not. Check a
  fly sold on curvature by regressing its P&L series on the PCs. Details in
  [curve-pca-factor-model](../../curve-pca-factor-model/SKILL.md) and
  [quant-regression-and-hedge-ratios](../../quant-regression-and-hedge-ratios/SKILL.md).
- **P&L in PC space**: for orthonormal E, PC risk = E'S, PC moves = E'dr, per-PC P&L = product (the covariant/contravariant
  rule of the main skill). Example: seven tenors 2y-30y, DV01 +10k, +30k, -5k, +20k, -10k, +20k, -60k, moves +1, -1, -1, -2, -3,
  -4, -5bp: P&L 195k in outright space and PC space (PC P&L 17.6, 108.9, 35.6, 7.2, -8.4, 9.4, 24.6). Truncating to 3 PCs left a
  large residual (PCs 4-7); a wrong method using rescaled (standardised-data) eigenvectors gave -131,025 - "report the
  residual" (Quantitative Finance Stack Exchange, "Attribute P&L to PCA vectors (swaps)", Jan 2022; source sign convention).
