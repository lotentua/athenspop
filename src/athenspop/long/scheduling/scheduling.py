#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


from collections.abc import Sequence
from typing import NamedTuple, TypeAlias

import numpy as np
import pydantic

from athenspop.long.scheduling.base import (
    FlexibleTripInfo,
    SchedulingError,
    TravelTimeFn,
)
from athenspop.long.scheduling.refinement import DepartureWindowRefiner
from athenspop.long.scheduling.sampling import DepartureWindowSampler


class SchedulingSuccess(NamedTuple):
    scheduled_departures: list[float]


class SchedulingFailure(NamedTuple):
    error: SchedulingError


SchedulingResult: TypeAlias = SchedulingSuccess | SchedulingFailure


# TODO: Should we add a `schedule_or_raise` function?
# TODO: Add multiple schedule sampling.
# TODO: Add a convenience function for inspecting refined departure windows.
def schedule(
    trip_info: Sequence[FlexibleTripInfo],
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
    refiner: DepartureWindowRefiner,
    sampler: DepartureWindowSampler,
    rng: np.random.Generator,
) -> SchedulingResult:
    try:
        refined_windows = refiner(
            trip_info, travel_time_fn=travel_time_fn, min_act_duration=min_act_duration
        )
        scheduled_departures = sampler(
            trip_info,
            windows=refined_windows,
            travel_time_fn=travel_time_fn,
            min_act_duration=min_act_duration,
            rng=rng,
        )

        return SchedulingSuccess(scheduled_departures=scheduled_departures)
    except SchedulingError as e:
        return SchedulingFailure(e)
