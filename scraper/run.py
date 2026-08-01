"""
Scrape Target's Texas stores for Topo Chico stock and write docs/data.json,
which the static site at docs/index.html reads.

Usage: python -m scraper.run
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from . import config, target_scraper as target


def run() -> dict:
    product = target.find_product_by_upc(config.UPC)
    if not product:
        raise SystemExit(f"Could not resolve UPC {config.UPC} to a Target product (TCIN).")

    print(f"[run] found product: {product.title} (tcin={product.tcin})")

    stores_by_id: dict[str, target.Store] = {}
    for city, zip_code in config.TEXAS_SEARCH_POINTS:
        found = target.nearby_stores(zip_code)
        print(f"[run] {city} ({zip_code}): {len(found)} stores within {config.SEARCH_RADIUS_MILES}mi")
        for store in found:
            if store.state == "TX" or store.state == "":
                stores_by_id.setdefault(store.store_id, store)
        time.sleep(config.REQUEST_DELAY_SECONDS)

    stores = list(stores_by_id.values())
    print(f"[run] {len(stores)} unique Texas stores to check")

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

    rows.sort(key=lambda r: (r["city"], r["name"]))

    output = {
        "upc": config.UPC,
        "product_title": product.title,
        "product_image_url": product.image_url,
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
