---
name: macro-inflation-and-energy-drivers
description: 'Turns energy and commodity moves (Brent, WTI, diesel, gasoline, TTF gas, freight, wheat) into inflation paths and rate implications. Covers energy-weight pass-through, CPI/PPI-to-core-PCE nowcasts, median and trimmed-mean cores with skew bias, market-implied CPI from fixings and ZC swaps, breakeven and real-rate decomposition, and oil days-of-cover. Use when nowcasting PCE or HICP, judging how an oil or diesel shock hits headline vs core or front-end breakevens, reading CPI fixings or inflation swaps, checking whether a robust core reading is trustworthy, or assessing a PCE methodology revision. Triggers: Brent, WTI, diesel, crack spread, 3-2-1 crack, TTF, pass-through, energy weight, headline vs core, PCE nowcast, trimmed mean, median CPI, skewness bias, CPI fixing, ZCIS, days of cover, HICP. Breakeven and linker valuation: infl-breakevens-and-linkers; war and sanctions: macro-geopolitical-risk.'
---

# Macro inflation and energy drivers

Energy is the fastest input to headline inflation. It reaches core later, through freight, inputs and PPI. Oil and
gas enter CPI and HICP directly (gasoline, fuel oil, electricity, gas), then through diesel into goods prices, then
through PPI into core. This skill turns an energy move into an inflation path, then compares that path with what
fixings, inflation swaps and robust measures already price. The two errors it guards against are reading a headline
spike as core, and reading a robust-core trough as disinflation while the price distribution is skewed.

## When to use

- Converting an oil, gas, diesel or freight move into a headline or core CPI, HICP or PCE path, in m/m and y/y bp.
- Nowcasting core PCE from CPI and PPI components before the BEA release.
- Deciding whether a median or trimmed-mean core reading is usable, given the skew of price changes.
- Comparing market-implied CPI (CPI fixings, zero-coupon inflation swaps) with an economist's path.
- Judging whether an energy move belongs in front-end breakevens, UK RPI or EUR HICP forwards.
- Deciding if a statistical methodology change (BEA PCE revisions, UK RPI/CPI wedge) is a level shift or a trend shift.
- Building oil or gas scenarios to map onto a central bank's own threshold. The reaction function itself lives in
  [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md).

Not for breakeven and linker RV mechanics ([infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md)),
regime labels ([macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md)), or central bank
text ([macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md)).

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Index levels (NSA) for CPI, HICP, RPI, PCE-related series, with release vintages | `infl_fixings` | monthly, >= 5y | Use `is_first_release` for fixing comparisons; keep revisions |
| Seasonal factors (12 values, % deviation from trend) | `infl_seasonals` | per fit | Use only after `valid_from` |
| Zero-coupon inflation swap rates by index and tenor | `infl_swaps` | daily EOD, 1y to 30y | `index_lag_months` and `base_month` needed for index ratios |
| Nominal swap curve (par or zero) | `curve_par`, `curve_zero` | daily | Needed for real rates and forwards |
| Linker quotes | `bond_quotes` | daily | For bond breakevens (linker vs nominal yield) |
| Component CPI/PPI releases with consensus | `macro_series` | monthly, per vintage | `consensus` column for surprises |
| Brent, WTI, RBOB, ULSD, TTF, freight, wheat prices | `macro_series` | daily or weekly | The unit vocabulary has no $/bbl or EUR/MWh entry. Flag to the data-contract owner before use |
| Inventories, refinery runs, demand proxies | `macro_series` | weekly or monthly | Stock units must be stated in the row |
| Category price-change distribution (for skew) | not in the canonical tables | monthly, category-level with weights | Use the published skew or median/trimmed series from `macro_series` if category data is absent |
| Energy, food and transport weights; PCE category weights | `macro_series` (`ratio` unit) or user-supplied | annual | Weights change with the statistics office's update cycle |
| Central bank scenario paths (oil, gas) | user-supplied | per publication | Never invent a path |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values, and never fill a
gap with a number from a reference in this skill.

## Method

### Step 1. Units and compounding

