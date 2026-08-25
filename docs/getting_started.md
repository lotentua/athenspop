# Getting started

From a source checkout, install the core package with Python 3.12 or later:

```console
python -m pip install .
```

Install the optional plotting dependency when an analysis needs the visualization API:

```console
python -m pip install ".[visualization]"
```

## Build a trusted dataset

The smallest useful input is a long-form trip table. Each row identifies one movement and supplies exactly one supported timing pattern.

```python
import pandas as pd

import athenspop.model.survey

trips = pd.DataFrame(
    [
        {
            "household_id": "h1",
            "person_id": "p1",
            "trip_id": "t1",
            "trip_sequence": 1,
            "origin": "home",
            "destination": "work",
            "purpose": "work",
            "mode": "bus",
            "earliest_departure_second": 28_800,
            "latest_departure_second": 30_600,
            "travel_time_seconds": 1_800,
        },
        {
            "household_id": "h1",
            "person_id": "p1",
            "trip_id": "t2",
            "trip_sequence": 2,
            "origin": "work",
            "destination": "home",
            "purpose": "home",
            "mode": "bus",
            "earliest_departure_second": 61_200,
            "latest_departure_second": 63_000,
            "travel_time_seconds": 1_800,
        },
    ]
)

dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
```

`athenspop.model.survey.SurveyDataset.from_dataframes` validates and normalizes the table before it constructs model objects. Use `athenspop.validation.schema.validate_dataframes` directly when an application needs to display all collected diagnostics instead of raising an exception.

## Schedule and discretize the diary

```python
import athenspop.scheduling.engine
import athenspop.sequence.episodes

scheduled = athenspop.scheduling.engine.schedule_once(dataset, seed=2026)
if scheduled.diagnostics.has_errors:
    for issue in scheduled.diagnostics.issues:
        print(issue.code, issue.message)
else:
    states = athenspop.sequence.episodes.state_sequence_from_diary(
        scheduled.dataset.diaries[0],
        initial_activity_state="home",
        interval_seconds=1_800,
    )
```

Successful diaries are available through `scheduled.dataset`. Infeasible diaries are excluded from that dataset and described by `scheduled.diagnostics`.

## Choose the next stage

- Read [Data model and validation](concepts/data_model.md) before adapting an external survey.
- Read [Scheduling](concepts/scheduling.md) before supplying a time-dependent travel-time function.
- Read [Sequences and clustering](concepts/sequences.md) before choosing state definitions or costs.
- Follow [Compose a synthetic schedule](workflows/compose_schedule.md) for a complete executable workflow.
