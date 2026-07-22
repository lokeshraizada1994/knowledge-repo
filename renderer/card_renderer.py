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

    icons = {
        "youtube": "▶️", "podcast": "🎙️", "article": "📰",
        "case_study": "📋", "report": "📊", "text": "📝"
    }
    icon = icons.get(source_type, "📄")

    # ── TL;DR ────────────────────────────────────────────────────────────
    tldr = card.get("tldr", [])
    tldr_html = "".join(f"<li>{t}</li>" for t in tldr if t)

    # ── Top Insights ─────────────────────────────────────────────────────
    insights = card.get("top_insights", [])
    insights_html = ""
    for i, item in enumerate(insights, 1):
        insight = item.get("insight", "")
        why = item.get("why_it_matters", "")
        insights_html += f"""
        <div class="insight-card">
          <div class="insight-num">{i}</div>
          <div class="insight-body">
            <div class="insight-text">{insight}</div>
            {f'<div class="insight-why">💡 {why}</div>' if why else ''}
          </div>
        </div>"""

    # ── Best Example ─────────────────────────────────────────────────────
    example = card.get("best_example", {})
    example_present = example.get("present", False)
    if example_present:
        ex_title = example.get("title", "")
        ex_story = example.get("story", "")
        example_html = f"""
        <div class="example-box">
          {f'<div class="example-title">{ex_title}</div>' if ex_title else ''}
          <div class="example-story">&ldquo;{ex_story}&rdquo;</div>
        </div>"""
    else:
        reason = example.get("reason_absent", "No standout example in this source.")
        example_html = f'<div class="empty-note">{reason}</div>'

    # ── Do This ──────────────────────────────────────────────────────────
    do_this = card.get("do_this", {})
    do_present = do_this.get("present", False)
    if do_present:
        actions = do_this.get("actions", [])
        do_html = "".join(f'<li><span class="check">✓</span>{a}</li>' for a in actions)
        do_html = f'<ul class="do-list">{do_html}</ul>'
    else:
        reason = do_this.get("reason_absent", "No concrete actions in this source.")
        do_html = f'<div class="empty-note">{reason}</div>'

    # ── The Catch ────────────────────────────────────────────────────────
    catch = card.get("the_catch", "")

    # ── Extra Sections (flexible) ────────────────────────────────────────
    extra_html = ""
    for sec in card.get("extra_sections", []) or []:
        emoji = sec.get("emoji", "✨")
        sec_title = sec.get("title", "Worth Noting")
        sec_type = sec.get("type", "bullets")
        content = sec.get("content", [])

        if sec_type == "quote" and content:
            body = f'<div class="quote-block">&ldquo;{content[0] if isinstance(content, list) else content}&rdquo;</div>'
        elif sec_type == "stat" and isinstance(content, list):
            body = '<div class="stat-grid">' + "".join(f'<div class="stat-chip">{c}</div>' for c in content) + '</div>'
        elif isinstance(content, list):
            body = "<ul class='extra-list'>" + "".join(f"<li>{c}</li>" for c in content) + "</ul>"
        else:
            body = f"<p>{content}</p>"

        extra_html += f"""
        <div class="card-block extra-block">
          <div class="block-header"><span class="block-icon">{emoji}</span><span class="block-title">{sec_title}</span></div>
          {body}
        </div>"""

    tags_html = "".join(f"<span class='tag'>{t}</span>" for t in tags)
    source_link = f'<a href="{source_url}" target="_blank" class="source-link">View original ↗</a>' if source_url else ""

    # ── Flashcards ───────────────────────────────────────────────────────
    flashcards = card.get("flashcards", [])
    flash_html = ""
    for i, fc in enumerate(flashcards):
        q = fc.get("question", "")
        a = fc.get("answer", "")
        flash_html += f"""
        <div class="flashcard" onclick="this.classList.toggle('flipped')">
          <div class="flash-inner">
            <div class="flash-face flash-front">
              <div class="flash-label">Q{i+1}</div>
              <div class="flash-text">{q}</div>
              <div class="flash-hint">Tap to reveal 👆</div>
            </div>
            <div class="flash-face flash-back">
              <div class="flash-label">Answer</div>
              <div class="flash-text">{a}</div>
            </div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title}</title>
<style>
  :root {{
    --bg: #faf8f4;
    --surface: #ffffff;
    --border: #ece4d6;
    --text: #3a352e;
    --text2: #8a8074;
    --accent: #c96f4a;
    --accent2: #d9a441;
    --green: #4d8a5f;
    --green-bg: #f0f7f1;
    --amber-bg: #fbf5e9;
    --amber-border: #ecdcb0;
    --shadow: rgba(201, 111, 74, 0.06);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 15px; line-height: 1.7; padding: 28px 20px 60px;
    max-width: 760px; margin: 0 auto;
  }}

  .hero {{
    background: linear-gradient(135deg, #f6efe3 0%, #f2e9d8 100%);
    border: 1px solid #e8d9bf;
    border-radius: 20px; padding: 32px; margin-bottom: 20px;
    box-shadow: 0 4px 20px var(--shadow);
  }}
  .hero-icon {{ font-size: 34px; margin-bottom: 10px; }}
  .hero-title {{ font-size: 25px; font-weight: 800; color: #2a251f; margin-bottom: 10px; line-height: 1.35; }}
  .hero-meta {{ display: flex; gap: 16px; flex-wrap: wrap; color: var(--text2); font-size: 12.5px; margin-bottom: 14px; }}
  .hero-meta span {{ display: flex; align-items: center; gap: 4px; }}
  .tags {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }}
  .tag {{ background: #fff; color: var(--accent); border: 1px solid #e8d4c2;
    padding: 4px 12px; border-radius: 999px; font-size: 11.5px; font-weight: 700; }}
  .source-link {{ color: var(--accent); text-decoration: none; font-size: 12.5px; font-weight: 700; }}
  .source-link:hover {{ text-decoration: underline; }}

  .card-block {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; padding: 22px 26px; margin-bottom: 16px;
  }}
  .block-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }}
  .block-icon {{ font-size: 19px; }}
  .block-title {{ font-size: 12.5px; font-weight: 800; text-transform: uppercase;
    letter-spacing: 1.2px; color: var(--text2); }}

  /* TL;DR */
  .tldr-block {{ background: linear-gradient(135deg, #fbf7f0 0%, #fefdfa 100%); border: 1px solid #ece0cc; }}
  .tldr-list {{ list-style: none; }}
  .tldr-list li {{ position: relative; padding-left: 26px; margin-bottom: 10px; font-weight: 600; font-size: 15.5px; color: #2a251f; }}
  .tldr-list li::before {{ content: '→'; position: absolute; left: 0; color: var(--accent); font-weight: 900; }}

  /* Top Insights */
  .insight-card {{ display: flex; gap: 14px; padding: 14px 0; border-bottom: 1px solid #f2ece0; }}
  .insight-card:last-child {{ border-bottom: none; }}
  .insight-num {{ flex-shrink: 0; width: 30px; height: 30px; border-radius: 50%;
    background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #fff;
    display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; }}
  .insight-text {{ font-weight: 600; color: #2a251f; margin-bottom: 4px; }}
  .insight-why {{ font-size: 12.5px; color: var(--text2); }}

  /* Best Example */
  .example-box {{ background: var(--amber-bg); border: 1px solid var(--amber-border);
    border-radius: 12px; padding: 18px 20px; }}
  .example-title {{ font-weight: 800; color: #8a5a2e; font-size: 13px; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 8px; }}
  .example-story {{ font-style: italic; color: #4a3a24; line-height: 1.7; }}

  /* Do This */
  .do-list {{ list-style: none; }}
  .do-list li {{ display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; font-weight: 500; }}
  .check {{ flex-shrink: 0; width: 20px; height: 20px; border-radius: 6px; background: var(--green-bg);
    color: var(--green); display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 900; border: 1px solid #cde3d1; }}

  /* The Catch */
  .catch-block {{ background: #faf3e9; border: 1px solid #e6d3ae; }}
  .catch-text {{ color: #6b4a28; font-weight: 500; }}

  .empty-note {{ color: var(--text2); font-style: italic; font-size: 13px; }}

  /* Extra sections */
  .quote-block {{ font-style: italic; font-size: 16px; color: #2a251f; padding: 8px 0 8px 16px;
    border-left: 3px solid var(--accent); }}
  .stat-grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .stat-chip {{ background: #f6efe3; border: 1px solid #e8d4c2; border-radius: 10px;
    padding: 10px 16px; font-weight: 700; font-size: 13.5px; color: #2a251f; }}
  .extra-list {{ padding-left: 20px; }}
  .extra-list li {{ margin-bottom: 8px; }}

  /* Flashcards */
  .flash-block {{ background: linear-gradient(135deg, #f6f0f3 0%, #f6efe3 100%); border: 1px solid #e6d9de; }}
  .flash-grid {{ display: grid; grid-template-columns: 1fr; gap: 12px; }}
  .flashcard {{ perspective: 1000px; height: 110px; cursor: pointer; }}
  .flash-inner {{ position: relative; width: 100%; height: 100%; transition: transform 0.5s;
    transform-style: preserve-3d; }}
  .flashcard.flipped .flash-inner {{ transform: rotateY(180deg); }}
  .flash-face {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden;
    border-radius: 12px; padding: 16px 20px; display: flex; flex-direction: column; justify-content: center; }}
  .flash-front {{ background: #fff; border: 2px solid #e8d4c2; }}
  .flash-back {{ background: linear-gradient(135deg, var(--accent), var(--accent2));
    transform: rotateY(180deg); color: #fff; }}
  .flash-label {{ font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;
    opacity: 0.7; margin-bottom: 6px; }}
  .flash-text {{ font-weight: 700; font-size: 14.5px; line-height: 1.4; }}
  .flash-hint {{ font-size: 11px; color: var(--text2); margin-top: 8px; font-weight: 500; }}

  .progress-note {{ text-align: center; padding: 18px; background: linear-gradient(135deg, #f6efe3, #fbf7f0);
    border-radius: 14px; margin-bottom: 16px; font-weight: 700; color: #8a5a2e; font-size: 13.5px;
    border: 1px solid #ece0cc; }}

  .footer {{ text-align: center; color: var(--text2); font-size: 11.5px; margin-top: 28px; }}
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

<div class="progress-note">🔥 One more piece of knowledge locked in — you're building something real.</div>

<div class="card-block tldr-block">
  <div class="block-header"><span class="block-icon">⚡</span><span class="block-title">TL;DR</span></div>
  <ul class="tldr-list">{tldr_html}</ul>
</div>

<div class="card-block">
  <div class="block-header"><span class="block-icon">🎯</span><span class="block-title">Top Insights</span></div>
  {insights_html}
</div>

<div class="card-block">
  <div class="block-header"><span class="block-icon">📖</span><span class="block-title">Best Example</span></div>
  {example_html}
</div>

<div class="card-block">
  <div class="block-header"><span class="block-icon">✅</span><span class="block-title">Do This</span></div>
  {do_html}
</div>

{extra_html}

<div class="card-block catch-block">
  <div class="block-header"><span class="block-icon">⚠️</span><span class="block-title">The Catch</span></div>
  <div class="catch-text">{catch}</div>
</div>

<div class="card-block flash-block">
  <div class="block-header"><span class="block-icon">🧠</span><span class="block-title">Test Yourself</span></div>
  <div class="flash-grid">{flash_html}</div>
</div>

<div class="footer">Generated by Knowledge Repository · {date}</div>
</body>
</html>"""

    return html
