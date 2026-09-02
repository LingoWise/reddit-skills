"""Hybrid planner: pattern-match known workflows, fall back to LLM for novel requests."""

import re

from .skill_catalog import catalog_summary
from .workflows import build_plan

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
        "extract_topic": r"(?:trends?\s+for\s+(.+)|趋势[:：]\s*(.+)|热门[:：]\s*(.+)|(.+?)(?:的)?(?:趋势|热门)|热门(?:的)?\s*(.+)|趋势\s*(.+))",
        "extract_topic_group_fallback": True,
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
        if topic_m:
            groups = [g for g in topic_m.groups() if g is not None]
            params["topic"] = groups[0].strip() if groups else request_text
        else:
            params["topic"] = request_text
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


def _default_params(workflow, request_text):
    """Return minimal params for a forced workflow using the request text."""
    primary = {
        "validate_idea": "idea",
        "brand_growth": "brand",
        "track_trends": "topic",
        "engage_community": "brand",
    }
    key = primary.get(workflow, "idea")
    return {key: request_text}


def llm_plan(request_text):
    """Generate a plan using the LLM fallback."""
    import importlib.util
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
            params = _default_params(workflow, request_text)
        return build_plan(workflow, request_text, params)

    matched = match_workflow(request_text)
    if matched is not None:
        workflow_name, params = matched
        return build_plan(workflow_name, request_text, params)

    ok, _ = _llm_available()
    if ok:
        try:
            return llm_plan(request_text)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"LLM planning failed: {exc}", "request": request_text}

    return {
        "error": "Could not match a known workflow and LLM is not available. "
                 "Set OPENAI_API_KEY or OPENROUTER_API_KEY for LLM-driven planning, "
                 "or specify a workflow with --workflow.",
        "request": request_text,
    }
