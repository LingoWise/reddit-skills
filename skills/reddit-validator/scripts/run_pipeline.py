import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.runner import run


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Scrape Reddit for idea validation.")
    parser.add_argument("idea", help="The idea or niche to validate.")
    parser.add_argument("--profile", default="standard", choices=["fast", "standard", "deep"], help="Pipeline profile.")
    parser.add_argument("--log", default=None, help="Path to the JSONL log file.")
    parser.add_argument("--run-id", default=None, help="Run ID (optional).")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    log_path = Path(args.log) if args.log else None

    for event in run(args.idea, args.profile, log_path=log_path, run_id=args.run_id, analyze_fn=None, report_fn=None):
        print(json.dumps(event))

    if event["event"] == "done" and event.get("success"):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
