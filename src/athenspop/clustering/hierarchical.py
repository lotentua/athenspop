"""SciPy-backed average-linkage clustering for precomputed dissimilarities."""

from collections.abc import Sequence
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import cast

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import ClusterNode, cophenet, dendrogram, fcluster, leaves_list, linkage, to_tree
from scipy.spatial.distance import squareform

type DissimilarityMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
type LinkageMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
type ClusterLabels = np.ndarray[tuple[int], np.dtype[np.int64]]
type LeafOrder = np.ndarray[tuple[int], np.dtype[np.int64]]
type BranchCoordinates = tuple[tuple[float, float, float, float], ...]
type _NodeHeapEntry = tuple[float, int, ClusterNode]
type _DisplayNodeHeapEntry = tuple[float, int, "_DisplayNode"]

DENDROGRAM_COORDINATE_COUNT = 4


@dataclass(frozen=True, slots=True)
class DendrogramLayout:
    """Plotting-ready dendrogram geometry produced without importing matplotlib.

    Attributes:
        branch_x: X coordinates for dendrogram branch polylines.
        branch_y: Y coordinates for dendrogram branch polylines.
        leaf_indices: Original observation indices in dendrogram leaf order.
        leaf_labels: Leaf labels in dendrogram order.
        branch_colors: Branch color labels produced by SciPy.
        leaf_colors: Leaf color labels produced by SciPy.
    """

    branch_x: BranchCoordinates
    branch_y: BranchCoordinates
    leaf_indices: tuple[int, ...]
    leaf_labels: tuple[str, ...]
    branch_colors: tuple[str, ...]
    leaf_colors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CutDendrogramNode:
    """One displayed node in a dendrogram cut at a requested number of clusters.

    Attributes:
        members: Original observation indices contained in the displayed node.
        height: Raw linkage height for the represented SciPy tree node.
        normalized_height: `height` divided by the root linkage height, with zero roots reported as zero.
        order: Horizontal order for plotting, where displayed leaves occupy consecutive integer positions and internal nodes are centered over their children.
        depth: Vertical split-order depth, where the root has depth zero and later displayed splits receive larger depths.
        is_leaf: Whether this displayed node is a cut cluster or singleton leaf rather than an expanded internal split.
        leaf_label: One-based cut-cluster label for displayed leaves, or `None` for expanded internal nodes.
        left: Left displayed child when the node is expanded.
        right: Right displayed child when the node is expanded.
    """

    members: tuple[int, ...]
    height: float
    normalized_height: float
    order: float
    depth: int
    is_leaf: bool
    leaf_label: int | None
    left: "CutDendrogramNode | None"
    right: "CutDendrogramNode | None"


@dataclass(slots=True)
class _DisplayNode:
    """Mutable construction node used before freezing a public `CutDendrogramNode`."""

    linkage_node: ClusterNode
    is_leaf: bool
    left: "_DisplayNode | None" = None
    right: "_DisplayNode | None" = None
    order: float = 0.0
    depth: int = 0


def average_linkage(dissimilarity_matrix: DissimilarityMatrix, *, optimal_ordering: bool = False) -> LinkageMatrix:
    """Run average-linkage hierarchical clustering on a square precomputed dissimilarity matrix.

    Args:
        dissimilarity_matrix: Square symmetric precomputed dissimilarity matrix.
        optimal_ordering: Whether SciPy should reorder leaves to minimize adjacent distances.

    Returns:
        SciPy linkage matrix in float64 form.
    """
    condensed = squareform(dissimilarity_matrix, checks=True)
    return linkage(condensed, method="average", optimal_ordering=optimal_ordering)


def flat_cluster_labels(linkage_matrix: LinkageMatrix, *, n_clusters: int) -> ClusterLabels:
    """Extract flat cluster labels from a linkage matrix.

    Args:
        linkage_matrix: SciPy linkage matrix.
        n_clusters: Positive number of flat clusters to extract.

    Returns:
        One positive integer cluster label per original observation.

    Raises:
        ValueError: If `n_clusters` is not positive.
    """
    if n_clusters <= 0:
        raise ValueError(f"`n_clusters` must be positive, got {n_clusters}.")
    labels = fcluster(linkage_matrix, t=n_clusters, criterion="maxclust")
    return labels.astype(np.int64, copy=False)


def leaf_order(linkage_matrix: LinkageMatrix) -> LeafOrder:
    """Return the observation index order used by the hierarchical dendrogram leaves.

    Args:
        linkage_matrix: SciPy linkage matrix.

    Returns:
        Integer array of original observation indices in leaf order.
    """
    return leaves_list(linkage_matrix).astype(np.int64, copy=False)


