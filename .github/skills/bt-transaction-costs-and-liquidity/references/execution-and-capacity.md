# Execution, hedging frequency, dealer pricing and capacity

Detail behind the main skill. Figures are from the cited source and period; most are USD, and where a source studied
corporate bonds or index CDS it is flagged as an analogue for rates RFQ behaviour, not a rates measurement.

## 1. How often to trade: bands, thresholds, turnover

- **Costs set the hedge frequency** (Citi Research, US Rates Vol Lab: The art of gamma hedging, 12 Mar 2018). Short
  1m10y straddles hedged at the 3pm close only when delta exceeds a threshold (0% = every close, 100% = never), 1994-2017:
  at 0.5bp swap b/o the Sharpe peaks at a threshold of about 3-7%; at 0.3bp (near the historical low) the best is 0%,
  daily hedging. A threshold policy beat daily hedging historically only because costs used to be higher. Re-optimise the
  band whenever b/o changes. Move-based hedge band for convex flatteners: 15-30bp is a plateau (hedged every 20bp in
  USD, 25bp in GBP); tighter bands lose to costs, wider ones add P&L variance (Citi, Trading long-dated convexity,
  9 May 2019; Liquidity, vega, and convexity, 30 Mar 2020). Without rebalancing the trade earns gamma only on the move
  from entry to exit.
- **Time of day**: hedge when realised vol between hedges is lowest. Citi found flat realised vol 9am-3pm NY over
  2014-18 and the lowest around noon in the 6 months to Mar 2018 (NY/Europe overlap, past morning data, before algorithmic
  events around 3-4pm that inflate close-to-close vol); later windows to 2019 put 9-10am lowest and 3-5pm highest.
  The best hour drifts, so re-estimate per window; the principle (hedge at peak liquidity) is the stable part.
- **No-trade band** (Constantinides 1986, via Hasbrouck, Empirical Market Microstructure, 2004): hold inside a band and
  trade only to its edge; the band widens with the proportional cost k, yet the return cost is second order (liquidity
  premium about an order of magnitude below k).
- **Cost-aware entry/exit for mean-reverting spreads** (Leung and Li, Optimal Mean Reversion Trading, 2016): exit cost c_s
  raises the optimal take-profit level; entry cost c_b lowers the entry level; faster mean reversion narrows the band,
  higher sigma widens it. Brownian special case: exit level b* = c_s + sigma / sqrt(2 r). Never enter when the best
  achievable gain net of costs is not positive (sup over x of V(x) - x - c_b <= 0). A constant holding penalty q (negative
  carry) folds into the costs: exit cost c_s - q/r, entry cost c_b + q/r. Switching (repeated) bands sit inside one-shot
  bands. Ad hoc +/-1 sd bands ignore all of this. Implementation lives in
  [quant-mean-reversion-ou](../../quant-mean-reversion-ou/SKILL.md).
- **Turnover frontier** (Grinold and Kahn, Active Portfolio Management, 2nd ed., 1999): value added is increasing and
  concave in turnover; even prorating every trade keeps at least 75% of incremental value added at 50% of the turnover
  (at least 87% of the information ratio); doing the best trades first beats the bound. Optimal turnover is where the
  frontier slope equals the round-trip cost; a turnover cap implies a cost equal to the slope at the cap, so check the
  implied number against your estimate. S&P 100 illustration (alpha 3.2%, risk 4%, lambda 0.1): at 10/30/50/70/90% of
  unconstrained turnover you keep 39.2/71.4/86.8/95.5/99.5% of value added, implied round-trip cost 8.66/3.40/1.90/1.02/0.33%.
- **Mean reversion costs more than trend** under the same dependence: expected round turns of a moving-average rule
  on a random walk is E(N) = 1 + (T-2)(1/2 - arcsin(rho_F)/pi); negative autocorrelation means more trades than that
  (Dunis, Laws and Naim, Applied Quantitative Methods for Trading and Investment, 2003). At 0.03% per round turn over 250
  days: MA2 125 turns, drag 3.75%; MA5 67.4, 2.02%; MA17 34.9, 1.05%; MA61 18.6, 0.56%; MA117 13.7, 0.41%.
  `scripts/costs.py` has `ma_round_turns`.
- **Cutting turnover without cutting edge**: linear decay or winsorising and decaying inputs removes needless signal
  flips; margin = P&L per dollar traded before costs, and low-margin signals fail (Tulchinsky et al., Finding Alphas, 2015).
  Discretise sizes, m* = round(m/d) x d with d = 0.2 and a cap at +/-1, and average the sizes of active bets rather
  than overriding them (Lopez de Prado, 2018, Ch.10).
