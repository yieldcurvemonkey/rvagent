# Break, change-point and explosiveness tests: formulas and settings

Detail for [quant-regime-detection](../SKILL.md). T = number of observations, k = number of regressors.

## Known break date

**Chow F** (Greene, Econometric Analysis, 8th ed., 6.6.1). Fit the pooled regression (SSR S*) and one regression per
sub-period (S1, S2):

    F = [(S* - S1 - S2) / k] / [(S1 + S2) / (T - 2k)]  ~  F(k, T - 2k)

Greene's example: gasoline demand 1953-73 vs 1974-2004, F[6, 40] = 67.645 against a 5% critical value of 2.336, so
equal coefficients are rejected. The test assumes equal error variances in both regimes. Rates regimes usually
break the variance as well, and then the true size is above nominal.

**Wald test with unequal variances** (Greene 6.6.2): fit each sub-period separately.

    W = (b1 - b2)' (V1 + V2)^-1 (b1 - b2)  ~  chi2(k)   (large samples)

Use HAC (Newey-West) for V1 and V2 when the regression is on overlapping or serially correlated changes. The
lag is about T^(1/4) for non-overlapping daily changes, but at least h - 1 for h-day overlapping changes (e.g. ≥ 20
for 21-day changes), or use non-overlapping changes. In Tsay's 1y/3y UST example, naive t = 107.9 shrank to 39.9 with HAC.

## Unknown single break

**sup-F (Quandt-Andrews).** Compute the Chow F at every candidate date in [tau0·T, (1 - tau0)·T] and take the
maximum. Trim with tau0 = 0.15 so both regimes have data. Critical values come from Andrews (1993), not from F
tables. A sup-F above the 5% Andrews value means a break somewhere. The arg-max is the break-date estimate, and its
confidence band is wide when the shift is small relative to the residual sd.

**Chow-type Dickey-Fuller (SDFC)** (López de Prado, AFML, Ch.17): fit Δy_t = δ·y_{t-1}·D_t[τ*] + ε_t, where D = 1
after τ*·T, and take the sup over τ* of δ̂/σ̂_δ. It tests a switch from a random walk to explosive behaviour. It
allows one break only and assumes the bubble runs to the end of the sample.

## Multiple unknown breaks (Bai & Perron 2003)

- Model: y_t = x_t' β_j + u_t for t in regime j = 1..m+1. Breaks minimise the total SSR over all partitions.
  Dynamic programming finds the global minimum in O(T²) SSR evaluations (`find_breaks` in
  [regimes.py](../scripts/regimes.py)).
- Minimum regime length h = ε·T. ε = 0.15 is the usual default; 0.05-0.25 is allowed. Bai-Perron critical values
  depend on ε. A break cannot be dated in the last h observations of the sample.
