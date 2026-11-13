---
name: xccy-basis
description: 'Cross-currency (xccy) basis analysis for G10 currencies against USD. Measures the FX-implied rate versus OIS (FX-OIS, FX-SOFR, CCBS, basis swap, FX swap points, covered interest parity deviation), attributes it to drivers (net foreign assets, reserves/QT, relative swap spreads, Yankee/reverse-Yankee issuance, hedging flows, year-end G-SIB turns), builds fair-value, carry/roll and curve views, and tests FX-hedged yield pickup and basis-swapped asset-swap (USD ASW vs CDS) arbitrage. Use when asked about EURUSD, USDJPY, GBPUSD, AUDUSD basis, whether the xccy basis is cheap or rich, pay or receive basis, 1y1y SOFR/TONAR, dollar funding premium, hedged UST/Bund/JGB pickup, swapped issuance, Samurai/Yankee flows or FX swap-implied USD rates. CDS-bond arbitrage: spread-sovereign-cds-and-basis; cross-market pickup selection: spread-cross-market-govies.'
---

# Cross-currency basis (FX-implied funding spreads and hedged-return arbitrage)

The xccy basis is the spread added to the non-USD floating leg of a cross-currency swap against USD SOFR flat. It is
the price of borrowing USD through FX swaps relative to the interest differential: a negative basis means USD is at a
premium. Its level is set by structural hedging demand (net foreign assets) and moved by reserves, bank balance-sheet
dates, issuance and investor hedge flows. It matters for RV in three ways: as a tradable spread (outright, curve,
forward-start, cross vs EUR/JPY), as the hedge cost that decides whether foreign bonds are worth owning, and as the
link that keeps Bund/UST/JGB asset-swap spreads and CDS consistent.

**Conventions used here (state them in every output)**
- `basis_bp` = spread on the non-USD leg (`leg_a`) against USD SOFR flat, bp, per the `basis_swaps` table. Negative =
  USD premium = "wider"; less negative or positive = "tighter" = looser USD funding. If a source quotes on the other
  leg, swap legs and flip the sign.
- Long basis (market jargon "pay basis") gains when the basis rises (narrows). Short basis ("receive") gains when it
  falls. Jargon varies between desks: define pay/receive by the P&L sign, never by the word. P&L = (basis_now - basis_entry)
  x CB01 x direction, direction +1 for long basis.
- CB01 = USD P&L per 1bp of spread, about USD-equivalent notional x non-USD leg annuity x 0.0001 (annuity close to
  years to maturity at low rates).
- FX prices as USD per 1 unit of the non-USD currency (`fx_rates.pair` is base then quote: invert USDJPY, USDCAD and
  the other USDxxx pairs). "Sell EURUSD" in flow jargon means sell EUR spot, buy it back forward.
- Day count per leg (EUR/CHF/USD ACT/360; GBP/JPY/CAD ACT/365). AUD (3M BBSW) and NZD (90-day BKBM) legs are term bank
  bills, not overnight RFRs: do not compare them level-for-level with overnight-leg currencies without adjustment.

## When to use
- "Is the 5y EURUSD / USDJPY basis cheap?" / "pay or receive 1y1y SOFR/TONAR?" / "what is priced into the front end?"
- Hedged pickup questions: does a Japanese lifer, European or Taiwanese investor still earn more in hedged USTs, USD credit
  or JGBs than at home, and what does the hedge cost say about the flow?
