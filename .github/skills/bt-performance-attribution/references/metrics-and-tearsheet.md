# Metrics, benchmarks and tearsheet fields

Companion to [SKILL.md](../SKILL.md). `scripts/perf.py` implements the starred (*) items.

## 1. Definitions

| Metric | Definition | Source and caveat |
|---|---|---|
| Sharpe* | `mean(r - rf)/std(r)`; annualised x `sqrt(periods)`; units are time^-1/2 | iid assumption; with autocorrelation rho > 0 the naive annualised Sharpe is overstated, corrected SR ~ (1 - rho) x naive for small rho (Paleologo, The Elements of Quantitative Investing, 2025) |
| Annualisation | 252 or 251 trading days (swaps: `sqrt(251)` on daily bp changes, no rf; Burton, Dektor, Wheeler, Stanford, c.2008); 256 in one equity text | state it; hourly NYSE-hours strategy: 252 x 6.5 = 1,638 periods, not 252 x 24 (Chan, Quantitative Trading, 2009) |
| rf subtraction | only if the strategy incurs a financing cost; not for dollar-neutral, self-financing or unfunded swaps and futures | Chan 2009; with funded bonds, financing is already in P&L |
| Excess over cash | macro tearsheets measure returns as excess over 3m bills to replicate the funded return of a levered investor | Willer & Saunders, Trading Global Macro Markets, 2026 |
| IR | mean(excess over benchmark)/std(excess) = annualised residual return / residual risk; Sharpe = IR vs cash | IR is independent of aggressiveness until constraints bind; scales with sqrt(horizon), so quote annual (Grinold & Kahn, Active Portfolio Management, 2nd ed., 1999) |
| Active IR / % on | IR over periods in the market only, with the time in market | long-run comparisons: a rule on 27% of the time has R:R 0.53, active IR 1.01 (Willer & Saunders) |
| SE(Sharpe)* | `sqrt((1+SR_p^2/2)/T)` per period | t = SR x sqrt(years); 16 years to show IR 0.5 at t = 2 |
| Sortino* | mean excess / downside deviation | LPM / semivariance family in Palomar, Portfolio Optimization, 2025 |
| Drawdown* | loss from peak `DD_t = NAV_t - HWM_t <= 0` (additive) or `(1+cum)/(1+HWM) - 1` (compounded); sources print it as a positive magnitude, Chan uses `(1+HWM)/(1+cum) - 1` = HWM/NAV - 1, which exceeds the percentage loss | max DD = global max minus subsequent min; max DD duration = longest time to recover; the two usually do not overlap (Chan 2009) |
| Time under water* | time from an HWM until P&L exceeds it | report 95th-percentile DD and TuW (Lopez de Prado, Advances in Financial Machine Learning, 2018) |
| Calmar* / Sterling | excess return / max DD; Sterling = excess / (abs(max DD) + 10% of capital) | Palomar 2025 |
| Average DD, CDaR | mean drawdown, CVaR of drawdowns | prefer to max DD, which depends on one path point; CVaR at 99% with about 200 observations rests on 2 points |
| Hit rate* | `#positive/(#total - #flat)` | desk scorecards; average P/L in bp of yield for linear trades and abp for options (JPM, Global FI Markets Weekly, 21-22 Aug 2026) |
| Non-parametric ratio* | average of median/IQR, median return/median loss (Sterling-type), return/5th percentile | bootstrap random 50% subsets, 1,000 repeats (JPM, Zen and the art of gamma maintenance, 9 Mar 2018) |
| HHI concentration* | `h+ = (sum w^2 - 1/n)/(1 - 1/n)`, `w_i = r_i/sum r+` | ideal profile: low h+, h-, and h[t] of bets per month |
| TWRR | daily return = P&L / capital (prior dirty holdings + net new capital); link `phi = prod(1 + r_t)`; annualise `phi^(1/y) - 1` | GIPS convention (Lopez de Prado 2018) |
| Expected Sharpe (ex ante) | expected return / sigma of trade returns; linear: carry + rolldown + convexity; options: theta + vol slide + gamma | puts outrights, curves, flies, swaptions on one frontier screen; pair with realised delta/carry/convexity split (Citi, Holistic Approach to Convexity, Jun 2022) |
| Return on risk | P&L / risk, risk = largest 2-week change in the trade since a fixed start date | model portfolio of fixed size, mid marks incl. costs (Citi, US Rates Weekly, 2 Oct 2026) |
| Capital at risk | equal to the stop-loss level; typical 0.25-1% of portfolio per trade | Citi, EM Strategy Weekly, 20 Aug 2026; Citi, Macro tapas, 7 Aug 2026 |

