# Published lead-lag evidence (use as priors, re-estimate before trading)

Companion to [SKILL.md](../SKILL.md). Every row is a published, dated result from sell-side research or a textbook; none is a validated trading rule. Sample sizes are small, regimes differ, and the numbers should be reproduced on the user's own data (`scripts/lead_lag.py`) before use.

## 1. Policy and speech leads
| Test | Result | Source |
|---|---|---|
| Fed vs G9 policy-rate changes, cross-correlation scan about +/-12 months | Peak about 0.10 at a 3-month Fed lead, above coincident; +2m lag negative; G9 net-hiked while the Fed held or cut in 2006-08 and 2010-12 ("often leads but behaves idiosyncratically") | Citi, Global Macro Strategy Views and Trade Ideas, 13 Aug 2026 |
| Monthly VAR of central-bank speech scores (6-12 lags tried), Cholesky with Fed first then by economy size | A Fed shock raises other banks' scores in the same month, persisting several months. Granger Fed to others fails except for ECB; lags beyond one month add nothing | JPM, Talk is Cheap, 30 May 2024 |
| Speakers lead statements: change in statement score on change in 3m speech score and lagged statement change, 1998-2023 | Fed speech coefficient 0.56-0.58 (t 6.3), lagged statement 0.66 (t 14.3); ECB speech 0.20 (t 2.2, from 2017); BoE 0.08 (t 1.9). +10 Fed speaker points gives +5.8 statement points | JPM, Welcome to the machine, 26 Apr 2023 |
| Speech score (3m average, lagged 7 days) vs 90-day change in 1y yield | +10 points: +14 bp US, +12 EA, +12 UK univariate; about +7 bp for the Fed after the lagged rate change; +11 bp outside ZLB and +10 bp in ZLB (full model); residual s.e. 30-40 bp. Decay per 10 points: 0w 12-13, 1w 11-12, 4w 7-9, 8w 3-4, 13w about 0 | JPM, Welcome to the machine, 26 Apr 2023 |
| ECB-minus-Fed score gap vs 3m/3m change in EURUSD (same for BoE-Fed vs GBPUSD) | Lines up visually; the author suggests the same relative signal for rates RV | JPM, Welcome to the machine, 26 Apr 2023 |
| Bund factor vs inflation: VAR, Granger, Cholesky with inflation first | Peak cross-correlation at the 4th lead (about 0.746); Granger F = 6.12 (p = 0.03). The source does not say whether the series were differenced: treat as an illustration of method, not as evidence of a tradable lead | Dunis, Laws, Naim (eds), Applied Quantitative Methods for Trading and Investment, 2003 |

## 2. Indicator lead times (event studies; n is small)
| Indicator | Lead | Source |
|---|---|---|
| First 3m10y inversion to recession | median 14 months | Willer and Saunders, Trading Global Macro Markets, 2026 |
| First 3m10y inversion to first Fed cut | median 18 months, range 1-23 (Oct 2022 inversion to Sep 2024 cut = 23) | same |
| Cut within 12 / 24 months of inversion, average months to cut | 3m10s 52.2% / 100% / 10.3; 6m2s 73.7% / 84.2% / 12.0; 2s5s 73.3% / 93.3% / 7.7; 2s10s 57.1% / 85.7% / 11.4; median 65.0% / 93.3% / 10.5 | same |
| 6m2y inversion of at least 12.5 bp | cut within 6m 57.9%, 12m 73.7%, 24m 84.2%; the strongest 10y rally followed a 6m/2y inversion, 2s10s is the weakest signal | same |
| FF6-FF1 below -12.5 bp (at least half a 25 bp cut priced 6m out) | followed by cuts or no hikes within 6m; failed in Mar 2023 (FF6-FF1 -34 bp, funds rate +50 bp over 3m) | same |
| Before a 10y sell-off peak (n = 20 since 2000; median 120 bp over about 135 days) | 2y breakevens turn down about 1 month before; 5s30s flattens and peaks earlier than 10s; 2s10s peaks with 10s (except 2023, supply-driven); oil up more than 20% over 3m into the median peak; cyclicals/defensives down almost 5% in the 2 months before | same |
| Credit, equities, labour | Credit spreads tightest about 12 months before recession, SPX peaks about 6 months before (7 recessions since 1973); Sahm rule: SPX peaks on average 126 trading days before the trigger and bonds trade well into and after it | same |
| Oil | Detrended Brent leads weaker ISM momentum; yields do not look through oil rallies (2008 rates peaked ahead of oil, 2011 two months ahead, 2022 yields rose with oil) | same |
| Robust vs headline PCE: lag (months) maximising correlation | 1978-2001: 0 in every case. 2022-Jun 2026: median PCE 8 (vs headline) / 6 (vs core); trimmed mean 7 / 6. Granger results inconsistent; lead varies with the shock | JPM, US Focus: Lags in robust PCE cores challenge policy, 13 Aug 2026; US Weekly Prospects, 14 Aug 2026 |
| GDP and equities (Shiller data from 1947) | Contemporaneous correlation 0.02; weak GDP leads higher equity returns 2 quarters later; strong equity returns lead GDP by 1-2 quarters; weak GDP leads higher EPS growth 3-5 quarters later | Willer and Saunders, 2026 |
| Global vs local lead indicators for duration | Global indicators beat local ones for individual markets except UK PMI | JPM, Simple rules to trade duration, 2 Oct 2012 |

