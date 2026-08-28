from pathlib import Path


def skill_dir() -> Path:
    """Return the root directory of the reddit-validator skill."""
    return Path(__file__).resolve().parent.parent


def reports_dir() -> Path:
    path = skill_dir() / "reports"
    path.mkdir(exist_ok=True)
    return path


def checkpoints_dir() -> Path:
    path = skill_dir() / "checkpoints"
    path.mkdir(exist_ok=True)
    return path


def logs_dir() -> Path:
    path = skill_dir() / "logs"
    path.mkdir(exist_ok=True)
    return path


def latest_run_log() -> Path:
    return logs_dir() / "latest_run.jsonl"
