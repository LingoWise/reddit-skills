import importlib.util
import json
from pathlib import Path


def _load_explorer():
    explore_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "explorer.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_explorer", explore_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_explorer_client():
    client_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "client.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_client", client_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_llm():
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build_corpus(records):
    parts = []
    for rec in records:
        sub = rec.get("subreddit", "unknown").removeprefix("r/")
        title = rec.get("title", "")
        text = rec.get("text", "")
        parts.append(f"r/{sub}: {title}\n{text}")
    return "\n\n---\n\n".join(parts)


def _normalize_subreddit(name):
    if not name:
        return None
    name = name.strip()
    if name.lower().startswith("r/"):
        name = name[2:]
    return name


def _canonical_subreddit(name):
    n = _normalize_subreddit(name)
    if not n:
        return None
    return f"r/{n}"


def research(
    topic: str,
    *,
    subreddit: str | None = None,
    limit: int = 25,
    sort: str = "top",
    time_filter: str = "month",
    suggest_subreddit: bool = False,
    records: list[dict] | None = None,
    language: str = "en",
):
    from pipeline import prompts

    target = _normalize_subreddit(subreddit)
    suggestions = []

    if records is None:
        explorer = _load_explorer()
        client_mod = _load_explorer_client()

        fetcher = client_mod.get_fetcher()
        try:
            if target:
                records = explorer.list_subreddit(target, fetcher=fetcher, sort=sort, limit=limit, time_filter=time_filter)
                records += explorer.search_posts(topic, fetcher=fetcher, subreddits=target, sort="relevance", time_filter="all", limit=limit)
            else:
                records = explorer.search_posts(topic, fetcher=fetcher, sort=sort, time_filter=time_filter, limit=limit)
        finally:
            fetcher.close()

    if suggest_subreddit and not target:
        llm = _load_llm()
        corpus = _build_corpus(records[:limit])
        raw = llm.chat_json(
            messages=[
                {"role": "system", "content": "You output only valid JSON."},
                {"role": "user", "content": prompts.SUBREDDIT_SUGGEST_PROMPT.format(topic=topic, corpus=corpus)},
            ],
            temperature=0.2,
        )
        suggestions = [f"r/{s.removeprefix('r/')}" for s in raw.get("subreddits", [])]
    elif not target:
        counts = {}
        for rec in records:
            sub = rec.get("subreddit", "unknown")
            if not sub.startswith("r/"):
                sub = f"r/{sub}"
            counts[sub] = counts.get(sub, 0) + 1
        suggestions = sorted(counts, key=counts.get, reverse=True)[:5]

    patterns = {}
    if records:
        llm = _load_llm()
        corpus = _build_corpus(records[:limit])
        patterns = llm.chat_json(
            messages=[
                {"role": "system", "content": "You output only valid JSON."},
                {"role": "user", "content": prompts.RESEARCH_PROMPT.format(topic=topic, subreddit=_canonical_subreddit(target or "all"), corpus=corpus)},
            ],
            temperature=0.2,
        )

    return {
        "topic": topic,
        "subreddit": _canonical_subreddit(target),
        "suggestions": suggestions,
        "records": records,
        "patterns": patterns,
        "language": language,
    }
