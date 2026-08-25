# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Define integer-second time units and generic diary defaults."""

import typing

#: Seconds per minute.
SECONDS_PER_MINUTE: typing.Final[int] = 60
#: Seconds per hour.
SECONDS_PER_HOUR: typing.Final[int] = 60 * SECONDS_PER_MINUTE
#: Seconds per civil day.
SECONDS_PER_DAY: typing.Final[int] = 24 * SECONDS_PER_HOUR
#: Default clock origin for elapsed-second conversions.
DEFAULT_TIME_ORIGIN_CLOCK: typing.Final[str] = "00:00"
#: Default diary observation-window duration.
DEFAULT_OBSERVATION_WINDOW_SECONDS: typing.Final[int] = SECONDS_PER_DAY
#: Default discrete-sequence interval width.
DEFAULT_SEQUENCE_INTERVAL_SECONDS: typing.Final[int] = 15 * SECONDS_PER_MINUTE
#: Default minimum duration between consecutive trips.
DEFAULT_MIN_ACTIVITY_DURATION_SECONDS: typing.Final[int] = 0
