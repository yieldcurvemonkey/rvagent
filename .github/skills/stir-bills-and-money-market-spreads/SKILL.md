---
name: stir-bills-and-money-market-spreads
description: Prices and trades the front-end spreads between T-bills, OIS, SOFR/EFFR, ON RRP and money-market fund (MMF) demand. Covers bill-OIS and bill swap spreads by tenor (1m/3m/6m), discount-to-simple yield conversion, net bill supply and its financing waterfall, MMF AUM/WAM/WLA and 2a-7 eligibility, ON RRP drain, bills-minus-reserves, debt-limit/X-date and TGA rebuild, CMBs, buybacks, SOFR-FF futures basis, JPY T-bill ASW, BBSW-OIS. Use when the user asks about T-bill richness or cheapness vs OIS, bills vs SOFR, 1m/3m/6m bill spread, bill supply or paydowns, debt ceiling or debt limit, X-date, TGA rebuild, MMF demand or WAM, ON RRP drain, or bill-funded buybacks. SOFR-FF basis is spread-tenor-and-index-basis; reserves and QT are stir-central-bank-balance-sheet-and-reserves.
---

# Bills and money-market spreads

Bills and OIS are both near risk-free, so the bill-OIS spread is mostly a supply, demand and funding-collateral
spread. Bill yields are set by who has to buy them: money-market funds (MMFs) with short mandates, dealers, and
foreign officials, against net issuance and the repo or RRP alternative. The spread moves on supply flow more than
on stock, and it jumps around debt-limit episodes and Fed balance-sheet regimes. This skill turns bill and
money-market quotes into comparable yields, measures richness vs OIS, and maps the supply, MMF and debt-limit
drivers that move it. Reserves, repo plumbing and the corridor belong to the sibling skills linked below.

## When to use
- Bill richness or cheapness vs OIS, "1m / 3m / 6m bill spread", T-bill swap spread, bills vs SOFR or FF OIS.
- Forecasting bill cheapening or richening from net issuance, CMBs, paydowns, or a buyback programme.
- Debt ceiling / debt limit / X-date: bill-curve kinks, TGA rebuild pace, SOFR-FF pressure after resolution.
- MMF demand: AUM growth, WAM/WLA, 2a-7 60-day WAM and 397-day eligibility, MMF holdings of bills.
- ON RRP balances, RRP-to-bill switching, "bills minus reserves" funding models.
- SOFR-FF or SR1-ZQ basis trades, JPY T-bill ASW vs CP or cross-currency funding bills.
- Not for: repo specials, GC/triparty mechanics, reserve ampleness (see the linked skills).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Bill prices (price per 100) or discount yields by maturity | `bond_quotes` (bill instrument_id, `clean_px`, `settle_date`) | daily snap, >= 2y | Price, not yield: convert with the bill's own day count. |
| Bill auction results (stop yield, size, cover, tail) | `auctions` (`stop_yield_pct`, `offered_ccy`, `allotted_ccy`, `bid_to_cover`) | every auction, >= 2y | Basis for net issuance; a CMB is an auction too. |
| Matched OIS curve (SOFR or FF) | `curve_par` (`curve_id`, `start` 0D, `tenor` 1M-1Y) | daily close, >= 2y | Use the same index the bill spread is measured against. |
| Policy and index fixings (EFFR, SOFR, IORB, ON RRP) | `rate_fixings` with `rate_indices` family POLICY/RFR | daily, >= 2y | Gives SOFR-FF and RRP-minus-bill spreads. |
| Repo / triparty rates | `repo_rates` (`collateral`, `term` ON, `segment` triparty) | daily, >= 2y | Repo alternative to bills for MMFs. |
| SOFR and FF futures | `stir_quotes` (SR1 and ZQ, `price_px`) | daily settle | SR1-ZQ price basis for SOFR-FF; use settlement, not last. |
| Fiscal and balance-sheet series (TGA, bills outstanding, reserves, ON RRP, MMF AUM, net bill and coupon supply) | `macro_series` | weekly or daily, >= 3y | Series ids follow `<CC>-<AGG>` (`US-TGA`, `US-ON-RRP`; unit `ccy_bn`), see the `macro_series` patterns in `data-contract-and-adapters`. |
| Calendars (settlement, tax dates, X-date, FOMC) | `calendars`, `cb_meetings` | future-dated ok | Needed for business-day counts and turn effects. |

Look-ahead: SOFR and other fixings publish the next business day and `auctions` results only exist from
`results_ts_utc`, so read inputs as-of the signal time (see `data-contract-and-adapters`). Compute z-scores from data
up to the signal date and trade the next day.

If an input is missing (for example MMF holdings, or debt-limit extraordinary-measure inventory), ask the user or
hand off to the data adapter. Never invent values.

