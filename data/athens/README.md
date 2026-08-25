# Athens respondent travel diaries

The `data/athens` directory contains a processed, de-identified release of travel diaries reported by 513 respondents in the Athens metropolitan area. The records were collected through a revealed-preference online survey distributed through Hellenic Broadcasting Corporation websites and radio frequencies in 2022. Respondents described as many as five trips on a typical workday and could omit demographic answers. The collection context is reported by Andrinopoulou and Tzouras (2025), [doi:10.3390/app15073419](https://doi.org/10.3390/app15073419).

The release is a standalone data product. It contains no routing matrix, geographic zone crosswalk, questionnaire export, source respondent identifiers, or exact ages. The maintainers recorded the deterministic source-to-release transformations documented below. Raw source files and preprocessing code are outside the public release.

## Files and observation units

| File | Rows | Observation unit |
| --- | ---: | --- |
| `households.csv` | 513 | Each row is one structural grouping record for a respondent. |
| `persons.csv` | 513 | Each row represents one respondent. |
| `trips.csv` | 1,347 | Each row represents one reported trip. |

`household_id` is retained because `athenspop` supports conventional household, person, and trip tables. In this release, each synthetic household key contains exactly one respondent. It must not be interpreted as a sampled household roster or used to estimate household structure.

## Privacy transformation

The published identifiers are stable synthetic labels created only to join these three tables. Zone labels are also synthetic and have no released geographic crosswalk. Exact ages are replaced by broad bands. Direct identifiers, coordinates, source identifiers, and contact information are absent.

These controls reduce disclosure risk but do not establish formal anonymity. As an ethical data-use request rather than a license condition, the maintainers ask users not to attempt re-identification or link these records to external person-level data.

## Trip timing and chain construction

Respondents reported an integer clock hour for each trip. A reported hour (h) is represented by the inclusive one-hour departure interval

\[
[3600h,\;3600(h+1)-1].
\]

The first trip uses the reported home zone as its origin. Each later trip uses the preceding reported destination as its origin. Within each respondent's reported order, 86,400 seconds are added whenever the next reported hour is lower than the preceding hour. Consequently, 102 chains extend beyond 86,400 seconds and four extend beyond 172,800 seconds. These values preserve reported order across clock rollovers; they do not establish that the diary spans multiple complete days.

The tables contain only reported trips. No return-home trip is imputed, no chain is completed, and no travel duration or route is supplied. Of the 513 reported chains, 203 do not end at the first origin. The trip table contains 373 same-zone movements; a same-zone label does not imply zero distance or zero travel time. Scheduling therefore requires a user-supplied travel-time function.

## Field dictionary

All missing values are empty CSV fields. Identifier and category values are UTF-8 strings. Second-valued and sequence fields are base-10 integers.

### `households.csv`

| Field | Nullable | Contract |
| --- | --- | --- |
| `household_id` | No | Primary key and synthetic structural key that matches `persons.household_id` and `trips.household_id`. |
| `home_zone` | No | Synthetic home-zone label from `z001` through `z036`. No geographic crosswalk is released. |

### `persons.csv`

| Field | Nullable | Contract |
| --- | --- | --- |
| `household_id` | No | Foreign key to `households.household_id`. |
| `person_id` | No | Synthetic respondent identifier. The pair `(household_id, person_id)` is the primary key. |
| `gender` | Yes | The reported category is `female` or `male`. Six values are missing. The survey offered no released category beyond these two labels. |
| `age_group_years` | Yes | The de-identification band is `18_to_30`, `31_to_40`, `41_to_50`, `51_to_65`, or `66_or_older`. Seven values are missing. |
| `education_level` | Yes | The normalized category is `primary_school`, `secondary_school`, `bachelors_degree`, or `masters_or_doctoral_degree`. Two values are missing. |
| `employment_status` | Yes | The normalized category is `employed`, `unemployed`, `student`, or `not_in_labor_force`. Five values are missing. |
| `monthly_income_eur_band` | Yes | The reported categorical band is normalized as `no_income`, `up_to_750_eur`, `750_to_1500_eur`, `1500_to_2500_eur`, or `2500_eur_or_more`. The source labels did not document endpoint conventions for adjacent bands. Forty-five values are missing. |
| `owns_car` | No | Whether the respondent reported private-car ownership. |

## Demographic normalization

The person table uses the following deterministic source-to-release mapping. Blank optional responses remain blank. Three reported ages below the documented adult analysis range are also blanked, so `age_group_years` contains seven missing values: four missing responses and three suppressed values.

| Released field | Source-to-release mapping |
| --- | --- |
| `gender` | Female responses map to `female`, and male responses map to `male`. Blank responses remain blank. |
| `age_group_years` | Ages from 18 through 30 map to `18_to_30`. Ages from 31 through 40 map to `31_to_40`. Ages from 41 through 50 map to `41_to_50`. Ages from 51 through 65 map to `51_to_65`. Ages of 66 or older map to `66_or_older`. Values below 18 and blank responses remain blank. |
| `education_level` | Primary school maps to `primary_school`. High school maps to `secondary_school`. A bachelor's degree maps to `bachelors_degree`. A master's or doctoral degree maps to `masters_or_doctoral_degree`. Blank responses remain blank. |
| `employment_status` | Active employment maps to `employed`. Unemployment maps to `unemployed`. Student status maps to `student`. Inactive status maps to `not_in_labor_force`. Blank responses remain blank. |
| `monthly_income_eur_band` | No income maps to `no_income`. An income of 750 euros or less maps to `up_to_750_eur`. An income of 750-1,500 euros maps to `750_to_1500_eur`. An income of 1,500-2,500 euros maps to `1500_to_2500_eur`. An income of 2,500 euros or more maps to `2500_eur_or_more`. Blank responses remain blank. |
| `owns_car` | Yes responses map to `true`, and no responses map to `false`. |

### `trips.csv`

| Field | Nullable | Contract |
| --- | --- | --- |
| `household_id` | No | Foreign key to `households.household_id`. |
| `person_id` | No | Foreign key to the composite person key with `household_id`. |
| `trip_id` | No | Primary key and synthetic trip identifier. |
| `trip_sequence` | No | One-based position in the respondent's reported chain. Values range from one through five. |
| `origin` | No | Synthetic origin-zone label. The first value is the reported home zone. Later values equal the preceding destination. |
| `destination` | No | Reported synthetic destination-zone label. |
| `purpose` | No | The reported category is `education`, `home`, `market`, `other`, `recreation`, `service`, or `work`. |
| `mode` | No | The reported category is `bicycle`, `bus`, `car`, `escooter`, `motorcycle`, `taxi`, `train`, or `walk`. |
| `earliest_departure_second` | No | Inclusive lower bound of the reported one-hour departure interval. |
| `latest_departure_second` | No | Inclusive upper bound, exactly 3,599 seconds after the lower bound. |

## Analytical scope

The released records are an unweighted respondent sample. Recruitment through broadcasting channels was not probability sampling, demographic responses were optional, and the sample over-represents younger respondents. Results describe these released records and must not be presented as population estimates for Athens. The trip chains contain two through five reported destinations and yield 144 distinct ordered purpose chains. They are not verified complete daily activity sequences.

## Integrity

| File | SHA-256 digest |
| --- | --- |
| `households.csv` | `772c4ecc15418f02c34826b190e4773b510de50af8c2409e2956af4cb36ab560` |
| `persons.csv` | `2a24378c38089ae8ca107181222ef3d15a55d8496df47eef5635c1b60e5b9ab3` |
| `trips.csv` | `4b36212ae877df944e451b36a121d4a4f688334b421ad9b0666e51346241e591` |

## License and attribution

The three CSV files are licensed under the Creative Commons Attribution 4.0 International Public License. The complete legal text is in [LICENSE](LICENSE).

Use the following suggested attribution.

> Theodore Chatziioannou and National Technical University of Athens published *Athens respondent travel diaries: processed dataset* in 2026 under CC BY 4.0 International. The dataset is available at https://github.com/lotentua/athenspop.

Theodore Chatziioannou holds the 2022 copyright.

National Technical University of Athens holds the 2026 copyright.
