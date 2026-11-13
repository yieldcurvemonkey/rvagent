---
name: rv-trade-monitoring
description: 'Monitors open G10 rates relative-value trades after entry, covering daily P&L explain (carry, roll, rates, spread, residual), z-score and half-life drift, DV01 and vega hedge drift, stops, targets and time stops, re-underwriting triggers, add and reduce rules, event and vol-regime checks, and a decision journal that scores process separately from outcome. Use when the user asks to monitor, review, mark, manage or exit open RV trades or a book, or to track an idea after entry. Trigger words include open trades, book review, daily P&L, P&L explain, stop, stop-loss, target, take profit, time stop, half-life, z-score drift, re-underwrite, thesis check, hedge drift, DV01 rebalance, vega drift, roll, carry, breakeven, BE/RV, add, scale out, cut size, legging, trade journal, process vs outcome, post-mortem. Full attribution and tearsheets: bt-performance-attribution; entry-time note: rv-trade-idea-writeup.'
argument-hint: "<open trades or ideas/ files>"
---

# RV trade monitoring

Entry is the easy part. A live relative-value trade is a set of levels (entry, target, stop, time), a set of exposures
(DV01 or vega per leg, beta, convexity) and a thesis about what drives the spread. Monitoring checks that each of those
still holds, decides what to do when one does not, and records the decision so the process can be judged apart from the
result. This skill is a workflow: it turns a list of open trades or idea files into a dated status report, a set of
actions with reason codes, and journal entries.

## When to use
- A book review, daily or weekly: "what's the status of my open trades", "mark the book", "P&L explain", "any stops hit".
- A single position: "is the 2s10s steepener still working", "re-underwrite the 5s30s fly", "should I add or cut".
- Exits and resizing: "take profit", "stop me out", "is this time stop up", "scale down into the vol spike".
- Hedge maintenance: "DV01 drift", "vega drifted", "re-hedge the strip", "beta has moved", "hedge decay".
- Review after the fact: "why did I lose on this", "process vs outcome", "trade journal", "post-mortem".
- Before a known event (auction, central bank, quarter or year end) that could flip a trade.

Not for: finding new trades (use [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md)), writing a new idea note
([rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md)), or a pre-trade challenge ([rv-devils-advocate](../rv-devils-advocate/SKILL.md)).

## Workflow (run when invoked with `<open trades or ideas/ files>`)
1. Load the trade records. Each open trade needs the fields in Method 0. Read the idea files under `ideas/` if given.
   If a required field is missing (no target, no stop, no DV01), stop and ask for it. Never infer a stop.
2. Pull the canonical tables for each leg: `positions`, `trades`, `pnl`, `curve_par` or `curve_zero`, `bond_quotes`,
   `fut_quotes`, `repo_rates`, `swap_spreads`, `vol_surface` or `opt_quotes`, `cb_meetings`, `auctions`. Use
   [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) for the definitions. Missing data goes into the
   report as a gap, not a filled number.
3. For each trade compute: daily P&L explain (Method 2), spread level, z-score, half-life and their drift (Method 3),
   stop, target and time status (Method 4), DV01 or vega drift (Method 5), and the convexity or carry ratio if it applies (Method 6).
4. Run the trigger table (Signals and interpretation). Each fired trigger gets a reason code and an action.
5. Run the re-underwriting questions (Method 7) for every trade with a fired trigger or within two days of an event.
6. Write the report and the journal lines (Output). Do not change a stop or size without a written reason code.
   Any change is a new decision with a new journal line.

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Trade record (fields in Method 0) | `ideas/` write-up or `trades` | at entry | Entry, target, stop, named risk, driver. Not a data table: it comes from the write-up |
| Holdings per leg, DV01 or vega | `positions` | end of day | Signed DV01, positive = long duration |
| Executions and fill prices | `trades` | per fill | Needed for slippage and realised cost |
| Daily P&L by package | `pnl` | daily | Components must sum to total; check before explaining |
| Par curve by tenor | `curve_par` | daily snap, at least 3y history for the spread | Build the spread from par or zero rates |
| Zero curve | `curve_zero` | daily | Needed for forwards and roll |
| Bond prices and yields | `bond_quotes` | daily, with snap | Cash legs; benchmark switches must be handled (Method 3) |
| Futures prices | `fut_quotes` | daily, per contract | Strip hedges; front-contract drop-out |
| Repo and specials | `repo_rates` | daily, per issue where available | GC and reverse RP for basis trades |
| Swap spreads and ASW | `swap_spreads` | daily | Swap spread convention must be stated |
| Vol | `vol_surface`, `opt_quotes` | daily | Normal vol in bp per year |
| Events | `cb_meetings`, `auctions` | scheduled | Event dates and auction sizes |
| Crowding | `positioning`, `flows_trades` | weekly or better | Optional, for crowding checks |

If an input is missing, ask the user or the data adapter for it. Never invent values.

Spread convention used throughout: curve spread = longer minus shorter (2s10s = 10y minus 2y, in bp). DV01 is currency
per bp and positive for long duration; receive fixed is long duration. Direction +1 = long the spread (profits when it
rises), -1 = short the spread. Normal (bp) vol for rates options. Swap spread: US = swap rate minus Treasury yield; EGB and gilt
ASW = bond yield minus swap rate (bond spread over swaps); state which one a trade uses and never mix them in one history.

## Method

