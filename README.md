# Topo Chico Hunter

Finds Topo Chico Mineral Water (UPC `021136050462`) in stock, across three
independent sources, and publishes the results as a small dashboard site.

**Live site:** GitHub Pages is enabled (source: GitHub Actions) at
`https://poseyatx.github.io/Topo_Chico_Hunter/`

## Sources

| Source | Coverage | How |
|---|---|---|
| **Target** | Statewide Texas (~40 search points, deduplicated) | Target's public RedSky product/fulfillment API. |
| **Randalls / Tom Thumb** (Albertsons Companies' TX banners) | Each banner's single default/nearest store, best-effort | Real headless Chromium (Playwright) driving the actual site, since the API is Incapsula-protected. |
| **General web search** | Anywhere, not Texas-specific | A keyless DuckDuckGo HTML search for the UPC, catching whatever grocery/retail/wholesale pages are indexed as carrying it. |

`docs/index.html` renders whatever `docs/data.json` currently holds: a
filterable/sortable store table plus a "Web Mentions" list. No build step —
GitHub Pages serves it directly. `.github/workflows/scrape.yml` re-runs all
three sources daily (and on demand via "Run workflow") and commits the
refreshed `docs/data.json`. Each source is wrapped independently, so one
failing doesn't block the others or fail the run.

## Known limitations

**Target** publishes a clean, well-documented API -- but Akamai bot-detection
CAPTCHAs requests from datacenter IPs (confirmed by running this from a
GitHub Actions runner: it reached Target's real server and got
`captchaRelativeURL` back, not a parsing error). It should work fine from an
ordinary home connection; on GitHub's shared runners, expect it to
contribute nothing most days. There's no legitimate fix for that from a
datacenter IP -- solving/routing around a CAPTCHA is bot-evasion, not
something this project does.

**Randalls/Tom Thumb** have no documented public API. `scraper/albertsons_scraper.py`
was built by reverse-engineering real browser traffic (see
`scraper/diagnose_playwright.py`): the actual product-search endpoint
(`/abs/pub/xapi/pgmsearch/v1/search/products`) and the subscription-key
header it requires were extracted from the page's own embedded config. But
these sites sit behind Incapsula bot-detection that intermittently blocks
even a real headless-browser session for no code-visible reason -- across
diagnostic runs it succeeded roughly half the time. So:
- Only each banner's single default/nearest store is checked, not a
  statewide sweep -- multiplying flaky page-loads across many search points
  wasn't worth it for coverage that may not be retrievable at all.
- Up to 3 retries per banner per run; a run can still legitimately come back
  with `UNKNOWN` for one or both banners.
- The product-search response's JSON shape was never directly observed
  (it didn't fire during response-capture diagnostics), so parsing is
  defensive -- it searches the payload for the UPC and a plausible
  availability field rather than assuming exact key names. If this needs
  correcting, `debug/*.json` (uploaded as a build artifact on failure, or
  written locally) has the raw response.

**General web search** is the most reliable of the three (no bot-walls, no
store-level precision) but only as good as what's indexed -- it surfaces
retailer/wholesale pages that mention the UPC, not confirmed live stock.

**Not included:** H-E-B (Texas's dominant grocery chain for Topo Chico) and
Walmart have no public inventory API; scraping their live stock pages would
mean reverse-engineering an internal ordering session, which is fragile and
against their terms. Kroger has an official
[Developer API](https://developer.kroger.com/) but essentially no store
footprint left in Texas.

## Running it yourself

```bash
pip install -r requirements.txt
playwright install --with-deps chromium   # needed for Randalls/Tom Thumb
python -m scraper.run
```

Writes `docs/data.json`. Open `docs/index.html` in a browser (or serve the
`docs/` folder) to view it locally.

## Dev tools

- `python -m scraper.diagnose` -- scans Randalls/Tom Thumb pages for embedded
  API references (no browser needed).
- `python -m scraper.diagnose_playwright` -- loads those pages in real
  headless Chromium and captures the actual pgmsearch/storeresolver network
  traffic, including response bodies. Both are wired up as manual-only jobs
  in `.github/workflows/diagnose.yml` since this sandbox has no route to
  these sites to test locally.

## Notes on scope and etiquette

Each source runs once a day at a modest rate: ~40 location lookups against
Target's API, one page-load (with retries) per Albertsons banner, and a
single web search query. Not a high-volume or disruptive crawl.
