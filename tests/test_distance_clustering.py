# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Sequence-dissimilarity and clustering contracts."""

from typing import cast

import numpy as np
import pytest

import athenspop.clustering.hierarchical
import athenspop.sequence.distance


def test_optimal_matching_uses_substitution_when_cheaper_than_indels() -> None:
    """Choose a low-cost substitution instead of an insertion and deletion pair."""
    costs = {("A", "B"): 0.25, ("B", "A"): 0.25}
    assert (
        athenspop.sequence.distance.optimal_matching_dissimilarity(
            ("A",), ("B",), substitution_cost=costs, indel_cost=1.0
        )
        == 0.25
    )


def test_optimal_matching_uses_indels_for_shifted_equal_length_sequences() -> None:
    """Use insertion and deletion edits when substitutions cost more."""
    costs = {
        ("A", "B"): 2.0,
        ("B", "A"): 2.0,
        ("A", "C"): 2.0,
        ("C", "A"): 2.0,
        ("B", "C"): 2.0,
        ("C", "B"): 2.0,
    }
    assert (
        athenspop.sequence.distance.optimal_matching_dissimilarity(
            ("A", "B"), ("B", "C"), substitution_cost=costs, indel_cost=1.0
        )
        == 2.0
    )


@pytest.mark.parametrize("indel_cost", [0.0, -1.0, float("nan"), float("inf")])
def test_optimal_matching_rejects_invalid_indel_costs(
    indel_cost: float,
) -> None:
    """Reject nonpositive and nonfinite insertion-deletion costs."""
    with pytest.raises(ValueError, match="finite positive"):
        athenspop.sequence.distance.optimal_matching_dissimilarity(
            ("A",),
            ("B",),
            substitution_cost={("A", "B"): 1.0},
            indel_cost=indel_cost,
        )


def test_optimal_matching_rejects_non_numeric_indel_cost() -> None:
    """Reject booleans as insertion-deletion costs despite integer subclassing."""
    with pytest.raises(TypeError, match="finite positive"):
        athenspop.sequence.distance.optimal_matching_dissimilarity(
            ("A",), ("B",), substitution_cost={("A", "B"): 1.0}, indel_cost=True
        )


@pytest.mark.parametrize("substitution_cost", [-1.0, float("nan"), float("inf")])
def test_optimal_matching_rejects_invalid_substitution_costs(
    substitution_cost: float,
) -> None:
    """Reject negative and nonfinite substitution costs."""
    with pytest.raises(ValueError, match="finite non-negative"):
        athenspop.sequence.distance.optimal_matching_dissimilarity(
            ("A",), ("B",), substitution_cost={("A", "B"): substitution_cost}
        )


def test_optimal_matching_rejects_non_numeric_substitution_cost() -> None:
    """Reject booleans as substitution costs despite integer subclassing."""
    with pytest.raises(TypeError, match="finite non-negative"):
        athenspop.sequence.distance.optimal_matching_dissimilarity(
            ("A",), ("B",), substitution_cost={("A", "B"): True}
        )


@pytest.mark.parametrize(
    ("invalid_sequence", "error_type"),
    [
        ((), ValueError),
        (("",), TypeError),
        (cast("tuple[str, ...]", (1,)), TypeError),
    ],
)
def test_optimal_matching_rejects_invalid_state_sequences(
    invalid_sequence: tuple[str, ...],
    error_type: type[Exception],
) -> None:
    """Reject empty sequences and states without non-empty string labels."""
    with pytest.raises(error_type):
        athenspop.sequence.distance.optimal_matching_dissimilarity(
            invalid_sequence,
            ("A",),
            substitution_cost={},
        )


def test_dissimilarity_matrix_is_symmetric_with_zero_diagonal() -> None:
    """Return a square float matrix with symmetry and an exact zero diagonal."""
    sequences = (("A", "A", "B"), ("A", "B", "B"), ("B", "A", "B"))
    costs = {
        ("A", "A"): 0.0,
        ("A", "B"): 1.0,
        ("B", "A"): 1.0,
        ("B", "B"): 0.0,
    }
    matrix = athenspop.sequence.distance.dissimilarity_matrix(
        sequences, substitution_cost=costs
    )
    assert matrix.shape == (3, 3)
    assert matrix.dtype == np.float64
    np.testing.assert_allclose(matrix, matrix.T)
    np.testing.assert_allclose(np.diag(matrix), np.zeros(3))


