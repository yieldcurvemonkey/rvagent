---
name: fi-balance-sheet-and-regulatory-costs
description: 'Prices bank and dealer balance-sheet and regulatory costs (SLR/eSLR, leverage ratio, G-SIB surcharge, RWA, LCR/NSFR, repo haircuts, initial margin, PFE/SA-CCR) as a shadow cost in RV, so "arbitrages" that do not close can be judged as free money or compensation. Gives ROE-hurdle and breakeven-spread maths for swap-spread wideners and tighteners, haircut-cost and carry/vol hurdles, leverage-ratio hurdle for cash-futures basis, a binding-constraint screen, window-dressing calendars by jurisdiction, and a bundled calculator. Use when asked about SLR relief or eSLR, Basel endgame, G-SIB year-end, quarter-end turn, balance-sheet capacity, haircut cost, ASW or Bund/BTP/gilt haircut differences, basis trade funding, implied repo vs term repo, SOFR vs EFFR, IM/margin cost, ROE on a spread trade, window dressing. Spread levels and fair value: spread-swap-spreads-and-asw.'
---

# Balance-sheet and regulatory costs as a shadow price

Dealers and banks are the marginal arbitrageurs in swap spreads, asset swaps, cash-futures basis, repo, FX swaps and xccy basis, and they are
limited by regulatory ratios and internal capital rules, not by price. A relationship such as "swap = Treasury yield", "SOFR <= EFFR" or "ASW <= CDS" holds only
while balance sheet is slack. When it binds, the violation is the aggregate shadow cost of the binding constraint: the improvement in a bank's objective if the constraint
were relaxed (Huggins and Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024). This skill turns that into numbers: what a trade costs in capital,
what spread clears the hurdle, which constraint binds for which bank, and when the calendar makes the cost jump.

## When to use
- A spread "should" be arbitraged away but is not: negative USD swap spreads, SOFR above fed funds, implied repo above term repo, ASW far from CDS, xccy basis at year-end.
- "Is this swap-spread widener/tightener attractive after capital?", "what does SLR/eSLR relief do to 10y/30y spreads?", "does Basel endgame matter for this trade?"
- Sizing the haircut and margin drag in a bond-vs-swap, bond-vs-bond across issuers (BTP-Bund, gilt vs UST), basis or repo-financed RV trade.
- Trade spans a quarter-end, year-end or G-SIB snapshot date, or the user asks whether repo/FX-swap/basis is cheap because dealers de-lever.
- Pre-trade devil's-advocate check that the carry is not just compensation for balance-sheet cost (hand-off to [rv-devils-advocate](../rv-devils-advocate/SKILL.md)).

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). Never invent values; if one is missing, ask the user or the data adapter.

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Swap spreads or ASW by tenor | `swap_spreads` | daily, >= 3y (spans at least one regulatory regime) | read `sign_convention`; US `swap_minus_govt`, EGB ASW `govt_minus_swap` |
| Repo rate and haircut by collateral, term, segment | `repo_rates` | daily; `haircut_frac`, `segment` (triparty, dvp, gcf, sponsored, bilateral) | haircut is often missing: ask, do not assume 0 |
| Overnight fixings with percentiles and volume | `rate_fixings` | daily, with `p25_pct`, `p75_pct`, `volume_ccy` | SOFR bimodality, SOFR minus RRP and similar |
| Futures prices (basis, implied repo) | `fut_quotes`, `fut_static`, `fut_basket` | daily | cash-futures basis hurdle |
| Bond yields and statics | `bond_quotes`, `bond_static` | daily | maturity bucket for haircut and PFE |
| Par OIS curves and xccy basis | `curve_par`, `basis_swaps` | daily | funding and window-dressing gauges |
| Central-bank balance-sheet series and bank regulatory ratios | `macro_series` (series_id per bank/aggregate; `<CC>-GSIB-<BANK>-SLR` unit `pct`, `-SCORE` unit `score`, `-SURCHARGE` unit `pct`) | quarterly/monthly | the per-bank ratios are user-supplied from public disclosures: the contract fixes the series pattern, not the data |
| Parameters the market does not publish | user / desk | per trade | cost of equity, required ROE, IM per CCP model, haircut agreed with the counterparty |

## Method