- Reading FX swap points as a USD funding gauge (T/N, 1M-3M FX-OIS, quarter-end and year-end turns).
- Asset-swap trades across currencies: USD ASW of a basis-swapped Bund/JGB/Gilt, bond-vs-CDS bound, swapped issuance.
- Attributing a move (swap spreads? QT? reverse-Yankee? year-end?) or deciding which funding signal to believe.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Quoted xccy basis by pair, tenor, forward start | `basis_swaps` (`basis_type=xccy`) | daily, one snap, 3y+ (RFR-era legs only) | `spread_bp` on `leg_a` (non-USD) vs `leg_b` = USD-SOFR; note `collateral`, `mtm_reset` |
| FX spot and forwards (or points) | `fx_rates` | daily, SPOT row plus 1W-1Y with `value_date` | same snap as the OIS curves |
| OIS par rates, 1M-1Y both currencies | `curve_par` | same snap | single-payment tenors only; see `swap_conventions.fixed_freq` |
| Curve nodes, to value legs and annuities | `curve_zero` | daily | basis-adjusted non-USD discounting if you price swaps |
| Swap spreads / ASW for the driver map | `swap_spreads`, `bond_quotes`, `bond_static` | daily, 3y+ | relative US vs EGB swap spreads by tenor |
| Reserves, balance sheets, NFA, issuance counts | `macro_series` | weekly/monthly vintages | use publication timestamps, not reference dates |
| Positioning, funding gauges | `positioning`, `rate_fixings`, `repo_rates` | daily/weekly | FRA/OIS and GC/OIS proxies, SOFR-FF |
| Trade prints | `flows_trades` (`product=xccy`) | intraday | blocks are capped; size is understated |
| Bonds for hedged-pickup tests | `bond_quotes`, `fx_rates`, `curve_par` | daily | local alternative of equal duration and credit |

Canonical definitions: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If a table, a leg index or
a collateral currency is missing, ask for it. Never invent a basis level; store basis in bp with the unit in the column
name (decimal-versus-bp mistakes make a book look 10,000x too small) and carry sign, leg and collateral with the data.

## Method
1. **Pin the instrument.** Which pair, which tenor or forward start, which leg index (SOFR vs ESTR overnight, or a term
   bank bill), MTM or non-MTM, collateral currency. Post-RFR, a CCBS embeds the secured-unsecured basis once or twice: SOFR
   vs a foreign overnight rate is more negative than a Libor/Libor basis, and SOFR vs a foreign term rate more negative still
   (illustrative -20 vs -28bp for ESTR vs EURIBOR). Check which series you hold. All CCBS carry a USD leg, so a non-USD
   cross is two USD legs (EURJPY = EURUSD and USDJPY).
2. **Measure the FX-implied basis (tenors up to 1Y).** With S, F the USD-per-ccy spot and forward, d the days between
   the two value dates, r_usd and r_ccy the simple OIS rates over the same window (single-payment OIS par rates):
   `F/S = (1 + r_usd d/dc_usd) / (1 + (r_ccy + b) d/dc_ccy)`, so
   `b = [ (1 + r_usd d/dc_usd) S/F - 1 ] dc_ccy/d - r_ccy`. This is the FX-OIS basis. Reconcile to the quoted 3M basis:
   a gap above about 2bp (default, own judgement) means day count, snap, value-date or leg-index error, or a year-end/term
   bank-bill effect. Each OIS window starts at its own spot lag (GBP T+0, USD T+2): the 2-day offset is immaterial from 3M
   out but not for ON-1M or across a turn. Beyond 1Y read quoted `basis_swaps`; do not extend the simple formula (see
   [mechanics-and-pricing](references/mechanics-and-pricing.md) for the multi-period discount-factor form).
   Use [`scripts/xccy_basis.py`](scripts/xccy_basis.py).
