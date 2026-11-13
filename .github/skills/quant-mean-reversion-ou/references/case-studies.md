# Sourced case studies and back-test tables

Numbers behind the worked examples in [SKILL.md](../SKILL.md). Every row is cited; none were re-run. All back-tests
below are gross of costs unless stated.

## 1. Swap-spread PCA dislocation indicator (daily, 2001-2016)

Method: rebuild 2y/5y/10y/30y swap spreads from the first two PCs (rolling 250-day PCA), z-score the residual over 250 days,
dislocation indicator DI_t = 10-day moving average of RMS_i(z_i,t); if DI exceeds the threshold buy the cheapest and sell the
richest spread by z (1:1 bp), re-select daily, stop when DI is below threshold. Residuals are AR(1)-like with half-lives about 20 days.
No costs, carry or stops. Readings at publication: Germany DI 1.13, UK and Japan about 0.6, US about 0.3.

| Market | DI threshold | Cum. bp | Sharpe | Days in | bp/day | Avg hold (days) |
|---|---|---|---|---|---|---|
| US | 1.0 | 267 | 1.2 | 1750 | 0.15 | 32 |
| US | 1.2 | 221 | 1.2 | 1359 | 0.16 | 26 |
| US | 1.4 | 153 | 1.0 | 1061 | 0.14 | 29 |
| US | 1.6 | 111 | 0.8 | 879 | 0.13 | 28 |
| US | 1.8 | 96 | 0.7 | 755 | 0.13 | 33 |
| US | 2.0 | 51 | 0.4 | 676 | 0.08 | 38 |
| Germany | 1.0 | 869 | 2.4 | 2278 | 0.38 | 43 |
| Germany | 1.2 | 803 | 2.5 | 1906 | 0.42 | 37 |
| Germany | 1.4 | 726 | 2.5 | 1601 | 0.45 | 36 |
| Germany | 1.6 | 675 | 2.7 | 1352 | 0.50 | 30 |
| Germany | 1.8 | 618 | 2.7 | 1160 | 0.53 | 26 |
| Germany | 2.0 | 554 | 2.8 | 967 | 0.57 | 21 |

Reading: the US edge falls with threshold (fewer days, same bp/day), the German edge rises with threshold, holds of 21-43 days are
consistent with a 20-day half-life. (BofA Merrill Lynch, Liquid Insight: A simple framework for swap spread relative value, 2 Jun 2016.)

## 2. EUR 5s10s30s fly residual episodes (fair-value residual, since 2013)

Seven episodes of residual < -5 bp lasting more than a week (10y rich to the model): normalisation with a flatter 10s30s in 6 of 7 (86%);
overshoot to 10y cheap by 5 bp "or even 10 bp" in 6 of 7; average start to fair 3.1 months, fair to overshoot 2.7 months; overshoot
typically lasted under three months. Episodes (start / fair / overshoot-end): Feb13/Jun13/Jul13; Oct13/Nov13/Dec13; Jun14/Feb15/Mar15;
Nov15/Dec15/none; Jan16/Feb16/Feb16; Jan17/Apr17/Nov17; Mar19/Aug19/Mar20. Trade: pay the fly, model 10y about 6 bp rich on 7 Apr 2021, entry
-5 bp, short target +3/4 bp, longer target +8 bp, stop moved to -4 bp, carry plus roll +0.8 bp a month. Do not take profit mechanically at zero
residual. (BNP Paribas, G10 Interest Rates Focus: EUR curve convexity, Lessons from history, 25 May 2021.)

## 3. EUR forward-grid residuals: carry versus reversion speed

1F1Y-10F1Y steepener about 14 bp too flat but rolls -15.5 bp over 3 months: breakeven only if the residual closes in under 2.6 months.
1F1Y-6F1Y-9F1Y fly belly 23 bp rich with carry -2 bp over 3 months: carry erases the profit only if reversion takes more than 36 months.
Spot 2s7s10s fly: entry 71 bp (incl. 0.5 bp charged off the 70.5 mid), target 91, stop 61, carry -2.5 plus roll +3.2 = +0.7 bp over 3 months,
9 bp from the 3-year mean. (ING Global Markets Research, Rates Strategy: Deconstructing the EUR yield curve, 15 Jan 2020.)

## 4. USD 3s5s10s PCA-weighted fly with an OU overlay

PCA on the covariance of swap levels (variances 7.1%, 14.0%, 17.5% for 3y/5y/10y); PC3 loadings 0.63 / -0.70 / 0.32; weights normalised
by the belly [-0.90, +1.00, -0.46]. PV01 per 1mm 274 / 482 / 903 (3y/5y/10y); for 50k of 5y PV01: pay 103.7mm 5y, receive about 164mm 3y,
receive 25.5mm 10y. OU fit: half-life 11 business days, z = -2.15, fly about -47 (range about -36 to -50, Dec 2011-Jun 2015), expected
path reverts from about -47 toward about -42, expected P&L about 5 bp ex carry, carry plus roll +6.25 bp over 3 months. The 50:50 fly by
contrast is correlated with the 5y level (quadratic R^2 0.66) and with 3s10s. Caveats: fixed current weights back-cast over history have
look-ahead; loadings are unstable so rebalance; the market quotes 50:50 flies so a PCA fly costs more to execute.
(bquanttrading blog, Principal Component Analysis Part II, 29 Jun 2015, updated 7 Jan 2016.)

## 5. USD 5s30s swap-spread flattener (z-bands)

