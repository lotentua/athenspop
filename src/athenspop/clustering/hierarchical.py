# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module uses SciPy to cluster precomputed dissimilarities."""

import dataclasses
import heapq
from collections.abc import Sequence
from typing import Final, cast

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy
import scipy.spatial.distance

import athenspop._sequences
import athenspop.types

#: This type represents a SciPy-compatible hierarchical-linkage matrix.
type LinkageMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
#: This type represents one positive integer cluster label per observation.
type ClusterLabels = np.ndarray[tuple[int], np.dtype[np.int64]]
#: This type represents observation indices in dendrogram leaf order.
type LeafOrder = np.ndarray[tuple[int], np.dtype[np.int64]]
#: This type represents four-point coordinates for each dendrogram branch.
type BranchCoordinates = tuple[tuple[float, float, float, float], ...]
#: This type represents a heap entry selected by node height and identifier.
type _NodeHeapEntry = tuple[float, int, scipy.cluster.hierarchy.ClusterNode]
#: This type represents a heap entry used to assign cut-tree display depths.
type _DisplayNodeHeapEntry = tuple[float, int, "_DisplayNode"]

#: One dendrogram branch requires this number of coordinates.
DENDROGRAM_COORDINATE_COUNT: Final[int] = 4
#: Hierarchical clustering accepts at least this number of observations.
MINIMUM_CLUSTERING_OBSERVATIONS: Final[int] = 2
#: Dissimilarity and linkage matrices must have this rank.
TWO_DIMENSIONAL_ARRAY_RANK: Final[int] = 2
#: This value is the absolute tolerance for dissimilarity invariants.
DISSIMILARITY_ABSOLUTE_TOLERANCE: Final[float] = 1e-12


