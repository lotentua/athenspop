# Build your first diary schedule

This tutorial starts with two rows in a pandas dataframe and ends with a half-hour activity-travel sequence. Along the way, you will see where validation ends, where scheduling begins, and how to handle a diary that cannot be scheduled.

The example uses fixed travel durations, so it runs without a routing service or external data.

## Install the package

From a source checkout, install `athenspop` with Python 3.12 or later:

```console
python -m pip install .
```

The plotting dependency is not needed for this tutorial. Install `.[visualization]` when you reach the [visualization workflow](workflows/compose_schedule.md).

## Describe a day as trip rows

`athenspop` accepts [pandas dataframes](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html). Each trip row identifies a movement, its destination purpose and mode, and one supported description of its timing.

Here, one respondent travels from home to work in the morning and returns in the evening. Each departure may occur anywhere inside a 30-minute window, while each bus ride lasts 30 minutes.

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

diaries = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
```

{py:meth}`athenspop.model.survey.SurveyDataset.from_dataframes` checks column types, identifiers, timing combinations, trip order, and relationships between tables. It returns immutable model objects only after the input satisfies that contract.

```python
diary = diaries.diaries[0]
print(diary.person_id, len(diary.trips))
# p1 2
```

If you are building a user interface and want to display every detected issue at once, call {py:func}`athenspop.validation.schema.validate_dataframes` instead. The [validation guide](concepts/data_model.md#inspect-problems-before-building-a-model) shows that workflow.

## Realize the departure windows

Scheduling chooses concrete departure seconds that respect the reported windows, travel durations, trip order, and configured minimum activity duration.

```python
import athenspop.scheduling.engine

result = athenspop.scheduling.engine.schedule_once(diaries, seed=2026)
```

The seed makes the random choices reproducible. The returned {py:class}`athenspop.scheduling.engine.ScheduledSurveyDataset` keeps successful diaries in `result.dataset` and structured failures in `result.diagnostics`.

```python
if result.diagnostics.has_errors:
    for issue in result.diagnostics.issues:
        print(issue.code, issue.message)
else:
    for trip in result.dataset.diaries[0].trips:
        print(trip.trip_id, trip.departure_second, trip.arrival_second)
```

Always inspect the diagnostics before assuming that the scheduled dataset contains every input diary. The [scheduling explanation](concepts/scheduling.md) shows how future trips can tighten an earlier departure window and why the scheduler works in two passes.

## Turn the schedule into states

A schedule is continuous in time. Many sequence methods instead need one state per fixed interval. The next call labels each 30-minute interval as an activity or a trip.

```python
import athenspop.sequence.episodes

scheduled_diary = result.dataset.diaries[0]
states = athenspop.sequence.episodes.state_sequence_from_diary(
    scheduled_diary,
    initial_activity_state="home",
    window_start_second=27_000,
    window_end_second=64_800,
    interval_seconds=1_800,
)

print(len(states), sorted(set(states)))
# 21 ['home', 'trip_bus', 'work']
```

This window runs from 07:30 through 18:00, so it produces 21 half-hour states. The result contains home, work, and bus travel without requiring a separate state table.

{py:func}`athenspop.sequence.episodes.state_sequence_from_diary` first creates continuous episodes and then assigns each interval to the state that occupies it for the longest time. A shorter interval preserves more timing detail; a longer interval produces a smaller, coarser sequence. The [sequence guide](concepts/sequences.md) explains that tradeoff.

## Where to go next

- Adapt a real survey with [Data model and validation](concepts/data_model.md).
- Learn how departure windows are tightened in [Scheduling departure windows](concepts/scheduling.md).
- Compare several diaries in [Sequences and clustering](concepts/sequences.md).
- Run the complete [synthetic composition workflow](workflows/compose_schedule.md).
- Look up signatures in the [API reference](api/index.md).
