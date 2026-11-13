---
name: bt-performance-attribution
description: 'Explains and scores backtest or live P&L for G10 rates RV. Splits P&L into carry, roll-down, rates (delta by tenor or PCA level/slope/curvature), spread, convexity/gamma, vega, hedge, costs and an unexplained residual (accept <= 10% of gross), then computes risk-adjusted metrics (Sharpe/IR with standard error, Sortino, max drawdown and time under water, Calmar, hit rate, return concentration, non-parametric ratio, active IR and % on) and a tearsheet, and tests whether edge is signal or just long bias, regime beta, leverage or short vol. Use when asked for P&L attribution, PnL explain or decomposition, unexplained P&L, carry vs price P&L, roll-down contribution, convexity vs curve P&L, Greek or Taylor explain, PC / factor attribution, what drove the return, tearsheet or tear sheet, Sharpe ratio, information ratio, drawdown, hit rate, Calmar, Sortino, backtest performance report, alpha vs beta, or "is there edge beyond carry / beta". Daily review of open positions: rv-trade-monitoring.'
---

# Backtest performance attribution

A backtest number is only useful once you know where it came from. Most RV P&L is some mix of carry (paid for sitting
still), roll-down (an unchanged-curve assumption), directional rates exposure that the hedge did not fully remove,
convexity or gamma (short vol in disguise), and costs; the skill is the remainder. This skill explains P&L bucket by
bucket against a full revaluation, attributes it to curve factors, tests it against simple benchmarks, and reports
risk-adjusted metrics with their standard errors, so that a headline Sharpe is never quoted without its anatomy.

## When to use
- Any backtest, live trade or book needs a P&L explain: "how much was carry vs price?", "was this a slope bet?".
- A curve or fly trade needs P&L split into level / slope / curvature / convexity / carry.
- A tearsheet or performance report is requested: Sharpe, IR, drawdown, hit rate, turnover, concentration.
- A strategy looks good and you must check long bias, regime beta, short-vol carry or leverage before believing it.
- Unexplained P&L is persistent: audit the risk model, interpolation, roll and funding accounting.

## Conventions (state them on every output)
- **Sign.** P&L > 0 = gain. `dv01_ccy` is signed positive for long duration (receive fixed, long bond or futures). For
  a yield move `dy` in bp: first-order P&L = `-dv01_ccy * dy`. The helper functions use **delta S = P&L per +1bp**
  (`S = -dv01_ccy`); positive gamma = long convexity = receiver / long bond. Check the sign of any imported risk strip:
  one reference book uses +pv01 = payer ("never take the direction for granted", Darbyshire, Pricing and Trading
  Interest Rate Derivatives, 3rd ed., 2022).
- **Units.** Rates and spreads in bp; normal vol in bp/yr; P&L in currency; linear trades quoted in bp of yield or ccy,
  option trades in bp of notional ("abp") (JPM, Near, far, wherever yields are, 2 Oct 2026). Curve A-B = longer minus
  shorter; fly 2s5s10s = 2x5y - 2y - 10y.
- **Time.** Carry and theta accrue per calendar day (zero-move Friday-to-Monday = 3 days of carry); volatility
  annualises with sqrt(252) on business-day P&L. Write `periods` next to every Sharpe (252 daily, 52 weekly, 12 monthly).
- **Scenario.** Every carry and roll number is relative to a named "nothing happens" scenario: **curve unchanged**
  (default, matches [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md)) or **forwards realised** (the benchmark
  under which any bond or par swap earns the short rate; Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022).
- **Currency.** Explain in the instrument's local currency, then convert in post-processing. Greeks FX-converted and
  Taylor-expanded were off by more than 5% in a EUR/SEK example (Darbyshire, Coding Interest Rates, c.2024).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Daily P&L components per package | `pnl` | daily, whole backtest | `total = mtm + carry + financing + cost` is enforced |
| Holdings with signed DV01 and weights | `positions` | daily | legs frozen at entry; needed for hedge and factor buckets |
| Executions | `trades` | per fill | slippage and fees for the cost bucket and new-activity P&L |
| Curves for full revaluation | `curve_par`, `curve_zero`, `rate_fixings` | daily close, same snap each day | fixings must be in the curve or accrued coupons are wrong |
| Bond / futures / STIR marks | `bond_quotes`, `fut_quotes`, `stir_quotes`, `repo_rates` | daily | futures P&L is price change only; repo for financing |
| Option marks | `opt_quotes`, `vol_surface` | daily | normal vol in bp for vega and theta buckets |
| Signals | `signals` | per decision date | for time-in-market, long-bias and signal-vs-beta tests |
| FX | `fx_rates` | daily | only for converting local-currency explains |

