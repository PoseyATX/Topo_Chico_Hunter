"""
One-off reconnaissance tool #2: loads Randalls/Tom Thumb pages in real headless
Chromium and logs every XHR/fetch request the page makes, so the real
product-search and availability API calls (issued by client-side JS after
load, invisible in the raw HTML `diagnose.py` scans) can be observed directly.

Usage: python -m scraper.diagnose_playwright
Requires `playwright install chromium` first. Run via the "Diagnose Albertsons
endpoints (browser)" GitHub Action -- this sandbox has no route to these sites.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from . import config

STATIC_EXT = (".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2", ".ico", ".gif", ".webp")

PAGES = [
    ("home", "/"),
    ("search", "/shop/search-results.html?q=021136050462"),
]


def scan(host: str) -> None:
    print(f"\n=== {host} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=config.USER_AGENT)
        page = context.new_page()

        seen = []

        def on_request(request):
            url = request.url
            if any(url.split("?")[0].endswith(ext) for ext in STATIC_EXT):
                return
            if "randalls.com" not in url and "tomthumb.com" not in url and "albertsons" not in url:
                return
            seen.append((request.method, url))

        page.on("request", on_request)

        for label, path in PAGES:
            url = f"https://{host}{path}"
            print(f"-- navigating to {label}: {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as exc:
                print(f"   navigation issue (continuing anyway): {exc}")
            page.wait_for_timeout(3000)

        print(f"\n{len(seen)} non-static requests captured:")
        for method, url in seen:
            print(f"  {method} {url}")

        browser.close()


def main() -> None:
    for _, host in config.ALBERTSONS_BANNERS:
        scan(host)


if __name__ == "__main__":
    main()
