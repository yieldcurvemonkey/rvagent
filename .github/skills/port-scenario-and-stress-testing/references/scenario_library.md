# Scenario library: named windows, hypothetical templates, per-market notes

Companion to [SKILL.md](../SKILL.md). Windows are replayed as the **level change per tenor** between the window end
points (`window_shocks` in `scripts/scenarios.py`), applied to the current key-rate ladder. Numbers below come from the
cited sources; reconstruct the exact shocks from the user's own `curve_par` history rather than from this page.

## 1. Named historical windows
| Window | Dates | Why it is in the suite | Source facts |
|---|---|---|---|
| COVID / March 2020 | 2020-02-20 -> 2020-04-30 | basis unwind, repo and liquidity dislocation, dash for cash | 99th-pct repo - SOFR peaked 174bp on 16 Mar; small-trade execution cost ~10x; basis-linked hedge-fund UST sales est. $35-173bn; foreign sales ~$400bn; liquidity index 2.44 (31 Mar) vs 5.32 (13 Mar) (CFTC MRAC Dec 2024; Tuckman & Serrat 2022; J.P. Morgan, Are we there yet?, 1 Apr 2020) |
| 2022 hiking year | full calendar 2022 | inflation shock; bonds and equities fall together; positive stock-bond correlation | Treasuries failed as an equity hedge, credit shorts protected (Willer & Saunders 2026) |
| SVB | 2023-03 | front-end rally and curve steepening shock | named stress window in backtest specs; reconstruct from data |
| Tariff shock | 2025-04 | cross-asset risk-off | reconstruct from data |
| GFC 2008 | autumn 2008 | funding and basis disruption; Z 5.2 on the risk ruler | required in basis-trade stress (CFTC MRAC 2024) |
| Taper tantrum | May-Aug 2013 | 10y 1.7% -> 3%; convexity-hedging event | 10y +81bp (z 2.8), swap spread +13bp (z 1.9) May-Jul 2013 (BofA, MBS convexity hedging primer, 18 Mar 2021) |
| 2003 convexity / JGB VaR shock | Jun-Aug 2003 | ~150bp UST sell-off in 3 months; JGB stop-loss feedback | 10y +145bp (z 4.1), swap spread +19bp (z 2.3); JGB selling waves June and August 2003 (BofA 2021; During, Fixed Income Trading and Risk Management, 2021) |
| Feb 2021 | Feb 2021 | small convexity event, 10y ~+30bp | 10y +13bp window, z 1.1 (BofA 2021) |
| Fall 1998 | Aug-Oct 1998 | swap-spread blowout, flight to quality | 8/19-8/20/98 rally with swap spreads +7bp = 5.5 SD; 10/1-10/9/98 10y spot +57bp (3 SD) with swap spreads +9.5bp (Golub & Tilman 2000) |
| NFP shock | 7-8 Mar 1996 | single-print gap | 10y spot +35bp ~ 3.7 SD (Golub & Tilman 2000) |
| Flash rally | 15 Oct 2014 | >35bp in ~12 minutes, principal trading firms > 50% of volume, no single trigger | (Yadav & Younger, Central Clearing the US Treasury Market, 2025) |
| Repo spike | 17 Sep 2019 | O/N repo nearly 10% from ~2% | QT plus tax payments; UST-secured repo briefly dearer than high-yield debt (Yadav & Younger 2025) |
| Debt-limit X-dates | 2011, 2013, 2019, others | bill kinks, GCF repo up to +20bp before X-date | markets price risk ~2 weeks before; 2019 1w prior 10Y +22.5bp, GCF +23.4; 2013 1w post GCF -21.0, 10Y -16.2; 2011 1w post 10Y -36.3, VIX +10.3 (BofA, Debt limit FAQ, 12 May 2025) |
| MBS/bank convexity | see events above | non-linear hedger flow | hedge need for a 25bp move, 10y-eq $bn: Jun-03 169 (10.1% of UST market), May-13 105 (1.7%), Feb-21 63 (0.5%) (BofA 2021) |
| Quant de-risking day | 19 Aug 2026 | momentum crash on a Treasury buyback day | systematic long-short funds -1.4% by 1pm, worst day in 2 years; pure-momentum index -4% while S&P rose (Financial Times, 20 Aug 2026) |

Replay rules:
- Replay in **key-rate space** on today's ladder; do not reuse the P&L of instruments that did not exist then.
- Add the worst 1, 5 and 10-day windows from history (`rolling_pnl`), since named windows miss unnamed ones.
- For new products with short history, replay a proxy market (size a BRL devaluation on RUB/MXN episodes: Golub & Tilman
  2000) and state the proxy and its beta.
- Keep the stress horizon equal to the VaR horizon (liquidation time) unless you are explicitly testing a forced hold.
- Include the institution's own crisis actions (e.g. guidelines that force duration to zero after a 100bp move).
- Event study template for relative-value residuals: define an episode by a rule (fly residual < -5bp vs model for > 1
  week), record when it returns to 0 and when it overshoots (> +5bp), tabulate hit rate and duration. EUR 5s10s30s
  since 2013: 7 rich-fly episodes, normalised with flatter 10s30s 6/7, overshot 5-10bp 6/7, ~3.1 months to fair then
  ~2.7 to overshoot; do not take profit mechanically at zero residual (BNP Paribas, EUR curve convexity, 25 May 2021).
