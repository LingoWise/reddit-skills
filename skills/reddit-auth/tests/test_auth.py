import base64
import importlib.util
import sys
from pathlib import Path

import pytest


_auth_path = Path(__file__).resolve().parent.parent / "pipeline" / "auth.py"
_spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", _auth_path)
_auth = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_auth)


class TestCredentialHygiene:
    def test_placeholder_client_id(self, monkeypatch):
        monkeypatch.setenv("REDDIT_LOGIN_METHOD", "praw")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "your_reddit_app_client_id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USERNAME", "user")
        monkeypatch.setenv("REDDIT_PASSWORD", "pass")
        ok, problems = _auth.credential_hygiene()
        assert ok is False
        assert any("placeholder" in p.lower() for p in problems)

    def test_valid_praw_creds(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "real_id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "real_secret")
        monkeypatch.setenv("REDDIT_USERNAME", "user")
        monkeypatch.setenv("REDDIT_PASSWORD", "pass")
        ok, problems = _auth.credential_hygiene()
        assert ok is True

    def test_bearer_token_parse(self, monkeypatch):
        payload = '{"accessToken": "abc123"}'
        secret = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", secret)
        assert _auth.bearer_token() == "abc123"


class TestResolveStrategy:
    def test_browser_method(self, monkeypatch):
        monkeypatch.setenv("REDDIT_LOGIN_METHOD", "rustwright")
        assert _auth.resolve_strategy() == "browser"

    def test_bearer_strategy(self, monkeypatch):
        payload = '{"accessToken": "abc123"}'
        secret = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", secret)
        monkeypatch.delenv("REDDIT_LOGIN_METHOD", raising=False)
        assert _auth.resolve_strategy() == "bearer"

    def test_praw_strategy(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "real_id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "real_secret")
        monkeypatch.delenv("REDDIT_LOGIN_METHOD", raising=False)
        assert _auth.resolve_strategy() == "praw"


class TestIsLoggedIn:
    def test_anonymous_me(self, monkeypatch):
        calls = []

        class FakePage:
            def evaluate(self, script, arg):
                calls.append(arg)
                return {"ok": True, "status": 200, "body": '{"features": {"x": true}}'}

        assert _auth.is_logged_in(FakePage()) is None
