import json

from scripts.extract_report import extract


def test_extract_prints_summary(tmp_path):
    log_path = tmp_path / "run.jsonl"
    log_path.write_text(json.dumps({"event": "run_started", "run_id": "r1"}) + "\n")
    with open(log_path, "a") as f:
        f.write(json.dumps({
            "event": "done",
            "success": True,
            "run_id": "r1",
            "report_path": str(tmp_path / "report.html"),
            "score": 72,
            "pain_points": [{"text": "pain A", "weight": 2}],
            "opportunities": [{"text": "op A", "weight": 1}],
        }) + "\n")

    result = extract(["--log", str(log_path)])
    assert result["score"] == 72
    assert result["run_id"] == "r1"
    assert result["top_pain_points"] == ["pain A"]
    assert result["top_opportunities"] == ["op A"]
