---
name: vol-convexity-and-long-end
description: 'Values convexity in the long end and trades it as synthetic (strikeless) vol. Covers value of convexity (0.5*Cx*sigma^2), convexity bias in 30y/50y forwards and flies, DV01-neutral forward flatteners/steepeners as long/short gamma, curve-implied breakeven vol (sigma_BE) vs swaption vol, BE/RV screens, delta-hedge bands, convexity cost in flies/barbells, and sizing of MBS/VA/callable convexity-hedging flows. Use when asked if 10y10y/20y10y, 15y5y/20y10y, 20y5y/25y5y, 30s50s, GBP 15y10y/25y10y is cheap convexity, curve vs straddle, "is the ultra-long inversion just convexity", free convexity, gamma from the curve, convexity harvesting, strikeless or synthetic vol, forward flattener/steepener as long/short vol, 10y10y vs 20y10y, century/ultra bond convexity, barbell vs bullet, fly convexity cost, or MBS hedge need in a rally or sell-off. Forward-grid shape and kinks: curve-forward-grid-rv; hedged-option P&L: vol-gamma-vega-pnl.'
---

# Long-end convexity, convexity bias and synthetic vol

Convexity per unit of DV01 grows roughly linearly with tenor and with forward start, so a DV01-neutral package that
receives the later forward and pays the earlier one is long gamma. It pays on large moves either way and bleeds carry
if rates stand still, exactly like an option. That is why very long forward curves are inverted (the market charges
for convexity), why those curves co-move inversely with implied vol, and why a flattener can be a cheaper source of
gamma than a swaption straddle. This skill turns that into numbers: what convexity is worth, how much carry the
curve charges for it (breakeven vol), whether that is cheap versus option vol and realised vol, how to manage the
position, and how much of the long end is moved by other people's convexity hedging.

Conventions used throughout: curve A/B = rate(later) - rate(earlier) in bp; flattener = receive the later/longer leg,
pay the earlier/shorter leg, DV01-neutral; receiver = long duration = positive convexity; vols are normal bp per year
(daily ~ annual / 16, `sqrt(252)` = 15.87); carry in bp per year per unit curve DV01; fly 2s5s10s = 2x5y - 2y - 10y
(positive = belly cheap/high yield).

## When to use
- "Is 10y10y/20y10y (or 15y5y/20y10y, 20y5y/25y5y, 25y/30y/40y/50y, GBP 15y10y/25y10y) a cheap way to be long gamma?" or "what is the vol-adjusted carry of this forward flattener / steepener?"
- "Is the 30s50s (or ultra-long) inversion just convexity?" / "is this long-end bond rich or is that the convexity bias?"
- Curve package vs ATM straddle: "pay vol or pay the curve", gamma-matched straddle sizing, "strikeless vol".
- Convexity cost embedded in a fly, steepener or barbell/bullet; whether a forward fly is cheap after deducting convexity.
- Delta-hedge rules, re-weighting and exit for a convexity-harvest trade.
- "How much duration do MBS / VA / bank / pension hedgers have to buy or sell if rates move X bp?"

Out of scope (use the neighbours below): general swaption RV and implied-vs-realised grids, option P&L mechanics, listed
futures convexity adjustment, callable-to-vega-supply conversion, CTD/delivery options.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par rates of forward-starting swaps on a same-tenor strip (start 10y..30y, tenor 5y and 10y) | `curve_par` | daily snap, >= 3y (>= 10y for z-scores and share-of-days tests) | `par_rate_pct` x 100 = bp. The roll needs >= 3 starts per strip. If forward rows are missing, ask for them or build them (see [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md)); never bootstrap inside this skill |
| Discount factors (to reprice aged packages on shifted curves) | `curve_zero` | daily snap | For full-repricing convexity checks; flat-yield annuity durations are the fast default |
| ATMF swaption normal vols, expiry 1M-1Y, tails 20Y and 30Y | `vol_surface` | daily, >= 3y | `product=swaption`, `strike_offset_bp=0`, `nvol_bp`. Listed (futures-option) vol is a different market: do not mix |
| Realised vol of the long leg | derived from `curve_par` | 63d and 252d | bp/day, close-to-close on the same snap; same-contract (aged) series only |
| Bond DV01 / convexity, century and ultra bonds | `bond_quotes`, `bond_static` | daily | For single-bond expected-return work |
| Hedger stock (MBS duration/convexity, callable stock) | user-supplied or `positioning`, `flows_trades` | monthly/weekly | Only the sizing formula is data-free; stock data come from the user or the flow skills |

If an input is missing, ask for it or hand off to the data adapter. Never invent values. Contract is in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Method

