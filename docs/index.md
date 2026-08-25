# athenspop

`athenspop` is a typed Python package for composing travel-diary validation, schedule realization, state-sequence construction, sequence comparison, clustering, and visualization. Each stage exposes ordinary Python objects so that an analysis can use only the stages it needs.

The package accepts long-form pandas tables at one validation boundary. It then represents each respondent as an immutable ordered diary. Departure windows can be realized subject to diary constraints, scheduled diaries can be discretized into activity and travel states, and those sequences can be compared with optimal matching and grouped with average-linkage clustering.

```{admonition} This note defines the package scope.
:class: important

`athenspop` supplies composable analytical operations. It does not infer missing trips, routes, travel times, population weights, or a statistically preferred number of clusters. Those inputs and analytical decisions remain explicit.
```

Start with [Getting started](getting_started.md) for a compact tour. The [synthetic scheduling workflow](workflows/compose_schedule.md) follows the full validation-to-visualization composition. The [Athens exploratory analysis](workflows/athens_analysis.md) uses the released processed tables without requiring geographic or routing data.

```{toctree}
:maxdepth: 2
:caption: Use athenspop.

getting_started
concepts/data_model
concepts/scheduling
concepts/sequences
workflows/compose_schedule
workflows/athens_analysis
```

```{toctree}
:maxdepth: 2
:caption: Consult the reference.

reference/data_contract
reference/methods
api/index
development
```
