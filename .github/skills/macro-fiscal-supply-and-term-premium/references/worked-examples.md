# Worked examples: fiscal supply and term premium

Supplement to [SKILL.md](../SKILL.md). Every number is taken from a cited source and dated. Use them to test the
arithmetic, not as current levels. Re-run the arithmetic on live data.

## 1. Expected return of a long bond (risk-premium identity)

Inputs (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022, App. A8): short rate r0 = 1%, factor duration
D = 5, market price of risk lambda = 10bp per year of duration.

- Expected return: E[dP/P] = r0 + lambda x D = 1% + 0.10% x 5 = **1.5%**.
- Sharpe ratio with factor volatility sigma = 100bp per year: lambda / sigma = 0.10 / 1.00 = **10%**.

Use: a premium is proportional to duration. A 10y bond with the same lambda earns twice the premium of a 5y bond.

## 2. Gauss+ long-factor premium and expected short rate (10y)

Inputs (Tuckman and Serrat, 2022, Gauss+ example): lambda (Sharpe-type price of rate risk) = 0.09 (sample average),
long-factor vol 100bp, 10y loading on the long factor 0.7.

- 10y risk premium = 0.09 x 0.01 x 10 x 0.7 = **63bp**.
- Convexity term about **24bp**.
- With a 10y forward of 3%, the expected 1y rate 9y ahead = 3% + 0.24% - 0.63% = **2.61%**.

Caveat from the same source: a lambda of 0.09 looks low against typical Sharpe ratios, but bonds have been
negatively correlated with risky assets, so a low or negative price of rate risk is expected. The model's 10y
premium rose as rates fell in 2014-22 (curve steepening read as higher premium), which is a regime effect, not a
bearish signal.

## 3. Forward decomposition in one line

Forward = expected short-rate path + duration x lambda - convexity bias, with convexity bias = 0.5 x C x sigma^2.
The formula is from Tuckman and Serrat (2022), eq. 8.20. The numbers below are illustrative and not from the source:
a convexity of 100 (years squared) and sigma of 100bp give a bias of 0.5 x 100 x 0.0001 = 0.5%. Read the
convexity term before calling a forward rich or cheap. The bias is a model term, not a market quote.

## 4. Term premium table (Barclays, Global Rates Weekly: The urgency question, 2 Oct 2026)

| Tenor | SOFR swap | Expected FF | Rate-TP (swap - expected) | Tsy - SOFR | Tsy | Total TP | Historical average TP |
|---|---|---|---|---|---|---|---|
| 2y | 4.67 | 4.36 | 0.31 | 0.15 | 4.81 | 0.46 | 0.34 |
| 5y | 4.75 | 4.17 | 0.57 | 0.29 | 5.04 | 0.86 | 0.85 |
| 10y | 4.85 | 3.91 | 0.95 | 0.41 | 5.26 | 1.35 | 1.31 |
| 30y | 4.94 | 3.69 | 1.25 | 0.68 | 5.62 | 1.93 | 1.78 |

Rows are in percent. Total TP = (SOFR swap - model expected FF) + (Tsy - SOFR). The 10y total is 1bp off its
columns (0.95 + 0.41 = 1.36), and the 5y and 10y rate-TP cells are 1bp off their differences, from rounding in the
source. Use a 1bp tolerance when you check the table. Reading: Oct 2026 TP is near its historical
average at 5y and 10y (2y and 30y are 12-15bp above), so the TP level is not stretched. The latest move can still be TP:
Barclays had the post-FOMC 10y rise at about 25bp, of which about 16bp TP, and the SF Fed model attributed the year's
rise almost wholly to expected short rates while ACM attributed the post-FOMC rise almost wholly to TP.

## 5. Financing waterfall (BofA, US Rates Viewpoint: Lower UST WAM => backdoor easing, 2 Jul 2025)

Identity: borrowing need = deficit + other adjustments + change in TGA. Net coupons = gross coupons - public coupon
maturities - buybacks. Net bills = borrowing need - net coupons. Bill share = bills / marketable debt.

| Fiscal year ($bn) | Deficit | Borrowing need | Net coupons | Net bills | Bill share |
|---|---|---|---|---|---|
| FY25 | 1,925 | 1,819 | 1,505 | 314 | 21.4% |
| FY26 | 2,000 | 2,100 | 1,275 | 825 | 22.6% |
| FY27 | 2,050 | 2,100 | 1,033 | 1,067 | 24.3% |

