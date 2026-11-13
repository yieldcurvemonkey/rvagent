# Signal combination and decay: derivations and lookup tables

Supporting material for [SKILL.md](../SKILL.md). Grinold-Kahn (G-K) formulas marked *reconstructed* were rebuilt so
that they reproduce the book's printed worked numbers (the displayed equations are images in the source). The
bundled `scripts/signal_ic.py --selftest` asserts each reconstruction against the printed numbers.

## 1. Combining N standardized signals

Setting: scores z (each mean 0, sd 1) with correlation matrix R, target return r with sd σ, and IC vector
IC_i = corr(z_i, r). The best linear forecast is the regression of r on z:

```
E[r | z] = σ · ICᵀ R⁻¹ z = σ · wᵀ z,        w = R⁻¹ IC
IC_comb² = Var(wᵀz) = ICᵀ R⁻¹ IC            (squared correlation of the forecast with r)
```

So the refined combined forecast is already in "vol × IC × score" form: σ·wᵀz = σ·IC_comb·z_comb with
z_comb = wᵀz / IC_comb (unit variance).

Two signals, correlation ρ (G-K Ch.10 and Ch.13):

```
w₁ = (IC₁ − ρ·IC₂)/(1 − ρ²)        w₂ = (IC₂ − ρ·IC₁)/(1 − ρ²)
IC_comb² = (IC₁² + IC₂² − 2ρ·IC₁·IC₂)/(1 − ρ²)
equal ICs:  IC_comb = IC·√(2/(1+ρ))       uncorrelated: IC_comb² = IC₁² + IC₂²
```

`w₂ < 0` exactly when IC₂ < ρ·IC₁. The second signal is then a noise hedge, not a second source of information.

**G-K binary-model example (Ch.10).** Quarterly return vol 9. g has 3 signal and 13 noise units, so Var g = 16 and
IC_g = 3/(9·4) = 0.0833. g′ has 4 signal units, Var g′ = 25 and IC_g′ = 4/(9·5) = 0.0889. Cov(g, g′) = 5, so
ρ = 5/(4·5) = 0.25. The combined IC is 0.1090. The raw-unit regression coefficients are
Σ⁻¹·Cov(g, r) = [[16,5],[5,25]]⁻¹·[3,4] = [55, 49]/375 = 0.1467 and 0.1307, as printed.

Strategy-level analogue (unit-risk strategies with information ratios IR_i and return correlation R): the
risk weights are ∝ R⁻¹·IR and IR_comb = √(IRᵀ R⁻¹ IR). Equal risk weights with average pairwise correlation ρ̄
give

```
IR_EW = mean(IR) · √N / √(1 + (N − 1)·ρ̄)
```

You can invert this to back out the average correlation implied by a published combined IR.

## 2. Information horizon (decay)

- Event or one-off information: IC(j) = IC(1)·γ^(j−1) and half-life = ln 0.5 / ln γ (G-K Ch.12).
- Gradual decay of a periodic score: the IC against the return n+1 periods ahead is IC·δⁿ. A half-life of one
  quarter on monthly data gives δ = 0.5^(1/3) = 0.7937 (G-K Ch.13).
