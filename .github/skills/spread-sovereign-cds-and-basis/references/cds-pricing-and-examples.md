# CDS pricing derivations and extended worked examples

Supporting detail for [the skill](../SKILL.md). Units: spreads in bp, prices per 100, hazard rates as decimals.

## 1. Flat-hazard CDS pricing (market upfront convention)

Survival `S(t) = e^(−λt)`. Default probability in period i is `S_{i−1} − S_i`. Default accrual is paid at half
the period.

```
fee leg (spread s, % per yr)  = s · Σ DF_i · Δt_i · [ S_i + ½ (S_{i−1} − S_i) ]  = s · RPV01
contingent leg (per 100)      = 100 (1 − R) · Σ DF_i · (S_{i−1} − S_i)
par spread                    : fee leg = contingent leg  →  solve λ
upfront (per 100, + = buyer pays) = RPV01 · (s − coupon) = fee leg · (1 − coupon/s)
```

The upfront quote is "only a convention, like ... price and yield-to-maturity" (Tuckman & Serrat, 2022).
Recovery conventions: 40% for most contracts, 25% for European emerging markets, 20% for North American
subordinated. G10 sovereigns use 40%.

**Textbook case** (Tuckman & Serrat, Fixed Income Securities 4th ed., Table 14.10; 5y, annual pay for simplicity,
16 Aug 2021). Spread 558.92bp, coupon 500bp, R = 40%:

| Year | DF | Cumulative survival % | Default prob. % |
|---|---|---|---|
| 1 | 0.998462 | 91.099 | 8.901 |
| 2 | 0.994257 | 82.991 | 8.109 |
| 3 | 0.985062 | 75.604 | 7.387 |
| 4 | 0.973167 | 68.875 | 6.729 |
| 5 | 0.959797 | 62.744 | 6.130 |

- λ = 9.322%.
- Year-1 fee: `0.998462 × [91.099% × 5.5892 + 8.901% × 2.7946] = 5.332`.
- Year-3 contingent: `0.985062 × 7.387% × 60 = 4.366`.
- Both legs total 21.995. The fee leg at the 5% coupon is 21.995 × 5/5.5892 = 19.676, so the **upfront = 2.319 per
  100**, i.e. $23,190 per $1mm.
- At a spread of 450bp: λ = 7.504%, legs 18.462, upfront −2.051 (the buyer receives).
- Mark-to-market: if the upfront falls to $13,000 per $1mm a month later, the buyer loses $10,190.

`scripts/sov_cds_basis.py --selftest` reproduces every number above.

## 2. CDS-equivalent bond spread

Solve the λ that reprices the bond with par recovery, then report the par CDS spread at that λ (Tuckman & Serrat,
Table 14.11).

A 5y 5% annual bond at **94.561** gives λ = 9.322%, so its CDS-equivalent spread is **558.92bp**. Price components:

| Component | Value |
|---|---|
| Coupons | 19.676 = survival part 18.760 + default-period half coupons 0.916 |
| Recovery | 14.663 |
| Principal on survival | 0.959797 × 62.744% × 100 = 60.222 |
| **Total** | **94.561** |

Approximations:
- `s_CDS ≈ λ(1 − R)`: 9.322% × 0.6 = 559.3bp, against 558.92 exact.
- A bond spread behaves like `λ(1 − R_m)`, with recovery as a fraction of **market** value.

The two measures diverge on discount bonds:

| λ | Bond price | CDS | Bond spread |
|---|---|---|---|
| 9.322% | 94.561 | 559bp | 551bp |
| 16.70% | 80.688 | 1,000bp | 932bp |

Par recovery is the better-supported assumption, so prefer the CDS-equivalent spread when prices are well below par.

## 3. Local-currency (quanto) CDS and the implied FX move on default

The FX component (Huggins & Schaller, Fixed Income Relative Value Analysis 2nd ed., 2024, Ch.13):
- Buy USD-denominated and sell local-currency CDS on the same sovereign, same maturity.
- On default, deliver the bond against USD at the pre-agreed FX rate. If the local currency then falls by a
  fraction d, the package pays `d × (1 − R)` per USD notional. With JPY going from 80 to 160, d = 50%, so it pays
  $50 per $100.
- Fair pricing makes the local quote about the USD quote scaled by the post-default value of the currency:

```
s_local ≈ s_USD × (1 − d)      →      d_implied = 1 − s_local / s_USD
```

- Observed local-currency quotes are 30–60% of USD quotes, i.e. d ≈ 40–70%, with a 55% midpoint.
- The authors also describe a delta-hedging view: if you scale a long-local / short-USD FX hedge as CDS rises, the
  FX component is worth more the more volatile the CDS. Their preliminary model makes this a major driver in
  high-volatility CDS markets, e.g. Portugal in the euro crisis.
- Even the sign is uncertain for some issuers: Japan could see JPY strengthen on repatriation. Treat `d` as a
  scenario input, never a point estimate.

## 4. Jump-to-default-neutral hedge

A bond bought at dirty price P (per 100) loses `P/100 − R` per unit face on default. CDS pays `1 − R` per unit
notional. So:

```
N_CDS = Face × (P/100 − R) / (1 − R)
```

| Price | R | Notional per 100 face |
|---|---|---|
| 100 | any | 100 |
| 80 | 40% | 66.7 |

A premium bond needs more than face. This sizing ignores the post-default ASW and CCBS legs (see the SKILL.md
default checklist).

## 5. USD ASW of a non-USD bond

