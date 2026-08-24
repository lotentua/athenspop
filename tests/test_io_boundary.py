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
        (
            datetime(year=2026, month=1, day=1, hour=4, minute=15, tzinfo=UTC),
            900,
        ),
        (timedelta(hours=5), 3_600),
        (12_600, 84_600),
        (pd.Timestamp("2026-01-01 04:01:00"), 60),
        (pd.Timedelta(hours=4, minutes=30), 1_800),
    ],
)
def test_clock_seconds_from_time_origin_wraps_clock_values_around_diary_start(
    value: ClockValue, expected: int
) -> None:
    assert clock_seconds_from_time_origin(value, time_origin_clock="04:00") == expected


def test_generic_clock_origin_defaults_to_civil_midnight() -> None:
    assert clock_seconds_from_time_origin("04:00") == 14_400


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
        time_origin_clock="04:00",
    )
    assert "departure_second" not in frame.columns
    assert converted["departure_second"].tolist() == [0, 84_600]
    assert converted["arrival_second"].iloc[0] == 1_800
    assert pd.isna(converted["arrival_second"].iloc[1])
    assert str(converted["arrival_second"].dtype) == "Int64"


def test_convert_clock_columns_rejects_non_scalar_cells() -> None:
    frame = pd.DataFrame([{"departure_clock": ["04:00"]}])

    with pytest.raises(ValueError, match="scalar clock values"):
        convert_clock_columns(frame, {"departure_clock": "departure_second"})


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 1, 1, microsecond=500_000, tzinfo=UTC),
        time(microsecond=500_000),
        pd.Timestamp("2026-01-01 00:00:00.000000500"),
        pd.Timedelta(1, unit="ns"),
        pd.Timedelta(seconds=1, nanoseconds=1),
        pd.NaT,
    ],
)
def test_clock_seconds_rejects_fractional_and_missing_temporal_values(
    value: ClockValue,
) -> None:
    with pytest.raises(
        ValueError,
        match=r"whole seconds|must not be missing",
    ):
        clock_seconds_from_time_origin(value)


def test_convert_clock_columns_reads_overlapping_sources_from_input_snapshot() -> None:
    frame = pd.DataFrame([{"start": "04:00", "end": "05:00"}])

    converted = convert_clock_columns(
        frame,
        {"start": "end", "end": "start"},
    )

    assert converted.to_dict(orient="records") == [{"start": 18_000, "end": 14_400}]


def test_convert_clock_columns_rejects_duplicate_targets() -> None:
    frame = pd.DataFrame([{"start": "04:00", "end": "05:00"}])

    with pytest.raises(ValueError, match="target names must be unique"):
        convert_clock_columns(
            frame,
            {"start": "second", "end": "second"},
        )
