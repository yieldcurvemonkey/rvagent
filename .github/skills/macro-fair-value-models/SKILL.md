---
name: macro-fair-value-models
description: "Macro-factor regression fair values for G10 yields, forwards, curves and spreads. Regress the rate on policy expectations (1y1y OIS, policy rate), growth (PMI/ISM, GDP, forecast revisions), inflation, employment, central-bank balance sheet (QE/QT), global yields, FX/terms of trade and money aggregates (M2, Divisia, P-star). Rolling/expanding out-of-sample fits with HAC t-stats, residual rich/cheap in bp and z, attribution of a move to its drivers, curve-wide PCA-macro fair values, scenario projection and FX-rates linkage. Use when asked: is 10y cheap to fundamentals, macro fair value, what does the macro model say, fair value for 5y5y, was the selloff justified, yields decoupled from drivers, attribute the move, UST/Bund/gilt/JGB/ACGB fair value, yields vs PMI or ISM, rates vs Fed balance sheet, USDJPY vs rate differential, P-star, money growth and inflation, macro residual z-score, rich/cheap vs macro, regression fair value, cross-market 10y screen."
---

# Macro fair-value models for yields and spreads

A macro fair-value (FV) model regresses a rate (yield, forward, curve, spread, breakeven) on the macro and policy
variables that should set it. The fitted value is the level that fundamentals justify. The residual is rich/cheap,
in bp and in units of model standard error (SE). Macro residuals are wide: for USTs, a 14y weekly model has a residual
SD of about 35bp at 2y/5y and 20-25bp at 10y/30y (BofA, Introducing a new UST macro framework, Oct 2024). They also
persist for months. So the model is mainly a **valuation, attribution and veto** tool: it tells you whether a move
was justified, which markets or tenors are stretched against their own drivers, and where rates go under a macro
scenario. It is a weak stand-alone timing signal. Pair it with carry, PCA/curve RV and catalysts.

## When to use
- "Is 10y UST / Bund / gilt / JGB cheap or rich vs fundamentals?" "What is fair value for USD 5y5y?"
- "Was this selloff justified?" Attribute Δy to drivers and compare the model-implied move with the actual one.
- Cross-market: which G10 10y or 5y5y screens cheapest against its own drivers (rank by residual z, not bp).
- Curve: is 2s10s or 5s30s too steep vs macro? Use the PCA-macro variant (step 9).
- Scenario: where do yields go under the economists' path, a hard landing, or a QT change?
- Cross-asset linkage: FX vs rate differentials (USDJPY vs the real 10y spread), breakevens vs oil, swap spreads vs
  funding/QT, money growth (P-star) vs inflation, as an overlay for front-end and inflation views.
- Veto check on an RV idea: do not fade a "cheap" leg whose cheapness the drivers explain.

