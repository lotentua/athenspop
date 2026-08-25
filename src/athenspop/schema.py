# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Define the canonical dataframe schema vocabulary."""

import enum
from typing import Final

#: Canonical trip-table name.
TRIPS_TABLE: Final[str] = "trips"
#: Canonical person-table name.
PERSONS_TABLE: Final[str] = "persons"
#: Canonical household-table name.
HOUSEHOLDS_TABLE: Final[str] = "households"

#: Columns that uniquely identify a trip.
TRIP_KEY_COLUMNS: Final[tuple[str, ...]] = (
    "household_id",
    "person_id",
    "trip_id",
)
#: Columns that uniquely identify a person.
PERSON_KEY_COLUMNS: Final[tuple[str, ...]] = ("household_id", "person_id")
#: Columns that uniquely identify a household.
HOUSEHOLD_KEY_COLUMNS: Final[tuple[str, ...]] = ("household_id",)
#: Domain columns required in every trip table.
TRIP_REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    *TRIP_KEY_COLUMNS,
    "origin",
    "destination",
    "purpose",
    "mode",
)
#: Columns that form the supported timing patterns.
TRIP_TIMING_COLUMNS: Final[tuple[str, ...]] = (
    "departure_second",
    "arrival_second",
    "travel_time_seconds",
    "earliest_departure_second",
    "latest_departure_second",
)
#: Columns reserved by the canonical trip schema.
TRIP_RESERVED_COLUMNS: Final[tuple[str, ...]] = (
    *TRIP_REQUIRED_COLUMNS,
    *TRIP_TIMING_COLUMNS,
    "trip_sequence",
    "timing_pattern",
)
#: Unsupported arrival-window columns rejected by the scheduler.
UNSUPPORTED_ARRIVAL_WINDOW_COLUMNS: Final[tuple[str, ...]] = (
    "earliest_arrival_second",
    "latest_arrival_second",
)
#: Columns containing integer seconds from the diary time origin.
SECOND_COLUMNS: Final[tuple[str, ...]] = (
    "departure_second",
    "arrival_second",
    "travel_time_seconds",
    "earliest_departure_second",
    "latest_departure_second",
    "earliest_arrival_second",
    "latest_arrival_second",
)


class TimingPattern(enum.StrEnum):
    """Supported timing patterns for trip rows.

    Attributes:
        DEPARTURE_ARRIVAL:
            The row supplies concrete departure and arrival seconds.
        DEPARTURE_DURATION:
            The row supplies concrete departure seconds and travel
            duration seconds.
        DEPARTURE_TRAVEL_TIME_FUNCTION:
            The row supplies concrete departure seconds
            and relies on a travel-time callable.
        DEPARTURE_WINDOW_DURATION:
            The row supplies a departure window and travel
            duration seconds.
        DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION:
            The row supplies a departure window
            and relies on a travel-time callable.
    """

    DEPARTURE_ARRIVAL = "departure_arrival"
    DEPARTURE_DURATION = "departure_duration"
    DEPARTURE_TRAVEL_TIME_FUNCTION = "departure_travel_time_function"
    DEPARTURE_WINDOW_DURATION = "departure_window_duration"
    DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION = "departure_window_travel_time_function"
