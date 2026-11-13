---
name: fi-carry-and-rolldown
description: Carry and roll-down for G10 swaps, repo-financed bonds, bond and STIR futures, forward-starting swaps and curve trades, with forwards read as breakevens and carry/vol ratios. Gives exact formulas (forward-minus-spot carry, frozen-curve roll, forward price and forward yield at term repo, basis carry), sign and scenario conventions, breakeven as a fraction of a 1-sigma move, and carry-to-risk screens that expose carry as short vol. Use when asked about carry, roll, rolldown, roll-down, slide, roll yield, rolling yield, C&R, carry and roll, breakeven, forward vs spot, 1y forward, aged yield, pull-to-par, repo carry, specialness, negative carry, carry per DV01, carry/vol, ex-ante Sharpe, forwards realised vs curve unchanged, what happens if the market does nothing, receiver or payer carry, flattener, steepener or fly carry, forward-starting swap roll, or ranking trades by carry.
---

# Carry and roll-down

Carry is the P&L you collect for holding a position while nothing is marked; roll-down is the mark-to-market you gain
when the curve keeps its shape and the instrument ages along it. Both are measured against a stated scenario, are
quoted as a rate or yield cushion (bp) and as cash (rate x DV01), and always have to be read against volatility: a
position that earns carry if "nothing happens" is economically short volatility. This skill defines the numbers
exactly, for swaps, bonds with repo, futures and packages, and turns them into breakevens and carry/vol ratios.

## Conventions (state these on every output)
- **Sign.** Receiver / long duration / long bond is positive. Positive carry or roll = the position earns it. A payer
  or short bond has the opposite sign. Curve A-B = longer minus shorter (2s10s = 10y - 2y); a steepener is long the
  spread = **receive the short end, pay the long end**. Fly 2s5s10s = 2x5y - 2y - 10y (positive = belly cheap); long the
  fly level = pay the belly; "receive the belly" is short the fly level and earns when it falls. Carry/roll below are always
  per **receiver** leg, so a structure's carry = sum of weight x leg carry with receive = +.
