---
name: fut-calendar-roll
description: 'Fair value and dynamics of the bond-futures calendar roll (front minus back, e.g. Sep/Dec UST TU FV TY UXY US WN, Bund/Bobl/Schatz/Buxl, Long Gilt, JGB, CGB, plus SOFR SR3/SR1 and other STIR strips). Fair roll from forward CTD prices, carry, net basis and delivery options, calendar implied repo (IRP), BPV-neutral roll ratios, funding and CTD-slope sensitivity, positioning and roll-pace read (asset-manager longs, open interest), delivery timing, squeezes, and roll-adjusted generic and continuous series. Use when asked "is the roll rich or cheap", "calendar spread", "Sep/Dec roll", "roll in ticks", "buy or sell the roll", "calendar IRP", "roll hedge ratio", "roll season", "first notice day / first position day", "generic front-month series", "back-adjusted continuous futures", "roll cost", or when a futures series jumps at expiry. STIR strip calendar spreads and flies: stir-futures-rv.'
---

# Futures calendar roll

A bond-futures calendar spread is the price of moving a futures position from the front to the next contract. Its fair
value is the difference of the two contracts' fair prices: carry between the two delivery dates, plus the change in
delivery-option value, plus (if the CTDs differ) the curve slope between the two CTDs. Nothing forces the spread to
converge at expiry (unlike a basis), so the roll trades on fair value **and** on flows: asset managers must roll longs
before delivery and push the calendar around when they are concentrated. The skill values the roll, reads the
flow picture, sizes a BPV-neutral roll, and builds roll-adjusted series that never book the roll as a return.

## When to use
- "Is the Sep/Dec roll rich or cheap?" "What is fair for the TY/UXY/WN calendar?" "Calendar IRP vs forward repo?"
- Choosing how and when to roll a futures hedge or a basis position; buying or selling the calendar as a trade.
- Reading roll season: how much open interest has rolled, who is long, whether delivery timing favours early or late.
- Building generic / continuous futures series, roll-adjusted P&L, or a backtest that holds futures through expiries.
- SOFR/STIR strip rolls (which contract to roll into, roll cost) and the SR1-SR3 spread.
- Not for: valuing the delivery options themselves ([fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md)),
  cash-futures basis and IRR of one contract ([fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md)),
  futures-versus-swap spreads ([fut-invoice-spreads](../fut-invoice-spreads/SKILL.md)).

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Futures settles, volume, open interest (front and back) | `fut_quotes` | daily, same `snap` for both legs, >= 8 prior rolls for comparisons | price in points, decimal; OI/volume lag 1-2 days |
| Contract dates: first notice, first/last delivery, last trade | `fut_static` | per contract | verify against current exchange spec: conventions have changed |
| Basket, conversion factors, eligibility | `fut_basket` | per contract, point-in-time | back basket may contain when-issued bonds |
| CTD (and runner-up) clean prices, coupons, maturities | `bond_quotes`, `bond_static` | daily, same snap | accrued/dirty separate; ex-div for gilts |
| Term repo to each delivery date (GC and CTD-specific) | `repo_rates` | daily | forward repo d1 to d2 is the key driver; never assume GC if the CTD is special |
| Net positions by trader class, open interest | `positioning` | weekly, `pub_ts_utc` = knowledge time | US report is Tuesday data, released Friday: use the release before first notice |
| Generic-to-specific mapping | `roll_map` | daily | always store `roll_rule` |
| Model net basis (option value) per contract | from [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md) | per roll | if absent, use 0 and say the fair roll is carry-only |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values.

## Method

### 0. Conventions
- **Roll = front minus back** futures price, in points; quote in 32nds (x32) or ticks of the contract. Positive roll =
  front above back, which is what positive carry produces. "Buy the calendar" = buy front, sell back (Burghardt et al., The Treasury Bond Basis, 2005).
- **Rich calendar** = market roll above fair roll (sell front, buy back). Rich/cheap = `market roll - fair roll`, in ticks.
- Prices decimal (never 32nds text); repo and IRR in percent; days calendar; repo ACT/360 for USD/EUR/CHF/SEK/NOK, ACT/365 for GBP/JPY/CAD/AUD/NZD (confirm in [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md)).
- Basis: gross = CTD clean - CF x F; net = forward clean CTD - CF x F; carry = gross - net.
- Direction of conversion-factor scaling: contracts per face = par x CF / contract size (Burghardt prints 124 contracts for $10mm at CF 1.2390, i.e. par x CF / $100k).

