# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Define the stable vocabulary shared by structured diagnostics."""

import enum


class IssueSeverity(enum.StrEnum):
    """Severity levels for structured diagnostics.

    Attributes:
        ERROR:
            The condition prevents a valid result.
        WARNING:
            The condition preserves a result but may affect interpretation.
    """

    ERROR = "error"
    WARNING = "warning"


class IssueCode(enum.StrEnum):
    """Machine-readable codes emitted by validation and scheduling.

    Attributes:
        ACTIVITY_DURATION_TOO_SHORT:
            Consecutive trips leave less than the required activity duration.
        ARRIVAL_AFTER_OBSERVATION_WINDOW:
            A realized arrival exceeds the configured observation window.
        BLANK_KEY:
            A string key contains no non-whitespace characters.
        DEPARTURE_AFTER_OBSERVATION_WINDOW:
            A departure exceeds the configured observation window.
        DUPLICATE_COLUMNS:
            A dataframe contains duplicate column labels.
        DUPLICATE_INDEX:
            A dataframe index does not identify rows uniquely.
        DUPLICATE_KEY:
            Multiple rows share the same table key.
        DUPLICATE_TRIP_SEQUENCE:
            Multiple trips in one diary share a sequence position.
        INFEASIBLE_DEPARTURE_WINDOW:
            Applied constraints leave no feasible departure time.
        INFEASIBLE_FUTURE_DEPARTURE:
            A departure violates a bound implied by later trips.
        INVALID_DEPARTURE_WINDOW:
            A departure window ends before it begins.
        INVALID_SECOND:
            A timing value is not an integer second.
        INVALID_TIMING_PATTERN:
            A trip row does not match a supported timing pattern.
        INVALID_TRAVEL_TIME_FUNCTION_RESULT:
            A travel-time callable returned an invalid duration.
        INVALID_TRIP_SEQUENCE:
            A trip sequence value is not a non-negative integer.
        MISSING_DEPARTURE:
            A trip supplies neither a departure nor a departure window.
        MISSING_REQUIRED_COLUMNS:
            A dataframe omits one or more required columns.
        MISSING_TRAVEL_TIME_FUNCTION:
            Scheduling needs a travel-time callable but none is available.
        MISSING_TRIP_SEQUENCE:
            A trip lacks a sequence position when explicit sequence ordering is used.
        MISSING_TRIP_VALUE:
            A required trip value is missing.
        NEGATIVE_SECOND:
            A timing value is earlier than the time origin.
        NON_POSITIVE_TRAVEL_DURATION:
            A movement trip has zero or negative duration.
        NORMALIZED_COLUMN_COLLISION:
            Distinct column labels collide after string normalization.
        NULL_KEY:
            A table key contains a missing value.
        ORIGIN_MISMATCH:
            A trip origin differs from the preceding destination.
        ORPHAN_PERSON_HOUSEHOLD:
            A person refers to a household that is not present.
        ORPHAN_TRIP_HOUSEHOLD:
            A trip refers to a household that is not present.
        ORPHAN_TRIP_PERSON:
            A trip refers to a person that is not present.
        OVERLAPPING_TRIPS:
            A trip departs before the preceding trip arrives.
        TABLE_NOT_DATAFRAME:
            An input table is not a pandas dataframe.
        TRAVEL_TIME_FUNCTION_ERROR:
            A travel-time callable raised an exception.
        UNRESOLVED_TRIP_ORDER:
            Available timing fields do not establish diary order.
        UNSUPPORTED_ARRIVAL_WINDOW:
            A trip supplies a non-missing arrival-window value.
        UNSUPPORTED_KEY_VALUE:
            A table key contains a non-scalar value.
        UNSUPPORTED_METADATA_VALUE:
            Metadata cannot be represented by the model contract.
        UNSUPPORTED_TRIP_VALUE:
            A required trip field contains a non-scalar value.
    """

    ACTIVITY_DURATION_TOO_SHORT = "activity_duration_too_short"
    ARRIVAL_AFTER_OBSERVATION_WINDOW = "arrival_after_observation_window"
    BLANK_KEY = "blank_key"
    DEPARTURE_AFTER_OBSERVATION_WINDOW = "departure_after_observation_window"
    DUPLICATE_COLUMNS = "duplicate_columns"
    DUPLICATE_INDEX = "duplicate_index"
    DUPLICATE_KEY = "duplicate_key"
    DUPLICATE_TRIP_SEQUENCE = "duplicate_trip_sequence"
    INFEASIBLE_DEPARTURE_WINDOW = "infeasible_departure_window"
    INFEASIBLE_FUTURE_DEPARTURE = "infeasible_future_departure"
    INVALID_DEPARTURE_WINDOW = "invalid_departure_window"
    INVALID_SECOND = "invalid_second"
    INVALID_TIMING_PATTERN = "invalid_timing_pattern"
    INVALID_TRAVEL_TIME_FUNCTION_RESULT = "invalid_travel_time_function_result"
    INVALID_TRIP_SEQUENCE = "invalid_trip_sequence"
    MISSING_DEPARTURE = "missing_departure"
    MISSING_REQUIRED_COLUMNS = "missing_required_columns"
    MISSING_TRAVEL_TIME_FUNCTION = "missing_travel_time_function"
    MISSING_TRIP_SEQUENCE = "missing_trip_sequence"
    MISSING_TRIP_VALUE = "missing_trip_value"
    NEGATIVE_SECOND = "negative_second"
    NON_POSITIVE_TRAVEL_DURATION = "non_positive_travel_duration"
    NORMALIZED_COLUMN_COLLISION = "normalized_column_collision"
    NULL_KEY = "null_key"
    ORIGIN_MISMATCH = "origin_mismatch"
    ORPHAN_PERSON_HOUSEHOLD = "orphan_person_household"
    ORPHAN_TRIP_HOUSEHOLD = "orphan_trip_household"
    ORPHAN_TRIP_PERSON = "orphan_trip_person"
    OVERLAPPING_TRIPS = "overlapping_trips"
    TABLE_NOT_DATAFRAME = "table_not_dataframe"
    TRAVEL_TIME_FUNCTION_ERROR = "travel_time_function_error"
    UNRESOLVED_TRIP_ORDER = "unresolved_trip_order"
    UNSUPPORTED_ARRIVAL_WINDOW = "unsupported_arrival_window"
    UNSUPPORTED_KEY_VALUE = "unsupported_key_value"
    UNSUPPORTED_METADATA_VALUE = "unsupported_metadata_value"
    UNSUPPORTED_TRIP_VALUE = "unsupported_trip_value"
