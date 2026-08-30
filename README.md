# Reddit Skills

A modular collection of Reddit operation skills for AI agents. Each skill uses **Python + Rustwright** to browse Reddit like a human and exposes a clean tool interface through **MCP**, so you can automate discovery, publishing, interaction, and validation to operate a brand or product on Reddit.

## Why this exists

Reddit is one of the richest sources of product-market signal, but it is also one of the most hostile to bots and low-effort automation. This project makes it possible to:

- Explore communities, posts, and user profiles at human speed.
- Validate business ideas against real Reddit discussions.
- Publish content and interact with comments authentically.
- Run compound operations like trend tracking and engagement campaigns.

The goal is agentic operations: the agent decides what to do, the skill executes it in a browser, and the result is returned as structured output.

## Stack

- **Python** — orchestration, data processing, and LLM integration.
- **Playwright** — realistic browser control with human-like input, scrolling, and navigation.
- **MCP (Model Context Protocol)** — standard tool interface so an AI agent can discover and call skills.
- **LLMs** — summarization, scoring, content generation, and report writing where appropriate.

## Skill catalog

| Skill | Status | Description | Core Capabilities |
| --- | --- | --- | --- |
| reddit-auth | Complete | Authentication and session management | Rustwright browser login, bearer token, PRAW script app, public fallback, session refresh, credential hygiene |
| reddit-validator | Complete | Idea validation via Reddit scraping and LLM analysis | Search, scrape, multi-agent analysis, scored HTML report, recovery |
| reddit-explore | Complete | Discovery and research | Search posts, browse subreddits, read post details with comments, view user profiles |
| reddit-publish | Complete | Content publishing | Research top content, draft in a chosen style, submit text/link/image posts (with `--dry-run`) |
| reddit-interact | Complete | Social interaction | Comment, reply, upvote, downvote, save |
| reddit-content-ops | Planned | Compound operations | Subreddit analysis, trend tracking, engagement campaigns |

The five completed skills are runnable today. `reddit-content-ops` is a reserved stub.

## How it works

1. **Browser layer**: Rustwright drives a real Chromium browser, with human-like delays, scrolls, and clicks to avoid bot detection.
2. **Skill layer**: Each skill is a self-contained module with a `SKILL.md` contract and a `pipeline/` of Python scripts.
3. **MCP layer**: Skills expose entrypoints an AI agent can call, returning JSON or rendered reports.
4. **Orchestration layer**: The agent composes skills into workflows — for example, validate an idea, then publish a post, then track replies.

## Quickstart

Each completed skill follows the same contract: a `SKILL.md` describing purpose, prerequisites, workflow, and error recovery, plus a `pipeline/` and `scripts/` implemented in Python.

1. Clone the repo.
2. Read the `SKILL.md` for the skill you want to run.
3. Install dependencies: `uv pip install -r skills/<skill-name>/requirements.txt`.
4. Configure environment variables (Reddit credentials in `.env`; `OPENAI_API_KEY` / `OPENROUTER_API_KEY` as shell env vars when AI steps are needed).
5. Run preflight, then the skill's scripts.

### Common first run

Authenticate once with `reddit-auth`, then any other skill reuses the saved session:

```bash
python skills/reddit-auth/scripts/preflight.py
python skills/reddit-auth/scripts/login.py
```

### Per-skill entrypoints

```bash
# reddit-validator — validate an idea and produce a scored HTML report
python skills/reddit-validator/scripts/preflight.py
python skills/reddit-validator/scripts/run_pipeline.py "your idea" --profile standard
python skills/reddit-validator/scripts/extract_report.py --run-id <run_id>

# reddit-explore — search, browse, read posts, look up users
python skills/reddit-explore/scripts/preflight.py
python skills/reddit-explore/scripts/search.py "<query>"
python skills/reddit-explore/scripts/subreddit.py "<name>"
python skills/reddit-explore/scripts/post.py "<url_or_id>"
python skills/reddit-explore/scripts/user.py "<name>"

# reddit-publish — research, draft, and submit a post
python skills/reddit-publish/scripts/preflight.py
python skills/reddit-publish/scripts/research.py "<topic>" [--subreddit ...] [--suggest-subreddit]
python skills/reddit-publish/scripts/draft.py path/to/research.json [--style ...]
python skills/reddit-publish/scripts/publish.py path/to/draft.json [--dry-run]

# reddit-interact — comment, reply, vote, save (all support --dry-run)
python skills/reddit-interact/scripts/preflight.py
python skills/reddit-interact/scripts/comment.py "<post_url_or_id>" --text "..." [--text-file path] [--dry-run]
python skills/reddit-interact/scripts/reply.py "<comment_url_or_id>" --text "..." [--text-file path] [--dry-run]
python skills/reddit-interact/scripts/upvote.py "<url_or_id>" [--dry-run]
python skills/reddit-interact/scripts/downvote.py "<url_or_id>" [--dry-run]
python skills/reddit-interact/scripts/save.py "<url_or_id>" [--unsave] [--dry-run]
```

## Adding a new skill

1. Create `skills/<skill-name>/`.
2. Write a `SKILL.md` describing purpose, prerequisites, workflow, error recovery, and operating principles.
3. Implement the `pipeline/` in Python, using Rustwright for browser work.
4. Add `requirements.txt` and preflight checks.
5. Expose an MCP-friendly entrypoint.

## License

[MIT](LICENSE)
