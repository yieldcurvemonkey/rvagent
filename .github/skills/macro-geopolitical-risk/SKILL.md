---
name: macro-geopolitical-risk
description: 'Assesses geopolitical risk for G10 rates: constraints-based net assessment (preferences vs constraints, fulcrum constraint, bond market as constraint), own probability vs what is priced (attention/GPR indices, priced-in decay), and a channel classifier that sets sign, instrument and fade horizon: no-oil flight-to-quality (fade), oil/gas/chip supply shock (bear-flattening, front-end repricing by CPI energy weight), targeted vs self-harming tariffs, fiscal/defence supply (ASW, term premium), dollar funding (xccy basis, bills), reserve-manager selling, FX intervention. Use when asked how war, Iran/Hormuz, Middle East, Russia-Ukraine, Taiwan, sanctions, tariffs, trade war, Liberation Day, terror/cyber attacks or intervention headlines move UST, Bund, gilt, JGB, OIS, 1y1y, breakevens, swap spreads, xccy basis or rates vol; fade or follow a geopolitical rally/sell-off; safe-haven bid; risk-off; geopolitical scenario shocks; GPR index; headline risk. Scheduled events: macro-event-risk-and-prediction-markets.'
---

# Geopolitical risk for G10 rates

Geopolitical shocks reach rates through a small number of channels: flight-to-quality, energy-driven inflation and
policy repricing, tariff growth shocks, fiscal and defence supply, dollar funding, and reserve or FX-intervention
flows. Each channel has its own sign and decay. This skill does four things:

1. Forecasts the political outcome from **constraints, not rhetoric**.
2. Compares that probability with **what is priced**.
3. Classifies the **channel**, which sets the direction by market and tenor.
4. Decides whether to **fade or follow**.

The evidence says spike-day moves and equity drawdowns mostly mean-revert within days to weeks. The exceptions are
shocks with an oil or energy angle, and shocks where the safe-haven issuer is itself the source of the risk.

## When to use
- "War / strikes / Hormuz closure: does that mean receive or pay? Which G10 front end?"
- "Tariffs announced: is it a bond rally or a sell-off this time? UST vs Bund?"
- "Is this flight-to-quality rally fadeable?" or "Has the geopolitical premium already been priced out?"
- "The leader threatens X. How likely is it really?" (constraints vs preferences)
- Building a geopolitical scenario shock vector for stress tests, or a kill-switch for an RV book
- Front-end, ASW, xccy-basis or vol dislocations that coincide with a geopolitical headline

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| OIS/swap par curves incl. forward starts (1y1y, 2y1y, 5y5y) per G10 currency | `curve_par` | daily, ≥ 10y (to cover past episodes) | `par_rate_pct`; moves in bp = Δpct × 100 |
| Government benchmark yields (2y, 10y, 30y; DE/FR/IT/ES for EUR) | `curve_par` (`<CCY>-GOVT-<issuer>`) or `bond_quotes` | daily | safe-haven vs periphery spread |
| Meeting-dated policy pricing, STIR futures | `stir_quotes`, `cb_meetings`, `events_probs` (`venue=implied_ois`) | daily | what is priced, by meeting |
| Breakevens / inflation swaps | `infl_swaps` | daily | energy pass-through channel |
| Swap spreads / ASW | `swap_spreads` | daily | keep the row's `sign_convention` |
| Cross-currency basis | `basis_swaps` (`basis_type=xccy`) | daily | more negative = more USD demand |
| FX spot (safe-haven and terms-of-trade read) | `fx_rates` | daily | |
| Swaption normal vol | `vol_surface` | daily | `nvol_bp` |
| Futures positioning, client surveys | `positioning` | weekly | crowding / degrossing risk |
| Geopolitical risk or attention index (GPR-type, own news/text score); CPI energy weights by country | `macro_series` (`unit` = `score`; state the unit of a basket weight explicitly) | monthly or daily | e.g. `series_id` = `GL-GPR`, `<CC>-CPI-ENERGY-WEIGHT` |
| Prediction-market or option-implied event probabilities | `events_probs` | daily | handled in macro-event-risk-and-prediction-markets |
| Oil and gas prices (Brent, WTI, TTF front month and curve) | `macro_series` (`GL-<COMMODITY>-M<n>`, unit `price`, `unit_detail` = per bbl or per MWh) | daily, ≥ 20y | one series per nearby (M1, M2, ...): see [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) |
| Event list: date, label, category, oil angle (y/n), protagonist | user-supplied (no canonical table) | per event | build it from the spike rule below, not from memory |

If an input is missing, ask for it or hand off to the data adapter. Never invent levels, probabilities or index
readings.

