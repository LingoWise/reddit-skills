import base64
import json
import os

import requests
from dotenv import load_dotenv


PUBLIC_BASE = "https://www.reddit.com"
OAUTH_BASE = "https://oauth.reddit.com"


def _praw_client():
    from praw import Reddit
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")
    kwargs = {
        "client_id": os.getenv("REDDIT_CLIENT_ID"),
        "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
        "user_agent": os.getenv("REDDIT_USER_AGENT"),
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


def _user_agent():
    return os.getenv("REDDIT_USER_AGENT") or "python:reddit-validator:v0.1"


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


def _bearer_token(secret=None):
    if secret is None:
        load_dotenv()
        secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    if not secret:
        return None

    # Case 1: the value is a base64-encoded JSON object containing an access token.
    try:
        padded = secret + "=" * (-len(secret) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        token = data.get("accessToken") or data.get("token")
        if token:
            return token
    except Exception:
        pass

    # Case 2: the value is a JWT whose payload contains an access token.
    if "." in secret:
        try:
            payload = secret.split(".")[1]
            padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded))
            token = data.get("accessToken") or data.get("token")
            if token:
                return token
        except Exception:
            pass

    return None


def _bearer_headers():
    return {
        "Authorization": f"Bearer {_bearer_token()}",
        "User-Agent": _user_agent(),
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
    load_dotenv()
    headers = {"User-Agent": _user_agent()}
    total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
    data = _api_search(idea, total_posts, PUBLIC_BASE, headers)
    return _records_from_search(data, total_posts, PUBLIC_BASE, headers)


def _bearer_search(idea, profile):
    total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
    headers = _bearer_headers()
    data = _api_search(idea, total_posts, OAUTH_BASE, headers)
    return _records_from_search(data, total_posts, OAUTH_BASE, headers)


def _use_bearer():
    return _bearer_token() is not None


def _use_praw():
    load_dotenv()
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return False
    if client_id == "your_reddit_app_client_id" or client_secret == "your_reddit_app_client_secret":
        return False
    if _use_bearer():
        return False
    return True


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

    if _use_bearer():
        return _bearer_search(idea, profile)

    if _use_praw():
        client = _praw_client()
        total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
        submissions = client.subreddit("all").search(
            idea,
            sort="relevance",
            time_filter="all",
            limit=total_posts,
        )
        return _praw_records(submissions, total_posts)

    return _public_search(idea, profile)
