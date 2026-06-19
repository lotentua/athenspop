# Athens Workflow Walkthrough

This page is the notebook-like walkthrough for the maintained CSuM2026 example. It explains the workflow step by step while keeping the executable contract in `examples.athens.reproduce`, so the example does not depend on hidden notebook state.

## 1. Check The Source Files

The full workflow starts by verifying `CSuM2026.pdf`, `CSuM2026.zip`, and the required LaTeX and figure members inside the ZIP against the hashes recorded in `examples/athens/docs/athens_method_contract.md`.

```python
from pathlib import Path

from examples.athens.reproduce import verify_athens_sources

source_report = verify_athens_sources(Path.cwd())

assert source_report["all_sources_match"] is True
```

The generated artifact is `examples/athens/output/full/source_hashes.json`.

## 2. Convert The Migrated Survey Source

The raw migrated survey file is still wide because it preserves the historical paper input, but the maintained converter immediately turns it into canonical long-form `trips`, `persons`, and `households` tables.

```python
from examples.athens.inputs import load_athens_wide_diaries

tables = load_athens_wide_diaries(fixture_travel_time_seconds=None)

assert tables.raw_diaries == 513
assert tables.canonical_trips == 1347
assert len(tables.persons) == 513
assert len(tables.households) == 513
```

The full writer saves these tables as `data/trips.csv`, `data/persons.csv`, and `data/households.csv` under `examples/athens/output/full`.

## 3. Validate And Build The Canonical Model

The example uses the same dataframe boundary as ordinary library users. Validation is intentionally front-loaded: once `SurveyDataset.from_dataframes(...)` succeeds, the downstream code can treat the internal model as complete and coherent.

```python
from athenspop import SurveyDataset, validate_dataframes
from examples.athens.travel_time import AthensTravelTimeResolver

travel_time = AthensTravelTimeResolver.from_files(missing_sample_policy="strict")
validation = validate_dataframes(tables.trips, persons=tables.persons, households=tables.households, travel_time_function=travel_time)

validation.report.raise_if_invalid()
dataset = SurveyDataset.from_dataframes(tables.trips, persons=tables.persons, households=tables.households, travel_time_function=travel_time)
```

The full writer saves `validation_report.json`, and it must contain no hard errors.

## 4. Schedule Reported Trips

The paper analysis path uses the strict migrated travel-time resolver for reported trips. This preserves the single legacy routing-infeasible diary, `household_id=549; person_id=549`, and yields the 512-diary analysis set.

```python
from athenspop import SchedulingConfig, schedule_once

scheduled = schedule_once(dataset, seed=2026, config=SchedulingConfig(min_activity_duration_seconds=1800, allow_trips_after_observation_window=True), travel_time_function=travel_time)

assert scheduled.diagnostics.attempted_diaries == 513
assert scheduled.diagnostics.scheduled_diaries == 512
assert scheduled.diagnostics.infeasible_diaries == ("household_id=549; person_id=549",)
```

The full writer saves `scheduling_diagnostics.json`, `scheduled_trips.csv`, and `diary_summary.csv`.

## 5. Impute Missing Return-Home Trips

The Athens-specific return-home policy belongs in `examples.athens.imputation`, not in the generic package API.
It fits empirical return-home departure samples from observed return-home trips, samples a feasible synthetic return after the final reported activity when required, and keeps recreation-ending diaries open as described in the method contract.

```python
from examples.athens.imputation import impute_athens_return_home_trips

return_travel_time = AthensTravelTimeResolver.from_files(missing_sample_policy="finite_mean")
scheduled_with_returns = impute_athens_return_home_trips(scheduled, travel_time_function=return_travel_time, seed=2026, min_activity_duration_seconds=1800)
```

The exported `scheduled_trips.csv` contains `is_imputed_return_home`, `imputation_method`, and `observed_last_trip_id` so synthetic rows can be audited separately from reported survey trips.

## 6. Build Episodes And State Sequences

Scheduled diaries are converted into continuous episodes over `[0, 86400]`, then discretized into 96 bins of 900 seconds. State assignment follows maximum temporal overlap with earliest-start tie breaking.

```python
from athenspop.sequence import episodes_from_diary, state_sequence_from_diary
from examples.athens.method import athens_travel_state

episodes = episodes_from_diary(scheduled_with_returns.diaries[0], initial_activity_state="home", travel_state_labeler=athens_travel_state)
states = state_sequence_from_diary(scheduled_with_returns.diaries[0], initial_activity_state="home", travel_state_labeler=athens_travel_state)

assert episodes[0].start_second == 0
assert episodes[-1].end_second == 86400
assert len(states) == 96
```

The full writer saves `episodes.csv`, `state_sequences.npy`, and `compound_state_sequences.npy`.

## 7. Compute Athens Costs And Dissimilarities

The Athens-specific cost construction reduces activities and modes, combines states with four demand periods, excludes self-transitions from transition denominators, builds `c(i, j) = 2 - P(j|i) - P(i|j)`, and uses indel cost `1` for optimal matching.

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

The full writer performs this on the 512-diary compound sequences and saves `transition_counts.csv`, `substitution_costs.csv`, and `dissimilarity_matrix.npy`. The maintained full command is the authoritative way to run this stage on the paper dataset.

## 8. Cluster And Summarize

The clustering stage uses average linkage on the precomputed optimal-matching dissimilarity matrix, then writes the 10-cluster presentation and interpretation tables.

```python
from athenspop.clustering import average_linkage, flat_cluster_labels

# In the full workflow, `dissimilarity` is the 512 by 512 matrix loaded from the previous stage.
# linkage = average_linkage(dissimilarity)
# labels = flat_cluster_labels(linkage, n_clusters=10)
```

The full writer saves `linkage_average.npy`, `cluster_labels.csv`, `cluster_summaries.csv`, `cluster_state_distribution.csv`, `cluster_time_distribution.csv`, `dendrogram_layout.json`, and `figures/dendrogram.svg`.

## 9. Write Demographic Summaries

Demographic summaries are generated from the 461 person records complete across gender, age, education, employment status, monthly income, and car ownership.

```python
from examples.athens.demographics import demographic_summary

demographics = demographic_summary(tables.persons)

assert len(demographics.complete_records) == 461
```

The full writer saves `demographics/complete_records.csv`, `demographics/marginal_demographics.csv`, `demographics/bivariate_demographics.csv`, `figures/marginal_demographics.svg`, and `figures/bivariate_demographics.svg`.

## 10. Run The Maintained Full Workflow

For ordinary reproduction, run the maintained artifact command instead of copying the snippets above into a separate script.

```powershell
uv run python -m examples.athens.reproduce
```

The command writes `examples/athens/output/full`, validates the source hashes, validates the generated artifact set against `examples/athens/docs/athens_output_manifest.md`, and fails if a release-relevant count, shape, manifest path, matrix property, or imputed-row provenance check no longer matches the documented baseline.

Generated SVG figures are not copied into the built documentation.
They remain reproducible output paths under `examples/athens/output/full/figures` so documentation builds stay fast and do not depend on the 512-diary optimal-matching run.
