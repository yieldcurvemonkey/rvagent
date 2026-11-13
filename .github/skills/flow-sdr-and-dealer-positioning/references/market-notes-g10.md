# G10 market notes for swap flow and dealer positioning

Companion to `SKILL.md`. Numbers are from the cited sources and carry their sample dates. Most are
2010 to 2016 samples, pre-cap or pre-SEF-mandate in part. Re-estimate before use.

## Summary by market

| Market | Flow sources in practice | Key differences | Thresholds to re-check |
|---|---|---|---|
| USD | US-nexus SDR prints, SEF and CCP data | Largest IRS market; CME-LCH basis and CCP switches; spreadovers; swaptions mostly off-venue; IMM roll | Block cap about USD 110k DV01 (2015 estimate, re-estimate); spreadover share on SEF |
| EUR | SDR prints (US-nexus only), venue data, ECB-day intraday flow | Bund futures drive 8y-9y activity; Eurex clearing labels; desk location distorts volume | Desk-location effect; 5/10/30y share of DV01 |
| GBP | SDR prints; asset-swap structures | Gilt maturities in swap prints identify synthetic floaters; short sterling | Gilt maturity matches |
| JPY | Official intervention via custody and repo data | Offsetting is front-loaded (MOR falls to 0.3 at 8h); JGB net of central bank | MOR window profile |
| CAD, AUD, NZD, CHF, SEK, NOK | No SDR flow analysis in the sources | CAD early termination valued same day; AUD AFMA discounting for FRAs | None sourced; test first |

## USD

- 2010 IRS: 609 trades and USD 86bn per day; OIS USD 30bn; FRA USD 27bn. 98% 3m Libor; 91% semi-annual fixed. IRS HHI 475; 4-firm share 32% (Fleming et al., NY Fed Staff Report 557, Mar 2012).
- SEF share rose from about 60% (Oct 2013) to over 80% (Sep 2014); mean 48%. Liquidity gains largest in USD (Benos et al., Bank of England Staff WP 580, Jul 2016).
- Spreadovers: about 89% on-SEF after the mandate of 15 June 2014. Average DV01 traded in spreadovers in 2015 about USD 8.1m per day, about 15% of daily risk; peak USD 16.7m on 19 Mar 2015 (Clarus, Mechanics and Definitions of Spreadovers, May 2015).
- CME-LCH basis: pay at LCH, receive at CME in the 2015 term structure; 28 Mar 2016 mid 0.95bp at 5y, 1.75bp at 10y (Clarus, CME-LCH Basis, May 2015; Clarus, Identifying CCP Basis Trades, Mar 2016).
- Invoice spreads vs CME Treasury futures (TU, FV, TY, US, UL) in 2014: delivery dates 3 Oct and 6 Jan for 2y and 5y, 30 Sep and 31 Dec for 10y, Bond and Ultra. Exact matching is a floor (Clarus, Invoice Spreads, Sep 2014).
- USD IRS 2024 mix: customer-to-dealer and SEF compression; DV01 and trade counts both used for size (Clarus, SOFR Swap SEF Volumes, Jun 2024).
- Swaption flow is mostly off-venue; high-strike payer demand persisted into 2026 (Morgan Stanley, Jul 2026).
- April 2025 swap-spread sell-off: SLR-change positioning and Treasury credit worries were cited (Clarus, Swapalypse Now, Apr 2025).

## EUR

