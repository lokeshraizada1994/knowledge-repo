"""
Pending card writer — fallback when all content extraction fails.

Instead of Google Drive (service accounts have no storage quota on personal Gmail),
writes a 'pending' card to GitHub Pages so it shows up in your knowledge base UI.
The card links directly to the original URL so you can open it manually.
"""
import os
from datetime import datetime


def write_pending_doc(url: str, title: str, subject: str) -> str | None:
    try:
        from github import Github
        gh = Github(os.getenv("GITHUB_TOKEN"))
        username = os.getenv("GITHUB_USERNAME")
        repo_name = os.getenv("GITHUB_REPO", "knowledge-repo")
        repo = gh.get_user(username).get_repo(repo_name)

        date = datetime.utcnow().strftime("%Y-%m-%d")
        slug = "".join(c if c.isalnum() else "-" for c in (title or subject or "pending").lower())[:50]
        folder = f"pending/{date}-{slug}"

        display_title = title or subject or url

        html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>[Pending] {display_title}</title>
<style>
  body {{ background:#0b0d14; color:#e8eaf0; font-family:system-ui,sans-serif;
    display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
  .box {{ background:#13172a; border:1px solid #232840; border-radius:16px;
    padding:40px; max-width:600px; text-align:center; }}
  h1 {{ color:#f59e0b; font-size:20px; margin-bottom:12px; }}
  p {{ color:#7b82a8; font-size:14px; line-height:1.7; margin:8px 0; }}
  a {{ color:#6366f1; }}
  .url {{ background:#1a1f35; border-radius:8px; padding:12px 16px;
    font-family:monospace; font-size:12px; color:#a5b4fc; word-break:break-all; margin:16px 0; }}
  .steps {{ text-align:left; background:#1a1f35; border-radius:8px;
    padding:16px 20px; margin-top:20px; font-size:13px; line-height:2; }}
</style>
</head>
<body>
<div class="box">
  <h1>⏳ Pending — Manual extraction needed</h1>
  <p><strong>{display_title}</strong></p>
  <p>All automatic scrapers were blocked by this site.<br/>
  Open the article, copy the text, and re-email it as a PDF.</p>
  <div class="url">{url}</div>
  <div class="steps">
    <strong>Steps:</strong><br/>
    1. <a href="{url}" target="_blank">Open the article ↗</a><br/>
    2. Select all text (Ctrl+A) and copy<br/>
    3. Paste into a Word doc / Google Doc<br/>
    4. Export as PDF<br/>
    5. Email the PDF to <strong>lokesh.ai1994@gmail.com</strong>
  </div>
</div>
</body>
</html>"""

        # Write pending card HTML
        try:
            existing = repo.get_contents(f"{folder}/index.html")
            repo.update_file(f"{folder}/index.html", f"Pending: {display_title}", html, existing.sha)
        except Exception:
            repo.create_file(f"{folder}/index.html", f"Pending: {display_title}", html)

        # Add to index as a pending card
        _add_pending_to_index(repo, display_title, url, date, folder)

        pages_url = f"https://{username}.github.io/{repo_name}/{folder}/"
        print(f"[Pending] Card created on GitHub Pages: {pages_url}")
        return pages_url

    except Exception as e:
        print(f"[Pending] Failed to create pending card: {e}")
        return None


def _add_pending_to_index(repo, title: str, url: str, date: str, folder: str):
    try:
        index_file = repo.get_contents("index.html")
        existing_html = index_file.decoded_content.decode("utf-8")

        new_entry = f"""
    <div class="card" data-type="pending">
      <div class="card-header">
        <div class="card-icon-type">
          <span class="card-icon">⏳</span>
          <span class="card-type" style="background:#2a1a00;color:#f59e0b;border-color:#7c4a00;">Pending</span>
        </div>
        <span class="card-date">{date}</span>
      </div>
      <div class="card-title"><a href="{folder}/index.html">{title}</a></div>
      <div class="card-summary" style="color:#f59e0b;">Site blocked automatic extraction. Click to see manual steps.</div>
      <div class="card-footer">
        <div class="tags"><span class="tag">needs-manual</span></div>
        <a class="read-link" href="{folder}/index.html">View →</a>
      </div>
    </div>
    """
        updated = existing_html.replace("<!-- NEW_ENTRY -->", new_entry + "\n    <!-- NEW_ENTRY -->")
        repo.update_file("index.html", f"Index: pending — {title}", updated, index_file.sha)
    except Exception as e:
        print(f"[Pending] Could not update index: {e}")
