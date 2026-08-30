# reddit-interact Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the reddit-interact skill with five core actions (comment, reply, upvote, downvote, save) that interact with Reddit's JSON API through an authenticated browser session.

**Architecture:** One `Interactor` pipeline class mirrors `Publisher` from reddit-publish, using `page.evaluate` to POST to Reddit's JSON API with modhash. Six scripts (preflight + 5 action scripts) follow the explore pattern of independent CLI entrypoints. All outputs go to `.reddit-skills/records/`.

**Tech Stack:** Python 3.10+, Rustwright (browser automation), Reddit JSON API

## Global Constraints

- Python 3.10+ required.
- Dependencies: `requests`, `python-dotenv`, `praw`, `rustwright` (same as reddit-explore).
- Auth is handled by `reddit-auth` skill — loaded via `importlib.util.spec_from_file_location`.
- All runtime outputs go to `.reddit-skills/` (via `src/common/paths.py`).
- Scripts print a single JSON line: `{"event": "done", "success": true/false, ...}`.
- Tests use FakePage/FakeSession pattern from `test_publisher.py`.
- No LLM dependencies — agent provides comment/reply text directly.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `skills/reddit-interact/SKILL.md` | Skill contract: purpose, prerequisites, workflow, operating principles |
| `skills/reddit-interact/requirements.txt` | Python dependencies |
| `skills/reddit-interact/.env.example` | Environment variable template |
| `skills/reddit-interact/.markdownlint.json` | Markdownlint config (MD013/MD060 disabled) |
| `skills/reddit-interact/pipeline/__init__.py` | Empty package init |
| `skills/reddit-interact/pipeline/paths.py` | Load `src/common/paths.py`, expose `skill_dir()` and `records_dir()` |
| `skills/reddit-interact/pipeline/interactor.py` | `Interactor` class with comment/reply/vote/save/unsave methods + thing ID normalization |
| `skills/reddit-interact/scripts/__init__.py` | Empty package init |
| `skills/reddit-interact/scripts/preflight.py` | Deps + auth validation |
| `skills/reddit-interact/scripts/comment.py` | Comment on a post |
| `skills/reddit-interact/scripts/reply.py` | Reply to a comment |
| `skills/reddit-interact/scripts/upvote.py` | Upvote a post or comment |
| `skills/reddit-interact/scripts/downvote.py` | Downvote a post or comment |
| `skills/reddit-interact/scripts/save.py` | Save/unsave a post or comment |
| `skills/reddit-interact/tests/__init__.py` | Empty package init |
| `skills/reddit-interact/tests/test_interactor.py` | Unit tests for Interactor methods + ID normalization |
| `skills/reddit-interact/tests/test_preflight.py` | Preflight deps check test |
| `skills/reddit-interact/tests/test_scripts_comment.py` | Dry-run path test for comment.py |
| `skills/reddit-interact/tests/test_scripts_reply.py` | Dry-run path test for reply.py |
| `skills/reddit-interact/tests/test_scripts_vote.py` | Dry-run path tests for upvote.py and downvote.py |
| `skills/reddit-interact/tests/test_scripts_save.py` | Dry-run path test for save.py |
| `skills/reddit-interact/resources/.gitkeep` | Keep resources dir in git |
| `skills/reddit-interact/resources/CLAUDE.md` | Claude Code runtime guide |
| `skills/reddit-interact/resources/DEVIN.md` | Devin runtime guide |
| `skills/reddit-interact/resources/failure-recovery.md` | Error code table |

---

### Task 1: Scaffolding (paths, requirements, config files)

**Files:**
- Create: `skills/reddit-interact/pipeline/__init__.py`
- Create: `skills/reddit-interact/pipeline/paths.py`
- Create: `skills/reddit-interact/scripts/__init__.py`
- Create: `skills/reddit-interact/tests/__init__.py`
- Create: `skills/reddit-interact/requirements.txt`
- Create: `skills/reddit-interact/.env.example`
- Create: `skills/reddit-interact/.markdownlint.json`
- Create: `skills/reddit-interact/resources/.gitkeep`

