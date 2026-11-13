# Specialised panels: layouts, definitions, dated numbers

Detail behind section 7 of [SKILL.md](../SKILL.md). All numbers are dated snapshots as printed by the cited source,
there as layout checks and worked data, not as current market levels. Sign conventions: the desk best-trade tables are
payer view (parentheses = negative); Darbyshire uses positive pv01 = paid fixed, the opposite of this agent's rule (positive
DV01 = long duration = receive fixed), so convert on input.

## 1. Cash-bond RV screen (US Treasuries; GS US Treasury Asset Swap Spreads, 25 Sep 2026)
Four panels:
1. **Universe scatter**: proceeds ASW vs maturity year (2027-2056), coloured by original tenor (2y 3y 5y 7y 10y 20y 30y),
   on-the-run flagged, principal STRIPS overlaid; a second version excludes STRIPS.
2. **Sector view**: one chart per maturity bucket (0-1.5y, 1.5-3.5y, 2.5-6y, 5-10y, 10-30y); bonds labelled coupon and
   maturity; the CTDs of the current and next futures flagged.
3. **Series history**: per original tenor, today's proceeds-ASW curve overlaid on the curve 1m ago.
4. **Detail tables**: on/off-the-run, principal-STRIP and coupon-STRIP tables.

Per-bond columns: description, coupon, maturity, price, yield, duration; matched-maturity swap spread (MMS) with 3m z;
proceeds ASW with 3m z; the same pair vs OIS; fitted-curve spread with 3m z; invoice spread (futures CTDs only); identifier.
Conditional format red if z < -2, green if z > 2.
Roll-sheet add-ons (RiskVal Overview 201, 12 Nov 2021): colour codes for on-the-run, front and back CTD, when-issued;
columns outstanding, central-bank holdings %, free float (true liquidity), daily change, z-scores. Standard RV block:
level, daily change, 3m range heat-bar, 3m z, expected return = (bp to 3m mean) + 3m carry & roll, MR frequency.
Use desk repo (GC or special) for carry; the default GC curve is a fallback.

Dated rows (as printed, 25 Sep 2026; MMS bp, z = 3m): 2y 4.75% Sep-28 MMS 14.5 (z 0.4), fitted -1.2 (z 0.6); 7y future CTD
4.5% Aug-33 MMS 33.8, fitted -0.8 (z -2.2, rich), invoice 35.6; 10y future CTD 4.375% May-36 MMS 39.5, fitted +2.0 (z 1.9);
20y future CTD 4.875% Aug-45 MMS 64.9, fitted +2.1 (z 2.9, cheap), invoice 68.3. Flagged |z| >= 2: Oct-Dec 2026 paper with
high ASW z (2y 4.25% Nov-26 MMS z 4.2); 1.25% May-50 fitted -4.0 (z -2.5). ASW sign convention and fitted-curve method are
undocumented in the report: re-derive before relying on levels.
Vendor worked case (RiskVal, 12 Nov 2021): buy 0.375% Nov-25 (2 sd cheap to the constant-maturity curve) vs sell 2.75% Aug-25
(0.2 sd rich), carry & roll 9.9 vs 9.8 bp; strategy-level curve-based RV 2.7 sd cheap, direct yield spread 1.8 sd cheap;
the curve-based number is theoretical, so trade and judge the direct yield spread.

## 2. Futures positioning panels in DV01 (GS UST Futures Positioning Report, 2 Oct 2026)
- Positions in $mm DV01 per contract family (2y, 5y, 10y, bond, Ultra-bond, STIR), with and without STIR.
  Classes: institutional (asset managers), dealer, leveraged, other. Read DV01, not contract counts.
- Changes over 1w and 1m, also in "5-year standard deviations"; context = 5y min/max and percentile; concentration on a
  1y window (% of open interest held by the 4 and 8 largest traders).
- CTD valuation panels in OIS-proceeds ASW bp (2y CTD minus CT2; 5y CTD-CT3-CT5 fly; 10y CTD-CT5-CT10 fly; bond/Ultra CTD-CT10-CT30
  fly), plotted against institutional net length and the net basis in 32nds.
- Dated numbers (2 Oct 2026): institutional +527 (63rd percentile over 5y), 10y-note family +176 = 5y max (99.6th), Ultra-bond
  +135 (22.6th) with 1w change -22 (-3 sd); leveraged -486 (39.8th), 1m change +52 (+2 sd); dealer -63; 10y 4 largest longs
  29.3% of open interest (98.1st pct, 1y); 8 largest 38.1%.
- Canonical input: `positioning.net_dv01_ccy`, positive = long duration. The source values for charts were not machine-readable
  in the reader's extraction; only tables were used.

