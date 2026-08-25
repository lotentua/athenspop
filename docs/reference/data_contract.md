# Data contract

`athenspop` defines a generic dataframe boundary and additional semantics for the released Athens tables. The validator accepts pandas dataframes. File format, source-system parsing, category harmonization, clock-rollover handling, and disclosure control belong before this boundary.

## Generic trip fields

| Field | Requirement | Type and rule |
| --- | --- | --- |
| `household_id` | Yes | The validator normalizes this nonmissing scalar to a nonempty string. |
| `person_id` | Yes | The validator normalizes this nonmissing scalar to a nonempty string. |
| `trip_id` | Yes | The validator normalizes this nonmissing scalar to a nonempty string. The value must be unique with the household and person keys. |
| `origin` | Yes | The validator normalizes this nonmissing scalar to a nonempty string. |
| `destination` | Yes | The validator normalizes this nonmissing scalar to a nonempty string. |
| `purpose` | Yes | The validator normalizes this nonmissing scalar to a nonempty string. |
| `mode` | Yes | The validator normalizes this nonmissing scalar to a nonempty string. |
| `trip_sequence` | Conditional | A unique nonnegative integer within a diary. Required when distinct concrete departures do not establish order. |
| `departure_second` | Pattern-dependent | The value must be a nonnegative integer second from the diary time origin. |
| `arrival_second` | Pattern-dependent | The value must be a nonnegative integer second that occurs strictly after its concrete departure. |
| `travel_time_seconds` | Pattern-dependent | The value must be a positive integer duration. |
| `earliest_departure_second` | Pattern-dependent | The value is an inclusive nonnegative integer lower bound. |
| `latest_departure_second` | Pattern-dependent | The value is an inclusive nonnegative integer upper bound that cannot be below the earliest bound. |

See [Data model and validation](../concepts/data_model.md#timing-patterns) for the five permitted timing combinations. `earliest_arrival_second` and `latest_arrival_second` are rejected because arrival windows are not a supported scheduling input.

Extra trip, person, and household columns may contain strings, integers, floats, booleans, NumPy equivalents, or missing values. Nested objects and other nonscalar values are rejected.

## Generic metadata tables

`persons` requires `household_id` and `person_id`. `households` requires `household_id`. Their remaining scalar columns are preserved without assigning package-level meaning. The optional tables are relational metadata, not a requirement that every survey use household sampling.

## Released Athens tables

The processed release is stored under `data/athens` and licensed separately under CC BY 4.0 International. Its complete field dictionary, privacy transformation, integrity hashes, and attribution text are in the [dataset README](https://github.com/lotentua/athenspop/blob/v2/data/athens/README.md).

| File | Rows | Observation unit |
| --- | ---: | --- |
| `households.csv` | 513 | Each row is one structural grouping record for a respondent. |
| `persons.csv` | 513 | Each row represents one respondent. |
| `trips.csv` | 1,347 | Each row represents one reported trip. |

Each synthetic household key contains one respondent. It cannot measure household composition. Zone values are synthetic labels from `z001` through `z036` without a geographic crosswalk.

The person table uses controlled snake-case categories:

- `gender` accepts `female`, `male`, or a missing value.
- `age_group_years` accepts `18_to_30`, `31_to_40`, `41_to_50`, `51_to_65`, `66_or_older`, or a missing value.
- `education_level` accepts `primary_school`, `secondary_school`, `bachelors_degree`, `masters_or_doctoral_degree`, or a missing value.
- `employment_status` accepts `employed`, `unemployed`, `student`, `not_in_labor_force`, or a missing value.
- `monthly_income_eur_band` accepts `no_income`, `up_to_750_eur`, `750_to_1500_eur`, `1500_to_2500_eur`, `2500_eur_or_more`, or a missing value.
- `owns_car` contains a Boolean value.

The source income labels did not define shared band endpoints. The normalized labels preserve that unresolved boundary rather than implying a precise continuous-income interval.

The maintainers recorded the deterministic source-to-release mapping summarized here. Raw source files and preprocessing code are outside the public release. Female and male responses retain those labels. Exact adult ages become the five documented age bands; three values below 18 and four missing responses become missing. Primary school, high school, bachelor's degree, and master's or doctoral degree map to the four education labels in order. Active employment, unemployment, student, and inactive status map to `employed`, `unemployed`, `student`, and `not_in_labor_force`. The five source income responses map to the five released income labels in ascending order. Yes and no car-ownership responses become Boolean values. All missing optional responses remain missing.

## Athens timing transformation

A reported integer clock hour $h$ becomes the inclusive interval

$$
[3600h,\ 3600(h+1)-1].
$$

Within a respondent's order, 86,400 seconds are added whenever the next clock hour is lower than the previous hour. This transformation preserves order across clock rollovers. It does not establish elapsed multi-day observation. The release supplies neither durations nor routes, so scheduling it requires a user-defined travel-time function.

No return-home trip is added. A same-zone movement remains a trip and does not imply zero travel time. Users should preserve these distinctions when deriving analysis tables.
