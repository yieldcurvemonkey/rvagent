---
name: spread-ccp-basis
description: Analyse and trade the CCP basis, the fixed-rate gap between the same swap cleared at two clearing houses (CME vs LCH in USD, Eurex vs LCH in EUR, JSCC vs LCH in JPY). Covers sign conventions, the drivers (futures-netting demand, double initial margin, concentration charges, balance sheet), the fair-value band and MVA model, personal breakeven for a CCP switch / basis "arbitrage", term-structure and forward basis, factor fair-value regression with residual z-score, positioning read-across, split-book basis risk, and which CCP curve to use for convexity adjustments. Use when someone asks about CME-LCH basis, LCH-CME spread, CCP basis, clearing house basis, Eurex-LCH or JSCC-LCH basis, CCP switch trade, basis switch, margin-driven swap pricing, IM optimisation, cross-margining, or "which CCP is this swap curve on".
---

# CCP basis (CME-LCH, Eurex-LCH, JSCC-LCH)

The same par swap (same index, tenor, start) clears at different rates at different CCPs. The gap is not a collateral
(CSA) difference: all CCPs use the same cash/RFR-remunerated terms. It exists because the *cost of carrying* a position
differs by CCP (initial margin methodology, concentration charges, netting against futures, default fund, capital) and
because client flow is one-sided at one CCP while dealers hold risk at the other. It is a positioning/funding spread
bounded by those costs, not a quick-convergence arbitrage. Use it as (a) a trade in its own right, (b) a positioning and
balance-sheet indicator, (c) a correction to convexity-adjustment and swap-spread work: always know which CCP curve a
number is measured on.

## When to use
- "Where is CME-LCH / Eurex-LCH / JSCC-LCH, is it rich or cheap, why did it move?"
- Pricing or choosing between clearing venues for a swap, or a CCP switch trade (receive at one CCP, pay at the other).
- A DV01-flat dealer book with offsetting CME and LCH positions: basis risk and margin.
- Reading the basis as a short-positioning gauge, or checking whether a futures-vs-swap or swap-spread signal is
  contaminated by the clearing venue.
- Event risk: discounting/PAI changes, IM rule changes, cross-margining launches, CCP operational events.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Basis by tenor and CCP pair | `ccp_basis` | daily, tenors 1Y-30Y (benchmark tenors only), >= 3y | stored `basis_bp = 100 x (rate_a_pct - rate_b_pct)`; default orientation LCH minus CME, **the opposite of the market quote**; normalise first |
| Par swap rates per CCP, or LCH + basis | `curve_par` | daily | each CCP needs its own curve; LCH is the reference |
| Dealer funding / repo spreads (fair-value regression) | `repo_rates`, `macro_series` | daily | SOFR minus EFFR, SOFR minus an overnight bank funding rate, BBB corporate OAS |
| Futures and swap rates (CA work, positioning) | `fut_quotes`, `stir_quotes`, `positioning` | daily / weekly | speculative net positions normalised by open interest |
| Swap trade prints with venue and CCP label | `flows_trades` | intraday, T+1 | needed only to detect switch trades |
| Margin (IM) projections, fees, funding spread | user / desk input | per trade | no public source; these set the personal breakeven |

If an input is missing, ask for it or hand off to the data adapter (see [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)). Never invent IM, fee or funding numbers; if the user gives none, show the breakeven as a function of the funding spread instead.

## Method

### 1. Conventions (state them on every output)
- `basis_bp = rate(other CCP) - rate(LCH)`, same index/tenor/start, in bp. Positive = paying fixed is dearer at the other
  CCP; to earn it, **pay fixed at LCH and receive fixed at the other CCP**. USD market quote CME-LCH is positive in most
  history; Eurex-LCH positive; JSCC is often quoted LCH-JSCC (the ECB paper uses JSCC-LCH, negative = oversupply of
  receivers at JSCC).
- Flip the stored sign when `ccp_a = LCH` (stored LCH minus CME -> CME minus LCH = -stored). `scripts/ccp_basis.py normalise`
  does this and tags `sign_convention` (e.g. `CME_minus_LCH`).
