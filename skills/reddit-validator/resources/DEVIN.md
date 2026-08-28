# Devin Runtime Guide

This guide is for agents running in Devin. It contains the exact tool calls for the `reddit-validator` skill.

## Phase 1 — Preflight

Run:

```bash
python "<skill_dir>/scripts/preflight.py"
```

Read the JSON output and react:

| Field       | On false                                                                                                     |
| ----------- | ------------------------------------------------------------------------------------------------------------ |
| `env_ok`    | Usually no longer critical; only the user name might be set. Proceed if a Reddit method is available.        |
| `deps_ok`   | Offer `pip install -r <skill_dir>/requirements.txt`, then re-run preflight                                   |
| `reddit_ok` | Rustwright not installed, or token/PRAW creds wrong. For Rustwright, tell the user a Chromium window will open. |
| `ai_ok`     | No `OPENAI_API_KEY` or `OPENROUTER_API_KEY` set. Ask the user to set one in the shell if they want AI analysis. |

Only proceed when `deps_ok` and `reddit_ok` are true. `ai_ok` is optional: if false, the agent supplies the analysis manually in Phase 4.

If the user wants AI-generated analysis, ask them to set `OPENAI_API_KEY` or `OPENROUTER_API_KEY` as shell environment variables before scraping. Do not instruct them to store these keys in `.env`.

## Phase 2 — Pick a profile

Ask the user to pick a profile with `AskUserQuestion` if they haven't specified one. Choices:

- **fast** — ~5 min, 3 subreddits × 5 posts
- **standard** — ~30 min, 5 subreddits × 25 posts
- **deep** — ~60 min, 10 subreddits × 100 posts

Signals:

- "fast" / "快速" / "试试" / "smoke test" / dev iteration → **fast**
- default / "完整" / "正式" / "深度调研" / no signal → **standard**
- "尽可能多" / "最深" / "thorough" / one-shot for a real decision → **deep**

See `resources/param-matrix.md` for exact numbers.

## Phase 3 — Scrape Reddit

Use the Bash tool with `run_in_background: true`, then poll output with `TaskOutput`. Each line is JSON; key events:

```json
{"event":"run_started","run_id":"...","profile":"standard","idea":"..."}
{"event":"stage","step":"login","progress":0.0,"message":"..."}
{"event":"stage","step":"login","progress":1.0,"message":"..."}
{"event":"stage","step":"scrape_data","progress":0.0,"message":"..."}
...
{"event":"done","success":true,"needs_analysis":true,"records_path":"...","run_id":"..."}
```

Command:

```bash
python "<skill_dir>/scripts/run_pipeline.py" "<idea>" --profile standard
```

To target specific subreddits (when the user already knows where to look):

```bash
python "<skill_dir>/scripts/run_pipeline.py" "<idea>" --profile standard --subreddits "IELTS,TOEFL,EnglishLearning"
```

When `--subreddits` is provided, the scraper searches each subreddit individually instead of all of Reddit, producing more targeted results. The `run_started` event will include a `subreddits` field.

On `done` with `success:true`, note `records_path` and `run_id` and go to Phase 4.

On `done` with `success:false`, read `error` and `failed_step`, then jump to Phase 4 / `resources/failure-recovery.md`.

When `REDDIT_LOGIN_METHOD=rustwright` (or `playwright`), the `reddit-auth` skill opens a Chromium window on `https://www.reddit.com`. The user clicks **Log in** and completes the flow. `reddit-auth` polls `/api/v1/me` and continues once a real user is detected.

## Phase 4 — Analyze

1. Read `records_path`.
2. **Detect the user's language** from their original request (e.g. Chinese → `"zh"`, English → `"en"`).
3. If the user configured `OPENAI_API_KEY` or `OPENROUTER_API_KEY`, call `analyzer.analyze(records, idea, profile, language="<lang>")` directly to generate the analysis JSON.
4. Otherwise, use Devin's own model to analyze the Reddit corpus and produce the structured analysis schema described in `SKILL.md`. Include `language`, `original_idea`, `analysis_method`, and `sources` on each item.
5. Save it to a JSON file (e.g. `<skill_dir>/analysis.json`).

## Phase 5 — Render the report

```bash
python "<skill_dir>/scripts/render_report.py" --analysis "<analysis.json>" --run-id "<run_id>" --language "<lang>"
```

This appends the final `done` event to the log, writes the HTML report, and **auto-opens it in the default browser**. Use `--no-open` to suppress.

## Phase 6 — Surface results

Extract:

```bash
python "<skill_dir>/scripts/extract_report.py" --run-id "<run_id>"
```

Tell the user concisely:

- Overall score (0-100): ≥75 strong, 50-74 promising, 30-49 weak, <30 likely no-go
- Analysis method used
- Top 3 pain points
- Top 3 opportunities
- Report absolute path (already opened in browser)
- Run id

Do not paste full HTML. Offer follow-ups: re-run with `deep`, compare runs, adjust idea wording.
