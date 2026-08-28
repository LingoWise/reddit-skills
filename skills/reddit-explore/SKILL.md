---
name: reddit-explore
description: Use when the user wants to discover, browse, or research Reddit content — search posts, browse subreddits, read post details with comments, or view user profiles.
---

# Reddit Explore

Discover and research Reddit content: search posts, browse subreddits, read post details with comments, and view user profiles.

## When to use

- "search Reddit for X", "find posts about X", "what's trending on r/X"
- "show me posts from r/X", "browse r/X", "what's hot on r/X"
- "read this post", "get post details", "show comments on this post"
- "look up user X", "what does user X post about", "user X's comment history"
- Another skill (e.g. reddit-validator) needs Reddit data fetched

Do NOT use for: validating a business idea, posting content, voting/commenting, or compound operations like trend tracking.

## Prerequisites

- Python 3.10+.
- Dependencies installed: `pip install -r <skill_dir>/requirements.txt`.
- Reddit access via one of the four auth strategies handled by `reddit-auth`.

## Workflow

1. Preflight: `python "<skill_dir>/scripts/preflight.py"`
2. Pick a capability and run the matching script:
   - Search: `python "<skill_dir>/scripts/search.py" "<query>"`
   - Subreddit: `python "<skill_dir>/scripts/subreddit.py" "<name>"`
   - Post: `python "<skill_dir>/scripts/post.py" "<url_or_id>"`
   - User: `python "<skill_dir>/scripts/user.py" "<name>"`
3. Read the `done` JSON event and the records file.

## Operating principles

- Run preflight first.
- These are fast synchronous queries.
- Return structured JSON; let the agent decide how to present it.
- Reuse a saved browser session when available.
