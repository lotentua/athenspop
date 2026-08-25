# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Compose validation, scheduling, sequencing, clustering, and visualization."""

from collections.abc import Mapping

import matplotlib.figure
import matplotlib.pyplot as plt
import pandas as pd

import athenspop.clustering.hierarchical
import athenspop.model.survey
import athenspop.scheduling.engine
import athenspop.sequence.distance
import athenspop.sequence.episodes
import athenspop.visualization.dendrogram


def travel_time(origin: str, destination: str, mode: str, departure_second: int) -> int:
    """Return a deterministic duration for the self-contained example.

    Args:
        origin:
            Origin location label.
        destination:
            Destination location label.
        mode:
            Movement-mode label.
        departure_second:
            Candidate departure in seconds from the diary time origin.

    Returns:
        Fifteen minutes for every synthetic movement.
    """
    del origin, destination, mode, departure_second
    return 900


def example_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return small long-form trip and person tables for three respondents."""
    trips: list[Mapping[str, object]] = []
    persons: list[dict[str, object]] = []
    for index, (purpose, mode_name) in enumerate(
        (("work", "bus"), ("education", "walk"), ("market", "car")), start=1
    ):
        household_id = f"h{index}"
        person_id = f"p{index}"
        persons.append(
            {
                "household_id": household_id,
                "person_id": person_id,
                "segment": "demonstration",
            }
        )
        trips.extend(
            (
                {
                    "household_id": household_id,
                    "person_id": person_id,
                    "trip_id": f"{person_id}_1",
                    "trip_sequence": 1,
                    "origin": "home",
                    "destination": purpose,
                    "purpose": purpose,
                    "mode": mode_name,
                    "earliest_departure_second": 1_800,
                    "latest_departure_second": 8_000,
                },
                {
                    "household_id": household_id,
                    "person_id": person_id,
                    "trip_id": f"{person_id}_2",
                    "trip_sequence": 2,
                    "origin": purpose,
                    "destination": "home",
                    "purpose": "home",
                    "mode": mode_name,
                    "earliest_departure_second": 8_100,
                    "latest_departure_second": 9_000,
                },
            )
        )
    return pd.DataFrame(trips), pd.DataFrame(persons)


def build_figure() -> matplotlib.figure.Figure:
    """Run the complete composition and return its temporal dendrogram figure."""
    trips, persons = example_tables()
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, persons=persons, travel_time_function=travel_time
    )
    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=2026,
        config=athenspop.scheduling.engine.SchedulingConfig(
            observation_window_seconds=14_400,
            min_activity_duration_seconds=900,
        ),
    )
    if scheduled.diagnostics.has_errors:
        raise RuntimeError("Not every synthetic diary could be scheduled.")
    sequences = tuple(
        athenspop.sequence.episodes.state_sequence_from_diary(
            diary,
            initial_activity_state="home",
            window_end_second=14_400,
            interval_seconds=900,
        )
        for diary in scheduled.dataset.diaries
    )
    states = {state for row in sequences for state in row}
    travel_states = {"trip_bus", "trip_car", "trip_walk"}
    if not travel_states <= states:
        raise RuntimeError(
            "The synthetic schedule must represent every configured travel state."
        )
    costs = {
        (source, target): 0.0 if source == target else 1.0
        for source in states
        for target in states
    }
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(
        athenspop.sequence.distance.dissimilarity_matrix(
            sequences, substitution_cost=costs
        )
    )
    return athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution(
        linkage_matrix,
        sequences,
        n_clusters=2,
        style=athenspop.visualization.dendrogram.TemporalDendrogramPlotStyle(
            title="Synthetic activity and travel states",
            state_groups={
                "Activity states": (
                    "education",
                    "home",
                    "market",
                    "work",
                ),
                "Travel states": (*sorted(travel_states),),
            },
            state_labels={
                "education": "Education",
                "home": "Home",
                "market": "Market",
                "trip_bus": "Bus",
                "trip_car": "Car",
                "trip_walk": "Walk",
                "work": "Work",
            },
        ),
    )


def main() -> None:
    """Display the composed example while deferring style to Matplotlib."""
    build_figure()
    plt.show()


if __name__ == "__main__":
    main()
