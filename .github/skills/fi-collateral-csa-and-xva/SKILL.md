---
name: fi-collateral-csa-and-xva
description: 'CSA- and collateral-aware fair value for G10 swaps, and the xVA wedge between quotes. Picks the discount curve (benchmark local-cash CSA, foreign-currency cash CSA via xccy basis, multi-currency cheapest-to-deliver collateral curve), values the poster''s collateral switch option, maps discounting risk and cross-gamma, and converts CVA, DVA, FVA (funding valuation adjustment), MVA (initial-margin funding) and capital/KVA into bp running so an RV signal is judged net of them. Use when a swap, asset-swap, xccy, SOFR/FF or CCP-basis level may reflect collateral, margin or counterparty terms; when pricing bilateral vs cleared, off-market or legacy swaps; or for CSA discounting, OIS discounting, USD CSA, multi-CSA, CTD collateral, collateral optionality, one-way CSA, uncollateralised swap, bond CSA, haircut, initial margin, IM, SIMM, MPOR, PAI, discounting switch, big bang, XVA, CVA, PFE, EE, EPE, SA-CCR, cash balance profile. Not for forward volatility agreements. CCP-basis trades: spread-ccp-basis.'
---

# Collateral, CSA and xVA in swap fair value

Screen and CCP mid prices are prices under the **benchmark CSA**: cash in the trade's own currency, zero threshold,
daily exchange, remunerated at the RFR. Any other collateral arrangement changes the discount curve. Any credit,
funding, margin or capital cost left over is charged on top as an xVA. These wedges run from a few hundredths of a bp
to several bp running, the same order as many RV signals. They explain persistent "mispricings" such as the CME-LCH
basis, and they decide whether a cross-counterparty or cross-venue price gap can be captured at all. This skill prices
the wedge, so the agent trades only the edge that remains.

## When to use
- Two quotes for the "same" swap differ: bilateral vs cleared, CME vs LCH vs Eurex vs JSCC, or dealer A vs dealer B
  with different CSAs.
- An RV signal sits in a market whose price contains collateral or margin economics: the CCP basis, SOFR/FF or other
  discounting basis, xccy basis, swap spreads and asset swaps funded with margin, or futures vs swaps (IM).
- Valuing or restructuring off-market and legacy swaps: novation, re-couponing, CSA renegotiation, unwinds.
- A non-standard CSA: foreign-currency cash, several currencies, bond collateral with haircuts, one-way CSAs
  (sovereigns, SSAs), or no CSA at all (corporates, legacy SPVs).
- Event risk from a discounting or PAI switch, such as the 2020 USD CCP "big bang", and the forced hedging flows it
  creates.
- Sizing the holding cost of a large or one-sided position through IM funding (MVA) and capital.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Local RFR discount curve per cashflow currency (= benchmark-CSA curve) | `curve_zero` | daily node DFs, 1D–50Y | e.g. `EUR-ESTR`, `USD-SOFR` |
| Cross-collateral discount curves (currency X cashflows, currency Y cash) | `curve_zero` (`curve_id` `<CCY>-CSA-<COLL>`, `collateral` = COLL) | daily | or build from the next row ([formulas](references/cross-collateral-curves.md)) |
| Xccy basis by tenor, with collateral currency | `basis_swaps` (`basis_type = xccy`, `collateral`) | daily, 3M–30Y, ≥ 1y history for vol | spread is on `leg_a` |
| Discounting / index basis (SOFR-FF, etc.) | `basis_swaps` (`basis_type = index`) | daily | for discounting-switch effects |
| CCP basis | `ccp_basis` | daily, ≥ 1y | canonical sign is **LCH − CME** |
| FX spot and forwards | `fx_rates` | daily | forward FX must be CSA-invariant |
| GC and special repo for bond collateral | `repo_rates` | daily | bond-CSA CTD and haircut funding |
| Swap conventions | `swap_conventions` | static | day count for O/N compounding; DV01 from `fi-risk-dv01-and-transforms` |
| CSA terms per netting set | `csa_terms` (user-supplied rows) | static | eligible collateral and currencies, threshold, MTA, frequency, uni- or bilateral, remuneration, haircuts, right to switch, rehypothecation |
| Counterparty PD curve (or CDS) and LGD | `cds_quotes` (`entity` = counterparty id, `recovery_frac`); otherwise user-supplied | | ask; never assume a rating |
| Own funding spreads over the RFR (borrow and lend) | none, user-supplied | | institution-specific |
| IM profile, incremental, by future date | none (CCP calculator or SIMM output) | | incremental, not standalone |
| Exposure profile EE / EPE / ENE | none (simulation, or the approximations below) | | per netting set |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent a CSA term, PD, funding
spread or IM figure.