Definitions of these tables: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). Never invent marks;
ask for missing curves or the adapter. Same snap every day: a mixed snap shows up as fake unexplained P&L.

## Method

### 1. Start from the accounting identity
`pnl.total_ccy = mtm_ccy + carry_ccy + financing_ccy + cost_ccy` (check every row; a break is a data or booking bug, not
a result). `carry_ccy` is interest earned (change in accrued plus coupon cash), `mtm_ccy` is the clean-price or NPV
change and therefore **already contains roll-down, pull-to-par and market moves**. The explain below splits `mtm`.
`scripts/perf.py` has `pnl_component_split` for this check.

### 2. Per-position daily explain by full revaluation
Run each day and position; every bucket is a repricing, so the pieces must reconcile.
1. **Carry / roll / theta.** Age the *struck* position one day on the unchanged t-1 curve and reprice (option:
   `theta = P(tau - dt) - P(tau)`). Never use a constant-maturity series or a curve "translate" (forwards held) as the
   carry scenario: a repriced 1y roll of the aged package matched a dealer's published 1y carry (correlation +0.99) while a
   running carry field correlated -0.14 and ranked packages wrongly, and a curve translate gave 0.000bp carry on a
   forward-starting package and -531.9bp on a 1y-aged 30y payer (Internal convexity-RV research handover, undated).
   Split cash carry (coupon minus financing, below) from carry-roll-down (price change from time alone); a premium bond
   on an upward curve shows large negative roll-down offset by large cash carry, so report both, not the net (Tuckman).
2. **Rates (delta).** `sum_j S_j * dr_j` with `S` per calibrating (liquid) instrument, `dr` the day's bp moves, using
   the same interpolation as the pricing curve. Risk expressed on curve nodes or solver parameters is not hedgeable and
   explains badly (Darbyshire, Coding Interest Rates).
3. **Gamma.** `0.5 * dr' G dr` (full cross-gamma) or `0.5 * Gamma_parallel * dr^2` for routine use. Single
   cash flow: delta `-t e^{-rt}`, gamma `t^2 e^{-rt}`, so gamma/delta grows with tenor, is independent of the rate level
   and decays linearly with time; convexity P&L therefore sits in long tenors (Citi, A Holistic Approach to Convexity,
   Jun 2022). Linear products (swaps, bonds, FRAs) are convex too: attribute it explicitly.
4. **Vega** `V * d(nvol_bp)` and **spread / basis** `S_spread * d(spread_bp)` for swap-spread, ASW, tenor or CCP
   basis legs (`S_spread` = P&L per +1bp of the stated spread convention, so its sign flips with the convention). **Hedge** bucket = P&L of the hedging legs that is not part of the thesis (futures hedge, delta hedge).
5. **Costs** = `trades.fee_ccy` (<= 0) minus `slippage_bp * |dv01|` (slippage positive = cost), matching `pnl.cost_ccy` <= 0.
   Always shown, never netted into other buckets.
6. **Residual** = full revaluation - sum of buckets. **Accept if `sum|residual| <= 10% of sum|gross|`** over the
   run and the daily residual mean has no persistent sign (Internal forward-curve vs straddle backtest spec v0.4, 23 Oct
   2026). A persistent sign is a risk-model design defect (interpolation mismatch, misaligned inputs, missing
   curve foundation): a hedged book can have a risk-model explain of exactly zero and still lose
   (Darbyshire, Pricing and Trading Interest Rate Derivatives). Use `explain_residual` and `taylor_pnl`. Comparing actual MtM changes with risk-factor MtM changes is also a risk
   control, with stress cases such as March 2020 (CFTC MRAC, Treasury Cash-Futures Basis Trade, Dec 2024).
7. **Realised gamma edge** (option or convexity trades) = curve roll + curve gamma + option theta + option gamma; "other"
   = slope + vega + hedge residue + costs. Show both: the first is the thesis, the second is what hurt.

Sequential order matters when explaining a *bond* (each step holds later factors fixed), see worked example 1: price at
spread to start curve -> reprice on scenario curve (carry-roll-down) -> reprice on actual end curve at the same spread
(rates) -> reprice at actual spread (spread) -> add cash flows (cash carry). Total must equal gross return.

### 3. Funding, futures and cash accounting traps
- **Bond cash carry** = coupon income - financing. Coupon `= (C/2) * days / DC` (DC = actual days in the coupon period,
  181-186); financing `= (P + AI) * RP/100 * days / 360` at **term repo matched to the holding period** (Burghardt et
  al., The Treasury Bond Basis, 3rd ed., 2005). Include specials on the long leg and reverse-repo cost (typically
  10-25bp below general repo) on shorts.