**Interfaces:**
- Produces: `pipeline.paths.records_dir()` → `Path` (used by all scripts for output)
- Produces: `pipeline.paths.skill_dir()` → `Path`

- [ ] **Step 1: Create empty init files and .gitkeep**

Create these four files as empty:

```python
# skills/reddit-interact/pipeline/__init__.py
```

```python
# skills/reddit-interact/scripts/__init__.py
```

```python
# skills/reddit-interact/tests/__init__.py
```

```text
# skills/reddit-interact/resources/.gitkeep
```

- [ ] **Step 2: Create `pipeline/paths.py`**

```python
import importlib.util
from pathlib import Path


def _load_common_paths():
    paths_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "paths.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_paths", paths_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_common = _load_common_paths()


def skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def records_dir() -> Path:
    return _common.records_dir()
```

- [ ] **Step 3: Create `requirements.txt`**

```text
requests
python-dotenv
praw
rustwright
```

- [ ] **Step 4: Create `.env.example`**

```text
# Authentication method (optional; defaults to browser if no API creds present):
# - rustwright | playwright | browser: open a real Chromium window for manual login
# - token: paste a base64 Reddit token JSON in REDDIT_CLIENT_SECRET
# - praw: use a script app client_id / client_secret / username / password
REDDIT_LOGIN_METHOD=rustwright

# Optional: for token/praw methods
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=script:reddit-interact:v0.1 (by /u/your_username)

# Optional: for PRAW script apps only
REDDIT_USERNAME=
REDDIT_PASSWORD=
```

- [ ] **Step 5: Create `.markdownlint.json`**

```json
{
  "MD013": false,
  "MD060": false
}
```

- [ ] **Step 6: Verify paths module loads**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -c "import sys; sys.path.insert(0, 'skills/reddit-interact'); from pipeline.paths import records_dir, skill_dir; print(records_dir()); print(skill_dir())"
```

Expected: prints two paths without error.

- [ ] **Step 7: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add skills/reddit-interact/pipeline/__init__.py skills/reddit-interact/pipeline/paths.py skills/reddit-interact/scripts/__init__.py skills/reddit-interact/tests/__init__.py skills/reddit-interact/requirements.txt skills/reddit-interact/.env.example skills/reddit-interact/.markdownlint.json skills/reddit-interact/resources/.gitkeep && git commit -m "feat(reddit-interact): scaffold directory structure and config files"
```

---

### Task 2: Interactor pipeline with thing ID normalization

**Files:**
- Create: `skills/reddit-interact/pipeline/interactor.py`
- Test: `skills/reddit-interact/tests/test_interactor.py`

**Interfaces:**
- Consumes: `reddit-auth/pipeline/auth.py` → `ensure_authenticated_page(headless)` returns `Session` with `.page` and `.close()`
- Produces: `Interactor(session)` class with methods: `create()`, `comment(thing_id, text)`, `reply(comment_id, text)`, `vote(thing_id, direction)`, `save(thing_id)`, `unsave(thing_id)`, `close()`
- Produces: `normalize_thing_id(value, kind)` → `str` (kind is `"post"` or `"comment"`)

- [ ] **Step 1: Write the failing test**

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import interactor


def test_normalize_post_id_from_url():
    assert interactor.normalize_thing_id(
        "https://www.reddit.com/r/test/comments/abc123/title_here/", "post"
    ) == "t3_abc123"


def test_normalize_post_id_from_permalink():
    assert interactor.normalize_thing_id("/r/test/comments/abc123/title/", "post") == "t3_abc123"


def test_normalize_post_id_bare():
    assert interactor.normalize_thing_id("abc123", "post") == "t3_abc123"


def test_normalize_post_id_already_prefixed():
    assert interactor.normalize_thing_id("t3_abc123", "post") == "t3_abc123"


def test_normalize_comment_id_from_url():
    assert interactor.normalize_thing_id(
        "https://www.reddit.com/r/test/comments/abc123/title/def456/", "comment"
    ) == "t1_def456"


def test_normalize_comment_id_bare():
    assert interactor.normalize_thing_id("def456", "comment") == "t1_def456"


