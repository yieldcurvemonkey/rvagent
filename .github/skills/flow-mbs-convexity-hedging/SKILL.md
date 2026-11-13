---
name: flow-mbs-convexity-hedging
description: Agency MBS and TBA convexity hedging flows and their rates RV effects - negative convexity, OAS vs OAD vs option-adjusted convexity, effective and drift convexity, CPR and burnout, dollar roll and implied financing, coupon stack, the 10y-equivalent hedge need of servicers, banks, GSEs, mREITs and callable issuers, and transmission to swap spreads, swaption vol and the long end. Use when the user asks about MBS convexity, negative convexity, convexity hedging or convexity flows, mortgage hedging, 10y-eq hedge need, TBA or dollar roll, specified-pool pay-ups, current coupon, OAS vs vol, mortgage rate vs 10y CMS, MBS duration extension, or how mortgage hedging moves swap spreads, 30y spreads, 5s30s or 3y10y vol.
---

# MBS convexity hedging flows

Agency MBS holders are short a prepayment option: borrowers can refinance when rates fall. So MBS duration shortens in rallies and extends in sell-offs, and a holder who hedges must buy duration into rallies and sell or pay fixed into sell-offs. That forced trading moves swap spreads, swaption vol and the long end. This skill sizes the flow in 10y-equivalents, tests whether the flow is active, separates it from pipeline and vol-supply effects, and covers the pricing side (OAS, OAD, dollar roll) of the same option.

## When to use
- Sizing how much duration MBS hedgers must buy or sell after a move ("10y-eq hedge need", "convexity flows", "negative convexity bid", "duration extension").
- Deciding whether mortgage hedging is actually moving swap spreads or the long end (directionality beta, 30y spread, flow share of the Treasury market).
- Pricing or screening agency MBS / TBA: OAS, OAD, convexity, current coupon, pay-ups, dollar roll, implied financing, specialness.
- Relating MBS vol demand to swaption vega (3y10y, belly), implied/realised vol, or the 5y20y straddle as a callable-vega proxy.
- Estimating offsets from servicers, banks, GSEs, mREITs, VA writers and long-dated callable issuers.
- Not for: Treasury futures basis and CTD ([fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md)); generic swap-spread RV ([spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md)); pension and insurer ALM beyond mortgages ([flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md)).

## Inputs (data-agnostic)
Agency-MBS inputs are the canonical tables `mbs_tba` and `mbs_pool_stats` in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). Never invent a price, OAS or balance.

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par govt and swap curve, 1y-30y | `curve_par` | daily, >= 3y | DV01 of 10y-eq; curve shocks |
| Swap spreads 2y, 10y, 30y | `swap_spreads` | daily, >= 3y | sign: swap minus govt |
| Swaption normal vols: 3y10y, 1y10y, 10y10y, 5y5y | `vol_surface` | daily, >= 2y | vol supply, implied/realised |
| Repo, GC and specials | `repo_rates` | daily | TBA carry, implied financing |
| Mortgage rate series (30y primary, current-coupon proxies) | `macro_series` | weekly, >= 5y | constant-maturity mortgage minus 10y CMS |
| Callable and Bermudan issuance; swap-into-callable flow | `callable_issuance`, `flows_trades` | daily, >= 6m | offsets to negative convexity |
| Treasury auction supply | `auctions` | >= 3y | net duration supply context |
| Holder balances: banks, GSEs, Fed, mREIT, MSR; MBS outstanding | `positioning` or `macro_series` | monthly/quarterly, >= 3y | active-share sizing |
| TBA prices by coupon and settlement; specified-pool pay-ups | `mbs_tba` (`pool_class` = `tba` or a pool class) | daily; >= 1y | dollar roll, coupon stack |
| Pool stats: WAC, WALA, factor, CPR, OAS, OAD | `mbs_pool_stats` | monthly; >= 2y | prepayment and OAS checks |

If an input is missing, ask the user or the data adapter. Use the public source's own figure with its date when no series exists, and label it as a point estimate.

## Method

### 1. Conventions (state them in every output)
- Prices per 100 face. Yields in decimal internally. Shocks in bp. Durations in years.
- Effective duration `D = (P_dn - P_up) / (2 * P0 * dy)`. Effective (standard) convexity `C = (P_up + P_dn - 2*P0) / (P0 * dy^2)`, dy in decimal. Re-run the prepayment model inside each shock with OAS held constant.
- Drift convexity `C_d = -dD/dy_pct`: the change in duration per +1% yield, sign flipped. MBS and callables are negative; non-callable bullets are positive. Use only in the hedge-need recipe. It is on a different scale from standard convexity, and mixing them mis-sizes the hedge by a large factor (see Pitfalls). Link: with D and C from the lines above, `C_d = (C - D^2) / 100` (D in years, C with dy in decimal). The Bassman pair in example A gives (-224 - 3.95^2)/100 = -2.4, the same scale as BofA's -2 and the -2.42 Bassman prints for a typical par MBS (the conversion is derived here, not printed by either source).
- Hedge need in $bn of 10y-equivalents: `10y_eq = D * N / 10`, N in $bn face. Negative = sell duration (receive fixed, sell UST). Positive = buy duration. The divisor 10 is the source's convention (a 10y duration of 10 years). A 10y benchmark has modified duration nearer 8-9, so to get actual 10y notional divide the DV01 by the live 10y DV01 from `curve_par`.
- Swap spread = swap yield minus Treasury yield (US convention, negative when swaps trade below Treasuries). A positive directionality beta means the spread rises with yields.

