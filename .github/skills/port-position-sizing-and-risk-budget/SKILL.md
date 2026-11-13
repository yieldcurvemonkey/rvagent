---
name: port-position-sizing-and-risk-budget
description: 'Sizes G10 rates RV trades and budgets portfolio risk - inverse-vol DV01 sizing, risk-per-trade to stop, vol targeting (and why it does not tame tails), VaR limits, Kelly / fractional Kelly and conviction scaling, stops, targets and time stops, funding/margin/haircut/liquidity caps, drawdown and high-vol de-risking. Use when asked how big to put on a trade, DV01 budget or limit, risk per trade, size of a fly / curve / swap-spread / basis / STIR-spread / vol package, vol target, risk budget, VaR limit, Kelly or half-Kelly, stop-loss, take-profit, max loss, leverage, margin, haircut, scale in or out, cut risk in high vol, or "is this too big". Combining many trades into a book (risk parity, HRP, optimisers): port-portfolio-construction.'
---

# Position sizing and risk budget

A trade idea has no size until risk is measured, budgeted and capped. Rates RV packages (spreads, flies, basis) have
small, mean-reverting P&L and large notional, so the dangers are mis-measured risk (notional, DV01-neutral is not
factor-neutral), vol estimates that lag regime breaks, and funding or margin that binds before market risk does.
Default rule here: **constant risk per package, sized as the minimum of several independent constraints**, then
aggregated and checked at book level. Signal strength changes ranking and conviction; it changes size only within a
narrow band (see step 5).

