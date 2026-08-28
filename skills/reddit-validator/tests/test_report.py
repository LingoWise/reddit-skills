import pytest

from pipeline.report import render


def test_render_creates_html_report(tmp_path):
    analysis = {
        "score": 72,
        "language": "en",
        "original_idea": "AI todo app",
        "pain_points": [{"text": "pain A", "weight": 3}, {"text": "pain B", "weight": 2}],
        "opportunities": [{"text": "opportunity A", "weight": 2}],
        "recommendations": ["Launch a focused landing page"],
        "existing_solutions": ["incumbent X"],
        "comment_tags": {
            "positive": 10,
            "negative": 5,
            "question": 3,
            "suggestion": 2,
        },
    }

    path = render(analysis, "AI todo app", "r1", {})
    html = open(path).read()
    assert "AI todo app" in html
    assert "72" in html
    assert "pain A" in html
    assert "opportunity A" in html
    assert path.endswith(".html")


def test_render_with_citations_and_analytics(tmp_path):
    analysis = {
        "score": 65,
        "language": "en",
        "original_idea": "AI grading tool",
        "analysis_method": {"name": "Jobs-to-be-Done", "rationale": "Fits SaaS product"},
        "market_snapshot": [{"text": "Users complain about X", "sources": [{"subreddit": "r/IELTS", "url": "https://reddit.com/r/IELTS/1"}]}],
        "pain_points": [{"text": "pain A", "weight": 4, "sources": [{"subreddit": "r/TOEFL", "url": "https://reddit.com/r/TOEFL/2"}]}],
        "existing_solutions": [{"name": "TestGlider", "description": "AI speaking practice", "sources": [{"subreddit": "r/IELTS", "url": "https://reddit.com/r/IELTS/3"}]}],
        "opportunities": [{"text": "gap A", "weight": 3, "sources": [{"subreddit": "r/TOEFL", "url": "https://reddit.com/r/TOEFL/4"}]}],
        "how_to_win": ["Position as calibrated engine"],
        "recommendations": ["Build MVP"],
        "comment_tags": {"positive": 5, "negative": 2, "question": 1, "suggestion": 0},
    }
    records = [
        {"subreddit": "r/IELTS", "is_comment": False, "text": "post", "url": "https://reddit.com/r/IELTS/1"},
        {"subreddit": "r/IELTS", "is_comment": True, "text": "comment", "url": "https://reddit.com/r/IELTS/2"},
        {"subreddit": "r/TOEFL", "is_comment": True, "text": "comment", "url": "https://reddit.com/r/TOEFL/1"},
    ]

    path = render(analysis, "AI grading tool", "r2", {}, records=records, language="en")
    html = open(path).read()
    assert "Jobs-to-be-Done" in html
    assert "https://reddit.com/r/IELTS/1" in html
    assert "TestGlider" in html
    assert "Total records" in html or "total_records" in html.lower() or "3" in html
    assert path.endswith(".html")


def test_render_chinese_labels(tmp_path):
    analysis = {
        "score": 50,
        "language": "zh",
        "original_idea": "AI 备考系统",
        "pain_points": [{"text": "痛点 A", "weight": 3}],
        "opportunities": [{"text": "机会 A", "weight": 2}],
        "recommendations": ["建议一"],
        "existing_solutions": ["方案 X"],
        "comment_tags": {"positive": 1, "negative": 0, "question": 0, "suggestion": 0},
    }

    path = render(analysis, "AI 备考系统", "r3", {}, language="zh")
    html = open(path).read()
    assert "验证报告" in html
    assert "痛点 A" in html
    assert 'lang="zh"' in html
    assert path.endswith(".html")
