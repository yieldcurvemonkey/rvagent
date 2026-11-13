---
name: vol-rates-options-rv
description: Relative value in rates options (swaptions, caps/floors, listed bond and STIR futures options) in normal bp vol. Covers Bachelier pricing and unit conversion, implied vs realised and straddle breakevens, macro-vol and surface-PCA rich/cheap, expiry x tail grid switches and vol flies, forward vol / FVA / calendars, vol carry, listed (Board) vs OTC vol, event vol, and zero-bound/regime rules. Use when asked if swaption vol, gamma or vega is rich or cheap, 1m10y, 3m10y, 1y10y, 10y10y, vol grid or surface z-score, implied/realized, straddle breakeven, forward vol, vol calendar, expiry or tail switch, vol fly, normal vs lognormal, MOVE, SOFR options, Treasury futures options vs swaptions, long/short gamma, upper-left or bottom-right vol, cap/floor or swaption straddle pricing, implied vol vs realized vol.
---

# Rates options RV: swaption and futures-option vol

Implied vol is the rent paid for realised vol plus a flow premium. Vol RV asks, for one cell of the grid (currency x expiry x
tail x listed/OTC), whether that rent is mispriced against five yardsticks: (1) realised, (2) the rate level and curve
(macro-vol), (3) neighbouring cells (surface PCA, switches, flies), (4) its own forward-consistency (forward vol), and (5)
carry/roll. The lenses disagree often; the skill is choosing the trade that is cheap on several AND whose payoff isolates it.
Deep material is in `references/`; this file is the decision path.

## When to use
- "Is 1y10y / 3m10y / 10y10y / 30y-tail vol rich or cheap?", "where is the cheapest gamma?", "vol surface z-scores", "sell
  gamma or vega here?".
- Choosing between expiry switches, tail switches, vol flies, calendars, forward-vol (FVA) and midcurve trades.
- Implied vs realised, ATMF straddle breakeven, normal vs lognormal, upper-left / upper-right / bottom-right vol.
- Treasury-futures options ("Board") vs CTD-matched swaptions; SOFR / Euribor option vol; event-day vol.
- Out of scope here (use the sibling): gamma/vega P&L accounting [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md); skew and
  tails [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md); correlation, midcurve and CMS curve options
  [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md); curve-as-gamma and long-end convexity
  [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md); callable/Formosa vega supply
  [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md); option-based conditional curve trades
  [curve-conditional-trades](../curve-conditional-trades/SKILL.md); futures delivery option as vol
  [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md).

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).
| Input | Table | Granularity / history | Notes |
|---|---|---|---|
| ATMF normal vols, expiry x tail grid | `vol_surface` (`product=swaption`, `strike_offset_bp=0`) | daily, one snap; >= 2y for PCA, >= 5y for z-scores and regime-matched macro-vol | `nvol_bp` bp/yr; skew rows only for wings |
| Listed option vols, premiums, strikes | `opt_quotes`, `opt_static` | daily settle; stale flag | units differ by root (bond futures: price vol; STIR: rate-normal) |
| Par swap/OIS rates incl. forward starts | `curve_par` | daily, same snap as vols, >= 5y | for rate PCs, forwards, roll-down, realised vol of the ATMF rate |
| Futures prices, CTD/invoice spreads | `fut_quotes`, `swap_spreads` | daily | CTD-matched swaption mapping |
| Meetings and event dates | `cb_meetings`, `events_probs` | forward calendar | event-day vol, gamma gating |
| Optional: breakeven curve | `infl_swaps` | daily | inflation-augmented macro-vol |
If an input is missing, ask the user or the data adapter; never invent vols. Hard checks before any signal: one snap per series;
`nvol_bp` within [0, 2000]; no constant-maturity listed series; realised and implied on the same underlying and day basis; vols
and rates observed at the same time of day.

## Conventions (state them in every output)
- **Vol** = normal (Bachelier) bp per year. Daily vol = annual / sqrt(252) (122nv = 7.7bp/day). Lognormal = normal / forward
  rate (22% at 5% = 110bp). Always say the day basis and any shift.
