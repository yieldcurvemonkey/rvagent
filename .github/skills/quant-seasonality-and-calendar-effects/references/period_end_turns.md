# Period-end turns: measurement, sizes, curve treatment, trade templates

Companion to [SKILL.md](../SKILL.md). Mechanics of repo and funding (who borrows, which facility) live in
[stir-repo-and-funding-plumbing](../../stir-repo-and-funding-plumbing/SKILL.md); installing a turn in a curve is
[fi-curve-construction](../../fi-curve-construction/SKILL.md). This file keeps the calendar-effect numbers and the
estimation recipes.

## 1. Definition and sign

- Turn premium = forward rate from the last day of the year to the first day of the next minus the neighbouring overnight rates; described as one that "usually ranges around a few percent" and is always positive. Size differs by instrument (unsecured, repo, OIS). Strip it before inferring policy expectations (Düring, Fixed Income Trading and Risk Management, 2021).
- Sign is market-specific: unsecured and GC repo turns are usually positive at year-end, but an overnight index can print below the neighbouring days when cash is abundant (a 2021 SONIA premium of about -0.25 to -1 bp on the day before each quarter-end; Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022) and fed funds month-end jumps are negative in the source's convention (Ametrano, Bertocchi, Mazzocchi, Advanced Eonia Curve Calibration, 2016). Always store the sign with the measurement.
- Historic turns: Euribor 1M fixings, turn-of-year jump +64 bp (29 Nov 2007), +22 bp (27 Nov 2008), end-semester +9 bp (29 May 2008) (Ametrano and Bianchetti, Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping, 2013). Turn premia have declined as participants fund earlier. Big historic turns: euro introduction 1998/99, Y2K, euro cash 2000/01.
- Drivers: balance-sheet reporting dates and averaging rules. Leverage-ratio derivatives and repo use daily averages, off-balance-sheet items use month-end averages; G-SIB scores use year-end snapshots. The BIS attributes "around half" of year-end derivative-exposure contractions to the G-SIB framework (Conks, The Great Flattening, 4 Aug 2024). Year-end "risk dieting" shows most in cross-currency basis (short-dated, switched back on in January) and less in repo (Abate, US short interest rate primer, Jan 2025).

## 2. Jump size from curves (formulas)

- Effect of a one-day overnight jump J on a period of N days is J / N on the period average rate (a 0.5 bp year-end overnight jump moves a 1M (about 22 business days) average by about 0.5/22 = 0.02 bp and a 3M by about a third of that: a spike in forward overnight rates, a tiny move in 3M forwards, and a zero-curve hike that is larger the earlier the jump date; Deriscope, Turn-of-the-Month Effect in SOFR Curve built out of 1- & 3-Month Futures, 18 Feb 2024).
- Jump model: multiplicative factor on discount factors, additive on zeros, for affected dates (Ametrano and Bianchetti, 2013).
- JSize = (F_original - F_interp) x tau / tau_J, where F_original is the quoted forward crossing the jump date, F_interp the smooth non-crossing forward, tau the forward's accrual length and tau_J the jump length (1 day); for negative month-end jumps (fed funds) the sign flips: JSize = (F_interp - F_original) x tau / tau_J (Ametrano, Bertocchi, Mazzocchi, 2016).
- Procedure: fit the liquid quotes; move an out-of-line segment's difference into a jump; remove it; iterate for the next jump date. Strip the turn before smoothing and reinsert after. Include only the first two year-ends: a 1M deposit carries about 1/22 of the overnight weight and a 3M about 1/3 of the 1M effect (Ametrano and Bianchetti, 2013).
- Estimation sources: 3M futures (first year-end only, to the September IMM), 6M FRAs (to June), 1M swaps (to November), Monday FRA strips; the estimates normally agree.
- Installing in a curve: a year-end turn needs two nodes (31 Dec and 1 Jan, ignoring holidays) and two calibrating instruments, the turn size and "before/after overnight rates equal". Preferred: assign the turn to exactly one calibration parameter. Worked 0% curve: spike -50 bp at 31 Dec; instruments overnight swap from 1 Dec = 0%, spread (30 Dec, 31 Dec) = -50 bp, overnight swap from 1 Jan = 0% gives s = [0.0, -0.5, 0.0] percent in two Gauss-Newton iterations. For splines, compose a log-linear turn curve with the spline curve and calibrate both (Darbyshire, Coding Interest Rates, c. 2024).
- Fading turn (3M STIBOR, 2022): 20 bp turn with nodes 15 Sep 0, 30 Sep 0, 1 Oct -0.20, 31 Dec -0.04, 1 Jan 0; the turn was large at first (end-September into October) but faded before January expiry, while the overnight rate at end-December still showed a substantial turn (Darbyshire, Coding Interest Rates, c. 2024). Quarterly turns of -3 bp and half-year/year-end turns of -5 bp are quoted in the same author's swaps text (currency not stated).
- Use mid-month samples when fitting models across the pre-standing-facility quarter-end spikes (Huggins and Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).

