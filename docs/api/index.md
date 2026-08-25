# API reference

Import domain modules and qualify their symbols. This keeps the stage that owns each operation visible in analysis code:

```python
import athenspop.model.survey
import athenspop.scheduling.engine
import athenspop.sequence.episodes

dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
result = athenspop.scheduling.engine.schedule_once(dataset, seed=2026)
states = athenspop.sequence.episodes.state_sequence_from_diary(
    result.dataset.diaries[0],
    initial_activity_state="home",
)
```

The domain pages below define the public API.

```{toctree}
:maxdepth: 1

model
io
validation
scheduling
generation
sequence
clustering
visualization
```