### 1. Classify the roll
| Case | What drives the roll | Method |
|---|---|---|
| Same CTD in front and back (US, WN, often TY/UXY) | carry between d1 and d2 and the change in option value; curve is not a factor | step 2 |
| Different CTDs (TU, FV, TY, UXY, Schatz new issues) | adds CTD-slope: front CTD vs back CTD | steps 2 and 3 |
| Back CTD is a when-issued or unissued bond | roll depends on WI price and its repo | treat WI repo separately; flag the model as lower confidence |
| Cash-settled (AUD bond futures, price = 100 - yield) | no CTD, no delivery option; the two PVBPs are equal so the yield-per-cent conversion is undefined and the BPV ratio is 1:1 | fair roll = forward yield at d2 minus forward yield at d1 of the notional bond (derived from price = 100 - yield; quote in yield bp, not 32nds) |
| SOFR / STIR strip | not a bond roll: reference-period and curve slope | step 8 and [stir-futures-rv](../stir-futures-rv/SKILL.md) |

### 2. Fair roll from forward CTD prices
1. For each contract i (front f at delivery date d1, back b at d2) price the CTD forward by bond plus term repo:
   `Fwd_i = (clean + AI_0) x (1 + r_i x days_i/360) - sum_k coupon_k x (1 + r_i x n_k/360) - AI_{d_i}`
   (coupons reinvested at repo; `n_k` days from coupon to delivery). Use the bond's own term repo to d_i, else GC.
2. Fair futures price `FV_i = (Fwd_i - b_i) / CF_i`, with `b_i` = model net basis = delivery-option value (0 if ignored).
   At the CTD, futures underpriced = basis rich; the futures mispricing is about the option-adjusted basis with the opposite sign (Burghardt 2005).
   Equivalently futures price = forward CTD price / CF - total option value (BofA, 10 Jul 2025); the futures have no coupon, but drift deterministically as the forward converges to spot and roll down with the CTD, so a one-month futures roll is the one-month roll of the CTD.
3. **Fair roll** `= FV_f - FV_b`. Equivalent net-basis form: `roll = (Fwd_f - Fwd_b)/CF - (b_f - b_b)/CF` when CFs match.
4. Decompose into **carry part** `(Fwd_f/CF_f - Fwd_b/CF_b)` and **option part** `(b_b/CF_b - b_f/CF_f)`. Same CTD:
   carry part `~ (coupon accrual d1 to d2 - financing of the dirty price over d1 to d2) / CF`, positive when repo is below yield.
5. **Pricing date convention**: positive carry means the short delivers late, so price to the last delivery day; negative
   carry means early delivery, so price to the first (Burghardt 2005; JPM, Bond Futures Rollover Outlook, Aug 2026; BofA, 10 Jul 2025: FV then trades to the first delivery day, WN to the last). Delivery is a T+2 process (intent, notice, settle), so measure carry with a T+2 start. Use the same convention for both legs.
6. `rich/cheap = market roll - fair roll`. If the option part is not modelled, a positive net basis of the back above the front still widens the calendar: a widening back basis widens the calendar (JPM, Aug 2026).

The script ([`scripts/roll_fv.py`](scripts/roll_fv.py)) does steps 1-6 for a same-CTD or different-CTD pair.

### 3. Funding and CTD slope sensitivities
- **Funding.** A parallel move `dr` in repo over the d1 to d2 gap moves the roll by
  `d(roll) = - P_full x dr x (d2-d1)/360 / CF`. +25bp on a quarter gives about -0.0625 points = -2/32 (JPM, Aug 2026): higher funding lowers the calendar. The back contract has three more months of carry, so a rise in 4m repo with 1m unchanged cuts the roll.
