"""SciPy-backed average-linkage clustering for precomputed dissimilarities."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cophenet, dendrogram, fcluster, leaves_list, linkage
from scipy.spatial.distance import squareform

type DissimilarityMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
type LinkageMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
type ClusterLabels = np.ndarray[tuple[int], np.dtype[np.int64]]
type LeafOrder = np.ndarray[tuple[int], np.dtype[np.int64]]
type BranchCoordinates = tuple[tuple[float, float, float, float], ...]

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


def _branch_coordinates(values: Sequence[Sequence[float]]) -> BranchCoordinates:
    """Convert SciPy dendrogram coordinate rows into immutable four-float tuples."""
    return tuple(_four_float_tuple(value) for value in values)


def _four_float_tuple(values: Sequence[float]) -> tuple[float, float, float, float]:
    """Validate and coerce one SciPy dendrogram coordinate row."""
    if len(values) != DENDROGRAM_COORDINATE_COUNT:
        raise ValueError(f"SciPy dendrogram branch coordinates must have four values, got {len(values)}.")
    return (float(values[0]), float(values[1]), float(values[2]), float(values[3]))
