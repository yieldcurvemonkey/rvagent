---
name: spread-sovereign-cds-and-basis
description: "Sovereign CDS as an RV input and as a trade. Covers the CDS-bond basis (CDS minus bond spread), the USD asset-and-basis-swapped ASW vs CDS arbitrage inequality, stripping the settlement-currency (FX/quanto) and delivery-option parts out of a sovereign CDS quote, hazard-rate and upfront conversions, CDS-equivalent bond spreads, CDS-adjusted 'risk-free' yields and PCA, cross-sovereign CDS PCA, and credit vs repo vs redenomination risk in EGB spreads. Use when asked about sovereign CDS, CDS-bond basis, negative or positive basis, negative basis trade, bond-CDS basis, asset swap vs CDS, jump-to-default hedge, ASW vs CDS, USD ASW, CDS-equivalent spread, hazard rate, upfront, quanto CDS, EUR vs USD CDS, redenomination or euro break-up risk, Italy/France/Germany/US/Japan CDS, credit-adjusted swap spreads, Treasury convenience premium, yield minus CDS, BTP or JGB curve vs CDS curve trades, debt-ceiling CDS, or whether a BTP-Bund / OAT-Bund move is credit, funding or scarcity."
---

# Sovereign CDS and the bond-CDS basis

A sovereign bond spread mixes credit, funding (repo, haircuts, balance sheet), scarcity and currency risk. Sovereign
CDS prices credit as a running premium comparable to a bond spread over USD SOFR, so it is the one market quote that isolates credit, but only
after you strip its two non-credit parts: the **FX component** (G10 sovereign CDS usually pay out in USD, and US CDS
in EUR, i.e. in a currency likely to strengthen on default) and the **delivery option** (DO). Comparing the bond,
asset-and-basis-swapped into USD SOFR, with the CDS gives a hard no-arbitrage bound (`USD ASW ≤ CDS`) and a basis
that tracks repo stress, arbitrage-capital scarcity and central-bank scarcity. Subtracting CDS from yields gives
"risk-free" curves whose PCA stays stable through credit regime shifts.

## When to use
- "Is the BTP (OAT, Bono) spread to Bunds credit, funding or scarcity?" / "is Italy's CDS-bond basis stressed?"
- "Are basis-swapped JGBs (Bunds, gilts) cheap against Japan (Germany, UK) CDS?" / any USD ASW vs CDS question.
- Credit-adjusting a swap spread or a cross-market pickup ("is the Treasury convenience premium real after CDS?").
- Choosing which sovereign CDS or tenor to buy/sell (cross-sovereign or curve PCA on CDS).
- Curve trades on yield-minus-CDS ("BTP curve too flat vs the Italy CDS curve").
- Redenomination / euro break-up, debt-limit or default-scenario checks on any trade that holds CDS.

## Conventions (state them in every output)

