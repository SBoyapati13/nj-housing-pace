# Changelog

Methodology changes are recorded here before results that depend on them are published. Data updates are not listed; they are in `data/runs.jsonl`.

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
