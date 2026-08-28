---
name: reddit-validator
description: Use when the user wants to validate a business idea, product, or niche using Reddit discussions and get a scored HTML report.
---

# Reddit Validator

Validate a business idea by scraping Reddit posts and comments, using the host agent's own LLM to analyze the corpus, and producing a scored HTML report.

## When to use

- "验证创业想法", "调研 XX 在 Reddit 上的反响", "这个产品有市场吗"
- "validate business idea", "is X a good business idea", "analyze market demand for X"
- "what pain points do people have around X"
- The user provides a product, niche, or idea and wants market signals, pain points, sentiment, competitive landscape, or a go/no-go recommendation.
- The user references this repo's pipeline, orchestrator, or asks for a Reddit report.

Do NOT use for: pure keyword research, SEO tasks, generic LLM brainstorming, or data sources other than Reddit.

## Prerequisites

- Python 3.10+.
- Dependencies installed: `pip install -r <skill_dir>/requirements.txt`.
- **Reddit access (choose one):**
  - Rustwright browser login (default, no app needed). Set `REDDIT_LOGIN_METHOD=rustwright` in `.env`. The browser login is handled by the `reddit-auth` skill.
  - Bearer token or script-app credentials: paste `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` in `.env`. Optional `REDDIT_USERNAME` / `REDDIT_PASSWORD` for PRAW.
- **Optional AI analysis:** Set `OPENAI_API_KEY` or `OPENROUTER_API_KEY` (and optionally `OPENAI_BASE_URL`) as **shell environment variables** for AI-generated analysis. Do not put these secrets in `.env`. If not set, the host agent provides the analysis manually.

## File layout

```text
<skill_dir>/
├── SKILL.md
├── requirements.txt
├── pipeline/
│   ├── scraper.py
│   ├── report.py
│   └── runner.py
├── scripts/
│   ├── preflight.py
│   ├── run_pipeline.py
│   ├── render_report.py
│   ├── extract_report.py
│   └── recover.py
└── resources/
    ├── DEVIN.md
    ├── CLAUDE.md
    ├── param-matrix.md
    ├── failure-recovery.md
    └── report-anatomy.md
```

All scripts emit JSON or JSONL. Outputs (reports, checkpoints, logs, records) are managed by the skill and land under `<skill_dir>` — see `pipeline/paths.py`.

## Workflow

### Phase 0 — Decide if this skill applies

Apply when the user provides an idea/product/niche AND wants market validation, pain-point discovery, demand estimation, sentiment, competitive landscape, go/no-go, or a Reddit-based report. If no data source is stated but the user mentions "Reddit", "subreddit", "post", or English-language markets, default to this skill.

### Phase 1 — Preflight

Run:

```bash
python "<skill_dir>/scripts/preflight.py"
```

Only proceed when `env_ok && deps_ok && reddit_ok` are all true. See `resources/failure-recovery.md` for common fixes.

If the user wants AI-generated analysis, `preflight` will also report `ai_ok`. When `ai_ok` is false, ask the user to set `OPENAI_API_KEY` or `OPENROUTER_API_KEY` as shell environment variables before continuing.

### Phase 2 — Pick a profile

Ask the user to pick a profile if they have not specified one:

- **fast** — quick smoke test (~5 min, 3 subreddits × 5 posts)
- **standard** — regular validation (~30 min, 5 subreddits × 25 posts)
- **deep** — high-stakes decisions (~60 min, 10 subreddits × 100 posts)

See `resources/param-matrix.md` for exact numbers. When running `run_pipeline.py` directly without `--profile`, the script will prompt for a profile if the terminal is interactive.

### Phase 3 — Scrape Reddit

Launch the scraper and poll its structured JSONL output:

```bash
python "<skill_dir>/scripts/run_pipeline.py" "<idea>" --profile standard
```

This only scrapes; it does not run an LLM. On `done` with `success:true`, note `records_path` and `run_id` and go to Phase 4. On `done` with `success:false`, use `recover.py` or `resources/failure-recovery.md`.

When `REDDIT_LOGIN_METHOD=rustwright` (or `playwright`), `reddit-validator` calls `reddit-auth` to open a real Chromium window on `https://www.reddit.com`. The user clicks **Log in** and completes the flow. `reddit-auth` emits a `login` stage event, then the scraper continues once a successful `/api/v1/me` response is detected.

### Phase 4 — Analyze

1. Read the `records_path` from Phase 3.
1. If `OPENAI_API_KEY` or `OPENROUTER_API_KEY` is configured, use `pipeline/analyzer.py` to generate the analysis JSON. Otherwise, use the host agent's own model to produce the structured JSON matching this schema:

```json
{
  "score": 70,
  "market_snapshot": ["..."],
  "pain_points": [{ "text": "...", "weight": 3 }],
  "existing_solutions": ["..."],
  "opportunities": [{ "text": "...", "weight": 3 }],
  "how_to_win": ["..."],
  "recommendations": ["..."],
  "comment_tags": {
    "positive": 5,
    "negative": 3,
    "question": 2,
    "suggestion": 1
  }
}
```

1. Save it as `<skill_dir>/analysis.json` or another path.

### Phase 5 — Render the report

```bash
python "<skill_dir>/scripts/render_report.py" --analysis "<analysis.json>" --run-id "<run_id>"
```

This produces the HTML report and appends a final `done` event to the run log.

### Phase 6 — Surface results

Extract the summary:

```bash
python "<skill_dir>/scripts/extract_report.py" --run-id "<run_id>"
```

Tell the user the score, top 3 pain points, top 3 opportunities, report path, and run id. Do not paste the full HTML.

## Runtime-specific instructions

For exact tool-calling details, read `resources/DEVIN.md` if you are Devin, or `resources/CLAUDE.md` if you are Claude Code.

## Operating principles

- Never reimplement pipeline stages; call `run_pipeline.py` for scraping and `render_report.py` for rendering.
- Always run preflight first.
- Background the scraper; it can take 3–30 min.
- Parse JSONL, don't regex human text.
- Be honest about scores.
- Resume from checkpoint instead of restarting when possible.
