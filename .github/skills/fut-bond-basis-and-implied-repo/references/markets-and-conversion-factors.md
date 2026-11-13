# Markets, contract terms and conversion-factor mechanics

Detail behind [SKILL.md](../SKILL.md). Read it when the contract is not a plain CBOT note/bond, when a conversion factor
(CF) must be checked, or when a source quotes basis in different units.

## 1. CBOT/CME conversion factor, step by step

Definition: CF = price per 1 of par of the deliverable at a yield equal to the notional coupon (6% since Mar 2000, 8%
before), with the term measured from the **first day of the delivery month** (Salomon, Understanding Treasury Bond
Futures Q&A, Oct 1990; CME Group, Understanding Treasury Futures, Nov 2017). It is fixed for a bond/month pair and does
not move with yields or as delivery approaches. Always take the exchange-published CF into `fut_basket.conversion_factor`;
`scripts/basis.py: cbot_cf` only reproduces it (selftest: 7 published values).

Rounding recipe (Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005, App. A):

1. Term = whole years `n` plus leftover months `z` from the first of the delivery month to maturity (first call date if callable).
   Days are dropped: 16y 2m 14d counts as 16y 2m.
2. Round `z` DOWN to the quarter (0, 3, 6, 9) for the 10y/Bond/Ultra contracts; keep whole months for the 2y/3y/5y contracts.
3. `v = z` if `z < 7`; else `v = 3` (10y/Bond) or `v = z - 6` (2y/5y).
4. With coupon `C` (decimal) and notional `N = 0.06`:
   `a = 1.03^(-v/6)`, `b = (C/2)(6-v)/6`, `c = 1.03^(-2n)` if `z < 7` else `1.03^(-(2n+1))`, `d = (C/N)(1-c)`,
   `CF = a(C/2 + c + d) - b`, rounded to 4 dp.

Checks (published): 4-7/8% 15-Feb-2012 for Jun-2004 gives 0.9328; 3-5/8% 15-May-2013 for Jun-2004 gives 0.8401;
7-1/2% 15-Nov-2016 for Jun-2001 gives 1.1484; 8-7/8% 15-Aug-2017 for Jun-2001 (bond) gives 1.2931 (Burghardt et al., 2005);
2.375% 15-Aug-2024 for Dec-2017 (10y) gives 0.8072 and 1.875% gives 0.7807 (CME Group, Nov 2017).
A simpler statement of the same object, for a coupon-date settlement: `CF = (C/N)(1 - 1.03^-m) + 1.03^-m` with `m` semi-annual
periods left, e.g. 1.25% with 13 periods gives 0.7474 (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022).
Tuckman quotes "last delivery date" as the CF settlement date; CME's rule is the first day of the delivery month.
The difference is below one rounding step for most bonds, but if your CF will not tie to the exchange, test both.

Behaviour worth knowing:
- Coupon above notional gives CF above 1, falling toward 1 in successive contract months; coupon below gives CF below 1, rising toward 1.
- "Scalloping": for coupon near the notional, CF can be non-monotonic across months because quarter-rounding leaves a 1/4 or 3/4
  year fractional term (Salomon, 1990).
- If every deliverable yielded the notional coupon, `F = P/CF` would be equal for all bonds and all would be jointly CTD.
  Yield below notional: low-duration bonds are CTD; above: high-duration bonds (subject to slope) (Burghardt et al., 2005).
