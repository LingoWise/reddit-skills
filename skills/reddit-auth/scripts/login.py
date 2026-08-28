import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.auth import ensure_authenticated_page, default_session_path


def main():
    session_path = default_session_path()
    try:
        session = ensure_authenticated_page()
        session.close()
        result = {
            "success": True,
            "username": session.username,
            "session_path": str(session.session_path or session_path),
        }
        print(json.dumps(result))
        return 0
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
