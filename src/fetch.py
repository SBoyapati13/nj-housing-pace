"""Fetch new or revised Census Building Permits Survey place files.

Keeps data/raw/bps/ in sync with the Census Northeast-region directory:
  - full-year files (neYY12y.txt) for every baseline and round year
  - the latest year-to-date file (neYYMMy.txt) and the prior-year file for the same month
A file is (re)downloaded when it is missing or Census has changed it (size or Last-Modified).
manifest.json records what was fetched, so every run is auditable.
"""
import hashlib, json, re, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www2.census.gov/econ/bps/Place/Northeast%20Region/"
ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "raw" / "bps"
MANIFEST = DIR / "manifest.json"
FIRST_YEAR = 2015          # earliest full year kept
ROUND_START = (2025, 7)    # Fourth Round begins July 1, 2025 (P.L.2024, c.2)
DCA_URL = "https://www.nj.gov/dca/dlps/pdf/FourthRoundCalculation_Workbook.xlsx"
UA = {"User-Agent": "nj-housing-pace (public-data research; github.com/SBoyapati13)"}

def _get(url, method="GET"):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA, method=method), timeout=60)

def available():
    html = _get(BASE).read().decode("utf-8", "replace")
    yy = lambda y: (1900 if int(y) >= 80 else 2000) + int(y)   # files run 1988-present
    return sorted({(yy(y), int(m)) for y, m in re.findall(r"ne(\d{2})(\d{2})y\.txt", html)})

def latest_vintage():
    return max(available())

def needed(vintage):
    year, month = vintage
    names = {f"ne{y % 100:02d}12y.txt" for y in range(FIRST_YEAR, year)}
    names.add(f"ne{year % 100:02d}{month:02d}y.txt")
    names.add(f"ne{(year - 1) % 100:02d}{month:02d}y.txt")   # for trailing-12-month pace
    ry, rm = ROUND_START
    if rm > 1:
        names.add(f"ne{ry % 100:02d}{rm - 1:02d}y.txt")         # months before the round began
    return sorted(names)

def sync():
    DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"files": {}}
    vintage = latest_vintage()
    changed = []
    for name in needed(vintage):
        time.sleep(1.5)   # be polite to census.gov
        head = _get(BASE + name, "HEAD")
        remote = {"size": head.headers.get("Content-Length"), "last_modified": head.headers.get("Last-Modified")}
        local = manifest["files"].get(name, {})
        path = DIR / name
        if path.exists() and local.get("size") == remote["size"] and local.get("last_modified") == remote["last_modified"]:
            continue
        data = _get(BASE + name).read()
        path.write_bytes(data)
        manifest["files"][name] = {**remote, "sha256": hashlib.sha256(data).hexdigest(),
                                   "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        changed.append(name)
    try:   # obligation source: record upstream state, never auto-replace (it is a methodology input)
        time.sleep(1.5)
        h = _get(DCA_URL, "HEAD")
        manifest["dca_upstream"] = {"size": h.headers.get("Content-Length"), "last_modified": h.headers.get("Last-Modified")}
    except Exception as e:
        manifest["dca_upstream"] = {"error": str(e)}
    manifest["vintage"] = {"year": vintage[0], "month": vintage[1]}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return vintage, changed

if __name__ == "__main__":
    v, ch = sync()
    print(f"latest Census vintage: {v[0]}-{v[1]:02d}; new or revised files: {ch or 'none'}")


# ---------------------------------------------------------------------------
# Certificates of occupancy (completed housing units) from the NJ DCA
# Construction Reporter: one year-to-date workbook per month, per year.
# We keep the December file for each complete year, the June 2025 file
# (the month before the Fourth Round began), and the latest month published.
# ---------------------------------------------------------------------------
CO_DIR = ROOT / "data" / "raw" / "co"
CO_MANIFEST = CO_DIR / "manifest.json"
CO_FIRST_YEAR = 2015
CO_PAGES = ["https://www.nj.gov/dca/codes/reporter/co{y}.shtml",
            "https://www.nj.gov/dca/divisions/codes/reporter/co{y}.html"]

def co_links(year):
    for page in CO_PAGES:
        try:
            html = _get(page.format(y=year)).read().decode("utf-8", "replace")
        except Exception:
            continue
        links = {}
        for href in re.findall(r'href="([^"]*certs_(\d{2})_' + str(year) + r'\.xls)"', html, re.I):
            url = href[0] if href[0].startswith("http") else "https://www.nj.gov" + href[0]
            links[int(href[1])] = url
        if links:
            return links
        time.sleep(1.5)
    return {}

def sync_co():
    CO_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(CO_MANIFEST.read_text()) if CO_MANIFEST.exists() else {"files": {}}
    this_year = datetime.now(timezone.utc).year
    wanted, latest = {}, None
    for y in range(CO_FIRST_YEAR, this_year + 1):
        time.sleep(1.5)
        links = co_links(y)
        if not links:
            continue
        m = max(links)
        latest = (y, m)
        if 12 in links:
            wanted[f"certs_12_{y}.xls"] = links[12]
        if y == 2025 and 6 in links:
            wanted["certs_06_2025.xls"] = links[6]
    if latest:
        y, m = latest
        wanted[f"certs_{m:02d}_{y}.xls"] = co_links(y)[m]
    changed = []
    for name, url in sorted(wanted.items()):
        time.sleep(1.5)
        head = _get(url, "HEAD")
        remote = {"size": head.headers.get("Content-Length"), "last_modified": head.headers.get("Last-Modified"), "url": url}
        local = manifest["files"].get(name, {})
        path = CO_DIR / name
        if path.exists() and local.get("size") == remote["size"] and local.get("last_modified") == remote["last_modified"]:
            continue
        data = _get(url).read()
        path.write_bytes(data)
        manifest["files"][name] = {**remote, "sha256": hashlib.sha256(data).hexdigest(),
                                   "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        changed.append(name)
    if latest:
        manifest["vintage"] = {"year": latest[0], "month": latest[1]}
    CO_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return latest, changed
