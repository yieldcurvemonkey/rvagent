# Energy, oil supply and cover, scenario anchors, and per-currency notes

Companion to `SKILL.md`. Covers the oil and gas side: the supply and cover framework, the refining chain, the
diesel and freight pass-through detail, dated scenario anchors, and currency-specific notes. Every figure is as
reported in the cited source and dated; the anchors go stale quickly, so re-read the cited note before use.

## 1. Oil: what "price" means

- "Oil" is not one commodity. It covers crude, condensate, NGLs, refinery gain and biofuels. Crude and condensate
  get most attention, but products drive inflation (JPMorgan, Oil Primer, 14 Jan 2025).
- Crude quality: graded by API gravity (lower API = denser, heavier) and sulfur (sour vs sweet). Light sweet
  crude trades at a premium: easier to refine, more high-value light products. Most global reserves are sour; the
  most-quoted benchmarks are light sweet (JPMorgan, Oil Primer, 14 Jan 2025).
- Cut-offs are inconsistent in the source: the taxonomy uses sulfur 0.5% for sour/sweet, the refining grid uses
  0.7%. Use the grid only with the source's definitions.

**Refinery yield by crude grade** (output shares: propane/butane / gasoline / distillate / HFO-other; EIA data as
shown in JPMorgan Oil Primer, 14 Jan 2025; figures read from rotated scans, so approximate):

| Crude class | Examples | API | Share of demand | Yields |
|---|---|---|---|---|
| Light sweet | WTI, LLS, Brent | >34 | 35% | 3 / 32 / 30 / 35 |
| Medium sour | Mars, WTS, Arab Medium, Basrah | 24-34 | 50% | 2 / 24 / 26 / 48 |
| Heavy sour | Maya, Cold Lake, WCS | <24 | 15% | 1 / 15 / 21 / 63 |

Complexity tiers (output shares, same source): hydroskimming 4 / 32 / 32 / 32; catalytic cracking 8 / 43 / 30 / 19
(runs more sour crude, gains volume); coking 6 / 47 / 33 / 14 (runs heavier, sourer crude for the highest light
yield).

**Why it matters for inflation.** A refinery's margin depends on which products are short. A diesel squeeze can
hit before aggregate stocks fall, so the product split, not the crude price, carries the inflation signal.

## 2. Crack spreads and all-in cost

- Crack spread: product price minus crude. The 3-2-1 crack (standard convention, external) is
  `(2 * RBOB + ULSD) / 3 - WTI`, with RBOB and ULSD in $/gal converted to $/bbl (x 42).
- All-in oil cost = crude + refinery cracks weighted by yield (Citi, Oil Monitor, 19 Aug 2026).
- Citi's readings (19-21 Aug 2026): all-in about $120/bbl, up about 80% YTD from $67; weighted refinery margin $33
  vs $7 at start-2026; diesel $172/bbl, up about 105% YTD; refining margins up about 350% YTD.
- Spot oil is a poor stress gauge on its own. Demand destruction, reserve policy and Hormuz workarounds can keep
  spot calm while the system is stressed. Citi (FX, 20 Aug 2026) says normalised spot oil "has created too much
  complacency" and reads crack spreads as the clearer stress sign.

## 3. Days of cover

**Definition.** `cover_days = inventory / demand_per_day`. Inventory is expressed in days of demand covered.

**Reference points.** About 70 days of cover was the level in the 1970s-80s second oil shock, when energy spend was
about 8% of GDP. Citi equates 70 days with an all-in price above $200/bbl (Citi, Oil Monitor, 19 Aug 2026).