### 1. Identify the marginal balance-sheet player and the binding constraint
1. Name who clears the trade (US G-SIB dealer, foreign bank, non-G-SIB, hedge fund via prime broker or sponsored repo, insurer, pension). Constraints differ: the SLR applies to banks only; hedge funds face haircuts and margin instead.
2. Capital held = max(risk-based requirement, leverage requirement), not their sum. Compute for each bank the excess over each test (CET1, Tier 1, Tier 1 leverage, SLR, CCAR buffers, G-SIB surcharge) and take the one with the least slack (J.P. Morgan, Funding market interventions Part II, 20 Mar 2020). Example: RWA needs 100, SLR needs 60 -> hold 100; cutting the SLR requirement to 50 frees nothing for a risk-bound bank (Conks, Money Market Update, 15 Mar 2025).
3. Binding constraint flips by bank and date: in 2022 only two US G-SIBs were SLR-bound (JPM, MS), in mid-2024 a different pair (GS, MS; JPM briefly) (Conks, The Fed's Relief Valve I, 7 Mar 2025). Treat "SLR relief -> more UST intermediation" as a hypothesis per bank, not a rule. USTs carry 0% risk weight in the banking book but attract risk-based charges in dealer trading books, and repo financing creates counterparty RWA, so RWA can bind even when SLR is relaxed (BofA, Fed's SLR proposal: underwhelming, 25 Jun 2025).
4. Rule of thumb: leverage ratio binds on short-dated, large-notional, thin-margin activity (repo, cash-futures basis, front-end spreads); RWA and market-risk capital bind on long-dated derivatives (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022).
5. If the constraint is binding, the shadow cost is the return on the marginal asset that would be sold to make room (7% asset sold -> 7% shadow cost even if marginal funding is 4%), not the funding rate. Banks try to equalise shadow costs across constraints (Huggins and Schaller, 2024, Box 18.1).

### 2. Haircut cost (financing drag)
- `haircut_cost_bp = haircut_frac x excess_funding_bp` per year, applied to the notional financed. Haircut = collateral value minus cash lent (100 posted, 95 borrowed: 5 funded elsewhere). It matters only to the extent the replacement funds cost more than repo.
- Choose the excess by who funds it (Huggins and Schaller, 2024): from reserves, IORB minus SOFR (5.40% vs 5.30% in Oct 2023 -> 10bp); from equity, about 10% cost of equity (US G-SIBs) or about 600bp over the short rate for European banks (cost of equity about 10% vs ESTR 3.9%). Default for "your" spread: 500-600bp if the haircut is equity-funded at a bank on the margin, 10-50bp if the funder has spare reserves or unsecured funding; show both, because the marginal participant's cost of equity and haircut are unobservable. Compute "your" spread from "the" spread.
- Repo interest with haircut = dirty price x (1 - haircut) x repo rate x days / 360 (BofA, US Treasury repo primer, 7 Jul 2025); the divisor is the market's money-market basis: 360 for USD, EUR, CHF, SEK, NOK, 365 for GBP, JPY, CAD, AUD, NZD (check [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md)). Tables of Fed, BoE and ECB schedules and private-market haircuts: [haircut-schedules-and-repo-data](references/haircut-schedules-and-repo-data.md).
- Cross-market comparison: haircut cost differences = (haircut_A - haircut_B) x excess cost, e.g. BTP minus Bund at a 10y bullet: (11.5% - 3.0%) x 600bp = 51bp (book: about 47bp; 54bp at 30y). Because schedules rise with maturity, they steepen every bond-vs-swap curve and widen weaker credits. Caveat from the authors: assumes identical positive excess funding cost and identical credit risk, "too restrictive to be practical but illustrative".
- Decomposition: SOFR-ASW is approximately specialness (<= 0) + adjusted CDS + haircut cost (>= 0). Without a haircut term the model underestimates the 5y UST SOFR-ASW; adding the haircut cost (2% x 500bp excess over SOFR, about 10bp) fits (Huggins and Schaller, 2024). For US and Germany the adjustment is small at the front but rises with maturity, so adjust when comparing different maturities.
- Haircuts are counter-cyclical (rise in stress) and can be changed unilaterally by a CCP; hedging the price risk does not hedge the margin risk.

