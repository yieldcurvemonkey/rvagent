---
name: macro-central-bank-reaction-functions
description: 'Reads a G10 central bank''s reaction function (Fed, ECB, BoE, BoJ, BoC, RBA, RBNZ, SNB, Riksbank, Norges Bank) and compares the market-priced policy path with what the bank''s rule, framework and voting arithmetic imply, by classifying the regime, anchoring a Taylor-type rule and neutral rate (r-star), converting meeting-dated pricing to hike or cut probabilities, counting votes and dissents, testing credibility (5y5y, FOMC-day moves) and mapping the gap to front-end, curve and cross-bank trades. Covers guidance removal, new chairs, last-hike and first-cut timing, curve regime mapping, QT levers and FX intervention triggers (JPY REER band, 3-in-6-months rule). Use when a trader asks about a reaction function, Taylor rule, hike or cut pricing vs fair, terminal or neutral rate, r*, credibility, dot plot, dissents, BoJ yen defence or MoF intervention, last hike or first cut, forecast meetings, policy spreads between banks, or meeting-spread RV. Priced path: stir-policy-pricing-whats-priced-in.'
---

# G10 central bank reaction functions

A reaction function maps the economy (inflation against target, labour or output gap, expectations, financial
conditions, FX) to a policy decision. Markets price the expected path, so a reaction-function view is a view on the path.
The RV edge is the gap between the market-priced path and what the bank's own rule, framework and voting arithmetic imply,
plus the regime change when that rule itself changes. Long rates move with the expected policy path, so a path view is
expressed in the segment that carries it: front meetings, the belly, or a cross-CB spread (King, Mais Lecture, 17 May 2005).

## When to use
- A meeting or string of meetings is priced far from your rule-based path (hike or cut pricing vs fair).
- A new chair, governor, board member, or framework or guidance change (guidance removed, dots changed, new inflation gauge).
- A supply, energy or FX shock hits a bank and you need its starting point: adjustment hikes, a hold, or cuts later.
- Relative policy trades across banks (pay one CB's meeting vs receive another's, 1y1y or FRA spreads).
- Positioning around a last hike, first cut, or a pause, or a view that the curve shape is changing regime.
- FX intervention or a balance-sheet decision could move the policy path (JPY, CHF, QT end).

Not for: fitting the path itself (`stir-policy-pricing-whats-priced-in`), NLP scoring of speeches
(`macro-central-bank-nlp`), reserve plumbing (`stir-central-bank-balance-sheet-and-reserves`).

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/references/schemas.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Meeting calendar and forecast-meeting flag | `cb_meetings` | per meeting, >= 10y | `has_projections` marks SEP, MPR and similar months |
| Policy and administered rates | `rate_fixings` (policy index) | daily, >= 10y | regime dating and the policy-rate level |
| Meeting-dated STIR and OIS strip | `stir_quotes` | daily settle, meeting-dated | convexity- and turn-adjusted before reading as a path |
| Market event probabilities, if present | `events_probs` | daily snaps | cross-check the strip, do not replace it |
| CPI, core, PCE, trimmed mean and median, unemployment, ULC, energy CPI weight, REER | `macro_series` | monthly/quarterly, >= 5y | use vintage (`pub_ts_utc`) and first-release flag |
| Inflation swaps (1y, 2y1y, 5y, 5y5y) | `infl_swaps` | daily | credibility and r-star proxy |
| Zero or par curve (2y, 5y, 10y, 30y) | `curve_zero` | daily | 2s5s10s fly, 6m2s and 2s10s inversion |

If an input is missing, stop and ask the user or the data adapter for it. Never invent a level, probability or dot.

## Method

### 1. Classify the regime and starting point
- Regime: hiking, on hold at neutral, easing, pre-turn (hold but hikes or cuts priced), transition (new chair, board,
  framework), or shock-led (energy, FX).
