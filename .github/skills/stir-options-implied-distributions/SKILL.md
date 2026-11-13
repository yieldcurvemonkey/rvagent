---
name: stir-options-implied-distributions
description: Extract the risk-neutral distribution of a future policy/RFR rate from listed STIR options (SOFR SR3, Euribor, SONIA, CORRA, midcurves), or caps and short-expiry swaptions where none trade. Breeden-Litzenberger with normal-vol smoothing, a mixture of normals on the 25bp meeting lattice, meeting-outcome probabilities, moments, skew, tail mass, mode vs priced mean, and a check against the OIS/futures path. Use when asked what options price for the Fed/ECB/BoE/BoC path beyond the mean, the probability of a hike, cut or no change by a meeting, whether pricing is bimodal, landing zones or pins, recession or hike-tail odds, skew on STIR options, or whether a call fly, put fly, vertical, digital, 1x2 or ladder is cheap vs your scenario odds. Trigger words - Breeden-Litzenberger, risk-neutral density, RND, implied PDF/CDF, implied distribution, SOFR options, SR3 options, Euribor options, SONIA options, mid-curves, FedWatch vs options, hike/cut probability, 25bp lattice, tail probability, option-implied odds.
---

# STIR option-implied distributions

The OIS/futures strip prices only the **mean** of each future fixing. Options on STIR futures price the whole
distribution. Put-call parity pins the option-implied mean to the futures rate, so options and the curve never
disagree on the mean. The RV is in the **shape**: how probability splits between policy outcomes on the 25bp
lattice, how fat each tail is, and where the mode sits relative to the priced mean. When pricing is bimodal,
"what's priced, is almost the least likely path" (JWS Macro, Global Rates Update #7, Jul 2026). Linear trades at
the mean then lose in both modes, and pins, flies, verticals and 1x2s are the cheaper expressions. The edge is
your view against the risk-neutral density (RND), or the RND against its own history or another market. It is
never a parity arbitrage.

## When to use
- "What do SOFR / SONIA / Euribor options say about a hike by December?" You need probabilities per number of
  25bp moves, not just the bp priced.
- The priced mean sits between lattice nodes (e.g. 31bp priced). Is that one hike for sure, or 0-or-2?
- Tail questions: P(SOFR < 2.75% by June) as a recession proxy, P(Bank Rate back to 5.25%) (25-30% in SONIA options, JWS Macro,
  Global Rates Outlook #5, May 2026), hike-tail cost.
- Skew questions: are puts on price (rate payers, hike side) rich vs calls? Does skew agree with the OIS direction?
- Before you structure a STIR option trade (call fly on a pin, vertical, 1x2, ladder), find the probability the
  premium implies and compare it with your scenario odds.
- Cross-checking curve-implied meeting probabilities from [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Option premiums by strike, one expiry | `opt_quotes` (`premium_px`, `bid_px`/`ask_px`, `underlying_px`, `oi_cnt`, `nvol_bp`) | one `date` + `snap` (prefer `settle`); ≥ 1y daily for percentiles | premium in price points = % of rate |
| Option terms | `opt_static` (`strike_px`, `option_right`, `expiry_date`, `exercise_style`, `premium_style`, `is_midcurve`, `underlying_id`) | static | right is on the **price** |
| Underlying future and reference window | `stir_quotes`, `fut_static` (`ref_start_date`, `ref_end_date`, `ref_method`, `ref_index_id`) | same snap as options | rate = 100 − price |
| Meeting calendar | `cb_meetings` (`meeting_date`, `effective_date`) | all meetings to option expiry + reference window | effective date drives day weights |
| Current RFR fixing and policy rate | `rate_fixings` | daily, ≥ 60 business days | sets the no-change node and the RFR-policy basis |
| Discount factor from today (premium payment) to option expiry (premium-up-front options only) | `curve_zero` (OIS) | same date | DF = 1 for futures-style margined options |
| OTC fallback (no listed options) | `vol_surface` (`product` = `capfloor` / `swaption`, `strike_offset_bp`, `nvol_bp`, `atm_fwd_pct`) | same date | short expiry, short tail |
| Your scenario odds (optional) | none; ask the user | per lattice node | used only for the edge column |

Read `opt_static.premium_style` (`upfront` or `futures_style`). When it is null, default by exchange: CME = premium
paid up front (American); ICE and Eurex STIR options = futures-style margined (no discounting, no early exercise). Confirm in
[fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md) and the per-market table in
[references/g10-stir-option-markets.md](references/g10-stir-option-markets.md). If an input is missing, ask
for it or hand off to the `rv-data-engineer` agent ([data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)).
Never invent premiums or fill strikes.

## Method

**1. Pick the contract and expiry that isolate the meetings you care about.**
- An option on future *i* settles to the futures price at option expiry. That price is the market's expectation,
  at expiry, of the compounded or averaged RFR over `[ref_start, ref_end)`. It is not the policy rate after a
  given meeting.
- Quarterly SR3 options stop trading on the Friday before the 3rd Wednesday of the contract month, i.e. before
  the reference quarter starts (Huggins & Schaller, SOFR Futures and Options, 2022). So:
  - meetings whose effective date falls **before** option expiry are resolved. They create lattice atoms.
  - meetings **after** expiry but inside the reference quarter enter at day weight
    `W_m = (ref_end − effective_m) / (ref_end − ref_start)` and stay unresolved. They smear each atom.
    A dated example is in [references/g10-stir-option-markets.md](references/g10-stir-option-markets.md) §3.
- For a quarterly option every resolved meeting has weight 1. The surface therefore identifies only the
  distribution of the **total move count N** up to expiry, not the per-meeting path. To split timing, use
  serial expiries on earlier contracts, or the OIS step path for the means.
- **No-change node** `r0` = what the contract settles at if policy never moves. Take the current RFR fixing (or
  the policy rate plus the trailing 20-business-day median RFR−policy basis), and add any known turn or
  quarter-end effect inside the window. Nodes are `r0 + n × 25bp`. Change the step only where the central bank's
  usual increment differs (e.g. 10bp or 15bp moves near zero).

**2. Clean the quotes.**
- Use one snap for options and future. `|RND mean − futures rate| > 0.5bp` after fitting means a snap, DF or
  parity problem.
- Use **OTM only**. Calls on price are OTM below the futures rate, puts on price above it. ITM American premiums
  carry early-exercise value. For CME SOFR options that value is small but real when deep ITM (Quantitative
  Finance Stack Exchange, SOFR futures options, 2023).
- Drop premiums below 0.5bp (two ticks at the 0.25bp small-premium tick). These are cabinet marks or model
  settles and inflate wing vol. In a test with ±0.125bp noise, keeping min-tick wings inflated the RND standard
  deviation by about 20%.
- Drop `data_ok = false` rows and strikes with `oi_cnt < 100`. Where both rights trade at a strike, check
  parity: `C_px − P_px = DF·(F_px − K_px)` within one tick.

**3. Convert to rate space.** `k = 100 − K_px`, rate forward `F = 100 − F_px`.
- A **call on price is a put on the rate** (receiver). A **put on price is a call on the rate** (payer).
- Premium in price points equals premium in % of rate. Normal vol of the rate in bp = price vol in points × 100.

**4. Price with Bachelier (normal model; no shift needed at negative rates).**
```
d = (F − k) / (σ·√T)        σ in % per year (= nvol_bp / 100), T = ACT/365 to expiry
C(k) = DF · [ (F − k)·Φ(d) + σ·√T·φ(d) ]        rate call = put on price
P(k) = C(k) − DF·(F − k)                          rate put  = call on price
```
- Futures-style margined options (Euribor on ICE and Eurex; SONIA on ICE, confirm): DF = 1 and American = European. Under daily
  settlement there is no intrinsic value to capture early (Henrard, OpenGamma, 2012; Tuckman & Serrat, 2022).
- Premium paid up front (CME SR3): DF = OIS discount factor from premium payment (trade date) to option expiry,
  when the exercise payoff is realised.
  If you omit it, the density mass is DF instead of 1, and model-free moments show spurious excess kurtosis
  `3·(e^{rT} − 1)`.

**5. Breeden-Litzenberger density (model-free shape).**
```
q(k)     = (1/DF) · ∂²C/∂k²                 risk-neutral density of the futures rate at expiry
P(r > k) = −(1/DF) · ∂C/∂k                  so CDF(k) = 1 + (1/DF)·∂C/∂k
discrete: q(K) ≈ [C(K−δ) − 2C(K) + C(K+δ)] / (DF·δ²)      (Darbyshire, 2022)
```
- **Never difference raw quotes.** With ±0.125bp (half-tick) premium noise, a 1-2-1 fly has noise
  `√6 × 0.125 = 0.31bp`. Over a 25bp cell that is ±1.2pp of probability. Over 6.25bp strikes it is ±5pp per bin.
- Default pipeline (the bundled script): invert each OTM premium to a normal vol, then fit a cubic smoothing
  spline in strike with an RMS tolerance of **0.5bp vol**. Hold vol flat beyond the quoted strikes, so the tails
  are normal. Re-price calls on a 0.25bp grid and take second differences. Clip negative density and renormalise.
- Diagnostics to report every time:
  - raw mass, which should be 1 ± 0.5% (a gap points to a DF error).
  - negative mass.
  - **mass outside the quoted strikes.** Above 10%, the tails are an assumption, not a price.
  - **smoothing sensitivity:** refit at 0.5× and 2× the tolerance. A cell that moves more than 3pp is not robust.
- Bias vs noise, measured on the self-test's synthetic cases with ±0.125bp noise added:
  - At a 0.5bp tolerance, a normal RND is recovered to about 1pp per 25bp cell (typical error 0.6pp).
  - The same tolerance flattens a lumpy five-node RND by 4-6pp per cell.
  - Use BL for moments, CDF and tails. Use step 6 for outcome probabilities.

**6. Mixture of normals on the lattice (meeting-outcome probabilities).**
```
q(r) = Σ_n w_n · N(r; r0 + n·25bp, s)      w_n ≥ 0, Σ w_n = 1, Σ w_n·μ_n = F
C(k) = Σ_n w_n · Bachelier_call(μ_n, k, s)  premiums are linear in w, so solve by NNLS
```
- The common width `s` (bp at expiry) is the smear from unresolved meetings plus basis noise. Choose it by
  minimum RMSE over 2-30bp. J.P. Morgan decomposes the SR3 option-implied density the same way: a weighted mix
  of pre-specified, fixed-width normals with means 25bp apart, weights fitted to option prices (J.P. Morgan, Cross
  currency basis 2H25 Outlook, Jun 2025).
- On the self-test's five-node case it recovers weights to within 2-3pp typically (about 5pp on the worst of five
  noise draws) under half-tick noise when the true `s` ≤ 10bp.
- Identification fails as the smear widens: max weight error is about 3pp at s = 12.5bp, 6pp at 15bp and 10pp at
  20bp. The fit also under-estimates `s`. If the fitted `s` exceeds 12bp, merge adjacent nodes into 50bp buckets
  or report BL cells instead of weights.
- A weight change smaller than its bootstrap sigma is noise. Re-fit with premiums jittered ±½ tick about 200
  times to get that sigma.

**7. Shape metrics** (rate space, bp unless stated):
- mean − F, which must be ≈ 0.
- standard deviation, skew, excess kurtosis.
- mode, median, and `mean − median`. Positive means the upper (hike) tail is fatter.
- p05, p25, p75, p95.
- `P(r < X)` and `P(r > Y)` at the user's thresholds.
- 25-delta risk reversal in normal vol, as rate-call vol minus rate-put vol. Positive = payer/hike skew = puts on
  price bid.
- Model-free cross-check of the moments: Bakshi-Kapadia-Madan (2003) integrals, each divided by DF.

**8. Compare with the OIS/futures path.**
- The curve alone supports only the **minimum-variance lattice**. Let `p = frac((F − r0)/25bp)`. Put p on the
  upper adjacent node and 1−p on the lower one. Then `Var_min = 25²·p·(1−p)` bp². This is what FedWatch-style
  probabilities assume.
- Excess dispersion: with mixture weights, `Var_lattice = Σ w_n·(μ_n − F)²` and
  `excess = Var_lattice − Var_min ≥ 0`. A negative value is a data or fit error. Report `√excess` in bp:
  dispersion beyond what the curve's two-point story needs. At ≥ 25bp the market prices a fork of at least one
  full move, not a coin-flip on timing.
- Read curve probabilities with care. Reading 10bp priced as 40% of a 25bp move is "just a loose manner of
  speaking". 50% at each of two successive meetings usually means one hike with uncertain timing, not a 25%
  chance of two hikes (Düring, Fixed Income Trading and Risk Management, 2021). The options on the later contract tell you which:
  compare the mass at N = 1 with the mass at N = 2.
- The RND mean is a **futures** rate. Before comparing it with OIS forwards beyond the whites, remove the
  convexity bias ([stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md)).

**9. Price cells and digitals, then compute the edge.**
- A 25bp **fly** centred on a node (1-2-1 at node−25, node, node+25; calls or puts give the same payoff by
  parity) costs about `DF × 25bp × P(cell)` for a lattice-like RND.
- A **vertical** of width Δ costs about `DF × Δ × P(r beyond the strikes)`, the digital approximation.
- Breakeven probability = cost / (DF × payoff width).
- For any other structure (1x2, ladder, condor), compare cost with `DF × ∫ payoff(r)·q(r) dr` under the RND, and
  with the same integral under your view distribution (J.P. Morgan, An option by any other name, Feb 2017).
- Edge = your probability − breakeven. Act only when `|edge| ≥ 10pp` for a cell or ≥ 5pp for a tail digital,
  and the edge is ≥ 3× the noise floor from step 5.
- Price the structure from **listed bid/ask**, never from the smoothed fit.
- Costs: a 1-2-1 is 4 lots. One tick (0.25bp) per lot is 1bp, or 4pp of probability on a 25bp payoff.
  A 6.25bp-wide cell scaled to the same 25bp max payoff takes 16 lots (4× a 6.25bp 1-2-1) and costs 16pp. Do not trade cells narrower than 25bp.

## Worked examples

**A. Lattice mixture on Dec-25 SR3 options** (J.P. Morgan, Cross currency basis 2H25 Outlook, 5 Jun 2025).
Weights as of 2 Jun 2025, read from the chart:

| Node (%) | 4.75 | 4.50 | 4.25 | 4.00 | 3.75 | 3.50 | 3.25 |
|---|---|---|---|---|---|---|---|
| Weight | ≈0 | 0.06 | 0.28 | 0.07 | 0.36 | ≈0 | 0.24 |

- Mean = Σ w·μ = 3.87% (3.83% after renormalising the 1.01 read-off total).
- The node nearest the mean (4.00) holds only 7%. Mass splits across three modes 50bp apart (4.25: 28%,
  3.75: 36%, 3.25: 24%), with near-empty nodes between them (4.00: 7%, 3.50: ≈0). The bimodal flag below fires.
- J.P. Morgan concluded that policy uncertainty was significant. In practice, a receiver at the priced mean is
  the wrong instrument. The right one is a structure that pays in the mode you believe in.

**B. Pins richest despite hikes priced** (JWS Macro, Global Rates Update #7, 19 Jul 2026).
- Dec-26 SOFR options: the "unchanged" pin was the richest landing zone even with 31bp of hikes priced to
  December. 50bp priced can mean 50% × 0 + 50% × 100bp.
- SONIA: the 96.25 pin was the most popular and richest. Euribor: most weight on one more hike.
- Read: an RND with a fat no-change mode plus a hike tail, so the mean is not a scenario anyone holds.

**C. One hike modal, consistent with OIS** (J.P. Morgan, US IRD: Near, far, wherever yields are, 2 Oct 2026).
- BL on Dec-26 SR3 calls across strikes put one hike by year-end as the modal Fed outcome after the
  distribution "shifted back towards the left somewhat and narrowed".
- OIS: Dec-26 FOMC forward 4.14%, Mar-27 4.41%. With the USD overnight rate at 3.88% (Citi Research, Japan Rates
  Weekly, 2 Oct 2026), the Dec mean is 26bp above today.
- Illustrative arithmetic: the minimum-variance lattice gives p = 0.04, i.e. 96% one hike and 4% two hikes. Any
  RND mass at zero or two hikes beyond that is dispersion the curve cannot show.

**D. Tail probability as a recession proxy** (JWS Macro, USD Rates & Fed outlook #1, 21 Aug 2025).
- SOFR options implied P(SOFR < 2.75% by next June) = 22%. The author treated this as the market-implied
  recession probability: "marginally overpriced. But its not an option I would sell!" The tail carries insurance
  premium, so fair-but-rich is not a sell signal on its own.
- BofA did the same with swaptions: hard landing c.20-25%, taken from the CDF of 10y SOFR rates implied by the
  option smile to end-2024 (BofA, 10y rates and the Monty Hall problem, Aug 2024).

**E. Selling rich hike skew with a costless 1x2** (Citi Research, Global Macro Trade Ideas Radar, 13 Aug 2026).
- Trade: Dec-26 SR3 96.50/96.125 1x2 put spread (buy 1 put at 96.50, sell 2 at 96.125) for a 2.5bp credit, with
  the future near 96.50 (3.50%).
- In rate space this is long a 3.50% payer and short two 3.875% payers.
- Payoff: max 37.5 + 2.5 = 40bp at 3.875%. Breakeven 96.125 − 0.40 = 95.725, i.e. 4.275%, a 77bp sell-off.
  Losses only beyond that.
- Rationale: rich vol and put skew, with a "terminal cushion" of about three hikes judged overdone.
- RND check: the trade sells `P(r > 4.275%)` weighted by the open-ended payoff. Run it only if your probability of
  that tail is clearly below the RND's.

**F. Normal-approximation probability from a breakeven** (BofA, US Vol Primer, Mar 2024).
- A costless 1y10y payer ladder breakeven 127bp out at 110bp normal vol (σ√T = 110bp at T = 1y) gives z = 1.155, so P = 12.4% of a sell-off
  beyond breakeven.
- Use the BL CDF instead whenever skew is material. The normal approximation misstates the tail probability by
  the skew.

**G. Textbook pricing check** (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022).
- Inputs: Sep-22 Euribor futures 100.235 (rate −0.235%), call on price = put on rate at −0.25%, T = 203/365,
  σ = 68.42bp.
- Bachelier put = 0.1961%, about €490 per contract at €25 per bp (€490.34 as printed).
- No DF (futures-style). The bundled self-test reproduces 0.1961.

## Signals & interpretation
- **Bimodal flag.** Two nodes each ≥ 20%, ≥ 50bp apart, with a node between them < 10% (example A).
  - The priced path is a low-probability outcome, so avoid linear trades at the mean.
  - If you agree with the fork, own the cheaper mode with a call or put fly, or a vertical.
  - If you think one outcome dominates, compare the pin fly's breakeven with your odds. Pins are often the
    richest cell (example B).
- **Tail mass.** P(|r − F| ≥ 50bp), or P(r < X) at a user threshold.
  - Top decile of its 1y history within the same regime: sell wings (1x2, ladder), sized for the tail.
  - Bottom decile: buy wings.
  - Never treat a tail as "wrong" only because it exceeds your forecast. The excess is insurance premium
    (example D).
- **Skew vs direction.** `mean − median` > +2bp, or 25d RR z > +1.5 on 1y, means the hike tail is rich.
  - If OIS prices cuts while skew bids hikes, hedging demand is the likely cause.
  - Sell that skew with a 1x2 or ladder (example E; Barclays faded excess EUR hike odds with a 1y1y 1x1x1 payer
    ladder, Global Rates Weekly, 2 Oct 2026), or buy the opposite tail cheaply.
  - Persistent tail demand keeps skew elevated "even if rates remain within their recent range" (Morgan Stanley,
    Investors Are Paying for Protection Against 6% Rates, Jul 2026).
- **Excess dispersion** ≥ 25bp near a meeting means the market prices a fork. Straddles on that expiry are
  fairly priced only if you also expect a decisive outcome.
- **Straddle breakevens vs nodes.** When an expiry straddles a near-binary meeting, check the ATM straddle
  breakevens against the adjacent outcomes. Sep-26 SR3 96.1875 straddle at 10.75bp: breakevens 96.08 / 96.295
  vs a hike settle of about 96.09 and no change at about 96.345, so the straddle prices the fork almost exactly
  (Citi Markets, SOFR/CBOT Vol EOD, 21 Aug 2026). It is cheap only if you expect more than one move.
- **Curve vs options consistency.** A futures fly or calendar equals its expected settlement. Its "median path"
  version differs by `Σ w_i (mean_i − median_i)` across legs.
  - That gap retires leg by leg as each option expiry passes.
  - It is a risk premium carrying tail risk, not an arbitrage.
  - Express it with wing options delta-hedged with futures ([stir-futures-rv](../stir-futures-rv/SKILL.md)).
- **Cross-market.** The same bp priced over the same horizon can hide different distributions, e.g. a Fed fork vs
  ECB "one more then stop". Compare node probabilities across USD/EUR/GBP before a cross-market policy spread.
- **Confirmation.** Open interest clustering at strikes within ±25bp of the mode, block trades in the same
  structure, and a consistent move in serial vs quarterly expiries.

## Pitfalls
- **Price vs rate inversion.** A call on price is a rate receiver. Mixing them flips skew and tails.
- **The reference window is not the meeting.** A Dec contract's RND covers an average that can include the
  following Jan and Mar meeting days at partial weight. Map nodes with step 1 before calling anything "the December outcome".
- **Expiry before the reference period.** SR3 options never become Asian, but SR1 options trade through their
  month as arithmetic American Asians, which have no closed form. Do not run BL on Bachelier for an in-period SR1
  (Huggins & Schaller, 2022).
- **Mid-curve options.** These give the distribution of a later contract's futures price at an early expiry. That
  is an expectation, so unresolved meetings widen the smear. Expect a larger `s`, and do not read lattice weights
  if the fitted `s` > 12bp.
- **Margining and DF.** Wrong DF scales the mass and distorts kurtosis. ITM American quotes add early-exercise
  value. Use OTM only.
- **Settlement marks in the wings.** Exchange settles for far-OTM strikes are model marks. Low-premium quotes
  inflate wing vol, so filter them (step 2) and report mass outside strikes.
- **Smoothing bias.** Heavy smoothing erases modes. Light smoothing turns noise into fake modes. Always show
  smoothing sensitivity, and use the lattice mixture for probabilities.
- **Basis and turns.**
  - RFR minus policy rate drifts with reserves and repo ([stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md)).
  - Euribor options embed the Euribor−€STR basis and its volatility. Shift `r0` by the forward basis
    ([spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md)).
  - Year-end turns sit inside Q4 windows.
- **Joint distributions.** Per-contract RNDs do not give the distribution of a spread or fly. That needs a
  coupling: comonotone (one policy factor) and independent meetings bracket it.
- **Risk-neutral ≠ forecast.** Persistent richness of a tail is premium. "Selling high-strike swaptions is better
  viewed as a volatility trade than a macro view" (Morgan Stanley, Jul 2026).
- **Thin markets.** CAD, AUD, NZD, CHF, SEK, NOK and JPY listed STIR options are thin or absent.
  - Use cap/floor or short-expiry swaption smiles from `vol_surface`. That gives the RND of a term or swap rate,
    not a quarter average.
  - Or fall back to the curve-only minimum-variance lattice and say so. Never fill strikes.

## Output
1. **Header:** market, contract, option expiry and T, snap, margining and DF, F, `r0` with its basis assumption,
   meetings resolved before expiry, and meetings smeared with their day weights.
2. **Lattice table:** `n_moves, level_pct, prob_bl, prob_mixture, prob_min_var_curve, view_prob, edge_pp,
   cell_fly_cost_bp, breakeven_prob`, plus `√excess` dispersion in bp.
3. **Shape:** mean − F, sd, skew, excess kurtosis, mode, median, mean − median, p05/p95, user tail
   probabilities, 25d RR, and each of these as a 1y percentile.
4. **Diagnostics:** quotes used, raw mass, negative mass, mass outside strikes, smoothing sensitivity, mixture
   `s` and RMSE, parity breaches. Mark the read **not robust** if mass outside > 10%, sensitivity > 3pp, or
   `|mean − F|` > 0.5bp.
5. **Chart:** node probability bars (BL vs mixture vs curve minimum-variance) with the CDF overlaid, plus a time
   series of the main node probabilities
   ([eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md)).
6. **Storage and hand-off:**
   - Store node probabilities in `events_probs` with `venue = implied_options` and `linked_meeting_date`.
   - Hand any structure with an edge to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), with listed
     bid/ask cost, max payoff, breakeven rates and breakeven probability.

## Scripts
- [`scripts/implied_dist.py`](scripts/implied_dist.py): takes canonical `opt_quotes` + `opt_static` for one
  underlying and date. It converts price-space quotes to rate space, keeps OTM quotes, and runs the BL density
  (normal-vol smoothing spline, diagnostics, smoothing sensitivity) and the lattice mixture (NNLS, smear by
  RMSE). It prints moments, `P(rate < X)` and node probabilities, with optional CSV output. Run
  `python scripts/implied_dist.py --help`.
- Example: `python scripts/implied_dist.py --opt-quotes opt_quotes.parquet --opt-static opt_static.parquet --date 2026-11-10 --underlying FUT:SR3:2026-12 --base-rate-pct 3.88 --df 0.997 --thresholds 3.5 4.5`.
- `--selftest` checks the following, and fails if any of them breaks:
  - the Bachelier price against the Tuckman textbook value.
  - recovery of a known normal RND: mass, mean, sd, skew, cells, CDF.
  - recovery of a known five-node lattice mixture: weights and smear, both clean and with half-tick noise.
  - an end-to-end CLI run.
- The script does not build the curve minimum-variance lattice, the edge column or listed structure costs. Add
  those from method steps 8-9.

## Related skills
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-dated OIS path, the means this skill decomposes
- [stir-futures-rv](../stir-futures-rv/SKILL.md): futures flies and calendars, option-implied asymmetry of linear structures
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): reference-period mechanics and day weights
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures vs OIS mean before comparing paths
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): contract specs, margining, meeting effective dates
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): implied vs realised STIR vol, listed vs OTC vol
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): risk reversals, ladders, 1x2s, tail hedges
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): mid-curve vs white option packages
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): mid-curve options and the correlation they embed
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): compare RND node odds with prediction markets
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): turn your scenario tree into `view_prob`
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): percentiles of tail mass and skew
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): trade note hand-off

