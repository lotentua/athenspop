from pathlib import Path

import numpy as np

from athenspop.visualization import (
    cluster_time_distribution,
    cut_dendrogram_distribution_svg,
    cut_dendrogram_tree,
    write_cut_dendrogram_distribution_svg,
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

    cluster_one_bin_two = distribution[(distribution["cluster"] == 1) & (distribution["bin_index"] == 2) & (distribution["state"] == "home")]

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


def test_cut_dendrogram_distribution_svg_draws_node_local_purpose_and_mode_panels(tmp_path: Path) -> None:
    linkage_matrix = np.array(
        [
            [0.0, 1.0, 0.1, 2.0],
            [2.0, 3.0, 0.2, 2.0],
            [4.0, 5.0, 1.0, 4.0],
        ],
        dtype=np.float64,
    )
    sequences = (
        ("home", "trip_car", "work", "home"),
        ("home", "trip_car", "work", "home"),
        ("home", "trip_bus", "education", "home"),
        ("home", "trip_walk", "market", "home"),
    )

    svg = cut_dendrogram_distribution_svg(linkage_matrix, sequences, n_clusters=2)

    assert "Cut dendrogram with temporal state distributions" in svg
    assert "Average-linkage diary dendrogram" not in svg
    assert "ID: 1" in svg
    assert "Size: 2" in svg
    assert 'class="travel-mode-panel"' in svg
    assert 'class="travel-mode-panel-state"' in svg
    assert 'class="activity-purpose-panel"' in svg
    assert 'class="activity-purpose-panel-state"' in svg
    assert "Activity Purpose" in svg
    assert "Travel Mode" in svg

    output = tmp_path / "cut_dendrogram.svg"
    write_cut_dendrogram_distribution_svg(linkage_matrix, sequences, output, n_clusters=2)

    assert output.read_text(encoding="utf-8") == svg
