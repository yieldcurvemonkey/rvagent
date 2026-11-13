---
name: curve-term-structure-models
description: "Fits term-structure models to G10 OIS/swap and government zero curves: dynamic Nelson-Siegel(-Svensson) level/slope/curvature factors, Vasicek and Hull-White short-rate models, the Gauss+ three-factor cascade, Gaussian affine models and shadow-rate models near the lower bound. Uses them for model-implied fair value, treats fitting errors (market minus model, bp) as rich/cheap signals with factor-neutral hedges, and splits yields and forwards into expected short rate, term premium and convexity (Gauss+, ACM, Kim-Wright, survey and regression proxies). Use when asked: how much term premium is in 10y, 5y5y or 10y10y; was the move policy path or term premium; ACM, KW or risk-neutral yield; model fair value of a forward; Nelson-Siegel or NSS betas, residuals, Diebold-Li forecast; Vasicek, Hull-White mean reversion, sigma or factor duration; Gauss+ fitting error; expectations hypothesis test; shadow rate, ELB or YCC; convexity bias in long forwards; affine model; term structure model."
---

# Term-structure models: fair value and expectations vs term premium

A term-structure model ties every point on the curve to a few state variables, so you get two things a
spline cannot give you.
1. **Model-relative value.** A forward or yield that sits away from the model, once the model's factors are hedged,
   is a candidate RV trade.
2. **Decomposition.** Split a forward into the expected short rate, the term premium and the convexity bias. This
   answers "is the curve pricing policy or premium?"

Neither output is observable. Both are only as good as the identifying assumption behind them, so this skill always
reports the method, the assumption and a cross-check with each number.

## When to use
- "How much of 10y / 5y5y / 10y10y is term premium? Is it high vs history?" or "Was this sell-off policy path or
  term premium?"
- "Is the 9y forward cheap to the model?" You want forward-rate RV with factor-neutral hedges, rather than
  bond-vs-bond rich/cheap (for that see [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md)).
- You need a smooth zero/forward curve with interpretable factors (NS betas), residual screening across tenors, or
  a Diebold-Li style forecast curve.
- You need consistent pricing across instruments with one set of parameters (Vasicek/Hull-White): factor durations,
  convexity in long forwards, or the σ and mean reversion that other skills consume.
- The curve is at or near an effective lower bound or under a yield floor/YCC (EUR 2014-22, JPY, CHF), and
  observed vols and PCA loadings have collapsed.

## Conventions
- **Decomposition identity** (Ilmanen & Iwanowski; Tuckman & Serrat):
  `forward f(τ) = E^P[r_τ] + TP_f(τ) − CX(τ)`. Here `CX ≥ 0` is the convexity bias (Jensen term), which grows
  roughly with σ²τ², so convexity pulls long forwards **below** expectations. Yield: `y(n) = mean of E^P[r] over 0..n
  + TP_y(n) − CX_y(n)`. A **forward** term premium (e.g. the 10y-forward TP) is not a **yield** term premium (the
  average of forward TPs to n). Always label which one you report.
- **Instrument basis.** `govt yield = OIS-implied expected path + OIS term premium + (govt − OIS spread)`. A term
  premium estimated on Treasuries contains the swap spread, and one estimated on SOFR/€STR OIS does not. US swap
  spread = swap − Treasury, so "Tsy − SOFR = +41bp" is a swap spread of −41bp. For EGBs, compare on the
  €STR curve or on Bunds. BTP/OAT curves add credit and redenomination premia that a model will call "term premium".
- **Units and signs.** Rates are in % in the tables. Term premium, convexity, residuals and fitting errors are in bp.
  `residual = market − model`. Positive means the market yield or forward is above the model, i.e. cheap to receive
  or buy. Short-rate σ is a normal (bp) vol. Factor DV01 follows `fi-risk-dv01-and-transforms` (positive = long
  duration).
- **Fit or fair value.** No-arbitrage models (Ho-Lee, Hull-White, HJM) reprice today's curve exactly by
  construction, so they give no curve RV signal. They are for consistent pricing, hedging and convexity.
  Equilibrium or parsimonious models (Vasicek, NS, Gauss+, affine) do not fit exactly, and their residual is
  "either the benchmarks are rich/cheap or the model is misspecified" (Salomon Brothers, Ilmanen & Iwanowski, 1996).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| OIS/swap or govt zero curve | `curve_zero` | daily, ≥ 3y for residual z-scores, ≥ 8y for Gauss+/affine parameters | `discount_factor` required. `z = −100·ln(DF)/τ`, τ = days/365, skip the τ = 0 node |