- **Scenario.** Default = **curve unchanged** (today's par/zero curve frozen, the instrument ages along it). Benchmark
  = **forwards realised** (the curve evolves to today's forwards), under which a mid-market swap and every bond earn the
  short rate, so carry + roll beyond that is a bet against the forwards (Tuckman & Serrat, Fixed Income Securities,
  4th ed., 2022). A third, "expectations realised", needs a term-premium model and is not implemented. Never quote a
  number without naming the scenario.
- **Units.** Rates in percent in, bp out. Rate-space carry/roll (bp of yield) is comparable across maturities; cash =
  bp x DV01 of the **aged** (forward) position, not today's. A 10bp roll is about 10 x DV01 (Nordea Research, Carry &
  Roll, 12 Jul 2013).
- **Horizon h** in years: 1m, 3m (default, matches desk screens), 6m, 1y. Roll is **not linear in h**: compute each
  horizon from the curve, never scale 3m by 4.
- **Carry vs roll.** Carry = certain, locked by cash flows known today. Roll = uncertain, an unchanged-curve
  assumption, "not an expectation" (Nordea 2013). Quote them separately and as a total, and say which "carry" a
  source means: some sources call carry+roll "carry", some call the fixed-minus-first-float coupon gap "carry".

## When to use
- "What is the carry / roll / C&R on the 5s30s?", "what do I earn if nothing happens?", "what is the breakeven?"
- Ranking outrights, curves, flies, forward-starting swaps or bonds by carry and carry per unit of vol.
- Deciding spot vs forward vs term-financed expression of the same view.
- Net-of-carry targets and stops in a trade write-up; re-underwriting a position whose carry has changed.
- Sanity-checking a dealer or screener carry number, or a backtest's carry accrual.

## Inputs (data-agnostic)
Schemas in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If an input is missing, ask for it. Never invent values.

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap/OIS rates, spot and forward-start | `curve_par` | daily snap, all tenors incl. 3m-1y short end | spot-start `start=0D`; forward grid via `start` |
| Discount factors (preferred for forwards) | `curve_zero` | same snap | forward par rates from DFs, not from par rates |
| Fixed/float conventions, accrual, lags | `swap_conventions` | static | accrual fraction goes into carry DV01 |
| IBOR-style or policy first fixing | `rate_fixings` | latest | only for the fixing cross-check |
| Bond terms, coupons, ex-div rule | `bond_static` | static | coupon schedule gives interim cash |
| Clean/dirty price, accrued, yield | `bond_quotes` | daily | `settle_date` matters |
| GC and specific (special) repo by term | `repo_rates` | daily, terms to horizon | `specialness_bp`; use term to the horizon |
| Bond-futures prices, CTD, conversion factors | `fut_quotes`, `fut_static`, `fut_basket` | settle snap | for basis carry |
| STIR futures strip | `stir_quotes` | settle snap | roll along the strip |
| Realised vol of the structure | derived from `curve_par` history | 63d (3m) to 252d | same structure, same snap, daily changes in bp |
| Implied vol (optional) | `vol_surface` | daily | for carry-vs-premium comparisons |

## Method

### 1. Pick scenario and horizon, build the aged instrument
Age by moving the **valuation date** forward by h and re-reading the frozen curve (a "rolled" curve needs no
recalibration; Darbyshire, Coding Interest Rates). Do not age a struck swap by translating the curve. Reprice the aged
package. Age forward legs by their **start**, not their tail (5y5y becomes 4y5y, not 5y4y).

### 2. Spot-starting swap (receiver positive)
```
carry = F(h, T-h) - S(0, T)          # forward par rate of the aged tail minus today's par
roll  = S(0, T)   - S(0, T-h)        # frozen curve, shorter spot
total = carry + roll = F(h, T-h) - S(0, T-h)
cash  = total_bp x DV01 of the aged swap (forward annuity), per currency unit
```
- Compute F from discount factors: `F(s,n) = (DF(s) - DF(s+n)) / sum(alpha_i DF(t_i))`. Applying the zero-rate
  identity to par rates is only approximate.
- **Fixing shortcut** (term-index legs only): `carry = DF(h) x (S - fix) x alpha / A_fwd`, alpha = 0.5 for a 6m
  period, A_fwd = annuity (DV01) of the forward swap. It equals F - S **only when h equals the fixing period** and
  must not be used for longer horizons (Nordea 2013). Omitting alpha doubles the carry. Because
  `S(T) x A(T) = fix x DF(h) x alpha + F x A_fwd`, the two quotes agree once scaled, e.g. 0.25 (S5y - L3m) = 4.75 (F - S5y)
  ignoring discounting (Quantitative Finance Stack Exchange, "Carry calculation on an interest rate swap", Aug 2017).
- On RFR (OIS) swaps there is no single known first fixing, so use forward-minus-spot from the curve; collateral
  carry should reference the RFR/repo rate, not an IBOR (same source).
- Under forwards-realised, the same carry is exactly offset by the mark of the aged swap (roll = S(T) - F(h, T-h)), so
  carry + roll of a par swap is zero by construction and ranks nothing; use it as the benchmark only. Scenario table and
  the per-notional vs per-DV01 split: [formulas](references/formulas-and-derivations.md).
- **Roll depends on interpolation.** Read roll at knots and mid-knots with two interpolators (shape-preserving default,
  plus linear). Differences concentrate at local extrema and mid-knot points (Darbyshire, Pricing and Trading IR
  Derivatives, 3rd ed., 2022). If they differ by more than 25% of the roll, flag it as model-dependent.

### 3. Forward-starting swaps and forward grids
- **Carry = 0** (no float payment is known). Roll = S(s,T) - S(s-h,T): the forward period shortens, tenor unchanged.
  1y5y -> 6m5y; 6m5y -> 0d5y (Nordea 2013).
- If h > s the aged swap is spot-starting with a known first fixing; assume today's fixing persists (Darbyshire 2022)
  and say so, or keep h <= s.
- All the "carry" of a forward-starting trade is roll, so a forward-starting position that earns it only has the
  unchanged-curve scenario. It is a view that the market will not reprice the near-term policy path.
- **Forward-curve top.** Plot 1y forwards by start with each point's 1y roll. Roll is positive below the hump and
  negative above it; "receive below the hump, pay above it" (receive 10y5y, pay 15y5y in EUR) (Nordea, EUR Rates Flash,
  24 Jan 2020). Long-start forwards beyond about 20y can roll negatively (EUR, Feb 2020). Detail: [forward-grid](../curve-forward-grid-rv/SKILL.md).

### 4. Curve trades and flies
- Use **DV01 weights** (receive +). Then each leg carries the same initial risk and leg rolls in bp add without scaling:
  `structure_total_bp = sum_i w_i x total_i` (Nordea 2013). A cash steepener ages (2s10s -> 1s9s); a forward-starting
  steepener does not carry a short-end fixing.
- Forward slope minus spot slope = the steepening the trade needs to break even. A DV01-weighted trade depends only
  on the slope change (BofA, Rates Basics: Spot vs Forward, 15 Feb 2024).
- Hedge ratios decay as PVBP ages; size with the forward PVBP matched to the horizon (Duering, Fixed Income Trading
  and Risk Management, 2021). Do not re-weight risk-neutral legs to manufacture positive carry.
- In a concave curve any duration-neutral flattener has negative carry (Ilmanen, Understanding the Yield Curve Pt 1,
  May 1995). In a cutting cycle receiving front outrights bleeds while receiving curves and front flies earns
  (Nordea, EUR rates: Pushing back, 17 Jan 2024).

### 5. Bonds financed in repo
**Price form** (per 100 face; Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005):
```
no coupon in period:  income = (C/f) x D/DCOUP ;  financing = (P + AI) x RP x D/360   # repo basis per market: 360 USD/EUR, 365 GBP
one coupon inside:    income = (C/f) x (D1/DCOUP1 + D2/DCOUP2) ;  financing = (P+AI) x RP x D1/360 + P x RP x D2/360
carry  = income - financing        # RP = TERM repo to the horizon/delivery, own-issue not generic GC
```
**Forward price** (Tuckman & Serrat 2022, ch. 11): `full_fwd = (P+AI)(1 + r d/360) - sum c_i (1 + r d_i/360)`,
`flat_fwd = full_fwd - AI_fwd`, **forward drop = P - flat_fwd ~ carry**. Forward < spot when coupon income exceeds
financing.

**Yield form (preferred for ranking, coupon independent):**
```
carry_bp = y_fwd - y_spot ~ (y - repo) x h / D_fwd        # forward modified duration, SIMPLE yield
roll_bp  = y(T) - y_proxy(T-h)                            # proxy: same-type bond or fitted curve point, 3m shorter
total_bp = y_fwd - y_proxy(T-h)
```
Use the bond's **yield, not its coupon**: a 10% coupon 1y bond at 110 shows why (swapsball.net, How to calculate
carry and roll-down for a bond future's asset swap, Dec 2017). The simple-yield approximation tracks exact 3m carry
across prices 80-120; the compound-yield version diverges badly off par (Duering 2021, ch. 16).

- **Roll proxy is subjective.** Take a fitted par curve (bond-rich-cheap-fitted-curve), exclude structurally different
  paper (rich/cheap issues, on-the-runs); a discrete curve needs a spline. Anchor the short end to GC repo, not bills,
  for stable forwards (J.P. Morgan, new and improved Treasury par curve model, 16 Jul 2018).
- **Buffer** (Duering 2021): forward yield (bond-specific repo) minus expected yield (spot yield + curve fair-value
  change over the horizon). It is how far the whole curve can rise before carry and roll are gone, and it embeds
  specific repo, pull-to-par and rich/cheap.
- **Repo.** Match term repo to h; overnight is cheaper on a positive curve but leaves roll-over risk (a long loses if
  overnight rises) and a stub rate exposure (about a 3m duration position if not termed). Shorts: reverse repo is
  normally 10-25bp below repo and specials have no floor (10y CTD traded at -15% o/n in May 2005, Burghardt 2005).
  Specialness drag = (GC - special) x notional x t, so a special short leg can flip a "positive carry" steepener
  negative. Fails penalty since May 2009 is max(0, 3% - fed funds) (Tuckman 2022, ch. 10). Haircut risk is part of
  carry risk: repo-to-maturity carry on peripheral EGBs (6.00%/4.50% coupons vs about 0.70% repo) was destroyed when
  haircuts rose from 3% to 80% (Tuckman 2022, ch. 10).
- **Pull-to-par.** A premium bond loses price as it pulls to par while collecting a large coupon. Cash carry and
  carry-roll-down must be read together (Tuckman 2022, ch. 3); the yield form handles it.

### 6. Futures and packages
- A future has no pure carry (zero outlay, only MTM). "Futures carry" = futures-implied forward yield of the CTD minus
  spot CTD yield, i.e. the carry of the deliverable at implied repo. A long future is long the CTD forward financed at
  implied repo (swapsball 2017).
- **Basis.** Gross basis GB = P - CF x F; net basis NB = P_fwd - CF x F; **GB - NB = carry to delivery**; the daily
  drop in gross basis = carry (a Friday spans T+1 to T+3, so drops ~3x). Positive carry favours delivery on the last day;
  an inverted front end favours early delivery (Burghardt 2005). IRR = (Invoice/Purchase - 1) x 360/n; compare IRR
  with **your own** term repo. Positive curve slope = positive carry for the long basis.
- A low net basis is not free optionality: if carry into delivery is strongly negative the option window shrinks
  to the start of the month (BofA, Buy futures basis = cheap options, 10 Apr 2025). The roll-down hypothesis forces all
  optionality to zero, including the short delivery option embedded in a long future (swapsball 2017).
- **Packages (future vs swap, EFP).** Compute C&R per leg because dates differ. The classic error is rolling only the
  swap leg ("the future is a forward already"), which assumes an unchanged swap curve but a fully realised bond
  forward (swapsball 2017). Bobl futures ASW: carry = spot CTD ASW - futures ASW at the delivery date (3m horizon
  minimises assumptions); roll = move toward a proxy bond 3m shorter.
- **STIR futures.** No carry; all return is roll along the strip. Roll-down of a fly = current fly - the fly one slot
  shorter, i.e. where it sits in 3m if nothing changes (Clarus Financial Technology, Dummies Guide to Trading IRS,
  Jun 2024). Roll SR3 before a contract enters its reference quarter, between the 2nd and 3rd listed, not front to back;
  Dec-19 to Mar-20 cost 138bp at quarter-end vs 4bp at the start (Huggins & Schaller, SOFR Futures and Options, 2022).
  Convexity-adjustment roll: [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md).
- Futures rates exceed forward rates (compounded 3m > average 1m > forward); convexity-adjust before comparing a
  futures strip with OIS forwards (Tuckman 2022, App. A).

### 7. Forwards as breakevens, not forecasts
- A forward is the arbitrage-free breakeven between two maturities. 1y 3%, 2y 4% imply 1y1y ~ 5%. If the 1y rate in a
  year is below that, owning the 2y beats rolling (Bassman, Sharp Curve Ahead, 25 Jan 2024).
- **Breakeven yield change** over h: in rate/yield space `total_bp` (carry + roll) already is the parallel yield rise the
  position can absorb; if carry + roll is in price units, divide by the forward modified duration.
  `breakeven_in_sigma = total_bp / (sigma_daily x sqrt(252 h))`. Active rule: be bearish only if you expect yields to
  rise **more** than the forward implies; bullish if you expect a smaller rise than needed to offset positive carry
  (Ilmanen, Understanding the Yield Curve Pt 1-2, 1995). The forward is the same for a long and a short.
- **Spot vs forward is a view on term financing vs the expected overnight path.** Long duration: if term repo (or the
  1y rate) looks too high, own spot and roll overnight; if you do not disagree with term pricing, the forward is
  simpler (carry locked, threshold known). A long financed 5y UST ~ receive 5y swap / pay o/n SOFR; the 1y-forward 5y
  note ~ 1y4y (BofA 2024).
- **Evidence.** US 1968-95: 3m-ahead implied changes averaged +0.65 (3m) falling to +0.07 (6y) while realised changes
  averaged about 0, correlations -0.04 to -0.13 (Ilmanen & Iwanowski, Understanding the Yield Curve Pt 7, Feb 1996).
  Steep curves predict excess returns, not rising long rates (Ilmanen Pt 2). So use today's spot curve, not the
  forward curve, as the neutral base case, and treat carry as a risk premium that is earned on average and lost in
  vol spikes and crowded unwinds.
- Long forwards embed a convexity bias (~ -0.5 C sigma^2); a forward-based cheapness screen mechanically makes the long
  end look rich unless adjusted. The bias is only a few bp under 3y (Ilmanen Pt 1-2).

### 8. Expected return = carry + roll + convexity
For maturity M, horizon T, yield Y, funding F, normal vol sigma (yield bp/yr), D = horizon duration:
`E(R) = (Y - F) T / D  +  (Y_M - Y_{M-T})  +  0.5 Cx sigma^2 T / D` in yield bp (drop the /D for price return; J.P. Morgan, Valuing convexity in the long end,
9 Feb 2018; Ilmanen Pt 5). Use **bp (normal) vol** and scale with sqrt(h) (annual 82bp -> 41bp for 3m, so 0.5 x 2.57 x
0.41^2 = 0.22% of price for a 30y par, Ilmanen Pt 5). Doubling vol quadruples the convexity value. Rolling yield alone assumes zero vol and
is biased down for positively convex bonds. Ilmanen's five-term build (yield income, rolldown, convexity, duration
impact, local rich/cheap incl. repo advantage) is in [formulas](references/formulas-and-derivations.md). Long-end
carry vs convexity trades (curve-implied breakeven vol, daily breakeven BE/realised vol):
[vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md).

