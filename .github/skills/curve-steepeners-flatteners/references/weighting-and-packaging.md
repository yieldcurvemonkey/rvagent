# Weighting, hedge ratios and packaging of curve trades

Detail behind the "Weighting" step of [SKILL.md](../SKILL.md). Notation: `h` = risk (DV01) on the long-tenor leg per unit of
risk on the short-tenor leg, so a steepener P&L is `R * (h * dy_long - dy_short)` per unit of short-leg risk `R`. `h = 1`
is DV01-neutral. Rates in bp.

## 1. The four hedge ratios when the legs are not perfectly correlated

Hedging a long bond (30y) with a shorter instrument (5y). Let `s5, s30` be the vols of daily/weekly yield changes and `rho`
their correlation. Amount of 5y needed, relative to the conventional (DV01) amount (Burghardt, Belton, Lane, Papa, The
Treasury Bond Basis, 3rd ed., 2005):

| Rule | 5y amount | In `h` terms (script column) | Property |
|---|---|---|---|
| Conventional (DV01) | `DV01_30 / DV01_5` | `1` (`dv01`) | zero net DV01; the right one for trading the quoted spread |
| Yield beta | conventional `/ (s5/s30)` | `s5/s30` (`vol`) | assumes `rho = 1`; over-corrects when `rho < 1` |
| Yield delta | yield beta `/ rho` | `rho * s5/s30` (`reg_long`) | = OLS slope of `dy_5` on `dy_30`; zero *expected* P&L for a given long-leg move |
| Minimum variance | yield beta `* rho` | `s5 / (rho * s30)` (`reg_short`) | lowest P&L variance when the long position is fixed and the short leg is its hedge; the largest `h` of the four (least short-leg hedge) |

Worked numbers, $100mm OTR 30y vs 5y on 12 Jan 1998 (same source): `s5 = 101.9bp`, `s30 = 81.7bp`, `rho = 0.88`,
conventional hedge $341.2mm of 5y. Yield beta 273.6, yield delta 310.9, minimum variance 240.7 ($mm of 5y); net DV01 left
unhedged 29.5 / 13.2 / 43.9 ($k per bp). The script's `--selftest` reproduces these three figures.

Weekly OTR yield-change correlations 1990-97: 30/10 0.97, 30/5 0.88, 30/3 0.74, 10/5 0.96, 10/3 0.87, 5/3 0.97; annualised
vols 30y 81.7bp, 10y 94.3, 5y 101.9, 3y 104.1. Distant legs need the correlation adjustment; adjacent legs do not.

Yield-vol-vs-duration fit (UST, annualised sd of weekly yield changes regressed on modified duration D, from 1990): R2 0.81, valid for D between 2 and 12.5 and
breaking down inside 2y. The printed coefficients (-0.0002, 0.0111) do not reproduce the source's own table; the table implies `sd ~ 1.121 - 0.0243 * D` (%, annualised). Beta to the 12.5-duration OTR bond assuming rho = 1 (table): 1.31 at D=2, 1.22 at 5, 1.08 at 10, 1.00 at 12.5.

Beta instability: the OTR 10y beta was 1.186 on 12 Jan 1998 but ranged 2.88 (1991) to 0.46 (1993, the year the curve flattened
as yields fell). "Betas might actually work against you" in such years (same source). Hence the stability test in the
script (`h_unstable`).

Regression hygiene: a DV01 hedge implicitly assumes beta = 1 (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022); the risk
weight of a regression hedge equals the slope coefficient; direct and reverse regressions give different hedges; level
regressions have serially correlated errors, so regress changes (US 1y vs 3y CMT weekly 1962-2009: levels r3 = 0.832 + 0.930*r1
with unit-root-like residual, changes c3 = 0.792*c1, R2 82.5%; Tsay, Analysis of Financial Time Series, 3rd ed., 2010).

## 2. Weighting by a level factor and by PCA

- **Level-neutral h**: `h = beta_s|x / beta_l|x`, betas of each leg's changes on the changes of a level factor `x` (10y yield, or
  PC1 score). Then the weighted spread `h*y_l - y_s` has zero regression beta to `x` by construction (script check
  `dir_beta_weighted_on_level = 0`).
