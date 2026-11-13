---
name: stir-policy-pricing-whats-priced-in
description: 'Builds the meeting-by-meeting implied policy path ("what''s priced in") for G10 central banks from meeting-dated OIS, 1M/3M RFR futures and fed-funds-average contracts, converts steps to per-meeting hike/cut probabilities and cumulative bp, compares the priced path with house paths, hike-count fair value, option and prediction-market distributions, and finds policy-pricing RV (meeting spreads, meeting flies, cross-CB, front-loading vs terminal). Use when asked what is priced in, market-implied or OIS-implied path, hike or cut probability/odds, how many hikes or cuts by year-end, FOMC/ECB/BoE/BoJ/BoC/RBA/RBNZ/SNB/Riksbank/Norges meeting pricing, stub, cumulative bp to year-end, MPC-dated or meeting-dated OIS, receive/pay a meeting, meeting spread or fly, terminal rate, fading hike or cut premium, year-end turn premium, priced vs delivered. Rule-based fair path and votes: macro-central-bank-reaction-functions.'
---

# What's priced in: meeting-date policy path, probabilities and policy-pricing RV

Short-dated rate instruments are bets on the central bank's next few decisions. Because an overnight rate only
changes on effective dates, the front end is a staircase: rate in force today (the stub), then one jump per meeting.
This skill extracts that staircase from market prices, reads it as per-meeting steps and probabilities, normalises
it across the ten G10 banks, tests it against a view (house path, hike-count distribution, option or prediction-market
distribution) and turns gaps into trades. The path is a risk-neutral, probability-weighted mean that includes a risk
premium: a forward is a break-even, not a forecast.

## When to use
- "What is priced for the Fed/ECB/BoE/BoJ/BoC/RBA/RBNZ/SNB/Riksbank/Norges, meeting by meeting? How many hikes by year-end?"
- Convert OIS, futures or average contracts into a hike/cut probability for a named meeting.
- Build the standard G10 table: implied rate, step, cumulative bp, change on day and week.
- Is a meeting, a meeting pair or the terminal rate rich or cheap versus a view? Which meeting to receive or pay?
- Meeting spreads, meeting flies, cross-central-bank spreads, fading hike or cut premium, year-end turn premium.
- Cross-check of "priced vs delivered" and cycle-timing rules for 2y positioning.

## Inputs (data-agnostic)
Schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Meeting calendar with effective dates | `cb_meetings` | per CB, next ~12m firm, 2nd year provisional | use `effective_date` when it differs from `meeting_date`; moved meetings have a new row |
| Policy-rate and RFR fixings (stub, realised days in the current averaging window) | `rate_fixings` | daily, last 60d | policy decisions are rows with `fixing_date` = effective date |
| Meeting-dated OIS (start = ISO meeting date) or par OIS by tenor | `curve_par` (`start` ISO date) | daily snap | preferred input: isolates policy |
| 1M-average and 3M RFR futures prices | `stir_quotes` + `fut_static` (`ref_start_date`, `ref_end_date`, `ref_method`) | daily settle, front 8-12 contracts | rate = 100 - price; settle snaps only |
| Step-meeting curve nodes (optional) | `curve_zero` (`interpolation = step_meeting`) | daily | |
| Option surface for distributions | `opt_quotes`, `vol_surface` | daily | hand off to [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md) |
| Prediction-market probabilities | `events_probs` | daily | `venue = implied_ois` rows hold curve-implied probabilities |
| House / consensus policy path | user supplied | per CB, per horizon | never invent; ask the user |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values. Per-market bases and
effective-date rules are in [references/g10_cases_and_tables.md](references/g10_cases_and_tables.md); fitting detail in
[references/path_fitting.md](references/path_fitting.md).

## Method

### 1. Fix the base and the dates for each central bank (before any arithmetic)
- Path = expected OVERNIGHT RFR, not the policy rate. Euro short-rate and SONIA trade a few bp off the policy rate
  (euro ~6-10bp below the deposit rate under excess liquidity; SONIA 1-2bp from Bank Rate). Quote steps in bp so the
  spread cancels, and add it back only when you need the policy-rate level.
- Base ("stub") differs by bank: Fed = effective fed funds, not the target-range mid; ECB = last fixing or prior
  maintenance-period average; BoE = SONIA fixing; BoC = effective overnight (6m forward minus effective is the quick
  gauge). Normalise before comparing banks (Nordea Markets, EUR Rates Flash, 5 Feb 2020).
