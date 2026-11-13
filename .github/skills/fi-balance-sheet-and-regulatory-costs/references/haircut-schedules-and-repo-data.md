# Haircut schedules, repo data and margin examples (lookup)

Companion to [SKILL.md](../SKILL.md). Schedules are as published at the cited date; central banks revise them. Verify the live schedule before pricing.

## 1. Central-bank collateral haircuts (% of market value)

Fed, Oct 2023 (Huggins and Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024, Table 18.1):

| Residual maturity | Bills | Notes/bonds | TIPS | STRIPS |
|---|---|---|---|---|
| < 10y | 1.0 | 2.0 | 2.9 | 3.8 |
| 10-20y | - | 2.9 | 5.7 | 6.5 |
| 20-30y | - | 2.9 | 5.7 | 9.9 |

BoE (same source, Table 18.2), coupon / zero:

| Bucket | Haircut |
|---|---|
| floating | 0.5 / 0.5 |
| < 1y | 0.5 / 0.5 |
| 1-3y | 1.5 / 1.5 |
| 3-5y | 2.0 / 2.0 |
| 5-10y | 3.0 / 3.5 |
| 10-20y | 5.5 / 6.5 |
| 20-30y | 7.0 / 9.5 |
| > 30y | 8.5 / 15.0 |

ECB (same source, Table 18.3), DE/FR/ES bullet, DE/FR/ES zero, IT bullet, IT zero:

| Bucket | DE/FR/ES bullet | DE/FR/ES zero | IT bullet | IT zero |
|---|---|---|---|---|
| < 1y | 0.5 | 0.5 | 5.0 | 5.0 |
| 1-3y | 1.0 | 2.0 | 6.0 | 7.0 |
| 3-5y | 1.5 | 2.5 | 8.5 | 10.0 |
| 5-7y | 2.0 | 3.0 | 10.0 | 11.5 |
| 7-10y | 3.0 | 4.0 | 11.5 | 13.0 |
| 10-15y | 4.0 | 5.0 | 12.5 | 14.0 |
| 15-30y | 5.0 | 6.0 | 13.5 | 15.0 |
| > 30y | 6.0 | 9.0 | 14.0 | 17.0 |

Reading: ECB lends 98.5 per 100 against a 5y Bund, 95 against a 30y Bund, 86.5 against a 30y BTP. Haircuts rise with maturity and fall with credit quality,
so haircut cost steepens every bond-vs-swap curve and widens weaker credits. The book's stated haircut effect on BTP-Bund is about 47bp at 10y and 54bp at 30y at a 600bp
excess cost; the simple product (haircut gap x 600bp: 10y bullet gap 8.5% -> 51bp; 30y bullet gap 8.0% -> 48bp) lands within roughly 15% of those figures, and the book does not state its method.
Haircut arbitrage: the BoE lends more against a bullet than against the strips that replicate it, so reconstitute strips into a low-coupon issue before posting.
Fig 17.2 (17 Oct 2023, SOFR-swapped bond spreads, chart-read, bp): Bunds 1y -21, 5y -24, 10y -22, 20y -3, 25y +3; USTs +1, +25, +29, +41, +64, +65 (1y to 25y); Gilts -31, -5, +35, +63, +84, +95. All slope up; the steep BoE schedule is one reason Gilts are steepest.

## 2. Private repo haircut data

- Tri-party median haircuts: UST/agency debt and MBS 2%; agency CMO 4%; IG corporates, money-market, private CMO IG, international 5%; ABS IG 7%; equities, HY, ABS HY, private CMO HY, munis 8%. Collateral mix of the tri-party pool: UST 62.3%, agency and GSE MBS 21.1%, equities 7.1%, IG corporates 2.5% (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022, Ch.10).
- Hedge-fund UST repo borrowing: 74% has a zero or negative haircut, about 20% above 2% (Banegas and Phillip, Fed, cited in Huggins and Schaller, 2024). About 75% of uncleared Treasury repo has a zero haircut, mostly offsetting repo/reverse with the same counterparty (Hempel et al., OFR 2023, cited in Barclays, Jan 2025). Haircuts are not set in the master agreement; they are agreed trade by trade from price volatility and counterparty.
- Haircut = leverage: a zero-haircut package lets a fund run $200m of position with no cash of its own; a 2% haircut would need $4m. By 2019 hedge funds borrowed up to about 100x capital in non-centrally-cleared bilateral repo (Conks, The Treasury Market Basis Trade, 14 Sep 2023).
- Cleared repo carries CCP initial and variation margin, so it is not the same product as zero-haircut bilateral repo.
- A haircut of 1% on JPY 10bn of collateral lets you borrow 9.9bn; government bonds 0-1% by maturity, equities about 50% at a central bank (Duering, Fixed Income Trading and Risk Management, 2021).