**Conventions:**
- **Yields and spreads:** in bp; **positive = yield up**.
- **Curve:** 2s10s = 10y − 2y. Bear-flattening means yields up and 2s10s down.
- **Forward-forward STIR spread:** implied rate (later contract) − implied rate (earlier contract). Negative means
  the market prices hikes followed by cuts.
- **Swap spreads:** US is swap − Treasury; EGB ASW is bond − swap (as in `swap_spreads`).
- **Receive = long duration.**
- **Price returns:** event tables quoted as price returns are in % with positive = rally. Do not mix them with bp
  yield changes.

## Method

### 1. Define the risk precisely
Write down five items: (a) the risk, (b) the escalation triggers (catalysts), (c) the adverse outcome(s), (d) the
horizon (default 1-6 months), and (e) the assets most exposed.

A vague risk ("Middle East tension") cannot be priced or monitored. "Strait of Hormuz closed for more than 4 weeks"
can. This is step 1 of BlackRock's four-step process: identify, analyse incl. priced-in, translate into factor
shocks, act (Golub ed., BlackRock's Guide to Fixed-Income Risk Management, 2023).

### 2. Net assessment: constraints over preferences
Forecast what the actors *can* do, not what they say they will do. The book's core maxim: "Preferences are optional
and subject to constraints, whereas constraints are neither optional nor subject to preferences" (Papic, Geopolitical
Alpha, 2021).

The book formalises it as a sum over constraint states Z:

```
P(Y) = Σ_Z  pX(y | Z) · py(Y | Z) · pZ(Z)
```

- `pX(y|Z)` = probability that actor X chooses action y given the constraint state.
- `py(Y|Z)` = probability that the action produces outcome Y.
- `pZ(Z)` = probability that the state holds.

The preference-only model `P(Y) = pX(y)·py(Y)` matches it only when constraints have no influence.

**"Hold me back" example.** A threat is made loudly only when teammates are there to stop it: `pX(y|Z=1) = 1` but
`py(Y|Z=1) ≈ 0`, and `pX(y|Z=0) = 0`. So `P(Y) = 0·1·pZ(0) + 1·0·pZ(1) = 0`. Loud rhetoric can coexist with near-zero
odds of action, and its aim may be to bring the other side to the table.

The author says the framework "is not scientific or quantitative". Use the sum as a structuring discipline: list the
states, put a number on each term, and show your work. Do not use it as a model to fit.

Constraint checklist. For each item, name the data stream that would show it binding:

| Constraint | Diagnostic question | Rates-relevant data stream |
|---|---|---|
| Market (the bond market) | Would the action push yields or the currency to levels the government cannot tolerate? | 10y/30y yields, term premium, swap spreads, FX, auction tails |
| Economic | Does the action damage growth or inflation enough to reverse? | PMI, CPI fixings, real incomes |
| Political (median voter) | Does it move policy away from the median voter? | approval, election calendar |
| Legal / constitutional | Can courts, legislatures or treaties block it? | rulings, budget process |
| Material / military | Does capacity exist (oil spare capacity, stockpiles, ESF/FX reserves)? | inventories, SPR, reserve data |
| Time | Do the actor's preferences run down the clock? | deadlines, elections |

- **Fulcrum constraint.** The one constraint that bends all the others is "the most diagnostic of all variables".
  Monitor its data stream first; if it changes, the whole call pivots.
- **The bond market as a constraint** is the rates-specific case: "Bond yields can be more powerful than missiles"
  (Papic, 2021). Papic and Shapiro list three US political-uncertainty ("vibes") sell-offs in about 24 months:
  - Sep 2024 - Jan 2025, on fiscal fears. It calmed on the Treasury Secretary nomination, which they say lowered
    yields "by 50 basis points" (also called "worth like 80 basis points" in the same transcript).
  - Liberation Day 2025. It calmed when the Treasury Secretary took over negotiations.
  - The 2026 Iran war. Here the doubled long-end buybacks did not hold: yields went back to pre-intervention levels
    (about 4.7% on the 10y).

  The first two calmed when the actor changed course; technical tools did not do it in the third (Geopolitical
  Cousins podcast, ~Sep 2026; auto-transcribed, so re-verify any figure).

### 3. Your probability vs what is priced
"The key to harvesting geopolitical alpha is betting against the spread, not trying to predict who wins the game",
and "your assessment has to be out of consensus, or the market may have already priced it in" (Papic, 2021).

Track record from the book: Brexit (Mar 2016) at about 50% vs about 30% priced in currency and betting markets; Trump
(1 Nov 2016) at 40% vs 29%, 15%, 7% and 2% from public models. Priced-probability sources, in order of preference:
prediction markets or option-implied odds (see macro-event-risk-and-prediction-markets), policy-pricing shifts on
the curve, attention indices.