- EUR 5s10s30s fly vs equity risk-off (fly change / VIX change): Oct-14 -20 -> -12bp / 12 -> 23; Aug-15 +5 -> +14 / 12 -> 41;
  Jun-16 -4 -> +7 / 13 -> 26; Jan-Feb 18 -4 -> +13 / 9 -> 37; Dec-18 +2 -> +7 / 20 -> 36; Feb-Mar 20 -16 -> +26 / 14 -> 83.
  Average fly rise 15bp (10y cheapens) for a 28-point VIX rise (BNP Paribas 2021). Use as a risk-off shock for the fly.

## 2. Hypothetical event templates (conditional core/peripheral)
Shock the core variables, imply the rest, then report Z, C and implied peripheral moves (BlackRock 2023).

| Template | Core shocks | Implied / notes |
|---|---|---|
| Soft Brexit (calibrated 23 Feb 2016, Z = 1.5, ruler: Remain 1.2, Adverse 3.5) | FTSE All Share -5%; GBP 2y -25bp (-2.1 SD), GBP 10y -10bp; GBP/USD -5%; UK credit +20bp | UST 10y -9bp, DEM 30y -19bp, JPY 30y -13bp, EUR/USD -2.9%, Italy 5y +7bp, Spain 5y +7bp. Contentious: do gilts rally (safe haven) or sell off (adverse)? Large z-deltas flag the inconsistent UK rates inputs |
| Trade tensions (Jun 2018) | US 10y -35bp, Mexico 10y +80bp, US 10y breakeven +20bp, China equities -20% (3 SD monthly) | UK 10y -30bp, Germany 30y -24bp, Japan 10y -4bp (lowest beta), Spain 5y +15bp, Italy 5y +59bp (periphery widens in risk-off) |
| Inflation shock hedge | +30bp monthly rise in US 10y breakeven (~1% probability on 10y history) | 10-ETF book ex-ante risk 303bp/yr, scenario loss 96bp; allowing 22bp tracking error vs holdings cut the loss 16bp |
| IORB removal (front end) | $500bn-$1tn+ excess reserves move to money markets | rates fall, front-end spreads richen, ON RRP a "very soft floor", SOFR/FF near or slightly tighter (low conviction), more vol around tax dates / TGA; low odds, high impact (BofA, Eliminating IORB, 13 Jun 2025) |
| Basis unwind | half of a $600bn gross levered short unwinds (~$150bn) | futures richen (implied repo up), Treasuries cheapen vs OIS/SOFR (swap spreads tighten), FRA/OIS and FX basis pressure; track futures implied repo (J.P. Morgan 2020) |
| CCP operational event | one CCP impaired | cross-CCP spread vol spikes, direction unpredictable; $1bn 5Y switch LCH receive 1.65642 vs CME pay 1.66842 = 1.2bp give-up ~ $600k, halves basis risk (Clarus 2015) |
| Fiscal stress | separate safe-asset, rollover and central-bank channels | UK 1976: long gilts fell ~20% within months; rollover narratives moved beliefs more than safe-asset erosion; stated perceived crisis probability rose 14.9pp but planned Treasury reductions only 4.2pp (insignificant) (Delao & Li 2026). Do not assume proportional flows |
| Geopolitical | identify triggers, outcomes, what is priced; translate to factor shocks | multiplier: dampen when attention is high, amplify when low (BlackRock 2023) ([macro-geopolitical-risk](../../macro-geopolitical-risk/SKILL.md)) |
| Cross-asset de-risking | 60/40 portfolio drawdown >= 4% in one month as trigger | condition the target asset on the regime; EM local and credit are hit harder than usual, credit recovers faster (Citi Research, EM Strategy Weekly, 20 Aug 2026) |

## 3. Instrument-specific grids
- **CTD (bond futures)**: shift the reference bond (shortest in basket or on-the-run) by -120..+120bp in 20bp steps (or
  +-60 in 10bp), others by yield beta to the reference; steepening/flattening = +-1.5 SD twist about the CTD. Re-run the
  delivery-option model per cell. Example Dec-26 ultra-bond: CTD one issue for -20..+20bp, another for rallies >= 40bp,
  another for sell-offs >= 40bp; twists move the CTD zone by ~20bp (J.P. Morgan, Basis Scenario Analysis Report, 28 Oct 2026).
  Use unbeta'd parallel shifts only to isolate pure duration.
- **Level x slope probability grid** (option-adjusted basis): level -100/0/+100, slope steeper/per-beta/flatter (+-20bp);
  probabilities 0.16/0.68/0.16 on each axis. Cell net-basis-to-CTD [down, unch, up] 32nds: steeper [20, 2, 20]; beta
  [25, 1, 15]; flatter [30, 3, 10]; expected 7.41/32 (Burghardt et al. 2005). Check each issue's weighted forward price equals
  its market forward and the implied ATM option vol matches listed vol.
