# G10 STIR options: markets, margining, meeting mapping and derivations

Supporting detail for [../SKILL.md](../SKILL.md). Verify every contract term against the exchange specification
through [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md) before using it in a calculation.
Where this file says "check", the term was not confirmed in the source library.

## 1. Where an option-implied policy distribution exists

| Ccy | Policy anchor / RFR | Underlying for the RND | Listed STIR options | Premium style | `r0` (no-change node) | If no usable options |
|---|---|---|---|---|---|---|
| USD | Fed target range; SOFR (also EFFR) | SR3 (compounded SOFR, IMM to IMM); SR1 (monthly average); ZQ (30d FF average) | SR3 quarterly, serial, weekly and 1Y-5Y mid-curves. The deepest G10 market | Up front, American (CME) | SOFR fixing median; SOFR−IORB basis drifts with reserves and repo; quarter-end and year-end prints in Q4/Q1 windows | n/a |
| EUR | ECB deposit rate; €STR; 3M Euribor | 3M Euribor futures; €STR futures | Euribor options and mid-curves are deep. €STR options are newer and thinner (check OI) | Futures-style (ICE, Eurex) | €STR + forward Euribor−€STR basis for Euribor options | €STR caps/floors, short-expiry swaptions |
| GBP | Bank Rate; SONIA | 3M SONIA futures | SONIA options and mid-curves | Futures-style (LIFFE heritage; check) | SONIA fixing vs Bank Rate basis | SONIA caps, swaptions |
| CAD | BoC target; CORRA | 3M CORRA futures | Listed, thin (check OI) | Check | CORRA fixing | swaptions, curve-only lattice |
| AUD | RBA cash rate; AONIA; BBSW | 90d bank bill futures (physically settled); 30d interbank cash-rate futures | Thin | Check | BBSW−OIS basis shifts the nodes | swaptions, curve-only lattice |
| NZD | OCR; BKBM | 90d bank bill futures | Thin or none | Check | BKBM−OCR basis | curve-only lattice |
| CHF | SNB policy rate; SARON | 3M SARON futures | None of note | n/a | SARON fixing | curve-only lattice |
| SEK | Riksbank policy rate; SWESTR / STIBOR | STIBOR futures | None of note | n/a | n/a | meeting-dated OIS lattice, OTC swaptions |
| NOK | Norges policy rate; NOWA / NIBOR | NIBOR futures | None of note | n/a | n/a | meeting-dated OIS lattice, OTC swaptions |
| JPY | BoJ policy rate; TONA | 3M TONA futures | Thin or none | n/a | TONA fixing; BoJ steps have been 10-25bp, so set `step_bp` to match | swaptions, curve-only lattice |

Margining facts from the sources:
- CME options on STIR futures are premium-style and American, and the premium is paid up front (Henrard,
  OpenGamma, 2012; Huggins & Schaller, 2022).
- LIFFE-heritage EUR/GBP/CHF/USD and Eurex EUR STIR options are margined futures-style. For these,
  `price = E[(K − R_θ)^+]` with no discounting, and American = European because the payoff is convex
  (Chen & Scott 1993, cited in Henrard, 2012).

## 2. Contract terms that change the computation

**SR3 options** (Huggins & Schaller, SOFR Futures and Options, 2022):
- Expiries: quarterly options on the 16 nearest quarterly months, plus 4 serials.
- Mid-curves: 1Y-5Y (5 quarterly + 4 serial), and 3M/6M/9M (nearest quarterly + 2 serial). 1Y-3Y weeklies on
  the nearest 2 Fridays.
- Strikes: 6.25bp steps within ±150bp of ATM for the first 4 quarterly and 4 serial expiries. 12.5bp steps
  elsewhere, and 25bp steps out to ±550bp.
- Size: USD 25 per bp, American exercise.
- Last trading day: the **Friday before the 3rd Wednesday** of the contract month, i.e. before the reference
  quarter starts. Eurodollar options used to trade to the Monday.
- Tick: 0.25bp if the premium is ≤ 5bp, else 0.5bp.

**SR1 options** (same source):
- Strike steps: 6.25bp within ±62.5bp, then 12.5bp within ±125bp.
- Only the nearest 4 months are listed.
- They trade through the reference month, where they become arithmetic-average American Asians. No closed form
  exists, so do not run BL with Bachelier on an in-period SR1.

**Euribor options** (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022):
- €25 per bp, with payoff `€250,000 × [K − R]^+` for a call on price.
- Margined futures-style, so DF = 1 and early exercise has no value.
- Worked example: F = −0.235%, K = −0.25%, T = 203/365, σ = 68.42bp gives a Bachelier put on the rate of
  0.1961%, i.e. €490.34 per contract as printed.

