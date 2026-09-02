import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.plan import main


def test_plan_outputs_json_to_stdout(capsys):
    code = main(["validate my idea: test idea"])
    assert code == 0
    captured = capsys.readouterr()
    plan = json.loads(captured.out)
    assert plan["workflow"] == "validate_idea"
    assert "plan_id" in plan
    assert "steps" in plan


def test_plan_writes_to_file(tmp_path):
    out_path = tmp_path / "plan.json"
    code = main(["validate my idea: test idea", "--out", str(out_path)])
    assert code == 0
    plan = json.loads(out_path.read_text())
    assert plan["workflow"] == "validate_idea"


def test_plan_with_forced_workflow(capsys):
    code = main(["some text", "--workflow", "track_trends"])
    assert code == 0
    captured = capsys.readouterr()
    plan = json.loads(captured.out)
    assert plan["workflow"] == "track_trends"


def test_plan_error_returns_nonzero(capsys, monkeypatch):
    monkeypatch.setattr("pipeline.planner._llm_available", lambda: (False, "no key"))
    code = main(["what is the weather today?"])
    assert code != 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "error" in result
