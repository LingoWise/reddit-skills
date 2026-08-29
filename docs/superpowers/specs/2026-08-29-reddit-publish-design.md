# reddit-publish skill design

## Goal

`reddit-publish` is the canonical content publishing skill for the `reddit-skills` monorepo. It researches top-performing posts in a target subreddit, drafts a community-native post in a chosen style, and publishes it to Reddit. It supports self-text, link, and image posts and is exposed as three focused CLI stages (`research.py`, `draft.py`, `publish.py`) plus a `preflight.py` check.

The skill reuses existing shared code:

- `reddit-auth` for authenticated browser sessions.
- `reddit-explore` for reading top/search posts.
- `src/common/llm.py` for text generation.
- `src/common/paths.py` for output directories.

## In scope for v1

- Text (`self`), link (`link`), and image (`image`) post submission via a logged-in browser session.
- Research by topic, optionally scoped to a subreddit, with optional subreddit suggestion.
- Draft generation with a choice of style presets or a free-form style prompt.
- Image resolution: user-provided local file, user-provided URL, or AI-generated image.
- Explicit `--language` parameter (default `en`) for generated content.
- Separate, composable stage scripts: `research.py`, `draft.py`, `publish.py`.
- Dry-run mode in `publish.py` so a draft can be validated without going live.

## Out of scope for v1

- Scheduling posts or bulk posting.
- Crossposting.
- Commenting on the published post or replying to replies.
- Engagement analytics after publishing.
- Inline images/media inside self-text body.
- Non-OpenAI image providers (OpenRouter image endpoints may be added as a fast-follow).
- Auto-engagement loops.

## File layout

```text
skills/reddit-publish/
├── SKILL.md
├── requirements.txt
├── .env.example
├── .markdownlint.json
├── pipeline/
│   ├── __init__.py
│   ├── paths.py          # output directory helpers (wraps src/common/paths)
│   ├── prompts.py        # shared LLM prompts
│   ├── researcher.py     # stage 1: find and analyze inspiration
│   ├── drafter.py        # stage 2: generate title/body
│   ├── imager.py         # resolve or generate an image
│   └── publisher.py      # stage 3: browser-based submission
├── scripts/
│   ├── __init__.py
│   ├── preflight.py      # deps + auth + LLM/image checks
│   ├── research.py       # run research stage
│   ├── draft.py          # run draft stage
│   └── publish.py        # run publish stage
└── resources/
    ├── DEVIN.md          # Devin-specific tool calling guide
    ├── CLAUDE.md         # Claude-specific tool calling guide
    └── failure-recovery.md
```

## Architecture

### Data flow

```text
Agent / user
   │
   ▼
scripts/preflight.py
   │
   ▼
scripts/research.py  ──►  pipeline/researcher.py  ──►  reddit-explore
   │                              │
   ▼                              ▼
records/research_<id>.json  inspiration + subreddit suggestions
   │
   ▼
scripts/draft.py  ──►  pipeline/drafter.py (+ imager.py if image)
   │                         │
   │                         ▼
   │                    src/common/llm.py
   │                         │
   │              (draft.py calls imager.py here if needed)
   │                         ▼
   ▼
drafts/draft_<id>.json  {title, body, kind, subreddit, image_path, style, language}
   │
   ▼
scripts/publish.py  ──►  pipeline/publisher.py  ──►  reddit-auth browser session
   ▼
done JSON {success, post_id, post_url, permalink}
```

### Component boundaries

- `researcher.py` owns finding and analyzing top posts. It delegates fetching to `reddit-explore`.
- `drafter.py` owns content generation. It consumes research output and a style, and returns a draft. It does not publish.
- `imager.py` owns image resolution: validate a provided file/URL or generate a new image and save it locally. It does not upload.
- `publisher.py` owns Reddit submission. It consumes a completed draft and uses the authenticated browser. It does not generate content or resolve images.
- `scripts/*.py` are thin argparse wrappers. They write JSON artifacts and emit a `done` event.
- `prompts.py` centralizes LLM prompt templates so `researcher.py` and `drafter.py` share the same anti-advertising and style rules.

## pipeline/paths.py

Wraps `src/common/paths.py` and adds skill-specific subdirectories under `.reddit-skills/`.

```python
import importlib.util
from pathlib import Path


def _load_common_paths():
    paths_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "paths.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_paths", paths_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_common = _load_common_paths()


def records_dir() -> Path:
    return _common.records_dir()


def drafts_dir() -> Path:
    path = _common.output_root() / "drafts"
    path.mkdir(exist_ok=True)
    return path


def images_dir() -> Path:
    path = _common.output_root() / "images"
    path.mkdir(exist_ok=True)
    return path
```

