"""Rewrite the LIVE block in README.md from out/summary.json, data/runs.jsonl and data/history/."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- LIVE:START -->", "<!-- LIVE:END -->"
MONTHS = "January February March April May June July August September October November December".split()

def changes(vintage):
    snaps = sorted((ROOT / "data" / "history").glob("town_pace_*.csv"))
    prev = [p for p in snaps if p.stem.split("_")[-1] < vintage]
    if not prev:
        return "First live run: no earlier release to compare against yet."
    a = pd.read_csv(prev[-1]).set_index("fips"); b = pd.read_csv(ROOT / "out" / "town_pace.csv").set_index("fips")
    j = b[["municipality", "live_progress"]].join(a[["live_progress"]], rsuffix="_prev").dropna()
    up = j[(j.live_progress_prev < 1) & (j.live_progress >= 1)].municipality.tolist()
    down = j[(j.live_progress_prev >= 1) & (j.live_progress < 1)].municipality.tolist()
    fmt = lambda xs: ", ".join(xs[:8]) + (f" and {len(xs) - 8} more" if len(xs) > 8 else "") if xs else "none"
    return (f"Since the previous release ({prev[-1].stem.split('_')[-1]}): towns that moved **onto** pace: {fmt(up)}. "
            f"Towns that fell **off** pace: {fmt(down)}.")

def main():
    s = json.loads((ROOT / "out" / "summary.json").read_text())
    runs = [json.loads(l) for l in (ROOT / "data" / "runs.jsonl").read_text().splitlines() if l.strip()]
    runs = [r for r in runs if "vintage" in r]
    vy, vm = map(int, s["vintage"].split("-"))
    hist = "\n".join(f"| {r['vintage']} | {r['run_utc'][:10]} | {r.get('method', 'v1 (superseded)')} | {r['live_units_round_to_date']:,} | {r['live_progress_statewide']:.0%} | {r['live_towns_below_half']} |"
                     for r in runs[-12:])
    h = s["health"]
    icon = {"ok": "OK", "warn": "WARN", "stop": "STOP", "manual": "MANUAL"}
    health_rows = "\n".join(f"| {c['check'].replace('_', ' ')} | {icon[c['status']]} | {c['detail']} |" for c in h["checks"])
    banner = ("" if h["can_answer"] else
              "> **This system cannot currently answer its question.** A STOP check failed (see System health). "
              "The figures below are the last valid run and should not be read as current.\n\n")
    block = f"""{START}
## Live status

*Updated automatically from the Census release covering January–{MONTHS[vm - 1]} {vy}. Every update is logged in `data/runs.jsonl`.*

**Interactive map:** https://sboyapati13.github.io/nj-housing-pace/ (search any town, hover for its numbers, switch between Fourth Round to date and the 2021–25 baseline). Rebuilt by `src/web.py` and redeployed on every update.

{banner}| Fourth Round to date (July 2025 – {MONTHS[vm - 1][:3]} {vy}, {s['months_elapsed']} of 120 months) | |
|---|---|
| Homes permitted statewide | {s['live_units_round_to_date']:,} |
| Implied affordable at 20% | {s['live_implied_affordable_to_date']:,.0f} |
| Pro-rated obligation to date | {s['live_target_to_date']:,.0f} |
| **Statewide progress** | **{s['live_progress_statewide']:.0%}** |
| Obligated towns on pace (≥ 1.0) | {s['live_towns_on_pace']} of {s['live_obligated_towns']} |
| Obligated towns below half pace | {s['live_towns_below_half']} of {s['live_obligated_towns']} |
| Share of permits in exempt towns | {s['live_exempt_share_round_to_date']:.0%} |
| Homes permitted, trailing 12 months | {s['live_units_ttm']:,} |

**Point of no return.** For each obligated town, could it still finish by June 2035 if it built at its best year since 2015?
- **Inclusionary route closed** (20% of new homes affordable): **{s['inclusionary_route_closed']} towns**, holding {s['inclusionary_route_closed_obligation']:,} units of obligation. Another {s['inclusionary_route_closing_next_12m']} close within 12 months if their current pace holds.
- **Every route closed** (even if *every* new home were affordable): **{s['any_route_closed']} towns**, holding {s['any_route_closed_obligation']:,} units.
- Per-town status and dates are in `out/town_pace.csv` (`inclusionary_route_*`, `any_route_*`).

{changes(s['vintage'])}

![Figure 1](out/map_live_progress.png)

*Figure 1. Every New Jersey town, colored by Fourth Round progress to date. Dark red: towns that couldn't finish even by building at their best year since 2015 with a 20% set-aside. Outlined: towns that couldn't finish even if every new home were affordable. Hatched gray: urban-aid towns exempt from new obligations.*

![Figure 2](out/county_live_progress.png)

*Figure 2. The same measure aggregated by county.*

**System health.** Overall: **{icon[h['overall']]}**

| Check | Status | Detail |
|---|---|---|
{health_rows}

*Run history (last 12 updates; full log in `data/runs.jsonl`):*

| Census vintage | Run date | Method | Homes since round start | Statewide progress | Towns below half |
|---|---|---|---|---|---|
{hist}
{END}"""
    readme = ROOT / "README.md"; text = readme.read_text()
    if START in text:
        text = text[:text.index(START)] + block + text[text.index(END) + len(END):]
    else:
        anchor = "## 1. Background"
        text = text.replace(anchor, block + "\n\n" + anchor, 1)
    readme.write_text(text)
    print("README live block updated")

if __name__ == "__main__":
    main()
