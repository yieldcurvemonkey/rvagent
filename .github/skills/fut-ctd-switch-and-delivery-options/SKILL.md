---
name: fut-ctd-switch-and-delivery-options
description: 'Values and trades the delivery options embedded in physically delivered bond futures - cheapest-to-deliver (CTD) switch / quality option, wildcard, end-of-month (EOM), timing and new-issue options - via CTD scenario analysis (parallel + twist shifts, switch points, CTD probabilities, delivery option value, option-adjusted net basis / IRR, probability-weighted futures DV01/CF), and flags delivery squeezes and fails. Covers CBOT TU/FV/TY/UXY/US/WN vs Eurex Schatz/Bobl/Bund/Buxl/OAT/BTP, Gilt, JGB, CGB, cash-settled AUD. Use when asked about cheapest-to-deliver (CTD) switch risk, switch point, crossover yield, delivery option value (DOV), net basis / BNOC vs option value, option-adjusted basis, wildcard value, delivery timing (first vs last day), non-dominant CTD, CF bias, futures negative convexity, hedge-ratio jump after a switch, or a short squeeze / negative net basis in the CTD. Pricing the option against Board or swaption vol: vol-basis-vs-vol.'
---

# CTD switch and delivery options

The short in a bond future chooses what, when and (in the US) at what time of day to deliver. Those choices are
options the long pays for, so futures trade below the CTD forward by the delivery option value (DOV), the CTD net basis
(BNOC) contains that value, and the futures contract behaves like "bullet minus options": it shortens duration in
rallies and lengthens it in sell-offs. This skill values the options by scenario, tells you whether a basis is rich or
cheap *after* the option is removed, shows where the CTD flips and how the hedge ratio jumps, and watches for the
opposite regime: a scarce CTD where net basis goes negative. Carry, implied repo and plain basis mechanics are in
[fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md).

## When to use
- "Which bond is CTD, what is the probability it changes, and at what yield / curve twist?" (switch points, CTD map).
- "Is the net basis rich or cheap?" - compare BNOC with option value (option-adjusted basis), not with zero.
- "How much is the wildcard / EOM / switch option worth in the front vs back contract?" (roll and calendar calls).
- "When will the short deliver?" - first vs last delivery day, and which dates to price implied repo to.
- "How many contracts hedge this bond if the CTD switches?" - CF-adjusted DV01 jump, probability-weighted DV01.
- Eurex vs CBOT vs gilt / JGB differences in what options exist.
- CTD scarcity: negative net basis, IRR above the bond's own term repo, open interest vs CTD outstanding.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Contract terms: delivery dates, last trade date, notional coupon, tick | `fut_static` | per contract month | `first_delivery_date`, `last_delivery_date`, `last_trade_date`, `settlement_type` (physical vs cash) |
| Deliverable basket and conversion factors (CF) | `fut_basket` | point-in-time | Use exchange CFs. Include when-issued (WI) bonds from their issue date, flag them |
| Bond terms (coupon, maturity, freq, day count, ex-div rule) | `bond_static` | static | Needed to roll forward and reprice at delivery |
| Bond clean prices (and yields) | `bond_quotes` | daily snap, same snap as futures | `is_wi`; use settle-snap, never mix snaps |
| Futures settlement price | `fut_quotes` | daily | `price_px` decimal; `oi_cnt` for squeeze checks |
| Term repo to delivery (GC and bond-specific) | `repo_rates` | daily, terms to the delivery date | Specials flip the CTD only when large (see Method 1). Day count: ACT/360 for USD/EUR/CHF/SEK/NOK, ACT/365 for GBP/JPY/CAD/AUD/NZD - state it |
| Futures-option normal vol | `opt_quotes` (`nvol_bp`) | ATM, nearest expiry | Yield-bp per year, level vol for scenarios; expires about a month before the future's last trade date. If only a price vol (points) is available, divide by the CTD's DV01 in price per bp (CF-adjusted for the future) - do not multiply by duration |
| Yield history of deliverables | `bond_quotes` (`ytm_pct`) | >= 1y daily | Yield betas, spread vol (longest - shortest), sd of the spread to the CTD |

If an input is missing, ask for it or hand off to the data adapter. Never invent CFs, repo or vols. Take the
contract-level tick from `fut_static.tick_size_px`; state option values in ticks and in price points.

## Method
### 1. Fix the contract, basket and CTD today
- Invoice = `F x CF + accrued`; CF = price per 1 of face at the notional coupon yield (CME 6% since the Mar-2000
  contract, 8% before; Eurex 6% except Buxl 4%; Gilt 4% in the canonical spec table, 7% in the older literature -
  take the value from `fut_static`). CF is fixed per bond per contract month and does not move with yields (Salomon
  Brothers, Understanding Treasury Bond Futures, Oct 1990).
