# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module defines behavior contracts for dataframe validation and models."""

from typing import cast

import numpy as np
import pandas as pd
import pytest

import athenspop.model.survey
import athenspop.scheduling.engine
import athenspop.types
import athenspop.validation.report
import athenspop.validation.schema


def _constant_travel_time(seconds: int) -> athenspop.types.TravelTimeFunction:
    """Return a deterministic travel-time function for a test scenario."""

    def travel_time_function(
        origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        """Return the duration configured by the enclosing test."""
        del origin, destination, mode, departure_second
        return seconds

    return travel_time_function


def _trip_row(**overrides: object) -> dict[str, object]:
    """Return one valid trip row with selected values replaced."""
    row: dict[str, object] = {
        "household_id": "h1",
        "person_id": "p1",
        "trip_id": "t1",
        "origin": "home",
        "destination": "work",
        "purpose": "work",
        "mode": "bus",
        "departure_second": 0,
        "arrival_second": 900,
    }
    row.update(overrides)
    return row


def test_validates_and_loads_concrete_trip_with_zero_departure_second() -> None:
    """Preserve midnight as a valid departure while joining numeric identities."""
    trips = pd.DataFrame(
        [
            {
                "household_id": 1,
                "person_id": 10,
                "trip_id": 100,
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "departure_second": 0,
                "arrival_second": 900,
            }
        ]
    )
    persons = pd.DataFrame([{"household_id": 1, "person_id": 10, "age": 22}])
    households = pd.DataFrame([{"household_id": 1, "home_zone": "home"}])
    result = athenspop.validation.schema.validate_dataframes(
        trips, persons=persons, households=households
    )
    assert not result.report.has_errors
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, persons=persons, households=households
    )
    assert len(dataset.diaries) == 1
    trip = dataset.diaries[0].trips[0]
    assert trip.departure_second == 0
    assert trip.arrival_second == 900
    assert dataset.diaries[0].person is not None
    assert dataset.diaries[0].person.values["age"] == 22
    assert dataset.diaries[0].household is not None
    assert dataset.diaries[0].household.values["home_zone"] == "home"


def test_model_normalizes_numpy_and_missing_metadata_scalars() -> None:
    """Expose user metadata as immutable Python scalar values or `None`."""
    persons = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "count": np.int64(2),
                "ratio": np.float64(0.5),
                "flag": np.bool_(True),
                "missing": pd.NA,
            }
        ]
    )
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        pd.DataFrame([_trip_row()]), persons=persons
    )

    person = dataset.persons[0]
    assert person.values == {
        "count": 2,
        "ratio": 0.5,
        "flag": True,
        "missing": None,
    }
    assert all(
        type(person.values[name]) is expected_type
        for name, expected_type in {
            "count": int,
            "ratio": float,
            "flag": bool,
        }.items()
    )


def test_loads_departure_plus_duration_as_concrete_arrival() -> None:
    """Derive a concrete arrival from a departure and fixed travel duration."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "a",
                "destination": "b",
                "purpose": "shop",
                "mode": "walk",
                "departure_second": 60,
                "travel_time_seconds": 120,
            }
        ]
    )
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    trip = dataset.diaries[0].trips[0]
    assert trip.departure_second == 60
    assert trip.travel_time_seconds == 120
    assert trip.arrival_second == 180


def test_scheduler_resolves_the_dataset_travel_time_function() -> None:
    """Resolve an unresolved trip only at the scheduling boundary."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "a",
                "destination": "b",
                "purpose": "shop",
                "mode": "walk",
                "departure_second": 60,
            }
        ]
    )
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, travel_time_function=_constant_travel_time(120)
    )
    assert dataset.diaries[0].trips[0].arrival_second is None
    scheduled = athenspop.scheduling.engine.schedule_once(dataset)
    assert scheduled.dataset.diaries[0].trips[0].arrival_second == 180

    invalid_dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, travel_time_function=_constant_travel_time(0)
    )
    invalid = athenspop.scheduling.engine.schedule_once(invalid_dataset)
    assert invalid.diagnostics.issues[0].code == "invalid_travel_time_function_result"