### 2. Why the flow exists
Price-yield: `dP/P ~ -D*dy + (C/2)*dy^2`. With negative convexity, a rally shortens duration and a sell-off lengthens it. In drift terms, `D_new = D + move_pct * (-C_d)`. With C_d = -2 and a 100bp rally (move_pct = -1), D_new = D - 2: duration falls two years, so the holder must buy duration to stay hedged. A 100bp sell-off adds two years, and the holder must sell or pay.

### 3. Hedge need recipe (default: parallel moves of +/-25, +/-50, +/-100bp)
1. `D0` = model MBS duration (section 4); `N` = position, $bn face.
2. `D(m) = D0 + (m/100) * (-C_d)`, m in bp, linear in m.
3. `need(m) = (D0 - D(m)) * N / 10`. Negative = sell duration; positive = buy.

Defaults and reasons: the 25/50/100bp grid spans where sources say hedgers act (they act on net moves above about 20bp and peak exposure appears in 70-100bp rallies). The recipe is linear, so read +/-100bp as an upper bound on a single rebalance. It ignores path dependence (hedgers rebalance relative to their last hedge), prepayment model changes and the cost of rebalancing.

Worked example B below gives the numbers. Rally cases use the same recipe and are derived here, not printed in the source. Linear extrapolation is the recipe's assumption, not a claim about the market.

### 4. Pricing the MBS duration and convexity
- Static duration (fixed cash flows) is misleading. A 30y 4.5% mortgage has static duration about 11.7 (Tuckman & Serrat 2022, Ch.15). Model OAD is much shorter because prepayments respond to rates. FNMA 30y index OAD averaged 4.3 over Dec 2011 to Dec 2021, range 1.5 to 6.3, and moved with the 5y Treasury yield, the negative-convexity signature. Use model OAD in the hedge need.
- Shock size: +/-25bp for duration; +/-50bp (or +/-100bp) for convexity, because a second difference needs larger shifts to beat model noise. This is a practitioner default. The BlackRock guide uses 20-50bp for key-rate shocks.
- Key-rate durations `krd_i = -(1/P) dP/dr_i` (OAS constant), key points 3m, 1, 2, 3, 5, 7, 10, 15, 20, 25, 30y. Agency MBS sensitivity sits mainly in 7-10y (Tuckman & Serrat 2022, Ch.5). Use wave or principal-component shocks, not triangular shocks: triangular shocks create forwards that oscillate and go negative, which distorts prepayment models.
- Empirical (implied) duration: regress `dP/P` (y) on `dy` (x) over 10, 20 or 40 business days; duration = minus the slope; report R^2. Carry-adjust forward and TBA prices first. Use as a sanity check on model OAD only.
- Generalised duration with spread and vol directionality: `GenDur = OAD + SSDir * SwSpdDur + VOLDir * VolDur`, with `SSDir = ds/dr` and `VOLDir = dvol/dr` (Golub & Tilman 2000, Ch.4). For an MBS the spread leg also carries the mortgage-to-benchmark duration: add `SSDir * MTBDur`, as example F does. Worked example F. Use it when spreads and vol move with rates; in crises the directionality coefficients grow, can change sign, and are rarely zero.
- Volatility duration `VolDur = -(1/P)(P_volup - P_voldn)/(2*dvol)`. Short embedded options (MBS, callables) have positive vol duration; largest for at-the-money options.

### 5. Who hedges, and how big the flow is
Holders and their convexity sign:

| Holder | Convexity | Hedge behaviour and source |
|---|---|---|
| Agency MBS investors (money managers, REITs, GSEs, banks) | negative | buy duration in rallies, sell or pay fixed in sell-offs, if they hedge |
| Originator pipeline (rate locks) | negative (borrower option) | short UST or pay-fixed (ratio near OAD), plus payer swaptions and straddles (Tuckman & Serrat 2022, Ch.15) |
| Servicers (MSR) | negative duration, negative convexity in most regimes | receive fixed or buy UST; buying TBAs adds negative convexity, so buy swaptions to offset (JPM, Markets struggle to feed the convexity beast, 28 Feb 2020) |
| Banks (asset side: agency MBS, mortgages, MSR) | short convexity | receive swaps; deposits (long) offset (JPM, Is bank convexity hedging lying in wait, 31 May 2019) |
| mREITs | negative, kept for dividend income | receive swaps; with price to book below about 100%, equity raising is unlikely (JPM, Markets struggle, 28 Feb 2020) |
| VA writers (insurers) | short long-end gamma | liabilities extend in rallies (more so when equities fall), so they are left short and must buy long-end duration in rallies (JPM, For cheap gamma, look to the long end, 23 Aug 2019); VA duration contracted $23bn in one week in Feb 2020 (JPM, Markets struggle, 28 Feb 2020) |
| Long-dated callable issuers (Formosa and Korean lifers, original maturity over 15y) | positive (issuer call sold) | modelled as callable swaps struck at par; offset MBS (JPM, Dynamic hedgers are long, banks are short, 13 Sep 2019) |
| Bermudan callable issuers (5nc3m) | positive | offset MBS; 5y20y straddle as vega proxy (Citi, Time for moderation, 17 Feb 2023) |

