# Optimal entry / exit under OU (Leung and Li) and the repeated-trading alternative

Detail behind the "Entry and exit levels" step of [SKILL.md](../SKILL.md). Implementation: `leung_li_levels` and
`optimal_symmetric_band` in [`scripts/ou_fit.py`](../scripts/ou_fit.py).

## 1. Problem statement (one-shot, long the spread)

Spread value X follows dX = mu (theta - X) dt + sigma dB (mu = speed, theta = mean). The trader buys once, sells once,
discounts at rate r (an impatience / opportunity-cost rate, same time unit as mu) and pays costs c_b (entry), c_s (exit).

- Exit: V(x) = sup_tau E_x[ e^(-r tau) (X_tau - c_s) ].
- Entry: J(x) = sup_nu E_x[ e^(-r nu) (V(X_nu) - X_nu - c_b) ].
- Let c = sqrt(2 mu / sigma^2). Fundamental solutions of (sigma^2/2) u'' + mu (theta - x) u' = r u:
  - F(x) = int_0^inf u^(r/mu - 1) exp( c (x - theta) u - u^2/2 ) du (increasing)
  - G(x) = int_0^inf u^(r/mu - 1) exp( c (theta - x) u - u^2/2 ) du (decreasing)
- Exit level b*: F(b) = (b - c_s) F'(b), with b* >= max(c_s, L*), L* = (mu theta + r c_s)/(mu + r).
  V(x) = (b* - c_s) F(x)/F(b*) for x < b*, else x - c_s. Sell the first time X reaches b* from below.
