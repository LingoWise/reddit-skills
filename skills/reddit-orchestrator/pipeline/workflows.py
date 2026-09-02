"""Pre-defined workflow templates for the orchestrator.

Each function returns a plan JSON dict with parameterized steps.
The planner fills in user-provided parameters.
"""

import time
import uuid
from datetime import datetime, timezone

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
        "created_at": datetime.now(timezone.utc).isoformat(),
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
    plan = WORKFLOW_FNS[workflow](**params)
    plan["request"] = request
    return plan
