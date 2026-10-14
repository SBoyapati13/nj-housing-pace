"""One command to keep the system current: fetch (three sources) -> build -> figures -> web map -> README."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch, build, chart, report
import map as town_map
import web, source_agreement

if __name__ == "__main__":
    for label, fn in [("State permits (NJ DCA)", fetch.sync_dca_permits), ("Census permits", fetch.sync),
                      ("Completions (NJ DCA)", fetch.sync_co)]:
        v, changed, errors = fn()
        print(f"{label}: data through {v[0]}-{v[1]:02d}; new or revised files: {changed or 'none'}" if v else f"{label}: no data yet")
        for e in errors:
            print(f"  fetch problem (previous copy kept): {e}")
    build.main(); chart.main(); town_map.main(); web.main(); report.main(); source_agreement.main()
