#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Departure window refinement.

Tightens user-supplied departure windows so that every trip can
depart, travel, and leave enough time for the minimum activity
duration before the next trip departs.  Refinement proceeds in
two passes:

1. **Forward pass** — propagates arrival-time constraints from the
   first trip to the last, raising the earliest feasible departure
   where necessary.
2. **Backward pass** — propagates latest-departure constraints from
   the last trip to the first using bisection search over the
   travel-time function.
"""

import math
from collections.abc import Sequence
from typing import NamedTuple, Protocol

import pydantic

from athenspop.long.scheduling.base import (
    FlexibleTrip,
    SchedulingError,
    TravelTimeFn,
)


class RefinedDepartureWindow(NamedTuple):
    """Feasible departure window produced by refinement.

    Attributes:
        earliest_departure: Earliest feasible departure time.
        latest_departure: Latest feasible departure time.
    """

    earliest_departure: pydantic.NonNegativeFloat
    latest_departure: pydantic.NonNegativeFloat


class DepartureWindowRefiner(Protocol):
    """Protocol for departure-window refinement strategies."""

    def __call__(
        self,
        trip_info: Sequence[FlexibleTrip],
        travel_time_fn: TravelTimeFn,
        min_act_duration: pydantic.PositiveFloat,
    ) -> list[RefinedDepartureWindow]: ...


def refine_departure_windows(
    trip_info: Sequence[FlexibleTrip],
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
) -> list[RefinedDepartureWindow]:
    """Refine departure windows for a sequence of trips.

    Runs a forward pass to tighten earliest departures and a
    backward pass to tighten latest departures, ensuring that every
    pair of consecutive trips satisfies the minimum activity
    duration constraint.

    Args:
        trip_info: Ordered sequence of flexible trips.
        travel_time_fn: Function returning travel time in hours.
        min_act_duration: Minimum activity duration between
            consecutive trips, in hours.

    Returns:
        One refined window per trip, in the same order as
        ``trip_info``.

    Raises:
        SchedulingError: If no feasible departure window exists for
            any trip.
    """
    earliest_departures = _refine_earliest_departures(
        trip_info, travel_time_fn, min_act_duration
    )
    latest_departures = _refine_latest_departures(
        trip_info, travel_time_fn, min_act_duration, earliest_departures
    )

    return [
        RefinedDepartureWindow(
            earliest_departure=earliest_departure,
            latest_departure=latest_departure,
        )
        for earliest_departure, latest_departure in zip(
            earliest_departures, latest_departures
        )
    ]


def _refine_earliest_departures(
    trip_info: Sequence[FlexibleTrip],
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
) -> list[pydantic.PositiveFloat]:
    """Forward pass: propagate arrival constraints to tighten earliest departures."""
    earliest_departures: list[pydantic.PositiveFloat] = []
    for index, info in enumerate(trip_info):
        if index == 0:
            curr_earliest_departure = info.earliest_departure
        else:
            prev_info = trip_info[index - 1]
            prev_earliest_departure = earliest_departures[index - 1]

            travel_time = travel_time_fn(
                prev_info.ozone,
                prev_info.dzone,
                prev_info.mode,
                prev_earliest_departure,
            )
            curr_earliest_arrival = prev_earliest_departure + travel_time

            # Clamp to the window start; sparse chains with short
            # travel times can produce arrivals before the window.
            curr_earliest_departure = max(
                curr_earliest_arrival + min_act_duration,
                info.earliest_departure,
            )
            if curr_earliest_departure > info.latest_departure:
                raise SchedulingError(
                    f"The earliest feasible departure of "
                    f"Trip {index} "
                    f"({curr_earliest_departure}) is later "
                    f"than the end of the corresponding "
                    f"window ({info.latest_departure})."
                )

        earliest_departures.append(curr_earliest_departure)

    return earliest_departures


def _refine_latest_departures(
    trip_info: Sequence[FlexibleTrip],
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
    earliest_departures: list[pydantic.PositiveFloat],
) -> list[pydantic.PositiveFloat]:
    """Backward pass: propagate latest-departure constraints via bisection."""
    latest_departures: list[pydantic.PositiveFloat] = []
    for index, info in reversed(list(enumerate(trip_info))):
        curr_earliest_departure = earliest_departures[index]
        if index == len(trip_info) - 1:
            curr_latest_departure = info.latest_departure
        else:
            next_latest_departure = latest_departures[-1]
            curr_latest_arrival = (
                next_latest_departure - min_act_duration
            )

            curr_latest_departure = _calculate_latest_departure(
                trip_info=info,
                target_arrival=curr_latest_arrival,
                earliest_departure=curr_earliest_departure,
                travel_time_fn=travel_time_fn,
            )

            # TODO: Why is this clamping necessary?
            curr_latest_departure = min(
                curr_latest_departure, info.latest_departure
            )
            if curr_latest_departure < curr_earliest_departure:
                raise SchedulingError(
                    f"The latest feasible departure time "
                    f"of Trip {index} is earlier than the "
                    f"start of the corresponding window "
                    f"({info.earliest_departure})."
                )

        latest_departures.append(curr_latest_departure)

    return list(reversed(latest_departures))


def _calculate_latest_departure(
    trip_info: FlexibleTrip,
    target_arrival: pydantic.PositiveFloat,
    earliest_departure: pydantic.PositiveFloat,
    travel_time_fn: TravelTimeFn,
) -> pydantic.PositiveFloat:
    """Bisect the departure window to find the latest departure arriving by ``target_arrival``."""
    earliest_departure, latest_departure = (
        earliest_departure,
        trip_info.latest_departure,
    )
    for _ in range(100):
        if math.isclose(earliest_departure, latest_departure):
            break

        mid_departure = (earliest_departure + latest_departure) * 0.5

        travel_time = travel_time_fn(
            trip_info.ozone,
            trip_info.dzone,
            trip_info.mode,
            mid_departure,
        )
        if mid_departure + travel_time <= target_arrival:
            earliest_departure = mid_departure
        else:
            latest_departure = mid_departure

    return earliest_departure
