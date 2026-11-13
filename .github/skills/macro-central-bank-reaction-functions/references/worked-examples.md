# Worked examples and cycle statistics

Each example is either quoted from the cited source (dated) or recomputed here. Where a source's own arithmetic does
not reproduce, the discrepancy is noted. Run `scripts/reaction_rules.py --selftest` to confirm the formulas.

## 1. Taylor-type anchor (recomputed)

Policy rate = r* + pi + 0.5 (pi - pi*) + 0.5 gap, with r* = 2, pi* = 2 (Taylor-type form, as in Duering, Fixed Income
Trading and Risk Management, 2021, eq. 20.1).

- Inflation 3.0%, gap +1.0: 2 + 3 + 0.5 + 0.5 = **6.0%**.
- On target (pi = 2, gap = 0): 4.0%. This case cannot tell weights apart. Do not use it as a test.
- Inflation 4.0%, gap -2.0: 2 + 4 + 1.0 - 1.0 = **6.0%**.

Use it as a bound. Duering notes the Taylor rule "works well as an ex-post explanation ... much less well as a forecasting
tool" because the output gap cannot be measured in real time. Willer and Saunders (Trading Global Macro Markets, 2026)
found no Taylor specification with a high out-of-sample Sharpe.

## 2. Terminal bound from a rule grid (quoted)

BofA (Start of rates bite, 2 Oct 2026): a Taylor grid of unemployment 4.0-4.5% by core PCE 2.25-3.40% gives a
terminal of about 4.9% (unemployment 4.0) falling to 4.4% (unemployment 4.5) at core PCE 3.0%. The same note reads a
core PCE of 3.0% as a peak Fed funds of 4.8%. Use it as a bound, not a point forecast.

## 3. Real policy rate cycle (quoted)

Real Fed funds = nominal policy rate minus core PCE. In a typical tightening cycle the real rate peaks at 2.5-4.5%,
and reaching the low end implied a 5.5% terminal in one source's history check (BofA, Start of rates bite, 2 Oct 2026).
Sanity-check any terminal call against this range.

## 4. Market-implied neutral (quoted, EUR)

r*_mkt = 2y1y nominal swap rate minus 2y1y inflation swap. Nordea (EUR rates: Pushing back, 17 Jan 2024) read it at
about 0 in Jan 2024 against about +250bp in 2007-08 and about -200bp in 2021. With a 2% target, neutral deposit rate
= 2%, so pricing back to 2% is "merely a normalisation"; easing means going below 2%. The same source warns "0% r*
is not a level that markets have often priced."

## 5. Meeting strip to probability (recomputed)

- P(full 25bp move at a meeting) = (forward - current) in bp / 25.
- 10bp of the meeting-period rate above the current rate: 10 / 25 = **40%**.
- ECB example: 21bp priced for the September 2026 meeting, quoted as 84% (Citi, STIRT Weekly, 7 Aug 2026):
  21 / 25 = 0.84. The arithmetic matches.
- Joint probabilities are not meeting-date probabilities. "50%/50% at two consecutive meetings means one hike with
  uncertain timing" (Duering). Probabilities derived from individual meetings do not add to a joint path.

## 6. FF6 minus FF1 screen (quoted, US, Willer and Saunders 2026, Table 5.6)

FF6 minus FF1 (bp) at the signal date, followed by the change in the effective fed funds rate over 3m and 6m (bp):

| Signal date | FF6-FF1 | FF change 3m | FF change 6m |
|---|---|---|---|
| May 1995 | -19 | -25 | -25 |
| Feb 1998 | -13 | 0 | 0 |
| Aug 1998 | -13 | -75 | -75 |
| Sep 2000 | -15 | 0 | -100 |
| Oct 2006 | -15 | 0 | 0 |
| Feb 2007 | -17 | 0 | 0 |
| Jul 2007 | -19 | -50 | -100 |
| May 2019 | -16 | -25 | -75 |
| Mar 2023 | -34 | +50 | +75 (failure) |
| Nov 2023 | -13 | 0 | 0 |
| May 2024 | -16 | 0 | -50 |

Reading: most signals are followed by cuts or no hikes, but the one large miss (Mar 2023) came in a high-inflation
cycle. Treat -12.5bp as a screen, and do not use it alone when inflation is high. Many results rest on fewer than 25 events.

## 7. Curve inversion to cut (quoted, Willer and Saunders 2026, Table 5.8)

