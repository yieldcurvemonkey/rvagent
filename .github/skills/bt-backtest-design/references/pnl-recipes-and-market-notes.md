# P&L recipes by product, and G10 notes

Companion to [SKILL.md](../SKILL.md) section 6. All P&L is in the currency of the package, split into mtm / carry /
financing / cost so that `total = mtm + carry + financing + cost` (canonical `pnl` table). Mark at mid, open and close
at bid/offer, prior-day close or settlement as the price, model (matrix) price only where no quote exists, and state
this (Citi, EM Strategy Weekly, 20 Aug 2026, hypothetical P&L convention). Costs, impact and capacity are in
[bt-transaction-costs-and-liquidity](../../bt-transaction-costs-and-liquidity/SKILL.md).

## 1. Financed cash bond (UST, gilt, Bund, JGB ...)
- Buy the current benchmark, finance in overnight repo **including specialness**, do not roll into the new on-the-run during the hold.
  Total return = change in dirty price minus repo (JPM, Do androids dream of electric bonds?, 22 Nov 2017; JPM, TradeRunner, 16 Aug 2018: 5-day hold, daily initiation).
- Keep **clean price, accrued, coupon cash** as separate fields. Marking at dirty NPV without booking coupon cash separately lets trades that span coupon dates dominate P&L.
  Coupons and repo accrue over (last mark, next mark] while marked and over (last mark, now] at unwind.
- Financing: `financing_ccy = -dir x |MV| x (1 - haircut) x repo x yearfrac`, `dir = +1` long (pays repo, negative = cost), `-1` short (earns the reverse-repo rate); `repo = GC - specialness`, ACT/360 on the **dirty** value, haircut in [0, 1).
  Reverse repo is typically 10-25 bp below repo; specials have no floor (a June 2005 10y CTD traded at -15% overnight); thin basis margins flip sign on financing.
  Term financing vs overnight adds curve-slope exposure (Burghardt et al., The Treasury Bond Basis, 2005, ch.6).
- Holding-period return (Tuckman & Serrat, 2022): `(P1 + coupon - P0)/P0`; net of funding subtract `P0 x r x t`; return on capital divides by equity put up (50x leverage turns 0.27% into 13.27%).
  Decide the denominator (balance sheet vs capital) and say which.
- Time-weighted return with accrued interest (AFML ch.14, GIPS-style): `r_t = pi_t / K_t`, `pi_t = sum_j [(dP_j + A_j) theta_{j,t-1} + dtheta_j (P_j - Pbar_j)]`,
  `K_t = sum_j Ptilde_{j,t-1} theta_{j,t-1} + max(0, sum_j Ptildebar_j dtheta_j)` (P clean, Ptilde dirty, A accrued/coupon per unit, bar = average transacted). Coupons are not external flows.
  Link `phi_T = prod(1 + r_t)`, annualise `phi_T^{1/years} - 1`; include liquidation cost of the terminal position; also report longs-only P&L.
- Geometric mean for compounding history (GM <= AM); be consistent between log, geometric and arithmetic.

## 2. Swap spread (cash bond vs swap)
- Buy the on-the-run 10y and pay fixed on a PVBP-weighted, on-market, maturity-matched swap; include carry from **both** legs (JPM, Androids, Nov 2017).
- Per-market spread convention must be stated: US swap minus Treasury yield; EGB asset-swap spread = bond yield minus swap. Position +1 = long the spread level.
  Details in [spread-swap-spreads-and-asw](../../spread-swap-spreads-and-asw/SKILL.md).

## 3. Interest rate swaps (outrights, curves, flies)
- P&L is entirely NPV change of the **aged** swap, with fixings in the curve for correct accrued coupons. Carry and roll-down are value metrics, not booked cash.
- Total return (Macrosynergy, IRS returns, 2018 data): price change + roll-down (shortening maturity) + fixed-vs-floating differential. Price + roll return ~ -(modified duration) x change in the fixed-leg yield of the aged swap for a
  fixed **payer**; the receiver has the opposite sign. Returns in bp or % of notional; carry = fixed-floating spread plus curve roll-down.
- In-sample reference: 5y receivers, 2000-Feb 2018, average monthly return 19 bp of notional (~2.3% p.a.), average monthly SD 126 bp across the sample (45 for CHF to 273 for BRL), average excess kurtosis 2.6.
  An 11-day-half-life EWMA vol target with monthly rebalance raised excess kurtosis from 2.4 to 2.9.
- Hedges: open a new ticket on the generic forward; do not edit notionals. Legs DV01-equal at entry, struck at market forwards. Rebalance by the move rule (SKILL.md section 5).
- Curve conventions: curve spread A-B = longer minus shorter; fly `2x5y - 2y - 10y`. Quoting `b - 0.5(f + k)` instead of `2b - f - k` halves belly DV01 (assert with a hand-computed package).
- Linked: [fi-carry-and-rolldown](../../fi-carry-and-rolldown/SKILL.md), [fi-risk-dv01-and-transforms](../../fi-risk-dv01-and-transforms/SKILL.md).