### 9. Carry/vol, ranking and screens
```
sigma_h        = vol_daily_bp x sqrt(252 x h)            # same structure, window ~ horizon
horizon_sharpe = total_bp / sigma_h                       # also = breakeven as a fraction of 1 sigma
annual_sharpe  = horizon_sharpe / sqrt(h)
carry_over_R   = annual_sharpe / (1 + |R|)               # R = rank correlation of 3-day changes with the outright
months_to_BE   = mispricing_bp / (carry bleed bp per month)
```
- **Why not carry alone.** Long carry is short vol, so rank on carry/vol. Positive roll "is akin to selling volatility
  and going long theta"; roll-down strategies are "inherently short volatility positions" (Darbyshire 2022, ch. 23).
- **Defaults.** 3m horizon, 63d realised vol of the structure level (252d for slower monitors; Nordea uses 252d, Goldman
  Sachs desk screens 3m). Use the vol of the **same** structure, and for roll along a forward path the average vol of the
  points spanned (Nordea EUR Rates Flash, 23 May 2019).
- **Thresholds in sources.** Sharpe above 1.0 "reasonably attractive" (Darbyshire, subjective). Swap spreads: hurdle
  carry/vol 0.25, solve for the spread at which the ratio falls to it (Barclays, Swap spreads: the bright spot in US
  rates, 30 Sep 2026). Nordea ratios of 0.3-1.2 flag screen leaders (EUR 2s5s 0.30, paid 5y7y/12y8y/20y10y 0.85-1.01).
  Agent defaults (judgement, not sourced): breakeven below 0.5 sigma_h = meaningful cushion; above 1 sigma_h = carry
  cannot be the reason for the trade.