| Item | Convention used here |
|---|---|
| CDS spread | bp per year on notional; "par spread" = running premium with zero upfront. Standard contracts quote a fixed coupon (100 or 500bp in the Tuckman & Serrat example; 25bp is also standard for Western European sovereigns) plus an upfront in points per 100 |
| Long CDS | buying protection = paying premium = short credit. "Sell protection" ≈ long the bond |
| Denomination | currency the protection pays in. G10 sovereign CDS: usually USD; US CDS: usually EUR (Huggins & Schaller, Fixed Income Relative Value Analysis 2nd ed., Wiley 2024) |
| Bond spread | ASW in "reference rate + X" form, **positive = bond cheap**. This is the canonical `asw_*` `govt_minus_swap` sign. US `spread_*` rows are `swap_minus_govt`: flip the sign before use |
| USD ASW | spread over USD SOFR of the bond after asset swapping and cross-currency basis swapping into USD |
| Basis | `basis = CDS − bond spread` (bp). **Negative = bond cheap vs CDS**, positive = bond rich / CDS wide. The arbitrage slack is the mirror image, `slack = USD ASW − CDS ask − hurdle`: positive = tradeable |
| Adjusted CDS | the pure-credit part of a quote: `k × CDS` (k defined in Method step 1) |
| Risk-free yield | `y − CDS`, in the bond's yield convention; CDS converted to % (bp/100) |
| Recovery | 40% of par unless the contract or the user says otherwise |

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Sovereign CDS par spreads by tenor (6M–10Y, ideally 30Y), bid/ask, with contract terms | `cds_quotes` (date, snap, entity = ISO issuer code, tenor, ccy = denomination, settlement, definitions vintage, coupon_bp, par_spread_bp, ask_spread_bp, upfront_px, recovery_frac) | daily close, ≥ 3y (PCA: weekly, ≥ 3y spanning a stress episode) | Ask the data adapter if it is missing. Never proxy with an index or a bank CDS. Pick one contract per entity and tenor |
| Bond prices, yields, static | `bond_quotes`, `bond_static` | daily, same snap as CDS | maturity drives CDS interpolation |
| Asset-swap spreads (local and USD SOFR) | `swap_spreads` (`measure` asw_parpar/asw_proceeds, `ref` = instrument_id) | daily | check `sign_convention` row by row |
| Cross-currency and tenor basis | `basis_swaps` (`basis_type` xccy / tenor) | daily | needed to build USD ASW for non-USD bonds |
| Swap curves for BPV and CF | `curve_par` (OIS per currency) | daily | `CF = BPV_USD / BPV_local` at the bond's maturity |
| GC, specials, haircuts | `repo_rates` | daily, term if available | specialness and haircut cost terms |
| FX spot | `fx_rates` | daily | only for quanto / default-scenario P&L |

Schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If CDS quotes, contract terms or term
repo are missing, ask for them (or hand off to the `rv-data-engineer` agent). Never invent a CDS level, recovery or
definitions vintage.

## Method

**1. Clean the CDS quote before using it.**
- Check the contract: denomination, settlement (physical, cash, auction), credit-event list and definitions
  vintage. Sovereign credit events are failure to pay, repudiation/moratorium and restructuring (Tuckman & Serrat,
  Fixed Income Securities 4th ed., Wiley 2022). Whether **redenomination** is a credit event "depends on the
  specifications of the individual CDS agreements" (Huggins & Schaller 2024). Record what the contract says. Do not assume.
- Convert between upfront and quoted spread with a flat hazard rate λ: survival `S(t) = e^(−λt)`, fee leg =
  `s × Σ DF_i·Δt_i·(S_i + ½(S_{i−1} − S_i))`, contingent leg = `(1 − R)·Σ DF_i·(S_{i−1} − S_i)`. Spread → upfront: solve λ so the
  legs are equal at the quoted spread, then `upfront = RPV01 × (s − coupon)`. Upfront → spread: solve λ so
  `contingent − RPV01 × coupon = upfront`, then `s = contingent / RPV01`. Rule of thumb: `s ≈ λ(1 − R)`. Full
  derivation and the textbook table are in [references/cds-pricing-and-examples.md](references/cds-pricing-and-examples.md).
- **Adjusted CDS** (pure credit) `= k × CDS`, with `k = 0.45` for cash-settled and `k = 0.39` for physically settled
  contracts. The FX component is 55% of the quote, because local-currency CDS trade at 30–60% of USD CDS (midpoint
  45%). The DO adds another 6% (worth about USD 6 per 100 on Latin American defaults). The two are assumed
  independent (Huggins & Schaller 2024). This is a rule of thumb from a handful of observations. **Always run
  k_FX ∈ {0.30, 0.45, 0.60}** (minus 0.06 when physical) and keep only conclusions that hold at all three.
- The direction is certain even when the size is not: DO ≥ 0 by construction, and FX ≥ 0 if the defaulter's currency
  weakens. So **pure credit ≤ quoted CDS**. Only the inequality in step 3 relies on this.
- With a local-currency and a USD quote on the same name, the market-implied currency fall on default is
  `d = 1 − s_local / s_USD`. For example, 45bp vs 100bp gives d = 55%. This ignores the correlation of FX with
  pre-default spread moves.

