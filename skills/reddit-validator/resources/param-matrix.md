# Parameter matrix

| Profile | Posts per subreddit | Subreddits | LLM agents | Approx. timeout | Best for |
| --- | --- | --- | --- | --- | --- |
| fast | 5 | 3 | 1 | 5 min | Smoke test, dev iteration |
| standard | 25 | 5 | 3 | 30 min | Regular validation |
| deep | 100 | 10 | 5 | 60 min | High-stakes decisions |

These numbers are approximate defaults. They may be tuned in `pipeline/paths.py` or the runner config.