- **Futures** P&L = price change x tick value x contracts (fully leveraged, no financing). **Basis trade** P&L =
  change in basis + carry (worked example 3). A CF-weighted basis tracks basis P&L but has a directional tilt;
  DV01-neutral removes the tilt but then P&L no longer tracks the basis: report which one you ran.
- **Two risks in a futures hedge**: spot DV01 and repo (stub) DV01 (`dF/dR = (S + AI) * n/360` per unit of rate, R in decimals, n days to delivery). Weekly spot yield and
  1m repo changes were almost uncorrelated (R^2 0.002-0.025), so attribute them separately; stub is about 2% of spot
  DV01 for the long bond, 3.8% for 10y, 13% for 2y (Burghardt et al.).
- **Swaps marked on NPV only** book no carry cash: P&L is entirely the NPV change, and fixings must be in the curve or
  accrued coupons are wrong. For bonds accrue coupons and repo explicitly (`financing = sign * |MV| * (1 - haircut) *
  repo * yearfrac`, ACT/360).
- **Sweep P&L out of the cash balance daily.** Interest on accumulated profit is not trading P&L. Use the ledger
  F1 funding inconsistency (overnight interest vs carry) + F2 market moves + F3 new activity (Darbyshire, Pricing and
  Trading Interest Rate Derivatives, 3rd ed., 2022); [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md)
  covers CSA, CTD-collateral and funding lines that sit outside market P&L.
- **Opening curve.** Reusing yesterday's input prices on today's date schedules injects fake roll-down in some
  sections (IMM-dated vs rolling par tenors) and an offsetting error in market moves; close-to-close total is
  unaffected but the carry/market split is noise. Re-quote each instrument on today's schedule from yesterday's curve,
  and close all currencies at the same instant (1615 local is one convention). The "viewless shift" (forwards realised)
  explain double-counts realised forwards inside the rate bucket unless an IR-time cross-gamma term is added (Darbyshire;
  Quantitative Finance Stack Exchange, carry-roll-down thread, Dec 2020). Be consistent day to day.
- **Path dependence.** Market-vs-new-business splits depend on ordering: compute positions-first and curves-first and
  average, with short sampling intervals (Darbyshire, ch.17).

### 4. Factor and curve-shape attribution
1. **Per-PC P&L.** `E` = orthonormal eigenvectors (columns = PCs) from PCA on **bp changes**. PC risk = `E' S`, PC move =
   `E' dr`, P&L_i = risk_i x move_i, sum over **all** PCs = `S . dr`. Use raw (non-demeaned) moves; use all PCs or
   report the residual of the truncated ones: in a 7-tenor book PCs 4-7 carried 33k of 195k (17%), so a 3-PC
   truncation leaves a large residual (Quantitative Finance Stack Exchange, Attribute P&L to PCA vectors (swaps), Jan 2022).
   Standardised (z-score) PCA breaks orthogonality and the P&L stops adding up. Eigenvector signs are arbitrary:
   align them across dates before comparing. Check: risk proportional to PC1 must give PC risk `[c, 0, ..., 0]`. Nonlinear alternative: shift the curve
   sequentially by `c_i * PC_i` and fully reprice (or reprice each PC alone from the start curve); report the residual.
2. **Invariance rule.** If risk is transformed `S' = T S`, moves must be transformed `dr' = T^-T dr`; never combine
   transformed risk with the real moves of the new basis (use the pseudo-inverse if `T` is non-square). Only transform
   from complex to simple models, and do not chain transforms (Darbyshire, ch.10). `change_basis` implements it.
3. **Pick the basis that matches the trade.** Swap spread: outright [bond, swap]; "spread + swap"; or "spread + bond"
   (bond desks prefer it because the residual delta sits in the native liquid hedge). The total is identical in all
   three (worked example 2).
4. **Trader-model view.** Express P&L on 2Y, 10Y, 2s5s10s, 5s7s10s ... via the (pseudo)inverse transformed moves; the
   total is invariant but the view shows which RV component paid, e.g. a loss that came from 2Y moving while 10Y did not
   (Darbyshire, sec 16.3.2). One personal trader model, square and full rank.
5. **Regression on a P&L series.** Regress daily trade P&L on PC1-3 moves (PCs are uncorrelated, so separate univariate
   slopes are fine; correlated PCs mean the PCA is wrong), plus a squared-move convexity term and carry. Report shares
   of P&L and incremental R^2 because carry/slope and level/convexity are collinear at trade horizon. **Daily convexity is
   unidentified** (t 0.9-2.1 daily vs 2.1-5.4 at trade level): read linear factors daily, convexity per trade.
