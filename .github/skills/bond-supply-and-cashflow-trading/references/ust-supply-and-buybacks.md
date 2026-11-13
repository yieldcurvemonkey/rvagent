# US Treasury supply machinery, buybacks, bills and the debt limit

Detail behind `SKILL.md`. Dollar figures are as published in the cited notes; 2026 episodes are recent and the
long-run structure matters more than the levels.

## 1. Issuance process and calendar (knowable ahead)

- **Quarterly Refunding Announcement (QRA)**, first week of Feb/May/Aug/Nov: financing estimates Monday 15:00 ET, refunding
  statement Wednesday 08:30 ET. Gives coupon sizes by tenor, the 2y FRN size, expected TIPS sizes, and only an aggregate
  net-bill number for the quarter. Treasury may over-issue while rebuilding the TGA and under-issue while drawing it down;
  it publishes a TGA forecast for the next two quarter-ends (BofA, US Treasury auction primer, 8 Mar 2024).
- **Schedule.** Bills 4/8/13/17/26w weekly, 52w every four weeks, cash-management bills ad hoc; bill sizes announced Tuesday
  and Thursday for settlement the following week. 2y/5y/7y issue month-end, 3y on the 15th, 10y/30y auction in week 2 and
  issue on the 15th (new in Feb/May/Aug/Nov, reopened otherwise), 20y auction next-to-last Wednesday. TIPS: 5y new
  Apr/Oct, 10y new Jan/Jul, 30y new Feb; 2y FRN new Jan/Apr/Jul/Oct. Reopenings exist since 2000 (BofA primer; Tuckman &
  Serrat, Fixed Income Securities, 4th ed., 2022).
- **Auction announcement** carries offering amount, dates, max award, SOMA maturing amount and close times. Coupon sizes are
  usually known from the QRA ahead of it.
- **Settlement drains reserves**: on the issue date the dealer's reserve account is debited. Repo rates rise on bill/coupon
  settlement days, more so with scarce reserves and when they coincide with quarter-ends (Federal Reserve Board, FEDS Notes,
  What Happens on Quarter-Ends in the Repo Market, 6 Jun 2025).
- **Duration supply gauge**: weekly duration supply net of central-bank purchases and buybacks in $mn/bp vs the prior-year
  weekly average, by market. Week of 5 Oct 2026: G4 about $101mn/bp vs $48mn/bp the week before (~1.2x the 2025 average);
  UST ~$70mn/bp net of buybacks (~1.7x); EGB ~$9mn/bp (0.3x); gilts ~$2mn/bp (0.4x); JGB ~$20mn/bp net of BoJ (~2x)
  (Goldman Sachs, US Rates: The Week That Was, 2 Oct 2026).

## 2. Auction mechanics and scoring

- **Single-price (uniform) auction.** Lowest yield filled first, all at the stop-out (high) yield; bids at the stop are
  prorated. Example: offering 100; bids 3% x30, 3.5% x50, 4% x20, 4.5% x10 gives stop 4%, first three filled, the 4.5% bid
  gets nothing (BofA primer). Max award 35% of the offering; non-competitive capped at $10mn; NLP reportable when bids plus
  NLP reach 35%.
- **Tail / through.** `tail_bp = (stop_yield - wi_yield) x 100`. Stop above WI = tailed (weak); below = through (strong);
  equal = on the screws. Duration-adjust tails across tenors (long maturities tail more); meaningless when non-competitive
  bids are large (BofA primer; Düring, Fixed Income Trading and Risk Management, 2021).
- **Allocation.** PDs bid pro rata, so high PD takedown is weak; high directs (real money via non-PD access) strong;
  indirects proxy foreign demand for coupons but not for bills (funds without direct access dominate). Investor-class
  allotments post around the 7th business day of the month. FIMA bids come out of the offering; SOMA rollovers are an
  add-on and "should have no impact on the success of an auction".
- **Bid-to-cover** is imperfect: dealer bids placed far above the expected stop inflate it, self-bids and a larger new-issue
  premium can "buy" cover. No single indicator is sufficient (Düring 2021).