- **Illustration of cost vs signal** (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008): on 100 days of USD
  swaps 1y-30y the fastest mean-reverting baskets looked promising out of sample, but a 1bp bid-ask "completely
  neutralised" them; optimal baskets were local flies with tiny price range. Always compare the out-of-sample price
  range in bp with the round-trip cost.
  Cuturi and d'Aspremont (2015): Sharpe falls roughly linearly in cost, so summarise a strategy by intercept and slope;
  impose a variance floor (0.2-0.3 x median constituent variance) and a cardinality cap (30-50% of the universe).

## 2. Execution protocol

- **RFQ competition vs leakage.** Asking many dealers creates a winner's curse and tells losers the winner's likely
  position, so dealers pre-price the hedge cost (Duering, Fixed Income Trading and Risk Management, 2021). For
  transparent, non-informative trades asking many dealers is costless; for informative or very large trades show fewer
  dealers while still signalling competition (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022, Ch.18).
  Index CDS on SEFs (analogue): on average 4.1 dealers queried, 3.6 respond, 92% of requests trade; response about 90%
  with 3-5 dealers and about 80% with 6 or more; price improvement from extra dealers is tiny in liquid products, and
  larger size means fewer dealers queried (Riggs, Onur, Reiffen and Zhu, JFE 2020). Corporate bonds (analogue): costs
  fall to about zero above 10 responses; an unexpectedly thin response is costly (coefficient -97 vs -11.6 for an
  expected one); a failed auction costs +2.5bp (IG) to repeat and +11.6bp to fall back to voice; voice wins above a
  critical size because leakage grows with size (Hendershott and Madhavan, Journal of Finance, Feb 2015).
- **Optimal dealer set**: minimise size x E[min markup over the chosen dealers] + linear inquiry cost. The first term is
  submodular, so add dealers while the marginal expected improvement exceeds the leakage cost (Cotton, Who Ya Gonna Call?,
  Quant Summit NY, 18 Jul 2019).
- **Information leakage example** (Darbyshire, 2022, Ex 18.3): a hedge fund asked for 200mm 10Y GBP IRS against a typical
  25-50mm; quoted 1.25bp from mid and traded; the mid moved about 2bp; the dealer inferred 2-3x the stated size was being
  worked elsewhere and quoted 1.75bp from mid thereafter.
- **Leg order and legging.** Go to the point of least liquidity first: fill the pack or bundle leg before the liquid bond
  future; never leg a closing spread; set a size multiple on the second leg and ignore implied prices; implied prices
  vanish when needed (Aikin, STIR Futures, 2012). A bundle bid one tick above the bid means paying the offer on only 2
  of 8 legs at half-tick markets: check the individual legs.
- **Off-benchmark structure** (Darbyshire, 2022): to hedge an 8s35s spread choose between cost (8s10s + 10s30s + 30s35s,
  each liquid, dearer in total), liquidity (work 8s35s patiently at fill risk) and effectiveness (a single 10s30s proxy
  with residual risk). Practical resolution: execute 10s30s now as the proxy, then work 8s10s and 30s35s at slightly
  favourable levels.
- **Hedge-cost ordering, cheapest first** (Darbyshire, 2022, Ch.18): benchmark tenors before non-standard; few hedge
  instruments before many; smaller than average size before larger; no exposure to isolated calendar events before reset
  risk on central-bank meetings. Equivalent presentations of the same risk must cost the same (receive 100mm 5Y5Y =
  pay 5Y and receive 10Y = receive 5s10s plus 50mm 10Y).
- **Avoid size into releases**: depth falls below a quarter of base into 08:30 payrolls and takes 15-60 minutes to rebuild;
  FOMC depth does not recover through the close; Tokyo hours are thinnest (J.P. Morgan, When the going gets tough, the
  tough get going, 5 Nov 2019; Markets struggle to feed the convexity beast, 28 Feb 2020).
- **Do not initiate when illiquid**: Citi declined a USD 15y5y/20y10y flattener at -5.21bp (1y z-score 4.21, 3y z 3.58) on
  26 Mar 2020 as "effectively a free convexity buy" because of illiquidity and wide b/o; and a 10y10y/20y10y/30y10y
  forward fly entered at 16bp in late Feb 2020 had its peak P&L in March but could only be exited once costs returned
  to about 3bp, unwound at 10bp on 15 Jun 2020 for $360k (Citi, Liquidity, vega, and convexity, 30 Mar 2020; North
  America Rates Trade Idea Alert, 15 Jun 2020). Peak mark-to-market on multi-leg long-end packages can be unrealisable.
- **Tie-break by liquidity**: of near-identical screens pick the tighter market (15y5y/20y10y chosen over 15y5y/20y15y;
  trade $50K DV01, $148.8mn 15y5y vs $90.3mn 20y10y; Citi, Trading long-dated convexity, 9 May 2019).