Return definitions: average log <= geometric <= arithmetic; be consistent. Variances add over time if returns are
uncorrelated: annual risk = sqrt(12) x monthly. Compare horizons by repeating a 1-month trade 12 times (expected values add,
standard deviations grow with sqrt(N)). Cost amortisation: annualised TC = round-trip cost / holding period in years.

## 2. Calibration anchors

- Before-fee IR across managers: 90th percentile 1.0, 75th 0.5, median 0.0, 25th -0.5, 10th -1.0. US active bond funds:
  institutional 90th 1.81, 75th 0.89, median 0.01; mutual median -0.11 before fees, -0.86 after (Grinold & Kahn).
- A true IR 0.5 manager has positive alpha in 56% of months and 87% of 5-year windows. 20 tries gives roughly a 60% chance of
  at least one |t| >= 2 fluke (the source quotes 64%). IC tiers: good 0.05, great 0.10, world-class 0.15; above 0.20 is usually a faulty backtest.
- Breadth back-out `BR = (IR/IC)^2`: IR 0.27, IC 0.01 means about 700 independent bets per year. Reassessing annually but
  rebalancing monthly is one bet, not twelve. Direction hit rate to IC: `IC = 2*N1/N - 1` (IC 0.02 is 51% correct).
- Equity cross-section Sharpe grades (about 3,000 names, daily rebalanced; delay-1 / delay-0): average > 2.5 / 3.95,
  good > 3.0 / 4.5, excellent > 3.5 / 5.25, spectacular > 4.5 / 6.0. They do not transfer to rates RV (Tulchinsky et al., Finding Alphas, 2015).
- Chan heuristics: Sharpe < 1 not suitable stand-alone; profitable almost every month implies Sharpe > 2; almost every day > 3;
  drawdown > 10% or longer than 4 months signals low Sharpe; few trades a year cannot support a high Sharpe. Swap
  scale (Burton et al.): > 1 good, > 2 very good, > 3 outstanding.
- Benchmarks to quote beside any bond-strategy result: long-run UST since 1973 6.3% (IR 1.1 gross); excess over bills 1.66%
  (IR 0.3); drawdowns of excess return median -9.0%, 532 days to trough, 1,083 days to recover; two above 10% (1977-81
  -25.5%, 2020-23 -23.1%) (Willer & Saunders, 2026). Quote any 60/40-style benchmark with figure and sample (the same
  benchmark reads 0.49 / 0.55 / 0.53 / 0.65 across samples).
- Realised versus ex-ante tracking error: median ex-post 0.72% vs ex-ante 0.61% (perfect-correlation assumption shrinks ex ante).

## 3. Tearsheet fields

Minimum set for a systematic RV backtest:
1. Time range, `periods`, average capital or risk budget, denominator used for returns, capacity if known.
2. Return, vol, Sharpe with SE, Sortino, max DD, 95th-percentile DD, TuW, Calmar, skew, excess kurtosis.
3. Hit rate, average win / average loss (payoff ratio), average return of hits and misses, number of bets (a bet ends when
   flattened or flipped, so bets < trades), average holding period, annualised turnover, ratio of longs (about 0.5 for neutral).
4. Leverage (average dollar position / average capital), correlation to the underlying or to a hedged bond index.
5. Cost grid: P&L at 0x / 0.5x / 1x / 2x costs and break-even cost on gross DV01 traded (break-even costs of 1.21 / 1.63 /
   1.35bp per leg against 0.25bp charged for three headline books; Internal convexity-RV research handover).
6. Holding-period returns 1M / 3M / 6M / 12M / 5Y / 10Y / since inception (annualised beyond 12M), per signal: Return /
   Vol / IR / Max DD / Success ratio (JPM, Systematic rule based strategies, 6 Mar 2017).
