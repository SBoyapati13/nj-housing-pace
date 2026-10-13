"""Pin the DCA Fourth Round workbook: extract the Final Summary sheet to a small CSV and record the
original file's size and SHA-256, so the 35 MB workbook need not live in the repo.
Re-run only when deliberately adopting a new DCA release (a methodology change: log it in CHANGELOG.md).
Downloads the workbook if it is missing."""
import hashlib, json, urllib.request
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
URL = "https://www.nj.gov/dca/dlps/pdf/FourthRoundCalculation_Workbook.xlsx"
XLSX = RAW / "dca_fourth_round_workbook.xlsx"

def main():
    if not XLSX.exists():
        req = urllib.request.Request(URL, headers={"User-Agent": "nj-housing-pace (public-data research)"})
        XLSX.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    df = pd.read_excel(XLSX, "Final Summary", header=None, skiprows=3)[[0, 1, 2, 3, 4, 5, 6, 13, 16]]
    df.columns = ["fips", "dca_municode", "municipality", "county", "region", "present_need",
                  "qualified_urban_aid", "households_2020", "prospective_need"]
    df = df[df.fips.notna() & df.municipality.notna()].copy()
    df["fips"] = df.fips.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(10)
    df.to_csv(RAW / "dca_final_summary.csv", index=False)
    data = XLSX.read_bytes()
    pin = {"url": URL, "sheet": "Final Summary", "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
           "rows": int(len(df)), "note": "DCA Fourth Round calculation (October 2024). Extract of the columns used by src/build.py."}
    (RAW / "dca_pin.json").write_text(json.dumps(pin, indent=2))
    print(f"pinned {len(df)} towns, workbook sha256 {pin['sha256'][:16]}")

if __name__ == "__main__":
    main()