Not this skill: statistical RV between curve points ([curve-pca-factor-model](../curve-pca-factor-model/SKILL.md)),
affine term-premium decompositions ([curve-term-structure-models](../curve-term-structure-models/SKILL.md)), or
hedge ratios as such ([quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Target: par or forward swap/OIS rate, constant-maturity govt yield | `curve_par` (`start`/`tenor`; govt curves as `<CCY>-GOVT-<issuer>`) | daily close; ≥ 2y (tactical), ≥ 10y (structural) | pct; report residuals in bp |
| Target alternatives: bond yield, swap spread/ASW, ZC inflation swap, xccy basis | `bond_quotes`, `swap_spreads`, `infl_swaps`, `basis_swaps` | daily | carry each table's sign convention through |
| Policy expectations and global yields (1y1y or 3mx3m OIS, 2y, foreign 10y) | `curve_par` | same snap as the target | never mix snaps |
| Policy rate | `rate_fixings` (policy family) | daily | |
| Macro releases: PMI/ISM, CPI/PCE/HICP, payrolls/claims/unemployment, GDP, forecast revision indices, CB balance sheet, M2/Divisia, consensus | `macro_series` | release vintages; ≥ 10y monthly for structural fits | align on `pub_ts_utc`; as-of vintages (what was published by the snap) |
| Implied vol, breakevens, FX | `vol_surface`, `infl_swaps`, `fx_rates` | daily | nvol in bp; FX quote direction |
| Equity index, commodity price, trade-weighted FX, terms-of-trade index, forecast-revision and growth indices | `macro_series` (`<CC>-EQ-<INDEX>-TR`, `GL-<COMMODITY>-M1` unit `price`, `<CC>-FX-TW`, `<CC>-TOT`; unit `index` or `score`) | daily | series patterns are in [schemas](../data-contract-and-adapters/references/schemas.md); a wide panel is a view built at read time |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values or coefficients.
The published model specifications in [references/model_catalogue.md](references/model_catalogue.md) are templates
to re-estimate on your own data, not numbers to reuse.

## Method

### 1. Pick the model class: the horizon sets the window and frequency
| Class | Window / frequency | Typical drivers | Residual SD seen in sources | Use |
|---|---|---|---|---|
| Structural (cycle) | 7-15y, longer than one cycle; weekly | growth/inflation/employment factors, policy rate, CB balance sheet, global yield PC1 | UST 2y/5y about 35bp, 10y/30y 20-25bp (BofA, Oct 2024) | strategic tilt, scenarios, "is the level justified?" |
| Medium (regime) | 2-5y daily, or a rolling 2y | 1y1y or 3mx3m OIS, 5y5y breakeven, forecast revisions, CB holdings share, event dummies | JPM 30y on its 10y UST drivers 14-16bp; JPM 10y JGB 7bp | outright and curve rich/cheap, attribution |
| Tactical | 3-12m daily | front-end OIS, oil/gas, FX, vol, funding spreads | JPM UK 5y5y RPI 3bp; 10y gilt swap spread 2bp | inflation forwards, swap spreads, short-horizon RV |

**Default when the user does not specify:** run the structural fit (weekly Wednesday closes, 520 obs ≈ 10y) and the
medium fit (daily, 520 obs ≈ 2y) side by side and report both. Two windows that disagree in sign tell you the
relationship is shifting. Citi runs USDJPY on 2017-25 and 2023-25 fits for this reason (Citi, Recent changes in
USD/JPY price formation, Jun 2026). JPM runs its FX models on 2y and 1y windows.

### 2. Choose 2-5 drivers, each with an expected sign
| Driver | Typical proxy | Expected sign on yields | Sourced magnitude |
|---|---|---|---|
| Policy path | 1y1y OIS (long end), 3mx3m OIS (JGBs), policy rate | + | 30y UST: +0.414 per 1pp of 1y1y, t 49.5 (JPM, Aug 2026) |
| Growth | PMI/ISM, IP, capacity utilisation, GDP, growth forecast revisions | + | ISM/PMI have the largest yield sensitivities of 19 standardised inputs, 0.51-0.56% at 2y-30y (BofA, Oct 2024) |
| Inflation | CPI/core, PCE, ECI, import prices, inflation forecast revisions, 5y5y breakeven | + | 5y5y EUR: 0.27 on inflation revisions vs 0.12 on growth (JPM, Aug 2026) |
| Employment | payrolls, claims (×−1), unemployment rate (×−1) | + | enter as signed z-scores so every beta is expected positive (BofA) |
| CB holdings / QE / QT | CB balance sheet % GDP, CB share of recent issues, QT stock | − (more holdings, lower yields) | Fed B/S share −0.127 per pp, t −33 (JPM, Aug 2026) |
| Global yields / foreign demand | global DM 10y PC1, 10y UST for JGB/ACGB, FX-hedged pickup | + | |
| Supply / fiscal | projected deficit/GDP, WAM, free float | + (long end, curve) | see [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md) |
| Risk / vol | VIX, swaption vol | − for yields | |
| FX / terms of trade | trade-weighted FX, commodity terms of trade | market-specific | |
| Money | P-star price gap from M2 or Divisia | + inflation | γ ≈ 0.10 per 1pp of gap (Hudson Bay, Jul 2026) |
| Event / regime dummy | 1 during the regime, else 0 | by design | tariff dummy +14.4bp (JPM, Aug 2026) |

Selection rules:
- **Parsimony.** If more than about 5 correlated macro series compete, reduce them inside each group first (PCA, or
  a dynamic factor model with constrained loadings). BofA reduces 19 US series to 4 factors (broad, growth,
  inflation, employment), z-scores them, and flips claims, JOLTS and unemployment to ×−1.
- **Drop a driver that adds no R² and does not move the residual.** JPM tested TTF gas in its EUR 1y1y HICP model
  and dropped it for this reason (JPM, Monthly Inflation Outlook, Aug 2026).
- **Say what the residual means.** With front-end OIS among the regressors, the model is "fair given the policy
  path", and its residual is roughly term premium, supply and flows. Without it, the residual also contains
  policy mispricing. Label every output with the class and regressor set.

### 3. Build a point-in-time panel
- Align macro releases on `pub_ts_utc`, as-of the snap time: use the vintage published by then (the first release
  until a revision is out). A revised history, or a model estimated through t and evaluated at t, leaks the future
  and shrinks the residual. Set the cutoff to the target's snap time, not a default NY close: a US release at
  12:30 UTC is not known at a Tokyo close (about 06:00 UTC) on the same date (`--cutoff-utc`).
- Use one snap for all market data. In multi-timezone panels (AUD/NZD/JPY vs USD) use weekly Wednesday closes. This
  removes the Asia T+1 lag and NFP Fridays (Citi, Decomposing Global Rate Drivers Across EM Asia 5y5y, Aug 2026).
- Units: rates in pct, residuals in bp. Index-type drivers (equity, commodity) in logs. Write the FX quote direction
  down explicitly.

### 4. Estimate
`y_t = α + Σ_k β_k·x_{k,t} + ε_t`, OLS in levels.
- **Out-of-sample fair value:** fit on obs `[t−W, t−1]` and apply the fit to `x_t`: `FV_t = α̂ + Σ β̂_k·x_{k,t}`.
  Nothing dated t enters the coefficients. Default W = 520 obs.
- **Rolling vs expanding:** use rolling by default. An expanding window adapts slowly to regime change (BofA, Many
  EGBs, one simple value tool, Mar 2018).
- **HAC t-stats:** use Newey-West with L = ⌈1.3·√T⌉ lags. Levels residuals are highly autocorrelated. With AR(1)
  regressor and errors at ρ = 0.8, plain OLS understates the slope SE by a factor of about √((1+ρ²)/(1−ρ²)) ≈ 2.1.
  Lazarus, Lewis, Stock and Watson pair this lag rule with fixed-b critical values, which are larger than 1.96. Treat
  |t_HAC| ≥ 2 as the minimum, and require ≥ 2.5 for a driver whose residual you will trade.
- **Regime breaks:** keep the data and add a dummy plus interaction terms rather than deleting the year (Citi's
  2022 Fed-shock dummy in USDJPY). Drop only regimes that are mechanically distorted, such as debt-limit funding
  periods (BofA excludes one from its funding regressions, Monthly rates models, Aug 2025), or the ELB for vol-type
  models.
- **Non-economic betas:** if QE produces negative growth betas, impose sign priors (Bayesian shrinkage, or sign
  restrictions as BofA uses to identify shocks in its BVAR, UST RV Primer, May 2022) or add the CB balance sheet. See [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md).

### 5. Diagnose before you produce any signal
| Check | Threshold (default and reason) | Action |
|---|---|---|
| Sign vs prior | any wrong sign | flag it (JPM marks such models with `*`); do not trade that model alone |
| Sign stability | rolling β has the opposite sign to the full-sample β in > 20% of windows (default: a driver that flips one window in five cannot anchor a level) | replace the driver. JPM switched from the €STR-SOFR differential to outright 1y SOFR when its xccy-basis beta flipped in 2024 (JPM, Cross currency basis 2H25 Outlook, Jun 2025) |
| Fit (levels FV regressions whose residual you trade) | R² < 0.3: no signal; 0.3-0.7: tilt only; > 0.7: usable | below 0.3 the residual is mostly unexplained noise. This gate does not apply to overlays (P-star, R² 0.18) or to pooled cross-sectional signals (real-yield study: adjusted R² 0.05, IR 0.65; see the catalogue). Judge those on out-of-sample IR |
| Rolling R² trend | 120d R² falling (JPM SONIA curve model went from about 100% to about 60%) | reliability is falling; halve conviction |
| Residual mean reversion | AR(1) half-life ≤ ½ of the holding horizon; ADF on the residual with Engle-Granger critical values | if it fails, treat the residual as a regime shift, not a trade ([quant-cointegration](../quant-cointegration/SKILL.md)). The script reports HL in fit observations (weeks on a weekly fit), so convert it to days before comparing |
| Levels vs changes | β from a changes regression close to the levels β | if the level residual trends while the change-betas hold, the intercept has shifted. Citi found USDJPY had decoupled from the level implied by rate differentials but still tracked changes in them (Citi, Macro tapas, Aug 2026) |
| Smoothed inputs | moving averages, overlapping windows | R² and t are inflated: Citi's 200d-MA USDJPY base model has R² 0.994. Discount them |

### 6. Fair value, residual, z
- `resid_bp = 100·(y − FV)` for a pct target. For yields and forwards, **positive = cheap** (yield above what the
  drivers justify) and negative = rich. For spreads, use the stored sign convention (`swap_spreads.sign_convention`).
- `z = resid / SE_window`, where SE_window is the in-window regression SE. To compare markets, standardise each market by
  its own residual history: `z_i = (resid_i − mean_i) / SD_i`, with mean_i and SD_i taken over that market's past
  residuals (not across markets), as in BofA's global table (example F). Out of sample, a non-zero mean residual
  means the model is drifting.
- Report the ±1 SE band. A residual inside 1 SE means the level is consistent with fundamentals.

### 7. Attribute a move
`Δŷ(d0→d1) = Σ_k β_k·(x_{k,d1} − x_{k,d0})`. Then `unexplained = Δy − Δŷ`, which equals the change in residual
when β is held fixed. Use the latest window's β and report each contribution in bp.

### 8. Invert for the implied driver move
`Δx_k* = resid / β_k` is the move in driver k that would justify the current level, and `Δx_k* = Δy / β_k` the move
that would justify a recent change in y. If that move is implausible, the residual (or the move) is a mispricing.
JPM applied the second form to its term-funding-premium model: the −0.3 TFP move over one day, against a WAM
coefficient of 0.1, required WAM expectations about 3 months shorter (−0.3/0.1 = −3), which the deficit outlook contradicted. JPM took profit on
its 10s30s swap-spread steepener (JPM, Buying back time, Aug 2026).

### 9. Curve-wide PCA-macro fair values
Use this to value a whole curve consistently (BofA, Understanding the yield curve dynamic, Jul 2025; UST RV Primer,
May 2022):
1. Run PCA on yield levels (2y, 5y, 10y, 30y) over 10-15y: `S = (Y − μ)·W_k`, with k = 2 (level, slope).
2. Regress each PC score on the macro factors, the policy rate (cycle), the CB balance sheet (non-economic buying)
   and global DM yield PC1 (foreign demand).
3. Map back: `Ŷ = μ + Ŝ·W_kᵀ`. A curve FV is a difference of fitted yields, e.g. `FV(2s10s) = Ŷ10 − Ŷ2`.
4. Yield sensitivity to driver m: `∂y_j/∂x_m = Σ_i β_{m,i}·W_{j,i}`. Check that every sign matches the prior.
5. Report two FVs, "domestic fundamentals only" (without the CB balance sheet and global terms) and "adjusted"
   (with them). The gap between the two shows how much non-economic or foreign demand is holding yields away from
   macro.
6. As published, the PCA, the betas and the residual SD are all full-sample, so the z is descriptive. For a traded
   signal, estimate on data through t−1 and apply the fit to the drivers at t, as in step 4.

### 10. Project scenarios
`ŷ_s = α̂ + Σ β̂_k·x_{k,s}`, with a ±1 SE band, where `x_{k,s}` is the driver path under the scenario (economists'
forecasts, a hard landing, a QT change). FV drift matters as much as the residual. If consensus drivers are moving
toward the current yield, the residual closes without any price move. Scenario trees are in
[macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md).

### 11. Cross-asset linkage: FX against rates
- **Two-tier structure** (Citi, USD/JPY price formation, Jun 2026). Trend tier: regress the 200d MA of FX on the
  200d MAs of the real 10y yield spread, log equity index, log commodity index and a broad USD index. Deviation
  tier: regress FX minus its 200d MA on the matching deviations of the nominal 10y spread, equities, the commodity
  terms-of-trade spread and the USD index. FV = fitted trend + fitted deviation. Fit on a long window (with
  regime dummies) and a recent window, and report both.
- **Short-term version** (JPM, FX Markets Weekly, Aug 2026): FX on the 2y OIS spread and relative terms of trade
  over 2y and 1y windows. Read the residual z, and combine models with R² weights.
- **Read-through to rates.** If FX tracks *changes* in the rate differential but not its *level*, something outside
  the policy path is driving it. In Aug 2026 Citi attributed JPY weakness to a rising Japan term premium. In that
  case the rates-relevant question is what compresses the premium (faster hikes, a flatter JGB curve), not whether FX
  will revert. In the other direction, FX can be a driver in a rates model: trade-weighted sterling sits in JPM's UK
  5y5y RPI model, and USDCAD sits in Citi's US 5y breakeven model.

## Worked examples

**A. Curve-wide macro FV, USTs (BofA, Understanding the yield curve dynamic, 23 Jul 2025, levels of 22 Jul):**

| | Current | FV | Resid (bp) | Resid SD (bp) | z |
|---|---|---|---|---|---|
| 2y | 3.827 | 3.77 | 6.1 | 34.2 | 0.18 |
| 5y | 3.876 | 3.94 | −6.7 | 34.3 | −0.19 |
| 10y | 4.334 | 4.31 | 2.3 | 25.6 | 0.09 |
| 30y | 4.901 | 4.70 | 20.3 | 20.1 | 1.01 |
| 2s10s | 50.7 | 54.5 | −3.8 | 23.7 | −0.16 |
| 5s30s | 102.5 | 75.5 | 27.0 | 29.0 | 0.93 |

Read: z = resid/SD (20.3/20.1 = 1.01). Only the back end is cheap, and 5s30s is too steep by about 0.9σ. Every
front-end z is under 0.2. As a macro-consistent RV expression this points to 5s30s flatteners or the 30y outright,
not 2s10s. Confirm with carry and with the curve's own PCA residual before trading.

**B. Was the 30y selloff justified? (JPM, Global Fixed Income Markets Weekly, 21 Aug 2026).** JPM applied the
independent variables of its 10y UST FV model to the long end. The regression runs 31 Dec 2020 to 31 Dec 2025
(frequency not stated), with R² 97.9% and SE 16.0bp in the table (14bp in the text). Attribution of the 30y move
from year-end 2025:

| Driver | β | Δx YTD | Contribution, β×Δx (bp; JPM prints 40 / 0 / 0 / 2 / −14) |
|---|---|---|---|
| 1y1y OIS (%) | 0.414 | +0.98 | +40.6 |
| US forecast revision index | −0.04 | +0.1 | −0.4 |
| 5y5y TIPS breakeven (%) | 0.284 | +0.02 | +0.6 |
| Fed B/S share of economy (pp) | −0.127 | −0.2 | +2.5 |
| Tariff dummy (1 from 2 Apr 2025 to 26 Feb 2026) | 0.144 | −1 | −14.4 |
| **Model-implied** | | | **+29** |

The actual move was +45bp. The residual went from −5bp at year-end to +9bp, inside 1 SE. JPM's verdict: the move
was fundamentally justified, so there is no fade. Note the FRI beta is negative (t −5.2) against the "+" prior for
forecast revisions in step 2: under step 5 that coefficient gets a wrong-sign flag. Its contribution here is under
1bp, so the verdict stands, but do not use this model to attribute a forecast-revision move. `scripts/fair_value.py --selftest` reproduces the +29bp.

**C. Long-run 5y5y FV on forecast revisions (JPM, 21 Aug 2026; past 10y, cumulative changes in growth and inflation
forecast revision indices):** USD = 0.18·infl + 0.16·growth + 2.2 (R² 82%); EUR = 0.27·infl + 0.12·growth + 1.0
(R² 91%); GBP = 0.28·infl + 0.05·growth + 1.1 (R² 93%). The read was USD cheap but less so than at the end-2024 peak,
EUR fair, and GBP cheap. The loadings show GBP 5y5y is almost purely an inflation-revision story (growth 0.05),
while USD loads about equally on both.

**D. Cheap is not enough (JPM, Japan Fixed Income Markets Weekly, 21 Feb 2025).** The 10y JGB was regressed on
3mx3m JPY OIS, the 10y UST yield and the BoJ share of the three newest 10y issues (rolling 2y, R² 92.3%, SE 7.0bp).
The residual of +10bp (about 1.4 SE) was the cheapest since the prior July, with a peak near +15bp in mid-2024. JPM
did **not** fade it, for four reasons: medium-term policy expectations could still reprice, long-end flatteners were
pressuring the belly, positioning was light, and event risk was asymmetric around Tokyo CPI. Apply the same four
checks before fading any macro residual.

**E. Money overlay: P-star (Hudson Bay Research, A return to monetarism?, Jul 2026).**
`Δπ_t = α + Σ_{i=1..4} β_i·Δπ_{t−i} + γ·(p*_{t−1} − p_{t−1})`, with `P* = M·V*/Y*`. V* and Y* come from a one-sided
HP filter, so the estimate is real-time. Over 1967Q1-2026Q1, γ is 0.08-0.12 (t 3.6-4.0) across M2, Divisia M2 and
Divisia M4. Rule of thumb: 1pp of price gap adds about 10bp to annualised inflation the next quarter. The 2026Q1 gaps
of −0.36 to +0.79pp imply −3.5bp to +8bp, which is neutral. R² is only 0.18-0.19, so use P-star as a regime overlay
for front-end and breakeven views, never as a trading model. If Divisia M4 grows faster than M2, read it as a
financial-froth flag.

**F. Cross-market z, not bp (BofA, Monthly rates models, Aug 2025; global 10y model):**

| | Resid (bp) | Avg resid (bp) | SD (bp) | z = (resid − avg)/SD |
|---|---|---|---|---|
| Japan | +78.1 | +0.8 | 23.4 | +3.3 |
| Italy | −56.9 | −4.4 | 46.1 | −1.1 |
| Switzerland | −33.8 | +1.5 | 19.6 | −1.8 |
| US | −21.7 | +0.3 | 31.6 | −0.7 |
| UK | +29.6 | +1.2 | 31.3 | +0.9 |
| Canada | −10.8 | +0.9 | 21.4 | −0.5 |

Italy: (−56.9 + 4.4)/46.1 = −1.14. Italy's 57bp is a smaller dislocation than Switzerland's 34bp, because residual
SDs differ by market. Rank on z.

More published specifications (curves, breakevens, swap spreads, USDJPY, xccy basis, FX) are in
[references/model_catalogue.md](references/model_catalogue.md).

## Signals & interpretation
- |z| < 0.5: noise. BofA calls ±0.5σ "slightly rich", a tilt and not a signal.
- 0.5 ≤ |z| < 1: a tilt. Use it only to choose between legs or to size another signal.
- 1 ≤ |z| < 2: a candidate. It needs all of: step-5 diagnostics passed, the same sign in both windows, carry not
  adverse, and a catalyst. Expected reversion over horizon h is `resid·(1 − 0.5^(h/HL))`, with HL the residual
  half-life in the same units as h. It must beat the carry+roll given up over h and the round-trip cost.
- |z| ≥ 2 on a stable model: strong. First rule out a regime change (policy normalisation, fiscal premium, a QE
  start or end). When yields "completely decouple" from their drivers, either the yields revert or the drivers move
  to justify them (JPM, Canary in a coal mine, 25 Feb 2020). That note came on the eve of the COVID collapse, when
  the drivers moved. Before fading, ask which side is more likely to move.
- Residual within 1 SE after a big move: the move was "justified". Do not fade it (example B).
- Several models on one target: report each, plus the R²-weighted average z, `Σ R²_i·z_i / Σ R²_i`, as JPM does for
  FX. Keep low-R² and wrong-signed models visible but flagged.
- Composite scoring and the trade note: hand off to [rv-composite-scoring](../rv-composite-scoring/SKILL.md). The
  macro z is one input, with a low weight for timing and a high weight as a veto.

## G10 market notes
| Market | Drivers that matter, from the sources | Notes |
|---|---|---|
| USD | 1y1y OIS, growth/inflation revisions, 5y5y breakeven, Fed B/S share, global DM PC1, policy-shock dummies | adjusted FV (Fed B/S, global PC1) vs domestic-only; foreign demand through FX-hedged pickup |
| EUR | €STR 1y1y, inflation revisions (0.27) above growth (0.12), oil for 1y1y HICP | €STR 1y1y/5y5y curve on 1y1y €STR: −70.7bp per 1pp, R² 91% (JPM, past 1y); EGB spreads in [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md) |
| GBP | SONIA 2y1y and money-market curve shape, inflation revisions, APF (QT) stock, TW-£ | 10y real swap: R² 71%, SE 7bp; intermediate gilts have a high US beta (5y5y gilt on 5y5y UST: β 1.1, R² 75%, 6M) |
| JPY | 3mx3m OIS, 10y UST, BoJ share of recent issues | in Aug 2026 the R² of EUR/GBP/AUD daily moves on JPY rates rose from about 0% to 20-50%. When that happens, add JPY rates as a driver in those markets' models |
| AUD, NZD | USD forwards (the anchor), domestic policy and NLP scores | R² of the AUD/NZD/HKD 5y5y factor on USD 5y5y was 0.47 before 2023 and 0.76 after (Citi, Aug 2026; the HKD peg inflates it); fit around the break |
| CAD | UST (anchor), domestic policy path | small residuals vs the global model (−10.8bp, z −0.5; BofA, Aug 2025) |
| CHF, SEK, NOK | EUR and USD anchors, domestic policy, FX | SEK 10y on UST 10y: β 0.8, R² 56% (1M, Aug 2026); CHF screened −1.8σ rich in Aug 2025 |

## Pitfalls
- **Non-economic buying breaks the model:** the Greenspan conundrum (foreign CB buying 2004-06), QE (negative
  growth betas) and FX-hedged global demand. Add the CB balance sheet and global PC1, and show both FVs (BofA, UST
  RV Primer, May 2022).
- **Spurious levels regressions.** Two random walks give a high R². A levels residual is tradable only if something
  pulls it back (stationary residual, short half-life). A regression on changes gives hedge ratios but **cannot**
  give a fair value (swapsball.net, Regression in finance: friend or foe?, Oct 2017).
- **Look-ahead:** revised macro data, a full-sample β, full-sample z or percentiles. Willer and Saunders "avoid like
  the plague" full-sample percentiles.
- **Endogenous regressors.** Front-end OIS is itself a market price, so you are explaining yields with yields.
  USDJPY and equities cause each other. Present the model as descriptive, never as causal.
- **Taylor-rule FVs** explain central-bank action well after the fact but forecast poorly (Düring, 2021). Willer and
  Saunders found no Taylor specification with a high out-of-sample Sharpe. Put the policy path in as market forwards.
- **Linearity.** The model misses nonlinear stress dynamics and lower-bound effects. At the very long end, convexity
  makes curve models show ultra-longs as overvalued. That is a model artefact, "not a real trading opportunity"
  (Düring, 2021).
- **Fiscal beta.** Historically, fiscal easing came in downturns alongside safe-haven demand, which muted the
  estimated supply beta. Pro-cyclical easing can show a larger beta than the model has (BofA, Oct 2024).
- **Regime breaks.** JPM's US 5y5y CPI regression on Brent fell from R² 0.64 (Jul 2023 to Feb 2026) to 0.08
  afterwards. Re-fit around breaks. Do not average across them.
- **Residuals persist.** Goldman Sachs warns that spreads can stay wide to fair-value models for some time without
  a macro or fiscal shift (Global Rates Trader: Reaching Limits, Oct 2026). An Ilmanen-style regression forecast of
  UST returns gave IR 0.46, against 0.40 for buy-and-hold: "Valuation—use sparingly" (Willer and Saunders, 2026).
- **Overfitting.** Scoring an FV model against the next print rewards overfit univariate models (Cotton, 2016).
  Validate out of sample: [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).
- **Model uncertainty is as large as the residual.** BofA's old PCA and new DFM 10y UST fair values differ with an SD
  of about 25bp, the same size as the residual SD (BofA, Oct 2024). Before calling a 20bp residual, check that a
  second reasonable specification gives the same sign.
- **The residual is not "the risk premium".** Calling it a risk premium amounts to naming "the things one does not
  know", and it is only as good as the model (Düring, 2021).
- **Units and conventions:** pct vs bp; index levels vs yoy rates; the FX quote side; spread sign conventions;
  first-release vs revised data.

## Output
1. **FV table**, one row per model × target: `model_id | target | class | window (obs, dates) | drivers | R² | SE_bp |
   t_HAC per driver | sign flags | y | FV | resid_bp | z | z (other window) | resid half-life (fit obs and days) |
   expected reversion over horizon (bp) | verdict (cheap/rich/fair; tradable / tilt / no signal)`.
2. **Attribution table** for the requested period: contribution per driver in bp, model-implied vs actual, unexplained.
3. **Charts:** actual vs FV with ±1 and ±2 SE bands; the residual z history for both windows; rolling β per driver.
   Conventions in [eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md).
4. **Scenario table** (if asked): driver path → FV ± SE per tenor.
5. **Hand-off:** tradable signals go to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) with the
   residual, SE, half-life and driver attribution in the thesis. Vetoes ("cheap but justified") go to
   [rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Scripts
- [`scripts/fair_value.py`](scripts/fair_value.py) does the following. Run `python scripts/fair_value.py --help`.
  - Full-sample OLS with Newey-West t-stats.
  - Rolling or expanding out-of-sample fair value, residual and z.
  - Residual AR(1) half-life (full-sample and out-of-sample residual), rolling sign stability, and the wrong-sign
    flag (`--expect alias:+`).
  - Attribution (`--attr-from`).
  - `pca_macro_fair_value()` for curve-wide FVs and yield sensitivities. It is in-sample (descriptive), like the
    published versions; see step 9.
  - Reads `curve_par`, `macro_series` (point-in-time on `pub_ts_utc`, cutoff `--cutoff-utc`) or a wide panel
    (`--y-unit` required for a non-`curve_par` target). Selectors look like
    `curve_par:USD-SOFR|1Y|1Y`, `macro:US-ISM-MFG` and `panel:<col>`.
  - `--selftest` checks known answers: exact OLS, the JPM +29bp attribution, no look-ahead, the AR(1) half-life, the
    HAC inflation factor, PCA-macro recovery and as-of alignment.

## Related skills
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA loadings, inverse mapping, statistical residuals to pair with macro residuals
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): OLS/TLS/Kalman betas, residual diagnostics
- [quant-cointegration](../quant-cointegration/SKILL.md): residual stationarity tests (Engle-Granger, Johansen)
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life and entry/exit for residual trades
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): HAC, VARs, structural-break tests
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): sign priors and shrinkage against non-economic betas
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores and cross-sectional ranking
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): ACM/KW term premium as an alternative decomposition
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): scenario driver paths
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): the policy-path driver
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): hawk-dove and topic scores as drivers (ACGB 3s10s model)
- [quant-regime-detection](../quant-regime-detection/SKILL.md): break tests and regime labels for re-fitting around breaks
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): supply and fiscal drivers
- [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md): oil and gas drivers of breakevens
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): QE/QT driver series
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md), [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md), [xccy-basis](../xccy-basis/SKILL.md), [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): target-specific FV models
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): value as one systematic signal
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): vintages, snaps, holidays
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-grid RV, kinks and aged forwards.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): the implied policy path.

