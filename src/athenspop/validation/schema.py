# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module validates dataframe schemas for long-form survey input."""

import dataclasses
import types
from collections.abc import Hashable, Mapping
from typing import Final, cast

import numpy as np
import pandas as pd

import athenspop.schema
import athenspop.validation.report

#: This type represents scalar values accepted at the dataframe boundary.
type ScalarValue = str | int | float | bool | np.integer | np.floating | np.bool_ | None
#: This type represents integer scalars accepted for second-valued fields.
type IntegerSecondValue = int | np.integer

#: This mapping resolves timing patterns from the presence of five timing fields.
_TIMING_PATTERN_BY_PRESENCE: Final[
    Mapping[tuple[bool, bool, bool, bool, bool], athenspop.schema.TimingPattern]
] = types.MappingProxyType(
    {
        (
            True,
            True,
            False,
            False,
            False,
        ): athenspop.schema.TimingPattern.DEPARTURE_ARRIVAL,
        (
            True,
            False,
            True,
            False,
            False,
        ): athenspop.schema.TimingPattern.DEPARTURE_DURATION,
        (
            True,
            False,
            False,
            False,
            False,
        ): athenspop.schema.TimingPattern.DEPARTURE_TRAVEL_TIME_FUNCTION,
        (
            False,
            False,
            True,
            True,
            True,
        ): athenspop.schema.TimingPattern.DEPARTURE_WINDOW_DURATION,
        (
            False,
            False,
            False,
            True,
            True,
        ): athenspop.schema.TimingPattern.DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION,
    }
)


@dataclasses.dataclass(frozen=True, slots=True)
class NormalizedTables:
    """This class contains validated tables for trusted model construction.

    Attributes:
        trips: This trip table copy is sorted into validated diary order and annotated
            with `timing_pattern`.
        persons: This optional person table copy has passed table, key, and join
            validation.
        households: This optional household table copy has passed table and key
            validation.
    """

    trips: pd.DataFrame
    persons: pd.DataFrame | None = None
    households: pd.DataFrame | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class ValidationResult:
    """This class pairs validation diagnostics with normalized tables.

    Attributes:
        report: These validation diagnostics come from all independent checks.
        normalized_tables: This value contains validated table copies when no hard
            errors were found, or it is `None` otherwise.
    """

    report: athenspop.validation.report.ValidationReport
    normalized_tables: NormalizedTables | None