## Conventions (fix these before any number)
- **Units:** yields and rates in percent, spreads in bp. `bill_ois_bp = (bill simple yield - matched OIS) x 100`.
- **Sign:** positive bill-OIS = bill yields above OIS = bill **cheap**. Some sources print OIS minus bill, with
  negative = bill cheap. Flip those before combining. The cited sources are mixed, so always state the sign next to
  each figure you quote. Citi's "T-bill swap spread" is swap minus bill, so its z of -3.4 means bills cheap
  (the opposite sign to `bill_ois_bp`).
- **Compare simple with simple:** money-market simple yields on the index basis (USD bills and SOFR: ACT/360).
  Never compare a discount rate with a simple rate or a YTM directly.
- **OIS choice:** SOFR OIS for USD bills post-2021. Older work and FF-based analysis use FF OIS. The SOFR-FF
  basis is a few bp and moves in stress, so a switch of benchmark changes the answer.
- **SR1-ZQ futures basis** is price-based. Positive price basis = SOFR priced below FF = easier conditions. The
  realised SOFR minus EFFR spread has the opposite sign: positive realised = tighter. Quote both and say which one.

## Method

### 1. Put every bill on one yield basis
Bills are quoted on a discount basis. A discount rate understates the yield, so convert before comparing.

- Discount price (US convention, ACT/360): `P = 100 x (1 - d x t / 360)`, with `d` the discount rate in decimal
  and `t` days to maturity.
- Money-market simple yield: `r_s = (100 / P - 1) x 360 / t`. Identity: `r_s = d / (1 - d x t / 360)`.
- ACT/365 simple, for comparison with the 365-day markets: `r_365 = (100 / P - 1) x 365 / t`.
- Gap from discount to simple: at `d = 4.00%`, a 6m bill (182 days) has `r_s = 4.0826%`, i.e. the discount
  quote understates the yield by about 8bp. The gap grows with tenor and with the rate level.
- Default basis: 360 for USD bills and SOFR; for GBP, JPY and other 365 markets, read the index's day count in
  `rate_indices.day_count` and use it. Keep the basis explicit in every output.
- Use the bill's own YTM convention when comparing with bonds: model it as a zero-coupon bond with one period.
  Canadian bills use different YTM definitions above and below one year (Darbyshire, undated).

`scripts/bill_yields.py` implements these, and its `--selftest` checks them against hand-computed values.

### 2. Matched-tenor OIS and bill-OIS
- OIS zero-equivalent for a bill maturing at `t` (simple, ACT/360): `r_OIS(t) = (1 / DF(t) - 1) x 360 / t`, with `DF(t)`
  from the OIS curve (see `fi-curve-construction`). Interpolate to the bill maturity; do not use the nearest
  pillar for a 1m bill against a 3m pillar.
- `bill_ois_bp(t) = (r_bill_s(t) - r_OIS(t)) x 100`. Report 1m, 3m and 6m separately. The 1m is the MMF
  switching and RRP line; the 3m and 6m carry the Fed-path and term component.
- Term premium in bills: a bill curve that is cheap at 3-6m and rich at 1m is normal when Fed-path uncertainty is
  high (see section 5). Historically, Treasury bill returns rose monotonically from 1m to 9m in every five-year
  subperiod of 1970-94 (Ilmanen, 1995), so a positive term component is the default. Do not assume bills trade flat
  to OIS.

### 3. Richness signal
- Z-score the bill-OIS level over a 1y window (about 252 business days): `z_t = (x_t - mean_252) / sd_252`. Sources
  use 1y z-scores for the bill-swap spread (Citi, Oct 2026), so the 1y window is the default. Flag `z <= -2` (rich)
  and `z >= +2` (cheap) as a starting screen, not a rule.
- Use the level history only with context. Sources report the 3m bill-OIS path roughly as -10 to -17bp in 2015-17,
  0 to +8bp in 2018-20, a trough near -34bp in 2022, and +4 to +8bp in 2023-24 (Barclays, Jan 2025). A 2022-style
  trough is a regime, not a z-score outlier.
- Flow beats stock. The share of bills in debt is a weak predictor of bill-OIS. Model it with the 3m change in net
  bill supply (Barclays, Jan 2025): large paydowns coincide with very rich bills (to about -50bp), large issuance
  with 0 to +15bp. "Flow" here is cumulative issuance over a window, not one week's settlement; cheapening persists
  when MMF inflows stall (Barclays, Oct 2026).
- Free float: bills held by the public net of Fed and government-MMF holdings. Negative net supply shrinks it and
  richens bills (J.P. Morgan, Feb 2020; framework estimate: bills -5 to -10bp vs OIS).
