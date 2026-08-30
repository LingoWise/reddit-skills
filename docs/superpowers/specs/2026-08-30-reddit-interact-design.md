# reddit-interact Skill Design

## Purpose

Social interaction on Reddit: comment on posts, reply to comments, upvote, downvote, and save posts or comments. All operations use an authenticated browser session from `reddit-auth` and execute via Reddit's JSON API through `page.evaluate`.

## Architecture

Follows the established skill pattern:

```text
skills/reddit-interact/
├── SKILL.md
├── requirements.txt
├── .env.example
├── .markdownlint.json
├── pipeline/
│   ├── __init__.py
│   ├── interactor.py
│   └── paths.py
├── scripts/
│   ├── __init__.py
│   ├── preflight.py
│   ├── comment.py
│   ├── reply.py
│   ├── upvote.py
│   ├── downvote.py
│   └── save.py
├── tests/
│   ├── __init__.py
│   ├── test_interactor.py
│   ├── test_preflight.py
│   ├── test_scripts_comment.py
│   ├── test_scripts_reply.py
│   ├── test_scripts_vote.py
│   └── test_scripts_save.py
└── resources/
    ├── .gitkeep
    ├── CLAUDE.md
    ├── DEVIN.md
    └── failure-recovery.md
```

## Pipeline

### `pipeline/interactor.py`

`Interactor` class — mirrors `Publisher` from reddit-publish:

- `__init__(self, session)` — stores the auth Session.
- `create(cls, headless=False)` — classmethod that loads `reddit-auth/pipeline/auth.py` via importlib and calls `ensure_authenticated_page()`.
- `_fetch_modhash()` — GET `/api/v1/me.json` through `page.evaluate`, extract `modhash` and `name`.
- `_post_json(path, payload)` — POST to Reddit JSON API with `api_type=json`, `uh=modhash`, form-urlencoded body, via `page.evaluate`. Includes 0.5s delay before request (same as Publisher).
- `comment(thing_id, text)` — POST `/api/comment` with `thing_id` and `text`. Returns `{"comment_id": ..., "permalink": ...}`.
- `reply(comment_id, text)` — same endpoint as comment; `thing_id` is a comment fullname (`t1_...`).
- `vote(thing_id, direction)` — POST `/api/vote` with `dir` (1 or -1).
- `save(thing_id)` — POST `/api/save`.
- `unsave(thing_id)` — POST `/api/unsave`.
- `close()` — delegates to `session.close()`.

### `pipeline/paths.py`

Loads `src/common/paths.py` via importlib (4 `.parent` calls from `pipeline/`). Exposes `skill_dir()` and `records_dir()`.

### Thing ID normalization

A helper function `_normalize_thing_id(value, kind)` accepts:

- Full URLs (`https://www.reddit.com/r/.../comments/abc123/title/`)
- Permalinks (`/r/.../comments/abc123/...`)
- Bare IDs (`abc123`)
- Already-prefixed fullnames (`t3_abc123`, `t1_abc123`)

For posts: extracts the ID from URL path after `comments/`, prefixes with `t3_`.
For comments: extracts the comment ID from URL path (segment after the post slug), prefixes with `t1_`.
If already prefixed (`t3_` or `t1_`), returns as-is.
If bare ID and kind is known, prefixes accordingly.

## Scripts

All scripts follow the explore pattern: `sys.path.insert`, import from `pipeline`, `parse_args`, `main`, print JSON line, return exit code.

### `scripts/preflight.py`

Checks deps (`dotenv`, `requests`, `rustwright`, `praw`) and `auth.validate_credentials()`. Prints JSON result. Same structure as explore's preflight.

### `scripts/comment.py`

```bash
python skills/reddit-interact/scripts/comment.py <post_url_or_id> --text "Hello" [--text-file path] [--dry-run] [--out path]
```

- `--text-file` overrides `--text` if both provided.
- `--dry-run`: prints `{"event": "done", "success": true, "dry_run": true, "action": "comment", "thing_id": ..., "text": ...}` without executing.
- On success: saves result JSON to `records/comment_<timestamp>.json`, prints `{"event": "done", "success": true, "comment_id": ..., "permalink": ...}`.

### `scripts/reply.py`

```bash
python skills/reddit-interact/scripts/reply.py <comment_url_or_id> --text "Reply" [--text-file path] [--dry-run] [--out path]
```

Same pattern as comment.py. Target is a comment (normalized with `t1_` prefix).

### `scripts/upvote.py`

```bash
python skills/reddit-interact/scripts/upvote.py <url_or_id> [--dry-run] [--out path]
```

- Accepts post or comment URL/ID. Auto-detects kind from URL structure.
- `--dry-run`: prints action details without executing.
- On success: prints `{"event": "done", "success": true, "action": "upvote", "thing_id": ...}`.

### `scripts/downvote.py`

```bash
python skills/reddit-interact/scripts/downvote.py <url_or_id> [--dry-run] [--out path]
```

Same as upvote.py with `dir=-1`.

### `scripts/save.py`

```bash
python skills/reddit-interact/scripts/save.py <url_or_id> [--unsave] [--dry-run] [--out path]
```

- `--unsave` flag: calls `unsave()` instead of `save()`.
- Default action is save.

## Dependencies

`requirements.txt`:

```text
requests
python-dotenv
praw
rustwright
```

Same as reddit-explore. No LLM dependencies — the agent provides comment/reply text directly.

## Error handling

| Error code | Cause | Recovery |
| --- | --- | --- |
| `auth_failure` | Browser session expired | Re-run `reddit-auth/scripts/login.py` |
| `not_found` | Post/comment doesn't exist | Check the URL/ID |
| `rate_limited` | Too many requests | Wait and retry |
| `interact_error` | Reddit rejected the action (deleted content, permissions, etc.) | Check error message from Reddit response |
| `text_missing` | Neither `--text` nor `--text-file` provided | Provide text via one of the flags |

## Testing

Unit tests use FakePage/FakeSession pattern from `test_publisher.py`:

- `test_interactor.py`: Test each method (comment, reply, vote, save, unsave) with mocked page.evaluate returning appropriate Reddit JSON responses.
- `test_scripts_*.py`: Test dry-run path (no browser launched), verify JSON output format.
- `test_preflight.py`: Test deps check logic.

## SKILL.md

Frontmatter:

```yaml
---
name: reddit-interact
description: Use when the user wants to interact with Reddit content — comment on posts, reply to comments, upvote, downvote, or save posts and comments.
---
```

Sections: When to use, When NOT to use, Prerequisites, Workflow, Operating principles. Same structure as reddit-explore/publish SKILL.md.

## Resources

- `CLAUDE.md` — Claude Code runtime guide with Bash tool commands per action.
- `DEVIN.md` — Devin runtime guide.
- `failure-recovery.md` — error code table.

## Out of scope

- No LLM content generation (agent provides text).
- No batch operations (one action per invocation).
- No comment editing or deletion.
- No post deletion.
