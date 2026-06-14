import re
from extractors.youtube import extract_youtube
from extractors.article import extract_article
from extractors.podcast import extract_podcast
from extractors.pdf import extract_pdf

YOUTUBE_PATTERN = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+"
)
STREAMING_PATTERN = re.compile(
    r"https?://(www\.)?(soundcloud\.com|open\.spotify\.com|podcasts\.apple\.com|anchor\.fm)/"
)
PODCAST_EXTENSIONS = (".mp3", ".mp4", ".m4a", ".wav", ".ogg")
PDF_EXTENSION = ".pdf"

# Short URL / tracking domains to skip — not actual content
SKIP_DOMAINS = {
    "mck.co", "bit.ly", "tinyurl.com", "t.co", "ow.ly",
    "buff.ly", "goo.gl", "short.io", "rb.gy", "cutt.ly"
}

# High-value content domains — prioritise these if found
PRIORITY_DOMAINS = {
    "mckinsey.com", "hbr.org", "wsj.com", "ft.com", "economist.com",
    "nature.com", "arxiv.org", "substack.com", "medium.com", "forbes.com",
    "techcrunch.com", "wired.com", "mit.edu", "stanford.edu"
}


def _pick_best_url(urls: list) -> str:
    clean = [u.rstrip(".,)>\"'") for u in urls]

    # First pass: YouTube
    for u in clean:
        if YOUTUBE_PATTERN.search(u):
            return u

    # Second pass: priority domains
    for u in clean:
        domain = _get_domain(u)
        if domain in PRIORITY_DOMAINS:
            return u

    # Third pass: skip tracking/short URLs, take first real one
    for u in clean:
        domain = _get_domain(u)
        if domain not in SKIP_DOMAINS:
            return u

    return clean[0]


def _get_domain(url: str) -> str:
    try:
        host = url.split("//")[-1].split("/")[0].lower()
        return host.replace("www.", "")
    except Exception:
        return ""


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

    # Find all URLs in body
    urls = re.findall(r"https?://[^\s<>\"']+", body)
    if not urls:
        return {
            "type": "text",
            "title": subject,
            "content": body,
            "source_url": None,
            "author": None,
            "duration": None,
        }

    url = _pick_best_url(urls)

    if YOUTUBE_PATTERN.search(url):
        return extract_youtube(url)

    if STREAMING_PATTERN.search(url):
        return extract_podcast(url=url)

    if any(url.lower().endswith(ext) for ext in PODCAST_EXTENSIONS):
        return extract_podcast(url=url)

    return extract_article(url)
