# Performance, storage, metrics and reproducibility

Backtest design and validation theory are in [bt-backtest-design](../../bt-backtest-design/SKILL.md) and
[bt-validation-and-overfitting](../../bt-validation-and-overfitting/SKILL.md); data cleaning rules in
[data-quality-and-timeseries-hygiene](../../data-quality-and-timeseries-hygiene/SKILL.md). This file is the engineering layer under them.

## Vectorise first, then parallelise
- Replace Python loops with array ops: masks, `cumsum`, `std`, `corrcoef`, `eigh`; `itertools.product` over a dict of lists to build parameter or scenario grids (adding a dimension needs no code change) (Lopez de Prado, Advances in Financial Machine Learning, 2018, ch.20).
- CPU-bound parallelism needs processes (GIL). Pattern: a pool with `imap_unordered(expand_call, jobs)` where `expand_call(kw)` pops `func` and calls `func(**kw)`; always `close()` and `join()`. Keep `num_threads == 1` as a plain loop: parallel-only bugs are unreadable. Order is not preserved: jobs carry their own key. On Windows (spawn) the function must be module-level and the entry point guarded by `if __name__ == "__main__"` (`mp_map` in the bundled script).
- Atoms and molecules: an atom is an indivisible task, a molecule a group run sequentially on one worker. `lin_parts = ceil(linspace(0, n_atoms, min(n_threads, n_atoms)+1))`. For a double loop over a triangle (row i costs ~i) use `nested_parts`: `r_m = (-1 + sqrt(1 + 4(r_{m-1}^2 + r_{m-1} + N(N+1)/M)))/2`; heaviest rows first. The selftest checks 100 atoms on 4 workers balance to within 10% of work.
- Load balance: make the number of molecules a multiple of the cores and front-load heavy ones. 10 molecules, one twice as heavy, on 10 cores leaves nine idle half the time; 100 molecules halves the run time.
- Reduce on the fly (`DataFrame.add`, in-place `dict.update`) instead of holding every worker output in memory. Memory, not speed, is often the reason to parallelise.
- Block PCA projection when the panel does not fit in memory: keep the first M eigenvectors with cumulative eigenvalue share >= tau, project block by block `P = sum_b Z_b W_b` (each block a separate file, loaded and summed in parallel).
- Reported gains (Lopez de Prado, AFML, ch.22 by Wu and Simon): HDF5 instead of serial ASCII gave 21x (604 s vs 3.5 h); an algorithmic rewrite of an estimator cut 18 min to 1.5 s (720x) with no parallelism. Profile and fix the algorithm before adding cores. Cloud virtualisation costs 2-10x on HPC-style codes; benchmark before moving a job.
- Daily-bar rates work (tens of series, thousands of days) rarely needs any of this: `numpy` + `pandas` + a single process suffices. Parallelise parameter sweeps and Monte Carlo, not curve builds (a build is ~10 ms).
- Storage: Parquet (typed columns, compression) for canonical tables; HDF5 for large arrays with attributes. Round-trip a table and `assert_frame_equal` once per schema change.

## Numerical hygiene
- Missing data are NaN, not 0 (zero is a valid signal; demeaning and decay otherwise create spurious positions). Never forward-fill signals or marks. Inner-join input series, drop weekends, log stale rows.
- Assign in place (`alpha[:] = ...`) when a framework tracks the array object; `alpha = ones(...)` rebinds the name and later in-place lines do nothing (Tulchinsky, Finding Alphas, 2015, ch.31).
- Do not add quantities with different units (price + volume): valid Python, invalid expression.
- Access data through an explicit delay: `x.shift(delay)` or `data[di - delay]`.
- Do not copy Python 2 code (`xrange`, print statements) or removed pandas APIs (`pd.stats.moments.rolling_*`, `DataFrame.append`) from books.
- Printed book numbers can disagree with the book's own code output (a 3Y cap printed 0.013078 vs prose "~1.77%"; a 1Y5Y payer 167.6bp vs "1726bp") (Brenndoerfer, Advanced Interest Rate Models: HJM and LMM, 7 Dec 2025). Re-run before using any figure as a test target.
- Prefer QR/SVD/`lstsq`/`solve` to explicit inverses; ridge is better conditioned than OLS.

