---
name: spread-tenor-and-index-basis
description: 'Single-currency tenor and index basis swaps: SOFR vs Fed funds (SOFR-FF, FF-SOFR, secured vs unsecured overnight), IBOR tenor basis (3s6s, 6s3s, 1s3s, 6s12s, E/E Euribor vs estr, BBSW, BKBM, STIBOR, NIBOR), RFR vs term rate (Term SOFR, Term CORRA) and legacy FRA/OIS, LIBOR-OIS. Covers sign conventions (realised vs futures price spread, which leg carries the spread), fair spread and the two-curve identity, basis DV01 by instrument bump and Jacobian, 1M SOFR vs 30-day FF futures spreads and 10:6 weights, drivers (reserves, bills, TGA, FHLB, period-ends, bank credit), z-score and driver-residual screens, carry-checked structures. Use when asked about basis swap, SOFR/FF, FF-SOFR, 3s6s, tenor basis, index basis, FRA-OIS, ICBS, basis DV01, SOFR-FF futures basis, ''is the basis rich or cheap'', or hedging term vs overnight exposure. Owns SOFR-FF in swap and futures form; why SOFR sits above or below EFFR (repo drivers) is stir-repo-and-funding-plumbing.'
---

# Tenor and index basis (single-currency basis swaps)

A basis swap exchanges two floating rates in one currency. Because default-free rates of any term swap flat, the
spread is a price of something else: bank credit and liquidity over a longer term (tenor basis such as 3s6s,
Euribor vs estr, FRA/OIS), or the gap between secured and unsecured overnight funding (SOFR-FF). It pays when you
can name the driver (reserves vs collateral, bill supply, fixing methodology, discounting flows) and the carry
does not eat the edge. It also matters everywhere else: a swap or bond hedge in the wrong index leaves exactly this
basis as residual risk.

## Conventions (read first, state them in every output)

Sources disagree on sign more than on anything else. Restate every number into the canonical form below before
reusing it.

| Quantity | Definition used here | Notes |
|---|---|---|
| Canonical basis row | `basis_swaps.spread_bp` = spread added to `leg_a` against `leg_b` flat, bp | read `leg_a`/`leg_b` from the row; OTC convention puts the spread on the shorter-tenor or overnight leg; if a source quotes it on the other leg, swap legs and flip the sign |
| Realised overnight basis | secured minus unsecured, e.g. SOFR − EFFR, bp | positive = repo above unsecured = tighter funding |
| Futures price spread | (1M SOFR future price) − (30-day FF future price), same month | price = 100 − rate, so this equals FF − SOFR in rate terms: **opposite sign to the realised basis** |
| Desk "SOFR/FF" quotes (BofA, Citi) | FF − SOFR, i.e. the futures price spread | negative = SOFR above FF. "Short SOFR/FF" = bet SOFR rises vs FF |
| Tenor basis | longer-tenor index vs shorter, quoted as the shorter leg plus a positive spread | 3s6s = 3M index + x vs 6M index flat, x > 0 normally; EUR (and AUD) markets quote it as the difference of two par swap rates, longer-tenor-index swap minus shorter (S6M − S3M), normally positive and about `x` times an annuity ratio |
| Basis DV01 | PV change per +1bp in the market spread, for the party who **receives leg_a plus the contract spread** | negative: `dPV/ds = −N · annuity(leg_a) · 1e-4`. Receiving the spread loses when the spread widens |
| Units | bp for spreads, pct for rates; futures prices decimal | never mix settle and close snaps in one series (they differ by roughly 0.2–0.9bp) |

Worked sign check: SOFR 4.00%, FF 3.90%: realised basis +10bp; futures prices 96.00 and 96.10; price spread −10bp.
If FF falls to 3.85 with SOFR still 4.00, realised +15bp (+5bp wider), the price spread goes to −15bp ("sell-off" in
the futures basis) (Conks, The SOFR/FF Basis primer, 10 Jun 2026). A "long SOFR-FF basis" is a short futures
price spread. Always restate a recommendation in rate terms ("SOFR − EFFR from +4 to +8bp") before trading.

