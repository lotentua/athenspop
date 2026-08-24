from typing import cast

import numpy as np
import pytest

from athenspop.clustering import (
    average_linkage,
    cluster_size_summary,
    cluster_state_distribution,
    cophenetic_correlation,
    dendrogram_layout,
    flat_cluster_labels,
    leaf_order,
)
from athenspop.sequence import (
    dissimilarity_matrix,
    optimal_matching_dissimilarity,
)


def test_optimal_matching_uses_substitution_when_cheaper_than_indels() -> None:
    costs = {("A", "B"): 0.25, ("B", "A"): 0.25}
    assert (
        optimal_matching_dissimilarity(
            ("A",), ("B",), substitution_cost=costs, indel_cost=1.0
        )
        == 0.25
    )


def test_optimal_matching_uses_indels_for_shifted_equal_length_sequences() -> (
    None
):
    costs = {
        ("A", "B"): 2.0,
        ("B", "A"): 2.0,
        ("A", "C"): 2.0,
        ("C", "A"): 2.0,
        ("B", "C"): 2.0,
        ("C", "B"): 2.0,
    }
    assert (
        optimal_matching_dissimilarity(
            ("A", "B"), ("B", "C"), substitution_cost=costs, indel_cost=1.0
        )
        == 2.0
    )


@pytest.mark.parametrize("indel_cost", [0.0, -1.0, float("nan"), float("inf")])
def test_optimal_matching_rejects_invalid_indel_costs(
    indel_cost: float,
) -> None:
    with pytest.raises(ValueError, match="finite positive"):
        optimal_matching_dissimilarity(
            ("A",),
            ("B",),
            substitution_cost={("A", "B"): 1.0},
            indel_cost=indel_cost,
        )


def test_optimal_matching_rejects_non_numeric_indel_cost() -> None:
    with pytest.raises(TypeError, match="finite positive"):
        optimal_matching_dissimilarity(
            ("A",), ("B",), substitution_cost={("A", "B"): 1.0}, indel_cost=True
        )


@pytest.mark.parametrize(
    "substitution_cost", [-1.0, float("nan"), float("inf")]
)
def test_optimal_matching_rejects_invalid_substitution_costs(
    substitution_cost: float,
) -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        optimal_matching_dissimilarity(
            ("A",), ("B",), substitution_cost={("A", "B"): substitution_cost}
        )


def test_optimal_matching_rejects_non_numeric_substitution_cost() -> None:
    with pytest.raises(TypeError, match="finite non-negative"):
        optimal_matching_dissimilarity(
            ("A",), ("B",), substitution_cost={("A", "B"): True}
        )


def test_dissimilarity_matrix_is_symmetric_with_zero_diagonal() -> None:
    sequences = (("A", "A", "B"), ("A", "B", "B"), ("B", "A", "B"))
    costs = {
        ("A", "A"): 0.0,
        ("A", "B"): 1.0,
        ("B", "A"): 1.0,
        ("B", "B"): 0.0,
    }
    matrix = dissimilarity_matrix(sequences, substitution_cost=costs)
    assert matrix.shape == (3, 3)
    assert matrix.dtype == np.float64
    np.testing.assert_allclose(matrix, matrix.T)
    np.testing.assert_allclose(np.diag(matrix), np.zeros(3))


def test_dissimilarity_matrix_matches_scalar_optimal_matching_reference() -> (
    None
):
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
    matrix = dissimilarity_matrix(
        sequences, substitution_cost=costs, indel_cost=1.0
    )
    expected = np.zeros((len(sequences), len(sequences)), dtype=np.float64)
    for row_index, first in enumerate(sequences):
        for column_index, second in enumerate(sequences):
            expected[row_index, column_index] = optimal_matching_dissimilarity(
                first, second, substitution_cost=costs, indel_cost=1.0
            )
    np.testing.assert_allclose(matrix, expected)


def test_dissimilarity_matrix_rejects_invalid_cost_domains() -> None:
    with pytest.raises(ValueError, match="finite positive"):
        dissimilarity_matrix(
            (("A",), ("B",)),
            substitution_cost={("A", "B"): 1.0, ("B", "A"): 1.0},
            indel_cost=float("nan"),
        )

    with pytest.raises(ValueError, match="finite non-negative"):
        dissimilarity_matrix(
            (("A",), ("B",)),
            substitution_cost={("A", "B"): -1.0, ("B", "A"): -1.0},
        )


