# Fly weighting methods: derivations, formulas, comparisons

Conventions as in [SKILL.md](../SKILL.md): legs (A, B, C) short wing / belly / long wing, risk (DV01) weights for the
receive-belly package, belly = 2 unless stated, `fly = 2*y_B - y_A - y_C` in bp. Every formula below is implemented or
checked in [`scripts/fly_weights.py`](../scripts/fly_weights.py) unless marked "text only".

## 1. Sizing principle and the equal-risk family
- n legs need n equations (Duering, Fixed Income Trading and Risk Management, 2021, Ch.31). One equation sets size in risk,
  `R = N*PVBP`. The other n-1 hedge the n-leg trade against every trade with up to n-1 legs: a fly is hedged against
  outright and slope; if you want slope exposure, put it on as a separate trade.
- **50/50 (equal-risk)**: `N_B*PVBP_B = -(N_A*PVBP_A + N_C*PVBP_C)` and `N_A*PVBP_A = N_C*PVBP_C`. Equivalent to a
  steepener plus a flattener of equal risk sharing the belly split evenly. Clarus sizing: agree the belly notional; wing
  notional `N_A = [D_B/D_A] * N_B/2` (D = DV01 per unit notional). Legs are set at market (NPV 0) to avoid convexity from
  off-market coupons; agree the belly rate plus one tenor spread, imply the other wing from the fly price
  `S_A = 2*S_B - S_C - P` (Clarus, Mechanics and Definitions of Spread and Butterfly Swap Packages, 14 Oct 2014).