3. **Attribute with the driver map** (tenor matters: 1Y PC1 explains about 72% of variance across EUR/GBP/JPY/AUD but 5Y
   about 93%, so the front end is domestic and the back end shares a USD factor).
   - Structural level: net foreign assets. About -4 +/- 1bp of 3M basis per +$100bn NFA; AUD and CAD sit persistently high
     to NFA, CHF, JPY and SEK low. Compare a currency with its own historical residual.
   - USD liquidity regime: reserves vs RRP/TGA/bills, QT divergence between the Fed and the ECB/BoJ, bill supply.
     A TGA rebuild widens the basis only once RRP is depleted. Hand off to
     [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md) and
     [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md).
   - Bank balance sheets: regulatory snapshot dates (G-SIB year-end, quarter-end window dressing; FX swaps shrink more than
     repo). Hand off to [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md).
   - Cross-border issuance and investor hedging: Yankee (non-US issuer in USD, swapped back) narrows; reverse-Yankee widens;
     foreign investors hedging USD assets widen, USD investors hedging foreign assets narrow; Samurai and bank offshore
     issuance widen. Pension/insurer ALM flows: [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md).
   - Relative swap spreads (EUR): 10y EUR basis = 0.64 x (US minus German 10y swap spread) + 17.79, R2 0.82 (2025); both
     spreads as swap minus bond yield (the source's US-minus-Germany 10y reading is about -39bp). Do not
     assume the link holds for JPY (weak); judge the EUR front end on reserves, not swap spreads.
   - Stress and backstops: swap lines at OIS + 25bp cap offshore USD stress "in theory"; usage clusters at period ends.
   Full coefficients and windows: [driver-models](references/driver-models.md).
4. **Value it.** Build a small fair-value regression for the pair and tenor from the drivers above (one structural, one
   liquidity, one flow variable; do not exceed three to four regressors). Defaults (own judgement): 3-5y daily window for
   structural variables, 6-12m for liquidity regressions; report coefficient signs on two sub-windows; require the residual
   to exceed about 1x the model residual standard error and the signs to agree before calling cheap or rich. Published
   R2 are 0.5-0.8 in sample and relationships switch on and off (bills vs basis decoupled while RRP drained; GBP relative
   policy R2 fell from 67% to 0; the EUR policy-differential beta changed sign). Use
   [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md) and
   [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md). Screen table per pair: 1Y and 5Y level,
   change, z = (level - mean)/SD over a stated window (positive = narrower than average), 20-day SD of daily changes
   (normal 10Y/30Y SONIA/SOFR about 0.5bp/day; spiked to 2.5-3.5bp in Apr 2025).
5. **Carry and roll.** Roll of paying a tenor-T basis over h = 0.25y is `b(T-h) - b(T)` on the interpolated curve. Carry/risk
   screen: `4 x carry_3M / (sd_daily x sqrt(252))`, with sd_daily the 1Y standard deviation of daily changes. The published
   EUR/USD exhibit (27 Mar 2015) gives 3M carry of paying 1.0 / 1.4 / 0.7 / 0.2 / -0.1bp at 3M / 1Y / 2Y / 5Y / 10Y with
   daily SD 1.2 / 0.8 / 0.7 / 0.7 / 0.7bp and annualised carry/risk 0.2 / 0.4 / 0.2 / 0.1 / 0.0 (the script reproduces the
   6M-10Y carries within 0.5bp; the 3M figure needs the overnight node, which is not in the exhibit table, so the script
   returns NaN there; carry/risk comes out of the formula above). Carry from paying is about 0 beyond 5Y; carry/risk is
   best at 6M-1Y. Only pay a forward-starting basis if it rolls down positively: the old rule that the 5y basis reverts to
   the 3m roll broke after the GFC. In policy-uncertain regimes demand a larger discount to spot on carry trades.
   (JPM, Stretched EUR/USD valuations, 27 Mar 2015; Citi, STIRT Weekly, 7 Aug 2026.) Generic carry framework:
   [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md).
6. **Test the hedged-return arbitrage** (the same drivers viewed from the investor). Hedged yield in the investor's home
   currency = asset yield + annualised (F/S - 1) at the hedge tenor (F, S in home per asset), against a local bond of equal
   duration and credit. Compute at the rolling 3M hedge and at the maturity-matched hedge; the gap is roll risk. Pickup
   scales with the policy-rate gap plus the basis. Flows follow the hedged pickup only at extremes: Japan bought USTs with a
   deeply negative hedged pickup in 2019 and 2023 (Fed cycle and capital-gain expectations dominate); use it as a boundary
   condition, not a trigger. Cross-market ranking: [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md).
7. **Basis-swapped asset swap.** `USD ASW = (ASW_foreign - CCBS) / CF`, CF = BPV_usd / BPV_foreign; ASW = bond yield minus swap
   rate (positive = bond cheap; the negative of the US swap-minus-Treasury swap spread), CCBS on the foreign leg as above. Check the CDS bound:
   `CDS >= adjusted CDS ~ USD ASW`, adjusted CDS = 0.45 x CDS (FX effect only) or 0.39 x CDS (with delivery option); run
   30/45/60% of quoted CDS. Trade only the side where USD ASW exceeds the adjusted CDS (capital permitting); the other side
   needs a hedge for currency depreciation on default. For low-risk issuers (Bunds) the CCBS absorbs local ASW volatility;
   for JGBs the USD ASW mirrors the JPY CCBS. Credit leg: [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md);
   ASW mechanics: [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md).
8. **Choose the expression and the hedge.** Outright pay or receive at a tenor, curve (1Yx1Y vs 5Yx5Y, 3s/10s), forward-start,
   or relative (1.5 : 1 : 1 JPY vs EUR and CHF by DV01). The basis curve has beta below 1 to the front end (steepens in
   widenings), so neutralise a curve trade for front-end beta. A SOFR-FF or 3M SOFR-minus-Eurodollar futures spread can stand in for the CCBS
   when only its moves matter (no principal exchange): CCBS 2Y JPY regression R2 0.51-0.67; use only for move exposure and
   re-estimate after the LIBOR cessation. Risk transforms: [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md);
   collateral choice and CSA: [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md).
9. **Time it.** Quarter-end and year-end turns are technical and revert: use them for entry timing. The turn premium is
   customarily priced but "rarely realised", and overnight often collapses on the day. Check the calendar
   ([quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md)) and G-SIB reform timing
   before holding a position through a year-end.

## Worked examples
**A. Basis-adjusted forward (Aikin, STIR Futures 2nd ed., 2012).** EUR/USD 23 Jan 2012, S = 1.2960, 92 days, EUR 1.12%,
USD 0.56%. Theoretical F = 1.2942 (-18.49 pips). With a 3m basis of -75bp:
F = 1.2960 x (1 + 0.0056 x 92/360) / (1 + (0.0112 - 0.0075) x 92/360) = 1.2966, +6 pips, the market quote. Inverting
that quote with the script gives -75bp (-74.1 from the rounded 1.2966). So the forward points were mostly basis, not rates.

**B. USD ASW of a basis-swapped JGB (Huggins & Schaller, Fixed Income RV Analysis, 2024, Libor era 23 Sep 2012).** 10Y
JGB 6M ASW -1bp plus 3M/6M basis 12bp = 11bp; CCBS -64.5bp; CF 0.95: USD ASW = (11 + 64.5)/0.95 = 79.5bp over USD Libor,
against 10Y Japan CDS about 130bp, so about 51bp of room before the unadjusted CDS is hit. Against the adjusted CDS the
bound is tighter: 0.45 x 130 = 58.5bp (0.39 x 130 = 50.7bp), so USD ASW already sits 21-29bp above it, the side worth
trading subject to capital (even at the 60% end, 78bp, the margin is only 1.5bp). In Korea in 2008-09 the USD ASW exceeded CDS
by more than 100bp at times when the KRW CCBS gapped.

**C. EUR/USD room from relative swap spreads (BofA, European Rates Watch, 27 Mar 2025).** The 10y German swap spread was
about 15bp tighter vs the US year to date. At 0.64 per bp that implies about 10bp of basis tightening; the basis had instead
widened 1bp, so about 11bp of room at 10y, about 8bp at 5y, little at 2y. A Jun 2025 forecast mapping (US-Germany spreads
2y -14 to -10, 10y -39 to -29) gave EUR about 2bp tighter at 2y and about 5bp tighter at 10y. Assumes ASW valuations stay
fixed; the front end is a reserves question.

**D. Hedged pickup (Citi, The High-Grade Beat, 19 Aug 2026).** Japanese lifers: 7-10y USD A-and-better 5.42% less a 2.68%
1y USDJPY hedge = 2.74% (10-20y: 5.83% less 2.68% = 3.15%), below the 30y JGB at 4.03%, so a negative for the foreign bid.
Europe: USD IG 7-10y 5.57% less 1.36% = 4.21% vs EUR corporates 4.04%. The hedge cost is the interest differential plus the
basis, so a 20bp basis tightening on the same differential cuts a non-USD investor's cost of hedging USD assets by about 20bp per year.

## Signals & interpretation
- Basis cheap (high) or rich (low) only after step 4: residual beyond about 1x residual standard error, stable signs, and
  the trade is not just a year-end or quarter-end effect.
- Wide basis plus wide FX-implied USD rate vs repo and unsecured funding = USD scarcity in the FX-swap market. Check where
  the T/N FX-swap-implied USD rate sits against the swap-line ceiling (OIS + 25bp): 1bp under in Nov 2025 vs 14bp under in
  Mar 2026 (Conks, Plumbing Notes, 24 Nov 2025 and 1 Mar 2026). Failing to move in a broad vol shock is information too
  (Aug 2024 yen-carry unwind: bases barely reacted).
- A move that agrees across the FX-implied measure, the quoted CCBS and a funding gauge (FRA/OIS, GC/OIS) is a USD funding
  signal; a move in one tenor or pair only is flow or an artefact.
- Direction for spot: do not read the basis as a spot FX signal. The correlation of the FX-OIS basis with spot is weak on
  average and regime-dependent (5Y EUR/USD CCBS vs spot: about 0 before 2008, 0.78-0.84 in 2009-11; the 2022 USDJPY
  basis-spot link vanished from mid-2023; Huggins and Schaller, FIRVA, 2024; JPM, 4Q24 Outlook); trade the basis as its
  own RV. Do not read USD strength as a funding shortage either: bases rallied alongside the
  dollar in Nov 2024.
- Positive carry in a hedged-pickup trade is not an edge by itself: a 30bp pickup on a 1y hedge is erased by 30bp of
  underperformance (BofA, UST RV Primer, 2 May 2022).
- Filters: volume (Jan 2020 swap-data-repository xccy volume 57% / 24% of 2019 / 2018); period-end dates for swap-line usage and turns;
  vol regime (low vol enabled tighter bases in 2026).

## G10 differences that change the answer
| Ccy | What to remember |
|---|---|
| EUR | swap-spread link (80-90% of levels), ECB vs Fed reserves/QT, Yankee narrows / reverse-Yankee widens, real-money USD hedging widens; ESTR vs SOFR, MTM, spread on EUR leg |
| JPY | structural NFA negative; lifers/banks hedge, GPIF does not; Samurai issuance and quarter-end widen; 1Y -33 and 5Y -44 on 5 Jun 2025; weak swap-spread link |
| GBP | tracks BoE reserves (about -0.1bp per GBP bn), beta 0.4-0.5 to EUR, not relative policy; BPA hedging widens the 30Y |
| CHF | very negative vs NFA; SNB balance sheet; floor about -75bp (2015) |
| CAD | high vs NFA, very volatile month-end turns; avoid paying the front end at historical tights |
| AUD | positive basis; BBSW term leg; bank offshore term issuance widens, Kangaroo narrows; pension hedge ratios a steepening risk |
| NZD | BKBM term leg; settlement cash and OMO drive short tenors |
| SEK/NOK | structural liquidity, FX-OIS about -20bp (Aug 2026); SEK stability fee |
More detail, dated levels and the published trade log: [g10-notes](references/g10-notes.md).

## Pitfalls
- Wrong orientation: pairs quoted USDxxx must be inverted; points scale is 100 for JPY, 10,000 otherwise; USDCAD spot is T+1.
  Use immediate (T+0) FX in discount-factor formulas, not screen spot.
- Mixed legs: Libor/Libor, SOFR/foreign-overnight and SOFR/foreign-term bases are different series; AUD/NZD are term legs.
  History before the RFR transition has a structural break; LIBOR-era statistics are indicative only.
- Snap mismatch between the FX forward and the OIS curve, or between pairs, contaminates FX-OIS residuals.
- Simple-rate formula applied beyond 1Y or on a coupon-paying par rate (the CAD 1Y fixed leg is not single-payment).
- Sign confusion with swap spreads: basis "tight" means looser USD funding, swap-spread "tight" (more negative) means worse
  Treasury plumbing.
- Treating a regression as stable. Betas flip sign (EUR policy differential 2024 vs 2025; peripheral beta from -20% to +30%
  in 2014). NFA drivers are slow, so short-horizon deviations are large; light-volume moves reverse.
- Papering over the principal exchange: a futures-spread proxy tracks CCBS moves, not cash flows; a hedged bond purchase
  needs the real CCBS. CCBS grow the balance sheet one for one and carry capital, margin and counterparty exposure to a
  depreciated currency on default.
- Hedge-tenor mismatch: a rolling 3M hedge earns a different pickup than a maturity-matched hedge (EA investor UST vs Bund:
  17-29bp rolling vs 24-56bp matched) and carries roll risk.
- Year-end and G-SIB effects mean a position held through year-end is a bet on the turn; reform (averaging, 10bp surcharge
  increments) would compress it.
- Basis curve beta below 1: a curve trade is also a front-end trade. Cheap-to-fair-value is not a reason to fade while
  expectations reprice; back-end basis tightening can trigger JGB asset-swap unwinds that spill into swap spreads.
- Official ceilings hold "in theory (not always in practice)": do not use the swap-line rate as a hard bound.
- CDS inputs need an FX and delivery-option haircut with wide uncertainty (30-60% of the USD quote).
- Report sizes in CB01 and DV01, not notional, and state whether quoted flows are capped block prints.

## Output
Return, per pair and tenor: (1) basis level, 1m/3m change, z over the stated window, 20d SD of changes; (2) the FX-implied
measure (<= 1Y) and its gap to the quoted basis; (3) driver attribution (structural NFA residual, liquidity regime, bank
dates, flows, relative swap spreads) with sign and approximate bp; (4) fair-value residual with model R2, residual
standard error and sub-window sign check; (5) carry, roll and carry/risk for the proposed side, CB01, and the stop and
target in bp; (6) for hedged-return ideas, hedged yield vs local bond at rolling-3M and matched hedges, and the USD ASW vs
adjusted CDS; (7) the calendar (quarter/year-end), what would change the view, and which assumptions are unverified. Include
the sign convention line. Hand a shortlist to the trade write-up
([rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md)) and invite
[rv-devils-advocate](../rv-devils-advocate/SKILL.md) review.

## Scripts
- [`scripts/xccy_basis.py`](scripts/xccy_basis.py): FX-implied basis from `fx_rates` and `curve_par` (<= 1Y; handles USDxxx
  inversion), forward from basis, USD ASW, hedged yield and basis roll. `python scripts/xccy_basis.py --help`.
  `--selftest` checks published cases (the Aikin forward, the Darbyshire overnight example, the JGB USD ASW, the EUR/USD
  carry exhibit); mutating the parity formula, a day count or the ASW sign makes it fail.

## Related skills
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): RFR indices, day counts, spot lags per currency
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): snap times, stale FX/OIS pairs
- [fi-curve-construction](../fi-curve-construction/SKILL.md): bootstrapping OIS and basis-adjusted discount curves
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CSA currency, cheapest-to-deliver collateral, cross-gamma
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): SLR/G-SIB cost behind turns
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): reserves, RRP, TGA, QT
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo, SOFR-FF, period-end funding
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bill supply and MMF demand
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): 3s6s and SOFR-FF bases that embed in the CCBS
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): relative swap spreads and ASW mechanics
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): FX-hedged cross-market carry
- [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md): CDS bound on USD ASW
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): lifers, pensions, reserve managers
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): fair-value regressions and betas
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): quarter/year-end turns
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores and screens on basis levels
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): generic carry/roll and carry-to-risk
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): CB01/DV01 transforms and hedge mapping
- [stir-futures-rv](../stir-futures-rv/SKILL.md): futures-spread proxies for basis moves
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): trade-repository volumes and block prints
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): leveraged-fund positioning regressor
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and [rv-devils-advocate](../rv-devils-advocate/SKILL.md): hand-off and review
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): geopolitical channels and fade/follow rules.

