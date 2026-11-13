# Venues, execution cost, timing and leg risk

Companion to [SKILL.md](../SKILL.md). Most cost and liquidity levels below are dated and come from one market or study.
Treat them as calibration examples and refresh them from `trades` (slippage_bp) and `bond_quotes` before use.
Corporate-bond and index-CDS results are method only. Their levels do not transfer to G10 rates.

## 1. Venue and protocol

**Protocols (Benos, Payne and Vasios, Bank of England Staff Working Paper 580, Jul 2016; Riggs, Onur, Reiffen and Zhu,
Journal of Financial Economics, 2020):**
- Central limit order book (CLOB): anyone can post; prices are firm; price-time priority.
- RFQ: a client requests quotes from several dealers. Minimum rule: at least 2 dealers during phase-in to Oct 2014, then at
  least 3. Dealers cannot see each other's quotes or how many were asked, so an RFQ behaves like a first-price sealed-bid
  auction. Work-up follows an execution.
- RFS (request for stream): the client sees streaming indicative two-way quotes and hits one dealer, who can accept or
  reject. Like FX last-look.
- Moving from CLOB to RFQ to RFS shrinks the set of participants who see the order. None is anonymous after the trade.
- Exemptions from the RFQ-to-3 rule include block trades, non-MAT contracts and packages.

**Quote type by product (Burgess, Electronic Rates Markets and Low Latency Interest Rate Swap Calculations, SSRN, May 2022;
SEF rulebook, Chapter 9, Rule 901 swap specifications, undated):**
- Standard swap on a SEF: par rate, or spread over the benchmark government bond.
- IMM swap on venue: cash NPV.
- Bespoke or OTC swap by RFQ or voice: cash NPV.
- MAC (market agreed coupon) swaps round the fixed coupon to 25bp, so CCPs can compress and net them.
- Spread vs UST, spreadover, rate switch, spread switch and butterfly are separate transaction types on some venues. Check
  the product type in the SDR fields before reading volume.

**Choosing voice or electronic (Hendershott and Madhavan, Click or Call?, Journal of Finance, Feb 2015): framework only.**
Price of an auction p_a = q (p0 + s) + (1 - q)(v + pi), where q = P(no dealer responds), s = information-leakage cost on
failure, pi = dealer inventory premium, and d = dealer markup. Choose voice iff q s + (1 - q)(pi - d) > 0 (for sells the
buy/sell differential is added). Leakage rises with size, so electronic wins small tickets and voice wins above a critical
size. Use the rule to rank routes for a given size. Do not use the study's bp levels for rates.

**Dealer behaviour in RFQ (Riggs et al., 2020; index CDS, May 2016, method only):**
- Average 4.1 dealers queried and 3.6 responses. 92% of RFQs trade. Three dealers in about 45% of sessions.
- Response about 90% with 3 to 5 dealers and about 80% with 6 or more.
- A standard size lowers RFQ probability by 18.3%. Size signals urgency.
- Client choice of k dealers: maximise E[max_j beta(z_j)] - c (k - 1). Without a per-dealer cost c the optimum is k = n, so an
  explicit cost is needed for an interior answer. The winner's-curse term grows with k.
- For large single tickets, a single dealer may beat a multi-dealer request. Multi-dealer requests create a winner's curse:
  dealers price in their hedge cost, and the second dealer is told "were cover" (Düring, Fixed Income Trading and Risk
  Management, 2021).

**Cash UST interdealer venue (Fleming, Mizrach and Nguyen, Federal Reserve Bank of New York Staff Report 381, Jul 2009, rev.
Mar 2017):** a limit order book with price-time priority and a $1mm minimum. Walking the book is rare (under 0.5% of marketable
orders sweep more than one level). Workup extra size trades at the same price, so do not count workup prints as separate
trades. Cancellation rates exceed 95%.

## 2. Blocks, capped notional and dealer offsets

- Median DV01-adjusted trade size is roughly constant across tenors, at about $30 to 50k DV01 for G4 swaps. Use separate
  thresholds for G4 and non-G4 currencies (Fleming, Jackson, Li, Sarkar and Zobel, FRBNY Staff Report 557, Mar 2012, rev. Oct 2012).
