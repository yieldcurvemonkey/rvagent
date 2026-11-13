# Published readings, conversions and derivations

This file supports [SKILL.md](../SKILL.md). The readings are dated observations from sell-side monitors. They are
context for calibrating "how rich is rich". They are not current data. Numbers are as printed. Rich/cheap residuals
are in bp of normal vol, with z-scores in brackets.

## 1. Midcurve readings (USD unless stated)
| Close | Reading | Source |
|---|---|---|
| 8 Mar 2018 | 6m1y1y rich on vol-surface PCA, +2.7 (z 1.5); bull steepeners expressed through midcurves | Citi, US Rates Vol Lab: The art of gamma hedging, 12 Mar 2018 |
| 11 Jan 2019 | 1y1y, 2y1y, 1y2y rich to vanilla (3m 1y1y +2.3, z 1.1), consistent with low implied correlation; 5y5y cheap (1y −2.5, z −1.9); 10y10y implied/realized correlation z 2.4-2.6 | Citi, US Rates Vol Lab: Gamma and Vega RV, 14 Jan 2019 |
| 22 Mar 2019 | 1y1y midcurves rich (implied correlation down); 2y-expiry midcurves cheap | Citi, US Rates Vol Lab: Vol cycle, steepeners, and SOFR, 25 Mar 2019 |
| 8 May 2019 | 3m2y1y about 1.7 normals rich to swaptions | Citi, US Rates Vol Lab: Trading long-dated convexity, 9 May 2019 |
| 24 Sep 2019 | 6m 2y1y +5.3 (z 2.4); 6m 1y2y +3.1 (z 1.9); 3m 10y10y −4.2 (z −3.0) | Citi, US Rates Vol Lab: Buying vol for less, 25 Sep 2019 |
| 16 Jan 2020 | 1y5y5y about 3σ cheap to vanillas; EUR 1y2y midcurves rich on implied/realized correlation | Citi, Rates Vol Lab: In search of cheap vol, 17 Jan 2020 |
| 27 Mar 2020 | 3m1y1y −10.7 (z −3.7) and 3m1y2y −10.2 (z −3.8) cheap; 1m3y1y +23.3 (z 4.4) and 1y3y1y +16.6 (z 4.6) rich; EUR 6m3y2y about 3σ cheap | Citi, Rates Vol Lab: Liquidity, vega, and convexity, 30 Mar 2020 |
| 21 Jun 2021 | USD 3y2y and 5y5y rich, 6m2y1y and 6m1y2y cheap; EUR 5y5y and 10y10y cheap (high implied-correlation z) | Citi, Rates Vol Lab: Left-side vols' outperformance, 22 Jun 2021 |
| 17 Feb 2023 | 1m ATM normals: 1y1y 165.0, 5y5y 109.6 (3m z −1.5), 10y10y 85.1 (−1.6); 1m implied correlations 89-105%, 10y10y 97.9% (z 1.4); 1m and 3m 10y10y cheap to vanilla | Citi, Rates Vol Lab: Short Blues convexity via futures/swaps, 21 Feb 2023 |
| 9 Jun 2023 | 5y5y cheap: implied correlation about 95-96% (3y z +1.2 to +1.6), 2y-expiry residual −3.2 (z −2.5); EUR 3y1y and 3y2y cheap; EUR 1m1y1y +21.8 (3.3σ) rich | Citi, Rates Vol Lab: Forward steepener and vol divergence, 12 Jun 2023 |
| 11 Sep 2026 | 2y1y cheap (3m −4.4, z −0.7; 1y −4.4, z −1.3); EUR 10y10y cheap on implied/realized correlation | Citi, Rates Vol Lab: Slow and steady wins the short gamma race, 14 Sep 2026 |
| 2 Oct 2026 | USD short-dated 5y5y rich to swaptions; EUR 10y10y cheap on implied/realized correlation | Citi, Rates Vol Lab: Fading vega dislocations, 5 Oct 2026 |

Pattern: front-end midcurves (1y1y, 2y1y, 1y2y) swing rich when Fed-path trades run through them and cheap when
that demand fades. 5y5y and 10y10y midcurves are more often cheap, with high implied correlation. Not always: USD 5y5y was rich in Jun 2021, and short-dated 5y5y in Oct 2026.