| Par swap / fitted govt par yields | `curve_par` (`start = 0D`) | daily, tenors 1y..30y (≥ 8 tenors) | use when no zero curve exists. NS on par rates is a smoother only |
| Policy rate and RFR fixings | `rate_fixings` | daily | the short-rate anchor `r` for Gauss+ (the policy target, not repo) |
| Meeting calendar | `cb_meetings` | full schedule | front-end jumps, and dating "policy vs premium" events |
| ATM normal vols (cap/swaption) | `vol_surface` | daily | calibrate short-rate σ to one liquid point (e.g. 10y) |
| Survey / long-run expectations | `macro_series` | monthly or quarterly vintages | survey anchor for E^P[r] (Kim-Wright style), long-run inflation trend |
| Published model TP (ACM, KW, others) | `macro_series` (`<CC>-TP-<MODEL>-<TENOR>`, unit `pct`; convert to bp here) | daily or monthly, stored as vintages | Treat as revisable |

Contract details are in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If an input is missing,
ask the user or the data adapter. Never invent curve points, survey values or published TP numbers.

## Method

### 1. Pick the model for the question
| Question | Model | Why / limitation |
|---|---|---|
| Smooth curve, factor time series, residual screen across tenors | Dynamic NS, fixed λ ([script](scripts/nelson_siegel.py)) | OLS, stable, interpretable. Imposed loadings push off-shape moves into residuals |
| Consistent pricing, factor duration, convexity in forwards | Vasicek / Hull-White 1F | closed forms. One factor. Downward-sloping vol, no hump |
| Forward-rate RV with policy and long factors, and a term premium from long forwards | Gauss+ | hump-shaped vol. Needs staged estimation |
| Published-style term premium | ACM, Kim-Wright (external) | time-varying premium. Model choice moves the answer |
| Near the lower bound, yield floors, YCC | shadow-rate Vasicek | stable dynamics at the bound. Unstable estimation |
| Quick premium proxy without a model | slope-on-level regression residual | cheap. It is a residual, not a premium |

One consistent model gives one RV benchmark and avoids "model arbitrage" between instruments priced on different
models. The cost is that you may end up reading your own assumptions back. Huggins & Schaller deliberately prefer
modest models with a clear view of specific market mechanisms (Wiley, Fixed Income Relative Value Analysis, 2024).

### 2. Dynamic Nelson-Siegel (smooth curve, factors, residuals)
1. Zero form (time-scale λ, in years; this is the form the script uses):
   `z(τ) = β0 + β1·(1 − e^{−τ/λ})/(τ/λ) + β2·[(1 − e^{−τ/λ})/(τ/λ) − e^{−τ/λ}]`. NSS adds `β3` with a second decay
   λ2. In this form `β0 = z(∞)`, `β0 + β1` is the instantaneous short rate, `−β1 ≈` the slope (long − short) and `β2`
   is the curvature. The curvature loading peaks at `τ = 1.793·λ`. Forward form and par conversion are in
   [model-formulas](references/model-formulas.md).
