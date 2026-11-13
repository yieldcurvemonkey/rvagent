# CCP basis: levels, term structures and history

All numbers are historical snapshots from the cited documents, for calibration of what "normal" looked like in each
regime. Never present them as current. Sign: other CCP minus LCH, in bp, unless stated.

## USD CME minus LCH, term structure snapshots (bp)

| Tenor | 18-May-15 | 26-May-15 | 17-Jun-15 (SEF indicative) | 28-Mar-16 | 26-Jun-17 |
|---|---|---|---|---|---|
| 1Y | | | 0.25 | | 0.10 |
| 2Y | 0.35 | 0.65 | 0.35 | 0.20 | 0.25 |
| 3Y | 0.60 | 1.10 | 0.60 | 0.30 | 0.45 |
| 4Y | 0.85 | 1.60 | 0.95 | 0.65 | 0.70 |
| 5Y | 1.20 | 1.85 | 1.25 | 0.95 | 1.05 |
| 7Y | 1.35 | 2.05 | 1.55 | 1.35 | 1.55 |
| 10Y | 1.60 | 2.30 | 1.85 | 1.75 | 2.45 |
| 15Y | 1.70 | 2.30 | 2.05 | 2.05 | 2.85 |
| 20Y | 1.75 | 2.30 | 2.20 | 2.25 | 3.05 |
| 25Y | 1.82 | 2.40 | 2.30 | 2.40 | 3.25 |
| 30Y | 1.90 | 2.50 | 2.40 | 2.50 | 3.40 |

Sources: Clarus (C. Barnes), CME-LCH Basis, What does the Term Structure tell us?, 26 May 2015 (first two columns; the 4y
point moved +0.75bp in a week, 30Y +0.60bp; 5y5y forward +2.9bp vs spot 5y +1.85bp); Clarus (T. Skarecky), Pricing and
Arbitraging the CME/LCH Basis, 22 Jun 2015 (IDB SEF indicative, also 6Y 1.45, 8Y 1.65, 9Y 1.73, 12Y 1.90); Clarus (C. Barnes),
Identifying CCP Basis Trades in the SDR, 30 Mar 2016 (broker mids, identical at 11am/3pm/5pm; sign not stated in the
source, orientation here is by analogy with the other columns); Clarus (T. Skarecky), CME-LCH Basis For Dummies, 28 Jun 2017
(broker mid; also 6Y 1.35, 8Y 1.95, 9Y 2.20, 11Y 2.55, 12Y 2.70, 35Y 3.45, 40Y 3.50, 50Y 3.55).

Reading the shape: monotone in tenor in all snapshots (long-end IM cost per unit of DV01 is larger); the 2015 jump was
parallel-ish with a front-end hump at 4y; by 2017 the long end had stayed wide while the front end had normalised
("well under 1bp, mostly about 0.25bp since mid-2016" at 1-3y; 30y about 3.8bp in May 2017, JPM, 3 May 2017).

Bid-offer on the basis package is about 0.25bp. Indicative 30Y (IDB SEF, May 2015, 0.25bp b/o at both CCPs): receive LCH 2.74584
vs CME 2.76484; pay LCH 2.74834 vs CME 2.76734: a $95,000 difference on a $25m ticket (Clarus, CME-LCH Basis Spread, 20 May 2015).

## USD history (CME minus LCH)
| Period | Level / event | Source |
|---|---|---|
| to 2014 | below 0.15bp, ignorable (June 2014 below 0.1bp) | Clarus (A. Khwaja), 20 May 2015 and 30 Jun 2014 |
| May 2015 | jump from about 0 to about 2bp in weeks (0.15bp to up to 1.9bp by tenor); about $20bn of switch volume in 12 business days | Clarus 26 May 2015; Clarus 20 May 2015 |
| Nov 2015 to late 2018 | 10y range about 1 to 4.5bp | Citi (J. Williams), 16 Jan 2019 |
| Oct to Dec 2018 | 10y basis collapsed as the 10y rallied from 3.25% to about 2.7% (short covering) | Citi, 16 Jan 2019 |
| Aug 2019 | 30y at 0.8bp, tightest since 2015 (real-money steepener unwinds, bilateral-SOFR IM exemption hopes) | Citi US Rates Weekly, 2 Aug 2019 |
| Oct 2019 | prudential regulators' narrow IM-exemption proposal: "any room for further CME/LCH compression is now limited" | Citi US Rates Weekly, 4 Oct 2019 |
| Mar 2020 | CME about 30% of USD IRD gross notional; operational-event risk at one CCP raises basis vol | JPM, 10 Mar 2020 |
| 2024 | CME-LCH dipped below zero; JSCC-LCH turned positive early 2024 | SUERF 940, Jul 2024 |
| H1 2025 | narrowed and less volatile; 7y about 0.85bp (chart label); flat through the April tariff shock when swap spreads moved over 15bp | Coalition Greenwich, Q3 2025 |

