"""CSuM2026-specific sequence labels and transition-cost construction."""

from collections.abc import Iterable, Sequence
from typing import Final

from athenspop.model import Diary, Trip
from athenspop.sequence import (
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_WINDOW_SECONDS,
    dissimilarity_matrix,
    state_sequence_from_diary,
)
from athenspop.types import DissimilarityMatrix

ATHENS_WINDOW_SECONDS: Final[int] = DEFAULT_WINDOW_SECONDS
ATHENS_DELTA_SECONDS: Final[int] = DEFAULT_INTERVAL_SECONDS

_ACTIVITY_REDUCTION: Final[dict[str, str]] = {
    "home": "home",
    "education": "rigid",
    "work": "rigid",
    "market": "flexible",
    "recreation": "flexible",
    "service": "flexible",
    "other": "flexible",
}

_MODE_REDUCTION: Final[dict[str, str]] = {
    "car": "trip_car",
    "taxi": "trip_car",
    "motorcycle": "trip_motorcycle",
    "bus": "trip_bus",
    "train": "trip_train",
    "bicycle": "trip_micromobility",
    "escooter": "trip_micromobility",
    "walk": "trip_walk",
}


def period_label(second: int) -> int:
    """Return the CSuM2026 demand-period label for a diary second."""
    if 0 <= second < 3 * 3600 or 15 * 3600 <= second <= ATHENS_WINDOW_SECONDS:
        return 1
    if 3 * 3600 <= second < 6 * 3600:
        return 2
    if 6 * 3600 <= second < 12 * 3600:
        return 3
    if 12 * 3600 <= second < 15 * 3600:
        return 4
    raise ValueError(f"`second` must be in [0, {ATHENS_WINDOW_SECONDS}], got {second}.")


def compound_sequence_from_diary(
    diary: Diary,
    *,
    initial_activity_state: str = "home",
    window_end_second: int = ATHENS_WINDOW_SECONDS,
    interval_seconds: int = ATHENS_DELTA_SECONDS,
) -> tuple[str, ...]:
    """Convert one scheduled diary into the reduced compound state-period sequence
    used by the Athens example.
    """
    states = state_sequence_from_diary(
        diary,
        initial_activity_state=initial_activity_state,
        travel_state_labeler=athens_travel_state,
        window_end_second=window_end_second,
        interval_seconds=interval_seconds,
    )
    return compound_period_sequence(states, interval_seconds=interval_seconds)


def athens_travel_state(trip: Trip) -> str:
    """Return the Athens-example movement state label for one trip."""
    return f"trip_{trip.mode}"


def compound_period_sequence(
    states: Sequence[str], *, interval_seconds: int = ATHENS_DELTA_SECONDS
) -> tuple[str, ...]:
    """Reduce states and append CSuM2026 period labels based on each bin start time."""
    return tuple(
        f"{reduce_athens_state(state)}@p{period_label(index * interval_seconds)}"
        for index, state in enumerate(states)
    )


def reduce_athens_state(state: str) -> str:
    "Reduce an activity or `trip_` mode state according to the Athens example alphabet."
    if state in _ACTIVITY_REDUCTION:
        return _ACTIVITY_REDUCTION[state]
    if state.startswith("trip_"):
        mode = state.removeprefix("trip_")
        if mode in _MODE_REDUCTION:
            return _MODE_REDUCTION[mode]
    raise ValueError(f"Unknown Athens example state {state!r}.")


def transition_counts(
    sequences: Iterable[Sequence[str]],
) -> dict[tuple[str, str], int]:
    "Count non-self transitions across state sequences using the CSuM2026 example rule."
    counts: dict[tuple[str, str], int] = {}
    for sequence in sequences:
        for source, target in zip(sequence, sequence[1:], strict=False):
            if source == target:
                continue
            key = (source, target)
            counts[key] = counts.get(key, 0) + 1
    return counts


def transition_probabilities(
    sequences: Iterable[Sequence[str]],
) -> dict[tuple[str, str], float]:
    """Compute empirical transition probabilities with self-transitions excluded
    from denominators.
    """
    materialized_sequences = tuple(tuple(sequence) for sequence in sequences)
    states = _states(materialized_sequences)
    counts = transition_counts(materialized_sequences)
    denominators = {
        state: sum(count for (source, _), count in counts.items() if source == state)
        for state in states
    }
    probabilities: dict[tuple[str, str], float] = {}
    for source in states:
        denominator = denominators[source]
        for target in states:
            if source == target or denominator == 0:
                probabilities[(source, target)] = 0.0
            else:
                probabilities[(source, target)] = (
                    counts.get((source, target), 0) / denominator
                )
    return probabilities


def substitution_costs(
    sequences: Iterable[Sequence[str]],
) -> dict[tuple[str, str], float]:
    """Compute the symmetric CSuM2026 transition-rate substitution cost matrix."""
    materialized_sequences = tuple(tuple(sequence) for sequence in sequences)
    states = _states(materialized_sequences)
    probabilities = transition_probabilities(materialized_sequences)
    costs: dict[tuple[str, str], float] = {}
    for source in states:
        for target in states:
            if source == target:
                costs[(source, target)] = 0.0
            else:
                costs[(source, target)] = (
                    2.0
                    - probabilities[(source, target)]
                    - probabilities[(target, source)]
                )
    return costs


def athens_dissimilarity_matrix(
    sequences: Sequence[Sequence[str]], *, indel_cost: float = 1.0
) -> DissimilarityMatrix:
    """Compute the Athens example pairwise OM matrix using local CSuM2026
    substitution costs.
    """
    materialized = tuple(tuple(sequence) for sequence in sequences)
    return dissimilarity_matrix(
        materialized,
        substitution_cost=substitution_costs(materialized),
        indel_cost=indel_cost,
    )


def _states(sequences: Sequence[Sequence[str]]) -> tuple[str, ...]:
    return tuple(sorted({state for sequence in sequences for state in sequence}))
