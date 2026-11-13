---
name: curve-forward-grid-rv
description: 'Forward-space relative value on G10 swap/OIS (and govt) curves. Builds the non-overlapping 1y-forward strip and the forward grid (1y1y, 2y1y, 5y5y, 10y10y, 15y5y, 20y10y, 10y20y), compares forward vs spot, finds kinks and humps with cross-sectional fair-value residuals and a value-vs-carry frontier, computes roll-adjusted (aged) forwards, carry/roll of forward-starting structures, forward flatteners/steepeners/flies, and a breakeven-vol cross-check. Use when asked about forwards, 5y5y, 1y1y, xF1Y, forward-starting swap, forward curve, forward steepener/flattener/fly, 10y10y/20y10y, 15y5y/20y10y, aged or 1y-forward curve, rolling yield, top of the forward curve, hump or kink in the strip, forward-implied neutral or terminal rate, forward vs spot, roll-down of a forward, fwd 2s10s. Breakeven vol and convexity valuation: vol-convexity-and-long-end; spot-tenor two-leg trades: curve-steepeners-flatteners.'
---

# Forward-grid relative value

Spot and par rates are averages of the same short-rate path, so comparing 9y with 10y double-counts 0-9y. Forward space
splits the curve into non-overlapping building blocks (1y1y, 2y1y, ... 10y10y), so a cheap or rich sector shows up where
it really is, hedges are exact (the forward is a difference of two benchmark swaps), and "what does the curve earn if
nothing happens" (roll, aged forward) is explicit. A forward is a breakeven, not a forecast: it pays only when you hold a
view that differs from it, or when carry/roll/convexity/structural flow (ALM, insurers, supply) pays you for waiting.

## When to use
- "Is 5y5y / 10y10y / 2y1y cheap?", "where is the kink in the forward curve?", "what does the 1y-forward curve look like?"
- Any structure on forward-starting swaps: 1y1y/2y1y, 5y5y/10y5y, 10y10y/20y10y, 15y5y/20y10y, forward 2s10s, forward flies.
- Carry and roll of a curve trade expressed forward; "forward vs spot" choice for a duration or curve view.
- Long-end convexity: why the very-long forward curve is inverted, whether a forward flattener is cheap gamma vs swaptions.
- Reading policy expectations from the forward curve (forward-implied neutral, 5y5y as terminal rate, 1y1y vs 5y5y flat).
- Screening a G10 forward grid for the best carry / entry / trend combination.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par OIS/RFR swap rates, spot-start, tenors 1y-30y (40y, 50y if quoted) | `curve_par` (`start=0D`) | daily, same `snap`, >= 3y; since 2000 for long-end z | percent. Fixed-leg convention from `swap_conventions` |
| Directly quoted forward-start swaps (5Y5Y, 10Y10Y, 1Y1Y) | `curve_par` (`start`=tenor) | daily | use as a check on the bootstrapped forward |
| Built discount factors (preferred for trade levels) | `curve_zero` | daily nodes | exact forwards in the market's own day count and interpolation |
| Convention per curve (fixed frequency, day count, spot lag) | `swap_conventions`, `rate_indices` | static | spot lag differs (GBP T+0, AUD T+1, most others T+2; verify per curve); forward start is measured from the spot date |
| Policy meeting dates | `cb_meetings` | schedule | marks the "meeting zone" (forward start < 2y) |
| ATMF normal vol, e.g. 1Y expiry x 30Y tail, and long-expiry grid | `vol_surface` (`nvol_bp`) | daily | for sigma_imp vs sigma_BE |
| Futures strips for the front end | `stir_quotes` | daily | only after convexity adjustment (see [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md)) |
| Inflation swaps (for real forwards) | `infl_swaps` | daily | 5y5y real = nominal 5y5y - inflation 5y5y |

If an input is missing, ask for it or hand off to the data adapter. Never invent values. Table definitions:
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Conventions (state them in every output)
- `AyBy` = swap of tenor B years starting in A years; `xF1Y` = the 1y rate x years forward (1F1Y = 1y1y).
  `5y5y` is the 5y rate 5y forward; `10y10y` ends in 20y.
- Rates in percent, spreads/residuals/rolls in bp. Normal (bp) vol only.
- Forward-curve spread **S/L = rate(L) - rate(S)**, L = later-starting leg (2s10s style: later minus earlier). Negative = inverted.
- **Flattener = receive L, pay S**, DV01-neutral (profits when L-S falls). Steepener is the reverse. A fly is
  `2*mid - wing1 - wing2`: positive = belly high = belly cheap; "receive the belly" profits when it falls.
- Receive fixed = long duration = positive DV01. **Receiver roll (bp) = R(A,B) - R(A-h,B)**, positive when the strip slopes
  up into the start date, i.e. a receiver earns if the curve stays unchanged.
- **fwd_minus_spot = R(A,B) - R(0,B)**: the change in the B-year rate the curve implies over A years.
- Swap spreads are not used here; for sign conventions see [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md).

## Method

