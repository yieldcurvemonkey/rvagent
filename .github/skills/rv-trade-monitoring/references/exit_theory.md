# Exit, stop and hedge theory for monitored RV trades

Long-form formulas behind the rules in [SKILL.md](../SKILL.md). Spreads in bp, curve spread = longer minus shorter.
Sources are cited inline; Leung-Li and Lopez de Prado results are model results, not live track records.

## 1. Discrete Ornstein-Uhlenbeck spread (the working model)

Continuous: `dX = theta (mu - X) dt + sigma dB`. Discrete AR(1) at step `dt`:

- `X_t = a + phi X_{t-1} + e_t`, with `phi = exp(-theta dt)`, `mu = a / (1 - phi)`.
- Half-life `tau_1/2 = -ln(2) / ln(phi)` in units of `dt` (equivalently `ln(2)/theta`).
- Stationary sd `sd_stat = sd(e) / sqrt(1 - phi^2)`, which equals `sigma / sqrt(2 theta)` in continuous time.
  (Consistent with Leung-Li's printed example, where sd = sigma / sqrt(2 mu) = 0.0277.)
- Estimate by OLS of `X_t` on `X_{t-1}`; equivalently OLS of `dX_t` on `(X_{t-1} - mean)`, slope `= phi - 1`.
- OLS phi is biased low in short samples (half-life too short), and `se(phi) ~ sqrt((1 - phi^2) / n)`: a half-life from fewer
  than about 100 observations, or from a 1-year window that contains one regime, is noise. Do not confuse this with the
  decay half-life of an EWMA risk model, which shrinks that model's effective sample (Golub, BlackRock, 2023: an 8-day
  half-life carries about 23 effective observations).
- Lopez de Prado (AFML, 2018) warns that as phi tends to 1 there is no recognisable optimum for exit rules, so
  calibrating exits to history on a near-random-walk spread is overfitting.

Transition mean and variance (Huggins and Schaller, RV Analysis, 2024): mean `mu + (x_t - mu) e^{-k tau}`;
variance `sigma^2 (1 - e^{-2 k tau}) / (2k)`. The hitting time to a level is a random variable: simulate paths and read
the hit probabilities for a stop or target within a horizon. Under the mean-reverting (linear) drift the expected path decays towards the mean without reaching it,
yet the expected first-passage time to the mean is finite, because paths cross the mean repeatedly.

## 2. Optimal exit with a stop (Leung and Li, Optimal Mean Reversion Trading, 2016)

Exit cost `c_s` (one way), entry cost `c_b`, stop level `L`, discount rate `r`. Notation in this section follows Leung-Li:
`dX = mu (theta - X) dt + sigma dB`, so `mu` is the reversion speed and `theta` the long-run mean (section 1 uses `theta` for speed).

- Liquidation (take-profit) level `b_L*` falls as the stop `L` rises, and meets the line `b = L` at `L*`.
  Above that point the investor liquidates at once. The critical level is
  `L* = (mu theta + r c_s) / (mu + r)` for the OU spread (a little below the mean `theta`); if the stop is at or above it there is no waiting region.
- Higher exit cost means a higher take-profit level; tighter stops force earlier, lower-level exits.
- Entry is a bounded band `[a_L*, d_L*]`, strictly above the stop and below `b_L*`. Between the stop and `a_L*` do not
  enter even if the price looks cheap, because a forced exit at a loss is likely.
- Non-triviality: enter only if the value of the round trip exceeds the entry cost. For the CIR case this is
  `(b* - c_s) / F(b*) > c_b`; if `c_b >= mu theta / r` never enter.
- Minimum holding period delta: `V^delta(x) = E_x[e^{-r delta} V(X_delta)]`. Enter only at a cheaper price (`d^delta <= d*`).
- A constant holding cost q maps exactly to adjusted costs: exit cost `c_s - q/r`, entry cost `c_b + q/r`.
- Ad hoc plus or minus 1 sd bands ignore costs, discounting, reversion speed and the stop. The optimal levels are outputs
  of `(mu, theta, sigma)`, the costs and the stop.