- **Tail repo.** With the same CTD in both months the roll is the carry on the d1 to d2 tail (e.g. the Sep-Dec tail repo): if the forward (tail) repo falls, back-month carry rises, the back price falls and the calendar widens (BofA, US Treasury futures and basis primer, 10 Jul 2025). A longer back-month CTD adds a tail of curve carry to the roll. Before back-month liquidity builds, proxy the back contract by its anticipated CTD cash bond and its forward repo, so the roll can be valued from cash and repo alone.
- **GC term structure.** Steepening of the GC/OIS term structure is bearish for the roll; a 1w repo spike of about 10bp against 3m GC into month-end flattened the term structure and richened calendars (JPM, May 2019; Aug 2019).
- **CTD slope** (different CTDs): a steeper curve between the front CTD and back CTD richens the front CTD and widens the calendar (BofA, 10 Jul 2025). Translate a curve view into ticks by regressing the roll on the CTD slope or on a curve segment:
  TU CTD slope on 1s2s SOFR slope `y = 0.0449x + 0.5932`, R^2 0.16: 10bp of 1s2s steepening is about 0.4bp CTD steepening, about 0.3 tick of roll. UXY CTD slope follows 7s10s: 10bp of 7s10s steepening is about 4 ticks of roll; TY follows 5s7s (Citi, Treasury Futures Roll Sep26-Dec26, 18 Aug 2026).
  Flatter 5s30s cheapened the WN calendar when the CTD changed between months (Citi, US Rates Weekly, 10 May 2019). Same CTD in both months: the curve is not a factor (Citi, 18 Aug 2026).
- **CTD robustness.** Test the CTD in both months under parallel moves and a +/-1.5 sd steepener/flattener about the CTD: a CTD switch changes the roll, and a net long calendar carries switch risk. A bullish roll view partly reflects wanting the deferred delivery option (Citi, Treasury Futures Roll, 14 Aug 2026). Scenario convention: shocks beta-weighted off the on-the-run, twist = +/-1.5 sd about the CTD (J.P. Morgan, Basis Scenario Analysis, 28 Oct 2026).
  Direction of CTD migration: conversion factors price at a 6% yield, so with yields below 6% a parallel rally moves the CTD to shorter-duration bonds and a sell-off to longer ones; an upward-sloping basket favours the longest bond, an inverted one the shortest. Futures therefore shorten in rallies and lengthen in sell-offs, so each month's CTD (and the CTD slope between months) must be re-run under the shock, not held fixed (BofA, 10 Jul 2025). Scenario grid and long-bond example: [references/worked-examples.md](references/worked-examples.md).

### 4. Calendar implied repo (IRP) and the option-adjusted check
- **Calendar IRP** = breakeven funding for a long calendar (take delivery of the CTD on the front, deliver on the back):
  `IRP_cal = (Inv_b + sum coupons - Inv_f) / ((Inv_f x days - sum coupon_k x n_k)/360) x 100`, with `Inv_i = CF_i x F_i + AI_{d_i}`.
- Compare with the **forward** repo d1 to d2, not the spot-start term repo (flat 4% term repo gives about 3.98% forward over a quarter starting 51 days out: see script self-test).
  For contracts with negligible option value, calendar IRP **below** forward funding means the spread is **rich** (JPM, Aug 2026).
- IRP is wrong where delivery options matter because it ignores CTD switches. Use the option-adjusted net basis over carry (OABNOC) or risk-adjusted yield-spread measure (RAYS): front OABNOC/RAYS below back = calendar rich (JPM, Aug 2026).
- Validity: same CTD only. With different CTDs, use step 2.
- **Cash-ASW cross-check** (different CTDs): assume the ASW/OIS Z-spread level is smooth between d1 and d2; the theoretical roll is the one that equalises the two CTDs' Z-spreads at d2. R/C = (spread between the CTDs at spot) - (same at d2): R/C > 0 means the back CTD is cheap and the roll is rich (sell front, buy back); R/C < 0 the reverse (RiskVal, Overview 201, 2021; Highlights, Mar 2023).

### 5. BPV-neutral roll and sizing
- `N_back / N_front = PVBP_front / PVBP_back` (Duering, Fixed Income Trading and Risk Management, 2021, Eq. 28.21-28.22), usually below 1 as the back CTD is the same or a longer bond. Quote as back contracts per 1,000 front.
  Aug 2026 (JPM): WN 990, US 980, UXY 977, TY 960, FV 927, TU 872. Unchanged basket: ~1:1; when the shortest bond drops out of the basket the ratio is below 1 at low yields.
- Yield move worth one cent of roll: `dy = 0.01 / (PVBP_front - PVBP_back)` (Eq. 28.20). Undefined when PVBPs are equal (cash-settled).
- Use the optionality-adjusted BPV (OABPV), not the CTD's converted BPV, which jumps at CTD inflection points (Huggins & Schaller, Fixed Income RV Analysis, 2024).
- If the CTDs differ, the calendar is directional with yield: size BPV-weighted, not 1:1.
- A basket change can break the ratio: the 2015 long-bond CTD moved from 6.25% May-30 (DV01 $166) to 4.5% Feb-36 ($252), so an equal-DV01 roll needed 34.1% fewer June contracts (Citi, The long end basket case, 4 Feb 2015).