- 2010 IRS: 499 trades and USD 79bn per day; OIS USD 144bn (no liquid listed EUR OIS; Eonia futures about USD 440mn). 85% 6m Euribor, annual fixed (Fleming et al., Mar 2012).
- SEF share 20 to 40% (mean 20%); about 80% of EUR volume is non-US to non-US (Benos et al., Jul 2016).
- The US-to-non-US share of EUR volume fell from about 20% to 5% after SEFs, through inter-dealer trades moving to non-US desks, without any change in who trades. USD was unaffected (Benos et al., Jul 2016).
- ECB policy days: the peak sits in the 16:00-16:15 CET slot at more than 3x the average slot. On 5 June 2014 the peak (8.5x average) came about two hours into the press conference. Telegraphed policy means low volume at the announcement and repositioning late in the day and the day after (Clarus, ECB June Meeting, Jun 2014).
- Swap DV01 by tenor, June 2014: 10y EUR 23.6% of desk DV01, USD 25.7%; 5y EUR 18.4%, USD 22.9%; 5, 10 and 30y were 62-64% of each market (Clarus, Principals of Swap Trading, Jul 2014). Desk DV01 was USD 1,133m against EUR 321m, which is a reporting bias: only US persons were guaranteed to report.
- Long-end pension and insurer receiving: the EUR 10-30y swap-spread curve was flat at the start of 2020, dived in March 2020 and recovered about 75% by December 2020 (Quantitative Finance Stack Exchange, Dec 2020, read as a practitioner discussion; a weak source).
- June 2008: a 2s30s structured-note event forced dealers to sell the curve and buy short-tail vol at once (Merrill Lynch RateLab, Jun 2008).
- EGB stress (OAT, BTP) spills into USD spreads through stops (Goldman Sachs, cuRated, Oct 2026).

## GBP

- 2010 IRS: 168 trades and USD 15bn per day; OIS 31 trades and USD 79bn. 87% 6m, 85% semi-annual fixed. Offset ratio 0.6 at 30m. Liquid hedges: medium-long government bond futures (Fleming et al., Mar 2012).
- Gilt maturity dates in GBP swap prints help identify synthetic floating-rate notes; the match is "particularly fruitful" in the source (Clarus, Mechanics of Asset Swaps and Government Bond Swap Spreads, May 2015).
- Short sterling volume exceeded Euribor on 11 days in June 2016 around the Brexit vote (Clarus, Mechanics and Definitions of STIR Futures, Jul 2016).
- Desk gilt supply about USD 2mn/bp in the week of Oct 2026, 0.4x the average (Goldman Sachs, Oct 2026).

## JPY

- 2010 IRS: 222 trades and USD 34bn per day; HHI 625, the most concentrated of the sampled markets; 4-firm share 39% (Fleming et al., Mar 2012).
- Offsetting is front-loaded: MOR 0.7 at 30m falling to 0.3 at 8h (Fleming et al., Mar 2012).
- Official intervention: the Ministry of Finance sold an estimated USD 46bn of USTs in May 2024. Custody holdings fell USD 34bn in three weeks and deposits of USD 135bn sat mostly in the central bank's foreign repo pool. Track custody holdings and the foreign repo pool together; they move in opposite directions as official accounts shift between securities and cash (BofA Global Research, FX intervention primer, Jul 2024).
- Desk JGB supply about USD 20mn/bp net of the central bank in Oct 2026, 2x the average (Goldman Sachs, Oct 2026). Japanese bond identifiers do not derive from short codes; use the reference table.

## CAD, AUD, NZD, CHF, SEK, NOK

- No SDR flow analysis in the sources. AUD and NZD appear only in trade-idea examples.
- CAD: CDOR-based basis with its own minimum size and increments; early termination valued same day (tpSEF Rulebook, May 2021).
- AUD: AFMA yield discounting for FRAs differs from ISDA discounting elsewhere (tpSEF Rulebook, May 2021).
- NZD and CHF appear only in FX-option sentiment work (BofA, Feb 2021). Do not transfer those results to rates flow.

## Cross-market

- Hedge-fund and real-money spread longs are crowded in the futures invoice. EGB stress feeds USD spreads through stops (Goldman Sachs, Oct 2026).
- Dealer skew: quote skews can reflect inventory, not views. Check inventory first (O'Hara, Market Microstructure Theory, 1995; partial read, equity-focused; rates mapping is an inference).
- FRN auction cycle: dealer FRN volume about USD 2.6bn per day (0.5% of Treasury trading); net dealer FRN position about USD 4.5bn; the newest-FRN volume in auction week is more than twice any other week (Federal Reserve Bank of New York, Liberty Street Economics, Mar 2018).
