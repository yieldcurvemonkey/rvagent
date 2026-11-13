# Engine test battery, controls and run discipline

Companion to [SKILL.md](../SKILL.md) section 9. The script [`scripts/backtest.py`](../scripts/backtest.py) implements
the panel-engine subset (T1-T8 in its `--selftest`). A repricing engine needs the full list. Rule for every check: **run
it first on an input whose answer you know, then break the code on purpose and confirm the check fails.**

## 1. Look-ahead and timing tests
| Test | Procedure | Pass criterion |
|---|---|---|
| Truncation (Chan, Quantitative Trading, 2009) | Run on full data -> positions A. Drop the last N = 10-100 days, rerun -> B. Drop the last N rows of A | A == B on the overlap. Any difference is look-ahead (e.g. full-sample z, regression fitted on the whole sample, 'buy within 1% of the day's low') |
| Lag sweep | Execution lag 0 (diagnostic), 1, 2, 3, 5 | Performance degrades smoothly with lag. A 1-day delay that *improves* results = signal is early (Narang: +746% -> +870%). A rule that works only contemporaneously is suspect (Willer & Saunders) |
| Look-ahead injection | Feed tomorrow's change into the signal | Sharpe must rise sharply, proving the harness can see leakage |
| Date permutation | Permute daily sizing/decisions across days thousands of times (3,000) at a fixed sell fraction (JPM, Androids, 2017; TradeRunner, 2018) | Actual Sharpe above the 95th / 99.9th percentile of shuffled Sharpes; residual Sharpe = Sharpe - percentile. Tests timing skill beyond being long; penalises high-kurtosis tenors in small samples |
| Random entry | 1,000 random entry dates with the same exit rule | p-value of the real result |
| Inverted signal | Multiply the signal by -1 | Must lose (about the same magnitude on a symmetric rule) |
| Null instrument | Run where no relationship should exist (random data; a series with a known unbiased random walk) | No profit: an unbiased random walk is a martingale, E[profit] = 0 for every algorithm (Chakraborty & Kearns, Market Making and Mean Reversion, 2011). Test sophisticated methods on random data: finding predictability is a bug (Grinold & Kahn ch.10) |
| Weaker-effect control and leave-one-out | Add an instrument where the effect should be weaker; delete each instrument in turn (Finding Alphas, 2015) | Ordering as expected; result not driven by one instrument |
| Time-zone check | Same rule with 1- vs 2-day lag when legs have different closes | No collapse; blend daily and weekly betas |

## 2. Accounting and unit tests (known answers)
| Id | Setup | Expected |
|---|---|---|
| T1 | Flat strip, zero moves | Curve P&L 0 to 1e-9; option leg theta only |
| T2/T3 | Monte Carlo daily delta hedge of a Bachelier straddle, 5,000 paths | `sigma_real = sigma_imp` -> mean P&L ~ 0; `sigma_real = 2 sigma_imp` -> `0.5 Gamma (sigma_r^2 - sigma_i^2)` per unit time |
| T4 | Synthetic Ho-Lee curve with known vol | Recovered breakeven vol within 5% (record the bias factor) |
| T5 | Analytic option scalars | `Theta_opt = 1e-4 x dD x sigma^2`, `Gamma_opt = 2 dD x 1e-4` within 0.1% |
| T6 | Look-ahead injection | Sharpe rises sharply |
| T7 | Zero-move carry identity | Ageing P&L = quoted carry x d(calendar days)/365.25; Friday->Monday = 3x |
| T8 | Date permutation | Sharpe ~ 0 |
| T9 | Attribution residual | <= 10% of gross |
| T10 | Side symmetry | Long and short versions mirror to 1e-9 in every bucket |
| T11 | Straddle premium | `2e-4 x dD x sigma^2 x tau0` |
| T12 | Hedge-cost curve | `c_h = 0` on a flat strip, analytic on a quadratic strip, tends to `c` as h -> 0 |
(Internal backtest spec v0.4, 23 Oct 2026.) Add: canonical `pnl` identity `|total - mtm - carry - financing - cost| < 0.01`; hand-computed package test for the sign and DV01 of each leg (catches the factor-of-two and sign(bpv) traps);
unit assertions by column name (`_bp`, `_pct`, `_ccy`), never magnitude heuristics.

**Mutation test**: flip the option sign for the short side, drop the 2 in the straddle premium, replace `h_{t-1}` by `h_t`, drop the lag, use a full-sample z; confirm the relevant tests (T10, T11, T1, lag sweep, truncation) fail; restore (Internal implementation prompt).

## 3. Controls for component strategies
For a package of two components (e.g. curve + option) report: C1a option-only on the same dates, C1b option-only standalone, C2 curve-only on the same dates, C3a always-on one side, C3b always-on signed by the signal's sign convention, C4 random entry (1,000 draws, p-value), C5 inverted signal (should lose).
Never generalise one structure's result to the strategy; state the factor exposure of the sizing rule before quoting P&L.

## 4. Data gates before the engine
- Inner-join inputs; drop weekends; **drop and log stale rows; never forward-fill**; gate: no stale input in the last 3 days; report match rates of every join and cache.
- Return outlier screen: flag days > 4 std from the mean; a genuine extreme coincides with news (Chan 2009). One bad data point can kill an alpha signal; put sanity checks in code.
- Identity checks graded exactly: `as_of + days_to_expiry == expiry`; accrued + clean = dirty; tail_bp = 100 x (stop - wi). Expiry rules handle holidays.
- A series flat across all tenors on 100% of days (e.g. a GC repo series) is not informative term structure: store, flag, do not use. Off-the-run closes sitting 100% on the 1/32 grid are dealer quotes, not matrix prices.
- Required gating columns that are present but null are errors, not empties.
- Chart hygiene: reindex to business days before plotting so gaps show (inner-joined frames contain no NaNs to break the line; an audit found 152 traces bridging gaps > 15 days, worst 553 days).

## 5. Run discipline
- **Trial log**: every run appended with its full config; row count = N for the deflated Sharpe. Report every result with all trials behind it (AFML ch.14). Pre-registered cell lists counted in a test.
- **Holdout lock**: the holdout cannot be read; run once when instructed; report whatever it says. Re-running after peeking makes it in-sample. A quarantine period (e.g. a deliberately hard selloff) stays unused in design (JPM, TradeRunner, 2018).
- **Parity**: against a prototype on several dates with numeric anchors; explained differences are listed as deviations (spec says / did / why / expected effect); unexplained differences are bugs.
- **Costs on in every headline number**; in-sample never reported as performance; no silent default changes; a negative result is an acceptable outcome.
- **Sample and decay**: report subperiod results (Salomon Brothers, Understanding the Yield Curve, 1995: "period specificity is a problem that sophisticated econometric techniques cannot overcome"); choose a neutral sample with similar start and end yields when estimating average returns; 300 monthly observations give `t ~ 5 x Sharpe`.
- **Process rules**: identical code, optimiser and impact model in backtest and production; calibrate the impact model to live fills; fix protocol and dataset beforehand and re-run all strategies if the protocol changes (Paleologo, ch.8).
- **Backtest schemes** (choose here, validate in [bt-validation-and-overfitting](../../bt-validation-and-overfitting/SKILL.md)): walk-forward is the default (historical interpretation, reconcilable with paper trading; purge labels that straddle the split; no embargo needed trailing; but single path, sequence-dependent, early decisions on small samples);
  vanilla 70/30 splits; CV backtests need purge and embargo and Palomar advises avoiding them; multiple randomised backtests (random instrument subsets and contiguous random windows) give a distribution of metrics. Invalid OOS designs: earlier history as 'OOS', splitting correlated instruments into IS/OOS sets.
- **Embargo for overlapping labels**: drop the first label-horizon days of each test fold (5 days for a 5-day return).
- **Synthetic data** for stress: parametric heavy-tailed iid, non-parametric resampling (destroys vol clustering), hybrid residual resampling (preserves it); synthetic bull/sideways/bear regimes or crisis replays.