### 1. Unit maths (what convexity is worth)
- Single cash flow: `P = e^{-yT}`, delta `-T·P`, gamma `T²·P`, so **gamma/delta = T**, independent of the level. Convexity per DV01 rises with maturity and decays linearly with time (Citi, A holistic approach to convexity, Jun 2022).
- Receiver on a (forward) swap at strike K: `V = (K - S)·A(S)`; at the money `Γ = 2·D_A·A`. **Gamma per unit DV01 = 2·D_A·1e-4 per bp**, with `D_A` the modified annuity duration measured from today (start + average life of the annuity, discounted, at the flat semi-annual forward yield). Script: `ann_duration()`.
- Value of convexity of one DV01 over horizon T: `½·(2·D_A·1e-4)·σ²·T = 1e-4·D_A·σ²·T` bp. **Doubling vol quadruples it** (JPM, Valuing convexity in the long end, Feb 2018). At σ = 50bp/yr, 1y: 10y 1.4bp, 10y10y 3.9, 20y10y 6.4, 30y10y 8.9, 40y10y 11.4 (QF Stack Exchange, why the ultra-long end inverts, Aug 2019; the formula at 0% yield gives 1.3 / 3.8 / 6.3 / 8.8 / 11.3, the source rounds gamma to one decimal).
- Bond/swap expected return over horizon T (yield bp, JPM 2018): `E(R) = carry + slide + 0.5·γ·σ²·T/PVBP`. Use end-of-horizon duration and convexity, bp (normal) vol and a current vol forecast: the sample matters (including the 1980s more than doubles the value; Ilmanen, Convexity Bias and the Yield Curve, Salomon, Sep 1995).
- Convexity bias: forward = expected rate + risk premium - ½·Cx·Vol². It is small below 3y and "dramatic" at long duration; it explains the concave/inverted long end. A forward or rolling-yield cheapness screen therefore makes the ultra-long end look rich mechanically, so do not call it rich without removing the bias. Detail and the Ilmanen tables are in [references/convexity-theory.md](references/convexity-theory.md).

### 2. Build the same-tenor forward strip and the pair universe
1. For each swap tenor n in {5y, 10y}, take the strip of forward par rates `f_i` (bp) at starts T_i. Universe = all pairs (short start, long start); about 10 pairs on the 5y strip (starts 10, 15, 20, 25, 30y) and 6 on the 10y strip (10, 12, 15, 20y) (internal forward-curve-vs-straddle backtest spec, v0.4, Oct 2026).
2. **Roll** `r_i = ∂f/∂T` at T_i in bp/yr: 3-point Lagrange (centred; one-sided at the ends). This is the receiver's gain per year at an unchanged spot curve. It is not a translate of the curve: a translate gives exactly zero carry to a not-yet-started par forward. Script: `roll_from_strip()`.
3. `D_i` = modified annuity duration at flat semi-annual yield `f_i`; `ΔD = D_long - D_short`. Typical: 10y10y/20y10y ΔD ~ 9.9, 10y10y/12y10y ~ 2.0.
4. Carry per unit curve DV01: `c = r_long - r_short` (bp/yr; negative = the flattener costs carry).