2. **Freeze λ.** Default λ = 1.368y (Diebold-Li's 0.0609/month, which puts the curvature peak at about 30 months), for
   curves to 10y. For 30y swap or govt curves, grid-search one λ on the pooled sample (`--grid`, 0.3-6y), then hold
   it fixed. Only a fixed λ gives constant loadings and comparable beta time series. Free daily λs are very volatile,
   and with NSS the β2/β3 split is not identified when λ1 ≈ λ2 (Düring, Wiley, 2021, Ch.19 and Ch.31). Add NSS (λ2
   around 5-15y) only when the 20-50y convexity hump matters.
3. **Fit daily by OLS** on zero rates with equal weights. Report RMSE and mean absolute residual (MAD) per day.
   Quality gate, relative to the curve's own history: if today's MAD is above the 95th percentile of its trailing
   1y, treat residuals as noise (stress, bad nodes) and not as RV. A fixed-λ 3-factor fit on swap nodes has its own
   normal MAD, so do not reuse bond thresholds. For bond-level govt fits, Düring's gauge is the 7-15y spline spreads
   re-centred to zero each day: typically 1-2bp, with stress readings of 4-5.5bp (2010-11), about 9bp (2019 spike)
   and about 4.5bp (March 2020) (Düring, 2021, Figs 18.3-18.4, read from chart). That gauge belongs to
   [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md).
4. **Residual signal:** `e_τ,t = z_mkt − z_NS` in bp per tenor. Take a z-score over 250 days, and require
   mean-reversion half-life ≤ the intended holding period (see [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md)).
   Do not trade the betas directly. Betas are correlated through time, linear in zeros but non-linear in par
   instruments, and a 3-leg fly hedge would need beta-bump sensitivities plus their historical correlation (Düring,
   2021, Ch.31).
5. **Dynamics (Diebold-Li):** fit AR(1) per beta, `β_{t+h} = μ + φ^h(β_t − μ)`, and rebuild the forecast curve.
   `forward(h) − forecast(h)` is a crude premium proxy. It is unreliable beyond 1-2y because monthly yield
   autocorrelation is above 0.98 (Cassola & Luis, in Dunis, Laws & Naim, 2003). Use it for direction, not size.
6. NS is a smoother and an RV lens, never a pricing curve. Best-fit curves are "not good enough for trading ...
   where 0.25 basis points can make the difference" (Ametrano & Bianchetti, 2013). Price off the exact-fit curve from
   [fi-curve-construction](../fi-curve-construction/SKILL.md).

### 3. Short-rate models: Vasicek and Hull-White
1. Vasicek `dr = k(θ − r)dt + σdW`. `E[r_t] = r0·e^{−kt} + θ(1 − e^{−kt})`, half-life `ln2/k`,
   `f(t) = E^Q[r_t] − ½σ²B(t)²` with `B(t) = (1 − e^{−kt})/k`. `B(τ)` is the factor duration of the τ zero
   (`dP/P = −B·dr`). The forward-vol term structure is `σe^{−kt}`, always downward sloping. `θ = r∞ + λ/k`, so the
   fitted θ mixes the long-run rate and the risk premium and is not a neutral-rate estimate on its own.
2. **Vasicek as an RV tool** (Tuckman & Serrat, Wiley, 2022, Ch.9): calibrate r0, k and θ to the curve shape and
   factor-sensitivity shape, and σ to one implied vol (e.g. 10y). Each day reset r0 to match the market 10y, then read
   10-30y deviations as RV with model hedge ratios. It is too rigid for varied curve shapes, and one factor is not
   enough for 2-7y or for hedging one segment with another.
3. **Hull-White** `dr = [θ(t) − a·r]dt + σdW` fits today's curve exactly. Use it for consistent forward and option
   pricing, convexity and hedge ratios, not for curve rich/cheap. Calibration default: fix a ≈ 3% and solve σ to one
   ATM cap or swaption normal vol, because the joint (a, σ) minimum is unstable (West, 2010; Ametrano & Bianchetti,
   2013).
4. Futures-vs-forward convexity uses these parameters but lives in
   [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md). The convexity that belongs here is the
   `−½σ²B²` term inside forwards.
5. Reality check: Düring's daily-fitted Vasicek σ against UST implied vol gave R² < 0.1 (2014-19). A self-consistent
   calibration of rates and vol in a structural model is "very difficult". Never treat a curve-implied σ as a vol
   signal without checking it against options.

### 4. Gauss+ forward-rate RV (Tuckman & Serrat, 2022, Ch.9)
1. Cascade dynamics: r is pulled to m (policy, no shock), m to l (business cycle), and l to μ (long run, with the
   premium included). That gives 3 states but 2 shocks, which produces the hump-shaped vol curve. Equations,
   estimation steps and Table 9.1 parameters are in [model-formulas](references/model-formulas.md).
2. Estimate in stages on 8 years of daily zeros with an annual decay weight of 0.8. (a) Set r to the policy target.
   (b) Choose the α's so the model betas of zero-yield changes on Δ2y and Δ10y match OLS betas (e.g. 3y = 0.91·Δ2y +
   0.22·Δ10y; 15y = −0.20·Δ2y + 1.10·Δ10y). (c) Choose σ_m, σ_l and ρ to match the realised yield-vol term structure.
   (d) Choose μ by least squares on yield levels.
3. Daily: solve (m, l) so the 1y-rate-2y-forward and 1y-rate-10y-forward are fitted exactly. Then
   `fitting error e_τ = f_mkt(τ) − f_model(τ)` (bp) for every other 1y forward.
4. **Signal:** `s = MA5(e) − MA40(e)`. Receive forward τ if the demeaned error is > 0 (too high) **and** s < 0
   (convergence has started). Pay in the mirror case. Demean with a trailing mean (e.g. 1y) known at the decision
   date; a full-sample mean is look-ahead in a backtest. Speed of convergence is the key variable, because neighbours
   are often rich or cheap together and single errors persist.
