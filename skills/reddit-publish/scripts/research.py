import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import paths
from pipeline.researcher import research as researcher_research


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Research Reddit for post inspiration.")
    parser.add_argument("topic", help="The post topic.")
    parser.add_argument("--subreddit", default=None, help="Target subreddit.")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", default="top", choices=["top", "hot", "relevance", "new"])
    parser.add_argument("--time", default="month", choices=["day", "week", "month", "year", "all"], dest="time_filter")
    parser.add_argument("--suggest-subreddit", action="store_true")
    parser.add_argument("--language", default="en")
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = researcher_research(
            args.topic,
            subreddit=args.subreddit,
            limit=args.limit,
            sort=args.sort,
            time_filter=args.time_filter,
            suggest_subreddit=args.suggest_subreddit,
            language=args.language,
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "research_error"}))
        return 1

    out_path = Path(args.out) if args.out else paths.records_dir() / f"research_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "records_path": str(out_path), "subreddit": result.get("subreddit")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
