# Calendar barometers, first-N-day rules and seasonal tables

Published conditional-return tables for the US 10y yield (the only G10 rates series in the source) with equity, dollar
and oil cases as templates, and the arithmetic needed to judge them. Use it to (a) rebuild the same tables on any series
with `scripts/seasonality.py` or a pandas groupby, (b) compare a claim with its base rate, (c) see how fast such
barometers decay. All tables are one observation per year, so every cell is a soft prior (see [SKILL.md](../SKILL.md)
step 3 and the grading rules). Source for all tables unless stated: (BofA, Technicals Explained: In 2025, 14 Jan 2025).
"Our calculation" marks numbers derived here from the printed counts, not published ones.

## 1. Template: the conditional table

For each calendar block B1 (January, or the first 5 trading days) and later block B2 (Feb-Mar, Feb-to-year-end, rest of
January, rest of year):
1. Count B1 up and down years, with average and median change (bp for yields, % for prices).
2. 2x2 table B1 up/down x B2 up/down: count, conditional ratio (share of B2 up given B1), average B1 change, average B2
   change, average combined change.
3. Unconditional B2 up-ratio from the row totals; the edge is the conditional ratio minus this base rate.
4. Fisher's exact test on the 2x2 (two-sided); report n per cell. Cells below 10 observations are anecdotes.
5. Check overlap: if B2 contains or is mechanically tied to B1 (the year contains January; January contains its first
   five days) the correlation is partly arithmetic. Prefer B2 that starts after B1 (Feb to year-end, not the full year).
6. Check stability by decade or by split halves; the table has no memory of regimes.

## 2. US 10y yield, January barometer (since 1963, 61 Januarys, changes in bp)

January itself: up 33 times (54%), average +20, median +13; down 28 times (46%), average -23, median -18; all Januarys
average 0, median +1.

| January | Feb-Mar | n (share) | Jan avg | Feb-Mar avg | Q1 avg |
|---|---|---|---|---|---|
| up | up | 23 (70%) | +20 | +34 | +54 |
| up | down | 10 (30%) | +19 | -36 | -17 |
| down | up | 17 (61%) | -21 | +33 | +13 |
| down | down | 11 (39%) | -27 | -34 | -61 |

| January | Feb-to-year-end | n (share) | Jan avg | Feb-YE avg | Year avg |
|---|---|---|---|---|---|
| up | up | 20 (61%) | +22 | +83 | +105 |
| up | down | 13 (39%) | +17 | -94 | -78 |
| down | up | 12 (43%) | -23 | +85 | +63 |
| down | down | 16 (57%) | -23 | -89 | -112 |

Reading against base rates (our calculation):
- Feb-Mar is up unconditionally in (23+17)/61 = 66% of years, so the headline "70% after a January rise" is 4 points
  above base, and a down January is still followed by a higher Feb-Mar 61% of the time. Fisher on [[23,10],[17,11]]: p = 0.59.
- Feb-to-year-end up: 52% unconditional (32/61); 61% after a January rise, 43% after a fall. Fisher on [[20,13],[12,16]]:
  p = 0.20. The gap is the largest in the set and still not significant at 10%.
- The yield trended for long stretches (1960s-81 up, 1981-2020 down), which induces serial correlation between January
  and later months without any calendar mechanism: year-demean the changes or split at 1981 before trusting the gap.

## 3. First five trading days, US 10y (61 years)

First five days: up 34 times (56%), average +13, median +8; down 27 times (44%), average -9, median -7; all years
average +3, median +3.

| First 5 days | Rest of January | n (share) | First-5 avg | Rest avg |
|---|---|---|---|---|
| up | down | 22 (65%) | +12 | -17 |
| up | up | 12 (35%) | +13 | +23 |
| down | up | 14 (52%) | n/a | n/a |
| down | down | 13 (48%) | n/a | n/a |

| First 5 days | Rest of Q1 | n (share) | Rest avg |
|---|---|---|---|
| up | up | 21 (62%) | +42 |
| up | down | 13 (38%) | -50 |
| down | up | 14 (54%) | +41 |
| down | down | 12 (46%) | -29 |

| First 5 days | Rest of year | n (share) | Rest avg |
|---|---|---|---|
| up | up | 18 (55%) | +76 |
| up | down | 15 (45%) | -130 |
| down | up | 17 (63%) | +79 |
| down | down | 10 (37%) | -95 |

