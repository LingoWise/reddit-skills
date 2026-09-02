# Reddit Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a skill-based AI harness that dispatches other Reddit skills to match user needs via hybrid pattern-matching + LLM planning, with optional autonomous execution via subprocess calls.

**Architecture:** The orchestrator sits above the 5 existing Reddit skills. A planner module pattern-matches user requests against 4 known workflows, falling back to an LLM planner for novel requests. A runner module optionally executes the resulting plan JSON by calling skill scripts as subprocesses, streaming JSONL events with DAG resolution, conditionals, retries, and checkpoints.

**Tech Stack:** Python 3.10+, subprocess (stdlib), json (stdlib), openai (for LLM fallback), pytest

## Global Constraints

- Python 3.10+ required.
- All skill scripts are called via `subprocess` — no direct Python imports of other skills' pipelines (except `reddit-auth` for preflight, following the existing pattern).
- Shared libraries loaded via `importlib.util.spec_from_file_location` from `src/common/` — same pattern as all other skills.
- Runtime outputs go to `.reddit-skills/` directory (via `src/common/paths.py`).
- `SKILL.md` follows the same frontmatter + section format as other skills.
- `.markdownlint.json` disables MD013 and MD060 (same as other skills).
- Tests run from the skill directory: `cd skills/reddit-orchestrator && python -m pytest tests/ -v`
- `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` at the top of every script for pipeline imports.

---

## File Structure

```text
skills/reddit-orchestrator/
├── SKILL.md                      # Skill contract (Task 1)
├── requirements.txt              # Dependencies (Task 1)
├── .markdownlint.json            # Lint config (Task 1)
├── pipeline/
│   ├── __init__.py               # Empty init (Task 1)
│   ├── paths.py                  # Path helpers, loads src/common/paths.py (Task 1)
│   ├── skill_catalog.py          # Static catalog of available skills (Task 2)
│   ├── workflows.py              # 4 workflow template functions (Task 3)
│   ├── planner.py                # Pattern matcher + LLM fallback (Task 4)
│   ├── runner.py                 # DAG executor with conditionals/retries/checkpoints (Task 5)
│   └── state.py                  # Plan state persistence (Task 5)
├── scripts/
│   ├── __init__.py               # Empty init (Task 1)
│   ├── preflight.py              # Deps + auth + skill dir checks (Task 6)
│   ├── plan.py                   # CLI: plan a request -> output plan JSON (Task 7)
│   └── run.py                    # CLI: execute a plan -> stream JSONL events (Task 8)
└── tests/
    ├── __init__.py               # Empty init (Task 1)
    ├── test_skill_catalog.py     # Test catalog structure (Task 2)
    ├── test_workflows.py         # Test workflow templates produce valid plans (Task 3)
    ├── test_planner.py           # Test pattern matching + LLM fallback (Task 4)
    ├── test_runner.py            # Test DAG, conditionals, retries, checkpoints, dry-run (Task 5)
    ├── test_preflight.py         # Test preflight checks (Task 6)
    ├── test_plan_script.py       # Test plan.py CLI (Task 7)
    └── test_run_script.py        # Test run.py CLI (Task 8)
```

---

### Task 1: Scaffolding — SKILL.md, requirements.txt, paths, empty inits

**Files:**

- Create: `skills/reddit-orchestrator/SKILL.md`
- Create: `skills/reddit-orchestrator/requirements.txt`
- Create: `skills/reddit-orchestrator/.markdownlint.json`
- Create: `skills/reddit-orchestrator/pipeline/__init__.py`
- Create: `skills/reddit-orchestrator/pipeline/paths.py`
- Create: `skills/reddit-orchestrator/scripts/__init__.py`
- Create: `skills/reddit-orchestrator/tests/__init__.py`

**Interfaces:**

- Produces: `pipeline/paths.py` with `skill_dir()`, `orchestrator_dir()`, `records_dir()`, `logs_dir()`, `checkpoints_dir()` — used by all later tasks.

- [ ] **Step 1: Create directory structure and empty init files**

Create these empty files:

- `skills/reddit-orchestrator/pipeline/__init__.py`
- `skills/reddit-orchestrator/scripts/__init__.py`
- `skills/reddit-orchestrator/tests/__init__.py`

- [ ] **Step 2: Create `requirements.txt`**

```text
python-dotenv
openai
```

- [ ] **Step 3: Create `.markdownlint.json`**

```json
{
  "MD013": false,
  "MD060": false
}
```

- [ ] **Step 4: Create `pipeline/paths.py`**

```python
import importlib.util
from pathlib import Path


def _load_common_paths():
    """Load the shared paths module from src/common/."""
    paths_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "paths.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_paths", paths_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_common = _load_common_paths()


def skill_dir() -> Path:
    """Return the root directory of the reddit-orchestrator skill."""
    return Path(__file__).resolve().parent.parent


def orchestrator_dir() -> Path:
    """Return the orchestrator output directory under .reddit-skills/."""
    path = _common.output_root() / "orchestrator"
    path.mkdir(parents=True, exist_ok=True)
    return path


def records_dir() -> Path:
    return _common.records_dir()


def logs_dir() -> Path:
    return _common.logs_dir()


def checkpoints_dir() -> Path:
    return _common.checkpoints_dir()
```

- [ ] **Step 5: Create `SKILL.md`**

```markdown
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

```

- [ ] **Step 6: Verify structure**

Run:
```bash
find skills/reddit-orchestrator -type f | sort
```

Expected output:

```text
skills/reddit-orchestrator/.markdownlint.json
skills/reddit-orchestrator/SKILL.md
skills/reddit-orchestrator/pipeline/__init__.py
skills/reddit-orchestrator/pipeline/paths.py
skills/reddit-orchestrator/requirements.txt
skills/reddit-orchestrator/scripts/__init__.py
skills/reddit-orchestrator/tests/__init__.py
```

- [ ] **Step 7: Verify paths module loads**

Run:

```bash
cd skills/reddit-orchestrator && python -c "import sys; sys.path.insert(0, '.'); from pipeline.paths import skill_dir; print(skill_dir().name)"
```

Expected: `reddit-orchestrator`

- [ ] **Step 8: Commit**

```bash
git add skills/reddit-orchestrator/
git commit -m "feat: scaffold reddit-orchestrator skill structure"
```

---

### Task 2: Skill Catalog

**Files:**

- Create: `skills/reddit-orchestrator/pipeline/skill_catalog.py`
- Create: `skills/reddit-orchestrator/tests/test_skill_catalog.py`

**Interfaces:**

- Produces: `SKILLS` list, `get_skill(name) -> dict | None`, `catalog_summary() -> str` — used by planner (Task 4) and preflight (Task 6).

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-orchestrator/tests/test_skill_catalog.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.skill_catalog import SKILLS, get_skill, catalog_summary


def test_skills_has_five_entries():
    assert len(SKILLS) == 5


def test_skills_contains_expected_names():
    names = [s["name"] for s in SKILLS]
    assert "reddit-auth" in names
    assert "reddit-validator" in names
    assert "reddit-explore" in names
    assert "reddit-publish" in names
    assert "reddit-interact" in names


def test_each_skill_has_required_fields():
    for skill in SKILLS:
        assert "name" in skill
        assert "scripts" in skill
        assert "purpose" in skill
        assert isinstance(skill["scripts"], list)
        assert len(skill["scripts"]) > 0


def test_get_skill_returns_match():
    skill = get_skill("reddit-validator")
    assert skill is not None
    assert skill["name"] == "reddit-validator"


def test_get_skill_returns_none_for_unknown():
    assert get_skill("nonexistent") is None


