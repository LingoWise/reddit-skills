---
name: reddit-validator
description: Use when the user wants to validate a business idea, product, or niche using Reddit discussions and get a scored HTML report.
---

# Reddit Validator: for Creative or Business Idea

Validate a business idea by scraping Reddit posts and comments, then running a multi-agent LLM analysis that produces a scored HTML report.

## When to use

- "验证创业想法", "调研 XX 在 Reddit 上的反响", "这个产品有市场吗"
- "validate business idea", "is X a good business idea", "analyze market demand for X"
- "what pain points do people have around X"
- The user provides a product, niche, or idea and wants market signals, pain points, sentiment, competitive landscape, or a go/no-go recommendation.
- The user references this repo's pipeline, orchestrator, or asks for a Reddit report.

Do NOT use for: pure keyword research, SEO tasks, generic LLM brainstorming, or data sources other than Reddit.

## Prerequisites

- `.env` with at minimum: `OPENAI_API_KEY`, `OPENAI_BASE_URL` (must end with `/v1`), `OPENAI_MODEL`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`.
- Python 3.10+.
- Dependencies installed: `pip install -r <skill_dir>/requirements.txt`.
- Reddit app type must be **"script"** at <https://www.reddit.com/prefs/apps>.

## File layout

```text
<skill_dir>/
├── SKILL.md
├── requirements.txt
└── resources/
    ├── DEVIN.md
    ├── CLAUDE.md
    ├── param-matrix.md
    ├── failure-recovery.md
    └── report-anatomy.md
```

All scripts emit JSON or JSONL. Outputs (reports, checkpoints, logs) are managed by the skill and land under `<skill_dir>` — see `pipeline/paths.py`.

## Workflow

### Phase 0 — Decide if this skill applies

Apply when the user provides an idea/product/niche AND wants market validation, pain-point discovery, demand estimation, sentiment, competitive landscape, go/no-go, or a Reddit-based report. If no data source is stated but the user mentions "Reddit", "subreddit", "post", or English-language markets, default to this skill.

### Phase 1 — Preflight

Run:

```bash
python "<skill_dir>/scripts/preflight.py"
```

Only proceed when `env_ok && deps_ok && reddit_ok && llm_ok` are all true. See `resources/failure-recovery.md` for common fixes.

### Phase 2 — Pick a profile

Default to **standard**. Choose **fast** for quick smoke tests, **standard** for normal validation, **deep** for high-stakes decisions. See `resources/param-matrix.md` for exact numbers.

### Phase 3 — Run the pipeline

Launch the pipeline and poll its structured JSONL output:

```bash
python "<skill_dir>/scripts/run_pipeline.py" "<idea>" --profile standard
```

Key events: `run_started`, `stage`, `done`. On `done` with `success:true`, go to Phase 5. On `done` with `success:false`, go to Phase 4.

### Phase 4 — Recover from failure

Use:

```bash
python "<skill_dir>/scripts/recover.py" --resume-last --idea "<idea>" --profile standard
```

For known errors, see `resources/failure-recovery.md` instead of blind retry.

### Phase 5 — Surface results

Extract results:

```bash
python "<skill_dir>/scripts/extract_report.py" --run-id "<run_id>"
```

Tell the user the score, top 3 pain points, top 3 opportunities, report path, and run id. Do not paste the full HTML.

## Runtime-specific instructions

For exact tool-calling details, read `resources/DEVIN.md` if you are Devin, or `resources/CLAUDE.md` if you are Claude Code.

## Operating principles

- Never reimplement pipeline stages; call `run_pipeline.py`.
- Always run preflight first.
- Background the pipeline; it can take 3–30 min.
- Parse JSONL, don't regex human text.
- Be honest about scores.
- Resume from checkpoint instead of restarting when possible.