## 3. Cross-market transmission
| Test | Result | Source |
|---|---|---|
| Daily-change regressions on USD and JPY equivalents, past 1m vs previous 3m | R2 to JPY rose from about 0% to 20-50%: 5y5y EUR beta 0.5 / R2 30%, GBP 0.5 / 21%, AUD 0.7 / 50%; 10y EUR vs USD 0.7 / 38%, vs JPY 0.4 / 28%; SEK 10y vs USD 0.8 / 56%; 10y vs JPY was 0-4% in the prior 3m | JPM, Global Fixed Income Markets Weekly, 21-22 Aug 2026 |
| Rolling PCA with USD/JPY/CNY anchors on weekly Wednesday closes, 52-week window | Full-period PC1 46.4% of variance, R2 to USD 0.59; without HKD (peg) 0.24; R2 0.47 before 2023 and 0.76 after; JPY anchor significant for SGD/KRW/THB but moderate and fading | Citi, Decomposing Global Rate Drivers Across EM Asia 5y5y, 13 Aug 2026 |
| Global PC1 betas, bp per 1 sd | USD 0Yx1Y 32, 1Yx1Y 17, 2Yx1Y 12; EUR 0Yx1Y 8.5, 3Yx1Y 3.3, 10-15Yx1Y 4.8; JPY mostly long end (0.6 at 0Yx1Y to 8 at 15Yx1Y); GBP 1Yx1Y beta rose most (about 29 at 5Y); NZD largest PC2 beta rise | JPM, Talk is Cheap, 30 May 2024 |
| Heteroskedasticity-identified G4 10y decomposition | US exerted about 40 bp of bearish impulse on G4 yields since May; much of the gilt rise came from abroad | GS, Global Rates Trader: Reaching Limits, 2 Oct 2026 |
| US-Germany PC1, 2014-2020 | Two regimes: near one-for-one co-movement, then a static German PC1 against a volatile US PC1 (ECB asset purchases dampened euro yields while the Fed shrank its balance sheet): non-standard policy suppresses cross-market correlation | Alexander During, Fixed Income Trading and Risk Management, 2021 |
| Back end vs front end, daily 10y change on the 5th SOFR-type future, Mar 2022-Mar 2025 | Beta 0.9, R2 just below 91% | Willer and Saunders, 2026 |
| JGB vs UST | JGBs expected to follow USTs for now. FX-hedged long JGB / short UST on the pickup tail: IR 0.72 long/short; long JGB only when UST yields are below their 55-day average: IR 0.90 vs 0.28 above (conditioning on the leader's state improves the follower rule) | Citi, Japan Rates Weekly, 21 Aug 2026; Willer and Saunders, 2026 |
| European asset-swap stress to USD spreads | Large moves in BTP and OAT asset swaps "started to feed through to USD spreads" | GS, GS Macro cuRated, 3 Oct 2026 |

## 4. Rates to FX and cross-asset
| Test | Result | Source |
|---|---|---|
| Perfect-foresight weekly sign of the realised rate change as an FX signal (Sharpe read from bars) | Relative (US minus Germany) 2y about 2.2, 5y 1.8, 10y 1.7; relative equity about -0.65; US-only 2y 1.25; EUR-only 2y 0.7: differentials beat outrights, the US side beats the European side, 2y best. Perfect foresight is an upper bound, not a forecast | Willer and Saunders, 2026 |
| Cross-sectional rank correlation of G10 FX with factors | Rates (2y change) strongest at short horizons, peaks at about 2 months and fades from about 5 weeks; equities peak at 6 months; correlations broke down in 2011, 2013, 2017 | BofA Merrill Lynch, FX Quant Primer, 1 Oct 2018 |
| Time-zone decomposition (UK 8-13h GMT, US 13-24h, Asia 0-8h), 6m regressions of 24h returns on single-zone returns | Zone with the highest R2 is dominant: US hours for 16 of 24 pairs in 1H18, UK 6, Asia 2 | same |
| CTA index betas on six PC1 features (rolling 2m regression) vs a multiple-crossover momentum signal | Maximum correlation at a lead/lag of about 15-20 days; significant for S&P, 10y note and WTI | BofA, US Rates: CTAs impact on the rates market, 18 Aug 2020 |
| HFT vs non-HFT depth, 25-minute changes at integer lags, about 40,000 periods over 11 years | HFT depth falls ahead of slower participants at 5-25 minute horizons; on 3 Mar 2020 the HFT depth share fell right after the 10y breached 1%, ahead of the next move | JPM, Did US rates markets just experience a mini Flash Rally?, 5 Mar 2020 |
| EUR risk-aversion legs | BTP-Bund spread vs its 55-day average (IR 0.42); Euro Stoxx vs MSCI US vs 55-day average with 2-day lag (IR about 0.50) | Willer and Saunders, 2026 |

## 5. How to use these
- Treat each as a prior on sign and rough size; the skill's estimation protocol and hard rules still apply (same sign and lead in two non-overlapping sub-samples, n >= 250 independent bars).
- Information ratios quoted in the books are in-sample on published samples; discount accordingly.
- A lead that is published and works gets traded: expect it to shrink (Tulchinsky et al., Finding Alphas, 2015).
