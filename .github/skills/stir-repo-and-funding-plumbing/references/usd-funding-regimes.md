# USD funding regimes: levels, regressions, monitors and calendar

Companion to [SKILL.md](../SKILL.md). Use it to place the current USD money market in a regime and to pick the monitors.

**Caveat.** Every coefficient below is a published fit from one note, on one sample, for one regime. They are direction and scale only. Refit on your own canonical data before using a number, and expect R-squared below 0.2 in recent regimes. Dates and levels are as printed by each source.

## 1. Regime map

| Regime (approx.) | ON RRP | Reserves and collateral | What moved |
|---|---|---|---|
| Ample / abundant, 2020-21 | >$500bn, often $1tn+ | Reserves high, cash excess | SOFR pinned near ON RRP; EFFR-IORB sensitive to reserves |
| Drain, 2022-24 | Falling from peak | QT drains RRP first | SOFR anchored near RRP until RRP near zero |
| Excess collateral, late 2024-2025 | Near zero | Reserves ~$3tn, TGA swings | SOFR-IORB and TGCR-RRP positive; FF-SOFR tight |
| Post-QT, 2026 | Near zero | RMPs (reserve management purchases) | Reserves "lightly abundant"; SOFR near or below IORB at times |

Heuristic from a 2025 note: ON RRP at or above $500bn keeps tri-party and SOFR anchored near RRP, because MMFs need RRP plus a few bp to leave the Fed. Below $500bn, SOFR is pushed up and the SOFR/FF basis tightens (BofA, US Treasury repo primer, Jul 2025).

## 2. Liquidity regressions (bp; x as defined)

| Spread | Form | Sample / regime | Fit | Source |
|---|---|---|---|---|
| SOFR-IOER | -2.3505 x (Reserves/GDP) + 31.678 | from Jun 2020 | R2 0.85 | BofA, Fed QT beyond taper, Oct 2021 |
| SOFR-IOER | 1.2102 x (MktDebtExFed/GDP) - 95.008 | from Jun 2020 | R2 0.67 | same |
| FF-IOER | -1.0997 x (Reserves/GDP) + 14.363 | from Jun 2020 | R2 0.72 | same |
| SOFR-IORB | -34.59 ln(x) + 88.95 | 3Q20-1Q21, x = (ON RRP + reserves)/GDP, % | R2 0.73 | BofA, Fed plumbing, Jul 2025 |
| SOFR-IORB | -4.96 ln(x) + 4.53 | 2Q21-1Q24 | R2 0.06 | same |
| SOFR-IORB | -9.16 ln(x) + 16.6 | 2Q24-mid-Dec 2024 | R2 0.17 | same |
| SOFR-IORB | -8.065 ln(x) + 13.912 | since mid-2024, x = (reserves + ON RRP)/GDP | R2 0.34 | BofA, Repo sensitivity, May 2025 |
| EFFR-IORB | -10.55 ln(x) + 26.54 | 3Q20-3Q21 | R2 0.74 | BofA, Monthly rates models, Apr 2025 |
| EFFR-IORB | -0.074 ln(x) - 6.82 | later, sticky regime | R2 0.02 | BofA, Monthly rates models, Aug 2025 |
| EFFR-IORB | -0.448 ln(x) - 5.8136 | since mid-2024 | R2 0.14 | BofA, Repo sensitivity, May 2025 |

Log-reserves form (BofA, Fed QT beyond taper, 2021): SOFR-IOR 2015-19 y = -42.29 ln(x) + 314.47 (R2 0.60); from Jun 2020 y = -25.59 ln(x) + 202.56 (R2 0.91). FF-IOR 2015-19 y = -30.24 ln(x) + 224.36 (R2 0.91); from Jun 2020 y = -12.26 ln(x) + 96.63 (R2 0.74). The beta to reserves falls as reserves become abundant. A Feb 2022 refit said the SOFR and FF relation to IOER could flip when reserves fall below about $2.7tn (BofA, SOFR primer, Feb 2022).

