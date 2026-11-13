# Extra worked examples (data quality and time-series hygiene)

Numbers are taken from the cited sources; "(checked)" means the arithmetic was reproduced when writing this skill.
Main method: [data-quality-and-timeseries-hygiene](../SKILL.md).

## 1. Mid-price construction on a rates book

**Arithmetic first-depth mid is unstable on a wide-tick contract.** Book 98.01 / 98.02: mid 98.015. A small bid
added at 98.015 moves it to 98.0175; lots sold at 98.015 plus a small offer there move it to 98.0125. That is variance
with no information. Size-weighted mid with a 5000-lot bid and 6500-lot ask gives 98.0143; an incoming 10-lot bid at
98.015 moves it to 98.0150 (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., Aitch & Dee, 2022,
Ex.19.1-19.3).

**Size-weighted mid can be spoofed.** Short-sterling book: 98.01 bid for 2000, 98.02 ask for 4500, weighted mid 98.0131.
A fund wanting to receive 1Y GBP swaps added 3000 lots behind the 4500 offer (unlikely to fill); the weighted mid moved
to 98.0121, 0.1bp higher in rate; the fund got its swap quote and pulled the offers. The desk then switched to a
multi-instrument least-squares mid (same source, Ex.19.3).

**Intrinsic depth mid, Bund future.** Book 36 @ 169.70 / 169.71 @ 53 and 78 @ 169.69 / 169.72 @ 88, `z = 65`:
`p_bida = (169.70*36 + 169.69*29)/65 = 169.6955`, `p_aida = (169.71*53 + 169.72*12)/65 = 169.7118`,
`p_ida = 169.7037` (checked). `z` is subjective: cross-validate it on training data (same source, Ex.19.4-19.5).

**Least-squares consistent mid, three SOFR futures (M2, U2, Z2).** Single-book mids 98.2120, 98.1160, 98.0440; own-book
spreads and fly 0.0950 (M2-U2), 0.1665 (M2-Z2), 0.0740 (U2-Z2), fly 0.0220, against 0.0960, 0.1680, 0.0720, 0.0240
implied by the outrights. Rows of `A`: `[1,0,0], [0,1,0], [0,0,1], [1,-1,0], [1,0,-1], [0,1,-1], [1,-2,1]`;
`s = [98.212, 98.116, 98.044, 0.095, 0.1665, 0.074, 0.022]`. OLS `p* = [98.2114, 98.1167, 98.0439]` (checked); WLS with
`W = diag(1,1,1,0.2,0.2,0.2,0.1)` gives `[98.2116, 98.1165, 98.0439]` (checked: 98.21165, 98.11645, 98.04390)
(same source, Table 19.2).

## 2. Filling a market that has not opened (Bayesian cross-market fill)

NOK 2Y before the Oslo open. Previous close (16:15 CET): USD 2.20, EUR 0.43, GBP 1.54, NOK 2.02. At `t1` the others
read USD 2.22, EUR 0.44, GBP 1.56, so `x = [2.0, 1.0, 2.0]` bp. Correlation matrix `Q` (USD, EUR, GBP, NOK) with rows
`[1,.80,.85,.75], [.80,1,.87,.84], [.85,.87,1,.82], [.75,.84,.82,1]`. The inferred NOK move is
`Y = Q_{NOK,x} Q_{xx}^{-1} x = 1.294bp` (checked: 1.2943), so NOK 2Y is inferred at 2.0329%. NOK then trades at 2.0275%,
which becomes the new reference. At `t2`, `x = [0.5, -1.5, 0.0]` gives `Y = -0.710bp` (checked: -0.7096), so 2.0204%.
Assumes multivariate normality and a stable covariance; reset the reference at every print of the opaque market
(Darbyshire, 2022, Ex.19.6). Use for indicative marks only, never as an observation.

## 3. Bid-ask bounce (Roll)

Model `p_t = m_t + c*q_t`, `q = +/-1`: `Var(dp) = 2c^2 + sigma_u^2`, `gamma1 = -c^2`, higher-lag autocovariances zero.
821 trades with `gamma1 = -0.0000251` give `c = 0.005` (checked: 0.00501), Roll spread `2c = $0.01`, against a quoted
spread of 0.022 and an effective spread of 0.0158 (Hasbrouck, Empirical Market Microstructure, NYU Stern teaching notes,
2004, Ch.3). Read: a negative lag-1 autocovariance in traded prices is bounce, and it understates the true spread here.
Pushes variance ratios above 1 at short horizons and can make a random walk look stationary: clean before testing.

## 4. Turn-of-year jumps in a short-rate curve

Euribor 1M fixings jumped +64bp (29 Nov 2007), +22bp (27 Nov 2008) and +9bp at the end of the semester (29 May 2008).
Quotes that carry the turn: OND on the last working day; TND and SND one or two days before; the 1M deposit jumps two
business days before the first business day of December; 12M deposits always include it except two business days before
year-end; the December IMM future and October/November serials always; 2Y swaps include two turns. Jump size scales
with the weight of the single crossing overnight rate (1M deposit about 1/22). On 11 Dec 2012: overnight-curve turn
+10.2bp (2013) and +8.5bp (2014); the 1M curve about 1/20 of the overnight curve; the 3M curve about 1/3 of the 1M;
negligible for 6M and 12M. One turn gives one discontinuity in the zero/discount curve and two in the FRA curve.
Estimate by interpolating non-crossing forwards and differencing against the quoted crossing one; futures-based
estimates for the first turn work only until the September IMM expiry. In practice include only the first two
year-ends (Ametrano & Bianchetti, SSRN 2219548, 2013).

