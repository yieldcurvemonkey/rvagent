# G10 pricing bases, snapshot tables, cycle statistics and trade cases

Supporting data for [SKILL.md](../SKILL.md). Snapshot numbers are dated levels from the cited notes: they show format
and orders of magnitude, they are not current market data. Never reuse them as inputs.

## 1. Pricing base and conventions by market
| Market | Meeting-dated instrument | Base to subtract (current/stub) | Date to use | Notes |
|---|---|---|---|---|
| USD | policy-dated OIS; 1M average and 3M compounded SOFR futures; fed-funds-average futures | effective fed funds (EFFR), not the target-range mid | day after the meeting | 8 meetings/yr; 25bp move assumed; average-only products give a mean, not a distribution; SOFR-target spread is volatile (options need an assumption) |
| EUR | euro short-rate meeting-dated OIS | average of the prior reserve-maintenance period, or last fixing | effective date (Wednesday after the meeting), not meeting date | euro short rate trades below the deposit rate (add ~6-10bp); cuts likelier at staff-projection meetings (Mar/Jun/Sep/Dec) |
| GBP | MPC-dated SONIA OIS (start/end on consecutive MPC publication dates) | SONIA fixing; Bank Rate is not tradeable | MPC publication date | SONIA OIS settles T+0 (others often T+2); 8 meetings/yr; SONIA vs Bank Rate differs by 1-2bp |
| JPY | TONA OIS by meeting; OIS by IMM date | TONA fixing | per source, meeting dates with new rate from the start of the reserve maintenance period (16th-15th): verify per meeting | BoJ rarely moves back-to-back; strip 1-April turn |
| CAD | CORRA meeting OIS | effective overnight rate; gauge = 6m forward CORRA minus effective | meeting date | corridor: deposit = target - 5bp, standing facility = target + 25bp; month-end turns can round-trip ~40bp in FX-implied OIS |
| AUD | RBA meeting OIS | cash rate | meeting date | 8 meetings a year since 2024 (11 in the older studies cited below); statement-on-monetary-policy months Feb/May/Aug/Nov; bank bills trade 8.5-10bp over OIS and are not policy |
| NZD | RBNZ meeting OIS | OCR; check table header against the actual stub | meeting date | 7 meetings a year; headers go stale (header 2.25%, stub 2.50% in one table); settlement-cash drives some basis, not the path |
| CHF | SNB meeting OIS (SARON) | SARON | meeting date | quarterly meetings (4 a year); policy at/near zero floor: stub can be negative (-5bp); SNB used to target 3m Libor so IBOR futures were close to policy then |
| SEK | SWESTR meeting OIS | SWESTR | meeting date | meeting OIS illiquid: published tables use a best-guess path; central bank's own rate path can be read as a probability |
| NOK | NOWA meeting swaps | NOWA | meeting date | front meetings vs later meetings spreads are the liquid expression |

Corridor/floor facts (BofA Global Research, Global policy implementation: a short guide, 9 Jul 2025): Fed range
4.25-4.50 with IORB 4.40, ON RRP 4.25, discount window 4.50 (all Jul-2025); ECB DFR 2.00/refi 2.15; BoE reserves
remunerated at Bank Rate; BoC deposit = target - 5bp; RBA exchange-settlement balances at cash rate - 10bp (moving from
floor to corridor); BoJ targets the uncollateralised overnight rate. "Banks with narrower deposit facilities have
leakier floors": a leaky floor lets the overnight rate sit below the policy rate and biases a naive path.

