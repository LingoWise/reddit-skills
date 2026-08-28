import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.paths import logs_dir, checkpoints_dir
from pipeline.runner import run


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Recover and inspect pipeline runs.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all runs and checkpoints.")
    group.add_argument("--show", default=None, help="Show events for a run id.")
    group.add_argument("--resume-last", action="store_true", help="Resume the most recent run.")
    parser.add_argument("--idea", default=None, help="Idea to use for resume.")
    parser.add_argument("--profile", default="standard", help="Profile to use for resume.")
    return parser.parse_args(argv)


def _runs():
    return sorted(logs_dir().glob("run_*.jsonl"), key=os.path.getmtime, reverse=True)


def _log_for_run_id(run_id):
    for p in _runs():
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") == "run_started" and event.get("run_id") == run_id:
                return p
    return None


def _read_log(log_path):
    events = []
    for line in log_path.read_text().splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def main(argv=None):
    args = parse_args(argv)
    if args.list:
        result = {
            "runs": [str(p) for p in _runs()],
            "checkpoints": [str(p) for p in checkpoints_dir().glob("*.json")],
        }
        print(json.dumps(result, indent=2))
        return 0

    if args.show:
        log_path = _log_for_run_id(args.show)
        if not log_path:
            print(json.dumps({"error": f"run {args.show} not found"}))
            return 1
        events = _read_log(log_path)
        print(json.dumps({"run_id": args.show, "events": events}, indent=2))
        return 0

    if args.resume_last:
        if not args.idea:
            print(json.dumps({"error": "--idea is required for --resume-last"}))
            return 1
        logs = _runs()
        if not logs:
            print(json.dumps({"error": "no runs found"}))
            return 1
        latest = logs[0]
        run_id = None
        for line in latest.read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") == "run_started":
                run_id = event.get("run_id")
                break
        if not run_id:
            print(json.dumps({"error": "no run_started event in latest log"}))
            return 1

        resume_log = latest.parent / f"run_{run_id}_resume.jsonl"
        for event in run(args.idea, args.profile, log_path=resume_log, run_id=run_id):
            print(json.dumps(event))
            with open(resume_log, "a") as f:
                f.write(json.dumps(event) + "\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
