---
name: <prefix>-<short-name>
description: <One or two sentences on WHAT this does. Then "Use when ..." with the trigger words a trader would type (instrument names, structures, metrics). Max 1024 chars.>
---

# <Title>

<2–4 sentence summary: the RV idea, why it exists (mechanism), when it pays.>

## When to use
- <question or situation that should trigger this skill>
- <...>

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| <e.g. par OIS swap rates 1y–30y> | `curve_par` | daily close, ≥ 3y | bp or % stated |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values.

## Method
1. <step, with formula written out, e.g. `fly = 2·y5 − y2 − y10`>
2. <step, with the default parameter and the reason for it (lookback, window, weights)>
3. <...>

## Worked example
<Numbers from a cited reference or a clearly labelled illustrative example. Cite inline: "(Publisher, Title, Date)".>

## Signals & interpretation
- <threshold / rule → action; what rich or cheap means here>
- <confirmation checks>

## Pitfalls
- <data, model, regime, liquidity, convention traps>

## Output
<Exactly what to return: table columns, chart(s), and the hand-off to rv-trade-idea-writeup.>

## Scripts
- [`scripts/<tool>.py`](scripts/<tool>.py): <what it computes>. `python scripts/<tool>.py --help`. `--selftest` checks a known case.

## Related skills
- [<other-skill>](../<other-skill>/SKILL.md): <why>

## References
- <Author/Publisher> - <Title> (<edition or series>, <date>): <what it contributes>
- <Public paper or book> (external): <what it contributes>