### 1. Build forwards exactly (never from rounded quotes)
Use discount factors `DF(t)` from the market curve ([fi-curve-construction](../fi-curve-construction/SKILL.md)); for
screening, bootstrap annual DFs from par rates `p_i`:
```
DF_i      = (1 - p_i * sum_{j<i} DF_j) / (1 + p_i)         (annual fixed leg, par in decimals)
f(a, a+1) = DF(a)/DF(a+1) - 1                              1y simple forward, non-overlapping
R(A,B)    = (DF(A) - DF(A+B)) / sum_{i=1..B} DF(A+i)       forward par swap rate (annual leg)
zero form : f(t1,t2) = [(1+z2)^t2 / (1+z1)^t1]^(1/(t2-t1)) - 1
annuity identity: R(0,i+j)*A(0,i+j) = R(0,i)*A(0,i) + R(i,j)*A(i,j)      (e.g. 10y = 5y + 5y5y)
```
(Salomon Brothers, Understanding the Yield Curve Part 6, Nov 1995; Duering, Fixed Income Trading and Risk Management, 2021;
Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022.) Quick approximation
`f(n-1,n) ~ s_n + (n-1)(s_n - s_{n-1})` shows the forward curve magnifies slope changes of the spot curve (Salomon Brothers,
Understanding the Yield Curve Part 1, May 1995). Annual-leg screening is good to about 1bp; semiannual (CAD, AUD),
quarterly bank-bill markets and day-count differences need the real curve for trade levels. Pin the forward-start schedule
(swaps-aligned vs swaption-expiry) when comparing levels with another source: see
[forward conventions and curve artefacts](references/forward-conventions-and-curve-artefacts.md).

### 2. Read a forward correctly
Three equivalent readings: arbitrage price; **breakeven** future spot rate (return of the long bond equals financing); and
**rolling yield** (return if the curve is unchanged). "Forwards imply rising rates" is the same statement as "spot curve is
upward sloping" and tells you nothing about expectations (Salomon Brothers, Understanding the Yield Curve Part 6, Nov 1995).
```
f = E[short rate path] + risk premium - 0.5 * Cx * sigma^2         expectations + premium - convexity
```
(Tuckman & Serrat, Fixed Income Securities 4th ed., 2022, Ch.8). The three cannot be separated from forwards alone.
Empirical sanity check (monthly overlapping data, Jan 1968-Dec 1995): the 3m-ahead change in the constant-maturity rate implied by
forwards averaged +0.65% for the 3m rate falling to +0.07% for the 6y, the realised mean change was about 0, and the implied-vs-realised
correlation was -0.04 to -0.13, insignificant (Salomon Brothers, Understanding the Yield Curve Part 7, Feb 1996). So: do not trade
"the forward will be realised"; trade carry, roll, convexity and structural distortions, and subtract a risk-premium estimate before
calling a front-end forward a hike forecast. Forwards already embed the curve's mean reversion, so do not pay for it twice: look for risk
that points the "wrong way" in forward space, e.g. 2y and 10y swung widely while 5y5y stayed in a narrow band (Credit Suisse, Bassman,
Building a Better Volatility Mousetrap, 6 Sep 2012). Cheap-sector trade: a high forward between years a and b is cheap, so buy the
bond maturing at b against the one maturing at a, ideally level- and slope-neutral with a longer wing (Ilmanen, Part 1; in Jan 1990 the
cheap 12y sector richened over the next 3 months).

### 3. The grid (screen)
Per currency, compute for each point and for each forward-curve pair/fly:
`level`, `fwd_minus_spot`, **z-scores backward-looking, today excluded** (3y window minimum 1y, and since-2000 for the long
end), 1y carry/roll, realised vol (bp/day, 1y), and the headline ratios:

| Metric | Definition | Use |
|---|---|---|
| Ex-ante Sharpe | (3m implied carry + roll) / (3m realised vol, annualised) | ranking by what time alone pays |
| Carry/R | Sharpe / (1 + abs(R)), R = correlation of structure changes with outright rates | penalises disguised duration |
| Entry | z vs 5y mean/std | cheap or rich vs own history |
| Trend | vol-adjusted 2-week change | avoid fading a move in progress |
| BE/RV | daily breakeven vol / 1y realised daily vol (section 6) | convexity cost; flatteners want low, steepeners high |

(Goldman Sachs, Global Rates Best Trade Report, 30 Sep 2026; Citi, Taking profits 15y5y/20y10y, 5 Dec 2019). Standard
universe: outrights 1y1y, 2y1y, 3y1y, 5y2y, 7y3y, 5y5y, 10y5y, 15y5y, 20y5y, 25y5y, 10y10y, 30y10y, 40y10y; forward curves
between neighbours (5y5y/10y5y, 10y5y/15y5y, 15y5y/20y5y, 10y10y/20y10y, 20y5y/25y5y, 30y10y/40y10y); forward-starting
spot-curve templates (1y/2y/3y forward 2s5s, 2s10s, 5s30s); forward flies (5y5y/10y5y/15y5y, 10y10y/20y10y/30y10y,
20y10y/30y10y/40y10y). SEK and NOK curves are liquid only to about 10y: use 1y-3y starts and 2y-tenor flies
(4y2y/6y2y/8y2y, 1y2y/3y2y/5y2y). Rank within the screen only; scores are relative; the source quotes signs from the payer's perspective, so flip carry and trend for a
receiver. Rebuild any screen package with explicit
DV01-neutral (or PCA) weights before trading. Run [`scripts/forward_grid.py`](scripts/forward_grid.py) for strip, grid and
pair tables.

### 4. Fair value of the strip: cross-sectional residual, then value vs carry
1. Take the 1y-forward strip `f(k)`, k = 1..15, 20, 25, 30 (abscissa = start + 0.5). Fit **per day** a smooth curve across the
   strip: least-squares cubic B-spline with interior knots near 3, 7, 15 (dense front, sparse back), >= 8 points, check the
   Schoenberg-Whitney condition. `resid_bp = market - fit`; positive = forward high = **cheap to receive** (fade by receiving).