- **Directionality.** Carry/R = Sharpe/(1 + |R|); in trending markets Carry+Entry screens fill with outright forwards
  at extreme z that are pure duration (R near 1) (Goldman Sachs desk material, Global Rates Best Trade Report,
  30 Sep 2026). Check payer/receiver perspective: a receiver idea needs negative payer-perspective carry.
- **Do not trust first-order carry/vol matrices** (roll / vol of the spread) alone: "easy to calculate ... can be
  misleading by considerably overestimating some of the ratios". Use second-order Sharpe with gamma per leg, or at least
  check that the highest ratio is not simply the longest, most convex leg (Darbyshire 2022, ch. 23.3).
- **Value vs carry frontier.** Scatter PC1 residual (value) against 3m roll per forward. ING EUR 2F1Y-15F1Y: y = -1.27 x
  + 16.4, R^2 = 0.93: "more attractive valuations come at the expense of carry"; 1F1Y and 20F1Y+ sit off the line
  (ING, Deconstructing the EUR yield curve, 15 Jan 2020). For negative-carry value trades compute months-to-breakeven.
- **Carry vs vol scatter.** EUR ATM normal vol vs 3m roll per forward: R^2 = 0.97 for 2F1Y-15F1Y; receive where carry is
  high and vol low, breaks down at 20F1Y-30F1Y (ING 15 Jan 2020).
- **Regime.** Rate vol spikes around the first cut, last cut, first hike and when the Fed accelerates; quiet late in
  hiking cycles and in the pause (Willer & Saunders, Trading Global Macro Markets, 2026). Carry is flat to negative
  in recessions, vol spikes and crowded unwinds (post-LTCM 1999-2002; J.P. Morgan, Investment Strategies No. 31,
  Jan 2007). A stress switch (cut carry when max z-score > 2) lifted a vol-adjusted FX carry IR from 0.89 to 1.30
  (Willer & Saunders 2026, ch. 12). Policy uncertainty should widen the discount required of a carry trade.
- **Cross-market carry rules** (10y yield minus 1m rate, FX-hedged UST-Bund pickup deciles, carry-to-risk position
  sizing) belong to [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md); use carry-to-risk,
  not raw carry (Japan: low carry but not low carry-to-risk; J.P. Morgan, Investment Strategies No. 74, 2 Oct 2012).

