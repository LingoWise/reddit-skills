# Devin Runtime Guide for reddit-explore

## Phase 1 — Preflight

Run:

```bash
python "<skill_dir>/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true.

## Phase 2 — Pick a capability

### Search

```bash
python "<skill_dir>/scripts/search.py" "<query>" --subreddits "IELTS,TOEFL" --limit 10
```

### Browse a subreddit

```bash
python "<skill_dir>/scripts/subreddit.py" "<name>" --sort hot --limit 25
```

### Post details

```bash
python "<skill_dir>/scripts/post.py" "<url_or_id>" --comments 10
```

### User profile

```bash
python "<skill_dir>/scripts/user.py" "<name>" --section overview --limit 25
```

## Phase 3 — Read output

Each script prints a single JSON line:

```json
{"event": "done", "success": true, "count": 10, "records_path": "/path/to/.reddit-skills/records/search_xxx.json"}
```

If `success` is false, read `error` and `code`.

## Phase 4 — Surface results

Summarize the records for the user. Do not dump full JSON.
