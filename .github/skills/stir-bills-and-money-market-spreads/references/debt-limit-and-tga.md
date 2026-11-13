# Debt limit, X-date and TGA rebuild: detail

Companion to `SKILL.md` section 7. Figures are as printed in the cited notes. Units: $bn unless stated. Sign
conventions are stated where they matter. Chart-read levels are approximate.

## 1. Mechanics and sequence

- The limit binds. Treasury keeps coupons on schedule, cuts bills, uses extraordinary measures (EM), and runs down
  the TGA. Bill paydowns suppress front-end yields, and MMFs move cash from ON RRP into non-Fed repo or bills
  (BofA, May 2025; Conks, May 2025).
- Suspension expiry: Treasury may hold a "business as usual" balance (5-7 days of outflows) rather than the level
  at suspension (Barclays, Jan 2025).
- Resolution: heavy bill issuance rebuilds the TGA, draining ON RRP first and reserves second. Repo and SOFR rise
  against IORB and EFFR (BofA, Jun 2025; Conks, Jan 2025).
- Reserve levels are misleading while the TGA is moving. A TGA rebuild lowers reserves one-for-one; a TGA drawdown
  raises them, and the "liquidity mirage" overstates ampleness during the drawdown (Conks, Jan 2025).

## 2. X-date inventory (BofA, Feb 2025)

Extraordinary-measures inventory ($mn):
- Two months of EM: total 336,600 (G-Fund 299,000; ESF 20,000; CSRDF and PSRHBF 17,600).
- Eight months through August: total 536,400 (G-Fund 299,000; ESF 20,000; CSRDF and PSRHBF 70,400; one-time
  30 June measure 147,000).
- $132bn of EM had been used by 29 Jan 2025, and the limit had bound since 21 Jan.

X-date moved from 15 Aug to 29 Aug 2025 after the February refunding estimates and a higher January TGA. BofA
treated anything after 15 Aug as high risk.

Financing identity used for the bill line (BofA, Feb 2025):
- Total (4) = marketable borrowing (2) + other sources (3); change in cash (5) = (4) - financing need (1).
- Marketable borrowing (4) = need + change in TGA - other sources.
- Net bills to the public = net bills + Fed bill maturities; net supply = net bills + net coupons.

Quarterly financing, 2025 (BofA, Feb 2025): Jan-Mar need 520, borrowing 815, other -166, total 649, change in cash
128, end-quarter cash 850, SOMA redemptions -75. Apr-Jun need -20 (tax surplus), borrowing 123, other -144, change
in cash 0, end-quarter cash 850, SOMA -75.

Monthly 2025 path (BofA, Feb 2025; TGA end of period / net bills / net supply):

| Month | TGA | Net bills | Net supply |
|---|---|---|---|
| Jan | 793 | 193 | 265 |
| Feb | 650 | -22 | 125 |
| Mar | 500 | -134 | 73 |
| Apr | 650 | -171 | -61 |
| May | 450 | -180 | 7 |
| Jun | 375 | -230 | -17 |
| Jul | 180 | -76 | 46 |
| Aug | 350 | 363 | 532 |
| Sep | 650 | 97 | 288 |
| Oct | 850 | 313 | 396 |
| Nov | 875 | 319 | 471 |
| Dec | 900 | -101 | 86 |

The path assumes resolution in late July and QT ending in September. Calendar-2025 bill supply was forecast at
about $380bn, with more than $800bn of paydowns from February to end-July and almost $1tn from August to December.
Cumulative bill supply bottomed near -$620bn in July 2025 (BofA, Feb 2025).

Other X-date estimates in the same period: Conks put it near mid-August 2025 (Conks, May 2025 and Apr 2025). The
Treasury warned cash plus EM would run out by August (Conks, Jun 2025).

## 3. Bills outstanding around debt-limit episodes (BofA, Jun 2025)

| Episode | 6 months before | 6 months after | Change |
|---|---|---|---|
| 2017 | 1,750 | 2,266 | +29% |
| 2019 | 2,358 | 2,474 | +5% |
| 2023 | 3,915 | 5,838 | +49% |
| 2025 (projection) | 6,380 | 6,497 | +2% |

ON RRP over the 2017 episode fell from 233 to 3 (6 months). The 2025 projection took it from 143 to 80 (1m) and
then to zero.

## 4. Resolution-day averages and the event-study method (BofA, Jun 2025; Jul 2025)

