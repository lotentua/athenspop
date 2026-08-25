# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module defines episode and state-sequence construction contracts."""

import dataclasses

import pandas as pd
import pytest

import athenspop.model.survey
import athenspop.scheduling.engine
import athenspop.schema
import athenspop.sequence.distance
import athenspop.sequence.episodes


def _trip(**overrides: object) -> athenspop.model.survey.Trip:
    """Return a valid scheduled trip with selected values replaced."""
    base = athenspop.model.survey.Trip(
        household_id="h1",
        person_id="p1",
        trip_id="t1",
        origin="home",
        destination="work",
        purpose="work",
        mode="bus",
        departure_second=900,
        arrival_second=1_800,
        travel_time_seconds=900,
        departure_window=None,
        timing_pattern=athenspop.schema.TimingPattern.DEPARTURE_ARRIVAL,
        metadata={},
    )
    return dataclasses.replace(base, **overrides)


def _prefixed_trip_state(trip: athenspop.model.survey.Trip) -> str:
    """Return a movement-state label derived from the trip mode."""
    return f"trip_{trip.mode}"


def test_overlap_duration_counts_integer_second_intersection() -> None:
    """Measure half-open intersections without returning negative durations."""
    episode = athenspop.sequence.episodes.Episode(
        state="work", start_second=300, end_second=1200
    )
    assert athenspop.sequence.episodes.overlap_duration(episode, 0, 900) == 600
    assert athenspop.sequence.episodes.overlap_duration(episode, 900, 1800) == 300
    assert athenspop.sequence.episodes.overlap_duration(episode, 1200, 1800) == 0


def test_discretize_episodes_uses_overlap_and_tie_break() -> None:
    """Select the greatest-overlap state and break equal overlaps by first start."""
    tied = (
        athenspop.sequence.episodes.Episode(
            state="home", start_second=0, end_second=450
        ),
        athenspop.sequence.episodes.Episode(
            state="work", start_second=450, end_second=900
        ),
    )
    assert athenspop.sequence.episodes.discretize_episodes(
        tied, window_end_second=900
    ) == ("home",)
    dominant = (
        athenspop.sequence.episodes.Episode(
            state="home", start_second=0, end_second=400
        ),
        athenspop.sequence.episodes.Episode(
            state="work", start_second=400, end_second=900
        ),
    )
    assert athenspop.sequence.episodes.discretize_episodes(
        dominant, window_end_second=900
    ) == ("work",)


def test_episodes_from_diary_partitions_activity_and_trip_states() -> None:
    """Partition a scheduled diary into contiguous activity and travel episodes."""
    diary = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            _trip(),
            _trip(
                trip_id="t2",
                origin="work",
                destination="home",
                purpose="home",
                mode="walk",
                departure_second=3600,
                arrival_second=4500,
            ),
        ),
    )
    episodes = athenspop.sequence.episodes.episodes_from_diary(
        diary,
        initial_activity_state="home",
        travel_state_labeler=_prefixed_trip_state,
        window_end_second=5400,
    )
    assert episodes == (
        athenspop.sequence.episodes.Episode(
            state="home", start_second=0, end_second=900
        ),
        athenspop.sequence.episodes.Episode(
            state="trip_bus", start_second=900, end_second=1800
        ),
        athenspop.sequence.episodes.Episode(
            state="work", start_second=1800, end_second=3600
        ),
        athenspop.sequence.episodes.Episode(
            state="trip_walk", start_second=3600, end_second=4500
        ),
        athenspop.sequence.episodes.Episode(
            state="home", start_second=4500, end_second=5400
        ),
    )


def test_episodes_from_diary_crops_trip_crossing_observation_window() -> None:
    """Crop travel at the exclusive observation-window boundary."""
    diary = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            _trip(
                destination="cinema",
                purpose="recreation",
                mode="walk",
                departure_second=800,
                arrival_second=1200,
                travel_time_seconds=400,
            ),
        ),
    )
    episodes = athenspop.sequence.episodes.episodes_from_diary(
        diary,
        initial_activity_state="home",
        travel_state_labeler=_prefixed_trip_state,
        window_end_second=1000,
    )
    assert episodes == (
        athenspop.sequence.episodes.Episode(
            state="home", start_second=0, end_second=800
        ),
        athenspop.sequence.episodes.Episode(
            state="trip_walk", start_second=800, end_second=1000
        ),
    )


def test_state_sequence_from_scheduled_diary() -> None:
    """Convert a scheduled diary into fixed-width activity and mode states."""
    diary = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            _trip(
                destination="market",
                purpose="market",
                mode="car",
            ),
        ),
    )
    states = athenspop.sequence.episodes.state_sequence_from_diary(
        diary,
        initial_activity_state="home",
        window_end_second=2700,
        interval_seconds=900,
    )
    assert states == ("home", "trip_car", "market")


