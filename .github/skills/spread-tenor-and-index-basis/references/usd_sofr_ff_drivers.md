# USD SOFR vs Fed funds: structure, drivers, models, dated views

Detail for [SKILL.md](../SKILL.md). Sign: **realised basis = SOFR − EFFR**; desk "SOFR/FF" = FF − SOFR (futures price
spread). Every level below is restated in the convention named in its row. All regressions and trade levels are
dated and regime-specific: refit before use, and treat dated views as history, not as current recommendations.

## 1. What each leg is

| Item | Facts | Source |
|---|---|---|
| SOFR | volume-weighted median of UST-backed repo: tri-party GC (TGCR) + GCF (BGCR = TGCR + GCF) + FICC-cleared DVP; bilateral non-centrally-cleared excluded. Lower tail of DVP trimmed (volume-weighted bottom 25% in one source, a 20% hard cut in a 2024 proposal; sources differ, check current methodology). Volume about $2.2–3.3tn/day | Conks, The Repo Market Dislocation II, 31 Aug 2024; BofA repo primer 2025 |
| EFFR | volume-weighted median of overnight fed funds; about 95% of lending is FHLBs lending to foreign banks; volume $80–160bn/day, peak about $144bn Mar 2023 | BofA, Fed policy plumbing '25 edition, 8 Jul 2025 |
| OBFR | EFFR + Eurodollar + selected deposits (Eurodollar about 62%); MMF/corporate/official lending | same |
| Why EFFR is idle | FHLBs cannot earn IORB, so they lend to foreign banks that park the cash at IORB (borrow at EFFR 4.09, earn IORB 4.15 in the source example); US banks cannot profit (FDIC fees, leverage ratio). Quarter-end dips in FF volume are foreign-bank window dressing | Conks, The Fed's Reckoning II, 30 Sep 2025 |
| SOFR bimodality | modes at the cash-lender rate (about tri-party) and cash-borrower rate (about the 75th percentile); little volume between them, so the median jumps more than the 25th/75th. Regress SOFR − ON RRP on (75th − 25th): R² 0.68. Tri-party near 50% of trimmed volume: median can jump between segments | JPM, A dollar funding market riddle, 26 Feb 2020; Citi, FX Basis Quarterly, 13 Dec 2024 |
| SOFR ≤ EFFR | holds only when balance-sheet constraints do not bind; 29 Jun 2018 SOFR 2.12% vs EFFR 1.91%. A standing-repo cap (SOFR ≤ SRF rate, from Jul 2021) is soft: not all participants eligible. SOFR futures cannot be priced purely by no-arbitrage; a few bp of fixing risk remain | Huggins & Schaller, SOFR Futures and Options, 2022 |
| Rate order, 2018–25 | GCF > bilateral > tri-party; SOFR minus segment averages −2bp (GCF), +1bp (bilateral), +4bp (tri-party), so tri-party prints below SOFR | BofA, US Treasury repo primer 2025 |

Corridor, 1 Jul 2025 (sources agree on all but the SOFR print, which they give as 4.30 and 4.44): standing repo 4.50, IORB 4.40,
EFFR 4.33, ON RRP 4.25. IORB adjustments historically followed EFFR trading ≥ 5bp from the top or bottom of the range.

## 2. Mechanism (supply and demand)

- SOFR supply = Treasuries needing financing; repo cash demand = f(reserves): banks invest reserves in repo when repo
  exceeds IORB (about 5–10bp above IORB for GC). FF supply = FHLB excess cash; FF demand = foreign-bank arbitrage
  and reserve scarcity.
- Abundant reserves: SOFR several bp below IORB, FF modestly above, FF ≥ SOFR. Scarce or collateral outrunning cash:
  SOFR > FF, both above IORB. Theoretical maximum overnight FF − SOFR about 10–12bp (very abundant reserves, SOFR
  drifting to zero, FF pinned mid-range by the IORB arbitrage).