def test_callable_resolution_preserves_a_later_fixed_trip() -> None:
    """Reject a diary whose callable trip cannot precede its next fixed trip."""
    trips = pd.DataFrame(
        [
            _trip_row(
                trip_id="t1",
                trip_sequence=1,
                arrival_second=None,
            ),
            _trip_row(
                trip_id="t2",
                trip_sequence=2,
                origin="work",
                destination="home",
                purpose="home",
                departure_second=50,
                arrival_second=60,
            ),
        ],
        dtype=object,
    )

    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, travel_time_function=_constant_travel_time(100)
    )
    scheduled = athenspop.scheduling.engine.schedule_once(dataset)

    assert scheduled.diagnostics.scheduled_diaries == 0


def test_validation_collects_join_and_timing_errors_without_cascade() -> None:
    """Report independent join and timing faults without validating a null-key row."""
    trips = pd.DataFrame(
        [
            {
                "household_id": None,
                "person_id": "p1",
                "trip_id": "bad-key",
                "origin": "a",
                "destination": "b",
                "purpose": "work",
                "mode": "car",
                "departure_second": -1,
                "arrival_second": 10,
            },
            {
                "household_id": "h2",
                "person_id": "p2",
                "trip_id": "orphan",
                "origin": "a",
                "destination": "b",
                "purpose": "work",
                "mode": "car",
                "departure_second": 20,
                "arrival_second": 10,
            },
        ]
    )
    persons = pd.DataFrame([{"household_id": "h1", "person_id": "p1"}])
    result = athenspop.validation.schema.validate_dataframes(trips, persons=persons)
    codes = [issue.code for issue in result.report.errors]
    assert "null_key" in codes
    assert "negative_second" not in codes
    assert "orphan_trip_person" in codes
    assert "non_positive_travel_duration" in codes


def test_ambiguous_timing_pattern_raises_concise_validation_error() -> None:
    """Reject rows that specify both arrival time and travel duration."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "a",
                "destination": "b",
                "purpose": "work",
                "mode": "car",
                "departure_second": 10,
                "arrival_second": 20,
                "travel_time_seconds": 10,
            }
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == ["invalid_timing_pattern"]
    with pytest.raises(athenspop.validation.report.ValidationError):
        result.report.raise_if_invalid()


def test_table_level_validation_diagnostic_codes_are_reported() -> None:
    """Distinguish invalid table types, duplicate columns, and missing columns."""
    not_dataframe = athenspop.validation.schema.validate_dataframes(
        cast("pd.DataFrame", object())
    )
    assert [issue.code for issue in not_dataframe.report.errors] == [
        "table_not_dataframe"
    ]

    duplicate_columns = pd.DataFrame(
        [["h1", "p1", "t1"]],
        columns=["household_id", "household_id", "trip_id"],
    )
    duplicate_result = athenspop.validation.schema.validate_dataframes(
        duplicate_columns
    )
    assert [issue.code for issue in duplicate_result.report.errors] == [
        "duplicate_columns"
    ]

    missing_columns = athenspop.validation.schema.validate_dataframes(
        pd.DataFrame([{"household_id": "h1"}])
    )
    assert [issue.code for issue in missing_columns.report.errors] == [
        "missing_required_columns"
    ]


@pytest.mark.parametrize("table_name", ["persons", "households"])
def test_invalid_optional_table_type_returns_validation_report(
    table_name: str,
) -> None:
    """Return one table-type error when optional metadata is not a dataframe."""
    invalid_table = cast("pd.DataFrame", 42)
    result = (
        athenspop.validation.schema.validate_dataframes(
            pd.DataFrame([_trip_row()]), persons=invalid_table
        )
        if table_name == "persons"
        else athenspop.validation.schema.validate_dataframes(
            pd.DataFrame([_trip_row()]), households=invalid_table
        )
    )

    assert [issue.code for issue in result.report.errors] == ["table_not_dataframe"]
    assert result.normalized_tables is None


def test_duplicate_dataframe_index_is_rejected_before_row_mutation() -> None:
    """Reject duplicate row labels before normalization can overwrite rows."""
    trips = pd.DataFrame(
        [
            _trip_row(trip_id="t1"),
            _trip_row(
                trip_id="t2",
                departure_second=1_800,
                arrival_second=2_700,
            ),
        ],
        index=[0, 0],
    )

    result = athenspop.validation.schema.validate_dataframes(trips)

    assert [issue.code for issue in result.report.errors] == ["duplicate_index"]


def test_metadata_column_names_must_be_unique_after_string_normalization() -> None:
    """Reject distinct column labels that normalize to the same text."""
    trips = pd.DataFrame([_trip_row()])
    trips[1] = "first"
    trips["1"] = "second"

    result = athenspop.validation.schema.validate_dataframes(trips)

    assert [issue.code for issue in result.report.errors] == [
        "normalized_column_collision"
    ]


def test_model_rejects_a_non_callable_travel_time_function() -> None:
    """Reject a non-callable resolver before constructing a survey dataset."""
    trips = pd.DataFrame([_trip_row(arrival_second=None)])

    with pytest.raises(TypeError, match="must be callable"):
        athenspop.model.survey.SurveyDataset.from_dataframes(
            trips,
            travel_time_function=cast("athenspop.types.TravelTimeFunction", 42),
        )


def test_float_seconds_are_rejected_even_when_integer_valued() -> None:
    """Require integer-typed seconds rather than integer-valued floats."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "a",
                "destination": "b",
                "purpose": "work",
                "mode": "car",
                "departure_second": 10.0,
                "arrival_second": 20,
            }
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == ["invalid_second"]