- Source reading: a rise in the first five days tended to reverse over the rest of January (short-term mean reversion) and
  then rise into the end of Q1; the first five days showed little relation to the trend of the full year (a down start was
  followed by a higher year in 17 of 27 cases, 63%).
- Tests (our calculation, two-sided Fisher): first 5 vs rest of January [[12,22],[14,13]] p = 0.30; vs rest of Q1
  [[21,13],[14,12]] p = 0.60; vs rest of year [[18,15],[17,10]] p = 0.60. None clears 10%, and the 65% "reversal" is
  22 of 34 against an unconditional 57% (the rest of January is down in 35 of 61 Januarys).
- Counts in the source sum to one less than the total in places (for example 18+15 = 33 against 34), probably because
  the current incomplete year is dropped; do not reconcile by guessing.

## 4. Other assets, same template (for the shape of the result)

| Asset (history) | January rule | Result and base rate |
|---|---|---|
| US dollar index (50 yr) | Jan up 33 (66%), avg +2.39%, median +2.03%; Jan down 17, avg -1.69% | Jan up then Feb-Mar up 20 of 33 (61%), Q1 avg +5.07%; Jan up then Feb-YE up 21 (64%), full year +8.79%; Jan down then Feb-YE down 9 of 17 (53%), full year -10.24%. Fisher Jan vs Feb-Mar [[20,13],[8,9]] p = 0.39, vs Feb-YE [[21,12],[8,9]] p = 0.37 (our calculation) |
| US dollar index, first 5 days (51 yr) | up 31 (61%), avg +1.12% | after a first-5 down the rest of the year is up 13 of 20 (65%, avg +6.93%); after a first-5 up only 12 of 30 (40%): a weak start is mildly contrarian-bullish |
| Front-month WTI, roll-adjusted (since 1984) | Jan up 21, down 19: "no tendency" | Jan up then Feb-Mar up 14 of 21 (67%); January does not predict the year (55/45 and 47/53 splits); first 5 up then rest of Q1 up 16 of 20 (80%, avg +11.47%) |
| US equity index (1928-2024, 97 yr) | Jan up 60 yr: year up 80% (avg +13.40%), Feb-Dec up 78.33% (+8.92%); Jan down 37 yr: year up 45.95% (-0.72%), Feb-Dec up 59.46% (+3.00%) | unconditional year up 67.01% (+8.01%), Feb-Dec up 71.13% (+6.66%). Fisher Jan vs year [[48,12],[17,20]] p = 0.001 (overlap: January is inside the year); Jan vs Feb-Dec [[47,13],[22,15]] p = 0.065 (our calculation, counts rebuilt from the printed shares) |
| US equity index, first 5 days | first 5 up (64 yr): rest of year up 70.31% (+9.16%); down (33 yr): 51.52% (+3.83%) | overall 63.92% (+7.35%); first 5 and January both up (47 yr): year up 82.98% (+14.79%); both down (20 yr): 40% (-2.48%) |
| US equity index, first 5 days vs rest of January | first 5 up: rest of January up only 56.25% (+0.32%) while all January is up 73.44% | the first-5-day signal largely overlaps the January return it helps form |

Presidential-cycle split of the equity barometer: year 1 with January up (14 yr) is up 78.57% (+13.90%), with January
down (10 yr) up 30% (-3.54%); year 4 with January up (12 yr) up 100% (+17.12%).

Decay of the January barometer for calling the year (equity index): about 90% in the 1950s, about 80% from the 1940s
through the 1990s, 60% in the 2000s, 50% in the 2010s, 60% in 2020-24; all periods 70% for the year and 64% for
Feb-Dec. A calendar rule that scored 80-90% before 2000 and 50-60% since is the typical decay profile: apply the "last
three cycles" downgrade in SKILL.md and prefer the post-decay window as the prior.

## 5. US 10y calendar shapes (direction only)

- Month of year since 1963: average path up into May and down into year-end; February the most likely up month (63%).
  Since 1999: up into May, down through September, bounce in October-November, down in December; strongest rise
  November, strongest fall July. Last 10 years (2015-24): choppy first half, peak in May, low in early August, rise into
  November (up 10 of 10 Novembers), dip into year-end. Averages and up-ratios were computed four ways (full history,
  year 1 of the presidential cycle, since 1999, last 10 years) with no significance tests; the windows overlap and shift,
  so the stable part is whatever persists across all four.
