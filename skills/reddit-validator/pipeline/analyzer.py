import json
import os
from dotenv import load_dotenv


PROMPT = """You are a market research analyst. Given the Reddit posts and comments below, evaluate the business idea or niche described in the user's query.

Idea: {idea}

Reddit content:
{corpus}

Return a single JSON object with exactly these keys:
- score: integer 0-100
- pain_points: list of {{"text": string, "weight": integer}}
- existing_solutions: list of strings
- opportunities: list of {{"text": string, "weight": integer}}
- recommendations: list of strings
- comment_tags: {{"positive": int, "negative": int, "question": int, "suggestion": int}}

Do not include markdown or explanation, only the JSON object."""


def _build_corpus(records):
    parts = []
    for record in records:
        label = "COMMENT" if record.get("is_comment") else "POST"
        parts.append(f"[{label}] {record.get('title', '')}\n{record.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def _client():
    load_dotenv()
    from openai import OpenAI
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )


def analyze(records, idea, profile, client=None):
    if client is None:
        client = _client()
    model = os.getenv("OPENAI_MODEL")
    corpus = _build_corpus(records)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": PROMPT.format(idea=idea, corpus=corpus)},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.strip("`").strip("json").strip()
    return json.loads(content)