- 3m vs 6m: the quarterly 6m-3m bill spread is stationary (beta fixed at 1, DF t -7.71, AR(1) coefficient 0.33;
  Wooldridge). In weekly 1958-2004 data only the 3m leg adjusts (Tsay, 2010). Trade the tenor spread, not levels; with
  an estimated beta use the stricter Engle-Granger critical values. These are historical samples, so check the
  relation on a post-2008 sample before relying on it.

### 4. Net bill supply: the financing identity
- Marketable borrowing need = deficit + other adjustments + change in cash (TGA).
- Net coupon supply = gross coupons auctioned - maturing coupons held by the public - buybacks.
- **Net bill supply = borrowing need - net coupon supply** (BofA, Jul 2025). Net supply to the public adds Fed
  bill-maturity roll-off.
- Worked (BofA FY25/26/27, $bn): need 1,819 / 2,100 / 2,100; net coupons 1,505 / 1,275 / 1,033; net bills 314 / 825
  / 1,067; bill share 21.4% / 22.6% / 24.3% (BofA, Lower UST WAM => backdoor easing, 2 Jul 2025). The same identity
  gives the bill supply in each debt-limit scenario.
- Buybacks are not WAM-neutral. Treasury funds them like any other need, which implies more bill supply (Citi,
  Aug 2026; BofA, Jul 2025). Raising the long-end buyback from $2bn to at least $4bn per operation
  adds at least $14bn per quarter of bill-funded supply (Citi, Aug 2026).
- Seasonality: January tax receipts pay bills down; February to mid-April refunds bring CMBs; mid-April to June
  paydowns. The 12m bill-OIS richens in April-May on tax paydowns, about 7bp cumulative on average over five years
  (Citi, Feb 2017). Strip these seasonal flows before reading supply signals.

### 5. Supply-to-bill-OIS screen and MMF demand
Use the flow sensitivity from your own sample, not from the older sources. For the screen itself, the 2019 Citi
result on Treasury-vs-OIS is a useful bound: regressing 1m and 3m changes in the spread on 1m and 3m cumulative bill
supply gave coefficients of about -0.013 to -0.036 bp per $bn (t -1.7 to -3.6), in the swap-spread sign (OIS minus
Treasury yield) and only for the 2y, with a 25% haircut on historical WAM betas (Citi, Jan 2019). Applied: a $130bn
paydown widens the 2y spread by +2 to +5bp (Treasury yield falls vs OIS: Treasuries rich); +$220bn of bills tightens
it by -3 to -8bp (Treasuries cheap). Use these as the sign and scale check, and haircut them by at least 25%. The
windows overlap, so a re-estimate needs non-overlapping changes or HAC standard errors.

MMF demand model (BofA, Oct 2025):
- MMF bill demand growth = AUM x AUM growth x bill allocation.
- Worked: $7.34tn x 10% = $734bn of new AUM; x about 33% bill allocation = about $242bn. The note itself prints
  about $225bn, which implies a bill allocation near 30.6%. Use a 30-33% range and show it.
- AUM growth depends on the 3m bill yield, with a lag: flat at 0-1%, about 10% a year at 2-3%, about 15% a year at
  4-6% (BofA, Jul 2025, and BofA, Oct 2025; see [MMF and G10 detail](references/mmf-and-g10-bills.md)).
- Other demand (ROW and other investors) is an unstable residual. Haircut it: about 10% a year post-COVID growth,
  but only $150-250bn a year is reliable (BofA, Oct 2025).
- Gap: demand of $375-475bn against about $600bn of FY26 supply leaves a gap of at least $125bn (BofA, Oct 2025).

Other MMF signals:
- **Fed-path uncertainty shifts tenor:** MMFs shorten when hikes are uncertain, so 1m rich and 3-6m cheap, and FRNs
  richen. Proxy: MOVE vs 6m bill-OIS (BofA, Oct 2026).
- **Indirect bidders:** a fall in 3m indirect take-down often coincides with a rise in 1m take-down (BofA, Oct 2026).
- **WAM and WLA:** government MMF WAM near 40 days (BofA, Jul 2025) leaves little room to extend into bills beyond
  about 1.5 months, so new supply at longer tenors must cheapen. WLA falling while WAM is flat means a shift out of
  government debt, into term repo or agency.
- **2a-7 eligibility:** WAM limit 60 days; maximum maturity 397 days. Bills and notes near the eligibility cut-off
  richen as they age into eligibility (Fleckenstein and Longstaff, 2023). Watch aging issues near 397 days. The
  2010 cut of the WAM limit from 90 to 60 days made 1m bills about 7.9bp richer vs 1y bills (same paper). MMFs hold
  1m bills and overnight repo because repo counts as zero-day maturity for the WAM (Conks, Jan 2025).
