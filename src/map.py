"""Figure 1: town-level map of permit pace since July 2025 (method v3; Census cartographic boundaries, 2024)."""
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
SURFACE, INK, INK2, EDGE = "#ffffff", "#14181d", "#4c5560", "#ffffff"
MONTHS = "January February March April May June July August September October November December".split()
# Diverging orange <-> purple (each arm validated as an ordinal ramp, light and dark); grays = can't be read yet.
CLASSES = [
    ("below_half",         "#b35806", None,   "Below half the pro-rated pace"),
    ("half_to_one",        "#f1a340", None,   "Half to full pro-rated pace"),
    ("one_to_two",         "#a497d1", None,   "At or above pro-rated pace (1–2×)"),
    ("two_plus",           "#542788", None,   "More than twice the pro-rated pace"),
    ("disagree",           "#a3a9b0", "....", "The two permit sources disagree"),
    ("not_enough_reports", "#d5d9dd", None,   "Not enough reports to read"),
    ("too_early",          "#eceef0", None,   "Too early to read (small obligation)"),
    ("exempt",             "#e4e3df", "////", "No new obligation"),
    ("no_data",            "#ffffff", None,   "No permit data"),
]
COLOR = {k: c for k, c, _, _ in CLASSES}; HATCH = {k: h for k, _, h, _ in CLASSES}
LABEL = {k: l for k, _, _, l in CLASSES}
ONE_SOURCE_NOTE = {"below_half", "half_to_one", "one_to_two", "two_plus"}

def shapes():
    if not GEO.exists():
        GEO.parent.mkdir(parents=True, exist_ok=True)
        GEO.write_bytes(urllib.request.urlopen(GEO_URL, timeout=90).read())
    z = zipfile.ZipFile(GEO); b = "cb_2024_34_cousub_500k"
    r = shapefile.Reader(shp=io.BytesIO(z.read(b + ".shp")), dbf=io.BytesIO(z.read(b + ".dbf")))
    for sr in r.iterShapeRecords():
        pts, parts = sr.shape.points, list(sr.shape.parts) + [len(sr.shape.points)]
        yield sr.record["GEOID"], [pts[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]

def month(v):
    y, m = map(int, v.split("-")); return f"{MONTHS[m - 1]} {y}"

def main():
    df = pd.read_csv(OUT / "town_pace.csv", dtype={"fips": str}).set_index("fips")
    s = json.loads((OUT / "summary.json").read_text())
    cls = df.class_live
    plt.rcParams["hatch.color"] = "#9a9a96"; plt.rcParams["hatch.linewidth"] = 0.5
    k = math.cos(math.radians(40.1))                       # equirectangular, scaled at NJ's mid-latitude
    fig, ax = plt.subplots(figsize=(7.6, 10.4), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    patches = {c: [] for c in COLOR}
    for geoid, rings in shapes():
        c = cls.get(geoid, "no_data")
        for ring in rings:
            patches[c].append(Polygon([(x * k, y) for x, y in ring], closed=True))
    for c, ps in patches.items():
        ax.add_collection(PatchCollection(ps, facecolor=COLOR[c], edgecolor=EDGE if c != "no_data" else "#b9b8b3",
                                          linewidth=0.35, hatch=HATCH[c], zorder=2))
    ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
    counts = cls.value_counts()
    one = df.live_sources.eq(1)
    def lab(key, text):
        n = int(counts.get(key, 0)); k1 = int((cls.eq(key) & one).sum())
        return f"{text} ({n}; {k1} on one source)" if key in ONE_SOURCE_NOTE and k1 else f"{text} ({n})"
    handles = [Patch(facecolor=c, edgecolor="#b9b8b3", hatch=h, label=lab(key, l))
               for key, c, h, l in CLASSES if counts.get(key, 0)]
    leg = fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.03, 0.035), fontsize=7.6, frameon=True, framealpha=1,
                     edgecolor="#e4e3df", title="Permit pace vs. pro-rated obligation, by town", title_fontsize=8.5,
                     borderpad=0.8, alignment="left")
    leg.get_frame().set_facecolor(SURFACE)
    fig.suptitle("Homes permitted since July 2025, compared with each town's\nFourth Round affordable-housing obligation",
                 x=0.03, ha="left", fontsize=13, fontweight="bold", color=INK, y=0.985)
    fig.text(0.03, 0.927,
             f"Two permit sources, compared over the same period: July 2025 – {month(s['window_end'])}. Census (through {month(s['vintage'])}) and the\n"
             f"state's Construction Reporter (through {month(s['dca_vintage'])}). Pace = homes permitted × 20% ÷ obligation pro-rated to date.\n"
             "Colored where a town's usable sources agree or from its only usable source. An indicator built from permits, not a compliance finding.",
             fontsize=7.8, color=INK2, va="top")
    fig.text(0.03, 0.012, "Sources: U.S. Census Bureau Building Permits Survey; NJ DCA Construction Reporter; NJ DCA Fourth Round Calculation Workbook (2024); Census boundaries (2024).",
             fontsize=6.4, color=INK2)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.875, bottom=0.2)
    fig.savefig(OUT / "map_live_progress.png", facecolor=SURFACE); plt.close(fig)
    print("map written:", dict(counts))

if __name__ == "__main__":
    main()
