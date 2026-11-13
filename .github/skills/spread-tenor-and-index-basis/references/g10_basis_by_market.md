# Tenor and index basis by G10 market, plus legacy IBOR mechanics

Detail for [SKILL.md](../SKILL.md). Confirm current index status and conventions in
[fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md) before trading: instrument lists in some sources are
LIBOR-era (2021) and index status changes. Sign: spread on `leg_a` against `leg_b` flat unless stated.

## 1. Live vs legacy by market

| Market | Overnight RFR | Term / IBOR still the swap standard? | Tradeable single-currency basis today | Notes (sources) |
|---|---|---|---|---|
| USD | SOFR (ACT/360); EFFR/OBFR unsecured | No (USD LIBOR gone; history and fallback spreads only) | **SOFR vs FF** (swap, 1M futures vs FF futures); Term SOFR vs futures | CCP discounting is SOFR since Oct 2020; EFFR curve is built from EFFR/SOFR basis swaps; OTC spec: both legs compounded quarterly, ACT/360, spread on the FF leg (DBIQ, 2 Feb 2023; CME, 2 Jun 2020) |
| EUR | estr (annual, ACT/360) | **Yes, Euribor** (3M/6M) | **E/E (estr vs 3M Euribor)**, 1s3s, 3s6s, 6s12s to 60y | OIS 53% of EUR swap turnover and EUR FRAs about 80% of global FRA turnover, so Euribor tenor basis persists (BIS Quarterly Review, Dec 2025). IRBS quoting standard since 2008: difference of two IRS fixed rates (Ametrano & Bianchetti, 2013) |
| GBP | SONIA (annual, ACT/365F) | No (LIBOR curve discontinued) | none single-currency | 3s6s and LIBOR-SONIA basis (to 60y) are legacy; GBP IG funding comparison in the xccy skill |
| JPY | TONA (ACT/365F) | Partly: TIBOR variants; euro-yen TIBOR stopped at end-2024 | TONA vs TIBOR is thin; JPY FX-OIS via TONA/SOFR | JPY LIBOR and TIBOR differed by panel credit; Sep 2012 JGB 3M/6M ICBS 12bp (legacy; Huggins & Schaller, 2nd ed., 2024) |
| CAD | CORRA (ACT/365F, no leap-year adjustment) | No: CDOR ceased 28 Jun 2024 | Term CORRA vs CORRA basis (market-convention terms: ACT/365F, flat compounding, MF, spot 2bd); BAX futures converted to CRA at a 32.138bp spread | Term CORRA recommended-terms detail seen only as a search snippet: verify. Legacy CDOR was keyed off bankers' acceptances and carried less credit than LIBOR; CDOR 3M vs 1M basis used 1M compounded quarterly |
| AUD | AONIA | **Yes, BBSW** (1/3/6m) | 3s6s (synthetic: semi 6m swap rate − quarterly 3m swap rate, 1y–30y); BBSW vs OIS | IRS vs 3m (quarterly) 1–3y, vs 6m (semi) 4y–30y (conventions switch, one row per `from_tenor`). Four partially interconnected curves, so use a global optimiser for curve building. Desk commentary in 2026 put BBSW roughly 8.5–10bp over OIS; the 2007 12M OIS-Libor basis had mean 8.82bp, sd 1.46bp |
| NZD | NZIONA | **Yes, BKBM** (3m) | BKBM vs OIS | IRS 2y–15y vs 3m bill; about half of turnover is OIS |
| SEK | SWESTR | **Yes, STIBOR** (1/3/6m) | STIBOR vs OIS; an SWESTR/STIBOR futures inter-contract spread exists as a listed alternative to IMM FRA-OIS | IRS vs 3m, 1y fixed 30/360 |
| NOK | NOWA | **Yes, NIBOR** (1/3/6m, fixing 2bd before reset) | 6s3s quoted as fixed-rate difference between 6M and 3M NIBOR swaps | IRS vs 6m |
| CHF | SARON (ACT/360) | No | none | RFR-only market; no tenor basis to trade |

Sources found no basis-level data (levels, history) for SEK, NOK, NZD (beyond one 2026 RFR-vs-SOFR remark), CHF, GBP or CAD
single-currency basis. Do not supply levels: ask the user or the data adapter. Share of OIS in swap turnover (2025): about 65% globally, above
90% in USD/GBP/CHF/CAD, about 50% in AUD/NZD (BIS Quarterly Review, Dec 2025). Basis swaps are under 1% of OTC IRD turnover even in EUR.

