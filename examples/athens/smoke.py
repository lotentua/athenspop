"""Executable miniature of the canonical paper-reproduction pipeline."""

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from athenspop import (
    DendrogramLayout,
    ScheduledSurveyDataset,
    SchedulingConfig,
    SurveyDataset,
    ValidationReport,
    average_linkage,
    cluster_size_summary,
    cluster_state_distribution,
    dendrogram_layout,
    flat_cluster_labels,
    schedule_once,
    validate_dataframes,
)
from athenspop.clustering import ClusterLabels, LinkageMatrix
from athenspop.types import DissimilarityMatrix, TravelTimeFunction
from examples.athens.method import (
    athens_dissimilarity_matrix,
    compound_sequence_from_diary,
)

type ScheduledSurveyTransform = Callable[
    [ScheduledSurveyDataset], ScheduledSurveyDataset
]


@dataclass(frozen=True, slots=True)
class AthensSmokeOutputs:
    """Outputs from the miniature paper pipeline."""

    validation_report: ValidationReport
    dataset: SurveyDataset
    scheduled: ScheduledSurveyDataset
    sequences: tuple[tuple[str, ...], ...]
    dissimilarity_matrix: DissimilarityMatrix
    linkage_matrix: LinkageMatrix
    labels: ClusterLabels
    cluster_sizes: pd.DataFrame
    state_distribution: pd.DataFrame
    dendrogram: DendrogramLayout


def run_example() -> AthensSmokeOutputs:
    """Run a tiny deterministic version of the CSuM2026-oriented workflow."""
    trips, persons, households = build_example_dataframes()
    return run_pipeline(trips, persons, households)


def run_pipeline(
    trips: pd.DataFrame,
    persons: pd.DataFrame,
    households: pd.DataFrame,
    *,
    travel_time_function: TravelTimeFunction | None = None,
    allow_infeasible_diaries: bool = False,
    n_clusters: int = 2,
    scheduled_transform: ScheduledSurveyTransform | None = None,
) -> AthensSmokeOutputs:
    """Run the canonical sequence and clustering pipeline for supplied canonical dataframes."""
    validation = validate_dataframes(
        trips,
        persons=persons,
        households=households,
        travel_time_function=travel_time_function,
    )
    validation.report.raise_if_invalid()
    dataset = SurveyDataset.from_dataframes(
        trips,
        persons=persons,
        households=households,
        travel_time_function=travel_time_function,
    )
    scheduled = schedule_once(
        dataset,
        seed=2026,
        config=SchedulingConfig(
            min_activity_duration_seconds=1800,
            allow_trips_after_observation_window=True,
        ),
        travel_time_function=travel_time_function,
    )
    if scheduled.diagnostics.has_errors and not allow_infeasible_diaries:
        issue_codes = ", ".join(
            issue.code for issue in scheduled.diagnostics.issues
        )
        raise RuntimeError(
            f"The paper pipeline expected every supplied diary to schedule, but got: {issue_codes}."
        )
    if scheduled_transform is not None:
        scheduled = scheduled_transform(scheduled)
        if scheduled.diagnostics.has_errors and not allow_infeasible_diaries:
            issue_codes = ", ".join(
                issue.code for issue in scheduled.diagnostics.issues
            )
            raise RuntimeError(
                f"The paper pipeline expected transformed diaries to schedule, but got: {issue_codes}."
            )
    sequences = tuple(
        compound_sequence_from_diary(diary) for diary in scheduled.diaries
    )
    dissimilarity_matrix = athens_dissimilarity_matrix(sequences)
    linkage_matrix = average_linkage(dissimilarity_matrix)
    labels = flat_cluster_labels(linkage_matrix, n_clusters=n_clusters)
    label_tuple = tuple(int(label) for label in labels.tolist())
    diary_labels = tuple(
        f"{diary.household_id}:{diary.person_id}" for diary in scheduled.diaries
    )
    return AthensSmokeOutputs(
        validation_report=validation.report,
        dataset=dataset,
        scheduled=scheduled,
        sequences=sequences,
        dissimilarity_matrix=dissimilarity_matrix,
        linkage_matrix=linkage_matrix,
        labels=labels,
        cluster_sizes=cluster_size_summary(label_tuple),
        state_distribution=cluster_state_distribution(sequences, label_tuple),
        dendrogram=dendrogram_layout(linkage_matrix, labels=diary_labels),
    )