## References
- BofA Global Research (B. Braizinha) - US Rates Viewpoint: Understanding the yield curve dynamic (23 Jul 2025): PCA + macro fair values, the inverse PCA mapping, residual z table (example A)
- BofA Global Research (B. Braizinha) - US Rates Viewpoint: Introducing a new UST macro framework (15 Oct 2024): DFM on 19 macro series to 4 factors, residual SDs by tenor, sensitivity sanity check, failure modes
- BofA Global Research (A. Zhang, B. Braizinha, R. Axel) - US Rates Primer: UST RV Primer: A hitchhikers guide to RV on the UST curve (2 May 2022): adjusted vs unadjusted macro FV, non-economic buying, PC-beta to yield-beta conversion, sign-restricted BVAR
- BofA Global Research (B. Braizinha, K. Craig) - US Rates Watch: Monthly rates models, August '25 edition (4 Aug 2025): global 10y state-space model and residual table, debt-limit regime exclusion
- BofA Merrill Lynch Global Research (E. Satko) - European Rates Viewpoint: Many EGBs, one simple value tool (21 Mar 2018): expanding vs rolling windows, residual screens without fundamentals
- J.P. Morgan (F. Diamond et al.) - Global Fixed Income Markets Weekly: Reduce outright duration risk but keep long 10Y Eur vs. US (21 Aug 2026): 30y attribution, 5y5y FRI models, UK and cross-market betas
- J.P. Morgan (F. Diamond, F. Infante et al.) - Monthly Inflation Outlook: A mixed bag of inflation market views (13 Aug 2026): UK/EUR/US inflation FV models, driver-selection rule, regime split
- J.P. Morgan (H. Yamamoto, T. Yamawaki) - Japan Fixed Income Markets Weekly: Non-Stop Dynamics (21 Feb 2025): 10y JGB FV model and why a cheap residual was not faded
- J.P. Morgan (I. Ozil, C. Hayward, E. Alptuna) - US Rates: Buying back time (19 Aug 2026): implied-driver inversion on a term-funding-premium FV model
- J.P. Morgan (F. Diamond, K. Gupta, T. Yamawaki et al.) - Cross currency basis 2H25 Outlook: Domestic idiosyncratic drivers in the limelight (5 Jun 2025): a regressor beta that flipped sign, and the driver replaced
- J.P. Morgan (M. Chandan et al.) - FX Markets Weekly: Currencies amid long-end UST shenanigans (21 Aug 2026): short-term FX FV regressions, R²-weighted residual scores, keep-but-flag low-R² models
- Citi Research (O. Takashima, D. Tobon, B. Levine) - Japan FX: Recent changes in USD/JPY price formation (15 Jun 2026): two-tier FX-rates model, regime dummies with interactions, dual windows
- Citi Research (A. Pickett, D. Willer et al.) - Global Macro Strategy: Macro tapas: running with the bulls; should rates scare us? (7 Aug 2026): level decoupling vs change tracking in USDJPY
- Citi Research (G. Goh, R. Garg) - Asia FX and Rates Strategy: Decomposing Global Rate Drivers Across EM Asia 5y5y (13 Aug 2026): weekly Wednesday panels, USD-anchor R² break in 2023
- Hudson Bay Research (P. Ireland, S. Miran, N. Roubini) - A return to monetarism? (Jul 2026): P-star with M2 and Divisia aggregates, real-time one-sided HP trends
- Citi Research (J. Mathai, R. Bikbov, S. Kang, J. Williams) - US Rates Weekly: Going nuclear (on the curve) (3 Feb 2017): fundamental 10s30s models (deficits, inflation target, global curve factor)
- Nordea Markets (J. Vainikainen) - EUR Rates Flash: Rates low vs global manufacturing PMI (5 Feb 2020): swap rates vs global PMI cross-check
- J.P. Morgan (J. Barry et al.) - US Treasury Market Daily: Canary in a coal mine (25 Feb 2020): yields decoupled from fundamental drivers as a regime warning
- Goldman Sachs (G. Cole et al.) - Global Rates Trader: Reaching Limits (2 Oct 2026): spread FV residuals can persist without a macro or fiscal shift
- swapsball.net - Regression in finance: friend or foe? (27 Oct 2017): spurious levels regressions; changes regressions give hedges, not fair values
- A. Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): residual-as-risk-premium caution, the Taylor rule as an ex-post tool, convexity artefacts at the long end
- D. Willer, A. Saunders - Trading Global Macro Markets (Wiley, 2026): backtested valuation regressions, point-in-time and no-full-sample-percentile rules
- P. Cotton - Filtering bond and credit default swap markets (NYU Tandon seminar, 27 Apr 2016): evaluating FV models without rewarding overfit
- W. Newey, K. West - A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix (Econometrica, 1987) (external): HAC standard errors
- E. Lazarus, D. Lewis, J. Stock, M. Watson - HAR inference: recommendations for practice (Journal of Business & Economic Statistics, 2018) (external): lag-length rule
- J. Hallman, R. Porter, D. Small - Is the price level tied to the M2 monetary aggregate in the long run? (American Economic Review, 1991) (external): original P-star model

Sources used only in the catalogue are cited in its rows: Citi's 5y-breakeven, 2y swap-spread and PMI-to-growth
models, and the JPM xccy-basis (2015, 2024) and cross-sectional real-yield (2012) studies. See
[references/model_catalogue.md](references/model_catalogue.md).