- **Bills vs repo switching:** a sizeable RRP drain needs 1m bill yields above both the RRP rate and SOFR, with the
  bill-repo spread widening (Conks, Jun 2023). Monitor 1m bill minus SOFR and minus RRP.

### 6. ON RRP, reserves and the bill-funding link
- Simple ON RRP regression (BofA, Aug 2025): daily change in ON RRP = -0.52 x change in net bill supply - 8.3 ($bn,
  settlement dates since Aug 2023, R-squared 0.20). Use the direction and scale, not as a forecast; the beta is
  unstable near zero.
- Level model (Citi, Dec 2024): RRP = -0.492 x (bills outstanding - Fed liquidity) + 1519, R-squared 0.98 from Jan
  2023. Fed liquidity = Fed assets less liabilities other than reserves and RRP. Run it alongside the flow model,
  because the two give different answers in a shrinking-bill regime.
- Sequencing: bills first drain RRP; once RRP is near zero, the drain falls on reserves and repo rises above IORB
  (BofA, Aug 2025). Do not read the RRP balance as the reserve buffer until it is gone.
- Bills minus reserves (Citi, Feb 2023; Aug 2026): regress SOFR-FF on reserves and bills outstanding with month-end
  controls. The levels fit is y = -0.011x + 5.084 (R-squared 0.59, x = bills minus reserves in $bn, y presumably in
  bp, so about 1bp per $100bn; y is FF minus SOFR, the futures price sign). The slope is much lower in 2022, and in
  weekly changes the post-2021 beta on bills minus reserves is about -0.3bp per $100bn (t -2.1) against -0.8 for
  2010-25 (t -3.8); bills alone are insignificant (Citi, Jun 2025). Use a post-2021 sample and re-estimate before
  relying on it.

### 7. Debt-limit state machine
Treat the debt limit as a sequence, not an event. Map the current phase, then apply the matching signals.

| Phase | What happens | Signals |
|---|---|---|
| 1. Limit binds | Extraordinary measures (EM) and TGA spend-down; bill paydowns; coupons kept on schedule. | Bills rich. MMF cash goes to RRP while it has a buffer (2017-19, 2023) or, with RRP depleted, from RRP into non-Fed repo (Conks, Jan and May 2025). |
| 2. Pre-X-date | Cash and EM run out. Bills maturing near the X-date cheapen, bills maturing just after it cheapen most. | Kink in the bill curve; 1m bill-OIS cheapens; GCF repo up to +20bp into prior X-dates (BofA, May 2025). Markets price the risk only about 2 weeks ahead. |
| 3. Resolution | TGA rebuilt with heavy bill issuance, drains RRP then reserves; SOFR rises vs IORB and EFFR. | Use the TGA rebuild table below. Bills cheapen; SOFR-FF tightens. |

TGA rebuild pace after resolution (BofA, Jun 2025; 2013-2023 episodes, average business days to close a share of
the gap): 5% in 3 days, 10% in 5, 20% in 10, 30% in 13, 40% in 21, 50% in 28, 60% in 30, 70% in 31, 80% in 34, 90%
in 43, 100% in 51. The rule of thumb is about 51 business days to reach target. Dispersion is large (20-day
closure ranged from 0% to 112% across episodes), and recent episodes were slower, so skew to a slower build.
`scripts/bill_yields.py` implements the days-to-close lookup as `business_days_to_close`.

Expression of the resolution trade (BofA, Funding & debt limit, 27 Jun 2025): prefer an outright SOFR-FF short to a
SOFR-FF curve trade, because the whole curve cheapens as SOFR moves up and a Fed liquidity add that could anchor later
dates is hard to time. SOFR leads and EFFR follows with a lag. Take the event-study average as a floor, not a forecast:
the study implied at least 4-5bp of further tightening. In the 2019 stress analog SOFR-IORB went from about +7bp
pre-stress to +15bp at the peak and back to +2bp (see
[debt-limit and TGA detail](references/debt-limit-and-tga.md), section 10).

Bill-supply view for each phase: net bill supply is negative while the limit binds. After resolution the wave is
large: BofA sized over $900bn of bill supply from August to November 2025 to rebuild the TGA to about $850bn+
(BofA, May 2025), and Conks put it at up to about $1tn (Conks, Jun 2025).

### 8. SOFR-FF and the bill-funding link
- A TGA rebuild lifts SOFR above EFFR and IORB, so realised SOFR-FF tightens. Quote the sign of the position
  (futures price basis or realised) on every trade.
- Sign map: the SR1-ZQ price basis equals FF minus SOFR in rate terms. BofA and Citi quote it that way ("short
  SOFR/FF" = bet SOFR rises vs EFFR). Conks calls the same bet "long the SOFR-FF basis" (the realised SOFR minus EFFR
  spread, the opposite sign), so one position carries opposite labels. Restate every trade in your sign before you
  act (see Conventions).