- **Preview checklist**: previous tail, bid/cover, direct/indirect and end-user/foreign/investment-manager shares vs their
  3- and 6-auction averages; yield change since last auction; sector richness vs wings adjusted for rate level and curve
  shape; WI roll vs carry erosion (J.P. Morgan, US Treasury Market Daily, 25 Feb 2020).
- **Strength screen.** Strong auction = average z-score of tail/through, investor takedown, bid-cover over the last 2
  auctions; two consecutive strong 10y auctions were followed by higher 10y yields (small sample; Citi, US Rates Weekly, 9 Oct
  2026). Use `scripts/supply_arithmetic.py strength`.
- **10y refunding tail model**: foreign takedown regressions (previous-three average: y = -12.19x + 2.6219, R2 0.22;
  contemporaneous: y = -11.482x + 2.7495, R2 0.48), plus 1m change in global surprise index and in USDJPY; logistic
  classifier accuracy 64% in sample (Citi, US Rates Weekly, 2 Aug 2019). Yield change into the auction had no predictive
  power. Tiny samples: use as colour, not as a signal.
- **Dealer behaviour.** Dealers underwrite then distribute: net positions peak in the auction/issuance week and decline
  after; auction-week volume is more than twice any other week. Dealer share of 10y auctions fell from up to ~80% to ~17%
  (Federal Reserve Bank of New York, Liberty Street Economics, Dealer Trading and Positioning in FRNs, 26 Mar 2018; Conks,
  The Coming Volatility Suppression, 5 Sep 2023).

## 3. Auction-week seasonality and the supply grid

- **10y seasonality by week type** (Citi, US Rates Weekly, 20 Apr 2018; since 2014; median bp / % of weeks the 10y rallied):
  first week of month +2.7 / 46% (sells off, pre-positioning); 3s/10s/30s week -1.9 / 56%; TIPS week -0.1 / 50%; empty
  week -3.9 / 69%; 2s/5s/7s week -0.9 / 53%; final week -7.4 / 86%.
- **Forward 6-week DV01 supply terciles** (same source), next-1w 10y change median/avg/% rally: lowest tercile -3.3/-2.1/63%;
  middle +1.4/+1.6/47%; top +1.5/+1.2/46%. Next-2w: -2.3/-1.1/61%; -0.4/+0.8/52%; +1.8/+1.3/46%. The market prices
  supply 4-6 weeks ahead; the 2-week horizon is stronger.
- **Entry/exit grid on curve trades** (BofA, US Treasury auction primer, 8 Mar 2024; last 12 10y auctions): 2s10s steepener
  best average entry -9 / exit -3 = +3.5bp (next -9/-5 +3.1bp); exiting after the auction loses (entry -3 / exit +5 =
  -5.8bp); hit ratios 55-58%, Sharpe 21-39%, Score (hit x Sharpe) low (best 23%). 2s10s flattener best cell entry -3 /
  exit -1: Score 52% (Sharpe 69% x hit 75%), +2.9bp (the text says "2s20s" but the exhibit is 2s10s, probably a typo). 2s5s10s
  fly long belly: entry -9 average +1.9 to +4.8bp, best at exit -1; best Score 49% at -3/-1. Short belly Score at most ~25%.
- **The sign flipped between samples.** In the 2022 edition (BofA, UST RV Primer, 2 May 2022) 2s10s steepeners around the
  last 12 10y auctions were mostly negative (-10/+10 at -11.9bp, hit 8-50%), while short belly in 2s3s10s gained (-8/+10
  +13.3bp, hit above 70%). 12 observations and a regime-dependent sign: never trade a single cell; require the cell
  neighbourhood and the regime to agree.
- **Off-the-run/roll cycle** (J.P. Morgan, US Rates Strategy: Times like these, 10 Feb 2016): on-the-run 5s outperform old 5s
  about 0.8bp in the two weeks after auction, then cheapen about 0.7bp in the two weeks into the next auction (avg of 12
  cycles). Monthly issues (2/3/5/7y) cheapen most off-the-run; in 10s/30s reopenings cheapen the OTR over the cycle.

## 4. Specialness and the new-issue cycle

