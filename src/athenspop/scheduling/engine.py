"""Scheduling engine for realizing concrete trips from trusted survey diaries."""

from dataclasses import dataclass, replace
from random import Random

from athenspop.model import (
    Diary,
    HouseholdMetadata,
    PersonMetadata,
    SurveyDataset,
    Trip,
)
from athenspop.time_units import (
    DEFAULT_MIN_ACTIVITY_DURATION_SECONDS,
    DEFAULT_OBSERVATION_WINDOW_SECONDS,
)
from athenspop.types import TravelTimeFunction


@dataclass(frozen=True, slots=True)
class SchedulingConfig:
    """Policy knobs for one scheduling realization.

    Attributes:
        min_activity_duration_seconds:
            Minimum dwell time required between an arrival and the next departure.
        observation_window_seconds:
            Diary observation horizon in integer seconds from the survey time origin.
        allow_trips_after_observation_window:
            Whether any trip may depart or arrive after the observation window.
        allow_final_trip_after_observation_window:
            Whether only the final trip may arrive after the observation window.
        refine_callable_departure_windows:
            Whether callable travel-time trips use bisection to tighten feasible departure windows against later fixed trips.
            Keep this enabled only when the travel-time callable is deterministic and FIFO over the searched window, meaning later departures cannot produce earlier arrivals.
    """

    min_activity_duration_seconds: int = DEFAULT_MIN_ACTIVITY_DURATION_SECONDS
    observation_window_seconds: int = DEFAULT_OBSERVATION_WINDOW_SECONDS
    allow_trips_after_observation_window: bool = False
    allow_final_trip_after_observation_window: bool = False
    refine_callable_departure_windows: bool = True

    def __post_init__(self) -> None:
        """Validate scheduler policy values at the public construction boundary."""
        if isinstance(
            self.min_activity_duration_seconds, bool
        ) or not isinstance(self.min_activity_duration_seconds, int):
            raise TypeError(
                "`min_activity_duration_seconds` must be an integer number of seconds."
            )
        if self.min_activity_duration_seconds < 0:
            raise ValueError(
                "`min_activity_duration_seconds` must be non-negative."
            )
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


@dataclass(frozen=True, slots=True)
class SchedulingIssue:
    """One scheduler diagnostic tied to a diary and optionally to a trip.

    Attributes:
        code:
            Stable machine-readable issue code.
        message:
            Human-readable explanation of the infeasibility or invalid callable result.
        household_id:
            Household identifier for the affected diary.
        person_id:
            Person identifier for the affected diary.
        trip_id:
            Optional trip identifier when the issue is trip-specific.
    """

    code: str
    message: str
    household_id: str
    person_id: str
    trip_id: str | None = None


@dataclass(frozen=True, slots=True)
class SchedulingDiagnostics:
    """Summary of one scheduling pass.

    Attributes:
        attempted_diaries:
            Number of diaries submitted to the scheduler.
        scheduled_diaries:
            Number of diaries returned with concrete schedules.
        infeasible_diaries:
            Diary identifiers that could not be scheduled.
        issues:
            Detailed scheduler diagnostics for infeasible diaries.
    """

    attempted_diaries: int
    scheduled_diaries: int
    infeasible_diaries: tuple[str, ...]
    issues: tuple[SchedulingIssue, ...] = ()

    @property
    def has_errors(self) -> bool:
        """Return whether any diary failed scheduling.

        Returns:
            `True` when at least one diary identifier appears in `infeasible_diaries`.
        """
        return len(self.infeasible_diaries) > 0


