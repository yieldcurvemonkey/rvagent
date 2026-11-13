---
name: eng-skill-authoring
description: How to add a new skill (technique, strategy, workflow, model) to this G10 rates RV agent so Copilot discovers and uses it. Covers folder naming and category prefixes, frontmatter rules, writing a description that routes correctly, data-agnostic inputs, bundled scripts with self-tests, references, and validation. Use when asked to add, extend, split, rename or review a skill, or when a request falls outside the existing skills.
argument-hint: "<what the new skill should cover>"
---

# Authoring a skill

Skills are how this agent learns new techniques. Each skill is one folder under `.github/skills/` with a
`SKILL.md`. Copilot reads only the `name` and `description` of every skill to decide relevance, then loads the body,
and loads bundled files only when the body links to them. A skill is therefore modular: add a folder and the agent
picks it up; delete a folder and nothing else breaks.

## When to use
- "Add a skill for <technique>" / "teach the agent <strategy>" / "turn this research note into a reusable method".
- A request repeatedly needs know-how that no existing skill covers.
- An existing skill has grown past one coherent method. Split it.

## Rules (enforced by `tools/check_skills.py`)

| Rule | Detail |
|---|---|
| Location | `.github/skills/<name>/SKILL.md`, one level deep (nested category folders are not discovered) |
| `name` | equals the folder name; lowercase letters, digits, single hyphens; ≤ 64 chars |
| Category prefix | `rv-` workflows · `fi-` fundamentals · `curve-` · `bond-` · `spread-` · `fut-` · `stir-` · `xccy-` · `vol-` · `infl-` · `macro-` · `flow-` · `quant-` · `ml-` · `bt-` · `port-` · `data-` · `eng-` |
| `description` | ≤ 1024 chars: what it does + "Use when …" + trigger words (instrument names, structures, metrics) |
| Optional keys | `argument-hint` (slash-command hint), `user-invocable: false` (hide from `/` menu), `disable-model-invocation: true` (only via `/`) |
| References | `## References` with ≥ 1 bullet; cite title, author or publisher, and date. **No file paths or download file names.** |
| Agnostic | No vendor APIs, terminal functions, tickers or internal libraries outside `## References`. Inputs are canonical tables from [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). |
| Links | Relative links (`../other-skill/SKILL.md`, `scripts/x.py`) must resolve |
| Scripts | Every `scripts/*.py` supports `--selftest`, which must pass |

## Method

1. **Check for overlap.** Read `docs/skill-catalog.md`. Extend an existing skill if the new material is a variant
   of its method. Create a new skill if it needs different inputs, outputs or decision rules.
2. **Name it.** Use `<prefix>-<what-it-is>`, e.g. `curve-butterflies`, `fut-calendar-roll`. Pick a noun phrase
   over a verb, and don't put the market in the name unless the method is market-specific
   (e.g. `fut-eurex-ctd` only if Eurex mechanics differ materially).
3. **Write the description first.** It is the routing key. Test it by asking: would a trader's phrasing
   ("is 5s30s cheap vs PCA?", "CTD switch risk in WN") match words in it? Include synonyms (fly/butterfly,
   ASW/asset swap, basis/net basis).
4. **Copy the template** [assets/SKILL_TEMPLATE.md](assets/SKILL_TEMPLATE.md) and fill each section:
   - *Inputs*: canonical table names, granularity and history needed. If a new data field is required, propose a
     contract change in `data-contract-and-adapters` rather than reading a vendor field directly.
   - *Method*: formulas written out, defaults with rationale, sign and unit conventions.
   - *Worked example*: real numbers from a cited source, or clearly labelled illustrative numbers.
   - *Pitfalls* and *Output*: be specific.
5. **Bundle code only when computation is the core of the skill.** Scripts must be self-contained (numpy, pandas,
   scipy; optional statsmodels, scikit-learn, matplotlib, guarded), take canonical tables or pandas objects, and
   expose `--selftest` against a case with a known answer (an analytic value, or a simulation with known
   parameters). Keep long reference material in `references/*.md` and link it from the body (progressive
   disclosure).
6. **Cross-link.** Add the new skill to *Related skills* of its neighbours, and theirs to it.
7. **Validate.** Run `python tools/check_skills.py --catalog` and fix all errors. Then ask the agent a question
   that should trigger the skill and confirm it loads (the chat References list shows which skills were used).

## Writing for an agent reader
- Lead with decisions and numbers, not history. The agent needs *what to compute, how, and what it means*.
- Put defaults inline with the reason ("60-day z-score: one quarter, short enough to track regime changes").
- State the failure modes as tests the agent can run ("if the hedge ratio's 1y rolling β drifts > 30%, the fly is
  not stable; re-weight").
- Keep a single skill to one coherent method. Workflows (`rv-*`) orchestrate other skills by linking them.

## Pitfalls
- Vague descriptions ("helps with rates") never get routed.
- Names that don't match the folder fail **silently**: the skill just never appears.
- Files that are not linked from `SKILL.md` are never loaded.
- Citing a document you did not read, or a file path, breaks provenance. The validator rejects paths.
- Hard-coding a vendor field "just for now" couples every user to that vendor.

## Output
A new or updated skill folder that passes `tools/check_skills.py`, an updated `docs/skill-catalog.md`, and
reciprocal links in related skills.

## Related skills
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical inputs every skill declares
- [eng-python-analytics-stack](../eng-python-analytics-stack/SKILL.md): coding conventions for bundled scripts
- [rv-research-digest](../rv-research-digest/SKILL.md): turning a research note into a candidate skill

## References
- Visual Studio Code documentation - "Use Agent Skills in VS Code" (code.visualstudio.com, 2026) (external): skill locations, frontmatter fields, progressive loading
- Visual Studio Code documentation - "Custom agents" and "Custom agent file reference" (2026) (external): agent files, tool aliases, harness differences
- Visual Studio Code documentation - "Use custom instructions in VS Code" (2026) (external): `copilot-instructions.md` and `*.instructions.md` with `applyTo`
- Agent Skills open specification (agentskills.io) (external): SKILL.md format shared across agent harnesses
