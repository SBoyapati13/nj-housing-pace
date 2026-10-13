"""Interactive web map: docs/index.html + docs/data/towns.json (served by GitHub Pages from /docs).

Rebuilt from out/town_pace.csv, out/summary.json and the Census boundary file on every run,
so the published page always reflects the latest Census release. Also writes
out/web_preview.html: the same page with the data inlined, for previews and sharing.
"""
import json, math
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from map import shapes, classify

ROOT = Path(__file__).resolve().parents[1]
OUT, DOCS = ROOT / "out", ROOT / "docs"
REPO_URL = "https://github.com/SBoyapati13/nj-housing-pace"
WIDTH = 600.0          # SVG viewBox width
MIN_STEP = 0.35        # drop vertices closer than this (viewBox units) to the last kept one

def base_class(row):
    if not row.matched: return "no_data"
    if not row.prospective_need > 0: return "exempt"
    if row.coverage >= 2: return "ahead"
    if row.coverage >= 1: return "on_pace"
    if row.coverage >= 0.5: return "behind"
    return "far"

def clean(v, nd=None):
    if v is None or (isinstance(v, float) and math.isnan(v)): return None
    if isinstance(v, float) and nd is not None: return round(v, nd)
    return v.item() if hasattr(v, "item") else v

def project(geoms):
    k = math.cos(math.radians(40.1))
    xs = [x * k for _, rings in geoms for r in rings for x, _ in r]
    ys = [y for _, rings in geoms for r in rings for _, y in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = WIDTH / (x1 - x0); height = (y1 - y0) * s
    paths = {}
    for geoid, rings in geoms:
        parts = []
        for r in rings:
            pts, last = [], None
            for lon, lat in r:
                p = ((lon * k - x0) * s, (y1 - lat) * s)
                if last is None or math.dist(p, last) >= MIN_STEP:
                    pts.append(p); last = p
            if len(pts) >= 3:
                parts.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
        paths[geoid] = "".join(parts)
    return paths, round(height, 1)

def last_data_update():
    """Timestamp of the last run whose inputs changed, so reruns without new data leave the page byte-identical."""
    runs = [json.loads(l) for l in (ROOT / "data" / "runs.jsonl").read_text().splitlines() if l.strip()]
    runs = [r for r in runs if "run_utc" in r]
    return runs[-1]["run_utc"] if runs else datetime.now(timezone.utc).isoformat(timespec="seconds")

def main():
    df = pd.read_csv(OUT / "town_pace.csv", dtype={"fips": str}).set_index("fips")
    summary = json.loads((OUT / "summary.json").read_text())
    paths, height = project(list(shapes()))
    towns = []
    for f, d in paths.items():
        if f not in df.index: continue
        r = df.loc[f]
        towns.append({
            "f": f, "n": r.municipality, "c": r.county, "d": d,
            "cls_live": classify(r), "cls_base": base_class(r),
            "pn": clean(r.prospective_need), "target": clean(r.live_target_to_date, 1),
            "rtd": clean(r.live_units_round_to_date), "prog": clean(r.live_progress, 3),
            "ttm": clean(r.live_units_ttm), "best": clean(r.best_year_units_since_2015),
            "avg": clean(r.avg_units_per_year, 1), "cov": clean(r.coverage, 3),
            "inc_status": clean(r.inclusionary_route_status), "inc_date": clean(r.inclusionary_route_closes),
            "any_status": clean(r.any_route_status), "any_date": clean(r.any_route_closes),
        })
    start = df[df.municipality == "Paramus borough"].index
    payload = {"meta": {"width": WIDTH, "height": height, "repo": REPO_URL,
                        "built_utc": last_data_update(),
                        "start_fips": start[0] if len(start) else None},
               "summary": summary, "towns": towns}
    data = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "data" / "towns.json").write_text(data)
    (DOCS / ".nojekyll").write_text("")
    tpl = (ROOT / "src" / "web_template.html").read_text()
    (DOCS / "index.html").write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Live map: are New Jersey towns permitting enough homes to meet their Fourth Round affordable-housing obligations?">\n'
        + tpl.replace("<style>", "<style>\n[hidden]{display:none!important} body{margin:0}", 1)
        + "\n</html>\n")
    inline = '<script id="town-data" type="application/json">' + data.replace("</", "<\\/") + "</script>\n"
    i = tpl.index("<script>\n(async")
    (OUT / "web_preview.html").write_text(tpl[:i] + inline + tpl[i:])
    print(f"web map written: {len(towns)} towns, data {len(data) / 1e6:.2f} MB")

if __name__ == "__main__":
    main()