## When to use
- "Is the SOFR-FF (FF-SOFR) basis rich or cheap?", "what is priced for the Dec / quarter-end SOFR-FF futures basis?"
- "Is 3s6s (E/E, 6s3s, 1s3s) wide or tight?", "why does the 2y swap price off a different index than the futures strip?"
- Sizing or hedging a basis swap: basis DV01, instrument deltas, what hedges a 3M-vs-OIS exposure.
- Choosing the index for a hedge (corporate vs government, term-rate loan vs RFR swap) and what basis is left.
- Legacy-IBOR basis (FRA/OIS, LIBOR-OIS, FF vs LIBOR) in AUD, NZD, SEK, NOK and Euribor markets, or old history.
- Not here: cross-currency basis (see [xccy-basis](../xccy-basis/SKILL.md)); CME-LCH basis (see
  [spread-ccp-basis](../spread-ccp-basis/SKILL.md)); fixed-vs-bond swap spreads
  ([spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Quoted basis swaps by type, pair, start, tenor | `basis_swaps` | daily, one snap, ≥ 3y (5y for regime work) | `basis_type` = tenor or index; check `leg_a`/`leg_b` and `data_ok` |
| Index definitions, term, fallback spread, status | `rate_indices` | static | `family` RFR/IBOR/POLICY; `fallback_spread_bp`; `status` ceased/active |
| Fixed/float frequency, day count, lag, CCP | `swap_conventions` | static | tenor-dependent conventions (AUD 3y/4y switch) need one row per `from_tenor` |
| Par OIS and IBOR swap rates (spot and forward) | `curve_par` | daily, ≥ 3y | to derive fair basis or synthetic swaps |
| Discount factors for both legs | `curve_zero` | daily | RFR discount curve, plus tenor forward curves |
| Overnight fixings incl. percentiles and volumes | `rate_fixings` | daily, with `pub_ts_utc` | SOFR, EFFR, OBFR, TGCR; use `p25/p75` for SOFR bimodality |
| 1M SOFR and 30-day FF futures by month | `stir_quotes`, `fut_static` | daily settle | `price_px` = 100 − `rate_pct`; one snap only |
| Repo by segment (tri-party, DVP, GCF), GC vs special | `repo_rates` | daily | SOFR − TGCR, GC − RRP |
| Reserves, ON RRP, TGA, bills outstanding, bank assets | `macro_series` | weekly or daily | drivers for the USD model; point-in-time `pub_ts_utc` |
| Policy meeting dates, calendars | `cb_meetings`, `calendars` | static | FOMC-neutral weights, period-end filters |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values. See
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Method

### 1. Classify the basis (what is actually being priced)

| Type | Legs | Prices | Live today (G10) |
|---|---|---|---|
| Secured vs unsecured overnight | SOFR vs EFFR (OBFR); estr vs SOFR is xccy | cost of capital, reserves vs collateral, FHLB/foreign-bank arbitrage | USD only is liquid |
| Tenor basis | 3M vs 6M, 1M vs 3M, 6M vs 12M of one IBOR | credit/liquidity of rolling short loans vs a term loan (value of the option to switch counterparty), LCR effects | EUR (Euribor), AUD (BBSW), NZD (BKBM), SEK (STIBOR), NOK (NIBOR) |
| Term vs overnight | Euribor/BBSW/BKBM vs RFR OIS; legacy LIBOR vs OIS/FF | bank credit + term liquidity + expected policy path in the term | same markets; legacy USD/GBP/JPY/CHF LIBOR gone |
| Averaging vs compounding | 1M average futures vs 3M compounded futures | arithmetic vs geometric accrual, 0.1bp at low rates up to about 3bp at 5% | all RFR futures |
| Fixing methodology | index with changed panel or survey rules | sampling noise, not economics | Euribor hybrid, SOFR percentile trim |

Overnight/term LIBOR-type indices exist in USD/GBP/JPY/CHF only as history and fallback spreads
([G10 table](references/g10_basis_by_market.md)). CAD, CHF and GBP have no IBOR tenor basis to trade (Term CORRA vs OIS is thin; see the table).

### 2. Normalise every series

1. Put each series on `spread_bp` for a named `leg_a` vs `leg_b`. If you receive the opposite, `spread_bp *= −1`
   and swap legs. If the source adds the spread to the other leg (`leg_b + z_b`), the equivalent canonical value is
   `spread_bp = −z_b · A_b / A_a` (same PV; sign flips, magnitude scales by the annuity ratio). With near-equal annuities
   (flat curve, similar payment dates) the magnitudes coincide.
2. Futures: realised basis (bp) = (price_FF − price_SOFR) × 100, per contract month. Never compare a month with
   a different averaging window (1M average vs 30-day average are close but not identical on holiday-affected months).
3. Drop `data_ok = false` rows, period-end days when judging "normal" level (month-end, quarter-end, mid-month
   coupon/tax settlement), and rows from a different snap.

### 3. Fair value and drivers

**Tenor basis (credit view).** Default-free rates of different terms swap flat; the observed spread is the credit
and liquidity premium of a fixed 6M loan over rolling 3M loans, because a rolling lender gets a fresh credit check
every 3M. Hence 2×3M carries less credit than 1×6M and a rolling overnight lender less again, so
`1M < 3M < 6M < 12M` in expected-credit order and the quote 3s6s, 1s3s, 6s12s is positive in normal times
(Lehman, Money Market Basis Swaps, Jun 2003; Huggins & Schaller, Fixed Income Relative Value Analysis, 2024). The
spread widens with bank credit stress. Bill supply works through the same chain: bill paydowns richen bills, push money funds toward prime/unsecured paper and narrow
the FRA/OIS (net yield gaps of 5–7bp triggered reallocation; JPM, Bills, Bonds, and basis...oh my, 7 Feb 2020). A term rate also embeds the policy path over its own term, so a fixed
"10–15bp term credit" assumption used to back out what is priced in term-index futures is flawed (Lehman, The
Short-End of the Curve, 10 Jul 2007).

**Capital-cost anchor for unsecured vs secured overnight.** `spread ≈ g · q · d` with g = cost of equity,
q = interbank risk weight (min 20%), d = capital ratio (8%): q·d = 1.6%, g = 10% gives 16bp. g and the marginal
lender are unobservable, so use this qualitatively, except for rule changes (Huggins & Schaller, Fixed Income
Relative Value Analysis, 2024). A repo-LIBOR identity that also adds default and recovery:
`L = [R + p(1−c) + q·d·(g−b)] / [1 − p(1−c)]`; see [derivations](references/pricing_and_risk.md).

**USD SOFR-FF structure.** Short end (to about 2y, possibly 5y) the swap basis tracks the overnight spread
(10-day average of the overnight spread); the 10y/30y adds segmentation, LDI/insurer discounting-hedge flows and
the CCP discounting switch (BofA, SOFR/FF term structure post "big bang", 22 Oct 2020). Overnight regime rule: FF
above SOFR (realised basis negative) when reserves and ON RRP are abundant; SOFR above FF as collateral outruns
cash and reserves become scarce. SOFR is the mover: EFFR is a thin FHLB-to-foreign-bank arbitrage market that
prints flat (about 1bp under the administered rate) unless a large cash flow hits it. Fair value for the
overnight spread in abundance is FF 1–5bp above SOFR, most likely 1–3bp (realised −1 to −3bp; 2014–2020 average
about −1.5bp). Regime averages of FF − SOFR ran from −3.2bp to +9.9bp, i.e. realised +3.2 to −9.9bp (BofA,
22 Oct 2020). Details, regressions and event table:
[USD SOFR-FF drivers](references/usd_sofr_ff_drivers.md).

**Two-curve / multi-curve identity (EUR and other IBOR markets).** Let `d` be the RFR discount factors,
`c` the fixed rate of an annual-fixed vs 3M-IBOR swap and `x` the RFR+x vs 3M-IBOR basis:
`c · Σ acc_ann · d + d_T = 1 + x · Σ acc_q · d`. Either `c` or `x` can be solved from the other. With the published
24 Feb 2022 estr discount factors, c = 0.078% and x = 13.8bp both legs are worth 100.281 (Tuckman & Serrat, Fixed
Income Securities, 4th ed., 2022). You cannot have the RFR leg at par, RFR + x fair against the IBOR, and the IBOR
leg at par at once: value the fixed flows on the RFR curve and the IBOR leg as par plus the PV of the basis
stream. Only a forwarding curve built **on** an exogenous OIS discount curve is multi-curve consistent; a
self-discounted curve reprices its own inputs but misprices other instruments by up to a couple of bp (Ametrano &
Bianchetti, Multiple Interest Rate Curve Bootstrapping, SSRN 2013).

**Fair spread by PV = 0.** For the receiver of `leg_a + Z` paying `leg_b`:
`Z = [Σ d_b r_b v_b − Σ d_a r_a v_a] / Σ d_a v_a` (d = accrual, r = forward, v = discount factor). The printed
formula in one practitioner text has the numerator reversed, so derive and test it (the script does). Under ISDA
spread compounding the PV is non-linear in Z; solve with the quadratic, not a linear shortcut.

### 4. Basis DV01 and risk (never a parallel DV01)

1. Parallel DV01 of a float-float swap is small and meaningless; one pay-SOFR/receive-3M-LIBOR 5y $10mn swap made
   about +$80k as SOFR fell 1.55 to 0.01 and 3M LIBOR 1.836 to 1.216, with a tiny DV01 (QF Stack Exchange, DV01 on
   LIBOR vs SOFR basis swaps, Dec 2020).
2. **Instrument deltas:** bump each curve-building instrument (par OIS, futures, tenor basis swaps) up and down,
   refit, reprice. P&L explain for linear products is delta × move. Map to reporting instruments with the inverse
   Jacobian, then aggregate: parallel risk per curve, bucketed risk, or n-sd moves in the first PCs. Build summary
   numbers from the building blocks.
3. **Spread DV01:** `−N · Σ d_a v_a · 1e-4` per bp (negative for the spread receiver). Flat check: $100mn, 5y quarterly leg,
   DF 1: 20 × 0.25 × 1e-4 × 1e8 = $50,000/bp.
4. **Discounting vs forecasting:** `dP/dr = dP/ds + dP/dz` (discount-curve spread s, forecast spread z); fixed flows
   have no forecasting basis. Quick discounting check on an off-market annuity swap:
   `dP/ds ≈ −P · tenor / (2 · 10,000)`. For a 30y GBP swap with $1mm pv01 under a mismatched CSA, a 1bp rate move changes its
   discounting (CSA-basis) pv01 by ±$1mm × 30 / 20,000 = ±$1,500: a cross-gamma, not a first-order risk (Darbyshire,
   Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022).
5. **Cross-gamma** between outright and basis risk is about 1e-4 of first-order risk but scales with the square of the
   move; run separate PCAs for outright and basis grids (one PCA is swamped by outright variance); hedging with a
   different product type hedges delta, not basis cross-gamma.
6. Proxy hedge when the basis is illiquid: minimum-variance outright hedge `x* = −Q_hh⁻¹ Q_hb S_basis`; it leaves
   residual risk (a worked case cut the VaR multiplier by only about 25%). See [derivations](references/pricing_and_risk.md).
7. After the IBOR transition one RFR curve per currency removes most basis cross-gamma; it persists in EUR,
   AUD, NZD, SEK, NOK and in CSA/xccy mismatches.

Hand the bucketed output to [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md).

### 5. Futures expressions and weights (USD)

- Quote the basis in rate terms, then choose the contract month that spans the catalyst (debt-limit resolution,
  tax date, QT end, a quarter-end). One cleanest instrument for overnight secured-vs-unsecured exposure is the 1M
  SOFR vs 30-day FF month spread (1:1, equal bp value). A 3M SOFR vs FF spread also carries period and averaging
  differences (Huggins & Schaller, SOFR Futures and Options, 2022).
- Bp value: 1M contract $41.67/bp ($5mn × 30/360), 3M contract $25/bp. 10 three-month = 6 one-month in value
  (6 × 41.67 = 250.02 vs 10 × 25 = 250). $100mn for three months = 60 one-month = 100 three-month (CME, STIR
  Inter-Commodity Spreads, Apr 2024).
- Exchange spread price: `spread = avg front-leg price − back-leg price`; e.g. (94.890 + 94.735)/2 − 94.7775 =
  0.035, i.e. 3.5bp for the FF vs 3M SOFR spread of Jun-2024 (CME, Apr 2024).
- The standard 6:10 hedge is **not FOMC-neutral** when a meeting is off-centre: recompute from days-after-meeting
  fractions (example in the derivations file; 3.1 + 2.9 one-month contracts per ten three-month, not 3 + 3).
- Calendar spread of the futures basis (month A minus month B) shows relative expected tightness between periods:
  bill supply, leverage demand, reserve injections. A negative near-dated spread that implies an implausible
  pre-year-end Fed injection is likely to be faded (Conks, The Post-QT Era, 24 Nov 2025).
- Averaged vs compounded: compounded ≥ averaged, equal only at zero rates. Gap ≈ `r² · T / 2`: ≤ 0.1bp at 2021–22
  rates, about 1bp over a month and 3bp over a quarter near 5%. Compounded 1y: 1% → 1.005, 3% → 3.05, 5% → 5.13
  (Huggins & Schaller, 2022). Adjust when the gap is comparable to the bid/offer. Convexity is a separate
  adjustment ([stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md)).

### 6. Screen: level, z-score and driver residual

1. Compute for each (type, leg pair, start, tenor): level, 5d change, 252-day mean/sd, z, percentile, AR(1)
   half-life (`scripts/basis_tools.py`). Default window 1y because basis regimes change within years; use 3–5y
   only for regime comparison. Candidates: |z| ≥ 2 **and** the move not explained by the driver.
2. Residual regression (the dealer "basis monitor"): regress the basis on its driver(s) over 1y, report beta,
   correlation, residual and residual sd; positive residual = basis wide vs driver. Examples: LIBOR-OIS and
   3s1s on 2y swap spreads, 6s3s on spot 6s3s (Citi, US Rates Weekly, 18 Jan 2019 and 27 Mar 2020); SOFR-FF on
   bills-minus-reserves.
3. Compare with the model path month by month: fit SOFR-FF on reserves and bills with month-end dummies, project
   bills/reserves/TGA, overlay the average pre-period-end change, then compare with the futures basis month by month
   (Citi, Short-End Notes, 13 Jun 2025).
4. Carry and roll before the idea. Receivers of spot E/E basis pay heavy negative carry: Nordea's screen (17 Jan 2024)
   had 1y E/E at 7.8bp with annualised carry+roll −77.6 and 5y E/E 11.9 with −33.1, while 5y5y E/E was near flat
   (−0.6; units as published, the table's later columns may be cumulative). Prefer forward-start or a structure that pays carry.
5. Check **horizon**: front-end basis beta to rates explains 20–30% of daily variance but is not significant over a
   week or longer, so do not fade it on longer horizons (JPM, Markets struggle to feed the convexity beast, 28 Feb 2020).

### 7. Structures

| Idea | Expression | Why |
|---|---|---|
| USD funding pressure (debt-limit rebuild, bill flood, RRP at zero) | Long realised SOFR − EFFR for the month spanning the catalyst (= short the futures price spread) | SOFR moves, EFFR idle |
| USD liquidity relief (QT end, bill purchases, TGA drawdown) | Short realised SOFR − EFFR for that month (= long the futures price spread) | intervention before a repo spike lowers SOFR faster than idle EFFR |
| SOFR-FF term | Swap basis; discount-hedge flows make the long end wider | CCP switch and LDI flows |
| EUR 3s6s forward basis too low | Pay 5y5y 3s6s, size by carry | 6M fixing priced below 3M after 8y is "irrational" (Nordea, 17 Mar 2020) |
| Hedge corporates with SOFR swaps | add the SOFR-FF leg | secured vs unsecured basis |
| Strip vs swap "arbitrage" | read as tenor basis first | a 0.25% 6s3s basis explained most of a 40bp strip-vs-swap zero gap, Nov 2011 (Aikin, STIR Futures, 2012) |

Prefer an outright basis position to a basis curve trade when the whole curve should move on one catalyst
(BofA, Funding & debt limit: history lessons, 27 Jun 2025).

## Worked examples

1. **Restate trade levels (USD debt-limit).** BofA 27 Jun 2025: short Oct-25 "SOFR/FF" at −4bp, target −8, stop
   −1 (FF − SOFR). In realised terms: SOFR − EFFR from +4 to +8bp, stop +1. Debt-limit analogues averaged an SOFR-FF
   change of −7.7/−4.4/−5.1bp over 1/3/6 months in FF-less-SOFR terms, i.e. SOFR vs FF wider by 4–8bp
   (BofA, Funding & debt limit, 27 Jun 2025; BofA, Lower UST WAM, 2 Jul 2025). Reverse view, 6 Oct 2025: long Jan-26
   at −6.5 (realised +6.5), target −2 (+2), stop −11 (+11) (BofA, FHLB liquidity & SOFR/FF widening, 6 Oct 2025).
   Bp value on futures: $41.67 per bp per contract.
2. **Futures basis sign and monitor.** Realised path read from charts (approx.): May-25 −2.5bp, Jul +0.5, Sep +7,
   Oct +11, Nov-25 peak +12, Dec +6 (Fed bill purchases begin), Jan-26 +3 (Conks, Nothing Ever Happens, 1 Mar 2026).
   The 3 Oct 2025 snapshot (SOFR 4.18, TGCR 4.16, IORB 4.15, EFFR 4.09, ON RRP 4.00) is +9bp realised and shows the corridor: SOFR above IORB signals banks lending reserves in repo; EFFR
   above IORB would be the stronger "Fed adds reserves" trigger (Conks, Takeoff Begins, 6 Oct 2025).
3. **EUR: bank locks a margin.** Feb 2022, 2y estr vs 3M Euribor basis 13.8bp. A bank funding at estr flat and lending
   at 3M Euribor + 1% receives estr + 13.8bp against paying Euribor, locking 1.138%. The 2y fixed vs 3M Euribor swap at
   0.078% with a 13.8bp basis values both legs at 100.281 (Tuckman & Serrat, 2022; script `rfr_ibor_two_curve`).
4. **Forward basis sanity (EUR 3/6m).** Implied 1y-forward 3/6m basis turned negative beyond 7–8y to about −2.5bp
   on 17 Mar 2020, which the author called irrational; trade: pay the 3/6m basis (5y5y) but timing depends on
   receiving flows and position squaring (Nordea, EUR Rates Flash, 17 Mar 2020).
5. **Legacy combination (USD, 2019).** 1y1y 3s1s widener vs FF-LIBOR tightener at 2:1 DV01: quote = 2 × 3s1s − FF/LIBOR
   = 2 × 11.0 − 25.5 = −3.5bp; target 0, stop −6, carry 4.3bp/yr; chosen because 3s1s forwards have low pass-through
   from spot and FF/LIBOR forwards have high (Citi, US Rates Weekly, 2 Aug 2019). One-year roll of the combination 6.0bp (FF/LIBOR 3.0, 3s1s 4.5); a later 18m1y version of the trade
   was quoted with carry 4.3bp/yr (Citi, 17 May and 4 Oct 2019).
6. **Compounding vs average.** Constant SOFR 5% over a quarter: simple vs compounded gap about 3bp on the 3M settlement
   formula; zero rates: 0 (Huggins & Schaller, 2022).

## Signals & interpretation
- Realised SOFR − EFFR positive and rising: collateral outruns cash (bill supply, TGA rebuild, hedge-fund repo
  demand); about −1 to −3bp is the abundant-reserves fair value; persistently negative (SOFR below overnight FF)
  is treated as an "event horizon", not an equilibrium, ahead of a regime change (Conks, The Warsh Prelude,
  4 May 2026). History: about −10bp (Oct 2016–Jan 2018) to +3bp (Feb 2018–Sep 2019) regime averages, +11–12bp in
  Oct–Nov 2025. Use these as the range, not as targets.
- Scarcity ladder (USD): SOFR above IORB (banks lend reserves in repo) → EFFR above IORB (reserves scarce; the Fed
  likely adds reserves) → EFFR above the standing-repo minimum bid. Reserves/bank assets: abundant > 13%,
  ample 11–13%, scarce < 11% (Conks, Money Market Update, 15 Mar 2025).
- Two-regime anchor (BofA, US Treasury repo primer, 7 Jul 2025): ON RRP ≥ $500bn keeps SOFR near the RRP rate
  (SOFR − tri-party ≤ 4–5bp, FF can rise vs SOFR); below $500bn upward pressure on SOFR and more volatile prints.
  Bills substitute for repo: desk FF − SOFR falls about 1bp per $100bn rise in (bills − reserves) (Citi, Time for moderation, 17 Feb 2023).
- Secured RFRs hide bank credit stress: in the Mar 2020 stress LIBOR spiked above Fed funds while SOFR was calm, so a credit-sensitive
  index versus the RFR/FF leg (LIBOR or BSBY then, Euribor/BBSW/BKBM/STIBOR/NIBOR now) is the stress gauge (Conks, The Silent Monetary
  Revolution, 7 Feb 2023).
- Tenor basis wide in z and driver residual **and** forward carry ≥ 0 → candidate; wide only because credit or the policy
  path is priced → not a basis trade.
- A hedge package should be sized to an explicit residual exposure: normalisation structures stay directional to spot
  LIBOR/OIS (regression beta 0.36–0.56), so overlay to a target beta (Citi, US Rates Weekly, 27 Mar 2020).
- Stop out when the vol regime shifts even if the thesis holds; never read every SOFR spike as stress (JPM, 6 Mar 2020).

## Pitfalls
- **Sign.** Futures price spread = −realised basis; desk "SOFR/FF" = FF − SOFR; "tight" xccy = looser USD funding but swap
  spread "tightening" = worse plumbing. One source's own exhibits use both signs. Normalise first.
- **Which leg carries the spread.** OTC convention puts it on the shorter or overnight leg, but cleared-product tables
  can be ambiguous on the spread-eligible leg; restate legs from the confirmation, and check each CCP's terms.
- **Regime breaks.** SOFR statistics break at the SRF introduction (Jul 2021; dated Aug 2021 in one source; SOFR ≤ SRF rate becomes a soft cap),
  the Dec 2024 ON RRP cut, QT end, bill purchases. Re-estimate post-break; regressions of SOFR − IORB on liquidity
  have R² near zero in 2024–25 (0.01–0.17) and the forecast moved from −2.1 to −5.6bp on reweighting.
- **Period-ends.** Month/quarter-end and mid-month coupon/tax settlement dominate SOFR-based spreads; filter them from
  "normal" z-scores and trade them deliberately as period-specific views.
- **Thin and idiosyncratic EFFR.** FHLBs are about 95% of lending, foreign banks 93% of borrowing; SOFR methodology or clearing
  changes can move prints independent of funding (watch SOFR − TGCR and the 25th/75th percentile spread).
- **Corridor limits bind in theory.** The SRF is an impaired ceiling (stigma, timing, balance sheet); SOFR ≤ EFFR is not a hard
  bound (violated for weeks in 2018–19).
- **Basis swaps are illiquid** (under 1% of OTC IRD turnover; legacy FRA/OIS liquid only in the front IMM dates; LIBOR/LIBOR out to
  30y and 1y1y most liquid historically). Price from the curve identity when quotes are thin, and use bid/offer in
  the edge.
- **Mixed tenors in one curve** give dirty prices and unstable hedges. Hedge with same-underlying instruments. Plot forwards,
  not zeros; a smooth zero curve can hide forward oscillations of tens of bp, and strip the turn-of-year first.
- **Fixing risk.** Lookback and lockout compounding create lumpy, hard-to-hedge exposures; weekend/holiday fixings
  dominate short legs. Payment delay and observation shift are the market standard (Darbyshire, Coding Interest Rates).
- **Term-rate benchmarks.** Term SOFR is built from futures through a smoothness penalty (lambda about 0.33, which moved the
  6M rate only about +0.5bp vs lambda 0 on 27 Jan 2022; 0.42% vs 0.73% at lambda 200). The authors suspect an upward bias from
  upward-sloping curves; hedging it costs "multiple basis points" and has no interdealer market (Huggins & Schaller, 2022).
- **Fallback spreads anchor long-dated legacy forwards**: SOFR/LIBOR forwards traded wide of fallback estimates; test
  forwards against the median, 5y-lookback fallback method before calling them rich or cheap.
- **Forward vs spot pass-through.** A spot view maps to forwards unevenly across legs (1s/OIS high pass-through, 3s1s low).
- **Single-source regressions.** Parameters quoted in the references are dated and regime-specific; refit.
- **Levels regressions and half-lives.** Basis and driver (reserves, bills) are persistent, so a levels regression has inflated R² and
  t-stats: check the residual for stationarity or confirm on weekly changes (the Citi betas are weekly changes). With about 250 daily
  points an AR(1) fit biases phi down and the half-life short; use a longer sample for it. The screen's z baseline excludes the
  latest observation, and the driver fit excludes it too (no look-ahead).
- **Contract terms differ by product.** Cleared USD basis specs (LCH, 2019): SOFR leg with spread-exclusive compounding and a 2-day payment lag,
  LIBOR-leg fixing T−2 versus overnight leg T+1; the spread-eligible leg is ambiguous in some tables, so confirm it before reading a quote.

## Output
Return for each candidate:

| Column | Content |
|---|---|
| Basis | type, `leg_a` vs `leg_b`, start × tenor, currency, snap |
| Convention | sign (spread on leg_a, rate-space restatement), units |
| Level / z / percentile / half-life | 1y window, last obs date |
| Driver residual | beta, residual, residual sd, z vs driver |
| Carry+roll | annualised bp, ratio to realised 50d vol |
| Basis DV01 | per bp with its sign; per-curve and bucketed delta |
| Catalyst & month | contract month or tenor window; dates; scenario of what changes the sign |
| Structure | legs, weights (bp value or DV01), entry/target/stop in rate terms |
| Risks | period-end, regime break, liquidity, index change |

For a trade idea, pass the table to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) with the sign
restatement in the first line.

## Scripts
- [`scripts/basis_tools.py`](scripts/basis_tools.py): sign conversion from futures prices, RFR period compounding,
  basis-swap fair spread (PV = 0), spread PV and basis DV01 (sign tested by repricing), annuity-ratio conversion,
  the two-curve identity, AR(1) half-life, driver residual regression and a ranked monitor over the `basis_swaps`
  table. `python scripts/basis_tools.py --help`. `--selftest` checks known cases (published compounding examples,
  the estr/Euribor 100.281 case, flat 3s6s = 10bp, DV01 sign) and exits non-zero on failure.

## Related skills
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): GC vs special, SOFR-TGCR, period-end repo, balance sheet.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): QT, RRP/TGA/SRF, reserves ampleness, the SOFR-FF driver.
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bill supply and MMF demand behind bills-minus-reserves.
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): compounded RFR mechanics, term RFR hedging, fixing ladders.
- [stir-futures-rv](../stir-futures-rv/SKILL.md) and [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures spreads, packs, convexity.
- [xccy-basis](../xccy-basis/SKILL.md): FX-OIS and cross-currency basis, which embeds the tenor and index basis here.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md) and [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): the 2y swap spread = OIS/GC funding spread + 2y SOFR/FF basis.
- [fi-curve-construction](../fi-curve-construction/SKILL.md): OIS plus tenor curves, forwarding vs discounting, turns.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CSA discounting and the discounting-risk driver of long-end basis.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): Jacobian risk transforms and bucketing.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): index, day-count and calendar conventions per market.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): capital and haircut cost behind the unsecured-secured spread.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll check for forward-start basis.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md), [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md), [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): z, half-life, period-end filters.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): LDI/insurer and ALM flows behind the long-end basis.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): hand-off; [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): inputs.

