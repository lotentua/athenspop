"""Athens example visualization wrappers around generic plotting primitives."""

from collections.abc import Sequence
from os import PathLike
from pathlib import Path
from typing import Final

from athenspop.clustering import LinkageMatrix, cluster_time_distribution
from athenspop.visualization import (
    TemporalDendrogramPlotStyle,
    plot_cut_dendrogram_state_distribution,
)

ATHENS_MODE_PREFIX: Final[str] = "trip_"
ATHENS_STATE_COLORS: Final[dict[str, str]] = {
    "home": "#7FC97F",
    "work": "#BEAED4",
    "education": "#FDC086",
    "shop": "#FFFF99",
    "leisure": "#386CB0",
    "escort": "#F0027F",
    "other": "#BF5B17",
    "trip_car": "#1B9E77",
    "trip_bus": "#D95F02",
    "trip_walk": "#7570B3",
    "trip_bike": "#E7298A",
}


def write_cut_dendrogram_distribution_svg(
    linkage_matrix: LinkageMatrix,
    sequences: Sequence[Sequence[str]],
    path: str | PathLike[str],
    *,
    n_clusters: int,
) -> None:
    """Write the Athens example cut dendrogram figure as SVG.

    Args:
        linkage_matrix:
            SciPy linkage matrix defining the observation hierarchy.
        sequences:
            Equal-length Athens state sequences aligned with the observations used to
            compute `linkage_matrix`.
        path:
            Destination SVG path.
        n_clusters:
            Number of displayed cut clusters.
    """
    states = _states(sequences)
    mode_states = tuple(
        state
        for state in states
        if _state_without_period(state).startswith(ATHENS_MODE_PREFIX)
    )
    mode_state_set = set(mode_states)
    activity_states = tuple(state for state in states if state not in mode_state_set)
    figure = plot_cut_dendrogram_state_distribution(
        linkage_matrix,
        sequences,
        n_clusters=n_clusters,
        style=TemporalDendrogramPlotStyle(
            state_groups={
                "Activity Purpose": activity_states,
                "Travel Mode": mode_states,
            },
            state_colors=ATHENS_STATE_COLORS,
        ),
    )
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="svg")


def _states(sequences: Sequence[Sequence[str]]) -> tuple[str, ...]:
    """Return sorted unique states from example sequences."""
    return tuple(sorted({str(state) for sequence in sequences for state in sequence}))


def _state_without_period(state: str) -> str:
    """Remove an optional period suffix such as `@p1` from a sequence state."""
    return state.split("@", maxsplit=1)[0]


__all__: Final[tuple[str, ...]] = (
    "cluster_time_distribution",
    "write_cut_dendrogram_distribution_svg",
)