def validate_dataframes(
    trips: pd.DataFrame,
    persons: pd.DataFrame | None = None,
    households: pd.DataFrame | None = None,
) -> ValidationResult:
    """Validate long-form survey dataframes and collect independent diagnostics.

    Args:
        trips: This required trip table contains identity, movement, and timing
            columns.
        persons: This optional person or respondent table is keyed by `household_id`
            and `person_id`.
        households: This optional household table is keyed by `household_id`.

    Returns:
        The function returns a validation result containing a report and normalized
        tables when no hard errors exist.

    Notes:
        The function collects independent schema, key, join, timing, and diary-chain
        diagnostics without cascading row errors after the first row-blocking
        failure.
        A result with normalized tables is the boundary after which downstream code
        may trust the model contract.
    """
    builder = athenspop.validation.report.ValidationReportBuilder()
    table_is_usable = {
        athenspop.schema.TRIPS_TABLE: _validate_table_shape(
            builder,
            athenspop.schema.TRIPS_TABLE,
            trips,
            required_columns=athenspop.schema.TRIP_REQUIRED_COLUMNS,
        ),
        athenspop.schema.PERSONS_TABLE: True
        if persons is None
        else _validate_table_shape(
            builder,
            athenspop.schema.PERSONS_TABLE,
            persons,
            required_columns=athenspop.schema.PERSON_KEY_COLUMNS,
        ),
        athenspop.schema.HOUSEHOLDS_TABLE: True
        if households is None
        else _validate_table_shape(
            builder,
            athenspop.schema.HOUSEHOLDS_TABLE,
            households,
            required_columns=athenspop.schema.HOUSEHOLD_KEY_COLUMNS,
        ),
    }
    if not table_is_usable[athenspop.schema.TRIPS_TABLE]:
        validation_report = builder.build()
        return ValidationResult(report=validation_report, normalized_tables=None)
    normalized_trips = trips.copy()
    normalized_persons = (
        persons.copy()
        if persons is not None and table_is_usable[athenspop.schema.PERSONS_TABLE]
        else None
    )
    normalized_households = (
        households.copy()
        if households is not None and table_is_usable[athenspop.schema.HOUSEHOLDS_TABLE]
        else None
    )
    _validate_keys(
        builder,
        normalized_trips,
        table=athenspop.schema.TRIPS_TABLE,
        key_columns=athenspop.schema.TRIP_KEY_COLUMNS,
    )
    if (
        normalized_persons is not None
        and table_is_usable[athenspop.schema.PERSONS_TABLE]
    ):
        _validate_keys(
            builder,
            normalized_persons,
            table=athenspop.schema.PERSONS_TABLE,
            key_columns=athenspop.schema.PERSON_KEY_COLUMNS,
        )
    if (
        normalized_households is not None
        and table_is_usable[athenspop.schema.HOUSEHOLDS_TABLE]
    ):
        _validate_keys(
            builder,
            normalized_households,
            table=athenspop.schema.HOUSEHOLDS_TABLE,
            key_columns=athenspop.schema.HOUSEHOLD_KEY_COLUMNS,
        )
    _validate_joins(
        builder,
        normalized_trips,
        normalized_persons if table_is_usable[athenspop.schema.PERSONS_TABLE] else None,
        normalized_households
        if table_is_usable[athenspop.schema.HOUSEHOLDS_TABLE]
        else None,
    )
    _validate_metadata_values(
        builder,
        normalized_trips,
        table=athenspop.schema.TRIPS_TABLE,
        reserved_columns=athenspop.schema.TRIP_RESERVED_COLUMNS,
    )
    if (
        normalized_persons is not None
        and table_is_usable[athenspop.schema.PERSONS_TABLE]
    ):
        _validate_metadata_values(
            builder,
            normalized_persons,
            table=athenspop.schema.PERSONS_TABLE,
            reserved_columns=athenspop.schema.PERSON_KEY_COLUMNS,
        )
    if (
        normalized_households is not None
        and table_is_usable[athenspop.schema.HOUSEHOLDS_TABLE]
    ):
        _validate_metadata_values(
            builder,
            normalized_households,
            table=athenspop.schema.HOUSEHOLDS_TABLE,
            reserved_columns=athenspop.schema.HOUSEHOLD_KEY_COLUMNS,
        )
    timing_patterns = _validate_trip_rows(builder, normalized_trips)
    if timing_patterns is not None:
        normalized_trips["timing_pattern"] = timing_patterns
    ordered_trip_rows = _validate_trip_chains(builder, normalized_trips)
    validation_report = builder.build()
    if validation_report.has_errors:
        return ValidationResult(report=validation_report, normalized_tables=None)
    normalized_trips = normalized_trips.loc[ordered_trip_rows].copy()
    return ValidationResult(
        report=validation_report,
        normalized_tables=NormalizedTables(
            trips=normalized_trips,
            persons=normalized_persons,
            households=normalized_households,
        ),
    )


def _validate_table_shape(
    builder: athenspop.validation.report.ValidationReportBuilder,
    table: str,
    frame: pd.DataFrame,
    *,
    required_columns: tuple[str, ...],
) -> bool:
    """Validate a table before row-level checks."""
    if not isinstance(frame, pd.DataFrame):
        builder.add_error(
            code="table_not_dataframe",
            table=table,
            message=f"`{table}` must be a pandas DataFrame.",
        )
        return False
    if not frame.index.is_unique:
        builder.add_error(
            code="duplicate_index",
            table=table,
            message=(
                f"`{table}` must have a unique dataframe index so diagnostics "
                "and normalization identify each row unambiguously."
            ),
        )
        return False
    duplicated_columns = [
        str(column) for column in frame.columns[frame.columns.duplicated()].tolist()
    ]
    if duplicated_columns:
        builder.add_error(
            code="duplicate_columns",
            table=table,
            message=(
                f"`{table}` has duplicate column names: "
                f"{', '.join(duplicated_columns)}."
            ),
        )
        return False
    string_columns = [str(column) for column in frame.columns]
    normalized_duplicates = sorted(
        {column for column in string_columns if string_columns.count(column) > 1}
    )
    if normalized_duplicates:
        builder.add_error(
            code="normalized_column_collision",
            table=table,
            message=(
                f"`{table}` has column names that collide after string "
                f"normalization: {', '.join(normalized_duplicates)}."
            ),
        )
        return False
    missing_columns = [
        column for column in required_columns if column not in frame.columns
    ]
    if missing_columns:
        builder.add_error(
            code="missing_required_columns",
            table=table,
            message=(
                f"`{table}` is missing required column(s): "
                f"{', '.join(missing_columns)}."
            ),
        )
        return False
    return True


