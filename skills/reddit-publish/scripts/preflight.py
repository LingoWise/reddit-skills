import importlib
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


REQUIRED_DEPS = ["dotenv", "requests", "rustwright", "praw", "openai"]


def _load_auth():
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_llm():
    llm_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "llm.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_llm", llm_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def check_ai():
    llm = _load_llm()
    return llm.available()


def check_image():
    if not os.getenv("OPENAI_API_KEY"):
        return False, "OPENAI_API_KEY is required for image generation"
    try:
        import openai
        return True, "openai package available"
    except ImportError:
        return False, "openai package not installed"


def preflight():
    deps_ok, missing_deps = check_deps()

    reddit_ok = False
    reddit_message = "dependencies missing"
    if deps_ok:
        auth = _load_auth()
        reddit_ok, reddit_message = auth.validate_credentials()

    ai_ok, ai_message = (False, "")
    image_ok, image_message = (False, "")
    if deps_ok:
        ai_ok, ai_message = check_ai()
        image_ok, image_message = check_image()

    result = {
        "env_ok": True,
        "deps_ok": deps_ok,
        "reddit_ok": reddit_ok,
        "ai_ok": ai_ok,
        "image_ok": image_ok,
    }
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not reddit_ok:
        result["reddit_error"] = reddit_message
    if not ai_ok:
        result["ai_error"] = ai_message
    if not image_ok:
        result["image_error"] = image_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if all(result[k] for k in ["deps_ok", "reddit_ok"]) else 1)
