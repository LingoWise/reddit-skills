import importlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests


REQUIRED_ENV = []

REQUIRED_DEPS = [
    "dotenv",
    "jinja2",
    "requests",
]


def _load_dotenv():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def check_env(required=None):
    if required is None:
        required = REQUIRED_ENV
    missing = [key for key in required if not os.getenv(key)]
    return (len(missing) == 0, missing)


def check_deps(dependency_names=None):
    if dependency_names is None:
        dependency_names = REQUIRED_DEPS
    failed = []
    for name in dependency_names:
        try:
            importlib.import_module(name)
        except ImportError:
            failed.append(name)
    return (len(failed) == 0, failed)


def _has_reddit_creds(client_id, client_secret):
    client_id = (client_id or "").strip()
    client_secret = (client_secret or "").strip()
    if not client_id or not client_secret:
        return False
    if client_id == "your_reddit_app_client_id" or client_secret == "your_reddit_app_client_secret":
        return False
    return True


def _bearer_token(client_secret=None):
    try:
        from pipeline.scraper import _bearer_token as scraper_bearer
        return scraper_bearer(client_secret)
    except Exception:
        return None


def _use_playwright():
    try:
        from pipeline.scraper import _use_playwright as scraper_use
        return scraper_use()
    except Exception:
        return False


def check_reddit(client_id, client_secret, user_agent):
    if _use_playwright():
        try:
            importlib.import_module("playwright.sync_api")
            return True, "playwright login configured"
        except ImportError:
            return False, "playwright not installed"

    token = _bearer_token(client_secret)
    if token:
        try:
            response = requests.get(
                "https://oauth.reddit.com/r/all/search",
                headers={"Authorization": f"Bearer {token}", "User-Agent": user_agent or "python:reddit-validator:v0.1"},
                params={"q": "test", "limit": 1},
                timeout=15,
            )
            response.raise_for_status()
            return True, "bearer token works"
        except Exception as exc:
            return False, f"Bearer token failed: {exc}"

    if _has_reddit_creds(client_id, client_secret):
        try:
            from praw import Reddit
            kwargs = {
                "client_id": client_id,
                "client_secret": client_secret,
                "user_agent": user_agent,
            }
            username = os.getenv("REDDIT_USERNAME")
            password = os.getenv("REDDIT_PASSWORD")
            if username and password:
                kwargs["username"] = username
                kwargs["password"] = password
            reddit = Reddit(**kwargs)
            list(reddit.subreddit("all").search("test", limit=1))
            return True, "authenticated"
        except ImportError:
            return False, "praw not installed"
        except Exception as exc:
            return False, f"Reddit auth failed: {exc}"

    user_agent = user_agent or "python:reddit-validator:v0.1"
    try:
        response = requests.get(
            "https://www.reddit.com/search.json",
            headers={"User-Agent": user_agent},
            params={"q": "test", "limit": 1},
            timeout=15,
        )
        response.raise_for_status()
        return True, "public search works"
    except Exception as exc:
        return False, f"Public search failed: {exc}"


def preflight():
    _load_dotenv()
    env_ok, missing_env = check_env()
    deps_ok, missing_deps = check_deps()

    reddit_ok = False
    reddit_message = "Missing Reddit credentials"
    if env_ok and deps_ok:
        reddit_ok, reddit_message = check_reddit(
            os.getenv("REDDIT_CLIENT_ID"),
            os.getenv("REDDIT_CLIENT_SECRET"),
            os.getenv("REDDIT_USER_AGENT"),
        )

    result = {
        "env_ok": env_ok,
        "deps_ok": deps_ok,
        "reddit_ok": reddit_ok,
    }
    if not env_ok:
        result["missing"] = missing_env
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not reddit_ok:
        result["reddit_error"] = reddit_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if all(result[k] for k in ["env_ok", "deps_ok", "reddit_ok"]) else 1)
