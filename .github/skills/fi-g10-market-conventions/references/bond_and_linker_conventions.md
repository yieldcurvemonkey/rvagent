# Day counts, money-market and bond quoting, yields, FRNs, linkers

Detail behind `SKILL.md`. Per-market bond parameters are in `market_matrix.md`; futures are in `futures_specs.md`.

## 1. Day-count conventions
DCF = days in period / days in year. Interest = notional x DCF x per-annum rate.

| Convention | Rule | Typical use |
|---|---|---|
| ACT/360 | actual days / 360 | money markets, USD/EUR/CHF/SEK RFRs and OIS, Euribor, SOFR repo |
| ACT/365F (fixed) | actual days / 365, no leap adjustment | GBP, JPY, CAD, AUD, NZD swap and index legs; Canadian bond accrued; NOWA is plain ACT/365 |
| 30/360 (bond basis, 30U) | `D = (D2 - D1) + 30 (M2 - M1) + 360 (Y2 - Y1)`; a start on the 31st becomes the 30th; an end on the 31st becomes the 30th only if the start day is 30 or 31 | USD legacy fixed legs, corporates |
| 30E/360 (Eurobond basis) | both dates on the 31st become the 30th, unconditionally | EUR fixed swap legs (as 30/360), SEK and CHF bonds (NOK bonds and swap fixed legs are plain 30/360, Norges Bank/TP ICAP templates) |
| ACT/ACT ISDA | days in leap-year portion / 366 plus the rest / 365 | some swap legs |
| ACT/ACT ICMA (ISMA) | days / (days in the coupon period x coupon frequency) | UST, gilts, Bunds, OATs, BTPs accrued; frequency is itself an input |
| ACT/ACT AFB | 365 or 366 depending on whether 29-Feb falls in the period | |
| ACT/365L | 366 if the next coupon falls in a leap year | sterling FRNs |
| NL/365 | actual days, 29-Feb removed | JGB accrued (some descriptions) |
| 1/1 | one per period | absolute-rate loans |

Worked checks: 1-Jun to 15-Aug is 75 actual days but 74 on 30/360. 1-Jun-16 to 1-Sep-16, 100mm at 10%: 1/1 gives 10,000,000.00; ACT/ACT ISDA 92/366 gives
2,513,661.20; 30/360 90/360 gives 2,500,000.00; ACT/365F 92/365 gives 2,520,547.95 (Darbyshire, PTIRD 2022, Ex 2.3). In Ex 2.1/2.2 a "5% absolute" 1/1 loan pays
5mm and a "10% p.a. 30/360" loan pays 2.5mm over the same three months: a headline rate means nothing without its day count, frequency and payment timing.
Sizing a slip: using ACT/365 where ACT/360 applies understates the accrual by factor 360/365, about rate x 1.4%: about 5.5bp on a 4% rate.

The CFTC swap-data day-count codes (Technical Specification Parts 43/45, v3.0 and v3.1) map as: A001 30/360 US (bond basis), A002 30/365, A003 30/Actual, A004 ACT/360,
A005 ACT/365 Fixed, A006 ACT/ACT ICMA, A007 30E/360 ISDA, A008 ACT/ACT ISDA, A009 ACT/365L, A010 ACT/ACT AFB, A011 30E/360 Eurobond, A014 NL365, A015 ACT/ACT ICMA ultimo,
A016 30E+/360, A017 ACT/364, A018 BUS/252, A019 NL360, A020 1/1. Tape units: decimals unless spread notation 4 (integer bp); all-9s = unknown; times UTC.
Map vendor day-count labels to these codes explicitly and test the 31st-day handling against the formulas above rather than trusting the label.

Where used (Duering 2021, Ch.13; Tuckman and Serrat 2022, Ch.1): money markets, including Japan, ACT/360; the old Commonwealth (UK, Australia, NZ, South Africa) ACT/365;
government bonds ACT/ACT or 30/360; swap markets ACT/ACT, ACT/365 or 30/360; corporates 30/360. Instruments longer than 1y that straddle a leap year are split into a final
piece of exactly 1y plus a front stub, each with its own 365/366 denominator.

