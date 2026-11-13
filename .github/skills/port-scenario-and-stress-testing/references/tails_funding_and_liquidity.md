# Tails, funding and liquidity detail

Companion to [SKILL.md](../SKILL.md). Formulas first, then sourced numbers.

## 1. Invariant PC risk with a fat-tail extension (Musaelian, Nagarajan, Villani, SSRN 2777026, 2016)
Portfolio value change in PC space: dPi = J'a + 0.5 a'Ha, with J_j = dPi/dPC_j and H_ij = d2Pi/dPC_i dPC_j, a_i iid N(0,1).
- E[dPi^2] = |J|^2 + 0.5 |H|_F^2 + 0.25 [Tr H]^2. Rotation-invariant: aggregates across currencies without aligning PC signs.
- Mixed normal (all a jump together: N(0, theta^2), i.e. SD x theta, with prob p, N(0,1) with prob 1-p):
  E[dPi^2] = (1 + p(theta^2 - 1)) |J|^2 + (1 + p(theta^4 - 1)) (0.5 |H|_F^2 + 0.25 [Tr H]^2).
- General distribution: E[dPi^2] = sum J_i^2 E[a_i^2] + sum J_i H_ii E[a_i^3] + 0.25 sum_{i!=j}(H_ii H_jj + 2 H_ij^2) E[a_i^2 a_j^2] +
  0.25 sum H_ii^2 E[a_i^4]. Plug in empirical skew and kurtosis (skew matters near rate floors).
- Flylets: basis for the (n-2)-dim space orthogonal to PC1 and PC2 built from three adjacent nodes f_i = (..., a_i, b_i, c_i, ...)
  with f_i.PC1 = f_i.PC2 = 0, |f_i| = 1; exposure F_i = dPi/df_i; metric sigma_F^2 |F|^2; mixed-normal version sigma_F^2 (1 + p(theta^2 - 1)) |F|^2.
  Keep PC and flylet measures separate.
- Sensitivities by central difference: dpi/dPC_j = [pi(C + e PC_j) - pi(C - e PC_j)] / (2e); second derivatives similarly.
- Numbers: USD swaps DV01 1,000,000 across tenors are near linear; 1m straddles 200mm per leg at 1y/5y/10y/20y/30y are dominated by
  the Hessian. PC1/PC2-neutral 2y5y7y and 5y10y15y flies show negligible invariant measure but material flylet exposure. At p = 10%,
  theta = 5 net risk is x2 for swaps (1.84 from the formula) and x8 for straddles (7.96). 1y-trailing PC coefficient excess kurtosis:
  a1 1.19, a2 6.40, a3 8.82, a4 18.29, a5 30.19, a11 140.90, a12 42.29; skew a5 -1.92, a11 5.10. PC vols drift down after calm periods,
  so J and H look small exactly when tail risk builds.
`scripts/scenarios.py::invariant_risk` implements the first two bullets, verified by Monte Carlo in the self-test.

## 2. Horizon dependence and simulation
- **Horizon-dependent correlation (multivariate OU)**: dX = -Theta (X - mu) dt + S dB; off-diagonal Theta creates correlation that grows
  with horizon (about 0 at 1 day, 0.30 at 1 month, 0.6 at 3 months in the source example). "Over short horizons, there is essentially
  no directionality in the butterfly spread. But over longer horizons, the butterfly exhibits considerable directionality." Use MVOU when
  scenarios sit at different horizons, PCA when they do not (Huggins & Schaller, Fixed Income Relative Value Analysis, 2024).
- Beyond ~1 week local normality fails: simulate paths and smooth with a Gaussian kernel density (bandwidth by eye: h = 2 too rough,
  15 too smooth, 6 chosen in the example).
- **PCA scenario draws**: draw H_i ~ N(0, lambda_i), map to d_r = E h' and add back the mean; dropping minor PCs understates variance,
  rescale. Cholesky alternative: Q = L L', X = L Z. Example: eigenvalues [19.5, 1.53, 1.06, 0.55], h = [4.0, -1.6, 1.6, -0.2] gives
  (+4.4, +3.6, +0.1, +1.4) bp for 2Y/5Y/10Y/30Y (Darbyshire, Pricing and Trading IR Derivatives, 2022, Ex 15.3, 15.6).
