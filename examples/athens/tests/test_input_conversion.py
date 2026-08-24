from pathlib import Path

from athenspop import (
    SchedulingConfig,
    SurveyDataset,
    schedule_once,
    validate_dataframes,
)
from examples.athens.inputs import (
    load_athens_wide_diaries,
    load_wide_diary_fixture,
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


def test_load_athens_wide_diaries_matches_migrated_source_stage_counts() -> (
    None
):
    tables = load_athens_wide_diaries()
    assert tables.raw_diaries == 513
    assert tables.canonical_trips == 1347
    assert tables.persons.shape[0] == 513
    assert tables.households.shape[0] == 513
    result = validate_dataframes(
        tables.trips, persons=tables.persons, households=tables.households
    )
    assert not result.report.has_errors


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


def test_migrated_athens_source_schedules_with_real_travel_time_resolver() -> (
    None
):
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


def test_athens_source_strict_routing_matches_legacy_exclusion() -> (
    None
):
    tables = load_athens_wide_diaries(fixture_travel_time_seconds=None)
    resolver = AthensTravelTimeResolver.from_files(
        missing_sample_policy="strict"
    )
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
