import pytest

from pipeline.report import render


def test_render_creates_html_report(tmp_path):
    analysis = {
        "score": 72,
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
