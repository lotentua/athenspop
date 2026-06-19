# Input Tables

The public input is dataframe-first: one required `trips` dataframe and two optional dataframes, `persons` and `households`.

## Trips

Required identity columns are `household_id`, `person_id`, and `trip_id`.

Required movement and behavior columns are `origin`, `destination`, `purpose`, and `mode`.

`trip_sequence` is optional only when order is uniquely inferable from concrete departure seconds.
If a row has a departure window, a duplicated concrete departure, or any otherwise ambiguous order, provide non-negative integer `trip_sequence` values that are unique within each `(household_id, person_id)` diary.

Supported concrete timing patterns are:

- `departure_second` plus `arrival_second`.
- `departure_second` plus `travel_time_seconds`.
- `departure_second` plus a `travel_time_function`.

Supported uncertain timing patterns are:

- `earliest_departure_second` plus `latest_departure_second` plus `travel_time_seconds`.
- `earliest_departure_second` plus `latest_departure_second` plus a `travel_time_function`.

Arrival-time ranges are not part of the current public input contract.
Provide concrete arrival time, fixed travel time, or a travel-time function instead.

## Persons

When provided, `persons` must contain `household_id` and `person_id`.
Extra columns are preserved as person metadata when each value is a simple scalar string, number, boolean, or missing value.

## Households

When provided, `households` must contain `household_id`.
Extra columns are preserved as household metadata when each value is a simple scalar string, number, boolean, or missing value.

## Time

All model time columns are integer seconds from a documented diary time origin.
The package rejects floats, booleans, negative seconds, and timestamp objects in model timing columns.
When a table mixes timing patterns, preserve optional timing columns with Python `int` plus `None`, pandas nullable integer dtype such as `Int64`, or another representation that keeps present values as integer scalars.
Ordinary pandas construction can upcast integer-looking values to `float64` when missing values are present, and those floats are rejected intentionally.

Clock strings belong in the IO boundary.
Convert them before calling `SurveyDataset.from_dataframes(...)`.
