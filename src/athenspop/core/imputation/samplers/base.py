#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from abc import ABC
from collections.abc import Iterable

import numpy as np

from athenspop.models.diaries import ConcreteTimeDiary
from athenspop.models.trips import TripPurpose


class DepartureTimeSampler(ABC):
    def __init__(
        self,
        diaries: Iterable[ConcreteTimeDiary],
        min_activity_duration: float,
        rng=np.random.Generator,
    ) -> None:
        """Base trip departure time sampler.

        Samplers inheriting from this class should be used only to impute missing trips.
        For samplers related to schedule generation, see `athenspop.core.scheduling.samplers`.

        Args:
            diaries: The diaries to use to build an underlying time model.
            min_activity_duration: The minimum activity duration to enforce during sampling.
            rng: The random number generator to use during sampling.
        """
        self._diaries = diaries
        self._min_activity_duration = min_activity_duration
        self._rng = rng

    def sample(self, purpose: TripPurpose, arrival_time: float) -> float: ...
