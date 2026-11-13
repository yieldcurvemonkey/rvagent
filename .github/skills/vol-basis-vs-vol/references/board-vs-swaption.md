# Board (Treasury futures options) vs CTD-matched swaption: method, history, conditional spreads

Detail behind step 5 of [SKILL.md](../SKILL.md). Generic listed-vs-OTC hygiene:
[vol-rates-options-rv](../../vol-rates-options-rv/SKILL.md). Inputs: `opt_quotes`, `opt_static`, `fut_quotes`, `vol_surface`,
`swap_spreads` (see [data-contract-and-adapters](../../data-contract-and-adapters/SKILL.md)).

## 1. Series construction (repeated across the Citi monitor, 2015-2026)
1. Interpolated ATM Board vol on the second available expiry; roll when the front expires (expiry-effect noise).
2. CTD-matched swaption: same expiry, tail duration-matched to the CTD at expiry. Default tails when no CTD map is at hand (starting point only):
   2y note to 2y, 5y to 5y, 10y note (TY) to 7y, Ultra-10 / TN to 10y, bond to 20y, Ultra bond to 30y.
3. Each leg against its own 1m and 3m realised vol (yield bp). Plot: Board/swaption ratio, and futures/swap realised ratio (1m, 3m).
4. Strike map: swaption strike = Board strike yield + invoice spread. Compare skew strike by strike. Premium difference as running yield (premium / option DV01).
5. Richness test: Board is rich when implied ratio exceeds realised ratio (Citi Research, Rates Vol Lab, 12 Dec 2016; 1 May 2017; 25 Sep 2019; 14 Sep 2026).

## 2. Observed ratios (ATM, Board/swaption)
| Date | Ratios | Reading |
|---|---|---|
| Dec 2016 | FVG7 1.04, FVH7 1.08, TYG7 1.06, TYH7 1.10, USG7 0.97, USH7 1.00 | bond contracts at or below parity |
| Jan-May 2017 | TYH7 87.4 vs 81.8 (1.07), TYM7 1.05, FVM7 69.3 vs 64.7 (1.07), USM7 0.93; realised 0.97 (1m) / 1.02 (3m) | TY/FV rich vs realised, US cheap |
| Jan 2018 | USH8 1.03 | source calls US Board cheap to swaptions (read against its realised ratio) |
| 16 May 2019 | TYQ9 60.5 vs 62.4 (0.97; 1.02 a week earlier), TYN9 0.95, USN9 0.91, FVQ9 0.97; Board/1m realised TY 1.03-1.05; futures/swap realised TY 1.03 (1m), FV/US 0.97 | Board cheap; drivers below, episodes short-lived |
| Sep 2019 | FVX9 1.00, TYX9 0.95, USX9 0.90; US realised 0.92 | US Board discount in line with realised |
| 27 Mar 2020 | FVK0 67.1 vs 77.8 (0.86), USK0 106.9 vs 120.5 (0.89), TYK0 96.7 vs 95.1 (1.02); a week earlier TY, US 1.22-1.24; Board/3m realised 0.59-0.71 | stress: Board went from rich (1.22-1.24) to cheap (0.86-0.89) in a week |
| Sep-Oct 2026 | FVX6 1.03, TYX6 1.06, USX6 1.07, USZ6 1.08; Board 127.1 / 122.0 / 105.5; Board/3m realised 1.57-1.73; US 1m futures/swap realised 1.37 | implied ratio still below realised |

Sources: Citi Research, US Rates Vol Lab (12 Dec 2016; 17 Jan 2017; 1 May 2017; 8 Jan 2018; 25 Sep 2019), US Rates Weekly (17 May 2019), Rates Vol Lab (30 Mar 2020; 14 Sep 2026; 5 Oct 2026).

