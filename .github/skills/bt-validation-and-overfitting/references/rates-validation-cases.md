# Rates validation cases and market notes

Worked cases behind [SKILL.md](../SKILL.md): how published sell-side and practitioner work validated (or failed to validate) signals, with the numbers.
Treat levels as illustrative; the lesson in each case is the validation design.

## 1. ML timing models on UST with quarantine and permutation null
- **Design** (J.P. Morgan, Do androids dream of electric bonds?, 22 Nov 2017): contiguous walk-forward CV, test always later than train, the first n days of each test block dropped
  (n = holding period); train window expanded four times, test blocks about 1.5 years, 2009 to 30 Dec 2016; all of 2017 quarantined until final selection.
- **Result**: random-forest CV Sharpe above 1.2; on the quarantine, balanced RF 1.35 vs 0.38 for always-long; best single neural net 1.72 but the other four near always-long and one negative: the "million
  dart players" fallacy. Only RF and SVM-RBF beat the 95th and 99th percentile of the permutation null.
- **Permutation null** (3,000 shuffles of daily sizing at a fixed sell fraction): median threshold about 0.6 for always-long, 0.0 at 50/50, -0.6 always-short; the maximum over trials peaks near a 20% sell fraction at just under 0.95.
  During CV demand results well above the maximum; on the quarantine the 95th percentile suffices (avoids Type II errors). Residual Sharpe = model Sharpe minus the percentile, which behaves like a one-sample t-stat.
  The 10y bid/ask cost cut Sharpe by just under 0.1 (~10%). A swap-spread model above the 95th percentile but inside the Monte Carlo maximum earned only "tepid" confidence.
- **Update** (J.P. Morgan, Is bank convexity hedging lying in wait?, 31 May 2019): passive long Sharpe 2.5 over 8 months; the original model (trained to end-2016) Sharpe 1.1 selling about 35% of days, about 0.5 above the random same-sell-fraction benchmark;
  retrained through 3Q18 with no hyperparameter or feature changes: 1.27 selling about half of days, beyond 95% confidence.
