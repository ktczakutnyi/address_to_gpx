"""
PetSmart Store Scraper
----------------------
Crawls petsmart.com/stores/us/<state> pages to collect store addresses
for the states your husband covers, then geocodes them and writes a GPX file.

Target states: Ohio, Michigan, Pennsylvania, Indiana, Illinois (Chicago)

Usage:
    pip install requests beautifulsoup4 geopy
    python scrape_petsmart.py

Outputs:
    addresses.txt        — one address per line (raw, for re-use)
    petsmart_stores.gpx  — load into any GPS / navigation app
"""

import time
import re
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TARGET_STATES = {
    "oh": "Ohio",
    "mi": "Michigan",
    "pa": "Pennsylvania",
    "in": "Indiana",
    "ky": "Kentucky",
    "il": "Illinois",   # covers Chicago
}

BASE_URL   = "https://www.petsmart.com/stores/us"
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
SCRAPE_DELAY   = 1.5   # seconds between page fetches (be polite)
GEOCODE_DELAY  = 1.1   # Nominatim requires max 1 req/sec

# ---------------------------------------------------------------------------
# Step 1 — Scraping
# ---------------------------------------------------------------------------

def fetch(url: str) -> BeautifulSoup | None:
    """GET a page and return a BeautifulSoup object, or None on failure."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [FETCH ERROR] {url} — {e}")
        return None


def get_city_urls(state_code: str) -> list[str]:
    """
    Fetch /stores/us/<state> and return every city URL found in the list.
    e.g. https://www.petsmart.com/stores/us/mi/ann-arbor
    """
    url = f"{BASE_URL}/{state_code}"
    print(f"\nFetching city list: {url}")
    soup = fetch(url)
    if not soup:
        return []

    city_urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # City links follow pattern /stores/us/<st>/<city-slug>
        if re.match(rf"^/stores/us/{state_code}/[^/]+$", href):
            city_urls.append("https://www.petsmart.com" + href)

    print(f"  Found {len(city_urls)} cities")
    return city_urls


def parse_stores_from_city_page(url: str) -> list[str]:
    """
    Fetch a city page and extract all store addresses.
    Returns a list of formatted address strings.
    """
    time.sleep(SCRAPE_DELAY)
    soup = fetch(url)
    if not soup:
        return []

    addresses = []

    # The page structure groups each store in a section that contains:
    #   - store name heading
    #   - street address paragraph
    #   - city/state/zip paragraph
    # We look for all <p> tags that contain a zip-code pattern to anchor us.
    full_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    # Strategy: find lines that look like "City, ST ZIPCODE" and grab the
    # street line just before them.
    zip_pattern = re.compile(r"^.+,\s+[A-Z]{2}\s+\d{5}(-\d{4})?$")

    for i, line in enumerate(lines):
        if zip_pattern.match(line):
            # The street address is typically 1 line before
            if i >= 1:
                street = lines[i - 1]
                # Sanity check: street should start with a number
                if re.match(r"^\d", street):
                    full_address = f"{street}, {line}"
                    # Remove stray suite noise like "Ste D" already in city line
                    addresses.append(full_address)

    return addresses


def scrape_all_states() -> list[str]:
    """Scrape all target states and return a deduplicated address list."""
    all_addresses: list[str] = []

    for state_code, state_name in TARGET_STATES.items():
        print(f"\n{'='*55}")
        print(f"  STATE: {state_name} ({state_code.upper()})")
        print(f"{'='*55}")

        city_urls = get_city_urls(state_code)
        for city_url in city_urls:
            city_slug = city_url.split("/")[-1]
            print(f"  Scraping: {city_slug}")
            stores = parse_stores_from_city_page(city_url)
            print(f"    → {len(stores)} store(s) found")
            all_addresses.extend(stores)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for addr in all_addresses:
        key = addr.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(addr)

    return unique


# ---------------------------------------------------------------------------
# Step 2 — Geocoding
# ---------------------------------------------------------------------------

def geocode_addresses(addresses: list[str]):
    geolocator = Nominatim(user_agent="petsmart_route_planner_v2")
    successful: list[tuple[str, float, float]] = []
    failed:     list[str] = []
    total = len(addresses)

    for i, address in enumerate(addresses, 1):
        print(f"[{i}/{total}] {address}")
        try:
            loc = geolocator.geocode(address, timeout=10)
            if loc:
                print(f"        ✓  {loc.latitude:.5f}, {loc.longitude:.5f}")
                successful.append((address, loc.latitude, loc.longitude))
            else:
                print("        ✗  No result")
                failed.append(address)
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            print(f"        ✗  {e}")
            failed.append(address)
            time.sleep(3)
            continue
        time.sleep(GEOCODE_DELAY)

    return successful, failed


# ---------------------------------------------------------------------------
# Step 3 — Output
# ---------------------------------------------------------------------------

def save_addresses(addresses: list[str], path: str = "addresses.txt"):
    with open(path, "w", encoding="utf-8") as f:
        for addr in addresses:
            f.write(addr + "\n")
    print(f"\nAddresses saved → {path}  ({len(addresses)} entries)")


def generate_gpx(coords: list[tuple[str, float, float]], path: str = "petsmart_stores.gpx"):
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<gpx version="1.1" creator="PetSmart Route Planner" '
                'xmlns="http://www.topografix.com/GPX/1/1">\n')
        for address, lat, lon in coords:
            safe = address.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            f.write(f'  <wpt lat="{lat}" lon="{lon}">\n')
            f.write(f'    <name>{safe}</name>\n')
            f.write(f'    <desc>{safe}</desc>\n')
            f.write('  </wpt>\n')
        f.write('</gpx>\n')
    print(f"GPX file saved  → {path}  ({len(coords)} waypoints)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # --- Scrape ---
    print("PHASE 1: Scraping PetSmart website...")
    addresses = scrape_all_states()
    print(f"\nTotal unique addresses scraped: {len(addresses)}")
    save_addresses(addresses, "addresses.txt")

    # --- Geocode ---
    print("\nPHASE 2: Geocoding addresses...")
    successful, failed = geocode_addresses(addresses)

    # --- GPX ---
    print("\nPHASE 3: Writing GPX...")
    generate_gpx(successful, "petsmart_stores.gpx")

    # --- Summary ---
    print(f"\n{'='*55}")
    print(f"  Done!  {len(successful)} geocoded,  {len(failed)} failed.")
    if failed:
        print("\n  Failed addresses (consider looking these up manually):")
        for addr in failed:
            print(f"    - {addr}")


if __name__ == "__main__":
    main()
