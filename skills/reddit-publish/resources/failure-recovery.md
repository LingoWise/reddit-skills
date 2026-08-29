# Failure recovery

| Error / symptom | Likely cause | Fix |
| --- | --- | --- |
| `deps_ok: false` | Missing Python packages | `uv pip install -r skills/reddit-publish/requirements.txt` |
| `reddit_ok: false` | Stale session or missing credentials | Re-run `reddit-auth/scripts/login.py` or check `.env` |
| `ai_ok: false` | No `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | Set as shell environment variables (not `.env`) |
| `image_ok: false` | No `OPENAI_API_KEY` for image generation | Set `OPENAI_API_KEY` or provide `--image-path` / `--image-url` |
| `code: auth_failure` | Browser session expired | Re-run `reddit-auth/scripts/login.py` |
| `code: not_found` | Subreddit does not exist or is private | Check the subreddit name |
| `code: rate_limited` | Too many requests | Wait and retry |
| `code: publish_rejected` | Subreddit rules (title too long, missing flair, etc.) | Edit the draft manually and retry |
| `code: image_invalid` | Bad image URL or unsupported format | Try a different image or convert to PNG/JPG |
| `code: draft_error` | LLM returned invalid JSON | Re-run with a simpler topic or style |
