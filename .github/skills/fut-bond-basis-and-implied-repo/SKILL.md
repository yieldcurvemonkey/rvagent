---
name: fut-bond-basis-and-implied-repo
description: 'Cash-futures basis for physically delivered government bond futures (UST 2y/5y/10y/Ultra/Bond, Bund/Bobl/Schatz/Buxl, OAT, BTP, long gilt, JGB, CAD 10y, CONF). Conversion factors, invoice price, gross basis, carry, net basis (BNOC), implied repo rate (IRR) vs term repo, CTD by max IRR, CF vs DV01 hedge ratios, tailing, basis-trade funding, leverage and balance-sheet limits, and synthetic asset replacement with futures. Use when asked if a bond future is rich or cheap to cash, "implied repo vs GC", "net basis in ticks", "buy or sell the basis", "cash and carry", "CTD", "conversion factor", "basis trade unwind or crowding", "wildcard breakeven", "basis payoff by scenario", "how many futures hedge this bond", "replace bonds with futures" or "synthetic duration". Option valuation is in fut-ctd-switch-and-delivery-options. Invoice spreads and futures ASW: fut-invoice-spreads.'
---

# Bond futures basis and implied repo

A bond future is a forward on a basket of deliverables, sold with options (which bond, which day). With the cash CTD
(cheapest-to-deliver) priced forward by bond plus term repo, the future should trade at `forward / CF - option value`. The basis is the
gap between cash and that conversion-factor-scaled future. The implied repo rate (IRR) is the same gap expressed as a financing rate: if
IRR is above the repo you can lock, cash-and-carry earns the difference. The skill computes gross basis, carry, net basis and IRR for
every deliverable, picks the CTD, separates "rich/cheap" from "just option value", sizes hedges that lock the basis, and prices the
funding and balance-sheet limits that stop arbitrageurs closing it. Futures are the cheap, balance-sheet-light way to hold duration, so
the same maths drives synthetic asset replacement.

## When to use
- "Is the 10y future rich or cheap to the CTD?", "what is the IRR versus 1m/3m GC?", "net basis on the Dec Bond future".
- Build or monitor a long/short basis (CF-weighted bond versus futures), size it, roll it, fund it and stress it.
- Find which deliverable is CTD and how far the next one is (hand off to [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md) for switch/wildcard value).
- Decide whether to hold duration in cash bonds or in futures plus cash (synthetic replacement), or whether basis demand is crowding the futures.
- Read a sell-side "implied repo", "net basis", "IRP", "BNOC" or "OABNOC" line and check its conventions.
- Not for: futures-versus-swap invoice spreads ([fut-invoice-spreads](../fut-invoice-spreads/SKILL.md)), calendar rolls ([fut-calendar-roll](../fut-calendar-roll/SKILL.md)),
  cash-settled STIR futures ([stir-futures-rv](../stir-futures-rv/SKILL.md)), cash-settled AUD bond futures (no CTD, no IRR).

## Inputs (data-agnostic)
Canonical tables in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md); schemas in
[schemas](../data-contract-and-adapters/references/schemas.md). Ask the user or the data adapter if anything is missing. Never invent a repo rate.

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Futures price at one snap | `fut_quotes` (`price_px`, snap `settle` or `close`, never mixed) | daily; intraday for execution | decimal, never 32nds text |
| Contract terms: notional coupon, first/last delivery date, last trade date, contract size | `fut_static` | per contract month | physical contracts only |
| Deliverable basket with exchange conversion factor and eligibility dates | `fut_basket` (`conversion_factor`, `eligible_from/to`) | per contract month | when-issued bonds enter on issue date; prefer the exchange CF |
| Bond terms: coupon, maturity, frequency, day count, original term, `settle_days` | `bond_static` | static, point-in-time | day count drives accrued |
| Bond clean price and accrued, same snap as the future | `bond_quotes` (`clean_px`, `accrued_px`, `settle_date`) | daily | mid; flag `is_wi` |
| Term repo to the delivery date, GC and bond-specific | `repo_rates` (`term` = ISO delivery date, `collateral`, `specialness_bp`) | daily | the bond's OWN repo for the CTD test |
| Overnight RFR history and term OIS/swap curve (funding proxy and hedge) | `rate_fixings`, `curve_par` | daily | only if no term repo; label it a proxy |
| Futures-option implied vol (to calibrate option value) | `opt_quotes` (`nvol_bp`) | daily | feeds the option-adjusted view |
| Positioning / open interest for crowding | `positioning`, `fut_quotes.oi_cnt` | weekly / daily | see [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md) |

Minimum for a basis sheet: futures price, deliverable clean prices and conversion factors, a term repo to delivery and the delivery date.
Without a term repo the output is labelled "overnight proxy" and the IRR-versus-repo verdict is withheld.

## Method

### 0. Conventions (state them in every output)
- Price per 100, decimal. Basis in 32nds ("ticks") for USD bond contracts, cents for Eurex, sen for JGB. `ticks = decimal x 32`.
- `gross_basis = P_clean - CF x F`. `net_basis = P_fwd_clean - CF x F`. `carry = gross_basis - net_basis`. Positive carry means coupon accrual exceeds repo cost.
- IRR and repo in percent per annum, simple, ACT/360 for USD/EUR/CHF/SEK-style repo, ACT/365 for GBP/JPY/CAD/AUD/NZD-style (NOK: check [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md)). Print the day basis; a source quoting IRR on 365 (BofA, Primer, 10 Jul 2025) is not comparable to a 360 one.
- Delivery date (first / mid / last) and bond settlement date are inputs, not defaults to hide. IRR to the first and last delivery day can differ by about 25bp or more near a near-zero basis (27bp in worked example 3).
- "Long basis" = long bond, short `CF x face / contract size` futures. "Short basis" = short bond (reverse repo), long futures. Long basis is long the short's delivery options.
- Receive-fixed/long-duration is positive DV01. A long basis is roughly duration-neutral by construction, with a small CF-tilt (below).

