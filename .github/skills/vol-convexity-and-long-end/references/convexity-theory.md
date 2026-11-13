# Convexity theory, bias and valuation (long-end detail)

Loaded from [SKILL.md](../SKILL.md). Conventions: yields in %, vols in normal bp/yr, DV01 in currency per bp
(positive for long duration), receiver = long duration.

## 1. Price maths

| Object | Formula | Note |
|---|---|---|
| Price expansion | `dP/P = -D·dy + ½·C·dy²`, `D = -(1/P)dP/dy`, `C = (1/P)d²P/dy²` | positive C: DV01 falls as yields rise (Tuckman/Serrat, Fixed Income Securities, 4th ed., 2022) |
| Zero coupon, continuous | `P = e^{-yT}`, `DV01 ∝ T·P`, `d²P/dy² = T²·P` so **gamma/delta = T** | exact for one cash flow, "mostly true" for swaps/bonds (Citi, Holistic approach to convexity, Jun 2022) |
| Zero coupon, semi-annual | `D = T/(1+y/2)`, `C = T(T+½)/(1+y/2)²` | convexity grows ~T², duration ~T (Tuckman/Serrat 2022) |
| Par swap/forward swap receiver at strike K | `V = (K-S)·A(S)` so `dV/dS = -A` at the money, `d²V/dS² = -2A'(S) = 2·D_A·A` | **gamma per DV01 = 2·D_A·1e-4 per bp**; D_A = modified annuity duration measured from today |
| Dispersion | at equal duration a barbell/spread-out flow set has more convexity; a zero has the least | Kogelman form in Ilmanen, Convexity Bias and the Yield Curve (Salomon, Sep 1995) |
| Value of convexity | `½·C·Vol(dy)²` in yield-%; for a swap per unit DV01 **`1e-4·D_A·σ²·T` bp** | doubling vol quadruples it (JPM, Valuing convexity in the long end, Feb 2018) |

Gamma of a $1,000-PV01 swap (Q&A thread on why the ultra-long end inverts, QF Stack Exchange, Aug 2019):
10y 1.1, 10y10y 3.1, 20y10y 5.1, 30y10y 7.1, 40y10y 9.1 ($ per bp). The formula `2·D_A·1e-4·1000` at 0% yield gives
1.05 / 3.05 / 5.05 / 7.05 / 9.05, so the source is the same maths. At 50bp/yr, one-year gamma value
`½·50²·γ` = 1.4 / 3.9 / 6.4 / 8.9 / 11.4 bp per unit DV01.

Rule of thumb for swaps (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022): pay-fixed swap
from annual period h to i has `G ≈ -(h+i)/10,000 · S` (S = DV01), a receiver is the mirror. Better: DF-weighted
`G = -(S/10,000)·Σ_{j=h..i} 2j·A_j/A`, within 0.5% of the simple rule for a 5y5y at low rates, ~10% off for long tenors at high
rates. Single-number gamma assumes parallel moves; non-parallel needs the cross-gamma grid.
Flagged inconsistencies in the book's printed examples: the 30Y10Y example (-$182 printed vs 71 x 2 = 142 from the
stated inputs) and the 5Y5Y gamma 11 in the EUR table (rule gives 16). Re-derive before quoting.

## 2. Convexity bias in forwards and the shape of the long end

- Forward = expected future rate + risk premium − convexity bias. For a bond: `CB = -½·Cx·Vol²`, i.e. **convexity bias =
  minus the value of convexity**. One-period forwards (not spot or par rates) are the right object (Ilmanen, Understanding the Yield Curve Part 6, Nov 1995).
- Local expectations (all bonds same expected return) vs unbiased expectations (forward = expected spot): in yield terms the
  difference is the convexity bias. Rolling yield assumes zero vol, so it is a downward-biased expected return for convex bonds.
- Expected return `E(R) = carry + slide + 0.5·γ·σ²·T/PVBP` in yield bp (JPM 2018). Use end-of-horizon duration and convexity.
  A single scenario implicitly assumes zero vol and understates convex positions (Salomon Part 6).
- Mean vs mode: a flat modal path (3% forever) still prices forwards at the **mean**; log-normal `Mean = Mode·e^{(3/2)σ²}`.
  Combined with the gamma adjustment, forwards rise to a hump then fall, par rates rise then flatten (Darbyshire, ch.8).
- Gamma no-arbitrage: pay xY1Y / receive (x+1)Y1Y, each $10,000 PV01, perfectly correlated normal rates, zero expected move:
  `E[P] ≈ -x·σ_x² + (x+1)·σ_{x+1}²`; when positive, the longer swap must be priced upfront-biased (Darbyshire, ch.8).
- Ultra-long inversion beyond ~25-30y: expectations and term premium saturate while convexity value keeps growing, so
  models show ultra-longs "overvalued". Usually a model shortcoming, not a trade (Düring, Fixed Income Trading and Risk Management, 2021).
  A forward/rolling-yield cheapness screen will mechanically make the long end look rich (Ilmanen Part 1/2).
- Negative forwards beyond ~41y in the EUR curve: ultra-long (50y) trades must handle them (Nordea, EUR Rates Flash, Feb 2020).
- Maths caveat: with symmetric yield distributions, expected return from convexity explodes with maturity (zero at 2.25%, +-100bp
  equal odds: 30y +4.5%, 50y +12.8%, 100y +54%); in equilibrium the yield distribution must be asymmetric. Do not price
  ultra-long convexity off symmetric-yield assumptions (Huggins/Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).

