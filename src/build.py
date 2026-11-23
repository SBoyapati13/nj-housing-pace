"""NJ housing pace (method v4): are homes being permitted in the towns that carry New Jersey's
Fourth Round (2025-2035) affordable-housing obligations, compared with each town's own 2021-25 rate
and with towns that have no new obligation?

Permits come from two public sources, shown side by side:
  census  U.S. Census Bureau Building Permits Survey (revised annual files + latest year to date).
          Census fills in towns that don't report with estimates; the "months reported" field
          says how much of each figure is the town's own report.
  dca     NJ DCA Construction Reporter, housing units authorized by building permits (state data;
          marks towns with no report as "Missing Data" instead of estimating). Runs months behind.

The method (thresholds, classes, order of rules) was registered in CHANGELOG.md before any v4
results were computed. Every run whose inputs changed appends one line to data/runs.jsonl.
"""
import hashlib, json, warnings
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, HIST = ROOT / "data" / "raw", ROOT / "out", ROOT / "data" / "history"
LEDGER, HEALTH = ROOT / "data" / "runs.jsonl", ROOT / "data" / "health.json"
METHOD = "v4"
BASELINE_YEARS = [2021, 2022, 2023, 2024, 2025]
ROUND_START, WINDOW_YEARS = (2025, 7), 10           # July 1, 2025 - June 30, 2035 (P.L.2024, c.2)
ROUND_MONTHS = WINDOW_YEARS * 12
HIST_FIRST = 2015
SET_ASIDE = 0.20               # v4: used only by the labelled affordable sensitivity (*_aff_sens, sens_affordable_*)
USABLE_SHARE = 0.75            # a source is usable for a town that reported >= 75% of elapsed months to it
MIN_EXPECTED = 10              # a source is comparable only when the town's 2021-25 rate predicts >= 10 homes in the window
LARGE_PRODUCER = 200           # past peak (homes in a fully reported year 2015-24) that makes a reporting gap notable
PEAK_YEARS = range(2015, 2025)
BASELINE_MIN_YEARS, BEST_MIN_YEARS = 4, 5
RATIO_BANDS = [(0.5, "well_below"), (0.8, "below"), (1.25, "about_same"), (2.0, "above")]   # 2 or more: well_above
CLASS_ORDER = ["well_below", "below", "about_same", "above", "well_above"]
ORDINANCES_DUE = "2026-03"     # implementing ordinances due (P.L.2024, c.2)
FIRM_STATUSES = {"court order", "settlement", "accepted DCA number"}

# ---------------------------------------------------------------- Census BPS
BPS_COLS = ["survey","state","id6","county","census_place","fips_place","fips_mcd","pop",
            "csa","cbsa","footnote","central","zip","region","division","months","name",
            "u1_b","u1_u","u1_v","u2_b","u2_u","u2_v","u34_b","u34_u","u34_v","u5_b","u5_u","u5_v",
            "r1_b","r1_u","r1_v","r2_b","r2_u","r2_v","r34_b","r34_u","r34_v","r5_b","r5_u","r5_v"]

def bps(name):
    """Per NJ town: units (Census total, including estimates), reported units, months reported."""
    df = pd.read_csv(RAW / "bps" / name, skiprows=3, header=None, names=BPS_COLS, dtype=str)
    df = df[df.state.str.strip() == "34"].copy()
    num = lambda cols: sum(pd.to_numeric(df[c], errors="coerce").fillna(0) for c in cols)
    df["units"] = num(["u1_u", "u2_u", "u34_u", "u5_u"])
    df["reported"] = num(["r1_u", "r2_u", "r34_u", "r5_u"])
    df["m"] = pd.to_numeric(df.months, errors="coerce").fillna(0)
    df["fips"] = "34" + df.county.str.strip().str.zfill(3) + df.fips_mcd.str.strip().str.zfill(5)
    return df.groupby("fips").agg(units=("units", "sum"), reported=("reported", "sum"), m=("m", "max"))

def census_year(y, annual_years):
    """Full year y: the revised annual file if Census has published it, else the preliminary December file."""
    return bps(f"ne{y}a.txt") if y in annual_years else bps(f"ne{y % 100:02d}12y.txt")

# ---------------------------------------------------------------- NJ DCA permits
def _dca_rows(path, sheet):
    v = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str).iloc[6:]
    v = v[v[2].notna() & v[4].notna()].copy()
    v = v[v[2].str.strip().str.fullmatch(r"\d{1,4}(\.0)?")]
    v["code"] = v[2].str.replace(r"\.0$", "", regex=True).str.zfill(4)
    return v

