#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


from abc import ABC
from typing import Self, TypeAlias

from pydantic import NonNegativeFloat, PositiveFloat, model_validator

from athenspop.long.model.base import BaseDataModel


class BaseEpisode(BaseDataModel, ABC):
    """Base episode."""

    otime: NonNegativeFloat
    """The start time of the episode."""
    dtime: NonNegativeFloat
    """The end time of the episode."""

    @property
    def duration(self) -> PositiveFloat:
        """The duration of the episode."""
        return self.dtime - self.otime

    @model_validator(mode="after")
    def _validate_has_positive_duration(self) -> Self:
        if self.otime <= self.dtime:
            raise ValueError(
                f"The start time of the episode: {self.otime!r} must be earlier than the corresponding end time: {self.dtime!r}."
            )
        return self


class Activity(BaseEpisode):
    """Activity episode."""

    purpose: str
    """The activity purpose."""
    location: int
    """The activity location."""


class Trip(BaseEpisode):
    """Trip episode."""

    ozone: int
    """The trip origin zone."""
    dzone: int
    """The trip destin zone."""
    mode: str
    """"The trip mode."""


Episode: TypeAlias = Activity | Trip