def _validate_keys(
    builder: athenspop.validation.report.ValidationReportBuilder,
    frame: pd.DataFrame,
    *,
    table: str,
    key_columns: tuple[str, ...],
) -> None:
    """Validate table keys and block rows that lack identity."""
    for column in key_columns:
        frame[column] = frame[column].astype(object)

    for row_index, row in frame.iterrows():
        row_identifier = _row_identifier(table, row_index)
        for column in key_columns:
            raw_value = row[column]
            if not pd.api.types.is_scalar(raw_value):
                builder.add_error(
                    code="unsupported_key_value",
                    table=table,
                    row_identifier=row_identifier,
                    column=column,
                    bad_value=repr(raw_value),
                    message=(
                        f"`{table}` row {row_identifier} has non-scalar `{column}` "
                        "key. Key columns must contain simple scalar values."
                    ),
                )
                break
            value = cast("ScalarValue", raw_value)
            if _is_missing(value):
                builder.add_error(
                    code="null_key",
                    table=table,
                    row_identifier=row_identifier,
                    column=column,
                    bad_value=_format_value(value),
                    message=(
                        f"`{table}` row {row_identifier} has a missing `{column}` "
                        "key. Fill the key before validation."
                    ),
                )
                break
            normalized_value = str(value).strip()
            if not normalized_value:
                builder.add_error(
                    code="blank_key",
                    table=table,
                    row_identifier=row_identifier,
                    column=column,
                    bad_value=repr(value),
                    message=(
                        f"`{table}` row {row_identifier} has a blank `{column}` "
                        "key. Fill the key before validation."
                    ),
                )
                break
            frame.loc[row_index, column] = normalized_value
    rows_for_duplicate_check = [
        index
        for index in frame.index
        if _row_identifier(table, index) not in builder.blocked_rows
    ]
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
                message=(
                    f"`{table}` row {row_identifier} duplicates the table identity "
                    f"`{', '.join(key_columns)}`. Each identity must appear once."
                ),
            )


def _validate_joins(
    builder: athenspop.validation.report.ValidationReportBuilder,
    trips: pd.DataFrame,
    persons: pd.DataFrame | None,
    households: pd.DataFrame | None,
) -> None:
    """Validate joins without suppressing unrelated trip-row checks."""
    trip_rows = [
        index
        for index in trips.index
        if _row_identifier(athenspop.schema.TRIPS_TABLE, index)
        not in builder.blocked_rows
    ]
    if persons is not None:
        valid_person_keys = {
            _key_tuple(row, athenspop.schema.PERSON_KEY_COLUMNS)
            for _, row in persons.iterrows()
        }
        for row_index in trip_rows:
            row = trips.loc[row_index]
            if (
                _key_tuple(row, athenspop.schema.PERSON_KEY_COLUMNS)
                not in valid_person_keys
            ):
                builder.add_error(
                    code="orphan_trip_person",
                    table=athenspop.schema.TRIPS_TABLE,
                    row_identifier=_row_identifier(
                        athenspop.schema.TRIPS_TABLE, row_index
                    ),
                    column=", ".join(athenspop.schema.PERSON_KEY_COLUMNS),
                    message=(
                        "`trips` row "
                        f"{_row_identifier(athenspop.schema.TRIPS_TABLE, row_index)} "
                        "references a person that is not present in `persons`."
                    ),
                    suppress_row=False,
                )
    if households is not None:
        valid_household_keys = {
            _key_tuple(row, athenspop.schema.HOUSEHOLD_KEY_COLUMNS)
            for _, row in households.iterrows()
        }
        for row_index in trip_rows:
            row = trips.loc[row_index]
            if (
                _key_tuple(row, athenspop.schema.HOUSEHOLD_KEY_COLUMNS)
                not in valid_household_keys
            ):
                builder.add_error(
                    code="orphan_trip_household",
                    table=athenspop.schema.TRIPS_TABLE,
                    row_identifier=_row_identifier(
                        athenspop.schema.TRIPS_TABLE, row_index
                    ),
                    column=", ".join(athenspop.schema.HOUSEHOLD_KEY_COLUMNS),
                    message=(
                        "`trips` row "
                        f"{_row_identifier(athenspop.schema.TRIPS_TABLE, row_index)} "
                        "references a household that is not present in `households`."
                    ),
                    suppress_row=False,
                )
        if persons is not None:
            person_rows = [
                index
                for index in persons.index
                if _row_identifier(athenspop.schema.PERSONS_TABLE, index)
                not in builder.blocked_rows
            ]
            for row_index in person_rows:
                row = persons.loc[row_index]
                row_identifier = _row_identifier(
                    athenspop.schema.PERSONS_TABLE, row_index
                )
                if (
                    _key_tuple(row, athenspop.schema.HOUSEHOLD_KEY_COLUMNS)
                    not in valid_household_keys
                ):
                    builder.add_error(
                        code="orphan_person_household",
                        table=athenspop.schema.PERSONS_TABLE,
                        row_identifier=row_identifier,
                        column=", ".join(athenspop.schema.HOUSEHOLD_KEY_COLUMNS),
                        message=(
                            f"`persons` row {row_identifier} references "
                            "a household that is not present in `households`."
                        ),
                        suppress_row=False,
                    )


