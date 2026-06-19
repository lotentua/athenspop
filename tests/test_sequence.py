import pandas as pd
import pytest

from athenspop import SurveyDataset, schedule_once
from athenspop.model import Diary, Trip
from athenspop.sequence import (
    Episode,
    discretize_episodes,
    episodes_from_diary,
    overlap_duration,
    state_sequence_from_diary,
)
from athenspop.validation.schema import TimingPattern


def _prefixed_trip_state(trip: Trip) -> str:
    return f"trip_{trip.mode}"


def test_overlap_duration_counts_integer_second_intersection() -> None:
    episode = Episode(state="work", start_second=300, end_second=1200)
    assert overlap_duration(episode, 0, 900) == 600
    assert overlap_duration(episode, 900, 1800) == 300
    assert overlap_duration(episode, 1200, 1800) == 0


def test_discretize_episodes_uses_maximum_overlap_and_earliest_start_tie_break() -> None:
    tied = (
        Episode(state="home", start_second=0, end_second=450),
        Episode(state="work", start_second=450, end_second=900),
    )
    assert discretize_episodes(tied, window_end_second=900) == ("home",)
    dominant = (
        Episode(state="home", start_second=0, end_second=400),
        Episode(state="work", start_second=400, end_second=900),
    )
    assert discretize_episodes(dominant, window_end_second=900) == ("work",)


def test_episodes_from_diary_partitions_window_with_activity_and_trip_states() -> None:
    diary = Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t1",
                origin="home",
                destination="work",
                purpose="work",
                mode="bus",
                departure_second=900,
                arrival_second=1800,
                travel_time_seconds=900,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t2",
                origin="work",
                destination="home",
                purpose="home",
                mode="walk",
                departure_second=3600,
                arrival_second=4500,
                travel_time_seconds=900,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
        ),
    )
    episodes = episodes_from_diary(diary, initial_activity_state="home", travel_state_labeler=_prefixed_trip_state, window_end_second=5400)
    assert episodes == (
        Episode(state="home", start_second=0, end_second=900),
        Episode(state="trip_bus", start_second=900, end_second=1800),
        Episode(state="work", start_second=1800, end_second=3600),
        Episode(state="trip_walk", start_second=3600, end_second=4500),
        Episode(state="home", start_second=4500, end_second=5400),
    )


def test_episodes_from_diary_crops_trip_crossing_observation_window() -> None:
    diary = Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t1",
                origin="home",
                destination="cinema",
                purpose="recreation",
                mode="walk",
                departure_second=800,
                arrival_second=1200,
                travel_time_seconds=400,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
        ),
    )
    episodes = episodes_from_diary(diary, initial_activity_state="home", travel_state_labeler=_prefixed_trip_state, window_end_second=1000)
    assert episodes == (
        Episode(state="home", start_second=0, end_second=800),
        Episode(state="trip_walk", start_second=800, end_second=1000),
    )


def test_state_sequence_from_scheduled_diary() -> None:
    diary = Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t1",
                origin="home",
                destination="market",
                purpose="market",
                mode="car",
                departure_second=900,
                arrival_second=1800,
                travel_time_seconds=900,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
        ),
    )
    states = state_sequence_from_diary(diary, initial_activity_state="home", window_end_second=2700, interval_seconds=900)
    assert states == ("home", "car", "market")


def test_state_sequence_accepts_caller_defined_travel_state_labels() -> None:
    diary = Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t1",
                origin="home",
                destination="work",
                purpose="work",
                mode="pt",
                departure_second=900,
                arrival_second=1800,
                travel_time_seconds=900,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
        ),
    )
    states = state_sequence_from_diary(
        diary,
        initial_activity_state="home",
        travel_state_labeler=lambda trip: f"leg:{trip.mode}",
        window_end_second=2700,
        interval_seconds=900,
    )
    assert states == ("home", "leg:pt", "work")


def test_episodes_from_diary_rejects_unscheduled_or_overlapping_trips() -> None:
    unscheduled = Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t1",
                origin="home",
                destination="work",
                purpose="work",
                mode="bus",
                departure_second=900,
                arrival_second=None,
                travel_time_seconds=None,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
        ),
    )
    with pytest.raises(ValueError, match="not scheduled"):
        episodes_from_diary(unscheduled, initial_activity_state="home", window_end_second=1800)
    overlapping = Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t1",
                origin="home",
                destination="work",
                purpose="work",
                mode="bus",
                departure_second=900,
                arrival_second=1800,
                travel_time_seconds=900,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
            Trip(
                household_id="h1",
                person_id="p1",
                trip_id="t2",
                origin="work",
                destination="home",
                purpose="home",
                mode="bus",
                departure_second=1700,
                arrival_second=2200,
                travel_time_seconds=500,
                departure_window=None,
                timing_pattern=TimingPattern.DEPARTURE_ARRIVAL,
                metadata={},
            ),
        ),
    )
    with pytest.raises(ValueError, match="before the previous episode"):
        episodes_from_diary(overlapping, initial_activity_state="home", window_end_second=3600)


def test_sequence_bridge_accepts_scheduled_dataset_from_public_loader() -> None:
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
            }
        ]
    )
    dataset = SurveyDataset.from_dataframes(trips)
    scheduled = schedule_once(dataset)
    states = state_sequence_from_diary(
        scheduled.diaries[0],
        initial_activity_state="home",
        travel_state_labeler=_prefixed_trip_state,
        window_end_second=2700,
        interval_seconds=900,
    )
    assert states == ("home", "trip_bus", "work")
