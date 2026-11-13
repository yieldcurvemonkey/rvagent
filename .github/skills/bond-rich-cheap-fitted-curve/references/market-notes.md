# G10 market notes for fitted-curve rich/cheap (reference)

Linked from [SKILL.md](../SKILL.md). Convention details (day counts, ex-div, settlement) live in
[fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md). Items marked **[src]** come from a cited document; items marked
**[default]** are practitioner defaults of this skill with no direct source and should be checked against the user's own data.

## Summary table

| Ccy | What drives issue-level rich/cheap | Basket / fit choices | Source status |
|---|---|---|---|
| USD | Benchmark (OTR) premium (small post-2008, still real at 10y and in the auction cycle), repo specials, CTD status, free float (central-bank holdings, strips), coupon/age, maturity-threshold effects (2/5/7/10y, 13M money-fund cliff) | Exclude OTR/olds/double-olds in 2-10y(+20y), specials (6m repo ≥ 25bp below GC), < 1y, FRN/TIPS/strips, very low free-float original-issue 30y; spline with ~12 knots; weight by yield error (and DV01 × free float) | **[src]** J.P. Morgan 2016/2018/2024, Fleckenstein & Longstaff 2023, RiskVal 2021 |
| EUR (DE, FR, IT, ES, NL, BE, AT) | Futures lead price discovery, so CTDs cheapen first under selling and the benchmark premium is "more or less absent"; deliverability 2-4bp (DE); issue size and age; coupon effects (old tax-driven German coupon effect); benchmark discount/roll vs surrounds; auction concession | Fit per issuer (DE with original issues only; IT with separate low/high-coupon tabs); weight issue size × DV01; deliverability regressor in the joint fit; spread to peer (DBR vs NETHER, FRTR vs SPGB) | **[src]** Düring 2021, Huggins & Schaller 2024, RiskVal 2021, J.P. Morgan GFIMW 2026, Citi 2026 |
| GBP | Low-coupon tax effect (income taxed, gains not): low coupons rich, scarcity of 1/8% lines; 7-day ex-dividend; DMO reopenings leave the "5y" with ~4.5y; linkers priced in real space with 3m lag | Post-tax yield curve for a 40% taxpayer; fit with coupon regressor or a coupon-bucket spline; spreads of z-spreads to OIS | **[src]** BofA UK Rates 2022/2024 |
| JPY | Futures structurally rich (index funds buy futures, dealers short futures vs long inventory) so the 7y/10y CTD is the most expensive spline point; official-sector JGB buying cut liquidity at times; JGBs with decimal coupons; JGBi seasonality | NS fit with BoJ-share adjustment to free float; composite splines for agency/municipal credits over the JGB NSS; macro fair-value regression for the 10y level | **[src]** Düring 2021, J.P. Morgan Japan FI Weekly 2025 |
| CAD, AUD, NZD, CHF, SEK, NOK | No dedicated source in the library. Few lines, wide maturity gaps, benchmark concentration, futures (AUD, and 10y GoC) and state/provincial/agency curves priced over the sovereign | Few bonds per date (often 10-30) so use NS/NSS, not 12-knot splines; require ≥ 8-10 bonds per fit; weight by issue size × DV01 where float data exist; treat the benchmark lines and futures deliverables as separate regressors; widen thresholds (z-score of residual matters more than level) | **[default]** |

## USD detail

