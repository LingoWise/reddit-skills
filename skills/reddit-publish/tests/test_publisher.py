import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import publisher


def test_publish_self_post(monkeypatch):
    page_calls = []

    class FakePage:
        def evaluate(self, script, arg=None):
            page_calls.append(arg)
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200, "body": '{"json": {"data": {"url": "/r/test/comments/abc123/title", "id": "abc123"}}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    p = publisher.Publisher(FakeSession())
    result = p.publish(subreddit="test", title="Hello", kind="self", body="body text")
    assert result["post_id"] == "abc123"
    assert page_calls