### 6. Roll dynamics: score four drivers, then net them
Score each contract bullish / bearish / neutral on (JPM, Aug 2026): (1) **basis convergence**, (2) **positioning**, (3) **CTD relative value**, (4) **forward financing**.
1. *Basis convergence.* Compare each contract's net basis (BNOC) with its modelled option value. Net basis below option value = basis underpriced, expected to widen; a widening back basis is bullish for the roll (calendar widens). Example: US back BNOC about 4+/32 vs option about 15/32 (JPM, Aug 2026). Scale: net basis is a measure of option value and was close to 0 in mid-2025, with the wild card worth 4-5 ticks on some contracts, against 10+ ticks when yields were near 6%; a negative net basis means futures rich to forwards with options worth about 0 (BofA, 10 Jul 2025).
2. *Positioning.* Asset managers (net long) must roll longs before delivery: sell front, buy back, cheapening the calendar early in the roll; the roll converges to fair in the last week once most longs have rolled. Levered funds (basis, net short futures) roll by buying the calendar (Burghardt 2005; Citi, Aug 2026; BofA, 10 Jul 2025: asset managers sell the roll, levered funds buy it, roll season being roughly the month before delivery). Asset managers are in effect short the basis (long futures instead of cash, a leverage substitute favoured when the curve is inverted) and hedge funds long it, in similar size; asset managers carry that basis risk for the whole holding period even though they roll before delivery (BofA, 10 Jul 2025).
   - Per contract compute current, 3y mean, sd, percentile and **z** of net AM longs (JPM Aug 2026: TY (2595-1782)/412 = 1.97, WN 1.58, UXY 1.49, US 0.9, FV 0.2, TU -0.5). Mapping used: z about 2 bearish (TY 1.97), z 1.5-2 mildly bearish (WN, UXY), |z| < 1 no call.
   - Regression of end-of-roll richness (ticks) on normalised AM share of OI, using the report published before first notice (Citi, May 2019): FV `y = -17.517x + 2.5885`, R^2 0.64; WN `y = -14.666x + 3.039`, R^2 0.825, last ten cycles excluding Nov-2016. Re-estimate; `fit_line` in the script does it. Residual = rich/cheap vs positioning-implied.
   - Risk-weight open interest to compare contracts (UXY equivalents: TU 0.5, FV 0.5, TY 0.75, UXY 1, US 1.5, WN 2.5); record-high risk-weighted OI amplifies imbalances (JPM, Aug 2026).
   - Asset managers avoid delivery as a policy, so heavy longs roll early: early-roll pace is a symptom of large net long positioning (Citi, May 2019).
3. *CTD RV.* Front CTD cheap/rich versus the fitted curve and the CTD slope; a large roll can distort the CTD's own RV (see [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md)).
4. *Financing.* Forward repo, GC term structure, month-end/quarter-end turns, bill supply and TGA/reserve moves (see [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md)).

**Roll progress and pace.** `roll progress = back OI / (front OI + back OI)` (Duering 2021). Compare it with the same day count to first notice in the prior 7-10 rolls (back share of OI three days before first delivery vs the 7-cycle average; JPM May 2019; weighted 10-roll average, Citi 21 Aug 2026). CBOT rolls earlier than other exchanges because delivery can occur on any day of the month. Plot the tail-adjusted roll against the average of the last five rolls on a trading-days-to-first-notice axis (Citi, 14 Aug 2026).
**Do not infer direction from OI changes**: the market is net flat, daily data cannot separate intraday reversals, futures shorts often hedge cash longs, OI has roll seasonality and is reported with a 1-2 day lag (Duering 2021).

**Timeline (US, Aug 2026, Citi):** 50% rolled Tue 25 Aug (about 4 trading days before first notice); peak roll volume Wed 26 Aug; first intention day Fri 28 Aug; first day longs can be noticed Mon 31 Aug; longs roll by close Fri 28 Aug to avoid early delivery. Allocation: 100% pro-rata for US and WN rolls, 20% FIFO + 80% pro-rata for TU/FV/TY/UXY.

