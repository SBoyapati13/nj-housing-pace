"""Figure 3: town-level map of live Fourth Round progress (Census cartographic boundaries, 2024)."""
import io, json, math, urllib.request, zipfile
from pathlib import Path
import pandas as pd
import shapefile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon, Patch

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data" / "raw" / "geo" / "cb_2024_34_cousub_500k.zip"
GEO_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_34_cousub_500k.zip"
OUT = ROOT / "out"
SURFACE, INK, INK2, EDGE = "#fcfcfb", "#0b0b0b", "#52514e", "#ffffff"
# diverging blue<->red, each arm validated as an ordinal ramp; neutral gray (+hatch) = no obligation
CLASSES = [
    ("closed",   "#a8262b", None, "Would need more than its best year since 2015 (at 20%)"),
    ("behind",   "#ef8a83", None, "Below pro-rated pace"),
    ("on_pace",  "#86b6ef", None, "At or above pro-rated pace (1–2×)"),
    ("ahead",    "#1c5cab", None, "More than twice the pro-rated pace"),
    ("exempt",   "#e4e3df", "////", "No new obligation (Qualified Urban Aid)"),
    ("no_data",  "#ffffff", None, "No Census permit data"),
]
COLOR = {k: c for k, c, _, _ in CLASSES}; HATCH = {k: h for k, _, h, _ in CLASSES}
LABELS = {"Newark city": (-62, 14), "Jersey City": (22, -14), "Lakewood township": (14, 0), "Paramus borough": (18, 6),
          "Wayne township": (-62, 10), "Secaucus town": (24, 4), "Trenton city": (12, -12), "Camden city": (-60, 8)}

def shapes():
    if not GEO.exists():
        GEO.parent.mkdir(parents=True, exist_ok=True)
        GEO.write_bytes(urllib.request.urlopen(GEO_URL, timeout=90).read())
    z = zipfile.ZipFile(GEO); b = "cb_2024_34_cousub_500k"
    r = shapefile.Reader(shp=io.BytesIO(z.read(b + ".shp")), dbf=io.BytesIO(z.read(b + ".dbf")))
    for sr in r.iterShapeRecords():
        pts, parts = sr.shape.points, list(sr.shape.parts) + [len(sr.shape.points)]
        yield sr.record["GEOID"], [pts[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]

def classify(row):
    if not row.matched: return "no_data"
    if not row.prospective_need > 0: return "exempt"
    if row.inclusionary_route_status == "past": return "closed"
    if row.live_progress >= 2: return "ahead"
    if row.live_progress >= 1: return "on_pace"
    return "behind"

def main():
    df = pd.read_csv(OUT / "town_pace.csv", dtype={"fips": str}).set_index("fips")
    s = json.loads((OUT / "summary.json").read_text())
    vy, vm = map(int, s["vintage"].split("-"))
    cls = df.apply(classify, axis=1)
    plt.rcParams["hatch.color"] = "#b9b8b3"; plt.rcParams["hatch.linewidth"] = 0.5
    k = math.cos(math.radians(40.1))                       # equirectangular, scaled at NJ's mid-latitude
    fig, ax = plt.subplots(figsize=(7.6, 11.6), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    patches = {c: [] for c in COLOR}; any_route = []
    for geoid, rings in shapes():
        c = cls.get(geoid, "no_data")
        for ring in rings:
            poly = Polygon([(x * k, y) for x, y in ring], closed=True)
            patches[c].append(poly)
            if geoid in df.index and df.at[geoid, "any_route_status"] == "past":
                any_route.append(Polygon([(x * k, y) for x, y in ring], closed=True))
    for c, ps in patches.items():
        ax.add_collection(PatchCollection(ps, facecolor=COLOR[c], edgecolor=EDGE if c != "no_data" else "#b9b8b3",
                                          linewidth=0.35, hatch=HATCH[c], zorder=2))
    ax.add_collection(PatchCollection(any_route, facecolor="none", edgecolor=INK, linewidth=0.9, zorder=3))
    for name, off in LABELS.items():
        row = df[df.municipality == name]
        if row.empty: continue
        g = row.index[0]
        for geoid, rings in shapes():
            if geoid != g: continue
            ring = max(rings, key=len); xs = [p[0] * k for p in ring]; ys = [p[1] for p in ring]
            ax.annotate(name.replace(" city", "").replace(" township", "").replace(" borough", "").replace(" town", ""),
                        (sum(xs) / len(xs), sum(ys) / len(ys)), xytext=off, textcoords="offset points",
                        fontsize=7.5, color=INK, va="center", zorder=5,
                        bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.85),
                        arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
            break
    ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
    counts = cls.value_counts()
    handles = [Patch(facecolor=c, edgecolor="#b9b8b3", hatch=h, label=f"{lab} ({counts.get(key, 0)})") for key, c, h, lab in CLASSES if counts.get(key, 0)]
    handles.append(Patch(facecolor="none", edgecolor=INK, linewidth=1.2, label=f"Outlined: would need more than its best year since 2015\neven if every new home were affordable ({s['any_route_closed']})"))
    leg = fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.03, 0.035), fontsize=7.6, frameon=True, framealpha=1, edgecolor="#e4e3df",
                     title="Permit pace vs. pro-rated obligation, by town", title_fontsize=8.5, borderpad=0.8, alignment="left")
    leg.get_frame().set_facecolor(SURFACE)
    months = "January February March April May June July August September October November December".split()
    fig.suptitle("Homes permitted since July 2025, compared with each town's\nFourth Round affordable-housing obligation",
                 x=0.03, ha="left", fontsize=13, fontweight="bold", color=INK, y=0.985)
    fig.text(0.03, 0.932, f"Fourth Round to date: July 2025 – {months[vm - 1]} {vy} ({s['months_elapsed']} of 120 months). Pace = homes permitted × 20% ÷ obligation pro-rated\nto date. A building-permit indicator, not a compliance finding. Updates with each Census release.",
             fontsize=8, color=INK2, va="top")
    fig.text(0.03, 0.012, "Sources: U.S. Census Bureau Building Permits Survey; NJ DCA Fourth Round Calculation Workbook (2024); Census cartographic boundaries (2024).",
             fontsize=6.8, color=INK2)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.19)
    fig.savefig(OUT / "map_live_progress.png", facecolor=SURFACE); plt.close(fig)
    print("map written:", dict(counts))

if __name__ == "__main__":
    main()