- Bill vs SOFR futures: the price of 3m SOFR futures minus the price of 13-week T-bill futures equals the bill yield
  minus the implied SOFR (positive = bills cheap). Both have a DV01 of USD 25, so the spread is traded 1:1 (CME, Apr
  2024).
- Quarter-end SOFR above EFFR is seasonal, and month-end and quarter-end turns distort any z-score; model them
  separately from "good days" (Citi, Jun 2025).

### 9. Non-USD bill and money-market spreads
- **JPY 3m T-bill ASW:** `fair value = (a) 3m CP minus 3m bill (credit and stress) + (b) regulatory and liquidity
  costs + (c) year-end turn premium (about +15bp in Oct-Dec)`. Jun 2025 example: (a) 9.5bp + (b) 9.2bp = 18.7bp
  model vs 17.9bp actual, residual -0.8bp (J.P. Morgan, Jun 2025). The ASW is the USD pickup on yen bills over USD
  bills, so a high reading means yen bills are cheap in USD terms. A 12m rolling regression on the 3m USD/JPY
  basis, monthly net bill issuance and 3m GC/OIS gave a residual near -4bp in Feb 2025 (bills rich)
  (J.P. Morgan, Feb 2025). Overseas investors held about 67% of Japanese
  T-bills at end-2022 (BofA, Apr 2023). Money-market funds in Japan are dip-buyers of cheapness, not richness.
- **EUR:** French bills cheapened vs ESTR in the Oct 2026 OAT stress, with Schatz-ESTR and FRA-ESTR wider (Barclays,
  Oct 2026). Per Citi the deposit facility rate acts as a cap on GC, most visibly in Bunds (as printed; verify on your data).
- **AUD:** BBSW-OIS normalised to about 8.5bp from the wides (Citi STIRT, Aug 2026). AUD FRA-OIS can look too narrow
  vs the hedged cost of bank offshore issuance (J.P. Morgan, Jun 2025).
- **NZD:** tax outflows cut settlement cash; NZIONA-SOFR (1w-1m) tightened 5-7.5bp in Aug 2026 while forward spreads
  held (Citi STIRT, Aug 2026).
- **GBP:** the BoE reserve level sets the cap on balance-sheet-driven basis moves (J.P. Morgan, Jun 2025).
- **CAD, CHF, SEK, NOK:** the research base has no bill-specific material for these markets. Use the same
  framework with the local auction and day-count conventions from `fi-g10-market-conventions`, and do not fill
  from memory.

## Worked examples
- **Conversion (computed):** 4.00% discount, 90 days, ACT/360 gives `P = 99.00` and `r_s = 4.0404%`. The script
  reproduces both from the price.
- **Bill-OIS sign (Barclays, 2 Oct 2026):** 3m bill about +9bp and 6m about +13bp vs SOFR OIS, the highest of the
  year. Both are bill-cheap readings in the sign used here.
- **Debt-limit resolution averages (BofA, Jun 2025):** the source prints average changes in bill-OIS after the
  2017-2019 resolutions as OIS-less-bill, so negative = bills cheap. The three numbers are the horizons 1m / 3m / 6m
  after resolution (the SOFR-FF row averages out that way): 1m bill-OIS -7.5 / -4.0 / -9.3bp and 3m bill-OIS -3.6 /
  -1.5 / -4.2bp as printed, i.e. +7.5 / +4.0 / +9.3 and +3.6 / +1.5 / +4.2bp in this skill's bill-minus-OIS sign
  (bills cheapened). Use the sign and order of magnitude; 2019 is distorted by Fed action.
- **Kink (Citi, Jun 2025):** the 8-week bill maturing 12 Aug 2025 cleared 4.38%, the highest of the last four
  auctions. That is the kink: a bill that matures just after the X-date cheapens relative to neighbours.
- **Bill-funded buyback (Citi, Aug 2026; FT, 19 Aug 2026):** the buyback announcement lifted 3m and 6m bill
  yields, and the 30y fell 8bp to 5.21%. The sequence is long-end rally, bills cheapen, curve flattens.
- **Trade structure (BofA, Jun 2025):** short the Oct SOFR/FF futures spread (price basis, FF minus SOFR), entry
  -4bp, target -8bp, stop -1bp, so a profit means SOFR rising vs EFFR. The source called it the cleanest
  funding-pressure expression and said Oct picks up the Q3 quarter-end, though a 30 Sep print falls outside the Oct
  average, so verify the contract window. Risk: a later resolution or a slower TGA build cancels it.