## Method

### 1. Conventions
- **Discount at the collateral rate.** Under a perfect CSA (zero threshold and MTA, continuous margining, cash),
  `PV(t) = P_c(t,T) · E^{T}[payoff]`, where `P_c` is built from the collateral rate `r_c` (Ametrano & Bianchetti,
  SSRN, 2013). Cleared VM earns PAI at the RFR, so the RFR curve is the cleared discount curve. USD CCPs moved
  PAI and discounting from EFFR to SOFR in mid-October 2020, CME at COB 16 Oct (CME Group, SOFR Discounting
  Transition, Jun 2020).
- **Units and sign.** Express each adjustment as a PV in the trade currency, from the pricing party's side, with
  **positive = cost** to that party. Running cost in bp = `PV_adj / DV01`, with DV01 in currency per bp and positive.
  A cost moves the fixed rate against the client: a payer pays `R_mid + x`, a receiver receives `R_mid − x`.
- **Who holds the option.** The party with the liability posts collateral and chooses what to post. In a multi-CSA,
  the CTD discount rate is the **highest** eligible rate, because a higher discount rate lowers the magnitude of the
  poster's liability.
- **CCP basis sign.** Canonical `ccp_basis.basis_bp` is `LCH − CME`. Clarus and J.P. Morgan quote `CME − LCH`, so
  "+3.4bp" there is `−3.4` here.
- **Names.** FVA here means funding valuation adjustment, not a Forward Volatility Agreement (see
  `vol-rates-options-rv`). Darbyshire notes that some desks say "CVA" for a collateral valuation adjustment; this
  skill calls that **ColVA** and keeps CVA for credit.

### 2. Classify the collateral regime
| Regime | Discount curve | Adjustments to add |
|---|---|---|
| Cleared (LCH, CME, Eurex, JSCC, …) | that CCP's own RFR curve (VM is STM, earns PAI at the RFR) | MVA on incremental IM, CCP basis, fees; no CVA |
| Bilateral, benchmark CSA (local cash, RFR, zero threshold) | local RFR | small CVA from the MPOR gap, MVA if regulatory IM applies, KVA |
| Bilateral, foreign-currency cash CSA (e.g. EUR swap with USD cash) | `EUR:USD-CSA`: period rate `r_EUR + z`, with `z` the xccy basis on the EUR leg | xccy-basis risk, cross-gamma |
| Multi-currency or multi-asset CSA with right to switch | intrinsic CTD curve: daily `max_k r_k` | + collateral switch option (step 4) |
| Bond CSA (pensions, LDI, insurers) | the CTD among cash and the eligible bonds after haircuts | repo and haircut funding |
| One-way CSA (sovereigns, SSAs) | roughly collateralised when ITM to the counterparty, uncollateralised when ITM to the dealer | CVA, FVA, large option value near PV = 0 |
| No CSA (corporates, legacy SPVs) | benchmark uncollateralised curve | CVA, FVA (direction-dependent), KVA |

About 90% of IRS sat under a CSA in 2015 (J.P. Morgan, The law of one price vs. the law of unintended consequences,
May 2016). Bilateral trades are only about 15% of dealer gross notional but about half of gross market value,
because cleared trades are compressed near par (J.P. Morgan, Bills, Bonds, and basis...oh my, Feb 2020). The xVA
problem therefore lives in the off-market bilateral book.

### 3. Build the right discount curve
1. **Local CSA.** Use the RFR curve from `fi-curve-construction`. Per CCP, use that CCP's curve. LCH, the largest, is
   the "source of truth" for EUR RFR forecasts (Darbyshire, Pricing and Trading IRDs, 2022).