def test_duplicate_keys_are_checked_after_string_normalization() -> None:
    """Detect duplicate trip identities after converting key values to text."""
    trips = pd.DataFrame(
        [
            {
                "household_id": 1,
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "departure_second": 0,
                "arrival_second": 900,
            },
            {
                "household_id": "1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "work",
                "destination": "home",
                "purpose": "home",
                "mode": "bus",
                "departure_second": 1800,
                "arrival_second": 2700,
            },
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == [
        "duplicate_key",
        "duplicate_key",
    ]


@pytest.mark.parametrize("key", ["household_id", "person_id", "trip_id"])
def test_identity_keys_must_contain_nonblank_text(key: str) -> None:
    """Reject whitespace-only identities after canonical string normalization."""
    result = athenspop.validation.schema.validate_dataframes(
        pd.DataFrame([_trip_row(**{key: "  "})])
    )

    assert [issue.code for issue in result.report.errors] == ["blank_key"]


def test_non_scalar_key_and_movement_values_are_rejected_at_boundary() -> None:
    """Assign field-specific diagnostics to collection-valued row fields."""
    non_scalar_key_trips = pd.DataFrame(
        [
            {
                "household_id": ["h1"],
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "departure_second": 0,
                "arrival_second": 900,
            }
        ]
    )
    key_result = athenspop.validation.schema.validate_dataframes(non_scalar_key_trips)
    assert [issue.code for issue in key_result.report.errors] == [
        "unsupported_key_value"
    ]

    non_scalar_origin_trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": ["home"],
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "departure_second": 0,
                "arrival_second": 900,
            }
        ]
    )
    origin_result = athenspop.validation.schema.validate_dataframes(
        non_scalar_origin_trips
    )
    assert [issue.code for issue in origin_result.report.errors] == [
        "unsupported_trip_value"
    ]

    non_scalar_second = athenspop.validation.schema.validate_dataframes(
        pd.DataFrame([_trip_row(departure_second=[0])])
    )
    assert [issue.code for issue in non_scalar_second.report.errors] == [
        "invalid_second"
    ]


def test_trip_row_domain_diagnostic_codes_are_reported_once() -> None:
    """Emit one precise diagnostic for each invalid trip-domain value."""
    missing_value = athenspop.validation.schema.validate_dataframes(
        pd.DataFrame([_trip_row(origin="")])
    )
    assert [issue.code for issue in missing_value.report.errors] == [
        "missing_trip_value"
    ]

    arrival_window = athenspop.validation.schema.validate_dataframes(
        pd.DataFrame([_trip_row(earliest_arrival_second=100)])
    )
    assert [issue.code for issue in arrival_window.report.errors] == [
        "unsupported_arrival_window"
    ]

    negative_second = athenspop.validation.schema.validate_dataframes(
        pd.DataFrame([_trip_row(departure_second=-1)])
    )
    assert [issue.code for issue in negative_second.report.errors] == [
        "negative_second"
    ]


