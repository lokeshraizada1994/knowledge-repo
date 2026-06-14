"""
Google Drive fallback writer.

When all content extraction fails, creates a Google Doc in your Drive folder
with the source URL, subject, and a prompt to manually paste the content.
The pipeline continues; you later open the doc, paste the article, and
re-email it as a PDF attachment.

Required Railway env vars:
  GOOGLE_SERVICE_ACCOUNT_JSON  — full JSON string of the service account key
  GOOGLE_DRIVE_FOLDER_ID       — ID of the Drive folder to write into
"""
import os
import json


def write_pending_doc(url: str, title: str, subject: str) -> str | None:
    """
    Create a Google Doc flagged as 'PENDING — needs manual content'.
    Returns the Doc URL or None if Drive is not configured.
    """
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not sa_json or not folder_id:
        return None

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_service_account_info(
            json.loads(sa_json),
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/documents",
            ],
        )

        docs_svc = build("docs", "v1", credentials=creds)
        drive_svc = build("drive", "v3", credentials=creds)

        doc_title = f"[PENDING] {title or subject or url}"

        # Create the doc
        doc = docs_svc.documents().create(body={"title": doc_title}).execute()
        doc_id = doc["documentId"]
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

        # Write instructions into the doc body
        body_text = (
            f"SOURCE URL\n{url}\n\n"
            f"EMAIL SUBJECT\n{subject}\n\n"
            f"STATUS\nAutomatic extraction failed (site blocked scraping).\n\n"
            f"INSTRUCTIONS\n"
            f"1. Open the article in your browser: {url}\n"
            f"2. Select all text (Ctrl+A) and copy.\n"
            f"3. Paste below this line.\n"
            f"4. Export this doc as PDF (File → Download → PDF).\n"
            f"5. Email the PDF to lokesh.ai1994@gmail.com with subject: {subject}\n\n"
            f"--- PASTE ARTICLE CONTENT BELOW ---\n\n"
        )

        docs_svc.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": body_text,
                        }
                    }
                ]
            },
        ).execute()

        # Move into the designated Drive folder
        drive_svc.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents="root",
            fields="id, parents",
        ).execute()

        print(f"[Drive] Pending doc created: {doc_url}")
        return doc_url

    except Exception as e:
        print(f"[Drive] Failed to create pending doc: {e}")
        return None