- Index levels in `index`. Monthly changes in percent. 1 bp = 0.01 pp.
- Year-on-year is compounded, not summed: `y/y_t = prod_{k=0..11}(1 + m_{t-k}) - 1`. Summing monthly prints
  overstates y/y after a large month.
- Crude and products in $/bbl. RBOB and ULSD are quoted $/gal: multiply by 42 gal/bbl before taking a crack.
  European gas in EUR/MWh.

### Step 2. Direct energy channel (headline)

    dPi_headline,t ~ w_E,t * e_t          (m/m, percentage points)

`w_E` is the energy share of the CPI or HICP basket in force for that month; `e` is the energy index's m/m change.
The share is a beta: countries with a larger energy share get a larger headline response to an energy move. The
screen in the source puts the global average near 10%, with CH, AU and NO near 5% and CEEMEA most sensitive
(JWS, Iran and Front-End Rates, 8 Mar 2026). In the US, gasoline dominates monthly CPI energy volatility; diesel
enters CPI only through fuel oil and other motor fuels (Barclays, US Energy and Inflation, 1 Oct 2026).

**Linear oil rule.** A $10 Brent move is about 30bp on near-term y/y euro-area HICP (JWS, 8 Mar 2026). Use it for
small moves over a few months only. The same source reprices a $70 to $90 move at 70-85bp, against 60bp from the
linear rule for +$20. The note does not explain the gap, so do not extend the linear rule to multi-month paths
without stating a timing assumption.