def test_state_sequence_accepts_caller_defined_travel_state_labels() -> None:
    """Use the caller's travel-state labeler instead of the mode prefix."""
    diary = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            _trip(
                mode="pt",
            ),
        ),
    )
    states = athenspop.sequence.episodes.state_sequence_from_diary(
        diary,
        initial_activity_state="home",
        travel_state_labeler=lambda trip: f"leg:{trip.mode}",
        window_end_second=2700,
        interval_seconds=900,
    )
    assert states == ("home", "leg:pt", "work")


def test_episodes_from_diary_rejects_unscheduled_or_overlapping_trips() -> None:
    """Reject missing concrete times and departures before the prior arrival."""
    unscheduled = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            _trip(
                arrival_second=None,
                travel_time_seconds=None,
            ),
        ),
    )
    with pytest.raises(ValueError, match="not scheduled"):
        athenspop.sequence.episodes.episodes_from_diary(
            unscheduled, initial_activity_state="home", window_end_second=1800
        )
    overlapping = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            _trip(),
            _trip(
                trip_id="t2",
                origin="work",
                destination="home",
                purpose="home",
                departure_second=1700,
                arrival_second=2200,
                travel_time_seconds=500,
            ),
        ),
    )
    with pytest.raises(ValueError, match="before the previous trip"):
        athenspop.sequence.episodes.episodes_from_diary(
            overlapping, initial_activity_state="home", window_end_second=3600
        )


def test_episode_construction_validates_the_complete_diary_before_cropping() -> None:
    """Reject invalid timing even when the affected trip is outside the window."""
    invalid_before_window = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(_trip(departure_second=100, arrival_second=100),),
    )

    with pytest.raises(ValueError, match="must be after departure"):
        athenspop.sequence.episodes.episodes_from_diary(
            invalid_before_window,
            initial_activity_state="home",
            window_start_second=500,
            window_end_second=1_000,
        )


def test_episode_construction_tracks_trips_outside_and_across_the_window() -> None:
    """Use prior destinations and crop travel that crosses the window start."""
    before_and_after = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(
            _trip(departure_second=100, arrival_second=200, purpose="work"),
            _trip(
                trip_id="t2",
                origin="work",
                departure_second=1_100,
                arrival_second=1_200,
            ),
        ),
    )
    assert athenspop.sequence.episodes.episodes_from_diary(
        before_and_after,
        initial_activity_state="home",
        window_start_second=500,
        window_end_second=1_000,
    ) == (
        athenspop.sequence.episodes.Episode(
            state="work", start_second=500, end_second=1_000
        ),
    )

    crossing_start = athenspop.model.survey.Diary(
        household_id="h1",
        person_id="p1",
        trips=(_trip(departure_second=400, arrival_second=600),),
    )
    assert athenspop.sequence.episodes.episodes_from_diary(
        crossing_start,
        initial_activity_state="home",
        window_start_second=500,
        window_end_second=1_000,
    ) == (
        athenspop.sequence.episodes.Episode(
            state="trip_bus", start_second=500, end_second=600
        ),
        athenspop.sequence.episodes.Episode(
            state="work", start_second=600, end_second=1_000
        ),
    )
    assert athenspop.sequence.episodes.state_sequence_from_diary(
        crossing_start,
        initial_activity_state="home",
        window_start_second=500,
        window_end_second=1_000,
        interval_seconds=250,
    ) == ("work", "work")


def test_episode_construction_requires_nonempty_caller_defined_states() -> None:
    """Reject invalid initial and custom travel-state labels at the public boundary."""
    diary = athenspop.model.survey.Diary(
        household_id="h1", person_id="p1", trips=(_trip(),)
    )

    with pytest.raises(TypeError, match="initial_activity_state"):
        athenspop.sequence.episodes.episodes_from_diary(
            diary, initial_activity_state="", window_end_second=2_000
        )
    with pytest.raises(TypeError, match="travel_state_labeler result"):
        athenspop.sequence.episodes.episodes_from_diary(
            diary,
            initial_activity_state="home",
            travel_state_labeler=lambda trip: "",
            window_end_second=2_000,
        )


def test_sequence_bridge_accepts_scheduled_dataset_from_public_loader() -> None:
    """Pass a publicly loaded and scheduled diary directly into sequencing."""
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
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(trips)
    scheduled = athenspop.scheduling.engine.schedule_once(dataset)
    states = athenspop.sequence.episodes.state_sequence_from_diary(
        scheduled.dataset.diaries[0],
        initial_activity_state="home",
        travel_state_labeler=_prefixed_trip_state,
        window_end_second=2700,
        interval_seconds=900,
    )
    assert states == ("home", "trip_bus", "work")


def test_dissimilarity_matrix_rejects_asymmetric_substitution_costs() -> None:
    """Require reverse substitution costs to match in a symmetric matrix."""
    with pytest.raises(ValueError, match="requires symmetric substitution costs"):
        athenspop.sequence.distance.dissimilarity_matrix(
            (("home",), ("work",)),
            substitution_cost={
                ("home", "work"): 1.0,
                ("work", "home"): 5.0,
            },
        )
