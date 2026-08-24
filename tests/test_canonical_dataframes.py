from typing import cast

import pandas as pd
import pytest

from athenspop import SurveyDataset, ValidationError, validate_dataframes
from athenspop.types import TravelTimeFunction


def _constant_travel_time(seconds: int) -> TravelTimeFunction:
    def travel_time_function(
        origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        del origin, destination, mode, departure_second
        return seconds

    return travel_time_function


def _trip_row(**overrides: object) -> dict[str, object]:
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
    result = validate_dataframes(trips, persons=persons, households=households)
    assert not result.report.has_errors
    dataset = SurveyDataset.from_dataframes(
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


def test_loads_departure_plus_duration_as_concrete_arrival() -> None:
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
    dataset = SurveyDataset.from_dataframes(trips)
    trip = dataset.diaries[0].trips[0]
    assert trip.departure_second == 60
    assert trip.travel_time_seconds == 120
    assert trip.arrival_second == 180


def test_travel_time_function_is_checked_when_model_resolves_duration() -> None:
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
    dataset = SurveyDataset.from_dataframes(
        trips, travel_time_function=_constant_travel_time(120)
    )
    assert dataset.diaries[0].trips[0].arrival_second == 180
    with pytest.raises(ValueError, match="strictly positive integer"):
        SurveyDataset.from_dataframes(
            trips, travel_time_function=_constant_travel_time(0)
        )


def test_validation_collects_join_and_timing_errors_without_cascade() -> (
    None
):
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
    result = validate_dataframes(trips, persons=persons)
    codes = [issue.code for issue in result.report.errors]
    assert "null_key" in codes
    assert "negative_second" not in codes
    assert "orphan_trip_person" in codes
    assert "non_positive_travel_duration" in codes


def test_ambiguous_timing_pattern_raises_concise_validation_error() -> None:
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
    result = validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == [
        "invalid_timing_pattern"
    ]
    with pytest.raises(ValidationError):
        result.report.raise_if_invalid()


def test_table_level_validation_diagnostic_codes_are_reported() -> None:
    not_dataframe = validate_dataframes(cast("pd.DataFrame", object()))
    assert [issue.code for issue in not_dataframe.report.errors] == [
        "table_not_dataframe"
    ]

    duplicate_columns = pd.DataFrame(
        [["h1", "p1", "t1"]],
        columns=["household_id", "household_id", "trip_id"],
    )
    duplicate_result = validate_dataframes(duplicate_columns)
    assert [issue.code for issue in duplicate_result.report.errors] == [
        "duplicate_columns"
    ]

    missing_columns = validate_dataframes(
        pd.DataFrame([{"household_id": "h1"}])
    )
    assert [issue.code for issue in missing_columns.report.errors] == [
        "missing_required_columns"
    ]


def test_float_seconds_are_rejected_even_when_integer_valued() -> None:
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
    result = validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == ["invalid_second"]


def test_duplicate_keys_are_checked_after_string_normalization() -> None:
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
    result = validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == [
        "duplicate_key",
        "duplicate_key",
    ]


def test_non_scalar_key_and_movement_values_are_rejected_at_boundary() -> None:
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
    key_result = validate_dataframes(non_scalar_key_trips)
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
    origin_result = validate_dataframes(non_scalar_origin_trips)
    assert [issue.code for issue in origin_result.report.errors] == [
        "unsupported_trip_value"
    ]


def test_trip_row_domain_diagnostic_codes_are_reported_once() -> None:
    missing_value = validate_dataframes(
        pd.DataFrame([_trip_row(origin="")])
    )
    assert [issue.code for issue in missing_value.report.errors] == [
        "missing_trip_value"
    ]

    arrival_window = validate_dataframes(
        pd.DataFrame([_trip_row(earliest_arrival_second=100)])
    )
    assert [issue.code for issue in arrival_window.report.errors] == [
        "unsupported_arrival_window"
    ]

    negative_second = validate_dataframes(
        pd.DataFrame([_trip_row(departure_second=-1)])
    )
    assert [issue.code for issue in negative_second.report.errors] == [
        "negative_second"
    ]


def test_mixed_timing_patterns_accept_nullable_integer_second_columns() -> None:
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
    result = validate_dataframes(trips)
    assert not result.report.has_errors
    dataset = SurveyDataset.from_dataframes(trips)
    assert dataset.diaries[0].trips[0].departure_window is not None
    assert dataset.diaries[0].trips[1].departure_second == 100


def test_non_scalar_metadata_is_rejected_at_validation_boundary() -> None:
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
    result = validate_dataframes(trips, persons=persons)
    assert [issue.code for issue in result.report.errors] == [
        "unsupported_metadata_value"
    ]
    with pytest.raises(ValidationError, match="1 error"):
        SurveyDataset.from_dataframes(trips, persons=persons)


def test_origin_mismatch_is_warning_not_hard_error() -> None:
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
    result = validate_dataframes(trips)
    assert not result.report.has_errors
    assert result.report.has_warnings
    assert [issue.code for issue in result.report.warnings] == [
        "origin_mismatch"
    ]
    result.report.raise_if_invalid()


def test_validation_does_not_assume_scheduler_minimum_activity_duration() -> (
    None
):
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
    result = validate_dataframes(trips)
    assert not result.report.has_errors
    assert result.report.warnings == ()


def test_household_metadata_does_not_create_study_specific_chain_warnings() -> (
    None
):
    households = pd.DataFrame(
        [{"household_id": "h1", "home_zone": "zone-home"}]
    )
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
        validate_dataframes(trips, households=households).report.warnings == ()
    )


def test_user_defined_purpose_and_mode_labels_are_valid() -> None:
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
    result = validate_dataframes(trips)
    assert not result.report.has_errors
    assert result.report.warnings == ()


def test_trip_sequence_orders_model_trips_when_input_rows_are_unsorted() -> (
    None
):
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
    result = validate_dataframes(trips)
    assert not result.report.has_errors
    assert result.normalized_tables is not None
    assert result.normalized_tables.trips["trip_id"].tolist() == ["t1", "t2"]
    dataset = SurveyDataset.from_dataframes(trips)
    assert [trip.trip_id for trip in dataset.diaries[0].trips] == ["t1", "t2"]
    assert "trip_sequence" not in dataset.diaries[0].trips[0].metadata


def test_departure_window_requires_explicit_trip_sequence() -> None:
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
    result = validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == [
        "unresolved_trip_order"
    ]
    assert result.report.invalid_chains == ("household_id=h1; person_id=p1",)


def test_duplicate_concrete_departures_require_trip_sequence() -> None:
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
    result = validate_dataframes(trips)
    assert [issue.code for issue in result.report.errors] == [
        "unresolved_trip_order"
    ]


def test_trip_sequence_must_be_integer_and_unique_within_chain() -> None:
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
        issue.code for issue in validate_dataframes(invalid).report.errors
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
        issue.code for issue in validate_dataframes(duplicate).report.errors
    ] == ["duplicate_trip_sequence"]


def test_join_and_chain_diagnostic_codes_are_reported() -> None:
    orphan_household = validate_dataframes(
        pd.DataFrame([_trip_row(household_id="missing")]),
        households=pd.DataFrame([{"household_id": "known"}]),
    )
    assert [issue.code for issue in orphan_household.report.errors] == [
        "orphan_trip_household"
    ]

    orphan_person_household = validate_dataframes(
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
        for issue in validate_dataframes(missing_sequence).report.errors
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
        issue.code for issue in validate_dataframes(overlapping).report.errors
    ] == ["overlapping_trips"]