Jump removal before interpolation: (1) build an overnight curve with linear/flat interpolation on liquid quotes;
(2) put a segment that is out of line back in line by moving the difference into a jump,
`JSize = [F_orig(t1,t2) - F_interp(t1,t2)] * tau(t1,t2) / tau_J` (reverse the sign for USD fed funds, which jumps
negative at month ends); (3) remove the jump as an exogenous multiplicative factor on all later discount factors;
(4) iterate to the next jump date (Ametrano, Bertocchi & Mazzocchi, SSRN 2881445, 2016).

SOFR is different: a transient jump on one date is invisible in 3M term rates (it hits 1 of about 65 overnight
rates in the window); setting 0.5bp jumps on every month end did not remove the humps in the futures-built curve
(Deriscope blog, 18 Feb 2024).

## 5. Stale-run threshold

Tick `q = 0.01` (percent), daily s.d. `sigma = 0.05`: `p = q/(sigma*sqrt(2*pi)) = 0.0798`; `r >= ln(1e-4)/ln(p) = 3.64`,
so `r = 4` repeats, `min_run = 5` observations (the script's `min_run_for(0.01, 0.05, 1e-4) == 5`; own derivation).
For a series with `sigma = 0.01` (a pinned short rate) `p` is about 0.40 and the same rule gives `min_run = 12`: runs of
5 are normal there.

## 6. Seasonality claim stress-tested

Template (swapsball.net, Testing for seasonality, 19 Nov 2017): about 10 years of daily closes, daily bp changes, drop
roll-window changes, sum into a month-by-year table, trimmed means and medians per month (0/10/25/50% of the largest
moves removed; 50% is the median), two-tailed t-test on means and Wilcoxon signed-rank on medians against the overall,
`alpha = 10%`; compare the number of flags with `alpha x tests`. EUR Bund asset-swap spread, 2007-2017: January
`p = 0.750` (t) and 0.721 (Wilcoxon), September 0.136 and 0.155, so no calendar effect at 10%; the OE-RX box was
significant in January (0.068/0.086) and March (0.058/0.051). Also warned: a non-proprietary composite series (a public
Bund asset-swap index) may compromise the analysis. See
[quant-seasonality-and-calendar-effects](../../quant-seasonality-and-calendar-effects/SKILL.md).

## 7. Fitted-curve basket hygiene (UST par curve)

Low free-float bonds (outstanding minus central-bank holdings minus stripped amount; below about 8bn) were all rich:
-84.3bp at 2.5bn free float, -58.2bp at 2.3bn, -46.8bp at 3.2bn. Excluding them cut the year-to-date average fit RMSE
from 3.8bp to 2bp and its standard deviation from 0.66bp to 0.21bp (versus the legacy curve: RMSE down 2.5bp or 65%, std
down 0.56bp or 85%; legacy 0-2y RMSE 12.4bp last / 23.1bp average against 0.9bp / 1.2bp new). Also excluded: on-the-runs,
olds and double-olds, specials (6M repo at least 25bp below 6M GC) and bonds under 1y. A rising RMSE can be a basket
artefact, not market stress (J.P. Morgan, The (par) curves they are a-changin', 23 Jul 2024).

## 8. Multiplicative vs additive adjustment (equity analogue of futures stitching)

A 2:1 split on 9 Jun 2005 plus nine dividends: the nine multipliers (0.997214 to 0.998618) multiply to 0.976773; with the
split, 0.976773 x 0.5 = 0.488386 applies before 9 Jun 2005 (checked). The 10 Jun 2005 close of 74 becomes 72.28
(74 x 0.976773 = 72.281, checked), matching the vendor's adjusted close. Multipliers preserve historical returns;
subtraction preserves price changes only. The same trade-off applies to continuous futures: ratio adjustment for returns,
additive for rate-like series (Chan, Quantitative Trading, Wiley, 2009, Ch.3).

## 9. Scoring a filter against the last print

Simulation: error measured against the next trade was 0.020 (last trade), 0.0377 (univariate Kalman), 0.0383
(multivariate Kalman); measured against the truth: 0.056, 0.0512, 0.0286. The last trade looks best and is worst.
Serial correlation in trade errors rewards overfit univariate models: evaluate cleaning and fair-value filters against
ground truth (a simulation, or an independent settlement source), not against the next print (Cotton, Filtering bond
and credit default swap markets, NYU Tandon seminar slides, 27 Apr 2016).

## 10. Benchmark percentile monitor (USD funding)

For each published benchmark plot the volume-weighted median with its 1st, 25th, 75th and 99th percentiles. Reading a
widening gap between upper percentiles and the median shows funding-pressure tails the median hides: 23 Aug 2024 SOFR 5.33
with a 99th percentile about 5.44 and a 1st percentile about 5.28; 19 May 2025 99th percentile 4.40 against median
4.33 and 1st 4.28. Segment composition: SOFR = tri-party + GCF + bilateral cleared; BGCR = tri-party + GCF; TGCR =
tri-party only; OBFR = eurodollars + fed funds + domestic deposits; EFFR = fed funds only. On 23 Aug 2024 SOFR 5.33,
TGCR 5.32, all-collateral tri-party 5.24 (below the 5.25 floor), reverse-repo rate 5.30 (Conks, Money Market Updates,
26 Aug 2024 and 19 May 2025). Anomaly signal first, tradable breach second: check the construction.
