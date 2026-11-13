# Calendar catalogue: what repeats, when, and the mechanism

Use this to pick candidate windows and to attach a mechanism to a screen hit. Every entry is a hypothesis to test with
`scripts/seasonality.py` (see [SKILL.md](../SKILL.md)), not a trade. Dates are the published or typical schedule at the
time of the source: confirm against the `auctions`, `calendars` and `cb_meetings` tables before use.

## 1. Month-end, quarter-end, year-end (funding and index)

| Item | Pattern | Source |
|---|---|---|
| Month-end index extension | Duration demand from index trackers on the last trading day vs the 5y median. Euro government index projected +0.05y (equal to the 5y median); sterling gilt index -0.02y vs a +0.03y median. Indices are not free-float adjusted, so trackers buy market weight regardless of scarcity; month-end rebalancing is predictable "and therefore arbitraged across time" | (Citi Research, European Rates Morning Call, 19 Aug 2026); (Düring, Fixed Income Trading and Risk Management, 2021) |
| Index mechanics | Constituent and amount changes concentrate on the last trading day of the month; less liquid markets rebalance quarterly. Global index returns assume common T+0 settlement (even where JGBs settle T+2), bonds are valued at bid with new entrants at ask, and coupons accrue in a virtual cash account reinvested at the next rebalancing, so cash drag and rebalancing dates are the calendar levers (5% cash at a -44.3 bp carry gap, 10 Jun 2020: just over 2 bp underperformance) | (Düring, 2021) |
| Quarter-end funding | Severity year-end > quarter-end > month-end. German one-day GC richens into every quarter-end and reverses next month; December GC volume falls most | (BofA Securities, Bond market seasonality explained, 6 Jun 2022); (Conks, The Great Flattening, 4 Aug 2024) |
| Month-end funding (foreign banks) | Foreign banks de-lever at month-ends; cash borrowers pay up in the cleared bilateral market | (BofA Global Research, US repo sensitivity: higher than expected, 8 May 2025) |
| Settlement days | Repo rates rise on bill/coupon settlement days, more as reserves tighten, most when the day is a quarter-end. Mid-month corporate-tax date plus large coupon settlement produced a squeeze in Sep 2025 | (Federal Reserve Board, What Happens on Quarter-Ends in the Repo Market, 6 Jun 2025); (Conks, Plumbing Notes, 15 Sep 2025) |
| Fiscal year-end Japan | Banks shrink balance sheets for the 1 April reporting date, so turns also occur at the Japanese fiscal year-end; Japanese banks avoid borrowing at quarter-end and funding moves to FX forwards and basis swaps | (Düring, 2021); (J.P. Morgan, Drivers of cross currency basis, 11 Mar 2015) |
| Canada | Canadian banks cut repo at quarter-ends (their Q2 ends in April) | (BofA US repo sensitivity, 8 May 2025) |

Detail on size, measurement and curve treatment: [period_end_turns.md](period_end_turns.md).

## 2. Auction, issuance and cash-flow cycles

**US Treasury** (BofA Global Research, US Treasury auction primer, 8 Mar 2024)
- Quarterly refunding: first week of Feb, May, Aug, Nov. Financing estimates Monday 3pm ET, statement Wednesday 8:30am ET.
- 2y, 5y, 7y issue on the last business day; 3y on the 15th; 10y and 30y auction in week two and issue on the 15th; 20y auctions the next-to-last Wednesday and issues at month-end; TIPS auction the next-to-last Thursday, issue on the last business day and mature mid-month.
- Mid-month 15th: coupon and refunding settlement (15 Feb, May, Aug, Nov showed fed funds above target in a 2010 comparison; Credit Suisse, Basis Points, 18 Feb 2010).
- Cash-management bills mature on the 15th and are reissued the next day to hit a closing-balance target (Citi Research, US Rates Weekly: Going nuclear, 3 Feb 2017).

