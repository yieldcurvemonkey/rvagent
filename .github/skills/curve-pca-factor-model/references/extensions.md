# Extensions of the curve PCA

Each item is a variant of the core method in [SKILL.md](../SKILL.md). Residual convention: actual - model. Yields and spreads: + = above model = cheap (receive/buy). Vols: + = vol above model = rich (sell); publishers differ, state yours.

## 1. Vol-surface PCA ("relative value only")
- Fit 3 PCs to the ATM normal-vol surface (expiry x tail) on a 2y window (3y in an older note); rich/cheap = residual in normal-vol bp with a z-score. "By design, this
  framework only yields relative value" - it cannot say the whole surface is cheap (Citi, Rates Vol Lab, In search of cheap vol, 17 Jan 2020; Liquidity, vega, and convexity,
  30 Mar 2020). Curve-vol (CMS spread option) surface: 2 PCs on 3y (Citi, Vol cycle, steepeners, and SOFR, 25 Mar 2019).
- **Rates-anchored companion ("macro-vol")**: regress each ATM vol on the first 3 PCs of the swap curve; residual and z = level-aware rich/cheap. A point rich on both is
  stronger (USD 6m10y 0.4 sigma rich on macro-vol, 1.1 sigma on PCA; Citi, 17 Jan 2020). Sample by regime: USD 1996-2008 spliced with 2017+ (exclude ZLB), EUR 2016+
  (negative-rate regime); the model is "broken with near zero Fed Funds (<= 50bp)" (Citi, Fair value vs seasonality, 1 May 2017).
- **De-directionalise**: vol PC1 is directional with rates (sigma_N ~ F x sigma_B), so selling vol at residual > +1 sd is a hidden rates trade. Regress the first 2-3 vol PCs on
  the PCs of the forwards, map fitted PCs back to tenors with the transposed PCA matrix, and trade the residual (BofA, US Vol Primer, 11 Mar 2024).
- **Hierarchical PCA**: five static clusters on the ATM grid (short-expiry/short-tail, short-expiry/long-tail, long-expiry/short-tail, intermediate vega, long-expiry/long-tail),
  HPC1 = parallel grid level (directional), HPC2 = gamma vs vega, HPC3 = left vs right of the grid (BofA, 11 Mar 2024; BofA, Understanding Principal Components, 21 Aug 2020).
- Vega-sector PCA of JPY swaptions (weekly 2009-2011): F3 (tenor slope) was the only good RV factor (fast reversion, little correlation to F1/F2); F1, F2 revert slowly and are
  correlated in sub-periods (Huggins & Schaller, 2024). Surface PCA is less stable than curve PCA: PC2/PC3 often swap. Readings and trades: see `vol-rates-options-rv`.

## 2. Macro layer on curve PCs
Regress PC1 and PC2 of the UST curve (2s/5s/10s/30s) on policy rate and PCs of growth, inflation and employment data; calibrate over 7-15y (longer than a cycle); map fitted PCs
back through the inverse PCA to yield fair values; add central-bank balance sheet and global-DM PC1 to adjust for non-economic demand (BofA, Monthly rates models, 7 Apr 2025,
4 Aug 2025). R^2 about 90%+ for both PCs, residual sd about 35bp front end and 20-25bp back end (BofA, A new UST macro framework, 15 Oct 2024). See `macro-fair-value-models`.

## 3. Spread curves and cross-sections
- Swap-spread curve, EGB spreads, OIS/UST spreads: PCA on the spread panel, residual to the first 2 PCs (swap spreads) or first N PCs (42-series EGB panel), dislocation
  index = RMS or cross-sectional std of residual z; act only above a threshold and trade the cheapest vs richest (BofA, 2016, 2018). Numbers in
  [worked-examples.md](worked-examples.md) section H. See `spread-swap-spreads-and-asw`, `spread-cross-market-govies`.
- Off-the-run vs on-the-run: residual of the 10y OFR yield on 3 PCs of the on-the-run curve; a wide dislocation signals balance-sheet stress (Citi, US Rates Weekly, Eat, pay,
  spend, 27 Mar 2020).
- Cross-market: PCA on G10 central-bank hawk-dove scores, regress each forward on PC1/PC2 plus own-economy scores; PC1 explains 54% (JPM, Talk is Cheap, 30 May 2024). PCA on 1y/5y
  cross-currency bases: PC1 = broad USD scarcity (1y 72%, 5y 93% variance), PC2 = relative monetary policy; front-end factors are dominated by domestic drivers (JPM, xccy 2H25 Outlook,
  5 Jun 2025). See `xccy-basis`.
