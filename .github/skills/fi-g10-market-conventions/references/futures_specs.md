# STIR and bond futures: contract conventions

Detail behind `SKILL.md`. Specs change: confirm against `fut_static` rows or the exchange rulebook, and treat every table as
dated. Tags: **[UNVERIFIED]** = not confirmed by a primary document; **[CONFLICT]** = sources disagree.

## 1. Quoting rules common to all rate futures
- Price = 100 minus the rate in percent ("upside down"). A futures price rally = lower implied rate. A spread of two futures prices
  has the opposite sign to the spread of the rates (SOFR-FF: a realised +10bp SOFR minus EFFR is -10bp in 100-minus-rate terms, so a
  "futures sell-off" in SR1:FF means the basis is widening).
- BPV = notional x 0.0001 x accrual fraction. 3M contracts: 1,000,000 x 0.0001 x 90/360 = 25 per bp; 1M SOFR: 5,000,000 x 0.0001 x 30/360 = 41.67.
- P&L = contracts x bp change x BPV. "100 minus price" is the implied forward rate for a forward-starting deposit/period, not the
  expected fixing, and it needs a convexity adjustment before comparison with a FRA or swap forward (swap forward sits below the
  futures-implied rate). See [stir-convexity-adjustment](../../stir-convexity-adjustment/SKILL.md).
- Month codes: F Jan, G Feb, H Mar, J Apr, K May, M Jun, N Jul, Q Aug, U Sep, V Oct, X Nov, Z Dec; year = last digit.
- **Month-code semantics differ.** 3M contracts are named after the month in which the reference period STARTS. Legacy IBOR futures
  expire at that start (Eurodollar Mar-2023 expires 2 BD before the third Wednesday of Mar 2023 and fixes 3M LIBOR from that date;
  Euribor June covers June to September). RFR futures settle at the END of the period (SR3Z22 references the quarter from the Dec-2022
  IMM, 21-Dec-22, to the Mar-2023 IMM, 15-Mar-23, last trade 14-Mar-23). A mix-up shifts dates by one quarter. 1M SOFR is named after its
  delivery month. (One source shows a V-month 3M SOFR example; 3M SOFR lists only H, M, U, Z, so it is not reproduced here.)
- Strip names: whites = first 4 quarterlies, then reds, greens, blues, golds (then purples, oranges, pinks, silvers, coppers). Packs =
  4 consecutive quarterlies; bundles = 2-5y in multiples of 4. Both are quoted as the arithmetic average of the constituents, minimum tick 0.25bp.
- Yield-quoted exceptions: ASX bond futures price = 100 - yield but are cash-settled on a synthetic bond value so tick value varies
  with yield; AUD and NZ bank-bill futures are quoted in yield and valued via the bill price; Nasdaq Swedish bond futures quote the
  effective yield directly (not 100 - yield).
- An exchange settlement price and a near-close snap can differ by a fraction of a bp: keep `settle` and `close` distinct.
- Options on STIR futures are American, premium-margined at CME (early exercise never optimal when daily margined, so value as European);
  a call on price is a put on the rate.

## 2. RFR STIR futures (as of Nov 2026)