- **Settlement fails**: a failing seller effectively borrows at 0% repo, so the cure incentive is weak when rates are low
  or the bond is special (5% or more special is not uncommon); US flat 3% fails charge since May 2009; EU CSDR buy-ins
  from 1 Feb 2021 (Duering, 2021).

## 3. What the dealer does to your price (use to forecast quotes, not to charge them)

- **Inventory moves the quotes, not the width**: spread is proportional to size (Stoll 1978: (Ask - Bid)/P = (z/W0) s^2 |Q|);
  a long dealer lowers both bid and ask; a skewed mid can be an axe rather than a view (O'Hara, Market Microstructure
  Theory, 1995). A dealer long a correlated bond skews related bonds too (Ho and Stoll 1983, beta-weighted inventory).
- **Inventory-bounded market making** (Gueant, Lehalle and Fernandez-Tapia, arXiv 1105.3115): with fill intensity A e^(-k d)
  and risk aversion g, spread approx (2/g) ln(1 + g/k) + sqrt(s^2 g / (2 k A) x (1 + g/k)^(1 + k/g)), independent of
  inventory q; the skew is linear in q; wider with higher sigma^2, narrower with higher A or k; adverse selection xi adds
  xi to the spread. Exponential fill intensity suits only liquid, small-spread instruments.
- **RFQ markup** = market width + adverse selection + marginal inventory cost; skew = slope, width = convexity of the
  dealer's indifference price; benchmark rule of thumb is constant width, linear skew (Cotton and Papanicolaou, Trading
  Illiquid Goods, 2017).
- **Client tiering** (Duffie, Garleanu and Pedersen, Econometrica 73, 2005): bid-ask A - B = z d / (r + l_u + l_d + p(1 - z)),
  z = dealer bargaining power, p = dealer-contact intensity; spreads rise with dealer power and fall with the client's
  outside option, so clients with fewer dealer lines and credit lines pay more. Backtested costs are therefore
  counterparty-set specific: a fund with two dealers should not use an all-dealer panel's spread.
- **Two kinds of friction**: transaction-cost friction reprices instantly; search and slow-capital friction produces an
  overshoot then gradual reversion. The second creates RV mean reversion after supply shocks (Duffie, Dark Markets, 2012:
  calibration gives a 44bp liquidity spread, about a 15% immediate price drop after an aggregate shock, more than a year to
  recover). Scarcity can also give a price premium above the frictionless level (on-the-run, CTD).

## 4. Capacity and crowding

- **Capacity** = maximum P&L subject to the Sharpe staying above an acceptable floor; the Sharpe almost always falls with
  volatility deployed; cost grows super-linearly with size (Paleologo, 2025). Summing per-account impact underestimates cost
  because impact is nonlinear (total about size^1.5): aggregate before costing (Golub, BlackRock's Guide to Fixed-Income
  Risk Management, 2023). Cap each order at about 1% of ADV (Chan, Quantitative Trading, 2009) and track position DV01 against
  traded DV01 by tenor (the benchmark 5/10/30y concentrate liquidity, cost-benchmarks section 5).
- **Do not become the market**: a known oversized position invites predatory trading, and hedging by adding an offsetting
  position rather than unwinding grows gross size and illiquidity (Tuckman and Serrat, 2022). Exit cost example: the London
  Whale index-CDS book reached over 10 days of ADV; estimated cost of cutting RWA by $25bn was $400-590m (same book).
- **Low capacity means market making**: strategies that supply short-term liquidity earn high Sharpe at small size; at
  billions you become the liquidity demander and pay for it, which forces long holds and macro exposure (Chan, 2009).
- **Crowding and fragility**: similar models chasing one inefficiency exit together (Chan, 2009). Positions that are
  operationally intensive and balance-sheet intensive, with small upside and large dislocation downside, are unwound first
  (J.P. Morgan, 10 Mar 2020). Dealer constraints are common across markets, so diversification does not diversify
  liquidity risk (Duering, 2021). Stop spread and steepener trades when the vol regime shifts even if the thesis holds
  (J.P. Morgan, Impossible to walk in this muck, 6 Mar 2020).
- **Liquidity-dependent alpha**: European auction-cycle trades earned 3.4bp per trade pre-auction (IR 2.5) and 1.5bp post,
  before costs; 12-month P&L tracked the 12-month 10y FR/IT/ES bid-offer, so in 2011-12 costs bit most of the extra upside,
  and the edge faded when liquidity normalised (J.P. Morgan, European Rates Strategy: Follow the cash flow, 15 Sep 2015).
