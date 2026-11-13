# ASW structures, formulas, sizing and P&L bases

Detail behind `SKILL.md`. Sign tags: **(S-G)** swap minus govt, **(G-S)** govt minus swap. Prices per 100, rates in %, spreads in bp.
`A_fix`, `A_flt` = fixed and floating annuity factors (sum of accrual x DF; they differ when frequency or day count differ),
`d` = DF to maturity, `c` = coupon, `P` = dirty price.

## 1. The measures

| Measure | Definition | Sign / unit | Use | Weakness |
|---|---|---|---|---|
| Spreadover / "optical" (USD interdealer) | on-the-run bond vs spot-start standard-tenor swap, DV01-matched: P = S - B | S-G | liquid, tight bid-offer, short holds | maturities only nominally matched; jumps when the benchmark changes (by ~the old-new yield difference) |
| Matched-maturity (MMS, yield-yield) | par swap to the bond maturity (front stub) minus bond yield; swap notional set by DV01 | S-G (US) or G-S | no curve/duration risk, simple, trackable | convexity remains for off-par bonds; coupon frequency mismatch |
| I-spread | bond yield - swap rate interpolated to bond maturity | G-S | short-term hedges; fast, little balance sheet | "fundamentally flawed" as a cross-bond measure: on an upward curve the high-coupon bond always looks richer |
| Par/par ASW | pay bond coupons (fixed leg = bond cash flows), receive float + s on 100; package at 100 | G-S, bp on float leg | hedge quality, true bond-vs-swap-curve | coupon effect; uses balance sheet; bespoke |
| Proceeds / market-value ASW | as par/par but float notional = dirty price | G-S | preferred when price far from par (low-coupon linkers, zeros) | economically equivalent to par/par; only collateral/counterparty flows differ |
| Z-spread to swap curve | parallel spread z with PV(bond on swap zero curve + z) = dirty | G-S | best single bond-level RV metric; aggregates on a swap delta ladder | not coupon-neutral across very different coupons; model free but curve dependent |
| Spread to fitted govt curve | residual vs spline | either | issue-level rich/cheap | relative, not absolute (splines ignore specialness): see `../../bond-rich-cheap-fitted-curve/SKILL.md` |

Which to use: "the most sensible spread is the one that reflects the usual hedge strategy for the bond" (Düring, Fixed Income Trading and Risk
Management, Wiley, 2021): govies and SSAs vs the govt spline (euro-area SSAs mostly vs the French curve); corporates, covered and senior bank debt
vs swaps (I-spread or ASW).

## 2. Formulas

- **Par/par**: s_par = (c x A_fix + 100 x d - P) / (100 x A_flt). Fair if (P - 100) + 100 + 100 x s x A_flt = c x A_fix + 100 d. Lower P, higher s.
  Equivalent (r_fix, p_mkt, s as decimals): s = [(r_fix - p_mkt) x A_fix + (100 - P)/100] / A_flt, p_mkt = par swap rate. Rule of thumb (in %): s ~ (r - p) - (P - 100)/T
  (Burgess, Low Latency Interest Rate Markets, c. 2022). Per-period amortised spread x to a money-market spread: x x payments per year x 360/365 (JPM, Asset Swaps, Feb 2006: -0.166 per semi-annual period gives -32.7bp).
- **Proceeds**: s_mkt = (c x A_fix + 100 d - P)/(P x A_flt) = 100 x s_par / P (Tuckman & Serrat, Fixed Income Securities, 4th ed., Wiley, 2022).
  Premium bond: with par/par the asset swapper borrows 100 from repo and the swap desk lends the other P - 100 up front; with proceeds the asset swapper borrows P and the swap desk
  pays P - 100 at maturity instead. Reversed for discount bonds.
- **Worked check (Genworth 4.90s 15 Aug 2023, 15 Aug 2021, P 98.70, yield 5.596%, 2y swap 0.288%)** (Tuckman & Serrat 2022): yield spread 530.8bp, bond (forward-curve)
  spread 531.1bp, **par/par 526.4bp, market-value 533.3bp** (= 526.4 x 100/98.70). `scripts/asw.py` reproduces 526.43 and 533.37 on a flat 0.288% semi-annual curve.
- **FRN effective spread**: s_eff = s_float + (100 - P)/(100 x A_flt): converts a premium/discount into a running spread. Discount margin on a curve basis:
  mu' = mu - (P - 100)/sum(DCF x DF); the market-convention DM (future fixings = current) is curve-shape independent and "methodologically incorrect to compare across maturities" (Düring 2021).
