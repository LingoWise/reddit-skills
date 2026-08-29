import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import draft


def test_draft_main(monkeypatch, capsys, tmp_path):
    research_path = tmp_path / "research.json"
    research_path.write_text(json.dumps({
        "subreddit": "r/test",
        "patterns": {},
        "records": [],
        "language": "en",
        "suggestions": [],
    }))

    def fake_draft(*args, **kwargs):
        return {"title": "T", "body": "B", "kind": "self", "subreddit": "r/test", "style": "casual", "language": "en"}

    monkeypatch.setattr(draft, "drafter_draft", fake_draft)
    monkeypatch.setattr(draft.paths, "drafts_dir", lambda: tmp_path)
    code = draft.main([str(research_path)])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