- **FHLB allocation rule:** FHLB surplus cash (about $200bn average since 2022) goes to interest-bearing deposits, FF and repo;
  FF is preferred for early return. When repo > FF, FHLBs shift from FF to tri-party; as TGCR rises vs FF, FF volume falls and
  FF rises (lowest-rate trades drop out first). FHLBs never held more than 67% of the liquidity portfolio in repo.
  When a cash flood pushes repo below FF, FHLBs are forced into FF and EFFR can drop (mid-May 2026: EFFR −2bp, FF volume >$100bn)
  (BofA, FHLB liquidity & SOFR/FF widening, 6 Oct 2025; Conks, The Repo Rebound, 23 Jun 2026).
- **Intervention asymmetry:** action before a repo spike lowers SOFR faster than the idle FF rate, so QT end, bill purchases
  and term repo narrow the realised basis. Cuts to administered rates during a spike compress SOFR − FF; in calm both fall together.
  Fed bill purchases "crushed" the whole SOFR-FF futures curve within about a month (Conks, A Global Compression, 1 Feb 2026).
- Hedge-fund repo demand (cash-futures basis trades) and equity-financing spillover (dealers redirect dollar funding from
  Treasury repo to equity delta-one when equity financing spreads are fat) push SOFR up vs FF (Conks, The Equity Repo Mania, 12 Jul 2026).
- Debt-limit cycle: before the X-date bills shrink and reserves rise (realised basis down); after resolution the TGA rebuild drains
  cash while a wave of bills is financed (realised basis up). Well-telegraphed drawdowns are priced; the edge is refill timing.
- Policy-target risk: the Fed's operating target moving from EFFR toward a secured rate would reshape the SOFR/FF basis and FF futures;
  the repo clearing mandate (mid-2027) moves volume into cleared DVP and changes where SOFR prints (watch SOFR − TGCR).

## 3. Regimes and fair value

Average overnight spread by regime (BofA, SOFR/FF term structure post "big bang", 22 Oct 2020, 10-day average):

| Period | FF − SOFR (desk) | Realised SOFR − EFFR | Driver |
|---|---|---|---|
| Aug 2014 – Sep 2016 | +0.9bp | −0.9bp | abundant reserves |
| Oct 2016 – Jan 2018 | +9.9bp | −9.9bp | after MMF reform, large cash |
| Feb 2018 – Sep 2019 | −3.2bp | +3.2bp | tax-cut Treasury supply to repo blow-up |
| Oct 2019 – Oct 2020 | 0.0bp | 0.0bp | post-intervention |
| full sample | +1.5bp | −1.5bp | |

Two-regime anchor (BofA, US Treasury repo primer, 7 Jul 2025): **ON RRP ≥ $500bn**, SOFR anchored near ON RRP, SOFR − tri-party ≤ 4–5bp, FF has
scope to rise vs SOFR; **ON RRP < $500bn**, upward pressure on SOFR, basis moves led by SOFR, SOFR more volatile. ON RRP
falls about $0.52bn per $1bn of net bill supply (R² 0.20), so pressure appears once ON RRP is near zero
(BofA, Funding notes: bill tracking & repo, 8 Aug 2025). MMFs leave ON RRP when 1m bill-FF OIS is 2–5bp.

Reserve gauges: reserves/bank assets abundant > 13%, ample 11–13%, scarce < 11% (Conks, 15 Mar 2025). FF starts reacting
when (reserves + ON RRP)/GDP < 10%. IORB − EFFR: about 10bp (2023), 2bp "barely ample" vs 4–5bp "near abundant" (2026), 1bp Jan 2026.

## 4. Fitted models (dated; keep for method, not for levels)

Spread vs `ln(reserves in $bn)`, weekly, bp (BofA, Fed QT beyond taper, 22 Oct 2021, and SOFR/FF term structure, 22 Oct 2020):

| Dependent | Sample | Fit | R² |
|---|---|---|---|
| SOFR − IOER | 2015–19 | −42.29 ln(x) + 314.47 | 0.60 |
| SOFR − IOER | Jun 2020+ | −25.59 ln(x) + 202.56 | 0.91 |
| FF − IOER | 2015–19 | −30.24 ln(x) + 224.36 | 0.91 |
| FF − IOER | Jun 2020+ | −12.26 ln(x) + 96.63 | 0.74 |