Sizing rules:
- Active share: the share of negative convexity actively hedged fell from about 50% (early 2000s) to about 15%. Money managers 20% to 10%; GSEs about 25% (2005) to under 2% (Q3 2020, FHFA $250bn cap); REITs 7% (2013 peak) to under 3%. Non-hedgers (banks about 35%, Fed about 30%) hold over 65%. JPM assumed about 20% of bank negative convexity is actively managed.
- Flow = hedge need x active share x hedge ratio, summed over holders, net of callable offsets.
- Flow share of the Treasury market (BofA primer, Exhibit 7; 10y-eq per 25bp move): Jun 2003 169bn = 10.1% of a $1,669bn market; May 2013 105bn = 1.7% of $6,266bn; Feb 2021 63bn = 0.5% of $11,529bn. Share falls over time, so before blaming convexity hedging for a move, compute the share. Feb 2021 was mostly pipeline hedging.
- Triggers: hedgers act on net moves above about 20bp since their last rebalance; they "tend not to be involved until rates have re-priced materially" (JPM, Dynamic hedgers, 13 Sep 2019).
- Asymmetry: duration buying in a 50bp rally far exceeds duration shedding in a 50bp sell-off, because the universe moves out of the money (Barclays, The urgency question, 2 Oct 2026). Barclays puts convexity flow at about $40-50bn 10y-eq per 25bp rise for hedging investors (Barclays, Swap spreads: The Bright Spot, 30 Sep 2026).
- Bank gap: deposits are long duration and migrate to money funds as rates rise. Inputs in the JPM model: retail deposit beta 0.45, wholesale 0.65, both moving 0.15 per 100bp; book equity 9.5% of assets. Result: bank equity duration about 5 years short at 1Q19, and a further 100bp rally adds 6-7 years. Gap figures are upper bounds because banks hedge a fraction.

### 6. Dollar roll and implied financing
- Buy the roll = buy the front month, sell the deferred. Long TBA is approximately long pool plus short repo, so the forward drops whenever pool carry exceeds repo.
- Roll value = net cash from the sale and rebuy (incl. accrued, incl. reinvestment) minus hold value `H` (pool cash flow discounted to the sale settlement at repo).
- Implied financing `f` is the rate that sets roll value to zero. With `S_sell`, `S_buy` the invoice amounts incl. accrued, and `d` the days of the reinvestment (sell settlement to rebuy settlement, 360 basis): `f = (H - (S_sell - S_buy)) / (S_sell * d/360)`. Specialness = repo minus `f`.
- Worked (Tuckman & Serrat 2022, App. A15): $1mm 30y 2.5% pool, Jan/Feb 2022, repo 10bp. Hold value H = 10,849.67. Sell Jan at 101-28 incl. accrued = 1,019,583.33; reinvest 32 days at repo = 90.63; buy $991,200 Feb at 101-20 incl. accrued = 1,008,201.83. Net roll cash 11,472.13; roll value 622.46. The book prints implied financing -58.4bp against 10bp repo, specialness about 68bp. Recomputing on the printed cash flows with 32/360 gives about -58.7bp; the 0.3bp gap is not explained by the printed numbers, so reconstruct the number yourself (`scripts/mbs_convexity_hedge.py`, `implied_financing`) before quoting it. Day counts in the example: sell settles 13 Jan (12 days accrued), buy settles 14 Feb (13 days accrued), reinvestment 32 days, hold value discounts the 25 Feb payment 11 days.
- Breakeven sensitivity: slower prepayments lower roll value and raise implied financing. Holder roll value is overstated if you may not get the same pool back, and treating prepayments as known overstates the value of holding.
- Roughly 90% of RMBS trades are TBA (During 2021, Ch.25). A roll is a carry-adjusted settlement push when origination falls short. Coupon swaps handle structural shifts in which coupons are produced; rolls cannot, because prepayments change the relative value of old and new pools.

### 7. Prepayments, OAS and the coupon stack
- Single-month mortality to CPR: `CPR = 1 - (1 - SMM)^12`. SMM 2% gives CPR 21.5%, not 24%. Path form: `CPR = 1 - prod(1 - SMM_i)^(12/n)`.
- Four modules: refinancing (S-curve from an incentive to CPR; incentive as rate difference, rate ratio, PV of savings or monthly savings), turnover (base rate times seasoning ramp, seasonality, lock-in), default (FICO and LTV updated with regional house prices), curtailment (minor).
- Burnout and media effect make the S-curve path dependent. Price with Monte Carlo along risk-neutral short-rate paths, discounting along each path and averaging. Do not regenerate paths between base and shifted valuations; that adds noise.
- Logistic prepayment (During 2021, Ch.27, illustrative): `p_k = b_k + [e^((s-c)/w) / (1 + e^((s-c)/w))] * (1 - m)`, with s the PV saving from refinancing into a new 30y, b = 5%/yr, c = 6%, w = 2%, m = 60% rate-insensitive. It has no rate vol, no burnout and no loan-size effect.
- OAS: spread added to model discount rates, cash flows unshifted, so model price equals market. Risk-neutral expected return = short rate + OAS. P&L attribution (Tuckman & Serrat 2022, Ch.7): `dP = (r0 + OAS)*P*dt + (dP/dr)(dr - E[dr]) + (dP/dOAS)*dOAS`. A hedged rich/cheap trade earns OAS plus convergence (OAS sensitivity times the OAS change).
- Specified pools trade at pay-ups over TBA. Pay-ups rise with coupon (prepayment protection is worth more when incentive is high) and fall with loan balance. Jumbo loans trade at a discount.
- MBS as bond minus call: a 4.00% 10y at par less a 4-point call struck at 3.25% is a $96 package yielding 4.51%. Add 2 points of OAS (about 25bp) and the yield is 4.76%, matching the average 75bp spread (Bassman, A Deep Dive into Mortgage Bonds, 3 Nov 2022).

