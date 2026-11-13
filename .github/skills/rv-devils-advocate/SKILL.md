---
name: rv-devils-advocate
description: Adversarial pre-trade review of a G10 rates relative-value idea (curve steepener/flattener/fly, swap spread/ASW, bond or futures basis, STIR/FRA/SOFR/Euribor/SONIA spread, cross-market govie spread, vol or inflation RV). Plays devil's advocate - pre-mortem, alternative explanations for the apparent mispricing, regime and structural breaks, crowding and positioning, liquidity and exit cost, financing/haircut/margin stress, carry and convexity traps, model and hedge-ratio risk, event calendar, correlation with the existing book, numbers to recompute independently, pre-committed kill criteria - and returns a verdict, ranked top risks with scenario P&L, and kill criteria. Use when asked to challenge, stress-test, red-team, sanity-check or pre-mortem a trade, "what could go wrong", "why is it cheap", "is this crowded", "where is my stop", invalidation, kill criteria or risk review before sizing or sending an idea; used by the rv-risk-reviewer agent.
argument-hint: "<trade idea to challenge>"
---

# RV devil's advocate (adversarial pre-trade review)

Every RV screen produces false positives: most apparent mispricings are explained by something the screen does not
model (option value, financing, a balance-sheet constraint, a regime shift, a flow that is still running). This skill
is the cross-examination step between "the screen says rich/cheap" and "size it". It does not look for reasons to
reject; it forces the thesis to name the mechanism that closes the spread, the evidence that it has stopped working,
and the loss in the scenarios that hurt, then ends in a verdict and kill criteria fixed before entry. One source's
conclusion on a full RV screen of one vol sector was that "a proper relative value analysis leads to the correct
conclusion that there are no good relative value trades" and that this is "the more frequent experience"
(Huggins & Schaller, Fixed Income Relative Value Analysis, 2024).

## When to use
- Any trade idea about to be sized, written up (`rv-trade-idea-writeup`) or sent: "challenge this", "red-team it", "pre-mortem".
- "Why is it cheap/rich?", "what is the other side of this trade?", "is it crowded?", "where do I get out?", "what would make me wrong?".
- Re-underwriting an open position after a large move (feeds `rv-trade-monitoring`), or before adding.
- Not for finding trades (`rv-opportunity-scan`) or scoring them (`rv-composite-scoring`).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Trade ticket: legs, side, DV01 per leg (ccy/bp), entry level, target, stop, horizon, size | `trades`, `positions` | per trade | the idea under review; DV01 positive = long duration |
| Existing book | `positions`, `pnl` | current + >= 1y daily | for correlation/overlap and worst-day history |
| Spread/level history of the trade as quoted | `curve_par`, `swap_spreads`, `bond_quotes`, `fut_quotes`, `stir_quotes`, `vol_surface` | daily, >= 3y (>= 252 points per fitted parameter) | same snap and the same instruments as the signal |
| Financing | `repo_rates` | daily, own-issue/special where shorting | GC is not the short leg's rate |
| Deliverable set, conversion factors (basis trades) | `fut_basket`, `fut_static` | current | CTD switch and early-delivery checks |
| Positioning / flows | `positioning`, `flows_trades`, `auctions` | weekly/daily | crowding measures |
| Event calendar | `cb_meetings`, `calendars`, `events_probs`, `roll_map` | forward-looking through horizon | meetings, data, auctions, roll/expiry, quarter-end |
| Signal and its trial history | `signals` | full research record | number of configurations tried |

If an input is missing, say which lens could not be run and cap the verdict at HOLD; ask for it or hand off to the
`rv-data-engineer` agent. Never invent values. Table definitions: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Method
Run every lens; stop early only on a RED that is already fatal (lens 0, 5 or 6). Conventions: yields/spreads in bp;
curve spread = longer - shorter; fly 2s5s10s = 2x5y - 2y - 10y; swap-spread sign as stated in the ticket (US: swap
yield - Treasury yield; EGB ASW: bond yield - swap rate); DV01 > 0 = long duration; first-order P&L =
`-DV01 x yield shock (bp)`. Numbers marked (default) are this skill's starting values, not sourced constants; change
them with a stated reason.

