# G10 snap times, calendar rules, roll rules and the break register

Lookup tables for [data-quality-and-timeseries-hygiene](../SKILL.md). Every row is a **default to verify** against the
index publisher, exchange notice or adapter metadata (`calendars`, `fut_static`, `rate_indices`) before use. Where a
source is silent for a market the cell says so; record the value per curve rather than assuming.

## 1. Curve snap (fixing) times by centre

Closes are not synchronous: always carry `snap` and the exact `ts_utc`, and never mix snaps inside one series.

| Centre / currency | Curve snap | Note |
|---|---|---|
| London (GBP, EUR, and most curves) | 4pm London | most curves; check per curve (Deutsche Bank DBIQ, Interest Rate Curve Creation Process, 2 Feb 2023) |
| New York (USD) | 3pm New York | curve close; a house end-of-day snap (for example 17:00 New York) is a different instant from the exchange settlement (about 15:00 ET for SOFR futures) |
| Tokyo (JPY) | 3pm Tokyo | |
| Sydney (AUD) | 4:30pm Sydney | |
| Auckland / Wellington (NZD) | 4:30pm | |
| Singapore | 4pm SGT | outside G10, for cross-market panels |
| Oslo (NOK) | 4pm CET | local close since 27 Apr 2018, previously 4pm London |
| Stockholm / Copenhagen (SEK, DKK) | 4:15pm CET | local close since 27 Apr 2018, previously 4pm London |
| CAD, CHF | not specified in the source | record the snap each curve actually uses |

Consequences:
- **Snap-time break inside NOK/SEK/DKK histories on 27 Apr 2018.** A spread of one of these against a London-snapped
  curve changes its noise level at that date.
- **Asia vs US**: a US move on day T shows up in Asian closes on T+1. For multi-time-zone panels use weekly mid-week
  (Wednesday) closes, rolling 52-week windows (Citi, Decomposing Global Rate Drivers Across EM Asia 5y5y, 13 Aug 2026).
- **Exchange trading date vs calendar date**: a futures store may assign `trading_date` by the exchange's evening roll
  (for CME 17:00 Central) while other tables partition on the ET calendar date. Keep UTC, local time and trading date,
  query both candidate partitions and filter to exact UTC instants. Session-origin documentation can disagree with
  code (06:00 vs 07:00 CT was found in one store) (Internal research notes on a curve snapshot store, 2026).
- **Term SOFR (CME) sampling**: 14 thirty-minute intervals from 7am to 2pm Central; an interval is eligible if any SOFR
  future traded in it; per-interval price is VWAP, else an "optimised mid" from a random-time book snapshot, else the
  prior interval; with no eligible interval the previous day's price is used. So a "fresh" Term SOFR can be a
  carried value (Huggins & Schaller, SOFR Futures and Options, 2022, Ch.3).

## 2. Holiday and observance rules

| Rule | Where | Source |
|---|---|---|
| Saturday holiday observed Friday; Sunday holiday observed Monday | US | Darbyshire, Coding Interest Rates, c.2024, Ch.4 |
| New Year on a weekend moves to the following Monday; substitute days appear | UK | same |
| A holiday on a weekend is lost | euro area | same |
| London 2023 closures: 2 Jan (New Year, observed), 7 Apr (Good Friday), 10 Apr (Easter Monday), 1 May, 8 May (coronation, one-off), 29 May, 28 Aug, 25 and 26 Dec | GBP | same |
| 27 and 28 Dec 2021 were substitute days: 25 Dec 2021 + 1 business day (following) = 29 Dec 2021 | GBP | same |

Where calendars come from: exchange trading calendars (which follow government public holidays) for futures and
options; the index publisher for fixings (the central bank publishes SONIA on London business days); ISDA, ICMA and
SIFMA define calendars for some derivatives and securities. Reconcile all three. Cash-bond and futures calendars differ
(US rate futures and US Treasury cash do not share holidays).

