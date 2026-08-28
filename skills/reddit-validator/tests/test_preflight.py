import json
import os

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


class FakeAuth:
    def __init__(self, ok=True, message="ok"):
        self._ok = ok
        self._message = message

    def validate_credentials(self):
        return self._ok, self._message


class TestCheckReddit:
    def test_ok(self, monkeypatch):
        monkeypatch.setattr("scripts.preflight._load_auth", lambda: FakeAuth(ok=True, message="rustwright browser login available"))
        ok, message = check_reddit("id", "secret", "agent")
        assert ok is True
        assert "rustwright" in message

    def test_auth_fails(self, monkeypatch):
        monkeypatch.setattr("scripts.preflight._load_auth", lambda: FakeAuth(ok=False, message="bearer token failed: 401"))
        ok, message = check_reddit("id", "secret", "agent")
        assert ok is False
        assert "401" in message

    def test_browser(self, monkeypatch):
        monkeypatch.setattr("scripts.preflight._load_auth", lambda: FakeAuth(ok=True, message="rustwright browser login available"))
        ok, message = check_reddit("", "", "")
        assert ok is True
        assert "rustwright" in message


class TestPreflight:
    def test_returns_json_and_ok(self, monkeypatch, capsys):
        for key in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]:
            monkeypatch.setenv(key, "x")
        monkeypatch.setattr("scripts.preflight.check_reddit", lambda *_: (True, ""))
        result = preflight()
        assert result["env_ok"] is True
        assert result["deps_ok"] is True
        assert result["reddit_ok"] is True
