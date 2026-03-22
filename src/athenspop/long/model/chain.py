#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Flexible trip chain model with boundary validation."""

from typing import Final, Self

from pydantic import model_validator

from athenspop.long.model.base import BaseDataModel
from athenspop.long.scheduling.base import FlexibleTrip

_EMPTY_CHAIN_ERROR: Final[str] = (
    "The trip chain must contain at least one trip."
)

_MONOTONICITY_ERROR: Final[str] = (
    "Departure times must be non-decreasing "
    "but trip {index} "
    "has earliest_departure={curr_earliest} "
    "which exceeds "
    "trip {next_index} "
    "earliest_departure={next_earliest}."
)

_SPATIAL_CONTINUITY_ERROR: Final[str] = (
    "Trip chain must be spatially continuous "
    "but trip {index} ends at zone {curr_dzone} "
    "while trip {next_index} "
    "starts at zone {next_ozone}."
)


class FlexibleTripChain(BaseDataModel):
    """Ordered sequence of flexible trips for a single person.

    Validates that the chain is non-empty, that earliest departure
    times are non-decreasing, and that consecutive trips are
    spatially continuous (each trip starts where the previous one
    ended).
    """

    pid: int
    """Unique person identifier."""
    trips: tuple[FlexibleTrip, ...]
    """Ordered sequence of flexible trips."""

    @model_validator(mode="after")
    def _validate_has_at_least_one_trip(self) -> Self:
        if len(self.trips) == 0:
            raise ValueError(_EMPTY_CHAIN_ERROR)
        return self

    @model_validator(mode="after")
    def _validate_departures_are_monotonic(self) -> Self:
        for i in range(len(self.trips) - 1):
            curr, nxt = self.trips[i], self.trips[i + 1]
            if curr.earliest_departure > nxt.earliest_departure:
                raise ValueError(
                    _MONOTONICITY_ERROR.format(
                        index=i,
                        curr_earliest=curr.earliest_departure,
                        next_index=i + 1,
                        next_earliest=nxt.earliest_departure,
                    )
                )
        return self

    @model_validator(mode="after")
    def _validate_spatial_continuity(self) -> Self:
        for i in range(len(self.trips) - 1):
            curr, nxt = self.trips[i], self.trips[i + 1]
            if curr.dzone != nxt.ozone:
                raise ValueError(
                    _SPATIAL_CONTINUITY_ERROR.format(
                        index=i,
                        curr_dzone=curr.dzone,
                        next_index=i + 1,
                        next_ozone=nxt.ozone,
                    )
                )
        return self
