"""Figure 2: permit pace by county since July 2025, one bar per permit source (method v3)."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
SURFACE, INK, INK2, GRID = "#ffffff", "#14181d", "#4c5560", "#e4e3df"
SERIES = {"c": ("#2a78d6", "Census"), "d": ("#1baf7a", "State Construction Reporter")}
MONTHS = "January February March April May June July August September October November December".split()

def county(df):
    ob = df[df.matched & (df.prospective_need > 0) & ~df.too_early]
    c = ob[ob.cw_usable].groupby("county").agg(cu=("cw_units", "sum"), ct=("cw_target", "sum"))
    d = ob[ob.dw_usable].groupby("county").agg(du=("dw_units", "sum"), dt=("dw_target", "sum"))
    g = c.join(d, how="outer")
    g["c"] = g.cu * 0.20 / g.ct; g["d"] = g.du * 0.20 / g.dt
    return g.sort_values("d")

def main():
    df = pd.read_csv(OUT / "town_pace.csv", dtype={"fips": str})
    s = json.loads((OUT / "summary.json").read_text())
    g = county(df); g.to_csv(OUT / "county_live_progress.csv")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(8, 8.6), dpi=200, facecolor=SURFACE); ax.set_facecolor(SURFACE)
    h = 0.36
    for j, key in enumerate(["c", "d"]):
        y = [i + (h / 2 + 0.02) * (1 if key == "c" else -1) for i in range(len(g))]
        ax.barh(y, g[key], height=h, color=SERIES[key][0], edgecolor=SURFACE, linewidth=1, zorder=2)
        for yy, v in zip(y, g[key]):
            if pd.notna(v):
                ax.text(v + 0.02, yy, f"{v:.2f}", va="center", fontsize=7, color=INK2, zorder=4)
    ax.axvline(1.0, color=INK, linewidth=1.1, linestyle=(0, (4, 3)), zorder=3)
    ax.text(1.02, len(g) - 0.3, "Pro-rated pace", fontsize=8.5, color=INK, va="center")
    ax.set_yticks(range(len(g))); ax.set_yticklabels(g.index, color=INK)
    ax.set_xlim(0, max(1.4, float(g[["c", "d"]].max().max()) + 0.25))
    ax.set_xlabel("Pace: homes permitted since July 2025 × 20% ÷ obligation pro-rated to date", color=INK2, fontsize=8.5)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0); ax.set_axisbelow(True)
    for sp in ["top", "right", "left"]: ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(colors=INK2, length=0)
    fig.suptitle("Permit pace relative to pro-rated Fourth Round obligations, by county",
                 x=0.02, ha="left", fontsize=12.5, fontweight="bold", color=INK, y=0.985)
    wy, wm = map(int, s["window_end"].split("-"))
    fig.text(0.02, 0.935, f"Both sources over the same period: July 2025 – {MONTHS[wm - 1]} {wy} ({s['window_months']} months).\n"
             "Towns with an obligation that reported at least 75% of those months to the source, excluding towns too early\n"
             "to read; Census estimates for towns that didn't report most months are left out. Sorted by the state-data figure.", fontsize=8.2, color=INK2, va="top")
    fig.legend(handles=[Patch(color=c, label=l) for c, l in SERIES.values()], loc="upper left", bbox_to_anchor=(0.02, 0.89),
               fontsize=8, frameon=False, ncol=1)
    fig.text(0.02, 0.012, "Sources: U.S. Census Bureau Building Permits Survey; NJ DCA Construction Reporter; NJ DCA Fourth Round Calculation Workbook (2024).",
             fontsize=7, color=INK2)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.82, bottom=0.08)
    fig.savefig(OUT / "county_live_progress.png", facecolor=SURFACE); plt.close(fig)
    print("chart written")

if __name__ == "__main__":
    main()
