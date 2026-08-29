# reddit-publish implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `reddit-publish` skill so an agent can research a topic, draft a community-native Reddit post, and publish it as text, link, or image via an authenticated browser session.

**Architecture:** Three stage scripts (`research.py`, `draft.py`, `publish.py`) wrap four pipeline modules. `researcher.py` uses `reddit-explore` to gather and analyze top posts. `drafter.py` uses `src/common/llm.py` to generate a post in the chosen style. `imager.py` resolves a local image from a path, URL, or prompt. `publisher.py` uses `reddit-auth` to submit the post to Reddit through authenticated browser `fetch` calls.

**Tech Stack:** Python 3.10+, `rustwright`, `openai`, `requests`, `python-dotenv`, `praw`, `pytest`.

## Global Constraints

- All skills write runtime outputs under `.reddit-skills/` via `src/common/paths.py`.
- Pipeline modules load sibling skills and shared libraries with `importlib.util.spec_from_file_location`.
- All scripts emit a structured JSON `done` event to stdout.
- `reddit-auth` is the only source of logged-in browser sessions.
- `reddit-explore` is the only source of Reddit read data.
- The skill must be runnable from `skills/reddit-publish/` without requiring installation as a package.

---

### Task 1: Scaffold package and `pipeline/paths.py`

**Files:**

- Create: `skills/reddit-publish/pipeline/__init__.py`
- Create: `skills/reddit-publish/pipeline/paths.py`
- Create: `skills/reddit-publish/scripts/__init__.py`
- Create: `skills/reddit-publish/tests/__init__.py`
- Create: `skills/reddit-publish/resources/.gitkeep`
- Create: `skills/reddit-publish/requirements.txt`
- Create: `skills/reddit-publish/.env.example`
- Create: `skills/reddit-publish/.markdownlint.json`
- Overwrite: `skills/reddit-publish/SKILL.md` (currently empty)

**Interfaces:**

- Produces: `records_dir() -> Path`, `drafts_dir() -> Path`, `images_dir() -> Path`, `skill_dir() -> Path`.

- [ ] **Step 1: Create directories and package files**

```bash
mkdir -p skills/reddit-publish/{pipeline,scripts,tests,resources}
touch skills/reddit-publish/pipeline/__init__.py
touch skills/reddit-publish/scripts/__init__.py
touch skills/reddit-publish/tests/__init__.py
touch skills/reddit-publish/resources/.gitkeep
```

- [ ] **Step 2: Write `pipeline/paths.py`**

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


def skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def records_dir() -> Path:
    return _common.records_dir()


def drafts_dir() -> Path:
    path = _common.output_root() / "drafts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def images_dir() -> Path:
    path = _common.output_root() / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path
```

- [ ] **Step 3: Write `requirements.txt`, `.env.example`, `.markdownlint.json`, and `SKILL.md`**

`requirements.txt`:

```text
rustwright
openai
requests
python-dotenv
praw
```

`.env.example`:

```text
# Reddit auth method (see reddit-auth for details):
# - rustwright | playwright | browser: open a real browser for manual login
# - token: base64 bearer token JSON in REDDIT_CLIENT_SECRET
# - praw: script app client_id / client_secret / username / password
REDDIT_LOGIN_METHOD=rustwright

# Optional: for token/praw methods
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=script:reddit-publish:v0.1 (by /u/your_username)

# Optional: for PRAW script apps
REDDIT_USERNAME=
REDDIT_PASSWORD=

# AI / image generation (set as shell env, not in .env for real values)
OPENAI_API_KEY=
# OPENAI_BASE_URL=
# OPENAI_IMAGE_MODEL=dall-e-3
```

`.markdownlint.json`:

```json
{
  "MD013": false,
  "MD060": false
}
```

`SKILL.md` (skill contract for agent discovery):

```markdown
---
name: reddit-publish
description: Use when the user wants to publish content to Reddit — research a topic, draft a human-sounding post, and submit it as text, link, or image.
---

# Reddit Publish

Publish posts to Reddit by researching top content, drafting in a chosen style, and submitting through a real browser.

## When to use

- "publish a post to r/..."
- "draft a Reddit post about X"
- "find inspiration and post about Y"
- "post an image to r/..."

## When NOT to use

- Validating a business idea (→ `reddit-validator`).
- Browsing or searching Reddit (→ `reddit-explore`).
- Commenting or voting (→ `reddit-interact`, once it exists).

## Prerequisites

- Python 3.10+.
- Dependencies: `uv pip install -r skills/reddit-publish/requirements.txt`.
- Reddit authentication via `reddit-auth`.
- For AI-generated drafts/images: `OPENAI_API_KEY` in the shell environment.

## Workflow

1. Preflight: `python "skills/reddit-publish/scripts/preflight.py"`
2. Research: `python "skills/reddit-publish/scripts/research.py" "<topic>" [--subreddit ...] [--suggest-subreddit]`
3. Draft: `python "skills/reddit-publish/scripts/draft.py" path/to/research.json [--style ...]`
4. Publish: `python "skills/reddit-publish/scripts/publish.py" path/to/draft.json [--dry-run]`

## Operating principles

