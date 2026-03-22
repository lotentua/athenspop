#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

import re
from typing import Any

import pytest

from athenspop.long.scheduling.base import SchedulingError
from athenspop.long.scheduling.scheduling import (
    _TRAVEL_TIME_FN_ERROR,
    _validated_travel_time_fn,
)


class TestValidatedTravelTimeFn:
    def test_passes_through_positive_result(self) -> None:
        """Forwards the result when the inner function returns a positive value."""
        fn = _validated_travel_time_fn(lambda o, d, m, t: 15.0)
        assert fn(1, dzone=2, mode="car", time=6.0) == 15.0

    @pytest.mark.parametrize(
        "return_value, ozone, dzone, mode, time",
        [
            # Raises SchedulingError when the inner function returns zero.
            (0.0, 1, 2, "car", 6.0),
            # Raises SchedulingError when the inner function returns a negative value.
            (-5.0, 0, 3, "bus", 9.0),
        ],
    )
    def test_rejects_non_positive_result(
        self,
        return_value: float,
        ozone: int,
        dzone: int,
        mode: str,
        time: float,
    ) -> None:
        """Raises SchedulingError when travel_time_fn returns a non-positive value."""
        fn = _validated_travel_time_fn(lambda o, d, m, t: return_value)
        expected = _TRAVEL_TIME_FN_ERROR.format(
            ozone=ozone,
            dzone=dzone,
            mode=mode,
            time=time,
            result=return_value,
        )
        with pytest.raises(
            SchedulingError,
            match=re.escape(expected),
        ):
            fn(ozone, dzone=dzone, mode=mode, time=time)

    def test_forwards_arguments_to_inner_fn(self) -> None:
        """Passes all four arguments through to the wrapped function."""
        captured: dict[str, Any] = {}

        def spy(
            ozone: int, dzone: int, mode: str, time: float
        ) -> float:
            captured.update(
                ozone=ozone, dzone=dzone, mode=mode, time=time
            )
            return 10.0

        fn = _validated_travel_time_fn(spy)
        fn(5, dzone=7, mode="walk", time=12.0)
        assert captured == {
            "ozone": 5,
            "dzone": 7,
            "mode": "walk",
            "time": 12.0,
        }