- `special_spread = GC_rate - special_rate` (term-specific). 10y OTR cycle (new issue Feb/May/Aug/Nov, reopened after 1 and
  2 months; 51 notes, Nov 2008-Jul 2021): low right after auction, peaks at 156bp the day before the first reopening
  (2-sd band 116-196bp), 48bp before the second reopening, below 20bp before the next new issue. Mechanism: liquidity
  migrates to the new OTR and dealers short the OTR to hedge purchases at the upcoming auction; short demand vanishes after
  the reopening (Tuckman & Serrat 2022, Ch.10).
- Overnight special spreads on 27 May 2021 (bp) for 2y/3y/5y/7y/10y/20y/30y: OTR 5/1/13/9/3/2/4; old 2/2/2/1/11/2/12;
  double-old 2/10/6/8/10/2/3; triple-old 2/12/2/3/3/2/2 (same source). Fails penalty is max(0, 3% - fed funds), which
  is why cash lenders accept negative rates to borrow a bond.
- **Reopening RV**: around a reopening the security stays on-the-run and outperforms older off-the-runs for a few weeks.
  Buy $100m OTR 10y financed in repo, short $100m off-the-run via reverse repo; dealer charges 5.75% repo on the long and pays
  5.55% reverse repo (20bp dealer spread); closed after about a week, "banked around $2 million". The carry cost is the
  repo minus reverse-repo spread; a zero-haircut sponsored arrangement lets a fund run $200m with no own cash, a 2% haircut
  needs $4m (Conks, Demystifying the Repo Market Part III, 28 May 2024).
- **5y futures template** (Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005): the 5y CTD is usually the old 5y, so the
  OTR basis proxies OTR/old. Buy the OTR 5y basis early in the cycle, sell it late; the OTR cheapened about 5bp vs the old
  5y in the 1.5 months before the next auction (four semiannual cycles 2000-2002). Selling is negative carry when the OTR is
  special. A special new issue can flip short-basis P&L: May-Jun 2000, short $10mm old-5y basis +$14,211, short $10mm
  new-5y basis -$14,276 (nearly $11,000 from the lower reverse-repo rate). Always model own-issue repo, not GC.
- **1986 squeeze (9-1/4% 2/15/2016)**: crowded "obvious" short of the old long bond vs the when-issued; spread went from
  25-40bp through to over 100bp; basis widened about 6 points. Special rates have no floor (10y CTD at -15% overnight repo,
  May 2005).

## 5. Buybacks

### Programme facts
- Restarted 2024 via the NY Fed; funded from TGA cash or other issuance, not reserves; aims liquidity support (>2y, 1-2x per
  quarter) and cash management (<2y, ad hoc); 9 buckets; max $30bn/quarter at launch; excludes CTDs, specials, very rich
  issues, OTRs and near-off-the-runs; WAM unchanged in design (BofA primer). Quarterly allocation at launch: 0-2y $34bn;
  nominal buckets 2-3, 3-5, 5-7, 7-10, 10-20, 20-30y $4bn each; TIPS buckets $1bn each.
- Buybacks move the CTD: an announcement richens the targeted long sector and flattens the deliverable curve, a
  nonsystematic spread move that raises switch-option value (Burghardt 2005). January 2000: the 8/27 minus 11/18 yield spread
  moved from -13..-7bp to -17bp and the CTD switched.

### August-October 2026 episode
- 19 Aug 2026: long-end (10-20y, 20-30y) buybacks upsized from $2bn to at least $4bn per operation (9 Sep-4 Nov), quarterly
  schedule $52bn from $38bn, "at least $16bn/quarter" about 14% of 20y+30y gross supply; off-cycle, mid-quarter, about two weeks
  after the QRA, framed as liquidity support; expected to be bill-funded (FT, 19-21 Aug 2026; Citi, Top of Mind, 21 Aug 2026;
  J.P. Morgan, Buying back time, 19 Aug 2026).
- Reaction: 30y -8/-9bp (to 5.21%), 10y -4bp, DXY -0.7%, 3m/6m bill yields up, curve flatter; round-tripped above the
  starting level by next afternoon (30y +6bp to 5.24%); half-life about one day (FT, 20 Aug 2026; Wall Street Journal, 24 Aug
  2026). A 20y auction the same day: $16bn at 5.204% vs 5.199% WI (0.5bp tail), cover 2.53 vs 2.66 YTD.
