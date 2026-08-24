# athenspop

`athenspop` is a Python library for long-form household travel survey diaries.
It validates `trips`, optional `persons`, and optional `households` dataframes, builds trusted diary objects, schedules feasible trip times, turns diaries into activity and travel sequences, computes sequence dissimilarities, and clusters daily mobility patterns.

The package expects conventional dataframe columns so that students and maintainers can see the data contract directly.
The required trip keys are `household_id`, `person_id`, and `trip_id`; optional respondent and household records attach metadata through the same identifiers.

```python
import pandas as pd

from athenspop import SurveyDataset, schedule_once

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
            "departure_second": 0,
            "arrival_second": 900,
        }
    ]
)

dataset = SurveyDataset.from_dataframes(trips)
scheduled = schedule_once(dataset)
assert scheduled.diaries[0].trips[0].arrival_second == 900
```

Use `validate_dataframes(...)` when you want a complete validation report before constructing the model.
Use `schedule_once(...)` for one feasible realization and `generate_schedules(...)` for repeated realizations from the same validated survey.

Development uses `uv`, Ruff, ty, pytest, and Sphinx.
See `docs/index.md` for the documentation source.

The Athens backend is documented as two separate evidence surfaces: a frozen paper-result reference and a freshly generated migrated reanalysis. The project does not currently claim end-to-end reproduction of the frozen numerical result.