- Choosing m: sequential sup-F(ℓ+1 | ℓ), or an information criterion. The script uses
  BIC(m) = T·ln(SSR_m / T) + [(m+1)k + m]·ln T. BIC assumes roughly iid errors. On persistent levels, such as a fly
  with an AR(1) coefficient of 0.95, it picks spurious breaks. Fit y_t = c + φ·y_{t-1} per regime instead (the
  script's default for levels) and read the equilibrium as μ = c / (1 - φ). On a simulated persistent fly
  (φ = 0.95, innovation sd 1bp, one equilibrium shift at obs 600 of 1500; illustrative, own simulation), raw-level
  BIC chose 3-4 breaks in every seed. The AR(1) form found the single break in 6 of 10 seeds for a 6bp shift and
  in 10 of 10 for a 10bp shift (dated within about 40 obs), and a spurious break in 1 of 10 random walks. A shift
  below about 2 unconditional sd (σ/√(1 - φ²) ≈ 3.2bp here) is hard to detect, so absence of a break is weak
  evidence.
- Tuckman's setup (Lehman, Macro-Awareness in Relative Value Trading, Oct 2003): Δ5y swap regressed on the
  Δ(3rd Eurodollar contract), Δ2y and Δ10y swap rates, about 10 years of data, every coefficient switching. Leaving
  out the short-end regressor gives qualitatively similar but larger shifts.

## Online alarms

**CUSUM filter** (AFML Ch.2; event sampler):

    S+_t = max(0, S+_{t-1} + y_t - E_{t-1}[y_t]),   S-_t = min(0, S-_{t-1} + y_t - E_{t-1}[y_t])

An event fires when S+ ≥ h or S- ≤ -h, and the sum then resets. With E_{t-1}[y_t] = y_{t-1}, it accumulates daily
changes. A level hovering near the threshold does not fire repeatedly; a full run of size h is needed. AFML's
exercises use h = 1 × the daily sd (Ex. 3.1) and h = 2 × the sd (Ex. 5.6). The default here is 2 × the trailing
daily sd of changes. An event is a prompt to re-test the regime, not a break in itself.

**Brown-Durbin-Evans CUSUM on recursive residuals** (AFML Ch.17). Fit recursive least squares and standardise the
1-step-ahead errors: w_t = (y_t - b'_{t-1} x_t) / sqrt(f_t), with f_t = σ²[1 + x_t'(X_t'X_t)^-1 x_t].
S_t = Σ_{j=k+1..t} w_j / σ̂_w. Under no change, S_t ~ N(0, t-k-1). The result depends on the arbitrary start point.

**Chu-Stinchcombe-White CUSUM on levels** (AFML Ch.17):

    S_{n,t} = (y_t - y_n) / (σ̂_t·sqrt(t - n)),   σ̂²_t = (t-1)^-1 Σ_{i=2..t} (Δy_i)²

The one-sided 5% critical value is c(n, t) = sqrt(4.6 + ln(t - n)). Take sup_n S_{n,t} over all reference points n,
so the result does not hang on an arbitrary reference. It flags a spread that has run further than a random walk
should since some past date. For an RV spread, that means the trend has taken over from mean reversion. The test
is one-sided (upward runs). A spread can trend either way, so also run it on -y, i.e. test sup_n |S_{n,t}|. Each
side at b = 4.6 is a 5% test, so the two-sided size is about 10%.

## Explosiveness

**SADF** (Phillips, Wu & Yu 2011 (external); AFML Ch.17): fit
Δy_t = α + β·y_{t-1} + Σ_{l=1..L} γ_l Δy_{t-l} + ε_t on every window [t0, t] with t0 ≤ t - τ, and set
SADF_t = sup_{t0} β̂/σ̂_β. H1 is β > 0, explosive. AFML uses log prices. For rate spreads that can be zero or
negative, use levels in bp and say so. The cost is O(T²) ADF fits per series. The supremum is sensitive to
outliers. QADF (the q = 0.95 quantile of the ADF sequence) and CADF (the tail mean above that quantile) are robust
alternatives.

**Sub/super-martingale tests**: e.g. y_t = α + γt + βt² + ε. Take sup_{t0} |β̂| / (σ̂_β·(t - t0)^φ) with
φ in [0, 1]. φ = 0.5 offsets the shrinking standard error of long windows. A small φ favours long trends; a large
φ favours short bursts.

## Threshold models (a regime set by an observed variable)

- **TAR / SETAR** (Tsay, Analysis of Financial Time Series, 3rd ed., 4.1.2): the AR coefficients depend on whether
  x_{t-d} is above or below a threshold. Example: x_t = -1.5·x_{t-1} + a_t if x_{t-1} < 0, else 0.5·x_{t-1} + a_t.
  Use it when the regime variable is observable, e.g. the spread beyond a cost band.
- **Threshold cointegration** (Tsay 8.7): error correction is significant only outside a band (γ1, γ2). In the
  S&P futures-cash example, γ̂1 = -0.0226 and γ̂2 = 0.0377 (units of 100 × log basis). The t-stats are 10.47 and 9.75
  in the outer regimes and insignificant inside. The rates analogue is a basis or spread that reverts only once it
  exceeds transaction cost plus risk.

## HMM decoding and an example

- Forward: F_n(j) = p(s_n | j)·Σ_i F_{n-1}(i)·P_ij. Filtered P(X_n = j | s^n) = F_n(j) / Σ_i F_n(i). The backward
  pass gives smoothed probabilities. Viterbi (V_k(j) = p(s_k | j)·max_i P_ij·V_{k-1}(i), then backtrack) gives the
  single most likely path. The per-date mode of the smoothed probabilities maximises the expected number of
  correctly labelled dates. The two can disagree, so pick the objective deliberately (Ross, Introduction to
  Probability Models, 10th ed., 4.11).
- Ross Ex. 4.43: two states, P_11 = 0.9, an absorbing "bad" state, p(a|good) = 0.99, p(a|bad) = 0.96, prior 0.8,
  signals a, u, a. P(good at 3 | signals) ≈ 0.364, and P(good at 4) = 0.3276. One unusual observation sharply cuts
  the good-state probability. Hamilton makes the same point: an outlier makes the filter switch to the other
  regime's forecasting rule.
- Choosing the number of states: the likelihood-ratio χ² test of K vs K-1 states is invalid, because the extra
  state's parameters are unidentified under the null. Use Hansen (1993), Davies (1977) or Andrews-Ploberger (1992)
  type tests, or take the K-1 model as the null and run specification tests (Hamilton, Time Series Analysis, 22.4).
- The mixture likelihood has no global maximum: it is unbounded as μ_j → some y_t with σ_j → 0. Floor the
  variances, or use Hamilton's (1991) prior-penalised objective, and restart from several starting values.
