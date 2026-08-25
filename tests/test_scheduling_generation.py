# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Scheduling and conditional-generation contracts."""

import dataclasses
import functools
from collections.abc import Callable
from typing import cast

import pandas as pd
import pytest

import athenspop.generation.schedules
import athenspop.model.survey
import athenspop.scheduling.engine
import athenspop.schema
import athenspop.types


def _constant_travel_time(seconds: int) -> athenspop.types.TravelTimeFunction:
    """Return a deterministic travel-time function for a test scenario."""

    def travel_time_function(
        origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        """Return the duration configured by the enclosing test."""
        del origin, destination, mode, departure_second
        return seconds

    return travel_time_function


def _trusted_trip(**overrides: object) -> athenspop.model.survey.Trip:
    """Return a valid scheduled trip with selected values replaced."""
    base = athenspop.model.survey.Trip(
        household_id="h1",
        person_id="p1",
        trip_id="t1",
        origin="home",
        destination="work",
        purpose="work",
        mode="bus",
        departure_second=0,
        arrival_second=900,
        travel_time_seconds=900,
        departure_window=None,
        timing_pattern=athenspop.schema.TimingPattern.DEPARTURE_ARRIVAL,
        metadata={},
    )
    return dataclasses.replace(base, **overrides)


def _trusted_dataset(
    *trips: athenspop.model.survey.Trip,
) -> athenspop.model.survey.SurveyDataset:
    """Wrap trusted trips in a minimal survey dataset."""
    return athenspop.model.survey.SurveyDataset(
        diaries=(
            athenspop.model.survey.Diary(
                household_id="h1",
                person_id="p1",
                trips=trips,
            ),
        ),
        households=(),
        persons=(),
    )


@pytest.mark.parametrize(
    ("factory", "error_type", "message"),
    [
        (
            functools.partial(
                athenspop.scheduling.engine.SchedulingConfig,
                min_activity_duration_seconds=-1,
            ),
            ValueError,
            "non-negative",
        ),
        (
            functools.partial(
                athenspop.scheduling.engine.SchedulingConfig,
                min_activity_duration_seconds=True,
            ),
            TypeError,
            "integer",
        ),
        (
            functools.partial(
                athenspop.scheduling.engine.SchedulingConfig,
                observation_window_seconds=0,
            ),
            ValueError,
            "positive",
        ),
        (
            functools.partial(
                athenspop.scheduling.engine.SchedulingConfig,
                observation_window_seconds=False,
            ),
            TypeError,
            "integer",
        ),
        (
            functools.partial(
                athenspop.scheduling.engine.SchedulingConfig,
                allow_trips_after_observation_window=cast("bool", 1),
            ),
            TypeError,
            "boolean",
        ),
        (
            functools.partial(
                athenspop.scheduling.engine.SchedulingConfig,
                allow_final_trip_after_observation_window=cast("bool", 1),
            ),
            TypeError,
            "boolean",
        ),
        (
            functools.partial(
                athenspop.scheduling.engine.SchedulingConfig,
                refine_callable_departure_windows=cast("bool", 1),
            ),
            TypeError,
            "boolean",
        ),
    ],
)
def test_scheduling_config_rejects_invalid_policy_values(
    factory: Callable[[], athenspop.scheduling.engine.SchedulingConfig],
    error_type: type[Exception],
    message: str,
) -> None:
    """Reject invalid scheduling policy types and ranges during construction."""
    with pytest.raises(error_type, match=message):
        factory()


def test_schedule_once_preserves_concrete_trips_and_metadata() -> None:
    """Keep fixed times unchanged and derive their travel duration."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    scheduled = athenspop.scheduling.engine.schedule_once(dataset)
    assert scheduled.diagnostics.attempted_diaries == 1
    assert scheduled.diagnostics.scheduled_diaries == 1
    assert not scheduled.diagnostics.has_errors
    trip = scheduled.dataset.diaries[0].trips[0]
    assert trip.departure_second == 0
    assert trip.arrival_second == 900
    assert trip.travel_time_seconds == 900


def test_schedule_once_reports_missing_departure_for_trusted_model() -> None:
    """Diagnose an unresolved trusted trip that has no departure window."""
    dataset = _trusted_dataset(
        _trusted_trip(
            departure_second=None,
            arrival_second=None,
            travel_time_seconds=None,
            departure_window=None,
        )
    )

    scheduled = athenspop.scheduling.engine.schedule_once(dataset)

    assert scheduled.diagnostics.issues[0].code == "missing_departure"


def test_schedule_once_reports_non_positive_duration() -> None:
    """Diagnose a trusted trip whose arrival does not follow its departure."""
    dataset = _trusted_dataset(
        _trusted_trip(
            departure_second=100,
            arrival_second=100,
            travel_time_seconds=None,
        )
    )

    scheduled = athenspop.scheduling.engine.schedule_once(dataset)

    assert scheduled.diagnostics.issues[0].code == "non_positive_travel_duration"


def test_schedule_once_reports_activity_duration_too_short() -> None:
    """Diagnose an activity gap shorter than the configured minimum."""
    first_trip = _trusted_trip(
        trip_id="t1",
        departure_second=0,
        arrival_second=None,
        travel_time_seconds=None,
    )
    second_trip = _trusted_trip(
        trip_id="t2",
        origin="work",
        destination="home",
        purpose="home",
        departure_second=120,
        arrival_second=200,
        travel_time_seconds=80,
    )
    dataset = _trusted_dataset(first_trip, second_trip)

    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        config=athenspop.scheduling.engine.SchedulingConfig(
            min_activity_duration_seconds=50,
            refine_callable_departure_windows=False,
        ),
        travel_time_function=_constant_travel_time(100),
    )

    assert scheduled.diagnostics.issues[0].code == "activity_duration_too_short"


def test_schedule_once_reports_missing_travel_time_function() -> None:
    """Diagnose a callable timing pattern when no resolver is available."""
    dataset = _trusted_dataset(
        _trusted_trip(
            departure_second=None,
            arrival_second=None,
            travel_time_seconds=None,
            departure_window=athenspop.model.survey.TimeWindow(
                earliest_second=0, latest_second=10
            ),
            timing_pattern=athenspop.schema.TimingPattern.DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION,
        )
    )

    scheduled = athenspop.scheduling.engine.schedule_once(dataset, seed=1)

    assert scheduled.diagnostics.issues[0].code == "missing_travel_time_function"


def test_schedule_once_reports_travel_time_function_error() -> None:
    """Convert a resolver lookup failure into a scheduling diagnostic."""
    dataset = _trusted_dataset(
        _trusted_trip(
            departure_second=None,
            arrival_second=None,
            travel_time_seconds=None,
            departure_window=athenspop.model.survey.TimeWindow(
                earliest_second=0, latest_second=10
            ),
            timing_pattern=athenspop.schema.TimingPattern.DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION,
        )
    )

    def failing_travel_time(
        origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        """Simulate a route lookup failure from an external resolver."""
        del origin, destination, mode, departure_second
        raise LookupError("The requested route is missing.")

    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=1,
        travel_time_function=failing_travel_time,
    )

    assert scheduled.diagnostics.issues[0].code == "travel_time_function_error"


def test_schedule_once_contains_runtime_error_from_user_callable() -> None:
    """Contain a resolver runtime failure within the scheduling result."""
    dataset = _trusted_dataset(
        _trusted_trip(
            departure_second=None,
            arrival_second=None,
            travel_time_seconds=None,
            departure_window=athenspop.model.survey.TimeWindow(
                earliest_second=0, latest_second=10
            ),
            timing_pattern=athenspop.schema.TimingPattern.DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION,
        )
    )

    def failing_travel_time(
        origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        """Simulate an unavailable travel-time backend."""
        del origin, destination, mode, departure_second
        raise RuntimeError("The travel-time backend is unavailable.")

    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=1,
        travel_time_function=failing_travel_time,
    )

    assert scheduled.diagnostics.issues[0].code == "travel_time_function_error"


@pytest.mark.parametrize(
    "metadata_tables",
    [(), ("persons",), ("households",), ("persons", "households")],
)
def test_schedule_once_filters_metadata_to_scheduled_diaries(
    metadata_tables: tuple[str, ...],
) -> None:
    """Remove an infeasible diary and any metadata that only it references."""
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
                "departure_second": 0,
                "arrival_second": 900,
            },
            {
                "household_id": "h2",
                "person_id": "p2",
                "trip_id": "t2",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "trip_sequence": 1,
                "earliest_departure_second": 0,
                "latest_departure_second": 900,
            },
        ]
    )
    for column in (
        "trip_sequence",
        "departure_second",
        "arrival_second",
        "earliest_departure_second",
        "latest_departure_second",
    ):
        trips[column] = trips[column].astype("Int64")
    include_persons = "persons" in metadata_tables
    include_households = "households" in metadata_tables
    persons = (
        pd.DataFrame(
            [
                {"household_id": "h1", "person_id": "p1", "age": 20},
                {"household_id": "h2", "person_id": "p2", "age": 30},
            ]
        )
        if include_persons
        else None
    )
    households = (
        pd.DataFrame(
            [
                {"household_id": "h1", "zone": "a"},
                {"household_id": "h2", "zone": "b"},
            ]
        )
        if include_households
        else None
    )
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips,
        persons=persons,
        households=households,
        travel_time_function=_constant_travel_time(0),
    )

    scheduled = athenspop.scheduling.engine.schedule_once(dataset)

    assert [
        (diary.household_id, diary.person_id) for diary in scheduled.dataset.diaries
    ] == [("h1", "p1")]
    assert scheduled.diagnostics.infeasible_diaries == (
        "household_id=h2; person_id=p2",
    )
    assert [
        (person.household_id, person.person_id) for person in scheduled.dataset.persons
    ] == ([("h1", "p1")] if include_persons else [])
    assert [household.household_id for household in scheduled.dataset.households] == (
        ["h1"] if include_households else []
    )


def test_schedule_once_realizes_seeded_departure_window() -> None:
    """Realize a window reproducibly and replace it with concrete trip times."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    first = athenspop.scheduling.engine.schedule_once(dataset, seed=42)
    second = athenspop.scheduling.engine.schedule_once(dataset, seed=42)
    first_trip = first.dataset.diaries[0].trips[0]
    second_trip = second.dataset.diaries[0].trips[0]
    assert first_trip.departure_second == second_trip.departure_second
    assert first_trip.departure_second is not None
    assert 100 <= first_trip.departure_second <= 110
    assert first_trip.arrival_second == first_trip.departure_second + 30
    assert first_trip.departure_window is None


def test_final_fixed_duration_window_is_bounded_by_arrival_horizon() -> None:
    """Limit a final departure so its fixed-duration arrival stays in bounds."""
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
                "latest_departure_second": 86_400,
                "travel_time_seconds": 100,
            }
        ]
    )
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)

    scheduled = athenspop.scheduling.engine.schedule_once(dataset, seed=291)

    trip = scheduled.dataset.diaries[0].trips[0]
    assert trip.departure_second is not None
    assert trip.departure_second <= 86_300
    assert trip.arrival_second is not None
    assert trip.arrival_second <= 86_400