5. **Neutralise factors.** An outright 9y forward carries large m and l exposure. Either pay and receive
   positively correlated errors (the 9y and 5y errors co-move, and the difference of their signals was strongly
   mean-reverting over 2017-22), or pool several trades sized to near-zero net m and l DV01.
6. Factor reading: m drives 2-3y forwards ("where policy will be in 2-3y"), and l peaks at 6-8y (the 7y forward
   moves 0.9bp per bp of l). Near the lower bound, m goes deeply negative and acts as a tradable "forward shadow
   rate". It rose steeply from early 2014, about two years before Fed hikes, so it worked as a leading indicator.

### 5. Expectations vs term premium
Run at least two of these and report the spread between them as the model uncertainty.
1. **Gauss+ long-forward identification.** Assume the true expected short rate is flat beyond ~14y. Then
   `λ_t = [f(15y) − f(14y)] / [RP(15y)/Δτ − RP(14y)/Δτ]`, where RP is the model's quantity of long-factor risk, and
   `E[r_τ] = f(τ) − λ_t·RP(τ)` (Tuckman & Serrat A9.28-A9.29). The book's worked example shows the convexity
   separately: `E = f + CX − TP`. Only the long factor earns a premium. The resulting TP often moves **against**
   rates: falling rates steepen the curve, and the model reads that as a higher premium.
2. **Gaussian affine with constant prices of risk.** `f_n = E[r_{t+n}] + Λ_n` with a constant Λ_n, so the premium
   cannot vary over time. First run the forward-rate regression
   `f_{n−1,t+1} − y_{1,t} = c + c_n(f_{n,t} − y_{1,t})` (H0: c_n = 1; Newey-West s.e., with lags at least the overlap if
   you sample more often than the one-period step). If c_n is near 1 (Bund 1986-98: 0.953-0.981), subtracting
   an average premium curve is acceptable. If c_n is clearly below 1, premia vary over time and you need an
   essentially-affine model (ACM/KW class).
3. **Published models (external).** ACM: regression-based affine model on principal components of Treasury yields,
   published daily for 1-10y. Kim-Wright: three-factor Gaussian affine fitted to yields plus survey short-rate
   forecasts. They are USD only. For other G10 curves, estimate your own (Gauss+ or affine on the OIS zero curve) or
   use proxies 4-5. Models disagree. After the Sept 2026 FOMC, 10y rose about 25bp, and the SF Fed model attributed
   about 16bp of that to term premium while ACM attributed nearly all of it (Barclays, Global Rates Weekly, 2 Oct
   2026). "Mechanical quantitative decompositions should be treated with great care" (Düring, 2021).
4. **Swap-based split** (Barclays method): `implied-rate TP(n) = OIS swap(n) − model-expected policy path(n)`, and
   `total TP = implied-rate TP + (govt − OIS)`. Judge it against the historical average slope from the policy rate
   to that tenor.
5. **Regression proxies** (fast, model-free residuals; label them "proxy"):
   - `1Yx1Y/5Yx5Y OIS curve = a + b·1Yx1Y` over the past 1y. The residual is "policy-adjusted term-premium
     steepness" (J.P. Morgan, Global Fixed Income Markets Weekly, 21 Aug 2026).
   - `5s30s = a + b·y5`, rolling 5y window, residual = TP proxy (Citi, Global Macro Strategy, 31 Jul 2026).
   - In practice slope changes track term-premium estimate changes closely (Willer & Saunders, 2026).
6. **Survey anchor:** `TP ≈ forward-implied change − survey-expected change`, which is valid where convexity is
   negligible (bills, short forwards). See worked example 4.
7. Convexity bias cannot be separated from expectations when policy is in play. Implied vol and expected moves rise
   together, so in 2s5s "delineating these two effects is practically impossible" (Düring, 2021). Report the
   decomposition with the vol level used for CX.

### 6. Lower bound: shadow rates
- Model the shadow rate as Vasicek, observe `max(SR, LB)`, and price as the average of `max(LB, SR_path)` over
  simulated paths. LB may differ by maturity (purchase-programme floors). Scenario: move LB (e.g. an ECB APP floor
  from −25bp to −50bp), re-simulate and read the 2s10s change (Huggins & Schaller, 2024, Ch.6).
