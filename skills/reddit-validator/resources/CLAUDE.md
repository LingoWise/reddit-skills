# Claude Code Runtime Guide

This guide is for agents running in Claude Code. It contains the tool-calling conventions for the `reddit-validator` skill.

## Phase 1 — Preflight

Run with the `Bash` tool:

```bash
python "<skill_dir>/scripts/preflight.py"
```

Read the JSON output and react:

| Field       | On false                                                                                                     |
| ----------- | ------------------------------------------------------------------------------------------------------------ |
| `env_ok`    | Usually no longer critical; only the user name might be set. Proceed if a Reddit method is available.        |
| `deps_ok`   | Offer `pip install -r <skill_dir>/requirements.txt`, then re-run preflight                                   |
| `reddit_ok` | Rustwright not installed, or token/PRAW creds wrong. For Rustwright, tell the user a Chromium window will open. |

Only proceed when `deps_ok` and `reddit_ok` are true.

The skill does **not** require an external LLM provider. The agent (Claude Code) supplies the analysis in Phase 4.

## Phase 2 — Pick a profile

Default to **standard**. If the user hasn't specified, ask them to choose. Signals:

- "fast" / "快速" / "试试" / "smoke test" / dev iteration → **fast**
- default / "完整" / "正式" / "深度调研" / no signal → **standard**
- "尽可能多" / "最深" / "thorough" / one-shot for a real decision → **deep**

See `resources/param-matrix.md` for exact numbers.

## Phase 3 — Scrape Reddit

The scraper can take 3–30 minutes. Background it and poll a log file:

```bash
cd "<skill_dir>" && nohup python "scripts/run_pipeline.py" "<idea>" --profile standard > "logs/run_$(date +%s).jsonl" 2>&1 &
```

Then periodically `Read` the log file to find a `done` event. Parse each line as JSON. Key events:

```json
{"event":"run_started","run_id":"...","profile":"standard","idea":"..."}
{"event":"stage","step":"scrape_data","progress":0.0,"message":"..."}
...
{"event":"done","success":true,"needs_analysis":true,"records_path":"...","run_id":"..."}
```

If the scraper has not finished after several polls, tell the user you are still monitoring and ask whether to keep polling or come back.

On `done` with `success:true`, note `records_path` and `run_id` and go to Phase 4.

On `done` with `success:false`, read `error` and `failed_step`, then jump to Phase 4 / `resources/failure-recovery.md`.

When `REDDIT_LOGIN_METHOD=rustwright` (or `playwright`), the `reddit-auth` skill opens a Chromium window on `https://www.reddit.com`. The user clicks **Log in** and completes the flow. `reddit-auth` polls `/api/v1/me` and continues once a real user is detected.

## Phase 4 — Analyze with Claude Code's LLM

1. Read the `records_path`.
2. Use Claude Code's own model to analyze the Reddit corpus and produce the structured analysis JSON described in `SKILL.md`.
3. Save it to a JSON file (e.g. `<skill_dir>/analysis.json`).

## Phase 5 — Render the report

```bash
python "<skill_dir>/scripts/render_report.py" --analysis "<analysis.json>" --run-id "<run_id>"
```

This appends the final `done` event to the log and writes the HTML report.

## Phase 6 — Surface results

Extract:

```bash
python "<skill_dir>/scripts/extract_report.py" --run-id "<run_id>"
```

Tell the user concisely:

- Overall score (0-100): ≥75 strong, 50-74 promising, 30-49 weak, <30 likely no-go
- Top 3 pain points
- Top 3 opportunities
- Report absolute path
- Run id

Do not paste full HTML. Offer follow-ups: re-run with `deep`, compare runs, adjust idea wording.
