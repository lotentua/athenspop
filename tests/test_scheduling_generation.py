from collections.abc import Callable

import pandas as pd
import pytest

from athenspop import SchedulingConfig, SurveyDataset, generate_schedules, schedule_once

type TravelTimeFn = Callable[[str, str, str, int], int]


def _constant_travel_time(seconds: int) -> TravelTimeFn:
    def travel_time_fn(origin: str, destination: str, mode: str, departure_second: int) -> int:
        del origin, destination, mode, departure_second
        return seconds

    return travel_time_fn


def test_schedule_once_preserves_concrete_trips_and_metadata() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "departure_second": 0,
                "arrival_second": 900,
            }
        ],
        dtype=object,
    )
    dataset = SurveyDataset.from_dataframes(trips)
    scheduled = schedule_once(dataset)
    assert scheduled.diagnostics.attempted_diaries == 1
    assert scheduled.diagnostics.scheduled_diaries == 1
    assert not scheduled.diagnostics.has_errors
    trip = scheduled.diaries[0].trips[0]
    assert trip.departure_second == 0
    assert trip.arrival_second == 900
    assert trip.travel_time_seconds == 900


def test_schedule_once_realizes_departure_window_with_seeded_uniform_sampling() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "trip_sequence": 1,
                "earliest_departure_second": 100,
                "latest_departure_second": 110,
                "travel_time_seconds": 30,
            }
        ]
    )
    dataset = SurveyDataset.from_dataframes(trips)
    first = schedule_once(dataset, seed=42)
    second = schedule_once(dataset, seed=42)
    first_trip = first.diaries[0].trips[0]
    second_trip = second.diaries[0].trips[0]
    assert first_trip.departure_second == second_trip.departure_second
    assert first_trip.departure_second is not None
    assert 100 <= first_trip.departure_second <= 110
    assert first_trip.arrival_second == first_trip.departure_second + 30
    assert first_trip.departure_window is None


def test_schedule_once_applies_activity_duration_constraint_to_later_windows() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "trip_sequence": 1,
                "departure_second": 100,
                "travel_time_seconds": 100,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "home",
                "purpose": "home",
                "mode": "car",
                "trip_sequence": 2,
                "earliest_departure_second": 250,
                "latest_departure_second": 300,
                "travel_time_seconds": 100,
            },
        ],
        dtype=object,
    )
    dataset = SurveyDataset.from_dataframes(trips)
    scheduled = schedule_once(dataset, config=SchedulingConfig(min_activity_duration_seconds=50), seed=7)
    assert scheduled.diagnostics.scheduled_diaries == 1
    second_departure = scheduled.diaries[0].trips[1].departure_second
    assert second_departure is not None
    assert 250 <= second_departure <= 300
    infeasible = schedule_once(dataset, config=SchedulingConfig(min_activity_duration_seconds=150), seed=7)
    assert infeasible.diagnostics.scheduled_diaries == 0
    assert infeasible.diagnostics.infeasible_diaries == ("household_id=h1; person_id=p1",)
    assert infeasible.diagnostics.issues[0].code == "infeasible_future_departure"


def test_schedule_once_refines_windows_against_future_fixed_duration_trips() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "trip_sequence": 1,
                "earliest_departure_second": 0,
                "latest_departure_second": 10_800,
                "travel_time_seconds": 900,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "shop",
                "purpose": "market",
                "mode": "car",
                "trip_sequence": 2,
                "earliest_departure_second": 46_800,
                "latest_departure_second": 57_600,
                "travel_time_seconds": 900,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t3",
                "origin": "shop",
                "destination": "home",
                "purpose": "home",
                "mode": "car",
                "trip_sequence": 3,
                "earliest_departure_second": 46_800,
                "latest_departure_second": 57_600,
                "travel_time_seconds": 900,
            },
        ]
    )
    dataset = SurveyDataset.from_dataframes(trips)
    scheduled = schedule_once(dataset, seed=2026, config=SchedulingConfig(min_activity_duration_seconds=1800))
    assert scheduled.diagnostics.scheduled_diaries == 1
    second_trip = scheduled.diaries[0].trips[1]
    third_trip = scheduled.diaries[0].trips[2]
    assert second_trip.departure_second is not None
    assert second_trip.arrival_second is not None
    assert third_trip.departure_second is not None
    assert second_trip.departure_second <= 54_900
    assert third_trip.departure_second >= second_trip.arrival_second + 1800


def test_schedule_once_refines_windows_against_future_callable_trips() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "trip_sequence": 1,
                "earliest_departure_second": 0,
                "latest_departure_second": 1_000,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "home",
                "purpose": "home",
                "mode": "car",
                "trip_sequence": 2,
                "earliest_departure_second": 1_200,
                "latest_departure_second": 1_200,
            },
        ]
    )

    def travel_time_fn(origin: str, destination: str, mode: str, departure_second: int) -> int:
        del origin, destination, mode, departure_second
        return 500

    dataset = SurveyDataset.from_dataframes(trips, travel_time_fn=travel_time_fn)
    scheduled = schedule_once(
        dataset,
        seed=2026,
        config=SchedulingConfig(min_activity_duration_seconds=100),
        travel_time_fn=travel_time_fn,
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    first_trip = scheduled.diaries[0].trips[0]
    second_trip = scheduled.diaries[0].trips[1]
    assert first_trip.departure_second is not None
    assert first_trip.departure_second <= 600
    assert first_trip.arrival_second == first_trip.departure_second + 500
    assert second_trip.departure_second == 1_200


def test_schedule_once_checks_travel_time_function_at_scheduler_boundary() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "walk",
                "trip_sequence": 1,
                "earliest_departure_second": 100,
                "latest_departure_second": 100,
            }
        ]
    )
    dataset = SurveyDataset.from_dataframes(trips, travel_time_fn=_constant_travel_time(1))
    scheduled = schedule_once(
        dataset,
        seed=1,
        travel_time_fn=_constant_travel_time(75),
    )
    assert scheduled.diaries[0].trips[0].arrival_second == 175
    invalid = schedule_once(
        dataset,
        seed=1,
        travel_time_fn=_constant_travel_time(0),
    )
    assert invalid.diagnostics.scheduled_diaries == 0
    assert invalid.diagnostics.issues[0].code == "invalid_travel_time_function_result"


