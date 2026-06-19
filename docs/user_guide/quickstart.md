# Quickstart

Install the project in a development checkout with `uv sync`.

Start with a canonical `trips` dataframe.
`persons` and `households` are optional, but when provided they attach metadata through the same `household_id` and `person_id` keys.

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
trip = scheduled.diaries[0].trips[0]

assert trip.departure_second == 0
assert trip.arrival_second == 900
```

`departure_second = 0` is valid.
It means exactly the diary time origin; choose and document that origin before converting clock times to seconds.

Use `validate_dataframes(...)` directly when you want a diagnostic report before loading the model.

```python
from athenspop import validate_dataframes

result = validate_dataframes(trips)
result.report.raise_if_invalid()
```

The internal model assumes successful validation.
Keep raw parsing, clock conversion, column naming, and file reading at the boundary.
