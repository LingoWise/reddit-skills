import json
import openai
import os
import praw

import pytest

from scripts.preflight import (
    check_env,
    check_deps,
    check_reddit,
    check_llm,
    preflight,
)


class TestCheckEnv:
    def test_all_set(self, monkeypatch):
        for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]:
            monkeypatch.setenv(key, "x")
        ok, missing = check_env(["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"])
        assert ok is True
        assert missing == []

    def test_missing(self, monkeypatch):
        for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]:
            monkeypatch.delenv(key, raising=False)
        ok, missing = check_env(["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"])
        assert ok is False
        assert missing == ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]


class TestCheckDeps:
    def test_installed(self):
        ok, failed = check_deps(["json", "os"])
        assert ok is True
        assert failed == []

    def test_missing(self):
        ok, failed = check_deps(["not_a_real_package_12345"])
        assert ok is False
        assert failed == ["not_a_real_package_12345"]


class TestCheckReddit:
    def test_ok(self, monkeypatch):
        class FakeMe:
            name = "test"

        class FakeUser:
            def me(self):
                return FakeMe()

        class FakeReddit:
            user = FakeUser()

        monkeypatch.setattr(praw, "Reddit", lambda **_: FakeReddit())
        ok, message = check_reddit("id", "secret", "agent")
        assert ok is True
        assert "authenticated" in message

    def test_auth_fails(self, monkeypatch):
        def boom(**_):
            raise Exception("401")

        monkeypatch.setattr(praw, "Reddit", boom)
        ok, message = check_reddit("id", "secret", "agent")
        assert ok is False
        assert "401" in message


class TestCheckLlm:
    def test_bad_base_url(self):
        ok, message = check_llm("key", "https://api.openai.com", "model")
        assert ok is False
        assert "/v1" in message

    def test_ok(self, monkeypatch):
        from types import SimpleNamespace

        fake_message = SimpleNamespace(content="ok")
        fake_choice = SimpleNamespace(message=fake_message)
        fake_response = SimpleNamespace(choices=[fake_choice])

        class FakeCompletions:
            def create(self, **kwargs):
                return fake_response

        class FakeChat:
            completions = FakeCompletions()

        class FakeOpenAI:
            def __init__(self, **kwargs):
                pass

            chat = FakeChat()

        monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
        ok, message = check_llm("key", "https://api.openai.com/v1", "model")
        assert ok is True
        assert message == ""


class TestPreflight:
    def test_returns_json_and_ok(self, monkeypatch, capsys):
        for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]:
            monkeypatch.setenv(key, "x")
        monkeypatch.setattr("scripts.preflight.check_reddit", lambda *_: (True, ""))
        monkeypatch.setattr("scripts.preflight.check_llm", lambda *_: (True, ""))
        result = preflight()
        assert result["env_ok"] is True
        assert result["deps_ok"] is True
        assert result["reddit_ok"] is True
        assert result["llm_ok"] is True
