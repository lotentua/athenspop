#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Episode models representing activities and trips in a travel diary."""

from abc import ABC
from functools import cached_property
from typing import TypeAlias

from pydantic import NonNegativeFloat, PositiveFloat

from athenspop.long.model.base import BaseDataModel


class BaseEpisode(BaseDataModel, ABC):
    """Abstract base class for all diary episodes.

    An episode is a contiguous time interval during which a person
    performs an activity or travels between locations.
    """

    otime: NonNegativeFloat
    """Start time of the episode, in hours from midnight."""
    dtime: NonNegativeFloat
    """End time of the episode, in hours from midnight."""

    @cached_property
    def duration(self) -> PositiveFloat:
        """Duration of the episode in hours."""
        return self.dtime - self.otime


class Activity(BaseEpisode):
    """A stationary activity episode at a single location."""

    purpose: str
    """Activity purpose label (e.g. ``"work"``, ``"home"``)."""
    location: int
    """Zone identifier of the activity location."""


class Trip(BaseEpisode):
    """A travel episode between two locations."""

    ozone: int
    """Origin zone identifier."""
    dzone: int
    """Destination zone identifier."""
    mode: str
    """Transport mode label (e.g. ``"car"``, ``"bus"``)."""


Episode: TypeAlias = Activity | Trip
"""Union type covering both episode kinds."""