def test_catalog_summary_is_string():
    summary = catalog_summary()
    assert isinstance(summary, str)
    assert "reddit-validator" in summary
    assert "reddit-explore" in summary
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_skill_catalog.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.skill_catalog'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/reddit-orchestrator/pipeline/skill_catalog.py`:

```python
"""Static catalog of available Reddit skills.

Used by the pattern matcher to build plans with correct script paths,
and by the LLM planner as context for generating plans.
"""

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


def get_skill(name):
    """Return the skill dict for the given name, or None if not found."""
    for skill in SKILLS:
        if skill["name"] == name:
            return skill
    return None


def catalog_summary():
    """Return a human-readable summary of available skills for LLM context."""
    lines = []
    for skill in SKILLS:
        line = f"- {skill['name']}: {skill['purpose']}"
        if "params" in skill:
            param_str = ", ".join(f"{k}={v}" for k, v in skill["params"].items())
            line += f" (params: {param_str})"
        lines.append(line)
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_skill_catalog.py -v
```

Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-orchestrator/pipeline/skill_catalog.py skills/reddit-orchestrator/tests/test_skill_catalog.py
git commit -m "feat: add skill catalog for orchestrator"
```

---

### Task 3: Workflow Templates

**Files:**

- Create: `skills/reddit-orchestrator/pipeline/workflows.py`
- Create: `skills/reddit-orchestrator/tests/test_workflows.py`

**Interfaces:**

- Consumes: `pipeline/paths.py` (`skill_dir()` for building script paths)
- Produces: `validate_idea(idea, profile, subreddits) -> plan`, `brand_growth(brand, subreddits, post_count, style) -> plan`, `track_trends(topic, subreddits, time_filter) -> plan`, `engage_community(brand, subreddits, engage_count) -> plan`, `build_plan(workflow, request, params) -> plan` — used by planner (Task 4).

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-orchestrator/tests/test_workflows.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.workflows import (
    validate_idea,
    brand_growth,
    track_trends,
    engage_community,
    build_plan,
)


def test_validate_idea_returns_valid_plan():
    plan = validate_idea("AI language tutor")
    assert plan["workflow"] == "validate_idea"
    assert plan["request"] == "AI language tutor"
    assert len(plan["steps"]) == 3
    assert plan["steps"][0]["name"] == "scrape"
    assert plan["steps"][0]["skill"] == "reddit-validator"
    assert plan["steps"][0]["depends_on"] == []
    assert plan["steps"][1]["depends_on"] == ["scrape"]
    assert plan["steps"][2]["depends_on"] == ["render"]


def test_validate_idea_with_profile():
    plan = validate_idea("test idea", profile="fast")
    scrape_cmd = plan["steps"][0]["command"]
    assert "--profile" in scrape_cmd
    assert "fast" in scrape_cmd


def test_validate_idea_with_subreddits():
    plan = validate_idea("test idea", subreddits="IELTS,TOEFL")
    scrape_cmd = plan["steps"][0]["command"]
    assert "--subreddits" in scrape_cmd
    assert "IELTS,TOEFL" in scrape_cmd


def test_brand_growth_returns_valid_plan():
    plan = brand_growth("MyBrand", "python,learnpython")
    assert plan["workflow"] == "brand_growth"
    assert len(plan["steps"]) >= 5
    step_names = [s["name"] for s in plan["steps"]]
    assert "research_subreddits" in step_names
    assert "research_content" in step_names
    assert "draft_post" in step_names
    assert "publish_post" in step_names
    assert "engage_comments" in step_names


def test_brand_growth_has_checkpoint_before_publish():
    plan = brand_growth("MyBrand", "python")
    draft_step = next(s for s in plan["steps"] if s["name"] == "draft_post")
    publish_step = next(s for s in plan["steps"] if s["name"] == "publish_post")
    assert draft_step["checkpoint"] is True
    assert publish_step["depends_on"] == ["draft_post"]


def test_track_trends_returns_valid_plan():
    plan = track_trends("AI tools")
    assert plan["workflow"] == "track_trends"
    assert len(plan["steps"]) == 2
    assert plan["steps"][0]["name"] == "search_trends"
    assert plan["steps"][0]["skill"] == "reddit-explore"
    assert plan["steps"][1]["name"] == "summarize"
    assert plan["steps"][1]["depends_on"] == ["search_trends"]


def test_engage_community_returns_valid_plan():
    plan = engage_community("MyBrand")
    assert plan["workflow"] == "engage_community"
    assert len(plan["steps"]) >= 3
    step_names = [s["name"] for s in plan["steps"]]
    assert "find_discussions" in step_names
    assert "engage" in step_names
    assert "upvote_relevant" in step_names


def test_engage_community_has_checkpoint():
    plan = engage_community("MyBrand")
    find_step = next(s for s in plan["steps"] if s["name"] == "find_discussions")
    engage_step = next(s for s in plan["steps"] if s["name"] == "engage")
    assert find_step["checkpoint"] is True
    assert engage_step["depends_on"] == ["find_discussions"]


def test_build_plan_validates_workflow_name():
    with pytest.raises(ValueError, match="Unknown workflow"):
        build_plan("nonexistent", "request text", {})


def test_build_plan_passes_params():
    plan = build_plan("validate_idea", "test", {"idea": "my idea", "profile": "deep"})
    assert plan["workflow"] == "validate_idea"
    assert plan["request"] == "test"
    scrape_cmd = plan["steps"][0]["command"]
    assert "deep" in scrape_cmd


def test_every_step_has_required_fields():
    for plan_fn, args in [
        (validate_idea, ("idea",)),
        (brand_growth, ("brand", "subs")),
        (track_trends, ("topic",)),
        (engage_community, ("brand",)),
    ]:
        plan = plan_fn(*args)
        for step in plan["steps"]:
            assert "name" in step
            assert "skill" in step
            assert "description" in step
            assert "command" in step
            assert "depends_on" in step
            assert "output_key" in step
            assert "condition" in step
            assert "retry" in step
            assert "checkpoint" in step
            assert isinstance(step["command"], list)
            assert isinstance(step["depends_on"], list)
            assert isinstance(step["retry"], dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_workflows.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.workflows'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/reddit-orchestrator/pipeline/workflows.py`:

