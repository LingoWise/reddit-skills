---
name: reddit-orchestrator
description: Use when the user wants to run compound Reddit operations — validate an idea, grow a brand, track trends, or engage with communities across multiple subreddits.
---

# Reddit Orchestrator

Dispatch other Reddit skills to match user needs. Plans a workflow by pattern-matching the user's request against known workflows (with LLM fallback for novel requests), then optionally executes the plan by calling skill scripts as subprocesses.

## When to use

- "validate my idea: X" → dispatches reddit-validator for full analysis and report
- "grow my brand X on subreddits Y, Z" → dispatches reddit-explore, reddit-publish, reddit-interact in sequence
- "track trends for X on Reddit" → dispatches reddit-explore to find trending posts
- "engage with communities about X" → dispatches reddit-explore + reddit-interact to comment and vote
- Any compound operation that requires multiple Reddit skills working together

## When NOT to use

- Single-skill tasks (use the specific skill directly):
  - Validating a single idea → `reddit-validator`
  - Searching or browsing → `reddit-explore`
  - Publishing a post → `reddit-publish`
  - Commenting or voting → `reddit-interact`
  - Authentication → `reddit-auth`

## Prerequisites

- Python 3.10+.
- Dependencies: `uv pip install -r skills/reddit-orchestrator/requirements.txt`.
- All underlying skills installed and configured (reddit-auth, reddit-validator, reddit-explore, reddit-publish, reddit-interact).
- Reddit authentication via `reddit-auth`.
- Optional: `OPENAI_API_KEY` or `OPENROUTER_API_KEY` for LLM-driven planning (fallback only).

## Workflow

### Phase 1 — Preflight

```bash
python "skills/reddit-orchestrator/scripts/preflight.py"
```

Checks that all skill directories exist and reddit-auth is available.

### Phase 2 — Plan

```bash
python "skills/reddit-orchestrator/scripts/plan.py" "your request text"
```

Outputs a plan JSON to stdout. Use `--out` to write to a file instead. Use `--workflow` to force a specific workflow.

### Phase 3 — Execute (optional)

The host agent can either execute the plan itself (reading the plan steps and calling skill scripts directly) or let the orchestrator run it:

```bash
python "skills/reddit-orchestrator/scripts/run.py" --plan plan.json
```

Streams JSONL events to stdout. Use `--dry-run` to print commands without executing. Use `--request` to plan and run in one step.

### Phase 4 — Read events

The runner emits JSONL events: `plan_started`, `step_started`, `step_done`, `checkpoint`, `step_skipped`, `step_failed`, `plan_done`. The host agent reads these and surfaces results to the user.

For checkpoint events, the host agent must write `{"action": "resume"}` or `{"action": "skip"}` to the runner's stdin.

## Operating principles

- Always run preflight first.
- Use `--dry-run` before the first real execution in a session.
- Respect checkpoints — never auto-resume sensitive actions like publishing.
- Never bypass Reddit rate limits.
- The orchestrator does not replace individual skills — it composes them.
