# Delivery-option models: formulas and recipes

Companion to [SKILL.md](../SKILL.md). Units: yields pct, shifts and vols bp, prices per 100 face, DV01 in price points per bp.
All models value options owned by the short; the long basis holder is long them.

## 1. Switch (quality) option

**At expiry.** `F_T = min_i (P_i / CF_i)`. Cost of delivery of bond i = `P_i - CF_i x F` (accrued cancels). The CTD maximises
`CF x F - P`. Arbitrage proof: if `F_T > P_CTD/CF` buy the CTD, sell the future, deliver; if lower, short the CTD and buy the future
(Tuckman & Serrat, Fixed Income Securities, 2022).

**Parallel-shift Bachelier map (two-bond).** Under a parallel shift `s` of forward yields, `a_j(s) = a_j(0) - (DV01_j/CF_j) s`; CTD = argmin.
For current CTD `c` and an alternative `alt`: `m = DV01_c/CF_c - DV01_alt/CF_alt`, crossover `s* = (a_c(0) - a_alt(0)) / m`,
payoff to the CTD net basis `NB_c(T) = CF_c |m| max(0, +/-(s - s*))`. `m < 0`: switch on a sell-off (payer-like); `m > 0`: switch on a rally.
Value = Bachelier option on `s` struck at `s*` with slope `CF_c |m|`; can be inverted for an implied switch vol. Valid only when
two bonds dominate (check the number of bonds with >1% delivery probability first).

**One-factor decomposition (Huggins & Schaller, Fixed Income Relative Value Analysis, 2024, Box 7.1).** Map every deliverable's
yield from the CTD yield with regression betas over a range of delivery yields; find inflection points and switch payoffs;
decompose into puts and calls struck at the inflection points; price each with Black-Scholes at the futures-option implied vol
nearest its switch yield (handles skew); sum. Alternative: integrate the payoff over the CTD-yield density from futures options
(not advisable with large skew). Trading NB against futures options is practicable only when the switch is between the short
and long ends of the basket.

**Multi-factor Monte Carlo (Huggins & Schaller, Box 7.2, after an ABN Amro note of Feb 2002).**
1. Level: yield `y1` of a first bond (shortest or CTD), normal vol from futures-option implied vol.
2. Spreads: `y_k - y1` normal with their own vols and a full correlation matrix.
3. Simulate zero-mean to delivery; convert yields to converted prices; add `(forward converted price - mean simulated)` per bond.
4. Per path find the CTD and the switch profit; `DO` = average switch profit (with CFs); `P(CTD_i)` = share of paths.
5. Outputs: fair futures `FwdP_CTD/CF_CTD - DO`; fair calendar roll (repeat for the back contract); OABPV (re-run with yields shifted
   by the PCA first-factor response to +1bp in `y1`); scatter of simulated spread changes coloured by CTD (switch zones).
Inputs: spread vol is the delicate one. Similar bonds only gain "individuality" once they compete for CTD, so take the vol from before
they entered the basket and scale by the average increase into delivery; DO is roughly linear in spread vol through the origin;
correlations are stable and DO is not very sensitive to them. Run several parameter sets. One-factor models undervalue the DO far from the
notional coupon, so market net bases there are systematically too low (JGB: one-factor < 1 sen, multi-factor 7 sen).
Model-arbitrage logic: market NB reflects the average participant model; NB 5c vs your model 2c -> sell the CTD basis; vs 10c -> buy it.

**Burghardt valuation recipe (The Treasury Bond Basis, 3rd ed., 2005, Exh 4.3).** (1) Joint distribution of yield level (reference bond) and slope
(deviation from beta-implied moves). (2) Per cell: find CTD, value the EOM option, set `F = (P_CTD - carry_CTD - EOM)/CF_CTD`, compute every issue's BNOC.
(3) Probability-weighted BNOC is TDOV per issue. `OAB = BNOC - TDOV`; `F_mkt - F_theo = -OAB/CF`. Calibration checks: each issue's model expected forward equals its
market forward; price an ATM futures call off the model and compare implied vol with listed options (works better for 10y and bond than 2y/5y); adjust the
forward for CTD specials; model anticipated new issues (essential for 2y/5y); yield betas vary greatly over time; slope vol does not scale with sqrt(t).
Source note: the printed relation `sigma_y = (y x ModDur) x sigma_p` looks dimensionally inverted - divide, do not multiply, when converting.

