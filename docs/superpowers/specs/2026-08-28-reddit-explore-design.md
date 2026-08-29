# reddit-explore skill design

## Goal

Build `reddit-explore` as the canonical read layer for all Reddit skills. It owns four read primitives — keyword search, subreddit browsing, post details, and user profiles — and exposes them as a Python library (imported by other skills) and as four focused CLI scripts (called by agents and humans). Refactor `reddit-validator`'s scraper to delegate to `reddit-explore`, eliminating duplicated auth-strategy branching and record formatting.

## Architecture

```text
skills/reddit-explore/
├── SKILL.md
├── requirements.txt
├── .env.example
├── .markdownlint.json
├── pipeline/
│   ├── __init__.py
│   ├── client.py        # auth-strategy dispatch: returns a uniform Fetcher
│   ├── explorer.py      # the four read primitives (search, subreddit, post, user)
│   ├── records.py       # Reddit API JSON → validator record shape
│   └── paths.py         # loads src/common/paths.py (same pattern as validator)
├── scripts/
│   ├── __init__.py
│   ├── preflight.py     # deps + reddit-auth check (no AI key needed)
│   ├── search.py        # search.py "<query>" [--subreddits ...] [--limit N] [--sort ...] [--t ...]
│   ├── subreddit.py     # subreddit.py <name> [--sort hot|new|top|rising] [--limit N]
│   ├── post.py          # post.py <url|id> [--comments N] [--comment-sort ...]
│   └── user.py          # user.py <name> [--section overview|posts|comments] [--limit N]
├── resources/
│   ├── DEVIN.md
│   ├── CLAUDE.md
│   └── failure-recovery.md
└── tests/
    ├── test_client.py
    ├── test_explorer.py
    ├── test_records.py
    └── test_scripts.py
```

### Data flow

```text
Agent / human
   │
   ▼
scripts/<capability>.py  ──►  pipeline/explorer.py  ──►  pipeline/client.py  ──►  reddit-auth
   │                              │                         │
   │                              ▼                         ▼
   │                       pipeline/records.py         Fetcher (browser | bearer | praw | public)
   │                              │
   ▼                              ▼
JSON / JSONL output         validator record shape
(records/)                 [{id, post_id, subreddit, title, post_text, text, author, score, url, is_comment}, ...]
```

### Key boundaries

- `client.py` knows about auth strategies and Reddit endpoints. Nothing about records.
- `records.py` knows about the record shape. Nothing about auth.
- `explorer.py` orchestrates: takes a `Fetcher` + params, calls the right endpoint, normalizes via `records.py`.
- Scripts are thin CLI wrappers — no business logic.

### Validator migration

`reddit-validator`'s `scraper.py` shrinks to a thin adapter that calls `explorer.search_posts()` and returns the records. The runner, analyzer, and report stages are untouched.

## pipeline/client.py — the Fetcher

A single `Fetcher` abstraction that `explorer.py` uses, so the four read primitives never need to know which auth strategy is active.

### Public API

```python
class Fetcher:
    """Uniform Reddit JSON fetcher across all auth strategies."""
    strategy: str  # "browser" | "bearer" | "praw" | "public"

    def search(self, query, *, subreddit=None, limit=25, sort="relevance", time_filter="all") -> list[dict]: ...
    def subreddit_listing(self, name, *, sort="hot", limit=25, time_filter="all") -> list[dict]: ...
    def post(self, permalink_or_id, *, comment_limit=0, comment_sort="top") -> tuple[dict, list[dict]]: ...
    def user(self, name, *, section="overview", limit=25, sort="new") -> list[dict]: ...
    def close(self) -> None: ...

    @classmethod
    def from_existing(cls, client) -> "Fetcher":
        """Wrap an already-open reddit-auth client (Session, requests.Session, or praw.Reddit)."""

def get_fetcher() -> Fetcher: ...
```

