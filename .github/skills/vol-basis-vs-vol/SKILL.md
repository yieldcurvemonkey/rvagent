---
name: vol-basis-vs-vol
description: 'Prices a government-bond futures basis as embedded volatility (switch/CTD, wildcard, end-of-month, timing options) and compares it with what listed futures options ("Board" options) and CTD-matched swaptions charge for the same vol. Covers option-adjusted basis (net basis minus delivery-option value), implied switch vol, basis vs swaption cost per gamma, Board/swaption vol ratio vs realised ratio, strike mapping via invoice spread, DV01-neutral conditional spreads (futures put vs payer, call vs receiver, costless strike, pick-up), replication of the embedded option with swaptions. Use when asked "is the net basis cheap vs vol", "buy the basis / sell options", "basis vs swaption", "Board vs swaption vol", "futures option vs swaption", "long basis as long gamma", "is delivery option value priced", TY/FV/US/WN/Bund/Buxl/OAT/BTP basis vs vol, OAB, wildcard vol, vol arb, implied switch vol, cost per gamma. CTD scenarios and delivery-option value itself: fut-ctd-switch-and-delivery-options.'
---

# Basis vs vol: the delivery option as embedded vol

The short in a physically delivered bond future owns options (which bond, which day, what time of day). The long basis
holder (long CTD cash, short futures in CF proportion) is long them, and pays for them through the net basis (BNOC).
The same yield vol drives listed futures options and OTC swaptions, so the net basis, a Board option and a swaption are
three prices for one vol. They usually agree; occasional gaps are the trade. This skill turns a basis into a vol
statement (option-adjusted basis, implied switch vol, cost per gamma), compares it with listed and OTC vol, and builds the
DV01-neutral package. Delivery-option valuation itself (CTD map, switch probabilities, wildcard model) lives in
[fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md); plain basis, carry and IRR in
[fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md); generic swaption RV in
[vol-rates-options-rv](../vol-rates-options-rv/SKILL.md).

## When to use
- "Is the CTD net basis cheap or rich once I price the options?" (OAB, TDOV, `NB - option value`).
- "Buy the basis and sell Board options (or the reverse)": vol arb between delivery options and listed options.
- "Is a Board put/call rich or cheap to the matching payer/receiver swaption?" (Board/swaption ratio, skew, pick-up).
- "What vol does this net basis imply, and is it sane vs swaption vol?" / "cheapest gamma: basis, swaption or Board?"
- Wildcard or switch option looks mispriced into a roll or delivery month and you want the vol-market cross-check.

## Inputs (data-agnostic)
Canonical tables are in [schemas](../data-contract-and-adapters/references/schemas.md); see
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). Missing input: ask the user or the data adapter, never invent.

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Contract terms, dates, notional coupon | `fut_static` | per contract | last trade, first notice, last delivery dates fix the option windows |
| Basket and conversion factors | `fut_basket` | per contract, point-in-time | prefer exchange CFs; a WI bond enters on issue date |
| Futures settles | `fut_quotes` | daily, one snap type only | settle vs close never mixed (wildcard is about the 3pm US close) |
| CTD / basket clean, accrued, yields | `bond_quotes`, `bond_static` | daily | forward prices need coupon schedule |
| Term repo to delivery, special repo of the CTD | `repo_rates` | daily | basis is financed with term repo matched to delivery (Burghardt et al., The Treasury Bond Basis, 2005) |
| Listed futures-option vols/premia | `opt_quotes`, `opt_static` | daily, strikes around ATM, 2 expiries | `nvol_bp` normal vol of the underlying yield |
| Swaption normal vols, strike offsets | `vol_surface` | daily, expiry x tail x strike offset | tail = CTD-duration-matched swap |
| Invoice spread (swap - govt yield at CTD) | `swap_spreads` (`measure=invoice`) | daily | sign convention travels with the row |
| History for z-scores / realised ratio | `fut_quotes`, `curve_par` | >= 3y daily (>= 1y minimum) | realised vol of futures and swap in yield terms |

## Conventions (state in every output)
- Net basis in 32nds of a point of the CTD bond price (US long end) or ticks of the contract; **1/32 on $1mm face = $312.50**.
  Gross basis `GB = P - F x CF`; carry = coupon income - financing to delivery; net basis `NB = GB - carry` (BNOC).
