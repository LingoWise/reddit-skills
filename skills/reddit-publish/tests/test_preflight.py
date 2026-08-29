import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import preflight


def test_preflight_returns_json(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "_load_auth", lambda: type("Auth", (), {"validate_credentials": staticmethod(lambda: (True, "ok"))})())
    monkeypatch.setattr(preflight, "_load_llm", lambda: type("Llm", (), {"available": staticmethod(lambda: (True, "ok"))})())
    result = preflight.preflight()
    assert result["deps_ok"] is True
    assert result["reddit_ok"] is True