```python
"""Pre-defined workflow templates for the orchestrator.

Each function returns a plan JSON dict with parameterized steps.
The planner fills in user-provided parameters.
"""

import time
import uuid
from datetime import datetime

from .paths import skill_dir


def _skills_root():
    """Return the skills/ directory (parent of this skill)."""
    return skill_dir().parent


def _script_path(skill_name, script_name):
    """Return the full path to a skill script."""
    return str(_skills_root() / skill_name / script_name)


def _new_plan(workflow, request):
    """Create a plan skeleton with id and timestamp."""
    return {
        "plan_id": f"{int(time.time())}-{uuid.uuid4().hex[:8]}",
        "workflow": workflow,
        "request": request,
        "created_at": datetime.utcnow().isoformat(),
        "steps": [],
    }


def _step(name, skill, description, command, depends_on=None, output_key=None,
          condition=None, retry=None, checkpoint=False):
    """Create a step dict with defaults."""
    return {
        "name": name,
        "skill": skill,
        "description": description,
        "command": command,
        "depends_on": depends_on or [],
        "output_key": output_key or name,
        "condition": condition,
        "retry": retry or {"max_attempts": 1, "delay_seconds": 0},
        "checkpoint": checkpoint,
    }


def validate_idea(idea, profile="standard", subreddits=None):
    """Workflow: validate a business idea via reddit-validator."""
    plan = _new_plan("validate_idea", idea)
    scrape_cmd = ["python", _script_path("reddit-validator", "scripts/run_pipeline.py"), idea, "--profile", profile]
    if subreddits:
        scrape_cmd.extend(["--subreddits", subreddits])
    plan["steps"] = [
        _step(
            "scrape",
            "reddit-validator",
            "Scrape Reddit for idea validation",
            scrape_cmd,
            output_key="scrape",
            retry={"max_attempts": 2, "delay_seconds": 5},
        ),
        _step(
            "render",
            "reddit-validator",
            "Render the HTML report",
            ["python", _script_path("reddit-validator", "scripts/render_report.py"),
             "--analysis", "{scrape.analysis}", "--run-id", "{scrape.run_id}"],
            depends_on=["scrape"],
            output_key="render",
            condition="scrape.success == true",
        ),
        _step(
            "extract",
            "reddit-validator",
            "Extract report summary",
            ["python", _script_path("reddit-validator", "scripts/extract_report.py"),
             "--run-id", "{scrape.run_id}"],
            depends_on=["render"],
            output_key="extract",
            condition="render.success == true",
        ),
    ]
    return plan


def brand_growth(brand, subreddits="", post_count=1, style=None):
    """Workflow: grow brand presence across subreddits."""
    plan = _new_plan("brand_growth", brand)
    first_sub = subreddits.split(",")[0].strip() if subreddits else ""
    plan["steps"] = [
        _step(
            "research_subreddits",
            "reddit-explore",
            "Research target subreddits to understand tone and hot topics",
            ["python", _script_path("reddit-explore", "scripts/subreddit.py"), first_sub],
            output_key="research_subreddits",
            retry={"max_attempts": 2, "delay_seconds": 5},
        ),
        _step(
            "research_content",
            "reddit-publish",
            "Research top content in the subreddit",
            ["python", _script_path("reddit-publish", "scripts/research.py"), brand,
             "--subreddit", first_sub],
            depends_on=["research_subreddits"],
            output_key="research_content",
            condition="research_subreddits.success == true",
        ),
        _step(
            "draft_post",
            "reddit-publish",
            "Draft a post matching the subreddit's tone",
            ["python", _script_path("reddit-publish", "scripts/draft.py"),
             "{research_content.records_path}"] + (["--style", style] if style else []),
            depends_on=["research_content"],
            output_key="draft_post",
            condition="research_content.success == true",
            checkpoint=True,
        ),
        _step(
            "publish_post",
            "reddit-publish",
            "Publish the approved post",
            ["python", _script_path("reddit-publish", "scripts/publish.py"),
             "{draft_post.draft_path}"],
            depends_on=["draft_post"],
            output_key="publish_post",
            condition="draft_post.success == true",
        ),
        _step(
            "engage_comments",
            "reddit-interact",
            "Monitor and reply to comments on the published post",
            ["python", _script_path("reddit-interact", "scripts/comment.py"),
             "{publish_post.post_url}", "--text-file", "engage_response.txt"],
            depends_on=["publish_post"],
            output_key="engage",
            condition="publish_post.success == true",
            retry={"max_attempts": 2, "delay_seconds": 10},
        ),
    ]
    return plan


def track_trends(topic, subreddits=None, time_filter="week"):
    """Workflow: track trending content for a topic."""
    plan = _new_plan("track_trends", topic)
    search_cmd = ["python", _script_path("reddit-explore", "scripts/search.py"),
                  topic, "--sort", "hot", "--t", time_filter]
    if subreddits:
        search_cmd.extend(["--subreddits", subreddits])
    plan["steps"] = [
        _step(
            "search_trends",
            "reddit-explore",
            "Search for trending posts about the topic",
            search_cmd,
            output_key="search_trends",
            retry={"max_attempts": 2, "delay_seconds": 5},
        ),
        _step(
            "summarize",
            "reddit-orchestrator",
            "Summarize trending posts (host agent or LLM step)",
            ["python", "-c", "print('summarize step: host agent reads trends output')"],
            depends_on=["search_trends"],
            output_key="summary",
            condition="search_trends.success == true",
        ),
    ]
    return plan


def engage_community(brand, subreddits=None, engage_count=5):
    """Workflow: engage with community discussions about a brand."""
    plan = _new_plan("engage_community", brand)
    search_cmd = ["python", _script_path("reddit-explore", "scripts/search.py"),
                  brand, "--sort", "relevance", "--limit", str(engage_count)]
    if subreddits:
        search_cmd.extend(["--subreddits", subreddits])
    plan["steps"] = [
        _step(
            "find_discussions",
            "reddit-explore",
            "Find relevant discussions about the brand",
            search_cmd,
            output_key="find_discussions",
            checkpoint=True,
            retry={"max_attempts": 2, "delay_seconds": 5},
        ),
        _step(
            "engage",
            "reddit-interact",
            "Comment on selected posts",
            ["python", _script_path("reddit-interact", "scripts/comment.py"),
             "{find_discussions.posts.0.url}", "--text", "Thanks for sharing!"],
            depends_on=["find_discussions"],
            output_key="engage",
            condition="find_discussions.success == true",
        ),
        _step(
            "upvote_relevant",
            "reddit-interact",
            "Upvote relevant posts",
            ["python", _script_path("reddit-interact", "scripts/upvote.py"),
             "{find_discussions.posts.0.url}"],
            depends_on=["engage"],
            output_key="upvote",
            condition="engage.success == true",
        ),
    ]
    return plan


WORKFLOW_FNS = {
    "validate_idea": validate_idea,
    "brand_growth": brand_growth,
    "track_trends": track_trends,
    "engage_community": engage_community,
}


def build_plan(workflow, request, params):
    """Build a plan for a known workflow by name.

    Raises ValueError if the workflow name is not recognized.
    """
    if workflow not in WORKFLOW_FNS:
        raise ValueError(f"Unknown workflow: {workflow}. Choose from {list(WORKFLOW_FNS)}")
    return WORKFLOW_FNS[workflow](request, **params)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_workflows.py -v
```

Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-orchestrator/pipeline/workflows.py skills/reddit-orchestrator/tests/test_workflows.py
git commit -m "feat: add workflow templates for orchestrator"
```

---

### Task 4: Planner — Pattern Matching + LLM Fallback

**Files:**

- Create: `skills/reddit-orchestrator/pipeline/planner.py`
- Create: `skills/reddit-orchestrator/tests/test_planner.py`

**Interfaces:**

- Consumes: `pipeline/workflows.py` (`build_plan`), `pipeline/skill_catalog.py` (`catalog_summary`), `src/common/llm.py` (`available`, `chat_json`)
- Produces: `match_workflow(request_text) -> (workflow_name, params) | None`, `llm_plan(request_text) -> plan`, `plan(request_text, workflow=None) -> plan` — used by `scripts/plan.py` (Task 7) and `scripts/run.py` (Task 8).

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-orchestrator/tests/test_planner.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.planner import match_workflow, plan


class TestMatchWorkflow:
    def test_validate_idea_english(self):
        result = match_workflow("validate my idea: AI-powered language tutor")
        assert result is not None
        assert result[0] == "validate_idea"
        assert "AI-powered language tutor" in result[1]["idea"]

    def test_validate_idea_chinese(self):
        result = match_workflow("验证创业想法：AI英语家教")
        assert result is not None
        assert result[0] == "validate_idea"

    def test_brand_growth_english(self):
        result = match_workflow("grow my brand Acme on subreddits python, learnpython")
        assert result is not None
        assert result[0] == "brand_growth"
        assert "Acme" in result[1]["brand"]

    def test_brand_growth_chinese(self):
        result = match_workflow("推广品牌 Acme 在 reddit 上")
        assert result is not None
        assert result[0] == "brand_growth"

    def test_track_trends_english(self):
        result = match_workflow("track trends for AI tools on Reddit")
        assert result is not None
        assert result[0] == "track_trends"
        assert "AI tools" in result[1]["topic"]

    def test_track_trends_chinese(self):
        result = match_workflow("看看 Reddit 上 AI 工具的热门趋势")
        assert result is not None
        assert result[0] == "track_trends"

    def test_engage_community_english(self):
        result = match_workflow("engage with communities about my product Acme")
        assert result is not None
        assert result[0] == "engage_community"
        assert "Acme" in result[1]["brand"]

    def test_engage_community_chinese(self):
        result = match_workflow("在 Reddit 社区互动讨论 Acme")
        assert result is not None
        assert result[0] == "engage_community"

    def test_no_match_returns_none(self):
        assert match_workflow("what is the weather today?") is None

    def test_no_match_random_text(self):
        assert match_workflow("hello world") is None


class TestPlan:
    def test_plan_with_known_workflow(self):
        p = plan("validate my idea: test idea")
        assert p["workflow"] == "validate_idea"
        assert "plan_id" in p
        assert "steps" in p
        assert len(p["steps"]) > 0

    def test_plan_with_forced_workflow(self):
        p = plan("some text", workflow="track_trends")
        assert p["workflow"] == "track_trends"

    def test_plan_unknown_workflow_raises(self):
        with pytest.raises(ValueError, match="Unknown workflow"):
            plan("some text", workflow="nonexistent")

    def test_plan_no_match_no_llm_returns_error(self, monkeypatch):
        monkeypatch.setattr("pipeline.planner._llm_available", lambda: (False, "no key"))
        result = plan("what is the weather today?")
        assert "error" in result
        assert "could not match" in result["error"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_planner.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.planner'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/reddit-orchestrator/pipeline/planner.py`:

