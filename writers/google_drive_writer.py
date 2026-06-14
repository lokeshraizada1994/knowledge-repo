"""
Google Drive fallback writer.

When all content extraction fails, uploads a plain text file to your
'Knowledge Pending' Drive folder with the URL and instructions.

Required Railway env vars:
  GOOGLE_SERVICE_ACCOUNT_JSON  — full JSON string of the service account key
  GOOGLE_DRIVE_FOLDER_ID       — ID of the Drive folder to write into

Only requires Google Drive API (not Docs API).
"""
import os
import json
import io


def write_pending_doc(url: str, title: str, subject: str) -> str | None:
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not sa_json or not folder_id:
        print("[Drive] Not configured — skipping")
        return None

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaInMemoryUpload

        creds = Credentials.from_service_account_info(
            json.loads(sa_json),
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        drive_svc = build("drive", "v3", credentials=creds)

        file_name = f"[PENDING] {title or subject or url}.txt"

        body_text = (
            f"SOURCE URL\n{url}\n\n"
            f"EMAIL SUBJECT\n{subject}\n\n"
            f"STATUS\nAutomatic extraction failed (site blocked all scrapers).\n\n"
            f"INSTRUCTIONS\n"
            f"1. Open the article in your browser: {url}\n"
            f"2. Select all text (Ctrl+A) and copy.\n"
            f"3. Paste the content below this line.\n"
            f"4. Save this file, export as PDF, and email to lokesh.ai1994@gmail.com\n"
            f"   with subject: {subject}\n\n"
            f"--- PASTE ARTICLE CONTENT BELOW ---\n\n"
        )

        media = MediaInMemoryUpload(
            body_text.encode("utf-8"),
            mimetype="text/plain",
            resumable=False,
        )

        file_meta = {
            "name": file_name,
            "parents": [folder_id],
        }

        result = drive_svc.files().create(
            body=file_meta,
            media_body=media,
            fields="id, webViewLink",
        ).execute()

        file_url = result.get("webViewLink", f"https://drive.google.com/file/d/{result['id']}/view")
        print(f"[Drive] Pending file created: {file_url}")
        return file_url

    except Exception as e:
        print(f"[Drive] Failed to create pending file: {e}")
        return None
