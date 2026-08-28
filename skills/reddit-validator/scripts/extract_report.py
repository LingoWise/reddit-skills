import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.paths import logs_dir, reports_dir


def _interpretation(score):
    if score >= 75:
        return "strong"
    if score >= 50:
        return "promising"
    if score >= 30:
        return "weak"
    return "likely no-go"


def _latest_log():
    log_files = sorted(logs_dir().glob("run_*.jsonl"), key=os.path.getmtime, reverse=True)
    if not log_files:
        raise FileNotFoundError("No run logs found.")
    return log_files[0]


def _log_for_run_id(run_id):
    for path in logs_dir().glob("run_*.jsonl"):
        text = path.read_text()
        if run_id in text:
            return path
    raise FileNotFoundError(f"No log found for run {run_id}")


def _extract_done_event(log_path):
    done = None
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event") == "done":
            done = event
    if done is None:
        raise ValueError("No 'done' event found in log.")
    return done


def _safe_idea(idea):
    return re.sub(r"[^\w\-]+", "_", idea).strip("_")[:50]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Extract a summary from a run.")
    parser.add_argument("--run-id", default=None, help="Run ID to extract.")
    parser.add_argument("--log", default=None, help="Path to a JSONL log file.")
    return parser.parse_args(argv)


def extract(argv=None):
    args = parse_args(argv)
    if args.log:
        log_path = Path(args.log)
    elif args.run_id:
        log_path = _log_for_run_id(args.run_id)
    else:
        log_path = _latest_log()

    done = _extract_done_event(log_path)

    if done.get("needs_analysis"):
        summary = {
            "status": "needs_analysis",
            "message": "Use your agent's LLM to analyze the records and produce an analysis JSON, then run scripts/render_report.py.",
            "records_path": done.get("records_path"),
            "run_id": done.get("run_id"),
            "idea": done.get("idea"),
        }
        print(json.dumps(summary, indent=2))
        return summary

    if done.get("needs_report"):
        summary = {
            "status": "needs_report",
            "message": "Use your agent's LLM to produce an analysis JSON, then run scripts/render_report.py.",
            "analysis": done.get("analysis"),
            "records_path": done.get("records_path"),
            "run_id": done.get("run_id"),
            "idea": done.get("idea"),
        }
        print(json.dumps(summary, indent=2))
        return summary

    score = done.get("score", 0)
    market_snapshot = done.get("market_snapshot", [])[:5]
    pain_points = [p.get("text", "") for p in done.get("pain_points", [])[:3]]
    opportunities = [o.get("text", "") for o in done.get("opportunities", [])[:3]]
    how_to_win = done.get("how_to_win", [])[:3]
    report_path = done.get("report_path") or str(reports_dir() / f"{_safe_idea(done.get('idea', 'unknown'))}_{done.get('run_id')}.html")

    summary = {
        "score": score,
        "interpretation": _interpretation(score),
        "market_snapshot": market_snapshot,
        "top_pain_points": pain_points,
        "top_opportunities": opportunities,
        "how_to_win": how_to_win,
        "report_path": report_path,
        "run_id": done.get("run_id"),
    }
    print(json.dumps(summary, indent=2))
    return summary


def main(argv=None):
    extract(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