@dataclasses.dataclass(frozen=True, slots=True)
class DendrogramLayout:
    """This class stores plotting-ready dendrogram geometry.

    Attributes:
        branch_x: These values are the x-coordinates for dendrogram branch polylines.
        branch_y: These values are the y-coordinates for dendrogram branch polylines.
        leaf_indices: These values are the original observation indices in dendrogram
            leaf order.
        leaf_labels: These values are the leaf labels in dendrogram order.
        branch_colors: These values are the branch color labels produced by SciPy.
        leaf_colors: These values are the leaf color labels produced by SciPy.
    """

    branch_x: BranchCoordinates
    branch_y: BranchCoordinates
    leaf_indices: tuple[int, ...]
    leaf_labels: tuple[str, ...]
    branch_colors: tuple[str, ...]
    leaf_colors: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class CutDendrogramNode:
    """This class represents one node in a cut dendrogram.

    Attributes:
        members: These values are the original observation indices in the displayed
            node.
        height: This value is the raw linkage height for the represented SciPy tree
            node.
        normalized_height: This value is `height` divided by the root linkage height.
            A zero-height root produces zero.
        order: This value is the horizontal plotting order. Displayed leaves occupy
            consecutive integer positions, and internal nodes are centered over their
            children.
        depth: This value is the vertical split-order depth. The root has depth zero,
            and later displayed splits have larger depths.
        is_leaf: This value indicates whether the displayed node is a cut cluster or
            singleton leaf instead of an expanded internal split.
        leaf_label: This value is the one-based cut-cluster label for displayed
            leaves, or it is `None` for expanded internal nodes.
        left: This value is the left displayed child when the node is expanded.
        right: This value is the right displayed child when the node is expanded.
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


@dataclasses.dataclass(slots=True)
class _DisplayNode:
    """This mutable node is used to construct a public cut-dendrogram node."""

    linkage_node: scipy.cluster.hierarchy.ClusterNode
    is_leaf: bool
    left: "_DisplayNode | None" = None
    right: "_DisplayNode | None" = None
    order: float = 0.0
    depth: int = 0


def average_linkage(
    dissimilarity_matrix: athenspop.types.DissimilarityMatrix,
    *,
    optimal_ordering: bool = False,
) -> LinkageMatrix:
    """Run average-linkage clustering on a precomputed dissimilarity matrix.

    Args:
        dissimilarity_matrix: This precomputed dissimilarity matrix must be square and
            symmetric.
        optimal_ordering: This value controls whether SciPy reorders leaves to
            minimize adjacent distances.

    Returns:
        The function returns a SciPy linkage matrix in float64 form.
    """
    validated_matrix = _validate_dissimilarity_matrix(dissimilarity_matrix)
    condensed = scipy.spatial.distance.squareform(validated_matrix, checks=False)
    return scipy.cluster.hierarchy.linkage(
        condensed, method="average", optimal_ordering=optimal_ordering
    )


def flat_cluster_labels(
    linkage_matrix: LinkageMatrix, *, n_clusters: int
) -> ClusterLabels:
    """Extract flat cluster labels from a linkage matrix.

    Args:
        linkage_matrix: This value is a SciPy linkage matrix.
        n_clusters: This value is the positive number of flat clusters to extract.

    Returns:
        The function returns one positive integer cluster label per original
        observation.

    Raises:
        ValueError: The function raises this error if `n_clusters` is not positive.
    """
    tree = cut_dendrogram_tree(linkage_matrix, n_clusters=n_clusters)
    labels = np.empty(len(tree.members), dtype=np.int64)
    for leaf in _display_leaves(tree):
        if leaf.leaf_label is None:
            raise RuntimeError(
                "The cut-dendrogram invariant was violated: a displayed leaf has no "
                "label."
            )
        labels[list(leaf.members)] = leaf.leaf_label
    return labels


def leaf_order(linkage_matrix: LinkageMatrix) -> LeafOrder:
    """Return the observation index order used by the hierarchical dendrogram leaves.

    Args:
        linkage_matrix: This value is a SciPy linkage matrix.

    Returns:
        The function returns an integer array of original observation indices in leaf
        order.
    """
    validated_linkage = _validate_linkage_matrix(linkage_matrix)
    return scipy.cluster.hierarchy.leaves_list(validated_linkage).astype(
        np.int64, copy=False
    )


def dendrogram_layout(
    linkage_matrix: LinkageMatrix, *, labels: Sequence[str] | None = None
) -> DendrogramLayout:
    """Return plotting-ready dendrogram coordinates without rendering a figure.

    Args:
        linkage_matrix: This value is a SciPy linkage matrix.
        labels: These optional values label the original observations.

    Returns:
        The function returns dendrogram geometry and labels extracted from SciPy
        without importing matplotlib.
    """
    validated_linkage = _validate_linkage_matrix(linkage_matrix)
    layout = scipy.cluster.hierarchy.dendrogram(
        validated_linkage,
        no_plot=True,
        labels=None if labels is None else list(labels),
    )
    return DendrogramLayout(
        branch_x=_branch_coordinates(
            cast("Sequence[Sequence[float]]", layout["icoord"])
        ),
        branch_y=_branch_coordinates(
            cast("Sequence[Sequence[float]]", layout["dcoord"])
        ),
        leaf_indices=tuple(
            int(leaf) for leaf in cast("Sequence[int]", layout["leaves"])
        ),
        leaf_labels=tuple(str(label) for label in cast("Sequence[str]", layout["ivl"])),
        branch_colors=tuple(
            str(color) for color in cast("Sequence[str]", layout["color_list"])
        ),
        leaf_colors=tuple(
            str(color) for color in cast("Sequence[str]", layout["leaves_color_list"])
        ),
    )


def cluster_size_summary(labels: Sequence[int]) -> pd.DataFrame:
    """Return one row per cluster with the number and share of assigned observations.

    Args:
        labels: These values are positive integer cluster labels.

    Returns:
        The dataframe contains `cluster`, `n_observations`, and `share` columns.

    Raises:
        ValueError: The function raises this error if any label is boolean or not
            positive.
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
                "n_observations": count,
                "share": count / total,
            }
            for label, count in sorted(counts.items())
        ],
        columns=["cluster", "n_observations", "share"],
    )


def cluster_state_distribution(
    sequences: Sequence[Sequence[str]], labels: Sequence[int]
) -> pd.DataFrame:
    """Return state counts and within-cluster shares for clustered sequences.

    Args:
        sequences: These state sequences are assigned to clusters.
        labels: These positive integer cluster labels align with `sequences`.

    Returns:
        The function returns a dataframe with `cluster`, `state`, `count`, and `share`
        columns.

    Raises:
        ValueError: The function raises this error if `sequences` and `labels` have
            different lengths or a label is invalid.
    """
    materialized_sequences = athenspop._sequences.materialize_sequences(sequences)
    label_tuple = _label_tuple(labels)
    if len(materialized_sequences) != len(label_tuple):
        raise ValueError(
            f"`sequences` and `labels` must have the same length, got "
            f"{len(materialized_sequences)} and {len(label_tuple)}."
        )
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