- Credit-adjusted input: PCA on yield minus CDS removes PC1-PC2 correlation after credit regime shifts and reverts faster in PC2; Italy 2y-10y CDS curve is single factor (PC1 99.5%), so no
  curve RV there (Huggins & Schaller, 2024). Core EUR CDS PC2 trade 1.4 AT per FR, 42bp potential (26 Sep 2012).

## 4. Sparse and mean-reverting baskets
Smallest-eigenvalue "PCA baskets" are maximally mean-reverting but low-variance with wide support, so costs dominate. Box-Tiao/greedy sparse decomposition (3-5 legs capture most of the
mean reversion): best k = 3 on 1y-30y USD swaps was 3y -0.288, 4y 0.806, 5y -0.517; out-of-sample protocol: 200-day estimation window re-estimated every 50 days; a 1bp bid-ask neutralised the convergence trade
(d'Aspremont, 2008). Use a variance floor (0.2-0.3 x median asset variance) and cardinality cap 30-50% of the universe (Cuturi & d'Aspremont, 2015). When PCA is not enough (horizon-dependent
correlation, nonmonotonic reversion) use a multivariate OU (Huggins & Schaller, 2024); see `quant-mean-reversion-ou`.

## 5. Scenarios and plausibility
- Shocks in sd units of PC1/PC2 (parallel, slope, combo); factors shown in bp per 1 sd, e.g. 4 sd of PC1 on a 25-30y basket about 22.6bp (RiskVal, Future CTD Scenario Analysis user guide,
  25 Apr 2024). Use for CTD-switch scenarios (`fut-ctd-switch-and-delivery-options`) and stress (`port-scenario-and-stress-testing`).
- Shock probability: `sigma(xi) = sqrt(xi' Sigma xi)`; z-score of a shock `|z| / sigma(xi)`. 31 Jan 2020 1-sd parallel shock 60bp/yr (so 150bp = 2.5 sd, probability 0.00621);
  typical 1-sd parallel range 75-110bp (Golub, 2023). Magnitude plausibility = 2 x P(N >= |S|); shape plausibility compares the contribution vector with the explanatory powers
  (Golub & Tilman, 2000). A steepener shock is historically implausible (shape plausibility 30-45% vs 80-90% for PC1/parallel).
- Risk measures beyond one limit per PC: invariant delta and gamma norms, tail mixture, flylets (Musaelian, Nagarajan, Villani, SSRN, 2016).

## 6. Positioning and nowcasting
- Return-based PCA regression: PCA of standardised UST/MBS/IG returns and 2y10y change over a rolling 2-month window, regress fund returns on the kept PCs, map betas back; signal =
  fund beta minus benchmark beta, z-scored; lags because of the 2m window (BofA, Fund duration & curve positioning, 4 Jun 2024).
- Conditional-MVN nowcast of a whole curve from a few live quotes (practitioner code notes, unpublished): prior f ~ N(0, Lambda); posterior precision L_o' N^-1 L_o + Lambda^-1; flag nodes whose quote
  deviates.
- Realised PCA for intraday data: jump-truncated spot covariance, bias-corrected eigenvalues; the eigenvectors of the integrated covariance are not the integrated PCs unless
  the covariance is constant (Ait-Sahalia & Xiu, JASA, 2019). Only for liquid futures strips with synchronous 1-minute data.

## 7. Hedging and sizing notes
- Principal-component durations: pcdur_i = -(1/P)(P_up - P_down)/2 for a 1-sd PC shock; PC1-duration-neutral beats OAD-neutral before high-vol events; on 30 Sep 1996 PC1 93% vs parallel 88%,
  so the non-parallel part of PC1 equals PC2 in power: duration-neutral curve trades need at least 2 PCs (Golub & Tilman, 2000).
- Swaption/conditional curve trades use BPV-neutral not PCA-neutral weights: PCA neutral removes the directionality that the option structure is meant to exploit (Huggins & Schaller, 2024).
  See [curve-conditional-trades](../../curve-conditional-trades/SKILL.md).
- Dealers hedge swap risk with three benchmarks: 10y (level), 5s10s (slope), 5s10s30s (curvature); 5/10/30y hold 62-64% of swap DV01 in USD and EUR (Clarus, The Principals of
  Swap Trading, 1 Jul 2014).