### 7. Delivery timing and the seasonal into first notice
- Positive carry: deliver late (more than 90% of June TY/UXY/US/WN deliveries came in the last week); negative carry: deliver early. Carry to optimal delivery on 11 Aug 2026 (ticks): TU 1.6, FV -0.3 (only negative, so early), TY 2.3, UXY 2.2, US 5.5, WN 3.8 (JPM, Aug 2026). When financing was high, early delivery was optimal in all six contracts and about 75% of Dec-2022 deliveries came in the first two days (Citi, 17 Feb 2023).
- Wild card: the invoice is fixed at the 3pm settle but the short can declare delivery until 7pm while cash keeps trading, which matters most in FOMC delivery months (2:30pm press conference). Delivering on the wild card forfeits the remaining net basis; rule of thumb: delivery pays when (cash price - 3pm cash close) x (1 - CF) exceeds gross basis x CF (BofA, 10 Jul 2025). Worked case in [references/worked-examples.md](references/worked-examples.md).
- Seasonal (Burghardt Exh 6.10, Jun-1997 to Mar-2001 averages, chart read): the calendar drifted from about 10/32 fifteen business days before first notice to about 8.5/32 around it as longs rolled. Shorts needing to roll: buy the calendar just before first notice. Longs: roll early, sell the spread well before first notice.
- Delivery-month alternatives: unwind, roll, or set up for delivery; "refreshing" the long futures only postpones delivery to the last trading day. After the last trading day the CTD basis = remaining carry + end-of-month option.

### 8. Trading a mispriced calendar
- Calendar rich: sell it (sell front, buy back) and deliver into the front: this is a short deferred basis entered better by the mispricing. Cheap: buy it, take delivery on the front, long deferred basis at a lower price. Example: on 4 Apr 2001 the Sep 10y CTD basis was about 4/32 under fair; entering via the June/Sep calendar would add 2/32 to 3/32 (Burghardt 2005).
- Hedge rolls: if the calendar is cheap, buy it to roll a short; if rich, sell it to roll a long.
- An **outright** calendar has yield-curve risk and **no convergence anchor**: Burghardt judges it riskier than its expected profit. Prefer a calendar that is also a cheap entry into a basis you want.
- Shortages: the calendar widens when front CTD supply is low relative to expected deliveries: shorts buy the front and sell the back to avoid delivery, at a price that grows with P(fail) and the next CTD's BNOC. March 2001 Bobl: OI peaked at EUR 57bn two weeks before expiry, CTD BNOC -70 cents, the Mar-Jun calendar widened from about 0 to 70 cents (Burghardt 2005). A front CTD leaving the back basket loses its liquidity premium: trade by buying the basis of the second CTD or selling the calendar into expiry. A schatz-style unissued back CTD: buy the calendar if you expect a large or cheap new issue, sell if scarce or rich.
- Large OI with deep shorts does not by itself imply a squeeze: the Aug-2026 JGB roll passed without incident (Citi, Japan Rates Weekly, 21 Aug 2026). JGB calendar drivers: CTD slope (about 5bp between the two CTDs; 1bp of flattening is about -0.07 to -0.08 yen of calendar), IRR versus OIS, CTD outstanding; CTD spread vol more than doubles in the year before delivery (Citi, 21 Aug 2026; Huggins & Schaller, 2024; figures in [references/worked-examples.md](references/worked-examples.md)).

### 9. STIR strips (SOFR and similar)
Roll the 2nd listed contract into the 3rd, not front into back: once fixings are known the in-period front is sticky. Measured roll cost: 138bp at the end of the reference quarter vs 4bp at the start (Dec-19 to Mar-20) (Huggins & Schaller, SOFR Futures and Options, 2022). SR1-SR3 spread, in-period front-month adjustment and the 3-SR1 pair vs 10-SR3 ratio are in [references/market-specs-and-conventions.md](references/market-specs-and-conventions.md). For swap-curve IMM rolls: roll volume concentrates in the last sessions (Friday before expiry over 21% of rolled risk); the stub and the implied-to-settlement price switch are the P&L effects to manage (Clarus, 31 Mar 2015).

### 10. Roll-adjusted generic and spread series
1. **Store specific contracts as the primitive**; keep the generic-to-specific map as a roll table (`roll_map`: generic, date, instrument, `roll_rule`); derive constant-maturity and weighted series as views, never as raw data.
2. **Roll rule must use only information known at the previous close**: the contract held over day t (`held[t]` in the script) must be chosen with data up to t-1, so shift any OI/volume-based rule by one day. Typical rules: first position day, first notice, last trade, OI-max, volume-max, IMM cutoff. Record it: series built with different rules are not comparable. Liquidity moves before expiry (about half of OI has rolled 4 trading days before first notice), so an IMM/expiry rule holds a thin expiring contract for weeks.
3. **Back-adjust**: gap at the roll = new contract price minus old contract price at the close on which the roll executes (same snap); cumulative gaps shift history so the series is continuous and the last value equals raw (`matchEnd`). Use rolled prices for P&L and mark-to-market, raw prices for position sizing and capital (de Prado, Advances in Financial Machine Learning, 2018).
   Open-to-close gaps work when only bar data exist, but a settle-to-settle gap on the same snap is cleaner (script: `stitch`).