- Use EFFECTIVE dates as step nodes: the day after the meeting (Fed), Wednesday after (ECB), publication date (BoE),
  per-meeting rule (BoJ: new rate from the start of the reserve period). A spot OIS maturing on a meeting date has no
  exposure to that scheduled meeting, only to an inter-meeting move (Citi Research, US Rates Weekly: Learning on the job, 2 Aug 2019).
- Check table headers against the actual stub (one published RBNZ table had a 2.25% header and a 2.500% stub).
- Strip known non-policy effects: year-end and quarter-end turns, Japan 1-April, tax-date funding spikes. Use OIS, not
  IBOR-linked futures, for probabilities; a fixed 10-15bp IBOR-OIS assumption is wrong.

### 2. Build the path (steps by effective date)
Preferred order, most direct first:
1. **Meeting-dated OIS** (MPC-/FOMC-/ECB-dated): the forward OIS for the period starting at each effective date is the
   expected overnight rate in that period. `step_k = F_k - F_{k-1}`, `cum_k = F_k - stub`, `F_0 = stub`. Use
   backward-flat forwards with nodes on effective dates. GBP bootstrap check (Deriscope, GBP Sonia case, 18 Feb 2024):
   overnight 2.9248% to 14-Dec-2022 then 3.5029% = 57.8bp December hike.
2. **Average-rate futures (1M averages, fed-funds style).** Averages are linear in the steps, so solve exactly. Month with
   no meeting after a meeting month: read the post-meeting rate directly. With a meeting inside the month and `d_pre`,
   `d_post` calendar days either side of the effective date: `F_month = (d_pre f_pre + d_post f_post)/d_total`. Chain forward
   (Tuckman & Serrat, Fixed Income Securities 4th ed., 2022). When several meetings or a turn sit in the same windows,
   write every contract as day-weighted steps and solve: `scripts/meeting_path.py fit`.
3. **3M compounded futures**: use as a constraint, not a bootstrap input: 8 meetings per year but 4 contracts, so the
   system is under-identified. Fit with a smoothness or ridge penalty; do not read back-contract noise as policy reversals.
   Use 8 (small markets) to 12 (liquid markets) IMM contracts; avoid the 6th, 7th, 10th, 11th and 14th (roll and leverage effects).
4. **Hybrid beyond ~6-12 months**: meeting dates are firm for ~1y, provisional for year 2, estimated for year 3; instruments
   thin out after ~3y. Steps at the front, smooth spline behind ([fi-curve-construction](../fi-curve-construction/SKILL.md)).

Defaults: arithmetic averaging on calendar days with last-business-day carry for weekends; horizon cut-off 183 days for jumps
(far meetings and far contracts are unreliable); ridge 1e-6 on jumps (resolves under-identified meetings with a minimum-norm
split, a stand-in for policy gradualism); flag meetings with no post-meeting days in any contract as unidentified rather
than reporting a number. Compounded 3M contracts are treated as averages, which overstates their rate by about r^2 T/2: ~0.1bp at 1%, ~3bp at 5%
(1M windows: ~1bp at 5%); net it off the 3M targets when comparable to the bid-offer. Contracts starting beyond the horizon are dropped
(they would be explained by unmodelled meetings and bias the level). Fit only one reference index at a time (SOFR, not EFFR, futures).
Details, sensitivities and derivations: [references/path_fitting.md](references/path_fitting.md).

### 3. Steps to probabilities (per meeting, in isolation)
With move size `s` (25bp; 10bp in the old negative-rate euro regime; check the central bank's actual step) and `step = (k + frac) s`:
`P(k+1 moves) = frac`, `P(k moves) = 1 - frac`, same sign as the step (Lehman Brothers, The Short-End of the Curve, 10 Jul 2007).
- 10bp priced = 40% of a 25bp hike. 37.5bp priced = 50% of 50bp, 50% of 25bp. Expected moves = `step/s`.
- For meeting-dated OIS the cumulative form is `P(hike by meeting) = (OIS - base)/25bp` (Aikin, Welcome to STIR futures blog, 30 Jan 2014).
- Treat |p| < 5% (and negatives, which come from noise and basis) as zero.
- These are not joint probabilities. 50%/50% at two consecutive meetings usually means one hike with uncertain timing, not
  a 25% chance of two. Read probabilities across a block of meetings (step 6), not meeting by meeting.
- The mapping sells tail risk and cannot see bimodality: 115bp of cuts priced is equally "90% unchanged, 10% to a very low
  rate" (Convexity Maven, The Big 'O', 22 Aug 2023). For the distribution use options (call-spread digitals,
  normal-mixture or Breeden-Litzenberger densities) or prediction-market thresholds, and treat both as risk-neutral.