**Level vs rate.** A one-off energy level jump lifts y/y for 12 months, then drops out. It changes the trend only
if it persists. Inventories and contract resets absorb short spikes, so persistence matters more than peak (Barclays,
1 Oct 2026; JWS Outlook #4, 8 Apr 2026).

### Step 3. Pass-through lags

The chain is oil to PPI to headline CPI to core CPI, with the core link delayed (Willer & Saunders, Trading Global
Macro Markets, Ch.3, 2026). In the 2026 episode, PPI was soft in the month oil first rose, and the strength
appeared in the next two months (Citi, Details of PPI, 13 Aug 2026).

The sources do not quantify the core lag. Analyst default (not sourced): model core as a decaying share of the
headline shock, with the lag tested at 3, 6 and 9 months, and state which one was used.

### Step 4. Diesel and freight chain

Barclays (US Energy and Inflation, 1 Oct 2026) uses three steps:

1. Freight exposure, from two lenses. Lens 1 is the transport margin as a share of purchaser value (BEA bridge):
   food-at-home 1.5-2.0%, motor fuels 2.5-3.5%, furnishings and durables 4-5%. Lens 2 is upstream freight intensity
   from the Leontief inverse of BEA input-output: food-at-home about 7.2%.
2. Diesel share of carrier operating cost: trucking 20-30%, rail 10-20%, water 10-20%, courier 15-20%, airlines about
   one-third.
3. Consumer pass-through, attenuated by margins, inventories, sourcing and contracts.

Generic form (derived; the source does not print this equation): for category c,
`dP_c ~ rho * F_c * s_d * dDiesel`, with `F_c` the freight share from the chosen lens, `s_d` the diesel share of
carrier cost, and `rho` the pass-through. The headline effect is the weight-averaged sum over categories.

Use the source's outputs for an 80% diesel shock, cumulative price level, rather than rebuilding the sum without
full category weights (see the worked example in Section 3 below and `references/energy-and-cover.md`).

Regression check: regress monthly NSA CPI component changes on diesel changes at lags 0-3. Orthogonalise diesel
against crude and gasoline first, and control for GSCPI. A naive CPI-on-diesel regression mostly measures oil
volatility.

### Step 5. Robust cores (median, trimmed mean)

Definitions. Median is the 50th percentile of the weighted price-change distribution. Trimmed mean drops a fixed share
of each tail. Dallas Fed trims 24% from the bottom and 31% from the top of PCE; Cleveland Fed trims 8% from each
tail of CPI.

Skewness. Cleveland's measure is a weighted average of Bowley `B = (Q3 + Q1 - 2*Q2)/(Q3 - Q1)` and Kelly
`K = (P90 + P10 - 2*P50)/(P90 - P10)` (standard definitions), bounded in [-1, +1], taken as a one-sided 12-month
moving average. Positive skew means a long right tail of large price rises. Use the published skew series unless you
have the category weights.

Bias and adjustment (Cleveland Fed, Economic Commentary 2022-05, Mar 2022):

    g_t      = median_t - headline_t                (same for trimmed mean)
    bias_t   = centred 36-month average of g_t, dropping its highest and lowest value
    bias_t  ~ alpha + beta * skew_t                 (Jun 1986 - May 2020, HAC, 3 lags)
    median:       alpha = 0.20,  beta = -2.01,  R2 0.48
    trimmed mean: alpha = -0.10, beta = -1.38,  R2 0.38
    adjusted      pi_adj = pi - (alpha + beta * skew)

For the median this is `pi - 0.20 + 2.01 * skew`. Sign logic: right skew (positive) biases the median and trimmed
mean down, so the adjustment is upward. Left skew biases the median up.

Sensitivity (derived from the coefficients): each 0.1 of skew moves the adjusted median by about 0.20pp, and the
adjusted trimmed mean by about 0.14pp.

Convergence test (Dallas Fed, Skewness warrants caution..., 16 Apr 2026). For h = 1..24 months, regress the change in
12-month headline PCE on the core and trimmed-mean gaps to headline, with lags. A coefficient near 1 means headline
converges to that measure. The trimmed-mean coefficient reaches about 1 after 12 months in the full sample, but is
about 0 in positive-skew periods. A trimmed-mean trough in positive skew is therefore not a reliable disinflation
signal.

Lead-lag (JPMorgan, Lags in robust PCE cores, 13 Aug 2026). Robust measures lag headline and core by about 6-8 months
in the 2022-2026 sample (median 8 vs headline, 6 vs core; trimmed mean 7 vs headline, 6 vs core). They show a shock
only after the tails move.

### Step 6. PCE nowcast from components

PCE is a chained Fisher index: `I_t = I_{t-1} * sqrt(L_t * P_t)`, with L the Laspeyres and P the Paasche ratio of
the two adjacent periods (BEA, PCE Price Index Details; the source deck's formula is garbled, so the standard Fisher
form is used). Weights come from business surveys and change more often than CPI weights.

Core PCE m/m is approximately `sum_k omega_k * m_k`, where `omega_k` is the category's core PCE weight and `m_k` its
mapped change. PPI supplies several PCE categories: portfolio-management fees, airfares, medical services, and
computer software and accessories. Everything else maps from CPI (Citi, Details of PPI, 13 Aug 2026; JPMorgan, US
Economics, 14 Aug 2026). The notes do not print the full mapping, so state which mapping and which weights you used.

**Asset-price link.** Portfolio-management fees are treated as inflation when assets under management move. Using
the July 2026 example in Section 3 gives an effective core-PCE weight of about 1.8-2.0%. At that weight, a 10%
AUM-driven move adds about 18-20bp to core PCE m/m if the fee tracks AUM one-for-one (derived; check against the
current BEA weight).

### Step 7. Market-implied CPI

**Fixing to m/m.** NSA m/m is `I_t / I_{t-1} - 1`. The seasonal part of NSA m/m is about `s_m - s_{m-1}` (derived),
with `s` from `infl_seasonals` in % deviation from trend, so `SA m/m ~ NSA m/m - (s_m - s_{m-1})`. Use the month-on-month
difference, not the level of the factor. Euro-area HICPxT: January factor about -0.7 vs December 0, so a weak NSA
January is not news. US CPI: the chart reads give -0.55 (Jan) vs -0.7 (Dec), a seasonal m/m of about +0.15pp, so a
US January NSA print is flattered, not depressed (Duering, Ch.23; chart reads, use the official set).

**Implied core (method outline).** Strip the energy and food contributions the economist assumes, then divide by the
core weight (generic form; Citi's method is described in outline only, Citi, US Economics, 21 Aug 2026):

    core_implied_m/m = (headline_SA_m/m - w_E * E_SA_m/m - w_F * F_SA_m/m) / w_C

Compare `core_implied` with the economist's core forecast. Market and Citi readings differed by 0.04-0.2pp m/m in
the August 2026 notes.

**Zero-coupon forwards.** Standard definitions:

    1y1y = (1 + ZC_2y)^2 / (1 + ZC_1y) - 1
    5y5y = [(1 + ZC_10y)^10 / (1 + ZC_5y)^5]^(1/5) - 1

Read 5y5y as a credibility gauge, not a growth gauge: a falling 5y5y implies the central bank will hike (JWS Outlook
#4, 8 Apr 2026). Higher realised inflation lowers the forward for a given credibility level.

**Stripping an implied CPI path.** From ZC tenors, derive today's curve vs a pre-shock curve, the implied NSA index
path, and the forward 1y inflation sequence. Pre-shock minus post-shock fixings gives the accumulated price-level
effect (JWS Outlook #4, 8 Apr 2026: implied CPI about 1% higher by 2028, accumulated gap peaking around 2030).

### Step 8. Breakevens, real rates and linkers

- Breakeven: `BE ~ nominal - real`, or exactly `BE = (1 + n) / (1 + r) - 1` (standard Fisher).
- Real rate from swaps: real swap = nominal swap - ZC inflation swap at the same tenor. Prefer it to TIPS real
  yields when swap-spread distortion is large (JPMorgan Monthly Inflation Outlook, 13 Aug 2026).
- US TIPS index ratio (standard; US Treasury, TIPS Handbook): `IR = I_ref / I_base`, with `I_ref` the CPI-U NSA
  lagged three months and interpolated linearly by day: `I_ref(d) = CPI(M-3) + (d-1)/D_M * (CPI(M-2) - CPI(M-3))`.
  Other markets use different lags and floors; check the market's conventions in
  [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md).
- Compare breakevens only after seasonal adjustment and at a matched index lag (Duering, Ch.23). A raw breakeven from
  a different index month is not comparable.
- Energy beta: 1-month rolling partial betas of 1Yx1Y, 2Yx3Y, 5Yx5Y and 10Yx20Y inflation swaps to a commodity index,
  controlling for the OIS curve and VIX level (JPMorgan Monthly Inflation Outlook, 13 Aug 2026). Front-end betas have fallen and converged with
  the belly and long end. Betas are regime-dependent, so re-estimate before sizing.
- Linker asset swap: buy linker, pay fixed nominal swap, pay inflation on the ZC swap. This is the source of inflation-
  payer flow (Duering, Ch.23).
- Consumption-tax and other administered changes are mechanical: effect = `weight * (P_new / P_old - 1)` (Section 3).

### Step 9. Oil supply stress

- Crack spread: product minus crude. The 3-2-1 crack (standard convention) is `(2 * RBOB + ULSD) / 3 - WTI`, in $/bbl.
- All-in oil cost = crude + refinery cracks weighted by the product yield (Citi, Oil Monitor, 19 Aug 2026).
- Days of cover: `cover_days = inventory / demand_per_day`. Extrapolate observed draws linearly as a range, not a
  point. Citi's observed draws were about -2.9 mb/d over Feb-Aug 2026 (519m bbl, about -87m bbl per month). That gave
  OECD cover of 83 days in Aug-26 falling to about 70 by end-2027 (Citi, Oil Monitor, 19 Aug 2026). The authors call
  the timeline "more prudent" because draws are partly unobserved and the IEA release has ended.
- 70 days is the 1970s-80s reference (energy about 8% of GDP). Citi equates 70 days with an all-in price above $200/bbl.

## Worked examples

**1. July 2026 core PCE nowcast (sources as reported).** Core CPI +0.215% m/m (Citi, Benign details of benign core CPI,
12 Aug 2026). Core PCE after CPI 0.15%, after PPI 0.21% (Citi Flash, 12 and 13 Aug 2026). JPMorgan's mapping gives
+0.3% m/m. Portfolio-management PPI +6.5% added 12-13bp. Derived: effective weight `0.12/6.5` to `0.13/6.5`, about
1.8-2.0%. Record which mapping you used. The 0.09pp spread between houses shows the mapping is not unique.

**2. Robust-core adjustment and a consistency check.** At skew 0.2: median adjustment `-0.20 + 2.01*0.2 = +0.20pp`;
trimmed mean `+0.10 + 1.38*0.2 = +0.38pp`. Cross-check (derived): Cleveland's Dec-2021 adjustments were +14bp (median,
to 3.75%) and +34bp (trimmed mean, to 3.39%). They imply skew of about 0.17 in both cases (`0.34/2.01` and
`0.24/1.38`), so the two coefficient sets are internally consistent. Recent check: core PCE 3.4% y/y, median 2.8%,
trimmed mean 2.3% in July 2026 (JPMorgan, Lags in robust PCE cores, 13 Aug 2026). The trimmed mean is 1.1pp below headline core, a gap to read
with the skew sign before any disinflation call.

**3. 80% diesel shock, sustained (Barclays, 1 Oct 2026).** Cumulative price-level effect:

| Case | Pass-through | Cost shares | Headline PCE | Core PCE |
|---|---|---|---|---|
| Low | 50% | low end | +0.12pp | +0.10pp |
| Mid | 75% | midpoints | +0.20pp | +0.15pp |
| High | 100% | top of ranges | +0.31pp | +0.23pp |

Authors lean mid-to-upper: headline 20-30bp, core 15-20bp, mostly in 2027.

**4. CPI fixings check (JWS Update #7, 19 Jul 2026; Citi, US Economics, 14 and 21 Aug 2026).** The July 2026 CPI fixing
at 333.95/96 was flat on June (0.0% NSA) despite gasoline up about 15% since mid-June. The source judges it mispriced,
because retail gasoline lags wholesale futures. Market-implied core m/m ran 0.20 to 0.39 in the
Citi table against Citi's 0.13 to 0.18. Market headline CPI y/y was 2.6% for Mar-27 against Citi's 2.1% (21 Aug 2026
table; the 14 Aug table gives 2.5% against 2.1%).

**5. Core run-rate arithmetic (derived).** An ex-energy proxy of 18-23bp m/m for nine of the next eleven months
(Barclays, 1 Oct 2026) is `(1.0018)^12 - 1` to `(1.0023)^12 - 1`, about 2.2-2.8% annualised before any seasonal adjustment.
Compare that with the core forecast's y/y path, not with the monthly print alone.

**6. PCE methodology revision (Citi, US Economics, 21 Aug 2026).** A -25bp midpoint revision moves 3.249% to about
3.00%. Rounding trap: 3.249 rounds to 3.2 at one decimal, not 3.3. The source says it "could print 3.3%". Confirm the
unrounded figure and vintage. A revision of -20 to -30bp can also move a print across a rounding boundary.

**7. Consumption-tax cut (Japan, JPMorgan Monthly Inflation Outlook, 13 Aug 2026).** Food consumption tax from 8% to 1%
in April 2027. Core CPI effect: `0.201 * (101/108 - 1) = -1.3pp` (20.1% is the source's weight of the taxed items in
core CPI; use the weight of the items actually taxed).

**8. Oil cover arithmetic (Citi, Oil Monitor, 19 Aug 2026).** Observed global draws 519m bbl over Feb-Aug 2026: about
87m bbl per month, or 2.9 mb/d over 30 days. The source's OECD path (83 days in Aug-26, about 70 by end-2027, 58 by
4Q28E) is roughly linear at about 0.8 day per month. It cannot be reproduced from the 2.9 mb/d global draw without OECD
demand and the OECD share of draws, which the notes do not give. Quote the path as the source's, and run
`cover(T) = (S_0 - r*T)/D` yourself with stated `S_0`, `r`, `D`.

## Signals & interpretation

- **Robust core, sign first.** If skew is positive (use the sign from the cross-section), do not read a trimmed-mean
  trough as disinflation. Use the skew-adjusted median instead. Flag when `|skew| > 0.1`: each 0.1 moves the adjusted
  median by about 0.2pp.
- **Market vs economist gap.** Analyst default (not from the source): flag when the market-implied core m/m and the
  economist's core forecast differ by more than 5bp for two consecutive months. The source's Citi-vs-market gaps
  were larger, mostly in spring 2027.
- **Energy pass-through confirmation.** Before you call a second-round effect, check three things: PPI energy
  pass-through lagged 1-2 months, core goods price changes after diesel moves (regression above), and whether the
  fixing curve prices any core increase. The source found no second-round effect priced in the fixings after May
  2026: only 0.1-0.2% m/m SA from May (JWS Outlook #4).
- **Oil volatility.** Rising oil volatility raises hike pricing in proportion to oil shocks. A volatile oil path matters
  for the front end even when the average is unchanged (BofA, Fog of War, 2 Oct 2026).
- **Commodity inflation regime.** Long commodities when CPI is above 3% and above its five-month moving average
  (Willer & Saunders, Ch.14). Information ratio 0.32 to 0.66; active 22% of the time. The rule breaks in high-
  inflation cycles, so treat it as a filter, not a model.
- **Cover thresholds.** OECD cover of about 70 days is the level the source uses as a stress reference. Product
  cracks above spot oil are the earlier stress sign (Citi, FX Forecasts, 20 Aug 2026).
- **Breakeven carry.** Carry below -9bp was a contrarian signal for breakeven widening over five years (JPMorgan
  Monthly Inflation Outlook, 13 Aug 2026). The carry definition is not in the notes. Check it before use.

## Pitfalls

- **Robust measures lag.** They react after the tails move. A trough in a robust core during positive skew can be a
  lagged signal, not a turn.
- **Methodology changes are level shifts.** BEA's portfolio-management, software and legal changes lower the core PCE
  y/y by about 20-30bp from the August data, not the trend (Citi, 17 Aug 2026; BofA, 2 Oct 2026). Do not read them as
  disinflation, and check whether the SEP includes the revision.
- **Fee linkage makes core PCE track markets.** A hawkish core PCE print can be an equity-fee print. Check the
  component before trading it (JPMorgan, 14 Aug 2026).
- **Core CPI does not map one-for-one to core PCE.** Build the PCE estimate from components. July 2026 core CPI
  0.22% m/m mapped to PCE between 0.21% and 0.30% depending on the house.
- **Linear draw extrapolation overstates precision.** Use it for a range of dates, not a point.
- **Aggregate cover hides product shortages.** Track product stocks and cracks separately.
- **Headline HICP base effects.** Negative base effects can lift headline y/y while core is steady. The euro-area
  flash case is an example (Citi, Week Ahead, 21 Aug 2026).
- **Fixings are NSA; comparisons are often SA.** Convert with the seasonal set before comparing with an SA forecast.
  A raw fixing comparison without seasonal adjustment adds no precision.
- **Units in the source are not always stated.** The UK 1Yx1Y RPI model (`0.3*SONIA - 0.0001*Brent + 0.004*Gas + 1.94`,
  R2 87%, SE 8bp) has coefficients whose result depends on the Brent and gas units, which the source does not state.
  Do not use it without them.
- **Crude-grade cut-offs are inconsistent.** The source's taxonomy uses 0.5% sulfur; the refining grid uses 0.7%.
- **Chart reads are approximate.** Refinery yields and seasonal factors are read from scans or charts. Use the official
  set for any model.
- **Dated anchors go stale.** Oil and gas paths in the references change weekly. Re-read the cited note before use.
- **China import data.** The WSJ's 48.9% cut does not match 5.8 mb/d from 11 mb/d (52.7%). Verify the base before use.
- **Consensus vs repricing.** Do not assume a central bank cannot move because consensus says a shock is a supply
  shock. Reaction-function risk exists (JWS #3, 8 Mar 2026).

## Output

Return one table per request, plus a short narrative.

| Column | Content |
|---|---|
| `as_of` | Date and vintage of every input used |
| `series` | Headline, core, ex-energy, or robust core (median or trimmed mean) |
| `m_m_pct`, `y_y_pct` | Forecast or implied path, compounded |
| `energy_path` | Brent $/bbl or gas EUR/MWh, and the source of the path |
| `pass_through` | Energy weight used; diesel case (low, mid, high); core lag assumed |
| `market_implied` | Fixing or swap-implied value, and its seasonal basis |
| `gap_bp` | Market-implied minus model, in bp |
| `flags` | Skew sign and size; methodology change in window; rounding boundary; unit gaps in inputs |

Narrative (three lines): what is priced, what the model implies, what would change the view. If the output supports an
RV idea (for example a breakeven or front-end trade), hand off to
[rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) with the trigger levels and the data vintages.

## Related skills

- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): breakeven and linker RV mechanics, index ratios, real-rate trades.
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): how central banks respond to energy and inflation shocks.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): regime labels and scenario trees that use these inflation paths.
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): supply-disruption events that move oil and gas.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): fair-value regressions for breakevens and forwards.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): what the front end prices for policy.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): seasonal adjustment of inflation prints.
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag tests used for the robust-core and headline timing.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables and unit vocabulary used in Inputs.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): index lags and conventions across G10 linker markets.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event risk and prediction-market probabilities.

