# G10 market differences for the adversarial review

What is most likely to be hiding behind a "cheap/rich" signal differs by market. Use as a prompt list, then test with
local data. Parent skill: [rv-devils-advocate](../SKILL.md). Statistics from one market do not transfer to another
without a local test (BofA, Technicals Explained, Jan 2025).

## USD
- Treasury futures basis: option value is concentrated in the ultra-long contract (wildcard about 3 ticks; 0.5-1.5 ticks elsewhere; +50-100% in high vol); its implied repo can gap 50-100bp to CTD term repo in delivery months, and optionality distorted repo by 10-30bp in other contracts. Wildcard: invoice frozen at the 3pm ET pit close, CTD liquid until at least 5pm, notice of intent until 8pm (JPM, Special delivery, Dec 2019). Early delivery is rational when the front end is inverted (negative carry).
- Basis size/crowding: levered-fund futures shorts about $590-615bn at peak; asset-manager net longs above $700bn from Nov 2021 are structural (TBAC, Jan 2024; JPM, Mar 2020). Unwinds cheapen Treasuries vs OIS/SOFR and tighten swap spreads.
- Swap spreads load on dealer balance sheet and RWA from repo, not only leverage ratios: swapping reserves for Treasuries does not reduce SLR exposure "even if eSLR were set to 0%" (BofA, US Rates Watch, Jun 2025). The April 2025 swap-spread move was a positioning event (see [cases](cases.md)).
- Front end: SOFR futures gaps (Dec/Apr/Sep fly) are a meeting-hump trade; a chair change alters the front vs back-end response (JWS Macro, Autumn 2025; Central Casting, Jun 2026). Tax-date and debt-ceiling TGA rebuilds test funding markets.

## EUR (DE, FR, IT, ES, NL)
- Constraint-driven spreads: BTP vs OAT can cheapen further if the ECB raises Italian haircuts; Bunds can richen vs Spain if ECB hawkishness drives repo short demand (Huggins & Schaller, 2024, Ch.18). OAT stabilisation trade catalysts: inflation relief from energy or global yields, a credible budget, financial conditions tight enough to move the ECB; the bar for TPI is high (Goldman Sachs, Global Rates Trader, 2 Oct 2026). Stop example: a short 10y OAT credit fly entered at 76.5bp (target 91.5, stop 69) lost 9bp when positioning unwound on budget relief (Citi, Trade Ideas Radar, Aug 2026).
- Futures: small deliverable sets, a fixed delivery day and ex-dividend/benchmark issues mean higher squeeze or fail risk than Treasuries; benchmark switches contaminate histories (Duering, 2021; Burghardt et al., 2005).
- Euribor/STIR spreads stack credit, forward-start and fixing risks (Aikin, 2012; LIBOR-era instruments, map to RFR before reuse). Fixing risk is larger in 3m/6m IBOR-linked basis swaps than in daily-fixed RFR swaps (BIS Quarterly Review, Dec 2025).
- ECB has a sole inflation mandate: a euro-area energy shock can reprice from cuts to hikes (JWS Macro, Iran, Mar 2026).

## GBP
- Gilts trade cheap on average (Burghardt et al., 2005). Politics (leadership, budget) is the main swing factor; a pay 5s30s that relied on a bull steepening failed after a budget (-$113k, Citi, Aug 2026). Check gilt ASW against fiscal headlines before fading.

## JPY
- Liquidity: official-sector buying cut JGB liquidity "to a trickle"; life-insurer target yields set pivots (10s30s about 0.75%/2%, 2010-15) (Huggins & Schaller, 2024; Duering, 2021). Yen OTC turnover rose more than six-fold 2022-2025 (almost all OIS) after YCC ended (BIS, Dec 2025), so histories mix regimes.
- Vol: realised JPY vol regimes (peaks about 80bp at Lehman, 21-22bp at the 2010 QE low, 43bp after the 2011 earthquake) mean realised-vol curve trades depend on BoJ-limited short-end vol; the regime can change. Paying the belly is "just another short vol expression" (JWS Macro, Autumn 2025).
- ASW vs CDS: no-arbitrage threshold is "several dozens of bp" because of capital charges on cross-currency basis and CDS; do not trade the USD ASW < CDS side without quantified adjustments and a hedge for currency weakening after default (Huggins & Schaller, 2024, Ch.16).

## CAD, AUD, NZD
- No local source in the pack for CAD beyond a closed receive trade; apply the generic lenses and test local liquidity (a thin market makes the exit lens binding).
- AUD: RBA hiking with inflation in the mid-3s; AUD 1y1y sold off almost as much as any curve despite low energy CPI weight; receive-the-fade ideas carry dovish-pricing and long-end-demand risks (a receive 1y-forward 2s5s10s fly at 9bp, target -11bp, stop 16bp; Citi, Aug 2026). AUD/NZD OIS about half of swap turnover; bank-bill-type IBORs persist (BIS, Dec 2025).
- NZD: steepest curve vol-adjusted, a carry and roll harvester; neutral-phase trap: wary of receivers when the central bank pauses (JWS Macro, Autumn 2025).

## CHF, SEK, NOK
- CHF: the SARON swap curve was negative over a large range of terms and the forward curve sits below spot beyond about 22y, so carry/roll intuition from other markets breaks (Tuckman & Serrat, 2022, Ch.2). OIS is over 90% of swap turnover in RFR-only currencies (BIS, Dec 2025).
- SEK, NOK: small, energy-exporter or neutral-phase central banks priced little then repriced as data firmed; NOK sold off to cycle wides with low energy CPI weight (JWS Macro, Iran, Mar 2026; Autumn 2025). Neighbour-pair reversal alerts at 1,000-day extremes (SEK/NOK, AUD/NZD) are small-sample signals (Willer & Saunders, 2026).
- All three: liquidity for exit is thinner than USD/EUR; use the days-to-exit test with local ADV, and widen the financing and event scenarios.
