"""Hierarchical clustering helpers for precomputed dissimilarity matrices."""

from typing import Final

from athenspop.clustering.hierarchical import (
    ClusterLabels,
    CutDendrogramNode,
    DendrogramLayout,
    LeafOrder,
    LinkageMatrix,
    average_linkage,
    cluster_size_summary,
    cluster_state_distribution,
    cluster_time_distribution,
    cophenetic_correlation,
    cut_dendrogram_tree,
    dendrogram_layout,
    flat_cluster_labels,
    leaf_order,
)

__all__: Final[tuple[str, ...]] = (
    "ClusterLabels",
    "CutDendrogramNode",
    "DendrogramLayout",
    "LeafOrder",
    "LinkageMatrix",
    "average_linkage",
    "cluster_size_summary",
    "cluster_state_distribution",
    "cluster_time_distribution",
    "cophenetic_correlation",
    "cut_dendrogram_tree",
    "dendrogram_layout",
    "flat_cluster_labels",
    "leaf_order",
)