Regime-weighted version (BofA, Monthly rates models, Apr, May, Aug 2025): SOFR − IORB regressed on `ln(liquidity/GDP)` per regime,
liquidity = (ON RRP + reserves)/GDP, plus marketable debt ex-Fed/GDP and dealer holdings; fits 3Q20–1Q21: −34.59 ln(x) + 88.95 (R² 0.73);
2Q21–1Q24: −4.96 ln(x) + 4.53 (R² 0.06); 2Q24–Dec 2024: −9.16 ln(x) + 16.6 (R² 0.17). EFFR − IORB: sensitive period 3Q20–3Q21 −10.55 ln(x) + 26.54 (R² 0.74);
sticky period since 4Q21 R² 0.02. **Projection: FF − SOFR = (EFFR − IORB) − (SOFR − IORB).** Regime weights are a judgment call: moving from equal weights to 30/10/30/30
moved the Dec-26 FF − SOFR forecast from −2.1 to −5.6bp in one month. Reserve-demand curve since mid-2024 (BofA, Repo jump & Fed bill backfill, 20 Oct 2025): SOFR − IORB = −8.065 ln(x) + 13.9 (R² 0.34).

Bills-minus-reserves heuristic (Citi, Time for moderation, 17 Feb 2023): desk FF − SOFR = −0.011 × (bills − reserves, $bn) + 5.08, R² 0.59, about 1bp
per $100bn. Weekly-change betas per $100bn (Citi, SOFR/FF to go negative in Q3/Q4 and SOFR/FF spiking into quarter-end, Jun 2025): SOFR/FF on reserves 0.84 (t 3.7),
on bills−reserves −0.79 (t −3.8) full sample; 2021–25 reserves 0.38, bills−reserves −0.32; bills alone insignificant. Keep bills in to capture the non-linear 2023 move.

Model-path method (Citi): regress on reserves and bills (since Sep 2024) with month-end dummies, project bills/reserves/TGA, overlay the average change over the week
before each month-end, compare with futures month by month. Citi's Jun 2025 path (desk FF − SOFR): +4 to +5bp Jun–Jul, −4 to −5 Sep–Nov, below −6 Dec, possibly −10
(a Dec-2024-like non-linear move); futures were less negative.

## 5. Event-study (analogue) method for funding-driven basis

1. Choose episodes by matching state variables: limited ON RRP buffer, similar % growth in bills and total supply (debt-limit resolutions of 2017–2019; 2021 and 2023 not comparable because
   of huge ON RRP). 2017 and 2018 five months apart count as one episode.
2. Let the data speak: average 1m/3m/6m change after resolution (1m moving average). Result, FF − SOFR change: 2017 1.9/−0.4/−9.6; 2018 −10.0/−11.7/−7.7; 2019 −14.8/−1.0/2.1;
   average −7.7/−4.4/−5.1bp (SOFR wider by 4–8bp). SOFR − IORB average +3.0/+5.1/+5.7bp (BofA, Funding & debt limit: history lessons, 27 Jun 2025).
3. TGA rebuild speed (business days to close a share of the gap): 5% in 3, 10% in 5, 20% in 10, 30% in 13, 40% in 21, 50% in 28, 60% in 30, 80% in 34, 100% in 51 (per-episode 100%: 20 to 75 days).
   Dispersion is wide (20 days: 2017 112% vs 2019 0%) (BofA, Short July SOFR/FF, 30 Jun 2025).
4. Condition on remaining ON RRP buffer; a Fed intervention can truncate the analogue (2019). Quarter-ends inside the period add convexity.

## 6. Seasonality and calendar

SOFR rises into month/quarter-end and the basis widens (realised up); repeat across Sep-24, Dec-24, Mar-25, Jun-25 (plot vs business days before quarter-end, 40 to 0).
Mid-month coupon settlements on the corporate tax date (15 Sep 2025) pushed repo above IORB. Canadian banks cut repo at their fiscal quarter-ends (April), pressuring
month-end SOFR. Year-end basis "tends to overprice tightness in advance and then sell off as the year concludes" (Conks, Swifter Injections, 4 Dec 2025). Tail mapping: if the Fed cuts IORB 5bp
relative to the range, FF falls by the same and SOFR is unchanged, so desk FF − SOFR ≈ −15bp (Citi, Jun 2025).

## 7. Spread monitor (read as a set)