2. Value vs carry: regress `resid_bp` on the 3m receiver roll (bp/3m) across starts 2-15 each day. A negative slope means
   cheap tenors cost carry; trade tenors **off** the frontier, not along it (resid on roll, not roll on resid). In EUR (Jan 2020):
   `resid = -1.2716*roll + 16.425`, R^2 = 0.927 over 2F1Y-15F1Y (ING labels the residual "PC1 residual"; an in-house replication
   matched it only with the cross-sectional fit used here); pay tenors in the bottom-left quadrant (negative residual, negative receiver roll), receive
   tenors in the top-right; 20F1Y+ and 1F1Y sit off the line and are hard to value (ING, Deconstructing the EUR yield curve,
   15 Jan 2020).
3. **Months-to-breakeven = |residual| / (monthly adverse carry)**. Compare it with the expected reversion horizon (about
   3 months in the EUR study). Pay 1F1Y-10F1Y: 14bp too flat but rolls -15.5bp/3m, breakeven only if it closes in about
   2.6 months, so skip it; pay the direction-neutral 1F1Y-6F1Y-9F1Y fly (belly 23bp rich, carry -2bp/3m, carry erases the
   gain only after about 35-36 months) (ING, 15 Jan 2020).
4. A time-series PCA residual is **not** the same fair value: in in-house replication a walk-forward PC1 residual failed to reproduce the
   frontier above (R^2 0.03 vs 0.93). Use the cross-section as the fair value and the PCA residual as a second opinion;
   require **sign agreement** and |resid| >= 0.5bp before acting. Count non-overlapping dislocation episodes.
5. Zones. **Meeting zone** (forward start < 2y): residual is the central-bank calendar: never fade it statistically; use
   [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md). **Clean zone** (2y-20y): RV
   proper. **Convexity zone** (start >= 20y): level contains convexity and ALM flow; convexity-adjust before comparing (a Ho-Lee style term `0.5*sigma^2*t1*t2`, sigma in decimal per year, grows with both start and end)
   and treat as harvest/vol trades (section 6), not fair-value fades.

### 5. Carry, roll and the aged forward
- **Carry** = payments known today; **roll** = value from time passing with the curve frozen; **forward-starting swaps have no
  carry** (no float payment is known), only roll that shortens the forward period: 6M5Y -> 0D5Y, 1Y5Y -> 6M5Y (Nordea,
  Carry & Roll, 12 Jul 2013). Roll of a forward = `R(A,B) - R(A-h,B)` for horizon h < A.
- For a DV01-neutral spread, leg rolls in bp add without scaling: **flattener carry = roll(L) - roll(S)**.
- Spot trade identities for a long 5y financed at the 1y rate, 1y horizon, in yield bp: rolldown = `5y - 4y` (yield fall the roll
  delivers); carry breakeven = `5y - 1y4y` (total rally needed to break even, positive = adverse, e.g. +22bp in example B);
  needed after the roll = `4y - 1y4y` (the source calls this carry+roll; it is the shortfall, so the long's P&L-signed carry+roll is
  `1y4y - 4y`). 3m horizon: `5y - 4.75y`, `5y - 3m4.75y`, `4.75y - 3m4.75y` (BofA, Rates basics: spot vs
  forward, 15 Feb 2024). Never use carry approximation `SR(6m,4.5y) - SR(0,5y)` beyond the fixing period.
- **State which "unchanged" scenario**: (a) realised forwards (the 6m rate x years forward becomes spot) earns zero excess;
  (b) unchanged term structure (an n-year zero earns the 1y forward). Under (a) carry/roll P&L accrues only when forwards
  are *not* realised, so a positive-roll receiver is economically short vol / long theta (Tuckman & Serrat 2022, Ch.3;
  Darbyshire 2022, ch.23).
- **Aged forward series**: re-compute each trade's level with start shortened by 1y ("1y aged") and plot it against the
  trade history; the gap is the roll the market pays or charges; frequency that roll alone would have paid is the empirical
  carry hit rate (Nordea, EUR Rates Flash, 24 Jan 2020; Goldman Sachs desk, 30 Sep 2026).
- **Top of the forward curve**: plot 1y forwards by start (0-50y) with their 1y roll. The forward peak (EUR: around 14-15y start,
  Jan-Feb 2020) separates positive roll (receive before the peak) from negative roll (after it). Systematic version: receive
  the forward just before the peak, pay the one just after (Nordea, 24 Jan 2020). It is a carry trade: it is hit when
  forced ALM receiving drives the long end lower (see Pitfalls).
- Spot vs forward expression: a long-duration view with term financing too high -> hold spot and roll overnight; otherwise
  trade the forward (carry locked, breakeven known). Swap analogue: 1y SOFR too high -> receive spot; too low -> receive 1y4y
  (BofA, 15 Feb 2024). UST term repo rarely extends beyond about 3 months, so long forwards are built in swaps.