| Contract | Size and BPV | Settles on | Tick | Last trade | Listed |
|---|---|---|---|---|---|
| CME 3M SOFR (SR3) | USD 2,500 x index, 25 per bp | 100 - compounded SOFR (ISDA, A/360) from the third Wednesday of the contract month up to, excluding, the third Wednesday three months later. Cash, next BD after the last SOFR publishes | 0.25bp in the nearest contracts, 0.5bp otherwise (H&S: 0.25bp within 4 months of last trade) | business day before the third Wednesday ending the period | 39 quarterlies (2022); roll between the 2nd and 3rd listed contract |
| CME 1M SOFR (SR1) | USD 5mm, 41.67 per bp | 100 - arithmetic average of SOFR over calendar days of the month (weekends and holidays carry the prior BD rate, Friday counts 3 times), rounded 0.1bp | 0.25bp in delivery month, 0.5bp before | last BD of the month | 13 months |
| CME Fed Funds (ZQ) | USD 5mm, 41.67 per bp | 100 - monthly arithmetic average of EFFR, A/360 | 0.25bp (10.42 on the front month) | last BD of month | 36 months |
| ICE 3M SONIA (SO3) | GBP 2,500 x index, 25 per bp | 100 - compounded SONIA, A/365F, IMM to IMM | 0.25bp front (6.25), 0.5bp others (12.50) | 8:30 on the IMM-end day (GBP stops 30 minutes before the last fixing publishes) | 25 quarterlies (2018) |
| Eurex 3M ESTR (FST3) | EUR 2,500 x index | compounded ESTR, final settlement price set 09:00 CET | | | |
| Eurex/ICE 3M Euribor (FEU3) | EUR 2,500 x index | 100 - 3M Euribor (term fixing, 11:00 CET) | 0.25bp (6.25) | 2 BD before the third Wednesday, 11:00 CET | still the unsecured IBOR future |
| MX 3M CORRA (CRA) | CAD 2,500 x index, 25 per bp | compounded CORRA over IMM quarter, y = 365 | 0.25bp front (6.25), 0.5bp later (12.50) | business day before third Wednesday | 12 quarterlies; BAX gone |
| OSE 3M TONA | about JPY 2,500 per bp | 100 - compounded TONA, IMM-dated | | | launched 29-May-2023; TFX also lists TONA futures. TFX Euroyen suspended 28-Jun-2024 |
| Eurex 3M SARON (FSR3) | CHF 2,500 x index | compounded SARON | 0.5bp (12.50) | exchange day before the third Wednesday, 18:00 CET | 12 quarterlies; ICE also lists |
| ICE 3M SWESTR (SW3), 3M STIBOR (STI) | STIBOR SEK 25,000 x index; tick 0.25bp (62.50) | SWESTR compounded in arrears; STIBOR 100 - 3M STIBOR | | 2 BD before the third Wednesday, 11:00 CET (STIBOR) | 16 quarterlies (STIBOR). Nasdaq RIBA tracks the Riksbank policy rate, cash-settled daily |
| ICE 3M NOWA and NIBOR | launched 7-Apr-2026; ICE dated NOWA future 100 - rate | | | | **[UNVERIFIED details]** |
| ASX 90-day bank bill (IR) | AUD 1mm | 100 - 3M BBSW, cash-settled since Sep 2020 (physical until Jun 2020) | 0.01, about 24 per tick, variable | business day before settlement day (2nd Friday), 08:29 | 20 quarterlies + 2 serial |
| ASX 30-day interbank cash (IB) | AUD 3mm | monthly average of the RBA cash rate | 0.005, about 12.33 | | |
| ASX NZ 90-day bank bill (BB) | NZD 1mm | 100 - 3M BKBM (FRA settlement rate, 2dp), cash | 0.01, about 24 | first Wednesday after the 9th, 12:00 | |

Formulas (Fed FEDS 2019-014, CME, FactSet 2023):
- 3M: `R = [ product_i (1 + d_i R_i / (Y x 100)) - 1 ] x (Y / N) x 100`, price = 100 - R. Y = 360 (SOFR, ESTR, SARON), 365 (SONIA, CORRA);
  N = calendar days in the period; d_i = calendar days rate i applies. Rounded to 0.01bp.
- A revision of the last day's SOFR cannot enter settlement; revisions to earlier days do.
- 1M: `R = (1/N) sum_{calendar days} R_t` (arithmetic average).
- SR3 is the forward rate of its reference period because it compounds; SR1 is a simple average, so not exactly the forward. For
  constant SOFR 5% the averaging-versus-compounding gap is about 3bp over a quarter, 0 at SOFR = 0; for SR1 the adjustment is about 0.1bp
  at 2021-22 rates and of order 1bp near 5%. Adjust when it exceeds the SR1 bid-ask.