- Vol is **normal bp per year**. Futures-option price vol converts to yield vol by dividing by the futures DV01 in price/bp
  (a Board quoted in lognormal price vol needs this step before any comparison).
- Direction: describe an option by when the basis widens (rally or sell-off), not by "put/call on yields" - the sources mix price and yield wording.
- `T` for the switch option = years to the last trading day; EOM option runs last trade to last delivery day; wildcard is one-day vol after the close.
- Invoice / swap spread: US convention swap minus govt yield (negative = swaps below Treasuries). Sign is stored in `sign_convention`.

## Method

### 1. Map the basis to an option payoff
- Long basis = long (switch + EOM + timing + wildcard). Floor: worst case is full convergence, you earn the IRR; the loss on a long basis is
  capped at the net basis paid (Burghardt et al., 2005; CME Group, Understanding Treasury Futures, 2017). Short basis = short out-of-the-money options: earns
  decay up to BNOC, loss unlimited on a CTD change.
- **Direction rule.** Yields below the 6% notional coupon: the shortest-duration bond is CTD, a sell-off (and steepening) migrates CTD to longer duration, so the
  long CTD basis widens in sell-offs. Yields above 6%: longest-duration bond is CTD, long basis widens in rallies. Bases of the middle bonds are straddles/strangles. Near 6% many bonds are
  near-CTD (JPM, Near, far, wherever yields are, 2 Oct 2026). Exceptions to check: US sell-offs keep extending CTD duration, WN sell-offs anchor to the shortest bond and shorten it
  (Barclays, Divergent CTD switch behavior, 20 Aug 2026).
- **Payoff by construction**: at the end `F = min over the basket of (B/CF)`, so each bond's terminal basis is `B - CF x (CTD price / CTD CF)`; simulate yield shifts and twists to get payoff profiles and set fair net basis as the probability-weighted payoff. A long CTD basis then pays like a straddle: USU5 scenario, CTD 11/43 at +50bp moves to 11/44 (11/43 basis about 6 ticks from 7), at +100bp to 8/50 (11/53 basis worth 61 ticks), at -50bp or more to 2/41 (BofA, US Treasury futures primer, 10 Jul 2025; table in [references/basis-option-cases.md](references/basis-option-cases.md)).
- **Strike = crossover**: the yield (or spread) at which another bond becomes CTD. Drivers: time to delivery, vol, distance to crossover (CME, 2017). Value peaks where several candidates tie,
  is about zero when one bond is CTD across a wide range (JPM, The switch and the spur, 29 Oct 2026).
- Hedge ratio caveat: a CF hedge is exact only for the CTD; others need DV01 hedges; re-hedge after about 20-25bp (CME, 2017).

### 2. Option-adjusted basis (is NB cheap or rich in vol terms?)
1. Delivery option value `TDOV` = probability-weighted expected BNOC at expiry over a yield-level x slope grid (recipe and 7.41/32 example below), plus EOM and wildcard.
   Engine and wildcard model: [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md).
2. `OAB = NB - TDOV`. OAB > 0: basis rich, futures cheap, sell basis. OAB < 0: basis cheap, futures rich, buy basis. Market futures minus model futures `= -OAB / CF`.
   Option-adjusted IRR `= IRR + option value / dirty price x 360/n` compared with CTD term repo (JPM, Special delivery, 4 Dec 2019).
3. **Calibrate the vol inputs to listed vol, not to the basis**: level vol = futures-option implied vol at a strike near each switch yield (handles skew); spread vol = history of that spread
   (take pre-basket history and scale by the average pre-delivery increase); run >= 3 parameter sets (spread vol x0.5/1/2). The option is roughly linear in spread vol, so far from the notional coupon the answer is almost
   entirely that input; one-factor models understate DOV there (Huggins and Schaller, Fixed Income Relative Value Analysis, 2024).
4. Consistency checks: model expected forward equals market forward for every issue; price an ATM futures call off the model distribution and back out its vol vs the listed vol; adjust until they match. Works better for 10y and bond than 5y and 2y (Burghardt et al., 2005).
5. Only call OAB a signal if its sign survives all parameter sets and |OAB| > 1 tick (working default; half a tick is rounding and model noise).