def dca_ytd(name, strict=True):
    """Year-to-date units per DCA code from a monthly file. NaN where the state marks the total 'Missing Data',
    and (strict, v3.1) also where it marks the processing date 'Missing Data'."""
    v = _dca_rows(RAW / "dca_bp" / name, "house_ytd")
    missing = v[5].str.contains("missing", case=False, na=False)
    if strict:
        missing |= v[10].str.contains("missing", case=False, na=False)
    v["units"] = pd.to_numeric(v[5], errors="coerce").where(~missing)
    v["listed"] = ~v[5].str.contains("^see ", case=False, na=False)     # "See Princeton (1114)" etc.
    v = v[v.listed]
    return v.groupby("code").units.sum(min_count=1)

def dca_yearly(y):
    v = _dca_rows(RAW / "dca_bp" / f"house_yearly_{y}.xls", "house")
    v["units"] = pd.to_numeric(v[5], errors="coerce")
    return v.groupby("code").units.sum(min_count=1)

# ---------------------------------------------------------------- obligations
def load_obligations():
    df = pd.read_csv(RAW / "dca_final_summary.csv", dtype={"fips": str})
    df = df[["fips","dca_municode","municipality","county","present_need","qualified_urban_aid","households_2020","prospective_need"]]
    df["dca_municode"] = df.dca_municode.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(4)
    for c in ["present_need","qualified_urban_aid","households_2020","prospective_need"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.set_index("fips")

def ratio_class(r):
    """Band of the ratio to baseline (CHANGELOG v4)."""
    if r is None or pd.isna(r): return None
    for edge, key in RATIO_BANDS:
        if r < edge: return key
    return "well_above"

def combine(row, a="cw", b="dw"):
    """One class per town from two per-source results (rules in CHANGELOG v4, in order).
    Returns (class, one_band_apart)."""
    if not row.matched: return "no_data", False
    if not row.prospective_need > 0: return "exempt", False
    ca = row[f"{a}_class"] if row[f"{a}_comparable"] else None
    cb = row[f"{b}_class"] if row[f"{b}_comparable"] else None
    if ca and cb:
        ia, ib = CLASS_ORDER.index(ca), CLASS_ORDER.index(cb)
        if ia == ib: return ca, False
        if abs(ia - ib) == 1:
            mid = CLASS_ORDER.index("about_same")
            return (ca if abs(ia - mid) < abs(ib - mid) else cb), True
        return "disagree", False
    if ca or cb: return ca or cb, False
    if row[f"{a}_measurable"] or row[f"{b}_measurable"]: return "too_few", False
    return "reporting_gap", False

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

def main():
    bm = json.loads((RAW / "bps" / "manifest.json").read_text())
    pm = json.loads((RAW / "dca_bp" / "manifest.json").read_text())
    cm_ = json.loads((RAW / "co" / "manifest.json").read_text())
    vy, vm = bm["vintage"]["year"], bm["vintage"]["month"]          # Census
    dy, dmo = pm["vintage"]["year"], pm["vintage"]["month"]         # DCA permits
    annual = set(bm.get("annual_years", []))
    yearly = set(pm.get("yearly_years", []))
    df = load_obligations()
    idx, code = df.index, df.dca_municode
    on_fips = lambda s: s.reindex(idx)
    on_code = lambda s: pd.Series(s.reindex(code.values).values, index=idx)
    ry, rm = ROUND_START

    # ================= Census =================
    cy_full = {y: census_year(y, annual) for y in range(HIST_FIRST, vy)}
    df["in_census"] = idx.isin(cy_full[vy - 1].index)
    for y in range(HIST_FIRST, vy):
        df[f"c_units_{y}"] = on_fips(cy_full[y].units)
        df[f"c_reported_{y}"] = on_fips(cy_full[y].reported)
        df[f"c_months_{y}"] = on_fips(cy_full[y].m)
    jun, dec = on_fips(bps(f"ne{ry % 100:02d}{rm - 1:02d}y.txt")), on_fips(bps(f"ne{ry % 100:02d}12y.txt"))

    def census_period(ey, em):
        """Census homes permitted, reported homes and months reported, July 2025 through (ey, em)."""
        u = pd.Series(0.0, index=idx); rep = pd.Series(0.0, index=idx); mon = pd.Series(0.0, index=idx)
        for y in range(ry, ey + 1):
            whole = y < ey or (em == 12 and y in annual)
            if not whole:
                cur = on_fips(bps(f"ne{y % 100:02d}{em:02d}y.txt"))
                if y == ry:                      # still inside the first calendar year of the round
                    u += (cur.units - jun.units).fillna(0); rep += (cur.reported - jun.reported).fillna(0)
                    mon += (cur.m - jun.m).clip(0, em - rm + 1).fillna(0)
                else:
                    u += cur.units.fillna(0); rep += cur.reported.fillna(0); mon += cur.m.fillna(0)
                continue
            full = cy_full[y] if y in cy_full else census_year(y, annual)
            fu, fr, fm = on_fips(full.units), on_fips(full.reported), on_fips(full.m)
            if y == ry:   # revised 2025 total x share of the preliminary total that fell after June
                share = ((dec.units - jun.units) / dec.units.where(dec.units > 0)).clip(0, 1).fillna(0.5)
                u += (fu * share).fillna(0); rep += (fr * share).fillna(0)
                mon += (dec.m - jun.m).clip(0, 13 - rm).where(fm < 12, 13 - rm).fillna(0)
            else:
                u += fu.fillna(0); rep += fr.fillna(0); mon += fm.fillna(0)
        return u, rep, mon

    # ================= NJ DCA permits =================
    dca_full_years = range(HIST_FIRST, dy if dmo < 12 else dy + 1)
    d_dec_total = {y: on_code(dca_ytd(f"house_12_{y}.xls", strict=False)) for y in dca_full_years}
    df["in_dca"] = code.isin(dca_ytd(f"house_12_{max(dca_full_years)}.xls").index).values
    for y in dca_full_years:
        if y in yearly:      # revised yearly file; reported unless December marks the total missing (v3)
            val, rep_y = on_code(dca_yearly(y)), d_dec_total[y].notna()
        else:                # December year-to-date only: strict markers (v3.1, rule 2)
            val = on_code(dca_ytd(f"house_12_{y}.xls")); rep_y = val.notna()
        df[f"d_units_{y}"] = val.where(rep_y)
        df[f"d_reported_{y}"] = rep_y & df.in_dca
    for y in dca_full_years:   # v3.1 rule 3: unconfirmed state zeros for full years
        if f"c_months_{y}" not in df: continue
        uz = (df[f"d_units_{y}"] == 0) & ~((df[f"c_months_{y}"] >= USABLE_SHARE * 12) & (df[f"c_reported_{y}"] < 5))
        df.loc[uz, f"d_units_{y}"] = float("nan"); df.loc[uz, f"d_reported_{y}"] = False
    d_jun = on_code(dca_ytd("house_06_2025.xls"))

    def dca_period(ey, em):
        """State homes permitted and months counted as reported, July 2025 through (ey, em), year-to-date files."""
        u = pd.Series(0.0, index=idx); mon = pd.Series(0.0, index=idx)
        for y in range(ry, ey + 1):
            end_m = 12 if y < ey else em
            close = on_code(dca_ytd(f"house_{end_m:02d}_{y}.xls"))
            if y == ry: seg, ok, n = close - d_jun, close.notna() & d_jun.notna(), end_m - rm + 1
            else: seg, ok, n = close, close.notna(), end_m
            u += seg.where(ok, 0).fillna(0); mon += ok.astype(float) * n
        return u, mon

    df["matched"] = df.in_census | df.in_dca
    has_ob = df.prospective_need > 0
    months_between = lambda ey, em: 12 * (ey - ry) + em - rm + 1

    def unconfirmed_zero(state_units, c_rep, c_mon, n_months):
        """v3.1 rule 3: a state 0 counts only if the town reported >= 75% of the months to Census, totalling < 5 homes."""
        return (state_units == 0) & ~((c_mon >= USABLE_SHARE * n_months) & (c_rep < 5))

    def per_source(prefix, units, months, el, in_src):
        df[f"{prefix}_units"] = units.clip(lower=0).round(1).where(in_src)
        df[f"{prefix}_months"] = months.where(in_src)
        df[f"{prefix}_target"] = df.prospective_need * el / ROUND_MONTHS
        # v4: the old pace, kept only as a labelled sensitivity (no class, count or chart reads it)
        df[f"{prefix}_aff_sens"] = (df[f"{prefix}_units"] * SET_ASIDE / df[f"{prefix}_target"].where(df[f"{prefix}_target"] > 0)).round(4)
        df[f"{prefix}_usable"] = (df[f"{prefix}_months"] >= USABLE_SHARE * el).fillna(False)

    # each source over its own full period (statewide table, town detail)
    c_units, c_rep, c_mon = census_period(vy, vm)
    d_units, d_mon = dca_period(dy, dmo)
    c_elapsed, d_elapsed = months_between(vy, vm), months_between(dy, dmo)
    df["c_vintage"], df["c_months_elapsed"] = f"{vy}-{vm:02d}", c_elapsed
    df["d_vintage"], df["d_months_elapsed"] = f"{dy}-{dmo:02d}", d_elapsed
    df["c_negative_clipped"] = (c_units < 0) & df.in_census
    df["d_negative_clipped"] = (d_units < 0) & df.in_dca
    per_source("c", c_units, c_mon, c_elapsed, df.in_census)
    per_source("d", d_units, d_mon, d_elapsed, df.in_dca)
    df["c_reported_units"] = c_rep.clip(lower=0).round(1).where(df.in_census)
    # both sources over the common window (map class; v3.1 rule 1)
    wy, wm = min((vy, vm), (dy, dmo))
    w_el = months_between(wy, wm)
    cw_units, cw_rep, cw_mon = (c_units, c_rep, c_mon) if (wy, wm) == (vy, vm) else census_period(wy, wm)
    dw_units, dw_mon = (d_units, d_mon) if (wy, wm) == (dy, dmo) else dca_period(wy, wm)
    df["w_end"], df["w_months_elapsed"] = f"{wy}-{wm:02d}", w_el
    per_source("cw", cw_units, cw_mon, w_el, df.in_census)
    per_source("dw", dw_units, dw_mon, w_el, df.in_dca)
    df["cw_reported_units"] = cw_rep.clip(lower=0).round(1).where(df.in_census)
    df["dw_zero_unconfirmed"] = unconfirmed_zero(df.dw_units, cw_rep, cw_mon, w_el) & df.dw_usable
    df.loc[df.dw_zero_unconfirmed, "dw_usable"] = False
    # same rule for the state's own full period, checked against Census over that same period
    cd_rep, cd_mon = (cw_rep, cw_mon) if (dy, dmo) == (wy, wm) else census_period(dy, dmo)[1:]
    df["d_zero_unconfirmed"] = unconfirmed_zero(df.d_units, cd_rep, cd_mon, d_elapsed) & df.d_usable
    df.loc[df.d_zero_unconfirmed, "d_usable"] = False

    # ================= 2021-25 baseline, per source (v4: read before the class step) =================
    df["annual_target"] = df.prospective_need / WINDOW_YEARS
    yrs_c = [y for y in BASELINE_YEARS if f"c_units_{y}" in df]
    rep_c = pd.concat([df[f"c_months_{y}"] >= 12 for y in yrs_c], axis=1)
    val_c = pd.concat([df[f"c_units_{y}"] for y in yrs_c], axis=1)
    yrs_d = [y for y in BASELINE_YEARS if f"d_units_{y}" in df]
    rep_d = pd.concat([df[f"d_reported_{y}"] for y in yrs_d], axis=1)
    val_d = pd.concat([df[f"d_units_{y}"] for y in yrs_d], axis=1)
    for s, rep, val in (("c", rep_c, val_c), ("d", rep_d, val_d)):
        n = rep.sum(axis=1)
        df[f"{s}_base_years"] = n
        df[f"{s}_base_avg"] = val.where(rep.values).mean(axis=1).where(n >= BASELINE_MIN_YEARS).round(1)
        df[f"{s}_base_usable"] = df[f"{s}_base_avg"].notna()

    # ================= v4: ratio to the town's own 2021-25 rate, over the shared window =================
    for w, s in (("cw", "c"), ("dw", "d")):
        df[f"{w}_expected"] = (df[f"{s}_base_avg"] * w_el / 12).round(2)
        df[f"{w}_ratio"] = (df[f"{w}_units"] / df[f"{w}_expected"].where(df[f"{w}_expected"] > 0)).round(4)
        df[f"{w}_measurable"] = (df[f"{w}_usable"] & df[f"{s}_base_usable"]).astype(bool)
        df[f"{w}_comparable"] = (df[f"{w}_measurable"] & (df[f"{w}_expected"] >= MIN_EXPECTED)).fillna(False).astype(bool)
        df[f"{w}_class"] = df[f"{w}_ratio"].map(ratio_class).where(df[f"{w}_comparable"])
        df[f"{w}_months_missing"] = (w_el - df[f"{w}_months"]).where(df[f"{w}_months"].notna())
    res = [combine(r) for _, r in df.iterrows()]
    df["class_live"] = [c for c, _ in res]
    df["one_band_apart"] = [o for _, o in res]
    df["live_sources"] = df.cw_comparable.astype(int) + df.dw_comparable.astype(int)

    # ================= best year since 2015, per source (v4: a descriptive figure only) =================
    for s, years, reported in (("c", range(HIST_FIRST, vy), lambda y: df[f"c_months_{y}"] >= 12),
                               ("d", dca_full_years, lambda y: df[f"d_reported_{y}"])):
        rep = pd.concat([reported(y) for y in years], axis=1)
        val = pd.concat([df[f"{s}_units_{y}"] for y in years], axis=1)
        n = rep.sum(axis=1)
        df[f"{s}_best_year"] = val.where(rep.values).max(axis=1).where(n >= BEST_MIN_YEARS)

    # ================= v4: past large producers with no comparable source =================
    peaks = [df[f"c_units_{y}"].where(df[f"c_months_{y}"] >= 12) for y in PEAK_YEARS if f"c_units_{y}" in df]
    peaks += [df[f"d_units_{y}"].where(df[f"d_reported_{y}"]) for y in PEAK_YEARS if f"d_units_{y}" in df]
    df["past_peak"] = pd.concat(peaks, axis=1).max(axis=1)
    df["gap_large_producer"] = (df.past_peak >= LARGE_PRODUCER) & ~df.cw_comparable & ~df.dw_comparable & df.matched
    # obligations: DCA's calculation for every town in v4; final numbers are a later, separately registered change
    df["obligation_source"] = "dca"
    df["obligation_used"] = df.prospective_need

    # ================= final / adopted obligations (sensitivity) =================
    fin = pd.read_csv(RAW / "obligation_final.csv", dtype={"fips": str}).set_index("fips")
    assert fin.index.str.fullmatch(r"34\d{8}").all() and fin.index.isin(idx).all(), "obligation_final.csv: malformed or unknown fips"
    df["final_prospective_need"] = fin.final_prospective_need.reindex(idx)
    df["final_status"] = fin.status.reindex(idx)
    df["final_document"] = fin.document.reindex(idx)
    df["final_evidence"] = fin.evidence.reindex(idx)
    df["final_source"] = fin.source_url.reindex(idx)
    firm = df.final_status.isin(FIRM_STATUSES) & df.final_prospective_need.notna()
    df["obligation_sensitivity"] = df.prospective_need.where(~firm, df.final_prospective_need)

    # ================= reported completions (certificates of occupancy, NJ DCA) =================
    co_y, co_m = cm_["vintage"]["year"], cm_["vintage"]["month"]
    def co(name):
        v = _dca_rows(RAW / "co" / name, "certs_ytd")
        tot = pd.to_numeric(v[5], errors="coerce")
        v["units"] = tot
        v["missing"] = v[10].str.contains("missing", case=False, na=False) & (tot.fillna(0) == 0)
        v = v[~v[5].str.contains("^see ", case=False, na=False)]
        g = v.groupby("code").agg(units=("units", "sum"), missing=("missing", "all"))
        return on_code(g.units), on_code(g.missing).fillna(True).astype(bool)
    rtd_files = ["certs_06_2025.xls", "certs_12_2025.xls"] if co_y > 2025 or co_m == 12 else ["certs_06_2025.xls"]
    rtd_files += [f"certs_12_{y}.xls" for y in range(2026, co_y)]
    latest = f"certs_{co_m:02d}_{co_y}.xls"
    if latest not in rtd_files: rtd_files.append(latest)
    parts = {f: co(f) for f in rtd_files}
    jun_u = parts["certs_06_2025.xls"][0]
    if co_y == 2025:
        co_rtd = parts[latest][0] - jun_u
    else:
        co_rtd = parts["certs_12_2025.xls"][0] - jun_u
        for y in range(2026, co_y): co_rtd = co_rtd + parts[f"certs_12_{y}.xls"][0]
        co_rtd = co_rtd + parts[latest][0]
    co_ok = ~pd.concat([parts[f][1] for f in rtd_files], axis=1).any(axis=1)
    df["co_vintage"] = f"{co_y}-{co_m:02d}"
    df["co_reported_since_jul2025"] = co_rtd.clip(lower=0).where(co_ok & df.in_dca)
    ratio_years = [y for y in range(2015, 2025) if f"d_units_{y}" in df]
    co_years = {y: co(f"certs_12_{y}.xls") for y in range(2015, 2026)}
    every = pd.concat([~co_years[y][1] & df[f"d_reported_{y}"] for y in ratio_years], axis=1).all(axis=1)
    co_sum = sum(co_years[y][0].fillna(0) for y in ratio_years)
    pm_sum = sum(df[f"d_units_{y}"].fillna(0) for y in ratio_years)
    df["co_2015_2024"] = co_sum.where(every)
    df["d_permits_2015_2024"] = pm_sum.where(every)
    df["completion_ratio_2015_2024"] = (co_sum / pm_sum.where(pm_sum > 0)).where(every).round(4)
    two = [2024, 2025]
    two_ok = pd.concat([~co_years[y][1] & df[f"d_reported_{y}"] for y in two], axis=1).all(axis=1)
    df["pipeline_2024_2025"] = (sum(df[f"d_units_{y}"].fillna(0) for y in two) - sum(co_years[y][0].fillna(0) for y in two)).where(two_ok)
    last_full = co_y - 1 if co_m < 12 else co_y
    co_missing_last = co_years[last_full][1] & df.in_dca if last_full in co_years else pd.Series(False, index=idx)

    # ================= outputs =================
    OUT.mkdir(exist_ok=True); HIST.mkdir(parents=True, exist_ok=True)
    df.reset_index().to_csv(OUT / "town_pace.csv", index=False)

    ob = df[has_ob & df.matched]
    non = df[~has_ob & df.matched]
    def own_period(s, mask):
        """Homes permitted in obligated towns over the source's own full period (sensitivity and totals only)."""
        t = ob[mask]
        units = float(t[f"{s}_units"].sum())
        return units, round(units * SET_ASIDE / float(t[f"{s}_target"].sum()), 4) if len(t) else None, int(len(t))
    d_units_u, d_sens_u, d_n = own_period("d", ob.d_usable)
    c_units_all, c_sens_all, c_n_all = own_period("c", ob.in_census)
    c_units_u, c_sens_u, c_n_u = own_period("c", ob.c_usable)
    c_est_share = 1 - float(ob.c_reported_units.sum()) / float(ob.c_units.sum())
    sens = lambda s, mask: round(float(ob[mask][f"{s}_units"].sum()) * SET_ASIDE /
                                 float((ob[mask].obligation_sensitivity * (c_elapsed if s == "c" else d_elapsed) / ROUND_MONTHS).sum()), 4)
    allm = df[df.matched]
    exempt_share = lambda s: round(float(allm[allm.prospective_need == 0][f"{s}_units"].sum()) / float(allm[f"{s}_units"].sum()), 4)
    counts = df[df.matched].class_live.value_counts().to_dict()
    ob_total = float(ob.prospective_need.sum())

    def group(t, w):
        """Sum of all homes permitted / sum of expected homes over the group's comparable towns on one source."""
        g = t[t[f"{w}_comparable"]]
        u, e = float(g[f"{w}_units"].sum()), float(g[f"{w}_expected"].sum())
        return round(u, 1), round(e, 1), (round(u / e, 4) if e > 0 else None), int(len(g))
    s = {"method": METHOD, "vintage": f"{vy}-{vm:02d}", "dca_vintage": f"{dy}-{dmo:02d}",
         "months_elapsed": c_elapsed, "dca_months_elapsed": d_elapsed,
         "towns": int(len(df)), "towns_matched": int(df.matched.sum()), "obligated_towns": int(has_ob.sum()),
         "obligation_total": int(df.prospective_need.sum()),
         "window_end": f"{wy}-{wm:02d}", "window_months": w_el, "ordinances_due": ORDINANCES_DUE,
         "min_expected": MIN_EXPECTED, "large_producer": LARGE_PRODUCER}
    # headline: ratio to each town's own 2021-25 rate, obligated vs no new obligation, per source
    for gname, t in (("obl", ob), ("non", non)):
        for w, src in (("dw", "dca"), ("cw", "census")):
            u, e, r, n = group(t, w)
            s.update({f"units_{gname}_{src}": u, f"expected_{gname}_{src}": e, f"ratio_{gname}_{src}": r, f"towns_{gname}_{src}": n})
    s.update({
        "cov_dca": round(float(ob[ob.dw_comparable].prospective_need.sum()) / ob_total, 4),
        "cov_census": round(float(ob[ob.cw_comparable].prospective_need.sum()) / ob_total, 4),
        "cov_any": round(float(ob[ob.cw_comparable | ob.dw_comparable].prospective_need.sum()) / ob_total, 4),
        "cov_both": round(float(ob[ob.cw_comparable & ob.dw_comparable].prospective_need.sum()) / ob_total, 4),
        "towns_obl_neither": int((~ob.cw_comparable & ~ob.dw_comparable).sum()),
        "class_counts": {k: int(v) for k, v in counts.items()},
        "towns_too_few": int((ob.class_live == "too_few").sum()),
        "towns_reporting_gap": int((ob.class_live == "reporting_gap").sum()),
        "both_usable": int((ob.cw_comparable & ob.dw_comparable).sum()),
        "sources_agree": int((ob.cw_comparable & ob.dw_comparable & (ob.cw_class == ob.dw_class)).sum()),
        "sources_one_band_apart": int(ob.one_band_apart.sum()),
        "sources_disagree": int((ob.class_live == "disagree").sum()),
        "colored_one_source": int((ob.class_live.isin(CLASS_ORDER) & (ob.live_sources == 1)).sum()),
        "colored_two_sources": int((ob.class_live.isin(CLASS_ORDER) & (ob.live_sources == 2)).sum()),
        "colored_census_only_no_reports": int((ob.class_live.isin(CLASS_ORDER) & (ob.live_sources == 1) & ob.cw_comparable & (ob.cw_reported_units < 1)).sum()),
    })
    gl = df[df.gap_large_producer].sort_values("past_peak", ascending=False)
    s.update({
        "gap_large_n": int(len(gl)), "gap_large_obligated": int((gl.prospective_need > 0).sum()),
        "gap_large_names": gl.municipality.tolist(),
        "gap_large": [{"name": r.municipality, "county": r.county, "past_peak": int(r.past_peak), "obligated": bool(r.prospective_need > 0)}
                      for r in gl.itertuples()],
        "negatives_clipped": int((df.c_negative_clipped | df.d_negative_clipped).sum()),
        "state_zero_unconfirmed": int((df.dw_zero_unconfirmed & has_ob).sum()),
        "state_zero_unconfirmed_towns": sorted(df[df.dw_zero_unconfirmed & has_ob].municipality.tolist()),
        # each source over its own full period: all homes permitted (obligated towns)
        "dca_units_usable": int(d_units_u), "dca_towns_usable": d_n,
        "dca_obligation_share_usable": round(float(ob[ob.d_usable].prospective_need.sum()) / ob_total, 4),
        "census_units_all": int(c_units_all), "census_obligated_towns": c_n_all, "census_estimate_share": round(c_est_share, 4),
        "census_units_usable": int(c_units_u), "census_towns_usable": c_n_u,
        "census_obligation_share_usable": round(float(ob[ob.c_usable].prospective_need.sum()) / ob_total, 4),
        "exempt_share_census": exempt_share("c"), "exempt_share_dca": exempt_share("d"),
        # labelled sensitivity only: homes permitted x 20% / obligation pro-rated to date (feeds no class, count or chart)
        "sens_affordable_dca": d_sens_u, "sens_affordable_census": c_sens_all, "sens_affordable_census_usable": c_sens_u,
        # baseline
        "base_census_avg_units": round(float(df.c_base_avg.sum()), 1), "base_census_towns": int(df.c_base_usable.sum()),
        "base_dca_avg_units": round(float(df.d_base_avg.sum()), 1), "base_dca_towns": int(df.d_base_usable.sum()),
        "base_census_obligated": int(ob.c_base_usable.sum()), "base_dca_obligated": int(ob.d_base_usable.sum()),
        # final numbers (sensitivity; obligations used are DCA's for every town in v4)
        "obligation_source": "dca",
        "final_numbers_found": int(df.final_prospective_need.notna().sum()), "final_numbers_firm": int(firm.sum()),
        "sens_affordable_final_dca": sens("d", ob.d_usable), "sens_affordable_final_census": sens("c", ob.in_census),
        # completions
        "co_vintage": f"{co_y}-{co_m:02d}", "co_months_since_round_start": 12 * (co_y - ry) + co_m - rm + 1,
        "co_reported_since_jul2025": int(df.co_reported_since_jul2025.sum()),
        "co_towns_reporting_since_jul2025": int(df.co_reported_since_jul2025.notna().sum()),
        "co_completion_ratio_2015_2024": round(float(df.co_2015_2024.sum()) / float(df.d_permits_2015_2024[df.co_2015_2024.notna()].sum()), 4),
        "co_towns_reporting_every_year_2015_2024": int(df.completion_ratio_2015_2024.notna().sum()),
        "co_pipeline_2024_2025": int(df.pipeline_2024_2025.sum()),
        "co_towns_in_pipeline_measure": int(df.pipeline_2024_2025.notna().sum()),
        "co_marked_missing_last_full_year": int(co_missing_last.sum()),
    })
    s["health"] = health(bm, pm, (vy, vm), (dy, dmo), (co_y, co_m), df, s)
    (OUT / "summary.json").write_text(json.dumps(s, indent=2))
    HEALTH.write_text(json.dumps(s["health"], indent=2) + "\n")

    # history: one snapshot per data vintage; a revision of the same vintage is added, never overwritten
    snap = HIST / f"town_pace_{METHOD}_c{vy}-{vm:02d}_d{dy}-{dmo:02d}.csv"
    body = df.reset_index().to_csv(index=False)
    k = 2
    while snap.exists() and snap.read_text() != body:
        snap = HIST / f"town_pace_{METHOD}_c{vy}-{vm:02d}_d{dy}-{dmo:02d}_r{k}.csv"; k += 1
    if not snap.exists(): snap.write_text(body)

    inputs = sorted([f["sha256"][:16] for m in (bm, pm, cm_) for f in m["files"].values()] +
                    [json.loads((RAW / "dca_pin.json").read_text())["sha256"][:16], sha(RAW / "obligation_final.csv")])
    runs = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()] if LEDGER.exists() else []
    last = ([r for r in runs if "inputs" in r] or [None])[-1]
    if not last or last.get("inputs") != inputs or last.get("method") != METHOD:
        with LEDGER.open("a") as f:
            f.write(json.dumps({"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "inputs": inputs,
                                **{k: v for k, v in s.items() if k != "health"}, "health_overall": s["health"]["overall"]}) + "\n")
        print("ledger: new entry")
    else:
        print("ledger: inputs unchanged, no entry")
    print(json.dumps({k: v for k, v in s.items() if k != "health"}, indent=1))