- Distance to neutral: real policy rate = policy rate minus expected inflation. Compare with r-star (step 2).
- Starting point decides the response to a shock. ECB at neutral with a sole inflation mandate can make "adjustment
  hikes". BoE and Fed, still "somewhat restrictive" in their own view, can hold rather than hike. A weak economy
  with high energy sensitivity may cut sooner and deeper afterwards (JWS Macro, #3: Iran and Front End Rates, 8 Mar 2026).
- Price vs quantity: score the domestic channels (labour tightness and wage catch-up, household balance sheets,
  corporate pricing power, fiscal cushioning, and credibility, which buys time) and the external ones (free-float FX,
  net energy importer). Price-led shocks force hikes; quantity-led shocks force a hold. The source ranks the US nearer
  Price, CAD, NZD and SEK nearer Quantity, and AUD and NOK nearer Price (JWS Macro, Global Rates Outlook #5: Price Vs
  Quantity, 10 May 2026). Re-score each time the shock changes.

### 2. Anchor the rule (a bound, never a point forecast)
- Taylor-type rate: `i = r* + pi + a_pi*(pi - pi*) + a_y*gap`, with a_pi = a_y = 0.5, pi* = 2, r* set separately. The gap is an output gap in percent of potential; with an unemployment gap use
  (u* - u), a sign flip, with an explicit Okun scaling, and state the scaling used.
  Worked: pi = 3.0, gap = +1.0, r* = 2 gives 6.0% (see `references/worked-examples.md`, section 1). A forward-looking
  variant replaces pi with expected inflation (Clarida, Gali and Gertler, 2000, external). The gap is not observable in
  real time, so the rule explains past decisions better than it forecasts (Duering, Fixed Income Trading and Risk
  Management, 2021). Willer and Saunders (2026) found no Taylor specification with a high out-of-sample Sharpe.
- Neutral (r-star): market-implied r* = 2y1y nominal swap minus 2y1y inflation swap. With a 2% target, neutral deposit
  = 2 + r*. Use OIS-based swaps, and treat the inflation-swap leg as a gauge, since it carries a risk premium and index-lag and seasonal carry. Use the mid, not the bid-offer; the direction of the mid matters, and drivers that lift R* (deficits at
  full employment, defence, AI capex, shrinking labour supply) push it up (JWS Macro, Global Rates Outlook #6, 7 Jun 2026).
  Source ranges as of their dates: Fed neutral 2.5-3.5% (JWS Macro, USD Rates and Fed outlook #1, 21 Aug 2025); ECB
  neutral 1.75-2.25% (JWS Macro, 7 Jun 2026).
- Terminal bound: a grid of unemployment against core PCE, read as a range. At core PCE 3.0 and unemployment 4.0-4.5, a
  Taylor-type grid gave a terminal of about 4.4-4.9% (BofA, Start of rates bite, 2 Oct 2026). Sanity-check against
  the real-rate cycle: real Fed funds peaked at 2.5-4.5% in typical hiking cycles (same source).
- Pick the inflation gauge the bank targets, and treat trimmed mean and median as lagging confirmation. Post-2021
  robust cores lagged headline by 6-8 months, while 1978-2001 showed no lag (JPM, Lags in robust PCE cores, 13 Aug 2026).
  Weigh the 3m run-rate against the level. Strip methodology changes first: one July 2026 PCE print was lifted about
  13bp by an asset-linked fee category (JPM, 14 Aug 2026).
- Money cross-check (optional): price gap P* = M V*/Y* minus actual P, with 1pp of gap adding about 10bp to annualised
  inflation next quarter. R-squared is about 0.18, so use it only as a cross-check (Hudson Bay Research, Jul 2026).

### 3. Read the market path, correctly
- Meeting-period implied rate `f_k` from the strip (convexity-adjusted and with turns removed, e.g. Japan's 1 April
  turn). Move at meeting k: `(f_k - f_{k-1})` in bp. Probability of one full step: `P = move_bp / 25`. Worked: 10bp = 40%;
  the ECB's 21bp for a September hike = 84% (Citi, STIRT Weekly, 7 Aug 2026).
  For a bank that is cutting the sign flips: P(cut) = -move_bp / 25. Use the bank's usual step size.
  For monthly-average futures (fed funds style), first strip the days before the meeting: new rate =
  (avg x D - prev x d_pre) / (D - d_pre), where D is days in the month and d_pre the days before the decision
  (`post_meeting_rate`). The raw month average understates a late-month move.
  `scripts/reaction_rules.py strip` does the conversion, keeps the sign, and flags missing values and |P| above 1.
- Meeting-date probabilities are not joint probabilities. Two 50% meetings are one hike with uncertain timing (Duering).
- A forward is expectations plus a time-varying premium. Forwards historically implied rising rates and flattening that
  did not happen (Ilmanen, Salomon Brothers, Jun 1995). Do not read the forward as the modal central-bank path: the
  forward settles on the mean, which sits above the mode when the path is skewed or volatility is high
  (Darbyshire, 2022; see worked examples, section 11).

### 4. Form the gap and decide
Gap = market path minus rule path, in bp per meeting, and minus the bank's own guidance. Read direction and
catalyst together.

| Situation | Read | Typical expression |
|---|---|---|
| Hikes priced, the bank has not validated them, MPC or board majority on hold | Hike premium likely to fade slowly, one meeting at a time | Receive the front meeting; fade in steps (BoE, Citi, Global Macro Strategy, 31 Jul 2026) |
| Hikes priced beyond what the bank can plausibly validate | Reaction risk is dovish | Receive the front; "the market is priced more hawkishly than a CB can validate" (Citi, STIRT Weekly, 21 Aug 2026) |
| Hold priced, but rule and bank signals point to hikes | Hawkish repricing is the risk | Pay the front meeting, before the next decision |
| Bank at neutral and paused | Curves try to price hikes sooner and more than expected | Pin the unchanged meeting; own belly vol; be wary of receivers while the bank pauses (JWS Macro, USD and Global Rates Thoughts #2, 13 Nov 2025) |
| Meeting almost fully priced | Meeting-to-meeting risk is fruitless | Use adjacent meeting spreads (JWS, 13 Nov 2025) |
| Removing a priced cut is itself tightening | "Bailey's snookering": not hiking when hikes are priced is passive easing (JWS, 7 Jun 2026) | Treat as a policy move in the rule |

- Fade-the-premium rule: "You never fade at fair value. You fade a deep value." Expect the premium to take several
  meetings to come out (JWS, 7 Jun 2026).
- Doom loop: hike pricing feeds bank calls, which feed the dots, which feed pricing. Stop out at a radical call; a
  "fully cooked" market is the signal to stop fading (JWS, 7 Jun 2026).
- Number beats timing: the number of cuts matters more than the timing of the first cut for an EUR curve (Nordea,
  EUR rates: Pushing back, 17 Jan 2024).

### 5. Decision mechanics (who moves and when)
- Forecast meetings: a bank is less likely to start a cycle at a non-forecast meeting. Hikes rarely come intra-meeting
  or in a rush; cuts can. The market under-prices hikes at meetings without new forecasts (swapsball, 8 Mar 2018).
  Re-test on the current `cb_meetings` table.
- Vote arithmetic, not dots. With guidance removed, the outcome depends on the voters. Count the hawks and doves on the
  rotating roster and the marginal vote. The chair can be outvoted, as the BoE chair was in 2005 and 2007 (Citi, STIRT
  Weekly, 21 Aug 2026). Do not extrapolate a year's hawkishness across a roster rotation (JWS, 21 Jun 2026).
- Dissents lead: at the BoJ, the last two hikes followed meetings with at least two hawkish dissents. One dissent was
  read as an early dovish signal (Citi, Global Macro Strategy, 7 Aug 2026).
- Quantifiers in minutes: "most" means more than half and "many" usually less than half (J.P. Morgan, US Weekly Prospects,
  21 Aug 2026).
- Back-to-back: the BoJ is "loathe to go back-to-back". When one hike is near-certain, the probability of two can exceed
  zero hikes, so cumulative pricing over two meetings should sit modestly above one 25bp step (Citi put fair at about 28bp
  against 25bp priced, STIRT Weekly, 14 Aug 2026). The market has rarely priced more than 25bp across two consecutive
  meetings for more than a day, so a ceiling near 25bp is the default (Citi, Global Asset Allocation, 21 Aug 2026).
- Forecast-meeting odds: convert counts to per-meeting odds. RBA 61% of hikes in 4 forecast months is 15.3% per forecast
  month against 39%/7 = 5.6% per other month, about 3:1; the ECB is at worst 1.6:1 (swapsball, 8 Mar 2018). The test is a
  Pearson chi-square against equal odds per meeting; it is rudimentary, so re-run it on current calendars.

### 6. Credibility diagnostics
- FOMC-day credibility read (intraday): 2y down 6-10bp, 10y up 4-6bp, 5y inflation swap up about 5bp, DXY down, gold up,
  equities up = the market doubts the hawkish message (Citi, Global Macro Strategy: The Messi Theory, 31 Jul 2026).
- Nominal = real + breakeven. Since the war began, 10y nominal rose about 70bp with breakevens roughly unchanged, so the
  move was real yields (FT Alphaville, 19 Aug 2026). A real-yield move is not evidence of lost inflation credibility.
- 5y5y breakeven: the distance from target is the credibility gauge. A falling 5y5y in a front-loaded inflation shock is
  read as the bank taking action, not weak growth (JWS Macro, Global Rates Outlook #4, 8 Apr 2026). This is a contested
  view; cross-check against the 5y and the realised path before using it.
- Anchoring gauge: the standard deviation of daily changes in the 10y instantaneous forward over a year. Lower means
  better-anchored expectations (King, 2005).
- Guidance removal raises term premium: a long-end sell-off after reduced guidance took the 30y to its highest since
  2007 (FT, 6 Aug 2026). The source reads it as a reaction-function uncertainty premium. Expect persistent tail pricing
  of hikes or cuts.
- An inflation surprise index turning negative has preceded front-end yield peaks (Citi, FX Forecasts, 20 Aug 2026).
- Curve read: an inverted 2s10s means tight policy in the market's mind (JWS, 21 Jun 2026). A belly-led bear steepener
  (2s5s) "is incredibly rare if you were truly above neutral". Target 2s5s10s fly to zero as a neutral signal (JWS,
  7 Jun 2026). The fly is `2*y5 - y2 - y10`; positive means the belly is cheap.

### 7. Non-rate levers (escalation ladder)
Order matters. Banks move from the cheapest lever to the costliest.
- ECB: (1) verbal guidance, then the deposit-rate path, for tight conditions; (2) balance sheet only for moves
  disorderly in speed or size; (3) fine-tuning QT is a high bar; (4) new LTROs or a structural portfolio unlikely
  (banks would need about 40bn euros a month more); (5) TPI for disorderly unwarranted spread moves, with corrective
  action expected; (6) a possible long-end tool (BofA, Fog of war, 2 Oct 2026). The ECB acts on "disorderly", by its
  own higher standard. Do not position for early support.
- Fed: IORB is the main tool; ON RRP is the floor; SRF is a soft ceiling for EFFR, not for repo (Perli, NY Fed, 12 Nov 2024).
  In-band technical adjustments came when EFFR sat within 5bp of the top (IORB cut, spring 2018) or when rates risked
  falling toward zero (RRP +5bp, Jun 2021) (Barclays, Jan 2025). Theory says QT should end when the reserve-demand
  elasticity is slightly negative and statistically different from zero; it sat near zero in late 2024 (Barclays, Jan 2025).
  Balance-sheet detail belongs to `stir-central-bank-balance-sheet-and-reserves`.
- BoJ: yen defence is linked to back-end policy. Yield-curve control comeback fears undo FX intervention. "The price to
  pay for back-end intervention is a weaker currency" (Citi, Global Asset Allocation, 21 Aug 2026).
- BoC: overnight repo is the main tool against CORRA pressure, usually triggered when CORRA settles 5bp above target
  (Goldman Sachs, Global Rates Trader, 2 Oct 2026).

### 8. FX intervention as part of the reaction function
Applies to JPY (MoF with US Treasury), CHF (SNB), and USD (Treasury with NY Fed). Full detail in
`references/cb-playbooks.md`. Core rules:
- Trigger: a 2-sigma move of JPY REER from its 5-year average. Concerted G7 interventions tended to turn the long-term
  trend when it occurred (Citi, Global FX: Twelve questions, 29 Jan 2026). Plot the band before you trade a level.
- Level: intervention likely near USDJPY 160; above 162, Citi puts the probability over 50% (Citi, Japan FX, 13/14 Aug 2026).
- Rule: no more than three rounds in six months, each at most three trading days. Do not sell JPY on the assumption that
  no intervention follows day three; it can trigger a fast reversal (Citi, Japan FX, 4 Aug 2026).
- Capacity: about 30trn yen originally estimated; 25.5trn used by Jul 2026; about 10.5trn more under a 36trn practical
  limit (Citi, Global FX Strategy, 3 Aug 2026). Constraint is political will more than balance sheet.
- Intervention can pull hikes forward and turn the BoJ into a reaction-function regime change. Treat "a September hike is
  necessary if not sufficient" as the signal to watch (Citi, Weekly Macro Brief, 8 Aug 2026).
- Pitfall: if the market prices JPY the way it prices Fed and ECB pricing, with consecutive hikes, that is the policy-error
  risk (Citi, Japan Rates Weekly, 2 Oct 2026).

### 9. Leadership and framework change playbook
1. Decompose the event into a credibility component and a path component. A new chair's first meeting can carry both: a
   credibility-premium unwind (long USD, flatter twist, real yields up, breakevens down) and a repricing of the path
   (JWS Macro, Central Casting #6.1, 21 Jun 2026).
2. Credibility test: a higher USD with lower 5y5y real yield, the reverse of the usual relation, is "classic EM-type
   credibility price action" (JWS, 21 Jun 2026).
3. Count voters, not dots. Watch dissents and the marginal vote. Note voter rotations with dates.
4. Map each candidate's likely reaction to the curve. A candidate expected to cut or lean dovish tends to steepen the
   curve and weaken USD; one leaning hawkish tends to flatten it and strengthen USD (JWS Macro, USD and Global Rates
   Thoughts #2, 13 Nov 2025). Treat these as conditional on the candidate's stated framework, not on past behaviour.
5. Expect a catalyst-driven move before the first meeting. Attach an expiry to any "asymmetric" view and drop it when
   the catalyst fails (Citi, FX Forecasts, 20 Aug 2026).
6. A flattener or long USD on a new chair bets that the chair stays as first seen. Do not bet a year's pattern holds.

### 10. Cycle timing and trade rules (US reference; see worked examples sections 8-9)
- Hiking cycles (post-1986 median): 12 months, 8 hikes, median 8 months to the first cut. Easing: 8 months, 4 cuts,
  median 14 months to the first hike (Willer and Saunders, 2026).
- Pay the 2y about 3 months before the first hike; receive the 2y around the last hike; press receivers about 3 months
  before the first cut; pay into the last cut only if a 6m-plus hold is expected. Stay paid through pauses.
- Curve by phase: hiking bear-flattens and easing bull-steepens. A regression of daily 10y yield changes on the 5th SOFR
  futures contract (about a year out) gave beta 0.9 and R-squared just under 91% (Mar 2022 to Mar 2025; Willer and Saunders,
  2026), so the 10y moves less than the front end: hikes bear-flatten, cuts bull-steepen. Directionality changes:
  on hold, the long end drives the curve; approaching hikes, bear-flattening; easing onset, bull-steepening (J.P. Morgan,
  A primer on Conditional Trades, 26 May 2016).
- Look-ahead warning: first-hike and last-hike dates are known only after the fact (the dating rule needs the next quarter
  of data, so cycle statistics use post-1986 cycles only). These timings describe what to do if you hold the view; they are
  not a real-time signal. Fewer than 25 events, overlapping 3m and 6m windows and no transaction costs mean the hit rates are
  indicative only.
- Other cycle rules (Willer and Saunders, 2026): score an FOMC meeting by the 2y move, receiving (paying) after a move of at
  least 2 standard deviations of the trailing month; the first pause meeting is a better entry than the last cut; the Fed
  usually cuts more than priced in hard landings but delivers more than priced in actual hiking cycles; being on hold for
  six months is usually the same as being done; the Fed put starts near a 25% S&P 500 drawdown (about 20% if inflation is
  low) and moves later when inflation is high.

## Worked examples
Full numbers and recomputations live in [references/worked-examples.md](references/worked-examples.md).
- **Taylor anchor.** r* 2, pi 3.0, gap +1.0 gives 6.0%. Off-target, so the weights are tested.
- **Hike probability.** 10bp of the meeting-period rate over the current rate is 40% of a 25bp step. The ECB 21bp for a
  September hike is 84% (Citi, STIRT Weekly, 7 Aug 2026).
- **Front-end screen.** FF6 minus FF1 of -20bp meets the -12.5bp screen. In May 2019 the screen (-16bp) led to -75bp over
  6 months. In Mar 2023 (-34bp) it failed: fed funds rose 75bp over 6 months (Willer and Saunders, 2026).
- **Fly.** 2y 2.0%, 5y 2.6%, 10y 3.0%: 2*2.6 - 2.0 - 3.0 = +20bp, belly cheap.
- **Energy shock.** Brent from 70 to 90 in a week; Central Europe (CZ, HU, PL) 1y1y rates +60 to +100bp in a week. A $10 Brent move is about 30bp on
  near-term euro-area HICP (JWS Macro, 8 Mar 2026).
- **BoJ grid.** Market 2y OIS 194bp. At a 225 terminal, Oct-start every-meeting is 210bp and Oct-quarterly is 201bp (Citi,
  Japan Rates Weekly, 2 Oct 2026). The grid, not the source's summary sentence, is the reference.
- **Jackson Hole.** One standard deviation of the 2y move on chair speeches is about 5.5bp. Moves of 9-11bp happened in
  2019, 2024 and 2025 (J.P. Morgan, 21 Aug 2026).

## Signals & interpretation
- Hike or cut priced above the rule's bound (step 2) with no guidance validating it: the trade is the gap, not the level.
  Size it at the gap in bp per meeting, and state the bank's next forecast meeting as the catalyst.
- Cut signal: FF6 minus FF1 at or below -12.5bp. Use it as a screen; require a second confirmation (inversion, real-rate
  rise, or dovish dissent) before a cut trade, because the screen failed in 2023.
- Inversion signal: a front-end inversion of at least 12.5bp (6m2s, 2s5s) preceded cuts most often. For 2s5s the average
  time to the first cut was about 7.7 months in the source's sample. Receiving the 10y after a 6m2s inversion of at
  least 12.5bp returned +1.71% at 3m with a 70% hit rate (Willer and Saunders, 2026). Small samples; check costs.
- Neutral: when the market-implied r* sits at or near the bank's own neutral, a further hike needs a reaction-function
  reason, not just higher pricing.
- Regime change: a change in directionality (bear-flattening to bull-steepening) at the same time as a shift in the
  reaction function is the signal to move the curve trade, not just the front-end trade.
- Dovish-reaction confirmations: core and robust measures falling for two prints; a dovish dissent; front-end pricing
  easing while the 5y5y stays stable; the curve bull-steepening on the day.
- Hawkish-reaction confirmations: two or more dissents in the hawkish direction (the BoJ heuristic); a rising 5y5y with a
  stable or falling real yield; pricing still below about 80% of a hike until the bank communicates directly (Citi,
  Global Macro Strategy, 13 Aug 2026).

## Pitfalls
- Confusing a forecast with the reaction function. Taylor-type rules explain past decisions better than they forecast.
- Reading forwards as the modal path. A forward is expectations plus premium, and it embeds convexity and skew.
- Meeting probabilities that do not add up. They are not joint probabilities. Check the sum across meetings.
- Trusting a single core gauge. Robust cores lag by 6-8 months in persistent shocks, and some core moves are measurement
  artefacts (asset-linked fees, methodology revisions the BEA later changes). Check the composition before trading.
- Using a regime from one period on another. Inflation persistence depends on the regime; long histories mislead.
  Changes in models and parameters matter as much as changes in inputs (Duering, 2021).
- Assuming a bank cannot move because consensus says so. "Reaction-function risk" is real. Hedge-fund shorts on ECB-hike
  optionality were stopped out during the March 2026 energy repricing (JWS Macro, 8 Mar 2026).
- Expecting an early balance-sheet backstop. Banks act on disorderly moves by their own standard.
- Ignoring the source's date. Levels from 2026 notes, including Fed and BoJ paths, are snapshots. Re-read the state from
  the canonical tables.
- Forgetting the intervention ladder. Intervention buys time; it does not fix fundamentals (BofA, FX Primer, 8 Jul 2024).
- Treating an FX-intervention pause as a policy shift. Post-intervention dollar-funding softness fades within 1-2 weeks (Citi, STIRT
  Weekly, 7 Aug 2026), and a rebound risk to 160-162 remains after intervention ends (Citi, Japan FX, 4 Aug 2026).
- Calling a chair's stance from one speech. A chair who avoids guidance should produce a muted reaction, as in the Greenspan
  years (J.P. Morgan, 21 Aug 2026).
- Taking consensus crowding for a free signal. A bigger-than-expected hawkish reaction to a "receive the CB" trade signals
  crowding (Nordea, 19 Jun 2025).

## Output
Produce a reaction-function card for each bank in scope, plus the trade read. Keep numbers in bp or percent, and date every
level.

| Field | Content |
|---|---|
| Bank and date | CB, as-of date, next meeting, forecast meeting flag |
| Regime and starting point | hiking / hold / easing / pre-turn / transition / shock; price-vs-quantity score |
| Rule anchor | Taylor-type rate and bound, r* (market and bank), real policy rate |
| Market path | meeting-by-meeting bp moves and probabilities, from the strip |
| Gap | market minus rule, bp per meeting; direction |
| Mechanics | votes, dissents, forecast-meeting status, back-to-back risk |
| Credibility | 5y5y, FOMC-day or meeting-day read, real vs breakeven split |
| Levers and FX | ladder step in use; intervention levels and REER band |
| Trade read | expression (front meeting, belly, curve, cross-CB), catalyst date, expiry, what would make it wrong |
| Hand-off | `rv-trade-idea-writeup` for the note, `rv-devils-advocate` for the kill case |

Keep the card under about 25 lines per bank. Write each trade read as one sentence, for example: "Receive the next BoC
meeting if core trim and median stay at or below 2% and the strip still prices a hike; invalidated by a hot core print."

## Scripts
- [`scripts/reaction_rules.py`](scripts/reaction_rules.py): Taylor-type rule anchor, meeting-strip move and probability,
  FF6-FF1 cut screen, curve inversion test, post-meeting rate from a monthly-average future, and the 2s5s10s fly. `python -I scripts/reaction_rules.py --help`.
  `python -I scripts/reaction_rules.py --selftest` checks the off-equilibrium Taylor case (6.0) and the 40% hike-probability case.
  `python -I scripts/reaction_rules.py strip --csv <meetings.csv> --current <pct>` reads `meeting_date,implied_avg_rate_pct`.

## Related skills
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): fits the meeting path and probabilities that this skill reads against a rule.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): reserve demand, QT end, and balance-sheet levers in detail.
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): hawk-dove scoring of speeches, as a cross-check on the path.
- [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md): energy pass-through and inflation methodology behind the starting-point read.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro-factor fair values, including the money-based cross-check.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event pricing and data-release risk around meetings.
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): term premium and issuance when the reaction function is uncertain.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): scenario trees for shock-led regimes and terminal ranges.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): splitting yields into expected path and term premium.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): the curve trades that express a regime change.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): ECB fragmentation and periphery spreads.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): index, day-count and meeting conventions per market.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): where the trade read goes.
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): kill criteria for a reaction-function trade.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used in Inputs.
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): geopolitical channels and fade/follow rules.
- [macro-technical-analysis](../macro-technical-analysis/SKILL.md): trend, momentum and technical timing.