- Position MTM: receive at CME / pay at LCH (earns the basis, "long carry") has `PV = DV01 x (basis_entry - basis_now)`;
  each +1bp of widening costs one DV01 on that leg pair. A dealer net receiver at CME and net payer at LCH is short the
  basis in exactly this sense. The DV01 is the PVBP of the leg (currency per bp, positive for receive fixed).
- Quote on the LCH curve unless told otherwise. LCH is the "source of truth" for forecast RFR fixings (largest volume;
  other CCP prices carry cost-of-capital and execution-charge biases): build one curve per CCP, price each cleared trade
  on its own CCP curve, and generic/non-cleared trades on the LCH curve.
- Per-CCP implied inputs: `par_CCPx = par_LCH + basis_bp/100` (in %). (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022, Ex 6.1.)

### 2. Mechanism: what sets the sign and the size
- **Sign = who is forced where.** USD: asset managers and mortgage-hedging banks pay fixed and net the swap against
  Treasury/Eurodollar futures margin at CME; dealers receive from them, hedge by paying at LCH where their legacy book and
  netting pool sit, and so hold IM at both. CME fixed rates sit above LCH. EUR: buy side and insurers pay fixed at Eurex.
  JPY: the regulator pushes onshore flow to JSCC (domestic banks received to hedge loan books pre-2018, so JSCC-LCH was
  negative; it turned positive in early 2024).
- **Size = cost of carrying the imbalance:** IM model (netting, anti-procyclicality), concentration charges (super-linear in
  net risk relative to daily executable volume), cross-margining offsets, collateral haircuts, funding cost / rate level,
  balance-sheet capacity and default-fund contributions. Low rates and cheap funding compress it; hikes and dear funding widen it.
- A dealer that hedges a client trade at the other CCP holds two directional portfolios: IM at both (zero netting) vs ~0
  if everything sat in one house; for a $25m 30Y that is $5.5m vs $0 (Clarus, CME-LCH Basis Spread, 20 May 2015).
  Putting USD swaps on one CCP would cut dealer IM by more than 60% (JPM, The law of one price..., 20 May 2016).
- **It is flow, not IM level.** The IM-only test showed CME pay-fixed needs *less* IM than LCH pay-fixed, so IM level
  alone does not explain a higher CME rate; the one-way flow does (Clarus, 20 May 2015).

### 3. Fair-value band (tug of war)
- Upper bound: the most the client values the margin saving of clearing a pay-fixed swap against PVBP-weighted Treasury
  futures at the same CCP (freed cash earns a higher yield). Lower bound: the dealer's cost of funding IM at two CCPs for
  offsetting trades (5y holding horizon, normal collateral funding). The basis can sit away from "fair" for years. (JPM, 20 May 2016)
- **MVA model of the dealer's price** (use for a point estimate on a given book):
  1. Take the dealer's current CCP portfolios (IM is portfolio-specific).
  2. Compute incremental IM at each CCP from the hedged client trade (it can exceed standalone IM: CCPs add liquidity
     charges for large positions).
  3. Project the incremental IM forward as the trade ages (it tapers to about 0 at maturity).
  4. `MVA = sum_t IM_t x s x dt`, with `s` = dealer cost of funds minus the CCP's remuneration (e.g. FF + 20bp, cash earns FF).
  5. `basis_bp = MVA / DV01` (DV01 in currency per bp). `scripts/ccp_basis.py mva_bp`. DV01 is a *discounted* annuity, so
     discount the `IM_t x s x dt` terms too (`dfs`); undiscounted, a 30Y overstates the basis by about a fifth.
- Every firm has its own fair value and breakeven because its book changes the incremental IM: some have a natural axe.
- Client side: the CME-LCH spread was often larger than the CVA charge for single-A and BBB credits, so clients on the wrong
  side were overcharged, in some cases by more than 2x (JPM, 20 May 2016).
