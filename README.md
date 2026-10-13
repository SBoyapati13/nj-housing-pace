# Building Where the Obligation Isn't: Permit Pace and New Jersey's Fourth Round Affordable-Housing Obligations, 2021–2025

**Swapnil Boyapati** · October 2026 · *Unassembled public records*, project 1

---

## Abstract

New Jersey's 2024 Affordable Housing Law assigns 564 municipalities a combined 80,798 units of new ("prospective need") affordable housing for 2025–2035 [3, 4]. This project joins those obligations to U.S. Census Bureau building-permit records for every town [5] and asks whether recent construction is happening where the obligations are.

Statewide, recent building would nearly suffice. New Jersey permitted about 35,600 homes a year in 2021–2025; if every one carried a 20% affordable set-aside, that would yield about 7,100 affordable homes a year against the 8,080 needed. Geographically, though, building and obligation diverge sharply:

- **34%** of all permitted homes were in the 48 towns that owe no new affordable housing.
- Among the 514 towns that do, **290 are building at under half the required pace even under that generous assumption. Together they hold 63% of the statewide obligation.**

This is a living analysis. A pipeline checks the Census Bureau every week, pulls each new monthly release, and updates every town's progress since the round began on July 1, 2025. It also reports when, and whether, the question can still be answered (§7.2). The **Live status** section below, with its town map (Figure 1) and county chart (Figure 2), is rewritten automatically, and every update is logged. Every number can be rebuilt from public files with one command.

<!-- LIVE:START -->
## Live status

*Updated automatically from the Census release covering January–August 2026. Every update is logged in `data/runs.jsonl`.*

**Interactive map:** https://sboyapati13.github.io/nj-housing-pace/ (search any town, hover for its numbers, switch between Fourth Round to date and the 2021–25 baseline). Rebuilt by `src/web.py` and redeployed on every update.

| Fourth Round to date (July 2025 – Aug 2026, 14 of 120 months) | |
|---|---|
| Homes permitted statewide | 35,461 |
| Implied affordable at 20% | 7,092 |
| Pro-rated obligation to date | 9,426 |
| **Statewide progress** | **75%** |
| Obligated towns on pace (≥ 1.0) | 110 of 514 |
| Obligated towns below half pace | 329 of 514 |
| Share of permits in exempt towns | 36% |
| Homes permitted, trailing 12 months | 30,305 |

**Point of no return.** For each obligated town, could it still finish by June 2035 if it built at its best year since 2015?
- **Inclusionary route closed** (20% of new homes affordable): **240 towns**, holding 42,569 units of obligation. Another 12 close within 12 months if their current pace holds.
- **Every route closed** (even if *every* new home were affordable): **63 towns**, holding 9,960 units.
- Per-town status and dates are in `out/town_pace.csv` (`inclusionary_route_*`, `any_route_*`).

First live run: no earlier release to compare against yet.

![Figure 1](out/map_live_progress.png)

*Figure 1. Every New Jersey town, colored by Fourth Round progress to date. Dark red: towns that couldn't finish even by building at their best year since 2015 with a 20% set-aside. Outlined: towns that couldn't finish even if every new home were affordable. Hatched gray: urban-aid towns exempt from new obligations.*

![Figure 2](out/county_live_progress.png)

*Figure 2. The same measure aggregated by county.*

**System health.** Overall: **OK**

| Check | Status | Detail |
|---|---|---|
| round window | OK | Fourth Round active: month 14 of 120. |
| census freshness | OK | Latest Census data is 2 months old (normal lag is 1-3). |
| census format | OK | 41 columns (expected 41), 562 NJ places (expected 550+). |
| town match | OK | 562 of 564 towns matched between DCA and Census. |
| obligation source | OK | DCA workbook unchanged upstream. |
| proxy validity | MANUAL | Obligations are DCA-calculated, not adopted or court-approved; permits are a proxy for affordable output. Reviewed by hand each month. |

*Run history (last 12 updates; full log in `data/runs.jsonl`):*