## 3. Measuring a quarter-end or month-end turn (USD template; adapt per market)

| Measure | Definition | Source |
|---|---|---|
| Quarter-end spread | SOFR minus the overnight reverse-repo rate; quarter-end window = last day +/-2 business days | (Federal Reserve Board, What Happens on Quarter-Ends in the Repo Market, 6 Jun 2025) |
| Month-end change | spread on the last business day minus the average spread for the month excluding that day | same |
| Month-end gauge (alternative) | max of (SOFR minus reverse-repo rate) in the 5-day window centred on the last business day | (Federal Reserve Bank of New York, Facing Quarter-End Pressures, 12 Nov 2024) |
| Net supply-demand | reverse-repo balance + reserves held by large banks + primary-dealer tri-party borrowing - dealer reverse repo - sponsored reverse repo (body text and figure note differ on the supply side) | FEDS note |

Rule: turn size scales with base tightness. Month-end jumps "have tended to move in line with the overall levels" of repo
spreads, and lower net supply means larger base spreads and larger spikes, so use the ex-month-end average with net
supply-demand, not a fixed historical premium. Pressure concentrates in cleared segments: Sept 2024 tri-party traded firmly
below the standing-repo rate while cleared DVP and GCF traded at or above it (FRBNY, 12 Nov 2024).

Numbers (USD, for scale; all approximate):
- SOFR minus reverse-repo was at or below zero from 2022 until the March 2023 quarter-end (+7 bp), then rose temporarily at every quarter-end. Sep 2024 and year-end 2024 peaks about 25-28 bp (SOFR above IORB); base spread about 3-5 bp outside quarter-ends in H2 2024 (FEDS note, 6 Jun 2025).
- Sep 2024 quarter-end: SOFR about 21 bp above its prior-week average (FRBNY, 12 Nov 2024) or 15 bp (Abate, Jan 2025); more than $500bn (FRBNY) or $600bn (Conks, 26 Oct 2024) traded above the standing-repo minimum bid; usage of the facility itself about $2-3bn. Quote both sources when they differ.
- Event study around quarter-ends (2023Q1-2024Q3 averages, day 0 = quarter-end): tri-party borrowing about -$45bn at day 0, recovering by about day +3; sponsored reverse repo about +$135bn; overnight reverse-repo use about +$140bn; sponsored reverse-repo rate +8.5 bp (peak about day +1) (FEDS note).
- Year-end 2024 sequence: SOFR about 4.46 (27 Dec), 4.37 (30 Dec), 4.49 (31 Dec), 4.40 (2 Jan) with fed funds flat at 4.33 (Conks, Plumbing Notes, 5 Jan 2025). Repo stays elevated for days after a turn (trimming is faster than rebuilding) (Abate).
- June 2025: SOFR minus fed funds -7 bp at quarter-end, the first negative since the May month-end; Citi expected below -8 bp for 30 June; good days +3 to +4 bp in July and about -4 bp in September with below -13 bp possible at quarter-end (Citi Research, Short-End Notes: SOFR/FF spiking into quarter-end, 27 Jun 2025). Year-end SOFR-FF of about 4-5 bp expected for Dec 2026 (Conks, Plumbing Feed, 29 Apr 2026); Dec 2025 peaked at 13.5 bp.
- One-month GC/OIS change at the facility spread of 0/10/20/30 bp (J.P. Morgan, What does the SRF mean for swap spreads?, 12 Jul 2019): year-end -15.4 / -9.9 / -7.5 / -6.4; quarter-end excluding December -3.0 / -2.1 / -1.6 / -1.3; other days of 2019 -3.5 / -1.5 / -1.0 / -0.8.
- German one-day GC minus Eonia, average end-of-month change in the spread over 8 years (bp; share of years up in brackets): January +138 bp (up 88%); March -4 (25%); June -16 (13%); July +12 (100%); September -15 (0%); October +14 (100%); December average -188 (0%; min -445) (BofA Securities, Bond market seasonality explained, 6 Jun 2022). German 2y swap spread: January average -3.50 bp (year-end repo-OIS reversal).
- Quarter-end data exaggerate swap-spread moves: measure supply in DV01 and net-cash terms (Citi Research, What to do about OATs?, 1 Oct 2026). Month-end volatility dominates SOFR-FF: model good days separately from period-end prints (Citi, SOFR/FF to go negative in Q3/Q4, 13 Jun 2025).

