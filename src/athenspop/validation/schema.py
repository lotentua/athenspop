"""Dataframe schema validation for long-form travel survey input."""

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

import numpy as np
import pandas as pd

from athenspop.validation.report import ValidationReport, ValidationReportBuilder

type TravelTimeFunction = Callable[[str, str, str, int], int]
type ScalarValue = str | int | float | bool | np.integer | np.floating | np.bool_ | None
type IntegerSecondValue = int | np.integer

TRIPS_TABLE: Final[str] = "trips"
PERSONS_TABLE: Final[str] = "persons"
HOUSEHOLDS_TABLE: Final[str] = "households"

TRIP_KEY_COLUMNS: Final[tuple[str, ...]] = ("household_id", "person_id", "trip_id")
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
DEFAULT_MIN_ACTIVITY_DURATION_SECONDS: Final[int] = 1800


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
    DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION = "departure_window_travel_time_function"


@dataclass(frozen=True, slots=True)
class NormalizedTables:
    """Copies of validated boundary tables ready for trusted model construction.

    Attributes:
        trips:
            Trip table copy sorted into validated diary order and annotated with `timing_pattern`.
        persons:
            Optional person table copy after table/key/join validation.
        households:
            Optional household table copy after table/key validation.
    """

    trips: pd.DataFrame
    persons: pd.DataFrame | None = None
    households: pd.DataFrame | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validation output separated from normalized tables so reports stay diagnostic-only.

    Attributes:
        report:
            Validation diagnostics collected from all independent checks.
        normalized_tables:
            Validated table copies when no hard errors were found, otherwise `None`.
    """

    report: ValidationReport
    normalized_tables: NormalizedTables | None


def validate_dataframes(
    trips: pd.DataFrame,
    persons: pd.DataFrame | None = None,
    households: pd.DataFrame | None = None,
    *,
    travel_time_function: TravelTimeFunction | None = None,
) -> ValidationResult:
    """Validate long-form survey input dataframes and return independent diagnostics at once.

    Args:
        trips:
            Required trip table containing identity, movement, and timing columns.
        persons:
            Optional person/respondent table keyed by `household_id` and `person_id`.
        households:
            Optional household table keyed by `household_id`.
        travel_time_function:
            Optional callable used only to classify timing patterns that intentionally omit duration and arrival columns.

    Returns:
        Validation result containing a report and normalized tables when no hard errors exist.

    Notes:
        Validation collects independent schema, key, join, timing, and diary-chain diagnostics without cascading row errors after the first row-blocking failure.
        A result with normalized tables is the boundary after which package internals may trust the model contract.
    """
    builder = ValidationReportBuilder()
    table_is_usable = {
        TRIPS_TABLE: _validate_table_shape(builder, TRIPS_TABLE, trips, required_columns=TRIP_REQUIRED_COLUMNS),
        PERSONS_TABLE: True if persons is None else _validate_table_shape(builder, PERSONS_TABLE, persons, required_columns=PERSON_KEY_COLUMNS),
        HOUSEHOLDS_TABLE: True
        if households is None
        else _validate_table_shape(
            builder,
            HOUSEHOLDS_TABLE,
            households,
            required_columns=HOUSEHOLD_KEY_COLUMNS,
        ),
    }
    if not table_is_usable[TRIPS_TABLE]:
        report = builder.build()
        return ValidationResult(report=report, normalized_tables=None)
    normalized_trips = trips.copy()
    normalized_persons = None if persons is None else persons.copy()
    normalized_households = None if households is None else households.copy()
    _validate_keys(builder, normalized_trips, table=TRIPS_TABLE, key_columns=TRIP_KEY_COLUMNS)
    if normalized_persons is not None and table_is_usable[PERSONS_TABLE]:
        _validate_keys(
            builder,
            normalized_persons,
            table=PERSONS_TABLE,
            key_columns=PERSON_KEY_COLUMNS,
        )
    if normalized_households is not None and table_is_usable[HOUSEHOLDS_TABLE]:
        _validate_keys(
            builder,
            normalized_households,
            table=HOUSEHOLDS_TABLE,
            key_columns=HOUSEHOLD_KEY_COLUMNS,
        )
    _validate_joins(
        builder,
        normalized_trips,
        normalized_persons if table_is_usable[PERSONS_TABLE] else None,
        normalized_households if table_is_usable[HOUSEHOLDS_TABLE] else None,
    )
    _validate_metadata_values(builder, normalized_trips, table=TRIPS_TABLE, reserved_columns=TRIP_RESERVED_COLUMNS)
    if normalized_persons is not None and table_is_usable[PERSONS_TABLE]:
        _validate_metadata_values(builder, normalized_persons, table=PERSONS_TABLE, reserved_columns=PERSON_KEY_COLUMNS)
    if normalized_households is not None and table_is_usable[HOUSEHOLDS_TABLE]:
        _validate_metadata_values(builder, normalized_households, table=HOUSEHOLDS_TABLE, reserved_columns=HOUSEHOLD_KEY_COLUMNS)
    timing_patterns = _validate_trip_rows(builder, normalized_trips, travel_time_function=travel_time_function)
    if timing_patterns is not None:
        normalized_trips["timing_pattern"] = timing_patterns
    ordered_trip_rows = _validate_trip_chains(builder, normalized_trips)
    report = builder.build()
    if report.has_errors:
        return ValidationResult(report=report, normalized_tables=None)
    normalized_trips = normalized_trips.loc[ordered_trip_rows].copy()
    return ValidationResult(
        report=report,
        normalized_tables=NormalizedTables(
            trips=normalized_trips,
            persons=normalized_persons,
            households=normalized_households,
        ),
    )


def _validate_table_shape(
    builder: ValidationReportBuilder,
    table: str,
    frame: pd.DataFrame,
    *,
    required_columns: tuple[str, ...],
) -> bool:
    """Validate table type, duplicate columns, and required columns before row-level checks."""
    if not isinstance(frame, pd.DataFrame):
        builder.add_error(
            code="table_not_dataframe",
            table=table,
            message=f"`{table}` must be a pandas DataFrame.",
        )
        return False
    duplicated_columns = [str(column) for column in frame.columns[frame.columns.duplicated()].tolist()]
    if duplicated_columns:
        builder.add_error(
            code="duplicate_columns",
            table=table,
            message=f"`{table}` has duplicate column names: {', '.join(duplicated_columns)}.",
        )
        return False
    missing_columns = [column for column in required_columns if column not in frame.columns]
    if missing_columns:
        builder.add_error(
            code="missing_required_columns",
            table=table,
            message=f"`{table}` is missing required column(s): {', '.join(missing_columns)}.",
        )
        return False
    return True


def _validate_keys(
    builder: ValidationReportBuilder,
    frame: pd.DataFrame,
    *,
    table: str,
    key_columns: tuple[str, ...],
) -> None:
    """Validate missing and duplicate table keys while blocking rows that lack identity."""
    for row_index, row in frame.iterrows():
        row_identifier = _row_identifier(table, row_index)
        for column in key_columns:
            value = cast("ScalarValue", row[column])
            if _is_missing(value):
                builder.add_error(
                    code="null_key",
                    table=table,
                    row_identifier=row_identifier,
                    column=column,
                    bad_value=_format_value(value),
                    message=f"`{table}` row {row_identifier} has a missing `{column}` key. Fill the key before validation.",
                )
                break
    rows_for_duplicate_check = [index for index in frame.index if _row_identifier(table, index) not in builder.blocked_rows]
    if rows_for_duplicate_check:
        valid_key_frame = frame.loc[rows_for_duplicate_check, list(key_columns)]
        duplicate_mask = valid_key_frame.duplicated(keep=False)
        for row_index in valid_key_frame.index[duplicate_mask]:
            row_identifier = _row_identifier(table, row_index)
            builder.add_error(
                code="duplicate_key",
                table=table,
                row_identifier=row_identifier,
                column=", ".join(key_columns),
                message=f"`{table}` row {row_identifier} duplicates the table identity `{', '.join(key_columns)}`. Each identity must appear once.",
            )


def _validate_joins(
    builder: ValidationReportBuilder,
    trips: pd.DataFrame,
    persons: pd.DataFrame | None,
    households: pd.DataFrame | None,
) -> None:
    """Validate optional-table joins without suppressing unrelated trip-row domain checks."""
    trip_rows = [index for index in trips.index if _row_identifier(TRIPS_TABLE, index) not in builder.blocked_rows]
    if persons is not None:
        valid_person_keys = {_key_tuple(row, PERSON_KEY_COLUMNS) for _, row in persons.iterrows()}
        for row_index in trip_rows:
            row = trips.loc[row_index]
            if _key_tuple(row, PERSON_KEY_COLUMNS) not in valid_person_keys:
                builder.add_error(
                    code="orphan_trip_person",
                    table=TRIPS_TABLE,
                    row_identifier=_row_identifier(TRIPS_TABLE, row_index),
                    column=", ".join(PERSON_KEY_COLUMNS),
                    message=f"`trips` row {_row_identifier(TRIPS_TABLE, row_index)} references a person that is not present in `persons`.",
                    suppress_row=False,
                )
    if households is not None:
        valid_household_keys = {_key_tuple(row, HOUSEHOLD_KEY_COLUMNS) for _, row in households.iterrows()}
        for row_index in trip_rows:
            row = trips.loc[row_index]
            if _key_tuple(row, HOUSEHOLD_KEY_COLUMNS) not in valid_household_keys:
                builder.add_error(
                    code="orphan_trip_household",
                    table=TRIPS_TABLE,
                    row_identifier=_row_identifier(TRIPS_TABLE, row_index),
                    column=", ".join(HOUSEHOLD_KEY_COLUMNS),
                    message=f"`trips` row {_row_identifier(TRIPS_TABLE, row_index)} references a household that is not present in `households`.",
                    suppress_row=False,
                )
        if persons is not None:
            person_rows = [index for index in persons.index if _row_identifier(PERSONS_TABLE, index) not in builder.blocked_rows]
            for row_index in person_rows:
                row = persons.loc[row_index]
                if _key_tuple(row, HOUSEHOLD_KEY_COLUMNS) not in valid_household_keys:
                    builder.add_error(
                        code="orphan_person_household",
                        table=PERSONS_TABLE,
                        row_identifier=_row_identifier(PERSONS_TABLE, row_index),
                        column=", ".join(HOUSEHOLD_KEY_COLUMNS),
                        message=f"`persons` row {_row_identifier(PERSONS_TABLE, row_index)} references a household that is not present in `households`.",
                        suppress_row=False,
                    )


def _validate_metadata_values(
    builder: ValidationReportBuilder,
    frame: pd.DataFrame,
    *,
    table: str,
    reserved_columns: tuple[str, ...],
) -> None:
    """Validate user metadata columns before trusted model construction preserves them."""
    metadata_columns = [column for column in frame.columns if str(column) not in reserved_columns]
    for row_index, row in frame.iterrows():
        row_identifier = _row_identifier(table, row_index)
        if row_identifier in builder.blocked_rows:
            continue
        for column in metadata_columns:
            if not pd.api.types.is_scalar(row[column]):
                builder.add_error(
                    code="unsupported_metadata_value",
                    table=table,
                    row_identifier=row_identifier,
                    column=str(column),
                    bad_value=repr(row[column]),
                    message=f"`{table}` row {row_identifier} has non-scalar metadata in `{column}`. Extra metadata columns must contain simple scalar values.",
                )
                break
            value = cast("ScalarValue", row[column])
            if _is_missing(value):
                continue
            if not isinstance(value, str | int | float | bool | np.integer | np.floating | np.bool_):
                builder.add_error(
                    code="unsupported_metadata_value",
                    table=table,
                    row_identifier=row_identifier,
                    column=str(column),
                    bad_value=repr(row[column]),
                    message=f"`{table}` row {row_identifier} has unsupported metadata in `{column}`. Extra metadata columns must contain strings, numbers, booleans, or missing values.",
                )
                break


def _validate_trip_rows(
    builder: ValidationReportBuilder,
    trips: pd.DataFrame,
    *,
    travel_time_function: TravelTimeFunction | None,
) -> pd.Series | None:
    """Validate per-trip domain fields and classify exactly one supported timing pattern per usable row."""
    patterns: dict[Hashable, str] = {}
    for row_index, row in trips.iterrows():
        row_identifier = _row_identifier(TRIPS_TABLE, row_index)
        if row_identifier in builder.blocked_rows:
            continue
        for column in ("origin", "destination", "purpose", "mode"):
            value = cast("ScalarValue", row[column])
            if _is_missing(value) or str(value) == "":
                builder.add_error(
                    code="missing_trip_value",
                    table=TRIPS_TABLE,
                    row_identifier=row_identifier,
                    column=column,
                    bad_value=_format_value(value),
                    message=f"`trips` row {row_identifier} is missing `{column}`. Fill the movement and behavior columns before loading.",
                )
                break
        if row_identifier in builder.blocked_rows:
            continue
        if _has_any_value(row, UNSUPPORTED_ARRIVAL_WINDOW_COLUMNS):
            builder.add_error(
                code="unsupported_arrival_window",
                table=TRIPS_TABLE,
                row_identifier=row_identifier,
                column=", ".join(UNSUPPORTED_ARRIVAL_WINDOW_COLUMNS),
                message=f"`trips` row {row_identifier} uses an arrival-time range. Provide concrete arrival time, fixed travel time, or a departure window plus travel time.",
            )
            continue
        for column in SECOND_COLUMNS:
            if column in trips.columns:
                value = cast("ScalarValue", row[column])
                second_value = _integer_second_value(value)
                if not _is_missing(value) and second_value is None:
                    builder.add_error(
                        code="invalid_second",
                        table=TRIPS_TABLE,
                        row_identifier=row_identifier,
                        column=column,
                        bad_value=_format_value(value),
                        message=f"`trips` row {row_identifier} has `{column}`={_format_value(value)}. Time values must be integer seconds from the diary time origin.",
                    )
                    break
                if second_value is not None and int(second_value) < 0:
                    builder.add_error(
                        code="negative_second",
                        table=TRIPS_TABLE,
                        row_identifier=row_identifier,
                        column=column,
                        bad_value=_format_value(value),
                        message=f"`trips` row {row_identifier} has `{column}`={_format_value(value)}. Time values must be non-negative integer seconds.",
                    )
                    break
        if row_identifier in builder.blocked_rows:
            continue
        pattern = _detect_timing_pattern(row, travel_time_function=travel_time_function)
        if pattern is None:
            builder.add_error(
                code="invalid_timing_pattern",
                table=TRIPS_TABLE,
                row_identifier=row_identifier,
                column=", ".join(TRIP_TIMING_COLUMNS),
                message=f"`trips` row {row_identifier} must match exactly one supported timing pattern.",
            )
            continue
        pattern_error = _validate_timing_semantics(row, pattern)
        if pattern_error is not None:
            code, column, message = pattern_error
            builder.add_error(
                code=code,
                table=TRIPS_TABLE,
                row_identifier=row_identifier,
                column=column,
                message=f"`trips` row {row_identifier} {message}",
            )
            continue
        patterns[row_index] = pattern.value
    if not patterns and len(trips.index) > 0:
        return None
    return pd.Series(patterns, name="timing_pattern", dtype="string")


def _validate_trip_chains(
    builder: ValidationReportBuilder,
    trips: pd.DataFrame,
) -> list[Hashable]:
    """Validate diary ordering and chain-level warnings, returning row labels in trusted diary order."""
    valid_trip_rows = [index for index in trips.index if _row_identifier(TRIPS_TABLE, index) not in builder.blocked_rows]
    if not valid_trip_rows:
        return []
    sortable = trips.loc[valid_trip_rows].copy()
    sortable["_input_order"] = range(len(sortable))
    ordered_rows: list[Hashable] = []
    for (household_id, person_id), group in sortable.groupby(["household_id", "person_id"], sort=False):
        chain_identifier = f"household_id={household_id}; person_id={person_id}"
        order_column = _resolve_trip_order_column(builder, group, chain_identifier)
        if order_column is None:
            continue
        ordered_group = group.sort_values([order_column, "_input_order"], kind="mergesort")
        ordered_rows.extend(ordered_group.index.to_list())
        previous_destination: str | None = None
        previous_arrival: int | None = None
        for row_index, row in ordered_group.iterrows():
            origin = str(row["origin"])
            if previous_destination is not None and origin != previous_destination:
                builder.add_warning(
                    code="origin_mismatch",
                    table=TRIPS_TABLE,
                    row_identifier=_row_identifier(TRIPS_TABLE, row_index),
                    column="origin",
                    message=f"`trips` row {_row_identifier(TRIPS_TABLE, row_index)} starts at `{origin}`, but the previous trip in {chain_identifier} ended at `{previous_destination}`.",
                )
            departure_second = _optional_int(row, "departure_second")
            arrival_second = _optional_int(row, "arrival_second")
            travel_time_seconds = _optional_int(row, "travel_time_seconds")
            computed_arrival = (
                arrival_second
                if arrival_second is not None
                else None
                if departure_second is None or travel_time_seconds is None
                else departure_second + travel_time_seconds
            )
            if previous_arrival is not None and departure_second is not None and departure_second < previous_arrival:
                builder.add_error(
                    code="overlapping_trips",
                    table=TRIPS_TABLE,
                    row_identifier=_row_identifier(TRIPS_TABLE, row_index),
                    column="departure_second",
                    message=f"`trips` row {_row_identifier(TRIPS_TABLE, row_index)} departs before the previous trip in {chain_identifier} has arrived.",
                )
                builder.mark_chain_invalid(chain_identifier)
                break
            if previous_arrival is not None and departure_second is not None and departure_second - previous_arrival < DEFAULT_MIN_ACTIVITY_DURATION_SECONDS:
                builder.add_warning(
                    code="short_activity_duration",
                    table=TRIPS_TABLE,
                    row_identifier=_row_identifier(TRIPS_TABLE, row_index),
                    column="departure_second",
                    message=f"`trips` row {_row_identifier(TRIPS_TABLE, row_index)} leaves {departure_second - previous_arrival} second(s) after the previous arrival in {chain_identifier}. The default scheduler uses a {DEFAULT_MIN_ACTIVITY_DURATION_SECONDS}-second minimum activity duration.",
                )
            previous_destination = str(row["destination"])
            previous_arrival = computed_arrival
    return ordered_rows


def _resolve_trip_order_column(builder: ValidationReportBuilder, group: pd.DataFrame, chain_identifier: str) -> str | None:
    """Choose explicit `trip_sequence` ordering or concrete departure ordering for one diary chain."""
    if "trip_sequence" in group.columns:
        return _resolve_trip_sequence_order(builder, group, chain_identifier)
    return _resolve_concrete_departure_order(builder, group, chain_identifier)


def _resolve_trip_sequence_order(builder: ValidationReportBuilder, group: pd.DataFrame, chain_identifier: str) -> str | None:
    """Validate explicit non-negative unique trip sequence values for one diary chain."""
    seen_sequences: dict[int, Hashable] = {}
    for row_index, row in group.iterrows():
        row_identifier = _row_identifier(TRIPS_TABLE, row_index)
        value = cast("ScalarValue", row["trip_sequence"])
        sequence = _integer_second_value(value)
        if _is_missing(value):
            builder.add_error(
                code="missing_trip_sequence",
                table=TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                bad_value=_format_value(value),
                message=f"`trips` row {row_identifier} is missing `trip_sequence`. Fill `trip_sequence` for every trip in {chain_identifier}, or omit the column only when order is uniquely inferable from concrete departure seconds.",
            )
            builder.mark_chain_invalid(chain_identifier)
            return None
        if sequence is None or int(sequence) < 0:
            builder.add_error(
                code="invalid_trip_sequence",
                table=TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                bad_value=_format_value(value),
                message=f"`trips` row {row_identifier} has invalid `trip_sequence`={_format_value(value)}. Use non-negative integer sequence values within each diary chain.",
            )
            builder.mark_chain_invalid(chain_identifier)
            return None
        sequence_int = int(sequence)
        if sequence_int in seen_sequences:
            builder.add_error(
                code="duplicate_trip_sequence",
                table=TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                bad_value=_format_value(value),
                message=f"`trips` row {row_identifier} duplicates `trip_sequence`={sequence_int} in {chain_identifier}. Each trip sequence value must be unique within a diary chain.",
            )
            builder.mark_chain_invalid(chain_identifier)
            return None
        seen_sequences[sequence_int] = row_index
    return "trip_sequence"


def _resolve_concrete_departure_order(builder: ValidationReportBuilder, group: pd.DataFrame, chain_identifier: str) -> str | None:
    """Use concrete departures as diary order only when they are present and unique within the chain."""
    seen_departures: dict[int, Hashable] = {}
    for row_index, row in group.iterrows():
        row_identifier = _row_identifier(TRIPS_TABLE, row_index)
        departure_second = _optional_int(row, "departure_second")
        if departure_second is None:
            builder.add_error(
                code="unresolved_trip_order",
                table=TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                message=f"`trips` row {row_identifier} has no concrete `departure_second`, so order is not uniquely inferable for {chain_identifier}. Add a non-negative integer `trip_sequence` column for the whole diary chain.",
            )
            builder.mark_chain_invalid(chain_identifier)
            return None
        if departure_second in seen_departures:
            builder.add_error(
                code="unresolved_trip_order",
                table=TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                bad_value=str(departure_second),
                message=f"`trips` row {row_identifier} has departure_second={departure_second}, which is duplicated in {chain_identifier}. Add `trip_sequence` so the diary order is explicit.",
            )
            builder.mark_chain_invalid(chain_identifier)
            return None
        seen_departures[departure_second] = row_index
    return "departure_second"


def _detect_timing_pattern(row: pd.Series, *, travel_time_function: TravelTimeFunction | None) -> TimingPattern | None:
    """Detect the single supported timing pattern represented by one row's populated timing columns."""
    has_departure = _has_value(row, "departure_second")
    has_arrival = _has_value(row, "arrival_second")
    has_travel_time = _has_value(row, "travel_time_seconds")
    has_earliest = _has_value(row, "earliest_departure_second")
    has_latest = _has_value(row, "latest_departure_second")
    candidates: list[TimingPattern] = []
    if has_departure and has_arrival and not has_travel_time and not has_earliest and not has_latest:
        candidates.append(TimingPattern.DEPARTURE_ARRIVAL)
    if has_departure and has_travel_time and not has_arrival and not has_earliest and not has_latest:
        candidates.append(TimingPattern.DEPARTURE_DURATION)
    if has_departure and travel_time_function is not None and not has_arrival and not has_travel_time and not has_earliest and not has_latest:
        candidates.append(TimingPattern.DEPARTURE_TRAVEL_TIME_FUNCTION)
    if has_earliest and has_latest and has_travel_time and not has_departure and not has_arrival:
        candidates.append(TimingPattern.DEPARTURE_WINDOW_DURATION)
    if has_earliest and has_latest and travel_time_function is not None and not has_departure and not has_arrival and not has_travel_time:
        candidates.append(TimingPattern.DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION)
    return candidates[0] if len(candidates) == 1 else None