- Auction cycle: 2/3/5/7y monthly; 10/20/30y new issue quarterly, reopened monthly. Ranks run on-the-run, old, double-old, triple-old.
  At the book's 2021 snapshot no Treasuries matured between May 2031 and Feb 2036 because the 30y was suspended 2001-2006 (Tuckman & Serrat 2022, Ch.0); 10y issuance has since filled that gap. About
  four-fifths of cash volume trades in on-the-runs; buybacks absorb off-the-run selling (Conks, Fed's Relief Valve I, 7 Mar 2025).
  About 400 nominal CUSIPs against 54 TIPS (48 after the 1y filter) (J.P. Morgan 2024).
- Two seasonality clocks: auction-cycle day (days since the tenor's last roll) is the mechanism clock, calendar month/day of week the
  other. Front tenors roll monthly so the clocks coincide; 10/20/30y roll quarterly so they separate. A flat auction-cycle profile
  means the effect is not the auction effect; run a placebo off the auction clock. Hold olds-vs-currents switches at constant DV01
  (rebalance daily; entry-fixed notionals drift about 0.5% per quarter) and pin to specific bonds, not generic "old 10y" series, which splice at every auction.
- Generic OTR series jump on auction dates. Roll adjustment: record WI roll = WI yield − benchmark yield at the auction-day cut-off and
  apply it to the benchmark pre-auction with linear decay `RollAdj_i = (WIroll/days)·(day_i − beginDay)`; no-decay adds artificial
  drift (RiskVal, Generic Time Series Data & Roll Adjustment, 28 Jul 2020: 10y unadjusted 0.679460 vs adjusted 0.690710, ~1.1bp).
- Cash-bond yield levels from a fitted curve are not tradable benchmarks: CMT yields cannot be traded, and the 10y future's CTD is
  roughly an 8y maturity / 7y duration bond (QF Stack Exchange, Jan 2022).
- Long end: 20Y bonds are structurally cheap (convenience premium −38.5bp in the 10-20y bucket; Fleckenstein & Longstaff 2023); ultra-long
  "rich vs model" is usually convexity (Düring 2021, Ch.19-20), so combine with [vol-convexity-and-long-end](../../vol-convexity-and-long-end/SKILL.md).

## EUR detail

- Bundesbank-style NSS/NS fits are the public reference for DE; the old REX index used NS plus a quadratic in coupon per bond to capture
  the German tax-driven coupon effect, so high-coupon Bunds yield more (Düring 2021, Ch.19).
- Benchmark switch OBL177 to OBL178 on 25 Jul 2018 produced a fake 2s5s steepening and 5s10s flattening in benchmark series
  (Düring 2021, Ch.31): use fitted constant-maturity yields for histories.
- EGB turnover is roughly constant over a bond's life (UST activity falls with age); fewer, larger lines improve liquidity.
- Most euro SSAs trade vs the French curve, not the German one (Düring 2021, Ch.32). EGB bonds are usually quoted vs Bunds
  (10y BTP 0.60% 8/1/31 minus Bund 0.00% 2/15/31 = 119.8bp, May 2021; Tuckman & Serrat 2022, Ch.3).
- A EUR-based investor must do global RV by asset- and basis-swapping every bond into EUR fixed flows and fitting one curve; spreads
  to EURIBOR/ESTR embed unobservable cost of capital (Huggins & Schaller 2024, Ch.17).
- Euro linkers: the DBRi/OBLi seasonality swing is much larger than HICP seasonality justifies; July French issues most advantaged,
  German most disadvantaged (Düring 2021, Ch.23; BofA 2025).

## GBP detail

- Gilts pay semiannual with 7 business-day ex-dividend; accrued is negative inside the ex-div window. Gilt accrued for identical terms
  1.43646409 vs Canadian ACT/365F 1.42465753: parametrise conventions per issuer (Darbyshire c.2024, s10.11-10.15).
- Screen columns: yield, post-tax yield at 40%, z-spread, private holdings as % of outstanding. A 1/8% coupon costs a 40% taxpayer
  ~5bp a year in income tax; sub-6y z-spreads on 5 Sep 2024 ranged from about −60bp (0.25% 2025) to +20bp (4.125% 2029), with 0.5% 2029
  at +6.0 and yield 3.70 vs post-tax 3.48 (BofA UK Rates Viewpoint, 5 Sep 2024).

## JPY detail

- Futures are structurally rich vs cash; measure the CTD spline spread against bonds 1y shorter and longer (the 1y offset removes
  seasonality in the coupon schedule). Pre-QQE the 7y CTD was the most expensive spline point and the least attractive on carry-roll.
- 10y fair value model: regress on 3Mx3M OIS, the 10y UST yield and the BoJ share of the three newest 10y JGBs (R² 92.3%, SE 7.0bp,
  2y rolling). A +10bp residual was not faded (see evidence file).

## Smaller markets [default]

- Sample size: below ~8 bonds the NS fit is nearly exact, so residuals are meaningless. Report `n_bonds`; if < 8 switch to spreads
  against two liquid neighbours (a fly) instead of a curve residual.
- Concentration: a benchmark line that is 60% of outstanding behaves like an OTR; test the benchmark flag as a regressor.
- Credit-adjacent curves (provinces, states, agencies, SSAs): fit the sovereign first, then a composite spread spline
  (see models file, section 2) and judge them by Z-spread to the sovereign curve; swaps are the usual hedge for covered and
  high-grade credit, so use ASW for those (Düring 2021, Ch.32).
- Cross-market comparison of fitted residuals needs a common hedge basis: see
  [spread-cross-market-govies](../../spread-cross-market-govies/SKILL.md).