- Rule for reading such a table: the month-of-year screen in SKILL.md step 1 is the test the source omitted. A 63% up
  month on about 60 observations has a two-sided binomial p of roughly 0.07 before the multiplicity of 12 months.

## 6. Presidential-cycle blocks (US 10y, since 1964, 15 terms, average bp change)

| Split | Year 1 | Year 2 | Year 3 | Year 4 | Full term |
|---|---|---|---|---|---|
| All terms, average | +23 (60% up) | -23 | +6 | -3 | +2 (40% up) |
| All terms, median | +44 | -1 | +10 | -1 | -45 |
| Republican | +1 | -84 | +5 | -41 | -119 |
| Democrat (7 terms) | +48 | +47 | +7 | +40 | +141 (100% up) |

First-term full-term change: Democrat +210, Republican -111. Dollar index (13 terms): average year 1 +1.01% (up 62%),
year 2 -2.93%, year 3 -0.74%, year 4 +4.17% (77% up), full term +2.99% (Republican -2.03%, Democrat +8.84%). Front-month
WTI (since 1983, 10-11 terms): average year 1 +13.40%, year 2 +0.06%, year 3 +14.57%, year 4 +2.66%, full term +18.20%;
% up 60/60/60/64/70; median +9.83/+3.37/+6.19/+2.61/+3.40; party and term sub-splits rest on 2-7 terms (a Democrat
second-term year 2 shows 0% up on n = 2).
- Process: bucket changes by year of term and full term, report average, median, % up, n, and split by party, first or
  second term, party x term. In the source's equity version most t-statistics are below 2 and the authors caution that
  limited observations make firm conclusions hard.
- The mean and median disagree in sign for the US 10y full term (+2 average against -45 median), and the source text
  calls the average full term "lower yield" while its table prints +2: use the median and the n, and treat the
  presidential cycle as a hypothesis with no mechanism beyond fiscal-policy narrative (grade C).

## 7. Seasonal windows with in-window drawdown (equity template)

Monthly average return / % up (1928 onward): Jan +1.20 / 61.9; Feb -0.09 / 52.6; Mar +0.59 / 61.9; Apr +1.25 / 64.9;
May +0.01 / 59.8; Jun +0.77 / 57.7; Jul +1.67 / 60.8; Aug +0.67 / 57.7; Sep -1.17 / 44.3; Oct +0.54 / 58.8;
Nov +1.01 / 61.9; Dec +1.28 / 73.2 (month mapping read from the extracted chart labels in order).

| Six-month window | Average | Median | % up | Average correction | Median correction |
|---|---|---|---|---|---|
| May-Oct | +2.26% | +3.11% | 66% | -8.7% | -5.2% |
| Nov-Apr | +5.28% | +5.56% | 70.8% | -6.8% | n/a |
| All windows | +3.92% | +4.77% | 66.61% | -7.85% | n/a |

Three-month windows: all-window average +1.9%; Jun-Aug +3.24% (the "summer rally"), Aug-Oct -0.10% (weakest), Nov-Jan
+3.54%: the May-Oct weakness is back-end loaded, so the "sell in May" rule is really about August to October. The
source's rule is "buy weakness in February and September, sell strength in April, July/August and December/January".
- Method worth copying for rates windows: report the average maximum adverse move inside each seasonal window next to
  the return, so that a +2.26% window with a -8.7% average correction is sized as such.
- Mechanism check: no flow story is given for these equity windows. For rates, a monthly or window table is a candidate
  list for the mechanism-first step, not a signal.

## 8. Source inconsistencies to carry forward

- Dollar-index text gives "19 of 33 (58%)" for Jan up then Feb-Mar up and "20 of 33 (61%)" for Feb-YE, while the tables
  print 20 (61%) and 21 (64%): the tables are used above.
- The first-five-day section is introduced as the 30y yield but analyses the 10y.
- Cross-references to exhibit numbers in the text are stale; counts in some conditional rows sum to the total minus one.
- Cross-check any number from this file against your own rebuild of the table before quoting it; the screen in
  SKILL.md reproduces the up-ratios from the daily series.
