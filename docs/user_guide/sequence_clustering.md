# Sequence Analysis And Clustering

The package sequence layer is generic:

- Build continuous activity and trip episodes that partition an observation window.
- Discretize the window into fixed-width bins.
- Assign each bin to the state with maximum overlap duration, using earliest-start tie breaking.
- Compute optimal-matching dissimilarities from an explicit substitution-cost dictionary.
- Cluster with average-linkage hierarchical clustering on the precomputed dissimilarity matrix.

```python
from athenspop.clustering import average_linkage, cluster_size_summary, cluster_state_distribution, cluster_time_distribution, cut_dendrogram_tree, dendrogram_layout, flat_cluster_labels, leaf_order
from athenspop.sequence import dissimilarity_matrix, state_sequence_from_diary

sequences = [
    state_sequence_from_diary(
        diary,
        initial_activity_state="home",
        travel_state_labeler=lambda trip: f"trip:{trip.mode}",
    )
    for diary in scheduled.diaries
]
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
temporal_distribution = cluster_time_distribution(sequences, tuple(labels.tolist()))
dendrogram_order = leaf_order(linkage_matrix)
layout = dendrogram_layout(linkage_matrix)
cut_tree = cut_dendrogram_tree(linkage_matrix, n_clusters=10)
```

`cluster_sizes` counts diaries per cluster. `state_distribution` counts sequence states within each cluster and reports within-cluster shares. `temporal_distribution` reports state shares by cluster and sequence bin. `dendrogram_order` is the row order used by the hierarchical clustering leaves. `layout` stores branch coordinates, leaf labels, and colors from SciPy's no-plot dendrogram path, so custom plotting code can render a full dendrogram when needed. `cut_tree` stores the pruned hierarchy at the selected number of clusters, so examples can draw cut dendrograms without putting file writers in the library.
