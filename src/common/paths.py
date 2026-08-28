"""Shared constants and path helpers for all reddit-skills.

Defines the default output directory and the project version. All skills
write their runtime outputs (reports, logs, checkpoints, records) under
``DEFAULT_OUTPUT_DIR`` instead of scattering them inside each skill folder.

The version is read from the ``VERSION`` file at the repo root, which is
the single source of truth for all skills in this monorepo.
"""

from pathlib import Path

# Repo root is 3 levels up from src/common/paths.py
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _read_version():
    """Read the version from the VERSION file at the repo root."""
    version_file = _REPO_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"


VERSION = _read_version()

# Default output root: .reddit-skills/ in the current working directory.
# This keeps generated artifacts out of the skill source tree and the git repo.
DEFAULT_OUTPUT_DIR = Path.cwd() / ".reddit-skills"

# Subdirectory names under the output root.
REPORTS_SUBDIR = "reports"
LOGS_SUBDIR = "logs"
CHECKPOINTS_SUBDIR = "checkpoints"
RECORDS_SUBDIR = "records"


def output_root() -> Path:
    """Return the root output directory, creating it if needed."""
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR


def reports_dir() -> Path:
    path = output_root() / REPORTS_SUBDIR
    path.mkdir(exist_ok=True)
    return path


def logs_dir() -> Path:
    path = output_root() / LOGS_SUBDIR
    path.mkdir(exist_ok=True)
    return path


def checkpoints_dir() -> Path:
    path = output_root() / CHECKPOINTS_SUBDIR
    path.mkdir(exist_ok=True)
    return path


def records_dir() -> Path:
    path = output_root() / RECORDS_SUBDIR
    path.mkdir(exist_ok=True)
    return path