- Margin-netting value: clearing long Treasury futures against PVBP-weighted pay swaps at one CCP saves 43% of IM for TY
  alone and about 70% for a bond-index-replication portfolio vs separate venues (JPM, 20 May 2016; the 43/70 mapping is read
  from chart labels, so approximate). Vendor-sponsored
  portfolio-margining maxima (SOFR futures vs swaps up to 78%, UST futures 50-65%, cross-currency 41-50%) are hypothetical
  upper bounds; real offsets are smaller (Coalition Greenwich, Portfolio Margining Imperative, Q4 2024).

### 4. Can I harvest it? Personal breakeven for a switch/"arbitrage"
Trade: pay at LCH, receive at CME, same tenor/size. Floating legs offset; day-1 MTM is zero at mid on each CCP's own curve;
the only income is `basis_bp x notional x 1e-4` per year (PV = `basis_bp x DV01`, DV01 already contains the annuity). Breakeven basis solves `PV(basis income) = PV(fees + funded IM)`:

```
breakeven_bp = sum_t DF_t x (fees_t + IM_t x s_t) / ( notional x 1e-4 x sum_t DF_t )     # annual accrual
```
- `IM_t`: forecast IM at both CCPs for each year of the trade (a step function that decays with the tenor); this is the
  dominant input ("how your margin behaves over time").
- Fees per year: SEF execution (the basis market sits on inter-dealer brokers, so a client may leg in and cross two
  spreads), DCO booking and maintenance, FCM booking and maintenance (10-100bp of IM p.a. plus monthly minimums).
- Ignore VM (it only moves between winners and losers, compensated by price alignment interest).
- `s_t` is the net funding spread (your cost minus CCP remuneration). The Clarus example below funds IM at all-in 1y-forward
  rates (0.5% rising to 2.8%) with no remuneration offset, so its 3.93bp is on the high side.
- Rule of thumb: a basis of roughly 4bp or more is needed for the arbitrage to be economical (lower when funding is
  cheap, as at Eurex before 2022); below it treat the basis as structural, not as a mispricing (Boudiaf, Kretschmann,
  Scheicher, SUERF Policy Brief 940, Jul 2024).
- Scale: every cost scales at least linearly with size and CCP IM add-ons are super-linear, so more size makes it worse.

Reasons a firm may not do the pay-LCH / receive-CME venue trade (Clarus, 20 May 2015): it can clear at only one CCP; its
existing book has lower risk or margin at the other CCP, offsetting the worse price; futures cross-margining, which only CME
offers; the trade is small; a market maker must quote its client.

**Dealer switch (reduce a split book):** pay at the CCP where you are a net receiver (CME) and receive at the other (LCH),
same tenor. Net DV01 is unchanged; gross DV01 and IM fall at both CCPs; brokerage is paid on one leg.
```
cost    = basis_bp x DV01 (+ bid/offer ~0.25bp)
benefit = IM_released x funding_spread x annuity x 0.5   (0.5: IM amortises roughly linearly)
          + IM_released x 8% default-fund ratio x 10% equity cost
```
The 8% x 10% term is an annual capital cost (our observation: the article books it once, as a crude estimate), so for a
like-for-like horizon scale it by the annuity x 0.5 (`df_years`).
`scripts/ccp_basis.py switch_benefit`. After a CCP moves to a CCP-specific marking curve, the day-1 switch MTM goes to
zero (not minus the basis), so check how each leg is marked.

### 5. Term structure, forwards and carry
- Use benchmark tenors only (1,2,3,4,5,7,10,15,20,30Y); drop thinly traded 6,12,25Y points, which add peaks and troughs.
- Typical USD shape: rises monotonically with tenor (2017: 0.10bp at 1Y to 3.55bp at 50Y). Heuristic reading (not from a
  source): front-end humps look positioning-driven, the long-end slope looks like IM cost per unit DV01 rising with tenor.
