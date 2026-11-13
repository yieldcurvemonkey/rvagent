---
name: quant-mean-reversion-ou
description: Fits an Ornstein-Uhlenbeck (AR(1)) model to a rates RV residual (curve spread, fly, swap spread or ASW, basis, PCA or fair-value residual, vol spread) to get mean, reversion speed, half-life with confidence interval, equilibrium sd, z-score and ex-ante Sharpe by horizon; tests mean reversion (ADF, KPSS, Hurst, variance ratio); sets cost-aware entry/exit bands (Bertram cycle-time, Leung-Li optimal stopping), time and statistical stops; multivariate OU. Use when asked how long a dislocation lasts, half-life, is this spread mean-reverting, z-score vs OU, where to enter, exit or stop a fade, optimal stopping, expected holding period, overshoot, MVOU, or whether a 2s10s, 5s30s, 2s5s10s fly, swap spread, ASW, basis or STIR fly residual is worth fading.
---

# Mean reversion and OU timing for rates RV residuals

A rich/cheap reading is only a trade if it closes before costs, carry and regime change eat it. The OU model
dx = kappa (mu - x) dt + sigma dW turns a residual series into three numbers the trade needs: where it is going (mu),
how fast (half-life ln2/kappa) and how wide it wanders (sd_eq = sigma / sqrt(2 kappa)). A z-score alone ignores speed: with a
200-day half-life tomorrow's expectation is about today's level, so z = 2 "tells us almost nothing" (Huggins and Schaller,
Fixed Income RV Analysis, 2024). This skill fits and tests the OU, converts it into an ex-ante Sharpe, entry/exit/stop levels and
a holding-period budget, and says when to refuse. Building the residual itself (fly weights, PCA, fair-value regression, cointegrating
weights) is done upstream; this skill times the fade.