def cluster_time_distribution(
    sequences: Sequence[Sequence[str]], labels: Sequence[int]
) -> pd.DataFrame:
    """Return temporal state shares by cluster and sequence time bin.

    Args:
        sequences: These equal-length state sequences align with `labels`.
        labels: These positive integer cluster labels align with `sequences`.

    Returns:
        The function returns a dataframe with `cluster`, `bin_index`, `state`,
        `count`, and `share` columns.

    Raises:
        ValueError: The function raises this error if `sequences` and `labels` have
            different lengths or the sequences are not equal length.
    """
    materialized_sequences = athenspop._sequences.materialize_equal_length_sequences(
        sequences
    )
    label_tuple = _label_tuple(labels)
    if len(materialized_sequences) != len(label_tuple):
        raise ValueError(
            f"`sequences` and `labels` must have the same length, got "
            f"{len(materialized_sequences)} and {len(label_tuple)}."
        )
    counts: dict[tuple[int, int, str], int] = {}
    totals: dict[tuple[int, int], int] = {}
    for sequence, label in zip(materialized_sequences, label_tuple, strict=True):
        for bin_index, state in enumerate(sequence):
            counts[(label, bin_index, state)] = (
                counts.get((label, bin_index, state), 0) + 1
            )
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


def cut_dendrogram_tree(
    linkage_matrix: LinkageMatrix, *, n_clusters: int
) -> CutDendrogramNode:
    """Cut a linkage tree to a requested number of displayed leaves.

    The cut is constructed top-down by repeatedly splitting the currently displayed
    node with the largest linkage height until the requested number of displayed
    leaves is reached. This gives an explicit tree of the nodes that should be drawn,
    instead of returning full-dendrogram geometry.

    Args:
        linkage_matrix: This value is a SciPy linkage matrix.
        n_clusters: This value is the requested number of displayed clusters.

    Returns:
        The function returns the root node of the displayed cut dendrogram.

    Raises:
        ValueError: The function raises this error if `n_clusters` is not positive or
            `linkage_matrix` is empty.
    """
    validated_linkage = _validate_linkage_matrix(linkage_matrix)
    validated_n_clusters = _validate_positive_cluster_count(n_clusters)
    root = cast(
        "scipy.cluster.hierarchy.ClusterNode",
        scipy.cluster.hierarchy.to_tree(validated_linkage),
    )
    observation_count = int(validated_linkage.shape[0]) + 1
    if validated_n_clusters > observation_count:
        raise ValueError(
            f"`n_clusters` cannot exceed the {observation_count} observations."
        )
    target_clusters = validated_n_clusters
    cut_node_ids = _cut_node_ids(root, target_clusters)
    display_root = _build_display_tree(root, cut_node_ids)
    _assign_orders(display_root, next_order=0)
    _assign_depths(display_root)
    root_height = float(root.dist)
    return _freeze_display_tree(
        display_root, root_height=root_height, next_leaf_label=1
    )[0]


def cophenetic_correlation(
    linkage_matrix: LinkageMatrix,
    dissimilarity_matrix: athenspop.types.DissimilarityMatrix,
) -> float:
    """Return the cophenetic correlation with the source dissimilarities.

    Args:
        linkage_matrix: This value is a SciPy linkage matrix.
        dissimilarity_matrix: This value is the original square precomputed
            dissimilarity matrix.

    Returns:
        The function returns the cophenetic correlation coefficient as a Python
        float.
    """
    validated_linkage = _validate_linkage_matrix(linkage_matrix)
    validated_matrix = _validate_dissimilarity_matrix(dissimilarity_matrix)
    observation_count = int(validated_linkage.shape[0]) + 1
    if validated_matrix.shape[0] != observation_count:
        raise ValueError(
            "`linkage_matrix` and `dissimilarity_matrix` must describe the same "
            f"number of observations, got {observation_count} and "
            f"{validated_matrix.shape[0]}."
        )
    condensed = scipy.spatial.distance.squareform(validated_matrix, checks=False)
    cophenetic_distances = scipy.cluster.hierarchy.cophenet(validated_linkage)
    if (
        condensed.size < 2
        or np.ptp(condensed) == 0.0
        or np.ptp(cophenetic_distances) == 0.0
    ):
        raise ValueError(
            "Cophenetic correlation is undefined for these constant distances."
        )
    return float(np.corrcoef(condensed, cophenetic_distances)[0, 1])


