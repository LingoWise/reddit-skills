import json
import sys
import io
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run import main


def test_run_with_plan_file(tmp_path, capsys):
    plan = {
        "plan_id": "test-run-1",
        "workflow": "test",
        "request": "test",
        "steps": [
            {
                "name": "echo",
                "skill": "test",
                "description": "echo",
                "command": ["python", "-c", "import json; print(json.dumps({\"success\": True}))"],
                "depends_on": [],
                "output_key": "echo",
                "condition": None,
                "retry": {"max_attempts": 1, "delay_seconds": 0},
                "checkpoint": False,
            },
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    code = main(["--plan", str(plan_path)])
    assert code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    events = [json.loads(l) for l in lines]
    assert events[0]["event"] == "plan_started"
    assert any(e["event"] == "step_done" for e in events)
    assert events[-1]["event"] == "plan_done"
    assert events[-1]["success"] is True


def test_run_dry_run(tmp_path, capsys):
    plan = {
        "plan_id": "test-run-2",
        "workflow": "test",
        "request": "test",
        "steps": [
            {
                "name": "echo",
                "skill": "test",
                "description": "echo",
                "command": ["echo", "hello"],
                "depends_on": [],
                "output_key": "echo",
                "condition": None,
                "retry": {"max_attempts": 1, "delay_seconds": 0},
                "checkpoint": False,
            },
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    code = main(["--plan", str(plan_path), "--dry-run"])
    assert code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    events = [json.loads(l) for l in lines]
    done = next(e for e in events if e["event"] == "step_done")
    assert done["output"]["dry_run"] is True


def test_run_with_request(capsys):
    code = main(["--request", "validate my idea: test idea", "--dry-run"])
    assert code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    events = [json.loads(l) for l in lines]
    assert events[0]["event"] == "plan_started"
    assert events[0]["workflow"] == "validate_idea"
