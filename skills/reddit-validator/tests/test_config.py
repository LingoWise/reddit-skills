import pytest

from pipeline.config import get_profile


def test_get_profile_returns_defaults():
    p = get_profile("standard")
    assert p["posts_per_subreddit"] == 25
    assert p["subreddits"] == 5
    assert p["llm_agents"] == 3
    assert p["timeout"] == 1800


def test_get_profile_fast_and_deep():
    fast = get_profile("fast")
    assert fast["posts_per_subreddit"] == 5
    deep = get_profile("deep")
    assert deep["posts_per_subreddit"] == 100


def test_get_profile_invalid():
    with pytest.raises(ValueError):
        get_profile("slow")
