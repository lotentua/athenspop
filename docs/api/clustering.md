# Clustering API

Clustering operations apply average linkage to validated precomputed dissimilarities and expose cuts, geometry, summaries, and cophenetic correlation. A requested flat cut is an analyst choice.

```{eval-rst}
.. automodule:: athenspop.clustering.hierarchical
   :members: ClusterLabels, CutDendrogramNode, DendrogramLayout, LeafOrder,
      LinkageMatrix, average_linkage, cluster_size_summary,
      cluster_state_distribution, cluster_time_distribution,
      cophenetic_correlation, cut_dendrogram_tree, dendrogram_layout,
      flat_cluster_labels, leaf_order
```
