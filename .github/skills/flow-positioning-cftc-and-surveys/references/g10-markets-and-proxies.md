# G10 markets: positioning sources, drivers and proxies

Companion to [SKILL.md](../SKILL.md). Use this file for market-specific sources and gotchas. Conventions that apply
everywhere are in SKILL.md (point-in-time release, net = long - short, DV01 positive = long duration, z-score
with sample sd). Only sources that appear in the library are cited, by title, author and date.

## Summary table

| Market | Public investor-type futures data in library | Main real-money and structural drivers | Key gotchas |
|---|---|---|---|
| USD | Yes: CFTC TFF classes on TU, FV, TY, UXY, US, WN; SOFR/ED futures | AM/LF basis mirror; MBS, VA, bank and mREIT convexity hedging; pension funded status; TIC and fund flows | TFF classes cover 35% to 45% of 10y note OI (Düring, 2021); the AM/LF mirror is basis, not a view |
| EUR | No investor-type futures series; Eurex OI and clearing data | Dutch pension DC transition; insurer ALM under Solvency II reform; NGEU paying; year-end coverage receiving | Eurex principal clearing inflates OI; dealers normally net short futures vs inventory |
| GBP | No futures category series; gilt holder-base data | LDI and pension hedging (30y+ anomalies, pro-cyclical); insurer bulk annuity hedging with cross-currency swaps | LDI margin calls forced selling in Sep and Oct 2022; holder base is price-sensitive |
| JPY | Holdings by investor type (MoF data); JGB futures positioning from desk material | Lifers' target buying (20s30s); GPIF unhedged; FX-hedged pickup; Fed-cycle UST buying; fiscal-year-end selling (March) | TIC can miss private buying; hedged pickup is not a sufficient signal alone |
| CAD | None in library | Foreign flows: buy in October, sell in December; CGB basis trades smaller and more recent | Canadian TIC data show custodial swings |
| AUD | None in library | Japanese fiscal-year buying in May; AUD bank term funding and basis hedging | Pension FX-hedge-ratio changes are unverified |
| NZD | None in library | None in library | State the gap; use CCP-basis and vol-based proxies only |
| CHF | None in library (FX options-flow sample only) | SNB intervention visible in sight deposits | Options-flow sample is FX, not rates |
| SEK, NOK | None in library | None in library | 2020 options-flow sample too thin: excluded for low volume (BofA, Feb 2021) |

## USD

- **Data.** TFF categories are Dealer, Asset Manager, Leveraged Funds and Other Reportables; investor-category data start
  in 2006. Normalise positions by Treasury coupons outstanding excluding SOMA holdings. Notional matches funding
  quantities; DV01 captures the long end better (TBAC, Jan 2024). Identified classes cover 35% to 45% of 10y note OI
  (Düring, 2021). ED DV01 is fixed at 25 USD per bp per contract (Citi, The rocky road to a steeper curve, Jan 2019).
- **Structure.** AM net longs rose from about $100bn to over $700bn after November 2021; LF net shorts rose to almost
  $800bn. Normalised, this is similar to the 2019 peak, not larger (TBAC, Jan 2024). TU, FV and TY are 80% of AM net
  notional and 55% of TY-equivalent. The average annual cost of replicating a Treasury index with futures was 0.45% in
  2018 to 2023, which AMs pay to hold higher-yielding spread products (TBAC, Jan 2024).
- **Basis size.** Use the cash-futures reconstruction (CFTC OCE, Sep 2024), the Form PF upper bound (BIS, Dec 2025) and
  gross LF shorts (J.P. Morgan, Mar 2020) together. They disagree by design; report the range, not one number.
  Gross LF shorts peaked near $615bn in March 2020; a half-basis unwind of half of that was under 5% of government MMF
  assets (J.P. Morgan, Mar 2020).
- **Roll.** Asset-manager net longs as % of OI drive the roll pattern: high longs cheapen the roll early while holders sell the
  front and buy back, then converge to fair value in the last week, once most have rolled (Citi, Aug 2026).
- **Dealers.** US dealers are marginally net long futures on average, with inventory hedged in cash; possible
  misclassification means dealer classes need checking (Düring, 2021). Primary-dealer net positions (weekly, public)
  show the inventory side of the same trade.
- **Convexity and pension flows.** MBS and VA hedgers, Formosa-style callables, bank duration gaps and pension
  funded status move swap spreads (see the convexity and ALM skills). A top-100 DB-pension funded-status index was 103.5% in
  October 2024; a 10y rally of 50bp or more would push funded status below 100% (sensitivity; BofA, Nov 2024).
- **CME-LCH basis.** A back-end short gauge: basis widened from about 0 to 2bp in May 2015, and collapsed from October
  to December 2018 as the 10y rallied from 3.25% to about 2.7% on short covering (Citi, Jan 2019). Clearing costs differ by
  client and dealer, so the fair value is not zero.

