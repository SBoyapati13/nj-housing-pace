# NJ housing pace

**Are New Jersey towns building fast enough to meet their 2025–2035 affordable-housing obligations?**

Part of *Unassembled public records*: small, reproducible projects that join public datasets nobody has put side by side.

## Finding

New Jersey's Fourth Round assigns 564 towns a combined **80,798 new affordable homes for 2025–2035**, about 8,080 a year. Over 2021–2025 the state permitted about 35,600 homes a year. That would be close to enough (about 7,100 affordable a year) **if** every new home carried a 20% affordable set-aside.

But the building and the obligations are in different places:

- **34% of all homes permitted in NJ** in 2021–25 were in the 48 towns with **no** new obligation. Almost all of them (47 of 48) are Qualified Urban Aid municipalities, which the formula exempts by design: Jersey City, Newark, Lakewood, Paterson, West New York, Weehawken.
- Among the 514 towns that do have an obligation, **290 are building at under half the needed pace**, even under the generous 20% assumption. **Those towns hold 63% of the statewide obligation.**
- In **17 of 21 counties**, obligated towns as a group fall short. Sussex, Hudson (outside its urban-aid towns), Passaic and Warren are at under a third of the needed pace. Only Cape May, Atlantic, Burlington and Ocean are above it.
- Some of the largest obligations sit with towns that barely build. Secaucus has 1,000 units owed and permitted about 7 homes a year. Wayne has 1,000 owed and about 15 a year. Paramus has 1,000 owed and about 62 a year.

![County coverage](out/county_coverage.png)

## Method (fixed before the numbers were run)

| | |
|---|---|
| Obligation | DCA "prospective need" per town, 2025–2035, after the 1,000-unit / 20% cap |
| Pace | Average yearly **total** housing units permitted, 2021–2025, from Census BPS (imputed totals) |
| Coverage | (pace × 20%) ÷ (obligation ÷ 10). At 1.0 or above, the recent pace could meet the target if every project carried a 20% set-aside |
| Join | 10-digit county-subdivision FIPS. 562 of 564 towns matched; Netcong and Tavistock are not in the Census permit universe |

## What this does not show

- **It's an upper bound.** Not every project is inclusionary, so real affordable output from market building is lower than 20%.
- **It misses other routes to compliance.** Towns can also meet obligations with 100%-affordable projects, group homes, accessory units, rehabilitation and bonus credits, and permits don't capture most of those.
- **The obligation numbers are DCA's calculation, not each town's final number.** Towns could adopt their own numbers, and vacant-land and court adjustments changed many.
- **Permits aren't completions,** and Census estimates permits for towns that don't report every month.

## Re-derive it

```
python3 src/build.py   # writes out/town_pace.csv and out/summary.txt
python3 src/chart.py   # writes out/county_coverage.png and out/county_coverage.csv
```

Raw inputs are in `data/raw/` and were downloaded from:
- Census Building Permits Survey, place files: https://www2.census.gov/econ/bps/Place/Northeast%20Region/ (`neYY12y.txt` = full year; `ne2608y.txt` = 2026 through August)
- NJ DCA Fourth Round Calculation Workbook: https://www.nj.gov/dca/dlps/pdf/FourthRoundCalculation_Workbook.xlsx (methodology: https://www.nj.gov/dca/dlps/pdf/FourthRoundCalculation_Methodology.pdf)

## Next

- Swap in each town's **adopted or court-approved** number where it's published.
- Track 2026 permits monthly, so this becomes a live tracker rather than a snapshot.
- Separate multifamily (5+ unit) permits, where inclusionary set-asides actually happen.

*Scoped, sourced and analyzed by Swapnil Boyapati; code written with Claude.*
