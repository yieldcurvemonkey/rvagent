# Schedules, business-day rules and holiday calendars

Detail behind `SKILL.md`. "Date arithmetic is deceptively simple but the source of many (all?) errors in vanilla swap valuation"
(Gunstensen, MIT 18.642 Lecture 7, 2024). No schedule generator is bundled: use the rules and the cited test cases below to check
whichever generator the environment provides.

## 1. Swap schedule roll-out (backward from maturity)
1. Trade date + spot lag (see `market_matrix.md`) on the joint calendar = **effective date**.
2. Effective date + tenor = **unadjusted maturity**. Book the maturity unadjusted.
3. Unadjusted maturity minus n x frequency = **unadjusted roll dates** (backward roll improves fungibility; this is the market default,
   and for instruments longer than 1y that straddle a leap year it also fixes the stub at the front).
4. Roll dates + the business-day rule = **accrual dates**. Accrual includes the start date and excludes the end date.
5. Accrual start + reset rule = **rate quote (fixing) date**; accrual end + payment rule = **payment date**.
Schedules therefore yield three date sets: fixing dates (forwards), accrual dates (tau) and payment dates (discount factors).

## 2. Business-day rules and defaults
- Rules: FOLLOWING (F); MODIFIED FOLLOWING (MF: roll back if rolling forward changes the month); PRECEDING (P); MODIFIED PRECEDING (MP); UNADJUSTED.
  Example: 2M from Tuesday 30-Sep-2014 is Sunday 30-Nov: F gives Monday 1-Dec, MF gives Friday 28-Nov.
- Roll day: 1-31, IMM, EOM, START or END. Month-end rule: 6M from 28-Feb (non-leap) ends 31-Aug under EOM; under MF alone 28-Aug would be valid.
- Combined calendar: a day is a holiday if it is a holiday in either centre. GBP payments need a London business day; EUR IRS fixings follow at least TARGET.
- Defaults (Tradeweb/tpSEF, ISDA): effective and termination dates unadjusted; period-end dates = payment dates; payment BDC MF; XCS initial exchange
  following, interim MF, final MF. Linear interpolation of the index only for long or short stubs, between the next-shorter and next-longer tenors.
- Keep adjusted and unadjusted dates apart: errors arise when the adjusted date is used as the roll anchor.
- Spot start for standard swaps: whole-year tenors 1y-30y, no spread on the floating leg, par rate quoted to 0.001 (percentage points), bid-offer typically a tenth of a bp.
  IMM swaps start on the third Wednesday of Mar/Jun/Sep/Dec and are quoted as cash NPV; MAC swaps standardise the coupon (par rate rounded to the nearest
  25bp), enabling compression at a CCP.

## 3. Frequency codes, regularity and stubs
Frequencies: A annual, S semi, Q quarterly, M monthly, B bi-monthly, T every 4 months.

A regular unadjusted schedule satisfies four axioms: the effective date is on the roll day; the termination date is on the roll day; the months between are
exactly divisible by the frequency; interim dates fall on the roll day at regular intervals. Regular examples: 1-Jan-22 to 1-Jan-23 roll 1 (A/S/Q/M/B/T);
28-Feb-22 to 31-Aug-28 roll 31 (S/Q/M/B); 15-Mar-23 to 20-Sep-23 IMM (S/Q/M/B); monthly IMM from 15-Mar-23 gives 15-Mar, 19-Apr, 17-May, 21-Jun,
19-Jul, 16-Aug, 20-Sep (third Wednesdays).

- **Roll ambiguity.** 28/29-Feb aligns with rolls 28-31; the 30th of 30-day months with 30 or 31; IMM is tested separately.
  Inference cases: 15-Mar-22 to 15-Mar-23 is roll 15 or IMM; 16-Mar-22 to 21-Sep-22 is IMM only; 30-Jun-22 to 30-Sep-23 is 30 or 31;
  28-Feb-22 to 28-Feb-23 is 28-31. Rules: never infer IMM (the user must supply it); control ambiguous end-of-month with an explicit `eom` flag; prefer the
  inferred roll that deviates least from the given effective date.
