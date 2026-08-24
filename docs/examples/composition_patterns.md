# Composition patterns

The same validated long-form tables can support several workflows. Compose only the stages needed for the question at hand.

| Goal | Composition |
| --- | --- |
| Inspect data quality | `validate_dataframes` |
| Realize one feasible diary schedule | `SurveyDataset.from_dataframes` → `schedule_once` |
| Explore timing uncertainty | `SurveyDataset.from_dataframes` → `generate_schedules` |
| Explore daily-pattern groups | schedule → state sequences → dissimilarities → clustering |
| Reanalyse a named study | generic stages plus study-specific input, cost, imputation, and artifact policy |

## Validate without scheduling

Validation is useful on its own during data preparation.

```python
from athenspop import validate_dataframes

result = validate_dataframes(trips, persons=persons, households=households)
if result.report.has_errors:
    for issue in result.report.errors:
        print(issue.code, issue.message)
```

## Realize one schedule or an ensemble

Build the trusted model once. Use one draw for a concrete schedule or multiple independent draws to inspect timing sensitivity.

```python
from athenspop import SurveyDataset, generate_schedules, schedule_once

dataset = SurveyDataset.from_dataframes(trips)
one_schedule = schedule_once(dataset, seed=42)
five_schedules = generate_schedules(dataset, 5, seed=42)
```

Departure-window rows can instead use a study-owned travel-time callable. Supplying it while constructing the dataset makes it the default for later scheduling calls.

```python
dataset = SurveyDataset.from_dataframes(
    trips,
    travel_time_function=travel_time_seconds,
)
scheduled = schedule_once(dataset, seed=42)
```

## Add exploratory sequence clustering

Sequence construction and clustering are separate layers. This keeps the state vocabulary and substitution costs explicit study decisions.

```python
from athenspop import average_linkage, flat_cluster_labels
from athenspop.sequence import dissimilarity_matrix, state_sequence_from_diary

sequences = tuple(
    state_sequence_from_diary(diary, initial_activity_state="home")
    for diary in one_schedule.diaries
)
states = {state for sequence in sequences for state in sequence}
costs = {
    (source, target): float(source != target) for source in states for target in states
}
distances = dissimilarity_matrix(sequences, substitution_cost=costs)
hierarchy = average_linkage(distances)
clusters = flat_cluster_labels(hierarchy, n_clusters=3)
```

The Athens walkthrough composes the same generic stages with paper-specific source verification, routing, return-home imputation, state reduction, demographics, figures, and artifact validation. Those policies remain in `examples/athens`; they are examples of composition, not defaults imposed by `athenspop`.