### 3. Breakeven vol and edge versus option vol
```
convexity P&L per yr = 1e-4 · ΔD · σ²                 (per unit curve DV01, bp)
σ_BE = sign(v)·sqrt|v|,  v = -c·1e4 / ΔD              (negative σ_BE: carry is positive, you are paid to own gamma)
edge = c + 1e-4·ΔD·σ_imp² = 1e-4·ΔD·(σ_imp² - σ_BE·|σ_BE|)  (bp/yr; > 0 = curve is the cheaper gamma; the sign-preserving square matters when c > 0)
daily BE = σ_BE/√252 if c < 0 else 0 ;  BE/RV = daily BE / 1y realised bp/day of the long leg
```
- `σ_imp` = ATMF normal vol of a **matched** swaption: 1Y expiry, 30Y tail is the default (30Y tail is matched even for belly pairs: median correlation 0.98 for 10y5y/15y5y vs 0.89 on the 10Y tail). Test 20Y/30Y tails x 1M/3M/6M/1Y expiries and report the cheapest, and how often the ranking changes (spec v0.4).
- Options-implied variant (JPM, An option by any other name, Feb 2017): integrate the aged flattener's payoff (coupons = 1y forwards so carry is included, parallel shifts) over the terminal distribution implied by ATMF and OTM 1Yx30Y swaptions; a positive expected payoff = curve is the cheaper gamma. It is highly correlated with the normal-distribution σ_BE above, which is the fast default.
- Two reading rules: **σ_BE < σ_imp or BE/RV < 1 = curve convexity is cheap** (flattener); the steepener mirror reads the other way (BE/RV > 1 means carry pays more than realised moves would cost) (Citi, Forward steepener and vol divergence, Jun 2023).
- Gamma-matched straddle (for packaging): straddle annuity-DV01 per curve DV01 = `ΔD·1e-4·σ_imp·√T/φ(0)`, `φ(0) = 0.3989` (from equating gamma: straddle gamma `2·A·φ(0)/(σ√T)` vs curve gamma `2·ΔD·A_c`; ΔD = 9.9, σ = 91, T = 1 gives 0.23). Matched-gamma identities: `Θ_opt = 1e-4·ΔD·σ²`, `Γ_opt = 2·ΔD·1e-4`.
- **Compare rates, not levels.** Carry per year against straddle theta per year at matched gamma and horizon. Comparing carry with the straddle premium overstates σ_BE by √2.
- Optional carry horizon h (f in %, c_h in bp/yr): `c_h = 100·[(f_l(T_l) - f_l(T_l - h)) - (f_s(T_s) - f_s(T_s - h))]/h`; differs from the derivative roll by ~½·f''·h per leg (small on the straight long end, visible near the 10y hump).
- What σ_BE contains: convexity bias **plus term premium**. A persistent σ_BE > σ_imp in belly pairs (10y5y/15y5y: above σ_imp on 75-85% of days over 2015-2026) is a belly carry trade, not convexity RV; the genuine mirror pairs are 10y5y/20y5y and 10y10y/15y10y (15-36% of days) (spec v0.4 and its implementation prompt).
- Cross-check against the sell-side screens before trusting the script: carry -1.75bp/yr with ΔD 9.9 gives 2.65bp/day (Citi printed 2.6); carry -0.31 with ΔD 7.3 gives 1.3bp/day (Citi printed 1.3).

### 4. Entry gates (defaults and reasons)
| Gate | Default | Reason |
|---|---|---|
| G1 long-leg vol / short-leg vol >= θ·1.02, `θ = sqrt(D_s/D_l)` | on | the flattener is long gamma only if σ_l/σ_s > θ; with a collapsing long-end vol it is not |
| G2 correlation with the straddle underlying | >= 0.75 (63d) | basis risk between curve legs and option underlying |
| G3 side · z(curve level, 252d) | >= -2.5 | do not enter at the extreme against the level. z is of `curve = later - earlier`, so a deeply inverted curve has z < 0 and a flattener (side +1) is blocked below -2.5. |
| G4 σ_imp rise over 10 days | <= 8bp | do not sell vol into a spike or buy at the top |
| G5 quality | ΔD >= 4, |σ_BE| <= 300, no stale input in the last 3 days | small ΔD makes σ_BE explode |
| G6 side · edge | > 0 | the point of the trade |
| G7 (optional) share of last 252d with sign(edge) = side | <= 0.6 | separates transient RV from structural carry |
Only G1 is re-checked on open trades (spec v0.4). Side +1 = long curve gamma (flattener), sell a gamma-matched straddle when packaging; side -1 = steepener, buy the straddle. The sides are not economic mirrors: side +1 sells the vol risk premium against curve convexity; side -1 pays it to own a concave curve's roll-down.

### 5. Choose the pair and make it a signal
- At the long end the curve-vs-1Yx30Y-straddle verdict is "curve cheaper" on ~97% of days: the raw signal is permanently on. Use **two axes**: cross-sectional rank (which pair) and per-pair time-series percentile (whether and which side), lagged one day. Traded statistic that is not saturated: `rac = carry_1y_bp / (realised vol_bp/day · √252)`, signed, continuous. The BE/RV ratio saturates at 0 whenever carry >= 0 (45-56% of 2022-23). (Internal convexity-RV handover and spec, 2026.)
- Ratio z-scores of σ_BE/σ_imp share a common σ_imp factor, so they are useless for curve selection when vol moves, and pooled IC across curves can be spurious from cross-curve mean differences.
- Prefer the very long end for sourcing gamma: shifts there are more parallel and carry is lowest (JPM, An option by any other name, Feb 2017). Prefer forward-starting pairs (25Yx5Y/20Yx5Y, 20Y/40Yx10Y) to spot-starting 30s/50s.
- Single-leg version (outright forward): convexity-adjusted carry&roll = 1y carry&roll + value of convexity, divided by 36m realised vol averaged over the points the forward rolls through (4y1y: mean of 3y1y and 4y1y vols). Values and the EUR long-forward example are in [references/screens-and-trades.md](references/screens-and-trades.md) (Nordea, EUR Rates Flash, May 2019).
- Add structural context: a 20y rich vs 10s/30s (10s20s30s fly high) from VA/ALM receiving, Formosa-type supply, pension reform. It is both why the convexity is cheap and the main risk (below).

