# Regulatory ratios, factors and exposure rules (lookup)

Companion to [SKILL.md](../SKILL.md). Rules change; every number is "as published in the cited source at its date".
Verify against the current rulebook of the jurisdiction before using a threshold in a sized trade.

## 1. Minimums and definitions

| Test | Definition | Minimum | Notes |
|---|---|---|---|
| CET1 | common equity / RWA | 4.5% | plus buffers and G-SIB surcharge (Basel III) |
| Tier 1 | CET1 + AT1 (CoCos, perpetual preferred) / RWA | 6% | |
| Total capital | T1 + T2 / RWA | 8% | |
| Tier 1 leverage ratio | Tier 1 / total assets | 3% | US G-SIBs at writing: 6.71% (Huggins & Schaller, FIRV, 2024) |
| SLR | Tier 1 / total leverage exposure (on-balance-sheet + derivatives + SFT/repo + off-balance-sheet) | 3%; G-SIB eSLR adds 2% at the holding company (5%) and 3% at the insured depository (6%) | US G-SIBs at writing: 5.64% |
| LCR | HQLA / 30-day net cash outflow | 100%, daily for large banks | |
| NSFR | available stable funding / required stable funding (1y) | 100% | |

- Capital held = max(risk-based requirement, leverage requirement), not the sum. A bank is "SLR-bound" or "RWA-bound".
  Example: RWA needs 100, SLR needs 60, hold 100; cutting the SLR requirement to 50 changes nothing (Conks, Money Market Update, 15 Mar 2025).
- G-SIBs need an SLR above 5% to avoid distribution and bonus limits, and bank subsidiaries need 6% to be "well capitalised" (Barclays FICC Research, US short interest rate primer, Jan 2025).
- eSLR reform (2025 proposal, Fed vote 5-2, 60-day comment): buffer moves from a fixed 2% to 50% of the method-1 G-SIB surcharge;
  IDI subsidiaries get 50% of the holding-company surcharge capped at 1%; surcharge buckets run 1.0% (Bucket 0) to 4.5% (Bucket 4).
  Barr's estimate: about -27% Tier 1 required at G-SIB depository subsidiaries ($210bn) but only -1.4% ($13bn) at the holding company (BofA, Fed's SLR proposal: underwhelming, 25 Jun 2025).

## 2. Leverage exposure measure (US)