2. **Foreign-cash CSA.** The period discount rate for currency-X cashflows under currency-Y cash is
   `r_X + z_{X/Y}`, where `z` is the xccy basis on the X leg under Y collateral. Bootstrap
   `w_i = w_{i−1} / (1 + (r_X,i + z_i) · d_i)`. Check that forward FX implied from any CSA pair is identical: "the
   forward FX rates are the same regardless of under which CSA the XCSs are traded" (Darbyshire, 2022). Formulas,
   the minimal curve set and a worked DF table are in
   [references/cross-collateral-curves.md](references/cross-collateral-curves.md).
3. **Multi-CSA (CTD) curve.** Step daily: `DF(t+1) = DF(t) / (1 + max_k r_k(t) · d)`, where every `r_k` is a rate for
   the *same cashflow currency* under collateral `k`. Never compare raw SOFR with raw ESTR. Block stepping (2–50 day
   steps, then a sigmoid growing to 1,825 days) is a sound approximation. Block DFs are always ≥ exact DFs (Darbyshire, Coding Interest Rates).
   This curve is **intrinsic** and excludes the switch option. Run `scripts/csa_xva.py ctd`.
4. **Bond collateral.** For a liability `L`, the poster's one-period income is
   `L·(1+h)·repo·d − L·h·r_unsecured·d` for a bond with haircut `h`, against `L·r_rem·d` for cash. The highest value is
   the CTD. Government collateral is arguably right-way risk, corporate or some mortgage collateral wrong-way
   (Tuckman & Serrat, 2022).
5. **No CSA.** Borrowing and lending rates differ, so an uncollateralised IRS cannot be priced with one discount
   curve. Price on one benchmark uncollateralised curve and add FVA for the expected cash balance (step 7).

### 4. Collateral switch option (beyond intrinsic)
The option is asymmetric in favour of the poster. With three eligible currencies, each equally likely to cheapen or
richen against the benchmark, 7 of the 8 outcomes give the poster cheaper collateral (Darbyshire, Ex 5.7). Value
rises with:
- the expected |PV| (zero at PV ≈ 0);
- maturity;
- the number of eligible choices;
- choices of *similar* cost (a clear CTD is worth little);
- basis volatility;
- the right and the operational ability to switch (no switch right means no value);

and falls with switching costs. Darbyshire's Table 5.1 ranks examples: USD+JPY is low (JPY is the clear CTD),
USD+EUR medium, USD+SEK low to medium (transaction costs), USD+EUR+SEK at 30Y high. Monte Carlo is the standard
method.

A first-order estimate, which is ours and not from the sources, is fine for screening. For two curves A and B, let
`s(t) = r_B − r_A` be forward `μ(t)` with normal vol `σ_s·√t`, taken from the history of the basis difference. Then:

```
δ(t)          = E+[s(t)] − max(μ(t), 0)          # E+[s] = μΦ(μ/σ) + σφ(μ/σ), >= 0
our option   ≈ Σ ENE(t_i) · δ(t_i) · Δt_i · DF_i   # we post when our PV < 0
their option ≈ Σ EPE(t_i) · δ(t_i) · Δt_i · DF_i   # they post when our PV > 0
```

Units: `s`, `μ` and `σ_s` in bp (σ_s in bp per √year), so multiply `δ` by 1e-4 before applying it to money; ENE is
entered as a positive magnitude.

Treat the option as material when `|net| / DV01 > 0.1bp`, roughly the electronic bid/offer on liquid swaps (Burgess,
Low Latency Interest Rate Markets). For one-way CSAs near PV = 0 the option is large, so run scenarios. Deep ITM,
treat the trade as simply collateralised or uncollateralised (Darbyshire, s.5.2.7).

### 5. Discounting risk and cross-gamma
- An off-market swap with PV `P` has discount-curve pv01 of about `P · T / 2 / 10,000` (annuity-like), or
  `P · T / 10,000` for a zero-coupon swap. Its sign is that of `P`: an asset gains when discount rates fall.
- A non-benchmark CSA curve also moves the **par rate** of a new at-market swap, not only the PV of old ones:
  negligible on a flat curve, larger on a steep one, where the cash balance builds (Darbyshire, ch.13).