- Weight overlap days when spreading monthly against quarterly contracts. 1M-arithmetic and 3M-compounded contracts "do not mix well" in
  a single bootstrap (oscillations): use one family per curve segment.
- Inter-commodity spreads (CME): SR1:SR3 ratio (3+3):10 (6 x 41.67 = 250.02 against 10 x 25 = 250, almost BPV-neutral), FF:ED, SR1:FF 1:1,
  SR3:ED 1:1, FF:SR3 (3+3):10. The CME price convention differs from the true weighted spread by under 1bp, which matters at low rates.
  Last trading day is the earliest leg's.
- Legacy Eurodollar converts to SOFR futures at a fixed 26.161bp; after Jun-2023 the SR1:FF and SR3:FF spreads carry the secured-unsecured
  basis (SR1:FF is the cleanest instrument).
- Term SOFR (CME): 1M/3M/6M/12M, published 5am CT, built from the prior day's first 13 SR1 and first 5 SR3 (VWAP over 14 half-hour
  windows 7am-2pm CT) in a jump-at-FOMC model. Criticised for no diffusion, ignoring non-policy spikes and a lambda about 0.33 that may
  add about 0.5bp to 6M. Secondary-market trading is restricted, so treat as a loan reference, not a swap reference.

**Stub and strip formulas.** Front contract inside its period: split into known and unknown fixings (see `rfr_indices_and_transition.md`).
Strip gross factor `S = (1 + R_unknown D_unknown/360) x product_j (1 + R_j D_j/360)`; annualise from `S = (1 + S_ann 365/360)^N (1 + S_ann F/360)`
with N whole years, F remaining days. A front SR3 inside its period has decaying vol; do not treat it like a normal forward.

