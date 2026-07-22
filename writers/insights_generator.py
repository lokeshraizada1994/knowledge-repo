"""
Insights page generator.

Reads every data.json in the repo, synthesizes cross-card themes, connections,
and stats using Claude, and writes a single insights.html page to GitHub Pages.

Called non-blocking after each successful pipeline run.
"""
import os
import json
import anthropic
from datetime import datetime

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYNTHESIS_PROMPT = """You are analyzing a personal knowledge archive — a collection of distilled cards from articles, videos, podcasts, and reports the user has saved over time.

Given compact summaries of every card (title, tags, TL;DR, top insights), find genuine cross-card patterns. Be honest — if there are too few cards to find real patterns, say so plainly rather than forcing connections.

Return strict JSON, no markdown fences:
{
  "recurring_themes": [
    {"theme": "Short theme name", "description": "1-2 sentences on the pattern across sources", "card_titles": ["title1", "title2"]}
  ],
  "connections": [
    {"description": "1-2 sentences on how two+ specific cards relate, agree, or contradict each other", "card_titles": ["title1", "title2"]}
  ],
  "standout_stat": "The single most striking number/fact across the whole archive, with its source title, or null if none stands out",
  "one_liner": "A single encouraging sentence about what this collection reveals about the user's current learning focus"
}

If there are fewer than 3 cards or no genuine cross-card patterns exist, return empty arrays for recurring_themes and connections rather than inventing shallow connections."""


def _fetch_all_cards(repo) -> list:
    cards = []
    try:
        entries = repo.get_contents("entries")
    except Exception:
        return cards

    for folder in entries:
        try:
            data_file = repo.get_contents(f"{folder.path}/data.json")
            card = json.loads(data_file.decoded_content.decode("utf-8"))
            cards.append(card)
        except Exception:
            continue
    return cards


def _compact_card(card: dict) -> dict:
    meta = card.get("metadata", {})
    return {
        "title": meta.get("title", "Untitled"),
        "tags": meta.get("tags", []),
        "source_type": meta.get("source_type", ""),
        "date": meta.get("date_processed", ""),
        "tldr": card.get("tldr", []),
        "top_insights": [i.get("insight", "") for i in card.get("top_insights", [])],
    }


def _synthesize(compact_cards: list) -> dict:
    if len(compact_cards) < 2:
        return {
            "recurring_themes": [],
            "connections": [],
            "standout_stat": None,
            "one_liner": "Add a few more cards and patterns will start to emerge here.",
        }

    user_message = "ARCHIVE:\n" + json.dumps(compact_cards, indent=2)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYNTHESIS_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)


def _tag_frequency(compact_cards: list) -> list:
    freq = {}
    for c in compact_cards:
        for t in c.get("tags", []):
            freq[t] = freq.get(t, 0) + 1
    return sorted(freq.items(), key=lambda x: -x[1])[:20]


def _render_insights_html(compact_cards: list, synthesis: dict) -> str:
    total = len(compact_cards)
    type_counts = {}
    for c in compact_cards:
        st = c.get("source_type", "other")
        type_counts[st] = type_counts.get(st, 0) + 1

    tag_freq = _tag_frequency(compact_cards)
    max_freq = max([f for _, f in tag_freq], default=1)

    themes_html = ""
    for t in synthesis.get("recurring_themes", []):
        titles = ", ".join(t.get("card_titles", []))
        themes_html += f"""
        <div class="theme-card">
          <div class="theme-name">{t.get('theme','')}</div>
          <div class="theme-desc">{t.get('description','')}</div>
          <div class="theme-sources">📚 {titles}</div>
        </div>"""
    if not themes_html:
        themes_html = '<div class="empty-note">Not enough cards yet to find recurring themes. Keep adding!</div>'

    connections_html = ""
    for c in synthesis.get("connections", []):
        titles = ", ".join(c.get("card_titles", []))
        connections_html += f"""
        <div class="connection-card">
          <div class="connection-desc">{c.get('description','')}</div>
          <div class="connection-sources">🔗 {titles}</div>
        </div>"""
    if not connections_html:
        connections_html = '<div class="empty-note">No cross-card connections found yet.</div>'

    stat = synthesis.get("standout_stat")
    stat_html = f'<div class="standout-stat">🌟 {stat}</div>' if stat else ""

    one_liner = synthesis.get("one_liner", "")

    type_icons = {"youtube": "▶️", "podcast": "🎙️", "article": "📰", "case_study": "📋", "report": "📊", "text": "📝"}
    type_chips = "".join(
        f'<div class="type-chip">{type_icons.get(t,"📄")} {t.replace("_"," ").title()}: {n}</div>'
        for t, n in type_counts.items()
    )

    tag_cloud = "".join(
        f'<span class="tag-cloud-item" style="font-size:{11 + (f/max_freq)*10:.0f}px">{tag}</span>'
        for tag, f in tag_freq
    )

    date = datetime.utcnow().strftime("%Y-%m-%d")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Insights — Knowledge Repository</title>