### 6. Delta-hedge, re-weight, exit (harvesting the gamma)
- Re-hedge by resizing the **longer leg** back to DV01-neutral after each **20bp** move in its rate (USD; 25bp used for GBP 25y10y). 15-30bp is the plateau: tighter loses to costs, wider adds variance; hedge time of day matters (USD 9am had among the lowest realised vol). Practitioner variant: after each 25bp move or ~2 months, rerun notionals, typical 2-10mm change on one leg, "always at a gain relative to the initial level" (Citi, Trading long-dated convexity, May 2019; chat excerpt, Jan 2026).
- When the curve turns directional (insurance flows steepen it in rallies, flatten it in sell-offs), re-weight with the empirical beta (1.025 for 15y5y vs 20y10y) and keep hedging with that beta instead of closing (Citi, Reweighting delta-hedged flatteners, Oct 2019).
- Exits: close when carry deteriorates and BE/RV drifts up toward 1 (carry to about -2bp/yr, BE/RV 0.8) even with the curve thesis intact; take profit when a policy shock flattens the curve (BoE QE, Mar 2020); close or roll after a few years, since convexity per DV01 falls and curve vol rises as the trade ages, and the curve (vega) P&L is only realised at close. Self-liquidating variant: always shrink notionals on each re-hedge.
- Costs (one way, mid to bid/offer): initiation 0.75bp for liquid pairs (1.0 otherwise), hedge/roll 0.3-0.4bp (Citi, May 2019). Internal books broke even at 1.21 / 1.63 / 1.35bp per leg versus 0.25bp charged, so stress costs at 0 / 0.5 / 1 / 2x.
- Do not initiate when the long-end market is illiquid, even if the screen is excellent (USD 15y5y/20y10y, 26 Mar 2020: z 4.2, carry +0.11, BE 0, skipped on bid/offer).

### 7. Convexity cost in flies, steepeners and barbells
- Forward curve/fly trades carry convexity cost that scales with realised vol: `target = (current fwd - fair value) - convexity cost`. Example: 1y-forward 10s30s steepener +27bp/yr carry but 11bp/yr convexity cost at 120bp/yr realised vol; receive 1y-forward 5s10s30s belly: carry -5bp, convexity cost 8bp (Citi, Flying too high, Dec 2010).
- Duration-neutral fly with a short bullet (long wings) is long convexity: the bullet yields above the wings' line as compensation to whoever holds it, so the short-bullet side pays that carry. Convexity cost = net convexity x implied vol; pickup tracked it in 2009-10 and the link weakens under asset purchases/forward guidance (Düring, Fixed Income Trading and Risk Management, 2021).
- Barbell vs bullet: the rolling-yield curve is concave, so barbells give up yield; ~99% of barbell-bullet variance is reshaping. 1s/30s vs 10y bullet gives up 71bp (51bp after convexity) and breaks even on an 11bp flattening or a 138bp parallel move (Ilmanen, Sep 1995). Treat such trades as curve trades.
- Regime conditioning (EUR, 2010-22, 3m changes vs a 3m10y ATMF vol hedge): in a front-end sell-off regime paying 5s10s30s was the best hedge for higher vol (R² 0.48), in a rally regime receiving 10y (R² 0.39); the 5s30s relation was weak (R² 0.06 / 0.22) (Citi, European Weekly, Mar 2022).
- Receive-belly forward 5s10s30s flies and forward steepeners are short-vol proxies: size them as short gamma and expect crowding to shake out in a vol spike (Citi, US Rates Weekly, Oct 2026).

### 8. Convexity-hedging flows (sizing only)
```
10y-eq ($bn) = duration × notional ($bn) / 10;  new duration = duration + (move_bp/100)·(-convexity)
hedge need = old 10y-eq - new 10y-eq     (negative = sell duration in a sell-off; MBS convexity quoted in points, -2 = -2)
```
Direction: MBS/VA/bank hedgers amplify (buy in rallies, sell in sell-offs); callable-note dealers resist. Flows are threshold-based (~20bp net moves), arrive late and are far smaller as a share of the UST market than in 2003. Per-hedger detail, tables and footprints (swap spreads, 3y10y vega, payer skew) are in [references/convexity-hedging-flows.md](references/convexity-hedging-flows.md); mechanics in [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md).

