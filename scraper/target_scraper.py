"""
Target store-inventory lookup via the RedSky API.

RedSky is the public JSON API target.com's own web front end calls (no login,
no API application required) -- widely documented by community projects, but
unofficial and not guaranteed stable. Endpoints or field names may drift; if a
call starts failing, `debug_dump()` writes the raw response so the selectors
here can be patched.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from . import config

BASE = "https://redsky.target.com/redsky_aggregations/v1/web"
API_KEY = os.environ.get("TARGET_API_KEY", config.DEFAULT_TARGET_API_KEY)

session = requests.Session()
session.headers.update(
    {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.target.com",
        "Referer": "https://www.target.com/",
    }
)
if config.RESIDENTIAL_PROXY_URL:
    session.proxies.update(config.requests_proxies())


def _get(path: str, params: dict) -> Optional[dict]:
    params = {**params, "key": API_KEY}
    try:
        resp = session.get(f"{BASE}/{path}", params=params, timeout=20)
    except requests.RequestException as exc:
        print(f"[target] request error on {path}: {exc}")
        return None
    if resp.status_code != 200:
        print(f"[target] {path} -> HTTP {resp.status_code}: {resp.text[:300]!r}")
        return None
    try:
        return resp.json()
    except ValueError:
        print(f"[target] {path} -> non-JSON response")
        return None


@dataclass
class Product:
    tcin: str
    title: str
    image_url: Optional[str] = None


@dataclass
class Store:
    store_id: str
    name: str
    address: str
    city: str
    state: str
    zip: str
    distance_miles: Optional[float] = None


@dataclass
class StockResult:
    store: Store
    status: str  # IN_STOCK | LIMITED_STOCK | OUT_OF_STOCK | NOT_SOLD_IN_STORE | UNKNOWN
    quantity: Optional[int] = None


def find_product_by_upc(upc: str) -> Optional[Product]:
    """Resolve a UPC to Target's internal TCIN via the product search API."""
    data = _get(
        "plp_search_v2",
        {"channel": "WEB", "keyword": upc, "count": 1, "default_purchasability_filter": "false"},
    )
    if not data:
        return None
    try:
        products = data["data"]["search"]["products"]
        if not products:
            print(f"[target] no product found for UPC {upc}")
            return None
        item = products[0]
        tcin = item["item"]["tcin"]
        title = item["item"]["product_description"]["title"]
        images = item["item"].get("enrichment", {}).get("images", {})
        image_url = images.get("primary_image_url")
        return Product(tcin=tcin, title=title, image_url=image_url)
    except (KeyError, IndexError, TypeError) as exc:
        print(f"[target] could not parse product search response: {exc}")
        debug_dump("product_search", data)
        return None


def nearby_stores(zip_code: str, radius_miles: int = config.SEARCH_RADIUS_MILES) -> list[Store]:
    data = _get(
        "nearby_stores_v2",
        {"place": zip_code, "radius": radius_miles, "limit": 20, "within": radius_miles, "unit": "mile"},
    )
    if not data:
        return []
    stores: list[Store] = []
    try:
        locations = data["data"]["nearby_stores"]["locations"]
        for loc in locations:
            addr = loc.get("mailing_address", {})
            stores.append(
                Store(
                    store_id=str(loc["location_id"]),
                    name=loc.get("location_name", ""),
                    address=addr.get("address_line1", ""),
                    city=addr.get("city", ""),
                    state=addr.get("state", ""),
                    zip=addr.get("postal_code", ""),
                    distance_miles=loc.get("distance"),
                )
            )
    except (KeyError, TypeError) as exc:
        print(f"[target] could not parse nearby_stores response for {zip_code}: {exc}")
        debug_dump(f"nearby_stores_{zip_code}", data)
    return stores


def fulfillment_for_stores(tcin: str, stores: list[Store]) -> list[StockResult]:
    """Batched store-pickup availability lookup, chunked to keep query strings short."""
    results: list[StockResult] = []
    chunk_size = 15
    by_id = {s.store_id: s for s in stores}
    ids = list(by_id.keys())
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        data = _get(
            "fulfillment_aggregator_v1",
            {"key": API_KEY, "tcin": tcin, "store_id": ",".join(chunk), "has_store_id": "true"},
        )
        if not data:
            for sid in chunk:
                results.append(StockResult(store=by_id[sid], status="UNKNOWN"))
            continue
        try:
            store_options = (
                data["data"]["product"]["fulfillment"].get("store_options", [])
            )
            seen = set()
            for opt in store_options:
                sid = str(opt.get("location_id"))
                seen.add(sid)
                pickup = opt.get("order_pickup", {})
                availability = pickup.get("availability_status", "UNKNOWN")
                quantity = opt.get("location_available_to_promise_quantity")
                results.append(
                    StockResult(store=by_id.get(sid, by_id[sid]), status=availability, quantity=quantity)
                )
            for sid in chunk:
                if sid not in seen:
                    results.append(StockResult(store=by_id[sid], status="UNKNOWN"))
        except (KeyError, TypeError) as exc:
            print(f"[target] could not parse fulfillment response for chunk {chunk}: {exc}")
            debug_dump(f"fulfillment_{chunk[0]}", data)
            for sid in chunk:
                results.append(StockResult(store=by_id[sid], status="UNKNOWN"))
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return results


def debug_dump(label: str, data: dict) -> None:
    os.makedirs("debug", exist_ok=True)
    path = os.path.join("debug", f"{label}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[target] dumped raw response to {path}")