## EUR

- **Data.** No investor-type futures series in the library. Eurex principal clearing lets one account be long and short,
  which inflates OI; US agency clearing nets (Düring, 2021). Use Eurex settlement data and the CCP basis instead.
- **CCP basis.** The local CCP minus LCH basis is positive when there are excess fixed payers at the local CCP. Eurex
  buy-side and insurers paying show up there. About 4bp is needed to make the basis arbitrage pay (SUERF/ECB, Jul 2024).
  The Eurex-LCH basis at 30y was read as "no receiving interest" when positive; 50y turned slightly negative
  (Nordea, Feb 2020).
- **Dutch pensions.** Defined-benefit to defined-contribution transition runs 2023 to 2027. Pensions received into
  year-end in prior years to protect coverage ratios (Nordea, Sep 2025). Transition paying flows are a long-end driver
  (BNP Paribas, May 2021). DNB quarterly coverage and hedge-ratio data show how much unwinding remains.
- **Solvency II reform (effective 30 Jan 2027).** Solvency ratio = own funds / SCR; technical provisions = best estimate
  + risk margin. Extrapolation: the first smoothing point replaces the last liquid point (20y for EUR). UFR 3.30%.
  The final alpha is 0.11 (ex SEK), phased in from 0.20 and declining linearly to 2032. Market rates begin to affect
  20 to 60y hedging needs, so receiving may move longer, but gradually. A lower risk margin sensitivity reduces the need
  to receive long-end swaps (Citi, Oct 2026). Govvies become more palatable than swaps from an ALM view: a swap-spread
  driver.
- **Investor base.** Euro investors buying hedged USD assets widen the FX basis; euro-area fund holdings of non-euro debt
  fell from above EUR 3trn (end-2021) to about EUR 2.7trn (June 2023) (BofA, Oct 2023). Non-resident share of French
  government bonds was 57% (Financial Times, Aug 2026).
- **Dealers.** EUR dealers are normally net short futures against inventory (Düring, 2021), so a dealer short is the
  default, not a signal.

## GBP

- **Data.** No futures category series in the library. Use holder-base data, swap-spread moves and the 5y-30y curve.
- **LDI and pensions.** Pension funds are a large share of the long end. Long-end anomalies in GBP swaps were "a function
  of regulatory fiat" and pro-cyclical: falling yields require more hedging, rising yields can spiral into reverse
  (Quantitative Finance Stack Exchange answers, Aug 2019; low confidence).
- **Insurer bulk annuity hedging.** Insurers sell long gilts and linkers, buy USD credit and hedge with long cross-currency
  swaps; this widens 30y SONIA and SOFR and flattens 10s30s (J.P. Morgan, Sep 2024).
- **Holder base.** UK insurers and pension funds held about GBP 277bn of non-UK long-term bonds in Q2 2023, down on LDI
  collateral calls (BofA, Oct 2023). Domestic LDI and insurer buyers of long gilts are retreating; the investor base is
  more price-sensitive (Financial Times, Aug 2026).
- **Forced selling.** Truss-era LDI margin calls forced selling in September and October 2022; the Bank of England bought
  up to GBP 65bn between 28 September and 14 October (Willer and Saunders, 2026). Treat hidden leverage as an amplifier:
  crowded holders become fire sales and basis widens.
- **Sentiment.** Exposure-minus-view survey positioning (BofA, Sep 2024). GBP rates were the most received in G10 before
  the March 2026 shock (JWS, low confidence).

## JPY

- **Data.** Holdings by investor type from the Ministry of Finance (pensions, banks, lifers); TIC can miss private
  buying because MoF data show stable holdings while TIC shows selling (BofA, Apr 2024 and Mar 2025 reports). Japanese
  UST demand follows the Fed cycle and expected capital gains, not hedged carry, except at extremes (Willer and
  Saunders, 2026).
- **Lifers and GPIF.** Lifers buy super-long bonds in January to March (ALM duration gap, fiscal year-end) while banks
  sell (BofA, Jun 2022). Lifers were about 50% hedged and falling; GPIF is largely unhedged and above $1tn (J.P. Morgan,
  Sep 2024 and Jun 2025; Citi, Aug 2026). Lifers' target buying caps the 20s30s yield. Japanese investors' pension funds
  treat hedged foreign bonds as domestic (BofA, Oct 2023).
- **Fiscal year-end.** Japan sold about $10bn of USTs in March 2019 at fiscal year-end (Citi, May 2019).
- **Super-long JGB futures.** Foreign longs vs proprietary shorts; lifers buy around current bonds but duration demand is
  limited; overseas investors are less interested, so resilience to heavy selling is low (Citi, Aug 2026).