- Netting: gross 20y+30y issuance Aug-Oct $111bn; doubling previously scheduled ops is a >= $6bn change; net 20-30y supply $97bn
  vs $103bn, "doesn't really move the needle" (Financial Times Alphaville, 20 Aug 2026). The signal (an implied ~5.30% 30y
  tolerance, bigger buybacks or coupon cuts if broken) matters more than the size (Citi, GAA House Views, 21 Aug 2026).
- Late-Sep 10-20y operation took the full $6bn against $46.4bn offered (vs ~$10.5bn at the prior two), only two CUSIPs bought:
  record offers concentrated in few CUSIPs read as holders de-risking (bearish), liquidity support not an aggressive bid
  (Goldman Sachs, The Week That Was, 2 Oct 2026; BofA, Global Rates Weekly, 2 Oct 2026). Execution price paid vs 2pm mid ran -0.08 to
  -0.01 across operations.
- Escalation ladder (Citi, US Rates Weekly, 21 Aug 2026): bigger buybacks; signal no coupon increases (lean on bills); cut
  20y/30y auction sizes into the front end/belly/bills; end the 20y (least likely). The 20y benefits most.
  Supply-cut trade seen: long 20y / 10s20s steepener at -30bp, target -15bp, stop -40bp (Citi, 2 Oct 2026).
- TBAC-style buyback score: 1y z-scores of (offer-to-max ratio, RMSE of the spline fit by sector, off-the-run discount); a
  near-average score means no market-functioning need (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026).
- Judge an intervention by what it responds to: plumbing (failed auctions, dealer balance-sheet seizure) is legitimate; a
  price-level response is treated as price management and faded (Wall Street Journal, 24 Aug 2026). Buybacks financed with
  bills are not WAM-neutral: bill supply up, 3m/6m up, front end cheaper, curve flatter.
- Swap-spread read: long-end buybacks act through RV (compressed long-end spline errors, wider 30y swap spreads) rather
  than outright yields; they affect the Treasury leg only (Barclays, Swap spreads: The Bright Spot in US rates, 30 Sep 2026).

## 6. Financing waterfall, bill share, TGA

- Marketable borrowing need = deficit + other adjustments + change in cash. **Net coupon supply** = gross coupons -
  (public coupon maturing = total maturing - Fed rollover) - buybacks. **Net bill supply = borrowing need - net coupon
  supply.** Net supply to public adds Fed runoff (BofA, Lower UST WAM => backdoor easing, 2 Jul 2025).
- FY25/FY26/FY27 (BofA): deficit 1,925/2,000/2,050; TGA end 850/950/1,000; borrowing need 1,819/2,100/2,100; gross coupons
  4,384/4,395/4,395; net coupon 1,505/1,275/1,033; net bills 314/825/1,067 (checks: 2,100-1,275 = 825); bill share 21.4%/
  22.6%/24.3%. Stable vs growing coupons means $1,003bn less 10y-equivalent issuance in FY26-27, ~30bp lower 10y.
- Bill-share tolerance: TBAC guidance 15-20%; 22.4% long-run historical share cited in 2023; BofA ~22.5% rough upper
  tolerance; Conks "up to 25% barely raises rollover risk, 30% or more is pushing it"; average 17% since the GFC, 22.5% since
  1980 (BofA, UST supply & demand in '25, 26 Nov 2024; Barclays, US short interest rate primer, Jan 2025; Conks, The Great
  Rebalancing, 16 Jul 2025).
- **Bill-OIS: model the flow, not the stock.** 3m change in bill supply vs 3m bill-OIS (2015-23) loosely positive: big
  paydowns take bills to about -50bp rich, big issuance about 0 to +15bp; the bill share is only loosely correlated with spreads
  (Barclays 2025). Indirect-bidder takedown by bill tenor (1m rolling) proxies money-fund demand; in a hiking-risk regime funds
  shorten, 3-6m bills cheapen to OIS while 1m is rich (BofA, Bills: policy & supply uncertainty = cheaper, 1 Oct 2026).
