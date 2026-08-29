import importlib.util
import json
from pathlib import Path


DEFAULT_STYLE = "casual"
STYLE_PRESETS = ("casual", "story", "question", "helpful", "hot_take", "meme", "discussion")


def _load_llm():
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _resolve_style(style: str | None) -> str:
    if not style:
        return DEFAULT_STYLE
    style = style.strip()
    if style in STYLE_PRESETS:
        return style
    return f"custom: {style}"


def _resolve_subreddit(research: dict, subreddit: str | None) -> str:
    if subreddit:
        s = subreddit.strip()
        return s if s.startswith("r/") else f"r/{s}"
    if research.get("subreddit"):
        return research["subreddit"]
    if research.get("suggestions"):
        return research["suggestions"][0]
    raise ValueError("No target subreddit in research output and none provided")


def _infer_kind(kind, image_path, image_prompt, image_url, link_url):
    if kind:
        return kind
    if link_url:
        return "link"
    if image_path or image_prompt or image_url:
        return "image"
    return "self"


def _build_patterns_text(patterns: dict) -> str:
    if not patterns:
        return ""
    parts = []
    for key, value in patterns.items():
        parts.append(f"{key}: {json.dumps(value)}")
    return "\n".join(parts)


def draft(
    topic: str,
    research: dict,
    *,
    subreddit: str | None = None,
    style: str | None = DEFAULT_STYLE,
    image_path: str | None = None,
    image_prompt: str | None = None,
    image_url: str | None = None,
    link_url: str | None = None,
    language: str = "en",
    kind: str | None = None,
):
    from pipeline import prompts

    target_sub = _resolve_subreddit(research, subreddit)
    resolved_style = _resolve_style(style)
    resolved_kind = _infer_kind(kind, image_path, image_prompt, image_url, link_url)

    llm = _load_llm()
    raw = llm.chat_json(
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompts.DRAFT_PROMPT.format(
                subreddit=target_sub.removeprefix("r/"),
                topic=topic,
                style=resolved_style,
                language=language,
                patterns=_build_patterns_text(research.get("patterns", {})),
            )},
        ],
        temperature=0.5,
    )

    title = raw.get("title", "").strip()
    body = raw.get("body", "").strip()
    if len(title) > 300:
        title = title[:300]

    return {
        "title": title,
        "body": body,
        "kind": resolved_kind,
        "subreddit": target_sub,
        "style": style or DEFAULT_STYLE,
        "language": language,
        "url": link_url or raw.get("url", ""),
        "image_path": image_path or "",
        "image_prompt": image_prompt or raw.get("image_prompt", "") or image_url or "",
        "inspiration": raw.get("inspiration", []),
    }