| Spread | Reads as |
|---|---|
| SOFR − EFFR | FHLB repo demand (up = FHLBs deploy more cash into repo); recently up to +15–20bp (Oct 2025) |
| SOFR − IORB > 0 | banks lending reserves in repo |
| EFFR − IORB > 0 | scarce reserves (stronger Fed-action trigger) |
| TGCR − ON RRP, up | excess collateral |
| GCF − tri-party | dealer balance-sheet capacity |
| SOFR − TGCR | SOFR composition and DVP/clearing effects; heavy specials can drag SOFR lower |

Separate funding demand (hedge funds, collateral) from reserve scarcity (EFFR − IORB, reserves/assets); rising repo can be demand-driven while reserves are ample.

## 8. Long-end SOFR-FF and discounting

- Long-end basis slope is driven by (a) liability hedgers, (b) asset hedgers, (c) **discounting-risk hedgers**, not by fixings. A negative-PV swap discounted on FF-OIS gains PV
  when FF-OIS rises vs the swap rate; holders are effectively long FF/Libor (now FF/SOFR) narrowing, hedged with the basis widener sized by duration and PV.
- Dealer book (2020): bilateral = 15% of gross notional but about half of gross market value; net about $80mn/bp long-end FF/Libor basis risk, clustered > 10y
  (legacy SPVs $260mn/bp, non-CSA corporates $106mn/bp). Falling rates increase negative PV of paid positions, so dealers buy long-end basis in a rally (JPM, Bills, Bonds, and basis...oh my, 7 Feb 2020).
- **CCP discounting switch** (cleared at CME and LCH, 16–19 Oct 2020): cash compensation plus mandatory EFFR/SOFR basis swaps at 2/5/10/15/20/30y restore the original discounting
  risk; the transition curve used 1M and 3M futures to 2y, then FF-SOFR basis swaps 3–50y. The 30y basis last traded above 8bp at the switch (Clarus, Spreadovers vs SOFR, 23 Sep 2020);
  netting a $5mn vs $2mn DV01 cut realised bid/ask from 1.0bp to 0.4bp (CME, SOFR Discounting Transition, 2 Jun 2020). Forced one-directional hedging creates predictable flow.
- The 30y basis at about 5bp in Oct 2020 implied overnight reserves of about $12.5tn, so it was "a bit wide" to overnight fundamentals but kept up by LDI/discounting demand.
- FF/SOFR term structure (Mar 2019): negative at short maturities, positive at long.
- 2y swap spread ≈ 3m OIS/GC funding spread + 2y SOFR/FF basis (fit slope 1.0, R² 0.81) (Citi, Short-End Notes, Aug 2026).

## 9. Dated trade views (historical; levels restated in rate terms)

| Date | View | Restated | Source |
|---|---|---|---|
| 27 Jun 2025 | short Oct-25 desk "SOFR/FF" at −4, target −8, stop −1 | long realised basis +4 → +8, stop +1 | BofA, Funding & debt limit |
| 30 Jun 2025 | short Jul-25 at +1, target −2, stop +2.5 (FF − SOFR) | long realised basis −1 → +2, stop −2.5 | BofA, Short July SOFR/FF |
| 6 Oct 2025 | long Jan-26 at −6.5, target −2, stop −11 | short realised basis +6.5 → +2, stop +11 | BofA, FHLB liquidity |
| 20–22 Oct 2025 | stay long Jan-26 at −8; Fed bill backfill about $150bn at $50–100bn/month | realised +8 | BofA, Repo jump; Bill demand gap |
| 3 Oct 2025 | short realised basis around year-end with QT end as catalyst | realised +9 at the time | Conks, Takeoff Begins |
| 1 Mar 2026 | Sep–Nov-26 months about 4.5bp realised judged too wide vs front-year about 3bp; risk a hawkish Chair restarting QT | short realised basis, those months | Conks, Nothing Ever Happens |

Historical P&L on index-basis structures (JPM, Feb–Mar 2020): long 3M SOFR vs FF contracts at $50k/bp each from 0.5bp, −4.0bp; long 10y SOFR/FF basis at 1.625bp, +0.2, +0.4, −1.8bp
over three weeks; FRA/OIS curve steepener exited −17.2bp in the March 2020 stress. Lesson: stop out on a volatility regime shift (JPM, Impossible to walk in this muck, 6 Mar 2020).
