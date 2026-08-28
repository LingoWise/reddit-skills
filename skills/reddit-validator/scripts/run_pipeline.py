import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.runner import run


def _ask_profile():
    """Prompt for a profile when running interactively without --profile."""
    if not sys.stdin.isatty():
        return "standard"
    print("Choose a profile:", file=sys.stderr)
    print("  1. fast     ~5 min, 3 subreddits x 5 posts", file=sys.stderr)
    print("  2. standard ~30 min, 5 subreddits x 25 posts", file=sys.stderr)
    print("  3. deep     ~60 min, 10 subreddits x 100 posts", file=sys.stderr)
    choice = input("Profile [1/2/3, default 2]: ").strip() or "2"
    mapping = {"1": "fast", "2": "standard", "3": "deep"}
    return mapping.get(choice, "standard")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Scrape Reddit for idea validation.")
    parser.add_argument("idea", help="The idea or niche to validate.")
    parser.add_argument("--profile", default=None, choices=["fast", "standard", "deep"], help="Pipeline profile.")
    parser.add_argument("--log", default=None, help="Path to the JSONL log file.")
    parser.add_argument("--run-id", default=None, help="Run ID (optional).")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    profile = args.profile or _ask_profile()
    log_path = Path(args.log) if args.log else None

    for event in run(args.idea, profile, log_path=log_path, run_id=args.run_id, analyze_fn=None, report_fn=None):
        print(json.dumps(event))

    if event["event"] == "done" and event.get("success"):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
