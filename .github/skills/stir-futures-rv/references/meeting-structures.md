# Meeting-dated structures inside the futures strip

Loaded from [SKILL.md](../SKILL.md). Probabilities and "what is priced in" belong to
[stir-policy-pricing-whats-priced-in](../../stir-policy-pricing-whats-priced-in/SKILL.md); this file covers how
policy-meeting timing, turns and averaging rules change the futures structures you trade.

## 1. Jump sensitivities and meeting-neutral hedges
- SR1 jump sensitivity to a hike h effective after the meeting = `h × (calendar days in month on/after the effective date) / (days in month)`.
  25bp on 4-May-2022 (effective 5 May): May SR1 moves 25 × 27/31 = 21.8bp.
- SR3 jump sensitivity: bump the post-meeting daily fixings and reprice (depends slightly on level via compounding).
  Same meeting: Mar-22 SR3 (16 Mar-15 Jun, 91 days) moves 25 × 41/91 = 11.3bp (Huggins & Schaller, SOFR Futures and Options, 2022).
- Two-step hedge of one SR3 with two SR1s: `n_late = s_j / ((d_post/d_total) × 41.67)` neutralises the jump;
  `n_early = s_l/41.67 − n_late` neutralises the level (s_l = USD 25.0 per bp level shift, s_j = SR3 USD per bp jump).
  Result per 10 SR3: **2.9 Apr + 3.1 May SR1** vs the CME standard 3 + 3. For Sep-2018 SR3 (meetings 26 Sep and 8 Nov)
  the book finds 2.24 Oct + 3.79 Nov per 10 SR3. `sr1_hedge_for_sr3` reproduces the first case (selftest).
- The 3+3:10 ratio is not meeting-neutral when the meeting is off-centre; a meeting after the SR1 months cannot be hedged
  with them at all. Avoid contracts with few post-meeting days in a sensitivity-matrix hedge (their ratios explode) and
  always include an SR3. Hedge ratios for averaging contracts: full month N = notional × days/($5m × 30); over a month
  they are constant from an in-month start to month-end.
- Meeting-date "stacking" (Tuckman & Serrat, 4th ed., 2022): if exposure in early month M is set before M's meeting,
  month-M futures embed post-meeting expectations → basis risk; hedge with the prior month's contract, then roll.
- Size meeting trades by CB01 (sensitivity to the specific meeting), not DV01: DV01 sizing overstated RBA meeting risk by 244%
  (Lehman Brothers, The Short-End of the Curve, 10 Jul 2007).

## 2. SR1-SR3 fair value (no basis, only slope and compounding)
Fair CME-convention spread (avg SR1 price − SR3 price) for Sep-22 SR3 vs Oct and Nov SR1, SOFR level at quarter start /
in-quarter drift, bp (Huggins & Schaller, 2022): level 0: drift +25 → 1.33, +50 → 2.67; level 100: −50 → −2.59, −25 → −1.24,
0 → 0.12, +25 → 1.49, +50 → 2.85; level 500: −50 → 0.15, 0 → 3.11, +50 → 6.09. `fair_sr1_sr3_bp` reproduces them to <0.07bp.
A hypothetical 50bp hike on 1-Dec-2022 (outside SR1 coverage, inside the SR3 quarter) → fair spread 12bp. Use it as a capital-efficient
way to trade Fed timing; compounding adds ~3bp at 5% constant SOFR (0 at zero).

## 3. Flies are partly calendar artefacts
Meetings fall unevenly relative to the IMM grid, so a fly of three consecutive SR3s mixes strip shape with meeting count.
- Weight matrix `W[i, m]` = share of contract i's reference days at the post-meeting-m rate (`meeting_weights`). Effective
  meeting count `M_i = Σ_m W[i, m]`. Fly loading to meeting m: `Φ_m = Σ_j w_j W[leg_j, m]`.
- Smooth-policy null: minimise `||base + W δ − r||² + λ ||D₂ δ||²` over per-meeting steps δ (λ = 10, D₂ second difference
  across meetings). As λ → ∞ it is constant policy acceleration, "the policy path is smooth and the calendar is not". The
  per-contract residual is the structure signal.
