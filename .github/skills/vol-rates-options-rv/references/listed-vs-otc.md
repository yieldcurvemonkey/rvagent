# Listed (futures options) vs OTC swaption vol; STIR option RV

Detail behind step 7 of [SKILL.md](../SKILL.md). Inputs: `opt_quotes`, `opt_static`, `fut_quotes`, `vol_surface`,
invoice spreads from `swap_spreads` (see [data-contract-and-adapters](../../data-contract-and-adapters/SKILL.md)).
Delivery-option and CTD logic: [vol-basis-vs-vol](../../vol-basis-vs-vol/SKILL.md),
[fut-ctd-switch-and-delivery-options](../../fut-ctd-switch-and-delivery-options/SKILL.md).

## 1. Treasury-futures options ("Board") vs CTD-matched swaption
Method (Citi Research, Rates Vol Lab: Trading long-dated convexity, 9 May 2019; The art of gamma hedging, 12 Mar 2018):
1. Take ATM-interpolated futures-option vol on the second available expiry (roll at front expiry to avoid expiry-effect noise).
2. Build the CTD-matched swaption: expiry = option expiry, tail = CTD duration-matched swap, strike map **swaption strike =
   Board strike yield + invoice spread**. Premium differences are expressed as running yield (premium / option DV01).
3. Convert units first: Board vol is lognormal price vol; compare in normal yield vol (`1e4 × price vol / ModDur_CTD`).
4. Ratio = Board vol / swaption vol. Compare with the REALISED ratio (futures realised / swap realised, 1m and 3m): if the
   implied ratio exceeds the realised ratio, listed is rich relative to OTC.
5. Check the smile as well: Board puts rich to swaption payers and calls cheap to receivers (2023); Board smile rich to
   swaption smile (Mar 2020).

