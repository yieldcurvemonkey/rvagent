# Formulas and derivations (carry and roll-down)

Sign: receiver / long positive. Rates in the units stated. Section numbers refer to [SKILL.md](../SKILL.md).

## 1. Swap carry and roll under the two scenarios
Notation: S(T) spot par rate to T; F(h, n) forward par rate starting h for tenor n; A(.) annuity (DV01 per unit notional per
unit rate). Spot swap over horizon h:

| Scenario | carry (certain) | roll (mark of the aged swap) | total |
|---|---|---|---|
| Curve unchanged | F(h, T-h) - S(T) | S(T) - S(T-h) | F(h, T-h) - S(T-h) |
| Forwards realised | F(h, T-h) - S(T) | S(T) - F(h, T-h) | 0 |

The certain carry is the same in both rows; only the assumption about the aged swap's rate differs (frozen spot curve gives S(T-h); realised forwards give
F(h, T-h)). Under forwards realised the mark-to-market loss of a receiver exactly offsets the carry, so expected P&L of a mid-market swap is zero (QFSE, Carry
calculation on an interest rate swap, Aug 2017; MtM of interest rate swap if forward rates are realised, May 2023). A source that quotes carry as the fixed rate
minus the first float fixing (payer: S1 - S5 in a 5y example) is quoting per unit notional rather than per forward DV01; the two agree after scaling.

Identity: the forward value of the residual swap over the horizon = minus the carry over that horizon (QFSE, MtM of interest rate swap if
forward rates are realised, May 2023). Pure carry = deterministic cash-flow component (a future has zero pure carry); broad carry =
expected return if the world is unchanged, including convergence, roll-down and delivery-option decay (QFSE futures carry, Feb 2018).

**Fixing form.** Float PV of the aged swap = fix x alpha x DF(h) + F x A_fwd, and S x A(T) = same value with A(T) = alpha DF(h) + A_fwd, so

```
(F - S) x A_fwd = (S - fix) x alpha x DF(h)    =>    carry_running = DF(h) (S - fix) alpha / A_fwd
```
Upfront carry over 6m (receive 5y vs 6m term index) = (S - L6m) x DV01(6m) with DV01(6m) = 0.5 x DF(0,6m); running carry = upfront /
DV01(6m-forward 4.5y swap) = F(6m,4.5y) - S(5y). The note formula without the 0.5 gives about 16bp instead of 7.9bp (QFSE, Carry
Roll Calculation for Interest Rate Swaps in Nordea Note, Jun 2024). The approximation carry ~ F(h, T-h) - S(T) with a single fixing
is exact only for h equal to the fixing period.

**Roll operation on a curve** (Darbyshire, Coding Interest Rates, ch. 6): a forward roll by j days assigns curve values to dates offset by j,
keeps the first node date, forward-fills the first j days at the overnight rate; DF curves are multiplied by 1/(1 + dbar r0)^j, spline knots
shift by j and a new initial node (date, 1.0) is inserted. No recalibration. Roll is distributive over composite curves.

## 2. Forward and zero-curve relations (Ilmanen, Understanding the Yield Curve Pts 1-2, 1995)
- Break-even: (1+s_n)^n / (1+f_{1,n})^{n-1} = 1 + s_1. Forward one year ahead: 1 + f_{n-1,n} = (1+s_n)^n / (1+s_{n-1})^{n-1}.
- Approximations (continuous compounding exact): f_{m,n} ~ (n s_n - m s_m)/(n - m); f_{n-1,n} ~ s_n + (n-1)(s_n - s_{n-1}) = yield + roll x horizon duration.
- Rolling yield of a zero = f_{n-1,n}; unchanged curve means the n-year zero returns f_{n-1,n}; forwards realised means every zero returns s_1.
- Break-even change in the constant-maturity yield: Delta f_{n-1} = f_{1,n} - s_{n-1} = (f_{1,n} - s_n) + (s_n - s_{n-1}) = carry component + rolldown component.
- Forward-spot premium FSP_n = f_{n-1,n} - s_1 ~ (n-1) E(Delta s_{n-1}) + BRP_n; for a linear spot curve FSP = 2 x the term spread.
- Forward curve lies above spot while spot slopes up, crosses spot from above at the spot peak and magnifies slope variation.
- Flattener break-even over a year needs the rolling-yield (1y-forward) curvature, not only the spot curvature. Concave curve: every
  duration-neutral flattener has negative carry; more concavity = more negative carry and more implied flattening.
