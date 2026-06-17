#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from collections.abc import Iterable
from typing import Any, Final, Literal, TypeAlias

import numpy as np
import scipy as sp
import seaborn as sns

ClusterLabels: TypeAlias = np.ndarray[tuple[Any], np.dtype[np.int32]]

DistanceMatrix2: TypeAlias = np.ndarray[tuple[Any, Any], np.dtype[np.float64]]
DistanceMatrix1: TypeAlias = np.ndarray[tuple[Any], np.dtype[np.float64]]

LinkageMatrix: TypeAlias = np.ndarray[tuple[Any, Literal[4]], np.dtype[np.float64]]
# TODO: Remove the option to select methods that do not make sense in non-Euclidean, non-metric space.
LinkageMethod: TypeAlias = Literal[
    "single", "complete", "average", "weighted", "centroid", "median", "ward"
]

_ALL_LINKAGE_METHODS: Final[list[LinkageMethod]] = [
    "single",
    "complete",
    "average",
    "weighted",
    # "centroid",
    # "median",
    # "ward"
]


# TODO: Support other clustering methods.
def compute_flat_clusters(
    linkage_matrix: LinkageMatrix, num_clusters: int
) -> ClusterLabels:
    labels = sp.cluster.hierarchy.fcluster(
        linkage_matrix, t=num_clusters, criterion="maxclust"
    )
    # Label clusters from 0 to be compatible with scikit-learn.
    labels -= labels.min()

    return labels


def hierarchical_clustering(
    distance_matrix: DistanceMatrix2,
    method: LinkageMethod | Literal["auto"] = "auto",
    validate_dmat_struct: bool = True,
    optimize_leaf_order: bool = False,
) -> tuple[DistanceMatrix1, LinkageMatrix]:
    distance = sp.spatial.distance.squareform(
        distance_matrix, checks=validate_dmat_struct
    )

    if method == "auto":
        method, cophenets = _compute_optimal_linkage_method(
            distance, methods=_ALL_LINKAGE_METHODS
        )
    linkage = sp.cluster.hierarchy.linkage(
        distance, method=method, optimal_ordering=optimize_leaf_order
    )

    return distance, linkage


def _compute_optimal_linkage_method(
    distance_matrix: DistanceMatrix1, methods: Iterable[LinkageMethod]
) -> tuple[LinkageMethod, dict[LinkageMethod, float]]:
    cophenets = {}
    for method in methods:
        linkage = sp.cluster.hierarchy.linkage(distance_matrix, method=method)
        cophenets[method] = _cophenetic_correlation_coefficient(
            distance_matrix, linkage
        )

    return max(cophenets, key=cophenets.get), cophenets


def _cophenetic_correlation_coefficient(
    distance_matrix: DistanceMatrix1, linkage_matrix: LinkageMatrix
) -> np.float64:
    return sp.cluster.hierarchy.cophenet(linkage_matrix, distance_matrix)[0]


def plot_clustered_distance_matrix(
    distance_matrix: DistanceMatrix2,
    linkage_matrix: LinkageMatrix,
    cbar_kws: dict[str, Any] | None = None,
    xticklabels: bool = False,
    yticklabels: bool = False,
    **kwargs,
) -> sns.matrix.ClusterGrid:
    if cbar_kws is None:
        cbar_kws = {"label": "Edit Distance"}

    return sns.clustermap(
        distance_matrix,
        cbar_kws=cbar_kws,
        row_linkage=linkage_matrix,
        col_linkage=linkage_matrix,
        xticklabels=xticklabels,
        yticklabels=yticklabels,
        **kwargs,
    )
