import requests
from bs4 import BeautifulSoup

# Ordered list of proxy services to try when a site blocks direct access
_BYPASS_PROXIES = [
    lambda u: f"https://12ft.io/proxy?q={u}",
    lambda u: f"https://r.jina.ai/{u}",  # retry Jina via bypass path
]


def extract_article(url: str) -> dict:
    # Try Jina reader first — returns clean markdown, no API key needed
    jina_url = f"https://r.jina.ai/{url}"
    try:
        resp = requests.get(jina_url, timeout=20, headers={"Accept": "text/plain"})
        if resp.status_code == 200 and len(resp.text) > 200:
            content = resp.text
            title = _extract_title_from_markdown(content) or url
            return {
                "type": "article",
                "title": title,
                "author": None,
                "content": content,
                "source_url": url,
                "duration": _estimate_read_time(content),
            }
        jina_blocked = resp.status_code in (403, 429, 451)
    except Exception:
        jina_blocked = True

    # If Jina was blocked, try 12ft.io bypass before direct scrape
    if jina_blocked:
        result = _try_bypass(url)
        if result:
            return result

    # Fallback: direct scrape with BeautifulSoup
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KnowledgeBot/1.0)"
        })
        if resp.status_code in (403, 429, 451):
            # Direct scrape also blocked — try bypass now
            result = _try_bypass(url)
            if result:
                return result
            return {
                "type": "article",
                "title": url,
                "author": None,
                "content": f"[Access blocked ({resp.status_code}): {url} — site requires subscription or blocks scrapers]",
                "source_url": url,
                "duration": None,
            }

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = soup.find("title")
        title = title.get_text(strip=True) if title else url

        main = soup.find("article") or soup.find("main") or soup.find("body")
        content = main.get_text(separator="\n", strip=True) if main else ""

        return {
            "type": "article",
            "title": title,
            "author": _extract_author(soup),
            "content": content,
            "source_url": url,
            "duration": _estimate_read_time(content),
        }
    except Exception as e:
        return {
            "type": "article",
            "title": url,
            "author": None,
            "content": f"[Could not extract content: {e}]",
            "source_url": url,
            "duration": None,
        }


def _try_bypass(url: str) -> dict | None:
    """Try 12ft.io to bypass paywalls/blocks. Returns result dict or None."""
    bypass_url = f"https://12ft.io/proxy?q={url}"
    try:
        resp = requests.get(bypass_url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KnowledgeBot/1.0)"
        })
        if resp.status_code == 200 and len(resp.text) > 500:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else url
            main = soup.find("article") or soup.find("main") or soup.find("body")
            content = main.get_text(separator="\n", strip=True) if main else ""
            if len(content) > 300:
                return {
                    "type": "article",
                    "title": title,
                    "author": _extract_author(soup),
                    "content": content,
                    "source_url": url,
                    "duration": _estimate_read_time(content),
                }
    except Exception:
        pass
    return None


def _extract_title_from_markdown(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("Title:"):
            return line[6:].strip()
    return None


def _extract_author(soup: BeautifulSoup):
    for selector in ['[rel="author"]', '[class*="author"]', '[name="author"]']:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return None


def _estimate_read_time(text: str) -> str:
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return f"~{minutes} min read"
