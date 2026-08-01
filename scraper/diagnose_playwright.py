"""
One-off reconnaissance tool #2: loads Randalls/Tom Thumb pages in real headless
Chromium and logs every XHR/fetch request the page makes, plus the full
response body for the product-search and store-resolver calls specifically,
so albertsons_scraper.py's endpoints and JSON parsing can be corrected against
real traffic (invisible from a plain requests-based fetch of the raw HTML).

Usage: python -m scraper.diagnose_playwright
Requires `playwright install chromium` first. Run via the "Diagnose Albertsons
endpoints (browser)" GitHub Action -- this sandbox has no route to these sites.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from . import config

STATIC_EXT = (".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2", ".ico", ".gif", ".webp")
BODY_OF_INTEREST = ("pgmsearch", "storeresolver")

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

        def on_response(response):
            url = response.url
            if not any(k in url for k in BODY_OF_INTEREST):
                return
            try:
                headers = response.request.headers
                interesting_headers = {
                    k: v for k, v in headers.items() if "key" in k.lower() or "subscription" in k.lower() or "auth" in k.lower()
                }
                body = response.text()
            except Exception as exc:
                print(f"\n--- response body for {url} ---\n  (could not read: {exc})")
                return
            print(f"\n--- response for {url} ---")
            print(f"  status: {response.status}")
            print(f"  request headers of interest: {interesting_headers}")
            print(f"  body[:4000]: {body[:4000]}")

        page.on("request", on_request)
        page.on("response", on_response)

        for label, path in PAGES:
            url = f"https://{host}{path}"
            print(f"-- navigating to {label}: {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as exc:
                print(f"   navigation issue (continuing anyway): {exc}")
            page.wait_for_timeout(4000)

        print(f"\n{len(seen)} non-static requests captured (see above for full bodies of pgmsearch/storeresolver calls).")

        browser.close()


def main() -> None:
    for _, host in config.ALBERTSONS_BANNERS:
        scan(host)


if __name__ == "__main__":
    main()