- Two-barrier value (stop `a`, target `b`, spread at `y`), for a diffusion with increasing and decreasing fundamental
  solutions F, G:
  `E[e^{-r tau} h(Y)] = h(a)[F(y)G(b) - F(b)G(y)]/[F(a)G(b) - F(b)G(a)] + h(b)[F(a)G(y) - F(y)G(a)]/[F(a)G(b) - F(b)G(a)]`.
  Use it to compare stop and target pairs before accepting them.
- Driftless Brownian stop and target odds (Ross, Introduction to Probability Models): `P(up A before down B) = B/(A+B)`.
  This is the no-drift benchmark: a symmetric target and stop on a driftless spread wins with probability equal to the
  stop distance over the total range.
- Switching (repeated round trips) lowers the per-trip threshold: entry and exit bands for repeated trading sit inside the
  one-shot band. Choose the formulation that matches how the strategy will actually be run.
- Smooth pasting holds at the threshold (value is C1, not C2). Do not assume twice-differentiability in numerics.

Worked model path (Leung-Li, exponential OU, model not a trade): mu = 0.8, sigma = 0.2, theta = 1, r = 0.05,
c_s = c_b = 0.02. One-shot: enter at xi <= 2.1754, exit at xi >= 3.0988. Switching: enter at xi <= 2.3888, exit at
xi >= 2.8323. On the same path the switching investor completes two round trips before the one-shot investor's first
liquidation. Comparative statics: raising mu moves entry levels up and leaves exit levels about flat.

## 3. Mechanical exit families (Chan, Quantitative Trading, 2009; Lopez de Prado, AFML, 2018)

Four exit types: fixed holding period; profit target or cap; latest-signal reversal; stop price. For mean reversion:

- Target = the historical mean (or a fraction of the way to it); time stop = about one half-life or a multiple of it.
- Chan: a reversal model should not carry a stop, because a rerun after a loss gives a same-sign, stronger signal and a
  stop "often means you are exiting at the worst possible time". Stops fit momentum, not reversal. Reconcile for RV:
  use a structural stop (the thesis is broken: the spread has moved beyond its own regime range, or a driver has changed),
  not a noise stop on mark-to-market.
- Triple barrier (AFML): profit take at `ptSl[0] * trgt`, stop at `ptSl[1] * trgt`, vertical barrier at a horizon, where
  `trgt` is realised or implied vol. First touch wins. Configuration `[1,0,0]` (no time limit) "could mean being locked
  on a losing position for years": always keep a vertical barrier.
- OTR calibration (AFML ch.8-18, positive equilibrium, sigma = 1, no costs): half-life 5 favours a profit target near 6
  with a 4 to 10 stop (Sharpe about 12); half-life 10 favours target about 5, stop 7 to 10 (about 9); half-life 25
  favours target about 3, stop 9 to 10 (about 2.7); half-life 50 gives 0.8; half-life 100 gives 0.32. Half-life sets the
  exit horizon; long half-lives give flat optima, so the exit cannot be tuned on them.
- Binomial check on a stop-and-target book (AFML): `theta = ((pi+ - pi-) p + pi-) / ((pi+ - pi-) sqrt(p(1-p))) * sqrt(n)`.
  Example n = 260, pi- = -0.01, pi+ = 0.005: p = 0.70 gives 1.173; p = 0.72 gives about 1.92 (the source prints 2.0; it reaches 2.0 near p = 0.722). Reject strategies where
  P[p < p_theta*] exceeds 5%.
- Trailing stop (During, Fixed Income Trading and Risk Management, 2021, fig 30.1): each time P&L rises by a fixed amount,
  raise the stop by the same amount. On reaching the target, move the stop to the target and set a new target.
- Scale in and out by thirds (BofA technicals primer, 2025): one third on a confirmed break, one third on a retest a few
  days later, the last third on the second turn from an equal high; exits in reverse.

## 4. Sizing while live

- Sigmoid target size (AFML): `q = int[m * Q]`, `m = x / sqrt(w + x^2)`, `x = f - p`, `Q` = max position. Calibrate w from one
  observed pair: `w = x^2 (m*^-2 - 1)`. Worked (AFML): m* = 0.95 at x = 10 gives w = 100 x (1/0.95^2 - 1) = 10.80.
  With Q = 100 and p = 100: f = 115 gives m = 0.977 and target 97; f = 110 gives m = 0.950 and target 95.
