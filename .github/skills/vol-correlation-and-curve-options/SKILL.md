---
name: vol-correlation-and-curve-options
description: "Prices and trades the correlation embedded in rates options. Backs implied correlation out of CMS spread (curve) option vols and midcurve swaption vols against their vanilla leg vols (normal model), compares it with realized correlation, and ranks rich/cheap with z-scores and regression/PCA residuals. Covers curve caps/floors and straddles (YCSO), curve-cap calendars and forward curve vol, midcurves and listed STIR midcurves vs vanillas, FVA via midcurves, correlation (dispersion-style) trades, hybrid/contingent rates options (payer contingent on equities), and rates-vs-FX vol RV. Use when a trader asks: is 2s10s or 5s30s curve vol rich, what correlation is the curve cap pricing, curve cap vs conditional steepener, spread option, spread vol, 1y5y5y or 2y1y midcurve cheap to vanilla, midcurve implied correlation, forward vol from midcurves, contingent or hybrid tail hedge, correlation sale, dispersion, implied vs realized correlation, swaption vol vs USDJPY vol, EUR vs USD curve caps."
---

# Correlation, curve options and midcurves

A curve (CMS spread) option, a midcurve swaption and a hybrid each price a correlation that is quoted nowhere
else. Given the vanilla vols of the legs, every spread or midcurve vol maps one-to-one to an implied correlation.
The RV is that implied correlation against realized correlation, against its own history, and against the rest of the
surface. It moves because demand hits the spread product while vanilla vols stay put: curve caps bought as
steepener or recession hedges, midcurves used for Fed-path trades, structured notes that leave dealers long spread
vol. Correlation is also cyclical: it peaks when the curve is flat and falls as the curve passes an inflection point,
so spread vol is cheapest just before the cycle turns (Merrill Lynch RateLab, Yield Curve Options, Dec 2006).
The leverage is high: one point of correlation is worth 1-2bp of spread vol on a 20-40bp spread vol.

## When to use
- "Is 2s10s / 5s30s / 10s30s curve vol rich or cheap?" "What correlation is this curve cap pricing?"
- Choosing between a curve cap/floor and a conditional steepener/flattener for the same curve view.
- "Is 1y5y5y, 2y1y or 10y10y midcurve cheap to vanilla?" Midcurve vs swaption switches, FVAs built from midcurves,
  listed SOFR/Euribor midcurve vol vs standard options.
- Curve-cap calendars ("buy 1y 2s10s caps vs 6m 5s30s caps"): long forward curve vol.
- Hybrid or contingent options: a payer contingent on an equity decline, a curve cap contingent on an equity rally.
  Is the priced cross-asset correlation cheap against the stress scenario?
- Rates vol vs FX vol (swaption vs USDJPY options), and cross-market spread vol (EUR vs USD curve caps).
- Not for: swaption grids, forward-vol frontiers and expiry/tail switches ([vol-rates-options-rv](../vol-rates-options-rv/SKILL.md));
  strike solving for conditional curve trades ([curve-conditional-trades](../curve-conditional-trades/SKILL.md));
  structured-note issuance as a vega/correlation supply ([vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md)).

## Conventions
- Vols are normal (Bachelier) vols in bp per year. Spreads are in bp, long minus short: 2s10s = 10y − 2y. Some desks
  write "10s/2s" or "30s/5s" for the same thing; restate every quote as long − short.
- Curve cap = call on the spread (pays on steepening, bull or bear). Curve floor = put on the spread (pays on
  flattening or inversion). A straddle is a cap plus a floor at the same strike.
- ρ is the correlation of daily changes (bp) of the two legs, observed at the same snap.
- Premiums are in bp of notional ("cents" per 100). A single-look spread option pays notional × (S_T − K)⁺ with no
  accrual factor: 100mm notional = $10,000 per bp (Merrill Lynch RateLab, Yield Curve Options, Dec 2006). Check
  the multiplier on every term sheet.
- Midcurve E×G×L: expiry E, swap starting G after expiry, tail L. Example: 1y2y1y is a 1y option on the 1y swap
  starting 2y after expiry. Its vanilla legs are E×(G+L) and E×G: 1y3y and 1y2y.
- Hybrid ρ = corr(Δyield in bp, equity % return). Positive means yields and equities rise together. Sources quote it
  with different signs; restate them in this convention before comparing.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| ATM swaption normal vols for the legs (E×2y, E×10y, E×(G+L), E×G) | `vol_surface` (`product=swaption`) | daily, ≥ 3y | `strike_offset_bp=0`; interpolate missing tails (11y, 3y) before use |