- Evidence (US 1970-94, horizons 3m/6m/2y/3y/4y/5y): corr(FSP, next change in s) 0.12/0.05/-0.05/-0.07/-0.11/-0.08; corr(FSP, realised
  BRP) 0.37/0.22/0.17/0.17/0.19/0.15. Steep curves predict excess return, not higher long yields.

## 3. Holding-period return and the five-term expected return (Ilmanen, Pt 6, Nov 1995)
Zero-coupon one-period return: h_n = f_{n-1,n} + (1 + f/100)[-Dur_{n-1} Delta s_{n-1} + 0.5 Cx_{n-1} (Delta s_{n-1})^2], with Delta s the change in
the **constant-maturity** (n-1)-year rate. Expected return =
1. yield income (coupon, accrual, pull to par);
2. + rolldown = rolling yield (unchanged-curve, zero-vol return);
3. + value of convexity = 0.5 x convexity at horizon x (bp vol over horizon)^2 x (1 + rolling yield/100);
4. + duration impact = -duration at horizon x expected change in the constant-maturity rate x (1 + rolling yield/100);
5. + local rich/cheap = financing advantage (3m GC minus 3m special term repo)/4 + (OTR yield - model par yield)/4 + expected cheapening.
26 Sep 1995, 3m (bill/3y/10y/barbell 0.53 x 10y + 0.47 x 3m): yield income 1.349/1.474/1.568/1.425; rolldown 0/0.065/0.108/0.038; value of convexity
0/0.014/0.082/0.029; duration impact 0/-0.056/-0.284/-0.099; local rich/cheap -0.015/-0.039/+0.025/-0.002; total 1.334/1.456/1.499/1.391.
Rich on-the-runs tend to lose richness rather than roll down. Long-duration decompositions are imprecise: a couple of bp of yield error x duration swamps
the premium.

Continuous form (Tuckman and Serrat, ch. 8): dP/P = f(T) dt - D dr + 0.5 C sigma^2 dt; with a risk premium E[dP/P] = r0 dt + lambda D dt and
Sharpe = lambda / sigma (lambda 10bp/yr per year of duration, sigma 100bp/yr gives 10%). OAS form: dP = (r0 + OAS) P dt + (dP/dr)(dr - E[dr]) + (dP/dOAS) dOAS; a
cheap bond bought, factor-hedged and financed at r0 earns OAS plus convergence P&L.

## 4. Bond forward, implied repo and basis
- Proceeds method (Darbyshire, Coding Interest Rates, ch. 10): P_t = P_0 (1 + r d_t) - sum c_i (1 + r d_i); implied repo r = (P_t - P_0 + sum c_i)/(P_0 d_t - sum c_i d_i).
  Compounded: P_t = P_0 (1 + rbar dbar)^n_t - sum c_i (1 + rbar dbar)^n_i. Proceeds usually suffices; net basis uses the compounded form.
- Tuckman (11.1-11.3): full forward = full spot x (1 + repo x days/360); with one coupon, [full spot x (1 + repo x d1/360) - coupon] x (1 + repo x d2/360). Forward
  yield = yield that discounts forward cash flows to the full forward price; spot yield is a weighted mix of the low repo and the higher forward yield.
- IRR = (Invoice/Purchase - 1) x 360/n; with one coupon IRR = (Invoice + C/2 - Purchase) x 360 / (Purchase x n - C/2 x n2) (Burghardt 2005).
- Basis net of carry (BNOC) subtracts pure carry (coupon - repo); a forward bond vs a future for the same date nets out slide and leaves CTD/delivery-option
  exposure. Overnight repo leaves a stub rate exposure of about a 3m duration position (QFSE, Carry/slide on Treasury CTD basis position, Aug 2023).
- Futures convergence repo: CTD term repo (to last delivery if carry positive, first if negative) gives pure carry and ignores the switch option; CTD implied repo
  includes futures rich/cheap. If the CTD changes the calculation is meaningless (QFSE, Feb 2018).
- STIR pack yield = prod_{i=1..4}(1 + (100 - P_i)% x 0.25) - 1; bundle yield = [prod_{i=1..4N}(1 + IFR_i x 0.25)]^(1/N) - 1; not comparable to bond or
  swap yields (Aikin, STIR Futures, 2nd ed., 2012).

