# Geopolitical episodes: rates evidence tables

Back-up tables for [macro-geopolitical-risk](../SKILL.md). Every number is copied from the cited source. Units are
as the source states them, and each table says which convention it uses:

- **Price returns** are in % with **positive = bond price up (rally)**. Willer & Saunders report these. Do not
  convert them to bp: the tables give no durations.
- **Yield and spread shocks** are in bp with **positive = yield or spread up**.

Most samples are small (n = 10 or 11). Use them as priors to re-test on your own data with the event-study recipe
in the skill. They are not trading rules.

## 1. Geopolitically driven oil spikes (WTI)

Source: Willer & Saunders, *Trading Global Macro Markets*, Table 4.1 (Wiley, 2026).

- *Peak move* is the % rise to the oil peak.
- *Peak days* is the number of calendar days from the event to that peak.
- *3m change* is the % change over 3 months.

| Event | Start | Oil peak move | Peak days | Oil 3m change |
|---|---|---|---|---|
| Israel-Arab war / oil embargo | 1973-10-16 | 134.6% | 77 | 134.6% |
| Iran hostage crisis | 1979-11-04 | 27.6% | 89 | 19.4% |
| US bombing of Libya | 1986-04-15 | 67.1% | 34 | -0.3% |
| Iraq invasion of Kuwait | 1990-08-02 | 149.1% | 70 | 43.2% |
| Gulf War | 1991-01-16 | 29.6% | 0 | -34.6% |
| Kosovo bombing | 1999-03-24 | 58.2% | 41 | 20.3% |
| Iraq War | 2003-03-20 | 11.4% | -22 | 7.0% |
| Libya intervention | 2011-03-19 | 34.9% | 44 | -7.7% |
| Crimea | 2014-02-20 | 11.5% | 11 | 1.8% |
| Russia/Ukraine | 2022-02-24 | 42.8% | 12 | 23.9% |
| **Mean** | | 56.7% | 36 | 20.7% |
| **Median** | | 38.8% | 38 | 13.2% |

How to read it:
- A negative peak-days value (Iraq 2003) means oil peaked *before* the start date: the risk premium was priced in
  advance.
- A negative 3-month change means the event's risk premium unwound below its pre-event level.
- Russia/Ukraine 2022: oil peaked on 8 Mar 2022, 12 calendar days (7 trading days) after the invasion. It then
  failed at a second high on 8 Jun 2022.

## 2. Tariff episodes: Trump 1.0 vs Liberation Day

Source: Willer & Saunders, Tables 4.2 and 4.3 (Wiley, 2026). Rates-relevant rows only: price returns in % at each
offset from the event day. Trump 1.0 is aggregated across 11 dates (the statistic is not stated); Liberation Day is
a single date.

- Trump 1.0 uses the 11 tariff dates of 2018-19 identified by Amiti et al. (2021).
- Liberation Day is the 2 Apr 2025 reciprocal-tariff announcement.

| Asset | Episode | -10d | -5d | -1d | 0d | +1d | +5d | +10d | +22d |
|---|---|---|---|---|---|---|---|---|---|
| US 2Y bond | Trump 1.0 | 0.0 | -0.0 | 0.1 | 0.0 | 0.1 | 0.0 | 0.1 | 0.0 |
| US 7-10Y bond | Trump 1.0 | 0.5 | 0.1 | 0.4 | 0.3 | 0.3 | 0.5 | 0.7 | 0.7 |
| Bund futures | Trump 1.0 | 0.4 | 0.6 | 0.2 | 0.2 | 0.3 | 0.5 | 0.8 | 1.2 |
| USD index | Trump 1.0 | 0.1 | 0.2 | -0.1 | -0.1 | -0.1 | -0.1 | 0.2 | 0.2 |
| Energy commodity index | Trump 1.0 | 0.9 | -0.7 | -0.1 | -0.6 | -0.3 | 0.6 | -0.1 | -1.8 |
| US 2Y bond | Liberation Day | 0.2 | 0.1 | -0.0 | -0.1 | 0.3 | -0.0 | 0.1 | 0.0 |
| US 7-10Y bond | Liberation Day | 0.8 | 0.9 | 0.2 | -0.1 | 0.9 | -0.9 | -0.6 | -0.8 |
| Bund futures | Liberation Day | 0.8 | 0.7 | 0.2 | -0.2 | 0.4 | 0.9 | 1.4 | 1.0 |
| USD index | Liberation Day | 0.5 | -0.4 | -0.4 | -0.4 | -2.1 | -1.3 | -4.7 | -4.1 |
| Energy commodity index | Liberation Day | 3.9 | 3.8 | -0.1 | 1.3 | -2.4 | -9.4 | -12.5 | -13.3 |

How to read it:
- **Trump 1.0** was a tariff war on one partner (China). Bonds rallied on growth fears, not inflation fears, and
  the USD firmed against CNY.
