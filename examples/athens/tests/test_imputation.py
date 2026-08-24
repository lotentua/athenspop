from random import Random
from types import MappingProxyType

from athenspop.model import Diary, HouseholdMetadata, SurveyDataset, Trip
from athenspop.scheduling import ScheduledSurveyDataset, SchedulingDiagnostics
from athenspop.schema import TimingPattern
from examples.athens.imputation import (
    IMPUTATION_METHOD,
    EmpiricalReturnHomeSampler,
    impute_athens_return_home_trips,
)
from examples.athens.reproduce import _scheduled_trips_frame


def test_athens_return_home_imputation_uses_empirical_return_departures() -> None:
    household = HouseholdMetadata(
        household_id="h1", values=MappingProxyType({"home_zone": "home"})
    )
    observed_return = Diary(
        household_id="h1",
        person_id="observed",
        household=household,
        trips=(
            _trip("observed_work", "observed", "home", "work", "work", 100, 150),
            _trip("observed_home", "observed", "work", "home", "home", 1000, 1050),
        ),
    )
    missing_return = Diary(
        household_id="h1",
        person_id="missing",
        household=household,
        trips=(
            _trip(
                "missing_work",
                "missing",
                "home",
                "work",
                "work",
                200,
                250,
                mode="taxi",
            ),
        ),
    )
    scheduled = ScheduledSurveyDataset(
        dataset=SurveyDataset(
            diaries=(missing_return, observed_return),
            households=(household,),
            persons=(),
        ),
        diagnostics=SchedulingDiagnostics(
            attempted_diaries=2, scheduled_diaries=2, infeasible_diaries=()
        ),
    )

    imputed = impute_athens_return_home_trips(
        scheduled,
        travel_time_function=_constant_travel_time,
        seed=2026,
        min_activity_duration_seconds=100,
    )

    assert imputed.diagnostics.scheduled_diaries == 2
    imputed_diary = imputed.diaries[0]
    assert len(imputed_diary.trips) == 2
    return_trip = imputed_diary.trips[-1]
    assert return_trip.trip_id == "missing_imputed_return_home_2"
    assert return_trip.origin == "work"
    assert return_trip.destination == "home"
    assert return_trip.purpose == "home"
    assert return_trip.mode == "taxi"
    assert return_trip.departure_second == 1100
    assert return_trip.arrival_second == 1150
    assert return_trip.metadata["is_imputed_return_home"] is True
    assert return_trip.metadata["imputation_method"] == IMPUTATION_METHOD
    assert return_trip.metadata["observed_last_trip_id"] == "missing_work"

    scheduled_trips = _scheduled_trips_frame(imputed.diaries)
    imputed_rows = scheduled_trips[scheduled_trips["is_imputed_return_home"]]
    assert imputed_rows["imputation_method"].tolist() == [IMPUTATION_METHOD]
    assert imputed_rows["observed_last_trip_id"].tolist() == ["missing_work"]


def test_empirical_return_sampler_is_seeded_truncated_and_purpose_specific() -> None:
    sampler = EmpiricalReturnHomeSampler(
        durations_by_purpose={"work": (500, 900, 1200), "market": (2000,)},
        min_activity_duration_seconds=100,
    )

    first = sampler.sample_departure_second(
        purpose="work", arrival_second=600, rng=Random(7)
    )
    repeated = sampler.sample_departure_second(
        purpose="work", arrival_second=600, rng=Random(7)
    )

    assert first == repeated
    assert first == 1100
    assert (
        sampler.sample_departure_second(
            purpose="work", arrival_second=1300, rng=Random(7)
        )
        == 1800
    )
    assert (
        sampler.sample_departure_second(
            purpose="education", arrival_second=600, rng=Random(7)
        )
        == 700
    )
    assert (
        sampler.sample_departure_second(
            purpose="market", arrival_second=600, rng=Random(7)
        )
        == 2600
    )


def test_return_imputation_exempts_allowed_endings_and_contains_callback_errors() -> (
    None
):
    household = HouseholdMetadata(
        household_id="h1", values=MappingProxyType({"home_zone": "home"})
    )
    diaries = (
        Diary(
            household_id="h1",
            person_id="at_home",
            household=household,
            trips=(_trip("home", "at_home", "work", "home", "home", 100, 150),),
        ),
        Diary(
            household_id="h1",
            person_id="recreation",
            household=household,
            trips=(
                _trip(
                    "recreation",
                    "recreation",
                    "home",
                    "park",
                    "recreation",
                    100,
                    150,
                ),
            ),
        ),
        Diary(
            household_id="h1",
            person_id="work",
            household=household,
            trips=(_trip("work", "work", "home", "work", "work", 100, 150),),
        ),
    )
    scheduled = ScheduledSurveyDataset(
        dataset=SurveyDataset(diaries=diaries, households=(household,), persons=()),
        diagnostics=SchedulingDiagnostics(
            attempted_diaries=3, scheduled_diaries=3, infeasible_diaries=()
        ),
    )

    def failing_travel_time(
        origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        raise RuntimeError("routing unavailable")

    result = impute_athens_return_home_trips(
        scheduled,
        travel_time_function=failing_travel_time,
        seed=2026,
        min_activity_duration_seconds=100,
    )

    assert tuple(diary.person_id for diary in result.diaries) == (
        "at_home",
        "recreation",
    )
    assert result.diagnostics.scheduled_diaries == 2
    assert result.diagnostics.infeasible_diaries == ("household_id=h1; person_id=work",)
    assert result.diagnostics.issues[0].code == "imputed_return_travel_time_error"


def _trip(
    trip_id: str,
    person_id: str,
    origin: str,
    destination: str,
    purpose: str,
    departure_second: int,
    arrival_second: int,
    *,
    mode: str = "car",
) -> Trip:
    return Trip(
        household_id="h1",
        person_id=person_id,
        trip_id=trip_id,
        origin=origin,
        destination=destination,
        purpose=purpose,
        mode=mode,
        departure_second=departure_second,
        arrival_second=arrival_second,
        travel_time_seconds=arrival_second - departure_second,
        departure_window=None,
        timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
        metadata=MappingProxyType({}),
    )


def _constant_travel_time(
    origin: str, destination: str, mode: str, departure_second: int
) -> int:
    return 50
