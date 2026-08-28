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


LANGUAGE_NAMES = {
    "en": "English",
    "zh": "中文（简体）",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "pt": "Português",
    "ru": "Русский",
    "ar": "العربية",
}

PROMPT = """You are a sharp market research analyst and startup strategist. Given the Reddit posts and comments below, evaluate the business idea and produce a scored, actionable, evidence-backed report.

## Idea
{idea}

## Language
Write ALL text content (market_snapshot, pain_points, existing_solutions, opportunities, how_to_win, recommendations, analysis_method) in {language_name}. The score, weights, and URLs remain as-is. The `original_idea` field must preserve the user's original wording verbatim.

## Reddit content
{corpus}

## Analysis method
First, classify the idea type (SaaS, consumer product, marketplace, creative content, service, platform, etc.). Then select the most fitting analysis framework from:
- Jobs-to-be-Done — for products solving a specific user job
- SWOT Analysis — for general strategic overview
- Porter's Five Forces — for competitive market analysis
- Lean Canvas — for startup viability assessment
- Blue Ocean Strategy — for finding uncontested market space
- Kano Model — for feature prioritization and customer satisfaction
- Two-Sided Market Analysis — for marketplace/platform ideas
- Competitive Moat Analysis — for ideas in crowded markets with incumbents

Pick ONE primary framework (or combine two if clearly justified). State why it fits this idea type. Apply the framework's lens throughout your analysis.

## Evidence and citations
Every claim in market_snapshot, pain_points, existing_solutions, and opportunities MUST include at least one source citation from the corpus. Use the `sources` field: a list of {{"subreddit": "r/...", "url": "..."}} objects referencing specific posts or comments that support the claim. Quote or paraphrase real evidence from those sources. Do not fabricate sources — only cite URLs that appear in the corpus above.

## Scoring
Be honest — do not inflate the score. Your job is to help the founder decide whether and how to pursue this, not to cheerlead.
- >=75: strong signal (clear pain + demand + room to win)
- 50-74: promising (real interest but execution/positioning matters)
- 30-49: weak (demand exists but fragmented or well-served)
- <30: likely no-go

## Output
Return a single JSON object with exactly these keys:

- score: integer 0-100
- language: "{language}" (echo back the language code)
- original_idea: the idea text verbatim as provided above
- analysis_method: {{"name": string, "rationale": string}} — the framework chosen and why it fits this idea
- market_snapshot: list of {{"text": string, "sources": [{{"subreddit": string, "url": string}}]}} — concise factual statements about the CURRENT market state, each grounded in specific Reddit evidence
- pain_points: list of {{"text": string, "weight": integer 1-5, "sources": [{{"subreddit": string, "url": string}}]}} — specific, verifiable problems expressed by real users, weight 5 = most acute
- existing_solutions: list of {{"name": string, "description": string, "sources": [{{"subreddit": string, "url": string}}]}} — products, services, or workarounds mentioned in the corpus
- opportunities: list of {{"text": string, "weight": integer 1-5, "sources": [{{"subreddit": string, "url": string}}]}} — unmet needs or exploitable gaps, weight 5 = biggest gap
- how_to_win: list of strings — opinionated strategic recommendations on wedge, positioning, moat, or go-to-market. Be specific — generic advice like "build a great product" is useless. Draw on the competitive landscape and user sentiment you observed.
- recommendations: list of strings — concrete next-step actions (go/no-go, what to build first, what to validate next)
- comment_tags: {{"positive": int, "negative": int, "question": int, "suggestion": int}} — count of comments in each sentiment/intent category

Do not include markdown or explanation, only the JSON object."""


def _build_corpus(records):
    parts = []
    for record in records:
        label = "COMMENT" if record.get("is_comment") else "POST"
        sub = record.get("subreddit", "unknown")
        url = record.get("url", "")
        title = record.get("title", "")
        text = record.get("text", "")
        parts.append(f"[{label}] r/{sub} | {url}\n{title}\n{text}")
    return "\n\n---\n\n".join(parts)


def analyze(records, idea, profile, client=None, language="en"):
    llm = _load_llm()
    corpus = _build_corpus(records)
    language_name = LANGUAGE_NAMES.get(language, "English")
    return llm.chat_json(
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": PROMPT.format(
                idea=idea,
                corpus=corpus,
                language=language,
                language_name=language_name,
            )},
        ],
        temperature=0.2,
        client_obj=client,
    )
