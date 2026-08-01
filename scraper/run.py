"""
Scrape Target (statewide Texas), Randalls/Tom Thumb (Albertsons Companies,
best-effort, default store per banner), and a general web search for Topo
Chico stock/mentions, and write docs/data.json, which the static site at
docs/index.html reads.

Usage: python -m scraper.run
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime, timezone

from . import albertsons_scraper, config, target_scraper as target, web_search_scraper


def run_target() -> list[dict]:
    product = target.find_product_by_upc(config.UPC)
    if not product:
        print(f"[run] Target: could not resolve UPC {config.UPC} -- skipping")
        return []

    print(f"[run] Target: found product {product.title} (tcin={product.tcin})")

    stores_by_id: dict[str, target.Store] = {}
    for city, zip_code in config.TEXAS_SEARCH_POINTS:
        found = target.nearby_stores(zip_code)
        if found:
            print(f"[run] Target near {city} ({zip_code}): {len(found)} stores within {config.SEARCH_RADIUS_MILES}mi")
        for store in found:
            if store.state in ("TX", ""):
                stores_by_id.setdefault(store.store_id, store)
        time.sleep(config.REQUEST_DELAY_SECONDS)

    stores = list(stores_by_id.values())
    print(f"[run] Target: {len(stores)} unique Texas stores to check")

    stock_results = target.fulfillment_for_stores(product.tcin, stores)
    rows = []
    for result in stock_results:
        s = result.store
        rows.append(
            {
                "retailer": "Target",
                "store_id": s.store_id,
                "name": s.name,
                "address": s.address,
                "city": s.city,
                "state": s.state,
                "zip": s.zip,
                "distance_from_search_point": s.distance_miles,
                "status": result.status,
                "quantity": result.quantity,
            }
        )
    return rows


def run_albertsons() -> list[dict]:
    rows = []
    for result in albertsons_scraper.run():
        rows.append(
            {
                "retailer": result.retailer,
                "store_id": result.store_id,
                "name": result.name,
                "address": result.address,
                "city": result.city,
                "state": result.state,
                "zip": result.zip,
                "distance_from_search_point": None,
                "status": result.status,
                "quantity": result.quantity,
            }
        )
    return rows


def run_web_search() -> list[dict]:
    mentions = web_search_scraper.search()
    print(f"[run] web search: {len(mentions)} mentions found")
    return [asdict(m) for m in mentions]


def run() -> dict:
    rows: list[dict] = []

    try:
        rows.extend(run_target())
    except Exception as exc:
        print(f"[run] Target scrape failed entirely: {exc}")

    try:
        rows.extend(run_albertsons())
    except Exception as exc:
        print(f"[run] Albertsons scrape failed entirely: {exc}")

    try:
        web_mentions = run_web_search()
    except Exception as exc:
        print(f"[run] web search failed entirely: {exc}")
        web_mentions = []

    rows.sort(key=lambda r: (r["retailer"], r["city"], r["name"]))

    output = {
        "upc": config.UPC,
        "product_title": "Topo Chico Mineral Water",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "stores": rows,
        "web_mentions": web_mentions,
        "summary": {
            "total_stores_checked": len(rows),
            "in_stock": sum(1 for r in rows if r["status"] == "IN_STOCK"),
            "limited_stock": sum(1 for r in rows if r["status"] == "LIMITED_STOCK"),
            "out_of_stock": sum(1 for r in rows if r["status"] in ("OUT_OF_STOCK", "NOT_SOLD_IN_STORE")),
            "unknown": sum(1 for r in rows if r["status"] == "UNKNOWN"),
            "web_mentions_count": len(web_mentions),
        },
    }
    return output


def main() -> None:
    output = run()
    with open("docs/data.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"[run] wrote docs/data.json ({output['summary']})")


if __name__ == "__main__":
    main()