**2. Put the bond on the same footing: a spread over USD SOFR.**
- `USD ASW = (local ASW + ICBS − CCBS) / CF`, where `CF = BPV_USD / BPV_local` (swap BPVs at the bond's maturity).
  CCBS is the spread on the non-USD leg against flat SOFR. ICBS converts the local ASW index to the CCBS index
  (e.g. TIBOR → TONAR). This assumes par bonds (Huggins & Schaller 2024). For a UST, USD ASW is its SOFR ASW
  directly.
- Interpolate the CDS curve linearly in years to each bond's remaining maturity. Use the **ask** for protection
  you would buy, and the ASW at the bond **offer** for bonds you would buy.
- For discount bonds or high spreads, use the CDS-equivalent spread instead: solve λ to the bond's dirty price,
  then price a par CDS at that λ. Spread measures understate risk on discount bonds: at λ = 16.7% a bond priced
  80.688 shows a 932bp bond spread against a 1,000bp CDS (Tuckman & Serrat 2022). For G10 near-par bonds, USD ASW
  is enough.

**3. The basis and the arbitrage inequality.**
- If USD ASW and CDS both priced only credit, asset & basis swap + long CDS would be riskless, so USD ASW = CDS.
  In practice `USD SOFR-ASW = adjusted CDS + specialness term (≤ 0) + haircut cost (≥ 0)`. Without specials or
  haircuts, `adjusted CDS ≤ CDS` gives **USD ASW (market) ≤ CDS (market)** (Huggins & Schaller 2024).
- `slack = USD ASW(offer) − CDS(ask) − hurdle`. The hurdle is the bid/offer of the ASW, the CCBS and the CDS legs,
  plus the haircut cost `h × (funding spread over SOFR)` (2% × 5% = 10bp in the source), plus capital. **slack > 0 is
  the only tradeable side**: buy the asset & basis-swapped bond and buy CDS protection. You earn the slack until
  default or maturity, and are long the DO and long the FX-on-default leg for free.
- `CDS − USD ASW` when positive is **headroom**, not a signal: it is how far the bond can cheapen before the bound
  binds.
- Simple repo version (Tuckman & Serrat 2022): for a par bond with matched-term repo, `basis = s − (c − r)`.
  Negative basis: buy the bond, repo it, buy protection, locking `(c − r) − s`. Positive basis: sell protection,
  short the bond, reverse it in. This needs **term repo to maturity**. Overnight repo turns the arbitrage into a
  funding bet.

**4. EGB spreads vs Bunds: split credit from funding and scarcity.**
- `EGB basis_i(T) = [CDS_i(T) − CDS_DE(T)] − [y_i(T) − y_DE(T)]`, with matched maturities, in bp. Tuckman & Serrat
  use the shortcut `CDS_i(5y) − (y_i − y_DE)(5y)`. That is fine while DE CDS is single digits (9.1bp in Nov 2021)
  and biased when it is not.
- Read the residual `(y_i − y_DE) − k·(CDS_i − CDS_DE)` at k = 1 and at the step-1 scenario k values. It is the
  part of the spread not explained by default risk: repo access, haircuts, liquidity, central-bank buying and any
  redenomination premium the CDS does not cover.
- Redenomination: if a euro bond can be repaid in a new currency without triggering the CDS, every bond-vs-CDS
  structure that is net long the bonds is **long the new currency** (in equal-notional bond + CDS packages,
  net long CDS means net long bonds). Use contracts that treat redenomination as a credit
  event, or move the trade to a non-euro market (Huggins & Schaller 2024).

**5. Statistical RV with CDS (PCA).** Use weekly levels and normalise CDS before the PCA (Credit Suisse, PCA
Unleashed, Oct 2012). Details: [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md).
- **One issuer's CDS curve:** expect one factor (Italy 2Y/5Y/10Y: PC1 = 99.5%). PC2's range is below bid/offer, so
  use the curve only to pick the tenor for a directional view, unless several tenors trade independently.
- **Cross-sovereign, same tenor:** EUR 5Y PC1 = 92%, a "fever chart". Use PC1 betas for hedge ratios (DE 10bp ↔
  FR 26bp ↔ IT 64bp, 2009–12). **Exclude bailout/programme countries** for pure RV, because their own factors are
  political and slow to revert.
- **Risk-free yields** `y − CDS`: use **unadjusted** CDS for anything you trade, so you are never under-hedged in
  default. Adjusted CDS is the better analytical proxy. Before entry, check the PC1–PC2 correlation over the recent
  sub-period; it should be near zero. Hedge ratios come from first-factor sensitivities of the bond + CDS packages.

**6. Size and default-proof the structure.**
- Jump-to-default-neutral CDS notional per bond face: `N_CDS = Face × (P_dirty/100 − R) / (1 − R)`. At par this is
  equal notional. Spread hedges use risky DV01 = `RPV01 × notional / 10,000` per bp, where RPV01 is the risky
  annuity in years; positive for the protection seller (long credit), like a long bond.
- Run the default checklist on every CDS-linked position (Huggins & Schaller 2024):
  1. **Net long CDS** is the safe side: long the DO and long the FX-on-default. Net short exposes you to both.
  2. The CDS terminates at default, but ASW and CCBS legs run on. You are left with rate and FX exposure
     after default.
  3. Repo can stop working near default.
  4. Euro redenomination (step 4).
  5. If the expected holding period, from the mean-reversion half-life, is far shorter than any plausible default
     horizon, you may model the CDS as a pure time series. Still pass the four checks above.

## Worked examples
- **Upfront convention** (Tuckman & Serrat, 2022): 5y CDS, annual pay, spread 558.92bp, coupon 500bp, R = 40%,
  DFs 0.998462…0.959797. Then λ = 9.322%, both legs = 21.995, upfront = 21.995 × (1 − 500/558.92) = **2.319 per
  100**. A 5% bond at 94.561 implies the same λ, i.e. a CDS-equivalent spread of 558.92bp. `s ≈ λ(1−R)` gives 559.3.
  The bundled script reproduces all of these.
- **JGBs vs Japan CDS** (Huggins & Schaller 2024; 23 Sep 2012, LIBOR era). The 10Y JGB 6M ASW was −1bp; adding the
  3M/6M ICBS of +12 gives 11bp. With CCBS −64.5 and CF 0.95, USD ASW = (11 + 64.5)/0.95 = **79bp**, against 10Y CDS
  ask ≈ 130 (chart-read). That leaves 51bp of headroom: no arbitrage, and much more downside than a 2Y JGB,
  whose USD ASW tracked the CDS ask closely. A Japan CDS of 100bp implies about 45bp of pure credit (ignoring the DO). Using the raw
  quote overstates the fair JGB ASW by **55bp**, so price the trade at adjusted CDS 30/45/60.
- **Credit-adjusted Treasury swap spread.** 30Y OIS 4.00%, UST 4.10% gives a swap spread of −10bp. Treasury CDS
  30bp gives a credit-adjusted yield of 3.80%, i.e. a **+20bp convenience premium** (Fleckenstein & Longstaff,
  Treasury Richness, Journal of Finance 2023). US CDS is EUR-denominated, though. Applying k = 0.39 (illustrative
  combination of the two sources) gives 11.7bp of credit, a yield of 3.983% and a premium of only **+1.7bp**. The
  verdict flips from "Treasuries 20bp rich" to "about fair", so report both.
- **Risk-free BTP 2s5s steepener** (Huggins & Schaller 2024; 26 Aug 2012). PC2 of the BTP-minus-CDS PCA was far
  from its mean, meaning the BTP curve was too flat relative to the Italy CDS curve. Buy 2Y BTP + 2Y CDS, sell 5Y BTP
  + 5Y CDS, notionals about **5:3**, for **73bp** potential. It did not show in a plain BTP PCA. The trade is net
  long CDS (safe on FX and DO) but long lira on an uncovered redenomination. The alternative was a risk-free JGB
  2s10s flattener at 47bp: it gives up 26bp but carries no redenomination risk.
- **Core EUR CDS PC2** (same source, 26 Sep 2012). On the DE/FR/NL/AT PCA, PC2 is big vs small core. Sell FR / buy
  AT CDS at **1.4 AT per FR** (PC1-neutral) for 42bp; DE or NL vs AT gives 23 / 29bp.
- **EGB basis history** (Tuckman & Serrat 2022, Fig 14.6, 5y CDS − 5y spread to DE, 2006–2021). Italy went
  significantly negative in 2009–12 (BTP-Bund > 600bp) and in the 2018 budget standoff (~300bp), as repo lenders
  pulled back from BTPs. France went positive in the crisis (OAT-Bund peak ~100bp) because OATs were hard to borrow
  and the ECB was buying. Both went somewhat negative in the COVID funding stress.

More examples (Korea 2008–09 violations, SOFR-spread curves for Bunds/USTs/gilts, Bund ESTR-ASW fair value, sovereign
5y CDS levels) are in [references/cds-pricing-and-examples.md](references/cds-pricing-and-examples.md).

## Signals & interpretation
- **slack > 0 after the hurdle** → buy asset & basis-swapped bond + buy CDS. Before the crisis, violations were
  arbitraged away at about transaction costs. Post-crisis, violations of "several dozens of bp" persist, because
  CCBS and CDS carry capital charges. The size of violations is a gauge of arbitrage-capital scarcity (Huggins & Schaller 2024),
  much as the corporate CDS-cash basis is used as a balance-sheet availability gauge (TBAC, Swap Spreads charge, Feb 2021).
- **Never trade the other side.** Do not sell CDS against a reverse-asset-swapped bond because USD ASW sits a few bp
  below adjusted CDS: the estimation error in k is larger than the edge. Do not trade spreads between two bases
  either (2Y vs 7Y of one issuer, or JGB/Japan vs UST/US).
- **What drives violations:** mostly CCBS volatility, which moves USD ASW faster than CDS. Korea in 2008–09 gave
  25–132bp violations over days to weeks (chart-read). Expect them when the CCBS gaps, not when the CDS does.
- **Two equilibria** (`USD ASW = local ASW/CF − CCBS/CF ≤ CDS`):
  - Low-risk issuers (Bunds): CDS is stable, so local-ASW moves are absorbed by the CCBS.
  - High-risk issuers (JGBs 2009–12): USD ASW mirrors the CCBS, and the correlation of 5Y Japan CDS with 5Y JGB USD
    ASW was 0.78.
  - Choose which leg to fade accordingly.
- **Basis level is not a signal.** Bases stay positive or negative for long periods. Rank on a 126-business-day (6m)
  z-score of the basis per bond and flag |z| ≥ 2, alongside 1w/1m changes and the 6m min/max (J.P. Morgan, EM US$
  Sovereign Bond-CDS Basis Report, Oct 2025). Hand the z-score to
  [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md).
- **EGB residual:**
  - Widening negative basis with rising haircuts or repo spreads is funding stress (Italy 2011, 2018). Don't fade
    it with overnight repo.
  - Positive basis during QE or heavy demand is scarcity. It mean-reverts with net supply, not with credit.
- **Structural positive bias:** banks and dealers buy sovereign protection to hedge loans and one-way-CSA derivative
  exposure (CVA). That keeps CDS wide to bonds independent of default risk (Burghardt et al., The Treasury Bond
  Basis 3rd ed., 2005; Düring, Fixed Income Trading and Risk Management, 2021).
- **US debt limit:** short-dated (6m) US CDS spikes before X-dates. A payment delay of more than 3 days is a
  potential ISDA trigger (BofA, Debt limit FAQ, May 2025). Read it as event pricing, not solvency.
- **Quanto spread:** `1 − s_EUR/s_USD` on a euro sovereign is the market's price of currency-on-default and
  redenomination. If it widens while the USD CDS is stable, break-up risk is being priced (our inference from the
  FX-component logic).
- **Cross-market pickups:** subtract the CDS differential before calling a hedged pickup cheap. The synthetic AUD
  bond built from JGBs picked up 40–120bp over ACGBs, while the JGB-ACGB USD CDS difference was only 5–30bp, so the
  pickup survived (J.P. Morgan, Drivers of cross currency basis, Mar 2015).

## G10 notes

| Market | What matters |
|---|---|
| USD | US CDS is usually EUR-denominated. Use it to credit-adjust SOFR swap spreads ([spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md)). Adjusted US/DE CDS is "at times (not always) below 10bp", so removing it may not be worth the effort. The front end reacts to debt-limit X-dates |
| EUR | USD-denominated standard. EUR-denominated CDS on Italy exists but is illiquid. 5y Nov 2021: DE 9.1, ES 35.2, IT 89.6, GR 112.3bp. EGB basis, redenomination and ECB buying dominate. In the euro crisis Bunds richened vs EURIBOR while German CDS widened: a CCBS + ICBS + CDS effect, not a fall in German credit quality (Huggins & Schaller 2024) |
| JPY | Japan CDS is USD-denominated. JPY-denominated CDS is thin, and even the sign of JPY's move on default is debatable (repatriation). The JGB USD ASW is driven by the JPY CCBS |
| GBP | Basis-swapped gilts have the steepest SOFR-spread curve (about −31bp at 1Y to +95bp at 25Y, chart-read, 17 Oct 2023). Part of that is the BoE haircut schedule, not credit, so subtract haircut cost before comparing with UK CDS |
| AUD, CAD, NZD, CHF, SEK, NOK | The sources give no liquidity data for these sovereign CDS. Confirm a two-way market and contract terms before using a quote. If there is none, use CDS only as a bound or a credit adjustment for cross-market pickups |

## Pitfalls
- **Raw CDS in a fair-value model.** It overstates sovereign credit by more than 2× (FX + DO). Using adjusted CDS
  under-hedges in default if the currency falls less than assumed. Analyse with adjusted CDS, hedge with raw.
- **Sign flips.** Canonical US `spread_*` rows are `swap_minus_govt`, so a UST USD ASW is roughly minus that value.
  Mixing them silently inverts the basis.
- **Tenor and roll.** CDS maturities fall on 20 Mar/Jun/Sep/Dec and the on-the-run contract rolls semi-annually (20 Mar, 20 Sep), so a
  generic "5Y" series jumps at rolls. Interpolate to
  the bond's maturity date and stitch constant-maturity series ([data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md)).
- **Short bonds.** Bonds under ~1Y can show USD ASW > CDS from redemption flows. The basis/CDS ratio is unstable
  when CDS is small (−329% in the J.P. Morgan screen). Suppress the ratio below 10bp of CDS.
- **Financing.** Every basis measure ignores financing risk unless repo is term. The IG CDS-bond basis went from 0
  to −250bp in 2007–09, and negative-basis traders lost heavily (Tuckman & Serrat 2022). Positive-basis trades risk
  losing the bond borrow ([stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md)).
- **Default mechanics.** Remember the post-default open legs (ASW and CCBS run on), the auction recovery and the
  CTD-style delivery. With more CDS outstanding than deliverable bonds, deliverables can trade near par.
- **Stale or quoted-only CDS.** AAA/AA sovereign CDS often trade rarely. A flat line is a missing quote, not a stable
  credit. Set `data_ok=false`, don't forward-fill.
- **PCA across a credit regime shift** on raw yields gives correlated PC1/PC2 and false "non-directional" trades.
  Use yields minus CDS (or shadow rates). Yields minus CDS are also not floored at zero, which steadies short-end
  loadings near the lower bound.
- **Unknown redenomination coverage** in a euro bond-vs-CDS trade is an open currency position. Size it as one.

## Output
1. **Basis table**, one row per bond. Columns:
   - issuer, instrument_id, maturity
   - CDS mid/ask (tenor-interpolated, denomination, settlement, definitions vintage)
   - k used, adjusted CDS
   - local ASW, CCBS, ICBS, CF, USD ASW
   - basis = CDS − USD ASW, slack and hurdle
   - basis z (126d), 1w/1m change, 6m min/max, basis/CDS ratio
   - risk-free yield. Sort by slack, then by z.
2. **Charts:**
   - per issuer, USD ASW vs maturity with the CDS ask curve overlaid
   - basis history with ±2σ bands
   - for EGBs, spread to Bunds split into the k·CDS part and the residual.
3. **Trade proposal:**
   - legs and notionals (JTD-neutral or PC1-neutral), and expected pickup in bp/yr after the hurdle
   - the k = 0.30/0.45/0.60 scenario table
   - the default checklist (net CDS sign, FX, DO, repo, redenomination)
   - holding horizon vs half-life
   - Pass it to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), and to
     [rv-devils-advocate](../rv-devils-advocate/SKILL.md) for anything net short CDS.