### 1. Conversion factor and invoice
- CBOT CF = price per 1 of par at yield = notional coupon (6%; 8% before Mar 2000) for the term from the first day of the delivery month, with term rounded down to the quarter (10y, Bond, Ultra) or month (2y, 3y, 5y).
  `scripts/basis.py: cbot_cf` implements it and ties to 7 published factors; the full recipe, scalloping, and Eurex/gilt/JGB differences are in
  [markets and conversion factors](references/markets-and-conversion-factors.md). Use the exchange-published CF from `fut_basket`; recompute only to validate.
- Invoice per 100 face = `F x CF + accrued(delivery)`. Per contract = `F x CF x contract_size/100` (USD 1,000 per point for 100k face, 2,000 for the 2y) plus accrued; the `F x CF` part is the principal invoice.
- Futures-implied bond yield: reprice the CTD at price `F x CF` for settlement on the delivery date. Never treat the future as a bond with the notional coupon (the Ultra-Bond example: a 172.2 "price" at 2.65% gave -0.09% yield instead of the CTD-based answer).
- A future is not a notional bond: it is a weighted hybrid of deliverables. Futures DV01 = CTD forward DV01 / CF; for a basket use probability-weighted `DV01_i / CF_i` and sort the basket by `DV01/CF` rather than maturity to see which way the CTD can move.

### 2. Financing, delivery date and carry
1. Term repo from bond settlement to the delivery date, matched to that date. Use the bond's own term repo where `repo_rates` has it, else GC with a flag. If only overnight is available, either build a synthetic term (overnight funding plus pay-fixed OIS to delivery: cost about OIS fixed plus the average GC-minus-policy-rate gap, which is negative when GC trades below; residuals are realised GC gap, specials and compounding) or label it a proxy. A 10bp change in term repo moves the net basis by about 0.4/32 in the front and 1.0/32 in the back-month Ultra-Bond contract (JPM, Rollover Outlook, 12 Aug 2026), so overnight funding misprices the carry.
2. Delivery date: price to the last delivery day when carry is positive (coupon above repo) and to the first when negative (a bond whose coupon is below financing). In the July 2025 USD screen the 5y contract priced to the first delivery day (negative carry) and the Ultra-Bond to the last (BofA, Primer, 10 Jul 2025). Check the CTD at both ends and use T+2 (intent, notice, delivery) when pricing early delivery. Around quarter/year-end turns the first/mid/last choice changes implied and term repo materially: do not default to "last".
3. Forward clean price with coupons reinvested at repo:
   `Fwd_full = (P + AI0)(1 + r d/360) - sum_k c_k (1 + r n2_k/360)`; `Fwd_clean = Fwd_full - AI_T`. `d` = calendar days from settlement to delivery,
   `n2_k` = days from coupon `k` to delivery. With no coupon this collapses to `Fwd_full = (P + AI0)(1 + r d/360)`.
   Burghardt and Tuckman instead roll the repo in two legs (grow to the coupon date, deduct the coupon, grow again): this adds
   `P r^2 d1 d2/360^2`, about 0.1 tick at 4.5% repo and 84 days. Use one method for both IRR and net basis, else `IRR = repo` at zero net basis fails by that amount.
4. `carry = P - Fwd_clean = (AI_T - AI0) + coupons - financing` (price points). `1 tick` of carry on USD 1mm = USD 312.5.
5. Daily drop in gross basis equals daily carry (futures treated as driftless): `GB_t - GB_{t+1} = carry per day`, with Friday-to-Monday three days. Net-basis P&L is the clean part: a forward-bond-versus-future position slides nothing.

### 3. Implied repo rate
- `IRR = [ (F x CF + AI_T) + sum c_k - (P + AI0) ] / [ (P + AI0) d/360 - sum c_k n2_k/360 ]`. With no intervening coupon: `IRR = ((F CF + AI_T)/(P + AI0) - 1) x 360/d`.
- Exact identity (no coupon): `IRR = repo - net_basis/(P + AI0) x 360/d`. Rule of thumb at a dirty price near 100: `repo_wedge_bp ~ 1125 x net_basis_ticks / d`. One tick is 18.8bp at 60 days, 37.5bp at 30 days, 112bp at 10 days. IRR becomes unreadable into delivery: a few ticks annualise into 50-100bp.
- IRR is the cash-and-carry return: it assumes the bond is CTD with certainty, full convergence, CF-weighted futures, and ignores the futures-forward gap and margin interest. Daily variation margin cancels (`F_T` drops out), so only `F_0 x CF` matters.
- **CTD = highest IRR** (equivalently lowest net basis when prices are similar). When any deliverable trades special use `IRR - own term repo` (the "algebraically largest" gap): this matters in the euro area where CTDs trade special and for recently auctioned US issues. Lowest net basis ignores price level and can rank differently (Burghardt, 2005). Never pick the CTD by lowest price, highest yield or lowest gross basis. Inside the delivery month use the minimum converted cash price.
- Duration/yield rules to sanity-check the pick: below the notional yield the lowest-duration bond tends to be CTD, above it the highest-duration; at equal duration the highest yield; steeper basket pushes the CTD longer, inverted shorter.
- Why the future is shorter-duration in rallies: if every deliverable yielded the notional 6%, all would be CTD together. In a parallel rally the shortest-duration bond becomes CTD and in a sell-off the longest, so the future tracks the worst performer, shortens as yields fall and lengthens as they rise. It has lower convexity than cash and can be negatively convex (BofA, Primer, 10 Jul 2025). So a CF-weighted package drifts away from delta-neutral once the CTD changes. Contract terms (tick size, last trade and delivery dates, FV eligibility) are tabulated in [markets and conversion factors](references/markets-and-conversion-factors.md) section 2.

