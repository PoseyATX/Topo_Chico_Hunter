"""
One-off reconnaissance tool #2: loads Randalls/Tom Thumb search pages in real
headless Chromium and deterministically waits for the pgmsearch (product
search) response, printing its full body -- needed to know the real field
names for availability/stock status before albertsons_scraper.py can parse it
correctly. Also tries a `zipcode` query param on the search URL to see whether
it changes which store gets selected (needed for multi-city coverage).

Usage: python -m scraper.diagnose_playwright
Requires `playwright install chromium` first. Run via the "Diagnose Albertsons
endpoints (browser)" GitHub Action -- this sandbox has no route to these sites.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from . import config


def check(host: str, banner: str, zip_code: str | None) -> None:
    label = f"{host} zipcode={zip_code}"
    print(f"\n=== {label} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=config.USER_AGENT)
        page = context.new_page()

        q = f"/shop/search-results.html?q={config.UPC}"
        if zip_code:
            q += f"&zipcode={zip_code}"
        url = f"https://{host}{q}"

        try:
            with page.expect_response(lambda r: "pgmsearch" in r.url, timeout=25000) as resp_info:
                page.goto(url, timeout=30000)
            response = resp_info.value
            print(f"pgmsearch -> HTTP {response.status}")
            print(f"  url: {response.url}")
            try:
                print(f"  body[:6000]: {response.text()[:6000]}")
            except Exception as exc:
                print(f"  (could not read body: {exc})")
        except Exception as exc:
            print(f"pgmsearch did not fire within timeout: {exc}")

        browser.close()


def main() -> None:
    for banner, host in config.ALBERTSONS_BANNERS:
        check(host, banner, None)
    # Does a zipcode query param change the resolved store? Test with Austin
    # (far from both banners' default/home stores) on Randalls only to keep
    # this diagnostic quick.
    check("www.randalls.com", "Randalls", "78701")


if __name__ == "__main__":
    main()
