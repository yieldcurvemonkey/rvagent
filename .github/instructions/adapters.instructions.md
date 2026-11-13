---
applyTo: 'adapters/**'
description: Rules for data/pricing adapters that connect the agent to a specific infrastructure
---
- Adapters are the only place where vendor, terminal, database or internal-library specifics may appear.
- Implement the interface and emit the canonical tables defined in
  `.github/skills/data-contract-and-adapters/SKILL.md`, with exact column names, units (bp, %, price), and dtypes.
- Read credentials from environment variables or the vendor SDK's own auth. Never hard-code or log secrets.
- Make adapters idempotent and point-in-time. Record the snap time and source in each table's metadata.
- Validate output with the contract validator before any skill consumes it.
