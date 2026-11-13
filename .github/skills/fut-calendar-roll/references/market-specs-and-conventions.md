# Calendar roll: market specifications and conventions

Supporting file for [fut-calendar-roll](../SKILL.md). Contract specifications change: treat every row as a
starting point and read the current exchange specification from `fut_static` / `fut_basket` before use.

## Government bond futures (G10)

| Market | Contract / deliverable range | Last trade, delivery (as printed in 2004 unless stated) | Roll-relevant points |
|---|---|---|---|
| USD | 2y TU, 5y FV, 10y TY, Ultra-10y UXY, bond US, Ultra bond WN; H/M/U/Z; TU is twice the notional of the others | First notice 2 business days before the contract month in 2004 text; last business day of the preceding month in 2026 notes. Delivery any day of the month, seller's choice | Delivery timing rule (late if carry > 0, early if < 0); pro-rata and FIFO allocation of notices; CTD often differs between months in TU/FV/TY/UXY (Burghardt 2005; JPM Aug 2026; Citi Aug 2026) |
| EUR | Bund 8.5-10.5y, Bobl 4.5-5.5y, Schatz 1.75-2.25y | Last trade 2 exchange days before delivery; delivery on the 10th calendar day of the month | Principal clearing lets one account hold long and short at once, inflating OI versus US netting; squeezes and fails more common than in the US; the Schatz back CTD is often not yet issued (Burghardt 2005; During 2021) |
| GBP | Long Gilt, CTD range 8.75-13y | Last trade 2nd business day before the last business day; delivery any business day at the seller's choice | A gilt that goes ex-dividend inside the delivery month cannot be delivered after that: futures priced to it until its last deliverable day, then jump to the next CTD (Burghardt 2005) |
| JPY | JGB 10y, CTD range 7-11y in 2004 text (7-10.5y in a 2024 text) | Last trade 7th business day before delivery; delivery on the 20th | Calendar driven by CTD slope, IRR versus OIS, CTD outstanding; CTD spread vol rises into delivery (Burghardt 2005; Huggins & Schaller 2024; Citi Aug 2026) |
| CAD | Canada 10y, CTD range 8-10.25y | Last trade 7th business day before the last business day; delivery any business day, seller's choice | Same-CTD carry roll; no calendar-specific numbers in the sources |
| AUD | 3y and 10y bond futures, cash-settled | Last trade 15th of the month; settlement the next business day | No CTD and no delivery option: see formula below |
| NZD, CHF, SEK, NOK | no roll-specific numbers in the source material | verify in `fut_static` | Use carry plus slope logic of step 2 where the contract is physically settled |

Conflicts to verify: JGB basket range (7-11y vs 7-10.5y); first notice rule (2004 vs 2026); wildcard interval (one
vendor guide states 6 and 15 hours).

## Cash-settled bond futures (AUD)

Settlement value per contract, with notional 6% semi-annual 10y bond: `Value = 1000 x [ (C/2) x (1 - (1 + R/200)^-20) / (R/200) + 100 x (1 + R/200)^-20 ]`,
`C = 6`, `R = 100 - futures price`. At price 95.00 (R = 5%): value A$107,794.58 on recomputation (the book prints
107,795.58, a typo of 1.00); average DV01 over 95.01 and 94.99 = A$81.63 (Burghardt 2005). Because the cash settlement
price depends only on R, front and back have the same PVBP: the BPV roll ratio is 1:1 and `dy = 0.01/(PVBP_f - PVBP_b)` is
undefined (During 2021, Eq. 28.20). Price = 100 - yield, so the fair roll is the forward-yield difference between d2 and d1
(derived).

## SOFR futures (USD) used for strip rolls

| Item | 3m SOFR (SR3) | 1m SOFR (SR1) |
|---|---|---|
| Reference period | 3rd Wednesday (included) of the third month before the delivery month to 3rd Wednesday (excluded) of the delivery month; contract month = month the period begins (Sep-22: 21 Sep to 21 Dec 2022) | calendar days of the delivery month, simple arithmetic average (weekends and holidays use the prior business day) |
| Settlement rate | compounded: `R = [prod(1 + SOFR_i/100 x d_i/360) - 1] x 360/D x 100`, price = 100 - R; `d_i` = calendar days SOFR_i applies (Friday fixing d = 3), `D = sum d_i` | arithmetic average |
| Last trade | business day before the 3rd Wednesday of the delivery month; cash settlement the next business day | last business day of the month |
| Value per bp, tick | USD 25; 0.25bp within 4 months of last trade, else 0.5bp | USD 41.67; 0.25bp in delivery month, else 0.5bp |

(Huggins & Schaller, SOFR Futures and Options, 2022, ch. 2.)

- **Roll rule.** Roll the 2nd listed SR3 into the 3rd, before the reference period begins; the in-period front is sticky
  and decouples from the market. Dec-19 into Mar-20 cost 138bp if rolled at the end of the reference quarter vs 4bp at the
  start (SOFR fell sharply: an extreme case; roll-at-start was closer to zero in almost every quarter Sep-18 to Jun-21).
- **In-period front SR3.** Split known and unknown fixings: `R_unknown = [ (R x D/360/100 + 1) / prod_known(1 + SOFR_i/100 x d_i/360) - 1 ] x 360/D_unknown x 100`.
  A strip does not need a cash stub (unlike Eurodollar). A revision of the last SOFR cannot enter settlement.
- **SR1-SR3 spread.** No basis. Driven by (1) different periods, so curve slope and Fed timing matter and (2) simple versus
  compounded averaging, which is 0 at SOFR = 0 and about 3bp for constant SOFR of 5% over the quarter. Quote as
  `(SR1_a + SR1_b)/2 - SR3` with 3 SR1 + 3 SR1 against 10 SR3 (BPV 6 x 41.67 = 250.02 vs 10 x 25 = 250); the CME convention
  differs from the contract-weighted spread by under 1bp, which matters at low rates. Fair spread by (SOFR level, in-quarter
  slope), bp: SOFR 0 and flat 0.00; SOFR 100 flat 0.12, slope +50 2.85, slope -50 -2.59; SOFR 500 flat 3.11, slope +50 6.09,
  slope -50 0.15. A 50bp hike on 1 Dec 2022 (outside SR1 coverage) gives a fair spread of 12bp.
- **Regime.** Re-estimate roll and spread statistics on post-August-2021 data (SOFR statistics changed).
- Hike sensitivity check: SR1 moves by `hike x calendar days after the meeting / days in month` (25bp on 4 May 2022: 21.8bp on May-22).
- Strip annualisation: `S = (1 + S_ann x 365/360)^N x (1 + S_ann x F/360)`, `N` whole years, `F` remaining days.

## Commodity-style roll yield (context only)

For a futures contract over [t1, t2] with expiry T: `R = (f_t2 - f_t1) - (S_t2 - S_t1)`; if t2 = T the roll yield is
`S_t1 - f_t1`. Backwardation gives a positive roll return to a long. This is not the bond-futures calendar: there the
spread is carry plus option value (Leung & Li, 2016, ch. 5).
