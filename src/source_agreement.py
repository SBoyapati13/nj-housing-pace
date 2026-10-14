"""How far apart are New Jersey's two permit counts? (figures for the note 'Two Counts of the Same Permits')

Writes out/source_agreement.json and out/source_totals.csv from the raw files the pipeline already keeps:
  - statewide totals per year: Census total, Census reported (non-estimated), state total, state towns marked missing
  - single-year agreement among town-years fully reported to both sources
  - agreement after summing each town's fully reported years (towns with 5 or more)
  - state zeros contradicted by a full-year Census report of 20 or more homes
Run after src/build.py:  python3 src/source_agreement.py
"""
import json
from pathlib import Path
import pandas as pd
import build

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "out"

def main():
    ob = build.load_obligations()
    idx, code = ob.index, ob.dca_municode
    on_code = lambda s: pd.Series(s.reindex(code.values).values, index=idx)
    pm = json.loads((RAW / "dca_bp" / "manifest.json").read_text())
    bm = json.loads((RAW / "bps" / "manifest.json").read_text())
    yearly, annual = set(pm["yearly_years"]), set(bm["annual_years"])
    dy, dmo = pm["vintage"]["year"], pm["vintage"]["month"]
    years = range(build.HIST_FIRST, dy if dmo < 12 else dy + 1)
    totals, pairs, zeros = [], [], 0
    for y in years:
        c = build.census_year(y, annual)
        # missing = "Missing Data" on the December total; for a year with no revised yearly file yet,
        # also on the processing date (the pipeline's v3.1 rule)
        dec = build.dca_ytd(f"house_12_{y}.xls", strict=y not in yearly)
        d = build.dca_yearly(y) if y in yearly else dec
        published = build.dca_yearly(y) if y in yearly else build.dca_ytd(f"house_12_{y}.xls", strict=False)
        rows = pd.read_excel(RAW / "dca_bp" / f"house_12_{y}.xls", sheet_name="house_ytd", header=None, dtype=str).iloc[6:]
        rows = rows[rows[2].notna() & rows[4].notna()]
        totals.append({"year": y, "census_total": int(c.units.sum()), "census_reported": int(c.reported.sum()),
                       "census_estimated_share": round(1 - c.reported.sum() / c.units.sum(), 4),
                       "state_total": int(published.sum()), "state_preliminary": y not in yearly,
                       "state_towns_marked_missing": int(rows[5].str.contains("missing", case=False, na=False).sum())})
        cc, dd, dm = c.reindex(idx), on_code(d), on_code(dec)
        full = (cc.m >= 12) & dm.notna() & dd.notna()
        zeros += int((full & (dd == 0) & (cc.units >= 20)).sum())
        ok = full & (cc.units > 0) & (dd > 0) & ((cc.units >= 20) | (dd >= 20))
        pairs += [(y, f, float(cc.units[f]), float(dd[f])) for f in idx[ok]]
    p = pd.DataFrame(pairs, columns=["year", "fips", "census", "state"])
    hi, lo = p[["census", "state"]].max(axis=1), p[["census", "state"]].min(axis=1)
    gap = (p.state - p.census).abs() / hi
    q = p.groupby("fips").agg(census=("census", "sum"), state=("state", "sum"), n=("year", "count"))
    q = q[q.n >= 5]
    qhi, qlo = q[["census", "state"]].max(axis=1), q[["census", "state"]].min(axis=1)
    qgap = (q.state - q.census).abs() / qhi
    out = {
        "single_year": {"town_years": int(len(p)), "within_10pct": round(float((gap <= .10).mean()), 4),
                        "within_25pct": round(float((gap <= .25).mean()), 4), "more_than_2x": round(float((hi > 2 * lo).mean()), 4),
                        "median_state_over_census": round(float((p.state / p.census).median()), 3)},
        "summed_5plus_years": {"towns": int(len(q)), "within_10pct": round(float((qgap <= .10).mean()), 4),
                               "within_25pct": round(float((qgap <= .25).mean()), 4), "more_than_2x": round(float((qhi > 2 * qlo).mean()), 4)},
        "state_zero_vs_census_full_report_20plus": zeros,
        "definition": "Fully reported = 12 months reported to Census and the state total not marked 'Missing Data' in its December file (for a year with no revised yearly file yet, nor its processing date); "
                      "agreement rows also need both counts above 0 and at least 20 homes in one of them.",
    }
    pd.DataFrame(totals).to_csv(OUT / "source_totals.csv", index=False)
    (OUT / "source_agreement.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
