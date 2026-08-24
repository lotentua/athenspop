"""Canonical dataframe schema vocabulary shared by model and validation code."""

from enum import StrEnum
from typing import Final

TRIPS_TABLE: Final[str] = "trips"
PERSONS_TABLE: Final[str] = "persons"
HOUSEHOLDS_TABLE: Final[str] = "households"

TRIP_KEY_COLUMNS: Final[tuple[str, ...]] = (
    "household_id",
    "person_id",
    "trip_id",
)
PERSON_KEY_COLUMNS: Final[tuple[str, ...]] = ("household_id", "person_id")
HOUSEHOLD_KEY_COLUMNS: Final[tuple[str, ...]] = ("household_id",)
TRIP_REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    *TRIP_KEY_COLUMNS,
    "origin",
    "destination",
    "purpose",
    "mode",
)
TRIP_TIMING_COLUMNS: Final[tuple[str, ...]] = (
    "departure_second",
    "arrival_second",
    "travel_time_seconds",
    "earliest_departure_second",
    "latest_departure_second",
)
TRIP_RESERVED_COLUMNS: Final[tuple[str, ...]] = (
    *TRIP_REQUIRED_COLUMNS,
    *TRIP_TIMING_COLUMNS,
    "trip_sequence",
    "timing_pattern",
)
UNSUPPORTED_ARRIVAL_WINDOW_COLUMNS: Final[tuple[str, ...]] = (
    "earliest_arrival_second",
    "latest_arrival_second",
)
SECOND_COLUMNS: Final[tuple[str, ...]] = (
    "departure_second",
    "arrival_second",
    "travel_time_seconds",
    "earliest_departure_second",
    "latest_departure_second",
    "earliest_arrival_second",
    "latest_arrival_second",
)


class TimingPattern(StrEnum):
    """Supported per-row timing patterns for trip rows.

    Attributes:
        DEPARTURE_ARRIVAL:
            Row supplies concrete departure and arrival seconds.
        DEPARTURE_DURATION:
            Row supplies concrete departure seconds and travel duration seconds.
        DEPARTURE_TRAVEL_TIME_FUNCTION:
            Row supplies concrete departure seconds and relies on a travel-time callable.
        DEPARTURE_WINDOW_DURATION:
            Row supplies a departure window and travel duration seconds.
        DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION:
            Row supplies a departure window and relies on a travel-time callable.
    """

    DEPARTURE_ARRIVAL = "departure_arrival"
    DEPARTURE_DURATION = "departure_duration"
    DEPARTURE_TRAVEL_TIME_FUNCTION = "departure_travel_time_function"
    DEPARTURE_WINDOW_DURATION = "departure_window_duration"
    DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION = (
        "departure_window_travel_time_function"
    )


__all__: Final[tuple[str, ...]] = (
    "HOUSEHOLDS_TABLE",
    "HOUSEHOLD_KEY_COLUMNS",
    "PERSONS_TABLE",
    "PERSON_KEY_COLUMNS",
    "SECOND_COLUMNS",
    "TRIPS_TABLE",
    "TRIP_KEY_COLUMNS",
    "TRIP_REQUIRED_COLUMNS",
    "TRIP_RESERVED_COLUMNS",
    "TRIP_TIMING_COLUMNS",
    "UNSUPPORTED_ARRIVAL_WINDOW_COLUMNS",
    "TimingPattern",
)