## Worked example
**Reading the 17 Oct 2026 snapshot (internal spec v0.4).** 10y10y/20y10y: ΔD ~ 9.9; six-month curve cost ~4.2bp/DV01; straddle decay over the same six months ~4.1bp; σ_BE 92 vs σ_imp 91. Check: carry `c = -σ_BE²·ΔD/1e4 = -8.4bp/yr`, half a year = 4.2 ✓; straddle decay `½·1e-4·9.9·91² = 4.1` ✓. Edge = `-8.4 + 1e-4·9.9·91² = -0.2bp/yr`, i.e. about zero: the curve is roughly fairly priced against the 30Y-tail straddle on that date. Same date: implied vs realised on long forwards ~91 vs 61 (so the straddle is the rich side), and 10y5y/15y5y σ_BE ~129 is "mostly not convexity" (belly carry). Parity anchors: σ_BE(10y10y/20y10y) in [87, 97], σ_BE(20y5y/25y5y) < 25.

**USD 15y5y/20y10y, May-Dec 2019 (Citi).** Receive 20y10y / pay 15y5y at -11.8bp (upper end of the range since 2002), $50K DV01 ($148.8mn 15y5y vs $90.3mn 20y10y), carry -0.31bp/yr, daily BE 1.3bp vs realised 3.0 (1y) / 2.8 (3m), BE/RV 0.42. Re-hedged every 20bp; reweighted 20y10y $81.97mn -> $84mn (beta 1.025); closed 5 Dec at -12.5bp (curve only 0.7bp more inverted than entry), ~$187K at mid / +$155K net: the Oct mark was +$105K despite ~2bp steepening, so realised vol, not the curve view, paid. The screen row, our check (ΔD 7.3 -> 20.6bp/yr = 1.3bp/day) and the table of 8 pairs are in [references/screens-and-trades.md](references/screens-and-trades.md).

**GBP 15y10y/25y10y, Jan-Mar 2020 (Citi).** Entered 17 Jan at ~-11bp with positive carry (+0.52bp/yr) and BE 0 ("effectively free convexity"), hedged every 25bp, closed 26 Mar after BoE QE flattened the curve: GBP 445K net = ~115K curve move + ~330K convexity (the weekly of that date quotes +$542K, ratio 1.22: plausibly GBP vs USD, not confirmed).

**Small-number sanity check.** Darbyshire's 29Y/30Y trade (pay 29Y, receive 30Y, same delta S): net gamma `S/10,000`; at σ = 60bp/yr, `E[dP] = ½·(S/10,000)·60² = 0.18S`, i.e. 0.18bp per year of delta (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022). "A no-arbitrage hypothesis might suggest the 30Y rate be lower than the 29Y rate": that is the inversion.

**MBS flow sizing (BofA, MBS convexity hedging primer, Mar 2021).** Duration 7, $100bn, convexity -2: +25/+50/+100bp -> hedge need -5/-10/-20 $bn 10y-eq (sell). Reproduced by `mbs_hedge_need()`.

**Ilmanen 1995 anchors.** 30y zero: convexity value 253bp (~30% of its 8.46% expected return); 30y par coupon 88bp; the adjusted curve still inverts beyond 25y. A 1s/30s barbell vs 10y bullet gives up 71bp of rolling yield for a convexity pickup of only ~20bp (value of convexity 0.47% vs 0.27%; convexity 1.38 vs 0.67), so 51bp is still given up.

## Signals & interpretation
| Reading | Meaning | Action |
|---|---|---|
| BE/RV < 0.5, carry >= -1bp/yr, curve level z (since 2000) > 1 | convexity cheap and curve at an extreme | candidate flattener; confirm gates G1-G7 |
| 0.5 <= BE/RV < 0.9 | cheaper than realised | acceptable if liquid (USD 0.46-1.08; GBP 0.00-0.89; EUR 0.60-1.48; CAD 0.45-1.82; JPY 0.76-1.50 in Jan 2020) |
| BE/RV ~ 1 or carry < -2bp/yr after entry | fair / carry eroded | trim or close (Citi: carry -2, BE/RV 0.8) |
| BE/RV = 0 (carry >= 0) | "free convexity", but signal saturated | rank on rac and time-series percentile instead |
| σ_BE > σ_imp, edge < 0 | curve convexity dearer than the straddle | steepener side only if G6/G7 pass; belly pairs usually term premium |
| Curve level vs vol: curve(10y10y/20y10y) = -0.5·nvol(2y10y) + 19.0, R² 0.5 (2010-19); 3y10y vol = -0.99·(15y15y-10y10y) + 48.3, R² 0.90 (3y, Oct 2026) | curve and vol co-move inversely; residual = signal | **re-fit, never reuse the coefficients**; fading rule: falling vol should steepen the curve |
| Realised long-end vol / short-end vol below θ | the package is no longer long gamma | exit (G1) |

