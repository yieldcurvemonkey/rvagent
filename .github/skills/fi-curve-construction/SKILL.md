---
name: fi-curve-construction
description: 'Builds and validates G10 OIS/RFR discount and forecast curves. Covers par-swap bootstrap and numerical fit, meeting-date step curves (central-bank effective dates) fitted to SR1/SR3 futures and OIS, STIR futures strips, turns (month/quarter/year-end), interpolation (log-linear, mixed, log-cubic, monotone), node and knot placement, convexity-adjusted futures inputs, single-RFR vs legacy IBOR and CSA multi-curve, diagnostics and curve persistence. Use when asked to build, bootstrap, fit, rebuild or sanity-check a swap, OIS, SOFR, ESTR, SONIA, TONA, SARON, CORRA curve; "step curve", "meeting-dated OIS", "forward overnight rate", "discount factors", "zero curve", "which interpolation", "turn of year", "IMM nodes", "futures vs swaps in the curve", "wiggly or kinked forwards", "pillars", "knots", "stub", "FOMC/ECB/MPC step", "curve does not reprice", or before any forward, carry, roll-down or key-rate calculation that needs a curve. Reading the implied policy path: stir-policy-pricing-whats-priced-in.'
---

# OIS/RFR curve construction

Every RV number in this agent (forwards, carry, roll-down, spreads, key-rate risk) is read off a curve, and most "rich/cheap"
signals on a curve are artefacts of how it was built: interpolation, a missing turn, an unadjusted futures price, or a stale pillar.
This skill builds one curve per currency from liquid instruments, makes it reprice what you will trade and hedge, and
proves it is clean before anything is read off it. Post-IBOR, the single overnight (RFR) curve is the forecast curve and the
default discount curve, so the job is dominated by the short end (central-bank steps, turns, futures) and by interpolation beyond ~2-3y.

## When to use
- Building or rebuilding a SOFR / ESTR / SONIA / TONA / SARON / CORRA / AUD-NZD-Scandi swap or OIS curve from quotes.
- Reading a policy path or "what is priced in" off OIS and STIR futures: you need a meeting-date step curve first.
- A forward, 1y1y, 5y5y, roll-down or key-rate number looks odd: check the curve before believing the trade.
- Choosing interpolation, nodes, knots, number of futures in the strip, or how to treat month-/quarter-/year-end turns.
- Deciding whether a futures-vs-swap or spot-vs-forward-OIS gap is RV or a construction error.
- Legacy tenor curves (EURIBOR, STIBOR, NIBOR, BBSW, BKBM) and CSA/xccy discounting: see Method step 9.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Spot-starting par OIS/swap rates, 1W..50Y | `curve_par` (`start=0D`) | one snap per build, same snap for every row | `par_rate_pct` mid; keep `bid_rate_pct`/`ask_rate_pct` for the fit tolerance |
| STIR futures (SR1/SR3 and local equivalents) | `stir_quotes` | settle snap for history, one snap per build | `price_px` = 100 - `rate_pct`; check the identity |
| Overnight fixings (in-period contracts, stubs) | `rate_fixings` | last ~3 months | `fixing_date` vs `pub_ts_utc`: a fixing is usable only after publication |
| Central-bank dates | `cb_meetings` | 12-24 months ahead | use `effective_date` when present, else meeting date (+1 day for FOMC, see Method 6) |
| Conventions, calendars | `swap_conventions`, `calendars`, `fut_static` | static | day count, payment lag, fixing lag, reference-period rules: see [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md) |
| Tenor/CCP/xccy basis | `basis_swaps`, `ccp_basis` | per snap | only for legacy tenor curves and non-RFR discounting |
| Output | `curve_zero` | every node, plus `build_id` | discount factors are primary, zero rates derived |

If an input is missing (no fixings for an in-period contract, no snap time, unknown calendar), ask for it or hand off to the
data adapter. Never invent values. Rates in percent, spreads and residuals in bp.

## Method

### 1. Fix the purpose and the design bar
Priority order (Darbyshire, Coding Interest Rates, c.2024): (1) accurate, practical delta risk, (2) usable by every desk,
(3) accurate pricing curve, (4) speed. A curve that reprices every input but gives unhedgeable risk is a bad trading curve:
"'perfect' curves do not make money, but 'accurate enough' curves that allow robust hedging do". Checklist (Darbyshire,
Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022): synchronous with its instruments, reprices mids, fast,
transparent enough to hand-edit in illiquid markets (NOK, NZD), hedge-aware, minimal internal volatility, valid history,
stable when rebuilt a week later. Use exact fit (N pillars reprice N instruments) for trading; best-fit parametric
(Nelson-Siegel/Svensson) is for smoothing and bond RV: "0.25bp can make the difference" in liquid swap markets (Ametrano & Bianchetti, 2013).

### 2. Identities and conventions (state them every time)
- Discount factor `Df(t) = exp(-∫0..t f)`; cc zero `z(t) = -ln Df(t)/t` (stored ACT/365F in `curve_zero`); the three are equivalent
  and convention-free. Par rate depends on frequency, day count and calendar.
- Simple forward over `[d0,d1]`: `F = (Df(d0)/Df(d1) - 1)/τ(d0,d1)`, τ in the index day count (ACT/360 USD, EUR, CHF; ACT/365F GBP, JPY).
- Par rate of a spot-start OIS: `R = (1 - Df(T)) / Σ τ_j Df(t_j)`. Single payment if maturity ≤ 12M: `1 = (1 + R τ) Df(T)`; longer swaps pay
  annually, counted back from maturity (18M pays at 6M and 18M).
