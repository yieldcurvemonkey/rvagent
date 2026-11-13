# Window conventions, sign conventions and G10 notes for z-score screens

Companion to [SKILL.md](../SKILL.md). Use it to translate a published z into your own convention, and to pick the
window a market's screen is normally quoted on.

## 1. Window and definition used by published screens
| Screen | z / percentile definition | Source |
|---|---|---|
| Treasury RV (UST) | 3m z; red < -2, green > 2 on swap spreads, proceeds ASW, fitted spread | GS, Treasury RV Report, 25 Sep 2026 |
| UST curve RV | 3m z of yields; +2 = cheap ("only c.2.5% of recent observations cheaper"); changes preferred to levels | BofA, UST RV Primer, 2 May 2022 |
| EGB auction RV | 3m z of yield, vs fitted, vs surrounds, vs closest-rated EGB, CAS; buckets <-2, -2..-1, -1..0, 0..1, 1..2, >2 | Citi, European Rates Morning Call, Aug 2026 |
| Entry z (trade report) | (level - 5y mean)/5y sd, with 5y min/max, 25th/75th pct; payer-perspective signs | GS, Global Rates Best Trade Report, 30 Sep 2026 |
| Normalised move | h-period change / sd of h-period changes; 62d history for 1d/1w, 252d for 1m | GS, Market Movers, 30 Sep 2026 |
| Curve slope dislocation | slope beyond 2.0 sd of its 120d average; fixed sample, exclude issues < 120d old | Citi, High-Grade Beat, 19 Aug 2026 |
| Swap-fly tables | 1m/3m/6m z (12m for forwards); positive = belly cheap | Citi, US Rates Weekly, Feb and Oct 2026 / Feb 2023 |
| Long-dated forward curves | 1y, 3y, since-2000 z | Citi, Rates Vol Lab, 2019-2023 |
| CA / convexity | 3m and 1y z of CA and of CA minus model | Citi, Short Blues convexity, Feb 2023 |
| ATM vol grid, switch ratios | 1m/3m z; forward-vol grid 5y-window z; frontier 1y and 3m z | Citi, Rates Vol Lab, 2016-2026 |
| EUR forward monitor | 50d and 200d z with ranges; carry-and-roll / 252d realised vol; PCA mispricing | Nordea, EUR rates, Jan 2024 / Jun, Aug, Sep 2025 |
| EUR PC1-residual | 3y percentile band (5th/median/95th), shortened to 1y in fast markets | ING, Jan and Mar 2020 |
| Swap-spread PCA | 2 PCs, residual z over 250d; DI = 10d MA of RMS of z over 2y/5y/10y/30y | BofA, Jun 2016 |
| EGB spread residual | cross-sectional sd of 42 residuals z-scored on an expanding window | BofA, Many EGBs, one simple value tool, Mar 2018 |
| Macro FV residual | (resid - avg resid)/SD; JPM adds R2; BofA tilt rule at +/-0.5 sigma | BofA, Aug 2025 and Oct 2024; JPM, May 2024 |
| FX basis | YTD z (and 3m z for GBP); 6m z with 6m min/max for bond-CDS basis | JPM, Cross currency basis 4Q24 Outlook, Sep 2024; JPM, EM Basis Report, Oct 2025 |
| Positioning | 5y z (CFTC), 1y z (surveys, model betas), 5y percentile dials | JPM, Feb 2020; BofA, Mar 2025 |
| Liquidity composite | average of six 5y z-scores, some inverted | JPM, Are we there yet?, 1 Apr 2020 |
| Vol/stress switch | max over inputs of the 1y z; cut risk above 2 | Willer and Saunders, 2026 |
| Seasonality | up-ratio over 20y (>= 70%/<= 30%); 10y of data for Japan | BofA, Jun 2022 |

Longer windows (3-5y, since-start) judge level; shorter (1m-3m) judge stretch now. Choose per metric, state it, and
show at least one more window beside it.

## 2. Sign conventions that differ between sources (normalise before combining)
| Source | Convention |
|---|---|
| Citi swap-fly tables | positive = belly cheap (fly `-0.5:1:-0.5`, receive belly) |
| Citi futures spline residual | spread to spline, positive = cheap |
| GS entry z | payer-perspective: for a receiver a positive z (level high) is attractive |
| Nordea 2019/2024 | receiver-perspective; Nordea 2025 z looks trade-direction-signed while PCA mispricing is unsigned (par - fair value) |
| BofA/JPM residual z | residual = actual - model; positive = cheap (high yield/spread) |
| BofA macro DFM | negative residual = rich |
| JPM basis screen | positive z = narrower than the YTD average; basis legend "positive = CDS cheap" |
| Auction dashboards | z below -2 = rich, above +2 = cheap (yield-based) |
| JPM percentile score | -5..+5 by percentile of own history; long investor positioning = short signal |
Convention used in this skill: `z > 0` = series high vs its own history; yield/spread high = cheap for a long-bond
or receive-fixed position. Record the mapping next to every flagged line.

