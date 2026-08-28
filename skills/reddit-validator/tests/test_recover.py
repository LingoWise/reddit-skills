import json

import pytest

from scripts.recover import main


def test_recover_list(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.recover.logs_dir", lambda: tmp_path)
    monkeypatch.setattr("scripts.recover.checkpoints_dir", lambda: tmp_path / "checkpoints")
    (tmp_path / "run_1.jsonl").write_text("\n")
    main(["--list"])
    out = json.loads(capsys.readouterr().out)
    assert len(out["runs"]) == 1


def test_recover_resume_last(capsys, monkeypatch, tmp_path):
    log_path = tmp_path / "run_2026.jsonl"
    log_path.write_text(json.dumps({"event": "run_started", "run_id": "r1", "idea": "x", "profile": "fast"}) + "\n")
    monkeypatch.setattr("scripts.recover.logs_dir", lambda: tmp_path)
    monkeypatch.setattr("scripts.recover.checkpoints_dir", lambda: tmp_path / "checkpoints")

    def fake_run(idea, profile, log_path=None, run_id=None):
        yield {"event": "run_started", "run_id": run_id, "idea": idea, "profile": profile}
        yield {"event": "done", "success": True, "run_id": run_id}

    monkeypatch.setattr("scripts.recover.run", fake_run)
    main(["--resume-last", "--idea", "x", "--profile", "fast"])
    lines = capsys.readouterr().out.strip().split("\n")
    assert json.loads(lines[0])["event"] == "run_started"
    assert json.loads(lines[-1])["event"] == "done"