def test_generate_schedules_uses_shared_scheduler_with_repeatable_seed() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "trip_sequence": 1,
                "earliest_departure_second": 0,
                "latest_departure_second": 1000,
                "travel_time_seconds": 60,
            }
        ]
    )
    dataset = SurveyDataset.from_dataframes(trips)
    first = generate_schedules(dataset, 3, seed=99)
    second = generate_schedules(dataset, 3, seed=99)
    assert [run.diaries[0].trips[0].departure_second for run in first] == [run.diaries[0].trips[0].departure_second for run in second]
    assert len({run.diaries[0].trips[0].departure_second for run in first}) > 1
    assert generate_schedules(dataset, 0, seed=99) == ()
    with pytest.raises(ValueError, match="non-negative"):
        generate_schedules(dataset, -1)


def test_schedule_once_can_impute_return_home_trip_with_provenance() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "departure_second": 0,
                "travel_time_seconds": 100,
            }
        ]
    )
    households = pd.DataFrame([{"household_id": "h1", "home_zone": "home"}])
    dataset = SurveyDataset.from_dataframes(trips, households=households)
    scheduled = schedule_once(
        dataset,
        config=SchedulingConfig(min_activity_duration_seconds=50, impute_return_home=True),
        travel_time_fn=_constant_travel_time(75),
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    assert len(scheduled.diaries[0].trips) == 2
    imputed = scheduled.diaries[0].trips[1]
    assert imputed.trip_id == "__imputed_return_home__2"
    assert imputed.origin == "work"
    assert imputed.destination == "home"
    assert imputed.departure_second == 150
    assert imputed.arrival_second == 225
    assert imputed.metadata["is_imputed_return_home"] is True


def test_schedule_once_does_not_impute_after_final_recreation() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "cinema",
                "purpose": "recreation",
                "mode": "walk",
                "departure_second": 0,
                "travel_time_seconds": 100,
            }
        ]
    )
    households = pd.DataFrame([{"household_id": "h1", "home_zone": "home"}])
    dataset = SurveyDataset.from_dataframes(trips, households=households)
    scheduled = schedule_once(
        dataset,
        config=SchedulingConfig(impute_return_home=True),
        travel_time_fn=_constant_travel_time(75),
    )
    assert len(scheduled.diaries[0].trips) == 1


def test_schedule_once_can_impute_return_after_observation_window_for_cropping() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "departure_second": 86_000,
                "travel_time_seconds": 1_000,
            }
        ]
    )
    households = pd.DataFrame([{"household_id": "h1", "home_zone": "home"}])
    dataset = SurveyDataset.from_dataframes(trips, households=households)
    rejected = schedule_once(
        dataset,
        config=SchedulingConfig(
            impute_return_home=True,
            allow_final_trip_after_observation_window=True,
        ),
        travel_time_fn=_constant_travel_time(75),
    )
    assert rejected.diagnostics.scheduled_diaries == 0
    assert rejected.diagnostics.issues[0].code == "imputed_return_after_observation_window"
    scheduled = schedule_once(
        dataset,
        config=SchedulingConfig(
            impute_return_home=True,
            allow_trips_after_observation_window=True,
        ),
        travel_time_fn=_constant_travel_time(75),
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    assert len(scheduled.diaries[0].trips) == 2
    assert scheduled.diaries[0].trips[1].departure_second == 88_800


def test_schedule_once_can_allow_final_arrival_after_observation_window() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "cinema",
                "purpose": "recreation",
                "mode": "walk",
                "departure_second": 86_000,
                "travel_time_seconds": 1_000,
            }
        ]
    )
    dataset = SurveyDataset.from_dataframes(trips)
    rejected = schedule_once(dataset)
    assert rejected.diagnostics.scheduled_diaries == 0
    assert rejected.diagnostics.issues[0].code == "arrival_after_observation_window"
    scheduled = schedule_once(
        dataset,
        config=SchedulingConfig(allow_final_trip_after_observation_window=True),
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    assert scheduled.diaries[0].trips[0].arrival_second == 87_000


def test_schedule_once_can_allow_nonfinal_trips_after_observation_window() -> None:
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "trip_sequence": 1,
                "departure_second": 80_000,
                "travel_time_seconds": 1_000,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "home",
                "purpose": "home",
                "mode": "bus",
                "trip_sequence": 2,
                "earliest_departure_second": 90_000,
                "latest_departure_second": 100_000,
                "travel_time_seconds": 1_000,
            },
        ]
    )
    for column in (
        "trip_sequence",
        "departure_second",
        "travel_time_seconds",
        "earliest_departure_second",
        "latest_departure_second",
    ):
        trips[column] = trips[column].astype("Int64")
    dataset = SurveyDataset.from_dataframes(trips)
    rejected = schedule_once(dataset)
    assert rejected.diagnostics.scheduled_diaries == 0
    assert rejected.diagnostics.issues[0].code == "infeasible_departure_window"
    scheduled = schedule_once(
        dataset,
        seed=7,
        config=SchedulingConfig(allow_trips_after_observation_window=True),
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    assert scheduled.diaries[0].trips[1].departure_second is not None
    assert 90_000 <= scheduled.diaries[0].trips[1].departure_second <= 100_000
