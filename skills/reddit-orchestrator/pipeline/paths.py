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
    """Return the root directory of the reddit-orchestrator skill."""
    return Path(__file__).resolve().parent.parent


def orchestrator_dir() -> Path:
    """Return the orchestrator output directory under .reddit-skills/."""
    path = _common.output_root() / "orchestrator"
    path.mkdir(parents=True, exist_ok=True)
    return path


def records_dir() -> Path:
    return _common.records_dir()


def logs_dir() -> Path:
    return _common.logs_dir()


def checkpoints_dir() -> Path:
    return _common.checkpoints_dir()