Thresholds in this table are working defaults read off the Citi/JPM screens above, not published rules; recalibrate on your own history. Confirmation checks: bucket P&L by size of the underlying move: "a convex payoff must show a smile, not a ramp"; daily convexity is not identifiable, read it at trade level; report incremental R² because carry/slope and level/convexity are collinear at trade horizon; report deflated Sharpe, Sharpe ex-direction, and P&L at 0 / 0.5 / 1 / 2x costs. Sharpe of 0.16-0.35 per pair is normal: the book is structurally long vol, which diversifies carry/short-gamma books.

## Pitfalls
- **Structural receiving is the thesis and the risk.** VA (15-25y), ALM/LDI and pension reform keep the 20y+ sector rich, so flatteners can lose in risk-off steepening (stock/curve correlation ~ -23%, but monthly P&L vs equities ~0). Forced ALM receiving in a rally can send the long end lower, the main risk to paid long-end positions.
- **Not clean option convexity.** No bounded downside, hard to hold to maturity, curve vol rises as the package ages, vega/curve P&L realised only at close. The analysis assumes roughly parallel moves: if the curve itself is volatile, slope P&L dominates (10s30s is less clean than 25y/30y because the 10s move more than the 30s).
- **Do not read inversion as mispricing.** Ultra-long "rich vs model" is usually convexity, not value; LDI/insurer regulation is a second driver. Do not price long-end convexity off symmetric-yield assumptions (expected return explodes with maturity).
- **Measurement.** Measure carry by repricing the aged package (correlation +0.991 with the published 1y carry), never from a running carry-and-roll field (-0.136) and never by translating the curve. Measure convexity by repricing on shifted curves, not analytic greeks. Mark aged tickets at their live start, not off constant-maturity series; hedge both legs on one grid ("most backtests of this trade go wrong here").
- **Carry vs premium.** Compare per-year rates at matched gamma (see Method 3), not carry with premium.
- **σ_BE accuracy.** Validate on a Ho-Lee curve (convexity bias only, no term premium): recovered σ_BE must be within 5% of true. A 5% bias is ~4.5 vol, as large as the whole edge on fairly priced pairs. Record the recovery factor next to every σ_BE.
- **Overlapping cohorts** (1y holds, monthly entries) inflate Sharpe: 76 cohorts ~ 7.6 independent years. Pooled long-end signals that are "on" 97% of days are not a timing rule.
- **First-order Sharpe on forward spreads overstates**; include gamma and a smile (a smile raises the value of gamma). Too few strikes in a swaption replication overestimates gamma value (Darbyshire ch.23).
- **Liquidity.** Multi-leg long-end bid/offer can blow out (10y swap ~0.6bp mid to bid/offer in Mar 2020); peak MTM can be unrealisable; wait for ~3bp.
- **Cheap for a reason.** Long-dated forward vol can be cheap because of callable supply, ELB convergence or reduced mortgage vega demand; do not buy on z-score alone. Check whether the flow story is already priced; trade the second-order leg if the obvious one is.
- **Sources disagree.** Citi printed carry -0.31 and -0.44 for the same trade; GBP P&L 445K net vs +$542K in the weekly (ratio 1.22: plausibly GBP vs USD, not confirmed); JPM's -100.6bp carry for 30s/50s was not reproduced (+1.36bp/yr). Prefer your own repricing.
- **Regime.** Vol/rate beta of long-dated vol flips (10y10y vol/rate beta positive for most of post-Covid, flipped in 2025). Fit EUR models pre/post the negative-rate regime separately. Event timing: do not initiate steepeners before a known hawkish-skip risk (FOMC).
- **Market coverage.** Source material covers USD, EUR, GBP, JPY, CAD; AUD, NZD, CHF, SEK, NOK have no long-end convexity evidence in the sources. The method applies only where a 20y+ forward strip and a long-tail swaption vol exist; check forward-curve depth and liquidity first.

### G10 notes
- **USD**: deepest evidence. VA ~20y, Formosa-type callables (30nc5/40nc5), MBS hedging (3y10y vega, intermediate swap spreads), bank duration gaps. Spread convention: US swap spread = swap - Treasury yield. Hedge band 20bp.
- **EUR**: convexity expensive versus USD in 2018-20 (BE/RV 0.60-1.48; 30s/50s needed a higher breakeven vol than swaptions); 12m roll positive to ~15y, negative beyond (min ~-4.6bp around 21-22y); negative forwards beyond ~41y; pension reform (NL/DK) imposes short convexity; ECB QE and the 31y limit distort the ultra-long EGBs. Paying the 5y5y-15y5y-25y5y fly was a top expected-Sharpe convexity-harvest trade (June 2022; ER +34bp, risk 50bp).
- **GBP**: cheapest flatteners in 2019-20 (BE/RV 0.00-0.89, often positive carry); LDI/pension flows dominate 30y+ and are pro-cyclical; 20y rich on ALM receiving; 30s50s +16.8bp (Jul 2026) is the least inverted ultra despite the highest implied vols.
- **JPY**: convexity generally expensive; realised long-forward vol lowest (2.4-3.1bp/day); forward vols held low by YCC; life-insurer target buying caps long yields.
- **CAD**: 15y5y/20y5y the most expensive convexity on BE/RV (2.00, Sep 2019). **AUD, NZD, CHF, SEK, NOK**: see Pitfalls.

