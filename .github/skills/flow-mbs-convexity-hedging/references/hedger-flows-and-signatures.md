# Convexity-hedger flows: taxonomy, sizing and market signatures

Companion to [SKILL.md](../SKILL.md). Sizes are as printed by each source at its date; they are not
current. Refresh any figure from the data adapter before using it as an input.

## 1. Who is short convexity, and how they hedge

| Participant | Convexity sign | Hedge behaviour | Source |
|---|---|---|---|
| Agency MBS holders (banks, money managers, GSEs, REITs) | negative (prepayment option sold) | Buy duration in rallies, sell or pay fixed in sell-offs, if they hedge | BofA primer 18 Mar 2021; Tuckman & Serrat 2022, Ch.15 |
| Originator pipeline (rate locks) | negative (borrower option) | Short UST or pay-fixed swaps (ratio ≈ OAD) plus payer swaptions for convexity and straddles for vol | Tuckman & Serrat 2022, Ch.15 |
| Servicers (MSR) | MSR has negative duration and negative convexity; can trade positive convexity in some regimes | Receive fixed or buy UST; buying TBAs adds negative convexity, so buy swaptions to flatten it | Tuckman & Serrat 2022, Ch.15; JPM, Markets struggle to feed the convexity beast, 28 Feb 2020 |
| Banks (asset side) | agency MBS, portfolio mortgages, MSR are short convexity | Receive swaps to add duration; deposits (long) offset | JPM, Is bank convexity hedging lying in wait?, 31 May 2019; JPM, Will mortgages bail banks out, 27 Mar 2020 |
| mREITs | negative, retained for dividend income | Receive swaps; P/B below about 100% makes equity raising unlikely | JPM, Markets struggle..., 28 Feb 2020 |
| GSE retained portfolios | negative | Historically paid fixed; shrinkage removed that payer demand | TBAC, Charge: Swap Spreads, Feb 2021 |
| Variable-annuity (VA) hedgers (insurers) | short long-end gamma (liabilities extend in rallies, so they are left short and must buy duration) | VA duration contracted $23bn in one week (Feb 2020) | JPM, Markets struggle..., 28 Feb 2020; JPM, For cheap gamma, look to the long end, 23 Aug 2019 |
| Callable issuers (Formosa and Korean lifers, >15y original maturity, post-2011) | positive (issuer call sold) | Modelled as callable swaps at par; offset MBS negative convexity | JPM, Dynamic hedgers are long, banks are short, 13 Sep 2019 |
| Bermudan callable issuers (5nc3m) | positive | Pay or receive per call probability; offset MBS | Citi, Time for moderation, 17 Feb 2023 |
| Danish-style callable mortgage bonds (EUR) | short calls to borrowers | Negative duration to about 140bp spread; vol mainly 5y and 10y expiries | During 2021, Ch.25-28; Nordea, 5 Nov 2021 |
| Dutch pension funds under UFR rules (EUR) | short convexity by regulation | Must buy duration as yields fall | During 2021, Ch.20-31 |

Key facts for sizing:
- Active hedger share fell from about 50% (early 2000s) to about 15%. Money managers 20% to 10%; GSEs about 25%
  (2005) to under 2% (Q3 2020, FHFA $250bn cap); REITs 7% (2013 peak) to under 3%. Non-hedgers (banks about 35%,
  Fed about 30%) hold over 65%; the Fed holds the most negatively convex bonds (BofA primer, 18 Mar 2021).
- Sizes (JPM, A comprehensive look at convexity hedging, 29 Mar 2019): banks about 30% of agency MBS (about $2tn),
  assume about 20% of their negative convexity is actively managed; GSEs about $850bn pre-crisis, now under
  $200bn; REITs about $280bn agency MBS plus TBAs.
- Non-banks (about 60% of the market) hedge infrequently because higher origination fees offset MSR losses
  (BofA primer 18 Mar 2021).

## 2. Trigger behaviour

- Hedgers act mainly on net moves above about 20bp, path-dependent relative to their last rebalance, and "tend
  not to be involved until rates have re-priced materially" (JPM, Dynamic hedgers..., 13 Sep 2019).
- Peak MBS negative convexity is reached only in a 70-100bp rally; exposure could rise about 30% if rates fall
  70bp or more (JPM, A comprehensive look..., 29 Mar 2019).
- Asymmetry: duration buying in a 50bp rally far exceeds duration shedding in a 50bp sell-off, because the
  universe moves out of the money (Barclays, The urgency question, 2 Oct 2026). Barclays puts convexity flows at
  roughly $40-50bn 10y-eq per 25bp rise for hedging investors (Barclays, Swap spreads: The Bright Spot in US rates,
  30 Sep 2026), and says negative convexity has already fallen a lot.
