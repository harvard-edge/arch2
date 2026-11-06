# Spec 08: Verification scissors rates and gap

## Claim
`book/contents/chapters/02-pressures/02-pressures.qmd:742`: "The 2022 Wilson Research Group study [...] reports verification staffing growing at about [VALUE]% per year from 2007 to 2022, compared with about [VALUE]% for design staffing [...] Mean peak verification staffing rose [VALUE]% from 2007 to 2014 against [VALUE]% for design [...], then [VALUE]% by 2022 against [VALUE]% for design, although the 2022 values are chart-read and constrained by the study's stated growth. [...] Verification staffing fell [VALUE]% from 2016 to 2018, then rose [VALUE]% by 2020 while design fell [VALUE]%. Measured in multiples of each group's 2007 staffing, the distance between the two indexed lines stayed between [VALUE] and [VALUE] in the printed waves from 2014 to 2020, and the chart-read 2022 point falls inside that range."

`book/contents/chapters/02-pressures/02-pressures.qmd:747-752` (caption of `fig-verification-demand-scissors`): "**Verification staffing outgrew design staffing through 2014, and the gap has held roughly level since.** Mean peak staffing per IC/ASIC project indexed to a 2007 baseline demonstrates that verification engineer demand grew by [VALUE]% (a [VALUE]% compound annual growth rate [CAGR], reaching $\approx [VALUE]\times$) from 2007 to 2022, while design engineer demand grew by [VALUE]% (a [VALUE]% CAGR, reaching $\approx [VALUE]\times$) [...]"

## Raw inputs
- `book/contents/chapters/02-pressures/data/fig-verification-demand-scissors/chapter2-wilson-verification-staffing.csv`. Columns: `year,design_engineers_mean_peak,verification_engineers_mean_peak,evidence_type,source,caveat`. This transcription is the rawest retained record; the survey charts are not retained.
- Row types by `evidence_type`: `printed_data_label` (waves), `chart_read_constrained` (2022), `stated` (the `CAGR 2007-2022` and `context` rows). The `context` row is out of scope.

## Definitions
- `D(t)`, `V(t)`: design and verification mean peak staffing at wave `t`.
- Percent change `a` to `b`: `100 * (x(b)/x(a) - 1)`, signed, unrounded.
- Required spans: 2007 to 2014 for both series; 2014 to 2022 and 2007 to 2022 for both; 2016 to 2018 for both; 2018 to 2020 for both; 2014 to 2020 for both.
- Index: `Iv(t) = V(t)/V(2007)`, `Id(t) = D(t)/D(2007)`, for every wave including 2022.
- `gap(t) = Iv(t) - Id(t)`.
- `gap_min`, `gap_max`: over `t` in 2014, 2016, 2018, 2020.
- `gap_2022`, and `gap_2022_in_range`: `gap_min <= gap_2022 <= gap_max`.
- CAGR computed: `100 * ((x(2022)/x(2007))^(1/15) - 1)` for both series.
- CAGR stated: the `CAGR 2007-2022` row's two numeric cells, read as design and verification percent.
- `share_of_growth_by_2014`: for each series, `(x(2014) - x(2007)) / (x(2022) - x(2007))`, to test "those rates rest on the early years".

## Expected output
```json
{
  "index": {"<year>": {"design": 0.0, "verification": 0.0, "gap": 0.0, "evidence_type": ""}},
  "pct_change": {"<from>_<to>": {"design": 0.0, "verification": 0.0}},
  "gap_min": 0.0, "gap_max": 0.0, "gap_2022": 0.0, "gap_2022_in_range": false,
  "cagr_computed": {"design": 0.0, "verification": 0.0},
  "cagr_stated": {"design": 0.0, "verification": 0.0},
  "share_of_growth_by_2014": {"design": 0.0, "verification": 0.0}
}
```

## Tolerance
Percent changes and CAGRs: 0.05 points. Index and gap values: 0.005. Each is a closed-form calculation on fixed cells, so these bounds only allow for the printed rounding. Computed CAGR against stated CAGR: 0.15 points, because the 2022 inputs are chart-read and the stated rate is rounded. Boolean: exact.

## Ambiguities
- "Then [VALUE]% by 2022" has no stated base year. It may be 2014 to 2022 or 2007 to 2022. Both are reported, and the agreement test accepts the one the book's value matches, which is itself a finding on clarity.
- "Then rose [VALUE]% by 2020 while design fell [VALUE]%" implies 2018 as the base but does not say so.
- "Distance" is read as the difference of indices. A ratio of indices would be another reading, and the prose does not rule it out.
- "Printed waves from 2014 to 2020" is read as 2014, 2016, 2018, 2020, inclusive.
- "Held roughly level" and "movement rather than a trend" have no test.
- The 2022 row is not an independent observation. Its caveat says the values are constrained by callouts in the source, whose labels the row's author had to reinterpret, so the 2022 percentages and the CAGR check partly restate each other.
- The CAGR row's column meaning is inferred from its column names.
