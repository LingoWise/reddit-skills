import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.paths import orchestrator_dir
from pipeline.planner import plan as generate_plan
from pipeline.runner import execute


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Execute a Reddit orchestrator plan")
    parser.add_argument("--plan", default=None, help="Path to a plan JSON file")
    parser.add_argument("--request", default=None, help="Plan and run in one step")
    parser.add_argument("--workflow", default=None, help="Force a specific workflow (with --request)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--resume", default=None, help="Resume from a checkpoint (plan ID)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    state = None

    if args.resume:
        from pipeline.state import load_state
        state = load_state(args.resume)
        if state is None:
            print(json.dumps({"error": f"No saved state for plan {args.resume}"}))
            return 1
        plan_path = orchestrator_dir() / f"{args.resume}.plan.json"
        if not plan_path.exists():
            print(json.dumps({"error": f"No plan file for plan {args.resume}"}))
            return 1
        plan = json.loads(plan_path.read_text())
    elif args.request:
        plan = generate_plan(args.request, workflow=args.workflow)
        if "error" in plan:
            print(json.dumps(plan))
            return 1
    elif args.plan:
        plan = json.loads(Path(args.plan).read_text())
    else:
        print(json.dumps({"error": "Either --plan or --request is required"}))
        return 1

    # Save plan to disk for potential --resume
    plan_id = plan.get("plan_id", "unknown")
    plan_path = orchestrator_dir() / f"{plan_id}.plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, default=str))

    for event in execute(plan, dry_run=args.dry_run, state=state):
        print(json.dumps(event))
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
