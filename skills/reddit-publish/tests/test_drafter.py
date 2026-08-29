import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import drafter


def test_draft_generates_self_post(monkeypatch):
    research = {
        "subreddit": "r/AskReddit",
        "patterns": {"tone": "casual", "hook_patterns": ["question"]},
        "records": [],
        "language": "en",
    }

    def fake_llm(messages, **kwargs):
        return {
            "title": "What is the best advice you ever received?",
            "body": "Just curious what others think.",
            "kind": "self",
            "url": "",
            "image_prompt": "",
            "inspiration": [],
        }

    monkeypatch.setattr(drafter, "_load_llm", lambda: type("Llm", (), {"chat_json": staticmethod(fake_llm)})())

    result = drafter.draft("advice", research)
    assert result["kind"] == "self"
    assert result["title"].startswith("What")
    assert result["body"]
    assert result["subreddit"] == "r/AskReddit"
