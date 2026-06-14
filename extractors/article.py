import requests
from bs4 import BeautifulSoup

# Any single one of these is enough to reject the content
_HARD_BLOCK_SIGNALS = [
    "access denied",
    "403 forbidden",
    "verify you are human",
    "checking your browser",
    "ddos protection by",
    "enable javascript and cookies",
    "just a moment...",
    "captcha",
    "ray id",          # Cloudflare Ray ID footer
    "subscription required",
    "sign in to read",
    "create a free account to continue",
    "this content is for subscribers",
    "please enable cookies",
]

# Two or more of these together also signal a block page
_SOFT_BLOCK_SIGNALS = [
    "cloudflare",
    "enable javascript",
    "too many requests",
    "this page isn't working",
    "403",
    "forbidden",
]


def _is_blocked_content(text: str) -> bool:
    """Return True if the extracted text looks like a block/error page."""
    if not text or len(text.strip()) < 300:
        return True
    sample = text[:3000].lower()
    # Any single hard signal is enough
    if any(s in sample for s in _HARD_BLOCK_SIGNALS):
        return True
    # Two or more soft signals together
    if sum(1 for s in _SOFT_BLOCK_SIGNALS if s in sample) >= 2:
        return True
    return False


def extract_article(url: str) -> dict:
    # 1. Jina reader — clean markdown, no API key needed
    result = _try_jina(url)
    if result and not _is_blocked_content(result.get("content", "")):
        return result

    # 2. Freedium bypass for Medium paywalls
    if "medium.com" in url:
        result = _try_freedium(url)
        if result and not _is_blocked_content(result.get("content", "")):
            return result

    # 3. 12ft.io bypass for CDN-blocked sites
    result = _try_12ft(url)
    if result and not _is_blocked_content(result.get("content", "")):
        return result

    # 4. Direct scrape
    result = _try_direct(url)
    if result and not _is_blocked_content(result.get("content", "")):
        return result

    # 5. Playwright headless browser (last resort before giving up)
    result = _try_playwright(url)
    if result and not _is_blocked_content(result.get("content", "")):
        return result

    # 6. Last resort: extract whatever meta/og tags exist even on blocked pages
    result = _try_meta_extraction(url)
    if result:
        return result

    return {
        "type": "article",
        "title": url,
        "author": None,
        "content": None,  # None signals complete failure to main.py
        "source_url": url,
        "duration": None,
    }


# ---------------------------------------------------------------------------
# Individual scrapers
# ---------------------------------------------------------------------------

def _try_jina(url: str) -> dict | None:
    try:
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            timeout=20,
            headers={"Accept": "text/plain"},
        )
        if resp.status_code == 200 and len(resp.text) > 200:
            content = resp.text
            return _build_result(url, content, _extract_title_from_markdown(content))
    except Exception:
        pass
    return None


def _try_freedium(url: str) -> dict | None:
    """Bypass Medium paywall via freedium.cfd."""
    try:
        bypass_url = f"https://freedium.cfd/{url}"
        resp = requests.get(bypass_url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KnowledgeBot/1.0)"
        })
        if resp.status_code == 200:
            return _parse_html(resp.text, url)
    except Exception:
        pass
    return None


def _try_12ft(url: str) -> dict | None:
    """Bypass CDN/paywall via 12ft.io proxy."""
    try:
        resp = requests.get(
            f"https://12ft.io/proxy?q={url}",
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (compatible; KnowledgeBot/1.0)"},
        )
        if resp.status_code == 200 and len(resp.text) > 500:
            return _parse_html(resp.text, url)
    except Exception:
        pass
    return None


def _try_direct(url: str) -> dict | None:
    """Direct HTTP scrape."""
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KnowledgeBot/1.0)"
        })
        if resp.status_code == 200:
            return _parse_html(resp.text, url)
    except Exception:
        pass
    return None


def _try_playwright(url: str) -> dict | None:
    """Headless Chromium render — bypasses JS gating and many CDN checks."""
    try:
        from extractors.playwright_extractor import extract_with_playwright
        text = extract_with_playwright(url)
        if text:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            title = lines[0][:120] if lines else url
            content = "\n".join(lines)
            return _build_result(url, content, title)
    except Exception as e:
        print(f"[Article] Playwright error: {e}")
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_html(html: str, url: str) -> dict | None:
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url
        main = soup.find("article") or soup.find("main") or soup.find("body")
        content = main.get_text(separator="\n", strip=True) if main else ""
        if len(content) < 200:
            return None
        return {
            "type": "article",
            "title": title,
            "author": _extract_author(soup),
            "content": content,
            "source_url": url,
            "duration": _estimate_read_time(content),
        }
    except Exception:
        return None


def _build_result(url: str, content: str, title: str = None) -> dict:
    return {
        "type": "article",
        "title": title or url,
        "author": None,
        "content": content,
        "source_url": url,
        "duration": _estimate_read_time(content),
    }


def _try_meta_extraction(url: str) -> dict | None:
    """
    Last resort: fetch the raw HTML and extract whatever is in <head> meta tags.
    Even sites that block scraping usually return og:title, og:description,
    JSON-LD structured data, and sometimes a preview paragraph in the HTML.
    Returns a partial content dict flagged as [PARTIAL] so Claude knows to note limitations.
    """
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KnowledgeBot/1.0)"
        })
        soup = BeautifulSoup(resp.text, "html.parser")

        # og: and twitter: meta tags
        meta_fields = {}
        for tag in soup.find_all("meta"):
            prop = tag.get("property") or tag.get("name") or ""
            content = tag.get("content", "").strip()
            if content and any(k in prop.lower() for k in ["og:", "twitter:", "description", "author", "keywords"]):
                meta_fields[prop] = content

        # JSON-LD structured data
        import json as _json
        json_ld_texts = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = _json.loads(script.string or "")
                if isinstance(data, dict):
                    for field in ["description", "articleBody", "abstract", "text"]:
                        if data.get(field):
                            json_ld_texts.append(data[field])
                    if data.get("name"):
                        meta_fields.setdefault("og:title", data["name"])
                    if data.get("author"):
                        author = data["author"]
                        if isinstance(author, dict):
                            meta_fields.setdefault("author", author.get("name", ""))
            except Exception:
                pass

        title = (
            meta_fields.get("og:title")
            or meta_fields.get("twitter:title")
            or (soup.find("title") and soup.find("title").get_text(strip=True))
            or url
        )
        description = (
            meta_fields.get("og:description")
            or meta_fields.get("twitter:description")
            or meta_fields.get("description")
            or ""
        )
        author = meta_fields.get("author") or meta_fields.get("article:author") or None
        keywords = meta_fields.get("keywords") or meta_fields.get("article:tag") or ""

        parts = []
        if description:
            parts.append(f"Page description: {description}")
        if keywords:
            parts.append(f"Keywords/topics: {keywords}")
        parts.extend(json_ld_texts)

        content = "\n\n".join(parts)
        if not content or len(content) < 80:
            return None

        content = (
            "[PARTIAL CONTENT — site blocked full extraction. "
            "Only meta tags and structured data were accessible. "
            "Summarise only what is explicitly stated below.]\n\n" + content
        )

        return {
            "type": "article",
            "title": title,
            "author": author,
            "content": content,
            "source_url": url,
            "duration": None,
        }
    except Exception:
        return None


def _extract_title_from_markdown(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("Title:"):
            return line[6:].strip()
    return None


def _extract_author(soup: BeautifulSoup) -> str | None:
    for selector in ['[rel="author"]', '[class*="author"]', '[name="author"]']:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return None


def _estimate_read_time(text: str) -> str:
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return f"~{minutes} min read"