def test_dataset_default_callable_bounds_final_window_arrival() -> None:
    """Use the dataset resolver when bounding a final arrival to the horizon."""
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
                "latest_departure_second": 86_400,
            }
        ]
    )
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips,
        travel_time_function=_constant_travel_time(100),
    )

    scheduled = athenspop.scheduling.engine.schedule_once(dataset, seed=291)

    trip = scheduled.dataset.diaries[0].trips[0]
    assert trip.departure_second is not None
    assert trip.departure_second <= 86_300
    assert trip.arrival_second is not None
    assert trip.arrival_second <= 86_400


def test_schedule_once_applies_activity_duration_constraint() -> None:
    """Accept or reject the same diary according to its minimum activity gap."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        config=athenspop.scheduling.engine.SchedulingConfig(
            min_activity_duration_seconds=50
        ),
        seed=7,
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    second_departure = scheduled.dataset.diaries[0].trips[1].departure_second
    assert second_departure is not None
    assert 250 <= second_departure <= 300
    infeasible = athenspop.scheduling.engine.schedule_once(
        dataset,
        config=athenspop.scheduling.engine.SchedulingConfig(
            min_activity_duration_seconds=150
        ),
        seed=7,
    )
    assert infeasible.diagnostics.scheduled_diaries == 0
    assert infeasible.diagnostics.infeasible_diaries == (
        "household_id=h1; person_id=p1",
    )
    assert infeasible.diagnostics.issues[0].code == "infeasible_future_departure"


def test_schedule_once_refines_fixed_duration_future_windows() -> None:
    """Propagate fixed durations backward to preserve future activity gaps."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=2026,
        config=athenspop.scheduling.engine.SchedulingConfig(
            min_activity_duration_seconds=1800
        ),
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    second_trip = scheduled.dataset.diaries[0].trips[1]
    third_trip = scheduled.dataset.diaries[0].trips[2]
    assert second_trip.departure_second is not None
    assert second_trip.arrival_second is not None
    assert third_trip.departure_second is not None
    assert second_trip.departure_second <= 54_900
    assert third_trip.departure_second >= second_trip.arrival_second + 1800


