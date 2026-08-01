"""
General web search for the UPC, independent of any specific retailer's store
locator -- catches whatever grocery/retail/wholesale pages are indexed as
carrying this product anywhere, not just a fixed list of Texas chains.

Uses DuckDuckGo's keyless HTML endpoint (html.duckduckgo.com/html/), which
returns plain server-rendered result markup with no JS and no API key
required -- a common, low-friction way to do this without needing a paid
search API. Run at a modest rate (once a day), this is a single request, not
a crawl.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from . import config

SEARCH_URL = "https://html.duckduckgo.com/html/"


@dataclass
class WebMention:
    title: str
    url: str
    snippet: str


def _resolve_ddg_redirect(href: str) -> str:
    """DDG's HTML endpoint wraps result links in a /l/?uddg=<encoded-url> redirect."""
    if href.startswith("//duckduckgo.com/l/") or "/l/?" in href:
        parsed = urlparse(href if href.startswith("http") else f"https:{href}")
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


def search(query: str = config.WEB_SEARCH_QUERY, max_results: int = config.WEB_SEARCH_MAX_RESULTS) -> list[WebMention]:
    try:
        resp = requests.post(
            SEARCH_URL,
            data={"q": query},
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Content-Type": "application/x-www-form-urlencoded",
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
    for result in soup.select(".result"):
        link = result.select_one(".result__a")
        snippet_el = result.select_one(".result__snippet")
        if not link or not link.get("href"):
            continue
        url = _resolve_ddg_redirect(link["href"])
        title = link.get_text(strip=True)
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        mentions.append(WebMention(title=title, url=url, snippet=snippet))
        if len(mentions) >= max_results:
            break

    if not mentions:
        print("[web_search] no results parsed -- DDG's result markup may have changed")
        print(f"[web_search] body[:1000]: {resp.text[:1000]!r}")

    return mentions
