# Reddit Orchestrator — Design Spec

## Purpose

The orchestrator is a skill-based AI harness that dispatches other Reddit skills to match user needs. It sits above `reddit-auth`, `reddit-validator`, `reddit-explore`, `reddit-publish`, and `reddit-interact`, providing two capabilities:

1. **Planning** — Pattern-matches the user's request against known workflows, falling back to an LLM planner for novel requests. Outputs a structured plan JSON.
2. **Execution** — Optionally executes the plan by calling skill scripts as subprocesses, streaming JSONL events. Supports DAG dependency resolution, conditional steps, retry policies, and human-in-the-loop checkpoints.

The host agent can either execute the plan itself (calling skill scripts step by step) or let the orchestrator run it autonomously.

## Architecture

```text
User request
    ↓
planner.py (pattern match → known workflow | LLM fallback → novel plan)
    ↓
Plan JSON (steps with DAG, conditionals, checkpoints)
    ↓
runner.py executes steps via subprocess
    ↓
JSONL event stream (stage/done/checkpoint events)
    ↓
Host agent reads events, surfaces results to user
```

### Design decisions

- **Hybrid planning**: Pattern-match common workflows first (fast, deterministic). Fall back to LLM planner only when pattern matching fails.
- **Skill contract for host agent**: The orchestrator is a skill with a `SKILL.md` contract. The host agent reads it, understands the workflow, and decides whether to execute the plan itself or let the orchestrator run it.
- **Plan + optional execution**: `plan.py` outputs a plan JSON. `run.py` can execute it. The host agent chooses either mode.
- **Subprocess calls**: The runner calls skill scripts via `subprocess`, capturing JSON/JSONL stdout. This matches the documented CLI interface and keeps skills decoupled.
- **DAG + conditionals + checkpoints**: Steps have dependencies, conditions, retry policies, and checkpoint pauses for sensitive actions.

## Components

### `pipeline/planner.py`

- `match_workflow(request_text) -> (workflow_name, params) | None` — keyword/intent pattern matcher for the 4 known workflows. Returns the workflow name and extracted parameters (e.g. idea text, subreddit names, topic).
- `llm_plan(request_text, skill_catalog) -> plan_json` — LLM fallback for novel requests. Sends the user's request plus the skill catalog as context. The LLM returns a plan JSON matching the same structure.
- `plan(request_text) -> plan_json` — entry point. Tries pattern match first, falls back to LLM. If LLM is not available and pattern matching fails, returns an error.

### `pipeline/runner.py`

- `execute(plan, dry_run=False) -> generator[events]` — executes plan steps in DAG order via subprocess. Passes outputs between steps (step output's `records_path` or other fields become available as `{step_name.field}` references in later steps' commands). Handles:
  - **DAG resolution**: Topological sort of steps by `depends_on`. Steps with no dependencies run first.
  - **Conditionals**: Each step has an optional `condition` string (e.g. `"research_subreddits.success == true"`). If the condition evaluates to false, the step is skipped with a `step_skipped` event.
  - **Retry**: Each step has an optional `retry` policy (`max_attempts`, `delay_seconds`). On subprocess failure, retry up to `max_attempts` with the specified delay.
  - **Checkpoints**: Steps with `checkpoint: true` emit a `checkpoint` event before execution. The runner pauses and waits for the host agent to send `resume` (proceed) or `skip` (skip this step). Used before sensitive actions like publishing.
  - **Dry run**: When `dry_run=True`, the runner prints the commands it would execute without actually running them.

### `pipeline/workflows.py`

Defines the 4 known workflow templates as functions that return plan JSON:

- `validate_idea(idea, profile="standard") -> plan` — calls reddit-validator pipeline
- `brand_growth(brand, subreddits="", post_count=1, style=None) -> plan` — multi-step campaign
- `track_trends(topic, subreddits=None) -> plan` — discovery + summary
- `engage_community(brand, subreddits) -> plan` — discovery + interaction

Each template produces a plan JSON with parameterized steps. The planner fills in user-provided parameters.

### `pipeline/skill_catalog.py`

