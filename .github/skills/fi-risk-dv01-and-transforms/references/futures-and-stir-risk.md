# Futures, STIR and short-end risk: DV01, hedge ratios and meeting risk (detail)

House signs: DV01 positive = long duration (long future, receive fixed). Contract specifics (CF, CTD, delivery
options) live in [fut-bond-basis-and-implied-repo](../../fut-bond-basis-and-implied-repo/SKILL.md) and
[fut-ctd-switch-and-delivery-options](../../fut-ctd-switch-and-delivery-options/SKILL.md); this file is the risk-unit
layer only.

## 1. Bond futures

**DV01 of the future** = forward DV01 of the CTD / CF (rule of thumb; F ~ CTD forward price / CF at expiry). Use the
forward DV01 to the end of the delivery month under the same curve-move assumption as the hedged bond (Salomon
Brothers, Understanding Treasury Bond Futures: Questions and Answers, Oct 1990). Per contract:
`contract size x (BPV_CTD / 100) / CF` (Aikin, STIR Futures, 2nd ed., 2012).

**Hedge ratio** of a bond (or portfolio) with futures: `N = DV01_bond / DV01_fut = CF_ctd x BPV_bond / BPV_ctd`.
For the CTD itself the ratio is its CF, so a 1:1-notional cash-and-carry carries rate risk.

- 10y-note future, $10mm 2-3/8 May-27 (BPV $8,558) vs CTD 2-3/8 Aug-24 (BPV $63.78 per $100k, CF 0.8072): HR =
  0.8072 x 8,558 / 63.78 = 108.31, sell 108. A CF-only ratio (0.7455) would give 75 (CME Group, Understanding Treasury
  Futures, Nov 2017).
- Portfolio $100mm, BPV $80,000, duration 8: sell 80,000 / (63.78/0.8072) = 1,012 contracts; cut duration 8 -> 6:
  (6-8)/8 x 1,012.48 = -253.1. Re-evaluate after about 20-25bp (BPV falls as yields rise).
- BPV per $1mm, 30 Oct 2017 (duration / BPV): 2y 1.978/$196; 3y 2.896/$287; 5y 4.783/$473; 7y 6.516/$645; 10y
  8.794/$863; 30y 20.241/$1,946 (same source). 10y is about 4.4x the risk of 2y, not 5x.
- Futures add price exposure but no market value: augmented duration
  `MD = [MD_raw x MV_raw + MD_fut x PEV_fut] / MV_raw`, PEV = futures price x contract par ($1,000 x price for
  bond/10y/5y, $2,000 x price for 2y). Target duration: `N = (target - current) x MV / (MD_fut x PEV per contract)`.
  $1bn at MD 3.0% -> 2.0% with 5y futures (OA duration 4.09%, PEV $105,687.50): -2,313 contracts (Burghardt et al., The
  Treasury Bond Basis, 3rd ed., 2005).

**Rule-of-thumb DV01 is a step function; use a smooth version near CTD crossovers.**
- Below the crossover RoT understates DV01 (overhedged), above it overstates; RoT DV01 jumps at the cusp. Option-
  adjusted (OA) DV01 = central-difference slope of theoretical futures prices across yield shifts. 4 Apr 2001 June
  contracts (RoT / OA vs CTD yield / OA vs OTR yield / repo DV01): 2y 38.63/39.06/39.07/-5.06; 5y 42.84/43.20/43.20/
  -2.50; 10y 60.76/66.13/69.75/-2.53; bond 121.86/122.42/132.92/-2.46. RoT 10y is about 8-9% below OA (60.76 vs 66.13), so it over-hedges; **state the
  reference yield** (CTD vs OTR differ by 5% at 10y and 9% at the bond).
- CTD-probability-weighted BPV/CF = `sum_bonds P(CTD) x BPV/CF`: smooth in yield versus the RoT jump; recommended for
  hedge ratios (J.P. Morgan, The switch and the spur, 29 Oct 2026). Dec-2026 classic bond contract (BPV of CTD / BPV/CF / P-weighted): 6.00%:
  853/1,382/1,452; 6.10%: 706/1,675/1,518 (RoT jumps 1,382 -> 1,675). Two forces: a switch to a higher-duration CTD raises
  BPV discontinuously, convexity lowers it. The ultra-bond contract has milder jump risk (6.27%: 759/1,466/1,463) because its deliverables are alike in
  BPV/CF.
