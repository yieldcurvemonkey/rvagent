# Worked examples and reference numbers

Extra numbers behind [SKILL.md](../SKILL.md). Every block is a published case: use them to unit-test your own
implementation (the first three are asserted in `scripts/basis.py --selftest`). Prices are decimal; "ticks" are 1/32.

## A. Full cash-and-carry walk, no intervening coupon (Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005, Ch. 1)

Bond 7-1/4% 15-Aug-2022, clean 119.875, settle 6-Apr-2001, delivery 29-Jun-2001 (84 days), futures 103.9375, CF 1.1481, repo 4.54% ACT/360.

| Step | Value |
|---|---|
| Accrued at settle (50 days of 181) | 1.0014; dirty (purchase) 120.8764 |
| Accrued at delivery (134 of 181) | 2.683702 |
| Invoice = 103.9375 x 1.1481 + 2.683702 | 122.014346 |
| Coupon income 3.625 x 84/181 | 1.68232 |
| Financing 120.8764 x 4.54% x 84/360 | 1.280484 |
| Carry | 0.401836 per 100 = USD 4,018 per USD 1mm = 12.9 ticks |
| IRR = (122.014346 / 120.8764 - 1) x 360/84 | 4.03% |

Gross basis of the 7-1/2% 15-Nov-2016 (CF 1.1484, cash 120-20, F 103-30): 120.625 - 103.9375 x 1.1484 = 1.2632 = 40.4 ticks.

With one intervening coupon `C/2` paid `n2` days before delivery, the same repo identity gives
`IRR = (Invoice + C/2 - Purchase) x 360 / (Purchase x n - C/2 x n2)`.

## B. Net basis and the IRR convention trap (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022, Ch. 11)

Sep-2021 10y future on 14-May-2021: F = 131-17+ (131.546875), repo 0.015%, 136 days to 30-Sep-2021. CTD 2.875% 15-May-2028, CF 0.8338, clean 110.77344.

- Forward: full spot 110.78906 x (1 + 0.015% x 136/360) = 110.79534; less accrued at delivery 1.07813 gives clean forward 109.71721.
- Gross basis 110.77344 - 0.8338 x 131.546875 = 1.0896 (34.9 ticks). Net basis 109.71721 - 109.68379 = 0.0334 (1.1 ticks). Carry 1.057 (33.8 ticks).
- IRR = -0.065% from `109.68379 + 1.07813 = 110.78906 (1 + r x 136/360)`. That is below the 0.015% repo, so the future is "cheap", but only
  by the 1.1 tick net basis: had the future traded at forward / CF the IRR would equal the repo.
- Rest of the basket (net basis in ticks): 2.875% Aug-28 24.8, 1.25% Apr-28 33.4, 3.125% Nov-28 43.6, 2.625% Feb-29 76.3, 2.375% May-29 104.8,
  1.625% Aug-29 144.9, 1.5% Feb-30 186.6, 0.625% Aug-30 242.9, 1.125% Feb-31 274.4. Net basis rises with distance from the CTD: the
  long end of the basket is far out of the money. "Sell the 2.875% Aug-28 basis at 24.8 ticks" is a bet it becomes CTD, not a carry trade.
- Package size: USD 100mm face = 834 contracts at 0.8338 CF.

## C. Same bond, four IRRs (Quantitative Finance Stack Exchange, "Ten Year Note Futures Implied Repo Rate calculation...", Jul 2022; CME Group, Understanding Treasury Futures, Nov 2017)

Dec-2017 10y future 125.265625, CTD 2.375% Aug-2024, CF 0.8072, clean 101.2266. CME's published table shows IRR 1.42% for the CTD.
Re-deriving it: n = 79 days gives 1.7837%; settlement 10-Oct-2017 with 80 days to 29-Dec gives about 1.79%; delivery on the first delivery day
(52 days) gives about 1.52%. Conventions move IRR by up to about 40bp on a near-zero net basis. Print settle date, delivery date and day basis next to every IRR.
CME's IRR ladder on the same day: 2.375% Aug-24 1.42%, 2.125% Jul-24 0.68%, 1.875% Aug-24 0.32%, 2% Jun-24 0.18%, 2.25% Nov-24 -1.76%,
2.375% May-27 -28.23%, 2.25% Aug-27 -31.73%: IRR falls monotonically with maturity. Comparators: 13-week bill 1.04%, EFFR 1.15%, 3m LIBOR 1.34%.