- **Debt-limit sequence.** Near the limit coupons stay on schedule, bills are cut, TGA is drawn, cash rises and collateral is
  scarce. After resolution the TGA rebuild drains cash and a wave of (mostly bill) supply pushes funding rates up. 2023
  precedent: about $500bn of bills in a month absorbed with tight bill-OIS (auctions ~3x covered); pre-resolution bills
  maturing just after the x-date cheapened about 450bp vs just before. 2025 rebuild: up to $1tn of issuance, TGA target $850bn
  vs $345.3bn on 22 Jul 2025; bill-OIS expected to widen only a few bp (up to 6bp).
- **Analog event study** (BofA, Funding & debt limit: history lessons, 27 Jun 2025): (1) pick episodes by matching state
  variables (ON RRP excess liquidity, % growth in bill and total UST supply; merge episodes five months apart); (2) average
  1m/3m/6m change after resolution; (3) separate stress episodes (2019). Average changes (bp, 1m/3m/6m): SOFR minus FF
  7.7/4.4/5.1 higher; SOFR-IORB +3.0/+5.1/+5.7; 3m bill-OIS cheaper 3.6/1.5/4.2. Condition on the RRP buffer: 2021 and 2023
  are not comparable because excess RRP liquidity was huge. Expected 2025 impact: SOFR-IORB up at least 5-12bp, SOFR/FF
  tighter 4-8bp, 3m bill-FF OIS cheaper 2-4bp. Trade seen: short Oct SOFR/FF vs entry -4bp, target -8bp, stop -1bp.
- 2025 bill path (BofA, X-date shift: now late August, 7 Feb 2025): $800bn+ of bill paydowns Feb to end-July, almost $1tn
  of bill supply Aug-Dec; cumulative bill supply bottoms about -$620bn in July. X-date = when extraordinary measures (about
  $315bn) and the TGA are exhausted; the forecast is highly uncertain until after the April tax date.
- Stripping non-TGA cash: routine injections (e.g. home-loan-bank cash) depress money-market rates temporarily. After
  quarter-ends and tax dates distortions are not trend.

## 7. Supply to spread regressions (US)

- **Front end vs private supply** (Citi, US Rates Weekly, 4 Oct 2019): OIS/2y UST and 2y swap spread regressed on 12m rolling
  private UST supply ex-Fed: R2 0.69 and 0.64; swap spread R2 0.61 coupon-only vs 0.21 coupon+bill. Steady-state private supply
  ~$500bn implies OIS/2y about -15bp vs -24bp then.
- **Univariate screen** (Citi, US Rates Weekly, 18 Jan 2019): since 2010, 1m/3m changes in the 2y/5y/10y futures vs swap and OIS on
  supply variables; only T-bill supply vs 2y futures/OIS was consistently significant (coefficient -0.013 to -0.036, t -1.7 to
  -3.6): ~$130bn bill paydown moves it +2 to +5bp, +$220bn of bills -3 to -8bp. Effect confined to the front end vs OIS.
- **SOMA WAM to private WAM to back-end spread**: private WAM regressions TY/OIS y = -2.5096x + 126.67 (R2 0.51), FV/OIS
  -1.3553x + 63.705 (0.29), TU/OIS -0.529x + 23.959 (0.09). Apply 25% of the historical beta (stock effects): an 8-month
  WAM differential gives TY/OIS -5bp, FV -2.5bp, TU -1bp, a spread-curve flattener.
- **Term funding premium** (J.P. Morgan, Buying back time, 19 Aug 2026): TFP = negative of the slope of a daily cross-sectional
  regression of maturity-matched swap spreads on modified duration (2/3/5/7/10/20/30Y), bp per year of duration. Fair value
  regression (Jun 2020-Jun 2026): excess deposits -0.6 (t -23.3), 1Yx10Y implied vol 0.3 (t 15.8), Treasury WAM 0.1 (t 6.6,
  value 70 months), net debt ex SOMA / Fed assets 0.5 (t 18.6, value 3.9), intercept -0.6, R2 83%, SE 0.3. Aug 2026: fair value
  4.2 vs actual 4.7 then 4.4; -0.3 would need WAM expectations ~3 months shorter, judged outsized; profit taken on 10s/30s
  spread-curve steepeners (+1.4bp). Exit spread-curve trades within one standard error of fair value.
