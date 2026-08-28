# Reddit Skills

A modular collection of Reddit operation skills for AI agents. Each skill uses **Python + Playwright** to browse Reddit like a human and exposes a clean tool interface through **MCP**, so you can automate discovery, publishing, interaction, and validation to operate a brand or product on Reddit.

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
| reddit-validator | Spec complete | Idea validation via Reddit scraping and LLM analysis | Search, scrape, multi-agent analysis, scored HTML report |
| reddit-auth | Planned | Authentication and session management | Login check, session refresh, credential hygiene |
| reddit-explore | Planned | Discovery and research | Search, subreddit browsing, post details, user profiles |
| reddit-publish | Planned | Content publishing | Text, link, and image post submission |
| reddit-interact | Planned | Social interaction | Comment, reply, upvote, downvote, save |
| reddit-content-ops | Planned | Compound operations | Subreddit analysis, trend tracking, engagement campaigns |

## How it works

1. **Browser layer**: Playwright drives a real browser, with human-like delays, scrolls, and clicks to avoid bot detection.
2. **Skill layer**: Each skill is a self-contained module with a `SKILL.md` contract and a `pipeline/` of Python scripts.
3. **MCP layer**: Skills expose entrypoints an AI agent can call, returning JSON or rendered reports.
4. **Orchestration layer**: The agent composes skills into workflows — for example, validate an idea, then publish a post, then track replies.

## Quickstart

The first skill, `reddit-validator`, has a complete spec in `skills/reddit-validator/SKILL.md`. As skills are implemented, each will follow the same contract:

1. Clone the repo.
2. Read the `SKILL.md` for the skill you want to run.
3. Install its dependencies.
4. Configure the required environment variables.
5. Run its preflight checks.
6. Execute the skill pipeline.

## Adding a new skill

1. Create `skills/<skill-name>/`.
2. Write a `SKILL.md` describing purpose, prerequisites, workflow, error recovery, and operating principles.
3. Implement the `pipeline/` in Python, using Playwright for browser work.
4. Add `requirements.txt` and preflight checks.
5. Expose an MCP-friendly entrypoint.

## License

[MIT](LICENSE)
