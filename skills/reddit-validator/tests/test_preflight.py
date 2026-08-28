import json
import os
import praw

import pytest

from scripts.preflight import (
    check_env,
    check_deps,
    check_reddit,
    preflight,
)


class TestCheckEnv:
    def test_all_set(self, monkeypatch):
        for key in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]:
            monkeypatch.setenv(key, "x")
        ok, missing = check_env(["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"])
        assert ok is True
        assert missing == []

    def test_missing(self, monkeypatch):
        for key in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]:
            monkeypatch.delenv(key, raising=False)
        ok, missing = check_env(["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"])
        assert ok is False
        assert missing == ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]


class TestCheckDeps:
    def test_installed(self):
        ok, failed = check_deps(["json", "os"])
        assert ok is True
        assert failed == []

    def test_missing(self):
        ok, failed = check_deps(["not_a_real_package_12345"])
        assert ok is False
        assert failed == ["not_a_real_package_12345"]


class FakeSearch:
    def __init__(self, fail=False):
        self._fail = fail

    def search(self, *args, **kwargs):
        if self._fail:
            raise Exception("401")
        return [type("Submission", (), {"id": "p1"})]


class FakeSubreddit:
    def __init__(self, fail=False):
        self._fail = fail

    def search(self, *args, **kwargs):
        if self._fail:
            raise Exception("401")
        return [type("Submission", (), {"id": "p1"})]


class FakeReddit:
    def __init__(self, fail=False):
        self._fail = fail

    def subreddit(self, name):
        return FakeSubreddit(self._fail)


class TestCheckReddit:
    def test_ok(self, monkeypatch):
        monkeypatch.setattr("scripts.preflight._use_playwright", lambda: False)
        monkeypatch.setattr(praw, "Reddit", lambda **_: FakeReddit())
        ok, message = check_reddit("id", "secret", "agent")
        assert ok is True
        assert "authenticated" in message

    def test_auth_fails(self, monkeypatch):
        monkeypatch.setattr("scripts.preflight._use_playwright", lambda: False)
        monkeypatch.setattr(praw, "Reddit", lambda **_: FakeReddit(fail=True))
        ok, message = check_reddit("id", "secret", "agent")
        assert ok is False
        assert "401" in message

    def test_playwright(self, monkeypatch):
        monkeypatch.setattr("scripts.preflight._use_playwright", lambda: True)
        ok, message = check_reddit("", "", "")
        assert ok is True
        assert "playwright" in message


class TestPreflight:
    def test_returns_json_and_ok(self, monkeypatch, capsys):
        for key in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]:
            monkeypatch.setenv(key, "x")
        monkeypatch.setattr("scripts.preflight.check_reddit", lambda *_: (True, ""))
        result = preflight()
        assert result["env_ok"] is True
        assert result["deps_ok"] is True
        assert result["reddit_ok"] is True