- Large trade = above the 95th percentile by currency and tenor bucket, and only trades that add to the dealer's running
  risk. Dealer offset ratios after large spot swaps (30m / 1h / 4h / 8h): USD 0.5 / 0.5 / 0.7 / 0.7; EUR 0.7 / 0.7 / 0.6 /
  0.5; GBP 0.6 / 0.6 / 0.5 / 0.5; JPY 0.7 / 0.6 / 0.4 / 0.3. About 60% of large-trade DV01 offsets within 30 minutes.
  For a buy-side ticket, the dealer's hedge and your market impact arrive in the first half hour.
- In the reporting data studied, SDR-reported USD IRS notional is capped at about $110k DV01 per trade, and RFQ blocks
  typically run about twice that cap. A trade reported at the cap without a block flag was executed on a CLOB-style platform
  (Clarus, Identifying Customer Block Trades in the SDR Data, Oct 2015). Public data understate the largest prints.
- Splitting a large off-the-run order across dealers worsens future quotes (bilateral etiquette and price discrimination of
  toxic flow). Large trades cluster when market makers are willing to quote large size at good prices (Federal Reserve Board,
  FEDS 2025-049, Trading Costs v. Indicative Liquidity in the Off-the-Run Treasury Market, Jul 2025).

## 3. Bid/offer, impact and margin by structure

**Dated bid/offer and quote-width references (refresh before use):**
- Standard USD swap on a venue: "typically 1/10th of a bp" (Burgess, SSRN, May 2022). The same paper also writes 0.001%,
  which is 0.001 percentage points = 0.1bp. Read the unit before using it.
- Non-transparency: the standard deviation of dealer mids was 0.07bp for 5Y EUR IRS and 0.65bp for 5Y SEK IRS, which has no
  order book (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, Ch.18).

**Outright and structure margins (Darbyshire, 3rd ed., 2022, Ch.19, risk-based margin LP; model inputs, not quotes):**

| Structure | Margin, bp of DV01 (as printed in the source) |
|---|---|
| Outrights 2Y / 5Y / 10Y / 30Y | 0.4 / 0.5 / 0.5 / 0.6 |
| Spreads 2s5s / 2s10s / 2s30s / 5s10s / 5s30s / 10s30s | 0.25 / 0.45 / 0.85 / 0.25 / 0.7 / 0.55 |
| Flies 2s5s10s / 5s10s30s | 0.5 / 0.6 |

Sub-additivity rule: a spread margin must be strictly below the sum of its component spreads (2s10s < 2s5s + 5s10s). Otherwise
the solution is non-unique and the longer spread is never used. Solve with a linear programme. Square-root impact is added
outside the LP. Use these as a shape check on your own model, not as market levels.

**Price-taking margin (Darbyshire, 3rd ed., 2022, Ch.18): model structure.**
- Equilibrium margin X = max(Z + 1.15 T, C + 1.71 I + 0.5 T). Z = market-wide margin; C = interbank hedge brokerage;
  I = impact or information content; T = non-transparency (dispersion of dealer mids). The first term dominates for
  low-information, uncertain trades. The second dominates for high-information trades.
- Tradable margin when N dealers quote bid-offer 2X with mids dispersed by sd T: 2 (X - g(N) T), with g(2) 0.564, g(3) 0.846,
  g(4) 1.029, g(5) 1.163, g(7) 1.352, g(8) 1.423, g(9) 1.485, g(10) 1.539. The printed g(6) is out of sequence, so verify
  it before using it.
- Four trade categories (same chapter): small MAT trades (margin = Z); very large benchmark trades (high information,
  transparent); small off-the-run (ask as many dealers as possible and assume the request is broadcast); large off-the-run
  (alternate competitive and single-dealer quotes to withhold information).
- Hedge-cost ranking, lowest to highest: benchmark vs non-standard tenor; few vs many hedge instruments; smaller vs larger
  than average; exposure to isolated events such as central-bank meetings and speeches.

**Impact and inventory (square-root law: J.P. Morgan, Drivers of price impact and the role of hidden liquidity, Jan 2017;
add-on model: Darbyshire, 3rd ed., 2022, Ch.19):**
- Square-root add-on: impact = alpha sqrt(|x|) per unit; average cost = (2 alpha/3) sqrt(|x|). Incremental add-on when the
  inventory moves from x1 to x2 = (2/3) alpha (|x2|^1.5 - |x1|^1.5). Worked: alpha = 1/1000 with inventory from 50,000 to
  100,000 gives 13,628. The implementation is in the cost script of the bt-transaction-costs skill.
