import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.scraper import scrape


class FakeComment:
    def __init__(self, body, author="user", score=1):
        self.id = "c1"
        self.body = body
        self.author = author
        self.score = score
        self.permalink = "/r/test/comments/p1/test/c1/"


class FakeComments:
    def __init__(self, comments):
        self._comments = comments

    def replace_more(self, limit=None):
        pass

    def list(self):
        return self._comments


class FakeSubmission:
    def __init__(self, title="Test post", body="post body", comments=None):
        self.id = "p1"
        self.title = title
        self.selftext = body
        self.subreddit = "test"
        self.author = "op"
        self.score = 10
        self.url = "https://reddit.com/r/test/comments/p1/test/"
        self.permalink = "/r/test/comments/p1/test/"
        self.comments = FakeComments(comments or [FakeComment("need this")])


class FakeSubreddit:
    def __init__(self, submissions, name="all"):
        self._submissions = submissions
        self.name = name

    def search(self, idea, sort=None, time_filter=None, limit=None):
        return self._submissions[:limit]


class FakeReddit:
    def __init__(self, submissions):
        self._submissions = submissions
        self.searched_subs = []

    def subreddit(self, name):
        self.searched_subs.append(name)
        return FakeSubreddit(self._submissions, name=name)


def test_scrape_returns_comment_records():
    submission = FakeSubmission(
        title="Best app for X?",
        body="Looking for ...",
        comments=[FakeComment("I need this so much", "u1", 5)],
    )
    client = FakeReddit([submission])

    records = scrape("app for X", {"subreddits": 1, "posts_per_subreddit": 1}, client=client)

    assert len(records) == 2
    assert records[0]["is_comment"] is True
    assert records[0]["title"] == "Best app for X?"
    assert records[0]["text"] == "I need this so much"
    assert records[0]["subreddit"] == "test"
    assert records[1]["is_comment"] is False


def test_scrape_targets_specific_subreddits():
    """When subreddits are specified, the scraper searches each one individually."""
    submission = FakeSubmission(
        title="IELTS speaking practice",
        body="Need feedback on my speaking",
        comments=[FakeComment("I struggle with fluency", "u1", 3)],
    )
    client = FakeReddit([submission])

    records = scrape(
        "AI IELTS grading",
        {"posts_per_subreddit": 5},
        client=client,
        subreddits="IELTS,TOEFL",
    )

    # Should have searched two specific subreddits, not "all"
    assert client.searched_subs == ["IELTS", "TOEFL"]
    # Each sub returns 1 post + 1 comment = 2 records, 2 subs = 4 records
    assert len(records) == 4
    assert all(r["subreddit"] == "test" for r in records)  # FakeSubreddit always returns "test"


def test_scrape_without_subreddits_searches_all():
    """Without subreddits, the scraper falls back to /r/all search."""
    submission = FakeSubmission(title="test", body="body")
    client = FakeReddit([submission])

    scrape("test idea", {"subreddits": 1, "posts_per_subreddit": 1}, client=client)

    assert client.searched_subs == ["all"]


def test_normalize_subreddits():
    from pipeline.scraper import _normalize_subreddits

    assert _normalize_subreddits(None) == []
    assert _normalize_subreddits("") == []
    assert _normalize_subreddits("IELTS") == ["IELTS"]
    assert _normalize_subreddits("r/IELTS") == ["IELTS"]
    assert _normalize_subreddits("IELTS, TOEFL") == ["IELTS", "TOEFL"]
    assert _normalize_subreddits(["IELTS", "TOEFL"]) == ["IELTS", "TOEFL"]
    assert _normalize_subreddits(["r/IELTS", " TOEFL "]) == ["IELTS", "TOEFL"]