- **Naming**: "1y10y" = 1y expiry on a 10y swap; a bare vol is the ATMF straddle. "6m1y1y" = 6m expiry on a 1y swap starting 1y
  after expiry (midcurve); "1y5y5y" = forward swap. Corners of the grid: upper-left = short expiry/short tail, upper-right = short
  expiry/long tail, bottom-left = long expiry/short tail, bottom-right = long/long.
- **Sectors**: gamma sector = expiries <= 6m (to 1y), vega sector = >= 3y, 2y grey; the border tilts to longer expiry for short
  tails (JPY ~4y for 1y tails). Gamma sector: delta-hedge and compare with realised. Vega sector: statistical series, hedge vega.
- **Signs**: rich/cheap = actual − model (> 0 rich, in normal bp), reported with a z-score and the window. Ratios > 1 = rich.
  Receiver = long duration (long rates-down); payer = short duration. Listed: a PUT on a futures price = payer, a CALL = receiver.
  Straddle: long gamma, long vega, short theta. Curve and fly sign conventions as in the repo rules (2s10s = 10y − 2y).
- **Units of P&L**: premium and breakeven in bp of the forward rate; money = bp x PV01 per bp; trade P&L in annualised bp of vol
  ("abp") for vol trades, bp of yield for curve trades; always say which.
- Formulas, conversions, settlement, date conventions, surface marking: [pricing-and-units](references/pricing-and-units.md).

## Method

### 0. Classify the trade by what it is exposed to (Huggins & Schaller, Fixed Income RV Analysis, 2024)
| Type | Structure | You are long | Implied vol matters |
|---|---|---|---|
| 1 | Gamma-sector options NOT delta-hedged | terminal level of the underlying (breakeven analysis) | only at entry |
| 2 | Gamma-sector options delta-hedged to expiry | realised vol until expiry | only at entry |
| 3 | Vega-sector straddles unwound well before expiry | change in implied vol | at entry and exit |
Do not mix exposures: a type-2 trade is unaffected by the terminal level; a type-1 trade is unaffected by realised vol. With two
or more underlyings, type 2 trades the realised-vol curve vs the implied-vol curve; type 3 trades the implied-vol curve.
Switching category mid-life (stop hedging, or unwind early) is allowed, but re-state the exposure.

### 1. Normalise and mark (see [pricing-and-units](references/pricing-and-units.md))
- Price every position at its OWN expiry and moneyness; never difference constant-maturity vol series as P&L.
- Check richness in both bases ("be bilingual"): normal vol and lognormal vol; if they disagree (typical near zero or after a big
  rate move) let implied-vs-realised arbitrate. Split a normal-vol change into forward move and logVol change before calling a
  vol move "vol".
- Interpolate in total variance (sigma^2 x T); skew as a bp-offset spread to the node ATM.

### 2. Implied vs realised (the model-light arbiter)
- Realised = zero-mean close-to-close std of daily changes of the ATMF swap rate, annualised x sqrt(252), over 21d and 63d;
  ratio = implied(1m or 3m ATMF) / realised (`realized_vol_bp`). Rolling windows overlap, so ratio z-scores are autocorrelated
  (effective sample ~ n/window): treat 1.5 as a screen, not a t-test. Also compute intraday realised (30-minute sampling in the home
  session); intraday/close-to-close > 1 = intraday mean reversion (good for hedgers who rebalance), < 1 = trending.
- Fair ratio is ~1.0-1.10 in the gamma sector: 3m10y implied averages ~7% above 60-business-day realised and is usually within 10%
  of that spread (Bassman, Skewered by Skew, 17 Apr 2013); 3y10y implied / 6m realised averaged 107% ("risk-adjusted fair value");
  USD 1y10y 108 vs 6m realised 106, EUR 69 vs 70 over 15y. Use the instrument's OWN history: 1y z-score of the ratio.
- Defaults: rich if ratio >= 1.25 and z >= +1.5; cheap if ratio <= 0.9 and z <= −1.5 (author's thresholds; EUR 3Mx10Y rules used 125%
  and 66%). "Cheap" vs realised only helps if realised persists: low implied vs a realised spike needs a catalyst.