| Midcurve swaption vols | `vol_surface` (`product=midcurve`, `fwd_start`=G) | daily, ≥ 3y | `atm_fwd_pct` sets the DV01 weights |
| CMS spread option vols or premiums, with the dealer ATM (convexity-adjusted) forward spread | `vol_surface` (`product=cms_spread`, `tenor` = `2Y-10Y`, `atm_fwd_pct` = convexity-adjusted forward spread) | daily, ≥ 3y | if absent, user-supplied CSV or dealer runs |
| Listed STIR midcurve options | `opt_static` (`is_midcurve`), `opt_quotes` (`nvol_bp`) | daily | American; price-based (call = receiver) |
| Par swap rates, spot and forward-starting | `curve_par` (`start=0D`, or `start`=expiry for forward legs) | daily close, ≥ 3y | realized correlation and realized spread vol |
| FX spot, FX implied vol | `fx_rates`; `macro_series` (`<PAIR>-FXVOL-<TENOR>-<DELTA>`, unit `pct`) | daily | implied vol is a lognormal vol in percent, not a rates normal vol |
| Equity index level and implied vol (hybrids) | `macro_series` (`<CC>-EQ-<INDEX>-TR` unit `index`, `<CC>-EQVOL-<INDEX>-<TENOR>` unit `pct`) | daily | dealer hybrid and vanilla premiums come from the quote |

Contract and adapters: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If an input is missing, ask
for it or hand off to the `rv-data-engineer` agent. Never invent vols or correlations.

## Method

### 1. Implied correlation from a spread vol
For a spread S = w_B·B − w_A·A:

```
σ_S² = w_A²σ_A² + w_B²σ_B² − 2ρ·w_A·w_B·σ_A·σ_B
ρ_imp = (w_A²σ_A² + w_B²σ_B² − σ_S²) / (2·w_A·w_B·σ_A·σ_B)
∂σ_S/∂ρ = −w_A·w_B·σ_A·σ_B / σ_S        (bp of spread vol per 1.00 of ρ)
∂ρ_imp/∂σ_S = −σ_S / (w_A·w_B·σ_A·σ_B)  (error in ρ per bp of spread-vol error)
```

- Curve options: w = 1. σ_A and σ_B are the ATM normal vols of the two legs at the same expiry. Use the E×2y and
  E×10y swaption vols for an E-expiry 2s10s option.
- Lower ρ gives higher spread vol. **Low implied correlation means spread or midcurve vol is rich to vanillas.**
  Sell-side monitors read it this way for both curve options and midcurves (Citi, Rates Vol Lab: Forward steepener
  and vol divergence, Jun 2023).
- Keep ρ_imp raw, never clipped. A value above 1 means σ_S is below the ρ = 1 floor |w_Bσ_B − w_Aσ_A|. Treat it
  as a data or strike mismatch until proven otherwise. A value below −1 is a data error.
- Convert every correlation signal into vol: Δσ_S = |∂σ_S/∂ρ|·Δρ. Compare that with bid/offer before calling
  anything rich.

### 2. From premium to vol (normal model)
```
C = DF·A·[(F − K)·N(d) + σ√T·φ(d)],  d = (F − K)/(σ√T)      put = C − DF·A·(F − K)
ATM:  C = DF·A·σ·√(T/2π)      ATM straddle = 2C   →   σ = straddle / (DF·A·√(2T/π))
```
- A = 1 for single-look spread options and A = annuity for swaptions. In the published examples F, K and C are
  in bp and DF is close to 1.
- Under the normal model the spread of two normal rates is itself normal, so Bachelier on σ_S is consistent. Kirk or
  Margrabe formulas model lognormal legs. A lognormal model of the spread itself cannot handle a negative spread,
  and inversions do happen (EUR 2s30s in 2007-08).
- F for a curve option is the dealer's convexity-adjusted CMS forward spread, not the forward swap curve. The
  published strikes "are the convexity-adjusted forward spreads" (Merrill Lynch RateLab, Yield Curve Options,
  Dec 2006). The gap grows with expiry, tail and vol.

### 3. Midcurves
At expiry T1 the midcurve's forward rate is a DV01-weighted spread of two spot-starting rates:
```
F(T2,T3) = w13·F(T1,T3) − w12·F(T1,T2),   w13 = DV01(T1,T3)/DV01(T2,T3),  w12 = DV01(T1,T2)/DV01(T2,T3),  w13 − w12 ≈ 1
σ_MC² = w13²σ13² + w12²σ12² − 2ρ·w13·w12·σ13·σ12
```
(Credit Suisse, The FVA: Forward Volatility Agreement, Aug 2013). ρ is the correlation between the T1-T2 and
T1-T3 rates. Back it out with Method 1, using w_A = w12 and w_B = w13. As printed: "the forward volatility of the
mid-curve trades above the level implied using a correlation of one", partly because the vanilla replication
ignores skew.

- **FVA / forward vol from a midcurve.** Take an FVA struck at T1 that expires at T2 on the T2-T3 swap:
  `(T2−T1)·σ_FVA² = (T2−T0)·σ²(T2,T3) − (T1−T0)·σ²_MC`. Vega hedges:
  `∂σ_FVA/∂σ(T2,T3) = (T2−T0)·σ(T2,T3)/((T2−T1)·σ_FVA)` (buy) and `∂σ_FVA/∂σ_MC = (T1−T0)·σ_MC/((T2−T1)·σ_FVA)`
  (sell). Hedge in vega, not notional. Notional-neutral vanilla vs midcurve replicates the terminal payoff but
  mismatches inception vega, which gives "considerable mark-to-market variation".
