"""
Store-inventory lookup for Albertsons Companies' Texas banners (Randalls,
Tom Thumb), discovered by inspecting real browser traffic against
www.randalls.com / www.tomthumb.com (see scraper/diagnose_playwright.py).

These sites sit behind Incapsula bot-detection that blocks plain HTTP clients
outright (requests to the product-search endpoint just hang) and even
intermittently blocks a real headless-browser session for no code-visible
reason. So this module:
  - Uses Playwright (real headless Chromium), not `requests`, since that's
    the only thing that gets past Incapsula at all.
  - Retries a few times per banner, since even browser sessions sometimes
    time out.
  - Checks only each banner's single default/nearest store rather than
    sweeping all of Texas -- multiplying flaky browser page-loads across
    ~40 search points was not a reasonable trade for statewide coverage
    that may not be reliably retrievable at all.

The product-search response's JSON shape has never been directly observed
(it didn't fire during response-capture diagnostics), so parsing here is
defensive: it searches the payload for the UPC and a plausible availability
field rather than assuming exact key names, and dumps the full raw response
to debug/ whenever that search comes up empty.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

import requests
from playwright.sync_api import sync_playwright

from . import config

_ADDR_HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept": "application/json",
    "ocp-apim-subscription-key": config.ALBERTSONS_SUBSCRIPTION_KEY,
}


def _lookup_store_address(host: str, store_id: str) -> dict:
    try:
        resp = requests.get(
            f"https://{host}/abs/pub/xapi/storeresolver/storeaddress",
            headers=_ADDR_HEADERS,
            params={"storeid": store_id},
            timeout=15,
            proxies=config.requests_proxies(),
        )
        if resp.status_code != 200:
            return {}
        addr = resp.json().get("storeAddressModel", {}).get("address", {})
        return {
            "name": resp.json().get("storeAddressModel", {}).get("storeRewards", {}).get("storeName", ""),
            "address": addr.get("line1", ""),
            "city": addr.get("city", ""),
            "state": addr.get("state", "TX"),
            "zip": addr.get("zipcode", ""),
        }
    except (requests.RequestException, ValueError):
        return {}


@dataclass
class StockResult:
    retailer: str
    store_id: Optional[str]
    name: str
    address: str
    city: str
    state: str
    zip: str
    status: str  # IN_STOCK | LIMITED_STOCK | OUT_OF_STOCK | UNKNOWN
    quantity: Optional[int] = None


AVAILABILITY_KEY_PATTERN = re.compile(r"(availab|stock|inventory|onhand|quantity)", re.IGNORECASE)
UPC_KEY_PATTERN = re.compile(r"(upc|gtin)", re.IGNORECASE)


def _find_product_entry(node: Any, upc: str) -> Optional[dict]:
    """Walk the response JSON looking for a dict whose upc/gtin-ish field matches."""
    if isinstance(node, dict):
        for key, value in node.items():
            if UPC_KEY_PATTERN.search(key) and isinstance(value, (str, int)) and str(value).lstrip("0") == upc.lstrip("0"):
                return node
        for value in node.values():
            found = _find_product_entry(value, upc)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_product_entry(item, upc)
            if found is not None:
                return found
    return None


def _guess_status(product_entry: dict) -> tuple[str, Optional[int]]:
    for key, value in product_entry.items():
        if AVAILABILITY_KEY_PATTERN.search(key):
            text = str(value).upper()
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                qty = int(value)
                return ("IN_STOCK" if qty > 0 else "OUT_OF_STOCK"), qty
            if "OUT" in text or text in ("FALSE", "NO", "UNAVAILABLE"):
                return "OUT_OF_STOCK", None
            if "LIMIT" in text or "LOW" in text:
                return "LIMITED_STOCK", None
            if "IN_STOCK" in text or "AVAILABLE" in text or text in ("TRUE", "YES"):
                return "IN_STOCK", None
    return "UNKNOWN", None


def debug_dump(label: str, body: str) -> None:
    os.makedirs("debug", exist_ok=True)
    path = os.path.join("debug", f"{label}.json")
    with open(path, "w") as f:
        f.write(body)
    print(f"[albertsons] dumped raw response to {path}")


def check_banner(banner: str, host: str) -> StockResult:
    url = f"https://{host}/shop/search-results.html?q={config.UPC}"
    last_error = None

    for attempt in range(1, config.ALBERTSONS_MAX_ATTEMPTS + 1):
        print(f"[albertsons:{banner}] attempt {attempt}/{config.ALBERTSONS_MAX_ATTEMPTS}")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, proxy=config.playwright_proxy())
                context = browser.new_context(user_agent=config.USER_AGENT)
                page = context.new_page()
                try:
                    with page.expect_response(lambda r: "pgmsearch" in r.url, timeout=25000) as resp_info:
                        page.goto(url, timeout=30000)
                    response = resp_info.value
                    body = response.text()
                finally:
                    browser.close()

            store_id_match = re.search(r"storeid=(\d+)", response.url)
            store_id = store_id_match.group(1) if store_id_match else None
            addr = _lookup_store_address(host, store_id) if store_id else {}
            name = addr.get("name") or banner
            address, city, state, zip_ = addr.get("address", ""), addr.get("city", ""), addr.get("state", "TX"), addr.get("zip", "")

            try:
                data = json.loads(body)
            except ValueError:
                print(f"[albertsons:{banner}] response was not JSON")
                debug_dump(f"{banner.lower().replace(' ', '_')}_pgmsearch_nonjson", body)
                return StockResult(banner, store_id, name, address, city, state, zip_, "UNKNOWN")

            product_entry = _find_product_entry(data, config.UPC)
            if product_entry is None:
                print(f"[albertsons:{banner}] UPC not found in response")
                debug_dump(f"{banner.lower().replace(' ', '_')}_pgmsearch_no_upc_match", body)
                return StockResult(banner, store_id, name, address, city, state, zip_, "UNKNOWN")

            status, quantity = _guess_status(product_entry)
            if status == "UNKNOWN":
                debug_dump(f"{banner.lower().replace(' ', '_')}_pgmsearch_unrecognized_status", json.dumps(product_entry, indent=2))

            return StockResult(banner, store_id, name, address, city, state, zip_, status, quantity)

        except Exception as exc:  # Playwright timeouts, navigation errors, etc.
            last_error = exc
            print(f"[albertsons:{banner}] attempt {attempt} failed: {exc}")

    print(f"[albertsons:{banner}] all {config.ALBERTSONS_MAX_ATTEMPTS} attempts failed: {last_error}")
    return StockResult(banner, None, banner, "", "", "TX", "", "UNKNOWN")


def run() -> list[StockResult]:
    results = []
    for banner, host in config.ALBERTSONS_BANNERS:
        results.append(check_banner(banner, host))
    return results