**Auction-week drift in the 10y** (Citi Research, US Rates Weekly: What to expect when you're expecting a turn, 20 Apr 2018; sample since 2014; median / average change in bp, share of weeks that rallied):

| Week type | Median | Average | Rally share |
|---|---|---|---|
| First week (no auction) | +2.7 | | 46% |
| 3s10s30s auction week | -1.9 | -1.1 | 56% |
| TIPS week | -0.1 | +0.4 | 50% |
| Empty week between auctions | -3.9 | -3.4 | 69% |
| 2s5s7s week | -0.9 | -1.0 | 53% |
| Final week (no auction) | -7.4 | -6.0 | 86% |

Read: the yield drifts lower in the weeks without supply and higher into the first week. The final-week number is
the single largest effect and is a candidate for a screen on your own data (it should survive a placebo that shifts
week boundaries by one week).

**Bills and tax calendar** (Citi Research, Going nuclear, 3 Feb 2017; Citi, Swearing in huge expectations, 13 Jan 2017;
J.P. Morgan, Markets struggle to feed the convexity beast, 28 Feb 2020)
- January tax receipts drive bill paydowns; February to mid-April refunds normally lead to issuance. Q2 paydowns reflect prior-year tax liabilities.
- 12m bill-OIS richened in April and May on tax paydowns, about 7 bp cumulative over five years; Q2 paydown expected -$74bn.
- Debt-ceiling precedent: market concern surfaced about 2 weeks before the X-date in 2011, 2013 and 2015.

**Germany and Italy** (Düring, 2021)
- German auctions on Wednesdays, Bubills Mondays, linkers Tuesdays; BKO (2y, four issues a year, maturities Mar/Jun/Sep/Dec, about 12bn) moved to Tuesdays in 2017. Mid-month BKO maturities let BKO swap spreads be traded with Euribor contracts at low basis risk.
- Italy: BTP auctions twice a month (mid-month 5/15/30y, month-end 3/10y, 10-30bn each); CCT 7y floater monthly at month-end.

**Japan** (BofA Global Research, Japan Rates Basics, 24 Apr 2023): central-bank purchase quarterly amounts are announced at quarter-end and the monthly schedule at month-end. 2Q2023 operations, per operation in JPY bn (operations per month): up to 1y 150 (1); 1-3y 350-650 (4); 3-5y 425-725 (4); 5-10y 475-875 (4); 10-25y 100-500 (4); over 25y 50-350 (3). Total JPY 5.7-12.2tn per month vs 7.25-10.65tn in 1Q2023.

**Supply seasonality**
- Financial issuance is 13% of annual supply in January (median 2012-16); redemptions about $36bn in January vs $11bn in December; December 2016 financial supply $24bn vs a $42bn monthly average. Year-end spread event study (10y spread change, 5y median, bp): -0.6 (10 days before), -0.4 (5 before), -3.0 (5 after), -2.0 (10 after), -0.2 (20 after) (Citi Research, Corporate supply to bring spreads tighter, 3 Jan 2017).
- Callable-note supply picks up in January; dealers receiving 30y to hedge long-dated callables push 30y spreads tighter (Citi, Corporate supply, 3 Jan 2017). 30y swap spreads tighten around year-end and widen modestly into February (Citi, US Rates Weekly: The rocky road to a steeper curve, 18 Jan 2019).
- After Labor Day 2018, more than $85bn of high-grade supply in eight trading days; non-financials 71% of gross notional, under 8% swapped (J.P. Morgan, Issuance, pensions, and long-end spreads, 14 Sep 2018). Gross issuance is not swapping: check the swapped share.
- Financial issuance falls steeply in the roughly four-week earnings blackout (J.P. Morgan, Dynamic hedgers are long, banks are short, 13 Sep 2019).
- Samurai issuance is higher May-July and non-yen issuance abroad peaks in July (both widen the intermediate USD/JPY basis); Q1 SSA issuance is seasonally strong in AUD, narrowing the 5y basis early in the year (J.P. Morgan, Cross currency basis 2H25 Outlook, 5 Jun 2025; Drivers of cross currency basis, 11 Mar 2015).

**Known-demand windows used as uncited screening defaults** (start here, then test and replace by your own estimate):
month-end duration extension: enter 3 business days before month-end, exit 1 after (long duration); quarter-end
extension: same window on the 10y receive; pre-auction concession: T-2 to T+1; post-auction squeeze: T to T+1;
coupon reinvestment (5y): T-1 to T+1; quarter-end balance-sheet window (2y): T-2 to T; corporate rate-lock:
settlement-1 to settlement on the tenor matching the bond maturity. These are entry-to-exit day offsets: entry at the close of the first day, exit at the close of the last, so month-end extension (enter T-3, exit T+1) is `--lo -2 --hi 1` in `window_study`, and the expected sign of the yield change is negative for the long-duration legs.

## 3. Futures and delivery calendar (Treasury bond contract)

(Burghardt, Belton, Lane, Papa, The Treasury Bond Basis, 3rd ed., 2005; Salomon Brothers, Understanding Treasury Bond Futures, Oct 1990)
- Timeline, March 2004 example: first tender Thu 26 Feb, first notice Fri 27 Feb, first delivery Mon 1 Mar, last trading day Mon 22 Mar (8th business day before month-end), last tender Mon 29 Mar, last notice Tue 30 Mar, last delivery Wed 31 Mar. The first two tender days fall in the prior month, under daily price limits.
- Upward-sloping curve: shorts prefer month-end delivery (IRR to month-end is a lower bound); inverted curve: early delivery. Invoice price is dirty, so accrued grows with later delivery and implied repo is typically higher to the last date (Quantitative Finance Stack Exchange, implied repo and the last delivery date, 7 Jul 2018).
- Calendar spread drifts from about 10/32 fifteen business days before first notice to about 8.5/32 around it (June 1997-March 2001, read from a chart). Shorts needing to roll buy the spread just before first notice; longs roll early.
- Deferred-month net basis was mostly within +/-5 ticks (1989-92) but fell below -10 ticks before year-end 1990 and 1991 (cash cheap vs futures).
- Invoice spreads: 2y and 5y deliver early in the month (3rd and 6th), 10y, bond and ultra at month-end (30th, 31st). Match delivery and CTD maturity dates exactly (Clarus Financial Technology, What's the Deal with Invoice Spreads, 17 Sep 2014).
- 1-month averaging contracts: hedge ratio N = notional x days in month / ($5mm x 30); full February: 50mm x 28/(5mm x 30) = 9.33; mid-January start with 18 days left: 10 x 31/30 = 10.33 (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022).

## 4. Day-of-week, holiday and event-day effects (thin evidence: test before use)

The reference library has only qualitative statements here. Treat each as a hypothesis for `window_study` with
events built from the `calendars` table (pre-holiday, post-holiday, Fridays) and a placebo.
- Funding drivers: corporate tax days, financial year-end and month-end push overnight rates up (larger at quarter-end); weekends and Fridays up (three-day roll); Mondays down (cash returns); central-bank repo maturities, e.g. the ECB main refinancing operation maturing on Tuesdays after the Governing Council, averaged about 30 bp below the refinancing rate; the year-turn premium is customarily priced but "rarely realised" and the overnight rate often collapses on the day (Lehman Brothers, The Short-End of the Curve, 10 Jul 2007).
- Fed funds in a 2010 comparison: below target on weekends and at year-end; above on Thursdays, month-ends, quarter-ends, tax days, refunding settlement and the 25th (Credit Suisse, Basis Points, 18 Feb 2010).
- STIR futures traders square positions on Friday afternoons and before holidays (Aikin, STIR Futures, 2nd ed., 2012).
- Event-day weighting for vol: count event days, not calendar days (weekdays 1, weekends about 0, Fridays slightly more, big releases more). Per-event-day vol = sigma_1w / sqrt(n_1w); a longer option spanning a release solves sigma_2w = per-day vol x sqrt(n_normal + X) for the release-day weight X. Illustration with round numbers (not the source's): 1w at 10 bp over 5 event days gives 4.47 bp per day; a 2w at 20 bp over 9 normal days plus the release gives X = (20/4.47)^2 - 9 = 11, so the release carries about 11 normal days of variance. (BofA Global Research, US Vol Primer, 11 Mar 2024, gives the method; its printed arithmetic does not reconcile with 10/sqrt(5), so recompute.)
- Intraday seasonality (open and close) breaks covariance stationarity unless modelled (Hasbrouck, Empirical Market Microstructure, 2004).

## 5. Seasonal flow timing

- Dutch pensions have received into year-end to keep coverage ratios high; year-end receiving can hit steepeners (Nordea Markets, EUR rates: How about that outright receiving, 26 Sep 2025).
- Lifers buy super-longs in January to March (ALM gap, spending before fiscal year-end) while banks sell; use supply seasonality mainly for curves and spreads (BofA, Bond market seasonality explained, 6 Jun 2022).
- Funding easing past year-end can mask convexity hedging flows (J.P. Morgan, The return of convexity hedging, 31 Jan 2020).
- Vol seasonality: median month-on-month change in 3m10y vol by calendar month over 5, 10 and 20 year samples; gamma outperformed in 4 of the last 5 Mays and 7 of the last 10 (Citi Research, US Rates Vol Lab: Fair value vs seasonality, 1 May 2017). Callable supply also picks up seasonally.
- Summer and September: the average and median 10y move from 20 July to 20 August over 20 years was about 27 bp (read as absolute, since the source compares it with a straddle breakeven) vs an unhedged 1m10y straddle breakeven of about 20.4 bp (Citi, US Rates Weekly: Summer lull, 17 Jul 2015); depth rises and 3m10y implied vol falls into September, about 5 bp on average post-crisis, in 7 of 9 years 2008-18 (J.P. Morgan, For cheap gamma, look to the long end, 23 Aug 2019). SPX realised vol typically rises in September and peaks in October; DXY up in about two-thirds of Septembers (Citi, Mid-week musings, 19 Aug 2026; J.P. Morgan, Currencies amid long-end UST shenanigans, 21 Aug 2026).

## 6. Election and policy-event templates

- Cumulative change in 2y, 10y, 30y, 2s10s, 5s30s over about +/-125 business days around US midterm Election Day, from 1960, split by All Midterms, Trifecta Lost (5 cases), Trifecta Held (3 cases). The path is a prior to update (Citi Research, How to trade US midterm elections, 14 Aug 2026). The uncertainty premium starts about 50 business days before and peaks weeks before; divided government tends to be bond-positive afterwards (Citi Research, US midterms on the mind, 2 Oct 2026). With 3 to 5 cases per bucket this is context, not a signal.
- FOMC template: normalise each series on the event day, compare the average of past cycles with the latest (5 days before to 10 days after) (RiskVal, RiskVal Overview 201: Cash and Futures, 12 Nov 2021).