@pytest.mark.parametrize(
    ("invalid_sequences", "error_type"),
    [
        ((), ValueError),
        (((),), ValueError),
        ((("",),), TypeError),
        (cast("tuple[tuple[str, ...], ...]", ((1,),)), TypeError),
    ],
)
def test_dissimilarity_matrix_rejects_invalid_state_sequences(
    invalid_sequences: tuple[tuple[str, ...], ...],
    error_type: type[Exception],
) -> None:
    """Reject missing sequences and states without non-empty string labels."""
    with pytest.raises(error_type):
        athenspop.sequence.distance.dissimilarity_matrix(
            invalid_sequences,
            substitution_cost={},
        )


def test_dissimilarity_matrix_matches_scalar_optimal_matching_reference() -> None:
    """Match the scalar recurrence for variable-length symbolic sequences."""
    sequences = (
        ("A", "B", "C"),
        ("A", "C"),
        ("B", "A", "C", "C"),
        ("C",),
    )
    states = ("A", "B", "C")
    costs = {
        (source, target): 0.0 if source == target else 1.25
        for source in states
        for target in states
    }
    matrix = athenspop.sequence.distance.dissimilarity_matrix(
        sequences, substitution_cost=costs, indel_cost=1.0
    )
    expected = np.zeros((len(sequences), len(sequences)), dtype=np.float64)
    for row_index, first in enumerate(sequences):
        for column_index, second in enumerate(sequences):
            expected[row_index, column_index] = (
                athenspop.sequence.distance.optimal_matching_dissimilarity(
                    first, second, substitution_cost=costs, indel_cost=1.0
                )
            )
    np.testing.assert_allclose(matrix, expected)


def test_dissimilarity_matrix_rejects_invalid_cost_domains() -> None:
    """Apply scalar cost-domain validation during pairwise matrix construction."""
    with pytest.raises(ValueError, match="finite positive"):
        athenspop.sequence.distance.dissimilarity_matrix(
            (("A",), ("B",)),
            substitution_cost={("A", "B"): 1.0, ("B", "A"): 1.0},
            indel_cost=float("nan"),
        )

    with pytest.raises(ValueError, match="finite non-negative"):
        athenspop.sequence.distance.dissimilarity_matrix(
            (("A",), ("B",)),
            substitution_cost={("A", "B"): -1.0, ("B", "A"): -1.0},
        )


def test_average_linkage_accepts_precomputed_dissimilarity_matrix() -> None:
    """Cluster a valid matrix and expose compatible labels, order, and correlation."""
    matrix = np.array(
        [[0.0, 1.0, 4.0], [1.0, 0.0, 5.0], [4.0, 5.0, 0.0]], dtype=np.float64
    )
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(matrix)
    assert linkage_matrix.shape == (2, 4)
    assert linkage_matrix[0, 0] == 0
    assert linkage_matrix[0, 1] == 1
    assert linkage_matrix[0, 2] == 1.0
    assert linkage_matrix[0, 3] == 2
    labels = athenspop.clustering.hierarchical.flat_cluster_labels(
        linkage_matrix, n_clusters=2
    )
    assert labels.shape == (3,)
    assert labels[0] == labels[1]
    assert labels[2] != labels[0]
    order = athenspop.clustering.hierarchical.leaf_order(linkage_matrix)
    assert order.shape == (3,)
    assert sorted(order.tolist()) == [0, 1, 2]
    assert (
        0.0
        <= athenspop.clustering.hierarchical.cophenetic_correlation(
            linkage_matrix, matrix
        )
        <= 1.0
    )


@pytest.mark.parametrize(
    "matrix",
    [
        np.array([0.0, 1.0], dtype=np.float64),
        np.zeros((2, 2, 1), dtype=np.float64),
        np.zeros((2, 3), dtype=np.float64),
        np.zeros((1, 1), dtype=np.float64),
        np.array([[0.0, -1.0], [-1.0, 0.0]], dtype=np.float64),
        np.array([[0.0, np.nan], [np.nan, 0.0]], dtype=np.float64),
        np.array([[0.0, np.inf], [np.inf, 0.0]], dtype=np.float64),
        np.array([[0.0, 1.0], [2.0, 0.0]], dtype=np.float64),
        np.array([[1.0, 1.0], [1.0, 0.0]], dtype=np.float64),
        np.array([[1e-9, 1.0], [1.0, 0.0]], dtype=np.float64),
        np.array([[0.0, 100.0], [100.0005, 0.0]], dtype=np.float64),
    ],
)
def test_average_linkage_rejects_invalid_dissimilarity_matrices(
    matrix: np.ndarray,
) -> None:
    """Reject matrices that violate shape, finiteness, sign, or symmetry invariants."""
    with pytest.raises(ValueError, match="dissimilarity_matrix"):
        athenspop.clustering.hierarchical.average_linkage(matrix)


