# SDR field dictionary, netting and cleaning recipe

Companion to `SKILL.md`. Field names follow the canonical `flows_trades` table. Source fields are
those of the public swap data repository dissemination rules (CFTC Technical Specification, Parts 43
and 45, v3.0 Sep 2021 and v3.1 Aug 2022). Field mapping is repository-specific until a unique product
identifier is designated, so build one adapter per repository.

## 1. What the public tape carries

| Concept | Source field (public) | Canonical column | Notes |
|---|---|---|---|
| Dissemination identifier | unique transaction identifier | `trade_uid` | Changes on a new print, not on a correction. |
| Action | action type: NEWT, MODI, CORR, EROR, TERM, REVI, PRTO, VALU, MARU | `action` (new, correct, cancel, error) | CORR points to the original; EROR removes the original; REVI is a new print. |
| Event | event type: TRAD, NOVA, COMP, ETRM, CLRG, EXER, ALOC, CLAL, CREV, PTNG, CORP, UPDT | `is_compression`, derived | Compression is TERM or NEWT with COMP. Clearing legs (NEWT-CLRG) and allocations are non-printing. |
| Cleared | Y, N, I (I = original alpha swap) | `cleared` | The public print of a cleared trade is the alpha execution. |
| Venue | platform MIC (XOFF = listed off-venue, XXXX = unlisted, BILT = unknown) | `venue` | Venue code list below. |
| Package flag and price | package flag, package spread or price | `is_package` | Package membership is a boolean; the type is inferred. |
| Fixed rate | fixed rate as decimal (0.0257) | `fixed_rate_pct` | Convert to percent (2.57) at ingestion. |
| Spread notation | notation 3 (decimal) or 4 (integer bp, 257 = 2.57%) | `spread_bp` | Check the notation field before scaling. |
| Notional | notional, first 10 schedule values only | `notional_ccy`, `notional_capped` | Capped and rounded; other fields scaled when capped. |
| Execution time | execution timestamp, UTC, fixed for the UTI's life | `exec_ts_utc` | Use for sequencing. |
| Dissemination time | dissemination timestamp | `pub_ts_utc` | Knowledge time. |

**Not disseminated:** counterparty identifiers and LEIs, the transaction identifier chain (prior and
original), the package identifier, the reporting timestamp, the clearing member, valuation, collateral
and direction (payer or receiver, buyer or seller). Direction and dealer identity therefore need a
second source.

**Since 5 Dec 2022 (Part 43):** unique transaction and product identifiers (CPMI-IOSCO) are
disseminated. The platform identifier is on every record, separating customer-to-dealer, dealer-to-
dealer and off-venue. The package identifier marks membership of a multi-transaction package, not its
type (Clarus, SDR Trading Venues and Packages, Jan 2023).

## 2. Netting and sentinels

1. A `CORR` row points to the original identifier. Drop the original; keep the correction.
2. An `EROR` removes the original it refers to. Drop both.
3. A `REVI` is a new print. Do not net it against the original.
4. A cancel removes the referenced print and itself.
5. All-nines values ("unknown", not data): notional `99999999999999999999.99999`; package spread
   `99999` in notation 4. Set to missing before any statistic.
6. Non-printing events (clearing legs, compression terminations and new trades, allocations, block
   prints counted once, SDR transfers, non-amendment modifications, partial physical exercise) must be
   removed before volume or direction work.

The `price_forming` function in `scripts/sdr_flow_metrics.py` implements steps 1, 2 and 4 with
compression and package removal. Test it on a case with known survivors before use.

## 3. Cleaning recipe with thresholds

Run in this order. Record the count removed at each step; that count is part of the output.

