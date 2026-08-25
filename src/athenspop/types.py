# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Define shared type contracts for the travel diary package."""

import collections.abc

import numpy as np

#: Square pairwise dissimilarity matrix of floating-point values.
type DissimilarityMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
#: Travel-second resolver parameterized by origin, destination, mode, and departure.
type TravelTimeFunction = collections.abc.Callable[[str, str, str, int], int]