- **Adjusted-date inference.** Mon 6-Jun-22 to Mon 5-Dec-22 quarterly following: roll is 5 or 4, not 6 (choose 5). Fri 7-Jan-22 to Fri 7-Oct-22 Q preceding:
  7, 8 or 9 (choose 7). Fri 29-Dec-23 to Mon 30-Sep-24 Q MF: 29, 30 or 31 (29, or 31 if eom).
- **Date arithmetic is not invertible without the roll.** 28, 29 and 30-Mar-2001 + 6M (MF) all give Fri 28-Sep-2001; 28-Sep-2001 - 6M gives 28-Mar (default),
  30-Mar (roll 31) or 29-Mar (roll 29).
- **Stubs**: short-front, long-front, short-back, long-back (combinable; default SHORTFRONT; standard swaps have none). A short stub has fewer days than a regular
  period. Front stub: roll inferred from the termination date; back stub: from the effective date. Example short front: 15-Jun-2022 to 28-Feb-2023 monthly gives
  stub date 28-Jun-2022 (eom false), 30-Jun (eom true) or 29-Jun (roll 29). A long stub = find the short stub, step one day, find the short stub again. Two
  stub dates cannot both be inferred.
- **Null stubs.** An inferred stub with at most one valid business day collapses after adjustment and must be removed. Example: effective Sun 2-May-27, termination
  Wed 3-May-47: the inferred front stub Mon 3-May-27 is null, so the effective date becomes Mon 3-May-27.
- **Stub rates.** IBOR stubs: linear interpolation between neighbouring tenors by value end date (for example about 5M between the 3M and 6M fixings, 2M = linear
  between 1M and 3M). RFR stubs simply compound fewer or more daily fixings. A one-off first coupon (German long first coupons over 1y) needs the ACT/ACT fictitious-period split.
- **Forward-start ambiguity (1Y1Y).** Over 2024, three methods agreed on only 73.2% of days; swaps-aligned (2Y = 1Y + 1Y1Y) and swaption-expiry methods differ on
  about 27%. Wed 17-Jan-24 gives rolls 19, 21 or 20 depending on the method. Swaps-aligned is the dealer-swap convention; the swaption-expiry method is "never seen"
  in the interdealer swap market. Pin the evaluation date, evaluation mode, calendar and modifier.
- **Forward notation.** `5Yx10Y` = starts in 5y and runs 10y (first fixed flow at 6y on an annual fixed leg such as EUR or SOFR/SONIA/TONA OIS, 5.5y on a semi-annual one such as legacy USD/GBP/JPY LIBOR swaps). FRA notation `6M9M` = start x end.
  Naming: `1Y5Y` forward (or a 1y-expiry swaption on a 5y swap); `1Y2Y5Y` = swaption on a 2Y5Y with 1y expiry; `2s5s` spread; `2s5s10s` butterfly;
  `2s3s4s5s` "pascal"; `2s3s/4s5s` "condor".

## 4. Holiday calendars
- **Business-centre codes (FpML)**: USD USNY (swaps may also need USGS, the US Government Securities calendar); EUR EUTA (TARGET); GBP GBLO; JPY JPTO; CHF CHZU;
  CAD CATO; AUD AUSY; NZD NZAU and NZWE (both); SEK SEST; NOK NOOS; DKK DKCO. Legacy LIBOR floating-rate options for USD, JPY and CAD added GBLO "applies to both legs".