Check the arithmetic: FY26 2,100 - 1,275 = 825; FY27 2,100 - 1,033 = 1,067. Against the source's "stable coupons" case, the plan issues $1,003bn less 10y-equivalent duration over FY26-27 (FY26 $284bn, FY27
$719bn). That is about 3.3% of GDP (derived, assuming GDP near $30tn), so about 33bp lower 10y yield unadjusted and about
31bp adjusted, using the supply-to-yield rule below. The
source's trade was a 3y-to-20y swap-spread steepener at -51bp (target -30, stop -65), on the view that front spreads
cheapen on bills and the 20y richens on a shorter WAM.

## 6. Duration supply to yield (rule of thumb from the same source)

- Gagnon, Raskin, Remache and Sack (2011): a 1% of GDP increase in unadjusted supply = about 7bp on the 10y.
- Crawley et al., FEDS Note (Jun 2022): a permanent 1% of GDP cut in 10y-equivalent duration = about 10bp.
- Use the sign and rough size, not the decimal, because estimates vary widely.

## 7. Bill-OIS by flow (Barclays, US short interest rate primer, Jan 2025)

Model bill-OIS with the 3m change in bill supply, not the bill share. Large net paydowns coincided with very rich bills
(to about -50bp). Large net issuance coincided with bills at about 0 to +15bp (scatter, 2015-23). Bill share alone
was a weak predictor.

## 8. Fiscal fair value and sovereign betas

- Barclays (2 Oct 2026): 1pp of deficit/GDP is about 20-30bp on long yields. A +100bp rate path adds more than USD 3trn
  to 10y borrowing over 10 years, about 1% of GDP a year. Unlike MBS or futures convexity, this does not fade as rates
  rise.
- Citi, Going nuclear on the curve (3 Feb 2017): 10s30s was 28bp too flat with no fiscal expansion and 35bp with a
  2pp deficit/GDP rise. Implied slope effect about 3.5bp per pp (derived here from the two numbers).
- GS, Reaching Limits (2 Oct 2026): OAT-Bund moves about 10bp per 1pp of GDP change in one-year-ahead deficit
  expectations. Cross-country spread to OIS against debt/GDP is about 1 to 3bp per ppt since 2013.

Implied-move test on the September 2026 OAT-Bund widening (GS): a 50bp move at 3bp per ppt needs a debt/GDP shift of
about 15 to 17ppt. Economists revised 2026 and 2027 deficits by only 0.4pp and 0.5pp of GDP. The move is therefore
mostly risk premium and uncertainty. The 10y OAT-Bund went above 150bp before retracing to 140bp.

## 9. Term funding premium arithmetic (J.P. Morgan, Buying back time, 19 Aug 2026)

TFP = minus the cross-sectional slope of maturity-matched swap spreads on modified duration (bp per year of duration).
The model's residual was tested against a one-year window.

- Aug 2026: TFP moved from 4.7 to 4.4 against a fair value of 4.2, about one standard deviation above it.
- Inversion: back out the Treasury WAM shift that would justify the move. A -0.3bp TFP move needed about 3 months
  shorter WAM. If that is implausible against the deficit, the move is outsized and a profit-taking candidate.

Mechanics and the full model belong to the spread skill (see Related skills).

## 10. Buyback reaction, Aug 2026 (sources as cited)

- Size: USD 2bn to at least USD 4bn per 10-20y and 20-30y operation, from 9 Sep to 4 Nov. At least +USD 14bn for the
  quarter and a USD 16bn quarterly floor, about 14% of 20y and 30y gross supply per quarter (Citi, Top of Mind, 21 Aug
  2026; 16/111 = 14.4% of the USD 111bn gross for Aug-Oct). Net 20y+30y supply is USD 97bn against 103bn before, a
  small change (FT Alphaville, 20 Aug 2026).
- Curve: the long end fell 8-9bp, the 2s30s swap spread moved from about -60 to -55bp (toward zero, meaning Treasuries
  richened against swaps), and the market round-tripped the next day (Financial Times, 20 Aug 2026; J.P. Morgan, Buying back time, 19 Aug 2026).
- Market-implied threshold: the 30y at 5.3% was read as the trigger for more action (Citi, 19 Aug 2026).

## 11. Solvency-belief survey (Delao and Li, NBER WP 35612, Aug 2026)

- Mean value shares of backing (investors / voters / econ-fin): safe-asset 29.5 / 25.7 / 26.0; rollover 16.9 / 17.8 /
  18.8; Fed 15.1 / 15.7 / 17.6; government real assets 14.1 / 17.1 / 13.3; repression 9.7 / 9.4 / 8.4; primary
  surpluses 14.7 / 14.3 / 16.0 (percent). Safe-asset plus rollover is about three times the surplus share.
