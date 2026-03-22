#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Travel diary model composed of alternating activity and trip episodes."""

from functools import cached_property

from pydantic import NonNegativeFloat, PositiveFloat

from athenspop.long.model.base import BaseDataModel
from athenspop.long.model.episode import Activity, Episode, Trip


class TravelDiary(BaseDataModel):
    """Complete travel diary for a single individual.

    A diary is an ordered sequence of episodes that alternates between
    activities and trips, starting and ending with an activity.
    """

    pid: int
    """Unique identifier of the corresponding individual."""
    episodes: tuple[Episode, ...]
    """Ordered sequence of recorded episodes."""

    @cached_property
    def activities(self) -> tuple[Activity, ...]:
        """Activity episodes extracted from the diary."""
        return tuple(
            episode for episode in self.episodes if isinstance(episode, Activity)
        )

    @cached_property
    def trips(self) -> tuple[Trip, ...]:
        """Trip episodes extracted from the diary."""
        return tuple(episode for episode in self.episodes if isinstance(episode, Trip))

    @property
    def otime(self) -> NonNegativeFloat:
        """Start time of the diary (start of the first episode)."""
        return self.episodes[0].otime

    @property
    def dtime(self) -> NonNegativeFloat:
        """End time of the diary (end of the last episode)."""
        return self.episodes[-1].dtime

    @property
    def duration(self) -> PositiveFloat:
        """Total duration of the diary in hours."""
        return self.dtime - self.otime
