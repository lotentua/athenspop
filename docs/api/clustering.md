# Clustering API

The clustering layer validates a precomputed dissimilarity matrix, builds an average-linkage hierarchy, exposes its geometry, and summarizes caller-selected cuts.

A cut count is an analytical choice rather than an estimate produced by the package. See [From distances to a hierarchy](../concepts/sequences.md#from-distances-to-a-hierarchy) for interpretation.

```{eval-rst}
.. automodule:: athenspop.clustering.hierarchical
   :members: BranchCoordinates, ClusterLabels, CutDendrogramNode,
      DendrogramLayout, LeafOrder, LinkageMatrix, average_linkage,
      cluster_size_summary,
      cluster_state_distribution, cluster_time_distribution,
      cophenetic_correlation, cut_dendrogram_tree, dendrogram_layout,
      flat_cluster_labels, leaf_order
```
