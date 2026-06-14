"""Playwright headless browser fallback for blocked articles."""


def extract_with_playwright(url: str) -> str | None:
    """Render URL in headless Chromium. Returns page text or None."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)  # let JS settle

            # Remove nav/footer/ads before extracting
            page.evaluate("""
                ['nav','footer','header','aside','[class*="ad"]','[id*="ad"]'].forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
            """)

            text = page.evaluate("""
                () => {
                    const main = document.querySelector('article') ||
                                 document.querySelector('main') ||
                                 document.querySelector('[role="main"]') ||
                                 document.body;
                    return main ? main.innerText : document.body.innerText;
                }
            """)
            browser.close()
            return text if text and len(text.strip()) > 300 else None
    except Exception as e:
        print(f"[Playwright] Failed: {e}")
        return None
