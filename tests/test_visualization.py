# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Style-agnostic visualization behavior contracts."""

import cycler
import matplotlib.figure
import matplotlib.patches
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


@pytest.mark.parametrize("font_size", (10.0, 16.0))
def test_plot_cut_dendrogram_exposes_quantitative_axes_and_aligned_bars(
    font_size: float,
) -> None:
    """Expose unclipped hierarchy coordinates and unit-width state-share bars."""
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

    with plt.rc_context(
        {
            "grid.color": "#123456",
            "axes.prop_cycle": cycler.cycler(color=("#111111", "#555555", "#999999")),
            "font.size": font_size,
        }
    ):
        figure_object = (
            athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
                linkage_matrix,
                sequences,
                n_clusters=2,
                style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
                    title="Purpose and travel states",
                    state_groups={
                        "Activity states": ("home", "shop", "work"),
                        "Travel states": ("bus", "car", "walk"),
                    },
                ),
            )
        )

    try:
        assert isinstance(figure_object, matplotlib.figure.Figure)
        assert len(figure_object.axes) == 5
        tree_axes, *distribution_axes = figure_object.axes
        assert tree_axes.get_title() == ""
        assert any(
            text.get_text() == "Purpose and travel states"
            for text in figure_object.texts
        )
        assert tree_axes.get_xlabel() == "Cut cluster"
        assert tree_axes.get_ylabel() == "Normalized height"
        assert [tick.get_text() for tick in tree_axes.get_xticklabels()] == [
            "Cluster 1",
            "Cluster 2",
        ]
        assert tree_axes.lines
        assert all(line.get_color() == "#123456" for line in tree_axes.lines)

        bottom_axes = distribution_axes[1::2]
        assert all(axis.get_xlabel() == "Sequence bin" for axis in bottom_axes)
        assert all(axis.get_title() == "" for axis in distribution_axes)
        assert distribution_axes[0].get_ylabel() == "Activity states"
        assert distribution_axes[1].get_ylabel() == "Travel states"
        assert all(axis.get_ylabel() == "" for axis in distribution_axes[2:])
        assert all(
            all(spine.get_visible() for spine in axis.spines.values())
            for axis in distribution_axes
        )
        bars = [
            patch
            for axis in distribution_axes
            for patch in axis.patches
            if isinstance(patch, matplotlib.patches.Rectangle)
        ]
        assert bars
        assert all(patch.get_width() == 1.0 for patch in bars)
        renderer = figure_object.draw_without_rendering()
        tick_values = [
            int(text.get_text()) for text in distribution_axes[-1].get_xticklabels()
        ]
        assert tick_values
        assert min(tick_values) >= 0
        assert max(tick_values) < len(sequences[0])

        canvas_bounds = figure_object.bbox
        layout_artists = [
            *figure_object.texts,
            *(axis.xaxis.label for axis in figure_object.axes),
            *(axis.yaxis.label for axis in figure_object.axes),
            *figure_object.legends,
        ]
        for artist in layout_artists:
            bounds = artist.get_window_extent(renderer)
            assert bounds.x0 >= canvas_bounds.x0
            assert bounds.y0 >= canvas_bounds.y0
            assert bounds.x1 <= canvas_bounds.x1
            assert bounds.y1 <= canvas_bounds.y1
        legend_bounds = figure_object.legends[0].get_window_extent(renderer)
        assert all(
            not legend_bounds.overlaps(axis.xaxis.label.get_window_extent(renderer))
            for axis in bottom_axes
        )
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
                state_groups={"Activity states": ("home", "shop")}
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
                state_groups={"Activity states": ()}
            ),
        )

    with pytest.raises(TypeError, match="grouped state"):
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix,
            sequences,
            n_clusters=1,
            style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
                state_groups={"Activity states": ("",)}
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
