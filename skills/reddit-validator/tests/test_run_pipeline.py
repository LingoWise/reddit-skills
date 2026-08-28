import json

import pytest

from scripts.run_pipeline import main


def test_main_runs_pipeline_and_prints_events(monkeypatch, capsys):
    def fake_run(idea, profile_name, **kwargs):
        yield {"event": "run_started", "run_id": "r1", "idea": idea, "profile": profile_name}
        yield {"event": "done", "success": True, "run_id": "r1", "report_path": "/tmp/report.html", "score": 72, "execution_time": 0.1}

    monkeypatch.setattr("scripts.run_pipeline.run", fake_run)
    main(["test idea", "--profile", "fast"])

    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    assert json.loads(lines[0])["event"] == "run_started"
    assert json.loads(lines[-1])["event"] == "done"
    assert json.loads(lines[-1])["score"] == 72
