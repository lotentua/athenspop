#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

from collections.abc import Callable
from typing import Any

import pytest

from athenspop.long.scheduling.base import FlexibleTrip


@pytest.fixture
def make_trip() -> Callable[..., FlexibleTrip]:
    """Factory fixture for creating FlexibleTrip instances."""

    def _factory(**overrides: Any) -> FlexibleTrip:
        defaults = dict(
            ozone=1,
            dzone=2,
            purp="work",
            mode="car",
            earliest_departure=6.0,
            latest_departure=8.0,
        )
        defaults.update(overrides)
        return FlexibleTrip(**defaults)

    return _factory
