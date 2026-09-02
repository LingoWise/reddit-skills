import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.planner import plan as generate_plan


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Plan a Reddit orchestrator workflow")
    parser.add_argument("request", nargs="?", help="The user's request text")
    parser.add_argument("--workflow", default=None, help="Force a specific workflow")
    parser.add_argument("--out", default=None, help="Write plan to file instead of stdout")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.request:
        print(json.dumps({"error": "No request provided. Usage: plan.py \"your request\" [--workflow name] [--out file]"}))
        return 1

    result = generate_plan(args.request, workflow=args.workflow)

    if "error" in result:
        print(json.dumps(result))
        return 1

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, default=str))
    else:
        print(json.dumps(result, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