```python
"""Hybrid planner: pattern-match known workflows, fall back to LLM for novel requests."""

import re

from .workflows import build_plan
from .skill_catalog import catalog_summary


WORKFLOW_PATTERNS = [
    {
        "name": "validate_idea",
        "patterns": [
            r"validate.*idea", r"analyze.*idea", r"business\s+idea",
            r"market\s+demand", r"pain\s+points",
            r"验证.*想法", r"验证.*创业", r"调研.*reddit",
            r"创业想法", r"市场.*需求",
        ],
        "extract_idea": r"(?:idea[:\s]+|想法[：:]\s*|验证.*?[:：]\s*)(.+)",
    },
    {
        "name": "brand_growth",
        "patterns": [
            r"grow\s+(?:my\s+)?brand", r"enlarge\s+brand",
            r"brand\s+presence", r"subreddit\s+campaign",
            r"post\s+and\s+engage",
            r"推广.*品牌", r"品牌.*推广",
        ],
        "extract_brand": r"(?:brand\s+|品牌\s*)(\S+)",
        "extract_subreddits": r"(?:subreddits?\s+|在\s*)(\S+)",
    },
    {
        "name": "track_trends",
        "patterns": [
            r"trend\s+track", r"track\s+trend", r"what'?s\s+hot",
            r"trends?\s+on\s+reddit",
            r"趋势", r"热门",
        ],
        "extract_topic": r"(?:trends?\s+for\s+|趋势.*?[:：]\s*|热门.*?[:：]\s*)(.+)",
    },
    {
        "name": "engage_community",
        "patterns": [
            r"engage.*communit", r"community\s+engagement",
            r"comment\s+on\s+reddit", r"reply\s+to\s+posts",
            r"互动", r"参与.*社区",
        ],
        "extract_brand": r"(?:about\s+(?:my\s+)?(?:product\s+)?|讨论\s*)(\S+)",
    },
]


def _llm_available():
    """Check if LLM is available for fallback planning."""
    import importlib.util
    from pathlib import Path

    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    llm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llm)
    return llm.available()


def match_workflow(request_text):
    """Try to match the request against known workflows.

    Returns (workflow_name, params_dict) if matched, None otherwise.
    """
    text_lower = request_text.lower()

    for wf in WORKFLOW_PATTERNS:
        for pattern in wf["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                params = _extract_params(wf, request_text)
                return wf["name"], params
    return None


def _extract_params(workflow_def, request_text):
    """Extract parameters from the request text based on workflow type."""
    name = workflow_def["name"]
    params = {}

    if name == "validate_idea":
        m = re.search(workflow_def.get("extract_idea", r"(.+)"), request_text, re.IGNORECASE)
        params["idea"] = m.group(1).strip() if m else request_text
        if "fast" in request_text.lower():
            params["profile"] = "fast"
        elif "deep" in request_text.lower():
            params["profile"] = "deep"
        else:
            params["profile"] = "standard"
        sub_m = re.search(r"subreddits?\s*[:，,]?\s*(\S+)", request_text, re.IGNORECASE)
        if sub_m:
            params["subreddits"] = sub_m.group(1)

    elif name == "brand_growth":
        brand_m = re.search(workflow_def.get("extract_brand", r"brand\s+(\S+)"), request_text, re.IGNORECASE)
        params["brand"] = brand_m.group(1).strip() if brand_m else request_text
        sub_m = re.search(r"subreddits?\s+(\S+)", request_text, re.IGNORECASE)
        params["subreddits"] = sub_m.group(1).strip() if sub_m else ""

    elif name == "track_trends":
        topic_m = re.search(workflow_def.get("extract_topic", r"(.+)"), request_text, re.IGNORECASE)
        params["topic"] = topic_m.group(1).strip() if topic_m else request_text
        sub_m = re.search(r"subreddits?\s+(\S+)", request_text, re.IGNORECASE)
        if sub_m:
            params["subreddits"] = sub_m.group(1)

    elif name == "engage_community":
        brand_m = re.search(workflow_def.get("extract_brand", r"about\s+(\S+)"), request_text, re.IGNORECASE)
        params["brand"] = brand_m.group(1).strip() if brand_m else request_text
        sub_m = re.search(r"subreddits?\s+(\S+)", request_text, re.IGNORECASE)
        if sub_m:
            params["subreddits"] = sub_m.group(1)

    return params


def llm_plan(request_text):
    """Generate a plan using the LLM fallback."""
    import importlib.util
    import json
    import time
    import uuid
    from pathlib import Path

    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    llm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llm)

    summary = catalog_summary()
    system_msg = (
        "You are a Reddit operations planner. Given a user's request and the available skills, "
        "generate a plan JSON with steps that call the skill scripts. "
        "Each step has: name, skill, description, command (argv array), depends_on (list), "
        "output_key, condition (null or expression), retry ({max_attempts, delay_seconds}), "
        "checkpoint (bool). "
        "Available skills:\n" + summary
    )
    user_msg = f"User request: {request_text}\n\nGenerate a plan JSON."
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]
    result = llm.chat_json(messages, temperature=0.2)
    if "plan_id" not in result:
        result["plan_id"] = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    if "workflow" not in result:
        result["workflow"] = "custom"
    if "request" not in result:
        result["request"] = request_text
    if "steps" not in result:
        result["steps"] = []
    return result


def plan(request_text, workflow=None):
    """Plan a workflow for the user's request.

    If workflow is specified, force that workflow (skip pattern matching).
    Otherwise, try pattern matching first, then fall back to LLM.
    If both fail, return an error dict.
    """
    if workflow is not None:
        matched = match_workflow(request_text)
        if matched and matched[0] == workflow:
            params = matched[1]
        else:
            params = {}
        return build_plan(workflow, request_text, params)

    matched = match_workflow(request_text)
    if matched is not None:
        workflow_name, params = matched
        return build_plan(workflow_name, request_text, params)

    ok, msg = _llm_available()
    if ok:
        try:
            return llm_plan(request_text)
        except Exception as exc:
            return {"error": f"LLM planning failed: {exc}", "request": request_text}

    return {
        "error": "Could not match a known workflow and LLM is not available. "
                 "Set OPENAI_API_KEY or OPENROUTER_API_KEY for LLM-driven planning, "
                 "or specify a workflow with --workflow.",
        "request": request_text,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_planner.py -v
```

Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-orchestrator/pipeline/planner.py skills/reddit-orchestrator/tests/test_planner.py
git commit -m "feat: add hybrid planner with pattern matching and LLM fallback"
```

---

### Task 5: Runner — DAG Execution with Conditionals, Retries, Checkpoints

**Files:**

- Create: `skills/reddit-orchestrator/pipeline/state.py`
- Create: `skills/reddit-orchestrator/pipeline/runner.py`
- Create: `skills/reddit-orchestrator/tests/test_runner.py`

**Interfaces:**

- Consumes: `pipeline/paths.py` (`orchestrator_dir()` for state persistence)
- Produces: `execute(plan, dry_run=False, stdin_input=None) -> generator[events]`, `resolve_placeholders(command, step_outputs, params) -> list`, `evaluate_condition(condition, step_outputs) -> bool`, `topological_sort(steps) -> list` — used by `scripts/run.py` (Task 8).

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-orchestrator/tests/test_runner.py`:

