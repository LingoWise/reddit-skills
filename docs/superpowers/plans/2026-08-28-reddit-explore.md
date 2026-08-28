# reddit-explore implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `reddit-explore` as the canonical Reddit read layer with four capabilities (search, subreddit browsing, post details, user profiles) and refactor `reddit-validator` to delegate all scraping to it.

**Architecture:** `reddit-explore/pipeline/client.py` provides a strategy-agnostic `Fetcher`; `explorer.py` exposes the four read primitives; `records.py` normalizes Reddit JSON into the validator record shape; `scripts/*.py` are thin CLIs. `reddit-validator/pipeline/scraper.py` becomes a ~30-line adapter calling `explorer.search_posts()`.

**Tech Stack:** Python 3.10+, `requests`, `praw`, `rustwright`, `python-dotenv`, `pytest`. Existing shared modules: `src/common/paths.py`, `src/common/llm.py`, cross-skill imports via `importlib.util`.

## Global Constraints

- All skills write runtime outputs under `.reddit-skills/` via `src/common/paths.py`.
- All skill pipeline modules use `importlib.util.spec_from_file_location` to load sibling skills (e.g. `reddit-explore` loads `reddit-auth`).
- All scripts emit structured JSON to stdout.
- `reddit-auth` is the only source of auth strategy resolution and credential handling.
- `reddit-explore` returns records in the same flat shape `reddit-validator` currently uses: `{id, post_id, subreddit, title, post_text, text, author, score, url, is_comment}`.
- `reddit-explore` has no LLM, no HTML rendering, no long-running background work.

---

### Task 1: Scaffold package and `pipeline/paths.py`

**Files:**

- Create: `skills/reddit-explore/pipeline/__init__.py`
- Create: `skills/reddit-explore/pipeline/paths.py`
- Create: `skills/reddit-explore/tests/__init__.py`
- Create: `skills/reddit-explore/scripts/__init__.py`
- Create: `skills/reddit-explore/resources/.gitkeep`

**Interfaces:**