- Estimation jumps between near-identical optima. Use the staged fix in [model-formulas](references/model-formulas.md).
  Shadow-rate curves give stable PCA eigenvectors at the bound, which feeds
  [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md), but shadow rates are not tradable.

### 7. G10 notes
- **USD:** daily published ACM/KW and the Fed's fitted Treasury zero curve exist. Use the policy target (fed funds)
  as r, not GC repo. Gauss+ parameters in the source are USD 2014-22.
- **EUR:** fit on €STR OIS or Bunds. The ECB publishes a daily AAA NSS curve, whose λs are very volatile. Shadow
  rates were essential in 2014-22: the EUR O/N shadow rate implied by the 1Y-10Y curve fell below −15% in 2014.
- **JPY:** ZIRP/YCC regimes distort loadings and vol. Prefer shadow-rate or lower-bound-aware models (external:
  Kim & Singleton, 2012), and expect term premium to rise steeply out the curve when the BoJ is seen as behind the
  curve (Goldman Sachs, Global Rates Trader, 2 Oct 2026; Citi, Global Macro Strategy, 7 Aug 2026).
- **GBP, CAD, AUD, NZD, CHF, SEK, NOK:** there is no official daily TP series. Estimate on the OIS zero curve. Where
  the liquid curve stops near 10-15y, the 14y/15y-forward identification is fragile, so lean on survey anchors and
  regression proxies. The level of the 1Yx1Y/5Yx5Y curve differs widely by market: USD 39, EUR 44, GBP 57, SEK 81,
  NOK −42, AUD 71, NZD 107, JPY 136bp (J.P. Morgan, 21 Aug 2026). Compare residuals within a market, not raw levels
  across markets.

## Worked examples
1. **Vasicek mechanics** (Wiley, Tuckman & Serrat, Fixed Income Securities 4th ed., 2022): r0 = 2%, k = 0.0165,
   θ = 11%, σ = 0.95%. Drift = 0.0165 × (11% − 2%) = 14.85bp/yr (about 1.2bp/month). Monthly shock s.d. =
   95 × √(1/12) = 27.4bp. Half-life = ln2/0.0165 = 42y. With λ = 0.125%, r∞ = θ − λ/k = 3.424%. Computed from the
   same parameters, the 10y forward convexity term is `½σ²B(10)² = ½ × 0.0095² × 9.22² ≈ 38bp`.
2. **Factor duration** (Pearson, Hull, Options, Futures and Other Derivatives 9th ed., Ch.31): a 4y zero has
   duration 4. With Vasicek a = 0.1, B(0,4) = (1 − e^{−0.4})/0.1 = 3.30, so a 10bp short-rate rise costs about 0.33%,
   not 0.40%.
3. **Gauss+ decomposition of the 10y forward** (Tuckman & Serrat, 2022, App. A9): λ = 0.09, long-factor loading of
   the 10y zero 0.7, σ_l ≈ 100bp. Risk premium ≈ 0.09 × 0.01 × 10 × 0.7 = 63bp, convexity ≈ 24bp. With a 3% 10y
   forward, `E[r] = 3% + 0.24% − 0.63% = 2.61%`. Over 2014-22 the model's long-run expected rate tracked a Cleveland
   Fed-based estimate (real-rate forecast plus long-run inflation). The gap between the two is an outright duration
   signal.
4. **Survey anchor** (Salomon Brothers, Ilmanen, Understanding the Yield Curve Part 6, Nov 1995): in Dec 1994,
   3m bills were at 5.70% and f(0.5, 0.75) at 7.51%, so the forward-implied change was 181bp. The survey expected
   6.60%, a change of 90bp. Risk premium = 181 − 90 = 91bp. By Jun 1995 it was 18bp, so the 1995 rally was largely a
   premium collapse.
5. **Swap-based term premium table** (Barclays, Global Rates Weekly, 2 Oct 2026). Columns: SOFR swap / model-expected
   FF / implied-rate TP / Tsy − SOFR / total TP vs historical average since 1985 (all %, as printed; rows can differ
   by 0.01 from the arithmetic because of rounding, e.g. 4.75 − 4.17 = 0.58 vs 0.57 printed).
   - 2y: 4.67 / 4.36 / 0.31 / 0.15 / 0.46 vs 0.34
   - 5y: 4.75 / 4.17 / 0.57 / 0.29 / 0.86 vs 0.85
   - 10y: 4.85 / 3.91 / 0.95 / 0.41 / 1.35 vs 1.31
   - 30y: 4.94 / 3.69 / 1.25 / 0.68 / 1.93 vs 1.78

   Reading: TP is within +1 to +15bp of its average, so duration risk is two-sided. The Tsy − SOFR leg is 0.41 at
   10y, i.e. a −41bp swap spread, and is a large part of the "term premium" in Treasury yields.
