---
name: stir-rfr-compounding-and-fixing-risk
description: Mechanics and risk of compounded overnight RFRs (SOFR, ESTR, SONIA, TONA, CORRA, SARON, SWESTR, NOWA, AONIA) - daily compounding vs arithmetic averaging, payment delay / observation shift / lookback / lockout, spread compounding, SR3/SR1/SO3/FST3/CRA reference-period settlement, partially-fixed periods, per-fixing reset-risk ladders, futures-vs-forward convexity, CME Term SOFR and term-vs-overnight premia, and hedging term-rate or IMM-misaligned cash flows with overnight futures. Use when asked how a compounded RFR leg or futures contract settles, what a stub or front contract is worth per bp, how much fixing/reset risk a book carries by date, SR1 vs SR3, in-arrears vs term rate, lookback vs shift, or how to hedge Term SOFR / a loan / a non-IMM swap with futures.
---

# RFR compounding, fixing conventions and reset risk

Overnight RFR products pay on the daily rate compounded (or averaged) over a reference or accrual period. Which days
count, how many calendar days each fixing carries, and which fixing date feeds which accrual day decide the cash flow, the
hedge ratio and where the residual risk sits. Most "RV" in the front end that looks like a rate gap is a convention gap
(1M arithmetic vs 3M compounded, shift vs lookback, IMM vs non-IMM dates, forward-looking term vs backward-looking
compounded). This skill gives the exact formulas, the per-fixing risk ladder, and the checks to run before calling
something cheap or rich.