## Scripts
- [`scripts/sov_cds_basis.py`](scripts/sov_cds_basis.py) has three parts:
  - pricing: hazard rate and upfront from spread, spread from upfront, bond price under a hazard rate, CDS-equivalent spread
  - adjustments: adjusted CDS, USD ASW, quanto-implied FX move on default, JTD-neutral notional
  - screen: per-bond basis, inequality slack and z-score.
- CLI: `python scripts/sov_cds_basis.py --cds cds_quotes.csv --asw swap_spreads.csv --bonds bond_static.csv --cost-bp 15`.
  The ASW rows must already be in USD SOFR terms (`curve_id` USD-SOFR), one `--measure` (default `asw_parpar`), one
  snap, and one CDS contract per entity/tenor (it stops on duplicates rather than mixing them). Use `usd_asw()` to convert local ASW first.
- `--selftest` reproduces the Tuckman-Serrat hazard, upfront (both directions) and CDS-equivalent tables, the
  Huggins-Schaller JGB USD ASW, and checks the screen and the CDS-to-bond-maturity join on synthetic data.

## Related skills
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): ASW measures; adjusted CDS as the credit term in swap-spread fair value
- [xccy-basis](../xccy-basis/SKILL.md): CCBS levels and drivers that move USD ASW
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): EGB spreads, betas and FX-hedged pickups that this skill credit-adjusts
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA mechanics for CDS curves and risk-free yields
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): specialness, term repo, haircuts
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): capital hurdle for ASW-CDS arbitrage
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CVA hedging demand for sovereign protection
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): bond-level rich/cheap after credit is removed
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md), [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): basis z-scores, half-lives
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): debt-limit, election and budget events
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): default and redenomination scenarios
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), [rv-devils-advocate](../rv-devils-advocate/SKILL.md): write-up and challenge
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): fiscal supply and term premium.

