import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import search


class FakeFetcher:
    def __init__(self, records):
        self._records = records

    def search(self, *args, **kwargs):
        return [{"id": "p1", "subreddit": "test", "title": "T", "selftext": "", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"}]

    def close(self):
        pass


def test_search_main(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(search, "get_fetcher", lambda: FakeFetcher([]))
    monkeypatch.setattr(search, "records_dir", lambda: tmp_path)
    code = search.main(["hello", "--limit", "1", "--comments", "0"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["count"] == 1
    assert "posts" in out
    assert isinstance(out["posts"], list)
    assert out["posts"][0]["url"]