Inversion of at least 12.5bp. Share of signals followed by a cut within 6m / 12m / 24m, and average months to first cut:

| Inversion | 6m | 12m | 24m | Avg months | Max months |
|---|---|---|---|---|---|
| 6m2s | 57.9% | 73.7% | 84.2% | 12.0 | 54.1 |
| 2s5s | 53.3% | 73.3% | 93.3% | 7.7 | 26.9 |
| 2s10s | 50.0% | 57.1% | 85.7% | 11.4 | 30.1 |
| 3m10s | 39.1% | 52.2% | 100% | 10.3 | 23.4 |
| Median (all rows) | 43.8% | 65.0% | 93.3% | 10.5 | 26.8 |

Receiving the 10y after a 6m2s (6m versus 2y) inversion of at least 12.5bp returned +0.78% at 1m and +1.71% at 3m, with a
70% hit rate at both horizons (Willer and Saunders 2026, Table 5.7). Inversions whose short leg is 5y or 10y returned
negative on average. Front-end inversions (6m2s, 2s5s) are the best cut signals. The
2s10s measure scores poorly. Sample sizes are small and transaction costs are ignored.

## 8. Cycle medians, post-1986 (quoted, Willer and Saunders 2026, Tables 5.3 and 5.4)

- Hiking cycles: 12 months, 8 hikes, average move 0.29%, total 2.62%, median 8 months to the first cut.
- Easing cycles: 8 months, 4 cuts, average move 0.37%, total 2.25%, median 14 months to the first hike (mean 24).
- Easing is faster because emergencies are growth or financial-accident driven. The text's 8/14 pause figure conflicts
  with the table. Prefer the table.
- Soft-landing easing cycles (Jul 1995, Sep 1998, 2024) each delivered 75bp of cuts, lasting 2 months (1998) to 7
  months (1995) (Willer, Ch.8). Rates rally into the first cut; take profits soon after the cycle starts, since the
  trough comes when one cut is left (Willer and Saunders 2026).

## 9. Cycle-timed trades (quoted, US, Willer and Saunders 2026)

- Pay the 2y about 3 months (75-55 trading days) before the first hike. Paying earlier carries negatively.
- 2s10s DV01-neutral flatteners from about 50 trading days before the first hike.
- Press receivers about 3 months before the first cut. The largest countertrend sell-off in that window was 21bp (2001).
- Receive the 2y around the last hike. Late-cycle bear steepeners stopped out such receivers: 2006 by 36bp, 2007 by
  28bp, 2023 by 93bp.
- Pay into the last cut only if the Fed is expected to hold for 6m or more. Median 1y-out hikes priced at the last cut
  was +50bp, rising to +66bp 6m later, which the source says are exaggerated on average.

## 10. Expectations vs forwards (quoted, Ilmanen, Salomon Brothers, June 1995)

Dec 1981-Dec 1994, average 6m change: 3m forward +0.80, survey -0.26, actual -0.25; 30y forward +0.10, survey -0.14,
actual -0.24. The forward-minus-survey gap on the 3m bill was 80 - (-26) = 106bp. Scaled by the 0.25 duration of the extra 3m, it is the
expected six-month excess return of a nine-month bill over a six-month bill: 106 x 0.25 = 26.5bp, about 53bp annualised. Forwards
implied rising rates and flattening that did not happen. Do not equate forward-implied changes with expectations
without netting the premium.

## 11. Mean vs mode of market-implied policy (recomputed, illustrative)

If the central bank's modal path is a flat rate, the forward settles on the mean. For log-normal X with log-volatility
sigma: mode = exp(mu - sigma^2), mean = exp(mu + sigma^2/2), so mean = mode x exp(1.5 sigma^2). Illustration with
sigma = 0.20: exp(0.06) = 1.062, so the mean sits about 6% above the mode. The gap grows with forward-rate volatility
(Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022).

## 12. BoJ 2y OIS scenario grid (quoted, Citi, Japan Rates Weekly, 2 Oct 2026)

Market 2y OIS at 194bp on 1 Oct 2026. Cells are 2y OIS in bp for terminal 175 / 200 / 225 / 250:

- Oct start, every meeting: 169 / 190 / 210 / 228.
- Oct start, quarterly: 168 / 186 / 201 / 212.
- Oct start, every 3 meetings: 166 / 181 / 191 / 196.
- Dec start, every meeting: 166 / 186 / 204 / 220.

