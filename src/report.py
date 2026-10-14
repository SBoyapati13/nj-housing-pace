"""Rewrite the LIVE block in README.md from out/summary.json, data/runs.jsonl and data/history/."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- LIVE:START -->", "<!-- LIVE:END -->"
MONTHS = "January February March April May June July August September October November December".split()
LABELS = {"below_half": "Below half the pro-rated pace", "half_to_one": "Half to full pro-rated pace",
          "one_to_two": "At or above pro-rated pace (1–2×)", "two_plus": "More than twice the pro-rated pace",
          "disagree": "The two permit sources disagree", "not_enough_reports": "Not enough reports to read",
          "too_early": "Too early to read (small obligation)", "exempt": "No new obligation", "no_data": "No permit data"}

def month(v):
    y, m = map(int, v.split("-")); return f"{MONTHS[m - 1]} {y}"

def changes(s):
    """Towns whose map class changed since the previous v3 snapshot (snapshots of other methods aren't comparable)."""
    snaps = sorted((ROOT / "data" / "history").glob(f"town_pace_{s['method']}_*.csv"))
    if len(snaps) < 2:
        return "First run under the current method: no earlier release to compare against yet."
    a = pd.read_csv(snaps[-2]).set_index("fips"); b = pd.read_csv(snaps[-1]).set_index("fips")
    j = b[["municipality", "class_live"]].join(a[["class_live"]], rsuffix="_prev").dropna()
    moved = j[j.class_live != j.class_live_prev]
    if moved.empty:
        return "No town changed class since the previous release."
    items = [f"{r.municipality} ({LABELS[r.class_live_prev]} → {LABELS[r.class_live]})" for r in moved.itertuples()]
    return "Changed class since the previous release: " + "; ".join(items[:10]) + (f"; and {len(items) - 10} more." if len(items) > 10 else ".")

def main():
    s = json.loads((ROOT / "out" / "summary.json").read_text())
    runs = [json.loads(l) for l in (ROOT / "data" / "runs.jsonl").read_text().splitlines() if l.strip()]
    v3 = [r for r in runs if r.get("method") == s["method"]]
    hist = "\n".join(f"| {r['vintage']} | {r['dca_vintage']} | {r['run_utc'][:10]} | {r['dca_pace_usable']:.0%} | {r['census_pace_all']:.0%} | "
                     f"{r['class_counts'].get('below_half', 0)} |" for r in v3[-12:])
    h = s["health"]
    icon = {"ok": "OK", "warn": "WARN", "stop": "STOP", "manual": "MANUAL"}
    health_rows = "\n".join(f"| {c['check'].replace('_', ' ')} | {icon[c['status']]} | {c['detail']} |" for c in h["checks"])
    banner = ("" if h["can_answer"] else
              "> **This system cannot currently answer its question.** A STOP check failed (see System health). "
              "The figures below are the last valid run and should not be read as current.\n\n")
    cc = s["class_counts"]
    class_rows = "\n".join(f"| {LABELS[k]} | {cc.get(k, 0)} |" for k in LABELS if cc.get(k, 0))
    block = f"""{START}
## Live status

*Rewritten automatically whenever either permit source publishes. Census data through {month(s['vintage'])}; state data through {month(s['dca_vintage'])}. Every update is logged in `data/runs.jsonl`.*

**Interactive map:** https://sboyapati13.github.io/nj-housing-pace/ (search any town to see both sources side by side; switch between Fourth Round to date and the 2021–25 baseline).

{banner}**Pace since July 2025, towns with an obligation only**

| | State Construction Reporter | Census Building Permits Survey |
|---|---|---|
| Period | July 2025 – {month(s['dca_vintage'])} ({s['dca_months_elapsed']} months) | July 2025 – {month(s['vintage'])} ({s['months_elapsed']} months) |
| Towns counted | {s['dca_towns_usable']} with usable reports (holding {s['dca_obligation_share_usable']:.0%} of the obligation) | all {s['census_obligated_towns']} with a Census record; {s['census_towns_usable']} reported at least 75% of months |
| Homes permitted | {s['dca_units_usable']:,} | {s['census_units_all']:,}, of which {s['census_estimate_share']:.0%} are Census estimates |
| **Pace vs. pro-rated obligation** | **{s['dca_pace_usable']:.0%}** | **{s['census_pace_all']:.0%}** (towns that reported: {s['census_pace_usable']:.0%}) |
| Towns below half the pro-rated pace (excluding towns too early to read) | {s['dca_below_half']} | {s['census_below_half']} |
| Share of all permits in towns with no obligation | {s['exempt_share_dca']:.0%} | {s['exempt_share_census']:.0%} |

Pace = homes permitted × 20% ÷ obligation pro-rated to date. The 20% is a yardstick, not a bound (see §3 and §6).

**Map classes** (Figure 1). Both sources are compared over the same period, July 2025 – {month(s['window_end'])} ({s['window_months']} months); a town is colored when its usable sources agree or from its only usable source.

| Class | Towns |
|---|---|
{class_rows}

Of the {s['colored_one_source'] + s['colored_two_sources']} colored obligated towns, {s['colored_two_sources']} rest on both sources agreeing and {s['colored_one_source']} ({s['colored_one_source'] / (s['colored_one_source'] + s['colored_two_sources']):.0%}) on one usable source. {s['colored_small_window_target']} colored towns have an obligation pro-rated over the shared period of under 5 affordable homes (the too-early test uses the longer Census period; see §6), and {s['colored_census_only_no_reports']} are colored from Census alone with no homes actually reported (their Census figure is all estimates for the unreported months, or zero). Where both sources were usable ({s['both_usable']} towns), they put the town in the same class {s['sources_agree']} times and disagreed {s['sources_disagree']} times.

{s['state_zero_unconfirmed']} obligated towns have a state figure of 0 for the period that their Census reports don't confirm; those zeros are treated as not reported (§3, item 4).

**Best-year threshold.** Would reaching the obligation by June 2035 take more than permitting at the town's best fully reported year since 2015, every remaining year?
- At a 20% set-aside: yes for {s['dca_best_exceeds_20']} of {s['dca_best_assessed']} towns on state data, {s['census_best_exceeds_20']} of {s['census_best_assessed']} on Census data.
- Even if every new home were affordable: yes for {s['dca_best_exceeds_100']} (state) and {s['census_best_exceeds_100']} (Census).
- This compares obligations with past building patterns. It doesn't assess compliance: rezoning, 100%-affordable projects, credits and other routes can exceed past patterns. It isn't shown on the map.

**Final obligation numbers.** {s['final_numbers_found']} towns have a final or adopted number on file ({s['final_numbers_firm']} recorded as settled, court-ordered or accepted as calculated; most of these statuses come from town documents describing the order, see `evidence` in `data/raw/obligation_final.csv`). Using those numbers in place of the state's calculation, pace is {s['dca_pace_usable_sensitivity']:.0%} on state data (vs. {s['dca_pace_usable']:.0%}) and {s['census_pace_all_sensitivity']:.0%} on Census data (vs. {s['census_pace_all']:.0%}).

**Reported completions** (certificates of occupancy, NJ DCA; through {month(s['co_vintage'])}):
- {s['co_reported_since_jul2025']:,} homes reported completed since July 2025 in the {s['co_towns_reporting_since_jul2025']} towns not marked missing in the state's files.
- Over 2015–2024, reported completions equalled **{s['co_completion_ratio_2015_2024']:.0%}** of homes permitted (state data, same agency and town codes), in the {s['co_towns_reporting_every_year_2015_2024']} towns that reported both every year. The gap mixes projects still under way, permits never built and incomplete reporting; the data can't separate them.
- Homes permitted in 2024–25 minus homes reported completed in 2024–25: **{s['co_pipeline_2024_2025']:,}** across {s['co_towns_in_pipeline_measure']} towns, a rough size of the recent pipeline.
- {s['co_marked_missing_last_full_year']} towns are marked missing in the state's completions file for the latest full year and are left out.

{changes(s)}

![Figure 2](out/county_live_progress.png)

*Figure 2. The same pace measure by county, both sources over the same period, counting only towns with usable reports to each source and leaving out towns too early to read.*

**System health.** Overall: **{icon[h['overall']]}**

| Check | Status | Detail |
|---|---|---|
{health_rows}

*Run history under the current method (last 12 updates; full log, including superseded methods, in `data/runs.jsonl`):*

| Census data through | State data through | Run date | Pace, state data | Pace, Census | Towns below half (map) |
|---|---|---|---|---|---|
{hist}
{END}"""
    readme = ROOT / "README.md"; text = readme.read_text()
    text = text[:text.index(START)] + block + text[text.index(END) + len(END):]
    readme.write_text(text)
    print("README live block updated")

if __name__ == "__main__":
    main()
