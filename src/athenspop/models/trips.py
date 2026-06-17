#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from enum import UNIQUE, StrEnum, auto, verify
from typing import Final

from pydantic import NonNegativeFloat

from athenspop.models.base import ImmutableNumericBaseModel


############################################################
@verify(UNIQUE)
class TripModeCategory(StrEnum):
    DRIVING = auto()
    TRANSIT = auto()
    ACTIVE = auto()


class _TripModeData(ImmutableNumericBaseModel):
    category: TripModeCategory
    mean_speed: NonNegativeFloat


@verify(UNIQUE)
class TripMode(StrEnum):
    # Driving
    CAR = auto()
    MOTORCYCLE = auto()
    TAXI = auto()

    # Transit
    BUS = auto()
    TRAIN = auto()

    # Active
    # Micromobility
    BICYCLE = auto()
    ESCOOTER = auto()

    # Active
    # Miscellaneous
    WALK = auto()

    @property
    def category(self) -> TripModeCategory:
        return self._data.category

    @property
    def mean_speed(self) -> float:
        return self._data.mean_speed

    @property
    def _data(self) -> _TripModeData:
        return _TRIP_MODE_DATA[self]


_TRIP_MODE_DATA: Final[dict[TripMode, _TripModeData]] = {
    # Driving
    TripMode.CAR: _TripModeData(category=TripModeCategory.DRIVING, mean_speed=40),
    TripMode.MOTORCYCLE: _TripModeData(
        category=TripModeCategory.DRIVING, mean_speed=40
    ),
    TripMode.TAXI: _TripModeData(category=TripModeCategory.DRIVING, mean_speed=40),
    # Transit
    TripMode.BUS: _TripModeData(category=TripModeCategory.TRANSIT, mean_speed=35),
    TripMode.TRAIN: _TripModeData(category=TripModeCategory.TRANSIT, mean_speed=35),
    # Active
    # Micromobility
    TripMode.BICYCLE: _TripModeData(category=TripModeCategory.ACTIVE, mean_speed=15),
    TripMode.ESCOOTER: _TripModeData(category=TripModeCategory.ACTIVE, mean_speed=15),
    # Active
    # Miscellaneous
    TripMode.WALK: _TripModeData(category=TripModeCategory.ACTIVE, mean_speed=5),
}


class TripPurpose(StrEnum):
    # Rigid Timing
    EDUCATION = auto()
    WORK = auto()

    # Flexible Timing
    MARKET = auto()
    RECREATION = auto()
    SERVICE = auto()

    # Miscellaneous
    HOME = auto()
    OTHER = auto()


############################################################


class BaseTrip(ImmutableNumericBaseModel):
    """Base class for all trip types.

    A trip represents person-level movement between two locations with a specific purpose and mode of transportation.

    Attributes:
        orig:
            The unique orig identifier.
        dest:
            The unique dest identifier.
        purp:
            The purp.
        mode:
            The mode.
    """

    # TODO: Narrow down integer types.
    orig: int
    dest: int
    purp: TripPurpose
    mode: TripMode


class ConcreteTrip(BaseTrip):
    """A trip with a concrete departure time.

    This trip type is used when the exact departure time is known.

    Attributes:
        time:
            The departure time in hours from midnight.
    """

    time: NonNegativeFloat


class WindowedTrip(BaseTrip):
    """A trip with a variable departure time.

    This trip type is used when the departure time is specified as an interval rather than an exact value.

    Attributes:
        min_time:
            The min possible departure time in hours from midnight.
        max_time:
            The max possible departure time in hours from midnight.
    """

    min_time: NonNegativeFloat
    max_time: NonNegativeFloat