### 0. Trade record (required fields before monitoring starts)
- Id, structure and legs with signed weights (e.g. receive-belly fly: -0.5, +1, -0.5), direction, entry date and level.
- DV01 (or vega) per leg at entry, and the currency of risk.
- Thesis, driver (the market variable that must move for the trade to work), and kill criteria (what would make it wrong).
- Target, stop, maximum holding period, and the reward-to-risk at entry (must be at least 1.5:1; Citi's radar screen uses this minimum).
- Entry half-life and entry z-score (from the write-up), and the named risk. The source standard is "an explicit entry,
  target, stop, rationale and one named risk" (BofA, UK Rates Viewpoint, 5 Sep 2024).
- Event calendar for the holding period.

### 1. Units and bookkeeping
- Report every trade in bp (spread), in DV01 or vega units, and in currency. Return on risk = P&L / risk unit, where the
  risk unit is the largest two-week change in the trade's own history (Citi, US Rates Weekly, 4 Oct 2019).
- Track the closed-trade book separately: count, winners, hit rate (JPM, 6 Mar 2020 used 34 winners of 47 trades in 12 months).

### 2. Daily P&L explain
Decompose each package's day into components that sum to the total:

`total = carry + roll + rates + spread + convexity + financing + cost + residual`

- Carry and roll: the change from time passing with the curve unchanged. Use the scenario you state: realised-forward
  (the forward curve is realised) or unchanged curve. Carry and roll numbers depend on the scenario (Tuckman and Serrat,
  Fixed Income Securities, 2022).
- Rates: `rates = -sum_legs( DV01_leg x dy_bucket_bp )`. Use the same bucket moves as the risk model. A positive DV01 loses
  when yields rise.
- Spread: reprice at the actual end-date spread with the curve held; the difference is the spread component. Order
  matters; state it.
- Convexity (delta-hedged or option positions): separate the curve move from the realised-vol component. Example: a GBP
  15y10y/25y10y flattener earned about $115K from the curve and $330K from convexity in a vol spike (Citi, Taking profits
  on GBP 15y10y/25y10y flatteners, 26 Mar 2020).
- Residual = total minus the explained parts. Treat a large residual as a model or data problem before any trade action.
  House default (not from the sources): investigate when |residual| > max(20% of |total|, 2 times the trailing 60-day
  standard deviation of residuals). A risk model can show zero P&L while a mis-specified hedge loses (Darbyshire, 2022).
- Check against the canonical identity: `total_ccy = mtm_ccy + carry_ccy + financing_ccy + cost_ccy` in the `pnl` table, tolerance 0.01.
  Bridge: `carry_ccy` is accrual or coupon income (the cash carry); the clean-price drift from time passing (carry-roll-down)
  sits inside `mtm_ccy`, together with rates, spread, convexity and residual. Do not count carry twice.

Worked check (Tuckman and Serrat, 2022, realised-forward scenario, bond 7.625s of 15 Nov 2022): start 114.87654;
carry-roll-down -3.76099; rates +0.18292; spread +0.09843; cash carry +3.81250; total 0.33286. The four components sum to
the total. Full numbers in [references/worked_examples.md](references/worked_examples.md).

Concentration check: if one instrument produced about 40% of the day's P&L (a single 7s8s9s fly did so in the Darbyshire,
2022, example), consider banking it, and check whether the rest of the book carries the risk.

### 3. Spread level, z-score, half-life drift and benchmark hygiene
- Spread `s_t` in bp. z-score `z_t = (s_t - mean_W) / sd_W` over a trailing window `W`, sample sd (ddof = 1).
  Defaults: `W = 252` observations for the z-score (about one year; Chan, Quantitative Trading, 2009, asks for about 252 data
  points per free parameter in a fitted rule); `W = 63` as a fast check. Report the window used.
- Half-life. Fit `s_t = a + phi s_{t-1} + e_t` by OLS on the last `W` observations. Half-life
  `h = -ln(2) / ln(phi)`, in observation units. Require 0 < phi < 1; if phi is at or above 1 the spread has no
  measurable reversion and the trade is a directional bet (no half-life). House rule: fewer than about 100 observations is too few
  to trust a half-life (Darbyshire, 2022, asks for at least 100 points per instrument before trusting a covariance estimate).
  The estimate is noisy: `se(phi) ~ sqrt((1 - phi^2) / n)`, so with n = 252 and phi = 0.98 (h about 34 days) the 2-se range
  0.955 to 1.005 spans h of 15 days to no reversion. OLS also biases phi low in short samples (half-life too short). Quote h with
  its range, use daily (non-overlapping) observations for the fit, and do not trade on h alone.
- Half-life drift: `h_now / h_entry`. House default bands (not from the sources): above 2 = the spread has slowed down
  and the thesis is weakening, re-underwrite; below 0.5 = check for a structural change in the spread or a data break before
  treating it as good news.
- Level drift: `z_now` against `z_entry`. A z that moves further against the trade for many days is a warning, not a
  stop by itself. Do not fade a spread that is still blowing out; wait for it to stabilise (BofA, 2 Oct 2026). Fade deep
  value only: "You never fade at fair value. You fade deep value." (JWS Macro, 21 Jun 2026).
- Break test on the mean (regime check). Use a CUSUM on levels: `S_nt = (y_t - y_n) / (sigma_t sqrt(t - n))`; the 5%
  one-sided critical value is `sqrt(4.6 + ln(t - n))`; take the supremum over reference points `n` (Lopez de Prado,
  Advances in Financial Machine Learning, 2018). A break says the mean may have moved: re-underwrite before using the old
  target.
- Benchmark rolls create fake slope and fly jumps. Use spline or constant-maturity yields. Example: OBL177 to OBL178
  on 25 Jul 2018 created fake 2s5s steepening and 5s10s flattening (During, Fixed Income Trading and Risk Management, 2021).
  Re-check any spread history that spans a switch.
- Exit calibration on history is overfitting when phi is near 1 (Lopez de Prado): do not re-tune a live book on a
  backtest, and do not change a parameter after one loss (Chan).

### 4. Stops, targets, time stops and the exit cost check
Use the full derivation in [references/exit_theory.md](references/exit_theory.md). Working rules:

- Target (mean reversion): halfway from entry to the mean or tighter. The source rule is "target halfway to the mean or
  tighter" (Huggins and Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024). Target = `entry + 0.5 (mu - entry)`
  for a spread below its mean that is expected to rise.