Average market changes after the 2017, 2018 and 2019 resolutions, at horizons 1m / 3m / 6m after resolution
(Exhibit 4 signs: SOFR-FF is FF less SOFR; bill-OIS is OIS less bill, so negative = bills cheap; the SOFR-FF row
averages out across the three years per horizon, which confirms the layout):
- SOFR-FF: -7.7 / -4.4 / -5.1 (2018: -10.0 / -11.7 / -7.7; 2019: -14.8 / -1.0 / 2.1; 2017: 1.9 / -0.4 / -9.6).
- SOFR-IORB: +3.0 / +5.1 / +5.7 (2018: +10.5 / +15.0 / +12.4).
- 1m bill-OIS: -7.5 / -4.0 / -9.3 (2019 at 1m: -13.9).
- 3m bill-OIS: -3.6 / -1.5 / -4.2.
- 2y UST-OIS: +0.5 / -0.8 / +3.5. 5y UST-OIS: -0.1 / +0.2 / +3.3.
- The 2019 3m and 6m values were distorted by Fed intervention after the September 2019 repo stress.

Event-study method:
1. Select episodes by matching state, not by date: (a) how much ON RRP buffer remains; (b) the growth of bills and of
   total Treasury supply. This pairs 2017 and 2018 (five months apart, one episode in the study).
2. Exclude 2021 and 2023 as analogs, because excess liquidity was huge then.
3. Average 1m, 3m and 6m changes after resolution with a 1-month moving average over each window.
4. Study 2019 separately as a funding-stress analog, and note that Fed action truncated it.

Resulting 2025 forecast (BofA, Jul 2025, roughly $850bn of bills July-November): SOFR up vs IORB by 5-12bp;
SOFR-FF tighter by 4-8bp; 3m bill minus FF OIS cheaper by 2-4bp; 2y and 5y UST-OIS mixed, biased cheaper.

## 5. TGA rebuild pace (BofA, Jun 2025; BofA, Jul 2025)

Business days after resolution to close X% of the TGA gap (average across 2013-2023 episodes):

| Share of gap closed | Business days |
|---|---|
| 5% | 3 |
| 10% | 5 |
| 20% | 10 |
| 30% | 13 |
| 40% | 21 |
| 50% | 28 |
| 60% | 30 |
| 70% | 31 |
| 80% | 34 |
| 90% | 43 |
| 100% | 51 |

Average share closed after N business days (second table, same episodes): 5 days 19%; 10 days 25%; 15 days 30%; 20
days 49%; 30 days 60%; 50 days 68%; 100 days 106%. The two tables disagree: interpolating the first gives about 39%
at 20 days. Use a range (39-49%) at 20 days.

Dispersion: at 20 days the closure ranged from 0% (2019) to 112% (2017). Recent episodes were slower, so skew to a
slower build. Rule of thumb: about 51 business days to target (BofA, Jul 2025).

Worked (BofA, Jul 2025): a short-July SOFR-FF position was set with July bill supply of $391bn and total UST supply
of $484bn, 19 business days left, about 50% of the TGA gap to rebuild. Entry +1bp, target -2bp, stop +2.5bp, quoted
FF minus SOFR.

2025 TGA path (BofA, Jul 2025): resolution around 4 July; TGA $575bn end-July and $850bn mid-September; implied bill
issuance $234bn in July, $479bn in Q3 and $270bn in Q4. Reserves about $2,946bn in July 2025 falling to about
$2,781bn by March 2026 in that path; ON RRP from $311bn to zero by September 2025. Post-resolution bill wave over
$900bn between August and November to rebuild the TGA (BofA, May 2025).

Quarter-end cash flows 30 June to 1 July 2025 (Citi, Jun 2025): maturing non-marketable -$132bn, coupon cash
+$116bn, 77-day CMB +$60bn, bill paydown -$37bn (net about flat). Up to $250bn of CMBs were available. The 4, 6 and 8
week auctions were cut by $20, $15 and $20bn. July net bills were about $100bn lower.

## 6. Pre-X-date signals (BofA, May 2025; Citi, Feb 2017; Citi, Jun 2025)

- Bills maturing just after the X-date cheapen; coupons with possibly delayed payments cheapen vs neighbours.
- Markets price the risk only about two weeks before the date. Bills cheapen materially 10-15 days ahead.
- GCF repo rises up to about +20bp into prior X-dates, with Treasury-only MMF outflows (they cannot use ON RRP),
  capped at or slightly above the SRF rate.
- The 1m bill-OIS cheapens in the days before. The UST curve fell into the X-date in 3 of 7 episodes. Expect the
  OIS curve to bull-steepen on acute concern.
- MMF AUM falls into the X-date and then reverses. MMFs prefer agency debt, which is not subject to the limit.
- In 2011, 2013 and 2015 the concern surfaced only about two weeks before the X-date (Citi, Feb 2017).
- Kink example (Citi, Jun 2025): the 8-week bill maturing 12 Aug 2025 cleared at 4.38%, the highest of the last four
  auctions.
