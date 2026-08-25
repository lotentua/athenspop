# Data model and validation

`athenspop` separates untrusted dataframe input from immutable model objects. Validation is the only public boundary that interprets table shape, key values, timing combinations, and diary order. Downstream scheduling and sequence operations therefore receive a smaller, explicit contract.

## Three long-form tables

The trip table is required. Person and household tables are optional metadata layers.

| The table has this name. | These fields identify each row. | The table has this role. |
| --- | --- | --- |
| `trips` | `household_id`, `person_id`, `trip_id` | Each row represents one movement and includes movement labels and timing fields. |
| `persons` | `household_id`, `person_id` | Each row provides optional respondent attributes for the matching diary. |
| `households` | `household_id` | Each row provides optional attributes shared by matching diaries. |

Keys are normalized to stripped strings. They must be present, nonempty, and unique at their table level. When optional metadata tables are supplied, trip-to-person, trip-to-household, and person-to-household references must resolve.

Each trip also requires nonempty `origin`, `destination`, `purpose`, and `mode` labels. Additional scalar columns are preserved in immutable metadata mappings. Missing metadata becomes `None`; NumPy scalar values become the corresponding Python scalars.

## Timing patterns

Each trip row must match exactly one pattern. All times are nonnegative integer seconds from a diary-specific origin.

| The pattern has this name. | The pattern requires these timing fields. | Use the pattern under this condition. |
| --- | --- | --- |
| This pattern uses a concrete interval. | `departure_second`, `arrival_second` | Both endpoints are observed or otherwise fixed. |
| This pattern uses a concrete departure and duration. | `departure_second`, `travel_time_seconds` | The departure and positive duration are fixed. |
| This pattern uses a concrete departure and resolver. | `departure_second` | A travel-time function supplies the positive duration. |
| This pattern uses a departure window and duration. | `earliest_departure_second`, `latest_departure_second`, `travel_time_seconds` | The departure is uncertain within an inclusive window, and the duration is fixed. |
| This pattern uses a departure window and resolver. | `earliest_departure_second`, `latest_departure_second` | The departure is uncertain, and a travel-time function supplies the duration. |

Arrival windows are outside the supported contract. A departure window must satisfy `earliest_departure_second <= latest_departure_second`. Concrete arrivals and fixed travel times must imply positive movement duration.

Use `athenspop.io.clock.convert_clock_columns` when source data contain civil clock values. It converts `HH:MM`, `HH:MM:SS`, datetime-like values, timedeltas, or seconds after midnight into integer seconds from a selected clock origin. The conversion wraps once within a civil day. Multi-day diary construction remains an upstream data decision.

## Diary order and continuity

Rows are grouped by `(household_id, person_id)`. A supplied `trip_sequence` must contain unique nonnegative integers within each diary. If the column is absent, every trip in the diary must have a distinct concrete departure, which becomes the order.

An origin that differs from the preceding destination produces a warning because disconnected chains can be analytically meaningful. Overlapping concrete trips produce an error. Validation collects independent issues where possible, then suppresses checks that would only cascade from a row or chain already known to be invalid.

## Validation before construction

Use the report API when an interface needs all diagnostics:

```python
import athenspop.validation.schema

result = athenspop.validation.schema.validate_dataframes(
    trips,
    persons,
    households,
)
for issue in (*result.report.errors, *result.report.warnings):
    print(issue.severity, issue.code, issue.message)

result.report.raise_if_invalid()
```

Use `athenspop.model.survey.SurveyDataset.from_dataframes` when raising `athenspop.validation.report.ValidationError` is the desired control flow. On success, it returns immutable `Diary`, `Trip`, `PersonMetadata`, and `HouseholdMetadata` objects. Validation does not invoke a travel-time function; function evaluation occurs only during scheduling.

```{admonition} This note defines the interpretation boundary.
:class: note

Schema validity establishes that the supplied records satisfy the package contract. It does not establish survey representativeness, trip-chain completeness, geographic accuracy, or fitness of an analyst's state definitions and costs.
```