### 8. Vol and curve transmission
- Homeowners own the refinancing option and are net long vol. MBS investors are net short vol, so each $100mm of new 30y fixed MBS roughly equals $50mm of 3y x 10y straddles sold (Bassman, The Largest Volatility Sale Ever, 23 Mar 2010).
- Fed QE as a vol sale: the Fed does not delta-hedge, so $1.25tn of purchases equals about $625bn of 3y x 10y straddles sold (same source). Count Fed purchases as un-recycled prepayments.
- Implied/realised: 3y10y implied normal vol over 6-month realised has a long-run average of 107%, which is the "risk-adjusted fair value" for short convexity. It diverged after FASB 156 (2005), when servicer hedge buying richened belly vol (Merrill Lynch RateLab, Professional Javelin Catching, 16 Feb 2007).
- Belly vega: MBS vega centres on 2y into 10y; 3y10y is the largest MBS vega bucket. In the 2013 taper, MBS hedgers bought belly vega and tail vol fell (Bassman, Forwards are NOT a Prediction, 12 Aug 2013).
- Vega PCA (Citi, Gamma and Vega RV, 14 Jan 2019): 3y10y cheap by about 1.9 normals (z about -2.2), attributed to less convexity-hedger vega demand than before the crisis. Source text and table disagree on the 3y2y z-score (3.6 vs 2.6); use the table and say so.
- Floaters with fixed caps (Citi, Fading vega dislocations, 5 Oct 2026): $496bn outstanding, 72% capped at 6-7%. As forwards approach caps, holders become long duration and short vega; max short vega $204mm, equal to $217bn notional of 3y10y straddles.
- Long-dated forward steepeners (10y10y vs 20y5y) carry net negative convexity and forward flatteners net positive, so forward-curve shape and implied vol tend to move inversely. A bear-flattened curve with collapsing vol was flagged as an entry signal (Citi, Forward steepener and vol divergence, 12 Jun 2023).

### 9. Swap spreads and the long end
- Spread duration mapping (Golub & Tilman 2000, Ch.4): `dOAS = a + beta * ds + e`, `SwSpdDur = beta * SpdDur`. Governments have beta 0. For MBS: `SwSpdDur = beta * (SpdDur + MTB Dur)` with `OAD = SpdDur + MTB Dur`. Worked: CMBS beta 1.5, spread duration 5; a 10bp swap-spread widening costs 5 * 1.5 * 0.10% = 0.75%.
- Directionality: rolling 3-month beta of swap-spread changes on yield changes (bp/bp). Positive beta = swap-paying hedging in sell-offs and swap-receiving in rallies. Beta through 2019 was about 0.10-0.15, strongest out the curve (JPM, Is bank convexity hedging lying in wait, 31 May 2019).
- Active test: counter-directional moves mean hedgers are not yet active (JPM, The return of convexity hedging, 31 Jan 2020). Spreads move meaningfully only after large outright moves (JPM, Markets struggle, 28 Feb 2020).
- Payers and receivers: GSE shrinkage cut the historical mortgage-payer demand, and Fed MBS QE removed more of it; net receive demand pushes spreads down until toggling investors take the other side (TBAC, Charge: Swap Spreads, Feb 2021).
- Regression (TBAC, Feb 2021): 30y spread on Treasury supply, 5s30s steepness, S&P 500 (VA proxy) and MBS duration gave R^2 of 61%. Since YE-2019 the 30y spread ran 16bp wider than predicted; residuals in 2015 and 2020 coincide with Basel III and the SLR exemption, so add regime dummies.
- Flow balance (JPM, What about bonds? SLR relief, 2 Apr 2020, 10y-eq, Apr to year-end 2020): buyers about $1.1-1.3tn (Fed $400bn; banks $300-500bn and financial issuers $250bn via derivatives); sellers about $2tn (Treasury $1.6tn). The printed buyer components sum to about $1.05-1.25tn, a little below the headline range. Buyers use swaps and sellers use securities, which biases swap spreads narrower.
- Conditional steepener (JPM, The return of convexity hedging, 31 Jan 2020): rolling 3-month beta of weekly 10y vs 2y swap-rate moves, estimated separately on sell-offs, rallies and all moves. Negative convexity helps bear-steepen in sell-offs, so a sell-off beta above 1 gives positive expected value for a premium-neutral bear steepener.