### 6. Convexity regime: long forward curves as strikeless vol
For starts >= 10-15y the forward curve is inverted by convexity, so a DV01-neutral flattener (receive later, pay earlier)
is **long gamma, negative or small carry**; the spread behaves like implied vol (Citi, Trading long-dated convexity, 9 May
2019). Zero-coupon maths: convexity per unit DV01 grows linearly with T.
```
gamma per PV01 of AyBy  ~ 2 * GD * 1e-4 per bp,   GD(A,B) = A + (B + 1)/2        (mean payment year j)
convexity value (bp)    = 1e-4 * dGD * sigma_yr^2 * tau          dGD = GD(L) - GD(S), sigma in bp/yr, tau in years
carry cost (bp/yr)      = max(0, -(roll(L) - roll(S)))            flattener, per bp of DV01
sigma_BE (bp/yr)        = sqrt(carry_cost / (1e-4 * dGD))         0 if carry >= 0: "free convexity"
daily breakeven (bp/d)  = sigma_BE / sqrt(252);   BE/RV = daily breakeven / 1y realised daily vol of the later leg
```
Convexity bias is the same effect in outright forwards: a 30y zero's 5.93% rolling yield plus 2.53% convexity value was an 8.46%
expected return (1 Sep 1995), and the convexity-adjusted curve still inverted beyond 25y (Salomon Brothers, Ilmanen, Understanding the
Yield Curve Part 5, Sep 1995); use normal vol. Check against a source: gamma per 1000 PV01 of 10Y, 10Y10Y, 20Y10Y, 30Y10Y, 40Y10Y = 1.1, 3.1, 5.1, 7.1, 9.1; at 50bp/yr
vol the 1y convexity value is 1.4, 3.9, 6.4, 8.9, 11.4bp of PV01 (QF Stack Exchange, Why does the ultra long-end invert?,
2019); doubling vol quadruples it (JPM, Valuing convexity in the long end, 9 Feb 2018). The script reproduces these. Bump-and-reprice
of a receiver on a flat curve gives exactly `(2A + B)*1e-4` per bp (1.0, 3.0, 5.0, 7.0, 9.0 per 1000 PV01); the `+1` is a
payment-timing convention that cancels in dGD. It is a parallel-shift rule of thumb: size real trades with full repricing.
- **Flattener selection**: lowest BE/RV (cheap embedded convexity), non-negative carry, high since-2000 z (inverted vs
  history). BE/RV 0.4-0.8 = attractive, about 1 = fairly priced, > 1 = expensive. Exit when carry deteriorates and BE/RV rises
  toward 0.8-1.0 even if the curve thesis is intact (Citi, Taking profits, 5 Dec 2019).
- **Steepener side** (short convexity, positive carry): require BE/RV meaningfully > 1 and a low since-2000 z; the best-carry
  steepeners have the worst entry (Citi, Forward steepener and vol divergence, 12 Jun 2023). Long-end forward steepeners are
  short payer skew on belly rates and lose in volatile sell-offs (Citi, Higher yields are here to stay, 24 Sep 2026).
- **Versus options**: curve-implied vol = normal vol at which the expected aged-flattener payoff is zero; if below
  ATMF swaption vol the curve is the cheaper gamma. Regression: `10y10y/20y10y (bp) = -0.5 * (2y10y normal vol) + 19.0`,
  R^2 0.5, 2010-2019 (Citi, Trading long-dated convexity, 9 May 2019). Systematic package: flattener when `sigma_BE <
  sigma_imp`, add a gamma-matched sold ATM straddle; steepener plus bought straddle when `sigma_BE > sigma_imp`. Compare
  rates (carry per year vs theta per year) at matched gamma and horizon, **not** carry vs premium, or sigma_BE looks sqrt(2)
  too high (Fwd curve vs straddle backtest spec, Oct 2026).
- Filters: dGD >= 4 (small dGD makes sigma_BE explode), |sigma_BE| <= 300, no stale input in the last 3 days, strictly
  backward z. Persistent sigma_BE > sigma_imp (75-85% of days, e.g. 10y5y/15y5y hump near 10y) is term premium / belly
  carry, not convexity; transient (15-36% of days, e.g. 10y5y/20y5y) is genuine RV (same spec). Detail and grids:
  [long-end convexity flatteners](references/long-end-convexity-flatteners.md).
- **Hedging**: re-neutralise the longer leg to DV01-neutral every 20bp (USD) to 25bp (GBP), band 15-30bp; tighter loses to
  costs, wider adds P&L variance. Roll or close after about a year or when convexity per DV01 has decayed. If flows make
  the curve directional, scale the later leg by the empirical beta (1.025 for 15y5y vs 20y10y) instead of closing (Citi,
  Reweighting 15y5y/20y10y, 16 Oct 2019).

### 7. Forward-space PCA and hedge weights
- PCA on non-overlapping forwards (spot 1y, 1y1y, 2y1y ... 9y1y, 10y2y, 12y3y, 15y5y, 20y5y, 25y5y, 30y10y, 40y10y in EUR)
  with a 1y rolling window: PC1 > 80%, PC2 10.1%, PC3 4.3%; use <= 3 PCs. Residual = data - reconstruction; positive = high
  = cheap; a large residual flanked by opposite signs suggests a fly; exit when the residual crosses zero (Credit Suisse,
  PCA Unleashed, 24 Oct 2012). Forwards give sharper residuals than spot (a cheap 5y spot hides a rich 2y) but cost more legs
  (Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024). Full PCA method:
  [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md).
- PC1-only hedge `gamma = u1x/u1y` explodes where level loadings approach zero (30y10y vs 1y1y: 7.88); two-PC hedge
  `gamma = (u1x u1y l1^2 + u2x u2y l2^2)/(u1y^2 l1^2 + u2y^2 l2^2)`. Residuals can be policy-driven dislocations (Dutch
  pension reform in 2012), not trades: track the residual's history (today, 3d, 1w, 1m).