Static catalog of available skills, their scripts, and accepted parameters. Used by:

- The pattern matcher (to build plans with correct script paths and params)
- The LLM planner (as context so the LLM knows what skills are available)

```python
SKILLS = [
    {
        "name": "reddit-auth",
        "scripts": ["scripts/preflight.py", "scripts/login.py"],
        "purpose": "Authentication and session management",
    },
    {
        "name": "reddit-validator",
        "scripts": ["scripts/preflight.py", "scripts/run_pipeline.py", "scripts/render_report.py", "scripts/extract_report.py"],
        "purpose": "Validate a business idea via Reddit scraping and LLM analysis",
        "params": {"idea": "str", "profile": "fast|standard|deep", "subreddits": "comma-separated"},
    },
    {
        "name": "reddit-explore",
        "scripts": ["scripts/preflight.py", "scripts/search.py", "scripts/subreddit.py", "scripts/post.py", "scripts/user.py"],
        "purpose": "Search and browse Reddit content",
        "params": {"query": "str", "subreddit": "str", "limit": "int", "sort": "relevance|hot|new|top"},
    },
    {
        "name": "reddit-publish",
        "scripts": ["scripts/preflight.py", "scripts/research.py", "scripts/draft.py", "scripts/publish.py"],
        "purpose": "Research, draft, and publish Reddit posts",
        "params": {"topic": "str", "subreddit": "str", "style": "str", "dry_run": "bool"},
    },
    {
        "name": "reddit-interact",
        "scripts": ["scripts/preflight.py", "scripts/comment.py", "scripts/reply.py", "scripts/upvote.py", "scripts/downvote.py", "scripts/save.py"],
        "purpose": "Comment, reply, vote, and save on Reddit",
        "params": {"url_or_id": "str", "text": "str", "dry_run": "bool"},
    },
]
```

### Scripts

**`scripts/preflight.py`** — checks Python deps, reddit-auth availability, and that all skill directories exist. Emits JSON like other skills' preflight scripts.

**`scripts/plan.py`** — CLI entry point for planning.

```bash
python skills/reddit-orchestrator/scripts/plan.py "validate my idea: AI-powered language tutor"
# → outputs plan JSON to stdout
```

Options:

- `--request` (positional) — the user's request text
- `--workflow` — force a specific workflow (skip pattern matching)
- `--out` — write plan to file instead of stdout

**`scripts/run.py`** — CLI entry point for execution.

```bash
python skills/reddit-orchestrator/scripts/run.py --plan plan.json
# → streams JSONL events to stdout
```

Options:

- `--plan` — path to a plan JSON file
- `--request` — plan + run in one step (calls planner, then executes)
- `--dry-run` — print commands without executing
- `--resume` — resume from a checkpoint (reads plan + state from `.reddit-skills/orchestrator/`)

## Plan JSON Structure

```json
{
  "plan_id": "auto-generated-uuid",
  "workflow": "brand_growth",
  "request": "user's original request text",
  "created_at": "ISO timestamp",
  "steps": [
    {
      "name": "research_subreddits",
      "skill": "reddit-explore",
      "description": "Research target subreddits to understand tone and hot topics",
      "command": ["python", "skills/reddit-explore/scripts/subreddit.py", "{subreddit}"],
      "depends_on": [],
      "output_key": "subreddit_data",
      "condition": null,
      "retry": {"max_attempts": 2, "delay_seconds": 5},
      "checkpoint": false
    },
    {
      "name": "draft_post",
      "skill": "reddit-publish",
      "description": "Draft a post matching the subreddit's tone",
      "command": ["python", "skills/reddit-publish/scripts/draft.py", "{research_subreddits.records_path}"],
      "depends_on": ["research_subreddits"],
      "output_key": "draft",
      "condition": "research_subreddits.success == true",
      "retry": {"max_attempts": 1, "delay_seconds": 0},
      "checkpoint": true
    }
  ]
}
```

### Field reference

