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
        # Step 1: Extract content from URL/attachment
        content = extract_content(email_body, email_subject, attachments)
        print(f"[Pipeline] Content extracted — type: {content['type']}")

        # Step 2: Process with Claude
        knowledge_card = process_content(content)
        print(f"[Pipeline] Knowledge card generated")

        # Step 3: Render visual HTML card
        html_card = render_card(knowledge_card)
        print(f"[Pipeline] HTML card rendered")

        # Step 4: Write to all stores
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

        # Return 200 as long as GitHub succeeded — prevents Gmail watcher retrying
        return jsonify({
            "status": "success",
            "title": knowledge_card.get("metadata", {}).get("title"),
            "notion_url": notion_url,
            "github_url": github_url
        })

    except Exception as e:
        import traceback
        print(f"[Pipeline] Error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