## When to use
- "How big should the 2s5s10s / 5s30s / swap-spread / basis / STIR calendar be?" or "is this DV01 too large?"
- Setting a DV01, VaR, vol or drawdown budget for a book, desk or strategy; allocating risk across themes or currencies.
- Converting a stop level into size ("risk 0.5% to the stop"), or choosing stop / target / time-stop for a mean-reverting spread.
- Deciding whether to use vol targeting, Kelly, half-Kelly or conviction scaling, and how much.
- Checking funding, margin, haircut, balance-sheet or liquidity limits on a levered RV trade.
- Reducing risk in high-vol regimes, after losses, or ahead of events.

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) and
[schemas](../data-contract-and-adapters/references/schemas.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Current and proposed holdings, signed DV01 per leg and package | `positions` | daily, current + proposal | DV01 in ccy per bp, positive = long duration (receive fixed / long bond) |
| Par or zero rates by tenor (for bucket changes, package vol R, covariance Q) | `curve_par`, `curve_zero` | daily, >= 252 changes (>= 3y preferred for regime coverage) | one snap only; changes in bp, never levels |
| Package level series (spread, fly, basis in bp) for R and half-life | `curve_par`, `swap_spreads`, `basis_swaps`, `fut_quotes`, `stir_quotes` | daily, >= 1y | same units as the signal |
| Signals / z-scores / hit-rates for conviction | `signals` | daily | calibrated probability only if available |
| Implied vol for the stress switch | `vol_surface` | daily, 1y | normal vol, bp |
| P&L history for drawdown and realised-risk checks | `pnl` | daily | |
| Funding, haircut, initial margin, capital charge | `repo_rates` plus user-supplied margin / haircut / balance-sheet terms | current | never infer margin from price data |
| Risk limits, capital, risk appetite, stop level | user | current | ask if absent |

If an input is missing, ask the user or the data adapter. Never invent vol, margin or capital numbers.

## Method

### 1. Measure risk in the right unit
- Risk = standard deviation of P&L (symmetric, aggregates, forecastable; downside measures are not persistent).
  Cost of risk is variance (Grinold & Kahn, Active Portfolio Management, 1999).
- Strip every package to a signed DV01 vector S by bucket (ccy/bp) via [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md).
  Notional is not risk: short-dated swaps inflate it (CFTC OCE, Do Banks Hedge Using Interest Rate Swaps?, Apr 2023).
- P&L sd over h days = DV01 x sigma_daily(bp) x sqrt(h). 5bp/day over 63d is 40bp, so quarterly sd = 40 x DV01 (same source).
- Yield DV01 weights front and long-end bp equally although short rates are more volatile, so it overstates long-end
  sensitivity. Compare packages in vol-adjusted (or 5y-equivalent) DV01 (During, Fixed Income Trading and Risk Management, 2021).
- Book risk (CoVaR): `c = sqrt(S' Q S)`, Q = covariance of daily bucket changes in bp^2, horizon = Q's horizon (1 day).
  `VaR_5% = 1.645c`, `VaR_1% = 2.326c`. Same value in par, zero or forward risk if Q is transformed consistently.
  Assumes zero mean, normal, linear P&L, so keep horizons short and add a gamma / stress view elsewhere
  (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022).
- Estimating Q: use changes; >= 100 observations and >= n_buckets + 1; do not demean; default 252 days. Use EWMA
  (lambda 0.94, half-life ~11d) for monitoring, but for **limits and sizing use max(EWMA, 252d vol)**: limits tied to
  a trailing-year vol expand mechanically when a shock rolls out, giving the most risk when vol is lowest (Bassman,
  BAS/ML RateLab, 7 Oct 2009). Blend daily with weekly estimates for cross-market correlation (time zones bias daily
  betas down). Match estimation frequency to rebalance frequency (monthly data was best overall for monthly-rebalanced
  carry-to-risk spreads, daily/weekly better for cross-market pairs: J.P. Morgan, Investment Strategies No. 31, 11 Jan 2007). Shrinkage and factor models:
  [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md).
- Underestimating vol is worse than overestimating: optimisers and size rules exploit errors (Grinold & Kahn).

### 2. Package vol and the default size (inverse risk)
- R = annualised vol in bp of the package's weighted level (spread, fly or basis, in bp per unit DV01), from daily changes
  of the package, floor at the 1y value.
- `DV01 = min(target_vol_ccy / R, DV01_cap)`. Defaults from the user's own backtests: target vol 250k ccy per package per
  year, cap 50k DV01. R = 12.5bp -> 250k/12.5 = 20k DV01 (cap would bind below R = 5bp). Scale target and cap to capital;
  they are scales, not truths.
- Optional book vol target: rescale all packages by k = target / c_book (126-day covariance with Ledoit-Wolf shrinkage is the
  user's backtest default) **only at entries and rolls**, not daily, to avoid turnover.
- Equal risk beats scaling by signal in the one controlled test: carry-to-risk spreads at constant 100bp annualised risk
  per trade had IR 0.94 / 1.10 / 1.00 for 1 / 2 / 3 trades versus 0.60 / 0.53 / 0.45 when scaled by carry-to-risk
  level (J.P. Morgan, Investment Strategies No. 31, 2007). Do not lever up on signal strength by default.

### 3. Stop-based size (risk per trade)
- `DV01_stop = risk_budget_ccy / stop_distance_bp`. Risk per trade is typically 0.25-1% of portfolio, measured to the
  stop or "watch" level (Citi, Macro tapas, 7 Aug 2026). Non-rates form: size = risk % / stop % x portfolio
  (2% stop, 0.5% risk -> 25% of portfolio; Citi, EM Strategy Weekly, 20 Aug 2026).
- Set the stop first from the thesis or model, then size from it. For mean-reverting spreads the stop is on the adverse side,
  >= 2 stationary sd from the mean (`sd_stat = sigma / sqrt(2 kappa)`, kappa = reversion speed per year) and always beyond the entry level,
  or the level that invalidates the thesis. Default vol stop used in the user's backtests:
  adverse move >= 1.5 x R x sqrt(max_hold/252) per unit DV01 (R = 12.5bp, 63d -> 9.4bp). With inverse-risk sizing the
  loss at the stop is then `0.75 x target_vol`. Stop level and size are one decision: a wider stop means a smaller DV01.
- Accept only if reward/risk >= ~1.5 to the target (Citi, Trade Ideas Radar, 13 Aug 2026). Break-even hit rate = 1 / (1 + reward/risk)
  (R/R 1.5 -> 40%); compare it with the realised hit rate of the signal bucket, not with a hoped-for one.

### 4. Binding constraint = minimum of
| Constraint | Formula | Source / default |
|---|---|---|
| Inverse risk | target_vol / R | step 2 |
| Stop risk | risk budget / stop bp | step 3 |
| Book headroom | DV01 s.t. c_book after add <= limit (Euler marginal, step 7) | user limit |
| VaR limit | VaR limit / (k x daily sd bp x DV01 per mm), k = 3 | Bassman 2009: $10mm limit, 174 normal vol, $863/mm -> $352mm |
| Liquidity | size <= executable block; cost ~ size^1.5 | step 10 |
| Funding / margin | stressed cash need <= free liquidity buffer | step 10 |
| Capital / ROE | ROE after balance-sheet cost >= hurdle | [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md) |
Report which constraint binds; that is the useful information.

### 5. Signal strength, conviction and Kelly
- Default: constant risk (step 2). Optional signal scaling `inverse_risk x min(|S|/s_in, 2)` caps at 2x; use only if a
  hit-rate-by-bucket table shows monotone payoff, and discount for the fact that scaling lost to constant risk above.
- Probability to size (symmetric payoff): Kelly `S = 2P - 1` (P > 0.5); or `z = (p - 0.5)/sqrt(p(1-p))`, `m = 2 Phi(z) - 1`
  (Lopez de Prado, Advances in Financial Machine Learning, 2018). Average the sizes of overlapping active bets and
  discretise `m* = round(m/d) d` with d = 0.2 to avoid churn. Cap or winsorise the largest signals: they tend to arrive late in trends or at dislocations (Narang, Inside the Black Box, 2024).
  Keep reserve: do not start at full size
  (scale in thirds; a forced cut after an adverse move turned two correct forecasts into a loss in the book's example).
  Symmetric Kelly does not fit skewed payoffs (options, convexity packages).
- Growth-optimal (Kelly) leverage `f = mu / sigma^2 = SR / sigma` for excess return mu and vol sigma per period.
  Sharpe errors are magnified: vol 19%, SR 0.84 -> 4.4x; with parameter uncertainty `f = mu/(mu^2 + sigma^2 + tau^2)` is always lower
  (mu 0.08, sigma 0.19: plug-in 2.22; second-moment form 1.88; 1.81 with tau_mu 0.04, 1.52 with tau_sigma 0.1; Paleologo, The Elements of Quantitative Investing, 2025).
  Compounded growth is ~ Sharpe^2 / 2, so maximise Sharpe first and lever second (Chan, Quantitative Trading, 2009).
- Default: **quarter to half Kelly, then capped at tolerable one-period drawdown / worst historical one-period loss**
  (Chan, Quantitative Trading, 2009). Mean estimates are the bottleneck (error > 100% at N=100, T=500; Palomar, Portfolio
  Optimization, 2025), so in rates the stop-risk and funding constraints almost always bind first.
- Book-level aggressiveness: optimal risk `omega* = IR / (2 lambda)`, lambda 0.05 / 0.10 / 0.15 = low / moderate / high
  aversion. IR 0.5 and lambda 0.10 -> 2.5% annual risk on capital. Use a shrunk IR (0.5 good, 0.75 very good, 1.0 exceptional;
  an IR far above 2 on public information signals a faulty backtest). Rescale over-confident alphas first (Grinold & Kahn).

### 6. Vol targeting: use it for scale, not for tails
- Rule: compare recent realised vol to target, lever down when higher, up when lower, rebalance monthly. It lifts Sharpe a
  little for bonds (US 7-10y 0.40 -> 0.46) but does not fix tails: targeting a 5y IRS receiver at 10% (EWMA half-life 11d,
  monthly) raised excess kurtosis 2.4 -> 2.9 and enlarged outliers in most countries (Macrosynergy, Interest rate swap
  returns: empirical lessons). Trailing realised vol is low just before crises; implied-vol cut-outs worked better
  (Willer & Saunders, Trading Global Macro Markets, 2026).
- Stress switch (default): gauge = max over equity, rates, oil, G10 and EM FX implied vols and HY credit spreads of their 1y z-score
  (Willer & Saunders tested it as a credit cut-out; use for rates is the agent's judgement). If > 2,
  cut new risk to 50% (ING halved a EUR fly's risk allocation in high vol; Rates Strategy, 9 Mar 2020); re-enter when < 2;
  hold at least a month for illiquid positions. Do not open a package when implied vol has jumped sharply over the last ~10 days
  (do not sell into a spike). Calibrate the threshold to time-in-market, not just IR (a max-of-z
  gauge exceeds 2 often). Bonds: only extreme vol quintiles hurt; reduce size when vol is rising.
- Spread-level overlay: when a spread's daily vol doubles (1.2bp -> > 2bp over a week), overlay swap spreads or move to
  same-issuer / more liquid legs (Astor Ridge, Trade Radar, 6 Mar 2022).
- Crowding kill-switch: a high rolling 12-month beta of fixed-income-arbitrage / macro hedge-fund returns to the carry strategy preceded
  the LTCM and 2001 drawdowns; cut carry-type packages when it is high (J.P. Morgan 2007).
- Size asymmetrically when the likely regime shift agrees with RV (larger) or conflicts (smaller); hedge regime
  exposure at book level, since the desk's mean-reversion trades share it (Tuckman, Lehman LMR, Oct 2003).

### 7. Book aggregation and risk budget
- Aggregate in one currency (USD): convert every bucket first; cross-currency basis risk is its own bucket.
- Euler contributions: `RC_i = w_i (Sigma w)_i / sqrt(w' Sigma w)`; they sum to c. Negative contribution = diversifier; do not cut
  it for risk reduction (Darbyshire 2022). Risk budgets b_i (sum 1): `w_i (Sigma w)_i = b_i w' Sigma w`; naive solution `w_i ~ sqrt(b_i)/sigma_i`
  (inverse vol; exact only for equal budgets b_i = 1/N AND equal correlations) (Palomar 2025). For many correlated sleeves use hierarchical risk
  parity or inverse variance, not covariance inversion (out-of-sample variance 0.0671 vs 0.0928 vs 0.1157 for
  HRP, IVP, CLA; Lopez de Prado 2018). Allocation logic: [port-portfolio-construction](../port-portfolio-construction/SKILL.md).
- Correlated spreads are often one trade (several STIR calendars; flies sharing a belly): aggregate before applying the
  budget and err lower. Diversify across themes: 50/50 curve and cross-market (best two of each) IR 1.33 versus 1.06
  best across both; curve versus cross-market return correlation 0.06 (J.P. Morgan 2007). 1 -> 2 trades helps,
  more adds little.
- Structure risk per unit DV01 differs by a factor of 3-5: spreads and flies carry roughly a third or less of an outright's
  risk. Size by c, not by DV01 (worked example).
- Agent defaults (judgement, tune to mandate): flag any package with RC_i > 35% of c; flag book c above 80% of limit;
  flag Herfindahl of relative risk contributions > 0.4; flag a currency block > 50% of c.
- Factor view: DV01-neutral is not factor-neutral. PC1 loadings are humped (0.279 at 2Y, 0.334 at 7Y, 0.272 at 50Y), so a
  DV01-neutral package keeps 3.8-16.7% of an outright's level exposure (user's own research). State level / slope / curvature
  variance shares before quoting P&L; PC1-neutral weights on tight pairs cut level risk 66-96% and kept 67-89% of P&L,
  but PC1+PC2-neutral on 5Y/30Y turned into a slope bet. Compare walk-forward and full-sample PCA weights: a large gap means you
  are trading the estimator. See [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md), [curve-butterflies](../curve-butterflies/SKILL.md).

### 8. Hedge sizing
- VaR-minimising trade in buckets i: `t = -(Q_ii)^-1 (Q S)_i`. A single-bucket hedge is easiest to execute and often nearly as good.
  **Only one single-instrument VaR-minimising trade is valid at a time**; doing several at full size can raise VaR, so trade
  ~50% of each and re-run (Darbyshire 2022). If the best single hedge cuts c by only ~15%, risk is RV-dominated, not directional.
- Hedge ratios are noisy: with beta error, shrink the hedge `y* = 1 - w'Omega_eta w / (w'beta)^2`, floor at 0 (never hedge the wrong way)
  (Paleologo 2025). A DV01 hedge assumes beta = 1 and is meaningless across markets or very different maturities (During 2021).
- Neutrality is instantaneous: DV01 decays with ageing and convexity breaks hedges. Re-hedge on a schedule, size with forward
  DV01 over the holding horizon.

### 9. Stops, targets, time exits
- Four ingredients of every trade: rationale; target and stop (so capital at risk is computable); an exit plan with cost; sizes
  consistent with the analysis (During 2021). Name one invalidation condition; if you cannot name the repricing, size down (Global Macro Method, Feb 2026).
- Mean-reverting spreads: Ornstein-Uhlenbeck (OU) half-life `ln2 / kappa`. If half-life << holding horizon, a small target with a
  wide stop has the best Sharpe; tight stop with wide target is worst; with half-life ~ 100 observations the heat-map is flat (SR 0.8 at 50, 0.32 at 100), so
  calibrating stop and target there is overfitting (Lopez de Prado 2018). Target about half-way to the mean or tighter (Huggins &
  Schaller, Fixed Income Relative Value Analysis, 2024). A stop at or above the OU boundary L* ~ mean destroys the trade, and entry
  should be inside the band above the stop (Leung & Li, Optimal Mean Reversion Trading, 2016); derive thresholds, not ad hoc +/-1 sd.
  Fit and thresholds: [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md).
- Time stop: max hold 63 trading days (tuned over {21, 42, 63, 126}) in the user's backtests; if the half-life exceeds the
  holding horizon the trade may not revert in time (judgement: size smaller or skip).
- Trailing: raise the stop by the same amount as P&L rises; when the target is hit, move the stop to the target and set a
  new one (During 2021). Take profit once mean reversion has worked and on winners with ~0 VaR contribution.
- Stops gap and fill worse; they help in momentum regimes and in squeezable shorts ("no maximum loss on a squeezed basis short"),
  and they are a poor fit for pure reversal entries (Chan 2009; Burghardt et al., The Treasury Bond Basis, 2005). Erroneous
  (data / ops) positions are exited at once.
- Book stops: strategy drawdown stop 10-15% (stat-arb practice; Brenndoerfer, Mean Reversion and Statistical Arbitrage, 2025);
  de-lever gradually as trailing edge decays (trailing Kelly) rather than switching off. Do not re-tune parameters after one loss.
- Event discipline: weight event days in the VaR horizon (10y IRS sd 4bp, payrolls Friday x2 -> weekly sd sqrt(4x16 + 4x16)=11.3bp,
  95% bound 18.6bp; Darbyshire 2022). Trim before sessions you cannot monitor; stand aside from "deep play" volatility
  (Aikin, STIR Futures, 2012). Gap risk is why traders cut into the close.

### 10. Funding, margin, capital and liquidity
- **Never size off margin.** A calendar spread with ~$160 initial margin "allows" > 6,000 spreads; 1 tick = $25 each = $150k per tick
  = 15% of a $1M account (Aikin, Welcome to STIR futures forum, 2006-14). Margin offsets (SOFR futures vs swaps up to 78%,
  UST futures vs swaps 50-65%, EUR 41%, GBP 46%, CAD/AUD 50%) are maxima, not planning numbers (Coalition Greenwich, Q4 2024).
- Haircut = leverage. Size levered RV for haircut stress, especially when a CCP can change haircuts unilaterally
  (peripheral EGB haircuts 3% -> 80% in July 2011; a limit sized for a 15% haircut would have survived; Tuckman & Serrat, Fixed Income
  Securities, 4th ed., 2022). Hedges of price risk do not hedge margin risk. See [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md).
- Stressed cash need = (worst plausible 1-day adverse move x DV01) + increase in initial margin + haircut change. It must
  be below free liquidity, and the single-day loss must not breach the loss limit that forces exit. Convergence trades
  can be right and still closed out: a $1bn Treasury basis trade expected $2.5mm P&L but needed ~$4mm cash in one day (Tuckman & Serrat 2022). 20:1 leverage was the
  assumed norm; 10:1 / 20:1 / 25:1 simulations gave worst-case -> +2.3% / -1.9% / -4.0% (Burghardt et al. 2005;
  [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md)).
- Balance sheet: equity = SLR x (gross notional + haircut + IM + PFE); a 10y swap-spread widener had ROE 35% at 1% SLR down to
  ~6% at 6% (Boyarchenko et al., Negative Swap Spreads, FRBNY Economic Policy Review, Oct 2018). Compare trades on return on capital
  used, not P&L. See [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md).
- Liquidity: cost ~ sigma x sqrt(size / ADV), total cost ~ size^1.5; "it costs roughly one day's volatility to trade one day's volume"
  (Grinold & Kahn). A known oversized position invites predators and hedging by adding offsetting trades grows gross size: a
  position > 10 days of ADV was the warning in the London Whale case (Tuckman & Serrat 2022). 200mm 10y GBP IRS (typical 25-50mm)
  quoted 1.25bp from mid, mid moved ~2bp, repeats 1.75bp (Darbyshire 2022). Costs and capacity:
  [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md).
- Check sparse-portfolio edge against costs: 1bp bid-offer fully neutralised out-of-sample Sharpe for sparse mean-reverting baskets
  (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008).

## Worked example

**A. Inverse-risk size plus vol stop** (user's backtest defaults). Package R = 12.5bp/yr. DV01 = 250k/12.5 = 20k. Stop at 1.5 x 12.5 x
sqrt(63/252) = 9.4bp adverse -> loss at stop 20k x 9.4 = 187.5k = 0.75 x 250k. On $100mm that is 0.19% of capital, BELOW the usual 0.25-1% risk-per-trade band (it reaches 0.25% at a target vol of ~333k and 1% at ~1.33mm),
so scale the target to capital and mandate; the 50k cap binds for R < 5bp (low-vol packages are not given unbounded size).

**B. Risk budget to DV01** (Citi, Macro tapas, 7 Aug 2026). Receive an FOMC-date OIS at 3.8075%, watch level 3.91%, target 3.63%, 50k DV01,
risk $500k = 0.5% of a $100mm portfolio. Check: (3.91 - 3.8075) = 10.25bp x 50k = $512k, consistent. Reward/risk to target = 17.75/10.25 = 1.7 (>= 1.5 hurdle).
(The source's table lists a different contract and 25k DV01; use the text figures.)

**C. Size by c, not DV01** (Darbyshire 2022, Example 16.1; covariance in bp^2/day across 2Y/5Y/10Y/30Y). One-day c in 000s for 100k-DV01 legs:
10Y outright 452; 5s10s 164; 2s5s10s (-50, 100, -50) 149; 5s10s30s 123; 2s5s/10s30s 238; 2s5s10s30s 91. A flat 100k DV01 leg would therefore give the outright 3-5x
the risk of curve packages. Equal-risk (c = 100k/day) sizes: outright 22k DV01, 5s10s 61k per leg, 2s5s10s belly 67k. Hence the sizing rule in step 2.
The script reproduces these numbers.

**D. Euler allocation and best hedge** (same source, S = -10,000 / 2,500 / 10,000 / -4,000 in book sign, c = 16,174 with the published unrounded
covariance). Contributions 2Y 15,787; 5Y -2,602; 10Y 1,437; 30Y 1,552 (sum = c): risk is almost entirely 2Y, the 5Y is a diversifier. Best single trades cut c by
15.6% (2Y), 7.7% (5Y), 0.2% (10Y), 4.1% (30Y); a two-instrument 2Y and 10Y hedge cuts ~70%. Signs flip in this skill's convention.

More cases (Kelly arithmetic, OU stop numbers, strategy-risk binomial, basis-trade margin path, MF Global, per-currency notes):
[worked examples](references/worked-examples.md) and [formulas and market notes](references/market-notes-and-formulas.md).

## Signals & interpretation
| Observation | Reading | Action |
|---|---|---|
| Best single VaR-minimising hedge cuts c < ~15% | risk is RV / combination risk, not direction | trade ~50% of the suggested hedge, use spread/fly hedges |
| All suggested hedges share a sign | they only fix directionality | size the RV legs, not the net delta |
| Recent (EWMA) vol > 1.5 x 1y vol | regime shift | use the larger vol; consider the stress switch |
| Spread daily vol doubles over ~1 week | jump regime (spread-vol rule) | overlay or move to liquid same-issuer legs |
| Stress gauge (max 1y z of implied vols) > 2 | high-vol regime | new risk at 50%; re-enter below 2 |
| Package RC_i > 35% of c or Herfindahl > 0.4 | concentration (agent default) | cut or hedge the contributor |
| Stop reached / thesis invalidated | trade wrong | exit; do not double down, do not re-tune after one loss |
| Half-life > max hold (63d) | may not revert in time | smaller size or skip |
| Trailing-year two-sided exceedances of 2 sd > ~5% (normal gives 4.6%) | risk model understates | widen vol, add a tail term; check regime |
| Stressed cash need > free liquidity | funding binds | cut size until it holds |
| Realised P&L attribution is almost all one factor | package is a disguised directional bet | re-weight (PC-neutral) or label it as such |

## Pitfalls
- Sizing off margin, notional or "what the dealer will finance". Margin is for the clearer's risk, not yours.
- Treating DV01-neutral as hedged: factor exposure remains; weights can be unstable (PC1-neutral 5Y/30Y: +1408bp walk-forward vs -66bp full-sample).
- Pro-cyclical limits from trailing vol; trailing realised vol targeting that is low before crises; vol targeting that raises kurtosis.
- Overfitting stops, targets and sizing rules. Sizing-rule comparisons need deflated Sharpe at effective sample size (n_eff ~7.5 per
  structure in the user's test); report such results as exposure results. See [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).
- High-n, asymmetric-payoff strategies are very sensitive to precision (hit rate 0.70 -> 0.67 wipes out the profit in the binomial example); test precision uncertainty, not only the point estimate.
- Kelly with estimated parameters, full Kelly, or levering a high-Sharpe backtest; Kelly-driven deleveraging is itself a contagion channel (August 2007).
- Correlation is not constant: STIR correlations 0.95+ in 2008-11 and negative in 2011 when the ECB diverged; crowded unwind moved correlations from 0.1-0.3 to 0.7-0.95.
- Stale or asynchronous prices understate vol and correlation and over-allocate to illiquid positions; front-month STIR spreads lock into cash and understate risk.
- Counting conventions: some risk systems count a 100-lot spread as two 100-lot outrights while exchange margin treats it as ~25% of an outright; check how limits count packages.
- Doubling up when down (paper losses induce risk-seeking); measure the disposition effect (probability of realising gains versus losses) rather than assuming it.
- Using backtest IR or IC at face value (IC > 0.20 usually means a faulty backtest; IR above 2 on public information).
- Mixing sign conventions: Darbyshire's book uses positive = pay fixed; this skill uses positive = long duration. c is sign-invariant, hedge trades are not.

## Output
Return two tables and a note, then hand to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) (Sizing section) and
[rv-trade-monitoring](../rv-trade-monitoring/SKILL.md) (stop, target, time-stop levels).
1. **Package sizing** (one row per package): `package_id`, structure, ccy, leg DV01 and notional or contracts, R (bp/yr) and its window, DV01 under each constraint
   (inverse risk, stop, book headroom, VaR limit, liquidity, funding), **binding constraint**, final DV01, stop / target / time-stop levels, loss at stop in ccy and % of capital,
   reward/risk, standalone c, Euler contribution, stressed cash need.
2. **Book risk**: c, VaR 95 and 99 (state normal-model caveat), DV01 by currency and bucket, top contributors, diversification ratio (c versus sum of standalone),
   level / slope / curvature variance shares, limit headroom, flags from Signals & interpretation.
3. **Note**: estimator used (window, EWMA, shrinkage), assumptions, anything estimated from fewer than 100 observations, and which defaults are the agent's judgement versus sourced.
Never present a size without the binding constraint and the stop-loss in ccy.

## Scripts
- [`scripts/sizing.py`](scripts/sizing.py): inverse-risk DV01, stop-based DV01 and vol-stop distance, EWMA vol, CoVaR / VaR, Euler allocation, VaR-minimising and
  best single hedges, VaR-limit and STIR VaR sizing, Kelly (single, multi, with uncertainty, with drawdown cap), Cantelli bound, bucket covariance from `curve_par`.
  `python scripts/sizing.py --help`. `--selftest` checks published values (structure risk table, Kelly cases, desk VaR sizing), analytic hedge and allocation identities, and a simulated
  covariance recovered through the `curve_par` pipeline.

## Related skills
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 vectors, par/zero/key-rate transforms feeding S
- [port-portfolio-construction](../port-portfolio-construction/SKILL.md): combining sized packages, risk parity, factor neutrality
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): stress and tail views that complement normal CoVaR
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): shrinkage, EWMA, factor covariance for Q
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md), [curve-butterflies](../curve-butterflies/SKILL.md): factor-neutral weights, directionality
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life, optimal entry and exit thresholds
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC, IR, breadth, conviction
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): impact, capacity
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md), [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md), [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): capital, margin, funding limits
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): leveraged basis sizing
- [quant-regime-detection](../quant-regime-detection/SKILL.md): regime flags for de-risking
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): testing sizing and stop rules honestly
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md), [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), [rv-devils-advocate](../rv-devils-advocate/SKILL.md): consumers of the sizing output
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): noisy betas, hedge-ratio estimation
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): leg weights, clip sizes, contracts per package
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event-day risk and stand-aside rules
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md), [stir-futures-rv](../stir-futures-rv/SKILL.md): carry-to-vol ranking and STIR spread packages
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables

