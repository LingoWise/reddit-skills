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
