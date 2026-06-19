from pathlib import Path

import numpy as np

from examples.paper.visualization import (
    cluster_time_distribution,
    write_cut_dendrogram_distribution_svg,
)


def test_paper_visualization_adapter_uses_cut_dendrogram_distribution_svg(tmp_path: Path) -> None:
    sequences = (
        ("home", "trip_car", "work"),
        ("home", "trip_bus", "home"),
        ("home", "trip_walk", "market"),
    )
    labels = (1, 1, 2)
    distribution = cluster_time_distribution(sequences, labels)

    cluster_one_bin_two = distribution[(distribution["cluster"] == 1) & (distribution["bin_index"] == 2) & (distribution["state"] == "home")]
    assert cluster_one_bin_two["share"].iloc[0] == 0.5

    linkage_matrix = np.array(
        [
            [0.0, 1.0, 1.0, 2.0],
            [2.0, 3.0, 2.0, 3.0],
        ],
        dtype=np.float64,
    )
    output = tmp_path / "dendrogram.svg"

    write_cut_dendrogram_distribution_svg(linkage_matrix, sequences, output, n_clusters=2)

    text = output.read_text(encoding="utf-8")
    assert "Cut dendrogram with temporal state distributions" in text
    assert "Average-linkage diary dendrogram" not in text
    assert 'class="travel-mode-panel-state"' in text
    assert 'class="activity-purpose-panel-state"' in text