Research output (inspiration records) goes to `records/`. Drafts go to `drafts/`. Resolved/generated images go to `images/`.

## pipeline/researcher.py

Finds inspiration for the draft. It loads `reddit-explore/pipeline/explorer.py` via `importlib` (the same pattern `reddit-validator` uses for `reddit-explore`).

### Public API

```python
def research(
    topic: str,
    *,
    subreddit: str | None = None,
    limit: int = 25,
    sort: str = "top",
    time_filter: str = "month",
    suggest_subreddit: bool = False,
    records: list[dict] | None = None,
    language: str = "en",
) -> dict:
    """Return research results for a topic."""
```

### Behavior

- If `records` are provided, skip fetching and use them directly.
- If `subreddit` is provided, search inside that community (`/r/{sub}/search` and `list_subreddit`) and set it as the target.
- If `subreddit` is not provided and `suggest_subreddit=True`, search all of Reddit for the topic and ask the LLM to suggest 3–5 relevant subreddits; `subreddit` in the output is `null`.
- If `subreddit` is not provided and `suggest_subreddit=False`, the output `subreddit` is `null` and `suggestions` contains the most common subreddits from the search results.
- The `sort` for inspiration defaults to `top` so the skill learns from high-performing posts.
- Returns a dict:

```python
{
    "subreddit": "r/AskReddit",
    "suggestions": ["r/AskReddit", "r/NoStupidQuestions", "r/explainlikeimfive"],
    "records": [...],           # validator-shaped records from reddit-explore
    "patterns": {
        "hook_patterns": ["...", "..."],
        "title_length": "short",
        "tone": "conversational",
        "high_engagement_themes": ["..."],
    },
    "language": "en",
}
```

### Subreddit normalization

Accepts `"r/AskReddit"`, `"AskReddit"`, or `"askreddit"` and stores the canonical `r/<name>` form. Leading `r/` is stripped internally when calling `reddit-explore`.

## pipeline/drafter.py

Generates the post draft. Uses `src/common/llm.py` for LLM calls.

### Public API

```python
def draft(
    topic: str,
    research: dict,
    *,
    subreddit: str | None = None,
    style: str | None = "casual",
    image_path: str | None = None,
    image_prompt: str | None = None,
    image_url: str | None = None,
    link_url: str | None = None,
    language: str = "en",
    kind: str | None = None,
) -> dict:
    """Generate a post draft from research."""
```

### Behavior

- If `subreddit` is provided, it overrides `research["subreddit"]`. Otherwise the target subreddit comes from the research output.
- If the research output has no target subreddit and no `subreddit` override, `drafter.draft()` raises `ValueError`.
- If `kind` is not provided, it is inferred from `link_url` / image arguments.
- Returns a draft dict with all fields needed by `publisher.py`.

### Style

`style` can be:

- A named preset: `casual`, `story`, `question`, `helpful`, `hot_take`, `meme`, `discussion`.
- A free-form custom prompt, e.g. `--style "write like a tired but enthusiastic grad student"`.

Default is `casual`.

The prompt template instructs the LLM to:

- Avoid marketing or advertising language.
- Match the target subreddit's tone, based on the `patterns` from `researcher.py`.
- Keep the content native to Reddit (first-person, community context, no CTAs unless appropriate).
- Honor the chosen `language`.
- Return only a valid JSON object.

### Draft output

```python
{
    "title": "...",
    "body": "...",
    "kind": "self" | "link" | "image",
    "subreddit": "r/AskReddit",
    "style": "casual",
    "language": "en",
    "url": "",                 # for link posts
    "image_path": "",          # for image posts
    "image_prompt": "",        # if image was generated
    "inspiration": ["..."],    # URLs of top posts used
}
```

### Kind resolution

If `kind` is not specified, infer from provided fields:

- `link_url` → `link`
- `image_path` or `image_prompt` or `image_url` → `image`
- otherwise → `self`

If `kind=image` and `image_path` is not yet present, the draft includes a `body` and an `image_prompt`. `scripts/draft.py` then calls `imager.resolve_image()` to resolve `image_path`, `image_url`, or `image_prompt` into a local file and writes the final `image_path` into the draft JSON before it is saved.

## pipeline/imager.py

Resolves the image for `image` posts. Does not upload to Reddit.

### Public API

```python
def resolve_image(
    image_path: str | None = None,
    image_url: str | None = None,
    image_prompt: str | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Return a local image file path ready for publishing."""
```

### Behavior

`imager.py` is called by `scripts/draft.py` (not by `publisher.py`) so the final image is part of the reviewable draft.