6. **BPV-neutral does not mean factor-neutral.** A 2Y-5Y-7Y Bund BPV fly carried about 44% PC1, 29% PC2, 28% PC3
   exposure; the PCA-weighted fly loaded 99.7% (R^2) on PC3 only (Huggins & Schaller, Fixed Income Relative Value
   Analysis, 2nd ed., 2024). Regress what you actually traded; "hedge against all factors of lower order than the one
   you want exposure to".
7. **Curve package P&L variance** (forward flatteners): carry = ex-ante spot minus forward; curve = change in the spot
   curve over the horizon; convexity = remainder. The 30s/50s package had about 80% of P&L variance in convexity,
   while 5s/10s and 10s/30s were mostly curve (JPM, An option by any other name, Feb 2017). Barbell-versus-bullet
   is mostly reshaping: 99% of monthly P&L variance, so do not call it a convexity trade (Salomon Brothers,
   Understanding the Yield Curve Part 5, Sep 1995).
8. **Return decomposition for outright duration** (realised): `return = yield - D*dy + 0.5*C*dy^2 + residual`; use *yield*
   when `dy` is bond-specific, *rolling yield* when `dy` is constant-maturity; percentage contributions to the mean
   return add to 100%, volatility contributions do not. Ex-ante: yield income + rolldown + value of convexity
   + duration impact of the view + local rich/cheap (Salomon, Part 5, Part 6). Details in
   [references/explain-formulas.md](references/explain-formulas.md).

### 5. Is the edge real? Strip beta, regime and short vol
1. **Benchmark against simple carry or being long, not zero.** Measure on positions (signal applied from t+1, never the
   same close), then report fraction of time long, the IR of simply being long
   and the signal's IR over it. A combined duration signal was long about 57% of the time versus 80% for bond momentum;
   its IR of 1.3 compared with 0.84 for long G4 (JPM, Systematic fixed income trading strategies, 13 Apr 2015).
2. **Active IR and % on.** For intermittent rules report return, vol, risk/reward, max DD, **active IR** (computed only
   over periods in the market) and **% on**. A rule on 27% of the time showed risk/reward 0.53 but active IR 1.01
   (Willer & Saunders, Trading Global Macro Markets, 2026); check: active IR is about full-period IR / sqrt(% on) =
   0.53 / sqrt(0.275) = 1.01 when the rule earns nothing while off.
3. **Controls** (same package side): option-only or leg-only with copied dates; curve-only with copied dates;
   always-on; random entry (1,000 draws gives a p-value); inverted signal (must lose). Package ~ option-only means the
   curve adds nothing; curve-only strongly positive with large slope P&L means a slope bet in disguise (Internal
   forward-curve vs straddle backtest spec v0.4, 23 Oct 2026).
4. **Permutation Sharpe.** Shuffle daily sizing decisions at fixed long fraction (3,000 trials) and compare with the
   median/95th/99th percentile: 0.75 Sharpe at 50% long is far better than 0.75 at 80% long (JPM, Do androids dream of
   electric bonds?, 22 Nov 2017).
5. **Regime split.** Report active IR by regime (rally/sell-off, easing/hiking cycle, high/low vol x dispersion) beside
   the unconditional figure; a strategy that only works in one cell is a regime bet (Citi, QIS Corner, 20 Aug 2026).
6. **Short-vol test.** Roll-down and receive-belly flies are "akin to selling volatility and going long theta":
   bucket P&L by the size of the underlying move. A convex payoff must show a **smile, not a ramp**; a long-convexity
   position loses on flat days and a short-convexity one has a high hit rate and a fat left tail (a 10y CTD short
   basis won 23 of 25 trades, yet a stress case cost 17/32; Burghardt et al.).
7. **Liquidity split and uniqueness.** Compute IR separately on liquid and illiquid instruments (a signal that only works
   in illiquid ones is of limited use at size) and the P&L correlation with the existing book; above about 0.7 a new
   strategy adds little (Tulchinsky et al., Finding Alphas, 2015).
8. **Concentration.** HHI of positive returns `h+ = (sum w^2 - 1/n)/(1 - 1/n)` with `w_i = r_i / sum r+`; same for losses and
   for bets per month. P&L from one group, one tenor or a few extreme days is fragile (López de Prado, Advances in
   Financial Machine Learning, 2018).

