# Price discovery across venues: derivations and closed forms

Companion to [SKILL.md](../SKILL.md) section 5. Use when ONE security is quoted in several places (futures vs cash, swap vs bond, venue A vs venue B) and the question is which market first reflects new information. Prices here are mids or settlement snaps on a common clock; shocks are in price or bp units.

## 1. VMA, Cholesky, variance bounds (Hasbrouck, Empirical Market Microstructure, 2004)
- VAR in changes `dp_t = A_1 dp_{t-1} + ... + A_p dp_{t-p} + e_t`, `Var(e) = Omega`. Vector moving average by feeding unit shocks: `Theta_0 = I`, `Theta_h = sum_{j=1..min(h,p)} A_j Theta_{h-j}`. Judge a VAR through its impulse responses, never through single coefficients.
- Cumulative response of the price LEVEL to a shock: `Psi_k = sum_{h<=k} Theta_h`; long run `Psi = (I - sum A_j)^-1` (a VAR in differences of cointegrated prices only approximates this, so use a VECM, section 3).
- Cholesky: `Omega = F F'`, F lower triangular. 2x2: `F = [[s1, 0], [rho s2, s2 sqrt(1 - rho^2)]]`. The first variable is credited with the whole common (contemporaneous) component. Re-order and report the range.
- k-step forecast-error covariance is `sum_{j<k} Theta_j Omega Theta_j'`. The random-walk (permanent) variance is `Psi Omega Psi'` with `Psi = sum_j Theta_j`, which is NOT the same object (the k-step sum is a variance of a finite sum of shocks, the permanent variance is the variance of the infinite cumulated sum).
- MA(1) check: autocovariances `gamma_0, gamma_1` give `theta/(1+theta^2) = gamma_1/gamma_0`, take the root with `|theta| < 1`; `sigma_e^2 = gamma_0/(1+theta^2)`; permanent variance `(1+theta)^2 sigma_e^2 = gamma_0 + 2 gamma_1`. Bid-ask bounce: `gamma_0 = 1, gamma_1 = -0.2` gives `theta = -0.2087`, `sigma_e^2 = 0.958`, permanent variance 0.600 (the other root, -4.79, reproduces the autocovariances but not the shocks). Trade clustering (positive autocovariance): `gamma_0 = 0.2304, gamma_1 = 0.1024` gives `theta = 0.610`, `sigma_e^2 = 0.168` (Hasbrouck 2004).
- Incremental R2 / attribution with correlated regressors depends on entry order: all n! orderings (362,880 for n = 9) can be replaced by the 2^n subsets (512) to bound the contribution.

## 2. Information share (Hasbrouck 1995, external; Hasbrouck 2004)
Let `psi` be the common row of `Psi` (all rows equal when the markets share one efficient price), `Omega` the innovation covariance. Efficient-price variance `psi Omega psi'`. For an ordering with Cholesky factor F:

`IS_j = [(psi F)_j]^2 / (psi Omega psi')`, sum over j = 1.

- Diagonal Omega: `IS_j = psi_j^2 omega_jj / sum_k psi_k^2 omega_kk`, no ambiguity.
- Two markets, `Omega = [[s1^2, rho s1 s2], [rho s1 s2, s2^2]]`:
  - market 1 ordered first: `IS_1 = (psi_1 s1 + psi_2 rho s2)^2 / (psi Omega psi')` (upper bound of market 1)
  - market 2 ordered first: `IS_1 = psi_1^2 s1^2 (1 - rho^2) / (psi Omega psi')` (lower bound of market 1)
  - Example `psi = (0.5, 0.5)`, `s1 = s2 = 1`, `rho = 0.6`: `psi Omega psi' = 0.8`; bounds on market 1 are 0.20 and 0.80. At `rho = 0.6` the bounds (0.2 to 0.8) are too wide to name a leader.
- The bounds are wide when contemporaneous correlation is high. Sample on a finer clock (lower contemporaneous correlation) rather than reporting a midpoint.
- A noisier price (larger pricing noise) earns a lower share; the market with the more precise signal and the bigger permanent-component loading leads.

## 3. Cointegrated prices: VECM
Same security in two markets means `p1 - p2` is stationary (cointegrating vector `beta = (1, -1)'`). A VAR in differences omits the error-correction term and is misspecified. Use