## Metric definitions (fix them once, in one module)
- `daily_PnL = sum(position x daily_return)`, `daily_return = close_t/close_{t-1} - 1`; positive weight = buy, negative = sell, NaN = no position. For rates use DV01 x bp change instead (see the unit contract in SKILL.md).
- Information ratio (daily) `= mean/std`; Sharpe annualised with `sqrt(252)` (the same book uses 256 in one chapter and 252 in another: state yours). `IR = IC x sqrt(breadth)`. Turnover = value traded / value held; profit per dollar traded = P&L / dollars traded; max drawdown measured against a stated capital base (Tulchinsky, Finding Alphas, 2015, ch.6, 26-30).
- `decay_linear(x, n) = sum_{k=0}^{n-1} (n-k) x_{t-k} / sum (n-k)`. Rank to [0,1] as rank/(n-1) with average ranks on ties (Spearman is more stable than Pearson for non-stationary inputs); Fisher `arctanh(r)` has s.e. `1/sqrt(n-3)`; winsorise or cap shares; least-median-of-squares as a robust regression.
- Equity-platform Sharpe thresholds (2.5-6, ~3,000 names rebalanced daily) do not transfer to a rates universe of a few dozen series.
- Square-root impact add-on: `impact = alpha sqrt(|x|)`, average incremental cost `(2 alpha/3) sqrt(|x|)`, total `(2/3) alpha |x|^1.5`; with alpha = 1/1000, 1mm risk costs 1bp. Keep it outside any linear program so the LP stays linear (Darbyshire, PT3e, ch.19).

## Reproducibility protocol (house rules, unattributed)
1. One run = one manifest: Python/numpy/pandas/scipy versions, platform, RNG seed, sha256 of every input file, and free-form config. The bundled `run_manifest` does this.
2. Seed every stochastic step explicitly (`np.random.default_rng(seed)`); never the global generator. Parallel workers get child seeds (`SeedSequence.spawn`).
3. Truncation test for look-ahead: a causal signal at date t is identical on the full panel and on the panel cut at t. Run it on every signal function (`lookahead_check`); it flags `rolling(center=True)` and `shift(-1)`.
4. Signals use data through t-1; execution at t + lag; marks owned by one engine; precomputed signal panels certified through the full engine on the top few cells (daily-change correlation should be about 1).
5. Mutation test every check you write: break the formula in a copy (flip an option sign, drop a factor 2, change a convention) and confirm the check fails. A check that cannot fail is not a check. The bundled script was mutation-tested this way, and a mutant in the product rule exposed a missing test.
6. Log every parameter variant tried to a trial log whose row count is N for deflated-Sharpe style corrections; report in-sample numbers as in-sample; keep a holdout locked until a single final run; keep a deviations list (spec says / did / why / expected effect). Unexplained differences against a reference implementation are bugs.
7. Stop and ask when data are missing or shorter than assumed, when two reasonable implementations differ materially, or when a concept has no equivalent in the stack.
8. Costs on in every headline; report P&L at 0x, 0.5x, 1x, 2x costs and the break-even cost.

## Data-pipeline checks that have bitten
- Snap time: the nearest bar to a fixed clock time is not the settlement time of a listed contract (settlement happens earlier). Mixing snaps adds noise several times larger than the true daily move on near-dated packs. Keep `snap` in the key and refuse to difference across snaps.
- Roll detection by settlement-tick grid: a rate future's final settlement (100 minus compounded rate) is almost never on the tick grid while the starting contract is: use it to timestamp rolls.
- Listed vol units differ by product family (normal price vol for rate futures options; lognormal price vol for bond futures options; conversion `1e4/ModDur`). Never pool roots.
- Constant-maturity listed vol is not tradeable: a large share of observations lies outside a 30-90 day window and the constant-maturity series diverges from the listed one at longer expiries.
- Date identity `as_of + days_to_expiry = expiry` must hold exactly: a one-day misalignment left median vol almost unchanged but widened the cross-sectional dispersion by an order of magnitude.
- Caches: a regex that fails across a timezone offset silently dropped a third of rows; "no_data" can mean fetch failure. Report match rates for every join.
- Deep-strip contracts can stop being settled by the exchange; past-start futures need a past-fixings object.
- Every observation needs a delivery timestamp and is usable only after it; point-in-time data give more realistic (worse) backtests; one bad point can kill a signal, so run outlier and staleness checks in code (Tulchinsky, Finding Alphas, 2015, ch.14, 22).
