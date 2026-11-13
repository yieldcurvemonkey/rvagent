# Dated skew readings (regime context)

Snapshots from sell-side skew monitors, to calibrate what "2 sigma" looked like in different regimes and to show how readings
changed with policy and flows. RR = payer minus receiver normal vol at the monitor's OTM distance; "to realized" = market minus
empirical-SABR model (vol pts), z = 1y z-score unless stated. Backward-looking; not current levels. Method in
[SKILL.md](../SKILL.md) section 3. Source for all rows: Citi Research, Rates Vol Lab (month shown) unless stated.

| Date | Reading |
|---|---|
| Dec 2016 | RR 1y z mostly +2 to +3 for 6m-2y expiries; receiver skews -2 to -3.4; 3m30y RR z 2.76; 1y2y RR > 2 sigma rich to realized (spread 1.6, z 2.2), mainly from cheap receivers; longer tails smile too cheap. Forecast: skews flatten by H2 2017. MBS-driven demand for low strikes in a rally flattens skew |
| Jan 2017 | 6m30y RR > 2 sigma rich to realized skew (receivers cheap to model); 2y30y RR ~2 sigma rich; receiver skews cheap to call skews in the bond future |
| May 2017 | ATM vol collapsed but skew barely moved; short-dated RRs slightly inverted; market minus realized RR (1y z): 3m1y -2.3 (-0.9), 3m5y -1.8 (-1.4), 3m10y -1.9 (-1.1); expected high-strike demand to return into the June FOMC |
| Jan 2018 | Upper-left receiver skews richened, payers cheapened; upper-left RRs (e.g. 1y2y) at a large discount to realized skew |
| Mar 2018 | 3y1y RRs 3.3 sigma cheap to realized skew; put skew on futures rich to payer skew; "when skew fights the Fed" (front-end receiver skew rich while hikes priced) |
| Jan 2019 | Smile richened (payers and receivers); 3m2y RR -10.7nv but rich to realized; 3m30y RR 2.5 (z 1.0); 5y30y RR 1.2 (z 2.0); long-dated payer skews (10y10y) bid |
| Mar 2019 | 5y10y RRs > 2 sigma rich to realized; short-dated RRs cheapened, long-dated richened; call skew rich to receiver skew |
| May 2019 | 5y30y RR > 2.7 sigma rich to realized; long-expiry RRs rich generally; 3m change in 3m10y skew ~flat = neutral duration signal |
| Sep 2019 | Short-dated RRs highly inverted: 3m1y -8.7, 6m1y -11.8, 1y1y -10.4nv; 3y30y RR +15.0nv vs model (z 2.3); 3y-5y OTM payers 1.16-1.21x model (z ~2-2.5) |
| Jan 2020 | Longer-dated payer skew very cheap historically; short-dated RRs slightly inverted; short-expiry RRs cheap to realized (6m10y ~2 sigma); EUR short-dated RRs richened into positive |
| Mar 2020 | ZLB onset: 3m10y RRs ~3 sigma rich to realized, short-dated RRs richened especially 3m2y; long-expiry payer skews richened and receiver skews cheapened (2y-3y expiry receiver z -3 to -4); Board smile rich to swaption smile |
| Jun 2021 | Left-side (receiver) vols outperformance; skew conventions per monitor |
| Feb 2023 | 3m30y OTM payer price/model +1.2 sigma (30y-tail payers most overvalued); EUR 3m30y RR > 2 sigma above its 1y mean (down from 3.2 in late Jan) |
| Jun 2023 | Payer skews rebounded on upside-breakout fears (expected short-lived; favour short-dated receiver skew); 3m10y RR +6.0 vs model = +2.9 sigma; 3m10y OTM payer/model 1.04 (z 3.2), receiver 0.98 (z -2.8); EUR 2y10y RR 2 sigma cheap on 1y; Board puts above swaption payers, calls below receivers. Vol regime: declines in the months after the last hike; tail risk is a hawkish surprise pushing the last hike out |
| May 2026 | SONIA options: ~25-30% chance of Bank Rate back at 5.25%; cut distribution cheap; skew bid for puts out to Mar-27, calls richer beyond (JWS Macro, Global Rates Outlook #5, 10 May 2026) |
| Aug 2026 | 3m30y RR low vs model, 5y30y high at a long-run peak: "not worried about near-term de-anchoring, but the long-run fiscal tail remains"; long-bond Board put skew cheapened after a buyback announcement but still elevated (Citi, US Rates Weekly, 21 Aug 2026) |
| Sep 2026 | 6m30y RR slightly low vs model, 5y30y high; 3m30y and 1y30y RR at -1.2 sigma (cheap); bottom-right payer skew anecdotally driven by non-rates investors buying deep-OTM payers as fiscal tail hedges; EUR 3m2y payer skew fell and receiver skew rose from early-July highs/lows. Board/swaption vol ratios 5y 1.01, 10y 1.03, long bond 1.14, ultra 1.17 |
| Oct 2026 | USD long-expiry payer skews richening at multi-decade-high yields (1y-10y expiry payer skew 1y z ~+1.6 to +2.8, receivers ~-1.4 to -2.9); front-end receiver skews below ATM; long-dated RRs still rich to SABR but less; EUR payer skews cheapened from July highs, 10y-tail RRs rich via low receiver skew; US Board put skew well above call skew; a 3Yx10Y 200bp RR sold delta-hedged was stopped at -8.2 abp (JPM, US IRD, 2 Oct 2026) |

## Lessons from the readings
- RR rich to realized by 2-3 sigma persisted for months in several periods (Dec 2016, Mar 2019, Mar 2020, Jun 2023): a screen is a reason to
  investigate flows, not a trade; stops matter.
- The sign of the mispricing often differs by corner: upper-left receivers cheap while bottom-right payers rich (fiscal-tail demand) is the
  recurring 2026 pattern.
- Short-dated RRs inverted (receivers over payers) usually reflected positioning (core shorts hedged with OTM receivers) or a pending hiking
  cycle, not a bullish consensus; cross-check CFTC-style data.
- Signal table (3m change in 3m10y 25bp-out RR -> next-month 10y change, Jan 2006 - Nov 2016, Citi, Jan 2017): see SKILL.md section 6. Jan 2017
  reading: RR rose from about -1 to +8 (Sep-16 to Jan-17), then ~4.5; the 3m change moved from the top bucket to 50-75 = "not an outright long
  signal yet", consistent with record leveraged-fund short futures DV01 and peak survey optimism; no formal trade.