- **Liberation Day** was a tariff war against everyone. USTs rallied for one day and then sold off, while Bunds kept
  rallying and the USD fell 4.7% by day +10.
- The authors' explanation: the broad war hit the US economy more than its partners. Their lesson is "not be overly
  dogmatic about which country is likely to outperform".

## 3. Global trade-tensions scenario (calibrated June 2018)

Source: Golub (ed.), *BlackRock's Guide to Fixed-Income Risk Management*, Ch. 6, Tables 6.2 and 6.3 (Wiley, 2023).

- The shocks are 1-month moves.
- *sd* is the move in monthly standard deviations.
- *Policy shocks* are set by hand. *Implied shocks* come from the risk model's covariance, conditional on the policy
  shocks.

| Asset | Type | Shock | sd |
|---|---|---|---|
| US 10y Treasury yield | policy | -35bp | -1.8 |
| US 10y inflation (TIPS breakeven) | policy | +20bp | 2.8 |
| Mexico 10y yield | policy | +80bp | 3.1 |
| EM debt spread | policy | +80bp | 3.5 |
| China equities | policy | -20% | -3.3 |
| US dollar | policy | +3% | 1.7 |
| Chinese yuan | policy | -2% | -1.9 |
| Gold | policy | +6% | 2.2 |
| UK 10y yield | implied | -30bp | -1.71 |
| Germany 30y yield | implied | -24bp | -1.63 |
| Japan 10y yield | implied | -4bp | -0.98 |
| Spain 5y yield | implied | +15bp | 0.81 |
| Italy 5y yield | implied | +59bp | 0.86 |
| Japan 10y inflation | implied | +4bp | 0.62 |
| Eurozone 10y inflation | implied | +8bp | 1.43 |
| EUR / GBP / AUD / JPY vs USD | implied | -3.3% / -3.2% / -2.7% / -1.7% | -1.60 / -1.31 / -1.17 / -0.82 |
| Brent | implied | +1.1% | 0.18 |

How to read it:
- The sd column is the plausibility check: Italy 5y +59bp is only 0.86 sd, while Japan 10y -4bp is about 1 sd.
  Scale by each market's own vol before ranking moves.
- The prose says the China equity shock was "three standard deviations"; the table says -3.3. Use the table.
- The scenario was judged more extreme than the 2015 China crash and less extreme than the 2008 crisis.

## 4. Tariff macro mapping (Citi economists, May 2019)

Source: Citi Research, *US Rates Weekly: Trade worries linger* (17 May 2019).

Growth impact in pp by tariff package on Chinese goods:

| Package | China | US | Eurozone | Global |
|---|---|---|---|---|
| $50bn @25% | -0.21 | -0.03 | -0.07 | -0.08 |
| $200bn @10% | -0.33 | -0.04 | -0.11 | -0.12 |
| $200bn @25% | -0.83 | -0.10 | -0.27 | -0.31 |
| $325bn @10% | -0.54 | -0.07 | -0.17 | -0.20 |
| $325bn @25% | -1.35 | -0.17 | -0.43 | -0.51 |

Inflation:
- Existing tariffs add about 0.1-0.15% to core PCE.
- Core PCE could rise by up to about 0.4% on the full 25% applied to $325bn.
- The pass-through table assumes 60% and 100% pass-through.

What the market did: "the Treasury market rallied massively on Monday, indicating that investors are worried
primarily about growth impacts of tariffs rather than inflation". The curve priced a full 25bp cut by end-2019 and
about 1.5 cuts in 2020.

## 5. 2026 Gulf/Iran energy shock: front-end repricing

Sources are cited per row. All moves are in bp, with positive = rates up.

| Market / instrument | Move | Source |
|---|---|---|
| Brent | $70 -> $90 in the first week (from about $60 at the start of the year) | JWS Macro, #3 Iran & Front End Rates, 8 Mar 2026 |
| CE3 (Czech, Hungary, Poland) 1y1y swaps | +60 to +100bp in a week | same |
| EUR: ECB pricing for Dec-26 | from 0 to -15bp (cuts) to about +25bp (a full hike); about 40bp repricing | same |
| EUR: Dec-26/Dec-27 3m Euribor fwd-fwd spread | about +12.5bp; author's target -12.5bp (an adjustment hike, then demand destruction) | same; the author later reported the target hit quickly (JWS, Global Rates Outlook #4, 8 Apr 2026) |
| GBP: SONIA cuts priced to Dec-26 | about 50bp -> as little as about 2bp; RPI shock priced at +80 to 120bp by Q3 | JWS, 8 Mar 2026 |
| GBP: Bank Rate pricing for 2026 | pre-war -50bp, peak +83bp in late March, +57.5bp on 10 May | JWS, Global Rates Outlook #5, 10 May 2026 |
| AUD: RBA | 57.5bp of hikes priced through Dec-26; 1y1y sold off almost as much as any curve despite a low energy weight; author would fade (receive) | JWS, 8 Mar 2026 |
| Excess hikes later priced out (3m futures to Dec-26) | US SOFR 1 -> 0 hikes; UK SONIA 4 -> 1.5; EU Euribor 4 -> 3 | Conks, Plumbing Notes: The Peak-TACO Era, 9 Apr 2026 |
| UST on an escalation day | 2s +7.9, 5s +8.2, 10s +7.6, 30s +5.6; 2s10s -0.3, 5s30s -2.6 (bear flattening); Brent above $108.5 | Goldman Sachs, GS Macro cuRated: 2Oct26, 3 Oct 2026 |
| UST on a flight-to-quality day, same week | 2s -9.6, 5s -7.5, 10s -4.4, 30s -1.6 (bull steepening); OATs at their widest since 2011 | same; "for the first time in a while, the risk-off sentiment translated into a duration rally, despite oil rallying" |

