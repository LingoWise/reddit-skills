# Devin Runtime Guide for reddit-interact

## Phase 1 — Preflight

Run:

```bash
python "skills/reddit-interact/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true.

## Phase 2 — Pick an action

### Comment on a post

```bash
python "skills/reddit-interact/scripts/comment.py" "<post_url_or_id>" --text "Your comment"
```

For long comments, use `--text-file path/to/comment.txt` instead of `--text`.

### Reply to a comment

```bash
python "skills/reddit-interact/scripts/reply.py" "<comment_url_or_id>" --text "Your reply"
```

### Upvote

```bash
python "skills/reddit-interact/scripts/upvote.py" "<url_or_id>"
```

### Downvote

```bash
python "skills/reddit-interact/scripts/downvote.py" "<url_or_id>"
```

### Save / Unsave

```bash
python "skills/reddit-interact/scripts/save.py" "<url_or_id>"
python "skills/reddit-interact/scripts/save.py" "<url_or_id>" --unsave
```

## Phase 3 — Read output

Each script prints a single JSON line:

```json
{"event": "done", "success": true, "action": "upvote", "thing_id": "t3_abc"}
```

If `success` is false, read `error` and `code`.

## Phase 4 — Surface results

Report the action result to the user. Do not dump full JSON.
