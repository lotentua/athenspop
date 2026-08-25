# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module defines the canonical dataframe schema vocabulary."""

import enum
import typing

#: This value is the canonical trip-table name.
TRIPS_TABLE: typing.Final[str] = "trips"
#: This value is the canonical person-table name.
PERSONS_TABLE: typing.Final[str] = "persons"
#: This value is the canonical household-table name.
HOUSEHOLDS_TABLE: typing.Final[str] = "households"

#: These columns uniquely identify a trip.
TRIP_KEY_COLUMNS: typing.Final[tuple[str, ...]] = (
    "household_id",
    "person_id",
    "trip_id",
)
#: These columns uniquely identify a person.
PERSON_KEY_COLUMNS: typing.Final[tuple[str, ...]] = ("household_id", "person_id")
#: These columns uniquely identify a household.
HOUSEHOLD_KEY_COLUMNS: typing.Final[tuple[str, ...]] = ("household_id",)
#: These domain columns are required in every trip table.
TRIP_REQUIRED_COLUMNS: typing.Final[tuple[str, ...]] = (
    *TRIP_KEY_COLUMNS,
    "origin",
    "destination",
    "purpose",
    "mode",
)
#: These columns form the supported timing patterns.
TRIP_TIMING_COLUMNS: typing.Final[tuple[str, ...]] = (
    "departure_second",
    "arrival_second",
    "travel_time_seconds",
    "earliest_departure_second",
    "latest_departure_second",
)
#: These columns are reserved by the canonical trip schema.
TRIP_RESERVED_COLUMNS: typing.Final[tuple[str, ...]] = (
    *TRIP_REQUIRED_COLUMNS,
    *TRIP_TIMING_COLUMNS,
    "trip_sequence",
    "timing_pattern",
)
#: These arrival-window columns are rejected because the scheduler does not
#: support them.
UNSUPPORTED_ARRIVAL_WINDOW_COLUMNS: typing.Final[tuple[str, ...]] = (
    "earliest_arrival_second",
    "latest_arrival_second",
)
#: These columns represent integer seconds from the diary time origin.
SECOND_COLUMNS: typing.Final[tuple[str, ...]] = (
    "departure_second",
    "arrival_second",
    "travel_time_seconds",
    "earliest_departure_second",
    "latest_departure_second",
    "earliest_arrival_second",
    "latest_arrival_second",
)


class TimingPattern(enum.StrEnum):
    """This enumeration defines the supported timing patterns for trip rows.

    Attributes:
        DEPARTURE_ARRIVAL: The row supplies concrete departure and arrival seconds.
        DEPARTURE_DURATION: The row supplies concrete departure seconds and travel
            duration seconds.
        DEPARTURE_TRAVEL_TIME_FUNCTION: The row supplies concrete departure seconds
            and relies on a travel-time callable.
        DEPARTURE_WINDOW_DURATION: The row supplies a departure window and travel
            duration seconds.
        DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION: The row supplies a departure window
            and relies on a travel-time callable.
    """

    DEPARTURE_ARRIVAL = "departure_arrival"
    DEPARTURE_DURATION = "departure_duration"
    DEPARTURE_TRAVEL_TIME_FUNCTION = "departure_travel_time_function"
    DEPARTURE_WINDOW_DURATION = "departure_window_duration"
    DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION = "departure_window_travel_time_function"
