---
name: rv-trade-idea-writeup
description: Writes a standard G10 rates relative-value trade note (an ideas/ file) from a trade idea or structure. Covers thesis and premise, legs with signed DV01 or vega sizing, hedge ratios, entry, target and stop in bp with reward-to-risk and kill criteria, carry and roll over a stated horizon, z-score or residual with its lookback, scenario P&L, catalysts, devil's-advocate review and sources with as-of times. Use when the user asks to write up, document, draft or justify a trade idea, trade note, trade box or trade ticket, or types "trade idea", "write this up", "trade recommendation", "entry target stop", "risk reward", "scenario table" or "kill criteria". It assembles the note; the numbers come from the method skills (curve-, spread-, stir-, vol-), so a bare "is this fly cheap" question goes there.
argument-hint: "<trade idea or structure>"
user-invocable: true
---

# Trade idea write-up

A trade note is a decision record. It states the economic mechanism that makes the other side lose money,
the premise the trade depends on, how it is sized, where it is wrong, and what will make you exit. Every level
carries an as-of time and a source table. This skill turns a trade idea into that note, filled from data the
user supplies, and never invents a level, a z-score or a P&L figure.

Use the template in [assets/trade_idea_template.md](assets/trade_idea_template.md). A filled historical example
is in [references/worked_example_blues_ca.md](references/worked_example_blues_ca.md). Market-specific points,
a second example and a list of failure modes are in [references/markets_and_failure_modes.md](references/markets_and_failure_modes.md).

## When to use
- "Write up this trade", "trade note for the 2s5s10s fly", "draft a trade box", "document the idea".
- A candidate from a screen or a research digest needs entry, target, stop, carry, z-score and scenarios before it
  is presented or put on.
- A user asks how to size, hedge or justify a G10 curve, fly, swap-spread, basis, convexity, vol or STIR trade.
- A written note must be checked against the house format before it goes into `ideas/`.

Out of scope: the screen itself ([rv-opportunity-scan](../rv-opportunity-scan/SKILL.md)), the pre-trade challenge
([rv-devils-advocate](../rv-devils-advocate/SKILL.md)) and live tracking after entry ([rv-trade-monitoring](../rv-trade-monitoring/SKILL.md)).

## Inputs (data-agnostic)

Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap and OIS rates for each leg | `curve_par` | snap-stamped, at least 3y daily | Constant-maturity or fitted; never raw bond yields for curve fits |
| Zero rates and forwards | `curve_zero` | same snap as `curve_par` | Forward breakevens and roll-down |
| Futures quotes and contract specs | `fut_quotes`, `fut_static` | settle, 1st to 16th generic | Conversion factors, lot size, first and last delivery |
| Bond quotes and static data | `bond_quotes`, `bond_static` | close, with coupon and maturity | Hedge ratios on actual PVBP, not curve-point PVBP |
| Financing rates | `repo_rates`, `rate_fixings` | daily | Carry needs term or overnight funding stated |
| Option quotes and vol surface | `opt_quotes`, `vol_surface` | snap, normal vol in nv | Vega, vomma and skew legs |
| Swap spreads, basis and CCP basis | `swap_spreads`, `basis_swaps`, `ccp_basis` | snap, convention stated | Name the clearing house with each CA or basis level |
| Z-scores and residuals | `signals` | lookback stated per row | Recompute if the lookback is not in the row |
| Central-bank meetings and event probabilities | `cb_meetings`, `events_probs` | dated | Horizon anchors and priced path |
| Positioning and supply | `positioning`, `auctions` | weekly or per event | Crowding and flow catalysts |
| Book exposure (for crowding and risk budget) | `positions`, `pnl` | end of day | Current signed DV01 by tenor |

If an input is missing, say so in the note's sources and ask the user or the data adapter for it. Do not fill it
from memory or from a published number that has no as-of time.

## Conventions (state them in every note)

- **Rates and spreads in bp.** A yield level in % is converted once, and the as-of stamp is kept with it.
- **DV01 is signed.** Positive DV01 = long duration (receive fixed, long bond, long future), in currency per bp.
  Leg P&L = -DV01 x change in yield (bp). A receive gains when yields fall.
- **Curve spread = longer minus shorter.** 2s10s = y10 - y2. A steepener is a rise in this spread.
- **Fly, equal weight.** F = 2 x y(belly) - y(wing 1) - y(wing 2). For 2s5s10s, F = 2 x y5 - y2 - y10.
  F positive = belly cheap (higher yield). "Receive the belly" = long belly DV01 and short the wings.
- **Other weight sets** (PC-neutral, DV01-weighted, regression) are quoted belly-relative. Write them in
  wing / belly / wing order and say whether the package is level-neutral, slope-neutral or PC1-neutral.
- **Swap spread.** US: swap minus Treasury yield, in bp (a 30y swap spread of -67.7bp is swap below the bond).
  EGB asset swap: bond yield minus swap, quoted as a bond spread over swaps. Say which one is used.
- **Options.** Normal (Bachelier) vol in nv, bp per year. Annualised bp vol in abpvs (the usual unit for vega
  packages). Premium in bp running for payer or receiver spreads, in $ for straddles. Name the expiry x tenor.
- **Carry and roll are signed as P&L:** positive means earned. Say the sign in the note.
- **P&L:** give every $ amount with its unit ($k or $mn) and the DV01 or vega basis beside it.
- **FF-SOFR and SOFR-FF** are opposite conventions in different sources. Normalise before comparing.

## Method

