# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module builds trusted survey models after dataframe validation."""

import collections.abc
import dataclasses
import types
import typing

import numpy as np
import pandas as pd

import athenspop.schema
import athenspop.types
import athenspop.validation.schema

#: This type represents a scalar value preserved in immutable user metadata.
type MetadataValue = str | int | float | bool | None
#: This type represents a scalar metadata value accepted at the dataframe boundary.
type RawMetadataValue = (
    str | int | float | bool | np.integer | np.floating | np.bool_ | None
)
#: This type maps user-defined metadata column names to normalized values.
type Metadata = collections.abc.Mapping[str, MetadataValue]


@dataclasses.dataclass(frozen=True, slots=True)
class TimeWindow:
    """This class represents an inclusive departure window in integer seconds.

    Attributes:
        earliest_second: This value is the earliest allowed departure second,
            inclusive.
        latest_second: This value is the latest allowed departure second, inclusive.
    """

    earliest_second: int
    latest_second: int


@dataclasses.dataclass(frozen=True, slots=True)
class Trip:
    """This class represents one validated long-form movement record.

    Attributes:
        household_id: This identifier is copied from the input trip row.
        person_id: This person identifier is copied from the input trip row.
        trip_id: This trip identifier is unique within the trip table identity.
        origin: This value labels the movement origin.
        destination: This value labels the movement destination.
        purpose: This value is the activity state reached after the trip.
        mode: This travel-mode label is used for sequence states and travel-time
            lookup.
        departure_second:
            The concrete departure is measured in seconds from the diary time origin,
            or it is `None` when the scheduler must realize a departure window.
        arrival_second:
            The concrete arrival is measured in seconds from the diary time origin,
            or it is `None` when a duration or travel-time callable must derive it.
        travel_time_seconds: This value is the positive integer travel duration, or
            it is `None` when a travel-time callable must supply the duration.
        departure_window: This value is the optional feasible departure range for
            trips that are not concrete at load time.
        timing_pattern: This validation-classified pattern identifies the timing
            columns that supplied the trip.
        metadata: This immutable typed metadata preserves additional non-key input
            columns.
    """

    household_id: str
    person_id: str
    trip_id: str
    origin: str
    destination: str
    purpose: str
    mode: str
    departure_second: int | None
    arrival_second: int | None
    travel_time_seconds: int | None
    departure_window: TimeWindow | None
    timing_pattern: athenspop.schema.TimingPattern
    metadata: Metadata

    @property
    def is_scheduled(self) -> bool:
        """Return whether this trip already has concrete departure and arrival seconds.

        Returns:
            The property returns `True` when both `departure_second` and
            `arrival_second` are present.
        """
        return self.departure_second is not None and self.arrival_second is not None


@dataclasses.dataclass(frozen=True, slots=True)
class PersonMetadata:
    """This class represents an optional respondent record for one diary.

    Attributes:
        household_id: This household identifier is shared with the diary.
        person_id: This person identifier is shared with the diary.
        values: This immutable mapping contains additional person table columns after
            boundary normalization.
    """

    household_id: str
    person_id: str
    values: Metadata


@dataclasses.dataclass(frozen=True, slots=True)
class HouseholdMetadata:
    """This class represents an optional household record for its diaries.

    Attributes:
        household_id: This household identifier is shared with diaries and persons.
        values: This immutable mapping contains additional household table columns
            after boundary normalization.
    """

    household_id: str
    values: Metadata