def _validate_metadata_values(
    builder: athenspop.validation.report.ValidationReportBuilder,
    frame: pd.DataFrame,
    *,
    table: str,
    reserved_columns: tuple[str, ...],
) -> None:
    """Validate metadata before trusted model construction preserves it."""
    metadata_columns = [
        column for column in frame.columns if str(column) not in reserved_columns
    ]
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
                    message=(
                        f"`{table}` row {row_identifier} has non-scalar metadata in "
                        f"`{column}`. Extra metadata columns must contain simple "
                        "scalar values."
                    ),
                )
                break
            value = cast("ScalarValue", row[column])
            if _is_missing(value):
                continue
            if not isinstance(
                value,
                str | int | float | bool | np.integer | np.floating | np.bool_,
            ):
                builder.add_error(
                    code="unsupported_metadata_value",
                    table=table,
                    row_identifier=row_identifier,
                    column=str(column),
                    bad_value=repr(row[column]),
                    message=(
                        f"`{table}` row {row_identifier} has unsupported metadata "
                        f"in `{column}`. Extra metadata columns must contain strings, "
                        "numbers, booleans, or missing values."
                    ),
                )
                break


def _validate_trip_rows(
    builder: athenspop.validation.report.ValidationReportBuilder,
    trips: pd.DataFrame,
) -> pd.Series | None:
    """Validate trip fields and classify one timing pattern per usable row."""
    patterns: dict[Hashable, str] = {}
    for row_index in trips.index:
        row_identifier = _row_identifier(athenspop.schema.TRIPS_TABLE, row_index)
        if row_identifier in builder.blocked_rows:
            continue
        if not _normalize_trip_labels(builder, trips, row_index=row_index):
            continue
        row = trips.loc[row_index]
        if not _validate_second_values(builder, row, row_identifier=row_identifier):
            continue
        pattern = _classify_trip_timing(builder, row, row_identifier=row_identifier)
        if pattern is None:
            continue
        patterns[row_index] = pattern.value
    if not patterns and len(trips.index) > 0:
        return None
    return pd.Series(patterns, name="timing_pattern", dtype="string")


def _normalize_trip_labels(
    builder: athenspop.validation.report.ValidationReportBuilder,
    trips: pd.DataFrame,
    *,
    row_index: Hashable,
) -> bool:
    """Normalize one trip's movement labels and report the first invalid value."""
    row_identifier = _row_identifier(athenspop.schema.TRIPS_TABLE, row_index)
    row = trips.loc[row_index]
    for column in ("origin", "destination", "purpose", "mode"):
        raw_value = row[column]
        if not pd.api.types.is_scalar(raw_value):
            builder.add_error(
                code="unsupported_trip_value",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column=column,
                bad_value=repr(raw_value),
                message=(
                    f"`trips` row {row_identifier} has non-scalar `{column}`. "
                    "Movement and behavior columns must contain simple scalar values."
                ),
            )
            return False
        value = cast("ScalarValue", raw_value)
        normalized_value = "" if _is_missing(value) else str(value).strip()
        if not normalized_value:
            builder.add_error(
                code="missing_trip_value",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column=column,
                bad_value=_format_value(value),
                message=(
                    f"`trips` row {row_identifier} is missing `{column}`. Fill "
                    "the movement and behavior columns before loading."
                ),
            )
            return False
        trips.loc[row_index, column] = normalized_value
    return True


