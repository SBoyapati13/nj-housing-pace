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
