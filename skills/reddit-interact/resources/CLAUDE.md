# Claude Code Runtime Guide for reddit-interact

## Phase 1 — Preflight

Run with the `Bash` tool:

```bash
python "skills/reddit-interact/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true.

## Phase 2 — Pick an action

### Comment on a post

```bash
python "skills/reddit-interact/scripts/comment.py" "<post_url_or_id>" --text "Your comment" --dry-run
python "skills/reddit-interact/scripts/comment.py" "<post_url_or_id>" --text "Your comment"
```

### Reply to a comment

```bash
python "skills/reddit-interact/scripts/reply.py" "<comment_url_or_id>" --text "Your reply" --dry-run
python "skills/reddit-interact/scripts/reply.py" "<comment_url_or_id>" --text "Your reply"
```

### Upvote

```bash
python "skills/reddit-interact/scripts/upvote.py" "<url_or_id>" --dry-run
python "skills/reddit-interact/scripts/upvote.py" "<url_or_id>"
```

### Downvote

```bash
python "skills/reddit-interact/scripts/downvote.py" "<url_or_id>" --dry-run
python "skills/reddit-interact/scripts/downvote.py" "<url_or_id>"
```

### Save

```bash
python "skills/reddit-interact/scripts/save.py" "<url_or_id>" --dry-run
python "skills/reddit-interact/scripts/save.py" "<url_or_id>"
```

### Unsave

```bash
python "skills/reddit-interact/scripts/save.py" "<url_or_id>" --unsave
```

## Phase 3 — Read output

The `Bash` tool returns a single JSON line:

```json
{"event": "done", "success": true, "comment_id": "abc", "permalink": "/r/test/..."}
```

If `success` is false, read `error` and `code`, then check `resources/failure-recovery.md`.

## Phase 4 — Surface results

Report the action result to the user. Do not dump full JSON.