**Term-structure tree (Tuckman & Serrat, App. 11).** Futures `F_0 = E[p_n]` (undiscounted risk-neutral expectation; futures price < forward price because bond
prices are negatively correlated with rates). Quality option: at each delivery node `F = min_i(P_i/CF_i)`, roll back with the futures rule.
Timing, EOM, wildcard: at each node `F = min(exercised, not exercised)`. Calibrate each deliverable's spread so its model forward equals the market forward.
Basket yield beta `beta_i` = ratio of yield-change regression slope (one factor: ratio of yield vols).

## 2. Wildcard option

**Mechanics.** Invoice fixed at the futures settle (3pm ET); bonds trade, and notice of intent is accepted, for hours afterwards; exercisable from the first
delivery day to the day before the last trade date. A CF-hedged short holds `1/CF` face per face delivered (CF < 1): after a post-close rally deliver and sell
the tail `(1/CF - 1)`; after a sell-off wait. Cost of exercising = remaining gross basis (carry plus option time value) on the delivered bonds.

**Backward induction (per face delivered, price points).** `x ~ N(0, s^2)` = post-close price move, `k = 1/CF - 1`, `g` = one day of carry.
`W_i = V_{i+1} + g`; exercise iff `k x > W_i` i.e. `x > a_i = W_i/k`; `V_i = k s phi(a_i/s) + Phi(a_i/s) W_i`; `V_{N+1} = 0`. Value = `V_1 - V_1(k=0)`.
`s = (post-close yield sd in bp) x DV01`. Check: `N = 1, g = 0` gives `k s / sqrt(2 pi)`; with carry it is a Bachelier call on `k x` struck at `g`.
Positive carry raises the threshold and favours last-day delivery.

**J.P. Morgan form (per futures notional, Good things come to those who wait, 18 May 2018, appendix).** `x = p - p0`; eve of last trade date exercise iff
`x > x1 = GB(1d)/(1 - C)`; `E1 = (1 - C) { s^2 p(x1) + (x1/2)[1 + erf(x1/(s sqrt 2))] }`; recursion `x_n = (E_{n-1} + GB(1d))/(1 - C)`,
`E_n = (1 - C)[s^2 p(x_n) + (x_n/2){1 + erf(x_n/(s sqrt 2))}]`. Post-close sd typically 1-2bp over the window; baseline 1bp per 2 hours (1-1.5bp/day),
doubled on FOMC days; sensitivities 1.0 / 1.5 / 2.0 with and without an FOMC x2. A positive GB pushes the threshold above zero (exercise odds < 50%); a negative GB exercises slightly out of the money.
The `(1 - C)` vs `(1/CF - 1)` difference is a unit convention (per futures notional vs per face delivered); BofA's dollar example reconciles with the per-face form.
Decision: if the expected payoff is positive on the first delivery date and after, withhold delivery, even at negative carry, until it turns negative or a large post-close move occurs.

**Vendor Black-Scholes-style induction (RiskVal, Future CTD Scenario Analysis user guide, 2024).** Delivery profit `q F_3PM(t) - B_9PM(t)`; with the option
`F(t) = B(t)/q - V(t)`; `X_t = dB(1 - 1/q) + (q - 1) V_3PM(t) + V_3PM(t+1)`; `V(t) = E_3PM[max(X_t, 0)]`; `V(T) = 0` at the last trade date.
Lognormal: `V = (1/q)[lambda B N(d1) - E N(d2)]` for `q > 1`, `(1/q)[lambda B N(-d1) - E N(-d2)]` for `q < 1`; `lambda = 1 - 1/q`,
`E = lambda B + (1 - q) V(t) + V(t+1)`, `d1 = [ln(lambda B/E) + sigma^2/2]/(sigma sqrt T)`, `d2 = d1 - sigma sqrt T`. Inputs: listed futures-option implied vol as one-day vol;
FOMC days x3; wildcard interval 6 hours by default (the document also says 15 and its E formula is inconsistent: verify before reuse).

