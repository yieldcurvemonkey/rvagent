# Inflation measurement detail: robust cores, PCE, revisions, seasonality

Companion to `SKILL.md`. Covers the measurement mechanics: robust (limited-influence) measures, the PCE
construction and CPI/PPI-to-PCE mapping, methodology revisions, lead-lag evidence, and seasonal factors.
Figures are as reported in the cited sources; formulas marked (standard) are textbook definitions added for
completeness and are not quoted from a source.

## 1. Robust (limited-influence) measures

**Definitions.** Median and trimmed-mean inflation are computed from the cross-section of monthly price changes
across categories, using expenditure weights.
- Median: the 50th percentile of the weighted price-change distribution.
- Trimmed mean: drop a fixed share of each tail, average the rest. Dallas Fed trims the bottom 24% and top 31% of
  the PCE distribution (177 categories; pre-2009 thresholds were 19.4% / 25.4%). Cleveland Fed trims 8% from each
  tail of CPI (Cleveland Fed, Economic Commentary 2022-05, Mar 2022; Dallas Fed, Skewness warrants caution as
  Trimmed Mean PCE inflation eases, 16 Apr 2026).

**Skewness measure (Cleveland).** A weighted average of two robust skew coefficients, bounded in [-1, +1], taken as
a one-sided 12-month moving average:
- Bowley (standard): `B = (Q3 + Q1 - 2*Q2) / (Q3 - Q1)`, quartiles of the price-change distribution.
- Kelly (standard): `K = (P90 + P10 - 2*P50) / (P90 - P10)`.
- Cleveland combines weighted B and K. The averaging weights are not in the notes. Use the published skew series
  rather than recomputing it unless the category weights are available.
- Sign: positive skew = a long right tail of large price rises (the pandemic pattern). Negative skew = a long left
  tail of large falls (historically normal, goods deflation).

**Bias.** Monthly gap `g_t = median_t - headline_t` (same for trimmed mean). Bias = a two-sided, centred 36-month
moving average of `g_t`, dropping the highest and lowest observation in each window (Cleveland Fed, 2022-05).

**Bias regression (Jun 1986 - May 2020, HAC SE, 3 lags)** (Cleveland Fed, 2022-05):

| Measure | alpha (pp) | t | beta on skew | t | R2 |
|---|---|---|---|---|---|
| Median PCE | 0.20 | 4.49 | -2.01 | -9.22 | 0.48 |
| Trimmed mean PCE | -0.10 | -2.39 | -1.38 | -6.86 | 0.38 |

**Adjusted measure.** `pi_adj = pi - (alpha + beta*skew)`. For the median this is `pi - 0.20 + 2.01*skew`; the
source rounds the coefficient to `pi - 0.20 + 2*skew`. For the trimmed mean use its own coefficients.

Derived cross-check (not in the source): the Dec-2021 adjustments in the source (median +14bp to 3.75%, trimmed mean
+34bp to 3.39%) imply skew of about 0.17 for the median (`(0.14 + 0.20)/2.01`) and about 0.17 for the trimmed mean
(`(0.34 - 0.10)/1.38`). The two agree, which supports reading the coefficients as a single skew adjustment.

**Sensitivity rule (derived).** Each 0.1 of skew moves the adjusted median by about 0.2pp
(`2.01 * 0.1`); the trimmed mean by about 0.14pp (`1.38 * 0.1`). At skew 0.2 the median adjustment is about
+0.20pp and the trimmed-mean adjustment about +0.38pp (`0.10 + 1.38*0.2`).

**Cleveland adjustment sizes.** Average adjustment since Apr-2021: +0.30pp for the trimmed mean and +0.08pp for the
median. The median has averaged about 0.3pp above the trimmed mean since 2000. CPI versions carry adjustments of
95-115bp (Cleveland Fed, 2022-05).

**Convergence test (Dallas Fed, 16 Apr 2026).** For h = 1..24 months, regress the change in 12-month headline PCE on
the (core - headline) and (trimmed mean - headline) gaps plus lags of all three. A coefficient near 1 means headline
converges to that measure. Result: the trimmed-mean coefficient rises with horizon to about 1 after 12 months; core
is about 0. In positive-skew periods (sample from 1960, coarser aggregation) the trimmed-mean coefficients are about
0, so the trimmed mean is not a reliable disinflation signal when skew is positive.

**Lead-lag evidence (JPMorgan, Lags in robust PCE cores, 13 Aug 2026).** Lag (months) that maximises the
correlation of each robust core with lagged headline or core:

