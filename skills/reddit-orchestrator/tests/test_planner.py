import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.planner import match_workflow, plan


class TestMatchWorkflow:
    def test_validate_idea_english(self):
        result = match_workflow("validate my idea: AI-powered language tutor")
        assert result is not None
        assert result[0] == "validate_idea"
        assert "AI-powered language tutor" in result[1]["idea"]

    def test_validate_idea_chinese(self):
        result = match_workflow("验证创业想法：AI英语家教")
        assert result is not None
        assert result[0] == "validate_idea"

    def test_brand_growth_english(self):
        result = match_workflow("grow my brand Acme on subreddits python, learnpython")
        assert result is not None
        assert result[0] == "brand_growth"
        assert "Acme" in result[1]["brand"]

    def test_brand_growth_chinese(self):
        result = match_workflow("推广品牌 Acme 在 reddit 上")
        assert result is not None
        assert result[0] == "brand_growth"

    def test_track_trends_english(self):
        result = match_workflow("track trends for AI tools on Reddit")
        assert result is not None
        assert result[0] == "track_trends"
        assert "AI tools" in result[1]["topic"]

    def test_track_trends_chinese(self):
        result = match_workflow("看看 Reddit 上 AI 工具的热门趋势")
        assert result is not None
        assert result[0] == "track_trends"

    def test_track_trends_chinese_no_colon(self):
        result = match_workflow("热门的AI工具")
        assert result is not None
        assert result[0] == "track_trends"
        assert "AI" in result[1]["topic"]

    def test_engage_community_english(self):
        result = match_workflow("engage with communities about my product Acme")
        assert result is not None
        assert result[0] == "engage_community"
        assert "Acme" in result[1]["brand"]

    def test_engage_community_chinese(self):
        result = match_workflow("在 Reddit 社区互动讨论 Acme")
        assert result is not None
        assert result[0] == "engage_community"

    def test_no_match_returns_none(self):
        assert match_workflow("what is the weather today?") is None

    def test_no_match_random_text(self):
        assert match_workflow("hello world") is None


class TestPlan:
    def test_plan_with_known_workflow(self):
        p = plan("validate my idea: test idea")
        assert p["workflow"] == "validate_idea"
        assert "plan_id" in p
        assert "steps" in p
        assert len(p["steps"]) > 0

    def test_plan_with_forced_workflow(self):
        p = plan("some text", workflow="track_trends")
        assert p["workflow"] == "track_trends"

    def test_plan_unknown_workflow_raises(self):
        with pytest.raises(ValueError, match="Unknown workflow"):
            plan("some text", workflow="nonexistent")

    def test_plan_no_match_no_llm_returns_error(self, monkeypatch):
        monkeypatch.setattr("pipeline.planner._llm_available", lambda: (False, "no key"))
        result = plan("what is the weather today?")
        assert "error" in result
        assert "could not match" in result["error"].lower()

    def test_plan_forced_brand_growth_no_subreddits(self):
        """Forcing brand_growth without matching pattern should not crash."""
        p = plan("some random text", workflow="brand_growth")
        assert p["workflow"] == "brand_growth"
        assert len(p["steps"]) >= 5
