import json
import sys
import io
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.runner import (
    resolve_placeholders,
    evaluate_condition,
    topological_sort,
    execute,
)


class TestTopologicalSort:
    def test_simple_linear(self):
        steps = [
            {"name": "a", "depends_on": []},
            {"name": "b", "depends_on": ["a"]},
            {"name": "c", "depends_on": ["b"]},
        ]
        ordered = topological_sort(steps)
        names = [s["name"] for s in ordered]
        assert names == ["a", "b", "c"]

    def test_parallel_branches(self):
        steps = [
            {"name": "a", "depends_on": []},
            {"name": "b", "depends_on": ["a"]},
            {"name": "c", "depends_on": ["a"]},
            {"name": "d", "depends_on": ["b", "c"]},
        ]
        ordered = topological_sort(steps)
        names = [s["name"] for s in ordered]
        assert names.index("a") < names.index("b")
        assert names.index("a") < names.index("c")
        assert names.index("b") < names.index("d")
        assert names.index("c") < names.index("d")

    def test_no_dependencies(self):
        steps = [
            {"name": "x", "depends_on": []},
            {"name": "y", "depends_on": []},
        ]
        ordered = topological_sort(steps)
        assert len(ordered) == 2

    def test_cycle_raises(self):
        steps = [
            {"name": "a", "depends_on": ["b"]},
            {"name": "b", "depends_on": ["a"]},
        ]
        with pytest.raises(ValueError, match="cycle"):
            topological_sort(steps)


class TestResolvePlaceholders:
    def test_resolves_step_output_reference(self):
        command = ["python", "script.py", "{scrape.records_path}"]
        outputs = {"scrape": {"records_path": "/tmp/records.json", "success": True}}
        resolved = resolve_placeholders(command, outputs, {})
        assert resolved == ["python", "script.py", "/tmp/records.json"]

    def test_resolves_param_reference(self):
        command = ["python", "script.py", "{idea}"]
        resolved = resolve_placeholders(command, {}, {"idea": "AI tutor"})
        assert resolved == ["python", "script.py", "AI tutor"]

    def test_step_output_takes_priority_over_param(self):
        command = ["python", "script.py", "{scrape.records_path}"]
        outputs = {"scrape": {"records_path": "/tmp/out.json"}}
        resolved = resolve_placeholders(command, outputs, {"scrape": "should not use this"})
        assert "/tmp/out.json" in resolved

    def test_unresolved_placeholder_left_as_is(self):
        command = ["python", "script.py", "{unknown.thing}"]
        resolved = resolve_placeholders(command, {}, {})
        assert "{unknown.thing}" in resolved

    def test_multiple_placeholders(self):
        command = ["python", "script.py", "{a.path}", "--out", "{b.out}"]
        outputs = {
            "a": {"path": "/tmp/a.json"},
            "b": {"out": "/tmp/b.json"},
        }
        resolved = resolve_placeholders(command, outputs, {})
        assert resolved == ["python", "script.py", "/tmp/a.json", "--out", "/tmp/b.json"]


class TestEvaluateCondition:
    def test_true_condition(self):
        outputs = {"scrape": {"success": True}}
        assert evaluate_condition("scrape.success == true", outputs) is True

    def test_false_condition(self):
        outputs = {"scrape": {"success": False}}
        assert evaluate_condition("scrape.success == true", outputs) is False

    def test_null_condition_returns_true(self):
        assert evaluate_condition(None, {}) is True

    def test_neq_condition(self):
        outputs = {"step": {"status": "failed"}}
        assert evaluate_condition("step.status != success", outputs) is True

    def test_and_condition(self):
        outputs = {"a": {"success": True}, "b": {"success": True}}
        assert evaluate_condition("a.success == true and b.success == true", outputs) is True

    def test_and_condition_false(self):
        outputs = {"a": {"success": True}, "b": {"success": False}}
        assert evaluate_condition("a.success == true and b.success == true", outputs) is False

    def test_or_condition(self):
        outputs = {"a": {"success": False}, "b": {"success": True}}
        assert evaluate_condition("a.success == true or b.success == true", outputs) is True

    def test_missing_step_in_condition(self):
        assert evaluate_condition("missing.success == true", {}) is False