## 2. Money-market pricing, compounding and annualisation
- Simple: `P = 100 / (1 + r DCF)`, `r = (100/P - 1)/DCF`.
- Discount (US bills): `P = 100 - r DCF`, `r = (100 - P)/DCF`. Bill discount rate is not the simple rate and not the bond yield:
  `r_simple = (1/(1 - r_disc t) - 1)/t`. Example: 5% discount over 91 days is 5.0636% simple (ACT/360). To compare a bill with a bond treat it as a zero-coupon bond:
  a US bill maturing 26-Sep-23, settling 7-Sep-23 at 99.75 has a YTM of 4.90740754% (Darbyshire, Coding Interest Rates, c.2024).
- Effective annual: `(1 + r/n)^n - 1`; continuous `e^r - 1`. 12% monthly compounded = 12.68% effective; the same 100 to 102 over a year is 2% annual, 1.9901% semi-annual,
  1.9819% monthly (Tuckman and Serrat 2022, Ch.2). More frequent compounding lowers the quoted rate; annualised rates are for comparison, never for payments.
  10% p.a.: annual 10%, semi-annual 10.25%, quarterly 10.381%.
- An annualised rate is valid only for its stated period: 2.1% for 6M and 2.5% for 1Y do not contradict each other. At constant rate, higher payment frequency at the same
  p.a. rate is worth more (reinvestment); this reverses when rates are negative.
- Continuously compounded rate: `exp(DCF x CC) = 1 + DCF x r`. Useful only for formula manipulation and Greeks.
- Payment frequency example (10%, GBP 10mm, ACT/365F, 1-Jan-16 to 1-Jan-17, a leap year): annual 1,002,739.73; semi-annual 498,630.14 + 504,109.59; quarterly
  249,315.07, 249,315.07, 252,054.79, 252,054.79. Totals equal, flows differ with the day count.
- Mid swap rate from discount factors (single RFR curve): `R_mid = (v_0 - v_T) / sum_i d_i v_i`.
- Zero-coupon swap: single net payment at maturity, fixed leg as a cash amount or an IRR (needs frequency and exact versus rounded-year DCF). Always clarify.
- Equivalence for FX forwards (basis applied to the non-USD rate by convention): `F = S x (1 + i_p D/B_p) / (1 + i_b D/B_b)`; Aikin 2012: EURUSD spot 1.2960, 92 days, EUR 1.12%, USD 0.56%
  gives F = 1.2942 (-18.49 pips); with a -75bp basis on the EUR rate F = 1.2966 (+6 pips, matching the market). Negative basis = USD premium. Fed standing swap lines (BoC, BoE, BoJ, ECB, SNB)
  are priced OIS + 25bp, tenors 7 and 84 days.

## 3. Price quoting and accrued interest
- Dirty = clean + accrued; invoice = dirty x par. The accrual convention changes only the quoted price, never the full price. Flat prices are quoted because the full price jumps down on coupon dates.
  The par yield (clean = par) is not exactly the coupon, since accrued is linear while discounting is a power; the gap grows with coupon and in leap years. Minimum tick is usually 0.001% of par.
- Accrued `I = C x DCF(t_{i-1}, t_s)` on the bond day count. With a rounded coupon fixed in the prospectus accrue on the rounded coupon. Ex-dividend (UK) gives negative accrued
  `I = C x DCF(t_i, t_s)`; Japan has no negative accrued (no settlement in the ex-period); German 10y bonds often have a long first coupon (>1y) needing a fictitious-period split.