- **Grid Monte Carlo VaR with PCs**: fully revalue on a grid of PC realisations (+-0.25, 0.5, 1, 2, 3 SD), interpolate the surface, simulate. One PC
  is usually enough for directional books (generic MBS: 1-PC VaR $6.18 vs 2-PC $6.09 per $100 face); variance-covariance and grid-MC
  VaR can differ by up to 300% for non-linear securities (Golub & Tilman, Risk Management: Approaches for Fixed Income Markets, 2000).
- **Synthetic data**: parametric (fit a heavy-tailed model), non-parametric (resample; destroys vol clustering), hybrid (fit mean/vol model,
  resample residuals; preserves clustering), crisis replays. Residual bootstrap is wrong under heteroskedasticity; resample cases
  (Palomar, Portfolio Optimization, 2025; Shalizi 2025).
- **Variance of a random sum** (uncertain number of events): Var = E[N] Var(X) + (E[X])^2 Var(N) (Ross 2010).
- **Minimum residual VaR with restricted hedge buckets**: P&L ~ N(0, Sigma); hedge Q only in allowed buckets; residual c*^2 = (P - Q)' Sigma (P - Q), Q = Sigma_MM^-1
  Sigma_M P; VaR99 = 2.326 c*. Compare hedge sets; or simulate many random portfolios and hedge each (Quantitative Finance Stack Exchange, PCA for risk bucketing, 2019).

## 3. Plausibility measures in full (Golub & Tilman 2000; BlackRock's Guide, 2023)
- z = |z| xi with |xi| = 1; sigma^2(xi) = xi' Sigma xi; 1-SD shock of that shape = sigma(xi) xi; realisation S = |z| / sigma(xi).
  Magnitude plausibility mpl(z) = 2 P(N(0,1) >= |S|): symmetric, ignores mean reversion.