## 3. Money-market stress and funding monitors (USD; Conks, Money Market Updates / Plumbing Notes, 2024-2026)
**Stress monitor**: one panel per gauge, each with a pass/fail scarcity warning line and an overall banner (LOW or MILD).
Panels: EFFR - IORB (warning at 0); SOFR - IORB (warning about 0); reserves vs the lowest comfortable level of reserves
(LCLoR; the author's and the Fed's estimates differ, and both change by issue: record which one a chart uses); standing repo
facility usage; central-bank swap-line usage.

| Spread | Meaning (as printed) |
|---|---|
| EFFR - IORB | reserve scarcity: a positive spread suggests scarce reserves on a historical basis; if EFFR > IORB the Fed likely adds reserves |
| SOFR - IORB | bank activity in repo: SOFR above IORB points to sizeable bank repo activity |
| GCF - tri-party repo rate | dealer balance-sheet capacity and funding demand |
| TGCR - ON RRP | private repo demand: up = excess collateral, down = excess cash |
| SOFR - EFFR | FHLB repo demand: up = FHLBs deploy more cash into repo |

**Benchmark monitor**: SOFR, BGCR, TGCR, OBFR, EFFR as volume-weighted medians with 1st/25th/75th/99th percentile bands
(upper percentiles minus median = dispersion). Composition: SOFR = tri-party + GCF + DVP; BGCR = GCF + tri-party; TGCR =
tri-party (later issues add sponsored GC); OBFR = Eurodollars + fed funds + domestic deposits; EFFR = fed funds.
**Fed funds monitor**: percentiles vs IORB and RRP; lenders (mostly FHLBs) and borrowers (mostly foreign banks) as separate bars.
**FHLB monitor**: liquidity in IBDAs, reverse repo, fed funds sold, plus total advances as a stress gauge.
**Hierarchy ladder**: "global jaws" (full range) and "local jaws" (target range); each rung labelled ceiling or floor with the
footnote "in theory (not always in practice)"; soft facilities (SRF, discount window) carry stigma, so repo can print above
the SRF minimum bid with no take-up. **Dollar complex**: onshore bank corridor (discount window to EFFR/OBFR) and shadow bank
corridor (swap lines to ON RRP). **Dislocation panel**: OFR tri-party rate vs TGCR, SOFR, ON RRP and the target range to expose
a segment that should co-move but does not (tri-party and TGCR diverged about 8 bp in Aug 2024). **Non-Fed repo complex**: DVP,
GCF, tri-party and estimated non-centrally-cleared bilateral repo; the latter usually highest, tri-party usually lowest.
**Level tiles** with week-on-week change: TGA (opening, deposits, withdrawals, closing), reserves, ON RRP, foreign repo pool,
FIMA custody, SOFR and fed funds volumes. **Reserve adequacy**: reserves / bank assets (abundant > 13%, ample 11-13%, scarce < 11%);
NY Fed RDE (increasingly negative = scarcity).
Rules: separate funding-demand gauges (GCF - TPR, TGCR - RRP, SOFR - IORB) from scarcity gauges (EFFR - IORB, RDE,
reserves/assets); flag and filter quarter-end and month-end spikes before z-scoring; in cut cycles compare spreads to IORB and RRP,
not levels; EFFR is thin and sluggish so repo moves first.
Dated checks (as printed): 10 Sep 2024 IORB 5.40, SOFR 5.35, EFFR 5.33, ON RRP 5.30, reserves USD 3,243.0bn, LCLoR 2,700bn (author) vs
2,200bn (Fed), banner LOW. 16 May 2025: SOFR 4.30, EFFR 4.33, IORB 4.40, ON RRP 4.25, reserves/assets about 13.5-14%, RDE about 0 to -0.1.
26 Oct 2025: banner MILD, SOFR - IORB status "REACHED", LCLoR 2,900bn vs 2,700bn. May 2026: EFFR 3.64, SOFR 3.64, IORB 3.65,
reserves about USD 2,919bn, LCLoR 2.8tn vs 2.7tn. Related: [stir-repo-and-funding-plumbing](../../stir-repo-and-funding-plumbing/SKILL.md),
[stir-central-bank-balance-sheet-and-reserves](../../stir-central-bank-balance-sheet-and-reserves/SKILL.md).