## When to use
- "Is this fly / spread / residual mean-reverting, and how fast?" or "what is the half-life of this dislocation?"
- Choosing entry, target, stop and maximum holding time for a z-score fade, or replacing a flat |z| > 2 rule with a cost-aware one.
- Comparing candidate trades on ex-ante Sharpe over a common horizon (e.g. 2 weeks) instead of raw z.
- Deciding whether carry/roll or reversion dominates (see the breakeven rule below).
- Multi-leg residuals whose paths overshoot or whose correlation depends on horizon (multivariate OU).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| A residual or spread series x_t in bp (fly, curve spread, swap spread, ASW, basis, PCA / curve-fit / fair-value residual, forward-grid residual) | derived from `curve_par` / `curve_zero`, `swap_spreads`, `stir_quotes`, `fut_quotes`, `bond_quotes`, `vol_surface`, or a `signals` row (`value`, unit bp) | daily on one `snap`, >= 250 obs, ideally 500+ (>= 5 half-lives; 10 is better) | Constant-maturity or fixed-structure series, never a rolling single bond. Sign convention stated by the caller |
| Round-trip cost of the structure (bp, in the series' own units) | `bond_quotes` / `fut_quotes` bid-ask, or `trades` history | current | Cost of opening and closing one position. Without it the band is degenerate (a* = 0): ask |
| Carry and roll per day of the package (bp/day, sign for the position) | from [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md) | current | For the breakeven rule |
| Optional: >= 2 related residuals for multivariate OU | same | same sampling, same `snap` | Do not mix snaps inside one series |

If an input is missing, ask for it or hand off to the data adapter. Never invent values. The script CLI reads a CSV or Parquet file with
a `date` column and a value column (default `value`), optionally grouped by a package id column.

## Method

### 1. Prepare the series
1. Use levels in bp on a single `snap`, business-day grid, with stale or failed rows removed (see
   [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md)). Drop overnight gaps if mixing sessions.
2. Orientation: x is the caller's series in bp. x above mu means the fade is **short x** (profit when x falls), x below mu means long x.
   Translate that into instruments before output. Curve spread A-B = longer - shorter: x above mu on 2s10s means steeper than usual, fade = flattener.
   Fly 2s5s10s = 2 x 5y - 2y - 10y: x above mu means belly cheap (high yield), fade = receive the belly. Swap-spread signs follow the
   market (US swap minus Treasury; EGB bond minus swap); never flip a sign silently.
3. Prefer a residual with a presumed zero mean (curve-fit, PCA or fair-value residual) over a quoted spread, whose fair level drifts
   with unobservable factors (Huggins and Schaller 2024). A PCA residual estimated on changes is not mean-zero in levels: cumulate
   the factors and test the level residual for stationarity first (Quantitative Finance Stack Exchange, 2015). Fixed current weights
   back-cast over history carry look-ahead; rebuild causally.

### 2. Fit the OU (AR(1) mapping)
Regress x_t = a + phi x_{t-1} + e on the window. Require 0 < phi < 1, else report "not mean-reverting" (one sentinel, NaN).
- kappa = -ln(phi) / dt; mu = a / (1 - phi); sigma = sqrt( var(e) * 2 kappa / (1 - phi^2) ); sd_eq = sigma / sqrt(2 kappa).
- Half-life = ln 2 / kappa = -ln 2 / ln(phi) (phi = 2^(-1/half-life)). In daily data dt = 1 so kappa is per business day; annualise with 252
  (weekly 52). Report in business days.
- The closed-form exact MLE (Leung and Li, 2016) equals the OLS fit; keep `method` as a sweep axis, not a source of disagreement.
- Equivalent regression: regress daily change on (mu - x_{t-1}); the slope is about kappa (EUR-GBP 5y5y vol spread: slope 0.055 vs fitted
  OU 0.056 per day, Huggins and Schaller 2024). The half-life uses the whole series, so it is a more robust holding-period estimate than a
  back-test-optimised holding period (Chan, Quantitative Trading, 2009).
- Confidence interval: phi_se = sqrt(var(e) / sum (x_{t-1} - mean)^2); half-life CI from phi +/- 1.96 se. If the upper phi reaches 1 the
  half-life CI is unbounded: treat the half-life as unknown.
- **Small-sample bias**: phi is biased down near 1, so slow reversion reads too fast. With 250 daily obs a true 40-day half-life reads a median
  21 days (10-90%: 11-44); true 11 reads 9 (6-14). Do not trust one-window half-lives above about n/6; compare 250, 500 and full windows.
- Re-fit on a rolling window (250-day: one year, long enough for phi, short enough to follow regimes; BofA and Rhodes both use about 250/252).
  Flag instability when the rolling half-life leaves [0.5x, 2x] of the full-sample value.

### 3. Test that it mean-reverts (do not rely on one test)
| Test | Pass rule (defaults) | Notes |
|---|---|---|
| ADF, constant only, AIC lags | t < -2.86 (5%, asymptotic) | Low power near phi = 1; fail-to-reject is not acceptance |
| KPSS level | stat < 0.463 (5%) | Over-rejects persistent series (about 18-25% false rejections at half-life 14 vs 5-8% at 1.7): a warning, not a veto |
| Hurst (std-dev method) | H < 0.5 (0.4 or lower is convincing) | Validate code on a random walk first (H must read 0.5) |
| Variance ratio VR(2,5,10) | VR < 1 with robust z* < -2 | For an AR(1), VR(q) = (1 - phi^q) / (q (1 - phi)); use heteroskedasticity-robust z* across vol regimes |
| Known-weight spread | test each leg I(1), then ADF on the spread with ordinary critical values | When weights are fixed (1:-1, -1:2:-1, DV01-neutral) use them directly (Hamilton, 1994); estimated weights need Engle-Granger or Johansen critical values: see [quant-cointegration](../quant-cointegration/SKILL.md) |

Details, critical values, power and contaminants: [references/tests-and-critical-values.md](references/tests-and-critical-values.md).
Verdict logic in `diagnose`: flags = ADF fails to reject, KPSS rejects, Hurst >= 0.5. OK = no flags; WEAK = one flag; REJECT = two or more flags, or a hard gate fails
(phi outside (0,1), half-life < 2 or > 90 obs, half-life CI unbounded, n < 5 half-lives; section 4).

### 4. Gate on half-life and sample (defaults; calibrate out of sample)
| Half-life (business days) | Action | Reason |
|---|---|---|
| < 2-3 | do not trade the OU | Statistically insignificant on daily data (a half-life of 1 day was insignificant; d'Aspremont, 2008) and inside bid-ask; 1 bp bid-ask erased the fly-like edge in liquid US swaps |
| 3 to 40 | tradable; band and time stop below | Fast OU shows a clear optimal rule (half-life 5-10 in the profit-take/stop mesh; Lopez de Prado, 2018); swap-spread residual about 20 days (BofA, 2016); USD PCA fly 11 days (bquanttrading, 2015) |
| 40 to about 90 | carry-dominated: only with the breakeven rule | Half-life 25+ is flat and random-walk-like in the mesh; model residuals reverting in about 3 months (BNP, 2021; ING, 2020) are carry/roll trades |
| > 90, or CI upper bound unbounded, or n < 5 half-lives | refuse an OU timing; use a fundamental or cointegration argument | Calibrating on near-random-walk spreads is overfitting |

Also compare the expected reversion time with the stability horizon of the relationship: only take trades whose reversion speed delivers
performance before structural issues bite (Huggins and Schaller 2024).

### 5. Ex-ante Sharpe by horizon (the comparison metric)
With x0 today, horizon h (days): E[x_h] = mu + (x0 - mu) e^(-kappa h); sd(x_h) = sigma sqrt((1 - e^(-2 kappa h)) / (2 kappa)).
Expected move = (mu - x0)(1 - 2^(-h/half-life)); Sharpe_h = |E[x_h] - x0| / sd(x_h); annualised x sqrt(252/h) falls with h beyond about the
half-life. Compare trades at one horizon (default **h = 10 business days, two weeks**: Huggins and Schaller 2024; this is a reversion-Sharpe comparison horizon, not the 3-month carry/roll default, so label which one a figure uses; screen with raw Sharpe_h
>= 0.5 as an agent default, then validate out of sample). Constant-vol OU overstates Sharpe at extreme entries (vol is often higher in the
tails): check level-dependence with Stanton bucketing ([references/mvou-and-baskets.md](references/mvou-and-baskets.md), section 6). Autocorrelated P&L
biases the Sharpe estimate; the standard error of an annual Sharpe is about sqrt((1 + SR^2/2)/T) with T in years (Paleologo, 2025).

### 6. Entry, exit and stop levels
Thresholds are **outputs** of (kappa, sigma, costs, stop), not inputs (Leung and Li 2016): faster reversion narrows the band, higher vol widens
it, higher entry cost lowers the entry level, higher exit cost raises the target and lowers the entry. Never copy +/-2 from a textbook.
1. **Repeated trading (default for a screen): Bertram cycle-time band.** Standardised units a = distance/sd_eq, c = round-trip cost/sd_eq.
   Maximise profit rate (2a - c) / T(a), T(a) = pi erfi(a/sqrt2)/kappa (mean first-passage -a to +a). FOC T(a) = (a - c/2) T'(a), solved by
   `optimal_symmetric_band`. Zero cost gives a* = 0 (degenerate: it says trade continuously, so always supply a real cost).
   Example: half-life 11 d, sd_eq 2.33 bp, cost 0.25 / 0.5 / 1.0 / 2.0 bp gives a* = 0.56 / 0.71 / 0.91 / 1.19 sd_eq, one-way hold 23 / 31 / 42 / 61 days.
2. **One-shot (a single position, wait for the best price): Leung-Li** `leung_li_levels` on the demeaned series (theta = 0, x read as the position's
   mark-to-market, r = opportunity-cost rate per day). Gives wider levels (exit +2.5, entry -2.3 sd_eq at r = 0.0005/day for the same inputs, costs split c_s = c_b = cost/2) because there
   is one trade to be made. Details, stop-loss and switching: [references/leung-li-optimal-stopping.md](references/leung-li-optimal-stopping.md).
3. **Practical entry floor**: enter when |z| >= max(a*, 1.5). The solver assumes known parameters and a clean OU; parameter error, regime risk and the fact that
   "the signal of mean-reversion is strongest far away from the mean" (swapsball.net, 2017) argue for the floor. 1.5 is an agent default consistent with
   the 1.0-2.0 threshold grid of the swap-spread study and the +/-1.5 to +/-2.5 z-score range used in practice (Brenndoerfer, 2025); do not optimise it in-sample.
4. **Target**: exit when |z| <= 0.5 (or flip at the opposite a* if running the repeated strategy). Do not take profit mechanically at zero: EUR fly residuals overshot
   5-10 bp within about 3 months in 6 of 7 episodes (BNP, 2021).
5. **Time stop = 3 half-lives** (12.5% of the gap left); the half-life approximates the expected holding period (Chan, 2009). For holding periods that depend
   on history use the half-life, not a back-test optimum, which is snooping-prone with few trades.
6. **Statistical stop, not a price stop**: exit if |z| >= 3.5 (at least 1 sd_eq beyond entry) AND the rolling re-fit fails (phi up to 1 or ADF no longer rejects), or a
   portfolio drawdown stop of 10-15% (Brenndoerfer, 2025). Reversal models "never recommend a stop loss" because after a loss the signal is stronger (Chan, 2009),
   so a stop is justified only by news of a momentum regime or a break in the relationship; a stop set too tight (L >= L* = (mu theta + r c_s)/(mu + r), about the mean) destroys
   the trade, and with a stop, do not enter when very cheap but close to it (Leung and Li 2016). A stop lowers the take-profit level.
7. **Profit-take / stop-loss mesh** (only when a real optimum exists): for fast-reverting zero-mean processes the best rule is a small profit-take with a wide stop, the worst
   is a tight stop with a wide profit-take, symmetric barriers are near-neutral; slow half-lives show no optimum (Lopez de Prado 2018, [references/case-studies.md](references/case-studies.md) section 7).

### 7. Carry and breakeven (when reversion is slow)
Expected P&L over h days = (x0 - mu)(1 - 2^(-h/half-life)) x side + carry-and-roll x h - cost, with side = +1 for short x (x0 > mu), -1 for long x, and carry-and-roll signed for the position.
Months to breakeven = (mispricing - execution cost) / (carry loss per month): a forward-grid steepener 14 bp too flat that rolls -15.5 bp over 3 months only breaks even if the residual
closes in under 2.6 months ((14 - 0.5) / (15.5/3) = 2.6 with a 0.5 bp charge, our reading); a 23 bp rich fly belly with carry -2 bp/3m is safe unless reversion takes more than 36 months (ING, 2020).
Charge execution off the mid in the entry level.

### 8. Multivariate OU (when one-dimensional OU fails)
dX = -Theta (X - mu) dt + S dB, fit by VAR(1): Theta = -logm(A)/dt. A weighted spread w'X is a univariate OU only if w is a left eigenvector of Theta; otherwise its path can
be non-monotonic (rises before it falls, or overshoots without momentum) and its correlation to other legs depends on horizon. Use `fit_mvou` and `spread_is_ou`.
Half-lives are ln2/Re(eigenvalues of Theta). Pipeline, estimation recipe, sparse baskets: [references/mvou-and-baskets.md](references/mvou-and-baskets.md).

## Worked examples

**A. Time a PCA-weighted fly fade (inputs from a cited source, rest computed with the script).** USD 3s5s10s PCA fly, weights [-0.90, 1.00, -0.46]; the source reports an OU
half-life of 11 business days, z = -2.15, fly about -47 bp (range about -36 to -50), expected path reverting from about -47 toward about -42, expected P&L about 5 bp ex carry and carry-plus-roll
+6.25 bp over 3 months (bquanttrading blog, Principal Component Analysis Part II, 2015). Take mu = -42 bp, sd_eq = 5/2.15 = 2.33 bp as an illustration consistent with those numbers
(so kappa = ln2/11 = 0.0630/day, sigma = 0.826 bp/sqrt(day)). Script output:

| h (days) | E[move] bp | sd bp | Sharpe_h | annualised |
|---|---|---|---|---|
| 5 | +1.35 | 1.59 | 0.85 | 6.0 |
| 11 | +2.50 | 2.01 | 1.24 | 5.9 |
| 22 | +3.75 | 2.25 | 1.67 | 5.6 |
| 44 | +4.69 | 2.32 | 2.02 | 4.8 |

The expected move is half the gap at one half-life (2.5 of 5 bp), 3/4 at two; the 5 bp "expected P&L" is the full convergence. Bertram band at 0.5 bp cost: a* = 0.71, i.e. enter beyond
+/-1.65 bp of mu; the practical floor |z| >= 1.5 (3.5 bp) is binding, and z = -2.15 qualifies. Time stop 33 days; statistical stop z = -3.5 (-50.2 bp) with a failed re-fit. Because the
source's own back-cast used fixed current weights, treat the fit as look-ahead until rebuilt causally. The source's carry-plus-roll (+6.25 bp over 3 months) is positive, so carry does not fight the trade.

**B. Swap-spread residual threshold choice (cited back-test).** Rolling 250-day PCA residuals of 2/5/10/30y swap spreads are AR(1)-like with half-lives about 20 days. With the dislocation
indicator threshold 1.0 to 2.0 the German strategy ran Sharpe 2.4-2.8 (554-869 cum. bp, average hold 21-43 days) and the US 0.4-1.2 (51-267 bp, hold 26-38), no costs, carry or stops
(BofA Merrill Lynch, Liquid Insight, 2 Jun 2016; full table in [references/case-studies.md](references/case-studies.md)). Read-across: a 20-day half-life implies a 60-day time stop and holds of 20-40
days; the edge was market-specific (German rising with threshold, US falling), so fit per market. Use as a prior, not a forecast.

**C. EUR fly residual and overshoot.** Since 2013, 7 episodes of 5s10s30s residual < -5 bp for over a week: normalised in 6 of 7 with a flatter 10s30s (86%), start-to-fair 3.1 months, then overshoot
to 10y cheap by 5-10 bp in 6 of 7 (BNP Paribas, EUR curve convexity: Lessons from history, 25 May 2021). About 3 months from start to fair value is a time-to-target, not a half-life, but it signals a slow process where carry and roll matter:
fit the OU on the residual itself, apply the breakeven rule, and target fair value plus part of the typical 5 bp overshoot rather than a fixed z threshold.

**D. Optimal stopping numbers (check the implementation).** Leung and Li inputs theta 0, mu 8, sigma 0.3, r 0.05, c_s = c_b = 0.02 give exit b* = 0.198 and entry d* = -0.180 (the book charts show
about +/-0.17 to 0.2); with sigma 0.1 and 0.5, b* = 0.068 and 0.329 (Leung and Li, Optimal Mean Reversion Trading, 2016; `leung_li_levels` reproduces them).

## Signals & interpretation
- **Tier A (trade candidate)**: verdict OK, half-life 3-40 d with CI upper bound finite, |z| >= max(a*, 1.5), Sharpe_10d >= 0.5, positive confirmation that reversion has started
  (the signal turns toward the mean, e.g. 5-day average of the residual minus its 40-day average has the right sign; Tuckman and Serrat, 2022, and "cheap/rich to history, pay you to wait, started moving
  your way", Goldman Sachs desk material, 2026). Securities are often persistently cheap or rich, so require evidence that convergence has begun and pool trades to neutralise factor exposure.
- **Tier B (slow)**: half-life 40-90 d or one flag: only with carry-adjusted breakeven, smaller size, and a catalyst or fundamental reason.
- **Reject**: REJECT verdict, a recent break (rolling phi up, ADF no longer rejects, rolling half-life > 2x), a regime change in the driver (QE, central-bank policy, large forced flows: "rich can get richer and cheap cheaper"
  and a small dislocation "might be a harbinger of bigger things", During, 2021).
- Ask why it is rich or cheap before fading (a repo squeeze can intensify before easing) and whether the reversion has a source: anchoring or arbitrage, central-bank anchoring, overreaction,
  microstructure, or slow absorption of a supply shock (Brenndoerfer, 2025; Duffie, 2012). Statistics identify opportunities; they are not the trade rationale (swapsball.net, 2017).
- Cross-check the direct spread z-score, not only the model-implied one, when the residual is from a fitted curve (RiskVal, 2021).

## Pitfalls
- **Level vs change**: regressions on levels of autocorrelated series are spurious; a regression on changes cannot give a fair value. For level-based reversion check (1) local reversion, (2) where the long-run mean is, (3) the speed (swapsball.net, 2017).
- **Z-score without speed**: report half-life and ex-ante Sharpe with every z; with an unknown mean the sd is estimated, so a t-distribution is more apt (Huggins and Schaller 2024).
- **Look-ahead**: full-sample mean/sd or weights bias every statistic. Use trailing windows; a signal at t trades from t+1 (see [bt-backtest-design](../bt-backtest-design/SKILL.md)).
- **Window length**: long windows detect breaks slowly, short windows are noisy and over-trade the hedge (During, 2021).
- **Roll and benchmark switches** create fake slope or fly jumps; use constant-maturity or spline-fitted series (Huggins and Schaller 2024; During 2021). Futures rolls can create spurious reversion.
- **Bad quotes and bid-ask bounce** inflate reversion in back-tests (buy on a fictitious low print); cleanse first. Bounce makes a random walk look stationary.
- **Costs**: negative autocorrelation is harder to exploit net of costs; a back-test without costs, carry and stops is optimistic. Check the oracle first: E|x_{t+h} - x_t| on trigger days vs round-trip cost.
  A fade can be directionally right and still lose because moves barely exceed the round trip.
- **Thresholds are fitted hyper-parameters**: optimising them in-sample overfits; smooth the frequency curve, validate out of sample, record every trial (see [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md)).
- **Persistence regime**: reversion strength changes with regime (front-end futures became more mean-reverting as the hiking cycle neared neutral, J.P. Morgan, 3 Aug 2018) and relationships shift: the R^2 of a PC1 on a USD anchor
  was 0.47 before 2023 and 0.76 after for AUD/NZD-type pairs, which a full-period average hides (Citi Research, Asia FX and Rates Strategy: Decomposing Global Rate Drivers Across EM Asia 5y5y, 13 Aug 2026). Test for breaks: see [quant-regime-detection](../quant-regime-detection/SKILL.md).
  "Picking up dimes in front of a steamroller" (Aikin forum archive).
- **Extreme signals are adverse selection**: the biggest z often arrive in unprecedented dislocations (March 2020); winsorise at +/-2.5 sd_eq for sizing, cap exposure (Narang, 2024).
- **Sharpe inflation and Kelly**: parameter uncertainty always lowers the optimal fraction; size via [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).
- **Non-linear drift**: bucketing can reveal stronger reversion in the tails or higher tail variance; do not fit cubic drifts without a bucketing plot (they fit noise).
- **Real-world vs risk-neutral**: historical fits give real-world parameters; a model calibrated to bond prices gives risk-neutral ones. Do not mix them (Hull, ch.31). Equilibrium short-rate models (Vasicek) do not fit today's curve; see [curve-term-structure-models](../curve-term-structure-models/SKILL.md).
- **G10 notes**: USD short rates are indistinguishable from a unit root over decades (quarterly T-bill phi 0.969, ADF not rejected) (Hamilton, 1994) while curve spreads and swap-spread residuals revert; use residuals, not outright yields.
  Front-end futures vol varies about 10x between zero-rate and hiking regimes, so use robust VR and re-estimate sigma by regime; outright front-end levels follow a moving policy path, so fit spreads, flies and residuals rather than outrights. Post-benchmark-change
  or post-facility structural breaks (e.g. overnight-rate series after a standing repo facility) require re-estimation on the post-break sample only. EUR: a Bobl ASW ARMA forecast fitted on 2013-14 worked briefly, then failed when the QE-driven trend began (swapsball.net, 2017); fit EUR residuals per issuer and per regime. Cross-time-zone pairs (JPY, AUD, NZD with US legs): common snap or weekly closes. GBP, CAD, CHF, SEK, NOK: no market-specific OU evidence in the sources; fit per market.

## Output
Return one row per series (and a short note):
`package_id, snap, n, window_obs, mu_bp, sd_eq_bp, z, kappa_per_day, half_life_d (lo, hi), phi, adf_t, kpss, hurst, vr_10 (z*), verdict + reasons,
exp_move_bp(h=5,10,20), sharpe_h(10d), entry_z (max(a*,1.5)), entry_bp, target_bp, time_stop_d (3 x half-life), stat_stop_bp, breakeven_months (vs carry), cost_bp used`.
For the hand-off write `signals` rows: `value` = z, `unit` = z, `zscore`, `horizon_days` = half-life, `model_version` = window and method. Feed the verdict and Sharpe_h to
[rv-composite-scoring](../rv-composite-scoring/SKILL.md), and the levels and rationale to the trade write-up. State every assumption explicitly (mean, window, cost, discount rate r) and the parameter uncertainty
(half-life CI). If the verdict is REJECT, say so plainly and do not output levels.

## Scripts
- [`scripts/ou_fit.py`](scripts/ou_fit.py): `fit_ou` (OLS and closed-form MLE, CI), `rolling_ou`, `adf`, `kpss`, `hurst_std`, `variance_ratio`, `ou_expected_path`, `ou_sharpe`,
  `optimal_symmetric_band`, `leung_li_levels`, `fit_mvou`, `spread_is_ou`, `diagnose`.
  `python scripts/ou_fit.py diagnose data.csv --value-col value --group-col package_id --cost-bp 0.5`; `python scripts/ou_fit.py bands --kappa 0.063 --sigma 0.83 --cost 0.5`.
  `--selftest` checks simulated OU with known parameters (kappa, mu, sigma recovered; closed-form MLE equals OLS), ADF/KPSS equal to statsmodels, the analytic variance ratio, the erfi cycle time against quadrature, a brute-force grid and a Monte Carlo
  first-passage time, Leung-Li levels (0.198) and F(x)/F(b) against Monte Carlo, multivariate OU parameter recovery and the left-eigenvector test. Optional: statsmodels (p-values and cross-checks).

## Related skills
- [quant-cointegration](../quant-cointegration/SKILL.md): decides whether a level combination is cointegrated and supplies the weights and residual that this skill times
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score screens that this skill upgrades with reversion speed
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): general unit-root, ARMA and state-space tools
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): hedge ratios and residual diagnostics feeding the series
- [quant-regime-detection](../quant-regime-detection/SKILL.md): breaks and regimes that switch reversion off
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): half-life vs turnover and signal decay
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA residuals and PC-weighted flies
- [curve-butterflies](../curve-butterflies/SKILL.md) and [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): the structures being faded
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread and ASW residuals
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md) and [stir-futures-rv](../stir-futures-rv/SKILL.md): forward-grid and STIR fly residuals to be timed
- [bt-backtest-design](../bt-backtest-design/SKILL.md): causal (shifted) signals and back-test mechanics
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll for the breakeven rule
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): round-trip cost inputs
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): thresholds as hyper-parameters, trial counting
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): Vasicek / OU short-rate models and real-world vs risk-neutral parameters
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): shrinkage, priors and Bayesian updating.
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag and transmission between markets.