**Attention score (BGRI-style).** `Total = Attention − 0.2 × Sentiment`, where:
- Attention is the relative frequency of risk keywords, with broker research weighted above news.
- Sentiment comes from about 150 positive and 150 negative words, on a weighted moving average.
- The total score is expressed in standard deviations above its exponentially weighted historical average. A change
  of 0.1 or less is noise.

The priced-in rule: when attention is above its level at scenario launch, scale the impact *down* (more is priced).
When attention wanes, scale it *up*, because "the less attention markets are paying to a particular geopolitical
risk, the greater the potential market impact" (Golub ed., Ch. 6, 2023). The book gives the direction of the
multiplier but not its functional form. If you build one, label it your own calibration.

To find exposed assets, BlackRock compared 3-month returns in windows where the risk's score rose or fell by more
than 0.75 sd.

**GPR index (Caldara-Iacoviello, news-share based).**
- A **spike** is a jump of at least 100% in a month, or a move to the 99th percentile.
- **Oil above +15% together with GPR at the 95th percentile** flags a supply-driven oil shock.
- Spikes mean-revert quickly (Willer & Saunders, Trading Global Macro Markets, 2026).
- For a live flag, compute the percentiles on an expanding window of index vintages known at the time (`pub_ts_utc`
  in `macro_series`). Full-sample percentiles are look-ahead: fine for picking study events, not for a signal.

**Edge:** `edge_bp = (p_own − p_priced) × (y_scenario − y_no_scenario)`, in bp of the instrument. The priced level
is the probability-weighted mix of the two outcomes, so the impact is the gap *between the outcomes*, not the move
from today's level. The sign of the result gives the direction. Act only when the gap is large and you can name the
constraint the market is mispricing.

### 4. Classify the channel: this sets the sign
Do not assume that geopolitics means bonds rally. The sources disagree by design: Trump 1.0 tariffs, bonds up; Liberation
Day, USTs down vs Bunds; the 2026 oil shock, bear-flattening; Oct 2026, a duration rally despite rising oil. Score
every channel that applies:

| Discriminator | If yes → expected rates response (sign) | Instruments | Typical fade horizon |
|---|---|---|---|
| **No oil/energy angle** (terror, cyber, distant conflict) | Spike-day flight-to-quality pop (Δy < 0) that reverses within 1-2 days; equities dip and recover. Do not fade a wider bond drift: across all large GPR spikes, US bonds did well into day 0 and for the next 50 trading days | govts, STIR futures | the pop: 1-2 days (London 2005: Short Sterling +25 ticks, soon corrected). Equities: 9/11 −12% in week 1, recouped by business day 25. The no-oil sample is essentially 9/11 and London 2005 |
| **Oil/energy supply shock** (Gulf, Hormuz, Russia; treat a chip-supply shock such as Taiwan the same way: "semiconductors are the oil of the twenty-first century", Willer & Saunders, 2026) | Front end sells off (Δy > 0) more than the long end → **bear-flattening**; breakevens up. When oil rises 30%+ in 3 months, bonds go sideways to down into the day that threshold is crossed, then track their unconditional path | 1y1y OIS, meeting OIS, breakevens, CPI fixings | geopolitical oil spikes peaked a median 38 days after the event; median 3m change +13.2% (n = 10) |
| **Tariffs, targeted** (one partner; growth shock dominates) | Bonds rally, cuts priced (Δy < 0). Breakeven sign depends on whether the import-price or the growth effect dominates: BlackRock's 2018 scenario set +20bp, while Citi (2019) rated long breakevens the most vulnerable position under escalation | 2y/10y, OIS | 10-22 days. US 7-10y +0.7% and Bunds +1.2% (price) by day 22 |
| **Tariffs, broad/self-harming** (the safe-haven issuer is the protagonist; credibility is in question) | Home bonds sell off vs peers (UST − Bund spread widens), home currency falls, term premium up | UST-Bund, 10s30s, swap spreads | weeks. Liberation Day: UST −0.8% vs Bund +1.0% (price) at day 22; USD index −4.7% at day 10 |
| **Fiscal/defence response** (energy subsidies, price caps, defence at 3.5% + 1.5% of GDP) | More issuance → bonds cheapen vs swaps (US swap − Treasury falls; EGB ASW, bond − swap, rises), term premium up; supply shows in spreads more than in curve shape | ASW, swap spreads, 10s30s | structural (months) |
| **Dollar funding split** | Onshore easy (money-fund inflows, bills rich, SOFR can fix below EFFR); offshore xccy basis more negative; converges after resolution | bills-OIS, SOFR-FF, xccy basis | until resolution |
| **Reserve-manager selling, sanctions, FX intervention** | Fear of official UST selling tightens US swap spreads (swap − Treasury falls); intervention changes the domestic reaction function | swap spreads, invoice spreads, JPY OIS | days (fear) to quarters (regime) |
| **Volatility** | Implied vol up. On flight-to-quality days the vol-rate beta flips **negative** (yields down, vol up) | swaption straddles, skew | days |