- Always run preflight first.
- Use `--dry-run` before the first real publish in a session.
- Generated content must avoid advertising language and match the subreddit's tone.
- Respect Reddit rate limits; do not bulk post.
```

- [ ] **Step 4: Verify the module loads without errors**

```bash
cd skills/reddit-publish
python -c "from pipeline.paths import records_dir, drafts_dir, images_dir, skill_dir; print(records_dir()); print(drafts_dir()); print(images_dir()); print(skill_dir())"
```

Expected: no errors; prints paths under `.reddit-skills/` and the skill directory path.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/pipeline/__init__.py skills/reddit-publish/pipeline/paths.py skills/reddit-publish/scripts/__init__.py skills/reddit-publish/tests/__init__.py skills/reddit-publish/resources/.gitkeep skills/reddit-publish/requirements.txt skills/reddit-publish/.env.example skills/reddit-publish/.markdownlint.json skills/reddit-publish/SKILL.md
git commit -m "scaffold reddit-publish package and skill contract"
```

---

### Task 2: Implement `pipeline/prompts.py`

**Files:**

- Create: `skills/reddit-publish/pipeline/prompts.py`
- Create: `skills/reddit-publish/tests/test_prompts.py`

**Interfaces:**

- Produces: `RESEARCH_PROMPT`, `DRAFT_PROMPT`, `SUBREDDIT_SUGGEST_PROMPT`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_prompts.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import prompts


def test_prompts_defined():
    assert "{topic}" in prompts.RESEARCH_PROMPT
    assert "{style}" in prompts.DRAFT_PROMPT
    assert "{corpus}" in prompts.SUBREDDIT_SUGGEST_PROMPT
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_prompts.py -v
```

Expected: `ModuleNotFoundError` or `AttributeError` because `pipeline/prompts.py` does not exist.

- [ ] **Step 3: Write `pipeline/prompts.py`**

```python
SUBREDDIT_SUGGEST_PROMPT = """Given the topic below and the Reddit posts provided, suggest 3-5 relevant subreddits where a post about this topic would fit naturally. Return a single JSON object with one key "subreddits" containing a list of strings like "r/AskReddit". Do not explain.

Topic: {topic}

Reddit posts:
{corpus}
"""

RESEARCH_PROMPT = """You are a Reddit content strategist. Analyze the top posts below and summarize what makes them successful in this community.

Topic: {topic}
Target subreddit: {subreddit}

Return a single JSON object with these keys:
- "hook_patterns": list of common title structures or hooks
- "title_length": "short", "medium", or "long"
- "tone": one word describing the dominant tone
- "high_engagement_themes": list of themes that get attention

Be concise. Do not include markdown or explanation.

Reddit posts:
{corpus}
"""

DRAFT_PROMPT = """You are a native Reddit contributor. Write a post for r/{subreddit} about the topic below.

Topic: {topic}
Style: {style}
Language: {language}

Rules:
- Do NOT sound like an advertisement, marketer, or salesperson.
- Match the style requested.
- Use the research patterns below to fit the community.
- Write in the requested language.
- Keep the tone natural and community-native.

Research patterns:
{patterns}

Return a single JSON object with these keys:
- "title": the post title (max 300 chars)
- "body": the post body or caption (use empty string if style is "image-only")
- "kind": one of "self", "link", "image" (infer from content)
- "url": external URL, only if kind is "link"
- "image_prompt": a detailed image generation prompt, only if kind is "image"
- "inspiration": list of URLs from the research that influenced the post

Only return valid JSON. No markdown, no explanation.
"""
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_prompts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/pipeline/prompts.py skills/reddit-publish/tests/test_prompts.py
git commit -m "add reddit-publish prompt templates"
```

---

### Task 3: Implement `pipeline/researcher.py`

**Files:**

- Create: `skills/reddit-publish/pipeline/researcher.py`
- Create: `skills/reddit-publish/tests/test_researcher.py`

**Interfaces:**

- Consumes: `reddit-explore/pipeline/explorer.py` (`search_posts`, `list_subreddit`), `src/common/llm.py` (`chat_json`).
- Produces: `research(topic, *, subreddit=None, limit=25, sort="top", time_filter="month", suggest_subreddit=False, records=None, language="en") -> dict`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_researcher.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import researcher


def test_research_uses_provided_records(monkeypatch):
    records = [{"subreddit": "AskReddit", "title": "T", "text": "hello", "url": "https://reddit.com/1", "is_comment": False}]
    called = {}

    def fake_llm(messages, **kwargs):
        called["llm"] = True
        return json.dumps({"hook_patterns": ["question"], "title_length": "short", "tone": "casual", "high_engagement_themes": ["relatable"]})

    from pipeline import researcher as rmod
    monkeypatch.setattr(rmod, "_load_llm", lambda: type("Llm", (), {"chat_json": fake_llm})())

    result = rmod.research("test", records=records, subreddit="AskReddit")
    assert result["subreddit"] == "r/AskReddit"
    assert result["patterns"]["tone"] == "casual"
    assert result["records"] == records
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_researcher.py -v
```

Expected: `ModuleNotFoundError` for `pipeline.researcher`.

