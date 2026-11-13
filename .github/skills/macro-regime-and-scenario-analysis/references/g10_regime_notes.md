# G10 regime differences (market by market)

Companion to `SKILL.md`. Regimes that work in one G10 market often fail in another, because the central bank's
reaction function, the CPI energy weight, the funding plumbing and the positioning differ. Each note cites its source
inline. Dates matter: most figures are as of the cited date and must be refreshed before use.

## USD

- **Curve regime and the dollar.** Long USD by 2s10s regime (Willer and Saunders, Trading Global Macro Markets, 2026,
  information ratios): bear steepening 0.86; bull steepening -0.47; bull flattening -0.24; bear flattening 0.10; twist
  flattening 0.55; twist steepening -0.07; buy-and-hold 0.08. Bull steepening of the Treasury curve "has historically
  been the most corrosive environment for USD".
- **Term premium x terminal quadrant** (JPMorgan, FX Markets Weekly, 21 Aug 2026): bucket monthly changes in the 2y
  yield and the ACM term premium. The worst case for the dollar is a rising term premium with a falling Fed terminal;
  the dollar can strengthen with a rising term premium if the terminal is also rising.
- **SPX by curve regime** (same book): bull flattening best (IR 0.99), bear flattening worst (IR -0.12, typical of
  hiking cycles, losses concentrated in 1987 and 2022). Bear steepening was "not as negative as widely believed" (IR 0.44).
- **Fed phase rules.** Soft-landing easing cycles totalled 75bp in 1995, 1998 and 2024. The USD fell about 4% in the three
  months into the first cut and stabilised after the last cut (same book). Median 76 days from recession start to first
  cut (same book, playbook statistics).
- **Reserve-regime funding.** Fed funds traded above SOFR when reserves were abundant and below when scarce (BofA,
  Fed QT Beyond Taper & Funding Impact, 22 Oct 2021). The beta of funding spreads to reserves fell after 2020:
  SOFR-IOER 2015-19 y = -42.29 ln(x) + 314.47 (R-squared 0.60) vs 2020 onward y = -25.59 ln(x) + 202.56 (R-squared 0.91),
  with x in $bn reserves. Use a regime-specific fit.
- **Stock-bond correlation.** Above about 2.5% core CPI the one-year correlation of SPX and Treasuries turns mostly
  positive, so duration stops hedging equities (Willer and Saunders, 2026).
- **Macro fair value.** Five-year, five-year OIS fair value (JPMorgan, Global Fixed Income Markets Weekly, 21-22 Aug
  2026): USD = 0.18 x inflation revision index + 0.16 x growth revision index + 2.2 (R-squared 82%). Dated; refit.
- **Positioning.** The "smirk": a weak dollar is very rare when PMI is below 45, and long dollar has a poor hit rate
  when PMI is above 60 (Willer and Saunders, 2026).
- **Regime breaks.** The US-rates driver of USD/JPY failed for about eight years under Abenomics; the SPX filter on FX
  carry stopped working after COVID (Willer and Saunders, 2026).

## EUR

- **End point over timing.** For EUR swap curves, "the end point is even more important than the timing of the first
  rate cut" (Nordea, EUR rates: Pushing back, 17 Jan 2024). "The number of policy rate cuts is more important than the
  timing of the first cut or the pace of subsequent cuts." Score scenarios on the terminal and the count of moves.
- **Bund sensitivity to surprise regimes.** Positive German and Italian surprise regimes were historically the worst for
  Bunds (Citi, House Views August 2026, 21 Aug 2026). Bunds are a relative safe haven when global yields come under
  pressure, with little room to rally.
- **Bund and UST.** Directionally near-identical over decades; Bunds outperformed only in 2014-15. The only lasting
  divergence cited was German reunification in 1990-91 (Willer and Saunders, 2026).
- **Energy sensitivity.** The ECB is "arguably the most sensitive G4 central bank to energy shocks" (Citi, House Views
  August 2026). The ECB's sole inflation mandate allows "adjustment hikes" in an energy shock (JWS, Iran and Front End
  Rates, 8 Mar 2026).