- Overnight chain: `Df_i = Df_{i-1}/(1 + r_i d_i/N)`, `d_i` = calendar days the rate applies (3 on a Friday), `N` = 360 or 365 per the index; compounded period rate
  `(Df_start/Df_end - 1)/τ` is valid only for ACT/360 or ACT/365F (a fixed-denominator actual count), not 30/360.
- Shape (Ilmanen, Understanding the Yield Curve Pt 1, May 1995): upward curve gives par < zero < forward; inverted reverses; the
  forward curve magnifies slope changes, so forward kinks are where construction error shows first.
- Sign/unit: rates and quotes in percent, spreads/steps/residuals in bp, `step_bp = rate_k - rate_{k-1}` (positive = hike priced), futures
  rate = 100 - price. "Receive fixed" = long duration.

### 3. Pick the instruments (liquid, non-overlapping, mostly)
| Zone | Use | Why |
|---|---|---|
| < ~3M | In-period fixing plus the first futures; exclude the raw O/N fixing from the fit (its value date is out of sync with the quotes) | stub computed from known fixings, not treated as a forward |
| 3M to ~2-3y | 1M futures (SR1) for month-end and meeting effects, 3M futures (SR3, 2nd to ~9th-12th) for the quarterly shape; OIS dated to meetings if liquid | only electronic instruments that see FOMC jumps; swaps up to 3y are best priced off the futures-derived curve (Clarus, CME-LCH Basis: Convexity in Eurodollar Futures, Jul 2015) |
| > 3y | Annual par OIS: 3Y, 4Y, 5Y, 7Y, 10Y, 12Y, 15Y, 20Y, 25Y, 30Y, 40Y, 50Y | futures beyond ~3-5y are largely implied; thinner nodes outward |

Defaults and reasons:
- Number of IMM futures: 8 (small currencies) or 12 (liquid). Avoid 6, 7, 10, 11, 14: with 10 the strip ends at 2.75y just after a roll and
  decays to 2.5y, so par swaps added beyond it become leveraged (e.g. 2.75y x 0.25y) and change daily; 8 always ends just past 2y, 12 just past 3y (Darbyshire, PTIRD, 2022).
- Roll the strip when the front contract fixes, or earlier if its liquidity fades (Ametrano & Bianchetti, 2013); when rolling a position roll 2nd into 3rd, not front into back, because the in-period contract is
  partly fixed with decaying vol (Huggins & Schaller, SOFR Futures and Options, 2022).
- Keep excluded liquid instruments out of the fit but monitor them: their error (RMSE, max) is the honest out-of-sample test (Ametrano, Bertocchi, Mazzocchi, Advanced EONIA Curve Calibration, Dec 2016).
- Never mix 1M (arithmetic average) and 3M (compounded) SOFR futures naively: a mixed curve showed a 0.081-0.099% bumpy first year where 1M-only and 3M-only curves were smooth; SR1 sat 0.17-0.5bp above SR3 (uncorrected averaging) (Deriscope, SOFR curve in Excel, Feb 2024).
- Par swaps from the interbank market, not IMM swaps, are the observable benchmark inputs; keep few par tenors, add skews for the rest in a second layer (PTIRD 2022).

Per-market input sets, step-date rules and snap times: [references/g10-curve-inputs.md](references/g10-curve-inputs.md).

### 4. Pre-process the quotes
1. **Snap and units.** One snap per build; settle and close differ by 0.2-0.9bp on STIR futures. Percent vs decimal and price vs rate: reject, do not rescale.
2. **Futures to forwards.** `forward = 100 - price - CA`: the futures rate exceeds the forward by the convexity adjustment (CA), which applies to 3M contracts and grows with maturity and vol:
   ~1bp (2020), 2bp (2021), 3.3bp (2022), 5bp (2023), 7.3bp (2024) for GBP at end-2017 with HW 65bp/3% (Henrard, Overnight Futures: Convexity Adjustment, Feb 2018); negligible on 1M contracts (0-0.07bp) (FINCAD, Convexity Adjustment of Averaged Overnight Rate Futures, Mar 2019).
   Separately, the *averaging-vs-compounding nonlinearity* affects SR1 only (well under 1bp at current levels; SR3 compounds the same overnight rate and needs none) (Huggins & Schaller 2022).
   Models and sizing: [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md); formulas and sizes: [references/instrument-formulas.md](references/instrument-formulas.md).
   OIS bootstrapping itself needs no CA (forwards are in the natural measure) and the 2-day payment lag is "for all practical purposes negligible" (Henrard, 2004).
3. **In-period futures.** Use known fixings for elapsed days and solve the remaining rate so the contract reprices:
   `R_unknown = [(R·D/36000 + 1)/Π_known(1 + SOFR_i d_i/36000) - 1] · 36000/D_unknown` (rates in percent, `D` contract days, `D_unknown` days still to fix). This is the ACT/360 *compounded* rate of the unfixed window, not the flat overnight rate: convert (about `(1 + r/360)^D_unknown = 1 + R_unknown·D_unknown/360`) before feeding a step curve, the gap is ~`R²·D_unknown/720` (2.5bp at 5%, 72 days). No cash-deposit stub is needed (unlike LIBOR strips).
