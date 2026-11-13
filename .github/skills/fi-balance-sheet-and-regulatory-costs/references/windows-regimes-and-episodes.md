# Reporting windows, regime breaks, gauges and dated episodes (lookup)

Companion to [SKILL.md](../SKILL.md).

## 1. Reporting-window regimes by jurisdiction

| Jurisdiction | Rule that creates the window | Visible effect |
|---|---|---|
| US | G-SIB score is a year-end snapshot; SLR is a daily average (on-balance-sheet) with off-balance-sheet at the average of month-ends | Q4 shrinkage; quarter-end pressure persists because off-balance-sheet uses month-ends; repo takes several days to normalise because trimming is easier than rebuilding (BofA, FX-Sofr primer, 31 Oct 2023; Barclays, Jan 2025) |
| Euro area | Leverage ratio reported at quarter-end and as a daily average (higher requirements and quarterly averages from Dec 2023, per Conks) | quarter-end window dressing persists; French banks pull back from US MMF repo on reporting dates |
| UK | PRA bans short-term window dressing; quarterly reporting with 42-day remittance | muted |
| Japan | banks far above requirement; fiscal year-end 1 April | JPY quarter-end widening comes from the USD side |
| Foreign banks generally | quarter-end snapshots | de-lever at quarter-ends; internal risk month-end checks and FDIC fees add month-end spikes (Conks, The Great Flattening, 4 Aug 2024) |

- The June 2019 Basel Pillar 3 change (daily plus quarter-end disclosure of SFT assets) damped spikes (BofA, 2025).
- The SLR is not the whole story: tri-party and fed-funds window dressing predates the SLR, shows up on many month-ends, and different dealers respond to different rules (Federal Reserve Board FEDS Notes, What Happens on Quarter-Ends in the Repo Market, 6 Jun 2025).
- Year-end G-SIB dieting shows most in the short xccy basis (cheap to switch back on in January) and less in repo (averaged in STWF) (Barclays, Jan 2025).
- Year-end balance-sheet constraints tend to widen SSA-EGB and covered spreads in Nov-Dec (Citi, European Rates Strategy, 20 Aug 2026).
- G-SIB regime is responsible for "around half" of year-end contractions in banks' derivative exposures such as repo (BIS, as cited in Conks, 2024).

## 2. Seasonal numbers (use as priors, then re-measure on your own data)

- German 1-day GC vs the policy-rate-based reference, end-of-month change, 8y from 2014: Jan +138bp avg; Mar -4; Jun -16; Jul +12; Sep -15; Oct +14; Dec -188bp avg (min -445). GC richens into every quarter-end and reverses the next month (BofA, Bond market seasonality explained, 6 Jun 2022).
- Quarter-end event study 2023Q1-2024Q3 averages vs four days earlier: tri-party borrowing -$45bn; sponsored reverse repo +$135bn; ON RRP +$140bn; sponsored reverse repo rate +8.5bp vs sponsored repo +2bp (so the intermediation spread widens); G-SIB non-centrally-cleared reverse repo -$30bn ($718bn -> $688bn). Foreign tri-party quarter-end drop stable at -$30bn to -$60bn in 2021-24. SOFR minus ON RRP reached +25bp at Sep 2024 and YE 2024 (FEDS Notes, 6 Jun 2025).
- Quantity response to quarter-end is stable but the price response is growing (falling elasticity); larger turns signal tight reserves rather than more window dressing (FEDS Notes, 2025).
- G-SIB FX-swap notional (4 G-SIBs): -6.2% q/q into YE19, vs -0.4% in 2018 and -8.7% in 2017 (J.P. Morgan, There is one market..., 20 Feb 2020).
- Strip the year-end turn out before extracting policy expectations; the turn is always positive, which distinguishes it from noise (Duering, 2021).

## 3. Balance-sheet capacity gauges

