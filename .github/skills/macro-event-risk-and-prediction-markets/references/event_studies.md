# Event studies and market-specific numbers

Detail behind [SKILL.md](../SKILL.md). All numbers are from the cited documents; samples are small, so use them as priors.
Bracketed sign notes matter: normalise sign conventions before reuse.

## 1. US elections

| Finding | Numbers | Source |
|---|---|---|
| Vol seasonality | G10 FX implied vol +15% late Aug to late Oct in US general-election years; USD rates vol +20-30%; CS rates vol index +60% late Jul-late Oct 1992 | Credit Suisse (Bassman), Building a Better Volatility Mousetrap, 6 Sep 2012 |
| Vol timing | VIX rises from about 50 days before, peaks a few days before, unwinds about 2 months; FX and bond vol rise 25-50 days before then unwind | Willer & Saunders, Trading Global Macro Markets, 2026 |
| Election-day hit ratio at 10d | DXY 93% (n = 14), SPX 86%, MXN 10y 100% (n = 4), 10y UST futures 91% at 1d but 64% at 5/10/22d (n = 11), Bund futures 67% (n = 9). 2016: US rates rose for about 1.5 months | Willer & Saunders 2026 |
| Unified government | USTs underperform into and after unified-government results, more after the first 150 days; USD strengthens | Willer & Saunders 2026 |
| Fed | no pre-election "goosing"; hikes tend to come after; election-year deficit/GDP rise median 1.18% vs 1.16% long run | Willer & Saunders 2026 |
| Midterm scenario map | split Congress limited; D sweep 2y -5 to -7bp, 10y -3 to -5bp (bull flattening); R sweep 2y +7-10bp, 10y +3-5bp (bear flattening) | BofA, Global Rates Weekly, 2 Oct 2026 |
| Midterm event study | 12-16 midterms since 1960; trifecta lost 5 (1994, 2006, 2010, 2018, 2022), held 3; trifecta lost: more persistent post-election rally, 2y reverses about 50 days after; existing trifecta: pre-election sell-off and choppiness | Citi QGMS, How to trade US midterm elections, 14 Aug 2026 |
| Midterm-year performance | US bonds midterm return about -0.02%, vol 2.23%, max DD -17.34%; all-except-midterm 1.74% / 4.04% / R:R 0.43; unconditional 1.72% / 4.62% / 0.37 | Citi QGMS 14 Aug 2026 |
| Post-midterm spreads | 10s30s flattened over the next month in 3 of 5 (2006-2022); 30y swap spreads widened in the next week in 4 of 5 (2014 exception); median back to 0 within a month; refunding falls the day after the 2026 election | Citi Multi-Asset, US midterms on the mind, 2 Oct 2026 |
| Presidential cycle (US10Y since 1964, 15 terms, avg bp) | Y1 +23, Y2 -23, Y3 +6, Y4 -3, full term +2 (n tiny, no significance) | BofA, Technicals Explained primer, 14 Jan 2025 |
| Prediction inputs | Polymarket Dem House 86%, Rep Senate 55% (2026) -> likely lost trifecta; generic ballot +8 Dem | Citi QGMS 14 Aug 2026; Citi Multi-Asset 2 Oct 2026 |

Conflict to resolve before use: Citi's 5s30s midterm path is described inconsistently (figure vs text) and Macro tapas says
rates sell off into the election in trifecta-lost years while QGMS says the post-election rally is more persistent.