- Size of a switch (CF-adjusted DV01 jump, J.P. Morgan, Eurex CTDs wobble with higher yields, 2 Oct 2026): Buxl DBR
  2.5% Aug-54 1,391/0.751530 = 1,851 vs DBR 0% Aug-52 925/0.365252 = 2,532 (+37%); OAT 3.7% Nov-36 870 vs Nov-35 806
  (-7%); BTP 3.65% Aug-35 780 vs 3.8% Jul-36 844 (+8%); Schatz/Bobl/Bund switch risk minimal.
- Futures can be negatively convex near switch yields even if every deliverable is positively convex: a DV01-neutral long
  future / short bond position loses on every rebalance; do not compute a stand-alone modified duration for a future.
- Quality-option time decay: as delivery nears the futures DV01 drifts to the likely CTD's converted DV01 with no rate
  move. After notification the P&L is the actual DV01 of the delivered bond times the amount (large step when CFs are far
  from 1). After the last trading day switch from CF-weighted to face-matched.
- "BPV-neutral calendar roll": when front and back CTDs differ, roll with BPV-weighted ratios.

**Spot vs repo DV01 of the CTD** (Burghardt, 7-5/8% 11/22): spot DV01 145.45 per $100k; forward DV01 = 1.0106 x spot =
146.99; repo DV01 -2.88 per $100k (report negative). With futures use the 0.9895 spot/forward factor. Term repo and spot
yields are almost uncorrelated weekly (R^2 0.025 / 0.011 / 0.0018 at 5y / 10y / 30y), so hedges carry separate stub-
repo risk, largest at 2y; best practice is a two-factor hedge (repo with short instruments, forward yield with long).
Forward-yield DV01 = spot DV01 + repo DV01; a compromise assumes repo moves 30% of spot: DV01 = spot + 0.3 x repo
(2.875s28: spot 0.0708, forward 0.0666, repo -0.0042 -> 0.0695) (Tuckman and Serrat, 2022).

**Tailing**: reduce contracts by the PV factor `1/(1 + r d/360)` to the hedge horizon (variation-margin interest);
Euribor example below. A CF hedge locks in the cash-and-carry IRR, a DV01 hedge needs adjusting but its return varies
less; if the bond's ModD is below the CTD's, CF weighting needs more contracts than DV01 weighting.

**Four hedge ratios** (long $100mm OTR 30y, hedged by shorting 5y; columns: 5y sold in $mm, daily SD in $k, net DV01 in $k, Burghardt et al., 2005;
weekly correlations 1990-97: 30y/10y 0.97, 30y/5y 0.88): conventional DV01 341.2mm sold (SD 462.5, net 0); yield delta
310.9 (415.8, 13.2); yield beta 273.6 (377.4, 29.5); minimum variance 240.7 (365.9, 43.9). Formulas with `beta =
sigma_5 / sigma_30` scaling: conventional `DV01_30 / DV01_5`; yield beta `DV01_30 / (DV01_5 x sigma_5/sigma_30)`; yield
delta adds `/rho`; minimum variance multiplies by `rho`. Minimum variance has the lowest SD but leaves a net bullish
position; conventional suits spread trading. Yield betas are unstable (OTR 10y beta 2.88 in 1991, 0.46 in 1993), so
never use them without re-estimation. Beta by duration: fitted SD/beta 2y 1.0721/1.313, 5y 0.999/1.224, 9y 0.9016/1.104,
12.5y 0.8164/1.000.

**Cash-settled yield-formula futures (AUD)**: value = `1000 x [(C/2)(1-(1+R/200)^-20)/(R/200) + 100(1+R/200)^-20]`, R = 100 -
price, C = 6 over 20 half-years for the 10y (the 3y contract uses a 6-half-year schedule). DV01 = average of +-0.01 price bumps; it varies with the
rate level: A$89.65 at 4%, 81.63 at 5%, 74.39 at 6%, 67.85 at 7%, 61.93 at 8% (Burghardt et al., 2005). European and
Japanese bond futures have no timing option; JGB deliverables (7-10.5y basket) have near-identical BPV so CTD
switches are common yet the one-factor delivery option is about zero.

## 2. STIR futures

