# Athens migrated reanalysis walkthrough

This notebook-like page follows the maintained CSuM2026 workflow without hidden notebook state. The snippets expose intermediate objects for study; the module command remains the authoritative end-to-end run.

:::{important}
This workflow is a migrated reanalysis. It is not an end-to-end reproduction of the frozen paper result. See the paper-result page for the evidence boundary and known historical 13-state deviation.
:::

## 1. Verify provenance

```python
from pathlib import Path

from examples.athens.reproduce import verify_athens_sources

source_report = verify_athens_sources(Path.cwd())
assert source_report["all_sources_match"] is True
assert source_report["software"]["uv_lock_sha256"]
```

The report verifies the manuscript, survey, routing and encoder hashes. It also records the lock hash, Git revision, tracked-worktree state, Python version and core dependency versions.

## 2. Convert the 513 wide diaries

```python
from examples.athens.inputs import load_athens_wide_diaries

tables = load_athens_wide_diaries(fixture_travel_time_seconds=None)

assert tables.raw_diaries == 513
assert tables.canonical_trips == 1347
assert (tables.trips["purpose"] == "service").sum() == 9
assert (tables.trips["mode"] == "taxi").sum() == 52
```

The converter emits canonical long-form `trips`, `persons` and `households`. It preserves all seven activities and eight modes; service and taxi are reduced only later for cost construction.

## 3. Validate and build the model

```python
from athenspop import SurveyDataset, validate_dataframes
from examples.athens.travel_time import AthensTravelTimeResolver

travel_time = AthensTravelTimeResolver.from_files(missing_sample_policy="strict")
validation = validate_dataframes(
    tables.trips,
    persons=tables.persons,
    households=tables.households,
    travel_time_function=travel_time,
)
validation.report.raise_if_invalid()

dataset = SurveyDataset.from_dataframes(
    tables.trips,
    persons=tables.persons,
    households=tables.households,
    travel_time_function=travel_time,
)
```

The dataset retains its default travel-time callable, so later scheduling calls do not need to repeat it unless they intentionally override it.

## 4. Schedule reported trips

```python
from athenspop import SchedulingConfig, schedule_once

scheduled = schedule_once(
    dataset,
    seed=2026,
    config=SchedulingConfig(
        min_activity_duration_seconds=1800,
        allow_trips_after_observation_window=True,
    ),
)

assert scheduled.diagnostics.attempted_diaries == 513
assert scheduled.diagnostics.scheduled_diaries == 512
```

The strict lookup excludes person 549 because one routing sample is non-finite. The retained evidence does not establish temporal infeasibility, so the diagnostic and documentation use the narrower missing-routing-data description.

## 5. Impute return-home trips

```python
from examples.athens.imputation import impute_athens_return_home_trips

return_travel_time = AthensTravelTimeResolver.from_files(
    missing_sample_policy="finite_mean"
)
scheduled_with_returns = impute_athens_return_home_trips(
    scheduled,
    travel_time_function=return_travel_time,
    seed=2026,
    min_activity_duration_seconds=1800,
)
```

The imputation stage fits empirical destination-activity durations by purpose, draws an observed duration with a separate `python.random.Random` stream, and adds it to the final reported arrival. Exported synthetic rows include the method and observed predecessor identifiers. The finite-mean return resolver covers six survey zones absent from the routing encoder; the output manifest quantifies every affected trip and diary.

## 6. Build 96-bin sequences

```python
from athenspop.sequence import episodes_from_diary, state_sequence_from_diary
from examples.athens.method import athens_travel_state

diary = scheduled_with_returns.diaries[0]
episodes = episodes_from_diary(
    diary,
    initial_activity_state="home",
    travel_state_labeler=athens_travel_state,
)
states = state_sequence_from_diary(
    diary,
    initial_activity_state="home",
    travel_state_labeler=athens_travel_state,
)

assert episodes[0].start_second == 0
assert episodes[-1].end_second == 86400
assert len(states) == 96
```

Each 15-minute bin takes the state with the greatest total overlap; ties go to the earliest-starting episode.

## 7. Construct costs and dissimilarities

```python
from examples.athens.method import substitution_costs, transition_counts

toy_sequences = (
    ("home@p1", "trip_car@p2", "rigid@p2"),
    ("home@p1", "trip_walk@p2", "rigid@p2"),
)
counts = transition_counts(toy_sequences)
costs = substitution_costs(toy_sequences)

assert counts[("home@p1", "trip_car@p2")] == 1
assert costs[("home@p1", "home@p1")] == 0.0
```

The full run reduces to 36 state-period labels, excludes self-transitions from denominators, applies `2 - P(j|i) - P(i|j)`, and uses indel cost 1 in optimal matching.

## 8. Compare linkage methods and cut the tree

The release artifact compares `single`, `complete`, `average` and `weighted` linkage by cophenetic correlation without optimal ordering. Average must be strictly highest among those four. The displayed hierarchy then uses average linkage with optimal leaf ordering and the same exact ten-leaf cut for tables and figures.

```python
from athenspop.clustering import average_linkage, flat_cluster_labels

# linkage_matrix = average_linkage(dissimilarity, optimal_ordering=True)
# labels = flat_cluster_labels(linkage_matrix, n_clusters=10)
```

## 9. Reproduce the demographic evidence

```python
from examples.athens.demographics import demographic_summary

demographics = demographic_summary(tables.persons)

assert len(demographics.complete_records) == 461
assert len(demographics.associations) == 15
```

The association table uses decade age bins and bias-corrected Cramér’s V. The four highest pairs and values are checked against the literal paper reference before the bivariate figure is accepted.

## 10. Write and validate every artifact

```powershell
uv run python -m examples.athens.reproduce
```

The command writes `examples/athens/output/reanalysis`. Its validator checks source and environment provenance, row ordering, matrix structure, canonical cluster IDs, membership-derived summaries, distribution namespaces, dendrogram references, the 15-state and 36-state-period alphabets, all 15 demographic associations, and the selected paper values.

The generated figures are not copied into Sphinx output. Keeping them under the ignored reanalysis directory makes documentation builds fast and prevents generated binary evidence from being mistaken for source documentation.