## 2. Non-US elections and political events
- **France**: plot 10y OAT-BTP against the (inverted) polling gap of the candidates to read the political risk carried by the spread (Citi, European Rates Weekly, 1 Oct 2026). 2017: long 1m10y straddles paid after the first-round uncertainty lifted vols; 3m10y cheapened about 9 normals since the first round (Citi, US Rates Vol Lab, 1 May 2017). Fitch review of France (A+ stable) before the budget process: change highly unlikely (Citi European Economics Week Ahead, 21 Aug 2026).
- **UK**: Polymarket by-election odds 80-85% for one candidate; gilt ASWs traded well. A non-tightening budget hits gilt ASW; a leadership result repriced 2027 dates about 12bp (JWS Macro, Global Rates Outlook #6, 7 Jun 2026; Central Casting #6.1, 21 Jun 2026).
- **Brazil (EM analogue for event vol)**: 1-day fixed forward vol about 65 per round, about 2.5-3.0% per event; incremental event premium about 1.8 vols over base about 11; 2018 implied about 8% vs realised 3.7%, 2022 implied 6.8% about equal to realised; best entry to sell delta-hedged straddles 4-5 weeks before the vote; calendars/FVAs worked only in Brazil; skew trades mixed (JPM, FX Markets Weekly, 21 Aug 2026).
- **Odds vs market**: Brexit Mar 2016 author 50% vs about 30% priced; Trump 2016 about 40% vs FiveThirtyEight 29%; no-deal Brexit 2019 under 10% -> long GBP returned 9% from 1 Aug to year-end (Papic, Geopolitical Alpha, 2021).
- **Brexit referendum event vol**: see SKILL.md worked example (Darbyshire 2022, Ex 20.7).

## 3. Debt limit, X-date, shutdowns (USD)

Mechanics: before the X-date Treasury cuts bill issuance, uses extraordinary measures (EM) and draws the TGA; cash rises and
collateral is scarce. After resolution the TGA is rebuilt with a bill wave that drains cash (BofA, Funding & debt limit: history
lessons, 27 Jun 2025).

| Item | Numbers | Source |
|---|---|---|
| EM inventory 2025 | $547.6bn total (G-Fund 319, ESF 20, CSRDF & PSRHBF 61.6, one-time Jun-30 measure 147); X-date revised 15 Aug -> 29 Aug; 2-month EM $336.6bn, 8-month $536.4bn | BofA, Debt limit FAQ, 12 May 2025; BofA, X-date shift, 7 Feb 2025 |
| X-date estimation | point estimate with +/-$100bn and $200bn cash bands; cross-check Treasury and CBO; reconciliation can only raise (not suspend) the limit; highly uncertain until after the April tax date | BofA 12 May 2025; 7 Feb 2025 |
| Pre-X-date signals | markets price risk about 2 weeks ahead; bills cheapen 10-15 days ahead; GCF repo up to +20bp (capped near the SRF rate); 1m bill-OIS cheapens in the last days; short sovereign CDS rises; UST yields fell into X-date in 3 of 7 episodes | BofA 12 May 2025 |
| 2023 X-date | bills maturing just after cheapened about 450bp vs just before; 1m bill-OIS swung about -165bp to +60bp in a month; about $500bn bills issued in the month after suspension absorbed at tight bill-OIS | Barclays, US short interest rate primer, Jan 2025 |
| Frontrunning vs shortage | 1m bill yield below GCF, bilateral repo and ON RRP = positioning for the ceiling; true shortage would show EFFR/SOFR/TGCR/BGCR breaking the bottom of the target range | Conks, Collateral Damage, 18 Apr 2023 |
| Resolution averages (1m/3m/6m after) | FF-SOFR about -7.7/-4.4/-5.1bp (negative = SOFR above FF); SOFR-IORB +3.0/+5.1/+5.7; OIS-1m bill -7.5/-4.0/-9.3 (negative = bill yield above OIS, i.e. cheaper bill); 2y UST-OIS +0.5/-0.8/+3.5; 5y -0.1/+0.2/+3.3. 2019 distorted by Fed repo intervention (Sep-19) | BofA 27 Jun 2025 |
| Analog method | match on state variables (ON RRP excess liquidity, bill supply growth: 2017-2019 matched, 2021/2023 not); merge episodes only months apart; average 1m/3m/6m change using 1m moving averages; study stress analog separately | BofA 27 Jun 2025 |
| Trade | short Oct-25 SOFR/FF basis (SOFR futures price minus FF futures price), entry -4bp, target -8bp, stop -1bp; risks: later resolution, slower TGA rebuild; October contract also captures Q3 quarter-end | BofA 27 Jun 2025 |
| Next ceiling | limit $41.1tn vs about $39.9tn subject, $1.2tn headroom; EM and TGA drawdown from about May 2027, X-date likely Q4 2027 | Citi Multi-Asset, US midterms on the mind, 2 Oct 2026 |
| Shutdown | not the debt limit; about 0.1pp GDP per week; does not affect issuance; vol-negative because data are delayed (gamma cheapened Sep-Oct 2013) | BofA 12 May 2025; Citi US Rates Vol Lab, 1 May 2017 |

## 4. FX intervention (JPY and others)
- Escalation ladder: "excessive and disorderly" -> close monitoring -> rate checks -> "determined action" -> intervention confirmed after the fact (Willer & Saunders 2026, Ch.13).
- Levels: above 160 possible, above 162 Citi puts intervention above 50%; EURJPY warning zone 185-186 (Citi, Japan FX, Bessent's plans, 14 Aug 2026).
- USD-buying regressions (change in yield, bp, on size x in JPY bn; 30 episodes; the JPY-supportive case at 160 is USD-selling, 9 episodes): 2y -0.0022x + 0.29 (R2 0.50), 5y -0.0034x + 1.91 (0.51), 10y -0.0033x + 2.60 (0.46); USD-selling R2 0.12 / 0.0008 / 0.04. Swap spreads R2 about 0-0.07. Episodes: 22 Sep 2022 JPY 2,838bn: 2y +7, 5y +25, 10y +18bp; May 2024 JPY 9,789bn: 2y -25, 5y -17, 10y -26bp; 8 Dec 2003 JPY 17,451bn: 2y -40, 5y -58, 10y -55bp (BofA, FX intervention primer: G10, 8 Jul 2024).
- Efficacy: coordinated beats unilateral; signalling beats size; only work with a macro tailwind (rate differential); intervention is sterilised (Willer & Saunders 2026; BofA 8 Jul 2024).
- Triggers and constraints: concerted G7 interventions came when JPY REER was >= 2 sd from its 5-year mean; IMF "free floating" rule (at most 3 interventions per 6 months, each at most 3 days) is not safe to bet on; ammunition accounting (JPY 25.5tn used of a 30tn base, 36tn practical limit); timing heuristic: equities neither rising nor falling (Citi, Japan FX, 3/4 Aug 2026; Citi, What next for JPY?, 3 Aug 2026; Citi, Japan FX Viewpoint, 19 Aug 2026).
- BoJ 18 Sep pricing went from about 50% to about 80% after the joint intervention (Citi, 3 Aug 2026 and week-ahead cheatsheet, Aug 2026).
- CHF: SNB intervenes via EUR/CHF; proxy = sight deposits (BofA 8 Jul 2024).

## 5. Geopolitics, tariffs, disasters, buybacks
- GPR spikes (Caldara-Iacoviello) mean-revert quickly; fade unless oil is involved. Oil spikes from geopolitics (10 events 1973-2022): median peak +38.8% in 38 days, 3m change +13.2%; oil +30% in 3m: bonds underperform into day 0 then track the unconditional path (Willer & Saunders 2026).
- Tariffs: Trump 1.0 (11 dates): bonds up (US 7-10y +0.7% at 10d/22d, Bunds +0.8%/+1.2%). Liberation Day 2 Apr 2025: US 7-10y +0.9% at +1d then -0.9% at +5d; Bunds +0.9/+1.4/+1.0% at 5/10/22d; DXY -4.7% by +10d. Do not be dogmatic about which market outperforms (Willer & Saunders 2026).
- Headline posts: median 30-min 2y range 0.6bp (posts) vs 0.4bp (random); 95th percentile 2.7 vs 1.7bp; Apr-May 2025 IQR about 6x later; impact decays within about 2 months (JPM, Comfortably numb, 24 Jul 2026).
- Hurricanes: delta-hedged 3m10y straddles bought at landfall of the 10 costliest hurricanes mostly lost money (JPM, Issuance, pensions, and long-end spreads, 14 Sep 2018).
- Extreme stress: VIX > 35 together with a daily US rates sell-off > 15bp (1998, 2008, 2020) signals liquidity problems or forced RV deleveraging (Willer & Saunders 2026).
- Off-cycle buyback doubling (19 Aug 2026): 10-30y buckets $2bn to at least $4bn; 30y -8bp to 5.21%, 10y -4bp, DXY -0.7%, bills cheaper; yields later returned to pre-announcement levels. Pattern: long-end rally, bills cheapen, flattening, weaker USD (FT, US Treasury to boost long-term bond purchases, 19 Aug 2026).
- "Vibes" sell-offs: three in about 24 months; technical Treasury tools are likely insufficient against a political-uncertainty premium (Geopolitical Cousins podcast, about Sep 2026).

## 6. Liquidity around events (USD, EUR)
- Payrolls worst tier; middle tier prelim GDP, ADP, CPI, ISMs; FOMC: depth falls into 2pm and does not recover through the press conference; volume doubles, price impact about 2x, realised vol about 2x (JPM, When the going gets tough, 5 Nov 2019).
- Into 8:30 payrolls top-3 depth falls to under 1/4 of base; recovery time grew from 1-2 minutes to 15-30 minutes (JPM 5 Nov 2019; JPM, Far from the shallow now, 12 Apr 2019).
- Off-meeting cut 3 Mar 2020: depth collapsed to overnight levels, only partly recovered by noon; 3Mx10Y vol up over 20bp; 10y breached 1% (JPM, mini 'Flash Rally', 5 Mar 2020).
- ECB days: pre-commitment day activity 5x average as the press conference ended; 5 Jun 2014 peak 8.5x average about 2h after the start; the two days after (9 May and 6 Jun) traded EUR 27.1m DV01 combined, about 13.6m a day, vs a EUR 10.1m daily average: stay late on the day after (Clarus Financial Technology blog, ECB June Meeting, 18 Jun 2014).
- FOMC price discovery: post-FOMC 60-min incremental price impact up 48-118% (buys, 4 of 6 securities) and 24-134% (sells, all six) vs control windows (Fleming, Mizrach & Nguyen, FRBNY Staff Report 381).

## 7. G10 snapshots (meeting pricing, mid-2026, as published)
- Jun 2026: ECB July gap 6bp; BoE about 7.5bp for Jun/Jul "about fair"; BoJ June hike 24.4bp (97%+); RBA Aug 6.75bp; RBNZ July 20.5bp; Riksbank +2bp; Norges +5bp (Citi, STIRT Weekly, 12 Jun 2026).
- Aug 2026: Fed Sep hike about 39-40% (JPM thinks a bit high); ECB 10 Sep +24bp priced; Riksbank about 50% Sep hike priced, expected to moderate after a dovish statement; RBA house view one final 25bp hike in November; RBNZ 2 Sep JPM +25bp; BoC 2 Sep hold at 2.25 (JPM, US Weekly Prospects, 21 Aug 2026; Citi cheatsheet, Aug 2026).
- ECB-dated EUR RFR swaps, 19 Jun 2025: Jul25 1.907%, Sep25 1.805% (-10.1bp by meeting), Oct25 1.772%, Dec25 1.698%; about one cut priced -> receive (Nordea, 19 Jun 2025).
- Release times: UK 0930 GMT, US 1330/1500 GMT, Eurozone 0700/0900/1000 GMT; EUR-specific movers IFO (4th week) and ZEW (2nd/3rd Tuesday) (Aikin, STIR Futures, 2012).
- Calendar hygiene: mark the "last print before the meeting" (e.g. August flash PMIs before the September ECB); record house forecast vs consensus (the gap is the event-risk signal); EZ composite PMI above 52 is consistent with about 0.4% q/q GDP (Citi, European Economics Week Ahead, 14 Aug 2026).
- Supply weeks stack with events: US $211bn across 2y/5y/7y/FRN in 24-28 Aug 2026; since 2022 SPX realised move on 20y auction days averaged +/-77bp, 9bp above long run (Citi, Mid-week musings, 19 Aug 2026).
