# adapters/

The only place for infrastructure-specific code: vendor SDKs, terminal APIs, databases, internal pricing libraries.

Each adapter implements the interface in `.github/skills/data-contract-and-adapters/` and writes canonical
tables to `data/`. Skills consume only those tables, so swapping data vendors never touches a skill.
Ask the `rv-data-engineer` agent to build one for your source.