### 4. Rich/cheap, and the option adjustment
| Observation (CTD certain) | Reading | Action if it survives the option adjustment |
|---|---|---|
| IRR above term repo (net basis < 0) | future rich to cash | long basis: buy CTD, repo to delivery, sell CF x face futures; locks `IRR - repo` |
| IRR below term repo (net basis > 0) | future cheap, or just option premium | short basis / synthetic: sell bond, invest cash, buy futures; only if net basis exceeds option value |
- Net basis is the market price of the short's options (which bond, which day, the wildcard after the 3pm close, end-of-month). Fair `F = Fwd_CTD / CF - DO`; fair CTD net basis = `DO x CF`, zero at delivery and non-negative in theory. Since the short picks the bond, `F <= min_i (Fwd_i / CF_i)`.
- Options make futures look cheap: positive net basis, IRR below repo, even with the future fairly priced. Compare with an option value, not with zero:
  `edge = DOV_model - net_basis` (ticks), with DOV in net-basis units (price per 100 face of the bond = futures-price option value x CF; divide the edge by CF for futures points: Burghardt's -3.5 ticks of option-adjusted basis at CF 1.1936 is a future 2.93 ticks rich). Positive edge = basis cheap, buy; negative = rich, sell. Equivalent in rate space: option-adjusted IRR `= IRR + DOV/dirty x 360/d` versus CTD term repo (JPM, Special delivery, 4 Dec 2019). The value itself comes from [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md) or a scenario grid (parallel shifts +/-150bp x basket steepening +/-10bp); see worked examples E.
- Defaults for the edge threshold (house judgement, not from a source): act when `|edge| >= max(1 tick, 2 x basis bid-offer)` for TU/FV/TY/UXY and `>= 2 ticks` for the Bond and Ultra-Bond, where model error is larger. Model error is larger when vol input is high: delivery-option value is close to linear in spread vol, so run two vol sets and require the sign to hold in both.
- Typical levels, USD (Aug 2026 data): TU/TY/UXY BNOC about -0.1 to 0.4 ticks, WN 1.6-2.0, US 2.3-4.4; carry to delivery TU 1.6, FV -0.3, TY 2.3, UXY 2.2, US 5.5, WN 3.8 ticks (JPM, Rollover Outlook, 12 Aug 2026). A wildcard of about 3 ticks in WN and 0.5-1.5 elsewhere is normal and pushes IRR 10-30bp below repo with no mispricing. A WN wildcard can exceed 10 ticks if post-close vol persists. For scale in July 2025: net basis was often near 0 across the USD contracts while the wildcard alone could be worth 4-5 ticks on some; with rates near 6% (notional coupon) nets were often 10+ ticks (BofA, Primer, 10 Jul 2025).
- Net basis can be negative: that is IRR above repo (futures rich to the converted forward, options worth about zero, so the holder is paid to own the delivery options if the bond can be carried to delivery) and it is traded in size, with balance sheet as the binding limit (not arbitrage-free). Before the delivery month negative basis is possible. Inside the delivery month it cannot persist for any deliverable. A negative CTD net basis "is not free money" when deliverable supply is short: price `P(fail) x gap` (fail charges can create a negative basis).
- **Wildcard exercise test** (timing option): the invoice is fixed at the 3pm ET futures settle but the short can still declare delivery later in the evening while cash trades on, so it is a short-dated call on `(1 - CF)` of the CTD paid for with the gross basis on `CF`. Deliver early only if `gross_basis x CF < (cash price now - cash price at the 3pm close) x (1 - CF)`, both sides per 100 face of the bond; exercising forfeits the remaining net basis (gross = net + carry). Breakeven post-close move `= gross_basis x CF / (1 - CF)`: 5 ticks of gross basis at CF 0.7342 needs a rally of about 0.43 points (13.8/32) after the close (derived from the rule; example J). The option is valuable in FOMC delivery months (the 2:30pm press conference runs into the 3pm settle) and for low-CF bonds, where `1 - CF` is large (BofA, Primer, 10 Jul 2025).
- **Scenario-grid fair value and payoff**: at the end `F = min_i (B_i / CF_i)`, so each bond's terminal basis is `B_i - CF_i x (B_CTD / CF_CTD)`. Shift yields (parallel and twists) over a grid, find the CTD and each bond's basis in every cell, and take the probability-weighted value as the fair net basis; the same grid gives the futures PV01 (`sum_i P(CTD_i) x forward PV01_i`, with `P(CTD_i)` the share of grid weight where bond i is CTD). The payoff of a long CTD basis is a straddle: it gains when the CTD changes in either direction and loses the premium when yields stay put (example K). Cross-check with a replicating futures option: if the basis is cheaper than the option, buy the basis and sell the option (BofA, Primer, 10 Jul 2025; hand-off to [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md)).
- Regression screen: scatter IRR versus estimated term GC, fit a line; points above the line are rich futures versus cash (long basis candidates). Contaminated by quarter-end premia in term GC.

### 5. Package construction and hedge ratios
- **CF-weighted** (default for a CTD basis): contracts = `face x CF / contract_size`. USD 10mm of a CF 0.8072 bond is 80.72 contracts. P&L tracks the net basis exactly whatever the rate direction, but carries a small bullish/bearish tilt for non-CTD bonds.
- **Tail**: reduce contracts by `1/(1 + r d/360)` (daily margin earns interest): USD 1bn at CF 0.8006, 116 days, 1.10%: 7,978 contracts, not 8,006.
- **DV01-weighted** (curve-aware, for a non-CTD bond or a real hedge): contracts = `bond_DV01 / (CTD_fwd_DV01_per_contract / CF_CTD)`. Equals CF weighting only for the CTD. For the 2.375% May-2027 example this is 108 contracts versus 75 by its own CF. Re-evaluate after 20-25bp of yield change. Non-CF weights are a CF basis plus a futures overlay, so a non-CTD bond versus futures is mostly a curve trade versus the CTD (BofA, Primer, 10 Jul 2025).
- **Switch risk in the hedge**: the RoT futures DV01 jumps at a CTD crossover and the futures are negatively convex near it. If candidates are bunched use the probability-weighted `BPV/CF` (JPM, Switch and spur, 29 Oct 2026) or an option-adjusted DV01 from central differences of the model futures price.
- **After the last trading day** the futures price is frozen and cash still moves. A CF-weighted hedge leaves `(1 - CF) x face` unhedged. Face-match: USD 1bn long basis, short 8,338 at 0.8338, futures frozen at 133.87, i.e. CTD-equivalent 111.62: sell 1,662 more for 10,000 total (a 1-point CTD fall otherwise loses USD 1.66mm on 166mm unhedged) (Tuckman and Serrat, 4th ed., 2022). Before notification 1bp P&L is the CTD's converted DV01 x notional; after notification it is the delivered bond's actual DV01 x amount, a jump that grows with the distance of CF from 1 (Düring, 2021).
- **Repo stub risk**: term repo and spot yield are nearly independent week to week (weekly R2 under 3%). Repo DV01 of the forward is about `(P + AI) d/360 / 10,000` price per bp (about USD 2.9 per 100k face per bp for 84 days): roughly the same for 5y/10y/Bond contracts and about 2x for the 2y; stub risk is 2% of spot DV01 (Bond), 3.8% (10y), 13% (2y). Overnight funding leaves a roughly 3m-duration stub: hedge with STIR futures/OIS or term the repo.
- Execution: legged, or via an EFP quoted on the basis with the futures leg set near market and cash as the residual (`P = basis + CF x F`). Packages quoted DV01-neutral get tighter bid-offer than outright bonds.

### 6. Funding, margin and balance sheet
- Economics: a long basis profits if financing plus the carry cost of initial and variation margin is lower than the basis, i.e. `IRR - term repo > margin carry cost` (CFTC MRAC, Dec 2024). Return on capital: `(net_basis_ticks/32 /100) x notional / capital`. Example: USD 1bn at -4 ticks earns USD 1.25mm to convergence; at 20:1 leverage that is 2.5% over 141 days, about 6.5% annualised; at 40:1 about 13% (Tuckman and Serrat, 2022).
- Haircut is leverage: zero haircut on USD 200mm needs no cash, 2% needs USD 4mm. Most basis financing is bilateral/uncleared or sponsored; cross-margining and the clearing mandate change the economics but do not remove margin double-counting. Size for haircut changes the counterparty can make unilaterally.
- Leverage-ratio hurdle: capital is about 3% of exposure (6% for US G-SIBs), so USD 100mm needs USD 3mm (6mm). At a 10% return on capital this requires at least 7.5 cents (15 cents) of net basis per 3 months whether buying or selling (Quantitative Finance Stack Exchange, Funding Treasury net basis trades, 2019). Balance-sheet-constrained dealers shrink at reporting dates, so contracts spanning year-end trade cheap.
- Liquidity buffer, not the arbitrage, is the binding risk: size so that a daily net-basis move of at least 10 ticks plus a 25% margin step is fundable. In the Mar-2020 case the net basis went from -8.3 to -18.5 in one day, needing about USD 4mm per 8,000 contracts of cash while the position later made +USD 2.5mm.
- Repo tolerance (practitioner): 15bp spikes do not faze basis traders; they tolerate at least 50bp, up to 200bp nearer delivery. Dangerous window: just after the quarterly rolls. Repo-minus-SOFR 99th percentile was 10-11bp in Feb 2020 and peaked at 174bp on 16-Mar-2020. Quarter-end repo turns scale with base tightness: price them from the ex-month-end spread, not a fixed historical premium.
- Term repo versus overnight: overnight is cheaper on a positive curve and easy to unwind but long basis loses if overnight repo rises, short basis if it falls. "Term" repo that runs past delivery means the bond is on repo when it has to be delivered: fail to the exchange. Plan to fail in cash rather than in futures.
- Short basis needs reverse repo, which is typically 10-25bp below GC for plentiful collateral, and CTDs trade special (specialness = GC minus bond repo; heavily short or about-to-be-delivered issues). Special rates have no floor (a CTD traded at -15% overnight in May 2005) and in the US the fails charge (3% minus the bottom of the target range, floored at zero) caps specialness only when policy rates are below 3%: at rates above 3% it is zero and caps nothing (BofA, US Treasury repo primer, 7 Jul 2025). Specialness is horizon-specific (100bp o/n, 10bp 1m).

### 7. Synthetic asset replacement with futures
- Recipe: sell the cash bond, invest proceeds short (term repo, bills, or floating-rate paper to keep credit quality), buy futures. Contracts = cash DV01 / futures option-adjusted DV01; tail by `0.9895`-style factor (spot DV01 / forward DV01) when P&L is paid immediately.
- Pickup per year on the cash proceeds is approximately the rate expression of the net basis: `term repo - IRR` for the CTD (the premium for being short the delivery options). Sign: positive when the future is cheap to forward. Static yield of futures + bills = `(CTD yield - implied repo) x leverage + bill yield`; recompute at each quarterly roll because special repo resets.
- Evidence: 48 quarters of long 10y futures plus overnight cash returned 4.85%/yr versus 4.71% in the CTD (+14bp); replacing the 10y CTD three months before expiry averaged 62bp annualised over 25 contracts (2 losers) (CME, 2017; Burghardt et al., 2005). A high IRR means futures are rich: sell futures against cash to augment returns, after the option adjustment.
- Why use futures: lower bid-offer (UST off-the-run 4.7 cents versus futures 1.6 cents per 100; JGB 16 versus 1 cents, 2003), built-in financing, no custody or FX on foreign contracts, and a '40 Act or insurer capital advantage (futures are not repo leverage or an RBC charge). Futures replication of a Treasury index cost about 0.45%/yr over overnight SOFR in 2018-23.
- Portfolio duration: `MD_aug = [MD_raw x MV_raw + MD_fut x PEV_fut] / MV_raw`; `PEV = N x 1,000 x F` (2,000 for the 2y). Futures add duration but no market value. Target: `N = (target MD - MD) x MV / (futures MD x PEV per contract)`.
- Keep the short-options exposure explicit: the replaced position gives up optionality and gains it back only through the CTD behaving. Check that the CTD basket has real switch risk before treating the net basis as free money.

### 8. Monitoring and series hygiene
- Store the verdict in the row: `data_ok`, `dq_reason`, delivery date used, repo source (own/GC/proxy), day basis. A flag that only exists in a log is a flag nobody reads. Validate prices on the tick grid; return NaN rather than decode.
- IRR time series: make futures and bond prices contemporaneous (same snap). Spikes come from stale legs or from comparing overnight SOFR to a term IRR and are not executable. Roll the front contract about 5 days before the delivery month (first day of delivery month in the US; last trade date in EUR/GBP/JPY conventions) and never treat a roll as a return.
- The cash-futures spread has a cost-of-carry `c` that drifts as delivery nears and jumps at the roll. Use a threshold error-correction view: no adjustment is expected inside the marginal trader's transaction-cost band, so require `|IRR - repo|` (option adjusted) to exceed that band, not zero, before calling it mispriced (Hasbrouck, Empirical Market Microstructure, 2004).
- Crowding dashboard (levels, not signals): futures open interest as a share of the Treasury market, leveraged-fund short futures versus asset-manager long futures (mirrored almost one-for-one; the aggregate is not a pure tenor-matched basis, scale cash estimates by 0.6-0.7), cleared repo size, basis versus open interest (cash richening versus futures while OI grows = crowding), dealer inventories, overnight versus term repo spread. Futures positioning overstates cash basis positions (CFTC OCE, Sep 2024; TBAC, 30 Jan 2024).
- IRR as a funding barometer: front 10y IRR versus 1m GC, 3m bank paper, and FX-forward-implied USD yields. An IRR collapsing below GC means leveraged basis is being unwound (futures richen, Treasuries cheapen versus OIS); the trade turned unprofitable with IRR below repo in early Mar-2020.

## Worked examples
All numbers are published; the first two are asserted in `scripts/basis.py --selftest`. More cases in [worked examples](references/worked-examples.md), including a wildcard exercise (J) and a basket screen with a scenario CTD map (K) from BofA, Primer, 10 Jul 2025.

1. **Carry and IRR, no coupon in the window** (Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005): 7-1/4% 15-Aug-2022, clean 119.875, accrued 1.0014, repo 4.54%, 84 days to delivery, F 103.9375, CF 1.1481. Accrued at delivery 2.683702, invoice 122.014346, coupon income 1.68232, financing 1.280484, carry 0.401836 = 12.9 ticks, IRR = (122.014346/120.8764 - 1) x 360/84 = 4.03%.
2. **Net basis from a forward** (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022): Sep-2021 10y future at 131-17+, CTD 2.875% May-2028, CF 0.8338, clean 110.77344, repo 0.015%, 136 days. Forward clean 109.71721 gives gross basis 1.0896 (34.9 ticks), net 0.0334 (1.1 ticks), carry 33.8 ticks. IRR from the market future is -0.065%, 8bp below the 0.015% repo: futures cheap by exactly the 1.1 tick net basis (1125 x 1.1 / 136 x 100/110.8 = 8bp). Had the future traded at forward / CF the IRR would equal the repo. Same-day contrast: the 2.875% Aug-2028 net basis is 24.8 ticks, the Feb-2031 is 274 ticks. A basket with that spread has one CTD; "selling the Aug-2028 basis" is a switch bet.
3. **Conventions change the IRR** (CME, Understanding Treasury Futures, Nov 2017; Quantitative Finance Stack Exchange, Jul 2022): Dec-2017 10y future 125.265625, CTD 2.375% Aug-2024 CF 0.8072 invoice USD 101,114.41. The principal invoice (ex accrued) is USD 101,114.41. The published IRR is 1.42%; re-derivations with different day counts or delivery dates give 1.52% to 1.79%. Never compare two IRRs without the same settle date, delivery date and day basis.
4. **Option premium looks like cheapness** (JPM, Special delivery, 4 Dec 2019): IRR minus term repo was distorted by 10-30bp in the 10y/Ultra-10y/Bond contracts; Ultra-Bond implied repo dropped 50-100bp below CTD term repo into the delivery month on a few ticks of net basis. Compare option-adjusted values only.
5. **Long basis with leverage** (Tuckman and Serrat, 2022, Mar-2020): 7,978 tailed contracts at net basis -8.33; next day -18.48 (-USD 3.17mm plus margin), then +USD 2.46mm cumulative as the basis converged by 12-Mar. The trade needed about USD 4mm of cash in one day.
6. **Modern cross-section** (JPM, Rollover Outlook, 12 Aug 2026; JPM data pack, 28 Oct 2026): USD 100mn 4.625% Nov-2044 versus 851 Bond futures, gross basis 16/32, term repo 3.87% to 31-Dec-2026, net about 2/32, marked +2.1/32 later. On 2 Oct 2026 a net basis near 15/32 in the Dec-2026 Bond future was judged not attractive while funding could tighten into late October.

## Signals & interpretation
- Long basis (buy the cash, sell futures) when option-adjusted net basis is cheap: `edge = DOV - NB >= threshold`, funding term-locked to delivery, CTD probability concentrated, and the carry on the leg is zero or positive. A near-zero IRR-minus-repo on a high-coupon, low-vol CTD (net basis at or below 0 with carry through the month roughly flat) is the cheapest optionality: BofA's April 2025 example bought a CF-weighted 10y package at gross -1 / net 0 ticks, targeted a 1 tick option payout with a stop at -4 ticks.
- Short basis only with a positive edge `NB - DOV`, reverse-repo available for the bond's tenor, and a stop: losses are open-ended if the CTD changes through yield or spread levels. Net P&L of a short CTD basis held to expiry equals `-(change in BNOC)`. The most obviously attractive short has the greatest squeeze risk (1986: a basis widened about 6 points as the spread to neighbours went from 25-40bp to over 100bp).
- A high-duration basis behaves like a call on the bond (gains if yields fall or the curve flattens), a low-duration basis like a put, a mid-duration basis like a straddle (Burghardt, 2005). Worst case for a long CTD basis: yields barely move and the curve flattens; the option decays at roughly the carry deficit.
- IRR above repo that also persists in the option-adjusted view and in the regression versus term GC: futures rich, possibly structurally (asset-manager long demand). Before 2020 futures were often rich to CTDs because constrained institutions prefer off-balance-sheet futures (Tuckman and Serrat, 2022), and TU/FV traded rich on structural asset-manager longs (Citi, Fixing the plumbing, 30 Sep 2019): the basis did not reach fair value before delivery, so treat convergence as a carry-and-roll trade into delivery, not a one-off arbitrage.
- Cash-only CTD relative value: a bond richens as it becomes CTD and cheapens as it falls out of the basket. Bonds years away from CTD status are usually bought against matched-maturity swaps to capture that (BofA, Primer, 10 Jul 2025); check the result against [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md).
- Who is on which side: asset managers are generally short the basis (long futures instead of cash, favoured when the curve is inverted) and levered funds long it, in similar size. They sell the basis to levered funds at zero or negative net basis, limited by dealer repo funding, which is one source of structural futures richness. Asset managers carry basis risk for their whole holding period even though they roll before delivery (BofA, Primer, 10 Jul 2025).
- Terminal payoff is near-arbitrage (a few ticks) but mark-to-market volatility is not low: size to stress, not to the terminal payoff.
- Rate sell-off: net basis narrows for bonds moving toward CTD and widens for those displaced. The basis is partly a directional CTD view: check which bond is CTD in `+/-50bp` and `+/-100bp` scenarios (the Bond future's CTD moved to the 11/44 at +50bp, 8/50 at +100bp in one 2025 example) before treating it as delta-neutral.
- Escape routes: close or roll before the first delivery day (as early as 2 business days before the month for some contracts). Only about 2.8% of Treasury futures go to physical delivery, so a dynamic-convergence plan is the norm; more than 90% of June deliveries in the 10y/Ultra-10y/Bond/Ultra-Bond contracts came in the last week (Citi, Roll, 18 Aug 2026).

## Pitfalls
- Wrong CF or CF month: always use the exchange CF for that contract month; rounding conventions differ by exchange.
- Mismatched dates or snaps: bond settlement versus futures delivery, bond mid versus futures last, different snaps. Use the same snap; record the settle date.
- Repo: overnight versus term, GC versus own repo, 360 versus 365, wrong horizon (to a different delivery date). Not terming the repo is the commonest error. A flat repo curve in the data (identical terms most days) means the source is not observing terms.
- Using IRR minus GC to rank CTDs when a bond is special, or treating the lowest outright basis as CTD.
- Reading net basis as free money: it includes option value; a positive CTD net basis is "too high" only if vol is too low to switch. WI-issue CTDs inflate measured option value, and WI cells may be blank until issued.
- Reading IRR as a hold-to-delivery return near delivery: annualisation explodes. Do not use it inside the last few days.
- Not tailing, not face-matching after the last trade day, rounding contracts without checking the 1-tick effect on 100mm+ packages (rounding 114.84 to 115 contracts changed one trade's P&L by about USD 625).
- Option models: one-factor models understate option value when yields are far from the notional coupon (the JGB example: under 1 sen versus 7 sen); a scenario model of parallel shifts plus twists may overstate switch value; model errors can dominate a 1-tick edge. Calibrate to futures-option implied vol and check model forwards equal market forwards.
- Ignoring balance sheet: the legs are not nettable at a dealer; LR charge, quarter-end shrinkage and margin steps mean an apparently cheap basis can stay cheap. Do not assume convergence before delivery.
- Basis risk is live from the contract's first day, not only in the delivery month. Buying the net basis normally loses the premium (about 1 tick if bought at 1 tick and delivered optimally, more for a non-CTD); after the last trade date the futures price is fixed while cash still trades (BofA, Primer, 10 Jul 2025).
- Negative-carry long basis bleeds while waiting for the option; positive carry masks time decay. Count both.
- Regime: option value depends on notional coupon versus yield level, curve slope and vol, supply (new CTD from an auction), and basket changes. Re-check each roll. Systematic flattening as yields rise reduces switch value; unsystematic spread vol raises it.
- Market differences: EUR/JPY single delivery day (no timing option) with different CF conventions; euro CTDs can be special, so highest-IRR is often wrong; gilt ex-dividend can remove a CTD; AUD is cash-settled; JGB futures are structurally rich to cash. See [markets and conversion factors](references/markets-and-conversion-factors.md).
- Not every short future is a basis trade (curve arbitrage, auction hedges). Positioning proxies overstate cash basis.
- Forward gross basis equals forward net basis only when the forward date is the delivery settlement; a "forward basis" at any other date still carries carry to delivery (QF Stack Exchange, May 2018).
- A future has no pure carry: do not quote futures carry as CTD yield minus IRR (the future forgoes coupons). List convergence to spot, rolldown, option decay and rich/cheap convergence separately (QF Stack Exchange, Feb 2018).
- Negative gross basis normally says deliver early, but a low-CF CTD with a wildcard can make waiting optimal when the gross basis is only a few ticks negative; CF near 0.95 is best delivered at once (JPM, Good things come to those who wait, 18 May 2018).
- Short-basis financing: the reverse repo rate, not GC, funds the short. In a 2000 case the short basis in the issue that went special lost USD 14,276 per 10mm, nearly 11,000 of it from the lower reverse rate, while the old issue's short basis made USD 14,211 (Burghardt, 2005). The OTR basis is more liquid than the CTD basis but selling it is negative carry when the OTR is special.
- April 2025 showed hedged-basis desks stopped out without systemic stress; swap-spread trades were hit harder. After a stress move "sometimes it's best to do nothing until an opportunity presents itself".

## Output
Return, per contract and as-of date/snap, a basis sheet and a verdict.
1. **Header**: contract, futures price, snap, bond settle date, delivery date used (first/mid/last, with the reason), repo source (own / GC / overnight proxy), day basis, CF source (exchange / computed), data flags.
2. **Table per deliverable** (sorted best CTD first): bond, CF, clean price, gross basis (32nds), carry (32nds), net basis (32nds), forward yield, term repo used, IRR, IRR minus own repo (bp), probability of being CTD (if modelled), option value (if modelled), option-adjusted net basis and IRR, special flag.
3. **Verdict**: CTD and runner-up; edge in ticks and bp after option adjustment; richness vs cheapness; confidence (vol sets agree? repo own vs GC? model error band?).
4. **If a trade is proposed**: legs and sizes (face, CF-weighted contracts, tail, DV01-hedge alternative, after-LTD face match), entry level, target, stop in ticks, carry per day, P&L table for yield shifts (-100..+100bp) and steepening, repo +25/+50/+100bp, delivery-timing scenarios, margin and liquidity call in a 10-tick day, funding assumption and leverage; roll/exit date.
5. **Hand-offs**: stress and sizing to [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md) and [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md); packaging to [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md); write-up to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts
- [`scripts/basis.py`](scripts/basis.py): CBOT conversion factor, accrued, forward clean price with coupons, IRR, gross/net basis and carry, CTD sheet sorted by `IRR - own repo`, CF/tail/DV01 hedge sizing, and a canonical-table front end (`--fut-id --date --dir`, optional `--delivery first|last|auto`, `--repo-pct`). Repo day basis is set by currency (365 for GBP/JPY/CAD/AUD/NZD); supports ACT/ACT ICMA and ACT/365F accrued; other day counts must be passed in. `python scripts/basis.py --help`. `--selftest` checks 7 published CFs, the Burghardt carry/IRR case, the Tuckman net-basis case run through the canonical-table front end, and exact identities (IRR = repo at zero net basis, IRR = repo - NB/dirty x 360/d), and exits non-zero on failure.

## Related skills
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): values the switch, wildcard and end-of-month options that sit inside net basis
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): roll fair value, calendar IRP and roll-adjusted generics
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): futures versus swaps and CTD-based hedging
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): GC versus special repo, quarter-end turns, sponsored repo
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): leverage-ratio and capital hurdles behind the basis
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 conventions and hedge-ratio transforms
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts, settlement and contract conventions by market
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and rolldown of bonds and futures
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): reserves, standing facilities and balance-sheet drivers of repo pressure
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): deliverability premium in fitted curves, CTD cheapness versus neighbours
- [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md): basis versus listed-option vol arbitrage
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): leveraged-fund shorts and asset-manager longs as a basis-crowding gauge
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used above