Difference = 30y spread minus 5y spread = -43.1 bp, z about +2.1 on 252 days; regression residual -6.3 bp (about -1.5 sigma); target below
-53 bp, stop above -40 bp, about 3 bp risk vs 8-12 bp reward (about 2.5:1); roll +23.1 bp over 5y (about +1 bp over 80 days); difference
vol about 32 bp a year (about 2 bp a day); back-test since 2023 with holds over 40 days: hit rate 100%, average +14 bp, optimum hold 40-80
trading days. The rolling mean itself drifts and a 100% hit rate on a short sample is a small-sample artefact.
(Ade Rhodes, Trade Idea: USD 5s30s Swap Spread Flattener, 9 Oct 2025.)

## 6. Levels versus spreads (US, 1968-95)

Change-on-level regression (coefficient, t, R^2), monthly / annual: 3m -0.03 (-1.26, 2%) / -0.26 (-1.75, 12%); 2y -0.02 / -0.26; 30y
-0.01 / -0.20 (10%); 2y-3m spread -0.13 (-3.40, 7%) / -0.74 (-2.49, 37%); 30y-2y -0.06 (-2.19, 3%) / -0.42 (-2.70, 22%). First-order
autocorrelation of monthly changes: 3m 0.10, 2y 0.17 (t 2.46), 30y 0.15 (2.08), 2y-3m -0.12, 30y-2y 0.08. Outright levels revert slowly or
insignificantly; curve spreads revert more, clearer at an annual horizon; short-run trending then a "rubber-band" pull back. The level
evidence leans on 1979-82: check sub-periods. (Salomon Brothers, Understanding the Yield Curve Part 7, Feb 1996.)

## 7. Trading-rule calibration on a discrete OU (profit-take / stop-loss mesh)

Setup: P_t = (1 - phi) E0[P_T] + phi P_{t-1} + sigma eps, phi = 2^(-1/tau); exit at profit pi_bar or loss pi_; maximum holding 100 obs;
100,000 paths per mesh node; mesh 20 x 20 over {0.5 sigma ... 10 sigma}; non-annualised Sharpe, no costs. Results: forecast 0, tau = 5: best
is a small profit-take with a wide stop (Sharpe about 3.2, "5-fold or 7-fold unrealised losses" tolerated), worst is a tight stop with a wide
profit-take, symmetric barriers near-neutral; tau = 25/50/100 progressively flat (random-walk-like, no optimum). Forecast +5: tau = 5 profit-take about 6,
stop 4-10, Sharpe about 12; tau = 10 PT about 5, SR about 9; tau = 25 SR 2.7; tau = 50 SR 0.8; tau = 100 SR 0.32. Negative forecasts mirror.
Binomial check: n = 260, payouts +0.005 / -0.01: p = 0.70 gives SR 1.17, p = 0.72 gives SR 2, p = 2/3 gives SR 0. A rule calibrated by history on a near-random-walk
spread is overfit; an overfit rule has out-of-sample Sharpe below the median across the mesh. (Lopez de Prado, Advances in Financial Machine Learning, 2018.)

## 8. Residual of a futures basis versus a cross-currency regressor (weekly)

Fair-value regression residual fitted as OU, columns = single regressor / two regressors: mean -0.18% / -0.09%; speed 0.19 / 0.27 per week;
sigma 5.60 / 5.48; half-life 3.70 / 2.56 weeks; expected 90% convergence 12.3 / 8.5 weeks. Use the residual as an uncorrelated overlay or a
timing guide, not stand-alone: costs of the regressor leg mean the residual is seldom large enough. Structural break: re-estimate overnight-rate
reversion on post-August-2021 data (standing repo facility acted like a cap added mid-series); whether spikes are included in the calibration moved a
futures price by about 32 bp. (Huggins and Schaller, SOFR Futures and Options, 2022.)

## 9. Other cited data points

- Front-end futures forwards rarely price more than 70-80% of the eventual cycle; the front end became more mean-reverting as the hiking cycle
  neared neutral; Reds most mean-reverting in 2018. (J.P. Morgan, 3 Aug 2018.)
- Vol calendars: regression of 3m/1m vol ratio on the mean-reversion measure across 2y-30y: y = 0.6087 x + 0.6217, R^2 0.70; the 10y is less mean
  reverting than the 30y but has a similar ratio, so 10y is the best calendar. (Citi Research, US Rates Weekly, 17 Jul 2015.)
- Swap-spread fitted-curve residuals are preferable to quoted swap spreads as reversion indicators: zero presumed mean (a fair swap spread drifts
  with unobservable factors such as bank cost of equity). (Huggins and Schaller, 2024.)
- Cross-timezone and regime: weekly Wednesday closes over a rolling 52 weeks for cross-timezone pairs; R^2 of a PC1 on USD about 0.47 before 2023,
  about 0.76 after. (Citi Research, Asia FX and Rates Strategy, 13 Aug 2026.)
- Short-rate persistence: German yields 1972-98 have monthly autocorrelation above 0.98; two-factor persistence 0.95 (short-end factor) and 0.986
  (long-end factor). (Dunis, Laws and Naim, 2003, ch.3.) The 6m-3m US bill spread is strongly reverting (DF t -7.71, rho 0.33 per quarter; holding-yield
  error-correction speed -0.84 per quarter) while the 3m bill level is close to a random walk. (Wooldridge.)
- Ladder / grid identity: profit = (K - z^2)/2 with K the total absolute price movement and z the net change; any reversion to the start gives positive expected
  profit, an unbiased random walk gives zero; the killer is z^2 (inventory carried against a trend). Refreshing the ladder every 40 periods keeps over 80% of
  the profit but triples its standard deviation. (Chakraborty and Kearns, Market Making and Mean Reversion, 2011.)
- Rebalancing simulation: with weak mean reversion trend-following beats mean-reversion rebalancing; the optimal choice changes with correlations and
  central-bank reaction functions. (During, Fixed Income Trading and Risk Management, 2021.)