4. **Strip turns before smoothing** and reinsert them afterwards (Method 7). A quote that crosses a turn date carries the turn.
5. **Wide bid/ask or a stale quote** on close pillars causes oscillation ("greater adjustments on DFs between successive maturities means greater oscillations"): drop or down-weight, do not smooth over it.

### 5. Solve: bootstrap or fit
- **Bootstrap** (exact, node by node) when specific instruments must reprice. Annual par swaps (accrual 1): `Df_1 = 1/(1+p_1)`, `Df_i = (1 - p_i Σ_{j<i} Df_j)/(1 + p_i)`.
  With accruals: `Df_n = (1 - R_n Σ_{t<n} Df_t A_t)/(1 + R_n A_n)`. With sparse tenors the intermediate coupon DFs need the interpolator, so each maturity is a 1-D root solve
  (`scripts/bootstrap.py`).
- **Fit** (all node DFs at once, `min (r-S)ᵀW(r-S)`) for mixed SR1+SR3+OIS inputs, dual-curve or interdependent sets, or over-specified inputs. FOMC-step curves from mixed SR1/SR3 are
  "an exercise in fitting rather than bootstrapping" (Huggins & Schaller 2022): there are more steps than SR3s per year but too few to reprice every SR1.
- **Specification.** n nodes vs m instruments: n = m exactly determined; n < m over-determined (usable, objective > 0); n > m under-determined, which oscillates (O/N swings of about +/-40% on an unregularised SONIA step curve).
  Regularise with visible low-weight calibrating instruments, not a hidden ridge: zero-priced butterflies between policy periods at weight ~1e-8 to 1e-4 vs 1 for market quotes
  ("setting butterfly prices to zero promotes minimum curvature"); the regularisers then appear as risk buckets you can ignore (Darbyshire, CIR, c.2024).
- **Algorithm.** Gauss-Newton `J W Jᵀ δ = -J W (r - S)` started from yesterday's curve converges in single or low double-digit iterations; Levenberg-Marquardt (`+λI`, start λ0 = 1000, quarter on success, double on failure)
  only when the start is poor; gradient descent is for teaching. Compute the Jacobian once per build and reuse it for risk.
- **Acceptance (house defaults, tune per market).** Exact fit: every input reprices to within 1e-6bp. Fit: residual per instrument within half the bid/ask; liquid SR1/SR3 within ~1bp. Larger on the first six SR1 means a data/date/convention error, not an opportunity.

### 6. Meeting-date step curve (short end, RFR)
Overnight RFRs track the policy rate, so the forward overnight curve is piecewise-constant with jumps at central-bank effective dates. Bonds-and-swaps curves that avoid jumps cannot see policy.
1. **Nodes = effective dates**, not announcement dates ("aligned with the dates where new policy rates become effective", Darbyshire, CIR). FOMC: decision day + 1 (a 25bp hike announced 4-May-2022 lifts the SR1 for
   May by 25 × 27/31 = 21.8bp, Huggins & Schaller 2022). ECB: the Wednesday after the Thursday meeting for €STR. BoE: SONIA OIS pays off MPC publication dates (Deriscope, Yield Curve Building ... GBP Sonia, Feb 2024). JPY: start of the reserve period.
   Meeting calendars are published well ahead (about 1y for most banks; take them from `cb_meetings`, not from memory) but contracts beyond ~6m are thin, so Heitfield-Park allow no jumps past 6 months; beyond ~2y revert to smooth interpolation (step at the front, spline at the back "works fairly well", MIT 18.642, Sep 2024).
2. **Model** (Heitfield & Park, Inferring Term Rates from SOFR Futures Prices, Fed FEDS 2019-014, Feb 2019): `f(t;θ) = θ_0 + Σ_k θ_k 1{t > M_k}`: `θ_0` = forward for tomorrow (the level), `θ_k` = the jump at the k-th effective date `M_k` after the as-of date; the rate level after meeting k is `r_k = θ_0 + Σ_{i≤k} θ_i`.
   Daily compounding on business days with Friday accruing 3 days. With `f` in percent: SR1 price = `100 - (1/N_m) Σ f` over calendar days (weekends = prior business day); SR3 price = `100 - (36000/N_q)[Π(1 + f_t d_t/36000) - 1]`.
3. **Estimator.** `min sqrt(Σ w_m (P¹_m - P̂¹_m)² + Σ w_q (P³_q - P̂³_q)²) + λ·sqrt(Σ_k θ_k²)` over the first 13 SR1 and 5 SR3 (CME Term SOFR set) or 7 SR1 + 3 SR3 (Heitfield-Park), equal weights.
   The penalty is on jump sizes `θ_k = r_k - r_{k-1}` (CME writes the same thing as a first difference of levels); CME's `λ = 1/sqrt(number of scheduled meetings)` (≈ 0.33 for 9) applies in that root-sum-square form; use a tiny λ only to resolve under-identified jumps.
   Alternative: a butterfly penalty on levels, `φ Σ_j (2r_j - r_{j-1} - r_{j+1})²` added to the sum of squared errors; raising it is "necessarily subjective". The CME-style λ adds ~0.5bp to 6M Term SOFR (27-Jan-22) and may bias it up.
   `scripts/bootstrap.py step` uses the sum-of-squares form `Σ resid_bp² + lam·Σ jump_bp²`: its `lam` is a regulariser, not comparable with CME's λ.
