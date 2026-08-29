import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import paths
from pipeline.publisher import Publisher


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Publish a drafted Reddit post.")
    parser.add_argument("draft_json", help="Path to draft JSON.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    draft = json.loads(Path(args.draft_json).read_text())

    if args.dry_run:
        print(json.dumps({"event": "done", "success": True, "dry_run": True, "draft": draft}))
        return 0

    publisher = None
    try:
        publisher = Publisher.create()
        result = publisher.publish(
            subreddit=draft["subreddit"],
            title=draft["title"],
            kind=draft["kind"],
            body=draft.get("body"),
            url=draft.get("url"),
            image_path=draft.get("image_path"),
            nsfw=draft.get("nsfw", False),
            spoiler=draft.get("spoiler", False),
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "publish_error"}))
        return 1
    finally:
        if publisher:
            publisher.close()

    out_path = Path(args.out) if args.out else paths.drafts_dir() / f"publish_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
