"""Generic sequence construction and optimal-matching helpers."""

from athenspop.sequence.distance import (
    dissimilarity_matrix,
    optimal_matching_dissimilarity,
)
from athenspop.sequence.episodes import (
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_WINDOW_SECONDS,
    Episode,
    discretize_episodes,
    episodes_from_diary,
    overlap_duration,
    state_sequence_from_diary,
)

__all__ = [
    "DEFAULT_INTERVAL_SECONDS",
    "DEFAULT_WINDOW_SECONDS",
    "Episode",
    "discretize_episodes",
    "dissimilarity_matrix",
    "episodes_from_diary",
    "optimal_matching_dissimilarity",
    "overlap_duration",
    "state_sequence_from_diary",
]