Minimum size and increment on a US swap execution facility rulebook (2021): 5mn / 100k for USD, EUR, GBP, JPY, AUD, CHF, SEK, NOK, NZD; CAD 25mn / 1mn. Basis
swaps have two floating legs, each with its own payer, notional, designated maturity, spread, day count, reset, averaging, compounding (compounding or flat
compounding) and business-day terms; legal terms of the same basis swap differ across CME, LCH, Eurex, JSCC and ASX, and ISDA amendments can take effect at different times for bilateral and cleared contracts.

## 2. EUR tenor basis: levels and screens (dated)

| Date | Quote | Source |
|---|---|---|
| 11 Dec 2012 | 1s6s: 22.2bp at 1y, peak 25.0 at 5–6y, 16.3 at 30y; 3s6s: 14.5 at 1y, 12.5 at 10y, 7.0 at 30y, 5.4 at 50y; 6s12s: 26.2 at 1y, 11.3 at 10y, 6.6 at 30y | Ametrano & Bianchetti, 2013 |
| 2010 | 5y 3s6s: within about 1bp of zero before Jul 2007, then wide; Jun 2010 pay 6M Euribor vs receive 3M + 18bp. Correlation with EUR FX: none pre-crisis, 0.68 after; with 5y EUR/USD CCBS −0.62 | Huggins & Schaller, 2nd ed., 2024 |
| 1 Nov 2011 | 2y 6s3s ≈ 0.25%; 2y Euribor strip zero 2.167% vs swap zero 2.564% | Aikin, STIR Futures, 2012 |
| 17 Mar 2020 | implied 1y-forward 3/6m basis negative beyond 7–8y, about −2.5bp | Nordea, EUR Rates Flash, 17 Mar 2020 |
| 17 Jan 2024 | strategy table (received; annualised carry+roll; carry+roll/vol; 50d z; PCA mispricing): 1y E/E 7.8, −77.6, −7.9, −9.5, −9.3; 5y E/E 11.9, −33.1, −7.4, −9.3, −9.5; 5y5y E/E 11.5, −0.6, −0.1, −2.0, −3.2; 10y E/E 11.7, −16.3, −4.1, −6.2, −6.8; 5y5y 3s6s −2.2, −2.6, −0.8, −0.6, −1.1 | Nordea, Pushing back, 17 Jan 2024 |
| Feb 2022 | estr vs 3M Euribor 2y 13.8bp | Tuckman & Serrat, 2022 |

PCA on EUR FRA − overnight bases: PC1 is level plus slope (all positive, declining with maturity), PC2 curvature; PC3 excluded so curvature stays in the residual
(Credit Suisse, PCA Unleashed, 24 Oct 2012). Euribor fixing methodology: EMMI hybrid and the ECB money-market statistical data tightened and added
day-to-day volatility to short bases; the IMM FRA/OIS narrowed eight sessions in a row (about 6.3 to 4.5bp) in May 2019: trade the trend, not each fixing
(Nordea, EUR Rates Flash, 23 May 2019). Futures-vs-cash 3M Euribor basis in the last month is about ±10bp and converges in the final week (Aikin, 2012).

Curve recipe (EUR, 11 Dec 2012): 1M curve = 1M swaps to 1y then 6M swaps + 1s6s basis to 30y (basis flat-extrapolated to 35–60y); 3M curve beyond 35y = 6M swaps + 3s6s;
12M curve = 6M swaps + 6s12s to 30y. Basis quotes reach 30y while 6M swaps run to 60y, so extrapolation is a judgment call (Ametrano & Bianchetti, 2013).

## 3. Legacy USD IBOR tenor and index basis (mechanics, still useful for history and for AUD/NZD/SEK/NOK analogues)

From Credit Suisse, Basis Points: A Guide to the Front-End and Basis Swap Markets, 18 Feb 2010:

| Product | Mechanics | Notes |
|---|---|---|
| LIBOR/LIBOR (3s1s, 6s3s) | float-float; 3s1s = 3mL vs 1mL compounded over 3 months quoted as 1mL ± spread, quarterly pay, ACT/360 | positive basis = compounded 1m below 3m; fixing lag 2 days; term structure usually slopes down |
| FF/LIBOR | EFFR leg vs 3mL, quarterly, ACT/360, spread on the FF leg | FF leg is a daily-weighted **arithmetic** average (OIS is geometric) with a 2-day rate cut-off; Exh. 41: 0.17548% vs 0.17537% with cut-off (Dec 2008–Mar 2009) |
| Prime/LIBOR, prime/FF | prime = FF target + 300bp; quoted prime minus spread | discrete prime basis carries inter-meeting FOMC risk |
| FRA/OIS | pay FRA, receive OIS: payoff = (3mL − 3mOIS) − (FRA fixed − OIS fixed) | credit/liquidity bellwether, co-moved with 5y bank CDS; includes term premium |

