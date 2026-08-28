import importlib.util
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from .paths import reports_dir


def _load_version():
    """Load the project version from src/common/paths.py."""
    paths_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "common" / "paths.py"
    spec = importlib.util.spec_from_file_location("reddit_skills_common_paths", paths_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.VERSION


VERSION = _load_version()


LABELS = {
    "en": {
        "title": "Reddit Validation Report",
        "idea": "Idea",
        "run_id": "Run ID",
        "date": "Date",
        "score": "Overall Score",
        "analysis_method": "Analysis Method",
        "market_snapshot": "Market Snapshot",
        "market_snapshot_desc": "Current state of the market, grounded in Reddit data.",
        "pain_points": "Top Pain Points",
        "existing_solutions": "Existing Solutions",
        "opportunities": "Opportunities",
        "how_to_win": "How to Win",
        "how_to_win_desc": "Strategic playbook — opinionated, not generic.",
        "recommendations": "Recommendations",
        "comment_tags": "Comment Tag Analysis",
        "analytics": "Data Analytics",
        "total_records": "Total records",
        "posts": "Posts",
        "comments": "Comments",
        "subreddits": "Subreddits",
        "sources": "Sources",
        "weight": "weight",
        "interpretation_strong": "Strong signal: pain and demand are clearly present.",
        "interpretation_promising": "Promising: real interest, but execution and positioning will matter.",
        "interpretation_weak": "Weak: demand exists but is fragmented or already well served.",
        "interpretation_nogo": "Likely no-go: insufficient or negative market signal.",
    },
    "zh": {
        "title": "Reddit 验证报告",
        "idea": "想法",
        "run_id": "运行 ID",
        "date": "日期",
        "score": "总分",
        "analysis_method": "分析方法",
        "market_snapshot": "市场概况",
        "market_snapshot_desc": "当前市场状态，基于 Reddit 数据。",
        "pain_points": "核心痛点",
        "existing_solutions": "现有方案",
        "opportunities": "机会",
        "how_to_win": "如何制胜",
        "how_to_win_desc": "战略建议 — 有态度，不空泛。",
        "recommendations": "行动建议",
        "comment_tags": "评论标签分析",
        "analytics": "数据分析",
        "total_records": "总记录数",
        "posts": "帖子",
        "comments": "评论",
        "subreddits": "子版块",
        "sources": "来源",
        "weight": "权重",
        "interpretation_strong": "强烈信号：痛点和需求明确存在。",
        "interpretation_promising": "有前景：存在真实兴趣，但执行和定位至关重要。",
        "interpretation_weak": "较弱：需求存在但分散或已被充分满足。",
        "interpretation_nogo": "不建议：市场信号不足或负面。",
    },
}


TEMPLATE = """<!DOCTYPE html>
<html lang="{{ lang_code }}">
<head>
  <meta charset="UTF-8">
  <title>{{ L.title }} — {{ idea }}</title>
  <style>
    :root {
      --bg: #dae0e6;
      --card: #ffffff;
      --border: #edeef0;
      --border-strong: #d7dadc;
      --text: #1a1a1b;
      --text-secondary: #3a3a3c;
      --muted: #7c7c7c;
      --accent: #ff4500;
      --accent-light: #fff1ed;
      --accent-text: #cc3700;
      --green: #46a508;
      --green-light: #e8f5e0;
      --yellow: #e8a100;
      --yellow-light: #fff8e0;
      --red: #cc2200;
      --red-light: #ffe8e0;
      --surface: #f6f7f8;
      --radius: 10px;
      --radius-sm: 6px;
      --shadow: 0 1px 3px rgba(255,69,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
      --shadow-lift: 0 2px 8px rgba(255,69,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      max-width: 820px;
      margin: 0 auto;
      padding: 2.5rem 1.25rem;
      line-height: 1.65;
      color: var(--text);
      background: var(--bg);
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    h1 {
      font-size: 1.65rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin-bottom: 0.15rem;
      color: var(--text);
    }

    h2 {
      font-size: 1.05rem;
      font-weight: 600;
      letter-spacing: -0.01em;
      margin-bottom: 0.75rem;
      padding-bottom: 0.4rem;
      border-bottom: 1px solid var(--border);
      color: var(--text);
    }

    .header {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem 1.75rem;
      margin-bottom: 1.25rem;
      box-shadow: var(--shadow);
    }

    .meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      color: var(--muted);
      font-size: 0.8rem;
      margin-top: 0.35rem;
      font-variant-numeric: tabular-nums;
    }

    .meta-row span { white-space: nowrap; }

    .original-idea {
      background: var(--accent-light);
      border-left: 3px solid var(--accent);
      padding: 0.7rem 1rem;
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      margin-top: 0.85rem;
      font-size: 0.92rem;
      color: var(--text-secondary);
    }

    .original-idea strong {
      color: var(--accent-text);
      font-weight: 600;
    }

    .score-section {
      display: flex;
      align-items: center;
      gap: 1.75rem;
    }

    .score-ring {
      width: 88px;
      height: 88px;
      flex-shrink: 0;
      position: relative;
    }

    .score-ring svg {
      width: 100%;
      height: 100%;
      transform: rotate(-90deg);
    }

    .score-ring .ring-bg {
      fill: none;
      stroke: var(--border);
      stroke-width: 6;
    }

    .score-ring .ring-fill {
      fill: none;
      stroke-width: 6;
      stroke-linecap: round;
      transition: stroke-dashoffset 0.6s ease;
    }

    .score-ring .ring-fill.strong { stroke: var(--green); }
    .score-ring .ring-fill.promising { stroke: var(--accent); }
    .score-ring .ring-fill.weak { stroke: var(--yellow); }
    .score-ring .ring-fill.nogo { stroke: var(--red); }

    .score-ring .score-number {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.7rem;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.03em;
    }

    .score-bar-wrap { flex: 1; }

    .score-bar {
      height: 6px;
      background: var(--surface);
      border-radius: 3px;
      overflow: hidden;
    }

    .score-bar-fill {
      height: 100%;
      border-radius: 3px;
      transition: width 0.6s ease;
    }

    .score-bar-fill.strong { background: var(--green); }
    .score-bar-fill.promising { background: var(--accent); }
    .score-bar-fill.weak { background: var(--yellow); }
    .score-bar-fill.nogo { background: var(--red); }

    .interpretation {
      font-size: 0.85rem;
      color: var(--muted);
      margin-top: 0.45rem;
    }

    .section {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem 1.5rem;
      margin-bottom: 1rem;
      box-shadow: var(--shadow);
    }

    .section > p.desc {
      color: var(--muted);
      font-size: 0.82rem;
      margin-bottom: 0.65rem;
      margin-top: -0.2rem;
    }

    ul {
      padding-left: 0;
      list-style: none;
    }

    li {
      margin-bottom: 0.7rem;
      padding-left: 1.1rem;
      position: relative;
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.6;
    }

    li::before {
      content: "";
      position: absolute;
      left: 0;
      top: 0.55rem;
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: var(--border-strong);
    }

    li:last-child { margin-bottom: 0; }

    .item-weight {
      display: inline-block;
      background: var(--surface);
      color: var(--muted);
      font-size: 0.72rem;
      font-weight: 500;
      padding: 1px 7px;
      border-radius: 10px;
      margin-left: 0.35rem;
      font-variant-numeric: tabular-nums;
      vertical-align: middle;
    }

    .sources {
      margin-top: 0.25rem;
      font-size: 0.78rem;
      color: var(--muted);
      padding-left: 0;
    }

    .sources a {
      color: var(--accent-text);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.15s;
    }

    .sources a:hover {
      border-bottom-color: var(--accent-text);
    }

    .solution-name {
      font-weight: 600;
      color: var(--text);
    }

    .method-card {
      background: var(--accent-light);
      border-radius: var(--radius-sm);
      padding: 0.85rem 1.1rem;
      border: 1px solid var(--border);
    }

    .method-card .name {
      font-weight: 600;
      font-size: 0.95rem;
      color: var(--text);
    }

    .method-card .rationale {
      font-size: 0.83rem;
      color: var(--text-secondary);
      margin-top: 0.35rem;
      line-height: 1.55;
    }

    .tag-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
      gap: 0.5rem;
    }

    .tag {
      background: var(--surface);
      border-radius: var(--radius-sm);
      padding: 0.65rem 0.5rem;
      text-align: center;
      border: 1px solid var(--border);
    }

    .tag .tag-name {
      font-size: 0.75rem;
      color: var(--muted);
      text-transform: capitalize;
    }

    .tag .tag-count {
      font-size: 1.25rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      color: var(--text);
    }

    .analytics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
      gap: 0.5rem;
      margin-bottom: 1rem;
    }

    .stat {
      background: var(--surface);
      border-radius: var(--radius-sm);
      padding: 0.6rem 0.5rem;
      text-align: center;
      border: 1px solid var(--border);
    }

    .stat .stat-value {
      font-size: 1.35rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      color: var(--text);
    }

    .stat .stat-label {
      font-size: 0.72rem;
      color: var(--muted);
      margin-top: 0.1rem;
    }

    .sub-bar-row {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      margin-bottom: 0.28rem;
      font-size: 0.8rem;
    }

    .sub-bar-label {
      width: 150px;
      text-align: right;
      color: var(--muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }

    .sub-bar-track {
      flex: 1;
      height: 14px;
      background: var(--surface);
      border-radius: 3px;
      overflow: hidden;
    }

    .sub-bar-fill {
      height: 100%;
      background: var(--accent);
      border-radius: 3px;
      opacity: 0.8;
    }

    .sub-bar-count {
      width: 28px;
      font-weight: 500;
      font-variant-numeric: tabular-nums;
      color: var(--text-secondary);
    }

    footer {
      text-align: center;
      color: var(--muted);
      font-size: 0.78rem;
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
    }

    footer a {
      color: var(--accent-text);
      text-decoration: none;
      border-bottom: 1px solid transparent;
    }

    footer a:hover { border-bottom-color: var(--accent-text); }

    @media (max-width: 600px) {
      body { padding: 1.25rem 0.75rem; }
      .header, .section { padding: 1rem 1.15rem; }
      .score-section { flex-direction: column; gap: 1rem; align-items: flex-start; }
      .sub-bar-label { width: 100px; }
    }

    @media print {
      body { background: #fff; padding: 1rem; max-width: none; }
      .section, .header { box-shadow: none; border-color: #ccc; break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>{{ L.title }}</h1>
    <div class="meta-row">
      <span>{{ L.run_id }}: {{ run_id }}</span>
      <span>{{ L.date }}: {{ timestamp }}</span>
    </div>
    <div class="original-idea">
      <strong>{{ L.idea }}:</strong> {{ original_idea }}
    </div>
  </div>

  <div class="section">
    <h2>{{ L.score }}</h2>
    <div class="score-section">
      <div class="score-ring">
        <svg viewBox="0 0 88 88">
          <circle class="ring-bg" cx="44" cy="44" r="38"></circle>
          <circle class="ring-fill {{ score_class }}"
                  cx="44" cy="44" r="38"
                  stroke-dasharray="238.76"
                  stroke-dashoffset="{{ 238.76 * (1 - score / 100) }}"></circle>
        </svg>
        <div class="score-number">{{ score }}</div>
      </div>
      <div class="score-bar-wrap">
        <div class="score-bar"><div class="score-bar-fill {{ score_class }}" style="width: {{ score }}%"></div></div>
        <p class="interpretation">{{ interpretation }}</p>
      </div>
    </div>
  </div>

{% if analysis_method %}
  <div class="section">
    <h2>{{ L.analysis_method }}</h2>
    <div class="method-card">
      <div class="name">{{ analysis_method.name }}</div>
      <div class="rationale">{{ analysis_method.rationale }}</div>
    </div>
  </div>
{% endif %}

{% if analytics %}
  <div class="section">
    <h2>{{ L.analytics }}</h2>
    <div class="analytics-grid">
      <div class="stat"><div class="stat-value">{{ analytics.total_records }}</div><div class="stat-label">{{ L.total_records }}</div></div>
      <div class="stat"><div class="stat-value">{{ analytics.posts }}</div><div class="stat-label">{{ L.posts }}</div></div>
      <div class="stat"><div class="stat-value">{{ analytics.comments }}</div><div class="stat-label">{{ L.comments }}</div></div>
      <div class="stat"><div class="stat-value">{{ analytics.subreddits }}</div><div class="stat-label">{{ L.subreddits }}</div></div>
    </div>
    {% for sub in analytics.top_subreddits %}
    <div class="sub-bar-row">
      <span class="sub-bar-label">{{ sub.subreddit }}</span>
      <div class="sub-bar-track"><div class="sub-bar-fill" style="width: {{ sub.pct }}%"></div></div>
      <span class="sub-bar-count">{{ sub.count }}</span>
    </div>
    {% endfor %}
  </div>
{% endif %}

  <div class="section">
    <h2>{{ L.market_snapshot }}</h2>
    <p class="desc">{{ L.market_snapshot_desc }}</p>
    <ul>
    {% for m in market_snapshot %}
      <li>
        {% if m is string %}{{ m }}{% else %}{{ m.text }}{% endif %}
        {% if not m is string and m.sources %}
        <div class="sources">{{ L.sources }}:
          {% for s in m.sources %}<a href="{{ s.url }}" target="_blank">r/{{ s.subreddit }}</a>{% if not loop.last %}, {% endif %}{% endfor %}
        </div>
        {% endif %}
      </li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>{{ L.pain_points }}</h2>
    <ul>
    {% for p in pain_points %}
      <li>
        {{ p.text }} <span class="item-weight">{{ L.weight }} {{ p.weight }}</span>
        {% if p.sources %}
        <div class="sources">{{ L.sources }}:
          {% for s in p.sources %}<a href="{{ s.url }}" target="_blank">r/{{ s.subreddit }}</a>{% if not loop.last %}, {% endif %}{% endfor %}
        </div>
        {% endif %}
      </li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>{{ L.existing_solutions }}</h2>
    <ul>
    {% for s in existing_solutions %}
      <li>
        {% if s is string %}{{ s }}{% else %}<span class="solution-name">{{ s.name }}</span>{% if s.description %}: {{ s.description }}{% endif %}
        {% if s.sources %}
        <div class="sources">{{ L.sources }}:
          {% for src in s.sources %}<a href="{{ src.url }}" target="_blank">r/{{ src.subreddit }}</a>{% if not loop.last %}, {% endif %}{% endfor %}
        </div>
        {% endif %}
        {% endif %}
      </li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>{{ L.opportunities }}</h2>
    <ul>
    {% for o in opportunities %}
      <li>
        {{ o.text }} <span class="item-weight">{{ L.weight }} {{ o.weight }}</span>
        {% if o.sources %}
        <div class="sources">{{ L.sources }}:
          {% for s in o.sources %}<a href="{{ s.url }}" target="_blank">r/{{ s.subreddit }}</a>{% if not loop.last %}, {% endif %}{% endfor %}
        </div>
        {% endif %}
      </li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>{{ L.how_to_win }}</h2>
    <p class="desc">{{ L.how_to_win_desc }}</p>
    <ul>
    {% for w in how_to_win %}
      <li>{{ w }}</li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>{{ L.recommendations }}</h2>
    <ul>
    {% for r in recommendations %}
      <li>{{ r }}</li>
    {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>{{ L.comment_tags }}</h2>
    <div class="tag-grid">
    {% for tag, count in comment_tags.items() %}
      <div class="tag"><div class="tag-count">{{ count }}</div><div class="tag-name">{{ tag }}</div></div>
    {% endfor %}
    </div>
  </div>

  <footer>Generated by <a href="https://github.com/LingoWise/reddit-skills" target="_blank">reddit-validator</a> v{{ version }} · {{ run_id }}</footer>
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


def _interpretation(score, labels):
    if score >= 75:
        return labels["interpretation_strong"]
    if score >= 50:
        return labels["interpretation_promising"]
    if score >= 30:
        return labels["interpretation_weak"]
    return labels["interpretation_nogo"]


def _safe_filename(text):
    return re.sub(r"[^\w\-]+", "_", text).strip("_")[:50]


def _compute_analytics(records):
    if not records:
        return None
    subs = Counter(r.get("subreddit", "unknown") for r in records)
    posts = sum(1 for r in records if not r.get("is_comment"))
    comments = sum(1 for r in records if r.get("is_comment"))
    max_count = max(subs.values()) if subs else 1
    top_subs = [
        {"subreddit": sub, "count": cnt, "pct": round(cnt / max_count * 100)}
        for sub, cnt in subs.most_common(10)
    ]
    return {
        "total_records": len(records),
        "posts": posts,
        "comments": comments,
        "subreddits": len(subs),
        "top_subreddits": top_subs,
    }


def render(analysis, idea, run_id, profile, records=None, language=None):
    lang_code = language or analysis.get("language", "en")
    labels = LABELS.get(lang_code, LABELS["en"])
    original_idea = analysis.get("original_idea", idea)
    analytics = _compute_analytics(records) if records else None

    ctx = {
        "L": labels,
        "lang_code": lang_code,
        "idea": idea,
        "original_idea": original_idea,
        "run_id": run_id,
        "score": analysis.get("score", 0),
        "score_class": _score_class(analysis.get("score", 0)),
        "interpretation": _interpretation(analysis.get("score", 0), labels),
        "analysis_method": analysis.get("analysis_method"),
        "analytics": analytics,
        "market_snapshot": analysis.get("market_snapshot", []),
        "pain_points": analysis.get("pain_points", []),
        "existing_solutions": analysis.get("existing_solutions", []),
        "opportunities": analysis.get("opportunities", []),
        "how_to_win": analysis.get("how_to_win", []),
        "recommendations": analysis.get("recommendations", []),
        "comment_tags": analysis.get("comment_tags", {}),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "version": VERSION,
    }
    html = Template(TEMPLATE).render(**ctx)
    path = reports_dir() / f"{_safe_filename(idea)}_{run_id}.html"
    path.write_text(html)
    return str(path)