- Under a foreign-cash CSA, that risk sits in the **xccy basis plus the foreign OIS curve**, not the local OIS curve
  (Darbyshire, Ex 13.2). Under a multi-CSA it splits by CTD segment (Ex 13.3). Do not draw hard boundaries at the
  switch tenor when collaterals are nearly equal in cost.
- The discounting risk scales with PV, so it is **convex** (cross-gamma). Two offsetting trades under different CSAs
  develop opposite basis risks of ±$1,500 pv01 after a 1bp move on $1mm pv01 of 30Y (Ex 21.4). Tables are in
  [references/cross-collateral-curves.md](references/cross-collateral-curves.md).
- Book-level flow: dealers hedging discounting risk drive long-end discounting basis. They carried about $80mn/bp of
  long-end FF/Libor basis risk and became buyers of long-end basis in a rally (J.P. Morgan, Feb 2020).

### 6. Counterparty credit: exposure, CVA, DVA
- `CE = RC_mtm + C_lag + C_tran + RC_risk`. Collateral removes `RC_mtm` but not the one-day collateral lag, the
  valuation change from default notice to close-out, or replacement cost. Together these are the MPOR.
- Quick collateralised exposure (reader check, reproduces Darbyshire Ex 5.10/5.12):
  `C_lag ≈ pv01·σ_1d·z`, `C_tran ≈ 1.5·C_lag`, `RC_risk ≈ pv01·1bp·z`, with `z = 1.645` (95%) for PFE and
  `z = 0.399` for EE.
- `CVA = LGD · Σ p_i · EE_i · DF_i`, per netting set, never per trade in isolation. PFE and EE are undiscounted future
  values. Formulas, tables and capital are in
  [references/exposure-cva-capital.md](references/exposure-cva-capital.md).
- Screening approximation (external, Gregory): `CVA_bp_running ≈ CDS spread × EPE / notional`.
- DVA: rating-trigger collateral raises your costs as your own credit worsens, and "an actual hedge is virtually
  impossible" (Düring, 2021). Do not count DVA as tradeable edge.

### 7. Funding: FVA
- A collateralised hedge of an uncollateralised trade must be funded. When the client trade is an asset, the hedge is
  a liability and you post VM. Then `FCA ≈ Σ s_borrow · EPE_i · Δt_i · DF_i` and
  `FBA ≈ −Σ s_lend · ENE_i · Δt_i · DF_i`, with spreads as decimals (50bp = 0.005) and ENE a positive magnitude.
- **Direction matters.** In an upward curve a zero-PV receiver accumulates a positive cash balance and a payer a
  negative one (Darbyshire, s.5.4). A one-sided book should skew its FVA to attract offsetting flow.
- Mismatched CSA terms leave a market-flat dealer with funding risk. When posted margin is eligible in several
  currencies, its remuneration rate is itself a cheapest-to-deliver currency option (Düring, 2021).
- FBA overlaps DVA. Count only one of them (external, Gregory).

### 8. Initial margin and MVA
- **IM sizing.** `IM ≈ z · σ_1d · DV01 · √MPOR` (Düring writes `ρ·√t`) plus replacement cost. Tuckman's example is a
  99% move of $5mm plus $250k replacement, so IM = $5.25mm.
- **MPOR.** 1 day for futures, 5 days for cleared IRS (CME Group, Rogerson, Jun 2025), 10 days for uncleared
  (BCBS-IOSCO, external). Futures therefore need much less IM. Cross-margining needs the same FCM and the same CCP, or
  CCPs with a cross-margin agreement. Collateral optimisation picks the CTD collateral but does not cut the amount
  owed (Coalition Greenwich, Q3 2025).
- **Use incremental IM, not standalone.** CCP liquidity and concentration add-ons scale super-linearly. Adding $100mm
  30Y raised CME IM by $10.43m (standalone $7.40m) and LCH IM by $21.21m (standalone $11.51m) (Clarus, CME-LCH Basis
  For Dummies, Jun 2017).
- **Split clearing costs gross IM.** Offsetting positions at two CCPs do not net: $218m at CME plus $262m at LCH,
  $480m gross, against "probably no more than $5 to $10 million" at one CCP (Clarus, Hedging the CME-LCH Basis,
  May 2015).
