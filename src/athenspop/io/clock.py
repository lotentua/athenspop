# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module parses clock-of-day values into normalized integer seconds."""

import collections.abc
import datetime
import typing

import numpy as np
import pandas as pd

import athenspop.time_units

#: This type represents a clock-like scalar accepted by the conversion boundary.
type ClockValue = (
    str
    | int
    | datetime.time
    | datetime.datetime
    | datetime.timedelta
    | np.integer
    | pd.Timestamp
    | pd.Timedelta
)

#: An `HH:MM:SS` clock string contains this number of fields.
HH_MM_SS_PARTS: typing.Final[int] = 3
#: This value is the largest valid hour in a civil-clock value.
MAX_CLOCK_HOUR: typing.Final[int] = 23
#: This value is the largest valid minute or second in a civil-clock value.
MAX_CLOCK_MINUTE_OR_SECOND: typing.Final[int] = 59


def clock_seconds_from_time_origin(
    value: ClockValue,
    *,
    time_origin_clock: ClockValue = athenspop.time_units.DEFAULT_TIME_ORIGIN_CLOCK,
) -> int:
    """Convert a clock value to seconds from a diary time origin.

    Args:
        value: This clock value is expressed as `HH:MM`, `HH:MM:SS`, a datetime or
            time object, a timedelta, a pandas temporal value, or integer seconds
            after civil midnight.
        time_origin_clock: This clock value defines the diary time origin.

    Returns:
        The function returns integer seconds from the diary time-origin clock and
        wraps overnight within one civil day.

    Raises:
        TypeError: The function raises this error if a value has an unsupported type
            or is boolean.
        ValueError: The function raises this error if a value cannot be represented
            as whole seconds within one civil day.
    """
    civil_second = _clock_second_of_day(value, parameter_name="value")
    time_origin_second = _clock_second_of_day(
        time_origin_clock, parameter_name="time_origin_clock"
    )
    return (civil_second - time_origin_second) % athenspop.time_units.SECONDS_PER_DAY


def convert_clock_columns(
    frame: pd.DataFrame,
    columns: collections.abc.Mapping[str, str],
    *,
    time_origin_clock: ClockValue = athenspop.time_units.DEFAULT_TIME_ORIGIN_CLOCK,
) -> pd.DataFrame:
    """Convert dataframe clock columns to normalized second columns.

    Args:
        frame: This input dataframe contains the source clock columns.
        columns: This mapping associates source clock column names with target
            integer-second column names.
        time_origin_clock: This clock value defines the diary time origin.

    Returns:
        The function returns a dataframe copy with converted target columns. Missing
        source values remain missing.

    Raises:
        KeyError: The function raises this error if a requested source column is
            absent.
        TypeError: The function raises this error if a non-missing value has an
            unsupported type.
        ValueError: The function raises this error if a non-missing value is outside
            the supported clock domain.
    """
    target_columns = tuple(columns.values())
    if len(target_columns) != len(set(target_columns)):
        raise ValueError("Clock-column target names must be unique.")
    result = frame.copy()
    for source_column, target_column in columns.items():
        if source_column not in frame.columns:
            raise KeyError(f"Column {source_column!r} is not present in the dataframe.")
        converted: list[int | None] = []
        for row_index, value in frame[source_column].items():
            if not pd.api.types.is_scalar(value):
                raise ValueError(
                    f"`{source_column}` row {row_index!r} must contain scalar clock "
                    f"values, got {type(value).__name__}."
                )
            if bool(pd.isna(value)):
                converted.append(None)
            else:
                converted.append(
                    clock_seconds_from_time_origin(
                        typing.cast("ClockValue", value),
                        time_origin_clock=time_origin_clock,
                    )
                )
        result[target_column] = pd.Series(converted, index=result.index, dtype="Int64")
    return result


