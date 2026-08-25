# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Parse clock-of-day values into normalized integer seconds."""

import datetime
from collections.abc import Mapping
from typing import Final, cast

import numpy as np
import pandas as pd

import athenspop.time_units

#: Clock-like scalar accepted by the conversion boundary.
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

#: Number of fields in an `HH:MM:SS` clock string.
HH_MM_SS_PARTS: Final[int] = 3
#: Largest valid hour in a civil-clock value.
MAX_CLOCK_HOUR: Final[int] = 23
#: Largest valid minute or second in a civil-clock value.
MAX_CLOCK_MINUTE_OR_SECOND: Final[int] = 59


def clock_seconds_from_time_origin(
    value: ClockValue,
    *,
    time_origin_clock: ClockValue = athenspop.time_units.DEFAULT_TIME_ORIGIN_CLOCK,
) -> int:
    """Convert a clock value to seconds from a diary time origin.

    Args:
        value:
            Clock value expressed as `HH:MM`, `HH:MM:SS`, a datetime or
            time object, a timedelta, a pandas temporal value, or integer seconds
            after civil midnight.
        time_origin_clock:
            Clock value that defines the diary time origin.

    Returns:
        Integer seconds from the diary time-origin clock, wrapped within one civil
        day.

    Raises:
        TypeError:
            If a value has an unsupported type or is boolean.
        ValueError:
            If a value cannot be represented as whole seconds within one
            civil day.
    """
    civil_second = _clock_second_of_day(value, parameter_name="value")
    time_origin_second = _clock_second_of_day(
        time_origin_clock, parameter_name="time_origin_clock"
    )
    return (civil_second - time_origin_second) % athenspop.time_units.SECONDS_PER_DAY


def convert_clock_columns(
    frame: pd.DataFrame,
    columns: Mapping[str, str],
    *,
    time_origin_clock: ClockValue = athenspop.time_units.DEFAULT_TIME_ORIGIN_CLOCK,
) -> pd.DataFrame:
    """Convert dataframe clock columns to normalized second columns.

    Args:
        frame:
            Input dataframe containing the source clock columns.
        columns:
            Mapping from source clock column names to target
            integer-second column names.
        time_origin_clock:
            Clock value that defines the diary time origin.

    Returns:
        Dataframe copy with converted target columns. Missing source values remain
        missing.

    Raises:
        KeyError:
            If a requested source column is absent.
        TypeError:
            If a non-missing value has an unsupported type.
        ValueError:
            If a non-missing value is outside the supported clock domain.
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
                        cast("ClockValue", value),
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