Date arithmetic: under modified following, 28, 29 and 30 Mar 2001 + 6M all land on Fri 28 Sep 2001; going back, 28 Sep
2001 - 6M is 28 Mar by default, 30 Mar with roll day 31, 29 Mar with roll day 29. Some combinations are impossible
(Thu 27 Sep 2001 - 6M with 30th rolls). Store the roll day and an end-of-month flag; never infer IMM rolls.

Settlement: most bond markets settle T+2, US and UK government bonds can settle T+0 in some circumstances. Join vendor
tie-outs on the **as-of close date**, not the "for business" date.

## 3. Futures roll and contract-calendar rules

| Market / contract family | Rule or fact | Source |
|---|---|---|
| UST futures (CME) | first position day beats IMM date (IMM held the expiring contract a median 16 business days late); "deliverable" rule differs from first-position-day on 3.6% (10y) to 14.5% (2y) of days | Internal research notes on series construction, 2026 |
| USD, CAD (vendor preference) | roll on first day of the delivery month; front contract active; Treasury futures last trade about 1 week (10y/bond group) or about 4 weeks (2y/3y/5y) after first delivery | vendor global-preference settings, Apr 2024 |
| EUR, GBP, JPY (vendor preference) | roll on last trade date of the 10y futures; front contract active | same |
| Active-contract selection | either open-interest driven or a fixed rule; differs by currency; record it on the series | same |
| CBOT bond futures | delivery any day of the month, so non-delivery holders exit before the delivery month: rolls earlier | Düring, Fixed Income Trading and Risk Management, 2021 |
| Eurex BTP future | rolls later (partly a non-netting artefact) | same |
| Compounded-RFR 3M STIR futures | roll the 2nd into the 3rd listed contract before a contract enters its reference quarter; Dec-19 to Mar-20 roll cost 138bp at the end of the reference quarter vs 4bp at the start | Huggins & Schaller, SOFR Futures and Options, 2022, Ch.2 |
| 1M arithmetic vs 3M compounded SOFR futures | do not mix in one bootstrap (1M-implied curve sat about 1/6 to 1/2 bp above the 3M curve; wiggles result) | Deriscope blog, 18 Feb 2024 |
| AUD, NZD bank-bill futures | treated by the source as yield-convention contracts valued through a synthetic bond price, so tick value is not constant per bp; read quote type and tick value from `fut_static` | FactSet, Interest Rate Future white paper, 23 Mar 2023 |
| Month-code semantics | legacy IBOR futures: month code = expiry month; RFR futures: month code = start of the reference quarter (expiry the following quarter) | same |
| Implied-repo series | roll 5 days before the delivery month; residual spikes then attributed to CTD-switch anticipation and roll flows | Quantitative Finance Stack Exchange, Treasury futures implied repo thread |
| Specifics / generics | specific bond-futures contracts live ~9 months; serial generics jump at each expiry; "most active" series switch when activity migrates to the back contract | Düring, 2021 |
| Month codes | F G H J K M N Q U V X Z (Jan to Dec); bond futures cycle H M U Z | same |
| Contract-spec change | CBOT bond futures notional coupon changed from 8% to 6% (source: 1998; effective from the Mar 2000 delivery month, verify): price jump | Merrill Lynch, RateLab: Implied Volatility, 7 Oct 2008 |

Fields to carry on every generic series: price field (mid vs last), roll rule, active-contract setting, first delivery
date, last trade date, early-delivery flag, any CTD override and WI inclusion (they change CTD yield and basis).

## 4. Break register (dated)

Create one row per series with the dates that apply; analyses that cross a break use post-break data only or condition
on regime.