- Low CFs raise contract DV01 and convexity (the original Ultra Bond future had DV01 56% above the classic bond contract's) and give the
  wildcard its value (CFs 0.43 to 0.83 in one Ultra-Bond basket) (Credit Suisse, New Ultra Long Contract, 28 Sep 2009; BofA, Primer, 10 Jul 2025).
- Exchanges sometimes move a new contract to a different notional coupon when basket yields are far from the old one. That
  changes option value and CTD behaviour materially (Huggins and Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).

## 2. Contract terms that change the basis arithmetic

Terms below are exchange terms as stated in the cited sources or in the data contract (`fut_static`). Verify against the
exchange notice before use; `fut_static` is the source of truth in the agent.

| Market / contract | Notional coupon | Delivery | Options held by the short | Notes |
|---|---|---|---|---|
| USD 2y (TU), 3y, 5y (FV) | 6% | any business day of the month; LTD = last business day of month | quality, timing, wildcard, EOM | 2y contract is USD 200k face, so basis per contract is double. 2y original term at most 5y3m, remaining 1y9m-2y; 5y remaining at least 4y2m (CME, Nov 2017). FV is the one contract with negative carry in Aug 2026 (first-day delivery) (JPM, Rollover Outlook, 12 Aug 2026). |
| USD 10y (TY), Ultra-10y (UXY), Bond (US), Ultra-Bond (WN) | 6% | any business day; LTD = 7 business days before last business day | quality, timing, wildcard, EOM | TY remaining term 6.5y to under 8y (CME, 2017); Bond 15y to under 25y; Ultra-Bond at least 25y. WN and UXY have the lowest CFs and the largest wildcard. Delivery cycle is 3 days: intention, notice, delivery. Wildcard window runs from the 3pm futures close to the notice deadline (JPM, Special delivery, 4 Dec 2019). |
| EUR Schatz / Bobl / Bund | 6% | one delivery day: the 10th calendar day or next business day | quality only (no timing, no wildcard) | Invoice per contract = 100,000 x (F/100) x CF + accrued. CF per Eurex convention: take from the exchange. Net basis in cents (Dec-2026: Schatz/Bobl/Bund 0/1/3c) (JPM, Eurex CTDs wobble, 2 Oct 2026). |
| EUR Buxl | 4% | as above | quality | Net basis about 8c versus delivery option about 25c: "essentially a duration play" (JPM, 2 Oct 2026). |
| EUR OAT, BTP | 6% | as above | quality | OAT delivery option about 10c, option-adjusted net basis near 0; BTP option about 7c (JPM, 2 Oct 2026). Non-dominant CTDs at higher yields. |
| GBP long gilt (ICE) | 4% | any business day of the month | quality, timing | CF = clean price at yield equal to notional coupon on first delivery day: exact for the gilt (Darbyshire, Coding Interest Rates). Ex-dividend rules can remove a CTD mid-month; small basket raises squeeze and fail risk (Düring, Fixed Income Trading and Risk Management, 2021). Repo is ACT/365F; gilt accrued is actual/actual, not ACT/365F (1.4365 versus 1.4247 for the same coupon and dates, Darbyshire). |
| JPY 10y JGB (JPX) | 6% | one delivery day per month | quality | Basket about 7-10.5y; at low yields the shortest bond is CTD and 2-3 near-identical bonds compete. A one-factor model sees under 1 sen of option, a multi-factor model 7 sen (Huggins and Schaller, 2024). Futures are structurally rich to cash because index funds proxy JGB exposure with futures (Düring, 2021). IRR tracks OIS: use it as a policy-pricing check (Citi, Japan Rates Weekly, 21 Aug 2026). |
| CAD 10y (MX) | 6% (data contract) | physical delivery | not covered by sources read | Treat as US-style physical basis: take CF and delivery window from `fut_static`/`fut_basket`; no source material on its option value was read. |
| CHF (Eurex), SEK (Nasdaq designated bond) | 1% / 1% (data contract) | physical / single designated bond | | CHF: small basket, run the same formulas with exchange CFs. SEK: single designated deliverable and yield quoting, so there is no CTD choice: the "basis" is just the bond versus the futures-implied yield. |
| AUD (ASX) | 6% | cash settled | none | EDSP = 100 - 100 x sum(w_i y_i) with fixed weights over a basket of yields: no CTD, no CF, no IRR (Düring, 2021). Use only the replacement and funding sections. |
| NZD, NOK | n/a | n/a | n/a | No liquid physically settled government bond future in the data contract and no source read. Skip. |

### 2b. USD contract specification table (BofA, Primer, 10 Jul 2025)

| Contract | Face | Deliverable remaining maturity | Original maturity | Minimum tick |
|---|---|---|---|---|
| TU (2y) | USD 200k | 1 3/4 to 2y | at most 5 1/4y | 1/8 of 32nd = USD 7.8125 |
| FV (5y) | USD 100k | 4 1/6 to 5 1/4y | at most 5 1/4y | 1/4 of 32nd = USD 7.8125 |
| TY (10y) | USD 100k | 6 1/2 to 8y | none | 1/2 of 32nd = USD 15.625 |
| UXY (Ultra-10y) | USD 100k | 9 5/12 to 10y | at most 10y | 1/2 of 32nd = USD 15.625 |
| US (Bond) | USD 100k | 15 to 25y | none | 1/32 = USD 31.25 |
| WN (Ultra-Bond) | USD 100k | 25 to 30y | none | 1/32 = USD 31.25 |

- Last trade date: last business day of the delivery month for TU and FV; 7 business days before the last business day for the others.
  Last delivery date: third business day after the last trade date for TU and FV; last business day of the delivery month for the others.
- FV needs original maturity of at most 5y3m and remaining maturity of at least 4y2m on the first day of the delivery month, so only original-issue 5y notes are deliverable.
- Scale (2023-25 sources): FV open interest about 7mm contracts (about USD 700bn); TU about 4.3mm contracts, about USD 900bn notional because of the double face.
  Futures volume was about USD 645bn per day in 2023 against about USD 460bn per day of primary-dealer cash trading.
- The Sep-2025 Ultra-Bond basket had CFs from 0.43 (1.625% coupon) to 0.83 (4.75%): factors well below 1 are what give the wildcard its value.

## 3. Quoting units

- Prices are decimal in the data contract. 32nds text is never stored. Convert: `ticks = decimal x 32` for the US bond contracts.
  "Tick" in US research means 1/32 of a point for gross/net basis unless the text says otherwise; the contract's minimum
  price increment is finer for TU, FV and TY (1/256, 1/128, 1/64). Quote basis as `32nds` with the unit in the column name.
- Eurex basis is in cents per 100 (`c`), JGB basis in sen.
- Money per 1/32 per contract is USD 31.25 for the Bond and Ultra-Bond contracts (USD 100k face); a CF-weighted package P&L per tick of basis is that times the number of contracts.
- Futures DV01 per contract = CTD forward DV01 per 100k face / CF (Salomon, 1990; CME, 2017; Darbyshire). Convexity likewise (d2I/dy2)/CF.
  Futures PV01 for a multi-CTD basket = sum over candidates of P(CTD_i) x forward PV01_i / CF_i (BofA, Primer, 10 Jul 2025; MS, 27 Aug 2026).

## 4. Regression conversion factors (non-deliverable bonds)

European desks sometimes quote a basis for non-deliverable bonds using `P_bond = alpha + beta P_F` and use `beta` as the CF.
It is fitted over a fixed window before the contract becomes front and is unstable because the contract is illiquid then
(Düring, 2021). Label any such basis "regression CF" and do not mix it with exchange-CF bases.

## 5. Basis report columns worth emitting

Per contract: model price, rich/cheap in 32nds (model minus market; positive = futures cheap), futures DV01 (probability-weighted
forward DV01 / CF), repo sensitivity (change in model price per +100bp repo). Per bond: term repo (specials visible), forward
price and yield, forward asset-swap spread, CF, gross basis, carry, net basis, model basis, difference to model (rich/cheap of the basis),
IRR, probability of being CTD (BofA, US Rates Data: Futures Basis Report, 7 Aug 2025).
