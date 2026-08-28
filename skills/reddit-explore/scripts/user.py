import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.client import get_fetcher
from pipeline.explorer import get_user
from pipeline.paths import records_dir


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Fetch a Reddit user profile.")
    parser.add_argument("name", help="Reddit username.")
    parser.add_argument("--section", default="overview", choices=["overview", "posts", "comments"])
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", default="new", choices=["new", "hot", "top"])
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    fetcher = None
    try:
        fetcher = get_fetcher()
        records = get_user(
            args.name,
            fetcher=fetcher,
            section=args.section,
            limit=args.limit,
            sort=args.sort,
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "fetch_error"}))
        return 1
    finally:
        if fetcher is not None:
            fetcher.close()

    out_path = Path(args.out) if args.out else records_dir() / f"user_{args.name}_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "count": len(records), "records_path": str(out_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
