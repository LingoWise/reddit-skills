import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.workflows import (
    validate_idea,
    brand_growth,
    track_trends,
    engage_community,
    build_plan,
)


def test_validate_idea_returns_valid_plan():
    plan = validate_idea("AI language tutor")
    assert plan["workflow"] == "validate_idea"
    assert plan["request"] == "AI language tutor"
    assert len(plan["steps"]) == 3
    assert plan["steps"][0]["name"] == "scrape"
    assert plan["steps"][0]["skill"] == "reddit-validator"
    assert plan["steps"][0]["depends_on"] == []
    assert plan["steps"][1]["depends_on"] == ["scrape"]
    assert plan["steps"][2]["depends_on"] == ["render"]


def test_validate_idea_with_profile():
    plan = validate_idea("test idea", profile="fast")
    scrape_cmd = plan["steps"][0]["command"]
    assert "--profile" in scrape_cmd
    assert "fast" in scrape_cmd


def test_validate_idea_with_subreddits():
    plan = validate_idea("test idea", subreddits="IELTS,TOEFL")
    scrape_cmd = plan["steps"][0]["command"]
    assert "--subreddits" in scrape_cmd
    assert "IELTS,TOEFL" in scrape_cmd


def test_brand_growth_returns_valid_plan():
    plan = brand_growth("MyBrand", "python,learnpython")
    assert plan["workflow"] == "brand_growth"
    assert len(plan["steps"]) >= 5
    step_names = [s["name"] for s in plan["steps"]]
    assert "research_subreddits" in step_names
    assert "research_content" in step_names
    assert "draft_post" in step_names
    assert "publish_post" in step_names
    assert "engage_comments" in step_names


def test_brand_growth_has_checkpoint_before_publish():
    plan = brand_growth("MyBrand", "python")
    draft_step = next(s for s in plan["steps"] if s["name"] == "draft_post")
    publish_step = next(s for s in plan["steps"] if s["name"] == "publish_post")
    assert draft_step["checkpoint"] is True
    assert publish_step["depends_on"] == ["draft_post"]


def test_track_trends_returns_valid_plan():
    plan = track_trends("AI tools")
    assert plan["workflow"] == "track_trends"
    assert len(plan["steps"]) == 2
    assert plan["steps"][0]["name"] == "search_trends"
    assert plan["steps"][0]["skill"] == "reddit-explore"
    assert plan["steps"][1]["name"] == "summarize"
    assert plan["steps"][1]["depends_on"] == ["search_trends"]


def test_engage_community_returns_valid_plan():
    plan = engage_community("MyBrand")
    assert plan["workflow"] == "engage_community"
    assert len(plan["steps"]) >= 3
    step_names = [s["name"] for s in plan["steps"]]
    assert "find_discussions" in step_names
    assert "engage" in step_names
    assert "upvote_relevant" in step_names


def test_engage_community_has_checkpoint():
    plan = engage_community("MyBrand")
    find_step = next(s for s in plan["steps"] if s["name"] == "find_discussions")
    engage_step = next(s for s in plan["steps"] if s["name"] == "engage")
    assert find_step["checkpoint"] is True
    assert engage_step["depends_on"] == ["find_discussions"]


def test_build_plan_validates_workflow_name():
    with pytest.raises(ValueError, match="Unknown workflow"):
        build_plan("nonexistent", "request text", {})


def test_build_plan_passes_params():
    plan = build_plan("validate_idea", "test", {"idea": "my idea", "profile": "deep"})
    assert plan["workflow"] == "validate_idea"
    assert plan["request"] == "test"
    scrape_cmd = plan["steps"][0]["command"]
    assert "deep" in scrape_cmd


def test_every_step_has_required_fields():
    for plan_fn, args in [
        (validate_idea, ("idea",)),
        (brand_growth, ("brand", "subs")),
        (track_trends, ("topic",)),
        (engage_community, ("brand",)),
    ]:
        plan = plan_fn(*args)
        for step in plan["steps"]:
            assert "name" in step
            assert "skill" in step
            assert "description" in step
            assert "command" in step
            assert "depends_on" in step
            assert "output_key" in step
            assert "condition" in step
            assert "retry" in step
            assert "checkpoint" in step
            assert isinstance(step["command"], list)
            assert isinstance(step["depends_on"], list)
            assert isinstance(step["retry"], dict)
