---
applyTo: '.github/skills/**'
description: Rules for authoring and editing agent skills
---
Follow `.github/skills/eng-skill-authoring/SKILL.md`. In short:

- The folder name equals the frontmatter `name`: lowercase, digits and hyphens, at most 64 chars, with a category
  prefix (`rv-`, `fi-`, `curve-`, `bond-`, `spread-`, `fut-`, `stir-`, `xccy-`, `vol-`, `infl-`, `macro-`,
  `flow-`, `quant-`, `ml-`, `bt-`, `port-`, `data-`, `eng-`).
- The `description` (at most 1024 chars) says what the skill does and when to use it, with trigger words.
- The body declares data-agnostic inputs (canonical tables), method with formulas, worked example, signals,
  pitfalls, output, related skills, and `## References`.
- Cite references by title, author or publisher, and date. Never use file paths or download file names.
- Bundled files load only if the body links to them with a relative path.
- Run `python tools/check_skills.py --catalog` after any change.