- **MVA.** `MVA = Σ (r_fund − r_IM) · E[IM_i] · Δt_i · DF_i`. With IM running off linearly to 0 over `T`,
  `MVA_bp ≈ (r_fund − r_IM) · IM_0 · T / (2 · DV01)`, with rates as decimals (20bp = 0.002) and DV01 per bp.
- **Cleared cost stack.** Execution fees; DCO booking (about $4/mm) and maintenance ($2–3/mm a year), or "active"
  plans at 10bp of IM a year; FCM booking (about $1,000 a ticket) and maintenance (10–100bp of IM); then IM funding,
  the largest cost component (Clarus, Pricing and Arbitraging the CME/LCH Basis, Jun 2015).

### 9. Capital (KVA)
SA-CCR `EAD = 1.4 × (RC + PFE)`. CCP-cleared trades carry about a 2% risk weight. The CVA capital charge
synthesises a bond or CDS portfolio that replicates CVA moves (Darbyshire, ch.17). The external standard is
`KVA ≈ Σ hurdle · K_i · Δt_i · DF_i`, with the hurdle taken from the user. Leave balance-sheet detail to
`fi-balance-sheet-and-regulatory-costs`.

### 10. Net it out of the RV signal
`R_fair = R_mid(benchmark CSA, own CCP curve) ± (ColVA + CVA + FVA + MVA + KVA) / DV01`. A price gap between two
venues, counterparties or collateral sets is RV only if
`|gap| > Δ(xVA band)/DV01 + bid/offer of both legs`. Report that difference as the **net edge**.

## Worked examples
1. **Cash vs gilts (Darbyshire, Pricing and Trading IRDs, Ex 5.5, 2022).** The setup:
   - £100mm liability;
   - the CSA allows GBP cash at RFR 0.75%, or gilts with a 2% haircut under 5Y and 6% over 5Y;
   - gilt repo is RFR + 8bp;
   - unsecured funding costs 2.5%.

   One-day income: cash £2,055; 3Y gilt £2,319 − £137 = **£2,182**; 15Y gilt £2,410 − £411 = £1,999. The CTD is
   the short gilt, even after its haircut.
2. **Multi-CSA, JPY cashflows (Ex 5.6).** O/N rates under the JPY CSA are 2.00, 2.05, 2.15, 2.20%; under the USD CSA
   they are 2.10% flat. The CTD path is 2.10, 2.10, 2.15, 2.20%: post USD for 2 days, then switch to JPY through an FX
   swap. DF at t+4: JPY-only 0.999770, CTD 0.999766. `--selftest` reproduces this.