Hedge ratios, USD 10mm 2.375% May-2027 (DV01 USD 8,558; CTD DV01 USD 63.78 per 100k, CF 0.8072): DV01 hedge `0.8072 x 8,558 / 63.78 = 108.3` contracts
versus 75 contracts by CF weighting (its own CF 0.7455). CF weighting is exact only for the CTD (CME, Nov 2017).

## D. Repo wedge created by a few ticks of option value (JPM, Special delivery, 4 Dec 2019)

`IRR = term repo - NB / dirty x 360 / n`. A net basis of 1 tick on a 100 bond is 18.8bp of repo at 60 days and 37.5bp at 30 days. In Dec 2019
the 10y, Ultra-10y and Bond futures showed 10-30bp of IRR/term-repo distortion; the Ultra-Bond future's implied repo "plunged" into the delivery month,
a 50-100bp gap versus CTD term repo from only a few ticks of net basis (wildcard about 3 ticks in WN, 0.5-1.5 elsewhere). Option-adjusted IRR = IRR + option value / dirty x 360 / n.

## E. Long basis as an option, and what it earned (Burghardt et al., 2005, Ch. 2 and 6)

Buy the 7-5/8% 15-Nov-2022 CTD basis at 18.09 ticks: carry 13.56, so 4.53 ticks are paid for options. Held to expiry the P&L is about -3 ticks at
unchanged yields, +7 at -60bp, +19.5 at +60bp. The mirror (short basis) earns at most about +3. Short CTD basis, 25 contracts (10y, sold 3 months out, held to expiry,
Jun-1998 to Jun-2004): BNOC fell in 23 of 25, average entry 6.7 ticks, average kept 4.9 ticks. The two losers were Mar-99 and Jun-01.
A 92% hit rate is the signature of selling out-of-the-money options, not of richness: stress with a selloff plus curve steepening.

Option-adjusted basis (OAB = BNOC - theoretical delivery-option value) on 4-Apr-2001: every deliverable was between -3.0 and -4.5 ticks, CTD basis
18.1 = carry 13.6 + BNOC 4.5, theoretical DOV 8.0, so OAB -3.5 and the future was 3.5/1.1936 = 2.93 ticks rich.

## F. Leveraged long basis through March 2020 (Tuckman and Serrat, 2022, Ch. 11)

10-Feb-2020: USD 1bn long Jun-2020 10y basis at -4.0 ticks earns (4/32)% x 1bn = USD 1.25mm if net basis goes to 0. Capital 50mm (20:1) gives 2.5% over 141 days,
about 6.5% annualised; 40:1 gives about 13%. Opened 6-Mar at -8.33 with a tailed hedge `10,000 x 0.8006 / (1 + 1.10% x 116/360) = 7,978` contracts.

| Date | Net basis (ticks) | Daily P&L (USD) | Cum P&L | Margin per contract | Margin call | Cumulative cash |
|---|---|---|---|---|---|---|
| 6-Mar | -8.33 | | | 1,275 | | -10,171,597 |
| 9-Mar | -18.48 | -3,172,148 | -3,172,148 | 1,375 | -797,772 | -14,141,517 |
| 10-Mar | -11.22 | +2,268,613 | -903,535 | 1,375 | 0 | -11,872,904 |
| 11-Mar | -5.70 | +1,725,636 | +822,101 | 1,600 | -1,794,988 | -11,942,256 |
| 12-Mar | -0.47 | +1,633,228 | +2,455,330 | 1,600 | 0 | -10,309,028 |

The position finished +2.5mm but needed about USD 4mm of cash in one day (loss plus margin), enough to force an exit at the worst point.
The 99th-percentile repo-minus-SOFR was 10-11bp in Feb 2020, 20-50bp on several March days and peaked at 174bp on 16-Mar-2020.

## G. Quarter-roll cross-section of a modern USD basis (JPM, Rollover Outlook, 12 Aug 2026; JPM data pack, 28 Oct 2026)

