---
name: reddit-auth
description: Use when a skill needs a Reddit-authenticated browser session, credential check, or session refresh before performing Reddit operations.
---

# Reddit Authentication

Centralize Reddit authentication and session management for other Reddit skills. Supports browser-based manual login via Rustwright, bearer tokens, PRAW script apps, and public (unauthenticated) fallback.

## When to use

- A skill needs a logged-in Reddit session before scraping, posting, or interacting.
- You need to check credential hygiene before starting a pipeline.
- A saved browser session may be stale and needs refresh.
- You want to log in once and reuse the session across multiple skills.

Do NOT use for: storing or encrypting long-lived secrets; bypassing Reddit's terms of service; fully headless authentication without user interaction.

## Prerequisites

- Python 3.10+.
- Dependencies installed: `uv pip install -r <skill_dir>/requirements.txt`.
- Chromium/Chrome available (Rustwright finds the system browser or its own download automatically).

## File layout

```text
<skill_dir>/
├── SKILL.md
├── requirements.txt
├── .env.example
├── pipeline/
│   └── auth.py
├── scripts/
│   ├── preflight.py
│   └── login.py
└── checkpoints/
    └── reddit_session.json   # runtime session storage (ignored by git)
```

## Workflow

### Phase 1 — Preflight

```bash
python "<skill_dir>/scripts/preflight.py"
```

Returns `env_ok`, `deps_ok`, `reddit_ok` plus `credential_hygiene` problems if any. Only proceed when `deps_ok` and `reddit_ok` are true.

### Phase 2 — Choose a strategy

The strategy is resolved from environment variables in this order:

1. `REDDIT_LOGIN_METHOD=rustwright|playwright|browser` — open a real browser.
2. `REDDIT_CLIENT_SECRET` contains a parseable bearer token.
3. `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` are set (PRAW).
4. Public (unauthenticated) fallback.

### Phase 3 — Log in

For browser login, run:

```bash
python "<skill_dir>/scripts/login.py"
```

A Chromium window opens on `https://www.reddit.com`. Click **Log in** and complete the flow. The script polls `https://www.reddit.com/api/v1/me` and saves the browser storage state to `checkpoints/reddit_session.json` once login is detected.

### Phase 4 — Use the session from another skill

```python
import importlib.util
from pathlib import Path

auth_path = Path("skills/reddit-auth/pipeline/auth.py")
spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)

session = auth.ensure_authenticated_page()
# use session.page for authenticated browser fetches
session.close()
```

## Runtime-specific instructions

- The browser window must remain visible for manual login. Use `headless=False`.
- Starting at `https://www.reddit.com` (not `/login/`) reduces human-verification prompts.
- The session file is a standard Playwright/Rustwright storage-state object and can be reused by any Rustwright context.

## Operating principles

- Never commit credentials or session files to version control.
- Reuse a saved session when it is still valid; prompt for login only when necessary.
- Treat `REDDIT_LOGIN_METHOD=playwright` as an alias for `rustwright` for backward compatibility.