- `search()` returns a list of raw Reddit post dicts (the `data` inside each `children` entry).
- `subreddit_listing()` returns a list of raw post dicts from a subreddit's listing endpoint.
- `post()` returns `(post_dict, comments_list)` — the post's own data plus top-level comment dicts. `comment_limit=0` skips comment fetching.
- `user()` returns a list of raw item dicts from the user's profile section.
- `get_fetcher()` resolves the strategy via `reddit-auth.resolve_strategy()`, instantiates the right client once, and returns a `Fetcher` that holds the live client (browser `Session`, `requests.Session`, or `praw.Reddit`).
- `from_existing()` inspects the client type (has `page` → browser, has `headers` with `Authorization` → bearer, has `subreddit` → praw, else → public) and builds the right strategy wrapper without opening a new connection. Used by validator's runner to avoid opening a second browser session.

### Strategy implementations (private, inside client.py)

| Strategy | How it fetches | Source of helpers |
| --- | --- | --- |
| `browser` | `auth.fetch_json(page, PUBLIC_BASE, path, params)` — same pattern validator's `_rustwright_search` uses today | `reddit-auth` `Session` |
| `bearer` | `requests.Session` with `Authorization: Bearer <token>` header, hitting `OAUTH_BASE` | `reddit-auth` `bearer_token()` |
| `praw` | `praw.Reddit` client — `subreddit.search()`, `.hot()`, `.new()`, `.top()`, `submission(id)`, `redditor(name)` | `reddit-auth` `get_client("praw")` |
| `public` | `requests.Session` with just a `User-Agent`, hitting `PUBLIC_BASE/.json` endpoints | `reddit-auth` `user_agent()` |

