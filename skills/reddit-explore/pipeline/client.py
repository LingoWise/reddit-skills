import importlib.util
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

    @staticmethod
    def _extract_user_items(data) -> list[dict]:
        """Return user listing children with their kind wrappers intact."""
        if isinstance(data, list):
            return data
        return data.get("data", {}).get("children", [])

    def search(self, query, *, subreddit=None, limit=25, sort="relevance", time_filter="all") -> list[dict]:
        """Return raw post dicts for a search query."""
        if self.strategy == "praw":
            sub_name = subreddit or "all"
            subs = self._client.subreddit(sub_name)
            results = subs.search(query=query, sort=sort, time_filter=time_filter, limit=limit)
            return [s if isinstance(s, dict) else {
                "id": s.id, "title": s.title, "selftext": s.selftext, "subreddit": str(s.subreddit),
                "author": str(s.author), "score": s.score, "url": s.url, "permalink": s.permalink,
            } for s in results]

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
            return self._extract_user_items(data)

        base = OAUTH_BASE if self.strategy == "bearer" else PUBLIC_BASE
        data = self._requests_get(f"{base}/user/{name}/{section}.json",
                                  params={"limit": min(limit, 100), "sort": sort})
        return self._extract_user_items(data)

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
