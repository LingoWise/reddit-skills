import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.skill_catalog import SKILLS, get_skill, catalog_summary


def test_skills_has_five_entries():
    assert len(SKILLS) == 5


def test_skills_contains_expected_names():
    names = [s["name"] for s in SKILLS]
    assert "reddit-auth" in names
    assert "reddit-validator" in names
    assert "reddit-explore" in names
    assert "reddit-publish" in names
    assert "reddit-interact" in names


def test_each_skill_has_required_fields():
    for skill in SKILLS:
        assert "name" in skill
        assert "scripts" in skill
        assert "purpose" in skill
        assert isinstance(skill["scripts"], list)
        assert len(skill["scripts"]) > 0


def test_get_skill_returns_match():
    skill = get_skill("reddit-validator")
    assert skill is not None
    assert skill["name"] == "reddit-validator"


def test_get_skill_returns_none_for_unknown():
    assert get_skill("nonexistent") is None


def test_catalog_summary_is_string():
    summary = catalog_summary()
    assert isinstance(summary, str)
    assert "reddit-validator" in summary
    assert "reddit-explore" in summary
