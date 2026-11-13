---
name: macro-central-bank-nlp
description: Score central-bank communication (speeches, statements, minutes, press conferences) for hawkishness and turn the score into G10 rates signals. Covers sentence hawk/dove scoring, the relevance-weighted document Hawk-Dove Score (-100..+100), the 90-day speaker average, a speaker surprise index and topic mind-share. Maps the score to the 1y rate change, meeting hike probabilities and statement tone, and to forward-curve fair value on G10 HDS factors (PC1/PC2) with residual z-scores, cross-market relative-HDS spreads and FX, and HDS dispersion as a vol input. Bundles a dictionary scorer with negation handling. Use when a trader asks about Fedspeak or ECB/BoE/BoJ/BoC/RBA/RBNZ/SNB/Riksbank/Norges tone, a hawkish or dovish shift, the hawk-dove score (HDS), central bank sentiment, NLP/LLM scoring of FOMC minutes or statements, press-conference tone, forward-guidance language, minutes quantifiers, whether the front end is cheap vs rhetoric, rhetoric vs pricing, or relative CB hawkishness for cross-market spreads.
---

# Central-bank communication NLP: hawk/dove scores as a rates signal

Central-bank rhetoric moves far more often than policy rates, and the front end prices it. A sentence-level
hawk/dove score, aggregated over every speech in the last 90 days, gives a daily, systematic read of policy
intent. It leads the next statement's tone and short-rate changes by up to ~8 weeks. Used as a fair-value
regressor, it shows when forwards are cheap or rich relative to what central bankers are saying (J.P. Morgan,
Welcome to the machine, Apr 2023; J.P. Morgan, Talk is Cheap, May 2024). The score is a *conditioning and
fair-value input*. It explains a minority of rate variance (regression SE 30-40bp), so it never stands alone as
a trade trigger.

## When to use
- "Has Fedspeak / ECB / BoE / RBA tone turned hawkish? By how much, and is it priced?"
- "Score today's speech, statement, minutes or press conference. Is it a surprise vs the speaker's usual stance?"
- "Is 1y1y (or 2y1y, 3y1y) cheap or rich vs central-bank rhetoric?" Front-end fair value across G10.
- "Which central bank is most hawkish relative to the Fed?" Relative HDS for cross-market spreads or FX.
- "Do the minutes really show a hawkish shift?" Quantifier counts vs sentence scores.
- Building or auditing an in-house hawk/dove scorer: rubric, labels, model choice, evaluation.
- Adding a text-derived regressor to a curve, swap-spread or vol model.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| CB texts: speeches, statements, minutes, pressers, Q&A, testimony | `cb_texts`: `doc_id, cb, speaker, role, doc_type, pub_ts_utc, lang, ref_meeting_date, text, source` | per document; ≥ 1 full cycle (≥ 5y for fair value; scored history exists back to 1998) | `pub_ts_utc` is the knowledge time. Q&A must be attributed so only the official's words are scored |
| Third-party or in-house HDS, topic shares | `macro_series` (`unit = score`; e.g. `US-CB-HDS-SPEECH-3M`, `US-CB-HDS-STMT`, `US-CB-TOPIC-INFL`) | daily, one row per vintage | store `model_version` in `source`; a re-scored history is a new series |
| Meeting schedule | `cb_meetings` | all G10 banks | defines inter-meeting windows |
| Policy rate decisions | `rate_fixings` (policy-rate series) | daily | for the ELB dummy and the `1y − policy` control |
| 1y govt yield, OIS par curve | `curve_par` | daily close, ≥ 5y | derive the 1y forwards (0y1y, 1y1y … 10y1y, 15y1y) from the par curve |
| Meeting-implied probabilities | `events_probs` (`venue = implied_ois`) | per meeting | compare with HDS-implied probabilities |
| Macro forecast revisions (growth, inflation) | `macro_series` | weekly/monthly | controls in fair-value regressions |
| FX spot | `fx_rates` | daily | relative-HDS vs FX |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent a score, and never
back-fill history with a model version that did not exist at the time.

