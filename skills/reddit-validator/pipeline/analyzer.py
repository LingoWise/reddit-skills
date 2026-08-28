import importlib.util
import json
from pathlib import Path


def _load_llm():
    """Load the shared LLM client from the project-root lib/ directory."""
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    llm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llm)
    return llm


PROMPT = """You are a sharp market research analyst and startup strategist. Given the Reddit posts and comments below, evaluate the business idea and produce a scored, actionable report.

Idea: {idea}

Reddit content:
{corpus}

Analyze the corpus carefully. Quote or paraphrase real evidence from the posts when possible. Be honest — do not inflate the score. Your job is to help the founder decide whether and how to pursue this, not to cheerlead.

Return a single JSON object with exactly these keys:

- score: integer 0-100. Score guide: >=75 strong signal (clear pain + demand + room to win), 50-74 promising (real interest but execution/positioning matters), 30-49 weak (demand exists but fragmented or well-served), <30 likely no-go.
- market_snapshot: list of strings. Each entry is a concise factual statement about the CURRENT state of the market/niche, grounded in the Reddit data (e.g. "Multiple founders are already launching AI IELTS writing tools and recruiting beta testers", "Students widely use ChatGPT/Claude for writing feedback but find scores inconsistent"). Capture what is happening RIGHT NOW — trends, player activity, user behavior, sentiment baseline.
- pain_points: list of {{"text": string, "weight": integer}}. Weight 1-5 (5 = most acute). Each pain point should be a specific, verifiable problem expressed by real users in the corpus.
- existing_solutions: list of strings. Products, services, or workarounds already mentioned by name or description in the corpus.
- opportunities: list of {{"text": string, "weight": integer}}. Weight 1-5 (5 = biggest gap). Unmet needs or gaps you can exploit.
- how_to_win: list of strings. Subjective but worthy strategic recommendations on how to differentiate and win given what the corpus reveals. Think like a founder: what wedge, positioning, moat, or go-to-market move would give this idea the best chance? Be specific and opinionated — generic advice like "build a great product" is useless. Draw on the competitive landscape and user sentiment you observed.
- recommendations: list of strings. Concrete next-step actions (go/no-go, what to build first, what to validate next).
- comment_tags: {{"positive": int, "negative": int, "question": int, "suggestion": int}}. Count of comments that fall into each sentiment/intent category.

Do not include markdown or explanation, only the JSON object."""


def _build_corpus(records):
    parts = []
    for record in records:
        label = "COMMENT" if record.get("is_comment") else "POST"
        parts.append(f"[{label}] {record.get('title', '')}\n{record.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def analyze(records, idea, profile, client=None):
    llm = _load_llm()
    corpus = _build_corpus(records)
    return llm.chat_json(
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": PROMPT.format(idea=idea, corpus=corpus)},
        ],
        temperature=0.2,
        client_obj=client,
    )