Cash flows (Huggins & Schaller, Ch.16, par bonds):
- The asset-swapped bond pays `local index + ASW_local`.
- In the CCBS you pay `local index + CCBS` and receive SOFR.
- The residual `ASW_local − CCBS` is a running spread in local currency.
- Converting at equal PV, `x · BPV_local = y · BPV_USD`, gives

```
USD ASW = (ASW_local + ICBS − CCBS) / CF,     CF = BPV_USD / BPV_local
```

**Worked case, 23 Sep 2012 (LIBOR era):**
- 10Y JGB 6M ASW = −1bp. Add the 3M/6M ICBS of 12 to get 11bp.
- CCBS = −64.5, CF = 0.95 (10Y USD swap BPV / 10Y JPY swap BPV).
- USD ASW = 75.5/0.95 = **79bp over USD LIBOR**.

Combined with the inequality: `CDS ≥ adjusted CDS ≈ USD ASW = ASW_local/CF − CCBS/CF`.

Risk ladder (Table 16.1). Each swap removes one risk:

| Position | Yield risk | FX risk | Default risk |
|---|---|---|---|
| Bond | yes | yes | yes |
| + asset swap | no (conceptually) | yes | yes |
| + basis swap | no | no | yes |
| + CDS | no | no | no |

## 6. Extended cases (all Huggins & Schaller 2024 unless stated; "chart-read" = approximate)

**JGB USD ASW vs Japan CDS ask (23 Sep 2012, chart-read).**
- The CDS ask rises from about 17bp at 1Y to about 120 at 7Y and about 130 at 10Y. The JGB USD ASW rises from about
  15 at 1Y to 79 at 10Y.
- Up to about 2–2.5Y the JGBs sit on the CDS ask, so credit is fully priced there. The 1–2Y USD ASW should not widen
  unless Japan CDS rises.
- A 2Y JGB + 2Y CDS at zero basis gives the DO and the JPY-falls-on-default exposure for free.
- Under 1Y, USD ASW > CDS can appear but may reflect redemption flows.

**Korea 5.75% 09/18 vs 10Y Korea CDS ask (Sep 2008 – Dec 2009, daily).**
- After Lehman, forced selling widened the KRW ASW, and Korean banks' USD demand pushed the KRW CCBS deeply
  negative. The CDS moved on a different timing.
- The USD ASW exceeded CDS by more than 100bp at times. Annotated episodes (chart-read):

| Profit | Period |
|---|---|
| 130bp | 1 week |
| 68bp | 1 week |
| 49bp | 3 days |
| 132bp | 3 weeks |
| 71bp | 8 weeks |
| 25bp | 3 days |

- In quiet times violations are rare and small.

**USD SOFR spreads of basis-swapped govies (17 Oct 2023, chart-read, bp over SOFR).**

| Issuer | 1Y | 5Y | 10Y | 15Y | 20Y | 25Y |
|---|---|---|---|---|---|---|
| Bunds | −21 | −24 | −22 | −12 | −3 | +3 |
| USTs | +1 | +25 | +29 | +41 | +64 | +65 |
| Gilts | −31 | −5 | +35 | +63 | +84 | +95 |

- All three curves slope up, as CDS curves and haircut schedules do. The 5Y order (Bunds < gilts < USTs) matches
  the 5Y CDS order qualitatively.
- Long Bunds look richer than CDS plus haircuts justify, which led to a trade idea: sell long Bunds against
  USTs or gilts, all on SOFR ASW. It works only if the imbalance is judged ephemeral.

**Swap-spread fair value from CDS (Ch.12).**
- 10Y Bund ESTR-ASW fair value: −16bp (unsecured-secured capital basis) + 15bp (adjusted 10Y German CDS) − 6bp
  (average specialness) = **−7bp**.
- 5Y UST SOFR-ASW (mid-month, Jan 2021 – Sep 2023): adjusted CDS + specialness alone under-predicts. Adding a haircut
  cost of 2% haircut × 5% funding spread = 10bp fits. Run in reverse, the implied haircut cost was 8bp in Sep 2023.
  In early 2022 the ASW sat about 10bp above the model during a sharp sell-off, which the authors read as flow,
  not model failure.

**Risk-free BTP PCA (weekly, Jan 2006 – Aug 2012).** Correlation of PC1 with each point (Table 13.1):

| Tenor | BTP | BTP − adjusted CDS |
|---|---|---|
| 2Y | 0.95 | 0.99 |
| 5Y | 0.98 | 1.00 |
| 10Y | 0.79 | 0.96 |

In the risk-free PCA, PC2 mean-reverts faster and is no longer correlated with PC1 after 2010. The same effect,
smaller, shows in USTs and JGBs.

**Sovereign 5y CDS, Nov 2021** (Tuckman & Serrat, Table 14.9), bp:

| Germany | United States | Spain | China | Italy | Greece | Brazil | Turkey |
|---|---|---|---|---|---|---|---|
| 9.1 | 16.0 | 35.2 | 48.9 | 89.6 | 112.3 | 265.8 | 469.6 |

**Auction settlement** (Tuckman & Serrat, 14.11):
- Cash settlement pays `notional × (100 − final price)`. Final price 26.375 paid buyers 73.625%.
- Auctions can fail on a technicality. In one 2021 corporate auction, phase-2 sell interest fell short of the net
  open interest, so the final price was set to 100 and protection buyers received nothing.
- Check the deliverable set and the auction rules for any default-scenario P&L.
