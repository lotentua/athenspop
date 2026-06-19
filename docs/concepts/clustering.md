# Clustering

Clustering groups diaries from a precomputed sequence dissimilarity matrix.

`average_linkage(...)` converts a square dissimilarity matrix into a SciPy linkage matrix. `flat_cluster_labels(...)` cuts the hierarchy into a requested number of clusters. `leaf_order(...)` returns the dendrogram leaf order.

Summary helpers turn labels and sequences into dataframe outputs: cluster sizes, within-cluster state distributions, temporal state distributions, cut-tree nodes, and plotting-ready dendrogram geometry.

The clustering core returns both numerical clustering outputs and object-level display data.
Use `cut_dendrogram_tree(...)` and `cluster_time_distribution(...)` when an example needs to inspect or customize a cut dendrogram whose displayed nodes contain temporal state distributions.
Use `athenspop.visualization.plot_cut_dendrogram_state_distribution(...)` when a generic Matplotlib figure is enough.
The library still does not write figure files; examples and applications decide whether and where to save returned figures.