## References
- Huggins & Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024), Ch.12, 13, 16, 17: adjusted CDS (0.45/0.39), FX component and DO, USD ASW formula, the ASW ≤ CDS inequality, CDS and risk-free-yield PCA, JGB/BTP/core-EUR/Korea cases, redenomination, SOFR-spread curves
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets, 4th ed. (Wiley, 2022), Ch.14: hazard-rate CDS pricing, upfront convention, CDS-equivalent spread, CDS-bond basis with repo, Italy/France sovereign basis 2006–2021, sovereign 5y CDS levels, auctions
- Fleckenstein & Longstaff - Treasury Richness (Journal of Finance, accepted manuscript, 2023): CDS-adjusted Treasury convenience premium vs swap spreads
- J.P. Morgan EM Strategy (Poojary, Chawla) - EM US$ Sovereign Bond-CDS Basis Report (22 Oct 2025): basis definition vs par-equivalent spread, screen layout, z-score, "level is not a signal"
- J.P. Morgan Credit Research (Beinstein) - HG and HY CDS Bond Basis Reports (22 Oct 2025): basis = CDS − bond spread sign convention, basis-to-spread ratio instability
- BofA Global Research (Cabana, Craig, Axel) - US Rates Viewpoint: Debt limit FAQ, spring 2025 update (12 May 2025): US CDS around X-dates, 3-day payment-delay trigger
- Treasury Borrowing Advisory Committee - Charge: Swap Spreads (Feb 2021): CDS-cash basis as a balance-sheet availability gauge
- J.P. Morgan Global Rates Strategy (Bassi et al.) - Drivers of cross currency basis in EUR, GBP, JPY, AUD & CHF (11 Mar 2015): bank-CDS link to EUR/USD basis, CDS-differential check on the JGB-to-AUD pickup
- Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): sovereign one-way CSAs hedged with sovereign CDS
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis, 3rd ed. (McGraw-Hill, 2005): synthetic corporates; CDS wide to bonds on bank hedging
- Credit Suisse Fixed Income Research (Pelata, Giannopoulos, Haworth) - PCA Unleashed (24 Oct 2012): PCA algorithm, normalising CDS inputs
- Fontana & Scheicher - An analysis of euro area sovereign CDS and their relation with government bonds (Journal of Banking & Finance, 2016) (external): euro-area sovereign basis evidence cited by Tuckman & Serrat
- ISDA - 2014 Credit Derivatives Definitions (external): credit events, deliverables and the euro redenomination language to check per contract