### 3. Implied switch vol and cost per gamma (script `scripts/basis_vs_vol.py`)
- Describe the basis by legs `(slope px/bp, switch yield shift k bp, call|put)`, with slope the difference in converted-price duration between the bonds (price per bp of yield).
  Value of a leg: `slope x s x (phi(d) + d Phi(d))`, `s = sigma sqrt(T)`, `d = -k/s` (call-type) or `k/s` (put-type). Gamma `= slope x phi(d)/s`, analytic (never bump across the kink).
- **Implied switch vol** = sigma that makes model value equal market NB. Compare with the swaption normal vol for the CTD tail. Use only when the crossover is within about 1.5 sd (`|k| < 1.5 sigma sqrt(T)`) and NB >= 2 ticks (working defaults):
  a past inversion of long-bond net basis (own research, unpublished) gave 400-1000bp implied vols vs about 81bp swaption vol, with the median crossover 131bp away while median NB was 1.8/32, i.e. net basis was mostly financing, squeeze and flow, not switch optionality.
- **Cost per gamma** `= value / gamma` (bp^2). ATMF: `sigma^2 T` (annuity cancels). Like-for-like richness `= swaption cpg (same strike, swaption vol) / basis cpg`; > 1 means the basis is the cheaper gamma. Fair basis gives exactly 1.
  With like-for-like strikes and one vol the gamma cancels (`richness = model value / NB`), so it is the same test as OAB and implied switch vol, not an independent confirmation. The practical test is the pack's version: price the gamma in the instrument you would actually sell, an ATMF swaption (`atmf_cpg_richness`: `sigma^2 T / (NB / gamma_basis)`),
  which is biased towards "buy basis" for an OTM basis (an OTM option costs less per gamma), so read it with the like-for-like number beside it. Arms to test: (A) long basis alone, (B) long basis plus short gamma-matched swaption, (C) cheap NB alone. If C matches A and B the vol comparison adds nothing.
- Guards: minimum net basis (2 ticks default, as above), minimum gamma (distribution seen: median ~1e-7, p90 ~1e-3 in 32nds per bp^2, so drop dust), days-to-delivery window (exclude the last week where IRR is noisy).

### 4. Basis vs listed options (vol arb)
1. Compute OAB per deliverable. Entry for a buy-basis/sell-options trade: OAB <= -5 ticks in the 1990 sample, with the options market paying more for vol than the basis market. Scale the threshold with today's vol and tick size.
2. Hedge with listed options: search (optimiser or small grid) for the options whose P&L over a shift x slope scenario grid best matches the basis P&L; put-like bases are hedged mostly with short puts, call-like with short calls
   (Burghardt et al., 2005, Ch.7). True arbitrage is unattainable; profile mismatch is the main residual.
3. Residual risks: deliverable spread changes, carry/repo changes, profile mismatch, **option expiry about one month before futures last trading day (vega mismatch)**. Hold to option expiry.
4. Sell-basis side (OAB high) = short OTM options: a high hit rate is not proof of richness. Stress level and twist (selloff with steepening) before sizing.

### 5. Board vs CTD-matched swaption ([detail and history](references/board-vs-swaption.md))
1. Board vol = ATM interpolated, second available expiry (roll when the front expires). Swaption: expiry = option expiry, tail = duration-matched to the CTD, strike map `K_swaption = Board strike yield + invoice spread` (strike by strike, so skew is compared).
2. Ratio `R = Board nvol / swaption nvol`. Compare with the **realised ratio** (futures realised / swap realised, 1m and 3m, both in yield bp). Board rich if `R - R_realised > 0.05` (working band), cheap if `< -0.05`. Compare ratio with ratio, never with level.
3. Skew: Board puts tend to trade above payers and Board calls below receivers; US call skew cheap to receiver skew (2016-2017) and FV/TY put skew rich to payer skew (2018-2019) were the printed patterns; FV call skew was still rich to receiver skew in 2017, so check each contract.
4. Conditional spread (DV01-neutral): futures put vs payer, or futures call vs receiver. Swaption notional per 1000 contracts `= 1000 x face x fut DV01 / swap DV01` (TY 7.53/6.26 gives $120.3mn, FV 4.77/4.01 gives $119.0mn). Solve the swaption strike that makes it costless; report pick-up
   `= invoice spread - costless strike spread`, i.e. how far the costless swaption strike sits below the invoice-mapped strike. Reading (derived from the strikes, not stated by the source): positive pick-up for puts vs payers means the Board put is rich (sell put, buy payer at a better strike);
   positive for calls vs receivers means the Board call is cheap (buy call, sell receiver). This matches the vol ratios in the printed rows (put/payer above 1 with positive pick-up; call/receiver 0.87-0.90 with +2.3 to +5.7). The source's prose states the opposite subtraction order; its printed rows follow this one. Recompute from raw numbers and confirm with the vol ratio.