def dendrogram_layout(linkage_matrix: LinkageMatrix, labels: None | Sequence[str] = None) -> DendrogramLayout:
    """Return plotting-ready dendrogram coordinates without rendering a figure.

    Args:
        linkage_matrix: SciPy linkage matrix.
        labels: Optional labels for original observations.

    Returns:
        Dendrogram geometry and labels extracted from SciPy without importing matplotlib.
    """
    layout = dendrogram(
        linkage_matrix,
        no_plot=True,
        labels=None if labels is None else list(labels),
    )
    return DendrogramLayout(
        branch_x=_branch_coordinates(cast("Sequence[Sequence[float]]", layout["icoord"])),
        branch_y=_branch_coordinates(cast("Sequence[Sequence[float]]", layout["dcoord"])),
        leaf_indices=tuple(int(leaf) for leaf in cast("Sequence[int]", layout["leaves"])),
        leaf_labels=tuple(str(label) for label in cast("Sequence[str]", layout["ivl"])),
        branch_colors=tuple(str(color) for color in cast("Sequence[str]", layout["color_list"])),
        leaf_colors=tuple(str(color) for color in cast("Sequence[str]", layout["leaves_color_list"])),
    )


def cluster_size_summary(labels: Sequence[int]) -> pd.DataFrame:
    """Return one row per cluster with the number and share of assigned observations.

    Args:
        labels: Positive integer cluster labels.

    Returns:
        Dataframe with `cluster`, `n_diaries`, and `share` columns.

    Raises:
        ValueError: If any label is boolean or not positive.
    """
    label_tuple = _label_tuple(labels)
    total = len(label_tuple)
    counts: dict[int, int] = {}
    for label in label_tuple:
        counts[label] = counts.get(label, 0) + 1
    return pd.DataFrame(
        [
            {
                "cluster": label,
                "n_diaries": count,
                "share": count / total,
            }
            for label, count in sorted(counts.items())
        ],
        columns=["cluster", "n_diaries", "share"],
    )


def cluster_state_distribution(sequences: Sequence[Sequence[str]], labels: Sequence[int]) -> pd.DataFrame:
    """Return state counts and within-cluster shares for clustered sequences.

    Args:
        sequences: State sequences assigned to clusters.
        labels: Positive integer cluster labels aligned with `sequences`.

    Returns:
        Dataframe with `cluster`, `state`, `count`, and `share` columns.

    Raises:
        ValueError: If `sequences` and `labels` have different lengths or a label is invalid.
    """
    materialized_sequences = tuple(tuple(sequence) for sequence in sequences)
    label_tuple = _label_tuple(labels)
    if len(materialized_sequences) != len(label_tuple):
        raise ValueError(f"`sequences` and `labels` must have the same length, got {len(materialized_sequences)} and {len(label_tuple)}.")
    counts: dict[tuple[int, str], int] = {}
    totals: dict[int, int] = {}
    for sequence, label in zip(materialized_sequences, label_tuple, strict=True):
        for state in sequence:
            counts[(label, state)] = counts.get((label, state), 0) + 1
            totals[label] = totals.get(label, 0) + 1
    return pd.DataFrame(
        [
            {
                "cluster": label,
                "state": state,
                "count": count,
                "share": count / totals[label],
            }
            for (label, state), count in sorted(counts.items())
        ],
        columns=["cluster", "state", "count", "share"],
    )


def cluster_time_distribution(sequences: Sequence[Sequence[str]], labels: Sequence[int]) -> pd.DataFrame:
    """Return temporal state shares by cluster and sequence time bin.

    Args:
        sequences: Equal-length state sequences aligned with `labels`.
        labels: Positive integer cluster labels aligned with `sequences`.

    Returns:
        Dataframe with `cluster`, `bin_index`, `state`, `count`, and `share` columns.

    Raises:
        ValueError: If `sequences` and `labels` have different lengths, or if the sequences are not equal length.
    """
    materialized_sequences = _materialize_sequences(sequences)
    label_tuple = _label_tuple(labels)
    if len(materialized_sequences) != len(label_tuple):
        raise ValueError(f"`sequences` and `labels` must have the same length, got {len(materialized_sequences)} and {len(label_tuple)}.")
    counts: dict[tuple[int, int, str], int] = {}
    totals: dict[tuple[int, int], int] = {}
    for sequence, label in zip(materialized_sequences, label_tuple, strict=True):
        for bin_index, state in enumerate(sequence):
            counts[(label, bin_index, state)] = counts.get((label, bin_index, state), 0) + 1
            totals[(label, bin_index)] = totals.get((label, bin_index), 0) + 1
    return pd.DataFrame(
        [
            {
                "cluster": cluster,
                "bin_index": bin_index,
                "state": state,
                "count": count,
                "share": count / totals[(cluster, bin_index)],
            }
            for (cluster, bin_index, state), count in sorted(counts.items())
        ],
        columns=["cluster", "bin_index", "state", "count", "share"],
    )