## 4. Fed funds futures: isolating the year-end premium

Monthly fed funds futures average the daily rate. Let F be the expected pre-December rate (November futures), dDec and
dJan the FOMC steps and YE the year-end excess (positive = overnight rate above neighbouring days). With the December
meeting effective 12 Dec (11 days before, 20 after) and the January meeting effective 30 Jan (29 days before, 2 after):

    FF_Dec = (11/31) F + (20/31) (F + dDec + YE)
    FF_Jan = (29/31) (F + dDec) + (2/31) (F + dDec + dJan)
    FF_Feb = F + dDec + dJan
    dDec = -F + (31/29) FF_Jan - (2/29) FF_Feb
    dJan = (31/29) (FF_Feb - FF_Jan)
    YE   = -(11/20) F + (31/20) FF_Dec - (31/29) FF_Jan + (2/29) FF_Feb

(Citi Research, US Rates Weekly: Fixing the plumbing, 30 Sep 2019). The day counts are one calendar's: re-derive for the
current year (`ff_year_end_decomp` in `scripts/seasonality.py` takes them as arguments; its self-test checks the algebra).

YE is defined in the source as the average overnight rate over 12-31 Dec minus the average over 1-29 Jan; YE > 0 is a premium, and
"a technical FF drop of -4.5bp post the year-end" is the same gap seen from the other side.

Checked worked example. DV01 weights for 100K of year-end exposure are the coefficients times 100K: -55K (Nov), +155K
(Dec), -107K (Jan), +7K (Feb); the source prints -55K : 155K : -106K : 7K, contracts -1375 : 3875 : -2672 : 172. Policy
neutrality check: December step exposure = 155K x 20/31 - 107K + 7K = 0; January step = -107K x 2/31 + 7K = 0; parallel
= -55 + 155 - 107 + 7 = 0; year-end = 155K x 20/31 = 100K. Trade as published in 2019: sell the November contract, buy December, sell January and buy February
in that ratio; the package quoted +4.5 bp (27 Sep 2019) with DV01 100K, target +1.5 bp, stop +6 bp, i.e. a fade of the
year-end premium (in futures-price terms, long the December contract is short the premium). Stated risk: a messy quarter-end
that gets extrapolated to year-end; the note also offered a version with the December-meeting OIS. The market-implied
year-end drop of -4.5 bp was called rare against a largest realised drop of -2.65 bp.

## 5. Turns in FX-OIS and cross-currency basis