- Normalised impact (same study, US Treasuries by trading session): the square-root law holds, with slopes about 0.57 in NY and
  0.61 in Tokyo. Power-law fits of impact in 32nds on net imbalance in $mn: Tokyo y = 0.0589 x^0.7624, London y = 0.038 x^0.782,
  NY y = 0.0146 x^0.8815, so the Tokyo session has the highest intercept. The FOMC full-day slope was 0.83 against 0.58 on all days.
- Inventory: a second same-direction trade is priced on the post-trade book. Worked: a 100mm 5Y5Y margin rose from 33,405
  (0.78bp of delta) to 46,252 (1.08bp) once impact was added (Darbyshire, 2022, Ch.19, model example).
- Negative add-ons must be floored at zero. In one example a reverse-request add-on of -4,816 was floored; the source
  reports dealer profit of 32,454 against an intended 50,000.
- Venue split (O'Hara, Market Microstructure Theory, 1995, sec 8.2): divide a large order across venues in proportion to
  1/lambda_i, where lambda_i is each venue's relative price impact. Do not split equally.
- Trade-only impact studies overstate impact by 20 to 50%, because limit orders carry information too (Fleming et al.,
  FRBNY Staff Report 381).

## 4. Timing calendar

| Event | Observed effect | Execution rule |
|---|---|---|
| IMM expiry (3rd Wed of Mar, Jun, Sep, Dec) | DV01 migrates from swaps to futures at the back and from futures to cash and FRAs at the front. The front-end stub is hard to hedge | Roll 3 to 4 sessions before expiry. The Friday before expiry carried over 21% of IMM risk, and the four busiest sessions over 71% (Clarus, The IMM Roll for Swaps, Mar 2015) |
| IMM roll volume | Naive roll estimates overstate volume. For 5y USD, the naive roll was $26.5bn, and the naive all-tenor DV01 was $73.5m against $39.9m trade-by-trade (Clarus, Mar 2015) | Match trades by timestamp and benchmark maturity, not by a notional share |
| SR3 roll | Roll between the second and third listed contract. Dec-19 into Mar-20 cost 138bp at the end of the reference quarter vs 4bp at the start, an extreme case after a sharp fall in SOFR (Huggins and Schaller, SOFR Futures and Options, 2022) | Roll before the reference quarter starts |
| Treasury futures delivery | First position (intent) day = 2nd business day before the delivery month; first notice day = the business day before it. Older texts call the earlier date first notice day (Burghardt et al., The Treasury Bond Basis, 2005; Citi Markets Futures Sales, Aug 2026) | Longs roll by the close before the first intent day. Sep/Dec 2026 roll: busiest 21 and 24 to 26 Aug, about half rolled crossing 25 Aug. Check position limits and the allocation rule for your contract |
| Central-bank decision (FOMC) | Depth drops and volatility rises around the decision. Post-FOMC 60-minute impact higher for buys (+48 to 118%) and sells (+24 to 134%) in the cash-Treasury sample, where the statement came at 14:15 ET (Fleming et al., FRBNY Staff Report 381); check the current release time | Default (house rule, reason: the impact figures above): no size crossing in the 60 minutes around a decision unless the trade is for the event |
| ECB decision (EUR) | Late-day repositioning and heavy day-after volume (EUR 27.1m DV01 over the two day-after sessions vs a EUR 10.1m daily average) | Repositioning came late on the decision day and the day after, so a hedge timed for the decision day alone misses it (Clarus, ECB June Meeting, Jun 2014) |
| EUR intraday liquidity | Runs about 08:00 to 19:00 CET, with a lunchtime lull and a 15-minute peak at 16:00 to 16:15 CET (more than 3x average risk) (Clarus, ECB June Meeting, Jun 2014) | Size EUR trades in the peak window, not in the lunchtime lull |
| Data releases | Depth thins into 8:30, 10:00, 13:00, FOMC and 15:00 (ET) events (Fleming et al., FRBNY Staff Report 381). Payroll-day impact slopes were not significantly different from normal (J.P. Morgan, Jan 2017) | Avoid executing size into scheduled prints; plan size for the window after |
| Auction cycle | Special premia cluster around auction dates. Specialness peaked about 156bp the day before a 10y reopening in one worked example (Tuckman and Serrat, Fixed Income Securities, 2022). A positive tail (stop above when-issued) signals weak demand | Check tails and results timing before trading the bond leg. Results are visible only after the results timestamp |
| Month-end, quarter-end, tax dates | Repo specialness and funding spikes at the turn (Tuckman and Serrat, 2022) | Check the financing leg for the period before entering. Avoid unhedged term funding across the turn |
| Fixings | A mismatch between the hedge's fixing dates and the exposure is the main hedge error in the STIR examples (Huggins and Schaller, 2022). EURIBOR fixes two TARGET business days before the effective date (SEF rulebook, Rule 901) | Match fixing dates to the exposure; close a hedge at the end of the exposure, not after |

## 5. Leg risk and sequencing

- Never leg a closing spread: "the first cut is always the cheapest" (Aikin, STIR Futures, 2nd ed., 2012). When opening a term
  spread, go to the least liquid point first.
- Auto-spreaders leg outrights, which creates legging risk and can attract order-traffic penalties. Avoid them in volatile
  markets (Aikin, 2012).
- EFP and basis packages remove most leg risk when the futures and cash legs trade in one ticket. A leg-in leaves the basis as
  a residual (Burghardt et al., 2005).
- Implied prices vanish when you need them. Lean against implieds and net matrix trades on paper first. Implied-upon-implied
  is not exchange-supported (Aikin, 2012).

## 6. G10 differences that change execution

| Market | Execution-relevant difference | Source |
|---|---|---|
| USD | SOFR futures $25/bp per $1mm; SR1 and fed funds $41.67/bp per contract; SEF mandate for spreadovers since Jun 2014 (about 89% on-SEF in 2015); USD IRS notional capped in SDR data | Huggins and Schaller (2022); Clarus, Spreadovers (May 2015); Clarus (Oct 2015) |
| EUR | EUR IRS clears at LCH (use its curve as truth); EUR SEF share 20 to 40%; intraday peak at 16:00 CET; annual fixed swaps vs semi-annual BTPs | Darbyshire (2022), Ch.6 Ex 6.1; Benos et al. (Jul 2016); Clarus (Jun 2014); Düring (2021) |
| GBP | Gilt reopenings create "5y" bonds with 4.5y left, so use exact date matching; GBP IRS fully on SONIA, with no LIBOR-era basis | Clarus, Asset Swaps (May 2015); Darbyshire (2022), Ch.20 to 22 |
| JPY | Onshore clearing required (JSCC), so the JPY cross-CCP basis is regulatory-driven; price discovery in JGBs sits in futures, and the 10y JGB has no natural investor base; minimum swap size 2.5bn with 100mm increments (legacy table) | J.P. Morgan (May 2016, JSCC clearing); Düring (2021); tpSEF Appendix B (legacy tables) |
| AUD | Cash-settled bond futures quoted in yield; swap plus futures is a standard inter-dealer package with the EFP spread as the measure; FRA discounting uses the AFMA yield method; minimum swap 25mm with 100k increments (legacy table) | Düring (2021); tpSEF Appendix B (legacy tables) |
| CAD | Spot T+0; CORRA on Act/365 (CDOR in the legacy rulebook has since been discontinued); Toronto calendar; spread quoted vs Government of Canada securities | Tradeweb SEF rulebook (Rule 901) |
| SEK | No order book or exchange for 5Y SEK IRS; non-transparency 0.65bp vs 0.07bp for EUR; priced off EUR/USD and other factors; 50mm 5Y example quoted 0.989 / 1.011% | Darbyshire (2022), Ch.18 |
| NOK | 2Y benchmark has few contributors and periods with no trading; Bayesian reference reset when the opaque market prints | Darbyshire (2022), Ch.19 |
| NZD, CHF | Only minimum sizes (5mm with 100k increments in the legacy table) and no execution data in the sources | tpSEF Appendix B (legacy tables) |

Legacy caution: the SEF minimum-size tables are LIBOR-era (before the change to RFR indices). Verify them against the current
rulebook before use.