### 6. Risk-adjusted metrics (defaults)
| Metric | Formula and default | Note |
|---|---|---|
| Sharpe / IR | `mean/std(ddof=1) * sqrt(periods)` on P&L-per-capital; **no rf** for unfunded swaps and futures or when financing is already in P&L | quote annual; state `periods`; positive autocorrelation rho overstates the sqrt(periods) Sharpe: corrected ~ naive x (1-rho) (Paleologo) |
| SE(Sharpe) | `sqrt((1 + SR_p^2/2)/T)` per period, iid (Paleologo, The Elements of Quantitative Investing, 2025); annual SE about `1/sqrt(years)` | t about SR*sqrt(years); IR 0.5 needs about 16 years for t = 2 (Grinold & Kahn, Active Portfolio Management, 2nd ed., 1999) |
| Sortino | mean excess / downside deviation over all obs | compare with Sharpe; a gap flags skew |
| Drawdown | `dd = cum - hwm`; `TuW` = longest run below hwm | report max, 95th pct DD and TuW; max DD is one path point, so add average DD or CDaR (Palomar, Portfolio Optimization, 2025) |
| Calmar | annualised excess / abs(max DD); Sterling = / (abs(max DD) + 10% of capital) | sensitive to a single point |
| Hit rate | `#positive / (#total - #flat)` | meaningless without payoff ratio for short-vol packages |
| Non-parametric | average of median/IQR, median return / median loss, return / 5th percentile | for fat tails; bootstrap 50% subsets, 1,000 repeats (JPM, Zen and the art of gamma maintenance, 9 Mar 2018) |
| Cost line | P&L at 0x / 0.5x / 1x / 2x costs and break-even cost per leg | costs on in every headline |

Calibration: a generic before-fee IR has median 0, 75th percentile 0.5, 90th percentile 1.0; 0.5 is "good", 0.75 "very
good", 1.0 "exceptional"; **IR far above 2, or IC above 0.20, usually signals a faulty backtest** (Grinold & Kahn). Sharpe
grades from equity cross-sections of about 3,000 names (2.5 to 6) do **not** transfer to a small rates RV universe
(Tulchinsky, Finding Alphas, 2015). Heuristics (Chan, Quantitative Trading, 2009): Sharpe < 1 is not stand-alone; profitable
nearly every month implies Sharpe > 2; drawdown deeper than 10% or longer than 4 months implies low Sharpe.
Overlapping holding periods and high kurtosis inflate apparent significance: use HAC or non-overlapping samples and
defer multiple-testing deflation to [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).
Full metric catalogue, benchmark tables and tearsheet fields: [references/metrics-and-tearsheet.md](references/metrics-and-tearsheet.md).

## Worked examples
1. **Sequential bond explain, UST 7.625s of 11/15/22, 13 Nov 2020 to 14 May 2021, realised-forwards scenario**
   (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022, Tables 3.6-3.8). Start 114.87654 at spread -1.16bp.
   Reprice on realised-forward curve: 111.11555, **carry-roll-down -3.76099** (pull to par on a high coupon). Reprice
   on actual end curve, same spread: 111.29847, **rates +0.18292**. Reprice at actual spread (-7.27bp) = market
   111.39690, **spread +0.09843**. Cash carry (15 May coupon) **+3.81250**. Total **0.33286** = 0.2898% gross, and
   cash carry + roll-down = 0.0449% = six-month short rate plus spread, as realised forwards predict. Net of 6m
   financing at 0.05% a year the return is 0.2648% (0.2653% with 98% repo funding); on the 2% capital (50x leverage) it
   is 13.27%. `sequential_bond_explain` reproduces it.
2. **Same P&L in three bases, swap-spread trade** (Quantitative Finance Stack Exchange, Calculating PnL on Swap Spread
   Trade, Jul 2018). risk S (P&L per +1bp: bond +102, swap -99)
   and moves (bond +2bp, swap +1.7bp); spread = bond yield - swap rate. Outright: 204 - 168.3 = **35.7**. Spread + swap: risk
   [102; 3], moves [0.3; 1.7] -> 30.6 + 5.1 = **35.7**. Spread + bond: risk [3; 99], moves [2; 0.3] -> 6.0 + 29.7 =
   **35.7**.
3. **Basis trade = change in basis + carry** (Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005, ch.1). Long $10mm
   7-1/2% 11/16 at 120-20, short 115 June futures at 103-30; unwind 14 days later at 116-21 and 100-16. Bond -$396,875;
   futures +$395,312.50; coupon +$29,005.52; repo -$21,624.23. Total **+$5,818.80 = basis change -$1,562.50 + carry
   +$7,381.29**. Quoting only price P&L would show a small loss on a winning trade.
4. **Curve-shape attribution of a fly** (Nordea, EUR rates: The quiet game, 12 Aug 2025): receive EUR 5s10s30s, -19.6bp
   since January with loadings 0.73 / -0.36 / 0.57. Since early May the 10s30s steepening added 3bp, while the **curvature
   drop added 15bp**; the gain was a curvature and vol-decline trade, not the curve view.
