# Exposure, CVA and capital: formulas and worked tables

Detail for [SKILL.md](../SKILL.md). Main source: Darbyshire, *Pricing and Trading Interest Rate Derivatives* (3rd
ed., 2022), s.5.3, s.17.2. The money figures are £ in the book's examples.

## Credit exposure decomposition (s.5.3.1)

`CE_α = RC_mtm + C_lag,α + C_tran,α + RC_risk,α`, a VaR-like figure at confidence `1 − α`:

| Term | Collateralised | Uncollateralised |
|---|---|---|
| `RC_mtm` (replacement cost of current MTM) | 0 | `max(PV, 0)` |
| `C_lag` (collateral is one day in arrears) | cost of the lag move | 0 |
| `C_tran` (move from default notice to final valuation) | yes | yes |
| `RC_risk` (bid/offer and timing of replacement hedges) | yes | yes |

Basel groups `C_lag`, `C_tran` and `RC_risk` as the margin period of risk (MPOR). Netting agreements apply the
aggregate PV per counterparty, and without them CE is far higher. For G-SIB-type counterparties, conservative practice
raises the volatility after a default notice. CE ignores recovery.

- `PFE_α = max_i CE_α(m_i)`. It is a future value and is *not discounted*.
- `EE(m_i) = E+[RC_mtm] + E+[C_lag] + E+[C_tran] + E+[RC_risk]`, where `E+` is the expectation floored at zero. For
  `X ~ N(0, σ²)`, `E+[X] = σ/√(2π) ≈ 0.399σ`.
- EEE = the running maximum of EE. EPE = the average EE over time. EEPE = the average EEE. Basel uses these because
  trades tend to be rolled over.
- `CVA = LGD · Σ_i p(m_i) · EE(m_i) · v_i`, with `p(m_i)` the default probability in period `i`. Compute it per
  netting set. A single trade's marginal CVA can be counter-intuitive without the rest of the set.

**Reader check, not printed in the source.** The Ex 5.10 columns reproduce as follows:

- `C_lag ≈ E[pv01] · σ_1d · 1.645`
- `C_tran = 1.5 · C_lag` (distressed multiplier DM = 1.5)
- `RC_risk ≈ E[pv01] · 1bp · 1.645`

For EE in Ex 5.12, replace 1.645 with 0.399. Use these to rough out the collateralised exposure of any swap from its
pv01 and its daily bp vol.

## Worked tables

**Ex 5.9 (5% CE).** 0 (`RC_mtm`) + 1,500,000 (`C_lag`, observed) + 6,500,000 (`C_tran`, model) + 1,200,000 (`RC_risk`)
= **9,200,000**.

**Ex 5.8, collateralised default.** Lima's PV ran 7.1mm, 8.6mm, 13.1mm over the last three days, on daily moves of
−1bp, −7bp and −21bp. Collateral held was 7.1mm. The claim of 6mm is 1.5mm of collateral lag plus 4.5mm of
uncollateralised valuation change, with a further 0.6mm replacement loss. At 30% recovery the loss is about 4.8mm.

**Ex 5.10, collateralised £100mm 10Y IRS (95%, DM 1.5).**

| m_i | E[pv01] | σ_1d | C_lag | C_tran | RC_risk | CE |
|---|---|---|---|---|---|---|
| 0y | £92k | 4.5bp | 681k | 1,021k | 151k | **£1,853k** |
| 2y | £75k | 5.5bp | 679k | 1,018k | 123k | £1,820k |
| 4y | £57k | 6.5bp | 609k | 914k | 94k | £1,617k |
| 6y | £38k | 6.5bp | 406k | 609k | 63k | £1,078k |
| 8y | £19k | 6.5bp | 203k | 305k | 31k | £539k |

PFE = £1,853k = today's CE, because a collateralised swap's delta declines over its life. Forward-starting swaps are
the exception.

**Ex 5.11, uncollateralised £100mm 2y-forward 8Y IRS (`RC_mtm` by Monte Carlo).**

| m_i | E[pv01] | RC_mtm | C_tran | RC_risk | CE |
|---|---|---|---|---|---|
| 0y | £73k | 540k | 540k | 120k | £1,200k |
| 2y | £75k | 12.5mm | 679k | 123k | £13,302k |
| 4y | £57k | 17.8mm | 609k | 94k | **£18,503k** |
| 6y | £38k | 15.2mm | 406k | 63k | £15,669k |
| 8y | £19k | 9.0mm | 203k | 31k | £9,234k |

**Ex 5.12 / 5.13, EE (£k).**

| m_i | collateralised: E+[C_lag] / E+[C_tran] / E+[RC_risk] / EE | uncollateralised: E+[RC_risk] / E+[C_tran] / E+[RC_mtm] / EE |
|---|---|---|
| 0y | 165 / 248 / 37 / **450** | 29 / 197 / 131 / 357 |
| 2y | 165 / 248 / 30 / 443 | 30 / 248 / 3,000 / 3,278 |
| 4y | 148 / 222 / 23 / 393 | 23 / 222 / 4,800 / **5,045** |
| 6y | 99 / 149 / 15 / 263 | 15 / 149 / 3,900 / 4,064 |
| 8y | 49 / 74 / 8 / 131 | 8 / 98 / 1,100 / 1,206 |

The book prints "max EE £5,193,000" for the uncollateralised case, but the column maximum is £5,045k.

**Ex 5.14, CVA at LGD 100%.** Discount factors `v` = 1.000, 0.963, 0.928, 0.906, 0.856.

- Collateralised, with p = 0.1% per period: **£1,592**.
- Uncollateralised, with p = 1%, 0.4%, 0.1%, 0.1%, 0.1%: **£25,593**.

At 60% LGD both fall by 40%. `scripts/csa_xva.py --selftest` reproduces both.

## Capital (s.17.2.5) and the CVA capital charge

- `RWA = EAD × RW + CVA vol charge`.
- SA-CCR: `EAD = 1.4 × (RC + PFE)`. RC is often zero for a well-collateralised counterparty, and PFE covers the MPOR.
- IMM: `EAD = α × EEPE`, with 1.2 ≤ α ≤ 1.4, EEPE over at most 5Y, and a 10-day MPOR for generic linear IRDs under
  stressed conditions. IMM is floored at a percentage of SA-CCR.
- Risk weights: cash 0%, BBB corporate bond 100%, CCP-cleared trades typically 2%.
- **Ex 17.7, CVA vol charge.** Start from Ex 5.14's CVA of $25,593. Raising PD by 0.1% a year lifts CVA to $51,354,
  a loss of $25,761. The replicating instrument is a 10Y zero-coupon corporate bond: the risk-free rate is 2%, the bond
  yields 2.171% (an unconditional 10Y PD of 1.7% at 100% LGD), and a 0.1% PD increase takes its yield to 2.274% and its
  price to $98.98. That $1.02 fall means a synthetic notional of $2.536mm (as printed; $25,761 / 1.02% ≈ $2.53mm). At 100% RW this gives a CVA RWA component
  of $2.536mm, and total RWA including EAD is $6.786mm.
- Basel III endgame floor: 0.725 × (credit + equity + operational + CVA RWAs) + standardised market-risk RWAs.
  SA-CCR raises RWAs and G-SIB scores most for one-directional, unmargined, uncleared derivatives (Barclays, *US
  short interest rate primer*, Jan 2025). Balance-sheet costs belong to `fi-balance-sheet-and-regulatory-costs`.