## 3. Estimator choices
| Choice | Default | Reason |
|---|---|---|
| Mean/std | rolling, ddof 1 | causal; unbiased variance |
| Today in the window | inclusive for dashboards; exclusive for entry signals/backtests | inclusive caps |z| at (L-1)/sqrt(L) and shrinks z by ~1/L |
| Std floor | NaN if std < 1e-12 x (1 + abs mean) | frozen series otherwise give astronomical z |
| EWMA | halflife 21 (lambda ~0.97), data to t-1 | tracks regime change; lambda 0.97 used for sigma moves (BofA, Systematic Flows Monitor, Jun 2025) |
| Outliers | median/MAD x 1.4826, or winsorise series at +/-2.5 sd; clip z at +/-4 (single) or +/-2 (cross-sectional) | breakdown point |
| Skewed positives | log then z | removes positive skew (Citi, QIS Corner, Aug 2026) |
| Percentile | share of window <= x_t; rolling only | bounded, no sd assumption; not comparable across markets |
| Warm-up | no output until L obs; 252 minimum for the 1y window | avoids partial-window z |
| Quote | z, percentile and raw bp together | z alone hides size (GS P-STRIPS example in SKILL.md) |
| Event z | 2-sigma day move vs trailing 1m sd (FOMC/NFP); control distribution of random windows for "market-moving" | Willer and Saunders, 2026; JPM, Comfortably numb, Jul 2026 |

Event-grid score (BofA, US Treasury auction primer, Mar 2024): per entry/exit lag cell compute average bp, sd, hit ratio
and "Sharpe" = average/sd, `Score = hit ratio x Sharpe`; on 12 auctions the best 2s10s flattener cell (entry -3, exit -1)
scored 52% (75% hit x 69%). 12 observations are regime-sensitive: contrast with the last 6m.

## 4. G10 notes
- **USD**: z-score on swap spreads vs SOFR and vs OIS differ by ~4-6bp in level, so state the benchmark. Exclude the zero
  bound from macro-vol fits (1996-2008 spliced with 2017-18). Swap-rate history has structural breaks (LIBOR, SOFR
  pre-/post-repo-facility); use fitted par government curves for since-2000 z. Swap bid/offer fell from 1.6bp (1995-98) to
  0.3bp (2017-18): an edge that survived costs once may not now.
- **EUR**: fit vol/rate models on the post-2016 negative-rate period; EGB screens use 25y in place of 30y for data; Euribor
  strip screens use the first 16 contracts only; benchmark switches (OBL177 to OBL178) create fake roll jumps; check which
  leg moved (EU-OAT tightening came from OAT weakness). Cross-country z: comparator-country spread z (IT 2/10 vs DE 2/10).
- **GBP**: long-dated flatteners screen best cross-market (lowest BE/RV, since-2000 z 1.1-2.05; 20y richness from pension/
  ALM receiving); a single-factor SONIA curve residual was not faded as rolling R2 fell (JPM, Aug 2026).
- **JPY**: curves are positive and realised vol is low (2.4-3.1bp/day), so BE/RV and z must use JPY's own vol; JPY is
  the extreme "cheap" point in the BofA (+3.3) and JPM (+3.82) residual screens, and permanently lowest in real-yield
  rankings (exclude or neutralise); carry rankings break under yield-curve control (substitute the next market); JGB
  seasonality uses only 10y of data.
- **CAD / AUD / NZD**: CAD long-dated flattener BE/RV 0.45-1.82 (Jan 2020); AUD and NZD appear in the 1Yx1Y cheapness
  screen at z 3.15 and 2.73 (May 2024); AUD seasonality 20y (some swap spreads 8y). Neighbour pairs (SEK/NOK, AUD/NZD,
  CAD/US): a 5y spread at a 1,000-day extreme is an alert for reversal, not an entry (Willer and Saunders, 2026).
- **CHF**: richest in the 10y residual screen (z -1.8, Aug 2025); CHF 1y basis the most stretched in the YTD basis screen
  (z 2.4, Sep 2024); CHF 1y1y forward at z 0.04 in the GS Sep 2026 market-state table: low-rate markets have small sd, so
  z moves with tiny bp changes.
