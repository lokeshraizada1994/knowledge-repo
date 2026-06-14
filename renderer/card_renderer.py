import json
from datetime import datetime


def render_card(card: dict) -> str:
    meta = card.get("metadata", {})
    title = meta.get("title", "Untitled")
    source_type = meta.get("source_type", "article")
    source_url = meta.get("source_url")
    author = meta.get("author")
    date = meta.get("date_processed", datetime.utcnow().strftime("%Y-%m-%d"))
    duration = meta.get("estimated_duration", "")
    tags = meta.get("tags", [])

    source_icons = {
        "youtube": "▶️", "podcast": "🎙️", "article": "📰",
        "case_study": "📋", "report": "📊", "text": "📝"
    }
    icon = source_icons.get(source_type, "📄")

    def is_na(val):
        if isinstance(val, str):
            return val.strip().upper().startswith("N/A")
        return False

    def safe_list(val):
        if isinstance(val, list):
            return val
        return []

    def render_section(section_id, label, emoji, content_html, na=False):
        na_class = "na-section" if na else ""
        return f"""
        <div class="section {na_class}" id="{section_id}">
            <div class="section-header">
                <span class="section-icon">{emoji}</span>
                <span class="section-title">{label}</span>
                {"<span class='na-badge'>N/A</span>" if na else ""}
            </div>
            <div class="section-body">{content_html}</div>
        </div>"""

    # ── Build each section ──────────────────────────────────────────────────

    # Executive Summary
    summary = card.get("executive_summary", {})
    summary_html = f"<p>{summary.get('content', '')}</p>"

    # Top 5 Takeaways
    takeaways = card.get("top_5_takeaways", {}).get("content", [])
    takeaways_html = "<ol class='takeaway-list'>"
    for t in takeaways:
        inferred = t.get("inferred", False)
        badge = "<span class='inferred-badge'>inferred</span>" if inferred else ""
        takeaways_html += f"<li>{t.get('point','')}{badge}</li>"
    takeaways_html += "</ol>"

    # Actionables
    actions = safe_list(card.get("actionables", {}).get("content", []))
    actions_html = "<ol class='action-list'>"
    for a in actions:
        actions_html += f"<li>{a}</li>"
    actions_html += "</ol>"

    # Critique
    critique = card.get("critique", {})
    strengths = safe_list(critique.get("strengths", []))
    weaknesses = safe_list(critique.get("weaknesses", []))
    missing = safe_list(critique.get("missing", []))
    critique_html = "<div class='critique-grid'>"
    critique_html += "<div class='critique-col strengths'><div class='col-label'>✅ Strengths</div><ul>"
    for s in strengths:
        critique_html += f"<li>{s}</li>"
    critique_html += "</ul></div>"
    critique_html += "<div class='critique-col weaknesses'><div class='col-label'>⚠️ Weaknesses</div><ul>"
    for w in weaknesses:
        critique_html += f"<li>{w}</li>"
    critique_html += "</ul></div>"
    critique_html += "<div class='critique-col missing'><div class='col-label'>❓ Missing</div><ul>"
    for m in missing:
        critique_html += f"<li>{m}</li>"
    critique_html += "</ul></div>"
    critique_html += "</div>"

    # Thinking Framework
    framework = card.get("thinking_framework", {})
    fw_content = framework.get("content", "")
    fw_name = framework.get("framework_name")
    fw_na = is_na(fw_content)
    if fw_na:
        fw_html = f"<p class='na-text'>{fw_content}</p>"
    else:
        fw_name_html = f"<div class='fw-name'>{fw_name}</div>" if fw_name else ""
        fw_html = f"{fw_name_html}<p>{fw_content}</p>"

    # Knowledge Insights
    insights = card.get("knowledge_insights", {}).get("content", "")
    insights_na = is_na(insights)
    insights_html = f"<p class='{'na-text' if insights_na else ''}'>{insights}</p>"

    # Examples & Stories
    examples = card.get("examples_and_stories", {}).get("content", "")
    examples_na = is_na(examples) if isinstance(examples, str) else False
    if examples_na:
        examples_html = f"<p class='na-text'>{examples}</p>"
    elif isinstance(examples, list):
        examples_html = "<ul class='examples-list'>"
        for e in examples:
            examples_html += f"<li>{e}</li>"
        examples_html += "</ul>"
    else:
        examples_html = f"<p>{examples}</p>"

    # Limitations
    limitations = card.get("limitations_and_challenges", {}).get("content", "")
    lim_na = is_na(limitations) if isinstance(limitations, str) else False
    if lim_na:
        lim_html = f"<p class='na-text'>{limitations}</p>"
    elif isinstance(limitations, list):
        lim_html = "<ul class='lim-list'>"
        for l in limitations:
            lim_html += f"<li>{l}</li>"
        lim_html += "</ul>"
    else:
        lim_html = f"<p>{limitations}</p>"

    # Best Practices
    practices = card.get("best_practices", {}).get("content", "")
    bp_na = is_na(practices) if isinstance(practices, str) else False
    if bp_na:
        bp_html = f"<p class='na-text'>{practices}</p>"
    elif isinstance(practices, list):
        bp_html = "<ul class='bp-list'>"
        for p in practices:
            bp_html += f"<li>{p}</li>"
        bp_html += "</ul>"
    else:
        bp_html = f"<p>{practices}</p>"

    # Use Cases
    use_cases = card.get("use_cases", {}).get("content", "")
    uc_na = is_na(use_cases) if isinstance(use_cases, str) else False
    if uc_na:
        uc_html = f"<p class='na-text'>{use_cases}</p>"
    elif isinstance(use_cases, list):
        uc_html = "<div class='use-case-grid'>"
        for uc in use_cases:
            uc_html += f"<div class='use-case-chip'>{uc}</div>"
        uc_html += "</div>"
    else:
        uc_html = f"<p>{use_cases}</p>"

    # What's Ahead
    ahead = card.get("whats_ahead", {}).get("content", "")
    ahead_na = is_na(ahead)
    ahead_html = f"<p class='{'na-text' if ahead_na else ''}'>{ahead}</p>"

    # Tags HTML
    tags_html = "".join(f"<span class='tag'>{t}</span>" for t in tags)

    # Source link
    source_link = f'<a href="{source_url}" target="_blank" class="source-link">View original →</a>' if source_url else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title}</title>