## 4. Trader risk dashboard (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, Ch. 14-16)
Three panels: Risk & P&L estimate; VaR & PCA; Simplified portfolio (VaR-based). Grouping by liquidity and market-driving
tendency: macro (2y, 10y); sub-macro (2s5s10s); micro (1s2s, 2s3s4s, 3s4s5s, 5s7s10s); sub-micro (5s6s7s, 7s8s9s, 8s9s10s). The summary
shows par, forward and model risk side by side; P&L is explained in the model only. Book convention: "2s5s" = -1 x 2y, +1 x 5y;
"2s5s10s" = -1/+2/-1; positive pv01 = paid fixed (convert).
Example 16.9 rows (risk, change in rate bp, P&L): 2y (41, +1.3, 54); 10y (6, +1.4, 8); 2s5s10s (30, +0.7, 21); 1s2s (11, +0.1, 1);
2s3s4s (-65, -0.1, 6); 3s4s5s (-165, -0.2, 33); 5s7s10s (64, +0.1, 6); 5s6s7s (-28, +0.5, -14); 7s8s9s (114, +0.6, 69);
8s9s10s (13, -0.7, -9); total P&L 175 (check: the rows sum to 175). The forward 4y1y bucket (40) is the largest independent risk.
Reading rules: only one single-instrument VaR-minimising trade is valid at a time (several at full size can raise VaR; trade
about 50% of each and re-run); a negative VaR allocation means the bucket diversifies the book, so do not cut it; if the best
single hedge cuts VaR by only about 15%, the book is dominated by RV or combination risk, not direction; single-instrument
trades are preferred because they execute more easily and traders can see which are independent.

## 5. Price-format futures spread display (Aikin, STIR Futures, 2nd ed., 2012)
Spread = (P_bf x T x Q_bf) - (P_s x T x Q_s): P_bf bond-future price, P_s simple average price of the strip legs, T tick value per
bp, Q = number of contracts of each leg (hedge ratio from the strip and bond-future BPV). A rise profits a long spread; price change x 100 gives the EUR P&L. The
yield-difference display is useful against the swap spread but "rather meaningless" between two differently quoted instruments.
The book is LIBOR-era; the method carries over to RFR futures but the mapping is not in the source. See
[fut-invoice-spreads](../../fut-invoice-spreads/SKILL.md).

## 6. Credit basis screen layout (JPM Credit Research, HG CDS Bond Basis Report, 22 Oct 2025; JPM EM Sovereign Bond-CDS Basis, 22 Oct 2025)
Low G10-rates relevance; kept as a layout template. Per bond: amount outstanding, 1-week average price, price, I-spread, par-equivalent
CDS spread (A), CDS-implied spread (B), basis = B - A (positive = CDS cheap; legend on the page), basis change over 1d/1w/1m/ytd,
basis % of spread (inferred as basis / I-spread, undefined in the source; needs a denominator floor). Summary hierarchy: market ->
sector -> tenor bucket (3y 5y 7y 10y) -> rating; ranked top/bottom N by basis level, weekly change and % of spread. Chart pair: market
basis vs a benchmark index over about 6m, and sector histories from a fixed start date. Snapshot check: 1,369 bonds, USD 1,724,694m,
basis -48 bp; by rating AAA -28, AA -32, A -48, BBB -51 (monotone in quality: a quick consistency test on any bucketed screen).
EM sovereign country pages: three charts (PECS vs CDS curve, basis vs maturity, basis/CDS ratio vs maturity), each with current vs
1m-ago overlay; per-bond z (6m) and 6m min/max columns.

## 7. Desk best-trade picks as a layout check (GS Global Rates Best Trade Report, 30 Sep 2026; global pool; payer view)
| Rank list | Top row | Numbers |
|---|---|---|
| 3-factor score | EUR 5y5y/10y5y/15y5y fly | 2.69 (carry 0.04, entry -0.95, trend 14.10, R -0.05) |
| 3-factor, next | JPY 1y1y/2y1y/3y1y fly | 2.60 (1.20, -0.71, 7.66, 0.26) |
| 3-factor, receive side | AUD 1y 2s5s10s | 2.33 (-1.09, 1.01, -2.74, 0.47) |
| Carry + entry | JPY 1y1y | 3.21 (carry -0.74, entry 2.89; level 2.256%; 3m payer carry -9.6 bp, i.e. receivers earn 9.6 bp, vol 25.8; 2 x 9.6 / 25.8 = 0.74) |
| Entry + trend | EUR 3y 5s10s20s | 2.38 (entry -0.62, trend 15.50) |
| Best entry (z) | JPY 1y1y-1y5y | 2.78-2.89 |
| Strongest trend | EUR 3y 5s10s20s | 15.50 |
Currency-pool #1 3-factor scores (the global pool differs): EUR 2.64 (global 1.99 for the same trade), GBP 2.13, USD 0.81 (three qualifying trades),
JPY 4.41, CHF 1.24, CAD 1.23, SEK 0.93, NOK 1.24, AUD 2.44, NZD 1.39. Realised 3m vol ranges: outrights 25-55 bp, curves 2-23 bp, flies 2-18 bp.
Use these only to sanity-check an implementation of the column definitions; do not quote them as current.
