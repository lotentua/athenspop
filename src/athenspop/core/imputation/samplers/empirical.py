#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from collections import defaultdict
from collections.abc import Iterable

import numpy as np
import scipy
from scipy.stats._result_classes import EmpiricalDistributionFunction
from typing_extensions import override

from athenspop.core.imputation.samplers.base import DepartureTimeSampler
from athenspop.models.diaries import ConcreteTimeDiary
from athenspop.models.trips import TripPurpose


class EmpiricalDepartureTimeSampler(DepartureTimeSampler):
    def __init__(
        self,
        diaries: Iterable[ConcreteTimeDiary],
        min_activity_duration: float,
        rng=np.random.Generator,
    ) -> None:
        super().__init__(diaries, min_activity_duration, rng)

        self._distributions = self._fit(diaries)

    @override
    def sample(self, purpose: TripPurpose, arrival_time: float) -> float:
        earliest_departure_time = arrival_time + self._min_activity_duration

        distribution = self._distributions.get(purpose)
        if distribution is None:
            return earliest_departure_time

        # Truncated Inverse Transform Sampling
        # https://en.wikipedia.org/wiki/Inverse_transform_sampling

        # Compute P(Departure Time <= Earliest Departure Time).
        earliest_departure_time_prob = distribution.evaluate(earliest_departure_time)

        sampled_departure_prob = self._rng.uniform(earliest_departure_time_prob, 1)
        # Invert the eCDF to obtain the actual departure time.
        sampled_departure_time = np.interp(
            sampled_departure_prob,
            xp=distribution.probabilities,
            fp=distribution.quantiles,
        )

        # Handle out-of-distribution times, i.e., later than the latest observed time for the input purpose.
        return max(earliest_departure_time, sampled_departure_time)

    def _fit(
        self, diaries: Iterable[ConcreteTimeDiary]
    ) -> dict[TripPurpose, EmpiricalDistributionFunction]:
        samples = self._collect_samples(diaries)
        return self._build_distributions(samples)

    @staticmethod
    def _collect_samples(
        diaries: Iterable[ConcreteTimeDiary],
    ) -> defaultdict[TripPurpose, list[float]]:
        samples = defaultdict(list)
        for diary in diaries:
            if len(diary.trips) == 1:
                continue

            for curr_index, curr_trip in enumerate(diary.trips):
                prev_trip = diary.trips[curr_index - 1]

                is_return = (
                    curr_trip.dest == diary.home and curr_trip.purp == TripPurpose.HOME
                )
                if is_return:
                    samples[prev_trip.purp].append(curr_trip.time)

        return samples

    @staticmethod
    def _build_distributions(
        samples: defaultdict[TripPurpose, list[float]],
    ) -> dict[TripPurpose, EmpiricalDistributionFunction]:
        return {
            purpose: scipy.stats.ecdf(sample).cdf for purpose, sample in samples.items()
        }
