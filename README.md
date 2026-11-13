# rvagent: G10 rates relative-value agent for GitHub Copilot

A GitHub Copilot (VS Code) agent that finds, sizes, stresses and documents relative-value opportunities across
G10 fixed income: govt bonds, swaps, bond futures, STIR, basis, swap spreads, cross-market, inflation and rates
vol, in USD, EUR, GBP, JPY, CAD, AUD, NZD, CHF, SEK and NOK.

It is **data-source and pricing-infrastructure agnostic**. Skills declare the canonical tables they need, and
small adapters you own translate your files, database, vendor SDK or internal pricer into those tables.

## Quick start

1. Open this folder in VS Code with GitHub Copilot Chat enabled. Use Agent mode.
2. Pick the **rv-strategist** agent in the chat agent picker. Other agents: `rv-risk-reviewer`,
   `rv-quant-researcher`, `rv-data-engineer`, `rv-skill-author`.
3. Connect data: ask *"@rv-data-engineer build an adapter for my curve exports in X"*, or drop canonical
   CSV/Parquet files into `data/`. The schemas are in
   `.github/skills/data-contract-and-adapters/references/schemas.md`.
4. Ask a question, or invoke a workflow skill from the `/` menu:
   - `/rv-opportunity-scan EUR swaps, 3m horizon`: screen, rank, stress and shortlist
   - `/rv-trade-idea-writeup receive 5y in 2s5s10s EUR fly`: a full trade write-up saved to `ideas/`
   - `/rv-devils-advocate`: an adversarial review of an idea
   - `/rv-research-digest`: turn a research note into testable trades
   - `/rv-trade-monitoring`: re-underwrite open positions

Python 3.11+ with `pip install -r requirements.txt` is needed for the bundled scripts.

## Layout

```
.github/
  copilot-instructions.md        always-on operating rules (conventions, no fabricated data, workflow)
  agents/*.agent.md              custom agents (strategist, risk reviewer, quant researcher, data engineer, skill author)
  instructions/*.instructions.md file-scoped rules (Python, adapters, skills, trade ideas)
  skills/<prefix>-<name>/        one folder per skill: SKILL.md (+ scripts/, references/, assets/)
adapters/                        YOUR infrastructure-specific code (the only place vendor/internal APIs appear)
data/                            canonical tables produced by adapters (git-ignored)
ideas/                           trade write-ups
docs/skill-catalog.md            generated list of all skills
tools/check_skills.py            validator + script self-tests + catalog generator
```

## Skills

Skills load on demand. Copilot reads each skill's `name` and `description`, then pulls in the body and any
linked scripts or references only when relevant. Categories are encoded as name prefixes, because skill folders
are discovered one level deep:

| Prefix | Area |
|---|---|
| `rv-` | workflows: scan, write-up, devil's advocate, research digest, monitoring, scoring, execution |
| `fi-` | fundamentals: G10 conventions, curve construction, DV01 and risk transforms, carry and roll, collateral/XVA, balance-sheet costs |
| `curve-` | PCA, steepeners/flatteners, butterflies, forward grids, conditional trades, term-structure models |
| `bond-` / `spread-` | fitted-curve rich/cheap, supply and cash-flow trading, swap spreads and ASW, cross-market, CCP and tenor basis, sovereign CDS |
| `fut-` | futures basis and implied repo, CTD switch and delivery options, calendar roll, invoice spreads |
| `stir-` / `xccy-` | policy pricing, STIR futures RV, convexity adjustment, repo and funding, CB balance sheet, bills, RFR compounding, STIR option densities, cross-currency basis |
| `vol-` / `infl-` | options RV, gamma/vega P&L, convexity and the long end, basis vs vol, skew and tails, correlation and curve options, structured-flow vega supply, linkers |
| `macro-` / `flow-` | reaction functions, regimes, event risk and prediction markets, CB NLP, fiscal and term premium, energy and inflation, geopolitics, technicals, fair-value models, positioning, SDR flows, MBS convexity, ALM demand |
| `quant-` / `ml-` | z-scores, mean reversion/OU, regression and hedge ratios, cointegration, econometrics, regimes, Bayesian, lead-lag, covariance, signal combination, seasonality, systematic signals, ML models and methodology |
| `bt-` / `port-` | backtest design, validation and overfitting, costs and liquidity, attribution, sizing, portfolio construction, stress tests |
| `data-` / `eng-` | data contract and adapters, data hygiene, Python stack, reporting, skill authoring |

See [docs/skill-catalog.md](docs/skill-catalog.md) for the full list. Each skill ends with a **References**
section citing the research notes, books and papers it was built from, by title, publisher and date.

## Extending

Ask the `rv-skill-author` agent, or follow `.github/skills/eng-skill-authoring/SKILL.md`:

1. Create `.github/skills/<prefix>-<name>/SKILL.md` from `eng-skill-authoring/assets/SKILL_TEMPLATE.md`.
2. Declare inputs as canonical tables, write the method, examples, pitfalls and references, and give any bundled
   script a `--selftest`.
3. Run `python tools/check_skills.py --catalog`.

No registration step is needed: the folder is the registration.

## Harness notes

- Built for the Copilot harness in VS Code. Agents use the Copilot tool aliases (`read`, `edit`, `search`,
  `execute`, `web`, `todo`, `agent`).
- Slash workflows are implemented as user-invocable **skills**, not prompt files. Prompt files and agent handoffs
  run only in the Local harness, which is deprecated (removal is scheduled for February 2027).
- rateslib and QuantLib are optional. rateslib's default licence is non-commercial, so the scripts never require it.