## When to use
- "How does SR3 / SR1 / SO3 / FST3 / CRA settle?" "What is one bp worth in the front contract mid-quarter?"
- Pricing or risking an OIS, FRN, loan or cross-currency leg that compounds an RFR with lag, shift, lookback or lockout.
- A swap or loan period that does not align with IMM reference quarters: how much reset (fixing) risk, on which dates, and how many contracts hedge it.
- SR1 (arithmetic, monthly) vs SR3 (compounded, quarterly) spread, or a wiggle at month/quarter ends in a futures-implied curve.
- Term SOFR (or another term RFR) vs compounded RFR / OIS-implied, and how to hedge a term-rate payment with futures.
- Futures vs forward gap (convexity) sizing before building a curve from futures (hand the model detail to [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Daily RFR prints with publication time | `rate_fixings` | daily, from the earliest period start in the book; keep `pub_ts_utc` | `rate_pct`; use the latest `is_final` vintage per `fixing_date` except when testing "known at time t" |
| Index definitions: day count, publication lag, status | `rate_indices` | static | ACT/360 vs ACT/365F changes the compounding basis B |
| Business-day calendars (fixing and payment) | `calendars` | holidays for the horizon | Weekend and holiday fixings carry 3+ days; exchange and cash calendars differ |
| Payment lag, spot lag, frequency per curve | `swap_conventions` | static | `pay_lag_days` drives discounting and the lag convexity (negligible) |
| STIR contract terms: reference start/end, method, bp value | `fut_static` | per listed month | `ref_method` compound / average; `ref_start_date` is the IMM date for SR3-type |
| STIR prices | `stir_quotes` | daily settle | price = 100 - rate; SR1 and SR3 must not be mixed within one curve fit |
| Policy meetings | `cb_meetings` | schedule | reset risk and Term SOFR jumps concentrate on these dates |
| Forward overnight rates for unpublished days | `curve_zero` (or flat user input) | as-of snap | unfixed days of a live period are forecast from the curve; never invent them |

If any are missing, ask for them or hand off to the data adapter ([data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)). Check the
fixing publication lag before calling a day "known": SOFR for day t prints on the next business day (see `rate_fixings`).

## Method
Notation: r_i = daily rate (decimal) for fixing day i; d_i = calendar days it is applied (1; 3 for Friday; more around holidays);
B = day-count basis (360 for SOFR, ESTR, SARON, SWESTR, Euribor-style; 365 for SONIA, CORRA, TONA, AONIA; NOWA is ACT/365 but its
fallback is rebased to ACT/360); D = sum d_i. Rates in percent in tables, bp for spreads and risk.

### 1. Compounded and averaged period rates
- **Compounded (ISDA / NY Fed):** `R = [ prod_i (1 + r_i d_i / B) - 1 ] * B / D`. Cash on notional N: `N * (prod_i (1 + r_i d_i/B) - 1)`.
  The identity `1 + R*D/B = I(end)/I(start) = v_start/v_end` links it to a compounded index and to discount factors; it holds
  only for fixed-denominator day counts (ACT/360, ACT/365F). 30E/360-style rules break it
  (Darbyshire, Coding Interest Rates, c.2024).
- **Arithmetic average (SR1, Fed Funds style):** `R = sum_i r_i d_i / D`.
- **Compounded >= averaged** with equality only at zero rates. Constant-rate gap over a quarter is about `r^2 D / (2B)`:
  zero at 0%, about 3bp at 5% (Huggins & Schaller, SOFR Futures and Options, 2022). One-year loan at constant SOFR of 1/2/3/4/5%
  accrues 101/202/305/408/513bp (same source, Table 3.2).
- **Rounding of published/compounded results (ISDA 2021 matrix):** 0.0001% for AONIA, SARON, ESTR, SONIA, NZIONA; 0.00001%
  for CORRA, TONA, NOWA, SOFR. SR3 settles to the nearest 0.01bp.
- **Day weights:** a Friday fixing counts d=3, so a weekend rate has 3x the weight of a Tuesday; around Easter/Christmas short OIS
  are dominated by those fixings. Always build the schedule from the `calendars` table, never assume 1 day per business day.

### 2. Fixing conventions (which rate feeds which accrual day)
| Convention | Rule | Where used | Risk note |
|---|---|---|---|
| Payment delay | each day's rate on its own date; payment k business days after period end (SOFR 2, ESTR 1 in the book's convention sheet, SONIA 0; always read the trade's own `pay_lag_days`) | OIS, XCS (market standard) | DF-based, hedges cleanly with futures |
| Observation shift n | observe rates for dates n BD earlier; weights are the observed days' own day counts | FRNs, loans; common n = 2 or 5 | same exposure shape as payment delay, shifted n days |
| Lookback n | day i uses the rate of day i-n, weights from the unshifted calendar | some loans | a 1-day fixing applied over a weekend gets x3, a Friday fixing applied over 1 day gets /3: hard to hedge, rarely worth adopting |
| Lockout n | last n days reuse the rate of the day before them | some loans | locked rate carries (n+1) days (about 3x for n=2) |
| ISDA 2021 defaults when silent | shift 5 BD, lookback 5 applicable BD, lockout 5 BD | confirmations | the matrix cells are placeholders the parties set |

Longer lookback/lockout means more mismatch with futures and a costlier hedge (Huggins & Schaller 2022, Ch.3). Check the lockout
n semantics in the confirm: the book's Table 8.4 treats the locked rate as covering n+1 days.

### 3. Spread over an RFR (float spread z)
- **None-simple (spread after compounding, the NOWA OIS and most XCS convention):** `R = (1/D)(prod(1+r_i d_i) - 1) + z`. dR/dz = 1.
- **ISDA compounding (spread inside each step):** `R = (1/D)(prod(1+(r_i+z)d_i) - 1)`. dR/dz about `(1+(rbar+z)dbar)^(n-1)`, slightly above 1.
- **ISDA flat compounding** (spread earns interest only through the daily rates): no closed form, dR/dz exceeds 1 for positive rates; the
  source recommends avoiding it. Confirm the method before comparing books or hedging basis. Averaging allows only none-simple
  (Darbyshire, Coding Interest Rates, c.2024; details in [references/compounding_math.md](references/compounding_math.md)).

### 4. Partially fixed periods and the front contract
1. Past days use published fixings; future days use forwards from the curve (or a flat user rate), same as the settlement formula.
2. Value of 1bp in a compounded futures contract: `bp_value_live = bp_value * sum_{unfixed k} d_k * prod_{i!=k}(1 + r_i d_i/B) / D`
   (= bp_value x the sum of dR/dr_k over unpublished days; the 1/B in dR/dr_k cancels the B in R). At the start it is about the quoted tick value
   (USD 25, GBP 25, EUR 25, CAD 25, CHF 25; SR1 USD 41.67), higher by roughly rD/(2B) (about 1% at 4%, because each day's rate is also grossed up by the other days' interest);
   mid-period it is about the unfixed share of days (slightly above, same reason). Use the live
   value, not 25, to size a front-contract hedge (Huggins & Schaller 2022, Ch.8). Script: `contract_bp_value`.
3. A revision of the last day's SOFR cannot enter SR3 settlement; revisions of earlier days do (Huggins & Schaller 2022, Ch.2).

### 5. Futures reference periods and settlement
- **3M compounded contracts** (SR3 USD, SO3 GBP, FST3 EUR, CRA CAD, TONA 3M JPY, SW3 SEK, FSR3 CHF): price = 100 - R, R compounded over the IMM
  reference quarter, from the 3rd Wednesday of the contract month (inclusive) to the 3rd Wednesday three months later (exclusive). SR3 last trade: the
  business day before the 3rd Wednesday of the delivery month, final settlement the next business day when the last SOFR prints (Huggins & Schaller 2022, Ch.2).
- **SR1:** arithmetic average over the calendar month, settled to 0.1bp (1M); USD 41.67/bp.
- **Month code = start of the reference quarter** for the RFR contracts. Legacy IBOR codes name the expiry month, so mixing the two shifts dates by a
  quarter (FactSet, Interest Rate Future white paper, 23 Mar 2023). Example: SFRM2 references the quarter starting 15 Jun 2022 and expires 21 Sep 2022, whereas the
  legacy term contract ERM2 expired 13 Jun (Tuckman & Serrat, Fixed Income Securities, 2022, Fig 12.5).
- **The settlement formula, not the label, defines the rate.** "Compounded daily" with equal daily rates does not settle at that rate, because each day's
  rate is simple while accrual compounds (OpenGamma/Henrard, Overnight Futures Convexity Adjustment, 2018).
- **Options.** SR3 options stop trading the Friday before the 3rd Wednesday of the contract month, i.e. at the start of the reference period, so the option
  underlies a forward compounded rate and a floorlet is unhedged by listed options for about 3M plus a few days. SR1 options remain after that; they are American
  arithmetic Asians (Huggins & Schaller 2022, Ch.5 and Ch.8). Option distribution detail: [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md).
- **Roll:** roll the 2nd listed SR3 into the 3rd before the front enters its reference quarter, not front-to-back as with legacy ED. The Dec-19 to Mar-20 roll cost 138bp at the end of
  the reference quarter against 4bp at its start (Huggins & Schaller 2022, Ch.2). See [fut-calendar-roll](../fut-calendar-roll/SKILL.md).

### 6. Per-fixing exposure and the reset-risk ladder
A 1bp move in one fixing changes PV by an amount that depends on period length, spread and method, so exposures are not comparable until standardised.
1. **Cash per bp of fixing s** (payment at T, DFs held fixed): `dC/dr_s = N * v_T * sum_{days k fed by s} (w_k / B) * prod_all / (1 + r_k w_k / B)`; per bp multiply by 1e-4.
2. **One-day-equivalent notional:** `N_s = dC/dr_s / ((d_own_s/B) * v(m_s))`, d_own_s = true days from the fixing date to the next business day (not the lookback-shifted weight), m_s = end of that day.
   Check: a USD 10/bp weekend fixing (3 days, ACT/365F, DF 1) equals USD 12,166,667 notional (Darbyshire, Coding Interest Rates, c.2024).
3. **Aggregate across the book by fixing date**, split known vs open at the as-of fixing date. Only open fixings are live risk.
4. **Bucket and hedge:** fold open fixings into SR3 reference quarters (the stub to the next IMM goes with the front contract at its live bp value, see 4). Contracts = bucket cash per bp / bp value.
   The residual after an IMM strip is the mismatch ladder (non-IMM start/end, lookback/lockout distortions, central-bank-date clusters).
5. **Reset VaR is not in standard VaR**, which measures immediate risk only; the loss accrues over time so shock-and-panic rarely forces action (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022, s24.1).
   Heuristic (not from the sources): residual bucket cash/bp x vol of the fixing over the time to that fixing; weight buckets whose fixing falls just after a policy meeting more
   (jump-like). Calibrate on history before relying on it.
- **Scale:** for equal notional a daily RFR fixing carries about 1/30 of a 1M IBOR fixing's risk, 1/90 of 3M, 1/182 of 6M, 1/365 of 12M (Darbyshire 2022, s18.2.4), so an RFR-only swap book has many small, mostly self-hedged resets; the big ladders come from lookback/lockout, mismatched start dates and mixed term/overnight books.
- Script: [`scripts/rfr_compounding.py`](scripts/rfr_compounding.py) produces the ladder for payment delay, shift, lookback and lockout and reproduces the book's fixing table (below).

### 7. Futures vs forward (convexity) - sizing only
Daily margining makes the futures rate exceed the forward. Normal one-factor model with constant drift, sigma = short-rate normal vol in bp/yr, t = years to the START of the reference period, beta = underlying term
(Tuckman & Serrat 2022, s12.6):
- term-rate future: `s^2 t^2/2 + s^2 t b/2`, b = 0.25
- averaged ON (SR1): `... + s^2 b^2/6`, b = 1/12
- compounded ON (SR3): `... + s^2 b^2/3`, b = 0.25
Ordering at the SAME beta: compounded > averaged > term > forward; the table below mixes tenors (3M term and compounded vs 1M average), so the 1M average shows the smallest number. At sigma = 80bp: t = 1/2/5/10y gives 0.4/1.4/8.4/32.8bp (Euribor-type), 0.3/1.3/8.1/32.3 (1M average), 0.4/1.5/8.4/32.8 (3M compounded). The `s^2 t^2/2` term dominates.
Ho-Lee form: futures = forward + `sigma^2 T1 T2 / 2`, T1 = futures expiry, T2 = end of the reference period, sigma = normal short-rate vol (BSIC, Understanding Convexity Bias in STIR Futures Markets, 29 Mar 2026). The SR3 payoff itself is linear in the daily compounding
(an overnight-invested balance gives B_T = N(1 + tau R0)), so for SR3 the quoted rate is the forward before the margin effect; SR1 needs the adjustment (Huggins & Schaller 2022, Ch.5). This conflicts with the 3M compounded line above (Tuckman & Serrat give SR3 a positive adjustment): treat it as an open source conflict, bound the effect with `futures_convexity_bp` and defer to the model in the convexity skill. Averaged vs compounded adjustment
differs by under 0.01bp for 1M contracts and up to about 1/3bp at long maturities; 3M SOFR adjustments were about 4-4.5bp for the furthest 2024 contracts (FINCAD/Rosen, Averaged Overnight Rate Futures Convexity Adjustment, 1 Mar 2019).
Hull-White overnight-futures adjustments (exact for time-only vol) are in Garcia-Lorite & Merino (2023). Script: `futures_convexity_bp`. Model choice and curve use belong in [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md).

### 8. Term RFR benchmarks and hedging
- **CME Term SOFR (1M/3M/6M/12M):** built from the prior day's first 13 SR1 and first 5 SR3 (in-period contracts adjusted for known fixings), sampled in 14 half-hour windows 7:00-14:00 CT (VWAP, else optimised mid, else
  prior price); a pure-jump model with jumps only at FOMC dates is fitted and compounded with the ISDA formula. Criticisms: no diffusion (cannot price options), ignores non-policy spikes, futures beyond the term end can affect the fixing,
  upward bias from curve slope (6M Term SOFR on 27-Jan-22 about +0.5bp at the CME regularisation weight lambda about 0.33 vs lambda 0) (Huggins & Schaller 2022, Ch.3 and Ch.8).
- **Term vs overnight premium.** Term rate minus compounded FF OIS, Jun-18 to Jan-19 (bp, mean / SD / 5th / 95th): 1M 1.6 / 1.4 / -0.4 / 4.1; 3M 1.7 / 1.4 / -0.3 / 4.0; 6M 1.6 / 1.6 / -0.8 / 4.3; over 90% of differences under 5bp
  (Heitfield & Park, Inferring Term Rates from SOFR Futures Prices, FEDS 2019-014, Feb 2019). Realised term premium over compounded FF futures 2000-19, mean / SD: 1M 1.3 / 8.0; 3M 4.4 / 15.6; 6M 10.5 / 28.3bp,
  about 0 post-2011 outside crises (same source). Indicative 3M SOFR term averaged 3.2bp above 3M EFFR OIS vs a 2.8bp compounded SOFR-EFFR gap (Bowman, FEDS Notes, 15 Jul 2019).
- **Hedge by sensitivity, not by label.** For a USD 10m 3M loan paying forward Term SOFR, if 3M Term SOFR moves +5bp when the Dec SR1 moves -10bp in price, payment change is 10m x 0.0005 x 90/360 = USD 1,250; one 10bp SR1 move is USD 416.70, so sell 3 SR1. The hedge is local: recompute the sensitivity to each input futures price by central differences (+/-5bp) and re-hedge as the curve moves (Huggins & Schaller 2022, Ch.8).
- **Compounded loans aligned to SR3 reference periods hedge near-perfectly with SR3** (residual = interest on variation margin); simple-average loans hedge with SR1 (same source, Ch.3).
- **IMM-swap strip hedge:** receiver PV (per 100) `= C/4 * sum_{i<=4} 1/prod_{j<=i}(1 + R_j D_j/360) + 100/prod_{j<=4}(...) - 100`, R_j = (100 - price_j)/100 as a decimal, C in the same percent units as the 100 par; hedge ratio = PV change for 1bp of each R_j divided by the contract bp value. Shortcut: parallel PV01/25 spread evenly (valid when DFs are about 1).
  Real OIS needs ACT/360 on both legs (scale a 365-quoted fixed coupon by 365/360), the payment delay in discounting, and the live bp value of the front contract (Huggins & Schaller 2022, Ch.8).
- **Strip gross factor** for a non-IMM term: `S = (1 + R_unknown D_unknown/360) * prod_j (1 + R_j D_j/360)`, last D_j only to the term end. Accurate only if the term matches the reference quarters or forward rates are flat in the last quarter.
- If interdealer trading in a term benchmark is restricted, dealers can pile onto one side of SR1/SR3; watch Term SOFR vs futures dislocations (Huggins & Schaller 2022, Ch.3).

## Worked examples
All numbers are from the cited sources unless labelled illustrative. Reproduce them with the script's `--selftest`.
1. **Two-day compounding** (O/N 1% then 2%, ACT/365F): `((1+1%/365)(1+2%/365)-1) * 365/2 = 1.5000274%` (Darbyshire, Coding Interest Rates, c.2024, s6.3).
2. **One-week OIS breakeven** (EFFR 0.12, 0.13, 0.14 over the weekend = 3 days, 0.13, 0.10%, 7 days): product 1.0000250, breakeven 0.0000250 x 360/7 = 0.1286% (Credit Suisse, Basis Points, 18 Feb 2010).
3. **SR3 settlement check, June 2022:** 98-day reference period, 42 days at 0.51% then 56 days at 0.76%: `R = [(1+0.51%/360)^42 (1+0.76%/360)^56 - 1] * 360/98 = 0.653%`, price 99.347 (Tuckman & Serrat, 2022, s12.4).
4. **Fixing exposure table** (period 3-10 Feb 2022, USD 1mm, all rates 4.03%, notional-equivalent per fixing date; Darbyshire, Coding Interest Rates, c.2024, Table 8.4) - reproduced by the script to within about USD 1-2:
   | Method | Fixing date: exposure |
   |---|---|
   | Payment delay | 3 Feb 1,000,000; 4 Feb 1,000,112; 7 Feb 1,000,447; 8 Feb 1,000,559; 9 Feb 1,000,671 |
   | Observation shift 3 | 31 Jan 999,665; 1 Feb 999,776; 2 Feb 999,888; 3 Feb 1,000,000; 4 Feb 1,000,112 |
   | Lockout 2 | 3 Feb 1,000,000; 4 Feb 1,000,112; 7 Feb 3,001,342 (about 3x on the locked rate) |
   | Lookback 3 | 31 Jan 999,665; 1 Feb 2,998,658 (x3); 2 Feb 999,888; 3 Feb 1,000,000; 4 Feb 333,445 (/3) |
   Reading: payment delay and shift exposures are flat to a slow compounding drift; lockout and lookback create x3 and /3 spikes that only direct fixing management can offset.
5. **Cash-balance mechanics** (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022, s5.3): pay-fixed USD 100mm 1Y semi/semi at 1.0%; first 6M compounded RFR 1.1% receives USD 50,000; second 6M 0.8996% pays USD 50,200; the USD 200 gap is recouped by 0.8% interest on USD 50,000 for 6M, which is why a compounded leg needs its own forecasting-basis risk strip.
6. **Euribor-style cash hedge (contrast):** EUR 10mm 92-day loan hedges with 10mm x 92/(1mm x 90) = 10.22 contracts and nets about EUR 12,011 in every scenario (Tuckman & Serrat, 2022, Table 12.11). The RFR equivalent uses SR3-type contracts only where the loan period matches the reference quarter.
7. **Illustrative (computed with the script, not from a source):** USD 100m, 1-Dec-2026 to 4-Jan-2027, flat 3.7%, ACT/360. A 5 BD lookback equals exactly one calendar week without holidays, so each fixing is applied on the same weekday and every one-day-equivalent notional is about 1.00x (0.999-1.002x). With 25-Dec and 1-Jan as holidays the weeks stop aligning around them and a few buckets jump to about 4x and 0.33x. A 3 BD lookback misaligns every week (x3 / 1/3 spikes). So the unhedgeable residual depends on n versus the holiday calendar, not on n alone; run `--method lookback --n <n>` with the real calendar before judging.

## Signals & interpretation
- **SR1 vs SR3 spread (same dates):** no basis exists, so a persistent gap beyond the compounding term `r^2 D/(2B)` (about 3bp at 5% over a quarter) plus convexity difference (under 0.1bp at 2021-22 rates, nearer 1bp as rates approach 5% in simulation) is curve-shape or a convexity misspecification (Huggins & Schaller 2022, Ch.2 and Ch.5). If 1M-implied zeros sit 1/2 to 1/6bp above 3M-implied zeros, suspect unaccounted arithmetic-average convexity; test each contract set separately and look for turn-of-month wiggles (Deriscope, Turn-of-the-Month Effect in SOFR Curve, 18 Feb 2024).
- **Term vs OIS-implied:** the historical Term-minus-compounded-OIS gap averaged 1.5-2bp with a 95th percentile near 4bp (Jun-18 to Jan-19 sample, a calm regime), so a gap inside about 5bp is noise; beyond about 5bp it is a dislocation to explain (balance sheet, one-way futures flow) before trading it. In stress the gap widens with horizon (6M realised premium 31bp mean in Jul-07 to Dec-10).
- **Futures-forward gap:** trade or fit only if the adjustment exceeds the bid/ask: at 80bp vol, 2y is about 1.4bp but 5y about 8bp, so use unadjusted futures only inside roughly 1y of the start of the reference period.
- **Convention RV:** two exposures to the same RFR with different fixing conventions (observation shift vs lookback vs lockout) have the same expected rate, different risk; price the extra reset risk as the unhedgeable residual, not as carry.
- **Basis checks:** single-curve bootstraps mis-price RFR-vs-IBOR FRAs (a 1x7 compounded-implied 0.146% sat 14.7bp below the market FRA at 0.293%; Ametrano & Bianchetti, Multiple Interest Rate Curve Bootstrapping, SSRN 2219548, Apr 2013). Compounded ESTR is normally below 3M Euribor (bank credit), 2y ESTR vs 3M Euribor basis 13.8bp in Feb 2022 (Tuckman & Serrat, 2022, s13.6).
- **Structural SOFR vs FF:** long-end SOFR/FF is expected a few bp wider than overnight because of structural duration demand (BofA, US Rates Viewpoint, 22 Oct 2020). Cross-link [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md).

## Pitfalls
- Not standardising fixing exposures to one-day-equivalent notionals before comparing periods, books or methods.
- Using 25 per bp for a front contract mid-quarter; use the live value (section 4).
- Counting a fixing as known on its own date: SOFR/ESTR/SONIA/CORRA print the next business day; TONA has provisional and final vintages (`rate_fixings`); CORRA publishes 9:00-11:00 ET, the CORRA index 11:30 ET; Eurex FST3 final settlement is 09:00 CET (Bank of Canada; Eurex, exchange pages, excerpts).
- Day-count mix-ups across currencies: SONIA futures EDSP ACT/365F, SARON ACT/360, NOWA ACT/365 with the NIBOR fallback rebased to ACT/360, AONIA A/365F. Convert B before comparing compounded rates.
- Ticker semantics: RFR futures month code = start of reference quarter, IBOR codes = expiry month; tick sizes differ between front (0.25bp) and later months (0.5bp) for SR3, SO3 and CRA.
- Reference-period boundaries are IMM dates, not calendar quarters. Use the calendar of the index for fixing days, the payment calendar for pay dates.
- Payment delay changes discounting: with a 2-day delay on the float only, two discount factors are needed and the floating PV is not par (Huggins & Schaller 2022, Ch.8). The pure lag convexity is negligible (Henrard, OIS and Floored Compounded Instrument in HJM One-Factor Model, 3 Feb 2004).
- Book typos to avoid: the printed period DCF `d = (sum d_i)^-1` for spread compounding must be `d = sum d_i`; the printed left side of the fixing-notional identity conflicts with its divisor, so use the N_i form in section 6.
- Compounded legs and averaged legs need separate forecasting risk strips; a book netted on a single OIS curve misses compounding-basis and reset risk (Darbyshire 2022, Tables 22.4-22.5).
- Mixing 1M arithmetic and 3M compounded SOFR futures in one bootstrap produces wiggles.
- FRN near ex-dividend: if ex-div is more than one plus the shift/lookback parameter, the last fixing needed for negative accrued is not yet published, so forecast it from the curve (Darbyshire, Coding Interest Rates, c.2024, s10.14).
- Source conflicts to resolve on the trade, not assume: AONIA OIS payment lag is stated two ways in the same convention document (2 BD after maturity vs 1st day after termination); ESTR payment lag is quoted as 1 BD in one convention source and 2 in another; the CAD spot lag also conflicts. Read the trade's `swap_conventions` row.
- Exchange-spec figures (tick, size, last trade) in [references/g10_rfr_conventions.md](references/g10_rfr_conventions.md) come partly from web excerpts: verify against the primary contract specification before sizing.

## Output
Return, in this order:
1. **Method statement:** index, B, convention (delay/shift/lookback/lockout n, spread method), payment lag, calendar ids, and whether the period is partially fixed (last known fixing date).
2. **Rate table:** period compounded rate, arithmetic average, compounded-minus-average gap (bp), implied futures price, with the day-weight schedule if a weekend/holiday dominates.
3. **Fixing ladder:** one row per fixing date: status known/open, cash per bp, one-day-equivalent notional, d_own, hedge contracts (bucket / live bp value), residual after the strip.
4. **Convexity/term adjustments applied** (bp) with the model and vol, and the dislocation (bp) vs the reference (OIS-implied, SR1-vs-SR3, Term SOFR vs compounded).
5. **Flags:** convention conflicts, unverified conventions, data staleness. Hand actionable trades to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and execution questions to [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md).

## Scripts
- [`scripts/rfr_compounding.py`](scripts/rfr_compounding.py): `compound_rate`, `average_rate`, `period_rate` (plain/payment_delay, obs_shift, lookback, lockout), `fixing_ladder` (cash/bp and one-day-equivalent notional per fixing), `fixing_ladder_asof` (known vs open), `contract_bp_value` (live bp value of a compounded futures contract), `sr3_price`, `futures_convexity_bp`.
  CLI reads a canonical `rate_fixings` file: `python scripts/rfr_compounding.py --fixings <file> --index USD-SOFR --start 2026-11-02 --end 2026-12-02 --method lookback --n 5 --asof 2026-11-12 --fwd-pct 3.7`.
  `python -I scripts/rfr_compounding.py --selftest` checks the examples above, the full Table 8.4 exposure grid, the convexity table, a brute-force bump of the analytic ladder, and the front-contract bp value.

## Related skills
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market RFR, swap and futures conventions this skill relies on
- [fi-curve-construction](../fi-curve-construction/SKILL.md): bootstrapping from OIS and futures, meeting-date steps, turns
- [stir-futures-rv](../stir-futures-rv/SKILL.md): spreads, flies, packs and strips on the contracts defined here
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): model-based futures-vs-FRA/OIS adjustments
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-date path implied by futures and OIS
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): option-implied distributions on reference-period underlyings
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): why SOFR prints differ from policy rates and term benchmarks
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): RFR vs term basis swaps, SOFR-FF
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): bucketed DV01 and hedge-instrument mapping
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): roll rules and cost across reference quarters
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): holiday, month-end and turn effects in fixings
- [xccy-basis](../xccy-basis/SKILL.md): spread added to compounded RFR in cross-currency basis legs
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): write-up of actionable convention or reset-risk trades
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used here
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bill, OIS and money-market spreads.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): reserves and balance-sheet plumbing.