## 4. STIR futures
- `P&L = (dPrice / 0.01) x PV01 per contract` with price in index points (100 - rate), so +1 tick of 0.01 = 1 bp; long the contract profits when the implied rate falls. Store the entry price.
  Variation margin is cash: `VM = dir x dF/tick x tick_value x n`, `dir = +1` long the contract (a basis trade is short futures against long cash, so `dir = -1` on that leg).
- Package economics: for exchange-listed packs/bundles the package tick is independent of the number of legs; costs are per leg, round trip, on leg DV01, and swept x{0, 0.5, 1, 2}.
- Roll: a constant-rank series jumps at each roll (see SKILL.md section 7). Detect rolls from settlement ticks if no map exists: the ending contract's final settle (100 - compounded rate) is almost never on the tick grid (off-grid 18/18),
  the starting contract is on-grid (32/32). Check snap alignment: futures settle ~15:00 ET against a 17:00 NY snap.
- Listed vol units differ by product root (normal price vol for one root, lognormal for another; ratio 1e4 / ModDur_ctd). Never pool across roots. Constant-maturity listed vol is not tradeable (55.9% of observations fell outside the 30-90d window).
- Deep strips may not be maintained: depth >= 16 only on 1-53 dates/yr from 2023 in one study: check coverage before using deferred packs.
  See [stir-futures-rv](../../stir-futures-rv/SKILL.md) and [stir-convexity-adjustment](../../stir-convexity-adjustment/SKILL.md).

## 5. Bond futures and the basis
- Cash leg: dirty NPV mark; futures: variation margin; coupons; repo at (GC - specialness) ACT/360 on the dirty value.
- Long basis P&L = basis change + carry (worked example D in SKILL.md). Net basis (BNOC) shrinks into expiry: in 25 short-CTD-basis trades held to expiry (Jun 1998 - Jun 2004) BNOC fell in 23, average entry 6.7/32 and average kept 4.9/32 (Burghardt, ch.6). High win rate from short-option-like exposure is not edge.
- Hold-to-expiry trades must model delivery mechanics: last practical switch day = second-to-last business day; off-repo financing in the final days; positive carry -> deliver on the last day; inverted front end -> early delivery (especially 2y/5y).
- Rule-based simulations: 297 overlapping 'cases' (|OAB| > 3 ticks) were not independent; hedged average +4.9 ticks, SD 8.6, worst -16.7, best +29.2 (Burghardt, ch.7). Recommendations +6.9 ticks versus +3.3 net in real trades.
- Use synchronous cash and futures closes (a 14:00 Chicago close database was used for CBOT Treasuries).
  See [fut-bond-basis-and-implied-repo](../../fut-bond-basis-and-implied-repo/SKILL.md), [fut-ctd-switch-and-delivery-options](../../fut-ctd-switch-and-delivery-options/SKILL.md).

## 6. Options (ATM straddle tickets)
- Normal (Bachelier) model, `d = (F - K)/(sigma sqrt(tau))`: straddle value `(F-K)(2 Phi(d) - 1) + 2 sigma sqrt(tau) phi(d)`; delta `2 Phi(d) - 1`; gamma `2 phi(d)/(sigma sqrt(tau))`; vega `2 sqrt(tau) phi(d)`; theta `-sigma phi(d)/sqrt(tau)`; each scaled by the annuity.
  ATM: premium `= 2 sigma sqrt(tau) phi(0) = 0.7979 sigma sqrt(tau)` per unit annuity. Vol at tau: linear interpolation in total variance `w = sigma^2 tau`, flat extrapolation.
- Delta-hedge on the same move threshold as the curve leg (re-hedge when |net delta| >= |Gamma| x 25 bp). At ~90 bp vol a 1M straddle held ~10 business days sees an ~18 bp 1-sd move (`90 x sqrt(10/252)`), so with a 25 bp threshold the option leg is rarely hedged: intended.
  Re-match gamma when `|Gamma_opt/Gamma_curve - 1| > 0.25`; roll at `0.5 x tau0`.
- Short-gamma book (Citi, The art of gamma hedging, 12 Mar 2018): sell the same notional every day, hold each option to expiry (~21 live options for 1m, ~63 for 3m); variants: hedge daily at the close / hedge only when the average portfolio delta deviates >= 25% / unhedged.
  Without rolling, higher-order Greeks turn the position directional; daily unwind-and-restart is wiped out by costs (a 0.2 vol-point bid/offer per leg kills a skew-arbitrage P&L) (QF Stack Exchange, Bergomi skew arbitrage).