- For long expiries compare with WALK vol (`walk_vol`), not the plain delivered vol: 1y1y walk vol 132.3 vs 142.8 plain (BofA, US
  Vol Primer, 11 Mar 2024).
- Local identity (ATMF, small vol gap): expected hedged P&L ~ Vega x (realised − implied). A delta-hedged option breaks even per
  re-hedge interval when the RMS move = implied/sqrt(252) (6.93bp/day at 110nv; dS_BE = sqrt(2 theta dt/Gamma)); the same break-even
  as a MEAN ABSOLUTE daily move is 0.798x that (5.5bp; Darbyshire's "daily breakeven", normal moves). Do not mix the two.
  Unhedged ATMF straddle breakeven at expiry = 2 x sigma x sqrt(T/2pi) (110nv, 1y: 88bp). Check the delta-hedge band vs the
  breakeven: re-hedge every 20-25bp in long-dated trades (15-30bp sweet spot), tighter if bid/offer is ~0.3bp.
- Per-grid selection: pick the SELL leg where implied/realised is highest and the BUY leg where it is lowest at matched
  vega/gamma, then check jump risk: a rich left side (short tails) is not a sell if it is prone to jumps (J.P. Morgan GFIMW, 21-22
  Aug 2026: left 1.2-1.4 vs right 1.06-1.13; 30y tails ~1.5 on 2 Oct 2026).

### 3. Level view: macro-vol (rich/cheap to rates)
Regress each ATMF vol on the first 3 PCs of the swap curve (optionally + breakeven PCs); residual in normals with z
(`rate_pcs`, `grid_residuals(..., exog=...)`). Fit ONLY on the regime the market is in: exclude the zero-bound regime for USD
(1996-2008 + 2017-19 in the cited work, "broken with Fed funds <= 50bp"), use the negative-rate era for EUR; refit when rolling
betas flip sign. Simple alternative for short expiries: 3m10y vol on the 10y rate and 2s10s. Detail and published fits:
[surface-rv-models](references/surface-rv-models.md).

### 4. Relative view: surface PCA, switches, flies (relative only)
- `grid_residuals(vol_wide, n_pc=3)` on a 2y window; residual z per cell. By design it says nothing about the level; a cell
  rich on BOTH macro-vol and PCA is the stronger signal. De-directionalise first (vol ~ forward x logVol).
- Switch ratios (expiry: 1m/3m, 3m/6m, 6m/1y, 1y/3y, 3y/5y, 5y/10y; tail: 1y/2y ... 10y/30y) with 3m z; tenor flies 2x belly −
  wings, vega-weighted. Regress slope on level (e.g. 3y10y − 1y10y vs 1y10y: slope = −0.29 x vol + 25.7, R^2 0.89) and trade the
  residual. Vega weights from vol-vs-vol betas (2y30y = 0.78 x 2y10y + 13.3 -> regressing y on x gives neutral vega weights V_x = beta x V_y: buy 1 vega 2y30y vs sell 0.8 vega 2y10y).
- A cheap cell must also have bearable carry (step 6) and a reason for the dislocation (supply, ELB, YCC, event).

### 5. Forward vol, calendars, midcurves
- Same-rate forward vol: sigma_fwd^2 = (T2 s2^2 − T1 s1^2)/(T2 − T1) (`forward_vol`). Forward swap vol from same-expiry par vols with
  annuity ratio L and correlation rho (`fwd_swap_vol`). Midcurve = DV01-weighted spread option (`midcurve_vol`). Rich midcurve =
  cheap implied correlation.
- Calendars: a notional-neutral calendar is long forward vol but also carries gamma/theta; vega-weight it, and gamma-weight when
  isolating forward vol. A vanilla calendar is not an FVA. A short FVA in a gap is short an ATM option as vol explodes.
- Screen all executable forward-vol trades (gamma-neutral calendars + triangles): value = 1y z; ex-ante Sharpe = vol-adjusted 3m roll.
  Forward vol often already contains the mean reversion; do not pay twice. Details: [forward-vol-and-calendars](references/forward-vol-and-calendars.md).

### 6. Carry and roll
- Vol carry = price change over 3m/6m with the surface unchanged; check each leg ("cheapest on a model is not automatically the
  best long"). Long vol is generally negative carry; positive carry means you are selling something.
- Carry-to-premium (Three-to-One, personal rule, not backtested): ratio = 1y roll-down(bp) x DV01 / receiver premium; buy when it
  approaches 3 (2.75-2.85 acceptable); normally < 2. Premium > carry wanted -> use spreads/contingencies.
- Short-gamma filters that beat the naive rule (EUR 3Mx10Y, IR 1.9-2.5 vs 1.0 always-short): vol-return momentum, carry,
  macro-shock (PMI), liquidity; fading implied extremes alone had IR −0.3.

### 7. Listed vs OTC
Compare Board vol (converted to normal yield vol) with the CTD-matched swaption (strike = Board strike yield + invoice spread), and the
implied ratio with the futures/swap realised ratio. Observed ratios 0.86-1.24 (mostly 0.97-1.11); flag outside 0.90-1.10 (author's thresholds) and only if the realised ratio
does not explain it. Parity checks and stale-premium flags for listed data. No mean-level RV exists inside a listed contract (parity
pins it). Detail: [listed-vs-otc](references/listed-vs-otc.md).

### 8. Events and regimes
Event-day vol from one-day breakevens or from variance additivity; gamma gating around FOMC/ECB/BoE, payrolls, CPI. Do not
sell delta-hedged gamma at ZLB entry (sell vega instead); do not sell vol straight after a spike (house gate: implied up >= 8 normals in 10
trading days against a short-vol idea); vol-rate beta flips on flight-to-quality days. Detail:
[market-notes-and-cases](references/market-notes-and-cases.md).

### 9. Combine, then structure
1. Score each candidate cell: macro-vol z, PCA z, implied/realised z, forward-vol z, carry/roll per leg, flow/supply tag. Candidate
   when |z| >= 1.5 on at least two independent lenses (sources report signals at 1.5-5 sd; treat > 3 sd with suspicion, usually a
   regime break) and the lenses are not just re-statements of one factor (ratio z-scores across tails share a common level factor).
2. Hand a ranked list to [rv-composite-scoring](../rv-composite-scoring/SKILL.md); persistence and decay to
   [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md).
3. Choose the structure: outright straddle (type 2), calendar/expiry switch, tail switch, vol fly, forward vol/FVA, ratio/ladder
   (costless but short vol and long delta at inception: they lose when rates and vol rise together), conditional curve via options.
   Size by vega (vol-vs-vol beta) for vega-sector legs and by gamma for gamma-sector legs; notional-neutral is wrong for different
   tails/expiries. State residual delta, vega, gamma, theta, and what the trade loses in a gap.
4. Holding period: vol spreads mean-revert fast (EUR-GBP 5y5y half-life 15 days), so set the target/stop from a first-passage
   estimate and recycle capital; hedge at peak liquidity (time-of-day matters for realised).
5. Kill criteria in writing before entry: stop in abp, regime-shift trigger, event gating, supply/flow already-priced test.

## Worked examples
All numbers are from the cited sources; they illustrate scale, they are not live levels.
1. **Units.** A 2.0% 1y10y ATM straddle priced 25bp -> normal vol 25/(2 x 0.3989) = 31.33bp, lognormal 15.68%; 15.68% x 2.0% =
   31.36 (Darbyshire, Pricing and Trading Interest Rate Derivatives 3rd ed., 2022). A 110nv 1y10y ATM payer: premium 43.9bp
   (breakeven 44.1bp), daily vol 6.93bp, unhedged straddle breakeven ~88bp, hedged RMS daily breakeven = daily vol 6.93bp (5.5bp as mean absolute move) (BofA, US
   Vol Primer, 11 Mar 2024; breakeven convention: Darbyshire, 2022). `python scripts/bachelier.py price --F 0 --K 0 --vol 110 --T 1 --side straddle` gives 87.77.
2. **Choosing the sell leg from implied/realised.** Grid (implied / 1m realised), 20 Aug 2026, tails 1y/2y/5y/10y/30y: 1M
   1.38/1.39/1.22/1.11/1.06; 1Y 1.26/1.27/1.20/1.21/1.19. Left side rich but jump-prone -> do not short it; right side is where to
   own gamma (J.P. Morgan GFIMW, 21-22 Aug 2026). By 2 Oct 2026 the 30y tail was ~1.5 at every expiry vs 1.03-1.33 for short tails
   and the desk sold 6Mx30Y vs vega-neutral long 1Yx30Y delta-hedged (−1abp) (J.P. Morgan IRD, Near, far, wherever yields are,
   2 Oct 2026).
3. **Two lenses.** Jun 2023 USD: macro-vol 1m30y −41.3 (−1.7 sd), 3m30y −32.0 (−1.6 sd) cheap, while 1y10y/1y30y +1.5 sd and
   1y5y/1y30y +1.3 sd (10y tails rich to 30y); spot 1y2y 143.0, 1y5y 121.8, 1y10y 103.8, 1y30y 83.2 (Citi Research, Rates Vol Lab:
   Forward steepener and vol divergence, 12 Jun 2023). A point rich on macro-vol and PCA (6m10y +0.4 and +1.1 sd) is a stronger
   signal than either alone (Citi, In search of cheap vol, 17 Jan 2020).
4. **Forward vol.** 2Y7Y = 50bp, 1Y1Y7Y = 44bp -> year-two vol sqrt(2 x 50^2 − 44^2) = 55.35 (`forward_vol(50,2,44,1)`). 1y5y 39, 1y10y
   59, L = 2.10, rho = 0.95 -> 1y5y5y = 84bp, not the naive 79 (Darbyshire, 2022). FVA replication of 6m-forward 1y10y: buy 160k/nv
   18m10y, sell 60k/nv 6m1y10y midcurve; bought at 95nv vs 100nv spot (Credit Suisse, The FVA: Forward Volatility Agreement, 27 Aug 2013).
5. **Vol fly.** 3y 2y/10y/30y vols 80.4/70.1/63.3: fly = 2 x 70.1 − 80.4 − 63.3 = −3.5 (table −4.0, z −1.9 since 1999, model FV +5): sell $230mn
   3y2y, buy $100mn 3y10y, sell $21mn 3y30y, vega-neutral, take-in $240k, carry ~+0.75 normals/yr (Citi Rates Vol Lab: Gamma and Vega
   RV, 14 Jan 2019).
6. **Slope-on-level.** 3y10y − 1y10y = −0.2929 x (1y10y) + 25.726, R^2 0.885: at 1y10y = 100nv the fitted slope is −3.6 (arithmetic
   illustration); the observed slope was 5.5 normals steeper and 3y10y ~14 normals "too high" vs the rate curve -> short 3y10y vs a
   10y10y/15y15y flattener (Citi, Fading vega dislocations, 5 Oct 2026).
7. **Board vs swaption.** Jun 2023: ratios 1.01/0.98/1.03 (5y/10y/long-bond), Board/1m realised 1.16-1.22, Board/3m 0.77-0.93: fair.
   Mar 2020: 0.86/1.02/0.89, a week earlier 1.22-1.24 for 10y/long-bond (Citi, 12 Jun 2023; Liquidity, vega, and convexity, 30 Mar 2020).
8. **Three-to-One.** 1y-into-2y receiver 56bp, K 1.45%, roll-down 82bp, DV01 1.97 -> 82 x 1.97/56 = 2.88 (Bassman, Your Ace in the
   Hole, 16 Jul 2014).
9. **Mean-reverting vol spread.** EUR minus GBP 5y5y: k = 16.5/yr, half-life 15.4d; P(hit target in 10d) 45%, expected-change Sharpe
   1.78 over 1m (Huggins & Schaller, 2024). More cases, incl. losers: [market-notes-and-cases](references/market-notes-and-cases.md).

## Signals & interpretation
| Lens | Rich (sell / avoid long) | Cheap (buy / avoid short) | Confirm / veto |
|---|---|---|---|
| Implied / 1m, 3m realised | >= 1.25 and z >= +1.5 | <= 0.9 and z <= −1.5 | realised regime persists? jump risk on the cheap side? event inside window? |
| Macro-vol residual | z >= +1.5 (regime-matched fit) | z <= −1.5 | rates must be outside the zero-bound regime; rolling beta not flipped |
| Surface-PCA residual | z >= +1.5 (relative) | z <= −1.5 | needs macro-vol or realised agreement for a level call |
| Switch / fly ratio z (3m) | z >= +2 | z <= −2 | vega-weight; leg carry; supply story priced? |
| Forward vol vs spot | fwd/spot >> 1 or z >= +2 | z <= −2 AND positive 3m roll | "cheap for a reason": ELB, callables |
| Vol slope vs level regression | residual > 0 | residual < 0 | regime breaks make a second regression line |
| Board / swaption | > ~1.10 and above realised ratio | < ~0.90 | typically short-lived; CTD-matched, converted units |
| Carry/premium (receivers) | | >= 2.75 | personal rule, diversify |
Rate-vol directionality: if the vol-rate beta is more negative than fair, vol should underperform in a rally; flight-to-quality days
flip it. High excess kurtosis in 1m daily changes (significance -log10 p > 1.3): selling 3Mx10Y delta-hedged and held 1m (vega-monetising)
beat selling 1Mx10Y delta-hedged to expiry (gamma short), as implied falls faster than realised when fat tails recede; after low
kurtosis in rising vol implied outpaces realised, long vega gains and hedged gamma loses (J.P. Morgan, 9 Mar 2018; 2013-18 sample).

## Pitfalls
- Normal vs lognormal can flip the conclusion (Nov 2011: blended 1m normal vol cheap, lognormal +2 sd rich). Normal vol can
  "move" only because forwards moved.
- Macro-vol is regime-dependent; PCA residuals are relative only; both depend on the window. Backward-looking screens are not
  recommendations; do not initiate in illiquid sectors on a screen alone.
- Vol-vs-vol and vol-vs-rate regressions break at regime changes (two regression lines): an apparent 4 sd residual is usually a
  break. Honest RV work often concludes "no trade".
- Constant-maturity series, rolled listed series and mixed vol units (price vs normal) manufacture RV. Stale listed settles and
  parity violations are flags. Cash vs physical settlement and 1y1y date ambiguity shift PV.
- Forward vols from the triangle use realised correlation as a proxy for implied; midcurve vs vanilla replication ignores
  correlation exposure; FVA cannot be replicated by fixed strikes.
- Short gamma into ZLB onset, into a vol spike, around scheduled events, or when hedging bid/offer is wide pays "pennies in front of a
  steamroller". Fading implied extremes alone has negative information ratio.
- Ratio structures (1x2, ladders) are costless but long delta and short vol at inception and lose on sharp early moves; ratio
  payer spreads lose when rates and vol rise together.
- Cheap-to-history is not a timing signal ("markets do not go from cheap to fair"); a 3:1 carry rule and published fits are
  personal/in-sample.
- Supply/flow stories can persist (callables, MBS, systematic selling); check whether the obvious leg is priced and trade the
  second-order leg.
- Ratio z-scores across tails share a common level factor and are useless for selecting between tails when vol moves; comparing
  curve carry with straddle PREMIUM instead of straddle decay overstates breakeven vol by sqrt(2).
- `grid_residuals` fits and z-scores on a window that includes the latest row: fine for a today screen; for a historical signal or
  backtest refit point-in-time (expanding or rolling, shifted one day) or the z-scores look ahead.
- Source typos exist (sign of the spread-vol formula, 100x vega/theta in a textbook example, a denominator in the normal-to-lognormal
  conversion): re-derive before reuse; the script's selftest checks the corrected forms.

## Output
Return, per candidate:
1. Table: cell(s), currency, instrument (swaption/futures option), implied nv, realised 1m/3m, ratio and z, macro-vol resid and z,
   PCA resid and z, switch/fly z, forward-vol z, 3m roll and Sharpe, Board/swaption ratio if listed, window and snap, data flags.
2. The view in one line (e.g. "long 1m10y gamma vs 1m5y/1m30y, vega-weighted"), type 1/2/3, structure with notionals by vega/gamma,
   premium, residual greeks, breakeven(s), hedge frequency, target/stop in abp, catalyst and kill criteria, what loses in a gap.
3. Lens agreement matrix and the "why is it cheap" explanation.
4. Hand-off: [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md); screening roll-up [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md).

## Scripts
- [`scripts/bachelier.py`](scripts/bachelier.py): Bachelier price/greeks/implied-vol, daily and straddle breakevens, normal<->lognormal,
  realised vol, forward/midcurve/forward-swap vol, walk vol, swap-curve PCs and macro-vol/surface-PCA residual z-scores. CLI:
  `price`, `iv`, `ratio` (rates CSV + implied -> ratio), `grid` (vol_surface CSV, optional curve_par CSV). `python -I scripts/bachelier.py --selftest`
  checks put-call parity, vol round trip, closed-form ATM price, textbook examples (forward vol 55.35 and 84.2, walk vol 132.3),
  finite-difference greeks and a planted rich cell.

## Related skills
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): P&L attribution, hedging, theta and gamma maintenance
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): skew, risk reversals, wings
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): midcurves, CMS spread options, implied correlation
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): curve vs options as gamma source, breakeven-to-realised
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable and structured vega supply
- [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md): futures delivery option vs option vol
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): premium-neutral conditional curve structures
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-space RV that vol forwards should be consistent with
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA machinery for rates and vol surfaces
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): regression fair values and regime-matched estimation
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): option-implied densities and policy odds
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures convexity and its vol dependence
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): MBS flows that move vega and gamma
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): OU fits, half-lives and entry/exit thresholds
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score windows and robust screening
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market swap, settlement and futures conventions
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): combining lenses into a ranking score
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): CTD switch and delivery option behind Board vs swaption gaps
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): policy-path pricing that event vol and STIR option vol must be consistent with
- [quant-regime-detection](../quant-regime-detection/SKILL.md): regime breaks that invalidate macro-vol and vol-vs-vol fits
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): stale quotes, roll seams and constant-maturity artefacts in vol history
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): challenge a vol idea before it is written up
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): hand-off and screening roll-up