```python
import json
import sys
import io
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.runner import (
    resolve_placeholders,
    evaluate_condition,
    topological_sort,
    execute,
)


class TestTopologicalSort:
    def test_simple_linear(self):
        steps = [
            {"name": "a", "depends_on": []},
            {"name": "b", "depends_on": ["a"]},
            {"name": "c", "depends_on": ["b"]},
        ]
        ordered = topological_sort(steps)
        names = [s["name"] for s in ordered]
        assert names == ["a", "b", "c"]

    def test_parallel_branches(self):
        steps = [
            {"name": "a", "depends_on": []},
            {"name": "b", "depends_on": ["a"]},
            {"name": "c", "depends_on": ["a"]},
            {"name": "d", "depends_on": ["b", "c"]},
        ]
        ordered = topological_sort(steps)
        names = [s["name"] for s in ordered]
        assert names.index("a") < names.index("b")
        assert names.index("a") < names.index("c")
        assert names.index("b") < names.index("d")
        assert names.index("c") < names.index("d")

    def test_no_dependencies(self):
        steps = [
            {"name": "x", "depends_on": []},
            {"name": "y", "depends_on": []},
        ]
        ordered = topological_sort(steps)
        assert len(ordered) == 2

    def test_cycle_raises(self):
        steps = [
            {"name": "a", "depends_on": ["b"]},
            {"name": "b", "depends_on": ["a"]},
        ]
        with pytest.raises(ValueError, match="cycle"):
            topological_sort(steps)


class TestResolvePlaceholders:
    def test_resolves_step_output_reference(self):
        command = ["python", "script.py", "{scrape.records_path}"]
        outputs = {"scrape": {"records_path": "/tmp/records.json", "success": True}}
        resolved = resolve_placeholders(command, outputs, {})
        assert resolved == ["python", "script.py", "/tmp/records.json"]

    def test_resolves_param_reference(self):
        command = ["python", "script.py", "{idea}"]
        resolved = resolve_placeholders(command, {}, {"idea": "AI tutor"})
        assert resolved == ["python", "script.py", "AI tutor"]

    def test_step_output_takes_priority_over_param(self):
        command = ["python", "script.py", "{scrape.records_path}"]
        outputs = {"scrape": {"records_path": "/tmp/out.json"}}
        resolved = resolve_placeholders(command, outputs, {"scrape": "should not use this"})
        assert "/tmp/out.json" in resolved

    def test_unresolved_placeholder_left_as_is(self):
        command = ["python", "script.py", "{unknown.thing}"]
        resolved = resolve_placeholders(command, {}, {})
        assert "{unknown.thing}" in resolved

    def test_multiple_placeholders(self):
        command = ["python", "script.py", "{a.path}", "--out", "{b.out}"]
        outputs = {
            "a": {"path": "/tmp/a.json"},
            "b": {"out": "/tmp/b.json"},
        }
        resolved = resolve_placeholders(command, outputs, {})
        assert resolved == ["python", "script.py", "/tmp/a.json", "--out", "/tmp/b.json"]


class TestEvaluateCondition:
    def test_true_condition(self):
        outputs = {"scrape": {"success": True}}
        assert evaluate_condition("scrape.success == true", outputs) is True

    def test_false_condition(self):
        outputs = {"scrape": {"success": False}}
        assert evaluate_condition("scrape.success == true", outputs) is False

    def test_null_condition_returns_true(self):
        assert evaluate_condition(None, {}) is True

    def test_neq_condition(self):
        outputs = {"step": {"status": "failed"}}
        assert evaluate_condition("step.status != success", outputs) is True

    def test_and_condition(self):
        outputs = {"a": {"success": True}, "b": {"success": True}}
        assert evaluate_condition("a.success == true and b.success == true", outputs) is True

    def test_and_condition_false(self):
        outputs = {"a": {"success": True}, "b": {"success": False}}
        assert evaluate_condition("a.success == true and b.success == true", outputs) is False

    def test_or_condition(self):
        outputs = {"a": {"success": False}, "b": {"success": True}}
        assert evaluate_condition("a.success == true or b.success == true", outputs) is True

    def test_missing_step_in_condition(self):
        assert evaluate_condition("missing.success == true", {}) is False


class TestExecute:
    def test_dry_run_emits_events_without_executing(self):
        plan = {
            "plan_id": "test-1",
            "workflow": "test",
            "request": "test request",
            "steps": [
                {
                    "name": "step1",
                    "skill": "test",
                    "description": "test step",
                    "command": ["echo", "hello"],
                    "depends_on": [],
                    "output_key": "step1",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan, dry_run=True))
        event_types = [e["event"] for e in events]
        assert "plan_started" in event_types
        assert "step_started" in event_types
        assert "step_done" in event_types
        assert "plan_done" in event_types
        done = next(e for e in events if e["event"] == "step_done")
        assert done["success"] is True

    def test_execute_real_subprocess(self):
        plan = {
            "plan_id": "test-2",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "echo_step",
                    "skill": "test",
                    "description": "echo test",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True, \"data\": \"hello\"}))"],
                    "depends_on": [],
                    "output_key": "echo_step",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan))
        done = next(e for e in events if e["event"] == "step_done")
        assert done["success"] is True
        assert done["output"]["data"] == "hello"

    def test_execute_with_dependency(self):
        plan = {
            "plan_id": "test-3",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "first",
                    "skill": "test",
                    "description": "first step",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True, \"path\": \"/tmp/out.json\"}))"],
                    "depends_on": [],
                    "output_key": "first",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
                {
                    "name": "second",
                    "skill": "test",
                    "description": "second step uses first output",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True, \"received\": \"{first.path}\"}))"],
                    "depends_on": ["first"],
                    "output_key": "second",
                    "condition": "first.success == true",
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan))
        second_done = next(e for e in events if e["event"] == "step_done" and e["step"] == "second")
        assert second_done["success"] is True
        assert "/tmp/out.json" in second_done["output"]["received"]

    def test_condition_false_skips_step(self):
        plan = {
            "plan_id": "test-4",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "first",
                    "skill": "test",
                    "description": "fails",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": False}))"],
                    "depends_on": [],
                    "output_key": "first",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
                {
                    "name": "second",
                    "skill": "test",
                    "description": "should be skipped",
                    "command": ["echo", "should not run"],
                    "depends_on": ["first"],
                    "output_key": "second",
                    "condition": "first.success == true",
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan))
        skipped = [e for e in events if e["event"] == "step_skipped"]
        assert len(skipped) == 1
        assert skipped[0]["step"] == "second"

    def test_retry_on_failure(self):
        plan = {
            "plan_id": "test-5",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "fail_step",
                    "skill": "test",
                    "description": "always fails",
                    "command": ["python", "-c", "import sys; sys.exit(1)"],
                    "depends_on": [],
                    "output_key": "fail_step",
                    "condition": None,
                    "retry": {"max_attempts": 2, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan))
        failed = next(e for e in events if e["event"] == "step_failed")
        assert failed["attempts"] == 2
        plan_done = next(e for e in events if e["event"] == "plan_done")
        assert plan_done["steps_failed"] == 1

    def test_checkpoint_pause_and_resume(self):
        plan = {
            "plan_id": "test-6",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "checkpoint_step",
                    "skill": "test",
                    "description": "has checkpoint",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True}))"],
                    "depends_on": [],
                    "output_key": "checkpoint_step",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": True,
                },
            ],
        }
        stdin_input = io.StringIO(json.dumps({"action": "resume"}) + "\n")
        events = list(execute(plan, stdin_input=stdin_input))
        checkpoint_events = [e for e in events if e["event"] == "checkpoint"]
        assert len(checkpoint_events) == 1
        done = next(e for e in events if e["event"] == "step_done")
        assert done["success"] is True

    def test_checkpoint_skip(self):
        plan = {
            "plan_id": "test-7",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "checkpoint_step",
                    "skill": "test",
                    "description": "has checkpoint",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True}))"],
                    "depends_on": [],
                    "output_key": "checkpoint_step",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": True,
                },
            ],
        }
        stdin_input = io.StringIO(json.dumps({"action": "skip"}) + "\n")
        events = list(execute(plan, stdin_input=stdin_input))
        skipped = [e for e in events if e["event"] == "step_skipped"]
        assert len(skipped) == 1
        assert skipped[0]["step"] == "checkpoint_step"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_runner.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.runner'`

