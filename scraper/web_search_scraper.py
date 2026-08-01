"""
General web search for the UPC, independent of any specific retailer's store
locator -- catches whatever grocery/retail/wholesale pages are indexed as
carrying this product anywhere, not just a fixed list of Texas chains.

Uses real headless Chromium (Playwright), not `requests`. Confirmed via real
runs: both DuckDuckGo (html and lite endpoints) and Bing serve a
JavaScript-dependent shell with no crawlable result markup to a plain HTTP
client -- there is no working no-JS/no-browser path left for either engine.
A real browser is the only thing that has actually retrieved content from
any bot-aware source in this project (see scraper/albertsons_scraper.py).
Run at a modest rate (once a day), this is a single page load, not a crawl.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, quote, urlparse

from playwright.sync_api import sync_playwright

from . import config

RESULT_SELECTOR = "li.b_algo, #b_results li"
JUNK_DOMAINS = ("bing.com", "microsoft.com", "microsofttranslator.com", "msn.com", "live.com")


@dataclass
class WebMention:
    title: str
    url: str
    snippet: str


def _resolve_bing_redirect(href: str) -> str:
    """Bing wraps organic result links in bing.com/ck/a?...&u=a1<base64url>,
    even in the live, JS-rendered DOM."""
    if "bing.com/ck/a" not in href:
        return href
    qs = parse_qs(urlparse(href).query)
    u = qs.get("u", [""])[0]
    if not u.startswith("a1"):
        return href
    b64 = u[2:]
    b64 += "=" * (-len(b64) % 4)
    try:
        import base64
        return base64.urlsafe_b64decode(b64).decode("utf-8", errors="replace")
    except Exception:
        return href


def search(query: str = config.WEB_SEARCH_QUERY, max_results: int = config.WEB_SEARCH_MAX_RESULTS) -> list[WebMention]:
    mentions: list[WebMention] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=config.USER_AGENT)
            page = context.new_page()
            try:
                page.goto(f"https://www.bing.com/search?q={quote(query)}", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                items = page.query_selector_all(RESULT_SELECTOR)
                print(f"[web_search] {len(items)} result items found in rendered DOM")
                seen = set()
                raw_hrefs_for_debug = []
                for item in items:
                    link = item.query_selector("h2 a") or item.query_selector("a")
                    if not link:
                        continue
                    raw_href = link.get_attribute("href") or ""
                    href = _resolve_bing_redirect(raw_href)
                    title = (link.inner_text() or "").strip()
                    if len(raw_hrefs_for_debug) < 5:
                        raw_hrefs_for_debug.append((raw_href, href, title))
                    if not href.startswith("http") or any(d in href for d in JUNK_DOMAINS) or not title or href in seen:
                        continue
                    seen.add(href)
                    snippet_el = item.query_selector(".b_caption p, p")
                    snippet = (snippet_el.inner_text().strip() if snippet_el else "")
                    mentions.append(WebMention(title=title, url=href, snippet=snippet))
                    if len(mentions) >= max_results:
                        break
                if not mentions and raw_hrefs_for_debug:
                    print(f"[web_search] first 5 (raw_href, resolved_href, title): {raw_hrefs_for_debug}")
            finally:
                browser.close()
    except Exception as exc:
        print(f"[web_search] failed: {exc}")

    if not mentions:
        print("[web_search] no mentions found this run")

    return mentions
