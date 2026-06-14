import os
import json
import hmac
import hashlib
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from extractors.router import extract_content
from processor.claude_processor import process_content
from renderer.card_renderer import render_card
from writers.notion_writer import write_to_notion
from writers.github_writer import write_to_github
from writers.supabase_writer import write_to_supabase

load_dotenv()

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    secret = os.getenv("WEBHOOK_SECRET", "")
    provided = request.headers.get("X-Webhook-Secret", "")
    if secret and provided != secret:
        return jsonify({"error": "Unauthorized"}), 401

    email_body = data.get("body", "")
    email_subject = data.get("subject", "Untitled")
    attachments = data.get("attachments", [])

    print(f"[Pipeline] New email received: {email_subject}")

    try:
        # Step 1: Extract content
        content = extract_content(email_body, email_subject, attachments)
        print(f"[Pipeline] Content extracted — type: {content['type']}")

        # Detect complete extraction failure
        raw_content = content.get("content") or ""
        raw_title = (content.get("title") or "").lower()
        extraction_failed = (
            not raw_content
            or "access denied" in raw_title
            or "403" in raw_title
            or len(raw_content.strip()) < 200
        )
        if extraction_failed:
            print("[Pipeline] All extraction methods failed — creating Drive pending doc")
            drive_url = _create_drive_pending(
                url=content.get("source_url", ""),
                title=content.get("title", email_subject),
                subject=email_subject,
            )
            return jsonify({
                "status": "pending",
                "reason": "Content extraction failed — site blocked all scrapers",
                "drive_doc": drive_url,
                "action": "Open the Google Doc, paste article text, export as PDF, re-email as attachment",
            })

        # Step 2: Process with Claude
        knowledge_card = process_content(content)
        print(f"[Pipeline] Knowledge card generated")

        # Step 3: Render HTML card
        html_card = render_card(knowledge_card)
        print(f"[Pipeline] HTML card rendered")

        # Step 4: Write to stores (GitHub is primary; others are non-blocking)
        github_url = write_to_github(knowledge_card, html_card)
        print(f"[Pipeline] Written to GitHub: {github_url}")

        notion_url = None
        try:
            notion_url = write_to_notion(knowledge_card, github_url)
            print(f"[Pipeline] Written to Notion: {notion_url}")
        except Exception as notion_err:
            print(f"[Pipeline] Notion skipped: {notion_err}")

        try:
            write_to_supabase(knowledge_card, github_url=github_url, notion_url=notion_url)
            print(f"[Pipeline] Written to Supabase")
        except Exception as sb_err:
            print(f"[Pipeline] Supabase skipped: {sb_err}")

        return jsonify({
            "status": "success",
            "title": knowledge_card.get("metadata", {}).get("title"),
            "notion_url": notion_url,
            "github_url": github_url,
        })

    except Exception as e:
        import traceback
        print(f"[Pipeline] Error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


def _create_drive_pending(url: str, title: str, subject: str) -> str | None:
    try:
        from writers.google_drive_writer import write_pending_doc
        return write_pending_doc(url=url, title=title, subject=subject)
    except Exception as e:
        print(f"[Pipeline] Drive pending doc failed: {e}")
        return None


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
