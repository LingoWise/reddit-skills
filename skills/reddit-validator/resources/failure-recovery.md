# Failure recovery

| Error / symptom | Likely cause | Fix |
| --- | --- | --- |
| 401 on Reddit auth | Wrong Reddit app type or bad credentials | Verify the app is "script" type at <https://www.reddit.com/prefs/apps> and credentials are correct |
| 429 / rate limited | Too many requests | Wait and resume from checkpoint with `recover.py --resume-last` |
| `llm_ok: false` | Bad base URL or no quota | Check `OPENAI_BASE_URL` ends with `/v1`; verify billing and quota |
| `deps_ok: false` | Missing Python packages | Run `pip install -r <skill_dir>/requirements.txt` |
| Malformed JSON from LLM | Model output invalid JSON | Re-run the analysis step; if persistent, switch model or simplify the prompt |
| Missing report file | Pipeline crashed before report | Resume from the latest checkpoint |
| `env_ok: false` | Missing environment variables | Create `.env` in cwd or `<skill_dir>/.env` with all required keys |
