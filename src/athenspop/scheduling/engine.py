# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Concrete trip scheduling for trusted survey diaries."""

import dataclasses
import random

import athenspop.model.survey
import athenspop.time_units
import athenspop.types


@dataclasses.dataclass(frozen=True, slots=True)
class SchedulingConfig:
    """Policy for one scheduling realization.

    Attributes:
        min_activity_duration_seconds:
            Minimum dwell time between an arrival and the next departure.
        observation_window_seconds:
            Diary observation horizon in integer seconds from the time origin.
        allow_trips_after_observation_window:
            Whether trips may depart or arrive after the observation window.
        allow_final_trip_after_observation_window:
            Whether only the final arrival may exceed the observation window.
        refine_callable_departure_windows:
            Whether bisection tightens callable travel-time windows against later
            trips. This requires deterministic FIFO arrivals over each searched
            window.
    """

    min_activity_duration_seconds: int = (
        athenspop.time_units.DEFAULT_MIN_ACTIVITY_DURATION_SECONDS
    )
    observation_window_seconds: int = (
        athenspop.time_units.DEFAULT_OBSERVATION_WINDOW_SECONDS
    )
    allow_trips_after_observation_window: bool = False
    allow_final_trip_after_observation_window: bool = False
    refine_callable_departure_windows: bool = True

    def __post_init__(self) -> None:
        """Validate scheduler policy values at the public construction boundary."""
        if isinstance(self.min_activity_duration_seconds, bool) or not isinstance(
            self.min_activity_duration_seconds, int
        ):
            raise TypeError(
                "`min_activity_duration_seconds` must be an integer number of seconds."
            )
        if self.min_activity_duration_seconds < 0:
            raise ValueError("`min_activity_duration_seconds` must be non-negative.")
        if isinstance(self.observation_window_seconds, bool) or not isinstance(
            self.observation_window_seconds, int
        ):
            raise TypeError(
                "`observation_window_seconds` must be an integer number of seconds."
            )
        if self.observation_window_seconds <= 0:
            raise ValueError("`observation_window_seconds` must be positive.")
        for field_name in (
            "allow_trips_after_observation_window",
            "allow_final_trip_after_observation_window",
            "refine_callable_departure_windows",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"`{field_name}` must be a boolean.")


@dataclasses.dataclass(frozen=True, slots=True)
class SchedulingIssue:
    """A scheduler diagnostic for one diary or trip.

    Attributes:
        code:
            Stable machine-readable issue code.
        message:
            Explanation of the infeasibility or invalid callable result.
        household_id:
            Household containing the affected diary.
        person_id:
            Person associated with the affected diary.
        trip_id:
            Affected trip, when the diagnostic is trip-specific.
    """

    code: str
    message: str
    household_id: str
    person_id: str
    trip_id: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class SchedulingDiagnostics:
    """Summary of one scheduling pass.

    Attributes:
        attempted_diaries:
            Number of diaries submitted to the scheduler.
        scheduled_diaries:
            Number of diaries returned with concrete schedules.
        infeasible_diaries:
            Identifiers for diaries that could not be scheduled.
        issues:
            Detailed diagnostics for infeasible diaries.
    """

    attempted_diaries: int
    scheduled_diaries: int
    infeasible_diaries: tuple[str, ...]
    issues: tuple[SchedulingIssue, ...] = ()

    @property
    def has_errors(self) -> bool:
        """Return whether any diary failed scheduling.

        Returns:
            `True` when at least one diary is infeasible.
        """
        return len(self.infeasible_diaries) > 0


@dataclasses.dataclass(frozen=True, slots=True)
class ScheduledSurveyDataset:
    """A scheduled survey paired with realization diagnostics.

    Attributes:
        dataset:
            Survey data containing only successfully scheduled diaries.
        diagnostics:
            Counts and issues from the scheduling pass.
    """

    dataset: athenspop.model.survey.SurveyDataset
    diagnostics: SchedulingDiagnostics


