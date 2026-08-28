import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.auth import preflight


def main():
    result = preflight()
    print(json.dumps(result))
    return 0 if all(result[k] for k in ["env_ok", "deps_ok", "reddit_ok"]) else 1


if __name__ == "__main__":
    sys.exit(main())
