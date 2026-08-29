import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import paths
from pipeline.drafter import draft as drafter_draft
from pipeline.imager import resolve_image


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Draft a Reddit post from research.")
    parser.add_argument("research_json", help="Path to research JSON.")
    parser.add_argument("--subreddit", default=None)
    parser.add_argument("--style", default="casual")
    parser.add_argument("--image-path", default=None)
    parser.add_argument("--image-url", default=None)
    parser.add_argument("--image-prompt", default=None)
    parser.add_argument("--link-url", default=None)
    parser.add_argument("--language", default=None)
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    research = json.loads(Path(args.research_json).read_text())

    topic = research.get("topic") or ""
    language = args.language or research.get("language", "en")

    try:
        d = drafter_draft(
            topic,
            research,
            subreddit=args.subreddit,
            style=args.style,
            image_path=args.image_path,
            image_url=args.image_url,
            image_prompt=args.image_prompt,
            link_url=args.link_url,
            language=language,
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "draft_error"}))
        return 1

    if d["kind"] == "image" and not d["image_path"]:
        try:
            img_path = resolve_image(
                image_path=args.image_path,
                image_url=args.image_url,
                image_prompt=d["image_prompt"],
            )
            d["image_path"] = str(img_path)
        except Exception as exc:
            print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "image_error"}))
            return 1

    out_path = Path(args.out) if args.out else paths.drafts_dir() / f"draft_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(d, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "draft_path": str(out_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
