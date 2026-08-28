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
