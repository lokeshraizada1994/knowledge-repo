import requests
from bs4 import BeautifulSoup


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
    except Exception:
        pass

    # Fallback: direct scrape with BeautifulSoup
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KnowledgeBot/1.0)"
        })
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove nav, footer, scripts
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = soup.find("title")
        title = title.get_text(strip=True) if title else url

        # Try article tag first, then main, then body
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