4. **Constraints.** Policy gradualism: when 2+ meetings fall inside one contract window, choose the path minimising the largest single jump. No jumps >6 months ahead (thin contracts).
5. **Mixing OIS.** Meeting-dated OIS (one per month, mapping m-th OIS to m-th meeting, to ~6M) bootstraps recursively: `(1 + R1 (T1-t0)/D) = Π(1 + n_l r0/D) · Π(1 + n_l r1/D)`; with the binomial approximation
   `r1 = D[((1+R1(T1-t0)/D)/(1+r0/D)^{t1-t0})^{1/(T1-t1)} - 1]` (Lehman Brothers, The Short-End of the Curve, Jul 2007). Add the daily funding spread to model unsecured vs secured jointly.
   Where a spot OIS overlaps an ECB-dated OIS, use a **forward stub** from the spot OIS maturity to the first meeting rather than the overlapping spot OIS, or its information is lost (Ametrano et al. 2016).
6. **Under-identified steps**: use `scripts/bootstrap.py step` with a tiny λ, or add zero-priced flies at tiny weight.
7. **Output the policy path** as a table: per meeting `rate`, `step_bp`, cumulative bp vs stub (OIS up to but not including the next meeting). `step_bp/25` is the implied hike probability for a 25bp move
   (RBA Apr 2007: +11bp to May = 44%, Lehman 2007). Footnote: RFR-based pricing is not the policy rate (€STR, SONIA differ), and read effective vs meeting dates.

### 7. Turns and funding seasonals
- Turns are fundamental, date-specific jumps in the overnight rate (month-end, quarter-end, year-end; JPY 1-April; Fed tax/settlement days). Their effect is confined to a few fixings, so "much less significance for RFR curves than for IBOR" (PTIRD 2022), but they bias short OIS and month-end futures.
- **Size by looking at current repo tightness**, not a fixed history: the spike scales with base tightness (Fed, What Happens on Quarter-Ends in the Repo Market, Jun 2025): SOFR-ON RRP +7bp at Mar 2023 quarter-end, up to ~+25bp at Sep and year-end 2024; ordinary base spread 3-5bp.
  Year-end turn premium is "customarily priced but rarely realised" (Lehman 2007); severity year-end > quarter-end > month-end (leverage-ratio snapshots).