def _validate_timing_semantics(row: pd.Series, pattern: TimingPattern) -> tuple[str, str, str] | None:
    """Validate timing inequalities that depend on the detected timing pattern."""
    if pattern == TimingPattern.DEPARTURE_ARRIVAL:
        departure_second = _required_int(row, "departure_second")
        arrival_second = _required_int(row, "arrival_second")
        if arrival_second <= departure_second:
            return (
                "non_positive_travel_duration",
                "arrival_second",
                f"arrives at {arrival_second}, which must be after departure_second={departure_second}.",
            )
    if pattern == TimingPattern.DEPARTURE_DURATION:
        travel_time_seconds = _required_int(row, "travel_time_seconds")
        if travel_time_seconds <= 0:
            return (
                "non_positive_travel_duration",
                "travel_time_seconds",
                f"has travel_time_seconds={travel_time_seconds}. Movement travel time must be strictly positive.",
            )
    if pattern == TimingPattern.DEPARTURE_WINDOW_DURATION:
        earliest = _required_int(row, "earliest_departure_second")
        latest = _required_int(row, "latest_departure_second")
        travel_time_seconds = _required_int(row, "travel_time_seconds")
        if latest < earliest:
            return (
                "invalid_departure_window",
                "latest_departure_second",
                f"has latest_departure_second={latest} before earliest_departure_second={earliest}.",
            )
        if travel_time_seconds <= 0:
            return (
                "non_positive_travel_duration",
                "travel_time_seconds",
                f"has travel_time_seconds={travel_time_seconds}. Movement travel time must be strictly positive.",
            )
    if pattern == TimingPattern.DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION:
        earliest = _required_int(row, "earliest_departure_second")
        latest = _required_int(row, "latest_departure_second")
        if latest < earliest:
            return (
                "invalid_departure_window",
                "latest_departure_second",
                f"has latest_departure_second={latest} before earliest_departure_second={earliest}.",
            )
    return None