def test_average_linkage_accepts_precomputed_dissimilarity_matrix() -> None:
    matrix = np.array(
        [[0.0, 1.0, 4.0], [1.0, 0.0, 5.0], [4.0, 5.0, 0.0]], dtype=np.float64
    )
    linkage_matrix = average_linkage(matrix)
    assert linkage_matrix.shape == (2, 4)
    assert linkage_matrix[0, 0] == 0
    assert linkage_matrix[0, 1] == 1
    assert linkage_matrix[0, 2] == 1.0
    assert linkage_matrix[0, 3] == 2
    labels = flat_cluster_labels(linkage_matrix, n_clusters=2)
    assert labels.shape == (3,)
    assert labels[0] == labels[1]
    assert labels[2] != labels[0]
    order = leaf_order(linkage_matrix)
    assert order.shape == (3,)
    assert sorted(order.tolist()) == [0, 1, 2]
    assert 0.0 <= cophenetic_correlation(linkage_matrix, matrix) <= 1.0


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
    ],
)
def test_average_linkage_rejects_invalid_dissimilarity_matrices(
    matrix: np.ndarray,
) -> None:
    with pytest.raises(ValueError, match="dissimilarity_matrix"):
        average_linkage(matrix)


def test_dendrogram_layout_returns_geometry_without_rendering() -> (
    None
):
    matrix = np.array(
        [[0.0, 1.0, 4.0], [1.0, 0.0, 5.0], [4.0, 5.0, 0.0]], dtype=np.float64
    )
    linkage_matrix = average_linkage(matrix)
    layout = dendrogram_layout(linkage_matrix, labels=("a", "b", "c"))
    assert layout.leaf_indices == (2, 0, 1)
    assert layout.leaf_labels == ("c", "a", "b")
    assert layout.branch_x == ((15.0, 15.0, 25.0, 25.0), (5.0, 5.0, 20.0, 20.0))
    assert layout.branch_y == ((0.0, 1.0, 1.0, 0.0), (0.0, 4.5, 4.5, 1.0))
    assert layout.branch_colors == ("C1", "C0")
    assert layout.leaf_colors == ("C0", "C1", "C1")


def test_flat_cluster_labels_rejects_non_positive_cluster_count() -> None:
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float64)
    linkage_matrix = average_linkage(matrix)
    with pytest.raises(ValueError, match="positive"):
        flat_cluster_labels(linkage_matrix, n_clusters=0)


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
    with pytest.raises(ValueError, match="linkage_matrix"):
        flat_cluster_labels(linkage_matrix, n_clusters=1)


@pytest.mark.parametrize("n_clusters", [False, 0.5])
def test_flat_cluster_labels_rejects_non_integer_cluster_count(
    n_clusters: object,
) -> None:
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float64)
    linkage_matrix = average_linkage(matrix)
    with pytest.raises(TypeError, match="positive integer"):
        flat_cluster_labels(linkage_matrix, n_clusters=cast("int", n_clusters))


def test_cluster_size_summary_returns_counts_and_shares() -> None:
    summary = cluster_size_summary((2, 2, 1, 1, 1))
    assert summary.to_dict(orient="records") == [
        {"cluster": 1, "n_diaries": 3, "share": 0.6},
        {"cluster": 2, "n_diaries": 2, "share": 0.4},
    ]
    with pytest.raises(ValueError, match="positive"):
        cluster_size_summary((1, 0))


@pytest.mark.parametrize(
    "labels", [(1.0,), (float("nan"),), (float("inf"),), (None,)]
)
def test_cluster_labels_must_be_positive_integers(labels: object) -> None:
    with pytest.raises(ValueError, match="positive integers"):
        cluster_size_summary(cast("tuple[int, ...]", labels))


def test_cluster_state_distribution_returns_within_cluster_state_shares() -> (
    None
):
    distribution = cluster_state_distribution(
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
        cluster_state_distribution((("home",),), (1, 2))
