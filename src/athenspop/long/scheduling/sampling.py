#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Departure time sampling from refined windows.

Draws a concrete departure time for each trip by sampling
uniformly within the refined window, while ensuring that
travel time plus the minimum activity duration constraint is
respected between consecutive trips.
"""

from collections.abc import Sequence
from typing import Protocol

import numpy as np
import pydantic

from athenspop.long.scheduling.base import (
    FlexibleTrip,
    SchedulingError,
    TravelTimeFn,
)
from athenspop.long.scheduling.refinement import RefinedDepartureWindow


class DepartureWindowSampler(Protocol):
    """Protocol for departure-time sampling strategies."""

    def __call__(
        self,
        trip_info: Sequence[FlexibleTrip],
        windows: Sequence[RefinedDepartureWindow],
        travel_time_fn: TravelTimeFn,
        min_act_duration: pydantic.PositiveFloat,
        rng: np.random.Generator,
    ) -> list[pydantic.PositiveFloat]: ...


def sample_departures(
    trip_info: Sequence[FlexibleTrip],
    windows: Sequence[RefinedDepartureWindow],
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
    rng: np.random.Generator,
) -> list[pydantic.PositiveFloat]:
    """Sample a concrete departure time for each trip.

    Iterates forward through the refined windows, drawing a uniform
    random departure and propagating the stochastic travel time to
    constrain the next trip's earliest feasible departure.

    Args:
        trip_info: Ordered sequence of flexible trips.
        windows: Refined departure windows (one per trip).
        travel_time_fn: Function returning travel time in hours.
        min_act_duration: Minimum activity duration between
            consecutive trips, in hours.
        rng: NumPy random generator for reproducibility.

    Returns:
        Sampled departure time for each trip, in trip order.

    Raises:
        SchedulingError: If the stochastic travel time causes a
            trip's earliest feasible departure to exceed its
            refined latest departure.
    """
    scheduled_departures: list[pydantic.PositiveFloat] = []
    for index, window in enumerate(windows):
        if index == 0:
            curr_earliest_departure = window.earliest_departure
        else:
            prev_info = trip_info[index - 1]
            prev_scheduled_departure = scheduled_departures[index - 1]

            travel_time = travel_time_fn(
                prev_info.ozone,
                prev_info.dzone,
                prev_info.mode,
                prev_scheduled_departure,
            )
            curr_scheduled_arrival = (
                prev_scheduled_departure + travel_time
            )

            curr_earliest_departure = max(
                curr_scheduled_arrival + min_act_duration,
                window.earliest_departure,
            )
            if curr_earliest_departure > window.latest_departure:
                raise SchedulingError(
                    f"The scheduled departure of "
                    f"Trip {index} "
                    f"({curr_earliest_departure}) is later "
                    f"than the end of the corresponding "
                    f"window ({window.latest_departure})."
                )

        # TODO: Check for duplicate departure times.
        curr_scheduled_departure = rng.uniform(
            curr_earliest_departure, window.latest_departure
        )
        scheduled_departures.append(curr_scheduled_departure)

    return scheduled_departures