**Weekly-change betas** (Citi, Short-end notes, Jun 2025; Citi's SOFR/FF is FF minus SOFR, so it falls when SOFR rises, which is why reserves carry a positive sign there and a negative sign against SOFR-RRP; bp per $100bn of weekly change; t-stat in brackets; columns are reserves, T-bills, bills-minus-reserves):
- SOFR-RRP 2013-25: reserves -0.67 (-3.3); T-bills 0.27 (0.7); bills-minus-reserves 0.62 (3.3).
- SOFR-RRP 2021-25: reserves -0.39 (-2.4); T-bills 0.07 (0.2); bills-minus-reserves 0.33 (2.3).
- SOFR-FF 2010-25 (repo proxies SOFR before 2018): reserves 0.84 (3.7); T-bills -0.41 (-0.9); bills-minus-reserves -0.79 (-3.8).
- SOFR-FF 2021-25: reserves 0.38 (2.3); T-bills -0.07 (-0.2); bills-minus-reserves -0.32 (-2.1).

Full-sample betas differ a lot from post-2021 betas. The T-bill coefficient alone is usually insignificant; the bills-minus-reserves composite is the robust term. Keep bills in the model ahead of a TGA rebuild, since bills can capture non-linear SOFR moves when reserves are flat.

**Bill to RRP** (BofA, Aug 2025, settlement dates since Aug 2023): dRRP = -0.52 x dNetBills - 8.3, R2 0.20. Each $1bn of net new bills cut ON RRP by about $0.52bn. The beta falls toward zero as cash gets sticky. Conks (2025) states the same heuristic as "roughly half the magnitude". Interpretation: bills drain MMF cash from RRP first, reserves only after RRP is exhausted.

**SOFR-FF path model** (Citi, Jun 2025): regress SOFR/FF on reserves and bills outstanding with month-end controls; apply betas to projected TGA and bill paths; overlay turn effects; compare with futures month by month.

## 3. Reserve-adequacy gauges

| Gauge | Definition | Reading | Source |
|---|---|---|---|
| Reserve demand elasticity (RDE) | Change in EFFR-IORB (bp) per 1pp change in reserves/bank assets | ~0 = ample; ~-1.3 to -1.5 in 2019; ~0 in 2021-26. End of QT when slightly negative and significant | Barclays, Short-rate primer, Jan 2025; Conks, MMU, 2024-25 |
| Reserves / bank assets | Fed-internal zones as quoted by Conks, 2025 | Abundant >13%; ample 11-13%; scarce <11%. Dec 2024 edition used 14% and 11-14% | Conks, MMU, Jan 2025 |
| Fed liquidity ratio | (reserves + ON RRP) / bank assets | ~25% in 2022 falling to ~12% (Oct 2025), ~11-12% (2026) | Conks, The QT Enigma, Oct 2025 |
| LCLoR | Lowest comfortable level of reserves | Conks ~$2.7-2.9tn; Fed staff ~$2.2-2.7tn (estimates drift by edition) | Conks, MMU and Dealer Congestion, 2024-25; Waller ~$2.7tn cited in Conks, Shadow Cash, Jul 2025 |
| Reserve gap above LCLoR | Reserves minus LCLoR once RRP is drained | ~$400bn cushion estimated mid-2025 | Conks, Dealer Congestion, Jun 2025 |

Threshold choice changes the scarcity date. Do not hard-code a single LCLoR.

## 4. Monitors and their warning reads

| Monitor | Definition | Read | Source |
|---|---|---|---|
| EFFR-IORB | Fed funds minus IORB | >0 = scarcity; "if EFFR > IORB, the Fed likely starts adding reserves" | Conks, MMU, Oct 2024 and Jun 2025 |
| SOFR-IORB | Repo minus IORB | >0 = banks lending reserves into repo (drag on FF); bank lending in repo typically rises when repo is 5-10bp+ above IORB | BofA, US Treasury repo primer, Jul 2025 |
| TGCR-RRP | Tri-party GC minus ON RRP | >0 = excess collateral; <0 = excess cash | Conks, MMU, Jan 2025 |
| GCF-TPR | Interdealer GC minus tri-party | Dealer balance-sheet capacity; typically 0-10bp in 2023-24, spikes 45-65bp around year-end 2024 | Conks, MMU, Nov 2024-May 2025 |
| SOFR-EFFR | Repo minus FF | FHLB repo demand; typical -5 to +15bp in 2024-25 | Conks, MMU, Jan 2025 |
| Share of trades above IORB | Interdealer prints above IORB | ~50% in Oct 2024, "much lower" than pre-2019 | Conks, MMU, Oct 2024 |
| SRF take-up | Usage vs minimum bid | Bids above the minimum = real shortage, not arbitrage | Conks, Repo Defensive II, Nov 2024 |
| 99th percentile minus median | Dispersion tail | Spikes to ~50bp (SOFR-IORB 99th) mark funding stress the median hides | Conks, QT Enigma, Oct 2025 |

Stress is judged when EFFR-IORB, SOFR-IORB, the share of prints above IORB and SRF take-up move together. A quarter-end repo spike alone is not stress (Conks, MMU, Oct 2024).

## 5. Balance-sheet identities and reserve drains

- Fed liabilities: TGA, currency, reserves and reverse repo (ON RRP plus foreign RRP) move one-for-one against each other, all else equal. TGA up means reserves down (BofA, Fed plumbing, Jul 2025; Conks).
- Reserve drains in order (post-debt-limit sequence, Conks 2025): RRP drains first; reserves fall only when RRP is near zero. Foreign repo pool (FRP) is a further drain; unwinding it would release reserves but is considered unlikely.
- QT accounting (BofA, May 2022 to Jul 2025): ON RRP fell about $1.8tn while reserves rose about $32bn. "Stable reserves" meant banks were competing for liquidity.
- Debt-limit template: bill paydowns and extraordinary measures shrink bills, MMFs re-park in RRP. Resolution means TGA rebuild plus a bill deluge that drains RRP then reserves, and funding tightens.
- TGA rebuild pace: BofA's rule of thumb is about 51 business days to close 100% of the gap after a resolution; about 20 business days closes roughly half (BofA, US Rates Viewpoint, Jul 2025). Use only as a prior.
- Repo impact depends on the pace of the TGA rebuild and on reserve demand, not on the stock of bills alone (Citi, Short-end notes, Aug 2026).

## 6. Calendar: what moves funding, and when

| Date pattern | Effect | Notes |
|---|---|---|
| Month-end | Up, larger at quarter-end | Foreign-bank and Canadian-bank balance-sheet trimming |
| Quarter-end (+/-2 business days) | Up | Fed metric window; tri-party stays below SRF while cleared segments spike |
| Year-end | Largest turn | US G-SIB score measured on year-end snapshot; ON RRP rises as dealers reject MMF cash |
| Corporate tax dates (15 Apr, 15 Jun, 15 Sep, 15 Dec) | Up | TGA +$185bn on 15 Apr 2025 drained reserves in one day |
| Coupon settlements (15th, month-end) | Up, larger when reserves are thinner | Settlement size tracker, BofA May 2025 |
| GSE P&I float (MBS cash to ~25th-26th) | Depresses repo before the 25th-26th | Conks, Repo Rebound, Jun 2026 |
| FOMC meeting | Fed decisions effective the day after | Use the day-after date for stub FF windows (Citi, Learning on the job, Aug 2019) |
| Friday to Monday | Three-day roll, up; Monday cash returns, down | Lehman Short-End, Jul 2007 (old; direction still holds) |

Corridor levels to anchor the calendar: see the snapshot table in [worked-examples.md](worked-examples.md).

## 7. Corridor snapshots (as printed)

| Date | IORB | ON RRP | SRF min bid / DW | EFFR | SOFR | Source |
|---|---|---|---|---|---|---|
| Jul 2025 | 4.40 | 4.25 | 4.50 | 4.33 | 4.28-4.30 | BofA Fed plumbing and Conks |
| Oct 2025 (23 Oct) | 4.15 | 4.00 | 4.25 | 4.11 | 4.24 | Conks, QT Enigma, Oct 2025 |
| Nov 2025 | 3.90 | 3.75 | 4.00 | 3.88 | 4.05 | Conks, Post-QT Era, Nov 2025 |
| Mar 2026 | 3.65 | 3.50 | 3.75 | 3.64 | 3.67 | Conks, Nothing Ever Happens, Mar 2026 |

Global ladder (Mar 2026, as printed): FIMA repo rate 4.00; swap lines 3.90; T/N FX-swap implied 3.76; SRF/DW 3.75; GCF 3.73; SOFR 3.67; IORB 3.65; EFFR 3.64; FRP/RRP 3.50.

## 8. Outlook items (dated; verify before use)

- Q4 2026 (Citi, Oct 2026): SOFR below IORB through October; about $360bn of net private bills in Oct-Nov, about -$50bn in December; TGA target $850bn.
- Reserve management purchases: paused until mid-Sep 2026 (Citi, Aug 2026); the Fed later announced an end to RMPs (BofA, Oct 2026). Conks (Apr 2026) estimated RMPs of about $200bn per year as a dampener. Check current status.
- Debt-limit timing: 2027 X-date cited by Citi (Oct 2026) with headroom binding in Q1/Q2 2027.
- Target-rate debate: a proposal to move the unofficial target from EFFR toward TGCR (Logan, Sep 2025) would reshape the SOFR-FF basis and FF futures. Conks rated TGCR as the likely target within two years. Treat as a scenario, not a fact.
- Clearing mandate: sources cite a June 2027 repo clearing deadline, with an expected exodus from uncleared repo into year-end; SOFR may rise on migration (Conks, Apr 2026; Citi).
