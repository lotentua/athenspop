# Validation Report

`validate_dataframes(...)` checks the dataframe boundary and returns a `ValidationResult`.

```python
from athenspop import validate_dataframes

result = validate_dataframes(trips, persons=persons, households=households)
if result.report.has_errors:
    for issue in result.report.errors:
        print(issue.code, issue.message)
```

The report contains `errors`, `warnings`, `invalid_rows`, `invalid_chains`, `summary`, `has_errors`, `has_warnings`, and `raise_if_invalid()`.

Validation is staged.
A missing key, invalid second value, or unsupported timing pattern blocks later row checks for that row so users do not get a noisy cascade of duplicate errors.
Independent rows and joins are still checked in the same report.

Hard errors mean the data cannot be loaded into the internal model.
Warnings mean the data can be loaded, but the user should inspect a methodological or data-quality issue.

Current warnings include:

- `origin_mismatch`: a trip starts somewhere other than the previous trip's destination.
- `short_activity_duration`: the gap between two concrete trips is shorter than the default scheduler's minimum activity duration.

Validation does not enforce built-in purpose names, mode names, home-location columns, or return-home rules.
Those are study assumptions, so examples should document and test them locally.

Use `SurveyDataset.from_dataframes(...)` when you want validation and model construction in one step.
It calls `raise_if_invalid()` for you.
