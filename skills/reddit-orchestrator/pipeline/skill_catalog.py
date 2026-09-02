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
