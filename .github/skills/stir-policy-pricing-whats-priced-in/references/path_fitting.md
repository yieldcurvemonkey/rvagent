# Fitting the meeting-date path: formulas, regularisation, derivations

Detail behind Method steps 2-3 of [SKILL.md](../SKILL.md). Units: rates in percent, jumps in bp unless stated.
Curve-building generalities (interpolation, multi-curve, turns) live in
[fi-curve-construction](../../fi-curve-construction/SKILL.md). This file is only what policy pricing needs.

## 1. Step-function forward (Heitfield-Park)
Overnight forward f(t) = θ0 + Σ_k θk · 1{t >= E_k}, E_k = k-th EFFECTIVE date after the as-of date, θ0 = rate in force
from as-of+1, θk = jump at meeting k. Chosen over smooth curves because overnight RFRs sit in narrow bands and jump on
policy dates; it fits well inside 1y (Federal Reserve Board, Inferring Term Rates from SOFR Futures Prices, FEDS 2019-014, Feb 2019).

| Contract | Model RATE in percent (fixing known to day t0, forecast after); futures price = 100 - rate |
|---|---|
| 1M average (monthly) | `(1/N) [ sum_{t<=t0} r_t + sum_{t>t0} f(t) ]`, arithmetic over CALENDAR days, weekends/holidays take the last business-day fixing |
| 3M compounded | `(360/N) [ prod_t (1 + r_t d_t/360) - 1 ]` with `r_t` = fixing if known, `f(t)` if not, d_t = calendar days until the next business day, N = days in period |
| Term rate h(T) | `(360/T) [ prod_{business days} (1 + f(t) d_t/360) - 1 ]`, ACT/360, accrual from the next business day |

- Estimator: minimise squared price error over all 1M contracts plus the 3 nearest 3M contracts (equal weights;
  volume weights optional) plus a tiny ridge on the jumps (FEDS 2019-014).
- Policy gradualism: when two meetings sit inside one contract window the data cannot split them; choose the split
  that minimises the largest jump (two equal moves rather than one big one). L2 ridge is the cheap stand-in
  (`scripts/meeting_path.py` uses it).
- Ignore jumps more than ~6 months out: far meetings are not scheduled and far contracts are thin (same source); the script
  also drops contracts that start beyond that horizon, otherwise unmodelled far meetings bias the level theta0.
  Beyond that use a hybrid: steps at the front, smooth spline behind. Meeting dates are firm for ~1y, provisional
  for the 2nd year, estimated for the 3rd (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022).
- Fit, do not bootstrap: with 8 meetings a year but 4 quarterly 3M contracts the system is under-identified, and
  bootstrapped back contracts oscillate. Fit by least squares with a smoothness penalty on the forwards
  `sum (f_{i-1} - 2 f_i + f_{i+1})^2`; read oscillation in an unpenalised fit as noise, not policy reversals
  (Huggins & Schaller, SOFR Futures and Options, 2022).
- Regularise with low-weight pseudo-instruments instead of black-box ridge: butterflies across successive
  meeting periods priced at 0, weight 1e-8 versus 1.0 for market instruments (minimum curvature). Worked case:
  ECB effective dates 31-Jan-2024, 7 instruments, 10 d.o.f., 3 flies added, converged in 6 Gauss-Newton iterations,
  monotone step path from ~3.9% to ~2.3% (Darbyshire, Coding Interest Rates, c.2024). Without flies the solve
  "will succeed but the values are unconstrained".
- Solver: Gauss-Newton from yesterday's curve (converges in single or low double-digit iterations); Levenberg-Marquardt
  only from a poor start (lambda0 = 1000, quarter on success, double on failure).
- Number of IMM futures as inputs: 8 for small currencies, 12 for the most liquid, never more; avoid the 6th, 7th,
  10th, 11th and 14th contracts (roll and leverage effects) (Darbyshire, 3rd ed., 2022).
