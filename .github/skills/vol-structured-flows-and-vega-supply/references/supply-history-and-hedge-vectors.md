# Vega supply: data tables, hedge vectors and trade log

Supporting detail for [SKILL.md](../SKILL.md). All numbers are as printed in the cited notes. Vega is in USD per
1bp of normal vol unless stated. "Normals" and "nv" are bp of normal vol.

## 1. Bucketed vega shift from a longer lockout (30NC6 minus 30NC1)

Citi, *US Rates Weekly: Swearing in huge expectations* (13 Jan 2017), Figure 32 (the same chart as Figure 5 of
*US Rates Vol Lab: Long Live Formosa*, 9 Jan 2017). The figures are the model-implied difference in bucketed vega,
in $K normal vega per $100mn initial notional, for 30y zero-coupon callables. Rows are expiries and columns are
tails. The chart has no 8y or 9y expiry rows. Context: in Jan 2017 the regulator *proposed* a 6y minimum lockout.
A later draft (Citi, *Buy long expiries*, 17 Jan 2017) set the minimum at 5y.

| exp \ tail | 1y | 2y | 3y | 4y | 5y | 6y | 7y | 8y | 9y | 10y | 20y | 25y | 30y | row sum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1y | -0.4 | -0.7 | -0.8 | -0.9 | -1.0 | -0.9 | -0.9 | -0.8 | -0.7 | -1.7 | 1.3 | -0.9 | **-13.5** | -21.9 |
| 2y | -0.1 | -0.3 | -0.3 | -0.3 | -0.3 | -0.3 | -0.3 | -0.2 | -0.2 | -0.2 | 2.1 | -3.9 | **-8.7** | -13.0 |
| 3y | -0.2 | -0.4 | -0.4 | -0.5 | -0.5 | -0.5 | -0.4 | -0.4 | -0.3 | -0.7 | 1.1 | -4.6 | -3.8 | -11.6 |
| 4y | -0.1 | -0.1 | -0.2 | -0.2 | -0.2 | -0.2 | -0.1 | -0.1 | -0.1 | 0.2 | 2.4 | -9.2 | -2.6 | -10.5 |
| 5y | -0.1 | -0.2 | -0.3 | -0.3 | -0.3 | -0.3 | -0.3 | -0.2 | -0.2 | -0.5 | 0.2 | -2.4 | 0.0 | -4.9 |
| 6y | 1.5 | 2.6 | 3.1 | 3.3 | 3.3 | 3.1 | 2.8 | 2.5 | 2.1 | 4.7 | 3.7 | **24.6** | 0.0 | 57.3 |
| 7y | -0.1 | -0.1 | -0.2 | -0.2 | -0.3 | -0.3 | -0.4 | -0.5 | -0.6 | -3.2 | 10.0 | **31.2** | 0.0 | 35.3 |
| 10y | 1.3 | 2.0 | 2.3 | 2.3 | 2.2 | 2.0 | 1.9 | 2.0 | 2.3 | **30.1** | **30.4** | **19.8** | 0.0 | 98.6 |

- The grid sums to +129.3K. The headline parallel vegas give 270K − 145K = +125K, so the grid was read
  correctly.
- Vega moves out of 1y-5y expiries (−61.9K) and into 6y-10y expiries (+191.2K). By tail, 10y/20y/25y gain
  (+28.7/+51.2/+54.6K) and 30y loses (−28.6K).
- The vega follows the coterminal diagonal (expiry + tail ≈ 30y), so it lands on 6y25y and 7y25y. Because 6y
  expiries are illiquid, Citi expected the hedges to go into 10y10y and 10y20y.

## 2. Callable supply monitor history (Citi Vol Lab monitor)

Citi's monitor covers all callable Formosa bonds (zero-coupon and fixed-rate) plus zero-coupon non-Formosa bonds.
Vega is reported in $mn of normal parallel vega. It assumes that financial and government issuers swap their
callables and non-financial issuers do not. The monitor does not say whether the vega column nets redemptions. The
last column is our own ratio and is only a diagnostic of structure mix.