- [ ] **Step 3: Write state.py**

Create `skills/reddit-orchestrator/pipeline/state.py`:

```python
"""Plan state persistence for resume support."""

import json

from .paths import orchestrator_dir


def state_path(plan_id):
    """Return the state file path for a given plan_id."""
    return orchestrator_dir() / f"{plan_id}.json"


def save_state(plan_id, state):
    """Save plan execution state to disk."""
    path = state_path(plan_id)
    path.write_text(json.dumps(state, indent=2, default=str))
    return path


def load_state(plan_id):
    """Load plan execution state from disk. Returns None if not found."""
    path = state_path(plan_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())
```

- [ ] **Step 4: Write runner.py**

Create `skills/reddit-orchestrator/pipeline/runner.py`:

```python
"""DAG-based plan executor with conditionals, retries, and checkpoints."""

import json
import re
import subprocess
import sys
import time

from .state import save_state


def topological_sort(steps):
    """Sort steps by dependency order. Raises ValueError on cycle."""
    name_to_step = {s["name"]: s for s in steps}
    visited = {}
    result = []

    def visit(name, path):
        if visited.get(name) == "done":
            return
        if visited.get(name) == "visiting":
            raise ValueError(f"Dependency cycle detected: {' -> '.join(path + [name])}")
        visited[name] = "visiting"
        step = name_to_step.get(name)
        if step is None:
            raise ValueError(f"Unknown dependency: {name}")
        for dep in step.get("depends_on", []):
            visit(dep, path + [name])
        visited[name] = "done"
        result.append(step)

    for step in steps:
        visit(step["name"], [])

    return result


def resolve_placeholders(command, step_outputs, params):
    """Replace {step_name.field} and {param_name} placeholders in command args."""
    resolved = []
    for arg in command:
        if not isinstance(arg, str):
            resolved.append(arg)
            continue

        def replace_step_ref(match):
            ref = match.group(1)
            if "." in ref:
                parts = ref.split(".", 1)
                step_name, field = parts[0], parts[1]
                step_out = step_outputs.get(step_name, {})
                value = step_out
                for key in field.split("."):
                    if isinstance(value, dict):
                        value = value.get(key)
                    else:
                        return match.group(0)
                if value is not None:
                    return str(value)
            return match.group(0)

        arg = re.sub(r"\{([^}]+)\}", replace_step_ref, arg)

        def replace_param_ref(match):
            ref = match.group(1)
            if "." not in ref and ref in params:
                return str(params[ref])
            return match.group(0)

        arg = re.sub(r"\{([^}]+)\}", replace_param_ref, arg)
        resolved.append(arg)
    return resolved


def evaluate_condition(condition, step_outputs):
    """Evaluate a condition string against step outputs."""
    if condition is None:
        return True

    or_parts = re.split(r"\s+or\s+", condition)
    for or_part in or_parts:
        and_parts = re.split(r"\s+and\s+", or_part)
        all_true = True
        for part in and_parts:
            if not _eval_single_condition(part.strip(), step_outputs):
                all_true = False
                break
        if all_true:
            return True
    return False


def _eval_single_condition(expr, step_outputs):
    """Evaluate a single condition expression."""
    m = re.match(r"(\w+)\.(\w+)\s*(==|!=)\s*(.+)", expr)
    if not m:
        return False

    step_name, field, op, value_str = m.groups()
    step_out = step_outputs.get(step_name)
    if step_out is None:
        return False

    actual = step_out.get(field)
    if actual is None:
        return False

    value_str = value_str.strip()
    if value_str == "true":
        expected = True
    elif value_str == "false":
        expected = False
    else:
        expected = value_str

    if op == "==":
        return actual == expected
    elif op == "!=":
        return actual != expected
    return False


def _run_subprocess(command):
    """Run a subprocess and return (success, output_dict)."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        if result.returncode != 0:
            return False, {"error": result.stderr.strip() or f"exit code {result.returncode}"}

        lines = result.stdout.strip().split("\n")
        if not lines or not lines[-1].strip():
            return True, {"stdout": result.stdout}

        try:
            output = json.loads(lines[-1])
            if "success" not in output:
                output["success"] = True
            return output.get("success", True), output
        except json.JSONDecodeError:
            return True, {"stdout": result.stdout}
    except subprocess.TimeoutExpired:
        return False, {"error": "subprocess timed out"}
    except Exception as exc:
        return False, {"error": str(exc)}


def _read_checkpoint_response(stdin_input):
    """Read a checkpoint response from stdin. Returns 'resume', 'skip', or None."""
    if stdin_input is None:
        line = sys.stdin.readline()
    else:
        line = stdin_input.readline()
    if not line:
        return None
    try:
        data = json.loads(line.strip())
        action = data.get("action", "").lower()
        if action in ("resume", "skip"):
            return action
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


def execute(plan, dry_run=False, stdin_input=None):
    """Execute a plan and yield JSONL events.

    Args:
        plan: Plan dict with plan_id, workflow, request, steps.
        dry_run: If True, print commands without executing.
        stdin_input: File-like object for checkpoint responses. If None, reads from sys.stdin.

    Yields:
        Event dicts (plan_started, step_started, step_done, step_skipped,
        step_failed, checkpoint, plan_done).
    """
    plan_id = plan.get("plan_id", "unknown")
    workflow = plan.get("workflow", "unknown")
    steps = plan.get("steps", [])

    yield {"event": "plan_started", "plan_id": plan_id, "workflow": workflow, "step_count": len(steps)}

    ordered_steps = topological_sort(steps)
    step_outputs = {}
    skipped_steps = set()
    completed = 0
    skipped = 0
    failed = 0

    for step in ordered_steps:
        name = step["name"]
        condition = step.get("condition")
        checkpoint = step.get("checkpoint", False)
        retry = step.get("retry", {"max_attempts": 1, "delay_seconds": 0})
        max_attempts = retry.get("max_attempts", 1)
        delay = retry.get("delay_seconds", 0)

        # Check if any dependency was skipped or failed
        deps = step.get("depends_on", [])
        dep_failed = any(d in skipped_steps or not step_outputs.get(d, {}).get("success") for d in deps)
        if dep_failed and condition is not None:
            yield {"event": "step_skipped", "step": name, "reason": "dependency failed or skipped"}
            skipped += 1
            skipped_steps.add(name)
            continue

        # Evaluate condition
        if not evaluate_condition(condition, step_outputs):
            yield {"event": "step_skipped", "step": name, "reason": "condition not met"}
            skipped += 1
            skipped_steps.add(name)
            continue

        # Checkpoint handling
        if checkpoint:
            yield {"event": "checkpoint", "step": name, "message": f"Review step '{name}' before proceeding. Send 'resume' to continue or 'skip' to skip."}
            action = _read_checkpoint_response(stdin_input)
            if action == "skip":
                yield {"event": "step_skipped", "step": name, "reason": "user skipped at checkpoint"}
                skipped += 1
                skipped_steps.add(name)
                continue
            elif action is None:
                yield {"event": "step_skipped", "step": name, "reason": "checkpoint timeout"}
                skipped += 1
                skipped_steps.add(name)
                continue

        # Resolve placeholders in command
        command = resolve_placeholders(step["command"], step_outputs, plan.get("params", {}))

        yield {"event": "step_started", "step": name, "skill": step.get("skill", "")}

        if dry_run:
            yield {
                "event": "step_done",
                "step": name,
                "success": True,
                "output": {"dry_run": True, "command": command},
            }
            step_outputs[step.get("output_key", name)] = {"success": True, "dry_run": True}
            completed += 1
            continue

        # Execute with retry
        attempts = 0
        success = False
        output = {}
        for attempt in range(max_attempts):
            attempts = attempt + 1
            success, output = _run_subprocess(command)
            if success:
                break
            if attempt < max_attempts - 1 and delay > 0:
                time.sleep(delay)

        if success:
            yield {"event": "step_done", "step": name, "success": True, "output": output}
            step_outputs[step.get("output_key", name)] = output
            completed += 1
        else:
            yield {"event": "step_failed", "step": name, "error": output.get("error", "unknown"), "attempts": attempts}
            step_outputs[step.get("output_key", name)] = {"success": False, "error": output.get("error")}
            failed += 1
            skipped_steps.add(name)

        # Save state after each step
        try:
            save_state(plan_id, {
                "plan_id": plan_id,
                "completed_steps": list(step_outputs.keys()),
                "step_outputs": step_outputs,
                "skipped_steps": list(skipped_steps),
            })
        except Exception:
            pass

    yield {
        "event": "plan_done",
        "plan_id": plan_id,
        "success": failed == 0,
        "steps_completed": completed,
        "steps_skipped": skipped,
        "steps_failed": failed,
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_runner.py -v
```

