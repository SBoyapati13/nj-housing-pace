"""Figure 2: all homes permitted since July 2025 against the 2021-25 rate, by county, one bar per permit source (method v4)."""
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

NON = "No obligation (statewide)"

def county(df):
    """Ratio = sum of all homes permitted / sum of expected homes at the 2021-25 rate, over comparable obligated towns,
    per source; plus one row for comparable towns with no new obligation, statewide."""
    m = df[df.matched]
    ob, non = m[m.prospective_need > 0], m[~(m.prospective_need > 0)]
    def agg(t, w, by):
        t = t[t[f"{w}_comparable"].astype(bool)]
        return t.groupby(by).agg(**{f"{w[0]}u": (f"{w}_units", "sum"), f"{w[0]}e": (f"{w}_expected", "sum"), f"{w[0]}n": (f"{w}_units", "size")})
    g = agg(ob, "cw", "county").join(agg(ob, "dw", "county"), how="outer")
    one = lambda t: t[["cw_comparable", "cw_units", "cw_expected", "dw_comparable", "dw_units", "dw_expected"]].assign(_k=NON)
    n = agg(one(non), "cw", "_k").join(agg(one(non), "dw", "_k"), how="outer")
    g["c"] = g.cu / g.ce; g["d"] = g.du / g.de
    n["c"] = n.cu / n.ce; n["d"] = n.du / n.de
    return pd.concat([n, g.sort_values("d")])

def main():
    df = pd.read_csv(OUT / "town_pace.csv", dtype={"fips": str})
    s = json.loads((OUT / "summary.json").read_text())
    g = county(df); g.to_csv(OUT / "county_live_progress.csv")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(8.4, 9.2), dpi=200, facecolor=SURFACE); ax.set_facecolor(SURFACE)
    h = 0.36
    for j, key in enumerate(["c", "d"]):
        y = [i + (h / 2 + 0.02) * (1 if key == "c" else -1) for i in range(len(g))]
        ax.barh(y, g[key], height=h, color=SERIES[key][0], edgecolor=SURFACE, linewidth=1, zorder=2)
        for yy, v in zip(y, g[key]):
            if pd.notna(v):
                ax.text(v + 0.02, yy, f"{v:.2f}", va="center", fontsize=7, color=INK2, zorder=4)
    ax.axvline(1.0, color=INK, linewidth=1.1, linestyle=(0, (4, 3)), zorder=3)
    ax.text(1.02, len(g) - 0.3, "Same as 2021–25 rate", fontsize=8.5, color=INK, va="center")
    ax.axhline(0.5, color=GRID, linewidth=1.0, zorder=1)
    nlab = lambda v: "–" if pd.isna(v) else str(int(v))
    ax.set_yticks(range(len(g))); ax.set_yticklabels([f"{i}  ({nlab(r.cn)} | {nlab(r.dn)})" for i, r in g.iterrows()], color=INK)
    ax.get_yticklabels()[0].set_fontstyle("italic")
    ax.set_xlim(0, max(1.6, float(g[["c", "d"]].max().max()) + 0.25))
    ax.set_xlabel("All homes permitted since July 2025 ÷ homes expected at the 2021–25 rate", color=INK2, fontsize=8.5)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0); ax.set_axisbelow(True)
    for sp in ["top", "right", "left"]: ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(colors=INK2, length=0)
    fig.suptitle("Homes permitted in obligated towns against their own 2021–25 rate, by county",
                 x=0.02, ha="left", fontsize=12.5, fontweight="bold", color=INK, y=0.985)
    wy, wm = map(int, s["window_end"].split("-"))
    fig.text(0.02, 0.935, f"Both sources over the same period: July 2025 – {MONTHS[wm - 1]} {wy} ({s['window_months']} months).\n"
             f"Towns with an obligation that reported at least 75% of those months to the source and whose 2021–25 rate predicts\n"
             f"at least {s['min_expected']} homes; towns counted (Census | state) after each name. Bottom row: towns with no new\n"
             "obligation, statewide. Sorted by the state-data figure.", fontsize=8.2, color=INK2, va="top")
    fig.legend(handles=[Patch(color=c, label=l) for c, l in SERIES.values()], loc="upper left", bbox_to_anchor=(0.02, 0.865),
               fontsize=8, frameon=False, ncol=1)
    fig.text(0.02, 0.012, "Sources: U.S. Census Bureau Building Permits Survey; NJ DCA Construction Reporter; NJ DCA Fourth Round Calculation Workbook (2024).",
             fontsize=7, color=INK2)
    fig.subplots_adjust(left=0.33, right=0.97, top=0.79, bottom=0.08)
    fig.savefig(OUT / "county_live_progress.png", facecolor=SURFACE); plt.close(fig)
    print("chart written")

if __name__ == "__main__":
    main()
