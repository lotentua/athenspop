# Sequence Analysis And Clustering

The package sequence layer is generic:

- Build continuous activity and trip episodes that partition an observation window.
- Discretize the window into fixed-width bins.
- Assign each bin to the state with maximum overlap duration, using earliest-start tie breaking.
- Compute optimal-matching dissimilarities from an explicit substitution-cost dictionary.
- Cluster with average-linkage hierarchical clustering on the precomputed dissimilarity matrix.

```python
from athenspop.clustering import average_linkage, cluster_size_summary, cluster_state_distribution, dendrogram_layout, flat_cluster_labels, leaf_order
from athenspop.sequence import dissimilarity_matrix, state_sequence_from_diary
from athenspop.visualization import write_cut_dendrogram_distribution_svg

sequences = [state_sequence_from_diary(diary) for diary in scheduled.diaries]
states = sorted({state for sequence in sequences for state in sequence})
costs = {
    (source, target): 0.0 if source == target else 1.0
    for source in states
    for target in states
}
matrix = dissimilarity_matrix(sequences, substitution_cost=costs)
linkage_matrix = average_linkage(matrix)
labels = flat_cluster_labels(linkage_matrix, n_clusters=10)
cluster_sizes = cluster_size_summary(tuple(labels.tolist()))
state_distribution = cluster_state_distribution(sequences, tuple(labels.tolist()))
dendrogram_order = leaf_order(linkage_matrix)
layout = dendrogram_layout(linkage_matrix)
write_cut_dendrogram_distribution_svg(linkage_matrix, sequences, "dendrogram.svg", n_clusters=10)
```

`cluster_sizes` counts diaries per cluster. `state_distribution` counts sequence states within each cluster and reports within-cluster shares. `dendrogram_order` is the row order used by the hierarchical clustering leaves. `layout` stores branch coordinates, leaf labels, and colors from SciPy's no-plot dendrogram path, so custom plotting code can render a full dendrogram when needed. `write_cut_dendrogram_distribution_svg` writes a pruned dendrogram at the selected number of clusters; each displayed node contains two stacked temporal distributions, one for travel-mode states and one for activity-purpose states.
