import os
import json
from supabase import create_client, ClientOptions

_client = None


def _get_client():
    global _client
    if _client:
        return _client
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    if not url or not key:
        raise ValueError(f"Supabase config missing — URL={bool(url)} KEY={bool(key)}")
    _client = create_client(url, key, options=ClientOptions(auto_refresh_token=False, persist_session=False))
    return _client


def write_to_supabase(card: dict, github_url: str = None, notion_url: str = None):
    client = _get_client()
    meta = card.get("metadata", {})

    # Flatten card into a searchable record
    takeaways = card.get("top_5_takeaways", {}).get("content", [])
    takeaway_text = " | ".join(t.get("point", "") for t in takeaways)

    actions = card.get("actionables", {}).get("content", [])
    action_text = " | ".join(actions) if isinstance(actions, list) else str(actions)

    record = {
        "title":           meta.get("title", "Untitled"),
        "source_type":     meta.get("source_type", "article"),
        "source_url":      meta.get("source_url"),
        "author":          meta.get("author"),
        "date_processed":  meta.get("date_processed"),
        "tags":            meta.get("tags", []),
        "duration":        meta.get("estimated_duration"),
        "github_url":      github_url,
        "notion_url":      notion_url,
        "executive_summary": card.get("executive_summary", {}).get("content", ""),
        "top_takeaways":   takeaway_text,
        "actionables":     action_text,
        "thinking_framework": str(card.get("thinking_framework", {}).get("content", "")),
        "whats_ahead":     str(card.get("whats_ahead", {}).get("content", "")),
        "full_card_json":  json.dumps(card),
    }

    client.table("knowledge_entries").insert(record).execute()
