# athenspop

`athenspop` is a typed Python toolkit for composing travel-diary validation, scheduling, sequence analysis, hierarchical clustering, and visualization workflows. Each stage has a small public contract, so a workflow can stop after validation, substitute a project-specific travel-time function, or continue through symbolic sequence analysis.

## Installation

From a source checkout, install the core package with Python 3.12 or later:

```console
pip install .
```

Install the optional Matplotlib integration when a workflow creates figures:

```console
pip install ".[visualization]"
```

## Quick start

The canonical trip table is long form. Each row identifies one movement and supplies exactly one supported timing pattern. This example uses a concrete departure and arrival.

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

dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
result = athenspop.scheduling.engine.schedule_once(dataset)

assert not result.diagnostics.has_errors
assert result.dataset.diaries[0].trips[0].arrival_second == 30_600
```

`athenspop.validation.schema.validate_dataframes` returns all discoverable dataframe diagnostics without constructing the model. `athenspop.scheduling.engine.schedule_once` realizes one feasible schedule, and `athenspop.generation.schedules.generate_schedules` produces repeated seeded realizations. `athenspop.sequence.episodes`, `athenspop.sequence.distance`, `athenspop.clustering.hierarchical`, and the optional `athenspop.visualization.dendrogram` module operate on those scheduled diaries without prescribing a complete analysis pipeline.

## Documentation and examples

The [documentation](https://github.com/lotentua/athenspop/blob/v2/docs/index.md) explains the data contract, scheduling constraints, sequence methods, clustering interpretation, and failure boundaries. Two executable, notebook-like workflows show how to compose the tools:

- [compose_schedule.py](https://github.com/lotentua/athenspop/blob/v2/examples/compose_schedule.py) builds and analyzes a synthetic diary with a caller-supplied travel-time function.
- [analyze_athens.py](https://github.com/lotentua/athenspop/blob/v2/examples/analyze_athens.py) performs an exploratory purpose-chain analysis of the released Athens respondent diaries.

The processed [Athens respondent travel diaries](https://github.com/lotentua/athenspop/blob/v2/data/athens/README.md) are a separate data product licensed under CC BY 4.0 International. The software does not include a routing matrix or geographic zone crosswalk.

## Scope

The package supplies composable operations rather than a policy model or an inference framework. Scheduling reports infeasible diaries instead of silently repairing them. Cluster cuts describe an analyst-selected partition. They do not establish latent population types. Statistical claims remain the responsibility of the workflow that selects a sample, travel-time source, cost model, and interpretation.

## Development

The project uses `uv`, Ruff, ty, pytest, coverage.py, Sphinx, and Hatch. See [CONTRIBUTING.md](https://github.com/lotentua/athenspop/blob/v2/CONTRIBUTING.md) for the complete local checks.

Software is released under the [MIT License](https://github.com/lotentua/athenspop/blob/v2/LICENSE). Theodore Chatziioannou holds the 2022 software copyright, and National Technical University of Athens holds the 2026 software copyright.