- Shape plausibility: decompose into PC realisations v_i, theta_i = v_i^2 / sum v_j^2; most representative theta_M = explanatory powers
  (e.g. 92.80, 4.80, 1.27, ..., 0.03), least representative theta_L = last PC (0,...,0,100); spl = 1 - sum(theta_i - theta_M,i)^2 / sum(theta_L,i - theta_M,i)^2
  (the source's OCR is garbled; this form matches its stated 100% and 0% endpoints).
- Explanatory power on 9/30/96: PC1 93%, parallel 88%, a 2s10s +-50bp (SEDUR) shock 38%. On 12/31/98: PC1 83% vs parallel 67%, which made
  practitioners question parallel-shock risk measures.
- Z-score delta: reduction in Z if one policy shock is replaced by its conditional expectation given the others; large deltas flag
  internally inconsistent views (Soft Brexit: GBP 2y z-delta 0.56, GBP 10y 0.49 vs FTSE 0.04).
- Hygiene: few, non-collinear policy variables (adjusted R^2 < 90%); regime-consistent covariance; scenarios ignore carry.

## 4. VaR variants and aggregation
- Analytic VaR = -Phi^-1(1 - a) sigma_T. Historical VaR suffers "ghosting" when old extremes drop out of the window. Filtered:
  sigma_T x percentile{r_t / sigma_t}; HVaR = STRM x AVaR where STRM = VaR(z-scores)/(-Phi^-1(1-a)).
- Aggregation in quadrature: VaR_tot = -Phi^-1(1-a) sqrt((STRM sigma_sys)^2 + sum (ITRM_j sigma_idio,j)^2 + sigma_idio,other^2); slightly
  conservative (0-5%) vs exact convolution.
- Historical VaR/ES worked example (Darbyshire 2022, Ex 14.3), 400 days: worst 10 = -170k, -95k, -40k, -30k, -25k, -19k, -12k, -11k, -10k, -9k;
  VaR 1% = 4th worst = 30k; ES 2.5% = 421k/10 = 42.1k. (The source prints one value as "10k"; it must be -10k for the stated total.)
- Desk aggregation example: strips Alpha (spread) c = 336 and Bravo (outright) c = 291 combine to c = 529 vs 627 summed.
- Gap risk: traders cut VaR into the close because there is no chance to stop out overnight; stops gap and fill worse (Chan 2009).
- Covariance hygiene: use changes never levels; >= 100 points (or >= number of instruments); match VaR horizon; sample from a regime like the expected
  future; smoothing inflates correlations and can lower VaR for books with oscillating bucket risk; smooth on the correlation matrix, then rescale the diagonal, then apply vols.

## 5. Funding, margin and leverage detail
- Risk taxonomy for basis trades (CFTC MRAC, Treasury Cash-Futures Basis Trade, Dec 2024): market risk (VM on futures offset only if margin is exchanged on the cash leg;
  small correlation changes -> large margin calls at high leverage); delivery-option risk (convergence only for the CTD); liquidity risk (overnight vs term
  repo mismatch, lender refuses to roll); counterparty; fire-sale feedback. Effective practices: continuous market/liquidity/counterparty modelling,
  MtM attribution, extreme-but-plausible correlation changes, repo-rate paths and financing unavailability, liquidity buffers, term funding, diversified
  counterparties, intraday reserve, orderly-unwind plan.
- Leverage economics: 20x leverage gives 9-10% annual excess return; a March-2020-type drawdown would more than wipe out equity (15x proxy had high tail correlation with
  1-3y corporate OAS). Levered-fund gross shorts peaked ~$615bn; WN levered shorts ~1.5x daily volume (CFTC MRAC 2024; TBAC, Discussion of Treasury Futures Positions, 30 Jan 2024;
  J.P. Morgan 10 Mar 2020). Fed-estimated basis holdings ~$317bn. Gross HF UST exposure $4tn ($2.4tn long, $1.6tn short) Sep 2025; swap-spread arb > $300bn,
  maturity-matched ~$395bn, curve RV ~$375bn; ~$1.5tn UST in basis trades vs ~$1tn pre-March 2020 (FT Alphaville, 14 Aug 2026).
- Crowding dashboard (TBAC 2024): futures open interest as % of Treasury market, cleared repo size, basis valuations with open interest ("if cash richens vs
  futures and open interest is growing, suggests position crowding"), dealer inventories, overnight vs term repo spreads, CME and repo margin changes,
  concentration of bilateral repo funding.
- Operational-risk screen: positions that are operationally intensive (multi-counterparty, overnight funded), balance-sheet intensive, with small upside and
  large dislocation downside are unwound first: "there is a strong incentive to be the first out the door"; perception of risk, not realisation, drives
  unwinds (J.P. Morgan 10 Mar 2020). Stress-time dealer constraint is internal VaR limits: desks sell inventory (longer-dated USTs first) when vol spikes
  (Conks, The Shadow Cash Market Part II, 10 Aug 2025). A CCP addresses default risk, not illiquidity; reducing counterparty risk raises liquidity risk.
- Long basis trades "seem riskless, so long as they can be held to expiration": risks are MtM vs loss limits, margin calls, overnight repo withdrawal. Near-arbitrage terminal
  payoffs do not ensure low MtM volatility (Tuckman & Serrat 2022; Burghardt et al. 2005).

## 6. Liquidity-to-volatility chain (J.P. Morgan, Fast and furious, 20 Nov 2018, Exhibit 8)
Aggregate price impact = fast_fraction x PI_fast + (1 - fast_fraction) x PI_slow; map % change in price impact to % change in 10y realised vol with a 3y regression.
- Fast fraction -> price-impact shift -> change in 10y realised vol (bp): 20% -> +54% -> +26; 30% -> +36% -> +17; 40% -> +18% -> +9; 50% -> 0; 60% -> -18% -> -9; 70% -> -36% -> -17.
  Each +10% of fast share ~ -10bp realised vol.
- 3Mx10Y implied vol shock (bp) -> fast fraction -> PI shift -> realised-vol knock-on (bp): 10 -> 47% -> 6% -> 2; 50 -> 34% -> 28% -> 10; 100 -> 18% -> 57% -> 20; 150 -> 3% -> 85% -> 31
  (knock-on ~ 20% of the implied shock). Assumes HFT flow is true risk transfer and the past predicts the future; "liquidity is perhaps not as resilient under stress as it appears locally".
- Composite liquidity index = average of six 5-year z-scores (price impact; depth, inverted; HFT activity, inverted; expiry-curve slope 1Mx10Y/1Yx10Y; futures richness, inverted, CTD yield error
  adjusted for basis; O/N GC - EFFR). 31 Mar 2020 / 13 Mar 2020 peak: price impact 3.65/9.49; depth 2.90/3.18; HFT 4.97/6.43; slope 3.63/6.06; futures richness 0.94/6.60; funding -1.46/0.20;
  index 2.44/5.32 (J.P. Morgan, Are we there yet?, 1 Apr 2020). Futures can trade rich to cash in stress (liquidity tiering): adjust the CTD yield error for the basis before reading richness.
- Prolonged low volatility thins market-maker balance sheets so a vol shock meets depleted capacity (During, Fixed Income Trading and Risk Management, 2021). Vol targeting on trailing vol fails
  for assets whose vol is low just before crises; implied-vol switches worked better (Willer & Saunders 2026). "It takes extreme volatility to hurt bonds": only extreme realised-vol quintiles hurt.

## 7. Convexity-flow overlays
- MBS: hedge need = old 10y-eq - new 10y-eq; 10y-eq = duration x $ / 10; delta duration = (rate move / 100) x (-convexity); quoted convexity in percentage points (0.06 shown as 6). Duration 7, $100bn, convexity -2: +25/+50/+100bp ->
  duration 7.5/8/9, 10y-eq 75/80/90 vs base 70, hedge need -5/-10/-20bn. Pipeline pull-through ~5-6% per 15bp of mortgage rate, rebuilt in ~45 days. As the primary/secondary spread compresses
  toward ~105bp, mortgage beta to USTs and event risk rise. Coupon concentration (2003) creates "flashpoints"; spread distribution (2013) creates gradual "convexity bands" (BofA, MBS convexity hedging primer, 18 Mar 2021).
- Banks: assets short convexity, deposits long; assumptions deposit beta 0.45 retail / 0.65 wholesale, each changing 0.15 per 100bp, MSR as a 30bp IO strip, equity 9.5% of assets. Output: bank equity duration short ~5y, another 6-7y after a further 100bp
  rally; > $100mn/bp receive-fixed even if a quarter is hedged; another 50bp rally -> $300-400mn/bp. Thresholds are infrequent, so spreads are more directional in rallies than sell-offs. Mortgage hedger delivery ~$200mn/bp receive-fixed since Nov 2018, below 2003 and 2008 (J.P. Morgan, Is bank convexity hedging lying in wait?, 31 May 2019).
- Offsets: MBS negative convexity peaks only after a ~70-100bp rally (exposure could rise ~30% for 70bp+); callable (structured-note) dealer hedges resist moves, sensitivity staying 80-90% of current after a further rally and falling
  meaningfully only after 50bp+; net hedger flow = negative-convexity hedgers minus callable offset (J.P. Morgan, convexity hedging in interest rates, 29 Mar 2019). Convexity directionality appears late in a repricing and matters on single days, not over long repricings.

## 8. Distribution-free bounds
- One-sided Chebyshev: P(X >= mu + a) <= s^2/(s^2 + a^2); mean 100, variance 400, P(X >= 120) <= 1/2 vs 5/6 from Markov. Chernoff: P(X >= a) <= e^{-ta} M(t), minimised over t (Ross, A First Course in Probability, 2010).
- Best linear predictor MSE = sigma_y^2 (1 - rho^2): the residual of a linear hedge; stress rho directly.
- Stable laws with index alpha < 2 have infinite variance and jump-like paths (Shafer & Vovk, Probability and Finance, 2001): variance-based stress is unstable.
- Normal-time prices reveal total demand depth, not its stress-resilient part: Phi(b; b_Rep) = beta/(4 chi b) [(1+chi) b + chi b_Rep]^2 and stress capacity = Phi(surviving depth) + deployable resources; shifts between investor
  blocks leave prices unchanged but change stress capacity (Delao & Li, NBER WP 35612, 2026). Illustrative stress capacity 20% of debt (surplus only) to 32-36% (with elicited shares); not an estimate for the US.
