import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.client import get_fetcher
from pipeline.explorer import list_subreddit
from pipeline.paths import records_dir


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Browse a subreddit.")
    parser.add_argument("name", help="Subreddit name (without r/).")
    parser.add_argument("--sort", default="hot", choices=["hot", "new", "top", "rising"])
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--t", default="all", choices=["all", "day", "week", "month", "year"])
    parser.add_argument("--comments", type=int, default=0, help="Top comments per post (0=skip).")
    parser.add_argument("--comment-sort", default="top", choices=["top", "best", "new", "controversial"])
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    fetcher = None
    try:
        fetcher = get_fetcher()
        records = list_subreddit(
            args.name,
            fetcher=fetcher,
            sort=args.sort,
            limit=args.limit,
            time_filter=args.t,
            fetch_comments=args.comments > 0,
            comment_limit=args.comments,
            comment_sort=args.comment_sort,
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "fetch_error"}))
        return 1
    finally:
        if fetcher is not None:
            fetcher.close()

    out_path = Path(args.out) if args.out else records_dir() / f"subreddit_{args.name}_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "count": len(records), "records_path": str(out_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
