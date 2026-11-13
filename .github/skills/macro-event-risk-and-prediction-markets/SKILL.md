---
name: macro-event-risk-and-prediction-markets
description: 'Price and trade scheduled and unscheduled event risk in G10 rates - central-bank meetings, payrolls/CPI/PCE releases, elections, debt-limit X-dates, FX intervention, headline shocks - and use prediction markets (Kalshi/Polymarket-style binary contracts) as probability inputs. Covers ladder-to-PMF extraction and repair, risk-neutral caveats, event-day vol and event weight from option term structure, data-surprise beta, 2-sigma follow-through rules, event-conditional studies, calibration tests. Use when asked about event vol, event premium, FOMC/ECB/BoJ meeting risk, NFP/jobs report/CPI surprise, election or midterm trades, debt ceiling/X-date, Kalshi/Polymarket odds, implied probabilities vs OIS, "is the event priced", straddle/gamma into an event, headline or tail risk. Meeting path from OIS: stir-policy-pricing-whats-priced-in; options-implied distribution: stir-options-implied-distributions.'
---

# Macro event risk and prediction markets

Event risk is priced in two places that rarely agree: the option/OIS surface (variance and meeting-by-meeting drift) and
the narrative (consensus, polls, prediction markets). The edge is rarely "forecast the outcome"; it is (a) knowing how
much the market already pays for the event, (b) comparing that with a probability you can defend, and (c) knowing
whether the reaction tends to follow through or fade. This skill gives the extraction formulas, the evidence-based
rules of thumb (with sample sizes), and the traps. Prediction-market prices are an additional input, never a
mechanical replacement for futures, OIS, fixings or survey medians.

## When to use
- "What is priced for the FOMC/ECB/BoJ meeting and does the Kalshi/Polymarket distribution agree?"
- "Is event vol rich or cheap into payrolls/CPI/the election/the referendum?" (event-day weight, forward vol).
- "Receive/pay into a meeting, a data release, an election or a debt-limit X-date: what does history say?"
- "Did this headline/intervention/surprise move rates, and will it follow through or fade?"
- Scenario weights for a binary political event (chair nomination, by-election, tariff ruling, budget).

