#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from typing import Annotated, Protocol

import numpy.typing as npt

from athenspop.models.trips import TripMode

Array3D = Annotated[npt.NDArray, tuple[int, int, int]]


class TravelTimeFunction(Protocol):
    def __call__(
        self, origin: int, destination: int, mode: TripMode, departure: float
    ) -> float: ...
