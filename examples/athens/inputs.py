"""Convert wide CSuM-style diary rows into canonical long-form inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd

type RawCell = str | int | float | np.integer | np.floating | None

WIDE_DIARY_COLUMNS: Final[tuple[str, ...]] = (
    "pid",
    "gender",
    "age",
    "education",
    "employment",
    "income",
    "car_own",
    "home",
)
MAX_TRIPS_PER_DIARY: Final[int] = 5
SECONDS_PER_HOUR: Final[int] = 3600
ATHENS_TIME_ORIGIN_HOUR: Final[int] = 4
DEFAULT_FIXTURE_TRAVEL_TIME_SECONDS: Final[int] = 900
DEFAULT_ATHENS_WIDE_DIARY_PATH: Final[Path] = Path(__file__).resolve().parent / "data" / "raw_diaries_athens_wide.csv"
TIME_WINDOWS: Final[tuple[tuple[int, int], ...]] = (
    (5, 8),
    (8, 11),
    (11, 14),
    (14, 17),
    (17, 20),
    (20, 23),
)
PURPOSE_MAP: Final[dict[str, str]] = {
    "1: work": "work",
    "2: return home": "home",
    "3: education": "education",
    "4: market": "market",
    "5: recreation": "recreation",
    "6: service": "other",
    "7: other": "other",
}
MODE_MAP: Final[dict[str, str]] = {
    "1: car": "car",
    "2: taxi": "car",
    "3: bus": "bus",
    "4: train": "train",
    "5: motorcycle": "motorcycle",
    "6: bicycle": "bicycle",
    "7: walk": "walk",
    "8: escooter": "escooter",
}


@dataclass(frozen=True, slots=True)
class AthensInputTables:
    """Canonical paper input dataframes plus source-stage counts."""

    trips: pd.DataFrame
    persons: pd.DataFrame
    households: pd.DataFrame
    raw_diaries: int
    canonical_trips: int


def load_wide_diary_fixture(
    path: Path,
    *,
    fixture_travel_time_seconds: int | None = DEFAULT_FIXTURE_TRAVEL_TIME_SECONDS,
) -> AthensInputTables:
    """Load a wide CSuM-style diary CSV and convert it to canonical long-form tables."""
    wide = pd.read_csv(path)
    return wide_diaries_to_canonical(wide, fixture_travel_time_seconds=fixture_travel_time_seconds)


def load_athens_wide_diaries(
    path: Path = DEFAULT_ATHENS_WIDE_DIARY_PATH,
    *,
    fixture_travel_time_seconds: int | None = DEFAULT_FIXTURE_TRAVEL_TIME_SECONDS,
) -> AthensInputTables:
    """Load the migrated 513-row CSuM-style wide diary source and convert it to canonical long-form tables."""
    return load_wide_diary_fixture(path, fixture_travel_time_seconds=fixture_travel_time_seconds)


def wide_diaries_to_canonical(
    wide: pd.DataFrame,
    *,
    fixture_travel_time_seconds: int | None = DEFAULT_FIXTURE_TRAVEL_TIME_SECONDS,
) -> AthensInputTables:
    """Convert wide diary rows with up to five trips into canonical `trips`, `persons`, and `households` tables."""
    _validate_wide_columns(wide)
    if fixture_travel_time_seconds is not None and fixture_travel_time_seconds <= 0:
        raise ValueError(f"`fixture_travel_time_seconds` must be positive, got {fixture_travel_time_seconds}.")
    usable = wide.dropna(subset=["pid", "home"]).copy()
    households = _households_from_wide(usable)
    persons = _persons_from_wide(usable)
    trips = _trips_from_wide(usable, fixture_travel_time_seconds=fixture_travel_time_seconds)
    return AthensInputTables(
        trips=trips,
        persons=persons,
        households=households,
        raw_diaries=len(wide),
        canonical_trips=len(trips),
    )


def _validate_wide_columns(wide: pd.DataFrame) -> None:
    missing = [column for column in WIDE_DIARY_COLUMNS if column not in wide.columns]
    for trip_number in range(1, MAX_TRIPS_PER_DIARY + 1):
        for stem in ("dest", "purp", "mode", "time"):
            column = f"{stem}{trip_number}"
            if column not in wide.columns:
                missing.append(column)
    if missing:
        raise ValueError(f"The wide diary table is missing required column(s): {', '.join(missing)}.")


def _households_from_wide(wide: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "household_id": _identity(row["pid"]),
            "home_zone": _zone(row["home"]),
        }
        for _, row in wide.iterrows()
    ]
    return pd.DataFrame(rows, columns=["household_id", "home_zone"])


def _persons_from_wide(wide: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "household_id": _identity(row["pid"]),
            "person_id": _identity(row["pid"]),
            "gender": _optional_text(row["gender"]),
            "age": int(row["age"]) if not pd.isna(row["age"]) else None,
            "education": _optional_text(row["education"]),
            "employment_status": _optional_text(row["employment"]),
            "monthly_income": _optional_text(row["income"]),
            "car_ownership": _optional_text(row["car_own"]),
        }
        for _, row in wide.iterrows()
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "household_id",
            "person_id",
            "gender",
            "age",
            "education",
            "employment_status",
            "monthly_income",
            "car_ownership",
        ],
    )


def _trips_from_wide(wide: pd.DataFrame, *, fixture_travel_time_seconds: int | None) -> pd.DataFrame:
    rows: list[dict[str, str | int | None]] = []
    for _, row in wide.iterrows():
        household_id = _identity(row["pid"])
        previous_zone = _zone(row["home"])
        previous_time_hour: int | None = None
        day_offset_hours = 0
        for trip_number in range(1, MAX_TRIPS_PER_DIARY + 1):
            destination = cast("RawCell", row[f"dest{trip_number}"])
            if pd.isna(destination):
                break
            raw_time_hour = _hour(row[f"time{trip_number}"])
            if previous_time_hour is not None and raw_time_hour < previous_time_hour:
                day_offset_hours += 24
            absolute_hour = raw_time_hour + day_offset_hours
            earliest_second, latest_second = _departure_window_seconds(absolute_hour)
            trip_row: dict[str, str | int | None] = {
                "household_id": household_id,
                "person_id": household_id,
                "trip_id": f"{household_id}_trip_{trip_number}",
                "trip_sequence": trip_number,
                "origin": previous_zone,
                "destination": _zone(destination),
                "purpose": _purpose(row[f"purp{trip_number}"]),
                "mode": _mode(row[f"mode{trip_number}"]),
                "earliest_departure_second": earliest_second,
                "latest_departure_second": latest_second,
            }
            if fixture_travel_time_seconds is not None:
                trip_row["travel_time_seconds"] = fixture_travel_time_seconds
            rows.append(trip_row)
            previous_zone = _zone(destination)
            previous_time_hour = raw_time_hour
    columns = [
        "household_id",
        "person_id",
        "trip_id",
        "trip_sequence",
        "origin",
        "destination",
        "purpose",
        "mode",
        "earliest_departure_second",
        "latest_departure_second",
    ]
    if fixture_travel_time_seconds is not None:
        columns.append("travel_time_seconds")
    frame = pd.DataFrame(rows, columns=columns)
    for column in (
        "trip_sequence",
        "earliest_departure_second",
        "latest_departure_second",
        "travel_time_seconds",
    ):
        if column not in frame.columns:
            continue
        frame[column] = frame[column].astype("Int64")
    return frame


def _departure_window_seconds(absolute_hour: int) -> tuple[int, int]:
    day_offset = absolute_hour // 24
    hour = absolute_hour % 24
    if hour >= 23:
        start_hour = 23 + day_offset * 24
        end_hour = 29 + day_offset * 24
    elif hour < 5:
        start_hour = -1 + day_offset * 24
        end_hour = 5 + day_offset * 24
    else:
        matching_window = next(window for window in TIME_WINDOWS if window[0] <= hour < window[1])
        start_hour = matching_window[0] + day_offset * 24
        end_hour = matching_window[1] + day_offset * 24
    return (
        max(0, (start_hour - ATHENS_TIME_ORIGIN_HOUR) * SECONDS_PER_HOUR),
        max(0, (end_hour - ATHENS_TIME_ORIGIN_HOUR) * SECONDS_PER_HOUR),
    )


def _identity(value: RawCell) -> str:
    if pd.isna(value):
        raise ValueError("Diary identity values cannot be missing.")
    return str(value)


def _zone(value: RawCell) -> str:
    if pd.isna(value):
        raise ValueError("Zone values cannot be missing.")
    if isinstance(value, float | np.floating):
        return str(int(value)) if float(value).is_integer() else str(float(value))
    if isinstance(value, int | np.integer):
        return str(int(value))
    return str(value)


def _hour(value: RawCell) -> int:
    if pd.isna(value):
        raise ValueError("Reported departure hour cannot be missing for a reported trip.")
    if isinstance(value, str) or isinstance(value, int | float | np.integer | np.floating):
        number = float(value)
    else:
        raise TypeError(f"Unsupported departure hour value {value!r}.")
    if not number.is_integer():
        raise ValueError(f"Reported departure hour must be an integer hour, got {value!r}.")
    return int(number)


def _purpose(value: RawCell) -> str:
    text = _required_text(value, "purpose")
    try:
        return PURPOSE_MAP[text]
    except KeyError as error:
        raise ValueError(f"Unsupported raw trip purpose {text!r}.") from error


def _mode(value: RawCell) -> str:
    text = _required_text(value, "mode")
    try:
        return MODE_MAP[text]
    except KeyError as error:
        raise ValueError(f"Unsupported raw trip mode {text!r}.") from error


def _optional_text(value: RawCell) -> str | None:
    return None if pd.isna(value) else str(value)


def _required_text(value: RawCell, label: str) -> str:
    if pd.isna(value):
        raise ValueError(f"Raw {label} cannot be missing for a reported trip.")
    return str(value)
