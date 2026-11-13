# Multivariate OU and mean-reverting baskets

Detail for the "Multivariate" step of [SKILL.md](../SKILL.md). Code: `fit_mvou`, `spread_is_ou` in
[`scripts/ou_fit.py`](../scripts/ou_fit.py). Cointegration testing and sparse-basket search live in
[quant-cointegration](../../quant-cointegration/SKILL.md); this note covers the OU dynamics only.

## 1. Model

dX = -Theta (X - mu) dt + S dB, X in R^m (e.g. residuals of a 2y/5y/10y structure, or the first three curve PCs).
Theta = transition matrix, mu = long-run means, S S' = scatter. Scalar form (mu = 0, three variables):
dX_1 = (-theta_11 X_1 - theta_12 X_2 - theta_13 X_3) dt + S_11 dB_1 + S_12 dB_2 + S_13 dB_3.

- theta_12 > 0: X_1 is repelled by X_2; theta_12 < 0: attracted; theta_21 = 0: the interaction is one-way.
- Off-diagonal S: correlation through common shocks. Off-diagonal Theta: correlation through attraction, which is
  **horizon dependent** (it builds as the horizon lengthens). (Huggins and Schaller, Fixed Income RV Analysis, 2024, ch.1-5.)
- Deterministic path X_v = mu + exp(-Theta (v - t)) (X_t - mu); with A = exp(-Theta tau), X_{t+i tau} = A^i X_t. Converges
  if and only if every eigenvalue of Theta has positive real part. Half-life of mode i = ln 2 / Re(lambda_i). Matrix
  exponentials are eigen-decompositions, never element-wise: exp(A) = Q diag(exp(lambda_i)) Q^-1.