## Method

### 1. Corpus and point-in-time hygiene
- Keep one series per document type: speech average, statement, minutes, press conference. A statement is not a
  speech, and mixing them is not like-for-like.
- Timestamp every document at publication. A speech scored at 15:00 UTC enters the signal for that day's close
  only if it is before the snap; otherwise it counts for the next day (script `--cutoff-hour-utc`, set to the
  market's snap).
- Strip greetings, slide captions and moderator questions. In Q&A, score only the central banker's paragraphs.
- Store `n_sent`, `relevance` = Σw/N and `relevance_scored` = Σw/N(w>0) per document. A low-relevance document,
  such as a supervision or financial-literacy speech, carries little information. For example, Warsh press
  conferences scored only 30-40% monetary-policy relevant (J.P. Morgan, Global Fixed Income Markets Weekly,
  21-22 Aug 2026).

### 2. Score sentences (three stages)
1. **Relevance filter.** Keep a sentence only if it contains a concept from a taxonomy covering inflation (core,
   energy, housing/shelter, wages, expectations), labour, growth, monetary policy (rates, guidance, balance
   sheet, YCC) and financial conditions. The production taxonomy has 82 concepts and 263 rules, growing to 302
   patterns in 2024. It removes ~46% of sentences.
2. **Relevance weight** w_i ∈ [0, 1]: does the sentence state a hawk or dove opinion?
3. **Hawk-dove score** θ_i ∈ {0, 0.25, 0.5, 0.75, 1.0}, from most dovish to most hawkish.

Two implementations:
- **Dictionary baseline** ([`scripts/cb_text_score.py`](scripts/cb_text_score.py)). Pair each direction word with
  the nearest topic word; unemployment and slack invert the sign. Policy-action words count ±2. Negation flips
  the sign. Hedges cap θ at 0.25 / 0.75. The baseline is transparent and needs no labels. Its weak points are
  conditionals, goal clauses and context.
- **Supervised ordinal model.** Use a domain-adapted transformer with an ordinal head, trained on ≥ 3-4k labeled
  sentences per central bank, spanning low- and high-inflation regimes. It reaches A-2 (hawk vs dove) ≈ 0.90 and A-5 ≈ 0.57. Few-shot chat prompting gets
  A-2 ≈ 0.66 (J.P. Morgan, Listen up, Jul 2024).

Read [references/labeling-models-and-documents.md](references/labeling-models-and-documents.md) before building
or auditing a scorer. It covers the rubric, hard cases, label counts, the model table, metric formulas and the
G10 document map.

### 3. Document score
```
w̃_i   = w_i / Σ_i w_i
HDS_k = 200 · Σ_i w̃_i · (θ_i − 0.5)        ∈ [−100, +100];  > 0 hawkish, < 0 dovish
```
The units are ordinal, but **the zero line has meaning**. Do not read +40 as "twice as hawkish" as +20.

### 4. Aggregate to a daily series
- **Speaker average (main series).** A relevance-weighted average of every speech in the trailing 90 days:
  `HDS_t = Σ_k Ω_k · HDS_k`, where `Ω_k = W_k / Σ_k W_k`, `W_k = Σ_i w_ki`, over documents with
  `t − 90d ≤ date_k ≤ t`. It does **not** weight by speaker importance: a Chair counts the same as a Governor at
  equal relevance. 90 days is long enough to average out single-speech noise and short enough to track a turn.
  The window matters most for banks with few speakers.
- **Dispersion band.** Report the relevance-weighted SD across speeches in the window as the ±1 sd band. A wide
  band means a divided committee.
- **Speaker baseline.** Keep each speaker's average over their previous 5 speeches, excluding the current one. A
  speech's surprise is its HDS minus that baseline.
- **Surprise index (HDSI).** `HDSI_t = Σ (HDS_k − HDS_prev(speaker_k))`, cumulated across speakers. This is more
  timely than the 3-month average, and it removes the fixed effect of persistently hawkish or dovish speakers
  (J.P. Morgan, Listen up, Jul 2024).
- **Topic mind-share.** Report the share of sentences on inflation, labour, growth and policy, as a 3-month average
  and per document. A shift of airtime toward inflation and away from labour is a signal in its own right (see
  step 5f).

### 5. Map the score to rates
**a. Change in short rates (daily, from 1998)**
```
Δ90d[3m-avg 1y yield]_t (bp) = a + b·HDS_{t−7d}
                              [+ c·Δ90d[...]_{t−90d}] [+ ELB dummy × (HDS, lagged change)]
```
| CB | b, univariate (bp/pt) | b + lagged change | outside / inside ELB | full model, outside ELB | fit |
|---|---|---|---|---|---|
| Fed | 1.4 | 0.7 | 2.2 / 1.1 | 1.1 | SE 33-39bp; adj R² 0.26-0.45 |
| ECB | 1.2 | 0.8 | 1.6 | 1.2 | adj R² 0.21-0.30 |
| BoE | 1.2 | 0.8 | 1.6 | 1.1 | adj R² 0.11-0.19 |

Rule of thumb: **an HDS level 10 points higher ≈ +10bp more on the 90-day change in the (3m-average) 1y, outside
the ELB.** The regressor is the HDS *level*, so a sustained +10 keeps adding ≈ 10bp per 90 days; it is not a
one-off ΔHDS → Δrate mapping. For the Fed, 7bp is worth more than 25pp on the probability of a 25bp hike.
The lead is significant out to 8 weeks and gone by 13 weeks (J.P. Morgan, Welcome to the machine, Apr 2023). Regress *changes* on the HDS *level*. The score is "a better guide to changes
in rates rather than the level". The exception is the BoJ, whose score tracks the *level* of front-end rates
(J.P. Morgan, NLP extended to all DM central banks, Aug 2023).

**b. Speakers lead statements.**
`ΔHDS_stmt = a + b·ΔHDS_speech(inter-meeting) + c·ΔHDS_stmt,lag`. The speech coefficient b is 0.58 for the Fed
(t 6.3, R² 0.81), 0.20 for the ECB (t 2.2) and 0.08 for the BoE (t 1.9). So a +10 rise in Fed speaker tone →
+5.8 points in the next statement.

**c. Hike / cut probability (ordered logit).**
```
r*_t = ρ·r*_{t−1} + b0·S_t + b1·HDS_t + ε,   S_t = 1y yield − policy rate
P(k) = Λ(c_k − r*) − Λ(c_{k−1} − r*)
```
Buckets: cut ≥ 50, cut 25, hold, hike 25, hike ≥ 50. ELB meetings are left-censored. The effect is non-linear.
The score matters most when the bank is already moving and the tone agrees with that direction. In April 2023,
±10 Fed HDS → ≈ ±5-10pp on the next-meeting 25bp-hike probability, with almost no effect on cut probability. b1 is
information *incremental to market pricing*. Compare the model probability with `events_probs`; see
stir-policy-pricing-whats-priced-in.

**d. Forward-curve fair value on G10 rhetoric factors (levels, daily).**
1. Demean the 10 DM HDS series (Fed, ECB, BoE, BoJ, BoC, RBA, RBNZ, SNB, Riksbank, Norges) and run PCA on them.
   PC1 is the global hawk/dove cycle, explaining 54% of variance; every bank correlates with it at about +0.5
   or more (ECB ≈ 0.9, RBNZ ≈ 0.49). PC2 is
   "Follow / Deviate from the Fed": RBNZ ≈ −0.8, SNB ≈ −0.35, BoC ≈ +0.22.
2. For each 1y forward f_m (0y1y … 10y1y, 15y1y):
   `f_m = β0 + β1·PC1 + β2·PC2 + β3·HDS_home + β4·US_growth_FRI + β5·US_infl_FRI + e`.
   FRI is a forecast-revision index; any consensus-revision series serves. The inflation FRI entered only the
   10y and 5y samples (data limits). Leave out lagged rates and other
   market regressors. They raise R² but destroy the interpretation.
3. Fit on the full sample, the last 10y and the last 5y. Residual `e = actual − fitted` in bp, and `z = e / sd(e)`.
   **z > 0 = cheap (forward too high vs rhetoric) → receive; z < 0 = rich.** Past misvaluations tended to correct
   toward the fit (US 2007 overshoot, 2012-13 undershoot). The 2020 HDS-implied negative yields were the
   exception (J.P. Morgan, Talk is Cheap, May 2024). *House guidance, not from the source:* full-sample PCA
   loadings and betas make z in-sample, so for a backtest re-estimate them on an expanding or rolling window
   using only data to t−1. A levels regression on persistent regressors can have a near-unit-root residual:
   check residual stationarity (ADF) and half-life before fading. When every market shows z > 2 at once
   (example 4), suspect a common omitted factor (term premium, neutral-rate repricing) and prefer cross-market
   spreads.
4. For cross-market spreads, regress the matched forward spread vs USD on the same factors, using (Fed − home)
   HDS in place of home HDS (note the sign: Fed − home here, home − Fed in 5e). That gap adds little after
   PC1/PC2. Spreads are driven mostly by each market's
   different betas to the global factors (J.P. Morgan, Talk is Cheap, May 2024).

**e. Relative HDS vs FX and cross-market fronts.** The gap (home CB − Fed HDS) tracks the 3m/3m % change of
EUR, GBP, AUD, CAD, NOK, SEK and CHF vs USD, and the ECB − BoE gap tracks EUR/GBP. Use the gap as one input to a
cross-market front-end or FX model, not as a standalone model (J.P. Morgan, Welcome to the machine, Apr 2023;
NLP extended to all DM central banks, Aug 2023).

**f. Curve and topic share.** Regress ACGB 3s10s on a constant, USD 2s10s, the RBA HDS, the RBA labour topic
share, and (inflation share − labour share), daily since Jan 2020. More inflation-ex-labour airtime goes with a
steeper curve (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026). The same template applies to
any bank whose airtime rotates between mandates.

**g. Vol.** Use the delivered volatility or dispersion of speech scores as a proxy for reaction-function clarity.
The 3M delivered vol of BoE speech HDS above that of the ECB was one rationale for a wider GBP−EUR 3Mx10Y
normal implied vol spread, quoted in bp/day (same source). See vol-rates-options-rv.

### 6. Validate before use
- Use HAC (Newey-West) standard errors with lags ≥ the overlap length. The dependent is a 90-day change in a
  3-month average, so each observation spans ~180 calendar days (≈ 125 business days); use ≥ 125 lags on
  business-daily data. Naive t-stats (the published ones run 6-15) are inflated. Cross-check on non-overlapping
  quarterly samples.
- Use event-window tests against a random-window control. Text effects live in the tails, not the median.
  Example: after keyword-flagged posts, the median net 30-minute 2y move was < 1bp, but the 95th percentile was
  ~1bp above the random-window control, and the typical within-window 5-95 trade-price range (an intraday vol
  proxy) was ~0.6bp vs ~0.4bp. The reaction decayed over time as the market adapted (J.P. Morgan, 'Truth' and
  consequences, Jul 2026).
- Check the rolling R² of any HDS-based model. If the 120-day R² falls sharply (one curve model went from ~100% to
  ~60%), stop fading its residuals.

## G10 differences that change the read
| Market | What the score drives | Note |
|---|---|---|
| USD | bear-flattening response: per 1 sd PC1, 0y1y ≈ 32bp, 1y1y ≈ 17, 2y1y ≈ 12, 3y1y-15y1y ≈ 11-12 | Fed shocks lead other banks within the month; Granger causality beyond one month fails except for the ECB |
| EUR | barbell: 0y1y ≈ 8.5bp, 1y1y ≈ 5.6, 3y1y ≈ 3.3, 10y1y/15y1y ≈ 4.8 | ECB tone is about rates *and* the balance sheet; own-HDS beta higher since leaving negative rates |
| JPY | long end: 0y1y ≈ 0.6bp rising to 15y1y ≈ 8 | YCC legacy; score tracks rate *level*; translated text |
| GBP | largest rise in 1y1y PC1 beta (≈ 29bp/sd, 5y sample) | own-HDS beta negative this cycle; BoE vote split complements text |
| CAD | PC2 beta lower in 5y than 10y sample | BoC followed Fed rhetoric less this cycle; SNB speech can carry information for CAD via the common factor |
| AUD | RBA HDS tracks PC1 closely | topic-share curve model (5f) |
| NZD | negative PC2 loading (≈ −0.8) | led cycles alone (2014, 2022); PC2 beta swung from ≈ −50 to +55 |
| SEK, NOK | own-HDS beta negative this cycle | published rate paths are primary; few speakers → noisy 90-day average |
| CHF | SNB HDS + FX-management language | translated; leaned against the Fed post-GFC |

Sources: J.P. Morgan, Talk is Cheap, May 2024; J.P. Morgan, NLP extended to all DM central banks, Aug 2023.

## Worked examples
**1. Document score (illustrative, reproduced by the script self-test).** Take three sentences:
- "Inflation remains elevated and the labour market is tight." θ = 1, w = 1.
- "The committee met in Frankfurt." Off-topic, w = 0.
- "Growth was in line with our projections." θ = 0.5, w = 0.5.

Then w̃ = (2/3, 0, 1/3), HDS = 200·(2/3·0.5 + 1/3·0) = **+66.7**, and relevance = 1.5/3 = 50%.

**2. Speech surprise vs own baseline.** Powell's 22 Aug 2025 Jackson Hole speech scored HDS −1 against his trailing
5-speech average of 17. His previous document, the 30 Jul press conference, scored 16 (its Q&A 17). The Fed 3M all-speaker
average was 6, down from 12 in mid-May. Topic shares: policy 34%, inflation 26%, labour 17%, growth 16%
(J.P. Morgan, NLP Report: Powell, Monetary Policy and the Fed's Framework Review, 22 Aug 2025). The HDSI
increment is −1 − 16 = **−17**, and the surprise vs the 5-speech average is −1 − 17 = −18: a clear dovish
surprise from the Chair, even though the level is near zero. The 2y fell 11bp on the day, against a 1 sd daily
move of ~5.5bp. Jackson Hole moves that large come only when the Chair signals the near-term path (J.P. Morgan,
US Weekly Prospects, 21 Aug 2026).

**3. Rhetoric vs pricing (screen, 14 Aug 2026).** The 3m speech HDS read US 22.2, EA 17.7, UK 24.0, JP 16.6,
AU 31.4, CA −8.1 and SE 9.2. Over 6 months the US rose +23.0 and the UK +29.4. Market vs economist paths, as the
bp change to end-4Q27: Canada +83 priced vs 0 forecast; UK +54 priced vs −25 forecast (J.P. Morgan, Economic
Activity Tracking, 14 Aug 2026).
- US: with the full-model slope of 1.1bp/pt, a level of 22.2 contributes ≈ +24bp to the 90-day change in the
  3m-average 1y. The SE is ≈ 33bp, so the read is hawkish but inside one SE. No standalone edge.
- Canada: the only dovish score of the seven reported sits next to +83bp of hikes priced. That divergence puts CAD front-end receivers
  (outright, or vs USD 1y1y) on the shortlist. It goes to step 5d fair value and catalyst review, not straight to
  a trade. *This is a screen output derived from the cited data; the source did not recommend the trade.*

**4. Forward fair value (5y model, 1y1y, 30 May 2024).**

| | USD | EUR | JPY | CAD | GBP | SEK | NOK | AUD | NZD |
|---|---|---|---|---|---|---|---|---|---|
| R² | 0.84 | 0.83 | 0.51 | 0.85 | 0.83 | 0.83 | 0.81 | 0.86 | 0.89 |
| residual (bp) | 186 | 142 | 53 | 146 | 192 | 134 | 142 | 194 | 175 |
| z | 2.80 | 2.12 | 3.82 | 2.54 | 2.48 | 2.18 | 2.46 | 3.15 | 2.73 |

Every front end screened cheap (z > 2). A year earlier, z-scores were mildly negative. The read was that the
market doubted central banks would deliver a full cutting cycle (J.P. Morgan, Talk is Cheap, May 2024).
Cross-market version: EUR−USD 2y1y was rich, at ≈ −160bp actual vs ≈ −120bp fitted. JPY has the lowest R², so
rank it last despite having the highest z.

**5. Minutes: score vs quantifiers.** The July 2026 FOMC minutes were the most hawkish in almost two years on a
sentence-level metric (J.P. Morgan, FX Markets Weekly, 21 Aug 2026). But "many" (typically less than half)
thought hikes may be needed, against an evenly split June dot plot. That is no broad hawkish shift (J.P. Morgan,
US Weekly Prospects, 21 Aug 2026). Report both before leaning on the score.

## Signals & interpretation
- **Level:** > 0 hawkish, < 0 dovish. Cross-bank level comparisons are rough. Rank banks by z vs their own
  history.
- **Turn:** |Δ 3m HDS| ≥ 10 points over the last 90 days is economically meaningful: it lifts the step-5a predicted
  90-day 1y change by ≈ 10bp outside the ELB. ≥ 20 is a regime turn. *Both thresholds are house defaults.* If OIS has not moved in the same direction within 2-8 weeks, flag the market
  for a policy-pricing review.
- **Speech surprise:** |HDS_k − speaker 5-speech average| ≥ 20 with relevance ≥ 50% is worth a same-day note.
  Example: a regional president scored +30 against a +5 average. *This 20-point threshold is a house default,
  not from the source. Calibrate it to the speaker-level SD.* Chair, Governor and President surprises count more
  in practice, even though the index does not weight them.
- **Statement preview:** a rising inter-meeting speech average implies a more hawkish statement (Fed slope 0.58).
  Lean on this for the Fed; it is weak for the ECB and BoE.
- **Fair value:** residual |z| ≥ 2 on the 5d model, with R² ≥ 0.7, betas stable across the 5y and 10y samples,
  and the same sign on the cross-market version → candidate. Receive where cheap and pay where rich. Prefer
  spreads to outrights when neutral-rate uncertainty is high.
- **Dispersion:** a widening speaker band, or high delivered vol of the score, means an unclear reaction
  function. That supports owning gamma in that market vs a low-dispersion market.
- **Confirmations:** OIS meeting pricing (stir-policy-pricing-whats-priced-in), the reaction-function narrative
  (macro-central-bank-reaction-functions) and positioning. The score adds information to pricing; it does not
  replace it.

## Pitfalls
- **The ELB breaks the link.** Under QE the score goes deeply dovish while rates cannot fall, which biases b down.
  Add an ELB dummy interacted with the HDS. Rhetoric meant to compensate for the lower bound (2020) produced
  HDS-implied negative yields that never came.
- **The score is noisy.** Single sentences and single speeches are noisy: exact 5-class accuracy is only
  48-58%. Average them.
- **Speaker importance is not weighted,** and slide-deck or rare speakers are mis-scored. Bullard and Broadbent
  scored dovish against market perception, and the Barr financial-stability effect pulls scores dovish.
- **Context:** "whatever it takes" flips sign with inflation vs target. Tag forward guidance as Delphic (a forecast
  of the likely reaction) or Odyssean (a commitment) (Düring, Fixed Income Trading and Risk Management, 2021): long-horizon
  commitments are not credible if they could force action against the mandate. *House note:* a sentence scorer
  treats both the same, so read the type yourself. Balance-sheet, foreign-macro and
  backward-looking sentences need house rules (see the reference file).
- **Look-ahead:** a history re-scored with a newer model is not point-in-time. The v1→v2 upgrade moved scores by
  0.3-0.7 sd. Version every series.
- **Statement and speech series are not like-for-like.** Some published country tables mix them; check which one
  you have.
- **Overlapping-window t-stats:** see step 6. A residual "too steep" or "too cheap" is not faded when the driver is
  global term premium and the model R² is decaying.
- **Keyword filters admit noise.** "oil" let in posts about Venezuela. Translation changes phrasing for the BoJ,
  SNB, Riksbank and Norges Bank.
- **Markets habituate.** Repeated headlines of the same type lose impact. Measure surprise relative to the
  speaker's baseline and to pricing (novelty matters, as with news sentiment: Tulchinsky et al., Finding Alphas,
  2015).
- **Regime change:** fitted betas changed materially across the full, 10y and 5y samples (EUR 1y1y PC1 beta ≈ −8
  long-run, ≈ +10 last 10y, ≈ +5 last 5y). Always show the betas from all three windows.

## Output
1. **Score table** per document: `date, cb, speaker, doc_type, hds, speaker_avg5, surprise, relevance,
   relevance_scored, topic shares, model_version` (the script writes all but `model_version`).
2. **Daily series** per CB, written to `macro_series` (`unit = score`): `hds_avg` (90d), `n_docs`, `dispersion`,
   `hdsi`, and the Δ over 30, 90 and 180 days.
3. **Cross-section panel** (G10): HDS level, z vs own history, 90d Δ, priced hikes or cuts to 6m and 12m,
   HDS-implied 1y Δ (step 5a), the gap, and a flag.
4. **Fair-value table** (step 5d): `market, forward, R², beta_PC1, beta_PC2, residual_bp, z`, for each of the
   three windows.
5. **Charts:** the 90d HDS with its ±1 sd band and speaker dots sized by relevance; HDS vs the 3m/3m change in the
   1y; the residual z heatmap.
6. Hand candidates to rv-trade-idea-writeup. State the rhetoric thesis, the confirming pricing gap, and the kill
   condition: the score reverses by ≥ 10, or the lead window passes 8 weeks without the market following.

## Scripts
- [`scripts/cb_text_score.py`](scripts/cb_text_score.py): dictionary hawk/dove scorer. It splits sentences, pairs
  topics with directions, handles negation ("not hesitate" excepted) and hedges, and outputs θ and w per sentence.
  It then computes the document HDS, relevance and topic shares, the relevance-weighted 90-day speech average with
  dispersion, the speaker baseline and surprise, and the speaker surprise index. Run
  `python scripts/cb_text_score.py --texts cb_texts.csv --out-docs docs.csv --out-daily daily.csv --cutoff-hour-utc 21`.
  `--selftest` checks hand-computed θ on toy sentences (negation, hedge, policy action, unemployment inversion),
  a known document score (+66.7), window-edge aggregation, dispersion, the speaker baseline, the surprise index,
  abbreviation-safe sentence splitting and the snap cutoff.

## Related skills
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-dated pricing to compare HDS-implied moves and probabilities against
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): option-implied meeting-outcome probabilities to set against the ordered-logit HDS probabilities
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): frameworks, leadership and credibility behind the tone
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro-factor fair values; the HDS is one regressor
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA mechanics for the G10 HDS panel and curve betas
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): the 1y-forward grid that the fair-value model prices
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): cross-market front-end spreads from relative HDS
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): regression and residual diagnostics
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): HAC errors for overlapping changes, VAR
- [quant-lead-lag](../quant-lead-lag/SKILL.md): speech→statement and Fed→others lead tests
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): residual z-scores and ranking
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event-window studies of speeches and headlines
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): using HDS dispersion in vol spreads
- [ml-models-for-rates](../ml-models-for-rates/SKILL.md): supervised text models
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): leakage and labeling discipline
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): walk-forward estimation of the fair-value model before trading its residuals
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables, including `cb_texts`
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): hand-off format
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): geopolitical channels and fade/follow rules.