- Calendar-tilted fly (no fitting): wing split follows the meeting counts, weights (−(1−t), 2, −(1+t)) sum to zero,
  `t = ((M_belly − M_front) − (M_back − M_belly)) / (M_back − M_front)`, floor on the denominator 0.5, |t| ≤ 0.35.
  Typical tilt ±0.034 (sd(φ) ≈ 0.135, dM ≈ 4). It is exactly zero when the curve is linear in meeting count (`calendar_tilted_fly_bp`).
  Use before calling a kink; if the tilted fly still shows the dislocation it is not a calendar effect.
- Peak-rate tracker: for each date, the contract with the highest implied rate in the front-N strip (rolling as contracts
  expire); record migrations. Shows where the strip prices the cycle peak and when that moves.

## 4. Meeting flies and fading a meeting premium
- Front-meeting selling pressure filters through to later meetings (Citi S&T, Short End $waps: Fading the July Premium, 23 Jul 2026):
  shorts in Jul/Sep/Dec meeting flies and SR3 Sep-26/Sep-27 steepeners work even if near-meeting pricing resurges. Underweight the paid
  near leg (0.5×2×1 vs 1×2×1) for less front-meeting exposure; the front leg carries more directional delta.
- A meeting is priced hawkishly beyond what the CB can plausibly validate → reaction risk is dovish (Citi S&T, STIRT Weekly: Beam me up,
  Scotty, 21 Aug 2026). A CB is less likely to start a hiking cycle at a non-forecast meeting; cuts can come intra-meeting.
- Forecast-meeting odds: RBA SoMP months carry 61%/4 = 15.3% of hikes per month vs 39%/7 = 5.6% for others (2.7:1, quoted as ~3:1); ECB 45%/4 = 11.25%
  vs 55%/8 = 6.9% (at worst 1.6:1). If 10bp is priced per quarter, no single ECB meeting spread should be flatter than ~2.75bp
  (swapsball.net, Central bank decisions and inflation forecasts, 8 Mar 2018). Non-forecast spreads often trade flatter than the odds.
- Cumulative-pricing logic: for a CB loath to move back-to-back (BoJ) judge Sep+Oct totals (Citi S&T, STIRT Weekly, 7/14 Aug 2026).
- Rule of thumb (hiking cycles): forwards "struggle to price more than 70-80% of eventual hikes" so futures shorts have limited upside (J.P. Morgan,
  Interest Rate Derivatives: The long and short of it, 3 Aug 2018). Negative implied probabilities are basis noise.

## 5. FF futures: FOMC steps vs a year-end premium
Monthly FF futures average daily rates. With FOMC effective 12 Dec (11 days pre) and 30 Jan (29 days pre), ΔDec, ΔJan the steps and YE
the excess over 12-31 Dec vs early Jan (Citi Research, US Rates Weekly: Fixing the plumbing, 30 Sep 2019):
```
FF_Dec = (11/31)·FF_Nov + (20/31)·(FF_Nov + ΔDec + YE)
FF_Jan = (29/31)·(FF_Nov + ΔDec) + (2/31)·(FF_Nov + ΔDec + ΔJan)
FF_Feb = FF_Nov + ΔDec + ΔJan
ΔDec = −FF_Nov + (31/29)FF_Jan − (2/29)FF_Feb      ΔJan = −(31/29)FF_Jan + (31/29)FF_Feb
YE   = −(11/20)FF_Nov + (31/20)FF_Dec − (31/29)FF_Jan + (2/29)FF_Feb
```
Verified: bumping ΔDec or ΔJan leaves YE unchanged; `ff_decompose` solves the system for any meeting day. The YE weights are a
package with year-end exposure and no FOMC exposure; the 27 Sep 2019 trade was sell FF Nov, buy Dec, sell Jan, buy Feb at DV01 −55k/155k/−106k/7k
(printed counts −1375/3875/−2672/172 imply ~USD 40/bp per contract; at the 41.67/bp FF BPV the same DV01s are −1320/3720/−2565/166 contracts, so size from DV01) for 100k YE DV01. Entry level 4.5bp, target 1.5bp, stop 6bp; the market-implied year-end drop in FF was −4.5bp vs a largest realised −2.65bp (a fade of the premium).

## 6. Turns: strip them before reading policy
- Year-end turn = forward from the last day of the year to the first of the next minus neighbouring o/n rates; always positive in repo,
  size differs by market (Japan turn 1 April). Priced customarily but "rarely realised" (Lehman, 2007); December contracts trade cheap
  to neighbours; the year-end basis "tends to overprice tightness in advance and then sell off" (Conks, Plumbing Notes: Swifter Injections, 4 Dec 2025).