- 2023 extreme (Barclays, Jan 2025): bills maturing just after the X-date cheapened about 450bp vs those just
  before; 1m bill-OIS swung from about -165bp to +60bp within a month. Treat as a tail case, not a norm.

## 7. Treasury cash guidance and cash management (Citi, Jul 2015; Barclays, Jan 2025; Conks, Nov 2025)

- Daily cash needs can exceed $50bn, so guidance targets a date when it is within $50-100bn of the ceiling.
- Treasury keeps cash above $150bn into the hard ceiling and cuts 1m and 3m bill sizes. In 2015 this produced about
  $135bn of negative net bill issuance in October-November, with interdealer repo at least 5bp lower and more RRP use.
- The cash buffer target is 5-7 days of outflows (Barclays, Jan 2025; Conks, Jul 2025).
- TGA target: about $850bn in 2025; raised to about $900bn (Conks, Nov 2025). A higher TGA means more neutralised
  reserves (trapped settlement balances).

## 8. Sources and uses, 2019 (Citi, Jan 2019)

CQ1 2019: need 397, borrowing 308, other -63, change in cash -152, end-quarter cash 250, SOMA -46. CQ2: need -26,
borrowing 103, other -104, change in cash +25, end-quarter cash 275, SOMA -82. The soft deadline was 1 March (TGA
$200bn). The TU-OIS widener (swap-spread sign, OIS minus Treasury yield, so it profits when front-end Treasuries richen)
opened 14 Dec 2018 at -20bp and was closed 17 Jan 2019 at -16.2bp for about +$210k. Citi took profits because bill
issuance rose earlier than expected, which works against a widener.

## 9. The 2027 setup (Citi, Oct 2026; Citi, Aug 2026)

- Limit $41.1tn vs about $39.9tn subject to it. Headroom is quoted as $1.12tn (Citi, Oct 2026) and $1.24tn (Citi,
  Aug 2026), a difference of vintage. Binds in Q1 or Q2 2027; extraordinary measures of about $450bn from May 2027;
  X-date likely Q4 2027.
- Net bill supply about $100bn in the first ten months of 2027, vs $470bn through October 2026. Reserves rise about
  $700bn over the same window. Private bills about $9tn by end-2028.
- Private bills minus reserves: local low of about $3tn by October 2027, with SOFR below IORB through 2027, and up
  to $4tn as soon as December 2027.
- Offsets: piecemeal suspensions (the 2017 two-month precedent), LCR reform cutting reserve demand by $200-600bn, and
  MMF and bank growth.
- Expected 1y spread cheapening of 5-10bp in Q3 and Q4 2027, with the Fed able to buy bills to anchor (Citi, Oct 2026).
- Citi Aug 2026 forecast table (Aug 2026 and Dec 2026, $bn): TGA 950 and 850; private bills 6,715 and 6,849; reserves
  2,953 and 3,032; private bills minus reserves 3,762 and 3,817.

## 10. Resolution analogs: per-year detail, 2019 regimes and supply conditioning (BofA, Funding & debt limit, 27 Jun 2025)

Per-year averages after resolution at 1m / 3m / 6m, in bp, signs as printed in the source's Exhibit 4 (SOFR-FF is FF
less SOFR; bill-OIS is OIS less bill; UST-OIS is OIS less Treasury yield). The average row is in section 4.

| Series | 2017 | 2018 | 2019 | Average |
|---|---|---|---|---|
| SOFR-FF (FF less SOFR) | 1.9 / -0.4 / -9.6 | -10.0 / -11.7 / -7.7 | -14.8 / -1.0 / 2.1 | -7.7 / -4.4 / -5.1 |
| SOFR-IORB | -2.0 / 0.7 / 11.2 | 10.5 / 15.0 / 12.4 | 0.7 / -0.5 / -6.4 | 3.0 / 5.1 / 5.7 |

Read 2017 and 2018 as one long episode (five months apart) and 2019 as the funding-stress analog. The spread across
years is wide (SOFR-FF 1m ranges from +1.9 to -14.8), so quote the average as a floor on the move, not a point
forecast.

**2019 stress regimes (Exhibit 5, bp).** Averages over three windows: pre-stress (end-April to end-July 2019), peak
stress (end-July to end-September) and normalisation (end-September 2019 to end-January 2020).

| Series | Pre | Peak stress | Normalisation |
|---|---|---|---|
| 3m bill-OIS | -1.2 | -8.6 | 0.2 |
| SOFR-IORB | 7.2 | 15.1 | 2.1 |
| SOFR-FF (SOFR less FF) | 3.1 | 10.6 | 1.2 |