- Stop (reversion): at 2 stationary standard deviations beyond the mean, on the adverse side: `stop = mu - 2 sd_stat`
  for a long-spread trade entered below the mean. `sd_stat = sd(e) / sqrt(1 - phi^2)` from Method 3. Two stationary
  sd is the stop used in the Leung and Li (2016) model example. House default; the optimal stop depends on costs and
  reversion speed (Leung and Li). A stop at or above roughly the mean (for a long-spread trade) leaves no room to wait
  and forces liquidation (Leung and Li).
- Stop (regime): add a structural stop at the level where the thesis is invalid, and a P&L stop at the pre-committed
  maximum loss Z (set before entry; "plan in advance how to get out cheaply", Tulchinsky and Khan, Finding Alphas, 2015).
  Capital at risk is essentially the stop loss (Citi, Emerging Markets Strategy Weekly, 20 Aug 2026).
- Reversion trades and noise stops: a pure mark-to-market stop on a mean-reverting spread tends to exit at the worst
  moment; a rerun gives a stronger same-sign signal (Chan). Use structural and time stops for reversion trades. Keep
  the P&L stop as a risk-budget limit.
- Time stop: default 2 half-lives from entry (house default). Reason: the observed normalisation times in the sources were
  months, not days (BNP, EUR curve convexity, 25 May 2021: average 3.1 months to fair value, 2.7 months from fair value to
  overshoot). Always keep a time limit: a trade with no vertical barrier "could mean being locked on a losing position for
  years" (Lopez de Prado).
- Reward-to-risk: recompute on the current levels after every reset. Entry and each reset need at least 1.5:1 (Citi
  radar screen). Example: target +$450K, stop -$225K is 2:1 (Citi, Turning Green from Blue on short convexity, 6 Jun 2017).
- Trailing stop: each time P&L rises by a fixed amount, raise the stop by the same amount. After the target is hit, move
  the stop to the target and set a new target (During, 2021).
- Re-target only when the new levels pass the reward-to-risk screen and the thesis is unchanged. ING raised a EUR 2s7s10s
  target from 91 to 101bp and tightened the stop from 61 to 86bp (ING, 3 Mar 2020).
- Widen a stop only with a written rationale (Citi, 12 Aug 2026: stop widened from -10 to -12bpv because the balance of
  risk was still elevated). Tighten only after a favourable move (BNP: stop moved to -4bp, just above the -5bp entry).
- Exit cost check: the target must clear the round-trip cost on the spread. Higher exit cost moves the optimal take-profit
  level up (Leung and Li). If costs have blown out, the peak mark is not realisable: wait for costs to normalise.

Illustrative (not from the sources): spread mean 0, 2 stationary sd = 10bp, entry -6bp. Halfway target -3bp, stop -10bp.
Reward 3bp against risk 4bp is a ratio of 0.75, below the 1.5:1 screen. Wait for a better entry or reject the levels.

### 5. Hedge and risk maintenance
- DV01 neutrality: `DV01 = (P(y - 1bp) - P(y + 1bp)) / 2` (central difference, positive for a long position; Tuckman and Serrat). Re-size each leg when
  DV01 changes. House default band (not from the sources): re-hedge when net DV01 drifts beyond 5% of gross leg DV01 or when
  a 20bp move has occurred in the hedged market. Citi re-sized long-end delta hedges on each 20bp move in its 2019 book.
- Beta drift: when a curve trade becomes directional (steepens in rallies, flattens in selloffs), re-weight by the empirical
  beta rather than closing. Example: beta 1.025 of 15y5y against 20y10y; scale the DV01-neutral 20y10y leg by 1.025 and keep
  the delta hedges at the same beta (Citi, Reweighting delta-hedged 15y5y/20y10y flatteners, 16 Oct 2019). The 15y5y
  notional of $149.5mn then needed a 20y10y leg of about $84mn (81.97 x 1.025).
- Vega and vomma (skew and convexity packages): compute net vega, vomma and vanna each day. Second-order drift:
  `dP ~ Delta dS + 1/2 Gamma dS^2 + Vega dsigma + 1/2 Vomma dsigma^2 + Vanna dS dsigma`. Bachelier vomma is about
  `Vega d^2 / sigma` with `d = (F - K) / (sigma sqrt(T))`; OTM wings carry more vomma.
  Source thresholds (Rhodes, USD 3m2y payer skew, 8 Oct 2025): resize when |net vega drift| > 5 abpvs or the net rate move
  > 5bp; re-strike a wing that drifts more than 5bp from target; after a +/-5bp shift re-centre the wings and refresh the
  ATM hedge. Example: net vomma 0.9 and a +5 abpvs move give second-order P&L of 1/2 x 0.9 x 5^2 = +11.25 and net vega
  of about +4.5; trim the ATM straddle to re-flatten.
- Swap hedge for a package: `N_swap = -(sum_i N_i Delta_i) / DV01_swap`.
- Hedge decay: DV01 and PVBP age. Use forward PVBP matched to the holding period, or refresh the ratios on each rebalance.
  OLS hedge ratios are asymmetric; PCA or orthogonal regression is preferred for spread hedges (During, 2021).
- Futures strip: rehedge daily in theory; the front contract loses sensitivity and drops out at settlement. Longer
  intervals can be acceptable at some rate levels (Huggins and Schaller, SOFR Futures and Options, 2022). Check the
  Treasury-to-SOFR basis, because the hedge only holds while it is stable (see the March 2020 example in the worked examples).
- Risk bleed: as time passes, tenors move against fixed risk-model inputs. A 4y swap is 4y risk today, and as a 3.5y it
  shows about half in each of 3y and 4y under log-linear discount factors. Bleed is invisible to VaR. Monitor a bleed
  column (today's open against yesterday's close) and time large re-hedges to when tenors align with trade dates
  (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022).
- Delta-hedge timing: the time of day at which delta hedges run changes the realised vol a short-gamma book is exposed to.
  Fix the hedge time in the write-up and log the time used.