## 2. G10 "what's priced in" table, 14 Aug 2026 (cumulative bp vs stub, by effective date)
(Citi Markets STIRT, G10 What's Priced In, 14 Aug 2026). Step = difference of successive cumulative numbers.
| CB (rate) | Stub | Cumulative bp by meeting |
|---|---|---|
| FOMC (3.50-3.75) | 3.631 | 16-Sep 8.0; 28-Oct 13.5; 9-Dec 22.9; Jan-27 27.4; Mar-27 33.2; peak 36.3 Jul-27, then small cuts to 33.8 |
| ECB (2.25) | 2.188 | 10-Sep 23.0; 29-Oct 28.4; 17-Dec 40.3; Mar-27 49.9; Oct-27 57.3 |
| BoE (3.75) | 3.731 | 17-Sep 5.1; 5-Nov 17.0; 17-Dec 27.7; Mar-27 45.0; Sep-27 57.9 |
| BoC (2.25) | 2.277 | 2-Sep 1.0; Oct 6.2; Dec 15.9; Jan-27 27.0; Oct-27 78.3 |
| RBA (4.35) | 4.347 | 29-Sep 3.4; 3-Nov 11.9; Dec 15.6; peak Feb-27 18.3; cuts to 10.6 by Nov-27 |
| RBNZ (stub 2.500) | 2.500 | 1-Sep 22.6; Oct 33.7; Dec 49.5; Feb-27 66.0; Dec-27 105.4 |
| BoJ (1.00) | 0.979 | 18-Sep 20.0; 30-Oct 26.6; 18-Dec 40.3; 22-Jan-27 50.4 |
| SNB (0.00) | -0.053 | Sep 1.2; Dec 6.1; Mar-27 16.2; Jun-27 26.4; Sep-27 31.5 |
| Norges (4.25) | | 24-Sep 14.0; 5-Nov 20.2 |
| Riksbank (1.75) | | 20-Aug 2.3; 24-Sep 12.3; 4-Nov 19.5; 16-Dec 25.2 |

Mid-Aug summary (current fix; cumulative bp to end-26/27/28; CitiFX Wire STIRT, G10 What's Priced In, ~mid-Aug 2026):
FOMC 3.63% 25/40/37; ECB 2.19% 42/60/60; BoE 3.74% 27/57/55; BoC 2.27% 21/91/105; RBA 4.36% 15/9/4;
RBNZ 2.50% 53/111/133; BoJ 0.98% 39/97/126; SNB -0.07% 4/35/49; Norges 4.26% 20/5/-25; Riksbank 1.75% 21/76/94.
FOMC steps Sep 9.7, Oct 5.4, Dec 10.1, Jan-27 5.3, Mar 6.9 ... Sep-27 -0.5, Oct-27 -1.4 = hike-then-small-cut hump.
Standard layout to reproduce: per meeting `implied rate | step | cum | change on day | change on week`, plus a summary of
current fix and cumulative bp to end of year 1/2/3.

### House path vs market, bp change from current (JPM house / market; J.P. Morgan, Economic Activity Tracking, 14 Aug 2026)
| CB | end-3Q26 | end-4Q26 | end-2Q27 | end-4Q27 |
|---|---|---|---|---|
| US | 0 / 8 | 25 / 22 | 25 / 35 | 25 / 29 |
| EMU | 25 / 27 | 25 / 41 | 25 / 54 | 0 / 52 |
| Japan | 0 / 19 | 25 / 41 | 50 / 74 | 100 / 96 |
| UK | 0 / 15 | 25 / 36 | 0 / 55 | -25 / 54 |
| Norway | 0 / 14 | 25 / 22 | 0 / 16 | -25 / -2 |
| Sweden | 0 / 19 | 25 / 36 | 25 / 67 | 25 / 80 |
| Canada | 0 / 3 | 0 / 19 | 0 / 60 | 0 / 83 |
| Australia | 0 / 3 | 0 / 14 | 0 / 12 | -49 / 3 |
| New Zealand | 25 / 23 | 50 / 49 | 75 / 89 | 75 / 118 |
Largest market-minus-house gaps: Canada 2027 (+83bp vs 0), UK and EMU 2027, Sweden; NZ roughly aligned. Published
market paths lag 1-2 days.

## 3. ECB-dated euro short-rate tables (format and an applied view)
- 17 Jan 2024 (rate % / from last fix bp / by-meeting bp): Jan 3.904/-0.7/-0.7; Mar 3.859/-5.0/-4.3; Apr 3.695/-21.8/-16.7;
  Jun 3.382/-52.7/-30.9; Jul 3.118/-79.2/-26.5; Sep 2.867/-103.9/-24.7; Oct 2.679/-122.9/-19.0; Dec 2.490/-141.6/-18.7;
  Jan-25 2.339/-156.7/-15.1. March moved ~-15 to -4bp and April ~-25 to -16 as cut pricing was pushed back. Scenario
  end-points for the euro short rate: base 2.25% deposit rate (~215.5), late/slow/high 3% (~290.5), early/fast/low
  1.5% (~140.5), market ~207. Trade: receive 1y2y/3y2y/5y2y 6s fly at -8bp (target -25, stop +5) to fade early-cut
  pricing while keeping a sub-2% end-point open; carry/12m 79.2, 1y realised vol 46.5bp, carry/vol 1.70
  (Nordea Markets, EUR rates: Pushing back, 17 Jan 2024). Rule used: "the number of cuts matters more than the timing of
  the first; for EUR swap curves the end-point matters even more."
- 19 Jun 2025 (rate / d1d / d1w / from last fix / by meeting): Jul 1.907/-0.5/1.4/-1.7/-1.4; Sep 1.805/-0.2/4.2/-11.9/-10.1;
  Oct 1.772/0/4.5/-15.2/-3.3; Dec 1.698/0.4/4.9/-22.6/-7.4; Feb-26 1.682/-24.2/-1.6; Mar 1.663/-26.0/-1.8. With about one cut
  priced and risks skewed to cuts, "it is easier to price more cuts back in than to price out the last one"; 2y1y is the
  market-implied neutral. Receive 2y1y: carry+roll 25.6 (convexity-adjusted 27.1), 252d realised vol 77.4, ratio 0.35,
  50d z 0.1, PCA mispricing 17.6 (Nordea Markets, EUR rates: Risk/reward favours receiving ECB meetings, 19 Jun 2025).
  Counter-risk: the receive idea was consensus and the hawkish June-2025 reaction hurt.
- Cross-bank base normalisation (Nordea Markets, EUR Rates Flash, 5 Feb 2020): Fed base = effective rate (1.590, mid 1.625);
  ECB base = average over the previous maintenance period (-0.539, fix -0.536); BoE base = SONIA fix (0.710).
  Probability from cumulative pricing with a 10bp step (negative-rate era): -5.9bp by 10-Dec-2020 / 10bp = 59%.

## 4. Option- and market-implied distributions (summary; method in the options skill)
- SOFR option-implied Fed weights on the Dec-2025 3M contract, 2 Jun 2025 (normal mixture, means 25bp apart):
  4.75 ~0; 4.50 ~0.06; 4.25 ~0.28; 4.00 ~0.07; 3.75 ~0.36; 3.50 ~0; 3.25 ~0.24 (bimodal, large policy uncertainty)
  (J.P. Morgan, Cross currency basis 2H25 Outlook, 5 Jun 2025).
- Call spread as digital: a 99.75/100 call spread on a 3M IBOR future = probability the fixing is <= 25bp; peaked ~12%
  six months out (J.P. Morgan, Interest Rate Derivatives: Impossible to walk in this muck, 6 Mar 2020). Recession proxy: P(policy < 2.75% by next June)
  = 22% from SOFR options (JWS Macro, USD Rates & Fed outlook #1, 21 Aug 2025).
- Straddle breakevens sitting on the two discrete outcomes = priced for a binary event: breakevens 96.08/96.295 versus
  25bp-hike settle ~96.09 and unchanged ~96.345, expiry on CPI day (Citi Markets, SOFR/CBOT Vol EOD, 21 Aug 2026).
- Prediction-market threshold contracts (binary "upper bound above K after meeting", price = P(X > K)):
  last trade per strike per day, forward-fill stale strikes, drop strikes untraded > 60 days. No-arbitrage repair
  "middle-out": centre = strike priced closest to 49c; sweep left raising any lower-strike price below its inner
  neighbour; sweep right lowering any higher-strike price above its inner neighbour. Survival S(K) = P(X > K); PMF =
  differences of S; bubble zero buckets inside non-zero extremes outward; normalise by the 98c range. Example
  Dec-2025 FOMC on 1 Aug 2025: S(4.25) = 20c, S(4.50) = 4c -> P(UB = 4.50) = 16%; mean 3.98 < median 4.00 < mode 4.25.
  Accuracy at t-1 over 35 events (Mar-2022 to Jun-2026): median error 0.7bp, mean 1.7bp versus 1.4bp for the
  fed-funds-futures read; mean error ~40bp at 180 days to ~0 at the meeting; mean converges to futures/OIS inside ~100
  days, median/mode converge faster (Morgan Stanley Research, Kalshi Markets as Macro Signals, 18 Aug 2026).
  Median/mode versus a futures mean is not like-for-like (the mean carries risk premia).

## 5. Central-bank behaviour regularities (use as priors, small samples)
- BoJ: market "doesn't price more than 80% of a hike until 1 week before the meeting" and "has never priced more than
  25bp in back-to-back meetings for more than 1 day"; last two hikes were preceded by a meeting with >= 2 hawkish
  dissenters, a single dissent read as dovish (Citi GMS, Macro tapas, 7 Aug 2026; Citi House Views Aug 2026, 21 Aug 2026).
  Intervention-driven repricing front-loads rather than raises the total (Citi STIRT Weekly: Tokyo, we have a problem, 7 Aug 2026).
- Forecast-meeting effect, moves since Dec-1998 by share in meetings with new forecasts (cut/hike %): Fed 39/57; ECB
  44/45; RBA 46/61; BoE 46/67; BoC 55/44. Fair value for meeting spreads: RBA 61%/4 = 15.3% of hikes per forecast
  month versus 39%/7 = 5.6% elsewhere (3:1); ECB 45%/4 = 11.25% versus 55%/8 = 6.9% (1.6:1). If May/Aug and Aug/Nov RBA
  spreads each price 10bp, Aug/Sep and Sep/Oct should be ~2bp each; with 10bp of ECB hikes a quarter no single spread
  should be flatter than ~2.75bp. "The market tends to under-price the probability of a hike in meetings when the
  inflation forecasts are not updated" (swapsball.net, Central bank decisions and inflation forecasts, 8 Mar 2018).
  Chi-square test at 95% against equal meeting likelihood; hikes rarely come intra-meeting, cuts can.
  Caveat: the sample had 11 RBA and 12 ECB meetings a year; both now meet 8 times (4 with projections), so the per-meeting odds fall
  to ~1.6:1 (RBA) and no longer favouring projection meetings at all (ECB: 45% vs 55% over 4 + 4) - re-derive before using the spread rules above.
- Fed (Willer & Saunders, Trading Global Macro Markets, Wiley 2026): post-1986 hiking cycles median 12 months, 8 hikes,
  total 2.62%; easing cycles median 8 months, 4 cuts, 2.25%; soft-landing easing cycles (1995, 1998, 2024) all delivered
  75bp. A cycle hike (cut) month: policy rate above (below) both prior two months and next quarter higher (lower).
  The Fed usually cuts more than priced over 12m (by a wide margin in hard landings); hikes priced outside a hiking cycle
  often do not come; inside a hiking cycle the Fed delivers more than priced (2022). The 6th-month minus 1st-month fed-funds futures rate below -12.5bp (>= half a cut
  priced 6m out) preceded cuts or no hikes in 10 of 11 events; failure 03-2023 (-34bp, then +50/+75 over 3m/6m, inflation
  > 5%). After a >= 12.5bp inversion, P(cut) within 6/12/24m: 6m2s 57.9/73.7/84.2%; 2s10s 50.0/57.1/85.7%; median across
  pairs 43.8/65.0/93.3%. Median lag from the first 3m10y inversion to the first cut 18 months (range 1-23; lengthens
  with inflation). 2y timing: pay ~2.5-3m before the first hike, stay paid through pauses, cover near the last hike;
  press receivers ~3m before the first cut; "being on hold for six months is usually just the same as being done".
  Score an FOMC by the 2y move: receive/pay after a move >= 2 s.d. of trailing 1-month changes.
- Priced vs delivered (Citi, JPM, Credit Suisse): forwards rarely price more than 70-80% of an eventual cycle (J.P.
  Morgan, The long and short of it, 3 Aug 2018); 4th Eurodollar contract "predicted" the funds rate well only twice
  (Credit Suisse, Forwards are NOT a Prediction, 12 Aug 2013); implied-vs-realised correlations for 3m-6y forwards
  0.45 down to ~0 beyond 1y (Salomon Brothers, Understanding the Yield Curve Part 7, Feb 1996). Over-shoot loop: banks
  move calls, the central bank endorses, the market prices more until a 50bp call = "fully cooked"; "you never fade at
  fair value, you fade a deep value" (JWS Macro, Central Casting #6.1, 21 Jun 2026).
- Calendar logic: choose the meeting from the event calendar, not only data: an October FOMC less than a week before
  midterms makes a hike unlikely, so data strength pushes hikes into December (Citi GMS, No inflation trouble, 13 Aug 2026).
  With one CPI print before a meeting put low odds on a move (Citi Research, Nordic Economics Flash, 20 Aug 2026).

## 6. Applied trade cases with levels and outcomes
| Case | Structure and levels | Outcome / lesson |
|---|---|---|
| Fed Oct-2026 receiver (Citi GMS, 7 and 13 Aug 2026) | receive the October FOMC meeting at 3.8075, 50k DV01, target 3.63, watch 3.91, risk $500k = 0.5% of book | marked 3.78, +$150k a week later; trade table showed December/25k DV01: verify when text and table conflict |
| Fed Sep/Oct/Dec fly fade (Citi, Short End $waps, 23 Jul 2026) | short Jul/Sep/Dec 1x2x1 and 0.5x2x1 meeting flies and front/back futures steepeners; pay Sep/Oct/Dec fly at -3 to -2.5bp, target 0 to +3 | July ~5bp (~20%) expected; underweight the near leg for less front-meeting exposure; reduce if July reaches 12.5bp |
| FF year-end premium (Citi, 30 Sep 2019) | sell Nov, buy Dec, sell Jan, buy Feb average contracts at -55K:155K:-106K:7K DV01; level +4.5, target +1.5, stop +6 | market-implied YE drop -4.5bp vs max historical -2.65bp: fade the premium; risk: messy quarter-end extrapolated |
| Stub OIS inter-meeting option (Citi, 2 Aug 2019) | receive spot OIS maturing on the 18-Sep-2019 meeting date at 215.7 vs EFFR 214, 50K DV01 | pays ~19:1 if a mid-Aug 25bp cut, ~10:1 end-Aug, +1bp if none: stub OIS has no exposure to the scheduled meeting (decision effective next day) |
| BoE one meeting at a time (Citi, 20 Aug and 17 Sep 2026; JPM 21-22 Aug 2026) | receive Sep MPC SONIA 3.77% (+7 closed), then Nov MPC at 3.94% (target 3.83, stop 3.985) as a macro hedge, not held to the meeting; MPC OIS 5bp Sep/17 Nov/28 Dec | premium came out slowly; expect >= 3.5-4bp priced for Sep; Sep/Nov 12.25bp, Dec/Feb 10.45bp |
| ECB meeting spreads (Citi, 7 and 21 Aug 2026) | pay Sep/Nov ~+4.75bp ("little downside"), Nov/Dec in single digits, Sep/Dec ~12bp (was 15); get long near 3 full hikes priced to end-2027 | 21 Aug: 41bp/57bp cumulative to end-26/27; Sep/Nov flattened 3.3bp in a week |
| RBA (Citi 7 Aug; BofA 2 Oct; JPM 21-22 Aug 2026) | pay Sep/Nov RBA step into rallies (+8.0bp); pay Nov RBA OIS at 9, target 25, stop 3, latest 7.6 (economists ~13bp); Nov-26/Aug-27 RBA OIS flattener -18.4 | meeting spread paid from the cheap side |
| BoJ (Citi 7, 13, 14, 21 Aug 2026) | Sep 16bp "about right (15-19)"; Sep+Oct 24 right; Sep+Oct ~28 should be vs 25; Dec+Jan 23 right; ~50bp after Jan "a bit rich"; June/Sept meeting flattener 14.5 (target 0, stop 21) +6; pay 1y OIS 121.5 -> 138.5, 40k DV01, +$518k | receiving the second of two consecutive meetings = cheap risk-off hedge; capped near-term payoff of being paid the near meeting |
| SEK/NOK (Citi 7, 14, 21 Aug 2026) | receive Dec SWESTR into the meeting captured Sep repricing 50% -> <35%; then pay Sep/Dec SWESTR (MPR path higher); NOK receive next meeting vs pay Nov (Sep hike ~55%, 80% a month earlier) | pre-meeting: when pricing is more hawkish than the bank can validate, reaction risk is dovish |
| CAD (Citi 21 Aug 2026) | priced 35bp to Jan-27, ~70bp mid-27, ~93bp end-27 versus house next move a cut; receive | gap between house path (-50bp) and ~+95bp priced is the implied view |
| Fed terminal cushion (Citi, 13 Aug 2026) | 1x2 put spread in the Dec-2026 3M contract for a 2.5c credit; profitable to a 77bp sell-off (4.27%), max at 37.5bp | thesis: ~3-hike terminal cushion overdone; sell rich vol and put skew; marked 8.25 ticks, +$267k |
| Eurodollar inversion event study (Citi, 18 Jan 2019) | 1y-forward 2s10s after the first inversion of the 1st vs 4th Eurodollar contract: +55.1/+14.4/+189.5/-30.1/+151.4bp (5 episodes) | curve bull-steepened in 4 of 5; "time even 6 months after the first inversion to initiate steepeners" |
| Closed-outcome log 2026 (Citi GMS, 7 Aug 2026) | 229 trades since 2023, 51% in profit, risk per trade 0.25-1% sized to the loss at the watch level | trailing stops: a conflict can overtake a policy story |

## 7. Cross-market gauges
- Year-end hikes (Dec-2026 contract month) priced in 3M euro, SONIA and SOFR futures side by side; Apr-2026: US 1 -> 0 hikes, UK
  4 -> 1.5, EU 4 -> 3 while 1y1y inflation swaps stayed flat. Pricing at or above the maximum plausible hikes (BoE/ECB
  <= 50bp) was called peak impact, i.e. a fade candidate (Conks, Plumbing Notes: War & Plumbing, 11 Mar 2026; The Peak-TACO
  Era, 9 Apr 2026). The claim "the Fed has never hiked into a temporary (< 6 months) inflation shock" is the author's, not verified.
- 1y1y SONIA vs 1y1y euro short rate: y = 1.09x + 1.4, R^2 95% over 5m (J.P. Morgan, Global FI Markets Weekly, 21-22 Aug 2026).
  10y OAT-Bund spread widening while euro hike pricing falls = regime-change / policy-error signal (Citi Research, What to do
  about OATs?, 1 Oct 2026).
- 1y OIS minus fed funds has a floor near zero when the ISM manufacturing index is rising; with < 40bp of easing priced,
  front-end yields are sticky (J.P. Morgan, FX Markets Weekly, 21 Aug 2026).
- 2y1y as market-implied neutral: record the forward policy level whenever the 1y1y vs 5y5y curve crosses flat (US ~4.10-4.15%,
  drifting up since 2021); a falling 5y5y can signal a credible hike, not weak growth (JWS Macro, Central Casting #6.1,
  21 Jun 2026; Global Rates Outlook #4, 8 Apr 2026).
- Term-rate arithmetic: an X-year rate ~ average of the forward overnight path (24 monthly forwards for 2y, 60 for 5y);
  near-term cut timing and pace dominate 2-3y, the terminal level dominates 4y+ (BofA Global Research, US Rates Watch: Rates basics:
  fixed versus float, 24 Apr 2024). 2y swap minus EFFR averaged ~74bp since 1994 (~62bp post-GFC): 2y 1.696% on a 6m-forward
  basis minus 0.62% = 1.076% versus EFFR 2.375% = ~130bp = five cuts (Convexity Maven, For Propeller Heads Only, 17 Jun 2019).
- Taylor-rule grids and money-based stance checks forecast poorly out of sample (no specification gave a high
  out-of-sample Sharpe); use as terminal anchors only. Real policy rate (nominal minus core PCE) peaks 2.5-4.5% in a typical
  cycle (BofA, Global Rates Weekly: Start of rates bite, 2 Oct 2026; Willer & Saunders 2026).
