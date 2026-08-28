import importlib
import json
import os
import sys
from pathlib import Path


REQUIRED_ENV = [
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USER_AGENT",
]

REQUIRED_DEPS = [
    "playwright",
    "openai",
    "dotenv",
    "praw",
    "jinja2",
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


def check_reddit(client_id, client_secret, user_agent):
    try:
        from praw import Reddit
        reddit = Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        _ = reddit.user.me()
        return True, ""
    except ImportError:
        return False, "praw not installed"
    except Exception as exc:
        return False, f"Reddit auth failed: {exc}"


def check_llm(api_key, base_url, model):
    if not base_url.rstrip("/").endswith("/v1"):
        return False, f"OPENAI_BASE_URL must end with /v1: {base_url}"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1,
        )
        return True, ""
    except ImportError:
        return False, "openai not installed"
    except Exception as exc:
        return False, f"LLM call failed: {exc}"


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

    llm_ok = False
    llm_message = "Missing LLM credentials"
    if env_ok and deps_ok:
        llm_ok, llm_message = check_llm(
            os.getenv("OPENAI_API_KEY"),
            os.getenv("OPENAI_BASE_URL"),
            os.getenv("OPENAI_MODEL"),
        )

    result = {
        "env_ok": env_ok,
        "deps_ok": deps_ok,
        "reddit_ok": reddit_ok,
        "llm_ok": llm_ok,
    }
    if not env_ok:
        result["missing"] = missing_env
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not reddit_ok:
        result["reddit_error"] = reddit_message
    if not llm_ok:
        result["llm_error"] = llm_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if all(result[k] for k in ["env_ok", "deps_ok", "reddit_ok", "llm_ok"]) else 1)
