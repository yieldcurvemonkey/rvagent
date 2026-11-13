# P&L explain: formulas and derivations

Companion to [SKILL.md](../SKILL.md). Sign convention throughout: S = P&L per +1bp rate move (S = -dv01_ccy for long
duration), dr in bp, gamma G positive for receivers / long bonds.

## 1. Return decompositions (bonds, swaps, packages)

**Realised, outright bond** (Salomon Brothers, Understanding the Yield Curve Part 5, Sep 1995):
`return = yield impact - Dur*dy + 0.5*Cx*dy^2 + residual`.
- Use *yield* as the first term when `dy` are bond-specific yield changes (they already include the rolldown change);
  use *rolling yield* when `dy` are constant-maturity changes.
- Barbell: yield impact market-value weighted; `dy` market-value x duration weighted; duration impact = `-Dur_horizon * dy`;
  convexity impact = `0.5*Cx_horizon*dy^2`. Monthly returns annualise x12, vols x sqrt(12).
- Percent contributions to the average return sum to 100%; volatility contributions do not (vols are not additive).
- Variance link: `Var(h) ~ Dur^2 Var(dy) ~ 100 Cx Var(dy)`, so for zeros the value of convexity is about `Var(returns)/200`,
  which also equals the arithmetic-minus-geometric mean gap `GM ~ AM - Var(h)/200`. Extra duration raises the arithmetic
  mean via convexity but the extra vol drags the geometric mean down.

**Ex ante, additive** (Salomon, Part 6, Nov 1995): yield income + rolldown = rolling yield; + value of convexity =
convexity-adjusted expected return; + duration impact of the view; + local rich/cheap (financing advantage, spread to
par curve, expected cheapening) = total expected return.
`h_n ~ f_{n-1,n} + (1 + f/100) * [ -Dur_{n-1}*ds + 0.5*Cx_{n-1}*ds^2 ]` using end-of-horizon duration and convexity and the
constant-maturity yield change. Expected: `E(h) ~ f + (1+f/100)[-Dur*E(ds) + 0.5*Cx*E(ds)^2]`. Rolling yield and YTM give
convexity no value, so they understate expected return for convex positions; add `0.5*Cx*sigma_bp^2` with bp (normal) vol,
and note the value of convexity is only as good as the vol forecast (the sample choice can more than double it).
Short-horizon realised returns are dominated by the duration impact; yield, rolldown and convexity are harvested slowly.

**Instantaneous (Ito)** (Tuckman & Serrat, 4th ed., 2022, eq. 8.15): `dP/P = f(T) dt - D dr + 0.5 C sigma^2 dt` (time
passage, duration x move, convexity x variance). Second-order price approximation `dP/P ~ -D dy + 0.5 C dy^2`; DV01 by
central difference (+/-1bp). Long convexity = long vol: it pays only if rates move enough and bleeds when flat.

**OAS attribution** (Tuckman, eq. 7.37): `dP = (r0 + OAS) P dt + (dP/dr)(dr - E[dr]) + (dP/dOAS) dOAS`: carry/roll-down,
factor change versus expectation, spread change. For RV: hedge the factor (`dP/dr = 0`), and expected return = OAS plus
convergence P&L; risk premia cancel once factor risk is hedged.

**IRS total return** (Macrosynergy, Interest rate swap returns: empirical lessons): market price change + roll-down +
fixed-versus-floating differential; price and roll together = change in the fixed-leg yield x modified duration.

## 2. Sequential repricing (bond or swap)

Order matters; each step holds later factors fixed (Tuckman, ch.3):
1. start price at its spread to the start-date benchmark curve;
2. reprice on the scenario ("unchanged rates") curve at start + horizon, same spread -> **carry-roll-down**;
3. reprice on the actual end curve, same spread -> **rates**;
4. reprice at the actual end spread (= market price) -> **spread**;
5. add cash flows received -> **cash carry**. Sum = gross return.

Scenarios: *realised forwards* (forward curve slides down; a T-year zero returns f(1), the short rate) vs *unchanged term
structure* (a T-year zero returns f(T)). Under realised forwards any bond earns the short rate plus its constant spread;
that is the benchmark against which carry and roll are measured. The forward-curve bond spread `s` solves
`price = sum CF / prod(1 + (f_i + s)/2)` (negative = rich; equals OAS with no embedded options).

