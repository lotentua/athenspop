#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


from collections.abc import Sequence
from typing import Protocol

import numpy as np
import pydantic

from athenspop.long.scheduling.base import (
    FlexibleTripInfo,
    SchedulingError,
    TravelTimeFn,
)
from athenspop.long.scheduling.refinement import RefinedDepartureWindow


class DepartureWindowSampler(Protocol):
    def __call__(
        self,
        trip_info: Sequence[FlexibleTripInfo],
        windows: Sequence[RefinedDepartureWindow],
        travel_time_fn: TravelTimeFn,
        min_act_duration: pydantic.PositiveFloat,
        rng: np.random.Generator,
    ) -> list[pydantic.PositiveFloat]: ...


def sample_departures(
    trip_info: Sequence[FlexibleTripInfo],
    windows: Sequence[RefinedDepartureWindow],
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
    rng: np.random.Generator,
) -> list[pydantic.PositiveFloat]:
    scheduled_departures = []
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
            curr_scheduled_arrival = prev_scheduled_departure + travel_time

            curr_earliest_departure = max(
                curr_scheduled_arrival + min_act_duration, window.earliest_departure
            )
            if curr_earliest_departure > window.latest_departure:
                raise SchedulingError(
                    f"The scheduled departure of Trip {index} ({curr_earliest_departure}) is later than the end of the corresponding window ({window.latest_departure})."
                )

        # TODO: Check for duplicate departure times.
        curr_scheduled_departure = rng.uniform(
            curr_earliest_departure, window.latest_departure
        )
        scheduled_departures.append(curr_scheduled_departure)

    return scheduled_departures