close of business 11-Aug-2026, front/back contract: WN gross basis 5.8/11.1, BNOC 2.0/1.6, switch option 0.8/3.8, IRP (implied repo) 3.14%/3.70%, CTD repo 3.69/3.86;
US gross 7.8/18.7, BNOC 2.3/4.4, option 4.6/14.8; UXY BNOC 0.3/0.2; TY BNOC 0.0/0.4; FV gross -0.3/-2.5 (negative carry); TU BNOC -0.1/-0.1.
Carry to optimal delivery (ticks): TU 1.6, FV -0.3 (first day), TY 2.3, UXY 2.2, US 5.5, WN 3.8. Funding sensitivity of a calendar:
change in calendar spread = -(change in funding)/4 for a parallel move (+25bp lowers it 0.0625 pts = 2/32).
Term repo to delivery on 28-Oct-2026: Dec-26 4.0028%, Mar-27 4.2051%, Jun-27 4.3716%. Price vols: US Z 11.68%, TY Z 6.14%, UXY Z 7.68%, FV Z 4.35%, TU Z 1.91%.
A long-basis mark: USD 100mn 4.625% Nov-2044 bought versus 851 Dec-2026 Bond futures (notional/100k x CF 0.851), gross basis 16/32, term repo 3.87% to 31-Dec-2026, net about 2/32;
later marked +2.1/32 and +1.0/32 (JPM, Born(e) in the US(A), 31 Jul 2026; JPM Global Fixed Income Markets Weekly, 21-22 Aug 2026).
Convexity cross-check: long 5% May-45s versus a CF-weighted short Dec-2026 Bond future at 3.95% term repo: gross 17.02, net 5.52 ticks; Nov-43 net about 8.7 ticks
versus a replicated convexity value of 12.4 ticks, about 30% cheap (Morgan Stanley, Buy Higher Rates Protection at a 30% Discount, 27 Aug 2026).

## H. Eurex-style basis sheet (Düring, Fixed Income Trading and Risk Management, 2021, Table 28.1; fictitious, 14-Apr-2020)

Future 106.573, fair 106.553, quality option 0.2c, notional 6%, delivery 10-Jun, repo 2.00% flat.

| Bond | Price | Yield | CF | Converted forward price (CFP) | Net basis (cents) |
|---|---|---|---|---|---|
| 4.875% Jan-29 | 99.446 | 4.950 | 0.925874 | 106.946 | 36.3 |
| 5% Jul-29 | 99.904 | 5.010 | 0.931507 | 106.781 | 21.1 |
| 5% Jan-30 (CTD) | 99.363 | 5.080 | 0.928327 | 106.554 | 0.0 |
| 5.125% Jul-30 | 100.249 | 5.090 | 0.935186 | 106.711 | 14.6 |

CFP spans 106.554-106.946 while spot prices span 99.363-100.249: CFs equalise prices only partly. The CTD has the lowest CFP, which is the future's fair value.
Schatz walk, 11-Jan-2012 (Aikin, STIR Futures, 2nd ed., 2012): CTD 0.25% Dec-13 clean 100.205, repo 1.07%, 56 days, financing 0.1669, accrued earned 0.0387, carry cost 0.1282, gross 0.0822, net basis 0.2104.
"Most cash-and-carry trades will result in a loss": the small CTD net basis is the price of embedded optionality.

## I. Synthetic asset replacement, numbers

- Over 48 quarters (TYU2005-TYM2017) long 10y futures plus cash at overnight rates returned 4.85%/yr versus 4.71% for holding the CTD: +14bp/yr (CME, Nov 2017).
- Replace the 10y CTD with futures and GC-repo cash three months before expiry, Jun-1998 to Jun-2004: 25 contracts, 2 negative (Mar-99 -19.6bp, Jun-01 -38.9bp),
  average 5.2 ticks = 62.3bp annualised; the 3-month BNOC tracked the outperformance (Burghardt et al., 2005, Ch. 10). Single case 20-Sep to 18-Dec-2001 (89 days):
  sell USD 100mm 6-1/2% Feb-2010 CTD and USD 100mm 5% Aug-2011, invest the USD 215,581,500 at 2% term repo, buy 999 + 1,073 = 2,072 futures at OA DV01 USD 73.84:
  portfolio -4.87% versus -6.36% held, 149bp annualised.
- Special-repo version: a 2y at 4.21% financed at the contract's implied (special) repo 3.79% (GC 4.56%): `0.42% x 4.8 = 2.02%`, plus bills 4.39%, gives 6.41%/yr (1.60% per 90 days); recompute at each roll (Convexity Maven, Leverage is NOT a four-letter Word, 26 Jan 2023).
- Target duration: USD 1bn at modified duration 3.0 to 2.0 with 5y futures (PEV USD 105,687.50, duration 4.09): `N = -1.00% x 1bn / (4.09% x 105,687.50) = -2,313` (Burghardt et al., 2005, Ch. 10).
- Asset-manager substitutions, 5% allocations: floating CLO via sell UST + buy futures 4.8% adds 0.12% to fund yield; 1y ABS with sell 2y future adds 0.11%; high yield with a -2.1% futures hedge adds 0.17% (Treasury Borrowing Advisory Committee, Treasury Futures Positions Across Investor Types, 30 Jan 2024).
