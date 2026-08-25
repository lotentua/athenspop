# Visualization API

The temporal dendrogram places a normalized-height cut tree above aligned state-share panels. Quantitative axes and unit-width bar geometry are fixed; dimensions, typography, default colors, tree-line width, and other presentation choices follow Matplotlib configuration.

The function returns a Matplotlib figure and never writes a file. See [Summarizing and visualizing a cut](../concepts/sequences.md#summarizing-and-visualizing-a-cut) and the [synthetic workflow](../workflows/compose_schedule.md) for context.

```{eval-rst}
.. automodule:: athenspop.visualization.dendrogram
   :members: TemporalDendrogramPlotStyle,
      plot_cut_dendrogram_state_distribution
```