- Gross basis `GB = P_clean - CF x F`. Net basis `NB = P_fwd - CF x F` where `P_fwd` is the clean forward at the repo
  to the delivery date, so `NB = GB - carry`. At expiry `F = min_i(P_i / CF_i)`; before expiry
  `F = min_i(P_fwd_i / CF_i) - DOV` (Burghardt et al., The Treasury Bond Basis, 2005).
- CTD screens, in order: (1) highest implied repo (IRR) = lowest forward-price/CF; (2) when bonds trade special,
  largest `IRR - own term repo` (rarely binds); (3) lowest NB is a rough check only (it ignores price level). Never
  pick by lowest price, highest yield or lowest gross basis. Inside the delivery month use the minimum converted cash
  price, not a short-horizon IRR (Burghardt 2005; Salomon 1990).
- Market-implied DOV (futures points) `= NB_CTD / CF_CTD`; NB and TDOV are in bond price points (`= CF x` futures points).
- Exact link between repo and net basis: `IRR = repo_CTD - (NB / dirty_price) x 360/n_days` (365 for ACT/365 repo markets). Going from 60 to 30 days to
  delivery doubles the repo gap for a constant NB (J.P. Morgan, Special delivery, 4 Dec 2019).
- Duration rule (CF bias): CFs equalise converted prices only at the notional yield. Below it the lowest-duration
  bond (high coupon, short maturity) is CTD; above it the highest-duration bond. At equal duration the highest-yield
  bond is CTD; a flattening of the deliverable curve favours shorter bonds, steepening favours longer ones (Burghardt
  2005; CME, Understanding Treasury Futures, Nov 2017; Tuckman & Serrat, 2022). With 30y at ~5-6% the US switch option
  is live; with yields far below 6% the shortest-duration bond is always CTD and the option is near worthless
  (J.P. Morgan, Special delivery, 2019).
- Factor-scaled view: sort the basket by BPV/CF (not maturity) to see where the CTD sits and which way it can move;
  futures DV01 ~ CTD forward DV01 / CF. Basket eligibility (remaining-maturity windows per contract; FV takes only original-issue
  5y notes) and last trade / last delivery rules are tabulated in [references/market-and-case-notes.md](references/market-and-case-notes.md) section 6 (BofA, Primer: US Treasury futures and basis, 10 Jul 2025).

### 2. Run the scenario engine ([`scripts/ctd_scenarios.py`](scripts/ctd_scenarios.py))
1. Forward each deliverable to the delivery date at its repo: `P_fwd_dirty = (P_clean + AI)(1 + r x d/B) - sum(coupon x (1 + r x d_c/B))` (B = repo day-count basis, 360 or 365; `--repo-basis`),
   then clean `= dirty - AI(delivery)`. Solve the forward yield `y_fwd` from the forward clean price.
2. Shock: `dy_i = beta_i x level + slope x (pos_i - 0.5)` where pos runs 0 (shortest) to 1 (longest). Level shifts
   the OTR / reference bond; betas come from regression of each bond's yield changes on it (betas are unstable:
   re-estimate, and check the model's crossover against a dealer's printed one - a few bp of difference from betas and convexity is typical).
3. Reprice each bond at delivery from `y_fwd + dy_i`; converted price `a_i = P_i / CF_i`. CTD = argmin. Scenario
   futures = min a_i.
4. Weights: normal level distribution with `sd_level = nvol_bp x sqrt(T)` (T = years to the last trade date, nvol from
   listed futures options, which only approximates a basket and expire about a month before the future) and an independent normal
   slope with `sd_slope` = empirical sd of the horizon-length change in (longest - shortest) yield. Do not just
   scale 1Y spread vol by sqrt(T): spread vol is not sqrt-t and runs about 2x higher into delivery
   (JGB candidate spread vol more than doubled in the final year; Huggins & Schaller, 2024).
5. Mean-adjust each bond's simulated converted price so its mean equals the forward (removes convexity drift of the shocks).
6. Outputs: `P(CTD_i)`; `DOV = min_i(fwd a_i) - E[min_i a_i]`; model net basis `TDOV_i = CF_i x E[a_i - min_j a_j]`
   (the theoretical option value, per bond); fair futures `E[min a]`; futures DV01 `= sum P_i x DV01_i/CF_i`;
   parallel switch points by bisection.
7. Always run a grid view too: parallel shifts -120..+120bp (10bp inside +/-100, 20-25bp outside) crossed with twists
   of +/-1.5 sd; mark the CTD in each cell and show the CTD's own NB per cell, which is the switch-option payoff
   profile (convex in rates; long CTD basis = long that option). `*`/blank = no switch (Burghardt 2005, Exh 2.10;
   J.P. Morgan, Basis Scenario Analysis Report, Oct 2026; BofA, Futures Basis Report, Aug 2025).

DOV drivers: (1) yield level vs the notional coupon, (2) yield vol, (3) yield spread across the basket, (4) vol of
those spreads, (5) basket diversity (range of coupon/duration and how finely it is sampled). DOV is highest near a
switch point, is zero at delivery, and is non-monotonic in yield: it falls after a big rally (old CTD dominant again)
and after a big sell-off (new CTD dominates). Never extrapolate a regression of DOV on yield (J.P. Morgan, The switch and the spur, Oct 2026;
Eurex CTDs wobble, Oct 2026).