### 10. Accounting in backtests and P&L explain
- Attribution by sequential repricing: price at start; reprice at the scenario curve, spread unchanged = carry-roll-down;
  reprice at the actual end curve = rates; at actual end spread = spread; add cash carry. Check: cash carry + carry-roll
  = (short rate + spread) x time under realised forwards (Tuckman 2022, ch. 3).
- **Opening-curve rule.** For daily explain, build today's opening curve by holding **forwards constant** (scale
  yesterday's DFs by DF(today) seen yesterday, or reprice inputs on the new schedules). Reusing yesterday's closing input
  prices introduces spurious roll-down and offsetting noise between carry and market move (Darbyshire 2022, s. 6.1.10).
- Mark aged tickets at their live start; accrue bond coupons and repo over every mark interval; include fixings in the
  curve. See [bt-backtest-design](../bt-backtest-design/SKILL.md), [bt-performance-attribution](../bt-performance-attribution/SKILL.md).

## G10 differences that change the number
Detail and sources: [market-notes](references/market-notes.md).
- **USD.** Term repo rarely beyond about 3m, so long-dated forwards are cheaper to express in SOFR swaps; UST carry needs
  per-issue repo (specials) and a spline for roll; futures carry uses bond-specific term repo to delivery. SR3 rolls
  2nd into 3rd contract. In early 2024 every UST beyond bills was negative carry against money-market yields.
- **EUR.** Term-index (Euribor-style) legs give the fixing shortcut with alpha = 0.5; 2y1y EUR RFR was the best receive
  point on roll (about 25bp over 1y, Jun 2025); the forward curve tops near a 15y start and rolls negative beyond it;
  EGB repo is issuer-specific (GC by country) and haircut risk is real for periphery.
- **GBP.** Evaluation date T+0 (most others T+2) shifts forward-start and roll dates; low-vol long-end forward spreads
  give high Sharpe on small carry; gilt ex-dividend accrual is negative.
- **JPY.** Long-end curve slopes the other way, realised vol is low (2.3-3.1bp/day vs 3.9-4.7bp elsewhere), curve-control
  regimes break mechanical carry rules, FX-hedged JGBs showed the highest hedged carry in rates (Aug 2026).
- **CAD / AUD / NZD / CHF / SEK / NOK.** Check leg frequencies in `swap_conventions` (bank-bill floats are 3m or 6m, fixed legs annual or
  semi-annual; repo basis typically Act/365 in JPY, CAD, AUD, NZD, GBP and Act/360 in USD, EUR, CHF, SEK, NOK; confirm in [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md)) before using the fixing shortcut; AUD bond futures quote 100 - yield and cash-settle against a
  basket, so futures C&R is per leg; NZD has the steepest vol-adjusted curve; CHF and JPY low yielders rally in risk-off,
  which is why carry works worse in G10 than EM. SEK/NOK forward universes are small (screens stop near 1y10y/5y5y).

## Worked examples
Full numbers and more cases (Tuckman attribution, UST forward breakevens, Ilmanen tables, cross-market rolls):
[worked-examples](references/worked-examples.md).

**A. EUR 5y swap carry and roll (Nordea Research, Carry & Roll, 12 Jul 2013, close 14/6/2013).** S(5y) 1.023%,
S(4.5y) 0.928%, S(6m,4.5y) 1.1015%, 6m Euribor 0.319%, DF(6m) 0.9995, annuity of the 6m4.5y 4.45.
Roll 6m = 1.023 - 0.928 = **9.5bp**. Carry by the fixing form = 0.9995 x (1.023 - 0.319)% x 0.5 / 4.45 = **7.9bp**; by
forward-minus-spot = 1.1015 - 1.023 = **7.9bp** (agree; without the 0.5 the first form would be 16bp). Receiver on the
6m5y: roll 1.195 - 1.023 = 17bp. 2s5s 6m-forward flattener, DV01-neutral 1:2.48 on 100m of 6m5y (leg risk 4.93): roll
(1.195 - 1.023) - (0.632 - 0.498) = 3.7bp (3.8 from the rounded quotes shown) x 4.93 = 18.2bp, about 182,400 on 100m:248m.

**B. Zero-curve carry/roll and the 2s4s flattener (Ilmanen, Understanding the Yield Curve Pt 1-2, May-Jun 1995).** s1 = 6%,
s2 = 7%: forward 1y1y = 1.07^2/1.06 - 1 = 8.01%. Carry = 8.01 - 7.00 = 1.01, roll = 7.00 - 6.00 = 1.00, total 2.01 = the
2y zero's 1y excess return over the 1y rate; the 2y yield must rise 1.01% before it underperforms. With s3 = 7.75 and
s5 = 8.73, the 2s4s flattener via 1y/3y/5y zeros has carry 0.5(6.00 - 7.75) + 0.5(8.73 - 7.75) = -39bp and needs the 2-4y
spread to narrow 52bp in a year.

**C. Bond carry and forward (Burghardt 2005; Tuckman 2022).** 7-1/4% 8/15/22, full price 120.8764, term repo 4.54%, 84 of
181 days: income 1.68232, financing 1.280484, **carry 0.401836** per 100 (12.9/32). 2.875s 5/15/28, spot 110.77344 + AI
0.01562, repo 0.015%, 136 days to 30 Sep 2021: full forward 110.79534, flat forward **109.71721**, drop 1.06 =
(2.875/2)(136/184) - 0.015% x 136/360 x 100. TYU1 (futures 131-17+), CTD CF 0.8338: GB 1.0896 (34.9 ticks), NB 0.0334 (1.1
ticks), carry 17 May-30 Sep 1.056 (33.8 ticks).