@dataclass(frozen=True, slots=True)
class ScheduledSurveyDataset:
    """Scheduled survey plus diagnostics from the realization pass.

    Attributes:
        dataset:
            Survey dataset containing only successfully scheduled diaries.
        diagnostics:
            Counts and issues describing the scheduling pass.
    """

    dataset: SurveyDataset
    diagnostics: SchedulingDiagnostics

    @property
    def diaries(self) -> tuple[Diary, ...]:
        """Return scheduled diaries for convenience.

        Returns:
            The scheduled diary tuple from `dataset`.
        """
        return self.dataset.diaries

    @property
    def households(self) -> tuple[HouseholdMetadata, ...]:
        """Return household metadata for scheduled diaries.

        Returns:
            The household metadata tuple from the scheduled dataset.
        """
        return self.dataset.households

    @property
    def persons(self) -> tuple[PersonMetadata, ...]:
        """Return person metadata for scheduled diaries.

        Returns:
            The person metadata tuple from the scheduled dataset.
        """
        return self.dataset.persons


def schedule_once(
    dataset: SurveyDataset,
    *,
    seed: int | None = None,
    config: SchedulingConfig | None = None,
    travel_time_function: TravelTimeFunction | None = None,
) -> ScheduledSurveyDataset:
    """Realize one concrete schedule from a validated survey dataset.

    Args:
        dataset:
            Trusted survey dataset produced by validation/model loading.
        seed:
            Optional seed for repeatable uniform draws within departure windows.
        config:
            Optional scheduling policy; defaults are used when omitted.
        travel_time_function:
            Optional callable returning positive integer travel seconds for trips whose duration is not already concrete.
            When callable departure-window refinement is enabled, this function must make departure second plus travel time monotone nondecreasing over each searched departure window.

    Returns:
        A scheduled dataset containing only feasible diaries plus diagnostics for attempted and infeasible diaries.

    Notes:
        The scheduler assumes its input model is already valid and complete except for the documented timing realizations.
    """
    resolved_config = SchedulingConfig() if config is None else config
    rng = Random(seed)
    scheduled_diaries: list[Diary] = []
    infeasible_diaries: list[str] = []
    issues: list[SchedulingIssue] = []
    for diary in dataset.diaries:
        diary_id = _diary_id(diary)
        result = _schedule_diary(
            diary,
            rng=rng,
            config=resolved_config,
            travel_time_function=travel_time_function,
        )
        if isinstance(result, _ScheduledDiary):
            scheduled_diaries.append(result.diary)
        else:
            infeasible_diaries.append(diary_id)
            issues.extend(result.issues)
    diagnostics = SchedulingDiagnostics(
        attempted_diaries=len(dataset.diaries),
        scheduled_diaries=len(scheduled_diaries),
        infeasible_diaries=tuple(infeasible_diaries),
        issues=tuple(issues),
    )
    scheduled_person_keys = {
        (diary.household_id, diary.person_id) for diary in scheduled_diaries
    }
    scheduled_household_ids = {
        diary.household_id for diary in scheduled_diaries
    }
    scheduled_dataset = SurveyDataset(
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
    )
    return ScheduledSurveyDataset(
        dataset=scheduled_dataset, diagnostics=diagnostics
    )


@dataclass(frozen=True, slots=True)
class _ScheduledDiary:
    """Internal success wrapper used to keep scheduler branch results explicit."""

    diary: Diary


@dataclass(frozen=True, slots=True)
class _InfeasibleDiary:
    """Internal failure wrapper containing all issues collected for one diary."""

    issues: tuple[SchedulingIssue, ...]


def _schedule_diary(
    diary: Diary,
    *,
    rng: Random,
    config: SchedulingConfig,
    travel_time_function: TravelTimeFunction | None,
) -> _ScheduledDiary | _InfeasibleDiary:
    """Schedule one diary and stop at the first infeasibility that makes downstream checks untrustworthy."""
    scheduled_trips: list[Trip] = []
    issues: list[SchedulingIssue] = []
    previous_arrival_second: int | None = None
    latest_departure_bounds = _latest_departure_bounds(
        diary.trips, config=config, travel_time_function=travel_time_function
    )
    if isinstance(latest_departure_bounds, SchedulingIssue):
        return _InfeasibleDiary(issues=(latest_departure_bounds,))
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
            issues.append(realized)
            return _InfeasibleDiary(issues=tuple(issues))
        arrival_second = realized.arrival_second
        if arrival_second is None:
            raise RuntimeError(
                "Scheduler invariant violated: a realized trip has no arrival second."
            )
        is_final_trip = index == len(diary.trips) - 1
        if (
            arrival_second > config.observation_window_seconds
            and not config.allow_trips_after_observation_window
            and not (
                config.allow_final_trip_after_observation_window
                and is_final_trip
            )
        ):
            issues.append(
                _issue(
                    "arrival_after_observation_window",
                    f"The trip arrives at {arrival_second}, after the observation window end at {config.observation_window_seconds}.",
                    realized,
                )
            )
            return _InfeasibleDiary(issues=tuple(issues))
        scheduled_trips.append(realized)
        previous_arrival_second = arrival_second
    return _ScheduledDiary(diary=replace(diary, trips=tuple(scheduled_trips)))