- Fast rallies can outrun hedgers; servicer positive convexity can offset GSE receiving, so spreads may not
  narrow at first (JPM, Markets struggle..., 28 Feb 2020).
- Self-limiting: convexity sell-offs in MBS and CTD extension self-limit once rates move enough; fiscal convexity
  does not (Barclays, The urgency question, 2 Oct 2026).

## 3. Flow balance sheet (JPM, What about bonds? SLR relief..., 2 Apr 2020, 10y-eq, Apr to year-end 2020)

- Buyers about $1,100-1,300bn: Fed about $400bn securities; banks $300-500bn and financial issuers about $250bn
  via derivatives; levered mortgage hedgers about $50bn; insurers about $50bn.
- Sellers about $2,000bn: Treasury about $1,600bn; banks, foreign central banks and pensions about $100bn each;
  non-financial rate locks about $30bn.
- Buyers use swaps and sellers use securities, which biases swap spreads narrower.
- Mar 2020 bank gap: up to about $1.5tn 10y-eq short delivered, roughly equal from deposits extending and
  mortgages contracting; with the swap curve pinned at 0%, only about $230bn of duration was added through
  year-end (JPM, Dynamic hedgers..., 13 Sep 2019; JPM, Will mortgages bail banks out..., 27 Mar 2020).

## 4. Bank model details (JPM, Dynamic hedgers..., 13 Sep 2019; JPM, Is bank convexity..., 31 May 2019)

- Bank hedge model: banks on the JPM Agency MBS index composition, 20% of dynamic duration hedged with swaps.
  GSE retained portfolio on 2009 composition with paydowns reinvested into current coupon. MSR = 30bp IO strip
  off the index, weighted by top-4 bank share.
- Bank balance sheet: deposits are long duration; institutional deposits migrate to money funds when rates rise.
  Inputs: retail deposit beta 0.45, wholesale 0.65, both changing 0.15 per 100bp; banks above $250bn assets;
  book equity 9.5% of assets. Result: bank equity duration about 5 years short at 1Q19; a further 100bp rally adds
  6-7 years.
- Bank gap: $800bn 10s unhedged by late Aug 2019 (flat-book), with at most $150-200bn hedged, so more than $400bn
  short. Constraints: LCR, internal liquidity stress, G-SIB score. Banks replace lost duration by receiving swaps,
  described as "accounting-friendly and scalable" (JPM, The return of convexity hedging, 31 Jan 2020).
- Household-side hedging (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, §4.1): banks
  pay fixed on interbank IRS to hedge fixed-rate mortgages (often customised amortising swaps) and receive fixed to
  hedge current-account balances (marginal rate = central-bank deposit rate − current-account rate, using an
  actuarial model of deposit life). Pension and annuity providers may receive long-dated fixed to hedge falling rates.

## 5. Market signatures (what the flow shows up in)

### 5a. Swap spreads
- Directionality beta: rolling 3-month beta of daily or weekly swap-spread changes on yield changes (bp/bp), for 2y,
  10y, 30y and invoice spreads (front contract rolled at first notice). Compare with the 10y median and the 5th and
  95th percentiles. Sign convention: spread = swap yield minus Treasury yield. Positive beta = the spread rises
  with yields, which is what swap-paying hedgers in sell-offs and swap-receiving hedgers in rallies produce. Beta
  through 2019 about 0.10-0.15, strongest out the curve (JPM, Is bank convexity..., 31 May 2019; JPM, Dynamic
  hedgers..., 13 Sep 2019). Sources print the sign both ways, so state the convention before comparing.
- Active-hedging test: whether 10y spreads trade directionally with rates. Counter-directional moves in Jan 2020
  meant hedgers were not yet active (JPM, The return of convexity hedging, 31 Jan 2020).
- Spreads move meaningfully only after large outright moves (JPM, Markets struggle..., 28 Feb 2020, Exh 1: 1M swap
  spread change bucketed by 1M yield change, 2015-17 vs 2018-20).
- Post-2008 drivers of a negative 30y matched-maturity swap spread (UST minus swap): clearing removed credit risk
  from Libor swaps; more UST supply; fewer GSE payers; pension and insurance receiving with no natural long-end
  payer; reserves; regulatory frictions (BofA, UST RV primer, 2 May 2022).
- Natural payers vs receivers (Stathakopoulos, The Interaction Between Repo and Interest Rate Swaps, 27 Sep 2021;
  During 2021, Ch.29): payers are spread-product dealers, rate-lock and forward-starter hedgers, asset swappers,
  long-asset gap managers and RV funds; receivers are new-issue swappers, convexity hedgers (receive in rallies)
  and long-liability gap managers.
