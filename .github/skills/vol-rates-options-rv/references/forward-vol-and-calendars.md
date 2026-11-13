# Forward vol, FVAs, calendars, midcurves, vol carry, mean reversion

Detail behind steps 5-6 of [SKILL.md](../SKILL.md). Functions: `forward_vol`, `fwd_swap_vol`, `midcurve_vol` in
[`scripts/bachelier.py`](../scripts/bachelier.py). Correlation-based midcurve/CMS RV is deepened in
[vol-correlation-and-curve-options](../../vol-correlation-and-curve-options/SKILL.md).

## 1. Forward vol of the SAME rate (variance additivity)
Normal moves are independent over disjoint periods, so for one underlying rate:

    sigma_fwd(T1->T2)^2 = (T2·sigma(T2)^2 − T1·sigma(T1)^2) / (T2 − T1)

Darbyshire Ex 20.6: 2Y7Y = 50bp, 1Y1Y7Y = 44bp -> the 7y swap's vol in year two = sqrt(2×50² − 44²) = 55.35bp ("market
expects the second year more volatile") (Darbyshire, Pricing and Trading Interest Rate Derivatives 3rd ed., 2022). The
expiries must reference the SAME underlying swap; different tails need section 2.

## 2. Vol of a forward swap from same-expiry par vols
5y5y vol one year out ("1y5y5y") from 1y5y and 1y10y par vols: with L = annuity(1y10y)/annuity(1y5y5y) and rho = correlation
of the 1y5y and 1y10y par-rate changes,

    sigma_1y5y5y = sqrt( ((1−L)·s_1y5y)² + 2(1−L)·L·rho·s_1y5y·s_1y10y + (L·s_1y10y)² )

Ex 20.5: 1y5y = 39, 1y10y = 59, L = 2.10, rho = 0.95 -> 84bp (naive linear extrapolation 2×59 − 39 = 79bp, the rho = +1, L = 2 case; ~170bp at rho = −1 down to ~80 at
rho = +1). Results are far more sensitive to rho than to L moving. The 5y5y vol in terms of forward-swap replication:
DV01(1,10)·r(1,10) = DV01(11)·r(11) − DV01(1)·r(1) (Credit Suisse, The FVA: Forward Volatility Agreement, 27 Aug 2013).

## 3. Forward-starting vol grid ("triangular approximation")
Forward 1y2y/1y5y/1y10y/1y30y vols with forward starts 0-9y are derived from spot vols with a standard triangle and
6m realised correlations as the proxy for implied correlations (an approximation). Report level, 1w/1m change, difference to
1y average (z) and to the 10y average of the matching 1y-expiry spot vol (z), and ratios 1y2y/1y5y, 1y5y/1y10y,
1y10y/1y30y now, 1m and 3m ago. A kink in the forward term structure points to a cheap/rich SPOT point (steep 1y2y forward
term structure in long expiries -> "7y2y spot may be cheap to 10y2y"). A flat forward-vol term structure "offers an
attractive carry" (Citi Research, Rates Vol Lab: In search of cheap vol, 17 Jan 2020; Liquidity, vega, and convexity,
30 Mar 2020). Triangle replication example: 3y1y10y ≈ 4y10y + 3y1y − 3y11y (Citi, A Holistic Approach to Convexity Across
Fixed Income, Jun 2022).

Exact two-period identity for an FVA (4y-forward 1y10y): (5−4)·sigma_fwd² = 5·Var(F_5y^{5y,10y}) − 4·Var(F_4y^{5y,10y});
F_4y^{5y,10y} = (1+a)F^{4y,11y} − a·F^{4y,1y}, a = DV01(4y1y)/DV01(5y10y); Var = (1+a)²σ²_{4y11y} + a²σ²_{4y1y} −
2a(1+a)ρσ_{4y11y}σ_{4y1y}. Replication: long 5y10y swaption, short 4y midcurve on the 1y10y forward (= short 4y11y + long 4y1y),
all at the same strike. RV metric: forward/spot vol ratio with 3m z-scores; as gamma richens, forward vol cheapens (BofA, US
Vol Primer, 11 Mar 2024).

## 4. Midcurves and FVAs
- Midcurve as DV01-weighted spread option: sigma_MC = sqrt(D13²σ13² + D12²σ12² − 2ρ D13σ13 D12σ12)/D23. In practice midcurve
  vol trades ABOVE its rho = 1 level (Credit Suisse, 27 Aug 2013).
- FVA = forward on an ATM straddle, strike set at mid on the look date: only vega, no delta/gamma/theta/skew; the holder "owns
  the skew for free" at the look date. Cannot be replicated by a finite set of fixed-strike options (stochastic vol, skew
  slippage). A short FVA in a gap is short an ATM option exactly as vol explodes (Bassman, Building a Better Volatility
  Mousetrap, 6 Sep 2012).