- Worked: UST 0.625s of 8/15/30 settling 17-May-2021: 91 days since the last coupon, 181 in the period, AI = 31.25 x 91/181 = 15.711 per 10,000 (0.15711 per 100); flat 91.78125, full 91.93836
  (Tuckman and Serrat 2022, Ch.1). Gilt, 5% semi, settle 15-Apr-2022 (period 1-Jan to 1-Jul): 104/181 x 2.5 = 1.43646409. Canadian government bond ACT/365F: 104/365 x 5 = 1.42465753.
  Ex-dividend example: the 8% Treasury 2015 coupon on Mon 7-Jun-99 went ex-div on Wed 26-May-99 (7 business days with 31-May a holiday); measure from the unadjusted coupon end.
- UST 32nds: 99-24 = 99.75; "+" = 1/64 so 99-24+ = 99.765625; a third digit gives eighths of a 32nd: 99-245 = 99 + 24/32 + 5/256 = 99.76953125, and 99-244 = 99-24+; there is no "minus".
- Cash price tick: 2y/3y/5y 1/128; 7y/10y/30y 1/64. UK bid/offer is 5 ticks or less to 7y, JGB benchmark bid/offer 1/2bp (2001 figures).
- ISINs: 12 characters = 2-letter country (XS for eurobonds) + 9-character national id + check digit (Luhn-type); Japanese ISINs cannot be built from series codes; taps may carry temporary
  ISINs later funged; validate check digits with a tested routine.

## 4. Yield conventions
| Method | Formula | Used by |
|---|---|---|
| Running yield | `C/P` | quick carry |
| Simple yield (JGB) | `[C + (100 - P)/t] / (P/100)`; t = days from settlement (inclusive) to maturity (exclusive) / 365, removing each 29-Feb; P clean | Japan. Weights a capital loss in 10y like one in 1y |
| Compound yield (IRR) | `P = sum CF_i / (1 + y)^DCF(t_s, t_i)` | most markets, root-search |
| Moosmuller | first period treated as money market: `P = [1/(1 + y DCF(t_s,t_1))] sum CF_i/(1+y)^DCF(t_1,t_i)` | Germany; street convention in the last coupon period |
| ISMA | annual compounding regardless of coupon frequency | EUR sovereigns, CHF, SEK |
| US Street | semi-annual compounding, compound discounting of the fractional period | US |
| US Treasury | simple interest on the fractional period | US Treasury |
| DMO | quasi-coupon-date compounding | UK |
| Bond-equivalent yield | `y_B = 2 (sqrt(1 + y) - 1)`, about y^2/4 below the annual compound yield | convert before comparing |
General bond price for irregular settlement: `P = v_1 (sum c_i v_2^(i-1) + c_n v_2^(n-2) v_3 + 100 v_2^(n-2) v_3)` with stub discount factors `v_1, v_3`; the textbook
`sum (C/f)/(1 + y/f)^k + 100/(1 + y/f)^n` holds only for regular bonds settling on a coupon date. Never compare yields across coupon frequencies without converting, never compare
yields across maturities as returns, and do not rank bonds by yield (on an upward curve high-coupon bonds have lower yields). Use spreads to a discount curve. Rich/cheap to a discount curve = market price minus PV
from benchmark discount factors (positive = rich); the bond forward-curve spread `s` solves `price = sum CF / prod (1 + (f_i + s)/2)` (negative = rich).

## 5. FRNs and overnight-linked notes
- Reset `C_i = R(t_i - 2) + mu` (lags up to 20 BD for some); implicit zero floor `C = max(0, R + mu)`; an FRN is at par on every reset date if the discount spread equals mu.
- Curve-based discount margin `mu' = mu - (P - 100) / sum_i DCF(t_{i-1}, t_i) Df(t_i)`, close to an asset-swap spread. The market-convention DM assumes future fixings equal the current one and is
  independent of curve shape, so comparing DMs across maturities is methodologically incorrect.