def cut_dendrogram_tree(linkage_matrix: LinkageMatrix, *, n_clusters: int) -> CutDendrogramNode:
    """Return the displayed hierarchy after cutting a linkage tree to `n_clusters` leaves.

    The cut is constructed top-down by repeatedly splitting the currently displayed node with the largest linkage height until the requested number of displayed leaves is reached. This gives an explicit tree of the nodes that should be drawn, instead of returning full-dendrogram geometry.

    Args:
        linkage_matrix: SciPy linkage matrix.
        n_clusters: Requested number of displayed clusters.

    Returns:
        Root node of the displayed cut dendrogram.

    Raises:
        ValueError: If `n_clusters` is not positive or if `linkage_matrix` is empty.
    """
    if n_clusters <= 0:
        raise ValueError(f"`n_clusters` must be positive, got {n_clusters}.")
    if linkage_matrix.shape[0] == 0:
        raise ValueError("A cut dendrogram requires a linkage matrix with at least one merge.")
    root = cast("ClusterNode", to_tree(linkage_matrix))
    target_clusters = min(n_clusters, int(linkage_matrix.shape[0]) + 1)
    cut_node_ids = _cut_node_ids(root, target_clusters)
    display_root = _build_display_tree(root, cut_node_ids)
    _assign_orders(display_root, next_order=0)
    _assign_depths(display_root)
    root_height = float(root.dist)
    return _freeze_display_tree(display_root, root_height=root_height, next_leaf_label=1)[0]


def cophenetic_correlation(linkage_matrix: LinkageMatrix, dissimilarity_matrix: DissimilarityMatrix) -> float:
    """Return the cophenetic correlation coefficient for a linkage and its source dissimilarities.

    Args:
        linkage_matrix: SciPy linkage matrix.
        dissimilarity_matrix: Original square precomputed dissimilarity matrix.

    Returns:
        Cophenetic correlation coefficient as a Python float.
    """
    condensed = squareform(dissimilarity_matrix, checks=True)
    result = cophenet(linkage_matrix, condensed)[0]
    return float(result)


def _label_tuple(labels: Sequence[int]) -> tuple[int, ...]:
    """Validate cluster labels once and materialize them for repeated use."""
    label_tuple = tuple(labels)
    for label in label_tuple:
        if isinstance(label, bool) or label <= 0:
            raise ValueError("Cluster labels must be positive integers.")
    return label_tuple