## References
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis, 3rd ed. (McGraw-Hill, 2005): core definitions and formulas (CF, carry, IRR, BNOC, option-adjusted basis), CTD measures, repo stub DV01, basis as options, short-basis backtests, synthetic replacement
- Tuckman and Serrat - Fixed Income Securities: Tools for Today's Markets, 4th ed. (Wiley, 2022): forward by replication, tailing, net basis, IRR, basis P&L, post-LTD hedge, March 2020 trade
- CME Group - Understanding Treasury Futures (Johnson, Kerpel, Kronstein; Nov 2017): CF, invoice, IRR ladder, BPV versus CF hedge ratio, futures-plus-cash returns
- Salomon Brothers - Understanding Treasury Bond Futures: Questions and Answers (Oct 1990): CF method, converted forward, IRR/CTD rules, hedging, delivery timing
- J.P. Morgan - Special delivery: how delivery options distort rich/cheap metrics for US Treasury futures (Salem, Younger, St John; 4 Dec 2019): IRR identity, option-adjusted IRR, repo wedge
- J.P. Morgan - Good things come to those who wait: the wildcard in early delivery (Salem, Younger, Zhao; 18 May 2018): negative gross basis and delivery timing
- BofA Global Research - US Rates: Primer: US Treasury futures and basis (Ralph Axel, 10 July 2025): definitions, contract terms, delivery-date convention, wildcard test, scenario payoff, non-CF weights, positioning
- BofA Global Research - US Rates Alpha: Buy futures basis = cheap options (Axel; 10 Apr 2025): basis trade structuring, thresholds
- BofA Global Research - US Rates Data: Futures Basis Report (7 Aug 2025): analytics schema, scenario grid, levels
- J.P. Morgan - US Bond Futures Rollover Outlook, Sep 2026 / Dec 2026 (Ozil, Hayward, Alptuna; 12 Aug 2026): contract-level basis/IRR/carry table, funding sensitivity
- J.P. Morgan - Born(e) in the US(A) (Ozil, Hayward, Alptuna; 31 Jul 2026): factor-scaled metrics, CF-weighted long basis with termed repo
- J.P. Morgan - The switch and the spur (Ozil, Hayward, Alexeev, Alptuna; 29 Oct 2026): probability-weighted BPV/CF hedging
- J.P. Morgan - Why we should all care about Treasury futures basis (Younger, Salem, St John; 12 Mar 2020): basis primer, sizing, IRR as funding barometer
- J.P. Morgan - Eurex CTDs wobble with higher yields (Gupta, Mayfield; 2 Oct 2026): EUR net basis versus option value
- Morgan Stanley - Buy Higher Rates Protection at a 30% Discount (Zhou et al.; 27 Aug 2026): long basis as convexity, P-weighted DV01
- Citi Research - US Rates Weekly: Fixing the plumbing (30 Sep 2019) and Summer lull (17 Jul 2015): IRR regression versus term GC, net basis as floored option
- Citi Research - Treasury Futures Roll: Sep26-Dec26 (Datla et al.; 18 Aug 2026): delivery timing statistics
- Citi Research - Japan Rates Weekly (Fujiki; 21 Aug 2026): JGB IRR versus OIS
- Düring - Fixed Income Trading and Risk Management (Wiley, 2021): generic CF/net basis/IRR, Eurex basis sheet, euro CTD-special caveat, notification-jump
- Huggins and Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): fair futures = forward/CF - DO, model-arbitrage rule, JGB option, specialness
- Aikin - STIR Futures, 2nd ed. (Harriman House, 2012): Schatz and US 2y net basis walk-through
- Credit Suisse - US Treasury Futures Focus: New Ultra Long Contract (Li, Chang; 28 Sep 2009): basket size and option value, CF and DV01
- CFTC Market Risk Advisory Committee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): mechanics, profit condition, risk taxonomy
- CFTC Office of the Chief Economist - Observations on the Treasury Cash-Futures Basis Trade (Mixon, Orlov; Sep 2024): sizing and regression scale
- Treasury Borrowing Advisory Committee - Discussion of Treasury Futures Positions Across Investor Types (30 Jan 2024): asset-manager demand, replication cost, crowding dashboard
- Convexity Maven (Bassman) - Leverage is NOT a four-letter Word (26 Jan 2023): special-repo synthetic carry
- Quantitative Finance Stack Exchange - threads on implied repo conventions, gross-basis drop, net-basis balance-sheet hurdle (2018-2025): IRR conventions, LR hurdle
- Darbyshire - Coding Interest Rates (book; edition and year not stated in the copy read): CF, gross/net basis, IRR, futures yield and risk formulas
- Hasbrouck - Empirical Market Microstructure (NYU Stern teaching notes, draft 1.1, 2004): threshold error-correction for cash-futures spreads
- J.P. Morgan - US Interest Rate Derivatives: Near, far, wherever yields are (Ozil, Hayward, Alexeev, Alptuna; 2 Oct 2026): USZ6 net basis near 15/32 judged unattractive
- J.P. Morgan - Basis Scenario Analysis Report, U.S. Basis Traders Supplementary Package (Ozil, Hayward, Alptuna; 28 Oct 2026): term repo to delivery, price-vol inputs, negative FV gross basis, when-issued handling
- J.P. Morgan - What about Bonds? SLR relief, Treasury supply, and long-end spreads (Younger, St John; 2 Apr 2020): WN wildcard above 10 ticks when post-close vol persists
- Barclays Research - US Treasury Futures: Divergent CTD switch behavior in US and WN (Mok, Nashikkar; 20 Aug 2026): basis as a directional CTD view
- Barclays FICC Research - US short interest rate primer (Abate; Jan 2025): non-nettable basis legs, clearing mandate, cross-margining, quarter-end repo
- BofA Global Research - US Treasury repo primer, 2025 edition (Cabana, Craig; 7 Jul 2025): specials and the fails charge
- Credit Suisse - Basis Points: A Guide to the Front-End and Basis Swap Markets (Lantz, Chang, Dorji; 18 Feb 2010): synthetic term repo from overnight funding plus OIS
- Yadav and Younger - Central Clearing the U.S. Treasury Market (University of Chicago Law Review, vol. 92, 2025): double margining and haircuts
- Federal Reserve Board - FEDS Notes: What Happens on Quarter-Ends in the Repo Market (Bostrom, Bowman, Rose, Xia; 6 Jun 2025): quarter-end repo turns
- Conks (Monetary Mechanics) - Plumbing Notes: The Basis Trade Scare (17 Nov 2025) and Money Market Updates (17 Apr and 19 May 2025); Demystifying the Repo Market Part III (28 May 2024): repo tolerance, April 2025 stop-outs, haircut as leverage (practitioner commentary)
