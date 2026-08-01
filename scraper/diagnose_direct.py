"""
One-off reconnaissance tool #3: hits the real pgmsearch (product search) and
storeresolver (store locator) endpoints directly with plain `requests`, using
the ocp-apim-subscription-key header discovered via the browser diagnostic,
to see the actual JSON response shapes and confirm required parameters.

Usage: python -m scraper.diagnose_direct
"""

from __future__ import annotations

import requests

from . import config

SUBSCRIPTION_KEY = "7bad9afbb87043b28519c4443106db06"  # xapiSubscriptionKey, found in page config
HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept": "application/json",
    "ocp-apim-subscription-key": SUBSCRIPTION_KEY,
}


def try_get(url: str, params: dict, label: str) -> None:
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=20)
    except requests.RequestException as exc:
        print(f"{label}: request error {exc}")
        return
    print(f"\n{label} -> HTTP {resp.status_code}")
    print(f"  url: {resp.url}")
    print(f"  body[:4000]: {resp.text[:4000]}")


def main() -> None:
    host = "www.randalls.com"

    try_get(
        f"https://{host}/abs/pub/xapi/pgmsearch/v1/search/products",
        {
            "request-id": "1",
            "url": f"https://{host}",
            "pageurl": f"https://{host}",
            "pagename": "search",
            "rows": 30,
            "start": 0,
            "search-type": "keyword",
            "storeid": 1066,
            "featured": "true",
            "q": config.UPC,
            "sort": "",
            "timezone": "America/Chicago",
            "dvid": "web-4.1search",
            "channel": "instore",
            "visitorId": "diagnostic-visitor",
            "pgm": "merch-banner",
            "includeOffer": "true",
            "banner": "randalls",
        },
        "pgmsearch (storeid=1066, q=UPC)",
    )

    for params in [
        {"zipcode": "77024"},
        {"address": "77024"},
        {"zipcode": "77024", "radius": 50},
        {"zipcode": "77024", "radius": 50, "banner": "randalls"},
    ]:
        try_get(
            f"https://{host}/abs/pub/xapi/storeresolver/v2/storesByAddress",
            params,
            f"storesByAddress {params}",
        )


if __name__ == "__main__":
    main()
