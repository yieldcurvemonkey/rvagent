---
name: vol-skew-and-tail-hedging
description: 'Measure, value and trade the swaption / bond-futures-option smile in normal (bp) vol - payer vs receiver skew, risk reversals (RR), smile curvature, costless-ladder breakeven width, empirical-SABR "realized skew" fair value, skew as a positioning signal - and build tail hedges or skew-selling structures (payer/receiver 1x2, ladders, spreads, collars, calendars, skew-isolating RR+straddle+swap package, long-dated OTM payers with positive roll, SPX-contingent hybrids, CTD-switch convexity). Use when asked "is payer skew rich or cheap", "swaption smile / wings", "RR", "risk reversal", "skew z-score", "sell skew", "1x2 / 1x1.5 payer spread", "ladder", "costless", "tail hedge", "protect against a rates selloff", "hedge 6% rates", "bull-flattener / deflation hedge", "OTM payer / receiver", "Board vs swaption skew", "put/call skew on bond futures options", "zero-strike receiver", "upper-left / bottom-right vol". Curve-shaped conditional steepeners and flatteners: curve-conditional-trades.'
---

# Vol skew and tail hedging

Skew is the price of the tails: how much more (or less) an out-of-the-money (OTM) payer or receiver costs, in vol, than
the at-the-money-forward (ATMF) option of the same expiry and tail. This skill (1) puts skew on a comparable, tradable
scale, (2) decides whether it is rich or cheap versus what rates actually do, (3) explains who is pushing it (flows,
positioning, convexity hedgers) and (4) turns the view into a structure whose payoff, cost and Greeks are explicit.
Skew is "direction and speed": you can be right that rates rise and still lose by selling skew that was priced for a
faster move, or by buying a tail that costs more than the carry it protects.