- **Extract**: model forward O/N basis per quarter plus month-end and quarter-end turns jointly and fit monthly vs quarterly SOFR futures spreads (J.P. Morgan, What does the SRF mean for swap spreads?, Jul 2019).
- **Implement on local interpolators** (log-linear/flat-forward): nodes on both sides of the date, one calibration parameter per turn (Darbyshire's Version B, illustrative size: 1d swap from 1 Dec = 0, spread(1d swap 30 Dec, 1d swap 31 Dec) = -50bp, 1d swap from 1 Jan = 0; the sign is market-specific: repo-based RFRs such as SOFR spike up at period-ends, while SONIA showed small negative premia, so take sign and size from the data). Not with cubic splines (they oscillate).
  On a spline: build a log-linear turn curve and price on `composite(turn_curve, spline_curve)` solved jointly (Darbyshire, CIR, c.2024). Read turn risk net across the left/right pair.
- **Tenor (IBOR) curves**: turn can fade before expiry (SEK 3M STIBOR year-end turns); model a linearly fading turn. Turn-of-year in EUR 1M quotes: 2007 +64bp, 2008 +22bp; amplitude scales with the single crossing O/N weight (1M ~1/22 of ON, 3M ~1/3 of 1M); negligible at 6M/12M (Ametrano & Bianchetti 2013).
- **Jump removal before calibration** (Ametrano et al. 2016): build the O/N curve on dense liquid quotes, size an outlier segment `J = (F_orig - F_interp) τ(t1,t2)/τ_J`, remove it as a multiplicative DF factor after the date, iterate over dates. USD FF month-ends are negative: reverse the sign.
- Never infer policy from a quote that crosses a turn; strip the turn first. Month-end moves in SOFR are mostly +1-2bp but not consistent; 0.5bp month-end jumps did not remove the humps in a 1M+3M SOFR build (Deriscope 2024).

### 8. Interpolation, nodes, knots
| Zone | Scheme | Reason |
|---|---|---|
| Dense short end, to the last meeting-dated or IMM instrument (~2-3y) | log-linear DF (flat overnight forwards), nodes at effective dates and/or IMM dates | local, stable, steps = policy; one bump moves only neighbouring forwards |
| Sparse long end (par tenors every 2-10y) | log-cubic or Hyman monotone-cubic on log DF, strategic knots at IMM dates, first knot = last log-linear node | log-linear gives sawtooth forwards when pillars are sparse |
| Anywhere | never linear on DF ("extremely poor") or linear on zero (fails translate invariance; "not recommended for any purpose") | |

- Smooth zeros hide forward oscillations of tens of bp in sparse sections (13-14y, 16-19y... with pillars 3-10, 12, 15, 20, 25, 30, 35, 40, 50, 60y): always judge the curve on forwards (Ametrano & Bianchetti 2013).
- Local (log-linear) vs global (spline): local keeps risk where the instrument is; global is smoother but one input moves every forward and creates spurious partials (a 10y bump shows 10y risk on a 6y swap). Mixed interpolation is "equal to log-linear on short-end errors"; monotone cubic everywhere gave higher errors on every excluded instrument (Ametrano et al. 2016).
- Knots must be **static** strategic IMM dates, not rolling par maturities: rolling knots drift forwards by ~0.25bp day to day with unchanged rates, a systematic P&L (PTIRD 2022). Each spline interval needs at least one node (Schoenberg-Whitney); with `n+4` knots (ends repeated) a cubic needs `n-2` nodes.
- Spot-vs-meeting-dated overlap and instruments between knots depend on the functional form; a risk model must use the same form as the curve model (see [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md)).
- More detail, B-spline rules, shift/translate/roll operations: [references/interpolation-solver-turns.md](references/interpolation-solver-turns.md).

### 9. Multi-curve (legacy tenors, CSA, xccy)
- **RFR currencies (USD, EUR, GBP, JPY, CHF, CAD):** one RFR curve is forecast and discount; the basis effects of the IBOR era vanish ("the use of a single RFR curve in a currency negates any of these basis effects", Darbyshire 2022). Legacy tenor curves that still matter: EURIBOR 3M/6M, STIBOR, NIBOR, BBSW, BKBM.
- **Recipe** (Ametrano & Bianchetti 2013): (1) one discount curve from collateral-rate instruments (OIS); (2) one forwarding curve per tenor from instruments homogeneous in that tenor; (3) forwards from the tenor curve, DFs from the discount curve; (4) hedge with vanillas from the same sets.
  Discount curve is exogenous: self-discounting a forward curve misprices non-inputs by up to a couple of bp.
- **Two-curve shortcut** when tenor basis swaps are illiquid: define adjusted forwards `L'` from swap rates alone, `Σ L'(s)d(s) + (1+L'(t))d(t) = 1 + x(t)Σ d(s)`, project with `L'` and discount both legs on RFR DFs;
  "no need to know the basis swap spreads" if the tenor swaps are fair vs the RFR OIS (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022). Case: 2y €STR vs 3M Euribor basis 13.8bp, so both legs of a 2y fixed vs 3M Euribor are worth 100.281, not par.
- **Disentangling shortcut** (Quantifi, c.2023): fixed-vs-tenor swap + tenor-vs-OIS basis swap = synthetic fixed-vs-OIS swap, so a dual-curve problem reduces to a single-curve bootstrap if both legs are liquid. Where several tenor curves interlock (AUD has four) solve globally instead.
- A change of discounting regime (e.g. FF to SOFR) reprices options through annuities, not forwards (ATM forwards moved < 0.1bp) (Citi Research, US Rates Vol Lab, Mar 2019). For EUR/GBP a term-repo spread curve over the RFR OIS is an estimate, not an observable (Credit Suisse, Interaction Between Repo and IRS, Sep 2021).
- Discounting follows collateral: the cash CSA currency's OIS curve; non-standard or multi-currency CSAs turn discounting risk into xccy basis risk: [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md), [xccy-basis](../xccy-basis/SKILL.md), tenor basis: [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md).
- CCP basis: LCH is the reference curve for EUR; other CCPs trade above LCH (CME/LCH 10Y 0.35bp, Eurex/LCH 10Y 2.7bp in the source example): [spread-ccp-basis](../spread-ccp-basis/SKILL.md).

### 10. Operate it
- **Rebuild fast, solve slow.** Solve fully in the background and warm-start; between solves update `R_new = R_old + J ΔR̂` using the stored Jacobian (shifts ~1/100 bp); a full build is a few ms, fast layer microseconds (Burgess, Electronic Rates Markets & Low Latency IRS Calculations, May 2022).
- **Translate, don't rebuild, for next-day opening curves** (hold forwards constant, rebase DFs): rebuilding from yesterday's inputs injects spurious roll-down and noise into carry-vs-market P&L. Static roll-down needs no recalibration.
- **Persist** nodes, interpolation, spline knots/endpoints, conventions, input instrument set, snap and timestamps, a `build_id`. Without knots a log-cubic curve silently rebuilds as log-linear and misprices its own inputs.
- **Date arithmetic** is "the source of many (all?) errors" in swap valuation: pin evaluation date, spot lag, calendar, modifier, stub rule; null stubs (≤ 1 business day after adjustment) must be removed. Fixings and curve must share one holiday calendar.

## Worked example
**1. Annual bootstrap with published answers.** USD swaps 5-Jun-2020, par 1y 0.307%, 2y 0.299%, 3y 0.346% (30/360 annual): `Df_1 = 1/1.00307 = 0.996939`;
`Df_2 = (1 - 0.00299 × 0.996939)/1.00299 = 0.994047`; `Df_3 = (1 - 0.00346 × (0.996939 + 0.994047))/1.00346 = 0.989687`; forwards `f(1,2) = 0.291%`, `f(2,3) = 0.441%` (Duering, Fixed Income Trading and Risk Management, Wiley, 2021).
The upward curve gives par < zero < forward: 3y par 0.346% against a 2y-to-3y forward of 0.441%. Reproduced by `scripts/bootstrap.py --selftest`.

**2. Step-curve sensitivity (FOMC hike hedges).** Hike of 25bp effective 5-May-2022: SR1 May = 25 × 27/31 = 21.8bp; the SR3 whose reference quarter is 16-Mar to 15-Jun-2022 (91 days, 41 after the hike) moves 25 × 41/91 ≈ 11.3bp (Huggins & Schaller 2022 give 11.3bp).
The standard hedge of 3 + 3 SR1 (two consecutive months) per 10 SR3 is therefore not meeting-neutral when the meeting is off-centre: recompute from days-after-meeting fractions (a May hike gives 3.1 May + 2.9 April SR1 per 10 SR3 in the source). `--selftest` reproduces both.

**3. Strip to IMM OIS (CME method).** April 2025, 91-day periods, prices M5 95.895, U5 96.290, Z5 96.605, H6 96.815, M6 96.940, U6 96.985, Z6 96.965, H7 96.910: `Df_i = 1/(1 + (100-P_i) d_i/36000)`, cumulative DFs 0.989730 ... 0.935249,
discounted float 0.0647505, discounted accrual 699.926, fixed = 23.310/699.926 = **3.3304%**; bumping every future 1bp gives 3.3204% (CME Group, Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures, Jun 2025).

**4. Spot-vs-forward OIS consistency (GBP).** A MPC-dated step curve built from a 2.9275% stub and 7 forward OIS (21-Nov-2022) implied overnight 2.9248% to 14-Dec-2022 and 3.5029% from 15-Dec (+57.8bp December hike) and reproduced spot OIS within 0.74bp (0.12bp at 11m, market 4.2569%) (Deriscope 2024). More cases (SOFR 14-May-21, SOFR 25-Feb-22 bootstrap-vs-fit errors, RBA 2007, ECB 2024 regularised flies, a 13-knot RFR curve under three interpolators): [references/worked-examples.md](references/worked-examples.md).

## Signals & interpretation
- **Curve is a measuring instrument first.** A rich/cheap read of < ~1bp on a swap or future is inside construction noise; before trading it, rebuild with the alternative interpolator and with/without the instrument. Model uncertainty is greatest at local maxima/minima
  and the midpoint of convex or concave sections between knots: do not call those points rich or cheap (PTIRD 2022).
- **Spot vs forward OIS (< 1y):** fair rate equals the simple forward, so implied-spot minus market-spot is a screen. Gaps within ~1bp are noise; forward-start OIS trading above spot on an upward implied path is expected. Require persistence over several snaps before calling RV (liquidity and stale feeds).
- **Futures vs curve residuals:** first ~6 SR1/SR3 within ~1bp; contracts 7-13 can carry 3-6 bp residuals (less liquid) without meaning anything (Huggins & Schaller 2022). Persistent residuals on liquid contracts: check convexity, snap, in-period handling first.
- **Futures-implied vs OIS-implied term rates:** Term SOFR step model minus FF OIS averaged 1.6-1.7bp (sd 1.4-1.6bp), >90% of days within 5bp (Jun 2018-Jan 2019); futures-based terms carry a horizon-growing risk premium (FF futures vs realised compounded EFFR: 1M +1.3bp, 3M +4.4bp, 6M +10.5bp full sample) (Heitfield & Park 2019). A step at a date where no meeting exists is a turn or an artefact.
- **Implied jump at an IMM date** in the overnight curve is expected when futures override cash; it causes P&L noise at the roll (Clarus, Mechanics of FRA Risks, Sep 2018). Roll over several sessions rather than one.
- **Policy-path RV:** `step_bp / move_size` = implied probability; compare with surveys/other curves only after convexity, turn and term-premium caveats. Forwards are means, not modes (a lognormal mean exceeds the mode by `e^{1.5σ²}`), so they embed skew and gamma value (PTIRD 2022).
- **Size meeting trades by CB01** (bump of the step at a meeting), not DV01: the AUD 1M OIS DV01 overstated meeting risk by 244% (Lehman 2007).

## Pitfalls
- **Interpolating the wrong quantity.** Linear on DF/zero yields sawtooth FRA curves; smooth zeros "give a false impression". Plot instantaneous or ~250-business-day forward overnights; they are the most severe smoothness indicator.
- **Steps on the wrong date.** Meeting/announcement vs effective date moves the jump by one or more days and mis-weights the days-after-meeting fraction in every SR1/SR3 that contains it (FOMC +1 day, ECB Wednesday, JPY reserve start, BoE same day).
- **Compounding vs averaging.** SR1 is a simple calendar-day average, SR3 and OIS compound; the gap is ~0.1bp at near-zero rates and ~1bp near 5% for 1M, up to ~3bp SR1-SR3 over a quarter at constant 5% SOFR (Huggins & Schaller 2022). Do not compound IBOR curve values as overnight rates.
- **In-period and fixing handling.** Mixed realised/projected periods are unique to RFR curves; past-start contracts need fixings (a missing fixing must raise, not default); fixings are usable only after publication.
- **Futures code semantics.** IBOR contracts expire at the start of the accrual period they fix; RFR contracts name the month the reference quarter starts but expire at its end, a quarter later: mixing the two conventions shifts dates by a quarter. AUD and NZD bank-bill futures are yield-quoted; CAD futures use a 365 base.
- **Over-fitting a thin futures strip.** Fixing every SR1 with free overnight forwards is under-determined; steps at meetings plus a smoothness penalty reduce ~200 free parameters to ~10. Reject fitted curves whose steps land on non-meeting dates without a turn.
- **Rolling knots / rolling nodes** produce daily forward drift (~0.25bp) and fake carry; keep knots static.
- **Self-discounting forward curves, exogenous basis ignored.** Non-input swaps are mispriced by up to a couple of bp; check by repricing a long forward-start swap against the quote.
- **Risk model ≠ curve model.** A log-cubic pricing curve hedged with a log-linear risk model shows zero risk-model P&L yet loses when 2y and 3y fall together (unreliability €1,328 vs €1 with the matching model on a €300mm 4.25y payer, PTIRD 2022). Risk on DFs is not hedgeable: map to calibrating instruments through the inverse Jacobian.
- **Futures in a curve imply a term-structure model** (usually 1F Gaussian HJM) through the CA (Henrard, My Future Is Not Convex, May 2012); a residual-implied CA also absorbs the future/cash basis, and Ho-Lee over-corrects beyond ~2y (BSIC, Understanding Convexity Bias in STIR Futures, Mar 2026).
- **Curves differ by purpose.** The USD Treasury par curve is anchored to GC repo and fitted in yield space; do not use it for discounting and do not mix with the OIS curve without stating the spread: [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md).
- **Opening curves rebuilt from yesterday's inputs** inject spurious roll-down; translate instead.
- **Pre-meeting stub is nearly unhedgeable.** A FRA fixing 4-Sep-2018 overlaps the Sep future by 86%, but one fixing 25-Sep-2018 (FOMC 26-Sep) overlaps the Dec future by only 9%, leaving a 91% stub with no clean futures hedge; do not let delta jump the day before a meeting, and undersize a front future covering extra meetings (Clarus, Mechanics of FRA Risks, Sep 2018).
- **Unit/snap hygiene.** Percent vs decimal, price vs rate, settle vs close snaps, exchange vs federal holiday calendar (the exchange can be closed on Good Friday and open on Columbus/Veterans Day): quarantine implausible snapshots, return NaN rather than "decode" a bad price.
- **Stale conventions.** FOMC/ECB dates, curve snap times (London 4pm, NY 3pm, Tokyo 3pm, Sydney/Auckland 4:30pm; SEK/DKK 4:15pm CET) and index definitions change; track them (Deutsche Bank DBIQ Interest Rate Curve Creation Process, Feb 2023).

## Output
1. `curve_zero` rows: `date, snap, curve_id, node_date, tenor, discount_factor, zero_rate_pct, interpolation, build_id`, with knots/endpoints for splines recorded in the build metadata.
2. **Build report** per curve: input list (instrument, quote, bid/ask, used/excluded, CA applied bp, turn removed bp), per-instrument residual in bp (inputs and held-out liquid instruments), solver (algorithm, iterations, objective), interpolation by zone, regularisation weights.
3. **Policy path table** (step curves): `effective_date, rate_pct, step_bp, cum_bp_vs_stub, implied_prob_25bp`, stub rate stated as "OIS to next meeting, excluding it".
4. **Diagnostics**: 1d/overnight forward plot (no sawtooth, no unexplained step), spot-vs-forward OIS gap (bp), futures-vs-curve residuals, locality bump test (+0.1bp at one pillar moves only adjacent forwards), rebuild-next-day stability.
5. **Flags**: any interpolation-dependent conclusion ("rich/cheap < 1bp or at a knot midpoint"), any turn or CA assumption, any missing fixing.
6. Hand-off: forwards and risk to [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md), [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md), [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md); policy path to [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md).

## Scripts
- [`scripts/bootstrap.py`](scripts/bootstrap.py): (a) `par`: bootstrap `curve_par` rows (spot-start OIS, `0D`) to a log-linear DF curve and write `curve_zero`-shaped nodes; sparse tenors OK; any of ACT/360, ACT/365F, 30/360.
  (b) `step`: fit a meeting-date step curve (business-day compounding, Friday = 3 days) to OIS, SR1 and SR3 quotes with a jump penalty; prints residuals in bp; `--fixings` is required when a contract period began before the as-of date (a missing fixing raises). (c) `strip_ois_rate`: futures strip to IMM-dated OIS rate. No holiday calendar or payment lag (stated in the docstring). `par` builds a spot-start curve (`--start-date` = T+n date, DF = 1 there); NaN quotes and duplicate tenors raise, they are never filled.
  `python scripts/bootstrap.py --help`; `--selftest` checks published DFs and the IMM OIS rate, a par round trip incl. an 18M front stub, the 21.8bp/11.3bp hike sensitivities, the in-period stub formula, the jump penalty, rejection of bad input and recovery of a known step path.

## Related skills
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market RFR, day counts, calendars, payment lags, futures reference periods; curve-snap times.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): par vs zero risk, Jacobian transforms, CB01 and bucketing on the curve built here.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): collateral discounting, multi-CSA, CTD optionality.
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures-to-forward CA models and sizing.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-date probabilities and G10 policy-path RV from the step curve.
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): compounded RFR mechanics, reference periods, fixing ladders.
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md), [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): bills and Treasury/swap-spread consumers of the OIS curve.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): futures spreads/flies vs the curve; [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): why turns spike.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): month-/quarter-/year-end turn statistics.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md), [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md), [xccy-basis](../xccy-basis/SKILL.md): basis inputs for non-RFR and cross-currency curves.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md), [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md), [curve-term-structure-models](../curve-term-structure-models/SKILL.md), [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): consumers of the curve.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md), [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): `curve_par`, `stir_quotes`, `curve_zero` schemas; snaps, stale data.

