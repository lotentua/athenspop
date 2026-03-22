#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Top-level scheduling entry point.

Orchestrates departure-window refinement and sampling, returning
either a successful schedule or a structured failure.
"""

from collections.abc import Sequence
from typing import Final, NamedTuple, TypeAlias

import numpy as np
import pydantic

from athenspop.long.scheduling.base import (
    FlexibleTrip,
    SchedulingError,
    TravelTimeFn,
)
from athenspop.long.scheduling.refinement import DepartureWindowRefiner
from athenspop.long.scheduling.sampling import DepartureWindowSampler

_TRAVEL_TIME_FN_ERROR: Final[str] = (
    "travel_time_fn({ozone}, {dzone}, {mode!r}, {time}) "
    "returned {result}, expected a positive value."
)


class SchedulingSuccess(NamedTuple):
    """Result of a successful scheduling run.

    Attributes:
        scheduled_departures: Concrete departure time for each trip.
    """

    scheduled_departures: list[float]


class SchedulingFailure(NamedTuple):
    """Result of a failed scheduling run.

    Attributes:
        error: The scheduling error that caused the failure.
    """

    error: SchedulingError


SchedulingResult: TypeAlias = SchedulingSuccess | SchedulingFailure
"""Union of possible scheduling outcomes."""


def _validated_travel_time_fn(fn: TravelTimeFn) -> TravelTimeFn:
    """Wrap a travel-time function to enforce positive return values."""

    def wrapper(
        ozone: int,
        dzone: int,
        mode: str,
        time: pydantic.PositiveFloat,
    ) -> pydantic.PositiveFloat:
        result = fn(ozone, dzone, mode, time)
        if result <= 0:
            raise SchedulingError(
                _TRAVEL_TIME_FN_ERROR.format(
                    ozone=ozone,
                    dzone=dzone,
                    mode=mode,
                    time=time,
                    result=result,
                )
            )
        return result

    return wrapper


# TODO: Should we add a `schedule_or_raise` function?
# TODO: Add multiple schedule sampling.
# TODO: Add a convenience function for inspecting refined departure
#       windows.
def schedule(
    trip_info: Sequence[FlexibleTrip],
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
    refiner: DepartureWindowRefiner,
    sampler: DepartureWindowSampler,
    rng: np.random.Generator,
) -> SchedulingResult:
    """Schedule concrete departure times for a trip chain.

    Wraps ``travel_time_fn`` in a validating decorator, refines
    the departure windows, and samples concrete departure times.
    Returns a ``SchedulingSuccess`` on success or a
    ``SchedulingFailure`` if constraints are infeasible.

    Args:
        trip_info: Ordered sequence of flexible trips.
        travel_time_fn: User-provided travel-time function.
        min_act_duration: Minimum activity duration between
            consecutive trips, in hours.
        refiner: Strategy for tightening departure windows.
        sampler: Strategy for drawing concrete departure times.
        rng: NumPy random generator for reproducibility.

    Returns:
        A ``SchedulingSuccess`` containing the scheduled departure
        times, or a ``SchedulingFailure`` wrapping the error.
    """
    # TODO: Wrap the travel time function before passing it to the
    #       scheduler.
    travel_time_fn = _validated_travel_time_fn(travel_time_fn)
    try:
        refined_windows = refiner(
            trip_info,
            travel_time_fn=travel_time_fn,
            min_act_duration=min_act_duration,
        )
        scheduled_departures = sampler(
            trip_info,
            windows=refined_windows,
            travel_time_fn=travel_time_fn,
            min_act_duration=min_act_duration,
            rng=rng,
        )

        return SchedulingSuccess(
            scheduled_departures=scheduled_departures
        )
    except SchedulingError as e:
        return SchedulingFailure(e)