- Discretise size, `m* = round(m/d) d`, to avoid jitter and overtrading. Average the sizes of live bets rather than overriding them.
- Reserve capacity for a signal that strengthens before it weakens: sizes [1, 0.5, 0] lose -0.125 on a path where [0.5, 1, 0]
  makes 0.5 (AFML).
- Kelly (Chan): half-Kelly on a trailing window (about 6 months for roughly one-day holding), re-estimated at least daily.
  Cap leverage at (tolerable one-period drawdown) / (worst historical one-period loss); use the smaller of that and half-Kelly.
- Grinold and Kahn (Active Portfolio Management, 1999): transaction cost amortised per year = round-trip cost / holding period.
  No-trade band: stay put while `-SC <= MCVA <= PC`; trade back to the boundary, not to target. Impact: roughly one day's
  volatility to trade one day's volume; impact scales with the square root of size.

## 5. Hedge maintenance

- DV01 by central difference: `DV01 = (P(y - 1bp) - P(y + 1bp)) / 2`, per bp, positive for long duration (Tuckman and Serrat,
  Fixed Income Securities, 2022). Re-size as DV01 changes; it decays as the instrument ages.
- Duration-neutral notional: `N2 = -N1 D1 / D2` (market-value form `M2 = -M1 D1* / D2*`). Flaw: one yield variable only.
- Hedge calibration criterion: minimise unexplained daily P&L of the hedged book, not the in-sample curve fit (During 2021).
  A k-factor model needs k instruments.
- Hedge decay: ratios decay as PVBP ages; use forward PVBP matched to the holding period or update the ratios. OLS hedge
  ratios are asymmetric; prefer PCA or orthogonal regression when the spread residual matters.
- Risk bleed (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022): a 4y swap shows risk only at 4y today; six
  months later, as a 3.5y, it shows about 50% in each of 3y and 4y under log-linear discount factors. Bleed is invisible to
  VaR. Wider input gaps bleed more slowly; monitor a bleed column (today's open versus yesterday's close).
- Risk-change decomposition (Golub 2023): for risk `CTR = sigma rho X` with Y = sigma rho ("economy") and X = exposure,
  `dCTR = 1/2 (Y1 + Y2)(X2 - X1) + 1/2 (X1 + X2)(Y2 - Y1)`. Split a rise into exposure added (ask the PM to cut) and economy
  change (vol or correlation up: the breach is passive and may be waited out, depending on mandate).
- Trader-model VaR (Darbyshire): `c = sqrt(S' Q S)`, S the bucket risk strip, Q the covariance of bp changes;
  `VaR_5% = 1.644 c`, `VaR_1% = 2.326 c`. Single-instrument VaR-minimising trade: `S_trade = -Q_hh^-1 Q_hat S`. Only one
  such trade is valid at a time; trade about 50% and re-run.
- Expected shortfall for linear rate risk under normality: ES_2.5% (2.338 sigma) is about VaR_1% (2.326 sigma).

## 6. Repo, special and basis monitors (cash-futures basis, Burghardt et al., The Treasury Bond Basis, 2005)

- A bond is on special when its reverse RP rate is below general collateral (GC). If a short cannot find the issue, the
  short fails: the holder pays the coupon and earns no RP interest, so carry turns negative. Specials have no floor.
- Repo-status risk: long the basis of a special bond that goes back to GC: its RP rate rises and its basis falls. Short
  the basis of a GC bond that goes special: the reverse RP falls and its basis rises.
- Term versus overnight financing: overnight is cheaper on a positive curve and easier to unwind; a long basis loses if
  overnight RP rises; a short basis loses if overnight RP falls.
- Squeeze warning signs: a declining RP special rate, large short sales in the issue, and the issue's yield spread to similar
  issues changing. A squeezed short has no theoretical maximum loss; a stop cannot cap it.
- Option-adjusted basis (OAB) = actual basis minus theoretical basis (carry plus theoretical option value). OAB above zero:
  basis rich, sell the basis. Below zero: buy the basis. The 1990 client rule entered at OAB at least 5 ticks negative.
- Residual risks of the vol-arbitrage version: deliverable yield-spread changes, repo, profile mismatch between basis and
  option payoffs, and the option expiring about a month before futures last trade (vega mismatch).