- Single-curve forward basis between `t1` and `t2` from spot bases `b1, b2` and flat-rate annuities `A1, A2`:
  `fwd(t1,t2) = (b2 x A2 - b1 x A1) / (A2 - A1)` (`forward_basis`). An upward-sloping forward basis means the market does not
  expect reversion to zero (unlike Libor-OIS in 2008/9). Annuity: `A(T) = (1 - (1+r)^-T) / r`. Check: at r = 0, 5y 1.85 and
  10y 2.30 give 5y5y = 2.75bp (the article's curve read 2.9).
- Humps are positioning: in May 2015 the 4y point had the largest one-week widening (+0.75bp), consistent with many ~4y
  payers. A belly (about 10y) cheap vs the wings means less payer interest there.
- Roll-down is small (max about 1.1bp/yr on 1y forwards in 2015), so carry does not attract speculative capital.

### 6. Fair-value regression and signal
Per tenor, OLS (bp) of basis (y) on: swap-curve PCA scores (3 PCs of *changes*; we suggest scoring the level curve on those
loadings so regressors are levels like the basis), SOFR minus EFFR (dealer funding), SOFR minus
an overnight bank funding rate (repo funding), BBB corporate OAS (dealer credit), realised rate vol of the tenor
(20d std of daily bp changes, min periods max(10, w/2): proxy for IM cost), the rate level at that tenor, quarter-end
and year-end dummies (month in {3,6,9,12} and day >= 25; year-end: December and day >= 25). Framework after Benos, Huang,
Menkveld, Vasios, The cost of clearing fragmentation, BIS Working Paper 826 (external).
- Fit: require >= 30 observations; drop zero-variance columns. Residual z = `(resid_t - mean_{<t}) / std_{<t}` on an
  **expanding** window (min 20) so z never uses the future. `scripts/ccp_basis.py fv_regression`.
- The full-sample fit is in-sample. For a backtest refit on past data only (expanding or rolling) before computing the residual.
- Basis, funding spreads and level are persistent: daily-level OLS has autocorrelated residuals, so use HAC errors, check the
  residual is stationary (ADF, half-life) before trading its z, and never read R^2 or t-stats at face value. SOFR-based
  regressors only exist from 2018, which caps the sample; funding-spread regimes shift (re-check coefficient stability).

### 7. Positioning, flow and event reads
- **Back-end shorts gauge:** 10y CME-LCH widening = fresh payers clearing at CME. On 3m changes it was 31% correlated with
  TY speculative positioning (normalised by open interest) and 51% with 10y yield changes (Citi, Rates Focus, 16 Jan 2019).
  Useful when positioning data are delayed. Combined read: 10y basis widening plus the Eurodollar convexity adjustment
  collapsing to model = speculators entering steepeners.
- **Tightening evidence chain** (Aug 2019, Citi, US Rates Weekly, 2 Aug 2019): asset-manager net futures positions fell and the Blues convexity adjustment
  widened, concentrated in 30y: real money (structurally paying at CME) unwinding steepeners by receiving long swaps.
- **Eurex-LCH as a flow indicator:** a positive 30y basis means no Dutch/German receiving interest (Nordea, EUR Rates Flash, 5 Feb 2020).
- **Market-based mean reversion:** clients migrate to LCH as the basis widens; track CME share of volume and open interest.
- **Event list that moves it:** IM-exemption rules for bilateral SOFR swaps (hedging a 10y IRS with SOFR can cut CME IM by
  76-80%; an exemption would compress CME-LCH), cross-margining launches, CCP discounting/PAI switches (forced one-way
  re-hedging of discounting risk creates predictable flow in the basis swap), a CCP operational event (spike in
  cross-CCP vol, direction unpredictable).

### 8. Which CCP for a convexity adjustment or swap-spread signal
- Futures-vs-swap convexity adjustments look wider against LCH-cleared swaps than against CME ones. The reasons to
  measure and execute on CME: futures and swaps net for margin there, and the basis had retraced from its wides (Citi, Sell
  Blues convexity adjustments, hedged, 9 Feb 2017). Pick one CCP and state it. For a swap-curve fly hedge the CCP choice
  makes no material hedging difference.
- Implied collateral funding spread = excess CA (observed minus theoretical) / IM required for the PVBP-neutral package
  (static ~1.3% total IM for ED vs LCH FRA, IM earning FF). At a fixed funding spread excess CA should scale linearly with
  IM; comparing CME-based and LCH-based excess CA against their IM shows whether the basis is too narrow (JPM, A better way to sell vol, 3 May 2017).
- Convexity between futures and FRAs is only tradeable when the FRA clears at the futures CCP with portfolio margining;
  with split clearing the payoff shows humps from funding two lots of VM (EUR 2013: futures and FRA margin could not net and
  margin earned less than funding cost, so the convexity bias went slightly negative; Aikin, 16 Dec 2013). See [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md).

### 9. Detecting switch trades in trade data (optional)
Identify spot-starting, cleared, outright trades by tenor; exclude curves, flies, spreadovers and compressions; pair trades
with matching timestamp, size and maturity; confirm with venue reports whose mark-up shows the CCP. Without the CCP label
false positives equal true positives (24 pairs in 5y vs 12 confirmed). Strip double-counting (each trade is reported per
side; one $1bn switch is $4bn counted across CCPs and accounts) and compression trades before computing volumes or prices
(Clarus, CME-LCH Basis Spread, 20 May 2015 for the counting rule; Clarus, Identifying CCP Basis Trades in the SDR, 30 Mar 2016;
BoE SWP 580, 2016).

## Worked example
**MVA reproduces a 30Y basis** (Clarus, CME-LCH Basis For Dummies, 28 Jun 2017). Hypothetical dealer: CME IM $1,233m,
LCH $4,972m. Client pays fixed on $100m 30Y at CME (dealer receives 2.435%), dealer pays 2.40% at LCH. Incremental IM
+$10.43m at CME and +$21.21m at LCH, both tapering to about zero by 30Y. MVA at FF+20bp: CME $282,867 + LCH $443,678 =
$726,545; trade DV01 $225,000 -> CME 1.26bp + LCH 1.97bp = **3.2bp**. The article reports 1.30 + 2.10 = 3.4bp, matching
the 3.40bp screen mid of that day; the stated inputs give 3.23bp, so treat the match as approximate. Sanity check of the
engine: a linear taper from $10.43m at 20bp costs `10.43e6 x 0.002 x 15.5 = $323k` undiscounted (about $255k discounted at 2.5%) vs $283k reported, so the
reported figure sits between the two.

**Client breakeven** (Clarus, Pricing and Arbitraging the CME/LCH Basis, 22 Jun 2015): $100mm 5Y, pay LCH 1.86111%, receive
CME 1.87361% = 1.25bp = $12,500/yr. House IM about $3.87mm on day 1 decaying to about 0 at year 5; IM funding about
$181.6k over 5y; fees about $17k (the article's $45k is the $62.5k income left after fees). Breakeven basis **3.93bp** (check:
(181.6k + 17.4k) / (5 x $10k per bp) = 3.98bp undiscounted), about 3x the quote: the trade does not pay for a client.

**Dealer switch** (Clarus, Hedging the CME-LCH Basis, 26 May 2015): $1bn 5Y, receive LCH 1.65642 / pay CME 1.66842
(1.2bp give-up: 1.2 x about $450-460k DV01 = about $0.55m, which the article rounds to $0.6m). IM falls $17m at each CCP
($34m). Benefit about $391k (IM funding at 50bp, 5y, halved) + about $270k (default fund) = about $670k (source; 391 + 272 = 663) vs
about $0.55-0.6m cost; 5Y basis risk is roughly halved (+1bp costs $560k vs $1m).

More cases (EUR Eurex/LCH curve inputs and the market-maker game, switch-for-IM 2014, CA-vs-CCP trade) and level tables:
[references/worked_examples.md](references/worked_examples.md) and [references/levels_and_history.md](references/levels_and_history.md).

## Signals & interpretation
- Level vs own history: z of `basis_bp` over 252d, percentile, 3m change, 5y5y forward (`screen`). Weak because the
  structure shifts; prefer the fair-value residual z (section 6). Illustrative triggers: |z| > 2 on a tenor with a stable
  regression (rolling beta drift < 30%) is a candidate; also check the basis against the personal breakeven.
- **Wide vs breakeven:** basis > breakeven (and >= ~4bp) and funding cheap = harvestable, bound by size and balance sheet.
  Basis < breakeven = structural; do not fade it with an outright bet, express positioning views via the *change*.
- **Widening plus rising yields / payers in futures** = shorts building; **sharp tightening in 30Y** = real-money unwind or
  IM-exemption/cross-margining news. Spikes caused by policy-expectation positioning (JPY 2018-19) revert if the
  expectation does not materialise; structural components persist.
- **Basis flat while swap spreads move >15bp** (April 2025 shock, 7y) suggests cross-margining savings outweigh the basis
  cost; a re-emerging basis changes the calculation (Coalition Greenwich, Q3 2025).
- Dealer split book: basis risk = sum over tenors of CME DV01 x basis move. A widening of the basis by +1bp on a $1m 5Y
  CME DV01 costs $1m; across tenors a $7.5m loss in the 2015 example. Hedge it like a tenor/index basis (see [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md)).

## Market-specific notes (G10)
| Ccy | CCPs | Notes |
|---|---|---|
| USD | CME, LCH (LCH ~98% of USD swap volume per a competing venue's claim and about $225bn IRS margin vs about $37bn at CME in 2024; CME still had ~30% of gross notional in Mar 2020), Eurex (small) | the main CCP basis; CME above LCH; term structure rises with tenor; ~0.15bp pre-2015, ~2bp May 2015, 10y 1-4.5bp 2015-18, 30y 0.8bp Aug 2019, dipped below zero 2024, narrower and calmer in 2025 |
| EUR | LCH (majority), Eurex (~20% of notional), CME (negligible) | Eurex-LCH positive: buy side / insurers pay at Eurex; wider than CME-LCH (Ex 6.1: Eurex 0.70/1.60/2.70bp vs CME 0.10/0.20/0.35bp at 2/5/10Y); EMIR 3 active-account rule could move it either way |
| GBP | LCH nearly all | basis small (2015 quotes 0.10bp at 2y/5y to 0.20bp at 30y); matters for STIR convexity through the futures venue |
| JPY | JSCC (~70% of notional), LCH | JSCC clearing required for onshore firms; US clients cannot clear at JSCC (LSOC); "double digits" LCH-JSCC in 2018; sign driven by BoJ-expectation positioning of offshore LCH users |
| AUD, NZD | ASX (AUD), LCH | ASX restricts US-person trades; no basis levels in the source material |
| CAD, CHF, SEK, NOK | mostly LCH | no CCP-basis material in the source material; do not assume a number, request data |

## Pitfalls
- **Wrong sign.** The data store defaults to LCH minus CME; the market quote is CME minus LCH. Always label.
- **Not an arbitrage.** IM funding, fees, FCM minimums and default fund consume the quote; a CME-LCH arb has failed on
  IM financing at the broker. Concentration/IM add-ons are super-linear in size.
- **Own marking curve.** Firms marking CME swaps from CME VM statements may not see the basis in P&L; a CCP valuation-curve
  change creates a one-off VM jump (net receivers at CME lost, especially at the long end, in 2015).
- **Ignoring the venue in CA or spread work** mixes a 1-3bp venue effect into a signal; state the CCP.
- **Treating cross-margining numbers as guaranteed.** Maxima come from vendor/exchange sources; offsets vanish in stress
  and need the same FCM and either the same CCP or a cross-margin agreement. IM is pro-cyclical (margin calls and IM
  increases arrive together).
- **Event traps:** CCP discounting/PAI switches change what a spreadover screen quotes (PAI/PAA at SOFR); an auction with
  all participants on the same side gets more expensive.
- **Small-sample stats.** Traded basis-package prices in a month are few; std and z on them are unreliable. Using the
  basis price as a filter for switch detection fails when the basis is tiny (front end 0.2-0.3bp).
- **Contract terms differ by CCP** (ISDA amendment timing, Eurex 2006-definitions override, floating-rate-option and
  fee-date restrictions); the two swaps are economically identical but not legally identical. Source rulebook is dated (2021).
- **Double margining bites in stress:** a Treasury cash-futures basis margined separately at FICC and CME likely contributed
  to the March 2020 dash for cash (Yadav and Younger, 2025); by analogy a split-CCP book faces IM calls at both houses at once.
  A CCP does not provide liquidity, only default protection.
- **Dated levels.** Quote levels in the references are historical; never present them as current.

## Output
Return: (1) a table `ccy, tenor, ccp_pair, sign_convention, basis_bp, z_252d, pctile, chg_3m_bp, fwd5y5y_bp, fair_value_bp,
resid_z, breakeven_bp, data_date`; (2) a one-line verdict (structural / positioning / event-driven) with the evidence
used; (3) the trade expression if any (legs, CCPs, size in DV01, entry basis, cost = basis x DV01 + bid/offer, IM and
funding assumptions flagged as user-supplied); (4) risks (basis widening per bp = DV01, IM changes, venue/valuation-curve
changes). Hand a candidate to the trade write-up workflow in [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts
- [`scripts/ccp_basis.py`](scripts/ccp_basis.py): `normalise` (orientation), `annuity`, `forward_basis`, `breakeven_bp`,
  `switch_benefit`, `mva_bp`, `period_end_dummies`, `fv_regression` (OLS fair value + expanding residual z), `screen`
  (level/z/percentile/5y5y per tenor). `python scripts/ccp_basis.py --ccp-basis ccp_basis.csv --lookback 252`.
  `--selftest` checks analytic cases (normalise sign flip, flat/zero-rate forward, breakeven, switch and MVA arithmetic,
  recovery of known regression coefficients, no-look-ahead z).

## Related skills
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): `ccp_basis` schema and sign metadata
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CSA, margin funding and MVA/KVA concepts
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): SA-CCR, leverage ratio, capital drivers of cleared vs uncleared
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): CA depends on the clearing venue
- [stir-futures-rv](../stir-futures-rv/SKILL.md): futures-vs-swap packs and which CCP they hedge on
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap spreads move with venue and balance-sheet costs
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): hedging basis risk as an index basis
- [fi-curve-construction](../fi-curve-construction/SKILL.md): per-CCP curves, LCH as the reference
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 per CCP and tenor for basis risk
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): SOFR-EFFR and repo funding regressors, period-end effects
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): HAC errors and residual diagnostics for the fair-value fit
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): identifying switch trades in trade-repository data
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): positioning cross-checks
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score and screen conventions
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market clearing and index conventions
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): hand-off format