### 10. Market differences (G10)
- USD: agency MBS (FN, FH, GN; UMBS TBAs since June 2019), GSE and Fed portfolios, mREITs, servicers, bank deposit betas, callable offsets. Fed: QT cap of $35bn a month for MBS, rarely reached; after QT, paydowns were reinvested into Treasuries (BofA Global Research, Fed policy plumbing '25, 8 Jul 2025). Check current Fed policy before projecting reinvestment.
- EUR: no TBA market. Danish callable mortgage bonds are the analogue: 30y callables, vol exposure mainly at 5y and 10y expiries, negative duration to about 140bp spread (During 2021, Ch.25-28; Nordea, Bonds & bold, 5 Nov 2021). Dutch pension UFR rules impose short convexity on pension managers, who must buy duration as yields fall (During 2021, Ch.20-31). Use 5y20y straddles as a proxy for callable vega; Nordea's test shows the callable beat the government index in stable-rate periods and lagged in the periods when the straddle lost.
- GBP: UK mortgage hedging (pay fixed) increases as mortgage rates fall. BoE 2y and 5y fixed mortgage rates (75% LTV) peaked May 2024; net mortgage borrowing rose £2.8bn in July 2024, the highest since Nov 2022; bank receiving faded after 1H24 deposit churn. Expression cited: pay the 5y belly of a 3s5s7s fly (BofA, UK Rates Viewpoint, 5 Sep 2024).
- JPY: lifers hedge UST and MBS with FX forwards; banks fund UST and MBS in repo; GPIF does not FX hedge. Lifers reduce hedge ratios as hedging cost rises. Life-insurer yield floors predictably bear-flatten or bull-steepen the 20s30s JGB sector (JPM, Cross currency basis 2H25 Outlook, 5 Jun 2025).
- AUD and NZD: banks issue about USD 100bn a year of term funding at 3-5y to match about 5y mortgage duration; they pay the 6m-1y basis for money-market issuance and the 3y-5y basis for term funding (BofA, FX-SOFR primer, 31 Oct 2023).
- CAD, CHF, SEK, NOK: no agency-MBS pool or TBA data in the source set. SEK mortgage-bond futures are listed (product sheet, Apr 2024). Do not transfer USD numbers; ask the adapter for local pool, mortgage-rate and swap-spread data.

## Worked examples

**A. Convexity of MBS vs Treasury from a printed price pair** (Bassman, Leverage is NOT a four-letter Word, 26 Jan 2023). 10y UST at 105.06 (3.51%): -100bp gives 113.96, +100bp gives 96.96. Effective duration = (113.96 - 96.96) / (2 * 105.06 * 0.01) = 8.09. Standard convexity = (113.96 + 96.96 - 210.12) / (105.06 * 1e-4) = +76. FN 4.5% at 98.44 (about 4.75%): -50bp gives 100.11, +50bp gives 96.22. Effective duration = 3.95. Convexity = (100.11 + 96.22 - 196.88) / (98.44 * 2.5e-5) = -224 (rounded prices; treat as roughly -220 to -230). The two bonds have very different signs. The author treats the 148bp MBS-UST yield spread as mostly this convexity difference. These are standard-scale numbers, not the drift measure in section 3.

**B. Hedge need** (section 3): duration 7, $100bn, drift convexity -2. Up moves give hedge need -5/-10/-20 $bn; rallies give +5/+10/+20 $bn (buy).

**C. Vol-surface inversion from flows** (Merrill Lynch RateLab, The "Positive Carry" Hedge, 31 Oct 2008). A 10y swap 10 years forward was about 2bp below spot despite a +169bp 2s10s slope. A 1y10y straddle at 141 normal vol traded against 83 for 10y10y. Causes: receive-30s inversion hedging, and servicers' short-expiry gamma demand against trust-preferred long-expiry supply. Forwards are a DPV, not a forecast.

**D. Dollar roll** (section 6): Jan/Feb 2022, $1mm 30y 2.5%: roll value 622.46, implied financing about -58bp against 10bp repo, specialness about 68bp (book print -58.4bp).

**E. Mortgage vs swap spread signal** (Bassman, The Water is Warm in the MBS Pool, 1 Jun 2022): the constant-maturity mortgage minus 10y CMS spread was 115bp against a long-run average of 73bp, about 2 standard deviations wide; in Sep 2021 it was 50bp with MOVE in the mid-60s. The author calls it the best macro indicator of MBS value. Use it as a z-score against its own history, not as an absolute level.

**F. Generalised duration** (Golub & Tilman 2000, Ch.4; FNMA 7% 30y at 31 Dec 1998). OAD 1.78. SSDir x SwSpdDur = -0.1 x 2.17 = -0.22. SSDir x MTB duration = -0.1 x -1.48 = +0.15. VOLDir x VolDur = -0.6 x 0.17 = -0.10. GenDur = 1.78 - 0.22 + 0.15 - 0.10 = 1.61, against an empirical duration of 1.63. SSDir of about -0.1 means swaps tightened 10bp for a 100bp rise in rates. In 1998 rates fell while spreads widened, so implied duration went to about zero.

**G. Scenario grid** (Citi, Agency MBS Weekly: The Summer Lull, 21 Aug 2026): on 3-month annualised returns with OAS unchanged, 2.0% pools return 3.9% in forwards, -10.4% in a +50bp shock and +21.4% in a -50bp shock; 7.0% pools return 5.1%, +1.7% and +7.8%. Use the grid to show asymmetry by coupon, not as a forecast. The note's reusable curve-shock template has seven scenarios: forwards; +/-50bp parallel; bull steepener (-50bp at 2y and shorter, -25bp at 5y, 0 at 10y and beyond); bull flattener (0, -25, -50); bear steepener (0, +25, +50); bear flattener (+50, +25, 0).

## Signals & interpretation
- Net move of about 20bp or more since the last rebalance: expect the flow to start. Check the directionality beta before calling it active.
- Directionality beta (3-month rolling, regress the change in swap-minus-Treasury spread (y) on the change in yield (x), bp/bp): clearly positive and above the 10y median means active hedging. Negative or near zero means hedgers are not yet active (for example, January 2020). A 3-month window has only about 60 daily points, so report the standard error (HAC) next to the beta; rolling betas overlap, so their percentile band is descriptive, not a test.
- Size of the spread response in past events (BofA primer, Exhibit 9, bp): Jun-Aug 2003 10y yield +145, 10y swap spread +19, MBS OAS +19; May-Jul 2013 +81, +13, +7; Feb 2021 +13, +1, +1. Spread moves were about 0.13 to 0.16 of the yield move in the two big events, in line with the 0.10-0.15 beta, and negligible in 2021.
- Peak negative convexity in a 70-100bp rally. Exposure can rise about 30% if rates fall 70bp or more (JPM, A comprehensive look at convexity hedging, 29 Mar 2019). Use this to cap flow estimates.
- Refinancing trigger: prepayments jump once borrowers can refinance at least 50bp lower (Bassman, Awakening the MBS Convexity Beast, 20 May 2026). Refinanceable share is a better gauge than the coupon gap: in 2006 a 25bp drop took it from 31% to 64%; in Feb 2013 a 25bp rise cut it from 89% to 75% (Bassman, The Convexity Vortex, 6 Mar 2013).
- Mortgage spread decomposition (Bassman, A Deep Dive into Mortgage Bonds, 3 Nov 2022, toy bond-minus-call model): of a 175bp spread in 2022, implied vol 4 to 6 points added about 25bp, OAS 25 to about 60bp, and the curve inversion (10y forward moving from 30bp above spot to 35bp below it) took the call from 30bp out of the money to 35bp in the money, 6 to 9 points or about 40bp. The curve shape matters as much as vol: an inverted curve makes the refinancing option richer.
- Coupon stack: loans are issued near par about 50bp above the MBS rate, so call strikes cluster. Where they cluster, realised vol rises, then implied vol. Strikes go stale after re-couponing: the book's coupon regimes were 7.25% (1993-2001), 5.55% (2002-08) and 3.60% (2009 on), so re-map strikes after each regime shift.
- Implied/realised 3y10y: the 107% long-run average marks fair value for selling vol. Ratios far above it mean rich vol to sell; far below mean vol is cheap to buy.
- Pull-through: 70% pull-through means $700mm of TBA sold per $1bn of locks; if it rises to 80%, a further $100mm of TBA is sold per $1bn. Sensitivity is about 5-6% per 15bp of mortgage rate. Pull-through rises as rates rise, and the sensitivity falls after a large move until the pipeline rebuilds (about 45 days) (BofA primer, 18 Mar 2021). Rate locks usually run about 60 days (Bassman, A Deep Dive into Mortgage Bonds, 3 Nov 2022). Dealers absorb the TBA duration and pass it on by selling Treasuries or paying fixed.
- Primary/secondary spread (P/S, primary mortgage rate minus the secondary MBS yield): a wide P/S damps the beta of mortgage rates to Treasury yields; BofA puts the lowest economic level near 105bp (Mar 2021), and as P/S compresses toward it, beta and convexity-event risk rise (BofA primer, 18 Mar 2021). Bassman's 2022 figure of about 80bp (55bp g-fee plus 25bp servicing; a 6.80% primary rate against a 6.00% MBS coupon) is a different measure (primary rate minus MBS coupon, A Deep Dive into Mortgage Bonds, 3 Nov 2022). Do not compare the two levels; track one definition from your own data.
- Index convexity: Bassman (Awakening the MBS Convexity Beast, 20 May 2026) reports index convexity of -1.06 against a typical par MBS of -2.42. Index-level negative convexity forces buy-high, sell-low behaviour, which widens ranges and raises implied and realised vol. Units differ across sources; use as stated.
- OAS and the fair band: a dealer's fair-value OAS band is a model claim. Citi's Aug 2026 note puts Treasury production-coupon OAS at 29bp against a 20-30bp band. Ask for the model before trusting the band.
- OAS and vol: a high OAS when implied vol is low means you are selling vol cheaply, not that the MBS is cheap. Judge OAS against the vol you effectively sell.
- Expression logic: hedgers receive swaps in rallies and pay in sell-offs. A trade that stands with that flow (receive into a rally, pay into a sell-off) needs the beta and active-share checks above first. Without them, the flow is a hypothesis, not an edge.

## Pitfalls
- Units: MBS convexity in the drift recipe is not the standard convexity from section 1 or worked example A. Mixing them mis-sizes the hedge by a factor of 100. The BofA primer warns about exactly this.
- Hedge need is a flow against a flat-book base at a reference date. Gap figures (for example "$800bn unhedged") are upper bounds, since banks hedge only a fraction.
- Do not over-attribute moves. Convexity-flow share of the Treasury market fell from about 10% (Jun 2003) to 0.5% (Feb 2021), so February 2021 was mostly pipeline hedging.
- Model OAS: a whole sector (for example high loan balance) can look rich or cheap. That is usually model error or a bet that the model beats the market. OAS may not mean-revert within your funding horizon (Tuckman & Serrat 2022, Ch.15).
- Static duration is not model duration. A 30y 4.5% pool has static duration about 11.7, while a 4.5% pool in the Dec 2021 pool table had model OAD 3.98. Never size a hedge on static duration.
- Triangular KRD shocks create negative forwards that distort MBS and option models; use wave or principal-component shocks.
- SEDUR and LEDUR shocks (2s10s and long-end steepening) are not duration-neutral. A long-duration bullet can show a spurious steepener by construction. Use pivoted, duration-neutral shocks (0/2, 2/10, 10/30).
- Empirical duration needs carry-adjusted TBA prices and is unstable across regimes.
- Swap-spread betas and directionality are unstable. They grow in crises and can flip sign. Use shorter series, and check the result against trader intuition in spread levels.
- Errors in variables: if the spread is swap minus Treasury and the regressor is the Treasury yield, asynchronous closes bias the beta downward (the Treasury yield noise sits in both sides with opposite sign). Use synchronised snapshots, weekly changes, or a common regressor such as the swap yield, and state which.
- On-the-run specialness adds noise to swap spreads quoted against the on-the-run. Corporate supply hedged with paying swaps can widen spreads more than the MBS-driven move suggests (summer 1999 vs fall 1998).
- Regression fits are fragile: in one Citi study the 2y swap-spread R^2 was 0.61 for coupon-only and 0.21 with bills added (Citi, All it takes is a little push, 4 Oct 2019). Specification matters.
- Fast rallies can outrun hedgers, and servicer positive convexity can offset GSE receiving, so spreads may not narrow at first (JPM, Markets struggle, 28 Feb 2020).
- Convexity bias inverts the very long end beyond 25-30y in most models. That is a model shortcoming, not a trade (During 2021, Ch.20).
- Index MBS (low coupons, around 3.5% yield) has little curve exposure; only near-par new-issue pools carry the curve optionality. Do not proxy a covered-call trade with the index.
- Sources disagree in places (Citi vega z-score; a Tuckman net-column print; mixed sign conventions for directionality). Use the text or the table, say which, and state the sign convention.
- Dates: several sources are dated 2026 as printed. Refresh every number from the adapter before using it as an input.

## Output
Return one panel per question, with the as-of date and source on every number:
1. **Conventions line:** units (bp, $bn 10y-eq, drift convexity or standard), sign convention for swap spreads, shock size and OAS treatment.
2. **Hedge-need table:** columns move (bp), D_new, 10y-eq base, 10y-eq new, need ($bn; negative = sell). Rows -100, -50, -25, +25, +50, +100 unless the user asks otherwise. State the position size and drift convexity used.
3. **Flow:** active share used (and its source), flow after share ($bn 10y-eq), and that flow as a percentage of the Treasury market, with the market size used.
4. **Signal panel:** directionality beta (2y, 10y, 30y, with 10y median and 5th/95th percentiles), counter-directional flag, CMM minus CMS z-score, 3y10y implied/realised ratio, OAS against the fair band if one exists, P/S spread, and roll implied financing against repo.
5. **Verdict:** the expression (for example "receive 10y swap spread" or "sell 3y10y straddle"), the trigger, the invalidation level, and what would show the flow is not active.
6. **Data gaps:** any input not available from the adapter, with the question the user needs answered. Do not fill gaps with invented numbers.
7. **Hand-off:** send any trade idea to [rv-devils-advocate](../rv-devils-advocate/SKILL.md) for adversarial review, then [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) for the note.

## Scripts
- [`scripts/mbs_convexity_hedge.py`](scripts/mbs_convexity_hedge.py): CPR and SMM conversions, level-pay balances, effective duration and standard convexity from +/- shocks, drift convexity (also from standard D and C), dollar-roll `roll_value` and `implied_financing`, and the 10y-eq hedge need. Usage: `python -I scripts/mbs_convexity_hedge.py --hedge-need --duration 7 --amount-bn 100 --convexity=-2 --moves-bp=-25,-50,-100`. Use `=` for negative lists. `--scenario-px` reads a CSV or Parquet table with date, instrument_id, px_base, px_up, px_dn, dy_bp. `--selftest` checks the BofA hedge-need example, the rally case, a zero-coupon bond with analytic duration and convexity, the Bassman UST/MBS price pairs, the dollar-roll example, and the printed mortgage balances and CPR, and exits non-zero on failure.

## Related skills
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): pricing the long-end convexity that hedgers sell and buy.
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable and structured-product vega supply, the other side of MBS vol demand.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): gamma and vega P&L when hedging MBS convexity with swaptions.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread construction and sign conventions.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension, insurer and bank ALM duration demand that competes with mortgage hedgers.
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): trade-repository prints to identify swap-paying and receiving flow.
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): futures positioning to cross-check directional flow.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): repo and implied financing, the same logic as dollar-roll implied financing.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo mechanics behind TBA carry and specialness.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): Fed MBS runoff and reinvestment, which changes who holds negative convexity.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 and key-rate conversions behind the 10y-equivalent measure.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward steepeners and flatteners that carry convexity.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): running flow shocks through a book.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables, including `mbs_tba`, `mbs_pool_stats` and `callable_issuance`.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): conditional steepener betas on sell-offs and rallies.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): directionality-beta regressions, standard errors and errors in variables.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores for the mortgage-minus-CMS and implied/realised signals.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): SLR and LCR constraints on bank receiving and Treasury holdings.
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): Treasury supply that sets the market size for flow-share arithmetic.
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): adversarial review of any trade built on a flow thesis.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): write-up format for a trade idea.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): two-leg curve trades.