- Perceived debt/GDP: median 60% among bond investors against about 100% actual.
- Illustrative capacity model (beta = 0.8, rho = 1): a surplus-only composition deploys 20% of debt; elicited shares
  deploy 32-36%. The authors say this is illustrative, not an estimate of US capacity.

## 12. Market-constraint and fiscal-premium sanity checks

- Decomposition check (Citi, Global Macro Strategy, 31 Jul 2026): residual 5s30s on 5s, rolling five-year window. The
  residual is the term-premium proxy. Since the post-Covid fiscal expansion, a rising UST term premium has been
  dollar-negative. Use as a regime signal, not a timing signal.
- Kim-Wright survey-anchored model (Willer and Saunders, 2026): top quintile of one-month TP rises (more than +10bp in
  a month) gave US equity information ratios of -0.20, against +0.46 to +0.92 in the other quintiles. A 10y
  real-yield rise above +14bp a month was relatively consistently negative for equities since late 2014.

## 13. Debt-limit resolution analogs (BofA, Funding & debt limit: history lessons, 27 Jun 2025)

Method. (1) Choose episodes whose state matches today: limited excess liquidity left in ON RRP and a similar percentage
growth in expected bill and total marketable supply. The 2017 and 2018 resolutions were five months apart, so they count
as one long episode; 2019 is a separate funding-stress analog. The 2021 and 2023 episodes had far more ON RRP liquidity
and are not comparable. (2) Measure the average change over 1, 3 and 6 months after resolution, using a 1-month
moving average over each window. Mechanics: before the X-date the TGA is run down while net issuance is frozen, so cash
is plentiful; after resolution the TGA rebuild drains cash while mostly bills are issued.

Average change after resolution, in bp, in this skill's signs (SOFR minus FF, SOFR minus IORB, bill minus OIS; positive
means higher SOFR or a cheaper bill). The source printed FF less SOFR and OIS less bill, so its signs are the reverse.

| Indicator | 1m | 3m | 6m | Episode detail (1m / 3m / 6m) |
|---|---|---|---|---|
| SOFR - FF | +7.7 | +4.4 | +5.1 | 2017: -1.9 / +0.4 / +9.6; 2018: +10.0 / +11.7 / +7.7; 2019: +14.8 / +1.0 / -2.1 |
| SOFR - IORB | +3.0 | +5.1 | +5.7 | 2017: -2.0 / +0.7 / +11.2; 2018: +10.5 / +15.0 / +12.4; 2019: +0.7 / -0.5 / -6.4 |
| 1m bill - OIS | +7.5 | +4.0 | +9.3 | average only |
| 3m bill - OIS | +3.6 | +1.5 | +4.2 | average only |
| 2y UST-OIS | 0.5 | -0.8 | 3.5 | as printed (sign not normalised) |
| 5y UST-OIS | -0.1 | 0.2 | 3.3 | as printed (sign not normalised) |

The source labels the UST-OIS rows as OIS less UST yet describes the effect as Treasuries biased cheaper, so confirm the
sign in `swap_spreads` before using them directionally. The magnitudes are the point: under 1bp at 1 and 3 months and
about 3bp at 6 months, against 2-9bp in the funding rows. The 2019 3m and 6m figures are distorted by the Fed's
intervention after the Sept 2019 repo spike. Check: the SOFR-IORB average at 3m is (0.7 + 15.0 - 0.5) / 3 = 5.07, which
rounds to the printed 5.1; allow 0.1bp from rounding.

Supply conditioning, percent change in the six months before to after resolution (1m / 3m / 6m):

| Episode | Bills outstanding | Total marketable debt | ON RRP ($bn) |
|---|---|---|---|
| 2017 | +1 / +8 / +29 | - | 96 (1m before) to 120 (1m after) |
| 2019 | +4 / +3 / +5 | - | near 0 |
| 2023 | +11 / +25 / +49 | - | 2,218 to 1,910 |
| 2025 projection | +6 / +6 / +2 | +2 / +4 / +5 | 143 to 80 (1m); 138 to 0 (3m) |

Bills outstanding were about $5.8-6.5tn in 2025. Reading: the 2017-19 set was used because its ON RRP buffer and
bill-supply growth were closest to the 2025 projection; 2023 had a far larger buffer and a much larger bill surge. Hand
off front-end trade construction to the money-market skill (see Related skills).