- Entry level d*: G(d) (V'(d) - 1) = G'(d) (V(d) - d - c_b). Buy the first time X falls to d* from above.
  If no root exists (sup of V - x - c_b is not positive) never enter.
- First-passage Laplace transform: E_x[e^(-r tau_k)] = F(x)/F(k) for x <= k (G(x)/G(k) for x >= k).
- Brownian limit (mu = 0): b* = c_s + sigma / sqrt(2 r).
- Short side: apply everything to -X.

(Leung and Li, Optimal Mean Reversion Trading, 2016, ch.2.)

## 2. Comparative statics (all from the book; use as sanity checks)

- Faster reversion (higher mu) gives a narrower buy-sell band ("the faster the speed of mean reversion, the closer the buy
  and sell levels"). Higher sigma gives a wider band. Higher c_b lowers the entry level; higher c_s raises the exit level
  and also lowers the entry level. The one-shot exit level does not depend on c_b.
- Switching (repeat round trips) thresholds sit inside the one-shot thresholds: each round trip earns less, aggregate is larger.
  Switching levels are more parameter-sensitive. Match the formulation to how the strategy is actually run.
- A minimum holding period lowers the optimal entry level.
- Translation: for a spread, demean first (theta = 0) and read X as the mark-to-market value of the position. The discounted
  payoff treats X as an asset price, so the levels are not translation-invariant in a rates spread with theta far from 0.

## 3. Numbers

| Case | Inputs | Result | Source / check |
|---|---|---|---|
| Exit level | theta 0, mu 8, sigma 0.3, r 0.05, c_s = c_b = 0.02 | b* = 0.198 (script: 0.1984), d* = -0.180 (script) | Book charts show roughly +/-0.17 to 0.2 for these inputs; 0.198, 0.068, 0.329 for sigma 0.3/0.1/0.5 were recomputed by a reader from the exit equation and are reproduced by the script |
| Sigma sweep | sigma 0.1 / 0.3 / 0.5 | b* = 0.068 / 0.198 / 0.329 | as above |
| Two-barrier / stop-loss example | theta 0.5388, mu 16.6677, sigma 0.1599, r 0.05 | L = 0.4834 = theta - 2 sd_eq (sd_eq = 0.0277); printed d_L* 0.4978, b_L* 0.5570 | cost printed as 0.05 gives c_s + c_b > b - d, which implies no entry: treat the printed levels as illustrative and re-derive |
| XOU (log-price OU) | mu 0.8, sigma 0.2, theta 1, r 0.05, c 0.02 | one-shot enter <= 2.1754 / exit >= 3.0988; switching enter <= 2.3888 / exit >= 2.8323 | switching band is inside one-shot band |
| Fit check | 200 daily obs, dt 1/252 | simulated re-estimate of mu was about 14% below the empirical mu in both pairs | small-sample bias in the speed; mu is the least reliable input to the band |

(All Leung and Li, 2016.) Rates-spread illustration computed with the script (theta 0, half-life 11 days, sigma_eq 2.33 bp,
costs 0.25 bp each way): with r = 0.0005 per day the one-shot levels are b* = +5.9 bp and d* = -5.3 bp (about +/-2.3 to
2.5 sigma_eq); with r = 0.005 per day they shrink to about +/-1.5 to 1.8 sigma_eq. The Bertram repeated-trading optimum for the
same inputs and 0.5 bp round-trip cost is only +/-0.71 sigma_eq. One shot = wait for the best price; repeated = recycle capital.

## 4. Stop-loss, switching, CIR (formulas, not coded)

- Stop-loss L: the entry region is a band [a_L*, d_L*] strictly above L and below b_L*; a stop lowers the take-profit level
  (b_L* < b*); if L >= L* liquidate at once; if sup(V_L - x - c_b) <= 0 never enter. Do not enter when the spread is "very
  cheap" but close to the stop: it is optimal to wait.
- Switching (infinite round trips): value pair from min{r J~ - L J~, J~ - (V~ - c_b)} = 0 and min{r V~ - L V~, V~ - (J~ + c_s)} = 0.
  Solved as a 2x2 (or, with stop-loss, 8-equation) system; use the book's numerical scheme.
- Carry: a constant holding penalty q maps to exit cost c_s - q/r and entry cost c_b + q/r (reading q as negative carry is an
  interpretation).
- CIR (positive, level-dependent vol): dY = mu (theta - Y) dt + sigma sqrt(Y) dB; Feller 2 mu theta >= sigma^2 keeps 0
  unreachable. F is Kummer M(r/mu, 2 mu theta/sigma^2; 2 mu y/sigma^2), G is Tricomi U. Constants y_b = (mu theta - r c_b)/(mu + r),
  y_s = (mu theta + r c_s)/(mu + r) do not depend on sigma. If y_b <= 0 never enter.
- Valuing any stop-loss / take-profit pair for a diffusion with known F, G (two-barrier Laplace transform):
  E_y[e^(-r (tau_a ^ tau_b)) h(Y)] = h(a) [F(y)G(b) - F(b)G(y)] / [F(a)G(b) - F(b)G(a)] + h(b) [F(a)G(y) - F(y)G(a)] / [F(a)G(b) - F(b)G(a)].

## 5. Repeated trading: Bertram cycle-time optimum (coded)

Standardised OU dX = -X dt + sqrt(2) dW (stationary N(0,1)). Mean first-passage time -a -> +a is
T(a) = pi * erfi(a / sqrt(2)) in units of 1/kappa, T'(a) = sqrt(2 pi) e^(a^2/2). Maximise the profit rate
(2a - c) / T(a) with c = round-trip cost in sd_eq units: first-order condition T(a) = (a - c/2) T'(a), solved by Brent on
(c/2, 12]. Zero cost gives a* = 0 (trade continuously), which is why a grid cross-check is run. Entry distance in bp is
a* x sd_eq; expected one-way hold is T(a*)/kappa; rate per obs = (2 a* sd_eq - cost) / hold. Brute-force grid agrees with the root
to 0.01 in the self-test and the MC first-passage time matches T(1) = 2.995 to within 6%.
Reference: Bertram (2010), Analytic solutions for optimal statistical arbitrage trading (external).

## 6. Exit timing with a drive function (when a model says the market price will move against a held position)

Penalised liquidation: premium L = sup_tau E[ int_0^tau e^(-r u) G du ] with drive G = excess drift x dollar delta - penalty.
G > 0 everywhere: hold; G < 0 everywhere: sell now; never sell where G > 0. G = 0 is a cheap first-pass boundary and can sit
strictly inside the continuation region. Rates transfer (interpretation, not in the source): hold while the expected drift of
the position's value under your own mean-reversion model is positive after carry; exit when non-positive. (Leung and Li, 2016, ch.6-7.)

## 7. Futures under a mean-reverting spot (calendar and roll questions)

If the risk-neutral spot is OU with (mu~, theta~) then futures f_t^T = (S_t - theta~) e^(-mu~ (T - t)) + theta~ and the curve is
upward-sloping and concave when S < theta~, downward-sloping and convex when S > theta~. Expected roll yield needs both the
pricing-measure parameters (from today's strip) and the real-world ones (from history); a theta~ above theta makes a long rolling
futures position decay even if spot is flat. Under OU/CIR the futures price does not depend on sigma; under exponential OU it does.
(Leung and Li, 2016, ch.5.)
