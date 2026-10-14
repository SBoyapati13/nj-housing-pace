"""NJ housing pace: do towns' building permits keep pace with their
Fourth Round (2025-2035) affordable-housing obligations?

Two views, both re-derived from public files in data/raw/:
  BASELINE (frozen, pre-registered): average yearly permits 2021-2025 vs. obligation.
  LIVE (updates with every Census release): permits since the round began (July 1, 2025)
       vs. the pro-rated obligation to date, trailing-12-month pace, and each town's
       best-year threshold (whether reaching the obligation would take more than the town's best year since 2015).
Every run whose inputs changed appends one line to data/runs.jsonl.
"""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, HIST = ROOT / "data" / "raw", ROOT / "out", ROOT / "data" / "history"
LEDGER = ROOT / "data" / "runs.jsonl"
BASELINE_YEARS = [2021, 2022, 2023, 2024, 2025]   # frozen
ROUND_START, WINDOW_YEARS = (2025, 7), 10          # July 1, 2025 - June 30, 2035 (P.L.2024, c.2)
ROUND_MONTHS = WINDOW_YEARS * 12
HIST_FIRST = 2015                                   # best-year reference period starts here
SET_ASIDE = 0.20                                    # inclusionary yardstick (upper bound)

BPS_COLS = ["survey","state","id6","county","census_place","fips_place","fips_mcd","pop",
            "csa","cbsa","footnote","central","zip","region","division","months","name",
            "u1_b","u1_u","u1_v","u2_b","u2_u","u2_v","u34_b","u34_u","u34_v","u5_b","u5_u","u5_v",
            "r1_b","r1_u","r1_v","r2_b","r2_u","r2_v","r34_b","r34_u","r34_v","r5_b","r5_u","r5_v"]

def bps(name):
    """Units authorized per NJ town in one Census place file (imputed totals)."""
    df = pd.read_csv(RAW / "bps" / name, skiprows=3, header=None, names=BPS_COLS, dtype=str)
    df = df[df.state.str.strip() == "34"].copy()
    units = sum(pd.to_numeric(df[c], errors="coerce").fillna(0) for c in ["u1_u","u2_u","u34_u","u5_u"])
    fips = "34" + df.county.str.strip().str.zfill(3) + df.fips_mcd.str.strip().str.zfill(5)
    return pd.Series(units.values, index=fips.values).groupby(level=0).sum()

def full_year(y): return bps(f"ne{y % 100:02d}12y.txt")
def ytd(y, m):    return bps(f"ne{y % 100:02d}{m:02d}y.txt")

