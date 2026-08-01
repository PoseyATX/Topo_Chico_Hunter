"""
One-off reconnaissance tool: fetches a handful of Randalls/Tom Thumb pages and
scans them for embedded API references (inline JSON state, script bundle
URLs, anything mentioning "api"/"graphql"/etc.) so the real endpoints in
albertsons_scraper.py can be corrected without guessing blind.

Usage: python -m scraper.diagnose
Run via the "Diagnose Albertsons endpoints" GitHub Action (workflow_dispatch)
to see real output, since this sandbox has no route to these sites.
"""

from __future__ import annotations

import re

import requests

from . import config

HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

PAGES = [
    "/",
    "/robots.txt",
    "/shop/search-results.html?q=021136050462",
    "/store-locator.html",
]

KEYWORD_PATTERN = re.compile(
    r'["\']?(?:[a-zA-Z0-9_-]*api[a-zA-Z0-9_-]*|graphql|algolia|coveo|endpoint|baseUrl|storeLocator|__NEXT_DATA__|__INITIAL_STATE__|__PRELOADED_STATE__)["\']?\s*[:=]\s*["\']?[^\s"\'<>]{0,120}',
    re.IGNORECASE,
)


def scan(host: str) -> None:
    print(f"\n=== {host} ===")
    for path in PAGES:
        url = f"https://{host}{path}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        except requests.RequestException as exc:
            print(f"{url} -> request error: {exc}")
            continue
        print(f"{url} -> HTTP {resp.status_code}, {len(resp.text)} bytes, final URL {resp.url}")
        if resp.status_code >= 400:
            print(f"  body[:300]: {resp.text[:300]!r}")
            continue
        matches = KEYWORD_PATTERN.findall(resp.text)
        seen = []
        for m in matches:
            if m not in seen:
                seen.append(m)
        if seen:
            print(f"  {len(seen)} distinct api-ish matches (first 40):")
            for m in seen[:40]:
                print(f"    {m}")
        else:
            print("  no api-ish keywords found in body")


def main() -> None:
    for _, host in config.ALBERTSONS_BANNERS:
        scan(host)


if __name__ == "__main__":
    main()
