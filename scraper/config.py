"""Static configuration: the product we're hunting and the Texas search grid."""

UPC = "021136050462"  # Topo Chico Mineral Water, 12-digit UPC

# Albertsons Companies' Texas banners. Albertsons and Safeway don't operate
# stores in Texas -- Randalls (Houston/Austin/San Antonio) and Tom Thumb
# (Dallas-Fort Worth) are the company's Texas footprint, both running on the
# same underlying digital platform as the rest of the Albertsons family.
ALBERTSONS_BANNERS = [
    ("Randalls", "www.randalls.com"),
    ("Tom Thumb", "www.tomthumb.com"),
]

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