## 3. Repo arithmetic

- Repo interest with a haircut = dirty price x (1 - haircut) x repo rate x days/360. $100 dirty, 1% haircut, 2% repo, 30 days: 99 x 2% x 30/360 = $0.1650 (the source prints 0.166) (BofA, US Treasury repo primer, 7 Jul 2025).
- Sizing (Tuckman and Serrat, Ch.10): collateral $109,898,438 at a 3% haircut borrows 97% = $106,601,485; margin $3,296,953. If collateral falls to $108mm, post about $1.9mm more bonds or repay about $1.8mm of cash (loan falls to $104.8mm).
- Margin on a derivative: IM = 99% move + replacement cost, e.g. $5mm + $250k = $5.25mm. Securities collateral is taken at a haircut (3% haircut: $100 counts as $97) (Tuckman and Serrat, Ch.13).

## 4. When haircuts bite: MF Global (2011)

Repo-to-maturity carry on short peripheral EGBs (Dec 2010 yields: Germany 0.70%, Italy 2.25, Spain 3.32, Portugal 4.50, Ireland 6.00; term repo about 0.70%; haircuts about 3%).
Risk limit $4.75bn was sized so a 15% average haircut could be met from cash; positions peaked at $11.5bn (June 2011); the CCP raised IE/PT haircuts from 3% to 80% (July 2011);
margin as % of position went 2.9% (Jun) -> 4.8% -> 6.6% -> 10.6% (27 Oct 2011). Haircuts fell back to 15% by end-Nov; "had MF Global sized its position to account for the financing risk of increased haircuts, it might have profited rather than have been destroyed" (Tuckman and Serrat, 2022, p.254).
Lesson: size leveraged positions to the stressed haircut and to who can change it (a CCP can, unilaterally), not to price risk; hedging the price does not hedge margin.

## 5. Funding stress statistics

- March 2020: 99th percentile repo minus SOFR typically 10-11bp in Feb 2020, 20-50bp on several March days, peak 174bp on 16 Mar 2020 (Tuckman and Serrat, 2022, Fig 11.13).
- Sept 2019: reserves fell about 9%; with the Fed range 2-2.25%, transaction-weighted repo averaged 5.25% one day, one trade at 10%; banks did not lend reserves into repo because of the leverage ratio, HQLA preferences and daylight-overdraft stigma (Tuckman and Serrat, 2022).
- 29 Jun 2018: SOFR 2.12% vs EFFR 1.91%, an apparent +21bp "arbitrage" (borrow unsecured, lend secured) left open by segmentation and balance-sheet limits (Huggins and Schaller, SOFR Futures and Options, 2022).
- Pre-SRF quarter-ends: SOFR sometimes more than 20bp above fed funds. The standing repo facility (announced 28 Jul 2021) imposed SOFR <= facility rate. It is not a firm ceiling: stigma, afternoon timing, no netting (the dealer faces two counterparties, the Fed and its client) and haircuts mean dealers want up to about 25bp over the top of the range (Barclays, Jan 2025; Conks, The Repo Fortification, 3 Dec 2025; NY Fed, Perli speech, 12 Nov 2024).
- Dealer intermediation: primary dealers absorbed up to 80% of a 10y auction once, about 17% now (Conks, Volatility Suppression, 2023). Dealer repo activity $3.1tn Q1'08, trough $1.3tn, about $2.7tn in 2025; dealer share 60% -> 42% (BofA, 2025).