## References
- Mervyn King, Bank of England - "Monetary Policy: Practice Ahead of Theory" (Mais Lecture, 17 May 2005): reaction-function
  framing, porcupine chart, two-year heuristic, anchoring gauge.
- Dirk Willer and Alex Saunders - Trading Global Macro Markets (Wiley Finance, 2026): cycle medians, FF6-FF1 and inversion
  tables, Fed put, BoJ structural lag, soft-landing cycles.
- Alexander Duering - Fixed Income Trading and Risk Management (Wiley, 2021): Taylor-type formula, policy-path method,
  inflation persistence, control hierarchy, forward-guidance taxonomy.
- Joseph Abate, Barclays - US short interest rate primer (Jan 2025): in-band technical adjustments, reserve-demand
  elasticity, QT-end logic.
- Tomohisa Fujiki, Citi Research - Japan Rates Weekly (2 Oct and 14 Aug 2026): BoJ 2y OIS grid, hike probability, terminal and
  feasibility of one hike a quarter.
- Citi Research - Global Asset Allocation: House Views, August 2026 (21 Aug 2026): BoJ back-to-back pricing ceiling, back-end
  intervention trade-off.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): ECB 2011 guidance case,
  Fed dots from 2012, meeting mechanics.
- BofA Global Research - Japan Rates Basics (24 Apr 2023): YCC-era BoJ operations.
- JWS Macro (Substack) - USD Rates and Fed outlook #1 (21 Aug 2025): Fed neutral range and reaction heuristics.
- Citi Research - Japan and Global FX notes on JPY intervention (29 Jan, 3 Aug, 4 Aug and 13/14 Aug 2026): episode list,
  REER 2-sigma band, IMF rule, capacity, mechanics. Also Citi Markets, Weekly Macro Brief (8 Aug 2026): the three-step yen
  framework and the September-hike condition.