def schedule_once(
    dataset: athenspop.model.survey.SurveyDataset,
    *,
    seed: int | None = None,
    config: SchedulingConfig | None = None,
    travel_time_function: athenspop.types.TravelTimeFunction | None = None,
) -> ScheduledSurveyDataset:
    """Realize one concrete schedule from a validated survey dataset.

    Args:
        dataset:
            Trusted survey data produced by validation or model loading.
        seed:
            Optional seed for repeatable uniform departure draws.
        config:
            Scheduling policy; omit to use the default policy.
        travel_time_function:
            Optional callable returning positive integer travel
            seconds for trips whose duration is not already concrete.
            When callable departure-window refinement is enabled, this function must
            make departure second plus travel time monotone nondecreasing over each
            searched departure window.

    Returns:
        A dataset containing successful diaries and diagnostics for the full pass.

    Notes:
        The scheduler assumes its input model is already valid and complete except
        for the documented timing realizations.
    """
    resolved_config = SchedulingConfig() if config is None else config
    resolved_travel_time_function = (
        dataset.travel_time_function
        if travel_time_function is None
        else travel_time_function
    )
    rng = random.Random(seed)
    scheduled_diaries: list[athenspop.model.survey.Diary] = []
    infeasible_diaries: list[str] = []
    issues: list[SchedulingIssue] = []
    for diary in dataset.diaries:
        diary_id = _diary_id(diary)
        result = _schedule_diary(
            diary,
            rng=rng,
            config=resolved_config,
            travel_time_function=resolved_travel_time_function,
        )
        if isinstance(result, SchedulingIssue):
            infeasible_diaries.append(diary_id)
            issues.append(result)
        else:
            scheduled_diaries.append(result)
    diagnostics = SchedulingDiagnostics(
        attempted_diaries=len(dataset.diaries),
        scheduled_diaries=len(scheduled_diaries),
        infeasible_diaries=tuple(infeasible_diaries),
        issues=tuple(issues),
    )
    scheduled_person_keys = {
        (diary.household_id, diary.person_id) for diary in scheduled_diaries
    }
    scheduled_household_ids = {diary.household_id for diary in scheduled_diaries}
    scheduled_dataset = athenspop.model.survey.SurveyDataset(
        diaries=tuple(scheduled_diaries),
        households=tuple(
            household
            for household in dataset.households
            if household.household_id in scheduled_household_ids
        ),
        persons=tuple(
            person
            for person in dataset.persons
            if (person.household_id, person.person_id) in scheduled_person_keys
        ),
        travel_time_function=resolved_travel_time_function,
    )
    return ScheduledSurveyDataset(dataset=scheduled_dataset, diagnostics=diagnostics)


def _schedule_diary(
    diary: athenspop.model.survey.Diary,
    *,
    rng: random.Random,
    config: SchedulingConfig,
    travel_time_function: athenspop.types.TravelTimeFunction | None,
) -> athenspop.model.survey.Diary | SchedulingIssue:
    """Schedule one diary, stopping at the first infeasibility."""
    scheduled_trips: list[athenspop.model.survey.Trip] = []
    previous_arrival_second: int | None = None
    latest_departure_bounds = _latest_departure_bounds(
        diary.trips, config=config, travel_time_function=travel_time_function
    )
    if isinstance(latest_departure_bounds, SchedulingIssue):
        return latest_departure_bounds
    for index, trip in enumerate(diary.trips):
        earliest_allowed = (
            0
            if previous_arrival_second is None
            else previous_arrival_second + config.min_activity_duration_seconds
        )
        realized = _realize_trip(
            trip,
            earliest_allowed_second=earliest_allowed,
            latest_allowed_second=latest_departure_bounds[index],
            rng=rng,
            config=config,
            travel_time_function=travel_time_function,
        )
        if isinstance(realized, SchedulingIssue):
            return realized
        arrival_second = realized.arrival_second
        if arrival_second is None:
            raise RuntimeError(
                "The scheduler invariant was violated: a realized trip has no arrival "
                "second."
            )
        is_final_trip = index == len(diary.trips) - 1
        if (
            arrival_second > config.observation_window_seconds
            and not config.allow_trips_after_observation_window
            and not (config.allow_final_trip_after_observation_window and is_final_trip)
        ):
            return _issue(
                "arrival_after_observation_window",
                f"The trip arrives at {arrival_second}, after the observation "
                f"window end at {config.observation_window_seconds}.",
                realized,
            )
        scheduled_trips.append(realized)
        previous_arrival_second = arrival_second
    return dataclasses.replace(diary, trips=tuple(scheduled_trips))


