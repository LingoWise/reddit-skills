import importlib.util
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

from .config import get_profile
from .paths import checkpoints_dir, logs_dir, reports_dir


def _load_auth():
    """Load the reddit-auth pipeline module from the sibling skill directory."""
    auth_path = Path(__file__).resolve().parent.parent.parent / "reddit-auth" / "pipeline" / "auth.py"
    spec = importlib.util.spec_from_file_location("reddit_auth_pipeline_auth", auth_path)
    auth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth)
    return auth


def _default_analyze(records, idea, profile):
    from .analyzer import analyze
    return analyze(records, idea, profile)


def _default_report(analysis, idea, run_id, profile):
    from .report import render
    return render(analysis, idea, run_id, profile)


def _emit(log_path, event):
    if log_path:
        with open(log_path, "a") as f:
            f.write(json.dumps(event) + "\n")
            f.flush()
    return event


def _stage_event(step, progress, message=""):
    return {
        "event": "stage",
        "step": step,
        "progress": progress,
        "message": message,
    }


def _safe_idea(idea):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in idea).strip("_")[:50]


def run(
    idea,
    profile_name,
    log_path=None,
    run_id=None,
    scrape_fn=None,
    analyze_fn=_default_analyze,
    report_fn=_default_report,
    subreddits=None,
):
    profile = get_profile(profile_name)
    if run_id is None:
        run_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    if log_path is None:
        log_path = logs_dir() / f"run_{run_id}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

    client = None
    auth = None
    is_browser = False
    if scrape_fn is None:
        auth = _load_auth()
        is_browser = auth.resolve_strategy() == "browser"

        def _default_scrape(idea, profile):
            from .scraper import scrape
            return scrape(idea, profile, client=client, subreddits=subreddits)

        scrape_fn = _default_scrape

    start = time.time()
    run_started = {
        "event": "run_started",
        "run_id": run_id,
        "profile": profile_name,
        "idea": idea,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if subreddits:
        run_started["subreddits"] = subreddits
    yield _emit(log_path, run_started)

    if auth is not None and client is None:
        if is_browser:
            yield _emit(
                log_path,
                _stage_event(
                    "login",
                    0.0,
                    "logging in via reddit-auth",
                ),
            )

        client = auth.get_client()

        if is_browser and client is not None and hasattr(client, "page"):
            username = getattr(client, "username", None) or "unknown"
            yield _emit(
                log_path,
                _stage_event(
                    "login",
                    1.0,
                    f"logged in as {username}",
                ),
            )

    analysis = None
    report_path = None
    records_path = None
    try:
        try:
            yield _emit(log_path, _stage_event("scrape_data", 0.0, "scraping Reddit"))
            records = scrape_fn(idea, profile)
            records_path = checkpoints_dir() / f"{run_id}_records.json"
            records_path.write_text(json.dumps(records, indent=2, default=str))
            yield _emit(
                log_path,
                _stage_event("scrape_data", 1.0, f"collected {len(records)} records"),
            )
        finally:
            if client is not None and hasattr(client, "close"):
                try:
                    client.close()
                except Exception:
                    pass

        if analyze_fn is None:
            elapsed = time.time() - start
            yield _emit(
                log_path,
                {
                    "event": "done",
                    "success": True,
                    "run_id": run_id,
                    "idea": idea,
                    "needs_analysis": True,
                    "records_path": str(records_path),
                    "execution_time": round(elapsed, 2),
                },
            )
            return

        yield _emit(log_path, _stage_event("analyze", 0.0, "running LLM analysis"))
        analysis = analyze_fn(records, idea, profile)
        yield _emit(log_path, _stage_event("analyze", 1.0, "analysis complete"))

        if report_fn is None:
            elapsed = time.time() - start
            yield _emit(
                log_path,
                {
                    "event": "done",
                    "success": True,
                    "run_id": run_id,
                    "idea": idea,
                    "needs_report": True,
                    "analysis": analysis,
                    "records_path": str(records_path),
                    "execution_time": round(elapsed, 2),
                },
            )
            return

        yield _emit(log_path, _stage_event("report", 0.0, "rendering HTML report"))
        report_path = report_fn(analysis, idea, run_id, profile)
        yield _emit(log_path, _stage_event("report", 1.0, f"report at {report_path}"))

        elapsed = time.time() - start
        yield _emit(
            log_path,
            {
                "event": "done",
                "success": True,
                "run_id": run_id,
                "idea": idea,
                "report_path": report_path,
                "score": analysis.get("score", 0),
                "market_snapshot": analysis.get("market_snapshot", [])[:5],
                "pain_points": analysis.get("pain_points", [])[:3],
                "opportunities": analysis.get("opportunities", [])[:3],
                "how_to_win": analysis.get("how_to_win", [])[:3],
                "execution_time": round(elapsed, 2),
            },
        )
    except Exception as exc:
        failed_step = "scrape_data" if analysis is None else "analyze" if report_path is None else "report"
        elapsed = time.time() - start
        yield _emit(
            log_path,
            {
                "event": "done",
                "success": False,
                "run_id": run_id,
                "idea": idea,
                "error": f"{exc}",
                "failed_step": failed_step,
                "execution_time": round(elapsed, 2),
            },
        )


def resume(run_id, idea, profile_name, **kwargs):
    checkpoint = checkpoints_dir() / f"{run_id}.json"
    if not checkpoint.exists():
        raise FileNotFoundError(f"No checkpoint for {run_id}")
    state = json.loads(checkpoint.read_text())
    return run(idea, profile_name, run_id=run_id, **kwargs)
