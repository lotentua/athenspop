# athenspop

Build reproducible activity-travel schedules and sequence analyses from ordinary travel-diary tables.

Travel surveys usually arrive as rows of trips, departure times, and respondent attributes. Before those records can support a schedule or a sequence comparison, someone has to decide whether the rows form a valid diary, how uncertain departure times should be realized, and how activities and trips should be represented over time. `athenspop` provides those operations as small, typed Python tools that can be used together or independently.

```text
dataframes → validated diaries → schedules → state sequences → distances → clusters
```

Use the package to:

- validate related trip, person, and household tables and inspect all detected issues;
- realize departure windows while respecting trip order, travel time, activity duration, and observation-window constraints;
- convert scheduled diaries into continuous episodes or fixed-interval symbolic sequences;
- compare sequences with configurable optimal-matching costs;
- build and summarize average-linkage hierarchies; and
- create a temporal dendrogram without adopting a package-defined publication style.

Each arrow is optional. A data-quality tool can stop after validation, a simulator can stop after scheduling, and an exploratory analysis can continue through clustering and visualization.

## Installation

`athenspop` requires Python 3.12 or later. Install the core package from a checkout with:

```console
python -m pip install .
```

Add Matplotlib support when you want to create figures:

```console
python -m pip install ".[visualization]"
```

## A first schedule

The smallest input is a pandas `DataFrame` with one row per trip. This example describes a known bus trip from home to work.

```python
import pandas as pd

import athenspop.model.survey
import athenspop.scheduling.engine

trips = pd.DataFrame(
    [
        {
            "household_id": "h1",
            "person_id": "p1",
            "trip_id": "t1",
            "origin": "home",
            "destination": "work",
            "purpose": "work",
            "mode": "bus",
            "departure_second": 28_800,
            "arrival_second": 30_600,
        }
    ]
)

diaries = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
result = athenspop.scheduling.engine.schedule_once(diaries)

trip = result.dataset.diaries[0].trips[0]
print(trip.departure_second, trip.arrival_second)
# 28800 30600
```

Validation happens when the `SurveyDataset` is created. Scheduling preserves the concrete times above; when a row contains a departure window instead, the scheduler draws a feasible departure from that window.

The [getting-started tutorial](docs/getting_started.md) develops this into a two-trip diary and a symbolic state sequence. The [synthetic workflow](docs/workflows/compose_schedule.md) continues through distance calculation, clustering, and visualization.

## Documentation

- [Getting started](docs/getting_started.md) teaches the core workflow with a small example.
- [Concepts](docs/index.md#understand-the-methods) explain the data model, scheduler, and sequence analysis choices.
- [How-to workflows](docs/index.md#follow-a-complete-workflow) show a complete synthetic composition and an analysis of the released Athens data.
- [API reference](docs/api/index.md) lists the public classes and functions by task.
- [Contributing](CONTRIBUTING.md) covers the development environment, tests, style, and documentation workflow.

The repository also includes [513 processed Athens respondent diaries](data/athens/README.md) as a separate CC BY 4.0 data product. The accompanying workflow analyzes reported purpose order without routes, distances, or a geographic crosswalk.

## What athenspop leaves to you

`athenspop` does not recover unreported trips, choose a routing source, estimate population weights, or decide how many clusters are substantively meaningful. Those choices depend on the survey, the research question, and the evidence available to the analysis. The package keeps them visible instead of hiding them inside a fixed pipeline.

## License

The software is available under the [MIT License](LICENSE). Copyright belongs to Theodore Chatziioannou for 2022 and the National Technical University of Athens for 2026. The processed Athens tables have their own [CC BY 4.0 International license](data/athens/LICENSE).
