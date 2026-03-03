#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


import math
from collections.abc import Sequence
from typing import NamedTuple, Protocol

import pydantic

from athenspop.long.scheduling.base import (
    FlexibleTripInfo,
    SchedulingError,
    TravelTimeFn,
)


class RefinedDepartureWindow(NamedTuple):
    """Trip departure time window after refinement."""

    earliest_departure: pydantic.NonNegativeFloat
    """The earliest feasible departure time."""
    latest_departure: pydantic.NonNegativeFloat
    """The latest feasible departure time."""


class DepartureWindowRefiner(Protocol):
    def __call__(
            self,
            trip_info: Sequence[FlexibleTripInfo],
            travel_time_fn: TravelTimeFn,
            min_act_duration: pydantic.PositiveFloat,
    ) -> list[RefinedDepartureWindow]: ...


def refine_departure_windows(
        trip_info: Sequence[FlexibleTripInfo],
        travel_time_fn: TravelTimeFn,
        min_act_duration: pydantic.PositiveFloat,
) -> list[RefinedDepartureWindow]:
    earliest_departures = _refine_earliest_departures(
        trip_info, travel_time_fn, min_act_duration
    )
    latest_departures = _refine_latest_departures(
        trip_info, travel_time_fn, min_act_duration, earliest_departures
    )

    return [
        RefinedDepartureWindow(
            earliest_departure=earliest_departure, latest_departure=latest_departure
        )
        for earliest_departure, latest_departure in zip(
            earliest_departures, latest_departures
        )
    ]


def _refine_earliest_departures(
        trip_info: Sequence[FlexibleTripInfo],
        travel_time_fn: TravelTimeFn,
        min_act_duration: pydantic.PositiveFloat,
) -> list[pydantic.PositiveFloat]:
    earliest_departures = []
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

            # Ensure that the earliest feasible departure is no earlier than the start of the corresponding window.
            # This can happen with sparse trip chains and relatively short travel times.
            curr_earliest_departure = max(
                curr_earliest_arrival + min_act_duration, info.earliest_departure
            )
            if curr_earliest_departure > info.latest_departure:
                raise SchedulingError(
                    f"The earliest feasible departure of Trip {index} ({curr_earliest_departure}) is later than the end of the corresponding window ({info.latest_departure})."
                )

        earliest_departures.append(curr_earliest_departure)

    return earliest_departures


def _refine_latest_departures(
        trip_info: Sequence[FlexibleTripInfo],
        travel_time_fn: TravelTimeFn,
        min_act_duration: pydantic.PositiveFloat,
        earliest_departures: list[pydantic.PositiveFloat],
) -> list[pydantic.PositiveFloat]:
    latest_departures = []
    for index, info in reversed(list(enumerate(trip_info))):
        curr_earliest_departure = earliest_departures[index]
        if index == len(trip_info) - 1:
            curr_latest_departure = info.latest_departure
        else:
            next_latest_departure = latest_departures[-1]
            curr_latest_arrival = next_latest_departure - min_act_duration

            curr_latest_departure = _calculate_latest_departure(
                trip_info=info,
                target_arrival=curr_latest_arrival,
                earliest_departure=curr_earliest_departure,
                travel_time_fn=travel_time_fn,
            )

            # TODO: Why this clamping necessary?
            curr_latest_departure = min(curr_latest_departure, info.latest_departure)
            if curr_latest_departure < curr_earliest_departure:
                raise SchedulingError(
                    f"The latest feasible departure time of Trip {index} is earlier than the start of the corresponding window ({info.earliest_departure})."
                )

        latest_departures.append(curr_latest_departure)

    return list(reversed(latest_departures))


def _calculate_latest_departure(
        trip_info: FlexibleTripInfo,
        target_arrival: pydantic.PositiveFloat,
        earliest_departure: pydantic.PositiveFloat,
        travel_time_fn: TravelTimeFn,
) -> pydantic.PositiveFloat:
    earliest_departure, latest_departure = (
        earliest_departure,
        trip_info.latest_departure,
    )
    for _ in range(100):
        if math.isclose(earliest_departure, latest_departure):
            break

        mid_departure = (earliest_departure + latest_departure) * 0.5

        travel_time = travel_time_fn(
            trip_info.ozone, trip_info.dzone, trip_info.mode, mid_departure
        )
        if mid_departure + travel_time <= target_arrival:
            earliest_departure = mid_departure
        else:
            latest_departure = mid_departure

    # This is the latest known departure.
    return earliest_departure
