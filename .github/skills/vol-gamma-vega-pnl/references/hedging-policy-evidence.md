# Delta-hedging policy: evidence, costs, time of day, regime filters

Detail behind the hedging rules in [SKILL.md](../SKILL.md). All results are historical sell-side backtests (USD unless
stated); treat them as priors and re-run [`scripts/gamma_pnl.py sim`](../scripts/gamma_pnl.py) with current costs.

## 1. Systematic short gamma, USD swaptions, 1997-2017
Design: sell the same notional every day, hold to expiry (about 21 overlapping options for 1m, 63 for 3m), straddles and
25-delta strangles, 2y/5y/10y/30y tails. Hedge variants: daily at the 3pm close; only when portfolio delta deviates
by 25% or more; unhedged. (Citi, Rates Vol Lab: The art of gamma hedging, 12 Mar 2018)

| Structure (sold) | Hedge | Sharpe | Other |
|---|---|---|---|
| 1m10y straddle | daily | 0.48 | 0.64bp/day of running yield |
| 1m10y straddle | 25% threshold | 0.84 | 1.41bp/day, yearly hit rate 0.81, Calmar 0.27 |
| 1m10y straddle | none | 0.43 | |
| 3m10y straddle | 25% threshold | 0.71 | |
| 1m30y straddle | 25% threshold | 0.40 | |
| 3m2y straddle | daily / 25% | -0.59 / -0.45 | short tails lose: hawkish regime-shift risk |
| 1m2y straddle | | 0.08 | |

The 10y tail is the best tail for selling gamma (pivot point, best liquidity). Thresholds beat daily hedging in the
sample only because bid/offer was wide.

Swap bid/offer for the 2y/5y/10y (bp): 1.6 (1995-H1 1998), 2.0, 1.4, 1.2 (2000-04), 0.6 (2005-07), 1.2 (2008-09),
0.7 (2010-12), 0.4 (2013-16), 0.3 (2017-18); the 30y is about 0.1-0.6bp wider. 2018 swaption bid/offer in normal vol bp:
1m straddles 1.5 (1m10y 1.0), 1m 25D strangles 2.0 (1.25), 3m straddles 1.0 (3m10y 0.5), 3m strangles 1.5 (0.75).
(Citi, The art of gamma hedging, 12 Mar 2018)

Optimal threshold vs cost (sell 1m10y daily, hedge at the close if |delta| exceeds the threshold; 0% = every close,
100% = never): at 0.5bp swap bid/offer Sharpe peaked at a 3-7% threshold; at 0.3bp (Mar 2018) the best policy was daily.
Re-optimise whenever liquidity changes. Intraday hedging was not studied. (Citi, The art of gamma hedging, 12 Mar 2018)

Programmatic version: $500mn/day 1Mx10Y ATMF straddles to expiry; net of costs the best policy used a modest threshold
(25% tested against none/10/20/30%). Threshold hedging lowers the variance of delta delivered to the market but raises its
excess kurtosis; single-day delivery of $3-4mn/bp on 10-20% of days, total at most about $10mn/bp. (J.P. Morgan, A
comprehensive look at convexity hedging in interest rates, 29 Mar 2019; J.P. Morgan, Zen and the art of gamma
maintenance, 9 Mar 2018)

Live rules seen in practice: hedge once a day at 9am NY only if delta moved more than 15% since the last hedge;
sell 1m10y straddles hedged daily around noon (10y bid/offer about 0.3bp, implied/3m hourly realised 1.07). (Citi, Rates
Vol Lab: Gamma and Vega RV, 14 Jan 2019; Citi, The art of gamma hedging, 12 Mar 2018)

## 2. Time of day of the hedge
Method: compute day-to-day realised vol from rates sampled at one fixed clock time (8am to 8am, 9am to 9am, ...) for
each hour 7am-5pm over 3m/6m/1y, compare with hourly hedging. A short-gamma book hedges when realised vol between
hedges is lowest (= peak liquidity); a long-gamma book benefits from the opposite. The answer moved with the period,
so do not hard-code a time:

| Market | Lowest realised (hedge short gamma here) | Highest | Source period |
|---|---|---|---|
| USD 10y | about 9am NY | 3-5pm | Jan, Mar, May 2019 |
| USD 10y | 12-1pm | | H2 2017 to Mar 2018 |
| USD 10y | about 9am | about 12pm | Jan 2020 |
| USD 10y | 10am-12pm | | Mar 2020 |
| USD 10y | noon-1pm | hourly hedging and 4pm | Jun 2021 |
| USD 10y | 7am | 4pm | Feb 2023 |
| USD 2y | | 8am NY (data releases) | Feb 2023 |
| EUR 10y | about 2pm London | | Jan 2020 |
| EUR 10y | about 8am; 8am and 4pm; 1pm (7-8am London in Feb 2023) | | Mar 2020; Jun 2021; Jun 2023 |

(Citi, Gamma and Vega RV, 14 Jan 2019; Citi, Vol cycle, steepeners, and SOFR, 25 Mar 2019; Citi, In search of cheap vol,
17 Jan 2020; Citi, Liquidity, vega, and convexity, 30 Mar 2020; Citi, Left-side vols' outperformance, 22 Jun 2021; Citi,
Forward steepener and vol divergence, 12 Jun 2023; Citi, Short Blues convexity via futures/swaps, 21 Feb 2023.)
Close-to-close realised vol can be inflated by algo events at the close, so test a mid-session snap as well.