@dataclasses.dataclass(frozen=True, slots=True)
class Diary:
    """This class represents an ordered trip chain for one person.

    Attributes:
        household_id: This value is the household identifier for the diary.
        person_id: This value is the person identifier for the diary.
        trips: These validated trips are sorted into diary order.
        person: This optional respondent metadata is matched by `(household_id,
            person_id)`.
        household: This optional household metadata is matched by `household_id`.
    """

    household_id: str
    person_id: str
    trips: tuple[Trip, ...]
    person: PersonMetadata | None = None
    household: HouseholdMetadata | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class SurveyDataset:
    """This class represents a validated survey grouped into person diaries.

    Attributes:
        diaries: These person-level travel diaries are built from the trip table.
        households: These optional household metadata records were supplied at the
            dataframe boundary.
        persons: These optional person metadata records were supplied at the
            dataframe boundary.
        travel_time_function: This optional default resolver is retained for
            unresolved departure-window trips.
    """

    diaries: tuple[Diary, ...]
    households: tuple[HouseholdMetadata, ...]
    persons: tuple[PersonMetadata, ...]
    travel_time_function: athenspop.types.TravelTimeFunction | None = None

    @classmethod
    def from_dataframes(
        cls,
        trips: pd.DataFrame,
        persons: pd.DataFrame | None = None,
        households: pd.DataFrame | None = None,
        *,
        travel_time_function: athenspop.types.TravelTimeFunction | None = None,
    ) -> "SurveyDataset":
        """Validate input dataframes and build trusted model objects.

        Args:
            trips: This value is the required long-form trip table.
            persons: This optional person or respondent table is keyed by
                `household_id` and `person_id`.
            households: This optional household table is keyed by `household_id`.
            travel_time_function: This optional callable returns positive integer
                travel seconds for timing patterns that provide a departure time but
                no duration or arrival time.

        Returns:
            The method returns a trusted `SurveyDataset` containing immutable diaries
            and metadata records.

        Raises:
            TypeError: The method raises this error if `travel_time_function` is
                provided but is not callable.
            ValidationError: The method raises this error if dataframe validation
                collects any hard errors.
            RuntimeError: The method raises this error if validation reports success
                but does not provide normalized tables.

        Notes:
            The returned objects are complete and trusted; validation belongs at
            this dataframe boundary.
        """
        if travel_time_function is not None and not callable(travel_time_function):
            raise TypeError("`travel_time_function` must be callable when provided.")
        result = athenspop.validation.schema.validate_dataframes(
            trips,
            persons=persons,
            households=households,
        )
        result.report.raise_if_invalid()
        if result.normalized_tables is None:
            raise RuntimeError(
                "Validation unexpectedly produced no normalized tables after passing "
                "`raise_if_invalid`."
            )
        household_records = _build_households(result.normalized_tables.households)
        person_records = _build_persons(result.normalized_tables.persons)
        household_by_id = {record.household_id: record for record in household_records}
        person_by_id = {
            (record.household_id, record.person_id): record for record in person_records
        }
        trips_by_person: dict[tuple[str, str], list[Trip]] = {}
        for _, row in result.normalized_tables.trips.iterrows():
            trip = _build_trip(row)
            trips_by_person.setdefault((trip.household_id, trip.person_id), []).append(
                trip
            )
        diaries = tuple(
            Diary(
                household_id=household_id,
                person_id=person_id,
                trips=tuple(person_trips),
                person=person_by_id.get((household_id, person_id)),
                household=household_by_id.get(household_id),
            )
            for (household_id, person_id), person_trips in sorted(
                trips_by_person.items()
            )
        )
        return cls(
            diaries=diaries,
            households=household_records,
            persons=person_records,
            travel_time_function=travel_time_function,
        )


def _build_trip(row: pd.Series) -> Trip:
    """Build a trusted trip from a validated, normalized row."""
    household_id = str(row["household_id"])
    person_id = str(row["person_id"])
    origin = str(row["origin"])
    destination = str(row["destination"])
    purpose = str(row["purpose"])
    mode = str(row["mode"])
    timing_pattern = athenspop.schema.TimingPattern(str(row["timing_pattern"]))
    departure_second = _optional_int(row, "departure_second")
    arrival_second = _optional_int(row, "arrival_second")
    travel_time_seconds = _optional_int(row, "travel_time_seconds")
    departure_window = _build_departure_window(row)
    if (
        timing_pattern == athenspop.schema.TimingPattern.DEPARTURE_DURATION
        and departure_second is not None
        and travel_time_seconds is not None
    ):
        arrival_second = departure_second + travel_time_seconds
    metadata = _metadata(
        row,
        exclude=set(athenspop.schema.TRIP_RESERVED_COLUMNS),
    )
    return Trip(
        household_id=household_id,
        person_id=person_id,
        trip_id=str(row["trip_id"]),
        origin=origin,
        destination=destination,
        purpose=purpose,
        mode=mode,
        departure_second=departure_second,
        arrival_second=arrival_second,
        travel_time_seconds=travel_time_seconds,
        departure_window=departure_window,
        timing_pattern=timing_pattern,
        metadata=metadata,
    )


def _build_departure_window(row: pd.Series) -> TimeWindow | None:
    """Return the validated departure window when both window columns are present."""
    earliest = _optional_int(row, "earliest_departure_second")
    latest = _optional_int(row, "latest_departure_second")
    if earliest is None or latest is None:
        return None
    return TimeWindow(earliest_second=earliest, latest_second=latest)


def _build_persons(persons: pd.DataFrame | None) -> tuple[PersonMetadata, ...]:
    """Build immutable metadata from an optional validated person table."""
    if persons is None:
        return ()
    return tuple(
        PersonMetadata(
            household_id=str(row["household_id"]),
            person_id=str(row["person_id"]),
            values=_metadata(row, exclude={"household_id", "person_id"}),
        )
        for _, row in persons.iterrows()
    )


def _build_households(
    households: pd.DataFrame | None,
) -> tuple[HouseholdMetadata, ...]:
    """Build immutable metadata from an optional validated household table."""
    if households is None:
        return ()
    return tuple(
        HouseholdMetadata(
            household_id=str(row["household_id"]),
            values=_metadata(row, exclude={"household_id"}),
        )
        for _, row in households.iterrows()
    )


def _metadata(row: pd.Series, *, exclude: set[str]) -> Metadata:
    """Preserve non-domain columns as normalized, immutable metadata."""
    values = {
        str(column): _metadata_value(typing.cast("RawMetadataValue", row[column]))
        for column in row.index
        if str(column) not in exclude
    }
    return types.MappingProxyType(values)


def _metadata_value(value: RawMetadataValue) -> MetadataValue:
    """Normalize pandas/NumPy scalar values into the small metadata value union."""
    if pd.isna(value):
        return None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def _optional_int(row: pd.Series, column: str) -> int | None:
    """Read an optional normalized integer column from a trusted row."""
    if column not in row.index or pd.isna(row[column]):
        return None
    return int(row[column])
