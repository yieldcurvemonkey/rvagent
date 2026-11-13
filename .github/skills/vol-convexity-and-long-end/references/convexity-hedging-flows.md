# Convexity-hedging flows: sizing and where they show up

Loaded from [SKILL.md](../SKILL.md). Scope here is sizing and the rates/vol footprint. Full mortgage mechanics
(OAS/OAD/OAC, dollar roll, coupon stack) live in [flow-mbs-convexity-hedging](../../flow-mbs-convexity-hedging/SKILL.md);
callable/structured-note vega supply in [vol-structured-flows-and-vega-supply](../../vol-structured-flows-and-vega-supply/SKILL.md);
pensions/insurers/banks in [flow-structural-alm-demand](../../flow-structural-alm-demand/SKILL.md).

## 1. Hedge-need arithmetic (MBS-style, any negatively convex book)

```
10y-equivalents ($bn) = duration x notional ($bn) / 10
new duration          = old duration + (move_bp / 100) x (-convexity)     # convexity quoted in "MBS points": 30y UST 0.06 -> 6
hedge need ($bn 10y-eq) = old 10y-eq - new 10y-eq                         # negative = sell duration (sell-off), positive = buy (rally)
```
Example (BofA, MBS convexity hedging primer, Mar 2021): duration 7, $100bn hedged, convexity -2. Base 10y-eq 70.
+25 / +50 / +100bp gives duration 7.5 / 8 / 9, 10y-eq 75 / 80 / 90, hedge need -5 / -10 / -20 $bn (sell). Reproduced by
`mbs_hedge_need()` in [scripts/convexity_screen.py](../scripts/convexity_screen.py). Flow size depends on (1) size and speed
of the move, (2) convexity of the outstanding stock, (3) share that is duration-hedged.

Hedging need for a 25bp move ($bn 10y-eq; pipeline / MSR / REIT / money manager / total / % of UST market):
Jun 2003 53/28/1/87/169/10.1%; May 2013 23/25/18/39/105/1.7%; Feb 2021 37/6/7/13/63/0.5% (BofA primer). Do not over-attribute
current moves to MBS hedging: the share of the UST market is a twentieth of 2003. A later estimate: $40-50bn 10y-eq per 25bp
rise from hedgers ex Fed/banks/money funds/overseas, only ~0.5% of the 30y conventional universe 50bp or more in the money
(Sep 2026; Barclays, Swap spreads, Sep 2026).

## 2. Direction and footprint by hedger

| Hedger | Convexity | Rally | Sell-off | Where it shows |
|---|---|---|---|---|
| MBS holders (GSEs, REITs, money managers, banks) | short | buy duration (receive/buy UST) | sell duration (pay/sell UST) | swap spreads (pay-fixed pushes them wider), 3y10y vega, intermediate spreads, OAS |
| Originator pipeline | short | sell TBA/UST at pull-through weight (70% of $1bn = $700mm), pull-through moves ~5-6% per 15bp, rebuilds ~45 days after exhaustion | | UST/swaps via dealers |
| Servicers (MSR, IO-like) | most negative just before refi starts (BofA); JPM notes MSRs can trade with positive convexity at other levels, forcing them to pay as rates fall and offsetting GSE receiving | sign depends on where the stack sits versus the Vortex | | non-banks (~60% of the market) hedge infrequently; near the "Convexity Vortex" they switch from buying OTM payers to OTM receivers so payer skew flattens or inverts |
| Banks (assets short convexity, deposits long) | net short | receive | pay | swap spreads and basis; threshold-based, infrequent, so catch-up risk and rally-biased narrowing (JPM, Is bank convexity hedging lying in wait?, May 2019) |
| Variable annuities | short rates gamma scaled by equity level | duration extends when equities fall: receive ~20y | | 15y5y/20y10y steepens in equity sell-offs; 30y spreads narrow |
| Long-dated callables (Formosa-style) | dealers long convexity | callables shorten: dealers pay fixed | receive | resists moves; vega supply on long expiries |
| Programmatic short-gamma | short | | | single-day flows (e.g. 1Mx10Y ATMF straddles sold daily) |

- Dynamic hedgers mostly act on net moves above ~20bp, path-dependent versus their last rebalance, and "tend not to be involved until rates have re-priced materially"; fast rallies can outrun them (JPM, Dynamic hedgers are long, banks are short, Sep 2019; Markets struggle to feed the convexity beast, Feb 2020).
- Direction test: are 10Y swap spreads trading directionally with rates? If counter-directional, hedgers are not yet active (funding easing can mask the flow) (JPM, The return of convexity hedging, Jan 2020).
- Peak MBS negative convexity sits ~70-100bp below the then-current level; once the stack moves out of the money the convexity bias is to the downside, so duration buying in a 50bp rally far exceeds duration shedding in a 50bp sell-off (JPM Mar 2019; Barclays Global Rates Weekly, Oct 2026). Negative convexity helps bear-steepening "in much the same way as it drives bull flattening in a rally".
- Low implied vol makes MBS more negatively convex (option gamma up), so hedging acts as an accelerant in a shock (Bassman, It's Never Different This Time, Jan 2018). The prepayment option drives rates vol: every $100mm of new MBS is homeowners buying vega equal to ~$50mm of 3y x 10y straddles (Bassman, The Largest Volatility Sale Ever, Mar 2010).
- Positioning rule of thumb: flows resist moves for callables/long-gamma hedgers and amplify them for MBS/VA/bank hedgers. Net flow = amplifiers minus callable offset (JPM, A comprehensive look at convexity hedging, Mar 2019: >$200mn/bp of duration demand since the late-2018 peak, mostly MBS, with >$100mn/bp callable offset in a month; VA delivered >$150bn 10y-eq in ~a month at the 2020 peak).

## 3. Market-by-market (G10)

USD is the only G10 market where MBS, VA and Formosa-style callables are the dominant convexity flows. EUR: Dutch/Danish
pension regulation (market-rate discounting, UFR 4.2% in 2012, later 3.9%) imposes short convexity on pensions: they
buy duration as yields fall (Düring 2021); ALM receiving at 20y is the risk to paid 20y bellies, and "a severe equity meltdown could trigger such receiving" (Nordea, EUR Rates Flash, May 2019). GBP: LDI/pension flows dominate 30y+, pro-cyclical (UK 30y+ gilts £131bn, 12% of the market; JPM, Valuing convexity, Feb 2018). JPY: life-insurer target buying caps long yields. CAD, AUD, NZD, CHF, SEK, NOK: no long-end convexity-flow material in the sources: check local pension/insurer and covered-bond/callable issuance before assuming any.