- The very short-end basis widens into quarter-ends (Japanese banks avoid borrowing, foreign banks cut lending) and tightens after (J.P. Morgan, Drivers of cross currency basis in EUR, GBP, JPY, AUD & CHF, 11 Mar 2015).
- "The year-end basis market tends to overprice tightness in advance and then sell off as the year concludes" (Conks, Plumbing Notes: Swifter Injections, 4 Dec 2025).
- Year-end turn in EUR, JPY and CAD basis was at multi-year tights before any G-SIB change (Citi, STIRT Weekly: You Shall Not Pass, 14 Aug 2026). Decomposition of 3m JPY government-bond asset swap vs USD (4Q24): model 26.7 bp vs 13.2 bp actual; components CP-bill 10.6, regulatory/liquidity 15.0, year-end turn +15 (J.P. Morgan, Cross currency basis 4Q24 Outlook, 26 Sep 2024; the 2H25 outlook of 5 Jun 2025 uses about +15 bp for October-December).
- CAD July-August month-end turn: FX-OIS round trip 40 bp (+20 to -20); overnight FX-OIS tightened 70 bp to +60 (Citi, STIRT Weekly: Tokyo, we have a problem, week of 7 Aug 2026).
- NZD: tax outflows cut settlement cash from NZ$26.5bn to NZ$24bn and the overnight index vs SOFR 1w-1m tightened 5.0-7.5 bp (Citi, STIRT Weekly: Beam me up, Scotty, 21 Aug 2026). USD/JPY 1Y basis range 2015 -30 to -50 bp with a flattener placed before quarter-end (J.P. Morgan, 11 Mar 2015). FX-swap notional of four G-SIBs fell 6.2% quarter on quarter into year-end 2019 (-0.4% in 2018, -8.7% in 2017) (J.P. Morgan, There is one market where USD funding stress could reemerge, 20 Feb 2020).

## 6. A turn-occurrence and magnitude model (house defaults, uncited)

For a repo or spread series where turn days are not exactly dated:
1. Turn window = last 2 business days of the month plus the first business day of the next. Local base = median of the trailing 15 non-turn observations.
2. Occurrence: logit of (spike over local base > 5 bp) on log liquidity (reserves, balance-sheet room) and a quarter-end dummy (Mar/Jun/Sep/Dec with day >= 25; year-end = Dec with day >= 25).
3. Magnitude: quantile regression of the spike on the same regressors at q = 0.5 and 0.9. Expect about 2 effective spike days per turn.
4. Activate only after 750 training days and 24 turn events; below that, report the empirical window average with its n and nothing model-based.
5. Include mid-month tax and coupon-settlement days as calendar dummies (Conks, Plumbing Notes, 15 Sep 2025).

## 7. Pitfalls specific to turns

- A quarter-end spike is not scarcity alone: check base spread, ex-month-end average and net supply-demand first (FEDS note; Conks, 26 Oct 2024).
- SOFR-FF near quarter-end is seasonal, not a regime change (Conks, 27 Jun 2024).
- The year-end turn premium is customarily priced but rarely realised; the overnight rate often collapses on the day (Lehman Brothers, The Short-End of the Curve, 10 Jul 2007). A fade trade needs the stop sized to the premium plus the roll-in of the leg that spans the date.
- Settlement days and mid-month tax dates produce squeezes outside the period-end windows; large coupon settlement on a quarter-end is the worst case.
- Regulatory changes move the target: the June 2019 disclosure change damped spikes and a daily-average G-SIB calculation would reduce year-end window dressing (BofA Global Research, US Treasury repo primer: 2025 edition, 7 Jul 2025). Re-estimate after each regime change and keep pre/post samples apart.
- December futures historically trade cheaper to adjacent expiries (higher yield) from year-end interbank credit tightness; this origin was a 1980s liquidity episode, diminished in the 1990s and revived by the Y2K sell-off (Aikin, STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed., 2012).