Systematic spread behaviour matters: if the deliverable curve steepens as yields fall and flattens as they rise, the
actual crossover sits below the static parallel one and the option is worth *less*; non-systematic spread moves
(buybacks, squeezes, issuance surprises) *raise* it (Burghardt 2005).

### 3. Option-adjusted rich/cheap
- `TDOV` (model) vs `NB` (market) per bond. `OAB_i = NB_i - TDOV_i`. Market futures minus model futures
  `= -OAB / CF` (Burghardt 2005). OAB > 0: basis rich / futures cheap, sell the basis. OAB < 0: basis cheap / futures
  rich, buy the basis.
- Option-adjusted IRR: `OA_IRR = IRR + (option value in bond price points / dirty price) x 360/n_days`; compare with CTD term repo. Any
  residual is pure model-implied rich/cheap, not guaranteed to close before delivery (J.P. Morgan, 2019).
- Plain IRR-vs-repo and BNOC-vs-zero mislead whenever the option is not ~0: futures look optically cheap (positive
  NB / low IRR), especially UXY and WN. Net basis of the CTD ~0 and flat carry through the month means a long
  basis is a near-free option; at 1-tick option values the model cannot be validated against a quote (half-tick
  rounding = +/-50%).
- Convergence rule used by dealers: NB below the modelled DOV -> basis underpriced and expected to widen toward the
  option value; above -> overpriced.
- Buying the net basis normally costs the premium: buy at 1 tick and deliver optimally and you lose about 1 tick, more on a non-CTD bond; the
  long is paid only if the option moves in the money before delivery (BofA, Primer: US Treasury futures and basis, 10 Jul 2025). Net basis > 0 means futures trade below
  the converted CTD forward ("excess carry" for the long). Net basis < 0 means futures rich to forwards with the options worth ~0.
- Futures-vs-options trade: the basis is a long straddle-like option (high-duration bond basis = put on yields; low-duration basis = call on yields; middle = strangle).
  Compare model value with listed futures options struck near the switch yield; if the basis costs less, buy basis and
  sell the option (residual risks: spread moves, repo, profile mismatch, option expiry a month before LTD). See [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md).

### 4. Hedge ratios across switch points
- Futures DV01 jumps at a crossover: use `P`-weighted `DV01/CF`, not the current CTD's. Locking the CTD
  materially underestimates contract duration after a switch (J.P. Morgan, 2026; Morgan Stanley, Higher Rates, Aug 2026).
- Non-CF weighting: for any weight W, `B - W x F = (B - CF x F) + (CF - W) x F`, i.e. the CF basis plus a futures overlay. A non-CTD bond hedged against
  the future is mostly a curve trade between that bond and the CTD (BofA, Primer: US Treasury futures and basis, 10 Jul 2025). Hold a futures hedge as
  "bullet minus options": it is a better convexity hedge than cash for callable / MBS exposure, though MBS option value is orders of magnitude larger (BofA, same).
- Below the crossover (low-duration CTD) the rule-of-thumb DV01 is too low (overhedged); above it too high.
  Futures can be negatively convex near crossovers even though every deliverable is positively convex (Burghardt 2005; Salomon 1990).
- Re-size: report the percentage change in CF-adjusted DV01 vs the current CTD at each candidate: ~+37% Buxl, +8%
  BTP, -7% OAT (switch back to the shorter Nov35), ~+47% for a 50bp sell-off in USZ6 (J.P. Morgan, Eurex CTDs wobble, Oct 2026; Morgan Stanley, Aug 2026).
  CF-weighting hedges only the CTD; use DV01 weighting for other bonds and re-evaluate after ~20-25bp moves (CME 2017).
- After the last trade date the futures price is fixed: switch to a face-matched hedge (1 contract per contract face, e.g. $100k; $200k TU) or
  `(1 - CF) x face` stays unhedged.

### 5. Timing: first vs last delivery day
- Delivery runs intent, notice, delivery over ~2-3 business days; use T+2 in carry (BofA, Primer: US Treasury futures and basis, 10 Jul 2025; CME describes a 3-day cycle). Be consistent with the repo term you use.
- Price to the last delivery day when carry is positive (repo below yield) and to the first when negative: FV trades to the first, WN to the last (BofA, Primer, 10 Jul 2025).
- Positive carry (repo < CTD running yield): deliver on the last day; negative carry: deliver at the start unless the
  remaining option value exceeds the carry given up. A month of negative carry is roughly `(repo - yield)/12`, e.g. repo
  100bp above yield ~ 8bp of invoice (Burghardt 2005).
- Price implied repo and net basis to *both* first and last delivery date; the useful life of a long-basis option is
  set by carry: flat carry = whole month, strongly negative carry = start of month (BofA, Buy futures basis, 10 Apr 2025).