def _realize_trip(
    trip: athenspop.model.survey.Trip,
    *,
    earliest_allowed_second: int,
    latest_allowed_second: int,
    rng: random.Random,
    config: SchedulingConfig,
    travel_time_function: athenspop.types.TravelTimeFunction | None,
) -> athenspop.model.survey.Trip | SchedulingIssue:
    """Realize one trip under previous-activity and future-trip bounds."""
    if trip.departure_second is not None:
        if (
            trip.departure_second > config.observation_window_seconds
            and not config.allow_trips_after_observation_window
        ):
            return _issue(
                "departure_after_observation_window",
                f"The trip departs at {trip.departure_second}, after the "
                f"observation window end at {config.observation_window_seconds}.",
                trip,
            )
        if trip.departure_second < earliest_allowed_second:
            return _issue(
                "activity_duration_too_short",
                f"The trip departs at {trip.departure_second}, before the earliest "
                f"feasible departure {earliest_allowed_second}.",
                trip,
            )
        if trip.departure_second > latest_allowed_second:
            return _issue(
                "infeasible_future_departure",
                f"The trip departs at {trip.departure_second}, after the latest "
                f"feasible departure {latest_allowed_second} implied by later trips.",
                trip,
            )
        return _with_arrival(
            trip,
            departure_second=trip.departure_second,
            travel_time_function=travel_time_function,
        )
    if trip.departure_window is None:
        return _issue(
            "missing_departure",
            "The trip has neither a concrete departure time nor a departure window.",
            trip,
        )
    earliest = max(trip.departure_window.earliest_second, earliest_allowed_second)
    latest = min(trip.departure_window.latest_second, latest_allowed_second)
    if not config.allow_trips_after_observation_window:
        latest = min(latest, config.observation_window_seconds)
    if earliest > latest:
        return _issue(
            "infeasible_departure_window",
            "The feasible departure window is empty after constraints: earliest "
            f"{earliest}, latest {latest}.",
            trip,
        )
    departure_second = rng.randint(earliest, latest)
    return _with_arrival(
        trip,
        departure_second=departure_second,
        travel_time_function=travel_time_function,
    )


def _with_arrival(
    trip: athenspop.model.survey.Trip,
    *,
    departure_second: int,
    travel_time_function: athenspop.types.TravelTimeFunction | None,
) -> athenspop.model.survey.Trip | SchedulingIssue:
    """Return a concrete trip using its arrival, duration, or a callable."""
    if trip.arrival_second is not None:
        travel_time_seconds = trip.arrival_second - departure_second
        if travel_time_seconds <= 0:
            return _issue(
                "non_positive_travel_duration",
                f"The trip arrives at {trip.arrival_second}, which is not after "
                f"departure {departure_second}.",
                trip,
            )
        return dataclasses.replace(
            trip,
            departure_second=departure_second,
            travel_time_seconds=travel_time_seconds,
            departure_window=None,
        )
    if trip.travel_time_seconds is not None:
        if trip.travel_time_seconds <= 0:
            return _issue(
                "non_positive_travel_duration",
                f"The trip travel time is {trip.travel_time_seconds}; movement trips "
                "require a positive duration.",
                trip,
            )
        return dataclasses.replace(
            trip,
            departure_second=departure_second,
            arrival_second=departure_second + trip.travel_time_seconds,
            departure_window=None,
        )
    if travel_time_function is None:
        return _issue(
            "missing_travel_time_function",
            "This trip requires a travel-time function but none was supplied to "
            "`schedule_once`.",
            trip,
        )
    travel_time_seconds = _call_travel_time_function(
        travel_time_function, trip, departure_second
    )
    if isinstance(travel_time_seconds, SchedulingIssue):
        return travel_time_seconds
    return dataclasses.replace(
        trip,
        departure_second=departure_second,
        arrival_second=departure_second + travel_time_seconds,
        travel_time_seconds=travel_time_seconds,
        departure_window=None,
    )


def _latest_departure_bounds(
    trips: tuple[athenspop.model.survey.Trip, ...],
    *,
    config: SchedulingConfig,
    travel_time_function: athenspop.types.TravelTimeFunction | None,
) -> tuple[int, ...] | SchedulingIssue:
    """Compute reverse bounds that preserve later-trip feasibility."""
    bounds = [config.observation_window_seconds] * len(trips)
    next_latest_departure: int | None = None
    for index in range(len(trips) - 1, -1, -1):
        trip = trips[index]
        own_latest_departure = _own_latest_departure(trip, config=config)
        latest_departure = own_latest_departure
        is_final_trip = index == len(trips) - 1
        target_arrival: int | None = None
        if next_latest_departure is not None:
            target_arrival = (
                next_latest_departure - config.min_activity_duration_seconds
            )
        must_arrive_within_window = (
            not config.allow_trips_after_observation_window
            and not (is_final_trip and config.allow_final_trip_after_observation_window)
        )
        if must_arrive_within_window and trip.departure_second is None:
            target_arrival = (
                config.observation_window_seconds
                if target_arrival is None
                else min(target_arrival, config.observation_window_seconds)
            )
        if target_arrival is not None:
            travel_time_seconds = _known_travel_time_seconds(
                trip, departure_second=own_latest_departure
            )
            if travel_time_seconds is not None:
                latest_departure = min(
                    latest_departure,
                    target_arrival - travel_time_seconds,
                )
            elif (
                config.refine_callable_departure_windows
                and travel_time_function is not None
            ):
                bounded_departure = _latest_callable_departure_for_target_arrival(
                    trip,
                    earliest_departure=_own_earliest_departure(trip),
                    latest_departure=latest_departure,
                    target_arrival=target_arrival,
                    travel_time_function=travel_time_function,
                )
                if isinstance(bounded_departure, SchedulingIssue):
                    return bounded_departure
                latest_departure = min(latest_departure, bounded_departure)
        bounds[index] = latest_departure
        next_latest_departure = latest_departure
    return tuple(bounds)