def test_average_linkage_rejects_non_numeric_dissimilarities() -> None:
    """Reject matrices that cannot be converted to floating-point distances."""
    with pytest.raises(ValueError, match="numeric values"):
        athenspop.clustering.hierarchical.average_linkage(cast("np.ndarray", [["x"]]))


def test_dendrogram_layout_returns_geometry_without_rendering() -> None:
    """Return deterministic branch and leaf geometry without importing Matplotlib."""
    matrix = np.array(
        [[0.0, 1.0, 4.0], [1.0, 0.0, 5.0], [4.0, 5.0, 0.0]], dtype=np.float64
    )
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(matrix)
    layout = athenspop.clustering.hierarchical.dendrogram_layout(
        linkage_matrix, labels=("a", "b", "c")
    )
    assert layout.leaf_indices == (2, 0, 1)
    assert layout.leaf_labels == ("c", "a", "b")
    assert layout.branch_x == ((15.0, 15.0, 25.0, 25.0), (5.0, 5.0, 20.0, 20.0))
    assert layout.branch_y == ((0.0, 1.0, 1.0, 0.0), (0.0, 4.5, 4.5, 1.0))
    assert layout.branch_colors == ("C1", "C0")
    assert layout.leaf_colors == ("C0", "C1", "C1")


def test_flat_cluster_labels_rejects_non_positive_cluster_count() -> None:
    """Require at least one cluster in a flat dendrogram cut."""
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float64)
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(matrix)
    with pytest.raises(ValueError, match="positive"):
        athenspop.clustering.hierarchical.flat_cluster_labels(
            linkage_matrix, n_clusters=0
        )


def test_flat_labels_and_display_tree_share_exact_partition_with_ties() -> None:
    """Keep array labels and displayed leaves aligned when merge heights tie."""
    matrix = np.ones((4, 4), dtype=np.float64)
    np.fill_diagonal(matrix, 0.0)
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(matrix)

    labels = athenspop.clustering.hierarchical.flat_cluster_labels(
        linkage_matrix, n_clusters=2
    )
    tree = athenspop.clustering.hierarchical.cut_dendrogram_tree(
        linkage_matrix, n_clusters=2
    )

    assert len(set(labels.tolist())) == 2
    assert tree.left is not None
    assert tree.right is not None
    flat_partition = {
        frozenset(np.flatnonzero(labels == label).tolist())
        for label in set(labels.tolist())
    }
    displayed_partition = {
        frozenset(tree.left.members),
        frozenset(tree.right.members),
    }
    assert flat_partition == displayed_partition


@pytest.mark.parametrize(
    "linkage_matrix",
    [
        np.empty((0, 4), dtype=np.float64),
        np.ones((1, 3), dtype=np.float64),
        np.ones((1, 4, 1), dtype=np.float64),
        np.array([[0.0, 1.0, np.nan, 2.0]], dtype=np.float64),
        np.array([[0.0, 1.0, np.inf, 2.0]], dtype=np.float64),
        np.array([[0.0, 1.0, -0.5, 2.0]], dtype=np.float64),
    ],
)
def test_flat_cluster_labels_rejects_invalid_linkage_matrices(
    linkage_matrix: np.ndarray,
) -> None:
    """Reject linkage matrices with invalid shape, size, height, or finiteness."""
    with pytest.raises(ValueError, match="linkage_matrix"):
        athenspop.clustering.hierarchical.flat_cluster_labels(
            linkage_matrix, n_clusters=1
        )


@pytest.mark.parametrize("n_clusters", [False, 0.5])
def test_flat_cluster_labels_rejects_non_integer_cluster_count(
    n_clusters: object,
) -> None:
    """Reject boolean and fractional cluster counts at the public boundary."""
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float64)
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(matrix)
    with pytest.raises(TypeError, match="positive integer"):
        athenspop.clustering.hierarchical.flat_cluster_labels(
            linkage_matrix, n_clusters=cast("int", n_clusters)
        )