## References
- Tuckman, B. and Serrat, A., Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): Ch.15 MBS prepayment, OAD, OAS, TBA and dollar roll; App. A15 dollar-roll restatement; Ch.7 OAS and P&L attribution; Ch.16 callables.
- Golub, B. W. (ed.), BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): Ch.2 drift, empirical duration, key-rate and wave shocks, volatility duration; Ch.4 principal-component durations. Partial read.
- Golub, B. W. and Tilman, L. M., Risk Management: Approaches for Fixed Income Markets (Wiley, 2000): generalised duration, swap-spread duration, FNMA 7% worked example, SEDUR. Partial read (OCR).
- During, A., Fixed Income Trading and Risk Management: The Complete Guide (Wiley Finance, 2021): logistic prepayment model, dollar-roll share, Danish callables, convexity bias.
- BofA Global Research, US Rates Viewpoint: Primer on MBS convexity hedging and the Treasury market (18 Mar 2021): hedge-need recipe, active-share table, flow share of the Treasury market.
- JPMorgan, A comprehensive look at convexity hedging in interest rates (29 Mar 2019): hedger taxonomy, triggers, event windows, peak exposure in rallies.
- JPMorgan, Is bank convexity hedging lying in wait? (31 May 2019): directionality beta, bank balance-sheet duration gap.
- JPMorgan, Dynamic hedgers are long, banks are short, and both are buyers of spreads (13 Sep 2019): dynamic-hedger model and callable offsets.
- JPMorgan, The return of convexity hedging (31 Jan 2020): index convexity, active-hedging test, conditional steepener.
- JPMorgan, Markets struggle to feed the convexity beast (28 Feb 2020): servicers, mREITs, VA writers, spread responsiveness.
- JPMorgan, Will mortgages bail banks out of their duration short? (27 Mar 2020): bank gap, re-couponing lag.
- JPMorgan, What about bonds? SLR relief, Treasury supply and long-end spreads (2 Apr 2020): buyer and seller balance sheet of 10y-eq flows.
- JPMorgan, For cheap gamma, look to the long end (23 Aug 2019): VA and servicer long-end demand.
- Bassman, H. (Credit Suisse), The Convexity Vortex (6 Mar 2013): strike clustering, refinanceable share, coupon regimes.
- Bassman, H., The Largest Volatility Sale Ever (23 Mar 2010): homeowner vega rule, Fed QE as a vol sale, USD vs EUR vol.
- Bassman, H., The Water is Warm in the MBS Pool (1 Jun 2022): OAS against vol sold, constant-maturity mortgage vs CMS spread.
- Bassman, H., A Deep Dive into Mortgage Bonds (3 Nov 2022): MBS as bond minus call, 2022 spread decomposition, pipeline and P/S spread.
- Bassman, H., Leverage is NOT a four-letter Word (26 Jan 2023): MBS vs Treasury convexity and duration pair.
- Bassman, H., Awakening the MBS Convexity Beast (20 May 2026): refinancing trigger, index-level convexity.
- Bassman, H., Forwards are NOT a Prediction (12 Aug 2013): belly vega and 2013 taper flows.
- Merrill Lynch RateLab, Professional Javelin Catching (16 Feb 2007): implied/realised 107% fair value, FASB 156 effect on belly vol.
- Merrill Lynch RateLab, The "Positive Carry" Hedge (31 Oct 2008): forwards as DPV, vol-surface inversion from flows.
- Citi Research, Agency MBS Weekly: The Summer Lull (21 Aug 2026): fair-value OAS band, scenario grid, coupon screen.
- Citi Research, US Rates Vol Lab: Gamma and Vega RV (14 Jan 2019): vega PCA z-scores (source inconsistency noted).
- Citi Research, Time for moderation (17 Feb 2023): 5nc3m Bermudan callable and its offset to mortgage convexity.
- Citi Research, Rates Vol Lab: Fading vega dislocations (5 Oct 2026): MBS floaters with fixed caps, vega in 3y10y notional terms. Partial read.
- Barclays Research, The urgency question (2 Oct 2026): self-limiting convexity flows, asymmetry of rallies and sell-offs.
- Barclays, Interest Rate Derivatives: Swap spreads, the bright spot in US rates (30 Sep 2026): $40-50bn 10y-eq per 25bp.
- BofA Global Research, US Rates Viewpoint: Primer: Fed policy plumbing, '25 edition (8 Jul 2025): QT caps and MBS reinvestment.
- BofA Global Research, UK Rates Viewpoint: Back to school (5 Sep 2024): UK mortgage hedging and the 3s5s7s belly.
- BofA Global Research, FX-SOFR primer (31 Oct 2023): AUD and NZD bank term funding and basis.
- JPMorgan, Cross currency basis 2H25 Outlook (5 Jun 2025): JPY lifer hedging and 20s30s floors.
- Citi Research, US Rates Weekly: All it takes is a little push (4 Oct 2019): swap-spread regression fragility.
- Nasdaq, mortgage bond futures product sheet (Apr 2024) (external): SEK mortgage-bond futures listing.
- Treasury Borrowing Advisory Committee, Charge: Swap Spreads (Feb 2021): GSE and Fed effects on payer demand, regression with regime residuals.
- Nordea Markets, Bonds & bold: The one you don't like to read but need to read (5 Nov 2021): Danish callables against straddles. Partial read.
- Citi Research, Forward steepener and vol divergence (12 Jun 2023): forward-steepener convexity and breakeven/realised ratio. Partial read.