- CME-style published Term SOFR smoothing lambda = 1/sqrt(#FOMC) ~ 0.33 adds ~0.5bp to 6M term (27-Jan-2022) and
  may bias it up: do not use a published term rate as the "market path" without checking (Huggins & Schaller, 2022).

## 2. Contract sensitivities to a meeting (USD examples; same logic everywhere)
- 1M average contract in the meeting month: sensitivity to a move J at the meeting = `J * (calendar days after
  effective date) / (days in month)`. 25bp on 4-May-2022 (effective 5 May) moves the May contract 25 x 27/31 = 21.8bp
  (Huggins & Schaller, 2022).
- 3M compounded contract: bump all post-meeting fixings by J and reprice (compounding makes it level dependent).
  Same meeting moves the March-2022 3M contract 11.3bp (same source).
- FOMC-neutral 1M/3M hedge: `n_1M(meeting month) = s_jump / ((d_post/d_total) x 41.67)` neutralises the jump, then
  `n_1M(prior month) = s_level/41.67 - n_1M(meeting month)` neutralises the level. Off-centre meetings need more of
  the later contract than the standard 3+3 : 10 ratio (same source: 3.1 May + 2.9 Apr 1M per 10 3M).
- Averaging vs compounding gap: arithmetic `dR/dr_k = d_k/D`; compounded `dR/dr_k = prod_{i!=k}(1 + d_i r_i/360) d_k/D`.
  Sensitivity gap on a 1M window <= ~0.1bp at 2021-22 rates, ~1bp near 5%. On the LEVEL, compounding over a window of T years
  adds ~ r^2 T/2 to the simple rate: 3M ~0.1bp at 1% but ~3bp at 5% (the 3M-minus-1M futures gap is ~3bp at a constant 5%). Compounded 1y at constant SOFR 100/300/500bp = 101/305/513bp.
  Adjust when comparable to the bid-offer (same source). Hand off to
  [stir-rfr-compounding-and-fixing-risk](../../stir-rfr-compounding-and-fixing-risk/SKILL.md).
- Known fixings inside the front 3M contract: `R_unknown = [(R x D/360/100 + 1) / prod_known(1 + SOFR_i d_i/360) - 1] x 360/D_unknown x 100`.
  The in-period contract is "sticky": it responds less to expectations as fixings accrue (2019: the front contract
  stayed high while cuts were priced into the back).

## 3. Separating FOMC steps from a year-end premium (monthly average contracts)
With dDec, dJan the moves at the 11-Dec-2019 and 29-Jan-2020 meetings (effective 12-Dec, 30-Jan) and YE the excess
of the average over 12/12-12/31 versus 1/1-1/29 (Citi Research, US Rates Weekly: Fixing the plumbing, 30 Sep 2019):
```
FF_Dec = (11/31) FF_Nov + (20/31)(FF_Nov + dDec + YE)
FF_Jan = (29/31)(FF_Nov + dDec) + (2/31)(FF_Nov + dDec + dJan)
FF_Feb = FF_Nov + dDec + dJan
dDec = -FF_Nov + (31/29) FF_Jan - (2/29) FF_Feb
dJan = -(31/29) FF_Jan + (31/29) FF_Feb
YE   = -(11/20) FF_Nov + (31/20) FF_Dec - (31/29) FF_Jan + (2/29) FF_Feb
```
The YE weights form a package with turn exposure and no meeting exposure (DV01 -55K / +155K / -106K / +7K across
Nov/Dec/Jan/Feb gave 100K YE and zero FOMC; market-implied YE drop -4.5bp versus the largest historical -2.65bp).
General method: write each contract as day-weighted meeting steps plus turn premium, invert. `meeting_path.py`
solves the meeting part exactly (selftest case 4 reproduces the dDec formula).

## 4. Meeting-dated OIS bootstrap (Pulman 2007)
Assume one meeting per month so the m-th monthly OIS maps to the m-th meeting. With R the OIS rate, t0 start,
t1 meeting (effective), T1 maturity, D the day basis:
```
(1 + R (T1 - t0)/D) = (1 + r0/D)^(t1 - t0) * (1 + r1/D)^(T1 - t1)
r1 = D * [ ((1 + R (T1 - t0)/D) / (1 + r0/D)^(t1 - t0))^(1/(T1 - t1)) - 1 ]
```
Recurse out to ~6M. `bootstrap_next_rate` in the script implements it (Lehman Brothers, The Short-End of the
Curve, 10 Jul 2007). Add a daily funding spread s to r if the OIS index trades off the policy rate; the output is the
"1D central-bank forward curve", constant between meetings.
- Forward-stub trick (EONIA 2-Feb-2016): a plain bootstrap loses the information in (meeting start, next spot OIS
  end). Insert a forward-starting stub from the last non-overlapping spot OIS maturity to the meeting start, flat
  at the first meeting-OIS level beyond. Without it the calibrator pushed the curve to ~-0.40% to reprice the
  first meeting OIS; with it the excluded 2M OIS reprices exactly (Ametrano, Bertocchi & Mazzocchi, Advanced Eonia
  Curve Calibration, SSRN, 5 Dec 2016). The spot-vs-forward overlap matters exactly when a meeting OIS prices a move.
- Turn/month-end jump removal before interpolating: put an out-of-line segment back in line, move the difference
  into a jump `JSize = [F_orig - F_interp] x tau(t1,t2)/tau_J` (USD month-end jumps are negative: flip the sign),
  strip it as a multiplicative factor on later discount factors; otherwise smooth interpolation smears the turn
  into the neighbouring meeting (same source).
- Interpolation: backward-flat forwards with nodes on meeting dates; any other scheme smears steps. GBP check
  (21-Nov-2022): implied overnight 2.9248% until 14-Dec-2022 then 3.5029% from 15-Dec = a 57.8bp December hike;
  implied-minus-market spot OIS differences mostly <0.5bp (Deriscope, Yield Curve Building ... The GBP Sonia case, 18 Feb 2024).
  Repeat a spot-vs-forward OIS discrepancy over several snaps before claiming it: single snapshots show liquidity
  and stale-feed gaps.
- Mixed interpolation: flat forwards (log-linear DF) to the end of the meeting-dated strip (~2y), monotone cubic
  beyond; monotone cubic everywhere gave higher repricing error on every excluded instrument (Ametrano et al. 2016).

## 5. Cash-vs-policy adjustments before reading the path
1. Policy-to-RFR spread: ECB policy rate is a repo-type rate, overnight RFR trades below it under excess liquidity
   (EUR: add ~6-10bp to a euro short-rate path to get the deposit rate; "add 10bp" in Jan-2024, stub 6bp below the
   2.25% rate in Aug-2026: Nordea Markets, EUR rates: Pushing back, 17 Jan 2024; Citi Markets, G10 What's Priced In,
   14 Aug 2026). Re-estimate the spread when reserves regime changes.
2. Do not infer a path from IBOR futures with a fixed 10-15bp IBOR-OIS assumption (Lehman 2007); use OIS.
3. Turns: strip year-end (and Japan 1-April) turns before reading policy; turn size differs across unsecured, repo
   and OIS; the premium is "customarily priced but rarely realised" (Y2K turn +45bp intraday then collapsed).
4. Convexity: futures versus FRA/OIS bias grows with sigma^2 t^2; negligible for the first 1-2 contracts, a few bp
   by 3y ([stir-convexity-adjustment](../../stir-convexity-adjustment/SKILL.md)).
5. Funding seasonals around meetings: in a hiking cycle banks pre-fund reserves and the effective rate creeps up
   before FOMC, falls after (reverse when cutting); ECB MRO-maturity Tuesday averaged ~30bp below the refi rate
   (Lehman 2007). Tax dates and settlement days move the effective rate off target
   ([stir-repo-and-funding-plumbing](../../stir-repo-and-funding-plumbing/SKILL.md)).
6. Jump models fail for unscheduled meetings (2001, 2008, Mar-2020) and give zero value to every OTM option expiring
   before the next meeting; options need diffusion (Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).
   Daily-floor premium over a whole-period floor under pure jumps: 44% (one meeting, +25/0/-25 at 1/3 each),
   72% with an unscheduled meeting, so over-hedge ~10% when diffusion is present (Huggins & Schaller, 2022).

## 6. Hand-offs
Option-implied meeting distributions (call-spread digitals, Breeden-Litzenberger, normal-mixture weights):
[stir-options-implied-distributions](../../stir-options-implied-distributions/SKILL.md). Rhetoric overlays:
[macro-central-bank-nlp](../../macro-central-bank-nlp/SKILL.md).
