# Data contract

This page is the field-level reference for {py:func}`athenspop.validation.schema.validate_dataframes` and {py:meth}`athenspop.model.survey.SurveyDataset.from_dataframes`. For an explanation of the model and validation workflow, read [Data model and validation](../concepts/data_model.md).

## Trip table

The trip table is required and contains one row per movement.

| Field | Required | Accepted value |
| --- | --- | --- |
| `household_id` | Yes | Nonmissing scalar normalized to a nonempty string |
| `person_id` | Yes | Nonmissing scalar normalized to a nonempty string |
| `trip_id` | Yes | Nonmissing scalar normalized to a nonempty string; unique within household and person |
| `origin` | Yes | Nonmissing scalar normalized to a nonempty string |
| `destination` | Yes | Nonmissing scalar normalized to a nonempty string |
| `purpose` | Yes | Nonmissing scalar normalized to a nonempty string |
| `mode` | Yes | Nonmissing scalar normalized to a nonempty string |
| `trip_sequence` | Conditional | Unique nonnegative integer within a diary; required unless distinct concrete departures establish order |
| `departure_second` | Pattern-dependent | Nonnegative integer second from the diary origin |
| `arrival_second` | Pattern-dependent | Nonnegative integer later than its concrete departure |
| `travel_time_seconds` | Pattern-dependent | Positive integer duration |
| `earliest_departure_second` | Pattern-dependent | Inclusive nonnegative integer lower bound |
| `latest_departure_second` | Pattern-dependent | Inclusive nonnegative integer upper bound no earlier than the lower bound |

Boolean values are rejected for integer time and sequence fields.

### Valid timing combinations

Each trip must match exactly one row in this table. Timing fields not listed for that row must be absent or missing.

| Pattern | `departure_second` | `arrival_second` | `travel_time_seconds` | Departure bounds |
| --- | :---: | :---: | :---: | :---: |
| Concrete interval | Yes | Yes | No | No |
| Concrete departure and duration | Yes | No | Yes | No |
| Concrete departure and resolver | Yes | No | No | No |
| Departure window and duration | No | No | Yes | Both |
| Departure window and resolver | No | No | No | Both |

The resolver patterns require a travel-time function during scheduling. Arrival windows are not supported; `earliest_arrival_second` and `latest_arrival_second` are rejected.

## Person and household tables

The optional person table requires `household_id` and `person_id`. The optional household table requires `household_id`. Keys must be unique at their table level, and all supplied references must resolve.

Additional columns in any table may contain strings, integers, floats, booleans, corresponding NumPy scalar values, or missing values. The normalized model preserves them as immutable metadata. Nested containers and other nonscalar values are rejected.

## Diary-level checks

Rows are grouped by household and person, then ordered by `trip_sequence` or by distinct concrete departures. Validation applies these diary checks:

- duplicate sequence values are errors;
- overlapping concrete trips are errors;
- a trip origin that differs from the previous destination is a warning; and
- joins to supplied person and household tables must resolve.

Validation collects independent issues where possible. Errors prevent normalized tables; warnings do not. See the [validation API](../api/validation.md) for the report and issue objects.

## Released Athens data

The processed tables under `data/athens` implement the same generic contract:

| File | Rows | Observation unit |
| --- | ---: | --- |
| `households.csv` | 513 | One synthetic structural grouping per respondent |
| `persons.csv` | 513 | One respondent |
| `trips.csv` | 1,347 | One reported trip |

The complete field dictionary, controlled categories, missing-value counts, privacy transformation, hashes, and attribution are maintained in the [dataset README](https://github.com/lotentua/athenspop/blob/v2/data/athens/README.md).

### Athens timing transformation

The source survey recorded an integer clock hour. Hour `h` becomes an inclusive departure window from second `3600h` through second `3600(h + 1) - 1`. When the next reported hour is earlier than the preceding hour, the transformation adds one day to that trip and the trips that follow. This preserves reported order across midnight without claiming that the diary covers several observed days.

The release contains no travel durations, routes, or geographic zone crosswalk. Scheduling these records therefore requires a user-supplied travel-time function. Same-zone movements remain trips, and no return-home trip is added.

## Clock conversion

{py:func}`athenspop.io.clock.convert_clock_columns` converts civil clock columns before validation. The default diary origin is 03:00. A clock value earlier than the origin wraps once into the following civil day. The [input conversion API](../api/io.md) lists accepted clock types and exceptions.