- A switch to a lower-coupon CTD can turn carry negative and move the optimal date to the start of the month. Early
  deliveries concentrate when financing is high (Feb 2023: ~75% of Dec deliveries in the first two days); late
  deliveries dominate otherwise (>90% of TY/UXY/US/WN June 2026 deliveries in the last week; FV exception).
- Roll or close longs before the first day they can be noticed to avoid taking delivery.

### 6. Wildcard (US only: futures settle at 3pm ET, cash trades on, delivery may be declared until 7pm ET)
- Tail: a CF-hedged long basis holds `1/CF` face per 1 face delivered. After a post-close **rally** deliver and sell the
  `(1/CF - 1)` tail higher; a sell-off has no equivalent loss, you just wait. (CF > 1, as in the old 8%-notional contract, flips the sign: the
  short is short a tail and a post-close FALL pays; `x*` comes out negative and `wildcard_value` uses `|k|`; Burghardt 2005: $100mm 8-3/4% 8/20, CF 1.3093,
  1,309 futures, $30.9mm tail, 6/32 basis needs a 25.4/32 fall, `= 6/32 x 1.3093 / 0.3093`.) Exercise forfeits the remaining basis; FOMC delivery months (press conference 2:30pm) are where it matters most (BofA, Primer: US Treasury futures and basis, 10 Jul 2025). Exercise iff
  `(1/CF - 1) x x > GB`, i.e. `x* = GB x CF / (1 - CF)` (x = post-close price rise, points per 100 face; BofA, Primer:
  US Treasury futures and basis, 10 Jul 2025, equivalent to `GB x C < x (1 - C)`). It is a ~3-hour call on the tail,
  paid for with the gross basis on the delivered bonds.
- Value: backward induction over the delivery days, `V_i = k s phi(W_i/(k s)) + Phi(W_i/(k s)) W_i`,
  `W_i = V_{i+1} + carry`, `k = 1/CF - 1`, `s` = post-close sd in price points; wildcard value = `V_1 - V_1(k=0)` (no double
  counting of carry) - `wildcard_value()` in the script. Sources differ by a factor C in how they express
  GB and the tail; this skill uses per-face-delivered units, which reconcile to the dollar P&L in the worked example below.
- Defaults: post-close yield sd 1bp per 2-hour window (baseline, ~1-1.5bp/day), doubled on FOMC days (2:30pm press
  conference; a vendor uses x3 - pick one, state it); scenarios 1 / 1.5 / 2bp. In high-vol regimes 30y post-close vol
  runs 1.5-2bp. Convert to price points with the CTD's DV01 (price per bp per 100 face).
- Worth most for low CF (<0.9) and high vol: WN/UB, then TN, FV, TY; UXY has *only* the wildcard (3-bond basket). CF < 0.9
  stays optimally delivered late even with a clearly negative basis; CF ~0.95 delivers ASAP. A post-crisis shift to
  low-coupon CTDs and flatter curves (cheap to wait) increased it. Over 2025-26 it was "near non-existent" in the high-coupon/low-vol regime.
- Long-basis breakeven futures price for the wildcard: `F_BE = F + GB / (1 - CF)` (front); back = front BE - calendar roll.
- Owning the wildcard cheaply: bearish-weighted calendar spreads in high post-close vol regimes (J.P. Morgan, Aug 2019).

### 7. End-of-month and new-issue options
- EOM: after the last trade date the invoice is fixed but bonds keep trading; the short picks the bond with the lowest
  `P_i - CF_i x F_settle` ("BPV decides, not duration"). It is a long strangle, cost = CTD BNOC at the close; it is
  what keeps the CTD BNOC above zero on the last trade day. Crossover shift = BNOC gap / BPV gap (reference
  numbers in [references/market-and-case-notes.md](references/market-and-case-notes.md)). Value with annual normal vol from ATM futures options and a switch-like model with the futures price frozen.
- US last trade dates: TU/3Y/FV last business day of the month; TY/TN/US/WN seven business days before; the EOM window for
  the latter is ~7 business days. Last switch day is the second-to-last business day; fail risk in the last days is real (below).
- New issue: add anticipated auctions to the projected basket (a Schatz back-month CTD is often not yet issued: buy the calendar if a large/cheap new issue is expected, sell if scarce/rich; Burghardt 2005); if the new bond will clearly be CTD, back out its implied
  price from the future. The option is usually worth little (high yield = high coupon = low duration) except in the
  5y/10y when yields are high but falling. A basket gap can move the CTD far (2015: CME excluded a 5.375% Feb-31 and the
  CTD jumped from 6.25% May-30 to 4.5% Feb-36; equal-DV01 roll needed 34% fewer contracts; Citi, The long end basket case, Feb 2015).

