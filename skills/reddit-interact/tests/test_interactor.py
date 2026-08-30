import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import interactor


def test_normalize_post_id_from_url():
    assert interactor.normalize_thing_id(
        "https://www.reddit.com/r/test/comments/abc123/title_here/", "post"
    ) == "t3_abc123"


def test_normalize_post_id_from_permalink():
    assert interactor.normalize_thing_id("/r/test/comments/abc123/title/", "post") == "t3_abc123"


def test_normalize_post_id_bare():
    assert interactor.normalize_thing_id("abc123", "post") == "t3_abc123"


def test_normalize_post_id_already_prefixed():
    assert interactor.normalize_thing_id("t3_abc123", "post") == "t3_abc123"


def test_normalize_comment_id_from_url():
    assert interactor.normalize_thing_id(
        "https://www.reddit.com/r/test/comments/abc123/title/def456/", "comment"
    ) == "t1_def456"


def test_normalize_comment_id_bare():
    assert interactor.normalize_thing_id("def456", "comment") == "t1_def456"


def test_normalize_comment_id_already_prefixed():
    assert interactor.normalize_thing_id("t1_def456", "comment") == "t1_def456"


def test_comment(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200,
                    "body": '{"json": {"data": {"things": [{"data": {"id": "c1", "permalink": "/r/test/comments/abc/title/c1"}}]}}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.comment("t3_abc", "Hello world")
    assert result["comment_id"] == "c1"
    assert "permalink" in result


def test_reply(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200,
                    "body": '{"json": {"data": {"things": [{"data": {"id": "c2", "permalink": "/r/test/comments/abc/title/c2"}}]}}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.reply("t1_c1", "Reply text")
    assert result["comment_id"] == "c2"


def test_vote(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200, "body": '{"json": {}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.vote("t3_abc", 1)
    assert result["action"] == "vote"
    assert result["direction"] == 1


def test_save(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200, "body": '{"json": {}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.save("t3_abc")
    assert result["action"] == "save"
    assert result["thing_id"] == "t3_abc"


def test_unsave(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200, "body": '{"json": {}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.unsave("t3_abc")
    assert result["action"] == "unsave"
    assert result["thing_id"] == "t3_abc"