- **Midcurve calendar as synthetic forward vol.** Sell a 2y-expiry midcurve on the 8y-forward 20y rate and buy the
  10y-into-20y swaption on the same rate at the same strike (4.75%, about 92nv and 71nv): √((10·71² − 2·92²)/8) ≈
  65bp, the "mid-60s" printed. Like a butterfly it pays most if the rate sits near the strike at the first expiry
  (Credit Suisse, How High is High?, Sep 2013).
- **Rich/cheap regression** (Citi monitor standard): regress each midcurve vol on its two vanilla vols over 3y. For
  example, regress 1y2y1y on 1y3y and 1y2y. Alternatively, regress on 3 PCs of the vanilla surface. The residual and
  its z-score are the rich/cheap.
- **Listed STIR midcurves** (SOFR 1y-5y midcurves plus 3m/6m/9m short midcurves; Euribor midcurves) are
  options on a 3m futures rate that expire well before the reference period. Compare a midcurve with the standard
  option on the same contract (later expiry) to get forward vol, using Method 4. Compare it with the front-contract
  option at the same expiry to get a curve/correlation trade (Nomura, Conditional Euribor bull flatteners, Jun 2014). Nomura bought
  2y-midcurve vol against front (White) vol when their normal-vol spread sat just under its 10th percentile.
  These options are American and written on price, so a call is a receiver. Futures-option pricing without a
  convexity adjustment is "probably not" sufficient for long-dated midcurves (OpenGamma, Interest Rate Futures and
  their Options, Feb 2012).

### 4. Curve-cap calendars and forward curve vol
Variance is additive in time on the same underlying:
```
σ_fwd(T1→T2)² = (T2·σ_T2² − T1·σ_T1²)/(T2 − T1)       T1 = 6m, T2 = 1y:  σ_fwd = √(2·σ_1y² − σ_6m²)
```
Long the T2 cap and short the T1 cap is long forward curve vol. Using a different curve on the short leg (6m 5s30s
against 1y 2s10s) needs a beta of about 1 between the two curves. Citi checked that this beta had been about 1
since 2017 (Citi, US Rates Vol Lab: Vol cycle, steepeners, and SOFR, Mar 2019). If the beta is not 1, scale σ_T1
by β, or the formula misprices the switch.

### 5. Realized correlation and realized spread vol
- Use daily close-to-close changes in bp, from one snap and one time zone. Default window 63 days (3m): Citi uses
  3m realized for midcurve implied/realized. Also show 21 days (1m, the window Citi pairs with curve-vol
  implied/realized) and 126 days (6m, the proxy Citi uses for implied correlation in forward vols).
- For midcurve and forward legs, correlate the rates that start at the option expiry (`curve_par` with `start`=E),
  not spot rates.
- Measure realized spread vol directly as std(ΔS)·√252, as well as through the formula. Comparing the two catches
  unit and sign errors.