6. **Regression proxy, cross-market** (J.P. Morgan, Global Fixed Income Markets Weekly, 21 Aug 2026), fitting the
   1Yx1Y/5Yx5Y OIS curve (bp) on the 1Yx1Y level (%) over the past year:
   - USD: −72.46·x + 319.0 (R² 88%)
   - EUR: −70.7·x + 236.3 (91%)
   - GBP: −58.6·x + 301.5 (89%)

   All three were 10-20bp too steep after controlling for 1Yx1Y, a rise that started mid-July with Fed-credibility
   questions.
7. **NS sanity case** (illustrative, from the script's selftest): with λ = τ, the loadings are 1 − 1/e and 1 − 2/e.
   β = (4, −2, 1) gives z(λ) = 4 − 1.2642 + 0.2642 = 3.000%, z(0+) = 2%, z(∞) = 4%.

## Signals & interpretation
- **Gauss+ fitting error:** trade only when the demeaned error and the MA5 − MA40 crossover agree (step 4), and
  only as factor-neutral pairs or baskets. An error that is wide but still widening is not an entry.
- **NS residual:** |z| ≥ 2 on a 250-day window and half-life ≤ the holding period (house defaults: one year of
  history covers a policy cycle phase, and 2σ keeps the screen to a handful of tenors), plus that day's curve MAD
  below the 95th percentile of its trailing year (step 3).
  Residuals at 25-50y that show ultra-longs "overvalued" are usually the convexity-driven inversion beyond 25-30y,
  which is a model shortcoming, "not a real trading opportunity" (Düring, 2021).
- **Term premium level:** compare with the method's own history, not with other models. Barclays called deviations
  of +1 to +15bp from the post-1985 average "near historical average", i.e. two-sided duration risk (2 Oct 2026).
  The NY Fed estimate averaged about 1.3pp in the decade to summer 2007 (FT Alphaville, 20 Aug 2026), a regime
  anchor rather than a target.
- **Policy vs premium attribution:** twist steepening (front end down, long end up) means the move was "almost
  fully term premium driven" (Citi, US Rates Weekly, 21 Aug 2026). Bear steepening with the expected path unchanged
  is premium. Moves in the 1Yx1Y area are path. Route the trade accordingly. Premium views go to the long end and
  [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md). Path views go to
  [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md).
- **Market-implied vs fundamental long-run rate** (model E[r_10] vs a survey or real-rate-plus-trend-inflation
  estimate): the gap is an outright duration view (Tuckman & Serrat). House default trigger: the gap is more than one
  standard deviation from its own 5y mean. Size it as macro, not RV.
- **Cross-asset:** a 1-month rise of more than 10bp in the Kim-Wright premium has coincided with a negative S&P 500
  information ratio (−0.20), and this has worked again since 2015 (Willer & Saunders, Trading Global Macro Markets,
  2026). It is useful as a risk-off flag for RV books.

## Pitfalls
- **Treating TP as data.** It is a model output under an identifying assumption (flat long expectations, constant
  or affine prices of risk, survey accuracy). A "risk premium" defined as a fair-value residual `r = f(φ) + ε` is
  "the things one does not know" (Düring, 2021). Use changes, cross-check two methods, and show the model spread.
- **Negative TP is not a bug.** Tuckman & Serrat's sample-average price of risk (λ = 0.09) is low against typical
  Sharpe ratios because bonds hedged risky assets, so a low or negative premium is expected in that regime.
- **Mode vs mean.** Forwards price the mean of the rate distribution, not the modal policy path. A right-skewed
  distribution (sharp hikes possible, cuts floored) lifts forwards above the modal path, so "OIS − expected path"
  includes this skew as well as premium (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022).
- **Hull-White residuals.** HW fits by construction, so a zero residual means nothing. Rich/cheap needs a model that
  does not fit exactly.
- **Constant-premium Gaussian models** cannot produce a time-varying TP. Run the c_n test before reading one.
- **Persistent misfits.** Securities are often persistently rich or cheap to a model, and neighbours move together.
  Trade convergence (step 4), not level.
- **Parameter instability.** NS λ, shadow-rate optima and Kalman-ML estimates jump. Suspiciously small Kalman
  standard errors signal sensitivity, not precision. Freeze slow parameters and refit only fast states daily.
- **Wrong short rate.** Use the policy target or the RFR, not GC repo, because repo spikes are unrelated to policy
  expectations. For EUR, the policy-rate-to-€STR mapping depends on the liquidity regime (floor vs corridor).
- **Regime breaks.** ZIRP, forward guidance and YCC change loadings, not just factor levels. For US PCA-style
  loadings, Huggins & Schaller recommend data from 2022 onward. Re-estimate after a regime change instead of
  extending the window. Inflation-shock persistence also differs by era, so long-history VARs mislead about
  expectations (Düring, 2021, Ch.20).
- **Instrument mix.** Don't compare an OIS-based TP with a Treasury-based ACM number without adding the swap spread.
  Don't fit BTP/OAT curves and call the credit premium "term premium".
- **Look-ahead.** Estimate parameters on data available at the decision date (expanding or rolling window). Store
  published model series as vintages, because they can be revised.
- **σ from the curve.** Curve-implied σ (from forward convexity) contains term premium too. Don't sell vol because a
  curve-fitted σ is above implied.

## Output
1. **Decomposition table**, one row per point (2y, 5y, 10y, 30y yields; 1y1y, 5y5y, 10y10y forwards). Columns:
   `date, curve_id, point, yield_or_fwd, market_pct, exp_path_pct, tp_bp, cx_bp, method, identifying_assumption,
   chg_1w_bp, chg_1m_bp, chg_since_event_bp`. Run at least two methods, plus a `model_spread_bp` column.
2. **Model RV table**: `date, curve_id, model, model_version, point, market_pct, model_pct, resid_bp, resid_z,
   half_life_d, signal (e.g. MA5 − MA40), factor_dv01 (per factor), suggested_hedge`.
3. **Signals rows** for the `signals` table (`unit = bp`, `strategy_id` such as `tsm_ns_resid` or `tsm_gplus_fe`),
   dated with the data available at the snap.
4. **Charts**: NS betas and daily MAD; residual by tenor (latest vs ±2σ band); TP history by method on one axis;
   E[r_10] vs the survey or trend-inflation anchor.
5. A one-paragraph verdict: path or premium, which model, how confident, the cross-check, and what would change it.
   Hand off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) for anything tradeable.