- Regression (TBAC, Charge: Swap Spreads, Feb 2021): 30y LIBOR spread on Treasury debt, 5s30s steepness, S&P 500
  (VA proxy) and MBS duration gave R² 61%. Since YE-2019, 30y spreads ran 16bp wider than predicted. Residuals
  in 2015 and 2020 coincide with Basel III and the SLR exemption, so add regime dummies.
- Warning on fits: in one Citi study the 2y swap-spread R² was 0.61 for a coupon-only model and 0.21 with a
  bill term added, so specification matters (Citi, All it takes is a little push, 4 Oct 2019).
- Specific swap-spread points: MMSS is most sensitive at 10y and 30y (BofA, UST RV primer, 2 May 2022).

### 5b. Volatility
- Homeowners are the net vol buyer: a 30y fixed MBS is "effectively an Agency thirty-year non-call one twelfth".
  Rule of thumb: each $100mm of new MBS equals homeowners buying vega of $50mm 3y x 10y straddles (Bassman, The
  Largest Volatility Sale Ever, 23 Mar 2010).
- Issuance signal (the author calls it "a clever contrivance"): 12-month moving average of (net 30y fixed MBS
  issuance minus net 3/1 and 5/1 ARM production) against 3y x 10y implied normal vol lagged one year. Ignores 15y
  MBS and longer ARMs (Bassman, 23 Mar 2010).
- Fed QE as a vol sale: the Fed does not delta-hedge, so $1.25tn of purchases equals $625bn of 3y x 10y straddles
  sold; count Fed purchases as un-recycled prepayments (Bassman, 23 Mar 2010).
- Implied/realised: 3y10y implied normal vol over 6m realised has a long-run average of 107%, the "risk-adjusted
  fair value" for short convexity. It diverged after FASB 156 (2005), when servicer hedge buying richened belly
  vol (Merrill Lynch, RateLab: Professional Javelin Catching, 16 Feb 2007).
- Vol-surface inversion from flows: a 10y swap 10y forward about 2bp below spot despite a +169bp 2s10s; 1y10y
  straddle at 141 Nvol vs 10y10y at 83 Nvol, from receive-30s inversion hedging and servicer short-expiry gamma
  demand against trust-preferred long-expiry supply (Merrill Lynch, RateLab: The Positive Carry Hedge, 31 Oct 2008).
- Belly vega: PCA-weighted MBS vega centres on 2y-into-10y. In the 2013 taper move, MBS hedgers bought belly vega
  and long-expiry tail vol fell (Bassman, Forwards are NOT a Prediction, 12 Aug 2013).
- Vega PCA (Citi, US Rates Vol Lab: Gamma and Vega RV, 14 Jan 2019): 3y2y rich at 5.7 normals and 3y10y cheap at
  1.9 normals (z −2.2), attributed to less MBS convexity-hedger vega demand than before the crisis. The source text
  and table disagree on the 3y2y z-score (3.6 vs 2.6); use the table.
- Low vol means more negative convexity (more gamma). "Low volatility is usually found loitering near the scene of
  the crime because its associated negative Convexity acts as an accelerant" (Bassman, It's Never Different This
  Time, 29 Jan 2018).
- MBS floaters with fixed caps (Citi, Fading vega dislocations, 5 Oct 2026): $496bn outstanding, 72% ($358bn)
  capped at 6-7%. As forwards approach caps, holders become long duration and short vega; max short vega $204mm,
  equal to $217bn notional of 3y10y straddles. Intermediate-vol bid is the risk.

### 5c. Curve and long end
- Long-dated forward steepeners (10y10y vs 20y5y) carry net negative convexity; forward flatteners carry net
  positive convexity. Forward curve and implied vol therefore move inversely. Divergence (curve bear-flattened
  while vol collapsed) was flagged as an entry signal (Citi, Forward steepener and vol divergence, 12 Jun 2023).
- Breakeven/realised ratio (same Citi note): back out a daily yield breakeven (bp) from carry and negative convexity,
  divide by 1y realised daily vol. Ratio above 1 means carry pays more than realised moves cost. The exact formula
  is not given in the source; document any version used.
- Convexity bias in a duration-neutral 2-5-10 fly: bullet yield normally above the wings, so the fly is short
  convexity and the pickup compensates. Jan 2009-Jun 2010 test: net yield about 0.45-0.5 at a convexity cost of
  about 20, rising to 0.7-0.75 at 35-40. Convexity premium c(t) ~ sigma x sqrt(t) (During 2021, Ch.20).
- Convexity bias inverts the very long end beyond 25-30y in most models; this is a model shortcoming, "not a real
  trading opportunity" (During 2021, Ch.20).