## References
- J.P. Morgan - US Interest Rate Derivatives: Near, far, wherever yields are (I. Ozil, C. Hayward, M. Alexeev, E. Alptuna, 2 Oct 2026): Breeden-Litzenberger on Dec-26 SR3 options mapped to Fed outcome probabilities, read alongside OIS meeting forwards
- J.P. Morgan - Cross currency basis 2H25 Outlook (F. Diamond, K. Gupta, T. Yamawaki, I. Ozil, B. Jarman, 5 Jun 2025): mixture of fixed-width normals on a 25bp lattice fitted to Dec-25 SR3 options, with weights
- D. Huggins & C. Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): SR3/SR1 option specs, expiry before the reference quarter, American exercise, Asian behaviour in period
- B. Tuckman & A. Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): futures-style Euribor options, the Bachelier formula without DF, worked example
- M. Henrard - Interest Rate Futures and their Options: Some Pricing Approaches (OpenGamma Quantitative Research, v1.3, 2012): premium-style vs margined options, no early exercise for margined options
- J.H.M. Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022): density as the second strike derivative, finite-difference estimate, normal model, implied-vol inversion
- BofA Global Research - US Vol Primer: A Guide for the Perplexed (B. Braizinha, 11 Mar 2024): PDF/CDF from the smile (App. C), ladder breakeven to probability
- BofA Securities - US Rates Watch: 10y rates and the Monty Hall problem (B. Braizinha, 6 Aug 2024): scenario likelihoods from option-implied CDFs
- JWS Macro - Global Rates Update #7: Same North Star, Worse Weather (19 Jul 2026): bimodal pricing, priced path as the least likely path, SOFR/SONIA/Euribor pins
- JWS Macro - Global Rates Outlook #5: Price Vs. Quantity (10 May 2026): SONIA options read, i.e. probability of Bank Rate at 5.25% and put/call skew by expiry
- JWS Macro - USD Rates & Fed outlook #1: Summer 2025 (21 Aug 2025): option-implied P(SOFR < 2.75%) as a recession proxy
- Citi Research - Global Macro Trade Ideas Radar (L. Costa et al., 13 Aug 2026): costless SR3 1x2 put spread monetising rich put skew
- Citi Research - Japan Rates Weekly: JGBs look resilient as yen weakens (T. Fujiki, 2 Oct 2026): hike probability from meeting spreads, overnight levels
- A. Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): reading continuous pricing as probabilities and the two-meeting caveat
- Morgan Stanley - Investors Are Paying for Protection Against 6% Rates (S. Zhou, M. Hornbach et al., 2 Jul 2026): tail-strike demand keeps skew elevated; selling tails is a vol trade
- J.P. Morgan - An option by any other name: Sourcing cheap convexity in the long end (J. Younger, D. Sarkar, M. Salem, 3 Feb 2017): expected payoff of a structure under the option-implied terminal distribution
- J.P. Morgan - Interest Rate Derivatives: Is bank convexity hedging lying in wait? (J. Younger et al., 31 May 2019): policy distribution from OIS plus caps when listed options are not used
- Quantitative Finance Stack Exchange - "SOFR futures options" (2023): small early-exercise premium in American SOFR options; treat them as European OTM
- Citi Markets (US Macro Sales) - SOFR/CBOT Vol EOD (G. Compton, 21 Aug 2026): SR3 straddle breakevens mapped to the hike and no-change settles
- Barclays Research - Global Rates Weekly: The urgency question (2 Oct 2026): EUR 1y1y 1x1x1 payer ladder to fade excess hike probability
- D. Breeden & R. Litzenberger - Prices of State-Contingent Claims Implicit in Option Prices (Journal of Business, 1978) (external): the second-derivative result
- G. Bakshi, N. Kapadia & D. Madan - Stock Return Characteristics, Skew Laws, and the Differential Pricing of Individual Equity Options (Review of Financial Studies, 2003) (external): model-free moments
