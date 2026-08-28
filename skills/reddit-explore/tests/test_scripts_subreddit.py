import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import subreddit


class FakeFetcher:
    def subreddit_listing(self, *args, **kwargs):
        return [{"id": "p1", "subreddit": "test", "title": "T", "selftext": "", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"}]

    def close(self):
        pass


def test_subreddit_main(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(subreddit, "get_fetcher", lambda: FakeFetcher())
    monkeypatch.setattr(subreddit, "records_dir", lambda: tmp_path)
    code = subreddit.main(["test", "--limit", "1"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["count"] == 1