def test_schedule_once_refines_windows_against_future_callable_trips() -> None:
    """Refine an earlier window using callable durations and a fixed successor."""
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

    def travel_time_function(
        origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        """Assign a fixed duration to both unresolved trips."""
        del origin, destination, mode, departure_second
        return 500

    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, travel_time_function=travel_time_function
    )
    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=2026,
        config=athenspop.scheduling.engine.SchedulingConfig(
            min_activity_duration_seconds=100
        ),
        travel_time_function=travel_time_function,
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    first_trip = scheduled.dataset.diaries[0].trips[0]
    second_trip = scheduled.dataset.diaries[0].trips[1]
    assert first_trip.departure_second is not None
    assert first_trip.departure_second <= 600
    assert first_trip.arrival_second == first_trip.departure_second + 500
    assert second_trip.departure_second == 1_200


def test_schedule_once_can_disable_callable_refinement() -> None:
    """Allow non-FIFO durations when predictive window refinement is disabled."""
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
                "latest_departure_second": 6,
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
                "departure_second": 10,
                "arrival_second": 11,
            },
        ],
        dtype=object,
    )

    def non_fifo_travel_time(
        origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        """Return a shorter duration for later departures."""
        del origin, destination, mode
        return 100 if departure_second < 5 else 1

    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, travel_time_function=non_fifo_travel_time
    )
    refined = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=0,
        config=athenspop.scheduling.engine.SchedulingConfig(
            min_activity_duration_seconds=0
        ),
        travel_time_function=non_fifo_travel_time,
    )
    unrefined = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=0,
        config=athenspop.scheduling.engine.SchedulingConfig(
            min_activity_duration_seconds=0,
            refine_callable_departure_windows=False,
        ),
        travel_time_function=non_fifo_travel_time,
    )
    assert refined.diagnostics.scheduled_diaries == 0
    assert unrefined.diagnostics.scheduled_diaries == 1
    assert unrefined.dataset.diaries[0].trips[0].departure_second == 6
    assert unrefined.dataset.diaries[0].trips[0].arrival_second == 7