Applied to June 2025 levels, the source sized the move from the current average to each regime (current level, move to
normalisation, move to peak stress): 3m bill-OIS -1.6, +1.8, -7.0; SOFR-IORB -10.0, +12.0, +25.1; SOFR-FF -2.8, +3.9,
+13.4. Each regime value equals the current level plus the move (for example -10.0 + 25.1 = 15.1), so the table is
internally consistent. Sign check: the printed label for the 3m bill row reads bill less OIS, but a stress value of
-8.6 only makes sense as OIS less bill (negative = bills cheap), the same sign as Exhibit 4. Treat that row as
OIS less bill and state it. In the repo convention (bill minus OIS, positive = cheap) the three values flip to +1.2,
+8.6 and -0.2.

Rule of thumb from the table: peak stress meant SOFR-IORB about +15bp and SOFR-FF about +10bp over a two-month
window, then a return to roughly +2bp and +1bp. That is the upper bound for a Fed-intervention-free squeeze, not a base
case.

**Supply conditioning.** The analogs were chosen because bill and total Treasury supply grew by a similar percentage
and the ON RRP buffer was small. Percentage change in bills outstanding at 1m / 3m / 6m after resolution: 2017
1 / 8 / 29; 2019 4 / 3 / 5; 2023 11 / 25 / 49; 2025 projection 6 / 6 / 2. Total marketable debt, 2025 projection:
+2 / +4 / +5. ON RRP ($bn): 2017 96 one month before resolution and 120 one month after; 2019 near zero; 2023 2,218 to
1,910; 2025 projection 143 to 80 at 1m and 138 to zero at 3m. Bills outstanding were about $5.8-6.5tn in 2025. 2023
is not a usable analog: bills grew 49% into a $2tn RRP buffer.

**Expression and timing of the resolution trade.**
- Prefer an outright SOFR-FF short to a SOFR-FF curve trade. The whole curve should cheapen as SOFR moves up, and a Fed
  liquidity add (ending QT, buying bills) that could anchor later dates is hard to time, so a curve spread can lose to
  a Fed response that the outright expresses more cleanly.
- SOFR leads and EFFR follows with a lag. The market belief that EFFR will not move is wrong in the analogs.
- Use the historical minimum as the entry case: the event study implied at least 4-5bp of further SOFR-FF tightening
  from the June 2025 level, and the outright keeps the option on a larger SOFR spike.
- A quarter-end inside the contract window adds convexity to the position. The Q2 2025 quarter-end SOFR jump on a low
  TGA supported the October contract. Check which fixings the contract averages before relying on a quarter-end.
- Time the trade against the risk that resolution comes before the base case: the source entered in late June because
  passage in early July was a live risk against a late-July or early-August base case.

## Sources for this file
- BofA Global Research - US Rates Watch: Funding & debt limit: history lessons (Mark Cabana, Katie Craig, 27 Jun 2025).
- BofA Global Research - US Rates Viewpoint: Debt limit FAQ: spring 2025 update (Mark Cabana, Katie Craig, Ralph Axel, 12 May 2025).
- BofA Global Research - US Rates Viewpoint: Lower UST WAM => backdoor easing (Meghan Swiber, Mark Cabana, Katie Craig, 2 Jul 2025).
- BofA Global Research - US Rates Alpha: Short July SOFR/FF: debt limit => bills (Mark Cabana, Katie Craig, 30 Jun 2025).
- BofA Global Research - US Rates Watch: X-date shift: now late August, risks earlier (Katie Craig, Mark Cabana, 7 Feb 2025).
- Barclays FICC Research - US short interest rate primer (Joseph Abate, Jan 2025).
- Citi Research - US Rates Weekly: Summer lull (Mathai et al., 17 Jul 2015); The rocky road to a steeper curve (Mathai et al., 18 Jan 2019); Going nuclear (on the curve) (Mathai et al., 3 Feb 2017).
- Citi Research - Short-End Notes: SOFR/FF to go negative in Q3/Q4 (Vazquez Plata, Williams, 13 Jun 2025); SOFR/FF spiking into quarter-end (Vazquez Plata, Williams, 27 Jun 2025).
- Citi Research - US Rates Weekly: OAT of the blue (Williams et al., 2 Oct 2026); Pension plan for 20s? (Williams et al., 9 Oct 2026); Can Secretary Bessent and Chair Warsh save the curve? (Williams et al., 21 Aug 2026).
- Conks (Monetary Mechanics, Substack) - Plumbing Notes: The Money Market Blindspot Part I (23 Jan 2025); Money Market Update (19 May 2025, 2 Jun 2025); The Post-QT Era (24 Nov 2025); Collateral Damage (18 Apr 2023).