- Trade-level VaR (when the book needs it): `c = sqrt(S' Q S)`, S the bucket risk strip, Q the covariance of bp changes;
  `VaR_5% = 1.644 c`, `VaR_1% = 2.326 c`. Rank trades by their contribution to `c`, not by size. A negative
  contribution means the trade diversifies the book, so do not cut it for risk reduction. Trade about 50% of a suggested
  VaR-minimising cut and re-run; only one single-instrument VaR-minimising trade is valid at a time (Darbyshire, 2022).

### 6. Convexity and carry monitor (delta-hedged flatteners, short-gamma and vol-carry trades)
- Daily breakeven `BE`: the daily move in rates that gives a convexity gain offsetting the negative daily carry; set to
  zero when carry is positive. Realised vol `RV`: the trailing one-year standard deviation of daily moves in bp.
  Monitor `BE / RV`. Lower means convexity more than pays carry. Exit when carry deteriorates and `BE / RV` rises toward 1,
  even if the curve thesis is intact (Citi, Taking profits on delta-hedged 15y5y/20y10y flatteners, 5 Dec 2019; exit at
  carry as low as -2bp per year and `BE / RV` of 0.8).
- Screen values on 5 Dec 2019 (Citi): USD 15y5y/20y10y `BE/RV` 0.80 with carry -2.09bp and BE 3.33bp; GBP same structure
  `BE/RV` 0.26 and judged the better value.
- Short gamma: P&L can arrive with no curve move (realised vol delivered about $187K while the curve steepened about 2bp).
  Watch implied against realised vol, and the time of hedging.
- Curve-vol correlation can flip. Higher gamma demand tends to come with flatter curves and cheaper bellies, so a long-gamma
  book may be paired with flatteners or belly-cheapening flies (Citi EUR, 12 Aug 2026). Monitor it on the book's own legs.

### 7. Re-underwriting (thesis check)
Re-underwrite whenever a trigger fires, a driver changes, or the trade is within two days of a major event. Ask the
questions in writing, and answer from current data:
1. "If you did not own it today, would you buy it?" (Golub, 2023)
2. "What could happen to this position that would convince me that I don't understand the relevant market forces?"
   (Golub, 2023; Tuckman and Serrat, 2022)
3. "What has changed within the last five minutes...?" and "What do they know that I don't?" (Aikin, STIR Futures, 2012).
   When the questions stop, conviction has become dogma.
Interventions under strain: re-underwrite the thesis, and have someone not involved review it (Golub, 2023).

Driver-based examples from the sources:
- A flattening driven by aggressive QE can reverse when supply returns: take profit when the driver is policy flow that
  issuance may offset (Citi, GBP 15y10y/25y10y, 26 Mar 2020; the trade was closed on that basis).
- A forecast change can break a receive idea near its stop, for example an added ECB hike. Re-underwrite rather than hold
  (Nordea, EUR rates, 26 Sep 2025).
- Idea progression: once half-way to target, switch from the curve trade to the outright (Nordea, 19 Jun 2025).
- A dislocation can be a harbinger of a bigger move: understand it before fading (During, 2021).

### 8. Add, reduce and exit rules
Actions are one of HOLD, ADD, REDUCE, RE-WEIGHT (beta or DV01), RE-TARGET, EXIT-TARGET, EXIT-STOP, EXIT-TIME,
EXIT-THESIS, EXIT-OTHER (e.g. better use of capital), each with a reason code.

- ADD only when all of these hold: (a) the re-underwriting questions pass on new evidence, not on the price move alone;
  (b) the stop has not been hit; (c) the add keeps DV01 or vega inside the budget; (d) the stop, target and reward-to-risk
  are reset and re-screened. Martingale adding after losses does not create an edge: with stakes depending only on past
  outcomes in a subfair game, expected capital does not rise (Billingsley, Probability and Measure, 1995). Never add to fix
  a loss. Keep reserve size for a signal that strengthens before it weakens (Lopez de Prado).
- REDUCE (partial) when the edge shrinks but the thesis holds: a short 3m10y straddle book was halved from $100mn to $50mn
  at 59 normals, about 3 normals rich (Citi, Gamma and Vega RV, 14 Jan 2019). Cut size rather than exit when vol rises on a
  long-term conviction trade (ING, 3 Mar 2020).
- Scale in and out by thirds if the instrument allows it: one third on confirmation, one third on a retest, one third on
  the final leg; exits in reverse (BofA technicals primer, 2025).
- EXIT-TARGET: take the target. Taking profit before target on convergence is allowed if a better opportunity exists; document
  it as early exit for a better use of capital, not as a failed trade (Citi, 6 Jun 2017).
- EXIT-THESIS: the driver has changed or a kill criterion fired. Do not wait for the stop.
- Model-residual exits: unwind a spread-curve trade when its model residual (for example a term-funding-premium residual on
  maturity-matched swap spreads) is within one standard error of zero (JPM, IRD Strategy Update, 5 Nov 2025).
- EXIT-STOP: stop hit. Close. Do not re-enter the same write-up. A re-entry is a new trade with its own write-up and a
  better entry level (Citi, Commodities, 19 Aug 2026: "look for a better re-entry"; a non-G10 example).
- Do not exit mechanically at a zero fly residual. Overshoots of 5 to 10bp past fair value are typical and usually come within about 3 months (BNP, 2021).
- Sizing: Kelly with half-Kelly on a trailing window of about 6 months for one-day holding, re-estimated at least daily. Cap leverage
  at (tolerable one-period drawdown) / (worst historical one-period loss); use the smaller of that cap and half-Kelly.
  Worked: a 20% tolerance against a 20.47% worst day gives a cap near 1.0, below the 1.26 half-Kelly (Chan, 2009, an equity-index example; a rates book needs its own worst day).
- Decaying model: de-lever gradually as the trailing mean and sd move, rather than shutting off in one step (Chan).

### 9. Execution while monitoring
- Never leg out of a closing spread: the first cut is always the cheapest (Aikin, 2012). Fill the least liquid leg first for a
  term spread or bundle, and check implied bids before relying on them.
