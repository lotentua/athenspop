import numpy as np
import pytest
from matplotlib.figure import Figure

from athenspop.clustering import (
    cluster_time_distribution,
    cut_dendrogram_tree,
)
from athenspop.visualization import (
    TemporalDendrogramPlotStyle,
    plot_cut_dendrogram_state_distribution,
)


def test_cluster_time_distribution_returns_bin_level_cluster_shares() -> None:
    distribution = cluster_time_distribution(
        (
            ("home", "work", "work"),
            ("home", "work", "home"),
            ("home", "trip_car", "home"),
        ),
        (1, 1, 2),
    )

    cluster_one_bin_two = distribution[
        (distribution["cluster"] == 1)
        & (distribution["bin_index"] == 2)
        & (distribution["state"] == "home")
    ]

    assert cluster_one_bin_two["share"].iloc[0] == 0.5


def test_cut_dendrogram_tree_keeps_requested_number_of_displayed_clusters() -> None:
    linkage_matrix = np.array(
        [
            [0.0, 1.0, 0.1, 2.0],
            [2.0, 3.0, 0.2, 2.0],
            [4.0, 5.0, 1.0, 4.0],
        ],
        dtype=np.float64,
    )

    tree = cut_dendrogram_tree(linkage_matrix, n_clusters=2)

    assert tree.is_leaf is False
    assert tree.left is not None
    assert tree.right is not None
    assert tree.left.is_leaf is True
    assert tree.right.is_leaf is True
    assert tree.left.members == (0, 1)
    assert tree.right.members == (2, 3)
    assert tree.left.leaf_label == 1
    assert tree.right.leaf_label == 2


def test_cut_dendrogram_tree_exposes_members_for_local_visualization_code() -> None:
    linkage_matrix = np.array(
        [
            [0.0, 1.0, 0.1, 2.0],
            [2.0, 3.0, 0.2, 2.0],
            [4.0, 5.0, 1.0, 4.0],
        ],
        dtype=np.float64,
    )
    tree = cut_dendrogram_tree(linkage_matrix, n_clusters=2)

    assert tree.members == (0, 1, 2, 3)
    assert tree.left is not None
    assert tree.right is not None
    assert tree.left.members == (0, 1)
    assert tree.right.members == (2, 3)


def test_plot_cut_dendrogram_state_distribution_returns_matplotlib_figure() -> None:
    sequences = (
        ("home", "car", "work"),
        ("home", "bus", "home"),
        ("home", "walk", "shop"),
    )
    linkage_matrix = np.array(
        [
            [0.0, 1.0, 1.0, 2.0],
            [2.0, 3.0, 2.0, 3.0],
        ],
        dtype=np.float64,
    )

    figure = plot_cut_dendrogram_state_distribution(
        linkage_matrix,
        sequences,
        n_clusters=2,
        style=TemporalDendrogramPlotStyle(
            state_groups={
                "Activity": ("home", "shop", "work"),
                "Travel": ("bus", "car", "walk"),
            }
        ),
    )

    assert isinstance(figure, Figure)
    assert figure.axes


def test_plot_cut_dendrogram_rejects_sequence_count_mismatch() -> None:
    linkage_matrix = np.array([[0.0, 1.0, 1.0, 2.0]], dtype=np.float64)

    with pytest.raises(ValueError, match="must contain 2 rows"):
        plot_cut_dendrogram_state_distribution(
            linkage_matrix, (("home",),), n_clusters=1
        )


def test_plot_cut_dendrogram_rejects_empty_or_unequal_sequences() -> None:
    linkage_matrix = np.array([[0.0, 1.0, 1.0, 2.0]], dtype=np.float64)

    with pytest.raises(ValueError, match="At least one"):
        plot_cut_dendrogram_state_distribution(linkage_matrix, (), n_clusters=1)

    with pytest.raises(ValueError, match="same length"):
        plot_cut_dendrogram_state_distribution(
            linkage_matrix, (("home",), ("home", "work")), n_clusters=1
        )


def test_plot_cut_dendrogram_rejects_invalid_state_groups() -> None:
    linkage_matrix = np.array([[0.0, 1.0, 1.0, 2.0]], dtype=np.float64)
    sequences = (("home",), ("work",))

    with pytest.raises(ValueError, match="at least one group"):
        plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=1,
            style=TemporalDendrogramPlotStyle(state_groups={}),
        )

    with pytest.raises(ValueError, match="unknown state"):
        plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=1,
            style=TemporalDendrogramPlotStyle(
                state_groups={"Activity": ("home", "shop")}
            ),
        )


def test_plot_cut_dendrogram_rejects_bad_cluster_count_or_linkage() -> None:
    linkage_matrix = np.array([[0.0, 1.0, 1.0, 2.0]], dtype=np.float64)
    sequences = (("home",), ("work",))

    with pytest.raises(ValueError, match="positive"):
        plot_cut_dendrogram_state_distribution(linkage_matrix, sequences, n_clusters=0)

    with pytest.raises(ValueError, match="four columns"):
        plot_cut_dendrogram_state_distribution(
            np.array([[0.0, 1.0, 1.0]], dtype=np.float64),
            sequences,
            n_clusters=1,
        )