## Output
Return a ranked table per market and the trade card.
1. Screen table, one row per pair: `market | short start | long start | tenor | curve_bp | z 1y / 3y / since-2000 | D_s, D_l, ΔD | carry_bp_yr | σ_BE | σ_imp (expiry x tail) | edge_bp_yr | daily BE | RV (63d, 252d) | BE/RV | rac | gates G1-G7 pass/fail | share of last 252d with sign(edge)=side`. Flag the top 3 per metric, "most attractive but not necessarily recommended".
2. For each shortlisted trade: structure, DV01-neutral notionals, hedge band and rule, re-weight beta, costs assumed (0.75/0.3-0.4bp) and P&L at 0/0.5/1/2x costs, expected 1y carry and convexity P&L split, scenario P&L at +-50/100/200bp parallel and a bull-flattening / bear-steepening case, exit rules (carry, BE/RV, age).
3. Record σ_BE recovery factor on the Ho-Lee test and the data snaps used; state which of carry, BE/RV, rac drove the ranking.
4. Hand off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) with the vetting items in [rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Scripts
- [`scripts/convexity_screen.py`](scripts/convexity_screen.py): annuity duration, 3-point roll, σ_BE, edge, BE/RV, value of convexity, full-repricing flat-curve package P&L, MBS hedge need, and a pair table from `curve_par` (+ optional `vol_surface`): `python scripts/convexity_screen.py --curve curve_par.csv --vol vol_surface.csv --date YYYY-MM-DD --curve-id <id> --tenor 5Y [--snap <snap> --index-id <index>]` (the flags are needed when a date has several snaps or indices; the script stops rather than pick one). `--selftest` checks annuity duration at 0% (15.25/25.25), roll on a quadratic, the published anchors (σ_BE 92, BE 2.6bp/day, MBS -5/-20), repricing against `1e-4·ΔD·s²`, and a Ho-Lee curve built from discount factors (σ_BE within 5%).

## Related skills
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): builds the forward-start strips and roll-adjusted forwards this skill consumes
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): payer/receiver skew and tail hedges (30y/10yx10y flattener as tail hedge)
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores, percentiles and cross-sectional ranking for the screen
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): parallel and bull-flattening/bear-steepening scenario P&L
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): DV01-neutral vs beta-weighted spreads and directionality
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weights; convexity cost enters their fair value
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 definitions, gamma and cross-gamma, hedge mapping
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry/roll and carry-per-vol ratios behind BE/RV
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): swaption vol grids, implied vs realised, listed vs OTC vol
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): gamma/theta/vega P&L and delta-hedging mechanics
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable/Formosa issuance converted to vega supply
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): curve options, CMS spreads, implied correlation
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): MBS/TBA mechanics and hedger flows
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension/LDI/insurer/bank demand behind long-end richness
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures-vs-FRA convexity (short end)
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): cost and liquidity stress for hedged packages
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): overlapping cohorts, deflated Sharpe
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used here
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-based conditional curve trades.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): term-structure models and term premium.