Each strategy method maps its native response to the same raw-dict shape (the `children[].data` form Reddit's JSON API returns), so `explorer.py` sees a uniform input regardless of strategy.

### Lifecycle

`Fetcher` owns the client. `explorer.py` calls `get_fetcher()` once per run and passes it to each primitive. The caller (script or validator) is responsible for calling `close()` when done — matching the existing `Session.close()` pattern.

## pipeline/records.py — normalization

Converts raw Reddit API dicts (the `children[].data` shape) into the flattened record shape that `reddit-validator` already consumes. One job, no auth awareness.

### Public API

```python
def post_record(post: dict) -> dict:
    """Reddit post dict → validator record shape (is_comment=False)."""

def comment_record(post: dict, comment: dict) -> dict:
    """Reddit comment dict → validator record shape (is_comment=True)."""

def user_record(item: dict) -> dict:
    """User profile item (post or comment) → validator record shape."""
```

### Output shape (unchanged from validator's current record shape)

```python
{
    "id": str,
    "post_id": str,
    "subreddit": "r/<name>",
    "title": str,
    "post_text": str,
    "text": str,        # selftext for posts, body for comments
    "author": str,
    "score": int,
    "url": str,
    "is_comment": bool,
}
```

### User profile items

Reddit's user feed mixes posts and comments in one listing. A comment item has `kind = "t1"` and a body; a post item has `kind = "t3"` and a selftext. `user_record()` inspects the `kind` field and produces the right record shape, setting `is_comment` accordingly. For comment items from a user feed, `post_id` comes from `link_id` (which has a `t3_` prefix that gets stripped).

## pipeline/explorer.py — the four read primitives

The orchestration layer. Takes a `Fetcher` and params, calls the right fetcher method, and normalizes the results via `records.py`. Each primitive returns a list of validator-shaped records.

### Public API

```python
def search_posts(
    query: str,
    *,
    fetcher: Fetcher,
    subreddits: str | list[str] | None = None,
    limit: int = 25,
    sort: str = "relevance",
    time_filter: str = "all",
    fetch_comments: bool = False,
    comment_limit: int = 3,
) -> list[dict]:
    """Keyword search across all of Reddit or specific subreddits.
    Returns post records (+ comment records if fetch_comments=True)."""

def list_subreddit(
    name: str,
    *,
    fetcher: Fetcher,
    sort: str = "hot",
    limit: int = 25,
    time_filter: str = "all",
    fetch_comments: bool = False,
    comment_limit: int = 3,
) -> list[dict]:
    """Browse a subreddit's listing (hot/new/top/rising).
    Returns post records (+ comment records if fetch_comments=True)."""

def get_post(
    permalink_or_id: str,
    *,
    fetcher: Fetcher,
    comment_limit: int = 10,
    comment_sort: str = "top",
) -> list[dict]:
    """Fetch a single post and its comment tree.
    Returns [post_record, comment_record, ...]."""

def get_user(
    name: str,
    *,
    fetcher: Fetcher,
    section: str = "overview",
    limit: int = 25,
    sort: str = "new",
) -> list[dict]:
    """Fetch a user's profile section (overview/posts/comments).
    Returns user records (mixed posts and comments)."""
```

### Behavior details

- **`search_posts`**: when `subreddits` is provided, searches each subreddit individually (`/r/{sub}/search`) and merges results — same logic as validator's current `--subreddits` flag. When omitted, searches all of Reddit (`/search` or `/r/all/search`). When `fetch_comments=True`, fetches top comments for each post (capped at `comment_limit`), matching validator's current behavior of grabbing 3 top comments per post.
- **`list_subreddit`**: hits the subreddit listing endpoint (`/r/{name}/{sort}.json`). `rising` falls back to `hot` if the API doesn't support it. Same optional comment fetching as search.
- **`get_post`**: accepts a full URL, a permalink (`/r/.../comments/{id}/...`), or a bare post ID (`{id}` or `t3_{id}`). Normalizes to a permalink, fetches the post + comments endpoint, and returns the post record followed by comment records. `comment_limit=0` returns just the post.
- **`get_user`**: hits `/user/{name}/{section}.json`. The `overview` section mixes posts and comments; `posts` and `comments` sections return only that type. Each item is normalized via `records.user_record()`.

### Subreddit normalization

The `_normalize_subreddits` helper (currently in validator's scraper) moves here — it's a read concern, not an auth concern. Accepts `"IELTS"`, `"r/IELTS"`, `"IELTS,TOEFL"` and returns `["IELTS", "TOEFL"]`.

### No LLM, no report rendering, no profiles

This module is pure data retrieval. It's the thing `reddit-validator` imports to replace its scraper.

## Scripts — CLI entrypoints

Four focused scripts, one per capability. Each is a thin argparse wrapper that calls `get_fetcher()`, invokes the matching explorer primitive, writes JSON output, and closes the fetcher.

### Common script structure

```python
# scripts/search.py (representative — others follow the same shape)
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.client import get_fetcher
from pipeline.explorer import search_posts
from pipeline.paths import records_dir

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Search Reddit posts.")
    parser.add_argument("query", help="Search query.")
    parser.add_argument("--subreddits", default=None, help="Comma-separated subreddits.")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", default="relevance", choices=["relevance","hot","new","top"])
    parser.add_argument("--t", default="all", choices=["all","day","week","month","year"])
    parser.add_argument("--comments", type=int, default=0, help="Top comments per post (0=skip).")
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)

def main(argv=None):
    args = parse_args(argv)
    fetcher = get_fetcher()
    try:
        records = search_posts(
            args.query, fetcher=fetcher,
            subreddits=args.subreddits, limit=args.limit,
            sort=args.sort, time_filter=args.t,
            fetch_comments=args.comments > 0, comment_limit=args.comments,
        )
    finally:
        fetcher.close()

    out_path = Path(args.out) if args.out else records_dir() / f"search_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "count": len(records), "records_path": str(out_path)}))
    return 0
```

### The four scripts

| Script | Args | Explorer call |
| --- | --- | --- |
| `search.py` | `query`, `--subreddits`, `--limit`, `--sort`, `--t`, `--comments`, `--out` | `search_posts()` |
| `subreddit.py` | `name`, `--sort hot\|new\|top\|rising`, `--limit`, `--t`, `--comments`, `--out` | `list_subreddit()` |
| `post.py` | `url_or_id`, `--comments N` (default 10), `--comment-sort top\|best\|new\|controversial`, `--out` | `get_post()` |
| `user.py` | `name`, `--section overview\|posts\|comments`, `--limit`, `--sort`, `--out` | `get_user()` |

### preflight.py

Same shape as validator's preflight but without the `ai_ok` check — explore doesn't need an LLM. Checks deps (`dotenv`, `requests`, `rustwright`, `praw`) and `reddit-auth.validate_credentials()`. Emits the same `{env_ok, deps_ok, reddit_ok}` JSON.

### Output location

All scripts write to `records_dir()` (from `pipeline/paths.py` → `src/common/paths.py` → `.reddit-skills/records/`). Same shared output root as validator.

### No background/polling complexity

Unlike validator's scraper (which can take 30+ minutes), these scripts are fast individual queries. They run synchronously and print a single `done` event. No JSONL streaming needed.

## Validator refactor

`reddit-validator`'s `scraper.py` currently has 366 lines of auth-strategy branching and record formatting. After the refactor, it becomes a thin adapter that calls `reddit-explore`.

### Refactored scraper.py (~30 lines)

```python
import importlib.util
from pathlib import Path


def _load_explorer():
    """Load the reddit-explore pipeline module from the sibling skill directory."""
    explorer_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "explorer.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_explorer", explorer_path)
    explorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(explorer)
    return explorer


def _load_client():
    """Load the reddit-explore client module."""
    client_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "client.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_client", client_path)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    return client


def scrape(idea, profile, client=None, subreddits=None):
    """Scrape Reddit for idea validation using reddit-explore's search primitive."""
    explorer = _load_explorer()
    client_mod = _load_client()

    fetcher = None
    close_after = False
    if client is not None:
        fetcher = client_mod.Fetcher.from_existing(client)
    else:
        fetcher = client_mod.get_fetcher()
        close_after = True

    try:
        limit = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
        if subreddits:
            limit = profile.get("posts_per_subreddit", 25)
        records = explorer.search_posts(
            idea,
            fetcher=fetcher,
            subreddits=subreddits,
            limit=limit,
            sort="relevance",
            time_filter="all",
            fetch_comments=True,
            comment_limit=3,
        )
        return records
    finally:
        if close_after:
            fetcher.close()
```

### What changes in validator

- `scraper.py` shrinks from 366 lines to ~30.
- `runner.py` is unchanged — it still calls `scrape(idea, profile, client=client, subreddits=subreddits)`.
- `analyzer.py`, `report.py`, `config.py`, `paths.py` — untouched.
- All scripts (`run_pipeline.py`, `preflight.py`, `render_report.py`, `extract_report.py`, `recover.py`) — untouched.
- `test_scraper.py` — rewritten to mock `explorer.search_posts` instead of the old internal functions. Assertions stay focused on the same behavior: scrape returns records in the right shape, subreddits are normalized, comments are fetched.

### What does NOT change

- Validator's record shape — explore already returns it.
- Validator's analysis JSON schema.
- Validator's HTML report.
- Validator's SKILL.md, resources, runtime guides (except a one-line note that scraping is now delegated to reddit-explore).

## SKILL.md and runtime guides

### Frontmatter

```yaml
---
name: reddit-explore
description: Use when the user wants to discover, browse, or research Reddit content — search posts, browse subreddits, read post details with comments, or view user profiles.
---
```

### When to use

- "search Reddit for X", "find posts about X", "what's trending on r/X"
- "show me posts from r/X", "browse r/X", "what's hot on r/X"
- "read this post", "get post details", "show comments on this post"
- "look up user X", "what does user X post about", "user X's comment history"
- Another skill (e.g. reddit-validator) needs Reddit data fetched

### When NOT to use

Validating a business idea (→ reddit-validator), posting content (→ reddit-publish), voting/commenting (→ reddit-interact), compound operations like trend tracking (→ reddit-content-ops).

### Prerequisites

Same as validator minus the AI key — Python 3.10+, deps installed, Reddit access via one of the four auth strategies. No `OPENAI_API_KEY` needed.

### Workflow phases

| Phase | Action |
| --- | --- |
| 0 — Decide | Apply when the user wants to discover/browse/read Reddit content, or another skill needs Reddit data. |
| 1 — Preflight | `python "<skill_dir>/scripts/preflight.py"` — check deps + reddit auth. |
| 2 — Pick capability | Search, subreddit browse, post details, or user profile. |
| 3 — Execute | Run the matching script, read the JSON output. |
| 4 — Surface | Summarize results for the user (post titles, scores, comment counts, etc.). |

### Runtime guides (resources/DEVIN.md, resources/CLAUDE.md)

Shorter than validator's since there's no long-running background scraper or LLM analysis. Each guide covers:

- Preflight call
- The four script commands with example args
- How to read the `done` JSON event
- How to present results concisely (don't dump full JSON, summarize)

### resources/failure-recovery.md

Covers the same auth failures as validator's (stale session, missing creds, rate limiting) plus explore-specific ones (private subreddit, deleted user, non-existent post, 403 on user profile).

### Operating principles

- Always run preflight first.
- These are fast queries — run synchronously, no background needed.
- Return structured JSON; let the agent decide how to present it.
- Don't fabricate data — if a fetch fails, surface the error.
- Reuse a saved browser session when available; don't open redundant login windows.

## Error handling

Errors propagate as Python exceptions with clear messages. The scripts catch them at the top level and emit a structured `done` event with `success: false`, matching validator's pattern:

```json
{"event": "done", "success": false, "error": "subreddit r/foo is private", "code": "private_subreddit"}
```

### Error categories

| Scenario | Where caught | Behavior |
| --- | --- | --- |
| Auth failure (stale session, bad token) | `client.py` | Raise `RuntimeError` with auth context. Script emits `done` with `code: "auth_failure"`. |
| Network timeout | `client.py` (15s default) | Raise `TimeoutError`. Script emits `done` with `code: "timeout"`. |
| Reddit 403 / 404 (private sub, deleted post, banned user) | `client.py` | Raise `LookupError` with the resource name. Script emits `done` with `code: "not_found"` or `"forbidden"`. |
| Rate limiting (429) | `client.py` | Raise `RuntimeError`. Script emits `done` with `code: "rate_limited"`. No automatic retry in v1 — surface it and let the agent decide. |
| Empty results | `explorer.py` | Not an error. Return `[]`. Script emits `done` with `count: 0`. |

No silent swallowing. The fetcher's `close()` always runs via `try/finally` in both scripts and explorer primitives, so browser sessions don't leak on errors.

## Testing

Tests use the same pattern as validator's existing `test_scraper.py` — mock the fetcher/client layer and test the logic above it. No real Reddit calls in tests.

| Test file | What it covers |
| --- | --- |
| `test_records.py` | `post_record()`, `comment_record()`, `user_record()` — feed raw Reddit JSON fixtures, assert output shape. Pure functions. |
| `test_client.py` | `Fetcher.from_existing()` type detection, `get_fetcher()` strategy resolution (mock `reddit-auth.resolve_strategy`). Mock the actual HTTP/browser calls. |
| `test_explorer.py` | Each of the four primitives with a mocked `Fetcher`. Assert correct endpoint calls, record normalization, subreddit normalization, comment fetching toggle, empty results. |
| `test_scripts.py` | Each script's `main()` with a mocked `get_fetcher`. Assert argparse parsing, output file writing, `done` event shape, error events. |

### Test fixtures

Small raw Reddit JSON snippets stored inline in the test files (a post dict, a comment dict, a user listing item) — same approach as validator's tests. No external fixture files needed.

### Validator test update

`test_scraper.py` is rewritten to mock `explorer.search_posts` instead of the old internal functions. The test assertions stay focused on the same behavior: scrape returns records in the right shape, subreddits are normalized, comments are fetched.

## requirements.txt

```text
requests
python-dotenv
praw
rustwright
```

No `jinja2` or `openai` — explore does no rendering or LLM analysis.

## .devin/skills symlink

Create `.devin/skills/reddit-explore -> ../../skills/reddit-explore` so Devin discovers the skill, matching the existing pattern for reddit-auth and reddit-validator.

## Out of scope

- `reddit-publish`, `reddit-interact`, `reddit-content-ops` — separate design sessions.
- Pagination beyond the first page of results (Reddit's `after` cursor). Can be added later if needed.
- Full comment tree expansion (Reddit's `more` comments). v1 fetches top-level comments only, matching validator's current behavior.
- Caching of fetched data across runs.
- MCP server exposure. Skills are called via scripts and pipeline imports for now.
