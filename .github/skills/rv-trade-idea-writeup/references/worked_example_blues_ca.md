# Filled example: hedged short front-end convexity adjustment (Feb 2017)

A historical trade from a cited research note, filled into the `ideas/` template (`assets/trade_idea_template.md`).
It is not a live idea. Dates, levels and sizes are the note's own, and the note's pricing time is the as-of stamp.
Fields the note does not give are marked **not stated**. Figures marked **derived** are arithmetic on the note's
numbers and are shown with their formula. Contract codes are replaced by generic names.

Source: Citi Research, North America Rates Trade Idea, "Sell Blues convexity adjustments, hedged"
(Ruslan Bikbov, Jason Williams, 9 Feb 2017). Follow-up: Citi Research, "Turning Green from Blue on short
convexity" (Ruslan Bikbov, Jason Williams, 6 Jun 2017). Sizing precedent: Citi Research, US Rates Weekly,
"Swearing in huge expectations" (13 Jan 2017).

---

## 1. Header

| Field | Value |
|---|---|
| Date written | 9 Feb 2017 (note date) |
| As-of (levels) | 9 Feb 2017, 08:00, pricing time as printed in the note; snap **not stated** |
| Source tables | none in the note (research levels); in the canonical layout these would be the front-end futures quotes and the matched-maturity swap, and the fly levels from the par curve |
| Market(s) | USD front-end: short-maturity Eurodollar futures packs (quarterly, four consecutive contracts) against a matched-maturity CME-cleared swap |
| Structure | Short hedged convexity adjustment (CA). Buy 2,000 of each of four consecutive front-end futures (2,000 packs); pay $2bn matched-maturity CME-cleared swap at 8.8bp of CA; hedge = pay the belly of a 2s5s10s swap fly |
| Direction | Short CA (futures rich to swaps, expected to converge); hedge = pay 5y belly |
| Convention | CA in bp = futures-implied rate minus matched-period swap rate, as the note defines it. Fly level in bp of the DV01-weighted fly (**sign convention of the note's fly not restated**; the note's regression form is belly-positive, 5y minus 0.7 x 2y minus 0.47 x 10y) |
| Units | bp for CA and fly; P&L in $ thousands; DV01 in $ per bp |
| Sign | Signed DV01: + = long duration. The futures packs are the short-CA leg; the swap is paid |
| Size | $200k DV01 of CA (= $200k per bp of CA, derived from the note's sizing) |
| Risk | Stop = -$350k (capital at risk per the note's target/stop; see section 4) |
| Risk allocation | **not stated** |

## 2. Legs and sizing

| Leg | Instrument (generic) | Side | Weight (as printed) | Signed DV01 | Notional / contracts | Level at entry |
|---|---|---|---|---|---|---|
| 1 | Front-end futures pack, 4 consecutive quarters | Buy (short CA) | 2,000 of each contract | not stated per leg; total CA = $200k/bp | 2,000 packs | CA 8.8bp (the note's entry level) |
| 2 | Matched-maturity CME-cleared swap (pay fixed) | Pay | 1 | part of CA DV01 | $2bn notional | 8.8bp CA |
| 3 | 2s5s10s fly, 2y leg | Receive | $147mm (DV01 weight 0.705) | **derived**: not stated in $/bp | $147mm | fly -18.2bp |
| 4 | 2s5s10s fly, 5y leg | Pay | -$85.6mm (DV01 weight -1) | not stated | -$85.6mm | fly -18.2bp |
| 5 | 2s5s10s fly, 10y leg | Receive | $20.89mm (DV01 weight 0.465) | not stated | $20.89mm | fly -18.2bp |
| Net | Hedge (legs 3 to 5) | | DV01 weights sum to +0.170 of the belly DV01 | **derived**: 0.705 - 1 + 0.465 = +0.17 x belly DV01 | | |

Hedge sizing: the note gives the hedge as DV01 weights (0.705 / -1 / 0.465), not as a net-zero package. Those
weights sum to +0.17 of the belly DV01, so the hedge carries a small net long-duration exposure. The note does
not state it. The template's net-DV01 row exists so this is visible before the trade is put on.

Same structure at half size (Citi, Jan 2017): $100k DV01 = 1,000 packs, $1bn swap, hedge $79mn / -$44.4mn /
$10.9mn (0.73 / -1 / 0.46), package carry +$206k over 3m (+$130k CA, +$76k hedge). The alternative hedge with a
3y1y straddle ($96mn) carried about $65k over 3m (+$130k CA, -$65k hedge), so the curve hedge was preferred on
carry. (Citi Research, US Rates Weekly, "Swearing in huge expectations", 13 Jan 2017.)

Sizing in the note is in DV01 per bp of the CA, not in notional. Keep swap notional ($bn) and CA DV01 ($k per bp)
in separate columns.

## 3. Thesis and premise

- **Mechanism:** asset managers and leveraged funds were net short front-end futures, expecting a hawkish Fed.
  Dealers took the other side, paid swaps to hedge and so became structurally short convexity adjustments, which
  widened the CA. The CA dislocation is positively correlated with dealer positioning (Citi, Feb 2017).
- **Premise:** the CA reverts toward the one-factor model calibrated to cap and floor volatilities. The note says
  the Blues pack CA was about 4bp (about two sigma) wide to the model at entry.
- **Why now:** heavy corporate supply in January may have added receiving flows to swaps and widened the CA
  (Citi, Feb 2017).
- **Named failure mode:** further positioning imbalance keeps the CA wide. The note's rationale is positioning
  driven; it has no separate risk line. (Inferred from the rationale, and the companion note of Jan 2017 names
  "further positioning imbalance" as the main risk.)
- **Reversal trigger:** **not stated.**

## 4. Levels, horizon and risk-reward

| Item | Level | P&L | Basis / note |
|---|---|---|---|
| Entry CA | 8.8bp | | Matched CME-cleared swap, 9 Feb 2017 |
| Entry fly | -18.2bp | | DV01-weighted 2s5s10s |
| Target | not a level | +$600k | Stated as P&L, not in bp |
| Stop | not a level | -$350k | Stated as P&L, not in bp |
| Target in CA bp | 3.0bp | | **derived**: 600 / 200 per bp; ignores the hedge's P&L |
| Stop in CA bp | 1.75bp widening | | **derived**: 350 / 200 per bp; ignores the hedge's P&L |
| Reward / risk | 1.71 : 1 | | **derived**: 600 / 350 |
| Holding horizon | 3 months (carry horizon) | | The note states carry over 3m; no time stop is stated |
| Half-life | **not stated** | | Not a reversion-speed estimate in the note |
| Expected return | +$380k carry over 3m | | Expected CA move not stated beyond the target |

Stop as a risk input: the loss at stop is -$350k, which is the capital at risk for this trade (Citi Research,
"Can back-end USTs derail EM risk?", 20 Aug 2026: capital at risk "is essentially equal to the stop loss"). Express it in the note as $350k and as roughly 1.75bp of CA
against the $200k DV01.

## 5. Carry and roll

| Horizon | Carry | Roll-down | Carry + roll | Carry ($) | Months to breakeven |
|---|---|---|---|---|---|
| 3m | +$380k (note); the short fly alone about +3.2bp carry and roll over 3m | about +1.3bp (CA roll-down over 3 months, note) | not stated | +$380k | n/a (carry positive) |

Carry per bp of CA over 3m: 380 / 200 = 1.9bp-equivalent (**derived**). The note gives the total, not the split
between the CA leg and the hedge. The January version of the same structure split carry into +$130k from the
CA leg and +$76k from the hedge.

## 6. Fair value and rich/cheap

- **Model:** one-factor CA model calibrated to cap and floor volatilities (Citi, Feb 2017).
- **Residual at entry:** about 4bp wide to the model, described as about two sigma (note). The note also has the
  CA about 3bp (about two sigma) wide to the fly regression, which is the convergence the trade is built on.
- **Z-score lookback:** **not stated** in the note. Use the template's required lookbacks (for example 3m, 1y and 3y)
  before reusing the "two sigma" statement.
- **Positioning evidence:** asset managers and leveraged funds were net short Eurodollar futures and had
  increased those shorts over the prior year, with dealers on the other side (note's Figure 2, not reproduced).
- **Vol cross-check:** the note does not give the CA-implied vol at entry.

## 7. Scenarios and payoffs

The note gives no scenario table. The derived lines below use only the note's DV01 and levels and exclude the
hedge, whose DV01 composition is not given.

| Scenario | Shock | Total P&L (derived, excludes hedge) |
|---|---|---|
| CA narrows to the level printed at exit | 8.8bp to 6.6bp, i.e. -2.2bp | +$440k (= 2.2 x $200k) |
| CA widens by 2bp | +2bp | -$400k (= -2 x $200k) |
| Stop | +1.75bp CA widening | -$350k (approximately; hedge excluded) |

Realised check: the note's exit P&L was +$500k net of costs (section 11). The CA leg alone is +$440k. The hedge
pays the belly, so it gains when the DV01-weighted fly rises. The note's regression, CA = 9.7 + 20.6 x fly (rates
in %), implies 0.206bp of CA per bp of fly, so the hedge is about 0.206 x $200k = $41k per bp of fly (**derived**).
The fly moved from -18.2bp to -16.5bp (+1.7bp), so the hedge gained about +$70k. $440k + $70k = $510k, which
ties to +$500k within the transaction costs the note nets off. The note does not print this split.

## 8. Catalysts and dated events

| Date | Event | Expected effect |
|---|---|---|
| Jan 2017 | Heavy corporate supply | Associated receiving flows in swaps; may widen the CA (note) |
| Feb 2017 | Positioning of asset managers and leveraged funds in front-end futures | Positioning-driven CA dislocation (note) |
| Feb 2017 onward | Fed hiking expectations, which the crowded short-futures positioning was built on | The note does not state the trade's sign to a hawkish Fed surprise; the net level exposure after the hedge (section 2) is what matters. **No dated decision is given in the note** |

## 9. Devil's advocate and kill criteria

- **Strongest case against:** the CA may stay wide if positioning keeps building. A CA can widen against a model
  even while vol falls, and then positioning, not vol, is the driver. The note itself says the trade is exposed to
  further positioning imbalance.
- **Premise failure:** a CA that keeps widening after the model is re-estimated, with positioning still growing.
- **Kill criteria used:** stop at -$350k. The note's time horizon is 3 months (carry). A better trade is the
  reason the note gives for the early exit (section 11).
- **Not stated:** a pre-committed time stop and a reversal level.

## 10. Crowding, positioning and liquidity

- Positioning: the note says positioning is the main driver. Asset managers and leveraged funds were short, dealers
  were long and paying swaps.
- Book: the trade is a direct bet on CA convergence and adds to any existing short-convexity exposure. The note
  does not discuss the book.
- Liquidity: the note says the hedge fly clears equally well on either CCP. Bid/offer and delta-hedge rules are
  **not stated**. CCP curve: both legs are cleared at CME. Name the CCP with every CA level, because CA levels
  computed on CME and LCH curves differ.
- Execution cost: **not stated**.

## 11. Track record and review

| Opened | Closed | Entry CA | Exit CA | Entry fly | Exit fly | P&L (net of costs) | Premise held? | Stop respected? |
|---|---|---|---|---|---|---|---|---|
| 9 Feb 2017 | 6 Jun 2017 (117 days) | 8.8bp | 6.6bp | -18.2bp | -16.5bp | +$500k | Partly: CA narrowed by 2.2bp but the $600k target was not reached | Yes (not hit) |

Exit reason (note): "we have not reached our target of +$600K P&L yet," but the hedged Greens CA looked better, so
the trade was closed early at 1:30pm, 6 Jun 2017.

Lesson for the template: an early exit to a better trade is a documented choice. Record it in section 11 with the
comparison (here, the Green package's expected return against the remaining $100k to target and the remaining
time), not as a target hit.

## 12. Sources

- **Data tables used:** none in the note; levels are the note's own, at the pricing time shown.
- **Skills applied (in the canonical layout):** `stir-convexity-adjustment` for the CA and its hedge;
  `curve-butterflies` for the fly. Names only; no links are implied by this example.
- **Research cited:** Citi Research (Bikbov, Williams), "Sell Blues convexity adjustments, hedged", 9 Feb 2017;
  "Turning Green from Blue on short convexity", 6 Jun 2017; Citi Research (Mathai et al.), "Swearing in huge
  expectations", US Rates Weekly, 13 Jan 2017.
- **Known data issues:** the note's pricing time is 8am; the close is 1:30pm on 6 Jun 2017; the fly sign convention
  and the hedge net DV01 are not restated in the note; the z-score lookback is not stated.