- Overnight-linked FRN: compounded rate over the observation window, margin added without compounding; European FRNs use a 5 BD lag; with lagged rates a lag l = 2 makes payment equal the OIS rate.
- US 2y FRN: coupon = latest 13-week bill high discount rate (reset weekly) + fixed spread (the high discount margin at the original auction).

## 6. Inflation-linked bonds and inflation swaps
- **Index ratio** `R_t = I_t / I_0` multiplies every cash flow. `I_0` is usually the reference index at first settlement (Sweden: most bonds share one `I_0`). The reference index interpolates linearly
  between the two nearest CPI prints at a fixed lag (minimum = publication delay plus about one month). Principal is usually floored at par for redemption.
- **Canadian-model reference value** (3-month lag): `RV(d) = CPI_{m-3} + ((d - 1)/ND_m) x (CPI_{m-2} - CPI_{m-3})`. For a July settlement the April and May prints are used.
  Quoted in real terms: nominal price `P = R_t x P_real`; invoice `V = N x R_t x (P_real + Accrued_real)`; accrual in real terms.
- **Per-market table** (BofA, global inflation-linked primer, Jul 2025; Duering 2021, Ch.23, Ch.39):

| Market | Index | Lag | Principal floor | Quoted price |
|---|---|---|---|---|
| US TIPS | CPI-U NSA | 3m standard, interpolated | floor | real |
| UK | RPI | standard 3m for post-2005 issues; two old 8-month-lag issues quoted adjusted | no floor | real per BofA 2025; Duering 2021 says UK quotes include inflation **[CONFLICT]** |
| France | OATei on euro HICPxT; OATi on French CPI ex-tobacco | standard | floor | real |
| Italy, Germany (DBRei; OBLei discontinued), Spain | euro HICPxT | standard | floor | real |
| Japan | CPI ex fresh food (NSA) | "modified standard": the 10th of the month takes the index from 3 months earlier; coefficient = reference index / reference index on the 10th of the issue month | floor on series from 2013 (principal and last coupon), none earlier | real (clean price) |
| Canada | CPI All Items | standard | no floor | real |
| Australia | CPI All | 6 months | floor, coupons also floored | adjusted price |
| Sweden | SWCPI | standard | floor | adjusted price |

  The standard lag is "between 2-3 months". HICPxT became the EGB convention because French swap liquidity sat there.
- **Zero-coupon inflation swap**: fixed leg `(1 + K)^T - 1`; inflation leg `I(end)/I(start) - 1`; single exchange at maturity; the "receiver" receives inflation, so say long/short inflation.
  ZC swaps generally have no deflation floor; YoY swaps typically do. ZC swap IRR (ACT/ACT ICMA) is not directly comparable to an ESTR leg (ACT/360).
- **Swap lag and interpolation**: US same 3m lag and interpolation as TIPS; EUR HICPxT and French CPI swaps 3m lag with no interpolation ("month-end roll", all of July references April);
  UK RPI/CPI swaps 2-month lag with no interpolation. This matters for linker-swap basis and aged-swap valuation. Whole-year quotes cannot be linearly interpolated because of seasonality.
- **Index choice**: US CPI has tended to outrun PCE; UK RPI persistently outstrips UK CPI. Never compare raw breakevens across linkers with different maturity months or settlement dates without a
  seasonality adjustment; check how the vendor treats the base CPI after rebasing.
- Generic daily interpolation: `index(m) = index(m1) + (m - m1)/(m2 - m1) x (index(m2) - index(m1))`, monthly: `index(m) = index(m1)`; reference index(month) = actual(month - lag).
  RPI reference for 20-Jul-2001, daily, 3-month lag = act(1-Apr-01) + 19/31 (act(1-May-01) - act(1-Apr-01)). Only price instruments and curves with the same lag.