- Trim before a session you cannot monitor, and avoid overnight exposure in deep-play volatility (Aikin, 2012).
- Liquidity can vanish exactly when a stop is needed. On 15 Oct 2014 the 10y yield moved 16bp down and 16bp up within 12
  minutes against a daily sd of about 4 to 5bp; depth collapsed (Tuckman and Serrat, 2022). Size the stop for that.
- Wide wing bid-offers make delta hedging costly and can justify deferring an attractive trade (Citi, 27 Mar 2020).
- Post-stop behaviour in basis and swap spreads: the next move is uncertain; sometimes nothing is the right action until a
  new setup appears (Conks, money-market note, 17 Apr 2025).

### 10. Event calendar and regime monitors
- Decide hold, reduce or hedge for each event before it happens. Example from the sources: a Jackson Hole meeting was flagged
  as a risk to a short-convexity trade that was closed on the dislocation normalising (Citi, 8 Aug 2017).
- Auctions: score each bond on 3m z-scores against its fitted curve, its surrounds and its closest-rated peer, and log the
  pre- and post-auction move (Citi EUR, Morning Call, 12 Aug 2026; `auctions` table).
- Quarter- and year-end: repo and funding can spike. Around the 15 Apr 2025 tax date, SOFR and TGCR rose to about 4.35 to
  4.36 against EFFR 4.33 and fell back by 16 Apr (Conks, 17 Apr 2025). Check specials, repo tenor and funding maturity.
- Vol regime: relative-value relationships can break under a rates vol spike. JPM reported weighted steepeners stopped out
  by a vol regime shift although the thesis still held (JPM, 6 Mar 2020). Treat a vol regime shift as a stop reason.
  House default trigger (not from the sources): 1-month rates implied vol up more than 50% in a month triggers a review of
  every trade with vega or convexity.
- Crowding: crowded holders unwinding together cause fire sales and cascading widening (CFTC Market Risk Advisory Committee,
  Treasury cash-futures basis, Dec 2024). Year-end pension receiving can hit steepeners (Nordea, 26 Sep 2025). Prefer
  risk orthogonal to the crowd, and watch short interest and the special rate for squeeze risk.

### 11. Repo, specials and basis monitors (cash-futures and swap-spread trades)
- Specials: a bond is on special when its reverse RP rate is below GC. Long basis in a special that returns to GC loses
  as its RP rate rises; short basis in a GC bond that goes special loses as its reverse RP falls (Burghardt et al., The
  Treasury Bond Basis, 2005).
- Short-side carry: reverse RP on readily available collateral is typically 10 to 25bp below the RP rate; specials have no floor.
- Three squeeze warning signs (Burghardt): a declining RP special rate, large short sales in the issue, changes in the issue's
  yield spread to similar issues. A squeezed short has no theoretical maximum loss; a stop cannot cap a squeeze.
- Term versus overnight financing: a long basis loses if overnight RP rises; a short basis loses if overnight RP falls.
- Option-adjusted basis (OAB = actual basis minus theoretical basis): OAB above zero, sell the basis; below zero, buy it
  (Burghardt, 2005). Vol-arbitrage residuals: deliverable yield-spread changes, repo, profile mismatch between basis and option payoffs, and expiry about a month before futures last trade.

### 12. Decision journal and process versus outcome
Each trade gets a journal with three records: the entry (from the write-up), each monitoring event (date, metric, rule id,
decision), and the exit (reason code, P&L in bp, currency and risk units).

Score the decision process separately from the outcome. For each closed or stopped trade, mark yes or no:
1. Entry rule met as written (reward-to-risk at least 1.5:1; named risk recorded).
2. Sized inside the risk budget at entry and on any add.
3. Stop set at entry and not moved adversely.
4. Re-underwriting done on time at each fired trigger.
5. Exit reason coded against the rule set.
6. No unplanned add or re-tune after a loss.

Then classify:
- Good process, good outcome: keep the rule.
- Good process, bad outcome: expected loss; do not change the rule.
- Bad process, good outcome: lucky; record it as a process failure.
- Bad process, bad outcome: fix the process first.

Behavioural measures (Golub, 2023): over a rolling six months, compare the daily probability of realising a gain with the
probability of realising a loss. One FX case showed a manager twice as likely to take a gain as to cut a loss, with cost
peaking at about 2.5%. Measure the cost: the subsequent three-month performance of losers held against winners reaped, weighted by size.

Statistical honesty:
- Skill is slow to show. The standard error of an information ratio is about `1 / sqrt(years)`; sixteen years are needed to
  show an IR of 0.5 at t = 2 (Grinold and Kahn, Active Portfolio Management, 1999).
- A closed-trade hit rate is noisy. 34 winners in 47 trades is 72%; the normal-approximation 95% interval is roughly 60% to
  85%. Do not read a book's hit rate as skill without that interval.
- Multiple-trial control: the source bar is a deflated Sharpe ratio above 0.95 at the 5% level, for a long record that has
  survived many trials (Lopez de Prado, 2018).
- Peer tables are not evidence: they ignore survivorship and risk adjustment (Grinold and Kahn, 1999).
- Live forward tracking is the only true out-of-sample test (Tulchinsky and Khan, 2015). Judge live performance against the
  in-sample drawdown size and duration. A breach triggers re-underwriting, not re-fitting.

Journal line template (one per event):
`date | trade_id | metric (z, half-life ratio, BE/RV, DV01 drift, etc) | rule id | decision (action) | reason | next review date | kill criteria still valid (y/n)`

## Worked example(s)
Full numbers and sources are in [references/worked_examples.md](references/worked_examples.md). The three that show the logic:

1. Delta-hedged flattener exit (Citi, 5 Dec 2019). USD 15y5y/20y10y: 1y carry -2.09bp, daily BE 3.33bp, `BE/RV` 0.80.
   The curve stood at -12.5bp at exit, P&L about $187K at mid and $155K booked net. The exit was on carry and `BE/RV`, not on the curve.
