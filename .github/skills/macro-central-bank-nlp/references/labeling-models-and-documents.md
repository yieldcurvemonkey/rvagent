# Labeling, model choice, evaluation and the G10 document map

Detail behind [SKILL.md](../SKILL.md). Read this when building or auditing a hawk/dove scorer, not when only
consuming a score.

## 1. Sentence labeling rubric (5 levels)

| Label | θ | Meaning | Example pattern |
|---|---|---|---|
| 5 explicitly hawkish | 1.00 | advocates tightening, or points to inflation / labour extremes | "further increases in rates will be needed" |
| 4 hawkish | 0.75 | "things a hawk would say", without a policy call | "inflation remains uncomfortably high" |
| 3 hedged / mixed | 0.50 | balanced risks, two-sided, conditional | "risks to inflation and employment are two-sided" |
| 2 dovish | 0.25 | soft dovish observation | "the labour market is cooling" |
| 1 explicitly dovish | 0.00 | advocates easing, or points to slack / disinflation extremes | "it is time to lower rates" |
| irrelevant | w = 0 | no monetary-policy content | greetings, history, supervision detail |

The rubric runs explicitly hawkish / hawkish / hedged-mixed / dovish / explicitly dovish (J.P. Morgan, Listen up,
Jul 2024). Explicit labels mean advocating a policy change; soft labels mean statements a hawk or dove would make
(J.P. Morgan, Welcome to the machine, Apr 2023).

**Hard cases. Write the house rule down before labeling starts:**
- *Context dependence.* "We will do whatever it takes to return inflation to target" is hawkish when inflation is
  above target and dovish when it is below. The 2024 upgrade adds an explicit context adjustment for this.
- *Backward-looking sentences* ("inflation rose sharply last year"). The source labels them as if forward-looking.
  Decide, and apply the rule consistently.
- *Balance-sheet comments.* Use the separation principle: QT or QE talk is not automatically rate-hawkish or
  rate-dovish. The source treats it as a possible judgmental on/off switch. For the ECB the balance sheet matters
  for the long end (see the EUR barbell in SKILL.md), so keep a separate balance-sheet flag rather than forcing a sign.
- *Foreign macro comments* ("US tariffs weigh on global growth"): label the implication for domestic policy.
- *Mixed sentences*: label 3 unless one clause clearly dominates.
- *Financial stability*: often reads dovish. This is the "Barr effect": a supervision-heavy Vice Chair scored
  most dovish on the FOMC. Label on the policy implication, not the topic.
- *Synthetic sentences* (e.g. "an increase in labour supply" = dovish) may be used for training only, never for
  validation or test.

## 2. How much labeled data

| Fact | Value | Source |
|---|---|---|
| Labeled sentences for a well-trained single-bank model | 3,000-4,000; returns limited after 4,000 | J.P. Morgan, Welcome to the machine, Apr 2023 |
| Log loss vs labels | ~0.75 at 1,000 → ~0.56 at 3,800 | same |
| Gain from training vs rules/dictionary | accuracy +20-30% with ~4,000 labels | same |
| Relevance classifier, out of sample (v1) | 83% accuracy, but 67% of labels are relevant, so the base rate is 67% | same |
| Production label set (2024) | > 20,000 sentences, small pool of trained economists | J.P. Morgan, Listen up, Jul 2024 |
| Extra labels per newly added bank | ~1,000 (model itself trained on Fed/ECB/BoE labels) | J.P. Morgan, NLP extended to all DM central banks, Aug 2023 |
| Rule filter removes | ~46% of sentences (82 concepts, 263 rules; 302 patterns in v2) | Apr 2023; Jul 2024 |

**Active-learning loop** (Apr 2023): (1) bootstrap noisy labels from rules (inflation up, labour down, policy
tightening = hawkish); (2) uncertainty sampling on transformer embeddings with a random forest, up to ~1,000
labels; (3) switch to BADGE (gradient embeddings + k-means++ seeding), because neural-net probabilities are
poorly calibrated. Labels must span regimes (post-GFC low inflation vs post-pandemic high inflation) and bank
vocabularies (ECB "asset purchase programmes" vs Fed "LSAPs", BoJ "yield curve control").

## 3. Model choice and measured accuracy