| Census vintage | Run date | Method | Homes since round start | Statewide progress | Towns below half |
|---|---|---|---|---|---|
| 2026-08 | 2026-10-13 | v1 (superseded) | 51,655 | 77% | 319 |
| 2026-08 | 2026-10-13 | v2 | 35,461 | 75% | 329 |
<!-- LIVE:END -->

## 1. Background

### 1.1 The Mount Laurel doctrine

In 1975 the New Jersey Supreme Court held that a developing municipality must, through its zoning, "presumptively make realistically possible an appropriate variety and choice of housing," at least to the extent of its "fair share of the present and prospective regional need therefor" [1, 67 N.J. at 174]. The Court strengthened the doctrine in 1983 [2], and the Fair Housing Act of 1985 and the Council on Affordable Housing (COAH) were then built to carry out that duty. After the Supreme Court declared COAH inoperative in 2015 [4, p. 5], obligations were set town by town in the courts until the 2024 reform.

### 1.2 The 2024 Affordable Housing Law

P.L.2024, c.2, signed March 20, 2024, replaced that system. The Legislature declared that "the Council on Affordable Housing shall be abolished" [3]. It moved the calculation to a fixed statutory formula run by the Department of Community Affairs (DCA) and created an Affordable Housing Dispute Resolution Program to settle challenges [3, 4]. Three features of the formula matter for this analysis.

**Regional need comes from household growth.** The law states that household change, "if positive, shall be divided by 2.5 to estimate the number of low- and moderate-income homes needed" [3]. DCA's application of this produced 84,698 units of regional prospective need statewide [4, p. 10].

**Urban-aid municipalities are exempt.** In the law's words: "If a municipality is a qualified urban aid municipality, the municipality shall be exempt from responsibility for any fair share prospective need obligation for the upcoming 10-year round" [3]. DCA identified 47 such municipalities in 13 counties [4, p. 10].

**Obligations are capped.** A town may lower its number to avoid an obligation requiring "a realistic opportunity for more than 1,000 housing units," or one exceeding "20 percent of the total number of households" [3; 4, p. 18]. After the cap, the statewide total is 80,798 [6].

### 1.3 Where the process stands

Towns could accept DCA's number or adopt their own. By the February 2025 deadline, 282 towns had accepted DCA's figures and 158 had used their own calculations, 68 of which were challenged [7]. In January 2026, Fair Share Housing Center reported about 380 municipalities with compliant plans and about 40 without agreements, calling the result "nothing short of a sea change" [8].

The process has also been contested. A coalition led by Montvale sued to block the law; its mayor said the mandates "from Trenton go too far" [9]. Montvale's own dispute shows how much numbers can move: DCA assigned it 348 units, and the Dispute Resolution Program recommended 255, noting that "Prospective Need is not mandated to be perfect" [10].

### 1.4 The gap this project fills

Obligations come from DCA. Permits come from the Census Bureau. The two are published separately and use different town identifiers, so no public source puts each town's obligation next to how much that town actually builds. This project makes that join.

## 2. Data

| Source | What it contributes | Coverage |
|---|---|---|
| NJ DCA, *Fourth Round Calculation Workbook*, "Final Summary" sheet [6] | Present need, prospective need (capped), 2020 households, county-subdivision FIPS | 564 municipalities |
| NJ DCA, *Fair Share Housing Obligations for 2025–2035: Methodology and Background* [4] | Definitions and formula; source of quoted methodology | — |
| U.S. Census Bureau, cartographic boundary files, NJ county subdivisions, 2024 [12] | Town boundaries for the map (Figure 1), joined on the same 10-digit FIPS | 564 municipalities |
| U.S. Census Bureau, Building Permits Survey (BPS), place-level annual files [5] | Housing units authorized by permit, by structure type (1, 2, 3–4, 5+ units) | NJ permit-issuing places, full years 2015 onward plus the latest year-to-date release (refreshed automatically) |

On imputation, the Census Bureau states that its estimates "are based on received reports for places in the monthly survey and imputed activity for non-reporters and those not surveyed monthly" [11]. This project uses those imputed totals, which are the Bureau's headline series.

## 3. Methods

The method was written down before any results were computed.