- On-balance-sheet, derivative and repo exposure use daily averages in the quarter; off-balance-sheet uses the average of the three month-ends (Barclays, Jan 2025).
- Derivatives = replacement cost + PFE (SA-CCR) less collateral adjustments. Repo = gross repo receivables - eligible netting + counterparty credit-risk add-on. CCP trades are included.
- Repo/reverse netting for the leverage ratio ("Fin 41" style): same counterparty, same explicit settlement date, a master netting agreement, and settlement and bank conditions. Trades done with, or novated to, a CCP are nettable. Under GAAP/IFRS netting needs the same counterparty, collateral type and maturity.
- Consequence: matched-book repo and a long UST carry the same leverage capital as an unsecured loan, so the SLR penalises low-margin intermediation. Funding $25 of UST in repo grows the balance sheet 100 -> 125 (BofA, US Treasury repo primer, 7 Jul 2025).
- The leverage ratio is more binding for short-dated, large-notional, thin-margin activity (repo, cash-futures basis); RWA and market-risk capital bind on long-dated derivatives (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022).
- 2020 SLR exclusion of USTs and reserves: 1 Apr 2020 to 31 Mar 2021 for holding companies (depositories from 15 May 2020). Expiry coincided with deposits moving to MMFs and the RRP (Conks, The Fed's Reckoning I, 9 Sep 2025; BofA, Fed tools and balance sheet update, 2 Oct 2020).
- A leverage ratio excludes off-balance-sheet lease and backstop obligations (Citi, High-Grade Beat, 19 Aug 2026).

## 3. SA-CCR leverage exposure for interest-rate derivatives (Darbyshire simplification)

EAD = alpha x (RC + PFE), alpha = 1.4. RC = 0 for IRDs collateralised with cash or 100% HQLA; RC = max(MtM, 0) if uncollateralised or weakly collateralised.

1. Hedging set per netting set and currency (cross-currency swaps in distinct sets).
2. Start S and end E in years, S >= 0.
3. Adjusted notional AN = N x (exp(-0.05 S) - exp(-0.05 E)) / 0.05.
4. Margin factor MF (book's values): 0.175 cleared; 0.25 margined bilateral; 0.35 margined bilateral with > 5000 trades in the set; sqrt(E) unmargined with E < 1y; 1.0 unmargined E >= 1y.
5. Maturity buckets E < 1y, 1-5y, > 5y: E_k = sum of direction x AN x MF (pay fixed +1, receive -1).
6. PFE_set = 0.5% x sqrt(E1^2 + E2^2 + E3^2 + 1.4 E1 E2 + 1.4 E2 E3 + 0.6 E1 E3).
7. Sum PFE over hedging sets.

Cross-check (external): Basel's final SA-CCR uses MF = 1.5 x sqrt(MPOR / 1y) for margined sets (about 0.21 for a 5-day cleared MPOR, 0.30 for 10-day bilateral),
so the book's 0.175 / 0.25 are simplifications. Use the script (`saccr_ir_ead`) for orders of magnitude, not for a regulatory number; if a desk gives
its own add-on per unit notional, use that.

Simple Basel current-exposure-style add-ons used in the FRBNY widener model (Boyarchenko et al., Negative Swap Spreads, FRBNY Economic Policy Review, Oct 2018):
interest rate <= 1y 0.0%, 1-5y 0.5%, > 5y 1.5%; FX/gold 1.0/5.0/7.5%; equity 6/8/10%; precious metals 7/7/8%; other commodities 10/12/15%.

## 4. NSFR factors (as listed in Barclays, Jan 2025)

- ASF: 100% capital and liabilities > 1y; 95% insured retail; 90% other retail; 50% wholesale < 1y, 6m-1y funding and operational deposits; 0% funding < 6m from financials and central banks.
- RSF: 0% reserves, Level 1 HQLA, reverses on L1 < 6m, trade-date receivables; 15% L2A and reverses on non-L1 < 6m; 50% L2B and 6m-1y lending; 65%/85% mortgages and other lending by risk weight; 100% lending > 1y, NPLs, derivative assets.
- Repo and unsecured funding under 6m are not stable funding.
- IRDs never add ASF, only RSF: net liability with HQLA collateral -> RSF +20% of the net liability; net asset -> no impact. No or weak collateral: net liability RSF +20%, net asset RSF +100% of its value (Darbyshire, 2022, Table 17.7).
- Worked: uncollateralised corporate IRS asset $3mm -> RSF +$3mm; CCP IRS liability $1mm -> RSF +$0.2mm (Darbyshire, 2022, Ex 17.16).

## 5. LCR factors

- HQLA tiers: L1 (reserves, UST, GNMA) 100%; L2A (GSE debt, agency MBS) 85%; L2B (corporates, listed equities, GO munis) 50%. Caps: L2 <= 40% of HQLA, L2B <= 15%.
- Outflows: insured deposits 3%; other deposits 5-10%; operational deposits 25%; term deposits > 30d 0%; secured funding backed by L1 0%, L2A 15%, L2B 50%; overnight FHLB advance 25%; overnight fed funds borrowed from an FHLB 40%; all other secured funding 100% (Barclays, Jan 2025).
- Assets received under rehypothecation that the owner can withdraw within 30 days do not count as HQLA.
- Term-structure effect: rolling a $100mm 1M loan always has an outflow in the 30-day window (no HQLA credit); three overlapping $33.3mm 3M loans fund $99.9mm with only $33.3mm leaving in any window, so $66.6mm is usable as HQLA; six $16.7mm 6M loans give $83.5mm (Darbyshire, 2022, Ch.17.4.1).
- LCR arbitrage: each $100 borrowed as fed funds from an FHLB gives at worst a $60 LCR benefit (40% outflow); a secured FHLB advance (25%) is preferred; investing the cash in UST repo is LCR-neutral. The "LCR booster" is Category IV and smaller banks borrowing from FHLBs before month-end reporting (BofA, SOFR/FF term structure, 22 Oct 2020; Conks, The Fed's New Target I, 9 Jan 2026).
- Risk weights: reserves, USTs and GNMA 0% and Level 1; FNMA/FHLMC MBS and FHLB notes about 20%; interbank loans 20%. Swapping a UST does not change its LCR status (BofA, Rates basics: fixed versus float, 24 Apr 2024; Conks, Demise of the Fed Funds Market, 7 Aug 2023).

## 6. G-SIB surcharge mechanics (US)

- Score = weighted sum of size, interconnectedness, cross-jurisdictional activity, complexity and short-term wholesale funding (STWF). It sets the surcharge for the year starting two years later (Q4'24 score applies from Q1'27). Eight US G-SIBs.
- Repo in the score: size counts it net; interconnectedness includes CCP repo but not Fed repo and only the cash-collateral difference; STWF counts it gross including Fed transactions on a four-quarter trailing average (Barclays, Jan 2025).
- Method 2 runs 1-5.5% and is scored at year-end; STWF has no netting benefit, so novating repo to a CCP lowers SLR exposure but not the STWF score (Yadav and Younger, Central Clearing the U.S. Treasury Market, Univ. of Chicago Law Review, 2025).
- Excluding cash and UST from the size and complexity inputs would cut Method 2 scores by about 2-5%, mostly not enough to change a bucket (J.P. Morgan, What about Bonds?, 2 Apr 2020). Levers banks use: complexity and cross-jurisdictional sub-scores (J.P. Morgan, Dynamic hedgers, 13 Sep 2019).
- Bank equity rallies raise year-end surcharges (Conks, Money Market Update, 27 Nov 2024).
- Reform ideas (averages instead of year-end values; 10bp instead of 50bp increments) would cut window dressing; the counter-view is that daily averaging tightens funding through the quarter and leaves less FX-lending capacity (Citi STIRT Weekly, 14 Aug 2026; J.P. Morgan, There is one market..., 20 Feb 2020).

## 7. Endgame and market-risk rules

- Basel III endgame (US Jul 2023 proposal): banks above $100bn compute expanded risk-based and standardised approaches and the lower ratio binds; output floor = 0.725 x (credit + equity + operational + CVA RWA) + standardised market-risk RWA. Standardised market risk uses the sensitivities-based measure (delta, vega, curvature under three correlation scenarios), default risk and a residual add-on; term repo falls under it. SA-CCR raises RWA for one-directional unmargined uncleared derivatives. Sep 2024 re-proposal dropped minimum haircuts on uncleared SFTs with leveraged non-banks, exempted $100-250bn banks and lowered capital on the client leg of cleared derivatives (Barclays, Jan 2025). Estimated about 24% more capital buffers for the largest banks under the original (Conks, The Coming Volatility Suppression, 5 Sep 2023).
- FRTB: VaR -> Expected Shortfall and internal -> standardised models, so more capital; "a simple spread trade that appeared attractive previously may no longer appear attractive" (Huggins and Schaller, FIRV, 2024).
- Internal-model market-risk charge: ES(10d, 2.5%) in stress, scaled; capital to RWA x12.5 (Darbyshire, 2022, Ch.17.2.7).
- Operational-risk capital is about 15-20% of G-SIB Tier 1 (J.P. Morgan, When market risk meets operational risk, 10 Mar 2020).
- Compliance fix example: bank failing LCR and NSFR issues $50mm AT1 at 5% and $50mm term debt at 2.5% and buys sovereigns and central-bank deposits -> CET1 14.1%, T1 20.9%, LR 10.8%, LCR 138.6%, NSFR 100.3% (Darbyshire, 2022, Ex 17.17).