Full numbers, episode tables and the TGA calendar: [debt-limit and TGA detail](references/debt-limit-and-tga.md).
MMF, holder and G10 tables: [MMF and G10 detail](references/mmf-and-g10-bills.md).

## Signals & interpretation
| Signal | Threshold (default) | Reads as |
|---|---|---|
| 1y z of 3m or 6m bill-OIS | <= -2 or >= +2 | rich or cheap vs its own year; confirm with flow below |
| 3m change in net bill supply | positive and large (say > $200bn) | bills cheapen; paydowns richen |
| 1m bill minus FF OIS | 2-5bp | MMFs leave ON RRP for bills (BofA, Aug 2025) |
| 3-6m cheap vs 1m | rising with MOVE | Fed-path uncertainty; MMFs shorten; FRNs richen |
| MMF AUM growth | 0-1% = flat; 2-3% = about 10%; 4-6% = about 15% | sets the demand base for the bill-gap model |
| Bill share of marketable debt | 15% lower bound; 20% target; 22.5% tolerance; 25% upper | above 22.5% raises term-out risk (BofA, Nov 2024) |
| Days after resolution | business days to close TGA gap | pace of bill wave (see table in section 7) |
| Pre-X-date bill kink | bill maturing just after X-date cheap vs neighbours | debt-limit trade; act 10-15 days before X-date |

Confirmation checks before acting on a bill-OIS signal:
- Is the move supply-driven? Check the 3m net bill supply change and the TGA path before the spread.
- Is the move on a settlement date, a tax date or a quarter-end? Strip the turn.
- Does RRP still have a buffer? If RRP is near zero, reserves carry the drain and the RRP model stops working.
- Does the benchmark match? FF OIS and SOFR OIS can disagree by a few bp, enough to flip a 3-5bp signal.

## Pitfalls
- **Signs:** the cited sources mix bill-OIS signs and SOFR-FF quotes. Restate every number in the convention above.
- **Discount vs simple vs YTM:** a discount rate can be 8bp below the simple yield at six months. Never compare
  them without conversion.
- **Flow not stock:** bill share is a weak predictor. A large paydown can richen bills sharply for a few weeks
  and then reverse.
- **Debt-limit analogs need an RRP and supply condition:** 2021 and 2023 are not comparable with 2017-19 (large
  excess liquidity). Condition every analog on the remaining RRP buffer and on similar percentage growth in bills and
  total supply (BofA, Funding & debt limit, 27 Jun 2025).
- **Fed intervention truncates analogs:** the 2019 funding-stress analog was cut short by Fed action after Sep
  2019 repo stress. 3m and 6m averages for that year are distorted.
- **X-date uncertainty:** the X-date stays uncertain until after the April tax date. Treasury financing forecasts
  have been more optimistic than deficit-based forecasts, so the risk skews to an earlier X-date (BofA, Feb 2025).
- **Kinks are short-lived:** bills cheapen 10-15 days ahead of an X-date. Trade the kink close to the date, and
  expect it to clear once the date is resolved.
- **TGA dispersion:** the 20-day closure figure differs between two source tables (about 39% by interpolation of the
  days-to-close table, 49% from the average-share table). Use a range, not one number.
- **Bill-demand arithmetic:** $7.34tn x 10% x 33% is about $242bn, while the printed figure is about $225bn. Show
  the allocation you use.
- **Chart reads:** levels read off charts (bill curves, bills outstanding labels that look mis-scaled) are
  approximations. Verify against the `auctions` and `bond_quotes` tables before use.
- **Bills are not OIS:** bills trade rich or cheap to OIS for supply and MMF reasons. Do not use bills as the 1y
  swap-spread anchor; use off-the-run 2y notes (Citi, Oct 2026).
- **Mirage:** reserve and RRP levels are inflated while the TGA is being drawn down, so they overstate ampleness
  (Conks, Jan 2025); the rebuild reverses it. Do not read them at face value in either window. Who buys the rebuild
  bills matters: RRP-funded MMFs are liquidity-neutral, other buyers drain reserves (Conks, Jun 2023).
- **X-date front-running:** a bill bid below RRP just before the X-date is positioning, not a collateral shortage. A
  true shortage shows the repo complex breaking below the bottom of the target range (Conks, Apr 2023).
- **Stablecoins and ABCP:** stablecoin reserves add bill demand, while ABCP at about 12bp over AA CP competes with
  bills and repo for MMF cash (FT Alphaville, Aug 2026; Conks, Mar 2026).

