import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import user


class FakeFetcher:
    def user(self, *args, **kwargs):
        return [{"kind": "t1", "data": {"id": "c1", "link_id": "t3_p1", "subreddit": "test", "body": "hi", "author": "u1", "score": 1, "permalink": "/r/test/p1/c1"}}]

    def close(self):
        pass


def test_user_main(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(user, "get_fetcher", lambda: FakeFetcher())
    monkeypatch.setattr(user, "records_dir", lambda: tmp_path)
    code = user.main(["u1"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["count"] == 1