def health(bm, pm, cv, dv, cov, df, s):
    """Can this system still answer its question? Each check is ok / warn / stop / manual."""
    checks = []
    add = lambda name, status, detail: checks.append({"check": name, "status": status, "detail": detail})
    now = datetime.now(timezone.utc); months_old = lambda y, m: (now.year * 12 + now.month) - (y * 12 + m)
    vy, vm = cv
    if (vy, vm) > (2035, 6):
        add("round_window", "stop", "The Fourth Round ended June 30, 2035; results are now a retrospective. Switch to Fifth Round obligations.")
    else:
        add("round_window", "ok", f"Fourth Round active: month {s['months_elapsed']} of {ROUND_MONTHS} (Census), {s['dca_months_elapsed']} (state data).")
    lag = months_old(vy, vm)
    add("census_freshness", "ok" if lag <= 3 else ("warn" if lag <= 5 else "stop"), f"Latest Census data is {lag} months old (normal lag is 1–3).")
    dlag = months_old(*dv)
    add("state_permits_freshness", "ok" if dlag <= 11 else "warn", f"Latest state permit data (NJ DCA) is {dlag} months old (normal lag is 8–10).")
    latest = RAW / "bps" / f"ne{vy % 100:02d}{vm:02d}y.txt"
    lines = latest.read_text(errors="replace").splitlines() if latest.exists() else []
    ncol = len(lines[1].split(",")) if len(lines) > 1 else 0
    nj = sum(1 for l in lines if l.split(",")[1:2] == ["34"])
    add("census_format", "ok" if ncol == len(BPS_COLS) and nj >= 550 else "stop", f"{ncol} columns (expected {len(BPS_COLS)}), {nj} NJ places (expected 550+).")
    add("town_match", "ok" if s["towns_matched"] >= 560 else "stop", f"{s['towns_matched']} of {s['towns']} towns matched to at least one permit source.")
    cu, du = s["census_obligation_share_usable"], s["dca_obligation_share_usable"]
    add("reporting_coverage", "ok" if max(cu, du) >= 0.6 else "warn",
        f"Towns holding {du:.0%} of the obligation have usable state permit data since July 2025, and {cu:.0%} reported at least 75% of months to Census. "
        "Warns only when neither source covers 60%.")
    ca = s["cov_any"]
    add("comparison_coverage", "ok" if ca >= 0.6 else "warn",
        f"Obligated towns holding {ca:.0%} of the obligation can be compared with their 2021–25 rate on at least one source "
        f"({s['cov_dca']:.0%} state, {s['cov_census']:.0%} Census, {s['cov_both']:.0%} both). Warns under 60%.")
    add("source_agreement", "ok", f"Of {s['both_usable']} obligated towns comparable on both sources, {s['sources_agree']} fall in the same band, "
        f"{s['sources_one_band_apart']} are one band apart and {s['sources_disagree']} are two or more bands apart.")
    add("negative_values", "ok" if s["negatives_clipped"] == 0 else "warn", f"{s['negatives_clipped']} towns had negative homes permitted since July 2025 (clipped to 0).")
    up, local = bm.get("dca_upstream", {}), json.loads((RAW / "dca_pin.json").read_text())["size"]
    if up.get("size") and int(up["size"]) != local:
        add("obligation_source", "warn", "DCA's published obligation workbook has changed since it was pinned. Review before adopting.")
    else:
        add("obligation_source", "ok", "DCA obligation workbook unchanged upstream.")
    clag = months_old(*cov)
    add("completions_freshness", "ok" if clag <= 11 else "warn", f"Latest completions data (NJ DCA certificates of occupancy) is {clag} months old (normal lag is 8–10). Completions are a secondary layer.")
    add("proxy_validity", "manual", "Figures are all homes permitted; neither source tags affordable units. Reviewed by hand each month (data/review_log.md).")
    worst = "stop" if any(c["status"] == "stop" for c in checks) else ("warn" if any(c["status"] == "warn" for c in checks) else "ok")
    return {"overall": worst, "can_answer": worst != "stop", "checks": checks}

if __name__ == "__main__":
    main()