def _label_tuple(labels: Sequence[int]) -> tuple[int, ...]:
    """Validate cluster labels once and materialize them for repeated use."""
    label_tuple = tuple(labels)
    for label in label_tuple:
        if (
            isinstance(label, bool)
            or not isinstance(label, int | np.integer)
            or int(label) <= 0
        ):
            raise ValueError("Cluster labels must be positive integers.")
    return tuple(int(label) for label in label_tuple)


def _validate_dissimilarity_matrix(
    dissimilarity_matrix: athenspop.types.DissimilarityMatrix,
) -> athenspop.types.DissimilarityMatrix:
    """Validate a square, finite, symmetric, non-negative dissimilarity matrix."""
    try:
        matrix = np.asarray(dissimilarity_matrix, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "`dissimilarity_matrix` must contain numeric values."
        ) from error

    if matrix.ndim != TWO_DIMENSIONAL_ARRAY_RANK:
        raise ValueError(
            "`dissimilarity_matrix` must be a two-dimensional square matrix."
        )
    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError("`dissimilarity_matrix` must be square.")
    if matrix.shape[0] < MINIMUM_CLUSTERING_OBSERVATIONS:
        raise ValueError(
            "`dissimilarity_matrix` must contain at least two observations."
        )
    if not np.all(np.isfinite(matrix)):
        raise ValueError("`dissimilarity_matrix` must contain only finite values.")
    if np.any(matrix < 0.0):
        raise ValueError("`dissimilarity_matrix` cannot contain negative distances.")
    if not np.allclose(
        np.diag(matrix),
        0.0,
        rtol=0.0,
        atol=DISSIMILARITY_ABSOLUTE_TOLERANCE,
    ):
        raise ValueError("`dissimilarity_matrix` diagonal must be zero.")
    if not np.allclose(
        matrix,
        matrix.T,
        rtol=0.0,
        atol=DISSIMILARITY_ABSOLUTE_TOLERANCE,
    ):
        raise ValueError("`dissimilarity_matrix` must be symmetric.")

    return cast("athenspop.types.DissimilarityMatrix", matrix)


