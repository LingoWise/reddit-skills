# reddit-validator multi-runtime skill package

## Goal

Produce `dist/reddit-validator.zip` containing a `reddit-validator/` folder. The package is a runtime-agnostic skill contract plus per-runtime tool guides, suitable for Claude and Devin.

## Package layout

```
reddit-validator/
├── SKILL.md
├── requirements.txt
└── resources/
    ├── DEVIN.md
    ├── CLAUDE.md
    ├── param-matrix.md
    ├── failure-recovery.md
    └── report-anatomy.md
```

## SKILL.md (runtime-agnostic core)

Frontmatter:

- `name: reddit-validator`
- `description: Use when the user wants to validate a business idea, product, or niche using Reddit discussions and get a scored HTML report.`
- `dependencies: python>=3.10, playwright, openai`

Body:

- Overview
- When to use (trigger phrases)
- When not to use
- Prerequisites (`.env` keys, Python version, installed deps)
- High-level Phase 0–5 workflow, using generic commands like `python "<skill_dir>/scripts/preflight.py"` without Devin-specific tool names
- Reference list: runtime guides and reference resources

## Runtime overlays

- `resources/DEVIN.md` — exact Devin tool calls: `Bash` with `run_in_background`, `TaskOutput` polling, `AskUserQuestion`, etc.
- `resources/CLAUDE.md` — exact Claude Code tool calls: `Bash`, `Read`, and how to handle background/polling or ask the user.

## Reference resources

- `resources/param-matrix.md` — fast / standard / deep profile parameters.
- `resources/failure-recovery.md` — error codes and fixes.
- `resources/report-anatomy.md` — explains each section of the HTML report.

## requirements.txt

Minimal dependency list matching the README stack:

```
playwright
openai
python-dotenv
praw
jinja2
```

## Packaging

- Build `dist/reddit-validator.zip` from the prepared `reddit-validator/` folder.
- The ZIP root must be the `reddit-validator/` folder, not loose files.
- Verify by listing archive contents.

## Out of scope

The actual Python `pipeline/` and `scripts/*.py` code. This package is the skill contract and runtime guides; the executable pipeline can be added in a later implementation pass.
