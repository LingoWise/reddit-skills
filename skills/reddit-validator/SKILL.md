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
  - Playwright browser login (default, no app needed). Set `REDDIT_LOGIN_METHOD=playwright` in `.env`.
  - Bearer token or script-app credentials: paste `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` in `.env`. Optional `REDDIT_USERNAME` / `REDDIT_PASSWORD` for PRAW.

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

### Phase 2 — Pick a profile

Default to **standard**. Choose **fast** for quick smoke tests, **standard** for normal validation, **deep** for high-stakes decisions. See `resources/param-matrix.md` for exact numbers.

### Phase 3 — Scrape Reddit

Launch the scraper and poll its structured JSONL output:

```bash
python "<skill_dir>/scripts/run_pipeline.py" "<idea>" --profile standard
```

This only scrapes; it does not run an LLM. On `done` with `success:true`, note `records_path` and `run_id` and go to Phase 4. On `done` with `success:false`, use `recover.py` or `resources/failure-recovery.md`.

When `REDDIT_LOGIN_METHOD=playwright`, a real browser opens and the user must log in to Reddit. The scraper continues once login is detected.

### Phase 4 — Analyze with the host agent's LLM

1. Read the `records_path` from Phase 3.
2. Use your own model to produce a structured analysis JSON matching this schema:

```json
{
  "score": 70,
  "pain_points": [{ "text": "...", "weight": 3 }],
  "opportunities": [{ "text": "...", "weight": 3 }],
  "recommendations": ["..."],
  "existing_solutions": ["..."],
  "comment_tags": {
    "positive": 5,
    "negative": 3,
    "question": 2,
    "suggestion": 1
  }
}
```

3. Save it as `<skill_dir>/analysis.json` or another path.

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
