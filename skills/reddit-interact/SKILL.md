---
name: reddit-interact
description: Use when the user wants to interact with Reddit content — comment on posts, reply to comments, upvote, downvote, or save posts and comments.
---

# Reddit Interact

Interact with Reddit content: comment on posts, reply to comments, upvote, downvote, and save posts or comments.

## When to use

- "comment on this post"
- "reply to this comment"
- "upvote this post"
- "downvote that comment"
- "save this post for later"

## When NOT to use

- Publishing content (→ `reddit-publish`).
- Browsing or searching Reddit (→ `reddit-explore`).
- Validating a business idea (→ `reddit-validator`).
- Compound operations like trend tracking (→ `reddit-content-ops`, once it exists).

## Prerequisites

- Python 3.10+.
- Dependencies installed: `uv pip install -r skills/reddit-interact/requirements.txt`.
- Reddit authentication via `reddit-auth`.

## Workflow

1. Preflight: `python "skills/reddit-interact/scripts/preflight.py"`
2. Pick an action and run the matching script:
   - Comment: `python "skills/reddit-interact/scripts/comment.py" "<post_url_or_id>" --text "Your comment"`
   - Reply: `python "skills/reddit-interact/scripts/reply.py" "<comment_url_or_id>" --text "Your reply"`
   - Upvote: `python "skills/reddit-interact/scripts/upvote.py" "<url_or_id>"`
   - Downvote: `python "skills/reddit-interact/scripts/downvote.py" "<url_or_id>"`
   - Save: `python "skills/reddit-interact/scripts/save.py" "<url_or_id>"`
3. Read the `done` JSON event.

## Operating principles

- Always run preflight first.
- Use `--dry-run` before the first real action in a session.
- For long comments, use `--text-file` instead of `--text`.
- Respect Reddit rate limits; do not bulk vote or comment.
- `save.py --unsave` reverses a save.