def test_mixed_timing_patterns_accept_nullable_integer_second_columns() -> None:
    """Accept mixed timing patterns stored in nullable integer columns."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "trip_sequence": 1,
                "earliest_departure_second": 0,
                "latest_departure_second": 10,
                "travel_time_seconds": 20,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "home",
                "purpose": "home",
                "mode": "bus",
                "trip_sequence": 2,
                "departure_second": 100,
                "travel_time_seconds": 20,
            },
        ]
    )
    for column in (
        "trip_sequence",
        "departure_second",
        "travel_time_seconds",
        "earliest_departure_second",
        "latest_departure_second",
    ):
        trips[column] = trips[column].astype("Int64")
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert not result.report.has_errors
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    assert dataset.diaries[0].trips[0].departure_window is not None
    assert dataset.diaries[0].trips[1].departure_second == 100


def test_non_scalar_metadata_is_rejected_at_validation_boundary() -> None:
    """Reject collection-valued metadata before immutable model construction."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "departure_second": 0,
                "arrival_second": 900,
            }
        ]
    )
    persons = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "tags": ["student", "worker"],
            }
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips, persons=persons)
    assert [issue.code for issue in result.report.errors] == [
        "unsupported_metadata_value"
    ]
    with pytest.raises(athenspop.validation.report.ValidationError, match="1 error"):
        athenspop.model.survey.SurveyDataset.from_dataframes(trips, persons=persons)


def test_origin_mismatch_is_warning_not_hard_error() -> None:
    """Keep a discontinuous trip chain usable while reporting its origin warning."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "departure_second": 10,
                "arrival_second": 20,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "gym",
                "destination": "home",
                "purpose": "home",
                "mode": "car",
                "departure_second": 30,
                "arrival_second": 40,
            },
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert not result.report.has_errors
    assert result.report.has_warnings
    assert [issue.code for issue in result.report.warnings] == ["origin_mismatch"]
    result.report.raise_if_invalid()


def test_validation_does_not_assume_scheduler_minimum_activity_duration() -> None:
    """Accept positive gaps without imposing the scheduler's activity policy."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "trip_sequence": 1,
                "departure_second": 0,
                "arrival_second": 900,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "market",
                "purpose": "market",
                "mode": "walk",
                "trip_sequence": 2,
                "departure_second": 1200,
                "arrival_second": 1800,
            },
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert not result.report.has_errors
    assert result.report.warnings == ()


def test_household_metadata_does_not_create_study_specific_chain_warnings() -> None:
    """Treat household fields as metadata rather than universal chain rules."""
    households = pd.DataFrame([{"household_id": "h1", "home_zone": "zone-home"}])
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "not-home",
                "destination": "somewhere-else",
                "purpose": "work",
                "mode": "bus",
                "departure_second": 0,
                "arrival_second": 900,
            }
        ]
    )
    assert (
        athenspop.validation.schema.validate_dataframes(
            trips, households=households
        ).report.warnings
        == ()
    )


def test_user_defined_purpose_and_mode_labels_are_valid() -> None:
    """Accept nonempty user-defined purpose and mode labels without warnings."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "pier",
                "purpose": "fishing",
                "mode": "boat",
                "departure_second": 0,
                "arrival_second": 900,
            }
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert not result.report.has_errors
    assert result.report.warnings == ()


def test_trip_sequence_orders_model_trips_when_input_rows_are_unsorted() -> None:
    """Sort each diary by sequence and omit the structural field from metadata."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "home",
                "purpose": "home",
                "mode": "bus",
                "trip_sequence": 2,
                "departure_second": 3600,
                "arrival_second": 4500,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "trip_sequence": 1,
                "departure_second": 900,
                "arrival_second": 1800,
            },
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert not result.report.has_errors
    assert result.normalized_tables is not None
    assert result.normalized_tables.trips["trip_id"].tolist() == ["t1", "t2"]
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    assert [trip.trip_id for trip in dataset.diaries[0].trips] == ["t1", "t2"]
    assert "trip_sequence" not in dataset.diaries[0].trips[0].metadata


