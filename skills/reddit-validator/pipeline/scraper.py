import importlib.util
from pathlib import Path


def _load_explorer():
    """Load the reddit-explore pipeline module from the sibling skill directory."""
    explorer_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "explorer.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_explorer", explorer_path)
    explorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(explorer)
    return explorer


def _load_client():
    """Load the reddit-explore client module."""
    client_path = Path(__file__).resolve().parent.parent.parent / "reddit-explore" / "pipeline" / "client.py"
    spec = importlib.util.spec_from_file_location("reddit_explore_pipeline_client", client_path)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    return client


def scrape(idea, profile, client=None, subreddits=None):
    """Scrape Reddit for idea validation using reddit-explore's search primitive."""
    explorer = _load_explorer()
    client_mod = _load_client()

    fetcher = None
    close_after = False
    if client is not None:
        fetcher = client_mod.Fetcher.from_existing(client)
    else:
        fetcher = client_mod.get_fetcher()
        close_after = True

    try:
        limit = profile.get("subreddits", 5) * profile.get("posts_per_subreddit", 25)
        if subreddits:
            limit = profile.get("posts_per_subreddit", 25)
        records = explorer.search_posts(
            idea,
            fetcher=fetcher,
            subreddits=subreddits,
            limit=limit,
            sort="relevance",
            time_filter="all",
            fetch_comments=True,
            comment_limit=3,
        )
        return records
    finally:
        if close_after:
            fetcher.close()
