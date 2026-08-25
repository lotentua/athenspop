# API reference

The API is organized by the stage of the analysis rather than by one required pipeline. The table below points from a common task to its main entry point.

| Task | API page | Main entry point |
| --- | --- | --- |
| Build immutable diaries | [Model](model.md) | {py:meth}`athenspop.model.survey.SurveyDataset.from_dataframes` |
| Convert civil clock columns | [Input conversion](io.md) | {py:func}`athenspop.io.clock.convert_clock_columns` |
| Inspect dataframe problems | [Validation](validation.md) | {py:func}`athenspop.validation.schema.validate_dataframes` |
| Realize one schedule | [Scheduling](scheduling.md) | {py:func}`athenspop.scheduling.engine.schedule_once` |
| Generate repeated schedules | [Generation](generation.md) | {py:func}`athenspop.generation.schedules.generate_schedules` |
| Build episodes and sequences | [Sequence](sequence.md) | {py:func}`athenspop.sequence.episodes.state_sequence_from_diary` |
| Compare sequences | [Sequence](sequence.md) | {py:func}`athenspop.sequence.distance.dissimilarity_matrix` |
| Build and summarize a hierarchy | [Clustering](clustering.md) | {py:func}`athenspop.clustering.hierarchical.average_linkage` |
| Plot a temporal cut | [Visualization](visualization.md) | {py:func}`athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution` |

Examples throughout the documentation import modules and qualify their symbols. This makes ownership visible in analysis code and avoids an oversized package namespace.

Use the [getting-started tutorial](../getting_started.md) to learn the workflow and the [concept guides](../index.md#understand-the-methods) to understand the analytical choices. This section is the factual reference for signatures, attributes, return values, and exceptions.

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