**D. UST forward breakevens (BofA Global Research, Rates basics: spot vs forward, 15 Feb 2024).** 5y 4.15% vs 1y-forward
3.93%: financed for 1y at 4.91%, the long needs a 22bp rally (about a third of a 1y 1-sigma move of 65bp) to break
even; 30y breakeven 3bp (about 6% of 1 sigma). 5s30s spot 23bp, forward 42bp: a DV01-neutral steepener needs 19bp of
steepening in a year.

**E. Carry/vol screen (Nordea, EUR rates: How about that outright receiving, 26 Sep 2025).** Receive EUR 2s5s at 24bp,
12m carry 3.2 + roll 3.5, convexity-adjusted 6.7bp, 252d vol 22.3bp, ratio 0.30; a 2y1y 3s receiver has C+R 25.0 and
ratio 0.35 but correlation 0.92 to the 10y, so it is duration, not carry.

## Signals & interpretation
- **Carry/roll cushion vs vol.** Total below 0.5 sigma_h: carry is decoration. 0.5-1: helps timing, not the thesis.
  Above 1: the trade can wait for the view (positive carry gives "time to let the view unfold"; BofA, UST RV Primer,
  2 May 2022). Negative carry: require months-to-breakeven comfortably longer than the expected time to converge.
- **Receiver/payer.** If a cut is priced, front-end roll is mostly the priced path: "some but not all" survives a
  cut (Nordea 17 Jan 2024). A 6-week delay of a cut costs an 18m receiver about 14bp of roll (Darbyshire, Coding Interest Rates,
  Ex. 13.1). Show roll with and without the next priced meeting before calling it carry.
- **Value + carry agree** = best. Value + carry conflict = you are paying carry for mean reversion; use months-to-breakeven.
- **Exit/scale** when carry deteriorates and breakeven/realised vol rises toward 1 even with the view unchanged
  (Citi, Alert: taking profits on delta-hedged 15y5y/20y10y flatteners, 5 Dec 2019).
- **Steep forward steepeners** with the best carry usually come with the worst entry; use carry/BE and z-scores and
  check lookback sensitivity (Citi Rates Vol Lab, 12 Jun 2023).
- **Positive-carry crowding.** When everyone holds positive-carry steepeners, look for positive-carry flatteners as a
  diversifier; pick carry trades that do not duplicate the book's main risk (Nomura, Derivative Focus, 19 Jun 2014;
  Nordea 26 Sep 2025).

## Pitfalls
- **Wrong scenario.** Mixing "forwards realised" and "curve unchanged" inside one ranking. Under the first, a par swap
  has zero carry+roll. State the scenario.
- **Fixing shortcut beyond one fixing period**, or without the accrual fraction. Longer-horizon C&R on a spot swap is
  ambiguous for the unknown fixing: use roll assumptions (frozen curve incl. the fixing).
- **Carry per notional vs per DV01.** 100mm of 5y is about 50mm of 10y; compare per DV01 (QFSE, Aug 2017).
- **Coupon instead of yield** in bond carry, or compound instead of simple yield approximation.
- **One GC rate for all bonds.** Financing nets to about zero and a switch looks free. Use own-issue repo; specials change
  forwards and the repo term structure is time-varying (J.P. Morgan, Forward Treasury, Asset Swap and Funding Report,
  29 Jan 2015). Specialness varies each roll, so futures carry estimates are per quarter (Bassman, Leverage is NOT a
  four-letter word, 26 Jan 2023).
- **Spot-starting IRS fixed first period.** A 2y/10y is effectively 1.5y/9.5y forward-ish and adds an outright delta,
  "a common source of unexplained PnL"; use forward-starting legs sized to the intended vol-adjusted delta (QFSE,
  Different ways to express a 2s10s steepener, Mar 2018).
- **Roll ignores the rate path.** If a 25bp hike is fully priced tomorrow, receiving across the meeting shows 25bp of
  "roll" over one day (swapsball 2017). "When the IR curve is expected to change dramatically this is precisely the
  point at which roll-down becomes unappealing" (Darbyshire 2022).
- **Short vol in disguise.** Forward steepeners and long-end carry harvesters are short convexity and short payer
  skew; "more harmful in volatile selloff regimes than valuable in gradual rally regimes" (Citi, European Rates
  Weekly, 24 Sep 2026). Judge carry against realised vol via breakevens.
- **Convexity bias.** Forward-based cheapness makes the long end look rich; adjust first. Long convexity bleeds when
  realised vol is low, so "free convexity" at positive carry may only reflect an illiquid market (Citi, Rates Vol Lab,
  30 Mar 2020).
- **Roll from model noise.** Interpolation disagreement concentrates at local extrema and mid-knot points; supply
  short-end tenors (3m, 6m, 1y) or the front-end roll of any aged structure is understated.
- **Hedge DV01 decay and IMM/par-tenor mismatch.** DV01 changes as instruments age; revaluation jumps around IMM roll
  dates when a swap hedge turns into a future (Clarus, Mechanics and Definitions of Carry in Swap Markets, 16 Jan 2019).
- **Double-counted financing.** If you supply own-issue repo, switch off any pricing-engine carry that already includes a
  funding rate, or carry is counted twice. Roll-down aged on the wrong leg (tail instead of start) reverses the ranking.
