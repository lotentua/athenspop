#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Parse long-format DataFrames into scheduled trip chains.

Reads a DataFrame where each row is a single trip, groups rows by
person identifier, constructs validated ``FlexibleTripChain``
objects, and schedules concrete departure times for each chain.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pydantic

from athenspop.long.model.chain import FlexibleTripChain
from athenspop.long.scheduling.base import (
    FlexibleTrip,
    SchedulingError,
    TravelTimeFn,
)
from athenspop.long.scheduling.refinement import DepartureWindowRefiner
from athenspop.long.scheduling.sampling import DepartureWindowSampler
from athenspop.long.scheduling.scheduling import (
    SchedulingFailure,
    SchedulingResult,
    SchedulingSuccess,
    schedule,
)


@dataclass(frozen=True)
class FlexibleTripColumnSpec:
    """Maps DataFrame column names to ``FlexibleTrip`` fields.

    Attributes:
        pid: Column containing the person identifier.
        ozone: Column containing the origin zone.
        dzone: Column containing the destination zone.
        purp: Column containing the trip purpose.
        mode: Column containing the transport mode.
        earliest_departure: Column containing the earliest
            departure time.
        latest_departure: Column containing the latest
            departure time.
    """

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
    """Parse and schedule all trip chains in a DataFrame.

    Groups ``trips`` by person identifier, constructs a validated
    ``FlexibleTripChain`` for each group, and schedules concrete
    departure times.  Validation or scheduling failures are
    collected separately so that one person's failure does not
    prevent others from being processed.

    Args:
        trips: Long-format DataFrame with one row per trip.
        spec: Column-name mapping for the DataFrame.
        travel_time_fn: User-provided travel-time function.
        min_act_duration: Minimum activity duration between
            consecutive trips, in hours.
        refiner: Strategy for tightening departure windows.
        sampler: Strategy for drawing concrete departure times.
        rng: NumPy random generator for reproducibility.

    Returns:
        A ``(successes, failures)`` tuple where each dict is
        keyed by person identifier.
    """
    successes: dict[int, SchedulingSuccess] = {}
    failures: dict[int, SchedulingFailure] = {}

    for index, group in trips.groupby(spec.pid):
        try:
            scheduling_result = _parse_flexible(
                pid=index,
                trips=group,
                spec=spec,
                travel_time_fn=travel_time_fn,
                min_act_duration=min_act_duration,
                refiner=refiner,
                sampler=sampler,
                rng=rng,
            )
        except pydantic.ValidationError as e:
            failures[index] = SchedulingFailure(
                error=SchedulingError(str(e))
            )
            continue

        if isinstance(scheduling_result, SchedulingSuccess):
            successes[index] = scheduling_result
        else:
            failures[index] = scheduling_result

    return successes, failures


def _parse_flexible(
    pid: int,
    trips: pd.DataFrame,
    spec: FlexibleTripColumnSpec,
    travel_time_fn: TravelTimeFn,
    min_act_duration: pydantic.PositiveFloat,
    refiner: DepartureWindowRefiner,
    sampler: DepartureWindowSampler,
    rng: np.random.Generator,
) -> SchedulingResult:
    """Build a trip chain from one person's rows and schedule it."""
    chain = FlexibleTripChain(
        pid=pid,
        trips=tuple(
            FlexibleTrip(
                ozone=getattr(record, spec.ozone),
                dzone=getattr(record, spec.dzone),
                purp=getattr(record, spec.purp),
                mode=getattr(record, spec.mode),
                earliest_departure=getattr(
                    record, spec.earliest_departure
                ),
                latest_departure=getattr(
                    record, spec.latest_departure
                ),
            )
            for record in trips.itertuples(index=False)
        ),
    )

    return schedule(
        chain.trips,
        travel_time_fn=travel_time_fn,
        min_act_duration=min_act_duration,
        refiner=refiner,
        sampler=sampler,
        rng=rng,
    )
