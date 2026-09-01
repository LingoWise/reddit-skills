import importlib
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.skill_catalog import SKILLS
from pipeline.paths import skill_dir


REQUIRED_ENV = []

REQUIRED_DEPS = [
    "dotenv",
]


def _load_auth():
    auth_path = skill_dir().parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    auth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth)
    return auth


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


def _check_skill_dirs():
    """Check that all skill directories exist."""
    root = skill_dir().parent
    missing = []
    for skill in SKILLS:
        skill_path = root / skill["name"]
        if not skill_path.is_dir():
            missing.append(skill["name"])
    return (len(missing) == 0, missing)


def preflight():
    env_ok, missing_env = check_env()
    deps_ok, missing_deps = check_deps()
    skills_ok, missing_skills = _check_skill_dirs()

    reddit_ok = False
    reddit_message = "dependencies missing"
    if env_ok and deps_ok and skills_ok:
        auth = _load_auth()
        reddit_ok, reddit_message = auth.validate_credentials()

    result = {
        "env_ok": env_ok,
        "deps_ok": deps_ok,
        "skills_ok": skills_ok,
        "reddit_ok": reddit_ok,
    }
    if not env_ok:
        result["missing"] = missing_env
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not skills_ok:
        result["missing_skills"] = missing_skills
    if not reddit_ok:
        result["reddit_error"] = reddit_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if all(result[k] for k in ["env_ok", "deps_ok", "skills_ok", "reddit_ok"]) else 1)