- **Correlation of the score with the cumulative return over horizon T** (*reconstructed*). With continuous
  decay rate λ = ln2/HL and independent per-period returns,

  ```
  corr(T) ∝ (1 − e^(−λT)) / √(λT)
  ```

  The maximum is where 2x = eˣ − 1, i.e. x = λT = 1.2564, with value 0.6382 (the book prints "0.6382 at
  x = 1.257"). So T* = 1.2564·HL/ln2 = **1.81·HL**, which the book calls "about twice the half-life".
- **Macro version.** Delay implementation by k periods and record the realised IR(k). The IR half-life is the
  delay that halves the IR. Value added ∝ IR², so its half-life is half the IR half-life. G-K example: IR
  half-life 1.2 years, so value-added half-life 0.6 years.
- **Now/Later mix (G-K Ch.13).** Now IR 1.5 and Later (1-month lag) IR 1.2 give γ = 0.8. With active-return
  correlation ρ:

  | ρ | Now | Later | combined IR |
  |---|---|---|---|
  | 0.5 | 67% | 33% | 1.59 |
  | 0.7 | 81.5% | 18.5% | |
  | 0.8 | 100% | 0% | 1.50 (no gain) |
  | 0.85 | 118.5% | −18.5% | |

- **Optimal mix of past scores.** Mix them so that the mixture's autocorrelation equals δ. If δ = ρ, use the
  latest score. If δ > ρ, add older scores. If δ < ρ, subtract older scores. The repackaged signal keeps the same
  half-life.

## 3. Turnover of a position proportional to a persistent score (derived, not from a cited source)

For a stationary Gaussian AR(1) score with unit variance and lag-1 autocorrelation ρ, Δs ~ N(0, 2(1−ρ)), so

```
mean|Δs| / mean|s| = √(2(1 − ρ))           score half-life HL_s = ln 0.5 / ln ρ
```

| HL_s (periods) | 5 | 10 | 20 | 60 | 120 |
|---|---|---|---|---|---|
| ρ | 0.871 | 0.933 | 0.966 | 0.989 | 0.994 |
| turnover per period, fraction of gross | 0.51 | 0.37 | 0.26 | 0.15 | 0.11 |

This holds for proportional sizing only. Threshold entry/exit and no-trade bands cut it sharply.

## 4. Grinold-Kahn lookup tables

**IC tiers (Ch.10):** good 0.05, great 0.10, world-class 0.15. Above 0.20 "usually signals a faulty backtest".
Realised IR above 2 signals "mistakes in the analysis".

**Before-fee IR distribution (Table 5.1):** 90th percentile 1.0, 75th 0.5, 50th 0.0, 25th −0.5, 10th −1.0.

**IC shrinkage factor T·IC²/(1+T·IC²) (Table 11.4, *reconstructed*):**

| T (months) | IC 0.05 | IC 0.10 |
|---|---|---|
| 36 | 0.08 | 0.26 |
| 60 | 0.13 | 0.38 |
| 90 | 0.18 | 0.47 |
| 120 | 0.23 | 0.55 |
| 240 | 0.38 | 0.71 |

**Return forecasts barely change risk: σ_post = σ·√(1 − IC²) (Table 10.4, *reconstructed*).** With σ = 18%:
IC 0.05 gives 17.98, 0.10 gives 17.91, 0.15 gives 17.80, 0.25 gives 17.43.

**Qualitative view to score (Table 19.3), mean 0 and sd 1:**

| view | very positive | positive | none | negative | very negative |
|---|---|---|---|---|---|
| frequency | 0.11 | 0.22 | 0.33 | 0.22 | 0.11 |
| score | +1.73 | +0.87 | 0 | −0.87 | −1.73 |

IC 0.10 is right about 55% of the time. For sign forecasts IC = 2·hit − 1 (*reconstructed*), so 52.9% maps to
0.0577 and 51% maps to 0.02.

**Fundamental-law trade-offs (Ch.6):** doubling IR needs 2× IC or 4× breadth, and +50% breadth equals +22%
skill. A quarterly single-market timer (BR 4) needs IC 0.25 for IR 0.5. IR² adds across independent sources:
managers with IR 0.75, 0.50 and 0.30 combine to 0.95.

**Turnover vs value-added frontier (Ch.16, S&P 100 example).** Implied round-trip cost is the slope of the
frontier at that turnover:

| % of full turnover | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 | 90 |
|---|---|---|---|---|---|---|---|---|---|
| % of value added | 39.2 | 59.0 | 71.4 | 80.2 | 86.8 | 91.8 | 95.5 | 98.0 | 99.5 |
| implied round-trip cost % | 8.66 | 5.12 | 3.40 | 2.50 | 1.90 | 1.43 | 1.02 | 0.67 | 0.33 |

The lower bound from prorating every trade is 75% of the incremental value added, and 87% of the IR, at 50% of
the turnover.

**Event information (Ch.12):** an event with daily probability p arrives every 1/p days on average. Rare events give
a small effective breadth N*. A CEO change (p = 0.00056) contributes almost no breadth even across 1,000 names.

## 5. JPM duration signals: combination check (our computation from published inputs)

Inputs (J.P. Morgan, Systematic fixed income trading strategies, 13 Apr 2015): IRs since 1998 are PMI momentum
0.59, earnings-revision momentum 0.84, bond momentum 0.64, equity momentum 0.66 and carry-to-risk 0.59. The
published combined IR is 1.31, with weights 15/15/20/15/35.

Signal-return correlations:

| | PMI | revisions | bond mom | eq mom | carry/risk |
|---|---|---|---|---|---|
| PMI | 1 | 0.62 | 0.41 | 0.55 | −0.42 |
| revisions | | 1 | 0.21 | 0.61 | −0.19 |
| bond mom | | | 1 | 0.22 | −0.21 |
| eq mom | | | | 1 | −0.28 |

| weighting | combined IR |
|---|---|
| independent (√ΣIR²) | 1.50 |
| optimal R⁻¹·IR (risk weights ≈ 10/20/20/13/37) | 1.34 |
| JPM 15/15/20/15/35 treated as risk weights | 1.33 |
| equal risk weights (ρ̄ = 0.15) | 1.17 |
| **published** | **1.31** |

Assumptions: the signal strategies have equal vol, the weights act on risk, and the IRs are in-sample and
full-period. The match supports the method, not the specific weights. The note itself says equal and optimised
weights differed "only marginally" in its earlier tests, while this calculation puts equal weights 0.17 below
optimal. Treat optimised in-sample weights with the shrinkage above.

## 6. Signal operators (Finding Alphas, Ch.28-29)

| operator | definition |
|---|---|
| rank(x) | cross-sectional rank mapped to [0,1], ties averaged |
| ts_rank(x, n) | rank of today's value within its own last n values, in [0,1] |
| delta(x, n) | x_t − x_{t−n} |
| decay_linear(x, n) | (n·x_t + (n−1)·x_{t−1} + … + 1·x_{t−n+1}) / (n + (n−1) + … + 1) |
| decay_exp(x, f, n) | (x_t + f·x_{t−1} + … + f^(n−1)·x_{t−n+1}) / (1 + f + … + f^(n−1)), f < 1 |
| neutralize(x, group) | x − mean(x within group) |
| scale(x) | x / Σ\|x\| |
| signed_power(x, e) | sign(x)·\|x\|^e |
| Fisher transform | arctanh(r), approximately normal with standard error 1/√(n−3) |
