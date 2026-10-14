"""Fetch new or revised source files. Three sources, each with its own manifest:

  data/raw/bps/      Census Building Permits Survey place files (Northeast region)
                     - revised annual files (neYYYYa.txt), 2015 onward
                     - preliminary December files for full years without an annual file yet
                     - June and December 2025 preliminary files (to split 2025 at the round start)
                     - the latest year-to-date file
  data/raw/dca_bp/   NJ DCA Construction Reporter, housing units authorized by building permits
                     - revised yearly files, 2015 onward
                     - December year-to-date files (they mark towns with "Missing Data")
                     - June 2025 and the latest year-to-date file
  data/raw/co/       NJ DCA Construction Reporter, certificates of occupancy (completions)

A file is (re)downloaded when it is missing or its size or Last-Modified time changed.
A failed request never writes an error into a manifest: the previous state is kept and the
failure is returned to the caller (and printed), so a transient outage can't change published files.
"""
import hashlib, json, re, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "nj-housing-pace (public-data research; github.com/SBoyapati13)"}
FIRST_YEAR = 2015
ROUND_START = (2025, 7)    # Fourth Round begins July 1, 2025 (P.L.2024, c.2)

def _get(url, method="GET"):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA, method=method), timeout=60)

def _exists(url):
    try:
        _get(url, "HEAD"); return True
    except urllib.error.HTTPError as e:
        if e.code == 404: return False
        raise

