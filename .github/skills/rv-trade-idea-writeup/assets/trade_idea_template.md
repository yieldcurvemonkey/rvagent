# <Trade name, one line: what is bought vs sold, in which market>

Template for files under `ideas/`. Fields follow `.github/instructions/trade-ideas.instructions.md`.
Delete a row only if it is genuinely not applicable, and write "n/a" with the reason. Never leave a level
without its as-of time and source table.

## 1. Header

| Field | Value |
|---|---|
| Date written | YYYY-MM-DD |
| As-of (levels) | YYYY-MM-DD HH:mm TZ, snap (`settle` / `close` / `eod_ny` / `eod_ldn` / `fix` / `intraday`) |
| Source tables | e.g. `curve_par` (snap, curve_id), `fut_quotes`, `opt_quotes`, `vol_surface`, `swap_spreads` |
| Market(s) | e.g. USD SOFR swaps and futures |
| Structure | e.g. 2s5s10s fly, DV01-weighted, receive the belly |
| Direction | e.g. long the fly (belly cheapens) / short the fly |
| Convention | Spread = longer minus shorter (bp). Fly F = 2 x belly minus wings (bp), positive = belly cheap. Or state the weight set and its order if it differs |
| Units | bp for yields and spreads; $ per bp for DV01; nv or abpvs for normal vol; price in bp running or $ premium |
| Sign | DV01 signed, + = long duration (receive, long bond/future). P&L = -DV01 x change in yield (bp) |
| Size | Signed DV01 per leg (table in section 2); net DV01 of the package |
| Risk | $ loss at stop (= capital at risk); % of portfolio risk budget |
| Risk allocation | e.g. 100% / 50% (state the rule that set it, e.g. halved in high vol) |

## 2. Legs and sizing

| Leg | Instrument (generic) | Side | Weight (as quoted) | Signed DV01 (ccy/bp) | Notional / contracts | Level at entry (as-of) |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| Net | | | | sum | | |

Hedge ratio and its formula: e.g. N_b = N_a x PVBP_a / PVBP_b (state PVBP per unit notional and date).
Contracts = notional / contract size x conversion factor (bond being hedged is the deliverable). State lot size and whether the net basis is in the sizing.
Vega (options only): per leg, $ per nv or per abpvs; delta-hedge rule and threshold.

## 3. Thesis and premise

- **Mechanism (who loses money to us):** one or two sentences, economic, not "the spread looks cheap".
- **Premise (the belief that must be true):** the observable the trade depends on, e.g. "the policy path will be
  cut by N meetings" or "the CA reverts to the model".
- **Why now / why this structure:** the constraint that makes the mispricing persist (flows, supply, regime).
- **Named failure mode(s):** one specific event that makes the premise false, not "market risk".
- **Reversal trigger:** a level, data print or event that makes you exit or cut, stated in advance.

## 4. Levels, horizon and risk-reward

| Item | Level (bp) | P&L ($) | Basis / note |
|---|---|---|---|
| Entry (mid) | | | Mid and quoted-mid plus execution charge stated separately |
| Entry (incl. charge) | | | |
| Current | | | As-of stamp |
| Target | | | Fair-value or horizon anchor, e.g. "June meeting" |
| Stop | | | Level, not P&L; the $ loss at stop is in section 2 |
| Reward / risk | | | abs(target - entry) / abs(entry - stop), or target $ / stop $ |
| Holding horizon | | | Calendar days or meetings; event dates in section 8 |
| Half-life (if mean-reverting) | | | Method and window; "n/a" if the trade is not a reversion bet |
| Expected return over horizon | | | Carry + roll + expected move, with the probability used |

Rule: state the loss at stop in $ and as a multiple of the daily (or weekly) move so the reader sees how
unusual the stop is.

## 5. Carry and roll

| Horizon | Carry (bp) | Roll-down (bp) | Carry + roll (bp) | Carry ($) | Months to breakeven (if carry drags) |
|---|---|---|---|---|---|
| 1m | | | | | |
| 3m | | | | | |
| To expiry / 12m | | | | | |

Carry and roll computed on non-overlapping forwards (spot-vs-spot double-counts the short-rate path).
Funding basis (repo or SOFR, term or overnight) and the bp-to-$ conversion stated.
Carry/vol ratio (if vol-normalised): carry (bp/yr) / 1y realised bp vol, annualised (bp/yr), convexity-adjusted version if relevant.
Breakeven ratio (convexity trades): daily breakeven (bp) / 1y realised daily vol (bp).

## 6. Fair value and rich/cheap

- **Fair-value model:** name it and its inputs (e.g. policy path, PCA, regression on macro variables, model CA).
- **Residual today:** value in bp, and its definition (market minus model).
- **Z-score / percentile:** lookbacks printed side by side (e.g. 3m, 1y, 3y or since-2000), the window, and the
  sample exclusions (regimes such as zero-bound periods).
- **Regression fit:** R-squared and standard error if a regression is used; the R-squared of the trade against
  the risk factors (rate level, credit, equity, vol) to show what it is exposed to.
- **Episode definition (if mean reversion):** threshold, time in episode, and the overshoot history.

## 7. Scenarios and payoffs

| Scenario | Shock | Leg P&L ($) | Total P&L ($) | Total (bp of fly or spread) | Probability (if used) |
|---|---|---|---|---|---|
| Parallel up | +25bp / +50bp | | | | |
| Parallel down | -25bp / -50bp | | | | |
| Steepen | long end +10bp, front 0 | | | | |
| Flatten | long end -10bp, front 0 | | | | |
| PC1 | +1 sigma PC1 | | | | |
| PC2 | +1 sigma PC2 | | | | |
| Vol | +/-10 normal vol | | | | |
| Extreme curve | state the move that bounds the loss | | | | |
| Event | e.g. policy surprise of N bp on date D | | | | |

Terminal breakeven (options): the level at which the structure loses at expiry.
Probability-weighted value (if scenarios are weighted): sum of P(regime) x regime value.

## 8. Catalysts and dated events

| Date (local) | Event | Expected effect on the trade | Plan (hold / cut / add) |
|---|---|---|---|
| | | | |

## 9. Devil's advocate and kill criteria

- **Strongest case against:** the best argument that the trade is wrong, written in full sentences.
- **What would have to be true for the stop to be hit:** the scenario, not the level.
- **Kill criteria (pre-committed):**
  1. Stop hit: close at the stop, no re-underwriting in the same session.
  2. Premise broken: state the observable and its threshold.
  3. Time stop: exit if the horizon passes without the expected move (state the date).
  4. Better trade: take profit early if the spread converges and a better use of risk exists (state the comparison).

## 10. Crowding, positioning and liquidity

- Positioning evidence (CFTC or dealer data, surveys, dealer inventory) and the direction it pushes.
- Does the trade add to an existing book theme? Net exposure to the book's largest risk.
- Liquidity: bid/offer in bp for each leg at the as-of time; delta-hedge threshold and time of day; lot size.
- Execution plan: venue (cleared curve: name the CCP), order type, expected cost (bp), and whether the entry is
  deferred for liquidity.

## 11. Track record and review (filled after the trade)

| Date opened | Date closed | Entry | Exit | P&L ($) | Premise held? | Stop respected? | Lesson |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Judge the decision by premise and process, not only by P&L.

## 12. Sources

- **Data tables used:** table names, snap, as-of time (section 1).
- **Skills applied:** links or names of the skills whose method was used.
- **Research cited:** publisher, author, title, date (no file paths).
- **Known data issues:** any inconsistency in the inputs or the source, and how it was handled.
