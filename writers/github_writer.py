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
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Knowledge Repository</title>
<style>
  :root {
    --bg:#0b0d14; --surface:#13172a; --surface2:#1a1f35;
    --border:#232840; --text:#e8eaf0; --text2:#7b82a8; --text3:#4a5080;
    --accent:#6366f1; --accent2:#8b5cf6; --green:#22c55e; --yellow:#f59e0b;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,sans-serif; min-height:100vh; }

  .topbar { background:var(--surface); border-bottom:1px solid var(--border); padding:16px 32px;
    display:flex; align-items:center; justify-content:space-between; position:sticky; top:0; z-index:10; }
  .logo { font-size:18px; font-weight:800; display:flex; align-items:center; gap:10px; }
  .logo-icon { font-size:22px; }
  .stats { display:flex; gap:20px; }
  .stat { text-align:center; }
  .stat-num { font-size:18px; font-weight:800; color:var(--accent); }
  .stat-label { font-size:10px; color:var(--text2); text-transform:uppercase; letter-spacing:1px; }

  .hero { padding:48px 32px 32px; max-width:1200px; margin:0 auto; }
  .hero h1 { font-size:36px; font-weight:900; margin-bottom:8px; }
  .hero h1 span { color:var(--accent); }
  .hero p { color:var(--text2); font-size:15px; margin-bottom:28px; }

  .controls { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:32px; }
  .search-wrap { flex:1; min-width:260px; position:relative; }
  .search-wrap input { width:100%; background:var(--surface); border:1px solid var(--border);
    color:var(--text); border-radius:10px; padding:11px 16px 11px 40px; font-size:13px; outline:none;
    transition:border-color 0.2s; }
  .search-wrap input:focus { border-color:var(--accent); }
  .search-icon { position:absolute; left:13px; top:50%; transform:translateY(-50%); color:var(--text2); font-size:14px; }
  .filter-btn { background:var(--surface); border:1px solid var(--border); color:var(--text2);
    border-radius:10px; padding:10px 16px; font-size:12px; cursor:pointer; font-weight:600;
    transition:all 0.2s; white-space:nowrap; }
  .filter-btn:hover, .filter-btn.active { background:var(--accent); border-color:var(--accent); color:#fff; }

  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:16px;
    max-width:1200px; margin:0 auto; padding:0 32px 48px; }

  .card { background:var(--surface); border:1px solid var(--border); border-radius:14px;
    padding:20px; cursor:pointer; transition:all 0.2s; display:flex; flex-direction:column; gap:12px; }
  .card:hover { border-color:var(--accent); transform:translateY(-2px); box-shadow:0 8px 32px rgba(99,102,241,0.15); }

  .card-header { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; }
  .card-icon-type { display:flex; align-items:center; gap:8px; }
  .card-icon { font-size:20px; }
  .card-type { font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:1.5px;
    color:var(--text2); background:var(--surface2); padding:3px 8px; border-radius:4px; }
  .card-date { font-size:10px; color:var(--text3); white-space:nowrap; }

  .card-title { font-size:14px; font-weight:700; color:var(--text); line-height:1.4; }
  .card-title a { color:inherit; text-decoration:none; }
  .card-title a:hover { color:var(--accent); }

  .card-summary { font-size:12px; color:var(--text2); line-height:1.6; }

  .card-footer { display:flex; align-items:center; justify-content:space-between; margin-top:auto; }
  .tags { display:flex; gap:5px; flex-wrap:wrap; }
  .tag { background:#1a2040; color:#818cf8; border:1px solid #2d3464;
    padding:2px 8px; border-radius:999px; font-size:10px; font-weight:500; }
  .read-link { font-size:11px; color:var(--accent); text-decoration:none; font-weight:600;
    white-space:nowrap; opacity:0; transition:opacity 0.2s; }
  .card:hover .read-link { opacity:1; }

  .empty { text-align:center; padding:80px 32px; color:var(--text2); grid-column:1/-1; }
  .empty-icon { font-size:48px; margin-bottom:16px; }

  @media(max-width:600px) {
    .topbar { padding:12px 16px; }
    .hero { padding:24px 16px 16px; }
    .hero h1 { font-size:24px; }
    .grid { padding:0 16px 32px; }
    .stats { display:none; }
  }
</style>
</head>
<body>

<div class="topbar">
  <div class="logo"><span class="logo-icon">📚</span> Knowledge Repository</div>
  <div class="stats">
    <div class="stat"><div class="stat-num" id="total-count">0</div><div class="stat-label">Entries</div></div>
    <div class="stat"><div class="stat-num" id="type-count">0</div><div class="stat-label">Source Types</div></div>
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
    <button class="filter-btn active" onclick="filterByType('all', this)">All</button>
    <button class="filter-btn" onclick="filterByType('youtube', this)">▶️ YouTube</button>
    <button class="filter-btn" onclick="filterByType('article', this)">📰 Articles</button>
    <button class="filter-btn" onclick="filterByType('podcast', this)">🎙️ Podcasts</button>
    <button class="filter-btn" onclick="filterByType('report', this)">📊 Reports</button>
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
    var matchText = c.textContent.toLowerCase().includes(q);
    var matchType = activeType === 'all' || c.dataset.type === activeType;
    c.style.display = (matchText && matchType) ? '' : 'none';
  });
}

function filterByType(type, btn) {
  activeType = type;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterCards();
}

updateStats();
</script>
</body>
</html>"""
