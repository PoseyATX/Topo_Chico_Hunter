"""
General web search for the UPC, independent of any specific retailer's store
locator -- catches whatever grocery/retail/wholesale pages are indexed as
carrying this product anywhere, not just a fixed list of Texas chains.

Uses DuckDuckGo's "Lite" endpoint (lite.duckduckgo.com/lite/), a plain
table-based HTML results page with no JavaScript -- built for exactly this
kind of low-bandwidth/scriptable client, unlike html.duckduckgo.com/html/,
which (confirmed via a real run) serves a JS-bootstrap shell instead of
server-rendered results to this kind of request. Run at a modest rate (once
a day), this is a single request, not a crawl.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from . import config

SEARCH_URL = "https://lite.duckduckgo.com/lite/"


@dataclass
class WebMention:
    title: str
    url: str
    snippet: str


def _resolve_ddg_redirect(href: str) -> str:
    """DDG sometimes wraps result links in a /l/?uddg=<encoded-url> redirect."""
    if "/l/?" in href:
        parsed = urlparse(href if href.startswith("http") else f"https:{href}")
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


def search(query: str = config.WEB_SEARCH_QUERY, max_results: int = config.WEB_SEARCH_MAX_RESULTS) -> list[WebMention]:
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"q": query},
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        print(f"[web_search] request error: {exc}")
        return []

    if resp.status_code >= 400 or not resp.text:
        print(f"[web_search] HTTP {resp.status_code}, empty or error body")
        return []
    if resp.status_code != 200:
        print(f"[web_search] HTTP {resp.status_code} (non-200 but has a body, trying to parse anyway)")

    soup = BeautifulSoup(resp.text, "html.parser")
    mentions: list[WebMention] = []

    # Lite's markup: each result is a <tr> with a link (class result-link,
    # older markup) followed by a snippet <tr> (class result-snippet).
    # Fall back to any <a> whose href looks like an external result link, in
    # case the exact class names have drifted.
    links = soup.select("a.result-link") or [
        a for a in soup.find_all("a", href=True)
        if a["href"].startswith("http") or "/l/?" in a["href"]
        if "duckduckgo.com" not in _resolve_ddg_redirect(a["href"])
    ]

    for link in links:
        href = link.get("href", "")
        if not href:
            continue
        url = _resolve_ddg_redirect(href)
        title = link.get_text(strip=True)
        if not title or not url.startswith("http"):
            continue
        snippet = ""
        snippet_row = link.find_parent("tr")
        if snippet_row:
            next_row = snippet_row.find_next_sibling("tr")
            if next_row:
                snippet_cell = next_row.select_one(".result-snippet") or next_row
                snippet = snippet_cell.get_text(strip=True)
        mentions.append(WebMention(title=title, url=url, snippet=snippet))
        if len(mentions) >= max_results:
            break

    if not mentions:
        print("[web_search] no results parsed -- DDG's result markup may have changed")
        print(f"[web_search] body length: {len(resp.text)}")
        print(f"[web_search] body[:1500]: {resp.text[:1500]!r}")

    return mentions