## When to use
- "Payer skew looks rich in 3m10y / 5y30y: monetise it?" - rich/cheap screen, then a ratio or ladder structure.
- "Cheap tail protection against a selloff / bull-flattening / deflation / negative rates / fiscal scare."
- A skew number moved and you need to know if it is positioning, a flow (MBS, CMS caps, insurers, structured notes) or fundamentals.
- Futures-option (Board) smile versus swaption smile; CTD switch as embedded OTM payer convexity.
- Not for ATM vol level or term structure alone ([vol-rates-options-rv](../vol-rates-options-rv/SKILL.md)), delta-hedged gamma/vega P&L ([vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md)) or full RND extraction ([stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Swaption (and cap/floor) normal vols on expiry x tail x strike-offset | `vol_surface` | daily, same snap, >= 1y (3y+ for z-scores and regressions) | strikes as offset from ATMF; need +/-25, 50, 100 and ideally +/-200/300bp for tail work |
| Listed option quotes, strikes, deltas (bond-futures and STIR options) | `opt_quotes`, `opt_static` | daily settle | nvol_bp of the underlying rate; STIR nvol(bp) = futures-price nvol (points) x 100 |
| ATMF forwards, carry/roll of the underlying | `curve_par` (forward starts), `curve_zero` | daily | forward = drift-free breakeven, not a forecast |
| Futures, deliverable basket, conversion factors (CTD scenarios) | `fut_quotes`, `fut_basket`, `fut_static` | daily | for Board-vs-swaption and CTD-switch convexity |
| Positioning (core shorts/longs) and public swaption prints | `positioning`, `flows_trades` | weekly / daily | flows need package and compression filters |
| Event calendar | `cb_meetings` | forward looking | pin risk and event vol around meetings |

Check first: one snap per series, nvol in bp (see [schemas](../data-contract-and-adapters/references/schemas.md)), OTM strikes
exist out to the distance you need. The ladder metric below needs strikes out to ~2x the costless gap past ATMF; if the
grid ends earlier the solver returns NaN rather than extrapolating - ask for wider strikes. Never invent vols.
See [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Conventions (state them in every output)
- Vol is **normal (Bachelier) bp/yr**. Daily bp vol = annual / sqrt(252) (about /16). 1-sd terminal range = vol x sqrt(T). Normal vol = yield vol x yield (22% at 5% = 110bp), so it moves when forwards move; "be bilingual" and check lognormal / shifted-lognormal near zero (BofA, US Vol Primer, Mar 2024; Credit Suisse, Wall Street Babylon, Nov 2011).
- **Payer = call on the rate = short-duration / pay fixed; receiver = long duration.** Strikes are offsets K - F (bp). Payer-receiver parity: payer - receiver = F - K at the same strike and expiry, so parity says nothing about skew at equal distance.
- **Skew(d) = vol(ATMF + d) - vol(ATMF)** at the same expiry/tail. Payer skew uses +d, receiver skew uses -d. **RR(d) = vol(+d) - vol(-d)**; positive = payers over receivers. **Smile = (vol(+d)+vol(-d))/2 - ATM** (curvature).
- **OTM distance d scales with expiry** so strikes are comparably OTM: 25bp for 3m, 50bp for 6m-2y, 100bp for 3y+ (Citi skew monitor, conventions used across Citi Rates Vol Lab 2017-2023; later USD tables use 25bp throughout and a 100bp-out chart at 5y expiry - confirm before comparing issues). Fixed-bp strikes are not comparable across tenors; use delta (25-delta receiver, and the OTM payer that BofA labels "75-delta" in receiver-delta terms, i.e. payer delta 25%; a payer of delta 0.75 sits on the same strike as the 25-delta receiver and by parity has the same vol, so it adds no skew information) or the breakeven-width metric.
- Surface vocabulary: upper-left = short expiry/short tail, upper-right = short expiry/long tail, bottom-left = long expiry/short tail, bottom-right = long expiry/long tail (Darbyshire, Pricing and Trading IR Derivatives, 2022).
- Listed-option language (bond futures, STIR futures) is in price, rates language is in yield: **put on a futures price = payer (call on the rate); call on the price = receiver.** "Board put skew above call skew" = payer-like wing richer than receiver-like wing; Bassman's "put-minus-call" RR is payer minus receiver, the same sign as RR above.
- Option P&L units: annualised bp of vol (abp) for vol trades; bp of yield for curve/spread trades; DV01 in currency per bp, positive = long duration (receiver-like).

### Normal-model formulas (all in `scripts/skew_tools.py`)
```
s = sigma_N*sqrt(T);  d = w*(F-K)/s                    w = +1 payer, -1 receiver
price (per unit annuity) = w*(F-K)*Phi(d) + s*phi(d)    ATM = sigma_N*sqrt(T/(2*pi))
vega = sqrt(T)*phi((K-F)/s)  (same for payer/receiver);  delta_payer = Phi((F-K)/s), delta_receiver = -Phi(-(F-K)/s)
(delta = d value / d rate, payer positive. The duration-convention DV01 of a position is the opposite sign: DV01 = -delta x annuity PV01, so a long payer has negative DV01.)
vomma ~ vega * x^2 / sigma_N,  x = (F-K)/s   -> OTM wings carry more vomma
sigma_N ~ F*sigma_LN*(1 - sigma_LN^2*T/24)  (ATM; exact via equating ATM prices; short-expiry sigma_N ~ F*sigma_LN)
```
Check: 5Y30Y payer, mid 1.325%, K 1.5%, vol 52bp = 38.16bp, upfront 38.16bp x $230,500 PV01 = $8.80mm (Darbyshire, 2022); the script reproduces it.

## Method

### 1. Build the skew grid
For every expiry x tail: ATM, payer skew, receiver skew, RR, smile at the convention distance; each with a **1y z-score** (rolling 252d, no look-ahead; use robust median/MAD if the series has jumps). Run `python scripts/skew_tools.py grid --vol-surface <file>`.
Report the grid as in the Citi/BofA monitors: payer skew, receiver skew, RR, each scored. Flag |z| >= 2 (rich/cheap); 1.5 is "watch".

### 2. Costless-ladder breakeven (BE) width - preferred tradable skew metric
Ladder = buy 1 payer at ATMF (or OTM), sell 1 at +D, sell 1 at +2D, i.e. (1,-1,-1). Downside is unlimited, so a gap D always exists that makes it costless. Payoff = 0 below the long strike, rises to D at K+D, flat to K+2D, falls to 0 at **K+3D**, losses beyond. **BE width = 3D.** Richer wings -> more credit -> D must widen (BE width up); cheaper wings -> tighter (BofA, US Vol Primer, Mar 2024). For a 1x2 (1,-2): zero at K+2D; generally for (1,-r) the far breakeven is K + r*D/(r-1) (r=1.5 gives 3D).
1. Solve D per grid point with `costless_gap` (Brent root on the interpolated smile; strikes = ATMF, +D, +2D).
2. **Dimensionless form:** z_BE = BE width / (sigma_ATM*sqrt(T)). Probability beyond the far breakeven = 1 - Phi(z_BE). Reading: 1y10y BE 127bp vs 110bp vol = z 1.155 = 12.4% (BofA, Mar 2024).
3. **Flat-smile baseline (derived with the bundled solver, normal model):** costless ladder D = 0.341 sigma sqrt(T) (BE width 1.02 sigma sqrt(T), 15.3% beyond BE); costless 1x2 D = 0.495 sigma sqrt(T) (far BE 0.99 sigma sqrt(T)). z_BE above ~1.02 means wings richer than a flat smile (BofA's 1y10y: 1.155; 1x2 gap ~60bp vs the flat 54bp; ladder gap ~42bp vs flat 37.5bp at 110bp vol).
4. **De-directionalise:** BE width in bp co-moves with ATM vol and the forward. Regress per grid point over a 63-day window, BE = a + b*ATM + c*forward, and use the **3m z-score of the residual** as the skew RV signal (`ladder_residual_z`, no look-ahead). Do the same on receiver ladders (strikes downward, `w=-1`); payer/receiver BE-width ratio, and its z, gauges payer vs receiver skew RV.
5. Same logic for any unlimited-downside structure. For capped-downside structures (spreads, flies) define the cost relative to ATM (e.g. strike gap that recovers 70% of ATM premium).
Benefit: the metric is a position you can trade, so rich/cheap is unambiguous.

### 3. Fair value of skew: "realized skew" by empirical SABR
SABR (normal-ish form): dF = F^beta * sigma dW1, d sigma = nu * sigma dW2, corr = rho. beta = backbone (how ATM bp vol moves with the forward), rho = vol/rate co-movement (the tilt, drives RR), nu = vol-of-vol (the curvature) (BofA, 2024; Tuckman & Serrat, 2022).
1. Calibrate to **realized dynamics**: backbone beta on a **2y rolling window** (stable), rho and nu on a **3m window** (current co-movement). Match ATM exactly so the model differs from market only in skew.
2. "Realized skew" = model value of OTM payers, receivers and RR. Report **RR market - model (vol pts)** and **OTM payer/receiver market/model price ratios**, each with a 1y z (Citi Rates Vol Lab, Mar 2020; Feb 2023; Sep 2026).
3. Read: RR > +2 sigma rich to realized = payers too dear / receivers too cheap versus how vol actually co-moves with rates. Screen only; Citi flags that screen "best picks" are backward-looking and not necessarily trades.
4. Cross-check model-light with a scatter: realized vol-rate beta (beta of the weekly change in ATMF normal vol in bp/day on the weekly change in the forward yield in percentage points, so units are bp/day of vol per 1% of yield; 6M window in the monitor, 1M windows in the short-window version; 6/25-9/25 1M betas 6Mx2Y 2.13, 6Mx10Y 2.23, 6Mx30Y 2.44, 2Yx10Y 1.30) vs the vol implied by the smile at those rate levels (JPM, US IRD, 2 Oct 2026). Receiver skew implying more vol in a rally than recent realized directionality = room to cheapen (Citi, Sep 2026).
5. Shifted-lognormal / shifted SABR (shift h > 0) when rates can be near or below zero (EUR, CHF, JPY legacy); always state the shift. Near the zero bound much of normal-vol skew is flat in yield-vol terms and receiver skew softens as lognormality kicks in (Credit Suisse, Nov 2011; JPM, Feb 2020).
6. BSM deltas hold vol fixed and miss the vol move implied by skew; mark aged swaptions off the skew; no BSM-style model fits the entire cube, so fit per expiry/tail (Tuckman & Serrat, 2022).

### 4. Attribute the move: who is pushing skew
Classify before trading; structural flow persists, positioning flips. Checklist (reasoned, not exhaustive):
- **Mortgage / MSR hedgers:** skew compresses or inverts when rates cross the convexity point (payer demand for extension flips to receiver demand for contraction) (Credit Suisse, Skewered by Skew, Apr 2013; Citi Rates Vol Lab, Dec 2016).
- **CMS-cap and single-look cap dealers:** selling a cap struck at K means buying a strip of OTM payers; payout per bp is concave in rate because DV01 falls as rates rise, so dealers mark deep payers up (BAS/ML, No Bad Bonds, Oct 2009).
- **Insurers / fiscal-tail hedgers / non-rates investors:** buy high-strike, long-tail payers; keeps bottom-right payer skew bid within a range (MS, 6% Rates, Jul 2026; Citi, Sep 2026). Read swaption prints by expiry: long expiries (10y10y, 20y10y) = vega buyers/sellers; intermediate (2y10y, 3y10y) = macro delta; 5y20y = insurer expression. In 2024-26 USD, strikes >= 6% (typically > 200bp above forwards) have few natural end users. Exclude packages and compressions; motivation is ultimately unknowable from repository data.
- **Core shorts hedged with low strikes** make short-dated skew inverted (receivers rich) - positioning, not fundamentals; cross-check CFTC-style data.
- **Dealer gamma:** high-strike payer demand steepens skew and lifts vol-of-vol, worsening dealers' dV/dr and amplifying vol into selloffs, so tail payers get dearer when needed (Goldman Sachs, US Rates, 2 Oct 2026).
- **Regime:** 1990s higher rates were "bad" (payers rich); 2007 and QE lower rates meant crisis (receivers dear); 2013 a 3%+ 10y implied more uncertainty and payer-receiver skew was near its steepest ever. Skew usually compresses as vol rises; skew steepening with ATM is an anomaly worth a flow search.
- **Long-end steepeners embed short payer skew:** bear-flattening is much stronger than steepening in gradual rises, so carry-harvesting steepeners are short vol/short skew (Citi, European Rates Weekly, Sep 2026).

### 5. Is deep OTM skew sane? (fair-vol test)
Ask what ATM vol the strike implies if it is reached and compare with history. Example (2009): 5y10y ATM 122nv; +300bp payer 159nv implies a big ATM rise if rates reach 6.75% (near 1990s 10y swap average 6.95%), against a 1990s MOVE average of 101 and 1980s 3m T-note vol rarely > 180nv; deep payer skew was too rich (BAS/ML, Oct 2009). Also test **skew at fixed forward**: same 5y10y forward (4.88% -> 4.87%), ATM vols ~11% higher but +300bp vols ~33% higher is anomalous.
No-arbitrage bound: a more-OTM option may not cost more than a less-OTM one; check monotonicity and convexity of price in strike before trusting a deep wing quote (Darbyshire, 2022).

### 6. Skew as a signal
- **3m change in the 3m10y 25bp-out RR -> next-month 10y change** (USD, monthly Jan 2006 - Nov 2016; Citi, Flatter skew is a warning signal, Jan 2017): <25th pct: avg -11.5bp, median -5.0, 36% rises; 25-50: -2.1/-1.1/48%; 50-75: +0.2/-4.2/45%; >75th: +8.8/+11.1/69%. Steepening (payers richening) -> higher rates; flattening = core duration shorts built (hedged with low strikes) that may capitulate. Edge is in the tails, middle buckets non-monotonic. About 130 monthly observations, ~33 per bucket (the 3m-change signal overlaps month to month so bucket membership is autocorrelated; the next-month outcomes do not overlap): a 69% hit-rate has a binomial standard error of ~8 points, about 2.2 se from 50% (my arithmetic), and 2006-16 is a secular yield decline (the unconditional frequency of rises is not reported, so compare buckets with it, not with 50%) - a tactical warning, not a standalone rule; combine with positioning. Retest on current data via [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md) before use.
- Front vs back skew divergence flagged crowded flatteners (Jan 2018); short-dated RR cheapening weakens the bearish duration signal; payer skew falling while rates rise = market wants OTM calls (bull-flattener protection) (Citi Vol Lab, Apr 2018; BofA/ML, Look Right, Feb 2010).
- "Skew rotates in advance of a large move" (Credit Suisse, Apr 2013) - a heuristic. Equity skew-return evidence (Tulchinsky et al., Finding Alphas, 2015, ch.20) is an analogue only; do not transfer its thresholds.
- Skew-vs-level scatter: SABR rho of 3m10y and 3y10y vs the 10y level; a point above the level-implied relation = persistent high-strike demand (MS, Jul 2026).

### 7. Choose the structure
| Goal | Structure | Inception exposure | Wins | Loses |
|---|---|---|---|---|
| Pure tail protection | OTM payer (or receiver); long-dated OTM payer | long vega, short duration, long gamma | gap move, vol up | theta; premium vs the carry protected |
| Same, cheaper | payer spread (1,-1): max payoff D; fly (1,-2,1): net short vega | defined risk | move to sold strike | move beyond sold strike |
| Sell rich payer skew, defined view | **1x2** (1,-2), **ladder** (1,-1,-1), **1x1.5**, costless | net **long delta, short vega** - opposite of an outright payer | gradual underperformance vs forwards, range-bound | sharp early move in the favoured direction (MTM), then unlimited loss beyond far BE |
| Isolate skew, no gamma | long payer / short receiver (equal OTM distance) + small ATM straddle + swap | long (payer vol - receiver vol) only | skew mean-reversion | broad vol richening if vomma-neutral, curvature seesaw |
| Capped-view, collar | buy OTM receiver, sell further OTM payer, zero cost (deflation hedge); or sell payer ladder (inflation view) | | | tail beyond sold strike |
| Harvest short-dated skew, keep far tail | **payer calendar**: short near-expiry OTM payer, long longer-expiry payer spread | small vega | skew roll-down | near-term selloff |
| Cheap contingent hedge | **hybrid**: OTM long-tail payer pays only if SPX below trigger at expiry (correlation sale) | | stress with stocks down, yields up | growth scare with lower rates |
| Conditional curve/term-premium | receiver fly, e.g. sell 10y-tail 22-delta (20-delta in the printed trade table) vs buy 2y/30y tails at 55%/29% risk weights (JPM, Return of convexity hedging, Jan 2020) | short front-end duration in vol episodes | slowdown/vol episodes | |
Ratio structures have an **open tail**: size and set the sold strike where you are confident rates will not go; "the preference is to lose money later in a selloff rather than make money sooner" (BofA, Mar 2024). Do not run naked delta-hedged short deep-OTM payers; isolate skew with a ladder (flat delta/gamma, positive carry) instead (Credit Suisse, Apr 2013; BAS/ML, Oct 2009).

#### Skew-isolating package (RR + straddle + swap)
Long payer and short receiver at the same OTM distance (e.g. +/-50bp, 3m2y, equal notional); long a smaller ATM straddle for residual vega; a swap for delta (Rhodes, USD 3m2y Payer Skew Steepener, Oct 2025).
```
N_str = -N_rr*(vega_payer - vega_receiver)/vega_straddle        (vega-neutral)
N_swap = -(N_p*delta_p + N_r*delta_r + N_str*delta_ATM)/delta_swap   (delta-neutral; signed notionals, short receiver = negative; rate-deltas, payer +; N_swap > 0 = pay fixed)
dP ~ Delta dS + 1/2 Gamma dS^2 + Vega ds + 1/2 Vomma ds^2 + Vanna dS ds + ...
```
Caveat from the algebra: in a Bachelier model with strikes exactly symmetric about ATMF, payer and receiver vega (and vomma) are equal, so the RR is already vega-neutral and N_str ~ 0; the straddle ($9.71mm per $100mm in the source) only offsets the vega/vomma asymmetry from strikes not centred on ATMF after the forward moves and from different payer and receiver vols. Compute Greeks at actual vols and strikes; do not assume net vomma > 0 without checking.
Rebalance: resize when |net vega| drifts > 5 abpvs or net rate move > 5bp; re-strike wings if either drifts > 5bp from target; after a +/-5bp rate shift re-centre wings and refresh the straddle, else vanna accumulates vega. Net vomma > 0 (OTM wings have more vomma): broad vol richening pays even when vega-neutral (hypothetical: vega 0, vomma 0.9, vols +5 abpvs = +11.25 second-order, new vega ~ +4.5 -> trim). Risks: curvature (ATM vs wings), correlation, slight negative theta, gap/liquidity at the front end, hedge slippage; monitor wing bid/ask.

#### Positive-carry long-dated OTM payer
Static roll: price the fixed-strike payer at each expiry on **today's** surface; if the shorter-expiry price exceeds today's longer-expiry price, it rolls up (positive theta on a static surface). Arises only when the forward curve is flat/inverted at the long end and the vol surface is inverted (short expiries rich from mortgage demand, long expiries poor), and the +300bp OTM skew is roughly constant while ATM falls with expiry so relative skew rises with expiry. Long vega, short duration, long convexity; wide bid/offer; static roll is a starting point, not a forecast (Merrill Lynch, Positive Carry Hedge, Oct 2008; BofA/ML, Reprise, Dec 2010; numbers in [worked examples](references/worked-examples.md)).

#### Futures options and CTD switch
Map a bond-futures option to a swaption: swaption strike = Board strike yield + invoice spread, CTD-matched; compare Board vol with the CTD-matched swaption vol ratio per strike (skew makes the ratio strike-dependent). DV01-neutral conditional spread (buy puts, sell payers) solve the costless swaption strike and report the bp pick-up; the source text and numbers use opposite signs, so state your own sign. A bond future's CTD switch makes a short future behave like a long payer: in a ~50bp selloff the Dec-26 20y futures CTD flips from a 5% 2045 to a 1.375% 2050 and duration rises ~47%; the embedded convexity priced ~12.4 ticks vs ~8.7 net basis (~30% cheap) when yields sit near the 6% notional coupon, coupon dispersion is wide and payer skew rich (MS, Buy Higher Rates Protection, Aug 2026). Hand the delivery mechanics to [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md) and basis-as-vol to [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md).

#### Left tail: zero-strike receivers
Delta of a zero-strike receiver ~ market-implied P(rate < 0); benchmark with P(rate < 0) from a normal with mean ATMF and sigma = ATMF normal vol x sqrt(T). In 2015-17 receivers priced far below normal-implied; Feb 2020 ~12% implied vs ~9% normal-implied for 2y swap < 0 within a year (JPM, Feb 2020). Valid only if the market has "zero qualms" about negative rates.

### 8. Decide: hedge, monetise or stand aside
1. **Name the tail and the regime shift** the book is exposed to, and buy protection at **book level** against the shared exposure; subtract its cost from expected gains of RV trades and size RV smaller where they lose in the likely shift (Lehman, Macro-Awareness in RV Trading, Oct 2003).
2. **Premium vs carry:** if hedge premium > the carry it protects, cheapen with spreads/contingencies (hybrid cost fell 78% to 8c: Convexity Maven, Propeller Heads Only, Jun 2019).
3. **Spot vs forward vol:** to hedge a hawkish shock buy spot long-dated vol, not forward vol - a hawkish shock spikes short-dated vol and cheapens forward vol (taper tantrum 2013) (Citi Vol Lab, Jan 2017).
4. **Option value is tail value:** if the ultimate downside is known and the path continuous, urgency to own options falls.
5. Find the tail nobody is positioned for (often the bull-flattener), not the consensus one; do not be short long-dated OTM receivers with a tight stop on long curve trades (BofA/ML, Look Right, Feb 2010).
6. Entry gates for selling skew: skew z >= 2 on **both** BE-width residual and realized-skew gap; a flow story that is not structural; no event in the sold-strike window; costless or credit; target/stop set (examples use ~2:1, e.g. target $600k / stop -$300k).

## Worked examples
**A. BE-width read (BofA, US Vol Primer, 23 Feb 2024 levels).** 100m 1y10y ATM payer: 3.727% strike, NPV $3.432m, vol 110bp, DV01 -36,451, vega 31,203, gamma 230, theta -4,107/day; underlying PV01 ~$77.8k. Costless 1x2 gap ~60bp: net vega -23.4k, DV01 +8.1k, gamma -175, theta +3,869. Costless ladder gap 42bp: vega -22.3k, DV01 +7.5k, BE width 127bp = 3 x 42 -> z_BE 1.155 vs flat-smile 1.02 (wings rich), 12.4% beyond BE. Both costless structures are long delta / short vega at inception. Costless payer-ladder BE widths by expiry: 1m 27-35bp; 3m 49-60; 6m 77-87; 1y 114-133; 2y 161-203; 5y 245-326; 10y 327-427; 3m de-directionalised z mostly 0 to +1.6 (payer skew fair-to-rich) with 10y expiries at -0.5 to -1.4.

**B. Skew-selling ladder (Credit Suisse, Skewered by Skew, 17 Apr 2013).** Buy 100mm 5y5y payer K 3.65% (98nv), sell 100mm K 4.50% (106nv), sell 100mm K 5.50% (116nv): zero cost, flat delta and gamma, positive carry, max payoff 4.50-5.50%, far breakeven 6.35%; 5y5y 3.00%, par MBS ~2.50%. After +125bp the long strike is 60bp ITM (like a 60bp OTM receiver) so the 8nv skew to 4.50% should vanish; 18nv of skew across the ladder is the edge. Exit early on vega/skew compression. 2009 variant (BAS/ML): 5y10y ladder 6.25%/7.75%/9.50% at 138/157/181nv (25.0/25.5/26.4% yield vol), carry +$400k/yr, instant +200bp = -$500k, +200bp over a year = +$600k, loses only if rates rise > ~400bp in < 1y; "you will not top-tick".

**C. Costless 1x2 payer spread (Citi, US Rates Weekly, 21 Aug 2026).** Buy ATMF 3m30y payers, sell 2x at +17bp: profit if the 30y finishes 4.576%-4.916%, terminal loss only above 4.916% (34bp above the recent peak). Closed example: 3m2y, buy $150mm ATMF (3.94%), sell $300mm +27bp, closed +$430k at ATMF 4.094% before expiry. Ratio payer spreads lose when rates **and** vol rise together (Barclays 2y30y ratio spread stopped out, Oct 2026).

**D. Skew-isolating package P&L (Rhodes, 8 Oct 2025).** Long $100mm 3m2y +50bp payer, short $100mm -50bp receiver, long $9.71mm ATM straddle, swap. Skew at -23 abpvs was in the 10-20% decile (receivers rich); target 0. Scenarios: parallel vol +/-10 = +/-$3,240; payer +10 & receiver -10 = +$37,840; payer -10 & receiver +10 = -$31,360. Exits: skew makes new lows; deeper cuts priced in; liquidity deteriorates.

**E. Hybrid tail hedge (Citi, Rates Vol Lab, 14 Sep 2026).** 30mm 30y payer struck ATMF+40bp expiring Mar-27 contingent on SPX < 97%: 0.49% offer (3.1bp running), 64% below vanilla, implied correlation -5%. Cheap only if stress-scenario stock-bond correlation is far more negative than priced; such hedges cannot be backtested directly ("no historical comparable"). Risk: growth slowdown with lower rates.

More dated examples (positive-carry roll tables 2008/2010, CMS-cap ladder, EUR 3m1y balance-of-risk gauge, MS tail-strike flows, CTD replication, Board-vs-swaption rows): [references/worked-examples.md](references/worked-examples.md). Dated realized-skew readings and regime history: [references/skew-readings-history.md](references/skew-readings-history.md). Per-market notes: [references/market-notes.md](references/market-notes.md).

## Signals & interpretation
- Skew rich: BE-width residual 3m z >= +2 and RR - model >= +2 sigma (1y z) and no structural flow behind it -> sell via ladder/1x2 (credit), or buy the opposite wing.
- Skew cheap vs realized and a catalyst (event, supply, positioning squeeze): buy tail spreads; RR cheap + payer skew bid at long expiries = tail demand is structural, not an RV signal.
- BE-width z_BE far above 1.02 with the payer/receiver BE ratio also rising = payer wings richest; far below = payers cheap vs flat smile.
- Balance-of-risk gauge (Citi EUR, Aug 2026): costless 1x2 payer distance P minus receiver distance R at 3m1y; P-R > 0 = upside rate risk priced. 2026 path: ~16-17bp late March, ~2bp July, ~6-8bp after a vol spike.
- Confirm: ATM level and forward (so skew change is not just directionality), flows classified, positioning, event calendar, Board vs swaption ratio (CTD-matched). Skew normally compresses when vol rises; skew steepening with ATM vol is an anomaly, look for a flow (e.g. CMS caps).
- Flight-to-quality days flip vol-rate betas negative (yields down, implieds up): realized-skew models calibrated on the 3m window fail on those days.

## Pitfalls
- Comparing fixed-bp skew across tenors; ignoring that normal-vol skew is directional with forwards; mixing OTM conventions between publications.
- Calling a skew "fair" by one model only; near zero normal vs lognormal flips the answer. Use implied vs realized as the arbiter.
- Realized-skew screens and z-score "best picks" are backward-looking; RR cheap for months can stay cheap.
- Costless ratio structures are short vega and long delta: early mark-to-market against you, then unlimited tail. A stop is a stop: JPM exited a 200bp RR fade at -8.2abp although still seeing it mispriced; extending a stop needs a stated rationale.
- Persistent structural demand (insurers, fiscal hedgers) keeps payer skew elevated within a range; policy actions (buybacks) can suppress near-term long-end skew while long-dated skew stays bid.
- Selling a tail on a pure-jump model: a jump model can value an OTM policy-rate option at ~0; stress against diffusion first (Huggins & Schaller, SOFR Futures and Options, 2022).
- Too few strikes in a replication/strip overestimates value; piecewise-linear lies above a convex profile. Smile makes short gamma costlier than 1/2 G sigma^2 suggests (Darbyshire, 2022).
- Hybrids price today's correlation; value is the gap to stress correlation. ISDA/professional counterparties only.
- Skew arbitrage claims from equity (stickiness ratio ~2) do not carry over; rough-vol caveat: an empirical SSR below 2 need not be an arbitrage; a daily delta-hedged RR "skew arb" is eaten by costs (0.2 vol pt bid/offer per leg) and, if not rolled, becomes a leveraged directional bet short gamma into selloffs (Quantitative Finance Stack Exchange, "Bergomi: Skew arbitrage").
- Wide bid/offer in OTM wings and long-dated tails; price at executable levels, not mid.
- Mortgage-driven skew reverses when MBS cross the convexity point; do not extrapolate the pre-cross relationship.

## Output
A skew note with: (1) grid table per ccy: expiry, tail, ATM nvol, payer skew, receiver skew, RR, smile at stated OTM distance, BE width, z_BE, BE-residual 3m z, 1y z of each, RR market-model and ratio z; (2) driver attribution (flow / positioning / structural / fundamental) with evidence; (3) a recommended structure with strikes, notionals, cost (upfront or running bp), Greeks (DV01, vega, gamma, theta), both breakevens, profit zone and the open-tail strike, scenario P&L (gap move, gradual move, vol up/down, rates + vol together), target/stop, exit triggers, and the hedge-vs-carry comparison; (4) data gaps and assumptions (shifts, snaps, conventions). Hand off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and run [rv-devils-advocate](../rv-devils-advocate/SKILL.md) before sizing; sizing in [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).

## Scripts
- [`scripts/skew_tools.py`](scripts/skew_tools.py): normal pricing/Greeks, ATM log-to-normal conversion, costless 1x2/ladder gap solver and BE width (any smile), RR/skew/smile grid from a canonical `vol_surface` file, BE-residual rolling z, vega-neutral straddle and swap-hedge sizing. `python -I scripts/skew_tools.py --selftest` (known-answer checks: published 38.16bp price, parity, quadrature, finite-difference Greeks, 12.4% BE probability, ladder cost = 0); `python scripts/skew_tools.py grid --vol-surface <file>`.

## Related skills
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): ATM vol level/term RV, implied vs realized, vol grids
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): delta-hedged P&L attribution, gamma/theta for the structures here
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): curve caps, CMS spread options, hybrids, cross-asset vol RV
- [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md): futures basis/delivery option as embedded vol
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable/structured vega supply behind long-dated skew
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): long-end convexity and MBS hedging flows
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): mortgage convexity point and skew
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md), [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): positioning and swaption-print flow reads
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): RND, outcome probabilities, STIR option skew
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-based conditional steepeners/flatteners
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): carry steepeners as hidden short payer skew
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): STIR option skew, straddle breakevens vs policy outcomes
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md), [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): CTD convexity, Board-vs-swaption strike mapping
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market conventions behind strikes and vol quoting
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md), [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): z-scores and the BE-width regression
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): stress the open tail of ratio structures
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md), [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): pre-trade review and write-up
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): geopolitical channels and fade/follow rules.

