import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.interactor import Interactor, normalize_thing_id
from pipeline.paths import records_dir


def _detect_kind(value: str) -> str:
    value = value.strip()
    if value.startswith("t1_"):
        return "comment"
    if value.startswith("t3_"):
        return "post"
    parts = [p for p in value.split("/") if p]
    if "comments" in parts:
        idx = parts.index("comments")
        if idx + 3 < len(parts):
            return "comment"
    return "post"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Save or unsave a Reddit post or comment.")
    parser.add_argument("url_or_id", help="Post/comment URL, permalink, or ID.")
    parser.add_argument("--unsave", action="store_true", help="Unsave instead of save.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    kind = _detect_kind(args.url_or_id)
    thing_id = normalize_thing_id(args.url_or_id, kind)
    action = "unsave" if args.unsave else "save"

    if args.dry_run:
        print(json.dumps({"event": "done", "success": True, "dry_run": True, "action": action, "thing_id": thing_id}))
        return 0

    interactor = None
    try:
        interactor = Interactor.create()
        if args.unsave:
            result = interactor.unsave(thing_id)
        else:
            result = interactor.save(thing_id)
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "interact_error"}))
        return 1
    finally:
        if interactor:
            interactor.close()

    out_path = Path(args.out) if args.out else records_dir() / f"save_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