5. Drivers of Board cheapness: rallies tighten swap spreads, which raises swap realised vol relative to futures; mortgage prepayment demand for swaption gamma richens swaptions. Both temporary; Board-cheap episodes were short-lived. Pre-Lehman swap spreads widened in sell-offs
   (long payers vs short bond puts); post-Lehman the swaption premium over futures vol disappeared (Huggins and Schaller, 2024, Ch.19).

### 6. Cross-check by replication
Replicate the short future with a CF-sized cash short of the rally-CTD plus payer swaptions fitted to the residual payoff across instantaneous shocks (PC1 and PC2 shocks to +/-4 sd). Compare the replication cost with the net basis (example below).
The estimate may understate value because the switch payoff does not decay like swaption theta, and it diverges as the contract converges to one CTD (Morgan Stanley, Buy Higher Rates Protection at a 30% Discount, 27 Aug 2026).

### 7. Wildcard as one-day vol
- Mechanics: invoice price fixed at the 3pm ET futures close, notice later; deliver after a post-close rally, wait after a sell-off. Rule: exercise is attractive when `GB x CF < (cash now - cash at 3pm) x (1 - CF)` (BofA, US Treasury futures primer, 10 Jul 2025); threshold `x* = GB x CF / (1 - CF)` points of cash price (WN example: GB 5/32, CF 0.7342 gives 0.43pt; JPM's one-day form is `GB1/(1 - CF)` with GB1 one day of gross basis).
- Vol inputs: listed ATM futures-option vol read as one-day vol; post-close 1bp per 2 hours (1-1.5bp per day), doubled on FOMC days (JPM, Good things come to those who wait, 18 May 2018). Another source triples FOMC-day vol and its note quotes a 6 hour and a 15 hour window: state which you use.
- Size: ~0.75 tick TU and ~0.5 tick FV (May 2018, range 0.5-1); 0.5-1.5 ticks TN, sometimes FV/TY, and about 3 ticks of WN net basis (Dec 2019). Highest with low CF (low-coupon CTD), high vol, FOMC in the delivery month. A CF near 1 delivers early; CF < 0.9 tends to stay late even at negative basis.
- Reading of the rule: the wildcard is a roughly 3-hour call on `(1 - CF)` of the CTD, paid for with the gross basis on the `CF` part of the bond; exercising forfeits the remaining net basis (`GB = NB + carry`). Most valuable in FOMC delivery months (press conference at 2:30pm ET, before the 3pm settle) and for low-CF bonds (WNU5 CFs run 0.43 to 0.83) (BofA, US Treasury futures primer, 10 Jul 2025). Worked WN case: [references/basis-option-cases.md](references/basis-option-cases.md) section 5.
- Treat it as short-dated vega: compare with 1-day or overnight listed vol before accepting a model wildcard value as "the option the basis pays for".

### 8. Overlays that change the answer
- **Carry window**: positive carry means price to last delivery; negative carry to first delivery (FV to first, WN to last). Strongly negative carry shrinks the option window to the start of the month; flat carry keeps the whole month. Delivery is a T+2 process (intent, notice, settle), so compute carry to T+2 (BofA, US Treasury futures primer, 10 Jul 2025).
- **Funding**: use term repo to delivery and the CTD's own special repo. Overnight financing exposes the basis to slope: long basis loses if overnight rises. Basis traders shrug off repo spikes of about 15bp and tolerate at least 50bp, up to 200bp nearer delivery (Conks, The Basis Trade Scare, 17 Nov 2025).
- **Flows**: asset managers short the basis, levered funds long, similar size; basis cheapens when dealers cannot finance the levered side (BofA, US Treasury futures primer, 10 Jul 2025; CFTC Market Risk Advisory Committee, 2024). Negative net basis (options worth about 0, futures rich to the CTD forward) is attributed to asset-manager demand: they sell the basis to levered funds at 0 or below, capped by dealer repo balance sheet.
- **Squeeze**: negative CTD net basis is not free money when supply is short: price `P(fail) x gap`.
- **Hedge**: CF-weighted basis has a directional tilt, DV01-neutral basis stops tracking basis P&L. Choose, and near cusps use probability-weighted BPV/CF.

## Worked examples
1. **OAB (Burghardt et al., The Treasury Bond Basis, 4 Apr 2001, June bond).** CTD 7-5/8% 11/22: basis 18.1, carry 13.6, BNOC 4.5, TDOV 8.0, so `OAB = 4.5 - 8.0 = -3.5/32`; futures rich by `3.5/1.1936 = 2.93` ticks (fair 103-27 vs market 103-30): buy basis. Grid recipe (the book's separate hypothetical middling-duration issue, not the CTD above): level -100/0/+100bp and slope steeper/beta/flatter, each with probabilities 0.16/0.68/0.16, BNOC cells
   [20,2,20], [25,1,15], [30,3,10]: `0.16 x 7.76 + 0.68 x 7.08 + 0.16 x 8.44 = 7.41/32` fair BNOC for that issue.
2. **Vol-arb trades (same book, Ch.7, 1990).** Rule OAB <= -5 ticks, buy basis, sell CBOT options, hold to option expiry, before costs: OAB -6.6 -> +3.4 ticks; -6.0 -> +12.6; -5.7 -> +10.5; -6.1 -> -0.6; -12.9 -> +8.5; average OAB -7.5, average +6.9 ticks. Real proprietary trades Dec 1990-Jan 1992, net of costs (six trades, three shown: +7.8, +6.4, -0.5; average of all six +3.3 ticks per $1mm long basis): the gap between model and net-of-cost reality is the expected haircut.
3. **Basis vs swaption (Citi Research, US Rates Weekly, 17 Jul 2015, USZ5).** Long $100mm 5% May-37 vs short 911 USZ5 (spot DV01 of cash vs forward DV01 of futures), net basis 4.2 ticks = $130K, gamma $420 per bp^2 (as printed). The same gamma through a 1m25y swaption costs $187K, 1.4x the basis (the ATMF cost-per-gamma test). Matched expiry (5.5m25y ATMF receiver), +/-40bp parallel: risk/reward 1.3 swaption vs 1.56 basis (basis +135.9K at -40bp, -87.2K at +40bp). Conclusion in the note: the long basis is the cheaper rally option; forward yield falls of about 30bp bring the 4.5% Feb-36 back as CTD.
3b. **Cost per gamma (illustrative, not market data).** Basis with one call-type leg, slope 0.0125 px/bp (0.4/32 per bp), switch 30bp away, T = 0.25y, swaption vol 80bp: model value 2.10/32, gamma 9.4e-5 px/bp^2, basis cpg 664 bp^2 at NB 2.0/32, implied switch vol 78bp, richness 1.05 (fair). Same basis at NB 1.0/32: implied vol 60bp, richness ~2.1, the basis is half the price per gamma: buy basis, short gamma-matched swaption (arm B). Against an ATMF swaption (cpg `80^2 x 0.25 = 1600`) the 2.0/32 basis reads 2.4x, an artifact of strike mismatch (switch 30bp = 0.75 sd away) rather than cheapness.
4. **Board vs swaption (Citi Research, Rates Vol Lab, 2017).** TYH7 Board 87.4 vs swaption 81.8 (ratio 1.07), realised ratios 0.97 (1m) and 1.02 (3m): Board rich by 0.10 / 0.05 vs realised (1.0685 less 1.02 is just inside the 0.05 band, so only the 1m gap triggers). FVM7 69.3 vs 64.7 (1.07). USM7 0.93: read as Board cheap by the source (its realised ratio is not given here, so not a signal by this skill's rule). March 2020 (Citi, 30 Mar 2020): FVK0 0.86, USK0 0.89 vs 1.22-1.24 a week earlier, Board/3m realised 0.59-0.71: stress cheapening.
5. **Conditional spread (Citi, Rates Vol Lab, 12 Mar 2018; 12 Jun 2023; 5 Oct 2026).** FVK8 113.75 put (strike yield 2.74%) vs costless payer 2.85%: strike spread 10.8, invoice 11.6, pick-up +0.8, put vol 66.0 / payer 64.0 (1.03). TYX6 104.00 put vs costless payer -41.0, invoice -38.4: pick-up +2.6, vol 122.6/116.5 (1.05): Board rich, sell put / buy payer. TYM3 (12 Jun 2023): invoice -29.8 vs costless -24.6 gives -5.2, vol ratio 0.96: Board cheap.
6. **Replication (Morgan Stanley, 27 Aug 2026).** Short 1 USZ6 replicated by short $115,075 4.75% Nov-43 plus long payers struck ATMF+20bp ($17,502) and ATMF+30bp ($30,596), amounts as printed; value about 12.4 ticks vs Nov-43 net basis about 8.7 ticks: the convexity priced about 30% cheap in the basis. A ~50bp sell-off switches CTD from 5% May-45 to 1.375% Aug-50 and raises futures duration about 47%.
7. **EUR (JPM, Eurex CTDs wobble with higher yields, 2 Oct 2026).** Buxl Dec-26: CTD 71%, switch about 1/4 probable, option value about 25c vs net basis about 8c: net basis about 17c below option value (own arithmetic), the next bond needs 5.4bp of spread change vs a 3.2bp 1y sd. 10Y OAT: option about 10c, OA net basis about 0. Schatz/Bobl/Bund CTDs: option about 0.
8. **Front/back (JPM, Bond Futures Rollover Outlook, 12 Aug 2026).** US front NB ~2+/32 vs switch ~4+/32 (underpriced), back NB ~4+/32 vs ~15/32 (strongly underpriced: basis widening is bullish the calendar). WN front 2/32 vs option 1 (overpriced), back 1+/32 vs 3+/32 (underpriced).
9. **Option-adjusted signal in practice (BofA, Buy futures basis = cheap options, 10 Apr 2025).** Buy TYM5 CTD basis at gross -1 tick, net 0; target 1 tick of option payout, stop -4 ticks; model value 1.5 ticks (may overstate), market cost 0 to -0.25.

More dated cases, per-currency notes and 2026 levels: [references/basis-option-cases.md](references/basis-option-cases.md).

## Signals & interpretation
- **Buy basis / sell vol-equivalent**: OAB < -1 tick robust to spread-vol x0.5..2 (implied switch vol below swaption vol and like-for-like richness > 1.2 restate the same test under one model: count them once), plus an ATMF cost-per-gamma ratio above about 1.3 (the 2015 case was 1.4x). Board/swaption ratio below realised ratio less 0.05 means listed is cheap: buy Board, do not sell it.
  **Sell basis**: reverse, but only with a stress budget for selloff-with-steepening and a CTD change; short basis is short OTM options.
- **Board rich** (`R - R_realised > 0.05`; for puts vs payers also pick-up > 0): sell futures option / buy matched swaption; **Board cheap** the reverse (calls vs receivers: positive pick-up = call cheap). Single-ratio moves without the realised ratio are not a signal.
  Observed ratio range 2016-2026: mostly 0.90-1.10, 0.86-0.89 in stress, up to 1.22-1.24 one week before the March 2020 flip.
- **Confirm** the vol view is not a rates view: rally/sell-off drift moves spreads and the realised ratio; check mortgage gamma and swap-spread direction.
- **Net basis near 0 with flat carry** through the month is a near-free long position in switch and wildcard options: the cheapest basis in vol terms.
- **Which option dominates**: switch for CTD-neutral baskets near the notional coupon; wildcard in WN/low CF; EOM when the last trading day is about 7 business days before month-end (TY, TN, US, WN, TWE), so the window is long; far from the notional coupon (100+bp away) one bond is CTD across a wide range and the switch is worth about 0, unless a curve twist can still switch it (OAT did).
- **Z-score the OAB or the Board/swaption ratio** with 126d window as default, entry |z| 1.5-2, exit |z| < 0.5, max hold 10-42 days (working defaults; own unpublished backtest grids explored z window 63/126/252, entry 1.0-2.5, max hold 10/21/42 days); long-basis P&L = change in net basis, carry included.

## Pitfalls
- **Net basis is not all option.** Median NB can sit at 1-2 ticks while the crossover is 100+bp away: the rest is financing, squeeze premium and flow. Do not read it as vol.
- **Basis RV embeds a vol view**: a low CTD net basis is not free unless you believe vol is too low to switch the CTD (Tuckman and Serrat, Fixed Income Securities, 2022).
- **Black-style futures option pricing assumes away the delivery option** (futures vol changes with the CTD); it is still the market quote convention. Use normal vol for consistency with swaptions.
- **Day count conflict**: IRR uses 360 in one source, 365 in another. US Treasury repo and IRR are act/360 (the script default); gilt repo is act/365. State it.
- **Source inconsistencies to recompute, not copy**: pick-up sign (Board conditional tables); wildcard E formula and window (6h vs 15h) in the RiskVal guide; the `/Factor` in Burghardt's Exhibit 4.1 vs the prose; the yield-vol conversion printed without dividing by yield x duration.
- **Mismatched windows**: option expiry about one month before futures LTD; the Board second expiry is not the delivery window. Report the vega mismatch.
- **CTD-matched means matched at the option expiry**, not today (CTD and DV01 change), with strike mapped by invoice spread; ratios differ by strike.
- **Look-ahead and overlap in z-scores**: the rolling mean/sd of OAB or the ratio must end at t-1; net basis decays to zero into delivery and jumps at rolls, so z-score within a contract cycle or use the ratio; consecutive daily z-scores overlap, so count independent episodes, not days, in any hit-rate or t-stat.
- **Rank deliverables by OAB or IRR minus own term repo**, not raw BNOC: raw BNOC mis-ranks bonds with different price levels (Burghardt et al., 2005).
- **Hit rate is not richness**: Burghardt's 23-of-25 short-basis wins did not prove overpriced options.
- **Crowding and stress**: cash/futures correlation breaks, margin calls on small correlation changes, repo spikes (peak 174bp over SOFR in March 2020). Risk is mark-to-market and funding, not convergence (CFTC MRAC, 2024).
- **Backtest costs**: historical swaption bid/offer is not firm; swap bid/offer 2y/5y/10y was 0.3bp (2017-18), 0.4bp (2013-16), 1.2bp (2008-09) (Citi, 12 Mar 2018). Include both legs and the Board spread.
- **Hedge timing**: realised vol depends on the hour of the hedge; keep one snap per series.
- **Do not extrapolate DOV regressions**: DOV is non-monotonic in yield (peaks at the switch point, falls on both sides).
- **Futures are not a bullet bond**: futures track the worst-performing deliverable, so they shorten in rallies and lengthen in sell-offs, giving lower convexity than the CTD cash bond and possibly negative convexity; a delivery-option-adjusted DV01 or convexity hedge must use the probability-weighted CTD, not the current one (BofA, US Treasury futures primer, 10 Jul 2025).
- **Buying the net basis normally loses the premium**: buy at 1 tick and deliver optimally and you lose about 1 tick, more on a non-CTD, so a long basis needs the options to pay (a move through the crossover), not just convergence (BofA, US Treasury futures primer, 10 Jul 2025).

## Output
Return (1) a **basis table**: CTD, NB, TDOV split (switch/EOM/wildcard), OAB, futures rich/cheap in ticks `= -OAB/CF`, OA IRR vs term repo, parameter-set range; (2) a **vol table**: implied switch vol, swaption nvol (CTD tail, same expiry), Board nvol, ratios, realised ratio and gap, cost-per-gamma richness, z-scores; (3) **proposed package**: legs, DV01-neutral notionals, costless strike, pick-up, premium, vega/gamma/theta mismatch,
stress P&L (level +/-100bp, twist +/-1.5 sd, CTD switch), carry and financing assumptions; (4) the **verdict** with kill criteria (stop in ticks, vol regime break) and the hand-off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md). State conventions, snap and data dates.

## Scripts
- [`scripts/basis_vs_vol.py`](scripts/basis_vs_vol.py): normal-model basis leg value and gamma, implied switch vol, like-for-like cost-per-gamma richness, OAB and `-OAB/CF`, OA IRR, expected-BNOC grid, strike map, DV01-neutral notional, pick-up, realised ratio and Board signal; CLI subcommands `ratio` (from `opt_quotes` + `vol_surface` CSV), `cpg`, `conditional`, `oab`.
  `python scripts/basis_vs_vol.py --help`. `--selftest` checks closed forms against numeric integration and the printed examples above.

## Related skills
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): switch map, probabilities, wildcard model that feed TDOV.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): gross/net basis, IRR, carry, CF vs DV01 hedge, funding.
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): swaption and listed-vol RV, implied vs realised, normal-vol units.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): gamma vs vega P&L of the option legs, theta and gamma maintenance.
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): Board vs swaption skew, CTD option structures.
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): invoice spread used to map Board strikes to swaption strikes.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): costless-strike conditional structures.
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): front/back option value in the roll.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread directionality behind Board vs swaption.
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): mortgage gamma demand that richens swaptions vs Board.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): term and special repo for the basis.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): contract terms, day counts, notional coupons.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md) and [bt-backtest-design](../bt-backtest-design/SKILL.md): costs and point-in-time backtests.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score windows for OAB and ratios.
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): challenge before sizing a short-basis idea.
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): level, twist and CTD-switch stress for the package.

