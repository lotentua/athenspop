"""Shared type contracts used across the travel diary package."""

from collections.abc import Callable
from typing import Final

import numpy as np

type DissimilarityMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
type TravelTimeFunction = Callable[[str, str, str, int], int]

__all__: Final[tuple[str, ...]] = (
    "DissimilarityMatrix",
    "TravelTimeFunction",
)