- [ ] **Step 3: Write minimal `pipeline/researcher.py`**

```python
import importlib.util
import json
from pathlib import Path


def _load_explorer():
    explore_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "explorer.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_explorer", explore_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_llm():
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build_corpus(records):
    parts = []
    for rec in records:
        sub = rec.get("subreddit", "unknown")
        title = rec.get("title", "")
        text = rec.get("text", "")
        parts.append(f"r/{sub}: {title}\n{text}")
    return "\n\n---\n\n".join(parts)


def _normalize_subreddit(name):
    if not name:
        return None
    name = name.strip()
    if name.lower().startswith("r/"):
        name = name[2:]
    return name


def _canonical_subreddit(name):
    n = _normalize_subreddit(name)
    if not n:
        return None
    return f"r/{n}"


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
):
    from pipeline import prompts

    explorer = _load_explorer()
    client_mod = _load_explorer_client()

    target = _normalize_subreddit(subreddit)
    suggestions = []

    if records is None:
        fetcher = client_mod.get_fetcher()
        try:
            if target:
                records = explorer.list_subreddit(target, fetcher=fetcher, sort=sort, limit=limit, time_filter=time_filter)
                records += explorer.search_posts(topic, fetcher=fetcher, subreddits=target, sort="relevance", time_filter="all", limit=limit)
            else:
                records = explorer.search_posts(topic, fetcher=fetcher, sort=sort, time_filter=time_filter, limit=limit)
        finally:
            fetcher.close()

    if suggest_subreddit and not target:
        llm = _load_llm()
        corpus = _build_corpus(records[:limit])
        raw = llm.chat_json(
            messages=[
                {"role": "system", "content": "You output only valid JSON."},
                {"role": "user", "content": prompts.SUBREDDIT_SUGGEST_PROMPT.format(topic=topic, corpus=corpus)},
            ],
            temperature=0.2,
        )
        suggestions = [f"r/{s.lstrip('r/')}" for s in raw.get("subreddits", [])]
    elif not target:
        counts = {}
        for rec in records:
            sub = rec.get("subreddit", "unknown")
            if not sub.startswith("r/"):
                sub = f"r/{sub}"
            counts[sub] = counts.get(sub, 0) + 1
        suggestions = sorted(counts, key=counts.get, reverse=True)[:5]

    patterns = {}
    if records:
        llm = _load_llm()
        corpus = _build_corpus(records[:limit])
        patterns = llm.chat_json(
            messages=[
                {"role": "system", "content": "You output only valid JSON."},
                {"role": "user", "content": prompts.RESEARCH_PROMPT.format(topic=topic, subreddit=_canonical_subreddit(target or "all"), corpus=corpus)},
            ],
            temperature=0.2,
        )

    return {
        "subreddit": _canonical_subreddit(target),
        "suggestions": suggestions,
        "records": records,
        "patterns": patterns,
        "language": language,
    }


def _load_explorer_client():
    client_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "client.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_client", client_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_researcher.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/pipeline/researcher.py skills/reddit-publish/tests/test_researcher.py
git commit -m "add reddit-publish researcher with explore integration and pattern extraction"
```

---

### Task 4: Implement `pipeline/drafter.py`

**Files:**

- Create: `skills/reddit-publish/pipeline/drafter.py`
- Create: `skills/reddit-publish/tests/test_drafter.py`

**Interfaces:**

- Consumes: `src/common/llm.py` (`chat_json`), `pipeline/prompts.py` (`DRAFT_PROMPT`).
- Produces: `draft(topic, research, *, subreddit=None, style="casual", image_path=None, image_prompt=None, image_url=None, link_url=None, language="en", kind=None) -> dict`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_drafter.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import drafter


def test_draft_generates_self_post(monkeypatch):
    research = {
        "subreddit": "r/AskReddit",
        "patterns": {"tone": "casual", "hook_patterns": ["question"]},
        "records": [],
        "language": "en",
    }

    def fake_llm(messages, **kwargs):
        return json.dumps({
            "title": "What is the best advice you ever received?",
            "body": "Just curious what others think.",
            "kind": "self",
            "url": "",
            "image_prompt": "",
            "inspiration": [],
        })

    monkeypatch.setattr(drafter, "_load_llm", lambda: type("Llm", (), {"chat_json": fake_llm})())

    result = drafter.draft("advice", research)
    assert result["kind"] == "self"
    assert result["title"].startswith("What")
    assert result["body"]
    assert result["subreddit"] == "r/AskReddit"
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_drafter.py -v
```

Expected: Module or attribute error.

- [ ] **Step 3: Write `pipeline/drafter.py`**

```python
import importlib.util
import json
from pathlib import Path


DEFAULT_STYLE = "casual"
STYLE_PRESETS = ("casual", "story", "question", "helpful", "hot_take", "meme", "discussion")


def _load_llm():
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _resolve_style(style: str | None) -> str:
    if not style:
        return DEFAULT_STYLE
    style = style.strip()
    if style in STYLE_PRESETS:
        return style
    return f"custom: {style}"