- FVA vega-weighted replication example (Aug 2013): 100k/nv of 6m-forward 1y10y = buy 160k/nv 18m10y, sell 60k/nv of the 6m
  midcurve on the 1y10y. Inputs 6m1y 37bp, 6m11y 99bp, 1y10y 100bp, 18m10y 99bp; DV01 1.0/9.6/8.6; rho = 1 -> midcurve ~106-107bp;
  buy $186mm 18m10y vs sell $116mm midcurve; forward bought at 95nv vs 100nv spot (5% discount). Notional-neutral replication
  mismatches inception vega -> use vega weights (Credit Suisse, 27 Aug 2013).
- A vanilla CALENDAR is not forward vol: the gamma profiles differ. Stock example: sell Sep straddle 66, buy Dec 94 (28);
  after a rally to 675 the spread is 7 even with implied +20% (Bassman, 6 Sep 2012). A calendar needs gamma and vega
  neutrality (vega-weighted) to isolate forward vol; a notional-neutral calendar is long forward vol but carries
  gamma/theta (BofA, 11 Mar 2024).
- Synthetic forward vol via mid-curve calendar: sell 2y expiry on the 8y-forward 20y and buy 10y-into-20y at the same strike;
  Sep 2013: sell 100mm 2y-into-8y20y payer K 4.75% (~92nv), buy 100mm 10y20y payer (~71nv), pay 400bp; synthetic forward vol in
  the mid-60s; first-year roll-down +160bp; worth >= cost if the 8y20y rate is within +-150bp of strike at first expiry
  (Bassman, How High is High?, 17 Sep 2013).

## 5. Forward-vol efficient frontier (screening method)
1. Enumerate every executable forward-vol trade: gamma-neutral calendar spreads whose underlying forwards have matching
   mid-points, and triangles (3 legs).
2. Score: value = 1y z-score of the forward vol (also 3m); ex-ante Sharpe = vol-adjusted 3m roll on the unchanged surface.
3. Report the top 10-20 on the frontier with weights (gamma-neutral), short/long/forward vol, 3m roll (nv), Sharpe, 1y z, 3m z
   (Citi, 17 Jan 2020; 12 Jun 2023; 5 Oct 2026).
4. Then check carry per leg and the "why" (supply, ELB, YCC).

Reference outputs (Citi; illustrative of scale, not live): Jun 2023 1y2y1y fwd (long 3y1y vs short 1y2y1y, weights 69.8/100) fwd
106.1, roll 7.02nv, Sharpe 0.54, 1y z −1.0; 3m6m7y roll 14.08, Sharpe 0.69; long-tail calendars roll 1.3-2.3, Sharpe ~0.2.
Jan 2020: 1y3y2y roll 2.28, Sharpe 0.26, z −1.8; 5y-forward 5y20y roll 0.19, Sharpe 0.09, z −2.3. Mar 2020 sell 3m3m20y (3m20y vs
6m20y): roll 29.75nv, Sharpe 4.17, 1y z +2.1 (rich AND high carry). Sep 2019 3m20y vs 6m20y: roll 13.28nv, Sharpe 2.82, z 1.3.
A negative z with a tiny Sharpe is value without carry; a high Sharpe with a positive z is a carry trade in rich vol.

Expected-return/Sharpe grid (general): P&L = theta·dt + delta·dr + vega·d(sigma) + 0.5·gamma·dr²; straddles reduce to
theta + vega + gamma terms; expected Sharpe = expected return / stdev of trade returns, produced across swaptions, midcurves,
spread options, wedges and forward vol with Buy/Sell flags. Sample: June 2022 EUR 3m3m swaption −83%, 5y5y midcurve at 3m
+98% (Sharpe 2.2), 1y1y forward vol +28% (Sharpe 0.9) (Citi, A Holistic Approach to Convexity, Jun 2022).

## 6. Vol carry, roll and the carry-to-premium rule
- Static roll on the grid: price a fixed-strike option across expiries on today's surface; carry = price change as expiry
  shortens with the surface unchanged. Usually decays (4y->3y 6% payer: 344 -> 246 = 98bp, 28%), but a flat/inverted forward
  curve with an inverted vol surface can make long-expiry OTM payers roll UP (Bassman, The Positive Carry Hedge, A Reprise,
  8 Dec 2010; Merrill Lynch, The "Positive Carry" Hedge, 31 Oct 2008: 10y10y payer K 7.25% at 139bp rolls to 171bp after
  5y). Those are macro holdings, not RV.
- Vol roll for switches: 6m vol carry for 1y expiry (tails 1y..30y) in normals: −3.1, −2.0, 2.5, 2.0, 1.7, 1.4, 1.9, 2.3; for
  2y expiry −3.5, −3.0, −0.1, 0.1, 0.1, 0.4, 0.6, 0.7 -> a long 1y5y (+2.0) vs short 1y30y (+2.3) nearly offsets (Citi,
  22 Jun 2021). "Cheapest on a model is not automatically the best long: check each leg's vol carry."
