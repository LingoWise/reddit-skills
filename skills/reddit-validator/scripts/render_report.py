import argparse
import json
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.paths import logs_dir, reports_dir
from pipeline.report import render


def _latest_log():
    log_files = sorted(logs_dir().glob("run_*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        raise FileNotFoundError("No run logs found.")
    return log_files[0]


def _log_for_run_id(run_id):
    for path in logs_dir().glob("run_*.jsonl"):
        text = path.read_text()
        if run_id in text:
            return path
    raise FileNotFoundError(f"No log found for run {run_id}")


def _parse_event(line):
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _extract_records_path(log_path):
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        event = _parse_event(line)
        if not event:
            continue
        if event.get("event") == "done" and event.get("needs_analysis"):
            return event.get("records_path")
    return None


def _safe_idea(idea):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in idea).strip("_")[:50]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render the validation HTML report.")
    parser.add_argument("--analysis", required=True, help="Path to the analysis JSON file.")
    parser.add_argument("--run-id", default=None, help="Run ID to link to a previous scrape run.")
    parser.add_argument("--log", default=None, help="Path to the scrape JSONL log.")
    parser.add_argument("--idea", default=None, help="Idea to use on the report.")
    parser.add_argument("--language", default=None, help="Language code for the report (e.g. en, zh). Defaults to analysis JSON or en.")
    parser.add_argument("--no-open", action="store_true", help="Do not auto-open the report in the browser.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    analysis = json.loads(Path(args.analysis).read_text())

    if args.log:
        log_path = Path(args.log)
    elif args.run_id:
        log_path = _log_for_run_id(args.run_id)
    else:
        log_path = _latest_log()

    records_path = _extract_records_path(log_path)
    run_id = args.run_id
    if not run_id:
        for line in log_path.read_text().splitlines():
            if not line.strip():
                continue
            event = _parse_event(line)
            if not event:
                continue
            if event.get("event") == "run_started":
                run_id = event.get("run_id")
                break

    idea = args.idea
    if not idea:
        for line in log_path.read_text().splitlines():
            if not line.strip():
                continue
            event = _parse_event(line)
            if not event:
                continue
            if event.get("event") == "run_started":
                idea = event.get("idea", "unknown")
                break

    records = None
    if records_path:
        rp = Path(records_path)
        if rp.exists():
            records = json.loads(rp.read_text())

    language = args.language or analysis.get("language", "en")
    report_path = render(analysis, idea, run_id, {}, records=records, language=language)

    done_event = {
        "event": "done",
        "success": True,
        "run_id": run_id,
        "idea": idea,
        "report_path": report_path,
        "score": analysis.get("score", 0),
        "market_snapshot": analysis.get("market_snapshot", [])[:5],
        "pain_points": analysis.get("pain_points", [])[:3],
        "opportunities": analysis.get("opportunities", [])[:3],
        "how_to_win": analysis.get("how_to_win", [])[:3],
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(done_event) + "\n")

    if not args.no_open:
        webbrowser.open(f"file://{report_path}")

    print(json.dumps({
        "report_path": report_path,
        "score": analysis.get("score", 0),
        "run_id": run_id,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