## References
- Citi Research - US Rates Weekly: Summer lull (Mathai, Gollapudi, Hollenhorst, Shah; 17 Jul 2015) and Trade worries linger (Mathai, Bikbov, Kang, Williams et al.; 17 May 2019): long basis vs swaption cost per gamma and scenario P&L; Board ratios and cheapening drivers.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): OAB/TDOV recipe, vol-arb trades and results, CTD stress tests, repo and squeeze notes.
- Huggins, Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): one-factor delivery-option model (Box 7.1), spread-vol inputs, JPY case, conditional swap-spread vs bond-option vol (Ch.19).
- Tuckman, Serrat - Fixed Income Securities (4th ed., Wiley, 2022): net basis as option, converted-forward approximation, futures-option pricing and its delivery-option blind spot.
- Duering - Fixed Income Trading and Risk Management (Wiley, 2021): option windows, basis payoffs, negative net basis and squeeze.
- Salomon Brothers - Understanding Treasury Bond Futures: Questions and Answers (Oct 1990): four delivery options, CF vs DV01 hedge, last-week option (historical conventions).
- CME Group - Understanding Treasury Futures (Johnson, Kerpel, Kronstein; Nov 2017): basis-as-option map, hedge-ratio cautions, contract mechanics.
- J.P. Morgan - Good things come to those who wait: the wildcard option (Salem, Younger, Zhao; 18 May 2018): wildcard model, vol parameters.
- J.P. Morgan - Special delivery: how delivery options distort rich/cheap for Treasury futures (Salem, Younger, St John; 4 Dec 2019): OA IRR, wildcard size, WN repo gap.
- J.P. Morgan - The switch and the spur (Ozil, Hayward, Alexeev, Alptuna; 29 Oct 2026): DOV drivers and sweet spot, USZ6/WNZ6 scenario table.
- J.P. Morgan - Eurex CTDs wobble with higher yields (Gupta, Mayfield; 2 Oct 2026): Buxl/OAT/BTP switch thresholds and option values.
- J.P. Morgan - U.S. Bond Futures Rollover Outlook (Ozil, Hayward, Alptuna; 12 Aug 2026): front/back NB vs switch option tables.
- J.P. Morgan - Near, far, wherever yields are (2 Oct 2026) and Born(e) in the US(A) (31 Jul 2026): DOV levels, factor-scaled BPV.
- Morgan Stanley - Buy Higher Rates Protection at a 30% Discount (Zhou, Carter, Hornbach, Tobias, Singh; 27 Aug 2026): swaption replication of the embedded option.
- Citi Research - Rates Vol Lab series (Bikbov, Williams; Chang, Williams, Appeddu; 2016-2026): Board vs CTD-matched swaption method, ratios, conditional spreads, bid/offer.
- BofA Global Research - US Rates Alpha: Buy futures basis = cheap options (Axel; 10 Apr 2025): trade idea.
- BofA Global Research - US Rates: Primer: US Treasury futures and basis (Ralph Axel, 10 July 2025): wildcard rule and example, delivery-date convention, futures convexity, basis payoff and CTD scenarios, negative net basis and positioning.
- Barclays Research - US Treasury Futures: Divergent CTD switch behavior in US and WN (Mok, Nashikkar; 20 Aug 2026): CTD by shift, local-curve drivers.
- RiskVal Financial Solutions / RVFI - Future CTD Scenario Analysis user guide (2023-2024): scenario engine, wildcard induction, EOM option.
- CFTC Market Risk Advisory Committee - The Treasury Cash-Futures Basis Trade (Dec 2024): stress, margin, crowding.
- J.P. Morgan - Impossible to walk in this muck (Younger, Salem, St John; 6 Mar 2020): WNM0 wildcard vs net basis in the March 2020 dislocation.
- Conks (Monetary Mechanics) - The Basis Trade Scare (17 Nov 2025): repo tolerance of basis traders.