## 3. Reading the ratio
- Compare with the realised ratio, not with 1.0: a ratio below 1 is only cheap if realised futures/swap vol is not also below 1 (May 2019: implied TY 0.97 vs realised 1.03).
- A rally tightens swap spreads and raises swap realised vol relative to futures, which cheapens Board. Mortgage prepayment demand for swaption gamma richens swaptions. Both are seen as temporary (Citi, 17 May 2019).
- Directional read: Board puts trade above swaption payers and Board calls below swaption receivers: Board put skew rich to payer skew, call skew cheap to receiver skew; US call skew cheap to receiver skew in 2016-2017, FV and TY put skew rich to payer skew in 2018-2019. An FV 1x2 call spread 118.75/119.25 ("monetize call skew") traded at 1 to 1.5 ticks after vol cheapened (Citi, 1 May 2017).
- Futures-specific flows cause spikes in futures-option vol, and a post-Lehman regime removed the pre-crisis swaption premium to futures vol (Huggins and Schaller, Fixed Income Relative Value Analysis, 2024, Fig 19.12: weekly 11 May 2005 to 3 Oct 2012, 3M swaption vs futures option vol).
- If pre-crisis swap-spread directionality returns (spreads widening in sell-offs), the conditional is long swaption vs short bond option: payers vs bond puts, receivers vs bond calls.

## 4. Conditional spread (DV01-neutral)
Structure: futures put (call) vs payer (receiver) swaption, expiries matched, swaption notional per 1000 Board contracts, swaption strike solved so the package costs zero (costless strike).
- Notional: `1000 x $100k x fut DV01 / swap DV01`. TY 7.53/6.26 gives $120.3mn (printed $120.3mn). FV 4.77/4.01 gives $119.0mn (printed $119.1mn). DV01s share a unit; only the ratio matters.
- Pick-up (bp) as printed: `invoice spread - costless strike spread` = how far the costless strike sits below the invoice-mapped strike. The source prose says "costless strike spread minus invoice spread", which contradicts its own rows. Recompute.
- Reading (derived from the strikes, not stated by the source): a lower costless payer strike is a more valuable payer, so positive pick-up for puts vs payers = Board put rich; a lower costless receiver strike is a less valuable receiver, so positive pick-up for calls vs receivers = Board call cheap. Check against the printed vol ratios: FVK8 +0.8 (1.03), TYX6 +2.6 (1.05), TYM3 -5.2 (0.96), USX9 calls +2.3 to +5.7 (call/receiver 0.87-0.90: calls cheap). FVM3 (-5.4 with ratio about 1.00) breaks the pattern: treat the table as a screen and verify with vols.

| Contract (date) | Board strike | Costless swaption strike | Strike spread / invoice (bp) | Pick-up | Put vol / payer vol |
|---|---|---|---|---|---|
| FVK8 (12 Mar 2018) | 113.75 put, 2.74% | payer 2.85% | 10.8 / 11.6 | +0.8 | 66.0 / 64.0 (1.03) |
| TYX6 (5 Oct 2026) | 104.00 put, expiry 23 Oct 2026, fut 104-11+ | payer, spread -41.0 | -41.0 / -38.4 | +2.6 | 122.6 / 116.5 (1.05) |
| TYM3 (12 Jun 2023) | 114.00 put, 3.68% | payer 3.43% | -24.6 / -29.8 | -5.2 | 121.8 / 127.5 (0.96) |
| FVM3 (12 Jun 2023) | 109.00 put, 3.76% | payer 3.56% | -19.6 / -25.0 | -5.4 | 142.8 / 142.5 (fut DV01 4.22, swap 3.84) |
| USX9 (25 Sep 2019) calls vs receivers | strikes 164-169 | | | +2.3 to +5.7 | call/receiver 0.87-0.90 |

Also: TYH7 (124-20+): invoice -12.6, fut DV01 7.53, swap 6.26. FVM7 (expiry 26 May 2017): fut 118-13, invoice +11.9. Swap bid/offer for backtests: 0.3bp (2017-18), 0.4bp (2013-16), 1.2bp (2008-09); historical swaption bid/offer is not firm.

## 5. Unit conversions and checks
- Board vol in normal yield bp: `price vol (pts) / futures DV01 (pts per bp)`; lognormal price vol: `sigma_ln x F` first. Validate the Board vol by repricing one option with the stated vol; reject if the check fails.
- Annual to daily normal vol: divide by `sqrt(252)` (148.8 gives 9.4 per day).
- Compare like expiries: swaption expiry equals the option expiry, not the futures last trading day.
- Hedge: DV01-neutral using spot DV01 of cash vs forward DV01 of futures when one leg is the basis (Citi, US Rates Weekly, 17 Jul 2015).