- **CTD jump risk**: Dec-26 contract DOV ~18/32 near start of October at 30y > 5.6%; a ~20bp sell-off adds ~4/32; DOV ~ 0 after a >100bp
  rally; rule-of-thumb BPV jumps (e.g. 1382 -> 1675) at crossovers, probability-weighted BPV is smoother (J.P. Morgan, The switch and
  the spur, 29 Oct 2026). Futures can be negatively convex near crossovers.
- **STIR futures**: hold the convexity adjustment constant, P0 = 100 - f0 - CA, dP = -df, MTM = round(-df, tick) x BPV,
  BPV = notional x 0.0001 x accrual; a sub-tick rate change gives zero P&L; a constant CA understates risk in big moves or vol
  changes. AUD/NZD futures are quoted in yield and valued via a synthetic bond price; CORRA compounds on 365 (SOFR 360)
  (FactSet, Interest Rate Future, 23 Mar 2023).
- **Vol grid**: project vol-grid risk onto hierarchical PCs: HPC1 broad up/down, HPC2 gamma vs vega rotation (vol term structure),
  HPC3 short vs long tails (BofA, Understanding Principal Components, 21 Aug 2020).

## 4. G10 market notes
| Market | Stress-relevant facts (sourced) |
|---|---|
| USD | Replay March 2020, GFC, Sep 2019 repo, Oct 2014 flash rally, fall 1998 swap spreads, 2003/2013/2021 convexity, 2022, SVB, 2025 tariffs. Basis unwind makes swap spreads tighten. CME trades at a premium yield to LCH (0-6bp on 30y). Debt-limit X-date: bill kink, GCF +20bp. Perceived debt/GDP median 60% for investors vs ~100% actual |
| EUR | PCA on 17 non-overlapping forwards, 1y window. Bear-flattening more likely than bear-steepening; 10s30s flattens in sell-offs. Fly 10y cheapens in equity risk-off (+15bp average). Periphery (Italy, Spain) widens in risk-off. Dutch pension DC transition 2023-27 and the 2012 FTK II reform are structural, not inefficiency; a big 30y rally could cause "a scramble for hedges". MF Global: periphery haircuts 3% -> 80% and French shorts did not hedge haircut risk |
| GBP | Brexit gilt direction ambiguous; GBP swap PCA 1y-60y, 3 PCs ~ 97%; 30y10y-40y10y near all-time flats while 10s30s steepened (2012); 1976 rollover analogue (long gilts -20%) |
| JPY | Least correlated DM swap market (0.2-0.3 monthly), lowest vol, heavy tails; JGB 2003 VaR shock (stop-loss feedback after prolonged low vol); April 2013 QE sell-off; NIRP 29 Jan 2016 cut interbank volumes 75% overnight (recovery ~1 year); JSCC mandate drives the LCH/JSCC basis; realised vol ~0.6% annualised after April 2013 (During 2021; Macrosynergy 2025) |
| CAD / AUD / NZD | Monthly 5y IRS return correlations: CAD-USD 0.8, AUD-NZD 0.8; STIR futures conventions differ (above) |
| CHF / SEK / NOK | EUR-CHF and EUR-SEK 0.8; NOK-USD and NOK-NZD 0.5; CHF has the lowest monthly SD (45bp). No sourced episode library: ask the user for local stress dates and build replays from data (Macrosynergy 2025) |
| Cross-market | In pronounced rally years (2002, 2008, 2010-2012) no DM market posted a negative return; years of rising yields (2006-07, 2013) preceded USD funding stress. Correlations are "circumstantial rather than structural": inflation/monetary shocks -> positive correlation; growth/financial shocks -> negative. Daily-data betas understate cross-market correlation (time-zone non-overlap); blend with weekly |

## 5. Bear-market and regime taxonomy (for choosing hypothetical shocks)
- Equity bear markets (>= 20% drawdown, since 1950s): 14 episodes, 7 at or before a recession; labels recession, deflating
  bubble, stagflation (1966, 1984, 2022), financial accident (1987, 1998) which "can rarely ever be anticipated" (Willer & Saunders 2026).
- k-means on macro variables: ~80% of data in common clusters, ~20% in risk clusters used for stress. Bond Sharpe is worst in
  tightening financial conditions (about -0.85, "most difficult cluster": stocks, bonds and credit can all sell off) and goldilocks
  (about -0.47); stagflation shows ~3.2 on only 10 observations (read from charts, approximate; Willer & Saunders 2026).
- Stock-bond correlation = 7.43 x core CPI - 0.23 (R^2 0.22): zero near 3.1% core on that fit; authors' rule of thumb 2.5%. Duration stops
  hedging equities above that.
- Seasonal windows can stall trend trades for weeks (10y core EUR yields 2004-2020: bullish January 71% hit rate, third week of June
  94%; bearish June 65%, October 76%; BNP Paribas 2021).
