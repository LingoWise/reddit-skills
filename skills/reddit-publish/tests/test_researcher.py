import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import researcher


def test_research_uses_provided_records(monkeypatch):
    records = [{"subreddit": "AskReddit", "title": "T", "text": "hello", "url": "https://reddit.com/1", "is_comment": False}]
    called = {}

    def fake_llm(messages, **kwargs):
        called["llm"] = True
        return {"hook_patterns": ["question"], "title_length": "short", "tone": "casual", "high_engagement_themes": ["relatable"]}

    from pipeline import researcher as rmod
    monkeypatch.setattr(rmod, "_load_llm", lambda: type("Llm", (), {"chat_json": staticmethod(fake_llm)})())

    result = rmod.research("test", records=records, subreddit="AskReddit")
    assert result["subreddit"] == "r/AskReddit"
    assert result["patterns"]["tone"] == "casual"
    assert result["records"] == records