- **PC1-neutral is superior to parallel-DV01-neutral**, especially before high-vol events (Golub & Tilman, Risk Management:
  Approaches for Fixed Income Markets, 2000; Golub (ed.), BlackRock's Guide to Fixed-Income Risk Management, 2023). PC1 loadings
  track the term structure of vol: `p1_i = rho_1,i * sigma_i / sqrt(lambda_1)`, so when correlations are near 1 the PC1 shape
  mirrors the vol ratio (Golub 2023, Ch.3). Check PC1 explains > 95% before using a one-factor model.
- **A single PC1 hedge needs two PCs of risk checking**: on 30 Sep 1996 PC1 explained 93% while a parallel shift explained 88%, so
  the non-parallel part of PC1 (5%) is as big as PC2 (5%); duration-neutral strategies need at least PC1+PC2 (Golub & Tilman 2000).
- **PCA hedge ratios** `min Var(x - g*y)`, `x = sum_p c_p u_p^x` (Credit Suisse, PCA Unleashed, 24 Oct 2012): PC1 only
  `g = u1x/u1y`; PC1+PC2 `g = (u1x u1y l1^2 + u2x u2y l2^2) / ((u1y)^2 l1^2 + (u2y)^2 l2^2)`. PC1-only hedges explode where the level
  loading is near zero (long end: 30y10y row vs 1y1y = 7.88, 25y5y = 6.47).
- **PC1-neutralising an existing trade** with risk vector `t` and unit-norm eigenvector `e1` (Quantitative Finance Stack Exchange,
  Hedging a trade for PCA component neutrality, Nov 2019):
  A) divide-by-loadings `(t+x) = t/e1` elementwise (needs `sum t = 0`; weights blow up if a loading is near 0, e.g. `PC1 = [-1,0,1]`);
  B) minimum-change projection `t + x = (I - e1 e1')t`; each extra PC constraint removes a degree of freedom (3 instruments: PC1- and
  PC2-neutral leaves only PC3).
- **Directionality hedge comparison** for a 2s5s10s fly `[-1,2,-1,0]` (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed.,
  2022): naive PCA `[-0.89,1.94,-1.30,0]`, minimal adjustment `[-1.07,1.94,-1.05,0]`, regression on PC1 `[-1.07,1.94,-1.04,0]`,
  VaR-minimising on 2y+10y `[-1.43,1.94,-0.37,0]` (far more adjusted). More hedge freedom lowers VaR but moves the trade away from its
  intended identity.
- **Duration-neutral hedges are meaningless across markets or very different maturities**; OLS hedge ratios are asymmetric, so use
  PCA or orthogonal regression; calibrate hedge models to minimise unexplained daily P&L, not to fit today's curve (During, Fixed Income
  Trading and Risk Management, 2021).
- **Do not re-weight legs to manufacture carry**: it breaks the trade's logic (During 2021).

## 3. Total DV01 is not enough: partial (bucket) DV01

Equal total DV01 still leaves curve risk and the same "parallel" shift is a different shift in par, zero and forward space (10y par
swap DV01 8.50 under a cc-forward shift vs 8.38 under a par-yield shift; Coleman, A Guide to Duration, DV01, and Yield Curve Risk
Transformations, May 2011). Worked case (same source): a $100 10y annuity (DV01 1.46) hedged with $31.47 of 5y bond is flat to parallel
but has forward-bucket exposures of -0.02 / -0.05 / -0.29 / +0.36 (0y1y, 1y2y, 2y5y, 5y10y), i.e. long the curve. In par-partial
terms the same hedge is $0.09 of 10y, $0.12 of 5y, $0.05 of 2y, $0.03 of 1y per $1 of annuity. Always hedge on bucketed risk
(see [fi-risk-dv01-and-transforms](../../fi-risk-dv01-and-transforms/SKILL.md)).

Bucket sensitivities (fixed grid 6m, 1y, 2y..5y, 7y, 10y, 15y, 20y, 25y, 30y; P&L for a 1bp move in one rate): a steepener is a linear
combination of them. Scenario P&L "2s and 10s up 2bp, 5s down 3bp" is `2*P2 - 3*P5 + 2*P10` ignoring convexity; check plausibility
against PCA and fully reprice for large moves. Curve gamma: twist the wings by -/+0.5bp around a 5y anchor; the change in the steepener
delta is the curve gamma (a duration-flat book with +100k 2s30s delta and -5k curve gamma becomes +150k steepener after a 10bp
inversion) (Quantitative Finance Stack Exchange, How to measure Steepener/Flattener/Butterfly sensitivity?, Oct 2021).

## 4. Packaging conventions

**Swaps** (Clarus Financial Technology, Mechanics and Definitions of Spread and Butterfly Swap Packages, 14 Oct 2014): price `S(0,t2) - S(0,t1)`,
`t2 > t1`, quoted in bp as a positive number; agree the notional of the longest swap; short-leg notional `N1 = [D(0,t2)/D(0,t1)] * N2`
(the DV01 ratio) so total DV01 is zero; set both legs at market (NPV 0), `S(0,t1) = S(0,t2) - spread`, to avoid convexity from off-market
legs. "Buying / paying / lifting / taking" a steepener = pay fixed on the long swap, receive the short. Equal notionals (e.g. $50m each)
leave net duration because the 10y DV01 is almost double the 5y. Benchmark packages are weighted `-1/+1` by equal pv01 and named by the
longest tenor: "paying $50k 5y/10y" = receive $50k pv01 5y, pay $50k pv01 10y (Darbyshire 2022).

