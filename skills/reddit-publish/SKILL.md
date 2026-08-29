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