7. Event-trade table per bucket: number of trades, average P&L (bp), success rate, annualised IR, cut by holding window,
   hedge type, maturity bucket, country, year (JPM, Follow the cash flow, 15 Sep 2015).
8. Edge tests of SKILL.md section 5: time long, IR vs long, controls, permutation percentile, regime table, smile.
9. Headline set for a systematic RV claim: deflated Sharpe and E[max Sharpe | null] at effective sample size, ex-direction
   Sharpe, cost grid, break-even cost, and trial log ([bt-validation-and-overfitting](../../bt-validation-and-overfitting/SKILL.md)).
10. Limitations list: mid marks, no margin/CSA/balance-sheet cost, same-close snap, no smile, vanna/volga ignored, funding ignored.

## 4. Strategy-health monitoring from P&L

- Exit or de-risk when accumulated P&L falls more than a pre-set amount from its high; set the anticipated maximum loss
  before starting; use in-sample drawdown size and duration as the benchmark for judging live underperformance (Tulchinsky et al.).
- Signs a strategy has stopped working: larger-than-normal drawdown, falling Sharpe, behaviour outside the historical box.
- Per-trade: predetermined profit target (after which the signal is reduced) and stop loss; capital at risk is the stop.
- Behavioural diagnostics (Golub (ed.), BlackRock's Guide to Fixed-Income Risk Management, 2023): disposition bias = daily
  P(realise a paper gain) vs P(realise a paper loss), 6-month rolling, with cost = subsequent 3-month performance of losers
  held versus winners reaped; endowment effect = annualised return by holding-period bucket (< 3m, 3-6m, ...). Measure
  before acting: a mean-reversion book can benefit from the disposition pattern.
- Crowding: 12m rolling beta of hedge-fund indices (fixed-income arbitrage, global macro) to the strategy; a high beta preceded
  drawdowns and had a significantly negative effect on next-3-month returns (JPM, Investment Strategies No. 31, 11 Jan 2007).

## 5. Regime-split attribution

- Rally / sell-off months: rally if the average G4 10Y swap total return is positive. Central-bank cycles: an easing or
  hiking regime starts one month before the first cut or hike and ends one month after the last; QE counts as easing
  (JPM, Systematic fixed income trading strategies, 13 Apr 2015).
- Vol x dispersion 2x2, USD regime by dollar index above/below its 55-day average with a one-day lag; report active IR per
  cell and unconditional. Example (market-neutral curve carry): 2.33 / 2.86 / 0.04 / 1.31 vs 1.90 unconditional;
  most strategies weak in low-vol / high-dispersion (Citi, QIS Corner, 20 Aug 2026).
- Carry vs capital gains: a cross-market 10y carry portfolio earned 5.0% = 3.2 carry + 1.8 capital gains; carry is stable
  across regimes while capital gains are directional (bull 1.19 vs bear -0.79 in the best-2 spread basket; JPM, Investment
  Strategies No. 15, 9 Mar 2006 and No. 31, 11 Jan 2007).
- Event-study decomposition: compare forward returns of the signal pick, the alternative pick and the benchmark on the same
  dates; report hit rate and t-statistic of pick minus alternative. It separates the claimed signal from a regime gate or
  leverage that actually drives the headline (FinLab, 3-Day Laggard Rule backtest, Jun 2026: spread t 1.33, not significant).

## 6. Hygiene before comparing series

- Missing data are NaN, not 0 ("0 is a valid alpha value"); otherwise demeaning and decay create spurious positions and P&L.
- Unsmooth marked or appraised series using first-order autocorrelation before comparing Sharpes.
- Judge on out-of-sample Sharpe and on the in-sample-to-out-of-sample decay, not in-sample P&L; true out-of-sample is forward
  tracking. Dominance by one market is a warning; check up vs down markets, hit counts and turnover (Grinold & Kahn ch.18).
- Price and data errors look like realised opportunities; never use data in a backtest that production could not have used that day.
- A source's text and table can disagree (decay "improved" drawdown while the table shows 5.82% -> 7.74%): check claims
  against numbers.
- Neutralisation trades return for IR and drawdown (5-day reversal, illustrative equity case: raw return 31.2%, IR 1.00, max DD
  39.2%; industry-neutral 10.2%, IR 1.37, DD 8.7%): compare after the same risk-factor neutralisation, not before.