- Fed funds average futures give only a mean. SOFR options give a distribution but need a SOFR-to-target assumption that
  can materially reduce accuracy (Morgan Stanley Research, Kalshi Markets as Macro Signals, 18 Aug 2026).
- A central bank's own average-rate path gives a probability the same way: a rise of less than one full step over a quarter means a
  hike probability below 100% (Riksbank June path 1.75 -> 1.76/1.82/1.89 quarterly averages implied < 50% for Sep-Dec; Citi Research, Nordic Economics Flash, 20 Aug 2026).
- Two consecutive quarterly 3M futures differ by the bp priced over that quarter (a 25bp gap = one cut priced); read these spreads as steps (Conks, Plumbing Notes, 15 Mar 2025).

### 4. Adjust the raw path before judging it
- Risk premium: forwards include a premium that grows with horizon (futures-term minus realised compounded EFFR, 2000-2019
  mean/sd: 1M 1.3/8.0bp, 3M 4.4/15.6, 6M 10.5/28.3; crisis 6M 31.0) (Heitfield & Park, FEDS 2019-014, Feb 2019). Inside
  3m treat it as small; beyond 6m, net it off or widen the fair-value band. Forwards at least get the direction of the front end right (use a weighted average of spot and forward as the forecast), while the long end is an inverse indicator; at end-1994 surveys expected ~100bp of hikes against ~200bp in forwards, and the 1995 rally was largely the premium collapsing (Salomon Brothers, Understanding the Yield Curve, Parts 2 and 6, 1995).
- Convexity: futures versus FRA/OIS ([stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md)) matters beyond the first few contracts.
- In-period contracts are sticky: compute the unknown part from known fixings; do not treat as a normal forward.
- Terminal and term-rate arithmetic: an X-year rate is roughly the average of the forward overnight path (24 monthly forwards
  for 2y). Near-term timing and pace dominate 2-3y; the terminal level dominates 4y+. A flat front end can hide cut
  expectations offset by term premium.

### 5. Compare the priced path with a view
Tabulate for each bank at fixed horizons (end-quarter, year-end, 6m, 12m, 24m): priced cumulative bp, house cumulative bp,
gap. Then:
- **Discrete hike-count fair value**: `E[bp] = s * sum_n n P(n)` over a subjective distribution of moves in a block of
  meetings. Once one hike is near-certain, P(2) can exceed P(0), so the fair cumulative for a pair is above one hike.
  Illustrative: P(0,1,2 hikes) = 15/55/30% gives 28.75bp for a 25bp-step pair (Citi Markets, STIRT Weekly: You Shall Not Pass, 14 Aug 2026,
  made the same argument: 25bp priced for Sep+Oct versus ~28bp fair).
- **Scenario grid** for a 2y OIS: timing of the next move x pace (each meeting, quarterly, every third) x terminal rate; shade cells
  >= 5bp from market. JPY example: with a 2y OIS at 194bp, every-meeting pace from October gives 169/190/210/228bp for terminal
  175/200/225/250bp, (Citi Research, Japan Rates Weekly, 2 Oct 2026; the note says the 2y rises only if terminal > 225bp). Reading the full grid (our reading): no cell with terminal <= 200bp beats 194, and at 225bp only Oct every-meeting 210, Oct quarterly 201 and Dec every-meeting 204 are >= 5bp above it (other 225bp cells 179-198).
- **Probability-weighted regime value** of any curve metric: `sum_r P(r) x metric_r` (a 1y-forward 5s10s30s fly at 9%x6 +
  21%x10 + 70%x24 = 19bp versus 48bp market) (Citi, US Rates Trade Recommendation: Flying Too High, 20 Dec 2010).
- **Policy scenario overlay** (base, late/slow/high, early/fast/low) against the market daily; "the number of cuts matters more
  than the timing of the first" (Nordea Markets, EUR rates: Pushing back, 17 Jan 2024).
- **Bayesian collapse**: when a new fact rules scenarios out, move their probability mass to the survivors and reset the range
  (BofA Securities, US Rates Watch: 10y rates and the Monty Hall problem, 6 Aug 2024).
- **Communication overlay**: a hawk-dove score adds information to current pricing; +10 score points ~ +10-14bp on the 1y
  and ~5-10pp on the next-meeting hike probability, effect larger when already in a cycle, breaks at the zero bound,
  regression error 30-40bp (J.P. Morgan, Welcome to the machine, 26 Apr 2023). See [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md).

