"""Athens-specific return-home imputation for the CSuM2026 example workflow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from random import Random
from types import MappingProxyType

from athenspop.model import Diary, SurveyDataset, Trip
from athenspop.scheduling import (
    ScheduledSurveyDataset,
    SchedulingDiagnostics,
    SchedulingIssue,
)
from athenspop.schema import TimingPattern
from athenspop.types import TravelTimeFunction

IMPUTATION_METHOD = "empirical_activity_duration_inverse_transform"


@dataclass(frozen=True, slots=True)
class EmpiricalReturnHomeSampler:
    """Sample return departures from empirical destination-activity durations."""

    durations_by_purpose: Mapping[str, tuple[int, ...]]
    min_activity_duration_seconds: int

    def __post_init__(self) -> None:
        """Reject a non-positive activity-duration contract."""
        if self.min_activity_duration_seconds <= 0:
            raise ValueError("Minimum activity duration must be positive.")

    @classmethod
    def from_diaries(
        cls, diaries: tuple[Diary, ...], *, min_activity_duration_seconds: int
    ) -> EmpiricalReturnHomeSampler:
        """Fit activity-duration distributions by destination purpose."""
        samples: dict[str, list[int]] = {}
        for diary in diaries:
            home_location = _home_location(diary)
            for previous_trip, current_trip in zip(
                diary.trips, diary.trips[1:], strict=False
            ):
                if (
                    current_trip.destination == home_location
                    and current_trip.purpose == "home"
                    and current_trip.departure_second is not None
                    and previous_trip.arrival_second is not None
                ):
                    duration = (
                        current_trip.departure_second - previous_trip.arrival_second
                    )
                    if duration >= min_activity_duration_seconds:
                        samples.setdefault(previous_trip.purpose, []).append(duration)
        return cls(
            durations_by_purpose={
                purpose: tuple(sorted(values)) for purpose, values in samples.items()
            },
            min_activity_duration_seconds=min_activity_duration_seconds,
        )

    def sample_departure_second(
        self, *, purpose: str, arrival_second: int, rng: Random
    ) -> int:
        """Sample an empirical duration and add it to the scheduled arrival."""
        samples = self.durations_by_purpose.get(purpose)
        if not samples:
            return arrival_second + self.min_activity_duration_seconds
        probability = rng.random()
        duration = samples[min(int(probability * len(samples)), len(samples) - 1)]
        return arrival_second + max(duration, self.min_activity_duration_seconds)


def impute_athens_return_home_trips(
    scheduled: ScheduledSurveyDataset,
    *,
    travel_time_function: TravelTimeFunction,
    seed: int,
    min_activity_duration_seconds: int,
) -> ScheduledSurveyDataset:
    "Impute missing paper return-home trips after reported trips have been scheduled."
    sampler = EmpiricalReturnHomeSampler.from_diaries(
        scheduled.diaries,
        min_activity_duration_seconds=min_activity_duration_seconds,
    )
    rng = Random(seed)
    diaries: list[Diary] = []
    issues: list[SchedulingIssue] = list(scheduled.diagnostics.issues)
    infeasible_diaries = list(scheduled.diagnostics.infeasible_diaries)
    for diary in scheduled.diaries:
        result = _maybe_impute_diary(
            diary,
            sampler=sampler,
            rng=rng,
            travel_time_function=travel_time_function,
        )
        if isinstance(result, SchedulingIssue):
            issues.append(result)
            infeasible_diaries.append(_diary_id(diary))
            continue
        diaries.append(result)
    diagnostics = SchedulingDiagnostics(
        attempted_diaries=scheduled.diagnostics.attempted_diaries,
        scheduled_diaries=len(diaries),
        infeasible_diaries=tuple(infeasible_diaries),
        issues=tuple(issues),
    )
    dataset = SurveyDataset(
        diaries=tuple(diaries),
        households=scheduled.households,
        persons=scheduled.persons,
    )
    return ScheduledSurveyDataset(dataset=dataset, diagnostics=diagnostics)


def _maybe_impute_diary(
    diary: Diary,
    *,
    sampler: EmpiricalReturnHomeSampler,
    rng: Random,
    travel_time_function: TravelTimeFunction,
) -> Diary | SchedulingIssue:
    last_trip = diary.trips[-1]
    if last_trip.purpose in {"home", "recreation"}:
        return diary
    home_location = _home_location(diary)
    if last_trip.destination == home_location:
        return diary
    if last_trip.arrival_second is None:
        return _issue(
            "missing_previous_arrival",
            "Athens return-home imputation requires a scheduled final reported trip.",
            last_trip,
        )
    departure_second = sampler.sample_departure_second(
        purpose=last_trip.purpose,
        arrival_second=last_trip.arrival_second,
        rng=rng,
    )
    try:
        travel_time_seconds = travel_time_function(
            last_trip.destination,
            home_location,
            last_trip.mode,
            departure_second,
        )
    except Exception as error:
        return _issue(
            "imputed_return_travel_time_error",
            "Could not resolve imputed return-home travel time for departure "
            f"{departure_second}: {error}.",
            last_trip,
        )
    if isinstance(travel_time_seconds, bool) or not isinstance(
        travel_time_seconds, int
    ):
        return _issue(
            "invalid_imputed_return_travel_time",
            "Imputed return-home travel-time function returned "
            f"{travel_time_seconds!r}; it must return a positive integer.",
            last_trip,
        )
    if travel_time_seconds <= 0:
        return _issue(
            "invalid_imputed_return_travel_time",
            "Imputed return-home travel-time function returned "
            f"{travel_time_seconds}; it must be positive.",
            last_trip,
        )
    imputed = Trip(
        household_id=last_trip.household_id,
        person_id=last_trip.person_id,
        trip_id=_imputed_trip_id(diary),
        origin=last_trip.destination,
        destination=home_location,
        purpose="home",
        mode=last_trip.mode,
        departure_second=departure_second,
        arrival_second=departure_second + travel_time_seconds,
        travel_time_seconds=travel_time_seconds,
        departure_window=None,
        timing_pattern=TimingPattern.DEPARTURE_DURATION,
        metadata=MappingProxyType(
            {
                "is_imputed_return_home": True,
                "imputation_method": IMPUTATION_METHOD,
                "observed_last_trip_id": last_trip.trip_id,
            }
        ),
    )
    return replace(diary, trips=(*diary.trips, imputed))


def _home_location(diary: Diary) -> str:
    if diary.household is not None and "home_zone" in diary.household.values:
        return str(diary.household.values["home_zone"])
    return diary.trips[0].origin


def _imputed_trip_id(diary: Diary) -> str:
    existing_ids = {trip.trip_id for trip in diary.trips}
    suffix = len(diary.trips) + 1
    while f"{diary.person_id}_imputed_return_home_{suffix}" in existing_ids:
        suffix += 1
    return f"{diary.person_id}_imputed_return_home_{suffix}"


def _issue(code: str, message: str, trip: Trip) -> SchedulingIssue:
    return SchedulingIssue(
        code=code,
        message=message,
        household_id=trip.household_id,
        person_id=trip.person_id,
        trip_id=trip.trip_id,
    )


def _diary_id(diary: Diary) -> str:
    return f"household_id={diary.household_id}; person_id={diary.person_id}"
