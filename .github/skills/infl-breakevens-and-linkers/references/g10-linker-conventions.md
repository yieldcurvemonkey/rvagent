# G10 linker and inflation-swap conventions

Reference for [SKILL.md](../SKILL.md). Conventions drift (reforms, rebasings, new issuance rules): confirm every row
against the issuer term sheet and the CSA/ISDA confirmation, and prefer the values in `bond_static` / `swap_conventions`
(see [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md)) over this table. "Standard lag" = 3 months
with daily interpolation (reference value formula in SKILL.md, step 1).

## Cash linkers

| Market | Linker and index | Lag / interpolation | Principal floor | Quoted as | Notes |
|---|---|---|---|---|---|
| USD | TIPS, CPI-U NSA | standard (3m, interpolated) | yes (par at redemption) | real price | 5/10/30y. Issue months Jan/Feb, Apr, Jul give three seasonal cycles. As of Jan 2022: 5y issued semiannually and reopened 2 months later; 10y semiannual, reopened every 2 months; 30y annual, reopened semiannually. Floor worth most on recent issues (accreted principal near par). |
| EUR (FR) | OAT€i (euro HICPxT) and OATi (French CPI ex tobacco) | standard | yes | real price | France is the benchmark and allocates opportunistically between the two indices. French CPI has grown slightly slower than euro HICP long term. 3rd-Thursday auctions. |
| EUR (IT) | BTP€i (HICPxT) | standard | yes | real price | BTP Italia is a different animal: interest-indexed (pay-as-you-go), principal at par. |
| EUR (DE) | DBRi (HICPxT); OBLi discontinued | standard | yes | real price | Issuance ceased (BofA primer, 2025). Tuesday auctions when active. Seasonally adjusted German BE traded very close to French BE. |
| EUR (ES) | SPGBei (HICPxT) | standard | yes | real price | |
| GBP | index-linked gilts, RPI | 3m for issues from Apr 2005, daily interpolation; two older issues keep an 8m lag (quoted on adjusted price) | no | real price | Semi-annual coupons, 7-day ex-dividend. Use the DMO yield formulae for settlement. RPI reform in 2030 is visible as a step in forward real yields. RPI-CPI wedge 0.7-1.0% (median 0.8%) and it has a beta to the inflation level. |
| JPY | JGBi, CPI ex fresh food | "modified standard": the 10th of the month takes the index from 3 months prior (not the 1st) | yes on series from 2013 (earlier series had no par floor) | real price | Indexation coefficient = reference index on the day / reference index at the 10th of the issue month. Issuance halted Oct 2008, restarted Oct 2013, quarterly. Five-yearly CPI rebasing and a one-decimal index (about 0.1% quantisation noise). Seasonality exceeds trend. Thin liquidity; BoJ/MoF operations absorbed most supply in 2023 (dated). |
| CAD | Real Return Bonds, CPI all items | standard | no | real price | Source of the "Canadian model". The Government announced in Nov 2022 it would stop issuing RRBs: a legacy, long-duration market. |
| AUD | ACGB capital-indexed, CPI | 6 months | yes, coupons also floored | adjusted price | 2035/2040 BEIs have traded below the RBA band midpoint. |
| SEK | SGBi, SWCPI | standard | yes | adjusted price | Many bonds share one base index. Programme significantly downsized (2025). |
| NZD | NZ government linkers | not in the sources | not in the sources | | About USD 14bn in the global linker index (30 Jun 2025). Confirm terms before use. |
| CHF, NOK | none identified | | | | No sovereign linker curve in the sources. Express the view through inflation swaps where they trade, or through fixings-implied forward real rates (NOK forward real yield about 2% was quoted in Nov 2025). |

Market size (global linker index, 30 Jun 2025): US USD 1741bn, EZ 718bn, UK 716bn, JP 64bn, CA 53bn, AU 31bn,
SE 17bn, NZ 14bn. UK and Canada hold a disproportionate DV01 share because of their long duration (BofA, Welcome to
the real world, 22 Jul 2025).

Index vs index: US CPI tends to outrun PCE; UK RPI persistently exceeds UK CPI; French domestic CPI trails euro HICP.
Never move a BE or swap rate between indices without the wedge.

## Inflation swaps (zero-coupon, ZCIS)

| Market | Index | Lag / interpolation | Tenors seen | Notes |
|---|---|---|---|---|
| USD | CPI-U NSA | 3m with interpolation (same as TIPS) | 1-30y | Start 25 Jul 2023 = 303.95448, interpolated from Apr 303.363 and May 304.127 (BofA, Welcome to the real world, 22 Jul 2025). |
| EUR | HICPxT; French CPI ex tobacco | 3m, no interpolation ("month-end roll": every July date references April) | 1-50y | Integer-year ZC HICP swaps and even 5y5y show a seasonal pattern that tracks the inverted linker price pattern. |
| GBP | RPI (CPI swaps also trade) | 2m, no interpolation | 1-50y | GBP ZC swaps are quoted as IRR. |
| AUD | CPI | listed on SEF; terms not in the sources | | |

Contract terms that move PV: the index is non-revised unless a revised variant is named; the day count on the
inflation leg is 1/1; negative-inflation treatment (ZC swaps generally have no deflation floor, year-on-year swaps
usually do); "Related Bond / Fallback Bond" wording applies when the index is not published. ISDA amendments can start at
different dates for bilateral and cleared trades. Minimum SEF notionals seen: USD 10mm (increment 1mm), EUR and GBP
5mm (increment 100k) (tpSEF Rulebook App. B, 2021; dated, re-check).

## Why mixing lags is an error

A bond, its swap hedge and the index curve must use the same lag/interpolation, or the "inflation basis" you measure
contains a lag mismatch. The bond's 3m interpolated reference value is a blend of two months; the EUR ZC swap's
3m non-interpolated reference is a single month. On a July date the bond blends April/May, the swap uses April. The
difference is a pure seasonal/accrual artefact (Düring, Fixed Income Trading and Risk Management, 2021, Ch.23;
Darbyshire, Coding Interest Rates).