def build_example_dataframes() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame
]:
    """Return canonical `trips`, `persons`, and `households` dataframes for the smoke example."""
    trips = pd.DataFrame(
        [
            _trip(
                "h1",
                "p1",
                "p1_t1",
                1,
                "home",
                "work",
                "work",
                "bus",
                earliest_departure_second=14400,
                latest_departure_second=15300,
                travel_time_seconds=1800,
            ),
            _trip(
                "h1",
                "p1",
                "p1_t2",
                2,
                "work",
                "home",
                "home",
                "bus",
                departure_second=32400,
                arrival_second=34200,
            ),
            _trip(
                "h1",
                "p2",
                "p2_t1",
                1,
                "home",
                "market",
                "market",
                "walk",
                departure_second=19800,
                arrival_second=20700,
            ),
            _trip(
                "h1",
                "p2",
                "p2_t2",
                2,
                "market",
                "home",
                "home",
                "walk",
                earliest_departure_second=25200,
                latest_departure_second=27000,
                travel_time_seconds=900,
            ),
            _trip(
                "h2",
                "p1",
                "p3_t1",
                1,
                "home",
                "education",
                "education",
                "car",
                departure_second=10800,
                arrival_second=12600,
            ),
            _trip(
                "h2",
                "p1",
                "p3_t2",
                2,
                "education",
                "service",
                "service",
                "car",
                departure_second=23400,
                arrival_second=25200,
            ),
            _trip(
                "h2",
                "p1",
                "p3_t3",
                3,
                "service",
                "home",
                "home",
                "car",
                departure_second=32400,
                arrival_second=34200,
            ),
        ]
    )
    for column in (
        "trip_sequence",
        "departure_second",
        "arrival_second",
        "travel_time_seconds",
        "earliest_departure_second",
        "latest_departure_second",
    ):
        trips[column] = trips[column].astype("Int64")
    persons = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "age": 42,
                "employment_status": "worker",
            },
            {
                "household_id": "h1",
                "person_id": "p2",
                "age": 20,
                "employment_status": "student",
            },
            {
                "household_id": "h2",
                "person_id": "p1",
                "age": 35,
                "employment_status": "worker",
            },
        ]
    )
    households = pd.DataFrame(
        [
            {"household_id": "h1", "home_zone": "home", "vehicles": 1},
            {"household_id": "h2", "home_zone": "home", "vehicles": 2},
        ]
    )
    return trips, persons, households


def main() -> None:
    """Run the example as a directly executed script and print compact stage counts."""
    outputs = run_example()
    print(
        f"validated errors={len(outputs.validation_report.errors)} warnings={len(outputs.validation_report.warnings)}"
    )
    print(
        f"scheduled diaries={outputs.scheduled.diagnostics.scheduled_diaries}"
    )
    print(
        f"sequence shape={len(outputs.sequences)}x{len(outputs.sequences[0])}"
    )
    print(outputs.cluster_sizes.to_string(index=False))


def _trip(
    household_id: str,
    person_id: str,
    trip_id: str,
    trip_sequence: int,
    origin: str,
    destination: str,
    purpose: str,
    mode: str,
    *,
    departure_second: int | None = None,
    arrival_second: int | None = None,
    travel_time_seconds: int | None = None,
    earliest_departure_second: int | None = None,
    latest_departure_second: int | None = None,
) -> dict[str, str | int | None]:
    return {
        "household_id": household_id,
        "person_id": person_id,
        "trip_id": trip_id,
        "trip_sequence": trip_sequence,
        "origin": origin,
        "destination": destination,
        "purpose": purpose,
        "mode": mode,
        "departure_second": departure_second,
        "arrival_second": arrival_second,
        "travel_time_seconds": travel_time_seconds,
        "earliest_departure_second": earliest_departure_second,
        "latest_departure_second": latest_departure_second,
    }


if __name__ == "__main__":
    main()