def _clock_second_of_day(value: ClockValue, *, parameter_name: str) -> int:
    """Normalize one supported clock value to seconds after civil midnight."""
    _validate_temporal_precision(value, parameter_name=parameter_name)
    if isinstance(value, bool | np.bool_):
        raise TypeError(f"`{parameter_name}` must be a clock value, not a boolean.")
    if isinstance(value, int | np.integer):
        return _validate_second_of_day(int(value), parameter_name=parameter_name)
    if isinstance(value, str):
        return _parse_clock_string(value, parameter_name=parameter_name)
    if isinstance(value, datetime.datetime | datetime.time | pd.Timestamp):
        return (
            value.hour * athenspop.time_units.SECONDS_PER_HOUR
            + value.minute * athenspop.time_units.SECONDS_PER_MINUTE
            + value.second
        )
    if isinstance(value, datetime.timedelta | pd.Timedelta):
        total_seconds = value.total_seconds()
        if not total_seconds.is_integer():
            raise ValueError(
                f"`{parameter_name}` must resolve to whole seconds within one day."
            )
        return _validate_second_of_day(
            int(total_seconds), parameter_name=parameter_name
        )
    raise TypeError(
        f"`{parameter_name}` must be HH:MM, HH:MM:SS, a clock time, a timedelta, a "
        "pandas timestamp/timedelta, or integer seconds after civil midnight."
    )


def _validate_temporal_precision(value: ClockValue, *, parameter_name: str) -> None:
    """Reject missing pandas scalars and subsecond temporal precision."""
    if value is pd.NaT or (
        isinstance(value, pd.Timestamp | pd.Timedelta) and pd.isna(value)
    ):
        raise ValueError(f"`{parameter_name}` must not be missing.")
    if isinstance(value, datetime.datetime | datetime.time) and value.microsecond != 0:
        raise ValueError(f"`{parameter_name}` must resolve to whole seconds.")
    if isinstance(value, pd.Timestamp) and value.nanosecond != 0:
        raise ValueError(f"`{parameter_name}` must resolve to whole seconds.")
    if isinstance(value, pd.Timedelta) and value != value.floor("s"):
        raise ValueError(f"`{parameter_name}` must resolve to whole seconds.")


def _parse_clock_string(value: str, *, parameter_name: str) -> int:
    """Parse `HH:MM` or `HH:MM:SS` text into seconds after civil midnight."""
    stripped = value.strip()
    parts = stripped.split(":")
    if len(parts) not in {2, 3} or any(part == "" for part in parts):
        raise ValueError(
            f"`{parameter_name}`={value!r} must use HH:MM or HH:MM:SS clock format."
        )
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == HH_MM_SS_PARTS else 0
    except ValueError as error:
        raise ValueError(
            f"`{parameter_name}`={value!r} must contain integer clock fields."
        ) from error
    if not 0 <= hour <= MAX_CLOCK_HOUR:
        raise ValueError(
            f"`{parameter_name}`={value!r} has an hour outside the inclusive "
            "range from 0 through 23."
        )
    if not 0 <= minute <= MAX_CLOCK_MINUTE_OR_SECOND:
        raise ValueError(
            f"`{parameter_name}`={value!r} has a minute outside the inclusive "
            "range from 0 through 59."
        )
    if not 0 <= second <= MAX_CLOCK_MINUTE_OR_SECOND:
        raise ValueError(
            f"`{parameter_name}`={value!r} has a second outside the inclusive "
            "range from 0 through 59."
        )
    return (
        hour * athenspop.time_units.SECONDS_PER_HOUR
        + minute * athenspop.time_units.SECONDS_PER_MINUTE
        + second
    )


def _validate_second_of_day(value: int, *, parameter_name: str) -> int:
    """Validate integer seconds after civil midnight."""
    if not 0 <= value < athenspop.time_units.SECONDS_PER_DAY:
        raise ValueError(
            f"`{parameter_name}` must be within one civil day: 0 <= seconds < "
            f"{athenspop.time_units.SECONDS_PER_DAY}."
        )
    return value