## References
- Darbyshire - Coding Interest Rates (companion treatise, c.2024), s6.3-6.6, 8.4, 8.8, 10.14, Table 8.4: compounding identities, fixing conventions, spread compounding, per-fixing notional exposures
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): compounded vs non-compounded leg PVs, reset risk (s24.1), RFR fixing scale (s18.2.4), cash-balance example (s5.3)
- Huggins & Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): SR3/SR1 settlement, roll rule, Term SOFR model and criticisms, strip and Term SOFR hedges
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022), Ch.12-13: futures settlement, convexity formulas, loan conventions, Euribor basis
- ISDA - Interest Rate Derivatives Definitions Matrix for Overnight Rate Compounding, Averaging and Index Methods (v1.0, 11 Jun 2021): rounding, default 5-day parameters
- ISDA - Interest Rate Derivatives Definitions FRO Mapping Tables (v3, 10 Nov 2021): G10 RFR names and mappings
- Heitfield & Park - Inferring Term Rates from SOFR Futures Prices (Federal Reserve Board, FEDS 2019-014, Feb 2019): term vs OIS premia
- Bowman - Historical Proxies for the Secured Overnight Financing Rate (FEDS Notes, 15 Jul 2019): SOFR vs EFFR
- FINCAD / Rosen - Averaged Overnight Rate Futures Convexity Adjustment (SSRN 3350745, 1 Mar 2019): averaged vs compounded adjustment
- Garcia-Lorite & Merino - Convexity adjustments a la Malliavin (2023): Hull-White overnight futures convexity
- OpenGamma / Henrard - Overnight Futures Convexity Adjustment (SSRN 3134346, Feb 2018): settlement wording
- Henrard - Overnight Indexed Swaps and Floored Compounded Instrument in HJM One-Factor Model (BIS working paper, 3 Feb 2004): payment-lag convexity, floored compounded RFR
- BSIC - Understanding Convexity Bias in STIR Futures Markets (29 Mar 2026): Ho-Lee convexity
- CME Group / Rogerson - Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures (4 Jun 2025): SR3 settlement and USD 25 per bp
- FactSet - Interest Rate Future white paper (23 Mar 2023): RFR futures tickers and settlement forms
- Deriscope / Rigopoulos - How to build a SOFR Yield Curve in Excel using QuantLib and Deriscope; Turn-of-the-Month Effect in SOFR Curve built out of 1- and 3-Month Futures (18 Feb 2024): compounding formulas, 1M vs 3M gap
- Credit Suisse / Lantz, Chang & Dorji - Basis Points: A Guide to the Front-End and Basis Swap Markets (18 Feb 2010): OIS breakeven example
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): OIS mechanics, 6s3s term risk
- Ametrano & Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping (SSRN 2219548, Apr 2013): single-curve FRA error
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024), Table 11.1 and CCBS chapters: reference rates, spread added to compounded SOFR
- BofA - US Rates Viewpoint: SOFR/FF term structure post "big bang" (22 Oct 2020): SOFR-FF term structure
- Gunstensen - MIT OpenCourseWare 18.642 Lecture 7: Linear Rates Models (26 Sep 2024): compounded SOFR identity and forward replication
- Exchange and administrator pages (excerpts, verify against primary specs): CME SOFR futures specifications; ICE Three Month SONIA futures; Eurex Three-Month Euro STR futures; JPX 3M TONA futures; Montreal Exchange CRA; Bank of Canada CORRA; SIX Swiss reference rates (SARON); Riksbank SWESTR; Norges Bank NOWA/NIBOR fallback recommendations; AFMA Interest Rate Derivative Conventions
- Tradeweb - SEF Rulebook Chapter 9, Rule 901 Swap Specifications (undated): USD and CAD OIS and single-period conventions
- BIS Quarterly Review - Ehlers & Todorov, Goodbye Libor, hello basis traders (Dec 2025): turnover shares of FRA/OIS by currency
