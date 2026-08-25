# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module defines integer-second time units and generic diary defaults."""

import typing

#: One minute contains this number of seconds.
SECONDS_PER_MINUTE: typing.Final[int] = 60
#: One hour contains this number of seconds.
SECONDS_PER_HOUR: typing.Final[int] = 60 * SECONDS_PER_MINUTE
#: One civil day contains this number of seconds.
SECONDS_PER_DAY: typing.Final[int] = 24 * SECONDS_PER_HOUR
#: This value is the default clock origin for conversions to elapsed seconds.
DEFAULT_TIME_ORIGIN_CLOCK: typing.Final[str] = "00:00"
#: This value is the default duration of a diary observation window.
DEFAULT_OBSERVATION_WINDOW_SECONDS: typing.Final[int] = SECONDS_PER_DAY
#: This value is the default width of a discrete sequence interval.
DEFAULT_SEQUENCE_INTERVAL_SECONDS: typing.Final[int] = 15 * SECONDS_PER_MINUTE
#: This value is the default minimum duration between consecutive trips.
DEFAULT_MIN_ACTIVITY_DURATION_SECONDS: typing.Final[int] = 0
