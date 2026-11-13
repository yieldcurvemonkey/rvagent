# Regulatory discount curves and solvency mechanics

The constraint that turns liabilities into hedging flows. `scripts/alm_hedge_flow.py regcurve` implements the
extrapolation below. Parameters change by regulation, so always cite the date of the number you use.

## Solvency II (EEA insurers), revised regime effective 30 Jan 2027
Source: Citi Research, European Rates Weekly: What to do about OATs? (1 Oct 2026) for the formulas, and Citi
Research, European Rates Weekly: A QT revolution (17 Sep 2026) for dates and calibration. Legal basis: Directive (EU)
2025/2 and Delegated Regulation (EU) 2026/269, which amend Directive 2009/138/EC and Delegated Regulation (EU) 2015/35.

**Balance sheet**
```
TP_0 = BEL_0 + RM_0                       technical provisions = best-estimate liabilities + risk margin
SR_0 = OF_0 / SCR_0 = (A_0 − TP_0 − OL_0) / SCR_0
SCR calibrated to a 1-year 99.5% confidence level
```
Rates move BEL (PV of liability cash flows). Credit spreads move assets, and they move liabilities through the
VA or MA. A duration mismatch consumes capital, and diversification relieves it.

**Risk-free curve and extrapolation**
- The First Smoothing Point (FSP) replaces the Last Liquid Point (LLP). For EUR it stays at 20y, so the curve is
  unchanged up to 20y. The FSP is the longest maturity that passes the deep-liquid-transparent (DLT) test and the
  residual-volume criterion.
- Beyond the FSP: `f(h) = w(h;α)·LLFR + (1 − w(h;α))·UFR`, where h = years beyond the FSP, `w(0;α) ≈ 1` and
  `w(∞;α) = 0`.
- The LLFR is a liquidity-weighted average of the forward immediately before the FSP and DLT forwards beyond it.
  Market rates therefore start to move the 20–60y discount rates. Under the old Smith-Wilson method those rates were
  pulled toward the UFR.
- UFR: 3.30% for EUR, updated annually by EIOPA.
- α: the final value is 0.11 for all currencies ex SEK. With supervisory approval the phase-in starts at α = 0.20 and
  falls linearly each year until 2032 (Jan 2027 → Jan 2032). A lower α means slower convergence to the UFR and more
  weight on the LLFR.
- Functional form of w used in the script: `w(h;α) = (1 − e^(−αh)) / (αh)`. This is EIOPA's alternative
  extrapolation weight, and it applies to the average forward from the FSP to FSP+h (external: EIOPA technical
  documentation of the risk-free rate methodology). It satisfies the two limits above. Check the current EIOPA
  technical documentation before using it for anything beyond sizing.
- Rates implication (Citi): "market rates will affect forward rates starting after the FSP". Hedging needs between 20y
  and 60y now depend partly on market rates rather than only on the UFR, so receiving may extend longer. The phase-in
  makes it gradual and orderly. Discount-curve effects phase in over 5 years.

**Volatility Adjustment**
```
VA       = 0.85 · CSSR · RCS                                (application ratio 0.65 → 0.85)
RCS      = w_gov · RCS_gov + w_corp · RCS_corp              (reference portfolio from supervisory reporting)
Adj      = min(1.05, RCS_insurer_portfolio / RCS_reference)  (quality-overshooting adjustment, insurer-specific)
VA_macro,i = 0.85 · CSSR_EUR · max(RCS_i − 1.3 · RCS_EUR, 0) · w_i   (country trigger at 130% of EUR RCS)
```
- CSSR is the insurer-specific credit-spread sensitivity ratio: the sensitivity of assets relative to liabilities to
  a 1bp spread widening. When asset and liability sensitivities are equal, the full VA (× 0.85) is recognised. If
  liabilities are more sensitive, the VA shrinks. In practice this rewards matching liability duration with
  spread-bearing bonds rather than swaps.
- EA govvie risk correction is countercyclical. The share of each extra bp of sovereign spread that survives into the
  RCS is 70% below the long-term average spread, 80% between 1× and 2× the long-term average, and 85% above 2×.
- The Macro VA and the insurer-specific adjustment cannot be combined.
- The MA is not fundamentally redesigned. It recognises spread earned on a cash-flow-matched assigned portfolio.
- Market reading: govvies, including riskier EGBs such as BTPs for Italian lifers, become "considerably more palatable
  than swaps from an ALM perspective". The authors call the VA the most important change for long EGB/SSA demand.

**Risk margin**
```
RM_0 ≈ CoC · Σ_t λ_t · SCR_t / (1 + i_t)^(t+1)       λ_t declines exponentially with t to a floor
```
- The CoC falls from 6%. The 17 Sep 2026 note says 4.75% and the 1 Oct 2026 note says 4.5%. Verify against the
  Delegated Regulation before using either.
