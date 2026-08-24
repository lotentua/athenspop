from pathlib import Path

import pandas as pd
import pytest

from athenspop import (
    SchedulingConfig,
    SurveyDataset,
    schedule_once,
    validate_dataframes,
)
from examples.athens.inputs import (
    load_athens_wide_diaries,
    load_wide_diary_fixture,
    wide_diaries_to_canonical,
)
from examples.athens.travel_time import AthensTravelTimeResolver


def test_load_wide_diary_fixture_converts_to_canonical_tables() -> None:
    tables = load_wide_diary_fixture(
        Path("tests/example_data/NEW_diaries_athens_final.csv")
    )
    assert tables.raw_diaries == 3
    assert tables.canonical_trips == 9
    assert tables.persons.shape[0] == 3
    assert tables.households.shape[0] == 3
    assert tables.trips["trip_sequence"].tolist() == [1, 2, 3, 1, 2, 3, 1, 2, 3]
    assert tables.trips["earliest_departure_second"].min() == 14_400
    assert set(tables.trips["purpose"]) == {
        "education",
        "home",
        "other",
        "recreation",
        "work",
    }
    assert set(tables.trips["mode"]) == {"bus", "car", "walk"}
    result = validate_dataframes(
        tables.trips, persons=tables.persons, households=tables.households
    )
    assert not result.report.has_errors
    dataset = SurveyDataset.from_dataframes(
        tables.trips, persons=tables.persons, households=tables.households
    )
    assert len(dataset.diaries) == 3


def test_load_athens_wide_diaries_matches_migrated_source_stage_counts() -> None:
    tables = load_athens_wide_diaries()
    assert tables.raw_diaries == 513
    assert tables.canonical_trips == 1347
    assert tables.persons.shape[0] == 513
    assert tables.households.shape[0] == 513
    assert (tables.trips["purpose"] == "service").sum() == 9
    assert (tables.trips["mode"] == "taxi").sum() == 52
    result = validate_dataframes(
        tables.trips, persons=tables.persons, households=tables.households
    )
    assert not result.report.has_errors


def test_wide_diary_conversion_rejects_missing_columns() -> None:
    wide = pd.read_csv("tests/example_data/NEW_diaries_athens_final.csv").drop(
        columns="mode1"
    )

    with pytest.raises(ValueError, match="missing required column.*mode1"):
        wide_diaries_to_canonical(wide)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("time1", 7.5, "integer hour"),
        ("time1", 24, "between 0 and 23"),
        ("purp1", "unknown", "Unsupported raw trip purpose"),
        ("mode1", "unknown", "Unsupported raw trip mode"),
    ],
)
def test_wide_diary_conversion_rejects_malformed_trip_cells(
    column: str, value: object, message: str
) -> None:
    wide = pd.read_csv("tests/example_data/NEW_diaries_athens_final.csv").head(1)
    wide[column] = wide[column].astype(object)
    wide.loc[wide.index[0], column] = value

    with pytest.raises(ValueError, match=message):
        wide_diaries_to_canonical(wide)


def test_load_athens_wide_diaries_can_emit_travel_time_function_rows() -> None:
    tables = load_athens_wide_diaries(fixture_travel_time_seconds=None)
    resolver = AthensTravelTimeResolver.from_files()
    assert "travel_time_seconds" not in tables.trips.columns
    result = validate_dataframes(
        tables.trips,
        persons=tables.persons,
        households=tables.households,
        travel_time_function=resolver,
    )
    assert not result.report.has_errors


def test_migrated_athens_source_schedules_with_cropping_policy() -> None:
    tables = load_athens_wide_diaries()
    dataset = SurveyDataset.from_dataframes(
        tables.trips, persons=tables.persons, households=tables.households
    )
    scheduled = schedule_once(
        dataset,
        seed=2026,
        config=SchedulingConfig(
            min_activity_duration_seconds=1800,
            allow_trips_after_observation_window=True,
        ),
    )
    assert scheduled.diagnostics.attempted_diaries == 513
    assert scheduled.diagnostics.scheduled_diaries == 513
    assert scheduled.diagnostics.issues == ()


def test_migrated_athens_source_schedules_with_real_travel_time_resolver() -> None:
    tables = load_athens_wide_diaries(fixture_travel_time_seconds=None)
    resolver = AthensTravelTimeResolver.from_files()
    dataset = SurveyDataset.from_dataframes(
        tables.trips,
        persons=tables.persons,
        households=tables.households,
        travel_time_function=resolver,
    )
    scheduled = schedule_once(
        dataset,
        seed=2026,
        config=SchedulingConfig(
            min_activity_duration_seconds=1800,
            allow_trips_after_observation_window=True,
        ),
        travel_time_function=resolver,
    )
    assert scheduled.diagnostics.attempted_diaries == 513
    assert scheduled.diagnostics.scheduled_diaries == 513
    assert scheduled.diagnostics.issues == ()


def test_athens_source_strict_routing_matches_legacy_exclusion() -> None:
    tables = load_athens_wide_diaries(fixture_travel_time_seconds=None)
    resolver = AthensTravelTimeResolver.from_files(missing_sample_policy="strict")
    dataset = SurveyDataset.from_dataframes(
        tables.trips,
        persons=tables.persons,
        households=tables.households,
        travel_time_function=resolver,
    )
    scheduled = schedule_once(
        dataset,
        seed=2026,
        config=SchedulingConfig(
            min_activity_duration_seconds=1800,
            allow_trips_after_observation_window=True,
        ),
        travel_time_function=resolver,
    )
    assert scheduled.diagnostics.attempted_diaries == 513
    assert scheduled.diagnostics.scheduled_diaries == 512
    assert scheduled.diagnostics.infeasible_diaries == (
        "household_id=549; person_id=549",
    )
    assert len(scheduled.diagnostics.issues) == 1
    issue = scheduled.diagnostics.issues[0]
    assert issue.code == "travel_time_function_error"
    assert issue.trip_id == "549_trip_2"
