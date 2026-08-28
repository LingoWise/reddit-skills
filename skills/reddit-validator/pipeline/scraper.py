import os

import requests
from dotenv import load_dotenv


PUBLIC_BASE = "https://www.reddit.com"


def _praw_client():
    from praw import Reddit
    return Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )


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
        "limit": min(limit, 25),
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


def _public_comments(post, headers):
    permalink = post.get("permalink", "")
    if not permalink:
        return []
    url = f"{PUBLIC_BASE}{permalink}.json"
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


def _public_search(idea, profile):
    load_dotenv()
    headers = {"User-Agent": _user_agent()}
    total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
    response = requests.get(
        f"{PUBLIC_BASE}/search.json",
        headers=headers,
        params=_search_params(idea, total_posts),
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    records = []
    children = data.get("data", {}).get("children", [])[:total_posts]
    for child in children:
        post = child.get("data", {})
        if not post:
            continue
        records.append(_post_record(post))
        for comment in _public_comments(post, headers):
            records.append(_comment_record(post, comment))
    return records


def _use_praw():
    load_dotenv()
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return False
    if client_id == "your_reddit_app_client_id" or client_secret == "your_reddit_app_client_secret":
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
