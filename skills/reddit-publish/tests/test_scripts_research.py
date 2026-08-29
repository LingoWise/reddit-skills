import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import research


def test_research_main(monkeypatch, capsys, tmp_path):
    def fake_research(*args, **kwargs):
        return {"subreddit": "r/test", "suggestions": [], "records": [], "patterns": {}, "language": "en"}

    monkeypatch.setattr(research, "researcher_research", fake_research)
    monkeypatch.setattr(research.paths, "records_dir", lambda: tmp_path)
    code = research.main(["test topic"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["success"] is True
