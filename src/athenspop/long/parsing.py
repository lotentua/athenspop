#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


from dataclasses import dataclass

import numpy as np
import pandas as pd
import pydantic

from athenspop.long.scheduling.base import FlexibleTripInfo, TravelTimeFn
from athenspop.long.scheduling.refinement import DepartureWindowRefiner
from athenspop.long.scheduling.sampling import DepartureWindowSampler
from athenspop.long.scheduling.scheduling import (
    SchedulingFailure,
    SchedulingSuccess,
    schedule,
)


@dataclass(frozen=True)
class FlexibleTripColumnSpec:
    pid: str
    ozone: str
    dzone: str
    purp: str
    mode: str
    earliest_departure: str
    latest_departure: str


def parse_flexible(
    trips: pd.DataFrame,
    spec: FlexibleTripColumnSpec,
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
    refiner: DepartureWindowRefiner,
    sampler: DepartureWindowSampler,
    rng: np.random.Generator,
) -> tuple[dict[int, SchedulingSuccess], dict[int, SchedulingFailure]]:
    successes: dict[int, SchedulingSuccess] = {}
    failures: dict[int, SchedulingFailure] = {}

    for (
        # TODO: Validate the variable naming scheme.
        index,
        group,
    ) in trips.groupby(spec.pid):
        # TODO: Catch refinement, travel time calculation, and sampling errors.
        try:
            scheduling_result = _parse_flexible(
                trips=group,
                spec=spec,
                travel_time_fn=travel_time_fn,
                min_act_duration=min_act_duration,
                refiner=refiner,
                sampler=sampler,
                rng=rng,
            )
        except pydantic.ValidationError as e:
            print(e)
            failures[index] = scheduling_result

        if isinstance(scheduling_result, SchedulingSuccess):
            successes[index] = scheduling_result
        else:
            failures[index] = scheduling_result

    return successes, failures


def _parse_flexible(
    trips: pd.DataFrame,
    spec: FlexibleTripColumnSpec,
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
    refiner: DepartureWindowRefiner,
    sampler: DepartureWindowSampler,
    rng: np.random.Generator,
):
    # TODO: Validate the trip column specification.
    # TODO: Sort the trips by earliest departure.

    trip_info = [
        FlexibleTripInfo(
            ozone=getattr(record, spec.ozone),
            dzone=getattr(record, spec.dzone),
            purp=getattr(record, spec.purp),
            mode=getattr(record, spec.mode),
            earliest_departure=getattr(record, spec.earliest_departure),
            latest_departure=getattr(record, spec.latest_departure),
        )
        for record in trips.itertuples(index=False)
    ]

    scheduling_result = schedule(
        trip_info,
        travel_time_fn=travel_time_fn,
        min_act_duration=min_act_duration,
        refiner=refiner,
        sampler=sampler,
        rng=rng,
    )

    return scheduling_result
