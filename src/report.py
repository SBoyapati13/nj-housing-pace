"""Rewrite the LIVE block in README.md from out/summary.json, data/runs.jsonl and data/history/."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- LIVE:START -->", "<!-- LIVE:END -->"
MONTHS = "January February March April May June July August September October November December".split()
LABELS = {"well_below": "Under half its 2021–25 rate", "below": "Below its 2021–25 rate (0.5–0.8×)",
          "about_same": "About its 2021–25 rate (0.8–1.25×)", "above": "Above its 2021–25 rate (1.25–2×)",
          "well_above": "At least twice its 2021–25 rate", "disagree": "The two permit sources disagree",
          "too_few": "Too few homes to compare", "reporting_gap": "Reporting gap: not enough reports",
          "exempt": "No new obligation", "no_data": "No permit data"}
pct = lambda v: "–" if v is None else f"{v:.0%}"

def month(v):
    y, m = map(int, v.split("-")); return f"{MONTHS[m - 1]} {y}"

def changes(s):
    """Towns whose map class changed since the previous snapshot of the current method (other methods aren't comparable)."""
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
    cur = [r for r in runs if r.get("method") == s["method"]]
    hist = "\n".join(f"| {r['vintage']} | {r['dca_vintage']} | {r['run_utc'][:10]} | {pct(r['ratio_obl_dca'])} | {pct(r['ratio_obl_census'])} | "
                     f"{pct(r['cov_any'])} | {r['gap_large_n']} |" for r in cur[-12:])
    h = s["health"]
    icon = {"ok": "OK", "warn": "WARN", "stop": "STOP", "manual": "MANUAL"}
    health_rows = "\n".join(f"| {c['check'].replace('_', ' ')} | {icon[c['status']]} | {c['detail']} |" for c in h["checks"])
    banner = ("" if h["can_answer"] else
              "> **This system cannot currently answer its question.** A STOP check failed (see System health). "
              "The figures below are the last valid run and should not be read as current.\n\n")
    cc = s["class_counts"]
    class_rows = "\n".join(f"| {LABELS[k]} | {cc.get(k, 0)} |" for k in LABELS if cc.get(k, 0))
    W = month(s["window_end"])
    colored = s["colored_one_source"] + s["colored_two_sources"]
    gl = s["gap_large"]
    gap_list = "; ".join(f"{g['name']} ({g['past_peak']:,}{'' if g['obligated'] else ', no obligation'})" for g in gl)
    top3 = ", ".join(s["gap_large_names"][:3])
    block = f"""{START}
## Live status

*Rewritten automatically whenever either permit source publishes. Census data through {month(s['vintage'])}; state data through {month(s['dca_vintage'])}. Every update is logged in `data/runs.jsonl`.*

**Interactive map:** https://sboyapati13.github.io/nj-housing-pace/ (search any town to see both sources side by side).

{banner}**All homes permitted, July 2025 – {W}, against each town's own 2021–25 rate.**

- Towns with a Fourth Round obligation permitted **{pct(s['ratio_obl_dca'])}** of their 2021–25 rate on state data and **{pct(s['ratio_obl_census'])}** on Census data.
- Towns with no new obligation: **{pct(s['ratio_non_dca'])}** (state) and **{pct(s['ratio_non_census'])}** (Census).
- **Coverage:** towns holding {pct(s['cov_any'])} of the obligation can be compared on at least one source ({pct(s['cov_dca'])} state, {pct(s['cov_census'])} Census). {s['gap_large_n']} large past producers can't be compared on either source, including {top3}.

These are all homes permitted, not affordable homes: neither source tags affordable units. Implementing ordinances were due in {month(s['ordinances_due'])}, so most projects under the new zoning had not reached the permit stage in this window.

| | State Construction Reporter | Census Building Permits Survey |
|---|---|---|
| Period | July 2025 – {W}, shared window ({s['window_months']} months) | same |
| Obligated towns comparable (share of obligation) | {s['towns_obl_dca']} ({pct(s['cov_dca'])}) | {s['towns_obl_census']} ({pct(s['cov_census'])}) |
| All homes permitted in those towns | {s['units_obl_dca']:,.0f} | {s['units_obl_census']:,.0f} |
| At their 2021–25 rate it would be | {s['expected_obl_dca']:,.0f} | {s['expected_obl_census']:,.0f} |
| **Ratio, obligated towns** | **{pct(s['ratio_obl_dca'])}** | **{pct(s['ratio_obl_census'])}** |
| Ratio, towns with no obligation (towns compared) | {pct(s['ratio_non_dca'])} ({s['towns_non_dca']}) | {pct(s['ratio_non_census'])} ({s['towns_non_census']}) |

A source is comparable for a town when the town reported at least 75% of the window's months to it, has a 2021–25 baseline from it (4 of 5 fully reported years), and that baseline predicts at least {s['min_expected']} homes over the window. Each source over its own full period, all homes permitted in obligated towns: state data {s['dca_units_usable']:,} homes through {month(s['dca_vintage'])} ({s['dca_towns_usable']} towns with usable reports); Census {s['census_units_all']:,} homes through {month(s['vintage'])} (all {s['census_obligated_towns']} towns with a Census record; {pct(s['census_estimate_share'])} Census estimates).

**Map classes** (Figure 1).

| Class | Towns |
|---|---|
{class_rows}

Of the {colored} colored obligated towns, {s['colored_two_sources']} rest on both sources and {s['colored_one_source']} on one comparable source. Where both sources were comparable ({s['both_usable']} towns), they put the town in the same band {s['sources_agree']} times, one band apart {s['sources_one_band_apart']} times (shown in the band nearer "about the same") and two or more bands apart {s['sources_disagree']} times. {s['colored_census_only_no_reports']} are colored from Census alone with no homes actually reported. {s['towns_obl_neither']} obligated towns can't be compared on either source: {s['towns_too_few']} have too few homes to compare and {s['towns_reporting_gap']} have a reporting gap.

**Past large producers that can't be compared** (outlined on the map; most homes permitted in a fully reported year 2015–2024 in brackets): {gap_list}.

{s['state_zero_unconfirmed']} obligated towns have a state figure of 0 for the window that their Census reports don't confirm; those zeros are treated as not reported (§3).

**Final obligation numbers.** {s['final_numbers_found']} towns have a final or adopted number on file ({s['final_numbers_firm']} recorded as settled, court-ordered or accepted as calculated; see `evidence` in `data/raw/obligation_final.csv`). v4 uses DCA's calculation for every town (`obligation_source` = "dca"); the ratios above don't depend on obligations except to sort towns into the two groups.

**Reported completions** (certificates of occupancy, NJ DCA; through {month(s['co_vintage'])}):
- {s['co_reported_since_jul2025']:,} homes reported completed since July 2025 in the {s['co_towns_reporting_since_jul2025']} towns not marked missing in the state's files.
- Over 2015–2024, reported completions equalled **{s['co_completion_ratio_2015_2024']:.0%}** of homes permitted (state data, same agency and town codes), in the {s['co_towns_reporting_every_year_2015_2024']} towns that reported both every year. The gap mixes projects still under way, permits never built and incomplete reporting; the data can't separate them.
- Homes permitted in 2024–25 minus homes reported completed in 2024–25: **{s['co_pipeline_2024_2025']:,}** across {s['co_towns_in_pipeline_measure']} towns, a rough size of the recent pipeline.
- {s['co_marked_missing_last_full_year']} towns are marked missing in the state's completions file for the latest full year and are left out.

*Sensitivity, not a measure of progress:* if 20% of the homes permitted in obligated towns were affordable, they would equal {pct(s['sens_affordable_dca'])} (state) and {pct(s['sens_affordable_census'])} (Census) of the obligation pro-rated to date, each source over its own period ({pct(s['sens_affordable_final_dca'])} and {pct(s['sens_affordable_final_census'])} with final numbers where settled). This feeds no class, count or chart.

{changes(s)}

![Figure 2](out/county_live_progress.png)

*Figure 2. The same ratio by county, both sources over the same window, counting only obligated towns comparable on each source; the bottom row is towns with no new obligation, statewide.*

**System health.** Overall: **{icon[h['overall']]}**

| Check | Status | Detail |
|---|---|---|
{health_rows}

*Run history under the current method (last 12 updates; full log, including superseded methods, in `data/runs.jsonl`):*

| Census data through | State data through | Run date | Ratio, obligated (state) | Ratio, obligated (Census) | Coverage | Large-producer gaps |
|---|---|---|---|---|---|---|
{hist}
{END}"""
    readme = ROOT / "README.md"; text = readme.read_text()
    text = text[:text.index(START)] + block + text[text.index(END) + len(END):]
    readme.write_text(text)
    print("README live block updated")

if __name__ == "__main__":
    main()
