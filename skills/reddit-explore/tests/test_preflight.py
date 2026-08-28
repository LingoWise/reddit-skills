import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import preflight


class FakeAuth:
    def validate_credentials(self):
        return True, "ok"


def test_preflight_ok(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "_load_auth", lambda: FakeAuth())
    result = preflight.preflight()
    assert result["deps_ok"] is True
    assert result["reddit_ok"] is True