- Citi Research - Japan Economics: Regime shift in BoJ policy (7 Aug 2026): intervention-driven reaction-function shift.
- Citi Research - Global Macro Strategy: The Messi Theory of Interest Rates (31 Jul 2026): FOMC-day credibility read, no-guidance regime.
- Citi Research - Global Macro Strategy, Views and Trade Ideas (7 and 13 Aug 2026): BoJ dissent heuristic and the 80% pricing cap.
- Citi Markets (Sales and Trading) - STIRT Weekly (7, 14 and 21 Aug 2026): meeting-window pricing, back-to-back logic, dovish-reaction
  rule. Note: sales and trading commentary, not research.
- Citi Research - European Rates Weekly: What to do about OATs? (1 Oct 2026): ECB levers, fragmentation monitor.
- Citi Research - Foreign Exchange Forecasts: August 2026 (20 Aug 2026): expiry on asymmetric views, inflation surprise index.
- BofA Global Research - Global Economic Weekly "The fog of war" and Global Rates Weekly "Start of rates bite" (both 2 Oct 2026):
  ECB escalation ladder and pain threshold; Taylor-type grid and real-rate peak range.
- Citi Research - Canada Economics Weekly (13 and 21 Aug 2026) and Nordic Economics Flash (20 Aug 2026): BoC pricing gauge,
  Riksbank path read as a hike probability.