### 1. Mechanism, premise and structure
1. Write the mechanism as the economic reason someone on the other side loses money to us. "Gluing features
   together is not a theory." Name the counterparty whose constraint or flow makes the mispricing persist
   (dealer balance sheet, supply calendar, liability hedging, a central-bank reaction function).
2. Write the premise: the observable that must be true for the trade to work (a path of policy moves, a
   convergence to a model, a return of realised vol below implied). Each premise gets a test in the review.
3. Choose the structure to match the risk you want. Prefer a relative structure to an outright vol short when
   both are available: hedge rich vol with the rates structure it normally moves with, so the trade bets on
   the residual normalising (Citi Research, "Fading vega dislocations", 5 Oct 2026).
4. Name the hedge explicitly, with its DV01 and the factor it leaves open. Example from the sources: a
   2y forward 2s10s SOFR steepener at $25k DV01 hedged with $10k DV01 of a FOMC-dated FF-OIS steepener
   (Citi Research, "Time for moderation", 17 Feb 2023).
5. Write the trade ticket's four ingredients: a rationale, a profit target and stop-loss that give the capital at
   risk, an exit strategy known at entry with an estimate of its cost, and instruments and sizes that match the
   analysis (Düring, "Fixed Income Trading and Risk Management", 2021). A deliberate decision not to adjust a
   position is also a trade.