def test_normalize_comment_id_already_prefixed():
    assert interactor.normalize_thing_id("t1_def456", "comment") == "t1_def456"


def test_comment(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200,
                    "body": '{"json": {"data": {"things": [{"data": {"id": "c1", "permalink": "/r/test/comments/abc/title/c1"}}]}}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.comment("t3_abc", "Hello world")
    assert result["comment_id"] == "c1"
    assert "permalink" in result


def test_reply(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200,
                    "body": '{"json": {"data": {"things": [{"data": {"id": "c2", "permalink": "/r/test/comments/abc/title/c2"}}]}}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.reply("t1_c1", "Reply text")
    assert result["comment_id"] == "c2"


def test_vote(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200, "body": '{"json": {}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.vote("t3_abc", 1)
    assert result["action"] == "vote"
    assert result["direction"] == 1


def test_save(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200, "body": '{"json": {}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.save("t3_abc")
    assert result["action"] == "save"
    assert result["thing_id"] == "t3_abc"


def test_unsave(monkeypatch):
    class FakePage:
        def evaluate(self, script, arg=None):
            url = arg[0] if isinstance(arg, list) else ""
            if "/api/v1/me.json" in url:
                return {"ok": True, "status": 200, "body": '{"name": "testuser", "modhash": "abc"}'}
            return {"ok": True, "status": 200, "body": '{"json": {}}'}

    class FakeSession:
        page = FakePage()

        def close(self):
            pass

    i = interactor.Interactor(FakeSession())
    result = i.unsave("t3_abc")
    assert result["action"] == "unsave"
    assert result["thing_id"] == "t3_abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_interactor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.interactor'`

- [ ] **Step 3: Write minimal implementation**

```python
import importlib.util
import json
import time
import urllib.parse
from pathlib import Path


PUBLIC_BASE = "https://www.reddit.com"


def _load_auth():
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def normalize_thing_id(value: str, kind: str) -> str:
    """Normalize a URL, permalink, or bare ID into a Reddit fullname.

    kind is "post" (→ t3_) or "comment" (→ t1_).
    """
    value = value.strip()
    prefix = "t3_" if kind == "post" else "t1_"

    if value.startswith(prefix):
        return value

    if value.startswith("http") or value.startswith("/r/"):
        parts = [p for p in value.split("/") if p]
        if "comments" in parts:
            idx = parts.index("comments")
            if kind == "post" and idx + 1 < len(parts):
                return f"t3_{parts[idx + 1]}"
            if kind == "comment" and idx + 2 < len(parts):
                return f"t1_{parts[idx + 2]}"

    return f"{prefix}{value}"


class Interactor:
    def __init__(self, session):
        self._session = session
        self._modhash = None

    @classmethod
    def create(cls, headless: bool = False):
        auth = _load_auth()
        session = auth.ensure_authenticated_page(headless=headless)
        return cls(session)

    def _fetch_modhash(self):
        page = self._session.page
        result = page.evaluate(
            """
            async ([url, timeout_ms]) => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), timeout_ms);
                try {
                    const res = await fetch(url, { signal: controller.signal, credentials: 'include' });
                    const text = await res.text();
                    return {ok: res.ok, status: res.status, body: text};
                } catch (err) {
                    return {ok: false, error: err.toString()};
                } finally {
                    clearTimeout(timer);
                }
            }
            """,
            [f"{PUBLIC_BASE}/api/v1/me.json", 10000],
        )
        if not result.get("ok"):
            raise RuntimeError(f"Could not fetch user profile: {result}")
        data = json.loads(result["body"])
        me = data.get("data", data)
        self._modhash = me.get("modhash") or ""
        if not me.get("name"):
            raise RuntimeError("Not logged in")

    def _post_json(self, path: str, payload: dict) -> dict:
        if self._modhash is None:
            self._fetch_modhash()

        body = urllib.parse.urlencode({**payload, "api_type": "json", "uh": self._modhash})
        page = self._session.page

        time.sleep(0.5)
        result = page.evaluate(
            """
            async ([url, body, timeout_ms]) => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), timeout_ms);
                try {
                    const res = await fetch(url, {
                        method: 'POST',
                        signal: controller.signal,
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        body,
                    });
                    const text = await res.text();
                    return {ok: res.ok, status: res.status, body: text};
                } catch (err) {
                    return {ok: false, error: err.toString()};
                } finally {
                    clearTimeout(timer);
                }
            }
            """,
            [f"{PUBLIC_BASE}{path}", body, 30000],
        )
        if not result.get("ok"):
            raise RuntimeError(f"Reddit POST failed: {result.get('status')} {result.get('body', '')[:200]}")
        return json.loads(result["body"])

    def comment(self, thing_id: str, text: str) -> dict:
        data = self._post_json("/api/comment", {"thing_id": thing_id, "text": text})
        things = data.get("json", {}).get("data", {}).get("things", [])
        if not things:
            errors = data.get("json", {}).get("errors", [])
            if errors:
                raise RuntimeError(f"Reddit rejected comment: {errors}")
            raise RuntimeError("Comment returned no things")
        comment_data = things[0].get("data", {})
        return {
            "comment_id": comment_data.get("id", ""),
            "permalink": comment_data.get("permalink", ""),
        }

    def reply(self, comment_id: str, text: str) -> dict:
        return self.comment(comment_id, text)

    def vote(self, thing_id: str, direction: int) -> dict:
        self._post_json("/api/vote", {"id": thing_id, "dir": str(direction)})
        return {"action": "vote", "thing_id": thing_id, "direction": direction}

    def save(self, thing_id: str) -> dict:
        self._post_json("/api/save", {"id": thing_id})
        return {"action": "save", "thing_id": thing_id}

    def unsave(self, thing_id: str) -> dict:
        self._post_json("/api/unsave", {"id": thing_id})
        return {"action": "unsave", "thing_id": thing_id}

    def close(self) -> None:
        if self._session:
            self._session.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_interactor.py -v
```

Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add skills/reddit-interact/pipeline/interactor.py skills/reddit-interact/tests/test_interactor.py && git commit -m "feat(reddit-interact): add Interactor pipeline with comment/reply/vote/save/unsave"
```

---

### Task 3: Preflight script

**Files:**
- Create: `skills/reddit-interact/scripts/preflight.py`
- Test: `skills/reddit-interact/tests/test_preflight.py`

**Interfaces:**
- Consumes: `reddit-auth/pipeline/auth.py` → `validate_credentials()` returns `(bool, str)`
- Produces: `preflight.preflight()` → `dict` with `deps_ok`, `reddit_ok` keys

- [ ] **Step 1: Write the failing test**

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import preflight


class FakeAuth:
    def validate_credentials(self):
        return True, "ok"


def test_preflight_ok(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "_load_auth", lambda: FakeAuth())
    result = preflight.preflight()
    assert result["deps_ok"] is True
    assert result["reddit_ok"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_preflight.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.preflight'`

- [ ] **Step 3: Write minimal implementation**

```python
import importlib
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


REQUIRED_DEPS = [
    "dotenv",
    "requests",
    "rustwright",
    "praw",
]


def _load_auth():
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    auth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth)
    return auth


def check_deps(dependency_names=None):
    if dependency_names is None:
        dependency_names = REQUIRED_DEPS
    failed = []
    for name in dependency_names:
        try:
            importlib.import_module(name)
        except ImportError:
            failed.append(name)
    return (len(failed) == 0, failed)


def preflight():
    deps_ok, missing_deps = check_deps()

    reddit_ok = False
    reddit_message = "dependencies missing"
    if deps_ok:
        auth = _load_auth()
        reddit_ok, reddit_message = auth.validate_credentials()

    result = {
        "env_ok": True,
        "deps_ok": deps_ok,
        "reddit_ok": reddit_ok,
    }
    if not deps_ok:
        result["missing_deps"] = missing_deps
    if not reddit_ok:
        result["reddit_error"] = reddit_message

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    result = preflight()
    sys.exit(0 if result["deps_ok"] and result["reddit_ok"] else 1)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_preflight.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add skills/reddit-interact/scripts/preflight.py skills/reddit-interact/tests/test_preflight.py && git commit -m "feat(reddit-interact): add preflight script"
```

---

### Task 4: Comment script

**Files:**
- Create: `skills/reddit-interact/scripts/comment.py`
- Test: `skills/reddit-interact/tests/test_scripts_comment.py`

**Interfaces:**
- Consumes: `pipeline.interactor.Interactor` → `comment(thing_id, text)` returns `{"comment_id", "permalink"}`
- Consumes: `pipeline.interactor.normalize_thing_id(value, kind)` → `str`
- Consumes: `pipeline.paths.records_dir()` → `Path`

- [ ] **Step 1: Write the failing test**

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import comment


def test_comment_dry_run(capsys):
    code = comment.main(["t3_abc", "--text", "Hello", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "comment"


def test_comment_text_file(tmp_path, capsys):
    text_file = tmp_path / "comment.txt"
    text_file.write_text("From file body")
    code = comment.main(["t3_abc", "--text-file", str(text_file), "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["text"] == "From file body"


def test_comment_missing_text(capsys):
    code = comment.main(["t3_abc", "--dry-run"])
    assert code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["code"] == "text_missing"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_scripts_comment.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.comment'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_scripts_comment.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add skills/reddit-interact/scripts/comment.py skills/reddit-interact/tests/test_scripts_comment.py && git commit -m "feat(reddit-interact): add comment script"
```

---

### Task 5: Reply script

**Files:**
- Create: `skills/reddit-interact/scripts/reply.py`
- Test: `skills/reddit-interact/tests/test_scripts_reply.py`

**Interfaces:**
- Consumes: `pipeline.interactor.Interactor` → `reply(comment_id, text)` returns `{"comment_id", "permalink"}`
- Consumes: `pipeline.interactor.normalize_thing_id(value, kind)` with `kind="comment"`

- [ ] **Step 1: Write the failing test**

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import reply


def test_reply_dry_run(capsys):
    code = reply.main(["t1_c1", "--text", "Reply body", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "reply"


def test_reply_text_file(tmp_path, capsys):
    text_file = tmp_path / "reply.txt"
    text_file.write_text("Reply from file")
    code = reply.main(["t1_c1", "--text-file", str(text_file), "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["text"] == "Reply from file"


def test_reply_missing_text(capsys):
    code = reply.main(["t1_c1", "--dry-run"])
    assert code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["code"] == "text_missing"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_scripts_reply.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.reply'`

- [ ] **Step 3: Write minimal implementation**

```python
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.interactor import Interactor, normalize_thing_id
from pipeline.paths import records_dir


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Reply to a Reddit comment.")
    parser.add_argument("comment_url_or_id", help="Comment URL, permalink, or ID.")
    parser.add_argument("--text", default=None, help="Reply text.")
    parser.add_argument("--text-file", default=None, help="Read reply text from file (overrides --text).")
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

    thing_id = normalize_thing_id(args.comment_url_or_id, "comment")

    if args.dry_run:
        print(json.dumps({"event": "done", "success": True, "dry_run": True, "action": "reply", "thing_id": thing_id, "text": text}))
        return 0

    interactor = None
    try:
        interactor = Interactor.create()
        result = interactor.reply(thing_id, text)
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "interact_error"}))
        return 1
    finally:
        if interactor:
            interactor.close()

    out_path = Path(args.out) if args.out else records_dir() / f"reply_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_scripts_reply.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add skills/reddit-interact/scripts/reply.py skills/reddit-interact/tests/test_scripts_reply.py && git commit -m "feat(reddit-interact): add reply script"
```

---

### Task 6: Upvote and downvote scripts

**Files:**
- Create: `skills/reddit-interact/scripts/upvote.py`
- Create: `skills/reddit-interact/scripts/downvote.py`
- Test: `skills/reddit-interact/tests/test_scripts_vote.py`

**Interfaces:**
- Consumes: `pipeline.interactor.Interactor` → `vote(thing_id, direction)` returns `{"action", "thing_id", "direction"}`
- Consumes: `pipeline.interactor.normalize_thing_id(value, kind)` — auto-detects kind from URL

- [ ] **Step 1: Write the failing test**

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import upvote, downvote


def test_upvote_dry_run(capsys):
    code = upvote.main(["t3_abc", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "upvote"


def test_downvote_dry_run(capsys):
    code = downvote.main(["t3_abc", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "downvote"


def test_upvote_dry_run_comment(capsys):
    code = upvote.main(["t1_c1", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["thing_id"] == "t1_c1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_scripts_vote.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.upvote'`

- [ ] **Step 3: Write `upvote.py`**

```python
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
        if idx + 2 < len(parts):
            return "comment"
    return "post"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Upvote a Reddit post or comment.")
    parser.add_argument("url_or_id", help="Post/comment URL, permalink, or ID.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    kind = _detect_kind(args.url_or_id)
    thing_id = normalize_thing_id(args.url_or_id, kind)

    if args.dry_run:
        print(json.dumps({"event": "done", "success": True, "dry_run": True, "action": "upvote", "thing_id": thing_id}))
        return 0

    interactor = None
    try:
        interactor = Interactor.create()
        result = interactor.vote(thing_id, 1)
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "interact_error"}))
        return 1
    finally:
        if interactor:
            interactor.close()

    out_path = Path(args.out) if args.out else records_dir() / f"upvote_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Write `downvote.py`**

```python
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
        if idx + 2 < len(parts):
            return "comment"
    return "post"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Downvote a Reddit post or comment.")
    parser.add_argument("url_or_id", help="Post/comment URL, permalink, or ID.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    kind = _detect_kind(args.url_or_id)
    thing_id = normalize_thing_id(args.url_or_id, kind)

    if args.dry_run:
        print(json.dumps({"event": "done", "success": True, "dry_run": True, "action": "downvote", "thing_id": thing_id}))
        return 0

    interactor = None
    try:
        interactor = Interactor.create()
        result = interactor.vote(thing_id, -1)
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "interact_error"}))
        return 1
    finally:
        if interactor:
            interactor.close()

    out_path = Path(args.out) if args.out else records_dir() / f"downvote_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_scripts_vote.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add skills/reddit-interact/scripts/upvote.py skills/reddit-interact/scripts/downvote.py skills/reddit-interact/tests/test_scripts_vote.py && git commit -m "feat(reddit-interact): add upvote and downvote scripts"
```

---

### Task 7: Save script

**Files:**
- Create: `skills/reddit-interact/scripts/save.py`
- Test: `skills/reddit-interact/tests/test_scripts_save.py`

**Interfaces:**
- Consumes: `pipeline.interactor.Interactor` → `save(thing_id)` and `unsave(thing_id)` return `{"action", "thing_id"}`
- Consumes: `pipeline.interactor.normalize_thing_id(value, kind)` — auto-detects kind from URL

- [ ] **Step 1: Write the failing test**

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import save


def test_save_dry_run(capsys):
    code = save.main(["t3_abc", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "save"


def test_unsave_dry_run(capsys):
    code = save.main(["t3_abc", "--unsave", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "unsave"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_scripts_save.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.save'`

- [ ] **Step 3: Write minimal implementation**

```python
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
        if idx + 2 < len(parts):
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/tests/test_scripts_save.py -v
```

Expected: all 2 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add skills/reddit-interact/scripts/save.py skills/reddit-interact/tests/test_scripts_save.py && git commit -m "feat(reddit-interact): add save script with --unsave flag"
```

---

### Task 8: SKILL.md and resources

**Files:**
- Create: `skills/reddit-interact/SKILL.md`
- Create: `skills/reddit-interact/resources/CLAUDE.md`
- Create: `skills/reddit-interact/resources/DEVIN.md`
- Create: `skills/reddit-interact/resources/failure-recovery.md`

**Interfaces:**
- No code interfaces — documentation only

- [ ] **Step 1: Create `SKILL.md`**

```markdown
---
name: reddit-interact
description: Use when the user wants to interact with Reddit content — comment on posts, reply to comments, upvote, downvote, or save posts and comments.
---

# Reddit Interact

Interact with Reddit content: comment on posts, reply to comments, upvote, downvote, and save posts or comments.

## When to use

- "comment on this post"
- "reply to this comment"
- "upvote this post"
- "downvote that comment"
- "save this post for later"

## When NOT to use

- Publishing content (→ `reddit-publish`).
- Browsing or searching Reddit (→ `reddit-explore`).
- Validating a business idea (→ `reddit-validator`).
- Compound operations like trend tracking (→ `reddit-content-ops`, once it exists).

## Prerequisites

- Python 3.10+.
- Dependencies installed: `uv pip install -r skills/reddit-interact/requirements.txt`.
- Reddit authentication via `reddit-auth`.

## Workflow

1. Preflight: `python "skills/reddit-interact/scripts/preflight.py"`
2. Pick an action and run the matching script:
   - Comment: `python "skills/reddit-interact/scripts/comment.py" "<post_url_or_id>" --text "Your comment"`
   - Reply: `python "skills/reddit-interact/scripts/reply.py" "<comment_url_or_id>" --text "Your reply"`
   - Upvote: `python "skills/reddit-interact/scripts/upvote.py" "<url_or_id>"`
   - Downvote: `python "skills/reddit-interact/scripts/downvote.py" "<url_or_id>"`
   - Save: `python "skills/reddit-interact/scripts/save.py" "<url_or_id>"`
3. Read the `done` JSON event.

## Operating principles

- Always run preflight first.
- Use `--dry-run` before the first real action in a session.
- For long comments, use `--text-file` instead of `--text`.
- Respect Reddit rate limits; do not bulk vote or comment.
- `save.py --unsave` reverses a save.
```

- [ ] **Step 2: Create `resources/CLAUDE.md`**

```markdown
# Claude Code Runtime Guide for reddit-interact

## Phase 1 — Preflight

Run with the `Bash` tool:

```bash
python "skills/reddit-interact/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true.

## Phase 2 — Pick an action

### Comment on a post

```bash
python "skills/reddit-interact/scripts/comment.py" "<post_url_or_id>" --text "Your comment" --dry-run
python "skills/reddit-interact/scripts/comment.py" "<post_url_or_id>" --text "Your comment"
```

### Reply to a comment

```bash
python "skills/reddit-interact/scripts/reply.py" "<comment_url_or_id>" --text "Your reply" --dry-run
python "skills/reddit-interact/scripts/reply.py" "<comment_url_or_id>" --text "Your reply"
```

### Upvote

```bash
python "skills/reddit-interact/scripts/upvote.py" "<url_or_id>" --dry-run
python "skills/reddit-interact/scripts/upvote.py" "<url_or_id>"
```

### Downvote

```bash
python "skills/reddit-interact/scripts/downvote.py" "<url_or_id>" --dry-run
python "skills/reddit-interact/scripts/downvote.py" "<url_or_id>"
```

### Save

```bash
python "skills/reddit-interact/scripts/save.py" "<url_or_id>" --dry-run
python "skills/reddit-interact/scripts/save.py" "<url_or_id>"
```

### Unsave

```bash
python "skills/reddit-interact/scripts/save.py" "<url_or_id>" --unsave
```

## Phase 3 — Read output

The `Bash` tool returns a single JSON line:

```json
{"event": "done", "success": true, "comment_id": "abc", "permalink": "/r/test/..."}
```

If `success` is false, read `error` and `code`, then check `resources/failure-recovery.md`.

## Phase 4 — Surface results

Report the action result to the user. Do not dump full JSON.
```

- [ ] **Step 3: Create `resources/DEVIN.md`**

```markdown
# Devin Runtime Guide for reddit-interact

## Phase 1 — Preflight

Run:

```bash
python "skills/reddit-interact/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true.

## Phase 2 — Pick an action

### Comment on a post

```bash
python "skills/reddit-interact/scripts/comment.py" "<post_url_or_id>" --text "Your comment"
```

For long comments, use `--text-file path/to/comment.txt` instead of `--text`.

### Reply to a comment

```bash
python "skills/reddit-interact/scripts/reply.py" "<comment_url_or_id>" --text "Your reply"
```

### Upvote

```bash
python "skills/reddit-interact/scripts/upvote.py" "<url_or_id>"
```

### Downvote

```bash
python "skills/reddit-interact/scripts/downvote.py" "<url_or_id>"
```

### Save / Unsave

```bash
python "skills/reddit-interact/scripts/save.py" "<url_or_id>"
python "skills/reddit-interact/scripts/save.py" "<url_or_id>" --unsave
```

## Phase 3 — Read output

Each script prints a single JSON line:

```json
{"event": "done", "success": true, "action": "upvote", "thing_id": "t3_abc"}
```

If `success` is false, read `error` and `code`.

## Phase 4 — Surface results

Report the action result to the user. Do not dump full JSON.
```

- [ ] **Step 4: Create `resources/failure-recovery.md`**

```markdown
# Failure recovery

| Error / symptom | Likely cause | Fix |
| --- | --- | --- |
| `deps_ok: false` | Missing Python packages | `uv pip install -r skills/reddit-interact/requirements.txt` |
| `reddit_ok: false` | Stale session or missing credentials | Re-run `reddit-auth/scripts/login.py` or check `.env` |
| `code: interact_error` | Reddit rejected the action (deleted content, permissions, rate limit) | Check the error message; wait and retry if rate limited |
| `code: text_missing` | Neither `--text` nor `--text-file` provided | Provide text via one of the flags |
| `code: auth_failure` | Browser session expired | Re-run `reddit-auth/scripts/login.py` |
```

- [ ] **Step 5: Lint markdown files**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills/skills/reddit-interact && npx markdownlint-cli SKILL.md resources/*.md
```

Expected: no errors (warnings for MD013/MD060 are disabled by `.markdownlint.json`)

- [ ] **Step 6: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add skills/reddit-interact/SKILL.md skills/reddit-interact/resources/CLAUDE.md skills/reddit-interact/resources/DEVIN.md skills/reddit-interact/resources/failure-recovery.md && git commit -m "feat(reddit-interact): add SKILL.md and resource guides"
```

---

### Task 9: Update README and run full test suite

**Files:**
- Modify: `README.md:31` (update reddit-interact row in skill catalog table)

**Interfaces:**
- No code interfaces — documentation update

- [ ] **Step 1: Update README skill catalog**

In `README.md`, change the reddit-interact row from:

```markdown
| reddit-interact | Planned | Social interaction | Comment, reply, upvote, downvote, save |
```

to:

```markdown
| reddit-interact | Complete | Social interaction | Comment, reply, upvote, downvote, save |
```

Also update line 34 from:

```markdown
The four completed skills are runnable today. `reddit-interact` and `reddit-content-ops` are reserved stubs.
```

to:

```markdown
The five completed skills are runnable today. `reddit-content-ops` is a reserved stub.
```

And add interact entrypoints to the per-skill entrypoints section after the reddit-publish block:

```bash
# reddit-interact — comment, reply, vote, save
python skills/reddit-interact/scripts/preflight.py
python skills/reddit-interact/scripts/comment.py "<post_url_or_id>" --text "..."
python skills/reddit-interact/scripts/reply.py "<comment_url_or_id>" --text "..."
python skills/reddit-interact/scripts/upvote.py "<url_or_id>"
python skills/reddit-interact/scripts/downvote.py "<url_or_id>"
python skills/reddit-interact/scripts/save.py "<url_or_id>"
```

- [ ] **Step 2: Run full test suite**

Run:

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && python -m pytest skills/reddit-interact/ -v
```

Expected: all tests PASS (12 interactor + 1 preflight + 3 comment + 3 reply + 3 vote + 2 save = 24 tests)

- [ ] **Step 3: Commit**

```bash
cd /Users/chenillen/Codes/Projects/Lingo/reddit-skills && git add README.md && git commit -m "docs: mark reddit-interact as complete in README"
```
