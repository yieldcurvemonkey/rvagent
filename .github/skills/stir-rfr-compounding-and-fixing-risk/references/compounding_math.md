# Compounding math: identities, spread methods, approximations, worked loan examples

Companion to the main skill. Notation: N notional; d_i day-count fraction of fixing i (days_i / B); d = sum d_i period DCF; r_i daily rate (decimal);
rbar geometric-average daily rate; dbar DCF of one day (1/360 or 1/365); ntilde calendar days in the period; v discount factor.
Source for sections 1-3: Darbyshire, Coding Interest Rates (companion treatise, c.2024), s6.4-6.6, 8.4.4, 8.8.1-8.8.2.

## 1. Index and discount-factor identities
- `1 + r*d = prod_i (1 + d_i r_i) = I(end)/I(start) = v_start/v_end`, so `r = (v_start/v_end - 1)/d` and `I(m) = I_base * v_0 / v(m)`. Holds only for fixed-denominator
  day counts (ACT/360, ACT/365F); 30E/360-type rules break it.
- Example: index 100.0 on 1-Jan-2022 and 5% compounded SOFR over the year gives 105.0 on 1-Jan-2023.
- Forward from two DFs: `f = (Z(t0)/Z(t1) - 1)/delta` (Gunstensen, MIT OpenCourseWare 18.642 Lecture 7, 26 Sep 2024).
- Method efficiency on a DF-based curve: payment delay and observation shift are DF-only (fast); lockout is semi-efficient; lookback, averaging and ISDA spread variants need all
  ~252 daily fixings of a year and are an order of magnitude slower, so use the approximations below only when the tolerance allows.

## 2. Spread z over compounded RFR (cash recursion)
- **None-simple (spread after compounding):** `C_total = sum C_i + N d z`, `C_i = (N + sum_{j<i} C_j) r_i d_i`; `R = (prod(1 + r_i d_i) - 1)/d + z`; dR/dz = 1.
- **ISDA compounding (spread inside each step):** `C_i = (N + sum_{j<i} C_j)(r_i + z) d_i`; `R = (prod(1 + (r_i + z) d_i) - 1)/d`.
  Equal-rate approximation `R ~ ((1 + (rbar + z) dbar)^ntilde - 1)/(ntilde dbar)`, `dR/dz ~ (1 + (rbar + z) dbar)^(ntilde-1)`.
- **ISDA flat compounding (spread earns interest only through the rates):** `c_i = (r_i + z) d_i + r_i d_i sum_{j<i} c_j`, `R = (1/d) sum c_i`; no closed form, dR/dz > 1 for positive
  rates; the source says to avoid it.
- **Averaging:** `R = sum d_j r_j / sum d_j + z`, `dR/dr_i = d_i / sum d_j`; only the none-simple spread is allowed with averaging.
- **Fast approximation of dR/dr_i** (equal calendar-day fixings): none-simple `(1/ntilde)(1 + rbar dbar)^(ntilde-1)`; ISDA compounding `(1/ntilde)(1 + (rbar + z) dbar)^(ntilde-1)`.
  Table 8.5 of the source: approximation error on the 4-Feb fixing 1,000,336 vs exact 1,000,112 per 1mm; lookback 1-Feb 2,999,329 vs exact 2,998,658.
- Typo to avoid: the printed `d = (sum d_i)^-1` must be `d = sum d_i`.

## 3. Fixing-notional derivation
- Single fixing: `P_i = N_i d_i r_i v_i(m_i)`, `dP_i/dr_i = N_i d_i v_i` with the TRUE DCF of that day (not the lookback-shifted one).
- Multi-fixing period: `N_i = N (d v)/(d_i v_i) * dR/dr_i`, d the settlement-period DCF. The fully total derivative (DFs also depend on fixings) differs negligibly, so the partial form is used.
- Standardisation example: USD 10/bp on a 3-day weekend fixing, DF 1, ACT/365F: `N_i = 10 x 10,000 x 365/3 = USD 12,166,667`.

## 4. Payment-lag convexity (HJM one-factor)
A note paying at t3 the compounded rate over [t1, t2] has value `P(0,t3) P(0,t1)/P(0,t2) * beta`, `beta = exp(int_0^{t1} (nu(s,t2) - nu(s,t1))(nu(s,t2) - nu(s,t3)) ds)`.
With Hull-White `nu(s,t) = (1 - e^{-a(t-s)}) sigma/a` this evaluates to `ln beta = sigma^2/(2a^3) (e^{2a t1} - 1)(e^{-a t1} - e^{-a t2})(e^{-a t3} - e^{-a t2})`
(derived here from the integral; the printed closed form in the digest did not reproduce it). No lag (t2 = t3) gives beta = 1; for 0-2 day lags the effect is negligible
(Henrard, OIS and Floored Compounded Instrument in HJM One-Factor Model, BIS working paper, 3 Feb 2004).
Floored compounded RFR (payoff max(K, N_T), N_t compounded balance, sigma^2 = int_t^T nu^2(s,T) ds, kappa = (ln(N_t/(K P(t,T))) + sigma^2/2)/sigma):
`F_t = N_t Phi(kappa) + K P(t,T) Phi(sigma - kappa)`; the cap-side is `N_t Phi(-kappa) + K P(t,T) Phi(kappa - sigma)`.

## 5. Loan conventions on USD 1mm over 31 days (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022, s12.1 Fig 12.1)
| Convention | Rate | Interest |
|---|---|---|
| Term rate set in advance, paid in arrears | 0.07525% x 31/360 | USD 64.80 |
| Overnight set in arrears, daily compounded (3 days at 3bp, 1 at 4bp, 27 at 5bp) | compounded | USD 41.11 |
| Overnight set in advance (5bp for the whole month) | 0.05% x 31/360 | USD 43.06 |
The compounded-in-arrears figure is below the in-advance figure because the early days were set lower; the book prints an exponent typo in the compounded line.

## 6. Term SOFR hedge stress (Huggins & Schaller, SOFR Futures and Options, Wiley 2022, Ch.8)
2y USD 100m loan paying forward Term SOFR, forward payment USD 136,992.80 at 0.54850%. All forwards after 16-Mar-22 +25bp: payment 200,256.20 (+63,263.40) against a futures hedge gain
62,830.08, miss 433.32 (about 0.7%). -40bp: payment change -101,167.61 vs hedge -99,739.44 (about 1.4%). The source prints a forward of 0.54195% elsewhere, so reproduce rather than
quote the base payment. The hedge is local; re-estimate the central-difference sensitivities after large moves.
