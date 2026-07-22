"""Reset the GitHub Pages index to remove duplicates."""
import os
import sys
from dotenv import load_dotenv
from github import Github, Auth

load_dotenv()
gh = Github(auth=Auth.Token(os.getenv("GITHUB_TOKEN")))
repo = gh.get_user("lokeshraizada1994").get_repo("knowledge-repo")

sys.path.insert(0, ".")
from writers.github_writer import _base_index_html, _update_index
from writers.github_writer import _get_repo

# Get all entries from GitHub
entries_dir = repo.get_contents("entries")

# Build fresh index
fresh_index = _base_index_html()

# Inject each entry once
for folder in sorted(entries_dir, key=lambda x: x.path, reverse=True):
    folder_path = folder.path
    try:
        data_file = repo.get_contents(f"{folder_path}/data.json")
        import json
        card = json.loads(data_file.decoded_content.decode("utf-8"))
        meta = card.get("metadata", {})
        title = meta.get("title", "Untitled")
        date = meta.get("date_processed", "")
        source_type = meta.get("source_type", "article")
        tags = meta.get("tags", [])
        tldr = card.get("tldr", [])
        summary = (tldr[0] if tldr else "")[:200]

        icons = {"youtube": "▶️", "podcast": "🎙️", "article": "📰",
                 "case_study": "📋", "report": "📊", "text": "📝"}
        icon = icons.get(source_type, "📄")

        new_entry = f"""
    <div class="card" data-type="{source_type}">
      <div class="card-header">
        <div class="card-icon-type">
          <span class="card-icon">{icon}</span>
          <span class="card-type">{source_type.replace("_"," ").title()}</span>
        </div>
        <span class="card-date">{date}</span>
      </div>
      <div class="card-title"><a href="{folder_path}/index.html">{title}</a></div>
      <div class="card-summary">{summary}...</div>
      <div class="card-footer">
        <div class="tags">{"".join(f'<span class="tag">{t}</span>' for t in tags[:3])}</div>
        <a class="read-link" href="{folder_path}/index.html">Read →</a>
      </div>
    </div>
    """
        fresh_index = fresh_index.replace("<!-- NEW_ENTRY -->", new_entry + "\n    <!-- NEW_ENTRY -->")
        print(f"Added: {title}")
    except Exception as e:
        print(f"Skipped {folder_path}: {e}")

# Push clean index
existing = repo.get_contents("index.html")
repo.update_file("index.html", "Reset: clean index with no duplicates", fresh_index, existing.sha)
print("Done — index reset successfully!")
