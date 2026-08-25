# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module defines shared type contracts for the travel diary package."""

import collections.abc

import numpy as np

#: This type represents a square pairwise dissimilarity matrix of floating-point values.
type DissimilarityMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
#: This callable resolves travel seconds from an origin, destination, mode, and
#: departure.
type TravelTimeFunction = collections.abc.Callable[[str, str, str, int], int]
