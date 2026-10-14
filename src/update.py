"""One command to keep the system current: fetch -> build -> charts -> README."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch, build, chart, report
import map as town_map
import web

if __name__ == "__main__":
    vintage, changed = fetch.sync()
    print(f"Census vintage {vintage[0]}-{vintage[1]:02d}; new or revised files: {changed or 'none'}")
    co_vintage, co_changed = fetch.sync_co()
    print(f"Completions vintage {co_vintage[0]}-{co_vintage[1]:02d}; new or revised files: {co_changed or 'none'}")
    build.main(); chart.main(); town_map.main(); web.main(); report.main()