## References
- J.P. Morgan - An option by any other name: Sourcing cheap convexity in the long end of the curve (North America Fixed Income Strategy, 3 Feb 2017): curve-as-gamma, expected-payoff and curve-implied vol, backtest, variance decomposition
- J.P. Morgan - Valuing convexity in the long end of the yield curve: a global perspective (Global Fixed Income Strategy, 9 Feb 2018): expected-return formula, cross-market convexity values, gilt regression
- Citi Research - Trading long-dated convexity (US Rates Vol Lab, 9 May 2019): daily breakeven and BE/RV, delta-hedge band, costs, backtest, why convexity is cheap
- Citi Research - Reweighting delta-hedged 15y5y/20y10y flatteners (16 Oct 2019) and Taking profits on delta-hedged 15y5y/20y10y flatteners (5 Dec 2019): beta reweighting, exit rule, USD/GBP screen
- Citi Research - In search of cheap vol (17 Jan 2020), Liquidity, vega, and convexity (30 Mar 2020, partial), Taking profits on GBP 15y10y/25y10y flatteners (26 Mar 2020): cross-market BE/RV, GBP trade and P&L split
- Citi Research - Deal or no deal: Rates implications (US Rates Weekly, 10 May 2019), Buying vol for less (Rates Vol Lab, 25 Sep 2019), Eat, pay, spend (US Rates Weekly, 27 Mar 2020), Taking profits on long end butterfly trade (15 Jun 2020): trade entry, five-currency screen, GBP P&L, long-end fly
- Citi Research - Forward steepener and vol divergence (Rates Vol Lab, 12 Jun 2023): steepener-as-short-vol reading
- Citi Research - Fading vega dislocations (Rates Vol Lab, 5 Oct 2026, partial), Pension plan for 20s? and OAT of the blue (US Rates Weekly, 9 and 2 Oct 2026, the latter partial): vol-vs-forward-curve regression, 3y10y vs 10y10y/15y15y package, forward 5s10s30s as short vol
- Citi Research - A narrative shift looms (European Rates Weekly, 17 Mar 2022): regime-conditional curve-vs-vol regressions
- Citi Research - Flying too high: receive belly of 1-year forward 5s10s30s fly (20 Dec 2010): convexity cost deduction
- Citi - A holistic approach to convexity across fixed income (internal presentation, Jun 2022, partial): gamma maths, expected-Sharpe screen
- J.P. Morgan - Dynamic hedgers are long, banks are short (13 Sep 2019); Markets struggle to feed the convexity beast (28 Feb 2020): hedger models, 30Y/10Yx10Y flattener
- J.P. Morgan - For cheap gamma, look to the long end (23 Aug 2019); Renewed Formosa supply continues to flatten the long end (21 Feb 2020); A comprehensive look at convexity hedging in interest rates (29 Mar 2019); Is bank convexity hedging lying in wait? (31 May 2019); The return of convexity hedging (31 Jan 2020): trades, swap-curve implied vol, hedger models
- Barclays Research - Global Rates Weekly: The urgency question (2 Oct 2026); Interest Rate Derivatives: Swap spreads: The Bright Spot in US rates (30 Sep 2026): self-limiting convexity flows, MBS hedging per 25bp
- BofA Global Research - Primer: MBS convexity hedging and TSY market (US Rates Viewpoint, 18 Mar 2021): hedge-need formula, hedger taxonomy, event tables
- Salomon Brothers (Antti Ilmanen) - Understanding the Yield Curve, Part 5: Convexity Bias and the Yield Curve (Sep 1995); Part 6 (Nov 1995); Parts 1-2 (May-Jun 1995); Part 7 (Feb 1996, with R. Iwanowski): value of convexity, convexity-adjusted returns, barbell-bullet, curvature vs vol
- Bruce Tuckman and Angel Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): closed forms, century bond example, MBS hedging mechanics
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022): gamma rules of thumb, mean vs mode, second-order Sharpe for forward spreads
- Alexander Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): fly convexity bias, ultra-long inversion as model artefact, structural short convexity
- Doug Huggins and Christian Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): symmetric-yield convexity misuse, long-zero limits
- Quantitative Finance Stack Exchange - Why does the ultra long-end of a yield curve invert? (Aug 2019): zero-coupon gamma, forward gamma values, LDI flows
- Nordea Markets - EUR Rates Flash (23 May 2019; 24 Jan 2020; 5 Feb 2020) and The quiet game (12 Aug 2025): EUR value-of-convexity monitor, vol-curve rule, 20y5y/25y5y
- Citi Markets (hedge-fund rates sales, not research) - EUR 30s50s steepener vs 5y10y vol (27 Jul 2026): cross-currency 30s50s, vol-hedged steepener
- Nordea Markets - Bonds & bold (5 Nov 2021, partial): long-expiry straddle backtest
- Salomon Brothers - Understanding Treasury Bond Futures: Questions and Answers (Oct 1990): negative futures convexity
- Credit Suisse - US Treasuries Futures Focus: New Ultra Long Contract (28 Sep 2009): ultra futures vs swap convexity
- Credit Suisse (Harley Bassman) - The Convexity Vortex (6 Mar 2013); Convexity Maven (Harley Bassman) - It's Never Different This Time (29 Jan 2018); Bank of America Merrill Lynch (Harley Bassman) - The Largest Volatility Sale Ever (23 Mar 2010): MBS strike clustering, low-vol convexity, MBS as vol buyer
- Internal research notes - Forward curve vs straddle backtest spec (v0.4, Oct 2026) and convexity-RV replication handover (2026): sigma_BE definition, gates, measurement rules, replication results
- Rates traders' chat excerpt - 10y10y vs 20y10y as strikeless vol (21 Jan 2026): delta-hedge resizing procedure; its "long vega short gamma" claim for a linear package is unverified here, so compute DV01, gamma and forward vol before believing it
- Kopprasch, R.W. - Understanding Duration and Volatility (Salomon Brothers, Sep 1985): barbell vs bullet convexity