<style>
  :root {{
    --bg: #fdfaf5; --surface: #ffffff; --border: #f0e6d6;
    --text: #2d2a26; --text2: #7a7268;
    --accent: #ff7a45; --accent2: #ffb020;
    --shadow: rgba(255, 122, 69, 0.10);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif;
    padding: 32px 20px 60px; max-width: 900px; margin: 0 auto; line-height: 1.7; }}

  .topbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
  .back-link {{ color: var(--accent); text-decoration: none; font-weight: 700; font-size: 13px; }}

  .hero {{ background: linear-gradient(135deg, #fff5eb 0%, #fef3ff 100%); border: 1px solid #ffe0c2;
    border-radius: 20px; padding: 36px; margin-bottom: 24px; text-align: center;
    box-shadow: 0 4px 20px var(--shadow); }}
  .hero h1 {{ font-size: 28px; font-weight: 900; margin-bottom: 10px; }}
  .hero p {{ color: var(--text2); font-size: 14.5px; font-weight: 600; }}

  .stats-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 24px; }}
  .stat-box {{ flex: 1; min-width: 140px; background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 18px; text-align: center; }}
  .stat-num {{ font-size: 26px; font-weight: 900; color: var(--accent); }}
  .stat-label {{ font-size: 11px; color: var(--text2); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }}

  .type-chips {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; }}
  .type-chip {{ background: #fff; border: 1px solid #ffe0c2; border-radius: 999px; padding: 8px 16px;
    font-size: 12.5px; font-weight: 700; }}

  .section-title {{ font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px;
    color: var(--text2); margin: 28px 0 14px; display: flex; align-items: center; gap: 8px; }}

  .theme-card, .connection-card {{ background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 18px 22px; margin-bottom: 12px; }}
  .theme-name {{ font-weight: 800; font-size: 15px; margin-bottom: 6px; color: #1f1c19; }}
  .theme-desc, .connection-desc {{ color: var(--text); margin-bottom: 8px; }}
  .theme-sources, .connection-sources {{ font-size: 12px; color: var(--text2); font-weight: 600; }}

  .standout-stat {{ background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #fff;
    border-radius: 14px; padding: 20px 24px; font-weight: 700; font-size: 16px; margin-bottom: 24px; }}

  .tag-cloud {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
    padding: 20px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
  .tag-cloud-item {{ color: var(--accent); font-weight: 700; }}

  .empty-note {{ color: var(--text2); font-style: italic; font-size: 13px; }}

  .one-liner {{ text-align: center; padding: 20px; background: linear-gradient(135deg, #fff9f0, #fef3ff);
    border-radius: 14px; font-weight: 700; color: #92400e; margin-top: 24px; border: 1px solid #ffe9c7; }}

  .footer {{ text-align: center; color: var(--text2); font-size: 11px; margin-top: 32px; }}
</style>
</head>
<body>

<div class="topbar">
  <a class="back-link" href="index.html">← Back to Repository</a>
</div>

<div class="hero">
  <h1>✨ Your Learning Insights</h1>
  <p>Patterns and connections synthesized across everything you've saved</p>
</div>

<div class="stats-row">
  <div class="stat-box"><div class="stat-num">{total}</div><div class="stat-label">Total Cards</div></div>
  <div class="stat-box"><div class="stat-num">{len(type_counts)}</div><div class="stat-label">Content Types</div></div>
  <div class="stat-box"><div class="stat-num">{len(tag_freq)}</div><div class="stat-label">Unique Topics</div></div>
</div>

<div class="type-chips">{type_chips}</div>

{stat_html}

<div class="section-title">🧩 Recurring Themes</div>
{themes_html}

<div class="section-title">🔗 Connections Between Cards</div>
{connections_html}

<div class="section-title">☁️ Topic Cloud</div>
<div class="tag-cloud">{tag_cloud}</div>

<div class="one-liner">{one_liner}</div>

<div class="footer">Regenerated {date} · Knowledge Repository Insights</div>
</body>
</html>"""


def generate_insights(github_username: str, github_repo: str, github_token: str) -> str | None:
    try:
        from github import Github
        gh = Github(github_token)
        repo = gh.get_user(github_username).get_repo(github_repo)

        cards = _fetch_all_cards(repo)
        compact_cards = [_compact_card(c) for c in cards]
        synthesis = _synthesize(compact_cards)
        html = _render_insights_html(compact_cards, synthesis)

        path = "insights.html"
        try:
            existing = repo.get_contents(path)
            repo.update_file(path, "Update insights page", html, existing.sha)
        except Exception:
            repo.create_file(path, "Create insights page", html)

        url = f"https://{github_username}.github.io/{github_repo}/insights.html"
        print(f"[Insights] Updated: {url}")
        return url
    except Exception as e:
        print(f"[Insights] Failed to generate: {e}")
        return None
