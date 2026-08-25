# Compose a synthetic activity-travel analysis

This workflow connects every main stage of `athenspop`:

```text
tables → diaries → schedules → sequences → distances → hierarchy → figure
```

You will build three simple home-based diaries, give each travel mode a fixed 15-minute duration, schedule the departure windows, and compare the resulting activity-travel sequences. The data are synthetic so the example stays self-contained and each analytical choice remains visible.

The executable version is [`examples/compose_schedule.py`](https://github.com/lotentua/athenspop/blob/v2/examples/compose_schedule.py).

## 1. Provide travel times

Scheduling needs a duration for every trip. A duration may already be present in the trip row, or a function may calculate it from origin, destination, mode, and departure time.

The example uses the same 15-minute duration for every movement:

```{literalinclude} ../../examples/compose_schedule.py
:language: python
:pyobject: travel_time
```

A real application can connect this boundary to observed durations, a calibrated model, or a routing service. The callable contract and its FIFO assumption are explained in [Time-dependent travel times](../concepts/scheduling.md#time-dependent-travel-times).

## 2. Create three diaries

Each respondent leaves home, visits one activity, and returns home. Their destinations and modes differ so the final sequences contain both shared and contrasting states.

```{literalinclude} ../../examples/compose_schedule.py
:language: python
:pyobject: example_tables
```

The first departure window extends to second 8,000, but the return trip must leave by second 9,000. With a 15-minute trip and a 15-minute minimum activity, the scheduler tightens the first latest departure to second 7,200. This is a small, visible example of the reverse pass described in [Scheduling departure windows](../concepts/scheduling.md).

## 3. Compose the analysis

The complete function:

1. builds a {py:class}`athenspop.model.survey.SurveyDataset` from the two dataframes;
2. calls {py:func}`athenspop.scheduling.engine.schedule_once` with a reproducible seed;
3. converts every successful diary with {py:func}`athenspop.sequence.episodes.state_sequence_from_diary`;
4. calculates {py:func}`athenspop.sequence.distance.dissimilarity_matrix` using unit edit costs;
5. builds an {py:func}`athenspop.clustering.hierarchical.average_linkage` hierarchy; and
6. returns a figure from {py:func}`athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution`.

```{literalinclude} ../../examples/compose_schedule.py
:language: python
:pyobject: build_figure
```

The diagnostic check is part of the composition, not incidental error handling. Sequence construction should not continue silently with a subset of respondents when scheduling has excluded a diary.

```{figure} ../_static/composed-schedule.svg
:alt: A five-node hierarchy contains a pair of state-distribution panels at its root, internal branch, and three leaves. Travel states appear above activity states in every node.

The three synthetic schedules at a three-cluster cut. Every node combines the hierarchy with its own temporal summary: travel modes are above and activity purposes are below. The root describes all three schedules, the internal branch describes its two descendants, and each leaf describes one selected cluster. Membership illustrates the mechanics only and has no population interpretation.
```

The plotting function owns the tree layout, panel borders, tick visibility, legend placement, and bar geometry. Figure dimensions, typography, default colors, tree-line width, and unspecified styling follow the active Matplotlib configuration.

## 4. Adapt one boundary at a time

The example is deliberately easy to modify:

- Replace `travel_time` while leaving validation and scheduling unchanged.
- Change `interval_seconds` to study the effect of temporal resolution.
- Replace unit substitution costs with costs justified by the states and research question.
- Stop after scheduling if the desired output is a concrete diary.
- Stop after episode construction for continuous time-allocation summaries.
- Compare several cluster cuts before interpreting a hierarchy.

Run the complete example from the repository root:

```console
python examples/compose_schedule.py
```

The script displays the figure. Its reusable functions return data or Matplotlib objects and leave file export to the caller.