| Date | Series | Break | Action | Source |
|---|---|---|---|---|
| 1998 (source; Mar 2000 contract month, verify) | CBOT bond futures | notional coupon 8% to 6% | treat as price jump; do not pool across | Merrill Lynch, 7 Oct 2008 |
| 29 Jan 2016 | JPY interbank | negative rates introduced; interbank volumes fell 75% overnight and took about a year to recover | volume and level break | Düring, 2021 |
| Feb 1998 to Feb 2018 | USD repo proxy | primary-dealer survey GC rate (volume-weighted mean) as a SOFR proxy; Aug 2014 to Mar 2018 NY Fed modelled estimates | proxy, not SOFR (SOFR is a volume-weighted median) | Bowman, FEDS Notes, 2019 |
| 3 Apr 2018 | USD SOFR | first publication | before: proxy only; label | same |
| 27 Apr 2018 | NOK, SEK, DKK curves | snap moved to local close | snap break | Deutsche Bank DBIQ, 2 Feb 2023 |
| 25 Jul 2018 | EUR 5y benchmark | OBL177 replaced by OBL178 (about half a year longer) | fake 2s5s steepening, 5s10s flattening that day | Düring, 2021 |
| Aug 2014 | USD SOFR proxy | GC proxy shifted +1bp before this date | document the shift | BofA, 22 Oct 2020 |
| 28 Jul 2021 (announced) | USD SOFR | standing repo facility: SOFR bounded above by the facility rate | re-estimate on post-Aug-2021 data | Huggins & Schaller, 2024 and 2022 |
| LIBOR to SOFR transition | USD CCBS, SOFR-ASW, 10y swap history | one leg changes index: later data more negative and more volatile | label which kind of series; consider synthetic consistent series; keep LIBOR-era case studies separate | Huggins & Schaller, 2024, Ch.15 and 17 |
| 6 Feb 2023 | EUR/USD IBOR cross-currency curve | removed | series ends | Deutsche Bank DBIQ, 2 Feb 2023 |
| Jun 2023 | USD Eurodollar | becomes SOFR plus a fixed spread; only SOFR-FF spreads carry the secured/unsecured basis | re-run 3M-SOFR-futures vs Eurodollar regressions on 1M-SOFR vs fed funds futures and 3M-SOFR vs fed funds futures | Huggins & Schaller, 2022, Ch.2 and 4 |
| 18 Jul 2024 | USD tri-party benchmark (all-collateral) | fell below the reverse-repo rate while Treasury-only tri-party stayed in range (gap to about 8bp) | benchmark-construction artefact, not tradable | Conks, 12 and 26 Aug 2024 |
| Aug 2026 data | US core PCE | methodology change, expected to lower annual core PCE by 20-30bp | flag comparisons crossing it | Citi, CitiFX Wire Cheatsheet, 24-28 Aug 2026 |
| every 5 years | JP CPI | rebased (base year average = 100) | chain `I_old = I_new * <I_old>/<I_new>` | Düring, 2021 |
| per index | EU HICP, US CPI | past values revised (scaled so current is unchanged) | store vintages | Düring, 2021 |
| per benchmark | backfilled RFRs (for example SGD, THB) | history before the switch date is backfilled | mark the backfill boundary | Citi, 13 Aug 2026 |

## 5. Calendar effects that look like data errors (label, do not clean)

| Effect | Size / rule | Source |
|---|---|---|
| EUR overnight month-end jump | at least every month end; largest at turn of year; longer tenors show smaller jumps | Ametrano, Bertocchi & Mazzocchi, Advanced Eonia Curve Calibration, Dec 2016 |
| USD fed funds month-end | fixings jump negative at every month end (excess liquidity sold), no exceptions over the prior two years | same |
| SOFR month-end | no systematic turn-of-month pattern (most month-ends +1-2bp, not all) | Deriscope blog, 18 Feb 2024 |
| Euribor 1M turn of year | 2007 +64bp (29 Nov 2007), 2008 +22bp (27 Nov 2008), end-semester +9bp (29 May 2008) | Ametrano & Bianchetti, SSRN 2219548, 2013 |
| Pre-facility quarter-end SOFR | sometimes more than 20bp above fed funds | Huggins & Schaller, 2024 |
| Quarter-end 2024 | SOFR about 5.05 on 1 Oct 2024, above IORB 4.90 and the range top 5.00, then 4.85 by 3 Oct; EFFR flat at 4.83; facility use about 2-3bn | Conks, Money Market Update, 10 Oct 2024 |
| Euro overnight below deposit rate | EUR overnight rate has sat below the ECB deposit rate under excess liquidity because of non-bank transactions | Düring, 2021, p.66 |
| Month-end sampling | mid-month samples avoid pre-facility quarter-end SOFR spikes | Huggins & Schaller, 2024 |
