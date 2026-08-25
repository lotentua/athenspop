# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module defines behavior contracts for style-agnostic visualization."""

import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import pytest

import athenspop.clustering.hierarchical
import athenspop.visualization.dendrogram


def test_cluster_time_distribution_returns_bin_level_cluster_shares() -> None:
    """Compute within-cluster state shares independently for each sequence bin."""
    distribution = athenspop.clustering.hierarchical.cluster_time_distribution(
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
    """Represent the requested two-cluster cut as exactly two displayed leaves."""
    linkage_matrix = np.array(
        [
            [0.0, 1.0, 0.1, 2.0],
            [2.0, 3.0, 0.2, 2.0],
            [4.0, 5.0, 1.0, 4.0],
        ],
        dtype=np.float64,
    )

    tree = athenspop.clustering.hierarchical.cut_dendrogram_tree(
        linkage_matrix, n_clusters=2
    )

    assert tree.is_leaf is False
    assert tree.left is not None
    assert tree.right is not None
    assert tree.left.is_leaf is True
    assert tree.right.is_leaf is True
    assert tree.left.members == (0, 1)
    assert tree.right.members == (2, 3)
    assert tree.left.leaf_label == 1
    assert tree.right.leaf_label == 2


def test_plot_cut_dendrogram_state_distribution_returns_matplotlib_figure() -> None:
    """Return a closable Matplotlib figure with the requested title and panels."""
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

    figure_object = (
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=2,
            style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
                title="This figure shows purpose and travel states.",
                state_groups={
                    "These states represent activities.": ("home", "shop", "work"),
                    "These states represent travel.": ("bus", "car", "walk"),
                },
            ),
        )
    )

    try:
        assert isinstance(figure_object, matplotlib.figure.Figure)
        assert figure_object.axes
        assert (
            figure_object.axes[0].get_title()
            == "This figure shows purpose and travel states."
        )
        node_text = {
            text_object.get_text() for text_object in figure_object.axes[0].texts
        }
        assert any("This node contains 1 observation." in text for text in node_text)
        assert any("This node contains 3 observations." in text for text in node_text)
    finally:
        plt.close(figure_object)


def test_plot_cut_dendrogram_rejects_sequence_count_mismatch() -> None:
    """Require one symbolic sequence for every linkage observation."""
    linkage_matrix = np.array([[0.0, 1.0, 1.0, 2.0]], dtype=np.float64)

    with pytest.raises(ValueError, match="must contain 2 rows"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix, (("home",),), n_clusters=1
        )


def test_plot_cut_dendrogram_rejects_empty_or_unequal_sequences() -> None:
    """Reject absent sequences and rows with inconsistent interval counts."""
    linkage_matrix = np.array([[0.0, 1.0, 1.0, 2.0]], dtype=np.float64)

    with pytest.raises(ValueError, match="At least one"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix, (), n_clusters=1
        )

    with pytest.raises(ValueError, match="same length"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix, (("home",), ("home", "work")), n_clusters=1
        )


def test_plot_cut_dendrogram_rejects_invalid_state_groups() -> None:
    """Reject empty, malformed, and unknown state-panel definitions."""
    linkage_matrix = np.array([[0.0, 1.0, 1.0, 2.0]], dtype=np.float64)
    sequences = (("home",), ("work",))

    with pytest.raises(ValueError, match="at least one group"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=1,
            style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
                state_groups={}
            ),
        )

    with pytest.raises(ValueError, match="unknown state"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=1,
            style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
                state_groups={"These states represent activities.": ("home", "shop")}
            ),
        )

    with pytest.raises(TypeError, match="title"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=1,
            style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
                state_groups={"": ("home",)}
            ),
        )

    with pytest.raises(ValueError, match="at least one state"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=1,
            style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
                state_groups={"These states represent activities.": ()}
            ),
        )

    with pytest.raises(TypeError, match="grouped state"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=1,
            style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
                state_groups={"These states represent activities.": ("",)}
            ),
        )


def test_plot_cut_dendrogram_rejects_bad_cluster_count_or_linkage() -> None:
    """Validate the cluster count and SciPy linkage shape before plotting."""
    linkage_matrix = np.array([[0.0, 1.0, 1.0, 2.0]], dtype=np.float64)
    sequences = (("home",), ("work",))

    with pytest.raises(ValueError, match="positive"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix, sequences, n_clusters=0
        )

    with pytest.raises(ValueError, match="four columns"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            np.array([[0.0, 1.0, 1.0]], dtype=np.float64),
            sequences,
            n_clusters=1,
        )