### 6. Read the shape, not just the cumulative
1. Timing: when does the first move arrive (3 meetings out or 9)?
2. Smoothness: concentrated or spread across meetings? Look for humps (a step more than 2x its neighbours is a bet on a
   specific meeting, e.g. a new chair's first meeting, or a projections meeting).
3. Terminal: where does the cycle settle? Record the forward level where 1y1y crosses 5y5y as the market's neutral.
- Zones: front end = meeting risk; belly = disagreement (a leading belly means rising dispersion and vol); long end = term
  premium. Repricing types: cuts removed (front end leads the sell-off, can start a reaction-function shift, do not fade too
  early), terminal higher (belly matters), duration grab (long end rallies more) (Global Macro Method, STIR Application Process, 25 Feb 2026).
- Front-loading versus total: intervention or a hawkish speech can pull hikes earlier without raising the total (BoJ, Aug 2026):
  judge them separately.
- Dispersion check across banks: rank banks by likelihood of delivering the same priced amount and compare with the market
  ranking; pricing that meets or exceeds the maximum plausible move is "peak impact" and a fade candidate (Conks, Plumbing Notes, 11 Mar 2026).

### 7. Policy-pricing RV structures (conventions)
- Meeting spread A/B (A earlier) = `F_B - F_A` = cumulative bp priced between the two meetings. Pay A/B = pay the later leg,
  receive the earlier: gains if more is delivered in between. Bound the gap by what the bank can do: an ECB July gap was judged to
  live in 6-12bp (cap 12 because back-to-back moves are unlikely; floor 6 = roughly 1bp a week of roll-down) (JWS Macro, Global Rates Outlook #6, 7 Jun 2026).
- Meeting fly A/B/C = `2 F_B - F_A - F_C`. From the 14-Aug-2026 FOMC table (Sep 8.0, Oct 13.5, Dec 22.9) the Sep/Oct/Dec fly is
  2x13.5 - 8.0 - 22.9 = -3.9bp; Citi quoted -3 to -2.5bp when paying it (Citi Markets, Short End $waps: Fading the July Premium, 23 Jul 2026).
- Receive/pay a single meeting = enter at the meeting-dated OIS rate. Fade hike premium one meeting at a time (receive the next
  meeting, roll after it passes; worked for the BoE); never hold a fully priced meeting through the decision for carry, use an
  adjacent structure instead.
- Forecast-meeting effect: moves cluster in meetings with new projections (since Dec-1998, 61% of RBA hikes fell in the 4 statement months
  of an 11-meeting year = 3:1 odds per meeting; ECB 45% in 4 of 12 meetings). Fair value for adjacent meeting spreads follows these odds; the
  market under-prices hikes at non-forecast meetings (swapsball.net, Central bank decisions and inflation forecasts, 8 Mar 2018). The RBA and ECB
  now meet 8 times a year (4 with projections), so re-derive the odds: 61% over 4 of 8 meetings is only ~1.6:1.
- Cross-central-bank spreads: same meeting month across banks (e.g. BoE vs ECB in July near 0), 1y1y vs 1y1y regressions
  (SONIA vs euro: y = 1.09x + 1.4, R^2 95% over 5m), and likelihood ranking for the same priced amount.
- Turn-only package: weights from the average-contract closed form give pure year-end exposure with no meeting exposure
  (`references/path_fitting.md` section 3).
- Option overlay: compare a short straddle's breakevens with the settles for hike and no-change; if breakevens sit on the two
  discrete outcomes the event is priced as a binary, so "go micro" inside the range (meeting spreads, pins) rather than the wings.
- Risk by meeting, not DV01: size on CB01 (P&L per 1bp change in the expected rate at that meeting). For a pay-1M-OIS trade on
  one RBA meeting the DV01 overstated risk by 244% (Lehman 2007). Hedge pre-meeting days with the prior month's contract
  (stack), not the contract whose window straddles the meeting. A 1M/3M hedge is meeting-neutral only if recomputed from
  days-after-meeting fractions (3.1 May + 2.9 Apr 1M per 10 3M, not 3+3) (Huggins & Schaller, SOFR Futures and Options, 2022).

### 8. Priors on what markets and central banks do
- Forwards rarely price more than 70-80% of an eventual cycle: short outright forwards have limited upside; overshoot into
  "fully cooked" when banks, the central bank and the market feed each other.
- Priced cuts at the start of an easing cycle are usually smaller than delivered (hard landing); hikes priced outside a hiking
  cycle often do not come; inside one the Fed delivers more than priced (Willer & Saunders, Trading Global Macro Markets, 2026).
- BoJ: pricing seldom exceeds ~80% a week before a meeting without a leak or headline, and never held >25bp across back-to-back
  meetings for more than a day; two hawkish dissents preceded recent hikes. So receiving the second of two consecutive meetings is
  a cheap risk-off hedge, and paying the near meeting has capped payoff (Citi GMS, Aug 2026).
- Reaction risk: when pricing is hawkish beyond what the bank can validate (Riksbank, low inflation), reaction at the meeting is dovish.
- Variant perception: consensus outcomes are almost fully priced, so only a deviation from consensus moves the path; compare consensus with the priced step before the meeting (Aikin, STIR Futures, 2nd ed., 2012).
- Calendar: put low odds on a move at a meeting with only one CPI print behind it, and pick the meeting from the political and event calendar.

## Worked examples
All steps in bp unless stated. Further cases and tables: [references/g10_cases_and_tables.md](references/g10_cases_and_tables.md).

**A. Fed funds strip to a path (Tuckman & Serrat, Fixed Income Securities 4th ed., 17 Jan 2022).** Effective fed funds 0.08%; Feb
contract 0.095% with no meeting in February, so the rate after the January meeting is 0.095%: `p = (0.095-0.08)/0.25 = 6%` of a
25bp hike. April 0.355% is the rate after the March meeting. May contract 0.450% with the 4-May meeting effective 5 May (4 days
before, 27 after): `f_May = (31 x 0.450 - 4 x 0.355)/27 = 0.4641%`. `meeting_path.py` selftest reproduces 0.4641 from the four
contracts (its January probability is 5.9% because it also solves the level). Expected end-2022 EFFR moved from ~28bp (strip, 1 Oct
2021) to ~99.5bp (17 Jan 2022).

**B. Reading a G10 table (Citi Markets STIRT, G10 What's Priced In, 14 Aug 2026).** FOMC cumulative 8.0 / 13.5 / 22.9 / 27.4 for
Sep / Oct / Dec / Jan: steps 8.0, 5.5, 9.4, 4.5 -> P(Sep) = 8.0/25 = 32%, Dec carries the largest step (a projections meeting, 1.7-2.1x its neighbours). BoJ 20.0 / 26.6 / 40.3 /
50.4: steps 20.0, 6.6, 13.7, 10.1 -> P(Sep) = 80% (the empirical ceiling). Citi's reading: Sep 20bp is enough; Sep+Oct should be ~28bp
versus 25 priced in the note (26.6 in the table; once one hike is certain, two beat zero); Dec+Jan 23bp right; ~50bp after January "a bit rich" because more than
four hikes from Dec-26 to Dec-27 is less likely than two; no trade because the gap to fair value is small and there is no catalyst.

**C. Fade early-cut pricing (Nordea Markets, EUR rates: Pushing back, 17 Jan 2024).** ECB-dated euro short-rate table: Mar 3.859%
(-5.0 from last fix), Apr 3.695% (-21.8), Jun 3.382% (-52.7), Dec 2.490% (-141.6). March moved from about -15 to -4bp as cuts
were pushed back (first full cut priced for June); "add 10bp to every number for the implied deposit rate". Scenario end-points: base 2.25% (~215bp), late/slow/high
3% (~290), early/fast/low 1.5% (~140), market ~207. Trade: receive 1y2y/3y2y/5y2y 6s fly at -8bp, target -25, stop +5, to fade the
early-cut path while keeping a sub-2% end-point open. Carry/12m 79.2bp, 1y realised vol 46.5bp, carry/vol 1.70.

**D. Meeting risk is not DV01 (Lehman Brothers, The Short-End of the Curve, 10 Jul 2007).** RBA policy 6.25%; expected 2-May 6.36 (+11,
P = 44%), 6-Jun 6.43 (+7, 28%), 4-Jul 6.43 (0), 8-Aug 6.47 (+4, 16%). View: hike on 2 May -> pay 1M OIS, +14bp if hiked (25-11), -11bp
if not. Risk $100k at AUD/USD 0.8165 = AUD 122.5k over the 11bp loss -> CB01 = AUD 11,134 per bp (magnitude; negative for a payer); sized to CB01 the OIS notional is AUD 4.563bn;
the same position's DV01 is AUD 38,323, i.e. 3.44x, so DV01 sizing overstates the meeting risk by 244%. The script reproduces the probabilities.

**E. Strip a year-end premium (Citi Research, US Rates Weekly: Fixing the plumbing, 30 Sep 2019).** Market-implied year-end drop in
average funds rate -4.5bp versus the largest historical -2.65bp. Package long/short Nov/Dec/Jan/Feb average contracts at -55K : 155K :
-106K : 7K DV01 = 100K DV01 of year-end exposure and no FOMC exposure. Level +4.5bp, target +1.5, stop +6. Risk: a messy
quarter-end extrapolated to year-end.

## Signals & interpretation
Thresholds below are working defaults; where a number is a house default rather than from a source it is marked (default).
- **Probability materiality**: |p| < 5% = zero; p > 80-85% = "fully priced": do not run meeting-to-meeting risk ("fruitless"), use
  adjacent structures or fade the next meeting instead.
- **Edge to trade** (default): gap to fair value >= max(3bp, 2x bid-offer) for a single meeting or spread; >= 5bp for a 2y OIS
  scenario cell (Citi shading); fair-value bands of +-2bp are normal (BoJ Sep 16bp "about right, 15-19").
- **House-versus-market gap**: >= 10bp at a horizon = candidate (default); >= 25bp (one full move) = strong, but check the house
  forecaster's record and that the horizon contains a catalyst. Market tables lag 1-2 days.
- **Hump rule**: any step > 2x neighbouring steps (e.g. new-chair first meeting weighted like year-end) is a view on that meeting;
  trade it with meeting flies, underweighting the near leg (0.5x2x1 rather than 1x2x1) to cut front-meeting exposure.
- **Overshoot**: pricing at or above the maximum plausible move, or above 70-80% of an eventual cycle, favours fading, after
  consolidation rather than immediately. Fade zones from a deep value, not at fair value.
- **Cycle timing (US, post-1986)**: 2y returns turn poor ~3m before the first hike (pay ~2.5-3m ahead); stay paid through pauses;
  cover near the last hike; press receivers ~3m before the first cut (worst counter-trend sell-off 21bp, 2001); receive after a >= 2 s.d.
  FOMC-day 2y move. Best tactical pay: just before the first meeting the Fed sits out (a late-cycle pause is usually read as the end).
  Slope signal: 6th-month minus 1st-month fed-funds futures rate below -12.5bp (>= half a cut priced 6m out) preceded cuts or no hikes in 10 of 11 events, failed in Mar-2023
  (inflation > 5%) (Willer & Saunders, 2026). Samples are small (n < 25 for most).
- **Calibration of implied probabilities**: a single middling probability cannot be tested. A distribution-free bound needs
  N >= 1/(eps^2 delta) trials (eps = 0.1 on the +/-1 scale = 5pp on a hit rate, delta = 0.05 -> 2,000; very conservative, a normal approximation needs hundreds), far more than ~8 meetings a year per bank, so pool across banks and
  years and judge by a running betting test, not by one hit (Shafer & Vovk, Probability and Finance, 2001; the application is ours).
- **Confirmation**: step path vs option-implied modes; vs prediction-market mean inside ~100 days (they converge near the meeting);
  vs 1y1y inflation swaps (flat 1y1y while hikes are priced argues the central bank will anchor); vs 2y swap minus policy rate (average
  +62bp post-GFC; implied cuts = (spread gap)/25bp).

## Pitfalls
- Wrong base or date: policy rate vs RFR, target-range mid vs effective rate, meeting date vs effective date, stale table header.
- Reading probabilities as joint probabilities or as real-world odds (they are risk-neutral and carry premium and convexity).
- IBOR-linked futures for probabilities; fixed IBOR-OIS spread assumptions; ignoring year-end, 1-April and tax-date turns.
- Using the in-period futures contract as a plain forward; bootstrapping back contracts instead of fitting (noise looks like reversals).
- Jump models: unscheduled meetings (2001, 2008, Mar-2020) break them and they value every OTM option before the next meeting at zero;
  list inter-meeting moves as a main risk and stress against diffusion.
- Hedging a meeting with the contract whose window straddles it; sizing by DV01; trading a fully priced meeting for carry.
- Fading hikes or cuts at fair value; fading before consolidation; ignoring that a failure to cut can raise later-cut pricing
  (use bounded curve-shape expressions: receive the belly of a PC-neutral fly, halve size in high vol).
- Crowding: a consensus receive idea reverses sharply on one hawkish meeting; a book already "stacked with dovish Fed trades" should
  not add correlated risk. Positioning distorts cross-bank repricing betas in the first week of a shock.
- Methodology quirks (a core-PCE revision of 20-30bp, fee-driven PPI) move Fed pricing and are looked through; attach an expiry or
  catalyst to every skew or premium view.
- Small samples behind every timing rule; no transaction costs in the cited event studies. Taylor rules and money-based stance
  checks are cross-checks only (no out-of-sample edge).
- Published term rates (smoothed, pure-jump) are not the market path; they can embed a bias of ~0.5bp.

## Output
Return, per central bank requested (default all G10):
1. **Path table**: `cb | effective_date | implied_rate_pct | step_bp | cum_bp | p_move | p_low/n_low/p_high/n_high | d1d_bp | d1w_bp | identified`
   plus stub, base definition, date rule, instruments used and fit residual (max |resid| bp). Summary row: current fix and cumulative
   bp to end of year 1/2/3.
2. **View gap table**: `cb | horizon | priced_cum_bp | house_cum_bp | gap_bp | option_or_pm_mode | comment`.
3. **Candidate structures** ranked by edge versus fair value: single meeting, meeting spread, meeting fly, cross-bank spread, with
   level, fair-value band, CB01 sizing, carry/roll, catalyst/expiry, one invalidation condition, and what is already crowded.
4. **Flags**: unidentified meetings, humps, probabilities above 80%, caps (BoJ), bases that were normalised, data lag.
Then hand the shortlist to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and stress it with
[rv-devils-advocate](../rv-devils-advocate/SKILL.md). Label every number with its snap time and source table.

## Scripts
- [`scripts/meeting_path.py`](scripts/meeting_path.py): (a) `table`: meeting-dated OIS rates to step, cumulative and probability
  table; (b) `fit`: step-function fit of overnight forwards to futures averaging windows (`stir_quotes` + `fut_static` + `cb_meetings`
  + `rate_fixings`), ridge-regularised, unidentified meetings flagged; (c) `step_probabilities`, `expected_bp`, `bootstrap_next_rate`
  (Pulman recursion). `python scripts/meeting_path.py --help`. `--selftest` checks the Tuckman fed-funds example (f_May = 0.4641%),
  the Citi closed-form december step, the Pulman RBA probabilities, the Aikin MPC-dated probabilities and a random-path round trip.

## Related skills
- [fi-curve-construction](../fi-curve-construction/SKILL.md): step-meeting interpolation, turns, multi-curve inputs.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): RFR indices, day counts, meeting calendars, effective-date rules.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): futures spreads, flies and packs once the path is known.
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): meeting-outcome densities, skew and tails.
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures vs OIS adjustment before comparing paths.
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): compounding, reference periods, fixing ladders.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): effective rate vs target, turns, seasonals.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): why the overnight rate drifts inside the corridor.
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bills versus OIS when the path is uncertain.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): 1y1y, 2y1y and neutral-rate forwards.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): forwards as break-evens, roll in meeting trades.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): CB01 and meeting-bucket risk transforms.
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): why a bank should or should not validate the path.
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): hawk-dove overlay on pricing.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): prediction-market probabilities.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): scenario trees behind the house path.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): Taylor-rule and neutral-rate anchors for the terminal level.
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): updating scenario weights when a fact removes scenarios.
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): bank-bill/IBOR-OIS bases that are not policy.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): sizing meeting trades by risk, not notional.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): turns and calendar effects.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), [rv-devils-advocate](../rv-devils-advocate/SKILL.md): packaging and review.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): term-structure models and term premium.
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): geopolitical channels and fade/follow rules.
- [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md): energy-to-inflation pass-through and CPI nowcasts.

