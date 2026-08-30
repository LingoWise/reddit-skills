# Failure recovery

| Error / symptom | Likely cause | Fix |
| --- | --- | --- |
| `deps_ok: false` | Missing Python packages | `uv pip install -r skills/reddit-interact/requirements.txt` |
| `reddit_ok: false` | Stale session or missing credentials | Re-run `reddit-auth/scripts/login.py` or check `.env` |
| `code: interact_error` | Reddit rejected the action (deleted content, permissions, rate limit) | Check the error message; wait and retry if rate limited |
| `code: text_missing` | Neither `--text` nor `--text-file` provided | Provide text via one of the flags |
| `code: auth_failure` | Browser session expired | Re-run `reddit-auth/scripts/login.py` |
