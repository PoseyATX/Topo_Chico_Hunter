"""
Store-inventory lookup for Albertsons Companies' Texas banners (Randalls,
Tom Thumb), both of which run on the same underlying digital storefront
platform as the rest of the Albertsons family (Safeway, Vons, Jewel-Osco, ...).

Unlike Target's RedSky API, there's no widely-documented public API for this
platform to build against -- these are first-pass, best-guess endpoints based
on how comparable grocery storefronts structure store-locator and product
search/availability calls. `debug_dump()` writes the raw response (status,
headers, body) for every non-2xx or unparseable call so real traffic can be
used to correct the endpoint shapes here.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests

from . import config

session = requests.Session()
session.headers.update(
    {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
)


@dataclass
class Product:
    product_id: str
    title: str


@dataclass
class Store:
    store_id: str
    banner: str
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


def _request(method: str, host: str, path: str, **kwargs) -> Optional[requests.Response]:
    url = f"https://{host}{path}"
    try:
        resp = session.request(method, url, timeout=20, **kwargs)
    except requests.RequestException as exc:
        print(f"[albertsons:{host}] {method} {path} -> request error: {exc}")
        return None
    if resp.status_code >= 400:
        print(
            f"[albertsons:{host}] {method} {path} -> HTTP {resp.status_code} "
            f"({resp.headers.get('content-type', '?')}): {resp.text[:300]!r}"
        )
        debug_dump(f"{host.replace('.', '_')}_{path.strip('/').replace('/', '_')}", resp)
        return None
    return resp


def find_product_by_upc(host: str, upc: str) -> Optional[Product]:
    """Resolve a UPC to this banner's internal product ID via product search."""
    resp = _request(
        "GET",
        host,
        "/abs/pub/xapi/search/v3/products",
        params={"q": upc, "rows": 1},
    )
    if not resp:
        return None
    try:
        data = resp.json()
        products = data.get("products") or data.get("data", {}).get("products") or []
        if not products:
            print(f"[albertsons:{host}] no product found for UPC {upc}")
            return None
        item = products[0]
        product_id = str(item.get("productId") or item.get("id") or item.get("upc"))
        title = item.get("name") or item.get("productName") or upc
        return Product(product_id=product_id, title=title)
    except (ValueError, KeyError, TypeError) as exc:
        print(f"[albertsons:{host}] could not parse product search response: {exc}")
        debug_dump(f"{host.replace('.', '_')}_product_search_parse", resp)
        return None


def nearby_stores(host: str, banner: str, zip_code: str, radius_miles: int = config.SEARCH_RADIUS_MILES) -> list[Store]:
    resp = _request(
        "GET",
        host,
        "/abs/pub/xapi/storelocator/v1/stores",
        params={"zipcode": zip_code, "radius": radius_miles, "limit": 20},
    )
    if not resp:
        return []
    stores: list[Store] = []
    try:
        data = resp.json()
        locations = data.get("stores") or data.get("data", {}).get("stores") or []
        for loc in locations:
            addr = loc.get("address", {})
            stores.append(
                Store(
                    store_id=str(loc.get("storeId") or loc.get("id")),
                    banner=banner,
                    name=loc.get("name", banner),
                    address=addr.get("addressLine1", addr.get("street", "")),
                    city=addr.get("city", ""),
                    state=addr.get("state", ""),
                    zip=addr.get("zipcode", addr.get("zip", "")),
                    distance_miles=loc.get("distance"),
                )
            )
    except (ValueError, KeyError, TypeError) as exc:
        print(f"[albertsons:{host}] could not parse nearby_stores response for {zip_code}: {exc}")
        debug_dump(f"{host.replace('.', '_')}_nearby_stores_{zip_code}_parse", resp)
    return stores


def fulfillment_for_stores(host: str, product_id: str, stores: list[Store]) -> list[StockResult]:
    """Per-store pickup availability. Checked one store at a time -- this
    platform's product API takes store context per-request rather than a
    batched multi-store lookup like Target's."""
    results: list[StockResult] = []
    for store in stores:
        resp = _request(
            "GET",
            host,
            f"/abs/pub/xapi/product/v1/{product_id}/availability",
            params={"storeId": store.store_id},
        )
        if not resp:
            results.append(StockResult(store=store, status="UNKNOWN"))
            time.sleep(config.REQUEST_DELAY_SECONDS)
            continue
        try:
            data = resp.json()
            availability = data.get("availabilityStatus") or data.get("status", "UNKNOWN")
            quantity = data.get("quantity") or data.get("availableQuantity")
            results.append(StockResult(store=store, status=str(availability).upper(), quantity=quantity))
        except (ValueError, KeyError, TypeError) as exc:
            print(f"[albertsons:{host}] could not parse availability for store {store.store_id}: {exc}")
            debug_dump(f"{host.replace('.', '_')}_availability_{store.store_id}_parse", resp)
            results.append(StockResult(store=store, status="UNKNOWN"))
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return results


def debug_dump(label: str, resp: requests.Response) -> None:
    os.makedirs("debug", exist_ok=True)
    path = os.path.join("debug", f"{label}.json")
    payload = {
        "url": resp.url,
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp.text[:5000],
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[albertsons] dumped raw response to {path}")