**Linear extrapolation** (Citi's method). Observed global draws were 519m bbl from Feb to Aug 2026: an average of
-87m bbl/month, about -2.9 mb/d (87 / 30). Extrapolating the draw:

    cover(T) = (S_0 - r * T) / D        r = observed draw per day, D = demand per day, T in days

Citi's outputs on this trend: OECD about 70 days by end-2027 (83 days in Aug-26, falling to 58 by 4Q28E); ex-China
by mid-2028; global by 1Q29. The authors call this timeframe "more prudent" because draws are partly unobserved
and the IEA SPR release has ended. Their earlier projection assumed a 7-8 mb/d deficit, which put ex-China at 70
days by 1Q27.

**Caveats (from the source and from the arithmetic).**
- Linear extrapolation overstates precision. Treat a cover date as a range, not a point.
- Aggregate cover hides product shortages. Track product inventories and cracks separately.
- Reported stocks at Aug 2026 (Citi): commercial crude +4.4m bbl to 428.8m; SPR 293.4m, down from 415m in Feb-26;
  refinery runs a record 17.4m b/d.

**China import cut (WSJ, The Iran Oil Shock and China, 21 Aug 2026).** Crude imports cut 5.8 mb/d (-48.9%) from
about 11 mb/d in 2025. Check: 5.8 / 11 = 52.7%, not 48.9%. The stated percentage implies a base of about 11.9 mb/d.
Verify the base before using either number. Other data: Middle East share of imports fell from 59% to 29%; state
refinery runs 71.6% in May (lowest since Covid); reserve draws about 56m bbl commercial and 15m bbl refinery since
May; SPR largely untouched; total reserves estimated at 1.0-1.4bn bbl. The WSJ claims China's import cuts were
pivotal in capping oil prices and so global inflation; treat as the article's claim.

## 4. Oil volatility and supply shocks

- Oil volatility, not only the level, is inflationary. Prices are downwardly sticky, so volatility ratchets measured
  and core inflation up, and markets reprice hikes in proportion to oil shocks (BofA, Fog of War, 2 Oct 2026).
- Oil explains more of its own variance through supply shocks than base metals or gold do, so business-cycle rules
  work less well for oil. OPEC holds about 40% of supply, OPEC+ above 50% (Willer & Saunders, Trading Global Macro
  Markets, Ch.14, 2026).
- Path dependence: a temporary hit is manageable; weeks of elevated Brent force action; even immediate resolution
  leaves months of supply-chain disruption (JWS, #3 Iran and Front-End Rates, 8 Mar 2026).
- Price vs quantity (JWS Outlook #5, 10 May 2026). Domestic variables: (1) labour tightness and wages (tight =
  price; wage catch-up = persistence; real-wage compression = quantity); (2) household balance sheets (strong =
  price); (3) corporate margins and pricing power; (4) fiscal (cushioning = less quantity now, more price risk
  later); (5) central-bank reaction and expectations (credibility buys time). Ranking: US closest to price; UK
  mixed; EZ more quantity but the ECB pulls to price; CAD, NZD, SEK toward quantity; AUD and NOK toward price.
- Second-round channels after an energy shock (JWS #3, 8 Mar 2026): (1) FX pass-through (terms of trade: short
  importers, long producers; FX divergence about one month after the shock once risk stabilises); (2) fiscal
  response (tax cuts, price caps, cash support -> more issuance -> ASW pressure); (3) activity hit (direction
  negative, size unclear).

**Demand side (JPMorgan, Oil Primer, 14 Jan 2025; approximate).** Global demand 99.8 mb/d in 2022, forecast 108.5
mb/d in 2035. Gasoline demand peaks at 26.3 mb/d in 2024 and falls to 24.7 by 2035. Demand growth 2023-2035 by
product (mb/d): jet/kero +2.4, naphtha +1.7, LPG +1.4, other +1.3, diesel +0.6, fuel oil +0.4, gasoline -0.7.
Nowcast inputs: gasoline demand correlates with unemployment historically, but since the pandemic cell-phone
mobility and road-congestion data are the stronger indicators; jet demand from scheduled and cancelled flights; US
rail carloads and German truck toll mileage (y/y). Gulf Coast refining and production carry hurricane exposure.

## 5. Diesel and freight pass-through (Barclays, 1 Oct 2026)

**Three steps.**
1. Freight exposure, from two lenses:
   - Lens 1, transport margin as share of purchaser value (BEA bridge): furnishings and durables about 4-5%; other
     nondurables just over 4%; motor fuels 2.5-3.5%; food-at-home 1.5-2.0%; services negligible. Detail: games and
     toys about 15%, clocks and lamps about 10%, small appliances 7-8%.
   - Lens 2, upstream freight intensity (Leontief inverse of BEA input-output for truck, rail, water and courier as
     share of producer value): food-at-home about 7.2%; motor vehicles and furnishings 4-5%. Excludes freight
     provided overseas.
2. Diesel share of operating cost: trucking 20-30%, rail 10-20%, water 10-20%, courier 15-20%, airlines about
   one-third.
3. Consumer pass-through assumption, attenuated by margin compression, inventories, sourcing changes and contracts.

**Generic form of the chain (derived; the source does not print this equation).** For category c,

    dP_c ~ rho * F_c * s_d * dDiesel       (log changes)

where F_c is the freight share from the chosen lens, s_d the diesel share of carrier cost, and rho the consumer
pass-through. The headline effect is the weight-averaged sum over categories. Use the source's category outputs
below rather than rebuilding the sum without the full category weights.

**Result for a sustained 80% diesel shock** (cumulative price-level effect; Barclays, 1 Oct 2026):

| Case | Pass-through | Cost shares | PCE | Core PCE |
|---|---|---|---|---|
| Low | 50% | low end | +0.12pp | +0.10pp |
| Mid | 75% | midpoints | +0.20pp | +0.15pp |
| High | 100% | top of ranges | +0.31pp | +0.23pp |

Authors lean mid-to-upper: headline 20-30bp, core 15-20bp (or 15-23bp), mostly in 2027.

**Regression for CPI sensitivity to diesel.** Regress monthly changes in each NSA CPI component on diesel changes,
lags 0-3 months. Orthogonalise diesel against crude and gasoline first. Controls: crude, gasoline, seasonal
dummies, NY Fed GSCPI. Result: pass-through appears only in CPI fuel oil and other motor fuels. No robust core
category effect. The 2021-22 goods exposure disappears once GSCPI is controlled (correlated, not causal). A naive
CPI-on-diesel regression picks up oil volatility.

**Diesel context (Barclays).** Diesel +80% YTD (above the $6.5/gal record); Russian middle-distillate exports -0.6
mb/d y/y; US net diesel plus jet exports +380 kb/d y/y (Jan-Jul 2026); fuel surcharges FedEx Freight 61%, Union
Pacific Sep intermodal 55.5%. Freight- and fuel-exposed categories are 18% of PCE prices and 20% of core PCE.

**Fixings-based check (Barclays, data 29 Sep 2026).** Headline and ex-energy SA m/m (bp) vs Barclays core forecast:
Sep-26 55 / 19 / 20; Oct-26 18 / 21 / 23; Nov-26 11 / 21 / 23; Dec-26 24 / 23 / 23; Jan-27 13 / 41 / 21; Feb-27
10 / 23 / 21; Mar-27 21 / 22 / 21; Apr-27 13 / 7 / 19; May-27 14 / 22 / 19; Jun-27 11 / 18 / 19; Jul-27 14 / 21 /
19. Jan and Apr 2027 are distorted by RBOB curve shape and energy seasonals. Ex-energy proxy: 18-23bp m/m in 9 of
the next 11 months; applying a 15bp core-PCE pass-through to core CPI adds about +1bp m/m.

## 6. Gas and European energy

- EUR inflation is more gas than oil. Bunds track natural gas more than oil as crack spreads widen (Citi, European
  Rates Strategy, 20 Aug 2026).
- TTF at 57 tracks the ECB adverse case (JWS Update #7, 19 Jul 2026). TTF +12% WoW lifted UK and EUR front ends
  (Citi STIRT, 21 Aug 2026).
- Compare the market-implied gas path (EUR/MWh) with the ECB baseline, milder, adverse and severe paths.
- Broadening shock monitors (JWS Update #7): TTF; the Rhine at Kaub below about 1m with barge rates about tripled
  and French nuclear outages; wheat (about 30% of world wheat via the Black Sea; export season Aug-Nov); crack
  spreads (LS gasoil vs Brent, RBOB vs WTI, 3-2-1), watched as products, not crude.
- Geopolitics rule (Willer & Saunders, Ch.5-7): fade geopolitical risk unless oil is involved; oil spikes hurt bonds
  but rarely cause recessions.

## 7. Dated scenario anchors (re-check before use)

| Source, date | Anchor | Implication |
|---|---|---|
| JWS #3, 8 Mar 2026 | $10 Brent move | about 30bp on near-term y/y EZ HICP |
| JWS #3, 8 Mar 2026 | $70 -> $90 in one week | EZ 2026 HICP path repriced 70-85bp higher; Q3 HICP from about 1.8% to 2.5% y/y |
| JWS #3, 8 Mar 2026 | Brent about $110 | where HICP would break 3% |
| JWS Outlook #5, 10 May 2026 | BoE scenario C | Q2 average $127; above $100 through 2028; CPI peak about 6% early 2027 |
| JWS Outlook #5, 10 May 2026 | ECB mapping for the Dec-26 Brent future | baseline about $75, adverse about $92, severe $115-120 Brent (non-linear) |
| JWS Outlook #5/#6, May-Jun 2026 | Dec-26 HICP 3.6% with the Dec-26 Brent future at $87; Brent above $95 gives HICP above 4% | adverse case |
| Citi Global Resilience, 20 Aug 2026 | base Brent 3Q26 $80, 4Q26 $70, 2027 $65; bull above $100; wildcard $150+ | upside inflation, downside growth |
| Citi Top of Mind, 21 Aug 2026 | Brent above $92; base deal in 4Q26 -> Brent $60s in 2027; bull $110 | |
| Barclays Energy Sigma, 1 Oct 2026 | Brent Q4-26 $115 (2026 average $100; 2027 $85); quarterly 2027 path 90/85/85/80 | Gulf net exports 19.2 mb/d (83% of pre-war) |
| GS cuRated, 3 Oct 2026 | Dated Brent near $120; base $85 year-end; $80 in 2027 | |
| JPMorgan Monthly, 13 Aug 2026 | Brent $85 average 2026, $63 in 2027, $55 by end-2027 | |

Use anchors as scenario inputs, never as the forecast itself. The 2027 Brent averages in these notes range from $63
(JPMorgan) to $85 (Barclays), so the scenario spread matters more than any single path.

**Mapping method.** Pick a Brent or gas path. Convert it to headline m/m with Section 2-3 of `SKILL.md`
(energy weight x energy change; oil rule; diesel chain). Compare the resulting headline y/y with the central bank's
baseline and its trigger. The trigger is the bank's own threshold, not an inflation-model output.

## 8. Price vs quantity, and inflation regimes

- Commodity inflation regime (Willer & Saunders, Ch.14): long commodities when CPI is above 3% and above its
  five-month moving average. Information ratio 0.32 to 0.66, active 22% of the time; captured the 1970s and part
  of 2022. The rule breaks in high-inflation cycles.
- Money-gap (P-star) model (Hudson Bay Research, Jul 2026): gap = P-star minus the actual price level, with V* and
  Y* from one-sided HP filters (real time). Expected annualised inflation rises about 10bp the following quarter per
  1pp gap (gamma about 0.10; t 3.95 on GDP-based M2, 3.88 on PCE-based M2 with gamma 0.12). R2 about 0.18-0.19, so
  most quarter-to-quarter variation is non-monetary. The model cannot separate monetary policy from money financing
  fiscal deficits; use as a cross-check.
- Supply-shock rule (Hudson Bay Research): a temporary effect on inflation (not on the price level) can be looked
  through; a recurring shock beyond policy lags should move policy restrictive.
- Debasement basket (Citi Markets, c. 21 Aug 2026): higher gold, lower USD, steeper UST curve, higher UST
  breakevens, higher S&P; basket = average of risk-adjusted returns of the five. The source does not give the
  normalisation; use a z-score per gauge if you rebuild it, and say so. Good debasement = long end stabilised with a
  hawkish Fed; bad = acute long-end weakness with a dovish Fed (higher breakevens, bear steepening).

## 9. Per-currency notes

**USD.** Fed targets PCE (headline and core) plus robust measures; core PCE tracking 3.4% vs median 2.8% and trimmed
mean 2.3% (Jul-2026, JPMorgan). The incoming Fed chair targets the underlying 12-month trend (BofA); underlying estimate 2.5%. US
diesel pass-through appears only in CPI fuel oil and other motor fuels; gasoline dominates monthly CPI energy
volatility. US 5y5y CPI just below 2.45%; 30y TIPS real about 3% (JPMorgan, 13 Aug 2026). Market headline CPI swaps
sit above Citi's forecast through mid-2027; Citi sees core PCE at 3.1% in Q4-26 and 2.2% by late 2027. Citi and
others say CPI is the signal the market trusts over PCE; the two "should not be expected to permanently diverge"
(Citi, US Economics, 21 Aug 2026).

**EUR.** HICP and FCPI swaps: 2s5s HICP flattener; 5Yx5Y FCPI-HICP widener; 10Yx10Y HICP range-bound about 2.35%;
5Yx5Y HICP 2.10-2.20% range (JPMorgan, 13 Aug 2026). Food is 15.5% of HICP and food inflation is absent (ag prices
falling): the main risk to an energy-led view (JWS Outlook #6, 7 Jun 2026). ECB is the most energy-sensitive G4
central bank; Bunds track gas. Euro-area flash HICP forecast 3.3% headline and core about 2.5% (Citi, Week Ahead,
21 Aug 2026), driven by fuel and gas and negative base effects. Country prints: France HICP 2.6% (Aug P); Spain HICP
4.5%, CPI 4.2%, core 3.0%; Belgium HICP 4.1%. April-27 HICP fixing (the next year's low point) repriced 1.75% ->
2.5% since July; Dec-26 HICP fixing about 50bp below the May ceiling (JWS Update #7, 19 Jul 2026).

**GBP.** UK 1Yx1Y RPI fair value (12 months): `1Yx1Y RPI = 0.3 * 1Yx1Y SONIA - 0.0001 * front Brent + 0.004 * UK
NatGas + 1.94`, R2 87%, standard error 8bp (JPMorgan, 13 Aug 2026). The source does not state the units of Brent
or gas, and the Brent coefficient is so small that the units decide the answer. Do not use it without the source's
units. Partial betas are choppy over short horizons. 1Yx1Y RPI was 10bp above its 3-month average, with a 35bp range
over recent months. RPI-CPI wedge: CPI implied from RPI swaps is RPI minus a 0.8% median historical wedge, and the
wedge has a beta to the inflation level (JWS Outlook #5). RPI swaps peak at 5.1-5.3% in early 2027; energy shock
priced to lift RPI 80-120bp by Q3 (JWS #3, JWS Outlook #5). OFGEM caps delay pass-through. migration of a long-dated linker into
the 15Y+ linker index supported long-end breakevens; expected to abate. BoE scenario C has CPI peaking around 6% in early
2027; scenarios A and B about 3.5%, below 2% by 2028 (JWS Outlook #5).

**JPY.** Core-core CPI 1.9% y/y (first strengthening in nine months); core 1.8%; headline 1.9%; naphtha-driven
pass-through into consumer goods (FT, 21 Aug 2026). JGBi liquidity is thin, so BEI is vulnerable to flow-driven
declines; BEI range-bound near 200bp; 10y inflation swap about 1.85%; 5y JPY inflation swaps cycle-wide at 2.35%
(JPMorgan, 13 Aug 2026; JWS Outlook #5). Consumption-tax cut from 8% to 1% (April 2027): core CPI effect `w * (P_new /
P_old - 1) = 0.201 * (101/108 - 1) = -1.3pp` (JPMorgan, 13 Aug 2026; weight 20.1%). FX support can push the BoJ to
hike ahead of schedule (FT, 21 Aug 2026).

**CAD.** July 2026: headline 3.0% y/y (gasoline +25.7%, travel tours +15.2%); CPI-trim, CPI-median and CPI ex
food/energy/indirect taxes at or below 2%, read as evidence the economy does not need higher rates (Citi Canada,
21 Aug 2026). Leads: sales-to-new-listings ratio (6-month lag) for home prices; new home prices (1-month lag) for
CPI homeowners' replacement cost; CFIB price plans (3-month lag) have diverged from core and track oil. US CPI
airfares lead Canadian airfares by about 3 months (the recording convention differs; Citi Canada, 13 Aug 2026).

**AUD.** Energy exporter with a low energy CPI weight (about 5%); AUD 1y1y sold off almost as much as any curve (JWS
#3). Short end neutral; favour the belly and long widening; 2035/2040 BEI trade below RBA band midpoint; long-run fair
value 2.5%; AU-US real spreads narrow vs 1Y swap differentials (JPMorgan, 13 Aug 2026).

**NZD.** No inflation-specific data in the notes.

**CHF.** Energy CPI weight near the bottom of the cross-market screen (about 5%) (JWS #3). No other CHF inflation
data in the notes.

**SEK.** Only Q2 GDP (1.4% QoQ) on the EU calendar (Citi, Week Ahead, 21 Aug 2026). Not an inflation input in the
notes.

**NOK.** Energy CPI weight near the bottom (about 5%); energy exporter; NOWA sold off to cycle wides with AUD (author
receive) (JWS #3). Mainland GDP 0.3% QoQ on the EU calendar, not an inflation input.

## 10. Breakeven and linker reference points (as reported)

- US: 5y5y CPI just below 2.45%; 30y TIPS real about 3%. US commodity beta (JPMorgan, 13 Aug 2026): 1-month
  rolling partial beta of 1Yx1Y, 2Yx3Y, 5Yx5Y and 10Yx20Y ZC inflation swaps to a commodity index, controlling for
  the OIS curve (3Mx3M, 15Mx3M) and VIX level. Front-end betas have fallen and converged with the belly and long end.
- Carry as a contrarian: carry below -9bp was a contrarian signal for breakeven widening over five years
  (JPMorgan, 13 Aug 2026). The carry definition is not reproduced in the notes; check it before use.
- JPMorgan's breakeven forecasts: US TIPS 10y 217 now, then 205 / 200 / 195 / 195 (Sep-26 to Jun-27); UK 10y 339
  -> 330 / 330 / 330 / 320 (labelled % in the source, read as bp); France 10y 227 -> 225-240.
- Barclays (2 Oct 2026): short 5y breakevens (energy-hedged) into later-October supply. ISM prices-paid nowcast with
  diesel and BCOM: AR(1) alone about 70; with diesel and BCOM 75.1; actual 77.9; survey median 73.0.
- Breakevens and the policy cycle (Willer & Saunders, Ch.5): collapse in deep recessions and rebound fast; rise
  before the first hike and into its early part; fall once the Fed hikes in earnest; widen in easing cycles into a
  soft landing (2024). Large oil component; correlate with copper.
- Linker illiquidity (Willer & Saunders, Ch.5): in stress real yields spike while nominals rally (2008, 2020),
  depressing breakevens; helps short-breakeven positions into hard-landing cutting cycles.
- Historical linker (Duering, Ch.23): a 1780 Massachusetts soldiers' bond indexed to a basket of commodity prices,
  `I_M = 5 p_corn + 68 4/7 p_beef + 10 p_wool + 16 p_leather`, rescaled to `S = (I_M / I_0) * 499.14` with `I_0 =
  130` pounds, no floor. Sovereigns issue linkers partly because progressive taxes make the government naturally
  long inflation.
