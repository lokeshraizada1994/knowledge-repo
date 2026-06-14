import os
import re
import base64
from datetime import datetime
from github import Github

gh = Github(os.getenv("GITHUB_TOKEN"))
_repo = None


def _get_repo():
    global _repo
    if _repo:
        return _repo
    username = os.getenv("GITHUB_USERNAME")
    repo_name = os.getenv("GITHUB_REPO", "knowledge-repo")
    _repo = gh.get_user(username).get_repo(repo_name)
    return _repo


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def write_to_github(card: dict, html_card: str) -> str:
    repo = _get_repo()
    meta = card.get("metadata", {})
    title = meta.get("title", "Untitled")
    date = meta.get("date_processed", datetime.utcnow().strftime("%Y-%m-%d"))
    source_type = meta.get("source_type", "article")
    slug = _slugify(title)

    folder = f"entries/{date}-{slug}"
    html_path = f"{folder}/index.html"
    json_path = f"{folder}/data.json"

    import json
    json_content = json.dumps(card, indent=2, ensure_ascii=False)

    commit_message = f"Add: {title} [{source_type}]"

    # Write HTML card
    try:
        existing = repo.get_contents(html_path)
        repo.update_file(html_path, commit_message, html_card, existing.sha)
    except Exception:
        repo.create_file(html_path, commit_message, html_card)

    # Write raw JSON
    try:
        existing = repo.get_contents(json_path)
        repo.update_file(json_path, commit_message, json_content, existing.sha)
    except Exception:
        repo.create_file(json_path, commit_message, json_content)

    # Update index page
    _update_index(repo, card, folder)

    username = os.getenv("GITHUB_USERNAME")
    repo_name = os.getenv("GITHUB_REPO", "knowledge-repo")
    github_pages_url = f"https://{username}.github.io/{repo_name}/{folder}/"
    return github_pages_url


def _update_index(repo, card: dict, folder: str):
    meta = card.get("metadata", {})
    title = meta.get("title", "Untitled")
    date = meta.get("date_processed", "")
    source_type = meta.get("source_type", "")
    tags = meta.get("tags", [])
    summary = card.get("executive_summary", {}).get("content", "")[:200]

    icons = {
        "youtube": "▶️", "podcast": "🎙️", "article": "📰",
        "case_study": "📋", "report": "📊", "text": "📝"
    }
    icon = icons.get(source_type, "📄")

    # Load existing index or start fresh
    index_path = "index.html"
    try:
        existing_file = repo.get_contents(index_path)
        existing_html = existing_file.decoded_content.decode("utf-8")
        existing_sha = existing_file.sha
    except Exception:
        existing_html = _base_index_html()
        existing_sha = None

    # Inject new card entry before closing </div> of entries grid
    new_entry = f"""
    <div class="card" data-type="{source_type}">
      <div class="card-header">
        <div class="card-icon-type">
          <span class="card-icon">{icon}</span>
          <span class="card-type">{source_type.replace("_"," ").title()}</span>
        </div>
        <span class="card-date">{date}</span>
      </div>
      <div class="card-title"><a href="{folder}/index.html">{title}</a></div>
      <div class="card-summary">{summary}…</div>
      <div class="card-footer">
        <div class="tags">{"".join(f'<span class="tag">{t}</span>' for t in tags[:3])}</div>
        <a class="read-link" href="{folder}/index.html">Read →</a>
      </div>
    </div>
    """

    updated_html = existing_html.replace("<!-- NEW_ENTRY -->", new_entry + "\n    <!-- NEW_ENTRY -->")

    if existing_sha:
        repo.update_file(index_path, f"Index: add {title}", updated_html, existing_sha)
    else:
        repo.create_file(index_path, f"Index: add {title}", updated_html)