- **`name`** — unique step identifier, used by `depends_on` and `output_key` references
- **`skill`** — which reddit skill this step calls
- **`description`** — human-readable explanation of the step
- **`command`** — argv array. Supports two placeholder types: `{param_name}` filled from user params, and `{step_name.field}` filled from prior step outputs. Placeholder resolution order: `{step_name.field}` references first (dot in the key), then `{param_name}` (no dot). This avoids ambiguity since step names and param names occupy different namespaces.
- **`depends_on`** — list of step names that must complete before this step starts
- **`output_key`** — key under which this step's output is stored for reference by later steps
- **`condition`** — optional expression evaluated against prior step outputs. Supported syntax: `step_name.field == value`, `step_name.field != value`, `step_name.success == true|false`. Multiple conditions joined by `and`/`or`. If the condition evaluates to false (or any referenced step was skipped/failed), the step is skipped.
- **`retry`** — `{"max_attempts": int, "delay_seconds": int}`. Defaults to `{"max_attempts": 1, "delay_seconds": 0}` (no retry)
- **`checkpoint`** — if true, runner emits a `checkpoint` event and pauses before executing. Host agent must send `resume` or `skip`

### Output passing

When a step completes, its JSON output (parsed from the subprocess stdout's last line) is stored under `step_outputs[output_key]`. Later steps can reference fields from prior outputs using `{step_name.field}` syntax in their `command` arrays.

For example, if `research_subreddits` outputs `{"records_path": "/path/to/file.json"}`, a later step's command can include `"{research_subreddits.records_path}"` which gets replaced with `/path/to/file.json`.

## Pre-defined Workflows

### 1. Idea Validation (`validate_idea`)

**Trigger keywords**: "validate", "analyze idea", "business idea", "market demand", "pain points", "调研", "验证", "创业想法"

**Steps**:

1. `scrape` — call `reddit-validator/scripts/run_pipeline.py "{idea}" --profile {profile}` (long-running, streams JSONL)
2. `render` — call `reddit-validator/scripts/render_report.py --analysis {analysis_path} --run-id {run_id}`
3. `extract` — call `reddit-validator/scripts/extract_report.py --run-id {run_id}`

**Parameters**: `idea` (required), `profile` (default: "standard"), `subreddits` (optional)

### 2. Brand Growth Campaign (`brand_growth`)

**Trigger keywords**: "grow brand", "enlarge brand", "brand presence", "subreddit campaign", "post and engage", "品牌", "推广"

**Steps**:

1. `research_subreddits` — call `reddit-explore/scripts/subreddit.py "{subreddit}"` for each target subreddit to understand tone and hot topics
2. `research_content` — call `reddit-publish/scripts/research.py "{topic}" --subreddit {subreddit}`
3. `draft_post` — call `reddit-publish/scripts/draft.py {research_content.records_path}`
4. **Checkpoint** — ask user to approve the draft
5. `publish_post` — call `reddit-publish/scripts/publish.py {draft_post.records_path}` (only after approval)
6. `engage_comments` — call `reddit-interact/scripts/comment.py` and `reply.py` on comments on the published post

**Parameters**: `brand` (required), `subreddits` (required), `post_count` (default: 1), `style` (optional)

### 3. Trend Tracking (`track_trends`)

**Trigger keywords**: "trending", "trend tracking", "what's hot", "trends on reddit", "趋势", "热门"

**Steps**:

1. `search_trends` — call `reddit-explore/scripts/search.py "{topic}" --sort hot --t week`
2. `summarize` — the runner emits the search results; the host agent summarizes them (or an LLM step summarizes if configured)

**Parameters**: `topic` (required), `subreddits` (optional), `time_filter` (default: "week")

### 4. Community Engagement (`engage_community`)

**Trigger keywords**: "engage", "community engagement", "comment on reddit", "reply to posts", "互动", "参与"

**Steps**:

1. `find_discussions` — call `reddit-explore/scripts/search.py "{brand}" --sort relevance` to find relevant discussions
2. **Checkpoint** — show user the list of posts found, ask which to engage with
3. `engage` — for each selected post, call `reddit-interact/scripts/comment.py "{post_url}" --text "{comment_text}"`
4. `upvote_relevant` — call `reddit-interact/scripts/upvote.py "{post_url}"` on relevant posts

**Parameters**: `brand` (required), `subreddits` (optional), `engage_count` (default: 5)

## Event Stream

The runner emits JSONL events to stdout, following the same convention as other skills:

```json
{"event": "plan_started", "plan_id": "...", "workflow": "...", "step_count": 3}
{"event": "step_started", "step": "research_subreddits", "skill": "reddit-explore"}
{"event": "step_done", "step": "research_subreddits", "success": true, "output": {...}}
{"event": "checkpoint", "step": "draft_post", "message": "Review draft before publishing. Send 'resume' to continue or 'skip' to skip."}
{"event": "step_skipped", "step": "publish_post", "reason": "condition not met"}
{"event": "step_failed", "step": "engage_comments", "error": "...", "attempts": 2}
{"event": "plan_done", "plan_id": "...", "success": true, "steps_completed": 5, "steps_skipped": 1, "steps_failed": 0}
```

### Checkpoint protocol

When a step has `checkpoint: true`:

1. Runner emits `{"event": "checkpoint", "step": "...", "message": "..."}` and pauses.
2. Host agent surfaces the checkpoint to the user.
3. Host agent writes `{"action": "resume"}` or `{"action": "skip"}` to the runner's stdin.
4. Runner proceeds or skips the step.

For `run.py` used as a standalone CLI (not driven by host agent), checkpoints default to interactive prompts on stdin/tty.

## Error Handling

- **Subprocess failure**: Retry per step's `retry` policy. After max attempts, emit `step_failed` event. The plan continues with remaining steps unless the failed step is a dependency of others (those dependents are skipped).
- **Condition evaluation**: If a step's `condition` evaluates to false, emit `step_skipped` with the reason. Dependent steps are also skipped.
- **Checkpoint timeout**: If no response within a configurable timeout (default: 300s), emit `checkpoint_timeout` and skip the step.
- **Plan state persistence**: The runner saves plan state (completed steps, outputs) to `.reddit-skills/orchestrator/{plan_id}.json` after each step. This enables `--resume` after interruption.

## Prerequisites

- Python 3.10+
- All underlying skills installed and configured (reddit-auth, reddit-validator, reddit-explore, reddit-publish, reddit-interact)
- Reddit authentication via reddit-auth
- Optional: `OPENAI_API_KEY` or `OPENROUTER_API_KEY` for LLM-driven planning (fallback only)

## File Layout

```text
skills/reddit-orchestrator/
├── SKILL.md
├── requirements.txt
├── pipeline/
│   ├── __init__.py
│   ├── planner.py
│   ├── runner.py
│   ├── workflows.py
│   └── skill_catalog.py
├── scripts/
│   ├── __init__.py
│   ├── preflight.py
│   ├── plan.py
│   └── run.py
└── tests/
    ├── test_planner.py
    ├── test_runner.py
    └── test_workflows.py
```

## Testing

- **`test_planner.py`**: Test pattern matching for each of the 4 workflows (positive and negative cases). Test LLM fallback path (mocked). Test parameter extraction.
- **`test_runner.py`**: Test DAG resolution (topological sort). Test conditional evaluation. Test output passing between steps. Test retry logic. Test checkpoint protocol (mocked stdin). Test dry-run mode.
- **`test_workflows.py`**: Test that each workflow template produces a valid plan JSON with correct step structure.

## SKILL.md Contract

The `SKILL.md` will follow the same format as other skills:

- **When to use**: compound operations, multi-skill workflows, "analyze my idea", "grow my brand on Reddit", "track trends", "engage with community"
- **When NOT to use**: single-skill tasks (use the specific skill directly)
- **Prerequisites**: all underlying skills configured
- **Workflow**: plan → (optional) run → read events
- **Operating principles**: always run preflight first, use `--dry-run` for sensitive actions, respect checkpoints, never bypass Reddit rate limits

## Dependencies

`requirements.txt`:

```text
dotenv
openai
```

No additional dependencies beyond what the underlying skills already require. The orchestrator uses `subprocess` (stdlib) for calling skills and `json` (stdlib) for plan/event handling.