Ordinal head: encode labels 1-5 as four binary targets (y>1, y>2, y>3, y>4) with sigmoid + BCE, then
P(y=1) = 1 − P(y>1) and P(y=k) = P(y>k−1) − P(y>k). Relevance head: a separate binary classifier whose
probability (0-100) is the aggregation weight. Any sentence labeled 1-5 counts as relevant. Use one model for all
central banks: they share the vocabulary of monetary economics, so the training data can be pooled.

Out-of-sample results, 3-fold CV × 3 runs (J.P. Morgan, Listen up, Jul 2024):

| Model | A-2 | A-5 | LL | W-LL | RPS | MSE |
|---|---|---|---|---|---|---|
| BERT-base (1 layer unfrozen) | 0.80 | 0.49 | 1.24 | 0.37 | 0.13 | 1.14 |
| Falcon 7B (frozen) | 0.83 | 0.51 | 1.18 | 0.34 | 0.12 | 0.98 |
| Mistral (0 unfrozen) | 0.85 | 0.53 | 1.26 | 0.30 | 0.11 | 0.89 |
| General-purpose embeddings + small head | 0.82 | 0.50 | 1.25 | 0.35 | 0.12 | 1.09 |
| RoBERTa-large, 11 layers unfrozen | 0.90 | 0.57 | 1.05 | 0.22 | 0.10 | 0.81 |
| RoBERTa-large, 2-model ensemble | 0.90 | 0.58 | 1.01 | 0.21 | 0.09 | 0.75 |
| Chat LLM, few-shot prompt | 0.66 | 0.31 | n/a | n/a | n/a | n/a |

Takeaways:
- A domain-adapted encoder with most layers unfrozen beats frozen large models. Accuracy peaks around 11
  unfrozen layers and then declines.
- Few-shot chat prompting is the worst option: discrete outputs, slow and costly.
- Even the best model gets the exact 5-class label right only ~58% of the time. Hawk-vs-dove direction
  (A-2) is ~90%. Use averages, not single sentences.
- Re-scoring history with v2 moved document scores by 0.3-0.7 sd of the v1 series (GBP ~0.67, USD ~0.22).
  **A model upgrade is a new series.** Store `model_version` and never splice versions in a backtest.

**Metric definitions** (p_j = predicted class probabilities, r = 5 classes, e_j = 1 for the true class):
- A-2: accuracy on 1-2 vs 4-5, true 3s dropped. A-5: exact-class accuracy. LL: multiclass log loss.
- W-LL (windowed log loss): −ln(p1+p2) if the true label is 1; −ln(p1+p2+p3) if 2; −ln(p2+p3+p4) if 3;
  −ln(p3+p4+p5) if 4; −ln(p4+p5) if 5.
- RPS = 1/(r−1) · Σ_{i=1..r} (Σ_{j≤i} p_j − Σ_{j≤i} e_j)².
- MSE: score = p·[0, .25, .5, .75, 1], rescaled to [0.5, 5.5], squared error vs the 1-5 label.

Earlier generation (2019, cited in Apr 2023): rules and LDA topic models had high precision and low recall. LDA
was inferior to hand-built topic rules. "Direction vs valence" sentiment rules were backward-looking.

## 4. Dictionary baseline (what `scripts/cb_text_score.py` does) and its limits

Topic × direction pairing, after Apel and Blix Grimaldi (external). Each direction word is paired with the
nearest topic word within 6 tokens:
- contribution = direction sign × topic polarity. Unemployment, slack and spare capacity have polarity −1;
  inflation, wages, employment, growth and rates have +1.
- Policy-action words (hike, tighten, raise, cut, loosen, restrictive, accommodative) count ±2 with no pairing.
- A negator up to 3 tokens before the word flips the sign. "not hesitate", "not only" and "not just" are not
  negations.
- A hedge word (may, could, gradual, somewhat, modest) caps the sentence at θ = 0.25 / 0.75.
- θ: net 0 → 0.5; |net| = 1 or hedged → 0.5 ± 0.25; |net| ≥ 2 → 0 or 1.
- Weight w: 1 if directional, 0.5 if on-topic but neutral, 0 if off-topic.