## 3. Fig. 9 style table (US Treasuries, 1 Sep 1995; Ilmanen, Part 5)

Mod duration / convexity / bp yield vol / yield / rolling yield / value of convexity / convexity-adjusted E[r], %:
10y par 7.20 / 0.67 / 0.95 / 6.47 / 6.94 / 0.27 / 7.21; 30y par 12.66 / 2.57 / 0.82 / 6.81 / 6.67 / 0.88 / 7.55;
30y zero 28.07 / 8.14 / 0.79 / 6.88 / 5.93 / 2.53 / 8.46. The adjustment is trivial under 3y, 88bp for the 30y coupon bond
and 253bp (~30% of E[r]) for the 30y zero; the adjusted curve still inverts beyond 25y. Worked basics from the same note:
30y zero, y = 8%, P = 9.50, +-200bp equal odds gives 5.40 / 17.00, E(P) = 11.20, a 1.70 gain = value of convexity at 200bp vol;
long zero with Cx 2.25 and 100bp vol: `0.5·2.25·1² = 1.125%`.

## 4. Barbells, bullets, flies

- Rolling-yield curve is almost always concave, so the barbell gives up rolling yield; convexity pickup rarely covers it.
  1s/30s barbell vs 10y bullet (Sep 1995): give-up 71bp (6.23 vs 6.94), convexity 1.38 vs 0.67, adjusted give-up still 51bp.
  Breakevens: 10s30s narrows 11bp with no parallel move, or a 138bp parallel shift with no reshaping. Over 15 years 10s30s
  narrowed >=11bp in a year 30% of the time; a >138bp yearly move happened 17% of the time. So the give-up is more likely recovered by flattening than by convexity (Ilmanen Part 5).
- 1980-94: 30y + 1m-bill barbell vs 5y bullet returned 8.69% vs 9.75%; barbell-minus-bullet -1.05% = yield -0.95 + reshaping -0.36 + convexity +0.30; 99% of its variance is reshaping. Barbell-bullet trades are curve trades, not convexity trades (Ilmanen Part 5). Do not extend wide-barbell results to narrow ones.
- Duration-neutral fly with a short bullet: re-hedging earns positive P&L before costs; the bullet's yield sits above the
  wings' interpolation as compensation for being short convexity (Düring ch.20/31). Convexity cost = net convexity x implied vol;
  UST 2-5-10 pickup tracked it in 2009-10, weakening when central-bank asset purchases and forward guidance suppressed vol (Düring).
- Forward-fly cost deduction: `target = (current fwd - predicted fair value) - convexity cost` (Citi, Flying too high, Dec 2010):
  1y-forward 10s30s steepener +27bp/yr carry but 11bp/yr convexity cost at 120bp/yr realised vol; receive 1y-forward 5s10s30s belly
  (fly = 2x10y - 5y - 30y, positive = belly cheap) -5bp carry, 8bp convexity cost.
- Ratio of durations is not the hedge ratio, and barbell convexity is not free (Kopprasch, Understanding Duration and Volatility, Salomon, Sep 1985).
- Century-bond example (Tuckman/Serrat 2022): NSC 4.10s-2121 D 24.1, C 1,101 vs UST 1.625s-50 D 23.6, C 648. -100bp: duration only
  +24.1%, with convexity +29.6%, actual +30.978%. Long $100mm NSC / short $121mm UST-50 (DV01-matched): -100bp NSC +$30.96mm vs
  leg +$27.7mm; net positive both ways but bleeds carry if rates do not move.
- Ultra futures vs swaps (Credit Suisse, New Ultra Long Contract, Sep 2009): DV01/convexity 30y swap 1,684/432, ultra bond contract 2,079/442, classic bond contract
  1,331/112. Ultra convexity ~4x the classic contract and ~ a 30y swap. +-100bp DV01 change: 30y swap -22%/+29%, classic bond contract -6%/+12%.
  Futures convexity can be negative while each deliverable is positive (Salomon, Understanding Treasury Bond Futures, Oct 1990).

## 5. Expected-Sharpe screen for linear trades (Citi, Holistic approach to convexity, Jun 2022)

`pnl = θ·dt + Δ·dr + V·dvol + ½·Γ·dr²`. Linear trades: carry + roll + convexity (bp/yr) over P&L vol gives an expected
Sharpe that ranks swaps, govies, flies, wedges and forward-vol triangles on one frontier. EUR June 2022: pay 5y5y-15y5y-25y5y
fly ER +34bp, risk 50bp, expected Sharpe +0.7; selling 1Yx2Y wedges profitable 2013-22. Charts of trades with structural convexity
bias are misleading until P&L is split into delta, carry and convexity.

## 6. Second-order Sharpe for forward spreads (Darbyshire, ch.23)

First-order "roll-down / vol of spread" matrices can badly overstate long-end forward spreads. With gamma (EUR, Aug 2016):
pay 10Y20Y / rec 2Y3Y +0.25 first-order becomes -0.01; pay 2Y3Y / rec 30Y20Y -0.25 becomes +0.18. Receiving long-end forwards
gains from convexity. Roll-down is "akin to selling volatility and going long theta" and failed badly in 2021-22.
A smile raises the value of gamma; too few strikes in a swaption replication overestimates gamma value.