4. Rolled prices can go negative; the non-negative alternative is `returns = pnl / previous raw close`, `rPrices = cumprod(1 + r)` (script: `ratio_px`).
5. **Never book the roll as a return.** Charge the round-trip cost per roll (calendar bid-ask in 32nds) and a back-test roll date, e.g. a fixed number of business days before first notice (about 5-6 matches the liquidity migration above).
6. **Spread series** (calendar, fly, basis-versus-futures): modelling the spread directly fails because weights change over time, spreads go negative, legs trade non-simultaneously, costs. Model the value of $1 in the spread as a total-return series: holdings `h = omega x K / (o_next x phi x sum|omega|)` at rebalance/roll bars, P&L on open-to-close at the roll bar, costs outside K, tradeable volume `min_i(v_i/|h_i|)` (de Prado 2018).
7. Mean-reversion on rolled futures: rolling can create spurious cointegration and spread profits can vanish at expiry (Quantitative Finance Stack Exchange, Mean reverting strategies, 2011).
8. Data hygiene: IRR/IRP series built from non-contemporaneous futures and CTD prices spike; roll the monitored contract about 5 days before the delivery month; use the same snap for both legs (Quantitative Finance Stack Exchange, Treasury futures implied repo, undated).

## Worked example
**Illustrative same-CTD roll (labelled illustrative, not a market quote).** Dirty price 100, coupon 4%, repo to d2 3.5%, gap d1 to d2 = 92 days, CF 0.80 on both:
carry = 4 x 92/365 - 100 x 0.035 x 92/360 = 1.0082 - 0.8944 = +0.1138; carry part of fair roll = 0.1138/0.80 = 0.1422 = **4.55/32**.
Option part: back net basis 3/32 above front -> +3/32/0.80 = +3.75/32. Fair roll = **8.3/32**. A market roll of 9.6/32 is **1.3 ticks rich**: sell front, buy back (if the option model and CTD robustness hold); a +25bp repo move over the 92 days lowers fair by 100 x 0.0025 x 92/360/0.80 = 0.080 = 2.6/32 (JPM's rule of thumb, price 100 over a quarter: 0.0625/0.80 = 2.5/32).

**Futures from basis (Burghardt 2005, 4 Apr 2001, 5y).** CTD 5-3/4% 11/05 at 105-02.5, theoretical June basis 13.8/32, CF 0.9904: `FV = (105.078125 - 0.43125)/0.9904 = 105.66`, quoted as 105-21.2 (printed rounding).

**Citi roll scorecard, 18 Aug 2026 (U6-Z6).** TU 3.875 ticks (AM 38.5% of OI, smallest since H4-M4) slightly bullish; FV 4.25 bearish (AM 44.8%; roll near fair whereas past rolls traded cheap); TY 9 bearish (AM net long 36% to 46.8% of OI, largest since 2007); UXY 10.25 slightly bullish; US 10.5 slightly bearish (same-CTD rolls traded lower); WN 13.25 neutral (CTD robust to +/-25bp). JPM's four-driver view on 12 Aug 2026 mapped TY bearish (z 2.0), UXY mildly bearish, WN neutral, US bullish on basis convergence, FV and TU no call. More cases (calendar IRP, JGB, Bobl squeeze, SOFR, equal-DV01 roll): [references/worked-examples.md](references/worked-examples.md).

## Signals & interpretation
- **Fair-value gap.** `|market - fair|` above roughly 1 tick for the 2y/5y contracts or 2-3 ticks for TY/UXY/US/WN is worth a look; below that sits within model error and bid-ask (practitioner default, calibrate on prior rolls). Always check the repo used: a special CTD or an overridden repo flips conclusions.
- **Positioning.** z >= 1.5 in AM net longs with a regression residual that is not already cheap = expect cheapening early in the roll month, convergence in the last week. High-percentile AM longs with the calendar already cheap is the confirmation; the relationship is "not easy to prove statistically" and showed no cheapening in 2023 and early 2024 when AM longs were low.
- **Roll pace.** Pace ahead of the 7-10 roll average = heavy long positioning or pre-positioning; a calendar that is cheap and rolls ahead of pace has already paid for it.
- **Calendar IRP vs forward funding:** IRP < forward repo = rich (negligible options); > = cheap. If options matter, OABNOC/RAYS front < back = rich.
- **Confirmations before trading:** same-CTD or CTD-slope view consistent with step 3; CTD robust to +/-25bp and a twist; delivery-timing convention checked (first vs last); liquidity window (do not execute outside the 50%-rolled to first-intention window unless intended).
- **Do not trade** a rich/cheap read that disappears when the forward repo is changed by 5-10bp or the CTD flips, or an outright calendar with no basis leg and no yield view.

## Pitfalls
- **Delivery-date conventions change.** First notice was stated as 2 business days before the contract month in 2005 and as the last business day of the preceding month in 2026 notes. Read `fut_static` for the current rule; never hard-code.
- **Regression betas are unstable and small-sample.** Fits use about ten roll cycles; the TU CTD-slope beta was 0.14 (R^2 0.91, on 1s3s, Feb 2023) but 0.045 (R^2 0.16, on 1s2s, Aug 2026). Re-estimate each cycle, report n and R^2, and treat a low-R^2 beta as indicative only (Citi, 17 Feb 2023; 18 Aug 2026).
- Positioning signals are regime-dependent (low AM longs in 2023/early 2024: no cheapening); exclude extreme-vol cycles (Nov 2016 post-election) from regressions; CTD-slope flatness vs the fitted curve often persists through the roll month.
- **Pattern is not universal**: early-month cheapening then convergence is the generic pattern when AM longs are high, but TY cheapened into the last week and rallied in the final 4-5 days (Citi, Aug 2026). Non-economic long rollers can drive the roll price ("lost some of its put characteristics", Citi, 21 Aug 2026).
- WI bonds inflate measured option value and their basis is blank until issued; a placeholder row (factor 1.0000, BNOC -70) is not a real CTD. CTD maps parsed from PDFs are unreliable: cross-check.
- Calendar spread levels in dealer scorecards are theoretical mids and front prices are bids: align snaps before comparing.
- Negative net basis is not free money when deliverable supply is short: price it as P(fail) x BNOC gap.
- Forward-repo dependence: calendar fair value is only as good as the forward repo (the d1 to d2 tail), not the spot-start term repo.
- Do not assume convergence: delivery-option value decays to zero at expiry but only for the CTD; the speed of convergence is the risk (CFTC MRAC, The Treasury Cash-Futures Basis Trade, Dec 2024). Only a small single-digit % of positions are delivered (about 2.8%).
- A wide calendar is not automatically cheap: roll-period flows can move it with no change in fair value (ask why before fading).
- Roll-date detection errors give wrong gaps; a generic that changes rule midway is not a series. Generics with serial rolls (1st/2nd) jump at expiry; "most active" series switch when activity migrates, which is not always obvious (Duering 2021).
- Hedge/roll ratio from CTD-converted BPV jumps at inflection points: use OABPV.
- Source text conflicts to verify: wildcard interval stated as 6 and 15 hours in one vendor guide; one convergence caveat (CF rounding of remaining maturity, commenter claim) is unverified.

## Output
Return: (1) a table per contract: `front | back | CTD f / b | market roll (32nds) | fair roll (carry part, option part, curve part) | rich(+)/cheap(-) ticks | calendar IRP vs forward repo | BPV ratio (back per 1,000 front) | roll progress vs 7-10 roll average | AM net long z / residual | view`. (2) Assumptions stated: delivery convention, repo used (GC or specific), option model source, snaps. (3) Sensitivities: +/-25bp repo, +/-10bp CTD slope, CTD switch scenarios. (4) For a trade: legs, ratio, entry, stop in ticks, roll date, delivery plan. Hand off to rv-trade-idea-writeup; for a continuous series, deliver `roll_map` with the rule plus the adjusted series and the gap table.

## Scripts
- [`scripts/roll_fv.py`](scripts/roll_fv.py): fair roll with carry/option decomposition, calendar IRP, funding sensitivity, BPV roll ratio, positioning regression (`fit_line`), back-adjusted and non-negative generic series (`stitch`), and a canonical-table front end (`fair`, `stitch` sub-commands). Supports ACT/ACT ICMA and ACT/365F accrued; other day counts must be passed in. `python scripts/roll_fv.py --help`. `--selftest` checks a published futures-fair-value case, analytic zero-coupon and funding cases, published roll-ratio and DV01 numbers, a known regression, a known stitch case and an end-to-end canonical-table case, and exits non-zero on failure.

## Related skills
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): net basis, IRR and CTD that feed the fair roll
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): option value in the front and back basis, CTD scenario analysis, squeezes
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): futures versus swaps and CTD-based hedging
- [stir-futures-rv](../stir-futures-rv/SKILL.md): SOFR/SONIA/Euribor strip spreads, flies, packs
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures versus forward adjustment for strip rolls
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): GC vs special repo, term structure, turns
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): CFTC trader classes and positioning z-scores
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and rolldown conventions
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts, settlement, contract conventions
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 and hedge-ratio conventions
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): regression of roll on CTD slope and positioning
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score screens
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): CTD cheapness against a fitted curve
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): snap alignment, stale legs, roll-rule hygiene
- [bt-backtest-design](../bt-backtest-design/SKILL.md): continuous futures in back-tests, roll costs
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used above