## References
- Darbyshire, J.H.M. - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): CoVaR, Euler allocation, VaR-minimising hedges, structure risk table, event-day VaR, sqrt-impact size cost
- Grinold, R. and Kahn, R. - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): risk as sd, omega* = IR/(2 lambda), fundamental law, cost and turnover rules, risk-model validation
- J.P. Morgan Securities - Investment Strategies No. 31: Exploiting carry with cross-market and curve bond trades (Panigirtzoglou, 11 Jan 2007): constant 100bp risk beats variable risk, diversification, crowding beta
- Tuckman, B. and Serrat, A. - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): haircut-sized leverage (MF Global), March 2020 basis-trade margin path, size versus ADV, regression-hedge sizing
- Paleologo, G. - The Elements of Quantitative Investing (Wiley, 2025): Kelly under parameter uncertainty, vol-cap sizing, Cantelli bound, noisy-beta hedge shrinkage
- Chan, E. - Quantitative Trading (Wiley, 2009): Kelly and half-Kelly, drawdown leverage cap, rebalancing, stop-loss by regime, oversizing cases
- Willer, D. and Saunders, A. - Trading Global Macro Markets (Wiley, 2026): vol-targeting evidence, max-z stress switch, carry-to-vol sizing, vol-matched cross-market trades
- Lopez de Prado, M. - Advances in Financial Machine Learning (Wiley, 2018): bet sizing from probability, optimal PT/SL mesh, strategy-risk binomial, HRP
- Huggins, D. and Schaller, C. - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): OU ex-ante Sharpe, first-passage stop/target design, targets at half-way to the mean
- Leung, T. and Li, X. - Optimal Mean Reversion Trading (World Scientific, 2016): stop-loss effect on take-profit and entry band
- Palomar, D. - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): Euler risk contributions, risk budgeting, Kelly, practical constraints
- Bassman, H. (BAS/ML RateLab) - VAR: Driving while looking in the Rearview Mirror (7 Oct 2009): VaR-limit sizing formula and pro-cyclical limits
- Citi Research - Macro tapas (7 Aug 2026), Global Macro Trade Ideas Radar (13 Aug 2026), EM Strategy Weekly (20 Aug 2026), US Rates Weekly (18 Jan 2019): risk per trade to stop, DV01-sized trades, R/R hurdle, return-on-risk convention
- ING Global Markets Research - Rates Strategy: March ECB, QE or bust (9 Mar 2020): 50% risk allocation in high vol, entry/target/stop on a PC1-neutral fly
- Macrosynergy - Interest rate swap returns: empirical lessons (R. Sueppel): vol targeting test and cross-market vol/correlation by currency
- Aikin, S. - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012), and "Welcome to STIR futures" forum posts: VaR sizing of spreads, margin trap, SPAN, deep play
- Burghardt, G. et al. - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): leveraged basis-fund simulation, squeeze controls and stops
- Boyarchenko, Gupta, Steele, Yen - Negative Swap Spreads (FRBNY Economic Policy Review 24(2), Oct 2018): SLR equity charge, ROE and breakeven spread
- CFTC Market Risk Advisory Committee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): leverage, margin and liquidity-buffer practices
- McPhail, Schnabl, Tuckman - Do Banks Hedge Using Interest Rate Swaps? (CFTC OCE Staff Paper, 10 Apr 2023): DV01 to P&L vol, notional is not risk
- Coalition Greenwich - The Portfolio Margining Imperative for Interest-Rate Derivatives (Q4 2024): margin-offset maxima by currency
- Tuckman, B. - Macro-Awareness in Relative Value Trading (Lehman Brothers LMR Quarterly, Oct 2003): regime-aware asymmetric sizing and book-level hedging
- Musaelian, Nagarajan, Villani - PCA: invariant risk metrics and representation of residuals for bond returns (SSRN 2777026, 2016): delta-plus-gamma PCA risk limit, flylets
- Golub, B. (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): risk decomposition, PC1 duration for curve trades, covariance pitfalls
- During, A. - Fixed Income Trading and Risk Management (Wiley, 2021): vol-adjusted DV01, four ingredients of a trade, trailing stops
- d'Aspremont, A. - Identifying Small Mean Reverting Portfolios (Quantitative Finance, 2011; arXiv 2008): OU leverage, cost hurdle
- Brenndoerfer, M. - Mean Reversion and Statistical Arbitrage (online handbook chapter, 27 Dec 2025): z-stops, drawdown stop, leverage cap
- Astor Ridge - Trade Radar: Trades & Fades (6 Mar 2022): spread-vol-doubling overlay
- Narang, R. - Inside the Black Box (3rd ed., Wiley, 2024): capping the largest signals
- Global Macro Method (Substack) - STIR (Rates) Application Process (Lite) (25 Feb 2026): one invalidation condition per trade
- Also cited in the references/ files: Tsay, Analysis of Financial Time Series (3rd ed., Wiley, 2010); Golub and Tilman, Risk Management: Approaches for Fixed Income Markets (Wiley, 2000); Salomon Brothers, Understanding the Yield Curve Part 4 (Aug 1995); J.P. Morgan, Do androids dream of electric bonds? (22 Nov 2017), Update on systematic rule based trading strategies (2017-18) and TradeRunner (16 Aug 2018); Goldman Sachs, Global Rates Best Trade Report (30 Sep 2026); Conks, Demystifying the Repo Market Part III (28 May 2024); Quantitative Finance Stack Exchange thread on adjusting a 2s5s10s fly for directionality (2018-21)
