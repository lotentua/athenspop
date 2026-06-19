from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
from matplotlib.figure import Figure

from athenspop.clustering import average_linkage, cluster_time_distribution, flat_cluster_labels
from athenspop.model import SurveyDataset
from athenspop.scheduling import SchedulingConfig, schedule_once
from athenspop.sequence import dissimilarity_matrix, state_sequence_from_diary
from athenspop.validation import validate_dataframes
from athenspop.visualization import plot_cut_dendrogram_state_distribution

type PortableTravelTimeFunction = Callable[[str, str, str, int], int]
type PortableTables = tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None, PortableTravelTimeFunction | None]
type TableFactory = Callable[[], PortableTables]
type FixtureMetadataValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class _TripFixtureSpec:
    """Raw fields used to build one mapped trip-row fixture."""

    prefix: str
    household_id: str
    person_id: str
    sequence: int
    origin: str
    destination: str
    purpose: str
    mode: str
    departure_second: int
    timing: str


def test_mentioned_survey_families_fit_the_same_generic_workflow() -> None:
    for survey_name, factory in _portable_survey_tables().items():
        trips, persons, households, travel_time_function = factory()

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
            config=SchedulingConfig(observation_window_seconds=14_400, min_activity_duration_seconds=600),
            travel_time_function=travel_time_function,
        )

        assert not scheduled.diagnostics.has_errors, survey_name

        sequences = tuple(
            state_sequence_from_diary(
                diary,
                initial_activity_state="home",
                travel_state_labeler=lambda trip: f"travel_{trip.mode}",
                window_end_second=14_400,
                interval_seconds=1_800,
            )
            for diary in scheduled.diaries
        )
        substitution_cost = _unit_substitution_cost(sequences)
        distances = dissimilarity_matrix(sequences, substitution_cost=substitution_cost)
        linkage_matrix = average_linkage(distances)
        labels = flat_cluster_labels(linkage_matrix, n_clusters=2)
        temporal_distribution = cluster_time_distribution(sequences, tuple(int(label) for label in labels.tolist()))
        figure = plot_cut_dendrogram_state_distribution(linkage_matrix, sequences, n_clusters=2)

        assert distances.shape == (3, 3), survey_name
        assert temporal_distribution.empty is False, survey_name
        assert isinstance(figure, Figure), survey_name


def _portable_survey_tables() -> dict[str, TableFactory]:
    return {
        "athens_style_wide_mapping": _athens_style_tables,
        "uk_nts_pam_style_mapping": _uk_nts_pam_style_tables,
        "us_nhts_style_mapping": _us_nhts_style_tables,
        "france_entd_emp_style_mapping": _france_entd_emp_style_tables,
        "activitysim_style_generated_trips": _activitysim_style_tables,
        "populationsim_adjacent_metadata": _populationsim_adjacent_tables,
    }


def _athens_style_tables() -> PortableTables:
    return _base_tables("athens", timing="departure_arrival", person_extra={"income_band": "medium"}, household_extra={"home_zone": "athens_home"})


def _uk_nts_pam_style_tables() -> PortableTables:
    return _base_tables("uk", timing="departure_arrival", person_extra={"nts_weight": 1.25}, household_extra={"hzone": "uk_home"})


def _us_nhts_style_tables() -> PortableTables:
    return _base_tables("nhts", timing="departure_duration", person_extra={"travday": "weekday"}, household_extra={"vehicle_count": 1})


def _france_entd_emp_style_tables() -> PortableTables:
    return _base_tables("emp", timing="departure_window_duration", person_extra={"selected_individual": True}, household_extra={"vehicle_equipment": "car"})


def _activitysim_style_tables() -> PortableTables:
    return _base_tables("activitysim", timing="departure_window_function", person_extra={"time_window_id": "available"}, household_extra={"sample_rate": 1.0})


def _populationsim_adjacent_tables() -> PortableTables:
    return _base_tables(
        "populationsim", timing="departure_duration", person_extra={"synthetic_person_weight": 1.0}, household_extra={"synthetic_household_weight": 1.0}
    )


def _base_tables(
    prefix: str,
    *,
    timing: str,
    person_extra: dict[str, FixtureMetadataValue],
    household_extra: dict[str, FixtureMetadataValue],
) -> PortableTables:
    trip_rows: list[dict[str, FixtureMetadataValue]] = []
    person_rows: list[dict[str, FixtureMetadataValue]] = []
    household_rows: list[dict[str, FixtureMetadataValue]] = []
    patterns = (
        ("work", "car"),
        ("education", "bus"),
        ("shop", "walk"),
    )

    for person_index, (purpose, mode) in enumerate(patterns, start=1):
        household_id = f"{prefix}_household_{person_index}"
        person_id = f"{prefix}_person_{person_index}"
        person_rows.append({"household_id": household_id, "person_id": person_id, **person_extra})
        household_rows.append({"household_id": household_id, **household_extra})
        first_departure = person_index * 600
        trip_rows.extend(
            [
                _trip_row(
                    _TripFixtureSpec(
                        prefix=prefix,
                        household_id=household_id,
                        person_id=person_id,
                        sequence=1,
                        origin="home",
                        destination=f"{purpose}_zone",
                        purpose=purpose,
                        mode=mode,
                        departure_second=first_departure,
                        timing=timing,
                    )
                ),
                _trip_row(
                    _TripFixtureSpec(
                        prefix=prefix,
                        household_id=household_id,
                        person_id=person_id,
                        sequence=2,
                        origin=f"{purpose}_zone",
                        destination="home",
                        purpose="home",
                        mode=mode,
                        departure_second=first_departure + 7_200,
                        timing=timing,
                    )
                ),
            ]
        )

    travel_time_function = _portable_travel_time if timing == "departure_window_function" else None
    return pd.DataFrame(trip_rows), pd.DataFrame(person_rows), pd.DataFrame(household_rows), travel_time_function


def _trip_row(spec: _TripFixtureSpec) -> dict[str, FixtureMetadataValue]:
    row: dict[str, FixtureMetadataValue] = {
        "household_id": spec.household_id,
        "person_id": spec.person_id,
        "trip_id": f"{spec.person_id}_trip_{spec.sequence}",
        "trip_sequence": spec.sequence,
        "origin": spec.origin,
        "destination": spec.destination,
        "purpose": spec.purpose,
        "mode": spec.mode,
        "source_survey": spec.prefix,
    }
    if spec.timing == "departure_arrival":
        row["departure_second"] = spec.departure_second
        row["arrival_second"] = spec.departure_second + 900
    elif spec.timing == "departure_duration":
        row["departure_second"] = spec.departure_second
        row["travel_time_seconds"] = 900
    elif spec.timing == "departure_window_duration":
        row["earliest_departure_second"] = spec.departure_second
        row["latest_departure_second"] = spec.departure_second + 600
        row["travel_time_seconds"] = 900
    elif spec.timing == "departure_window_function":
        row["earliest_departure_second"] = spec.departure_second
        row["latest_departure_second"] = spec.departure_second + 600
    else:
        raise ValueError(f"Unsupported timing fixture: {spec.timing}.")
    return row


def _portable_travel_time(origin: str, destination: str, mode: str, departure_second: int) -> int:
    del origin, destination, mode, departure_second
    return 900


def _unit_substitution_cost(sequences: tuple[tuple[str, ...], ...]) -> dict[tuple[str, str], float]:
    states = sorted({state for sequence in sequences for state in sequence})
    return {(source, target): 0.0 if source == target else 1.0 for source in states for target in states}