1. **Obligation.** For each town: DCA prospective need after the 1,000-unit / 20% cap, covering 2025–2035. Annual target = obligation ÷ 10.
2. **Building pace.** For each town: average yearly housing units authorized in 2021–2025, all structure types, imputed totals.
3. **Yardstick.** New Jersey produces much of its affordable housing through inclusionary development, where a share of market-rate units is reserved as affordable. The law names "mandatory set-asides or density bonuses" among the tools towns may use [3]. A uniform 20% set-aside is assumed as a generous upper bound.
4. **Coverage ratio** = (building pace × 0.20) ÷ annual target. At 1.0 or above, a town's recent pace could meet its obligation if every unit came with a 20% set-aside.
5. **Join.** Census county code + minor civil division code → 10-digit county-subdivision FIPS, matched to DCA's FIPS field. 562 of 564 towns matched. Netcong and Tavistock are not in the Census permit universe.
6. **Live extension** (specified October 13, 2026, before any month-to-month comparison was run). Each new Census release adds two metrics per town:
   - **Progress to date** = (homes permitted since July 1, 2025 × 0.20) ÷ (obligation × months elapsed ÷ 120). The law states the round begins "with the fourth round on July 1, 2025" [3]. A first version mistakenly started the clock in January 2025; the correction is recorded in `CHANGELOG.md` and in the run log.
   - **Trailing-12-month coverage** = (homes permitted in the last 12 months × 0.20) ÷ (obligation ÷ 10).

   - **Point of no return**, at two thresholds. For each town: affordable units still owed = obligation − (homes permitted since July 2025 × 0.20). Its **inclusionary route** has closed when, even building every remaining year at its best year since 2015 with 20% affordable, it can't finish by June 30, 2035. Its **every route** has closed when it couldn't finish even if *every* new home were affordable. If a town is still open, the system projects the month the route closes if its trailing-12-month pace continues. A town's best year since 2015 is a historical yardstick, not a hard limit, since rezoning can push building beyond it.

   The 2021–2025 baseline in §4 stays frozen, so the original finding can always be compared with what happens next.
7. **Verification.** Town totals were hand-summed from raw Census rows (for example, Jersey City 2023 = 2,339 units; Wall Township 2024 = 387). The statewide obligation was checked against the workbook's TOTAL row (80,798).

## 4. Baseline results (frozen, 2021–2025)

### 4.1 Statewide totals nearly balance

| | Value |
|---|---|
| Statewide prospective need, 2025–2035 | 80,798 (8,080 / yr) |
| Homes permitted per year, 2021–2025 average | 35,625 |
| Implied affordable per year at 20% | 7,125 (88% of target) |
| Homes permitted Jan–Aug 2026 | 19,634 |

### 4.2 But building and obligation are in different places

- **Exempt towns build a third of the state's housing.** The 48 matched towns with zero prospective need account for **34%** of homes permitted in 2021–2025. Forty-seven of the 48 are Qualified Urban Aid municipalities. The largest builders among them are Jersey City (2,802 / yr), Newark (1,635), Lakewood (1,367), West New York (658) and Weehawken (641).
- **Most obligated towns fall well short.** Of the 514 towns with an obligation, 133 have coverage of 1.0 or more, 91 are between 0.5 and 1.0, and **290 are below 0.5**. Eighteen permitted no housing at all. The below-0.5 group holds **51,168 units, or 63%** of the statewide obligation. Median coverage is **0.40**.
- **County pattern.** Obligated towns fall short as a group in **17 of 21 counties** (Figure 3). Sussex (0.11), Hudson outside its urban-aid towns (0.14), Passaic (0.15) and Warren (0.31) are lowest. Only Cape May, Atlantic, Burlington and Ocean exceed 1.0.

![Figure 3](out/county_coverage.png)

*Figure 3. Baseline (frozen) coverage ratio by county, towns with a Fourth Round obligation only, 2021–2025. Sources: [5, 6].*

### 4.3 The largest obligations