- **Quarantine failure** (J.P. Morgan, TradeRunner, 16 Aug 2018; #SquadGoals, 21 Sep 2018): 2017-18 quarantine: 2y passive Sharpe about -2.0 with costs, classifiers about -0.8, 5y/10y GBM about flat, 30y about 0.5; the long bias learned in a secular rally failed in a sustained selloff.
  Stacked models reached about 0.5 and >99% shuffle significance versus 79% for a solo GBM. The 2y has high kurtosis, so shuffle tests penalise it in small samples. Exclude learners that are erratic in CV and in quarantine (KNN, single trees, simple ANNs).

## 2. PCA-residual and threshold backtests (rolling OOS by construction)
- **Swap-spread PCA dislocations** (BofA Merrill Lynch, A simple framework for swap spread relative value, 2 Jun 2016): decisions use only the past 250 days. US, threshold (sd) / cumulative bp / Sharpe / days / bp per day / average hold:
  1.0: 267 / 1.2 / 1,750 / 0.15 / 32; 1.2: 221 / 1.2 / 1,359 / 0.16 / 26; 1.4: 153 / 1.0 / 1,061 / 0.14 / 29; 1.6: 111 / 0.8 / 879 / 0.13 / 28; 1.8: 96 / 0.7 / 755 / 0.13 / 33; 2.0: 51 / 0.4 / 676 / 0.08 / 38.
  Germany: 1.0: 869 / 2.4 / 2,278 / 0.38 / 43; 2.0: 554 / 2.8 / 967 / 0.57 / 21 (Sharpe 2.5, 2.5, 2.7, 2.7 at 1.2 to 1.8). No costs, carry or stops; not back-tested on UK or Japan. A retroactive back-test without costs, carry, stops or intraday moves overstates; a realistic version needs a daily stop.
- **EGB PCA-residual screen** (BofA Merrill Lynch, Many EGBs, one simple value tool, 21 Mar 2018): Monte Carlo specification search over 1-15 PCs, hold 1/3/5/7/9 days, threshold 0.5x-3.0x z, scored on hit ratio and average spread change, no costs.
  Best hold 5-9 days, PCs 9-13; long hit ratio 56% at 0.5x to 71% at 3x, shorts about 50%. Chosen 11 PCs / 5-day / 2x: 2015 14 trades (long 71%, short 71%); 2016 33 trades (73%, 55%); 2017 16 trades (75%, 50%); the average 5-day long move fell from about 8bp to about 4bp.
  Lessons: the search is a trial family (count it); only the cheap (long) leg was reliable; high-threshold cells have few trades; expanding windows adapt slowly at regime change.
- **USD swap-rate PCA-residual pattern** (Burton, Dektor, Wheeler, Time Series Prediction of US Swap Rates, Stanford student paper, c.2008): train about 1994 to late 2007, test late 2007 to late 2008; Sharpe by tenor 0.4 (2y), 1.4 (3y), 1.2 (5y), 2.2 (7y), 0.8 (10y); the multi-swap Sharpe peaks at a window of about 500 days and fades beyond 1.5 years because the PCA basis drifts.
  A one-year test with no costs is unvalidated; choose windows from a broad range to avoid a random local maximum.

## 3. Hedge-weight and regression OOS checks
- **Fly weights** (Quantitative Finance Stack Exchange, butterfly 2s5s10s directionality Q&A, 2018, edited 2021): fit 1 Jan to 30 Jun 2016, test 1 Jul to 22 Dec on daily changes. Regression weights had the lowest OOS volatility, minimum-VaR almost the same;
  PCA ratio (-0.91, 2.00, -1.35), minimal-change PC1-neutral (-1.1002, 2, -1.0780), min-VaR (-1.48, 2.00, -0.38). Minimum variance is lowest in-sample by construction, so only the OOS comparison is informative.
- **GBP 2s10s regression hedge** (swapsball.net, Regression in finance: friend or foe?, 27 Oct 2017): betas on the last 122 days, test on the next 122; OOS R-squared about half; residuals show the model underestimates moves, which points to a missing variable, residual autocorrelation or drifting betas.
- **Corporate bond vs UST 30y regression hedge** (Tuckman, Serrat, Fixed Income Securities, 4th ed., 2022): 82 observations, beta 0.842 (SE 0.051, 95% CI 0.740-0.944, rejects 1), in-sample R-squared 77.5%, SE 2.00bp/day; OOS (17 May to 19 Jul 2021) SE 1.5bp. UST 10s20s30s fly residual SE 1.15bp in-sample vs 0.70bp OOS.
  Poor OOS means unstable coefficients; try a period before the window or an older analogous regime.
- **Rolling-beta illustration** (Dunis, Laws, Naim, Applied Quantitative Methods for Trading and Investment, 2003): the true beta drifts from -0.49 to 0.50 over 100 days; full-sample OLS -0.04 (R-squared 2%); last-50-day OLS 0.23 (61%); rolling OLS OOS R-squared 39.2%. A rolling regression measures an effect that may have long disappeared.
  Ridge cointegration hedge on 49 targets, 700/293 split: mean variance reduction 42% (median 53%) vs 24% (43%) for the market hedge, with some targets negative OOS. See [quant-regression-and-hedge-ratios](../../quant-regression-and-hedge-ratios/SKILL.md).

## 4. Macro and timing rules without a formal OOS split
- **Duration timing** (J.P. Morgan, Simple rules to trade duration, 2 Oct 2012): 3m momentum IR 0.3-0.7 depending only on the working day of the month used to rebalance; equal-weight combination IR about 1 vs average single signal 0.6;
  in-sample optimised weights 1.07 (look-ahead) vs about 1.03 equal weight, "only a little" better. Chosen weights (carry 35%, bond momentum 20%, three at 15%) gave IR 1.13 since 1990 and 1.06 since 1998. 12m momentum looked best because it was long 77% of the time in a bull market.
  JGB signals were weak (IR 0.3) but uncorrelated.
- **Rules tested without an OOS split** (Willer, Saunders, Trading Global Macro Markets, 2026): 55-day MA on a US 7-10y index IR 0.68 vs 0.55 (22d), 0.58 (200d), 0.47 (252d), 0.42 buy and hold; the authors state the lack of OOS split and costs and call for caution. Z-score windows of 3 to 10 years gave similar results for a valuation signal (a risk overlay, not a timing signal).
  A long JGB / short UST FX-hedged rule IR 0.72 vs -0.16 unconditional, mirroring the Bund-vs-UST rule: cross-market replication is a cheap robustness check.
- **Bond excess-return model** (Salomon Brothers, Understanding the Yield Curve Part 4, Aug 1995): expanding window from Jan 1955, first forecast Jan 1965, re-estimated monthly to Jul 1995; subperiod scaled Sharpe 0.72 / 0.75 / 0.87 / 1.10 (1965-74, 1975-84, 1985-94, 1990-95). Sample-period choice matters: use a neutral sample with similar start and end yields (Part 3, Jul 1995).
- **IC horse race** (Citi Research, Quantitative Framework for Regime Investing, 29 Oct 2021): score forecasts by IC, not by an optimiser backtest (which "can be sensitive to small forecast changes, risk models, constraints"): IC 0.0448 (levels), 0.0545 (changes), 0.0495 (both), 0.0758 (full model); long/short IR 0.29, 0.33, 0.35, 0.53.
- **Information analysis** (Grinold, Kahn, Active Portfolio Management, 1999): book-to-price quintiles were confounded by incidental bets (betas 0.92-1.12); the factor portfolio had beta 0.00, alpha 0.08%/month, t 0.59, IR 0.27, IC 0.01, none significant at 95%; implied breadth about 700 bets per year against 6,000 raw data items.
  Muller construction test: alphas = future return + noise at IC 0.1 predict IR 2.24; realised 0.86 (equal-weight top N) to 1.88 (QP). A simulation with a known IC is a valid test of any construction method.
- **Signal vs regime decomposition** (FinLab, Short-Term Mean Reversion Trading Strategy Backtest: The 3-Day Laggard Rule, Jun 2026): in 89 risk-on month-ends the laggard returned +5.13% vs leader +4.39% (laggard beat 57.3%, t 1.33, not significant): the returns came from the regime gate, not the signal. One OOS cycle at zero fees is not validation.
- **Evaluation target** (Cotton, Filtering bond and credit default swap markets, NYU Tandon seminar slides, 27 Apr 2016): apparent error vs the next print: last trade 0.020, univariate filter 0.0377, multivariate 0.0383; actual error vs truth: 0.056, 0.0512, 0.0286.

## 5. Cases where the specification was the finding
- **Persistent vs transient RV** (internal forward-curve-vs-straddle backtest spec v0.4, 23 Oct 2026): belly forward vol exceeded implied on 75-85% of days over 2015-10 to 2026-10 (structural carry, not RV); other structures flagged on 15-36% of days (transient, the genuine RV mirror). Gate: share of the last 252 days with the same sign <= 0.6.
- **Three-way cheapest-source test** (internal convexity-RV handover note, 2026): over 517 dates the cheapest source was listed 48.7%, curve 31.1%, swaption 20.1%, but the signals disagreed on only 1.59% of rows, and the median OTC-vs-listed basis (0.271bp/day) was far below the 2.721bp needed to flip a quarter of days: "nothing cleared the null".
- **Break-even costs**: headline books broke even at 1.21 / 1.63 / 1.35bp per leg against 0.25bp charged. Report break-even in bp per leg on gross DV01 traded.
- **Daily vs trade level**: a convexity factor was unidentified in daily P&L (t 0.9-2.1) but visible at trade level (t 2.1-5.4); where factors were collinear at the trade horizon (carry/slope, level/convexity) incremental R-squared was used.
- **Fitted-curve overfitting** (J.P. Morgan, The (par) curves they are a-changin', 23 Jul 2024): going from 6 to 12 knots reduced RMSE about 0.5bp; the new model's average RMSE was 2.5bp (65%) lower than the legacy one; rising RMSE can be a basket artefact (illiquid, tiny-free-float bonds) rather than a worse market.

## 6. Market-specific notes (G10)
| Market | What matters for validation |
|---|---|
| USD | Largest sample, but regime-heavy (ZIRP, QE, QT); overnight repo and issue specialness belong in P&L; futures settlement vs end-of-day snap mismatch (1.82bp/day noise vs 0.55bp true moves in one case) fakes signals; early-LIBOR to RFR splice, so start samples after seams; the 2y has high kurtosis and penalises shuffle tests in small samples. |
| EUR | Country effects (DE/FR/IT/ES/NL): test across the EGB universe, not one bond; swap-spread dislocation Sharpe above 2 in one study (BofA, 2016); Bund asset-swap seasonality not significant 2007-2017 (swapsball.net, 2017); EGB cash-flow trades need a robustness grid by country, bucket, year and cash-flow size (J.P. Morgan, Follow the cash flow, 15 Sep 2015). |
| GBP | Regression hedges to USD factors checked 122d/122d OOS; LIBOR to SONIA transition shortens the clean sample. |
| JPY | Yield-curve control is a distinct regime: results inside it are one observation of the effect; JGB signals have weak IR but low correlation to the rest. |
| CAD | CDOR ceased 28 Jun 2024 and futures converted to the compounded-RFR contract at a fixed spread: treat as a seam. |
| AUD, NZD | Bank-bill benchmarks and shorter futures histories: fewer independent observations; use descriptive reporting below the 20-trade floor. |
| CHF, SEK, NOK | Thin liquid history and wide costs: validate with cross-market replication (same rule on neighbours without tweaks) rather than local tuning. |