- **Model alternative (Gauss+)**: fit a three-factor Gaussian cascade (short rate pinned to the policy target) each day so that the 1y forwards 2y and 10y ahead are matched
  exactly, then read the fitting error of the other 1y forwards (e.g. 9y) as the signal (5d/40d MA crossover; the 9y-minus-5y
  signal difference was strongly mean reverting). Residuals persist: require convergence momentum and pool trades to neutralise
  factor exposure (Tuckman & Serrat 2022, Ch.9; see [curve-term-structure-models](../curve-term-structure-models/SKILL.md)).
- **Par-risk leverage**: a forward's par-risk is leveraged by roughly (tenor of the par instrument)/(tenor of the forward):
  30Y5Y is about 10x. Size RV in forward risk and hedge with the two bracketing par swaps: 5Y5Y = 2.109 x 10Y - 1.106 x 5Y
  on one solved curve (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, Ex.10.5, 11.1).
  Jacobians: [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md).

### 8. Forward curve vs policy anchors
- **Neutral from the curve**: record the forward policy rate where 1y1y crosses 5y5y; that is the market's real-time nominal
  neutral (US about 4.10% in mid-2026) (JWS Macro, Central Casting #6.1, 21 Jun 2026). Overlay 2s10s forwards vs neutral-rate
  templates; forwards implying a neutral far above the house view mean the curve is too steep for a bull-steepening
  (BofA, Understanding the yield curve dynamic, 23 Jul 2025).
- **Policy-adjusted 1Yx1Y/5Yx5Y**: regress the curve on the 1Yx1Y level (1y window); residual = term-premium steepness. Fits:
  USD `-72.5*x + 319` (R^2 88%), EUR `-70.7*x + 236` (91%), GBP `-58.6*x + 302` (89%); all 10-20bp "too steep" on 21 Aug 2026.
  Track SE and rolling 120d R^2: when R^2 decays (GBP ~100% -> ~60%), do not fade (J.P. Morgan, Global FI Markets Weekly,
  21-22 Aug 2026). See [macro-fair-value-models](../macro-fair-value-models/SKILL.md).
- **Forward-on-rhetoric model**: regress each forward (1Y ... 15Yx1Y) in levels on two G10 central-bank-rhetoric PCs, a home-market
  rhetoric score and US growth/inflation surprise scores; residual z per forward and per cross-market forward spread = rich/cheap. 5Y
  sample 1Yx1Y residuals were +2.1 to +3.8 sd (cheap) in all G10 on 30 May 2024; regime changes confound the fit (the 2020 residual
  was policy-intended) and cross-market forward spreads are safer than outrights when neutral is uncertain (J.P. Morgan, Talk is
  Cheap, 30 May 2024).
- **5y5y** isolates the terminal-rate view (5y spot is dominated by cut timing). Falling 5y5y can mean central-bank credibility
  or hikes, not weak growth. Real 5y5y policy forward = nominal 5y5y minus 5y5y inflation ([infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md)).
- **Regime-probability fair value** for forward curves/flies: `E[level at horizon] = sum_r P(r) * avg_level(r)`;
  target = (current forward - predicted) - convexity cost, convexity cost scaling with realised vol (Citi, Flying Too High,
  20 Dec 2010: 9%*6 + 21%*10 + 70%*24 = 19bp for the 5s10s30s fly).

## Worked examples

**A. Forward arithmetic you can run.** Par 6.00/8.00/9.50/10.50/11.00% (1-5y) bootstraps to spot 2y 8.08% and 1y forwards
6.00/10.20/13.07/14.36/13.77%; the approximation gives 10.16/13.00/14.28/13.76 (Salomon Brothers, Understanding the Yield
Curve Part 1, May 1995). Breakeven: 1y rate must rise by more than 420bp (6% -> 10.2%) before the 2y zero underperforms
the 1y. USD par 0.307/0.299/0.346% bootstraps to DF1 0.996939 and 1y forwards 0.291%, 0.441% (Duering, 2021, Ch.19).
`python scripts/forward_grid.py --selftest` asserts these.

**B. Spot vs forward breakeven.** 5y UST 4.15% vs 1y-forward 3.93% (-22bp); 30y 4.38% vs 4.35% (-3bp); 5s30s spot 23bp, forward
42bp. Long 5y financed at 1y 4.91% needs a 22bp rally (about a third of the 1y-by-5y 65bp implied vol); the 30y needs 3bp. A
DV01-neutral 5s30s steepener has negative carry and needs 19bp of steepening in a year (BofA, Rates basics: spot vs forward,
15 Feb 2024).

**C. Carry/roll of a forward curve trade.** 6m-forward 2s5s flattener, receive 6M5Y pay 6M2Y, DV01-neutral 1:2.48. SR(6M,5Y)
1.195%, SR(0,5Y) 1.023%, SR(6M,2Y) 0.632%, SR(0,2Y) 0.498%. Roll = (1.195 - 1.023) - (0.632 - 0.498) = 3.7bp (as printed,
inputs rounded), about 18bp on the 4.93 duration-weighted leg, i.e. 182,400 per 100m:248m (Nordea, Carry & Roll, 12 Jul 2013).
The 6M roll of the 6M5Y receiver alone is 17bp.

**D. Long-end flattener as vol (USD, 8 May 2019).** 15y5y/20y10y: level -11.3bp, 1y z 1.16, 3y z 1.01, 1y carry -0.31bp, daily
breakeven 1.3bp vs 3.0bp realised -> BE/RV 0.42, while 10y5y/15y15y had 1.07 and 20y5y/25y10y had carry +0.13 (BE 0). Entered
9 May 2019 at -11.8bp, $50K DV01 ($148.8mn 15y5y vs $90.3mn 20y10y), hedged every 20bp; reweighted 16 Oct 2019 to $84mn 20y10y
(beta 1.025); closed 5 Dec 2019 at -12.5bp with about $155K net, almost all from realised vol (Citi, Trading long-dated
convexity, 9 May 2019; Reweighting, 16 Oct 2019; Taking profits, 5 Dec 2019). **Check of the formulas against the Citi grid**: dGD = GD(20y10y) - GD(15y5y) = 25.5 - 18 = 7.5,
carry -0.31bp/yr -> sigma_BE = sqrt(0.31/(1e-4*7.5)) = 20.3bp/yr = 1.28bp/day (Citi table: 1.3). Likewise 10y10y/20y10y (carry
-1.75, dGD 10) -> 2.6bp/day and 10y10y/25y10y (carry -1.83, dGD 15) -> 2.2bp/day, both as printed. At 55bp/yr vol the
15y5y/20y10y convexity value is `1e-4*7.5*55^2 = 2.3bp/yr` (illustrative arithmetic).

**E. sigma_BE vs sigma_imp (Oct 2026).** 10y10y/20y10y: sigma_BE 92 vs sigma_imp 91 (dGD about 9.9; 6m curve cost about 4.2bp
vs straddle decay 4.1bp): fairly priced. 10y5y/15y5y: sigma_BE > sigma_imp on 75-85% of days: hump carry, not convexity
(Fwd curve vs straddle backtest spec, Oct 2026).

More cases (EUR top-of-curve, GBP 15y10y/25y10y, JPY, USD forward swap-spread grid, forward steepeners, EM trade log) in
[market cases by currency](references/market-cases-by-currency.md).

## Signals & interpretation
| Observation | Reading | Action |
|---|---|---|
| Spline residual > +3-5bp, sign-agrees with PCA residual, clean zone, months-to-breakeven < reversion horizon (3m) | forward cheap, carry affordable | receive it, ideally as a PC1-neutral fly of forwards |
| Residual large but on the wrong side of the value-carry line | carry already pays for it, or the point is illiquid | skip or switch to a fly; check 20F1Y+ and 1F1Y |
| Flattener BE/RV < 0.8, carry >= 0, since-2000 z > 1 | cheap convexity, structural receiver demand | flatten, delta-hedge each 20-25bp, review after 1y |
| Flattener BE/RV approaching 1 or carry < -2bp/yr | convexity now fairly priced | take profit |
| Steepener BE/RV > 1 (e.g. 1.2-1.4) and 3y z near -1 | paid to be short convexity | steepen, but wait for the event risk |
| sigma_BE > sigma_imp on > 75% of the last 252d | structural carry (term premium) | treat as carry, not vol RV |
| Forward-implied neutral (flat 1y1y/5y5y) well above house neutral | forward curve too steep in near forwards | favour flatteners / receive 1y1y-2y1y |
| Dislocation in meeting zone | central-bank calendar | price it as policy, not RV |
| Single-factor model R^2 falling (120d) | driver is global/term premium | do not fade |

Confirm with: a second fair-value method (cross-section vs PCA), trend (do not fade a 2w move that is accelerating), realised
vs implied vol, the trade's correlation to outright rates (R), and the cost: round-trip costs of about 1bp often equal the
mean reversion in liquid-tenor fades (median 63d reversion 0.81-1.14bp), so only trade dislocations that exceed costs (in-house tests).

## Pitfalls
- **Forwards are not forecasts.** Hold a forward trade for carry/roll/convexity, not because "the forward gets realised".
- **Interpolation and curve-build kinks.** Log-linear DFs make forwards step at nodes; under-specified curves oscillate; rolling
  knots drift forwards by up to ~0.25bp; turns are real forward kinks. Check a kink against the build before trading it
  ([references](references/forward-conventions-and-curve-artefacts.md)).
- **Aged positions must be marked off the strip at their live start**, not off constant-maturity series; hedge both legs on one
  grid ("most backtests of this trade go wrong here"); without rebalancing the trade earns gamma only from entry to exit.
- **Spot vs forward start convention** (swaps-aligned vs swaption-expiry): about 27% of 2024 business days gave different 1Y1Y
  schedules (Darbyshire, Coding Interest Rates, c.2024). GBP is T+0, AUD T+1, most others T+2.
- **Long-end flatteners are not betas.** They need near-parallel legs; insurer/VA/LDI receiving in 15-25y can keep forwards
  inverted for years and can steepen further in risk-off. Convexity can supply about 3/4 of P&L in vol spikes (GBP 15y10y/25y10y:
  GBP 445K = about 115K curve + 330K convexity, Citi, 26 Mar 2020). A flattener has no capped downside.
- **Short-window z-scores inflate** (62-day windows turn a 4bp move into 5.7sd). Use 3y and since-2000 together; check lookback
  sensitivity; today must be outside its own window.
- **First-order roll/vol is a false lure.** Roll-down divided by spread vol overstates some forward-spread ratios; include gamma,
  correlation and full P&L variance (EUR Aug 2016: pay 10y20y/receive 2y3y falls from Sharpe 0.25 to -0.01 at second order;
  Darbyshire 2022, ch.23; detail in the long-end reference, section 8).
- **Overlapping observations.** Daily z-scores, reversion horizons and hit rates built from overlapping windows are heavily
  autocorrelated: count non-overlapping episodes, use non-overlapping or HAC-corrected t-stats, and never quote a daily-sample
  p-value for a 63d-horizon fade.
- **Carry-only screens pick duration.** Extreme-z outright forwards (R ~ 1) dominate; use Carry/R and DV01-neutral
  packages. In in-house tests a carry harvest that did not beat a null was duration in disguise.
- **Front forwards (start < 2y)** follow the meeting calendar and year-end/quarter-end turns; strip turns before reading policy.
- **Futures-implied forwards** are biased by convexity (grows with sigma^2 t^2); adjust first.
- **Thin tenors** (6y, 12y, 25y, and interpolated broker quotes outside 2/3/5/7/10/30y) add noisy humps; build from benchmark tenors.
- **Negative forwards beyond ~41y (EUR 2020)**: ultra-long (50y) trades must account for them.
- **Beta extrapolation.** Do not extrapolate a forward-implied beta from 6 weeks of data (Citi, A narrative shift looms, 17 Mar 2022).
- **Liquidity**: forward packages blow out in dislocations; peak mark-to-market may be unrealisable (wait for costs ~3bp).
- **Persistent positions that "should" converge** (e.g. Dutch FTK reform, QE/QT, Formosa supply): "see little reason for a floor"
  while the flow continues (J.P. Morgan, Renewed Formosa supply, 21 Feb 2020).

## Output
Return, per currency, a markdown table sorted by the chosen score, then the shortlist:
1. **Strip table**: start, forward (%), fit (%), residual (bp), 3m roll (bp), off-frontier (bp), residual z, months-to-breakeven, zone.
2. **Grid table**: structure, forward, spot, fwd-minus-spot (bp), roll, 1y/3y/since-2000 z, trend.
3. **Pair/fly table**: legs and DV01-neutral weights, level (bp), 1y carry (bp/yr), dGD, sigma_BE, sigma_imp (if available), BE/RV,
   since-2000 z, correlation to outrights (R), Carry/R.
4. Charts (if asked): forward strip with fit and 1y-aged strip; value-vs-carry scatter with frontier; level vs aged level for the
   chosen pair.
5. For each shortlisted idea: conventions used (curve build, start schedule, unchanged scenario), data vintage, which gates failed,
   and the hand-off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) (entry, target, stop, carry/roll, re-hedge rule)
   and [rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Scripts
- [`scripts/forward_grid.py`](scripts/forward_grid.py): annual-leg bootstrap from `curve_par` or `curve_zero`, forward strip
  with cross-sectional spline residual, 3m receiver roll, value-vs-carry off-frontier, months-to-breakeven, forward grid with
  forward-minus-spot and trailing z, forward-curve pairs with carry, gamma-duration, sigma_BE and BE/RV.
  `python scripts/forward_grid.py --input curve_par.parquet --curve-id <id> --out fg` writes `fg_strip.csv`, `fg_grid.csv`,
  `fg_pairs.csv` (one curve and one snap per run). `--selftest` checks flat curve, Ilmanen and Duering bootstrap numbers,
  the annuity identity, a planted kink, look-ahead-free z, and the QF gamma table and the sigma_BE figure.

## Related skills
- [fi-curve-construction](../fi-curve-construction/SKILL.md): exact forwards, turns, interpolation and meeting-date steps.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll definitions this skill reuses for forwards.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market fixed-leg, day-count and spot-lag differences.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): par vs forward risk, Jacobians, bucketing.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA on forwards, hedge ratios, residual trading.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): DV01-neutral vs beta-weighted spreads, directionality.
- [curve-butterflies](../curve-butterflies/SKILL.md): flies, including forward flies.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): model forward fair value, term premium.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-based expressions of curve views.
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): value of convexity in the 30y+ sector.
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): swaption vols for sigma_imp.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): gamma vs vega P&L of delta-hedged flatteners.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-zone forwards and policy paths.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): futures strips, forward-forward spreads, kink fades.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): policy-anchored fair values for forwards.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life and first-passage timing for strip residuals.
- [bt-backtest-design](../bt-backtest-design/SKILL.md): aged-forward marking, rolling instruments, carry accrual in backtests.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): cross-market forward spreads and betas.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): insurer/pension flow behind inverted long forwards.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score windows and robust screening.
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): combine forward-grid metrics with other signals.
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): where this screen sits in the full scan.
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): packaging and costs of forward legs.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables.
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): MBS convexity hedging flows.
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable and structured vega supply.