| Period (source date) | Gross $bn | Formosa / non-Formosa | Fin / non-fin | Redeemed $bn | Net $bn | Vega $mn | Vega per $bn gross |
|---|---|---|---|---|---|---|---|
| 2016 full year (1 May 2017) | 57.9 | 38.2 / 19.8 | 51.4 / 6.5 | 20.8 | 37.1 | 104.2 | 1.80 (2.03 per fin $bn) |
| 2017 YTD to Apr (1 May 2017) | 24.5 | 20.5 / 4.0 | 18.5 / 6.0 | 1.0 | 23.5 | 39.7 | 1.62 (2.15 per fin $bn) |
| 2018 full year (14 Jan 2019) | 23.9 | n/a | n/a | n/a | 18.8 | 53.3 | 2.23 |
| 2020 YTD (30 Mar 2020) | 20.62 | n/a | n/a | n/a | n/a | 46.8 | 2.27 |
| Mar 2020 MTD, all financial (30 Mar 2020) | 5.08 | n/a | 5.08 / 0 | n/a | n/a | 14.6 | 2.87 |
| 2022 full year (12 Jun 2023) | 16.73 | n/a | n/a | n/a | 4.74 | 39.3 | 2.35 |
| 2023 YTD to Jun (12 Jun 2023) | 2.44 | n/a | n/a | 0.95 | 1.48 | 2.6 | 1.07 |
| 2025 full year (5 Oct 2026) | 13.88 | 0.55 / 13.33 | 13.88 / 0 | 2.88 | 10.99 | 13.9 | 1.00 |
| 2026 YTD (5 Oct 2026) | 18.14 | 1.28 / 16.86 | 18.14 / 0 | 2.42 | 15.71 | 16.6 | 0.92 |

Monthly reference points:
- Jan 2017 financial callables were about $9.5bn initial notional ($8.4bn Formosa), the highest month on record
  (Citi, *Going nuclear*, 3 Feb 2017).
- Mar 2018 was $3.6bn. Apr 2018 was about $0.3bn because of the earnings blackout (Citi, *Convexity Meets
  Steepeners*, 19 Apr 2018).
- Apr 2019 was about $0.73bn, and full-year 2019 was expected at about 25% of 2018 (Citi, *US Rates Vol Lab: Trading long-dated convexity*, 9 May 2019).
- Jan 2020 was about $5.3bn issued against a $5bn forecast, with about $16mn of swapped vega, the highest since
  Jan 2018 (Citi, *In search of cheap vol*, 17 Jan 2020).
- Feb 2023 month-to-date was under $0.5bn (Citi, *Rates Vol Lab: Short Blues convexity via futures/swaps*, 21 Feb 2023).
- BofA put 2024 YTD Formosa issuance at about $1.1bn (Feb 2024).

Since 2025 Citi's tally is mostly non-Formosa financial issuance. Our reading: Taiwan-lifer demand is no longer the
whole story.

## 3. Raw Bermudan vs empirical redemptions (J.P. Morgan, 10 Jan 2020)

| Item | Raw Bermudan | Empirical model |
|---|---|---|
| 2020 notional up for call | $85bn ($62bn financials, of which $45bn self-issued; $13bn corporates, $3bn of them likely swapped; $10bn SSA) | same |
| Expected 2020 redemptions | $78bn | ~$30bn |
| Empirical/raw by quarter | — | Q1 47%, Q2-Q3 ~32%, Q4 24% (front-loaded) |
| Q1 2020 vega supply | ~$40mn/abp | ~$20mn/abp, of which ~$5.5mn/abp in 20y+ expiries |

Classifier: each annual call date of a Formosa-style bond issued since 2012 is one observation (about 2,000). The
features are the Bermudan-model call probability, log(issue size) and issuer type (corporate, FIG third-party, FIG
self-placed, SSA). A logistic regression or a random forest both work. Credit-spread change, yield change since
issue and issuer identity were tested and dropped. Call rate = notional called / notional eligible.