def test_cluster_cut_cannot_request_more_clusters_than_observations() -> None:
    """Reject a flat partition larger than its observation set."""
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float64)

    with pytest.raises(ValueError, match="cannot exceed"):
        athenspop.clustering.hierarchical.flat_cluster_labels(
            athenspop.clustering.hierarchical.average_linkage(matrix), n_clusters=3
        )


def test_cluster_size_summary_returns_counts_and_shares() -> None:
    """Report ordered cluster counts and sample shares for positive labels."""
    summary = athenspop.clustering.hierarchical.cluster_size_summary((2, 2, 1, 1, 1))
    assert summary.to_dict(orient="records") == [
        {"cluster": 1, "n_observations": 3, "share": 0.6},
        {"cluster": 2, "n_observations": 2, "share": 0.4},
    ]
    with pytest.raises(ValueError, match="positive"):
        athenspop.clustering.hierarchical.cluster_size_summary((1, 0))


@pytest.mark.parametrize("labels", [(1.0,), (float("nan"),), (float("inf"),), (None,)])
def test_cluster_labels_must_be_positive_integers(labels: object) -> None:
    """Reject nonintegral, nonfinite, missing, and nonpositive cluster labels."""
    with pytest.raises(ValueError, match="positive integers"):
        athenspop.clustering.hierarchical.cluster_size_summary(
            cast("tuple[int, ...]", labels)
        )


def test_cluster_state_distribution_returns_within_cluster_state_shares() -> None:
    """Weight every state token equally within each cluster summary."""
    distribution = athenspop.clustering.hierarchical.cluster_state_distribution(
        (("home", "work"), ("home", "home"), ("work", "bus")),
        (1, 1, 2),
    )
    assert distribution.to_dict(orient="records") == [
        {"cluster": 1, "state": "home", "count": 3, "share": 0.75},
        {"cluster": 1, "state": "work", "count": 1, "share": 0.25},
        {"cluster": 2, "state": "bus", "count": 1, "share": 0.5},
        {"cluster": 2, "state": "work", "count": 1, "share": 0.5},
    ]
    with pytest.raises(ValueError, match="same length"):
        athenspop.clustering.hierarchical.cluster_state_distribution(
            (("home",),), (1, 2)
        )


def test_cluster_time_distribution_requires_aligned_sequences_and_labels() -> None:
    """Reject temporal summaries whose labels do not align with the sequences."""
    with pytest.raises(ValueError, match="same length"):
        athenspop.clustering.hierarchical.cluster_time_distribution(
            (("home",),), (1, 2)
        )


def test_cophenetic_correlation_requires_aligned_nonconstant_distances() -> None:
    """Reject mismatched observations and undefined constant correlations."""
    two_observation_matrix = np.array([[0.0, 1.0], [1.0, 0.0]])
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(
        two_observation_matrix
    )

    with pytest.raises(ValueError, match="same number of observations"):
        athenspop.clustering.hierarchical.cophenetic_correlation(
            linkage_matrix,
            np.array(
                [[0.0, 1.0, 2.0], [1.0, 0.0, 3.0], [2.0, 3.0, 0.0]],
                dtype=np.float64,
            ),
        )
    with pytest.raises(ValueError, match="undefined"):
        athenspop.clustering.hierarchical.cophenetic_correlation(
            linkage_matrix, two_observation_matrix
        )


def test_linkage_consumers_reject_non_numeric_matrices() -> None:
    """Reject linkage matrices that cannot be converted to floating-point values."""
    with pytest.raises(ValueError, match="numeric values"):
        athenspop.clustering.hierarchical.leaf_order(
            cast("athenspop.clustering.hierarchical.LinkageMatrix", [["x"]])
        )


@pytest.mark.parametrize(
    "sequences",
    [
        (("",), ("home",)),
        ((cast("str", 1),), ("home",)),
        ((), ()),
    ],
)
def test_sequence_analysis_requires_nonempty_string_states(
    sequences: tuple[tuple[str, ...], ...],
) -> None:
    """Reject empty, blank, and non-string symbolic sequence states."""
    with pytest.raises((TypeError, ValueError)):
        athenspop.clustering.hierarchical.cluster_state_distribution(sequences, (1, 1))