def _realize_trip(
    trip: Trip,
    *,
    earliest_allowed_second: int,
    latest_allowed_second: int,
    rng: Random,
    config: SchedulingConfig,
    travel_time_function: TravelTimeFunction | None,
) -> Trip | SchedulingIssue:
    """Realize one trip departure and arrival under previous-activity and future-trip bounds."""
    if trip.departure_second is not None:
        if trip.departure_second < earliest_allowed_second:
            return _issue(
                "activity_duration_too_short",
                f"The trip departs at {trip.departure_second}, before the earliest feasible departure {earliest_allowed_second}.",
                trip,
            )
        if trip.departure_second > latest_allowed_second:
            return _issue(
                "infeasible_future_departure",
                f"The trip departs at {trip.departure_second}, after the latest feasible departure {latest_allowed_second} implied by later trips.",
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
    earliest = max(
        trip.departure_window.earliest_second, earliest_allowed_second
    )
    latest = min(trip.departure_window.latest_second, latest_allowed_second)
    if not config.allow_trips_after_observation_window:
        latest = min(latest, config.observation_window_seconds)
    if earliest > latest:
        return _issue(
            "infeasible_departure_window",
            f"The feasible departure window is empty after constraints: earliest {earliest}, latest {latest}.",
            trip,
        )
    departure_second = rng.randint(earliest, latest)
    return _with_arrival(
        trip,
        departure_second=departure_second,
        travel_time_function=travel_time_function,
    )


def _with_arrival(
    trip: Trip,
    *,
    departure_second: int,
    travel_time_function: TravelTimeFunction | None,
) -> Trip | SchedulingIssue:
    """Return a concrete trip arrival using arrival, duration, or the supplied travel-time callable."""
    if trip.arrival_second is not None:
        travel_time_seconds = trip.arrival_second - departure_second
        if travel_time_seconds <= 0:
            return _issue(
                "non_positive_travel_duration",
                f"The trip arrives at {trip.arrival_second}, which is not after departure {departure_second}.",
                trip,
            )
        return replace(
            trip,
            departure_second=departure_second,
            travel_time_seconds=travel_time_seconds,
            departure_window=None,
        )
    if trip.travel_time_seconds is not None:
        if trip.travel_time_seconds <= 0:
            return _issue(
                "non_positive_travel_duration",
                f"The trip travel time is {trip.travel_time_seconds}; movement trips require a positive duration.",
                trip,
            )
        return replace(
            trip,
            departure_second=departure_second,
            arrival_second=departure_second + trip.travel_time_seconds,
            departure_window=None,
        )
    if travel_time_function is None:
        return _issue(
            "missing_travel_time_function",
            "This trip requires a travel-time function but none was supplied to `schedule_once`.",
            trip,
        )
    travel_time_seconds = _call_travel_time_function(
        travel_time_function, trip, departure_second
    )
    if isinstance(travel_time_seconds, SchedulingIssue):
        return travel_time_seconds
    return replace(
        trip,
        departure_second=departure_second,
        arrival_second=departure_second + travel_time_seconds,
        travel_time_seconds=travel_time_seconds,
        departure_window=None,
    )


def _latest_departure_bounds(
    trips: tuple[Trip, ...],
    *,
    config: SchedulingConfig,
    travel_time_function: TravelTimeFunction | None,
) -> tuple[int, ...] | SchedulingIssue:
    """Compute reverse latest-departure bounds so early random draws do not make later trips infeasible."""
    bounds = [config.observation_window_seconds] * len(trips)
    next_latest_departure: int | None = None
    for index in range(len(trips) - 1, -1, -1):
        trip = trips[index]
        own_latest_departure = _own_latest_departure(trip, config=config)
        latest_departure = own_latest_departure
        if next_latest_departure is not None:
            travel_time_seconds = _known_travel_time_seconds(
                trip, departure_second=own_latest_departure
            )
            if travel_time_seconds is not None:
                latest_departure = min(
                    latest_departure,
                    next_latest_departure
                    - travel_time_seconds
                    - config.min_activity_duration_seconds,
                )
            elif (
                config.refine_callable_departure_windows
                and travel_time_function is not None
            ):
                bounded_departure = (
                    _latest_callable_departure_for_target_arrival(
                        trip,
                        earliest_departure=_own_earliest_departure(trip),
                        latest_departure=latest_departure,
                        target_arrival=next_latest_departure
                        - config.min_activity_duration_seconds,
                        travel_time_function=travel_time_function,
                    )
                )
                if isinstance(bounded_departure, SchedulingIssue):
                    return bounded_departure
                latest_departure = min(latest_departure, bounded_departure)
        bounds[index] = latest_departure
        next_latest_departure = latest_departure
    return tuple(bounds)


def _own_earliest_departure(trip: Trip) -> int:
    """Return the earliest departure allowed by the trip's own concrete time or window."""
    if trip.departure_second is not None:
        return trip.departure_second
    if trip.departure_window is not None:
        return trip.departure_window.earliest_second
    return 0


def _own_latest_departure(trip: Trip, *, config: SchedulingConfig) -> int:
    """Return the latest departure allowed by the trip's own timing data and observation-window policy."""
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
    trip: Trip, *, departure_second: int
) -> int | None:
    """Return a trip duration when it can be derived without calling a stochastic travel-time function."""
    if trip.travel_time_seconds is not None:
        return trip.travel_time_seconds
    if trip.departure_second is not None and trip.arrival_second is not None:
        return trip.arrival_second - trip.departure_second
    if trip.arrival_second is not None:
        return trip.arrival_second - departure_second
    return None


