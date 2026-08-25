# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module tests the integration of composable survey workflows."""

from collections.abc import Mapping

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import athenspop.clustering.hierarchical
import athenspop.model.survey
import athenspop.scheduling.engine
import athenspop.sequence.distance
import athenspop.sequence.episodes
import athenspop.validation.schema
import athenspop.visualization.dendrogram


def _travel_time(
    origin: str, destination: str, mode: str, departure_second: int
) -> int:
    """Return a fixed duration for portable callable-timing tests."""
    del origin, destination, mode, departure_second
    return 900


@pytest.mark.parametrize(
    ("first_timing", "second_timing", "use_travel_time_function"),
    [
        (
            {"departure_second": 600, "arrival_second": 1_500},
            {"departure_second": 7_800, "arrival_second": 8_700},
            False,
        ),
        (
            {"departure_second": 600, "travel_time_seconds": 900},
            {"departure_second": 7_800, "travel_time_seconds": 900},
            False,
        ),
        (
            {"departure_second": 600},
            {"departure_second": 7_800},
            True,
        ),
        (
            {
                "earliest_departure_second": 600,
                "latest_departure_second": 1_200,
                "travel_time_seconds": 900,
            },
            {
                "earliest_departure_second": 7_800,
                "latest_departure_second": 8_400,
                "travel_time_seconds": 900,
            },
            False,
        ),
        (
            {
                "earliest_departure_second": 600,
                "latest_departure_second": 1_200,
            },
            {
                "earliest_departure_second": 7_800,
                "latest_departure_second": 8_400,
            },
            True,
        ),
    ],
)
def test_supported_timing_patterns_compose_through_the_complete_workflow(
    first_timing: Mapping[str, int],
    second_timing: Mapping[str, int],
    use_travel_time_function: bool,
) -> None:
    """Preserve metadata while composing every supported timing pattern."""
    trip_rows: list[Mapping[str, object]] = []
    person_rows: list[dict[str, object]] = []
    household_rows: list[dict[str, object]] = []
    for index, (purpose, mode_name) in enumerate(
        (("work", "car"), ("education", "bus"), ("shop", "walk")), start=1
    ):
        household_id = f"household_{index}"
        person_id = f"person_{index}"
        person_rows.append(
            {
                "household_id": household_id,
                "person_id": person_id,
                "person_weight": 1.25,
            }
        )
        household_rows.append({"household_id": household_id, "vehicle_count": 1})
        trip_rows.extend(
            (
                {
                    "household_id": household_id,
                    "person_id": person_id,
                    "trip_id": f"{person_id}_trip_1",
                    "trip_sequence": 1,
                    "origin": "home",
                    "destination": f"{purpose}_zone",
                    "purpose": purpose,
                    "mode": mode_name,
                    "source_survey": "portable_fixture",
                    **first_timing,
                },
                {
                    "household_id": household_id,
                    "person_id": person_id,
                    "trip_id": f"{person_id}_trip_2",
                    "trip_sequence": 2,
                    "origin": f"{purpose}_zone",
                    "destination": "home",
                    "purpose": "home",
                    "mode": mode_name,
                    "source_survey": "portable_fixture",
                    **second_timing,
                },
            )
        )

    trips = pd.DataFrame(trip_rows)
    persons = pd.DataFrame(person_rows)
    households = pd.DataFrame(household_rows)
    result = athenspop.validation.schema.validate_dataframes(
        trips, persons=persons, households=households
    )
    result.report.raise_if_invalid()
    travel_time_function = _travel_time if use_travel_time_function else None
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips,
        persons=persons,
        households=households,
        travel_time_function=travel_time_function,
    )
    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=2026,
        config=athenspop.scheduling.engine.SchedulingConfig(
            observation_window_seconds=14_400,
            min_activity_duration_seconds=600,
        ),
    )

    assert not scheduled.diagnostics.has_errors
    first_diary = scheduled.dataset.diaries[0]
    assert first_diary.trips[0].metadata["source_survey"] == "portable_fixture"
    assert first_diary.person is not None
    assert first_diary.person.values["person_weight"] == 1.25
    assert first_diary.household is not None
    assert first_diary.household.values["vehicle_count"] == 1

    sequences = tuple(
        athenspop.sequence.episodes.state_sequence_from_diary(
            diary,
            initial_activity_state="home",
            window_end_second=14_400,
            interval_seconds=1_800,
        )
        for diary in scheduled.dataset.diaries
    )
    states = {state for row in sequences for state in row}
    substitution_cost = {
        (source, target): 0.0 if source == target else 1.0
        for source in states
        for target in states
    }
    distances = athenspop.sequence.distance.dissimilarity_matrix(
        sequences, substitution_cost=substitution_cost
    )
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(distances)
    figure_object = (
        athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
            linkage_matrix, sequences, n_clusters=2
        )
    )
    try:
        labels = athenspop.clustering.hierarchical.flat_cluster_labels(
            linkage_matrix, n_clusters=2
        )
        distribution = athenspop.clustering.hierarchical.cluster_time_distribution(
            sequences, tuple(int(label) for label in labels)
        )
        assert distances.shape == (3, 3)
        assert not distribution.empty
    finally:
        plt.close(figure_object)