## References
- Huggins & Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): FOMC step curves, SR1/SR3 settlement and stub formulas, fit vs bootstrap, Term SOFR mechanics, meeting-neutral hedges. Also Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): discount-function criteria.
- Heitfield & Park - Inferring Term Rates from SOFR Futures Prices (Federal Reserve Board FEDS 2019-014, Feb 2019): step-curve estimator, futures pricing equations, term-rate formula, futures-vs-OIS gaps.
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): curve design, log-linear vs log-cubic, knot and node rules, IMM strip length, turns, layered curvesets, risk-model matching.
- Darbyshire - Coding Interest Rates (1st ed., c.2024): numerical solver (GN/LM), regularisation by low-weight instruments, turn implementations, ECB effective-date step curve, curve operations.
- Ametrano & Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping But Were Afraid To Ask (SSRN, Apr 2013): multi-curve recipe, interpolation failure modes, turn-of-year, instrument selection, validation.
- Ametrano, Bertocchi & Mazzocchi - Advanced EONIA Curve Calibration (QuantLib User Meeting, Dec 2016): jump removal, forward stub, mixed interpolation.
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): OIS bootstrap, flat forwards vs splines, two-curve method, SOFR/SARON curve shapes, partial PV01s from the fitted curve.
- Lehman Brothers - The Short-End of the Curve (Chris Pulman, Jul 2007): meeting-date OIS bootstrap, CB01 risk, funding seasonals, RBA example. Credit Suisse - Basis Points: A Guide to the Front-End and Basis Swap Markets (Feb 2010): OIS breakeven formula, EFFR/LIBOR seasonals.
- CME Group - Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures (Jun 2025): strip-to-OIS bootstrap with numbers; SOFR Discounting Transition Process for Cleared Swaps (Jun 2020): transition curve recipe.
- Deriscope - Yield Curve Building in Excel with Central Bank Meeting Dates ... GBP Sonia case (Feb 2024); How to build a SOFR Yield Curve in Excel (Feb 2024); Turn-of-the-Month Effect in SOFR Curve (Feb 2024): MPC step settings, spot-vs-forward check, SOFR recipes, oscillation and transient-jump diagnosis.
- Duering - Fixed Income Trading and Risk Management (Wiley, 2021): representations, bootstrap tables, weekend compounding, NS/NSS/splines, composite curves. Coleman - A Guide to Duration, DV01 and Yield Curve Risk Transformations (2011): piecewise-flat forwards, form dependence of risk.
- Henrard (OpenGamma) - Overnight Futures: Convexity Adjustment (Feb 2018); My Future Is Not Convex (May 2012); Interest Rate Futures and their Options (Feb 2012); OIS and Floored Compounded Instrument in HJM One-Factor Model (BIS, 2004): CA sizes, futures-in-curve framework, payment-lag convexity.
- FINCAD - Averaged Overnight Rate Futures: Convexity Adjustment (Rosen, Mar 2019); FactSet - Interest Rate Future (white paper, Mar 2023): 1M vs 3M CA, RFR futures settlement and code semantics.
- BSIC - Understanding Convexity Bias in STIR Futures Markets (Mar 2026); Quantitative Finance Stack Exchange threads on STIR convexity adjustment and RFR OIS bootstrapping: implied-convexity calibration, no CA in OIS bootstrap.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): deposit/swap bootstrap, DF interpolation, stringing, value basis.
- Ilmanen (Salomon Brothers) - Understanding the Yield Curve, Parts 1-2 (May-Jun 1995): par/spot/forward algebra and ordering. West - Interest Rate Derivatives lecture notes (Financial Modelling Agency, Dec 2010): raw interpolation benchmark, HW calibration.
- Quantifi - Mastering Interest Rate Curve Construction (whitepaper, c.2023): bootstrap vs global solve, accruing-future calibration.
- Fed Board FEDS Notes - What Happens on Quarter-Ends in the Repo Market (Jun 2025); J.P. Morgan - What does the SRF mean for swap spreads? (Jul 2019): turn magnitudes and extraction. Fleckenstein & Longstaff - Treasury Richness (Journal of Finance, 2023): SOFR OIS discount-curve conventions and pre-2017 backfill.
- J.P. Morgan - The new and improved Treasury par curve model (Jul 2018) and The (par) curves they are a-changin' (Jul 2024): spline par-curve fit quality, knot selection, overfitting test.
- Credit Suisse (Stathakopoulos) - The Interaction Between Repo and Interest Rate Swaps (ICMA workshop, Sep 2021); Citi Research - US Rates Vol Lab: Vol cycle, steepeners, and SOFR (Mar 2019): discounting regimes, term-repo curve, discounting-switch effects.
- Clarus Financial Technology - CME-LCH Basis: Convexity in Eurodollar Futures (Jul 2015); Mechanics of FRA Risks (Sep 2018); The IMM Roll for Swaps (Mar 2015): futures/swap crossover, IMM-node jump, roll effects.
- Deutsche Bank - DBIQ Interest Rate Curve Creation Process (Feb 2023): G10 curve inputs and snap times. Citi Markets - G10 What's Priced In (Aug 2026): policy-path table format and snapshots.
- MIT OpenCourseWare 18.642 - Lecture 7: Linear Rates Models (Sep 2024); Burgess - Electronic Rates Markets & Low Latency Interest Rate Swap Calculations (SSRN, May 2022): step-then-spline hybrid, fast Jacobian rebuild.
- Hagan & West - Interpolation Methods for Curve Construction (Applied Mathematical Finance, 2006) (external): monotone convex and forward-curve quality criteria.
