import json

import pytest

from pipeline.runner import run
from pipeline.config import get_profile


def test_run_emits_events_and_writes_log(tmp_path):
    log_path = tmp_path / "run.jsonl"

    records = [{"title": "post", "text": "hello"}]

    def fake_scrape(idea, profile):
        return records

    def fake_analyze(records, idea, profile):
        return {
            "score": 72,
            "pain_points": [{"text": "pain", "weight": 1}],
            "opportunities": [{"text": "opportunity", "weight": 1}],
            "recommendations": ["go"],
            "existing_solutions": ["x"],
            "comment_tags": {},
        }

    def fake_report(analysis, idea, run_id, profile):
        return str(tmp_path / "report.html")

    events = list(
        run(
            "test idea",
            "standard",
            log_path=log_path,
            scrape_fn=fake_scrape,
            analyze_fn=fake_analyze,
            report_fn=fake_report,
        )
    )

    assert events[0]["event"] == "run_started"
    assert events[0]["idea"] == "test idea"
    assert events[0]["profile"] == "standard"
    assert any(e["event"] == "stage" and e["step"] == "scrape_data" for e in events)
    assert any(e["event"] == "stage" and e["step"] == "analyze" for e in events)
    assert any(e["event"] == "stage" and e["step"] == "report" for e in events)
    done = [e for e in events if e["event"] == "done"][0]
    assert done["success"] is True
    assert done["score"] == 72
    assert "report_path" in done
    assert "run_id" in done

    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == len(events)
    assert json.loads(lines[0])["event"] == "run_started"


def test_run_fails_gracefully(tmp_path):
    log_path = tmp_path / "run.jsonl"

    def boom(*_):
        raise RuntimeError("scrape down")

    events = list(
        run(
            "test idea",
            "fast",
            log_path=log_path,
            scrape_fn=boom,
        )
    )

    done = [e for e in events if e["event"] == "done"][0]
    assert done["success"] is False
    assert "scrape down" in done["error"]
    assert "failed_step" in done
