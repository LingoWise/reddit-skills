import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import publish


def test_publish_main_dry_run(monkeypatch, capsys, tmp_path):
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(json.dumps({
        "title": "T",
        "body": "B",
        "kind": "self",
        "subreddit": "r/test",
    }))

    def fake_publish(*args, **kwargs):
        return {"post_id": "abc", "post_url": "https://reddit.com/abc", "permalink": "/r/test/abc", "subreddit": "r/test", "title": "T"}

    class FakePublisher:
        publish = staticmethod(fake_publish)

        def close(self):
            pass

    monkeypatch.setattr(publish, "Publisher", FakePublisher)
    code = publish.main([str(draft_path), "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
