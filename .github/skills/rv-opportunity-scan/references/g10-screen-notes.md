# G10 screen notes: what changes market by market

Companion to [SKILL.md](../SKILL.md). Levels and z-scores are dated snapshots from the cited desk notes, shown so the agent knows
the scale of a "normal" reading. They are NOT current market data: always recompute from the canonical tables.
Convention reminders: bp; curve A-B = longer minus shorter; fly = 2 x belly - wing - wing.

## Universe and realised-vol scale by currency

| Ccy | Practical RV universe | Realised vol scale / typical screen outcome | Source |
|---|---|---|---|
| USD | Full grid: outrights to 30y, forwards to 10y20y and 25y10y, curves, flies, ASW to 30y, STRIPS, CTDs by futures contract | Long-end forward-curve pairs about 4.1-4.2 bp/day (2019), 4.7-5.3 (2023). Printed 3m vol (2026): flies 2-18bp, curves 2-23bp, outright forwards 25-55bp | Citi Rates Vol Lab 5 Dec 2019, 12 Jun 2023; GS Best Trade 30 Sep 2026 |
| EUR | Swap curve to 30y with forwards to 30y10y; EGB spreads vs Bund (OAT, BTP, SPGB, OLO, DSL); Bund ASW | Forward-curve BE/RV 0.60-1.48 (Jan 2020). Hybrid Euribor fixing methodology adds daily fixing vol to short basis | Citi 17 Jan 2020; Nordea 23 May 2019 |
| GBP | Swap curve; forward-curve pairs 15y10y/25y10y; 5y5y/10y20y; 5s10s30s | Lowest BE/RV of G10 (0.00-0.89, Jan 2020) because the 20y is rich (ALM receiving) and carry is mostly positive | Citi 17 Jan 2020; GS Market Movers |
| JPY | Curve to 30y; JGB CTD basket 7-10.5y | Lowest realised vol (2.4-3.1 bp/day vs 3.9-4.7 elsewhere); vols collapsed after the 2016 YCC decision, so any vol-based filter must use a post-regime window | Citi 17 Jan 2020, 30 Mar 2020 |
| CAD | Curve to 30y, forwards to 20y5y | BE/RV 0.45-1.82 (Jan 2020), the widest range | Citi 17 Jan 2020 |
| AUD | Curve to 30y; 1y-forward 2s5s10s fly | Fly of -100k/+100k/-100k DV01 had HVaR 801k (2026) | Citi Radar 13 Aug 2026 |
| NZD | Curve to 20y: 10y5y/15y5y/20y5y fly, 15y5y/20y5y | Screens high on 3-factor score (1.89, 1.58) in Sep 2026 | GS Best Trade |
| CHF | Short: 1y1y/2y1y, 1y 2s5s | 1y1y/2y1y carry 7.7bp on vol 12.3 (Sharpe 1.26) in Sep 2026 | GS Best Trade |
| SEK | Smaller universe: outrights to about 1y10y / 5y5y | thin: fewer structures, so fewer independent bets | GS Best Trade |
| NOK | Universe to about 10y: 5y1y/6y2y/8y1y fly | 2y1y/3y1y/4y1y: carry 5.0bp on vol 10.4 | GS Best Trade |

Rule: scale lookbacks and thresholds by currency vol, not by a global number. The z-score removes scale; carry-to-vol and BE/RV do too;
bp hurdles (costs, stops) do not, so set them per currency.

## Regime exclusions before computing a statistic
- USD: exclude the zero-lower-bound years (fed funds <= 50bp) from vol-vs-rates regressions (Citi, Trading long-dated convexity,
  9 May 2019). EUR: exclude pre-2016 (Citi, In search of cheap vol, 17 Jan 2020).
- A vol/rate beta can flip: the 10y10y vol-to-rate beta flipped in 2025; re-check before trusting a vol-rate relation (Citi, Fading
  vega dislocations, 5 Oct 2026).
- SOFR has a break in its time series (post-LIBOR); use fitted-curve or par-curve histories for long samples (Huggins and Schaller, 2024).
- Policy-rate regime changes also move "normal" levels: a 5y window straddling a hiking cycle gives z-scores that mostly measure the cycle.
  Report z at two lookbacks (1y and 3y) and prefer candidates where both agree.

## Market-specific facts that change a screen
USD
- Matched-maturity and proceeds ASW differ for low-price bonds; OIS-based spreads sit about 4-6bp above SOFR-based (GS UST RV, 25 Sep 2026).
- SOFR-ASW is unaffected by capital-cost terms; ESTR/LIBOR-type ASW add a capital basis (cost of equity x risk weight x capital ratio,
  10% x 1.6% = 16bp), so the same bp number means different things (Huggins and Schaller, 2024).
- Callable-issuance rules (Formosa) were expected to richen the 30y tail vs 10y/5y in 1-2y expiries (2017); callable supply is converted to bucketed
  vega before judging vol screens (Citi, Long Live Formosa, 9 Jan 2017; Fading vega dislocations, 5 Oct 2026).
- Board (futures option) vs swaption ratios sit near 1.0 (Citi, Jun 2023).

EUR
- EGB comparison: Dutch 10y cheapness from a new DSL (5.8bn); April redemptions tighten the French front end and Spanish 5y; redenomination
  risk sits in the spread (BofA, European Rates Viewpoint, 21 Mar 2018; Huggins and Schaller, 2024).
- ECB: policy-path screens depend on staff-projection meetings (Mar, Jun, Sep, Dec) where cuts are more likely; "the number of policy rate cuts is more important
  than the timing of the first cut" (Nordea, 17 Jan 2024).
- EUR Bund ASW fair value decomposition: -16bp (unsecured-secured, g 10%) + 15bp (adjusted CDS) - 6bp (specialness) = -7bp (Huggins and Schaller).

GBP
- Spot SONIA settles with 0 business-day lag (others usually 2); BoE announces the day after the meeting (a Thursday), so meeting-date step
  curves jump on publication dates (Deriscope, 18 Feb 2024).
- OFGEM price caps delay energy pass-through: cuts priced to Dec 2026 fell from about 50bp to about 2bp (JWS Macro, 8 Mar 2026).

JPY
- JGB futures CTD basket 7-10.5y; switches among similar bonds are common; official buying can cut liquidity to a trickle, so screen
  liquidity first (Huggins and Schaller, 2024).
- 10y JGB near 3% (Aug 2026), currency-hedged G2 MBS yield about 38bp below it (Citi Agency MBS Weekly, 21 Aug 2026).

AUD, NZD, CAD, CHF, SEK, NOK
- AUD and NOK sold off to cycle wides despite a low energy weight in CPI; the energy-beta ranking (energy share of the CPI basket vs the
  1-week change in 1y1y) flags outliers that reflect positioning, not fundamentals (JWS Macro, 8 Mar 2026).
- RBNZ was more dovish than RBA (2016 receive-AU/pay-NZ 2y idea, BofA, 2 Jun 2016): cross-market screens in the Antipodes need the
  policy-path view, not just the z-score.
- Smaller markets (CHF, SEK, NOK) have fewer liquid tenors; DV01 minimums (100k DM) may not be executable. Check liquidity before ranking.

## Cross-market comparability checklist
1. Same ASW flavour and same swap index (SOFR vs OIS vs LIBOR-type) on both sides.
2. Same repo definition (general collateral vs desk repo) in carry.
3. Same horizon and vol window for carry/vol.
4. Level z computed on the same lookback and sample start per market.
5. Convert to a common unit (bp) and state the sign convention per market: US swap spread = swap minus Treasury (usually negative);
   EGB ASW = bond minus swap (positive = bond cheap).