def load_dca():
    """Obligations from the pinned extract of DCA's Final Summary sheet (see src/pin_dca.py)."""
    df = pd.read_csv(RAW / "dca_final_summary.csv", dtype={"fips": str})
    df = df[["fips","dca_municode","municipality","county","present_need","qualified_urban_aid","households_2020","prospective_need"]]
    df["dca_municode"] = df.dca_municode.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(4)
    for c in ["present_need","qualified_urban_aid","households_2020","prospective_need"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.set_index("fips")

def health(manifest, vy, vm, n_towns, n_matched, co_vintage=None, co_reporting=None):
    """Can this system still answer its question? Each check is ok / warn / stop."""
    checks = []
    def add(name, status, detail): checks.append({"check": name, "status": status, "detail": detail})
    end_y, end_m = 2035, 6
    if (vy, vm) > (end_y, end_m):
        add("round_window", "stop", "The Fourth Round ended June 30, 2035; results are now a retrospective. Switch to Fifth Round obligations.")
    else:
        add("round_window", "ok", f"Fourth Round active: month {12 * (vy - ROUND_START[0]) + vm - ROUND_START[1] + 1} of {ROUND_MONTHS}.")
    now = datetime.now(timezone.utc); lag = (now.year * 12 + now.month) - (vy * 12 + vm)
    add("census_freshness", "ok" if lag <= 3 else ("warn" if lag <= 5 else "stop"),
        f"Latest Census data is {lag} months old (normal lag is 1-3).")
    latest = RAW / "bps" / f"ne{vy % 100:02d}{vm:02d}y.txt"
    first = latest.read_text(errors="replace").splitlines()[1].split(",") if latest.exists() else []
    nj = sum(1 for l in latest.read_text(errors="replace").splitlines() if l.split(",")[1:2] == ["34"]) if latest.exists() else 0
    fmt_ok = len(first) == len(BPS_COLS) and nj >= 550
    add("census_format", "ok" if fmt_ok else "stop", f"{len(first)} columns (expected {len(BPS_COLS)}), {nj} NJ places (expected 550+).")
    add("town_match", "ok" if n_matched >= 560 else "stop", f"{n_matched} of {n_towns} towns matched between DCA and Census.")
    up, local = manifest.get("dca_upstream", {}), json.loads((RAW / "dca_pin.json").read_text())["size"]
    if "error" in up:
        add("obligation_source", "warn", f"Could not reach DCA workbook: {up['error']}")
    elif up.get("size") and int(up["size"]) != local:
        add("obligation_source", "warn", "DCA's published workbook has changed since it was pinned. Review before adopting.")
    else:
        add("obligation_source", "ok", "DCA workbook unchanged upstream.")
    if co_vintage:
        cy, cm = co_vintage
        now = datetime.now(timezone.utc); co_lag = (now.year * 12 + now.month) - (cy * 12 + cm)
        add("completions_freshness", "ok" if co_lag <= 10 else "warn",
            f"Latest completions data (NJ DCA certificates of occupancy) is {co_lag} months old; this source normally runs 8-10 months behind. Completions are a secondary layer, so this check never stops the system.")
        share = co_reporting / n_matched if n_matched else 0
        add("completions_reporting", "ok" if share >= 0.85 else "warn",
            f"{co_reporting} of {n_matched} towns filed usable completions reports for the latest full year ({share:.0%}). Missing reports, and zeros that look like missing reports, are left out of the completions figures.")
    add("proxy_validity", "manual", "Obligations are DCA-calculated (final numbers are tracked for the 15 largest only); permits are a proxy for affordable output. Reviewed by hand each month.")
    worst = "stop" if any(c["status"] == "stop" for c in checks) else ("warn" if any(c["status"] == "warn" for c in checks) else "ok")
    return {"overall": worst, "can_answer": worst != "stop", "checks": checks}

CO_DIR = RAW / "co"
FIRM_STATUSES = {"court order", "settlement", "accepted DCA number"}

def co_ytd(name):
    """Year-to-date housing units certified (certificates of occupancy) per DCA municode."""
    path = CO_DIR / name
    x = pd.ExcelFile(path)
    raw = pd.read_excel(path, sheet_name=x.sheet_names[0], header=None)
    r = raw.iloc[3:, 7:13].copy()
    r.columns = ["code", "name", "total", "onetwo", "multi", "mixed"]
    r = r[pd.to_numeric(r.code, errors="coerce").notna()].copy()
    r["code"] = r.code.astype(int).astype(str).str.zfill(4)
    r = r[r.code != "9999"]
    r["total"] = pd.to_numeric(r.total, errors="coerce").fillna(0)
    return r.groupby("code").total.sum()          # Princeton appears twice in 2017-21 files; merged

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

def main():
    manifest = json.loads((RAW / "bps" / "manifest.json").read_text())
    vy, vm = manifest["vintage"]["year"], manifest["vintage"]["month"]
    df = load_dca()

    # ---- baseline (frozen) ----
    for y in BASELINE_YEARS:
        df[f"units_{y}"] = full_year(y)
    base_cols = [f"units_{y}" for y in BASELINE_YEARS]
    df["matched"] = df[base_cols].notna().all(axis=1)
    df["avg_units_per_year"] = df[base_cols].mean(axis=1)
    df["annual_target"] = df.prospective_need / WINDOW_YEARS
    df["coverage"] = df.avg_units_per_year * SET_ASIDE / df.annual_target.where(df.annual_target > 0)
    df["years_to_meet"] = df.prospective_need / (df.avg_units_per_year * SET_ASIDE).where(df.avg_units_per_year > 0)

    # ---- live: round to date + trailing 12 months ----
    idx = df.index
    z = lambda ser: ser.reindex(idx).fillna(0)
    ry, rm = ROUND_START
    before = z(ytd(ry, rm - 1)) if rm > 1 else 0
    if vy == ry:
        rtd = z(ytd(vy, vm)) - before
    else:
        rtd = z(full_year(ry)) - before
        rtd = rtd + sum((z(full_year(y)) for y in range(ry + 1, vy)), 0) + z(ytd(vy, vm))
    months = 12 * (vy - ry) + vm - rm + 1
    ttm = z(ytd(vy, vm))
    if vm < 12:
        ttm = ttm + z(full_year(vy - 1)) - z(ytd(vy - 1, vm))
    df["live_vintage"] = f"{vy}-{vm:02d}"
    df["live_months_elapsed"] = months
    df["live_units_round_to_date"] = rtd.where(df.matched)
    df["live_target_to_date"] = df.prospective_need * months / ROUND_MONTHS
    df["live_progress"] = df.live_units_round_to_date * SET_ASIDE / df.live_target_to_date.where(df.live_target_to_date > 0)
    df["live_units_ttm"] = ttm.where(df.matched)
    df["live_coverage_ttm"] = df.live_units_ttm * SET_ASIDE / df.annual_target.where(df.annual_target > 0)

    # ---- best-year threshold ----
    # Two thresholds. "inclusionary" = future homes carry a 20% set-aside (the yardstick above).
    # "any_route" = every future home permitted is affordable (e.g. 100%-affordable projects);
    # if even that cannot finish at the town's best year since 2015, no route remains at historical pace.
    best = pd.concat([z(full_year(y)) for y in range(HIST_FIRST, vy)], axis=1).max(axis=1)
    m_rem = max(ROUND_MONTHS - months, 0)
    done_aff = df.live_units_round_to_date * SET_ASIDE                       # affordable credited so far (at 20%)
    df["best_year_units_since_2015"] = best.where(df.matched)
    H, r = best / 12, df.live_units_ttm / 12
    def no_return(need, rate_share):
        out_s, out_d = {}, {}
        for i in idx:
            if not df.at[i, "matched"] or not df.at[i, "prospective_need"] > 0:
                out_s[i], out_d[i] = "n/a", None; continue
            A = need[i]; h = H[i] * rate_share; rr = r[i] * rate_share       # affordable-units per month
            if A <= 0: st, t = "met", None
            elif A - h * m_rem > 0: st, t = "past", 0
            elif rr >= h: st, t = "open", None
            else:
                t = (h * m_rem - A) / (h - rr)
                st, t = ("open", None) if t >= m_rem else ("projected", t)
            out_s[i] = st
            if t is None: out_d[i] = None
            else:
                k = vy * 12 + (vm - 1) + int(-(-t // 1)); out_d[i] = f"{k // 12}-{k % 12 + 1:02d}"
        return pd.Series(out_s), pd.Series(out_d)
    need_aff = (df.prospective_need - done_aff).clip(lower=0)                # affordable units still owed
    df["inclusionary_route_status"], df["inclusionary_route_closes"] = no_return(need_aff, SET_ASIDE)
    df["any_route_status"], df["any_route_closes"] = no_return(need_aff, 1.0)
    df["required_units_per_year_at_20pct"] = need_aff / SET_ASIDE / (m_rem / 12) if m_rem else float("nan")

    # ---- final / adopted obligations (sourced; DCA number stays primary) ----
    fin = pd.read_csv(RAW / "obligation_final.csv", dtype={"fips": str}).set_index("fips")
    df["final_prospective_need"] = fin.final_prospective_need.reindex(idx)
    df["final_status"] = fin.status.reindex(idx)
    df["final_source"] = fin.source_url.reindex(idx)
    firm = df.final_status.isin(FIRM_STATUSES) & df.final_prospective_need.notna()
    df["obligation_sensitivity"] = df.prospective_need.where(~firm, df.final_prospective_need)
    sens_target = df.obligation_sensitivity * months / ROUND_MONTHS
    df["live_progress_sensitivity"] = df.live_units_round_to_date * SET_ASIDE / sens_target.where(sens_target > 0)

    # ---- reported completions (certificates of occupancy, NJ DCA) ----
    com = json.loads((CO_DIR / "manifest.json").read_text())
    cy, cm = com["vintage"]["year"], com["vintage"]["month"]
    code = df.dca_municode
    def by_town(series):
        return pd.Series(series.reindex(code.values).values, index=idx)
    def present(name):
        return pd.Series(code.isin(co_ytd(name).index).values, index=idx)
    SUSPECT_MIN_PERMITS = 100   # zero completions despite >=100 homes permitted in the prior two years
    def reported_year(y):
        """Town listed in year y's December report and not a likely missing report recorded as zero."""
        listed = present(f"certs_12_{y}.xls")
        cos = by_town(co_ytd(f"certs_12_{y}.xls")).fillna(0)
        recent_permits = sum((z(full_year(k)) for k in (y - 1, y - 2) if k >= HIST_FIRST), 0)   # permit files start in 2015
        return listed & ~((cos == 0) & (recent_permits >= SUSPECT_MIN_PERMITS))
    co_files = [f"certs_12_{y}.xls" for y in range(2015, cy)] + ["certs_06_2025.xls", f"certs_{cm:02d}_{cy}.xls"]
    co_files = list(dict.fromkeys(co_files))
    # since July 2025
    if cy == 2025:
        rtd_files = ["certs_06_2025.xls", f"certs_{cm:02d}_{cy}.xls"]
        co_rtd = by_town(co_ytd(f"certs_{cm:02d}_{cy}.xls")) - by_town(co_ytd("certs_06_2025.xls"))
    else:
        rtd_files = ["certs_06_2025.xls", "certs_12_2025.xls"] + [f"certs_12_{y}.xls" for y in range(2026, cy)] + [f"certs_{cm:02d}_{cy}.xls"]
        co_rtd = by_town(co_ytd("certs_12_2025.xls")) - by_town(co_ytd("certs_06_2025.xls"))
        for y in range(2026, cy):
            co_rtd = co_rtd + by_town(co_ytd(f"certs_12_{y}.xls"))
        co_rtd = co_rtd + by_town(co_ytd(f"certs_{cm:02d}_{cy}.xls"))
    # A town absent from the latest partial-year file usually just hasn't filed yet that year,
    # so presence is required only in the complete files (June 2025 and each December).
    need = [f for f in dict.fromkeys(rtd_files) if not (f == f"certs_{cm:02d}_{cy}.xls" and cm < 12)]
    rtd_ok = pd.concat([present(f) for f in need], axis=1).all(axis=1)
    rtd_ok &= ~((co_rtd.fillna(0) == 0) & ((z(full_year(2024)) + z(full_year(2025))) >= SUSPECT_MIN_PERMITS))
    df["co_vintage"] = f"{cy}-{cm:02d}"
    df["co_reported_since_jul2025"] = co_rtd.where(rtd_ok & df.matched)
    # completion ratio 2015-2024 (towns reporting every year)
    ratio_years = range(2015, 2025)
    full_rep = pd.concat([reported_year(y) for y in ratio_years], axis=1).all(axis=1)
    co_sum = sum(by_town(co_ytd(f"certs_12_{y}.xls")).fillna(0) for y in ratio_years)
    pm_sum = sum(z(full_year(y)) for y in ratio_years)
    df["co_2015_2024"] = co_sum.where(full_rep & df.matched)
    df["permits_2015_2024"] = pm_sum.where(df.matched)
    df["completion_ratio_2015_2024"] = (co_sum / pm_sum.where(pm_sum > 0)).where(full_rep & df.matched)
    # two-year pipeline: permits 2024-25 minus reported completions 2024-25
    two = ["certs_12_2024.xls", "certs_12_2025.xls"]
    two_rep = reported_year(2024) & reported_year(2025)
    co_two = sum(by_town(co_ytd(f)).fillna(0) for f in two)
    pm_two = z(full_year(2024)) + z(full_year(2025))
    df["pipeline_2024_2025"] = (pm_two - co_two).where(two_rep & df.matched)
    last_full = cy - 1 if cm < 12 else cy
    co_last_full = reported_year(last_full)
    co_suspect_last_full = present(f"certs_12_{last_full}.xls") & ~co_last_full

    OUT.mkdir(exist_ok=True); HIST.mkdir(parents=True, exist_ok=True)
    df.reset_index().to_csv(OUT / "town_pace.csv", index=False)
    df.reset_index().to_csv(HIST / f"town_pace_{vy}-{vm:02d}.csv", index=False)

    m = df[df.matched]; has = m[m.prospective_need > 0]
    s = {
        "method": "v2.2", "vintage": f"{vy}-{vm:02d}", "months_elapsed": months,
        "towns": int(len(df)), "towns_matched": int(df.matched.sum()),
        "obligation_total": int(df.prospective_need.sum()),
        "baseline_avg_units_per_year": round(float(m.avg_units_per_year.sum()), 1),
        "baseline_towns_below_half": int((has.coverage < 0.5).sum()),
        "baseline_obligation_share_below_half": round(float(has[has.coverage < 0.5].prospective_need.sum() / has.prospective_need.sum()), 4),
        "baseline_exempt_permit_share": round(float(m[m.prospective_need == 0].avg_units_per_year.sum() / m.avg_units_per_year.sum()), 4),
        "live_units_round_to_date": int(m.live_units_round_to_date.sum()),
        "live_implied_affordable_to_date": round(float(m.live_units_round_to_date.sum() * SET_ASIDE), 1),
        "live_target_to_date": round(float(df.live_target_to_date.sum()), 1),
        "live_progress_statewide": round(float(m.live_units_round_to_date.sum() * SET_ASIDE / df.live_target_to_date.sum()), 4),
        "live_obligated_towns": int(len(has)),
        "live_towns_on_pace": int((has.live_progress >= 1).sum()),
        "live_towns_below_half": int((has.live_progress < 0.5).sum()),
        "live_units_ttm": int(m.live_units_ttm.sum()),
        "inclusionary_route_closed": int((has.inclusionary_route_status == "past").sum()),
        "inclusionary_route_closed_obligation": int(has[has.inclusionary_route_status == "past"].prospective_need.sum()),
        "inclusionary_route_closing_next_12m": int(((has.inclusionary_route_status == "projected") & (has.inclusionary_route_closes <= f"{vy + 1}-{vm:02d}")).sum()),
        "any_route_closed": int((has.any_route_status == "past").sum()),
        "any_route_closed_obligation": int(has[has.any_route_status == "past"].prospective_need.sum()),
        "met_at_20pct": int((has.inclusionary_route_status == "met").sum()),
        "final_numbers_found": int(df.final_prospective_need.notna().sum()),
        "final_numbers_firm": int(firm.sum()),
        "live_progress_statewide_sensitivity": round(float(m.live_units_round_to_date.sum() * SET_ASIDE / (df.obligation_sensitivity.sum() * months / ROUND_MONTHS)), 4),
        "obligation_total_sensitivity": int(df.obligation_sensitivity.sum()),
        "co_vintage": f"{cy}-{cm:02d}",
        "co_months_since_round_start": 12 * (cy - 2025) + cm - 6,
        "co_reported_since_jul2025": int(df.co_reported_since_jul2025.sum()),
        "co_towns_reporting_since_jul2025": int(df.co_reported_since_jul2025.notna().sum()),
        "co_towns_reporting_last_full_year": int((co_last_full & df.matched).sum()),
        "co_completion_ratio_2015_2024": round(float(df.co_2015_2024.sum() / df.permits_2015_2024[df.co_2015_2024.notna()].sum()), 4),
        "co_towns_reporting_every_year_2015_2024": int(df.completion_ratio_2015_2024.notna().sum()),
        "co_pipeline_2024_2025": int(df.pipeline_2024_2025.sum()),
        "co_likely_unreported_last_full_year": int((co_suspect_last_full & df.matched).sum()),
        "co_towns_in_pipeline_measure": int(df.pipeline_2024_2025.notna().sum()),
        "live_exempt_share_round_to_date": round(float(m[m.prospective_need == 0].live_units_round_to_date.sum() / m.live_units_round_to_date.sum()), 4),
    }
    s["health"] = health(manifest, vy, vm, len(df), int(df.matched.sum()), (cy, cm), s["co_towns_reporting_last_full_year"])
    (OUT / "summary.json").write_text(json.dumps(s, indent=2))

    inputs = {f["sha256"][:16]: n for n, f in manifest["files"].items()}
    co_inputs = [f["sha256"][:16] for f in json.loads((CO_DIR / "manifest.json").read_text())["files"].values()]
    inputs_key = sorted(list(inputs) + co_inputs + [json.loads((RAW / "dca_pin.json").read_text())["sha256"][:16], sha(RAW / "obligation_final.csv")])
    runs = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()] if LEDGER.exists() else []
    runs = [r for r in runs if "inputs" in r]
    last = runs[-1] if runs else None
    if not last or last.get("inputs") != inputs_key or last.get("method") != s["method"]:
        entry = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "inputs": inputs_key, **s}
        with LEDGER.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        print("ledger: new entry")
    else:
        print("ledger: inputs unchanged, no entry")
    print(json.dumps(s, indent=2))

if __name__ == "__main__":
    main()
