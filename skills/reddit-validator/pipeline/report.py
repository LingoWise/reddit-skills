import re
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from .paths import reports_dir


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Reddit Validator — {{ idea }}</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 760px; margin: 2rem auto; padding: 1rem; line-height: 1.6; color: #222; }
    h1, h2 { border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3rem; }
    .score { font-size: 2.5rem; font-weight: bold; color: #4a4; }
    .score.weak { color: #c90; }
    .score.nogo { color: #c44; }
    .meta { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }
    .section { margin-bottom: 2rem; }
    ul { padding-left: 1.2rem; }
    li { margin-bottom: 0.4rem; }
    .tag-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.5rem; }
    .tag { background: #f4f4f4; border-radius: 4px; padding: 0.5rem; text-align: center; }
  </style>
</head>
<body>
  <h1>Reddit Validation Report</h1>
  <p class="meta">Idea: <strong>{{ idea }}</strong> &middot; Run: {{ run_id }} &middot; {{ timestamp }}</p>

  <div class="section">
    <h2>Overall Score</h2>
    <div class="score {{ score_class }}">{{ score }} / 100</div>
    <p>{{ interpretation }}</p>
  </div>

  <div class="section">
    <h2>Top Pain Points</h2>
    <ul>
    {% for p in pain_points %}
      <li>{{ p.text }} (weight {{ p.weight }})</li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>Existing Solutions</h2>
    <ul>
    {% for s in existing_solutions %}
      <li>{{ s }}</li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>Opportunities</h2>
    <ul>
    {% for o in opportunities %}
      <li>{{ o.text }} (weight {{ o.weight }})</li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>Recommendations</h2>
    <ul>
    {% for r in recommendations %}
      <li>{{ r }}</li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>Comment Tag Analysis</h2>
    <div class="tag-grid">
    {% for tag, count in comment_tags.items() %}
      <div class="tag">{{ tag }}: {{ count }}</div>
    {% endfor %}
    </div>
  </div>
</body>
</html>
"""


def _score_class(score):
    if score >= 75:
        return "strong"
    if score >= 50:
        return "promising"
    if score >= 30:
        return "weak"
    return "nogo"


def _interpretation(score):
    if score >= 75:
        return "Strong signal: pain and demand are clearly present."
    if score >= 50:
        return "Promising: there is real interest, but execution and positioning will matter."
    if score >= 30:
        return "Weak: the demand exists but is fragmented or already well served."
    return "Likely no-go: insufficient or negative market signal."


def _safe_filename(text):
    return re.sub(r"[^\w\-]+", "_", text).strip("_")[:50]


def render(analysis, idea, run_id, profile):
    ctx = {
        "idea": idea,
        "run_id": run_id,
        "score": analysis.get("score", 0),
        "score_class": _score_class(analysis.get("score", 0)),
        "interpretation": _interpretation(analysis.get("score", 0)),
        "pain_points": analysis.get("pain_points", []),
        "existing_solutions": analysis.get("existing_solutions", []),
        "opportunities": analysis.get("opportunities", []),
        "recommendations": analysis.get("recommendations", []),
        "comment_tags": analysis.get("comment_tags", {}),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    html = Template(TEMPLATE).render(**ctx)
    path = reports_dir() / f"{_safe_filename(idea)}_{run_id}.html"
    path.write_text(html)
    return str(path)