| Municipality | County | Obligation (2025–35) | Permits / yr (2021–25) | Coverage | Years to meet at 20% |
|---|---|---|---|---|---|
| Paramus | Bergen | 1,000 | 62.4 | 0.12 | 80 |
| Secaucus | Hudson | 1,000 | 7.0 | 0.01 | 714 |
| Wayne | Passaic | 1,000 | 15.4 | 0.03 | 325 |
| Roxbury | Morris | 989 | 28.4 | 0.06 | 174 |
| South Brunswick | Middlesex | 959 | 161.6 | 0.34 | 30 |
| Jackson | Ocean | 954 | 50.0 | 0.10 | 95 |
| Linden | Union | 787 | 134.8 | 0.34 | 29 |
| Monroe (Middlesex) | Middlesex | 751 | 305.4 | 0.81 | 12 |
| Wall | Monmouth | 744 | 374.2 | 1.01 | 10 |
| Edison | Middlesex | 727 | 154.4 | 0.42 | 24 |

*DCA calculated values; adopted or court-approved numbers may be lower (see §1.3).*

## 5. Discussion

The statute deliberately puts prospective need where land, income and commercial growth are, and exempts dense, lower-income municipalities [3, 4]. The finding is not that the formula is wrong. It is that **the towns the formula selects have, so far, built at a fraction of the rate their obligations assume.** The places that are building, chiefly the urban-aid cities, carry no new obligation by design.

Two readings are possible, and the data can't separate them yet:

- **The zoning reading.** The obligation itself is the remedy. Mount Laurel compliance plans rezone sites, so pace should rise in obligated towns as plans take effect in 2026 and later.
- **The capacity reading.** Obligated suburbs build little because of land, infrastructure or demand constraints. Some of those are exactly what towns argued before the Dispute Resolution Program [10]. If so, rezoning alone won't close the gap.

Monthly Census releases make this testable: the coverage ratio can be re-run each month to see which reading the 2026–2028 data supports.

## 6. Limitations

- **Upper bound.** Not every market project is inclusionary, and rental set-asides are often below 20%. Real affordable output from market building is lower than shown.
- **Other compliance routes.** Towns also comply through 100%-affordable projects, supportive housing, accessory units, rehabilitation (present need) and bonus credits. Permits capture only part of this.
- **DCA numbers, not final numbers.** Many towns adopted lower numbers or had them adjusted, for example Montvale from 348 to 255 [10].
- **Permits aren't completions.** Permits authorize construction; some projects are delayed or never built.
- **Imputation.** Census estimates activity for places that don't report every month [11].

## 7. How the system stays current

### 7.1 Pipeline

| Step | Script | What it does |
|---|---|---|
| Fetch | `src/fetch.py` | Lists the Census directory, finds the newest release, and downloads only new or revised files. Records size, Last-Modified time and SHA-256 hash in `data/raw/bps/manifest.json` |
| Build | `src/build.py` | Recomputes the frozen baseline and the live metrics for all 564 towns. Saves a dated snapshot to `data/history/` |
| Log | `data/runs.jsonl` | Adds one line per run **whose inputs changed**: the input hashes plus the headline numbers. Lines are only ever added, never edited, so the log is the system's full history |
| Interactive map | `src/web.py` → `docs/` | Rebuilds the web map (`docs/index.html`, `docs/data/towns.json`) from the same outputs. The workflow deploys `docs/` to GitHub Pages after each run, so the live site always matches the latest data. Also writes `out/web_preview.html`, a single-file copy with the data built in |
| Charts, map and report | `src/chart.py`, `src/map.py`, `src/report.py` | Redraw Figures 1–3, rewrite the Live status block, and list towns that moved onto or off pace since the previous release |
| Schedule | `.github/workflows/update.yml` | Runs every Monday on GitHub Actions and commits only when Census has published something new |

Census revises earlier months, and in May the annual files, so the fetcher re-checks every file it uses on each run. A revision shows up as a new entry in the log.

### 7.2 When this question can no longer be answered

Each run checks whether the system can still answer its question honestly. If a STOP check fails, the README says so at the top of the Live status section instead of presenting stale numbers as current.