- Long-end demand (JPM, For cheap gamma, look to the long end, 23 Aug 2019): VA hedgers are delivered net short in rallies
  (liabilities extend, especially if equities fall) and servicers add back duration, so both buy at the long end; more than $60mn/bp of long-end demand since late July, mostly Libor swaps, so
  20s outperformed.
- Conditional steepener (JPM, The return of convexity hedging, 31 Jan 2020): rolling 3-month beta of weekly 10Y vs
  2Y swap-rate moves, estimated separately on selloffs, rallies and all moves; compare premium-neutral bear
  steepeners (ATMF zero-premium, 25-delta, strike-shifted ATMF 2Y). Rationale: negative convexity helps
  bear-steepen in selloffs, so a selloff beta above 1 gives positive expected value.
- Long-dated straddles as the callable-vega proxy: 5y20y straddles proxy callable vega. Nordea (5 Nov 2021): the
  CM5Y callable beat the government index in Jul 2012-Dec 2014 and Jul 2015-Jul 2019, when the 5y20y straddle
  underperformed; over 17 years the straddle trend was up, so negative convexity does not pay without high OAS.

### 5d. Sizing the flow in a scenario (BofA primer, Exhibit 7; 10y-eq $bn per 25bp move)
- Jun 2003: pipeline 53, MSR 28, REIT 1, money managers 87; total 169, which was 10.1% of a $1,669bn Treasury
  market.
- May 2013: 23, 25, 18, 39; total 105, 1.7% of $6,266bn.
- Feb 2021: 37, 6, 7, 13; total 63, 0.5% of $11,529bn.
- Reading: flow share fell from about 10% to 0.5% of the Treasury market, so Feb 2021 was mostly pipeline hedging,
  not convexity hedging.

## 6. Currency notes (G10)

- USD: agency MBS (FN, FH, GN; UMBS TBAs since June 2019), GSE and Fed portfolios, mREITs, servicers, bank deposit
  betas, 5nc3m Bermudans and long-dated Formosa and Korean-lifer callables as offsets. Fed: QT MBS cap $35bn/month
  (rarely reached); after QT, MBS paydowns were reinvested into Treasuries, which moves negative convexity back to
  the public (BofA, Primer: Fed policy plumbing '25, 8 Jul 2025; check current Fed policy before relying on it).
  LCR: reserves and UST at 100%,
  GSE debt and agency MBS (L2a) at 85%, L2 at most 40% of HQLA (Barclays, US short interest rate primer, 2 Jan 2025).
- EUR: Danish callable mortgage bonds (30y callables; vol mainly at 5y and 10y expiries; balance principle; logistic
  prepayment; negative duration to about 140bp spread; Flexlan variable-rate loans; low EUR mortgage take-up). Dutch
  pension UFR (a 2012 rate of 4.2%, later revised to 3.9%) imposes short convexity on pension managers. Cross-currency
  vol: Bassman (The Largest Volatility Sale Ever, 23 Mar 2010) attributes richer USD than EUR vol to MBS hedging and
  reports that selling USD vs EUR vol has historically lost; the source's ratio figures are not reproduced here.
- GBP: UK mortgage hedging (pay fixed) picks up as mortgage rates fall. BoE 2y and 5y fixed mortgage rates (75% LTV)
  peaked May 2024; net mortgage borrowing rose £2.8bn in July 2024, the highest since Nov 2022; bank receiving
  faded after 1H24 deposit churn. Expression cited: pay the 5y belly of a 3s5s7s fly (BofA, UK Rates Viewpoint:
  Back to school, 5 Sep 2024).
- JPY: lifers hedge UST and MBS with FX forwards; banks fund UST and MBS in repo; GPIF does not FX hedge. Lifers'
  hedge ratio falls as hedging cost rises. If USD keeps weakening they may hedge more, widening the front end. Life
  insurer yield floors predictably bear-flatten or bull-steepen the 20s30s JGB sector (JPM, Cross currency basis
  2H25 Outlook, 5 Jun 2025; JPM, 4Q24 Outlook, 26 Sep 2024; During 2021, Ch.31).
- AUD and NZD: banks issue about USD 100bn/yr of term funding (3-5y to match about 5y mortgage duration); pay the
  6m-1y basis for money-market issuance and the 3y-5y basis for term funding. APRA HQLA rules leave few offshore
  assets to hedge (BofA, FX-SOFR primer, 31 Oct 2023).
- CAD, SEK, NOK, CHF: the source corpus for this skill has no MBS-specific data. Canadian mortgage arrears (3+
  months, highest since 2016) are macro context only (Citi, Canada Economics Weekly, 13 Aug 2026). SEK mortgage
  bond futures are listed (Nasdaq mortgage bond futures product sheet, Apr 2024), but no SEK pool data was
  reviewed. Do not transfer the USD numbers to these markets; ask the adapter for local pool, TBA and swap-spread data.