2. Vomma drift (Rhodes, 8 Oct 2025). Net vomma 0.9, +5 abpvs: second-order P&L +11.25 and net vega about +4.5. Trim the
   ATM straddle; the threshold is 5 abpvs.
3. Fly residual that overshoots (BNP, 25 May 2021). Seven rich-fly episodes since 2013; normalisation came with a flatter
   10s30s six times out of seven, and overshoot to +5bp or more six times out of seven. A mechanical exit at zero residual
   would have sold before the overshoot.

## Signals and interpretation
| Trigger | Threshold (source or house) | Action and reason code |
|---|---|---|
| Stop level hit | level (set in write-up) | EXIT-STOP; no re-entry under the same write-up |
| Target hit | level | EXIT-TARGET, or RE-TARGET if the new levels pass 1.5:1 and the thesis is unchanged |
| Time stop | 2 half-lives from entry (house) | EXIT-TIME, unless re-underwriting passes on new evidence |
| Half-life ratio | `h_now / h_entry` above 2, below 0.5 (house) | RE-UNDERWRITE; below 0.5 check for data break first |
| Break in mean | CUSUM above `sqrt(4.6 + ln(t-n))` (5%) | RE-UNDERWRITE; old target may be stale |
| Residual P&L | |residual| > max(20% of |total|, 2 sd of 60-day residuals) (house) | Fix the model or data first; no trade action on P&L alone |
| `BE/RV` rising toward 1 with falling carry | BE/RV toward 1 (Citi) | EXIT-OTHER (carry and convexity exit) |
| z back inside 0.5 with target still ahead | z near zero | HOLD; do not exit on z alone (overshoot is normal) |
| DV01 drift | beyond 5% of gross leg DV01, or a 20bp move (house; Citi cadence) | RE-WEIGHT (hedge rebalance) |
| Vega drift | |net vega drift| > 5 abpvs or rate move > 5bp (Rhodes) | RE-WEIGHT (resize ATM hedge, re-centre wings) |
| Beta drift | empirical beta differs from entry by > 0.05 (house) | RE-WEIGHT (scale the other leg; keep delta-hedge beta) |
| Driver changed | driver named in write-up no longer true | RE-UNDERWRITE; take profit or exit if the change is adverse |
| Event within 2 days | scheduled | Decide hold, reduce or hedge in advance and log it |
| Vol regime shift | rates vol up over 50% in a month (house) | Review all vega and convexity trades; stop-out is valid (JPM, 2020) |
| One trade > 40% of day's P&L | 40% (Darbyshire example) | Consider banking the gain; check other risk |
| Specials or squeeze signs | special rate falls, short interest rises, issue spread changes | Review the basis short; cut size; check borrow |
| Blow-out with thesis intact | no stabilisation yet | HOLD, add nothing; fade only after stabilisation and at deep value |

## Pitfalls
- A stop set on the wrong side of the mean (at or past the mean) leaves no room to wait and forces an exit (Leung and Li).
- Mark-to-market stops on a mean-reverting spread exit at the worst moment (Chan). Use structural and time stops.
- A mechanical exit at zero residual is wrong (BNP overshoot evidence).
- The half-life is only as good as the window. A short window or a benchmark roll produces a fake half-life (During); with short samples the OLS phi is biased low.
- Reward-to-risk on the levels in the write-up is not the reward-to-risk now. Recompute on every reset.
- Delta-hedged convexity: realised vol minus carry bleed is the edge. Monitor `BE/RV`, not the curve alone.
- Do not re-weight risk-neutral legs to manufacture positive carry; that breaks the trade's logic (During, 2021).
- Hedge that explains zero P&L can still lose money: a hedge built on the wrong instrument set (Darbyshire).
- A large net DV01 can hide large opposing buckets. Look at bucket risk, not only the total.
- Stops do not cap gap losses; they only realise them. Gap risk needs a plan before the close (Chan, 2009; Darbyshire, 2022).
- Crowding: the most attractive basis short carries the greatest squeeze danger; a stop cannot cap a squeeze.
- A trailing stop is honoured even when the thesis seems intact: a trade was stopped after an exogenous shock overtook its story
  (Citi, Global Macro Trade Ideas Radar, 13 Aug 2026).
- Do not treat one print as a trend; one custodial flow print is data, not a regime.
- Source data flags to reconcile before reuse: one Citi note labels a leg "25y10y" that should be 20y10y;
  two Greens notes describe the hedge legs with different contract months and prices; a combined level in one trade does not
  reproduce from its entries (27 Mar 2020 arithmetic gives 53.75bp, not the printed 53.125bp). Verify before using these numbers.
- A hedge ratio from past averages is backward-looking: a position thought market-neutral can be a hidden beta position
  (Dunis et al., Applied Quantitative Methods for Trading and Investment, 2003). Re-estimate it.
- Benchmark rolls and bond switches create fake slope, fly and spread jumps (During, 2021).
- Expiry and roll: a futures-based trade rolls rather than holds; about 2.8% of Treasury futures go to delivery (CFTC, Dec 2024).
- Model mismatch: explain-the-P&L checks use a model. If the explain fails, the model is the suspect until proven otherwise.

## G10 market differences (for monitoring)
| Market | What changes for monitoring | Source |
|---|---|---|
| USD | Treasury basis and swap spreads move with repo specials, bill supply and the leverage ratio; SOFR-FF and TU/OIS basis monitors; the Sept 2019 repo spike and March 2020 as stress memories. Treasury squeezes are a special-rate story. | Burghardt et al. (2005); Tuckman and Serrat (2022); CFTC (Dec 2024) |
| EUR | Bund-referenced spreads (OAT-Bund 140 to 141bp on 1 Oct 2026, with backstops cited near 150bp); BTP and OAT spreads move with ECB buying and supply; Euribor and EUR STR meeting trades; fly residual histories (BNP since 2013); benchmark roll dates | Citi EUR (1 Oct 2026); BNP (2021); During (2021) |
| GBP | Gilt ASW and z-spread trades; gilt scarcity (one coupon trade closed on target as the 1/8% coupons ran down to two); gilt-Bund 170 to 175bp range cited; SONIA and FF basis; tax-driven coupon switches | BofA (5 Aug 2024); Citi (27 Mar 2020); BofA (2 Oct 2026) |
| JPY | JGB ASW, thin liquidity at times, BoJ path steepeners; xccy basis carry | BofA (2 Oct 2026); Huggins and Schaller (2024) |
| AUD | AU OIS against ESTR and 2s10s and 6s3s basis; RBA meeting pricing; issuance-driven basis | BofA (2 Oct 2026) |
| CAD, CHF, NZD, SEK, NOK | The source set has no monitoring-specific trade records for these markets; apply the generic rules here and state the gap. | (no source) |