## References
- Clarus Financial Technology (A. Khwaja) - CME-LCH Basis Spread - 20 May 2015: definition, flow-imbalance cause, venue rule and exceptions, 30Y quotes, valuation-curve change risk
- Clarus Financial Technology (T. Skarecky) - CME-LCH Basis For Dummies - 28 Jun 2017: MVA model reproducing the 30Y basis, broker-mid term structure
- Clarus Financial Technology (T. Skarecky) - Pricing and Arbitraging the CME/LCH Basis - 22 Jun 2015: full cost stack, IM projection, 3.93bp breakeven
- Clarus Financial Technology (A. Khwaja) - Hedging the CME-LCH Basis - 26 May 2015: split-book basis risk, switch cost/benefit
- Clarus Financial Technology (A. Khwaja) - LCH-CME Switch Trades and Margin Management - 30 Jun 2014: switch for IM saving
- Clarus Financial Technology (C. Barnes) - CME-LCH Basis, What does the Term Structure tell us? - 26 May 2015: term structure, forwards, EUR/GBP quotes
- Clarus Financial Technology (C. Barnes) - CME-LCH Basis: Convexity in Eurodollar Futures - 1 Jul 2015: convexity needs CME FRA plus portfolio margining
- Clarus Financial Technology (C. Barnes) - Identifying CCP Basis Trades in the SDR - 30 Mar 2016: detection algorithm, false-positive rates, March 2016 term structure
- J.P. Morgan (J. Younger et al.) - The law of one price vs. the law of unintended consequences - 20 May 2016: fair-value band, margin-netting savings, CVA comparison, persistence
- J.P. Morgan (J. Younger et al.) - A better way to sell vol: CME-based convexity adjustments are rich - 3 May 2017: implied funding spread, sell-CA trade
- J.P. Morgan (J. Younger et al.) - Interest Rate Derivatives: The long and short of it - 3 Aug 2018: reallocation to LCH, JSCC double-digit basis
- J.P. Morgan (J. Younger et al.) - When market risk meets operational risk - 10 Mar 2020: basis under a CCP operational event
- Boudiaf, Kretschmann, Scheicher (ECB) - SUERF Policy Brief 940, Back to the basi(c)s: what is the CCP basis - Jul 2024: definition, sign and size drivers, 4bp threshold, EUR/JPY history
- Citi Research (J. Williams) - Shorts increasing? An alternative view of positioning - 16 Jan 2019: basis as a positioning proxy
- Citi Research - US Rates Weekly (17 May 2019, 2 Aug 2019, 4 Oct 2019): IM optimisation via bilateral SOFR, 30Y tightening, IM-exemption limits
- Citi Research (R. Bikbov, J. Williams) - Sell Blues convexity adjustments, hedged - 9 Feb 2017: CME vs LCH venue for CA trades
- Coalition Greenwich (S. Bruel) - The Portfolio Margining Imperative for Interest-Rate Derivatives, Q4 2024; Fixed-income cross-margin opportunities, Q3 2025: portfolio-margining maxima, 2025 basis behaviour
- Nordea Markets (J. Vainikainen) - EUR Rates Flash - 5 Feb 2020: Eurex-LCH basis as receiving-flow indicator
- J.H.M. Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): pricing window, per-CCP curves, LCH as source of truth, Ex 6.1, Ex 18.1, SA-CCR maturity factor
- CME Group (S. Dayon, D. Bawadhankar) - SOFR Discounting Transition Process for Cleared Swaps - 2 Jun 2020: discounting/PAI switch, mandatory basis-swap re-hedge
- Markets Media (S. Basar) - FMX Futures Says Margin Savings with LCH will Exceed CME - 30 Jul 2024: LCH share of USD swaps and IRS margin (a competing venue's claim)
- tpSEF Inc. - Rulebook, Appendix B: Swap Specifications - 8 May 2021: contract-term differences across CCPs, US-person restrictions at ASX and JSCC
- Clarus Financial Technology (T. Skarecky) - Swap Spreads For Dummies, The LIBOR Joke - 23 Nov 2015: CME-LCH arbitrage failed on IM financing
- Clarus Financial Technology (C. Barnes) - Spreadovers vs SOFR - 23 Sep 2020: PAI change alters broker-screen instruments
- Citi Research - US Rates Vol Lab, Sell Eurodollar convexity in Blues (8 Jan 2018) and Short Blues convexity via futures/swaps (21 Feb 2023): CME venue choice for convexity-adjustment trades
- Tuckman and Serrat - Fixed Income Securities, 4th ed. (Wiley, 2022): clearing concentration by currency
- Quantitative Finance Stack Exchange - STIR futures convexity adjustment - Jun 2025: CCP basis and venue effects in GBP/EUR convexity
- Aikin (Welcome to STIR Futures) - The disappearing convexity bias - 16 Dec 2013: cross-margining and the negative EUR convexity bias
- Bank of England Staff Working Paper 580 (Benos, Payne, Vasios) - 2016: strip double-counting and compression from CCP data
- Yadav and Younger - Central Clearing the U.S. Treasury Market, University of Chicago Law Review 92 (2025): CME-FICC cross-margining, cleared vs uncleared repo margin
- Benos, Huang, Menkveld, Vasios - The cost of clearing fragmentation, BIS Working Paper 826 (external): CME-LCH basis fair-value regression framework