## 5. Linker carry (Duering 2021 ch. 23; BofA Global inflation-linked primer, Jul 2025)
Real forward price P^_f = (R_0/R_f) P^_0/Df, with R_f = (1 + DCF i) R_0 and Df = 1/(1 + r DCF): P^_f = P^_0 (1 + r DCF)/(1 + DCF i) ~ P^_0 (1 + (r - i) DCF).
Cash method: dirty cash = (real clean + real accrued) x settlement index ratio; forward cash = dirty cash x (1 + term repo)^t - forward value of interim coupons
(coupon x index ratio on pay date, carried at repo); forward real dirty = forward cash / forward index ratio; subtract forward real accrued; solve the forward real
yield; carry = forward real yield minus spot real yield; repeat for the nominal comparator for breakeven carry. Short linkers are dominated by index carry.

## 6. Option and package carry (aged-price method; Nomura, Derivative Focus, 19 Jun 2014)
Carry = option repriced with 3m less to expiry (underlying rolled to the shorter contract) minus today's price, per leg; package carry = long leg minus short leg;
carry % = package carry / package price. Non-linear in time: quote several horizons and to expiry. Example (Euribor conditional bull flattener): long leg 18.00 -> 18.82
aged (+0.82), short leg 2.50 -> 1.53 (-0.97), package carry 1.79 ticks/3m = 11.6% of the 15.5-tick price; the 40bp forward spread ages into a 11.7bp spot spread.
Static roll-up (Bassman, The Positive Carry Hedge: A Reprise, 8 Dec 2010): price a fixed-strike payer across expiries on today's surface; if the shorter expiry costs more
than today's longer expiry the option rolls up. Needs a twisted forward curve plus an inverted vol surface (Dec 2010: 6% payer 4y 344bp rolling to 3y 246bp is the
reverse case; the chosen 10y x 10y payer at 433bp rolled to 459bp, +26bp, over three years).

## 7. Second-order Sharpe (Darbyshire 2022, ch. 22-23)
Ex-ante Sharpe theta = E[P]/sqrt(Var[P]), no risk-free asset, holding-period horizon. First order: E[P] = S'mu, Var[P] = S'QS. Second order: E[P] = S'mu + 0.5 tr(GQ) + 0.5 mu'G mu;
Var[P] = S'QS + 0.5 tr(GQGQ) + mu'GQG mu + 2 S'QG mu (normal moves, symmetric G). Gamma of a forward swap h x n (annual forwards): simple G ~ -(h+i) S/10,000 with h, i the first and last annual payment times (5y5y: 6 and 10, so 16);
DF-weighted: G = -(S/10,000) sum_j 2j A_j/A over the annual forwards. 5y5y with delta $50,000 pv01: G ~ -$80 pv01/bp (difference under 0.5%). Align the vol window with the horizon; the
smile makes short gamma costlier than presumed.

## 8. Curve-implied breakeven (JPM, An option by any other name, 3 Feb 2017; JPM 9 Feb 2018)
A PVBP-weighted flattener is long curve gamma and carries negatively like option premium. 1-year breakeven = minimum parallel shift that offsets the carry cost of a 1y forward
flattener held to spot. Curve-implied vol: assume a normal terminal distribution of parallel shifts centred on zero and solve for the sigma that makes the expected payoff zero. If it
is below the ATM forward swaption vol the curve is the cheaper gamma. Attribution: carry = ex-ante spot vs forward; curve = change of spot curve; convexity = remainder. Gate on
small duration differences between legs (breakeven vol explodes as the duration difference approaches zero) and compare rates (carry/yr vs theta/yr) at matched gamma and horizon,
not carry against straddle premium. Full treatment: [vol-convexity-and-long-end](../../vol-convexity-and-long-end/SKILL.md).

## 9. Cash balance and funding (Darbyshire 2022, s. 5.1)
Any derivative with initial PV zero has an expected final cash balance of zero, but interim balances are not zero: a 5y semi-semi receiver at par on an upward curve receives early,
pays late and has a hump-shaped balance returning to 0 at 5y. The funding rate on that balance is a cost (uncollateralised: borrow and lend rates differ, so price depends on direction).
Count it with IM, capital and gamma hedging as user-specific cost of carry: [fi-collateral-csa-and-xva](../../fi-collateral-csa-and-xva/SKILL.md).