## References
- Salomon Brothers (Antti Ilmanen) - Understanding the Yield Curve, Part 1: Overview of Forward Rate Analysis, May 1995: forward formulas, cheap-sector trades, worked par/spot/forward table.
- Salomon Brothers (Antti Ilmanen) - Understanding the Yield Curve, Part 6: A Framework for Analyzing Yield Curve Trades, Nov 1995: forward relation, three readings, decomposition into expectations/premium/convexity.
- Salomon Brothers (Ilmanen, Iwanowski) - Understanding the Yield Curve, Part 7: The Dynamics of the Shape of the Yield Curve, Feb 1996: forwards-as-predictors test.
- Salomon Brothers (Antti Ilmanen) - Understanding the Yield Curve, Part 5: Convexity Bias and the Yield Curve, Sep 1995: convexity bias in long forwards.
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Trading long-dated convexity, 9 May 2019: forward flattener as straddle, BE/RV grid, backtest, curve-vs-vol regression.
- Citi Research (Bikbov) - Taking profits on delta-hedged 15y5y/20y10y flatteners, 5 Dec 2019; Reweighting delta-hedged 15y5y/20y10y flatteners, 16 Oct 2019: breakeven definition, beta reweighting, cross-market grids.
- Citi Research (Bikbov, Williams) - Rates Vol Lab: In search of cheap vol, 17 Jan 2020; (Mathai, Bikbov, Kang, Williams, Li) US Rates Weekly: Eat, pay, spend, 27 Mar 2020: GBP 15y10y/25y10y trade, cross-market BE/RV ranges.
- Citi Research (Chang, Williams, Appeddu) - Rates Vol Lab: Forward steepener and vol divergence, 12 Jun 2023: steepener BE/RV frontier.
- Citi Research (Arora, Chen) - Flying Too High: Receive Belly of 1-Year Forward 5s10s30s Fly, 20 Dec 2010: regime-probability fair value and convexity cost.
- Citi Research (Searle et al.) - European Rates Weekly: Higher yields are here to stay, 24 Sep 2026; A narrative shift looms, 17 Mar 2022: forward decomposition of 5s30s, implied beta check.
- J.P. Morgan (Younger, Sarkar, Salem) - An option by any other name: Sourcing cheap convexity in the long end of the curve, 3 Feb 2017; For cheap gamma, look to the long end, 23 Aug 2019; Renewed Formosa supply continues to flatten the long end, 21 Feb 2020: curve-implied vol and forward flatteners.
- J.P. Morgan (Salford et al.) - Valuing convexity in the long end of the yield curve: a global perspective, 9 Feb 2018: expected-return formula with convexity value.
- Internal research spec - Forward Curve vs Straddle: Systematic Backtest Spec (v0.4), 23 Oct 2026: sigma_BE vs sigma_imp package, gates, filters.
- Quantitative Finance Stack Exchange - Why does the ultra long-end of a yield curve invert? (2019): convexity per DV01 proportional to T; forward-bucket gamma values.
- ING Global Markets Research (Bouvet, Schroeder, Garvey) - Deconstructing the EUR yield curve, 15 Jan 2020: xF1Y grid, value-vs-carry frontier, forward fly.
- Credit Suisse (Pelata, Giannopoulos, Haworth) - PCA Unleashed: The application of PCA across European Rates markets, 24 Oct 2012: PCA on non-overlapping EUR forwards, hedge ratios.
- Nordea Research (Lilleoere) - Carry & Roll, 12 Jul 2013; Nordea Markets (Vainikainen) - EUR Rates Flash, 24 Jan 2020 and 5 Feb 2020: carry/roll of forwards, top of the forward curve.
- BofA Global Research (Axel) - Rates basics: spot vs forward, 15 Feb 2024: building blocks, spot-vs-forward breakeven; (Braizinha) - Understanding the yield curve dynamic, 23 Jul 2025: forwards vs neutral.
- J.P. Morgan - Global Fixed Income Markets Weekly, 21-22 Aug 2026: policy-adjusted 1Yx1Y/5Yx5Y regressions; Talk is Cheap (Jarman, Bassi), 30 May 2024: forward-on-rhetoric model.
- Goldman Sachs desk (IRP Market Strats) - Global Rates Best Trade Report, 30 Sep 2026: G10 forward-grid screen, Carry/R.
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022); Coding Interest Rates (c.2024): par vs forward risk, Jacobians, forward roll-down, forward-start schedules, interpolation effects.
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): forward identities, decomposition, realised-forwards vs unchanged curve.
- Duering - Fixed Income Trading and Risk Management (Wiley Finance, 2021): bootstrap table, forward formulas.
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): forwards as PCA inputs.
- Credit Suisse (Bassman, Convexity Maven) - Forwards are NOT a Prediction, 12 Aug 2013; Building a Better Volatility Mousetrap, 6 Sep 2012: forwards as breakevens, forward stability.
- JWS Macro (Substack) - Central Casting #6.1, 21 Jun 2026: neutral from flat 1y1y/5y5y.
- Clarus Financial Technology (Barnes) - Mechanics and Definitions of Carry in Swap Markets, 16 Jan 2019: forward-starting carry.
- Further documents cited inline in the reference files: Citi Research, Short-End Notes (21 Aug 2026), All it takes is a little push (4 Oct 2019), Taking profits on GBP 15y10y/25y10y flatteners (26 Mar 2020) and on long end butterfly trade (15 Jun 2020), Emerging Markets Strategy Weekly (20 Aug 2026), Asia FX and Rates Strategy (13 Aug 2026); J.P. Morgan, Forward Treasury, Asset Swap and Funding Report (29 Jan 2015), Japan Fixed Income Markets Weekly (21 Feb 2025), Monthly Inflation Outlook (13 Aug 2026); Nordea, EUR rates: Pushing back (17 Jan 2024); Nomura, Conditional Euribor bull flatteners (19 Jun 2014); BofA, UK Rates Viewpoint (5 Sep 2024); Convexity Maven (Bassman) commentaries 2022-2024; Willer & Saunders, Trading Global Macro Markets (Wiley, 2026); Credit Suisse, Basis Points (18 Feb 2010); Burgess, Electronic Rates Markets and Low Latency IRS Calculations (May 2022).
