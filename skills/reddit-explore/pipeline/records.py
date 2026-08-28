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
