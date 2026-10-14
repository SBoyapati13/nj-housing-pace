# Changelog

Methodology changes are recorded here before results that depend on them are published. Data updates are not listed; they are in `data/runs.jsonl`.

## v3 method, pre-registered 2026-10-13 (written before any v3 results were computed)
What was looked at before writing this: reporting coverage and statewide totals in both permit sources for 2015–2025, the file formats, and a handful of named towns (Newark, Jersey City, Wayne, Manalapan, Linden, Edison). No v3 town classifications, statewide figures or maps had been computed.

**Permits come from two sources, shown side by side.**
- *Census Building Permits Survey.* Full years 2015 onward from the revised annual files (`neYYYYa.txt`). The current year from the latest year-to-date file. A town's months reported come from the file's "months reported" field. July–December 2025 = the revised 2025 annual total × the share of the preliminary December total that fell after June ((Dec − Jun) ÷ Dec, clipped to 0–1; 0.5 when the December total is 0). The same rule applies to any later year that is only partly inside the round.
- *NJ DCA Construction Reporter, housing units authorized by building permits.* Months since July 2025 from the monthly files (the month block); a month marked "No report" is not reported. Full years 2015–2024 from the state's revised yearly files; a year without a yearly file uses the December year-to-date figure. A town-year is not reported if the December file marks its year-to-date total "Missing Data".

**A source is usable for a town** when the town reported at least 75% of the round's elapsed months to that source.

**Pace, per source** = homes permitted since July 1, 2025 × 0.20 ÷ (obligation × months elapsed in that source ÷ 120). Classes: below 0.5; 0.5 to 1; 1 to 2; 2 or more.

**One map class per town**, in this order:
1. No obligation: hatched, with the reason (Qualified Urban Aid, or a calculated obligation of zero).
2. Too early to read: the obligation pro-rated to the latest month of either source is under 5 affordable homes.
3. Both sources usable and in the same class: that class. In different classes: "Sources disagree".
4. One source usable: that source's class, marked as one source.
5. No source usable: "Not enough reports".

**Statewide figures** cover obligated towns only, given per source. DCA: towns where DCA is usable. Census: all obligated towns, with the share that is Census estimates. Permits in towns with no obligation are reported separately.

**Best-year threshold.** Per source, the best year from 2015 through the latest full year, counting only years the town fully reported (12 months to Census; not marked missing by DCA). It needs at least 5 such years. It is no longer shown on the map; it appears in the town detail and the README.

**2021–25 baseline.** Re-derived from both sources' revised data. A town needs at least 4 of 5 years reported to a source to get a baseline figure from it. The v1 frozen baseline numbers are kept in `data/runs.jsonl` and marked superseded.

**Negative values.** A town's homes permitted since July 2025 are clipped at 0 and flagged; the count of flagged towns appears in the health checks.

**Completions.** The completion ratio and the pipeline are computed against DCA permits (same agency and town codes as the certificates of occupancy). A town-year of completions is treated as missing where the state marks the year-to-date processing date "Missing Data" and the total is 0. This replaces the v2.2 zero-with-permits rule.

**Health.** Health is written to `data/health.json` (no timestamps) and committed whenever it changes, so a stale-source warning is published even when no new data arrives. A failed check of an upstream file no longer writes an error into a manifest.

**Wording.** The 20% set-aside is described as a yardstick, not an upper bound: prior-round surplus credits, bonus credits, 100%-affordable projects and vacant-land adjustments can move delivered affordable homes either way. The map palette moves off red/blue.

## Notice of errors, 2026-10-13 (correction in progress)
An adversarial review of v2.2 found errors that affect published figures. Until the corrected version (v3) is posted, the map and README carry an "under revision" notice.
- **Preliminary 2024–25 permits.** Full years were read from the December year-to-date files, not from the revised annual files Census publishes each May. For 2025 the state total is 32,021 in the file used against 27,661 revised; some towns differ far more (Manalapan 1,451 vs. 366). The README wrongly said annual files and annual revisions were used.
- **Unreported months counted as town activity.** Census fills in towns that didn't report with estimates. In January–August 2026, 19,634 units were counted but 10,952 were reported; 144 of the 514 obligated towns reported no months. These estimates were shown as each town's own building.
- **Statewide figure mixed exempt and obligated towns.** The 75% statewide figure counted permits in the 48 towns with no obligation. Counting obligated towns only gives about 48%.
- **Map classes.** The best-year threshold overrode pace, so 9 towns at or above the pro-rated pace were shown in the darkest class.
- **Other issues** found in the same review (the 20% set-aside described as an upper bound, credits and adjustments not discussed, an overstated pre-registration claim, small-number and negative values, health status not published when no new data arrives, and labelling of final-obligation sources) will be addressed and listed in v3.

## v2.2, 2026-10-13
- **Added** a sourced file of final or adopted obligations for the 15 largest (`data/raw/obligation_final.csv`): status, date, document, link and verbatim quote for each. 12 of 15 were found; 9 are firm (court order, settlement, or accepted as calculated). The state's calculation remains the main measure. A sensitivity figure substitutes the firm final numbers (statewide pace 76% vs. 75% at the August 2026 vintage).
- **Added** a reported-completions layer from NJ DCA certificates of occupancy: completions since July 2025, a completion ratio for 2015–2024, and a two-year pipeline. It's a secondary layer and doesn't change the map colors or coverage ratios.
- **Added** two health checks: how old the completions data is, and the share of towns reporting. Both can WARN but never STOP.
- **Added after inspecting the data, before publishing:** a town-year with zero reported completions despite at least 100 homes permitted in the prior two years is treated as likely not reported. It's excluded from the completion ratio, the pipeline and completions since July 2025. Prompted by Jersey City, which reported 1,057–3,603 completions a year in 2019–2023 and zero in 2024 and 2025.
- The frozen 2021–2025 baseline and all v2 live metrics are unchanged.

## v2.1, 2026-10-13 (wording only; no numbers changed)
- Reworded every description of towns to be descriptive rather than judgmental: "pro-rated pace" instead of "behind" or "falling short", and "best-year threshold" instead of "point of no return" or "can't finish".
- Added a "How to read this" note: this is a permit-based indicator, not a finding about any town's compliance.
- Removed the "years to meet" column from the largest-obligations table; long projections next to named towns read as verdicts.
- The town map now sits at the top of the README, links to the interactive map, and carries a badge showing the Census data month.

## v2, 2026-10-13
- **Correction:** the Fourth Round clock now starts **July 1, 2025**, not January 1, 2025. P.L.2024, c.2 states the round begins "with the fourth round on July 1, 2025." All live metrics (progress to date, months elapsed, pro-rated target) moved. Effect at the August 2026 vintage: statewide progress 77% → 75%; towns below half pace 319 → 329.
- **Added** point-of-no-return metrics at two thresholds (inclusionary route at 20%, every route at 100%), each measured against the town's best year since 2015, with a projected closing month if the current pace continues.
- **Added** health checks covering when the question can no longer be answered (round end, Census freshness and format, town matching, obligation-source changes, and a manual proxy-validity review).
- The frozen 2021–2025 baseline is unchanged.

## v1, 2026-10-13
- Baseline analysis (2021–2025 permits vs. DCA prospective need) and the first live layer.
