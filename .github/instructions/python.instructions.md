---
applyTo: '**/*.py'
description: Conventions for analytics and research Python in this repo
---
- Python 3.11+. Core deps: numpy, pandas, scipy. Optional: statsmodels, scikit-learn, matplotlib, pyarrow. Guard
  optional imports and fail with a clear message.
- rateslib and QuantLib are optional pricing back-ends. rateslib's default licence is non-commercial, so never make
  it a hard requirement.
- Analytics functions take pandas/numpy objects and return pandas objects. I/O lives at the CLI edge. Functions
  never fetch data themselves; inputs are canonical tables (see `data-contract-and-adapters`).
- Units go in names or docstrings: `_bp`, `_pct`, `dv01_ccy`, `vol_bp_ann`. Dates are timezone-naive trade dates
  unless a snap time matters.
- No look-ahead: rolling statistics use only data up to t. Use `shift(1)` before turning a signal into a position.
- Every script bundled in a skill has `--selftest`, which checks a case with a known answer and exits non-zero on
  failure.
- Keep scripts small and self-contained. A skill's scripts must not import from another skill.