def _validate_second_values(
    builder: athenspop.validation.report.ValidationReportBuilder,
    row: pd.Series,
    *,
    row_identifier: str,
) -> bool:
    """Validate every present second-valued field on one trip row."""
    for column in athenspop.schema.SECOND_COLUMNS:
        if column not in row.index:
            continue
        raw_value = row[column]
        if not pd.api.types.is_scalar(raw_value):
            builder.add_error(
                code="invalid_second",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column=column,
                bad_value=repr(raw_value),
                message=(
                    f"`trips` row {row_identifier} has a non-scalar `{column}` "
                    "value. Time values must be integer seconds from the diary time "
                    "origin."
                ),
            )
            return False
        value = cast("ScalarValue", raw_value)
        second_value = _integer_second_value(value)
        if not _is_missing(value) and second_value is None:
            builder.add_error(
                code="invalid_second",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column=column,
                bad_value=_format_value(value),
                message=(
                    f"`trips` row {row_identifier} has `{column}`="
                    f"{_format_value(value)}. Time values must be integer seconds "
                    "from the diary time origin."
                ),
            )
            return False
        if second_value is not None and int(second_value) < 0:
            builder.add_error(
                code="negative_second",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column=column,
                bad_value=_format_value(value),
                message=(
                    f"`trips` row {row_identifier} has `{column}`="
                    f"{_format_value(value)}. Time values must be non-negative "
                    "integer seconds."
                ),
            )
            return False
    return True


def _classify_trip_timing(
    builder: athenspop.validation.report.ValidationReportBuilder,
    row: pd.Series,
    *,
    row_identifier: str,
) -> athenspop.schema.TimingPattern | None:
    """Classify one supported timing pattern and report semantic errors."""
    if _has_any_value(row, athenspop.schema.UNSUPPORTED_ARRIVAL_WINDOW_COLUMNS):
        builder.add_error(
            code="unsupported_arrival_window",
            table=athenspop.schema.TRIPS_TABLE,
            row_identifier=row_identifier,
            column=", ".join(athenspop.schema.UNSUPPORTED_ARRIVAL_WINDOW_COLUMNS),
            message=(
                f"`trips` row {row_identifier} uses an arrival-time range. Provide "
                "a concrete arrival time, fixed travel time, or a departure window "
                "plus travel time."
            ),
        )
        return None
    pattern = _detect_timing_pattern(row)
    if pattern is None:
        builder.add_error(
            code="invalid_timing_pattern",
            table=athenspop.schema.TRIPS_TABLE,
            row_identifier=row_identifier,
            column=", ".join(athenspop.schema.TRIP_TIMING_COLUMNS),
            message=(
                f"`trips` row {row_identifier} must match exactly one supported "
                "timing pattern."
            ),
        )
        return None
    pattern_error = _validate_timing_semantics(row, pattern)
    if pattern_error is None:
        return pattern
    code, column, message = pattern_error
    builder.add_error(
        code=code,
        table=athenspop.schema.TRIPS_TABLE,
        row_identifier=row_identifier,
        column=column,
        message=f"`trips` row {row_identifier} {message}",
    )
    return None