| Gauge | Reading | Source |
|---|---|---|
| GCF repo minus tri-party repo | up = inflexible dealer balance sheets; "as balance sheets tighten this spread tends to widen" | Conks, Money Market Update, 14 Aug 2025; Barclays, Jan 2025 |
| Cleared bilateral minus tri-party | sensitive to dealer balance-sheet capacity and positioning | Barclays, Jan 2025 |
| Interdealer repo above tri-party | structural: post-crisis rules raised the balance-sheet cost of repo | FEDS Notes, Historical Proxies for SOFR, 2019 |
| Off-the-run rich/cheap | regress the 10y off-the-run yield on the first 3 PCs of the on-the-run curve; residual = off-the-run cheapness; wide on/off-the-run spreads signal binding SLR/VaR and heavy inventory | Citi, Rates Vol Lab, 30 Mar 2020 |
| SOFR percentile spread (75th - 25th) | SOFR is bimodal; as the spread widens with balance-sheet costs the fixing moves toward the 75th percentile; SOFR - RRP regressed on it gave R^2 0.68 | Citi, FX Basis Quarterly, 13 Dec 2024 |
| Arbitrage-violation sizes | negative CDS-bond basis, SOFR > EFFR, negative swap spread: aggregate shadow cost of arbitrage capital; "can be quite high and persist for some time" | Huggins and Schaller, 2022, 2024 |
| Corporate CDS-cash basis, Treasury spline-fit RMSE, xccy basis | cross-check that the balance-sheet story is not idiosyncratic | TBAC, Charge: Swap Spreads, Feb 2021 |
| Linker vs inflation-swap deviation | average absolute deviation about 15bp implies a ~30bp corridor, read as balance-sheet cost of carrying a linker asset swap | Duering, 2021 |
| Dealer proxies | about 70% of CCAR banks (by Treasury holdings) were leverage-constrained under stress; off-the-runs are more financing-intensive | J.P. Morgan, Times like these, 10 Feb 2016 |

## 4. Regulatory timeline and what markets did

- 2015 Basel III leverage rules and 1 Apr 2020 SLR exclusion are regime breaks in swap-spread residuals: the 30y spread widened 16bp more than a TBAC model predicted since YE-2019; large residuals in 2015 and 2020 coincide with them (TBAC, Feb 2021). Do not fit across them blindly.
- SLR natural experiment (Fleckenstein and Longstaff, Treasury Richness, Journal of Finance manuscript, 2023): around the 1 Apr 2020 exclusion the event-day premium change correlated 78% with full price (R^2 61%); average premium change +3.09bp vs a daily sd of 2.06bp; a refcorp check shows Treasury richness rose 25-50bp post-crisis, so it is not solely balance-sheet cost.
- Temporary SLR relief helps intermediation (short-term repo, cash/futures basis, front-end spreads) more than bank portfolio allocation; long-end spreads are driven by structural end-user supply and demand; 30y spreads went negative in late 2008, before leverage and G-SIB constraints existed (J.P. Morgan, What about Bonds?, 2 Apr 2020; J.P. Morgan, Pension re-risking and long-end swap spreads, 3 Apr 2020).
- If USTs were exempted from the SLR, the 30y should move most because more capital is held against longer swaps; the SLR applies to banks only, not hedge funds or the buy side (Clarus Financial Technology, Swapalypse Now, 14 Apr 2025).
- 2025 eSLR proposal: for risk-bound banks the relief does little ("swapping reserves for Treasuries does not reduce SLR exposure even if eSLR were set to 0%", BofA, 25 Jun 2025). Later evidence: Big Six expanded repo books by about $300bn q/q and added USTs after the change (Conks, The Repo Rebound, 23 Jun 2026). Sources conflict, so test both.
- "Regulatory rug pull": markets price deregulation early (wider spreads); the 2025 hype trade unwound when delivery lagged. Mirror risk: consensus tighteners are exposed to a surprise SLR or RWA relief (Conks, Money Market Updates, Apr and Jun 2025).
- Catalyst cadence: rule changes normally need a comment period of at least 3 months, but interim final rules can be fast (Barclays, Jan 2025; J.P. Morgan, Funding market interventions Part II, 20 Mar 2020). Use sample splits, not event dates, because regulation arrives as long overlapping processes (Mixon and Onur, CFTC, Apr 2020).
- LCR-driven bank buying richened UST vs OIS by 10bp+ in 2014 but only once bank holdings actually grew; spreads do not efficiently anticipate large real-money flows (J.P. Morgan, What does the SRF mean for swap spreads?, 12 Jul 2019).
- HQLA: at 4Q19 banks held at least $375bn of HQLA above the minimum; LCR relief is a poor fix because raising cash means selling securities into a balance-sheet-constrained market (J.P. Morgan, Funding market interventions Part II, 2020). A binding-constraint screen over CET1, Tier 1, Tier 1 leverage, SLR vs CCAR buffers and G-SIB surcharge gave about $80bn "excess" capital across the G-SIB complex.