### 3. Swap-spread widener: ROE and breakeven spread
Trade (US convention, spread = swap rate - govt yield, negative when swaps trade below Treasuries): buy a matched-maturity Treasury financed in repo and pay fixed on a cleared swap (receive floating). Long bond, short swap duration: DV01-neutral; profits if the spread rises (widens toward zero or positive). Per unit of bond notional, one-year hold, carry and spread in bp p.a. (the script takes the rate levels in pct and the spread in bp):

```
carry_bp  = float - (1 - h) x repo - (h + im) x fund - spread
exposure  = 1 + h + im + pfe              # gross bond + haircut + IM receivable + PFE add-on
equity    = SLR x exposure
ROE       = carry x (1 - tax) / equity
breakeven spread = float - (1-h) x repo - (h+im) x fund - target_ROE x equity x 10^4 / (1 - tax)
```
- Leg cash flows: receive floating index; pay repo on (1 - h) of the bond; fund the haircut h and the swap IM at an unsecured/opportunity rate `fund`; the swap pays fixed = bond yield + spread, so a negative spread is carry earned.
- Largest capital item is the gross cash Treasury (financed notional, not the net repo liability); ROE is highly non-linear in SLR (FRBNY, Boyarchenko et al., Negative Swap Spreads, Oct 2018).
- Defaults: SLR 5% at a US G-SIB holding company and 6% at its insured depository (eSLR, pre-2025 proposal; use 5-6%), 3% for others; required ROE 10-15% (dealer target about 15%); IM 3-4% of notional for a 10y cleared swap (verify the CCP's model; IM is roughly a 99% move over the margin period plus replacement cost, Tuckman and Serrat; 3.9% is the FRBNY assumption); PFE add-on 0.0% (<= 1y), 0.5% (1-5y), 1.5% (> 5y) of notional; `fund` the bank's marginal unsecured cost, not repo; tax 0 unless comparing to an after-tax target (TBAC uses 20%).
- Reading `cushion_bp = breakeven - spread` from the script: negative means the spread is not yet wide enough (more negative needed) to pay the hurdle; positive means the trade clears it. Wideners are attractive when the observed spread is below (more negative than) the breakeven.
- Carry/vol hurdle (when risk-based capital rather than leverage binds, post-reform): banks optimise carry per unit of risk. Per tenor compute net carry (bp) and 1y annualised vol of the spread (bp); hurdle carry/vol = 0.25; solve for the spread at which carry/vol = 0.25; widening potential = implied spread - current spread (Barclays, Swap spreads: the Bright Spot in US rates, 30 Sep 2026). In that table carry changes only about 0.1-0.65bp per 1bp of spread across tenors (so it is not a pure spread effect), which means the implied spread must come from a full carry model, not from linear rescaling.
- Simple TBAC cross-check: carry of buying a UST on asset swap ~ sum of (-swap spread + (Libor - repo)); at 5% leverage ratio, 12% after-tax ROE, Libor-repo 15bp, 20% tax, the spread must be below -60bp (TBAC, Charge: Swap Spreads, Feb 2021).
- Missing carry items that sink spread trades: repo haircut, low coupon vs yield-to-maturity raising financing, term-repo roll, clearing-broker margin financing, capital, overheads (Clarus Financial Technology, Swap Spreads For Dummies, 23 Nov 2015).
- SOFR swap-spread decomposition (BofA, Taking a look at SOFR spreads, 6 Oct 2020): (1) balance sheet: required ROE 1-2% at a 9% leverage capital ratio = 10-20bp; (2) repo vs SOFR availability buffer = 2-3bp (1 sd of triparty - SOFR since Aug 2014, about 3bp); (3) crisis illiquidity premium 1-2bp; total 13-25bp, each term rising with maturity. Balance-sheet term about 10bp of the 5y's 15bp.

### 4. Cash-futures basis: leverage-ratio hurdle
- Buying $100mm of bonds on 3m repo vs short futures creates $100mm of leverage exposure; capital = LR x exposure: 3% -> $3mm, 6% (US G-SIB) -> $6mm. At a 10% p.a. return on capital over 3m, minimum net basis = 100 x LR x ROCE x days / 360 = 7.5 cents per 100 face at 3% LR (15 cents at 6%) (Quantitative Finance Stack Exchange, "Funding Treasury net basis trades and balance sheet", 6 Apr 2019). Applies both ways (repo or reverse repo are SFT exposure). Netting can reduce it. Function `basis_lr_hurdle` (use `day_basis=365` for GBP, JPY, CAD, AUD, NZD).
- Sanity check on a return: LR 6% means $60mm of capital per $1bn; a 2-3 tick profit (about $200k per $1bn) is 0.33% on capital (0.66% at 3%); banks reject about 5% RoC (QFSE, "Is my thinking on futures implied repo correct?", 9 Nov 2019).
- Profitability of the basis trade: repo rate + cost of posting IM/VM on the futures < futures-cash basis (CFTC Market Risk Advisory Committee, The Treasury Cash-Futures Basis Trade, Dec 2024). Implied repo minus term repo is governed by balance sheet (LR/SLR, G-SIB year-end), operational risk and stress; the gap persists because the trade spans year-end when banks shrink, and few banks or non-banks can participate. See [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md).
- Haircut = leverage: zero-haircut bilateral repo lets a fund run $200m of position with no cash; a 2% haircut needs $4m. Studies assume about 20x leverage; so the funding side of the trade is a haircut/margin-availability risk (see Pitfalls).

### 5. Secured-unsecured basis from capital costs
`L = [R + p(1-c) + q·d·(g - b)] / (1 - p(1-c))`, with R secured rate, p default probability, c recovery, q risk weight, d capital ratio, g cost of core capital, b marginal cost of funds (Huggins and Schaller, SOFR Futures and Options, 2022). With p = 0, q = 20%, d = 8%: L - R = 1.6% x (g - b), so a 5% rise in g - b widens the basis by 8bp and doubling d doubles it. Interpretation: the capital basis rises with the rate level, cost of equity and capital ratios and is flat across maturity unless g, q or d are expected to change. Function `capital_basis_bp`. SOFR <= EFFR holds only while the bank can execute the arbitrage; the cap is set by the arbitrage cost (raising equity), so spikes are larger in SOFR than EFFR.

### 6. LCR, NSFR and leverage-exposure shortcuts
- LCR: HQLA / 30-day net outflow >= 100%. Funding under 30 days has a real outflow; a bank prefers a secured FHLB advance (25% outflow) to fed funds (40%); the "LCR booster" shows up as month-end funding demand. Investing cash in UST repo is LCR-neutral.
- NSFR: repo and unsecured funding under 6m are not stable funding; IRDs add RSF only (net liability with HQLA collateral +20% of the net liability; weakly collateralised net asset +100%). A trade that pushes NSFR below 100% carries a shadow cost.
- Derivative leverage exposure = alpha x (RC + PFE) with alpha 1.4 (SA-CCR). Function `saccr_ir_ead` reproduces the Darbyshire simplification; factors and caveats in [regulatory-ratios-and-factors](references/regulatory-ratios-and-factors.md).
- Netting: repo/reverse nets only with the same counterparty, settlement date and collateral under a master netting agreement; novating to a CCP can net and lower SLR exposure, but the G-SIB short-term-wholesale-funding input counts gross. Sponsored repo nets legs through the CCP: zero added to the sponsor's balance sheet versus +$100 the traditional way (BofA, US Treasury repo primer, 2025).

### 7. Reporting-window calendar
Banks expand leverage between reporting windows and shrink at them, removing liquidity for rolls (Quantitative Finance Stack Exchange, Apr 2019).
- US: G-SIB score is a year-end snapshot (applies to the surcharge two years later); SLR is a daily average, off-balance-sheet at the average of month-ends. Expect Q4 shrinkage and persistent quarter-end pressure.
- Euro area: leverage ratio reported at quarter-end and as daily average, so quarter-end window dressing persists; German GC richens into every quarter-end (Dec -188bp average change, 2014-2022 sample) and reverses next month.
- UK: PRA bans short-term window dressing. Japan: banks far above requirement; JPY quarter-end widening comes from the USD side; fiscal year-end 1 April.
- Instruments by sensitivity: short-dated xccy basis and FX swaps > repo (averaged in STWF) > longer spreads. Price a trade spanning a snapshot with a turn premium; strip the turn before inferring policy expectations. Detail and numbers: [windows-regimes-and-episodes](references/windows-regimes-and-episodes.md). Seasonal screens belong to [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md).

### 8. Balance-sheet capacity gauges (live read)
GCF minus tri-party repo up = inflexible dealer balance sheets; cleared bilateral minus tri-party; SOFR 75th-25th percentile spread; off-the-run richness residual (10y off-the-run on the first 3 PCs of the on-the-run curve); SOFR minus RRP; wide on/off-the-run spreads. Table with sources in the windows reference. Use at least two gauges and confirm each is consistent before calling a regime "tight".

## Worked examples

### A. $10mm 10y swap-spread widener (FRBNY, fall-2015 inputs)
Inputs: IM 3.9% funded at 0.5%; receive 3M Libor 0.6%; Treasury repo 0.3% on $9.72mm; haircut 2.8% funded at 0.5%; spread -10bp.

| Leg | Item | $ |
|---|---|---|
| Swap | fund IM $390,000 at 0.5% | -1,950 |
| Swap | receive 0.6% on $10mm | +60,000 |
| Treasury | repo 0.3% on $9.72mm | -29,160 |
| Treasury | fund haircut $280,000 at 0.5% | -1,400 |
| | net before spread | 27,490 |
| | -10bp spread x $10mm | +10,000 |
| | total net carry | 37,490 |

Equity at an SLR of 1/2/3/4/5/6%: $107,300 / 214,600 / 321,900 / 429,200 / 536,500 / 643,800 (Treasury notional + haircut + IM + PFE), so ROE on $37,490 = 35 / 17 / 12 / 9 / 7 / 6%.
At a big-bank SLR of 6-6.5% the ROE is at most about 6%, under half a ~15% dealer target (Boyarchenko, Gupta, Steele, Yen, Negative Swap Spreads, FRBNY Economic Policy Review, Oct 2018).
Breakeven 10y spread (bp) for target ROE 15% by SLR 1..6%: +11, -6, -22, -38, -54, -70; at 5% ROE: +21, +16, +11, +5, 0, -6. Headline: 15% ROE at 5% SLR needs -54bp; before the post-crisis rules, 15% ROE was achievable at up to +11bp. The bundled function reproduces the full Table 3 within about 1.5bp (the paper's PFE input for Table 3 is not fully stated) and the Table 2 equity charges exactly (all 36 Table 3 cells checked, max error 1.3bp). Flag: the paper's PFE of $600 at 1% SLR implies $60k of PFE, while a 1.5% add-on on $10mm would be $150k; the paper does not reconcile this, so rerun with your own PFE.

### B. Haircut funding cost of a 5y UST asset swap
2% haircut x (SOFR + 5% funding, i.e. 500bp excess) = 10bp. Adding it moved the 5y UST SOFR-ASW model from underfitting to a good fit (Jan 2021-Sep 2023 monthly data); run in reverse the implied marginal haircut cost was 8bp in Sep 2023, and the actual ASW was about 10bp above the model in early 2022, read as flow-driven mispricing (Huggins and Schaller, 2024).

### C. Basis leverage hurdle
LR 6%, ROCE target 10%, 90 days: 100 x 0.06 x 0.10 x 90/360 = 0.15 points = 15 cents per 100 face; at 3% LR 7.5 cents. A basis that pays 2-3 ticks per $1bn clears only 0.33-0.66% on capital: below the hurdle of a leverage-ratio-bound bank.

### D. Carry/vol hurdle table (USD, Sep 2026, hurdle 0.25; Barclays)
| Tenor | Spread bp | Carry bp | Vol bp | Carry/vol | Implied spread | Widening room |
|---|---|---|---|---|---|---|
| 5y | -27 | 7 | 10 | 0.76 | -8 | 20 |
| 7y | -34 | 6 | 12 | 0.52 | -15 | 19 |
| 10y | -38 | 5 | 13 | 0.40 | -23 | 15 |
| 20y | -63 | 5 | 19 | 0.26 | -62 | 1 |
The belly has the most widening room; the 20-30y is already at the hurdle (Barclays, Swap spreads: the Bright Spot in US rates, 30 Sep 2026).

### E. Constraint arithmetic that surprises
Barr's eSLR estimate: -27% Tier 1 required at G-SIB depository subsidiaries ($210bn) but only -1.4% ($13bn) at the holding company. Yet later evidence showed the large banks added about $300bn q/q of repo book (Conks, The Repo Rebound, 23 Jun 2026). Both facts can hold: relief works through the entity and the instrument that actually bound.

## Signals & interpretation
- Observed spread below breakeven by more than the uncertainty of your inputs (cost of equity +/-2%, IM +/-1%, SLR +/-1%): the trade compensates for balance sheet with margin to spare. Within the uncertainty: it is fair, not an arbitrage. Above breakeven: the carry does not pay for the capital, so the trade needs a view on further widening or capital-light financing (e.g. a non-bank with a zero-haircut line) to work. These bands are a heuristic default; calibrate on the history of your own breakeven series.
- Aggregate shadow cost is observable as the size and persistence of no-arbitrage violations (negative CDS-bond basis, SOFR > EFFR, negative swap spread). Rising violation size = scarcer arbitrage capital. Do not read a persistent violation as free money (Huggins and Schaller, 2022, 2024).
- Regulatory change reprices spreads in this order: front-end and basis (intermediation) first, longer spreads later and by less; 30y most exposed to an SLR exemption on UST because more capital is held against longer swaps (Clarus, Swapalypse Now, 14 Apr 2025; J.P. Morgan, What about Bonds?, 2 Apr 2020). Long-end spreads are also driven by structural end-user supply and demand: 30y spreads went negative in late 2008, before the leverage rules (J.P. Morgan, Pension re-risking and long-end swap spreads, 3 Apr 2020).
- "Regulatory rug pull": markets price deregulation early. Long wideners bought on an SLR-relief headline are exposed to failure to deliver and a re-tightening (the 2025 hype trade unwound); consensus tighteners are exposed to a surprise SLR or RWA relief. Check the CFTC-style positioning and the stage of the rule (proposal, comment period of at least 3 months, final) before trading the headline; interim final rules can be fast.
- Constraint check beats rhetoric: before using "SLR relief is bullish for UST demand", run Method 1.2 for the actual banks. If risk-based capital binds, use the carry/vol hurdle instead of the SLR ROE hurdle.
- Reporting-date trades: a pre-snapshot widening in repo/basis/xccy is a carry-for-liquidity trade, not mean reversion: size it to the turn premium seen in the same window of prior years and close after the snapshot. Closing early is rational when G-SIB year-end data show fragile GC (Citi, US Rates Weekly, 18 Jan 2019: TU/OIS widener opened -20, closed -16.2, +$210k).

## Pitfalls
- Using the wrong sign convention: US spread = swap - govt (negative = swaps below govts); EGB ASW = bond - swap. Flip before applying the formulas; the script negates rows stored `govt_minus_swap`.
- Using equity cost for haircut funding when the marginal funder has reserves, or the opposite. State which; show the range.
- Mixing regimes: a 10y USD swap history spans LIBOR, pre-standing-repo-facility SOFR and post-facility SOFR. Where swaps have structural breaks use fitted constant-maturity par government yields as inputs; and do not fit regression residuals across 2015 (Basel III), 2020 (SLR exclusion) without split-sample tests (TBAC, Feb 2021; Huggins and Schaller, 2024).
- Event windows are contaminated: regulation arrives as long overlapping processes; use sample splits rather than single event dates (Mixon and Onur, CFTC, Apr 2020).
- Sources conflict on whether SLR relief increases intermediation; test both on your data rather than citing one (Conks, The Fed's Relief Valve I, 2025; The Repo Rebound, 2026).
- Funding-leg risks dominate basis and spread trades: repo spikes (99th percentile repo-SOFR typically 10-11bp, 20-50bp in March 2020, 174bp peak), haircut and margin changes at short notice, prime-broker line cuts. Term repo removes rate risk, not availability risk. Size to the stressed haircut, not to price vol (MF Global: IE/PT haircut 3% -> 80%, details in the haircut reference).
- VM calls on a hedged position can force asset sales in stress; margin is procyclical (raising IM converts counterparty risk to liquidity risk). Clearing nets only within a product class (no IRS + repo + CDS cross-netting).
- The standing repo facility is not a firm ceiling for repo spikes: stigma, afternoon timing, no netting (two counterparties) and haircuts mean dealers need up to about 25bp over the top of the range (Barclays, US short interest rate primer, Jan 2025).
- PCA/regression trade success rates ignore bid-ask and capital charges (Huggins and Schaller, 2024).
- Swapped Treasuries in bank portfolios add swap-spread MTM risk even under hedge accounting (BofA, Rates basics: fixed versus float, 24 Apr 2024).
- Non-bank constraints differ: '40 Act funds count repo as leverage but not futures; life insurers' repo is on balance sheet with higher RBC charge than futures; so the futures-cash basis has a structural, non-economic component (CFTC MRAC, Dec 2024).
- Do not extrapolate US rules to CHF, NZD, NOK: sources contain no market-specific evidence; ask for local leverage-ratio and reporting-date rules. Structure differs even where sources are silent (external, verify current text): the UK leverage ratio excludes central-bank reserves, and the EU G-SII leverage buffer is a share of the risk-based surcharge, so "reserves and USTs are SLR-costly" is a US-specific premise.
- Rule parameters (SLR %, eSLR, SA-CCR factors, NSFR/LCR factors) are as published at the source dates. Check currency before presenting a hurdle as current.

## Output
Return a short table per trade or tenor with: `instrument/tenor | observed spread (bp, convention stated) | who is marginal | binding constraint | haircut cost (bp) | carry (bp) | equity per unit notional | ROE | breakeven spread (bp) | cushion (bp) | calendar flag (snapshot date within horizon?)`, followed by:
1. one paragraph on which constraint binds and why (with the gauge reading used);
2. a sensitivity grid (target ROE x SLR, or excess funding cost x haircut);
3. the explicit input assumptions (haircut, IM, PFE, funding rate, cost of equity) flagged as market-observed or assumed;
4. the regulatory catalyst and stage, if relevant, and the "rug-pull" risk.
Hand the result to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) for the carry/hurdle paragraph and to [rv-devils-advocate](../rv-devils-advocate/SKILL.md) for the crowding/regulation check.

## Scripts
- [`scripts/balance_sheet_hurdles.py`](scripts/balance_sheet_hurdles.py): `haircut_cost_bp`, `widener_economics` (carry, equity, ROE, breakeven, cushion), `basis_lr_hurdle`, `capital_basis_bp`, `saccr_ir_ead`; CLI `widener` reads canonical `swap_spreads` (and optional `repo_rates`) and writes a per-date, per-tenor ROE table. `python scripts/balance_sheet_hurdles.py --help`. The CLI applies one `--pfe`, `--haircut` and `--im` to every tenor: run it per tenor bucket (PFE 0.5% for 1-5y, 1.5% beyond 5y) and avoid reading across tenors with the default 1.5%. `--selftest` checks the FRBNY Tables 1-3, the TBAC -60bp breakeven, the 10bp haircut rule, the 7.5/15 cent basis hurdle, the capital-basis formula (analytic cases) and SA-CCR netting.

## Related skills
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): the spread instruments themselves; this skill supplies the cost and hurdle side
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo mechanics, GC vs special, quarter/year-end behaviour
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): basis and implied repo; this skill gives the leverage-ratio hurdle
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): reserves, RRP, standing facilities, QT drivers of front-end spreads
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CSA, initial margin, FVA/MVA, collateral optionality
- [xccy-basis](../xccy-basis/SKILL.md): year-end and G-SIB effects on FX-swap and xccy basis
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): BTP-Bund, gilt vs UST and haircut-driven spread differences
- [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md): ASW vs CDS and the capital-scarcity bound
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CCP margin and cross-margin effects on swap pricing
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): structural end-user demand that competes with balance-sheet effects in the long end
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): quarter/year-end turn screens
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): repo and money-market day counts, per-market conventions
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): repo-financed carry that this skill's haircut and capital costs adjust
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): adversarial check of regulatory and crowding risks

