# Compose a synthetic schedule

This workflow combines every analytical stage on a self-contained three-respondent dataset. It is structured as notebook cells, but the same code is maintained as [`examples/compose_schedule.py`](https://github.com/lotentua/athenspop/blob/main/examples/compose_schedule.py).

The values are deliberately synthetic. The result demonstrates interface composition and does not represent observed travel behavior.

## 1. Define the travel-time boundary

The example uses a deterministic 15-minute duration for every movement. A real application can replace this function with any callable that satisfies the documented contract.

```{literalinclude} ../../examples/compose_schedule.py
:language: python
:pyobject: travel_time
```

## 2. Build long-form tables

The table builder creates two departure-window trips for each respondent and attaches one metadata value to each person.

```{literalinclude} ../../examples/compose_schedule.py
:language: python
:pyobject: example_tables
```

Each diary begins at `home`, visits one activity, and returns home. The explicit `trip_sequence` establishes order. The departure windows and constant travel time leave enough dwell time for the configured minimum activity duration.

## 3. Compose the operations

The complete function validates the dataframes through `SurveyDataset`, schedules one realization, turns successful diaries into 30-minute state sequences, calculates unit-cost optimal-matching dissimilarities, performs average-linkage clustering, and returns a two-cluster temporal dendrogram.

```{literalinclude} ../../examples/compose_schedule.py
:language: python
:pyobject: build_figure
```

The error branch is material: later operations must not silently proceed when scheduling has excluded a diary. In a production workflow, report `scheduled.diagnostics.issues` with the source records instead of replacing the diagnostic with a generic exception.

```{figure} ../_static/composed-schedule.svg
:alt: The figure shows a cut dendrogram for three synthetic scheduled diaries. Each displayed node contains a temporal distribution of activity and trip states.

This figure shows the composed synthetic result. It inherits dimensions, fonts, lines, and colors from the active Matplotlib stylesheet.
```

## 4. Adapt the composition

Change one analytical boundary at a time:

- Supply observed durations instead of a travel-time function when those durations belong to the input data.
- Change `initial_activity_state`, `interval_seconds`, or the travel-state labeler when the research question requires another state representation.
- Replace unit substitution costs with a documented domain cost matrix.
- Select and justify a cluster cut outside the package; `n_clusters=2` here only makes the three-row example visible.
- Omit clustering and visualization when schedules or episodes are the desired output.

The source example calls `plt.show()` only in its script entry point. Reusable functions return data or a figure and leave display and export to the caller.