`dp_t = alpha (beta' p_{t-1}) + sum_k Phi_k dp_{t-k} + e_t`, `z_t = p1_t - p2_t`, `dp1 = alpha_1 z`, `dp2 = alpha_2 z`.

- Sign: `alpha_1 < 0` means market 1 falls when it is above market 2 (it moves toward market 2); `alpha_2 > 0` means market 2 moves up toward market 1. A market with a small `|alpha|` barely adjusts, so it is the one that carries the information.
- Common-trend row (normalised to sum to 1): `psi = (alpha_2, -alpha_1) / (alpha_2 - alpha_1)`. Example `alpha = (-0.30, +0.10)`: `psi = (0.25, 0.75)`, so market 2 (the slow adjuster) carries 75% of the permanent component; feed this psi and the residual Omega to the information-share formula above.
- `alpha` and `beta` are identified only up to a rotation; the VMA, impulse responses and psi are invariant to that choice.
- **Threshold ECM**: when the gap sits inside the marginal trader's transaction-cost band there is no adjustment, so a linear VECM mixes "no arbitrage" and "arbitrage" regimes; estimate a threshold ECM or only use gaps beyond the cost bound.
- **Futures vs cash** `p_f = b p + c`: the carry `c` shifts at each roll and through time (convergence, declining carry), but is constant within a day. Estimate `c` day by day, model its determinants, or fit a step function; do not treat the raw basis as stationary around a constant (Hasbrouck 2004). Short samples cannot reliably test cointegration: assume the relationship from the economics.
- **Standard errors** of IS and IRFs when the delta method is unreliable: estimate per day, average, use the cross-day standard error (Hasbrouck 2004).

## 4. Why venues differ: stylised microstructure results (O'Hara, Market Microstructure Theory, 1995, Ch. 8)
These explain what the statistics can and cannot show; they are not estimators.
- **Order splitting** (Chowdhry and Nanda, as presented): a large uninformed order `d` is split across N venues with share proportional to `1/lambda_i` (price-impact coefficient), `k_i = c_i / sum_j c_j`, `c_i = 1/(2 lambda_i)`. A venue with half the impact takes twice the flow. Order-flow correlation across two venues `rho = 0.5 [1 + sigma_d^2/sigma^2]` (1 when only large discretionary traders exist, so the venues are near-identical).
- **Informativeness**: a variance ratio that is 1/2 for one venue (Kyle benchmark) and, as presented, rises with the number of venues when small fixed-flow traders are present; the share of discretionary large flow, `sigma_d^2/sigma^2`, caps it. Check against the source chapter before quoting a closed form.
- **Order splitting by small traders removes most clean multimarket results**: model it before concluding on price-discovery share.
- **Fragmentation does not automatically add liquidity**: an extra product (basket, future) can draw discretionary flow out of the existing market and raise adverse selection there (Subrahmanyam, as presented). Option volume has been found to lead the underlying (Easley, O'Hara, Srinivas 1993, cited in O'Hara 1995).
- **Cash-futures gap** (Kumar and Seppi, as presented): the gap is normal, converges to zero but not monotonically (information sets converge with a lag), and faster arbitrage widens bid-ask spreads in the short run. The mapping to cash-bond vs bond-future basis and futures vs swap gaps is an analogy, not a result from the book.
- **Depth-weighted mids can be pushed by queued orders** (a 3,000-lot offer behind 4,500 moved a depth-weighted mid from 98.0131 to 98.0121, Darbyshire 2022, Ex 19.3). Check queue depth before using a futures mid as the leader, and aggregated depth across venues can overstate liquidity (the same size is shown on several venues).

## 5. Practical protocol
1. Same clock, mids/settlements, roll-adjusted, sessions treated separately (drop each session's first change).
2. Test cointegration only if the economics allow it; otherwise assume it. Fit VECM, extract psi, report information-share bounds, then the lag-scan and Granger from SKILL.md on the error-corrected residuals.
3. Report the decision the result feeds: which leg to quote or execute first, which leg is the hedge driver.
4. Bounds that straddle 50% mean "no clear leader at this sampling frequency", not "equal".