3. **Collateral arbitrage (Ex 5.4).** A €5bn 1w-forward 3m IRS at 1.5% against a 1.0% market, PV ∓€6.23mm, with
   EUR or USD cash allowed on one side and only EUR on the other. With the 1W EUR/USD OIS XCS at +22bp, Alpha posts
   $7.79mm instead of €6.23mm and earns €260.5 (as printed; 22bp × €6.23mm × 7/360 ≈ €266 on the EUR leg's ACT/360, €263 on ACT/365). The USD-or-EUR trade
   should be valued that much higher. The same trade at two banks with different CSAs is not the same price.
4. **CVA with and without collateral (Ex 5.14).** At LGD 100%, CVA is £1,592 for the collateralised 10Y £100mm
   (pv01 about £92k), with PD 0.1% per 2y period. It is £25,593 for the uncollateralised 2y-forward 8Y (pv01 about
   £73k), with PD 1%, 0.4%, 0.1%, 0.1%, 0.1%. The two cases differ in swap and PD path as well as in collateral. At the
   same flat 0.1% PD, our rerun gives £12.9k uncollateralised vs £1.6k collateralised (about 8×). Our conversion to bp
   running is about **0.02bp vs 0.35bp**. Uncollateralised CVA is therefore not negligible next to the 0.1bp
   electronic bid/offer.
5. **MVA explains the CME-LCH basis (Clarus, CME-LCH Basis For Dummies, Jun 2017).** A dealer receives 30Y $100mm
   at CME and pays at LCH. Incremental IM is $10.43m at CME and $21.21m at LCH, tapering to 0 at 30Y. Funding at
   FF+20bp against FF paid on cash gives MVA $282,867 at CME + $443,678 at LCH = $726,545. Divided by DV01 $225,000,
   the article reports CME +1.3bp and LCH +2.1bp, so **3.4bp**, matching the broker mid of 3.40 on 26 Jun 2017.
   Plain division gives 3.2bp. The linear, undiscounted approximation gives 1.39bp for CME and 2.83bp for LCH, against 1.3bp and 2.1bp: it
   overstates, most at the larger LCH profile, so use it only as a conservative screen. In canonical
   orientation the basis is −3.4bp.
6. **Funding (Düring, Fixed Income Trading and Risk Management, 2021).** Funding at O/N + 50bp while posted cash
   earns O/N costs 50bp a year on every unit of margin posted. In the Greece (2018) example (Tuckman & Serrat, 2022),
   Greece paid fixed with no collateral, so dealers with positive NPV bore uncollateralised exposure plus FVA on their
   collateralised hedges. The fix was to novate the positive-NPV swaps to dealers whose NPV was negative.

## Signals & interpretation
- **Cross-venue gaps.** A CCP basis within the MVA plus capital "pricing window" is not arbitrage (Darbyshire, s.6.2).
  Compute the marginal dealer's MVA in bp. Only a basis beyond that band, after fees, is a candidate, and it goes to
  `spread-ccp-basis`.
- **CCP basis vs CVA.** When the CME/LCH basis exceeds the CVA of A and BBB counterparties, which it often did in
  2015–16, wrong-side users were "overcharged (in some cases more than double)" (J.P. Morgan, May 2016). A
  creditworthy client who can sign a CSA should compare bilateral CVA + FVA with the cleared basis.
- **The basis is portfolio-specific.** In 2015 IM differences made LCH pay-fixed dearer to hold by about 0.1bp,
  the wrong direction to explain higher CME rates (Clarus, CME-LCH Basis Spread, May 2015). In 2017 MVA explained 3.4bp for one crafted portfolio, and the basis "can move
  regardless of these costs". In April 2025 swap spreads moved more than 15bp while the 7Y CCP basis stayed flat
  (Coalition Greenwich, Q3 2025), a sign that cross-margining savings now dominate.
- **Discounting events.** A discounting or PAI switch forces one-directional basis re-hedging, so the flow is
  predictable. At the USD switch, CME booked mandatory EFFR/SOFR basis swaps at 2/5/10/15/20/30Y plus cash
  compensation, with an optional unwind auction (CME Group, Jun 2020). LCH let clients opt for cash only and
  auctioned the unwanted basis risk (Citi, US Rates Weekly, Aug 2019). 30Y SOFR/FF spiked around 16–19 Oct 2020 and looked "a bit wide" at about 5bp (BofA, SOFR/FF term structure post big bang, Oct
  2020). J.P. Morgan expected migration to be a long-end SOFR/FF widener and steepener (Feb 2020).
- **Stress.** USD cash-only CSAs create demand for USD collateral in a sell-off or volatility spike, which shows up in
  short-dated xccy basis (Darbyshire, s.8.2.2) and moves every `X:USD-CSA` curve. VM and IM calls rise together, which
  is pro-cyclical (Düring). A hedged pension can still be a forced seller to meet VM calls (Tuckman & Serrat).
- **Market notes.** Each CCP has its own curve per currency (EUR at LCH, Eurex and CME). The JPY LCH/JSCC basis
  reached double digits in 2018 after flow moved to JSCC (J.P. Morgan, The long and short of it, Aug 2018).
  Pension funds prefer bond CSAs (Düring), and in Darbyshire's gilt example the short gilt is the CTD after haircuts (Ex 5.5). Sovereigns use one-way CSAs that dealers hedge with sovereign CDS
  (see `spread-sovereign-cds-and-basis`), and are moving to clearing to cut xVA. MTM (FX-resetting) XCS carry less
  exposure and xVA than non-MTM XCS (Burgess). Switching into SEK is costlier, so its
  collateral optionality is lower (Darbyshire, Table 5.1); the same logic applies to other smaller-market currencies.
  RFRs, day counts and CCPs per market are in `fi-g10-market-conventions`.

## Pitfalls
- **One curve for every trade.** Valuing all trades alike regardless of CSA lets counterparties pick you off. Traders
  have been "picked off" through CSA terms (Huggins & Schaller, 2024). Map every trade to its CSA's curve.
- **Taking the max over raw RFRs** of different currencies. The CTD comparison must be between DFs for the same
  cashflow currency. The script refuses curve ids whose currency prefixes differ.
- **Treating the intrinsic CTD curve as fair value.** It ignores the switch option, and block DFs are biased high.
- **Inconsistent forward FX.** If forward FX differs across CSAs, the cross-collateral build is wrong.
- **Sharp risk boundaries at the CTD switch tenor** when collaterals are nearly equal. Smooth them, or show both
  allocations.
- **Standalone IM** understates MVA at concentrated CCPs, by about 1.8× at LCH in the Clarus example (21.21m vs
  11.51m).
- **Double counting.** CVA vs the CCP basis, FVA vs MVA on the same collateral, FBA vs DVA.
- **Discounting PFE or EE**, or computing CVA per trade instead of per netting set.
- **Assuming zero discounting risk** because the trade was at par at inception. After a large move, legacy and
  off-market swaps carry it in size, and it is convex.
- **Pricing off your own CCP curve** when the client flow comes from the reference CCP. You win only the side that
  builds a one-way, margin-heavy position (Darbyshire, Ex 18.1).
- **Confusing the acronyms.** FVA (funding) is not a Forward Volatility Agreement, and CVA (credit) is not ColVA
  (collateral).
- **Ignoring cleared vs bilateral VM legal form.** STM (cleared, settled daily) and CTM (collateral) differ in capital
  treatment (Tuckman & Serrat).

## Output
One row per trade or netting set:

`trade_id | ccy | tenor | notional | DV01 | regime | discount_curve | PV_benchmark | PV_csa | ColVA | switch_option | CVA | FVA | MVA | KVA | total_xVA | total_bp_running | R_mid | R_fair | observed_gap_bp | net_edge_bp | verdict`

Also produce:
- a discounting-risk ladder by bucket (local OIS / xccy basis / foreign OIS), with the CTD path and switch dates;
- for CCP-basis or bilateral-vs-cleared ideas, the MVA profile (IM by year) and the fee stack.

State every user-supplied assumption (PD, LGD, funding spreads, IM source). Hand the net edge and the assumptions to
`rv-trade-idea-writeup`.

## Scripts
- [`scripts/csa_xva.py`](scripts/csa_xva.py): intrinsic multi-CSA (CTD) DFs from canonical `curve_zero` curves, or
  from daily O/N rates, with optional block stepping; CVA; FVA/MVA funding cost; bp-running conversion; `E+` of a
  normal; and cash-vs-bond collateral carry. Cross-collateral `curve_id`s must start with the cashflow currency
  (e.g. `EUR-CSA-USD`), because the same-currency guard reads that prefix.
  - `python scripts/csa_xva.py ctd --curve-zero data/curve_zero.parquet --date 2026-11-10 --curves EUR-ESTR,EUR-CSA-USD --day-basis 360 --out ctd.csv`
  - `python scripts/csa_xva.py xva --profile profile.csv --lgd 0.6 --fund-spread-bp 50 --im-spread-bp 20 --dv01 225000`
  - `--selftest` checks Darbyshire's multi-CSA DFs (Coding Interest Rates s.6.6; Pricing and Trading Ex 5.6), CVA
    (Ex 5.14), gilt vs cash CTD (Ex 5.5) and `E+[N(0,σ²)] = σ/√(2π)`.

## Related skills
- [fi-curve-construction](../fi-curve-construction/SKILL.md): RFR and per-CCP curves that feed every CSA curve
- [xccy-basis](../xccy-basis/SKILL.md): the basis that builds foreign-collateral curves and drives the CTD
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): trading the CME-LCH-Eurex-JSCC basis once MVA is netted out
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): SOFR/FF and discounting-basis flows
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): SA-CCR, leverage, capital (KVA)
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): discounting-risk buckets and cross-gamma
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): margin and funding inside swap spreads
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo rates for bond collateral and funding spreads
- [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md): one-way sovereign CSAs hedged with CDS
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): RFRs, day counts and CCPs per market
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): choosing venue, CCP and counterparty
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): execution, clearing and FCM fees in the cost stack
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): where the net-of-xVA edge is reported
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical `curve_zero`, `basis_swaps`, `ccp_basis`