- To extend implied curve-vol history back before the options traded, combine swaption leg vols with realized
  correlation. Citi used this to call 6m-forward 18m 2s30s curve vol of 42nv historically cheap (Citi, US Rates
  Weekly: What to expect when you're expecting a turn, Apr 2018). Label such history as a proxy.
- Intraday sampling lowers noise. Citi samples hourly from 8am to 3pm, and every 30 minutes from 7am to 4pm in its
  2026 monitor. A low intraday/close-to-close ratio flags close-time effects.
- Estimator choice (EWMA, shrinkage, robust) is covered in [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md).

### 6. Rich/cheap screen: four lenses
| Lens | Metric | z-score window | Reading |
|---|---|---|---|
| Level | ATM spread or midcurve normal vol | 3m | context only |
| Implied correlation | ρ_imp | 3y | low z = rich spread/midcurve vol |
| Implied vs realized | ρ_imp/ρ_real(3m) for midcurves; σ_S,imp/σ_S,real (1m and 3m) for curve options | 1y | high vol ratio = rich; high correlation ratio = cheap (opposite signs) |
| Model residual | midcurve vol on its two vanilla vols (3y regression); PCA of the curve-vol surface (2 PCs, 3y) | own history | positive = rich; relative value only |

The windows are those of the Citi Rates Vol Lab monitor. A point is a candidate when at least two lenses agree at
|z| ≥ 1.5, and strong at |z| ≥ 2 (published flags ran from 2σ to 4.6σ). Citi warns that the implied/realized ratio
is "not necessarily a good leading indicator". Never trade it alone.

### 7. Structures and what each is long
| Structure | Exposure | Use when |
|---|---|---|
| Long curve cap (floor) | long spread vol = short correlation; max loss = premium; pays on bull or bear steepening (flattening) | correlation high, curve near an inflection |
| Conditional steepener (payer/receiver on each leg) | correlation-free: priced off leg vols only | strong, persistent directionality (J.P. Morgan, A primer on Conditional Trades, May 2016) |
| Short cap vs long the same-strike conditional | sells correlation-implied curve vol, buys the ρ = 1 version | ρ_imp low (curve vol rich) |
| Long spread option delta-hedged vs short leg options at equal gamma | P&L ≈ Γ_S·σ_A·σ_B·(ρ_imp − ρ_real)·dt: earns while realized ρ stays below implied | ρ_imp high vs realized |
| Midcurve vs its vanillas (vega-weighted) | correlation between T1-T2 and T1-T3 rates | ρ_imp z extreme plus regression residual |
| Curve-cap calendar (long T2, short T1) | long forward curve vol; negative near-term curve gamma | forward curve vol cheap |
| Cross-market caps, premium-neutral (EUR vs USD 2s10s) | relative spread vol across markets | spread-vol ratio dislocated vs realized |
| 1x2 or costless cap spreads | short wing spread vol; roll on a wide forward-spot gap | medium-term steepener without paying premium |

The dispersion-style row follows from the delta-hedged gamma P&L. ½Γ_S[(ΔB−ΔA)² − σ_S²dt] minus
½Γ_S[ΔA² − σ_A²dt] minus ½Γ_S[ΔB² − σ_B²dt] leaves Γ_S·(ρ_imp·σ_A·σ_B·dt − ΔA·ΔB). This is the rates form of the
dispersion decomposition in Jacquier & Slaoui (Variance Dispersion and Correlation Swaps). Equal-gamma weights leave
vega exposure, and vega-flat weights leave volga exposure. Name the residual you keep.

YCSO vs conditional: a curve cap pays on any steepening. A conditional bear steepener expires worthless if the
curve bull-steepens. With σ_sh and σ_lg the leg vols of the short and long tenor (not the spread vol σ_S), a conditional trade's implied
directionality is 1 − σ_sh/σ_lg (it assumes ρ = 1). Its delivered directionality is 1 − ρ·σ_sh,real/σ_lg,real, so
delivered − implied = σ_sh,imp/σ_lg,imp − ρ·σ_sh,real/σ_lg,real (J.P. Morgan, A primer on Conditional Trades, May 2016). Cross-market analogue: implied directionality =
1 − σ_EUR/σ_USD.

### 8. Hybrid and contingent rates options
- Payoff = vanilla rates option × 1{equity condition at expiry}. One example is a 30y payer that pays only if the
  equity index is below 97% of its reference level. The discount to vanilla depends on the equity digital and on the rates-equity
  correlation.
- Sanity decomposition: at ρ = 0, hybrid ≈ vanilla × P(condition), where P(condition) is the skew-consistent equity
  digital price. For a payer contingent on equities down, a hybrid/vanilla ratio below the digital means the price
  assumes ρ > 0 (yields rise with equities), so the joint "yields up, equities down" outcome looks unlikely. Buying
  that hybrid is a sale of that correlation.
- The value lies in the gap between the priced correlation and the correlation in the stress scenario. Test it with
  realized correlation conditional on the rate leg having moved beyond the strike: compare 6m realized correlation
  with (spot rate − the forward from 6m earlier). This is a tail scenario with few or no historical analogues, so
  any backtest is only indicative.
- Pricing is dealer-model and one-way. A hybrid needs an ISDA, and the unwind is with the same dealer. Size it as a
  premium-at-risk hedge, never as an RV convergence trade.

### 9. Rates vol vs FX vol
- Track σ_N(swaption, bp)/σ_FX(%) against its own history. The units differ, so only the z-score means anything.
  Pair it with a fair value for the FX level from the rate differential.
- Express the view as an FX option spread against a swaption: buy cheap FX vol, sell rich rates vol. The pair works
  only if the rates-FX co-movement holds in the scenario. For example, the yen rallies when US yields fall in
  risk-off. Size the legs on that co-movement (a beta of FX % change on Δrate differential) and state it as the
  main risk.
- Only one source covers this (Citi, Jan 2020). Keep conclusions tentative.

## Worked examples
The derived numbers come from `scripts/implied_corr.py` (Bachelier, undiscounted, flat-rate annual annuities).
The sources quote premiums. The vols and correlations below are this skill's own back-outs.

**A. Curve cap vs conditional, implied correlation (J.P. Morgan, A comprehensive look at convexity hedging in
interest rates, Mar 2019; trade from Feb 2019).** The trade: short $1bn 3M×(2s/10s) ATMF curve caps (K 9.8bp)
at 4c; sell $113mn 3M×10Y ATMF receivers (2.66%) at 96c; buy $519mn 3M×2Y ATMF receivers (2.59%) at 19c. The
receiver legs are DV01-matched at about $100k/bp each, which makes them a conditional bull steepener.
- Cap: σ_S = 4/√(0.25/2π) = **20.1bp**.
- Legs, with annuities 8.68 and 1.92: σ_10y = 96/(8.68·0.1995) = **55.4bp** and σ_2y = **49.5bp**.
  Semi-annual annuities move these by less than 0.4bp.
- ρ_imp = (49.5² + 55.4² − 20.1²)/(2·49.5·55.4) = **0.93**. ∂σ_S/∂ρ = −136bp per 1.00, so one correlation point is
  1.4bp of spread vol, or 7% of the cap premium. In reverse, a 1bp error in σ_S moves ρ_imp by 0.7 points.
- Reading: the package sells the correlation-priced curve cap and buys the ρ = 1 conditional.

**B. Spread vol when correlation is at its highs (Merrill Lynch RateLab, Yield Curve Options, Dec 2006).**
Single-look CMS2y vs CMS10y straddles were 30, 38 and 48bp for 1y, 2y and 5y expiries (K 28, 30, 31). The caps
were 15, 19 and 24bp: an ATM cap is exactly half the straddle. Undiscounted, the implied spread vols are 37.6,
33.7 and 26.9bp. Rates were near 5% (the note cites 425bp of Fed hikes). Discounting at 5% (DF 0.952, 0.907, 0.784)
gives **39.5, 37.1 and 34.3bp**, so ignoring DF understates the 5y vol by about a fifth (26.9 vs 34.3). The note gives 1y2y vol
as 86 Nvol and the 1y2y/1y10y vol ratio as 112%, so 1y10y ≈ 76.8. That gives ρ_imp(1y) ≈ **0.89-0.90**,
discounted or not (the note also quotes a vol level of 81; with 1y2y = 81, ρ_imp is 0.87-0.89). Spot 2s10s was in single digits and realized correlation was near its all-time high. The
author recommended buying curve caps and straddles, calling spread vol "the MOST levered way to purchase
volatility".

**C. Midcurve and FVA (Credit Suisse, The FVA: Forward Volatility Agreement, Aug 2013).** Inputs: 6m1y 37bp, 6m11y
99bp, 18m10y 99bp; DV01 6m1y 1.0, 6m11y 9.6, 18m10y 8.6; ρ = 1. 6m1y10y midcurve:
σ_MC = (9.6·99 − 1.0·37)/8.6 = **106.2bp**, printed as 107 (rounded DV01s). Six-month-forward 1y10y vol:
√(1.5·99² − 0.5·107²) = **94.7bp**. Per the note, a client could buy 1y10y vol six months forward at 95nv
while spot traded at 100nv. Hedges: ∂σ_FVA/∂σ_18m10y = 1.57
and ∂σ_FVA/∂σ_MC = 0.56, i.e. buy 160k/nv of 18m10y and sell 60k/nv of the midcurve for 100k/nv of FVA.
Converted with vegas of 8.4bp and 4.9bp, that is $186mm and $116mm notional.

**D. Curve-cap calendar (Citi, US Rates Vol Lab: Vol cycle, steepeners, and SOFR, Mar 2019).** Buy $1bn 1y 2s10s
caps at K 40bp (ATM 27bp), 6.4c; sell $1bn 6m 5s30s caps at K 45bp (ATM 37bp); net cost 2.7c, so the 6m leg is
3.7c. Curve delta was about flat at inception. The back-outs (OTM strikes, so skew is included) are 29.5bp (1y
2s10s) and 24.8bp (6m 5s30s), giving forward curve vol ≈ √(2·29.5² − 24.8²) = **33.6bp**. Citi called the 6m-forward
6m 2s10s vol "optically cheap" and put the main risk in a near-term 5s30s steepening (negative curve gamma). By
4 Oct 2019 the trade marked 2.6c against the 2.7c entry, −$5k (Citi, US Rates Weekly: All it takes is a little push,
Oct 2019).

**E. Hybrids.** (1) Buy a 19-Mar-27 USD 30mm 30y SOFR payer struck at ATMF+0.4%, contingent on the equity index
< 97% at expiry: 0.49% upfront (3.1bp running), 64% cheaper than the vanilla, implied correlation −5%, target $500k,
stop −$147k. The thesis is fiscal tail risk. 1m realized correlation of Δ30y yield against daily equity % change
centred near 0 and became extremely negative in the May 2026 sell-off. When 30y sold off beyond the 40bp OTM strike,
realized correlation was well below −5% (Citi, Rates Vol Lab: Slow and steady wins the short gamma race, Sep 2026).
(2) A 6m payer spread on the 2y (1.696%/2.196%), contingent on the equity index ≥ 5% lower, cost 8c against 36c for
the vanilla (−78%). It returns 3.75x if spot rates are unchanged and equities fall 5%. It was cheap because
yields and equities had been rising together since QE (ρ > 0 in this skill's convention); the author calls it
"effectively a sale of that correlation" (Convexity Maven, For Propeller Heads Only, Jun 2019).

**F. Rates vs FX vol (Citi, Rates Vol Lab: In search of cheap vol, Jan 2020).** The 6m10y/USDJPY vol ratio was very
rich by historical standards. USDJPY at 110.17 looked high against the 10y USD-JPY differential: USDJPY = 0.0266 ×
diff(bp) + 103.48, R² 0.32, 2018-19 sample. Citi bought $30mn 6m USDJPY 108/105 put spreads against selling $50mn
6m10y ATMF+45bp (2.2%) payers, net cost $35k. The trade also sold rich USDJPY put skew (6m 25d put/ATM ratio). Main
risk: 10y above 2.2% at expiry.

More dated readings and conversions are in [references/observations.md](references/observations.md).

## Signals & interpretation
- **Low ρ_imp (3y z ≤ −1.5) with realized ρ stable:** curve vol or midcurve vol is rich. Sell curve caps against
  conditionals or vanilla legs, or sell midcurves against vanillas. Alternatively, go long correlation with the
  reverse of the dispersion row in Method 7: short the spread option, delta-hedged, against long leg options at
  equal gamma. That earns while realized ρ stays above implied. Persistent demand can keep it rich for a long time. USD 5s30s implied correlation sat at multi-year
  lows on steady cap buying (Citi, Jun 2023). Require a catalyst or positive roll.
- **High ρ_imp near 1, flat curve, realized ρ at its highs:** spread options are at their cheapest. Buy caps or
  straddles ahead of an inflection, such as the first curve inversion of a cycle (RateLab, Dec 2006; Citi, US Rates
  Weekly: What to expect when you're expecting a turn, Apr 2018).
- **Midcurves:**
  - Cheap: ρ_imp z high and regression residual negative. For example, USD 5y5y midcurves at ρ_imp ≈ 95-96%
    (3y z +1.2 to +1.6) with a 2y-expiry residual of −3.2 (z −2.5) (Citi, Jun 2023).
  - Rich: front-end midcurves get rich when Fed-path steepeners are expressed through them. For example, 6m1y1y
    was +2.7 (z 1.5) on vol-surface PCA (Citi, US Rates Vol Lab: The art of gamma hedging, Mar 2018).
- **Lenses disagree, so pick the expression.**
  - Mar 2020: USD 6m 2s10s curve vol was +4.2 (2.7σ) rich on PCA, yet 1m 2s10s implied/3m realized was 0.83
    (z −1.5) (Citi, Rates Vol Lab: Liquidity, vega, and convexity, Mar 2020). That is rich vega but cheap gamma:
    sell longer expiries and own short-dated gamma, or pass.
  - Jun 2023: 1m 2s5s implied/1m realized was 2.55 (2.6σ), rich on both lenses.
- **Structural prior:**
  - A desk's ex-ante screen showed short-dated spread options with strongly negative expected returns to the buyer:
    3m 2s5s about −79%, Sharpe −1.2; short-expiry 10s20s about −71%. It listed "short spread options" among its structural
    trades (Citi, A Holistic Approach to Convexity Across Fixed Income, Jun 2022; small table cells were read at low
    resolution).
  - The same screen flagged buys too: 3m 5y5y midcurves about +98% (Sharpe 2.2), 1y 2s30s and long-expiry 10s30s
    spread options. The sell bias is in short expiries, not in all spread vol.
  - Treat this as a prior from one partially read screen, not a rule: curve gamma has also screened cheap to
    realized (Mar 2020 above). Lean short on short-dated curve vol only when the four lenses agree.
- **Vol fair value:** realized 2y-10y correlation is a factor in outright vol fair value, with high correlation going
  with low vol. Vol has asymmetric upside when slope, credit spreads and correlation are all at their bounds (Merrill
  Lynch RateLab, Professional Javelin Catching, Feb 2007). Hand the outright-vol view to
  [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md).
- **Hybrids:** cheap when the stress-scenario correlation is far from the priced one, and the condition matches a
  scenario you would hedge anyway (Example E).
- Confirm with flows. Cap demand from steepener or recession hedgers, and structured-note supply (EUR 2s30s
  inversion notes, EUR 13-20bn issued in 2007-08: Merrill Lynch RateLab, Another Fine Mess, Jun 2008), explain
  persistent dislocations. See [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md).

## Pitfalls
- **Sign of the cross term.** One primer prints `σ_2s10s = √(σ_2y² + σ_10y² + 2ρσ_2yσ_10y)` (BofA, US Vol Primer,
  Mar 2024). For a spread the term is −2ρ (RateLab 2006; FVA primer 2013). Test any implementation with ρ = 1:
  vols 100 and 60 must give 40.
- **Mismatched legs.** Leg vols must share the option's expiry, be ATM on each leg's own forward, and come from the
  same snap. Tails such as 11y or 3y usually need interpolation. With w = 1, ∂ρ_imp/∂σ_A = 1/σ_B − ρ/σ_A. It is
  near zero for the lower-vol leg and largest for the higher-vol leg: in Example A, 0.08 point per bp on the 2y leg
  but 0.34 on the 10y leg, against 0.73 per bp of spread-vol error; in Example B, 0.26 on the 2y (higher-vol) leg.
  The higher-vol leg needs the cleanest quote.
- **CMS convexity.** For a curve option, F and K are the convexity-adjusted CMS spread. Comparing a cap strike with
  the forward swap curve misstates moneyness, most of all for long expiries and 30y legs.
- **Skew.** OTM curve options and OTM midcurves embed smile. A ρ backed out from OTM premiums (Example D) is not the
  ATM ρ, so compare like with like.
- **ρ_imp > 1 does occur in published grids:** 1m USD midcurve implied correlations ran 89-105% (Citi, Rates Vol
  Lab: Short Blues convexity via futures/swaps, Feb 2023). Check the strike, the expiry date and the DV01 weights
  before calling it cheap.
- **Realized-correlation noise.** A 21-day window has a standard error of about (1 − ρ²)/√21. That is small near
  ρ = 0.95 but large near 0.5. Correlate changes, never levels. Use one snap: EUR and USD closes differ by hours.
  Windows that span holidays or data gaps are not comparable. Daily z-scores of a 3m rolling ratio over 1y rest on
  about four independent windows, so treat the z as a ranking, not a significance test.
- **Notional-neutral midcurve vs vanilla.** The terminal payoff matches but the inception vega does not, so expect
  MTM swings. Hedge in vega.
- **Curve cap ≠ conditional.** The payoffs differ in the opposite-direction scenario. Do not treat them as
  substitutes when comparing prices.
- **Parallel-shift scenarios imply ρ = 1.** They value curve options at zero spread vol. A scenario set's implied
  correlations (Salomon Brothers, Understanding the Yield Curve Part 6, Nov 1995: all ≥ 0.92 in its example) should
  match your view.
- **Hybrids:**
  - Dealer-model pricing, one-way liquidity, ISDA required.
  - The sign of the rates-equity correlation flips by regime: positive after QE (2019), and inversely tracking 30y
    yield changes in 2026.
  - A backtest cannot validate a scenario with no precedent.
- **Rates vs FX.** The ratio mixes bp and %, it rests on one source, and FX skew and rates skew enter the two legs
  differently.
- **G10 coverage.**
  - Covered by the sources: USD and EUR OTC curve options and midcurves, plus listed SOFR and Euribor midcurves.
  - Not covered: GBP, JPY, CAD, AUD, NZD, CHF, SEK and NOK curve options. Ask for dealer runs and do not assume
    USD liquidity or bid/offer.

## Output
Return one row per instrument screened, ranked by the strongest agreeing z-score.

| column | meaning |
|---|---|
| date, ccy, product | curve option, midcurve, listed midcurve, hybrid, xasset |
| structure | e.g. `1y 2s10s cap`, `1y5y5y midcurve` |
| σ_A, σ_B (bp) | leg ATM normal vols, with weights w_A and w_B |
| σ_S or σ_MC (bp) | spread or midcurve ATM vol; source premium if backed out |
| ρ_imp, z_3y | implied correlation, raw |
| ρ_real 1m / 3m / 6m | realized correlation of daily changes |
| impl/real σ_S (1m, 3m), z_1y | spread-vol ratio |
| residual (bp), z | regression or PCA rich/cheap |
| ∂σ/∂ρ (bp per 1.00 of ρ; ÷100 per point) | correlation leverage, as the script prints it |
| view | rich / cheap / no-trade; lenses agreeing |
| structure proposal | legs, notionals, vega or DV01 weights, premium, max loss, curve delta and gamma |
| risks / kill criteria | e.g. stop if ρ_imp z re-crosses 0 or the realized correlation regime breaks |

Charts: ρ_imp vs ρ_real (3y), spread vol vs spread level, the residual's z-score history. Hand the chosen trade to
[rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and the pre-trade challenge to
[rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Scripts
- [`scripts/implied_corr.py`](scripts/implied_corr.py) computes the following, all in the normal model:
  - spread vol ↔ implied correlation, with weights;
  - ∂σ_S/∂ρ;
  - Bachelier price and implied vol from a premium (with an annuity for swaptions);
  - forward vol from two expiries;
  - flat-curve midcurve DV01 weights;
  - a midcurve implied-correlation table from a canonical `vol_surface` file;
  - rolling realized leg vols, spread vol and correlation from `curve_par`.

  Run `python scripts/implied_corr.py --help` for usage. `--selftest` checks the closed forms (ρ = ±1, 0), a
  seeded bivariate simulation with known ρ, Bachelier parity, the FVA primer example (106.2 / 94.7), and a
  canonical `vol_surface` midcurve row priced at a known ρ. Inputs with more than one `snap` are rejected unless
  `--snap` is given.
  Example: `python scripts/implied_corr.py spread --sig-a 49.5 --sig-b 55.4 --sig-s 20.1`.

## Related skills
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): swaption surface RV, forward-vol triangles and frontier, outright vol fair value
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): conditional steepeners/flatteners, the correlation-free alternative to curve caps
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): CMS range accruals, inversion notes, callables as spread-vol supply
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): hybrids as tail hedges; spread and midcurve skew
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): delta-hedged gamma P&L behind the correlation trade
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA of the curve-vol surface and of vanilla vols
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): realized correlation estimators (EWMA, shrinkage, robust)
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores and lookbacks for the four lenses
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): listed STIR options and midcurves on SOFR/Euribor/SONIA
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures convexity behind long-dated listed midcurves
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): the underlying curve view and its directionality
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): `vol_surface` (incl. the `cms_spread` product), `curve_par`, `opt_quotes`, `macro_series`
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): trade note for the chosen structure
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): convexity and strikeless vol in the long end.