## Scripts
- [`scripts/trade_monitor.py`](scripts/trade_monitor.py): OU and half-life fit (AR(1)), stationary sd, direction-aware reversion
  stop, rolling z-score, one-day P&L explain, DV01-neutral quantity, and trade status against target, stop and time stop. Run
  `python -I scripts/trade_monitor.py --help`. `--selftest` checks known answers (exact AR(1) recovery, half-life ln2/k,
  P&L sign, worked attribution sum, hedge quantity and status cases) and exits non-zero on failure. CLI example:
  `python -I scripts/trade_monitor.py --spread <csv with date,spread_bp> --entry-date 2026-02-13 --direction 1 --entry -8 --target -3 --stop -14 --window 252`.

## Output
Return four blocks, in this order:

1. Status table, one row per trade:
   `trade_id | structure | direction | entry | level now | pnl_bp | pnl (currency and risk units) | DV01 or vega (now vs entry) | z now (entry z) | half-life now / entry | target | stop | days held / max | status | action | reason code`
2. P&L explain per package: carry, roll, rates, spread, convexity, financing, cost, residual, total, with the scenario named and
   any residual flag.
3. Triggers fired and re-underwriting answers (the three questions), for each trade with a trigger. Name what would change the view.
4. Journal lines (one per event) and, when asked, the monitoring file under `ideas/` named `<trade_id>-monitor.md`.
   Include the data gaps and any source conflicts found.

Use the status and action vocabulary in Method 8. Do not state a P&L figure that the data did not produce, and do not
produce a new stop or target without the reward-to-risk check. Hand new trade ideas off to
[rv-opportunity-scan](../rv-opportunity-scan/SKILL.md) and write-ups to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Related skills
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): the entry record this skill monitors (levels, driver, named risk).
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): kill criteria and pre-mortem, used again at re-underwriting.
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): where replacement ideas come from once a trade is closed.
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): re-score a trade on the composite after a trigger, before deciding to add.
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): how to close or resize a package without legging.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll definitions and scenarios used in the P&L explain.
- [curve-butterflies](../curve-butterflies/SKILL.md): fly residual monitors and weights.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): beta and directionality drift in curve trades.
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): delta-hedged flattener convexity and the BE/RV screen.
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): futures expiry and roll for strip and basis hedges.
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): benchmark-roll breaks and stale data in spread histories.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01, key-rate and hedge mapping.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): OU fit, half-life and first-passage details.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score windows and robust statistics.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): hedge-ratio estimation and decay.
- [quant-regime-detection](../quant-regime-detection/SKILL.md): regime tests behind the break monitor.
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): signal half-life and shelf life of old scores.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): risk budgets, Kelly caps and drawdown limits.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): stress checks on the book under vol and curve shocks.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): gamma, vega and theta P&L and delta-hedge timing.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): basis trade monitors and implied repo.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): specials, repo tenor and funding stress.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread and ASW convention and monitors.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event-date risk for the calendar.
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): attribution and return on risk across trades.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): when a monitor rule is overfit, and deflated Sharpe.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): costs, no-trade bands and liquidity regimes.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used in the inputs.
- [eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md): layout of the monitoring report.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): the implied policy path.
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): swaption and cap/floor vol RV.
- [xccy-basis](../xccy-basis/SKILL.md): cross-currency basis.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): regimes and scenario trees.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CCP basis between clearing houses.
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): tenor and index basis, including SOFR-FF.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR strip calendars, flies and packs.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA factors, neutral weights and residuals.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-grid RV, kinks and aged forwards.
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): breakevens, linkers and inflation swaps.
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): CTD switch and delivery options.
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): invoice spreads and futures asset swaps.
- [quant-cointegration](../quant-cointegration/SKILL.md): cointegration tests and level hedge ratios.
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): CFTC, survey and real-money positioning.