## References
- Huggins and Schaller - Fixed Income Relative Value Analysis: A Practitioner's Guide to the Theory, Tools, and Trades (2nd ed., Wiley, 2024): haircut cost, Fed/BoE/ECB schedules, shadow cost, Basel/SLR/NSFR/LCR, haircut-adjusted ASW
- Huggins and Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley Finance, 2022): capital-basis formula, SOFR <= EFFR under balance-sheet constraints
- Boyarchenko, Gupta, Steele, Yen - Negative Swap Spreads (Federal Reserve Bank of New York Economic Policy Review 24(2), Oct 2018): widener carry, equity charge, ROE and breakeven tables
- Barclays FICC Research (Joseph Abate) - US short interest rate primer (Jan 2025): G-SIB score, leverage exposure, LCR/NSFR factors, endgame, netting, standing-repo balance-sheet cost
- Barclays (Mok, Nashikkar) - Interest Rate Derivatives: Swap spreads: the Bright Spot in US rates (30 Sep 2026): carry/vol hurdle table
- Treasury Borrowing Advisory Committee - Charge: Swap Spreads (Feb 2021): 5% leverage ratio, 12% RoE, -60bp breakeven; regime residuals
- BofA Securities (Axel) - US Rates Watch: Taking a look at SOFR spreads (6 Oct 2020): balance-sheet, repo-buffer, illiquidity decomposition
- BofA Global Research (Cabana, Craig) - US Treasury repo primer: 2025 edition (7 Jul 2025): repo-with-haircut maths, netting conditions, sponsored repo, dealer repo statistics
- BofA Global Research (Axel, Cabana) - Fed's SLR proposal: underwhelming (25 Jun 2025): RWA from repo binds; Barr impact estimate
- BofA Global Research - Global Rates Viewpoint: FX-Sofr primer (31 Oct 2023): reporting windows by jurisdiction
- Tuckman and Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): repo haircut and margin mechanics, MF Global, LCR/NSFR/SLR effects, VM/IM, STM, CCP netting
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch and Dee, 2022): SA-CCR steps, LCR/NSFR examples, regulatory minimums
- CFTC Market Risk Advisory Committee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): basis profitability condition, structural futures preference, zero-haircut repo
- Quantitative Finance Stack Exchange - "Funding Treasury net basis trades and balance sheet" (Apr 2019) and "Is my thinking on futures implied repo correct?" (Nov 2019): leverage-ratio hurdle for basis, RoCE arithmetic
- Federal Reserve Board FEDS Notes - What Happens on Quarter-Ends in the Repo Market (Jun 2025): quarter-end event study, falling elasticity
- Yadav and Younger - Central Clearing the U.S. Treasury Market (University of Chicago Law Review 92, 2025): netting caveats, G-SIB short-term wholesale funding counts gross
- Fleckenstein and Longstaff - Treasury Richness (Journal of Finance, accepted manuscript 2023): SLR exclusion natural experiment
- J.P. Morgan - What about Bonds? SLR relief, Treasury supply, and long-end spreads (2 Apr 2020); Funding market interventions Part II (20 Mar 2020); There is one market where USD funding stress could reemerge (20 Feb 2020): SLR relief channels, binding-constraint screen, G-SIB statement-date mechanics
- Conks (Monetary Mechanics) - The Fed's Relief Valve Part I (7 Mar 2025) and The Repo Rebound (23 Jun 2026): binding constraint by bank, rug-pull risk, post-eSLR repo expansion
- Citi Research - FX Basis Quarterly: Paying the basis (again) into 2025 (13 Dec 2024) and STIRT Weekly (14 Aug 2026): SOFR bimodality, G-SIB reform proposals, FX-OIS trade
- Clarus Financial Technology - Swap Spreads For Dummies (Nov 2015) and Swapalypse Now (Apr 2025): missing carry items, SLR exemption hits the 30y most
- BofA Securities - Bond market seasonality explained (6 Jun 2022): German GC quarter-end and year-end seasonality
- Federal Reserve Bank of New York - Perli, Facing Quarter-End Pressures (12 Nov 2024): standing repo facility is not balance-sheet neutral
- Also cited inline or in the reference files: Mixon and Onur - Risk Appetite and Intermediation by Swap Dealers (CFTC OCE Staff Paper 2020-004, Apr 2020); J.P. Morgan - Pension re-risking and long-end swap spreads (3 Apr 2020), What does the SRF mean for swap spreads? (12 Jul 2019), Dynamic hedgers are long, banks are short (13 Sep 2019), Drivers of cross currency basis (11 Mar 2015); BofA - Rates basics: fixed versus float (24 Apr 2024); Citi - US Rates Weekly (18 Jan 2019); Conks (Monetary Mechanics) - Money Market Updates (Nov 2024 to Aug 2025) and The Fed's Reckoning Part I (9 Sep 2025); Duering - Fixed Income Trading and Risk Management (Wiley, 2021)
- BIS Quarterly Review - Goodbye Libor, hello basis traders (Dec 2025): basis from dealer balance-sheet costs
- SUERF Policy Brief 940 - Back to the basi(c)s: what is the CCP basis (Jul 2024): CCP basis drivers including balance sheet and cross-margining