Expected: PASS (19 tests)

- [ ] **Step 6: Commit**

```bash
git add skills/reddit-orchestrator/pipeline/state.py skills/reddit-orchestrator/pipeline/runner.py skills/reddit-orchestrator/tests/test_runner.py
git commit -m "feat: add DAG runner with conditionals, retries, and checkpoints"
```

---

### Task 6: Preflight Script

**Files:**

- Create: `skills/reddit-orchestrator/scripts/preflight.py`
- Create: `skills/reddit-orchestrator/tests/test_preflight.py`

**Interfaces:**

- Consumes: `pipeline/skill_catalog.py` (`SKILLS`), `pipeline/paths.py` (`skill_dir()`), `reddit-auth/pipeline/auth.py` (`validate_credentials`)
- Produces: `preflight() -> dict` — emits JSON to stdout like other skills' preflight scripts.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-orchestrator/tests/test_preflight.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import preflight


class FakeAuth:
    def validate_credentials(self):
        return True, "ok"


def test_preflight_ok(monkeypatch):
    monkeypatch.setattr(preflight, "_load_auth", lambda: FakeAuth())
    result = preflight.preflight()
    assert result["deps_ok"] is True
    assert result["reddit_ok"] is True
    assert result["skills_ok"] is True


def test_preflight_missing_skill_dir(monkeypatch):
    monkeypatch.setattr(preflight, "_load_auth", lambda: FakeAuth())
    monkeypatch.setattr(preflight, "_check_skill_dirs", lambda: (False, ["reddit-foo"]))
    result = preflight.preflight()
    assert result["skills_ok"] is False
    assert "reddit-foo" in result["missing_skills"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_preflight.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.preflight'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/reddit-orchestrator/scripts/preflight.py`:

```python
import importlib
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.skill_catalog import SKILLS
from pipeline.paths import skill_dir


REQUIRED_ENV = []

REQUIRED_DEPS = [
    "dotenv",
]


def _load_auth():
    auth_path = skill_dir().parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    auth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth)
    return auth


def check_env(required=None):
    if required is None:
        required = REQUIRED_ENV
    missing = [key for key in required if not os.getenv(key)]
    return (len(missing) == 0, missing)


def check_deps(dependency_names=None):
    if dependency_names is None:
        dependency_names = REQUIRED_DEPS
    failed = []
    for name in dependency_names:
        try:
            importlib.import_module(name)
        except ImportError:
            failed.append(name)
    return (len(failed) == 0, failed)


def _check_skill_dirs():
    """Check that all skill directories exist."""
    root = skill_dir().parent
    missing = []
    for skill in SKILLS:
        skill_path = root / skill["name"]
        if not skill_path.is_dir():
            missing.append(skill["name"])
    return (len(missing) == 0, missing)


def preflight():
    env_ok, missing_env = check_env()
    deps_ok, missing_deps = check_deps()
    skills_ok, missing_skills = _check_skill_dirs()

    reddit_ok = False
    reddit_message = "dependencies missing"
    if env_ok and deps_ok and skills_ok:
        auth = _load_auth()
        reddit_ok, reddit_message = auth.validate_credentials()

    result = {
        "env_ok": env_ok,
        "deps_ok": deps_ok,
        "skills_ok": skills_ok,
        "reddit_ok": reddit_ok,
    }
    if not env_ok:
        result["missing"] = missing_env
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not skills_ok:
        result["missing_skills"] = missing_skills
    if not reddit_ok:
        result["reddit_error"] = reddit_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if all(result[k] for k in ["env_ok", "deps_ok", "skills_ok", "reddit_ok"]) else 1)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_preflight.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-orchestrator/scripts/preflight.py skills/reddit-orchestrator/tests/test_preflight.py
git commit -m "feat: add preflight script for orchestrator"
```

---

### Task 7: Plan CLI Script

**Files:**

- Create: `skills/reddit-orchestrator/scripts/plan.py`
- Create: `skills/reddit-orchestrator/tests/test_plan_script.py`

**Interfaces:**

- Consumes: `pipeline/planner.py` (`plan`)
- Produces: CLI entry point that outputs plan JSON to stdout or `--out` file.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-orchestrator/tests/test_plan_script.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.plan import main


def test_plan_outputs_json_to_stdout(capsys):
    code = main(["validate my idea: test idea"])
    assert code == 0
    captured = capsys.readouterr()
    plan = json.loads(captured.out)
    assert plan["workflow"] == "validate_idea"
    assert "plan_id" in plan
    assert "steps" in plan


def test_plan_writes_to_file(tmp_path):
    out_path = tmp_path / "plan.json"
    code = main(["validate my idea: test idea", "--out", str(out_path)])
    assert code == 0
    plan = json.loads(out_path.read_text())
    assert plan["workflow"] == "validate_idea"


def test_plan_with_forced_workflow(capsys):
    code = main(["some text", "--workflow", "track_trends"])
    assert code == 0
    captured = capsys.readouterr()
    plan = json.loads(captured.out)
    assert plan["workflow"] == "track_trends"


def test_plan_error_returns_nonzero(capsys, monkeypatch):
    monkeypatch.setattr("pipeline.planner._llm_available", lambda: (False, "no key"))
    code = main(["what is the weather today?"])
    assert code != 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "error" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_plan_script.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.plan'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/reddit-orchestrator/scripts/plan.py`:

```python
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.planner import plan as generate_plan


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Plan a Reddit orchestrator workflow")
    parser.add_argument("request", nargs="?", help="The user's request text")
    parser.add_argument("--workflow", default=None, help="Force a specific workflow")
    parser.add_argument("--out", default=None, help="Write plan to file instead of stdout")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.request:
        print(json.dumps({"error": "No request provided. Usage: plan.py \"your request\" [--workflow name] [--out file]"}))
        return 1

    result = generate_plan(args.request, workflow=args.workflow)

    if "error" in result:
        print(json.dumps(result))
        return 1

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, default=str))
    else:
        print(json.dumps(result, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_plan_script.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-orchestrator/scripts/plan.py skills/reddit-orchestrator/tests/test_plan_script.py
git commit -m "feat: add plan.py CLI script for orchestrator"
```

---

### Task 8: Run CLI Script

**Files:**

- Create: `skills/reddit-orchestrator/scripts/run.py`
- Create: `skills/reddit-orchestrator/tests/test_run_script.py`

**Interfaces:**

- Consumes: `pipeline/runner.py` (`execute`), `pipeline/planner.py` (`plan`)
- Produces: CLI entry point that loads a plan JSON and streams JSONL events to stdout.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-orchestrator/tests/test_run_script.py`:

```python
import json
import sys
import io
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run import main


def test_run_with_plan_file(tmp_path, capsys):
    plan = {
        "plan_id": "test-run-1",
        "workflow": "test",
        "request": "test",
        "steps": [
            {
                "name": "echo",
                "skill": "test",
                "description": "echo",
                "command": ["python", "-c", "import json; print(json.dumps({\"success\": True}))"],
                "depends_on": [],
                "output_key": "echo",
                "condition": None,
                "retry": {"max_attempts": 1, "delay_seconds": 0},
                "checkpoint": False,
            },
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    code = main(["--plan", str(plan_path)])
    assert code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    events = [json.loads(l) for l in lines]
    assert events[0]["event"] == "plan_started"
    assert any(e["event"] == "step_done" for e in events)
    assert events[-1]["event"] == "plan_done"
    assert events[-1]["success"] is True


def test_run_dry_run(tmp_path, capsys):
    plan = {
        "plan_id": "test-run-2",
        "workflow": "test",
        "request": "test",
        "steps": [
            {
                "name": "echo",
                "skill": "test",
                "description": "echo",
                "command": ["echo", "hello"],
                "depends_on": [],
                "output_key": "echo",
                "condition": None,
                "retry": {"max_attempts": 1, "delay_seconds": 0},
                "checkpoint": False,
            },
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    code = main(["--plan", str(plan_path), "--dry-run"])
    assert code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    events = [json.loads(l) for l in lines]
    done = next(e for e in events if e["event"] == "step_done")
    assert done["output"]["dry_run"] is True


def test_run_with_request(capsys):
    code = main(["--request", "validate my idea: test idea", "--dry-run"])
    assert code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    events = [json.loads(l) for l in lines]
    assert events[0]["event"] == "plan_started"
    assert events[0]["workflow"] == "validate_idea"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_run_script.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/reddit-orchestrator/scripts/run.py`:

```python
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.runner import execute
from pipeline.planner import plan as generate_plan


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Execute a Reddit orchestrator plan")
    parser.add_argument("--plan", default=None, help="Path to a plan JSON file")
    parser.add_argument("--request", default=None, help="Plan and run in one step")
    parser.add_argument("--workflow", default=None, help="Force a specific workflow (with --request)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--resume", default=None, help="Resume from a checkpoint (plan ID)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.resume:
        from pipeline.state import load_state
        state = load_state(args.resume)
        if state is None:
            print(json.dumps({"error": f"No saved state for plan {args.resume}"}))
            return 1
        plan_path = Path(__file__).resolve().parent.parent.parent / ".reddit-skills" / "orchestrator" / f"{args.resume}.plan.json"
        if not plan_path.exists():
            print(json.dumps({"error": f"No plan file for plan {args.resume}"}))
            return 1
        plan = json.loads(plan_path.read_text())
    elif args.request:
        plan = generate_plan(args.request, workflow=args.workflow)
        if "error" in plan:
            print(json.dumps(plan))
            return 1
    elif args.plan:
        plan = json.loads(Path(args.plan).read_text())
    else:
        print(json.dumps({"error": "Either --plan or --request is required"}))
        return 1

    for event in execute(plan, dry_run=args.dry_run):
        print(json.dumps(event))
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/test_run_script.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Run all tests together**

Run:

```bash
cd skills/reddit-orchestrator && python -m pytest tests/ -v
```

Expected: All tests PASS (total: 6 + 12 + 13 + 19 + 2 + 4 + 3 = 59 tests)

- [ ] **Step 6: Commit**

```bash
git add skills/reddit-orchestrator/scripts/run.py skills/reddit-orchestrator/tests/test_run_script.py
git commit -m "feat: add run.py CLI script for orchestrator"
```

---

## Self-Review

**1. Spec coverage:**

- **Architecture**: Covered — planner + runner + workflows + skill_catalog + scripts.
- **Components**: `planner.py` (Task 4), `runner.py` (Task 5), `workflows.py` (Task 3), `skill_catalog.py` (Task 2), `state.py` (Task 5). All present.
- **Plan JSON Structure**: Defined in workflows.py via `_step()` and `_new_plan()` helpers. Field reference matches spec.
- **Pre-defined Workflows**: All 4 workflows implemented in Task 3 (validate_idea, brand_growth, track_trends, engage_community).
- **Data Flow**: Output passing via `{step_name.field}` placeholders implemented in Task 5 (`resolve_placeholders`).
- **Error Handling**: Retry logic, condition evaluation, checkpoint protocol, state persistence — all in Task 5.
- **Testing**: Tests for all components — test_skill_catalog, test_workflows, test_planner, test_runner, test_preflight, test_plan_script, test_run_script.
- **File Layout**: Matches spec exactly.
- **SKILL.md Contract**: Written in Task 1.
- **Dependencies**: requirements.txt in Task 1.
- **Scripts**: preflight.py (Task 6), plan.py (Task 7), run.py (Task 8). All present.

**2. Placeholder scan:** No TBDs, TODOs, or "implement later" found. All steps contain complete code.

**3. Type consistency:**

- `match_workflow` returns `(workflow_name, params) | None` — consistent in planner.py and tests.
- `build_plan(workflow, request, params)` — consistent in workflows.py and planner.py.
- `execute(plan, dry_run, stdin_input)` — consistent in runner.py and run.py.
- `resolve_placeholders(command, step_outputs, params)` — consistent in runner.py.
- `evaluate_condition(condition, step_outputs)` — consistent in runner.py.
- `topological_sort(steps)` — consistent in runner.py.
- `SKILLS` list and `get_skill` / `catalog_summary` — consistent in skill_catalog.py and planner.py.
- `_step()` helper fields match the Plan JSON Structure in the spec.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-01-reddit-orchestrator.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