def _row_identifier(table: str, row_index: Hashable) -> str:
    """Format a stable row identifier for diagnostics."""
    return f"{table}[{row_index}]"


def _key_tuple(row: pd.Series, columns: tuple[str, ...]) -> tuple[str, ...]:
    """Return normalized string key values for a validated row."""
    return tuple(str(row[column]) for column in columns)


def _is_missing(value: ScalarValue) -> bool:
    """Return whether a scalar input value should be treated as missing."""
    return bool(pd.isna(value))


def _has_value(row: pd.Series, column: str) -> bool:
    """Return whether a row contains a non-missing value in a column."""
    if column not in row.index:
        return False
    return not _is_missing(cast("ScalarValue", row[column]))


def _has_any_value(row: pd.Series, columns: tuple[str, ...]) -> bool:
    """Return whether any listed column has a non-missing value."""
    return any(_has_value(row, column) for column in columns)


def _format_value(value: ScalarValue) -> str:
    """Format a scalar value for a concise validation diagnostic."""
    return "<NA>" if _is_missing(value) else repr(value)


def _integer_second_value(value: ScalarValue) -> IntegerSecondValue | None:
    """Narrow a scalar value to an integer-second value without accepting booleans or floats."""
    if isinstance(value, bool | np.bool_):
        return None
    if isinstance(value, int | np.integer):
        return value
    return None


def _required_int(row: pd.Series, column: str) -> int:
    """Read a required integer-second value after validation has already narrowed the row."""
    value = _integer_second_value(cast("ScalarValue", row[column]))
    if value is None:
        raise RuntimeError(f"`{column}` was not narrowed to an integer second before model construction.")
    return int(value)


def _optional_int(row: pd.Series, column: str) -> int | None:
    """Read an optional integer-second value after validation has already narrowed the row."""
    if column not in row.index or _is_missing(cast("ScalarValue", row[column])):
        return None
    value = _integer_second_value(cast("ScalarValue", row[column]))
    if value is None:
        raise RuntimeError(f"`{column}` was not narrowed to an integer second before model construction.")
    return int(value)
