# MBS math, pool metrics, OAS/OAD and TBA mechanics

Companion to [SKILL.md](../SKILL.md). Formulas are for agency fixed-rate pass-throughs unless stated.
Citation short forms follow the References list in SKILL.md. Conventions: rates in percent, spreads in bp,
prices per 100 face, durations in years.

## 1. Level-pay schedule and pool metrics

- Level payment on balance B0 at rate r (annual, %), N months: `X = B0 · (r/12) / (1 − (1 + r/12)^−N)`
  (Tuckman & Serrat 2022, Ch.15, eq 15.2 in the book's annuity form).
- Balance after i months with no prepayment: `B(i) = B0·(1+m)^i − X·((1+m)^i − 1)/m`, with `m = r/12`.
  Equivalent to the book's closed form `B(i) = X·(12/r)·[1 − (1+r/12)^(i−N)]` (Tuckman & Serrat 2022, App. A15).
- Worked, $100,000, 4.5%, 360 months (Tuckman & Serrat 2022, Ch.15): payment $506.6853; month 1 interest
  $375.00, principal $131.69, balance $99,868.31; balance month 60 $91,157.92; month 120 $80,089.43.
  Interest share of the payment: 74.0% (month 1), 67.6% (month 60), 59.4% (month 120), 0.4% (final month).
  Implication: an amortising loan's interest share falls, so its effective duration shortens as it seasons.
- Pool terms: WAC = gross loan rate; coupon = net rate to investor; WAC − coupon = guarantee fee plus servicing
  (about 55bp g-fee + 25bp servicing, a primary 6.80% loan becoming a 6.00% MBS, Bassman, A Deep Dive into Mortgage Bonds, 3 Nov 2022). WAM = weighted-average
  maturity; WALA = weighted-average loan age; factor = current / original balance.
- "30-year" TBA pool = 15y1m to 30y1m remaining term (Tuckman & Serrat 2022, Ch.15).

## 2. Prepayment rates

- Single-month mortality (SMM): fraction of the start-of-month balance prepaid in month n, excluding
  scheduled principal.
- Annualised CPR: `CPR = 1 − (1 − SMM)^12`. SMM 2% gives CPR 21.53%, not 24% (Tuckman & Serrat 2022, eq 15.5).
  Inverse: `SMM = 1 − (1 − CPR)^(1/12)`.
- Path form: `CPR = 1 − [Π(1 − SMM_i)]^(12/n)`. For n = 3 this is the book's exponent-4 expression
  (Tuckman & Serrat 2022, eq 15.6). This generalisation is a derivation, not a quoted equation.
- Gap test: actual factor vs scheduled-only factor. Worked: a 5% loan 37 months after issue has scheduled factor
  0.952; an older 4.5% pool at factor 0.333 shows heavy prepayment (Tuckman & Serrat 2022, Ch.15).
- Prepayment modules (Tuckman & Serrat 2022, Ch.15): refinancing (S-curve from an incentive measure to CPR;
  incentive = rate difference, rate ratio, PV of savings or monthly savings), turnover (base rate x seasoning
  ramp x seasonality x lock-in), default (original FICO and LTV updated with regional house prices), curtailment
  (minor).
- Burnout: the S-curve depends on pool history. Worked: pool AI4813 peaked near 34% CPR (2012-13) and above 30%
  (fall 2016); in a later rally CPR stayed below 20% at a 2.00% mortgage rate and exceeded 40% only once rates
  broke below 1.50% (Tuckman & Serrat 2022, Ch.15).
- Media effect: refinancing bursts when rates hit a new low (Tuckman & Serrat 2022, Ch.15).
- Refinancing threshold: prepayments jump once a borrower can refinance at least 50bp lower (Bassman,
  Awakening the MBS Convexity Beast, 20 May 2026).
- Logistic prepayment model (During 2021, Ch.27; illustrative): `p_k = b_k + [e^((s−c)/w) / (1 + e^((s−c)/w))]·(1 − m)`,
  with s = PV saving from refinancing into a new 30y. Illustrative: b = 5%/yr, c = 6%, w = 2%, m = 60%
  rate-insensitive. Limits: no rate vol, no burnout, no loan-size effect; prepayments run above baseline at zero
  or negative incentive once spreads exceed about 80bp.
- Refinanceable share (Bassman, The Convexity Vortex, 6 Mar 2013): in 2006 a 25bp drop in the mortgage rate
  (4.60% to 4.35%) lifted the refinanceable share from 31% to 64%; in Feb 2013 a 25bp rise (2.80% to 3.05%)
  cut it from 89% to 75%.
- Refinancing demand (Tuckman & Serrat 2022, Ch.15): refinancing share of originations 33% (2018), 46% (2019),
  65% (H1 2020).
- Eligibility limits: LTV at or below 80% for most refinancing; GSEs do not accept cash-out loans with LTV above
  80%. Conforming limits quoted: FICO at least 620, LTV below 97%, DTI at most 45%, loan below $647,200 in most
  areas (Tuckman & Serrat 2022, Ch.15).

## 3. OAS, OAD, convexity and duration definitions

- OAS: spread added to the model's discount rates (cash flows unshifted) so the model price equals the market
  price. Expected excess return under the risk-neutral measure = short rate + OAS (Tuckman & Serrat 2022, Ch.7).
  Non-callable bonds, bills and FRNs: OAS reduces to a z-spread (Darbyshire, Coding Interest Rates).
- OAS = Z-spread minus the value of embedded options; model dependent (binomial tree or Monte Carlo along
  paths) (BofA, UST RV primer, 2 May 2022).
- P&L attribution (Tuckman & Serrat 2022, Ch.7, eq 7.37): `dP = (r0 + OAS)·P·dt + (dP/dr)(dr − E[dr]) + (dP/dOAS)·dOAS`.
  A hedged rich/cheap trade earns OAS plus convergence (OAS sensitivity x OAS change).
- Spread definitions for a 4.90s 08/2023 corporate (Tuckman & Serrat 2022, Ch.14): yield spread 530.8bp; bond
  spread 531.1bp; par-par ASW 526.4bp; market-value ASW 533.3bp. Use this as a reminder that the spread label
  matters before comparing across sources.
- Effective (static) vs model duration: a 30y 4.5% mortgage has static duration about 11.7 on fixed cash flows
  (Tuckman & Serrat 2022, Ch.15). OAD is much shorter because prepayments shorten it; the FNMA 30y index OAD
  averaged 4.3 over Dec 2011-Dec 2021 (range 1.5-6.3) and moved with the 5y UST yield (negative convexity).
- Price–yield shape: a pool price plateaus as rates fall (refinancing caps upside). Worked: CA2797 (4.5%, Tuckman &
  Serrat 2022, Ch.15) plateaus near 111-112 and is negatively convex below about 1.25% on the 5y UST. Mar 2 to
  May 15 2020 excluded (stress widened OAS independently of rates).
- Effective duration and convexity from ±dy shocks (OAS held constant): `D = (P_dn − P_up)/(2·P0·dy)`,
  `C = (P_up + P_dn − 2·P0)/(P0·dy²)`. Implemented in `scripts/mbs_convexity_hedge.py`.
- Duration drift (Golub (ed.), BlackRock's Guide to Fixed-Income Risk Management, 2023, Ch.2, eq 2.32):
  `−dOAD/dr = OAC − OAD²` (per unit of yield; divide by 100 for the per-1% drift used in the hedge-need recipe, with OAC in standard units). Non-callables drift positive (duration lengthens in rallies); MBS and callables drift
  negative, so a delta-hedged book must sell after rallies and buy after sell-offs. Drift is the cost of
  rebalancing a hedge and is the convexity measure used in the hedge-need recipe (see SKILL.md).
- Empirical duration (BlackRock 2023, Ch.2, eq 2.34): regress percent price change on yield change,
  `dP/P = α − EmpDur·dy + ε`, over 10, 20 or 40 business days; report R². Requires carry-adjusted forward/TBA
  prices; unstable across regimes; a sanity check only.
- Coupon-curve duration (generic MBS): `CCD_3.5 = (P_3.0 − P_4.0)/(P_3.5 · 2 · 0.005)`. Valid only for homogeneous,
  well-priced generic MBS (BlackRock 2023, Ch.2).
- OAS-curve duration: as CCD, but each coupon reprices at the neighbouring coupon's OAS. More model dependent.
- Volatility duration: `VolDur = −(1/P)(P_vol,up − P_vol,down)/(2·dvol)`. Long options negative; short embedded
  options (MBS, callables) positive; largest for ATM options (BlackRock 2023, Ch.2).

## 4. Key-rate, generalised and swap-spread duration

- KRD: `krd_i = −(1/P) dP/dr_i`, with OAS held constant; shock 20-50bp. Key rates: 3m, 1, 2, 3, 5, 7, 10, 15,
  20, 25, 30y (BlackRock 2023, Ch.2). Agency MBS sensitivity sits mainly in 7-10y (Tuckman & Serrat 2022, Ch.5).
- Triangular shocks create oscillating, sometimes negative, forwards that distort MBS and option models. Prefer
  wave shocks (`WKRD_ij` zero before i, full at j, flat after) or principal-component durations (BlackRock 2023, Ch.2).
- PCDs: `pcdur_i = −(1/P)(P_i,up − P_i,down)/2` per one-sd PC shock with OAS constant (Golub & Tilman 2000, Ch.4,
  eq 4.24); mapping `pcdur_i = Σ_j krd_j · p_ij · √λ_i` (eq 4.34).
- Generalised duration (Golub & Tilman 2000, Ch.4): `GenDur = OAD + SSDir·SwSpdDur (+ VOLDir·VolDur)`, with
  `SSDir = ds/dr` (spread vs rates) and `VOLDir = dvol/dr`. Worked, FNMA 7% 30y at 12/31/98: OAD 1.78;
  SSDir x SwSpdDur = −0.1 x 2.17 = −0.22; SSDir x MTB duration = −0.1 x −1.48 = +0.15; VOLDir x VolDur =
  −0.6 x 0.17 = −0.10; GenDur 1.61 vs empirical 1.63. In 1998 rates fell while spreads widened, so mortgage
  implied duration went to about zero.
- Swap-spread duration: `dOAS = a + β·ds + ε`, `SwSpdDur = β·SpdDur`; governments have β = 0. MBS generalisation
  `SwSpdDur = β·(SpdDur + MTB Dur)` with OAD = SpdDur + MTB Dur (Golub & Tilman 2000, Ch.4, eq 4.74-4.87).
  Worked: CMBS β 1.5, spread duration 5; a 10bp swap widening loses 5 x 1.5 x 0.10% = 0.75%.
- Term-structure fix: `β_5y,vs10y = β_5y,vs5y · p_1,5y / p_1,10y` (PC1 loadings; Golub & Tilman 2000, eq 4.88).
- Caveats (Golub & Tilman 2000, Ch.4): on-the-run specialness adds noise to swap spreads quoted against the OTR;
  paying-swap hedges of corporate supply widened spreads more in summer 1999 than in fall 1998; use short series
  because betas are unstable; reconcile with trader intuition, which is in spread levels, not changes.
- Yield-curve (steepener) duration: SEDUR from a 2s10s steepening/flattening of ±50bp, OAS constant:
  `SEDUR = −(P_down − P_up)/(P · 2 · 0.5)` (Golub & Tilman 2000, Ch.2, eq 2.42; check the source before use).
  Pitfall: these shocks are not duration-neutral, so a long-duration bullet can show a spurious steepener. Use
  duration-neutral pivoted shocks (0/2, 2/10, 10/30).

## 5. TBA, specified pools and dollar roll

- TBA: a forward on an unspecified pool; the seller chooses which pools to deliver (a delivery option). Liquidity
  concentrates in a few coupons and the front two months. Since June 2019 TBAs are written on uniform MBS (UMBS),
  so FNMA or FHLMC pools are deliverable (Tuckman & Serrat 2022, Ch.15). Notification is two business days
  before settlement.
- Current contract = front contract with the highest price below par. Current coupon = coupon interpolated to
  par (Tuckman & Serrat 2022, Ch.15).
- The TBA price tracks the cheapest-to-deliver pools (fastest and least predictable prepayers); TBA liquidity
  usually compensates for specified-pool vs TBA basis risk.
- Worked TBA grid, UMBS 30y bids, 30 Dec 2021 (Tuckman & Serrat 2022, Ch.15): January 1.5% 96-13, 2.0% 99-15+,
  2.5% 101-28, 3.0% 103-13. Current contract = Jan 2.0%; current coupon ≈ 2.11%.
- Specified-pool pay-ups over TBA (ticks: 2.0% / 2.5% / 3.0% coupon; Tuckman & Serrat 2022, Ch.15):
  balance under $85k 36 / 58 / 109; $85-110k 31 / 49 / 88; $125-150k 23 / 37 / 71; $200-225k 10 / 16 / 44;
  100% NY 9 / 28 / 75; 100% investor 3 / 14 / 34; jumbo (not TBA-deliverable) −14 / −18 / −38.
  Pay-ups rise with coupon (prepayment protection is worth more when the incentive is higher) and fall with
  loan balance.
- Dollar roll. "Buy the roll" = buy the front month, sell the deferred; "sell the roll" = the opposite.
  Long TBA ≈ long pool + short repo, so the forward drops whenever pool carry exceeds repo.
  - Roll value = net cash from the roll − hold value (hold value = the cash flow discounted to the settlement
    date).
  - Implied financing = rate at which roll value is zero. Specialness ≈ repo rate − implied financing rate.
  - Worked, $1mm 30y 2.5% pool, Jan/Feb 2022, repo 10bp (Tuckman & Serrat 2022, Ch.15; App. A15): Feb cash flow
    $10,850.00 (incl. $8,800.00 principal); hold value $10,849.67; sell Jan at 101-28 gives $1,019,583.33 incl.
    accrued, reinvested at repo for $90.63, buy Feb at 101-20 costs $1,008,201.83 incl. accrued; net roll cash
    $11,472.13; roll value $622.46; implied financing −58.4bp vs 10bp repo, so specialness about 68bp.
  - Caveats: (i) you may not get the same pool back, so the holder's roll value is overstated; (ii) slower
    prepayments lower roll value and raise implied financing; (iii) treating prepayments as known overstates the
    value of holding, because the holder bears prepayment risk.
  - Dollar rolls cover about 90% of RMBS trades (During 2021, Ch.25). A roll is a carry-adjusted settlement push
    when origination falls short. Coupon swaps handle structural shifts in which coupons are produced; rolls
    cannot, because prepayments change the relative value of old and new pools.
- Repo keeps prepayment risk and control of collateral; a short TBA is long the delivery option.
- Structured MBS: CMO/REMIC SEQ, PAC (fixed principal inside a prepayment band, supported by support and companion
  classes) and TAC (protects against fast prepayment only). IOs lose value as rates fall; POs gain strongly
  (Tuckman & Serrat 2022, Ch.15).

## 6. Callable bonds (issuer-side analogue)

- Callable = noncallable − call option. Call value = `d0(T) · ξLN(S0, T, K, σ)` (Tuckman & Serrat 2022, Ch.16, eq 16.1).
- Recipe for a European-type call: (1) solve two forward rates that reprice two reference bonds, giving the
  forward underlying price; (2) take the ATM swaption matching the call tenor, convert normal vol to price vol
  (normal vol × forward DV01 ÷ forward price); (3) iterate a spread on the forwards, holding price vol fixed,
  until the callable price matches the market.
- Worked, BoA 2.305s 2/22/2039, callable 2/22/2029 at par, EUR A2 issuer, 23 Aug 2021 (Tuckman & Serrat 2022,
  Ch.16): ATM 7y x 10y swaption 59.8bp normal; forward DV01 0.0896, so 59.8 x 0.0896 = 5.36 points; 5.36 / 102.29
  = 5.24% price vol. Result: spread −0.158%, option 7.797, noncallable 122.347, callable 114.551 incl. accrued.
- Bermudan/American call: short-rate tree on swap or government benchmark plus OAS; value the noncallable bond;
  value the option by backward induction, `max(exercise, continuation)`; callable = noncallable − option.
- Behaviour: effective duration runs between a short bond (low rates, call likely) and a long bond (high rates).
- Pitfall: market-implied OAS for an issuer with a changed credit spread can explain divergence between two
  otherwise similar callables, or higher rate vol raising the call value. The book gives both explanations;
  decompose before trading (Tuckman & Serrat 2022, Ch.16).