For the meeting-by-meeting OIS path itself use [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md);
for options-implied distributions of rates use [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Prediction-market ladder: price per strike ("above K") per event | `events_probs` (`threshold_pct`, `prob`, `bid_prob`, `ask_prob`, `volume_cnt`, `is_stale`, `resolution_date`) | daily last-trade snap, event life | prob 0..1 = price per 1 payout; use the last-traded price (the Kalshi method has no usable mid; if only a mid is stored, say so); keep `is_stale` to apply the staleness rule |
| Curve-implied probabilities (`venue = implied_ois`) for the same event | `events_probs`, `stir_quotes` | daily | meeting-dated OIS/futures minus current rate, in bp |
| Meeting schedule and effective dates | `cb_meetings` | forward-looking | decisions are effective the next day for some banks (check `effective_date`) |
| Releases, consensus, vintages | `macro_series` (`value`, `consensus`, `is_first_release`, `pub_ts_utc`) | per release, >= 2y of surprises | surprises must be vs the consensus known **before** `pub_ts_utc`; use first release |
| Rates/yields around events | `curve_par`, `bond_quotes`, `fut_quotes` | daily close; intraday if available | on-day change in bp, positive = yield up |
| Option vols by expiry | `vol_surface` (`nvol_bp`), `opt_quotes` | daily, expiries 1w..6m | normal vol in bp per year |
| Auction and supply dates, X-date inputs | `auctions`, `macro_series` (TGA, extraordinary measures) | schedule + level | for catalyst stacking and debt-limit work |

If a ladder, consensus or option vol is missing, ask the user or the data adapter; never infer a prediction-market
price. See [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

Conventions: yield change in bp, positive = yield up (price down); "receive" = long duration; STIR price = 100 - rate so
a weak-data surprise lifts futures prices; normal vol in bp per year, daily vol = annual / sqrt(252) (about annual/16).

## Method

### 1. Prediction-market ladder -> probability distribution (Kalshi threshold contracts)
A family of binaries at strikes K ("upper bound of the policy rate above K after the meeting?"); Yes pays 1, quoted
0.01..0.99. Price at K = **risk-neutral** P(X > K) = S(K), not a physical probability (Morgan Stanley, Kalshi Markets as
Macro Signals, 18 Aug 2026).
1. **Input**: last-traded price per strike per day (no usable mid). Forward-fill a strike on days it does not trade; **drop a
   strike whose last trade is > 60 days old**.
2. **No-arbitrage repair, middle-out**: S(K) must be non-increasing in K. Centre = strike priced closest to 0.49.
   Sweep left: a lower strike priced below its centre-ward neighbour is raised to it. Sweep right: a higher strike priced
   above its centre-ward neighbour is lowered to it. Violations come from stale illiquid tails (Aug 2025: the 4.75% strike
   was priced above 4.50%).
3. **PMF**: bucket mass = S(K_i) - S(K_{i+1}). With 25bp steps, P(K_i < UB <= K_{i+1}) = P(UB = K_{i+1}).
4. **Adjust**: (a) "bubble up" a 0% bucket that sits inside non-zero, more extreme buckets to the end of the distribution;
   (b) normalise: interior buckets sum to at most 0.98 (1c floor, 99c cap), so divide by their sum. Largest changes are in
   the upper tail, up to about -3.5c.
5. **Moments**: mean, median, mode (outcome = bucket upper strike). Compare like with like: Kalshi median/mode against
   a median/mode, Kalshi mean against futures-implied mean.
6. **Continuous variables** (CPI, core CPI, NFP, GDP, U3): use threshold markets, same steps; put each bucket's mass at its
   midpoint and cap open tails at the width of the nearest finite bucket.
7. **Decide how much weight** with the use-case matrix below, then compare with the OIS-implied probability
   (`two_outcome_prob`: implied move / 25bp when only {0, 25bp} outcomes are plausible; a full path needs
   [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md)).

Use-case matrix (Morgan Stanley, Kalshi Markets as Macro Signals, 18 Aug 2026):

| Series | When to weight it | Benchmark | Accuracy / unique info |
|---|---|---|---|
| Fed funds | inside 100 days of an FOMC; judge whether one outcome dominates or tails matter. Discount meetings > 3 ahead and during shocks | FF futures/OIS | strong / high |
| Headline CPI | inside 40 days; quote basis differs (contract on SA m/m, fixings on NSA index) | survey | strong / mild |
| Core CPI | when core is the main catalyst and survey still forming; > 60 days out too thin | survey | strong / high |
| NFP | before the survey is fully populated; not standalone (noisy) | survey | competitive / high |
| GDP | inside 100 days; watch repricing as components arrive | survey | competitive / high |
| U3 | do not over-weight small deviations (autocorrelated, errors already low) | survey | competitive / mild |

Rule: weight most where settlement is direct, liquidity sufficient, and traditional markets give only indirect signals.
Discount thin contracts, stale tails and volatile far-ahead pricing. The edge for NFP/GDP/U3 is earlier observability
(survey closes about 2 weeks before release), not accuracy. Evaluate any such input as mean absolute error vs the
**first release** by days-to-event, with t-1 = day before.

**Politics and legislation**: use ladder odds (Polymarket/Kalshi) as scenario probabilities, not as the trade. Trade the
gap between your probability and the market's ("betting against the spread"): your assessment must be out of consensus,
otherwise it is already priced (Papic, Geopolitical Alpha, 2021). High implied probability does not mean no reaction:
Hungary and Colombia market-friendly winners were well priced yet FX and bonds rallied before and after (Citi GMS, No
inflation trouble, 13 Aug 2026).

**Edge on a contract** = p_own - (ask + fee), in probability units; require it to clear fees and the bid-ask half-spread
plus a model-risk haircut you can name. Do not trade a contract you cannot defend against the venue's own book.

### 2. Option-implied event vol
Count event days, not calendar days: weekday = 1, weekend about 0, Friday slightly more, big releases more (BofA, US Vol
Primer: A Guide for the Perplexed, 11 Mar 2024).

**(a) Two expiries straddling the event** (BofA primer). Short expiry (before the event) with `days_short` (weighted) days,
vol sig_s; long expiry containing the event with `normal_days` ordinary days (all of them, including the short expiry's),
vol sig_l. Both are expiry-TOTAL vols in bp (annualised vol x sqrt(days/252)), not annualised vols:
`n = sig_s / sqrt(days_short)`; `X = (sig_l / n)^2 - normal_days`; event-day vol = `n * sqrt(X)`.
`X` is the event weight in normal-day units. Trade the expiry containing the event against the one before it,
vega-weighted, if X looks cheap or rich versus your own estimate.

**(b) Forward vol and one-day attribution** (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022,
s20.3 and Ex 20.7). Forward vol over (f, t] from annualised normal vols:
`sig_fwd = sqrt((t * sig_t^2 - f * sig_f^2) / (t - f))`. Window variance = `sig_fwd^2 * (t - f)`; put all excess variance on one day:
`event^2 = window_var - (n_days - 1) * sig_base^2 / 252`. This assumes independent normal increments and the same
underlying; for forward-starting swaps weight by PV01 ratio and correlation (result is very sensitive to rho; naive
averaging of par vols is wrong).

**(c) Compare with history**: event-day vol is a standard deviation, but a straddle pays on the *absolute* move: the one-day
breakeven (average absolute move needed) is `sqrt(2/pi) x` daily vol = 0.80 x (26.2bp in the Brexit example below = about 21bp), so compare it with the average
absolute realised move, not the RMS. Implied one-day move vs trailing 8-event average realised move and its percentile (Citi,
Mid-week musings, 19 Aug 2026, equity template, transferable); buy event straddles when implied < history. FX options have
priced the 1-day event vol at only about 50-60% of what macro analysts expect (JPM, FX Markets Weekly, 21 Aug 2026).
USD one-day FOMC/payroll swaption breakevens were about 1-1.5bp richer than the broader surface in 2017-19, justified by
realised; CPI in line (JPM, When the going gets tough, 5 Nov 2019).

**(d) Hedger structures**: buy gamma, not vega, before events, e.g. a forward-starting short-expiry straddle whose look
date is just before the event (strike set at the fixing; holder owns skew). Short FVA is dangerous in gaps (Credit
Suisse, Building a Better Volatility Mousetrap, 6 Sep 2012). Forward vol may already carry event premium and mean
reversion: do not pay for it twice. De-allocate short-gamma programmes around events (BofA primer).

### 3. Data-surprise beta and relevance
1. `z = (actual - consensus) / rolling_std(surprises, 24 releases)` using history only; first release vs consensus known
   pre-release.
2. Regress on-day yield change (bp, y) on z (x) over a rolling 1y: bp per z by instrument (2y, 5y, 10y, 30y, STIR packs, 5y5y).
   `surprise_beta` in the script. A year of a monthly release is only 12 points: report n and the standard error, and prefer 3y+ or
   a pooled fit when n < 30. Flip the sign of series where higher = weaker (unemployment, claims) so positive z always means stronger data. Compare the implied one-day breakeven with the realised absolute move (JPM, Zen and the art of
   gamma maintenance, 9 Mar 2018: by 2018 rates were much less sensitive to payrolls, especially Reds; attention had moved to
   inflation and wages).
3. Release impact ranking (STIR): NFP, retail sales, CPI high; PPI medium-high; PMI, consumer confidence, durable goods,
   industrial production medium; weekly claims low; GDP medium/low (lagging, anticipated) (Aikin, STIR Futures, 2nd ed.,
   2012). Check composition before trading a print: July 2026 PPI portfolio-management fees +6.5% added 13bp to core PCE
   (JPM, United States weekly, 14 Aug 2026); scheduled methodology breaks (BEA PCE revamp, about 20-30bp lower core PCE
   from August data) make pre/post-break comparisons invalid (WSJ, A Statistical Revamp, 19 Jul 2026).
4. NFP regime switch: a weak print moves the driver from inflation to recession: front yields fall faster, curve steepens,
   calendar spreads rise (Aikin 2012).

### 4. Event follow-through rules (sigma triggers)
Trigger = on-event-day yield change >= k x std of the previous 21 daily changes, today excluded (`sigma_trigger`, k = 2; +1 = yields
up/hawkish, -1 = yields down/dovish). Entry is the event-day close, so forward returns start there. Evidence, all small samples:
- **FOMC**: score by 2y price action, not statement. Receive (pay) after a 2y move of >= 2 sd; dovish 2-sd moves: median
  forward returns positive and persistent, 10th percentile not losing 20 days later; hawkish 2-sd follow-through clearer in
  easing cycles (n = 2) (Willer & Saunders, Trading Global Macro Markets, 2026). A day counts as "relevant news" if the 2y
  moves 2 sd.
- **NFP** (10y bond, 2-sd yield move; "bullish/bearish" is for the bond: bullish = yields fall, bearish = yields rise): bullish 45
  events, small follow-through, 3-sd (13 events) median > 1% over 20 sessions; rallies in easing cycles are entry points. Bearish 53
  (2-sd) / 25 (3-sd) events, weak follow-through: **a bond-bearish (yield-up) NFP is not a pay signal even in hiking cycles**
  (Willer & Saunders 2026). A first negative print after a year of positives (12 cases since 1974) was choppy then positive.
- **CESI trend** (Citi Economic Surprise Index): receive 5y swaps when CESI < -25, pay when > +75; IR 1.01 vs 0.26 buy-and-hold, in market 27% (Willer &
  Saunders 2026). CESI-extremes as contrarian failed.
- **Condition on the event-day reaction, not the decision** (decisions leak): classify by sign of the day-of move and read
  -60..+60 day paths (Willer & Saunders 2026, Ch.14).
- **Microstructure**: pre-load one tick through the market; fading consensus can pay more; first movers are fast locals;
  take partial profits; trim exposure before sessions you cannot monitor (Aikin 2012). Do not execute size into 8:30
  data, auctions or the FOMC: payroll depth falls below 1/4 of the pre-print base and takes 15-30 min to recover (JPM, When the going gets tough, 5 Nov
  2019). See [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md).

### 5. Central-bank meeting structures
- **Stub OIS into the next meeting** = cheap inter-meeting option: receive spot-starting OIS maturing **on** the meeting date;
  decisions are effective the day after, so the stub carries only inter-meeting risk. Size drift from funding drivers (e.g.
  rate-vs-floor regression on reserves). Aug 2019: receive at 2.157% vs EFFR 2.14% (maturity 18 Sep, 47 days; 50k DV01). A 25bp cut effective mid-Aug lowers the
  floating average by 25 x 33/47 = about 18bp, an end-Aug cut by 25 x 19/47 = about 10bp; with +1bp if no cut the receiver gains about 19bp
  or 10-11bp, i.e. 19:1 and 10:1 payoff ratios (Citi, US Rates Weekly, 2 Aug 2019). Not a conviction view.
- **Meeting gap as option on a driver** (ECB July gap = "option on Brent", range 6-12bp; floor about 1bp/week theta) (JWS Macro,
  Global Rates Outlook #6, 7 Jun 2026). If a meeting is nearly fully priced, running meeting-to-meeting risk is fruitless:
  receive the priced meeting to carry a further-out payer, or fly across gaps (JWS Macro, Autumn 2025).
- **Hump reading**: a new chair's first meeting priced at > 2x neighbouring gaps = market betting on a dovish first move.
- **Priced-probability ceilings**: BoJ hikes are seldom priced above about 80% until about a week before or a leak (Citi GMS,
  Macro tapas, 7 Aug 2026). With about one cut priced, it is easier to price more cuts in than to price out the last (Nordea,
  Risk/reward favours receiving ECB meetings, 19 Jun 2025); the biggest risk is crowded consensus.
- Attach an **expiry to an asymmetric view** (naming the catalyst) and drop it when the catalyst passes (Citi FX Forecasts, Aug 2026).
- Loss of forward guidance raises event vol: own gamma into CPI/NFP/meetings (JWS Macro, Central Casting #6.1, 21 Jun 2026).
  A speaker who avoids guidance gives a muted reaction: Jackson Hole 2y Thu-to-Fri moves were mostly within 1 sd (about 5.5bp)
  (JPM, US Weekly Prospects, 21 Aug 2026).

### 6. Elections, fiscal and policy events (summary; numbers in [references/event_studies.md](references/event_studies.md))
- **Election vol**: FX/rates vol rise about 25-50 days before and unwind after; US general-election years saw G10 FX vol +15%
  late Aug to late Oct, USD rates vol +20-30% (Credit Suisse 2012; Willer & Saunders 2026). Sell event premium only 4-5 weeks out;
  the premium decays into the event (JPM FX Markets Weekly, 21 Aug 2026).
- **US election follow-through** is short: 10y UST futures hit ratio 91% at 1d but 64% at 5/10/22d (n = 11); wait for the close
  (Willer & Saunders 2026). Midterm map: split Congress limited impact; D sweep 2y -5 to -7bp, 10y -3 to -5bp; R sweep 2y +7-10bp,
  10y +3-5bp (BofA, Global Rates Weekly, 2 Oct 2026).
- **Debt limit**: bill-curve kink around the projected X-date; markets price risk only about 2 weeks ahead; post-resolution TGA
  rebuild cheapens funding (BofA, Debt limit FAQ, 12 May 2025; BofA, Funding & debt limit, 27 Jun 2025). A 1m bill yield falling
  below repo before X-date is positioning, not collateral shortage (Conks, Collateral Damage, 18 Apr 2023).
  See [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md).
- **FX intervention** (JPY): escalation ladder from "excessive moves" to rate checks to action; effect on UST yields is weak but
  intuitive. The fit is only good for USD-buying episodes (about -2.2/-3.4/-3.3bp per JPY 1tn on 2y/5y/10y, R2 about 0.5, n = 30);
  the live case at USDJPY 160 is USD-selling (JPY-supportive; n = 9), where R2 is 0.12/0.0008/0.04: expect cheaper USTs in
  principle but no usable beta (BofA, FX intervention primer: G10, 8 Jul 2024).
- **Geopolitics**: fade quickly unless there is an oil angle (Willer & Saunders 2026). See
  [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md).
- **Headline shocks**: judge "market-moving" against a random-window control (95th percentile of 30-min 2y range = 1.7bp), not
  an absolute threshold; sensitivity to a recurring topic decays within about 2 months (JPM, Comfortably numb, 24 Jul 2026).

### 7. Calibration and sizing of probability inputs
- Test a probability source only on forecasts actually issued vs outcomes: Brier score, reliability table by bin, mean gap
  (mean outcome - mean price; should be about 0) (`calibration`). H0 "every forecast is calibrated" gives
  z = sum(y - p) / sqrt(sum p(1-p)) (`calibration_z`; |z| > 2 rejects). Shafer & Vovk's criterion is that the long-run average price
  converges to the event frequency; Brier and reliability tables are standard scoring tools, not theirs. A single mid-range probability
  is untestable without repetition; only many events or extreme probabilities carry meaning (Shafer & Vovk, Probability and Finance, 2001).
- If a market is calibrated, long-run average price converges to event frequency; one-sided (ask-only) data supports only
  one-sided conclusions, so keep bid and ask.
- Unique political events: start from a structured subjective prior (not a frequentist base rate), name the binding
  constraint and the data streams, then update prior -> posterior (Papic 2021; see [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md)).
- Scenario EV: `EV = sum p_i * payoff_i` with p summing to 1 (`scenario_ev`). Check scenario consistency: if a shock in the
  scenario would be very different under its conditional expectation given the other shocks, the scenario is internally
  inconsistent (scenario z-score delta; Golub, BlackRock's Guide to Fixed-Income Risk Management, 2023).

## Worked example(s)

**Kalshi ladder to PMF** (Morgan Stanley, Kalshi Markets as Macro Signals, 18 Aug 2026; Dec-2025 FOMC, as of 1 Aug 2025):
S(4.25%) = 20c, S(4.50%) = 4c, so P(UB = 4.50%) = 16%; P(UB in (4.00%, 4.25%]) = 24%. Distribution negatively skewed:
mean 3.98% < median 4.00% < mode 4.25%. Mar-2026 FOMC (as of 28 Jan): mass 4.00% about 46%, 3.75% about 25%, 3.50% about 21%;
median and mode settled on the eventual 3.75% UB before FF futures and OIS. Mar-2027 meeting was jumpy (illiquid): do not use.
t-1 error table (Kalshi median/mean/benchmark): Fed funds 0.7/1.7/1.4bp (OIS/futures-implied path); CPI 7.7/7.6/10.0bp (survey); core CPI 6.7/6.6/7.5bp;
NFP 65k/65k/60k; U3 10.9/11.2/10.2bp.

**Repair by hand** (illustrative): strikes 3.50/3.75/4.00/4.25/4.50 priced 0.97/0.60/0.20/0.04/0.06. Centre = 3.75 (0.60 closest
to 0.49). 4.50 is above its centre-ward neighbour 4.25, so lower it to 0.04. Interior masses: 3.75: 0.37, 4.00: 0.40, 4.25: 0.16,
4.50: 0.00; they sum to 0.93 (not 0.98 because S_0 = 0.97 and S_last = 0.04), divide by 0.93 -> 39.8/43.0/17.2/0%. Run
`python scripts/event_pricing.py pmf ...` to reproduce.

**UK EU referendum event vol** (Darbyshire, 3rd ed., 2022, Ex 20.7): 1M10Y normal vol 25bp, 2M10Y 69bp, event just over a month away.
1M-forward 1M10Y vol = sqrt((2/12 x 69^2 - 1/12 x 25^2) / (1/12)) = 94bp. Ordinary days at 25/sqrt(252) = 1.57bp; putting all excess
variance on one day over a 21-day window gives referendum-day vol of 26.2bp (about 416bp annualised), about 17x a normal day.
`python scripts/event_pricing.py eventvol --sig-short 25 --short-years 0.0833 --sig-long 69 --long-years 0.1667 --days 21` gives 94.3 and 26.3.

**Event weight, formula check** (method of BofA, US Vol Primer, 11 Mar 2024; numbers here are recomputed, illustrative): 1w option 10bp
total over 5 days gives n = 10/sqrt(5) = 4.47; a 2w option (10 days = 9 normal plus the release) at 20bp total implies X = (20/4.47)^2 - 9 = 11
normal-day equivalents, i.e. release-day vol 4.47 x sqrt(11) = 14.8bp, 3.3x a normal day (expected absolute move 0.80 x 14.8 = 11.8bp). The primer
prints n = 5.47 and X about 4.4 for the same inputs; 10/sqrt(5) is 4.47, so treat its exhibit as an arithmetic slip and recompute.

**Stub OIS inter-meeting option** (Citi, US Rates Weekly, 2 Aug 2019): see Method 5; 50k DV01, receive 2.157%, payoff ratios about 19:1
and 10:1.

**Fed-chair scenario map weighted by market odds** (JWS Macro, Autumn 2025, 13 Nov 2025): candidate A = front lower, back higher,
steeper, USD weaker (terminal 2.5-3.25%); candidate B = front mildly higher, long end lower, flatter, USD stronger (2.75-3.5%);
third candidate 12% on Polymarket; 1y1y in the low 3s; initial move perhaps 15-25bp. Map each outcome to front end / long end /
curve / USD / terminal range, weight by the market odds, then apply the scenario-consistency check above.

## Signals & interpretation
- Kalshi/OIS probability gap: act only when the ladder is liquid (inside 100 days for Fed, 40 days for CPI), repaired, compared
  mean-to-mean, and the gap exceeds fee + half-spread + haircut. Median/mode converging to the outcome earlier than futures is
  common; a lone far-dated jump is noise.
- Implied event weight X below your estimate -> long the event expiry vs the pre-event one (vega-weighted); above -> sell it,
  unless a gap risk or loss of guidance argues for owning gamma. Never sell event gamma into a meeting where the CB communicates
  nothing in advance.
- Sigma trigger fired (>= 2 sd on 2y for FOMC, 10y for NFP): follow in easing cycles and on dovish moves; treat hawkish moves
  and bearish NFP as non-signals.
- Election/political event: use as a soft prior only; the reaction to the event day matters more than the decision; fiscal risk
  premium and idiosyncratic risk (debt ceiling, new chair, tariff power) can override the historical pattern.
- Direction unclear but an event is certain (the closest past analog points one way while current drivers conflict): own strangles
  rather than a directional option (CitiFX on Vol, ~Aug 2026).
- Debt-limit: act on the funding-spread leg (outright SOFR/FF short rather than the SOFR/FF curve) and respect quarter-end
  dates inside the contract window.
- Headline: if the 30-min range is inside the control 95th percentile, no information; deal/no-deal ping-pong dominates and
  front meetings are more volatile on disappointment.

## Pitfalls
- Risk-neutral, not physical probabilities; thin strikes reflect one small order; in stress, low volumes distort moments.
- Quote basis mismatch (SA m/m vs NSA index, median vs mean); error measured vs revised data instead of first release.
- Meeting-pricing and FOMC/NFP rule samples are tiny (n = 2 for hawkish FOMC in easing cycles; elections n <= 14); no costs and no
  formal out-of-sample split in the cited studies. Treat as priors, not signals; see [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).
- Hit ratios on n <= 14 are wide: 13/14 (93%) has a 95% Wilson interval of about 69-99%, and the 64% US-rates figure (7/11) about 35-85%,
  so "91% at 1d vs 64% at 5d" is a weak contrast. Forward windows that overlap (20 sessions after FOMC/NFP clusters) are not independent
  events: count events, not days.
- Sign conventions flip between exhibits (FF-SOFR vs SOFR-FF; bill-OIS vs OIS-bill). Normalise before reusing any table.
- Sources contain internal conflicts: Citi midterm 5s30s path (title says steepens into the election then flattens, text says
  flattening troughs 20-50bd before then steepens) and a meeting-dated trade labelled Oct in text and Dec in the table. Verify
  against data; use only the consistent parts.
- Event-vol maths assumes independent normal increments and static PV01 ratios; state the day-count basis (holidays, Easter) for short expiries.
- Do not pay for event premium twice (forward vol often already includes it); election premium decays into the event.
- Intervention-yield links are confounded by safe-haven and funding flows; IMF "3 times in 6 months" rule is not a safe
  assumption for betting against further intervention (Citi, Japan FX, 3/4 Aug 2026).
- Buybacks are not QE; they inject no durable liquidity and transmit to USD more than to yields (JPM, FX Markets Weekly, 21 Aug 2026).
- "Deep play": in extreme volatility (ERM exit 1992) risk/reward is lopsided and events happen outside trading hours: sit out
  (Aikin 2012). Flight-to-quality STIR spikes are short-lived (London bombings 2005: Short Sterling +25 ticks, soon corrected).
- Do not hold an event view on its own once the primary drivers have run their course; midterms are secondary to data and the CB.
- Do not forecast from rhetoric: find binding constraints. The framework cannot time events (Papic 2021).

## Output
Return, per event:
1. Event header: id, date/time (UTC), CB or release, last print before the event, catalysts stacked on the same days.
2. Probability table: outcome | market (OIS-implied) | prediction-market (repaired, normalised) | own | gap | liquidity flag
   (days since last trade, volume) | weight used (use-case matrix).
3. Event-vol table: expiry pair, event weight X, event-day vol (bp), vs trailing realised and percentile; verdict rich/fair/cheap.
4. Reaction evidence: sigma trigger status, surprise beta (bp per z), analogue/follow-through stats with n.
5. Scenario table: scenario | probability | instrument payoffs (bp or currency) | EV and std; expiry/kill date of the view.
6. Trade structure(s) with sizing (DV01, premium), risks (gap, crowding, data revisions), and hand-off to
   [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and [rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Scripts
- [`scripts/event_pricing.py`](scripts/event_pricing.py): `repair_survival` (middle-out), `survival_to_pmf` (bubble-up, normalise),
  `pmf_moments`, `stale_filter`, `event_day_weight`, `forward_vol`, `event_day_vol`, `two_outcome_prob`, `contract_edge`,
  `scenario_ev`, `surprise_z`, `surprise_beta`, `sigma_trigger`, `calibration`, `calibration_z`. CLI: `pmf` (from `events_probs`, filter with `--venue`) and `eventvol`;
  `python scripts/event_pricing.py --help`. `--selftest` checks known cases (Kalshi 16% bucket, bubble-up, Brexit 94bp/26.2bp,
  event weight, exact surprise beta, sigma trigger incl. look-ahead check, stale filter, Brier, calibration z).

## Related skills
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-dated OIS path and probabilities to compare with ladders.
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): rate-option implied densities, the options analogue of the ladder PMF.
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): implied vs realised vol, grids, where event premium sits.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): gamma/theta P&L of owning event gamma.
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): tail structures for binary events.
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): who reacts to what; leadership change.
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): communication-regime reads.
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): constraints-based geopolitics.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): scenario trees and outcome maps.
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): budgets, debt ceiling, buybacks, term premium.
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bill curve and funding spreads around X-dates.
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): priors and updating for unique events.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): election/auction/refunding calendars.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): depth around releases.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): stress the position under event outcomes.
- [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md): PCE/CPI composition and methodology breaks, oil angle of geopolitical events.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread and ASW reaction to elections, budgets and supply events.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): SOFR/FF, GCF and TGA mechanics around X-dates.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): meeting dates, effective dates, conventions per market.
- [macro-technical-analysis](../macro-technical-analysis/SKILL.md): trend, momentum and technical timing.