## References
- BofA Global Research - US Rates Primer: US Vol Primer, A Guide for the Perplexed (B. Braizinha, 11 Mar 2024): normal/Black/SABR formulas, breakeven-width skew metric, 1x2/ladder Greeks, grid readings
- Credit Suisse (H. Bassman, Convexity Maven) - Skewered by Skew (17 Apr 2013): skew definition, four drivers, regime dependence, MBS skew ladder, vol-ratio trade
- BAS/ML (H. Bassman) - RateLab: No Bad Bonds, Just Bad Prices (27 Oct 2009): CMS-cap skew mechanics, fair-vol test, 5y10y payer ladder, positive-carry outcome (partial read)
- Merrill Lynch (H. Bassman) - RateLab: The "Positive Carry" Hedge (31 Oct 2008): static roll-up of long-dated OTM payers
- BofA Merrill Lynch (H. Bassman) - The Positive Carry Hedge, A Reprise (8 Dec 2010): second roll table, risks
- Citi Research - Rates Vol Lab: Liquidity, vega, and convexity (R. Bikbov, J. Williams, 30 Mar 2020): skew monitor conventions, empirical SABR, Board smile (partial)
- Citi Research - Rates Vol Lab: Short Blues convexity via futures/swaps (M. Chang et al., 21 Feb 2023): realized-skew method and readings
- Citi Research - Rates Vol Lab: Slow and steady wins the short gamma race (M. Chang et al., 14 Sep 2026): vol-rate directionality scatter, SPX-contingent 30y payer (partial)
- Citi Research - North America Rates Focus: Flatter skew is a warning signal for duration shorts (R. Bikbov, 12 Jan 2017): RR-change percentile signal table
- Citi Research - Rates Vol Lab series (Bikbov, Williams et al., 2016-2023: Dec 2016, Jan 2017, Mar 2018, Apr 2018, May 2019, Jan 2020, Jun 2023): skew readings, conditional flies, 1x2 receiver spread, Board vs swaption
- Citi Research - US Rates Weekly: Can Secretary Bessent and Chair Warsh save the curve? (J. Williams et al., 21 Aug 2026): 1x2 payer spreads, payer calendar, receiver ladder
- Citi Research - European Rates Strategy and Morning Call (Appeddu, Searle et al., 12 and 20 Aug 2026), European Rates Weekly (24 Sep and 1 Oct 2026): balance-of-risk gauge, EUR 1x2s, steepener-as-short-skew
- Ade Rhodes - Trade Idea: USD 3m2y Payer Skew Steepener (8 Oct 2025): skew-isolating package, vomma/vanna, rebalance rules
- Morgan Stanley - Investors Are Paying for Protection Against 6% Rates (S. Zhou et al., 2 Jul 2026): tail-strike flow classification, skew vs level
- Morgan Stanley - Buy Higher Rates Protection at a 30% Discount (S. Zhou et al., 27 Aug 2026): CTD-switch convexity replication
- J.P. Morgan - US Interest Rate Derivatives: Near, far, wherever yields are (I. Ozil et al., 2 Oct 2026): 200bp RR, vol-rate beta, ladders, RR stop-out
- J.P. Morgan - US Interest Rate Derivatives: Markets struggle to feed the convexity beast (J. Younger et al., 28 Feb 2020): zero-strike receiver NIRP probability
- J.P. Morgan - Is bank convexity hedging lying in wait? (J. Younger et al., 31 May 2019) and The return of convexity hedging (31 Jan 2020): futures-option vs receiver skew, conditional receiver fly
- Convexity Maven (H. Bassman) - For Propeller Heads Only (17 Jun 2019): hybrid contingent payer spread, premium-vs-carry rule
- Credit Suisse (H. Bassman) - How High is High? (17 Sep 2013), Wall Street Babylon (28 Nov 2011), The Convexity Vortex (6 Mar 2013); BofA Merrill Lynch (H. Bassman) - "Look Right..." (19 Feb 2010): zero-cost collars/ladders, normal vs lognormal, convexity concentration, OTM call tail hedge
- Goldman Sachs - US Rates: The Week That Was / The Week That Will Be (J. Coppola, V. Mistretta, 2 Oct 2026): payer skew and dealer gamma
- BNP Paribas - EUR curve convexity: Lessons from history (E. Oynoyan, M. Meijer, 25 May 2021): 30y receiver-skew hedge vs bull-flattening
- Lehman Brothers - Macro-Awareness in Relative Value Trading (B. Tuckman, Oct 2003): book-level option protection
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (2022): smile, no-arbitrage bound, value of gamma with smile, normal pricing example
- B. Tuckman, A. Serrat - Fixed Income Securities, 4th ed. (Wiley, 2022): shifted lognormal/SABR, backbone, delta caveat
- D. Huggins, C. Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): jump vs diffusion option values
- Barclays Research - Global Rates Weekly: The urgency question (A. Pradhan et al., 2 Oct 2026): ratio payer spread stop-out, payer spread/ladder trades
- Citi Research - Global Macro Trade Ideas Radar: Our Most Compelling Trade Ideas (L. Costa et al., 13 Aug 2026): 1x2 put/payer spreads, CMS cap ladder; Citi Markets - SOFR/CBOT Vol EOD (G. Compton, 14 and 21 Aug 2026): skew-nadir strikes, straddle breakevens vs policy outcomes
- JWS Macro - Global Rates Outlook #5 (10 May 2026): SONIA option skew; Citi Research - Japan Rates Weekly: 2% priced in as lack of demand continues (T. Fujiki, 14 Aug 2026): JPY risk-reversal idea
- Shafer, Vovk - Probability and Finance: It's Only a Game! (Wiley, 2001): option-implied VaR bound
- Tulchinsky et al. - Finding Alphas (Wiley, 2015), ch.20: equity skew signals (analogue only); Quantitative Finance Stack Exchange - "Bergomi: Skew arbitrage" (2020/2025): stickiness ratio, costs
- Hagan, Kumar, Lesniewski, Woodward - Managing Smile Risk (Wilmott, 2002) (external): SABR model