- **Carry is user-specific.** Count IM, balance sheet, capital, funding and gamma hedging costs; a mid swap's basic
  cost of carry is nil (Darbyshire 2022). See [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md).
  Negative swap spreads are not free carry: balance sheet, repo-vs-index basis and illiquidity all grow with maturity.
- **Vol targeting does not tame carry tails.** Trailing-vol targeting of IRS carry raised excess kurtosis 2.4 -> 2.9 and
  fails when vol is low just before a crisis (Macrosynergy, Interest rate swap returns: empirical lessons; Willer &
  Saunders 2026).
- **Specific market breaks.** Carry rules fail under yield-curve control (BoJ: substitute the next-lowest-carry market);
  SOFR statistics mixing pre- and post-Aug 2021 regimes should be re-estimated (Huggins & Schaller 2022).
- **Pennies in front of a steamroller.** Cash carry accrues only while held and the MTM on the remaining tenor can hit
  at any time; judge carry against the plausibility of the forwards being realised (Clarus 2019).

## Output
Return a table plus one-paragraph read per candidate, all with convention stated (receiver positive, scenario, horizon; name each
structure with its receiver legs, e.g. "steepener: rec 2y / pay 10y"):

| structure | h | carry_bp | roll_bp | total_bp | cash per 1mm (aged DV01) | breakeven (bp, % of 1 sigma_h) | vol_daily_bp (window) | horizon_sharpe | annual_sharpe | R vs outright | months_to_BE | repo/specialness used | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Flags: `fixing_shortcut_used`, `h>start`, `interp_sensitive`, `special_leg`, `priced_meeting_in_roll`, `negative_carry_months_lt_4`.
Then: scenario assumed, what has to happen to the market for the number to be wrong, and the hand-off to
[rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) (carry/roll lines, targets net of carry) or
[rv-composite-scoring](../rv-composite-scoring/SKILL.md) (carry/vol as a score input).

## Scripts
- [`scripts/carry_roll.py`](scripts/carry_roll.py): simplified single-curve carry/roll for outrights and structures
  (`Curve`, `carry_roll`, `structure_carry_roll`), the fixing cross-check, bond price-form and yield-form carry,
  forward price, basis carry and carry/vol helpers. CLI reads a `curve_par` CSV/Parquet:
  `python scripts/carry_roll.py --par curve_par.csv --curve USD-SOFR --h 0.25 --tenors 2,5,10,30 --structures 2s10s,2s5s10s`
  (`2s10s` = steepener, receive 2y/pay 10y; `2s5s10s` = long the fly level, pay the belly; negate for receive-the-belly; vol
  uses history up to `--date` only).
  `python -I scripts/carry_roll.py --selftest` checks closed-form and cited known answers (Ilmanen zero curve, Nordea 7.9bp,
  Burghardt 0.401836, Tuckman 109.71721, par-bond zero carry) and exits non-zero on failure. Screening only; for trading
  numbers use the dated curve from [fi-curve-construction](../fi-curve-construction/SKILL.md).

## Related skills
- [fi-curve-construction](../fi-curve-construction/SKILL.md): discount factors and forward par rates the roll is read from
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): accrual fractions, day counts, repo bases, lags
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 of the aged position, key-rate hedges
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-space RV, roll-adjusted forwards
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md), [curve-butterflies](../curve-butterflies/SKILL.md): weights and carry of curve structures
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): carry vs convexity, curve-implied breakeven vol
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): option carry, static roll, carry vs premium
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md), [fut-calendar-roll](../fut-calendar-roll/SKILL.md): basis carry, roll
- [stir-futures-rv](../stir-futures-rv/SKILL.md), [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): STIR roll along the strip, CA roll
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): GC vs special, term repo
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): priced path inside front-end roll
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): fitted curve for the bond roll proxy
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread carry and balance-sheet cost
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md), [xccy-basis](../xccy-basis/SKILL.md): FX-hedged carry, basis carry
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): linker and inflation-swap carry
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): carry as a systematic signal
- [bt-backtest-design](../bt-backtest-design/SKILL.md), [bt-performance-attribution](../bt-performance-attribution/SKILL.md): carry accrual and P&L explain
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): pre-mortem for carry trades