- **Maturity-weighted** (text and script `w_maturity`): `(m_B - m_A)*N_A*PVBP_A = (m_C - m_B)*N_C*PVBP_C`, i.e. assumes
  linear steepening, more risk on the wing nearer the belly. Very uneven weights behave like a steepener ("rare to see a
  recommendation like a 2Y-4Y-30Y butterfly").
- **Condor** (+1,-1,-1,+1 in risk): `N_1 PVBP_1 = -N_4 PVBP_4`, `N_2 PVBP_2 = -N_3 PVBP_3`, `N_1 PVBP_1 = -N_2 PVBP_2`.
  Interbank it is executed as a spread of spreads. **Pascal** (-1,+3,-3,+1) = spread of two flies (Darbyshire, Pricing and
  Trading Interest Rate Derivatives, 3rd ed., 2022).
- **Vol-curve-driven wing/belly ratio**: if 2y/5y/10y normal vols are 100/100/80bp the hedge needs
  `DV01_2 + 0.8*DV01_10 = DV01_5`, so the wings carry more DV01 than the belly because the 10y is less volatile; a more
  humped vol curve puts a larger fraction on the wings. A rising wing/belly DV01 ratio = rising intermediate-term
  uncertainty (Lehman, Tuckman, Macro-Awareness in Relative Value Trading, Oct 2003).
- Duration is not the hedge ratio: `HR = (PVBP_t/PVBP_h) * B_t` with yield beta `B_t = dY_t/dY_h`
  (Salomon, Kopprasch, Understanding Duration and Volatility, Sep 1985). BPV-neutral flies (1-2-3, 2-5-7 ...) only re-mix the
  same PCs: a 1-3-5 fly "may mix" ~70/25/5% of PC1/PC2/PC3, a 2-7-10 fly ~80/10/10% (Huggins and Schaller, 2024).

## 2. Regression weights
**Construction A (fly on belly and slope; script `w_regression`).** `d(fly) = a + b1*d(slope) + b2*d(y_B)`, `slope = y_C - y_A`.
`fly - b1*slope - b2*y_B = (2-b2) y_B - (1-b1) y_A - (1+b1) y_C`, so
`w = (-(1-b1), 2-b2, -(1+b1))`. Under the opposite slope convention (short minus long) the signs of b1 flip: verify on data.
Rescale the belly to 2. OLS on changes without intercept is the usual form (QFSE, How to adjust butterfly 2s5s10s swaps
trade for directionality?, 2018/2021).

**Construction B (belly on wings; script `w_belly_on_wings`).** `d(y_B) = a + b_A d(y_A) + b_C d(y_C)`; risk weights
`(-b_A, 1, -b_C)`. Tuckman's 10s20s30s form: `F_10 = -F_20*(DV01_20/DV01_10)*b_10`, `F_30 = -F_20*(DV01_20/DV01_30)*b_30`;
the risk weights equal the betas, and they sum above 100% whenever a joint 1bp wing move moves the belly by more than 1bp
(only under parallel shifts do they sum to 100%). OLS is the min-variance hedge: `b = sigma_xy/sigma_x^2`,
`DV01_x = -b*DV01_y`, hedged variance `DV01_y^2 sigma_y^2 (1-rho^2) = DV01_y^2 sigma_eps^2` (Tuckman and Serrat, 4th ed., 2022,
Ch.6 and App. A6). A and B are different constructions: A neutralises slope and belly level; B minimises variance. Reverse
regressions (which leg is dependent) give different hedges unless |rho| = 1.

**Weight-space regression** (generic): `w = x - F b`, `b = (F'QF)^-1 F'Q x`, factors F = wing slope (-1,0,1) and belly
outright (0,1,0) give construction A. **Kalman**: random-walk betas for belly on wings (state noise ~1e-4, observation noise
~1e-3 as a starting point) and trade the pre-observation innovation z; avoids asserting 1:-2:1. A weighting fitted with no
window is in sample: use a rolling window and lag the weights by one day for P&L (`w[t-1] * dy[t]`).

**Dealing with collinearity** (Greene, Econometric Analysis, 8th ed., 2018): `Var[b_k] = s^2 / [(1-R_k^2) * S_kk]`,
`VIF = 1/(1-R_k^2)`, condition number = sqrt(max/min eigenvalue of X'X) after column scaling, > 20 is a problem. Symptoms:
estimates swing on small data changes; wrong signs; individually insignificant betas despite high joint significance.
Multi-leg rate regressions are collinear by construction.

## 3. PCA-based weights
**Exact solve with belly pinned** (QFSE, Construct a butterfly interest rate portfolio to eliminate PCA exposures, 2018-2020).
Fly = `w1*5Y - 7Y + w2*10Y`; require `S' E_{1,2} = 0` with S the risk array: `w1*e5,k + w2*e10,k = e7,k`, k = 1,2.
`D = e5,1*e10,2 - e5,2*e10,1`, `w1 = (e7,1*e10,2 - e7,2*e10,1)/D`, `w2 = (e5,1*e7,2 - e5,2*e7,1)/D`. Weights are in
PV01/risk terms, not notionals; D near zero explodes. With 3 instruments, neutralising PC1 and PC2 forces the trade to be a
multiple of PC3 (each neutralised PC removes one degree of freedom).

**With DV01s (script `w_pc_neutral`).** Loadings of PCA on yield changes: for belly N_B fixed, solve
`sum_i N_i*dv01_i*L_{k,i} = 0`, k = 1..n-1. Two-leg PC1: `n_5/n_10 = (BPV_10/BPV_5)*(e_1,10/e_1,5)`. "Hedge against all factors
of lower order than the one to which exposure is wanted"; PC4+ remains but is small. The same in matrix form (Duering 36.19-
36.21): solve `[[0,1,0],[D1 f11, D2 f12, D3 f13],[D1 f21, D2 f22, D3 f23]] (N1,N2,N3)' = (+-100, 0, 0)'`; sign of the belly by
rich/cheap. Recipe for any package: price it, shift the curve by each PC, compute the '01 to each PC, solve for hedge
notionals that zero them; if it holds for a 1-sd shift it holds for any size (Tuckman and Serrat). Residual PC3 exposure is
usually tiny; a fourth leg could neutralise it but "a relative value trader wants to pay only in rates believed too low".

**Worked Bund example** (Huggins and Schaller, 2nd ed., 2024, Box 3.1; entry 3 Oct 2011): weekly CM levels 4 Jan 2010 - 3 Oct 2011,
BPV 2Y 1.98 / 5Y 4.86 / 7Y 6.62, PC1 0.42/0.55/0.53, PC2 -0.84/-0.04/0.29. Solving PC1/PC2-neutral for (2Y, 7Y) per 1 unit of 5Y:
sell 0.80 2Y, sell 0.58 7Y (sell 80m 2Y, buy 100m 5Y, sell 58m 7Y). Extending to the 10Y added only 0.5bp residual, not
worth it. OU: expected profit 32bp, mean first passage 84 days, 84-day carry EUR 70k; authors concede the example was chosen.

**PC3 directly.** With three legs the PC3 loadings are the weights. USD swap 3y/5y/10y covariance (%) 7.1 8.9 5.5 / 8.9 14.0
13.0 / 5.5 13.0 17.5: PC1 0.37/0.64/0.68, PC2 0.68/0.31/-0.66, PC3 0.63/-0.70/0.32; divide by -0.70: (-0.90, 1, -0.46)
(bquanttrading, PCA Part II, 2015/16; credited to Salomon Smith Barney's PCA note). The five-year rolling window and 3rd-PC
rule are the Citi monitor method.

**PC1-only adjustments** (QFSE; Darbyshire Ch.22-24, ex. 23.1; base (-1,2,-1), PC1 = (0.660, 0.604, 0.447)):
| Method | Weights (body 2) | Note |
|---|---|---|
| Divide by loadings, `x_i/p_i` | (-0.91, 2, -1.35) | needs `sum x = 0`; PC1 = (-1,0,1) gives (1, inf, -1), PC1 = (-1,2,-1) gives (1,1,1) |
| Minimal change, `x - p(p'x)/(p'p)` | (-1.1002, 2, -1.0780) | author's preferred ("more transparent"); extends to more PCs by adding constraints |
| Min-VaR (belly 2) | (-1.48, 2, -0.38) | 2y over-weighted (more correlated with 5y), 10y under-weighted; lets you maximise belly size for a VaR target |
| Multivariate regression (construction A) | `(-(1-b1), 2-b2, -(1+b1))` | no intercept, daily changes |
Darbyshire's 4-bucket (2Y/5Y/10Y/30Y, PC1 = 0.65/0.59/0.44/0.20, S_ini = -1,2,-1,0) variants: naive PCA (-0.89, 1.94, -1.30, 0) with
PC risk 0/-1.88/1.90/3.44; minimal adjustment (-1.07, 1.94, -1.05, 0); CoVaR adjusting only the 5Y (-1.17, 1.94, -1.17, 0);
CoVaR adjusting 2Y and 10Y (-1.43, 1.94, -0.37, 0), lower VaR but "significantly more adjusted from the traditional 2s5s10s".
Residual attribution: with the minimally adjusted fly and a 10-day move, the P&L (about $3.70) equals S times the PC1
residual because the PC1 risk is zero: track PC-hedged flies by their residual P&L.

**Basis change (no information loss).** `[5Y; 2s10s; 2s5s10s] = A [2Y; 5Y; 10Y]`, `A = [[0,1,0],[-1,0,1],[-1,2,-1]]`,
`Q' = A Q A'`. Jacobian transforms of a risk ladder into flies (5y, 5s10s, 5s7s10s, 5s6s7s ...) give "exact and intuitive" P&L
explain; PCA is a basis change, not dimension reduction. Transformed instruments are correlated (5s6s7s ~5% with 5s10s): overlay
a VaR minimisation or build a hedged instrument (QFSE, Can PCA be used to transform a ladder of interest rate risk?, 2023).
**Flylets** (Musaelian, Nagarajan, Villani, 2016): `f_i = (0,...,a_i,b_i,c_i,...,0)` on three adjacent nodes with
`f_i . PC1 = f_i . PC2 = 0`, `||f_i|| = 1`; flylet exposures retain locality that PC-projected partial durations lose; keep PC and
flylet limits separate, after calm periods PC vols drift down and give false comfort.
**PC durations** (Golub and Tilman, Risk Management: Approaches for Fixed Income Markets, 2000): `pcdur_i = -(1/P)(P_up - P_down)/2`
per 1-sd shock; use at least 2 PCs (1-factor risk badly misstates duration-neutral curve trades).
**Risk-target weights** (Lopez de Prado, Advances in Financial Machine Learning, 2018): `w = W*beta`, `beta_n = sigma*sqrt(R_n/L_nn)`; the
default puts all risk in the smallest-eigenvalue PC.

## 4. Choice of inputs for PCA/covariance weights
- Covariance, not correlation, for curve hedges (the point is to adjust for vol differences along the curve); long windows
  react slowly, short windows give noisy matrices and frequent hedge changes (Duering).
- Levels vs changes: BQ runs PCA on levels, QFSE advises changes then translating to returns with duration, Huggins and
  Schaller use weekly levels of constant-maturity yields, Duering uses daily first differences. Default here: changes for
  hedge weights, levels residual only for ranking.
- Frequency: no standard; match the hedge horizon. Epps effect lowers correlation at higher frequency. Short horizons:
  idiosyncratic risk; long horizons: factor (level) risk. A fly with correlation ~-0.70 to the level beyond a one-month
  horizon but ~0 daily (BTP example) shows why the horizon matters: MVOU `dX = -Theta(X-mu)dt + S dB` gives horizon-dependent correlation, a linear combination is univariate
  OU iff its weights are orthogonal to one of Theta's eigenvectors.
- Window examples: 5y (Citi PCA flies), 6m and 3m (BofA tables), 3y shortened to 1y in fast markets (ING), 1y for EUR forwards
  (Credit Suisse), 126d regressions with 63d SD of betas (generic scanner).
- Sources of instability: eigenvector sign, ephemeral correlation between factors ("the main pitfall of PCA"), regime change (pre-GFC
  hump vs ZLB shapes), characteristic PCA-basis drift of ~2 years (Burton, Dektor, Wheeler, c.2008).

## 5. Cash-and-duration-neutral (bonds)
Weights in market value with belly MV = 1: `MV_A + MV_C = -1`, `D_A MV_A + D_C MV_C = -D_B`. For durations 2/5/10:
MV = (-0.625, 1, -0.375) (script `w_cash_duration`). Cash neutrality adds a constraint, so equal-risk wings are generally not
available (3 equations for 3 weights). Published: 0.53 x 10y par + 0.47 x 3m bill vs a 3y par bullet, duration 2.706 vs 2.708
(Salomon, Ilmanen, Understanding the Yield Curve Part 6, Nov 1995). BofA reweights the UKTi 2032/36/47 fly daily to stay cash- and
duration-neutral (risk weights +43.8%/-100%/+56.2%), which turns it into a forward real flattener "selling the step" between
the 32-36 and 36-47 forwards (BofA, UK Rates Viewpoint, 5 Sep 2024).
Duration-neutral barbell-bullet P&L drivers: flattening of the longer spread, large parallel shifts (convexity), and the
yield give-up that grows with curve concavity. Convexity rises with cash-flow dispersion (duration roughly linear, convexity
roughly quadratic in term) but "convexity is not free" (Kopprasch; Ilmanen, Part 5).

## 6. Multi-instrument and statistical-search variants
- **Sparse mean-reverting baskets** (d'Aspremont, 2008/2011): penalised covariance selection splits the universe into
  clusters, then greedy/SDP search; mean-reversion lambda by number of legs: 2 -> 35, 3 -> 128, 4 -> 178, 5 -> 213, 6 -> 247.
  Best baskets are local flies (e.g. 3y/4y/5y weights -0.288/0.806/-0.517). Out of sample a 1bp bid-ask erased the profits.
- **Trader-model risk** (Darbyshire Ch.16): a par-only model's VaR-minimising trades all share a sign and only hedge
  directionality; a model of spreads and flies exposes independent RV risks. Example: a sub-micro 7s8s9s fly made ~40% of one
  day's P&L with no VaR contribution (a take-profit candidate).
- **Hedge-cost margins** (Darbyshire Ch.19): a risk-based margin LP needs a combination's margin strictly below the sum of its
  components' (2s10s < 2s5s + 5s10s) or the solution is ambiguous.
- **Fly = a P&L unit**: `fly = y5 - 0.45*y2 - 0.60*y10` (Tuckman 2003): a change from -7 to 0bp is a gain of 7bp x the 5y DV01 for
  selling 5s hedged with 45% of its DV01 in 2s and 60% in 10s. A two-factor model implies 34%/66% for 2s5s10s at fair value.

## 7. STIR futures flies (text)
Fly `(P1 - P2) - (P2 - P3) = P1 + P3 - 2*P2 = S1 - S2`, wings equidistant (3m, 6m or 1y); condor `(P1-P2) - (P3-P4) = S1 - S3`.
Width from outrights = sum of four leg widths (4 x 0.005 = 2 ticks), from spreads 1 tick. Fair level ~ aggregate of last traded
component prices; popular sequential 3m and 1y flies are less volatile than spreads but still directional around the body.
Examples: M2U2Z2 from outrights -0.015/0.005, from spreads -0.005/0.005; condor H2M2U2Z2 0.040/0.060, `B1 + B2 = 0.050 + 0.000 =
0.050 = S1 - S3 = 0.105 - 0.055` (Aikin, STIR Futures, 2nd ed., 2012). Four legs of fees: use sparingly to convert or exit
positions (a long calendar hit by flattening becomes a short fly by selling the preceding spread).
