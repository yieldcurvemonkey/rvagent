# Cross-collateral discount curves, CTD curves and where the risk lands

Detail for [SKILL.md](../SKILL.md). Sources: Darbyshire, *Pricing and Trading Interest Rate Derivatives* (3rd ed.,
2022), ch.5, 7, 13, 21; Darbyshire, *Coding Interest Rates*, s.6.6 and ch.7.

## Notation (Darbyshire)

`v_{cash:coll}` = DF for cashflows in currency *cash* collateralised in the same currency (local curve).
`w_{cash:coll}` = DF for cashflows in *cash* collateralised in another currency *coll*.
`F_0` = FX for immediate settlement, `f_i` = forward FX for date `m_i`, both for a pair written dom:for as in the
book (e.g. `F_usdeur`). Keep the pair direction explicit in code; canonical `fx_rates.pair` is BASEQUOTE.

Curve labels: the three letters before `:` are the only currency the curve may discount or forecast. After the
colon, `.` marks a forecasting curve and `-` a discounting curve: `EUR:1D.ESTR` (forecast), `EUR:EUR-CSA`
(benchmark CSA), `EUR:USD-CSA` (EUR cashflows under USD cash), `EUR:USD+EUR+GBP-CSA` (intrinsic multi-CSA). With
RFRs, `USD:1D.SOFR` = `USD:USD-CSA` and `EUR:1D.ESTR` = `EUR:EUR-CSA`. Three benchmark CSAs give 21 curves, 7 per
currency. The canonical `curve_id` grammar for these is `<CCY>-CSA-<COLL>` (`EUR:USD-CSA` is `EUR-CSA-USD`, with
`curve_zero.collateral` = USD); the forecasting curves are the plain RFR ids.

## Formulas

| Quantity | Formula | Source |
|---|---|---|
| PV of 1 USD under EUR collateral | `w_usdeur(m) = f_usdeur(m) · v_eureur(m) / F_usdeur,0` | Coding Interest Rates eq 7.4 |
| Forward FX, two equivalent forms | `f_i = (w_dom:for,i / v_for:for,i) · F_0 = (v_dom:dom,i / w_for:dom,i) · F_0` | eq 7.5 |
| Missing cross-CSA DF | `w_usdeur,i = (v_usdusd,i / w_eurusd,i) · v_eureur,i` | eq 7.6 |
| Proxy curve (any cash, any collateral) | `w_dom:for,i = (f_dom:for,i / F_0) · v_for:for,i` | eq 7.11 |
| Bootstrap EUR:USD-CSA from FX swaps | `w*_i = (1 + z^fx_i / f_{i-1}) · (v_i / v_{i-1}) · w*_{i-1}` | PT s.7.6.6 |
| Bootstrap EUR:USD-CSA from 1-period XCS | `w*_i = [(1 + r_i d_i) / (1 + (r*_i + z*_i) d*_i)] · (v_i / v_{i-1}) · w*_{i-1}` | PT s.7.6.6 |

In the XCS form, `v` is USD:USD-CSA, `r` the USD RFR, `r*` the EUR RFR and `z*` the basis on the EUR leg. Since
`v_i/v_{i-1} = 1/(1 + r_i d_i)`, the period discount rate of EUR cashflows under USD cash is `r*_i + z*_i`. With the
usual negative EUR/USD basis, EUR:USD-CSA DFs sit above EUR:EUR-CSA DFs. In canonical terms: `basis_swaps` row with
`leg_a = EUR-ESTR`, `leg_b = USD-SOFR`, `collateral = USD`, `spread_bp = z*`.

**Invariance check.** Forward FX must not depend on the CSA under which the XCS is traded ("the forward FX rates are
the same regardless of under which CSA the XCSs are traded", PT p.96). Burgess (*Low Latency Interest Rate
Markets*) puts it as: CSA curves calibrated to FX forwards and XCS change DFs only, not forwards. A cross-CSA build
that yields different forward FX for the same date is wrong.

**Minimal curve set.** `n` currencies need `n` local curves plus `n − 1` cross curves (from XCS or FX swaps). Example
USD/EUR/NOK: local USD, EUR, NOK curves; `EUR:USD-CSA` from EUR/USD XCS under USD collateral; `NOK:EUR-CSA` from
EUR/NOK XCS under EUR collateral. Validity: entries of the cash x collateral one-hot matrix sum to `2n − 1` and every
currency's row sum plus column sum exceeds 1 (Coding Interest Rates s.7.3.3).

### Ex 7.3 (PT p.96): USD:EUR-CSA DFs from the other three, F0 = 1.20 EURUSD

| i | v (USD:USD) | v* (EUR:EUR) | w* (EUR:USD) | f = (w*/v)·F0 | w (USD:EUR) = (v/w*)·v* |
|---|---|---|---|---|---|
| 1 | 0.990 | 0.985 | 0.986 | 1.1952 | 0.989 |
| 2 | 0.975 | 0.962 | 0.961 | 1.1828 | 0.976 |
| 3 | 0.951 | 0.941 | 0.937 | 1.1823 | 0.955 |

## Intrinsic multi-CSA (CTD) curve

`DF_CTD(t+1) = DF_CTD(t) / (1 + max_k r_k(t) · d)`, where `r_k` is the O/N discount rate of the *same cashflow
currency* under eligible collateral `k`. The max is right for both sides: the party holding the liability posts and
chooses the collateral that lowers the magnitude of its liability, which is the highest discount rate.

