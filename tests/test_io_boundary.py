from datetime import UTC, datetime, time, timedelta

import pandas as pd
import pytest

from athenspop.io import (
    ClockValue,
    clock_seconds_from_time_origin,
    convert_clock_columns,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("04:00", 0),
        ("04:00:05", 5),
        ("03:30", 84_600),
        ("09:15", 18_900),
        (time(hour=3, minute=30), 84_600),
        (datetime(year=2026, month=1, day=1, hour=4, minute=15, tzinfo=UTC), 900),
        (timedelta(hours=5), 3_600),
        (12_600, 84_600),
        (pd.Timestamp("2026-01-01 04:01:00"), 60),
        (pd.Timedelta(hours=4, minutes=30), 1_800),
    ],
)
def test_clock_seconds_from_time_origin_wraps_clock_values_around_diary_start(value: ClockValue, expected: int) -> None:
    assert clock_seconds_from_time_origin(value) == expected


@pytest.mark.parametrize("bad_value", ["24:00", "07:99", "07", 86_400, True])
def test_clock_seconds_from_time_origin_rejects_invalid_clock_values(
    bad_value: ClockValue,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        clock_seconds_from_time_origin(bad_value)


def test_convert_clock_columns_returns_copy_with_none_for_missing_values() -> None:
    frame = pd.DataFrame(
        [
            {"departure_clock": "04:00", "arrival_clock": "04:30"},
            {"departure_clock": "03:30", "arrival_clock": None},
        ]
    )
    converted = convert_clock_columns(
        frame,
        {
            "departure_clock": "departure_second",
            "arrival_clock": "arrival_second",
        },
    )
    assert "departure_second" not in frame.columns
    assert converted["departure_second"].tolist() == [0, 84_600]
    assert converted["arrival_second"].iloc[0] == 1_800
    assert pd.isna(converted["arrival_second"].iloc[1])