Discrepancy: the source summary says the 2y exceeds its current level "only if the terminal rate is above 225bp".
Reading the cells at a 225bp terminal: above 194 are Oct-every-meeting (210), Oct-quarterly (201) and Dec-every-meeting
(204); below 194 is Oct-every-3 (191). So the 225 terminal already clears the market on most paths. Use the grid cells,
not the summary sentence.

## 13. Jackson Hole reaction (quoted, JPM US Weekly Prospects, 21 Aug 2026)

2y UST reaction to chair speeches: 2019 -10bp, 2024 -9bp, 2025 -11bp, 2009 +10bp, 2008 +9bp. One standard
deviation of daily 2y changes since 2000 is about 5.5bp. Large moves come only when the chair signals the near-term
path. A chair who avoids guidance should produce a muted reaction, as in the Greenspan years.

## 14. FX intervention arithmetic (recomputed)

- Original estimate 30trn yen; used 11.7 + 13.8 = 25.5trn; remaining 30 - 25.5 = 4.5trn.
- Practical limit 36trn; remaining 36 - 25.5 = 10.5trn (Citi, Global FX Strategy, 3 Aug 2026).

## 15. Price-gap cross-check (quoted, Hudson Bay Research, Jul 2026)

P* = M V*/Y* (money times trend velocity over trend output). Gap = P* minus actual P. Regression of quarterly inflation
change on the lagged gap: coefficient about 0.10 per 1pp of gap, t about 3.9, R-squared 0.18 to 0.19. Current gaps of
-0.36 to +0.79 imply inflation change of -3.5bp to +8bp next quarter, "approximately neutral". Use as a cross-check.
Most quarterly inflation variation is not explained by money (R-squared 0.18).

## 16. Fed balance-sheet breakeven (recomputed; source figure differs)

Breakeven IORB = asset income / share of interest-bearing liabilities = 2.43% / 64% = 3.80%. The source states 3.82%.
The difference is input rounding. The point is that a negative Fed NIM does not limit tightening. The cost is political
(BofA, US Rates Watch, 24 Feb 2022).

## 17. Energy shock to front end (quoted, JWS #3, 8 Mar 2026)

Brent from $70 to $90 in a week (more than 50% year to date). Central Europe (CZ, HU, PL) 1y1y rates +60 to +100bp in a week. ECB pricing for Z6 went from about -15bp (a cut) to about +25bp (a full hike), roughly 40bp of repricing. The rule of thumb was $10 Brent about 30bp on near-term euro-area HICP, so the $20
move is about 60bp of HICP. The source notes "ECB either hikes in the Summer or likely doesn't have a reason at all".

## 18. Fed-speak repricing (quoted, Citi, US Economics Weekly, 2 Oct 2026)

Hike pricing for the October FOMC fell from about 16bp to about 5bp after two officials pushed back. Odds for the 28
Oct FOMC fell from about 70% to about 30%, about 10bp of hikes priced out. Use as an example of how quickly guidance moves
one meeting.

## 19. Hawk-dove score (pointer only)

The hawk-dove score method belongs to macro-central-bank-nlp. One result is worth knowing here: for the Fed, the
lagged statement coefficient was 0.66 and the speech coefficient 0.58, so 10 speaker points moved the statement by about
5.8 points (J.P. Morgan, Welcome to the machine, 26 Apr 2023). Use it only as a cross-check on the path read.

## 20. Source conflicts to flag, not resolve

- Fed hike triggers differ by note and date: 3m SA core PCE above 3.5% with unemployment 4.0% (JWS, 10 May 2026); July
  live trigger 4.2% unemployment and 0.3% core (JWS, 19 Jul 2026). Use the current data, not either trigger.
- Fed terminal: BofA's grid reads 4.8% at core PCE 3.0 (2 Oct 2026). A JWS author's required tightening of 75-100bp,
  to about 4.5% (JWS, Central Casting #6.1, 21 Jun 2026). Both are dated views, not comparable point forecasts.
- Fed September 2026: JPM (14 Aug 2026) expected no September hike but a hike by year-end. BofA and Citi (2 Oct 2026)
  report a 25bp hike in September. Check the current `cb_meetings` and `rate_fixings` tables, not any single note.
- BoJ JPY-defence fair value: about 163 (Citi two-tier model, 4 Aug 2026), with a 160-162 rebound risk after intervention ends.