## References
- Huggins & Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): jump-process path, 1M/3M futures math, step fit vs bootstrap, meeting-neutral hedges, Term SOFR critique.
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets, 4th ed. (Wiley, 2022): fed-funds futures to meeting probabilities, stacking around a meeting, step vs spline.
- Heitfield & Park - Inferring Term Rates from SOFR Futures Prices (Federal Reserve Board, FEDS 2019-014, Feb 2019): step-function estimator, gradualism, futures-OIS gaps, risk premium by horizon.
- Lehman Brothers - The Short-End of the Curve (Chris Pulman, 10 Jul 2007): meeting-date OIS bootstrap, probability rule, CB01 vs DV01, RBA example.
- Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022), and Coding Interest Rates (c.2024): effective-date nodes, regularising meeting curves, ECB stepped curve, delay roll.
- Citi Markets (STIRT) - G10 What's Priced In (Dolega, 14 Aug 2026) and CitiFX Wire G10 What's Priced In (Purcell, mid-Aug 2026): table template and G10 meeting paths.
- Citi Markets (STIRT) - STIRT Weekly: You Shall Not Pass (14 Aug 2026), Tokyo, we have a problem (7 Aug 2026), Beam me up, Scotty (21 Aug 2026): hike-count fair value, meeting-spread levels, G10 views.
- Citi Research - US Rates Weekly: Fixing the plumbing (30 Sep 2019); Learning on the job (2 Aug 2019); The rocky road to a steeper curve (18 Jan 2019): year-end premium decomposition, stub OIS, inversion event study.
- Citi Markets - Short End $waps: Fading the July Premium (23 Jul 2026); Citi Research Global Macro tapas (7 Aug 2026), No inflation trouble (13 Aug 2026), Trade Ideas Radar (13 Aug 2026), House Views Aug 2026 (21 Aug 2026): meeting flies, BoJ caps, outcome log.
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): cycle dating, fed-funds-curve slope signal, delivered vs priced, 2y timing rules.
- Nordea Markets - EUR rates: Pushing back (Svendsen, 17 Jan 2024); EUR rates: Risk/reward favours receiving ECB meetings (19 Jun 2025); EUR Rates Flash (Vainikainen, 5 Feb 2020): ECB-dated tables, bases, scenario overlay.
- Aikin - Welcome to STIR futures blog, Interest rate change probabilities (30 Jan 2014), and STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed. (Harriman House, 2012): MPC-dated OIS probabilities, OIS vs IBOR, variant perception.
- Morgan Stanley Research - Kalshi Markets as Macro Signals: A Practical Guide to Prediction Market Pricing (18 Aug 2026): prediction-market PMF repair and accuracy.
- J.P. Morgan - Economic Activity Tracking (14 Aug 2026): house vs market path table; Cross currency basis 2H25 Outlook (5 Jun 2025): option-implied Fed weights; Welcome to the machine (26 Apr 2023) and Talk is Cheap (30 May 2024): rhetoric overlays; The long and short of it (3 Aug 2018): 70-80% rule.
- Ametrano, Bertocchi & Mazzocchi - Advanced Eonia Curve Calibration (SSRN, 5 Dec 2016): forward stub, turn removal, mixed interpolation.
- Deriscope - Yield Curve Building ... The GBP Sonia case (Rigopoulos, 18 Feb 2024): MPC-dated bootstrap and implied December-2022 hike.
- Salomon Brothers - Understanding the Yield Curve, Parts 2, 6 and 7 (Ilmanen, Jun and Nov 1995; Ilmanen & Iwanowski, Feb 1996): forwards vs expectations and forecasting power.
- Credit Suisse (Bassman) - Forwards are NOT a Prediction (12 Aug 2013); Convexity Maven - For Propeller Heads Only (17 Jun 2019), The Big 'O' (22 Aug 2023): forwards as break-evens, implied-cut arithmetic, bimodality.
- swapsball.net - Central bank decisions and inflation forecasts (8 Mar 2018): forecast-meeting effect and meeting-spread fair values.
- Citi Research - Japan Rates Weekly (14 Aug and 2 Oct 2026): BoJ terminal anchors, 2y OIS scenario grid.
- JWS Macro - Central Casting #6.1 (21 Jun 2026), Global Rates Update #7 (19 Jul 2026), Global Rates Outlook #4-#6 (2026): market-implied neutral, bimodal path, doom loop, pins.
- BofA Global Research - Rates basics: fixed versus float (24 Apr 2024); Global policy implementation: a short guide (9 Jul 2025): term rate as average of the path, corridors and floors.
- Global Macro Method (Substack) - STIR (Rates) Application Process (25 Feb 2026); Conks - Plumbing Notes (2025-26): path-shape reading, repricing types, cross-market year-end gauge.
- Huggins & Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): jump versus jump-diffusion policy-path models, joint SOFR/fed-funds calibration, unscheduled meetings.
- Shafer & Vovk - Probability and Finance: It's Only a Game! (Wiley, 2001): upper/lower prices, betting-based calibration bounds.
- Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): path extraction procedure, probability caveats, turn stripping.
- Citi Investment Research - US Rates Trade Recommendation: Flying Too High (Arora & Chen, 20 Dec 2010): scenario-probability fit of hike timing.
- BofA Securities - US Rates Watch: 10y rates and the Monty Hall problem (6 Aug 2024): Bayesian collapse of scenarios.
- J.P. Morgan - Interest Rate Derivatives: Impossible to walk in this muck (6 Mar 2020); Global FI Markets Weekly (21-22 Aug 2026); FX Markets Weekly (21 Aug 2026): call-spread digitals, MPC OIS levels, 1y1y regression.
- JWS Macro - USD Rates & Fed outlook #1: Summer 2025 (21 Aug 2025): option-implied recession proxy.
- Citi Research - Nordic Economics Flash (20 Aug 2026); European Rates Weekly: What to do about OATs? (1 Oct 2026); Citi Markets - SOFR/CBOT Vol EOD (21 Aug 2026): Riksbank path read, OAT-Bund vs hike pricing, straddle breakevens.
- BofA Global Research - Global Rates Weekly: Start of rates bite (2 Oct 2026): real policy rate at cycle peaks.