## 3. Intraday vs close-to-close realised vol
Intraday realised vol from 30-minute snapshots 7am-4pm (NY for USD, London for EUR; earlier notes hourly 8am-3pm,
Mar 2020 note 7am-5pm on a 10-day window). Ratio intraday/close-to-close above 1 = whipsawing, mean-reverting
intraday market (illiquid; a short-gamma hedger with infrequent hedges benefits); below 1 = trending intraday.
In Mar 2020 the close-to-close/intraday ratio fell to about 0.5-0.6, a liquidity-stress signature. A normalising ratio
means liquidity is improving. (Citi, In search of cheap vol, 17 Jan 2020; Citi, Liquidity, vega, and convexity,
30 Mar 2020)

## 4. Regime and timing filters for short gamma
- Kurtosis: significance = -log10(p) of a non-normal-kurtosis test on trailing 1-month daily moves of the 1Mx10Y swap
  yield; 1.3 = 95%. High-kurtosis regime: selling 3Mx10Y ATMF, daily hedged and held one month (vega harvest), did much
  better than selling 1Mx10Y held to expiry (gamma harvest). After low kurtosis in a rising-vol environment, implied
  outpaces realised: long vega gains while actively hedged gamma loses. Sample 2013-2018. (J.P. Morgan, Zen and the art
  of gamma maintenance, 9 Mar 2018)
- Falling-vol regimes: implieds fall faster than realised as fat-tailed periods recede, so vega shorts beat gamma shorts;
  the reverse in rising-vol regimes. A short-gamma position can also lose while implieds fall if delivered vol jumps
  (Dec 2017). (J.P. Morgan, Zen and the art of gamma maintenance, 9 Mar 2018; J.P. Morgan, Update on systematic rule
  based trading strategies, 8 Jan 2018)
- Front-end slope: 3m10y implied minus next-3m realised correlates about 35% with the 3m/1y3m OIS slope: steeper, more
  hawkish curves paid short gamma better (inflation risk premia lift both). (Citi, Year-Ahead: Bumpy road for vol,
  12 Dec 2016)
- Zero lower bound: short delta-hedged gamma did not pay consistently until a few months after the Fed went to zero and
  began QE; bid/offer was wide (10y swap mid-to-bid/offer about 0.6bp on 27 Mar 2020, 1m10y 103nv, 10y gamma about 3
  sigma rich on a macro-vol model) so sell vega in longer expiries (2y2y at 55nv) instead. (Citi, Liquidity, vega, and
  convexity, 30 Mar 2020; Citi, Eat, pay, spend, 27 Mar 2020)
- Seasonality and events: gamma outperformed in 4 of the last 5 Mays and 7 of 10 (to 2017); government shutdowns were
  vol-negative; the 10 costliest US hurricanes were followed by money-losing delta-hedged 3Mx10Y straddle returns over
  1 month. (Citi, Fair value vs seasonality, 1 May 2017; J.P. Morgan, Issuance, pensions, and long-end spreads,
  14 Sep 2018)

## 5. EUR 3Mx10Y short-gamma timing rules (bp of notional, since 2000)
Base stance short 3Mx10Y straddles. Rules tested: vol-return momentum (long vol if the 1M momentum of the return from
selling vol is negative), carry (long vol if risk-adjusted carry is below its 30th percentile and rising), macro shock
(long vol if the 3M change in PMI is more than 1 SD below average), liquidity (neutral if the liquidity ratio exceeds 0.02).
Results, annual return (information ratio): always short 94 (0.98); momentum 180 (1.90); carry 159 (1.68); liquidity
102 (1.44); PMI 147 (1.54); equal-weight combination 147 (2.45); ECB regime 101 (0.9); implied/delivered thresholds
(long < 66%, short > 125%) 94 (0.8); fading 1y z-score extremes of 1.5 -37 (-0.3). Conditioning short gamma on momentum,
carry or macro filters beats always-short; fading implied-vol extremes alone loses. (J.P. Morgan, Update on systematic
rule based trading strategies, 6 Feb 2017; 10 Jul 2017; 8 Jan 2018)
Outcomes: profitable while delivered vol stayed subdued despite French election risk (Feb 2017); lost on the hawkish ECB
shift of June 2017.

## 6. Reading the implied/realised grid (USD, 20 Aug 2026)
Implied divided by 1m realised: 1M expiry by tail 1Y 1.38, 2Y 1.39, 5Y 1.22, 10Y 1.11, 30Y 1.06; 1Y expiry 1.26, 1.27,
1.20, 1.21, 1.19. The left side (short tails) is rich versus realised but jump-prone, so not a sell; the right side is
the entry for owning gamma. (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026)
Scaling rule seen in practice: short $100mn 3m10y, hedged at 9am with a 15% threshold; after 3m10y fell from 66 to about
59 normals and was still about 3 normals rich, cut 50% (11 Jan 2019). Closed short-gamma trades: 1m10y delta-hedged
straddles +$300K; GBP short 3Mx1Y straddles closed at -1.5bp of notional (entry 4.7bp/day, exit 4.55) on MPC repricing
jump risk. (Citi, Gamma and Vega RV, 14 Jan 2019; J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026)

## 7. Event days and expiry
Put the whole event premium on one day and run the other days at the base daily vol. GBP referendum example: 1M10Y 25bp
and 2M10Y 69bp give a 1M-forward 1M10Y vol of 94bp; the event day then carries 26.21bp (416bp annualised) and the other
days 1.57bp/day (25bp annualised). Near expiry ATM gamma explodes and a cash-settled swaption needs its risk replaced at
expiry: expect technical delta management. For a 31-calendar-day expiry spanning Easter, calendar time 31/365 = 0.0849
and business time perhaps 19/252 = 0.0754: subjective, material. (Darbyshire, Pricing and Trading Interest Rate
Derivatives, 3rd ed., 2022, Ch.20)