## Output
Return a bill-and-money-market table with one row per tenor (1m, 2m, 3m, 4m, 6m, 1y) and these columns:
- date, tenor, maturity date, basis (360 or 365);
- bill price, discount rate (if quoted), money-market simple yield, ACT/365 yield;
- matched OIS (type and tenor), `bill_ois_bp` with sign stated;
- 1y z-score of bill-OIS, regime label (rich / neutral / cheap);
- net bill supply over the last 3 months ($bn), TGA gap and business days since resolution (if in the debt-limit window);
- MMF AUM growth bucket and the bill-demand estimate (range, not a point);
- data gaps or flagged inputs.

Then a short signal block: which threshold fired, the confirmation checks above, and what would invalidate it.
If the signal becomes a trade, hand off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) with the
sign and quote convention spelled out for each leg. Run the risks through [rv-devils-advocate](../rv-devils-advocate/SKILL.md)
before sizing.

## Scripts
- [`scripts/bill_yields.py`](scripts/bill_yields.py): discount-to-price and simple/ACT365 yields, bill-OIS bp, net bill
  supply identity and TGA days-to-close lookup. CLI reads a CSV with `date, settle_date, maturity_date, price_px,
  [ois_pct]`. `python -I scripts/bill_yields.py --help`. `--selftest` checks the conversions against hand-computed
  values and the BofA financing waterfall.

## Related skills
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo rates, specials, triparty and GCF spreads that bills compete with.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): QT, RMOs, reserve ampleness and the RRP and TGA balance-sheet drivers.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): SR1-ZQ, strips and flies that express SOFR-FF views.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): the Fed path that drives tenor preference in bills.
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): compounded SOFR and fixing mechanics behind OIS.
- [fi-curve-construction](../fi-curve-construction/SKILL.md): OIS discount factors used for matched-tenor OIS.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts and bill conventions by market.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap spreads and ASW, where bill supply shows up in the swap spread.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): coupon auctions, buybacks and issuance calendars.
- [xccy-basis](../xccy-basis/SKILL.md): cross-currency basis, where bill supply and MMF demand feed the basis.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used in Inputs.
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): fiscal supply and term premium.
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): tenor and index basis, including SOFR-FF.

