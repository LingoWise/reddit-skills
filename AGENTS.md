# Agent notes for reddit-skills

## Project

A modular collection of Reddit operation skills for AI agents. Each skill is a self-contained folder under `skills/<skill-name>/` with a `SKILL.md` contract, `requirements.txt`, optional `resources/` guides, and a Python `pipeline/` + `scripts/` implementation.

## reddit-validator

The first skill. It validates a business idea by scraping Reddit discussions and producing a scored HTML report via LLM analysis.

### Where it lives

- Source package: `skills/reddit-validator/`
- Devin discovery symlink: `.devin/skills/reddit-validator -> ../../skills/reddit-validator`

### Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -r skills/reddit-validator/requirements.txt
uv pip install pytest  # dev dependency
```

Copy `skills/reddit-validator/.env.example` to `.env` and fill in the Reddit script-app credentials. `OPENAI_API_KEY` can come from the Devin / Claude Code runtime; dotenv does not overwrite existing environment variables.

### Run

```bash
python skills/reddit-validator/scripts/preflight.py
python skills/reddit-validator/scripts/run_pipeline.py "your idea" --profile standard
python skills/reddit-validator/scripts/extract_report.py --run-id <run_id>
```

### Test

```bash
python -m pytest
```

### Lint

```bash
cd skills/reddit-validator && npx markdownlint-cli SKILL.md resources/*.md
```

### Runtime notes

- The package-level `.markdownlint.json` disables `MD013` (line length) and `MD060` (table alignment) so the Chinese/English resources and long tables lint cleanly.
- Runtime outputs (`reports/`, `logs/`, `checkpoints/`) are ignored by `.gitignore`.