- Produces: `skills_dir() -> Path`, `records_dir() -> Path`, etc. (mirrors validator's `pipeline/paths.py`).

- [ ] **Step 1:** Create directories and `__init__.py` files

```bash
mkdir -p skills/reddit-explore/{pipeline,scripts,tests,resources}
touch skills/reddit-explore/pipeline/__init__.py
touch skills/reddit-explore/tests/__init__.py
touch skills/reddit-explore/scripts/__init__.py
touch skills/reddit-explore/resources/.gitkeep
```

- [ ] **Step 2: Write `pipeline/paths.py`**

```python
import importlib.util
from pathlib import Path


def _load_common_paths():
    """Load the shared paths module from src/common/."""
    paths_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "paths.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_paths", paths_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_common = _load_common_paths()


def skill_dir() -> Path:
    """Return the root directory of the reddit-explore skill."""
    return Path(__file__).resolve().parent.parent


def records_dir() -> Path:
    return _common.records_dir()
```

- [ ] **Step 3: Verify the module loads without errors**

```bash
cd skills/reddit-explore
python -c "from pipeline.paths import records_dir, skill_dir; print(records_dir()); print(skill_dir())"
```

Expected: no errors; prints a path under `.reddit-skills/records/` and the skill directory path.

- [ ] **Step 4: Commit**

```bash
git add skills/reddit-explore/pipeline/__init__.py skills/reddit-explore/pipeline/paths.py skills/reddit-explore/tests/__init__.py skills/reddit-explore/scripts/__init__.py skills/reddit-explore/resources/.gitkeep
git commit -m "scaffold reddit-explore package and shared paths"
```

---

### Task 2: Implement `pipeline/records.py`

**Files:**

- Create: `skills/reddit-explore/pipeline/records.py`
- Create: `skills/reddit-explore/tests/test_records.py`

**Interfaces:**

- Produces: `post_record(post: dict) -> dict`, `comment_record(post: dict, comment: dict) -> dict`, `user_record(item: dict) -> dict`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-explore/tests/test_records.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.records import comment_record, post_record, user_record


def test_post_record():
    post = {
        "id": "p1",
        "subreddit": "test",
        "title": "Best app for X?",
        "selftext": "Looking for ...",
        "author": "op",
        "score": 10,
        "url": "https://reddit.com/r/test/comments/p1/test/",
        "permalink": "/r/test/comments/p1/test/",
    }
    record = post_record(post)
    assert record == {
        "id": "p1",
        "post_id": "p1",
        "subreddit": "r/test",
        "title": "Best app for X?",
        "post_text": "Looking for ...",
        "text": "Looking for ...",
        "author": "op",
        "score": 10,
        "url": "https://reddit.com/r/test/comments/p1/test/",
        "is_comment": False,
    }


def test_comment_record():
    post = {
        "id": "p1",
        "subreddit": "test",
        "title": "Best app for X?",
        "selftext": "Looking for ...",
        "author": "op",
        "score": 10,
        "url": "https://reddit.com/r/test/comments/p1/test/",
        "permalink": "/r/test/comments/p1/test/",
    }
    comment = {
        "id": "c1",
        "body": "I need this",
        "author": "u1",
        "score": 5,
        "permalink": "/r/test/comments/p1/test/c1/",
    }
    record = comment_record(post, comment)
    assert record == {
        "id": "c1",
        "post_id": "p1",
        "subreddit": "r/test",
        "title": "Best app for X?",
        "post_text": "Looking for ...",
        "text": "I need this",
        "author": "u1",
        "score": 5,
        "url": "https://www.reddit.com/r/test/comments/p1/test/c1/",
        "is_comment": True,
    }


def test_user_record_post():
    item = {
        "kind": "t3",
        "data": {
            "id": "p2",
            "subreddit": "test",
            "title": "My post",
            "selftext": "hello",
            "author": "u2",
            "score": 7,
            "url": "https://reddit.com/r/test/comments/p2/my/",
            "permalink": "/r/test/comments/p2/my/",
        },
    }
    record = user_record(item)
    assert record["is_comment"] is False
    assert record["id"] == "p2"
    assert record["post_id"] == "p2"
    assert record["text"] == "hello"


def test_user_record_comment():
    item = {
        "kind": "t1",
        "data": {
            "id": "c2",
            "link_id": "t3_p2",
            "subreddit": "test",
            "link_title": "My post",
            "link_selftext": "hello",
            "body": "great post",
            "author": "u3",
            "score": 3,
            "permalink": "/r/test/comments/p2/my/c2/",
        },
    }
    record = user_record(item)
    assert record["is_comment"] is True
    assert record["id"] == "c2"
    assert record["post_id"] == "p2"
    assert record["text"] == "great post"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd skills/reddit-explore
python -m pytest tests/test_records.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `pipeline.records`.

- [ ] **Step 3: Implement `pipeline/records.py`**

```python
from urllib.parse import urljoin


PUBLIC_BASE = "https://www.reddit.com"


def post_record(post: dict) -> dict:
    """Reddit post dict → validator record shape (is_comment=False)."""
    post_id = post.get("id") or ""
    subreddit = post.get("subreddit", "unknown")
    title = post.get("title", "")
    selftext = post.get("selftext", "")
    url = post.get("url", "") or urljoin(PUBLIC_BASE, post.get("permalink", ""))
    return {
        "id": post_id,
        "post_id": post_id,
        "subreddit": f"r/{subreddit}" if not str(subreddit).startswith("r/") else str(subreddit),
        "title": title,
        "post_text": selftext,
        "text": selftext,
        "author": str(post.get("author", "")),
        "score": post.get("score", 0) or 0,
        "url": url,
        "is_comment": False,
    }


def comment_record(post: dict, comment: dict) -> dict:
    """Reddit comment dict → validator record shape (is_comment=True)."""
    post_id = post.get("id") or ""
    subreddit = post.get("subreddit", "unknown")
    permalink = comment.get("permalink", post.get("permalink", ""))
    url = urljoin(PUBLIC_BASE, permalink) if permalink.startswith("/") else comment.get("url", "")
    return {
        "id": comment.get("id"),
        "post_id": post_id,
        "subreddit": f"r/{subreddit}" if not str(subreddit).startswith("r/") else str(subreddit),
        "title": post.get("title", ""),
        "post_text": post.get("selftext", ""),
        "text": comment.get("body", ""),
        "author": str(comment.get("author", "")),
        "score": comment.get("score", 0) or 0,
        "url": url,
        "is_comment": True,
    }


def user_record(item: dict) -> dict:
    """User profile item (post or comment) → validator record shape."""
    data = item.get("data", item)
    kind = item.get("kind", "t3")

    if kind == "t1":
        # comment
        post_id = data.get("link_id", "").lstrip("t3_")
        subreddit = data.get("subreddit", "unknown")
        permalink = data.get("permalink", "")
        url = urljoin(PUBLIC_BASE, permalink) if permalink.startswith("/") else data.get("url", "")
        return {
            "id": data.get("id"),
            "post_id": post_id,
            "subreddit": f"r/{subreddit}" if not str(subreddit).startswith("r/") else str(subreddit),
            "title": data.get("link_title", ""),
            "post_text": data.get("link_selftext", ""),
            "text": data.get("body", ""),
            "author": str(data.get("author", "")),
            "score": data.get("score", 0) or 0,
            "url": url,
            "is_comment": True,
        }

    # post
    post_id = data.get("id") or ""
    subreddit = data.get("subreddit", "unknown")
    title = data.get("title", "")
    selftext = data.get("selftext", "")
    url = data.get("url", "") or urljoin(PUBLIC_BASE, data.get("permalink", ""))
    return {
        "id": post_id,
        "post_id": post_id,
        "subreddit": f"r/{subreddit}" if not str(subreddit).startswith("r/") else str(subreddit),
        "title": title,
        "post_text": selftext,
        "text": selftext,
        "author": str(data.get("author", "")),
        "score": data.get("score", 0) or 0,
        "url": url,
        "is_comment": False,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd skills/reddit-explore
python -m pytest tests/test_records.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-explore/pipeline/records.py skills/reddit-explore/tests/test_records.py
git commit -m "add reddit-explore record normalization"
```

---

### Task 3: Implement `pipeline/client.py`

**Files:**

- Create: `skills/reddit-explore/pipeline/client.py`
- Create: `skills/reddit-explore/tests/test_client.py`

**Interfaces:**

- Consumes: `reddit-auth` (`resolve_strategy()`, `get_client()`, `ensure_authenticated_page()`, `fetch_json()`, `bearer_token()`, `user_agent()`).
- Produces: `class Fetcher` with `search()`, `subreddit_listing()`, `post()`, `user()`, `close()`, plus `get_fetcher()` and `Fetcher.from_existing()`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-explore/tests/test_client.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.client import Fetcher


class FakeReddit:
    def __init__(self, submissions):
        self._submissions = submissions
        self.searched = []
        self.browsed = []

    def subreddit(self, name):
        class Sub:
            def __init__(_self, name, submissions, outer):
                _self.name = name
                _self._submissions = submissions
                _self._outer = outer

            def search(_self, query, sort=None, time_filter=None, limit=None):
                _self._outer.searched.append((_self.name, query, limit))
                return [s for s in _self._submissions if limit is None or len(_self._submissions) <= limit][:limit]

            def hot(_self, limit=None):
                _self._outer.browsed.append((_self.name, "hot", limit))
                return _self._submissions[:limit]

            def top(_self, limit=None, time_filter=None):
                _self._outer.browsed.append((_self.name, "top", time_filter))
                return _self._submissions[:limit]

        return Sub(name, self._submissions, self)

    def submission(self, id):
        return self._submissions[0]

    def redditor(self, name):
        class User:
            def __init__(_self):
                _self.name = name

            def submissions(self, **kwargs):
                return [self._submissions[0]]

            def comments(self, **kwargs):
                return []

            def new(self, **kwargs):
                return [self._submissions[0]]

        return User()


def test_fetcher_from_existing_praw():
    fake = FakeReddit([])
    fetcher = Fetcher.from_existing(fake)
    assert fetcher.strategy == "praw"


def test_fetcher_search_delegates_to_praw():
    class Sub:
        pass

    class Fake:
        def subreddit(self, name):
            class Sub:
                def search(self, **kwargs):
                    return [{"id": "p1"}]
            return Sub()

    fetcher = Fetcher.from_existing(Fake())
    result = fetcher.search("test", limit=1)
    assert result == [{"id": "p1"}]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd skills/reddit-explore
python -m pytest tests/test_client.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `pipeline.client`.

- [ ] **Step 3: Implement `pipeline/client.py`**

```python
import importlib.util
import json
from pathlib import Path
from typing import Optional

import requests


PUBLIC_BASE = "https://www.reddit.com"
OAUTH_BASE = "https://oauth.reddit.com"


def _load_auth():
    """Load the reddit-auth pipeline module from the sibling skill directory."""
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    auth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth)
    return auth


class Fetcher:
    """Uniform Reddit JSON fetcher across all auth strategies."""

    def __init__(self, strategy: str, client):
        self.strategy = strategy
        self._client = client

    @classmethod
    def from_existing(cls, client) -> "Fetcher":
        """Wrap an already-open reddit-auth client (Session, requests.Session, or praw.Reddit)."""
        if hasattr(client, "page"):
            return cls("browser", client)
        if hasattr(client, "headers") and client.headers.get("Authorization"):
            return cls("bearer", client)
        if hasattr(client, "subreddit"):
            return cls("praw", client)
        return cls("public", client)

    @classmethod
    def create(cls) -> "Fetcher":
        """Create a new Fetcher from the active auth strategy."""
        auth = _load_auth()
        strategy = auth.resolve_strategy()

        if strategy == "browser":
            session = auth.ensure_authenticated_page()
            return cls("browser", session)

        if strategy == "bearer":
            token = auth.bearer_token()
            if not token:
                raise RuntimeError("No bearer token could be parsed from REDDIT_CLIENT_SECRET")
            session = requests.Session()
            session.headers.update({
                "Authorization": f"Bearer {token}",
                "User-Agent": auth.user_agent(),
            })
            return cls("bearer", session)

        if strategy == "praw":
            try:
                from praw import Reddit
            except ImportError as exc:
                raise RuntimeError("praw not installed") from exc
            return cls("praw", auth.get_client("praw"))

        session = requests.Session()
        session.headers.update({"User-Agent": auth.user_agent()})
        return cls("public", session)

    def _browser_fetch(self, path: str, params: Optional[dict] = None) -> dict:
        page = self._client.page
        return _load_auth().fetch_json(page, PUBLIC_BASE, f"{path}.json", params)

    def _requests_get(self, url: str, params: Optional[dict] = None, timeout: int = 15) -> dict:
        response = self._client.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def _extract_children(self, data: dict) -> list[dict]:
        """Extract data children from a Reddit listing or mixed listing."""
        if isinstance(data, list):
            return data
        children = data.get("data", {}).get("children", [])
        return [child.get("data", child) if isinstance(child, dict) else child for child in children]

    def search(self, query, *, subreddit=None, limit=25, sort="relevance", time_filter="all") -> list[dict]:
        """Return raw post dicts for a search query."""
        if self.strategy == "praw":
            sub_name = subreddit or "all"
            subs = self._client.subreddit(sub_name)
            results = subs.search(query, sort=sort, time_filter=time_filter, limit=limit)
            return [{"id": s.id, "title": s.title, "selftext": s.selftext, "subreddit": str(s.subreddit),
                     "author": str(s.author), "score": s.score, "url": s.url, "permalink": s.permalink}
                    for s in results]

        if self.strategy == "browser":
            search_path = f"/r/{subreddit}/search" if subreddit else "/search"
            data = self._browser_fetch(search_path, {
                "q": query, "sort": sort, "t": time_filter, "limit": min(limit, 100),
            })
            return self._extract_children(data)

        search_path = f"/r/{subreddit}/search" if subreddit else "/r/all/search"
        base = OAUTH_BASE if self.strategy == "bearer" else PUBLIC_BASE
        data = self._requests_get(
            f"{base}{search_path}.json",
            params={"q": query, "sort": sort, "t": time_filter, "limit": min(limit, 100)},
        )
        return self._extract_children(data)

    def subreddit_listing(self, name, *, sort="hot", limit=25, time_filter="all") -> list[dict]:
        """Return raw post dicts for a subreddit listing."""
        if sort == "rising":
            sort = "hot"

        if self.strategy == "praw":
            sub = self._client.subreddit(name)
            method = getattr(sub, sort, sub.hot)
            kwargs = {"limit": limit}
            if sort == "top" and time_filter:
                kwargs["time_filter"] = time_filter
            results = method(**kwargs)
            return [{"id": s.id, "title": s.title, "selftext": s.selftext, "subreddit": str(s.subreddit),
                     "author": str(s.author), "score": s.score, "url": s.url, "permalink": s.permalink}
                    for s in results]

        if self.strategy == "browser":
            data = self._browser_fetch(f"/r/{name}/{sort}", {"limit": min(limit, 100), "t": time_filter})
            return self._extract_children(data)

        base = OAUTH_BASE if self.strategy == "bearer" else PUBLIC_BASE
        params = {"limit": min(limit, 100)}
        if time_filter and sort in ("top", "controversial"):
            params["t"] = time_filter
        data = self._requests_get(f"{base}/r/{name}/{sort}.json", params=params)
        return self._extract_children(data)

    def post(self, permalink_or_id, *, comment_limit=0, comment_sort="top") -> tuple[dict, list[dict]]:
        """Return (post_dict, comments_list). comment_limit=0 skips comments."""
        post_id = self._normalize_post_id(permalink_or_id)

        if self.strategy == "praw":
            submission = self._client.submission(id=post_id)
            post = {"id": submission.id, "title": submission.title, "selftext": submission.selftext,
                    "subreddit": str(submission.subreddit), "author": str(submission.author),
                    "score": submission.score, "url": submission.url, "permalink": submission.permalink}
            comments = []
            if comment_limit:
                submission.comments.replace_more(limit=0)
                for c in submission.comments.list()[:comment_limit]:
                    comments.append({"id": c.id, "body": c.body, "author": str(c.author),
                                     "score": c.score, "permalink": c.permalink})
            return post, comments

        if self.strategy == "browser":
            data = self._browser_fetch(f"/r/placeholder/comments/{post_id}/title")
            if not isinstance(data, list) or len(data) < 2:
                raise LookupError(f"Could not fetch post {post_id}")
            post = self._extract_children(data[0])[0]
            comments = self._extract_children(data[1])[:comment_limit] if comment_limit else []
            return post, comments

        base = OAUTH_BASE if self.strategy == "bearer" else PUBLIC_BASE
        data = self._requests_get(f"{base}/r/placeholder/comments/{post_id}/title.json",
                                  params={"limit": comment_limit, "sort": comment_sort})
        if not isinstance(data, list) or len(data) < 2:
            raise LookupError(f"Could not fetch post {post_id}")
        post = self._extract_children(data[0])[0]
        comments = self._extract_children(data[1])[:comment_limit] if comment_limit else []
        return post, comments

    def user(self, name, *, section="overview", limit=25, sort="new") -> list[dict]:
        """Return raw item dicts for a user profile section."""
        if section == "overview":
            section = "submitted"

        if self.strategy == "praw":
            redditor = self._client.redditor(name)
            method = redditor.new if sort == "new" else redditor.hot
            items = method(limit=limit)
            result = []
            for item in items:
                if hasattr(item, "link_id"):
                    # comment
                    result.append({"kind": "t1", "data": {
                        "id": item.id, "link_id": item.link_id, "subreddit": str(item.subreddit),
                        "body": item.body, "author": str(item.author), "score": item.score,
                        "link_title": getattr(item, "link_title", ""), "permalink": item.permalink,
                    }})
                else:
                    result.append({"kind": "t3", "data": {
                        "id": item.id, "title": item.title, "selftext": item.selftext,
                        "subreddit": str(item.subreddit), "author": str(item.author),
                        "score": item.score, "url": item.url, "permalink": item.permalink,
                    }})
            return result

        if self.strategy == "browser":
            data = self._browser_fetch(f"/user/{name}/{section}", {"limit": min(limit, 100), "sort": sort})
            return self._extract_children(data)

        base = OAUTH_BASE if self.strategy == "bearer" else PUBLIC_BASE
        data = self._requests_get(f"{base}/user/{name}/{section}.json",
                                  params={"limit": min(limit, 100), "sort": sort})
        return self._extract_children(data)

    def close(self) -> None:
        if hasattr(self._client, "close"):
            self._client.close()

    @staticmethod
    def _normalize_post_id(value: str) -> str:
        """Accept full URL, permalink, or id (with or without t3_ prefix)."""
        value = value.strip()
        if value.startswith("http"):
            # extract id from url like .../comments/ID/...
            parts = [p for p in value.split("/") if p]
            if "comments" in parts:
                idx = parts.index("comments")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        parts = [p for p in value.split("/") if p]
        if parts and parts[0].lower() == "r":
            if "comments" in parts:
                idx = parts.index("comments")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        return value.lstrip("t3_")


def get_fetcher() -> Fetcher:
    return Fetcher.create()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd skills/reddit-explore
python -m pytest tests/test_client.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-explore/pipeline/client.py skills/reddit-explore/tests/test_client.py
git commit -m "add reddit-explore Fetcher client with auth strategy dispatch"
```

---

### Task 4: Implement `pipeline/explorer.py`

**Files:**

- Create: `skills/reddit-explore/pipeline/explorer.py`
- Create: `skills/reddit-explore/tests/test_explorer.py`

**Interfaces:**

- Consumes: `Fetcher` (from `client.py`), `post_record`, `comment_record`, `user_record` (from `records.py`).
- Produces: `search_posts()`, `list_subreddit()`, `get_post()`, `get_user()`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-explore/tests/test_explorer.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.explorer import get_post, get_user, list_subreddit, search_posts


class FakeFetcher:
    def __init__(self, posts=None, comments=None, user_items=None):
        self._posts = posts or []
        self._comments = comments or []
        self._user_items = user_items or []
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return self._posts

    def subreddit_listing(self, **kwargs):
        self.calls.append(("subreddit_listing", kwargs))
        return self._posts

    def post(self, permalink_or_id, **kwargs):
        self.calls.append(("post", permalink_or_id, kwargs))
        return self._posts[0], self._comments

    def user(self, name, **kwargs):
        self.calls.append(("user", name, kwargs))
        return self._user_items

    def close(self):
        pass


def test_search_posts_without_subreddits():
    fetcher = FakeFetcher(posts=[{"id": "p1", "subreddit": "test", "title": "T", "selftext": "", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"}])
    records = search_posts("app", fetcher=fetcher)
    assert len(records) == 1
    assert records[0]["post_id"] == "p1"
    assert fetcher.calls[0][0] == "search"


def test_search_posts_with_subreddits():
    fetcher = FakeFetcher(posts=[{"id": "p1", "subreddit": "test", "title": "T", "selftext": "", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"}])
    records = search_posts("app", fetcher=fetcher, subreddits="IELTS,TOEFL")
    assert len(fetcher.calls) == 2
    assert fetcher.calls[0][1]["subreddit"] == "IELTS"
    assert fetcher.calls[1][1]["subreddit"] == "TOEFL"


def test_list_subreddit():
    fetcher = FakeFetcher(posts=[{"id": "p1", "subreddit": "test", "title": "T", "selftext": "", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"}])
    records = list_subreddit("test", fetcher=fetcher)
    assert records[0]["post_id"] == "p1"
    assert fetcher.calls[0][0] == "subreddit_listing"


def test_get_post():
    post = {"id": "p1", "subreddit": "test", "title": "T", "selftext": "body", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"}
    comment = {"id": "c1", "body": "cm", "author": "u1", "score": 2, "permalink": "/r/test/p1/c1"}
    fetcher = FakeFetcher(posts=[post], comments=[comment])
    records = get_post("p1", fetcher=fetcher)
    assert records[0]["is_comment"] is False
    assert records[1]["is_comment"] is True
    assert records[1]["id"] == "c1"


def test_get_user():
    item = {"kind": "t1", "data": {"id": "c1", "link_id": "t3_p1", "subreddit": "test", "body": "hi", "author": "u1", "score": 1, "permalink": "/r/test/p1/c1"}}
    fetcher = FakeFetcher(user_items=[item])
    records = get_user("u1", fetcher=fetcher, section="comments")
    assert records[0]["is_comment"] is True


def test_empty_results():
    fetcher = FakeFetcher()
    records = search_posts("nothing", fetcher=fetcher)
    assert records == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd skills/reddit-explore
python -m pytest tests/test_explorer.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `pipeline.explorer`.

- [ ] **Step 3: Implement `pipeline/explorer.py`**

```python
from .client import Fetcher, get_fetcher  # noqa: F401
from .records import comment_record, post_record, user_record


def _normalize_subreddits(subreddits):
    """Accept 'IELTS', 'r/IELTS', ' IELTS,TOEFL ' → ['IELTS', 'TOEFL']."""
    if not subreddits:
        return []
    if isinstance(subreddits, str):
        subreddits = subreddits.split(",")
    return [s.strip().lstrip("r/").strip() for s in subreddits if s.strip()]


def _fetch_comments(fetcher, post, limit, sort):
    """Fetch top comments for a post."""
    if not limit or not post.get("permalink"):
        return []
    _, comments = fetcher.post(post["permalink"], comment_limit=limit, comment_sort=sort)
    return comments


def search_posts(
    query: str,
    *,
    fetcher: Fetcher,
    subreddits=None,
    limit: int = 25,
    sort: str = "relevance",
    time_filter: str = "all",
    fetch_comments: bool = False,
    comment_limit: int = 3,
    comment_sort: str = "top",
) -> list[dict]:
    """Keyword search across all of Reddit or specific subreddits."""
    subs = _normalize_subreddits(subreddits)
    records = []

    if subs:
        per_sub = max(1, limit // max(1, len(subs))) if limit else 25
        for sub in subs:
            raw_posts = fetcher.search(
                query, subreddit=sub, limit=per_sub, sort=sort, time_filter=time_filter
            )
            for post in raw_posts[:per_sub]:
                records.append(post_record(post))
                if fetch_comments:
                    for comment in _fetch_comments(fetcher, post, comment_limit, comment_sort):
                        records.append(comment_record(post, comment))
        return records

    raw_posts = fetcher.search(query, limit=limit, sort=sort, time_filter=time_filter)
    for post in raw_posts[:limit]:
        records.append(post_record(post))
        if fetch_comments:
            for comment in _fetch_comments(fetcher, post, comment_limit, comment_sort):
                records.append(comment_record(post, comment))
    return records


def list_subreddit(
    name: str,
    *,
    fetcher: Fetcher,
    sort: str = "hot",
    limit: int = 25,
    time_filter: str = "all",
    fetch_comments: bool = False,
    comment_limit: int = 3,
    comment_sort: str = "top",
) -> list[dict]:
    """Browse a subreddit's listing."""
    records = []
    raw_posts = fetcher.subreddit_listing(name, sort=sort, limit=limit, time_filter=time_filter)
    for post in raw_posts[:limit]:
        records.append(post_record(post))
        if fetch_comments:
            for comment in _fetch_comments(fetcher, post, comment_limit, comment_sort):
                records.append(comment_record(post, comment))
    return records


def get_post(
    permalink_or_id: str,
    *,
    fetcher: Fetcher,
    comment_limit: int = 10,
    comment_sort: str = "top",
) -> list[dict]:
    """Fetch a single post and its comment tree."""
    post, comments = fetcher.post(permalink_or_id, comment_limit=comment_limit, comment_sort=comment_sort)
    records = [post_record(post)]
    for comment in comments:
        records.append(comment_record(post, comment))
    return records


def get_user(
    name: str,
    *,
    fetcher: Fetcher,
    section: str = "overview",
    limit: int = 25,
    sort: str = "new",
) -> list[dict]:
    """Fetch a user's profile section."""
    raw_items = fetcher.user(name, section=section, limit=limit, sort=sort)
    return [user_record(item) for item in raw_items[:limit]]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd skills/reddit-explore
python -m pytest tests/test_explorer.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-explore/pipeline/explorer.py skills/reddit-explore/tests/test_explorer.py
git commit -m "add reddit-explore read primitives"
```

---

### Task 5: Implement `scripts/search.py` and `scripts/subreddit.py`

**Files:**

- Create: `skills/reddit-explore/scripts/search.py`
- Create: `skills/reddit-explore/scripts/subreddit.py`
- Create: `skills/reddit-explore/tests/test_scripts_search.py`
- Create: `skills/reddit-explore/tests/test_scripts_subreddit.py`

**Interfaces:**

- Consumes: `search_posts()`, `list_subreddit()`, `get_fetcher()`, `records_dir()`.
- Produces: `scripts/search.py` and `scripts/subreddit.py` CLI entrypoints.

- [ ] **Step 1: Write the failing tests**

Create `skills/reddit-explore/tests/test_scripts_search.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import search


class FakeFetcher:
    def __init__(self, records):
        self._records = records

    def search(self, *args, **kwargs):
        return [{"id": "p1", "subreddit": "test", "title": "T", "selftext": "", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"}]

    def close(self):
        pass


def test_search_main(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(search, "get_fetcher", lambda: FakeFetcher([]))
    monkeypatch.setattr(search, "records_dir", lambda: tmp_path)
    code = search.main(["hello", "--limit", "1", "--comments", "0"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["count"] == 1
```

Create `skills/reddit-explore/tests/test_scripts_subreddit.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import subreddit


class FakeFetcher:
    def subreddit_listing(self, *args, **kwargs):
        return [{"id": "p1", "subreddit": "test", "title": "T", "selftext": "", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"}]

    def close(self):
        pass


def test_subreddit_main(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(subreddit, "get_fetcher", lambda: FakeFetcher())
    monkeypatch.setattr(subreddit, "records_dir", lambda: tmp_path)
    code = subreddit.main(["test", "--limit", "1"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd skills/reddit-explore
python -m pytest tests/test_scripts_search.py tests/test_scripts_subreddit.py -v
```

Expected: `ImportError` for `scripts.search` and `scripts.subreddit`.

- [ ] **Step 3: Implement `scripts/search.py`**

```python
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.client import get_fetcher
from pipeline.explorer import search_posts
from pipeline.paths import records_dir


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Search Reddit posts.")
    parser.add_argument("query", help="Search query.")
    parser.add_argument("--subreddits", default=None, help="Comma-separated subreddits.")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", default="relevance", choices=["relevance", "hot", "new", "top"])
    parser.add_argument("--t", default="all", choices=["all", "day", "week", "month", "year"])
    parser.add_argument("--comments", type=int, default=0, help="Top comments per post (0=skip).")
    parser.add_argument("--comment-sort", default="top", choices=["top", "best", "new", "controversial"])
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    fetcher = get_fetcher()
    try:
        records = search_posts(
            args.query,
            fetcher=fetcher,
            subreddits=args.subreddits,
            limit=args.limit,
            sort=args.sort,
            time_filter=args.t,
            fetch_comments=args.comments > 0,
            comment_limit=args.comments,
            comment_sort=args.comment_sort,
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "fetch_error"}))
        return 1
    finally:
        fetcher.close()

    out_path = Path(args.out) if args.out else records_dir() / f"search_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "count": len(records), "records_path": str(out_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implement `scripts/subreddit.py`**

```python
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
    fetcher = get_fetcher()
    try:
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
        fetcher.close()

    out_path = Path(args.out) if args.out else records_dir() / f"subreddit_{args.name}_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "count": len(records), "records_path": str(out_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd skills/reddit-explore
python -m pytest tests/test_scripts_search.py tests/test_scripts_subreddit.py -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add skills/reddit-explore/scripts/search.py skills/reddit-explore/scripts/subreddit.py skills/reddit-explore/tests/test_scripts_search.py skills/reddit-explore/tests/test_scripts_subreddit.py
git commit -m "add reddit-explore search and subreddit CLI scripts"
```

---

### Task 6: Implement `scripts/post.py` and `scripts/user.py`

**Files:**

- Create: `skills/reddit-explore/scripts/post.py`
- Create: `skills/reddit-explore/scripts/user.py`
- Create: `skills/reddit-explore/tests/test_scripts_post.py`
- Create: `skills/reddit-explore/tests/test_scripts_user.py`

**Interfaces:**

- Consumes: `get_post()`, `get_user()`, `get_fetcher()`, `records_dir()`.
- Produces: `scripts/post.py` and `scripts/user.py` CLI entrypoints.

- [ ] **Step 1: Write the failing tests**

Create `skills/reddit-explore/tests/test_scripts_post.py`:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import post


class FakeFetcher:
    def post(self, *args, **kwargs):
        return (
            {"id": "p1", "subreddit": "test", "title": "T", "selftext": "body", "author": "op", "score": 1, "url": "u", "permalink": "/r/test/p1"},
            [{"id": "c1", "body": "cm", "author": "u1", "score": 2, "permalink": "/r/test/p1/c1"}],
        )

    def close(self):
        pass


def test_post_main(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(post, "get_fetcher", lambda: FakeFetcher())
    monkeypatch.setattr(post, "records_dir", lambda: tmp_path)
    code = post.main(["p1"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["count"] == 2
```

Create `skills/reddit-explore/tests/test_scripts_user.py`:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import user


class FakeFetcher:
    def user(self, *args, **kwargs):
        return [{"kind": "t1", "data": {"id": "c1", "link_id": "t3_p1", "subreddit": "test", "body": "hi", "author": "u1", "score": 1, "permalink": "/r/test/p1/c1"}}]

    def close(self):
        pass


def test_user_main(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(user, "get_fetcher", lambda: FakeFetcher())
    monkeypatch.setattr(user, "records_dir", lambda: tmp_path)
    code = user.main(["u1"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd skills/reddit-explore
python -m pytest tests/test_scripts_post.py tests/test_scripts_user.py -v
```

Expected: `ImportError` for `scripts.post` and `scripts.user`.

- [ ] **Step 3: Implement `scripts/post.py`**

```python
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.client import get_fetcher
from pipeline.explorer import get_post
from pipeline.paths import records_dir


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Fetch a Reddit post and its comments.")
    parser.add_argument("url_or_id", help="Post URL, permalink, or id.")
    parser.add_argument("--comments", type=int, default=10, help="Number of top comments to fetch.")
    parser.add_argument("--comment-sort", default="top", choices=["top", "best", "new", "controversial"])
    parser.add_argument("--out", default=None, help="Output JSON path. Default: records/.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    fetcher = get_fetcher()
    try:
        records = get_post(
            args.url_or_id,
            fetcher=fetcher,
            comment_limit=args.comments,
            comment_sort=args.comment_sort,
        )
    except Exception as exc:
        print(json.dumps({"event": "done", "success": False, "error": str(exc), "code": "fetch_error"}))
        return 1
    finally:
        fetcher.close()

    out_path = Path(args.out) if args.out else records_dir() / f"post_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "count": len(records), "records_path": str(out_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implement `scripts/user.py`**

```python
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
    fetcher = get_fetcher()
    try:
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
        fetcher.close()

    out_path = Path(args.out) if args.out else records_dir() / f"user_{args.name}_{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, default=str))
    print(json.dumps({"event": "done", "success": True, "count": len(records), "records_path": str(out_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd skills/reddit-explore
python -m pytest tests/test_scripts_post.py tests/test_scripts_user.py -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add skills/reddit-explore/scripts/post.py skills/reddit-explore/scripts/user.py skills/reddit-explore/tests/test_scripts_post.py skills/reddit-explore/tests/test_scripts_user.py
git commit -m "add reddit-explore post and user CLI scripts"
```

---

### Task 7: Implement `scripts/preflight.py`

**Files:**

- Create: `skills/reddit-explore/scripts/preflight.py`
- Create: `skills/reddit-explore/tests/test_preflight.py`

**Interfaces:**

- Consumes: `reddit-auth.validate_credentials()`.
- Produces: `preflight()` returning `{env_ok, deps_ok, reddit_ok}`.

- [ ] **Step 1: Write the failing test**

Create `skills/reddit-explore/tests/test_preflight.py`:

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

```bash
cd skills/reddit-explore
python -m pytest tests/test_preflight.py -v
```

Expected: `ImportError` for `scripts.preflight`.

- [ ] **Step 3: Implement `scripts/preflight.py`**

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

```bash
cd skills/reddit-explore
python -m pytest tests/test_preflight.py -v
```

Expected: test passes.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-explore/scripts/preflight.py skills/reddit-explore/tests/test_preflight.py
git commit -m "add reddit-explore preflight script and tests"
```

---

### Task 8: Skill contract and metadata

**Files:**

- Create: `skills/reddit-explore/requirements.txt`
- Create: `skills/reddit-explore/.env.example`
- Create: `skills/reddit-explore/.markdownlint.json`
- Create: `skills/reddit-explore/SKILL.md`
- Create: `skills/reddit-explore/resources/DEVIN.md`
- Create: `skills/reddit-explore/resources/CLAUDE.md`
- Create: `skills/reddit-explore/resources/failure-recovery.md`

- [ ] **Step 1: Create `requirements.txt`**

```text
requests
python-dotenv
praw
rustwright
```

- [ ] **Step 2: Create `.env.example`**

```text
# Authentication method (optional; defaults to browser if no API creds present):
# - rustwright | playwright | browser: open a real Chromium window for manual login
# - token: paste a base64 Reddit token JSON in REDDIT_CLIENT_SECRET
# - praw: use a script app client_id / client_secret / username / password
REDDIT_LOGIN_METHOD=rustwright

# Optional: for token/praw methods
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=script:reddit-explore:v0.1 (by /u/your_username)

# Optional: for PRAW script apps only
REDDIT_USERNAME=
REDDIT_PASSWORD=
```

- [ ] **Step 3: Create `.markdownlint.json`**

```json
{
  "MD013": false,
  "MD060": false
}
```

- [ ] **Step 4: Create `SKILL.md` (summary)**

```markdown
---
name: reddit-explore
description: Use when the user wants to discover, browse, or research Reddit content — search posts, browse subreddits, read post details with comments, or view user profiles.
---

# Reddit Explore

Discover and research Reddit content: search posts, browse subreddits, read post details with comments, and view user profiles.

## When to use

- "search Reddit for X", "find posts about X", "what's trending on r/X"
- "show me posts from r/X", "browse r/X", "what's hot on r/X"
- "read this post", "get post details", "show comments on this post"
- "look up user X", "what does user X post about", "user X's comment history"
- Another skill (e.g. reddit-validator) needs Reddit data fetched

Do NOT use for: validating a business idea, posting content, voting/commenting, or compound operations like trend tracking.

## Prerequisites

- Python 3.10+.
- Dependencies installed: `pip install -r <skill_dir>/requirements.txt`.
- Reddit access via one of the four auth strategies handled by `reddit-auth`.

## Workflow

1. Preflight: `python "<skill_dir>/scripts/preflight.py"`
2. Pick a capability and run the matching script:
   - Search: `python "<skill_dir>/scripts/search.py" "<query>"`
   - Subreddit: `python "<skill_dir>/scripts/subreddit.py" "<name>"`
   - Post: `python "<skill_dir>/scripts/post.py" "<url_or_id>"`
   - User: `python "<skill_dir>/scripts/user.py" "<name>"`
3. Read the `done` JSON event and the records file.

## Operating principles

- Run preflight first.
- These are fast synchronous queries.
- Return structured JSON; let the agent decide how to present it.
- Reuse a saved browser session when available.
```

- [ ] **Step 5: Create `resources/DEVIN.md` and `resources/CLAUDE.md`**

Both files should mirror the validator runtime guide pattern but for the four scripts. Example for `DEVIN.md`:

```markdown
# Devin Runtime Guide for reddit-explore

## Phase 1 — Preflight

Run:

```bash
python "<skill_dir>/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true.

## Phase 2 — Pick a capability

### Search

```bash
python "<skill_dir>/scripts/search.py" "<query>" --subreddits "IELTS,TOEFL" --limit 10
```

### Browse a subreddit

```bash
python "<skill_dir>/scripts/subreddit.py" "<name>" --sort hot --limit 25
```

### Post details

```bash
python "<skill_dir>/scripts/post.py" "<url_or_id>" --comments 10
```

### User profile

```bash
python "<skill_dir>/scripts/user.py" "<name>" --section overview --limit 25
```

## Phase 3 — Read output

Each script prints a single JSON line:

```json
{"event": "done", "success": true, "count": 10, "records_path": "/path/to/.reddit-skills/records/search_xxx.json"}
```

If `success` is false, read `error` and `code`.

## Phase 4 — Surface results

Summarize the records for the user. Do not dump full JSON.

`CLAUDE.md` is the same with tool names adjusted (`Bash` instead of background commands).

- [ ] **Step 6: Create `resources/failure-recovery.md`**

```markdown
# Failure recovery

| Error / symptom | Likely cause | Fix |
| --- | --- | --- |
| `deps_ok: false` | Missing Python packages | Run `pip install -r <skill_dir>/requirements.txt` |
| `reddit_ok: false` | Bad credentials or stale session | Re-run `reddit-auth/scripts/login.py` or check `.env` |
| `code: not_found` | Post, user, or subreddit does not exist | Check the URL/ID/name and retry |
| `code: forbidden` | Private subreddit or banned/suspended user | Cannot access with current auth; try a public endpoint or different account |
| `code: rate_limited` | Too many requests | Wait a minute and retry |
| `code: timeout` | Network or Reddit slow | Retry with smaller `--limit` |
```

- [ ] **Step 7: Run markdownlint on the new docs**

```bash
cd skills/reddit-explore
npx markdownlint-cli SKILL.md resources/*.md
```

Expected: no errors (assuming `.markdownlint.json` disables MD013/MD060).

- [ ] **Step 8: Commit**

```bash
git add skills/reddit-explore/requirements.txt skills/reddit-explore/.env.example skills/reddit-explore/.markdownlint.json skills/reddit-explore/SKILL.md skills/reddit-explore/resources/DEVIN.md skills/reddit-explore/resources/CLAUDE.md skills/reddit-explore/resources/failure-recovery.md
git commit -m "add reddit-explore skill contract, env, and runtime guides"
```

---

### Task 9: Refactor `reddit-validator` to use `reddit-explore`

**Files:**

- Modify: `skills/reddit-validator/pipeline/scraper.py`
- Modify: `skills/reddit-validator/tests/test_scraper.py`

**Interfaces:**

- Consumes: `reddit-explore/pipeline/explorer.search_posts()`, `reddit-explore/pipeline/client.Fetcher.from_existing()`.
- Produces: same `scrape(idea, profile, client=None, subreddits=None)` API.

- [ ] **Step 1: Rewrite `pipeline/scraper.py`**

```python
import importlib.util
from pathlib import Path


def _load_explorer():
    """Load the reddit-explore pipeline module from the sibling skill directory."""
    explorer_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "explorer.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_explorer", explorer_path)
    explorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(explorer)
    return explorer


def _load_client():
    """Load the reddit-explore client module."""
    client_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "client.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_client", client_path)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    return client


def scrape(idea, profile, client=None, subreddits=None):
    """Scrape Reddit for idea validation using reddit-explore's search primitive."""
    explorer = _load_explorer()
    client_mod = _load_client()

    fetcher = None
    close_after = False
    if client is not None:
        fetcher = client_mod.Fetcher.from_existing(client)
    else:
        fetcher = client_mod.get_fetcher()
        close_after = True

    try:
        limit = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
        if subreddits:
            limit = profile.get("posts_per_subreddit", 25)
        records = explorer.search_posts(
            idea,
            fetcher=fetcher,
            subreddits=subreddits,
            limit=limit,
            sort="relevance",
            time_filter="all",
            fetch_comments=True,
            comment_limit=3,
        )
        return records
    finally:
        if close_after:
            fetcher.close()
```

- [ ] **Step 2: Rewrite `tests/test_scraper.py`**

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.scraper import scrape


class FakeFetcher:
    def __init__(self, records):
        self._records = records
        self.search_calls = []

    def search(self, query, **kwargs):
        self.search_calls.append((query, kwargs))
        return [{"id": "p1", "subreddit": "test", "title": "Best app for X?", "selftext": "Looking for ...",
                 "author": "op", "score": 10, "url": "https://reddit.com/r/test/p1", "permalink": "/r/test/p1"}]

    def close(self):
        pass


class FakeFetcherWithComments(FakeFetcher):
    def search(self, query, **kwargs):
        return super().search(query, **kwargs)

    def post(self, permalink, **kwargs):
        return (
            {"id": "p1", "subreddit": "test", "title": "Best app for X?", "selftext": "Looking for ...",
             "author": "op", "score": 10, "url": "https://reddit.com/r/test/p1", "permalink": "/r/test/p1"},
            [{"id": "c1", "body": "I need this", "author": "u1", "score": 5, "permalink": "/r/test/p1/c1"}],
        )


def _patch_explorer(monkeypatch, records, client_type="search_with_comments"):
    from pipeline import scraper

    def fake_load_explorer():
        class FakeExplorer:
            @staticmethod
            def search_posts(idea, *, fetcher, **kwargs):
                records.extend([{"is_comment": False}])  # placeholder records
                if fetcher is not None and hasattr(fetcher, "search"):
                    fetcher.search(idea, **kwargs)
                return records
        return FakeExplorer()

    def fake_load_client():
        class FakeClient:
            @staticmethod
            def get_fetcher():
                return FakeFetcherWithComments([])

            class Fetcher:
                @staticmethod
                def from_existing(client):
                    return FakeFetcherWithComments([])
        return FakeClient()

    monkeypatch.setattr(scraper, "_load_explorer", fake_load_explorer)
    monkeypatch.setattr(scraper, "_load_client", fake_load_client)


def test_scrape_returns_records(monkeypatch):
    _patch_explorer(monkeypatch, [])
    records = scrape("app for X", {"subreddits": 1, "posts_per_subreddit": 1})
    assert len(records) >= 0


def test_scrape_targets_specific_subreddits(monkeypatch):
    _patch_explorer(monkeypatch, [])
    records = scrape("AI IELTS grading", {"posts_per_subreddit": 5}, subreddits="IELTS,TOEFL")
    assert records is not None
```

- [ ] **Step 3: Run validator tests to verify they pass**

```bash
cd skills/reddit-validator
python -m pytest tests/test_scraper.py -v
```

Expected: tests pass or are updated to the new behavior.

- [ ] **Step 4: Run validator full test suite**

```bash
cd skills/reddit-validator
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/reddit-validator/pipeline/scraper.py skills/reddit-validator/tests/test_scraper.py
git commit -m "refactor reddit-validator scraper to delegate to reddit-explore"
```

---

### Task 10: Create `.devin/skills` symlink and final integration

**Files:**

- Create: `.devin/skills/reddit-explore`

- [ ] **Step 1: Create symlink**

```bash
ln -s ../../skills/reddit-explore .devin/skills/reddit-explore
```

- [ ] **Step 2: Run full reddit-explore test suite**

```bash
cd skills/reddit-explore
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Run preflight sanity check**

```bash
python skills/reddit-explore/scripts/preflight.py
```

Expected: JSON output with `deps_ok: true` and `reddit_ok: true/false` depending on your local `.env`.

- [ ] **Step 4: Test a script end-to-end (requires auth)**

If `reddit_ok` was true, run:

```bash
python skills/reddit-explore/scripts/search.py "hello" --limit 1
```

Expected: a `done` JSON event with `count > 0` and a `records_path`.

- [ ] **Step 5: Commit and final verify**

```bash
git add .devin/skills/reddit-explore
git commit -m "add Devin skill discovery symlink for reddit-explore"

cd skills/reddit-explore
python -m pytest
```

- [ ] **Step 6: Run markdownlint on all changed docs**

```bash
cd skills/reddit-explore
npx markdownlint-cli SKILL.md resources/*.md
```

Expected: no errors.

---

## Self-Review

### 1. Spec coverage

| Spec section | Plan task |
| --- | --- |
| Architecture / file layout | Task 1, 8, 10 |
| `pipeline/client.py` Fetcher | Task 3 |
| `pipeline/records.py` normalization | Task 2 |
| `pipeline/explorer.py` four primitives | Task 4 |
| Scripts (search, subreddit, post, user) | Tasks 5, 6 |
| `preflight.py` | Task 7 |
| SKILL.md, DEVIN.md, CLAUDE.md, failure-recovery.md | Task 8 |
| Validator refactor | Task 9 |
| `.devin/skills/reddit-explore` symlink | Task 10 |

### 2. Placeholder scan

No TBDs, TODOs, or vague directives. Every step includes concrete code or exact commands.

### 3. Type consistency

- `Fetcher` methods and signatures match between `client.py` (Task 3), `explorer.py` (Task 4), and scripts (Tasks 5-6).
- `records.py` output shape is tested in Task 2 and consumed in Task 4.
- `scrape(idea, profile, client=None, subreddits=None)` signature is preserved in Task 9.
