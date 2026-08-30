import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.interactor import Interactor, normalize_thing_id
from pipeline.paths import records_dir


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Comment on a Reddit post.")
    parser.add_argument("post_url_or_id", help="Post URL, permalink, or ID.")
    parser.add_argument("--text", default=None, help="Comment text.")
    parser.add_argument("--text-file", default=None, help="Read comment text from file (overrides --text).")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)


def _resolve_text(args):
    if args.text_file:
        return Path(args.text_file).read_text()
    if args.text is not None:
        return args.text
    return None


def main(argv=None):
    args = parse_args(argv)
    text = _resolve_text(args)

    if text is None:
        print(json.dumps({"event": "done", "success": False, "code": "text_missing", "error": "Provide --text or --text-file"}))
        return 1

    thing_id = normalize_thing_id(args.post_url_or_id, "post")

    if args.dry_run:
        print(json.dumps({"event": "done", "success": True, "dry_run": True, "action": "comment", "thing_id": thing_id, "text": text}))
        return 0

    interactor = None
    try:
        interactor = Interactor.create()
        result = interactor.comment(thing_id, text)
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "interact_error"}))
        return 1
    finally:
        if interactor:
            interactor.close()

    out_path = Path(args.out) if args.out else records_dir() / f"comment_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
