import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import preflight


class FakeAuth:
    def validate_credentials(self):
        return True, "ok"


def test_preflight_ok(monkeypatch):
    monkeypatch.setattr(preflight, "_load_auth", lambda: FakeAuth())
    result = preflight.preflight()
    assert result["deps_ok"] is True
    assert result["reddit_ok"] is True
    assert result["skills_ok"] is True


def test_preflight_missing_skill_dir(monkeypatch):
    monkeypatch.setattr(preflight, "_load_auth", lambda: FakeAuth())
    monkeypatch.setattr(preflight, "_check_skill_dirs", lambda: (False, ["reddit-foo"]))
    result = preflight.preflight()
    assert result["skills_ok"] is False
    assert "reddit-foo" in result["missing_skills"]
