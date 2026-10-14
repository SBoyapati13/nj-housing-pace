"""Interactive web map: docs/index.html + docs/data/towns.json (served by GitHub Pages from /docs).

Rebuilt from out/town_pace.csv, out/summary.json and the Census boundary file on every run,
so the published page always reflects the latest data from both permit sources. Also writes
out/web_preview.html: the same page with the data inlined, for previews and sharing.
"""
import json, math
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from map import shapes

ROOT = Path(__file__).resolve().parents[1]
OUT, DOCS = ROOT / "out", ROOT / "docs"
REPO_URL = "https://github.com/SBoyapati13/nj-housing-pace"
WIDTH = 600.0          # SVG viewBox width
MIN_STEP = 0.35        # drop vertices closer than this (viewBox units) to the last kept one

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
        why = "Qualified Urban Aid municipality" if r.qualified_urban_aid == 1 else "calculated obligation of zero"
        towns.append({
            "f": f, "n": r.municipality, "c_": r.county, "d": d,
            "cls": r.class_live, "clsb": r.class_base, "one": int(r.live_sources) == 1 and r.class_live in ("below_half", "half_to_one", "one_to_two", "two_plus"), "pn": clean(r.prospective_need), "why": why,
            "tgt": clean(r.cw_target, 1),
            "c": {"u": clean(r.cw_units), "m": clean(r.cw_months), "p": clean(r.cw_pace, 3), "ok": bool(r.cw_usable),
                  "est": clean(round(r.cw_units - r.cw_reported_units, 1)) if pd.notna(r.cw_units) else None,
                  "fu": clean(r.c_units), "fm": clean(r.c_months), "fp": clean(r.c_pace, 3), "fok": bool(r.c_usable),
                  "best": clean(r.c_best_year), "b20": clean(r.c_best_20), "b100": clean(r.c_best_100)},
            "s": {"u": clean(r.dw_units), "m": clean(r.dw_months), "p": clean(r.dw_pace, 3), "ok": bool(r.dw_usable),
                  "zu": bool(r.dw_zero_unconfirmed),
                  "best": clean(r.d_best_year), "b20": clean(r.d_best_20), "b100": clean(r.d_best_100)},
            "cb": {"n": clean(r.c_base_years), "a": clean(r.c_base_avg, 1), "v": clean(r.c_base_cov, 3)},
            "sb": {"n": clean(r.d_base_years), "a": clean(r.d_base_avg, 1), "v": clean(r.d_base_cov, 3)},
            "fin": clean(r.final_prospective_need), "fin_status": clean(r.final_status), "fin_doc": clean(r.final_evidence), "fin_src": clean(r.final_source),
            "co": clean(r.co_reported_since_jul2025), "cr": clean(r.completion_ratio_2015_2024, 3),
        })
    payload = {"meta": {"width": WIDTH, "height": height, "repo": REPO_URL,
                        "built_utc": last_data_update()},
               "summary": summary, "towns": towns}
    data = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "data" / "towns.json").write_text(data)
    (DOCS / ".nojekyll").write_text("")
    tpl = (ROOT / "src" / "web_template.html").read_text()
    (DOCS / "index.html").write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Live map of homes permitted in each New Jersey town since July 2025, compared with its Fourth Round affordable-housing obligation, from two public permit sources.">\n'
        + tpl.replace("<style>", "<style>\n[hidden]{display:none!important} body{margin:0}", 1)
        + "\n</html>\n")
    inline = '<script id="town-data" type="application/json">' + data.replace("</", "<\\/") + "</script>\n"
    i = tpl.index("<script>\n(async")
    (OUT / "web_preview.html").write_text(tpl[:i] + inline + tpl[i:])
    print(f"web map written: {len(towns)} towns, data {len(data) / 1e6:.2f} MB")

if __name__ == "__main__":
    main()
