# Clustering

Clustering groups diaries from a precomputed sequence dissimilarity matrix.

`average_linkage(...)` converts a square dissimilarity matrix into a SciPy linkage matrix. `flat_cluster_labels(...)` cuts the hierarchy into a requested number of clusters. `leaf_order(...)` returns the dendrogram leaf order.

Summary helpers turn labels and sequences into dataframe outputs: cluster sizes, within-cluster state distributions, and plotting-ready dendrogram geometry.

The clustering core intentionally does not depend on plotting libraries. The separate visualization layer can render a cut dendrogram SVG where each displayed node is a temporal distribution of activity-purpose and travel-mode states.