Observed ratios (ATM, Board/swaption; levels differ by episode; flags are the author's thresholds, see SKILL.md):

| Date | Ratios | Reading |
|---|---|---|
| Dec 2016 | two expiries each: 5y-note 1.04/1.08, 10y-note 1.06/1.10, long-bond 0.97/1.00; futures/swap RV 1m 1.05/1.01/0.95 | Long-bond Mar-expiry somewhat rich vs realised |
| May 2019 | 10y-note 3% rich (60.1 vs 58.5); range 0.97-1.11 across contracts | Board-cheap episodes "typically short-lived" |
| 20-27 Mar 2020 | 5y-note 0.86, long-bond 0.89, 10y-note 1.02; a week earlier 1.22-1.24 for 10y/long | Stress: Board cheap to swaptions; Board/3m RV 0.59-0.71 |
| Jun 2023 | 1.01 / 0.98 / 1.03 (5y/10y/long); Board/1m RV 1.16-1.22; Board/3m RV 0.77-0.93 | Fair; puts over payers, calls under receivers |
| Sep-Oct 2026 | 1.03/1.06/1.07 (5y/10y/long, Oct); long-bond 1.14 and 1.17 (Sep) vs futures/swap 1m RV 1.37 | Board above swaptions but below the realised ratio |

Sources for rows: Citi Rates Vol Lab 12 Dec 2016, 9 May 2019, 30 Mar 2020, 12 Jun 2023, 14 Sep 2026, 5 Oct 2026.

Conditional spread (futures option vs swaption): buy put on futures / sell payer (or call vs receiver), DV01-neutral, swaption
notional per 1000 contracts; a COSTLESS swaption strike makes it zero cost; "bp pick-up" = costless-strike spread minus invoice
spread (Citi Rates Vol Lab: Buy long expiries, 17 Jan 2017). Example May 2019: sell 1,000 10y-note calls (27c) vs buy $130mn
matched-expiry receivers (21.7c, strike 1.67% vs ATMF 1.96%) premium-neutral (J.P. Morgan, Is bank convexity hedging lying in
wait?, 31 May 2019). If futures options are rich to swaptions AND call skew is steeper than receiver skew, sell OTM futures calls
to fund matched receivers.

Single-CTD frameworks miss embedded futures convexity when yields are near the notional coupon and coupon dispersion is wide:
a swaption replication of a long-bond futures contract valued the embedded convexity at ~12.4 ticks vs ~8.7 ticks net basis
(~30% cheap), and futures-option skew on the CTD ~ a 3m20y swaption skew, i.e. futures options do not price the extra sell-off
convexity (Morgan Stanley, Buy Higher Rates Protection at a 30% Discount, 27 Aug 2026).

## 2. Is the listed leg worth it?
House three-way test (curve vs swaption vs listed as the cheapest gamma source; unpublished internal backtest, ~500 dates):
the three signals disagreed on only ~1.6% of rows, median |OTC − listed| basis was ~0.27bp/day against ~2.7bp/day needed to
flip a quarter of the days, so listed added essentially nothing over the sector-matched swaption on the short end. An
independent dealer package showed OTC-listed basis of 4.9-7.8%. Use listed mainly for liquidity, margin efficiency, anonymity
and small size, not as an RV source, unless the Board/swaption ratio is outside its normal band AND the realised ratio does not
explain it.

## 3. Listed SOFR / STIR options: what RV exists
(Huggins & Schaller, SOFR Futures and Options, 2022.)
- Contract specs as at the book: 3M-futures options USD 25 per bp, American, last trade the Friday before the 3rd Wednesday of
  the contract month, strikes 6.25bp near ATM; 1M-futures options only nearest 4 months, USD 41.67 per bp, American, last trade
  last business day, strikes within +-125bp. Re-verify against the exchange: specs change.
- Before the reference period an option on a SOFR future is a standard option on a forward term rate; inside it the payoff is
  path dependent (Asian). 3M options stop trading before the reference quarter; 1M options become arithmetic-average American
  Asians with no pricing formula. A model must be consistent for futures AND options: mixed jump-diffusion (FOMC-date jumps) not
  pure jump; "a trader whose pure-jump model says a call is worth zero should stress-test against diffusion before selling cheaply".
- Level and slope trades on the STIR vol curve: realised-vol curve by forward point (3M..24M) is computed from each contract's
  realised normal vol over ~quarters; compare today's implied curve with the range of historical realised curves. Level trade
  (sell and delta-hedge) when implied is high; slope trade (sell the long, buy the short expiry, both hedged) costs more to
  execute but hedges the level. When vol rises the realised-vol curve steepens (correlation of level and 2y-5y slope 0.71 in JPY).
  Dec 2021: implied ~50-75bp at 6-12M, steep vs history; after the 17-Dec FOMC the slope trade was better than the level trade.
- Secured vs unsecured: unsecured rates should realise more vol (the repo-unsecured basis widens as rates rise). Signal: secured
  (SOFR) implied above unsecured (ED) implied -> sell secured vol, buy unsecured vol; since the standing repo facility
  (announced 28 Jul 2021) SOFR spike-driven vol is lower, so re-estimate on post-Aug-2021 data.
- Listed mid-curve vs front vol: Euribor mid-curve minus front-contract normal-vol spread near all-time lows (percentile just
  under 10%) flagged a buy of mid-curve vol vs sell front vol (Nomura, Derivative Focus: Erratum: Conditional Euribor bull
  flatteners, 19 Jun 2014).
- What is NOT an RV: no mean-level RV exists within a contract (put-call parity pins it). RV lies in within-contract smile
  shape, cross-contract coupling (digital calendars: the sum over strikes of back-minus-front digitals equals the futures calendar
  spread, so only the SHAPE across strikes is tradeable), implied vs realised and event speed. For distribution-based work use
  [stir-options-implied-distributions](../../stir-options-implied-distributions/SKILL.md) and
  [stir-policy-pricing-whats-priced-in](../../stir-policy-pricing-whats-priced-in/SKILL.md).
- Straddle breakevens versus policy outcomes: compare the lower and upper straddle breaks with the futures settle under each
  discrete outcome (hike, unchanged): e.g. a straddle at 10.75 ticks with breaks 96.08/96.295 vs ~96.09 (25bp hike) and ~96.345
  (unchanged); expiry on CPI day (Citi Markets, Futures Sales: SOFR/CBOT Vol EOD, 21 Aug 2026). A bimodal policy distribution
  hides in a mean-priced path: 115bp of cuts can equal 90% unchanged + 10% a 1.50% outcome (Bassman, The Big 'O', 22 Aug 2023).
- 0DTE check: count how often realised beat the 0DTE implied breakeven and by how much; marginal beats (3 of 5 days by 1.3 ticks)
  = "tough to be long premium".

## 4. Listed hygiene (data defects that fake an RV)
- Mark on listed settle premiums at strikes fixed on the execution bar; on no-print days carry the last premium but report the
  stale fraction per trade; settles can be exchange-model marks.
- Parity check C − P − (F − K) per strike. For American options parity is only an inequality deep ITM: use it as a flag only;
  complete one-sided strikes via parity.
- Historic defects seen: OTM strike offsets mis-scaled by 100x (rebuild the smile from delta-based points); forward-yield jumps
  on contract rolls (drop those days); a flat-smile fallback seam in swaption smile history (ATM stepped 15bp: start the sample
  after it); front expiry rolled inside a "constant-maturity" series (55.9% of long-bond option observations fell outside a 30-90d
  window); notional-coupon changes and CTD shifts contaminate price-vol history; limit-locked days.
- Report BOTH fade and momentum signals ("the sign is a finding"), and cost scenarios (maker 0 / tight 1.5 / taker 2.5 bp).
- Option-package Greeks are model dependent (Bachelier delta/gamma depend on leg correlation); quote carry over several horizons
  and to expiry; check lots/Greeks/notional consistency (Nomura, 19 Jun 2014).