## References
- Nordea Research - Carry & Roll (L. P. Lilleore, 12 Jul 2013): swap carry/roll formulas, fixing shortcut, 2s5s forward flattener roll
- Salomon Brothers - Understanding the Yield Curve, Parts 1, 2, 5, 6 (A. Ilmanen, May-Nov 1995): forwards as breakevens, rolling yield, convexity-adjusted expected return, holding-period decomposition
- Salomon Brothers - Understanding the Yield Curve, Part 7 (A. Ilmanen, R. Iwanowski, Feb 1996): evidence that carry is earned
- Tuckman and Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): realised forwards vs unchanged curve, carry/roll attribution, forward price and drop, repo specialness, basis carry
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): exact bond carry, IRR, basis = carry + options, repo/special effects
- Duering - Fixed Income Trading and Risk Management (Wiley, 2021): carry price/yield forms, forward price with repo, buffer, curve-trade carry vs forward horizon
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022): cost-of-carry vs roll-down, roll scenarios, first- vs second-order carry/vol, opening-curve method
- Darbyshire - Coding Interest Rates: FX, Swaps and Bonds (rateslib companion): curve roll operation, 6-week delay example
- swapsball.net - How to calculate carry and roll-down for a bond future's asset swap (12 Dec 2017): definitions for swaps, bonds, futures, packages
- BofA Global Research - US Rates Watch: Rates basics: spot vs forward (R. Axel, 15 Feb 2024): forward breakevens in sigma, spot vs forward choice
- BofA Global Research - US Rates Primer: UST RV Primer (Zhang, Braizinha, Axel, 2 May 2022): carry/rolldown definitions, vol-adjusted carry
- BofA Global Research - US Rates Alpha: Buy futures basis = cheap options (R. Axel, 10 Apr 2025): net basis and flat carry into delivery
- J.P. Morgan - Valuing convexity in the long end of the yield curve (Salford, Younger, Salem et al., 9 Feb 2018): E(R) = carry + slide + convexity
- J.P. Morgan - The new and improved Treasury par curve model (J. Barry et al., 16 Jul 2018): GC-anchored par curve for slide
- J.P. Morgan - Forward Treasury, Asset Swap and Funding Report (A. Roever, 29 Jan 2015): forwards with bond-specific repo
- J.P. Morgan Investment Strategies No. 31 (Jan 2007) and No. 74 (Oct 2012) (Panigirtzoglou; Mac Gorain): carry-to-risk and failure regimes
- Goldman Sachs desk material (IRP Market Strats) - Global Rates Best Trade Report (30 Sep 2026): carry/R and ex-ante Sharpe screen
- Barclays - Swap spreads: the bright spot in US rates (Mok, Nashikkar, 30 Sep 2026): carry/vol hurdle
- Nordea Markets - EUR Rates Flash (J. Vainikainen, 23 May 2019 and 24 Jan 2020); EUR rates (A. Svendsen, 17 Jan 2024, 12 Aug and 26 Sep 2025): forward carry monitors, forward-curve top, carry/vol templates
- ING Global Markets Research - Deconstructing the EUR yield curve (Bouvet, Schroeder, Garvey, 15 Jan 2020); No rise in rates but position for lower volatility (4 Feb 2020); EUR crisis trades: let's get tactical (3 Mar 2020): value-vs-carry frontier, carry-vs-vol, months to breakeven
- Citi Research - Rates Vol Lab and US Rates Weekly notes (Bikbov, Williams et al., 2019-2023), European Rates Weekly (24 Sep 2026), Regime Model update (Saunders, Vo, 12 Aug 2026) and Markets STIRT Weekly (7 Aug 2026): daily breakeven vs realised vol, exit rules, short-skew risk of carry steepeners, JPY hedged carry, AUD receiver carry
- Willer and Saunders - Trading Global Macro Markets (Wiley, 2026): carry timing, stress switch, FX-hedged carry rules
- Huggins and Schaller - SOFR Futures and Options (Wiley, 2022): SR3 roll rule and cost
- Clarus Financial Technology - Mechanics and Definitions of Carry in Swap Markets (C. Barnes, 16 Jan 2019) and A Dummies Guide to Trading Interest Rate Swaps (Jun 2024): carry definition, forward-start measure, microfly roll
- Macrosynergy - Interest rate swap returns: empirical lessons: carry as return predictor, vol-targeting caveat
- Harley Bassman (Convexity Maven) - Sharp Curve Ahead (25 Jan 2024), The Cost of Carry (5 Mar 2024), Leverage is NOT a four-letter word (26 Jan 2023), For Propeller Heads Only (17 Jun 2019), The Positive Carry Hedge: A Reprise (8 Dec 2010): forwards as breakevens, curve-trade breakeven, roll-up carry
- Quantitative Finance Stack Exchange - threads on swap carry (Aug 2017), carry-roll under expectations (Dec 2020), futures carry (Feb 2018), 2s10s steepener expressions (Mar 2018), implied repo and curve slope (Sep 2022), MtM of a swap if forwards are realised (May 2023), carry/slide on a CTD basis position (Aug 2023), a swap-carry note formula (Jun 2024): scenario splits, pure vs broad carry, fixed first period, accrual-fraction pitfall
- Nomura - Derivative Focus: Conditional Euribor bull flatteners (N. Firoozye, Q. Zhang, 19 Jun 2014): option-package carry by aged price, positive-carry flatteners as diversifier
- JWS Macro - USD and Global Rates Thoughts #2: Autumn 2025 (13 Nov 2025): NZD vol-adjusted steepness as carry harvester
- Huggins and Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): forward-vs-roll breakevens
- Aikin - STIR Futures (2nd ed., Harriman House, 2012): pack and bundle yields, strip roll-down
- Boyarchenko, Gupta, Steele, Yen - Negative Swap Spreads (Federal Reserve Bank of New York Economic Policy Review 24(2), Oct 2018) and BofA Global Research - US Rates Watch: Taking a look at SOFR spreads (R. Axel, 6 Oct 2020), Rates basics: fixed versus float (24 Apr 2024): swap-spread trade carry arithmetic, swapped-Treasury roll
- BofA Global Research - Global inflation-linked primer, 2nd ed. (Capleton, Swiber, 22 Jul 2025): linker carry in cash
- J.P. Morgan - Basis Scenario Analysis Report (28 Oct 2026); European Rates Strategy rule-based strategies update (6 Mar 2017); Investment Strategies No. 15 (Panigirtzoglou, 9 Mar 2006): term repo to delivery, G10 carry rank, cross-market carry rule
- Conks - Demystifying the Repo Market, Part III (28 May 2024): term vs overnight repo, repo-reverse spread