## References
- Huggins and Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): CCBS theory, post-RFR CCBS types, USD ASW = (ASW - CCBS)/CF, CDS bound, JGB/Korea/Bund cases, synthetic GBP UST package, balance-sheet view
- Huggins and Schaller - SOFR Futures and Options (Wiley, 2022): futures-spread proxy for CCBS moves, regressions, OU residuals, Term SOFR dislocations
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps, 3rd ed. (Aitch and Dee, 2022): CIP with basis, MTM vs non-MTM, FX swaps, CSA/CTD collateral, risk conventions, issuer arbitrage
- Darbyshire - Coding Interest Rates (rateslib companion, c. 2024): collateral-consistent FX forwards, MTM notional rule, FX swap points, spread solve
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed. (Harriman House, 2012): forward parity with basis, synthetic FX swaps, worked EUR/USD example
- Tuckman and Porfirio, Lehman Brothers - Interest Rate Parity, Money Market Basis Swaps, and Cross-Currency Basis Swaps (Jun 2003): basis-adjusted parity, credit decomposition of the basis
- Tuckman and Serrat - Fixed Income Securities, 4th ed. (Wiley, 2022): valuation of an xccy basis swap, collateral currency and par leg
- BofA Global Research - FX-Sofr primer (31 Oct 2023): CIRP with basis, six-driver map, reference rates, swap lines, regulatory windows, repo arbitrage
- BofA Global Research - FX-Sofr and xccy: tightening themes (3 Jun 2025) and European Rates Watch, scope for 10y EURUSD tightening (27 Mar 2025): swap-spread regression, hedged-pickup mapping
- J.P. Morgan - There is one market where USD funding stress could re-emerge (20 Feb 2020): NFA cross-section, per-currency FV, G-SIB mechanics, trades
- J.P. Morgan - Cross currency basis 2H25 Outlook (5 Jun 2025) and 4Q24 Outlook (26 Sep 2024): PCA, PC1 FV, issuance models, GBP reserves, JGB ASW decomposition, screens
- J.P. Morgan - Drivers of cross currency basis in EUR, GBP, JPY, AUD and CHF (11 Mar 2015) and Stretched EUR/USD valuations (27 Mar 2015): Libor-era models, carry/risk exhibit, issuance arbitrage
- J.P. Morgan - HKD/USD cross currency basis (18 Sep 2019) and Taiwanese demand for US fixed income in 2020 (10 Jan 2020): NFA regression, hedge-cost wedge
- Citi Research - FX Basis Quarterly: Paying the basis (again) into 2025 (13 Dec 2024): liquidity regime, swap-spread decomposition, JPY flows
- Citi Markets - STIRT Weekly (Jun 2026; 7, 14 and 21 Aug 2026) and US Rates Weekly (2 Aug 2019, 17 Feb 2023, 21 Aug and 9 Oct 2026): structural long-basis checklist, FX-OIS monitors, trade marks, hedged-pickup matrices
- J.P. Morgan - Japan Fixed Income Markets Weekly (21 Feb 2025) and Global Fixed Income Markets Weekly (21-22 Aug 2026): USD/JPY basis curve, T-bill ASW fair value, xccy-ASW unwind spillover
- J.P. Morgan - US Fixed Income Markets Weekly (13 Sep 2019; 28 Feb, 6 Mar 2020): trade marks on EUR/USD and AUD/USD basis
- Citi Research - Japan Rates Weekly (21 Aug 2026): JBIC investment-framework flows too small to move the basis
- Citi Research - The High-Grade Beat (19 Aug 2026): hedged yield comparisons for Japan, Europe, Taiwan
- BofA - UST RV Primer (2 May 2022) and US Rates Watch (10 Mar 2025): hedged pickup as carry trade, JPY-investor pickup table
- BofA - FX Intervention primer, G10 (8 Jul 2024): swap lines, FIMA repo, intervention capacity
- Conks (Monetary Mechanics, Substack) - Plumbing Notes and primers (2023-2026), Fed's Global Put Part I (16 Sep 2024): dollar-rate hierarchy, swap-line gap, sign language, stress episodes
- Willer and Saunders - Trading Global Macro Markets (Wiley, 2026): Japan hedged-flow channel, basis not a spot signal
- Barclays - US Short Interest Rate Primer (Jan 2025): G-SIB year-end risk dieting
- Clarus Financial Technology - A Voyeur's Delight: Bond Issuance and Swaps (24 Jun 2014) and Mechanics and Definitions of Carry in Swap Markets (16 Jan 2019): issuance flow sizing, carry practice
- Lehman Brothers - The Short-End of the Curve (10 Jul 2007): funding-curve bootstrap, year-end turn
- Deutsche Bank Index Quant - Interest Rate Curve Creation Process (2 Feb 2023): xccy leg conventions and snap times
