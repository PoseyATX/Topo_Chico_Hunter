# Topo Chico Hunter

Finds Topo Chico Mineral Water (UPC `021136050462`) in stock at Randalls and
Tom Thumb stores across Texas, and publishes the results as a small dashboard
site. (Randalls and Tom Thumb are Albertsons Companies' Texas banners —
Albertsons and Safeway proper don't operate stores in Texas.)

**Live site:** enable GitHub Pages (see below), then it's at
`https://poseyatx.github.io/Topo_Chico_Hunter/`

## ⚠️ Status: first-pass endpoints, not yet verified against live traffic

Unlike Target (whose RedSky API is extensively documented across the scraper
community), Randalls/Tom Thumb's underlying Albertsons Companies storefront
platform has no widely-known public API reference. `scraper/albertsons_scraper.py`
is a best-guess first pass at the store-locator, product-search, and
per-store-availability endpoints, based on how comparable grocery storefronts
are typically structured — not confirmed against real responses yet.

This repo's sandbox has no general internet access (GitHub and the package
registries only), so the only way to validate these endpoints for real is to
run the GitHub Action on a real runner and read what actually comes back. If
you see this scraper failing, check the **Actions** tab and `debug/*.json`
(uploaded as a build artifact on failure) for the actual status codes and
response bodies — that's the fastest way to correct the endpoint paths/field
names in `albertsons_scraper.py`.

Note the same caveat that applied to Target may apply here too: if Randalls/Tom
Thumb sit behind similar cloud-IP bot detection, GitHub-hosted Actions runners
may get blocked even once the endpoints are right, in which case running
locally from a home connection (or a self-hosted Actions runner) becomes the
practical path — see `.github/workflows/scrape.yml`'s comments.

## How it works

- `scraper/` is a Python scraper that, per banner (Randalls, Tom Thumb):
  1. Resolves the UPC to the banner's internal product ID via its product
     search endpoint.
  2. Searches ~40 points spread across Texas for nearby stores within 50
     miles, and de-duplicates to a single list per banner (Randalls clusters
     around Houston/Austin/San Antonio, Tom Thumb around Dallas-Fort Worth —
     most other search points will simply return zero stores, which is
     correct, not a bug).
  3. Checks pickup availability for the product at every store found.
  4. Writes the combined results to `docs/data.json`.
- `docs/index.html` is a static dashboard that reads `docs/data.json` and lets
  you search/filter (by city, store, status, or retailer) and sort the
  results. No build step — GitHub Pages serves it directly.
- `.github/workflows/scrape.yml` re-runs the scraper daily (and on demand via
  "Run workflow") and commits the refreshed `docs/data.json`.

## Retailer coverage

| Retailer | Included? | Why |
|---|---|---|
| **Randalls / Tom Thumb** (Albertsons Companies) | Yes | The Albertsons family's actual Texas footprint. |
| **Target** | No | Has a public, well-documented inventory API, but Akamai bot-detection CAPTCHAs requests from datacenter IPs (cloud sandboxes, GitHub Actions), making it unreliable to run automatically. |
| **H-E-B** | No | Texas's dominant grocery chain for Topo Chico, but has no public inventory API. Getting per-store stock would mean reverse-engineering their internal ordering session flow, which is fragile and against their terms. |
| **Walmart** | No | Same issue — no public inventory API; only unofficial/reverse-engineered endpoints exist, which break often and risk IP blocks. |
| **Kroger** | No | Kroger *does* publish an official [Developer API](https://developer.kroger.com/), but Kroger has essentially no store footprint left in Texas, so it wouldn't add real coverage. |

If another retailer later exposes a public inventory endpoint,
`scraper/albertsons_scraper.py`'s shape (resolve product → find nearby stores
→ check availability) is the pattern to copy into a new module.

## Running it yourself

```bash
pip install -r requirements.txt
python -m scraper.run
```

Writes `docs/data.json`. Open `docs/index.html` in a browser (or serve the `docs/`
folder) to view it locally.

If parsing breaks, failed responses (URL, status, headers, body) are dumped to
`debug/*.json` for inspection — check there first, and correct the endpoint
paths/field names in `scraper/albertsons_scraper.py` to match.

## Enabling the live site (one-time)

1. Repo **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: **main**, folder: **/docs**
4. Save. The site will be live at `https://poseyatx.github.io/Topo_Chico_Hunter/`
   within a minute or two, and refreshes automatically every day from the scheduled
   Action (once the endpoints above are confirmed working).

## Notes on scope and etiquette

This queries the banners' own storefront APIs at a modest rate (~40 location
lookups + a handful of per-store availability checks, once a day, per banner)
— not a high-volume or disruptive crawl.