Observed call efficiency, for bonds with more than 80% model call odds since Jun 2019:
- about 50% overall;
- about 70% for issues of $300mn or more, and 20-40% for smaller issues;
- above 70% for non-financial corporates;
- lowest for FIG self-placed deals, where the issuer's own vol desk holds the cancellable-swap hedge.

## 4. Dealer stock estimate (Citi, *Vol cycle, steepeners, and SOFR*, 25 Mar 2019)

| Step | Value |
|---|---|
| Financial long-dated callables outstanding | ~$175bn, 95% zero-coupon accreters, average structure printed "4NC30" |
| Normal vega swapped to dealers | ~$366mn |
| Bought by hedge funds / held by dealers | 15% / 85% |
| Dealer positions hedged with short Europeans | 85%, giving 366 × 0.85 × 0.85 ≈ $265mn short European vega |
| Hedge mix (vega weights, from Citi's bucketing model) | 5y25y 35% / 10y20y 35% / 20y10y 30%, about $93mn / $93mn / $79mn |
| Value transfer from SOFR discounting of the European hedges | about −$100mn at unchanged vols, about −$260mn with FF/SOFR basis at Jan 2019 levels |

Implication: dealers may mark European vols lower against Bermudan vols.

J.P. Morgan (29 Mar 2019) gives these figures:
- About 40% of the risk (vega-weighted) is placed with end users through Bermudan-vs-European receiver switches.
- Dealers are long up to about $200mn/bp of aggregate convexity.
- They had delivered about $56mn/bp of pay-fixed since late 2018.

## 5. Structured-note hedge vectors

**EUR Daily Accrual Inversion Note** (Merrill Lynch RateLab, 11 Jun 2008)
- Terms: a 10y note issued at par with a 7% coupon. The coupon accrues on each day that EUR 30y CMS − 2y CMS ≥ 0
  and is paid quarterly as the average.
- Coupon formula: coupon = 7% × (non-inverted days / days in period). With 7 inverted days out of 91, the coupon is
  7% × 84/91 = 6.46%.
- Issued Apr-Jun 2007 and Nov 2007-Feb 2008. The estimated outstanding is EUR 13-20bn.

| Per 100mm of notes (= 700mm long digitals) | Scaled to EUR 15bn |
|---|---|
| Receive 450mm 10y | Receive ~67bn 10y |
| Pay 150mm 30y | Pay ~22bn 30y |
| Sell 400mm 4y-into-2y straddles | Short ~60bn 4y2y straddles |
| Buy 75mm 4y-into-30y straddles | Long ~11bn 4y30y straddles |

On a strike cross every Greek flips. Hedgers must then sell the curve (put on flatteners), buy back the 4y2y
straddles and buy about as much again to go net long. At EUR 15bn that is about 120bn of 4y2y straddles.

**USD CMS caps sold to non-traditional buyers** (BAS/ML RateLab, 27 Oct 2009)
- A swaption payout is (rate − strike) × DV01. DV01 falls as rates rise, so a swaption pays a concave $ per bp. For
  example, a 6% bond at 6% yield earns $0.0743/bp at 6.00-6.01% but only $0.0619/bp above 8%.
- To deliver a fixed $ per bp, a dealer short a 6% CMS cap must buy a string of OTM payers struck from 6% to 20%+.
- There is no natural seller of deep OTM payers, so payer skew is marked up.

**USD structured notes with embedded curve options** (ML RateLab [Yield Curve Options], 8 Dec 2006)
- These notes left dealers long spread vol.
- A grinding flattening made that position hard to distribute, so curve vol traded cheap.
- Spread vol: σ_spread = √(σ_A² + σ_B² − 2ρσ_Aσ_B).

**JPY / AUD**
- PRDC hedging links USD/JPY cross-currency basis to the FX level and hits 20y and 30y basis (Huggins & Schaller,
  2024).
- Prepayment of 20-30y structured notes linked to equity or FX unwinds super-long JPY receivers, which tightens
  long-end basis (J.P. Morgan, 11 Mar 2015).
- Reverse dual-currency hedging desks receive long-end AUD/USD basis when AUD/JPY falls and pay it when AUD/JPY
  rallies (J.P. Morgan, 11 Mar 2015).

## 6. Source trade log (levels as printed)

| Date, source | Driver | Trade | Level / sizing | Main risk (as printed; [ours] = our addition) |
|---|---|---|---|---|
| 9 Jan 2017, Citi | lockout proposal moves vega out of 1y-2y × 30y tails | buy 2y30y vs sell 2y10y straddles, beta-weighted | 1 unit vega vs 0.8 unit; $53mn 2y30y vs $100mn 2y10y (the Weekly prints $63mn; $53mn reconciles with annuities) | rule delayed or not adopted |
| 12 Jan 2017, Citi Weekly | 10y10y cheap after dVega/dRate selling plus January supply | buy $100mm 10y10y straddles, delta-hedged | open 72.2bp; target +$680K, stop −$440K | more callable supply than expected |
| 18 Jan 2019, Citi Weekly (*The rocky road to a steeper curve*) | callable supply cheapens 10y10y | short 10y10y straddles | 66 → 66.3 | [ours] supply lull |
| 17 Jan 2020, Citi | heavy January supply, lighter February | buy 5y-forward 5y20y via 10y20y vs 5y30y straddle switch | 10y20y 54.6nv, 5y30y 56.6nv | big Treasury selloff |
| 10 Jan / 21 Feb 2020, JPM | record 20y-expiry supply from 40NC5 | buy 10y10y vs sell 20y10y ATMF straddles, vega-neutral | long $58.4mn 10Yx10Y (1185c) vs short $50mn 20Yx10Y (1230c) | [ours] supply pause |
| 21 Feb 2020, JPM | issuance-related receiving, no natural ultra-long payer | receive 30Yx10Y vs pay 10Yx10Y forward swaps | $185mn at 1.70% vs $125mn at 2.09%, −39bp; slide −4bp/1y | [ours] supply stops; big selloff |
| 27 Mar 2020, Citi | pent-up Formosa supply (March bank callables about $5bn) plus long-vega liquidations | buy USD vs EUR 10y10y straddles | USD 59nv vs EUR 57.4nv | further stop-outs |
| 23 Feb 2024, BofA | Bermudan hedgers sell long-expiry European vol | long 5y30y vega for roll-up | 5y30y about 85bp vs 1y30y about 97bp, about +3bp/yr roll | [ours] vol collapse |
| 2 Jul 2026, Morgan Stanley | reduced callable vol supply plus mortgage-hedger demand | long 2y10y straddle | entry 670c (10 Jun 2026) | vol falls while rates stay pinned near the strike |
| 27 Aug 2026, Morgan Stanley | USD vol premium over EUR with similar realized; callable issuance compresses USD 5y5y vol | buy EUR vs sell USD 5y5y ATM straddles, delta-hedged | EUR 100mm vs USD 125mm | [ours] USD vol bid |

## 7. Surface regressions and readings quoted with supply arguments

| Date, source | Reading |
|---|---|
| 9 Jan 2017, Citi | 2y-expiry 10y/30y tail vol ratio 1.09 (3m z +2.4); 10y30y about 5 normals (about 1.6σ) cheap to 2y30y |
| 17 Jan 2017, Citi | 10y30y vol = 0.51 × 2y30y vol + 25.99, R² 0.80 |
| 3 Feb 2017, Citi | 3y30y vol = 0.69 × 3y10y vol + 18.68, R² 0.78 (sample 1 Jan 2016 to 27 Jan 2017); 3y30y cheap after record January supply |
| 25 Sep 2019, Citi | forward vols beyond 1y forward start were −1.5σ to −2.4σ on 5y z-scores; not bought because of ELB risk and callable supply |
| 22 Jun 2021, Citi (*Left-side vols' outperformance*) | muted callable supply cited as one reason 10y10y vol outperformed 5y10y |