## References
- BofA Global Research - US Rates Watch: Funding & debt limit: history lessons (Mark Cabana, Katie Craig, 27 Jun 2025): debt-limit analog study, sign conventions, SOFR-FF trade.
- BofA Global Research - US Rates Viewpoint: Lower UST WAM => backdoor easing (Meghan Swiber, Mark Cabana, Katie Craig, 2 Jul 2025): bill-share tolerance, financing waterfall, TGA rebuild.
- BofA Global Research - US Rates Watch: Bill demand gap: Fed help likely needed (Mark Cabana, Katie Craig, Meghan Swiber, 22 Oct 2025): MMF demand model, holder breakdown, Fed bill-buying channels.
- BofA Global Research - US Rates Watch: Bills: policy & supply uncertainty = cheaper (Mark Cabana, Katie Craig, 1 Oct 2026): bill-OIS by tenor, tenor preference under Fed uncertainty.
- BofA Global Research - US Rates Watch: MMF portfolio update: long WAMs may challenge bill supply absorption (Katie Craig, Mark Cabana, 29 Jul 2025): WAM and WLA capacity, AUM vs yield table.
- BofA Global Research - US Rates Watch: Funding notes: bill tracking & repo (Mark Cabana, Katie Craig, 8 Aug 2025): bill-OIS by tenor, RRP exit threshold, RRP regression.
- BofA Global Research - US Rates Viewpoint: Debt limit FAQ: spring 2025 update (Mark Cabana, Katie Craig, Ralph Axel, 12 May 2025): X-date signals and the bill kink.
- BofA Global Research - US Rates Alpha: Short July SOFR/FF: debt limit => bills (Mark Cabana, Katie Craig, 30 Jun 2025): TGA rebuild speed tables.
- Barclays Research - Global Rates Weekly: The urgency question (A. Pradhan, R. Khanna, S. Kadota et al., 2 Oct 2026): cumulative issuance, MMF demand, Oct 2026 bill-OIS levels.
- Barclays FICC Research - US short interest rate primer (Joseph Abate, Jan 2025): bill-OIS history, supply-flow relationship, debt-limit mechanics.
- Citi Research - US Rates Weekly: Can Secretary Bessent and Chair Warsh save the curve? (Jason Williams et al., 21 Aug 2026): bill-share path, 2027 debt limit, private bills minus reserves.
- Citi Research - Short-End Notes: SOFR/FF to go negative in Q3/Q4 (Alejandra Vazquez Plata, Jason Williams, 13 Jun 2025): SOFR-FF path model from bills and reserves, X-date kink.
- Citi Research - Short-End Notes: SOFR/FF spiking into quarter-end (Vazquez Plata, Williams, 27 Jun 2025): weekly bills and reserves betas, cash-flow calendar.
- Citi Research - US Rates Weekly: The rocky road to a steeper curve (Jabaz Mathai et al., 18 Jan 2019): bill supply vs Treasury-OIS screen, sources and uses.
- Citi Research - US Rates Weekly: Time for moderation (Mathai, Williams et al., 17 Feb 2023): bills-minus-reserves SOFR-FF heuristic.
- Citi Research - US Rates Weekly: Going nuclear (on the curve) (Mathai et al., 3 Feb 2017): CMB mechanics, 12m bill-OIS seasonality.
- Citi Sales & Trading - STIRT Weekly: Beam me up, Scotty (21 Aug 2026): buybacks feed bill supply; AUD BBSW-OIS; NZD settlement cash. Sales and trading, not research.
- J.P. Morgan - Global Rates Strategy: Cross currency basis 2H25 Outlook (Francis Diamond et al., 5 Jun 2025): JGB$ASW decomposition, TGA and RRP transmission.
- Citi Research - US Rates Weekly: Pension plan for 20s? (Jason Williams et al., 9 Oct 2026): 1y swap spreads should use off-the-run 2y notes, not bills; debt-limit and 1y swap-spread context.
- Fleckenstein and Longstaff - Treasury Richness (Journal of Finance, accepted manuscript, 2023): 2a-7 eligibility premia.
- Darbyshire - Coding Interest Rates (rateslib design book, undated in the extracted text): bill discount, simple and YTM conversions.
- Conks (Monetary Mechanics, Substack) - Plumbing Notes: The Transitory Pause (12 Jun 2023): MMF bill-vs-repo switching condition, TGA accounting.
- Conks (Monetary Mechanics, Substack) - Plumbing Notes: Money Market Update (19 May 2025 and 2 Jun 2025): MMF shift from RRP to repo under the limit; bill flood after resolution.
- Financial Times - US Treasury to boost long-term bond purchases in bid to steady market (19 Aug 2026): buyback reaction, bills cheapen.
- Financial Times Alphaville - How money-market funds are providing stock market rocket fuel (Toby Nangle, 21 Aug 2026): ABCP vs AA CP spread.
- BofA Global Research - Japan Rates Basics (Tomonobu Yamashita, Shusuke Yamada, 24 Apr 2023): JPY T-bill structure and foreign ownership.
- Salomon Brothers - Understanding the Yield Curve, Part 3 (Antti Ilmanen, Jul 1995) (partial read): bill term premium and the 1m to 1y return ladder.
- SEC Rule 2a-7 under the Investment Company Act of 1940 (external): MMF WAM and maturity limits.
- J.P. Morgan - Japan Fixed Income Markets Weekly: Non-Stop Dynamics (Hiroki Yamamoto, Takafumi Yamawaki, 21 Feb 2025): 3m T-bill ASW regression, MRF behaviour.
- J.P. Morgan - US Fixed Income Strategy: Bills, Bonds, and basis...oh my (Joshua Younger et al., 7 Feb 2020) and A dollar funding market riddle (26 Feb 2020): bill free float, negative net supply framework.
- Citi Research - Macro Think Tank: Top of Mind (21 Aug 2026): buybacks funded by bills, size step-up.
- CME Group - Short-Term Interest Rate (STIR) futures Inter-Commodity Spreads on Globex (Apr 2024): SOFR vs T-bill futures spread mechanics.
- Conks (Monetary Mechanics, Substack) - The Money Market Blindspot: Part I (23 Jan 2025) and Part II (12 Feb 2025); Collateral Damage (18 Apr 2023); Plumbing Notes: Nothing Ever Happens (1 Mar 2026): debt-limit sequencing, mirage, SOFR-FF sign, X-date front-running.
- Wooldridge - Introductory Econometrics (2nd ed.): 6m-3m bill spread cointegration and Engle-Granger critical values (partial read).
- Tsay - Analysis of Financial Time Series (3rd ed., Wiley, 2010): 3m/6m bill error-correction model (partial read).
- Citi Research - US Rates Weekly: OAT of the blue (Jason Williams et al., 2 Oct 2026): T-bill swap spread z-scores (1y window) and the 2027 bill outlook.
- Citi Research - FX Basis Quarterly: Paying the basis (again) into 2025 (Jason Williams, Tomohisa Fujiki, Andrea Appeddu, 13 Dec 2024): RRP level model and MMF absorption of bills.
- BofA Global Research - US Rates Viewpoint: UST supply & demand in '25 (Meghan Swiber, 26 Nov 2024): 22.5% bill-share tolerance.
- BofA Global Research - US Rates Watch: X-date shift: now late August, risks earlier (Katie Craig, Mark Cabana, 7 Feb 2025): X-date method, extraordinary-measures inventory, financing identity.