## Scripts
- [`scripts/nelson_siegel.py`](scripts/nelson_siegel.py): fixed-λ NS/NSS fit per date from `curve_zero` (DFs → zeros)
  or spot `curve_par`. Outputs `<out>_betas.csv` (betas, RMSE, MAD) and `<out>_resid.csv` (market − model, bp).
  Options: `--grid` for a pooled λ choice, `--lam2` for NSS, `--forecast-h` for Diebold-Li AR(1) beta forecasts.
  `--grid` uses the whole input sample. For backtests, choose λ on a training window and pass it with `--lam`.
  Pass `--snap` when the file holds several snaps (the script refuses to pool them).
  `python scripts/nelson_siegel.py --help`. `--selftest` checks analytic loadings (1 − 1/e, 1 − 2/e), limits,
  recovery of betas from independently integrated forwards, λ grid recovery, residual sign and AR(1) forecasts.

## Related skills
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical `curve_zero`, `curve_par`, `macro_series` tables
- [fi-curve-construction](../fi-curve-construction/SKILL.md): exact-fit OIS/govt zero curves that feed every model here
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): factor DV01 sign conventions and risk mapping for hedges
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): data-chosen loadings vs NS's imposed ones; shadow-rate PCA
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): the forward grid where Gauss+ fitting errors are traded
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): bond-level spline/NSS rich/cheap
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): why term premium moves (supply, fiscal, QT)
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): expected path at the front end
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures vs forward convexity with HW/Ho-Lee
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): convexity value in long forwards and flies
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): ATM normal vols used to calibrate short-rate σ
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): the expected policy path and survey anchors
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): the "expectations realised" carry scenario needs this decomposition
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life of residuals and fitting errors
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): Kalman/state-space, VAR, Newey-West
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro-regression fair value, the non-structural alternative
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): real vs inflation premia
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): write-up of any resulting trade
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weighting, residuals and sizing.

