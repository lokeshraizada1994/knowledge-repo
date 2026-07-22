import os
from notion_client import Client

notion = Client(auth=os.getenv("NOTION_TOKEN"))
PAGE_ID = os.getenv("NOTION_PAGE_ID", "").replace("-", "")

_database_id = None


def _get_or_create_database() -> str:
    global _database_id
    if _database_id:
        return _database_id

    # Search for existing database under the page
    results = notion.search(query="Knowledge Repository", filter={"property": "object", "value": "database"})
    for r in results.get("results", []):
        if r.get("parent", {}).get("page_id", "").replace("-", "") == PAGE_ID:
            _database_id = r["id"]
            return _database_id

    # Create it
    db = notion.databases.create(
        parent={"type": "page_id", "page_id": PAGE_ID},
        title=[{"type": "text", "text": {"content": "Knowledge Repository"}}],
        properties={
            "Title":          {"title": {}},
            "Source Type":    {"select": {"options": [
                {"name": "Article",    "color": "blue"},
                {"name": "YouTube",    "color": "red"},
                {"name": "Podcast",    "color": "purple"},
                {"name": "Case Study", "color": "green"},
                {"name": "Report",     "color": "yellow"},
                {"name": "Text",       "color": "gray"},
            ]}},
            "Author":         {"rich_text": {}},
            "Date Processed": {"date": {}},
            "Tags":           {"multi_select": {}},
            "Source URL":     {"url": {}},
            "Duration":       {"rich_text": {}},
            "GitHub URL":     {"url": {}},
        }
    )
    _database_id = db["id"]
    return _database_id


def _text(content: str) -> list:
    # Notion rich_text blocks max 2000 chars each
    chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
    return [{"type": "text", "text": {"content": c}} for c in chunks]


def _heading(text: str, level: int = 2) -> dict:
    tag = f"heading_{level}"
    return {"object": "block", "type": tag, tag: {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _text(str(text))}}


def _bulleted(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _text(str(text))}}


def _numbered(text: str) -> dict:
    return {"object": "block", "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": _text(str(text))}}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _callout(text: str, emoji: str = "💡") -> dict:
    return {"object": "block", "type": "callout",
            "callout": {"rich_text": _text(str(text)), "icon": {"type": "emoji", "emoji": emoji}}}


def _is_na(val) -> bool:
    if isinstance(val, str):
        return val.strip().upper().startswith("N/A")
    return False


def _build_blocks(card: dict) -> list:
    blocks = []

    # TL;DR
    blocks.append(_heading("⚡ TL;DR", 2))
    for line in card.get("tldr", []):
        blocks.append(_bulleted(line))
    blocks.append(_divider())

    # Top Insights
    blocks.append(_heading("🎯 Top Insights", 2))
    for item in card.get("top_insights", []):
        insight = item.get("insight", "")
        why = item.get("why_it_matters", "")
        blocks.append(_numbered(insight + (f" — {why}" if why else "")))
    blocks.append(_divider())

    # Best Example
    blocks.append(_heading("📖 Best Example", 2))
    example = card.get("best_example", {})
    if example.get("present"):
        blocks.append(_callout(example.get("story", ""), "📖"))
    else:
        blocks.append(_paragraph(example.get("reason_absent", "N/A")))
    blocks.append(_divider())

    # Do This
    blocks.append(_heading("✅ Do This", 2))
    do_this = card.get("do_this", {})
    if do_this.get("present"):
        for a in do_this.get("actions", []):
            blocks.append(_numbered(a))
    else:
        blocks.append(_paragraph(do_this.get("reason_absent", "N/A")))
    blocks.append(_divider())

    # The Catch
    blocks.append(_heading("⚠️ The Catch", 2))
    blocks.append(_callout(card.get("the_catch", ""), "⚠️"))
    blocks.append(_divider())

    # Extra sections (flexible, varies per source)
    for sec in card.get("extra_sections", []) or []:
        emoji = sec.get("emoji", "✨")
        sec_title = sec.get("title", "Worth Noting")
        blocks.append(_heading(f"{emoji} {sec_title}", 2))
        content = sec.get("content", [])
        if isinstance(content, list):
            for item in content:
                blocks.append(_bulleted(str(item)))
        else:
            blocks.append(_paragraph(str(content)))
        blocks.append(_divider())

    return blocks


def write_to_notion(card: dict, github_url: str = None) -> str:
    meta = card.get("metadata", {})
    db_id = _get_or_create_database()

    tags = [{"name": t} for t in meta.get("tags", [])]
    source_url = meta.get("source_url") or None
    date = meta.get("date_processed", "")

    properties = {
        "Title":          {"title": _text(meta.get("title", "Untitled"))},
        "Source Type":    {"select": {"name": meta.get("source_type", "Article").replace("_", " ").title()}},
        "Author":         {"rich_text": _text(meta.get("author") or "Unknown")},
        "Date Processed": {"date": {"start": date}} if date else {"date": None},
        "Tags":           {"multi_select": tags},
        "Duration":       {"rich_text": _text(meta.get("estimated_duration") or "")},
    }
    if source_url:
        properties["Source URL"] = {"url": source_url}
    if github_url:
        properties["GitHub URL"] = {"url": github_url}

    blocks = _build_blocks(card)

    # Notion API allows max 100 blocks per create call
    page = notion.pages.create(
        parent={"database_id": db_id},
        properties=properties,
        children=blocks[:100]
    )
    page_id = page["id"]

    # Append remaining blocks if any
    if len(blocks) > 100:
        for i in range(100, len(blocks), 100):
            notion.blocks.children.append(page_id, children=blocks[i:i+100])

    page_url = page.get("url", f"https://notion.so/{page_id.replace('-','')}")
    return page_url