- Vol-adjusted rolldown for long expiries: 1y absolute vol roll-down / 3y vol-of-vol, with 1y and 3y z (Citi, Buy long
  expiries, 17 Jan 2017). Example 10y10y: 72.7nv, roll-down 2.10, vol-adjusted 0.38, z −1.4 (1y), −2.0 (3y). Outcome: bought
  at 72.70 on 12 Jan 2017, 66.25 on 14 Dec 2017, −$640k on $100mm - cheap, rolled down, and still lost (supply, rates).
- Three-to-One rule (Bassman, personal rule, not backtested): ratio = 1y pure roll-down in bp × DV01 / premium of the 1y
  receiver. Buy the receiver when the ratio nears 3 (2.75-2.85 acceptable). Logic: fair coin-flip payoff is 2:1; 3:1 on a
  2:1 risk = option cheap vs the curve risk; normally <2:1 because curve slope and vol correlate. Jul 2014: 1y-into-2y receiver
  56bp, K 1.45%, 1y roll-down 82bp, DV01 1.97 -> 82×1.97/56 = 2.88, 5th time above 2.75 in 20 years. Jan 2010: 47bp premium vs
  132bp roll-down -> 2.8:1 (Bassman, Your Ace in the Hole, 16 Jul 2014; Paying Nickels for Dimes, 21 Jan 2010).
- If premium > carry you want to capture, use cheapening structures (spreads, contingencies), e.g. Jun 2019 6m payer on 2y
  ~46c vs 31c carry; ATM/25bp-OTM payer spread 26c (Bassman, For Propeller Heads Only, 17 Jun 2019).
- Vol is generally NEGATIVE carry to be long; an inverted vol term structure (1m10y > 1y10y) usually fades fast because
  fading is positive carry for the seller (post-Covid inversions persisted) (BofA, 11 Mar 2024).
- Carry expressed against premium for a package: compare carry per year against theta per year at matched gamma and horizon
  (see [vol-convexity-and-long-end](../../vol-convexity-and-long-end/SKILL.md)).

## 7. Mean reversion of vol spreads (OU)
For a vol spread x (e.g. EUR 5y5y − GBP 5y5y implied): dx = k(mu − x)dt + s dW; half-life = ln2/k; stationary sd = s/sqrt(2k);
regression shortcut: regress daily changes on (mu − x), slope ≈ k·dt (OU MLE and regression agreed: 0.056 vs 0.055 per day).
Case 25-May-05 to 4-Jul-12: level correlation 0.87, k = 16.5/yr, half-life 15.4 days, current 12.35 vs mean ~1.0, instantaneous
vol 28.25. P(spread above current): 1w 18%, 1m 4%, 3m <1%. Expected-change Sharpe 0.91 (1w), 1.78 (1m), 2.26 (3m) -> hold
briefly and recycle. First passage to target 7: mode 7d, mean 14.9d, P(hit) 13%/45%/67% within 5/10/15d; stop +4 vol points: P(hit)
5%/9%/10%/11% by 10/20/40/50d (Huggins & Schaller, Fixed Income RV Analysis 2nd ed., 2024). Cautions: constant-vol OU
overstates Sharpe at extreme entry points; parameters shift with the vol regime; the bivariate (MVOU) fit showed mutual
attraction and a non-monotone path for the cheaper leg (GBP first rises toward EUR, peak ~60 days). Details of OU fitting:
[quant-mean-reversion-ou](../../quant-mean-reversion-ou/SKILL.md).

## 8. Forward-vol pitfalls
- Forward vol prices often already contain the mean reversion; do not pay for it twice. A 38% forward premium can absorb the
  whole expected rise; the VIX 3m/6m forwards were +38%/+63% over spot while rates FVAs were +3-8% (Bassman, 6 Sep 2012;
  Forwards are NOT a Prediction, 12 Aug 2013).
- Forward vol inherits flow distortions of the spot surface. Spot-vs-forward: buy SPOT long-dated vol when a hawkish shock is
  the risk - short-dated vol spikes cheapen forward vol (2013 taper: spot outperformed forward) (Citi, 17 Jan 2017).
- "Cheap for a reason": forward vols at −1.5 to −2.4 sd (4y-forward 1y2y 61.25, z −2.19) were NOT bought in Sep 2019 because of
  ELB convergence toward EUR/JPY and callable supply (Citi, Buying vol for less, 25 Sep 2019).
- 8y20y spot below 65nv only twice since 2000 and both times just before a vol jump (Bassman, 12 Aug 2013): historical
  floors are evidence, not a guarantee.
- Realised correlation as an implied proxy is an approximation; midcurve replication with vanillas ignores correlation
  exposure; a forward vol is only as good as the correlation input.