## References
- Morgan Stanley Research - Kalshi Markets as Macro Signals: A Practical Guide to Prediction Market Pricing (US Rates Strategy, 18 Aug 2026): ladder repair, PMF, accuracy tables, use-case matrix.
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): FOMC/NFP 2-sd follow-through, CESI rule, elections, geopolitics, intervention lessons.
- Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): forward vol formula, event-day vol (EU referendum).
- BofA Global Research - US Vol Primer: A Guide for the Perplexed (11 Mar 2024): event-day weighting, de-allocating short gamma.
- Credit Suisse (Bassman) - Building a Better Volatility Mousetrap (6 Sep 2012): election vol seasonality, forward-starting straddle.
- J.P. Morgan - Zen and the art of gamma maintenance (9 Mar 2018): payroll-surprise beta vs options breakeven.
- J.P. Morgan - When the going gets tough, the tough get going (5 Nov 2019): event breakevens and release-time liquidity.
- J.P. Morgan - Comfortably numb (24 Jul 2026) and 'Truth' and consequences (16 Jul 2026): headline event study with random control.
- J.P. Morgan - FX Markets Weekly: Currencies amid long-end UST shenanigans (21 Aug 2026): election event-vol sizing, 50-60% rule, straddle selling.
- J.P. Morgan - US Weekly Prospects (21 Aug 2026) and United States weekly (14 Aug 2026): Jackson Hole 2y study, PCE composition.
- BofA Global Research - Debt limit FAQ: spring 2025 update (12 May 2025); Funding & debt limit: history lessons (27 Jun 2025); X-date shift (7 Feb 2025): X-date mechanics and signals.
- Barclays (Abate) - US short interest rate primer (Jan 2025): debt-ceiling rules, 2023 X-date numbers.
- BofA Global Research - FX intervention primer: G10 (8 Jul 2024): intervention event-study regressions.
- BofA Global Research - Global Rates Weekly: Start of rates bite (2 Oct 2026): midterm scenario map.
- Citi Research - How to trade US midterm elections (QGMS, 14 Aug 2026) and US midterms on the mind (Multi-Asset, 2 Oct 2026): election event-study framework.
- Citi - US Rates Weekly: Learning on the job (2 Aug 2019): stub OIS inter-meeting option.
- Citi - Macro tapas (7 Aug 2026) and No inflation trouble, in a SOX bubble? (13 Aug 2026): BoJ pricing ceiling, odds do not mean no reaction.
- Citi Research - Japan FX / Global FX Strategy notes on JPY intervention (3 Aug, 19 Aug 2026): REER 2-sd trigger, IMF rule, ammunition.
- JWS Macro - Global Rates Outlook #6 (7 Jun 2026); Central Casting #6.1 (21 Jun 2026); USD & Global Rates Thoughts #2: Autumn 2025 (13 Nov 2025): meeting gaps, chair scenarios.
- Nordea Markets - Risk/reward favours receiving ECB meetings (19 Jun 2025): meeting-dated EUR OIS, asymmetric pricing.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed. (Harriman House, 2012): release ranking, event microstructure, deep play.
- Papic - Geopolitical Alpha (Wiley, 2021): betting against the spread, net assessment as prior.
- Shafer & Vovk - Probability and Finance: It's Only a Game! (Wiley, 2001): calibration of market probabilities, betting tests.
- Othman & Sandholm - Rational Market Making with Probabilistic Knowledge (AAMAS 2012): market making on binary events.
- Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): scenario z-score delta consistency check.
- Citi - US Rates Vol Lab: Fair value vs seasonality (1 May 2017); Citi Global Markets - Mid-week musings (19 Aug 2026); Citi Research - Global FX Forecasts (Aug 2026): election/shutdown vol, equity event-vol screen, view expiry.
- Wall Street Journal - A Statistical Revamp Is About to Lower Inflation, at a Critical Time (19 Jul 2026): PCE methodology break.
- BofA Global Research - Technicals Explained primer (14 Jan 2025): presidential-cycle table; Citi - European Rates Weekly: What to do about OATs? (1 Oct 2026): OAT-BTP polling overlay.
- J.P. Morgan - Issuance, pensions, and long-end spreads (14 Sep 2018); Far from the shallow now (12 Apr 2019); mini 'Flash Rally' (5 Mar 2020): hurricane study, depth around events.
- Fleming, Mizrach & Nguyen - FRBNY Staff Report 381; Clarus Financial Technology blog - ECB June Meeting (18 Jun 2014); Geopolitical Cousins podcast (about Sep 2026): FOMC price discovery, ECB-day swap volumes, buybacks and political sell-offs.
- Conks (Monetary Mechanics) - Collateral Damage (18 Apr 2023); Signed Ceiled and Delivered (12 May 2023): debt-ceiling frontrunning diagnostic.
