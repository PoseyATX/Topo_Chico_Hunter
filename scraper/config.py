"""Static configuration: the product we're hunting and the Texas search grid."""

import os
from urllib.parse import urlparse

UPC = "021136050462"  # Topo Chico Mineral Water, 12-digit UPC

# Optional residential proxy (format: http://user:pass@host:port), set as the
# RESIDENTIAL_PROXY_URL repo secret. Every source in this project is blocked
# or degraded specifically because GitHub's runners come from recognizable
# datacenter IP ranges -- Target's Akamai CAPTCHA, Randalls/Tom Thumb's
# Incapsula flakiness, and Bing serving decoy content are all downstream of
# that one fact. A residential/mobile proxy routes these requests through an
# ordinary consumer IP instead, which is the actual fix, not a workaround --
# it changes which network the traffic looks like it's coming from, the same
# thing switching to home wifi would do, it just doesn't require owning or
# running any hardware. See README's "Zero-hardware fix" section. Unset (the
# default) leaves every scraper behaving exactly as before.
RESIDENTIAL_PROXY_URL = os.environ.get("RESIDENTIAL_PROXY_URL") or None


def playwright_proxy() -> dict | None:
    """RESIDENTIAL_PROXY_URL translated into Playwright's proxy dict shape."""
    if not RESIDENTIAL_PROXY_URL:
        return None
    parsed = urlparse(RESIDENTIAL_PROXY_URL)
    proxy = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        proxy["username"] = parsed.username
    if parsed.password:
        proxy["password"] = parsed.password
    return proxy


def requests_proxies() -> dict | None:
    """RESIDENTIAL_PROXY_URL translated into `requests`' proxies dict shape."""
    if not RESIDENTIAL_PROXY_URL:
        return None
    return {"http": RESIDENTIAL_PROXY_URL, "https": RESIDENTIAL_PROXY_URL}

# Target's public frontend API key (same one target.com's own site JS uses to
# call RedSky -- not a secret, but Target rotates it occasionally). Override
# with the TARGET_API_KEY env var if this one stops working.
DEFAULT_TARGET_API_KEY = "9f36aeafbe60771e321a7cc95a78140772ab3e96"

# Albertsons Companies' Texas banners. Albertsons and Safeway don't operate
# stores in Texas -- Randalls (Houston/Austin/San Antonio) and Tom Thumb
# (Dallas-Fort Worth) are the company's Texas footprint, both running on the
# same underlying digital platform as the rest of the Albertsons family.
ALBERTSONS_BANNERS = [
    ("Randalls", "www.randalls.com"),
    ("Tom Thumb", "www.tomthumb.com"),
]

# The "xapiSubscriptionKey" embedded in each banner's own page config --
# required as the ocp-apim-subscription-key header on /abs/pub/xapi/* calls.
# Not a secret; it's shipped to every visitor's browser.
ALBERTSONS_SUBSCRIPTION_KEY = "7bad9afbb87043b28519c4443106db06"

# Best-effort retries for the Albertsons product-search call, which sits
# behind Incapsula bot-detection that intermittently blocks even a real
# headless browser (see README's "Known limitations").
ALBERTSONS_MAX_ATTEMPTS = 3

# General web search for the UPC, independent of any specific retailer's
# store locator -- catches whatever grocery/retail sites are indexed as
# carrying this product, anywhere, not just Texas.
WEB_SEARCH_QUERY = f'"{UPC}" Topo Chico'
WEB_SEARCH_MAX_RESULTS = 15

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Search-origin cities spread across Texas so a ~50-mile store-radius search
# from each point covers the state, including the Panhandle, West Texas, the
# Rio Grande Valley, and East Texas. Deep rural gaps between these may simply
# have no Target within range -- that's a real absence, not a scraper miss.
TEXAS_SEARCH_POINTS = [
    ("Houston", "77002"),
    ("San Antonio", "78205"),
    ("Dallas", "75201"),
    ("Austin", "78701"),
    ("Fort Worth", "76102"),
    ("El Paso", "79901"),
    ("Corpus Christi", "78401"),
    ("Plano", "75023"),
    ("Laredo", "78040"),
    ("Lubbock", "79401"),
    ("Amarillo", "79101"),
    ("Brownsville", "78520"),
    ("McKinney", "75069"),
    ("Killeen", "76541"),
    ("McAllen", "78501"),
    ("Midland", "79701"),
    ("Denton", "76201"),
    ("Waco", "76701"),
    ("Round Rock", "78664"),
    ("Abilene", "79601"),
    ("Pearland", "77581"),
    ("Odessa", "79761"),
    ("Beaumont", "77701"),
    ("Wichita Falls", "76301"),
    ("Tyler", "75701"),
    ("College Station", "77840"),
    ("San Angelo", "76901"),
    ("Longview", "75601"),
    ("Texarkana", "75501"),
    ("Victoria", "77901"),
    ("Harlingen", "78550"),
    ("Del Rio", "78840"),
    ("Eagle Pass", "78852"),
    ("Nacogdoches", "75961"),
    ("Sherman", "75090"),
    ("Huntsville", "77340"),
    ("Kerrville", "78028"),
    ("Alpine", "79830"),
    ("Pampa", "79065"),
    ("Uvalde", "78801"),
]

SEARCH_RADIUS_MILES = 50
REQUEST_DELAY_SECONDS = 0.4