Evidence for the oil channel:
- **Pass-through rule of thumb:** about +30bp on near-term y/y CPI per +$10 Brent (EZ HICP). Brent around $110 is
  where HICP would break 3% (JWS Macro, #3 Iran & Front End Rates, 8 Mar 2026). The full arithmetic is in
  macro-inflation-and-energy-drivers.
- **Policy response.** A central bank at neutral with a single inflation mandate (the ECB) can make "adjustment
  hikes". Banks that see themselves as still restrictive (Fed, BoE) can hold instead (JWS, 8 Mar 2026). Another
  author claims the Fed has never hiked into a temporary inflation shock (under 6 months); treat that as unverified
  (Conks, Plumbing Notes: The Peak-TACO Era, 9 Apr 2026).

### 5. Cross-section across G10
Inside a shock, rank markets by what the channel predicts. Do not assume one global beta.

1. **Fundamental beta.** For an energy shock, regress the 1-week change in 1y1y on the energy share of each CPI basket
   across markets: `Δ1y1y_i = a + b·w_energy_i + e_i`, with Δ1y1y in bp, w in % of the basket, so b is bp per pp of
   weight. The global average energy weight is about 10%; CH, AU and NO sit near 5%. The author calls the fit general but imperfect (JWS, 8 Mar 2026).
2. **Positioning residual.** A large `e_i` in the first week is usually degrossing: "sharp increases in volatility
   will often see DEGROSSING of exposures regardless of their immediate performance". GBP (the most received
   market) and JPY (the most paid) were the G10 outliers. Fade the residual only once positioning is cleaner. Check
   the `positioning` table and flow-positioning-cftc-and-surveys.
3. **Price vs quantity absorption.** Some economies absorb the shock through prices (pay their front end); others
   through lower quantities (receive later). The ranking: US closest to price; UK messy; EZ more quantity, but the
   ECB's reaction pulls it to price; Japan mixed; CAD, NZD, SEK toward quantity; AUD, NOK toward price (JWS, Global
   Rates Outlook #5, 10 May 2026).