## References
- Huggins & Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): inter-commodity spreads and weights, FOMC-neutral hedges, averaged vs compounded gap, Term SOFR critique, SOFR ≤ EFFR bound.
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): capital-cost g·q·d, repo-LIBOR model, intra-currency basis pricing, ASW decomposition.
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): estr vs Euribor basis, two-curve identity and 100.281 example, futures-rate ordering.
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022): basis swap PV, discounting vs forecasting split, cross-gamma, LCR effect on tenor basis.
- Darbyshire - Coding Interest Rates: spread delta non-linearity and RFR fixing conventions (edition and year not shown in pages read).
- Ametrano & Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping (SSRN, Apr 2013): multi-curve procedure, basis-swap quoting, synthetic FRA-OIS.
- Quantitative Finance Stack Exchange - DV01 on LIBOR vs SOFR basis swaps (Dec 2020): instrument deltas and inverse Jacobian.
- Lehman Brothers (Tuckman, Porfirio) - Interest Rate Parity, Money Market Basis Swaps, and Cross-Currency Basis Swaps (Jun 2003): credit theory of tenor basis.
- Lehman Brothers (Pulman) - The Short-End of the Curve (10 Jul 2007): OIS-LIBOR basis curve, policy-path caveat, basis risk monitoring.
- Credit Suisse - Basis Points: A Guide to the Front-End and Basis Swap Markets (18 Feb 2010): product mechanics, stub risk, liquidity, legacy examples.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): strip vs swap as tenor basis, OIS mechanics, bundle weighting.
- BofA Global Research - SOFR/FF term structure post "big bang" (22 Oct 2020); US Treasury repo primer 2025 edition (7 Jul 2025); Funding & debt limit: history lessons (27 Jun 2025); FHLB liquidity & SOFR/FF widening (6 Oct 2025): regimes, regressions, dated trades.
- Citi Research - US Rates Weekly (18 Jan, 2 Aug 2019; 27 Mar 2020) and Short-End Notes (13, 27 Jun 2025): basis monitor, 2:1 structures, path model.
- J.P. Morgan - Bills, Bonds, and basis...oh my (7 Feb 2020); Markets struggle to feed the convexity beast (28 Feb 2020): discounting-risk driver, multi-horizon beta.
- Nordea Markets - EUR rates: Pushing back (17 Jan 2024) and EUR Rates Flash (17 Mar 2020, 23 May 2019): tenor-basis screen, forward 3/6m basis, fixing methodology.
- LCH SwapClear - Product Eligibility, USD (Oct 2019): cleared LIBOR-FF / LIBOR-SOFR basis terms.
- Conks (Monetary Mechanics) - Plumbing Notes and primers (2023–2026): futures sign conventions, calendar spreads, FHLB channel, scarcity ladder.
- CME Group - Short-Term Interest Rate Futures Inter-Commodity Spreads on Globex (Apr 2024) and SOFR Discounting Transition Process for Cleared Swaps (2 Jun 2020): weights, spread pricing, FF-SOFR basis swaps.
- Bank for International Settlements - Quarterly Review, Goodbye Libor, hello basis traders (Dec 2025): basis swap turnover, fixing risk, OIS shares.
- Deutsche Bank Index Quant - Interest Rate Curve Creation Process (2 Feb 2023): basis instruments and conventions per G10 currency.
- Board of Governors of the Federal Reserve System - FEDS Notes, Historical Proxies for the Secured Overnight Financing Rate (Bowman, Jul 2019): SOFR vs EFFR OIS gap.