Other observations from the same sources:
- **Hike ranking.** One author ranked the ECB most likely to hike, then the BoE, then the Fed, with BoE and ECB hikes
  of 50bp or less. At one point, 3m Euribor and SONIA futures priced at least the maximum, which he read as peak
  impact (Conks, Plumbing Notes: War & Plumbing, 11 Mar 2026).
- **Oil-to-front-end chain.** Under scenario guidance, the correlation of oil with front-end rates was about 1
  through Dec-26. The chain runs Brent December future -> Dec-26 inflation fixing -> Dec-26 implied policy rate.
  ECB Brent thresholds: baseline about $75, adverse about $92, severe about $115-120 (JWS, 10 May 2026).

## 6. Headline-risk event study (intraday)

Source: J.P. Morgan, *'Truth' and consequences* (16 Jul 2026).

Design:
- **Event set:** posts by the US president that contain Middle East keywords, Jan 2025 - Jul 2026.
- **Response:** net 2Y UST yield change within 30 minutes, computed from trade prints as −(price of the last trade
  in the window − price of the trade nearest the post) / PVBP, so that yield up is positive (a price rise is a yield
  fall).
- **Control:** 1,000 random 30-minute windows.

Results:
- Most posts moved the 2Y by less than 1bp. The effect sits in the tails: the typical 5th-95th percentile intraday
  range was about 0.6bp after posts vs about 0.4bp in random windows, and the 95th percentile was about 1bp higher.
- In the first month of the conflict (Mar-26), the tail was skewed toward yield *increases*. The reaction decayed
  afterwards although the conflict continued.
- **Example, 23 Mar 2026.** A post announced a 5-day postponement of strikes on energy infrastructure. The 2Y fell
  about 4bp in 10 minutes, then ended about +6bp versus the post time once reports said Iran denied any talks.

## 7. Trade-war escalation: what happens to standing RV positions

Source: Citi Research, *US Rates Weekly: Deal or no deal: Rates implications* (10 May 2019).

| Position | Escalation outcome |
|---|---|
| Long breakevens | most vulnerable |
| 1y-forward 2s10s flattener | underperforms: the belly richens and 5s30s steepens |
| Long 30y TIPS | holds up: the breakeven drop is offset by the real-yield drop |
| Long gamma | does best |

## 8. Other shock studies

- **31 exogenous geopolitical shocks, 1962-2017** (Golub ed., Ch. 6, Exhibit 6.1, Wiley, 2023):
  - Equities show modest losses over the 30 trading days after an event, with bonds rallying in the immediate
    aftermath.
  - Losses are larger when US manufacturing PMI is below 50 or when shocks coincide.
  - After 9/11 the S&P 500 fell almost 12% in the first week and had recouped it 25 business days later.
- **GPR spikes** (Willer & Saunders, Ch. 4, Wiley, 2026):
  - A spike is a 100% jump in a month or a move to the 99th percentile. The index peaks within days; 9/11 peaked
    after 14 days and the 1990 Gulf War after 20.
  - US bonds do well into day 0 and for the next 50 trading days. They trade sideways right around the spike.
  - Energy gains about 10% in the 10 days before the spike and then retraces. Gold works with less upside.
  - CHF is the best FX hedge but the move is small; JPY trades a volatile range.
- **Oil up 30% or more within 3 months** (Willer & Saunders, Fig 4.5):
  - Bonds go sideways to down into day 0 and track their unconditional path afterwards.
  - An oil move above 15% combined with GPR at the 95th percentile is read as supply-driven, and equities are not
    much affected.
- **London bombings, 7 Jul 2005** (Aikin, *STIR Futures*, Harriman House, 2012): the Jun-06 Short Sterling future
  spiked 25 ticks and was soon corrected. Flight-to-quality rallies are short-lived.