### 0. State the thesis so it can fail
Write three lines: (a) the **mechanism that closes the gap** (convergence at expiry, carry, a flow ending, policy
repricing, a constraint relaxing); (b) the **observable that would show the mechanism is not working** (a data series
and a level); (c) the **horizon**. A relative trade needs a named mechanism; "it is 2.3 sd wide" is not one. Stating
the mechanism is the reviewer's addition, derived from the sources' stress on binding constraints and on monitoring
which mechanisms are working now (Tulchinsky et al., Finding Alphas, 2015; Papic, Geopolitical Alpha, 2021). No
mechanism, or no falsifier, is RED: verdict NO-GO until supplied. Also fix the consensus position: when the view is
out of consensus the burden of proof sits with the market; once it is priced the burden shifts onto you (JWS Macro,
#8 Playing Devil's Advocate, Aug 2026). Check also Duering's trade ingredients: rationale, profit target and stop
sized to capital at risk, exit plan with a cost estimate at entry, and instruments/sizes consistent with the analysis
(Duering, Fixed Income Trading and Risk Management, 2021). Understand why the dislocation occurred before fading it: a small
dislocation can be a harbinger of a bigger move, and continuation may pay more than reversion (Duering, 2021). Test each
supporting datum for what it rules out; a non-diagnostic variable fits every hypothesis (Papic, 2021).

### 1. Pre-mortem
Assume the trade has hit the stop (or lost 2x the stop). Write the 3-5 most likely causes, one line each, and tag
each to a lens below. Rank by (probability class L/M/H) x (loss). Keep the ones that cannot be hedged or exited. The
pre-mortem output seeds the scenario table (lens 13).

### 2. Alternative explanations for the mispricing
List every non-mispricing reason the gap could be fair. For each, state the size of the explained gap in bp and
compare it with the signal. Only the unexplained remainder is the opportunity.
| Explanation | Test | Evidence |
|---|---|---|
| Embedded option value | basis: use option-adjusted basis net of carry, not raw gross/net basis or implied repo; raw implied repo is "poorly behaved" into roll and delivery | wildcard worth about 3 ticks in the ultra-long contract, 0.5-1.5 elsewhere, +50-100% when vol is high; ultra-long implied repo gaps 50-100bp to CTD term repo in delivery months from a few ticks of option value (JPM, Special delivery, Dec 2019) |
| Financing / specialness | price the short leg at its own-issue repo, not GC; reverse repo for plentiful collateral is 10-25bp below RP; specials have no floor (a 10y CTD traded at -15% in 2005) | Burghardt et al., The Treasury Bond Basis, 2005 |
| Coupon/liquidity premium | same-issuer same-maturity yield spread is not RV (higher coupon yields less on an upward curve); off-the-runs and CTDs often sit at negative OAS to the fitted curve | Huggins & Schaller, 2024; TBAC, Jan 2024 |
| Model misfit | if every bond in the "cheap" spline sector looks rich, the model does not fit and no mispricing exists; screens show asks, and repo/short-borrow/idiosyncratic demand absorb the gap | Duering, 2021; Tuckman & Serrat, Fixed Income Securities, 2022 |
| Balance-sheet constraint | the relevant cost is the shadow cost of the least onerous binding constraint; the marginal arbitrageur's capital, not yours, sets how far a no-arbitrage relation moves. Check which constraint binds before trading a regulatory headline (holdco vs bank subsidiary; leverage vs RWA); separate what regulators "ask about" from what they adopt | Huggins & Schaller, 2024; BofA, US Rates Watch, Jun 2025 |
| Benchmark switch / data | a benchmark roll creates a fake curve move (a 5y Bobl benchmark switch on 25 Jul 2018); stale prices; look-ahead timestamps | Duering, 2021; data-quality skill |
| Equilibrium moved | regime shift in the fair value itself (lens 3) | Lehman, LMR Quarterly, Oct 2003 |
| Structural demand/supply flow | asset-manager futures longs, pension or insurer target yields (JGB 10s30s pivot ~0.75%/2%), official-sector buying that cut JGB liquidity "to a trickle" | TBAC, 2024; Huggins & Schaller, 2024 |
Constraint-driven mispricings can widen before they close ("one man's constraint may be another man's
opportunity": BTPs may cheapen further if the ECB raises Italian haircuts). Scale the entry threshold up (default
+0.5 sd or +25% of the stop distance) when a government or regulator is on the other side (Huggins & Schaller, 2024,
Ch.18, Ch.20). Do not infer richness from a high hit rate of short-option-like trades: it "does not by itself prove
the options were overpriced" (Burghardt et al., 2005).

### 3. Regime and structural breaks
- Mean reversion is "nearly always off sides" across a regime shift: a positive shift in the equilibrium fly looks like cheapening and the trade is sold as the fly moves to its new level. Example: a 2s5s10s 34/66 fly (here 5y - 0.34 x 2y - 0.66 x 10y, i.e. bp per unit of 5y; the 2 x 5y - 2y - 10y convention is twice this for 50/50 weights) sat at 0bp; after a faster-recovery shift (2/5/10 at 4.326/4.729/4.865%) the fly is about 4.8bp, so an observed 4bp fly "looks 5s-cheap" against the old fair value of 0 but is about 1bp rich against the new one; long 5s lost about 15bp over five months in 2001 (Lehman, LMR Quarterly, Oct 2003).
- Macro-aware checklist (Lehman, 2003): state the macro assumption behind the trade and its hedge ratios; have a view on regime shifts (recovery speed, vol-curve curvature); size asymmetrically (large where the shift helps, small where it hurts); buy book-level protection net of cost. Desk trades share the same regime exposure.
- Tests the agent can run: rolling Engle-Granger cointegration (window 100-120 days, step 20; null = no cointegration, residual ADF needs Engle-Granger critical values, and the result changes with which leg is the dependent variable) with rolling beta; half-life tau = ln2/kappa against the horizon and margin tolerance (kappa 0.1 gives 6.9 periods, 0.3 gives 2.3); CUSUM/sup-ADF on log levels for strictly positive prices (use levels for spreads and flies that can be negative; sensitive to start point, so use the supremum over windows) (Brenndoerfer, Mean Reversion and Statistical Arbitrage, Dec 2025; Lopez de Prado, AFML, 2018). Cointegration is easy to find in-sample and easily lost out-of-sample (Palomar, Portfolio Optimization, 2025).
- Rule: if half-life > 1/3 of the horizon (default) the trade is mostly a random-walk bet; do not call a reverting spread an edge.
- High-inflation cycles break timing rules (end of hiking dangerous for receivers; inversion-to-cut lag lengthens); the neutral-phase trap: front-end receivers held as "free options" got "taken to the woodshed" as data firmed (Willer & Saunders, Trading Global Macro Markets, 2026; JWS Macro, Autumn 2025). Same words read hawkish or dovish depending on data; count votes not dots (JWS Macro, Central Casting, Jun 2026).
- Statistical significance of a regime difference is not economic significance: measure the P&L difference (Lehman, 2003).
- Sample sizes: conditional rates from 2-14 events or one observation per year are not evidence; compare with the unconditional base rate (BofA, Technicals Explained, Jan 2025; Willer & Saunders, 2026).

### 4. Crowding and positioning
Crowding is measured, not assumed. Pick the gauge for the trade type and report level, trend and the pain move.
| Trade | Gauge | Reading |
|---|---|---|
| Treasury basis long | levered-fund futures shorts (upper bound ~$600-650bn, "not likely more than half" in practice); futures OI as % of market; cash richening vs futures while OI grows; ultra-long basis cheapening despite high vol | peak ~$615bn (JPM, Mar 2020); scale futures-based proxy by 0.6-0.7, not 1 (CFTC OCE 2024-007) |
| Swap-spread widener/tightener | residual method (hedge-fund long UST minus all short UST incl. futures matched one-for-one with cash) | $631bn residual Q2 2025, an upper bound; 11% contraction in April 2025 turbulence (BIS Quarterly Review, Dec 2025, Box B) |
| Trend/CTA-sensitive trades | count of stop-outs in a 12-model ensemble (3 lookbacks x 4 stops) | >= 4 of 12 stopped coincides with above-average sigma moves (BofA Systematic Flows Monitor, Jun 2025) |
| Any futures/TFF market | net positioning beyond +/-2 sd of % open interest is contrarian; confirm with price trend; data are as of Tuesday, published Friday | BofA Technicals Explained, Jan 2025 |
| Index/constituent spread | skew vs constituents; the buyer's known size | Tuckman & Serrat, 2022, Ch.14 |
- Mechanism: a sudden tightening in funding or margin forces leveraged unwinds across exchange-traded and OTC markets; as capital chases a trade the share of return falls while risk rises, withdrawals are "precipitate", infusions slow (BIS, 2025; Tulchinsky et al., 2015). Correlations in an unwind go from 0.1-0.3 to 0.7-0.95 (Aug 2007; Brenndoerfer, 2025). Basis unwinds amplified but did not cause the March 2020 stress; estimated basis-exit sales $35-173bn (CFTC MRAC, Dec 2024), so attribute carefully.
- Pain move: name who is hurt by which move (real money overweight the belly via structural steepeners: a bear flattener is their pain trade; JWS Macro, Aug 2026). Crowded steepener in Europe "at an extreme" in 2014: positive-carry flattener as offset (Nomura, Erratum, Jun 2014).
- Rule (default): crowded in the direction of your trade -> require price-trend confirmation and halve size; crowded against -> look for the squeeze catalyst, but "a squeeze is not a bull market": a move whose only buyer is a short taking profit does not last (JWS Macro, Aug 2026). Positioning can stay stretched while issuance keeps a trend going.
- Unwind arithmetic (JPM, WFH, Mar 2020): half of a $600bn short is basis, half of that unwinds, ~$150bn; effects are futures richen, Treasuries cheapen vs OIS/SOFR, swap spreads tighten.

### 5. Liquidity and exit
- Cost to exit, not displayed depth: measure the share of a representative clip that fills wider than 0.5 tick; "optical" depth looked normal while about two-thirds of 30y flow filled wider on 9 Mar 2020 (JPM, WFH, Mar 2020).
- Days to exit = |position DV01| / (participation x ADV DV01); default participation 10%, flag > 3 days for a trade expected to be unwound in a stress (script `days_to_exit`). Chan's rule of thumb caps a single order at ~1% of ADV (Quantitative Trading, 2009); calibrate to the local contract.
- Illustrative floor: one published trade-radar admits ideas only with >= 100k DV01 (DM) or >= 40k (EM) of liquid, executable size (Citi, Trade Ideas Radar, Aug 2026). Use it as a sanity bound, not a rule.
- Flash events: 10y yield -16bp/+16bp between 9:33 and 9:45 on 15 Oct 2014 against a daily sd of 4-5bp (Tuckman & Serrat, 2022). Multi-leg trades and rare-security shorts face wider bid-offer and impaired repo exactly in the scenarios that protect (Duering, 2021).
- Operationally heavy, balance-sheet-heavy positions with limited upside are unwound first ("strong incentive to be the first out the door") (JPM, WFH, Mar 2020).
- Legging: never leg a closing spread; "go to the point of least liquidity first"; "the first cut is always the cheapest" (Aikin, STIR Futures, 2012). Write the exit cost estimate at entry (half the bid-offer x legs; a round trip is the full bid-offer x legs).
- G10 note: JGB official-sector buying; European futures have small deliverable sets and a fixed delivery day, so squeeze/fail risk is higher; see [market notes](references/market_notes.md).

### 6. Financing, haircut and margin survival
Size to funding stress, not only to price risk; hedges of price risk do not hedge margin risk (Tuckman & Serrat, 2022, Ch.10).
- Cash call = notional x (haircut_stress - haircut_now) (script `haircut_cash_call`). MF Global's repo-to-maturity book (peak $11.5bn, Jun 2011; haircuts on IE/PT from 3% to 80%; margin 2.9% -> 10.6% of position Jun-Oct 2011) was sized for a 15% average haircut and failed at end-Oct 2011; "had MF Global sized its position to account for the financing risk of increased haircuts, it might have profited rather than have been destroyed" (Tuckman & Serrat, 2022, Ch.10).
- Same trade, different financing: the March 2020 basis case (below) converged but needed ~$4mm cash in one day against a $2.5mm target. Daily closes understate intraday vol.
- Funding squeezes are not hypothetical: in Sep 2019 transaction-weighted repo averaged 5.25% on one day, one trade printed at 10%, with the policy range at 2-2.25% (Tuckman & Serrat, 2022, Ch.0).
- Tenor mismatch: repo shorter than the trade is rollover risk; the 99th-percentile repo minus SOFR was 10-11bp in Feb 2020, 20-50bp on several March days, 174bp on 16 Mar 2020 (Tuckman & Serrat, 2022, Ch.11). Basis-trade tolerance rule of thumb: ~15bp repo spikes do not matter, at least 50bp and up to 200bp near delivery are tolerated (Conks, Plumbing Notes, Nov 2025).
- Check cash-leg VM: it offsets futures VM only if margin is exchanged on the cash leg; correlation can break in stress; "small changes in overall correlations could result in large margin calls" (CFTC MRAC, Dec 2024). The counterparty's unilateral right to change haircuts or margin is a kill trigger.
- Leverage arithmetic: a convergence profit of (4/32)% on $1bn is $1.25mm; at 20:1 that is 2.5% on $50mm of capital over 141 days, about 6.5% annualised, about 13% at 40:1 (Tuckman & Serrat, 2022, Ch.11). Leverage of "up to 60x" is cited, and a March-2020-type drawdown wipes out the equity (TBAC, 2024; Conks, 2025). Thin annualised returns plus a margin spike is why these trades are forced out.
- Short leg: bleed = (GC - special repo) x notional per year; GC 5%, special 3%, $100mm short bleeds $2mm/yr (illustrative).
- Losing money and defaulting are different: the review must show the trade survives the financing scenario, not only that it is right.

### 7. Carry, roll and convexity traps
- Name the scenario before quoting carry: realized-forwards (forwards slide down the curve, any bond earns the short rate) vs unchanged-curve give different roll numbers. Return = cash carry + carry-roll-down + rates + spread; sum to the gross return (Tuckman & Serrat, 2022, Ch.3). Example (7.625% of 11/15/22, 13 Nov 2020 - 14 May 2021): carry-roll-down -3.761 (-3.27%), rates +0.183, spread +0.098, cash carry +3.813, total +0.333 (0.29%), same source.
- Cushion = horizon (carry + roll) / |DV01| in bp (script `carry_cushion_bp`); compare with the stop distance and with daily vol x sqrt(days). Negative cushion = the trade bleeds while you wait; a trade needing "patience" must show non-negative cushion or a funded reason.
- Long convexity is long vol: "bonds or portfolios that are more convex tend to earn less over time"; instantaneous P&L charts overstate its value (Tuckman & Serrat, 2022, Ch.4). Long gamma/curve options lose theta unless realised exceeds implied; premium paid for "right conditionality" mostly reflects directionality already priced (Huggins & Schaller, 2024, Ch.19).
- Short CTD basis = short out-of-the-money delivery options: capped gain (BNoC), unlimited loss if the CTD changes; long basis = long vol and loses if yields barely move and the curve flattens (Burghardt et al., 2005; Conks, 2025). A negative CTD net basis is not free money when deliverable supply is short: price it as P(fail) x the BNoC gap (Burghardt et al., 2005).
- Crowded carry: a steepener with large positive carry is where the consensus is; the carry is what you are paid for being the marginal holder.

### 8. Model and hedge-ratio risk
- "The hedge is always as good as the calibration" (swapsball.net, Regression in finance: friend or foe?, Oct 2017). Hedge ratios from regression: report in-sample SE, coefficient CI, out-of-sample residual variance, and direct vs reverse regression; level regressions have autocorrelated errors and are not fair-value tools (Tuckman & Serrat, 2022, Ch.6; swapsball, 2017).
- DV01-neutral assumes beta = 1: the 10y OTR yield beta was 1.186 on 1/12/98 but ranged 2.88 (1991) to 0.46 (1993); betas "might actually work against you" (Burghardt et al., 2005). Hedge-ratio error test: re-run the scenario with the hedge leg's DV01 off by 30% (default); the residual is directional risk.
- PCA: factors uncorrelated over the full sample can correlate over sub-periods, making a PCA-neutral trade directional; scatter the trade vs PC1 over the recent window; success rate rose from ~82% to just over 90% after this check, with fewer trades (Huggins & Schaller, 2024, Ch.3). PC1 is not parallel; explanatory power of 3 PCs is >99% beyond 3y but 74.5% at 1y (Golub, BlackRock's Guide to Fixed-Income Risk Management, 2023; Tuckman & Serrat, 2022). Hedge all factors of lower order than the target factor (Huggins & Schaller, 2024). PCs are not tradable without every tenor in proportion and residuals can flip sign with the neglected PCs; keep a static benchmark-trade risk check alongside (Darbyshire, 2022).
- Aging: forward PVBP over the holding period, not today's; highly asymmetric fly weights are a disguised slope trade (Duering, 2021).
- Stale or asynchronous prices understate vol and correlation (Golub, 2023). Use consistent snaps.
- Ornstein-Uhlenbeck/z-score sizing overstates Sharpe at extreme entries when vol is constant; predictability is necessary, not sufficient, for alpha (Huggins & Schaller, 2024, Ch.2).
- Calendar spreads have nothing forcing convergence at expiry, unlike basis (Burghardt et al., 2005); Amaranth lost about $6bn on a natural-gas calendar spread (Chan, 2009).
- Swap-future BPV changes with the rate level while STIR-future BPV is fixed: rebalance (Aikin, 2012).

### 9. Event calendar
For every date inside the horizon, mark which leg it hits and the plausible one-day move versus the carry cushion: central-bank meetings (`cb_meetings`), data and chair/voting changes, auctions and buybacks, futures roll/expiry/delivery windows (early delivery within 3 business days of the first delivery date is rational when carry is negative; wildcard window runs to 8pm ET), quarter/year-end and tax-date funding, fixing and compounding dates, budget/election dates, debt-ceiling X-dates. Examples: if an October payroll print delivers the December cut, the January and March gaps inside the Dec/Apr SOFR gap richen 3-5bp each, taking Dec/Apr from -26 to about -32/-37 (JWS Macro, Autumn 2025); Treasury doubled buyback sizes on 19 Aug 2026 and yields fell within minutes then round-tripped by the next afternoon (Druckenmiller, WSJ, Aug 2026). If an event is binary and larger than the stop, the stop is not a risk control: size to the event.

### 10. Correlation with the existing book
- Aggregate the new trade with `positions` and run the same scenarios on the combined book; report marginal change in worst-scenario loss, not stand-alone loss. Diversification shrinks in crises; size for independent bets, not number of trades (Narang, Inside the Black Box, 2024).
- Look for hidden common factors: same regime exposure (desk trades share the same macro assumption), same crowded bucket, same funding provider, same balance-sheet constraint (swap spreads, basis and repo trades all load on dealer balance sheet). Judge the signal by residual Sharpe after neutralising known factors (Tulchinsky et al., 2015). P&L from one group only is a warning sign.
- Duplicate-trade rule (default): if the marginal increase in the book's worst-scenario loss is >= 75% of the trade's stand-alone loss in that scenario, treat the idea as an add to an existing view, not a new one.
- Link: [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md).

### 11. Numbers to recompute independently
Recompute these from raw inputs using a different path than the screen (different code path or data snap); flag any
difference above the tolerance (default) and resolve before the verdict.
| Number | Recompute from | Tolerance (default) |
|---|---|---|
| Leg DV01s and fly/hedge weights | curve at the trade snap; DV01 per leg, sign | 2% |
| Entry level and z-score | same window, same snap, same instruments; confirm window end excludes look-ahead | 0.2 sd / 0.2bp |
| Carry and roll over the horizon | named scenario; repo for the specific issue | 10% or 0.1bp |
| Basis: net basis, implied repo, CF-weighted hedge | `fut_basket`; identity IRR = CTD term repo - (BNoC / dirty price) x 360/n_days | 1bp repo |
| Target/stop in ccy | bp x DV01 per bp of the spread | exact |
| Break-even hit rate | R/(R + G), compare with your probability | exact |
| Cushion, days to exit, haircut cash call | scripts below | exact |
| Conventions: day count, sign, benchmark roll, settlement | `fi-g10-market-conventions` | exact |
Treat a trade where an "erroneous position" (data, software, operational) is suspected as an immediate exit, not a review (Chan, 2009).

### 12. Evidence quality (backtest and signal gating)
- Trial count: after ~7 configurations a researcher expects at least one 2-year backtest with Sharpe > 1 when true Sharpe is 0; ~20 loops of backtest at the 5% level "to discover a (false) investment strategy" (Tulchinsky et al., 2015; Lopez de Prado, AFML, 2018). Demand the number of trials. Deflated Sharpe threshold SR* = sqrt(V) x ((1 - g) Z^-1(1 - 1/N) + g Z^-1(1 - 1/(N e))), g = 0.5772; reject unless DSR = PSR[SR*] > 0.95, i.e. the observed Sharpe (same annualisation as V) must clear SR* with margin (script `deflated_sr_threshold` returns SR*; e.g. trial-Sharpe variance 0.25: N = 7 gives SR* 0.69, N = 20 gives 0.95, N = 100 gives 1.27).
- Robustness: result survives a one-day entry delay (a result that improves with delay means the signal is early), neighbouring parameters (no lonely peak), another sub-period and each sector separately (Narang, 2024; Tulchinsky et al., 2015). No re-fitting after seeing OOS. True OOS is live forward tracking; "backtest the recent N years and call older years OOS" and "split instruments into IS/OOS" are both invalid (Tulchinsky et al., 2015).
- Parameters: at most ~5, about 252 points per free parameter, OOS at least a third the length of the training set (Chan, 2009).
- Hit-rate hurdles: break-even p = R/(R + G), e.g. R = 2, G = 1.5 gives 57%. Binomial strategy Sharpe = (2p - 1)/(2 sqrt(p(1 - p))) x sqrt(n); p = 0.55 needs 396 bets/yr for Sharpe 2, weekly bets need p = 0.6336; asymmetric payout (n = 260, loss 1%, gain 0.5%): p = 0.70 gives 1.17, p = 2/3 gives 0 (Lopez de Prado, 2018, Ch.15). Strategy Sharpe below 1 is not suitable stand-alone (Chan, 2009).
- Tables over prose: check the numbers in a research note against its own tables (Tulchinsky et al., 2015, Ch.6).

### 13. Scenario P&L, size to the scenario
Build scenarios as per-leg yield/spread shocks in bp and run `scripts/pretrade_checks.py scenario`. Default set:
(a) parallel +/-25bp (beta check; a fly or DV01-neutral spread should be ~0); (b) 2s10s +/-15bp as a pivot around the belly (wings -/+7.5bp); (c) belly
+/-10bp; (d) **regime gap**: the spread moves 2x the stop distance against you in one step (stops do not fill at
the stop); (e) **hedge failure**: hedge leg DV01 off by 30%, then parallel +/-25bp; (f) **liquidity/financing**:
(d) plus exit at 3x bid-offer, haircut x3 and repo +50bp on the short leg; (g) **event**: the largest scheduled
event's plausible surprise on each affected leg; (h) **book**: shock (d) applied to the combined book.
Rule (default): (d) is 2x the stop loss by construction for a linear trade, so the stop alone is never the control: size so
that the (d)/(f) loss is <= the per-trade risk budget, and flag (f) well above (d) as a financing/exit-cost problem (see [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md)).

### 14. Counterparty, fill and process checks
- Fill as information: "Conditional on my order being filled, what do I think the expected value is? Would I still be happy?" An easy fill on a package that is hard to value, or the other side being an EV-motivated peer rather than a price-insensitive holder, should prompt re-underwriting; the RV application is the reviewer's inference (Jane Street, Probability & Markets primer). The largest z-scores tend to arrive late in a trend or at a dislocation (adverse selection): cap or winsorise the signal (Narang, 2024).
- Disposition/endowment checks on open trades: "If you did not own it today, would you buy it?"; have someone uninvolved review the thesis; quantify the cost of the bias (a rolling 6-month gain-vs-loss realisation ratio; one FX case was 2x as likely to take a gain as cut a loss, cost peaked at 2.5%) (Golub, 2023; Chan, 2009). Do not double down after a break: in a simulated kappa 0.5 -> 0 break, doubling down led to ruin, while a stop-managed strategy ended above the unrestricted one (Brenndoerfer, 2025).
- Evaluate decisions by expected value and process, not one outcome; variance dominates small samples (swapsball.net, Poker series, Jul 2018; Clarke, The Grinder's Manual, 2016).
- Keep asking "what has changed within the last five minutes?"; when questioning stops, conviction becomes dogma (Aikin, 2012). Pick ONE invalidation condition in plain words (Global Macro Method, Feb 2026).

### 15. Pre-committed kill criteria
Fixed before entry, written into the ticket, each with metric, threshold, check frequency and action. Types, in priority order:
1. **Thesis kill**: the data series from lens 0 shows the mechanism is not working (e.g. "belly stops leading after the next major data", "futures OI keeps rising while cash cheapens"). Exit or halve.
2. **Financing/margin kill**: haircut/margin increase > X% of capital, repo-minus-benchmark above the tolerance, a counterparty changing terms. Exit before forced.
3. **Liquidity kill**: exit cost estimate > 50% of remaining target (default), or days-to-exit > limit.
4. **Price stop**: where the thesis is falsified, not where it hurts. Statistical RV book defaults: position stop at |z| 3.5-4 (entry |z| >= 2, exit 0 to +/-0.5), portfolio drawdown stop 10-15%, leverage 2-3x (Brenndoerfer, 2025). Reconcile with the opposing view that a reversal model "will never recommend a stop loss" and that stops suit momentum, not reversion (Chan, 2009): use a z-stop only to cap regime-break loss, name the regime assumption, and test it on a simulated break. For constraint/basis/event trades use hard stops (a squeezed basis short has no theoretical maximum loss; Burghardt et al., 2005).
5. **Time stop**: default 2-3 half-lives or the horizon, whichever is shorter (alpha decay: use in-sample drawdown size/duration as the benchmark; drawdown larger than normal, falling Sharpe, behaviour "outside the historical box" -> cut if exit cost is acceptable; Tulchinsky et al., 2015).
6. **Event kill**: flatten or hedge before a binary event larger than the stop.
7. **Book kill**: combined worst-scenario or drawdown limit breached.
8. **Data/ops kill**: erroneous position or benchmark switch -> exit immediately.
Plan the exit before the trade: set the anticipated maximum loss; if the realised loss exceeds it and the exit is cheap, cut (Tulchinsky et al., 2015, Ch.3). Ask at entry "what could happen that would convince me I don't understand the relevant market forces?" and exit if it does (Tuckman & Serrat, 2022).

### Verdict rubric
Score each lens GREEN / AMBER / RED with one line of evidence. Defaults:
- **NO-GO**: RED on mechanism (0), financing survival (6), exit/liquidity (5), or recompute failure (11), or the regime-gap loss exceeds the risk budget at the proposed size.
- **HOLD (need data)**: a lens could not be run, or a recompute is unresolved.
- **GO-SMALLER**: no RED; >= 3 AMBER, or crowded in the trade's direction, or half-life > 1/3 horizon. State size as a fraction of the proposed size (default 50%) and what moves it back.
- **GO**: no RED, <= 2 AMBER, kill criteria written, cushion non-negative or funded.

## Worked example
**A. Illustrative (numbers invented to show the mechanics).** Idea: receive 5y, pay 2y and 10y 50/50 (2s5s10s = +4bp, z = +2.3), DV01 +10,000 / -5,000 / -5,000 ccy per bp, i.e. 5,000 ccy per bp of fly. Target 0bp (+20,000), stop 8bp (-20,000), 3-month horizon, carry+roll +2,500.
- Break-even hit rate R/(R+G) = 4/(4+4) = 50%; with p = 0.60 and 12 independent bets a year the binomial Sharpe is 0.71 (`hurdles --risk 4 --gain 4 --p 0.6 --n 12`), below the Sharpe-1 stand-alone bar (Chan, 2009). Under a driftless spread a symmetric stop and target hit 50/50, so all the edge is reversion; the review must evidence it (lenses 3, 12).
- Cushion = 2,500/5,000 = 0.5 fly-bp: carry covers 12.5% of the 4bp stop distance. With daily fly vol 0.8bp, 3-month sd is ~6.3bp, larger than the stop: the stop is inside the noise.
- Scenario run (`scenario`): parallel +25 gives 0 (fly-neutral, good); regime gap (2y +3, 5y +8, 10y +5 = fly +8bp, 2x the stop distance) gives -40,000 = 2x the stop loss, so size must be set on -40,000, not on the -20,000 the stop implies.
- Alternative explanation: if the equilibrium fly moved (faster recovery), an observed +4bp is mostly new fair value (Lehman, Oct 2003, above: 4bp observed vs 4.8bp new model fly is ~1bp rich, not 4bp). Verdict for this ticket: GO-SMALLER (regime, evidence and stop-inside-noise AMBER, no RED) at 50% size, with a thesis kill "belly stops leading after the next data release" and a 6-week time stop.

**B. Basis financing case (Tuckman & Serrat, Fixed Income Securities, 2022, Ch.11).** Long $1bn of the June 2020 10y note-futures CTD basis, opened 6 Mar 2020 at net basis -8.33 ticks; hedge = 10,000 x 0.8006/(1 + 1.10% x 116/360) = 7,978 contracts; target about (8/32)% x $1bn = $2.5mm. On 9 Mar net basis went to -18.48: daily P&L -$3,172,148, margin per contract 1,275 -> 1,375 (call -$797,772), cumulative cash out -$14.1mm. By 12 Mar net basis was -0.47 and cumulative P&L +$2,455,330. The thesis was right and the trade converged, yet ~$4mm of cash was needed in one day against a $2.5mm target, enough to trip a loss limit and force a sale before convergence. At 20:1 leverage the same trade type earns about 6.5% annualised in calm markets (a 10 Feb 2020 entry at -4.0 ticks: $1.25mm on $50mm of capital over 141 days). Review verdict logic: financing lens AMBER/RED unless cash for a 3x-normal margin call and a 50bp repo spike is held in advance.

More cases (1986 squeeze, MF Global margin table, 2000 repo special, Dec 2001 CTD stress, April 2025 swap-spread move): [references/cases.md](references/cases.md).

## Signals & interpretation
- RED means "do not trade as proposed", not "wrong". Each RED must name the change that would clear it (data, size, structure, hedge).
- Agreement of several independent lenses on the same hidden factor (e.g. crowding + balance sheet + regime) is stronger than any one alone: escalate one level.
- Never let a good story offset a failed recompute or a missing falsifier.
- Disagree-and-commit: record the dissent and the kill criteria in the trade note; the reviewer does not veto, but the verdict and unresolved items go in the write-up.

## Pitfalls
- Turning the review into generic risk boilerplate: every risk must carry a number (bp, ccy, probability class) and a trigger.
- Treating stop loss as the risk: gaps, event and financing losses exceed it. Size to scenario loss.
- Checking only the stand-alone trade, not the book.
- Re-running the same code path as the screen and calling it an independent recompute.
- Reading one crowding gauge as truth (futures shorts are not a one-for-one cash match by tenor: the front-end match is poor, >5y matches; CFTC OCE 2024-007).
- Using a regime story post hoc to excuse a loss; the kill criteria were fixed before entry.
- Over-correction: the aim is calibrated doubt ("don't overcorrect"; Jane Street primer); restraint is part of the edge (Global Macro Method, Feb 2026).
- Sample-size blindness on event studies; US-only seasonal/COT statistics do not transfer to other G10 curves without a local test (BofA, 2025).

## Output
Return one report (markdown), then hand off:
1. **Verdict**: GO / GO-SMALLER (size) / HOLD (data needed) / NO-GO, one-sentence reason, confidence (L/M/H).
2. **Thesis as stated**: mechanism, falsifier, horizon, consensus position.
3. **Lens scorecard**: table lens | GREEN/AMBER/RED | key evidence with number | what would change the score.
4. **Top risks (max 5, ranked)**: scenario | shock (bp per leg) | P&L (ccy) | % of risk budget | probability class | mitigant, from the scenario run; include the combined-book effect.
5. **Alternative explanations**: table explanation | explained bp | residual opportunity bp.
6. **Recompute table**: number | claimed | recomputed | pass/fail.
7. **Kill criteria**: id | type | metric | threshold | frequency | action.
8. **Conditions** to proceed or restore size, and open items.
Hand-offs: kill criteria and thesis falsifier to [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md); risks and scenario table to the "risks" section of [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts
- [`scripts/pretrade_checks.py`](scripts/pretrade_checks.py): `scenario` (first-order P&L per scenario from positions and per-leg shocks CSV/Parquet; columns `instrument_id, dv01_ccy` (latest `date` only if present) and `scenario, instrument_id, shock_bp`), `hurdles` (break-even hit rate, binomial Sharpe), plus library functions `required_hit_rate`, `deflated_sr_threshold`, `carry_cushion_bp`, `days_to_exit`, `haircut_cash_call`. `python scripts/pretrade_checks.py --help`. `--selftest` checks known answers (fly-neutral parallel shock, p = 0.55/n = 396 Sharpe 2, weekly bets p = 0.6336, asymmetric payoff 1.173, SR* at N = 100).

## Related skills
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): consumes the risks, scenarios and kill criteria
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md): runs the kill criteria live; re-underwriting
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): the screen that feeds this review
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): ranking score; this skill challenges the top of the list
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): deflated Sharpe, purging, trial counting in depth
- [quant-regime-detection](../quant-regime-detection/SKILL.md), [quant-cointegration](../quant-cointegration/SKILL.md), [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): break tests and half-life
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md), [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): hedge-ratio and factor-model risk
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md), [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): carry cushion, DV01 and scenario risk
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md), [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): financing, haircut and balance-sheet constraints
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md), [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): basis option-value checks
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): crowding gauges
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md), [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): event and regime scenarios
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md), [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): exit-cost modelling, legging and package execution
- [curve-butterflies](../curve-butterflies/SKILL.md), [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md), [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): fly residual and weight risk, swap-spread sign and balance-sheet checks, z-score look-ahead
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md), [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): dealer positioning gauges, convention and day-count checks
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md), [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): book-level scenarios and sizing
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md), [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): input validity and tables
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): two-leg curve trades.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-grid RV, kinks and aged forwards.
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): P&L attribution and performance metrics.
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): geopolitical channels and fade/follow rules.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro-factor regression fair values.
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): swaption and cap/floor vol RV.
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): skew, smile and tail hedges.
- [port-portfolio-construction](../port-portfolio-construction/SKILL.md): combining trades into a book.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): the implied policy path.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): reserves and balance-sheet plumbing.
- [xccy-basis](../xccy-basis/SKILL.md): cross-currency basis.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CCP basis between clearing houses.
- [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md): sovereign CDS and CDS-bond basis.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension, insurer and ALM duration demand.
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): MBS convexity hedging flows.
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): fiscal supply and term premium.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): auction, issuance and cash-flow events.
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): fitted-curve residuals and bond switches.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CSA discounting and xVA wedges.
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): breakevens, linkers and inflation swaps.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): cross-market and EGB spreads.
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): bond-futures calendar roll.
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): invoice spreads and futures asset swaps.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR strip calendars, flies and packs.