def _own_earliest_departure(trip: athenspop.model.survey.Trip) -> int:
    """Return the earliest departure allowed by a trip's timing data."""
    if trip.departure_second is not None:
        return trip.departure_second
    if trip.departure_window is not None:
        return trip.departure_window.earliest_second
    return 0


def _own_latest_departure(
    trip: athenspop.model.survey.Trip, *, config: SchedulingConfig
) -> int:
    """Return the latest departure allowed by timing and horizon policies."""
    if trip.departure_second is not None:
        return trip.departure_second
    if trip.departure_window is not None:
        if config.allow_trips_after_observation_window:
            return trip.departure_window.latest_second
        return min(
            trip.departure_window.latest_second,
            config.observation_window_seconds,
        )
    return config.observation_window_seconds


def _known_travel_time_seconds(
    trip: athenspop.model.survey.Trip, *, departure_second: int
) -> int | None:
    """Return a trip duration without calling a travel-time function."""
    if trip.travel_time_seconds is not None:
        return trip.travel_time_seconds
    if trip.departure_second is not None and trip.arrival_second is not None:
        return trip.arrival_second - trip.departure_second
    if trip.arrival_second is not None:
        return trip.arrival_second - departure_second
    return None


def _latest_callable_departure_for_target_arrival(
    trip: athenspop.model.survey.Trip,
    *,
    earliest_departure: int,
    latest_departure: int,
    target_arrival: int,
    travel_time_function: athenspop.types.TravelTimeFunction,
) -> int | SchedulingIssue:
    """Find the latest departure whose callable arrival respects a bound."""
    if earliest_departure > latest_departure:
        return latest_departure
    earliest_travel_time = _call_travel_time_function(
        travel_time_function, trip, earliest_departure
    )
    if isinstance(earliest_travel_time, SchedulingIssue):
        return earliest_travel_time
    if earliest_departure + earliest_travel_time > target_arrival:
        return earliest_departure - 1
    feasible_departure = earliest_departure
    infeasible_departure = latest_departure + 1
    while feasible_departure + 1 < infeasible_departure:
        candidate_departure = (feasible_departure + infeasible_departure) // 2
        candidate_travel_time = _call_travel_time_function(
            travel_time_function, trip, candidate_departure
        )
        if isinstance(candidate_travel_time, SchedulingIssue):
            return candidate_travel_time
        if candidate_departure + candidate_travel_time <= target_arrival:
            feasible_departure = candidate_departure
        else:
            infeasible_departure = candidate_departure
    return min(feasible_departure, latest_departure)


def _call_travel_time_function(
    travel_time_function: athenspop.types.TravelTimeFunction,
    trip: athenspop.model.survey.Trip,
    departure_second: int,
) -> int | SchedulingIssue:
    """Convert travel-time callback failures into scheduler diagnostics."""
    try:
        result = travel_time_function(
            trip.origin, trip.destination, trip.mode, departure_second
        )
    except Exception as error:
        return _issue(
            "travel_time_function_error",
            f"`travel_time_function` failed for departure {departure_second}: {error}.",
            trip,
        )
    if isinstance(result, bool) or not isinstance(result, int):
        return _issue(
            "invalid_travel_time_function_result",
            f"`travel_time_function` returned {result!r}; it must return a strictly "
            "positive integer number of seconds.",
            trip,
        )
    if result <= 0:
        return _issue(
            "invalid_travel_time_function_result",
            f"`travel_time_function` returned {result}; movement trips require a "
            "positive travel time.",
            trip,
        )
    return result


def _issue(
    code: str, message: str, trip: athenspop.model.survey.Trip
) -> SchedulingIssue:
    """Create a scheduler issue from a trip while preserving diary identity fields."""
    return SchedulingIssue(
        code=code,
        message=message,
        household_id=trip.household_id,
        person_id=trip.person_id,
        trip_id=trip.trip_id,
    )


def _diary_id(diary: athenspop.model.survey.Diary) -> str:
    """Return the diagnostic identifier used for one diary."""
    return f"household_id={diary.household_id}; person_id={diary.person_id}"