## References
- BofA Global Research - US Rates: Primer: US Treasury futures and basis (Ralph Axel, 10 July 2025): tail-repo and CTD-slope drivers of the roll, who rolls (asset managers vs levered funds), delivery-date convention, wild card, CTD migration, contract specifications and a basket example.
- J.P. Morgan (Ozil, Hayward, Alptuna) - U.S. Bond Futures Rollover Outlook, Sep 2026 / Dec 2026 (12 Aug 2026): four-driver framework, calendar IRP, OABNOC/RAYS, AM z-scores, risk-weighted OI, roll ratios, carry to delivery, scorecard.
- Citi Research (Datla, Williams, Vazquez Plata) - US Rates Strategy: Treasury Futures Roll, Sep26-Dec26 (18 Aug 2026), and US Rates Weekly (21 Aug 2026): roll fair value, AM positioning, CTD-slope regressions, delivery timing, roll levels.
- Citi Markets (Futures Sales) - CBT Treasury Futures Sep/Dec Roll, 10 and 5 trading days until FND (14 and 21 Aug 2026): tail-adjusted roll, roll-pace monitor, roll calendar, allocation rules.
- Citi Research - US Rates Weekly (10 May 2019) and (17 Feb 2023): positioning regressions, CTD-change example, early delivery share, regime caveats.
- Citi Research (Mathai, Shah, Shapiro) - US Rate Strategy Notes: The long end basket case (4 Feb 2015): equal-DV01 roll after a basket change.
- J.P. Morgan - US Fixed Income Markets Weekly (31 May 2019; 23 Aug 2019): roll-pace measure, CTD micro-curve, GC term-structure rule, wildcard and long-end vol.
- J.P. Morgan Derivatives Strategy - Basis Scenario Analysis Report (28 Oct 2026): CTD maps, term repo to delivery, WI treatment, twist scenarios.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis, 3rd ed. (McGraw-Hill, 2005): futures fair value, calendar mispricing trades, first-notice seasonal, squeezes, market specifications.
- Duering - Fixed Income Trading and Risk Management (Wiley, 2021), Ch. 12-29: roll definition, BPV roll ratio, roll progress, OI cautions, clearing structures.
- Huggins & Schaller - SOFR Futures and Options (Wiley, 2022): SOFR roll rule, SR1-SR3 spread, in-period front SR3, roll cost.
- Huggins & Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): JGB spread vol into delivery, OABPV hedging.
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018), Ch. 2: roll-gap adjustment, non-negative series, ETF trick for spreads.
- RiskVal Financial Solutions - Overview 201: Cash and Futures (12 Nov 2021); help article Bond Futures: Futures Calendar Roll (2024); Highlights newsletter (Mar 2023): smooth-ASW theoretical roll, R/C ASW Z sign rule, roll-date preferences.
- Citi Research - Japan Rates Weekly (21 Aug 2026): JGB calendar drivers and sensitivities.
- Clarus Financial Technology - The IMM Roll for Swaps (Barnes, 31 Mar 2015): roll volume concentration, curve-roll P&L effects.
- CFTC Market Risk Advisory Committee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): delivery share, convergence caveats.
- Quantitative Finance Stack Exchange - "How does one price the market value and estimate the fair value of a bond futures roll?" (2018): net-basis roll form; "Mean reverting strategies" (2011); Treasury futures implied repo Q&A.
- Leung & Li - Optimal Mean Reversion Trading (World Scientific, 2016), Ch. 5: roll-yield definition for commodity-style futures (context only).
