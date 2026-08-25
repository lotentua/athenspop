# Visualization API

The temporal dendrogram arranges a selected cut as one split-order tree. Every displayed node contains two stacked temporal state-distribution panels. Panel placement, hidden ticks, visible borders, legend placement, and unit-width bar geometry are fixed; dimensions, typography, default colors, tree-line width, and unspecified styling follow Matplotlib configuration.

The function returns a Matplotlib figure and never writes a file. See [Summarizing and visualizing a cut](../concepts/sequences.md#summarizing-and-visualizing-a-cut) and the [synthetic workflow](../workflows/compose_schedule.md) for context.

```{eval-rst}
.. automodule:: athenspop.visualization.dendrogram
   :members: TemporalDendrogramPlotStyle,
      plot_cut_dendrogram_state_distribution
```