Return conventions: gross uses full purchase price; net-of-financing subtracts repo interest on the borrowed fraction;
return on capital uses the posted haircut (2% capital = 50x leverage). Yield-to-maturity is realised only with
reinvestment at that yield: a 2.375% 2051 bought at yield 2.343% returns 1.778%/yr with 0% reinvestment and 3.207% at 5%.

## 3. Rolled-curve carry explain (swaps)

Build the T+0 curve from the T-1 quotes unchanged (each par tenor keeps its rate, maturity one day later) and reprice;
the change in accrued on both legs is carry, the rest of the time-driven change is roll-down. The alternative
"viewless shift" `D(T+0,t) = D(T-1,t)/D(T-1,T+0)` (forwards realised) double-counts realised forwards inside the
rate-change P&L unless an IR-time cross-gamma term is added (QF.SE carry-roll-down thread). Definitions: swap carry =
fixed rate versus first floating coupon (bp/day or bp/month; a forward-starting swap has zero carry); roll-down = fixed
rate versus the next shorter point on a frozen curve. Roll is not linear in horizon: compute 1m/3m/6m from the curve.
Roll-down of a multi-period swap = analytic-delta-weighted average of component roll-downs (3M roll-down of a 2Y swap =
(173/197) x 17bp + (24/197) x 5bp = 15.5bp; Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022).

**Opening curve** (Darbyshire sec 6.1.10): flawed = reuse yesterday's input prices (misaligned date schedules, IMM vs
rolling tenors treated inconsistently). Robust = hold forward rates constant, either by scaling every previous-close
discount factor by the DF of today's date (interpolation fluctuations go to market move) or by repricing each input
instrument on today's schedule from the previous curve (fluctuations go to overnight carry; preferred because it
isolates carry that market moves would swamp; matters most on an IMM roll or when an input is added or removed).
Curve-model disagreement is largest at local extrema and at the midpoint of convex/concave sections between knots:
be cautious calling such points rich or cheap.

## 4. Taylor and cross-gamma explain

`dP ~ S.dx + 0.5 dx' G dx`, with `dx` = moves in calibrating par instruments (Darbyshire, Coding Interest Rates, eq. 12.22).
Same-currency case: no scope for significant inaccuracy. Example (10Y EUR IRS paid, EUR 1mm, curve 3.5%): delta 841.37,
gamma -0.86; +10bp re-solved NPV 8,370.82; Taylor `841.37*10 + 0.5*100*(-0.86) = 8,370.70`.
- Daily moves: second-order explain is "very accurate"; each cross-gamma element's P&L can be separated; sum sub-grids
  (discount/forecast basis vs rate) for a meaningful measure. With a single self-discounted RFR curve only the rate/rate
  block remains (basis blocks stay relevant for legacy IBOR books).
- Cross-gamma is symmetric, order 1e-4 of first-order risk per element, grids grow quadratically and P&L with the square
  of the move: in volatile periods cross-gamma can dominate. Full partial gamma costs N^2: use parallel or PCA-factor
  gamma for routine runs. Single-number parallel gamma for a payer with delta `S` spanning annual periods `h..i`: `G ~ -(S/10,000)(h+i)`
  (simple; 5y5y has h=6, i=10, so `-16 x 50,000/10,000 = -80` per bp) or the DF-weighted `G = -(S/10,000) * sum_j 2j a_j`,
  `a_j = A_j / sum A_j` with `A_j = d_j v_j` (15.97 for 5y5y); the two differ by <0.5% at 5y5y and about 10% at longer
  tenors in high-rate regimes.
- Keep risk and market-move bases consistent (zero-coupon deposit vs IRS) or cross-gamma explain carries a systematic scaling error.
- Bump size: smaller than 1bp and rescale; forward difference is usually enough. Layered curvesets: layer-1 unreliability
  comes overwhelmingly from skew moves in higher layers.

**Risk-model design.** Mismatched interpolation, misaligned inputs, or missing foundation can give a hedged book whose
risk-model explain is zero yet loses: pay 100mm 2.5Y on a log-cubic curve with log-linear risk, hedged with 2Y and 3Y;
when 2Y and 3Y fall together relative to the rest, the model shows 0 and the official result is a loss. Delta ladders are
interpolator dependent; smooth splines smear risk across buckets. Risk **bleed** (off-grid trade hedged on-grid) shifts
bucket risk as time passes; show Total / New / Gamma / Open / Close(t-1) / Bleed per bucket and time large hedges to
dates where tenors align.

