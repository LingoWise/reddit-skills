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
    def __init__(self, submissions):
        self._submissions = submissions

    def search(self, idea, sort=None, time_filter=None, limit=None):
        return self._submissions[:limit]


class FakeReddit:
    def __init__(self, submissions):
        self._submissions = submissions

    def subreddit(self, name):
        return FakeSubreddit(self._submissions)


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
