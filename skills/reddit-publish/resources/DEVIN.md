# Devin Runtime Guide for reddit-publish

## Phase 1 — Preflight

```bash
python "<skill_dir>/scripts/preflight.py"
```

Only proceed when `deps_ok` and `reddit_ok` are true. `ai_ok` is required for AI-generated drafts; `image_ok` is required for AI image generation.

## Phase 2 — Research

```bash
python "<skill_dir>/scripts/research.py" "<topic>" --subreddit r/AskReddit --suggest-subreddit
```

If no subreddit is known, omit `--subreddit` and use `--suggest-subreddit`. Note `records_path` from the `done` event.

## Phase 3 — Draft

```bash
python "<skill_dir>/scripts/draft.py" "<records_path>" --style casual --language en
```

If the research output had no target subreddit, pass `--subreddit r/YourChoice`.

## Phase 4 — Publish (dry-run first)

```bash
python "<skill_dir>/scripts/publish.py" "<draft_path>" --dry-run
python "<skill_dir>/scripts/publish.py" "<draft_path>"
```

## Phase 5 — Surface

Tell the user the post URL and title. Do not paste full JSON.