- Severity ordering year-end > quarter-end > month-end (Conks, The Great Flattening, 4 Aug 2024). Turn spike scales with base tightness: use the
  ex-month-end average spread plus net supply, not a fixed historical premium (Federal Reserve Board, FEDS Notes: What Happens on Quarter-Ends
  in the Repo Market, 6 Jun 2025: SOFR-ON RRP +7bp at Mar-2023 quarter-end, up to +25bp Sep-2024 and year-end 2024, base 3-5bp otherwise).
- A transient one-day turn is nearly invisible in a 3m term rate (1 of ~65 fixings). Extract turns jointly with the baseline from
  futures spreads (vary baseline per quarter plus month-end/quarter-end turns, fit CME 1m/3m spread payouts; J.P. Morgan, What does the SRF mean for
  swap spreads?, 12 Jul 2019). SEK: the STIBOR year-end turn was large when first in effect but faded before January expiry while the o/n turn persisted.
- Turn premia in EUR, JPY, CAD were at multi-year tights in 2026 before G-SIB surcharge reform (Citi Markets STIRT Weekly, 14 Aug 2026).

## 7. Step-curve fitting for the short end
- Fit, do not bootstrap: build SOFR curves by least squares with a butterfly smoothness penalty unless a contract must reprice exactly.
  Step-fit residuals are not arbitrage. Step nodes on CB effective dates, not announcement dates; only the first ~6 months after the as-of date
  need steps (FOMC dates known ~6m ahead), beyond that use Nelson-Siegel/Svensson-type hybrids or splines.
- Heitfield-Park (Fed Board, FEDS 2019-014): `f(t) = θ0 + Σ θ_k 1{t > M(k)}`, estimator on the 7 listed 1m and nearest 3 3m futures,
  tiny ridge λ, gradualism (choose the path minimising the largest single jump). 10 Aug 2018: ~80% hike on 19 Sep, ~50% on 12 Dec (both happened).
  Term SOFR minus FF OIS 1m/3m/6m means 1.6/1.7/1.6bp (Jun 2018-Jan 2019); FF-futures term minus realised compounded EFFR 3m mean 4.4bp (2000-19).
- Strip length: choose 8 contracts (small markets) or 12 (liquid) so the strip always ends just past 2Y or 3Y; 6, 7, 10, 11, 14 are the worst choices
  (roll leverage). Static knots at IMM dates avoid ~0.25bp spurious drift of forward spreads (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022, ch.12).
- Do not mix 1m and 3m SOFR futures naively in one bootstrap: 1m-implied zeros sit ½-⅙bp above 3m-implied zeros and the 1m uses an arithmetic average, not a cutoff-day OIS
  convention (Deriscope, SOFR curve in Excel, 18 Feb 2024). Back-contract noise and SR1 errors of 3-6 cents in 7th-13th contracts are normal.
- Hedges built from a strip assume jumps at contract dates; they fail when the swap's end and the strip's end straddle an FOMC date.
  Fed-delay scenario: rolling the curve forward 6 weeks costs a 18m receiver ~14bp (Darbyshire, Coding Interest Rates, c.2024).

## 8. Event studies
- Final-hike study (Citi Research, US Rates Weekly: Time for moderation, 17 Feb 2023; five cycles, ED proxy): "After the final rate hike the curve
  reaction generally flips with shorter-dated contracts flattening and longer-dated contracts steepening." Rolling adjacent-contract steepeners entered 3m before the final hike: Sharpe 0.92 (80% hit) on the 1st/2nd contracts, fading to −1.2..−1.5 by the 6th-8th;
  entered on the final-hike day and held 3m: −2.49 (0%) on 1st/2nd, turning positive from the 5th/6th (0.12) and 0.93 at 7th/8th (column alignment reconstructed by the note-taker). n = 5, hit rates in 20% steps, final hike known only ex post.
- 6th-minus-1st fed funds future spread < −12.5bp (≥ 50% of a cut priced 6m out) historically preceded cuts or at least no hikes within 6m; failed in Mar-2023 (inflation > 5%); fewer than 25 events (Willer &
  Saunders, Trading Global Macro Markets, 2026). 1s2s is nearly uncorrelated with other segments (−0.17 to 0.01).
