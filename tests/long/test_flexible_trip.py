#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

import re
from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from athenspop.long.scheduling.base import (
    FlexibleTrip,
    _DEPARTURE_WINDOW_ERROR,
)


class TestFlexibleTrip:
    def test_valid_trip(
        self, make_trip: Callable[..., FlexibleTrip]
    ) -> None:
        """Accepts a trip with valid fields and correct time window."""
        trip = make_trip()
        assert trip.ozone == 1
        assert trip.dzone == 2
        assert trip.earliest_departure == 6.0
        assert trip.latest_departure == 8.0

    @pytest.mark.parametrize(
        "earliest_departure, latest_departure",
        [
            # Rejects a trip whose earliest departure equals its latest.
            (8.0, 8.0),
            # Rejects a trip whose earliest departure exceeds its latest.
            (9.0, 8.0),
        ],
    )
    def test_rejects_invalid_departure_window(
        self,
        make_trip: Callable[..., FlexibleTrip],
        earliest_departure: float,
        latest_departure: float,
    ) -> None:
        """Rejects trips whose departure window is empty or inverted."""
        expected = _DEPARTURE_WINDOW_ERROR.format(
            earliest_departure=earliest_departure,
            latest_departure=latest_departure,
        )
        with pytest.raises(
            ValidationError,
            match=re.escape(expected),
        ):
            make_trip(
                earliest_departure=earliest_departure,
                latest_departure=latest_departure,
            )

    @pytest.mark.parametrize(
        "overrides",
        [
            # Rejects a trip with a negative origin zone.
            dict(ozone=-1),
            # Rejects a trip with a negative destination zone.
            dict(dzone=-1),
            # Rejects a trip with a zero earliest departure time.
            dict(earliest_departure=0.0),
            # Rejects a trip with a zero latest departure time.
            dict(latest_departure=0.0),
        ],
    )
    def test_rejects_invalid_field_value(
        self,
        make_trip: Callable[..., FlexibleTrip],
        overrides: dict[str, Any],
    ) -> None:
        """Rejects trips with field values outside their valid domain."""
        with pytest.raises(ValidationError):
            make_trip(**overrides)

    def test_is_frozen(
        self, make_trip: Callable[..., FlexibleTrip]
    ) -> None:
        """Prevents mutation of trip fields after construction."""
        trip = make_trip()
        with pytest.raises(ValidationError):
            trip.ozone = 99
