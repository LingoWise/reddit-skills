PROFILES = {
    "fast": {
        "posts_per_subreddit": 5,
        "subreddits": 3,
        "llm_agents": 1,
        "timeout": 300,
    },
    "standard": {
        "posts_per_subreddit": 25,
        "subreddits": 5,
        "llm_agents": 3,
        "timeout": 1800,
    },
    "deep": {
        "posts_per_subreddit": 100,
        "subreddits": 10,
        "llm_agents": 5,
        "timeout": 3600,
    },
}


def get_profile(name):
    if name not in PROFILES:
        raise ValueError(f"Unknown profile: {name}. Choose from {list(PROFILES)}.")
    return PROFILES[name]