- **SEK / NOK**: screen universes are shorter (to ~1y10y / 5y5y), so cross-sectional scores rest on fewer trades and are
  less comparable; NOK 3y2y/5y2y/7y2y z -2.26 (GS, Sep 2026). SEK and NOK FX options were excluded from a put/call ranking
  for low volume.

## 5. Further sources cited inline (documents read for this skill)
- Citi Research, US Rates Vol Lab: Buying vol for less (Bikbov, Williams, 25 Sep 2019); Trading long-dated convexity (9 May 2019);
  Fair value vs seasonality (1 May 2017); Year-Ahead: Bumpy road for vol (12 Dec 2016); Long Live Formosa (9 Jan 2017);
  Gamma and Vega RV (14 Jan 2019); The art of gamma hedging (12 Mar 2018); Convexity Meets Steepeners (19 Apr 2018).
- Citi Research, Rates Vol Lab: Short Blues convexity via futures/swaps (21 Feb 2023); Left-side vols' outperformance (22 Jun 2021);
  Fading vega dislocations (5 Oct 2026); Slow and steady wins the short gamma race (14 Sep 2026).
- Citi Research, US Rates Weekly: The rocky road to a steeper curve (18 Jan 2019); Time for moderation (17 Feb 2023); Swearing
  in huge expectations (13 Jan 2017); Fixing the plumbing (30 Sep 2019); Eat, pay, spend (27 Mar 2020); OAT of the blue (2 Oct 2026);
  Can Secretary Bessent and Chair Warsh save the curve? (21 Aug 2026).
- Citi Research, European Rates: Morning Call (12 and 19 Aug 2026); Weekly: What to do about OATs? (1 Oct 2026); Latest views (20 Aug 2026).
- Citi Research, QIS Corner (20 Aug 2026); Quantitative Framework for Regime Investing (Saunders, Willer, 29 Oct 2021);
  The High-Grade Beat (19 Aug 2026); Short-End Notes (21 Aug 2026); FX Basis Quarterly (13 Dec 2024).
- BofA Global Research: US Vol Primer (11 Mar 2024); US Treasury auction primer (8 Mar 2024); Long UST outflows & dealer holding highs
  (10 Mar 2025); Mixed UST positioning picture (22 Apr 2024); Systematic Flows Monitor (2 Jun 2025); Bond market seasonality
  explained (6 Jun 2022); Technicals Explained (14 Jan 2025); Introducing a new UST macro framework (15 Oct 2024); UK Rates
  Viewpoint (5 Sep 2024); FX Quant Primer (1 Oct 2018).
- J.P. Morgan: Canary in a coal mine (25 Feb 2020); Are we there yet? (1 Apr 2020); Valuing convexity in the long end (9 Feb 2018);
  Global Fixed Income Markets Weekly (21-22 Aug 2026); U.S. Bond Futures Rollover Outlook (12 Aug 2026); FX Markets Weekly
  (21 Aug 2026); Comfortably numb (24 Jul 2026); HG and EM CDS-bond basis reports (22 Oct 2025); Cross currency basis 4Q24
  Outlook (26 Sep 2024); Systematic fixed income trading strategies (13 Apr 2015).
- Credit Suisse, Wall Street Babylon (Bassman, 28 Nov 2011); Merrill Lynch RateLab, Implied Volatility: A Measurement of Fear
  (7 Oct 2008) and Javelin Catching (16 Feb 2007); Barclays, Global Rates Weekly (2 Oct 2026); Astor Ridge, Trade Radar
  (6 Mar 2022); Nordea Markets EUR rates notes (23 May 2019, 17 Jan 2024, 19 Jun, 12 Aug, 26 Sep 2025); RiskVal, Overview 201:
  Cash and Futures (12 Nov 2021); Rhodes, trade ideas (8-9 Oct 2025); swapsball.net, Testing for seasonality (19 Nov 2017).
- Books and notes: Tsay, Analysis of Financial Time Series (3rd ed., 2010); During, Fixed Income Trading and Risk Management (2021);
  Hasbrouck, Empirical Market Microstructure (2004 teaching notes); Hajek, Probability with Engineering Applications (ECE 313 notes,
  2025); Paleologo, The Elements of Quantitative Investing (2025); Brenndoerfer, Mean Reversion and Statistical Arbitrage (Dec 2025);
  Chan, Quantitative Trading (2009); Shafer and Vovk, Game-Theoretic Foundations for Probability and Finance (2019).
