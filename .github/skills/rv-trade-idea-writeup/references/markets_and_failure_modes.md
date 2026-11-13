# Market notes, a second filled example, and failure modes for trade write-ups

Overflow for [SKILL.md](../SKILL.md). Each item says what it changes in the write-up. Citations are given
inline as (Publisher, Title, Date). Levels quoted here are historical and only illustrate the field; they are not
current and must be re-pulled with their as-of stamp before reuse.

---

## A. Market-specific write-up points

### USD
- **Front-end CA trades.** The CA is futures-implied minus matched-maturity swap, and the swap clearing venue
  changes the level. State the CCP with every CA number (Citi Research, "Sell Blues convexity adjustments, hedged",
  9 Feb 2017; Citi Research, "Turning Green from Blue on short convexity", 6 Jun 2017). Both legs quarterly,
  so the matched swap is quarterly on both sides.
- **Board vs swaption.** Strike of the swaption = Board strike yield + invoice spread. Board vol and swaption vol
  are compared at the same strike, because skew differs by strike (Citi Research, "Trade worries linger", 17 May 2019).
- **Long-end flatteners.** 15y5y / 20y10y and 10y10y / 25y10y flatteners are delta-hedged convexity trades. Callable
  (Formosa-type) supply is seasonal, heavy in January and March, so a supply calendar belongs in the catalysts
  (Citi Research, "Deal or no deal: rates implications", 10 May 2019; J.P. Morgan, "Renewed Formosa supply continues
  to flatten the long end", 21 Feb 2020).
- **Swap spreads.** The 30y spread regression on 5s30s, budget-deficit expectations, variable-annuity hedging flows
  and debt maturity shows the spread is partly a curve trade, since its curve beta has more than doubled. Name both exposures in the risk line (J.P. Morgan, "The long
  and short of it", 3 Aug 2018).
- **FOMC dates.** Fed decisions take effect the day after the FOMC, which matters for the stub OIS. Put the effective
  date in the horizon field, not the meeting date (Citi Research, "Learning on the job", 2 Aug 2019; Citi Research,
  "Forward steepener and vol divergence", 12 Jun 2023).
- **Reserve regime.** Ample, moderate and efficient reserve scenarios change front-end spreads. Write which one the
  trade assumes (Citi Research, "Fixing the plumbing", 30 Sep 2019).

### EUR
- **Horizon anchor = ECB meeting date** (ING, "March ECB: QE or bust", 9 Mar 2020; ING, "March ECB: taking out the
  ECB put", 12 Mar 2020). Each note sets the target and stop around a dated meeting.
- **Futures RV uses liquid contracts only.** Restrict analysis to the first 16 generic contracts, where volume and
  open interest are high (ING, "EUR crisis trades: let's get tactical", 3 Mar 2020).
- **5s10s30s fly.** Across 7 episodes since 2013, 86% of normalisations came with a flatter 10s30s, and the fly
  overshot in 6 of 7 cases by 5 to 10bp, typically within about three months. Do not exit at zero residual (BNP
  Paribas, "EUR curve convexity: lessons from history", 25 May 2021).
- **SSA vs EGB.** SSA swap spreads are stable in sell-offs, so the SSA-EGB spread widens only for agencies funded
  in swaps, not for agencies funded in government bonds. Funding completion rates belong in the note (Citi Research,
  European Rates Weekly, 24 Sep 2026).

### GBP
- **Free-convexity flattener.** A 15y10y / 25y10y delta-hedged flattener had positive carry and a daily breakeven of
  zero in Jan 2020; it was re-hedged on the longer leg every 25bp (Citi Research, "In search of cheap vol", 17 Jan 2020).
  Profit was taken on 26 Mar 2020 at -19bp from -11bp for +$542k (Citi Research, "Eat, pay, spend", 27 Mar 2020).
  Check that against the DV01: 8bp x $50k is about $400k, so the printed figure implies other P&L (carry,
  gamma, hedging) that the note does not split.
- **Pension and ALM flows.** The 20y sector richened on liability hedging. A fiscal-risk premium that fades after an
  election is a dated catalyst (same source).

### JPY
- **BoJ pricing cap.** Policy pricing rarely exceeds about 80% until leaks or direct communication, and does not price
  back-to-back hikes for long (Citi Research, "Macro tapas", 7 Aug 2026). Use this as a limit on the size of a
  one-meeting bet.
- **Yen basis.** The paid basis is preferred for carry. Yen appreciation tightens the basis (Citi Research,
  "Paying the basis (again) into 2025", 13 Dec 2024). Names the funding side in the note.
- **Vol cross-check.** A rates-vol vs FX-vol spread can be the trade. A USD/JPY put spread against 6m10y payers was
  bought because rates vol looked rich to FX vol (Citi Research, "In search of cheap vol", 17 Jan 2020).

### CAD
- **Framework trigger.** The BoC uses overnight repo against upward CORRA pressure; intervention is typically
  triggered when CORRA settles 5bp above target (Goldman Sachs, "Reaching limits", 2 Oct 2026). Write the trigger
  into the catalysts.
- **Curve richness.** CAD 15y5y / 20y5y had a breakeven-to-realised ratio of 2.00, the most expensive curve in that
  2019 table. Use the ratio, not the level, to rank (Citi Research, "Buying vol for less", 25 Sep 2019).

### AUD and NZD
- **Bill-futures flattener, with a flagged mismatch.** The Goldman Sachs AUD bill-futures flattener had entry 13bp,
  target -5bp and stop 25bp, with the market pricing about 35bp of hikes over the next year. Its trade table and
  its text disagree on the opening level (0.19 vs 13). Re-check both before quoting (Goldman Sachs, 2 Oct 2026).
- **Curve flattener with issuance.** AUD 2s10s flattener: entry 36, target 10, stop 50, latest 41 (BofA Global Research,
  "Global Rates Weekly", 2 Oct 2026). A second leg, pay 2y 6s3s basis at 22, target 27, stop 19, was tied to Kangaroo
  issuance in the same table.

### CHF, SEK, NOK
- Only the cross-currency and FRA legs are in the sources. Write them with the basis convention and the FRA
  reference period explicit.

---

## B. Second filled example: receive the belly of a PC-neutral EUR 2s5s10s (Mar 2020)

Use this for a fly with non-DV01 weights, a risk allocation below 100% and a dated horizon. Source: ING Global Markets
Research, "March ECB: QE or bust", 9 Mar 2020. Figures were checked against a secondary reading of the note, not
the full text, so re-check them against the original note before reuse.

| Template field | Value (as printed unless marked) |
|---|---|
| Structure | Receive the belly of the EUR 2s5s10s fly, PC1-neutral weights -2.41 / +2 / -0.66 (2y / 5y / 10y) |
| Direction | Long the belly (receive 5y), short the two wings |
| Convention | Fly = belly minus weighted wings, positive = belly cheap (the weights as printed show the belly at +2) |
| Sizing | Risk allocation 50%, "because of greater market volatility". DV01 not stated |
| Entry | 49.5bp, which includes a 0.5bp charge from a 50bp mid |
| Target | 20bp (**derived**: 29.5bp below entry) |
| Stop | 65bp (**derived**: 15.5bp above entry) |
| Reward / risk | **derived**: 29.5 / 15.5 = 1.90 : 1 |
| Carry and roll | 4.7bp per 3 months, positive. Months-to-breakeven not needed, since carry helps |
| Horizon | June 2020 ECB meeting, or sooner if the March meeting disappoints |
| Named risks | The ECB decides cuts are appropriate after all; the long end of the EUR curve inverts |
| Scenario bound | The source's bound is for the DV01-neutral version (the DV01 fly at -8bp could go to zero; a maximum downside of about 10bp for receivers of the belly). It does not transfer to the PC-neutral weights; say so |
| Why this structure | Direction-neutral weights offset an existing front-end receiving exposure in the book, and raise carry and roll |
| Event overlay | Recommended only for investors with a prior curve position, or with high confidence that ECB rates stay unchanged |

Illustrative DV01 (**not in source**): a PC-neutral fly is a combination of yields, so the printed weights are
DV01 weights. If the belly DV01 is set at $50k per bp for the 50% allocation, the wings scale by the weights: 2y = -2.41/2 x 50k = -$60.3k, 10y = -0.66/2 x 50k = -$16.5k. The net DV01 is therefore about
-$26.8k per bp, so this package is not DV01-neutral. Write that down, because the PC-neutral weights were chosen to
neutralise PC1, not DV01.

Ex-post review in the sources: a related note (ING, 12 Mar 2020) reviewed its trades by premise, not only by
P&L, and recorded that the front-end receiving exposure in a pay-the-belly trade did not work. Do the same.

---

## C. Failure modes to write into the risk line

1. **Thesis overtaken by an outside event.** A receive trade was stopped on its trailing stop after an outside
   event overtook the thesis, and the note said it took the trailing stop seriously (Citi Research, "Global Macro Trade Ideas Radar",
   13 Aug 2026). Write the stop as an order
   and the review rule as "no re-underwriting in the same session".
2. **Positioning overrides valuation.** A short credit fly was unwound by near-term budget relief, and a short OAT
   credit fly lost 9bp against a 76.5bp entry on positioning (Citi Research, "Global Macro Trade Ideas Radar",
   13 Aug 2026). A fair-value gap is not a timing signal when flows are pushing the other way.
3. **Good thesis, bad curve.** A bull steepener in GBP 5s30s lost after a budget event, and a EUR steepener lost
   when sector-thematic moves (described in the source as AI-related) worked against it (same source). Name the
   event that flips the sign.
4. **Vol spike.** Spread wideners suffer when a vol spike breaks spread relationships and forces de-risking (BofA
   Global Research, "Global Rates Weekly", 2 Oct 2026).
5. **Small backtest.** A short backtest with high hit rates is a small sample. Say how many episodes it is. One
   example: holds longer than 40 days were 100% hits, average +14bp, no costs, sample since 2023 (Ade Rhodes,
   "USD 5s30s Swap Spread Flattener", 9 Oct 2025).
6. **Models stay wrong.** Spread models can stay wide for a long time without a macro or fiscal shift. A model
   signal alone is not a thesis (Goldman Sachs, "Reaching limits", 2 Oct 2026; J.P. Morgan, "Non-Stop Dynamics: Unpacking
   the Selloff, Plumbing, and USD/JPY x-ccy Basis", 21 Feb 2025).
7. **Hit rates that do not equal winners over trades.** Recompute every hit rate from its counts and ask what the
   denominator is. Three of five published closed-trade scorecards print a rate above winners / total trades:
   41 of 55 is 75% against 79% printed (J.P. Morgan, "A comprehensive look at convexity hedging", 29 Mar 2019);
   39 of 52 is 75% against 81% (J.P. Morgan, "The long and short of it", 3 Aug 2018); 35 of 48 is 73% against 78%
   (J.P. Morgan, "Zen and the art of gamma maintenance", 9 Mar 2018). Each printed rate fits a denominator a few
   trades smaller (for example 41 of 52 is 79%), which suggests scratch or flat trades are excluded; the definition
   is not stated. Quote the counts, and the denominator you use.

## D. Closed-trade log format (lessons, not only P&L)

Citi Research, "Global Macro Trade Ideas Radar" (13 Aug 2026) closed four trades with one lesson each. The
template in section 11 holds the same fields:

| Trade | Entry | Target / stop | Result | Lesson |
|---|---|---|---|---|
| BoJ flattener | 14.5bp | 0 / 21 | +6bp | Not stated in the source |
| Euribor steepener | 43bp | not stated | -11bp | Sector-thematic ("AI-related") moves worked against it |
| Short 10y OAT credit fly | 76.5bp | 91.5 / 69 | -9bp | Positioning |
| Pay 6m forward GBP 5s30s | 84.6bp | not stated | -$113k | Bull steepening failed after a budget event |

## E. Source inconsistencies to check before reuse

- A combined-leg return in a 2020 Citi note does not tie: 0.75 x 79 + 2 x 23 - 51.5 = 53.75bp, the note says 53.125bp
  (Citi Research, "Eat, pay, spend", 27 Mar 2020).
- Beta-weighted vega pair: 1 unit of 2y30y vs 0.8 of 2y10y printed as $53mn in one issue and $63mn in another
  (Citi Research, "Long Live Formosa", 9 Jan 2017; "Swearing in huge expectations", 13 Jan 2017).
- 15y5y / 20y10y carry: -0.44bp per year in the text, -0.31 in the table (Citi Research, "Deal or no deal", 10 May 2019).
- ING, 3 Mar 2020: a 4s30s entry printed as 101.75 in the text and 103.75 in the 4 Feb note.
- 1y1y basis open level printed as -0.63 in one place and -63 in another (Citi Research, "Can Secretary Bessent and
  Chair Warsh save the curve?", 21 Aug 2026). Check units before you copy.
- Date typos: a trade printed as 1/5/2017 is a 2018 trade; one printed as 4/18/2019 is an April 2018 trade (Citi
  Research, "Sell Eurodollar convexity in Blues", 8 Jan 2018).
- Some 2019 wording calls a flattener a "steepener". Treat it as a flattener, and check the sign of the entry level.
