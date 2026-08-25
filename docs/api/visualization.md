# Visualization API

Visualization returns Matplotlib figures without writing files. The temporal dendrogram combines a normalized-height cut tree with aligned state-share axes for each cut cluster. Dimensions, typography, default colors, tree-line width, and unspecified styling inherit the active stylesheet. Quantitative axes and bar geometry remain fixed so the display preserves its meaning.

```{eval-rst}
.. automodule:: athenspop.visualization.dendrogram
   :members: TemporalDendrogramPlotStyle,
      plot_cut_dendrogram_state_distribution
```