## 2. CMS curve-option readings
| Close | Reading | Source |
|---|---|---|
| 22 Mar 2019 | 5s10s cheap on PCA and to 3m realized; 10s30s rich on the surface | Citi, Vol cycle, steepeners, and SOFR, 25 Mar 2019 |
| 8 May 2019 | curve gamma trades at a higher premium to realized than swaptions; 10s30s rich on PCA and to realized | Citi, Trading long-dated convexity, 9 May 2019 |
| 16 Jan 2020 | 2s10s rich on PCA; 10s30s rich to realized; EUR 10s30s very rich to realized | Citi, In search of cheap vol, 17 Jan 2020 |
| 27 Mar 2020 | implied correlations fell, so spread vol was rich to swaptions: 6m 2s10s +4.2 (about 2.7σ) on PCA; but 1m 2s10s implied/3m realized 0.83 (z −1.5) | Citi, Liquidity, vega, and convexity, 30 Mar 2020 |
| 21 Jun 2021 | USD 2y/3y-expiry 2s10s and 2s30s richest on PCA (low implied correlation); EUR 1y 2s5s 1.3σ below its 3y conditional mean | Citi, Left-side vols' outperformance, 22 Jun 2021 |
| 17 Feb 2023 | implied curve correlations rebounded as recession-hedge cap demand waned; costless 1x2 curve cap spreads favoured for a wide forward-spot roll; EUR 1m 2s5s rich outright and vs 1m 5s10s; EUR 5y 5s30s 3σ rich | Citi, Short Blues convexity via futures/swaps, 21 Feb 2023 |
| 9 Jun 2023 | USD 5s30s implied correlation at multi-year lows (persistent cap demand); 1m 2s5s implied/1m realized 2.55 (z 2.6); EUR 6m 2s5s PCA +6.4 (2.9σ), vs 5s30s −10.8 (−2.9σ) | Citi, Forward steepener and vol divergence, 12 Jun 2023 |
| 11 Sep 2026 | USD curve vols 3m z about 2-3 (2s30s 3m 78.9nv, z 3.1); 30s/5s rich to swaptions as implied correlation fell; EUR 1m z about 4.2-4.9; EUR 2s5s and 2s10s at 2y-5y expiries rich on PCA | Citi, Slow and steady wins the short gamma race, 14 Sep 2026 |
| 2 Oct 2026 | USD implied correlations lower; EUR 3m 30s/5s implied correlation fell sharply; EUR 3m-1y 2s5s to 2s30s and 5s10s cheap on PCA, short-expiry 10s30s rich | Citi, Rates Vol Lab: Fading vega dislocations, 5 Oct 2026 |

## 3. Premium-to-vol conversions (ATM, single look, undiscounted: σ = premium / √(T/2π))
| Trade | Premium | Implied spread vol | Source |
|---|---|---|---|
| 6M 2s10s ATMF curve cap (short) vs 6M 5s30s (long), $500mn each | 9.3c / 8.15c | 33.0 / 28.9bp | J.P. Morgan, The long and short of it, Aug 2018 |
| 3M 2s10s caps: long EUR €1bn (ATMF 111.9bp) vs short USD $1.42bn (ATMF 16.5bp), premium-neutral | 7.6c / 6.3c | 38.1 / 31.6bp | J.P. Morgan, Issuance, pensions, and long-end spreads, Sep 2018 |
| 3M 2s10s ATMF cap, K 9.8bp | 4c | 20.1bp | J.P. Morgan, A comprehensive look at convexity hedging, Mar 2019 |
| 3m 5s30s ATM curve cap (Jul 2026) | 12c | 60.2bp | Morgan Stanley, Buy Higher Rates Protection at a 30% Discount, Aug 2026 |

The same 3m curve vol went from about 20bp (2s10s, early 2019) to about 60bp (5s30s, mid 2026). Always z-score
against the curve's own history, never against another regime.

Other 2026 curve-option structures in the sources:
- Citi: a 1y CMS 30s/5s curve cap contingent on the equity index > 110%, at 5.05c (Citi, US Rates Weekly: Can
  Secretary Bessent and Chair Warsh save the curve?, Aug 2026).