def _sync_files(wanted, directory, manifest, errors):
    """Download each {local name: url} that is new or changed upstream. Returns names changed."""
    changed = []
    for name, url in sorted(wanted.items()):
        time.sleep(1.5)
        try:
            head = _get(url, "HEAD")
            remote = {"size": head.headers.get("Content-Length"), "last_modified": head.headers.get("Last-Modified"), "url": url}
            local = manifest["files"].get(name, {})
            path = directory / name
            if path.exists() and local.get("size") == remote["size"] and local.get("last_modified") == remote["last_modified"]:
                continue
            data = _get(url).read()
        except Exception as e:                      # keep the previous copy and manifest entry
            errors.append(f"{name}: {e}"); continue
        path.write_bytes(data)
        manifest["files"][name] = {**remote, "sha256": hashlib.sha256(data).hexdigest(),
                                   "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        changed.append(name)
    return changed

def _load(path):
    return json.loads(path.read_text()) if path.exists() else {"files": {}}

# ---------------------------------------------------------------------------
# Census Building Permits Survey
# ---------------------------------------------------------------------------
BASE = "https://www2.census.gov/econ/bps/Place/Northeast%20Region/"
DIR = ROOT / "data" / "raw" / "bps"
MANIFEST = DIR / "manifest.json"
DCA_URL = "https://www.nj.gov/dca/dlps/pdf/FourthRoundCalculation_Workbook.xlsx"

def available():
    html = _get(BASE).read().decode("utf-8", "replace")
    yy = lambda y: (1900 if int(y) >= 80 else 2000) + int(y)   # monthly files run 1988-present
    ytd = sorted({(yy(y), int(m)) for y, m in re.findall(r"ne(\d{2})(\d{2})y\.txt", html)})
    annual = sorted({int(y) for y in re.findall(r"ne(\d{4})a\.txt", html)})
    return ytd, annual

def needed(vintage, annual):
    year, month = vintage
    names = set()
    for y in range(FIRST_YEAR, year):
        names.add(f"ne{y}a.txt" if y in annual else f"ne{y % 100:02d}12y.txt")
    ry, rm = ROUND_START
    names.update({f"ne{ry % 100:02d}{rm - 1:02d}y.txt", f"ne{ry % 100:02d}12y.txt"})   # preliminary split of 2025
    names.add(f"ne{year % 100:02d}{month:02d}y.txt")
    return sorted(names)

def _other_vintage(path):
    m = _load(path).get("vintage")
    return (m["year"], m["month"]) if m else None

def sync():
    DIR.mkdir(parents=True, exist_ok=True)
    manifest, errors = _load(MANIFEST), []
    try:
        ytd, annual = available()
    except Exception as e:                       # index unreachable: keep everything as it was
        errors.append(f"Census index: {e}")
        v = manifest.get("vintage")
        return ((v["year"], v["month"]) if v else None), [], errors
    vintage = max(ytd)
    wanted = {n: BASE + n for n in needed(vintage, annual)}
    other = _other_vintage(BP_MANIFEST)          # state permits: Census file for the common window's last month
    if other and ROUND_START <= other < vintage and not (other[1] == 12 and other[0] in annual):
        n = f"ne{other[0] % 100:02d}{other[1]:02d}y.txt"; wanted[n] = BASE + n
    changed = _sync_files(wanted, DIR, manifest, errors)
    try:   # obligation source: record upstream state, never auto-replace (it is a methodology input)
        time.sleep(1.5)
        h = _get(DCA_URL, "HEAD")
        manifest["dca_upstream"] = {"size": h.headers.get("Content-Length"), "last_modified": h.headers.get("Last-Modified")}
    except Exception as e:
        errors.append(f"DCA obligation workbook: {e}")
    manifest["vintage"] = {"year": vintage[0], "month": vintage[1]}
    manifest["annual_years"] = [y for y in annual if y >= FIRST_YEAR]
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return vintage, changed, errors

# ---------------------------------------------------------------------------
# NJ DCA Construction Reporter: housing units authorized by building permits
# ---------------------------------------------------------------------------
REPORTER = "https://www.nj.gov/dca/codes/reporter/"
BP_DIR = ROOT / "data" / "raw" / "dca_bp"
BP_MANIFEST = BP_DIR / "manifest.json"

def monthly_url(y, m):
    folder = f"{y}m" if y >= 2025 else f"{y}monthly"
    return f"{REPORTER}{folder}/house_{m:02d}_{y}.xls"

def yearly_links():
    html = _get(REPORTER + "building_permits.shtml").read().decode("utf-8", "replace")
    out = {}
    for path, y in re.findall(r'href="([^"]*?(\d{4})yearly/house_\d+\.xls)"', html, re.I):
        out[int(y)] = path if path.startswith("http") else "https://www.nj.gov" + path
    return out

def latest_month(previous):
    """Newest monthly file, probing forward from the last one seen (the state posts no index of them)."""
    y, m = previous or (2025, 6)
    while True:
        ny, nm = (y, m + 1) if m < 12 else (y + 1, 1)
        time.sleep(0.5)
        if not _exists(monthly_url(ny, nm)):
            return (y, m)
        y, m = ny, nm

def sync_dca_permits():
    BP_DIR.mkdir(parents=True, exist_ok=True)
    manifest, errors = _load(BP_MANIFEST), []
    prev = manifest.get("vintage")
    prev = (prev["year"], prev["month"]) if prev else None
    try:
        yl = yearly_links()
        ly, lm = latest_month(prev)
    except Exception as e:
        errors.append(f"DCA permit index: {e}")
        return prev, [], errors
    wanted = {f"house_yearly_{y}.xls": u for y, u in yl.items() if y >= FIRST_YEAR}
    last_full = ly if lm == 12 else ly - 1
    for y in range(FIRST_YEAR, last_full + 1):
        wanted[f"house_12_{y}.xls"] = monthly_url(y, 12)
    wanted["house_06_2025.xls"] = monthly_url(2025, 6)
    wanted[f"house_{lm:02d}_{ly}.xls"] = monthly_url(ly, lm)
    for y in range(2025, ly):                    # December year-to-date for each full year inside the round
        wanted[f"house_12_{y}.xls"] = monthly_url(y, 12)
    other = _other_vintage(MANIFEST)             # Census: state file for the common window's last month
    if other and ROUND_START <= other < (ly, lm):
        wanted[f"house_{other[1]:02d}_{other[0]}.xls"] = monthly_url(*other)
    changed = _sync_files(wanted, BP_DIR, manifest, errors)
    if not prev or (ly, lm) >= prev:
        manifest["vintage"] = {"year": ly, "month": lm}
    manifest["yearly_years"] = sorted(y for y in yl if y >= FIRST_YEAR)
    BP_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    v = manifest["vintage"]
    return (v["year"], v["month"]), changed, errors

# ---------------------------------------------------------------------------
# NJ DCA Construction Reporter: certificates of occupancy (completed housing units)
# We keep the December file for each complete year, the June 2025 file
# (the month before the Fourth Round began), and the latest month published.
# ---------------------------------------------------------------------------
CO_DIR = ROOT / "data" / "raw" / "co"
CO_MANIFEST = CO_DIR / "manifest.json"
CO_PAGES = ["https://www.nj.gov/dca/codes/reporter/co{y}.shtml",
            "https://www.nj.gov/dca/divisions/codes/reporter/co{y}.html"]

def co_links(year):
    for page in CO_PAGES:
        try:
            html = _get(page.format(y=year)).read().decode("utf-8", "replace")
        except Exception:
            time.sleep(1.5); continue
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
    manifest, errors = _load(CO_MANIFEST), []
    prev = manifest.get("vintage")
    prev = (prev["year"], prev["month"]) if prev else None
    this_year = datetime.now(timezone.utc).year
    wanted, latest, latest_url = {}, None, None
    for y in range(FIRST_YEAR, this_year + 1):
        time.sleep(1.5)
        links = co_links(y)
        if not links:
            continue
        m = max(links)
        latest, latest_url = (y, m), links[m]
        if 12 in links:
            wanted[f"certs_12_{y}.xls"] = links[12]
        if y == 2025 and 6 in links:
            wanted["certs_06_2025.xls"] = links[6]
    if latest and prev and latest < prev:       # a page failed to load: never move the vintage backward
        errors.append(f"certificates index returned {latest}, older than {prev}; kept {prev}")
        latest = None
    if latest:
        wanted[f"certs_{latest[1]:02d}_{latest[0]}.xls"] = latest_url
    changed = _sync_files(wanted, CO_DIR, manifest, errors)
    if latest:
        manifest["vintage"] = {"year": latest[0], "month": latest[1]}
    CO_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    v = manifest.get("vintage")
    return ((v["year"], v["month"]) if v else None), changed, errors

if __name__ == "__main__":
    for label, fn in [("Census", sync), ("DCA permits", sync_dca_permits), ("DCA completions", sync_co)]:
        v, ch, err = fn()
        print(f"{label}: vintage {v}; new or revised: {ch or 'none'}" + (f"; errors: {err}" if err else ""))