### 8. Ranking and attribution
Switch option is "far and away" the largest, EOM next, timing and wildcard "usually nothing" in the 2005 text; in the
2018-26 US regime the wildcard (WN, TN) and the switch (US, UB when 30y > ~5.5%) dominate, EOM is minor (Burghardt 2005;
J.P. Morgan 2019-2026). Regime context (BofA, Primer: US Treasury futures and basis, 10 Jul 2025): with yields well below 6% the CTD net basis is often close to 0 and the wildcard still gives 4-5 ticks on some contracts; near 6% rates nets were often 10+ ticks. Total option value = switch + wildcard + EOM (a vendor tool sums the selected options and subtracts `total x CF_i` from each bond's NB). A WI bond that is CTD inflates the back-month option (TY back ~4+/32 in Aug 2026): show it with and without.

### 9. Delivery squeezes and fails
- Normal theory: every NB > 0; in practice with a negligible switch probability many desks set the CTD NB to 0. Negative NB
  is rational only when CTD supply is short or fail risk is priced. Inside the delivery month a negative NB on any deliverable is an immediate
  arbitrage (short future, buy bond, deliver); before it, negative NB can persist (Salomon 1990).
- Fair CTD BNOC `= P(fail) x (CTD BNOC - 2nd-CTD BNOC)`; implied `P(fail) = CTD BNOC / (CTD BNOC - 2nd BNOC)`.
- Signals: negative CTD NB; CTD IRR above its *own* term repo and approaching central-bank/unsecured funding;
  CTD repo special; open interest several times CTD outstanding; wide gap to 2nd CTD; calendar widening as shorts roll.
  Alternative funding (trusted counterparties, central-bank operations) caps the CTD IRR and floors NB if enough CTD exists.
- The most obvious basis short is the most squeezable; size with stops. Never hold the front CTD into expiry expecting the
  back month to support it when it is not deliverable there (it loses its CTD premium).
- Mechanics: have the CTD "in the box" at least 2 days before delivery (no ordinary repo the last 2 days); a futures fail
  (fine plus the exchange picking the bond) is far worse than a cash fail; waiting too long to exercise the EOM option is the single greatest danger.
- Open interest can far exceed CTD supply; exchanges pooled/segregated baskets for CTD funding; ~2.8% of contracts
  historically go to physical delivery (CFTC MRAC, Dec 2024), so almost all risk is in the *price* to the last trade date.

## Worked examples
1. **Net basis and "solidly CTD" (TYU1, 14 May 2021, repo 0.015%; Tuckman & Serrat, 2022).** CTD 2.875% 5/15/28, CF 0.8338:
   `GB = 110.7734 - 0.8338 x 131.5469 = 1.0896` (34.9 ticks), `NB = 109.7172 - 0.8338 x 131.5469 = 0.0334` (1.1 ticks),
   carry 33.8 ticks; next-cheapest NB 24.8 ticks, longest bond 274 ticks. `F = 131.55` vs `fwd/CF = 109.7172/0.8338 = 131.59`:
   the CTD NB is pure (tiny) option value; the future is essentially a forward on that bond.
2. **Option-adjusted basis (Burghardt 2005, 4 Apr 2001, June bond).** CTD 7-5/8%: basis 18.1, carry 13.6, BNOC 4.5, TDOV
   8.0, so OAB = -3.5/32 and futures 3.5/1.1936 = 2.93 ticks *rich* (fair 103-27 vs 103-30). Grid behind it: level -100/0/+100bp
   x slope steeper/beta/flatter with probabilities 0.16/0.68/0.16; BNOC cells [20,2,20], [25,1,15], [30,3,10] give
   `0.16x7.76 + 0.68x7.08 + 0.16x8.44 = 7.41/32` for one issue. A short CTD basis is short a strangle: shorting the 10y CTD basis three months before expiry (25 contracts, Jun-98 to Jun-04) saw BNOC fall in 23 of 25
   (avg 6.7 -> 4.9/32) but a high hit rate is not proof of richness; stress level *and* twist (Dec-01: +60bp with 1.5 sd steepening gave 17/32 vs <= 6/32 for parallel moves).
3. **USZ6 / WNZ6 switch map (J.P. Morgan, The switch and the spur, Oct 2026).** DOV rose from ~0 (early Sep, 30y > ~5.6%) to
   ~18/32 USZ6 and ~7/32 WNZ6; USZ6 non-dominant (3 bonds >10%, none >~30%). Fig 9: OTR 4.28% -> Nov-43 DOV 0;
   5.57% -> 4 7/8 Aug-45 DOV 9; 6.00% -> 2 3/4 Nov-47 DOV 8; 6.10% -> 1 3/8 Aug-50 DOV 3; BPV/CF jumps 1382 -> 1675 at the last
   switch. WNZ6 4% Nov-52 ~60% CTD, DOV peaks (4/32) near 5.59% and is 0 at 4.34% and 6.27%. The CTD walk is non-linear
   in shift (Barclays, Divergent CTD switch behavior, 20 Aug 2026): USZ6 -40bp 4.75% Nov43; -30..-10 May44; 0/+10 5% May45;
   +20 4.625% Nov45; +30/+40 3% Feb48; +50 1.375% Aug50; WNZ6 4% Nov52 from -40 to +10 then the shortest-maturity 2.25% Feb52 for +30..+50.
4. **Eurex table (J.P. Morgan, Eurex CTDs wobble, 2 Oct 2026).** Buxl CTD 2.5% Aug54 71%, CF 0.75153; the 0% Aug52 (27%) needs a 5.4bp spread
   change (1Y sd 3.2bp) or +23.7bp parallel and has CF-adjusted DV01 +37%; switch probability ~1/4, DOV ~25c vs NB ~8c. 10Y OAT: CTD already
   moved 3.5% Nov35 -> 3.7% Nov36 after ~70bp of sell-off *and* steepening; switching back needs ~24bp rally or 1.6bp
   flattening (1Y sd 0.2bp). Read the required change against its sd: a 0.7bp gap with sd 0.2bp is 3.5 sd and the note still quotes ~2% (fat tails / short-horizon sd), so do not apply a normal tail blindly.
5. **Wildcard P&L (BofA, 10 Jul 2025, WNU5).** Long $100mm 4.75% 11/15/53 vs short 734 WN (CF 0.7342), GB 5 ticks, NB 4. After
   3pm the market rallies 1 point: deliver 734 contracts, give up `734 x 5 x 31.25 = $114,688`, sell the $26.6mm tail one point higher for
   `+$266,000`; threshold `x* = (5/32) x 0.7342 / 0.2658 = 0.43pt` (the script's `wildcard_exercise_threshold`).
6. **Wildcard breakeven (RiskVal, Future CTD Scenario Analysis, 2024; UXYH1, 9 Mar 2021):** F 148-027, GB 0.326/32, CF 0.6226 -> `F_BE = 148.0898 + (0.326/32)/(1-0.6226) = 148.1168`.
7. **Replication (Morgan Stanley, Higher Rates, 27 Aug 2026).** ~50bp parallel sell-off switches USZ6 CTD from 5% May-45 to 1.375% Aug-50
   (futures duration +47%). Short the CF-sized Nov-43 plus two payer swaptions fitted to the residual payoff costs ~12.4 ticks vs a Nov-43
   net basis of ~8.7 ticks (basis ~30% cheaper than the replicating option); caveats: leaves swap-spread risk, theta decays but the switch payoff does not.
8. **Script on a constructed basket.** Two zero-coupon bonds with CF = price at 6%: the crossover is exactly at 6.00% and a forward
   yield of 6.5% with 50bp level sd gives `P(longer CTD) = Phi(1) = 0.84` (the script's selftest; illustrative, not market data).

More dated cases and contract tables: [references/market-and-case-notes.md](references/market-and-case-notes.md); model formulas:
[references/option-models.md](references/option-models.md).

## Signals & interpretation
- **Is the switch live?** Count bonds with >= 10% CTD probability and the top probability. Top <= ~30% = "non-dominant" (high
  switch potential, high DOV). Sharp change in CTD probabilities for a small shift = high DOV. A basket with several bonds
  within 0-1/32 of NB has a rich option; the stat that matters is the *distance to the nearest crossover in sd units* (shift needed / horizon sd, and spread needed / spread sd).
- **Basis vs option.** Working rule (not from a source): `NB - DOV` (or OAB) > ~1 tick: basis rich, sell basis / buy futures; < -1 tick: buy basis. Treat |OAB| < 1/2 tick as noise
  (model error, tick rounding). Trade-level example: long CTD basis at gross -1, net 0, target 1 tick of option payout, stop -4 ticks (BofA, 10 Apr 2025).
- **Direction.** Yields rising toward/above the notional coupon: sell long-duration basis, buy short-duration basis; falling below: the reverse
  (CME 2017). In a sell-off the NB narrows for bonds moving toward CTD and widens for those being displaced. Long USZ6/WNZ6 factor-weighted basis = put on yields.
- **Worst case for long basis:** yields barely move, curve flattens, option value decays; also dash-for-cash cheapening of cash vs futures and rising funding costs.
- **Local slope drives the switch:** US 15s20s (CTD sector), WN 25s30s. Bear flattening of the CTD sector keeps the CTD; steepening raises the odds of moving out
  (Barclays, Aug 2026). In WN, a sell-off anchors CTD to the *shortest-maturity* bond, so duration extends only ~2 years then shortens (positive convexity); in US it keeps extending.
- **Calendar:** different front/back CTDs make the roll directional on the CTD slope and on option value: front option < back option and back NB far below back DOV
  -> calendar cheap/bullish (see [fut-calendar-roll](../fut-calendar-roll/SKILL.md)). Same CTD in both = no switch optionality in the roll.
- **Squeeze/fail:** negative NB or IRR > own term repo -> price `P(fail) x gap`; do not treat as free money.
- **Contract cheapening vs cash:** contract duration extension in a sell-off cheapens the future vs cash; Treasury buybacks reduce switch risk.

## Pitfalls
- Using the current CTD for DV01 and hedging; ignoring that a switch re-sizes the hedge by ~8-50%.
- Parallel-only scenarios: they overstate CTD robustness; check twists of +/-1.5 sd (UB CTD zone moves ~20bp between twist cases).
  A model on parallel + twist shocks can overstate switch value modestly; replication diverges as the contract converges to one CTD.
- One-factor models undervalue the option far from the notional coupon (spread factors dominate; JGB: one-factor < 1 sen vs multi-factor 7 sen).
- A two-bond Bachelier switch map (one swaption-like payoff on the parallel shift, see option-models) fails when many deliverables are live: in one check a seven-bond long-bond basis was valued at ~1.6 vs ~4.0 by a dealer package.
- WI bonds are deliverable and can be CTD (TY Mar-27 CTD is a WI 7y) and carry bond-specific repo; they inflate measured option value, so show results with and
  without them. Net basis is huge before a contract trades: use zero-NB pricing for far contracts.
- Historical yield betas and spread vols are unstable: run several parameter sets; DOV is roughly linear in spread vol and fairly insensitive to correlations.
- FOMC multiplier is x2 in one dealer and x3 in a vendor; vendor docs are internally inconsistent on the wildcard window (6h vs 15h): verify.
- IRR into delivery is badly behaved (tiny denominator, unknown optimal day); compute IRR/NB to first and to mid-month delivery when early delivery is plausible. Around quarter and year-end the term repo moves implied repo materially (balance-sheet effects keep March TU/FV basis negative).
- CF quirks: CME rounds remaining term down to a quarter (TY, TN, US, UB; whole month for TU/FV/3Y), so a net basis may not converge exactly. Use the exchange's CFs; `ust_cf()` is only a cross-check.
- Option values of 1-tick size cannot be validated; do not over-trade the signal. Regime changes quarter to quarter: reprice when post-close vol or the yield level moves.
- Basis does not reach theory before delivery: asset managers are structurally long futures (short basis) and levered funds short futures (long basis), limited by dealer repo (BofA, Primer, Jul 2025; TBAC, Jan 2024). Separately, CTD bonds carry a richness premium of ~0.6-1.2bp for TY CTDs vs a fitted curve (Citi, Fixing the plumbing, 2019).
- Specials: price the reverse repo on a short-basis leg (typically 10-25bp below GC, no floor); a special can flip a winning short basis (Burghardt 2005: May-Jun 2000 5y example in the case notes).
- Gilt ex-dividend rule can remove a CTD mid-month: futures price to it until its last deliverable day, then jump to the next CTD; cover or deliver on that day (Burghardt 2005).
- Do not read a squeeze into a large open interest: the Aug-2026 JGB roll with large OI and deep shorts passed without incident (Citi, Japan Rates Weekly, 21 Aug 2026).

## Output
Return (a) a **CTD table** per contract (front and back): bond, coupon, maturity, CF, forward clean, forward yield, CF-adjusted DV01, NB (ticks),
model NB (TDOV), OAB, P(CTD), shift/twist needed to switch and as sd of the horizon; flags for WI and special repo; (b) the **switch map**: parallel
crossovers (bp) and the shift x twist grid with CTD and CTD-NB payoff; (c) **DOV** split into switch, wildcard (and EOM where relevant) in ticks, with the vol inputs stated;
(d) **hedge**: probability-weighted DV01/CF and the % jump at each candidate; (e) **delivery date** assumed and carry to first/last; (f) a **verdict**
(rich/cheap in ticks after option adjustment, direction of the option, squeeze flag). Hand trade ideas to `rv-trade-idea-writeup` with entry, target and stop in ticks.
Tag assumptions (repo, vol, betas) and the as-of snap.

## Scripts
- [`scripts/ctd_scenarios.py`](scripts/ctd_scenarios.py): forward-prices a basket, finds CTD by parallel/slope shift, switch points, P(CTD), DOV,
  model net basis, OAB, probability-weighted DV01/CF and wildcard value. Models switch + single-date timing only (not EOM or new issues).
  `python scripts/ctd_scenarios.py --help`; `python -I scripts/ctd_scenarios.py --selftest` checks known answers (CF, forward price and repo basis, slope sign, exact zero-coupon crossover, Phi(1) probability, analytic DOV, TDOV/OAB identities, wildcard Bachelier limit and CF-symmetry). Pass `--repo-basis 365` for GBP/JPY/CAD/AUD/NZD repo.

## Related skills
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): GB/NB/IRR mechanics, carry, funding and balance-sheet cost of the basis trade
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): roll fair value; option-adjusted front vs back
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): futures vs swaps and CTD-based hedging
- [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md): comparing the delivery option with listed option / swaption vol
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): CTD option structures and payer skew
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): normal vol inputs from listed futures options
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): contract specs and settlement conventions per market
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 and hedge mapping
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): term repo, specialness, year-end
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): why negative net basis can persist
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): auctions, buybacks and new issues that change the basket
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): CTD premium vs fitted curve
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA shocks and yield betas
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): stressing basis positions
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): packaging the resulting basis / switch trade
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables

