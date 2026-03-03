#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


import math
from typing import Self

from pydantic import NonNegativeFloat, PositiveFloat, model_validator

from athenspop.long.model.base import BaseDataModel
from athenspop.long.model.episode import Activity, Episode, Trip


class TravelDiary(BaseDataModel):
    """Travel diary."""

    pid: int
    """The unique identifier of the corresponding individual."""
    episodes: tuple[Episode, ...]
    """The recorded episodes."""

    @property
    def activities(self) -> tuple[Activity, ...]:
        """The recorded activities."""
        return tuple(
            episode for episode in self.episodes if isinstance(episode, Activity)
        )

    @property
    def trips(self) -> tuple[Trip, ...]:
        """The recorded trips."""
        return tuple(episode for episode in self.episodes if isinstance(episode, Trip))

    @property
    def otime(self) -> NonNegativeFloat:
        """The start time of the diary."""
        return self.episodes[0].otime

    @property
    def dtime(self) -> NonNegativeFloat:
        """The end time of the diary."""
        return self.episodes[-1].dtime

    @property
    def duration(self) -> PositiveFloat:
        """The duration of the diary."""
        return self.dtime - self.otime

    @model_validator(mode="after")
    def _validate_has_at_least_one_episode(self) -> Self:
        if len(self.episodes) == 0:
            raise ValueError("The diary must record at least one episode.")

    @model_validator(mode="after")
    def _validate_first_episode_is_activity(self) -> Self:
        if not isinstance(self.episodes[0], Activity):
            raise ValueError("The diary must start with an activity episode.")

    @model_validator(mode="after")
    def _validate_episode_types_alternate(self) -> Self:
        for i in range(len(self.episodes) - 1):
            curr_episode, next_episode = self.episodes[i], self.episodes[i + 1]
            if type(curr_episode) is type(next_episode):
                raise ValueError(
                    f"The diary must contain alternating activity and trip episodes but the {i!r}-th and {i + 1!r}-th episodes are of the same type."
                )

    @model_validator(mode="after")
    def _validate_last_episode_is_activity(self) -> Self:
        if not isinstance(self.episodes[-1], Activity):
            raise ValueError("The diary must end with an activity episode.")

    @model_validator(mode="after")
    def _validate_temporal_domain_is_continuous(self) -> Self:
        for i in range(len(self.episodes) - 1):
            curr_episode, next_episode = self.episodes[i], self.episodes[i + 1]

            diff = curr_episode.dtime - next_episode.otime
            if math.isclose(diff, 0):
                raise ValueError(
                    f"The diary must record temporally continuous episodes but there is a {diff!r}-minute interruption between the end of the {i!r}-th and the start of the {i + 1!r} -th episode."
                )