class TestExecute:
    def test_dry_run_emits_events_without_executing(self):
        plan = {
            "plan_id": "test-1",
            "workflow": "test",
            "request": "test request",
            "steps": [
                {
                    "name": "step1",
                    "skill": "test",
                    "description": "test step",
                    "command": ["echo", "hello"],
                    "depends_on": [],
                    "output_key": "step1",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan, dry_run=True))
        event_types = [e["event"] for e in events]
        assert "plan_started" in event_types
        assert "step_started" in event_types
        assert "step_done" in event_types
        assert "plan_done" in event_types
        done = next(e for e in events if e["event"] == "step_done")
        assert done["success"] is True

    def test_execute_real_subprocess(self):
        plan = {
            "plan_id": "test-2",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "echo_step",
                    "skill": "test",
                    "description": "echo test",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True, \"data\": \"hello\"}))"],
                    "depends_on": [],
                    "output_key": "echo_step",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan))
        done = next(e for e in events if e["event"] == "step_done")
        assert done["success"] is True
        assert done["output"]["data"] == "hello"

    def test_execute_with_dependency(self):
        plan = {
            "plan_id": "test-3",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "first",
                    "skill": "test",
                    "description": "first step",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True, \"path\": \"/tmp/out.json\"}))"],
                    "depends_on": [],
                    "output_key": "first",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
                {
                    "name": "second",
                    "skill": "test",
                    "description": "second step uses first output",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True, \"received\": \"{first.path}\"}))"],
                    "depends_on": ["first"],
                    "output_key": "second",
                    "condition": "first.success == true",
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan))
        second_done = next(e for e in events if e["event"] == "step_done" and e["step"] == "second")
        assert second_done["success"] is True
        assert "/tmp/out.json" in second_done["output"]["received"]

    def test_condition_false_skips_step(self):
        plan = {
            "plan_id": "test-4",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "first",
                    "skill": "test",
                    "description": "fails",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": False}))"],
                    "depends_on": [],
                    "output_key": "first",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
                {
                    "name": "second",
                    "skill": "test",
                    "description": "should be skipped",
                    "command": ["echo", "should not run"],
                    "depends_on": ["first"],
                    "output_key": "second",
                    "condition": "first.success == true",
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan))
        skipped = [e for e in events if e["event"] == "step_skipped"]
        assert len(skipped) == 1
        assert skipped[0]["step"] == "second"

    def test_retry_on_failure(self):
        plan = {
            "plan_id": "test-5",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "fail_step",
                    "skill": "test",
                    "description": "always fails",
                    "command": ["python", "-c", "import sys; sys.exit(1)"],
                    "depends_on": [],
                    "output_key": "fail_step",
                    "condition": None,
                    "retry": {"max_attempts": 2, "delay_seconds": 0},
                    "checkpoint": False,
                },
            ],
        }
        events = list(execute(plan))
        failed = next(e for e in events if e["event"] == "step_failed")
        assert failed["attempts"] == 2
        plan_done = next(e for e in events if e["event"] == "plan_done")
        assert plan_done["steps_failed"] == 1

    def test_checkpoint_pause_and_resume(self):
        plan = {
            "plan_id": "test-6",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "checkpoint_step",
                    "skill": "test",
                    "description": "has checkpoint",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True}))"],
                    "depends_on": [],
                    "output_key": "checkpoint_step",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": True,
                },
            ],
        }
        stdin_input = io.StringIO(json.dumps({"action": "resume"}) + "\n")
        events = list(execute(plan, stdin_input=stdin_input))
        checkpoint_events = [e for e in events if e["event"] == "checkpoint"]
        assert len(checkpoint_events) == 1
        done = next(e for e in events if e["event"] == "step_done")
        assert done["success"] is True

    def test_checkpoint_skip(self):
        plan = {
            "plan_id": "test-7",
            "workflow": "test",
            "request": "test",
            "steps": [
                {
                    "name": "checkpoint_step",
                    "skill": "test",
                    "description": "has checkpoint",
                    "command": ["python", "-c", "import json; print(json.dumps({\"success\": True}))"],
                    "depends_on": [],
                    "output_key": "checkpoint_step",
                    "condition": None,
                    "retry": {"max_attempts": 1, "delay_seconds": 0},
                    "checkpoint": True,
                },
            ],
        }
        stdin_input = io.StringIO(json.dumps({"action": "skip"}) + "\n")
        events = list(execute(plan, stdin_input=stdin_input))
        skipped = [e for e in events if e["event"] == "step_skipped"]
        assert len(skipped) == 1
        assert skipped[0]["step"] == "checkpoint_step"