| Market | Geopolitical sensitivities in the sources |
|---|---|
| USD | Safe haven, except when the US is the protagonist (Liberation Day, "vibes" sell-offs). Oil shocks repriced hikes. Swap spreads carry the supply and plumbing channel. Reserve-manager fears tighten spreads |
| EUR | ECB has a single inflation mandate → front end most exposed to energy (Dec-26/Dec-27 Euribor spread +12.5bp → −12.5bp target hit). Gas (TTF) matters more than oil for EUR inflation (JWS, Global Rates Update #7, 19 Jul 2026). Bunds are the relative haven; OAT/BTP/SPGB widen in risk-off (Italy 5y +59bp in the trade-tensions scenario) |
| GBP | High energy sensitivity, but retail price caps delay pass-through. High beta to European gas: SONIA underperformed SOFR and Euribor on a +8% gas day, with the Dec-27 contract down 9.5bp in a day, i.e. implied rate up (Citi Markets, STIRT Weekly: You Shall Not Pass, 14 Aug 2026). Positioning-driven overshoots (SONIA from 50bp of cuts to about 2bp). Gilts rally in a global trade shock (−30bp implied) |
| JPY | Large oil importer: oil reaches CPI with a 6-12 month lag via fuel-cost adjustment. JGB 10y moves little (−4bp in the trade scenario). Intervention channel: Citi saw more intervention as possible above ¥160/$ and as more likely than not above ¥162/$. After the coordinated US-Japan intervention of Aug 2026, Citi pulled BoJ hikes forward to 2.00% by end-2027 (from 1.5%), reading it as freeing the BoJ (Citi, Japan Economics, 7 Aug 2026); post-intervention JPY dollar-funding softness normalised in about 1-2 weeks (Citi STIRT, 7 Aug 2026) |
| CHF | Low energy weight (about 5%). CHF is the best FX hedge for GPR spikes, but the move is small |
| AUD, NOK | Low energy weight, energy exporters. In Mar 2026 their 1y1y sold off almost as much as anyone's anyway → candidates to fade (receive) once positioning clears. The May 2026 ranking puts both on the price side, so re-check the fade if the shock persists |
| CAD | Trade-war exposure to the US (2026: new US tariffs on $20bn of exports on top of 50% steel/aluminium; Canada retaliating "dollar for dollar"). Absorbs through quantity |
| SEK, NZD | Quantity-absorbers per JWS. Citi saw Norges Bank as more hawkish than the Riksbank and expressed it as long NOKSEK through a US/Iran re-escalation window (Citi, 21 Aug 2026). No other source evidence: apply the generic screen |

### 6. Translate to a scenario shock vector
Set 3-6 "policy" shocks by hand (e.g. US 10y, front-end OIS, breakeven, oil, USD). Derive the rest from a
regime-consistent covariance. Express each shock in monthly standard deviations as a plausibility check.

The BlackRock trade-tensions scenario (June 2018), 1-month shocks:

| Shock | Size | Type |
|---|---|---|
| US 10y | −35bp (−1.8 sd) | set by hand |
| US 10y breakeven | +20bp | set by hand |
| Mexico 10y | +80bp | set by hand |
| China equities | −20% (−3.3 sd) | set by hand |
| UK 10y | −30bp | implied |
| DE 30y | −24bp | implied |
| JP 10y | −4bp | implied |
| ES 5y | +15bp | implied |
| IT 5y | +59bp | implied |

Hand the vector to port-scenario-and-stress-testing. More tables are in [references/episodes.md](references/episodes.md).

### 7. Choose the expression and size
- **Prefer options or conditional structures across a catalyst window.** The payoff is two-way and path-dependent.
  Example: long NOKSEK via a 4-month 1.03/1.05 call spread costing 48bp, chosen over spot to span a US/Iran
  re-escalation window into the midterms (Citi Research, Global FX Strategy: Long NOKSEK, 21 Aug 2026). For rates,
  see curve-conditional-trades and vol-skew-and-tail-hedging.
- **Size down while headlines drive prices.** Citi's STIR desk: in geopolitically driven markets it saw "little
  merit in owning large positions"; wait for catalysts and levels (Citi Markets, STIRT Weekly, 7 Aug 2026).
- **Preliminary deals are not resolutions.** One author treated MoU-driven rallies as chances to reload shorts (JWS,
  Central Casting #6.1, 21 Jun 2026). Score any "deal" headline through step 2 before chasing it.
- **Long gamma** was the best performer under trade-war escalation, while long breakevens were the most vulnerable
  (Citi Research, US Rates Weekly: Deal or no deal, 10 May 2019).

### 8. Decay and exit
Attention decays even while the conflict continues. The 2Y reaction to the president's Middle East posts was largest
in the first conflict month and faded afterwards (J.P. Morgan, 'Truth' and consequences, 16 Jul 2026).

Exit the fade when the channel changes. An exit is warranted if a no-oil event acquires an oil angle, or if the
fulcrum constraint moves.

### 9. Verify on your own data (event study)
The source samples are small (10 oil events, 11 tariff dates). Re-test before trading:

- **Response:** `Δy_i(h) = y(t_i + h) − y(t_i − 1)` in bp for h ∈ {0, 1, 5, 10, 22} trading days. The run-up is
  `y(t_i − 1) − y(t_i − 1 − k)` for k ∈ {5, 10}.
- **Control:** 1,000 random dates from the same sample period, excluding ±22 days around events, at the same
  horizons.
- **Report:**
  - the median event response minus the median control response;
  - the share of events beyond the control's 5th/95th percentiles (about 10% under the null);
  - the follow-through rate, P[sign(y(t_i + h) − y(t_i)) = sign Δy(0)]. Measure it on the *post-event* move:
    Δy(h) already contains the day-0 move, so testing it against Δy(0) inflates the hit rate mechanically.
- **Inference:** the null for follow-through is 50%; use a binomial (sign) test. With n = 10, 7 hits gives a
  one-sided p of about 0.17 (176/1024), which is not evidence. Events closer together than h share the same window:
  merge them into one event or drop the later one rather than count them as independent.
- **Where the effect shows:** J.P. Morgan found it in the tails, not the median. Most posts moved the 2Y by less than
  1bp in 30 minutes, but the 95th percentile ran about 1bp above control.
- **Event dates:** choose them by the GPR spike rule or a fixed keyword set, never from memory. Hindsight selection
  inflates the effect.

## Worked examples
**A. Constraint check on a feared official sale (Citi Research, US Rates Weekly: Trade worries linger, 17 May
2019).**

- *What moved:* fear that China would sell USTs as a trade weapon helped tighten 5y swap spreads (swap − Treasury)
  by 2.5bp on the week, to 1.5bp; the 2y futures invoice spread went to −19bp.
- *Constraint read:* tariffs are reversible, but selling and rebuying Treasuries cost-effectively is hard; the
  alternatives are less liquid; selling would hit China's own equities. Selling is plausible only if capital outflows
  and a weak CNY force it. Citi kept its swap-spread widener (2y futures vs OIS), noting that crowded wideners had
  amplified the move.
- *Growth channel, same week:* the Treasury market "rallied massively", pricing a full 25bp cut by end-2019 and about
  1.5 cuts in 2020. Citi's economists put the growth hit of 25% on $325bn at −0.17pp (US) and −1.35pp (China), with
  core PCE up to about +0.4%. Classification: targeted tariff → growth channel → receive.

**B. Priced-in decay (Golub ed., Ch. 6, 2023).** The trade-tensions scenario launched on 11 Jun 2018.
- Attention then rose above its launch level, so the adjusted impact was *smaller* (more priced).
- From the July 2018 peak to mid-May 2019, attention waned, and the adjusted impact grew to a potential double-digit
  equity loss.
- BlackRock kept the likelihood high because it judged US-China tension structural. The risk flared in May 2019:
  this is the bond rally in example A.
- Lesson: low attention with a high structural likelihood is the asymmetric setup.

**C. Energy shock cross-section, first week of the 2026 Gulf conflict (JWS, 8 Mar 2026).**
- Brent rose from $70 to $90 in a week. CE3 1y1y rose 60-100bp, and ECB pricing moved about 40bp, to a full hike.
- The energy-weight fit said pay high-energy-weight front ends with price-absorbing central banks. Concretely: the
  Dec-26/Dec-27 3m Euribor fwd-fwd inversion (pay Dec-26, receive Dec-27), from +12.5bp to a −12.5bp target. The
  author later reported the target hit quickly (JWS, Global Rates Outlook #4, 8 Apr 2026).
- The fit said receive the low-weight exporters, AUD 1y1y and NOK, whose sell-off ran ahead of the fit. RBA had
  57.5bp priced through Dec-26.
- The GBP overshoot (cuts priced from about 50bp to about 2bp) was positioning, so it was a later "shopping list"
  receive, not a day-1 trade.

**D. Same headline type, opposite sign (Willer & Saunders, Tables 4.2-4.3, 2026). Price returns in %, positive =
rally:**
- **Trump 1.0** tariffs on China: US 7-10y +0.7%, Bunds +1.2% at day 22.
- **Liberation Day** (broad tariffs): US 7-10y +0.9% at day 1, then −0.8% at day 22; Bunds +1.0%; USD index −4.7% at day
  10.

The discriminator is whether the tariff war hurts the issuer's own economy and credibility more than its targets'.

## Signals & interpretation
- **GPR spike, oil moves less than 15%, no supply link** → fade only the spike-day pop (it reversed within 1-2 days).
  Do not pay against the wider drift: bonds did well for 50 trading days after large GPR spikes. The no-oil sample is
  tiny (9/11, London 2005). Equity losses run larger when PMI is below 50 or shocks coincide (31-event study, Golub
  ed., 2023), so fade less in a contraction.
- **Oil above +15% with GPR at the 95th percentile** → treat it as a supply shock: expect the front end to lead a
  bear-flattening and breakevens to widen. Geopolitical oil spikes peaked a median 38 days after the event.
- **Oil spike without a lasting supply loss** (the 2019 Aramco attack, the 2020 Soleimani killing): "the correct
  call was to short the spike in oil prices" (Papic, 2021). If the constraint read says supply is not lost for long,
  fade the front-end sell-off with the oil spike.
- **Oil up 30% or more within 3 months** (a separate study) → bonds go sideways to down into the day the threshold is
  crossed, then track their unconditional path. **A big break in oil after a large rates sell-off often marks the
  rates peak** (Willer & Saunders, 2026).
- **Attention score:** a change of 0.1 sd or less is noise. A move of more than 0.75 sd over 3 months is material.
  Low attention plus a high structural likelihood is the setup to buy protection cheaply.
- **Tariffs:** a targeted measure with a growth shock is a receive. A broad, self-harming measure from the reserve
  issuer means home bonds underperform peers and the currency weakens. Decide which before choosing UST vs Bund.
- **Headline from a leader:** most move the 2Y by less than 1bp in 30 minutes. Trade only when the headline changes
  a constraint state, not on the median headline.
- **Swap spreads:** "war continues = bullish spreads, war ends = also bullish spreads" (Conks, Plumbing Notes: War &
  Short-end Rates, 23 Mar 2026) is a consensus view. When consensus is long spreads, EGB stress can tighten USD
  spreads through stops (Goldman Sachs, GS Macro cuRated: 2Oct26, 3 Oct 2026). Check crowding with
  rv-devils-advocate. A deleveraging tell: regress each day's maturity-matched swap spreads on modified duration
  across 2y-30y; a large one-day drop in the intercept (the zero-duration spread) means the whole spread curve shifted
  down. It had its largest fall since Liberation Day on the Oct 2026 flight-to-quality day, −8.2 to −10.4bp on the
  week (J.P. Morgan, 2 Oct 2026).
- **Regime marker:** in Oct 2026, "for the first time in a while, the risk-off sentiment translated into a duration
  rally, despite oil rallying", after months of oil shocks producing bear moves (GS, 3 Oct 2026). When the sign
  flips, re-estimate betas before reusing the energy screen.

## Pitfalls
- **A single-direction prior.** The prior that safe havens rally fails when the haven issuer is the source (Liberation Day,
  fiscal "vibes"). Run step 4 every time.
- **Recession calls from oil.** Oil spikes of 75% y/y or more held for at least 5 days preceded or coincided with 5
  of the last 6 recessions, but with many false alarms and unstable lags: "somewhat of an urban myth" (Willer &
  Saunders, 2026).
- **Supply vs demand oil shocks.** Classifying them by same-day equity direction ex ante assumes the answer. Use the
  joint GPR-oil rule instead.
- **Risk premium priced ahead of the event.** Oil was sometimes lower 3 months after the event than the day before
  it, because a premium was already priced. Measure the run-up (step 9) before assuming the event is unpriced.
- **First-week betas.** Positioning and degrossing distort the cross-section in the first week. Wait for positioning
  to clean up.
- **Flight-to-quality days flip vol-rate betas negative.** 6Mx30Y went to −3.13 and 2Yx30Y to −5.44 that day,
  against +2.1 to +2.4 for 6-month expiries over the prior three months. Delta and vega hedges sized on recent
  betas fail on exactly those days (J.P. Morgan, US IRD: Near, far, wherever yields are, 2 Oct 2026).
- **Official-holder data.** Falling custody holdings are not proof of reserve-manager selling: holdings can sit with
  third-country custodians. Holdings data reported at market value overstate purchases in rallies (Citi, 17 May 2019;
  Conks, Money Market Update, 15 Sep 2025).
- **Confounded episodes.** 1973 coincided with Watergate and a weak economy; the 1998 embassy bombings came amid the
  Asian crisis and Russian default. Average responses hide huge dispersion.
- **Keyword event sets** let in noise: "oil" captured Venezuela posts in the J.P. Morgan study.
- **Timing is the constraint method's ceiling.** It tells you *what*, not *when*. Use options or small size.
- **Opinion and transcript sources** (podcasts, newsletters) carry transcription errors and advocacy. Re-verify any
  number before it enters a trade note.
- **Overreach.** This skill classifies and sizes the geopolitical channel. Leave the CPI arithmetic, the reaction
  function and the scenario covariance to the linked skills.

## Output
Return a **geopolitical risk card**. Use this table, one row per field:

| Field | Content |
|---|---|
| risk_id, definition, horizon | step 1, with escalation triggers and adverse outcome |
| fulcrum constraint | the constraint, its data stream, and its current reading |
| p_own vs p_priced | both numbers, the source of p_priced, and the edge |
| attention / GPR | level (sd), 3-month change, spike flag |
| channels | each discriminator from step 4, with its sign |
| G10 cross-section | per market: expected Δ1y1y, Δ10y, Δ2s10s, Δbreakeven, Δswap spread or ASW, Δxccy basis (bp, signed), confidence, evidence row |
| expressions | fade/follow, structure (outright, curve, cross-market, option), horizon, size scale, kill criteria (constraint change, oil threshold, attention reversal) |
| scenario vector | policy shocks in bp and sd, for port-scenario-and-stress-testing |
| verification | event-study stats on the user's data (step 9), or "not yet tested" |

Then hand off to rv-trade-idea-writeup for each surviving trade, and to rv-devils-advocate for the pre-mortem.

## Related skills
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event probabilities, prediction markets, elections and data events
- [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md): oil and gas → CPI pass-through arithmetic, fixings-implied paths
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): which central bank hikes or holds into a supply shock
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-dated pricing, the "priced" side of the edge
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): defence and energy-subsidy issuance, term premium, "vibes" sell-offs
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): scenario trees, price vs quantity regimes
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): plausibility (sd, scenario z-score) and P&L of the shock vector
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): UST vs Bund, periphery spreads in risk-off
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): ASW and swap-spread reaction to supply and reserve-selling fears
- [xccy-basis](../xccy-basis/SKILL.md): offshore dollar funding stress during conflicts
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): onshore safe-haven flows, bills, SOFR-FF
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): positioning residuals and degrossing
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md) and [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): gamma and tail structures for catalyst windows
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): conditional steepeners and flatteners for two-way geopolitical paths
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): dictionary text scoring, reusable for attention and sentiment indices
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): updating subjective priors as constraint data arrive
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): crowding and kill criteria
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): the trade note
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): breakeven and inflation-fixing expressions of the energy channel
- [stir-futures-rv](../stir-futures-rv/SKILL.md): meeting and fwd-fwd STIR spreads such as the Euribor Dec/Dec inversion
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables; commodity prices as `macro_series`

