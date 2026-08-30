import importlib.util
from pathlib import Path


def _load_common_paths():
    paths_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "paths.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_paths", paths_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_common = _load_common_paths()


def skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def records_dir() -> Path:
    return _common.records_dir()