## References
- Bruce Tuckman & Angel Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022), Ch.9 and App. A8-A9: Vasicek, Gauss+ estimation, fitting-error RV signal, term-premium extraction (63/24bp example)
- Doug Huggins & Christian Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024), Ch.3 and Ch.6: single vs local models, shadow-rate model and estimation fix, factor-model categories
- Alexander Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021), Ch.18-20 and Ch.31: NS/NSS and Vasicek spline, spline-dispersion liquidity gauge, four curve drivers, convexity bias, NS parameter instability
- John C. Hull - Options, Futures, and Other Derivatives (9th ed., Pearson), Ch.31: Vasicek, CIR, Ho-Lee, Hull-White, BK closed forms and examples
- Nuno Cassola & Jorge Barros Luis - Gaussian affine term-structure models of the German yield curve, in Dunis, Laws & Naim (eds), Applied Quantitative Methods for Trading and Investment (Wiley, 2003): affine term premium, forward-regression EH test, Kalman estimation
- Salomon Brothers, Antti Ilmanen & Raymond Iwanowski - Understanding the Yield Curve, Part 7 (Feb 1996): forward = expectations + premium − convexity, model survey, CKLS level dependence
- Salomon Brothers, Antti Ilmanen - Understanding the Yield Curve, Part 6 (Nov 1995): survey-vs-forward premium table
- Barclays Research - Global Rates Weekly: The urgency question (2 Oct 2026): swap-based term-premium table, SF Fed vs ACM attribution
- J.P. Morgan - Global Fixed Income Markets Weekly: Reduce outright duration risk but keep long 10Y Eur vs. US (21-22 Aug 2026): 1Yx1Y/5Yx5Y-on-1Yx1Y regressions across G10
- Citi Research - Global Macro Strategy: The Messi Theory of Interest Rates (31 Jul 2026): 5s30s-on-5y residual as TP proxy
- Citi Research - US Rates Weekly: Can Secretary Bessent and Chair Warsh save the curve? (21 Aug 2026): twist steepening as a term-premium signal
- Dirk Willer & Alex Saunders - Trading Global Macro Markets (Wiley, 2026): slope ≈ TP changes, Kim-Wright TP vs equities
- Goldman Sachs - Global Rates Trader: Reaching Limits (2 Oct 2026): G10 10y term-premium monitor, JPY premium rising out the curve
- Citi Research - Global Macro Strategy: Macro tapas: running with the bulls; should rates scare us? (7 Aug 2026): JPY weakness tied to rising Japan term premium
- Doug Huggins & Christian Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): Hull-White with meeting-date jumps
- Ferdinando Ametrano & Marco Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping (SSRN, 2013): best-fit vs exact-fit, HW parameters
- Graeme West - Interest Rate Derivatives: Lecture notes (Financial Modelling Agency, 2010): HW calibration with fixed mean reversion
- BofA Global Research - UST RV Primer: A hitchhiker's guide to RV on the UST curve (2 May 2022): NS/NSS forward form, par-yield formula
- FT Alphaville - Treasury demand has become materially more valuation-sensitive (20 Aug 2026): NY Fed TP history anchor, model caveats
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): curve-shape drivers, mean vs mode of the rate distribution
- Michael Brenndoerfer - Advanced Interest Rate Models: HJM and LMM (Quantitative Finance handbook, Dec 2025): HJM drift condition, Ho-Lee/HW forward vols
- FINCAD Quantitative Research, Jonathan Rosen - Averaged Overnight Rate Futures: Convexity Adjustment (Mar 2019): Vasicek 65bp vol, 3% reversion example (after Henrard)
- Quantitative Finance Stack Exchange - "SOFR futures options" (Jul 2023): HW calibrated to ATM normal vol for futures convexity
- Nelson & Siegel (1987), Parsimonious Modeling of Yield Curves, Journal of Business; Svensson (1994), NBER WP 4871 (external): NS and NSS forms
- Diebold & Li (2006), Forecasting the Term Structure of Government Bond Yields, Journal of Econometrics 130 (external): fixed λ = 0.0609, AR(1) factor dynamics
- Adrian, Crump & Moench (2013), Pricing the Term Structure with Linear Regressions, Journal of Financial Economics 110(1) (external): ACM term premium
- Kim & Wright (2005), An Arbitrage-Free Three-Factor Term Structure Model and the Recent Behavior of Long-Term Yields and Distant-Horizon Forward Rates, Federal Reserve FEDS 2005-33 (external): survey-anchored affine TP
- Kim & Singleton (2012), Term Structure Models and the Zero Bound: An Investigation of Japanese Yields, Journal of Econometrics 170 (external): lower-bound models for JGBs