def _latest_callable_departure_for_target_arrival(
    trip: Trip,
    *,
    earliest_departure: int,
    latest_departure: int,
    target_arrival: int,
    travel_time_function: TravelTimeFunction,
) -> int | SchedulingIssue:
    """Find the latest callable-trip departure whose arrival respects a target arrival bound."""
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
    travel_time_function: TravelTimeFunction, trip: Trip, departure_second: int
) -> int | SchedulingIssue:
    """Call a user travel-time function and convert expected callable failures into scheduler diagnostics."""
    try:
        result = travel_time_function(
            trip.origin, trip.destination, trip.mode, departure_second
        )
    except (ArithmeticError, LookupError, ValueError) as error:
        return _issue(
            "travel_time_function_error",
            f"`travel_time_function` failed for departure {departure_second}: {error}.",
            trip,
        )
    if isinstance(result, bool) or not isinstance(result, int):
        return _issue(
            "invalid_travel_time_function_result",
            f"`travel_time_function` returned {result!r}; it must return a strictly positive integer number of seconds.",
            trip,
        )
    if result <= 0:
        return _issue(
            "invalid_travel_time_function_result",
            f"`travel_time_function` returned {result}; movement trips require a positive travel time.",
            trip,
        )
    return result


def _issue(code: str, message: str, trip: Trip) -> SchedulingIssue:
    """Create a scheduler issue from a trip while preserving diary identity fields."""
    return SchedulingIssue(
        code=code,
        message=message,
        household_id=trip.household_id,
        person_id=trip.person_id,
        trip_id=trip.trip_id,
    )


def _diary_id(diary: Diary) -> str:
    """Return the diagnostic identifier used for one diary."""
    return f"household_id={diary.household_id}; person_id={diary.person_id}"