def _resolve_subreddit(research: dict, subreddit: str | None) -> str:
    if subreddit:
        s = subreddit.strip()
        return s if s.startswith("r/") else f"r/{s}"
    if research.get("subreddit"):
        return research["subreddit"]
    if research.get("suggestions"):
        return research["suggestions"][0]
    raise ValueError("No target subreddit in research output and none provided")


def _infer_kind(kind, image_path, image_prompt, image_url, link_url):
    if kind:
        return kind
    if link_url:
        return "link"
    if image_path or image_prompt or image_url:
        return "image"
    return "self"


def _build_patterns_text(patterns: dict) -> str:
    if not patterns:
        return ""
    parts = []
    for key, value in patterns.items():
        parts.append(f"{key}: {json.dumps(value)}")
    return "\n".join(parts)


def draft(
    topic: str,
    research: dict,
    *,
    subreddit: str | None = None,
    style: str | None = DEFAULT_STYLE,
    image_path: str | None = None,
    image_prompt: str | None = None,
    image_url: str | None = None,
    link_url: str | None = None,
    language: str = "en",
    kind: str | None = None,
):
    from pipeline import prompts

    target_sub = _resolve_subreddit(research, subreddit)
    resolved_style = _resolve_style(style)
    resolved_kind = _infer_kind(kind, image_path, image_prompt, image_url, link_url)

    llm = _load_llm()
    raw = llm.chat_json(
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompts.DRAFT_PROMPT.format(
                subreddit=target_sub.lstrip("r/"),
                topic=topic,
                style=resolved_style,
                language=language,
                patterns=_build_patterns_text(research.get("patterns", {})),
            )},
        ],
        temperature=0.5,
    )

    title = raw.get("title", "").strip()
    body = raw.get("body", "").strip()
    if len(title) > 300:
        title = title[:300]

    return {
        "title": title,
        "body": body,
        "kind": resolved_kind,
        "subreddit": target_sub,
        "style": style or DEFAULT_STYLE,
        "language": language,
        "url": link_url or raw.get("url", ""),
        "image_path": image_path or "",
        "image_prompt": image_prompt or raw.get("image_prompt", "") or image_url or "",
        "inspiration": raw.get("inspiration", []),
    }
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_drafter.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/pipeline/drafter.py skills/reddit-publish/tests/test_drafter.py
git commit -m "add reddit-publish drafter with style presets and kind inference"
```

---

### Task 5: Implement `pipeline/imager.py`

**Files:**

- Create: `skills/reddit-publish/pipeline/imager.py`
- Create: `skills/reddit-publish/tests/test_imager.py`

**Interfaces:**

- Consumes: `pipeline/paths.py` (`images_dir`), `openai` (`images.generate`), `requests`.
- Produces: `resolve_image(image_path=None, image_url=None, image_prompt=None, out_dir=None) -> Path`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_imager.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import imager


def test_resolve_image_from_path(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"fake png")
    result = imager.resolve_image(image_path=str(img), out_dir=tmp_path)
    assert result.exists()
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_imager.py -v
```

Expected: Module/attribute error.

- [ ] **Step 3: Write `pipeline/imager.py`**

```python
import mimetypes
import os
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests


def _load_paths():
    from pipeline import paths
    return paths


def _validate_image(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        raise ValueError(f"Unsupported image format: {path.suffix}")


def _download_image(url: str, out_dir: Path) -> Path:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    parsed = urlparse(url)
    name = Path(parsed.path).name or "image"
    if not name or "." not in name:
        name = "downloaded_image.png"
    dest = out_dir / name
    dest.write_bytes(response.content)
    _validate_image(dest)
    return dest


def _generate_image(prompt: str, out_dir: Path, model: str | None = None) -> Path:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    model_name = model or os.getenv("OPENAI_IMAGE_MODEL") or "dall-e-3"
    response = client.images.generate(prompt=prompt, model=model_name, n=1, size="1024x1024")
    image_url = response.data[0].url
    return _download_image(image_url, out_dir)


def resolve_image(
    image_path: str | None = None,
    image_url: str | None = None,
    image_prompt: str | None = None,
    out_dir: Path | None = None,
) -> Path:
    paths = _load_paths()
    if out_dir is None:
        out_dir = paths.images_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    if image_path:
        src = Path(image_path)
        _validate_image(src)
        dest = out_dir / src.name
        shutil.copy2(src, dest)
        return dest

    if image_url:
        return _download_image(image_url, out_dir)

    if image_prompt:
        return _generate_image(image_prompt, out_dir)

    raise ValueError("One of image_path, image_url, or image_prompt is required")
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_imager.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/pipeline/imager.py skills/reddit-publish/tests/test_imager.py
git commit -m "add reddit-publish imager with path, url, and dalle support"
```

---

### Task 6: Implement `pipeline/publisher.py`

**Files:**

- Create: `skills/reddit-publish/pipeline/publisher.py`
- Create: `skills/reddit-publish/tests/test_publisher.py`

**Interfaces:**

- Consumes: `reddit-auth/pipeline/auth.py` (`ensure_authenticated_page`), `reddit-auth.Session`.
- Produces: `Publisher.create()` and `Publisher.publish(...)` returning `{post_id, post_url, permalink, subreddit, title}`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_publisher.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import publisher