## 5. Moving an explain between risk models

Target `dP ~ S_curve.dr_curve ~ S_A.dr_A`. For a transform `J_{A->B}` (rows = B instruments):
- transformed risk `S*_B = J_{A->B} S_A`; pair it with transformed moves `dr*_B = (J_{A->B}^-1)' dr_A` (pseudo-inverse `J^+` if
  non-square) or reverse `dr*_B = J_{B->A}' dr_A`. Square invertible case: `S*_B . dr*_B = S_A' J' J^-T dr_A = S_A.dr_A`.
- The reverse route gives different estimates for non-lossless transforms; the pseudo-inverse is closer on average, not always.
- Transform complex -> simple only; never chain; avoid very different models. Validation: if `S_A.dr_A ~ S_B.dr_B` and
  transformed moves match real moves, the transformed risks are accurate.
- Par -> forward moves: the 10Y10Y move = `dr_20Y A_0Y20Y / A_10Y10Y - dr_10Y A_0Y10Y / A_10Y10Y`; forward curves are far more
  sensitive to small par moves.
- Cross-instrument sets (swaps -> bonds, futures): `dV/dr2 = (dr1/dr2) dV/dr1`; across sets the Jacobian is subjective,
  so use multilinear regression and watch collinearity (QF.SE, Projecting swap risk on bonds and futures, Oct 2024).
- Instrument-delta risk (bump and refit each curve-building instrument, map through the inverse Jacobian) gives the best
  explain for linear products; a single net DV01 hides basis risk (QF.SE, DV01 on LIBOR vs SOFR basis swaps, Dec 2020).

## 6. PC attribution details

`S~ = E'S`; P&L by PC = `S~_i h_i`, `h = E' dr` with raw moves. PC multipliers are uncorrelated with variance equal to the
eigenvalues; eigenvector signs are arbitrary (book `S~ = (-17, 166, 38, 263)` vs code `(17, -166, 38, 263)`). VaR split by
PC: `dP = sum S~_i sqrt(lambda_i) Z_i ~ N(0, sum S~_i^2 lambda_i)`. Run separate PCAs per risk type (outright vs basis)
because outright variance dominates. To track a PC-hedged trade, remove the PC1 component of the realised move: since PC1
risk is zero, `S.xi = S.dr` and the residual `xi` shows the RV part. Align signs across dates (Procrustes rotation) if PC
attribution must be stable; "ephemeral correlation between factors is the main pitfall of PCA" (Huggins & Schaller, 2024).
k-factor residual ~ (k+1)-th factor x its loading when eigenvalues fall fast. A PCA-residual signal needs real covariance
(9 days is not), a non-trivial neglected-PC share (PC3+PC4 were 24% in one example) and a residual outside normal daily
ranges.

## 7. Option, straddle and convexity packages

- Delta-hedged option: `pnl = theta*dt + V*dvol + 0.5*Gamma*dr^2` (Citi, Holistic Approach to Convexity, Jun 2022; the deck
  prints the vega term as "V x dr", a typo). Straddle with funding: Convexity/rates, Vega, Theta, Funding; "Convexity minus
  (Theta + Funding)" is the realised-versus-implied verdict (Nordea, Bonds & bold, Nov 2021).
- Ex-ante average `0.5 Gamma S^2 (sigma_r^2 - sigma_i^2) dt`; ex-post daily `0.5 Gamma S^2 ((dS/S)^2 - sigma_i^2 dt)`
  (lognormal form). In normal (bp) vol, with Gamma in ccy per bp^2: `0.5 Gamma (dr_bp^2 - sigma_n^2 dt)`, `dt` in years. Use
  realised squared returns per period, not averages; the two forms agree only in aggregate (QF.SE, Delta hedge value formula, Mar 2017).
- Realised gamma edge = curve roll + curve gamma + option theta + option gamma; other = slope + vega + hedge residue + costs.
  Per-trade report: ex-ante side, `sigma_BE`, `sigma_imp`, score, realised effective curve vol and underlying vol at the hedge
  interval, realised gamma versus forecast `B*days/252`. Record the recovered/true bias factor next to every `sigma_BE`
  (a 5% bias is about 4.5 vol, as large as the whole edge on fairly priced pairs).