## 5. Dated trades and rules (for calibration, not for replication)

- J.P. Morgan, 20 Feb 2020: receive $25k/bp 2Yx1Y EUR/USD xccy basis (21 Feb 2022-21 Feb 2023) at -12.8bp; rationale: G-SIB daily averaging means less FX-lending capacity.
- Citi, 13 Dec 2024: pay 3m1y SOFR/TONAR FX-OIS basis, 25k DV01, at -38bp, carry about 3bp over 3m; risks: VaR shock or Q1 banking stress; right-way risk to G-SIB relief.
- Citi, Dec 2018-Jan 2019: 2y Treasury-futures vs OIS widener opened 14 Dec 2018 at -20, closed 17 Jan 2019 at -16.2, +$210k; closed because year-end G-SIB data showed fragile GC (Citi, US Rates Weekly, 18 Jan 2019).
- Barclays, Sep 2026: long belly (7y) swap-spread wideners; Barclays frames swap spreads as "carry trades that require balance sheet capacity, stable funding conditions, and smooth Treasury market functionality".
- BIS Quarterly Review, Dec 2025 (Box B): basis arises from dealer balance-sheet costs, liquidity premia and delivery options; risks are funding or margin spikes (2020) and leveraged unwinds.

## 6. Market notes beyond the USD

- EUR: German GC capped by the deposit facility rate; if banks are balance-sheet constrained the cap becomes the main refinancing rate (Citi, FX Basis Quarterly, Dec 2024). Bund asset-swap spread starts negative (capital basis) and rises with maturity. EUR is the most acute market for xccy-basis risk from daily-averaged leverage.
- GBP: the very steep BoE schedule predicts a steeper SOFR-swapped gilt curve than UST; lower haircuts on short gilts support 7y gilts vs swaps (BofA, Global Rates Weekly, 2 Oct 2026). GBP IRS clearing is nearly all at one CCP.
- JPY: banks far above requirements; USD funding demand is driven partly by leverage-ratio disclosure, SLR, LCR/NSFR and US prime-MMF reform (J.P. Morgan, Drivers of cross currency basis, 11 Mar 2015). Clearing is split between LCH and JSCC; JSCC (like Eurex) offers cross-margin offsets against its bond futures, one of the CCP-basis drivers listed in SUERF Policy Brief 940 (Jul 2024).
- AUD: 1y bank-bill-OIS (about 4-9bp) and 1y 6s/3s basis (about 16-24bp) stayed wide in 2024 because banks term out liabilities beyond the LCR window (J.P. Morgan, Cross currency basis 4Q24 Outlook, 26 Sep 2024).
- SEK: the Swedish stability fee on bank liabilities has influenced SEK/USD xccy swaps (Darbyshire, 2022, Ch.17).
- CAD/EUR/JPY: the year-end-turn xccy basis was at multi-year tights in 2026 before any G-SIB change (Citi STIRT Weekly, 14 Aug 2026).
- CHF/NZD/NOK: no balance-sheet-specific evidence in the sources; do not extrapolate the US rules; ask for local leverage-ratio and reporting-date rules.