def test_publish_self_post(monkeypatch):
    page_calls = []

    class FakePage:
        def evaluate(self, script, arg=None):
            page_calls.append(arg)
            return {"ok": True, "status": 200, "body": '{"json": {"data": {"url": "/r/test/comments/abc123/title", "id": "abc123"}}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    p = publisher.Publisher(FakeSession())
    result = p.publish(subreddit="test", title="Hello", kind="self", body="body text")
    assert result["post_id"] == "abc123"
    assert page_calls
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_publisher.py -v
```

Expected: Module/attribute error.

- [ ] **Step 3: Write `pipeline/publisher.py`**

```python
import json
import time
import urllib.parse
from pathlib import Path

import requests


PUBLIC_BASE = "https://www.reddit.com"


def _load_auth():
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Publisher:
    def __init__(self, session):
        self._session = session
        self._modhash = None

    @classmethod
    def create(cls, headless: bool = False):
        auth = _load_auth()
        session = auth.ensure_authenticated_page(headless=headless)
        return cls(session)

    def _fetch_modhash(self):
        page = self._session.page
        result = page.evaluate(
            """
            async ([url, timeout_ms]) => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), timeout_ms);
                try {
                    const res = await fetch(url, { signal: controller.signal, credentials: 'include' });
                    const text = await res.text();
                    return {ok: res.ok, status: res.status, body: text};
                } catch (err) {
                    return {ok: false, error: err.toString()};
                } finally {
                    clearTimeout(timer);
                }
            }
            """,
            [f"{PUBLIC_BASE}/api/v1/me.json", 10000],
        )
        if not result.get("ok"):
            raise RuntimeError(f"Could not fetch user profile: {result}")
        data = json.loads(result["body"])
        me = data.get("data", data)
        self._modhash = me.get("modhash") or ""
        if not me.get("name"):
            raise RuntimeError("Not logged in")

    def _post_json(self, path: str, payload: dict) -> dict:
        if self._modhash is None:
            self._fetch_modhash()

        body = urllib.parse.urlencode({**payload, "api_type": "json", "uh": self._modhash})
        page = self._session.page

        time.sleep(0.5)
        result = page.evaluate(
            """
            async ([url, body, timeout_ms]) => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), timeout_ms);
                try {
                    const res = await fetch(url, {
                        method: 'POST',
                        signal: controller.signal,
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        body,
                    });
                    const text = await res.text();
                    return {ok: res.ok, status: res.status, body: text};
                } catch (err) {
                    return {ok: false, error: err.toString()};
                } finally {
                    clearTimeout(timer);
                }
            }
            """,
            [f"{PUBLIC_BASE}{path}", body, 30000],
        )
        if not result.get("ok"):
            raise RuntimeError(f"Reddit POST failed: {result.get('status')} {result.get('body', '')[:200]}")
        return json.loads(result["body"])

    def _upload_media(self, image_path: Path) -> str:
        data = self._post_json("/api/media/asset.json", {"filepath": image_path.name, "mimetype": "image/png"})
        lease = data.get("json", {}).get("data", {})
        upload_url = lease.get("upload_url") or lease.get("action")
        fields = lease.get("fields", [])
        if not upload_url:
            raise RuntimeError("Could not get media upload lease")

        files = {"file": image_path.read_bytes()}
        form = {f["name"]: f["value"] for f in fields} if fields else {}
        response = requests.post(upload_url, data=form, files=files, timeout=60)
        response.raise_for_status()

        asset_url = lease.get("asset_url")
        if not asset_url:
            raise RuntimeError("Could not determine asset URL after upload")
        return asset_url

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
        sr = subreddit.lstrip("r/")
        payload = {
            "sr": sr,
            "title": title,
            "nsfw": "true" if nsfw else "false",
            "spoiler": "true" if spoiler else "false",
            "resubmit": "true",
        }

        if kind == "self":
            payload["kind"] = "self"
            payload["text"] = body or ""
        elif kind == "link":
            payload["kind"] = "link"
            payload["url"] = url or ""
        elif kind == "image":
            if not image_path:
                raise ValueError("image_path is required for image posts")
            asset_url = self._upload_media(Path(image_path))
            payload["kind"] = "image"
            payload["url"] = asset_url
        else:
            raise ValueError(f"Unknown kind: {kind}")

        data = self._post_json("/api/submit", payload)
        if data.get("json", {}).get("errors"):
            raise RuntimeError(f"Reddit rejected the post: {data['json']['errors']}")

        post_data = data.get("json", {}).get("data", {})
        post_url = post_data.get("url", "")
        post_id = post_data.get("id", "")
        permalink = post_url.replace("https://www.reddit.com", "") if post_url.startswith("https://www.reddit.com") else post_data.get("permalink", "")

        return {
            "post_id": post_id,
            "post_url": post_url or f"https://www.reddit.com{permalink}",
            "permalink": permalink,
            "subreddit": f"r/{sr}",
            "title": title,
        }

    def close(self) -> None:
        if self._session:
            self._session.close()
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_publisher.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/pipeline/publisher.py skills/reddit-publish/tests/test_publisher.py
git commit -m "add reddit-publish publisher with browser-based submit and media upload"
```

---

### Task 7: Implement `scripts/preflight.py`

**Files:**

- Create: `skills/reddit-publish/scripts/preflight.py`
- Create: `skills/reddit-publish/tests/test_preflight.py`

**Interfaces:**

- Consumes: `reddit-auth/pipeline/auth.py` (`validate_credentials`), `src/common/llm.py` (`available`).
- Produces: `preflight()` returns JSON with `env_ok`, `deps_ok`, `reddit_ok`, `ai_ok`, `image_ok`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_preflight.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import preflight


def test_preflight_returns_json(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "_load_auth", lambda: type("Auth", (), {"validate_credentials": lambda: (True, "ok")})())
    monkeypatch.setattr(preflight, "_load_llm", lambda: type("Llm", (), {"available": lambda: (True, "ok")})())
    result = preflight.preflight()
    assert result["deps_ok"] is True
    assert result["reddit_ok"] is True
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_preflight.py -v
```

Expected: Module/attribute error.

- [ ] **Step 3: Write `scripts/preflight.py`**

```python
import importlib
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


REQUIRED_DEPS = ["dotenv", "requests", "rustwright", "praw", "openai"]


def _load_auth():
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_llm():
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_deps(dependency_names=None):
    if dependency_names is None:
        dependency_names = REQUIRED_DEPS
    failed = []
    for name in dependency_names:
        try:
            importlib.import_module(name)
        except ImportError:
            failed.append(name)
    return (len(failed) == 0, failed)


def check_ai():
    llm = _load_llm()
    return llm.available()


def check_image():
    if not os.getenv("OPENAI_API_KEY"):
        return False, "OPENAI_API_KEY is required for image generation"
    try:
        import openai
        return True, "openai package available"
    except ImportError:
        return False, "openai package not installed"


def preflight():
    deps_ok, missing_deps = check_deps()

    reddit_ok = False
    reddit_message = "dependencies missing"
    if deps_ok:
        auth = _load_auth()
        reddit_ok, reddit_message = auth.validate_credentials()

    ai_ok, ai_message = (False, "")
    image_ok, image_message = (False, "")
    if deps_ok:
        ai_ok, ai_message = check_ai()
        image_ok, image_message = check_image()

    result = {
        "env_ok": True,
        "deps_ok": deps_ok,
        "reddit_ok": reddit_ok,
        "ai_ok": ai_ok,
        "image_ok": image_ok,
    }
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not reddit_ok:
        result["reddit_error"] = reddit_message
    if not ai_ok:
        result["ai_error"] = ai_message
    if not image_ok:
        result["image_error"] = image_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if all(result[k] for k in ["deps_ok", "reddit_ok"]) else 1)
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_preflight.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/scripts/preflight.py skills/reddit-publish/tests/test_preflight.py
git commit -m "add reddit-publish preflight with deps, auth, ai, and image checks"
```

---

### Task 8: Implement `scripts/research.py`

**Files:**

- Create: `skills/reddit-publish/scripts/research.py`
- Create: `skills/reddit-publish/tests/test_scripts_research.py`

**Interfaces:**

- Consumes: `pipeline/researcher.py` (`research`), `pipeline/paths.py` (`records_dir`).

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_scripts_research.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import research


def test_research_main(monkeypatch, capsys, tmp_path):
    def fake_research(*args, **kwargs):
        return {"subreddit": "r/test", "suggestions": [], "records": [], "patterns": {}, "language": "en"}

    monkeypatch.setattr(research, "researcher_research", fake_research)
    monkeypatch.setattr(research, "records_dir", lambda: tmp_path)
    code = research.main(["test topic"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["success"] is True
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_scripts_research.py -v
```

Expected: Module/attribute error.

- [ ] **Step 3: Write `scripts/research.py`**

```python
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import paths
from pipeline.researcher import research


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Research Reddit for post inspiration.")
    parser.add_argument("topic", help="The post topic.")
    parser.add_argument("--subreddit", default=None, help="Target subreddit.")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", default="top", choices=["top", "hot", "relevance", "new"])
    parser.add_argument("--time", default="month", choices=["day", "week", "month", "year", "all"], dest="time_filter")
    parser.add_argument("--suggest-subreddit", action="store_true")
    parser.add_argument("--language", default="en")
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = research(
            args.topic,
            subreddit=args.subreddit,
            limit=args.limit,
            sort=args.sort,
            time_filter=args.time_filter,
            suggest_subreddit=args.suggest_subreddit,
            language=args.language,
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "research_error"}))
        return 1

    out_path = Path(args.out) if args.out else paths.records_dir() / f"research_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "records_path": str(out_path), "subreddit": result.get("subreddit")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_scripts_research.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/scripts/research.py skills/reddit-publish/tests/test_scripts_research.py
git commit -m "add reddit-publish research script"
```

---

### Task 9: Implement `scripts/draft.py`

**Files:**

- Create: `skills/reddit-publish/scripts/draft.py`
- Create: `skills/reddit-publish/tests/test_scripts_draft.py`

**Interfaces:**

- Consumes: `pipeline/drafter.py` (`draft`), `pipeline/imager.py` (`resolve_image`), `pipeline/paths.py` (`drafts_dir`).

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_scripts_draft.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import draft


def test_draft_main(monkeypatch, capsys, tmp_path):
    research_path = tmp_path / "research.json"
    research_path.write_text(json.dumps({
        "subreddit": "r/test",
        "patterns": {},
        "records": [],
        "language": "en",
        "suggestions": [],
    }))

    def fake_draft(*args, **kwargs):
        return {"title": "T", "body": "B", "kind": "self", "subreddit": "r/test", "style": "casual", "language": "en"}

    monkeypatch.setattr(draft, "drafter_draft", fake_draft)
    monkeypatch.setattr(draft, "drafts_dir", lambda: tmp_path)
    code = draft.main([str(research_path)])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_scripts_draft.py -v
```

Expected: Module/attribute error.

- [ ] **Step 3: Write `scripts/draft.py`**

```python
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import paths
from pipeline.drafter import draft
from pipeline.imager import resolve_image


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Draft a Reddit post from research.")
    parser.add_argument("research_json", help="Path to research JSON.")
    parser.add_argument("--subreddit", default=None)
    parser.add_argument("--style", default="casual")
    parser.add_argument("--image-path", default=None)
    parser.add_argument("--image-url", default=None)
    parser.add_argument("--image-prompt", default=None)
    parser.add_argument("--link-url", default=None)
    parser.add_argument("--language", default="en")
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    research = json.loads(Path(args.research_json).read_text())

    try:
        d = draft(
            research.get("language", "en"),
            research,
            subreddit=args.subreddit,
            style=args.style,
            image_path=args.image_path,
            image_url=args.image_url,
            image_prompt=args.image_prompt,
            link_url=args.link_url,
            language=args.language,
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "draft_error"}))
        return 1

    if d["kind"] == "image" and not d["image_path"]:
        try:
            img_path = resolve_image(
                image_path=args.image_path,
                image_url=args.image_url,
                image_prompt=d["image_prompt"],
            )
            d["image_path"] = str(img_path)
        except Exception as exc:
            print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "image_error"}))
            return 1

    out_path = Path(args.out) if args.out else paths.drafts_dir() / f"draft_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(d, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "draft_path": str(out_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_scripts_draft.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/scripts/draft.py skills/reddit-publish/tests/test_scripts_draft.py
git commit -m "add reddit-publish draft script with image resolution"
```

---

### Task 10: Implement `scripts/publish.py`

**Files:**

- Create: `skills/reddit-publish/scripts/publish.py`
- Create: `skills/reddit-publish/tests/test_scripts_publish.py`

**Interfaces:**

- Consumes: `pipeline/publisher.py` (`Publisher`), `pipeline/paths.py`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-publish/tests/test_scripts_publish.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import publish


def test_publish_main_dry_run(monkeypatch, capsys, tmp_path):
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(json.dumps({
        "title": "T",
        "body": "B",
        "kind": "self",
        "subreddit": "r/test",
    }))

    def fake_publish(*args, **kwargs):
        return {"post_id": "abc", "post_url": "https://reddit.com/abc", "permalink": "/r/test/abc", "subreddit": "r/test", "title": "T"}

    class FakePublisher:
        publish = fake_publish

        def close(self):
            pass

    monkeypatch.setattr(publish, "Publisher", FakePublisher)
    monkeypatch.setattr(publish, "_load_publisher", lambda: FakePublisher())
    code = publish.main([str(draft_path), "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
```

- [ ] **Step 2: Run the failing test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_scripts_publish.py -v
```

Expected: Module/attribute error.

- [ ] **Step 3: Write `scripts/publish.py`**

```python
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import paths
from pipeline.publisher import Publisher


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Publish a drafted Reddit post.")
    parser.add_argument("draft_json", help="Path to draft JSON.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    draft = json.loads(Path(args.draft_json).read_text())

    if args.dry_run:
        print(json.dumps({"event": "done", "success": True, "dry_run": True, "draft": draft}))
        return 0

    publisher = None
    try:
        publisher = Publisher.create()
        result = publisher.publish(
            subreddit=draft["subreddit"],
            title=draft["title"],
            kind=draft["kind"],
            body=draft.get("body"),
            url=draft.get("url"),
            image_path=draft.get("image_path"),
            nsfw=draft.get("nsfw", False),
            spoiler=draft.get("spoiler", False),
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "publish_error"}))
        return 1
    finally:
        if publisher:
            publisher.close()

    out_path = Path(args.out) if args.out else paths.drafts_dir() / f"publish_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test**

```bash
cd skills/reddit-publish
python -m pytest tests/test_scripts_publish.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-publish/scripts/publish.py skills/reddit-publish/tests/test_scripts_publish.py
git commit -m "add reddit-publish publish script with dry-run support"
```

---

### Task 11: Write runtime guides and failure recovery

**Files:**

- Create: `skills/reddit-publish/resources/DEVIN.md`
- Create: `skills/reddit-publish/resources/CLAUDE.md`
- Create: `skills/reddit-publish/resources/failure-recovery.md`

- [ ] **Step 1: Write `resources/DEVIN.md`**

````markdown
# Devin Runtime Guide for reddit-publish

## Phase 1 — Preflight

```bash
python "<skill_dir>/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true. `ai_ok` is required for AI-generated drafts; `image_ok` is required for AI image generation.

## Phase 2 — Research

```bash
python "<skill_dir>/scripts/research.py" "<topic>" --subreddit r/AskReddit --suggest-subreddit
```

If no subreddit is known, omit `--subreddit` and use `--suggest-subreddit`. Note `records_path` from the `done` event.

## Phase 3 — Draft

```bash
python "<skill_dir>/scripts/draft.py" "<records_path>" --style casual --language en
```

If the research output had no target subreddit, pass `--subreddit r/YourChoice`.

## Phase 4 — Publish (dry-run first)

```bash
python "<skill_dir>/scripts/publish.py" "<draft_path>" --dry-run
python "<skill_dir>/scripts/publish.py" "<draft_path>"
```

## Phase 5 — Surface

Tell the user the post URL and title. Do not paste full JSON.
````

- [ ] **Step 2: Write `resources/CLAUDE.md`**

````markdown
# Claude Code Runtime Guide for reddit-publish

## Phase 1 — Preflight

Run with the `Bash` tool:

```bash
python "<skill_dir>/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true.

## Phase 2 — Research

```bash
python "<skill_dir>/scripts/research.py" "<topic>" --suggest-subreddit
```

## Phase 3 — Draft

```bash
python "<skill_dir>/scripts/draft.py" "<records_path>" --style casual --language en
```

## Phase 4 — Publish

```bash
python "<skill_dir>/scripts/publish.py" "<draft_path>" --dry-run
python "<skill_dir>/scripts/publish.py" "<draft_path>"
```

## Phase 5 — Surface

Return the post URL and title. If `success` is false, read `code` and `error`, then check `resources/failure-recovery.md`.

````

- [ ] **Step 3: Write `resources/failure-recovery.md`**

```markdown
# Failure recovery

| Error / symptom | Likely cause | Fix |
| --- | --- | --- |
| `deps_ok: false` | Missing Python packages | `uv pip install -r skills/reddit-publish/requirements.txt` |
| `reddit_ok: false` | Stale session or missing credentials | Re-run `reddit-auth/scripts/login.py` or check `.env` |
| `ai_ok: false` | No `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | Set as shell environment variables (not `.env`) |
| `image_ok: false` | No `OPENAI_API_KEY` for image generation | Set `OPENAI_API_KEY` or provide `--image-path` / `--image-url` |
| `code: auth_failure` | Browser session expired | Re-run `reddit-auth/scripts/login.py` |
| `code: not_found` | Subreddit does not exist or is private | Check the subreddit name |
| `code: rate_limited` | Too many requests | Wait and retry |
| `code: publish_rejected` | Subreddit rules (title too long, missing flair, etc.) | Edit the draft manually and retry |
| `code: image_invalid` | Bad image URL or unsupported format | Try a different image or convert to PNG/JPG |
| `code: draft_error` | LLM returned invalid JSON | Re-run with a simpler topic or style |
```

- [ ] **Step 4: Commit**

```bash
git add skills/reddit-publish/resources/
git commit -m "add reddit-publish runtime guides and failure recovery"
```

---

### Task 12: Integration and verification

**Files:**

- Modify: `skills/reddit-publish/tests/` (ensure all tests run together)
- Modify: `README.md` (update skill catalog status)

- [ ] **Step 1: Run all tests**

```bash
cd skills/reddit-publish
uv pip install -r requirements.txt
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run lint on SKILL.md and resources**

```bash
cd skills/reddit-publish
npx markdownlint-cli SKILL.md resources/*.md
```

Expected: no errors.

- [ ] **Step 3: Update `README.md` skill catalog status**

```markdown
| reddit-publish | Spec + plan complete | Content publishing | Research, draft, and publish text/link/image posts |
```

- [ ] **Step 4: Commit**

```bash
git add skills/reddit-publish tests README.md
git commit -m "complete reddit-publish tests, lint, and catalog update"
```

---

## Self-review

### Spec coverage

| Spec section | Task that implements it |
| --- | --- |
| File layout | Task 1 |
| `pipeline/paths.py` | Task 1 |
| `pipeline/prompts.py` | Task 2 |
| `pipeline/researcher.py` | Task 3 |
| `pipeline/drafter.py` | Task 4 |
| `pipeline/imager.py` | Task 5 |
| `pipeline/publisher.py` | Task 6 |
| `scripts/preflight.py` | Task 7 |
| `scripts/research.py` | Task 8 |
| `scripts/draft.py` | Task 9 |
| `scripts/publish.py` | Task 10 |
| Runtime guides | Task 11 |
| Error handling / codes | Tasks 6–10 |

### Placeholder scan

No `TBD`, `TODO`, or "implement later" steps remain. Each task contains exact file paths, code, commands, expected output, and a commit command.

### Type consistency

- `research()` returns `{subreddit, suggestions, records, patterns, language}`.
- `draft()` returns the dict consumed by `publish.py`.
- `resolve_image()` returns `Path`.
- `Publisher.publish()` returns `{post_id, post_url, permalink, subreddit, title}`.
