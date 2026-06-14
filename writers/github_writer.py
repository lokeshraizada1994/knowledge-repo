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
    <div class="card">
      <div class="card-icon">{icon}</div>
      <div class="card-type">{source_type.replace("_"," ").title()}</div>
      <div class="card-title"><a href="{folder}/index.html">{title}</a></div>
      <div class="card-summary">{summary}…</div>
      <div class="card-meta">
        <span>{date}</span>
        {"".join(f'<span class="tag">{t}</span>' for t in tags[:3])}
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
  :root { --bg:#0f1117; --surface:#1a1f2e; --border:#2d3448; --text:#e8eaf0; --text2:#9aa0b8; --accent:#6366f1; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--text); font-family:system-ui,sans-serif; padding:32px; }
  h1 { font-size:28px; font-weight:800; margin-bottom:8px; }
  .subtitle { color:var(--text2); margin-bottom:32px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:16px; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px; }
  .card-icon { font-size:24px; margin-bottom:8px; }
  .card-type { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:var(--text2); margin-bottom:6px; }
  .card-title a { font-size:15px; font-weight:700; color:var(--text); text-decoration:none; }
  .card-title a:hover { color:var(--accent); }
  .card-summary { font-size:12px; color:var(--text2); margin:8px 0; line-height:1.5; }
  .card-meta { display:flex; gap:8px; flex-wrap:wrap; align-items:center; font-size:11px; color:var(--text2); margin-top:10px; }
  .tag { background:#1e2d4a; color:#60a5fa; padding:2px 8px; border-radius:999px; font-size:10px; }
  input#search { width:100%; max-width:400px; background:var(--surface); border:1px solid var(--border);
    color:var(--text); border-radius:8px; padding:10px 14px; font-size:13px; margin-bottom:24px; outline:none; }
</style>
</head>
<body>
<h1>📚 Knowledge Repository</h1>
<p class="subtitle">Your personal knowledge base — articles, videos, podcasts, reports</p>
<input id="search" type="text" placeholder="Search entries..." oninput="filterCards(this.value)"/>
<div class="grid" id="grid">
    <!-- NEW_ENTRY -->
</div>
<script>
function filterCards(q) {
  q = q.toLowerCase();
  document.querySelectorAll('.card').forEach(c => {
    c.style.display = c.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}
</script>
</body>
</html>"""