5. **PCA attribution, 7-tenor USD swap book** (Quantitative Finance Stack Exchange, Attribute P&L to PCA vectors, Jan 2022):
   tenor P&L +195k; PC P&L 17.6 / 108.9 / 35.6 / 7.2 / -8.4 / 9.4 / 24.6 (k), sum 195. PC2 (slope) paid most; truncating
   to three PCs would have left about 17% of P&L unexplained.
6. **Convexity-RV attribution result** (Internal convexity-RV research handover): factor-regression shares of trade P&L
   ran 54.7% to 171.5% through the convexity term for the flatteners (10Yx10Y/20Yx10Y 171.5%, 30Y/50Y 142.2%,
   15Yx5Y/20Yx10Y 86.1%; shares exceed 100% where factors offset), while 5Y/30Y was a slope bet (slope 259.6% of P&L,
   carry -147.9%). More cases, including Citi's GBP 15y10y/25y10y flattener (GBP 445K = 115K curve
   + 330K convexity) in [references/worked-examples.md](references/worked-examples.md).

## Signals & interpretation
- Residual > 10% of gross, or one-signed: fix the explain before reading any bucket. Suspect interpolation mismatch,
  stale or mixed snaps, missing fixings, constant-maturity marking, or a missing second-order term in a volatile
  stretch (cross-gamma can dominate when volatility spikes).
- Carry share of gross high and price P&L near zero or negative: a carry harvest that is short volatility. Judge it by
  the left tail and the stress drawdown, not the hit rate.
- Convexity or gamma bucket > 100% of P&L with carry negative: a long-convexity trade bleeding theta; ask whether
  realised vol exceeded breakeven vol (`sigma_BE`). Attribute a short-gamma loss against the implied at entry: it can lose
  although implieds fall if delivered vol jumps (JPM, Rules-based strategies update, 8 Jan 2018).
- Slope or level bucket large on a "neutral" structure: the sizing rule is directional; state its factor exposure before
  quoting P&L.
- A Sharpe that falls after costs, ex-direction, or out of sample, or an IC above 0.20: treat as overfit or
  mis-measured, not as alpha.
- Judge decisions by expected value, not by one outcome, in low signal-to-noise settings (swapsball, Poker: the bright and
  dark sides, 18 Jul 2018).

## Pitfalls
- **Persistent unexplained P&L is a model defect, not noise.** Also silent per-step exceptions: assert non-zero marks and
  closed-trade counts so a failed day cannot leave an equity hole.
- **Yield is not return.** Do not rank by yield; coupon effects, reinvestment and horizon risk break it.
- **Cost bookkeeping.** A fee charged only at unwind must cover the whole round trip; one-way cost is about half the
  bid-offer plus commission; a round trip counts as two trades. High-turnover signals flip sign after costs.
- **Same-close snapshot, mid marks, no margin, CSA or balance-sheet charges, no smile (short-straddle losses after big
  moves understated), vanna and volga ignored, funding ignored.** Put this list in every report.
- **Vol targeting does not tame tails.** It raised excess kurtosis from 2.4 to 2.9 on IRS receivers (Macrosynergy, Interest
  rate swap returns: empirical lessons, web print Aug 2025). Hedging lowers correlation, not volatility.
- **Secular trend.** An outright version of an event trade can look better only because yields fell (JPM, Follow the cash
  flow, 15 Sep 2015); strip it before judging edge.
- **Frequency dependence.** Ex-post Sharpe and correlation depend on data frequency when correlation is horizon
  dependent (a BTP fly vs yield: -0.88 in levels, +0.06 daily, -0.57 two-weekly; Huggins & Schaller).
- **Smoothed or appraised returns** understate vol: unsmooth with the first-order autocorrelation before comparing
  Sharpes (private equity ex-VC 1.47 -> 0.77 after unsmoothing; Willer & Saunders, 2026).
- **Aggregating Sharpe across sleeves**: volatilities and vol contributions do not add; P&L contributions do.
  Independent equal-risk strategies add as `sqrt(n)`.
- **MTM share is not direction share.** A delta-hedged gamma harvest books all its earnings through the mark, so a high
  mark-to-market share of P&L does not mean a directional bet; only the factor attribution answers it (Internal
  convexity-RV research handover).
- **Survivorship and add-asset bias.** Peer tables and backtests that add instruments with hindsight overstate edge;
  fix the universe at decision time (Grinold & Kahn; Willer & Saunders).
- **Never** report in-sample as performance, run the holdout once, and keep a log of every trial.

## Output
Return, in this order:
1. **Header**: strategy, period, `periods`, snap, scenario for carry/roll, currency, cost assumption, denominator for returns.
2. **Bucket table** per package and total: carry (cash), roll-down, rates by tenor or PC, spread/basis, gamma, vega, theta,
   hedge, costs, residual; columns P&L (ccy), % of gross, % of net. State `sum|residual| / sum|gross|` and PASS/FAIL (10%).