## References
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): CTD screens, scenario analysis, TDOV/OAB, option taxonomy and ranking, wild card and EOM numerics, squeezes, non-dollar contracts.
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): one- and multi-factor delivery-option models, OA BPV, JGB example.
- Tuckman & Serrat - Fixed Income Securities (4th ed., Wiley, 2022): cost of delivery, CTD at expiry, TYU1 net bases, tree pricing of quality/timing/EOM/wild-card options.
- Salomon Brothers - Understanding Treasury Bond Futures: Questions and Answers (Oct 1990): CF mechanics, cusps, four option components, DV01 across cusps.
- Alexander Düring - Fixed Income Trading and Risk Management (Wiley, 2021): net bases as options, timing, squeeze signals, new issues.
- BofA Global Research - US Rates: Primer: US Treasury futures and basis (Ralph Axel, 10 July 2025): contract and basket terms, option taxonomy, wildcard rule and P&L, non-CF weighting, scenario fair value.
- BofA Global Research - US Rates Alpha: Buy futures basis = cheap options (10 Apr 2025): net basis as premium, TYM5 trade.
- BofA Global Research - US Rates Data: Futures Basis Report (7 Aug 2025): CTD scenario grid schema and numbers.
- J.P. Morgan - Special delivery: how delivery options distort rich/cheap metrics for UST futures (4 Dec 2019): OA BNoC/IRR, wildcard fair value, timing.
- J.P. Morgan - Good things come to those who wait: the wildcard option in early delivery (18 May 2018): wildcard induction model and CF thresholds.
- J.P. Morgan Global Markets Strategy - The switch and the spur: CTD switches for USZ6 and WNZ6 (29 Oct 2026): DOV drivers, scenario tables.
- J.P. Morgan - Eurex CTDs wobble with higher yields: Buxl, 10Y OAT, 10Y BTP (2 Oct 2026): Eurex CTD probabilities, spread sd, DV01 jumps.
- J.P. Morgan - Basis Scenario Analysis Report (28 Oct 2026) and US Bond Futures Rollover Outlook (12 Aug 2026): BNOC grids, option value vs BNOC, carry to delivery.
- J.P. Morgan - Near, far, wherever yields are (2 Oct 2026); Born(e) in the US(A) (31 Jul 2026): USZ6/WNZ6 DOV and BPV/factor view.
- Barclays Research - Divergent CTD switch behavior in US and WN (20 Aug 2026) and The urgency question (2 Oct 2026): CTD by shift, local-slope drivers.
- Morgan Stanley - Buy Higher Rates Protection at a 30% Discount (27 Aug 2026): probabilistic CTD and swaption replication.
- Citi Research - Japan Rates Weekly: Ball is back in the US court (21 Aug 2026): JGB roll with large open interest passed without a squeeze; JGB calendar drivers.
- Citi Markets (Futures Sales) - CBT Treasury Futures Sep/Dec Roll: 10 trading days until FND (14 Aug 2026): roll calendar, deferred delivery option in the roll.
- J.P. Morgan - US Treasury Market Daily: Canary in a coal mine (25 Feb 2020); Impossible to walk in this muck (6 Mar 2020); What about Bonds? (2 Apr 2020): WN shorts as CTD-sector RV, WN wildcard fair basis.
- Treasury Borrowing Advisory Committee - Discussion of Treasury Futures Positions Across Different Investor Types (30 Jan 2024): CTD negative OAS, basis participants.
- Marc Henrard (OpenGamma) - Interest Rate Futures and their Options: Some Pricing Approaches (v1.3, 2012): AUD bank-bill cheapest-to-deliver option.
- Citi Research - US Rates Weekly: Summer lull (17 Jul 2015); US Rate Strategy Notes: The long end basket case (4 Feb 2015); Fixing the plumbing (30 Sep 2019); Treasury Futures Roll Sep26-Dec26 (18 Aug 2026): CTD probability scenarios, basket-gap jump, CTD richness premium, delivery-timing evidence.
- CME Group - Understanding Treasury Futures (Nov 2017): CF bias, directional basis rules, contract specs.
- CFTC Market Risk Advisory Committee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): delivery-option risk, delivery rarity.
- RiskVal Financial Solutions - Future CTD Scenario Analysis user guide (2023/2024) and Bond Futures help articles (2022-24): PCA scenario/probability model, wildcard and EOM formulas, breakeven price.
- Credit Suisse Fixed Income Research - US Treasuries Futures Focus: New Ultra Long Contract (28 Sep 2009): basket size vs option value, low-CF DV01/convexity.
- Stephen Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): Schatz/CBOT 2y specs and low-duration CTD rule.
- Quantitative Finance Stack Exchange threads on implied vs term repo, bond futures roll fair value, and last-day delivery (2018-2024): CTD rule via IRR minus own repo, timing option via accrued.