Share of cleared volume (for the sign/size story): LCH clears about 98% of USD swaps ($53.3tn Q2 2024 volume) with about $225bn
of IRS margin vs about $37bn at CME (Markets Media, FMX Futures Says Margin Savings with LCH will Exceed CME, 30 Jul 2024);
CME daily volume was 20-30% of the two majors in 2016, from a peak above half (JPM, 20 May 2016); LCH about 50% of the
global IRS market and over 90% of cleared IRS in 2013-14 (BoE SWP 580, 2016). LCH swaps IM was $227bn vs CME $37.5bn in
Q1 2024 (Coalition Greenwich, Q4 2024).

## EUR (Eurex minus LCH, CME minus LCH)
- Darbyshire Ex 6.1 (Pricing and Trading Interest Rate Derivatives, 2022): Eurex/LCH 2Y 0.70, 5Y 1.60, 10Y 2.70bp; CME/LCH 2Y 0.10,
  5Y 0.20, 10Y 0.35bp. Implied curve inputs (LCH / Eurex / CME): 5Y 2.10% / 2.116% / 2.102%; 10Y 2.07% / 2.096% / 2.0735%.
  (As printed, the Eurex 10Y 2.096% does not equal 2.07% + 2.70bp = 2.097%; round-off. Use `par_LCH + basis/100`.)
- Broker quotes, 26 May 2015: EUR 2y 0.15, 5y 0.25, 10y 0.35, 30y 0.35bp (Clarus, 26 May 2015).
- History (SUERF 940, Jul 2024): positive (buy side and insurers pay at Eurex); near zero 2018-19 after the 2017 Eurex
  incentive programme; briefly negative at the Brexit peak, end-2019; spiked in March 2020; calm by end-2020; rose from mid-2021
  with inflation and kept rising through the 2022 hiking cycle without reverting. Eurex holds about 20% of EUR IRD notional.
- Flow read: 30y Eurex-LCH positive means no Dutch/German receiving interest; 50y slipped slightly negative in Feb 2020;
  chart range about -2 to +4.5bp (Nordea, EUR Rates Flash, 5 Feb 2020).
- EMIR 3 "active account" requirement could move the basis either way depending on the direction of relocated portfolios.

## GBP
- GBP IRS clear nearly all at LCH (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022). 26 May 2015 broker quotes: 2y 0.10,
  5y 0.10, 10y 0.15, 30y 0.20bp (Clarus, 26 May 2015). GBP and EUR STIR convexity is affected by futures venue, margin and the swap CCP basis, "can engulf
  the theoretical prices" (Quantitative Finance Stack Exchange, STIR futures convexity adjustment, Jun 2025).

## JPY (JSCC and LCH)
- JSCC holds about 70% of JPY IRS notional; Japanese FSA requires onshore investors and dealers to clear at JSCC. The LCH/JSCC
  basis reached "double digits" in early 2018 as flow migrated from LCH to JSCC (JPM, 3 Aug 2018).
- Sign history (JSCC minus LCH): negative for most of the period (domestic banks receiving to hedge loan books before 2018), positive
  from early 2024. Offshore LCH users move it with BoJ bets: 2018 tightening bets made payers rich at LCH; 2019 and 2024 easing
  bets did the same for receivers. The basis shrank after offshore hedge funds onboarded at JSCC from 2018. US clients cannot
  clear at JSCC (LSOC incompatibility). (SUERF 940, Jul 2024)

## Other markets
AUD and NZD (ASX), CAD, CHF, SEK, NOK: no basis levels in the source material. A commenter expected a basis at some regional
CCPs but had not checked (Clarus, 20 May 2015). Ask for data; do not extrapolate from USD/EUR.

## Margin-saving reference numbers (cross-venue IM)
- CCP IM ($K) for $100K DV01 10y, CME / LCH: pay IRS 3,237 / 4,539; pay IRS vs receive 10y SOFR 766 / 1,596 (-76% / -65%);
  receive IRS 3,959 / 4,165; receive IRS vs pay SOFR 782 / 2,180 (-80% / -48%) (Citi US Rates Weekly, 17 May 2019).
- IM for ED long vs PVBP-weighted FRA: CME-netted saves about 70-80% vs LCH (two postings); LCH about $1.2-1.5mm per $1bn notional
  across Z7-Z9 vs CME netted about $0.15-0.45mm (JPM, 3 May 2017).
- CME ED futures margin on a 1-2 day close-out vs 5 days for CME/LCH swaps and FRAs, so futures need much less IM (Citi, Sell Eurodollar convexity in Blues, 8 Jan 2018).
- CME portfolio-margining average daily savings $8.2bn in H1 2025 (about 90% from USD swaps vs USD IR futures/options); 93% of
  surveyed firms (n=14) would clear packages at an additional CCP if margin offsets exceed the CCP basis (Coalition Greenwich, Q3 2025).
- Benos et al. estimated gains from exploiting the price differential at about $80m a day (SUERF 940, Jul 2024).
- Approved CCP risk weight 2% (4% via a clearing broker) and SA-CCR maturity factor 0.175 for cleared trades vs 0.25-1.0 uncleared (Darbyshire, 2022).