- Known-answer tests for an explain engine (Internal forward-curve vs straddle backtest spec v0.4, 23 Oct 2026): flat strip and
  zero moves gives curve P&L 0 and option P&L = theta; Bachelier Monte Carlo with daily hedging, `sigma_real = sigma_imp` gives
  mean P&L ~ 0 and `2*sigma_imp` gives `0.5 Gamma (sigma_r^2 - sigma_i^2)`; side symmetry to 1e-9 in every bucket. Mutation
  test: flip an option sign or drop a factor 2 and confirm the tests fail before trusting the suite.
- Roll-down strategies are short vol / long theta; first-order "roll-down / vol of spread" ratio matrices overstate Sharpe
  (pay 10Y20Y / receive 2Y3Y: +0.25 first order, -0.01 with gamma). Avoid them; use second-order expected Sharpe.

## 8. Daily balance-sheet ledger (new / market / funding)

Darbyshire, ch.5, alpha = overnight rate. Opening: `A1` = previous PV, `A2 = -A1` cash. Scheduled: `B1 = alpha*A2`
interest, `B2` cashflows, `B3 = -B2`. Valuation: `C1 ~ -B1` overnight carry, `C2` market-move PV change. New: `D1` PV of
contracts acquired/disposed, `D2` cash for it, `D3` other cost-of-carry. Closing: `E1 = A1+B3+C1+C2+D1`, `E2 = A2+B1+B2+D2`,
`E3 = -(E1+E2)+D3` (P&L transferred out), `E4 = E2+E3`. **P&L statement**: `F1 = B1+C1` funding inconsistency, `F2 = C2` market
moves, `F3 = D1+D2+D3` new activity, `G1 = F1+F2+F3 = -E3`. Zero-PV derivatives realise zero at maturity only if forecast
floating rates publish as predicted and the DFs used are attained on real cash balances; the cash-balance profile of a zero-PV
receiver in an upward curve is hump-shaped, and its funding rate matters.
Valuing against a benchmark CSA (local currency, zero threshold, daily, bilateral, remunerated at the RFR) separates
CSA risk and P&L from market risk; CVA / FVA lines sit outside market P&L.

## 9. Risk attribution next to P&L attribution

- CoVaR `c = sqrt(S'QS)` with Q the covariance of bp *changes*; VaR_5% = 1.644c, VaR_1% = 2.326c. Aumann-Shapley allocation
  `c_alloc = (1/c) diag(S) Q S` sums to c; a negative allocation marks a diversifying bucket. Large P&L with ~0 VaR
  contribution is a take-profit candidate (Darbyshire, Ex 16.9, 16.12). Linear VaR ignores gamma: use short horizons.
- Contribution measures (BlackRock, Golub (ed.), BlackRock's Guide to Fixed-Income Risk Management, 2023): standalone
  `SAR = w*sqrt(diag V)` (ignores correlation); `CTR = w o Vw/sigma_p` (additive); factor `CTR_f = (B'w) o (Sigma B'w)/sigma_p`.
  Risk change through time: `dCTR = 0.5(Y1+Y2)(X2-X1)` (exposure change) `+ 0.5(X1+X2)(Y2-Y1)` (economy change), `Y = sigma*rho`.
  If risk rose because the PM added exposure ask them to cut; if vol/correlation rose the breach is passive.
- Risk-model validation: exceedance counts versus normal (about 5% beyond 2 sigma) and regress realised on forecast risk;
  ex-ante tracking error computed under perfect-correlation assumptions understates realised (0.61% versus 0.72%; Citi, House Views Aug 2026).
- Portfolio and timing attribution (Grinold & Kahn ch.17): attributed factor return = exposure(t) x factor return, remainder =
  specific selection; split active systematic return into average active beta x expected benchmark return, beta x surprise,
  and timing; test timing with up/down betas `(beta, beta + gamma)`, using a-priori forecast betas to avoid spurious correlation.
- Factor attribution and market-value Brinson can tell different stories (35bp allocation + 54bp selection versus +84bp
  corporate spreads, +18bp carry, -24.9bp idiosyncratic; Golub (ed.), 2023).