- If `image_path` is provided, validate it exists and is a supported format (`jpg`, `jpeg`, `png`, `gif`, `webp`). Convert/re-encode if needed.
- If `image_url` is provided, download it to `.reddit-skills/images/` and validate.
- If `image_prompt` is provided, call `openai.images.generate` (with `OPENAI_IMAGE_MODEL`, default `dall-e-3` and optional `OPENAI_BASE_URL`) and save the result.
- Return the local path.

### Image generation dependencies

For v1, `imager.py` uses OpenAI's `images.generate` endpoint:

- `OPENAI_API_KEY` (required for image generation; may be an OpenAI-compatible image endpoint if `OPENAI_BASE_URL` is set).
- `OPENAI_BASE_URL` (optional, for OpenAI-compatible image endpoints).
- `OPENAI_IMAGE_MODEL` (optional, defaults to `dall-e-3`).

## pipeline/publisher.py

Submits the draft to Reddit using an authenticated browser session from `reddit-auth`.

### Public API

```python
class Publisher:
    """Browser-based Reddit publisher."""

    def __init__(self, session: Session):
        ...

    @classmethod
    def create(cls, headless: bool = False) -> "Publisher":
        """Create a Publisher from the active reddit-auth session."""

    def publish(
        self,
        *,
        subreddit: str,
        title: str,
        kind: str,
        body: str | None = None,
        url: str | None = None,
        image_path: str | None = None,
        nsfw: bool = False,
        spoiler: bool = False,
    ) -> dict:
        """Submit the post and return {post_id, post_url, permalink}."""

    def close(self) -> None:
        """Close the browser session."""
```

### Publishing mechanism

`publisher.py` uses `reddit-auth.ensure_authenticated_page()` to get a logged-in Rustwright session and then runs authenticated `fetch` calls from inside the page against `https://www.reddit.com`.

1. **CSRF/modhash**: The publisher fetches the logged-in user's profile from `/api/v1/me.json` or `/api/me.json` to obtain a CSRF token / modhash for state-changing `POST`s.

2. **Text posts**: `POST` to `https://www.reddit.com/api/submit` with:

   - `api_type=json`
   - `kind=self`
   - `sr=<subreddit_name>`
   - `title=<title>`
   - `text=<body>`
   - `nsfw=<bool>`
   - `spoiler=<bool>`

3. **Link posts**: `POST` to `https://www.reddit.com/api/submit` with:

   - `kind=link`
   - `sr=<subreddit_name>`
   - `title=<title>`
   - `url=<url>`

4. **Image posts**:

   - Request a media upload lease from `POST https://www.reddit.com/api/media/asset`.
   - Upload the local image to the returned S3 / Reddit upload URL.
   - `POST` to `https://www.reddit.com/api/submit` with `kind=image` and the returned asset URL as the `url` field.

If the internal `fetch` media-asset flow fails due to CSRF or S3-redirect behavior, `publisher.py` falls back to Playwright form fill on Reddit's submit page. Both paths use the same logged-in browser session.

### Return value

```python
{
    "post_id": "...",
    "permalink": "/r/AskReddit/comments/...",
    "post_url": "https://www.reddit.com/r/AskReddit/comments/...",
    "subreddit": "r/AskReddit",
    "title": "...",
}
```

## scripts/research.py

Thin CLI wrapper for `researcher.research()`.

```bash
python skills/reddit-publish/scripts/research.py "<topic>" \
  [--subreddit AskReddit] \
  [--limit 25] \
  [--sort top|hot|relevance|new] \
  [--time day|week|month|year|all] \
  [--suggest-subreddit] \
  [--language en] \
  [--out path/to/research.json]
```

Default output: `.reddit-skills/records/research_<timestamp>.json`.

Emits `done` JSON:

```json
{"event": "done", "success": true, "records_path": "...", "subreddit": "r/AskReddit"}
```

## scripts/draft.py

Thin CLI wrapper for `drafter.draft()`.

```bash
python skills/reddit-publish/scripts/draft.py path/to/research.json \
  [--subreddit r/AskReddit] \
  [--style casual] \
  [--image-path /path/to/image.png] \
  [--image-url https://...] \
  [--image-prompt "a cozy cat reading a book"] \
  [--link-url https://...] \
  [--language en] \
  [--out path/to/draft.json]
```

`--subreddit` is required when the research output does not contain a target subreddit. If omitted, it defaults to the first suggestion in `research["suggestions"]`.

`scripts/draft.py` calls `drafter.draft()` first, then `imager.resolve_image()` if the draft contains an unresolved image, and writes the final draft JSON with `image_path` populated.