## References
- Citi Research - North America Rates Trade Idea notes on delta-hedged 15y5y/20y10y flatteners (Ruslan Bikbov, 16 Oct 2019; 5 Dec 2019): beta reweighting, DV01 changes, breakeven versus realised vol screen, exit on carry and BE/RV.
- Citi Research - Taking profits on GBP 15y10y/25y10y flatteners (Ruslan Bikbov, 26 Mar 2020): curve versus convexity P&L split, profit-taking on driver reversal.
- Citi Research - short Greens convexity notes (Ruslan Bikbov, Jason Williams, 6 Jun 2017; 8 Aug 2017): 2:1 stop and target, early exit for a better trade, dislocation normalisation, event risk.
- Citi Research - US Rates Vol Lab: Gamma and Vega RV (Ruslan Bikbov, Jason Williams, 14 Jan 2019): partial position cut, hedge timing, vega trades.
- Citi Research - US Rates Weekly: All it takes is a little push (Jabaz Mathai et al., 4 Oct 2019); Eat, pay, spend (27 Mar 2020): model portfolio, closed-trade appendix, return-on-risk method, open book with stops, wide-wing hedge costs.
- Citi Research - Global Macro Trade Ideas Radar (Luis Costa et al., 13 Aug 2026): inclusion and risk-to-reward screen, stop breach, lessons-learned log.
- Citi Research - European Rates Weekly: What to do about OATs? (Jamie Searle et al., 1 Oct 2026): OAT-Bund levels, open and closed book with targets and stops.
- Citi Research - European Rates, The Morning Call (12 Aug 2026): balance-of-risk metric, curve-vol correlation, auction scoring, stop widened with a written rationale.
- Citi Research - Emerging Markets Strategy Weekly (Luis Costa et al., 20 Aug 2026): capital at risk equals the stop loss; historical-vol stops understate jump risk.
- BofA Global Research - Technicals Explained: In 2025 (Paul Ciana and Stephen Suttmeier, 14 Jan 2025): scaling by thirds, ATR and trend-break confirmation, oscillator overlays on spreads.
- Citi Research - Global Commodities: Taking Profit on Sugar Trade and Closing Coffee Trade (19 Aug 2026): take profit at price target versus trade target; re-entry after a stop (non-G10).
- BNP Paribas - EUR curve convexity: Lessons from history (Eric Oynoyan, Marco Meijer, 25 May 2021): fly residual episodes, overshoot rule, live target and stop.
- J.P. Morgan - North America Fixed Income Strategy: Impossible to walk in this muck (Joshua Younger et al., 6 Mar 2020): take-profit levels, vol-regime stop-outs, 12-month closed-trade scorecard.
- Ade Rhodes - Trade Idea: USD 3m2y Payer Skew Steepener (8 Oct 2025): vega, delta and vomma formulas, rebalance thresholds.
- ING Global Markets Research - EUR crisis trades: let's get tactical (Antoine Bouvet et al., 3 Mar 2020): re-targeting, size-cut rule instead of exit.
- Nordea Markets - EUR rates notes (Anders Svendsen, 19 Jun 2025; 26 Sep 2025): stops and targets for receiving trades, half-way switch to the outright, re-underwriting after a forecast change, crowding.
- BofA Global Research - UK Rates notes (Agne Stengeryte, Mark Capleton, 5 Sep 2024; 5 Aug 2024): explicit entry, target, stop and named risk; tax-driven switch with scarcity exit.
- BofA Global Research - Global Rates Weekly: Start of rates bite (M. Cabana et al., 2 Oct 2026): backstops, vol-spike breakdown of RV, stops hit, wait for stabilisation.
- Leung, Tim and Xin Li - Optimal Mean Reversion Trading: Mathematical Analysis and Practical Applications (World Scientific, 2016): optimal take-profit and stop levels, entry band, minimum holding period, exit costs.
- Lopez de Prado, Marcos - Advances in Financial Machine Learning (John Wiley and Sons, 2018): triple-barrier exits, OTR calibration, sizing ramps, break monitors, binomial and deflated-Sharpe tests.
- Huggins, Doug and Christian Schaller - Fixed Income Relative Value Analysis (2nd ed., John Wiley and Sons, 2024): OU exit rules, target halfway to the mean, first-passage analysis, PCA residual reading.
- Huggins, Doug and Christian Schaller - SOFR Futures and Options: A Practitioner's Guide (John Wiley and Sons, 2022): strip hedge maintenance, hedge drift and the March 2020 example, date mismatch.
- Tuckman, Bruce and Angel Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., John Wiley and Sons, 2022): stepwise P&L attribution, DV01 by central difference, flash-event liquidity.
- Darbyshire, J H M - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch and Dee, 2022): risk bleed, daily P&L explain against a risk model, CoVaR and VaR-minimising trades, take-profit and gap risk.
- During, Alexander - Fixed Income Trading and Risk Management (John Wiley and Sons, 2021): trailing stops, hedge calibration against unexplained P&L, benchmark-roll hygiene.
- Burghardt, Galen et al. - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): special and repo mechanics, squeeze controls, option-adjusted basis monitoring.
- CFTC Market Risk Advisory Committee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): mark-to-market attribution, crowding, repo and funding monitors.
- Golub, Bennett W. (ed.) - BlackRock's Guide to Fixed-Income Risk Management (John Wiley and Sons, 2023): risk-change decomposition, disposition-bias measurement, re-underwriting questions, short-sample caveats.
- Grinold, Richard and Ronald Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): information horizon, no-trade bands, cost amortisation, skill versus luck.
- Chan, Ernest P. - Quantitative Trading (John Wiley and Sons, 2009): exit types, half-life exit horizon, stop-loss theory for reversion, Kelly and leverage caps, live-versus-backtest diagnosis.
- Aikin, Stephen - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): legging order, liquidity, conviction versus dogma.
- Tulchinsky, Igor and WorldQuant Virtual Research Center - Finding Alphas (John Wiley and Sons, 2015): pre-committed cut rules, live forward tracking as the true out-of-sample test, drawdown benchmarks.
- JWS Macro - Central Casting #6.1 (21 Jun 2026): "fade deep value, not fair value" rule.
- Conks - Money Market Update (Substack, 17 Apr 2025): tax-day repo spike, "do nothing" after a stop in basis and swap spreads.
- Citi Research - US Rates Weekly: OAT of the blue (Jason Williams et al., 2 Oct 2026); Citi Research - Alert: Taking profits on long end butterfly trade (Jabaz Mathai, Jason Williams, 15 Jun 2020); Alert: Take off the hedge on short Greens convexity trade (Ruslan Bikbov, Jason Williams, 13 Jul 2017): stop and target screen, cost normalisation before exit, hedge unwind.
- J.P. Morgan - IRD Strategy Update: No alarms and no surprises (Ipek Ozil et al., 5 Nov 2025): model-residual unwind rule.
- Ross, Sheldon M. - Introduction to Probability Models (10th ed., Academic Press, 2010): driftless stop and target hitting probabilities.
- Billingsley, Patrick - Probability and Measure (3rd ed., John Wiley and Sons, 1995): futility of martingale adding on a subfair game.
- Dunis, Christian L. et al. (eds.) - Applied Quantitative Methods for Trading and Investment (Wiley Finance, 2003): backward-looking hedge ratios and hidden beta.
