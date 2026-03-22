#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

import re
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from athenspop.long.model.chain import (
    FlexibleTripChain,
    _EMPTY_CHAIN_ERROR,
    _MONOTONICITY_ERROR,
    _SPATIAL_CONTINUITY_ERROR,
)
from athenspop.long.scheduling.base import FlexibleTrip


class TestFlexibleTripChain:
    def test_valid_single_trip_chain(
        self, make_trip: Callable[..., FlexibleTrip]
    ) -> None:
        """Accepts a chain with a single valid trip."""
        # Monotonicity and continuity are vacuously true for one trip.
        chain = FlexibleTripChain(
            pid=1,
            trips=(make_trip(ozone=0, dzone=1),),
        )
        assert chain.pid == 1
        assert len(chain.trips) == 1

    def test_valid_multi_trip_chain(
        self, make_trip: Callable[..., FlexibleTrip]
    ) -> None:
        """Accepts a spatially continuous chain with monotonic departures."""
        chain = FlexibleTripChain(
            pid=1,
            trips=(
                make_trip(
                    ozone=0,
                    dzone=1,
                    earliest_departure=6.0,
                    latest_departure=8.0,
                ),
                make_trip(
                    ozone=1,
                    dzone=2,
                    earliest_departure=9.0,
                    latest_departure=11.0,
                ),
                make_trip(
                    ozone=2,
                    dzone=0,
                    earliest_departure=17.0,
                    latest_departure=19.0,
                ),
            ),
        )
        assert len(chain.trips) == 3

    def test_rejects_empty_chain(self) -> None:
        """Rejects a chain with no trips."""
        with pytest.raises(
            ValidationError,
            match=re.escape(_EMPTY_CHAIN_ERROR),
        ):
            FlexibleTripChain(pid=1, trips=())

    def test_rejects_non_monotonic_departures(
        self, make_trip: Callable[..., FlexibleTrip]
    ) -> None:
        """Rejects a chain where earliest departures decrease."""
        expected = _MONOTONICITY_ERROR.format(
            index=0,
            curr_earliest=9.0,
            next_index=1,
            next_earliest=6.0,
        )
        with pytest.raises(
            ValidationError,
            match=re.escape(expected),
        ):
            FlexibleTripChain(
                pid=1,
                trips=(
                    make_trip(
                        ozone=0,
                        dzone=1,
                        earliest_departure=9.0,
                        latest_departure=11.0,
                    ),
                    make_trip(
                        ozone=1,
                        dzone=2,
                        earliest_departure=6.0,
                        latest_departure=8.0,
                    ),
                ),
            )

    def test_allows_equal_earliest_departures(
        self, make_trip: Callable[..., FlexibleTrip]
    ) -> None:
        """Accepts consecutive trips with the same earliest departure."""
        chain = FlexibleTripChain(
            pid=1,
            trips=(
                make_trip(ozone=0, dzone=1),
                make_trip(ozone=1, dzone=2),
            ),
        )
        assert len(chain.trips) == 2

    def test_rejects_spatial_discontinuity(
        self, make_trip: Callable[..., FlexibleTrip]
    ) -> None:
        """Rejects a chain where a trip origin differs from the prior destination."""
        expected = _SPATIAL_CONTINUITY_ERROR.format(
            index=0,
            curr_dzone=1,
            next_index=1,
            next_ozone=5,
        )
        with pytest.raises(
            ValidationError,
            match=re.escape(expected),
        ):
            FlexibleTripChain(
                pid=1,
                trips=(
                    make_trip(ozone=0, dzone=1),
                    make_trip(
                        ozone=5,
                        dzone=2,
                        earliest_departure=9.0,
                        latest_departure=11.0,
                    ),
                ),
            )