- Straddle recipes (JPM, Androids, 2017): no delta hedge; a 1-week hold uses the change in premium; hold-to-expiry uses payoff minus premium. Systematic delta-hedged swaption straddles are valued off the full vol grid, not a flat vol; premium funded; monthly ATMF re-entry
  (Nordea Markets, Bonds & bold, Nov 2021).
- Comparing carry with straddle premium overstates breakeven vol by sqrt(2); compare rates (carry per year vs theta per year) at matched gamma and horizon.
- Convexity is not identified daily: read convexity at trade level and linear factors daily; carry/slope and level/convexity are collinear at trade horizon (use incremental R^2).
  See [vol-gamma-vega-pnl](../../vol-gamma-vega-pnl/SKILL.md), [vol-convexity-and-long-end](../../vol-convexity-and-long-end/SKILL.md).

## 7. Inflation-linked bonds
- Quoted linker yields/breakevens misstate realised performance because index carry (seasonal plus unpredictable) is volatile, most for short-dated linkers. Build carry-adjusted real-yield and breakeven series.
  Example (BofA, Global inflation-linked primer, 22 Jul 2025): in 2024 the quoted real yield of a UK linker rose, yet a long did well on carry; the carry-adjusted breakeven gained nearly 900 bp while the observed breakeven fell.
  See [infl-breakevens-and-linkers](../../infl-breakevens-and-linkers/SKILL.md).

## 8. Cross-market and spread carry with per-leg financing
- Long bond + duration-weighted short of another, each leg financed in its own currency (currency-hedged): `carry = (y_long - cash) - (D_long/D_short)(y_short - cash)`, slide omitted. Risk = 12-month rolling annualised std of non-overlapping monthly returns of the combined spread (JPM, Exploiting carry, 11 Jan 2007).
- Returns are quoted in excess of cash (3m bills), FX-hedged for cross-currency legs, cross-market legs vol-matched (long JGB / short UST futures) (Willer & Saunders, 2026).
- Long-short hit ratio = share of periods with a positive combined return; 'long signals above funding' = number of longs whose period change beats the equal-weighted basket of shorts (BofA, FX Quant Primer, 1 Oct 2018). Hit rates there are gross, hypothetical and tied to a specific weekly close: state all three.

## 9. Event-driven engine shape (any product)
Step loop over the time grid: (1) triggers produce actions -> orders (open by structure query, or unwind by selector/tag); (2) execute; (3) resolve each open order into concrete instruments and **freeze them**; (4) unwind; (5) mark to market = realised + sum of position values,
with a per-position hook that can return a new position, a realised delta, and injected triggers. Keep histories: MTM, realised P&L, positions, and a closed-position log (opened_at, closed_at, holding period in steps and days, realised and gross P&L, fee allocated, snapshot, metadata).
A naive engine fills immediately, with no slippage or partial fills; a flat fee charged at unwind only must charge the **full round trip** there. Trigger types worth supporting: periodic, date, market-condition, risk, mean-reversion, trade count, event, roll.
Write per-day as completed; never consolidate an incomplete panel; one file per configuration with a content-addressed id so sweeps are resumable.

## 10. Sample-start and market notes (G10)
| Market | Note |
|---|---|
| USD | OTR 10y/30y auction second week, issue on the 15th; new issues Feb/May/Aug/Nov refunding; 2y/5y/7y issue month-end; 20y next-to-last Wednesday (BofA, UST auction primer, 8 Mar 2024). Swap curve: one convexity study starts in 2004 because earlier curve quality was unsatisfactory; swap-spread volume, liquidity and data reliability were lower before the late 1990s |
| EUR | EGB supply: NL pre-announces a quarterly calendar (dilutes concession); IT redemption/coupon dates coincide with supply; hedge vs Bund with the beta-adjusted spread for best IR (JPM, Follow the cash flow, 15 Sep 2015). Residual models: FI and IE excluded, 25y instead of 30y for data availability (BofA, Many EGBs, 21 Mar 2018) |
| GBP | Linker index carry; gilts trade cheap on average vs other futures baskets; ex-dividend rules remove CTDs mid-month; negative accrued in ex-div periods |
| JPY | 2-day lag against USD-timed legs; yield-curve control breaks carry/duration signals; JGB duration signals weak (IR ~0.3) but uncorrelated |
| CAD / AUD / NZD / CHF / SEK / NOK | Only cross-market statistics in the sources: DM IRS monthly correlations mostly 0.5-0.8 (EUR-GBP/CHF/SEK 0.8, CAD-USD 0.8, AUD-NZD 0.8); 5y spreads (SEK/NOK, AUD/NZD, CAD/US) at a 1,000-day extreme are an alert for reversal, not an entry rule. Use local calendars and own snaps |

Conventions per market: [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md).
