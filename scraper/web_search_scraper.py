"""
General web search for the UPC, independent of any specific retailer's store
locator -- catches whatever grocery/retail/wholesale pages are indexed as
carrying this product anywhere, not just a fixed list of Texas chains.

Tries DuckDuckGo's "Lite" endpoint first, falling back to Bing's plain HTML
results page. Confirmed via real runs: DuckDuckGo now serves the *same*
JS-bootstrap anti-bot shell to both html.duckduckgo.com/html/ and
lite.duckduckgo.com/lite/ for this kind of request -- there's no simple
no-JS DDG endpoint left to scrape. Bing's basic HTML search
(`b_algo` result markup) has historically been more tolerant of this. Run at
a modest rate (once a day), this is one or two requests, not a crawl.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from . import config


@dataclass
class WebMention:
    title: str
    url: str
    snippet: str


def _get(url: str, params: dict) -> str:
    try:
        resp = requests.get(
            url,
            params=params,
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        print(f"[web_search] {url} request error: {exc}")
        return ""
    if resp.status_code >= 400 or not resp.text:
        print(f"[web_search] {url} -> HTTP {resp.status_code}, empty or error body")
        return ""
    return resp.text


def _resolve_ddg_redirect(href: str) -> str:
    """DDG sometimes wraps result links in a /l/?uddg=<encoded-url> redirect."""
    if "/l/?" in href:
        parsed = urlparse(href if href.startswith("http") else f"https:{href}")
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


def _search_ddg_lite(query: str, max_results: int) -> list[WebMention]:
    body = _get("https://lite.duckduckgo.com/lite/", {"q": query})
    if not body:
        return []

    soup = BeautifulSoup(body, "html.parser")
    mentions: list[WebMention] = []
    links = soup.select("a.result-link") or [
        a for a in soup.find_all("a", href=True)
        if (a["href"].startswith("http") or "/l/?" in a["href"])
        and "duckduckgo.com" not in _resolve_ddg_redirect(a["href"])
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
        print("[web_search] DDG lite: no results parsed")
        print(f"[web_search] DDG lite body length: {len(body)}")
        print(f"[web_search] DDG lite body[:800]: {body[:800]!r}")

    return mentions


BING_JUNK_DOMAINS = (
    "bing.com", "microsoft.com", "microsofttranslator.com", "msn.com", "live.com",
)


def _resolve_bing_redirect(href: str) -> str:
    """Bing wraps organic result links in bing.com/ck/a?...&u=a1<base64url>."""
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


def _search_bing(query: str, max_results: int) -> list[WebMention]:
    body = _get("https://www.bing.com/search", {"q": query, "count": max_results})
    if not body:
        return []

    soup = BeautifulSoup(body, "html.parser")

    # Prefer the known results-list container (#b_results) if present, since
    # that scopes out the sidebar/related-searches/ad clutter; fall back to
    # the whole page if Bing's markup has dropped that id.
    container = soup.select_one("#b_results") or soup

    mentions: list[WebMention] = []
    seen_urls = set()
    for li in container.find_all("li", recursive=True) or [container]:
        link = li.find("a", href=True)
        if not link:
            continue
        href = _resolve_bing_redirect(link["href"])
        if not href.startswith("http") or any(d in href for d in BING_JUNK_DOMAINS):
            continue
        title = link.get_text(strip=True)
        if not title or href in seen_urls:
            continue
        seen_urls.add(href)
        # The caption/snippet is usually the first substantial <p> or <div>
        # text within the same <li>, after the title link itself.
        snippet = ""
        for el in li.find_all(["p", "div"]):
            text = el.get_text(strip=True)
            if len(text) > 20 and text != title:
                snippet = text
                break
        mentions.append(WebMention(title=title, url=href, snippet=snippet))
        if len(mentions) >= max_results:
            break

    if not mentions:
        print("[web_search] Bing: no results parsed")
        print(f"[web_search] Bing body length: {len(body)}, #b_results present: {soup.select_one('#b_results') is not None}")
        all_hrefs = [a["href"] for a in container.find_all("a", href=True)][:20]
        print(f"[web_search] Bing first 20 hrefs in container: {all_hrefs}")

    return mentions


def search(query: str = config.WEB_SEARCH_QUERY, max_results: int = config.WEB_SEARCH_MAX_RESULTS) -> list[WebMention]:
    mentions = _search_ddg_lite(query, max_results)
    if mentions:
        return mentions
    print("[web_search] DDG lite returned nothing, trying Bing")
    return _search_bing(query, max_results)
