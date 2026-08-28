import json
import os

import pytest

from pipeline.analyzer import analyze


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(FakeMessage(content))]


class FakeCompletions:
    def __init__(self, content):
        self._content = content

    def create(self, **kwargs):
        return FakeResponse(self._content)


class FakeChat:
    def __init__(self, content):
        self.completions = FakeCompletions(content)


class FakeOpenAI:
    def __init__(self, content):
        self._content = content

    @property
    def chat(self):
        return FakeChat(self._content)


def test_analyze_parses_llm_json(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = json.dumps({
        "score": 72,
        "pain_points": [{"text": "pain A", "weight": 2}],
        "existing_solutions": ["x"],
        "opportunities": [{"text": "opportunity A", "weight": 1}],
        "recommendations": ["go"],
        "comment_tags": {"positive": 5, "negative": 1, "question": 0, "suggestion": 0},
    })
    client = FakeOpenAI(payload)

    records = [{"title": "t", "text": "hello", "is_comment": True}]
    result = analyze(records, "AI todo", {"llm_agents": 1}, client=client)

    assert result["score"] == 72
    assert result["pain_points"][0]["text"] == "pain A"
    assert result["comment_tags"]["positive"] == 5