- BofA Global Research - FX Primer: G10 intervention (8 Jul 2024): who decides, funding, capacity, SNB.
- BofA Global Research - Global Policy Implementation, summer 2025 edition (9 Jul 2025): floor vs corridor, leaky-floor rule, forecast months.
- J.P. Morgan North America Economic Research - Lags in robust PCE cores (US Focus, 13 Aug 2026) and US Weekly Prospects
  (14 and 21 Aug 2026): robust-core lags, minutes quantifiers, Jackson Hole reaction.
- JWS Macro (Substack) - Global Rates Outlook #5: Price Vs. Quantity (10 May 2026): price-vs-quantity framework, Fed triggers.
- JWS Macro (Substack) - Global Rates Outlook #4 (8 Apr 2026) and #6: Kick-off for a Global Tightening Cycle (7 Jun 2026):
  5y5y as a credibility gauge; neutral mid, doom loop, fade rules.
- JWS Macro (Substack) - #3: Iran and Front End Rates (8 Mar 2026): starting-point reaction function, oil rule.
- JWS Macro (Substack) - Central Casting #6.1: The Fed Credibility Trade (21 Jun 2026): voter arithmetic, credibility price action.
- Nordea Markets - EUR rates: Pushing back (17 Jan 2024), and Risk/reward favours receiving ECB meetings (19 Jun 2025):
  market-implied r-star, number-beats-timing, consensus crowding.
