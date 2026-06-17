#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from typing import cast

from athenspop.models.trips import _TRIP_MODE_DATA, TripMode


def test_trip_mode_annotations():
    registered_modes = cast("set[TripMode]", set(TripMode))
    annotated_modes = cast("set[TripMode]", set(_TRIP_MODE_DATA.keys()))

    missing_modes = registered_modes - annotated_modes
    if missing_modes:
        raise AssertionError(
            f"The following trip mode(s) are registered but not annotated with metadata: {sorted('TripMode.' + mode.name for mode in missing_modes)}."
        )