- Combining JPY and USD collateral for JPY cashflows (PT Ex 5.6): post USD for 2 days, then switch to JPY through an
  XCS or FX swap. DFs t+0..t+4: JPY 1, 0.999945, 0.999889, 0.999830, 0.999770; USD 1, 0.999942, 0.999885,
  0.999827, 0.999769; combined 1, 0.999942, 0.999885, 0.999826, 0.999766.
- Speed. A naive 10Y DF takes about 3,650 sequential daily steps. Darbyshire prefers comparing block rates over
  steps that mimic node spacing: first steps of {2, 5, 10, 20, 30, 50} days, then
  `y = ceil(1825 / (1 + exp((4500 − Σx) / 1400)))` days (eq 6.17). That takes about 17 to 32 evaluations from 3Y to
  30Y. The block DF is always ≥ the exact daily DF, because a max of block averages is ≤ the average of daily maxima.
  Example C1 = {1, 2, 3}%, C2 = {3, 2, 1}%, C3 = {2, 2.5, 2}%: exact CTD DFs 0.99991781, 0.99984933, 0.99976716; with
  a 2-day block, 0.99986303 and 0.99978086.
- Darbyshire defends the approximation on three grounds: curves are smooth and the CTD persists in blocks; the
  intrinsic curve already ignores option value; and daily switching is operationally unrealistic. In his words, it is
  "more of a realistic valuation from an operational sense than an academic one".
- Combinatorics. Every subset of eligible currencies is its own multi-CSA curve. The institution must (i) automate
  single-CSA curves per cashflow currency, (ii) automate combining them, and (iii) extract CSA terms per trade to pick
  the curve.

## Where the discounting risk lands (PT ch.13, ch.21)

Signs in these tables are as printed in the source: per +1bp in the source's own instruments, so a received swap
shows negative ∂P/∂r. That is not this repo's DV01 convention, where receive fixed is positive. The bump direction of
the basis spread `s` is not defined in the source chapter, so read magnitudes and offsets, not the sign of `s`.

**Ex 13.2.** Received €100mm 10Y ESTR IRS, PV €5mm, discounting-basis pv01 €2,500 (≈ $3,000 at EURUSD 1.2).
Risk in $/bp:

| CSA | EUR ∂P/∂r | EUR ∂P/∂s | XCS | USD ∂P/∂r | USD ∂P/∂s |
|---|---|---|---|---|---|
| EUR cash only | −99,000 | +3,000 | 0 | 0 | 0 |
| USD cash only | −99,000 | 0 | −3,000 | 0 | +3,000 |

The discounting risk moves from the EUR OIS curve to the USD OIS curve through the XCS market. Hedge by paying a
EUR/USD XCS, using the USD collateral and converting it to EUR. The equal EUR delta in both rows implies the 10Y
basis was near zero.

**Ex 13.3.** The same trade under an EUR + USD cash CSA, where EUR is CTD to 5Y and USD after:

| Bucket | EUR ∂P/∂r | EUR ∂P/∂s | XCS | USD ∂P/∂s |
|---|---|---|---|---|
| 5Y | | +1,600 | +1,500 | −1,500 |
| 10Y | −98,900 | | −3,000 | +3,000 |

Total discounting risk is a little under $3k, split between EUR OIS to 5Y and USD OIS via XCS for 5y5y. PV is
slightly below €5mm because the CTD blend discounts more heavily. When the two collaterals are nearly equally cheap, a
hard risk boundary at the switch tenor "might be misleading". Hedging the XCS/OIS basis only makes sense once a
posting choice is committed, and committing gives up the switch profit.

**Ex 21.4, cross-gamma.** Received $1mm pv01 of 30Y GBP IRS under a USD-cash-only CSA, paid the same under the
benchmark GBP CSA. Flat at inception. After GBP +1bp the PVs are ∓$1mm, and discounting risk is
±$1mm × 30 / (2 × 10,000) = ±$1,500 pv01. Risk view ($/bp, 30Y): GBP SBS +1,500, GBP/USD XCS −1,500, USD SBS
−1,500. If instead the XCS spread moves 1bp, the GBP IRS delta becomes 1,500. The cross-gamma is symmetric. This
is common in XCS books, where the XCS benchmark CSA is USD cash but the fixed leg is hedged with a local-CSA IRS.

**Discount-delta shortcuts (PT ch.21).** Discounting pv01 ≈ PV × T/2 / 10,000 for an annuity-like swap, and
≈ PV × T / 10,000 for a zero-coupon swap. Use them for quick sanity checks of off-market and foreign-CSA trades.

**Book level (J.P. Morgan, *Bills, Bonds, and basis...oh my*, 7 Feb 2020).** On the dealer swap-book schematic
(Exhibit 5, as of 3 Feb 2019), bilateral trades are 15% of gross notional but about half of gross market value.
Discounting risk by segment ($mn/bp, DV01 / discounting):

| Segment | Discount curve | DV01 | Discounting risk |
|---|---|---|---|
| Corporates without CSA | Libor | 1,528 | 106 |
| Legacy SPVs (dealers receive fixed, positive PV) | Libor | 536 | 260 |
| Corporates with CSA | OIS | 260 | 50 |
| Callable issuers | OIS | 78 | 24 |
| SSAs | OIS | 31 | 7 |

Net, dealers carried about $80mn/bp of long-end FF/Libor basis risk, clustered beyond 10Y. The risk is convex. A
rally makes paid bilateral positions more negative, so dealers buy long-end basis in a rally. Callables offset this
only partly.
