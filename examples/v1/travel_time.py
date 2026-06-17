#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from functools import cached_property
from typing import Any

import numpy as np
from pydantic import ConfigDict, validate_call

from athenspop.models.trips import TripMode, TripModeCategory
from athenspop.utils.typing import Array3D


class TravelTimeCalculator:
    def __init__(
        self,
        # NumPy Arrays
        driving_matrix: Array3D[float],
        transit_matrix: Array3D[float],
        zonal_lengths: np.ndarray[tuple[Any], np.dtype[float]],
        # JSON
        zone_encoder: dict[str, int],
    ) -> None:
        self._driving_matrix = driving_matrix
        self._transit_matrix = transit_matrix
        self._zonal_lengths = zonal_lengths

        # TODO: Use Pydantic to coerce the zone encoder to the required type.
        self._zone_encoder = {int(k): v for k, v in zone_encoder.items()}

        # TODO: Provide this information along with the other resources.
        self._timestamps = np.arange(0, 24, step=2)

    @cached_property
    def _driving_means(self) -> np.ndarray[tuple[Any], np.dtype[float]]:
        # Some trips may not be feasible under certain conditions (e.g., when using public transport relatively past the end of its operational time window), in which case the Google Directions API returns NaN for the corresponding travel time.
        return np.nanmean(self._driving_matrix, axis=(1, 2))

    @cached_property
    def _transit_means(self) -> np.ndarray[tuple[Any], np.dtype[float]]:
        return np.nanmean(self._transit_matrix, axis=(1, 2))

    @validate_call(config=ConfigDict(allow_inf_nan=False), validate_return=True)
    def calculate(
        self, origin: int, destination: int, mode: TripMode, departure: float
    ) -> float:
        if origin == destination:
            return self._calculate_intrazonal_trip(origin, mode)

        return self._calculate_interzonal_trip(origin, destination, mode, departure)

    def _calculate_intrazonal_trip(self, zone: int, mode: TripMode) -> float:
        if zone in self._zone_encoder:
            length = self._zonal_lengths[self._zone_encoder[zone]]
        else:
            # loguru.logger.warning(
            #     f"Trip Endpoints: {zone} → {zone}: The zone is invalid."
            # )
            length = np.mean(self._zonal_lengths)

        return length / mode.mean_speed

    def _calculate_interzonal_trip(
        self, origin: int, destination: int, mode: TripMode, departure_time: float
    ):
        if origin in self._zone_encoder and destination in self._zone_encoder:
            encoded_origin = self._zone_encoder[origin]
            encoded_destination = self._zone_encoder[destination]

            driving_samples = self._driving_matrix[
                :, encoded_origin, encoded_destination
            ]
            transit_samples = self._transit_matrix[
                :, encoded_origin, encoded_destination
            ]
        else:
            invalid_zones = []
            if origin not in self._zone_encoder:
                invalid_zones.append("origin")
            if destination not in self._zone_encoder:
                invalid_zones.append("destination")
            # loguru.logger.warning(
            #     f"Trip Endpoints: {origin} → {destination}:"
            #     f" "
            #     f"The {' and '.join(invalid_zones)} {'zone is' if len(invalid_zones) == 1 else 'zones are'} invalid."
            # )

            driving_samples = self._driving_means
            transit_samples = self._transit_means

        if mode.category == TripModeCategory.TRANSIT:
            return self._interpolate_linear(
                departure_time, time_samples=transit_samples
            )

        driving_time = self._interpolate_linear(
            departure_time, time_samples=driving_samples
        )
        scaling_factor = TripMode.CAR.mean_speed / mode.mean_speed

        return driving_time * scaling_factor

    def _interpolate_linear(
        self, time: float, time_samples: np.ndarray[tuple[Any], np.dtype[float]]
    ) -> float:
        return np.interp(
            # The input time is automatically normalized by the sample period.
            time,
            xp=self._timestamps,
            fp=time_samples,
            period=24,
        )
