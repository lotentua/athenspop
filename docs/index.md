# athenspop

`athenspop` turns long-form travel-diary tables into validated diaries, feasible schedules, and symbolic activity-travel sequences. Its tools are deliberately composable: use one stage to check a survey, or connect the stages to compare and visualize daily patterns.

Many travel-diary analyses begin with the same practical questions. Do the trip rows form a coherent diary? Which departure times are known, and which are only bounded? Can every trip fit after the previous arrival? What information is lost when a day is divided into fixed intervals? Which costs make two sequences similar? `athenspop` makes each of those decisions explicit and testable.

```text
dataframes → validated diaries → schedules → state sequences → distances → clusters
```

## Start with a working example

The [getting-started tutorial](getting_started.md) builds a two-trip diary, schedules it, and turns it into a sequence. It is the best entry point if you are new to the package.

## Follow a complete workflow

- [Compose a synthetic analysis](workflows/compose_schedule.md) connects validation, scheduling, sequence construction, distance calculation, clustering, and visualization.
- [Explore the Athens diaries](workflows/athens_analysis.md) uses the released data to study reported purpose chains without requiring routing data.

## Understand the methods

- [Data model and validation](concepts/data_model.md) explains why the dataframe boundary exists, how trips become diaries, and how validation issues are reported.
- [Scheduling departure windows](concepts/scheduling.md) explains the reverse and forward passes, including the assumptions required by time-dependent travel times.
- [Sequences and clustering](concepts/sequences.md) explains how temporal resolution, edit costs, and cluster cuts shape an analysis.

## Look up exact behavior

Use the [data contract](reference/data_contract.md) for accepted columns and timing combinations, the [method reference](reference/methods.md) for computational definitions, and the [API reference](api/index.md) for signatures and object documentation.

```{admonition} Analytical responsibility
:class: important

The package validates and transforms the records it receives. It cannot establish that a survey represents a population, infer trips that were never reported, or determine which sequence costs and cluster cut answer a research question. The concept guides show where those choices enter the workflow.
```

```{toctree}
:maxdepth: 2
:caption: Tutorial

getting_started
```

```{toctree}
:maxdepth: 2
:caption: How-to workflows

workflows/compose_schedule
workflows/athens_analysis
```

```{toctree}
:maxdepth: 2
:caption: Explanation

concepts/data_model
concepts/scheduling
concepts/sequences
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/data_contract
reference/methods
api/index
```

```{toctree}
:maxdepth: 1
:caption: Development

development
```