| Condition | How it's detected | Status |
|---|---|---|
| The round has ended (after June 30, 2035) | Census vintage later than June 2035 | STOP: the result becomes a retrospective; switch to Fifth Round obligations, which the law requires DCA to calculate |
| Census data stops arriving | Latest release more than 3 months old (WARN), more than 5 (STOP) | WARN / STOP |
| Census changes the file format | Column count or number of NJ places changes | STOP |
| Towns no longer match between sources | Fewer than 560 of 564 matched | STOP |
| DCA republishes the obligation workbook | Size of the upstream file differs from the pinned copy | WARN: reviewed by hand, never swapped in automatically |
| The proxy stops measuring the real thing (adopted or court numbers diverge; compliance mostly through routes permits don't capture) | Can't be detected automatically | MANUAL: reviewed monthly |

The same weekly job publishes `docs/` to GitHub Pages, so the live map updates whenever new data arrives. One-time setup: repo **Settings → Pages → Source: GitHub Actions**.

To run it locally:

```
pip install -r requirements.txt
python3 src/update.py      # fetch → build → charts → README
```

Raw inputs are in `data/raw/`. DCA's 35 MB workbook isn't stored in the repo. Its Final Summary sheet is pinned as `data/raw/dca_final_summary.csv`, with the original file's size and SHA-256 in `dca_pin.json`. `python3 src/pin_dca.py` downloads the workbook and regenerates both. Text copies of the statute and Census documentation used for the quotations are in `data/sources/`.

## References

1. *Southern Burlington County N.A.A.C.P. v. Township of Mount Laurel*, 67 N.J. 151 (1975). https://njlaw.rutgers.edu/collections/d_space/33/67_NJ_151.pdf
2. *Southern Burlington County N.A.A.C.P. v. Township of Mount Laurel*, 92 N.J. 158 (1983) (*Mount Laurel II*).
3. P.L.2024, c.2 (A4/S50), New Jersey Affordable Housing Law, approved March 20, 2024. https://pub.njleg.gov/Bills/2024/PL24/2_.HTM
4. NJ Department of Community Affairs, *Fair Share Housing Obligations for 2025–2035 (Fourth Round): Methodology and Background* (October 2024). https://www.nj.gov/dca/dlps/pdf/FourthRoundCalculation_Methodology.pdf
5. U.S. Census Bureau, Building Permits Survey, place-level files, Northeast Region. https://www2.census.gov/econ/bps/Place/Northeast%20Region/
6. NJ Department of Community Affairs, *Fourth Round Calculation Workbook*. https://www.nj.gov/dca/dlps/pdf/FourthRoundCalculation_Workbook.xlsx
7. Fair Share Housing Center, "Historic Success: 85% of New Jersey Towns Adopt Reasonable Affordable Housing Calculations Under New Law" (February 28, 2025). https://www.fairsharehousing.org/press-release/historic-success-85-of-new-jersey-towns-adopt-reasonable-affordable-housing-calculations-under-new-law/
8. Fair Share Housing Center, "New Affordable Housing Law Delivers Results: Nearly All NJ Towns Resolve Challenges by Dec. 31 Deadline" (January 5, 2026). https://www.fairsharehousing.org/press-release/new-affordable-housing-law-delivers-results-nearly-all-nj-towns-resolve-challenges-by-dec-31-deadline/
9. "Nine towns sue New Jersey to stop next round of affordable housing mandates," via AOL News. https://www.aol.com/news/nine-towns-sue-jersey-stop-140000029.html
10. *In re Borough of Montvale*, BER-L-000750-25, Affordable Housing Dispute Resolution Program, statement of reasons (April 23, 2025). https://www.montvalenj.gov/media/uaoi45kb/mendez-decision.pdf
11. U.S. Census Bureau, "Building Permits Survey: Methodology." https://www.census.gov/construction/bps/methodology.html

12. U.S. Census Bureau, Cartographic Boundary Files, county subdivisions, New Jersey, 1:500,000 (2024). https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_34_cousub_500k.zip

All sources accessed October 13, 2026.

---

*Research design, data sourcing, verification and interpretation by Swapnil Boyapati. Analysis code written with Claude (Anthropic) under the author's direction.*
