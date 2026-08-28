import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.records import comment_record, post_record, user_record


def test_post_record():
    post = {
        "id": "p1",
        "subreddit": "test",
        "title": "Best app for X?",
        "selftext": "Looking for ...",
        "author": "op",
        "score": 10,
        "url": "https://reddit.com/r/test/comments/p1/test/",
        "permalink": "/r/test/comments/p1/test/",
    }
    record = post_record(post)
    assert record == {
        "id": "p1",
        "post_id": "p1",
        "subreddit": "r/test",
        "title": "Best app for X?",
        "post_text": "Looking for ...",
        "text": "Looking for ...",
        "author": "op",
        "score": 10,
        "url": "https://reddit.com/r/test/comments/p1/test/",
        "is_comment": False,
    }


def test_comment_record():
    post = {
        "id": "p1",
        "subreddit": "test",
        "title": "Best app for X?",
        "selftext": "Looking for ...",
        "author": "op",
        "score": 10,
        "url": "https://reddit.com/r/test/comments/p1/test/",
        "permalink": "/r/test/comments/p1/test/",
    }
    comment = {
        "id": "c1",
        "body": "I need this",
        "author": "u1",
        "score": 5,
        "permalink": "/r/test/comments/p1/test/c1/",
    }
    record = comment_record(post, comment)
    assert record == {
        "id": "c1",
        "post_id": "p1",
        "subreddit": "r/test",
        "title": "Best app for X?",
        "post_text": "Looking for ...",
        "text": "I need this",
        "author": "u1",
        "score": 5,
        "url": "https://www.reddit.com/r/test/comments/p1/test/c1/",
        "is_comment": True,
    }


def test_user_record_post():
    item = {
        "kind": "t3",
        "data": {
            "id": "p2",
            "subreddit": "test",
            "title": "My post",
            "selftext": "hello",
            "author": "u2",
            "score": 7,
            "url": "https://reddit.com/r/test/comments/p2/my/",
            "permalink": "/r/test/comments/p2/my/",
        },
    }
    record = user_record(item)
    assert record["is_comment"] is False
    assert record["id"] == "p2"
    assert record["post_id"] == "p2"
    assert record["text"] == "hello"


def test_user_record_comment():
    item = {
        "kind": "t1",
        "data": {
            "id": "c2",
            "link_id": "t3_p2",
            "subreddit": "test",
            "link_title": "My post",
            "link_selftext": "hello",
            "body": "great post",
            "author": "u3",
            "score": 3,
            "permalink": "/r/test/comments/p2/my/c2/",
        },
    }
    record = user_record(item)
    assert record["is_comment"] is True
    assert record["id"] == "c2"
    assert record["post_id"] == "p2"
    assert record["text"] == "great post"
