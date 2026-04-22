PetSmart Route Planner
Scrapes PetSmart store addresses for your target states, geocodes them,
and outputs a GPX file your husband can load into any GPS / navigation app.
---
Project structure
```
combine/
├── scrape_petsmart.py   ← THE script — run this
├── addresses.txt        ← auto-generated after first run
├── petsmart_stores.gpx  ← auto-generated after first run
└── README.md
```
The old `multi/` folder (format_addresses.py + getaddress.py + addresses.txt)
has been merged into this single script. You no longer need those files.
---
Setup (one time)
```bash
pip install requests beautifulsoup4 geopy
```
---
Run it
```bash
python scrape_petsmart.py
```
What it does — in order:
Scrapes petsmart.com for all store addresses in:
Ohio, Michigan, Pennsylvania, Indiana, Illinois (Chicago)
Saves raw addresses to `addresses.txt`
Geocodes each address using OpenStreetMap (Nominatim) — free, no API key needed
Writes `petsmart_stores.gpx` with every store as a waypoint
> ⏱ Runtime: ~10–20 min depending on address count (geocoder is rate-limited to
> 1 request/second per OpenStreetMap's terms of service — don't remove the delay).
---
Loading the GPX into navigation apps
App	How to load GPX
Google Maps	Import via My Maps (maps.google.com → My Maps → Import)
Waze	Not natively supported — use OsmAnd instead
OsmAnd (Android/iOS)	Menu → My places → Tracks → Import
Garmin GPS	Copy file to `Garmin/GPX/` on the device
Apple Maps	Not natively supported — use OsmAnd or Gaia GPS
---
Updating addresses
Just re-run the script. It re-scrapes the live PetSmart site each time,
so any new or closed stores will be reflected automatically.
If a few addresses fail to geocode (usually suite/unit number confusion),
check `addresses.txt` — you can manually fix the address and re-run
just the geocoder portion by editing the `main()` function to skip Phase 1.
---
Target states / adding more
Edit `TARGET_STATES` near the top of `scrape_petsmart.py`:
```python
TARGET_STATES = {
    "oh": "Ohio",
    "mi": "Michigan",
    "pa": "Pennsylvania",
    "in": "Indiana",
    "il": "Illinois",
    # Add more:
    # "ky": "Kentucky",
    # "wv": "West Virginia",
}
```
State codes match the URL slugs on petsmart.com/stores/us/<state>.