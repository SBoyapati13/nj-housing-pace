# Changelog

Methodology changes are recorded here before results that depend on them are published. Data updates are not listed; they are in `data/runs.jsonl`.

## v3.2, published 2026-10-19
Implemented as registered below. As expected, 100 towns moved to "too early to read" (all with obligations of 84 units or fewer) and none moved out; statewide pace figures are unchanged. Colored obligated towns: 190 (120 on both sources agreeing, 70 on one). The disclosure of colored towns with a small shared-period target is dropped, since there are none.

## v3.2 method, registered 2026-10-19 (before v3.2 results were computed)
One change, closing the inconsistency disclosed in v3.1 (README §6): the too-early test used the obligation pro-rated to the latest month of either source (Census, 14 months), while map colors compare both sources over the shared period (7 months), so 74 colored towns had a shared-period target under 5 affordable homes.
- **Too early to read** now means the obligation pro-rated over the shared period (July 2025 through the earlier of the two sources' latest months) is under 5 affordable homes. The threshold (5) is unchanged.
- Nothing else changes: sources, usable-source rule, missing-data and unconfirmed-zero rules, classes and their order, statewide figures. Figure 2 and the "below half" counts keep leaving out too-early towns.
- Expected before computing: more towns move to "too early" (any obligation under about 86 units at a 7-month shared period), none move out of it; colored-town counts fall accordingly.

## v3.1, published 2026-10-13
Implemented as registered below. Also in this release, none of which changes a figure:
- The interactive map, the static map and Figure 2 compare both sources over the same period. Each source's own full-period figures stay in the statewide table and the town detail.
- The static map's legend shows, for each color, how many towns rest on one usable source; the town detail marks them "(one usable source)".
- `obligation_final.csv`: the `verification` column now agrees with `evidence` (primary documents that describe an order or settlement are labelled as such).
- The fetcher no longer stops the whole run if the Census index can't be reached; it keeps the previous data and reports the problem.
- The build now stops if `obligation_final.csv` is malformed or names an unknown town, after a bad edit during this release briefly made it match no towns (caught before publication).
- Figure 2 leaves out towns too early to read, and the "towns below half" counts in the Live status exclude them. Presentation only; no class changes.
- New disclosures in the Live status and README §6: how many colored towns rest on one source, have a small shared-period target, or are colored from Census alone with no homes reported.
- The "under revision" notice was removed after a second independent check of v3.1 recomputed every town from the raw files and found no arithmetic errors (see `data/review_log.md`).

## v3.1 method, registered 2026-10-13 after v3 results were computed (before v3.1 results)
An independent check of v3 recomputed every figure and confirmed the arithmetic, but found three problems in the v3 rules. These corrections were written **after seeing v3 results**, in response to that check, and before any v3.1 results were computed. v3 was never published without the "under revision" notice.
1. **Same window for the map class.** v3 compared the state's 7 months with Census's 14, so "sources disagree" partly measured timing. In v3.1 the class compares both sources over the common window: July 2025 through the earlier of the two sources' latest months. For Census that is July–December 2025 (as in v3) plus the year-to-date file for the window's last month. The usable test (75% of months) applies to the same window. Each source's figures over its own full period stay in the town detail and the statewide table, labelled with their periods.
2. **State "Missing Data" markers on processing dates.** A state year-to-date figure read from a monthly file counts as reported only if neither its total nor its processing date is marked "Missing Data". This matches the completions rule. Revised yearly files are unaffected.
3. **Unconfirmed state zeros.** A state figure of exactly 0, for the window or for a full year, counts as reported only if the same town reported at least 75% of the same period's months to Census and those reports total fewer than 5 homes. Otherwise the state zero is treated as not reported. This replaces the v3 diagnostic flag.

## v3, built 2026-10-13 (never published without the "under revision" notice; superseded by v3.1): what changed beyond the registered method
Implemented as registered below, with these additions and removals, all made while building and listed so none is silent:
- **Added after the first v3 results (diagnostic only, changes no class):** a flag for towns whose state figure since July 2025 is 0 while the town reported 20 or more homes to Census (10 towns). The state's "Missing Data" marker turned out not to catch every missing report: in 62 town-years since 2015 the state recorded 0 against a full-year Census report of 20 or more. Replaced in v3.1 by rule 3.
- **Removed:** the trailing-12-month pace and the projected month a town would cross the best-year threshold. Both relied on Census estimates for non-reporting towns.
- **Health:** the two reporting checks became one (`reporting_coverage`), warning only when neither source has usable reports for towns holding 60% of the obligation. Census coverage alone is low by nature (towns holding 53% of the obligation at the first release) and is reported, not flagged.
- **Figure 2** (county chart) counts only towns with usable reports to each source. The former Figure 3 (frozen v1 county baseline) is removed; the re-derived baseline is in README §4.
- **Final numbers:** an `evidence` column says whether each status comes from the order, settlement or resolution itself, or from a document describing it. Montvale added: the Superior Court fixed its prospective need at 205 on June 12, 2025 (the README previously gave 255, the earlier dispute-program recommendation).
- **Presentation:** orange–purple palette instead of red–blue; no town names printed on the static map; the page heading and link-preview description no longer ask whether towns permit "enough"; "owes" and "Passed" removed from labels; "No new obligation" gives the reason per town (Qualified Urban Aid, or a calculated obligation of zero).
- **Run log:** a note line records that v1–v2.2 are superseded; their lines are kept unchanged.

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

**Amendment, same evening, before any v3 results were computed.** The state's month-by-month files mark a town "No report" whenever its report hadn't arrived by publication, and late reports are folded into later year-to-date totals, so counting months from the month blocks would undercount. DCA months since July 2025 are therefore counted from year-to-date files instead. July–December 2025 = December 2025 year-to-date minus June 2025 year-to-date; it counts as 6 reported months when neither total is marked "Missing Data", and otherwise as 0 months with no homes counted. Each later full year inside the round works the same way (12 months). The current year = the latest year-to-date total, counted as all of its months when not marked "Missing Data". The 75% usability rule applies to these counts. A missing current-year total is counted as 0 homes for those months, so DCA figures for towns that are usable but behind on reports lean low.

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
