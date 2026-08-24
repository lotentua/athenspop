from collections.abc import Sequence

import numpy as np
import pytest

from athenspop.model import Diary, Trip
from athenspop.schema import TimingPattern
from examples.athens.method import (
    athens_dissimilarity_matrix,
    compound_period_sequence,
    compound_sequence_from_diary,
    period_label,
    reduce_athens_state,
    substitution_costs,
    transition_counts,
    transition_probabilities,
)


@pytest.mark.parametrize(
    ("second", "expected"),
    [
        (0, 1),
        (10799, 1),
        (10800, 2),
        (21599, 2),
        (21600, 3),
        (43199, 3),
        (43200, 4),
        (53999, 4),
        (54000, 1),
        (86399, 1),
    ],
)
def test_period_label_matches_athens_boundaries(second: int, expected: int) -> None:
    assert period_label(second) == expected


def test_reduced_compound_period_sequence_matches_athens_alphabet() -> None:
    states = ("home", "work", "trip_taxi", "trip_escooter")
    assert compound_period_sequence(states, interval_seconds=10800) == (
        "home@p1",
        "rigid@p2",
        "trip_car@p3",
        "trip_micromobility@p3",
    )
    assert reduce_athens_state("market") == "flexible"
    assert reduce_athens_state("trip_bicycle") == "trip_micromobility"


def test_compound_sequence_from_scheduled_diary_uses_athens_labels() -> None:
    diary = Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t1",
                origin="home",
                destination="market",
                purpose="market",
                mode="car",
                departure_second=900,
                arrival_second=1800,
                travel_time_seconds=900,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
        ),
    )
    assert compound_sequence_from_diary(
        diary, window_end_second=2700, interval_seconds=900
    ) == ("home@p1", "trip_car@p1", "flexible@p1")


def test_transition_costs_exclude_self_transitions_from_denominators() -> None:
    sequences = [("A", "A", "B", "A", "A", "C")]
    counts = transition_counts(sequences)
    assert counts == {("A", "B"): 1, ("B", "A"): 1, ("A", "C"): 1}
    probabilities = transition_probabilities(sequences)
    assert probabilities[("A", "B")] == 0.5
    assert probabilities[("A", "C")] == 0.5
    assert probabilities[("B", "A")] == 1.0
    assert probabilities[("C", "A")] == 0.0
    costs = substitution_costs(sequences)
    assert costs[("A", "A")] == 0.0
    assert costs[("A", "B")] == costs[("B", "A")] == 0.5
    assert costs[("A", "C")] == costs[("C", "A")] == 1.5
    assert all(0.0 <= cost <= 2.0 for cost in costs.values())


def test_athens_transition_denominator_differs_from_traminer() -> None:
    sequence = ("A", "A", "B", "A", "A", "C")
    sequences = (sequence,)
    athens_probabilities = transition_probabilities(sequences)
    traminer_style_probabilities = _self_inclusive_transition_probabilities(sequences)
    assert athens_probabilities[("A", "B")] == 0.5
    assert athens_probabilities[("A", "C")] == 0.5
    assert athens_probabilities[("A", "A")] == 0.0
    assert traminer_style_probabilities[("A", "B")] == 0.25
    assert traminer_style_probabilities[("A", "C")] == 0.25
    assert traminer_style_probabilities[("A", "A")] == 0.5


def test_athens_substitution_costs_differ_from_traminer_trate() -> None:
    sequences = (("A", "A", "B", "A", "A", "C"),)
    athens_costs = substitution_costs(sequences)
    traminer_style_costs = _self_inclusive_substitution_costs(sequences)
    assert athens_costs[("A", "B")] == pytest.approx(0.5)
    assert traminer_style_costs[("A", "B")] == pytest.approx(0.75)
    assert athens_costs[("A", "B")] != traminer_style_costs[("A", "B")]


def test_athens_dissimilarity_fixture_remains_symmetric_and_finite() -> None:
    matrix = athens_dissimilarity_matrix(
        (
            ("A", "A", "B", "A", "A", "C"),
            ("A", "B", "A", "C", "A", "C"),
            ("C", "A", "B", "A", "C", "A"),
        )
    )
    assert matrix.shape == (3, 3)
    assert np.isfinite(matrix).all()
    assert matrix[0, 0] == 0.0
    assert matrix[1, 1] == 0.0
    assert matrix[2, 2] == 0.0
    assert matrix[0, 1] == pytest.approx(matrix[1, 0])
    assert matrix[0, 2] == pytest.approx(matrix[2, 0])
    assert matrix[1, 2] == pytest.approx(matrix[2, 1])
    assert matrix[0, 1] == pytest.approx(11 / 7)
    assert matrix[0, 2] == pytest.approx(9 / 7)
    assert matrix[1, 2] == pytest.approx(2.0)


def _self_inclusive_transition_probabilities(
    sequences: Sequence[Sequence[str]],
) -> dict[tuple[str, str], float]:
    states = tuple(sorted({state for sequence in sequences for state in sequence}))
    counts: dict[tuple[str, str], int] = {}
    denominators = dict.fromkeys(states, 0)
    for sequence in sequences:
        for source, target in zip(sequence, sequence[1:], strict=False):
            denominators[source] += 1
            counts[(source, target)] = counts.get((source, target), 0) + 1
    probabilities: dict[tuple[str, str], float] = {}
    for source in states:
        denominator = denominators[source]
        for target in states:
            probabilities[(source, target)] = (
                0.0
                if denominator == 0
                else counts.get((source, target), 0) / denominator
            )
    return probabilities


def _self_inclusive_substitution_costs(
    sequences: Sequence[Sequence[str]],
) -> dict[tuple[str, str], float]:
    states = tuple(sorted({state for sequence in sequences for state in sequence}))
    probabilities = _self_inclusive_transition_probabilities(sequences)
    costs: dict[tuple[str, str], float] = {}
    for source in states:
        for target in states:
            costs[(source, target)] = (
                0.0
                if source == target
                else 2.0
                - probabilities[(source, target)]
                - probabilities[(target, source)]
            )
    return costs