Default output: `.reddit-skills/drafts/draft_<timestamp>.json`.

Emits `done` JSON:

```json
{"event": "done", "success": true, "draft_path": "..."}
```

## scripts/publish.py

Thin CLI wrapper for `publisher.publish()`.

```bash
python skills/reddit-publish/scripts/publish.py path/to/draft.json \
  [--dry-run] \
  [--out path/to/result.json]
```

`--dry-run` validates the draft and prints the publish payload without submitting.

Emits `done` JSON:

```json
{"event": "done", "success": true, "post_id": "...", "post_url": "...", "permalink": "..."}
```

## scripts/preflight.py

Same shape as `reddit-explore/scripts/preflight.py` but adds an AI and image check.

Returns:

```json
{
  "env_ok": true,
  "deps_ok": true,
  "reddit_ok": true,
  "ai_ok": true,
  "image_ok": true
}
```

- `env_ok` / `deps_ok` / `reddit_ok` come from `reddit-auth` hygiene and dependency checks.
- `ai_ok` checks `OPENAI_API_KEY` / `OPENROUTER_API_KEY` and the `openai` package.
- `image_ok` checks `OPENAI_API_KEY` and the `openai` package's image generation support.

## Error handling

All pipeline modules raise exceptions with clear messages. Scripts catch them at the top level and emit a structured `done` event:

```json
{"event": "done", "success": false, "error": "...", "code": "..."}
```

### Error codes

| Scenario | Code | Notes |
| --- | --- | --- |
| Missing `openai` package or AI key | `ai_unavailable` | Only for draft/image generation stages. |
| Missing/stale Reddit session | `auth_failure` | `publisher.py` or `preflight.py`. |
| Subreddit private / does not exist | `not_found` | From `reddit-explore` or `/api/submit` response. |
| Reddit rate limit (429) | `rate_limited` | Surface the retry-after message. |
| Post rejected by subreddit rules | `publish_rejected` | e.g. title too long, missing flair. |
| Image generation failed | `image_gen_error` | Network or API error. |
| Image download/validation failed | `image_invalid` | Bad URL, unsupported format, corrupt file. |
| LLM returned invalid JSON | `draft_error` | Could not parse draft. |

## SKILL.md contract

Frontmatter:

```yaml
---
name: reddit-publish
description: Use when the user wants to publish content to Reddit — research a topic, draft a human-sounding post, and submit it as text, link, or image.
---
```

### When to use

- "publish a post to r/..."
- "draft a Reddit post about X"
- "find inspiration and post about Y"
- "post an image to r/..."

### When NOT to use

- Validating a business idea (→ `reddit-validator`).
- Browsing or searching Reddit (→ `reddit-explore`).
- Commenting, voting, or engagement (→ `reddit-interact`, once it exists).

### Workflow

1. Run `python skills/reddit-publish/scripts/preflight.py`.
2. Run `research.py` with a topic and optional subreddit.
3. Run `draft.py` with the research JSON and a style.
4. Run `publish.py` with the draft JSON (`--dry-run` first if desired).

## Testing

- `test_researcher.py`: mock `reddit-explore` and LLM, assert subreddit suggestion and pattern extraction.
- `test_drafter.py`: mock LLM, assert output schema, style prompt injection, and language pass-through.
- `test_imager.py`: mock image generation and URL download, assert local path and validation.
- `test_publisher.py`: mock `reddit-auth` `Session` and `page.evaluate`, assert submit payloads for `self`, `link`, and `image`.
- `test_scripts_research.py`, `test_scripts_draft.py`, `test_scripts_publish.py`: argument parsing and `done` JSON shape.

## Dependencies

`requirements.txt`:

```text
rustwright
openai
requests
python-dotenv
praw
```

`praw` is listed because `reddit-explore` lazily imports it during research. It is not used directly by `publisher.py` in v1.

## Operating principles

- Always run `preflight.py` first.
- All scripts emit structured `done` JSON; agents should parse it, not regex human text.
- Use `--dry-run` before the first real publish in a session.
- Reuse the saved browser session from `reddit-auth` when valid.
- Generated content must avoid advertising language and match the chosen subreddit's tone.
- Respect Reddit rate limits; do not bulk post.
- Keep human-like spacing and delays inside `publisher.py` to reduce bot signals.

## Future work

- Add OpenRouter image model support via `OPENAI_BASE_URL`.
- Add a `one_shot.py` convenience script that runs all three stages end-to-end.
- Add flair selection before publishing.
- Add a post-engagement stage (`reddit-interact`) for replying to comments.