## References
- Tuckman, B. & Serrat, A. - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): carry/roll decomposition, MF Global haircut case, March 2020 basis trade, flash events, SCP crowding case
- Lehman Brothers (Tuckman) - Macro-Awareness in Relative Value Trading (LMR Quarterly 2003-Q3, Oct 2003): regime-shift taxonomy, fly example, macro-aware checklist
- J.P. Morgan (Younger, Salem, St John) - Special delivery: how delivery options distort rich/cheap metrics for US Treasury futures (4 Dec 2019): option-adjusted basis and implied repo, wildcard, delivery timing
- J.P. Morgan - Why we should all care about Treasury futures basis (12 Mar 2020) and When market risk meets operational risk (10 Mar 2020): basis size, unwind arithmetic, liquidity metrics, de-risking signals
- CFTC Office of the Chief Economist (Mixon & Orlov) - Observations on the Treasury Cash-Futures Basis Trade (Staff Paper 2024-007, 23 Sep 2024): sizing, futures-to-cash scaling, maturity mismatch
- CFTC Market Risk Advisory Committee, Market Structure Subcommittee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): financing, margin, delivery risk, stress-test recommendations
- Treasury Borrowing Advisory Committee - Discussion of Treasury Futures Positions Across Different Investor Types (30 Jan 2024): asset-manager demand, crowding monitor, leverage
- Bank for International Settlements - Quarterly Review, Goodbye Libor, hello basis traders (Ehlers & Todorov; Box B Sushko & Todorov, Dec 2025): residual-method swap-trade sizing
- BofA Global Research - Systematic Flows Monitor: More CTA models = better impact estimates (2 Jun 2025): stop-out count as crowding gauge
- BofA Global Research - US Rates Watch: Fed's SLR proposal: underwhelming (25 Jun 2025): which regulatory constraint binds
- BofA Global Research - Technicals Explained: In 2025, get to know technical strategy (14 Jan 2025): COT +/-2 sd rule, small-sample warnings
- Burghardt, Belton, Lane & Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): short-option framing of basis, squeeze and special-repo cases, hedge-ratio pitfalls
- Huggins, D. & Schaller, C. - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): PCA correlation check, constraint-driven mispricing, honest-RV conclusion
- Lopez de Prado, M. - Advances in Financial Machine Learning (Wiley, 2018): deflated Sharpe, strategy-risk binomial model, backtest sins
- Duering, A. - Fixed Income Trading and Risk Management (Wiley, 2021): trade ingredients, hedge calibration, benchmark switches
- Chan, E. P. - Quantitative Trading (Wiley, 2009): stop-loss by signal type, capacity and crowding, psychology checklist, parameter-count rules
- Brenndoerfer, M. - Mean Reversion and Statistical Arbitrage (online handbook, 27 Dec 2025): stop/drawdown defaults, regime-break simulation, rolling cointegration
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): trial-count arithmetic, invalid OOS designs, crowding and alpha life-cycle
- Narang, R. - Inside the Black Box (3rd ed., Wiley, 2024): delay-sensitivity red flag, model and regime risks
- Golub, B. (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): PCA limits, stale-price vol, disposition-bias cost
- Palomar, D. - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): cointegration persistence
- swapsball.net - Regression in finance: friend or foe? (27 Oct 2017) and Poker: GTO balancing / bright and dark sides (Jul 2018): hedge-calibration pitfalls, process vs result
- JWS Macro (Substack) - #8 Playing Devil's Advocate (23 Aug 2026); #3 Iran & Front End Rates (8 Mar 2026); USD & Global Rates Thoughts #2 Autumn 2025 (13 Nov 2025); Central Casting #6.1 (21 Jun 2026): steelman audit, degrossing, neutral-phase trap, chair credibility
- Conks (Plumbing Notes) - The Basis Trade Scare (17 Nov 2025) and Money Market Update (17 Apr 2025): repo tolerance, long-basis vol exposure, April 2025 swap-spread positioning
- Clarus Financial Technology - Swapalypse Now (Barnes, 14 Apr 2025): swap-spread volume and trade counts in the April 2025 move
- Goldman Sachs - Global Rates Trader: Reaching Limits (2 Oct 2026): catalyst checklist for a risky EGB spread
- Citi Research - Global Macro Trade Ideas Radar (13 Aug 2026): inclusion standard, closed trades and stops as worked outcomes
- Druckenmiller, S. - Let the Bond Market Speak (Wall Street Journal, 24 Aug 2026): buyback as price management, plumbing vs price-level intervention
- Aikin, S. - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): legging and liquidity rules, trader discipline
- Willer, D. & Saunders, A. - Trading Global Macro Markets (Wiley Finance, 2026): regime failure of macro timing rules, small samples
- Jane Street - Probability & Markets (introductory primer): adverse selection, fill-as-information, overconfidence
- Papic, M. - Geopolitical Alpha: An Investment Framework for Predicting the Future (Wiley, 2021): diagnosticity, binding constraints, consensus check
- Darbyshire, J. - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): limits of PCA for risk management
- Nomura - Derivative Focus (Cross-Asset), Erratum: Conditional Euribor bull flatteners (Firoozye & Zhang, 19 Jun 2014): crowded-steepener screen, positive-carry flattener
- Global Macro Method (Substack) - STIR (Rates) Application Process, Lite (25 Feb 2026): single invalidation condition, restraint
