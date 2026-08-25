# Data model and validation

A travel diary is more than a table of trips. Its rows belong to people, the trips have an order, adjacent movements may need to connect, and several different combinations of time fields can describe the same kind of movement. If those relationships remain implicit, every later analysis has to interpret them again.

`athenspop` resolves that ambiguity once. It accepts familiar [pandas `DataFrame` objects](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html), reports problems in the source tables, and constructs immutable diaries for the rest of the workflow.

## Why the package uses long-form tables

One trip per row works well for surveys, database extracts, and dataframe operations. A trip table is required; person and household tables add attributes without changing the trip schema.

| Table | Row identity | What it contributes |
| --- | --- | --- |
| `trips` | `household_id`, `person_id`, `trip_id` | Movement, purpose, mode, and timing |
| `persons` | `household_id`, `person_id` | Respondent attributes |
| `households` | `household_id` | Attributes shared by related respondents |

The validator strips and normalizes identifiers, checks uniqueness, and verifies references between supplied tables. Additional scalar columns remain available as metadata, so a survey can carry its own categories without extending the package model.

After validation, {py:class}`athenspop.model.survey.SurveyDataset` groups the rows into {py:class}`athenspop.model.survey.Diary` objects. Each diary contains ordered {py:class}`athenspop.model.survey.Trip` objects and the matching person and household metadata.

## Five ways to describe trip timing

Some surveys record exact departures and arrivals. Others record a departure range, a travel duration, or only enough location information for an external travel-time function. The package accepts five combinations:

| Timing pattern | Required fields | Typical use |
| --- | --- | --- |
| Concrete interval | `departure_second`, `arrival_second` | Both times are known |
| Concrete departure and duration | `departure_second`, `travel_time_seconds` | Departure and duration are known |
| Concrete departure and resolver | `departure_second` | A function supplies the duration |
| Departure window and duration | `earliest_departure_second`, `latest_departure_second`, `travel_time_seconds` | Departure is uncertain; duration is known |
| Departure window and resolver | `earliest_departure_second`, `latest_departure_second` | Both departure choice and travel time are resolved later |

Each row must match exactly one pattern. Mixing an arrival with a departure window, for example, is ambiguous because the package would not know whether the arrival is fixed or should move with the sampled departure.

All package times are integer seconds from a diary-specific origin. If a source uses civil clock values such as `08:30`, {py:func}`athenspop.io.clock.convert_clock_columns` converts them before validation. It accepts clock strings, Python datetime-like values, timedeltas, and seconds after midnight. The [input conversion API](../api/io.md) documents rollover behavior and supported types.

## How rows become an ordered diary

Rows with the same household and person identifiers form one diary. A `trip_sequence` column is the clearest way to define order. When it is absent, every trip must have a distinct concrete departure so the validator can derive the order without guessing.

The destination of one trip usually becomes the origin of the next. A break in that chain produces a warning rather than an error because disconnected records can still be useful. Overlapping concrete trips are an error because they cannot describe one person's schedule.

This distinction is intentional:

- errors prevent construction of trusted model objects;
- warnings preserve the diary while drawing attention to a condition that may matter to the analysis.

## Inspect problems before building a model

Call {py:func}`athenspop.validation.schema.validate_dataframes` when you want to show or store all diagnostics:

```python
import athenspop.validation.schema

validation = athenspop.validation.schema.validate_dataframes(
    trips,
    persons=persons,
    households=households,
)

for issue in (*validation.report.errors, *validation.report.warnings):
    print(issue.severity, issue.code, issue.message)
```

The returned {py:class}`athenspop.validation.schema.ValidationResult` places the cleaned dataframes in `validation.normalized_tables` when the report contains no errors. {py:meth}`athenspop.validation.report.ValidationReport.raise_if_invalid` converts an error report into an exception when that control flow is more convenient.

Most analysis code can use {py:meth}`athenspop.model.survey.SurveyDataset.from_dataframes` directly:

```python
import athenspop.model.survey

diaries = athenspop.model.survey.SurveyDataset.from_dataframes(
    trips,
    persons=persons,
    households=households,
)
```

The travel-time function is stored but not called during validation. It is evaluated only when the scheduler needs a duration.

## What validation can and cannot tell you

Passing validation means the tables satisfy the package contract. It does not mean the survey is representative, that every trip was reported, or that the chosen purpose and mode categories are analytically useful. Those questions require information about survey design and the intended analysis.

For exact columns and types, use the [data contract](../reference/data_contract.md). The pandas documentation provides broader background on [dataframe data types](https://pandas.pydata.org/docs/user_guide/basics.html#dtypes) and [missing data](https://pandas.pydata.org/docs/user_guide/missing_data.html).
