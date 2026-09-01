"""Plan state persistence for resume support."""

import json

from .paths import orchestrator_dir


def state_path(plan_id):
    """Return the state file path for a given plan_id."""
    return orchestrator_dir() / f"{plan_id}.json"


def save_state(plan_id, state):
    """Save plan execution state to disk."""
    path = state_path(plan_id)
    path.write_text(json.dumps(state, indent=2, default=str))
    return path


def load_state(plan_id):
    """Load plan execution state from disk. Returns None if not found."""
    path = state_path(plan_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())
