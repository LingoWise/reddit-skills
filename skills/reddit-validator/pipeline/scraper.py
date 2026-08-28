import os
from dotenv import load_dotenv


def scrape(idea, profile, client=None):
    load_dotenv()
    if client is None:
        from praw import Reddit
        client = Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )

    total_posts = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
    submissions = client.subreddit("all").search(
        idea,
        sort="relevance",
        time_filter="all",
        limit=total_posts,
    )

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