## References
- J.P. Morgan (Lupton, Atlas, Weitzenfeld) - Welcome to the machine: NLP of central bank speak (Global Economic Research, 26 Apr 2023): HDS pipeline and formulas, 90-day aggregation, speaker→statement and HDS→1y regressions, ordered logit, relative HDS vs FX, labeling and active learning
- J.P. Morgan (Jarman, Bassi) - Talk is Cheap: Valuing DM Rates Markets with Central Bank Speak (AU/NZ Rates Strategy, 30 May 2024): PCA of G10 HDS, forward-on-HDS fair value, residual z table, curve-shape betas, cross-market spreads
- J.P. Morgan (Lupton, Weitzenfeld) - Listen up: Upgrading J.P. Morgan's central bank NLP machine (2 Jul 2024): v2 model, accuracy table, evaluation metrics, rubric, context adjustment, surprise index
- J.P. Morgan (Lupton, Weitzenfeld) - Welcome to the Machine: NLP extended to all DM central banks (11 Aug 2023): RBA/BoC/Riksbank/Norges/SNB coverage, BoJ level vs change, relative HDS vs FX, translation caveats
- J.P. Morgan (Lupton, Weitzenfeld) - NLP Report: Powell, "Monetary Policy and the Fed's Framework Review" (22 Aug 2025): report fields, speech score vs trailing average, topic shares
- J.P. Morgan (Lupton, Crook, Gallin) - Economic Activity Tracking (14 Aug 2026): cross-bank HDS snapshot, forecast vs market policy paths
- J.P. Morgan (Diamond et al.) - Global Fixed Income Markets Weekly (21-22 Aug 2026): topic-share ACGB curve model, HDS vol in the GBP-EUR vol spread, low relevance of press conferences, decaying R²
- J.P. Morgan (Feroli et al.) - US Weekly Prospects (21 Aug 2026): FOMC minutes quantifier counting
- J.P. Morgan (Chandan et al.) - FX Markets Weekly: Currencies amid long-end UST shenanigans (21 Aug 2026): minutes NLP reading; check NLP tone before acting on debasement narratives
- J.P. Morgan (Ozil, Hayward, Alptuna) - 'Truth' and consequences: The impact of President Trump's social media posts on rates markets during the Middle East conflict (Global Markets Strategy, 16 Jul 2026): keyword event sets, random-window control, tail effects, habituation
- Tulchinsky et al. - Finding Alphas: A Quantitative Approach to Building Trading Strategies (Wiley, 2015): news-sentiment novelty, relative sentiment, expected vs unexpected
- Düring, A. - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): Delphic vs Odyssean forward guidance (after Campbell et al.)
- Hansen, A. and Kazinnik, S. - Can ChatGPT Decipher Fedspeak? (2023) (external): LLM vs fine-tuned classifiers on FOMC statements
- Apel, M. and Blix Grimaldi, M. - The Information Content of Central Bank Minutes (Sveriges Riksbank Working Paper, 2012) (external): topic × direction dictionary hawk/dove index
- Hansen, S., McMahon, M. and Prat, A. - Transparency and Deliberation within the FOMC: A Computational Linguistics Approach (Quarterly Journal of Economics, 2018) (external): topic models on FOMC transcripts
- Loughran, T. and McDonald, B. - When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks (Journal of Finance, 2011) (external): why domain-specific dictionaries beat general sentiment lists
