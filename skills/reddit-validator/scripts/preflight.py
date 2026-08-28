import importlib
import importlib.util
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
    "rustwright",
    "praw",
]


def _load_auth():
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    auth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth)
    return auth


def _load_llm():
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    llm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llm)
    return llm


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


def check_reddit(client_id, client_secret, user_agent):
    auth = _load_auth()
    return auth.validate_credentials()


def check_ai():
    """Check whether an AI provider is available for analysis."""
    llm = _load_llm()
    return llm.available()


def preflight():
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

    ai_ok, ai_message = check_ai()

    result = {
        "env_ok": env_ok,
        "deps_ok": deps_ok,
        "reddit_ok": reddit_ok,
        "ai_ok": ai_ok,
    }
    if not env_ok:
        result["missing"] = missing_env
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not reddit_ok:
        result["reddit_error"] = reddit_message
    if not ai_ok:
        result["ai_error"] = ai_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if all(result[k] for k in ["env_ok", "deps_ok", "reddit_ok"]) else 1)