def _validate_trip_chains(
    builder: athenspop.validation.report.ValidationReportBuilder,
    trips: pd.DataFrame,
) -> list[Hashable]:
    """Validate diary chains and return row labels in trusted order."""
    valid_trip_rows = [
        index
        for index in trips.index
        if _row_identifier(athenspop.schema.TRIPS_TABLE, index)
        not in builder.blocked_rows
    ]
    if not valid_trip_rows:
        return []
    sortable = trips.loc[valid_trip_rows].copy()
    sortable["_input_order"] = range(len(sortable))
    ordered_rows: list[Hashable] = []
    for (household_id, person_id), group in sortable.groupby(
        ["household_id", "person_id"], sort=False
    ):
        chain_identifier = f"household_id={household_id}; person_id={person_id}"
        order_column = _resolve_trip_order_column(builder, group, chain_identifier)
        if order_column is None:
            continue
        ordered_group = group.sort_values(
            [order_column, "_input_order"], kind="mergesort"
        )
        ordered_rows.extend(ordered_group.index.to_list())
        previous_destination: str | None = None
        previous_arrival: int | None = None
        for row_index, row in ordered_group.iterrows():
            row_identifier = _row_identifier(athenspop.schema.TRIPS_TABLE, row_index)
            origin = str(row["origin"])
            if previous_destination is not None and origin != previous_destination:
                builder.add_warning(
                    code="origin_mismatch",
                    table=athenspop.schema.TRIPS_TABLE,
                    row_identifier=row_identifier,
                    column="origin",
                    message=(
                        f"`trips` row {row_identifier} starts "
                        f"at `{origin}`, but the previous trip in {chain_identifier} "
                        f"ended at `{previous_destination}`."
                    ),
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
            if (
                previous_arrival is not None
                and departure_second is not None
                and departure_second < previous_arrival
            ):
                builder.add_error(
                    code="overlapping_trips",
                    table=athenspop.schema.TRIPS_TABLE,
                    row_identifier=_row_identifier(
                        athenspop.schema.TRIPS_TABLE, row_index
                    ),
                    column="departure_second",
                    message=(
                        "`trips` row "
                        f"{_row_identifier(athenspop.schema.TRIPS_TABLE, row_index)} "
                        f"departs before the previous trip in {chain_identifier} has "
                        "arrived."
                    ),
                )
                builder.invalid_chains.add(chain_identifier)
                break
            previous_destination = str(row["destination"])
            previous_arrival = computed_arrival
    return ordered_rows


def _resolve_trip_order_column(
    builder: athenspop.validation.report.ValidationReportBuilder,
    group: pd.DataFrame,
    chain_identifier: str,
) -> str | None:
    """Choose explicit sequence or concrete-departure diary ordering."""
    if "trip_sequence" in group.columns:
        return _resolve_trip_sequence_order(builder, group, chain_identifier)
    return _resolve_concrete_departure_order(builder, group, chain_identifier)


def _resolve_trip_sequence_order(
    builder: athenspop.validation.report.ValidationReportBuilder,
    group: pd.DataFrame,
    chain_identifier: str,
) -> str | None:
    """Validate non-negative unique trip sequences for one diary."""
    seen_sequences: dict[int, Hashable] = {}
    for row_index, row in group.iterrows():
        row_identifier = _row_identifier(athenspop.schema.TRIPS_TABLE, row_index)
        value = cast("ScalarValue", row["trip_sequence"])
        sequence = _integer_second_value(value)
        if _is_missing(value):
            builder.add_error(
                code="missing_trip_sequence",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                bad_value=_format_value(value),
                message=(
                    f"`trips` row {row_identifier} is missing `trip_sequence`. Fill "
                    f"`trip_sequence` for every trip in {chain_identifier}, or omit "
                    "the column only when order is uniquely inferable from concrete "
                    "departure seconds."
                ),
            )
            builder.invalid_chains.add(chain_identifier)
            return None
        if sequence is None or int(sequence) < 0:
            builder.add_error(
                code="invalid_trip_sequence",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                bad_value=_format_value(value),
                message=(
                    f"`trips` row {row_identifier} has invalid `trip_sequence`="
                    f"{_format_value(value)}. Use non-negative integer sequence "
                    "values within each diary chain."
                ),
            )
            builder.invalid_chains.add(chain_identifier)
            return None
        sequence_int = int(sequence)
        if sequence_int in seen_sequences:
            builder.add_error(
                code="duplicate_trip_sequence",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                bad_value=_format_value(value),
                message=(
                    f"`trips` row {row_identifier} duplicates `trip_sequence`="
                    f"{sequence_int} in {chain_identifier}. Each trip sequence value "
                    "must be unique within a diary chain."
                ),
            )
            builder.invalid_chains.add(chain_identifier)
            return None
        seen_sequences[sequence_int] = row_index
    return "trip_sequence"


def _resolve_concrete_departure_order(
    builder: athenspop.validation.report.ValidationReportBuilder,
    group: pd.DataFrame,
    chain_identifier: str,
) -> str | None:
    """Use concrete departures as diary order when present and unique."""
    seen_departures: dict[int, Hashable] = {}
    for row_index, row in group.iterrows():
        row_identifier = _row_identifier(athenspop.schema.TRIPS_TABLE, row_index)
        departure_second = _optional_int(row, "departure_second")
        if departure_second is None:
            builder.add_error(
                code="unresolved_trip_order",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                message=(
                    f"`trips` row {row_identifier} has no concrete "
                    f"`departure_second`, so order is not uniquely inferable for "
                    f"{chain_identifier}. Add a non-negative integer `trip_sequence` "
                    "column for the whole diary chain."
                ),
            )
            builder.invalid_chains.add(chain_identifier)
            return None
        if departure_second in seen_departures:
            builder.add_error(
                code="unresolved_trip_order",
                table=athenspop.schema.TRIPS_TABLE,
                row_identifier=row_identifier,
                column="trip_sequence",
                bad_value=str(departure_second),
                message=(
                    f"`trips` row {row_identifier} has departure_second="
                    f"{departure_second}, which is duplicated in {chain_identifier}. "
                    "Add `trip_sequence` so the diary order is explicit."
                ),
            )
            builder.invalid_chains.add(chain_identifier)
            return None
        seen_departures[departure_second] = row_index
    return "departure_second"


def _detect_timing_pattern(row: pd.Series) -> athenspop.schema.TimingPattern | None:
    """Detect the timing pattern represented by one row."""
    presence = tuple(
        _has_value(row, column) for column in athenspop.schema.TRIP_TIMING_COLUMNS
    )
    return _TIMING_PATTERN_BY_PRESENCE.get(
        cast("tuple[bool, bool, bool, bool, bool]", presence)
    )


def _validate_timing_semantics(
    row: pd.Series, pattern: athenspop.schema.TimingPattern
) -> tuple[str, str, str] | None:
    """Validate timing inequalities that depend on the detected timing pattern."""
    if pattern == athenspop.schema.TimingPattern.DEPARTURE_ARRIVAL:
        departure_second = _required_int(row, "departure_second")
        arrival_second = _required_int(row, "arrival_second")
        if arrival_second <= departure_second:
            return (
                "non_positive_travel_duration",
                "arrival_second",
                f"arrives at {arrival_second}, which must be after "
                f"departure_second={departure_second}.",
            )
    if pattern == athenspop.schema.TimingPattern.DEPARTURE_DURATION:
        travel_time_seconds = _required_int(row, "travel_time_seconds")
        if travel_time_seconds <= 0:
            return (
                "non_positive_travel_duration",
                "travel_time_seconds",
                f"has travel_time_seconds={travel_time_seconds}. Movement travel time "
                "must be strictly positive.",
            )
    if pattern == athenspop.schema.TimingPattern.DEPARTURE_WINDOW_DURATION:
        earliest = _required_int(row, "earliest_departure_second")
        latest = _required_int(row, "latest_departure_second")
        travel_time_seconds = _required_int(row, "travel_time_seconds")
        if latest < earliest:
            return (
                "invalid_departure_window",
                "latest_departure_second",
                f"has latest_departure_second={latest} before "
                f"earliest_departure_second={earliest}.",
            )
        if travel_time_seconds <= 0:
            return (
                "non_positive_travel_duration",
                "travel_time_seconds",
                f"has travel_time_seconds={travel_time_seconds}. Movement travel time "
                "must be strictly positive.",
            )
    if pattern == athenspop.schema.TimingPattern.DEPARTURE_WINDOW_TRAVEL_TIME_FUNCTION:
        earliest = _required_int(row, "earliest_departure_second")
        latest = _required_int(row, "latest_departure_second")
        if latest < earliest:
            return (
                "invalid_departure_window",
                "latest_departure_second",
                f"has latest_departure_second={latest} before "
                f"earliest_departure_second={earliest}.",
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
    """Narrow a scalar to integer seconds without accepting booleans or floats."""
    if isinstance(value, bool | np.bool_):
        return None
    if isinstance(value, int | np.integer):
        return value
    return None


def _required_int(row: pd.Series, column: str) -> int:
    """Read required integer seconds from a validated row."""
    value = _integer_second_value(cast("ScalarValue", row[column]))
    if value is None:
        raise RuntimeError(
            f"`{column}` was not narrowed to an integer second before model "
            "construction."
        )
    return int(value)


def _optional_int(row: pd.Series, column: str) -> int | None:
    """Read optional integer seconds from a validated row."""
    if column not in row.index or _is_missing(cast("ScalarValue", row[column])):
        return None
    value = _integer_second_value(cast("ScalarValue", row[column]))
    if value is None:
        raise RuntimeError(
            f"`{column}` was not narrowed to an integer second before model "
            "construction."
        )
    return int(value)