def _materialize_sequences(sequences: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    """Materialize and validate equal-length state sequences."""
    materialized = tuple(tuple(str(state) for state in sequence) for sequence in sequences)
    if not materialized:
        raise ValueError("At least one state sequence is required.")
    sequence_length = len(materialized[0])
    for sequence in materialized:
        if len(sequence) != sequence_length:
            raise ValueError("All state sequences must have the same length.")
    return materialized


def _cut_node_ids(root: ClusterNode, target_clusters: int) -> set[int]:
    """Select displayed leaf node IDs by top-down largest-height splitting."""
    displayed_leaf_ids = {int(root.id)}
    heap: list[_NodeHeapEntry] = []
    if not root.is_leaf():
        heappush(heap, (-float(root.dist), int(root.id), root))
    while len(displayed_leaf_ids) < target_clusters and heap:
        _, _, node = heappop(heap)
        node_id = int(node.id)
        if node_id not in displayed_leaf_ids or node.is_leaf():
            continue
        displayed_leaf_ids.remove(node_id)
        left = _left_child(node)
        right = _right_child(node)
        displayed_leaf_ids.add(int(left.id))
        displayed_leaf_ids.add(int(right.id))
        if not left.is_leaf():
            heappush(heap, (-float(left.dist), int(left.id), left))
        if not right.is_leaf():
            heappush(heap, (-float(right.dist), int(right.id), right))
    return displayed_leaf_ids


def _build_display_tree(node: ClusterNode, cut_node_ids: set[int]) -> _DisplayNode:
    """Build the mutable displayed tree from selected cut-node IDs."""
    if int(node.id) in cut_node_ids or node.is_leaf():
        return _DisplayNode(linkage_node=node, is_leaf=True)
    left = _build_display_tree(_left_child(node), cut_node_ids)
    right = _build_display_tree(_right_child(node), cut_node_ids)
    return _DisplayNode(linkage_node=node, is_leaf=False, left=left, right=right)


def _assign_orders(node: _DisplayNode, *, next_order: int) -> int:
    """Assign left-to-right displayed leaf orders and centered internal orders."""
    if node.is_leaf:
        node.order = float(next_order)
        return next_order + 1
    left = _required_child(node.left)
    right = _required_child(node.right)
    next_after_left = _assign_orders(left, next_order=next_order)
    next_after_right = _assign_orders(right, next_order=next_after_left)
    node.order = (left.order + right.order) / 2.0
    return next_after_right


def _assign_depths(root: _DisplayNode) -> None:
    """Assign split-order depths to displayed nodes."""
    root.depth = 0
    heap: list[_DisplayNodeHeapEntry] = []
    if not root.is_leaf:
        heappush(heap, (-float(root.linkage_node.dist), int(root.linkage_node.id), root))
    next_depth = 0
    while heap:
        _, _, node = heappop(heap)
        next_depth += 1
        left = _required_child(node.left)
        right = _required_child(node.right)
        left.depth = next_depth
        right.depth = next_depth
        if not left.is_leaf:
            heappush(heap, (-float(left.linkage_node.dist), int(left.linkage_node.id), left))
        if not right.is_leaf:
            heappush(heap, (-float(right.linkage_node.dist), int(right.linkage_node.id), right))


def _freeze_display_tree(node: _DisplayNode, *, root_height: float, next_leaf_label: int) -> tuple[CutDendrogramNode, int]:
    """Convert a mutable display tree into immutable public nodes."""
    normalized_height = 0.0 if root_height <= 0 else float(node.linkage_node.dist) / root_height
    members = tuple(int(member) for member in node.linkage_node.pre_order())
    if node.is_leaf:
        return (
            CutDendrogramNode(
                members=members,
                height=float(node.linkage_node.dist),
                normalized_height=normalized_height,
                order=node.order,
                depth=node.depth,
                is_leaf=True,
                leaf_label=next_leaf_label,
                left=None,
                right=None,
            ),
            next_leaf_label + 1,
        )
    left, next_after_left = _freeze_display_tree(_required_child(node.left), root_height=root_height, next_leaf_label=next_leaf_label)
    right, next_after_right = _freeze_display_tree(_required_child(node.right), root_height=root_height, next_leaf_label=next_after_left)
    return (
        CutDendrogramNode(
            members=members,
            height=float(node.linkage_node.dist),
            normalized_height=normalized_height,
            order=node.order,
            depth=node.depth,
            is_leaf=False,
            leaf_label=None,
            left=left,
            right=right,
        ),
        next_after_right,
    )


def _left_child(node: ClusterNode) -> ClusterNode:
    """Return a non-null left child from a SciPy cluster node."""
    left = node.get_left()
    if left is None:
        raise ValueError("Expected a non-leaf SciPy cluster node to have a left child.")
    return cast("ClusterNode", left)


def _right_child(node: ClusterNode) -> ClusterNode:
    """Return a non-null right child from a SciPy cluster node."""
    right = node.get_right()
    if right is None:
        raise ValueError("Expected a non-leaf SciPy cluster node to have a right child.")
    return cast("ClusterNode", right)


def _required_child(node: _DisplayNode | None) -> _DisplayNode:
    """Return a required mutable displayed child."""
    if node is None:
        raise ValueError("Expanded displayed dendrogram nodes must have both children.")
    return node


def _branch_coordinates(values: Sequence[Sequence[float]]) -> BranchCoordinates:
    """Convert SciPy dendrogram coordinate rows into immutable four-float tuples."""
    return tuple(_four_float_tuple(value) for value in values)


def _four_float_tuple(values: Sequence[float]) -> tuple[float, float, float, float]:
    """Validate and coerce one SciPy dendrogram coordinate row."""
    if len(values) != DENDROGRAM_COORDINATE_COUNT:
        raise ValueError(f"SciPy dendrogram branch coordinates must have four values, got {len(values)}.")
    return (float(values[0]), float(values[1]), float(values[2]), float(values[3]))
