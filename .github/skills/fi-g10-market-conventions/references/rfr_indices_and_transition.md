# RFR index construction, fixing methods and the IBOR to RFR map

Detail behind `SKILL.md` sections on overnight rates and the transition. For repo plumbing, corridor levels and rate
hierarchies used as signals, see [stir-repo-and-funding-plumbing](../../stir-repo-and-funding-plumbing/SKILL.md): levels in
the sources differ by date (for example SOFR on 1 Jul 2025 is 4.44% in one note and 4.30% in another), so no level is stored here.

## 1. How each USD benchmark is built

| Rate | Definition | Notes |
|---|---|---|
| TGCR | overnight tri-party UST repo, excluding trades where the Fed is a counterparty | UST collateral only. Published since Apr 2018 |
| BGCR | TGCR plus FICC GCF repo | prints almost identical to TGCR; adds dealer window-dressing noise |
| SOFR | BGCR plus FICC-cleared bilateral DVP repo, volume-weighted median | rounded to 1bp; published about 8:00 ET for the previous business day; may be revised about 14:30 ET on the publication day only if the change is at least 1bp; percentiles (1/25/50/75/99) and volumes published, trades not. Published since 3-Apr-2018 (modelled history from Aug 2014) |
| NCCBR | non-centrally-cleared bilateral repo | tracked by no benchmark |
| EFFR | volume-weighted median of overnight fed funds | policy target (25bp range). Mostly FHLB lending to foreign banks (the "IORB arbitrage"), roughly 95% of volume. About 100bn a day against about 2-3tn for SOFR |
| OBFR | fed funds plus Eurodollar plus selected deposits | trades alongside EFFR |
| TPR (OFR) | tri-party repo on all collateral (UST, agency, corporates) | different from TGCR, so decompose by collateral before reading a move |

**Specials trimming.** Early SOFR dropped DVP trades below the 25th volume-weighted percentile. A methodology change
proposed 18-Jul-2024 would remove the lowest-rate 20% of DVP volume and strip inter-affiliate trades (about half of repo
volume), driven by the clearing mandate moving uncleared bilateral repo into FICC DVP. Cleared and uncleared medians sit within
about 1bp, so do not assume a large mechanical rise from clearing. Expect SOFR to print a couple of bp above TGCR/BGCR because of
hedge-fund DVP borrowing. Years: SEC clearing mandate for most UST repo with CCP members, mid-2026 to mid-2027 (sources differ).

**Facts that matter for modelling.**
- SOFR is an index, not a tradable cash rate; its volume-weighted median with opaque volumes means SOFR futures cannot be
  priced purely by no-arbitrage (residual fixing risk of a few bp).
- SOFR <= EFFR is not a hard bound (violated for weeks in 2018-19); SOFR <= standing-repo-facility rate is a soft bound.
- SOFR can print below the policy range without administered-rate action; the Fed's technical adjustments to IORB happened
  when EFFR had traded within about 5bp of the range edge.
- Quarter-end and year-end turn spikes in repo fixings are a turn effect, not a regime change (GCF about 5.60% in early Jan 2024
  against about 5.40% by mid-Jan). Treat turn dates separately.
- The Fed's standing repo facility (announced 28-Jul-2021, operating from Aug 2021) is a structural break in SOFR volatility:
  re-estimate spike statistics on post-Aug-2021 data (Huggins and Schaller, SOFR Futures and Options, 2022).

**SOFR Index** (NY Fed): base 1.00000000 on 2-Apr-2018, 8 decimals, Index = product over business days of
(1 + SOFR_i d_i / 360). Term rate R = (Index_end / Index_start - 1) x 360 / D. Example: USD 1mm between 15-Sep-21 and 15-Dec-21 on
index values 1.04235797 and 1.04227169 pays 1,000,000 x (1.04235797 / 1.04227169 - 1) = USD 82.78.

**Backfill proxy** (Federal Reserve Board FEDS Notes 2019): SOFR = SurveyRate + 0.38 x (GCF - SurveyRate - 0.05) (%), R-squared 99.8%
on Aug 2014 to end 2017, with the primary-dealer survey GC rate as the pre-2015 proxy.

## 2. Other RFRs: facts that change a calculation

- **SARON** (SIX, since 2009): volume-weighted from CHF repo trades and binding quotes; reference fixing 18:00 Zurich; A/360;
  compound rates and indices published for 1w to 12m in arrears. The SARON forward curve sat below spot beyond about 22y and
  was negative over a wide range of terms in May 2021 (Tuckman and Serrat 2022, Ch.2).
- **ESTR** (ECB, 2019): volume-weighted trimmed mean of overnight unsecured borrowing (47 reporting banks and 65.7bn volume on one
  Nov 2026 day); replaced EONIA (EONIA was re-defined as ESTR plus a fixed 8.5bp until it ended, external knowledge).
