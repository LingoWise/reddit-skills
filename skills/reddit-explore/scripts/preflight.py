import importlib
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


REQUIRED_DEPS = [
    "dotenv",
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


def preflight():
    deps_ok, missing_deps = check_deps()

    reddit_ok = False
    reddit_message = "dependencies missing"
    if deps_ok:
        auth = _load_auth()
        reddit_ok, reddit_message = auth.validate_credentials()

    result = {
        "env_ok": True,
        "deps_ok": deps_ok,
        "reddit_ok": reddit_ok,
    }
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not reddit_ok:
        result["reddit_error"] = reddit_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if result["deps_ok"] and result["reddit_ok"] else 1)
