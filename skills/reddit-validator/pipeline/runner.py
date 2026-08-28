import json
import time
import uuid
from datetime import datetime
from pathlib import Path

from .config import get_profile
from .paths import checkpoints_dir, reports_dir


def _default_scrape(idea, profile):
    from .scraper import scrape
    return scrape(idea, profile)


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
    return event


def _stage_event(step, progress, message=""):
    return {
        "event": "stage",
        "step": step,
        "progress": progress,
        "message": message,
    }


def run(
    idea,
    profile_name,
    log_path=None,
    run_id=None,
    scrape_fn=None,
    analyze_fn=None,
    report_fn=None,
):
    profile = get_profile(profile_name)
    if run_id is None:
        run_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    if log_path is None:
        log_path = Path(reports_dir()).parent / "logs" / f"run_{run_id}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

    scrape_fn = scrape_fn or _default_scrape
    analyze_fn = analyze_fn or _default_analyze
    report_fn = report_fn or _default_report

    start = time.time()
    yield _emit(
        log_path,
        {
            "event": "run_started",
            "run_id": run_id,
            "profile": profile_name,
            "idea": idea,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    analysis = None
    report_path = None
    try:
        yield _emit(log_path, _stage_event("scrape_data", 0.0, "scraping Reddit"))
        records = scrape_fn(idea, profile)
        yield _emit(log_path, _stage_event("scrape_data", 1.0, f"collected {len(records)} records"))

        yield _emit(log_path, _stage_event("analyze", 0.0, "running LLM analysis"))
        analysis = analyze_fn(records, idea, profile)
        yield _emit(log_path, _stage_event("analyze", 1.0, "analysis complete"))

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
                "pain_points": analysis.get("pain_points", [])[:3],
                "opportunities": analysis.get("opportunities", [])[:3],
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