- **Trade-level examples**: sell 2y Treasury vs OIS at -3.5bp, target +5bp, stop -8bp on forecast 2y coupon size $26bn to
  $35bn and record foreign-official custody (+$260bn YTD to $3.05tn) (BofA, Trade idea: sell 2y spreads, 27 Sep 2017); the move
  went to about 16bp cheap. Once supply was priced, buy 2y Treasury vs OIS at 18bp cheap, target 0, stop 25bp, catalyst early
  end of QT = less public supply (BofA, Trade idea: buy 2y Treasury vs OIS, 30 May 2018). TU/OIS tightener (sell TU vs OIS)
  50k DV01 entry -12.8bp target -24bp stop -7bp (Citi, 27 Mar 2020). Opened at -20 on 14 Dec 2018, closed at -16.2 on 17 Jan
  2019, +$210k, when bill issuance rose earlier than expected (Citi, 18 Jan 2019). Sign: Citi's TU/OIS is OIS minus UST (negative =
  Treasury cheap, so -20 to -16.2 is a richening, the gain on its long-Treasury "widener"); BofA's 2017 note quotes UST minus OIS
  ("negative = Treasury rich to OIS", the opposite); BofA's debt-limit exhibit uses OIS minus UST. Normalise before reusing any number.

## 8. QT and the Fed

- Rollover cap: maturing coupons redeemed up to the cap, excess reinvested as add-ons (mid-month vs end-month in proportion to
  maturities, then across tenors in proportion to offering size); bills roll unless coupon maturities fall below the cap, then
  bills fill the remainder. Worked example: $80bn maturing, $60bn cap: $20bn reinvested; 75% matures mid-month so $15bn
  mid-month; a 3y that is $50bn of $100bn offered mid-month gets $7.5bn; $5bn goes end-month. Bills: $40bn coupons + $30bn
  bills maturing with a $60bn cap: all coupons and $20bn of bills run off, $10bn of bills reinvested (BofA primer;
  `scripts/supply_arithmetic.py soma_addons`).
- Fed holds more than 15% of marketable USTs; more runoff means the public must hold more, which "will likely cheapen rates over
  time"; the add-on does not change gross auction size or strength.
- Runoff cap cut from $60bn to $25bn per month from June 2024 (J.P. Morgan, Cross currency basis 4Q24 Outlook, 26 Sep 2024).
  Regression (BofA, Fed QT Beyond Taper & Funding Impact, 22 Oct 2021, from Jun 2020): SOFR-IOER = -2.3505 x (reserves/GDP) +
  31.678 (R2 0.85); FF-IOER = 0.6455 x (marketable debt ex Fed / GDP) - 50.79 (R2 0.73); betas are regime dependent, use log
  reserves for nonlinearity.
- Post-QT "untwist" idea: the Fed buys bills ($20-25bn/month), replaces maturing coupons with bills and aims to match SOMA
  duration to the market over 5-20 years; it could crowd out bill supply (Conks, The Great Rebalancing, 16 Jul 2025).
  Restarting QT, selling MBS or shifting coupons to bills imply a steeper 5s30s (Citi, Global Economic Outlook & Strategy, 20 Aug
  2026). Treasury issuance mix decides how tight QT is: bills are absorbed with cash, notes and bonds add duration risk
  (Conks, The Stealth Liquidity Squeeze, 14 Aug 2023).

## 9. Buyer-base absorption

- Net coupon supply ex-Fed (including QT runoff) in 10y equivalents against each large buyer's projected absorption (Flow of
  Funds); the residual must be absorbed by price. 2025 example ($bn): foreign 400, pensions and insurers 150, banks 150,
  funds 200, households 350, large buyers 1,250 vs net new supply 1,610 and Fed runoff 75: residual 435; QT running
  longer adds $25bn per month (BofA, UST supply & demand in '25, 26 Nov 2024). Drivers: foreign private = duration view and FX-hedged
  pickup; foreign official = USD (custody holdings); DB pensions buy when funded status is high (a 10y rally of 50bp or more
  pushes funded status below 100% and cuts demand); banks = deposits and 3m5y slope; fund flows go via futures and are offset by
  leveraged-fund basis shorts (BofA, Basics of UST supply & demand, 24 Jun 2024).
- Official/private ownership 50/50 (2006, 2016) to 27/73 (2026): aggregate demand more valuation-sensitive, showing up in term
  premium (Financial Times Alphaville, 20 Aug 2026).