**Contract BPV**: `notional x 0.0001 x days/360`. 3M SOFR and 3M Euribor futures: 1,000,000 x 0.0001 x 90/360 = 25 per bp
(USD 25 / EUR 25); 1M SOFR (and fed funds-style) average-rate contract: USD 5,000,000 x 0.0001 x 30/360 = 41.67. Euribor
tick 0.005 = 0.5bp = 12.5 per tick. Equivalence: 100m for 3 months = 100 3M contracts = 60 1M contracts. The ICS
package 3 + 3 1M vs 10 3M is BPV-neutral (6 x 41.67 = 250.02 vs 250).

**Hedge a period exposure**: contracts = `notional x 0.0001 x d/360 / BPV_contract`; for a strip, period n:
`N_n = [Notional x DP/100 x 0.0001 x DF_n x days_n/360] / BPV` (DP dirty price when hedging a bond).
- 62-day EUR25m exposure: 25m x 0.01% x 62/360 = 430.56 -> /25 = 17.22 -> x beta 1.05 = 18.08 -> x tail 0.9924 (3% rate,
  D_h 60, D_b 62, B 360; tail = `1/[1 + i x ((D_h/2 + D_b)/B)]`) = 17.94 -> sell 18 (Aikin, 2012).
- Schatz BPV 0.0192: EUR10m -> 1,920/25 = 77 Euribor; Schatz H2 CTD BPV 0.0191, CF 0.906868 -> 21.02 per contract; 84
  Euribor per 100 Schatz. Round hedge ratios DOWN for strip-vs-bond-future hedges (bond-future BPV falls as the CTD
  ages); compare forward vs spot BPV.
- Averaging 1M contracts: `N = Notional x days in month / (5mm x 30)`; a hedge from inside a month to month-end is
  constant through the month; a start-to-mid-month exposure declines within the month (Tuckman and Serrat, 2022).

