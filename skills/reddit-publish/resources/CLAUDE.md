# Claude Code Runtime Guide for reddit-publish

## Phase 1 — Preflight

Run with the `Bash` tool:

```bash
python "<skill_dir>/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true.

## Phase 2 — Research

```bash
python "<skill_dir>/scripts/research.py" "<topic>" --suggest-subreddit
```

## Phase 3 — Draft

```bash
python "<skill_dir>/scripts/draft.py" "<records_path>" --style casual --language en
```

## Phase 4 — Publish

```bash
python "<skill_dir>/scripts/publish.py" "<draft_path>" --dry-run
python "<skill_dir>/scripts/publish.py" "<draft_path>"
```

## Phase 5 — Surface

Return the post URL and title. If `success` is false, read `code` and `error`, then check `resources/failure-recovery.md`.
