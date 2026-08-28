# Agent notes for reddit-skills

## Project

A modular collection of Reddit operation skills for AI agents. Each skill is a self-contained folder under `skills/<skill-name>/` with a `SKILL.md` contract, `requirements.txt`, optional `resources/` guides, and a Python `pipeline/` + `scripts/` implementation.

## Shared libraries

Cross-skill code lives in `src/common/` at the project root. Skills load these modules via `importlib.util.spec_from_file_location` with a path relative to `__file__` (same pattern used for sibling-skill imports like `reddit-auth`).

### src/common/llm.py

Shared LLM client. Reads `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENROUTER_MODEL` from the shell environment.

- `client()` — returns an `OpenAI` client.
- `model()` — returns the model name for the active provider.
- `available()` — `(ok, message)` check for preflight.
- `chat_json(messages, model_name=None, temperature=0.2, client_obj=None)` — call the LLM and return parsed JSON (strips markdown fences).

To use from a skill:

```python
import importlib.util
from pathlib import Path

def _load_llm():
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    llm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llm)
    return llm
```

The exact number of `.parent` calls depends on the file's depth: from `pipeline/foo.py` or `scripts/foo.py` it's 4 levels up to the project root.

## reddit-auth

Authentication and session management for all Reddit skills. Use it to log in via Rustwright, refresh a saved session, or validate credentials.

### Where it lives

- Source package: `skills/reddit-auth/`
- Devin discovery symlink: `.devin/skills/reddit-auth -> ../../skills/reddit-auth`

### Setup

```bash
uv pip install -r skills/reddit-auth/requirements.txt
```

### Run

```bash
python skills/reddit-auth/scripts/preflight.py
python skills/reddit-auth/scripts/login.py
```

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

Copy `skills/reddit-validator/.env.example` or `skills/reddit-auth/.env.example` to `.env` and fill in the Reddit credentials. For browser login, set `REDDIT_LOGIN_METHOD=rustwright`. `OPENAI_API_KEY` can come from the Devin / Claude Code runtime; dotenv does not overwrite existing environment variables.

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