## References

- Federal Reserve Bank of Cleveland - Economic Commentary 2022-05, Adjusting Median and Trimmed-Mean Inflation Rates for Bias Based on Skewness (Rich, Verbrugge, Zaman; Mar 2022): bias regression, skew adjustment, CPI and PCE sizes.
- Federal Reserve Bank of Dallas - Skewness warrants caution as Trimmed Mean PCE inflation eases (Atkinson, Dolmas, Zarutskie; 16 Apr 2026): convergence test; trimmed mean unreliable in positive skew.
- J.P. Morgan - US Focus: Lags in robust PCE cores challenge policy (Hanson; 13 Aug 2026): lead-lag table, 2021 episode, robust tracking.
- J.P. Morgan - North America Economic Research, United States (weekly; Feroli, Hanson, Reinhart, Parrish; 14 Aug 2026): CPI/PPI-to-PCE mapping; portfolio-fee linkage.
- Citi Research - US Economics: Details of PPI supportive of slowing core PCE (Clark, Hollenhorst; 13 Aug 2026): PPI items feeding PCE.
- Citi Research - US Economics: Benign details of benign core CPI (Clark, Hollenhorst; 12 Aug 2026): CPI component table and weights.
- J.P. Morgan Global Markets Strategy - Monthly Inflation Outlook: A mixed bag of inflation market views (Diamond, Infante et al.; 13 Aug 2026): UK RPI and US commodity beta models, real rates from swaps, breakeven carry, Japan tax effect.
- Citi Research - US Economics Weekly: Cooling inflation increasingly hard to ignore (Hollenhorst, Clark; 14 Aug 2026): fixings vs economists.
- JWS Macro - Global Rates Update #7: Same North Star, Worse Weather (19 Jul 2026): CPI fixing sanity check; MCT core.
- JWS Macro - Global Rates Outlook #6: Kick-off for a Global Tightening Cycle (7 Jun 2026): HICP vs Brent adverse case; food risk.
- BofA Global Research - Global Economic Weekly: The fog of war (Irigoyen, Gabriel et al.; 2 Oct 2026): oil volatility and hike pricing.
- BofA Global Research - US Economic Weekly: Revisions, risks, and rate hikes (Bhave, Juneau, Mishra; 2 Oct 2026): PCE revision and underlying inflation.
- Citi Research - European Economics Week Ahead: Week of 24 August (McLaren-Stewart et al.; 21 Aug 2026): euro-area flash HICP and base effects.
- Citi Research - US Economics Weekly: The resilient narrative of US resilience (Clark, Hollenhorst; 21 Aug 2026): market-implied core CPI method; CPI-vs-PCE signal.
- Citi Research - US Economics, Inflation Weekly: Last month of old PCE methodologies (Clark, Hollenhorst; 17 Aug 2026): fixings vs economists; revision size.
- Citi Research - US Economics Weekly: Main Street versus Wall Street (Clark, Hollenhorst; 2 Oct 2026): implied core CPI, fixings table.
- Barclays Research - US Energy and Inflation: Diesel's long haul to the US consumer (Sriram, Singh, Hill; 1 Oct 2026): diesel-to-PCE chain, three-lens exposure, regression design.
- Citi Research - Oil Monitor: At visible draw rates, when do we "run out" of oil stockpiles? (Lee et al.; 19 Aug 2026): days-of-cover framework and extrapolation.
- JWS Macro - Global Rates #3: Iran & Front End Rates (8 Mar 2026): energy-weight beta screen; $10 Brent rule; second-round channels.
- JWS Macro - Global Rates Outlook #5: Price Vs. Quantity & A New Era For Central Banking (10 May 2026): price-vs-quantity framework; oil scenarios.
- JWS Macro - Global Rates Outlook #4: Too Much Growth Fear, Not Enough Inflation Fear (8 Apr 2026): swap stripping; 5y5y as credibility gauge.
- Citi Research - European Rates Strategy: Latest views, summer updates (Harju et al.; 20 Aug 2026): Bunds vs gas vs oil.
- Citi Research - Global Economic Outlook & Strategy: Global Resilience (Sheets et al.; 20 Aug 2026): oil scenarios.
- Alexander Duering - Fixed Income Trading and Risk Management: The Complete Guide (Wiley Finance, 1st ed., 2021), Ch.23: linkers, seasonality, breakevens vs expectations.
- Dirk Willer and Alex Saunders - Trading Global Macro Markets (Wiley Finance, 1st ed., 2026), Ch.3, 5, 14: energy-to-inflation chain; breakevens over the cycle; commodity regime.
- J.P. Morgan Global Commodities Research - Oil Primer (Kaneva; 14 Jan 2025): crude quality, refinery yields, balances framework.
- Richard Clarida - The key inflation signal for investors (Financial Times, 19 Aug 2026): unit labour cost on a four-year average.
- Hudson Bay Research - A return to monetarism? (Ireland, Miran, Roubini; Jul 2026): P-star gap model; supply-shock rule.
- Goldman Sachs - GS cuRated 2Oct26 (Lee, Baker, Bhasin, Griswold; 3 Oct 2026): July PCE revision components.
- Wall Street Journal - The Outlook: A Statistical Revamp Is About to Lower Inflation (Grossman; 19 Jul 2026): BEA changes and timing.
- BEA - PCE Price Index Details, slide deck (undated): chained Fisher index construction.
- Citi Research - Foreign Exchange Forecasts: August 2026 (Tobon et al.; 20 Aug 2026): inflation surprise index; crack-spread stress gauge.
- Barclays Research - Energy Sigma: Unbent (Singh; 1 Oct 2026): Brent path anchors.
- Barclays Research - Global Rates Weekly: The urgency question (Pradhan, Khanna, Kadota et al.; 2 Oct 2026): ISM prices nowcast; breakeven views.
- Citi Research - Macro Think Tank: Top of Mind (21 Aug 2026): oil scenario levels.
- Citi Sales & Trading - STIRT Weekly: Beam me up, Scotty (Covre De Menezes et al.; 21 Aug 2026): energy and front ends.
- Citi Research - Canada Economics Weekly (Clark; 13 and 21 Aug 2026): CAD CPI components and leads.
- Wall Street Journal - See How China Weathered the Iran Oil Shock (Jiang, Shen; 21 Aug 2026): China import and reserve data.
- Financial Times - Japanese inflation rises as central bank weighs rate increase (Lewis; 21 Aug 2026): JPY core-core CPI.
- Reuters - Methodology changes could lower US May core PCE inflation, economists say (Mutikani; 29 Jun 2026): BEA changes.
- Irving Fisher - The Making of Index Numbers (1922) (external): Fisher ideal index used for the PCE chain.
- US Treasury - TIPS Handbook (external): index ratio and three-month reference-CPI lag.