- **Z-spread to swap curve**: P_D = sum C_i Z(t_i) e^(-s t_i) + Z(t_n) e^(-s t_n); solve s (root find, three Newton-style steps suffice). On non-callable bonds, bills and FRNs the OAS equals the z-spread.
  Callable: OAS = z-spread - option value (model dependent) (BofA, UST RV Primer, 2 May 2022).
- **Swap-spread DV01 and betas** (Golub & Tilman, Risk Management: Approaches for Fixed Income Markets, Wiley, 2000): dOAS = a + beta x ds; swap-spread duration = beta x spread duration;
  governments beta = 0. Example: CMBS beta 1.5, spread duration 5, +10bp swap widening = -0.75%. Betas are unstable and distorted by OTR specialness and supply hedging.
- **Hedge ratio (DV01-neutral)**: swap notional per bond notional = DV01_bond/DV01_swap. USD 2y example: 184.0/191.3 = 0.962 ($96.2mn swap per $100mn bond) (JPM, Global FI Markets
  Weekly, 21-22 Aug 2026). Rebalance after large moves because convexity differs. Yield-yield swap notional is set by delta, not bond face: Darbyshire's EUR 50mm bond at 99.85 uses a EUR 49.6mm
  yield-yield swap (spread 40bp, pay fixed 1.000%) versus a EUR 50mm par/par swap (pay 1.375%, receive RFR + 37.6bp = 37.5 standard + 0.3 convention - 0.2 make-to-par): the same bond shows
  40bp vs 37.6bp depending on definition (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022). Which type is the best delta hedge depends on market conditions; only the
  par/par synthetic FRN raises convexity issues.
- **Leg DV01s**: a 1bp spread has different DV01 on each leg when day counts/frequencies differ (EUR: annual fixed vs semi-annual floating). Price spread changes on the leg the spread sits on.

## 3. P&L attribution across risk bases (long 10y UST, pay 10y swap)

(Quantitative Finance Stack Exchange, "Calculating PnL on Swap Spread Trade", 2018.) DV01 bond +102, swap -99; yield moves bond +2.0bp, swap +1.7bp.
Outright: [102, -99] . [2.0, 1.7] = 204 - 168.3 = 35.7. "Spread + swap" basis: risk = [[1,0],[1,1]] x [102,-99] = [102, 3]; changes = [[1,-1],[0,1]] x [2.0, 1.7] = [0.3, 1.7];
P&L = 30.6 + 5.1 = 35.7. "Spread + bond" basis: risk [3, 99], changes [2, 0.3], P&L = 6.0 + 29.7 = 35.7. Risk and change transforms must be inverse-transposes so the total is invariant; swap
traders prefer basis 2 and bond traders basis 3 so the outright delta sits in the native liquid hedge. More in `../../fi-risk-dv01-and-transforms/SKILL.md`.

## 4. Direction and naming (state the legs)

- Clarus (Mechanics and Definitions of Spreadovers, 11 May 2015): quotes refer to the bond leg. Buy/pay/lift/take/widener = buy bond + pay fixed on the swap; sell/receive/hit/give/tightener = sell bond + receive.
  If you expect swaps to rise more than bonds, pay fixed and buy the bond; P&L is zero if both legs move together (given consistent carry and curve shape). Düring (2021) uses the opposite mapping.
- **Spread curve / box**: pay 5y swap + receive 10y swap, buy 5y UST + sell 10y UST = long 5y spread, short 10y spread = "selling the 5s10s box" (interdealer quote "5s10s box -4.0 offer"; no official term;
  "flattening" is ambiguous: always list every leg) (Quantitative Finance Stack Exchange, "Nomenclature for Swap Spreads", Nov 2024). Flattening the 2s5s swap-spread curve = cash 2s5s steepener + swap 2s5s flattener.
  30y-5y flattener = long 5y spread + short 30y spread, profits as (30y spread - 5y spread) falls (Rhodes, USD 5s30s Swap Spread Flattener, 9 Oct 2025).
- **Weighting convention**: hedge a 30y spread narrower with a 10% risk-weighted long 30y UST (JPM, Near, far, wherever yields are, 2 Oct 2026); hedge a long-end narrower's curve risk with a 50% matched-duration 10s/30s Treasury flattener
  (JPM, The long and short of it, 3 Aug 2018).