### 2. Sizing
1. **DV01 per leg.** DV01_i = notional_i x PVBP_i per unit notional, signed. Put it in the legs table.
2. **DV01-neutral hedge.** N_b = N_a x PVBP_a / PVBP_b, with both PVBPs per the same unit notional. Worked: $100mn
   of a bond with PVBP $184.0 per bp per $1mn against a swap with PVBP $191.3 per bp per $1mn needs a swap
   notional of 100 x 184.0 / 191.3 = $96.2mn, a hedge ratio of 0.962 (J.P. Morgan, "Global Fixed Income
   Markets Weekly", 21-22 Aug 2026).
3. **Futures.** Contracts = notional / contract size x conversion factor, for a bond that is the deliverable
   being hedged (other bonds: DV01 ratio). Worked: $100mn of bond against a future with CF 0.851 gives
   100,000,000 / 100,000 x 0.851 = 851 contracts (J.P. Morgan, "Born(e) in the US(A)", 31 Jul 2026).
4. **Fly DV01.** For the -0.5 : 1 : -0.5 DV01-weighted fly with belly DV01 B, the wings each carry -B/2 and
   P&L = -(B/2) x dF. So B = $100k gives $50k per bp of F. Check it against the sum of the printed DV01 weights:
   they must sum to the neutrality you claim.
5. **Vega packages.** A delta-hedged skew package (long payer, short receiver, small long straddle) is vega-neutral
   when N_p x V_p + N_r x V_r + N_atm x V_atm ~ 0, with signed notionals (long +, short -) and per-unit vegas.
   The source example: +40 - 41 + 1 = 0. Delta-hedge notional: N_swap = -(N_p x D_p + N_r x D_r + N_atm x D_atm)
   / DV01_swap, with deltas in DV01-equivalent per unit notional, signed (Ade Rhodes, "USD 3m2y Payer Skew
   Steepener", 8 Oct 2025).
6. **Cross-currency or cross-expiry vol.** Match by realised beta, not by vega alone, and disclose any expiry or tail
   mismatch in the note.
7. **Book sizing.** Macro desks size each trade as the loss to the watch level, typically 0.25% to 1% of portfolio
   per trade. A radar entry needs reward-to-risk above about 1.5 : 1 and at least about 100k DV01 in DM rates
   (Citi Research, "Global Macro Trade Ideas Radar", 13 Aug 2026).
8. **Scale to the edge.** Halve risk in high volatility (ING used 50% for a PC-neutral 2s5s10s fly "because of
   greater market volatility", 9 Mar 2020). Cut a short-gamma position from $100mn to $50mn when the edge has
   shrunk to about 3 normals rich (3m10y vol had fallen from 66 to 59 nv; Citi Research, "Gamma and vega RV",
   14 Jan 2019).
9. **Asymmetric, regime-aware sizing.** State the macro assumption the hedge ratios imply, and the likely regime
   shift. Size up when the valuation signal and the likely shift point the same way, size smaller when the trade
   loses if the shift happens (his example: sell 5s when 5s are rich to history and a faster-recovery shift is
   likely; do not size a buy of cheap 5s as large). Buy protection against the specific shift at book level and
   subtract its cost from expected gains (Lehman Brothers, Tuckman, "Macro-Awareness in Relative Value Trading",
   Oct 2003).

### 3. Entry, target, stop and horizon
1. **Entry.** Quote the mid and the charge separately: entry = mid moved against you by the charge. Worked: a 50bp
   mid with a 0.5bp charge gives an entry of 49.5bp for a receive (ING, 9 Mar 2020).
   Only the simplest structures are executed in stressed markets: use DV01 weights for execution (ING, 12 Mar 2020).
2. **Target.** Set it on the spread level in bp, tied to a dated anchor: the next central-bank meeting, a funding
   event, an auction or a fiscal date. Fair-value targets net off a convexity cost: expected profit = (current
   forward - predicted) - convexity cost, so 28bp - 8bp = a 20bp profit target on a receive-the-belly forward fly
   quoted at 48bp (Citi Research, "Flying too high", 20 Dec 2010). The 20bp is a profit, not a level.
3. **Stop.** Set it on the spread level, never on P&L. The loss at stop in $ is the capital at risk: the number the
   book has to absorb (Citi Research, "Can back-end USTs derail EM risk?", 20 Aug 2026). Also state the stop as a
   multiple of the normal daily or weekly move, so the reader sees how unusual it is.
4. **Reward-to-risk.** = |target - entry| / |entry - stop| for a level trade, or target $ / stop $ for a P&L-set
   trade. Typical sources use 1.5 : 1 to 2 : 1 (for example, a $450k target against a $225k stop).
5. **Half-life for reversion trades.** Fit dx = k (mu - x) dt + sigma dW (Ornstein-Uhlenbeck). Half-life =
   ln(2) / k, in the time unit of k (a per-day k gives days). A quick regression of daily changes on (mu - x) has
   slope approximately k (Huggins and Schaller: 0.055 against a fitted 0.056). Report the half-life and the
   window; a half-life longer than the holding period means the trade is a carry bet, not a reversion bet.
6. **Expected move and ex-ante Sharpe.** Sharpe over a horizon = conditional expected excess return / conditional
   standard deviation over the same horizon. Annualise with sqrt(periods per year), which assumes independent
   repeats of the trade. Include carry and pull-to-par. A 4-week Sharpe of 0.76 annualises to
   0.76 x sqrt(13) = 2.74 (Huggins and Schaller, "Fixed Income Relative Value Analysis", 2nd ed., 2024; the source
   prints 2.73). Under an OU process the annualised Sharpe falls as the holding horizon lengthens, so prefer short
   horizons with tight targets (for example half the distance to the mean), and constant-vol OU overstates Sharpe
   at extreme entry points.
7. **Stop-loss under OU.** The stop can follow the model's moving two-sigma band instead of a fixed level. The
   source example: a PCA-neutral 2s5s7s trade with an expected profit of 32bp, a mean first-passage time of 84 days
   and a stop at the band of -42bp, a 7bp loss after one week (same source). Scaling in as the spread
   widens conflicts with a stop, because size grows until the stop and then drops to zero.

### 4. Carry and roll
Carry is the income from holding the trade over a stated horizon. Roll is the change from moving down the curve
with the curve unchanged. Forward breakevens say how much the curve must move for the trade to break even.

1. **Total return.** Total = carry + price change. For a bond financed at repo, carry is approximately yield minus
   repo rate.
2. **Roll-down and carry breakeven, 1y horizon on a 5y point.** Let y5 and y4 be spot yields and f(1y,4y) the
   forward yield with term financing, which is the horizon yield at which total return is zero. The source quotes
   breakevens as the rally a long needs: carry breakeven = y5 - f(1y,4y), roll-down = y5 - y4, and the rally still
   needed after the roll = y4 - f(1y,4y) (= carry breakeven - roll-down). Positive = a drag on a long. In the
   P&L-positive convention used in this skill, carry = f - y5, roll = y5 - y4 and carry + roll = f - y4, the
   sell-off a long can absorb with the curve otherwise unchanged. A short has the equal and opposite carry; the
   forward is the same for long and short.
3. **Same at 3m on a 4.75y point.** Roll-down = y5 - y4.75, carry breakeven = y5 - f(3m,4.75y), carry + roll =
   f(3m,4.75y) - y4.75. Worked (1y horizon): a 5y note at 4.15% financed for 1y at 4.91% is negative carry. The
   1y4y forward is 3.93%, so the note must rally 22bp to break even (a rally beyond 22bp profits), against a
   1-sigma move of 65bp over the horizon: about one third of a sigma (BofA Global Research, "Rates basics: spot vs
   forward", 15 Feb 2024; the source rounds to about 30%). The 30y needs only 3bp, 6% of a sigma.
4. **Curve trades.** A DV01-neutral curve trade's carry breakeven is the forward slope minus the spot slope:
   the steepening needed to break even. Worked: a DV01-weighted 5s30s steepener with negative carry needs about
   19bp of steepening in one year to break even (same source).
5. **Months to breakeven.** For a trade whose residual is m bp and whose carry is c bp per month (negative),
   months = m / |c|. Worked: a 14bp-too-flat spread that rolls down 15.5bp per 3 months breaks even if the residual
   closes within 14 / (15.5 / 3) = 2.7 months (ING, "Deconstructing the EUR yield curve", 15 Jan 2020). The source
   prints 2.6 months; the formula with the stated inputs gives 2.7. Where carry is large against the move, also
   compute the probability that reversion takes longer than carry allows, from the first-passage-time distribution
   (Huggins and Schaller, 2024).
6. **Non-overlapping forwards.** Compare carry on forwards that do not overlap. Spot-to-spot comparisons count the
   short-rate path twice (same source).
7. **Carry at several horizons.** Carry is not linear in time: the 3-month blocks of one curve trade can earn very
   different amounts. Quote 1m, 3m and to expiry.
8. **Carry in money.** A bp carry must name its maturity and be converted to $: 84-day carry on a PCA-neutral
   trade was +EUR 70,000, which was negligible next to the mean-reversion potential (Huggins and Schaller, 2024).
9. **Carry and vol.** Carry/vol = carry (bp per year) / one-year realised bp vol, annualised (bp per year);
   Nordea's trade box has carry 79.2 over vol 46.5 = 1.70. Convexity-adjusted carry/vol uses the
   convexity-adjusted carry. The ratio ranks trades, not levels (Nordea Markets, "EUR rates: Pushing back",
   17 Jan 2024).
10. **Breakeven ratio for convexity trades.** BE/RV = daily breakeven (bp) / one-year realised daily vol (bp).
    A smaller ratio means cheaper embedded convexity. Worked: 10y10y / 25y10y with breakeven 2.2bp and realised
    3.0bp gives 0.73 from the rounded inputs; the source prints 0.72 (Citi Research, "Trading long-dated convexity",
    9 May 2019; Citi Research, "Forward steepener and vol divergence", 12 Jun 2023).
11. **Do not justify a steepener on roll.** Entry carry and roll are weak predictors of steepener P&L; rate and vol
    co-movement matter more (Citi Research, "A QT revolution", 17 Sep 2026).

### 5. Fair value, residuals and z-scores
1. **Residual.** Residual = market level minus model level, in bp. For a fly, residual < 0 means the belly is rich,
   > 0 cheap. For a cross-currency basis or CA, residual = market minus model CA. Name the model and its inputs.
2. **Z-score.** z = (x - mean over L) / standard deviation over L. Print at least two lookbacks side by side
   (for example 3m and 1y, or 1y and 3y). A steepener's z-scores should include a since-2000 or 3y window (Citi
   Research, "Forward steepener and vol divergence", 2023). Winsorise at +/-2.5 sigma and use a 252-day rolling mean
   for a z-band (Ade Rhodes, "USD 5s30s Swap Spread Flattener", 9 Oct 2025). Compute the mean and standard
   deviation from data up to the as-of snap only: a full-sample z-score is look-ahead in any backtest, and a
   signal dated t is traded from t+1. A z-score on a persistent level series is not a t-statistic, since |z| > 2
   occurs on far more than 5% of days.
3. **Thresholds.** Act on |z| of about 2 or more, with the lookback named; treat 3 as a stretch. The sources use
   "roughly 2 sigma" and "3 sigma" as description, not as rules, so the desk's threshold is a stated parameter.
   State which lookback the decision relies on; agreement between lookbacks is a check, not a rule.
4. **Episode statistics for mean reversion.** Define the episode, then count it. Example from one study: residual
   below -5bp for more than a week, then record the date it returns to zero and the date it overshoots by more than
   5bp. In 6 of 7 fly episodes the residual overshot by 5 to 10bp, typically within about three months (BNP Paribas,
   "EUR curve convexity: lessons from history", 25 May 2021). That is n = 7: quote the count and do not exit
   mechanically at zero.
5. **Exposure check.** Regress the trade's P&L on rate level, credit, equity and vol before writing it up.
   A fly with R-squared 0.03 against the 2y swap rate is rate-direction neutral. A fly with R-squared 0.65 against
   an equity P/E measure has equity term-premium exposure, and the note must say so (ING, "EUR crisis trades: let's get tactical", 3 Mar 2020). ING ran these on levels;
   levels regressions of persistent series overstate R-squared, so re-run on weekly changes before relying on it.
6. **PC residuals.** A k-factor residual is roughly the (k+1)-th factor times its loading, so a few factors cover
   most trades. Use PC-neutral weights from at least about a year of data on fitted constant-maturity yields, and
   hedge every lower-order factor, not only the DV01 (Huggins and Schaller, 2024). Check the non-linear relation
   to PC1 with a quadratic fit before trading a PC1-neutral fly (ING, "Deconstructing the EUR yield curve",
   15 Jan 2020).
7. **Model reliability.** Watch the rolling R-squared of the fair-value model. A 120-day R-squared that falls from
   about 100% to about 60% flags a model that no longer explains the market (J.P. Morgan, "Global Fixed Income
   Markets Weekly", 21-22 Aug 2026).

### 6. Convexity and vol
1. **Taylor P&L.** dP ~ Delta dS + 1/2 Gamma dS^2 + Vega dsigma + 1/2 Vomma dsigma^2 + Vanna dS dsigma.
2. **Bachelier vomma.** Vomma = Vega x d^2 / sigma, with d = (F - K) / (sigma sqrt T). Out-of-the-money wings carry more
   vomma, so a risk reversal plus an at-the-money straddle has positive net vomma. Worked (hypothetical, from the
   source): net vega 0 and vomma 0.9, a +5 abpvs vol move gives 1/2 x 0.9 x 25 = +11.25 and a net vega of +4.5,
   so trim the at-the-money leg (Rhodes, 8 Oct 2025).
3. **Rebalance thresholds.** Resize when |net vega drift| > 5 abpvs or the net rate move exceeds 5bp; re-strike the
   wings when they are more than 5bp off target (same source).
4. **Delta-hedge schedule and time.** State the threshold and the hour. Thresholds from the sources: every 15 to 30bp
   (a 2019 backtest's sweet spot), 20 to 25bp, and 25bp on the longer leg of a flattener (Citi Research, "Trading
   long-dated convexity", 9 May 2019; "In search of cheap vol", 17 Jan 2020). Time of day changes realised vol, so
   state the snapshot (same source).
5. **Convexity-adjustment (CA) trades.** CA = futures-implied rate minus matched-maturity swap rate. The
   one-factor model depends only on rates vol because maturity is fixed, so gaps to the model are positioning
   driven (Citi Research, "Time for moderation", 17 Feb 2023). A short CA is short vol. Hedge it with a weighted curve trade rather than a swaption when the curve
   trade is cheaper to carry. Worked: a $200k DV01 CA hedged with the 2s5s10s fly at DV01 weights
   0.705 / -1 / 0.465 (Citi Research, "Sell Blues convexity adjustments, hedged", 9 Feb 2017).
6. **Vol-rate beta and sign flips.** One-month beta of normal vol change on rate change can flip sign on
   flight-to-quality days, so a beta-based vol hedge can fail exactly when it is needed. Test it on stress days
   (J.P. Morgan, "Near, far, wherever yields are", 2 Oct 2026).

### 7. Scenarios and payoffs
1. **Scenario table.** Columns: scenario, shock, leg P&L, total P&L in $ and bp, probability if used. Rows: parallel
   +/-25 and +/-50bp; steepen and flatten 10bp; PC1 and PC2 at one sigma; vol +/-10 normal vol; the extreme-curve
   move that bounds the loss; each dated event. Section 7 of the [template](assets/trade_idea_template.md) holds the layout.
2. **Extreme-curve bound.** State one extreme move and the maximum loss it implies. Worked (ING, 9 Mar 2020): a
   2s5s10s DV01 fly at -8bp could go to zero; in an extreme move, duration demand slightly inverts 5s10s while 2s5s
   stays flat, giving a maximum downside of about 10bp for receivers of the belly.
3. **Zero-vol scenarios understate convexity.** One scenario assumes zero vol. Bear and bull at 0.5 each gives
   (5.02 + 9.06) / 2 = 7.04% against a 7.00% neutral yield, so the 4bp gap is the convexity value at 100bp vol
   (Salomon Brothers, "Understanding the Yield Curve, Part 6", Nov 1995).
4. **Equal-probability averages.** Scenario expected return = equal-weight average of scenario returns. Back out
   the implied yield vols and correlations and check them: strong views can make any position look attractive.
5. **Probability-weighted value.** Value = sum of P(regime) x regime value. Worked: 9% x 6 + 21% x 10 + 70% x 24
   = 19.44, about 19bp (Citi Research, "Flying too high", 20 Dec 2010).
6. **Costless option decomposition.** For a steepener (flatteners reverse the signs): curve pick-up = spot -
   forward; vol pick-up = forward - strike; total = spot - strike. Check, USD 3m 2y30y bear steepener: spot 27.6,
   forward 18.5, strike 5.7 gives 9.1 + 12.8 = 21.9 = 27.6 - 5.7 (Citi Research, "Fading vega dislocations",
   5 Oct 2026).
7. **Terminal breakeven.** For options, state the level at which the structure loses at expiry. Worked: a 6m1y1y
   receiver ladder loses only if the 1y1y rate is below 2.38% at expiry (Citi Research, "The art of gamma hedging",
   12 Mar 2018).
8. **Futures duration.** Shock the basket along PC1 (level) and PC2 (slope) and find the cheapest-to-deliver in each
   shock. Probability-weight the futures DV01 across them rather than using the current CTD. A 50bp parallel
   sell-off can move the CTD from a 5% 2045 bond to a 1.375% 2050 bond, raising futures duration about 47%
   (Morgan Stanley, "Buy Higher Rates Protection at a 30% Discount", 27 Aug 2026).

### 8. Catalysts, flows and horizon
1. Name the catalyst that closes the spread: a meeting, a funding event, an auction or buyback, a fiscal date, a
   budget. Give the date. A trade with no dated catalyst is a carry trade and must be labelled as one.
2. Wait for the event before entering long-end steepeners when a hawkish skip could cause a knee-jerk bear
   flattening (Citi Research, "Forward steepener and vol divergence", 2023).
3. Fed decisions take effect the day after the FOMC. Put the effective date in the horizon (same source).
4. Seasonality is a tailwind, not a standalone signal. Give the hit rate, the sample and the number of episodes
   (BNP Paribas, "EUR curve convexity: lessons from history", 25 May 2021).
5. A positive-carry flattener is described as "effectively a free long convexity buy" when its daily breakeven is near
   zero (GBP 15y10y / 25y10y example: 1y carry +0.52bp, daily breakeven 0.00). State the breakeven with the carry
   (Citi Research, "In search of cheap vol", 17 Jan 2020).

### 9. Devil's advocate and kill criteria
1. Write the strongest argument that the trade is wrong, in full sentences. Name the event or flow that makes the
   premise false.
2. Pre-commit four exits: stop (no re-underwriting in the same session); premise broken (observable and threshold);
   time stop (a date when the expected move has not happened); better trade (take profit early when a better use of
   the risk exists, and state the comparison).
3. Re-underwrite near the stop when a forecast changes, and record the change that prompted it.

### 10. Crowding, positioning and liquidity
1. Positioning evidence: CFTC asset-manager and leveraged-fund net positions, dealer inventory and the
   direction it pushes. A CA that keeps widening while vol falls is a positioning story; say so (Citi Research,
   "Swearing in huge expectations", 13 Jan 2017).
2. Book overlap: does the new trade add to the largest existing theme? Use direction-neutral weights to offset an
   existing exposure, not as a stand-alone directional bet.
3. Liquidity: bid/offer in bp for each leg at the as-of time, the lot size, and the hedge cost. Some attractive
   convexity trades are deferred until liquidity improves; say so.
4. Clearing: name the clearing house for every CA, basis or swap-spread level. CA levels differ between CME- and
   LCH-cleared curves.

## Worked examples
Figures are from the cited sources unless marked **derived** (arithmetic on the source's numbers, shown). The
full filled note is in [worked_example_blues_ca.md](references/worked_example_blues_ca.md); a second example and the
per-market points are in [markets_and_failure_modes.md](references/markets_and_failure_modes.md).

- **Hedged short CA (Citi Research, "Sell Blues convexity adjustments, hedged", 9 Feb 2017).** $200k DV01 of CA,
  2,000 packs against a $2bn matched swap at 8.8bp; hedge pays the 2s5s10s belly with DV01 weights 0.705 / -1 / 0.465
  at fly -18.2bp; target +$600k, stop -$350k. **Derived:** reward-to-risk 1.71 : 1; target 3.0bp and stop 1.75bp of CA
  per $200k DV01. Closed early on 6 Jun 2017 at CA 6.6bp for +$500k net; the CA leg alone is +$440k (2.2 x $200k).
- **Receive-belly PC-neutral 2s5s10s (ING Global Markets Research, "March ECB: QE or bust", 9 Mar 2020).** Entry 49.5bp
  (mid 50bp less a 0.5bp charge), target 20bp, stop 65bp, carry and roll +4.7bp per 3 months, 50% risk allocation.
  **Derived:** reward-to-risk 29.5 / 15.5 = 1.90 : 1. The printed weights are not DV01-neutral, so net DV01 must be stated.
- **Months to breakeven (ING, "Deconstructing the EUR yield curve", 15 Jan 2020).** Residual 14bp, roll-down 15.5bp per
  3 months: 14 / (15.5 / 3) = 2.7 months (the source prints 2.6).
- **Carry breakeven (BofA Global Research, "Rates basics: spot vs forward", 15 Feb 2024).** 5y note at 4.15% financed
  for 1y at 4.91%, 1y4y forward 3.93%: the note must rally 22bp to break even, against a 65bp one-sigma move:
  22 / 65 = 0.34 of a sigma (**derived**; the source says about 30%).
- **DV01 hedge ratio (J.P. Morgan, "Global Fixed Income Markets Weekly", 21-22 Aug 2026).** PVBP $184.0 and $191.3 per bp
  per $1mn: 184.0 / 191.3 = 0.962, so $100mn of the bond is hedged with $96.2mn of swap (printed).
- **Probability-weighted value (Citi Research, "Flying too high", 20 Dec 2010).** 9% x 6 + 21% x 10 + 70% x 24 = 19.4,
  printed as 19bp.
- **Costless option decomposition (Citi Research, "Fading vega dislocations", 5 Oct 2026).** USD 3m 2y30y bear steepener:
  spot 27.6, forward 18.5, strike 5.7: curve pick-up 9.1 + vol pick-up 12.8 = 21.9 = 27.6 - 5.7.

## Signals and interpretation
- **Rich or cheap** is market minus model, in bp, with its z-score and lookbacks. A large residual alone is not a
  timing signal: fading a residual into heavy supply "feels like catching a falling knife" (Citi Research, "What to
  do about OATs?", 1 Oct 2026).
- **Premise test.** Does the observable that the premise depends on move the way the note says? If not, the
  trade is wrong even while the spread is still wide.
- **Model vs market divergence is the signal**, not the level of the CA (Citi, "Swearing in huge expectations").
- **Take profit when the spread converges**, even before the target, when a better trade exists (Citi Research,
  "Turning Green from Blue on short convexity", 6 Jun 2017).
- **Event probabilities.** Compare your probability of an event with the market-implied one and trade the gap; the
  view must be out of consensus, or it is already priced (Papic, "Geopolitical Alpha", 2021).
- **Positive carry is not a reason** to enter a steepener on its own. Carry says how much the trade earns while
  waiting; the breakeven says how far the curve must move.

## Pitfalls
- **Stops set on P&L** drift as DV01 changes. Set stops on spread levels, and state the $ loss at stop in the note.
- **Unadjusted yield spreads** between bonds of the same issuer and maturity are not RV signals. On an upward-sloping
  curve the higher-coupon bond usually yields less; on a downward-sloping curve it yields more (Huggins and Schaller, 2024).
- **Backtests are not evidence of an open trade.** Label them illustrative, state the sample, the costs and the
  trial count. "Most discoveries in finance are false, due to multiple testing and selection bias" (López de Prado,
  "Advances in Financial Machine Learning", 2018).
- **Hedge sign and net DV01.** Print the net DV01 of the package. A hedge whose weights do not sum to the neutrality
  you claim is not neutral.
- **Two legs of different expiry or tail** are sized by realised beta and the mismatch is disclosed.
- **Stale or mixed snaps.** Never mix settlement and close in one level; state the snap on each leg.
- **Source inconsistencies.** Recompute every number you copy from a source: arithmetic, units (bp vs % vs $) and
  signs. Several cited notes print figures that do not tie (see the markets reference, section E).
- **Crisis execution.** Use DV01 weights and simple spreads so the trade can be executed; a PC-neutral weight set is
  harder to fill in a stressed market.
- **A trade with a named risk that is "market risk"** has no risk. Name the failure mode: "a hawkish Fed surprise
  flattens 2s5s", "a range-bound 20y sector prices the value out of the basis".
- **Scale changes.** Do not reuse a $-P&L target after the DV01 changes. Recompute the target from the bp move.

## Output
Produce one `ideas/` file from [the template](assets/trade_idea_template.md), with these fields filled or marked
"not stated in source" with the reason:

- **Header:** date written, as-of timestamp with zone and snap, source tables, market, structure, direction,
  sign and unit convention, signed DV01 per leg, net DV01, $ loss at stop.
- **Thesis:** mechanism, premise, named failure mode, reversal trigger.
- **Levels:** entry (mid and charge), current, target and stop in bp and in $, reward-to-risk, horizon, half-life.
- **Carry and roll:** at 1m, 3m and to expiry, in bp and $, with the funding basis and months to breakeven when carry drags.
- **Fair value:** model, residual in bp, z-scores with their lookbacks, regression R-squared, exposure check.
- **Scenarios:** parallel, curve, PC1, PC2, vol, extreme-curve bound and dated events, in $ and bp.
- **Catalysts:** dated list with the expected effect and the planned response.
- **Devil's advocate and kill criteria:** the strongest case against, plus the four pre-committed exits.
- **Crowding and execution:** positioning evidence, book overlap, bid/offer per leg, clearing house.
- **Sources:** tables and snaps used, skills applied, research cited by publisher, title and date.

If the DV01, the levels or the as-of stamps are missing, return the note with those fields marked missing and ask
for them. Do not estimate them. Hand the finished note to [rv-devils-advocate](../rv-devils-advocate/SKILL.md)
for challenge and to [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md) once it is on.

## Scripts
None. The arithmetic here (DV01 per leg, hedge ratios, months to breakeven, reward-to-risk, carry breakevens) is
short enough to show in the note, and the formulas are given in Method. The scenario table and portfolio
aggregation belong to [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md) and
[port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).

## Related skills
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): challenge the note before entry; kill criteria
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md): live stops, targets, re-underwriting after entry
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): combining z-score, carry/vol and half-life into a rank
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): where the candidate came from
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): how the package is traded and cleared
- [rv-research-digest](../rv-research-digest/SKILL.md): turning a research note into a testable idea
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry, roll and forward breakeven formulas in depth
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01, PVBP and hedge-ratio conventions
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts, conventions and benchmarks per currency
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weights, sign and residuals
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): DV01-neutral and beta-weighted spreads
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PC-neutral weights and exposure analysis
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): regression and beta-weighted hedge ratios
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread and asset-swap conventions and levels
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): positioning evidence for the crowding section
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event probabilities and dated catalysts
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): CA definition, model and hedge
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): delta-hedging, vomma and vega P&L
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): lookbacks and z-score conventions
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): OU fits, half-life and stop design
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): scenario tables across the book
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): risk per trade and budgets
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables named in Inputs
- [eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md): one-pagers and charts for the note
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): P&L attribution and performance metrics.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): overfitting and out-of-sample validation.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): bid/offer, impact and liquidity costs.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): balance-sheet and regulatory shadow costs.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-grid RV, kinks and aged forwards.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-based conditional curve trades.
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): fitted-curve residuals and bond switches.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): cross-market and EGB spreads.
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): tenor and index basis, including SOFR-FF.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CCP basis between clearing houses.
- [xccy-basis](../xccy-basis/SKILL.md): cross-currency basis.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): cash-futures basis and implied repo.
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): invoice spreads and futures asset swaps.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR strip calendars, flies and packs.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): the implied policy path.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo, specialness and funding turns.
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): breakevens, linkers and inflation swaps.
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): swaption and cap/floor vol RV.
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): convexity and strikeless vol in the long end.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): regimes and scenario trees.
- [quant-regime-detection](../quant-regime-detection/SKILL.md): statistical regimes and structural breaks.
- [quant-cointegration](../quant-cointegration/SKILL.md): cointegration tests and level hedge ratios.
- [port-portfolio-construction](../port-portfolio-construction/SKILL.md): combining trades into a book.
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): cleaning and point-in-time hygiene.