| Step | Rule | Source |
|---|---|---|
| 1 | Keep new prints plus amendments that carry a fee; drop fee-less amendments, cancels and novations | Fleming et al. (NY Fed Staff Report 557, Mar 2012) |
| 2 | Drop compression, FRA switch batches, prime-brokered, allocated, internal, physically exercised and manually duplicated prints | Fleming et al., Mar 2012 |
| 3 | Keep spot-starting trades for spot-liquidity work (effective more than 2 business days after trade excluded); or effective more than 5 days after trade excluded for the price-forming volume definition. State which | Benos et al. (Bank of England Staff WP 580, Jul 2016); Fleming et al., Mar 2012 |
| 4 | Remove duplicates: each cleared trade is reported once per clearing-member side. Key = execution time, product, currency, effective date, maturity, notional, rate | Benos et al., Jul 2016 |
| 5 | Keep rates within 5% of the same-day end-of-day benchmark for the same currency and maturity | Benos et al., Jul 2016 |
| 6 | De-duplicate across sources on trade date, effective date, maturity, notional and rate | Benos et al., Jul 2016 |
| 7 | Flag re-couponing: a long-dated swap terminated and replaced by a par swap on the same dates; count the chain once | Düring, Fixed Income Trading and Risk Management (Wiley, 2021) |

Reference results: Benos et al. retained 628,896 reports (USD 58.17tn). Fleming et al. found 167k
price-forming and 319k non-price-forming trades in 2010 (USD 45tn and USD 66tn).

## 4. Venue codes (data codes, not vendor functions)

| Class | Codes | Notes |
|---|---|---|
| Customer-to-dealer SEF | TWSF, BBSF | TWSF was the largest USD IRS venue in late Dec 2022, e.g. 520 of 873 prints on 21 Dec 2022, mostly compression as USD Libor ended (Clarus, SDR Trading Venues and Packages, Jan 2023). |
| Dealer-to-dealer | BGCD, DWSF, IGDL, ISWV, TPSE, TSEF | BGCD and ISWV assumed voice. TPSE trades likely from a matchbook. |
| Off-venue | BILT, XOFF, XXXX | USD swaptions are mostly BILT (off-venue) or voice. |
| Risk optimisation | REST | Portfolio-reset (risk optimisation) platform. |
| NDF-related | BHSF, CBNL, EBSS, JPCB, THRE, XEBS | Not G10 rates. |

Re-apply the venue whitelist at every stage. A null platform passes a naive "not inter-dealer broker"
gate, so test for it explicitly.

## 5. Product and taxonomy labels

ISDA OTC taxonomy as used in repository reporting:
- Interest rate, base product "IR Swap", sub-products: Basis, Fixed Floating, Inflation, Cap/Floor, Exotic.
- Base product "FRA", blank sub-product.
- Cleared at CME and LCH: "Fixed Float and OIS" plus "Basis". Eurex: "Fixed Float, Inflation, OIS and Basis". ASX and JSCC: "Fixed Float, OIS and Basis" (tpSEF Rulebook, Appendix B, May 2021).
- USD OIS package taxonomy in one vendor-independent review: Butterfly, Curve, List, Outright, Package (granular type not identified), SpreadCurve, Spreadover (over the government bond) (Clarus, SDR Trading Venues and Packages, Jan 2023).

ISDA amendments can take effect at different times for bilateral and cleared trades, so the same
economic swap can carry different legal terms at different clearing houses (tpSEF Rulebook, May 2021).
The 2021 product lists reflect the LIBOR and EONIA era; check current definitions before reuse.

## 6. Package and structure linking

- Public heuristic: package flag true + identical execution timestamp + identical package spread or
  price. This is a probable link, not a certain one.
- Anchor leg: the earliest print by (expiration, effective, trade identifier) is the package anchor.
- Legs per package: fly 3, curve 2, CCP switch 2 (Clarus, SOFR Swap SEF Volumes, Jun 2024).
- Package type from price: a fly has a near-zero or small package spread relative to the legs; a curve
  is a spread between two tenors. Infer type from the package price against expected leg levels,
  and mark the type confidence (Clarus, SDR Trading Venues and Packages, Jan 2023).

## 7. Data fields a derived DV01 needs

DV01 uses the fixed-leg frequency and day count from the swap conventions table, the tenor from
effective and maturity dates, and the par rate. A capped notional gives a censored DV01 (use the cap,
flag it). A zero or missing rate means no DV01 from the formula, so drop the print from DV01 totals and
say so.