## References
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): CSA terms, benchmark CSA, CTD collateral, multi-CSA curves, collateral optionality (Table 5.1), CE/PFE/EE/CVA/FVA with Ex 5.4-5.14, CCP curves, ch.13 CSA risk, ch.17 capital, ch.21 cross-gamma
- J H M Darbyshire - Coding Interest Rates: FX, Swaps and Bonds (rateslib companion book, c.2024): intrinsic multi-CSA curve and its block approximation, cross-collateral DFs, forward-FX formulas
- F M Ametrano & M Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping But Were Afraid To Ask (SSRN 2219548, Apr 2013): perfect-collateral pricing and why the collateral rate is the discount rate
- Clarus Financial Technology (T Skarecky) - CME-LCH Basis For Dummies (Jun 2017): incremental IM profiles and the MVA-to-bp worked example (3.4bp)
- Clarus Financial Technology (T Skarecky) - Pricing and Arbitraging the CME/LCH Basis (Jun 2015): the full cleared cost stack; IM funding dominates
- Clarus Financial Technology (A Khwaja) - CME-LCH Basis Spread (May 2015) and Hedging the CME-LCH Basis (May 2015): in 2015 IM differences pointed the wrong way (about 0.1bp); $480m gross IM from split clearing vs $5-10m at one CCP
- J.P. Morgan (J Younger, A Iglesias, D Sarkar) - The law of one price vs. the law of unintended consequences (May 2016): CME/LCH basis vs CVA by rating, CSA coverage, fair-value band from IM costs
- J.P. Morgan (J Younger, M Salem, H St John) - Bills, Bonds, and basis...oh my (Feb 2020): dealer discounting-risk book, convexity of discounting risk, big-bang flows
- J.P. Morgan (J Younger, M Salem) - Interest Rate Derivatives: The long and short of it (Aug 2018): clearing segmentation, LCH/JSCC basis, uncleared-margin phase-in
- CME Group (S Dayon, D Bawadhankar) - SOFR Discounting Transition Process for Cleared Swaps (Jun 2020): PAI and discounting switch mechanics, compensation basis swaps
- BofA Securities (M Cabana, R Axel, O Lima) - SOFR/FF term structure post "big bang" (Oct 2020): basis behaviour around the switch
- Citi Research - US Rates Weekly: Learning on the job (Aug 2019): LCH vs CME discounting-switch compensation and value transfer
- A Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): VM vs IM, IM sizing, xVA definitions, the 50bp FVA example, DVA, bond and one-way CSAs
- B Tuckman & A Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): VM/IM, CTM vs STM, MPOR, the IM example, haircuts, the Greece FVA case
- D Huggins & C Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): collateral terms differ by dealer and FCM; know your CSAs
- CME Group (M Rogerson) - Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures (Jun 2025): MPOR of 1 day for futures vs 5 days for IRS, portfolio margining conditions
- Coalition Greenwich (S Bruel) - Fixed-income cross-margin opportunities: A driver of change (Q3 2025): MPOR ranking, collateral optimisation vs cross-margining, the 2025 CCP basis
- N Burgess - Low Latency Interest Rate Markets: Theory, Pricing & Practice (slide deck): CSA curves change DFs not forwards, e-trading bid/offer, MTM xccy reduces XVA
- V Stathakopoulos (Credit Suisse) - The Interaction Between Repo and Interest Rate Swaps (ICMA workshop, Sep 2021): the move from Libor to OIS to CTD-collateral discounting
- Barclays (J Abate) - US short interest rate primer (Jan 2025): Basel III endgame floor and SA-CCR effects on uncleared derivatives
- J Gregory - The xVA Challenge: Counterparty Risk, Funding, Collateral, Capital and Initial Margin (Wiley, 4th ed., 2020) (external): CVA spread approximation, FVA/DVA overlap, KVA and MVA definitions
- V Piterbarg - Funding beyond discounting: collateral agreements and derivatives pricing (Risk, 2010) (external): collateral-rate discounting and the collateral option
- BCBS-IOSCO - Margin requirements for non-centrally cleared derivatives (2015, revised 2020) (external): 99% / 10-day IM standard, the basis of SIMM
