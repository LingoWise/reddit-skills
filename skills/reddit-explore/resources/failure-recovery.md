# Failure recovery

| Error / symptom | Likely cause | Fix |
| --- | --- | --- |
| `deps_ok: false` | Missing Python packages | Run `pip install -r <skill_dir>/requirements.txt` |
| `reddit_ok: false` | Bad credentials or stale session | Re-run `reddit-auth/scripts/login.py` or check `.env` |
| `code: not_found` | Post, user, or subreddit does not exist | Check the URL/ID/name and retry |
| `code: forbidden` | Private subreddit or banned/suspended user | Cannot access with current auth; try a public endpoint or different account |
| `code: rate_limited` | Too many requests | Wait a minute and retry |
| `code: timeout` | Network or Reddit slow | Retry with smaller `--limit` |