## References
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): gamma/vega sectors, three trade types, breakevens, realised-vol curve trades, vega-sector PCA, OU mean reversion of vol spreads.
- Huggins & Schaller - SOFR Futures and Options (Wiley, 2022): listed SOFR option structure, realised-vol curves, level/slope trades, secured vs unsecured vol.
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022): swaption pricing, parity, vol measures, shifts, forward and forward-forward vol, event vol, worked examples 20.1-20.9.
- Tuckman & Serrat - Fixed Income Securities (4th ed., Wiley, 2022): normal/lognormal formulas, numeraires, USD vol matrix, vol cube, caps and bond-option vol.
- BofA Global Research - US Vol Primer: A Guide for the Perplexed (B. Braizinha, 11 Mar 2024): formulas, hierarchical PCA, walk vol, structures, FVA replication.
- BofA Global Research - US Rates Viewpoint: Understanding Principal Components (B. Braizinha, 21 Aug 2020): grid PCA and HPCA.
- Citi Research - Rates Vol Lab: In search of cheap vol (Bikbov, Williams, 17 Jan 2020): complete vol-RV dashboard template, regime-matched macro-vol, forward-vol frontier.
- Citi Research - Rates Vol Lab: Forward steepener and vol divergence (Chang, Williams, Appeddu, 12 Jun 2023): inflation-augmented macro-vol, Board vs swaption, 2023 readings.
- Citi Research - Rates Vol Lab: Gamma and Vega RV (Bikbov, Williams, 14 Jan 2019): vol fly, surface PCA, midcurve/CMS RV, scaling.
- Citi Research - Rates Vol Lab: Liquidity, vega, and convexity (Bikbov, Williams, 30 Mar 2020): ZLB gamma rule, Board vs swaption in stress.
- Citi Research - Rates Vol Lab: Left-side vols' outperformance (Chang, Williams, Appeddu, 22 Jun 2021): tail ratio vs curve beta, rate/vol regression, vol carry.
- Citi Research - Rates Vol Lab: Fading vega dislocations (Chang, Williams, Appeddu et al., 5 Oct 2026): vol slope vs level, 2026 frontier and Board ratios.
- Citi Research - US Rates Vol Lab: The art of gamma hedging (Bikbov, Williams, 12 Mar 2018) and Trading long-dated convexity (9 May 2019): hedge timing and bands, Board strike mapping.
- J.P. Morgan - US Interest Rate Derivatives: Near, far, wherever yields are (Ozil et al., 2 Oct 2026); Global Fixed Income Markets Weekly (21-22 Aug 2026): implied/realised grids, vol-rate beta, GBP-EUR vol spread.
- J.P. Morgan - Zen and the art of gamma maintenance (Younger, Salem, Zhao, 9 Mar 2018): expiry-ratio regression, kurtosis regime signal.
- J.P. Morgan IRD - Markets struggle to feed the convexity beast (Younger, Salem, St John, 28 Feb 2020): vol-rate directionality model, NIRP odds.
- J.P. Morgan European Rates Strategy - Rules based strategies for trading duration and Euro area rates volatility (Gupta, Inkinen, Vijay, 2017-2018): systematic 3Mx10Y short-gamma rules.
- J.P. Morgan - When the going gets tough, the tough get going (Salem, Younger, St John, 5 Nov 2019): one-day event breakevens and event liquidity.
- Credit Suisse - The Convexity Maven: The FVA: Forward Volatility Agreement (Mohney, Bassman, 27 Aug 2013): forward/midcurve vol formulas and replication.
- Bassman (Convexity Maven) - Wall Street Babylon (28 Nov 2011); Building a Better Volatility Mousetrap (6 Sep 2012); Forwards are NOT a Prediction (12 Aug 2013); Skewered by Skew (17 Apr 2013): normal vs lognormal, FVAs, implied/realised rules.
- Bassman (Convexity Maven) - Your Ace in the Hole (16 Jul 2014) and Paying Nickels for Dimes (21 Jan 2010): Three-to-One rule, slope vs vol.
- Merrill Lynch RateLab - Professional Javelin Catching (16 Feb 2007) and Implied Volatility: A Measurement of Fear (7 Oct 2008): multi-factor vol fair value, 107% ratio, MOVE, listed vol pitfalls.
- Salomon Brothers (Ilmanen) - Convexity Bias and the Yield Curve (Sep 1995): bp vol vs yield level, vol dependence.
- Goldman Sachs - Global Rates Trader: Reaching Limits (2 Oct 2026): vol retracement after sell-offs, closed vol trade outcomes.
- Henrard - Interest Rate Futures and their Options: Some Pricing Approaches (OpenGamma, 23 Feb 2012): margined vs premium options, SABR on futures, convexity for mid-curves.
- Hull - Options, Futures, and Other Derivatives, Ch. 31, Interest Rate Derivatives: Models of the Short Rate (9th ed., Pearson): zero-bond options, vol structures, calibration to caps/swaptions.
- Also cited inline in references/: Willer & Saunders - Trading Global Macro Markets (Wiley, 2026); Darbyshire - Coding Interest Rates (companion book); West - Interest Rate Derivatives lecture notes (2010); Salomon Brothers (Ilmanen) - Understanding the Yield Curve Part 7 (Feb 1996); Quantitative Finance Stack Exchange threads on vega-gamma links and break-even vol; Nordea EUR Rates (2020, 2025); ING Rates Strategy (15 Jan 2020); Barclays, BofA and Citi weeklies and J.P. Morgan, Credit Suisse, Morgan Stanley and Nomura notes dated in the text; tpSEF swap specifications rulebook (May 2021).
