#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Core types for the scheduling subsystem.

Defines the input trip model, the travel-time function protocol,
and the scheduling error type shared across refinement, sampling,
and the top-level scheduling entry point.
"""

from typing import Final, Protocol, Self

import pydantic
from pydantic import NonNegativeInt, PositiveFloat, model_validator

from athenspop.long.model.base import BaseDataModel

_DEPARTURE_WINDOW_ERROR: Final[str] = (
    "The earliest departure ({earliest_departure}) "
    "must be strictly before "
    "the latest departure ({latest_departure})."
)


class FlexibleTrip(BaseDataModel):
    """A single trip whose departure time is bounded by a window.

    This is the primary input unit for the scheduling pipeline.
    Each trip specifies an origin/destination zone pair, a purpose,
    a transport mode, and a departure time window defined by its
    earliest and latest bounds.
    """

    ozone: NonNegativeInt
    """Origin zone identifier."""
    dzone: NonNegativeInt
    """Destination zone identifier."""
    purp: str
    """Trip purpose label (e.g. ``"work"``, ``"home"``)."""
    mode: str
    """Transport mode label (e.g. ``"car"``, ``"bus"``)."""
    earliest_departure: PositiveFloat
    """Earliest possible departure time, in hours from midnight."""
    latest_departure: PositiveFloat
    """Latest possible departure time, in hours from midnight."""

    @model_validator(mode="after")
    def _validate_departure_window(self) -> Self:
        if self.earliest_departure >= self.latest_departure:
            raise ValueError(
                _DEPARTURE_WINDOW_ERROR.format(
                    earliest_departure=self.earliest_departure,
                    latest_departure=self.latest_departure,
                )
            )
        return self


class TravelTimeFn(Protocol):
    """Protocol for user-provided travel-time functions.

    Implementations must return a strictly positive travel time
    (in hours) for a given origin, destination, mode, and
    departure time.
    """

    def __call__(
        self,
        ozone: int,
        dzone: int,
        mode: str,
        time: pydantic.PositiveFloat,
    ) -> pydantic.PositiveFloat: ...


class SchedulingError(Exception):
    """Raised when scheduling fails due to infeasible constraints."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
