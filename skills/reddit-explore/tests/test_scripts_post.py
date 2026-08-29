import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import post


class FakeFetcher:
    def post(self, *args, **kwargs):
        return (
            {"id": "p1", "subreddit": "test", "title": "T", "selftext": "body", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"},
            [{"id": "c1", "body": "cm", "author": "u1", "score": 2, "permalink": "/r/test/p1/c1"}],
        )

    def close(self):
        pass


def test_post_main(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(post, "get_fetcher", lambda: FakeFetcher())
    monkeypatch.setattr(post, "records_dir", lambda: tmp_path)
    code = post.main(["p1"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["count"] == 2