**Hedging a swap with a 3M strip by bump and reprice** (CME Group, Pricing and Hedging USD SOFR Interest Rate Swaps with
SOFR Futures, 4 Jun 2025): bump each future 0.01 in turn, reprice at the original coupon; contracts = dPV / USD 25.
Receive USD 100mm 2y IMM OIS at 3.3304%: sell 100, 99, 99, 98, 97, 96, 95, 95 = 779 (more than 100 per leg is
the money-market convention, fewer further out is discounting); bumping all: dPV 19,480.69 vs 779 x 25 = 19,475. The
shortcut "parallel PV01 / 25 split equally" is valid only when DFs are about 1 and worsens with rate level and tenor.
Realistic OIS needs: ACT/360 on both legs (multiply the coupon by 365/360), 2-day payment lag (extend discounting),
annual payments (decompose DF into 3M segments), bump daily SOFR inside each quarter (moves numerator and
denominator), and the front contract's divisor is not 25 because part of its quarter is known (use `R_unknown =
[(R D/360/100 + 1) / prod_known(1 + SOFR_i d_i/360/100) - 1] x 360/D_unknown x 100`; the front 3M contract carried 0.8384 of
its full sensitivity in Huggins and Schaller, SOFR Futures and Options, 2022).

**Futures vs swap convexity** (CME, 2025): futures DV01 is fixed (USD 25 per 3M contract), swap DV01 varies with the
level; receive fixed + short futures = long convexity, pay fixed + long futures = short convexity. P&L ~ 0.5 x d(hedge
contracts) x d(bp) x USD 25. Receive USD 100mm vs short 779: net P&L at -10/-25/-50/-100bp +253 / +1,451 / +5,638 /
+22,292; at +10/+25/+50/+100bp +182 / +1,269 / +5,241 / +21,226 (at -100bp DV01 grows 19,480 -> 19,921, hedge 779 -> 797;
approx 18 x 0.5 x 100 x 25 = 22,500). The swap rate must be below the futures-implied rate (premium for the embedded
option). Growth is non-linear in the move and assumes parallel futures moves. See
[stir-convexity-adjustment](../../stir-convexity-adjustment/SKILL.md).

**FOMC-neutral hedges** (Huggins and Schaller, SOFR Futures and Options, 2022): the 3+3 : 10 ratio of 1M to 3M is
neutral only when the meeting is mid-way through the 3M contract. Two-step ratio: with 3M level sensitivity `s_l` and jump
(meeting) sensitivity `s_j`, 1M sensitivity to a hike in the month after the meeting = `d_post/d_month x 41.67`;
`n_post-month = s_j / ((d_post/d_month) x 41.67)` neutralises the jump, `n_other = s_l/41.67 - n_post` the level.
Example long 1 Mar-22 3M future, meeting 4 May 2022: s_l 25.02, s_j 11.27 USD/bp; May 1M jump sensitivity (27/31) x 41.67 =
36.29; n_May = 0.31, n_Apr = 0.29: sell 3.1 May + 2.9 Apr 1M per 10 3M (vs 3+3). A 25bp hike on 4 May moves May 1M by
25 x 27/31 = 21.8bp and the Mar-22 3M by 11.3bp. General hedge of a term rate: parameters = start level + one jump per
meeting; sensitivities of target and candidates to each parameter; choose a square (or over-determined, robustly checked)
set and solve. Avoid contracts with few post-meeting days (exploding ratios), include a 3M, check across instrument sets.
Date mismatch dominates hedge error (about 4% with matched 1M strip vs more than 100% overhedge with a mismatched 3M); close
the hedge at the end of the exposure. A futures-strip hedge of Treasuries works only while Treasury ASW vs SOFR is stable
(Mar 2020: -328k, about 20% of the hedge, as ASW widened).

**CB01 (meeting-step Jacobian)** (Lehman Brothers, The Short-End of the Curve, 10 Jul 2007): DV01 on short OIS around
a meeting misstates risk; size meeting trades by the PV change for 1bp in the expected meeting outcome. Build the
step curve with each meeting date changing the overnight rate: `(1 + R_j (T_j-t0)/D) = prod_i (1 + r_{i-1}/D)^(t_i - T_{i-1}) (1 + r_i/D)^(T_i -
t_i)`, differentiate to get `dR_j/dr_k`, hedge with OIS notionals `n = J^-1 c`. AUD, 10 Apr 2007 (position sized at USD 100k of exposure, AUD/USD 0.8165): CB01 AUD 11,134
per bp, hedged by paying AUD 4.563bn of 1M OIS, while the DV01 (AUD 38,323) overstated meeting risk by 244%. Step-
based bucketing (meetings to the 2nd, then usual buckets) and traditional (deposits/futures/swaps) agree from about the
4th future; traditional overstates the deposit region (AUD 1bn: -19,736 vs -14,781).

**RFR fixing exposure as a standardised notional** (Darbyshire, Coding Interest Rates): the notional of a one-business-day
period on that fixing alone, `N_i = N (d v)/(d_i v_i) x dr/dr_i`. Weekend fixing at USD 10/bp, DF 1, ACT/365: N = 10 x
10,000 x 365/3 = USD 12,166,667. Table (1mm, 3-10 Feb 2022, 4.03%): payment delay 1,000,000..1,000,671; observation
shift (3) 999,665..1,000,112; lockout (2): the locked-out rate carries about 3x (3,001,342); lookback (3) shows x3 and /3
around weekends (2,998,658 and 333,445). Lookback and lockout create lumpy, hard-to-hedge fixing exposures; real payment
lags are SONIA 0, ESTR 1, SOFR 2 business days. See
[stir-rfr-compounding-and-fixing-risk](../../stir-rfr-compounding-and-fixing-risk/SKILL.md).

**Exact hedge of a model-defined term rate**: rebuild the administrator's step curve exactly, central-difference the payment
to each of the 18 input prices (+-5bp), and hold the opposite sensitivity (USD 100m 2y loan example: net sell 45 1M + 25 3M;
stress +25bp after the March meeting: payment +63,263 vs hedge +62,830, miss 0.7%).

## 3. Carry and size in DV01 units

Compare carry and trade sizes in DV01, not notional (an apparent contradiction between a per-notional and per-DV01 view
disappears: 0.25 x (S5y - L3m) = 4.75 x (F - S5y), where 4.75 becomes the forward-swap DV01 once discounting is included).
For a DV01-neutral spread, leg rolls in bp add without scaling; absolute and relative carry/roll are linked by DV01 (a
10bp roll = 10 x DV01). Carry DV01 over 6 months includes the 0.5 accrual fraction. See
[fi-carry-and-rolldown](../../fi-carry-and-rolldown/SKILL.md).