**Cash bonds**: size `N1 = R/PVBP1, N2 = -R/PVBP2` (During 2021). The sold leg (the long tenor in a steepener) needs borrow, pays accrued and must be rolled to the on-the-run;
model own-issue repo (specials) on the sold leg; term vs overnight financing adds exposure to the money-market slope (reverse repo
typically 10-25bp below repo in the source's sample). Benchmark switches create fake slope jumps (German 25 Jul 2018 new 5y issue made
2s5s steepen and 5s10s flatten that day), so use constant-maturity or spline series for analysis.

**Spot vs forward-start swaps**: a spot-start IRS has a fixed first float period, so 2y/10y behaves like 1.5y/9.5y and carries an outright delta
overlay, "a common source of unexplained P&L". Use forward starters with notionals set for the wanted vol-adjusted delta; a CMS steepener
(receive 10y CMS on 2y, pay 10y CMS on 10y) has no ageing (Quantitative Finance Stack Exchange, Different ways to express a 2s10s steepener?,
Mar 2018).

**Treasury futures inter-commodity spreads** (CME Group, U.S. Treasury Futures Inter-Commodity Spreads, Feb 2024; CurveTrades, Yield Curve Spread
Trades, Jun 2013): buying the spread = steepener (long shorter contract, short longer). Fixed quantity ratios from CTD DV01s, e.g. 2y/5y 1:1,
2y/10y 2:1, 5y/10y 3:2, 5y/bond 3:1, 10y/bond 2:1 (June 2013 table; ratios are refreshed rarely, so check current ones). Fixed ratios leave a
residual DV01 tail: DV01-neutral was "sell 242 10y / buy 100 bond"; selling 100 of the 2:1 spread gives -200/+100, leaving a 42-contract tail
to be added outright. The 5y/10y spread index correlates 0.94 with the cash 5s10s yield spread. Quote the CTD yield differential, not
the net-change price: the same price can mean very different spreads and can be negative. Margin offsets make futures capital efficient;
roll costs are excluded from published return examples. Return approximation: bp change in spread x DV01 (a 10y/bond flattener,
$10mm, 155bp to 111bp = 44bp at average DV01 $165 per spread = $7,260 per spread, 7.26% on notional unlevered over about a year).

**Hedging with futures by bucket**: hedge a bullet with the duration-matched contract, a barbell bucket by bucket with BPV ratios (2/5/10/bond),
not by stacking 5y futures. Tilt: hedging with longer futures profits from steepening, with shorter futures from flattening (CME Group,
Understanding Treasury Futures, Nov 2017). Per bond contract, to hedge steepening at unchanged duration buy 1.85 10y futures
(122.42/66.13) or 2.83 5y futures (122.42/43.20) (Burghardt et al. 2005, 4 Apr 2001 DV01s). BPV hedge ratios assume parallel moves and a stable
CTD; BPV falls as yields rise, so re-evaluate after about 20-25bp.

**PVBP drift**: both PVBPs fall with ageing, the short leg faster in relative terms, so a DV01-neutral slope trade drifts; size with forward PVBP at
the holding horizon or re-hedge (During 2021).

## 5. Backtesting a spread

Model the value of $1 invested in the (re-weighted) spread as a total-return series rather than the raw spread: time-varying weights make a
raw spread converge with no price move, spreads can go negative, legs trade at different times. Treat rebalancing costs as a negative
dividend, not inside the series, "or shorting the spread will generate fictitious profits" (Lopez de Prado, Advances in Financial Machine
Learning, 2018). See [bt-backtest-design](../../bt-backtest-design/SKILL.md).

## 6. Barbell-vs-bullet is a flattener

A duration- and cash-neutral barbell-minus-bullet is mostly a curve trade: 5s/30s, 1980-94, monthly rolled, 99% of P&L variance from
reshaping, total -1.05% = yield -0.95 + reshaping -0.36 + convexity +0.30 + residual -0.04; bullet won 4 of 5 sub-periods (Salomon Brothers,
Understanding the Yield Curve Part 5, Sep 1995). Do not generalise wide-barbell results to narrow ones. Breakeven example: sell 10y par (rolling
yield 6.94%), buy 30y (6.67%) and 1y (5.73%) at 0.53/0.47 weights gives a 71bp give-up, recovered by an 11bp narrowing of 10s30s with no
parallel move or a 138bp parallel shift with no reshaping (10s30s narrowed >= 11bp in a year 30% of the time; 10y moved > 138bp 17%).
