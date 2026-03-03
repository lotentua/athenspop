#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


from typing import NamedTuple, Protocol

import pydantic


class FlexibleTripInfo(NamedTuple):
    ozone: int
    dzone: int
    purp: str
    mode: str
    # TODO: Somehow combine this information with RefinedDepartureWindow without mixing states.
    earliest_departure: pydantic.PositiveFloat
    latest_departure: pydantic.PositiveFloat


class TravelTimeFn(Protocol):
    def __call__(
            self, ozone: int, dzone: int, mode: str, time: pydantic.PositiveFloat
    ) -> pydantic.PositiveFloat: ...


class SchedulingError(Exception):
    """Raised when scheduling fails due to infeasible constraints."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