- **Intervention.** USD-selling intervention by the MoF in the 2022 and 2024 episodes coincided with cheaper USTs and
  tighter front-end and intermediate swap spreads (BofA FX intervention primer, Jul 2024); see the worked-examples file.
- **CCP basis.** JSCC banks were receivers before 2018 (SUERF/ECB, Jul 2024). Policy-bet spikes at LCH revert.

## CAD, AUD, NZD, CHF, SEK, NOK

- **CAD.** Foreign flows: buy in October, sell in December; largest average buying in May (BofA, Jun 2022). CGB basis
  trades exist but are smaller and more recent (BIS, Dec 2025). Swings in Canadian TIC data are custodial.
- **AUD.** Japanese investors were net buyers of AUD government bonds in six of the last eight Mays (BofA, Jun 2022). AUD
  banks issue about USD 100bn of term funding a year and pay the 6m-1y and 3y-5y basis to hedge (BofA, Oct 2023).
  Pension FX-hedge-ratio increases would widen the front-end basis; treat this as unverified.
- **NZD.** No positioning-specific material in the library. Say so; do not fill the gap with other markets.
- **CHF.** SNB intervention can be proxied by sight deposits (BofA, Jul 2024). The 2020 options-flow sentiment was FX, not
  rates.
- **SEK, NOK.** No CFTC-style series. The 2020 options-flow sample excluded them for low volume (BofA, Feb 2021).

## Proxies when a market has no public positioning series

| Proxy | Works in | What it tells you | Limit |
|---|---|---|---|
| CA minus model (ED/SOFR-style) | USD and any market with listed STIR futures and caps | Short base covering or building | Needs the model vol fit; sign is a filter |
| CCP basis between two CCPs | USD, EUR, JPY | Excess payers or receivers at one CCP | Clearing costs and policy bets contaminate it |
| Auction screen (tail, takedown, bid-to-cover) | All government curves with auction data | Demand at the margin | Small sample; contrarian in one test |
| Holder data by investor type | USD (TIC), JPY (MoF), GBP and EUR (holder surveys) | Structural holders and their direction | Monthly, custody-distorted, long lag |
| Options put/call notional | Any market with listed options or OTC trade repository data | Hedging demand and skew | Partial coverage; one-year samples common |
| Funded status | Any DB-pension market | Duration demand direction | Index-based; slow; depends on credit spreads |

## Market conventions that change the reading

- CCP basis orientation: confirm before reading a sign. The library default is LCH minus local CCP; some notes quote the
  reverse.
- Swap spread sign: US convention is swap minus Treasury; EGB asset-swap convention is bond spread over swaps. A "narrowing"
  US swap spread means more negative.
- DV01 sign: positive = long duration (long futures, receive fixed). A short-futures position is a short duration position
  in the TFF data.

## References used here
- Düring, A. - Fixed Income Trading and Risk Management (Wiley, 2021).
- TBAC - Discussion of Treasury Futures Positions Across Different Investor Types (30 Jan 2024).
- CFTC OCE - Observations on the Treasury Cash-Futures Basis Trade (Mixon, Orlov, 23 Sep 2024).
- BIS Quarterly Review - Goodbye Libor, hello basis traders (Dec 2025).
- J.P. Morgan - When market risk meets operational risk (10 Mar 2020).
- Citi Research - Treasury Futures Roll Sep26-Dec26 (18 Aug 2026); Shorts increasing? (16 Jan 2019); The rocky road to a steeper curve (18 Jan 2019); Trade worries linger (17 May 2019).
- BofA - US Rates Watch, Long UST outflows and dealer holding highs (10 Mar 2025); FX intervention primer (8 Jul 2024); FX-Sofr primer (31 Oct 2023); Securities seasonality primer (6 Jun 2022); sentiment survey (5 Sep 2024).
- SUERF Policy Brief No 940, Back to the basi(c)s (Jul 2024); Nordea Markets, EUR Rates Flash (5 Feb 2020); Nordea Markets, EUR rates: How about that outright receiving (26 Sep 2025).
- Citi Research, What to do about OATs? (1 Oct 2026); Citi Research, Japan Rates Weekly (Aug 2026).
- J.P. Morgan, Cross currency basis 4Q24 Outlook (26 Sep 2024) and 2H25 Outlook (5 Jun 2025).
- Willer, D. and Saunders, A. - Trading Global Macro Markets (Wiley, 2026).
- BNP Paribas, EUR curve convexity: lessons from history (25 May 2021).
- Financial Times, Who owns government bonds? (Aug 2026).
- Quantitative Finance Stack Exchange, "Why does the ultra long-end of a yield curve invert?" (Aug 2019; low confidence, used only for the qualitative point).
- JWS Macro (Substack), #3: Iran and Front End Rates (8 Mar 2026; low confidence, used only for the qualitative GBP positioning point).
