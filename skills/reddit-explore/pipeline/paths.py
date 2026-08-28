import importlib.util
from pathlib import Path


def _load_common_paths():
    """Load the shared paths module from src/common/."""
    paths_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "paths.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_paths", paths_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_common = _load_common_paths()


def skill_dir() -> Path:
    """Return the root directory of the reddit-explore skill."""
    return Path(__file__).resolve().parent.parent


def records_dir() -> Path:
    return _common.records_dir()