## References
Main sources: Citi Research (15 notes), ING (four notes) and other publishers (15 documents). Each bullet names the source's contribution.
The last two bullets list 19 further notes cited only in the market file.
- Citi Research (Ruslan Bikbov, Jason Williams) - "Sell Blues convexity adjustments, hedged" (US Rates Trade Idea, 9 Feb 2017): CA definition, positioning, DV01 sizing and fly hedge; used for the filled example.
- Citi Research (Ruslan Bikbov, Jason Williams) - "Turning Green from Blue on short convexity" (US Rates Trade Idea, 6 Jun 2017): early close for a better trade, closing levels, 2:1 reward-to-risk.
- Citi Research (J. Mathai et al.) - "Swearing in huge expectations" (US Rates Weekly, 13 Jan 2017): DV01 sizing and carry split by leg; straddle versus curve hedge on carry.
- Citi Research (Ruslan Bikbov, Jason Williams) - "Gamma and vega RV" (US Rates Vol Lab, 14 Jan 2019): short-gamma scaling rule and vega-neutral fly.
- Citi Research (Ruslan Bikbov, Jason Williams) - "Trading long-dated convexity" (US Rates Vol Lab, 9 May 2019): breakeven-to-realised ratio, hedge bands, backtest caveats.
- Citi Research (Ruslan Bikbov, Jason Williams) - "In search of cheap vol" (Rates Vol Lab, 17 Jan 2020): delta-hedge bands and hedge timing; positive-carry flattener.
- Citi Research (Mike Chang, Jason Williams, Andrea Appeddu) - "Forward steepener and vol divergence" (Rates Vol Lab, 12 Jun 2023): steepener z-windows, FOMC timing, breakeven ratio.
- Citi Research (Mike Chang, Jason Williams, Andrea Appeddu, Alejandra Vazquez Plata) - "Fading vega dislocations" (Rates Vol Lab, 5 Oct 2026): relative structure over an outright vol short.
- Citi Research (J. Searle et al.) - "A QT revolution" (European Rates Weekly, 17 Sep 2026): carry is a weak predictor of steepener P&L; rate and vol co-movement.
- Citi Research (J. Searle et al.) - "What to do about OATs?" (European Rates Weekly, 1 Oct 2026): a large residual is not a timing signal into heavy supply.
- Citi Research (Ruslan Bikbov, Jason Williams) - "The art of gamma hedging" (Rates Vol Lab, 12 Mar 2018): costless decomposition, terminal breakeven of a receiver ladder.
- Citi Research (Amitabh Arora, Dan Chen) - "Flying Too High: Receive Belly of 1-Year Forward 5s10s30s Fly" (US Rates Trade Recommendation, 20 Dec 2010): convexity-adjusted target, probability-weighted fair value.
- Citi Research (Luis Costa et al.) - "Global Macro Trade Ideas Radar" (13 Aug 2026): loss-to-watch-level sizing, reward-to-risk and DV01 minimums, closed-trade lessons.
- ING Global Markets Research (Antoine Bouvet, Benjamin Schroeder, Padhraic Garvey) - Rates Strategy notes "Deconstructing the EUR yield curve" (15 Jan 2020), "EUR crisis trades: let's get tactical" (3 Mar 2020), "March ECB: QE or bust" (9 Mar 2020), "March ECB: taking out the ECB put" (12 Mar 2020): months to breakeven and non-overlapping carry; PC-neutral receive-belly trade with 50% allocation; exposure regressions; liquid-contract rule; premise review.
- Huggins, Doug and Schaller, Christian - "Fixed Income Relative Value Analysis: A Practitioner's Guide" (2nd ed., Wiley, 2024): OU half-life, ex-ante Sharpe, OU stop, carry in money terms, unadjusted-spread pitfall.
- Ilmanen, Antti - "Understanding the Yield Curve, Part 6: A Framework for Analyzing Yield Curve Trades" (Salomon Brothers, Nov 1995): expected-return decomposition; zero-vol scenario caveat.
- Citi Research (J. Mathai et al.) - "Time for moderation" (US Rates Weekly, 17 Feb 2023): hedge-sizing example, one-factor CA statement, closed-trade log format.
- Citi Research (L. Costa et al.) - "Can back-end USTs derail EM risk?" (Emerging Markets Strategy Weekly, 20 Aug 2026; G10-relevant part only): capital at risk equals the stop.
- Nordea Markets (Anders Svendsen) - "EUR rates: Pushing back" (17 Jan 2024): trade box with carry/vol, z-score and fly levels.
- Düring, Alexander - "Fixed Income Trading and Risk Management: The Complete Guide" (Wiley, 2021): four ingredients of a trade ticket.
- Tuckman, Bruce - "Macro-Awareness in Relative Value Trading" (Lehman Brothers, LMR Quarterly, Oct 2003): four steps of macro-aware RV, asymmetric sizing.
- Papic, Marko - "Geopolitical Alpha" (Wiley, 2021) (partial read): event probability against market-implied probability.
- Axel, Ralph - "Rates basics: spot vs forward" (BofA Global Research, US Rates Watch, 15 Feb 2024): roll-down, carry breakeven and forward formulas.
- BNP Paribas (Eric Oynoyan, Marco Meijer) - "EUR curve convexity: lessons from history" (G10 Rates Focus, 25 May 2021): fly episode study, overshoot statistics, seasonality caveat.
- Rhodes, Ade - "Trade Idea: USD 3m2y Payer Skew Steepener" (8 Oct 2025): vega and vomma package, rebalance thresholds.
- Rhodes, Ade - "Trade Idea: USD 5s30s Swap Spread Flattener" (9 Oct 2025): z-band with winsorising, residual signal, small-sample caveat.
- J.P. Morgan (Ipek Ozil et al.) - "Near, far, wherever yields are" (US Interest Rate Derivatives, 2 Oct 2026): implied versus realised, vol-rate beta and its sign flips.
- J.P. Morgan - "Global Fixed Income Markets Weekly" (F. Diamond et al., 21-22 Aug 2026): hedge ratio from PVBP, rolling R-squared of a fair-value model.
- J.P. Morgan (Ipek Ozil, Christopher Hayward, Ergin Alptuna) - "Born(e) in the US(A)" (Global Markets Strategy, 31 Jul 2026): futures contract count with conversion factor.
- Morgan Stanley (S. Zhou et al.) - "Buy Higher Rates Protection at a 30% Discount" (US Rates Strategy, 27 Aug 2026): CTD distribution under parallel shifts; futures duration jump.
- López de Prado, Marcos - "Advances in Financial Machine Learning" (Wiley, 2018) (partial read): trial counting and multiple testing; backtests are not research tools.
- Also cited in the market and failure-mode file: Citi Research, "Trade worries linger" (17 May 2019), "Deal or no deal: Rates implications" (10 May 2019), "Learning on the job" (2 Aug 2019), "Fixing the plumbing" (30 Sep 2019), "Buying vol for less" (25 Sep 2019), "Long Live Formosa" (9 Jan 2017), "Sell Eurodollar convexity in Blues" (8 Jan 2018), "Eat, pay, spend" (27 Mar 2020), "Higher yields are here to stay" (European Rates Weekly, 24 Sep 2026), "Macro tapas: running with the bulls; should rates scare us?" (7 Aug 2026), "Paying the basis (again) into 2025" (13 Dec 2024), "Can Secretary Bessent and Chair Warsh save the curve?" (21 Aug 2026).
- Also cited there: J.P. Morgan, "Zen and the art of gamma maintenance" (9 Mar 2018), "A comprehensive look at convexity hedging in interest rates" (29 Mar 2019), "The long and short of it" (3 Aug 2018), "Renewed Formosa supply continues to flatten the long end" (21 Feb 2020), "Non-Stop Dynamics: Unpacking the Selloff, Plumbing, and USD/JPY x-ccy Basis" (Japan Fixed Income Markets Weekly, 21 Feb 2025); Goldman Sachs, "Reaching Limits" (Global Rates Trader, 2 Oct 2026); BofA Global Research, "Start of rates bite" (Global Rates Weekly, 2 Oct 2026).