Known failure cases. Test them before trusting a new lexicon:
- **Goal clauses.** "raise rates to bring inflation down" nets +2 −1 = +1: hawkish, but weaker than intended.
- **Non-policy uses of action words.** "raised concerns", "cut back spending" score as policy actions.
- **Conditionals.** "if inflation rises we would act" scores hawkish. A model reads it as hedged.
- **Long negation scope.** "nor do we see a need to tighten" is caught; anything beyond 3 tokens is missed.
- **Translated text.** BoJ, Riksbank, Norges Bank and SNB English versions are the banks' own translations.
  Phrasing differs, so recall drops.
- **Abbreviations.** The splitter protects a fixed list (U.S., U.K., Mr., e.g. ...). A sentence that *ends* in
  "U.S." is merged with the next one.
- **Slides, tables and Q&A transcripts.** Score them only when the official's words can be isolated.

Use the dictionary to get a transparent, auditable direction signal. Use a supervised model when the 5-point
magnitude matters. A sensible audit: the dictionary and the model should agree on sign for > 80% of
high-relevance sentences. Where they disagree, read the sentence.

## 5. Minutes quantifiers (FOMC style)

| Word | Typical share of participants |
|---|---|
| "all" / "unanimous" | 100% |
| "almost all" | ~90%+ |
| "most" | more than half |
| "many" | typically less than half |
| "several" / "some" | a minority |
| "a few" / "a couple" | 2-4 |
| "one" / "a participant" | 1 |

Only the "most" and "many" rows come from the cited source. The other rows are common Fed-watcher conventions.
Calibrate them against the published dots before relying on them.

Count quantified clauses per stance ("many participants judged further hikes may be needed") and convert to a
committee share. Compare the result with the SEP dot distribution. Example: in the July 2026 minutes, "many"
participants thought hikes may be needed. That reads as only about half the Committee, so there was no broad
hawkish shift relative to the evenly split June dots. "Most" anticipated inflation stepping down (J.P. Morgan, US
Weekly Prospects, 21 Aug 2026). The same minutes scored the most hawkish in almost two years on a sentence-level
NLP metric (J.P. Morgan, FX Markets Weekly, 21 Aug 2026). A sentence-level score and a quantifier count can
disagree, so report both.

## 6. G10 document map (score each type as its own series)

| CB | Decision-day text | Later text | Speaker-level text | Notes for scoring |
|---|---|---|---|---|
| Fed | statement, press conference (+Q&A) | minutes (~3 weeks), SEP quarterly, Beige Book | Board + all Reserve Bank presidents | largest speech flow; minutes quantifiers; dots |
| ECB | monetary policy statement, press conference (+Q&A) | account (~4 weeks) | Executive Board + NCB governors | vocabulary: APP/PEPP/TPI; balance-sheet sentences |
| BoE | Monetary Policy Summary + minutes with named vote split | MPR quarterly | MPC members | vote split is a hard quantitative complement |
| BoJ | statement | Summary of Opinions (~1 week), minutes (after next meeting), Outlook Report | Governor, Deputy Governors, Board | translated; HDS tracks the *level* of front-end rates, not the change |
| BoC | rate announcement, press conference | MPR quarterly, summary of deliberations | Governing Council | few speakers → noisier 90-day average |
| RBA | Board statement, press conference | minutes (~2 weeks), SMP quarterly | Governor, Deputy, Assistant Governors | topic-share curve model (labour vs inflation share) |
| RBNZ | MPS / MPR with record of meeting | | Governor, Chief Economist | published OCR track; few speakers |
| SNB | quarterly assessment, press conference | | Governing Board | FX-management language; translated |
| Riksbank | decision + MPR/update | minutes with members' named views | Executive Board | published policy-rate path; translated |
| Norges Bank | decision, MPR quarterly | | Governor, Deputy Governors | published policy-rate path; few speakers; translated |

Where a bank publishes a policy-rate path (Riksbank, Norges Bank, RBNZ) or dots (Fed), that path is the primary
quantitative guidance. Use the text score to measure drift *between* projection rounds.

The 3-month speaker average matters most for banks with few speakers, where a single speech moves the series
(J.P. Morgan, NLP extended to all DM central banks, Aug 2023). Report `n_docs` alongside the level.
