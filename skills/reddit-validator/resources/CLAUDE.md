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
| `env_ok`    | List the missing keys from `missing[]`, tell user to create `.env` in cwd or at `<skill_dir>/.env`, **STOP** |
| `deps_ok`   | Offer `pip install -r <skill_dir>/requirements.txt`, then re-run preflight                                   |
| `reddit_ok` | Likely wrong app type — tell user to verify Reddit app is "script" type at <https://www.reddit.com/prefs/apps> |
| `llm_ok`    | Check `OPENAI_BASE_URL` ends with `/v1`; check API quota/billing                                             |

Only proceed when all are true.

## Phase 2 — Pick a profile

Default to **standard**. If the user hasn't specified, ask them to choose. Signals:

- "fast" / "快速" / "试试" / "smoke test" / dev iteration → **fast**
- default / "完整" / "正式" / "深度调研" / no signal → **standard**
- "尽可能多" / "最深" / "thorough" / one-shot for a real decision → **deep**

See `resources/param-matrix.md` for exact numbers.

## Phase 3 — Run the pipeline

The pipeline can take 3–30 minutes. Background it and poll a log file:

```bash
cd "<skill_dir>" && nohup python "scripts/run_pipeline.py" "<idea>" --profile standard > "logs/run_$(date +%s).jsonl" 2>&1 &
```

Then periodically `Read` the log file to find a `done` event. Parse each line as JSON. Key events:

```json
{"event":"run_started","run_id":"...","profile":"standard","idea":"..."}
{"event":"stage","step":"scrape_data","progress":0.0,"message":"..."}
...
{"event":"done","success":true,"report_path":"...","score":72,"run_id":"...","execution_time":187.4}
```

If the pipeline has not finished after several polls, tell the user you are still monitoring and ask whether to keep polling or come back.

On `done` with `success:true`, go to Phase 5.

On `done` with `success:false`, read `error` and `failed_step`, then jump to Phase 4 / `resources/failure-recovery.md`.

## Phase 4 — Recover from failure

Resume:

```bash
python "<skill_dir>/scripts/recover.py" --resume-last --idea "<idea>" --profile standard
```

Inspect:

```bash
python "<skill_dir>/scripts/recover.py" --list
python "<skill_dir>/scripts/recover.py" --list --idea "<idea>"
python "<skill_dir>/scripts/recover.py" --show <run_id>
```

## Phase 5 — Surface results

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