3. **Factor view** (curve packages): P&L by PC1-3 plus truncated remainder, or trader-model rows (2Y, 10Y, 2s5s10s, ...).
4. **Edge tests**: fraction of time long, IR vs always-long, active IR and % on, controls table, regime table,
   P&L-by-move-size (smile or ramp), HHI of wins and by group.
5. **Metrics**: Sharpe with SE and t, Sortino, max DD, 95th pct DD, TuW, Calmar, hit rate and payoff ratio, skew, excess
   kurtosis, non-parametric ratio, turnover, average holding period, P&L at 0x/0.5x/1x/2x cost and break-even cost.
6. **Verdict** in one line (carry harvest / slope bet / convexity trade / genuine RV / unproven) and the known limitations.
Feed the verdict to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) or the chart pack in
[eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md).

## Scripts
- [`scripts/perf.py`](scripts/perf.py): `sharpe`, `sharpe_se`, `sortino`, `drawdown`/`max_drawdown` (with time under
  water), `calmar`, `hit_rate`, `return_concentration`, `nonparam_sharpe`, `pnl_component_split` (identity check and
  carry share), `taylor_pnl`, `explain_residual`, `sequential_bond_explain`, `change_basis`, `pc_attribution`, and a
  `tearsheet` CLI on a canonical `pnl` table: `python scripts/perf.py tearsheet pnl.csv --strategy ID --periods 252`.
  `python scripts/perf.py --selftest` checks known answers (Tuckman table, swap-spread bases, PC1 identity, drawdown path).

## Related skills
- [bt-backtest-design](../bt-backtest-design/SKILL.md): produces the `pnl`, `positions` and `trades` tables that this skill explains.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): deflated Sharpe, multiple testing, walk-forward; apply after attribution.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): cost model behind the cost bucket and break-even cost.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): ex-ante carry and roll definitions and scenarios.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): par vs zero risk, Jacobians, bucketing used in the rates bucket.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): how the PCs and loadings used in section 4 are estimated.
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weights and the directionality that the factor attribution exposes.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): gamma, vega and theta P&L of delta-hedged options in more depth.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): collateral, funding and CTD-collateral lines outside market P&L.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): basis carry, implied repo and delivery option behind basis P&L.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): sizing rules whose factor exposure must be stated before quoting P&L.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): stress drawdowns and tail behaviour of carry harvests and short-vol packages.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread and ASW sign conventions that set the sign of the spread bucket.
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md): live P&L tracking, stops and process-vs-outcome review.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical `pnl`, `positions`, `trades` and curve tables.

