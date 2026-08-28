import importlib
import importlib.util
import json
import urllib.parse
from pathlib import Path

import requests


PUBLIC_BASE = "https://www.reddit.com"
OAUTH_BASE = "https://oauth.reddit.com"

_auth_module = None


def _load_auth():
    """Load the reddit-auth pipeline module from the sibling skill directory."""
    global _auth_module
    if _auth_module is not None:
        return _auth_module
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    _auth_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_auth_module)
    return _auth_module


def _praw_client():
    from praw import Reddit
    auth = _load_auth()
    username = auth.username()
    password = auth.password()
    kwargs = {
        "client_id": auth.client_id(),
        "client_secret": auth.client_secret(),
        "user_agent": auth.user_agent(),
    }
    if username and password:
        kwargs["username"] = username
        kwargs["password"] = password
    return Reddit(**kwargs)


def _praw_records(submissions, total_posts):
    records = []
    for submission in submissions:
        if len(records) >= total_posts * 3:
            break

        if hasattr(submission.comments, "replace_more"):
            submission.comments.replace_more(limit=0)
            comments = submission.comments.list()
        else:
            comments = submission.comments

        for comment in comments[:3]:
            records.append({
                "id": comment.id,
                "post_id": submission.id,
                "subreddit": str(submission.subreddit),
                "title": submission.title,
                "post_text": submission.selftext,
                "text": comment.body,
                "author": str(comment.author),
                "score": comment.score,
                "url": f"https://www.reddit.com{getattr(comment, 'permalink', submission.permalink)}",
                "is_comment": True,
            })

        records.append({
            "id": submission.id,
            "post_id": submission.id,
            "subreddit": str(submission.subreddit),
            "title": submission.title,
            "post_text": submission.selftext,
            "text": submission.selftext,
            "author": str(submission.author),
            "score": submission.score,
            "url": submission.url,
            "is_comment": False,
        })

    return records


def _search_params(idea, limit):
    return {
        "q": idea,
        "sort": "relevance",
        "t": "all",
        "limit": min(limit, 100),
    }


def _post_record(post):
    return {
        "id": post.get("id"),
        "post_id": post.get("id"),
        "subreddit": f"r/{post.get('subreddit')}",
        "title": post.get("title", ""),
        "post_text": post.get("selftext", ""),
        "text": post.get("selftext", ""),
        "author": post.get("author", ""),
        "score": post.get("score", 0),
        "url": post.get("url", ""),
        "is_comment": False,
    }


def _comment_record(post, comment):
    return {
        "id": comment.get("id"),
        "post_id": post.get("id"),
        "subreddit": f"r/{post.get('subreddit')}",
        "title": post.get("title", ""),
        "post_text": post.get("selftext", ""),
        "text": comment.get("body", ""),
        "author": comment.get("author", ""),
        "score": comment.get("score", 0),
        "url": f"https://www.reddit.com{comment.get('permalink', post.get('permalink', ''))}",
        "is_comment": True,
    }


def _api_comments(post, base, headers):
    permalink = post.get("permalink", "")
    if not permalink:
        return []
    url = f"{base}{permalink}.json"
    try:
        response = requests.get(url, headers=headers, params={"limit": 3, "sort": "top"}, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        return []

    data = response.json()
    if not isinstance(data, list) or len(data) < 2:
        return []

    listing = data[1]
    children = listing.get("data", {}).get("children", [])[:3]
    return [child.get("data", {}) for child in children if child.get("data")]


def _api_search(idea, limit, base, headers):
    response = requests.get(
        f"{base}/r/all/search",
        headers=headers,
        params=_search_params(idea, limit),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _records_from_search(data, total_posts, base, headers):
    records = []
    children = data.get("data", {}).get("children", [])[:total_posts]
    for child in children:
        post = child.get("data", {})
        if not post:
            continue
        records.append(_post_record(post))
        for comment in _api_comments(post, base, headers):
            records.append(_comment_record(post, comment))
    return records


def _public_search(idea, profile):
    auth = _load_auth()
    headers = {"User-Agent": auth.user_agent()}
    total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
    data = _api_search(idea, total_posts, PUBLIC_BASE, headers)
    return _records_from_search(data, total_posts, PUBLIC_BASE, headers)


def _bearer_search(idea, profile):
    auth = _load_auth()
    total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
    token = auth.bearer_token()
    if not token:
        raise RuntimeError("No bearer token could be parsed from REDDIT_CLIENT_SECRET")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": auth.user_agent()}
    data = _api_search(idea, total_posts, OAUTH_BASE, headers)
    return _records_from_search(data, total_posts, OAUTH_BASE, headers)


def _praw_search(idea, profile):
    client = _praw_client()
    total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
    submissions = client.subreddit("all").search(
        idea,
        sort="relevance",
        time_filter="all",
        limit=total_posts,
    )
    return _praw_records(submissions, total_posts)


def _rustwright_search(idea, profile):
    auth = _load_auth()
    total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
    session = auth.ensure_authenticated_page(timeout=300)
    try:
        page = session.page
        search_data = auth.fetch_json(
            page,
            PUBLIC_BASE,
            "/search.json",
            params=_search_params(idea, total_posts),
        )
        children = search_data.get("data", {}).get("children", [])[:total_posts]

        records = []
        for child in children:
            post = child.get("data", {})
            if not post:
                continue
            records.append(_post_record(post))
            permalink = post.get("permalink", "")
            if permalink:
                try:
                    comment_data = auth.fetch_json(
                        page,
                        PUBLIC_BASE,
                        f"{permalink}.json",
                        params={"limit": 3, "sort": "top"},
                    )
                    if isinstance(comment_data, list) and len(comment_data) >= 2:
                        listing = comment_data[1]
                        for c in listing.get("data", {}).get("children", [])[:3]:
                            records.append(_comment_record(post, c.get("data", {})))
                except Exception as exc:
                    print(f"  comments fetch warning for {permalink}: {exc}", flush=True)

        return records
    finally:
        session.close()


def scrape(idea, profile, client=None):
    if client is not None:
        total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
        submissions = client.subreddit("all").search(
            idea,
            sort="relevance",
            time_filter="all",
            limit=total_posts,
        )
        return _praw_records(submissions, total_posts)

    auth = _load_auth()
    strategy = auth.resolve_strategy()
    if strategy == "browser":
        return _rustwright_search(idea, profile)
    if strategy == "bearer":
        return _bearer_search(idea, profile)
    if strategy == "praw":
        return _praw_search(idea, profile)
    return _public_search(idea, profile)
