"""Trusted long-form survey model objects built only after dataframe validation."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

import numpy as np
import pandas as pd

from athenspop.validation import validate_dataframes
from athenspop.validation.schema import TimingPattern

type MetadataValue = str | int | float | bool | None
type RawMetadataValue = str | int | float | bool | np.integer | np.floating | np.bool_ | None
type Metadata = Mapping[str, MetadataValue]
type TravelTimeFunction = Callable[[str, str, str, int], int]


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Inclusive departure window in integer seconds from the survey time origin.

    Attributes:
        earliest_second:
            Earliest allowed departure second, inclusive.
        latest_second:
            Latest allowed departure second, inclusive.
    """

    earliest_second: int
    latest_second: int


@dataclass(frozen=True, slots=True)
class Trip:
    """One validated movement record in normalized long-form form.

    Attributes:
        household_id:
            Household identifier copied from the input trip row.
        person_id:
            Person identifier copied from the input trip row.
        trip_id:
            Trip identifier unique within the trip table identity.
        origin:
            Origin location label for the movement.
        destination:
            Destination location label for the movement.
        purpose:
            Activity state reached after the trip.
        mode:
            Travel mode label used for sequence states and travel-time lookup.
        departure_second:
            Concrete departure second from the survey time origin, or `None` when the scheduler still has to realize a departure window.
        arrival_second:
            Concrete arrival second from the survey time origin, or `None` when it must be derived from a duration or travel-time callable.
        travel_time_seconds:
            Positive integer travel duration, or `None` when it must be supplied by a travel-time callable.
        departure_window:
            Optional feasible departure range for trips that are not concrete at load time.
        timing_pattern:
            Validation-classified timing pattern that explains which timing columns supplied the trip.
        metadata:
            Additional non-key input columns preserved as immutable typed metadata.
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
    timing_pattern: TimingPattern
    metadata: Metadata

    @property
    def is_scheduled(self) -> bool:
        """Return whether this trip already has concrete departure and arrival seconds.

        Returns:
            `True` when both `departure_second` and `arrival_second` are present.
        """
        return self.departure_second is not None and self.arrival_second is not None


@dataclass(frozen=True, slots=True)
class PersonMetadata:
    """Optional respondent record attached to one person diary.

    Attributes:
        household_id:
            Household identifier shared with the diary.
        person_id:
            Person identifier shared with the diary.
        values:
            Immutable mapping of additional person table columns after boundary normalization.
    """

    household_id: str
    person_id: str
    values: Metadata


@dataclass(frozen=True, slots=True)
class HouseholdMetadata:
    """Optional household record attached to all diaries in a household.

    Attributes:
        household_id:
            Household identifier shared with diaries and persons.
        values:
            Immutable mapping of additional household table columns after boundary normalization.
    """

    household_id: str
    values: Metadata


@dataclass(frozen=True, slots=True)
class Diary:
    """Ordered trip chain for one household-person pair.

    Attributes:
        household_id:
            Household identifier for the diary.
        person_id:
            Person identifier for the diary.
        trips:
            Validated trips sorted into diary order.
        person:
            Optional respondent metadata matched by `(household_id, person_id)`.
        household:
            Optional household metadata matched by `household_id`.
    """

    household_id: str
    person_id: str
    trips: tuple[Trip, ...]
    person: PersonMetadata | None = None
    household: HouseholdMetadata | None = None


@dataclass(frozen=True, slots=True)
class SurveyDataset:
    """Validated survey dataset grouped into person-level diaries.

    Attributes:
        diaries:
            Person-level travel diaries built from the trip table.
        households:
            Optional household metadata records that were supplied at the dataframe boundary.
        persons:
            Optional person metadata records that were supplied at the dataframe boundary.
    """

    diaries: tuple[Diary, ...]
    households: tuple[HouseholdMetadata, ...]
    persons: tuple[PersonMetadata, ...]

    @classmethod
    def from_dataframes(
        cls,
        trips: pd.DataFrame,
        persons: pd.DataFrame | None = None,
        households: pd.DataFrame | None = None,
        *,
        travel_time_function: TravelTimeFunction | None = None,
    ) -> "SurveyDataset":
        """Validate input dataframes and build trusted model objects.

        Args:
            trips:
                Required long-form trip table.
            persons:
                Optional person/respondent table keyed by `household_id` and `person_id`.
            households:
                Optional household table keyed by `household_id`.
            travel_time_function:
                Optional callable returning positive integer travel seconds for timing patterns that provide a departure time but no duration or arrival time.

        Returns:
            A trusted `SurveyDataset` containing immutable diaries and metadata records.

        Raises:
            ValidationError:
                If dataframe validation collected any hard errors.
            RuntimeError:
                If validation reports success but does not provide normalized tables.
            ValueError:
                If `travel_time_function` is needed during model construction and returns an invalid value.

        Notes:
            Internal code treats the returned objects as complete and trusted; validation belongs at this dataframe/file boundary.
        """
        result = validate_dataframes(trips, persons=persons, households=households, travel_time_function=travel_time_function)
        result.report.raise_if_invalid()
        if result.normalized_tables is None:
            raise RuntimeError("Validation unexpectedly produced no normalized tables after passing `raise_if_invalid`.")
        household_records = _build_households(result.normalized_tables.households)
        person_records = _build_persons(result.normalized_tables.persons)
        household_by_id = {record.household_id: record for record in household_records}
        person_by_id = {(record.household_id, record.person_id): record for record in person_records}
        trips_by_person: dict[tuple[str, str], list[Trip]] = {}
        for _, row in result.normalized_tables.trips.iterrows():
            trip = _build_trip(row, travel_time_function=travel_time_function)
            trips_by_person.setdefault((trip.household_id, trip.person_id), []).append(trip)
        diaries = tuple(
            Diary(
                household_id=household_id,
                person_id=person_id,
                trips=tuple(person_trips),
                person=person_by_id.get((household_id, person_id)),
                household=household_by_id.get(household_id),
            )
            for (household_id, person_id), person_trips in sorted(trips_by_person.items())
        )
        return cls(diaries=diaries, households=household_records, persons=person_records)


def _build_trip(row: pd.Series, *, travel_time_function: TravelTimeFunction | None) -> Trip:
    """Build one trusted trip from a normalized row whose timing pattern already passed validation."""
    household_id = str(row["household_id"])
    person_id = str(row["person_id"])
    origin = str(row["origin"])
    destination = str(row["destination"])
    purpose = str(row["purpose"])
    mode = str(row["mode"])
    timing_pattern = TimingPattern(str(row["timing_pattern"]))
    departure_second = _optional_int(row, "departure_second")
    arrival_second = _optional_int(row, "arrival_second")
    travel_time_seconds = _optional_int(row, "travel_time_seconds")
    departure_window = _build_departure_window(row)
    if timing_pattern == TimingPattern.DEPARTURE_DURATION and departure_second is not None and travel_time_seconds is not None:
        arrival_second = departure_second + travel_time_seconds
    if timing_pattern == TimingPattern.DEPARTURE_TRAVEL_TIME_FUNCTION and travel_time_function is not None and departure_second is not None:
        travel_time_seconds = _resolve_travel_time(travel_time_function, origin, destination, mode, departure_second)
        arrival_second = departure_second + travel_time_seconds
    metadata = _metadata(
        row,
        exclude={
            "household_id",
            "person_id",
            "trip_id",
            "origin",
            "destination",
            "purpose",
            "mode",
            "departure_second",
            "arrival_second",
            "travel_time_seconds",
            "earliest_departure_second",
            "latest_departure_second",
            "trip_sequence",
            "timing_pattern",
        },
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


def _resolve_travel_time(
    travel_time_function: TravelTimeFunction,
    origin: str,
    destination: str,
    mode: str,
    departure_second: int,
) -> int:
    """Call a boundary travel-time function and narrow its result to positive integer seconds."""
    result = travel_time_function(origin, destination, mode, departure_second)
    if isinstance(result, bool) or not isinstance(result, int) or result <= 0:
        raise ValueError(
            f"`travel_time_function` returned {result!r} for origin={origin!r}, destination={destination!r}, mode={mode!r}, departure_second={departure_second}. It must return a strictly positive integer number of seconds."
        )
    return result


def _build_persons(persons: pd.DataFrame | None) -> tuple[PersonMetadata, ...]:
    """Build immutable person metadata records from a validated optional person table."""
    if persons is None:
        return ()
    records: list[PersonMetadata] = []
    for _, row in persons.iterrows():
        records.append(
            PersonMetadata(
                household_id=str(row["household_id"]),
                person_id=str(row["person_id"]),
                values=_metadata(row, exclude={"household_id", "person_id"}),
            )
        )
    return tuple(records)


def _build_households(households: pd.DataFrame | None) -> tuple[HouseholdMetadata, ...]:
    """Build immutable household metadata records from a validated optional household table."""
    if households is None:
        return ()
    records: list[HouseholdMetadata] = []
    for _, row in households.iterrows():
        records.append(
            HouseholdMetadata(
                household_id=str(row["household_id"]),
                values=_metadata(row, exclude={"household_id"}),
            )
        )
    return tuple(records)


def _metadata(row: pd.Series, *, exclude: set[str]) -> Metadata:
    """Preserve non-domain columns as immutable metadata after converting NumPy scalars to Python scalars."""
    values = {
        str(column): _metadata_value(cast("RawMetadataValue", row[column])) for column in row.index if str(column) not in exclude and not pd.isna(row[column])
    }
    return MappingProxyType(values)


def _metadata_value(value: RawMetadataValue) -> MetadataValue:
    """Normalize pandas/NumPy scalar values into the small metadata value union."""
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