- **Worked**: OATei 1.85% 2027 for value 22-Jul-2025: reference value = 128.16 + (21/31)(128.08 - 128.16) = 128.10581; base 93.72591; index ratio 1.36681. Real price 103.141 on 1mm: principal
  1,409,741.50 + accrued 0.0185 x 362/365 x 1.36681 x 1mm = 25,078.15, total 1,434,819.65 (BofA 2025, recomputed). US: April CPI NSA 320.79500 is the reference value for 1-Jul-25; 22-Jul-25 =
  320.795 + (21/31)(321.44339 - 320.795) = 321.23423. Both checked in `scripts/conventions.py`.

## 7. Spreads, quotes and ASW types
- Curve spreads in Europe and Japan: higher spread means the instrument is cheaper to the curve. US swap spreads are quoted as swap minus Treasury (a higher US swap spread means a richer Treasury).
  Vendors muddle this by applying the US convention to EUR and JPY series. Data pipelines commonly compute spread_bp = (swap rate - bond YTM) x 100 (swap minus bond, negative when the swap is below the bond), while
  some published charts use UST yield minus IRS (Bassman, Convexity Maven, Jan 2016). Always store the sign with the data.
- ASW sign: ASW = X in "reference rate + X" (a Bund at Euribor - 10bp has ASW -10bp; richening against swaps lowers the ASW). Par/par, optical (bond versus benchmark swap, no upfront; common in the UK),
  maturity-matched (traded a lot in EUR), true/market-value (rare in EUR) differ. Par/par bond-basis spread converts to money-market basis by x 360/365.
  Worked par/par: 5.5y 5% bond at dirty 112.16, annuity 10.0096, x = -0.166 per semi period, Libor spread -0.166 x 2 x 360/365 = -32.7bp (JPM, Asset Swaps, 2006). The same bond at 99.85: yield-yield ASW 40bp on IRS
  notional 49.6mm (delta neutral) versus par-par RFR + 37.6bp on 50mm (not delta neutral).
- USD "spreadover": on-the-run UST versus the same-tenor spot swap, neither coupon- nor maturity-matched, about 70% of interdealer volume; SOFR spreadover: fixed annual ACT/360, SOFR compounded in arrears paid annually,
  PAI at SOFR. With a SOFR floating leg the secured-unsecured basis disappears from government-bond swap spreads; a LIBOR swap spread was a LIBOR-repo basis swap over the bond's life.
- Basis swap quoting: spread on the shorter/overnight compounded leg ("spread adjusted"); for IBOR/OIS the spread is on the IBOR leg. Tenor basis (IRBS) is quoted either as two IRS (spread = difference of fixed rates;
  EUR standard since 2008) or as float versus float plus spread, differing by an annuity ratio; quote = higher-frequency leg fixed minus lower-frequency, normally positive. AUD 3s6s basis derived = semi 6M swap minus quarterly 3M swap.
- CCBS: all CCBS have a USD leg; the spread sits on the non-USD leg ("5Y EUR/USD at -38/-37": pay 3M EURIBOR - 37bp against receiving USD, or receive EURIBOR - 38bp against paying USD). Trade the float/float CCBS plus a separate
  fixed/float swap. Non-MTM XCS: notionals exchanged at start and end at the initial FX; MTM XCS is the interbank standard. "EURUSD" = USD per 1 EUR; "EUR/USD" XCS = spread on the EUR leg.
- Direction jargon: "mine" pays fixed for a swap trader but buys the bond for a bond trader. Outright delta positive prefers rates up; SBS basis positive prefers the longer-tenor index up; XCS basis positive prefers the
  domestic basis up. A SEF "buyer/seller" refers to options; payer/receiver to swaps.
- Curve naming (multi-CSA): the code before ":" is the only currency the curve applies to; after the colon "." = forecasting curve and "-" = discounting curve, for example EUR:1D.ESTR, USD:1D.SOFR, GBP:1D.SONIA,
  EUR:EUR-CSA, cross-CSA EUR:USD-CSA. Forward FX must not depend on the CSA. See [fi-collateral-csa-and-xva](../../fi-collateral-csa-and-xva/SKILL.md).