- **CME interest-rate calendar is not the US federal calendar.** Closed Good Friday, open on Columbus and Veterans Day, New Year observed Monday when it falls on Sunday.
  A federal calendar fails to reproduce actual contract last-trade days, the CME calendar does; CME has opened on Good Friday when it collided with payrolls. Test any calendar against historical last-trade dates. Swaps and bonds use
  the US Government Securities (SIFMA-style) calendar. Keep exchange calendars separate from cash-market calendars (`calendars.calendar_id`: CME_IR, EUREX, ICE_EU, JPX, MX, ASX, NASDAQ_STO).
- **Observance differs by jurisdiction.** UK moves a weekend holiday to the following Monday (or Tuesday). Continental Europe simply loses it. The US observes Saturday holidays on
  Friday and Sunday holidays on Monday. London 2023: 2-Jan, 7-Apr, 10-Apr, 1-May, 8-May (coronation, one-off), 29-May, 28-Aug, 25-Dec, 26-Dec. London 2021: Mon 27 and Tue 28 Dec were
  substitute days, so 25-Dec-2021 + 1d (F, London) = 29-Dec-2021.
- **Sources**: exchanges listing futures and options (they follow public holidays), ISDA, ICMA, SIFMA; the BoE publishes SONIA on London business days; the ICE calendar covers SONIA and gilt futures.
- **Validate a calendar with fixings.** A fixings series indexed by date must contain exactly the fixing days under the curve's holiday calendar. Some vendor USD OIS histories publish prints on
  holidays: filter with an explicit ignore-date list. A fixing series with gaps over 5 calendar days is almost certainly a missing-data problem, not a calendar one.
- **Spot lags** (ISDA/tpSEF defaults): basis swaps T+2 except CAD and GBP T+0 (MXN and ZAR differ); fixed/float IRS and inflation swaps T+2 except CAD and GBP T+0; swaptions and caps/floors the same;
  cash-settled swaptions and early terminations value 2 BD before exercise, except GBP and CAD same day. FX spot T+2 (USDCAD T+1). Most bond markets settle T+2 historically; US and UK
  government securities T+1 (see `market_matrix.md` for current values). "For value of ..." means the settlement date, not the trade date.
- **Weekend and holiday weights.** In compounded RFR periods a Friday fixing carries 3 days and a pre-holiday fixing more; Easter and Christmas weeks can dominate short OIS periods.
- **Turn dates.** Year-end, quarter-end and month-end spikes in repo and RFR fixings are calendar effects; flag them with the calendar, not by outlier removal. See
  [quant-seasonality-and-calendar-effects](../../quant-seasonality-and-calendar-effects/SKILL.md).
- **Meeting and effective dates.** Central-bank step curves belong on effective dates (ECB Wednesday after, BoE publication date, BoJ reserve-period start), not meeting dates (see
  `market_matrix.md` section 4). FOMC dates are known about six months ahead, so a step model allows no jumps beyond that.
- **Index-change dates.** Track definition and removal dates of indices (for example Euroyen TIBOR 30-Dec-2024, CDOR 28-Jun-2024) so a history can be stitched or truncated.
- **Benchmark switches** (for example one Bobl series replaced by the next on 25-Jul-2018) create fake 2s5s steepening and 5s10s flattening in benchmark series. Use fitted or
  constant-maturity yields for histories.

## 5. Test cases a schedule or calendar tool must pass
1. 30-Sep-2014 + 2M with F gives 1-Dec-2014; with MF gives 28-Nov-2014.
2. 25-Dec-2021 + 1d, F, London, with 27/28-Dec substitute holidays gives 29-Dec-2021.
3. 6M from 28-Feb-2023 with EOM roll gives 31-Aug-2023.
4. 28/29/30-Mar-2001 + 6M MF all give 28-Sep-2001.
5. Monthly IMM from 15-Mar-2023 gives 19-Apr, 17-May, 21-Jun, 19-Jul, 16-Aug, 20-Sep (third Wednesdays).
6. A 1-day stub that collapses after adjustment is removed, not paid.
Cases 1 and 2 are verified in `scripts/conventions.py --selftest`.