def test_departure_window_requires_explicit_trip_sequence() -> None:
    """Mark a windowed chain invalid when its trip order cannot be inferred."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "car",
                "earliest_departure_second": 100,
                "latest_departure_second": 200,
                "travel_time_seconds": 60,
            }
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == ["unresolved_trip_order"]
    assert result.report.invalid_chains == ("household_id=h1; person_id=p1",)


def test_duplicate_concrete_departures_require_trip_sequence() -> None:
    """Reject tied departure times when no explicit sequence resolves their order."""
    trips = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "departure_second": 900,
                "arrival_second": 1800,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "home",
                "purpose": "home",
                "mode": "bus",
                "departure_second": 900,
                "arrival_second": 1200,
            },
        ]
    )
    result = athenspop.validation.schema.validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == ["unresolved_trip_order"]


def test_trip_sequence_must_be_integer_and_unique_within_chain() -> None:
    """Distinguish noninteger sequence values from duplicate sequence positions."""
    invalid = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "trip_sequence": 1.5,
                "departure_second": 900,
                "arrival_second": 1800,
            }
        ]
    )
    assert [
        issue.code
        for issue in athenspop.validation.schema.validate_dataframes(
            invalid
        ).report.errors
    ] == ["invalid_trip_sequence"]
    duplicate = pd.DataFrame(
        [
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t1",
                "origin": "home",
                "destination": "work",
                "purpose": "work",
                "mode": "bus",
                "trip_sequence": 1,
                "departure_second": 900,
                "arrival_second": 1800,
            },
            {
                "household_id": "h1",
                "person_id": "p1",
                "trip_id": "t2",
                "origin": "work",
                "destination": "home",
                "purpose": "home",
                "mode": "bus",
                "trip_sequence": 1,
                "departure_second": 3600,
                "arrival_second": 4500,
            },
        ]
    )
    assert [
        issue.code
        for issue in athenspop.validation.schema.validate_dataframes(
            duplicate
        ).report.errors
    ] == ["duplicate_trip_sequence"]


def test_join_and_chain_diagnostic_codes_are_reported() -> None:
    """Report orphan metadata, incomplete ordering, and temporal overlap precisely."""
    orphan_household = athenspop.validation.schema.validate_dataframes(
        pd.DataFrame([_trip_row(household_id="missing")]),
        households=pd.DataFrame([{"household_id": "known"}]),
    )
    assert [issue.code for issue in orphan_household.report.errors] == [
        "orphan_trip_household"
    ]

    orphan_person_household = athenspop.validation.schema.validate_dataframes(
        pd.DataFrame([_trip_row(household_id="known")]),
        persons=pd.DataFrame(
            [
                {"household_id": "known", "person_id": "p1"},
                {"household_id": "missing", "person_id": "p2"},
            ]
        ),
        households=pd.DataFrame([{"household_id": "known"}]),
    )
    assert [issue.code for issue in orphan_person_household.report.errors] == [
        "orphan_person_household"
    ]

    missing_sequence = pd.DataFrame([_trip_row(trip_sequence=None)])
    assert [
        issue.code
        for issue in athenspop.validation.schema.validate_dataframes(
            missing_sequence
        ).report.errors
    ] == ["missing_trip_sequence"]

    overlapping = pd.DataFrame(
        [
            _trip_row(
                trip_id="t1",
                trip_sequence=1,
                departure_second=0,
                arrival_second=900,
            ),
            _trip_row(
                trip_id="t2",
                trip_sequence=2,
                departure_second=800,
                arrival_second=1200,
            ),
        ]
    )
    assert [
        issue.code
        for issue in athenspop.validation.schema.validate_dataframes(
            overlapping
        ).report.errors
    ] == ["overlapping_trips"]