## 5. Replicating spreads with futures (term TED, Schatz gadget)

- **Term TED** = cash bond hedged with a strip or bundle of STIR futures: "essentially a credit spread, akin to the swap spread" (Aikin, STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed., Harriman House, 2012).
  Notional-bond method: DF_stub = 1/(1 + Euribor x accrual); DF_n = DF_(n-1)/(1 + IFR_n x days/360), IFR = 100 - P; TED = strip-priced bond yield - actual yield. Hedge per period
  N_n = [Notional x DP/100 x 0.01% x DF_n x days_n/Year]/BPV_STIR (EUR 25 per bp for Euribor). Derivatives-only: strip yield SY = [(1 + IFR1 x 0.25)...(1 + IFRn x 0.25)]^(1/years) - 1; TED = SY - futures-implied yield.
  Example (20 Dec 2011, EUR 100M Schatz 0.25% Dec-13): hedge 785 Euribor futures sold, strip yield 1.1063% vs cash 0.2118%, TED 0.8945%.
  BPV_future = contract size x (BPV_CTD/100)/CF (Schatz BPV_CTD 0.0191, CF 0.906868: EUR 21.02, so 84 short Euribor per 100 long Schatz).
  Direction: expect TED widening, buy bond/future and sell the STIR futures. Never use the front-month STIR against a bond future (locks to the cash fixing); go to the least liquid point first; watch auctions for CTD changes;
  sellers of term spread face asymmetry (it blows out in flight-to-quality). Swap futures vs T-note futures avoid the convexity bias of Eurodollar forwards.
- **Schatz spread ("gadget")**: forward swap yield from the delivery date minus yield to the Schatz CTD; example front 2y Schatz-type future at 105.76, yield to CTD 2.669, swap yield 3.035, spread 36.6bp; vs IMM 2y swap 2.98 gives 31.1bp
  (Clarus, A Dummies Guide to Trading Interest Rate Swaps, 19 Jun 2024). Futures ASW (Bund, JGB, AUD): carry = CTD spot ASW - futures ASW, 3m horizon = delivery date; roll from the spot ASW curve with a proxy bond
  3m shorter; never compute C&R on the swap leg alone (swapsball.net, How to calculate carry and roll-down for a bond future's asset swap, 12 Dec 2017: Bobl ASW carry 53.7 - 53.1 = 0.6bp/3m, roll ~1.0bp/3m). Invoice spreads and CTD
  switches: `../../fut-invoice-spreads/SKILL.md`, `../../fut-ctd-switch-and-delivery-options/SKILL.md`. Conditional (option-based) invoice spreads: `../../curve-conditional-trades/SKILL.md`.
- **DSF-implied credit spread**: (deliverable swap futures - Treasury futures spread) - (cash 10y - 10y Treasury futures spread), DV01-neutral 58 - 40 = 18bp vs 1:1 92 - 76 = 16bp (CurveTrades/CME, Yield Curve Spread Trades, Jun 2013).
- **Treasury vs SOFR futures strip**: a 3M SOFR futures strip, a SOFR OIS and a repo-financed Treasury price the same segment of daily SOFR. Strip gross factor S to semiannual yield: y = (((S - 1) x 365/360 + 1)^(1/(2n)) - 1) x 2;
  Treasury PV = C/2 x sum 1/S_i + 100/S_n. If a Treasury always financed at SOFR, fair ASW vs SOFR = 0 (H&S, SOFR Futures and Options, 2022). In Mar 2020 an on-strip hedge lost ~20% of the move as the note's ASW widened;
  buying the bond vs selling the hedge on 18 Mar returned 315k of the 328k gap by 31 Mar: a futures-strip hedge works only while Treasury ASW vs SOFR is stable.

## 6. Linkers and bills (pointers only)

- Linker ASW: US/UK use proceeds ASW (notional = dirty incl. indexation), euro area par/par; z-spread (project cash flows with inflation-swap reference values, discount on the RFR curve, bump to dirty) is the preferred RV
  metric; "iota" = linker ASW - nominal ASW is not the inflation basis because cash flows are misaligned (BofA, Global inflation-linked primer, 2nd ed., 22 Jul 2025: TII 2.5% Jan-2029, dirty 156.247, PV at flat SOFR 157.893, z +31.2bp).
  Full treatment: `../../infl-breakevens-and-linkers/SKILL.md`. Bill ASW: `../../stir-bills-and-money-market-spreads/SKILL.md`.