## References
- Marko Papic - Geopolitical Alpha: An Investment Framework for Predicting the Future (Wiley, 2021): constraints vs preferences, the P(Y) sum over constraint states, fulcrum constraint, median voter, bond market as constraint, "betting against the spread"
- Bennett W. Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management, Ch. 6 "A Framework to Quantify and Price Geopolitical Risks" (Wiley, 2023): four-step process, attention-sentiment indicator, priced-in multiplier logic, trade-tensions shock tables, 31-shock event study
- Dirk Willer, Alex Saunders - Trading Global Macro Markets, Ch. 4 "(Geo)Politics" (Wiley, 2026): GPR spike rule, oil-spike table, fade-without-oil rule, hedges for GPR spikes, Trump 1.0 vs Liberation Day tables
- JWS Macro - #3: Iran & Front End Rates (8 Mar 2026): energy-weight beta screen, positioning residual, ECB adjustment hikes, AUD/NOK fade
- JWS Macro - Global Rates Outlook #5: Price Vs. Quantity & A New Era For Central Banking (10 May 2026): price vs quantity absorption ranking across G10, oil → fixing → policy chain
- JWS Macro - Global Rates Outlook #4: Too Much Growth Fear, Not Enough Inflation Fear (8 Apr 2026): outcome of the Euribor fwd-fwd inversion trade
- JWS Macro - Global Rates Update #7: Same North Star, Worse Weather (19 Jul 2026): gas over oil for EUR inflation
- JWS Macro - Central Casting #6.1: The Fed Credibility Trade & The Task Force Tail (21 Jun 2026): MoU rallies as chances to reload shorts
- Citi Research - US Rates Weekly: Trade worries linger (Mathai et al., 17 May 2019): tariff growth/inflation table, China UST-selling constraint read, swap-spread reaction
- Citi Research - US Rates Weekly: Deal or no deal: Rates implications (Mathai et al., 10 May 2019): trade-war escalation map for RV positions
- J.P. Morgan - 'Truth' and consequences: social media posts and rates during the Middle East conflict (Ozil, Hayward, Alptuna, 16 Jul 2026): intraday event study vs random control, tail effects, decay
- J.P. Morgan - US Interest Rate Derivatives: Near, far, wherever yields are (2 Oct 2026): vol-rate beta flip and zero-duration-spread drop on a flight-to-quality day
- Goldman Sachs FICC & Equities - GS Macro, cuRated: 2Oct26 (3 Oct 2026): daily UST moves on escalation vs flight-to-quality days, swap-spread crowding, regime marker
- Conks (Monetary Mechanics) - Plumbing Notes: War & Plumbing (11 Mar 2026), War & Short-end Rates (23 Mar 2026), The Peak-TACO Era (9 Apr 2026): dollar-funding split, safe-haven plumbing trades, excess hikes priced out
- Conks (Monetary Mechanics) - Money Market Update: Plumbing Notes: QT For (a Little) Longer (15 Sep 2025): custody data are not proof of reserve-manager selling
- Geopolitical Cousins podcast (M. Papic, J. Shapiro) - "Scotty doesn't know" episode transcript (~Sep 2026): three US "vibes" sell-offs, the bond market as the ultimate constraint
- Citi Research - Global FX: Twelve questions about concerted JPY-buying intervention (Takashima, Tobon, Levine, 29 Jan 2026): intervention history and thresholds
- Citi Research - Japan FX: What are Secretary Bessent's plans to assist PM Takaichi's JPY defense? (14 Aug 2026) and Japan Economics: Regime shift in BoJ policy (Nakamura, 7 Aug 2026): intervention thresholds, reaction-function change after intervention
- Citi Markets - STIRT Weekly: Tokyo, we have a problem... (7 Aug 2026): size discipline in geopolitically driven markets, post-intervention JPY funding normalisation
- Citi Markets - STIRT Weekly: You Shall Not Pass (14 Aug 2026): SONIA's high beta to European gas headlines
- Citi Research - Global FX Strategy: Long NOKSEK (Tobon, Levine, Takashima, 21 Aug 2026): option structure spanning a geopolitical catalyst window
- Stephen Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): short-lived flight-to-quality spikes in STIR
- The White House - National Security Strategy (Nov 2025) and U.S. Department of War - National Defense Strategy (Jan 2026): allied defence target of 3.5% + 1.5% of GDP, a structural issuance driver
- Financial Times - Mark Carney says Canada is now 'at war' with US over trade (Gridneff, Aug 2026): US-Canada tariff escalation
- Caldara, D. and Iacoviello, M. - Measuring Geopolitical Risk (American Economic Review, 2022) (external): the GPR index
- Heuer, R. J. - Psychology of Intelligence Analysis (CIA Center for the Study of Intelligence, 1999) (external): diagnosticity of evidence, the basis of the constraint method