- λ_t makes the RM less rate-sensitive, which "reduce[s] the need to receive long-end swaps". The RM is ~2.5% of
  technical provisions on the EMU-11 average (Dec 2025): Austria 4.9%, Portugal and Italy 1.4%. Austria, Belgium,
  the Netherlands, Greece and Spain gain most. Of those, only Belgium is a top-5 govvie holder.

**How to use it**
1. Build the regulatory curve for the liability currency: market zero to the FSP, then the extrapolation for the
   current year's α.
2. Run `regcurve` for the current α and for α in later phase-in years. The difference in `dv01_llfr` is the extra
   market-hedgeable DV01 that the phase-in creates. `dv01_ufr` is the part with no market hedge.
3. Map `dv01_llfr` onto the LLFR's component forwards, using the weights in the current EIOPA documentation, to locate
   the tenors that receive. Compare the result with sector liability DV01 from supervisory data, if the user supplies
   it.

## Dutch pensions
- Market-rate discounting with a UFR blend. The Dutch UFR was 4.2% in 2012, later revised to 3.9%. A fund holding risk
  assets must buy duration when yields fall, a regulatory short-convexity (Düring, Fixed Income Trading and Risk
  Management, 2021).
- The 2012 FTK II/DNB curve reform moved discounting toward market rates for 20y+ and created persistent 15y5y vs 25y5y
  residuals (Credit Suisse, PCA Unleashed, 24 Oct 2012).
- The transition to the new contract runs by cohort on 1 Jan dates. It lowers interest-rate hedge ratios, so swaps are
  paid on unwind (~€400mn DV01 over ~2 years per JWS Macro, 4 Sep 2025). Before transition, funds may receive into
  year-end to protect coverage ratios (Nordea, 26 Sep 2025). DNB quarterly coverage-ratio and hedge-ratio data is the
  check.

## UK DB pensions and insurers
- LDI hedges liabilities with long gilts, index-linked gilts and swaps, often levered. Leverage creates margin and
  collateral calls in sell-offs, which can force selling (Sep 2022). BPA transfers liabilities to insurers, who switch
  part of the gilt and linker holdings into USD credit hedged with long xccy (see the investor map).
- No formula-level detail in the source library. Ask for the user's sector liability profile and hedge-ratio data.

## US corporate DB pensions
- Liabilities are discounted on a high-grade corporate curve (Tuckman & Serrat use an HQM-style corporate par curve).
  Liabilities therefore move with Treasury yields and AA credit spreads. Funded ratio = assets / liabilities.
- Nowcast (J.P. Morgan, Issuance, pensions, and long-end spreads, 14 Sep 2018): a 3y regression of 1-month % changes
  in top-100 plan assets and liabilities on 1-month changes in swap rates and the AA corporate index spread, plus the
  S&P 500 % change for assets only. An auxiliary regression of S&P changes on 30y swap changes gives the expected
  equity move for a pure rates scenario. `nowcast` implements the first stage. Pass the equity move explicitly.
- Shock mapping (BofA, UST supply & demand in '25, 26 Nov 2024) has three parts: the historical rates → liability-
  valuation relation, the fixed-income allocation at the end of the last fiscal year, and rates → IG credit returns as
  the FI-return proxy. Result: a 10y rally of ≥ 50bp pushes funded status below 100%.
- Tuckman & Serrat stylized liability (Fixed Income Securities, 2022): payments start at $2mm semiannual, peak at $4mm
  in year 10 and fall to 0 by year 60. PV ≈ $140mm, duration 16.66, convexity 211.37. Use it as a default illustrative
  profile when the user has none, and label it.

## Japan life insurers
- An economic-value-based solvency regime, scheduled for 2025 when BofA wrote in 2022, is cited as a driver of Jan–Mar
  super-long buying (BofA, Bond market seasonality explained, 6 Jun 2022). Confirm its current calibration with the
  user's sources. ESR 215%, and +50bp in JPY rates costs ~ −8pt (J.P. Morgan, Global
  Fixed Income Markets Weekly, Aug 2026).
- Guarantee target yields drive target buying above the pivot (Düring, 2021).
- Banks: IRRBB dEVE limits are 15% (internationally active) and 20% (domestic) of capital. The average used was 5.3%
  (6.0% capital-weighted), so there was capacity of ~¥90.6tn 10y-eq (J.P. Morgan, Global Fixed Income Markets Weekly,
  Aug 2026).

## Smith-Wilson / UFR in curve tools
Parametric families used for regulatory curves include Smith-Wilson (UFR extrapolation, and solving for the UFR
implied by a yield). See `fi-curve-construction`. Smith & Wilson (2001), "Fitting yield curves with long term
constraints" (Bacon & Woodrow research note) (external), is the original method.