| Sample | Median vs headline | Median vs core | Trimmed mean vs headline | Trimmed mean vs core |
|---|---|---|---|---|
| Jan 1978 - Dec 2001 | 0 | 0 | 0 | 0 |
| Jan 2022 - Jun 2026 | 8 | 6 | 7 | 6 |

Granger results were inconsistent: in the later sample headline and core helped forecast the robust measures, not
the reverse. The 2021 episode: headline crossed 3% in Apr-2021 and 4% in May; core reached 3% in April and 4% in
September; the median reached 3% six months later and the trimmed mean seven months later; both reached 4% only in
Jan and Mar 2022 (JPMorgan, 13 Aug 2026).

**Other robust tools in the sources.**
- MCT (signal/noise) decomposition of core CPI, preferred by the JWS author to the trimmed mean; persistent
  component about 0.2% m/m (JWS Global Rates Update #7, 19 Jul 2026). The decomposition method is not in the notes.
- Unit labour cost (ULC) on a four-year average of annualised quarterly growth. ULC is about 60% of non-financial
  corporate value added. Reading: 4y average 2%, past year 1.5% (Clarida, The key inflation signal for investors,
  Financial Times, 19 Aug 2026). The source claims every postwar sustained inflation rise or fall came with a ULC
  trend. Treat as the author's claim, not a tested result.

## 2. PCE construction and CPI/PPI-to-PCE mapping

**Chained Fisher index.** PCE growth is the geometric mean of a Laspeyres and a Paasche index, chained from a base
year (BEA, PCE Price Index Details slide deck, undated; the deck's multiplier is garbled in the extraction, so the
form below is the standard Fisher ideal index):

    L_t = sum(p_t * q_{t-1}) / sum(p_{t-1} * q_{t-1})     (Laspeyres, prior basket)
    P_t = sum(p_t * q_t)     / sum(p_{t-1} * q_t)         (Paasche, current basket)
    I_t = I_{t-1} * sqrt(L_t * P_t)                       (chained level, I_0 = 100 in base year)

Monthly rate `m_t = sqrt(L_t * P_t) - 1`. Weights come from business surveys and change more often than CPI
weights. The Fisher form is used because it captures substitution between goods when relative prices move (BEA
deck, as summarised in the source notes).

**Mapping CPI and PPI to core PCE (nowcast).** Several PCE categories are priced from PPI rather than CPI:
portfolio-management fees, airfares (domestic and international), medical services, and computer software and
accessories (AI-related hosting and gaming feed the latter). Citi, Details of PPI supportive of slowing core PCE,
13 Aug 2026; JPMorgan, US Economics, 14 Aug 2026.

Core PCE m/m is approximately `sum_k omega_k * m_k`, where `omega_k` is the core PCE weight of category k and `m_k`
is its mapped monthly change (PPI for the PPI-sourced items, CPI otherwise). The source notes do not print the full
mapping table, so use the BEA weights and the mapping in the economist notes, and state which mapping was used.

**Weight differences vs CPI.** Core goods are softer in PCE than CPI (smaller used-car weight, larger medical-goods
weight). Non-shelter services carry a drag from equity-linked portfolio fees (Citi, Flash, 12 Aug 2026).

**Worked example: July 2026 (sources as reported).**
- Core CPI +0.215% m/m (Citi, Benign details of benign core CPI, 12 Aug 2026; JPMorgan reports +0.22%).
- Core PCE after CPI: 0.15% m/m (Citi Flash, 12 Aug 2026). After PPI: 0.21% (Citi Flash, 13 Aug 2026).
- JPMorgan's mapping gives +0.3% m/m and y/y 3.3% to 3.4%. The spread between houses (0.09pp m/m) shows the mapping
  is not unique; record which one you used.
- Portfolio-management PPI +6.5% added about 12-13bp m/m (Citi; JPMorgan adds 13bp).
- Derived: the implied effective core-PCE weight of that fee is `0.12 / 6.5` to `0.13 / 6.5`, about 1.8-2.0%.

**Asset-price linkage (derived from the above).** Fees are treated as inflation when AUM moves, so a 10% AUM rise
registers as a 10% rise in the fee (JPMorgan, 14 Aug 2026). With the effective weight above, a 10% AUM-driven move
adds about 18-20bp to core PCE m/m if the fee tracks AUM one-for-one. Check this against the current BEA weight
before using it; it is a sensitivity, not a forecast.

## 3. Methodology revisions

- BEA changes effective with the 30-Sep-2026 release: portfolio management (from asset-based fees to firm income
  vs labour input), software (blend of videogame software and web hosting), and legal services (CPI to PPI) (WSJ,
  The Outlook: A Statistical Revamp, 19 Jul 2026; Reuters, 29 Jun 2026).
- Size, by source: about -20 to -30bp to annual core PCE (Citi, 17 Aug 2026; FX note, 20 Aug 2026); about -25bp
  midpoint (Citi US Economics, 21 Aug 2026); about 0.2pp (economists, WSJ and Reuters); 35bp for July (BofA, 2 Oct
  2026, taking core to 3.0% y/y). GS (3 Oct 2026): July y/y revised down 36bp to 2.98%, with components portfolio
  management -0.23pp, software -0.11pp, legal +0.01pp. The components sum to -0.33pp, not -0.36pp; reconcile
  before using either figure.
- Treat it as a level shift in the y/y, not a change in trend. The Fed is expected to look through it, and an FOMC
  may be cautious about hiking on inflation that was "revised away" (BofA, 2 Oct 2026; JPMorgan, 14 Aug 2026).
- Arithmetic: `y/y_new = y/y_old + delta_level`, applied from the month the methodology switches (August data for
  these changes). Example: 3.25% before a -25bp revision is about 3.00% after it (illustration with Citi's
  midpoint, not a figure from the source).

**Rounding trap (checked).** Citi gives July core PCE at 3.249% unrounded and says it "could print 3.3%". At one
decimal, 3.249 rounds to 3.2, not 3.3. The source does not reconcile this. Confirm the unrounded figure and the
vintage before reading any boundary.

## 4. Seasonality of inflation data

Approximate seasonal factors, % deviation of the NSA index from trend (chart reads, Duering, Fixed Income Trading
and Risk Management, 1st ed., Ch.23, 2021):

| Month | HICPxT (EZ) | US CPI NSA |
|---|---|---|
| Jan | -0.7 | -0.55 |
| Feb | -0.5 | -0.35 |
| Mar | +0.1 | (not read) |
| Apr-Jun | +0.35 to +0.4 | +0.3 to +0.4 |
| Jul-Aug | slightly negative | +0.2 to +0.3 (Jul-Sep) |
| Sep-Oct | +0.1 | (not read) |
| Nov | -0.1 | -0.3 |
| Dec | 0 | -0.7 |

Use them as seasonal m/m contributions: the seasonal m/m for month m is about `s_m - s_{m-1}` (derived). In January
the NSA index falls relative to December by about 0.7pp at trend for HICPxT, so a weak NSA January is not news. For US CPI the
same chart reads give Dec -0.7, Jan -0.55, a seasonal m/m of about +0.15pp, so US January is not seasonally weak.
Duering also notes that German restaurants and hotels peak in summer and at Christmas; weight under 10%, but high
volatility makes it a significant driver. Use the official seasonal set (canonical table `infl_seasonals`) and
its `valid_from` date, not these chart reads.

## 5. Worked numbers and data points (for checking)

- US core PCE 3.0% vs Dallas trimmed mean 2.3% through Feb-2026; the two diverged after Sep-2025. Core goods
  contributed 0.6pp of the 0.7pp widening in the headline-trimmed gap (Dallas Fed, 16 Apr 2026).
- Robust tracking after July 2026 CPI/PPI: core PCE 3.4% y/y, median 2.8%, trimmed mean 2.3% (JPMorgan, 13 Aug 2026).
- Citi July 2026 component table (actual m/m / Citi forecast / basket weight): core goods 0.20 / 0.12 / 18.8%;
  core services 0.23 / 0.18 / 60.2%; shelter 0.14 / 0.21 / 35.3%; OER 0.26 / 0.22 / 25.8%; lodging -2.75 / 0.03 /
  1.5%; core services ex-shelter 0.35 / 0.13 / 24.9%; medical services 0.56 / 0.25 / 6.8%; energy -1.48 / -1.79 /
  7.4%. Headline +0.07% m/m, 3.4% y/y (Citi, Benign details of benign core CPI, 12 Aug 2026). Check: the weights
  are shares of the total CPI basket. Core (18.8 + 60.2 = 79.0%) plus energy (7.4%) leaves 13.6% for food, which
  the table does not show.
- Contribution arithmetic (derived): a component's contribution to headline m/m is `weight * change`. Lodging at
  1.5% weight and -2.75% m/m contributes about -0.04pp to headline CPI, or about -0.05pp to core (divide by 0.79).
  A single volatile line like this can explain a large share of a soft core print, so check contributions, not
  only the rate.
