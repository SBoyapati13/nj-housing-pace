"""Charts: county coverage, frozen baseline (Figure 1) and live round-to-date progress (Figure 2)."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
SURFACE, INK, INK2, GRID, SERIES = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
SOURCES = "Sources: U.S. Census Bureau Building Permits Survey (place files); NJ DCA Fourth Round Calculation Workbook (2024)."
MONTHS = "January February March April May June July August September October November December".split()

def county(df, units, target):
    has = df[df.matched & (df.prospective_need > 0)]
    g = has.groupby("county").agg(units=(units, "sum"), target=(target, "sum"))
    g["ratio"] = g.units * 0.20 / g.target
    return g.sort_values("ratio")

def draw(g, fname, title, subtitle, xlabel):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(8, 7.2), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    y = list(range(len(g)))
    ax.barh(y, g.ratio, height=0.68, color=SERIES, edgecolor=SURFACE, linewidth=2, zorder=2)
    for i, v in enumerate(g.ratio):
        ax.text(v + 0.04, i, f"{v:.2f}", va="center", fontsize=8.5, color=INK2, zorder=4,
                bbox=dict(boxstyle="square,pad=0.15", fc=SURFACE, ec="none"))
    ax.axvline(1.0, color=INK, linewidth=1.2, linestyle=(0, (4, 3)), zorder=3)
    ax.text(1.03, len(g) - 0.4, "Pro-rated pace", fontsize=9, color=INK, va="center")
    ax.set_yticks(y); ax.set_yticklabels(g.index, color=INK)
    ax.set_xlim(0, max(3.4, g.ratio.max() + 0.4))
    ax.set_xlabel(xlabel, color=INK2, fontsize=9)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0); ax.set_axisbelow(True)
    for s in ["top", "right", "left"]: ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(colors=INK2, length=0)
    fig.suptitle(title, x=0.02, ha="left", fontsize=13, fontweight="bold", color=INK, y=0.985)
    fig.text(0.02, 0.885, subtitle, fontsize=8.5, color=INK2)
    fig.text(0.02, 0.012, SOURCES, fontsize=7.5, color=INK2)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.86, bottom=0.1)
    fig.savefig(OUT / fname, facecolor=SURFACE); plt.close(fig)

def main():
    df = pd.read_csv(OUT / "town_pace.csv", dtype={"fips": str})
    s = json.loads((OUT / "summary.json").read_text())
    vy, vm = map(int, s["vintage"].split("-"))

    g = county(df, "avg_units_per_year", "annual_target")
    g.to_csv(OUT / "county_coverage.csv")
    draw(g, "county_coverage.png",
         "Permit pace relative to Fourth Round obligations, by county\n(towns with an obligation, 2021–25 average)",
         "Baseline (frozen): 2021–25 permits. Towns with a Fourth Round obligation only. Assumes a 20% set-aside on every unit (upper bound).",
         "Coverage: (avg yearly permits 2021–25 × 20%) ÷ (2025–35 obligation ÷ 10)")

    L = county(df, "live_units_round_to_date", "live_target_to_date")
    L.to_csv(OUT / "county_live_progress.csv")
    draw(L, "county_live_progress.png",
         f"Permit pace relative to pro-rated obligations, by county\n(July 2025 – {MONTHS[vm - 1]} {vy})",
         f"Live, updates with each Census release. Permits since July 2025 × 20% ÷ obligation pro-rated to {s['months_elapsed']} of 120 months.",
         "Progress: (permits since July 2025 × 20%) ÷ (obligation × months elapsed ÷ 120)")
    print("charts written")

if __name__ == "__main__":
    main()