- **SONIA** (BoE; reformed 2018): volume-weighted trimmed mean; simple compounding on A/365F; GBP overnight GC repo trades about
  3-8bp over Bank Rate (BoE Bank Overground 2025).
- **TONA** (BoJ, 2016): uncollateralised call-market average; two vintages (provisional same day, final next morning), so store both.
- **CORRA** (BoC): GC repo against GoC securities, 365-day year with no 366 adjustment. Compounded index published 11:30 ET.
- **AONIA** = RBA cash rate; **NZIONA** = RBNZ OCR-linked overnight index; **NOWA** A/365 while NIBOR is A/360; **SWESTR** is deposit-based.

## 3. Compounding, lags, lookbacks and lockouts

Compounded RFR over a period (ISDA 2021, NY Fed User's Guide form):
`R = [ product_i (1 + r_i n_i / N) - 1 ] x N / d_c`, with n_i the calendar days rate i applies (3 for Friday, more before a
holiday), N = 360 (USD, EUR, CHF, SEK) or 365 (GBP, JPY, CAD, AUD, NZD, NOK), d_c = calendar days in the period. A simple
average replaces the product with a sum. Do not compound consecutive values of a term (IBOR) curve. Compounding identity:
`f = (product (1 + d_i r_i) - 1) / sum d_i`; two days at 1% and 2% (A/365F) give 1.5000274%. Compounding reproduces a discount
factor ratio only for actual-day counts with a fixed denominator (A/360, A/365F), not for 30E/360.

| Method | What it does | Where it is the standard |
|---|---|---|
| Payment delay | observation = accrual period; pay n BD after period end | OIS and cross-currency swaps |
| Observation shift (lag) | observe the window shifted back n BD, weight by the shifted days | FRNs (2 or 5 BD; European FRNs use 5) |
| Lookback (no shift of weights) | rate from n BD earlier, weights from the accrual calendar | loans; lumpy fixing exposure around weekends |
| Lockout | freeze the rate n BD before period end | loans; mismatch with futures grows with n |
| Arithmetic averaging versions of each | simple instead of compounded | rare |
| In advance, in arrears (IBOR style) | single term fixing | legacy |

Payment delay and observation shift allow efficient discount-factor pricing, which is why ARRC recommended them. Lookback and
lockout create fixing exposures that are lumpy (about 3x and one third of the notional around weekends) and hard to hedge.
Policy transmission under lagged observation is delayed by about p/2 + l (observation period p, lag l).

**Three accrual structures** (Tuckman and Serrat 2022, Fig 12.1), 1mm, 31-day month:
(a) term rate set in advance, paid in arrears: 1mm x 0.07525% x 31/360 = 64.80;
(b) overnight set in arrears, compounded: 1mm x [(1 + 0.03%/360)^3 (1 + 0.04%/360)(1 + 0.05%/360)^27 - 1] = 41.11 (the book prints the last exponent as 2, a typo);
(c) overnight set in advance, paid in arrears: 1mm x [(1 + 0.05%/360)^31 - 1] = 43.06.

**FRN coupon** (Duering 2021, Ch.17): the "ideal" coupon compounds the margin; market practice computes the compounded rate over
the observation window and adds the margin **without compounding**, which keeps accrued interest defined. Fixing "should not be
published on the settlement day", hence the observation shift; with ex-dividend periods the last fixing may not be known when
negative accrued is due, so accrue with forecast fixings if the shift is shorter than the settlement lag.

**Spread on a compounded leg** (Darbyshire, Coding Interest Rates, c.2024): "none/simple" r = (1/d)(prod(1 + r_i d_i) - 1) + z so
dr/dz = 1; ISDA compounding applies the spread inside each daily factor (non-linear in z); ISDA flat compounds the spread on prior
accruals (no closed form). On one example, an extra 15mm PV on the float leg needed 362.23 / 357.71 / 360.66bp (none / ISDA /
ISDA flat). Solve the mid spread numerically.

**Known plus forecast fixings:** `1 + d r = (1 + R_1 d_1)...(1 + R_k d_k) x (1 + r_{k+1} d_{k+1})...` with capital R published.
For an in-period futures contract, split R into the known and unknown parts:
`R_unknown = [ (1 + R D/360) / prod_known(1 + r_i d_i/360) - 1 ] x 360 / D_unknown`.

**Constant-SOFR compounding gap** (SOFR Futures and Options, Table 3.2): 1y, constant SOFR in bp to compounded term rate in bp:
100 to 101, 200 to 202, 300 to 305, 400 to 408, 500 to 513. The constant daily rate reproducing a price of 98.41 is 1.5869%, below
the 1.59% simple rate.

## 4. IBOR to RFR map

| Ccy | Legacy overnight index | Legacy term index | RFR | Mapping notes |
|---|---|---|---|---|
| USD | EFFR (survives as policy rate) | USD LIBOR (ceased; last tenors 30-Jun-2023), BSBY (gone), CME Term SOFR (derived from futures) | SOFR | Fallback spread = 5-year median of LIBOR minus compounded SOFR, fixed on 5-Mar-2021. Eurodollar futures convert to SOFR futures at a fixed 26.161bp (ISDA adjustment added to option strikes) |
| EUR | EONIA (= ESTR + fixed spread, ended) | EURIBOR (reformed, alive) | ESTR | Legacy EUR LIBOR gone. EURIBOR hybrid methodology: Level 1 transactions, Level 2 modelled, Level 3 discontinued Feb 2024 |
| GBP | SONIA (reformed 2018), RONIA | GBP LIBOR (ended; synthetic as a fixed function of SONIA for a short tail) | SONIA | term SONIA rates are published by data vendors |
| JPY | TONA | JPY LIBOR (ended; synthetic for a tail), (D-)TIBOR alive, Euroyen TIBOR stopped end-2024 | TONA | TORF (QUICK) is a TONA-based term rate |
| CHF | TOIS (discontinued 2017), SARON | CHF LIBOR (ended) | SARON | |
| CAD | CORRA (reformed) | CDOR (ceased 28-Jun-2024) | CORRA | BAX to CRA at 32.138bp |
| AUD | AONIA | BBSW, BBSY | AONIA | BBSW persists as swap standard |
| NZD | NZIONA | BKBM | NZIONA | BKBM persists |
| SEK | STINA (legacy), SWESTR | STIBOR | SWESTR | STIBOR persists |
| NOK | NOWA | NIBOR | NOWA | NIBOR persists; fallback = NOWA compounded with a 2-day observation shift plus spread, rebased A/365 to A/360 |

"Mapping" means common benchmark, not identical floating rate option: fixing days and times, calendars and fallbacks may differ
(ISDA 2021 FRO mapping tables). Broker CCP-basis FROs, REPOFUNDS RATE, CAD-REPO-CORRA, CHF-TOIS and JPY-MUTANCALL were not carried
into the 2021 definitions.

**What the index measures** (risk content): LIBOR and EURIBOR were term, unsecured and bank-credit bearing, so they spiked in
stress (2008, 2011, 2020). SOFR and SARON are secured and risk-free and fell or stayed flat in stress; RFR futures and swaps
carry no bank-credit component. LIBOR-OIS was a stress gauge; OIS-SOFR gauges repo balance-sheet scarcity (SOFR far above OIS in Sep 2019).

**Structural breaks for history.** After cessation: swap-spread time series change meaning (the secured-unsecured basis leaves
government-bond swap spreads), cross-currency basis legs move from LIBOR to SOFR (ESTR-TONAR is now executed as ESTR-SOFR plus
SOFR-TONAR), and SOFR history behaves "like a series of swap rates to which a cap is added mid-series" (Huggins and Schaller
2022, 2024). For long histories use constant-maturity par yields from a fitted government curve (see
[bond-rich-cheap-fitted-curve](../../bond-rich-cheap-fitted-curve/SKILL.md)) or stitch with a documented break date; track
index-definition and removal dates in the pipeline (for example the EUR/USD IBOR cross-currency curve was removed 6-Feb-2023).
LIBOR-era swaps used 3M LIBOR vs fixed 30/360 semi-annual (USD), a 3M-LIBOR spot lag T+2 (T+0 GBP), and an FF/LIBOR basis that used
an arithmetic average with a 2-day cut-off, whereas OIS uses a geometric average.

## 5. Legacy IBOR mechanics (only for old trades and histories)
- **LIBOR fixing**: panel ranked, top and bottom quartiles dropped, remainder averaged arithmetically; A/360 (A/365 GBP); fixed 2 London
  BD before value; spot-date rule: 2 good London days forward, then advance until good in both London and the currency centre. Panels
  (2010): 16 banks for EUR/GBP/JPY/USD, 12 for CAD/CHF, 8 for AUD/DKK/NZD/SEK. EURIBOR panel about 44 banks, 15% trimmed each side,
  11am CET, first quoted 4-Jan-1999. EONIA: weighted average of overnight unsecured panel lending, A/360, 3 decimals.
- **FRA notation** "A x B over C": settle A months forward, mature B months forward, index tenor B minus A months, fixing 2 London BD
  before settle; C = day number, IMM (third Wednesday), End (last good NY and London BD of the month) or omitted. Buyer pays fixed.
  Settlement amount `N (r_fix - r_FRA) t/360 / (1 + r_fix t/360)` paid at period start (365 for GBP).
- **IBOR fixing lag**: GBP none (3M value 3-Feb published 3-Feb), EUR 2 BD.
- Fallback for IBOR swaps: compounded RFR plus a fixed spread set at cessation; the IBOR becomes look-back instead of look-forward,
  fine for in-arrears swaps, awkward for in-advance.