def _validate_linkage_matrix(linkage_matrix: LinkageMatrix) -> LinkageMatrix:
    """Return a validated SciPy linkage matrix."""
    try:
        matrix = np.asarray(linkage_matrix, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError("`linkage_matrix` must contain numeric values.") from error

    if (
        matrix.ndim != TWO_DIMENSIONAL_ARRAY_RANK
        or matrix.shape[1] != DENDROGRAM_COORDINATE_COUNT
    ):
        raise ValueError(
            "`linkage_matrix` must be a two-dimensional SciPy linkage matrix with "
            "four columns."
        )
    if matrix.shape[0] < 1:
        raise ValueError("`linkage_matrix` must contain at least one merge.")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("`linkage_matrix` must contain only finite values.")
    try:
        scipy.cluster.hierarchy.to_tree(matrix)
    except ValueError as error:
        raise ValueError("`linkage_matrix` is not a valid SciPy linkage.") from error

    return cast("LinkageMatrix", matrix)


def _validate_positive_cluster_count(n_clusters: int) -> int:
    """Return a positive integer cluster count."""
    if isinstance(n_clusters, bool) or not isinstance(n_clusters, int | np.integer):
        raise TypeError(f"`n_clusters` must be a positive integer, got {n_clusters!r}.")
    if int(n_clusters) <= 0:
        raise ValueError(f"`n_clusters` must be positive, got {n_clusters}.")

    return int(n_clusters)


def _cut_node_ids(
    root: scipy.cluster.hierarchy.ClusterNode, target_clusters: int
) -> set[int]:
    """Select displayed leaf node IDs by top-down largest-height splitting."""
    displayed_leaf_ids = {int(root.id)}
    heap: list[_NodeHeapEntry] = []
    if not root.is_leaf():
        heapq.heappush(heap, (-float(root.dist), int(root.id), root))
    while len(displayed_leaf_ids) < target_clusters and heap:
        _, _, node = heapq.heappop(heap)
        node_id = int(node.id)
        if node_id not in displayed_leaf_ids or node.is_leaf():
            continue
        displayed_leaf_ids.remove(node_id)
        left = _left_child(node)
        right = _right_child(node)
        displayed_leaf_ids.add(int(left.id))
        displayed_leaf_ids.add(int(right.id))
        if not left.is_leaf():
            heapq.heappush(heap, (-float(left.dist), int(left.id), left))
        if not right.is_leaf():
            heapq.heappush(heap, (-float(right.dist), int(right.id), right))
    return displayed_leaf_ids


def _display_leaves(root: CutDendrogramNode) -> tuple[CutDendrogramNode, ...]:
    """Return displayed cut leaves in canonical left-to-right label order."""
    if root.is_leaf:
        return (root,)
    left = root.left
    right = root.right
    if left is None or right is None:
        raise RuntimeError(
            "The cut-dendrogram invariant was violated: an expanded node is missing "
            "a child."
        )
    return (*_display_leaves(left), *_display_leaves(right))


def _build_display_tree(
    node: scipy.cluster.hierarchy.ClusterNode, cut_node_ids: set[int]
) -> _DisplayNode:
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
        heapq.heappush(
            heap,
            (-float(root.linkage_node.dist), int(root.linkage_node.id), root),
        )
    next_depth = 0
    while heap:
        _, _, node = heapq.heappop(heap)
        next_depth += 1
        left = _required_child(node.left)
        right = _required_child(node.right)
        left.depth = next_depth
        right.depth = next_depth
        if not left.is_leaf:
            heapq.heappush(
                heap,
                (
                    -float(left.linkage_node.dist),
                    int(left.linkage_node.id),
                    left,
                ),
            )
        if not right.is_leaf:
            heapq.heappush(
                heap,
                (
                    -float(right.linkage_node.dist),
                    int(right.linkage_node.id),
                    right,
                ),
            )


def _freeze_display_tree(
    node: _DisplayNode, *, root_height: float, next_leaf_label: int
) -> tuple[CutDendrogramNode, int]:
    """Convert a mutable display tree into immutable public nodes."""
    normalized_height = (
        0.0 if root_height <= 0 else float(node.linkage_node.dist) / root_height
    )
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
    left, next_after_left = _freeze_display_tree(
        _required_child(node.left),
        root_height=root_height,
        next_leaf_label=next_leaf_label,
    )
    right, next_after_right = _freeze_display_tree(
        _required_child(node.right),
        root_height=root_height,
        next_leaf_label=next_after_left,
    )
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


def _left_child(
    node: scipy.cluster.hierarchy.ClusterNode,
) -> scipy.cluster.hierarchy.ClusterNode:
    """Return a non-null left child from a SciPy cluster node."""
    left = node.get_left()
    if left is None:
        raise ValueError(
            "A non-leaf SciPy cluster node was expected to have a left child."
        )
    return cast("scipy.cluster.hierarchy.ClusterNode", left)


def _right_child(
    node: scipy.cluster.hierarchy.ClusterNode,
) -> scipy.cluster.hierarchy.ClusterNode:
    """Return a non-null right child from a SciPy cluster node."""
    right = node.get_right()
    if right is None:
        raise ValueError(
            "A non-leaf SciPy cluster node was expected to have a right child."
        )
    return cast("scipy.cluster.hierarchy.ClusterNode", right)


def _required_child(node: _DisplayNode | None) -> _DisplayNode:
    """Return a required mutable displayed child."""
    if node is None:
        raise ValueError("Expanded displayed dendrogram nodes must have both children.")
    return node


def _branch_coordinates(values: Sequence[Sequence[float]]) -> BranchCoordinates:
    """Convert SciPy dendrogram coordinate rows into immutable four-float tuples."""
    return tuple(
        (float(value[0]), float(value[1]), float(value[2]), float(value[3]))
        for value in values
    )