- Citi: a costless 6m 10s/2s CMS cap ladder, ATMF vs 11bp and 22bp OTM (Citi, US Rates Weekly: Pension plan for
  20s?, Oct 2026).
- Barclays: a 3m-forward 5s30s curve cap spread (Barclays, Global Rates Weekly: The urgency question, Oct 2026).
- GS: closed a long USD 3m 2s10s A+10/A+25 curve cap spread at −2 (Goldman Sachs, Global Rates Trader: Reaching
  Limits, Oct 2026).

## 4. Cross-market directionality (J.P. Morgan, A primer on Conditional Trades, May 2016)
Implied directionality = 1 − σ_EUR/σ_USD. 3M delivered = 1 − β(EUR on USD) = 1 − ρ·σ_EUR,real/σ_USD,real.
The gap is σ_EUR,imp/σ_USD,imp − ρ·σ_EUR,real/σ_USD,real: the correlation effect plus any difference between the
implied and realized vol ratios.

| Point | EUR/USD vol (as printed) | implied | 3M delivered |
|---|---|---|---|
| 1Yx1Y | 1.6 / 3.7 | 57% | 68% |
| 1Yx2Y | 1.9 / 4.3 | 57% | 65% |
| 1Yx7Y | 3.3 / 5.1 | 36% | 38% |
| 1Yx10Y | 3.8 / 5.1 | 26% | 27% |
| 1Yx30Y | 4.4 / 4.8 | 8% | −2% |
| 1Y midcurve on 1Yx1Y | 2.2 / 5.6 | 60% | 73% |

Cross-market straddles follow the same logic: buy EUR 100mm 5y5y ATM vs sell USD 125mm 5y5y ATM, delta-hedged,
because "USD vol carries a premium over EUR vol while realized are roughly the same" (Morgan Stanley, Aug 2026).

## 5. Derivations
**Correlation P&L of a delta-hedged spread option against its legs.** Take normal dynamics and gamma Γ_S on the
spread option. Short leg options with the same gamma Γ_S on A and on B. Daily P&L:

```
½Γ_S[(ΔB − ΔA)² − σ_S²dt] − ½Γ_S[ΔA² − σ_A²dt] − ½Γ_S[ΔB² − σ_B²dt]
  = Γ_S·(ρ_imp·σ_A·σ_B·dt − ΔA·ΔB)      using σ_S² = σ_A² + σ_B² − 2ρ_imp·σ_A·σ_B
  ≈ Γ_S·σ_A·σ_B·(ρ_imp − ρ_real)·dt    when leg vols realize at implied
```

This mirrors the equity dispersion result: gamma P&L = Σ(variance terms) + β_V·(ρ − ρ̂)·dt (Jacquier & Slaoui,
Variance Dispersion and Correlation Swaps). With leg vols that realize away from implied, the variance terms come
back. Vega-flat weights leave volga, and gamma-flat weights leave vega. The paper attributes about 10 points of gap
between correlation-swap strikes and dispersion-implied correlation to the volga term. The rates analogue is a
spread-vol premium that a static correlation trade does not capture.

**FVA hedge ratios.** From (T2−T1)σ_FVA² = (T2−T0)σ23² − (T1−T0)σ_MC²:
∂σ_FVA/∂σ23 = (T2−T0)σ23/((T2−T1)σ_FVA) and ∂σ_FVA/∂σ_MC = −(T1−T0)σ_MC/((T2−T1)σ_FVA). For the 6m1y10y
example: 1.5·99/94.7 = 1.57 and 0.5·107/94.7 = 0.56 (Credit Suisse, The FVA: Forward Volatility Agreement, Aug 2013).

**Flat-curve midcurve weights.** With annual-pay annuities A(n) at one flat rate, the T2-T3 forward annuity at T1 is
A(G+L) − A(G). So w13 = A(G+L)/(A(G+L) − A(G)), w12 = A(G)/(A(G+L) − A(G)), and w13 − w12 = 1 exactly. At 3.5%
this gives 5y5y weights 2.19 and 1.19 and 1y1y weights 2.03 and 1.03. At 2.5% the 6m1y10y weights are 1.114 and
0.114, within 0.002 of the FVA primer's 9.6/8.6 and 1.0/8.6.