**Breakeven.** Long-basis wildcard breakeven futures price `F_BE = F + GB/(1 - CF)` (front); back = front BE - calendar roll.
Burghardt's form: `(C - 1)(C F - P) = B` (profit on covering the tail = basis given up); example in the case notes.

## 3. End-of-month (last-week) option
After the last trade date the final settlement `F_s` is fixed. Net cost of delivery `= Cash - CF x F_s - carry`. Re-weight the hedge to 1:1 face. A long-basis holder of
bond i switches to j if `P_i - CF_i F_s > P_j - CF_j F_s`. BPV (absolute price sensitivity), not duration, decides: a yield rise that makes high-duration bonds cheap
before expiry makes high-BPV (high-coupon) bonds cheap afterwards. Crossover shift = BNOC gap / BPV gap (in 32nds per bp). Payoff = long strangle costing the CTD BNOC at the
close. Needs 2+ close contenders and vol; can be exercised repeatedly. Value with the annual normal vol from ATM futures options in a switch-like model with the futures price frozen.
Counterpoint: often worth little because the window is short and basis traders buy any bond that cheapens. A minor option between notice and nomination lasts under a day and is worth almost nothing.

## 4. Option-adjusted DV01
Schedule of theoretical (option-adjusted) futures prices across yield shifts, then central differences (Burghardt 2005): at 104.250 base, 105.531 at -10bp, 103.000 at +10bp the base DV01 is
$128.10 down, $125.00 up, mean $126.55 per contract, ~10% fewer 10y contracts than the rule of thumb. Rule of thumb `DV01_fut = fwd DV01_CTD / CF_CTD` jumps at crossovers
("a 1bp change can produce enormous changes in hedge ratios"); P-weighted `DV01/CF` is the smooth version; OABPV (Huggins & Schaller) is the multi-factor version.
Do not compute a stand-alone modified duration for a future (no market value).

## 5. PCA-based delivery probability (vendor-style)
PCA on ~3y of daily swap-rate changes; simulate forward yields to the last delivery date with the first (parallel) factor scaled to ATM implied normal vol (listed futures option, else swaption);
Gauss-Hermite quadrature for scenarios/probabilities; outputs P(delivery) per bond and the rally/sell-off (sd or bp) needed for a switch. Scenario futures price by the zero-NB rule
`F_bumped = min_i(bumped forward_i / CF_i)` or adjusted by the market-implied option value `MIOV = current 0-NB futures price - current futures price`:
`F_bumped = min(bumped forward / CF - MIOV)`. PC1/PC2 variant: shock level and slope +/-4 sd, repo = interpolated overnight benchmark + spread, futures DV01 probability-weighted across potential CTDs
(Morgan Stanley, Buy Higher Rates Protection at a 30% Discount, 27 Aug 2026).

## 6. Replicating the switch option with swaptions (Morgan Stanley, 27 Aug 2026)
Replicate short 1 future with short CTD-in-rally bond (CF-sized) plus payer swaptions fitted to the residual payoff across instantaneous shocks (expiry = last delivery date, swap matching the bond).
Swaption premium = value of embedded sell-off convexity; compare with net basis; if the basis is cheaper, buy basis and sell the replicating put. Caveats: valuation not a static hedge, leaves swap-spread risk,
swaption theta decays while the switch payoff does not (may understate value), residual grows as the contract converges to one CTD. Empirical DV01 (regression of futures changes on basket yield changes) vs CTD-scenario durations gauges how much switch risk is priced.

## 7. Delivery-day choice with options
IRR is a lower bound on cash-and-carry return: the switch option adds return (swap the old CTD for the new), and so does timing (inversion lets you deliver early and reinvest; steepening from inversion lets you deliver late).
Early-delivery valuation: `E[F] = P(early) E[P/CF at early date] + P(late) E[F at LTD]`; with negative carry and low vol the short delivers day one, with high vol it waits. Two further reasons to deliver early with positive carry:
monetising the quality option's time value, and repo-fail risk. Classification used in studies: early = within 3 business days of the first delivery date, late = within 3 of the last, mid otherwise.
