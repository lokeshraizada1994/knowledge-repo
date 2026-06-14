import re
from extractors.youtube import extract_youtube
from extractors.article import extract_article
from extractors.podcast import extract_podcast
from extractors.pdf import extract_pdf

YOUTUBE_PATTERN = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+"
)
PODCAST_EXTENSIONS = (".mp3", ".mp4", ".m4a", ".wav", ".ogg")
PDF_EXTENSION = ".pdf"


def extract_content(email_body: str, subject: str, attachments: list) -> dict:
    body = email_body.strip()

    # PDF attachment takes priority
    for att in attachments:
        name = att.get("filename", "").lower()
        if name.endswith(PDF_EXTENSION):
            return extract_pdf(att["data"], att["filename"])

    # Audio attachment → podcast
    for att in attachments:
        name = att.get("filename", "").lower()
        if any(name.endswith(ext) for ext in PODCAST_EXTENSIONS):
            return extract_podcast(attachment=att)

    # Find first URL in body
    urls = re.findall(r"https?://[^\s]+", body)
    if not urls:
        # Treat plain body text as article content directly
        return {
            "type": "text",
            "title": subject,
            "content": body,
            "source_url": None,
            "author": None,
            "duration": None,
        }

    url = urls[0].rstrip(".,)")

    if YOUTUBE_PATTERN.search(url):
        return extract_youtube(url)

    # Podcast URLs (audio file links)
    if any(url.lower().endswith(ext) for ext in PODCAST_EXTENSIONS):
        return extract_podcast(url=url)

    # Default: treat as article
    return extract_article(url)