**Swap-to-futures bridge** (CME 2025): 3M SOFR futures strip to par OIS: `DF_i = 1 / (1 + R_i d_i/360)`, `CDF_i = product DF`,
`fixed = sum CDF_i R_i d_i/360 x 360 / sum CDF_i d_i` (use the fixed leg's own day counts if different). Worked in `scripts/conventions.py`.
SOFR decompounding: SFRH5 at 95.705 implies 4.295% for 3 months, about 4.2725% as a constant overnight rate.

## 3. Legacy IBOR STIR specifications (dated; Aikin 2012, Henrard 2012)

| Contract | Size | Months | Tick | Last trade | Delivery |
|---|---|---|---|---|---|
| Eurodollar (CME) | USD 1mm | 40 (quarterly + 4 serial) | 0.005 = 12.50 (front 0.0025) | 2nd BD before third Wednesday | LTD + 2 |
| Euribor (Liffe/Eurex) | EUR 1mm | 24 | 0.005 = 12.50 | 10:00, 2 BD before third Wednesday | LTD + 1 |
| Short Sterling | GBP 500k | 22 | 0.01 = 12.50 | 11:00 third Wednesday (same-day fixing) | LTD + 1 |
| Euroswiss | CHF 1mm | 8 quarterlies | 0.01 = 25 | 11:00, 2 BD before third Wednesday | LTD + 1 |

Others in the legacy list: Euroyen (JPY 100mm, BPV 2,500 per bp), BAX (Montreal, CAD 1mm, converted to CRA in 2024), SFE 90-day bank bills (AUD 1mm to 5y),
NZ 90-day bills, STIBOR (OMX, SEK 1mm). Legacy overnight-index futures: 1M EONIA (EUR 3mm, 0.00005 = EUR 12.50, expiry last day of the ECB maintenance
period), 3M EONIA OIS (EUR 1mm), CME 3M Fed Funds OIS (USD 1mm, 100 minus realised compounded EFFR, backward-looking, tick USD 6.25), CME 30-day Fed Funds
(USD 5mm, 100 minus the monthly average, 0.000025 = USD 10.42).

Fixing/settlement timing for IBOR futures: fixing on the last trading date at the spot lag before the third Wednesday (Monday for T+2
currencies, the Wednesday for same-day GBP/CAD/AUD-type markets); EDSP = 100 - 3M fixing (11:00 London). Tick value check: 0.01 x 1,000,000 x 90/360 = 25.
IRS futures (CBOT-style): buying = receiving fixed; P = ((EDSP - 100)/100) N; illiquid.

Futures-versus-cash basis in the final month is usually within +-10bp, converging in the last week; hedge with an expiry within two weeks
of the exposure. December contracts carry a structural year-end (turn) cheapening. Futures hedges whose averaging window spans a policy meeting
carry meeting-date basis risk. FF futures (backward, monthly) become less volatile through the delivery month as averaging locks in.

## 4. Bond futures: US Treasury

| Contract | Face | Deliverable remaining maturity (from first day of delivery month) | Original maturity | Tick |
|---|---|---|---|---|
| TU (2y) | USD 200k | 1y9m - 2y | at most 5y3m | 1/8 of 1/32 = 7.8125 |
| 3-year (Z3N) | USD 200k | 2y9m - 3y | at most 7y | 1/8 of 32nd = 7.8125 |
| FV (5y) | USD 100k | 4y2m - 5y3m | at most 5y3m (so only original 5y notes) | 1/4 of 32nd = 7.8125 |
| TY (10y) | USD 100k | 6.5y - 8y (CME 2022 proposal: 6.5y - 7.75y) | none | 1/2 of 32nd = 15.625 |
| UXY/TN (Ultra 10y) | USD 100k | 9y5m - 10y | at most 10y | 1/2 of 32nd = 15.625 |
| US/ZB (bond) | USD 100k | 15y - under 25y | none | 1/32 = 31.25 |
| WN/UB (Ultra bond) | USD 100k | 25y - 30y | none | 1/32 = 31.25 |

(BofA, Treasury futures primer, Jul 2025; CME Understanding Treasury Futures, 2017; CME contract pages 2026.) Cash tick sizes on the
interdealer screen: 2y, 3y, 5y 1/128 of a point (78.125 per 1mm), 7y, 10y, 30y 1/64 (156.25 per 1mm).

- **Price quoting.** 32nds: 97-18 = 97.5625; 1/32 per USD 1mm = 312.50. Cash "+" = 1/64 and a trailing third digit = eighths of a 32nd
  (97-182 = 97.5703125, 97-186 = 97.5859375). On futures the third digit is the truncated decimal of a 32nd, so cash 97-18+ = futures 97-185
  and cash 97-186 = futures 97-187; for TU's 1/8 tick the digits are 1, 2, 3, 5, 6, 7, 8 (.125 ... .875). Some CBOT option quotes use rounded quarters
  of a 32nd: option 99.245 = bond 99-24+.
- **Last trade / delivery.** Last trade: last BD of the delivery month for TU/FV (3-year too); 7 BD before the last BD for the others (12:01 CT
  **[verify against rulebook]**). Last delivery: 3rd BD after last trade for TU/FV/3-year (so into the next month), last BD of the month
  for the others. Delivery is a three-day process (intention, notice, delivery) so delivery is a T+2 process for carry. Longs are assigned
  oldest first. After the last trade date the futures price is fixed while cash keeps trading; switch from a CF-weighted to a face-matched
  hedge (or carry an unhedged (1 - CF) x face).
- **Conversion factor.** Price of 1 par of the bond at a 6% yield (CBOT adopted 6% in 2000, replacing 8%; pre-2000 examples are not current).
  Remaining life from the first day of the delivery month is rounded DOWN to whole quarters for TY, Ultra 10y, US and Ultra bond (6y 8m 30d = 6y 6m)
  but to whole MONTHS for TU, 3-year and FV (Burghardt et al. 2005, CF appendix). Constant per bond per contract month. Coupon above 6% gives CF above 1, falling in later months; below 6% gives CF below 1, rising.
  Formula (c in decimals, n whole years, z leftover months: 0/3/6/9 for quarter rounding, 0..11 for month rounding; v = z if z < 7, else 3 for
  quarter rounding and z - 6 for month rounding):
  `a = 1/1.03^(v/6)`, `b = (c/2)(6 - v)/6`, `c' = 1/1.03^(2n)` if z < 7 else `1/1.03^(2n+1)`, `d = (c/0.06)(1 - c')`, `CF = a (c/2 + c' + d) - b`.
  Check values: 8-7/8s of 8/15/17 on 1-Jun-2001 (16y 2m 14d, rounded to 16y0m): 1.2931; 7.5s of 11/15/16 (15y 5.5m, z=3): 1.1484; 2.875s of 5/15/28 for TYU1: 0.8338.
  Implemented as `ust_conversion_factor` in `scripts/conventions.py` (`monthly=True` for TU, 3-year, FV).
- **Price relations.** Gross basis `GB = P_clean - F x CF`; net basis = GB minus carry (forward price minus F x CF); invoice `= F x CF + AI_delivery`;
  IRR (no coupon) `= (Invoice / Purchase - 1) x 360/n`, both dirty; CTD = highest IRR = lowest net basis. Futures DV01 = CTD DV01 / CF.
  Delivery-date convention: price to the last delivery day when carry is positive, to the first day when negative.
  The EFP bid/offer is quoted on the basis; the futures leg is set near market and the cash invoice is the residual: Bond price = Basis + CF x F.
- **Checks.** TYU1 at 131-17+ (14-May-2021, repo 0.015%): CTD 2.875s of 5/15/28, CF 0.8338, clean 110-24 3/4, GB = 110.7734 - 0.8338 x 131.5469 = 1.0896 = 34.9 ticks, carry 33.8, NB 1.1 ticks.
  Other bond: 1.125s of 2/15/31, CF 0.6577, NB 274.4 (Tuckman and Serrat 2022, Table 11.8).
- **IRR convention risk.** Conventions vary on the settlement date, the delivery date and the day count. Dec-2017 TY: F 125.265625 (125-08.5),
  CTD 2.375s Aug-2024, clean 101.2266, CF 0.8072, AI at settlement 0.367867, AI at delivery 0.877717, 79 days: IRR = 1.7837%; the CME
  table showed 1.42%, apparently using year fractions from the last delivery date. Verify vendor and exchange IRR conventions before use (QFSE, Jul 2022).
  A 365-day count raises the IRR.

## 5. Bond futures: other markets (spec as of Nov 2026 unless dated)

| Market, contract | Size and notional coupon | Deliverable | Delivery and last trade | Quote and tick |
|---|---|---|---|---|
| Eurex Schatz / Bobl / Bund / Buxl | EUR 100k, 6% (Buxl 4%) | 1.75-2.25y / 4.5-5.5y / 8.5-10.5y / 24-35y remaining | **single delivery day = 10th calendar day** of the contract month; last trade 2 exchange days before, 12:30 CET; short names the bond on the last trading day | percent of par, 0.01 (EUR 10) |
| Eurex BTP short/mid/long, OAT, Bono, Euro-EU | EUR 100k, 6% | BTP 2-3.25y, 4.5-6y, 8.5-11y; OAT 4.5-5.5y, 8.5-10.5y; Bono 8.5-10.5y; EU 8-12y | same | 0.01 |
| Eurex CONF (Swiss Confederation) | CHF 100k, **1%** notional coupon (one summary said 6%; two Eurex pages show 1%) | 8-13y | 10th calendar day; last trade 2 exchange days before 12:30 CET | 0.01 (CHF 10) |
| ICE Long Gilt | GBP 100k, 4% notional (7% in 2004) | 8y9m - 13y | **any business day of the delivery month (seller's choice)**; first notice 2 BD before the month; last trade 2 BD before the last BD, 11:00 | 0.01 (GBP 10). EDSP = 11:00 London price through the price-factor system. Ultra Long Gilt 28-37y |
| OSE 10y JGB | JPY 100mm, 6% | at least 7y, under 11y | **20th of the contract month**; last trade 5 BD before (JPX mini page says the 6th, **[CONFLICT]**) | tick JPY 0.01 per 100 = JPY 10,000. Mini-10y is 1/10 size, cash-settled |
| MX CGB / CGF / CGZ / LGB | CAD 100k, 6% | CGB 8-10.5y (8-10.25y in 2004); CGF 4.5-5.5y, issued at 5y auctions, min CAD 3bn outstanding | any business day of the delivery month; last trade 7th BD before the last BD, 13:00 | 0.01 (CAD 10) |
| ASX 3y (YT), 10y (XT), also 5y (2% coupon, n=10) and 20y | AUD 100k, 6% | **cash settled** against the mean of mid prices of a basket of CGBs, sampled 9:00, 9:45, 10:30, 11:15 Sydney | expiry 15th of the month (or next BD), 12:00 noon; settlement next BD | price = 100 - yield, tick 0.005 (3y reset from 0.01), worth about AUD 15 (3y) or 45 (10y), variable |
| Nasdaq Stockholm SGB2Y/5Y/10Y | SEK 1mm, 1% annual coupon (cut from 6% in 2021) | **a single designated deliverable bond** (no CTD) | expiration settlement on the third Wednesday of Mar/Jun/Sep/Dec; fix 11:00 CET, 4 bank days before | price expressed as an effective yield, 30E/360, tick 0.001; daily cash settlement plus delivery |
| Norway | no NGB bond future found | | | |

2004 snapshot for history (Burghardt et al. 2005, Exh 9.4): notional coupons 6% except Gilt 7% and Korea 8%; Eurex Bund 8.5-10.5y, Bobl 4.5-5.5y,
Schatz 1.75-2.25y, delivery on the 10th, LTD 2 exchange days before; JGB 7-11y, LTD 7th BD before delivery on the 20th; CGB 8-10.25y;
Long Gilt 8.75-13y, LTD 2nd BD before the last BD; SFE 3y/10y cash-settled against the mean of 10 randomly selected dealers.

**Delivery windows (Duering 2021, Burghardt 2005).** US, UK, Canada: seller chooses any business day of the delivery month (timing options);
Eurex and JPX: single delivery day. This decides how much optionality sits in the basis. Exchanges sometimes move a new contract to a different
notional coupon when basket yields drift far from the old one (Gilt 7% to 4%, Swedish 6% to 1%): the CF published at listing is determinative,
exchange formulas only predict it. Gilt ex-dividend: a CTD going ex-dividend during the delivery month cannot be delivered then, so futures jump to the next CTD.
JGB futures notional is about 10x a US contract.

**ASX contract value** (price = 100 - yield, i = yield/200, v = 1/(1+i), n = 20 for 10y, 6 for 3y, c = 6):
`Value = 1000 x [ (c/2)(1 - v^n)/i + 100 v^n ]`, no accrued because the half-year count is exact. 10y at 95.00 (5% yield): AUD 107,794.58
(Burghardt prints 107,795.58, a typo: its own differences +81.67 and -81.59 only reconcile with ...794.58); 95.01 gives 107,876.25; 94.99 gives
107,712.99; average DV01 per 1bp = 81.63. Average DV01 by yield level: 4% 89.65, 5% 81.63, 6% 74.39, 7% 67.85, 8% 61.93. 3y at 95.505 (4.495%): AUD 104,180.10 (ASX pricing guide).

**Futures-implied yield and asset swaps.**
- Futures-implied yield: replace the bond price by F x CF of the CTD in the price-yield formula, settling on the last delivery date.
- Bobl (and other physical contracts) futures ASW: spread in bp between a swap starting on the delivery date and ending at CTD maturity and the future-implied
  forward yield of the CTD; positive = future rich versus swap.
- AUD: EFP = spot-starting generic swap (3y/10y) minus futures-implied yield; start and end dates do not match, so compute carry and roll separately for the swap and bond legs.
  Interbank swap quotes reference the first futures expiry until 2 BD before it, then the second.
- JGB futures ASW = CTD implied forward yield minus forward-starting matched swap yield (the example inferred -18bp from 0.150 versus 0.330).
