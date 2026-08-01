"""
Scrape Randalls and Tom Thumb (Albertsons Companies' Texas banners) for Topo
Chico stock across Texas and write docs/data.json, which the static site at
docs/index.html reads.

Usage: python -m scraper.run
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from . import albertsons_scraper as albertsons, config


def run() -> dict:
    rows = []
    product_titles = []

    for banner, host in config.ALBERTSONS_BANNERS:
        product = albertsons.find_product_by_upc(host, config.UPC)
        if not product:
            print(f"[run] {banner}: could not resolve UPC {config.UPC} -- skipping banner")
            continue
        product_titles.append(product.title)
        print(f"[run] {banner}: found product {product.title} (id={product.product_id})")

        stores_by_id: dict[str, albertsons.Store] = {}
        for city, zip_code in config.TEXAS_SEARCH_POINTS:
            found = albertsons.nearby_stores(host, banner, zip_code)
            if found:
                print(f"[run] {banner} near {city} ({zip_code}): {len(found)} stores within {config.SEARCH_RADIUS_MILES}mi")
            for store in found:
                if store.state in ("TX", ""):
                    stores_by_id.setdefault(store.store_id, store)
            time.sleep(config.REQUEST_DELAY_SECONDS)

        stores = list(stores_by_id.values())
        print(f"[run] {banner}: {len(stores)} unique Texas stores to check")

        stock_results = albertsons.fulfillment_for_stores(host, product.product_id, stores)
        for result in stock_results:
            s = result.store
            rows.append(
                {
                    "retailer": banner,
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

    if not rows:
        raise SystemExit(f"Could not find any Randalls/Tom Thumb stock data for UPC {config.UPC}.")

    rows.sort(key=lambda r: (r["retailer"], r["city"], r["name"]))

    output = {
        "upc": config.UPC,
        "product_title": product_titles[0] if product_titles else "Topo Chico Mineral Water",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "stores": rows,
        "summary": {
            "total_stores_checked": len(rows),
            "in_stock": sum(1 for r in rows if r["status"] == "IN_STOCK"),
            "limited_stock": sum(1 for r in rows if r["status"] == "LIMITED_STOCK"),
            "out_of_stock": sum(1 for r in rows if r["status"] in ("OUT_OF_STOCK", "NOT_SOLD_IN_STORE")),
            "unknown": sum(1 for r in rows if r["status"] == "UNKNOWN"),
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