## References
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): sequential carry-roll-down / rates / spread attribution with a worked UST example; realised-forwards benchmark; OAS and Ito return decompositions.
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022): explain vs unexplained, transformed-move P&L, PC and trader-model attribution, cross-gamma, daily P&L ledger, opening-curve construction.
- Darbyshire - Coding Interest Rates (companion treatise, c.2024): Taylor explain from par-instrument greeks, multi-currency P&L, par-forward Jacobian.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): basis P&L = basis change + carry, hedge P&L accounting, spot vs repo DV01, short-basis caveat.
- Salomon Brothers (Ilmanen) - Understanding the Yield Curve, Part 5: Convexity Bias and the Yield Curve (Sep 1995) and Part 6: A Framework for Analyzing Yield Curve Trades (Nov 1995): realised yield / duration / convexity decomposition, barbell vs bullet, additive ex-ante expected return.
- Quantitative Finance Stack Exchange - Attribute P&L to PCA vectors (swaps) (Jan 2022): inverse-transpose rule, per-PC P&L, 7-tenor worked numbers.
- Quantitative Finance Stack Exchange - Calculating PnL on Swap Spread Trade (Jul 2018): same P&L in three risk bases.
- Quantitative Finance Stack Exchange - carry-roll-down under realised expectations (Dec 2020): rolled-curve explain, viewless-shift double count.
- Quantitative Finance Stack Exchange - Delta hedge value formula (Mar 2017); DV01 on LIBOR vs SOFR basis swaps (Dec 2020); Projecting swap risk on bonds and futures (Oct 2024): ex-ante vs ex-post gamma P&L, instrument-delta explain, cross-instrument risk mapping.
- Citi - Interest Rate Volatility Trading, A Holistic Approach to Convexity Across Fixed Income (Jun 2022): Greek P&L decomposition, convexity buckets, expected Sharpe.
- J.P. Morgan (Younger, Sarkar, Salem) - An option by any other name: sourcing cheap convexity in the long end (3 Feb 2017): carry/curve/convexity P&L variance split.
- J.P. Morgan (Salem, Younger, Zhao et al.) - Do androids dream of electric bonds? (22 Nov 2017): permutation Sharpe, non-parametric ratio.
- J.P. Morgan (Younger, Salem, Zhao) - Zen and the art of gamma maintenance (9 Mar 2018): non-parametric ratio, bootstrap robustness.
- J.P. Morgan (Salford, Chordia) - Follow the cash flow: trading strategies around supply, redemptions and coupon payments in Euro government bond markets (15 Sep 2015): event-trade statistics, secular-trend caveat.
- J.P. Morgan (Ozil, Hayward, Alexeev, Alptuna) - Near, far, wherever yields are (2 Oct 2026) and J.P. Morgan (Diamond et al.) - Global Fixed Income Markets Weekly (21-22 Aug 2026): hit-rate definition, bp-of-yield vs abp units, desk scorecards.
- J.P. Morgan (Inkinen, Bassi) - Systematic fixed income trading strategies (13 Apr 2015): long-bias and regime-split diagnostics.
- J.P. Morgan (Gupta, Inkinen, Vijay) - Update on systematic rule based trading strategies (Feb 2017, Mar 2017, Jan 2018): per-signal tables, realised-vs-implied short-gamma loss.
- J.P. Morgan (Panigirtzoglou) - Investment Strategies No. 15 (9 Mar 2006) and No. 31 (11 Jan 2007): carry vs capital-gains split of cross-market and curve carry.
- Nordea Markets (Svendsen) - EUR rates: The quiet game (12 Aug 2025): PCA fly attribution into curve, curvature and mis-pricing.
- Citi (Bikbov) - Taking profits on GBP 15y10y/25y10y flatteners (26 Mar 2020): curve vs convexity P&L split.
- Citi (Saunders, Vo) - Quantitative Global Macro Strategy, QIS Corner (20 Aug 2026); Citi (Willer et al.) - Global Asset Allocation, House Views August 2026 (21 Aug 2026): regime-conditional active IR, ex-ante vs ex-post tracking error.
- Citi (Pickett, Willer, Saunders et al.) - Macro tapas (7 Aug 2026); Citi - US Rates Weekly (2 Oct 2026); Citi - Emerging Markets Strategy Weekly (20 Aug 2026): trade-log conventions, capital at risk = stop, return on risk, hit rate.
- Nordea Markets (Aalund) - Bonds & bold (5 Nov 2021): delta-hedged straddle P&L as convexity minus (theta + funding).
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): regress P&L on PCs, BPV vs PCA fly exposure, horizon-dependent correlation.
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): Sharpe annualisation and standard error, autocorrelation bias, maximal attribution, vol-modulation Sharpe loss.
- Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): contribution-to-risk measures, exposure vs economy risk change, factor vs Brinson attribution, behavioural diagnostics.
- Burton, Dektor, Wheeler - Time Series Prediction of US Swap Rates (Stanford University student project paper, c.2008): swap Sharpe convention (sqrt(251), no rf) and rating scale.
- Credit Suisse (Pelata, Giannopoulos, Haworth) - PCA Unleashed: the application of PCA across European Rates markets (24 Oct 2012): portfolio PC exposure.
- CFTC Market Risk Advisory Committee, Market Structure Subcommittee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): MtM-versus-risk-factor attribution as a control.
- FinLab - Short-Term Mean Reversion Trading Strategy Backtest: The 3-Day Laggard Rule (Jun 2026): signal-versus-regime event-study decomposition.
- swapsball.net - Poker: the bright and dark sides (18 Jul 2018): judge decisions by expected value, not outcome.
- Grinold & Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): IR definitions and standard error, skill vs luck, attribution tools, IC tiers.
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): active IR and % on, tearsheet tables, unsmoothing, backtest caveats.
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): backtest statistics, HHI concentration, drawdown and time under water, TWRR.
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): performance-measure catalogue, drawdown and CVaR estimation fragility.
- Chan - Quantitative Trading (Wiley, 2009): Sharpe, rf and drawdown conventions, cost-adjusted P&L.
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): turnover, margin, drawdown and concentration diagnostics; equity Sharpe grades that do not transfer.
- Macrosynergy - Interest rate swap returns: empirical lessons (web print Aug 2025; data to Feb 2018): IRS return decomposition, vol-targeting kurtosis.
- Internal research documents - Forward curve vs straddle systematic backtest spec v0.4 (23 Oct 2026) and Convexity RV preflight handover (undated, data to about Aug 2026): attribution buckets, residual tolerance, control strategies, factor-regression shares of P&L, carry-measurement check.