- Conditional law: Normal with mean mu + exp(-Theta (t-s)) (X_s - mu) and vec(Sigma_t) = (Theta (+) Theta)^-1 (I - exp(-(Theta (+) Theta)(t-s))) vec(S S'),
  Kronecker sum A (+) B = A (x) I + I (x) B, vec stacks columns. Unconditional covariance: vec^-1[(Theta (+) Theta)^-1 vec(S S')].

## 2. Estimation recipe

1. VAR(1) with constant on the demeaned-free levels: X_t = c + A X_{t-1} + e. A = exp(-Theta dt), so Theta = -logm(A)/dt
   (take the real part; a complex logm or an eigenvalue of A <= 0 means the VAR is not a valid OU: stop).
2. mu = (I - A)^-1 c. 3. Residual covariance Sigma_dt gives S S' via vec(S S') = (I - exp(-(Theta (+) Theta) dt))^-1 (Theta (+) Theta) vec(Sigma_dt).
4. Full MLE (sum of conditional log densities) has m means + m^2 Theta + m^2 S parameters (21 for m = 3). Initialise from
   steps 1-3 (the book initialises Theta by least squares on the one-lag coefficient matrix and S from the 1-day covariance).
Self-test: a simulated bivariate OU (Theta = [[0.20, 0], [-0.15, 0.05]], 60,000 obs) recovers Theta to 0.003, mu to 0.5 and S S' to 0.01.

## 3. When MVOU instead of univariate OU

- Key result: a linear combination w'X is a univariate OU **if and only if w is a left eigenvector of Theta** (w' Theta = lambda w',
  equivalently orthogonal to all but one right eigenvector; in the bivariate case, orthogonal to one eigenvector).
  `spread_is_ou(Theta, w)` returns the relative violation (0 = exact). A fixed 1:-1 spread of two OU legs is generally NOT a
  univariate OU if Theta has off-diagonal terms: its path can be non-monotonic.
- Use MVOU when paths are non-monotonic (spread rises before it falls), when correlations depend on horizon, or when you need
  the joint law for correlation to an existing book. Use PCA when no horizon dependence matters. Use univariate OU when the
  weights are orthogonal to a Theta eigenvector. (Huggins and Schaller 2024.)
- Bivariate illustrations (start 3 and 2): Theta = diag(ln2/0.25, ln2/0.25) gives a univariate OU spread with 3-month half-life;
  Theta = diag(ln2/0.25, ln2 x 12) (3-month and 1-month legs) gives a **non-monotonic** spread (rises 1.0 to about 1.4 near 0.1y then
  decays); Theta = [[ln2/0.25, 0], [-8, ln2 x 12]] makes the spread cross zero and converge from below ("overshoot" without momentum).
  With diagonal S the implied correlation is about 0 at 1 day, 0.30 at 1 month, 0.6 at 3 months; with S = [[1,-0.2],[-0.2,1]] it is
  -0.4 at 1 day and +0.4 at 3 months. (Huggins and Schaller 2024.)

## 4. Automated monitoring pipeline (rates)

1. Fitted curves to constant-maturity series (never roll individual bonds: roll-down distorts the fit).
2. PCA on those series; calibrate one OU process to each of the first three PCs; flag when ex-ante Sharpe over the horizon passes a
   preset threshold. Candidates only.
3. Choose bonds from the fitted curve, rescale PCA hedge ratios to actual BPVs, compute carry at bond level, assess mean reversion
   on the constant-maturity series, then use the calibrated model for half-life, first-passage density and execution (target,
   stop, scaling), and the MVOU for correlation with the existing book. Variant: MVOU directly on constant-maturity series replaces PCA
   (loses eigenvector intuition and macro interpretation). (Huggins and Schaller 2024, ch.5-15.)

## 5. Maximally mean-reverting baskets (what to do with the OU result)

- Objective: choose weights x with ||x|| = 1 and at most k non-zero legs maximising kappa of P_t = sum_i x_i S_ti. Dense solutions
  (cointegration / smallest-eigenvalue) have high cost, poor interpretability, tiny range and "often behave like noise and sometimes vary
  well inside bid-ask spreads". Add a variance floor (0.2-0.3 x median variance) and a cardinality cap (about 30-50% of the universe).
- Proxies (lower = faster reversion): Box-Tiao predictability lambda(y) = y'(A1 A0^-1 A1') y / y'A0 y; portmanteau of order p; crossing
  statistic (AR(1) with coefficient a crosses zero at rate arccos(a)/pi). (Cuturi and d'Aspremont, 2015.)
- US swap curve 1y-30y, 100-day windows: Box-Tiao lambda rises 0.58, 8.61, 16.48, 38.59, 84.55, 174.82, 184.83, 238.11 across the eight
  eigen-portfolios (last has half-life about 1 day and is insignificant on daily data); greedy sparse by cardinality k = 1..8 gets
  0, 35, 128, 178, 213, 247, 252, 252 so 3-5 legs capture most of it; k = 3 is a 3y-4y-5y fly with weights -0.288 / +0.806 / -0.517.
  "Even minuscule transaction costs (a bid-ask spread of 1bp) are sufficient to completely neutralize these market inefficiencies"
  in the out-of-sample test (1998-2005; 200-day estimation, re-estimated every 50 days). (d'Aspremont, Identifying Small Mean Reverting
  Portfolios, 2008.) Out-of-sample Sharpe at about 15 bp cost: dense PCA -0.617, sparse PCA 2.023, crossing 2.772. (Cuturi and d'Aspremont 2015.)
- Diversify across cointegrating vectors: in a rank-2 system, trading both spreads in parallel gave Sharpe 8.37 against 6.78 and 5.39
  individually and 6.75 for the single optimised spread (synthetic). (Palomar, Portfolio Optimization, 2025.)
- Position rule for an AR(1) basket x_{t+1} = rho x_t + sigma e (log utility, Jurek and Yang): N_t = rho (mu - x_t) / sigma^2 x W_t.
  Parameter uncertainty always lowers the optimal (Kelly) fraction. (Cuturi and d'Aspremont 2015; Paleologo 2025.)

## 6. Non-linear drift and level-dependent vol (when the linear OU fails a bucketing check)

- Stanton bucketing: split the observed range into equal-width buckets (e.g. 1,000 obs into 20), average the **subsequent** change per
  bucket, plot against the bucket midpoint; the same with the std dev of subsequent changes for g. Reveals stronger reversion far
  from the mean or higher variance at extremes. Candidate drifts: cubic f = a + bx + cx^2 + dx^3 (d <= 0), or a/x + ... (a >= 0) for a
  reflecting zero barrier. Only the linear drift has closed-form likelihood, transition and first-passage densities; non-linear fits can
  fit sampling noise. Beyond about a week local normality fails: Monte Carlo the paths and smooth with a Gaussian kernel (bandwidth by
  eye; h = 6 chosen in the book example). (Huggins and Schaller 2024, ch.1-5.)