## References
- Credit Suisse US Rates Trading (D. Mohney, H. Bassman) - The FVA: Forward Volatility Agreement (27 Aug 2013): midcurve as DV01-weighted spread option, forward-vol formula, hedge ratios, worked 6m1y10y example
- Credit Suisse (H. Bassman) - How High is High? (17 Sep 2013): synthetic forward vol from a 2y midcurve vs 10y-into-20y calendar
- Merrill Lynch RateLab (H. Bassman) - Yield Curve Options (title inferred; 8 Dec 2006): spread-vol formula, single-look CMS 2s10s straddle/cap prices, correlation peaks when the curve is flat
- J.P. Morgan Interest Rate Derivatives (J. Younger, M. Salem, H. St John) - A comprehensive look at convexity hedging in interest rates (29 Mar 2019): short curve caps vs conditional bull steepeners with premiums
- Citi Research (R. Bikbov, J. Williams) - US Rates Vol Lab: Vol cycle, steepeners, and SOFR (25 Mar 2019): curve-cap calendar, forward curve vol formula, curve-vol PCA, implied correlation of 2s10s options
- Citi Research (M. Chang, J. Williams, A. Appeddu) - Rates Vol Lab: Forward steepener and vol divergence (12 Jun 2023): midcurve and CMS curve-option screens, low implied correlation = cap demand
- Citi Research (R. Bikbov, J. Williams) - Rates Vol Lab: Liquidity, vega, and convexity (30 Mar 2020): implied correlation falls, PCA rich vs implied/realized cheap
- Citi Research (M. Chang, J. Williams, A. Appeddu, A. Vazquez Plata) - Rates Vol Lab: Slow and steady wins the short gamma race (14 Sep 2026): equity-contingent 30y payer, implied correlation −5%, stress-correlation test
- Convexity Maven (H. Bassman) - For Propeller Heads Only (17 Jun 2019): equity-contingent payer spread as a sale of rates-equity correlation
- J.P. Morgan European Rates Strategy (K. Gupta, F. Bassi, S. Vijay) - A primer on Conditional Trades (26 May 2016): YCSO vs conditional payoffs, implied vs delivered directionality, cross-market version
- BofA Global Research (B. Braizinha) - US Vol Primer: A Guide for the Perplexed (11 Mar 2024): curve caps as a correlation view, FVA/midcurve replication appendix
- Citi Research (R. Bikbov, J. Williams) - Rates Vol Lab: In search of cheap vol (17 Jan 2020): rates vs USDJPY vol ratio, FX put spreads vs swaption payers
- Citi Research (R. Bikbov, J. Williams) - US Rates Vol Lab: Trading long-dated convexity (9 May 2019): monitor definitions (midcurve regression, curve-vol PCA, intraday realized)
- Citi Research Rates Vol Lab monitor issues - The art of gamma hedging (12 Mar 2018), Gamma and Vega RV (14 Jan 2019), Buying vol for less (25 Sep 2019), Left-side vols' outperformance (22 Jun 2021), Short Blues convexity via futures/swaps (21 Feb 2023), Fading vega dislocations (5 Oct 2026): midcurve and curve-option readings, implied correlations above 100%
- J.P. Morgan Interest Rate Derivatives (J. Younger, M. Salem) - The long and short of it (3 Aug 2018) and Issuance, pensions, and long-end spreads (14 Sep 2018): 6M 5s30s vs 2s10s caps, premium-neutral EUR vs USD 2s10s caps
- Morgan Stanley Interest Rate Derivative Strategy - Buy Higher Rates Protection at a 30% Discount (27 Aug 2026): 3m 5s30s ATM curve cap premium, EUR vs USD 5y5y straddles
- 2026 weeklies with curve-cap and contingent structures - Citi US Rates Weekly: Can Secretary Bessent and Chair Warsh save the curve? (21 Aug 2026) and Pension plan for 20s? (9 Oct 2026); Barclays Global Rates Weekly: The urgency question (2 Oct 2026); Goldman Sachs Global Rates Trader: Reaching Limits (2 Oct 2026)
- Citi Research US Rates Weekly - What to expect when you're expecting a turn (20 Apr 2018) and All it takes is a little push (4 Oct 2019): 6m 5s30s / 2y 2s30s cap switch, forward curve vol 42nv, curve-cap calendar mark
- Merrill Lynch RateLab - Another Fine Mess (11 Jun 2008): EUR 2s30s CMS inversion notes as spread digitals held by dealers
- Merrill Lynch RateLab - Professional Javelin Catching (16 Feb 2007): realized 2y-10y correlation in vol fair value
- A. Jacquier, S. Slaoui - Variance Dispersion and Correlation Swaps (working paper, Imperial College / Zeliade): implied correlation algebra, dispersion P&L ≈ correlation spread × variance, weighting residuals
- Citi Interest Rate Volatility Trading (M. Parolari) - A Holistic Approach to Convexity Across Fixed Income (presentation, Jun 2022): ex-ante expected returns of spread options and midcurves, structural short spread options
- Nomura Derivative Focus (N. Firoozye, Q. Zhang) - Conditional Euribor bull flatteners (erratum, 19 Jun 2014): listed Euribor midcurve vs front option, vol-spread percentile as entry signal
- D. Huggins, C. Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022), and OpenGamma (M. Henrard) - Interest Rate Futures and their Options: Some Pricing Approaches (v1.3, Feb 2012): listed SOFR midcurve specifications; limits of unadjusted futures-option pricing for long-dated midcurves
- Salomon Brothers (A. Ilmanen) - Understanding the Yield Curve, Part 6 (Nov 1995): scenario sets imply correlations
- P. Hagan - Convexity Conundrums: Pricing CMS Swaps, Caps, and Floors (Wilmott Magazine, 2003) (external): CMS convexity adjustment behind curve-option forwards