- Perli, Federal Reserve Bank of New York - Facing Quarter-End Pressures (speech, 12 Nov 2024): floor system, SRF as a ceiling for EFFR.
- Financial Times - Warsh to stick with lean Fed messaging (6 Aug 2026), and Alphaville on the nominal and real split (19 Aug 2026).
- Salomon Brothers (Antti Ilmanen) - Understanding the Yield Curve, Part 2: Market's Rate Expectations and Forward Rates (Jun 1995): forwards vs expectations, risk premium.
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch and Dee, 2022): forward mean vs mode, transmission.
- Bruce Tuckman and Angel Serrat - Fixed Income Securities (4th ed., Wiley, 2022): Fed floor system, ECB QE constraints.
- JWS Macro (Substack) - Global Rates Update #7: Same North Star, Worse Weather (19 Jul 2026): hike triggers, MPC vote drift, bimodal pricing.
- Citi Research - US Economics Weekly: Main Street versus Wall Street (2 Oct 2026): Fed-speak repricing of October hike pricing.
- J.P. Morgan Global Economic Research - Welcome to the Machine: NLP of central bank speak (26 Apr 2023): speech-to-statement coefficients.
- J.P. Morgan - Federal Reserve NLP Report: Jerome Powell (22 Aug 2025): 2025 framework review summary.
- BofA Global Research - US Rates Watch: Fed Negative Equity: No Tightening Limit (24 Feb 2022): Fed net-interest-margin breakeven.
- Conks (Substack, Plumbing Notes) - Shadow Cash (23 Jul 2025): reserve-ratio zones (source-specific cut-offs).
- Goldman Sachs - Global Rates Trader: Reaching Limits (2 Oct 2026): BoC CORRA trigger, RBA revealed preference.
- J.P. Morgan - A primer on Conditional Trades (26 May 2016): reaction-regime directionality.
- Hudson Bay Research - A return to monetarism? (Jul 2026): money-based price-gap cross-check.
- swapsball.net (Wayback archive) - Central bank decisions and inflation forecasts (8 Mar 2018): forecast-meeting effect.
- Taylor, J. B. (1993) "Discretion versus policy rules in practice", Carnegie-Rochester Conference Series on Public Policy 39 (external).
- Clarida, Gali and Gertler (2000) "Monetary Policy Rules and Macroeconomic Stability: Evidence and Some Theory", Quarterly Journal of Economics 115 (external).
