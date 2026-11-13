# Dates, schedules, day counts and swap-pricing code

Market conventions per currency live in [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md); fixings and
compounding in [stir-rfr-compounding-and-fixing-risk](../../stir-rfr-compounding-and-fixing-risk/SKILL.md). This file is how to
code them without silent date bugs. Table names are in `data-contract-and-adapters/references/schemas.md` (`calendars`, `swap_conventions`, `rate_fixings`).

## Schedule generation
- Frequency codes (unadjusted): A, S, Q, M, B (every 2 months), T (every 4 months). Unadjusted schedules ignore holidays; adjust afterwards with calendar + modifier (Darbyshire, Coding Interest Rates, c.2024, ch.5).
- Pipeline: infer and validate unadjusted arguments -> generate regular or irregular unadjusted schedule -> adjust. Inference is where bugs live; validate once at the public API and let helpers assume valid input.
- A regular schedule obeys four axioms: effective date on the roll day; termination on the roll day; months between divisible by the frequency; interim dates on the roll day at regular intervals.
- Roll inference: numeric rolls only. IMM and named days are never inferred (pass them). Ambiguous month-ends need an explicit `eom` flag. 15 Mar 22 -> 15 Mar 23 allows 15 or IMM; 16 Mar 22 -> 21 Sep 22 allows IMM only; 28 Feb 22 -> 28 Feb 23 allows 28, 29, 30 or 31.
- Stubs: front stub takes its roll from the termination date, back stub from the effective date. Two stub dates cannot both be inferred. A stub with <= 1 valid business day after adjustment collapses to zero width and must be dropped (found by generating 10,000 random schedules and tracing pricing errors). Example: effective Sun 2 May 2027, termination Wed 3 May 2047, short front stub: inferred stub date Mon 3 May 2027, null period removed.
- Date arithmetic is not invertible without the roll day (modified-following maps several starts to one end). Monthly IMM from 15 Mar 2023: 15 Mar, 19 Apr, 17 May, 21 Jun, 19 Jul, 16 Aug, 20 Sep (third Wednesdays) - a good unit test.
- Pin evaluation date, evaluation mode, calendar and modifier whenever comparing tenor-specified forwards (1Y1Y) or pairing swaps with swaptions. Over 2024 three 1Y1Y date methods agreed on only 73.2% of days (Wed 17 Jan 2024: rolls of 19, 21 or 20 depending on method). Swap spot lag: T+0 GBP, T+1 AUD, T+2 most others, CAD sources conflict (read `swap_conventions` per curve, see fi-g10-market-conventions); FX spot USDCAD is T+1.
- A fixings series must match the curve's holiday calendar exactly; use the mismatch as a validator. Instruments, curves and fixings must share the same index lag (monthly index values are dated the 1st, published mid-following-month).
- Holiday sources: the index publisher, the exchange and industry bodies, not a generic library; watch one-offs (2023 coronation). An expiry rule that returned Christmas Day for a December future was caught only by comparing every generated expiry to the exchange's published list: always test rules against one.

## Day counts and compounding
- Compounded RFR over a period: `[prod(1 + r_i n_i/N) - 1] N/d_c`, N = 360 (USD, EUR), 365 (GBP); simple average is `sum(r_i n_i/N) N/d_c`. 1% then 2% overnight, ACT/365F, two days = 1.5000274%. Daily fixings 12, 13, 14% over 3 days = 13.0046% (ACT/365F; checked).
- `(1 + r sum d_i) = prod(1 + d_i r_i) = v_0/v_n` only for actual-day counts with a fixed denominator (ACT/360, ACT/365F), not for 30E/360. Term (IBOR-style) rates are not overnight rates: never compound consecutive term-curve values.
- EUR ESTR is ACT/360, GBP SONIA ACT/365F: carry day-count metadata with the data. Accrual conventions are issuer-specific (same coupon and dates: gilt 1.43646409 vs a Canadian ACT/365F bond 1.42465753; Canadian bond accrual switches at one year) (Darbyshire, Coding Interest Rates, ch.9-10).

## Swap pricing plumbing
- Single curve: `R = (v_0 - v_n)/A`, `A = sum d_j v_j`. `analytic_delta = sum DF x DCF x notional/10000` (currency per bp); `NPV = (rate - fixed) x analytic_delta x 100` (payer positive; rate and fixed in percent, `analytic_delta` already carries notional/10000; check: (1.13627 - 1.15) x 32,714.29 x 100 = -44.9k) (Darbyshire, PT3e, s.11.1). Burgess identities (receive-fixed positive, r = fixed rate, p = par; the book above is payer-positive, so the signs are opposite): `PV = (r - p) A`, `PV01 = A x 0.01%`, `DV01 = PV01 + DF01` (DF01 = 0 for a par swap).
- Forecast vs discount curves: `R = sum r_j d_j v_j / sum d_i v_i`; floating PV `= sum (curve[p0]/curve[p1] - 1) x disc[p1]`.
- Fixtures: schedule from 1 Jan 22, 11M, 3M periods: DCFs 0.246575, 0.249315, 0.252055, back stub 0.167123. Swap from 14 Feb 22, 4M, annual fixed (0.328767) vs monthly float: mid 1.13627%, analytic delta on 1bn = 32,714.29, NPV at 1.15% on 1bn = -44,901.21 (sign: the book's pay-fixed-positive convention).
- 5Y swap, fixed 5%, N = 1mm: annuity 4,863,971.74, par 1.5482% (the slide's PV line prints 1.59%; only 1.5482% gives 167,892), PV01 486.40 (check `A x 1e-4`), PV 167.9k (Burgess, Low Latency Interest Rate Markets, undated deck). The annuity approximation with DF = 1 (PV about 175k) is for sanity checks, never pricing.
- Consolidated schedule: build one 30Y schedule per float index with cumulative fixed annuity and float PV at whole years; every whole-year swap is then a vector product. Valid only for regular, stub-free schedules; book real unadjusted maturities (Burgess, I Feel the Need, the Need for Speed, SSRN, May 2022).
- Discount-delta sanity: IRS/annuity `dP/ds ~ -P x tenor/(2 x 10000)`; ZCS `-P x tenor/10000`. A 30Y CSA mismatch with $1mm pv01 gives $1,500 pv01 (Darbyshire, PT3e, Ex 21.4).
- DF recursions: `v_i = v_{i-1}/(1 + d_i(r_i + s_i))`; a DF is never affected by rates after its own date. Par from DFs: `r_i = (w_{i-1}/w_i - 1)/d_i`.
- Roll-down for a static curve = rate on the rolled curve minus rate today; implement as "curve with its pillars date-shifted", not as an extra solve (Quant Finance Stack Exchange, "Calculating swap rolldown using the RatesLib Python Library", Jun 2024). Check carry numbers by repricing the aged trade; a running carry field and a translated curve gave wrong sign or rank in one audit.

## Library design conventions worth copying
- Validate in the public API; private helpers `_is_x -> bool`, `_get_x -> value`, `_check_x -> (ok, value_or_message)`, `_generate_x -> iterator`.
- Typed "no input" sentinel instead of `None`; accept strings (`"usd"`, `"mf"`, `"act365f"`) rather than enums; one instrument may carry 50+ arguments, so plan defaults early.
- Link instruments to curves indirectly through a solver-owned mapping (the author's recommended option) so a curve can be swapped without rebuilding trades.
- Prefer explicit if/else blocks to ternaries so the coverage tool flags an untested branch; target 100% coverage on date and convention code.
