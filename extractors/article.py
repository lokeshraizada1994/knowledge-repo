import requests
from bs4 import BeautifulSoup


def extract_article(url: str) -> dict:
    # 1. Jina reader — clean markdown, no API key needed
    result = _try_jina(url)
    if result:
        return result

    # 2. Freedium bypass for Medium paywalls
    if "medium.com" in url or "medium.com" in url:
        result = _try_freedium(url)
        if result:
            return result

    # 3. 12ft.io bypass for CDN-blocked sites
    result = _try_12ft(url)
    if result:
        return result

    # 4. Direct scrape
    result = _try_direct(url)
    if result:
        return result

    # 5. Playwright headless browser (last resort before giving up)
    result = _try_playwright(url)
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