def _base_index_html() -> str:
    return """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Knowledge Repository</title>
<style>
  :root[data-theme="dark"] {
    --bg:#0b0d14; --surface:#13172a; --surface2:#1a1f35;
    --border:#232840; --text:#e8eaf0; --text2:#7b82a8; --text3:#4a5080;
    --accent:#6366f1; --shadow:rgba(0,0,0,0.4);
    --tag-bg:#1a2040; --tag-color:#818cf8; --tag-border:#2d3464;
    --topbar-bg:#13172a;
  }
  :root[data-theme="light"] {
    --bg:#f4f5fb; --surface:#ffffff; --surface2:#f0f1f8;
    --border:#e2e4f0; --text:#1a1d2e; --text2:#6b7280; --text3:#9ca3af;
    --accent:#6366f1; --shadow:rgba(99,102,241,0.08);
    --tag-bg:#eef0ff; --tag-color:#4f46e5; --tag-border:#c7d2fe;
    --topbar-bg:#ffffff;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,sans-serif; min-height:100vh; transition:background 0.3s,color 0.3s; }

  .topbar { background:var(--topbar-bg); border-bottom:1px solid var(--border); padding:14px 32px;
    display:flex; align-items:center; justify-content:space-between; position:sticky; top:0; z-index:10;
    box-shadow:0 1px 12px var(--shadow); }
  .logo { font-size:17px; font-weight:800; display:flex; align-items:center; gap:10px; }
  .topbar-right { display:flex; align-items:center; gap:20px; }
  .stats { display:flex; gap:20px; }
  .stat { text-align:center; }
  .stat-num { font-size:17px; font-weight:800; color:var(--accent); }
  .stat-label { font-size:9px; color:var(--text2); text-transform:uppercase; letter-spacing:1px; }

  .theme-toggle { background:var(--surface2); border:1px solid var(--border); border-radius:999px;
    width:52px; height:28px; cursor:pointer; position:relative; transition:all 0.3s; flex-shrink:0; }
  .theme-toggle::before { content:''; position:absolute; top:3px; left:3px; width:20px; height:20px;
    border-radius:50%; background:var(--accent); transition:transform 0.3s; }
  [data-theme="light"] .theme-toggle::before { transform:translateX(24px); }
  .theme-icon { position:absolute; top:50%; transform:translateY(-50%); font-size:11px; }
  .theme-icon.moon { left:6px; }
  .theme-icon.sun  { right:5px; }

  .insights-link { background:var(--accent); color:#fff; border-radius:8px; padding:7px 14px;
    font-size:12px; font-weight:700; text-decoration:none; transition:opacity 0.2s; }
  .insights-link:hover { opacity:0.85; }

  .hero { padding:40px 32px 24px; max-width:1200px; margin:0 auto; }
  .hero h1 { font-size:32px; font-weight:900; margin-bottom:6px; }
  .hero h1 span { color:var(--accent); }
  .hero p { color:var(--text2); font-size:14px; margin-bottom:24px; }

  .controls { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:28px; }
  .search-wrap { flex:1; min-width:240px; position:relative; }
  .search-wrap input { width:100%; background:var(--surface); border:1px solid var(--border);
    color:var(--text); border-radius:10px; padding:10px 14px 10px 38px; font-size:13px; outline:none; transition:border-color 0.2s; }
  .search-wrap input:focus { border-color:var(--accent); }
  .search-icon { position:absolute; left:12px; top:50%; transform:translateY(-50%); color:var(--text2); font-size:13px; }
  .filter-btn { background:var(--surface); border:1px solid var(--border); color:var(--text2);
    border-radius:10px; padding:9px 14px; font-size:12px; cursor:pointer; font-weight:600; transition:all 0.2s; white-space:nowrap; }
  .filter-btn:hover, .filter-btn.active { background:var(--accent); border-color:var(--accent); color:#fff; }

  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:14px;
    max-width:1200px; margin:0 auto; padding:0 32px 48px; }

  .card { background:var(--surface); border:1px solid var(--border); border-radius:14px;
    padding:18px; cursor:pointer; transition:all 0.2s; display:flex; flex-direction:column; gap:10px;
    box-shadow:0 2px 8px var(--shadow); }
  .card:hover { border-color:var(--accent); transform:translateY(-2px); box-shadow:0 8px 28px var(--shadow); }

  .card-header { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; }
  .card-icon-type { display:flex; align-items:center; gap:7px; }
  .card-icon { font-size:18px; }
  .card-type { font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:1.5px;
    color:var(--text2); background:var(--surface2); padding:2px 7px; border-radius:4px; }
  .card-date { font-size:10px; color:var(--text3); white-space:nowrap; }
  .card-title { font-size:14px; font-weight:700; color:var(--text); line-height:1.4; }
  .card-title a { color:inherit; text-decoration:none; }
  .card-title a:hover { color:var(--accent); }
  .card-summary { font-size:12px; color:var(--text2); line-height:1.6; }
  .card-footer { display:flex; align-items:center; justify-content:space-between; margin-top:auto; }
  .tags { display:flex; gap:5px; flex-wrap:wrap; }
  .tag { background:var(--tag-bg); color:var(--tag-color); border:1px solid var(--tag-border);
    padding:2px 8px; border-radius:999px; font-size:10px; font-weight:500; }
  .read-link { font-size:11px; color:var(--accent); text-decoration:none; font-weight:700;
    white-space:nowrap; opacity:0; transition:opacity 0.2s; }
  .card:hover .read-link { opacity:1; }

  @media(max-width:600px) {
    .topbar { padding:10px 16px; }
    .hero { padding:20px 16px 16px; }
    .hero h1 { font-size:22px; }
    .grid { padding:0 14px 32px; }
    .stats { display:none; }
    .insights-link span { display:none; }
  }
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">📚 Knowledge Repository</div>
  <div class="topbar-right">
    <div class="stats">
      <div class="stat"><div class="stat-num" id="total-count">0</div><div class="stat-label">Entries</div></div>
      <div class="stat"><div class="stat-num" id="type-count">0</div><div class="stat-label">Types</div></div>
    </div>
    <a class="insights-link" href="insights.html">✨ <span>Insights</span></a>
    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">
      <span class="theme-icon moon">🌙</span>
      <span class="theme-icon sun">☀️</span>
    </button>
  </div>
</div>

<div class="hero">
  <h1>Your Personal <span>Knowledge Base</span></h1>
  <p>Articles · YouTube · Podcasts · Case Studies · Reports — all in one place</p>
  <div class="controls">
    <div class="search-wrap">
      <span class="search-icon">🔍</span>
      <input id="search" type="text" placeholder="Search by title, topic, or tag..." oninput="filterCards()"/>
    </div>
    <button class="filter-btn active" onclick="filterByType('all',this)">All</button>
    <button class="filter-btn" onclick="filterByType('youtube',this)">▶️ YouTube</button>
    <button class="filter-btn" onclick="filterByType('article',this)">📰 Articles</button>
    <button class="filter-btn" onclick="filterByType('podcast',this)">🎙️ Podcasts</button>
    <button class="filter-btn" onclick="filterByType('report',this)">📊 Reports</button>
  </div>
</div>

<div class="grid" id="grid">
    <!-- NEW_ENTRY -->
</div>

<script>
var activeType = 'all';

function updateStats() {
  var cards = document.querySelectorAll('.card');
  var types = new Set();
  cards.forEach(c => types.add(c.dataset.type));
  document.getElementById('total-count').textContent = cards.length;
  document.getElementById('type-count').textContent = types.size;
}

function filterCards() {
  var q = document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('.card').forEach(c => {
    c.style.display = (c.textContent.toLowerCase().includes(q) && (activeType==='all'||c.dataset.type===activeType)) ? '':'none';
  });
}

function filterByType(type, btn) {
  activeType = type;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterCards();
}

function toggleTheme() {
  var html = document.documentElement;
  var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}

// Restore saved theme
var saved = localStorage.getItem('theme');
if (saved) document.documentElement.setAttribute('data-theme', saved);

updateStats();
</script>
</body>
</html>"""
