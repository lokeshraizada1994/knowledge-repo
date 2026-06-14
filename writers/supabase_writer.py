import os
import json
import requests


def _get_headers():
    key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }


def _get_url():
    base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    return f"{base}/rest/v1/knowledge_entries"


def write_to_supabase(card: dict, github_url: str = None, notion_url: str = None):
    meta = card.get("metadata", {})

    takeaways = card.get("top_5_takeaways", {}).get("content", [])
    takeaway_text = " | ".join(t.get("point", "") for t in takeaways)

    actions = card.get("actionables", {}).get("content", [])
    action_text = " | ".join(actions) if isinstance(actions, list) else str(actions)

    record = {
        "title":              meta.get("title", "Untitled"),
        "source_type":        meta.get("source_type", "article"),
        "source_url":         meta.get("source_url"),
        "author":             meta.get("author"),
        "date_processed":     meta.get("date_processed"),
        "tags":               meta.get("tags", []),
        "duration":           meta.get("estimated_duration"),
        "github_url":         github_url,
        "notion_url":         notion_url,
        "executive_summary":  card.get("executive_summary", {}).get("content", ""),
        "top_takeaways":      takeaway_text,
        "actionables":        action_text,
        "thinking_framework": str(card.get("thinking_framework", {}).get("content", "")),
        "whats_ahead":        str(card.get("whats_ahead", {}).get("content", "")),
        "full_card_json":     json.dumps(card),
    }

    resp = requests.post(_get_url(), headers=_get_headers(), json=record, timeout=15)

    if resp.status_code not in (200, 201):
        raise Exception(f"Supabase insert failed: {resp.status_code} — {resp.text}")