## References
- Leung and Li - Optimal Mean Reversion Trading: Mathematical Analysis and Practical Applications (World Scientific, 2016): OU/XOU/CIR MLE, optimal entry/exit/stop-loss/switching, futures under OU, numbers
- Huggins and Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): OU SDE and densities, z-score critique, ex-ante Sharpe, Stanton bucketing, MVOU, monitoring pipeline
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): half-life in phi, optimal trading rules on OU (profit-take/stop-loss mesh), structural-break tests, fractional differencing
- d'Aspremont - Identifying Small Mean Reverting Portfolios (arXiv 0708.3048, 2008): OU estimators, sparse baskets, US swap results, 1 bp cost reality check
- Cuturi and d'Aspremont - Mean-Reverting Portfolios: Tradeoffs Between Sparsity and Volatility (arXiv 1509.05954, 2015): mean-reversion proxies, variance floor, Jurek-Yang position rule
- Hamilton - Time Series Analysis (Princeton University Press, 1994): ADF/PP formulas and critical values, variance ratio, low power example, known-vector test
- Chan - Quantitative Trading (Wiley, 2009): half-life regression, exit-rule taxonomy, no-stop rule, backtest pitfalls
- Tsay - Analysis of Financial Time Series (3rd ed., Wiley, 2010): AR(1) half-life, ADF, cointegration band rule 2 Delta > eta, spurious rates regressions
- Greene - Econometric Analysis (8th ed., Pearson, 2018): Dickey-Fuller and KPSS critical values, Newey-West lag
- Wooldridge - Introductory Econometrics (2nd ed.): ADF specification, Engle-Granger critical values, T-bill error-correction example
- Dunis, Laws and Naim (eds) - Applied Quantitative Methods for Trading and Investment (Wiley, 2003): variance-ratio function, Burgess residual simulation
- Hasbrouck - Empirical Market Microstructure (NYU Stern notes, 2004): two-horizon variance ratio, bid-ask bounce, over-differencing
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): threshold optimisation, unit-root batteries, Kalman vs rolling hedge ratios
- Tuckman and Serrat - Fixed Income Securities (4th ed., Wiley, 2022): Vasicek closed forms, AR(1) residual convergence, fitting-error MA signal
- Hull - Options, Futures and Other Derivatives (9th ed., Pearson), ch.31: Vasicek/CIR estimation, real-world vs risk-neutral parameters
- BofA Merrill Lynch - Liquid Insight: A simple framework for swap spread relative value (2 Jun 2016): PCA residual half-life about 20 days, dislocation back-test
- BNP Paribas - G10 Interest Rates Focus: EUR curve convexity, Lessons from history (25 May 2021): fly residual episodes and overshoot
- ING Global Markets Research - Rates Strategy: Deconstructing the EUR yield curve (15 Jan 2020): reversion horizon vs carry breakeven
- bquanttrading blog - Principal Component Analysis Part II (2015, upd. 2016): OU on a PCA-weighted fly, half-life 11 days
- Ade Rhodes - Trade Idea: USD 5s30s Swap Spread Flattener (9 Oct 2025): z-bands, target/stop, holding-period study
- Salomon Brothers - Understanding the Yield Curve Part 7 (Ilmanen, Iwanowski, Feb 1996): levels vs spread mean reversion
- Citi Research - US Rates Weekly: Summer lull (17 Jul 2015); J.P. Morgan - US Fixed Income Markets Weekly: The long and short of it (3 Aug 2018): mean-reversion gauges
- Duering - Fixed Income Trading and Risk Management (Wiley, 2021): mean reversion vs trend, continuation risk; swapsball.net - Regression in finance: friend or foe? (27 Oct 2017): level vs change regressions, ASW regime failure
- Huggins and Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): OU fit of a basis residual, structural-break caveat
- Brenndoerfer - Mean Reversion and Statistical Arbitrage (Quantitative Finance handbook, 27 Dec 2025): AR(1)-to-OU mapping, z-score rules, regime controls
- Goldman Sachs FICC and Equities (desk material) - Global Rates Best Trade Report (30 Sep 2026): entry z, carry and trend screen logic
- Citi Research - Asia FX and Rates Strategy: Decomposing Global Rate Drivers Across EM Asia 5y5y (13 Aug 2026): regime break, weekly sampling for cross-time-zone pairs
- Narang - Inside the Black Box (3rd ed., Wiley, 2024): mean-reversion rationale, dislocation and adverse-selection risk
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): autocorrelation and Sharpe estimates, Sharpe standard error, parameter uncertainty and Kelly
- Duffie - Dark Markets (Princeton University Press, 2012): slow reversion after supply shocks
- RiskVal Financial Solutions - RiskVal Overview 201: Cash and Futures (12 Nov 2021): mean-reversion diagnostics, direct vs model-implied spread z-score
- Chakraborty and Kearns - Market Making and Mean Reversion (EC'11, ACM, 2011): ladder profit identity
- Quantitative Finance Stack Exchange - "Reproducing levels when PCA has been done on changes" (2015): cumulated-factor level residual and stationarity test
- Stephen Aikin - "Welcome to STIR futures" forum archive (2006-2014): regime dependence of range trading
- Bertram - Analytic solutions for optimal statistical arbitrage trading (Physica A, 2010) (external): cycle-time optimal OU bands
- Avellaneda and Lee - Statistical arbitrage in the US equities market (Quantitative Finance, 2010) (external): OU s-score
- Kwiatkowski, Phillips, Schmidt and Shin - Testing the null hypothesis of stationarity (Journal of Econometrics, 1992) (external): KPSS test
- Lo and MacKinlay - Stock market prices do not follow random walks (Review of Financial Studies, 1988) (external): variance-ratio test
