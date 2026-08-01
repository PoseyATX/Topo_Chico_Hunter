# Topo Chico Hunter

Finds Topo Chico Mineral Water (UPC `021136050462`) in stock at stores across Texas,
and publishes the results as a small dashboard site.

**Live site:** enable GitHub Pages (see below), then it's at
`https://poseyatx.github.io/Topo_Chico_Hunter/`

## ⚠️ Known limitation: run this from home, not from the cloud

Target's RedSky API sits behind Akamai bot-detection that fingerprints the
*origin* of a request, not just its headers. Requests from GitHub-hosted
Actions runners (and most cloud/sandbox environments) come from well-known
datacenter IP ranges and get served a CAPTCHA challenge instead of data —
confirmed by actually running this scraper from a GitHub Actions runner: it
reached Target's real server (so the endpoints/params here are correct) and
got `captchaRelativeURL` back, not a 404 or malformed-request error.

There's no legitimate fix for that from a datacenter IP — solving or routing
around a CAPTCHA is bot-evasion, not something this project will do. The
practical workaround is running the scraper from an ordinary residential
connection, where Target's own website traffic normally comes from:

- **Run it locally** (see below) from your home network whenever you want
  fresh numbers, then commit + push the updated `docs/data.json`.
- **Or set up a [self-hosted Actions runner](https://docs.github.com/en/actions/hosting-your-own-runners)**
  on a machine at home (even a Raspberry Pi) — point `.github/workflows/scrape.yml`'s
  `runs-on:` at it, and the existing daily schedule + dashboard will update
  themselves automatically from a residential IP.

The scheduled run on GitHub's shared (`ubuntu-latest`) runners is left in place
for convenience if Target ever loosens this, but expect it to fail with the
CAPTCHA error above until you switch to a self-hosted runner.

## How it works

- `scraper/` is a Python scraper that:
  1. Resolves the UPC to Target's internal product ID (TCIN) via Target's public
     RedSky API (the same JSON API target.com's own website calls — no login required).
  2. Searches ~40 points spread across Texas (Panhandle to the Valley, El Paso to
     the Louisiana line) for nearby Target stores within 50 miles, and de-duplicates
     to a single statewide list.
  3. Checks store-pickup availability for the product at every store found.
  4. Writes the results to `docs/data.json`.
- `docs/index.html` is a static dashboard that reads `docs/data.json` and lets you
  search/filter/sort the results. No build step — GitHub Pages serves it directly.
- `.github/workflows/scrape.yml` re-runs the scraper daily (and on demand via
  "Run workflow") and commits the refreshed `docs/data.json`.

## Retailer coverage — and why it stops at Target

| Retailer | Included? | Why |
|---|---|---|
| **Target** | Yes | Publishes a public product/fulfillment API with real per-store stock. |
| **H-E-B** | No | Texas's dominant grocery chain for Topo Chico, but has no public inventory API. Getting per-store stock would mean reverse-engineering their internal ordering session flow, which is fragile and against their terms. |
| **Walmart** | No | Same issue — no public inventory API; only unofficial/reverse-engineered endpoints exist, which break often and risk IP blocks. |
| **Kroger** | No | Kroger *does* publish an official [Developer API](https://developer.kroger.com/), but Kroger has essentially no store footprint left in Texas, so it wouldn't add real coverage. |

If H-E-B or Walmart later expose a public inventory endpoint, `scraper/target_scraper.py`'s
shape (resolve product → find nearby stores → check fulfillment) is the pattern to copy
into a new `heb_scraper.py` / `walmart_scraper.py` module.

## Running it yourself

```bash
pip install -r requirements.txt
python -m scraper.run
```

Writes `docs/data.json`. Open `docs/index.html` in a browser (or serve the `docs/`
folder) to view it locally.

If Target changes their API and parsing breaks, failed responses are dumped to
`debug/*.json` for inspection — check there first.

## Enabling the live site (one-time)

1. Repo **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: **main**, folder: **/docs**
4. Save. The site will be live at `https://poseyatx.github.io/Topo_Chico_Hunter/`
   within a minute or two, and refreshes automatically every day from the scheduled
   Action.

## Notes on scope and etiquette

This queries a public, unauthenticated JSON API the same way target.com's own
website does, at a modest rate (~40 location lookups + a handful of batched
stock checks, once a day) — not a high-volume or disruptive crawl. Target's API
key embedded in `scraper/config.py` is the same one their site's frontend uses
and isn't a secret, but it does rotate occasionally; if lookups start failing,
grab a fresh key from target.com's network requests and set it via the
`TARGET_API_KEY` environment variable.
