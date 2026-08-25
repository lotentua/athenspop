# Athens respondent travel diaries

This directory contains a processed, de-identified travel-diary dataset for 513 respondents in the Athens metropolitan area. It is small enough to explore quickly and follows the same trip, person, and household contract accepted by `athenspop`.

The data are well suited to questions about reported trip order, destination purposes, modes, broad departure periods, and available respondent characteristics. They do not contain routes, distances, travel durations, coordinates, or a geographic crosswalk.

Andrinopoulou and Tzouras describe the 2022 survey and its recruitment context in [Applying spectral clustering to decode mobility patterns in Athens, Greece](https://doi.org/10.3390/app15073419). The [Athens workflow](../../docs/workflows/athens_analysis.md) shows a self-contained purpose-chain analysis of this release.

## Load the tables

```python
import pandas as pd

households = pd.read_csv("data/athens/households.csv")
persons = pd.read_csv("data/athens/persons.csv")
trips = pd.read_csv("data/athens/trips.csv")
```

Pass the three dataframes to [`SurveyDataset.from_dataframes`](../../docs/api/model.md) to validate their keys, categories, and trip order:

```python
import athenspop.model.survey

diaries = athenspop.model.survey.SurveyDataset.from_dataframes(
    trips,
    persons=persons,
    households=households,
)
```

## Files

| File | Rows | One row represents |
| --- | ---: | --- |
| `households.csv` | 513 | A synthetic structural grouping for one respondent |
| `persons.csv` | 513 | One respondent |
| `trips.csv` | 1,347 | One reported trip |

`household_id` is present because `athenspop` supports conventional household, person, and trip tables. Every synthetic household key in this release contains exactly one respondent. It is a join key, not a sampled household roster, and cannot support estimates of household structure.

## What was changed for release

Published household, person, trip, and zone identifiers are stable synthetic labels used only to join these tables. The release contains no direct identifiers, source identifiers, coordinates, contact details, or exact ages. Exact ages were replaced with broad bands.

These transformations reduce disclosure risk but do not establish formal anonymity. As an ethical data-use request rather than a license condition, please do not attempt to re-identify respondents or link the records to external person-level data.

Raw source files and preprocessing code are not part of this data product. The deterministic transformations needed to understand the released values are documented below.

## How trip chains and times were constructed

Respondents reported as many as five trips on a typical workday and supplied an integer clock hour for each trip. A reported hour `h` became a departure window beginning at second `3600h` and ending 3,599 seconds later.

The first trip begins at the respondent's reported home zone. Every later origin equals the preceding reported destination. When a reported hour moved backward across the clock, 86,400 seconds were added to preserve trip order across midnight. As a result, 102 chains extend beyond second 86,400 and four extend beyond second 172,800. These offsets preserve order; they do not establish several complete observed days.

Only reported trips appear in the table. No return-home movement was added, no chain was completed, and no duration or route was inferred. Of the 513 chains, 203 do not end at their first origin. The data also contain 373 same-zone movements; the shared zone label does not imply zero distance or travel time.

Scheduling the released departure windows requires a user-supplied travel-time function.

## Field dictionary

Missing values are empty CSV fields. Identifiers and categories are UTF-8 strings. Sequence and time fields are base-10 integers.

### `households.csv`

| Field | Missing allowed | Meaning |
| --- | --- | --- |
| `household_id` | No | Primary key shared with the person and trip tables |
| `home_zone` | No | Synthetic home-zone label from `z001` through `z036`; no geographic crosswalk is released |

### `persons.csv`

| Field | Missing allowed | Meaning |
| --- | --- | --- |
| `household_id` | No | Foreign key to `households.csv` |
| `person_id` | No | Synthetic respondent identifier; forms the primary key with `household_id` |
| `gender` | Yes | `female` or `male`; 6 values are missing |
| `age_group_years` | Yes | `18_to_30`, `31_to_40`, `41_to_50`, `51_to_65`, or `66_or_older`; 7 values are missing |
| `education_level` | Yes | `primary_school`, `secondary_school`, `bachelors_degree`, or `masters_or_doctoral_degree`; 2 values are missing |
| `employment_status` | Yes | `employed`, `unemployed`, `student`, or `not_in_labor_force`; 5 values are missing |
| `monthly_income_eur_band` | Yes | `no_income`, `up_to_750_eur`, `750_to_1500_eur`, `1500_to_2500_eur`, or `2500_eur_or_more`; 45 values are missing |
| `owns_car` | No | Whether the respondent reported private-car ownership |

The survey offered no released gender category beyond `female` and `male`. The source income labels did not document how shared endpoints between adjacent bands should be interpreted.

### Demographic normalization

Blank optional responses remain blank. Three reported ages below the documented adult analysis range were also blanked, giving four missing responses and three suppressed values in `age_group_years`.

| Released field | Source-to-release mapping |
| --- | --- |
| `gender` | Female and male responses become `female` and `male` |
| `age_group_years` | Adult ages become the five documented bands; values below 18 and blank responses remain blank |
| `education_level` | Primary school, high school, bachelor's degree, and master's or doctoral degree become the four documented labels |
| `employment_status` | Active employment, unemployment, student status, and inactive status become `employed`, `unemployed`, `student`, and `not_in_labor_force` |
| `monthly_income_eur_band` | The five source income responses become the five documented bands in ascending order |
| `owns_car` | Yes and no become `true` and `false` |

### `trips.csv`

| Field | Missing allowed | Meaning |
| --- | --- | --- |
| `household_id` | No | Foreign key to `households.csv` |
| `person_id` | No | Foreign key to the composite person key |
| `trip_id` | No | Synthetic primary key for the trip |
| `trip_sequence` | No | One-based position in the reported chain, from one through five |
| `origin` | No | Synthetic origin zone; the first is home and later values repeat the preceding destination |
| `destination` | No | Synthetic reported destination zone |
| `purpose` | No | `education`, `home`, `market`, `other`, `recreation`, `service`, or `work` |
| `mode` | No | `bicycle`, `bus`, `car`, `escooter`, `motorcycle`, `taxi`, `train`, or `walk` |
| `earliest_departure_second` | No | Inclusive start of the reported one-hour window |
| `latest_departure_second` | No | Inclusive end, 3,599 seconds after the start |

## Interpretation limits

The records are an unweighted respondent sample. Recruitment through broadcasting channels was not probability sampling, demographic responses were optional, and younger respondents are overrepresented. Results describe these released records and should not be presented as population estimates for Athens.

The chains contain two through five reported destinations and form 144 distinct purpose sequences. Because trips may be unreported and no return-home movement was added, they are not verified complete daily activity schedules.

## Verify file integrity

| File | SHA-256 digest |
| --- | --- |
| `households.csv` | `772c4ecc15418f02c34826b190e4773b510de50af8c2409e2956af4cb36ab560` |
| `persons.csv` | `2a24378c38089ae8ca107181222ef3d15a55d8496df47eef5635c1b60e5b9ab3` |
| `trips.csv` | `4b36212ae877df944e451b36a121d4a4f688334b421ad9b0666e51346241e591` |

## License and attribution

The three CSV files are licensed under the Creative Commons Attribution 4.0 International Public License. [LICENSE](LICENSE) contains the complete legal text.

Suggested attribution:

> Theodore Chatziioannou and National Technical University of Athens published *Athens respondent travel diaries: processed dataset* in 2026 under CC BY 4.0 International. The dataset is available at https://github.com/lotentua/athenspop.

Copyright (c) 2022 Theodore Chatziioannou

Copyright (c) 2026 National Technical University of Athens