def test_schedule_once_checks_travel_time_function_at_scheduler_boundary() -> None:
    """Prefer the call-level resolver and validate its result during scheduling."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, travel_time_function=_constant_travel_time(1)
    )
    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=1,
        travel_time_function=_constant_travel_time(75),
    )
    assert scheduled.dataset.diaries[0].trips[0].arrival_second == 175
    invalid = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=1,
        travel_time_function=_constant_travel_time(0),
    )
    assert invalid.diagnostics.scheduled_diaries == 0
    assert invalid.diagnostics.issues[0].code == "invalid_travel_time_function_result"


def test_generate_schedules_uses_shared_scheduler_with_repeatable_seed() -> None:
    """Observe seeded repeatability and variation across generated schedules."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    first = athenspop.generation.schedules.generate_schedules(dataset, 3, seed=99)
    second = athenspop.generation.schedules.generate_schedules(dataset, 3, seed=99)
    assert [run.dataset.diaries[0].trips[0].departure_second for run in first] == [
        run.dataset.diaries[0].trips[0].departure_second for run in second
    ]
    assert len({run.dataset.diaries[0].trips[0].departure_second for run in first}) > 1
    assert athenspop.generation.schedules.generate_schedules(dataset, 0, seed=99) == ()
    with pytest.raises(ValueError, match="non-negative"):
        athenspop.generation.schedules.generate_schedules(dataset, -1)


@pytest.mark.parametrize("n", [True, 1.5])
def test_generate_schedules_rejects_non_integer_counts(n: object) -> None:
    """Reject booleans and fractional realization counts."""
    with pytest.raises(TypeError, match="must be an integer"):
        athenspop.generation.schedules.generate_schedules(
            _trusted_dataset(_trusted_trip()), cast("int", n)
        )


def test_schedule_once_can_allow_final_arrival_after_observation_window() -> None:
    """Apply the final-arrival exception only when its policy is enabled."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    rejected = athenspop.scheduling.engine.schedule_once(dataset)
    assert rejected.diagnostics.scheduled_diaries == 0
    assert rejected.diagnostics.issues[0].code == "arrival_after_observation_window"
    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        config=athenspop.scheduling.engine.SchedulingConfig(
            allow_final_trip_after_observation_window=True
        ),
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    assert scheduled.dataset.diaries[0].trips[0].arrival_second == 87_000


def test_schedule_once_can_allow_nonfinal_trips_after_observation_window() -> None:
    """Permit an entire late chain only under the general horizon exception."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    rejected = athenspop.scheduling.engine.schedule_once(dataset)
    assert rejected.diagnostics.scheduled_diaries == 0
    assert rejected.diagnostics.issues[0].code == "infeasible_departure_window"
    scheduled = athenspop.scheduling.engine.schedule_once(
        dataset,
        seed=7,
        config=athenspop.scheduling.engine.SchedulingConfig(
            allow_trips_after_observation_window=True
        ),
    )
    assert scheduled.diagnostics.scheduled_diaries == 1
    assert scheduled.dataset.diaries[0].trips[1].departure_second is not None
    assert 90_000 <= scheduled.dataset.diaries[0].trips[1].departure_second <= 100_000