- **Risk-aversion leg.** BTP-Bund spread vs its 55-day average works as a risk-aversion leg (information ratio 0.42;
  Willer and Saunders, 2026). A long BTP-Bund spread when German surprises are negative and Italian positive had an
  active IR of 1.21 (same book, Willer's surprise rule).
- **Vol and curve.** In the selloff regime of a 2y-based regime model, paying 5s10s30s was the way to own vol; the
  long-end steepener suffered in vol selloffs; hedge the received 5y leg (Citi, A narrative shift looms, 17 Mar 2022;
  Citi, Higher yields are here to stay, 24 Sep 2026).
- **Equity risk-off.** In six risk-off episodes since 2014 (October 2014 to March 2020), the 10y cheapened on the
  5s10s30s fly: average rise 15bp vs average VIX +28 (BNP Paribas, EUR curve convexity: Lessons from history, 25 May 2021).
- **Seasonality (weak evidence).** Bullish 10y core-yield windows 2004-2020, hit rate: third week of June 94%; third week
  of November 88%; January 71%. Bearish June 65%, October 76% (BNP Paribas, 25 May 2021). About 16 years of data, no
  significance test in the source; use as a soft prior only.
- **Cross-central-bank normalisation.** The ECB's cumulative OIS base uses the previous maintenance-period average, the
  Fed the effective funds rate, the BoE the SONIA fixing. Normalise before comparing (Nordea, EUR Rates Flash, 5 Feb 2020).
- **Regime sub-samples are not proof.** An ING EUR 4y-30y PC1-neutral curve trade (4 Feb 2020) had its spread against
  the Euribor futures spread negative in all four sub-regimes checked from 2017 to 2020, and it hedged hawkish-ECB risk
  separately. It still hit its stop within weeks (level 85.0 on 9 March, through the 93.75 stop, levels as printed; ING, Rates Strategy: No rise in
  rates but position for lower volatility, 4 Feb 2020). A check that passes history is necessary, not sufficient.

## GBP

- **Scenario guidance keyed to oil.** Bank of England scenarios A (full Brent futures curve), B (futures for six months,
  then the average of futures and a random walk), C (oil well above futures). Market-implied CPI = RPI swaps minus a
  0.8% wedge, the median historical RPI-CPI wedge, which itself has beta to inflation (JWS, Global Rates Outlook #5,
  10 May 2026).
- **Energy pass-through lags.** UK energy sensitivity is high, and Ofgem price caps delay pass-through. UK rates' energy
  sensitivity feeds fiscal-headroom concerns (JWS, 8 Mar 2026; Citi, Global Economic Outlook, 20 Aug 2026).
- **Anchoring.** UK inflation persistence (sum of lagged-inflation coefficients) was 0.7-0.8 in the 1970s to 1992 and 0.2
  in 1993-2005. Ten-year forward vol fell steadily after inflation targeting was adopted in 1992 (Bank of England, Mais
  Lecture, Mervyn King, 17 May 2005).
- **Scenario steepening.** A soft-Brexit stress steepens the gilt curve on BoE dovishness: 2y -25bp vs 10y -10bp
  (Golub, BlackRock's Guide to Fixed-Income Risk Management, 2023).
- **Macro fair value.** Five-year, five-year OIS fair value (JPMorgan, 21-22 Aug 2026): GBP = 0.28 x inflation revision
  index + 0.05 x growth revision index + 1.1 (R-squared 93%). The source read it as cheap at that date.
- **Hike premium.** Fade the BoE hike premium one meeting at a time (Citi, House Views August 2026).

## JPY

- **Positioning outlier.** Japan was the most-paid G10 curve going into the 2026 energy shock (JWS, Iran and Front End
  Rates, 8 Mar 2026). Positioning distorts cross-sectional fundamental betas in the first week of a shock.
- **Hold JGBs only with US rates below trend.** Holding JGBs when US rates were below their 55-day average gave a 2.02%
  return, active information ratio 0.90, vs 0.56% and 0.28 above it (0.60 unconditional) (Willer and Saunders, 2026). BoJ-cycle positioning belongs at
  the front end, which is "less subject to US rates".
- **BoJ pricing heuristics.** The market "has never priced more than 25bp in back-to-back meetings for more than 1 day"
  (Citi, House Views August 2026). The market rarely prices more than 80% of a BoJ hike until about a week before the
  meeting (Citi, No inflation trouble, in a SOX bubble?, 13 Aug 2026).
- **Intervention thresholds** (Citi, Japan FX, 14 Aug 2026): above 160 yen per dollar, intervention possible; above 162,
  Citi puts the probability above 50%; EURJPY warning zone 185-186. The cost of back-end curve intervention is a weaker
  currency (Citi, House Views August 2026).
- **Structural pivot.** JGB 10y versus 30y (2010-15) broke around 10y about 0.75% and 30y about 2%, when life insurers with
  target yields bought long bonds in sell-offs, creating option-like payoffs near the pivot. Post-2016 BoJ QE changed the
  regime (During, Fixed Income Trading and Risk Management, 2021).
- **Least correlated DM swap market.** JPY had the lowest correlation with other DM swap markets (about 0.2-0.3) and the
  lowest vol (about 1%) (Macrosynergy, Interest rate swap returns, data through Feb 2018).
- **Political scenario map** (Citi, Japan FX, 14 Aug 2026): finance minister staying = positive for JPY, leaving =
  negative; a reflationist board member staying = negative, leaving = positive; terminating the government-BoJ accord = positive.

## CAD

- **Growth pattern.** "Strong patch, then fade": real GDP averaged about 1.1% per quarter since 2025 (Citi, Canada
  Economics Weekly, 21 Aug 2026). Core inflation at or below 2% was the key regime evidence in that note.
- **Pricing gap.** Market pricing was about +95bp of hikes by early 2028 against a Citi call for two cuts (same source,
  Aug 2026). A large pricing gap is itself a regime signal: check which side the data supports.
- **Supply-shock ranking.** CAD ranks toward quantity (absorbs a shock through lower output rather than higher prices),
  (JWS, Global Rates Outlook #5, 10 May 2026).

## AUD, NZD

- **Twist-steepening winners.** AUD and NZD were the high-beta winners in UST twist-steepening regimes (Citi, The Messi
  Theory of Interest Rates, 31 Jul 2026): AUD and NZD returned about 1.9%, EUR about 1.05%, copper about 5.1% (same source; units as printed).
- **Energy exporters.** AUD and NOK have low energy CPI weights (about 5%) and rank toward price in the price vs quantity
  framework. They are fade candidates when they sell off with energy importers (JWS, Iran and Front End Rates, 8 Mar 2026).
- **Steepest curve.** NZD's curve was "steepest curve in the world (when adjusting for vol)" (JWS, USD and Global Rates
  Thoughts #2, 13 Nov 2025).
- **Cross-market rules.** Carry-based cross-market rules stall in bond bear markets (Willer and Saunders, 2026).
  AUD/NZD five-year spreads correlate about 0.8 monthly (Macrosynergy, 2025 print).
- **Extremes are alerts.** A five-year spread at a 1,000-day extreme is an alert for reversal, not an entry (Willer and
  Saunders, 2026; applies to SEK/NOK, AUD/NZD and CAD/US pairs).

## SEK, NOK, CHF

- **SEK: neutral-phase trap.** Central banks that reached neutral (EUR, SEK, CZK, KRW, AUD) priced little; front-end
  receivers held as free options were "taken to the woodshed" as data firmed (JWS, USD and Global Rates Thoughts #2,
  13 Nov 2025). SEK ranks toward quantity in the price vs quantity framework (JWS, Global Rates Outlook #5, 10 May 2026).
- **NOK.** Energy exporter with a low energy CPI weight (see AUD above).
- **CHF.** Low energy CPI weight (about 5%) (JWS, 8 Mar 2026). Steepening (5s30s) supported CHF only when the US terminal
  also fell (JPMorgan, FX Markets Weekly, 21 Aug 2026). CHF and gold take the haven role when US bonds and the dollar
  fall together (FT, The Long View, about 22 Aug 2026).

## Cross-market and cross-asset

- **DM bloc correlations.** Monthly five-year swap correlations mostly 0.5-0.8 (EUR-GBP, EUR-CHF, EUR-SEK, CAD-USD), and
  0.8 for AUD-NZD. Risk expansion went with higher yields and a weaker dollar; sell-offs with lower yields and a stronger
  dollar (Macrosynergy, 2025 print). Correlations are circumstantial: test them in each regime.
- **Global breakeven PC1.** Across US, UK, AU, JP, EU and CAD the first principal component of breakevens (85% of
  variance) is oil (BofA, Monthly rates models: August '25 edition, 4 Aug 2025).
- **Cross-market "one bet".** A back-end-stabilising policy signal hits both steepeners and long-RoW/short-US cross-market
  trades. Do not assume RV positions are insulated (Citi, Buy Gold, 19 Aug 2026).
- **Macro overlay on a cross-market spread.** Long BTP-Bund when German surprises are negative and Italian positive (see
  EUR above). Use a surprise index and a broad financial conditions index together; a yields-only tightening reading can
  overstate tightening and credibility (Citi, Messi Theory, 31 Jul 2026).