## 3. Mapping meetings to a contract

For a contract with reference window `[S, E)` and a meeting with effective date `e_m`:
```
W_m = 0                        if e_m ≥ E
W_m = (E − max(e_m, S)) / (E − S)   if e_m < E        (day count, ACT; compounding nuance < 0.1bp at low rates)
contract rate = r0 + Σ_m W_m · Δ_m           Δ_m = move at meeting m (bp)
```
- A meeting resolved **before option expiry** contributes `W_m·Δ_m` as a known shift. It creates atoms on the
  lattice; at `W_m = 1` they sit exactly on the 25bp nodes.
- A meeting **after option expiry** contributes `W_m·E[Δ_m | info at expiry]`, which is still uncertain at expiry.
  That uncertainty is the smear `s`. It grows with `W_m` and with the meeting's own uncertainty.

Illustrative example (dates computed, meeting hypothetical):
- The Dec-26 SR3 reference window is 16-Dec-2026 to 17-Mar-2027, i.e. 91 days. Its quarterly options expire
  11-Dec-2026.
- A December meeting effective before 11-Dec is resolved, with W = 1.
- A late-January meeting effective 28-Jan-2027 has W = 48/91 = 0.53. A 25bp move there shifts the contract
  13bp, and the market's uncertainty about it at expiry blurs every node.
- Use `cb_meetings.effective_date`, not the decision date. FOMC changes apply from the day after the decision.
  ECB MRO changes were decided on a Thursday and applied from the next MRO settlement the following Wednesday
  (Düring, 2021).

## 4. Derivations used in the skill

**Breeden-Litzenberger in rate space.** A rate call is `C(k) = DF ∫_k^∞ (r − k) q(r) dr`, the swaption form in
Darbyshire (2022). Differentiate twice:
```
∂C/∂k   = −DF ∫_k^∞ q(r) dr = −DF · P(r > k)
∂²C/∂k² =  DF · q(k)
```
Hence `CDF(k) = 1 + (1/DF)·∂C/∂k`, and a vertical of width Δ costs `≈ DF·Δ·P(r > k)`.

**Lattice mixture.** For `q = Σ w_n N(μ_n, s)` the call price is `Σ w_n·Bachelier(μ_n, k, s)`, which is linear in
`w`. Stack the OTM premiums with two heavily weighted rows, `Σ w = 1` and `Σ w μ = F`, and solve with
non-negative least squares. Scan `s` and keep the minimum RMSE.

**Minimum-variance lattice consistent with the curve.** Among lattice distributions with mean F, variance is
minimised by mass `p = frac((F − r0)/step)` on the upper adjacent node and `1 − p` on the lower one:
`Var_min = step²·p·(1 − p)`. Any option-implied lattice variance below it is impossible, so a negative excess
is a data or fit error.

**Model-free moments** (Bakshi, Kapadia & Madan, 2003, in rate space around F). Use rate puts P and calls C, and
divide by DF for up-front premiums:
```
μ2 = (2/DF) [∫_{-∞}^{F} P dK + ∫_{F}^{∞} C dK]
μ3 = (1/DF) [−6 ∫ (F − K) P dK + 6 ∫ (K − F) C dK]
μ4 = (1/DF) [12 ∫ (F − K)² P dK + 12 ∫ (K − F)² C dK]
```
Omitting DF on up-front premiums makes a Gaussian RND show excess kurtosis `3(e^{rT} − 1)`.

**Noise floor** (illustrative arithmetic):
- Half-tick premium noise is 0.125bp, independent across strikes.
- A 1-2-1 fly then has noise `√6 × 0.125 = 0.31bp`. On a 25bp payoff that is 1.2pp of cell probability.
- A 6.25bp vertical has noise `√2 × 0.125 = 0.18bp`. On 6.25bp that is 2.8pp of digital probability.

**Transaction cost in probability units:** cost in bp ÷ payoff width in bp.
- A 25bp 1-2-1 at one tick (0.25bp) per lot costs 4 × 0.25 = 1bp, i.e. 4pp.

**OTC fallback, swaptions and caps:**
- A payer swaption is `A·E^A[(S − K)^+]`, where A is the annuity. So `q^A(K) = (1/A)·∂²Payer/∂K²`, the density
  under the annuity measure. It is close to the forward-measure density for short tails.
- For caplets, use the caplet's payment DF and accrual fraction in place of A.
- From `vol_surface` normal vols, build prices with Bachelier using A in place of DF, then apply the same pipeline.
- The result is the RND of a term or swap rate, not of a quarter average. Map it to policy nodes only through
  an explicit path assumption (BofA, US Vol Primer, Mar 2024; J.P. Morgan, Is bank convexity hedging lying in
  wait?, May 2019).