Sample 2010 levels: 1x4 FRA 0.30% vs OIS 0.18% = 12.0bp ($1bn ≈ $25k/bp); 5y 6s3s: 3mL + 7.75bp vs 6mL flat; 2y FF/LIBOR: FF + 20.75 vs 3mL; 2y prime/LIBOR: prime − 275 vs 3mL.
Liquidity: LIBOR/LIBOR to 30y and 1y1y most liquid; FF/LIBOR quarterly to 2y most liquid, > 10y illiquid; FRA/OIS liquid only in the whites.

**Stub risk.** A spot-start basis swap has first fixings known at inception, so it carries outright directional exposure: the basis payer is long the market (benefits from lower rates).
Stub of 3s1s = 3mL minus the 3-month 1s IRS over that stub. A fed-funds decision is effective the day after the meeting, so a swap maturing on the 18th has no exposure to that month's meeting.

**Correct LIBOR-OIS.** 3M LIBOR vs 1D compounded over 3M; 3M basis ≈ today's 3M fix minus market 3M OIS; 1m-forward 3M basis ≈ 1x4 FRA − 1x4 OIS (no fixing distortion)
(Lehman, 10 Jul 2007). Credit term premium (3M) = 3M LIBOR − 3M tri-party OIS = 3M LIBOR − (3M FF OIS − o/n FF + o/n tri-party repo) (Citi, Trade worries linger, 17 May 2019).
Post-crisis floor reasoning: 15bp minimum LIBOR/OIS credit term premium that MMFs require; < 10bp too extreme on 30-year history (same source).

**Building a 3M term curve from OIS plus basis** (Lehman, 10 Jul 2007): bootstrap FRAs and OIS separately, price 1D-3M basis swaps for 1M–1Y, solve recursively
`Σ_j [Π_{i in j-th 3M period} (1 + n_i (r_i + x)/D) − 1] dF_j = Σ_j L_j Δ_j dF_j`; sign: paying 1D OIS + x vs 3M LIBOR, x positive and larger in an upward-sloping policy path, smaller or negative when easing is priced.

**Basis risk monitoring.** No generally traded short basis swap existed; monitor by volatility or synthesise with OIS vs FRA/swap. Size meeting-date trades by cash-rate-change risk (CB01), not DV01:
DV01 overstated the risk by 244% against a CB01 view in a 1M OIS example (Lehman, 2007).

**Legacy uses.** Synthetic 3mL funding from an FF floater (issue FRN at EFFR + 18, receive EFFR + 18 vs pay 3mL in FF/LIBOR); short FRA/OIS approximately hedges a long 2y swap spread, and beyond
1y market makers hedged FRA/OIS with FF/LIBOR instead of FF futures. Normalisation trades: 30 Apr 2009 sell 3x6 FRA at 97bp and pay OIS at 24bp (lock 73); realised 3mL/OIS 29bp on 30 Jul 2009 gave about +44bp (CS, 2010).
Long 6m-forward 3s1s at 30bp vs 76bp spot (14 Nov 2008) realised 52bp on 14 May 2009: forwards over-estimated narrowing.

## 4. LIBOR-to-RFR fallback spreads (historical anchors)

5y median-based fallback spreads (JPM, Bills, Bonds, and basis...oh my, 7 Feb 2020): 1M about 11–12bp, 3M about 20–24bp, 6M about 27–31bp; 1s3s about 8.4–10.1; 3s6s about 6.3–10.1.
Citi (2 Aug 2019) valued long-dated FRA/OIS under a fallback assumption (LIBOR discontinued in 5y, historical median vs mean, 5y vs 10y lookback; EFFR/SOFR assumed −2.5bp rising to +4bp by 2023):
5y/5y5y slope for 6m/OIS 1.5bp vs fair −9.9bp (2.6 vol); 6s3s 2.8 vs −2.9 (3.0 vol); the expectation was flattening in the long end. `rate_indices.fallback_spread_bp` stores the contractual spread per index.

## 5. Panel and fixing structure

Trimmed-mean panels (LIBOR: top and bottom dropped) lagged policy expectations and had low or negative rank correlation with panel banks' CDS: LIBOR "has little to do with credit markets"
(JPM, 28 Feb 2020). Panel-shrinkage simulation: with 6 contributors, the average stays within 1bp of actual with 90% probability; in 10% of cases daily vol is up to 50% higher
(JPM, Dynamic hedgers are long, banks are short, 13 Sep 2019). Rolling-lender LCR arithmetic: a rolling $100mn 1M loan gives no LCR benefit; three staggered $33.3mn 3M loans leave $66.6mn usable as HQLA; six $16.7mn 6M loans leave $83.5mn,
which explains why 1M was skewed low (limited demand) in IBOR basis (Darbyshire, 3rd ed., 2022).