<style>
  :root {{
    --bg: #0f1117; --surface: #1a1f2e; --surface2: #242938;
    --border: #2d3448; --text: #e8eaf0; --text2: #9aa0b8;
    --accent: #6366f1; --accent2: #8b5cf6; --green: #22c55e;
    --red: #ef4444; --yellow: #f59e0b; --blue: #3b82f6;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif;
    font-size: 14px; line-height: 1.7; padding: 24px; max-width: 900px; margin: 0 auto; }}

  .hero {{ background: linear-gradient(135deg, #1a1f2e 0%, #242938 100%);
    border: 1px solid var(--border); border-radius: 16px; padding: 32px; margin-bottom: 24px; }}
  .hero-icon {{ font-size: 36px; margin-bottom: 12px; }}
  .hero-title {{ font-size: 26px; font-weight: 800; color: #fff; margin-bottom: 8px; line-height: 1.3; }}
  .hero-meta {{ display: flex; gap: 16px; flex-wrap: wrap; color: var(--text2); font-size: 12px; margin-bottom: 14px; }}
  .hero-meta span {{ display: flex; align-items: center; gap: 4px; }}
  .tags {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
  .tag {{ background: #1e2d4a; color: #60a5fa; border: 1px solid #1d4ed8;
    padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
  .source-link {{ color: var(--accent); text-decoration: none; font-size: 12px; font-weight: 600; }}
  .source-link:hover {{ text-decoration: underline; }}

  .section {{ background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px 24px; margin-bottom: 14px; }}
  .section.na-section {{ opacity: 0.5; }}
  .section-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }}
  .section-icon {{ font-size: 18px; }}
  .section-title {{ font-size: 13px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: var(--text2); }}
  .na-badge {{ background: #2a1a00; color: #f59e0b; border: 1px solid #78350f;
    font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 999px; }}
  .na-text {{ color: var(--text2); font-style: italic; font-size: 12px; }}
  .section-body p {{ color: var(--text); }}

  ol.takeaway-list {{ padding-left: 20px; }}
  ol.takeaway-list li {{ margin-bottom: 10px; color: var(--text); }}
  .inferred-badge {{ background: #1c1400; color: var(--yellow); border: 1px solid #78350f;
    font-size: 9px; padding: 1px 6px; border-radius: 4px; margin-left: 8px; vertical-align: middle; }}

  ol.action-list {{ padding-left: 20px; }}
  ol.action-list li {{ margin-bottom: 8px; color: var(--text); padding-left: 4px; }}

  .critique-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }}
  @media(max-width:600px) {{ .critique-grid {{ grid-template-columns: 1fr; }} }}
  .critique-col {{ background: var(--surface2); border-radius: 8px; padding: 12px; }}
  .critique-col.strengths {{ border-top: 3px solid var(--green); }}
  .critique-col.weaknesses {{ border-top: 3px solid var(--red); }}
  .critique-col.missing {{ border-top: 3px solid var(--yellow); }}
  .col-label {{ font-size: 11px; font-weight: 700; margin-bottom: 8px; color: var(--text2); }}
  .critique-col ul {{ padding-left: 16px; }}
  .critique-col ul li {{ margin-bottom: 6px; font-size: 13px; }}

  .fw-name {{ display: inline-block; background: var(--accent); color: #fff;
    font-size: 11px; font-weight: 700; padding: 3px 12px; border-radius: 999px; margin-bottom: 10px; }}

  ul.examples-list, ul.lim-list, ul.bp-list {{ padding-left: 20px; }}
  ul.examples-list li, ul.lim-list li, ul.bp-list li {{ margin-bottom: 8px; }}

  .use-case-grid {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .use-case-chip {{ background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 14px; font-size: 12px; color: var(--text); }}

  .footer {{ text-align: center; color: var(--text2); font-size: 11px; margin-top: 32px; padding-top: 16px;
    border-top: 1px solid var(--border); }}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-icon">{icon}</div>
  <div class="hero-title">{title}</div>
  <div class="hero-meta">
    {"<span>✍️ " + author + "</span>" if author else ""}
    {"<span>⏱ " + duration + "</span>" if duration else ""}
    <span>📅 {date}</span>
    <span>📁 {source_type.replace("_"," ").title()}</span>
  </div>
  {source_link}
  <div class="tags">{tags_html}</div>
</div>

{render_section("summary", "Executive Summary", "📌", summary_html)}
{render_section("takeaways", "Top 5 Takeaways", "🏆", takeaways_html)}
{render_section("actionables", "Actionables", "⚡", actions_html)}
{render_section("critique", "Critique", "🔍", critique_html)}
{render_section("framework", "Thinking Framework", "🧠", fw_html, na=fw_na)}
{render_section("insights", "Knowledge Insights", "💡", insights_html, na=insights_na)}
{render_section("examples", "Examples & Stories", "📖", examples_html, na=examples_na)}
{render_section("limitations", "Limitations & Challenges", "🚧", lim_html, na=lim_na)}
{render_section("practices", "Best Practices", "✅", bp_html, na=bp_na)}
{render_section("usecases", "Use Cases", "🎯", uc_html, na=uc_na)}
{render_section("ahead", "What's Ahead", "🔭", ahead_html, na=ahead_na)}

<div class="footer">Generated by Knowledge Repository Pipeline · {date}</div>
</body>
</html>"""

    return html
